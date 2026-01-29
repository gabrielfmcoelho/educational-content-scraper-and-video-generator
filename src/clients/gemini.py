from functools import lru_cache

import google.genai as genai

from ..config import get_config


@lru_cache(maxsize=1)
def get_gemini_client():
    """
    Returns a singleton Gemini client.

    Uses lru_cache to ensure the client is created only once.

    Returns:
        Gemini client instance
    """
    config = get_config()
    return genai.Client(api_key=config.gemini_api_key)


def gerar_conteudo_gemini(prompt: str) -> str:
    """
    Generates content using Gemini AI.

    Args:
        prompt: The prompt to send to Gemini

    Returns:
        Generated text response
    """
    config = get_config()
    client = get_gemini_client()
    response = client.models.generate_content(
        model=config.gemini_model_name,
        contents=prompt
    )
    return response.text


def gerar_conteudo(prompt: str) -> str:
    """
    Generates content using the configured AI provider.

    Automatically selects between Gemini and OpenAI based on
    the AI_PROVIDER environment variable.

    Args:
        prompt: The prompt to send to the AI

    Returns:
        Generated text response
    """
    config = get_config()

    if config.ai_provider.lower() == 'openai':
        from .openai_client import gerar_conteudo_openai
        return gerar_conteudo_openai(prompt)
    else:
        return gerar_conteudo_gemini(prompt)
