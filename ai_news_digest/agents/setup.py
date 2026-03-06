from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, set_default_openai_client, set_default_openai_api, set_tracing_disabled
from ai_news_digest.config import Settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def configure_agents_llm(settings: Settings) -> str | OpenAIChatCompletionsModel:
    """
    Configura el cliente global del SDK y devuelve el model name a usar en los agentes.
    Prioridad: Azure → OpenAI → OpenRouter.
    """
    if settings.has_azure:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            api_key=settings.azure_api_key,
            azure_endpoint=settings.azure_endpoint,
            api_version=settings.azure_api_version,
        )
        set_default_openai_client(client=client, use_for_tracing=False)
        set_default_openai_api("chat_completions")
        set_tracing_disabled(disabled=True)
        return settings.azure_deployment_summary

    if settings.has_openai:
        # El SDK detecta OPENAI_API_KEY automáticamente — no sobreescribimos el cliente.
        # Tracing disponible para usuarios reales de OpenAI.
        return settings.openai_model_summary

    if settings.openrouter_api_key:
        # OpenRouter usa nombres de modelo con "/" (ej: "google/gemini-2.0-flash-lite-001").
        # El MultiProvider del SDK interpreta el "/" como prefijo de proveedor y falla.
        # Solución: devolver un OpenAIChatCompletionsModel con el cliente embebido,
        # que bypasea el MultiProvider completamente.
        client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=settings.openrouter_api_key,
        )
        set_tracing_disabled(disabled=True)
        return OpenAIChatCompletionsModel(
            model=settings.openrouter_model_summary,
            openai_client=client,
        )

    raise ValueError(
        "No LLM provider configured. "
        "Completá al menos una de: OPENAI_API_KEY, OPENROUTER_API_KEY, o credenciales Azure."
    )
