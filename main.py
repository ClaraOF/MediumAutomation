"""
Entry point del pipeline agéntico de AI News Digest.

Uso básico:
    python main.py --month "OpenAI_Marzo_26"

Parámetros completos:
    python main.py \
        --days 28 \
        --top-n 20 \
        --month "OpenAI_Marzo_26" \
        --lang es \
        --ensure-source Kdnuggets.com \
        --ensure-source TechCrunch \
        --out-path outputs/mi_articulo.txt
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from ai_news_digest.agents import run_agentic_pipeline
from ai_news_digest.config import Settings

# Para volver al pipeline original (sin agentes), reemplazar la línea de arriba por:
# from ai_news_digest.pipeline import collect_articles, rank_and_select, summarize_and_build


def _default_month() -> str:
    """Genera un nombre de mes por defecto basado en la fecha actual (ej: 'Marzo_26')."""
    months_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }
    now = datetime.now()
    return f"{months_es[now.month]}_{str(now.year)[2:]}"


def _build_out_path(month_name: str) -> str:
    """Genera la ruta de salida con timestamp (ej: outputs/Highlights_AI_Marzo_26_20260302_143022.txt)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    return str(out_dir / f"Highlights_AI_{month_name}_{ts}.txt")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un artículo de Medium con las noticias de IA del mes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--days", type=int, default=28,
        help="Ventana de días hacia atrás para recolectar artículos (default: 28).",
    )
    parser.add_argument(
        "--top-n", type=int, default=20, dest="top_n",
        help="Cantidad máxima de artículos a incluir (default: 20).",
    )
    parser.add_argument(
        "--month", type=str, default=None, dest="month_name",
        help="Nombre descriptivo del mes, usado en el título y la ruta de salida "
             "(default: auto-generado, ej: 'Marzo_26'). "
             "Podés usar un nombre descriptivo como 'OpenAI_Marzo_26'.",
    )
    parser.add_argument(
        "--lang", type=str, default="es",
        help="Idioma de los resúmenes: 'es' o 'en' (default: 'es').",
    )
    parser.add_argument(
        "--ensure-source", type=str, action="append", default=[], dest="ensure_sources",
        metavar="SOURCE",
        help="Fuente que debe aparecer al menos una vez en el ranking. "
             "Repetir para múltiples fuentes (ej: --ensure-source Kdnuggets.com --ensure-source TechCrunch).",
    )
    parser.add_argument(
        "--out-path", type=str, default=None, dest="out_path",
        help="Ruta del archivo de salida .txt. Si no se especifica, se auto-genera como "
             "'outputs/Highlights_AI_<month>_<timestamp>.txt'.",
    )
    parser.add_argument(
        "--articles-csv", type=str, default=None, dest="articles_csv",
        metavar="PATH",
        help="CSV de artículos ya recolectados (saltea el paso 1 y no consume NewsAPI). "
             "Usar el .csv generado por una ejecución anterior.",
    )
    parser.add_argument(
        "--exclude-source", type=str, action="append", default=[], dest="exclude_sources",
        metavar="SOURCE",
        help="Fuente a excluir de la recolección (repetible). "
             "Valores válidos: newsapi, techcrunch, rss. "
             "Ej: --exclude-source newsapi --exclude-source techcrunch",
    )
    return parser.parse_args(argv)


def run(argv=None):
    args = parse_args(argv)

    month_name = args.month_name or _default_month()
    out_path = args.out_path or _build_out_path(month_name)

    print(f"[Config] days={args.days}, top_n={args.top_n}, month='{month_name}', lang={args.lang}")
    if args.ensure_sources:
        print(f"[Config] ensure_sources={args.ensure_sources}")
    print(f"[Config] out_path={out_path}")

    if args.articles_csv:
        print(f"[Config] articles_csv={args.articles_csv} (saltando recolección)")
    if args.exclude_sources:
        print(f"[Config] exclude_sources={args.exclude_sources}")

    settings = Settings()
    result = run_agentic_pipeline(
        settings=settings,
        days=args.days,
        top_n=args.top_n,
        month_name=month_name,
        lang=args.lang,
        out_path=out_path,
        ensure_sources=args.ensure_sources,
        articles_csv=args.articles_csv,
        exclude_sources=args.exclude_sources,
    )

    if result.get("status") == "success":
        print(f"\nPipeline completado exitosamente.")
        print(f"  Artículo : {result.get('txt_path')}")
        print(f"  CSV      : {result.get('csv_path')}")
        print(f"  Longitud : {result.get('article_length_chars')} caracteres")
        print(f"  Artículos: {result.get('articles_count')}")
    else:
        print(f"\nPipeline finalizado con estado: {result}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
