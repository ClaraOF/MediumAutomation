from typing import List, Dict
from datetime import date, timedelta
import time
import pandas as pd
from newsapi import NewsApiClient
from newspaper import Article
from ..utils import domains_from_urls

def fetch_newsapi_articles(api_key: str, days: int = 30, page_size: int = 100, max_pages: int = 2) -> pd.DataFrame:
    newsapi = NewsApiClient(api_key=api_key)
    sources = newsapi.get_sources()
    urls = [s['url'] for s in sources['sources']]
    domains = domains_from_urls(urls)

    today = date.today()
    start_date = today - timedelta(days=days)
    all_rows: List[Dict] = []

    for page in range(1, max_pages + 1):
        res = newsapi.get_everything(
            q="artificial intelligence OR AI OR machine learning",
            domains=",".join(domains),
            from_param=str(start_date),
            to=str(today),
            language="en",
            sort_by="publishedAt",
            page=page,
            page_size=page_size,
        )

        articles = res.get("articles", [])
        if not articles:
            break

        for a in articles:
            source_name = (a.get("source") or {}).get("name") or ""
            title = a.get("title") or ""
            url = a.get("url") or ""
            published_at = a.get("publishedAt") or ""

            content = ""
            if url:
                try:
                    art = Article(url, language="en")
                    art.download()
                    art.parse()
                    content = art.text or ""
                except Exception:
                    content = ""

            all_rows.append({
                "fuente": source_name,
                "titulo": title,
                "url": url,
                "fecha": published_at,
                "contenido": content,
            })

        time.sleep(1.0)

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df[df["contenido"].str.len() > 0].reset_index(drop=True)
    return df
