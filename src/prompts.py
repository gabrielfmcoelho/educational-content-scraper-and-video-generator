import re
from typing import List

# Content limits for prompts
INSIGHT_CONTENT_LIMIT = 15000
VIDEO_CONTENT_LIMIT = 5000
CONSOLIDATION_CONTENT_LIMIT = 50000


def parse_scenes_from_roteiro(roteiro: str) -> List[str]:
    """
    Parses a roteiro and extracts individual scene descriptions for video generation.

    Args:
        roteiro: Full roteiro text in markdown format

    Returns:
        List of scene prompts ready for VEO video generation
    """
    scenes = []

    # Pattern to match scene sections: ## CENA N or ## Cenário N
    scene_pattern = r'##\s*(?:CENA|Cenário|Cena)\s*(\d+)[^\n]*\n(.*?)(?=##\s*(?:CENA|Cenário|Cena|INFORMAÇÕES)|$)'
    matches = re.findall(scene_pattern, roteiro, re.DOTALL | re.IGNORECASE)

    for scene_num, scene_content in matches:
        # Extract visual description
        visual_match = re.search(r'\*?\*?(?:VISUAL|Descrição visual)[:\*]*\s*(.+?)(?=\*?\*?(?:AUDIO|ÁUDIO|Locução|TRANSIÇÃO)|$)',
                                  scene_content, re.DOTALL | re.IGNORECASE)

        if visual_match:
            visual_desc = visual_match.group(1).strip()
            # Clean up markdown formatting
            visual_desc = re.sub(r'\[|\]', '', visual_desc)
            visual_desc = re.sub(r'\*+', '', visual_desc)
            visual_desc = visual_desc.strip()

            if visual_desc:
                # Create a prompt suitable for VEO
                scene_prompt = f"Cena {scene_num}: {visual_desc}"
                scenes.append(scene_prompt)

    # Fallback: if no scenes parsed, split roteiro into chunks
    if not scenes:
        # Simple fallback - use the whole roteiro
        scenes = [roteiro[:1000]]

    return scenes


def get_insight_prompt(url: str, conteudo_bruto: str) -> str:
    """
    Returns the prompt for generating educational insights from scraped content.

    Args:
        url: The source URL of the content
        conteudo_bruto: Raw text extracted from the website

    Returns:
        Formatted prompt string for Gemini
    """
    return f"""
    Você é um especialista em educação digital para idosos.
    Analise o texto abaixo extraído do site {url}.

    Crie um arquivo Markdown (.md) contendo:
    1. Título.
    2. Principais tópicos.
    3. Principais insights.
    4. Sinais de Alerta (se for golpe) ou Dica de Ouro.
    5. Um breve resumo.

    Texto bruto:
    {conteudo_bruto[:INSIGHT_CONTENT_LIMIT]}
    """


def get_video_script_prompt(conteudo_insight: str, contexto_consolidado: str = '', num_scenes: int = 6) -> str:
    """
    Returns the prompt for generating a video script with multiple scenes.

    Args:
        conteudo_insight: Educational insight content in markdown format
        contexto_consolidado: Optional consolidated insights for additional context
        num_scenes: Number of scenes to generate (each ~8 seconds)

    Returns:
        Formatted prompt string for Gemini
    """
    contexto_extra = ''
    if contexto_consolidado:
        contexto_extra = f"""

    CONTEXTO ADICIONAL (Consolidado de Insights):
    Use este contexto para enriquecer o roteiro com informações relevantes e consistentes:
    {contexto_consolidado[:3000]}
    """

    # Build scene template
    scenes_template = ""
    for i in range(1, num_scenes + 1):
        start_time = (i - 1) * 8
        end_time = i * 8
        scenes_template += f"""
    ## CENA {i} ({start_time}-{end_time} segundos)
    **VISUAL:** [Descrição detalhada do que aparece na tela - pessoas, objetos, ações, cores, ambiente]
    **AUDIO:** [Narração ou diálogo em português brasileiro]
    **TRANSIÇÃO:** [Como esta cena conecta com a próxima]
"""

    total_duration = num_scenes * 8

    return f"""
    Você é um roteirista especializado em criar conteúdo educativo para idosos.

    Com base no seguinte conteúdo educativo:
    {conteudo_insight[:VIDEO_CONTENT_LIMIT]}
    {contexto_extra}

    Crie um ROTEIRO DE VÍDEO DE {total_duration} SEGUNDOS com EXATAMENTE {num_scenes} CENAS.

    IMPORTANTE: Cada cena deve ter uma descrição visual DETALHADA e ESPECÍFICA para geração de vídeo por IA.
    Descreva exatamente o que deve aparecer visualmente (pessoas, objetos, ações, ambiente, cores).

    FORMATO OBRIGATÓRIO:
{scenes_template}
    ## INFORMAÇÕES TÉCNICAS
    - Estilo visual: [Realista/Animação/Ilustrado]
    - Paleta de cores: [Cores predominantes]
    - Tom geral: [Amigável/Sério/Educativo]

    REGRAS:
    1. Linguagem simples e acessível para idosos
    2. Descrições visuais devem ser claras para IA de geração de vídeo
    3. Cada cena deve fluir naturalmente para a próxima
    4. Todo conteúdo em português brasileiro
    """


def get_consolidation_prompt(todos_insights: str) -> str:
    """
    Returns the prompt for consolidating all insights into a single summary.

    Args:
        todos_insights: Combined content from all insight files

    Returns:
        Formatted prompt string for generating consolidated insights
    """
    return f"""
    Você é um especialista em educação digital para idosos.

    Abaixo estão diversos insights educativos sobre segurança digital e uso de tecnologia para idosos.
    Sua tarefa é consolidar todo esse conhecimento em um único documento estruturado.

    Crie um arquivo Markdown (.md) chamado "Consolidado de Insights" contendo:

    # Consolidado de Insights - Educação Digital para Idosos

    ## 1. Principais Temas Abordados
    Liste os principais temas que aparecem nos insights (ex: golpes, PIX, WhatsApp, etc.)

    ## 2. Pontos-Chave de Aprendizado
    Liste os pontos mais importantes que um idoso deve aprender, organizados por categoria.

    ## 3. Principais Golpes e Como se Proteger
    Consolide informações sobre os golpes mais comuns e as formas de prevenção.

    ## 4. Principais Dicas Práticas de Segurança
    Liste as dicas de segurança digital mais relevantes e repetidas.

    ## 6. Principais Sinais de Alerta
    Liste os principais sinais de que algo pode ser um golpe.

    ## 7. Resumo Executivo
    Um parágrafo resumindo os principais aprendizados.

    Insights para consolidar:
    {todos_insights[:CONSOLIDATION_CONTENT_LIMIT]}
    """
