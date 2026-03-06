import re

from agents import Runner

from ai_news_digest.agents.builder import make_builder_agent
from ai_news_digest.agents.collector import make_collector_agent
from ai_news_digest.agents.ranker import make_ranker_agent
from ai_news_digest.agents.setup import configure_agents_llm
from ai_news_digest.agents.summarizer import make_summarizer_agent
from ai_news_digest.config import Settings


def _extract_tool_output(result) -> str | None:
    """
    Extrae el output de la primera tool call del resultado del agente.
    Necesario porque algunos modelos (ej: Gemini via OpenRouter) no retransmiten
    el JSON de la tool en su final_output.
    """
    for item in getattr(result, "new_items", []):
        if type(item).__name__ == "ToolCallOutputItem":
            output = getattr(item, "output", None)
            if output:
                return output
    return None


def _get_result_text(result, label: str = "") -> str:
    """
    Retorna el texto más útil de un RunResult:
    primero final_output, luego el output directo de la tool.
    Loguea debug si ninguno tiene contenido.
    """
    raw = getattr(result, "final_output", "") or ""
    if raw.strip():
        return raw

    tool_out = _extract_tool_output(result)
    if tool_out:
        print(f"   [{label}] El LLM no retransmitió el JSON — usando output directo de la tool.")
        return tool_out

    print(f"   [{label}] WARNING: respuesta vacía del agente.")
    print(f"   [{label}]   final_output: {repr(raw[:300])}")
    print(f"   [{label}]   new_items types: {[type(i).__name__ for i in getattr(result, 'new_items', [])]}")
    return ""


def run_agentic_pipeline(
    settings: Settings,
    days: int = 28,
    top_n: int = 20,
    month_name: str = "Marzo",
    lang: str = "es",
    out_path: str = "Highlights_AI.txt",
    ensure_sources: list[str] | None = None,
    articles_csv: str | None = None,
) -> dict:
    """
    Orquesta el pipeline agéntico completo.
    Los datos (JSON de artículos) viajan por closures en los factories —
    el LLM de cada agente solo recibe parámetros simples, no el JSON completo.
    Retorna un dict con status y rutas de los archivos generados.
    """
    import json
    ensure_sources = ensure_sources or []

    # Paso 0: Configurar el cliente LLM del SDK
    model = configure_agents_llm(settings)
    model_name = getattr(model, "model", model)
    print(f"[Orchestrator] Proveedor LLM: {model_name}")

    # Paso 1: Recolectar artículos (o cargar desde CSV)
    if articles_csv:
        print(f"[1/4] Cargando artículos desde {articles_csv} (sin consumir NewsAPI)...")
        import pandas as pd
        df_loaded = pd.read_csv(articles_csv)
        articles_json = df_loaded.to_json(orient="records", force_ascii=False)
        print(f"   -> {len(df_loaded)} artículos cargados desde CSV")
    else:
        print("[1/4] Recolectando artículos...")
        collector = make_collector_agent(model=model, newsapi_key=settings.newsapi_key)
        collect_result = Runner.run_sync(
            collector,
            input=f"Recolectá artículos de IA. Llamá a collect_all_articles con days={days} y max_pages=5.",
        )
        articles_json = _get_result_text(collect_result, label="Collector")

    if not articles_json or articles_json.strip() in ("[]", ""):
        print("   Sin artículos. Abortando.")
        return {"status": "error", "reason": "no_articles_collected"}

    # Validar y contar
    try:
        n_collected = len(json.loads(articles_json))
        print(f"   -> {n_collected} artículos recolectados")
    except Exception:
        print("   WARNING: JSON del collector no es un array válido. Abortando.")
        return {"status": "error", "reason": "no_articles_collected"}

    # Paso 2: Rankear artículos — datos por closure, LLM solo recibe parámetros
    print("[2/4] Rankeando artículos...")
    ensure_sources_json = json.dumps(ensure_sources)
    ranker = make_ranker_agent(model=model, settings=settings, articles_json=articles_json)
    rank_result = Runner.run_sync(
        ranker,
        input=f"Rankea los artículos. Llamá a score_and_rank con top_n={top_n} y ensure_sources_json='{ensure_sources_json}'.",
    )
    ranked_json = _get_result_text(rank_result, label="Ranker")

    if not ranked_json or ranked_json.strip() == "[]":
        print("   WARNING: ranking vacío, usando fallback (top_n sin score).")
        ranked_json = articles_json  # fallback: primeros N artículos

    try:
        n_ranked = len(json.loads(ranked_json))
        print(f"   -> Top {n_ranked} artículos seleccionados")
    except Exception:
        ranked_json = articles_json

    # Paso 3: Resumir artículos — datos por closure, LLM solo recibe idioma
    print("[3/4] Generando resúmenes (paralelo)...")
    summarizer = make_summarizer_agent(model=model, settings=settings, articles_json=ranked_json)
    summ_result = Runner.run_sync(
        summarizer,
        input=f"Resumí los artículos. Llamá a summarize_all_articles con lang='{lang}'.",
    )
    summaries_json = _get_result_text(summ_result, label="Summarizer")

    if not summaries_json or summaries_json.strip() == "[]":
        print("   WARNING: resúmenes vacíos, usando fallback.")
        summaries_json = ranked_json

    try:
        n_summ = len(json.loads(summaries_json))
        print(f"   -> {n_summ} resúmenes generados")
    except Exception:
        summaries_json = ranked_json

    # Paso 4: Construir y guardar — datos por closure, LLM solo recibe month_name
    print("[4/4] Construyendo artículo y guardando...")
    builder = make_builder_agent(model=model, out_path=out_path, summaries_json=summaries_json)
    build_result = Runner.run_sync(
        builder,
        input=f"Construí y guardá el artículo. Llamá a build_and_save con month_name='{month_name}'.",
    )
    build_text = _get_result_text(build_result, label="Builder")

    # Parsear resultado del builder (objeto JSON, no array)
    for candidate in [build_text]:
        if not candidate:
            continue
        for pattern in [candidate, re.search(r'\{.*\}', candidate, re.DOTALL)]:
            text = pattern.group(0) if hasattr(pattern, "group") else pattern
            try:
                status = json.loads(text)
                print(f"[Orchestrator] Finalizado: {status}")
                return status
            except Exception:
                continue

    status = {"status": "done", "raw": build_text[:200] if build_text else ""}
    print(f"[Orchestrator] Finalizado (fallback): {status}")
    return status
