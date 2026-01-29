import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

from ..config import get_config
from ..prompts import get_insight_prompt, get_consolidation_prompt
from ..clients.gemini import gerar_conteudo
from ..clients.minio import garantir_bucket, upload_to_minio, wipe_bucket
from ..utils.text import extrair_titulo_do_markdown, gerar_nome_arquivo
from ..utils.storage import garantir_diretorio, salvar_arquivo_local
from .extractor import extrair_texto_site


@dataclass
class ProcessingResult:
    """Result of processing a single URL."""
    url: str
    indice: int
    markdown: str
    titulo: Optional[str]
    nome_arquivo: str
    success: bool
    error: Optional[str] = None


def processar_url(url: str, indice: int) -> ProcessingResult:
    """
    Processes a single URL: extracts content and generates insights.

    Args:
        url: URL to process
        indice: Index of the URL in the source list

    Returns:
        ProcessingResult with generated markdown and metadata
    """
    try:
        # Extract text from website
        texto_bruto = extrair_texto_site(url)

        # Generate insights using AI
        prompt = get_insight_prompt(url, texto_bruto)
        markdown = gerar_conteudo(prompt)

        # Extract title and generate file name
        titulo = extrair_titulo_do_markdown(markdown)
        nome_arquivo = gerar_nome_arquivo(titulo, 'topico', indice)

        return ProcessingResult(
            url=url,
            indice=indice,
            markdown=markdown,
            titulo=titulo,
            nome_arquivo=nome_arquivo,
            success=True
        )
    except Exception as e:
        return ProcessingResult(
            url=url,
            indice=indice,
            markdown='',
            titulo=None,
            nome_arquivo=f'topico_{indice}.md',
            success=False,
            error=str(e)
        )


def salvar_resultado(resultado: ProcessingResult, diretorio: str) -> bool:
    """
    Saves a processing result to local storage or MinIO.

    Args:
        resultado: ProcessingResult to save
        diretorio: Local directory for saving

    Returns:
        True if save succeeded, False otherwise
    """
    if not resultado.success:
        print(f"Pulando {resultado.url} devido a erro: {resultado.error}")
        return False

    config = get_config()
    caminho = os.path.join(diretorio, resultado.nome_arquivo)

    if config.save_on_minio:
        garantir_bucket(config.minio_bucket_insights)
        success = upload_to_minio(
            config.minio_bucket_insights,
            resultado.nome_arquivo,
            resultado.markdown
        )
        if success:
            print(f"Salvo no MinIO: {resultado.nome_arquivo}")
        return success
    else:
        salvar_arquivo_local(caminho, resultado.markdown)
        print(f"Salvo localmente: {caminho}")
        return True


def processar_urls_paralelo(
    urls: List[str],
    diretorio_saida: str = 'insights_idosos'
) -> tuple[List[str], List[ProcessingResult]]:
    """
    Processes multiple URLs in parallel using ThreadPoolExecutor.

    Args:
        urls: List of URLs to process
        diretorio_saida: Output directory for saving results

    Returns:
        Tuple of (list of file names, list of ProcessingResult)
    """
    config = get_config()
    garantir_diretorio(diretorio_saida)

    # Wipe bucket if configured
    if config.save_on_minio and config.wipe_bucket_before_start:
        garantir_bucket(config.minio_bucket_insights)
        wipe_bucket(config.minio_bucket_insights)

    resultados: List[ProcessingResult] = []
    arquivos_gerados: List[str] = []

    print(f"Processando {len(urls)} URLs com {config.max_workers} workers...\n")

    # Phase 1: Process URLs in parallel
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {
            executor.submit(processar_url, url, i): (url, i)
            for i, url in enumerate(urls)
        }

        for future in as_completed(futures):
            url, indice = futures[future]
            try:
                resultado = future.result()
                resultados.append(resultado)
                status = "OK" if resultado.success else f"ERRO: {resultado.error}"
                print(f"[{indice + 1}/{len(urls)}] {url[:50]}... -> {status}")
            except Exception as e:
                print(f"[{indice + 1}/{len(urls)}] {url[:50]}... -> ERRO: {e}")

    # Phase 2: Save results (can also be parallelized if needed)
    print(f"\nSalvando {len(resultados)} resultados...")

    for resultado in resultados:
        if salvar_resultado(resultado, diretorio_saida):
            arquivos_gerados.append(resultado.nome_arquivo)

    return arquivos_gerados, resultados


def consolidar_insights(
    resultados: Optional[List[ProcessingResult]] = None,
    diretorio_insights: str = 'insights_idosos'
) -> Optional[str]:
    """
    Generates a consolidated summary from all insights.

    Can use either in-memory results or read from local files.

    Args:
        resultados: Optional list of ProcessingResult from previous processing
        diretorio_insights: Directory containing insight markdown files (fallback)

    Returns:
        Path to the consolidated file, or None if failed
    """
    config = get_config()
    todos_insights = []

    # Use in-memory results if provided
    if resultados:
        successful_results = [r for r in resultados if r.success]
        if not successful_results:
            print("Nenhum insight valido para consolidar.")
            return None

        print(f"\nConsolidando {len(successful_results)} insights...")

        for resultado in successful_results:
            todos_insights.append(
                f"### {resultado.nome_arquivo}\n\n{resultado.markdown}\n\n---\n"
            )
    else:
        # Fallback: read from local files
        arquivos = [
            f for f in os.listdir(diretorio_insights)
            if f.endswith('.md') and f != 'consolidado_insights.md'
        ]

        if not arquivos:
            print("Nenhum arquivo de insight encontrado para consolidar.")
            return None

        print(f"\nConsolidando {len(arquivos)} insights...")

        for arquivo in arquivos:
            caminho = os.path.join(diretorio_insights, arquivo)
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    todos_insights.append(f"### {arquivo}\n\n{conteudo}\n\n---\n")
            except Exception as e:
                print(f"Erro ao ler {arquivo}: {e}")

    conteudo_combinado = "\n".join(todos_insights)

    # Generate consolidated insights using AI
    prompt = get_consolidation_prompt(conteudo_combinado)
    consolidado = gerar_conteudo(prompt)

    # Save consolidated file
    nome_arquivo = 'consolidado_insights.md'
    caminho_consolidado = os.path.join(diretorio_insights, nome_arquivo)

    if config.save_on_minio:
        garantir_bucket(config.minio_bucket_insights)
        success = upload_to_minio(
            config.minio_bucket_insights,
            nome_arquivo,
            consolidado
        )
        if success:
            print(f"Consolidado salvo no MinIO: {nome_arquivo}")
    else:
        salvar_arquivo_local(caminho_consolidado, consolidado)
        print(f"Consolidado salvo localmente: {caminho_consolidado}")

    return caminho_consolidado
