# ai_news_digest/scraping/techcrunch.py
from __future__ import annotations
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_techcrunch_ai(max_pages: int = 5) -> pd.DataFrame:
    base_url = "https://techcrunch.com/category/artificial-intelligence/"
    articles = []

    for page in range(1, max_pages + 1):
        # Page 1 es especial
        url = base_url if page == 1 else f"{base_url}page/{page}/"
        print(f"Procesando {url}...")

        resp = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", class_="loop-card__title-link")
        if not links:
            print("No se encontraron más artículos.")
            break

        for a in links:
            href = a.get("href")
            if not href:
                continue

            try:
                art = requests.get(href, headers=HEADERS, verify=False, timeout=20)
                if art.status_code != 200:
                    continue

                s2 = BeautifulSoup(art.text, "html.parser")

                # Fecha
                time_tag = s2.find("time")
                date_val = None
                if time_tag and time_tag.has_attr("datetime"):
                    try:
                        date_val = datetime.fromisoformat(time_tag["datetime"].split("T")[0])
                    except Exception:
                        pass

                # Título
                h1 = s2.find("h1")
                title = h1.get_text(strip=True) if h1 else a.get_text(strip=True)

                # Contenido
                content_div = s2.find("div", class_=lambda x: x and "entry-content" in x)
                paragraphs = content_div.find_all("p") if content_div else []
                content = "\n".join(p.get_text(strip=True) for p in paragraphs)

                articles.append({
                    "fuente": "TechCrunch",
                    "titulo": title,
                    "url": href,
                    "fecha": date_val,
                    "contenido": content
                })
            except Exception as e:
                print(f"Error en {href}: {e}")
                continue

    df = pd.DataFrame(articles).drop_duplicates(subset=["url"]).reset_index(drop=True)
    return df