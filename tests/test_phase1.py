"""
Tests de regresión para la Fase 1 del refactor.
Verifican que los cambios no rompieron el comportamiento existente.
No consumen APIs ni hacen requests externos.

Ejecutar con:
    python -m pytest tests/test_phase1.py -v
"""

from ai_news_digest.config import Settings
from ai_news_digest.llm.base import BaseLLMClient
from ai_news_digest.llm.openai_client import OpenAIClient
from ai_news_digest.llm.openrouter import OpenRouterClient
from ai_news_digest.llm.azure_client import AzureOpenAIClient
from ai_news_digest.pipeline import _get_llm


# ── Capa 1: Importaciones ────────────────────────────────────────────────────

def test_imports_pipeline():
    from ai_news_digest.pipeline import collect_articles, rank_and_select, summarize_and_build
    assert callable(collect_articles)
    assert callable(rank_and_select)
    assert callable(summarize_and_build)


def test_imports_llm_clients():
    assert OpenAIClient
    assert OpenRouterClient
    assert AzureOpenAIClient
    assert BaseLLMClient


# ── Capa 2: Protocol ─────────────────────────────────────────────────────────

def test_openai_client_cumple_protocolo():
    assert issubclass(OpenAIClient, BaseLLMClient)

def test_openrouter_client_cumple_protocolo():
    assert issubclass(OpenRouterClient, BaseLLMClient)

def test_azure_client_cumple_protocolo():
    assert issubclass(AzureOpenAIClient, BaseLLMClient)


# ── Capa 3: Settings ─────────────────────────────────────────────────────────

def test_settings_azure_fields_default_vacios():
    s = Settings()
    assert s.azure_api_key == ""
    assert s.azure_endpoint == ""
    assert s.azure_deployment_relevance == ""
    assert s.azure_deployment_summary == ""
    assert s.azure_api_version == "2024-02-01"

def test_settings_has_azure_false_por_defecto():
    s = Settings()
    assert s.has_azure is False

def test_settings_has_azure_true_cuando_completo():
    s = Settings(
        azure_api_key="key",
        azure_endpoint="https://test.openai.azure.com/",
        azure_deployment_relevance="gpt-4o-mini",
        azure_deployment_summary="gpt-4o-mini",
    )
    assert s.has_azure is True

def test_settings_has_azure_false_si_falta_un_campo():
    s = Settings(
        azure_api_key="key",
        azure_endpoint="https://test.openai.azure.com/",
        azure_deployment_relevance="gpt-4o-mini",
        # azure_deployment_summary ausente
    )
    assert s.has_azure is False


# ── Capa 4: _get_llm — selección de proveedor ────────────────────────────────

def test_get_llm_devuelve_none_sin_keys():
    s = Settings(
        openai_api_key="",
        openrouter_api_key="",
    )
    client = _get_llm(s)
    assert client is None

def test_get_llm_devuelve_openrouter_cuando_no_hay_openai():
    s = Settings(
        openai_api_key="",
        openrouter_api_key="fake-openrouter-key",
    )
    client = _get_llm(s)
    assert isinstance(client, OpenRouterClient)

def test_get_llm_prioriza_openai_sobre_openrouter():
    s = Settings(
        openai_api_key="fake-openai-key",
        openrouter_api_key="fake-openrouter-key",
    )
    client = _get_llm(s)
    assert isinstance(client, OpenAIClient)

def test_get_llm_prioriza_azure_sobre_openai():
    s = Settings(
        azure_api_key="fake-azure-key",
        azure_endpoint="https://test.openai.azure.com/",
        azure_deployment_relevance="gpt-4o-mini",
        azure_deployment_summary="gpt-4o-mini",
        openai_api_key="fake-openai-key",
    )
    client = _get_llm(s)
    assert isinstance(client, AzureOpenAIClient)
