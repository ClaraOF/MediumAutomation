# AI News Digest

Pipeline de automatización para generar un **resumen mensual de noticias de Inteligencia Artificial** listo para publicar en Medium u otros blogs.

Dado un rango de fechas, el sistema recolecta artículos de múltiples fuentes, los rankea por relevancia usando un LLM, genera resúmenes narrativos en español y arma un artículo en formato Markdown con imágenes.

---

## Cómo funciona el proceso

El pipeline se ejecuta en 4 pasos secuenciales:

```
[1] Recolección      [2] Ranking          [3] Resúmenes         [4] Guardado
 NewsAPI (EN/ES)  →   Score LLM (1-10) →   LLM narrativo    →   .txt (Markdown)
 TechCrunch scraper    Batches de 20        imagen OG           .csv (metadata)
                       Fallback heurístico
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

El scoring se hace en **batches de 20 artículos por llamada LLM** para minimizar el número de requests y evitar rate limits.

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

Con todos los resúmenes se construye el **artículo final en Markdown**:

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

El sistema intenta conectarse a los proveedores en este orden de prioridad:

| Prioridad | Proveedor | Modelos por defecto |
|-----------|-----------|---------------------|
| 1 | **Azure OpenAI** | Configurable (ej: `gpt-5.4-mini`) |
| 2 | **OpenAI** (directo) | `gpt-4o-mini` |
| 3 | **OpenRouter** | `nvidia/nemotron-3-super-120b-a12b:free` |
| 4 | **Heurístico** | Scoring por keywords (sin LLM) |

Se puede usar un modelo distinto para scoring de relevancia y para generación de resúmenes, configurando `*_MODEL_RELEVANCE` y `*_MODEL_SUMMARY` por separado.

---

## Estructura del proyecto

```
MediumAutomation/
├── .env                        # API keys locales (NO commitear — ver .env.example)
├── .env.example                # Template de configuración
├── ARCHITECTURE.md             # Documentación de la arquitectura del pipeline
├── ai_news_digest/
│   ├── config.py               # Dataclass Settings — lee variables de entorno
│   ├── prompts.py              # Prompts para scoring de relevancia y resúmenes
│   ├── pipeline.py             # Funciones principales del pipeline
│   ├── scraping/
│   │   ├── newsapi_fetch.py    # Fetch de artículos via NewsAPI + newspaper3k
│   │   └── techcrunch.py       # Scraper de TechCrunch con BeautifulSoup
│   ├── llm/
│   │   ├── base.py             # Clase base para clientes LLM
│   │   ├── azure_client.py     # Cliente Azure OpenAI (scoring + resúmenes)
│   │   ├── openai_client.py    # Cliente OpenAI directo (scoring + resúmenes)
│   │   └── openrouter.py       # Cliente OpenRouter (scoring + resúmenes)
│   ├── builder/
│   │   ├── medium.py           # Arma el artículo final en Markdown
│   │   └── images.py           # Extrae imagen OG de cada URL
│   └── main_test.ipynb         # Notebook principal para ejecutar el pipeline
├── pyproject.toml
└── outputs/                    # Archivos generados (ignorados por git)
```

---

## Configuración

### 1. Crear el archivo `.env`

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales. Solo es necesario configurar un proveedor LLM:

```env
NEWSAPI_KEY=tu_key_de_newsapi

# Opción A: Azure OpenAI (prioridad más alta)
AZURE_API_KEY=...
AZURE_ENDPOINT=https://tu-recurso.openai.azure.com/openai/v1
AZURE_DEPLOYMENT_RELEVANCE=gpt-5.4-mini
AZURE_DEPLOYMENT_SUMMARY=gpt-5.4-mini

# Opción B: OpenAI directo
OPENAI_API_KEY=sk-...
OPENAI_MODEL_RELEVANCE=gpt-4o-mini
OPENAI_MODEL_SUMMARY=gpt-4o-mini

# Opción C: OpenRouter (modelos free disponibles)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL_RELEVANCE=nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_MODEL_SUMMARY=stepfun/step-3.5-flash:free
```

### 2. Instalar dependencias

```bash
pip install -e .
```

---

## Cómo ejecutar

Abrir `ai_news_digest/main_test.ipynb` en Jupyter y configurar los parámetros:

```python
DAYS = 28               # Rango de búsqueda en días hacia atrás
TOP_N = 20              # Cantidad de artículos a incluir
ENSURE_SOURCES = ['Kdnuggets.com']  # Fuentes que siempre deben aparecer
MONTH_NAME = "Marzo_26"             # Nombre del mes para el título y el archivo
LANG = "es"                         # Idioma de los resúmenes
```

Ejecutar las celdas en orden. El proceso tarda entre 5 y 15 minutos dependiendo de la cantidad de artículos y el proveedor LLM.

---

## Dependencias principales

| Librería | Uso |
|----------|-----|
| `requests` + `beautifulsoup4` | Scraping de TechCrunch e imágenes OG |
| `newspaper3k` | Extracción de contenido completo de artículos |
| `newsapi-python` | Cliente oficial de NewsAPI |
| `openai` | Cliente para OpenAI y Azure OpenAI |
| `python-dotenv` | Carga de variables de entorno desde `.env` |
| `pandas` | Manejo de DataFrames en todo el pipeline |
| `backoff` | Reintentos automáticos en llamadas a la API |

---

## Notas

- `.env` está en `.gitignore` — nunca commitear API keys
- Los archivos en `outputs/` se generan localmente y no se versionan
- El scoring de relevancia usa batches de 20 artículos por llamada — con 200 artículos hace ~10 requests en lugar de 200
- Si NewsAPI devuelve pocos artículos, revisar que el rango de fechas (`DAYS`) no exceda el límite del plan gratuito (30 días)
