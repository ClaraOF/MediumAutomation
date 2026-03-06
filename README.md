# AI News Digest

Pipeline de automatización para generar un **resumen mensual de noticias de Inteligencia Artificial** listo para publicar en Medium u otros blogs.

Dado un rango de fechas, el sistema recolecta artículos de múltiples fuentes, los rankea por relevancia usando un LLM, genera resúmenes narrativos en español y arma un artículo en formato Markdown con imágenes.

---

## Cómo funciona el proceso

El pipeline se ejecuta en 4 pasos secuenciales:

```
[1] Recolección      [2] Ranking          [3] Resúmenes         [4] Guardado
 NewsAPI (EN/ES)  →   Score LLM (0-10) →   LLM narrativo    →   .txt (Markdown)
 TechCrunch scraper    Filtros de fuente     imagen OG           .csv (metadata)
```

### Paso 1 — Recolección de artículos (`collect_articles`)

Se recolectan artículos de dos fuentes independientes:

**NewsAPI**
- Busca artículos en inglés y español por keywords de IA (`"artificial intelligence"`, `AI`, `"machine learning"`, etc.)
- Usa la lista oficial de fuentes de NewsAPI + dominios adicionales configurados manualmente (`kdnuggets.com`, `the-decoder.com`, `news.mit.edu`, etc.)
- El contenido completo de cada artículo se obtiene con `newspaper3k` (ya que NewsAPI solo devuelve un snippet)
- Rango de fechas configurable (`days` hacia atrás desde hoy)

**TechCrunch (scraper)**
- Navega hasta 5 páginas de la sección `/category/artificial-intelligence/`
- Extrae título, fecha, URL y contenido de cada artículo con `BeautifulSoup`
- No requiere API key

Los dos DataFrames se concatenan y se deduplican por URL.

### Paso 2 — Ranking por relevancia (`rank_and_select`)

Cada artículo recibe un **score de relevancia (1-10)** evaluado por el LLM según estos criterios:

- Novedad técnica: ¿presenta un nuevo desarrollo, método o arquitectura?
- Aplicaciones innovadoras o disruptivas
- Potencial de impacto alto en industria, ciencia o sociedad
- Score = 1 si trata principalmente de ética, política, funding o estrategia corporativa
- Score = 1 si usa lenguaje vago o promocional sin avances técnicos concretos

Luego se aplican filtros:
- Se pueden **garantizar artículos de fuentes específicas** (`ensure_sources`), útil para incluir siempre KDnuggets u otras fuentes clave
- Máximo **10 artículos por fuente** para asegurar diversidad
- Se seleccionan los **top N** (configurable, default: 20) con mayor score

Si el LLM no está disponible, se usa un **scoring heurístico** basado en keywords presentes en el título y contenido.

### Paso 3 — Generación de resúmenes (`summarize_and_build`)

Para cada artículo seleccionado, el LLM genera:
- Un **título atractivo y profesional** (no clickbait)
- Un **resumen narrativo de 220-300 palabras** en español con contexto, desarrollo e impacto, cerrado con un link al artículo original

Además se extrae la **imagen OG** (`og:image`) de cada URL para incluirla en el artículo.

Con todos los resúmenes se construye el **artículo final en Markdown** con el formato:

```markdown
# 🧠 Los Highlights de [Mes] en Inteligencia Artificial

### Título del artículo 1
![imagen](url_imagen)
Resumen narrativo...

---

### Título del artículo 2
...
```

### Paso 4 — Guardado de resultados

Se guardan dos archivos en `outputs/`:
- `Highlights_AI_<mes>_<timestamp>.txt` — artículo completo en Markdown
- `Highlights_AI_<mes>_<timestamp>.csv` — metadata + resúmenes de cada artículo

---

## Proveedores LLM

El sistema intenta conectarse a los proveedores en este orden:

| Prioridad | Proveedor | SDK | Modelos por defecto |
|---|---|---|---|
| 1 | **OpenAI** (directo) | `openai` | `gpt-4o-mini` |
| 2 | **OpenRouter** | `requests` | `google/gemini-2.0-flash-lite-001` |
| 3 | **Heurístico** | — | Scoring por keywords |

