# ai_news_digest/prompts.py

# RELEVANCE_PROMPT = """\
# Sos analista de contenido. Del 0 al 10, ¿qué tan relevante es esta noticia para un
# resumen mensual sobre IA en español para profesionales de datos en LATAM?
# Respondé SOLO con un entero entre 0 y 10.

# Título: {title}

# Texto (recortado):
# {content_snippet}
# """
# RELEVANCE_PROMPT  = """
# Estás evaluando artículos relacionados con inteligencia artificial. 
# Asignales un puntaje de relevancia del 1 al 10 (siendo 10 el más relevante), según estos criterios:

# - Si presenta un nuevo desarrollo tecnológico en IA
# - Si muestra aplicaciones innovadoras o disruptivas
# - Si tiene impacto potencial alto en la industria o sociedad
# - Si trata sobre etica, politica, economia o inversiones asignarle un puntaje igual a 1

# Respondé SOLO con un número del 1 al 10. No des explicaciones.

# Título: {title}

# Texto (recortado):
# {content_snippet}
# """

# SUMMARY_PROMPT = """\
# Redactá un resumen narrativo en {lang} de esta noticia sobre inteligencia artificial.
# Estilo: técnico, claro y periodístico (medios de tecnología en Argentina).
# Generá un TÍTULO atractivo y profesional (no clickbait) y un RESUMEN de 220-300 palabras.
# Cerrá con: "Seguí leyendo en este enlace: {url}".

# Título original: {title}

# Texto:
# {content_snippet}
# """

BATCH_RELEVANCE_PROMPT = """You are evaluating articles related to Artificial Intelligence.
Rate each article's relevance from 1 to 10 (10 = most relevant) using these criteria:

- Novelty and innovation: new AI models, methods, or architectures → higher scores
- Disruptive or creative AI applications → higher scores
- High potential impact on industry, science, or society → higher scores
- Ethics, politics, corporate strategy, funding rounds, leadership changes → score of 1
- Vague hype without concrete technical content → score of 1

Return ONLY a valid JSON array of {n} integers in the exact same order as the articles below.
Example for 3 articles: [8, 1, 6]

Articles:
{articles_list}"""

RELEVANCE_PROMPT  = """
You are evaluating articles related to Artificial Intelligence. Assign a relevance score from 1 to 10 (10 being the most relevant) based on these criteria:

- Novelty and innovation: Does the article present a new technological development, method, or architecture in AI?
- Innovative applications: Does it showcase disruptive or creative uses of AI in emerging or unconventional domains?
- High potential impact: Could this have a transformative effect on industry, science, or society through its technical implementation?
- Exclude certain topics: If the article is mainly about ethics, politics, corporate strategy, funding rounds, leadership changes, or market positioning, assign a score of 1.
- Avoid hype: If the article uses vague or promotional language without describing concrete technical advances or applications, assign a score of 1.

Respond ONLY with a single number from 1 to 10. Do not provide explanations.

Título: {title}

Texto (recortado):
{content_snippet}
"""

SUMMARY_PROMPT = """\
Write a narrative summary in Spanish (español) of this news article about Artificial Intelligence.
IMPORTANT: The entire response MUST be written in Spanish. Do not use English.

Style: technical, clear, and journalistic (similar to leading technology media).
Title: create an attractive, professional, and descriptive headline (avoid clickbait).
Summary: between 220 and 300 words, integrating:

- Context and background of the news
- Main development or announcement
- Its relevance and potential impact

Do not use section headers like 'Context:', 'Development:', or 'Relevance and Impact:'. Instead, weave these elements naturally into the narrative.

Closing: end the summary with one of the following phrases (chosen naturally based on tone and flow):
- "Seguí leyendo en este link: {url}"
- "Seguí leyendo en este enlace: {url}"
- "Conocé más en este enlace: {url}"

Additional instructions:

- Keep an objective tone, avoid personal opinions.
- Include key facts, figures, and examples if mentioned in the article.
- Use natural, fluent language while maintaining technical accuracy.
- Ensure the summary is coherent and flows well from one point to the next.

Título original: {title}

Texto:
{content_snippet}
"""