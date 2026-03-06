# Medium Automation

Automatiza tu _monthly roundup_ de noticias de Inteligencia Artificial (IA).
El pipeline hace scraping, ranking por relevancia y genera un artículo en formato Markdown listo para publicar.

## Funcionalidades
- **Scraping de TechCrunch** para noticias del mes anterior.
- **Fetch de artículos vía NewsAPI** (con cuerpo completo usando newspaper3k).
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
│  └─ test_phase2.py          # Tests de regresión Fase 2 (sin API)
├─ outputs/                   # Artículos generados (.txt + .csv)
├─ ai_news_digest/
│  ├─ config_keys.py          # Tus claves API
│  ├─ config.py               # Settings: OpenAI, OpenRouter, Azure
│  ├─ prompts.py              # Templates para prompts
│  ├─ pipeline.py             # Pipeline original (sin agentes)
│  ├─ scraping/               # Scrapers (TechCrunch, NewsAPI)
│  ├─ llm/
│  │  ├─ base.py              # Protocol BaseLLMClient (contrato común)
│  │  ├─ openai_client.py     # Cliente OpenAI
│  │  ├─ openrouter.py        # Cliente OpenRouter
│  │  └─ azure_client.py      # Cliente Azure OpenAI
│  ├─ agents/                 # Pipeline agéntico (Fase 2)
│  │  ├─ __init__.py
│  │  ├─ setup.py             # Configuración del SDK por proveedor
│  │  ├─ collector.py         # CollectorAgent: NewsAPI + TechCrunch
│  │  ├─ ranker.py            # RankerAgent: scoring y ranking
│  │  ├─ summarizer.py        # SummarizerAgent: resúmenes en paralelo
│  │  ├─ builder.py           # BuilderAgent: arma y guarda el artículo
│  │  └─ orchestrator.py      # run_agentic_pipeline()
│  └─ builder/                # Arma artículo final + manejo de imágenes
```

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
| `--days` | `28` | Ventana de búsqueda hacia atrás en NewsAPI |
| `--top-n` | `20` | Cantidad de artículos en el output final |
| `--month` | auto (`Marzo_26`) | Nombre del mes — aparece en el título del artículo |
| `--lang` | `es` | Idioma de los resúmenes: `es` o `en` |
| `--ensure-source` | — | Fuente que debe aparecer sí o sí en el ranking (repetible) |
| `--out-path` | auto | Ruta de salida personalizada para el `.txt` |
| `--articles-csv` | — | CSV de artículos previos (saltea la recolección, no consume NewsAPI) |

### Reutilizar artículos ya recolectados (ahorra cuota de NewsAPI)
```bash
python main.py \
  --month "OpenAI_Marzo_26" \
  --articles-csv outputs/Highlights_AI_OpenAI_Marzo_26_20260306_161644.csv
```
Útil para probar cambios en el ranking, resúmenes o formato sin gastar cuota de API.

---

## Correr los tests

```bash
python -m pytest tests/ -v
```

Los tests no consumen APIs ni hacen requests externos. Cubren Fase 1 (LLM clients, Settings) y Fase 2 (agentes, tools, orquestador).
