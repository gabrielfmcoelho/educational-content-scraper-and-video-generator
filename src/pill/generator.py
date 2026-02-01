"""Knowledge Pill (Pilula de Conhecimento) generation pipeline.

This module follows the same patterns as video/generator.py for consistency.
It generates accessibility-focused knowledge pills with:
- Short text (educational content)
- Infographic (AI-generated via Imagen/Vertex AI)
- Call to Action (question or challenge)
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from botocore.exceptions import ClientError

from ..config import get_config
from ..prompts_pill import (
    get_pill_short_text_prompt,
    get_pill_call_to_action_prompt,
    get_pill_title_prompt,
    get_infographic_prompt,
)
from ..clients.gemini import gerar_conteudo
from ..clients.minio import garantir_bucket, upload_to_minio, get_minio_client
from ..clients.imagen import gerar_infografico
from ..utils.text import extrair_titulo_do_markdown, slugify
from ..utils.storage import garantir_diretorio


@dataclass
class PillResult:
    """Result of generating a knowledge pill."""
    arquivo_origem: str
    pill_id: str
    title: str
    short_text: str
    call_to_action: Dict[str, str]
    infographic_filename: str
    infographic_bytes: Optional[bytes]
    success: bool
    error: Optional[str] = None

    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary (excludes bytes)."""
        return {
            "id": self.pill_id,
            "source_insight": self.arquivo_origem,
            "title": self.title,
            "short_text": self.short_text,
            "infographic_filename": self.infographic_filename,
            "call_to_action": self.call_to_action,
            "accessibility": {
                "target_audience": ["elderly", "neurodivergent"],
                "design_principles": [
                    "large_icons",
                    "high_contrast",
                    "soft_colors",
                    "literal_images"
                ]
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


def listar_insights_bucket() -> List[str]:
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
            print(f"No files found in bucket '{config.minio_bucket_insights}'")
            return []

        arquivos = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.md') and key != 'consolidado_insights.md':
                arquivos.append(key)

        return arquivos
    except Exception as e:
        print(f"Error listing files from MinIO: {e}")
        return []


def listar_pilulas_existentes() -> set:
    """
    Lists all existing pill files in MinIO or local directory.

    Returns:
        Set of existing pill filenames (e.g., {'pilula_xxx.json', ...})
    """
    config = get_config()
    pilulas = set()

    if config.save_on_minio:
        try:
            s3 = get_minio_client()
            # Ensure bucket exists before listing
            try:
                response = s3.list_objects_v2(Bucket=config.minio_bucket_pilulas)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        if key.endswith('.json'):
                            pilulas.add(key)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchBucket':
                    # Bucket doesn't exist yet - no pills exist
                    pass
                else:
                    raise
        except Exception as e:
            print(f"Error listing existing pills from MinIO: {e}")
    else:
        pilulas_dir = 'pilulas'
        if os.path.exists(pilulas_dir):
            for arquivo in os.listdir(pilulas_dir):
                if arquivo.endswith('.json'):
                    pilulas.add(arquivo)

    return pilulas


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
            print(f"File not found in MinIO: {arquivo}")
        else:
            print(f"Error loading file from MinIO: {e}")
        return ''
    except Exception as e:
        print(f"Error loading file from MinIO: {e}")
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
        try:
            s3 = get_minio_client()
            obj_data = s3.get_object(
                Bucket=config.minio_bucket_insights,
                Key='consolidado_insights.md'
            )
            return obj_data['Body'].read().decode('utf-8')
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                print("consolidado_insights.md not found in MinIO")
            else:
                print(f"Error loading consolidated from MinIO: {e}")
            return ''
        except Exception as e:
            print(f"Error loading consolidated from MinIO: {e}")
            return ''
    else:
        caminho = os.path.join(diretorio_insights, 'consolidado_insights.md')
        if os.path.exists(caminho):
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading local consolidated: {e}")
                return ''
        else:
            print(f"File not found: {caminho}")
            return ''


def gerar_titulo_pilula(conteudo_insight: str) -> str:
    """
    Generates a short, accessible title for the pill.

    Args:
        conteudo_insight: Educational insight content

    Returns:
        Generated title or fallback
    """
    try:
        prompt = get_pill_title_prompt(conteudo_insight)
        titulo = gerar_conteudo(prompt)
        # Clean up the response
        titulo = titulo.strip().strip('"\'')
        return titulo
    except Exception as e:
        print(f"Error generating title: {e}")
        # Fallback to extracting from markdown
        return extrair_titulo_do_markdown(conteudo_insight) or "Dica de Seguranca"


def gerar_texto_curto(conteudo_insight: str, contexto_consolidado: str = '') -> str:
    """
    Generates the short educational text for the pill.

    Args:
        conteudo_insight: Educational insight content
        contexto_consolidado: Optional consolidated insights for context

    Returns:
        Generated short text
    """
    prompt = get_pill_short_text_prompt(conteudo_insight, contexto_consolidado)
    return gerar_conteudo(prompt).strip()


def gerar_call_to_action(short_text: str, topic: str) -> Dict[str, str]:
    """
    Generates a call-to-action question for the pill.

    Args:
        short_text: The pill's short text
        topic: The topic/title

    Returns:
        Dict with type and text of the CTA
    """
    prompt = get_pill_call_to_action_prompt(short_text, topic)
    question = gerar_conteudo(prompt).strip().strip('"\'')
    return {
        "type": "question",
        "text": question
    }


def processar_insight_para_pilula(
    arquivo: str,
    diretorio_insights: str,
    contexto_consolidado: str = ''
) -> PillResult:
    """
    Processes a single insight file and generates a knowledge pill.

    This includes:
    1. Generate short text summary (Gemini)
    2. Generate title (Gemini)
    3. Generate call-to-action question (Gemini)
    4. Generate infographic (Imagen/Vertex AI)

    Args:
        arquivo: Name of the insight file
        diretorio_insights: Directory containing insight files
        contexto_consolidado: Optional consolidated insights for context

    Returns:
        PillResult with all generated content
    """
    config = get_config()

    try:
        # Load content from MinIO or local
        if config.save_on_minio:
            conteudo = carregar_insight_bucket(arquivo)
            if not conteudo:
                raise Exception(f"Could not load file {arquivo} from MinIO")
        else:
            caminho = os.path.join(diretorio_insights, arquivo)
            with open(caminho, 'r', encoding='utf-8') as f:
                conteudo = f.read()

        # Step 1: Generate title
        print(f"  Generating title...")
        titulo = gerar_titulo_pilula(conteudo)

        # Step 2: Generate short text
        print(f"  Generating short text...")
        short_text = gerar_texto_curto(conteudo, contexto_consolidado)

        # Step 3: Generate call-to-action
        print(f"  Generating call-to-action...")
        cta = gerar_call_to_action(short_text, titulo)

        # Step 4: Generate infographic
        print(f"  Generating infographic...")
        infographic_prompt = get_infographic_prompt(titulo, short_text)
        infographic_bytes = gerar_infografico(infographic_prompt)

        # Generate pill ID and filenames
        slug = slugify(titulo)
        pill_id = f"pilula_{slug}"
        infographic_filename = f"{pill_id}.png"

        return PillResult(
            arquivo_origem=arquivo,
            pill_id=pill_id,
            title=titulo,
            short_text=short_text,
            call_to_action=cta,
            infographic_filename=infographic_filename,
            infographic_bytes=infographic_bytes,
            success=True
        )

    except Exception as e:
        return PillResult(
            arquivo_origem=arquivo,
            pill_id='',
            title='',
            short_text='',
            call_to_action={},
            infographic_filename='',
            infographic_bytes=None,
            success=False,
            error=str(e)
        )


def salvar_pilula(resultado: PillResult, diretorio_pilulas: str = 'pilulas') -> bool:
    """
    Saves a knowledge pill to local storage or MinIO.

    Saves:
    1. Pill JSON data to pilulas bucket
    2. Infographic image to infograficos bucket

    Args:
        resultado: PillResult to save
        diretorio_pilulas: Local directory for saving

    Returns:
        True if save succeeded, False otherwise
    """
    if not resultado.success:
        print(f"Skipping {resultado.arquivo_origem} due to error: {resultado.error}")
        return False

    config = get_config()

    # Prepare JSON content
    pill_json = json.dumps(resultado.to_json_dict(), ensure_ascii=False, indent=2)
    pill_filename = f"{resultado.pill_id}.json"

    if config.save_on_minio:
        # Ensure buckets exist
        garantir_bucket(config.minio_bucket_pilulas)
        garantir_bucket(config.minio_bucket_infograficos)

        # Upload pill JSON
        success_json = upload_to_minio(
            config.minio_bucket_pilulas,
            pill_filename,
            pill_json
        )
        if success_json:
            print(f"  Pill JSON saved to MinIO: {pill_filename}")
        else:
            print(f"  ERROR saving pill JSON to MinIO: {pill_filename}")
            return False

        # Upload infographic if available
        if resultado.infographic_bytes:
            success_img = upload_bytes_to_minio(
                config.minio_bucket_infograficos,
                resultado.infographic_filename,
                resultado.infographic_bytes,
                content_type='image/png'
            )
            if success_img:
                print(f"  Infographic saved to MinIO: {resultado.infographic_filename}")
            else:
                print(f"  WARNING: Failed to save infographic to MinIO")
        else:
            print(f"  WARNING: No infographic bytes to save")

        return True
    else:
        # Save locally
        garantir_diretorio(diretorio_pilulas)
        garantir_diretorio('infograficos')

        # Save JSON
        caminho_json = os.path.join(diretorio_pilulas, pill_filename)
        with open(caminho_json, 'w', encoding='utf-8') as f:
            f.write(pill_json)
        print(f"  Pill saved locally: {caminho_json}")

        # Save infographic
        if resultado.infographic_bytes:
            caminho_img = os.path.join('infograficos', resultado.infographic_filename)
            with open(caminho_img, 'wb') as f:
                f.write(resultado.infographic_bytes)
            print(f"  Infographic saved locally: {caminho_img}")

        return True


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
        print(f"Error uploading to MinIO: {e}")
        return False


def gerar_pilulas(
    diretorio_insights: str = 'insights_idosos',
    diretorio_pilulas: str = 'pilulas'
) -> List[str]:
    """
    Generates knowledge pills for all insights in parallel.
    Skips insights that already have pills generated.

    Args:
        diretorio_insights: Directory containing insight markdown files
        diretorio_pilulas: Output directory for pill JSON files

    Returns:
        List of successfully generated pill file names
    """
    config = get_config()
    garantir_diretorio(diretorio_pilulas)

    # Get existing pills to skip
    pilulas_existentes = listar_pilulas_existentes()
    if pilulas_existentes:
        print(f"Found {len(pilulas_existentes)} existing pills.\n")

    # Load consolidated insights as context
    contexto_consolidado = carregar_consolidado(diretorio_insights)
    if contexto_consolidado:
        print(f"Consolidated loaded: {len(contexto_consolidado)} characters\n")
    else:
        print("Warning: consolidado_insights.md not found, generating without additional context\n")

    # Get all markdown files (from MinIO or local)
    if config.save_on_minio:
        arquivos = listar_insights_bucket()
    else:
        garantir_diretorio(diretorio_insights)
        arquivos = [f for f in os.listdir(diretorio_insights)
                    if f.endswith('.md') and f != 'consolidado_insights.md']

    if not arquivos:
        print("No insight files found.")
        return []

    # Filter insights that need pills (check by title from content)
    arquivos_pendentes = []
    for arquivo in arquivos:
        try:
            if config.save_on_minio:
                conteudo = carregar_insight_bucket(arquivo)
            else:
                caminho = os.path.join(diretorio_insights, arquivo)
                with open(caminho, 'r', encoding='utf-8') as f:
                    conteudo = f.read()

            titulo = extrair_titulo_do_markdown(conteudo)
            if titulo:
                pilula_esperada = f"pilula_{slugify(titulo)}.json"
            else:
                nome_base = arquivo.replace('.md', '')
                pilula_esperada = f"pilula_{slugify(nome_base)}.json"

            if pilula_esperada in pilulas_existentes:
                print(f">> Skipping {arquivo} - pill already exists ({pilula_esperada})")
            else:
                arquivos_pendentes.append(arquivo)
        except Exception as e:
            print(f"!! Could not check {arquivo}: {e}")
            arquivos_pendentes.append(arquivo)

    if not arquivos_pendentes:
        print("\nAll pills have already been generated. Nothing to do.")
        return []

    # Apply limit if configured
    total_pendentes = len(arquivos_pendentes)
    if config.max_pills_per_run > 0 and total_pendentes > config.max_pills_per_run:
        print(f"\nLimiting to {config.max_pills_per_run} pills this run (of {total_pendentes} pending).")
        arquivos_pendentes = arquivos_pendentes[:config.max_pills_per_run]

    print(f"\nGenerating pills for {len(arquivos_pendentes)} insights with {config.max_workers} workers...\n")

    resultados: List[PillResult] = []
    pilulas_geradas: List[str] = []

    # Process insights in parallel
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        futures = {
            executor.submit(
                processar_insight_para_pilula,
                arquivo,
                diretorio_insights,
                contexto_consolidado
            ): arquivo
            for arquivo in arquivos_pendentes
        }

        for future in as_completed(futures):
            arquivo = futures[future]
            try:
                resultado = future.result()
                resultados.append(resultado)
                status = "OK" if resultado.success else f"ERROR: {resultado.error}"
                print(f"[{len(resultados)}/{len(arquivos_pendentes)}] {arquivo} -> {status}")
            except Exception as e:
                print(f"[{len(resultados)}/{len(arquivos_pendentes)}] {arquivo} -> ERROR: {e}")

    # Save results
    print(f"\nSaving {len(resultados)} pills...")

    for resultado in resultados:
        if salvar_pilula(resultado, diretorio_pilulas):
            pilulas_geradas.append(f"{resultado.pill_id}.json")

    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total insights: {len(arquivos)}")
    print(f"Already existing: {len(pilulas_existentes)}")
    print(f"Processed this run: {len(resultados)}")
    print(f"Successfully saved: {len(pilulas_geradas)}")
    print(f"Errors: {len(resultados) - len(pilulas_geradas)}")

    return pilulas_geradas
