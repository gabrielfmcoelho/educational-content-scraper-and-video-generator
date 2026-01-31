import os
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

from botocore.exceptions import ClientError

from ..config import get_config
from ..prompts import get_video_script_prompt
from ..clients.gemini import gerar_conteudo
from ..clients.minio import garantir_bucket, upload_to_minio, upload_file_to_minio, get_minio_client
from ..clients.veo import gerar_video_veo
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


def gerar_roteiro_video(conteudo_insight: str, contexto_consolidado: str = '') -> str:
    """
    Generates a 30-second video script from insight content.

    Args:
        conteudo_insight: Educational insight in markdown format
        contexto_consolidado: Optional consolidated insights for additional context

    Returns:
        Generated video script text
    """
    prompt = get_video_script_prompt(conteudo_insight, contexto_consolidado)
    return gerar_conteudo(prompt)


def processar_insight(arquivo: str, diretorio_insights: str, contexto_consolidado: str = '') -> RoteiroResult:
    """
    Processes a single insight file and generates a video script.

    Args:
        arquivo: Name of the insight file
        diretorio_insights: Directory containing insight files
        contexto_consolidado: Optional consolidated insights for additional context

    Returns:
        RoteiroResult with generated script
    """
    config = get_config()
    try:
        # Load content from MinIO or local
        if config.save_on_minio:
            conteudo = carregar_insight_bucket(arquivo)
            if not conteudo:
                raise Exception(f"Não foi possível carregar o arquivo {arquivo} do MinIO")
        else:
            caminho = os.path.join(diretorio_insights, arquivo)
            with open(caminho, 'r', encoding='utf-8') as f:
                conteudo = f.read()

        # Generate video script
        roteiro = gerar_roteiro_video(conteudo, contexto_consolidado)

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


def listar_insights_bucket() -> list:
    """
    Lists all markdown files in the MinIO insights bucket.

    Returns:
        List of markdown file names (excluding consolidado_insights.md)
    """
    config = get_config()
    try:
        s3 = get_minio_client()
        response = s3.list_objects_v2(Bucket=config.minio_bucket_insights)

        if 'Contents' not in response:
            print(f"Nenhum arquivo encontrado no bucket '{config.minio_bucket_insights}'")
            return []

        arquivos = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.md') and key != 'consolidado_insights.md':
                arquivos.append(key)

        return arquivos
    except Exception as e:
        print(f"Erro ao listar arquivos do MinIO: {e}")
        return []


def carregar_insight_bucket(arquivo: str) -> str:
    """
    Loads a specific insight file from MinIO bucket.

    Args:
        arquivo: Name of the insight file

    Returns:
        Content of the file or empty string if not found
    """
    config = get_config()
    try:
        s3 = get_minio_client()
        obj_data = s3.get_object(
            Bucket=config.minio_bucket_insights,
            Key=arquivo
        )
        return obj_data['Body'].read().decode('utf-8')
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print(f"Arquivo não encontrado no MinIO: {arquivo}")
        else:
            print(f"Erro ao carregar arquivo do MinIO: {e}")
        return ''
    except Exception as e:
        print(f"Erro ao carregar arquivo do MinIO: {e}")
        return ''


