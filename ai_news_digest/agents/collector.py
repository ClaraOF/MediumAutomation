import json

import pandas as pd
from agents import Agent, function_tool

from ai_news_digest.scraping.newsapi_fetch import fetch_newsapi_articles
from ai_news_digest.scraping.techcrunch import scrape_techcrunch_ai


def make_collector_agent(model, newsapi_key: str) -> Agent:
    """Factory que crea el CollectorAgent con una sola tool que hace fetch + merge."""

    @function_tool
    def collect_all_articles(days: int, max_pages: int = 5) -> str:
        """
        Recolecta artículos de IA de todas las fuentes y devuelve un JSON array deduplicado.

        Args:
            days: Número de días hacia atrás para NewsAPI.
            max_pages: Número máximo de páginas de TechCrunch a scrapear.

        Returns:
            JSON array de artículos con campos 'titulo', 'fuente', 'url', 'contenido', 'fecha'.
        """
        dfs = []

        df_en = fetch_newsapi_articles(newsapi_key, days=days, lang="en")
        if not df_en.empty:
            dfs.append(df_en)

        df_es = fetch_newsapi_articles(newsapi_key, days=days, lang="es")
        if not df_es.empty:
            dfs.append(df_es)

        df_tc = scrape_techcrunch_ai(max_pages=max_pages)
        if not df_tc.empty:
            dfs.append(df_tc)

        if not dfs:
            return json.dumps([])

        combined = pd.concat(dfs, ignore_index=True)
        if "url" in combined.columns:
            combined = combined.drop_duplicates(subset=["url"])

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
