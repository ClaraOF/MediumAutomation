# Arquitectura Original del Pipeline — AI News Digest

> Estado del pipeline **previo** a los cambios del plan de mejoras agentic (`feature/agentic_improv`).

---

## Visión general

El pipeline toma noticias de múltiples fuentes, las rankea por relevancia usando un LLM, genera resúmenes en español y arma un artículo en formato Markdown listo para publicar en Medium.

```
Fuentes de datos
  │
  ▼
[1] Recolección de artículos
  │  NewsAPI (EN + ES) + TechCrunch scraping
  │
  ▼
[2] Scoring de relevancia
  │  LLM: 1 llamada por artículo (sin batching)
  │  Fallback: heurística por keywords
  │
  ▼
[3] Selección top N
  │  Ordena por score, aplica filtros de diversidad
  │
  ▼
[4] Generación de resúmenes
  │  LLM: 1 llamada por artículo, sin delay entre llamadas
  │
  ▼
[5] Construcción del artículo
     Markdown formateado para Medium (.txt + .csv)
```

---

## Etapa 1 — Recolección (`collect_articles`)

| Fuente | Método | Volumen típico |
|--------|--------|----------------|
| NewsAPI (inglés) | API REST | ~50 artículos |
| NewsAPI (español) | API REST | ~5 artículos |
| TechCrunch | Web scraping (BeautifulSoup, 5 páginas) | ~150 artículos |

- Deduplicación por URL al combinar fuentes.
- Contenido completo extraído con la librería `newspaper`.
- Keywords de búsqueda EN: `"artificial intelligence" OR AI OR "machine learning"`
- Keywords de búsqueda ES: `"inteligencia artificial" OR IA OR "aprendizaje automático"`

**Output:** DataFrame con columnas `fuente`, `titulo`, `url`, `fecha`, `contenido`.

---

## Etapa 2 — Scoring de relevancia (`rank_and_select`)

### Prioridad de cliente LLM

```
Azure OpenAI  →  OpenAI  →  OpenRouter  →  Heurística (sin LLM)
```

### Modelos usados

| Cliente | Modelo de relevancia |
|---------|---------------------|
| OpenAI | `gpt-4o-mini` |
| OpenRouter | `google/gemini-2.0-flash-lite-001` |
| Azure | deployment configurable |

### Criterios de scoring (prompt al LLM)

- **Score alto (7-10):** nuevo modelo o arquitectura de IA, aplicación disruptiva, alto impacto en industria o ciencia.
- **Score bajo (1):** ética, política, rondas de inversión, cambios de liderazgo, hype sin contenido técnico.

### Implementación original

- **Una llamada LLM por artículo** — con ~200 artículos implica ~200 requests consecutivos sin pausa.
- Si la llamada falla: score heurístico por keywords (`ai`, `llm`, `gpt`, `openai`, `nvidia`, etc.).
- Score heurístico: `min(10, hits // 2 + 1)`.

### Selección final

1. Agrega columna `relevancia` al DataFrame.
2. Garantiza al menos 1 artículo de fuentes especificadas (`ensure_source`).
3. Limita a 10 artículos por fuente (diversidad).
4. Retorna top N (default: 15) ordenados por score.

---

## Etapa 3 — Generación de resúmenes (`summarize_and_build`)

### Modelos usados

| Cliente | Modelo de summary |
|---------|------------------|
| OpenAI | `gpt-4o-mini` |
| OpenRouter | `google/gemini-2.0-flash-lite-001` |
| Azure | deployment configurable |

> Mismo modelo para relevancia y summary en cada cliente.

### Implementación original

- **Una llamada LLM por artículo**, sin delay entre llamadas.
- Input al LLM: título + primeros 2000 caracteres del contenido.
- Temperatura: `0.7`.
- Output esperado: titular atractivo + resumen narrativo de 220-300 palabras en español.
- Imagen: Open Graph tag del artículo (`og_image(url)`).
- Si falla: `(Sin LLM) {contenido[:400]}...` como fallback silencioso (sin log del error).

### Prompt de resumen (`SUMMARY_PROMPT`)

```
Write a narrative summary in {lang} of this news article about Artificial Intelligence.
Style: technical, clear, and journalistic.
Title: attractive, professional, no clickbait.
Summary: 220-300 words integrating context, main development, and impact.
Closing: "Seguí leyendo en este link: {url}"
```

> **Problema conocido:** `lang="es"` (código ISO) en lugar de "Spanish" causaba que algunos modelos generaran el resumen en inglés.

---

## Etapa 4 — Construcción del artículo (`build_medium_article`)

Genera un Markdown con la siguiente estructura:

```markdown
# 🧠 Los Highlights de {mes} en Inteligencia Artificial

Te compartimos las noticias más destacadas del mes.

### {titulo_sugerido}
![imagen]({imagen_url})

{resumen}

---

### {titulo_sugerido}
...

¿Querés seguir leyendo más? Volvemos el mes que viene con un nuevo resumen.
```

Guarda dos archivos:
- `.txt` — artículo en Markdown.
- `_articles_raw.csv` — DataFrame con todos los artículos procesados.

---

## Configuración

Todas las keys y modelos hardcodeados en `ai_news_digest/config_keys.py`:

```python
NEWSAPI_KEY                = "..."
OPENROUTER_API_KEY         = "..."
OPENROUTER_MODEL_RELEVANCE = "google/gemini-2.0-flash-lite-001"
OPENROUTER_MODEL_SUMMARY   = "google/gemini-2.0-flash-lite-001"
OPENAI_API_KEY             = ""
OPENAI_MODEL_RELEVANCE     = "gpt-4o-mini"
OPENAI_MODEL_SUMMARY       = "gpt-4o-mini"
```

El dataclass `Settings` (`config.py`) lee estos valores y expone propiedades como `has_openai`, `has_azure`, `has_llm` para que el pipeline decida qué cliente usar.

---

## Limitaciones del diseño original

| Limitación | Impacto |
|-----------|---------|
| 1 llamada LLM por artículo en scoring | ~200 requests → rate limit 429 con modelos free |
| 1 llamada LLM por artículo en summary | Rate limit 429, sin delay ni retry |
| Errores de summary silenciosos | Difícil diagnosticar fallos |
| `lang="es"` en lugar de "Spanish" | Resúmenes generados en inglés con algunos modelos |
| Keys hardcodeadas en código | Riesgo de exposición si se sube al repositorio |
| Mismo modelo para relevancia y summary | Comparten el mismo rate limit |
