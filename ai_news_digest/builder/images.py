import requests
from bs4 import BeautifulSoup

def og_image(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
    except Exception:
        return None
    return None
