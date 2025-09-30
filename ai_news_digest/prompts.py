# ai_news_digest/prompts.py

# RELEVANCE_PROMPT = """\
# Sos analista de contenido. Del 0 al 10, ¿qué tan relevante es esta noticia para un
# resumen mensual sobre IA en español para profesionales de datos en LATAM?
# Respondé SOLO con un entero entre 0 y 10.

# Título: {title}

# Texto (recortado):
# {content_snippet}
# """
RELEVANCE_PROMPT  = """
Estás evaluando artículos relacionados con inteligencia artificial. 
Asignales un puntaje de relevancia del 1 al 10 (siendo 10 el más relevante), según estos criterios:

- Si presenta un nuevo desarrollo tecnológico en IA
- Si muestra aplicaciones innovadoras o disruptivas
- Si tiene impacto potencial alto en la industria o sociedad
- Si trata sobre etica, politica, economia o inversiones asignarle un puntaje igual a 1

Respondé SOLO con un número del 1 al 10. No des explicaciones.

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
