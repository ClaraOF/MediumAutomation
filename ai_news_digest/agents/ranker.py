import io
import json

import pandas as pd
from agents import Agent, function_tool

from ai_news_digest.config import Settings
from ai_news_digest.pipeline import _get_llm, _heuristic_score


def make_ranker_agent(model, settings: Settings, articles_json: str) -> Agent:
    """
    Factory que crea el RankerAgent.
    articles_json se pasa por closure — el LLM solo recibe top_n y ensure_sources.
    """

    llm_client = _get_llm(settings)

    @function_tool
    def score_and_rank(top_n: int, ensure_sources_json: str = "[]") -> str:
        """
        Puntúa cada artículo por relevancia de IA y devuelve los top N.

        Args:
            top_n: Cantidad máxima de artículos a devolver.
            ensure_sources_json: JSON array de fuentes que deben aparecer al menos una vez (ej: '[\"Kdnuggets.com\"]').

        Returns:
            JSON array de los top artículos con campo 'relevancia' agregado.
        """
        df = pd.read_json(io.StringIO(articles_json), orient="records")
        if df.empty:
            return json.dumps([])

        scores = []
        for _, row in df.iterrows():
            title = row.get("titulo", "") or row.get("title", "")
            content = row.get("contenido", "") or row.get("content", "")
            if llm_client:
                try:
                    score = llm_client.score_relevance(title, content)
                except Exception:
                    score = _heuristic_score(title, content)
            else:
                score = _heuristic_score(title, content)
            scores.append(score)

        df = df.assign(relevancia=scores)

        # Garantizar al menos un artículo de cada fuente especificada
        ensure_sources = json.loads(ensure_sources_json) if ensure_sources_json else []
        keep_rows = []
        for src in ensure_sources:
            subset = df[df["fuente"].fillna("").str.contains(src, case=False, na=False)]
            if not subset.empty:
                keep_rows.append(subset.sort_values("relevancia", ascending=False).head(1))

        # Cap de 10 artículos por fuente para diversidad
        df_sorted = df.sort_values("relevancia", ascending=False)
        df_limited = (
            df_sorted
            .groupby("fuente", group_keys=False)
            .apply(lambda x: x.head(10), include_groups=False)
            .reset_index(drop=True)
        )

        if keep_rows:
            kept = pd.concat(keep_rows).drop_duplicates(subset=["url"])
            df_rest = df_limited[~df_limited["url"].isin(kept["url"])]
            df_combined = pd.concat([kept, df_rest], ignore_index=True)
        else:
            df_combined = df_limited

        df_top = df_combined.sort_values("relevancia", ascending=False).head(top_n)
        return df_top.to_json(orient="records", force_ascii=False)

    return Agent(
        name="RankerAgent",
        model=model,
        instructions=(
            "Sos un agente que rankea artículos por relevancia. "
            "Llamá a score_and_rank con top_n y ensure_sources_json. "
            "Devolvé el output de la tool directamente, sin modificarlo."
        ),
        tools=[score_and_rank],
    )
