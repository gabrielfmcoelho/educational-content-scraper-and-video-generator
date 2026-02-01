import os
import tempfile
import time
import uuid
from typing import Optional, List, Tuple, Dict, Any

from google import genai
from google.genai.types import GenerateVideosConfig

from ..config import get_config
from ..prompts import parse_scenes_from_roteiro


def _check_config(config) -> Tuple[bool, str]:
    """
    Validate VEO configuration based on selected mode.

    Args:
        config: Application configuration

    Returns:
        Tuple of (success, message)
    """
    if config.use_vertex_ai:
        if not config.vertex_project:
            return False, "VERTEX_PROJECT não configurado"
        if not config.vertex_gcs_bucket:
            return False, "VERTEX_GCS_BUCKET não configurado"
        return True, f"Projeto: {config.vertex_project}, Bucket: {config.vertex_gcs_bucket}"
    else:
        if not config.veo_api_key:
            return False, "VEO_API_KEY não configurado"
        return True, "API key configurada"


def _check_gcs_bucket(bucket_uri: str) -> Tuple[bool, str]:
    """
    Validate GCS bucket exists and is writable. Creates bucket if it doesn't exist.

    Args:
        bucket_uri: GCS URI in format gs://bucket/path

    Returns:
        Tuple of (success, message)
    """
    try:
        from google.cloud import storage
        from google.cloud.exceptions import NotFound, Forbidden, Conflict
    except ImportError:
        return False, "google-cloud-storage não instalado (pip install google-cloud-storage)"

    try:
        # Parse gs://bucket/path format
        uri = bucket_uri.replace("gs://", "")
        bucket_name = uri.split("/")[0]

        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Check if bucket exists, create if not
        bucket_created = False
        try:
            if not bucket.exists():
                # Try to create the bucket
                config = get_config()
                location = config.vertex_location if config.vertex_location else "us-central1"
                bucket = client.create_bucket(bucket_name, location=location)
                bucket_created = True
        except Conflict:
            # Bucket already exists (race condition or owned by someone else)
            pass
        except Forbidden:
            # Can't check existence or create - will try write test anyway
            pass

        # Check write permission with test file
        test_blob = bucket.blob("_veo_validation_test.txt")
        test_blob.upload_from_string("validation test")
        test_blob.delete()

        if bucket_created:
            return True, f"Bucket '{bucket_name}' criado e validado (leitura/escrita)"
        return True, f"Bucket '{bucket_name}' OK (leitura/escrita)"

    except Forbidden as e:
        # GCS returns 403 for both permission denied AND non-existent buckets
        return False, f"Sem permissão para criar/acessar bucket. Verifique IAM roles: Storage Admin ou Storage Object Admin"
    except Exception as e:
        error_str = str(e).lower()
        if 'credentials' in error_str or 'authentication' in error_str:
            return False, "Credenciais GCP não configuradas. Execute: gcloud auth application-default login"
        if 'does not have' in error_str and 'access' in error_str:
            return False, "Sem permissão para criar/acessar bucket. Verifique IAM roles: Storage Admin ou Storage Object Admin"
        return False, f"Erro GCS: {e}"


def _check_vertex_api(client, config) -> Tuple[bool, str]:
    """
    Check if Vertex AI API is accessible and billing is enabled.

    Args:
        client: The genai client
        config: Application configuration

    Returns:
        Tuple of (success, message)
    """
    try:
        # Try to list models - this validates credentials and project access
        models = list(client.models.list())
        # Check if our target model is available
        model_names = [m.name for m in models if hasattr(m, 'name')]
        if config.veo_model_name in str(model_names):
            return True, f"Modelo '{config.veo_model_name}' disponível"
        return True, f"API acessível ({len(models)} modelos encontrados)"

    except Exception as e:
        error_str = str(e).lower()
        if 'billing' in error_str:
            return False, "Billing desabilitado no projeto GCP. Ative em: https://console.cloud.google.com/billing"
        if 'permission' in error_str or 'forbidden' in error_str:
            return False, "Sem permissão. Verifique IAM role: Vertex AI User (roles/aiplatform.user)"
        if 'not found' in error_str:
            return False, f"Projeto '{config.vertex_project}' não encontrado ou API não habilitada"
        if 'credentials' in error_str or 'authentication' in error_str:
            return False, "Credenciais GCP não configuradas. Execute: gcloud auth application-default login"
        return False, f"Erro API: {e}"


