import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

from ..config import get_config
from ..prompts import get_video_script_prompt
from ..clients.gemini import gerar_conteudo
from ..clients.minio import garantir_bucket, upload_to_minio, upload_file_to_minio
from ..utils.text import extrair_titulo_do_markdown, slugify
from ..utils.storage import garantir_diretorio, salvar_arquivo_local


@dataclass
class RoteiroResult:
    """Result of generating a video script."""
    arquivo_origem: str
    roteiro: str
    nome_roteiro: str
    success: bool
    error: Optional[str] = None


def gerar_roteiro_video(conteudo_insight: str) -> str:
    """
    Generates a 30-second video script from insight content.

    Args:
        conteudo_insight: Educational insight in markdown format

    Returns:
        Generated video script text
    """
    prompt = get_video_script_prompt(conteudo_insight)
    return gerar_conteudo(prompt)


def processar_insight(arquivo: str, diretorio_insights: str) -> RoteiroResult:
    """
    Processes a single insight file and generates a video script.

    Args:
        arquivo: Name of the insight file
        diretorio_insights: Directory containing insight files

    Returns:
        RoteiroResult with generated script
    """
    try:
        caminho = os.path.join(diretorio_insights, arquivo)

        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        # Generate video script
        roteiro = gerar_roteiro_video(conteudo)

        # Extract title and generate file name
        titulo = extrair_titulo_do_markdown(conteudo)
        if titulo:
            slug = slugify(titulo)
            nome_roteiro = f"roteiro_{slug}.md"
        else:
            nome_arquivo_sem_ext = arquivo.replace('.md', '')
            nome_roteiro = f"roteiro_{nome_arquivo_sem_ext}.md"

        return RoteiroResult(
            arquivo_origem=arquivo,
            roteiro=roteiro,
            nome_roteiro=nome_roteiro,
            success=True
        )
    except Exception as e:
        return RoteiroResult(
            arquivo_origem=arquivo,
            roteiro='',
            nome_roteiro='',
            success=False,
            error=str(e)
        )


def salvar_roteiro(resultado: RoteiroResult, diretorio_roteiros: str) -> bool:
    """
    Saves a video script to local storage or MinIO.

    Args:
        resultado: RoteiroResult to save
        diretorio_roteiros: Local directory for saving

    Returns:
        True if save succeeded, False otherwise
    """
    if not resultado.success:
        print(f"Pulando {resultado.arquivo_origem} devido a erro: {resultado.error}")
        return False

    config = get_config()
    caminho = os.path.join(diretorio_roteiros, resultado.nome_roteiro)

    if config.save_on_minio:
        garantir_bucket(config.minio_bucket_roteiros)
        success = upload_to_minio(
            config.minio_bucket_roteiros,
            resultado.nome_roteiro,
            resultado.roteiro
        )
        if success:
            print(f"Roteiro salvo no MinIO: {resultado.nome_roteiro}")
        return success
    else:
        salvar_arquivo_local(caminho, resultado.roteiro)
        print(f"Roteiro salvo localmente: {caminho}")
        return True


def gerar_roteiros(
    diretorio_insights: str = 'insights_idosos',
    diretorio_roteiros: str = 'roteiros'
) -> List[str]:
    """
    Generates video scripts for all insights in parallel.

    Args:
        diretorio_insights: Directory containing insight markdown files
        diretorio_roteiros: Output directory for video scripts

    Returns:
        List of successfully generated script file names
    """
    config = get_config()
    garantir_diretorio(diretorio_roteiros)

    # Get all markdown files
    arquivos = [f for f in os.listdir(diretorio_insights) if f.endswith('.md')]

    if not arquivos:
        print("Nenhum arquivo de insight encontrado.")
        return []

    print(f"Gerando roteiros para {len(arquivos)} insights com {config.max_workers} workers...\n")

    resultados: List[RoteiroResult] = []
    roteiros_gerados: List[str] = []

    # Process insights in parallel
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {
            executor.submit(processar_insight, arquivo, diretorio_insights): arquivo
            for arquivo in arquivos
        }

        for future in as_completed(futures):
            arquivo = futures[future]
            try:
                resultado = future.result()
                resultados.append(resultado)
                status = "OK" if resultado.success else f"ERRO: {resultado.error}"
                print(f"[{len(resultados)}/{len(arquivos)}] {arquivo} -> {status}")
            except Exception as e:
                print(f"[{len(resultados)}/{len(arquivos)}] {arquivo} -> ERRO: {e}")

    # Save results
    print(f"\nSalvando {len(resultados)} roteiros...")

    for resultado in resultados:
        if salvar_roteiro(resultado, diretorio_roteiros):
            roteiros_gerados.append(resultado.nome_roteiro)

    return roteiros_gerados


def processar_e_subir_videos(diretorio_insights: str = 'insights_idosos') -> None:
    """
    Placeholder for Nano Banana video processing integration.

    This function is a stub for future video generation using
    the Nano Banana API.

    Args:
        diretorio_insights: Directory containing insight files
    """
    config = get_config()

    if config.save_on_minio:
        garantir_bucket(config.minio_bucket_aulas)

    arquivos = [f for f in os.listdir(diretorio_insights) if f.endswith('.md')]

    for arquivo in arquivos:
        caminho = os.path.join(diretorio_insights, arquivo)

        with open(caminho, 'r', encoding='utf-8') as f:
            roteiro = f.read()

        # --- PLACEHOLDER FOR NANO BANANA API ---
        # Here would go the Nano Banana API call using 'roteiro'
        # Assuming video is temporarily saved as 'video_temp.mp4'
        video_gerado = "video_temp.mp4"

        if not os.path.exists(video_gerado):
            print(f"Video temporario nao encontrado para {arquivo}")
            continue

        nome_video = arquivo.replace('.md', '.mp4')
        print(f"Subindo {nome_video} para o MinIO...")

        success = upload_file_to_minio(
            config.minio_bucket_aulas,
            video_gerado,
            nome_video,
            content_type='video/mp4'
        )

        if success:
            print(f"Sucesso: {nome_video} disponivel no storage.")
        else:
            print(f"Erro ao subir {arquivo}")
