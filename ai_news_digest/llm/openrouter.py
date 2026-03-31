import json as _json
import re as _re

import requests
import backoff
from ..prompts import BATCH_RELEVANCE_PROMPT, RELEVANCE_PROMPT, SUMMARY_PROMPT


def _parse_batch_scores(text: str, n: int) -> list[int] | None:
    """Parsea la respuesta del LLM para batch scoring. Retorna None si falla."""
    match = _re.search(r'\[[\d\s,]+\]', text)
    if not match:
        return None
    try:
        scores = _json.loads(match.group(0))
        if len(scores) == n:
            return [max(1, min(10, int(s))) for s in scores]
    except Exception:
        pass
    return None

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterClient:
    def __init__(self, api_key: str, model_relevance: str, model_summary: str):
        self.api_key = api_key
        self.model_relevance = model_relevance
        self.model_summary = model_summary
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local-script",
            "X-Title": "AI News Digest"
        }

    def _track_usage(self, response_json: dict):
        usage = response_json.get("usage", {})
        self.total_prompt_tokens += usage.get("prompt_tokens", 0)
        self.total_completion_tokens += usage.get("completion_tokens", 0)

    def token_summary(self) -> str:
        total = self.total_prompt_tokens + self.total_completion_tokens
        return (
            f"Tokens usados — prompt: {self.total_prompt_tokens:,} | "
            f"completion: {self.total_completion_tokens:,} | "
            f"total: {total:,}"
        )

    @backoff.on_exception(backoff.expo, (requests.exceptions.RequestException,), max_tries=3)
    def score_relevance(self, title: str, content: str) -> int:
        if not self.api_key:
            return 0
        prompt = RELEVANCE_PROMPT.format(
            title=title or "",
            content_snippet=(content or "")[:1500]
        )
        payload = {
            "model": self.model_relevance,
            "messages": [
                {"role":"system","content":"Sos un analista de IA que clasifica artículos por relevancia."},
                {"role":"user","content": prompt}
            ],
            "temperature": 0.0,
        }
        r = requests.post(OPENROUTER_ENDPOINT, headers=self._headers(), json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        self._track_usage(data)
        msg = data["choices"][0]["message"]["content"].strip()
        digits = "".join(ch for ch in msg if ch.isdigit())
        return int(digits[:2]) if digits else 0

    def score_relevance_batch(self, articles: list[tuple[str, str]]) -> list[int]:
        """
        Puntúa una lista de (titulo, contenido) en una sola llamada al LLM.
        Retorna lista de scores 1-10 en el mismo orden que `articles`.
        Si el LLM falla o devuelve una respuesta no parseable, retorna lista de ceros.
        """
        if not articles:
            return []
        articles_text = "\n".join(
            f"{i + 1}. Title: {(title or '')[:120]}\n   Snippet: {(snippet or '')[:200]}"
            for i, (title, snippet) in enumerate(articles)
        )
        prompt = BATCH_RELEVANCE_PROMPT.format(n=len(articles), articles_list=articles_text)
        payload = {
            "model": self.model_relevance,
            "messages": [
                {"role": "system", "content": "You are an AI content analyst. Respond only with a JSON array of integers."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
        }
        try:
            r = requests.post(OPENROUTER_ENDPOINT, headers=self._headers(), json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            self._track_usage(data)
            msg = data["choices"][0]["message"]["content"].strip()
            scores = _parse_batch_scores(msg, len(articles))
            if scores is not None:
                return scores
        except Exception:
            pass
        return [0] * len(articles)

    @backoff.on_exception(backoff.expo, (requests.exceptions.RequestException,), max_tries=5, max_time=120)
    def summarize(self, title: str, url: str, content: str, lang: str = "es"):
        if not self.api_key:
            return {
                "titulo_sugerido": title,
                "resumen": f"(Sin LLM) {(content or '')[:400]}...\nSeguí leyendo: {url}"
            }
        prompt = SUMMARY_PROMPT.format(
            lang=lang,
            url=url or "",
            title=title or "",
            content_snippet=(content or "")[:2000]
        )
        payload = {
            "model": self.model_summary,
            "messages": [
                {"role":"system","content":"Sos un redactor técnico especializado en IA."},
                {"role":"user","content": prompt}
            ],
            "temperature": 0.7,
        }
        r = requests.post(OPENROUTER_ENDPOINT, headers=self._headers(), json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        self._track_usage(data)
        txt = data["choices"][0]["message"]["content"].strip()
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        title_guess = lines[0].strip("#:- ")[:140] if lines else title
        return {"titulo_sugerido": title_guess, "resumen": txt}
