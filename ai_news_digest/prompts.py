# ai_news_digest/prompts.py

RELEVANCE_PROMPT = """\
Sos analista de contenido. Del 0 al 10, ¿qué tan relevante es esta noticia para un
resumen mensual sobre IA en español para profesionales de datos en LATAM?
Respondé SOLO con un entero entre 0 y 10.

Título: {title}

Texto (recortado):
{content_snippet}
"""

SUMMARY_PROMPT = """\
Redactá un resumen narrativo en {lang} de esta noticia sobre inteligencia artificial.
Estilo: técnico, claro y periodístico (medios de tecnología en Argentina).
Generá un TÍTULO atractivo y profesional (no clickbait) y un RESUMEN de 220-300 palabras.
Cerrá con: "Seguí leyendo en este enlace: {url}".

Título original: {title}

Texto:
{content_snippet}
"""
