from dataclasses import dataclass
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

    @property
    def has_llm(self) -> bool:
        # Sólo consideramos OpenAI si defini la api key
        return bool(self.openai_api_key not in (None, "", "PONER_AQUI"))
    # def has_llm(self) -> bool:
    #     # Sólo consideramos OpenAI
    #     return bool(self.openai_api_key)

    def validate(self) -> None:
        # No exigimos NEWSAPI si lo tenés desactivado
        pass
