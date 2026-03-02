# Plan de Mejora: AI News Digest → Arquitectura Agéntica

## Estado actual

El pipeline actual es **secuencial y monolítico**:

```
collect_articles() → rank_and_select() → summarize_and_build() → save
```

- Interfaz: Jupyter Notebook (`main_test.ipynb`) con parámetros hardcodeados en celdas
- LLMs: OpenAI directo o OpenRouter como fallback
- Scraping: NewsAPI + TechCrunch (web scraping)
- Sin estado entre ejecuciones, sin reintentos inteligentes, sin observabilidad

---

## Objetivo

Convertir el pipeline a una arquitectura **agéntica modular**, con:
- Agentes especializados por responsabilidad
- Soporte multi-proveedor de LLMs (OpenAI, Azure OpenAI, OpenRouter)
- Interfaz interactiva tipo notebook
- Fácil extensibilidad (nuevas fuentes, modelos, salidas)

---

## 1. Arquitectura Agéntica Propuesta

### ¿Por qué agentes?

El pipeline actual falla silenciosamente (cae al heurístico), no puede reintentar pasos, y no puede tomar decisiones adaptativas. Un diseño agéntico permite:

- **Reintentos inteligentes**: si una fuente falla, el agente decide qué hacer
- **Decisiones adaptativas**: si hay pocos artículos relevantes, busca más
- **Observabilidad**: cada paso es trazable y auditable
- **Extensibilidad**: agregar un nuevo agente (e.g., "Twitter/X Scraper") no rompe el resto

### Agentes propuestos

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                   │
│  Coordina el flujo, recibe parámetros, maneja errores   │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌──────────┐
│Collector│  │ Ranker │  │Summarizer│
│ Agent  │  │ Agent  │  │  Agent   │
└────────┘  └────────┘  └──────────┘
    │            │            │
    └────────────┴────────────┘
                 │
            ┌────────┐
            │Builder │
            │ Agent  │
            └────────┘
```

**Collector Agent** — Herramientas: `fetch_newsapi`, `scrape_techcrunch`, `scrape_custom`
- Recibe: `days`, `sources`, `lang`
- Devuelve: DataFrame de artículos crudos
- Puede reintentar fuentes fallidas, agregar nuevas fuentes sin modificar el pipeline

**Ranker Agent** — Herramientas: `score_with_llm`, `score_heuristic`, `filter_by_source`
- Recibe: DataFrame, `top_n`, `ensure_sources`
- Devuelve: DataFrame rankeado y filtrado
- Puede pedir más artículos al Collector si no hay suficientes relevantes

**Summarizer Agent** — Herramientas: `summarize_article`, `fetch_og_image`
- Recibe: DataFrame top N
- Devuelve: DataFrame con resúmenes y metadatos
- Puede paralelizar llamadas LLM (actualmente son secuenciales → lento)

**Builder Agent** — Herramientas: `build_medium_article`, `save_txt`, `save_csv`
- Recibe: DataFrame con resúmenes
- Devuelve: archivos de salida
- Podría extenderse para publicar directo en Medium via API

---

## 2. Collector Agent: Expansión de Fuentes

### El problema con NewsAPI

NewsAPI solo indexa los sitios que tiene registrados en su sistema. Aunque puedas agregar dominios en `added_domains`, si NewsAPI no indexó ese sitio, no devuelve artículos de ahí. La solución es agregar **métodos de colección independientes de NewsAPI**.

### Enfoques disponibles

#### A — RSS/Atom Feeds ⭐ Recomendado como base
La mayoría de blogs y medios técnicos tienen RSS feeds. Es el método más confiable, liviano y sin riesgo de bloqueo. No requiere API key ni scraping frágil.

**Implementación genérica** con `feedparser` (ya disponible o fácil de instalar):

```python
import feedparser
from newspaper import Article
from datetime import datetime, timedelta

