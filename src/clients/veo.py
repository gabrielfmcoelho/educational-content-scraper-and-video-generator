import time
from typing import Optional

import google.genai as genai
from google.genai.types import GenerateVideoConfig

from ..config import get_config


def gerar_video_veo(
    roteiro: str,
    titulo: str,
    timeout: int = 600
) -> Optional[bytes]:
    """
    Generates a video using Google Veo API based on a script.

    Args:
        roteiro: Video script in markdown format
        titulo: Video title
        timeout: Maximum time to wait for video generation (seconds)

    Returns:
        Video bytes if successful, None otherwise
    """
    config = get_config()
    
    if not config.veo_api_key:
        print("ERRO: VEO_API_KEY não configurada")
        return None

    try:
        print(f"Enviando roteiro para Google Veo: {titulo}")
        
        # Initialize Veo client
        client = genai.Client(api_key=config.veo_api_key)
        
        # Create a prompt from the script
        prompt = f"{titulo}\n\n{roteiro[:1000]}"  # Limit to 1000 chars for video generation
        
        # Configure video generation
        video_config = GenerateVideoConfig(
            model=config.veo_model_name,
            prompt=prompt,
            aspect_ratio="16:9",
            duration=30,  # 30-second video
        )
        
        # Generate video
        print(f"Gerando vídeo com Veo (isso pode levar alguns minutos)...")
        response = client.models.generate_video(config=video_config)
        
        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            if response.is_complete:
                if response.video:
                    video_bytes = response.video.data
                    print(f"Vídeo gerado com sucesso: {len(video_bytes)} bytes")
                    return video_bytes
                else:
                    print("Erro: Vídeo não disponível na resposta")
                    return None
            
            if response.is_failed:
                print(f"Geração de vídeo falhou: {response.error}")
                return None
            
            print(f"Status: processando... ({int(time.time() - start_time)}s)")
            time.sleep(10)
            response.refresh()  # Update response status

        print(f"Timeout: Vídeo não gerado após {timeout} segundos")
        return None

    except Exception as e:
        print(f"Erro ao gerar vídeo com Veo: {e}")
        return None


def testar_conexao_veo() -> bool:
    """
    Tests the connection to Google Veo API.

    Returns:
        True if connection is successful, False otherwise
    """
    config = get_config()
    
    if not config.veo_api_key:
        print("VEO_API_KEY não configurada")
        return False

    try:
        client = genai.Client(api_key=config.veo_api_key)
        # Try to list models to verify connection
        models = client.models.list()
        print("Conexão com Google Veo API: OK")
        return True
            
    except Exception as e:
        print(f"Erro ao conectar com Google Veo API: {e}")
        return False
