# ai_news_digest/pipeline.py
import pandas as pd
from ai_news_digest.config import Settings
from ai_news_digest.scraping.techcrunch import scrape_techcrunch_ai
from ai_news_digest.scraping.newsapi_fetch import fetch_newsapi_articles  # <- reactivado
from ai_news_digest.llm.openrouter import OpenRouterClient
from ai_news_digest.builder.images import og_image
from ai_news_digest.builder.medium import build_medium_article
from ai_news_digest.llm.openai_client import OpenAIClient

def collect_articles(settings, days: int = 30):
    print("Collecting articles with NewsAPI...")
    df_news_en = fetch_newsapi_articles(settings.newsapi_key, days=days, lang="en")
    print(f"------Artículos en Ingles recolectados con NewsAPI: {len(df_news_en)}")
    df_news_es = fetch_newsapi_articles(settings.newsapi_key, days=days, lang="es")
    print(f"------Artículos en Español recolectados con NewsAPI: {len(df_news_es)}")
    df_news = pd.concat([df_news_en, df_news_es], ignore_index=True).drop_duplicates(subset=["url"]).reset_index(drop=True)

    print("Collecting articles with TechCrunch...")
    df_tc = scrape_techcrunch_ai()
    print(f"------Artículos recolectados con TechCrunch: {len(df_tc)}")
    df = pd.concat([df_news, df_tc], ignore_index=True).drop_duplicates(subset=["url"]).reset_index(drop=True)
    #df = df_tc.copy()
    return df

KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
    "llm", "gpt", "genai", "vision", "nlp", "agents", "embedding", "retrieval",
    "openai", "google", "meta", "anthropic", "microsoft", "chips", "gpu", "nvidia"
]

def _heuristic_score(title: str, content: str) -> int:
    """Scoring simple por keywords (0..10)."""
    print("Heuristic scoring (no LLM)")
    text = f"{title} {content}".lower()
    hits = sum(1 for kw in KEYWORDS if kw in text)
    # Normalizamos a 0..10 (cap a 10)
    return min(10, hits // 2 + (1 if hits > 0 else 0))

def _get_llm(settings: Settings):
    """Devuelve instancia de LLM: OpenAI si hay key, si no OpenRouter si hay key, si no None."""
    # Intenta OpenAIClient primero
    if settings.has_llm and OpenAIClient is not None:
        try:
            print("Trying OpenAIClient...")
            return OpenAIClient(
                api_key=settings.openai_api_key,
                model_relevance=settings.openai_model_relevance,
                model_summary=settings.openai_model_summary,
            )
        except Exception as e:
            print(f"Error initializing OpenAIClient: {e}")
            print("Continuando con OpenRouterClient...")

    # Si falla OpenAIClient o no hay key, intenta OpenRouterClient
    if getattr(settings, "openrouter_api_key", None):
        try:
            print("Trying OpenRouterClient...")
            return OpenRouterClient(
                api_key=settings.openrouter_api_key,
                model_relevance=settings.openrouter_model_relevance,
                model_summary=settings.openrouter_model_summary,
            )
        except Exception as e:
            print(f"Error initializing OpenRouterClient: {e}")
            return None
    return None

def rank_and_select(df: pd.DataFrame, settings: Settings, top_n: int = 15, ensure_source=None) -> pd.DataFrame:
    ensure_source = ensure_source or []
    print("ensure_source:", ensure_source)
    client = _get_llm(settings)
    print(f"Using LLM: {type(client).__name__ if client else 'None (heuristic only)'}")
    print('client:', client)
    scores = []
    for _, row in df.iterrows():
        title = row.get("titulo", "") or row.get("title", "")
        content = row.get("contenido", "") or row.get("content", "")
        if client:
             try:
                 score = client.score_relevance(title, content)
             except Exception as e:
                 print(f"Error scoring relevance with LLM: {e}")
                 score = _heuristic_score(title, content)
        else:
             print("No LLM client available, using heuristic scoring.")
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

    # Limitar a máximo 10 artículos por fuente
    df_final = df_final.sort_values("relevancia", ascending=False)
    df_limited = df_final.groupby('fuente', group_keys=False).apply(lambda x: x.head(10)).reset_index(drop=True)
    # Seleccionar los top_n más relevantes, priorizando diversidad
    df_top = df_limited.sort_values("relevancia", ascending=False).head(top_n).reset_index(drop=True)
    return df_top

def summarize_and_build(df_top: pd.DataFrame, settings: Settings, month_name: str, lang: str = "es"):
    client = _get_llm(settings)
    print(f"Using LLM for summarization: {type(client).__name__ if client else 'None (no summaries)'}")
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