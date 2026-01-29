import re
from typing import Optional


def slugify(texto: str) -> str:
    """
    Converts text to a URL-safe slug format.

    Example: 'Proteção contra Golpes' -> 'protecao_contra_golpes'

    Args:
        texto: Text to convert to slug

    Returns:
        Lowercase underscore-separated slug
    """
    # Remove accents and special characters
    slug = re.sub(r'[^\w\s-]', '', texto)
    # Replace spaces and hyphens with underscore
    slug = re.sub(r'[\s-]+', '_', slug)
    # Convert to lowercase and strip underscores
    slug = slug.lower().strip('_')
    return slug


def extrair_titulo_do_markdown(conteudo_md: str) -> Optional[str]:
    """
    Extracts the first H1 title from markdown content.

    Args:
        conteudo_md: Markdown content string

    Returns:
        The title text without the # prefix, or None if not found
    """
    match = re.search(r'^# (.+)$', conteudo_md, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def gerar_nome_arquivo(titulo: Optional[str], prefixo: str, indice: int, extensao: str = '.md') -> str:
    """
    Generates a semantic file name based on title or falls back to index.

    Args:
        titulo: Optional title to use for the file name
        prefixo: Prefix for the file name (e.g., 'topico', 'roteiro')
        indice: Fallback index if title is not available
        extensao: File extension (default: '.md')

    Returns:
        Generated file name with the format: prefixo_slug.extensao
    """
    if titulo:
        slug = slugify(titulo)
        return f"{prefixo}_{slug}{extensao}"
    return f"{prefixo}_{indice}{extensao}"
