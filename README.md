# Medium Automation

Automatiza tu _monthly roundup_ de noticias de Inteligencia Artificial (IA).
El pipeline hace scraping, ranking por relevancia y genera un artículo en formato Markdown listo para publicar.

## Funcionalidades
- **Scraping de TechCrunch** para noticias del mes anterior.
- **Fetch de artículos vía NewsAPI** (con cuerpo completo usando newspaper3k).
- **RSS feeds públicos** de 12 fuentes de alta calidad (sin API key).
- **Ranking de relevancia con LLM** para priorizar las más importantes.
- **Resúmenes automáticos** en español con estilo periodístico/técnico.
- **Artículo en Markdown** con imágenes para publicar en Medium o blogs.
- **Soporte multi-proveedor LLM**: Azure OpenAI → OpenAI → OpenRouter (en ese orden de prioridad).
- **Arquitectura agéntica** con OpenAI Agents SDK: cada paso del pipeline es un agente independiente.

---

## Estructura del proyecto

```
MediumAutomation/
├─ main.py                    # Punto de entrada CLI con argparse
├─ tests/
│  ├─ test_phase1.py          # Tests de regresión Fase 1 (sin API)
│  ├─ test_phase2.py          # Tests de regresión Fase 2 (sin API)
│  └─ test_rss_fetch.py       # Tests del módulo RSS (sin requests reales)
├─ outputs/                   # Artículos generados (.txt + .csv)
├─ ai_news_digest/
│  ├─ config_keys.py          # Tus claves API
│  ├─ config.py               # Settings: OpenAI, OpenRouter, Azure
│  ├─ prompts.py              # Templates para prompts
│  ├─ pipeline.py             # Pipeline original (sin agentes)
│  ├─ scraping/
│  │  ├─ newsapi_fetch.py     # Fetch vía NewsAPI (requiere API key)
│  │  ├─ techcrunch.py        # Scraper de TechCrunch
│  │  └─ rss_fetch.py         # ← RSS feeds públicos (sin API key)
│  ├─ llm/
│  │  ├─ base.py              # Protocol BaseLLMClient (contrato común)
│  │  ├─ openai_client.py     # Cliente OpenAI
│  │  ├─ openrouter.py        # Cliente OpenRouter
│  │  └─ azure_client.py      # Cliente Azure OpenAI
│  ├─ agents/                 # Pipeline agéntico (Fase 2)
│  │  ├─ __init__.py
│  │  ├─ setup.py             # Configuración del SDK por proveedor
│  │  ├─ collector.py         # CollectorAgent: NewsAPI + TechCrunch + RSS
│  │  ├─ ranker.py            # RankerAgent: scoring y ranking
│  │  ├─ summarizer.py        # SummarizerAgent: resúmenes en paralelo
│  │  ├─ builder.py           # BuilderAgent: arma y guarda el artículo
│  │  └─ orchestrator.py      # run_agentic_pipeline()
│  └─ builder/                # Arma artículo final + manejo de imágenes
```

---

## Fuentes de artículos

El pipeline recolecta artículos de tres tipos de fuentes en cada ejecución:

| Fuente | Llamadas/run | Artículos aprox. | API key | Configurable en |
|--------|-------------|------------------|---------|-----------------|
| **NewsAPI EN** | 1 request | hasta 100 | ✅ requerida | `newsapi_fetch.py` |
| **NewsAPI ES** | 1 request | hasta 100 | ✅ requerida | `newsapi_fetch.py` |
| **TechCrunch** | 1 req/página | ~50 (5 páginas) | ❌ no | `orchestrator.py` (`max_pages=5`) |
| **RSS feeds** | 1 req/feed × 12 | ~100-200 en total | ❌ no | `rss_fetch.py` (`RSS_FEEDS`) |

**Total estimado por run: 300-450 artículos** antes de deduplicar. El ranker los reduce al `top_n` configurado (default 20).

> Los artículos RSS sin fecha parseable se incluyen con `fecha = "sin_fecha"` en el CSV para que puedas revisarlos manualmente si es necesario.

### Feeds RSS configurados

Todos son públicos, sin API key, diseñados para ser consumidos por agregadores:

| Fuente | Por qué vale la pena |
|--------|----------------------|
| Hugging Face Blog | Releases de modelos, papers |
| OpenAI Blog | Anuncios oficiales OpenAI |
| Anthropic News | Claude, seguridad, investigación |
| Google DeepMind | Research, Gemini |
| MIT Tech Review AI | Periodismo técnico de calidad |
| VentureBeat AI | Noticias de industria |
| The Decoder | Modelos, benchmarks, comparativas |
| MarkTechPost | Papers + aplicaciones |
| KDnuggets | Data science + ML práctico |
| The Gradient | Research + opinión técnica |
| DeepLearning.AI The Batch | Newsletter de Andrew Ng |
| AI News | Noticias generales de IA |

### Agregar una nueva fuente RSS

Solo editá el dict `RSS_FEEDS` en `ai_news_digest/scraping/rss_fetch.py`:

