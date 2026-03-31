from typing import Dict, Protocol, runtime_checkable


@runtime_checkable
class BaseLLMClient(Protocol):
    def score_relevance(self, title: str, content: str) -> int: ...
    def summarize(self, title: str, url: str, content: str, lang: str = "es") -> Dict[str, str]: ...
