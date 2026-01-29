from src.utils.storage import carregar_sites_fontes
from src.scraper.processor import processar_urls_paralelo, consolidar_insights


def main():
    """Main entry point for the scraper."""
    print("Iniciando processamento de conteudo educativo...\n")

    # Load source URLs
    sites_fontes = carregar_sites_fontes()

    if not sites_fontes:
        print("Nenhuma URL encontrada em sites_fontes.txt")
        return

    # Process URLs in parallel
    arquivos_gerados, resultados = processar_urls_paralelo(sites_fontes)

    # Summary
    print(f"\nTotal de topicos gerados: {len(arquivos_gerados)}")
    print("Os arquivos foram salvos com nomes semanticos baseados em seu conteudo.")

    # Consolidate all insights into a single file
    if resultados:
        consolidar_insights(resultados)


if __name__ == "__main__":
    main()
