import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    newsapi_key: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model_relevance: str = "gpt-4o-mini"
    openai_model_summary: str = "gpt-4o-mini"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model_relevance: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_model_summary: str = "stepfun/step-3.5-flash:free"

    # Azure OpenAI (todos opcionales)
    azure_api_key: str = ""
    azure_endpoint: str = ""
    azure_deployment_relevance: str = ""
    azure_deployment_summary: str = ""
    azure_api_version: str = "2024-02-01"

    def __post_init__(self):
        # Sobreescribir con variables de entorno si están definidas
        self.newsapi_key = os.getenv("NEWSAPI_KEY", self.newsapi_key)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.openai_model_relevance = os.getenv("OPENAI_MODEL_RELEVANCE", self.openai_model_relevance)
        self.openai_model_summary = os.getenv("OPENAI_MODEL_SUMMARY", self.openai_model_summary)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", self.openrouter_api_key)
        self.openrouter_model_relevance = os.getenv("OPENROUTER_MODEL_RELEVANCE", self.openrouter_model_relevance)
        self.openrouter_model_summary = os.getenv("OPENROUTER_MODEL_SUMMARY", self.openrouter_model_summary)
        self.azure_api_key = os.getenv("AZURE_API_KEY", self.azure_api_key)
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT", self.azure_endpoint)
        self.azure_deployment_relevance = os.getenv("AZURE_DEPLOYMENT_RELEVANCE", self.azure_deployment_relevance)
        self.azure_deployment_summary = os.getenv("AZURE_DEPLOYMENT_SUMMARY", self.azure_deployment_summary)
        self.azure_api_version = os.getenv("AZURE_API_VERSION", self.azure_api_version)

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
        pass
