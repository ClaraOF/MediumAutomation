import requests
import backoff
from ..prompts import RELEVANCE_PROMPT, SUMMARY_PROMPT

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterClient:
    def __init__(self, api_key: str, model_relevance: str, model_summary: str):
        self.api_key = api_key
        self.model_relevance = model_relevance
        self.model_summary = model_summary

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local-script",
            "X-Title": "AI News Digest"
        }

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
                #{"role":"system","content":"Respondé con un entero 0..10. Sin comentarios."},
                {"role":"system","content":"Sos un analista de IA que clasifica artículos por relevancia."},
                {"role":"user","content": prompt}
            ],
            "temperature": 0.0,
        }
        r = requests.post(OPENROUTER_ENDPOINT, headers=self._headers(), json=payload, timeout=60)
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]["content"].strip()
        digits = "".join(ch for ch in msg if ch.isdigit())
        return int(digits[:2]) if digits else 0

    @backoff.on_exception(backoff.expo, (requests.exceptions.RequestException,), max_tries=3)
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
        txt = r.json()["choices"][0]["message"]["content"].strip()
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        title_guess = lines[0].strip("#:- ")[:140] if lines else title
        return {"titulo_sugerido": title_guess, "resumen": txt}
