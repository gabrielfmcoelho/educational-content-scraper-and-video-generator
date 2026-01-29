import os
from typing import List


def carregar_sites_fontes(arquivo: str = 'data/sites_fontes.txt') -> List[str]:
    """
    Loads URL list from a text file.

    Args:
        arquivo: Path to the file containing URLs (one per line)

    Returns:
        List of URLs, or empty list if file not found
    """
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            sites = [url.strip() for url in f.readlines() if url.strip()]
        return sites
    except FileNotFoundError:
        print(f"Arquivo '{arquivo}' nao encontrado!")
        return []


def garantir_diretorio(diretorio: str) -> None:
    """
    Creates a directory if it doesn't exist.

    Args:
        diretorio: Path to the directory to create
    """
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)


def salvar_arquivo_local(caminho: str, conteudo: str) -> None:
    """
    Saves content to a local file.

    Args:
        caminho: Full path to the file
        conteudo: Content to write to the file
    """
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
