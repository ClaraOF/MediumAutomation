import json as _json
import re as _re
from typing import Dict

from openai import OpenAI

from ai_news_digest.prompts import BATCH_RELEVANCE_PROMPT, RELEVANCE_PROMPT, SUMMARY_PROMPT


class AzureOpenAIClient:
    def __init__(self, api_key: str, endpoint: str, deployment_relevance: str, deployment_summary: str, api_version: str = ""):
        self.client = OpenAI(
            api_key=api_key,
            base_url=endpoint,
        )
        self.deployment_relevance = deployment_relevance
        self.deployment_summary = deployment_summary
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def _track_usage(self, resp):
        if resp.usage:
            self.total_prompt_tokens += resp.usage.prompt_tokens or 0
            self.total_completion_tokens += resp.usage.completion_tokens or 0

    def token_summary(self) -> str:
        total = self.total_prompt_tokens + self.total_completion_tokens
        return (
            f"Tokens usados — prompt: {self.total_prompt_tokens:,} | "
            f"completion: {self.total_completion_tokens:,} | "
            f"total: {total:,}"
        )

    def score_relevance(self, title: str, content: str) -> int:
        prompt = RELEVANCE_PROMPT.format(
            title=title or "",
            content_snippet=(content or "")[:1500]
        )
        resp = self.client.chat.completions.create(
            model=self.deployment_relevance,
            messages=[
                {"role": "system", "content": "Sos un analista de IA que clasifica artículos por relevancia."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        self._track_usage(resp)
        msg = resp.choices[0].message.content.strip()
        digits = "".join(ch for ch in msg if ch.isdigit())
        return int(digits[:2]) if digits else 0

    def score_relevance_batch(self, articles: list[tuple[str, str]]) -> list[int]:
        """Puntúa una lista de (titulo, contenido) en una sola llamada al LLM."""
        if not articles:
            return []
        articles_text = "\n".join(
            f"{i + 1}. Title: {(title or '')[:120]}\n   Snippet: {(snippet or '')[:200]}"
            for i, (title, snippet) in enumerate(articles)
        )
        prompt = BATCH_RELEVANCE_PROMPT.format(n=len(articles), articles_list=articles_text)
        try:
            resp = self.client.chat.completions.create(
                model=self.deployment_relevance,
                messages=[
                    {"role": "system", "content": "You are an AI content analyst. Respond only with a JSON array of integers."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            self._track_usage(resp)
            msg = resp.choices[0].message.content.strip()
            match = _re.search(r'\[[\d\s,]+\]', msg)
            if match:
                scores = _json.loads(match.group(0))
                if len(scores) == len(articles):
                    return [max(1, min(10, int(s))) for s in scores]
        except Exception as e:
            print(f"   [AzureClient] Error en batch scoring: {e}")
        return [0] * len(articles)

    def summarize(self, title: str, url: str, content: str, lang: str = "es") -> Dict[str, str]:
        prompt = SUMMARY_PROMPT.format(
            lang=lang,
            url=url or "",
            title=title or "",
            content_snippet=(content or "")[:2000]
        )
        resp = self.client.chat.completions.create(
            model=self.deployment_summary,
            messages=[
                {"role": "system", "content": "Sos un redactor técnico especializado en IA."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        self._track_usage(resp)
        txt = resp.choices[0].message.content.strip()
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        title_guess = lines[0].strip("#:- ")[:140] if lines else (title or "Artículo")
        return {"titulo_sugerido": title_guess, "resumen": txt}