def _check_ai_studio_api(client, config) -> Tuple[bool, str]:
    """
    Check if AI Studio API is accessible.

    Args:
        client: The genai client
        config: Application configuration

    Returns:
        Tuple of (success, message)
    """
    try:
        # Try to list models to verify API key
        models = list(client.models.list())
        return True, f"API acessível ({len(models)} modelos encontrados)"
    except Exception as e:
        error_str = str(e).lower()
        if 'api key' in error_str or 'invalid' in error_str:
            return False, "API key inválida. Verifique VEO_API_KEY"
        if 'quota' in error_str:
            return False, "Quota excedida. Aguarde ou verifique limites em: https://aistudio.google.com"
        return False, f"Erro API: {e}"


def validar_configuracao_veo() -> Dict[str, Any]:
    """
    Comprehensive VEO configuration validation.

    Performs all pre-flight checks to ensure VEO video generation will work
    before attempting any expensive API calls.

    Returns:
        dict with:
        - 'valid': bool - True if all checks passed
        - 'mode': str - 'Vertex AI' or 'AI Studio'
        - 'checks': list of dicts with 'name', 'ok', 'message'
    """
    config = get_config()
    results = {
        'valid': True,
        'mode': 'Vertex AI' if config.use_vertex_ai else 'AI Studio',
        'checks': []
    }

    # Check 1: Configuration
    ok, msg = _check_config(config)
    results['checks'].append({
        'name': 'Configuração',
        'ok': ok,
        'message': msg
    })
    if not ok:
        results['valid'] = False
        return results  # Can't continue without basic config

    # Check 2: Client connection
    try:
        client = _get_veo_client()
        results['checks'].append({
            'name': 'Cliente VEO',
            'ok': True,
            'message': 'Cliente criado com sucesso'
        })
    except Exception as e:
        results['checks'].append({
            'name': 'Cliente VEO',
            'ok': False,
            'message': str(e)
        })
        results['valid'] = False
        return results  # Can't continue without client

    # Check 3: API access (and billing for Vertex AI)
    if config.use_vertex_ai:
        ok, msg = _check_vertex_api(client, config)
    else:
        ok, msg = _check_ai_studio_api(client, config)

    results['checks'].append({
        'name': 'Acesso API',
        'ok': ok,
        'message': msg
    })
    if not ok:
        results['valid'] = False

    # Check 4: GCS bucket access (Vertex AI only)
    if config.use_vertex_ai:
        ok, msg = _check_gcs_bucket(config.vertex_gcs_bucket)
        results['checks'].append({
            'name': 'Bucket GCS',
            'ok': ok,
            'message': msg
        })
        if not ok:
            results['valid'] = False

    return results


def imprimir_resultado_validacao(result: Dict[str, Any]) -> None:
    """
    Print validation result in a human-readable format.

    Args:
        result: Result from validar_configuracao_veo()
    """
    status = "✓" if result['valid'] else "✗"
    print(f"\n{status} Validação VEO ({result['mode']})")
    print("-" * 40)

    for check in result['checks']:
        icon = "✓" if check['ok'] else "✗"
        print(f"  {icon} {check['name']}: {check['message']}")

    print("-" * 40)
    if result['valid']:
        print("Pronto para gerar vídeos!\n")
    else:
        print("Corrija os erros acima antes de continuar.\n")


