from src.video.generator import gerar_roteiros, processar_e_subir_videos


def main():
    """Main entry point for video script generation."""
    print("Iniciando geracao de roteiros...\n")

    # Generate video scripts
    roteiros_gerados = gerar_roteiros()

    print(f"\nRoteiros gerados com sucesso: {len(roteiros_gerados)}")

    # Video upload placeholder (Nano Banana integration)
    print("\nProcessando e subindo videos...\n")
    processar_e_subir_videos()


if __name__ == "__main__":
    main()
