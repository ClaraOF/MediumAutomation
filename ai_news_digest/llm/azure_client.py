from typing import Dict
from openai import AzureOpenAI
from ai_news_digest.prompts import RELEVANCE_PROMPT, SUMMARY_PROMPT


class AzureOpenAIClient:
    def __init__(self, api_key: str, endpoint: str, deployment_relevance: str, deployment_summary: str, api_version: str = "2024-02-01"):
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self.deployment_relevance = deployment_relevance
        self.deployment_summary = deployment_summary

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
        msg = resp.choices[0].message.content.strip()
        digits = "".join(ch for ch in msg if ch.isdigit())
        return int(digits[:2]) if digits else 0

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
        txt = resp.choices[0].message.content.strip()
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        title_guess = lines[0].strip("#:- ")[:140] if lines else (title or "Artículo")
        return {"titulo_sugerido": title_guess, "resumen": txt}