def fetch_rss_feed(feed_url: str, source_name: str, days: int = 30) -> pd.DataFrame:
    feed = feedparser.parse(feed_url)
    cutoff = datetime.now() - timedelta(days=days)
    rows = []
    for entry in feed.entries:
        # Filtrar por fecha
        published = entry.get("published_parsed")
        if published:
            pub_date = datetime(*published[:6])
            if pub_date < cutoff:
                continue
        url = entry.get("link", "")
        # Obtener contenido completo con newspaper3k (ya lo usás en newsapi_fetch.py)
        content = ""
        try:
            art = Article(url)
            art.download()
            art.parse()
            content = art.text or ""
        except Exception:
            content = entry.get("summary", "")
        rows.append({
            "fuente": source_name,
            "titulo": entry.get("title", ""),
            "url": url,
            "fecha": entry.get("published", ""),
            "contenido": content,
        })
    return pd.DataFrame(rows)
```

Con esta función, agregar una nueva fuente es **una sola línea** en la config:

```python
RSS_FEEDS = {
    "Hugging Face Blog":    "https://huggingface.co/blog/feed.xml",
    "Google AI Blog":       "https://blog.google/technology/ai/rss/",
    "OpenAI Blog":          "https://openai.com/news/rss.xml",
    "MIT Tech Review AI":   "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "VentureBeat AI":       "https://venturebeat.com/category/ai/feed/",
    "The Decoder":          "https://the-decoder.com/feed/",
    "MarkTechPost":         "https://www.marktechpost.com/feed/",
    "Anthropic Blog":       "https://www.anthropic.com/news/rss.xml",
    "Microsoft Research":   "https://www.microsoft.com/en-us/research/feed/",
}
```

#### B — Google News RSS (gratis, sin API key)
Google News expone RSS para cualquier búsqueda. Muy útil para cubrir fuentes que no tienen RSS propio:

```python
# Busca noticias de IA en Google News
GOOGLE_NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=inteligencia+artificial&hl=es&gl=AR&ceid=AR:es",
    "https://news.google.com/rss/search?q=large+language+model&hl=en-US&gl=US&ceid=US:en",
]
```

- No requiere API key
- Cubre virtualmente cualquier fuente que Google indexa
- Puede usarse para nichos específicos (ej: "AI en salud", "AI en finanzas")

#### C — ArXiv API (papers académicos)
Para incluir papers de investigación recientes (cs.AI, cs.LG, cs.CL):

```python
import urllib.request
import xml.etree.ElementTree as ET

def fetch_arxiv_papers(query: str = "cat:cs.AI OR cat:cs.LG", max_results: int = 20) -> pd.DataFrame:
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query={query}&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    # Parsear XML de ArXiv
    ...
```

- Completamente gratuito, sin rate limits relevantes
- Ideal si querés cubrir investigación además de noticias

#### D — Reddit API (r/MachineLearning, r/artificial)
Permite capturar posts virales y discusiones relevantes:

```python
import praw  # pip install praw

reddit = praw.Reddit(client_id=..., client_secret=..., user_agent="AI Digest")
subreddit = reddit.subreddit("MachineLearning+artificial+LocalLLaMA")
posts = subreddit.hot(limit=50)
```

- Requiere API key de Reddit (gratuita)
- Captura tendencias y discusiones de la comunidad

#### E — Scrapers custom adicionales (como TechCrunch)
Para sitios sin RSS o con RSS limitado. Candidatos:

| Sitio | Dificultad | Valor |
|---|---|---|
| `kdnuggets.com/news/` | Media | Alto (ya en lista) |
| `towardsdatascience.com` | Media | Alto |
| `aiweekly.co` | Baja | Medio |
| `deeplearning.ai/the-batch/` | Media | Alto |

---

### Arquitectura del Collector con múltiples fuentes

En el contexto agéntico, el `CollectorAgent` tendría estas tools:

```
CollectorAgent tools:
├── fetch_newsapi(days, lang)           ← ya existe
├── scrape_techcrunch(max_pages)        ← ya existe
├── fetch_rss_feed(feed_url, name, days)← nuevo (genérico)
├── fetch_google_news(query, lang, days)← nuevo
├── fetch_arxiv(query, max_results)     ← nuevo (opcional)
└── fetch_reddit(subreddits, days)      ← nuevo (opcional)
```

El orquestador le dice al agente qué fuentes activar según el contexto del mes. Por ejemplo, si el `MONTH_NAME` incluye "OpenAI", el agente puede priorizar fuentes de OpenAI Blog y Google News con query "OpenAI".

---

### Fuentes RSS de alta calidad recomendadas para arrancar

| Fuente | RSS URL | Por qué vale la pena |
|---|---|---|
| Hugging Face Blog | `https://huggingface.co/blog/feed.xml` | Releases de modelos, papers |
| Google AI Blog | `https://blog.google/technology/ai/rss/` | Anuncios de Google/DeepMind |
| OpenAI Blog | `https://openai.com/news/rss.xml` | Anuncios oficiales OpenAI |
| MIT Tech Review AI | `https://www.technologyreview.com/topic/artificial-intelligence/feed` | Periodismo técnico de calidad |
| VentureBeat AI | `https://venturebeat.com/category/ai/feed/` | Noticias de industria |
| The Decoder | `https://the-decoder.com/feed/` | Ya en tus dominios, fácil de agregar |
| MarkTechPost | `https://www.marktechpost.com/feed/` | Papers + aplicaciones |
| Anthropic News | `https://www.anthropic.com/news/rss.xml` | Anuncios oficiales Anthropic |

