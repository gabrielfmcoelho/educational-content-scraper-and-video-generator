#!/usr/bin/env python3
"""
Knowledge Pills (Pilulas de Conhecimento) Generator

Generates accessibility-focused educational pills from insights:
- Short text (2-4 sentences, simple language)
- Infographic (AI-generated via Imagen/Vertex AI)
- Call to Action (question or challenge)

Target audiences:
- Elderly (idosos)
- Neurodivergent (autistas)

Usage:
    python pillGenerator.py

Environment variables:
    SKIP_PILL_GENERATION: Set to 'true' to skip pill text generation
    MAX_PILLS_PER_RUN: Limit number of pills generated (0 = unlimited)
    MINIO_BUCKET_PILULAS: MinIO bucket for pill JSON data
    MINIO_BUCKET_INFOGRAFICOS: MinIO bucket for infographic images
"""

import sys

from src.config import get_config
from src.clients.imagen import validar_configuracao_imagen, imprimir_resultado_validacao
from src.pill.generator import gerar_pilulas


def main():
    """Main entry point for knowledge pill generation."""
    config = get_config()

    print("=" * 50)
    print("KNOWLEDGE PILLS GENERATOR")
    print("Pilulas de Conhecimento - Educacao Digital")
    print("=" * 50)
    print()

    # Pre-flight validation for Imagen
    print("Validating Imagen configuration...")
    result = validar_configuracao_imagen()
    imprimir_resultado_validacao(result)

    if not result['valid']:
        print("WARNING: Imagen configuration is invalid.")
        print("Pills will be generated WITHOUT infographics.")
        print("To enable infographics, configure Vertex AI:")
        print("  - VERTEX_PROJECT=your-gcp-project")
        print("  - VERTEX_LOCATION=us-central1")
        print("  - Run: gcloud auth application-default login")
        print()

        # Ask user if they want to continue
        response = input("Continue without infographics? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(1)

    if config.skip_pill_generation:
        print("SKIP_PILL_GENERATION=true - Skipping pill generation...\n")
        print("Use existing pills in MinIO/local.\n")
        return

    print("Starting pill generation...\n")

    # Generate knowledge pills
    pilulas_geradas = gerar_pilulas()

    print(f"\nPills generated successfully: {len(pilulas_geradas)}")

    if pilulas_geradas:
        print("\nGenerated pills:")
        for pilula in pilulas_geradas:
            print(f"  - {pilula}")


if __name__ == "__main__":
    main()
