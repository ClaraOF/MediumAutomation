import json
import time

import pandas as pd
from agents import Agent, function_tool

from ai_news_digest.scraping.newsapi_fetch import fetch_newsapi_articles
from ai_news_digest.scraping.rss_fetch import fetch_all_rss_feeds
from ai_news_digest.scraping.techcrunch import scrape_techcrunch_ai


def _try_fetch(label: str, fetch_fn, retries: int = 1, delay: float = 3.0) -> pd.DataFrame:
    """
    Ejecuta fetch_fn con hasta `retries` reintentos ante fallos de red o excepciones.
    Siempre devuelve un DataFrame (vacío si la fuente falla definitivamente).
    Así una fuente caída no aborta la recolección de las demás.
    """
    for attempt in range(retries + 1):
        try:
            return fetch_fn()
        except Exception as e:
            if attempt < retries:
                print(
                    f"   [Collector] {label} falló (intento {attempt + 1}/{retries + 1}): {e}. "
                    f"Reintentando en {delay}s..."
                )
                time.sleep(delay)
            else:
                print(
                    f"   [Collector] {label} falló tras {retries + 1} intento(s): {e}. "
                    "Saltando fuente — el pipeline continúa con las demás."
                )
    return pd.DataFrame()


def make_collector_agent(
    model,
    newsapi_key: str,
    exclude_sources: list[str] | None = None,
) -> Agent:
    """
    Factory que crea el CollectorAgent con una sola tool que hace fetch + merge.

    Args:
        exclude_sources: Lista de fuentes a omitir. Valores válidos: 'newsapi', 'techcrunch', 'rss'.
    """
    _excluded = {s.lower() for s in (exclude_sources or [])}

    @function_tool
    def collect_all_articles(days: int, max_pages: int = 5) -> str:
        """
        Recolecta artículos de IA de todas las fuentes y devuelve un JSON array deduplicado.
        Fuentes: NewsAPI (EN + ES), TechCrunch (scraping), RSS feeds públicos.
        Cada fuente se intenta de forma independiente con 1 reintento — si una falla,
        las demás continúan y los artículos recuperados se incluyen igual.

        Args:
            days: Número de días hacia atrás para NewsAPI y RSS feeds.
            max_pages: Número máximo de páginas de TechCrunch a scrapear.

        Returns:
            JSON array de artículos con campos 'titulo', 'fuente', 'url', 'contenido', 'fecha'.
        """
        dfs = []

        # NewsAPI (EN + ES)
        if "newsapi" not in _excluded:
            df_en = _try_fetch("NewsAPI EN", lambda: fetch_newsapi_articles(newsapi_key, days=days, lang="en"))
            if not df_en.empty:
                dfs.append(df_en)

            df_es = _try_fetch("NewsAPI ES", lambda: fetch_newsapi_articles(newsapi_key, days=days, lang="es"))
            if not df_es.empty:
                dfs.append(df_es)
        else:
            print("   [Collector] NewsAPI: excluida (--exclude-source newsapi)")

        # TechCrunch scraping
        if "techcrunch" not in _excluded:
            df_tc = _try_fetch("TechCrunch", lambda: scrape_techcrunch_ai(max_pages=max_pages))
            if not df_tc.empty:
                dfs.append(df_tc)
        else:
            print("   [Collector] TechCrunch: excluida (--exclude-source techcrunch)")

        # RSS feeds públicos (sin API key)
        if "rss" not in _excluded:
            print("   [Collector] Fetching RSS feeds...")
            df_rss = _try_fetch("RSS feeds", lambda: fetch_all_rss_feeds(days=days))
            if not df_rss.empty:
                print(f"   [Collector] RSS total: {len(df_rss)} artículos de {df_rss['fuente'].nunique()} fuentes")
                dfs.append(df_rss)
        else:
            print("   [Collector] RSS: excluido (--exclude-source rss)")

        if not dfs:
            return json.dumps([])

        combined = pd.concat(dfs, ignore_index=True)
        if "url" in combined.columns:
            combined = combined.drop_duplicates(subset=["url"])

        # Truncar contenido para que el output de la tool no exceda el límite de tokens del LLM.
        # 500 chars es suficiente para scoring por keywords (ranker) y contexto de resumen (summarizer).
        # Nota: el orquestador auto-guarda el _articles_raw.csv DESPUÉS de recibir este JSON,
        # por lo que el CSV también tendrá contenido truncado a 500 chars.
        # Para acceder al contenido completo usá --articles-csv con el CSV original del primer run.
        if "contenido" in combined.columns:
            combined["contenido"] = combined["contenido"].str[:500]

        print(f"   [Collector] Total recolectados: {len(combined)} artículos de {combined['fuente'].nunique()} fuentes")
        return combined.to_json(orient="records", force_ascii=False)

    return Agent(
        name="CollectorAgent",
        model=model,
        instructions=(
            "Sos un agente de recolección de noticias de IA. "
            "Llamá a collect_all_articles con los parámetros days y max_pages. "
            "Devolvé el output de la tool directamente, sin modificarlo."
        ),
        tools=[collect_all_articles],
    )
