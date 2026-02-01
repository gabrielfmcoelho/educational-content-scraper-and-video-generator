import sys

from src.config import get_config
from src.clients.veo import validar_configuracao_veo, imprimir_resultado_validacao
from src.video.generator import gerar_roteiros, processar_e_subir_videos


def main():
    """Main entry point for video script generation."""
    config = get_config()

    # Pre-flight validation for VEO
    print("Validando configuração VEO...")
    result = validar_configuracao_veo()
    imprimir_resultado_validacao(result)

    if not result['valid']:
        print("Abortando: corrija os erros de configuração acima.")
        sys.exit(1)

    if config.skip_roteiro_generation:
        print("SKIP_ROTEIRO_GENERATION=true - Pulando geracao de roteiros...\n")
        print("Usando roteiros existentes no MinIO/local.\n")
    else:
        print("Iniciando geracao de roteiros...\n")

        # Generate video scripts
        roteiros_gerados = gerar_roteiros()

        print(f"\nRoteiros gerados com sucesso: {len(roteiros_gerados)}")

    # Video generation with Veo
    print("\nProcessando e subindo videos...\n")
    processar_e_subir_videos()


if __name__ == "__main__":
    main()
