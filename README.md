# Medium Automation

Automatiza tu _monthly roundup_ de noticias de Inteligencia Artificial (IA).  
El pipeline hace scraping, ranking por relevancia y genera un artículo en formato Markdown listo para publicar.

## 🚀 Funcionalidades
- **Scraping de TechCrunch** para noticias del mes anterior.  
- **Fetch de artículos vía NewsAPI** (con cuerpo completo usando newspaper3k).  
- **Ranking de relevancia con LLM (OpenRouter)** para priorizar las más importantes.  
- **Resúmenes automáticos** en español con estilo periodístico/técnico.  
- **Artículo en Markdown** con imágenes para publicar en Medium o blogs.  

---

## 📂 Estructura del proyecto
MediumAutomation/
├─ main.py # Punto de entrada: corre todo el pipeline
├─ ai_news_digest/
│ ├─ config_keys.py # Tus claves API (sin .env)
│ ├─ config.py # Lee keys y valida configuración
│ ├─ prompts.py # Templates para prompts de relevancia y resumen
│ ├─ pipeline.py # Orquestación del pipeline
│ ├─ scraping/ # Scrapers (TechCrunch, NewsAPI)
│ ├─ llm/ # Conexión a OpenRouter
│ ├─ builder/ # Arma artículo final + manejo de imágenes
│ └─ utils.py # Helpers varios

---

## 🛠️ Requisitos
- Python **3.9+**
- Librerías: `requests`, `pandas`, `beautifulsoup4`, `newspaper3k`, `click`, `tqdm`, `backoff`, `newsapi-python`

Instalá dependencias:
```bash
pip install -e .


