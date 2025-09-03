# ai_news_digest/pipeline.py
import pandas as pd
from ai_news_digest.config import Settings
from ai_news_digest.scraping.techcrunch import scrape_techcrunch_ai
# from ai_news_digest.scraping.newsapi_fetch import fetch_newsapi_articles  # <- desactivado
#from ai_news_digest.llm.openrouter import OpenRouterClient
from ai_news_digest.builder.images import og_image
from ai_news_digest.builder.medium import build_medium_article
from ai_news_digest.llm.openai_client import OpenAIClient

def collect_articles(settings, days: int = 30):
    #df_news = fetch_newsapi_articles(settings.newsapi_key, days=days)
    df_tc = scrape_techcrunch_ai()
    #df = pd.concat([df_news, df_tc], ignore_index=True).drop_duplicates(subset=["url"]).reset_index(drop=True)
    df = df_tc.copy()
    return df

KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
    "llm", "gpt", "genai", "vision", "nlp", "agents", "embedding", "retrieval",
    "openai", "google", "meta", "anthropic", "microsoft", "chips", "gpu", "nvidia"
]

def _heuristic_score(title: str, content: str) -> int:
    """Scoring simple por keywords (0..10)."""
    text = f"{title} {content}".lower()
    hits = sum(1 for kw in KEYWORDS if kw in text)
    # Normalizamos a 0..10 (cap a 10)
    return min(10, hits // 2 + (1 if hits > 0 else 0))

def _get_llm(settings: Settings):
    """Devuelve instancia de LLM si hay OpenAI, si no None."""
    if settings.has_llm and OpenAIClient is not None:
        return OpenAIClient(
            api_key=settings.openai_api_key,
            model_relevance=settings.openai_model_relevance,
            model_summary=settings.openai_model_summary,
        )
    return None

def rank_and_select(df: pd.DataFrame, settings: Settings, top_n: int = 15, ensure_source=None) -> pd.DataFrame:
    ensure_source = ensure_source or []
    client = _get_llm(settings)

    scores = []
    for _, row in df.iterrows():
        title = row.get("titulo", "") or row.get("title", "")
        content = row.get("contenido", "") or row.get("content", "")
        if client:
            try:
                score = client.score_relevance(title, content)
            except Exception:
                score = _heuristic_score(title, content)
        else:
            score = _heuristic_score(title, content)
        scores.append(score)

    df = df.assign(relevancia=scores)

    keep_rows = []
    for src in ensure_source:
        subset = df[df["fuente"].fillna("").str.contains(src, case=False, na=False)]
        if not subset.empty:
            keep_rows.append(subset.sort_values("relevancia", ascending=False).head(1))

    df_rest = df
    if keep_rows:
        kept = pd.concat(keep_rows).drop_duplicates(subset=["url"])
        df_rest = df[~df["url"].isin(kept["url"])]
        df_final = pd.concat([kept, df_rest], ignore_index=True)
    else:
        df_final = df

    df_top = df_final.sort_values("relevancia", ascending=False).head(top_n).reset_index(drop=True)
    return df_top

def summarize_and_build(df_top: pd.DataFrame, settings: Settings, month_name: str, lang: str = "es"):
    client = _get_llm(settings)
    rows = []
    for _, row in df_top.iterrows():
        title = row.get("titulo", "") or row.get("title", "")
        url = row.get("url", "")
        content = row.get("contenido", "") or row.get("content", "")
        if client:
            try:
                summ = client.summarize(title, url, content, lang=lang)
            except Exception:
                summ = {"titulo_sugerido": title, "resumen": f"(Sin LLM) {content[:400]}...\nSeguí leyendo: {url}"}
        else:
            summ = {"titulo_sugerido": title, "resumen": f"(Sin LLM) {content[:400]}...\nSeguí leyendo: {url}"}

        img = og_image(url)
        r = {
            "fuente": row.get("fuente", "TechCrunch"),
            "titulo": title,
            "url": url,
            "contenido": content,
            "titulo_sugerido": summ.get("titulo_sugerido", title),
            "resumen": summ.get("resumen", ""),
            "imagen": img,
        }
        rows.append(r)

    df_res = pd.DataFrame(rows)
    article = build_medium_article(df_res, month_name=month_name)
    return article, df_res