```python
RSS_FEEDS: dict[str, str] = {
    # ... fuentes existentes ...
    "Nueva Fuente":  "https://nueva-fuente.com/feed.xml",  # ← agregar acá
}
```

No hay que tocar ningún otro archivo. El collector la va a incluir automáticamente en la próxima ejecución.

### Agregar un scraper custom (como TechCrunch)

Para sitios sin RSS o con RSS limitado:

1. Crear `ai_news_digest/scraping/mi_fuente.py` con una función que retorne un `pd.DataFrame` con columnas `fuente, titulo, url, fecha, contenido`
2. Importar y llamar la función en `ai_news_digest/agents/collector.py` dentro de `collect_all_articles()`

---

## Requisitos

- Python **3.10+**

Instalá el proyecto y sus dependencias:

```bash
pip install -e .
```

---

## Configuración de LLM

Editá `ai_news_digest/config_keys.py` con tus claves. Solo necesitás completar el proveedor que vayas a usar:

**OpenAI**
```python
OPENAI_API_KEY = "sk-proj-..."
OPENAI_MODEL_RELEVANCE = "gpt-4o-mini"
OPENAI_MODEL_SUMMARY = "gpt-4o-mini"
```

**OpenRouter** (alternativa gratuita/barata)
```python
OPENROUTER_API_KEY = "sk-or-..."
OPENROUTER_MODEL_RELEVANCE = "google/gemini-2.0-flash-lite-001"
OPENROUTER_MODEL_SUMMARY = "google/gemini-2.0-flash-lite-001"
```

**Azure OpenAI**
```python
AZURE_API_KEY = "..."
AZURE_ENDPOINT = "https://tu-recurso.openai.azure.com/"
AZURE_DEPLOYMENT_RELEVANCE = "gpt-4o-mini"
AZURE_DEPLOYMENT_SUMMARY = "gpt-4o-mini"
```

> El pipeline selecciona el proveedor automáticamente según qué keys estén completas. Prioridad: **Azure → OpenAI → OpenRouter**.

---

## Correr el pipeline

### Ejecución básica
```bash
python main.py --month "OpenAI_Marzo_26"
```
Genera `outputs/Highlights_AI_OpenAI_Marzo_26_<timestamp>.txt` y su `.csv`.

### Todos los parámetros
```bash
python main.py \
  --days 28 \
  --top-n 20 \
  --month "OpenAI_Marzo_26" \
  --lang es \
  --ensure-source Kdnuggets.com \
  --ensure-source "Towards Data Science"
```

| Flag | Default | Descripción |
|------|---------|-------------|
| `--days` | `28` | Ventana de búsqueda hacia atrás (NewsAPI + RSS) |
| `--top-n` | `20` | Cantidad de artículos en el output final |
| `--month` | auto (`Marzo_26`) | Nombre del mes — aparece en el título del artículo |
| `--lang` | `es` | Idioma de los resúmenes: `es` o `en` |
| `--ensure-source` | — | Fuente que debe aparecer sí o sí en el ranking (repetible) |
| `--out-path` | auto | Ruta de salida personalizada para el `.txt` |
| `--articles-csv` | — | CSV de artículos previos (saltea la recolección, no consume NewsAPI) |
| `--exclude-source` | — | Fuente a excluir de la recolección: `newsapi`, `techcrunch`, `rss` (repetible) |

### Reutilizar artículos ya recolectados (ahorra cuota de NewsAPI)
```bash
python main.py \
  --month "OpenAI_Marzo_26" \
  --articles-csv outputs/Highlights_AI_OpenAI_Marzo_26_20260306_161644.csv
```
Útil para probar cambios en el ranking, resúmenes o formato sin gastar cuota de API.

> **Tip**: cada vez que corrés el pipeline completo, se auto-guarda un CSV de artículos crudos
> en `outputs/Highlights_AI_<month>_<timestamp>_articles_raw.csv` antes de rankear.
> Podés reutilizarlo con `--articles-csv` si el pipeline falla en pasos posteriores.

### Excluir fuentes de la recolección

Si ya tenés los artículos de una fuente guardados y no querés volver a consultarla:

```bash
# Solo RSS + TechCrunch (omitir NewsAPI)
python main.py --month "OpenAI_Marzo_26" --exclude-source newsapi

# Solo NewsAPI (omitir TechCrunch y RSS)
python main.py --month "OpenAI_Marzo_26" \
  --exclude-source techcrunch \
  --exclude-source rss

```

Los valores válidos para `--exclude-source` son: `newsapi`, `techcrunch`, `rss` (case-insensitive, repetible).

> **Nota**: `--exclude-source` y `--articles-csv` son mutuamente excluyentes — si usás `--articles-csv`,
> la recolección se saltea completamente y `--exclude-source` no tiene efecto.

---

## Correr los tests

```bash
python -m pytest tests/ -v
```

Los tests no consumen APIs ni hacen requests externos. Cubren Fase 1 (LLM clients, Settings), Fase 2 (agentes, tools, orquestador) y el módulo RSS.