> **Nota**: Antes de usar en producción, verificar que cada URL de RSS sigue activa, ya que algunos proveedores las cambian.

---

## 4. Framework Agéntico: Opciones

### Opción A — OpenAI Agents SDK ⭐ Recomendada
**Por qué**: Nativa de OpenAI, soporta Azure OpenAI out-of-the-box, `tool_use` integrado, trazabilidad con Traces.

```python
from agents import Agent, Runner, tool

@tool
def fetch_newsapi(days: int, lang: str) -> str: ...

collector_agent = Agent(
    name="Collector",
    instructions="Recolecta artículos de IA desde las fuentes disponibles.",
    tools=[fetch_newsapi, scrape_techcrunch],
)
```

- **Azure**: solo cambiar el cliente base (`AzureOpenAI`) en la config
- **Curva de aprendizaje**: baja si ya usás OpenAI
- **Limitación**: acoplado al ecosistema OpenAI (aunque OpenRouter es compatible)

### Opción B — LangGraph
**Por qué**: Flujos como grafos con estado (`StateGraph`), ideal para pipelines con ramas condicionales.

```python
from langgraph.graph import StateGraph

graph = StateGraph(PipelineState)
graph.add_node("collect", collect_node)
graph.add_node("rank", rank_node)
graph.add_conditional_edges("rank", check_enough_articles, ...)
```

- **Azure**: compatible via `langchain-openai` con `AzureChatOpenAI`
- **Curva de aprendizaje**: media (concepto de grafos + estado)
- **Ventaja**: muy visual, fácil de extender con ramas condicionales

### Opción C — PydanticAI
**Por qué**: Type-safe, minimalista, excelente si querés schemas estrictos para las respuestas de los agentes.

- Más nuevo, menos adopción que LangGraph
- Buena opción si valorás type safety sobre flexibilidad

### Opción D — Sin framework agéntico (refactor modular)
Mantener el diseño actual pero extraer cada función a clases con interfaz común, añadir reintentos con `tenacity`, y agregar logging estructurado.

- Riesgo mínimo, esfuerzo bajo
- No es verdaderamente agéntico (sin toma de decisiones)

---

## 5. Soporte Multi-Proveedor LLM

La migración a Azure (o cualquier otro proveedor) se puede abstraer con una interfaz común:

```python
# Interfaz LLM base (ya existe parcialmente)
class BaseLLMClient(Protocol):
    def score_relevance(self, title: str, content: str) -> int: ...
    def summarize(self, title: str, url: str, content: str, lang: str) -> dict: ...

# Implementaciones
class OpenAIClient(BaseLLMClient): ...          # OpenAI directo (ya existe)
class AzureOpenAIClient(BaseLLMClient): ...     # Solo cambia base_url + api_version
class OpenRouterClient(BaseLLMClient): ...      # Ya existe
```

