import io
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from agents import Agent, function_tool

from ai_news_digest.builder.images import og_image
from ai_news_digest.config import Settings
from ai_news_digest.pipeline import _get_llm

MAX_WORKERS = 5  # Conservador para evitar rate limiting


def make_summarizer_agent(model, settings: Settings, articles_json: str) -> Agent:
    """
    Factory que crea el SummarizerAgent con llamadas LLM paralelizadas.
    articles_json se pasa por closure — el LLM solo recibe el idioma.
    """

    llm_client = _get_llm(settings)

    def _summarize_one(row: dict, lang: str) -> dict:
        """Resume un artículo individual. Diseñado para correr en un thread."""
        title = row.get("titulo", "") or row.get("title", "")
        url = row.get("url", "")
        content = row.get("contenido", "") or row.get("content", "")

        if llm_client:
            try:
                summ = llm_client.summarize(title, url, content, lang=lang)
            except Exception:
                summ = {
                    "titulo_sugerido": title,
                    "resumen": f"(Error en LLM) {content[:400]}...\nSeguí leyendo: {url}",
                }
        else:
            summ = {
                "titulo_sugerido": title,
                "resumen": f"(Sin LLM) {content[:400]}...\nSeguí leyendo: {url}",
            }

        img = og_image(url)  # También es I/O bound — se beneficia del threading
        return {
            "fuente": row.get("fuente", ""),
            "titulo": title,
            "url": url,
            "contenido": content,
            "titulo_sugerido": summ.get("titulo_sugerido", title),
            "resumen": summ.get("resumen", ""),
            "imagen": img,
        }

    @function_tool
    def summarize_all_articles(lang: str) -> str:
        """
        Resume todos los artículos en paralelo usando ThreadPoolExecutor.

        Args:
            lang: Código de idioma para los resúmenes (ej: 'es', 'en').

        Returns:
            JSON array con campos 'titulo_sugerido', 'resumen', 'imagen' agregados.
        """
        df = pd.read_json(io.StringIO(articles_json), orient="records")
        if df.empty:
            return json.dumps([])

        rows = df.to_dict(orient="records")
        results: list[dict | None] = [None] * len(rows)  # Pre-asignado para preservar orden

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_idx = {
                executor.submit(_summarize_one, row, lang): idx
                for idx, row in enumerate(rows)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    row = rows[idx]
                    title = row.get("titulo", "") or ""
                    url = row.get("url", "")
                    results[idx] = {
                        "fuente": row.get("fuente", ""),
                        "titulo": title,
                        "url": url,
                        "contenido": row.get("contenido", ""),
                        "titulo_sugerido": title,
                        "resumen": f"(Error inesperado) {str(e)[:200]}",
                        "imagen": None,
                    }

        return pd.DataFrame(results).to_json(orient="records", force_ascii=False)

    return Agent(
        name="SummarizerAgent",
        model=model,
        instructions=(
            "Sos un agente que genera resúmenes de artículos. "
            "Llamá a summarize_all_articles con el código de idioma lang. "
            "Devolvé el output de la tool directamente, sin modificarlo."
        ),
        tools=[summarize_all_articles],
    )
