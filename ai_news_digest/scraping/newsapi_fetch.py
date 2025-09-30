from typing import List, Dict
from datetime import date, timedelta
import time
import pandas as pd
from newsapi import NewsApiClient
from newspaper import Article
from ..utils import domains_from_urls

def fetch_newsapi_articles(api_key: str, days: int = 30, page_size: int = 100, max_pages: int = 2, lang: str = "en") -> pd.DataFrame:
        newsapi = NewsApiClient(api_key=api_key)
        sources = newsapi.get_sources()
        urls = [s['url'] for s in sources['sources']]
        domains = domains_from_urls(urls)
        # agrego algunos dominios adicionales que no están en sources o si lo estaban luego los saco
        added_domains =["deeplearning.ai",
                        "kdnuggets.com",
                        "techcrunch.com",
                        "theverge.com",
                        "wired.com",
                        "engadget.com",
                        "arstechnica.com",
                        "thenextweb.com",
                        "digitaltrends.com",
                        #nuevos:
                        "the-decoder.com",
                        "artificialintelligence-news.com",
                        "news.mit.edu",
                        "bbc.com",
                        "gizmodo.com", #comentar si trae muchos de este
                    ]
        domains_new = list(set(added_domains + domains)) 
        print(f"Total NewsAPI domains used: {len(domains_new)}")
        # defino rango de fechas para la busqueda de articulos
        today = date.today()
        start_date = today - timedelta(days=days)
        print('From date: ', start_date, 'to date: ', today)
        all_rows: List[Dict] = []

        if lang == "en":
            keywords = '("artificial intelligence" OR AI OR "machine learning")'
        else:
            keywords = '("inteligencia artificial" OR IA OR "aprendizaje automático" OR "machine learning")'
    
        # Solo una página, máximo 100 resultados para que no falle
        try:
            res = newsapi.get_everything(
                q=keywords,
                domains=",".join(domains_new),
                from_param=str(start_date),
                to=str(today),
                language=lang,
                #sort_by="publishedAt",
                sort_by="relevancy", #articles more closely related to q come first
                page=1,
                page_size=min(page_size, 100),
            )
        except Exception as e:
            print(f"Error en NewsAPI get_everything: {e}")
            return pd.DataFrame()

        articles = res.get("articles", [])
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