**Migración a Azure OpenAI** — es casi trivial con el SDK de OpenAI:

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=settings.azure_api_key,
    api_version="2024-02-01",
    azure_endpoint=settings.azure_endpoint,  # e.g. https://mi-recurso.openai.azure.com/
)
# El resto del código de llamadas es idéntico al cliente OpenAI
```

Solo hay que agregar en `Settings`:
- `azure_api_key`
- `azure_endpoint`
- `azure_deployment_name` (en vez de model name)

---

## 6. Interfaz: Opciones

### Opción A — Marimo ⭐ Recomendada
Ya estás probándolo (`marimo_test.py`). Es la mejor opción para este caso:

| Característica | Marimo | Jupyter |
|---|---|---|
| Reactividad (re-ejecuta celdas dependientes) | ✅ | ❌ |
| Parametrización con UI (`mo.ui.slider`, `mo.ui.text`) | ✅ | ❌ nativo |
| Reproducible y versionable (es `.py`, no `.ipynb`) | ✅ | ❌ |
| Puede desplegarse como app web | ✅ | ❌ |
| Barra de progreso nativa | ✅ (`mo.status.progress_bar`) | manual |

**Propuesta de interfaz Marimo:**
```python
# marimo_pipeline.py
days_slider = mo.ui.slider(1, 90, value=30, label="Días a cubrir")
top_n_slider = mo.ui.slider(5, 50, value=20, label="Top N artículos")
month_input = mo.ui.text(placeholder="Ej: Febrero_26", label="Nombre del mes")
lang_dropdown = mo.ui.dropdown(["es", "en"], value="es", label="Idioma")
run_button = mo.ui.run_button(label="Ejecutar pipeline")
```

Cuando el usuario hace click en "Ejecutar", las celdas de colección, ranking y resumen se ejecutan reactivamente.

### Opción B — Streamlit
- Web app simple, fácil de desplegar
- No es notebook (flujo diferente)
- Buena opción si querés compartirlo con otros (no técnicos)

### Opción C — Jupyter + ipywidgets
- Familiaridad actual
- Menos reactivo que Marimo
- `.ipynb` dificulta el control de versiones (JSON con outputs)

---

## 7. Roadmap de Implementación Sugerido

### Fase 1 — Refactor base (sin romper nada) — ~1 día
- [ ] Crear `BaseLLMClient` Protocol en `llm/base.py`
- [ ] Agregar `AzureOpenAIClient` en `llm/azure_client.py`
- [ ] Actualizar `Settings` con campos Azure opcionales
- [ ] Actualizar `_get_llm()` para incluir Azure como opción

### Fase 2 — Agentizar el pipeline — ~2-3 días
- [ ] Elegir framework (recomendado: OpenAI Agents SDK o LangGraph)
- [ ] Convertir `collect_articles` → `CollectorAgent` con tools
- [ ] Convertir `rank_and_select` → `RankerAgent` con tools
- [ ] Convertir `summarize_and_build` → `SummarizerAgent` con tools
- [ ] Crear `OrchestratorAgent` que coordina el flujo
- [ ] Paralelizar llamadas LLM en el summarizer (actualmente secuencial)

### Fase 3 — Interfaz Marimo — ~1 día
- [ ] Crear `marimo_pipeline.py` con controles UI
- [ ] Mostrar progreso en tiempo real
- [ ] Mostrar preview de artículos seleccionados antes de generar resúmenes
- [ ] Mostrar output final renderizado en el notebook

### Fase 4 — Mejoras adicionales (futuro)
- [ ] Agregar nuevas fuentes: ArXiv, Reddit (r/MachineLearning), X/Twitter
- [ ] Cache de artículos para no re-fetchear en cada ejecución
- [ ] Logging estructurado (e.g., `loguru`)
- [ ] Tests unitarios para cada agente
- [ ] Despliegue opcional como app Marimo en un servidor

---

## 8. Recomendación Final

| Aspecto | Elección recomendada | Alternativa |
|---|---|---|
| Framework agéntico | OpenAI Agents SDK | LangGraph |
| Proveedor LLM | OpenRouter (actual) + Azure como opción | OpenAI directo |
| Interfaz | Marimo | Streamlit |
| Migración Azure | `AzureOpenAI` client del SDK openai | — |

**Por qué OpenAI Agents SDK + Marimo:**
- El SDK de OpenAI ya lo usás, la curva de aprendizaje es mínima
- Azure OpenAI usa el mismo SDK (solo cambia el cliente base)
- Marimo ya está en el proyecto, es reactivo y versionable
- La combinación permite pasar de "notebook de experimentación" a "herramienta productiva" sin cambiar el lenguaje ni el paradigma de trabajo

---

*Generado: 2026-03-02*
