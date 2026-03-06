"""
Tests de regresión para la Fase 2: arquitectura agéntica con OpenAI Agents SDK.
No consumen APIs ni hacen requests externos — todo está mockeado.

Ejecutar con:
    python -m pytest tests/test_phase2.py -v
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ai_news_digest.config import Settings


def _call_tool(tool, **kwargs) -> str:
    """Llama una FunctionTool del SDK de forma sincrónica en tests."""
    return asyncio.run(tool.on_invoke_tool(MagicMock(), json.dumps(kwargs)))


# ── Capa 1: Importaciones ────────────────────────────────────────────────────

def test_agents_module_imports():
    from ai_news_digest.agents import run_agentic_pipeline
    assert callable(run_agentic_pipeline)

def test_agents_setup_imports():
    from ai_news_digest.agents.setup import configure_agents_llm
    assert callable(configure_agents_llm)

def test_agents_collector_imports():
    from ai_news_digest.agents.collector import make_collector_agent
    assert callable(make_collector_agent)

def test_agents_ranker_imports():
    from ai_news_digest.agents.ranker import make_ranker_agent
    assert callable(make_ranker_agent)

def test_agents_summarizer_imports():
    from ai_news_digest.agents.summarizer import make_summarizer_agent
    assert callable(make_summarizer_agent)

def test_agents_builder_imports():
    from ai_news_digest.agents.builder import make_builder_agent
    assert callable(make_builder_agent)


# ── Capa 2: configure_agents_llm ────────────────────────────────────────────

def test_configure_agents_llm_openrouter(monkeypatch):
    """Para OpenRouter devuelve un OpenAIChatCompletionsModel (bypasea MultiProvider prefix)."""
    from agents import OpenAIChatCompletionsModel
    monkeypatch.setattr("ai_news_digest.agents.setup.set_tracing_disabled", lambda *a, **kw: None)

    s = Settings(
        openai_api_key="",
        openrouter_api_key="fake-or-key",
        openrouter_model_summary="google/gemini-flash",
    )
    from ai_news_digest.agents.setup import configure_agents_llm
    model = configure_agents_llm(s)
    assert isinstance(model, OpenAIChatCompletionsModel)
    assert model.model == "google/gemini-flash"


def test_configure_agents_llm_openai_no_client_override():
    """Cuando hay key de OpenAI, NO llama set_default_openai_client (el SDK lo detecta solo)."""
    s = Settings(openai_api_key="fake-openai-key", openai_model_summary="gpt-4o-mini")
    from ai_news_digest.agents.setup import configure_agents_llm
    with patch("ai_news_digest.agents.setup.set_default_openai_client") as mock_set:
        model = configure_agents_llm(s)
        mock_set.assert_not_called()
    assert model == "gpt-4o-mini"


def test_configure_agents_llm_raises_without_any_provider():
    """Lanza ValueError cuando no hay ningún proveedor configurado."""
    s = Settings(openai_api_key="", openrouter_api_key="")
    from ai_news_digest.agents.setup import configure_agents_llm
    with pytest.raises(ValueError, match="No LLM provider"):
        configure_agents_llm(s)


def test_configure_agents_llm_azure_priority(monkeypatch):
    """Azure tiene prioridad sobre OpenAI y OpenRouter."""
    monkeypatch.setattr("ai_news_digest.agents.setup.set_default_openai_client", lambda *a, **kw: None)
    monkeypatch.setattr("ai_news_digest.agents.setup.set_default_openai_api", lambda *a, **kw: None)
    monkeypatch.setattr("ai_news_digest.agents.setup.set_tracing_disabled", lambda *a, **kw: None)

    s = Settings(
        azure_api_key="fake-azure",
        azure_endpoint="https://test.openai.azure.com/",
        azure_deployment_relevance="gpt-4o-mini",
        azure_deployment_summary="gpt-4o-mini",
        openai_api_key="fake-openai",
    )
    from ai_news_digest.agents.setup import configure_agents_llm
    model = configure_agents_llm(s)
    assert model == "gpt-4o-mini"


# ── Capa 3: Tools individuales ───────────────────────────────────────────────

def test_score_and_rank_respeta_top_n():
    """score_and_rank devuelve a lo sumo top_n artículos y agrega columna 'relevancia'."""
    from ai_news_digest.agents.ranker import make_ranker_agent

    articles = [
        {"fuente": "TC", "titulo": f"AI Article {i}", "url": f"http://x.com/{i}",
         "contenido": "artificial intelligence machine learning", "fecha": "2026-01-01"}
        for i in range(20)
    ]
    articles_json = json.dumps(articles)

    with patch("ai_news_digest.agents.ranker._get_llm", return_value=None):
        # articles_json se pasa al factory, no a la tool
        agent = make_ranker_agent(model="fake", settings=Settings(), articles_json=articles_json)
        result_json = _call_tool(agent.tools[0], top_n=10)

    result = json.loads(result_json)
    assert len(result) <= 10
    assert all("relevancia" in r for r in result)


def test_score_and_rank_json_vacio():
    """score_and_rank devuelve '[]' si recibe un DataFrame vacío."""
    from ai_news_digest.agents.ranker import make_ranker_agent

    with patch("ai_news_digest.agents.ranker._get_llm", return_value=None):
        agent = make_ranker_agent(model="fake", settings=Settings(), articles_json="[]")
        result_json = _call_tool(agent.tools[0], top_n=10)

    assert json.loads(result_json) == []


def test_summarize_all_articles_preserva_orden():
    """summarize_all_articles preserva el orden de los artículos en el output."""
    from ai_news_digest.agents.summarizer import make_summarizer_agent

    articles = [
        {"fuente": "TC", "titulo": f"Article {i}", "url": f"http://x.com/{i}",
         "contenido": f"Content {i}", "fecha": "2026-01-01", "relevancia": 9 - i}
        for i in range(5)
    ]
    articles_json = json.dumps(articles)

    mock_client = MagicMock()
    mock_client.summarize.side_effect = lambda title, url, content, lang: {
        "titulo_sugerido": f"Summary of {title}",
        "resumen": f"Resumen de {title}",
    }

    with patch("ai_news_digest.agents.summarizer._get_llm", return_value=mock_client), \
         patch("ai_news_digest.agents.summarizer.og_image", return_value=None):
        # articles_json se pasa al factory, la tool solo recibe lang
        agent = make_summarizer_agent(model="fake", settings=Settings(), articles_json=articles_json)
        result_json = _call_tool(agent.tools[0], lang="es")

    result = json.loads(result_json)
    assert len(result) == 5
    for i, row in enumerate(result):
        assert row["titulo"] == f"Article {i}"
    assert all("resumen" in r for r in result)


def test_summarize_all_articles_maneja_fallos_parciales():
    """Ningún artículo se pierde si algunas llamadas LLM fallan."""
    from ai_news_digest.agents.summarizer import make_summarizer_agent

    N = 6
    articles = [
        {"fuente": "TC", "titulo": f"Art {i}", "url": f"http://x.com/{i}",
         "contenido": f"Content {i}", "fecha": "2026-01-01", "relevancia": i}
        for i in range(N)
    ]
    articles_json = json.dumps(articles)

    call_count = [0]
    mock_client = MagicMock()
    def mock_summarize(title, url, content, lang):
        call_count[0] += 1
        if call_count[0] % 2 == 0:
            raise RuntimeError("Simulated LLM failure")
        return {"titulo_sugerido": f"T: {title}", "resumen": f"R: {title}"}
    mock_client.summarize.side_effect = mock_summarize

    with patch("ai_news_digest.agents.summarizer._get_llm", return_value=mock_client), \
         patch("ai_news_digest.agents.summarizer.og_image", return_value=None):
        agent = make_summarizer_agent(model="fake", settings=Settings(), articles_json=articles_json)
        result_json = _call_tool(agent.tools[0], lang="es")

    result = json.loads(result_json)
    assert len(result) == N
    assert all(r["resumen"] for r in result)


def test_build_and_save_crea_archivos(tmp_path):
    """build_and_save escribe los archivos .txt y .csv correctamente."""
    from ai_news_digest.agents.builder import make_builder_agent

    summaries = [{
        "fuente": "TechCrunch",
        "titulo": "Test Article",
        "url": "http://example.com/1",
        "contenido": "Some content",
        "titulo_sugerido": "Suggested Title",
        "resumen": "This is a test summary.",
        "imagen": None,
    }]
    summaries_json = json.dumps(summaries)
    out_path = str(tmp_path / "output.txt")

    # summaries_json se pasa al factory, la tool solo recibe month_name
    agent = make_builder_agent(model="fake", out_path=out_path, summaries_json=summaries_json)
    result_json = _call_tool(agent.tools[0], month_name="Marzo")

    result = json.loads(result_json)
    assert result["status"] == "success"
    assert (tmp_path / "output.txt").exists()
    assert (tmp_path / "output.csv").exists()
    content = (tmp_path / "output.txt").read_text(encoding="utf-8")
    assert "Marzo" in content
    assert "Suggested Title" in content


# ── Capa 4: Orquestador ──────────────────────────────────────────────────────

def _make_sample_json():
    df = pd.DataFrame([{
        "fuente": "TC", "titulo": "A", "url": "http://x.com/1",
        "contenido": "ai content", "fecha": "2026-01-01"
    }])
    return df.to_json(orient="records")


def test_orchestrator_ejecuta_agentes_en_orden():
    """run_agentic_pipeline llama los 4 agentes en el orden correcto."""
    from ai_news_digest.agents.orchestrator import run_agentic_pipeline

    call_order = []
    sample_json = _make_sample_json()

    def mock_run_sync(agent, input, **kwargs):
        call_order.append(agent.name)
        result = MagicMock()
        result.final_output = sample_json
        result.new_items = []
        return result

    with patch("ai_news_digest.agents.orchestrator.Runner.run_sync", side_effect=mock_run_sync), \
         patch("ai_news_digest.agents.orchestrator.configure_agents_llm", return_value="fake-model"), \
         patch("ai_news_digest.agents.orchestrator.make_collector_agent") as mc, \
         patch("ai_news_digest.agents.orchestrator.make_ranker_agent") as mr, \
         patch("ai_news_digest.agents.orchestrator.make_summarizer_agent") as ms, \
         patch("ai_news_digest.agents.orchestrator.make_builder_agent") as mb:

        for mock_f, name in [(mc, "CollectorAgent"), (mr, "RankerAgent"),
                              (ms, "SummarizerAgent"), (mb, "BuilderAgent")]:
            agent = MagicMock()
            agent.name = name
            mock_f.return_value = agent

        run_agentic_pipeline(
            settings=Settings(openai_api_key="", openrouter_api_key="fake"),
            days=7, top_n=5, month_name="Marzo", lang="es", out_path="/tmp/t.txt"
        )

    assert call_order == ["CollectorAgent", "RankerAgent", "SummarizerAgent", "BuilderAgent"]


def test_orchestrator_aborta_sin_articulos():
    """run_agentic_pipeline retorna error si el collector no encuentra artículos."""
    from ai_news_digest.agents.orchestrator import run_agentic_pipeline

    def mock_run_sync(agent, input, **kwargs):
        result = MagicMock()
        result.final_output = "[]"
        result.new_items = []
        return result

    with patch("ai_news_digest.agents.orchestrator.Runner.run_sync", side_effect=mock_run_sync), \
         patch("ai_news_digest.agents.orchestrator.configure_agents_llm", return_value="fake-model"), \
         patch("ai_news_digest.agents.orchestrator.make_collector_agent") as mc:
        agent = MagicMock()
        agent.name = "CollectorAgent"
        mc.return_value = agent

        result = run_agentic_pipeline(
            settings=Settings(openai_api_key="", openrouter_api_key="fake")
        )

    assert result["status"] == "error"
    assert result["reason"] == "no_articles_collected"