def _download_from_gcs(gcs_uri: str) -> bytes:
    """
    Download file from Google Cloud Storage.

    Args:
        gcs_uri: GCS URI in format gs://bucket/path/to/file

    Returns:
        File contents as bytes
    """
    from google.cloud import storage

    # Parse gs://bucket/path format
    uri_without_prefix = gcs_uri.replace("gs://", "")
    parts = uri_without_prefix.split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else ""

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()


def _download_video_bytes(client, video, config) -> Optional[bytes]:
    """
    Download video bytes - different methods for AI Studio vs Vertex AI.

    Args:
        client: The genai client
        video: GeneratedVideo object from VEO API
        config: Application config

    Returns:
        Video bytes if successful, None otherwise
    """
    if config.use_vertex_ai:
        # Vertex AI: video was written to GCS, download from there
        if hasattr(video, 'video') and hasattr(video.video, 'uri') and video.video.uri:
            print(f"Baixando do GCS: {video.video.uri}")
            return _download_from_gcs(video.video.uri)
        else:
            print("ERRO: Vídeo Vertex AI não tem URI do GCS")
            return None
    else:
        # AI Studio: use SDK download method
        client.files.download(file=video.video)

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp_path = tmp.name

        video.video.save(tmp_path)

        with open(tmp_path, 'rb') as f:
            video_bytes = f.read()

        os.unlink(tmp_path)
        return video_bytes


def _get_veo_client():
    """
    Creates and returns a VEO client based on configuration.

    Supports two authentication methods:
    - AI Studio: Uses VEO_API_KEY
    - Vertex AI: Uses GCP project credentials (requires ADC setup)

    Returns:
        genai.Client configured for VEO API access

    Raises:
        ValueError: If required configuration is missing
    """
    config = get_config()

    if config.use_vertex_ai:
        # Vertex AI authentication (uses Application Default Credentials)
        if not config.vertex_project:
            raise ValueError("VERTEX_PROJECT not configured for Vertex AI mode")
        return genai.Client(
            vertexai=True,
            project=config.vertex_project,
            location=config.vertex_location
        )
    else:
        # AI Studio authentication (uses API key)
        if not config.veo_api_key:
            raise ValueError("VEO_API_KEY not configured")
        return genai.Client(api_key=config.veo_api_key)


def _poll_operation(client, operation):
    """Poll operation until done."""
    while not operation.done:
        print("Aguardando geração do vídeo...")
        time.sleep(10)
        operation = client.operations.get(operation)

    # Check for errors
    if hasattr(operation, 'error') and operation.error:
        print(f"ERRO na operação: {operation.error}")
        return None

    if operation.response is None:
        print("ERRO: operation.response é None")
        return None

    if not hasattr(operation.response, 'generated_videos') or not operation.response.generated_videos:
        print(f"ERRO: Nenhum vídeo gerado. Response: {operation.response}")
        return None

    return operation


