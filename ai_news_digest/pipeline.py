# ai_news_digest/pipeline.py
import time
import pandas as pd
from ai_news_digest.config import Settings
from ai_news_digest.scraping.techcrunch import scrape_techcrunch_ai
from ai_news_digest.scraping.newsapi_fetch import fetch_newsapi_articles  # <- reactivado
from ai_news_digest.llm.base import BaseLLMClient
from ai_news_digest.llm.openai_client import OpenAIClient
from ai_news_digest.llm.openrouter import OpenRouterClient
from ai_news_digest.llm.azure_client import AzureOpenAIClient
from ai_news_digest.builder.images import og_image
from ai_news_digest.builder.medium import build_medium_article

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

def _get_llm(settings: Settings) -> BaseLLMClient | None:
    """Devuelve un LLM client. Orden de prioridad: Azure → OpenAI → OpenRouter → None."""
    if settings.has_azure:
        try:
            print("Trying AzureOpenAIClient...")
            return AzureOpenAIClient(
                api_key=settings.azure_api_key,
                endpoint=settings.azure_endpoint,
                deployment_relevance=settings.azure_deployment_relevance,
                deployment_summary=settings.azure_deployment_summary,
                api_version=settings.azure_api_version,
            )
        except Exception as e:
            print(f"Error initializing AzureOpenAIClient: {e}")

    if settings.has_openai:
        try:
            print("Trying OpenAIClient...")
            return OpenAIClient(
                api_key=settings.openai_api_key,
                model_relevance=settings.openai_model_relevance,
                model_summary=settings.openai_model_summary,
            )
        except Exception as e:
            print(f"Error initializing OpenAIClient: {e}")

    if settings.openrouter_api_key:
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

def rank_and_select(df: pd.DataFrame, settings: Settings, top_n: int = 15, ensure_source=None, llm_client=None) -> pd.DataFrame:
    ensure_source = ensure_source or []
    print("ensure_source:", ensure_source)
    client = llm_client if llm_client is not None else _get_llm(settings)
    print(f"Using LLM: {type(client).__name__ if client else 'None (heuristic only)'}")
    print('client:', client)
    n = len(df)
    if client and hasattr(client, "score_relevance_batch"):
        BATCH_SIZE = 20
        articles_list = [
            (row.get("titulo", "") or row.get("title", "") or "",
             row.get("contenido", "") or row.get("content", "") or "")
            for _, row in df.iterrows()
        ]
        n_batches = (n + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"   Batch LLM scoring: {n} artículos en {n_batches} batches de {BATCH_SIZE}...")
        all_scores = []
        llm_count = 0
        heuristic_count = 0
        for i in range(n_batches):
            batch = articles_list[i * BATCH_SIZE: (i + 1) * BATCH_SIZE]
            print(f"   Batch {i + 1}/{n_batches}...")
            try:
                batch_scores = client.score_relevance_batch(batch)
                if all(s == 0 for s in batch_scores):
                    batch_scores = [_heuristic_score(t, c) for t, c in batch]
                    heuristic_count += len(batch)
                else:
                    llm_count += len(batch)
            except Exception as e:
                print(f"   Error en batch {i + 1}: {e}")
                batch_scores = [_heuristic_score(t, c) for t, c in batch]
                heuristic_count += len(batch)
            all_scores.extend(batch_scores)
        print(f"   Scoring: {llm_count} con LLM, {heuristic_count} con heurística")
        scores = all_scores
    elif client:
        scores = []
        llm_count = 0
        heuristic_count = 0
        for _, row in df.iterrows():
            title = row.get("titulo", "") or row.get("title", "")
            content = row.get("contenido", "") or row.get("content", "")
            try:
                scores.append(client.score_relevance(title, content))
                llm_count += 1
            except Exception as e:
                print(f"Error scoring relevance with LLM: {e}")
                scores.append(_heuristic_score(title, content))
                heuristic_count += 1
        print(f"   Scoring: {llm_count} con LLM, {heuristic_count} con heurística")
    else:
        print("No LLM client available, usando heurística para todos.")
        scores = [_heuristic_score(
            row.get("titulo", "") or row.get("title", ""),
            row.get("contenido", "") or row.get("content", "")
        ) for _, row in df.iterrows()]

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

def summarize_and_build(df_top: pd.DataFrame, settings: Settings, month_name: str, lang: str = "es", llm_client=None):
    client = llm_client if llm_client is not None else _get_llm(settings)
    print(f"Using LLM for summarization: {type(client).__name__ if client else 'None (no summaries)'}")
    rows = []
    n = len(df_top)
    for i, (_, row) in enumerate(df_top.iterrows(), 1):
        title = row.get("titulo", "") or row.get("title", "")
        url = row.get("url", "")
        content = row.get("contenido", "") or row.get("content", "")
        print(f"   [{i}/{n}] Resumiendo: {title[:70]}...")
        if client:
            try:
                summ = client.summarize(title, url, content, lang=lang)
                print(f"   [{i}/{n}] OK")
                time.sleep(8)
            except Exception as e:
                print(f"Error summarizing '{title[:60]}': {e}")
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