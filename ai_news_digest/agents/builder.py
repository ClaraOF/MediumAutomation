import io
import json
from pathlib import Path

import pandas as pd
from agents import Agent, function_tool

from ai_news_digest.builder.medium import build_medium_article


def make_builder_agent(model, out_path: str, summaries_json: str) -> Agent:
    """
    Factory que crea el BuilderAgent.
    summaries_json se pasa por closure — el LLM solo recibe month_name.
    """

    @function_tool
    def build_and_save(month_name: str) -> str:
        """
        Construye el artículo final de Medium y guarda los archivos en disco.

        Args:
            month_name: Nombre del mes para el encabezado del artículo (ej: 'Marzo').

        Returns:
            JSON con status, rutas de archivos generados y estadísticas.
        """
        df = pd.read_json(io.StringIO(summaries_json), orient="records")
        article_text = build_medium_article(df, month_name=month_name)

        txt_path = Path(out_path)
        csv_path = txt_path.with_suffix(".csv")

        txt_path.write_text(article_text, encoding="utf-8")
        csv_path.write_text(df.to_csv(index=False), encoding="utf-8")

        return json.dumps({
            "status": "success",
            "txt_path": str(txt_path),
            "csv_path": str(csv_path),
            "article_length_chars": len(article_text),
            "articles_count": len(df),
        })

    return Agent(
        name="BuilderAgent",
        model=model,
        instructions=(
            "Sos un agente que construye artículos de Medium. "
            "Llamá a build_and_save con exactamente el valor de month_name que te pasen, sin modificarlo ni validarlo. "
            "Devolvé el output de la tool directamente, sin modificarlo."
        ),
        tools=[build_and_save],
    )
