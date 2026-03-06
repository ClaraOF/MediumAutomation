from dataclasses import dataclass, field
from .config_keys import (
    NEWSAPI_KEY,
    OPENAI_API_KEY,
    OPENAI_MODEL_RELEVANCE,
    OPENAI_MODEL_SUMMARY,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL_RELEVANCE,
    OPENROUTER_MODEL_SUMMARY,
)

@dataclass
class Settings:
    newsapi_key: str = NEWSAPI_KEY

    # OpenAI
    openai_api_key: str = OPENAI_API_KEY
    openai_model_relevance: str = OPENAI_MODEL_RELEVANCE
    openai_model_summary: str = OPENAI_MODEL_SUMMARY

    # OpenRouter
    openrouter_api_key: str = OPENROUTER_API_KEY
    openrouter_model_relevance: str = OPENROUTER_MODEL_RELEVANCE
    openrouter_model_summary: str = OPENROUTER_MODEL_SUMMARY

    # Azure OpenAI (todos opcionales)
    azure_api_key: str = ""
    azure_endpoint: str = ""          # ej: "https://mi-recurso.openai.azure.com/"
    azure_deployment_relevance: str = ""  # nombre del deployment, ej: "gpt-4o-mini"
    azure_deployment_summary: str = ""
    azure_api_version: str = "2024-02-01"

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())

    @property
    def has_azure(self) -> bool:
        return bool(
            self.azure_api_key
            and self.azure_endpoint
            and self.azure_deployment_relevance
            and self.azure_deployment_summary
        )

    @property
    def has_llm(self) -> bool:
        return self.has_openai or self.has_azure or bool(self.openrouter_api_key)

    def validate(self) -> None:
        # No exigimos NEWSAPI si lo tenés desactivado
        pass