def carregar_consolidado(diretorio_insights: str = 'insights_idosos') -> str:
    """
    Loads the consolidated insights file to use as additional context.

    Args:
        diretorio_insights: Directory containing insight files

    Returns:
        Content of consolidado_insights.md or empty string if not found
    """
    config = get_config()
    
    if config.save_on_minio:
        # Try to load from MinIO
        try:
            s3 = get_minio_client()
            obj_data = s3.get_object(
                Bucket=config.minio_bucket_insights, 
                Key='consolidado_insights.md'
            )
            conteudo = obj_data['Body'].read().decode('utf-8')
            return conteudo
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                print("consolidado_insights.md não encontrado no MinIO")
            else:
                print(f"Erro ao carregar consolidado do MinIO: {e}")
            return ''
        except Exception as e:
            print(f"Erro ao carregar consolidado do MinIO: {e}")
            return ''
    else:
        # Try to load from local directory
        caminho = os.path.join(diretorio_insights, 'consolidado_insights.md')
        if os.path.exists(caminho):
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"Erro ao ler consolidado local: {e}")
                return ''
        else:
            print(f"Arquivo não encontrado: {caminho}")
            return ''


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

    # Load consolidated insights as context
    contexto_consolidado = carregar_consolidado(diretorio_insights)
    if contexto_consolidado:
        print(f"Consolidado carregado: {len(contexto_consolidado)} caracteres\n")
    else:
        print("Aviso: consolidado_insights.md não encontrado, gerando sem contexto adicional\n")

    # Get all markdown files (from MinIO or local)
    if config.save_on_minio:
        arquivos = listar_insights_bucket()
    else:
        garantir_diretorio(diretorio_insights)
        arquivos = [f for f in os.listdir(diretorio_insights) 
                    if f.endswith('.md') and f != 'consolidado_insights.md']

    if not arquivos:
        print("Nenhum arquivo de insight encontrado.")
        return []

    print(f"Gerando roteiros para {len(arquivos)} insights com {config.max_workers} workers...\n")

    resultados: List[RoteiroResult] = []
    roteiros_gerados: List[str] = []

    # Process insights in parallel
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {
            executor.submit(processar_insight, arquivo, diretorio_insights, contexto_consolidado): arquivo
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


def processar_e_subir_videos(diretorio_roteiros: str = 'roteiros') -> None:
    """
    Processes video scripts and generates videos using Veo API,
    then uploads them to MinIO.

    This function:
    1. Reads video scripts from local directory or MinIO
    2. Generates videos using Veo API
    3. Uploads generated videos to MinIO bucket

    Args:
        diretorio_roteiros: Directory containing script markdown files
    """
    config = get_config()

    # Ensure output bucket exists
    if config.save_on_minio:
        garantir_bucket(config.minio_bucket_aulas)
        garantir_bucket(config.minio_bucket_roteiros)

    # Get scripts from local directory or MinIO
    roteiros = obter_roteiros(diretorio_roteiros)

    if not roteiros:
        print("Nenhum roteiro encontrado para gerar vídeos.")
        return

    print(f"Processando {len(roteiros)} roteiros com Veo...\n")

    sucessos = 0
    erros = 0

    for idx, (nome_roteiro, conteudo_roteiro) in enumerate(roteiros.items(), 1):
        print(f"[{idx}/{len(roteiros)}] Processando: {nome_roteiro}")

        # Extract title for video generation
        titulo = extrair_titulo_do_markdown(conteudo_roteiro) or nome_roteiro.replace('.md', '')

        # Generate video using Veo
        video_bytes = gerar_video_veo(conteudo_roteiro, titulo)

        if not video_bytes:
            print(f"Erro ao gerar vídeo para: {nome_roteiro}")
            erros += 1
            continue

        # Generate video filename
        nome_video = nome_roteiro.replace('.md', '.mp4')

        # Upload video to MinIO
        if config.save_on_minio:
            success = upload_bytes_to_minio(
                config.minio_bucket_aulas,
                nome_video,
                video_bytes,
                content_type='video/mp4'
            )
            
            if success:
                print(f"✓ Vídeo salvo no MinIO: {nome_video}\n")
                sucessos += 1
            else:
                print(f"✗ Erro ao salvar vídeo no MinIO: {nome_video}\n")
                erros += 1
        else:
            # Save locally
            garantir_diretorio('videos')
            caminho_local = os.path.join('videos', nome_video)
            with open(caminho_local, 'wb') as f:
                f.write(video_bytes)
            print(f"✓ Vídeo salvo localmente: {caminho_local}\n")
            sucessos += 1

    print(f"\n=== RESUMO ===")
    print(f"Total de vídeos processados: {len(roteiros)}")
    print(f"Sucessos: {sucessos}")
    print(f"Erros: {erros}")


def obter_roteiros(diretorio_roteiros: str = 'roteiros') -> dict:
    """
    Gets video scripts from local directory or MinIO.

    Args:
        diretorio_roteiros: Directory containing script files

    Returns:
        Dictionary mapping script filename to content
    """
    config = get_config()
    roteiros = {}

    if config.save_on_minio:
        # Read from MinIO
        try:
            s3 = get_minio_client()
            response = s3.list_objects_v2(Bucket=config.minio_bucket_roteiros)

            if 'Contents' not in response:
                print(f"Nenhum roteiro encontrado no bucket '{config.minio_bucket_roteiros}'")
                return roteiros

            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.md'):
                    obj_data = s3.get_object(Bucket=config.minio_bucket_roteiros, Key=key)
                    conteudo = obj_data['Body'].read().decode('utf-8')
                    roteiros[key] = conteudo
                    print(f"Roteiro carregado do MinIO: {key}")

        except Exception as e:
            print(f"Erro ao ler roteiros do MinIO: {e}")
            return roteiros
    else:
        # Read from local directory
        if not os.path.exists(diretorio_roteiros):
            print(f"Diretório não encontrado: {diretorio_roteiros}")
            return roteiros

        for arquivo in os.listdir(diretorio_roteiros):
            if arquivo.endswith('.md'):
                caminho = os.path.join(diretorio_roteiros, arquivo)
                with open(caminho, 'r', encoding='utf-8') as f:
                    roteiros[arquivo] = f.read()
                print(f"Roteiro carregado localmente: {arquivo}")

    return roteiros


def upload_bytes_to_minio(
    bucket_name: str,
    key: str,
    content: bytes,
    content_type: str = 'application/octet-stream'
) -> bool:
    """
    Uploads bytes content to MinIO bucket.

    Args:
        bucket_name: Target bucket name
        key: Object key (file name in bucket)
        content: Bytes content to upload
        content_type: MIME type of the content

    Returns:
        True if upload succeeded, False otherwise
    """
    try:
        s3 = get_minio_client()
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type
        )
        return True
    except Exception as e:
        print(f"Erro ao fazer upload para MinIO: {e}")
        return False
