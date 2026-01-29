import requests
from bs4 import BeautifulSoup


def extrair_texto_site(url: str, timeout: int = 10) -> str:
    """
    Extracts main text content from a URL, ignoring navigation elements.

    Removes scripts, styles, navigation, footer, and header elements
    to extract only the main content.

    Args:
        url: The URL to extract text from
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Extracted text content, or error message if extraction fails
    """
    try:
        response = requests.get(url, timeout=timeout)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove irrelevant elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"Erro ao acessar {url}: {e}"
