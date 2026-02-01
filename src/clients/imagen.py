"""Google Imagen (Vertex AI) client for infographic image generation."""

import os
import time
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache

from google import genai
from google.genai.types import GenerateImagesConfig

from ..config import get_config


def _check_config(config) -> Tuple[bool, str]:
    """
    Validate Imagen configuration.

    Args:
        config: Application configuration

    Returns:
        Tuple of (success, message)
    """
    # Imagen is only available through Vertex AI (not AI Studio)
    if not config.vertex_project:
        return False, "VERTEX_PROJECT not configured"
    return True, f"Project: {config.vertex_project}, Location: {config.vertex_location}"


def _check_vertex_api(client) -> Tuple[bool, str]:
    """
    Check if Vertex AI API is accessible for Imagen.

    Args:
        client: The genai client

    Returns:
        Tuple of (success, message)
    """
    try:
        # Try to list models to verify access
        models = list(client.models.list())
        return True, f"API accessible ({len(models)} models found)"
    except Exception as e:
        error_str = str(e).lower()
        if 'billing' in error_str:
            return False, "Billing disabled. Enable at: https://console.cloud.google.com/billing"
        if 'permission' in error_str or 'forbidden' in error_str:
            return False, "Permission denied. Check IAM role: Vertex AI User (roles/aiplatform.user)"
        if 'not found' in error_str:
            return False, f"Project not found or API not enabled"
        if 'credentials' in error_str or 'authentication' in error_str:
            return False, "GCP credentials not configured. Run: gcloud auth application-default login"
        return False, f"API Error: {e}"


def validar_configuracao_imagen() -> Dict[str, Any]:
    """
    Comprehensive Imagen configuration validation.

    Performs all pre-flight checks to ensure Imagen image generation will work
    before attempting any API calls.

    Returns:
        dict with:
        - 'valid': bool - True if all checks passed
        - 'mode': str - Always 'Vertex AI' for Imagen
        - 'checks': list of dicts with 'name', 'ok', 'message'
    """
    config = get_config()
    results = {
        'valid': True,
        'mode': 'Vertex AI (Imagen)',
        'checks': []
    }

    # Check 1: Configuration
    ok, msg = _check_config(config)
    results['checks'].append({
        'name': 'Configuration',
        'ok': ok,
        'message': msg
    })
    if not ok:
        results['valid'] = False
        return results

    # Check 2: Client connection
    try:
        client = _get_imagen_client()
        results['checks'].append({
            'name': 'Imagen Client',
            'ok': True,
            'message': 'Client created successfully'
        })
    except Exception as e:
        results['checks'].append({
            'name': 'Imagen Client',
            'ok': False,
            'message': str(e)
        })
        results['valid'] = False
        return results

    # Check 3: API access
    ok, msg = _check_vertex_api(client)
    results['checks'].append({
        'name': 'API Access',
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
        result: Result from validar_configuracao_imagen()
    """
    status = "+" if result['valid'] else "x"
    print(f"\n{status} Imagen Validation ({result['mode']})")
    print("-" * 40)

    for check in result['checks']:
        icon = "+" if check['ok'] else "x"
        print(f"  {icon} {check['name']}: {check['message']}")

    print("-" * 40)
    if result['valid']:
        print("Ready to generate images!\n")
    else:
        print("Fix the errors above before continuing.\n")


@lru_cache(maxsize=1)
def _get_imagen_client():
    """
    Creates and returns an Imagen client using Vertex AI.

    Imagen is only available through Vertex AI (requires GCP project).

    Returns:
        genai.Client configured for Imagen API access

    Raises:
        ValueError: If required configuration is missing
    """
    config = get_config()

    if not config.vertex_project:
        raise ValueError("VERTEX_PROJECT not configured - Imagen requires Vertex AI")

    return genai.Client(
        vertexai=True,
        project=config.vertex_project,
        location=config.vertex_location
    )


def gerar_infografico(
    prompt: str,
    aspect_ratio: str = "1:1",
    style: str = "flat_design"
) -> Optional[bytes]:
    """
    Generates an infographic image using Google Imagen API.

    Args:
        prompt: The image generation prompt with accessibility requirements
        aspect_ratio: Image aspect ratio ("1:1", "16:9", "9:16", "4:3", "3:4")
        style: Visual style hint for the image

    Returns:
        Image bytes if successful, None otherwise
    """
    config = get_config()

    try:
        client = _get_imagen_client()
    except ValueError as e:
        print(f"ERROR: {e}")
        return None

    try:
        print(f"Generating infographic...")
        print(f"  Prompt: {prompt[:100]}...")
        print(f"  Aspect ratio: {aspect_ratio}")

        # Use imagen-3.0-generate-002 model (latest Imagen model)
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_medium_and_above",
                person_generation="dont_allow",  # Safer for educational content
            )
        )

        if not response.generated_images:
            print("ERROR: No images generated")
            return None

        # Get the first generated image
        image = response.generated_images[0]

        # Extract image bytes
        if hasattr(image, 'image') and hasattr(image.image, 'image_bytes'):
            image_bytes = image.image.image_bytes
            print(f"Image generated: {len(image_bytes)} bytes")
            return image_bytes
        elif hasattr(image, 'image_bytes'):
            image_bytes = image.image_bytes
            print(f"Image generated: {len(image_bytes)} bytes")
            return image_bytes
        else:
            print(f"ERROR: Could not extract image bytes from response")
            print(f"  Response structure: {type(image)}")
            return None

    except Exception as e:
        print(f"Error generating image: {e}")
        return None


def gerar_infografico_acessivel(
    topic: str,
    short_text: str,
    target_audience: str = "elderly,neurodivergent"
) -> Optional[bytes]:
    """
    Generates an accessibility-focused infographic for knowledge pills.

    This function builds the complete prompt with accessibility requirements
    for elderly and neurodivergent audiences.

    Args:
        topic: The main topic of the infographic
        short_text: The short educational text to visualize
        target_audience: Comma-separated target audiences

    Returns:
        Image bytes if successful, None otherwise
    """
    # Build accessibility-focused prompt
    prompt = f"""Create an educational infographic about: {topic}

Key message: {short_text[:500]}

Style requirements for accessibility:
- Simple, literal illustrations (no abstract metaphors)
- Large, clear icons and symbols (minimum 3 main visual elements)
- High contrast: dark text (#333) on light background (#FFF or #F5F5DC)
- Soft, calming color palette: blues (#4A90D9), greens (#7CB342), warm yellows (#FFD54F)
- NO text in the image - the text will be added separately
- Clean, uncluttered layout with generous whitespace
- Flat design style, no gradients or complex shadows
- Suitable for elderly (idosos) and neurodivergent (autistas) audiences
- Use realistic representations, not cartoons
- Include visual metaphors that are immediately understandable"""

    return gerar_infografico(
        prompt=prompt,
        aspect_ratio="1:1",  # Square works best for pills
        style="flat_design"
    )


def testar_conexao_imagen() -> bool:
    """
    Tests the connection to Google Imagen API with comprehensive validation.

    Returns:
        True if all checks pass, False otherwise
    """
    result = validar_configuracao_imagen()
    imprimir_resultado_validacao(result)
    return result['valid']