OpenRouter permite usar modelos de Google, Anthropic, Meta, Mistral y otros a través de una sola API key, sin cambiar el código.

---

## Estructura del proyecto

```
MediumAutomation/
├── ai_news_digest/
│   ├── config_keys.py          # API keys (NO commitear — ver config_keys_example.py)
│   ├── config_keys_example.py  # Template de configuración
│   ├── config.py               # Dataclass Settings con todas las keys
│   ├── prompts.py              # Prompts para scoring de relevancia y resúmenes
│   ├── pipeline.py             # Funciones principales del pipeline
│   ├── utils.py                # Helpers (extracción de dominios, etc.)
│   ├── scraping/
│   │   ├── newsapi_fetch.py    # Fetch de artículos via NewsAPI + newspaper3k
│   │   └── techcrunch.py       # Scraper de TechCrunch con BeautifulSoup
│   ├── llm/
│   │   ├── openai_client.py    # Cliente OpenAI (scoring + resúmenes)
│   │   └── openrouter.py       # Cliente OpenRouter (scoring + resúmenes)
│   ├── builder/
│   │   ├── medium.py           # Arma el artículo final en Markdown
│   │   └── images.py           # Extrae imagen OG de cada URL
│   └── main_test.ipynb         # Notebook principal para ejecutar el pipeline
├── IMPROVEMENT_PLAN.md         # Plan de mejoras hacia arquitectura agéntica
├── pyproject.toml
└── outputs/                    # Archivos generados (ignorados por git)
```

---

## Configuración

### 1. Copiar el template de keys

```bash
cp ai_news_digest/config_keys_example.py ai_news_digest/config_keys.py
```

Editar `config_keys.py` con tus credenciales:

```python
NEWSAPI_KEY = "tu_key_de_newsapi"

# Opción A: OpenAI directo
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL_RELEVANCE = "gpt-4o-mini"
OPENAI_MODEL_SUMMARY = "gpt-4o-mini"

# Opción B: OpenRouter (modelos alternativos, incluye Gemini, Claude, etc.)
OPENROUTER_API_KEY = "sk-or-..."
OPENROUTER_MODEL_RELEVANCE = "google/gemini-2.0-flash-lite-001"
OPENROUTER_MODEL_SUMMARY = "google/gemini-2.0-flash-lite-001"
```

No es necesario configurar ambos. Si solo tenés OpenRouter, el sistema lo usará automáticamente.

### 2. Instalar dependencias

```bash
pip install -e .
```

---

## Cómo ejecutar

Abrir `ai_news_digest/main_test.ipynb` en Jupyter y configurar los parámetros en la segunda celda:

```python
DAYS = 30               # Rango de búsqueda en días hacia atrás
TOP_N = 20              # Cantidad de artículos a incluir
ENSURE_SOURCES = ['Kdnuggets.com']  # Fuentes que siempre deben aparecer
MONTH_NAME = "Febrero_26"           # Nombre del mes para el título y el archivo
LANG = "es"             # Idioma de los resúmenes ("es" o "en")
```

Luego ejecutar las celdas en orden. El proceso tarda entre 5 y 15 minutos dependiendo de la cantidad de artículos y el proveedor LLM usado (el paso más lento es el scoring de relevancia, que hace una llamada LLM por artículo).

---

## Dependencias principales

| Librería | Uso |
|---|---|
| `requests` + `beautifulsoup4` | Scraping de TechCrunch e imágenes OG |
| `newspaper3k` | Extracción de contenido completo de artículos |
| `newsapi-python` | Cliente oficial de NewsAPI |
| `openai` | Cliente para OpenAI y compatible con OpenRouter |
| `pandas` | Manejo de DataFrames en todo el pipeline |
| `backoff` | Reintentos automáticos en llamadas a OpenRouter |
| `marimo` | Interfaz alternativa al notebook (en exploración) |

---

## Notas

- `config_keys.py` está en `.gitignore` — nunca commitear API keys
- Los archivos en `outputs/` se generan localmente y no se versionan
- El scoring de relevancia se hace artículo por artículo (secuencial) — con 200 artículos puede tardar varios minutos
- Si NewsAPI devuelve pocos artículos, revisar que el rango de fechas (`DAYS`) no exceda el límite del plan gratuito (30 días)
