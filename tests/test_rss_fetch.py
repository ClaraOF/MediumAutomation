"""
Tests para el módulo RSS fetch.
No hacen requests reales — feedparser.parse está mockeado.

Ejecutar con:
    python -m pytest tests/test_rss_fetch.py -v
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _make_mock_feed(entries: list[dict]) -> MagicMock:
    """Construye un objeto feed mockeado con el formato de feedparser."""
    feed = MagicMock()
    feed.bozo = False
    feed.entries = [MagicMock(**e) for e in entries]
    for entry, raw in zip(feed.entries, entries):
        entry.get = lambda k, default="", _raw=raw: _raw.get(k, default)
    return feed


def _make_entry(title="AI Test", url="http://example.com/1", days_ago=1,
                summary="Test summary content", source="TestSource") -> dict:
    """Construye un entry de feedparser simulado."""
    pub = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "title": title,
        "link": url,
        "published": pub.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "published_parsed": pub.timetuple(),
        "summary": summary,
        "content": [],
    }


# ── Tests de fetch_rss_feed ───────────────────────────────────────────────────

def test_fetch_rss_feed_retorna_dataframe():
    """fetch_rss_feed devuelve DataFrame con columnas correctas."""
    from ai_news_digest.scraping.rss_fetch import fetch_rss_feed

    mock_entry = MagicMock()
    mock_entry.get = lambda k, d="": {
        "title": "AI News Title",
        "link": "http://example.com/1",
        "published": "Mon, 01 Jan 2026 00:00:00 +0000",
        "published_parsed": datetime.now(timezone.utc).timetuple(),
        "summary": "Test content about artificial intelligence",
        "content": [],
        "updated_parsed": None,
    }.get(k, d)

    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = [mock_entry]

    with patch("ai_news_digest.scraping.rss_fetch.feedparser.parse", return_value=mock_feed):
        df = fetch_rss_feed("http://fake.feed/rss", "TestSource", days=28)

    assert not df.empty
    assert set(["fuente", "titulo", "url", "fecha", "contenido"]).issubset(df.columns)
    assert df.iloc[0]["fuente"] == "TestSource"


def test_fetch_rss_feed_filtra_articulos_viejos():
    """Los artículos más viejos que `days` no se incluyen."""
    from ai_news_digest.scraping.rss_fetch import fetch_rss_feed

    old_pub = datetime.now(timezone.utc) - timedelta(days=60)

    mock_entry = MagicMock()
    mock_entry.get = lambda k, d="": {
        "title": "Old Article",
        "link": "http://example.com/old",
        "published": "Mon, 01 Jan 2025 00:00:00 +0000",
        "published_parsed": old_pub.timetuple(),
        "summary": "Old content",
        "content": [],
        "updated_parsed": None,
    }.get(k, d)

    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = [mock_entry]

    with patch("ai_news_digest.scraping.rss_fetch.feedparser.parse", return_value=mock_feed):
        df = fetch_rss_feed("http://fake.feed/rss", "TestSource", days=28)

    assert df.empty


def test_fetch_rss_feed_maneja_error_de_red():
    """Retorna DataFrame vacío si feedparser lanza excepción."""
    from ai_news_digest.scraping.rss_fetch import fetch_rss_feed

    with patch("ai_news_digest.scraping.rss_fetch.feedparser.parse", side_effect=Exception("timeout")):
        df = fetch_rss_feed("http://fake.feed/rss", "TestSource", days=28)

    assert df.empty


def test_fetch_rss_feed_ignora_entries_sin_url():
    """Artículos sin URL o título son descartados."""
    from ai_news_digest.scraping.rss_fetch import fetch_rss_feed

    mock_entry = MagicMock()
    mock_entry.get = lambda k, d="": {
        "title": "",
        "link": "",
        "published_parsed": datetime.now(timezone.utc).timetuple(),
        "summary": "content",
        "content": [],
        "updated_parsed": None,
    }.get(k, d)

    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = [mock_entry]

    with patch("ai_news_digest.scraping.rss_fetch.feedparser.parse", return_value=mock_feed):
        df = fetch_rss_feed("http://fake.feed/rss", "TestSource", days=28)

    assert df.empty


# ── Tests de fetch_all_rss_feeds ─────────────────────────────────────────────

def test_fetch_all_rss_feeds_combina_fuentes():
    """fetch_all_rss_feeds combina artículos de múltiples feeds."""
    from ai_news_digest.scraping.rss_fetch import fetch_all_rss_feeds

    def mock_fetch(feed_url, source_name, days):
        return pd.DataFrame([{
            "fuente": source_name, "titulo": f"Article from {source_name}",
            "url": f"http://example.com/{source_name}", "fecha": "", "contenido": "content",
        }])

    feeds = {"Source A": "http://a.com/rss", "Source B": "http://b.com/rss"}

    with patch("ai_news_digest.scraping.rss_fetch.fetch_rss_feed", side_effect=mock_fetch):
        df = fetch_all_rss_feeds(days=28, feeds=feeds)

    assert len(df) == 2
    assert set(df["fuente"].tolist()) == {"Source A", "Source B"}


def test_fetch_all_rss_feeds_deduplica_por_url():
    """Artículos con la misma URL de distintas fuentes se deduplicados."""
    from ai_news_digest.scraping.rss_fetch import fetch_all_rss_feeds

    def mock_fetch(feed_url, source_name, days):
        return pd.DataFrame([{
            "fuente": source_name, "titulo": "Same Article",
            "url": "http://example.com/same", "fecha": "", "contenido": "content",
        }])

    feeds = {"Source A": "http://a.com/rss", "Source B": "http://b.com/rss"}

    with patch("ai_news_digest.scraping.rss_fetch.fetch_rss_feed", side_effect=mock_fetch):
        df = fetch_all_rss_feeds(days=28, feeds=feeds)

    assert len(df) == 1


def test_fetch_all_rss_feeds_retorna_vacio_si_todos_fallan():
    """Retorna DataFrame vacío si todos los feeds fallan."""
    from ai_news_digest.scraping.rss_fetch import fetch_all_rss_feeds

    with patch("ai_news_digest.scraping.rss_fetch.fetch_rss_feed", return_value=pd.DataFrame()):
        df = fetch_all_rss_feeds(days=28, feeds={"Source A": "http://a.com/rss"})

    assert df.empty


def test_rss_feeds_config_es_dict_no_vacio():
    """RSS_FEEDS tiene al menos 5 fuentes configuradas."""
    from ai_news_digest.scraping.rss_fetch import RSS_FEEDS
    assert isinstance(RSS_FEEDS, dict)
    assert len(RSS_FEEDS) >= 5
    assert all(url.startswith("http") for url in RSS_FEEDS.values())
