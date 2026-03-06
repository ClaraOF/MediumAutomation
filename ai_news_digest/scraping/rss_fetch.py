"""
Módulo de recolección de artículos vía RSS/Atom feeds.

Fuentes configuradas: sin API key, uso personal sin restricciones relevantes.
El contenido se extrae del summary del feed (no full-text scraping) para
respetar los ToS y mantener el proceso liviano.
"""

import re
from datetime import datetime, timedelta, timezone

import feedparser
import pandas as pd

# ── Feeds configurados ────────────────────────────────────────────────────────
# Todos públicos, sin API key, diseñados para ser consumidos por agregadores.

RSS_FEEDS: dict[str, str] = {
    "Hugging Face Blog":         "https://huggingface.co/blog/feed.xml",
    "OpenAI Blog":               "https://openai.com/news/rss.xml",
    "Anthropic News":            "https://www.anthropic.com/news/rss.xml",
    "Google DeepMind":           "https://deepmind.google/blog/rss.xml",
    "MIT Tech Review AI":        "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "VentureBeat AI":            "https://venturebeat.com/category/ai/feed/",
    "The Decoder":               "https://the-decoder.com/feed/",
    "MarkTechPost":              "https://www.marktechpost.com/feed/",
    "KDnuggets":                 "https://www.kdnuggets.com/feed",
    "The Gradient":              "https://thegradient.pub/rss/",
    "DeepLearning.AI The Batch": "https://www.deeplearning.ai/the-batch/rss/",
    "AI News":                   "https://www.artificialintelligence-news.com/feed/",
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub(" ", text).strip()


def _parse_entry_date(entry) -> datetime | None:
    """Intenta parsear la fecha de publicación de una entrada RSS."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _extract_content(entry) -> str:
    """Extrae el mejor texto disponible de una entrada RSS sin hacer full-text fetch."""
    # content[] > summary > title fallback
    content_list = entry.get("content", [])
    if content_list:
        raw = content_list[0].get("value", "")
    else:
        raw = entry.get("summary", "") or entry.get("description", "")
    return _strip_html(raw)[:2000]  # cap para no enviar demasiado al LLM


def fetch_rss_feed(feed_url: str, source_name: str, days: int = 28) -> pd.DataFrame:
    """
    Fetch artículos de un feed RSS/Atom publicados en los últimos `days` días.

    Args:
        feed_url: URL del feed RSS o Atom.
        source_name: Nombre de la fuente (aparece en la columna 'fuente').
        days: Ventana de tiempo hacia atrás.

    Returns:
        DataFrame con columnas: fuente, titulo, url, fecha, contenido.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        print(f"   [RSS] ERROR al parsear {source_name}: {e}")
        return pd.DataFrame()

    if feed.bozo and not feed.entries:
        # bozo=True significa que el feed tiene errores de parseo pero puede tener entries igualmente
        print(f"   [RSS] WARNING: feed malformado en {source_name}, intentando de todas formas.")

    rows = []
    for entry in feed.entries:
        url = entry.get("link", "").strip()
        title = _strip_html(entry.get("title", "")).strip()

        if not url or not title:
            continue

        pub_date = _parse_entry_date(entry)
        if pub_date and pub_date < cutoff:
            continue

        # Si no hay fecha parseable la marcamos explícitamente para revisión manual en el CSV
        if pub_date is None:
            fecha_str = "sin_fecha"
        else:
            fecha_str = entry.get("published", entry.get("updated", ""))

        content = _extract_content(entry)

        rows.append({
            "fuente": source_name,
            "titulo": title,
            "url": url,
            "fecha": fecha_str,
            "contenido": content,
        })

    return pd.DataFrame(rows)


def fetch_all_rss_feeds(days: int = 28, feeds: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Fetch artículos de todos los feeds RSS configurados.

    Args:
        days: Ventana de días hacia atrás.
        feeds: Dict {nombre: url}. Si es None usa RSS_FEEDS por defecto.

    Returns:
        DataFrame combinado y deduplicado por URL.
    """
    feeds = feeds or RSS_FEEDS
    dfs = []

    for source_name, feed_url in feeds.items():
        df = fetch_rss_feed(feed_url, source_name, days=days)
        if not df.empty:
            print(f"   [RSS] {source_name}: {len(df)} artículos")
            dfs.append(df)
        else:
            print(f"   [RSS] {source_name}: 0 artículos (feed vacío o error)")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    if "url" in combined.columns:
        combined = combined.drop_duplicates(subset=["url"])

    return combined
