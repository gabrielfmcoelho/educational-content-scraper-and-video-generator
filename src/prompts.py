# Content limits for prompts
INSIGHT_CONTENT_LIMIT = 15000
VIDEO_CONTENT_LIMIT = 5000
CONSOLIDATION_CONTENT_LIMIT = 50000


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


def get_video_script_prompt(conteudo_insight: str, contexto_consolidado: str = '') -> str:
    """
    Returns the prompt for generating a 30-second video script.

    Args:
        conteudo_insight: Educational insight content in markdown format
        contexto_consolidado: Optional consolidated insights for additional context

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

    return f"""
    Você é um roteirista especializado em criar conteúdo educativo para idosos.

    Com base no seguinte conteúdo educativo:
    {conteudo_insight[:VIDEO_CONTENT_LIMIT]}
    {contexto_extra}

    Crie um ROTEIRO DE VÍDEO DE 30 SEGUNDOS com o seguinte formato:

    # Roteiro para Vídeo de 30 Segundos

    ## Cenário 1 (0-10 segundos)
    - Descrição visual:
    - Locução:

    ## Cenário 2 (10-20 segundos)
    - Descrição visual:
    - Locução:

    ## Cenário 3 (20-30 segundos)
    - Descrição visual:
    - Locução:

    ## Efeitos e Áudio
    - Som de fundo:
    - Transições:

    Mantenha a linguagem simples, acessível e clara para idosos.
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
