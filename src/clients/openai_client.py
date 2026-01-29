from functools import lru_cache

from openai import OpenAI

from ..config import get_config


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """
    Returns a singleton OpenAI client.

    Uses lru_cache to ensure the client is created only once.
    Supports custom base URL via OPENAI_HOST for compatible APIs.

    Returns:
        OpenAI client instance
    """
    config = get_config()
    return OpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_host,
    )


def gerar_conteudo_openai(prompt: str) -> str:
    """
    Generates content using OpenAI API.

    Args:
        prompt: The prompt to send to the model

    Returns:
        Generated text response
    """
    config = get_config()
    client = get_openai_client()

    response = client.chat.completions.create(
        model=config.openai_model_name,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    return response.choices[0].message.content
