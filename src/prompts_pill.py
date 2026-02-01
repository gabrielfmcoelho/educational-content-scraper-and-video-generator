"""Prompts for Knowledge Pill (Pilula de Conhecimento) generation.

Prompts are designed with accessibility in mind for elderly (idosos)
and neurodivergent (autistas) audiences.
"""

# Content limits for prompts
PILL_CONTENT_LIMIT = 5000
CONTEXT_LIMIT = 3000


def get_pill_short_text_prompt(conteudo_insight: str, contexto_consolidado: str = '') -> str:
    """
    Returns the prompt for generating the short text of a knowledge pill.

    The short text should be:
    - 2-4 sentences maximum
    - Simple language accessible to elderly
    - Clear, actionable advice
    - No jargon or technical terms

    Args:
        conteudo_insight: Educational insight content in markdown format
        contexto_consolidado: Optional consolidated insights for additional context

    Returns:
        Formatted prompt string
    """
    contexto_extra = ''
    if contexto_consolidado:
        contexto_extra = f"""

ADDITIONAL CONTEXT (Consolidated Insights):
Use this context to ensure consistency with other educational content:
{contexto_consolidado[:CONTEXT_LIMIT]}
"""

    return f"""Voce e um especialista em educacao digital para idosos e pessoas neurodivergentes.

Com base no seguinte conteudo educativo:
{conteudo_insight[:PILL_CONTENT_LIMIT]}
{contexto_extra}

Crie um TEXTO CURTO (pilula de conhecimento) seguindo estas regras:

REGRAS OBRIGATORIAS:
1. Maximo 3-4 frases curtas
2. Linguagem simples, sem termos tecnicos
3. Use verbos no imperativo (Faca, Evite, Desconfie, etc.)
4. Inclua uma acao pratica que a pessoa pode fazer
5. Evite metaforas abstratas - seja literal e direto
6. Use palavras do dia-a-dia

FORMATO:
Retorne APENAS o texto da pilula, sem titulos ou formatacao markdown.

EXEMPLO BOM:
"Desconfie de mensagens pedindo dados bancarios. Nunca clique em links suspeitos. Antes de fornecer informacoes pessoais, confirme com a empresa por telefone."

EXEMPLO RUIM (muito tecnico):
"Implemente autenticacao de dois fatores para proteger suas credenciais digitais contra ataques de phishing."

Agora, gere o texto da pilula:"""


def get_pill_call_to_action_prompt(short_text: str, topic: str) -> str:
    """
    Returns the prompt for generating a call-to-action question for the pill.

    The CTA should:
    - Be a simple yes/no or reflective question
    - Encourage the person to think about the topic
    - Not require technical knowledge to answer
    - Be relevant to their daily life

    Args:
        short_text: The short pill text already generated
        topic: The main topic/title of the insight

    Returns:
        Formatted prompt string
    """
    return f"""Voce e um educador especializado em idosos e pessoas neurodivergentes.

TOPICO: {topic}

TEXTO DA PILULA:
{short_text}

Crie UMA pergunta de chamada para acao (call-to-action) seguindo estas regras:

REGRAS:
1. Deve ser uma pergunta simples e direta
2. Pode ser respondida com "sim" ou "nao", ou com uma reflexao pessoal
3. Deve conectar o tema com a vida real da pessoa
4. Nao pode exigir conhecimento tecnico
5. Deve incentivar a pessoa a pensar ou agir

TIPOS DE PERGUNTAS ACEITAS:
- "Voce ja passou por essa situacao?"
- "O que voce faria se recebesse essa mensagem?"
- "Voce conhece alguem que ja foi enganado assim?"
- "Qual senha voce usaria para sua conta?"

FORMATO:
Retorne APENAS a pergunta, sem explicacoes adicionais.

Pergunta:"""


def get_infographic_prompt(topic: str, short_text: str) -> str:
    """
    Returns the prompt for generating an accessibility-focused infographic.

    This prompt is designed for Google Imagen and includes specific
    accessibility requirements for elderly and neurodivergent audiences.

    Args:
        topic: The main topic of the infographic
        short_text: The short educational text to visualize

    Returns:
        Formatted prompt string for Imagen
    """
    return f"""Create an educational infographic about: {topic}

Key message: {short_text[:500]}

Style requirements for accessibility:
- Simple, literal illustrations (no abstract metaphors)
- Large, clear icons and symbols (minimum 3 main visual elements)
- High contrast: dark text (#333) on light background (#FFF or #F5F5DC)
- Soft, calming color palette: blues (#4A90D9), greens (#7CB342), warm yellows (#FFD54F)
- NO text in the image - the text will be added separately
- Clean, uncluttered layout with generous whitespace
- Flat design style, no gradients or complex shadows
- Suitable for elderly (idosos) and neurodivergent (autistas) audiences
- Use realistic representations, not cartoons
- Include visual metaphors that are immediately understandable
- Show positive outcomes and safe behaviors, not scary scenarios"""


def get_pill_title_prompt(conteudo_insight: str) -> str:
    """
    Returns the prompt for generating a short, accessible title for the pill.

    Args:
        conteudo_insight: Educational insight content in markdown format

    Returns:
        Formatted prompt string
    """
    return f"""Voce e um especialista em educacao digital para idosos.

Com base no seguinte conteudo educativo:
{conteudo_insight[:PILL_CONTENT_LIMIT]}

Crie um TITULO CURTO para uma pilula de conhecimento.

REGRAS:
1. Maximo 6-8 palavras
2. Comece com verbo no imperativo (Como, Aprenda, Proteja, Evite, etc.)
3. Linguagem simples, sem termos tecnicos
4. Deve capturar a essencia do conteudo

EXEMPLOS:
- "Como identificar golpes online"
- "Proteja suas senhas na internet"
- "Evite cair em armadilhas no WhatsApp"

FORMATO:
Retorne APENAS o titulo, sem aspas ou formatacao.

Titulo:"""