def gerar_video_veo(
    roteiro: str,
    titulo: str,
    extensions: Optional[int] = None,
    scenes: Optional[List[str]] = None
) -> Optional[bytes]:
    """
    Generates a video using Google VEO API with scene-based extensions.

    Args:
        roteiro: Full video script in markdown format
        titulo: Video title
        extensions: Number of extensions (each ~8s). Uses config if None.
        scenes: Pre-parsed scene prompts. If None, parses from roteiro.

    Returns:
        Video bytes if successful, None otherwise
    """
    config = get_config()

    try:
        client = _get_veo_client()
    except ValueError as e:
        print(f"ERRO: {e}")
        return None

    extensions = extensions if extensions is not None else config.veo_extensions

    # Vertex AI does not support video extensions - only AI Studio does
    if config.use_vertex_ai and extensions > 0:
        print("⚠ AVISO: Vertex AI não suporta extensões de vídeo. Gerando apenas vídeo inicial (~8s).")
        print("  Para vídeos mais longos, use AI Studio (VEO_USE_VERTEX_AI=false)")
        extensions = 0

    # Vertex AI requires GCS bucket for video output
    if config.use_vertex_ai and not config.vertex_gcs_bucket:
        print("ERRO: VERTEX_GCS_BUCKET não configurado para modo Vertex AI")
        print("  Configure: VERTEX_GCS_BUCKET=gs://seu-bucket/pasta-de-saida")
        return None

    # Parse scenes from roteiro if not provided
    if scenes is None:
        scenes = parse_scenes_from_roteiro(roteiro)
        print(f"Cenas extraídas do roteiro: {len(scenes)}")

    # Use first scene for initial video, rest for extensions
    initial_prompt = scenes[0] if scenes else f"{titulo}: {roteiro[:1000]}"
    extension_prompts = scenes[1:] if len(scenes) > 1 else []

    # Adjust extensions to match available scenes
    actual_extensions = min(extensions, len(extension_prompts)) if extension_prompts else extensions

    print(f"Configuração: {actual_extensions} extensões")

    try:
        # 1. Initial Generation with Scene 1
        print(f"Gerando vídeo inicial (Cena 1)...")
        print(f"  Prompt: {initial_prompt[:100]}...")

        # Build config - add GCS output for Vertex AI
        video_config = GenerateVideosConfig(
            aspect_ratio="16:9",
            resolution="720p"
        )

        # For Vertex AI, add output_gcs_uri to write video to GCS
        if config.use_vertex_ai:
            # Generate unique filename to avoid conflicts
            video_id = str(uuid.uuid4())[:8]
            gcs_output_uri = f"{config.vertex_gcs_bucket.rstrip('/')}/video_{video_id}.mp4"
            video_config = GenerateVideosConfig(
                aspect_ratio="16:9",
                resolution="720p",
                output_gcs_uri=gcs_output_uri
            )
            print(f"  Output GCS: {gcs_output_uri}")

        operation = client.models.generate_videos(
            model=config.veo_model_name,
            prompt=initial_prompt,
            config=video_config
        )
        operation = _poll_operation(client, operation)

        if operation is None:
            print("Falha ao gerar vídeo inicial")
            return None

        current_video = operation.response.generated_videos[0]
        print("Cena 1 gerada (~8s)")

        # 2. Sequential Extension Loop with scene-specific prompts
        # Use video= (not source=) to allow prompt for each extension
        for i in range(actual_extensions):
            # Get scene prompt for this extension
            if i < len(extension_prompts):
                scene_prompt = extension_prompts[i]
            else:
                scene_prompt = f"Continuação de: {titulo}"

            print(f"Estendendo vídeo (Cena {i+2}/{actual_extensions+1})...")
            print(f"  Prompt: {scene_prompt[:100]}...")

            # Must download/process the video before using for extension
            client.files.download(file=current_video.video)

            # Use video= with .video property (not source=) to allow prompt
            operation = client.models.generate_videos(
                model=config.veo_model_name,
                video=current_video.video,  # Use .video property
                prompt=scene_prompt,
                config=GenerateVideosConfig(
                    number_of_videos=1,
                    resolution="720p"
                )
            )
            operation = _poll_operation(client, operation)

            if operation is None:
                print(f"ERRO: Cena {i+2} falhou")
                break

            current_video = operation.response.generated_videos[0]
            print(f"Cena {i+2} concluída")

        # 3. Download the Final Video
        total_duration = (actual_extensions + 1) * 8
        print(f"Baixando vídeo final (~{total_duration}s)...")

        video_bytes = _download_video_bytes(client, current_video, config)

        if video_bytes:
            print(f"Download concluído: {len(video_bytes)} bytes")
        else:
            print("ERRO: Falha no download do vídeo")

        return video_bytes

    except Exception as e:
        print(f"Erro: {e}")
        return None


def testar_conexao_veo() -> bool:
    """
    Tests the connection to Google Veo API with comprehensive validation.

    Performs all pre-flight checks including:
    - Configuration validation
    - API access and billing status
    - GCS bucket access (Vertex AI only)

    Returns:
        True if all checks pass, False otherwise
    """
    result = validar_configuracao_veo()
    imprimir_resultado_validacao(result)
    return result['valid']
