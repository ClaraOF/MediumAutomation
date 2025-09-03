import pandas as pd

def build_medium_article(df_resumenes: pd.DataFrame, month_name: str, intro: str | None = None) -> str:
    texto = f"# 🧠 Los Highlights de {month_name} en Inteligencia Artificial\n\n"
    if intro is None:
        texto += "Te compartimos las noticias más destacadas del mes.\n\n"
    else:
        texto += intro.strip() + "\n\n"

    for _, row in df_resumenes.iterrows():
        titulo = row.get("titulo_sugerido") or row.get("titulo") or "Nota"
        texto += f"### {titulo}\n\n"
        if row.get("imagen"):
            texto += f"![{titulo}]({row['imagen']})\n\n"
        texto += f"{(row.get('resumen') or '').strip()}\n\n---\n\n"

    texto += "¿Querés seguir leyendo más? Volvemos el mes que viene con un nuevo resumen.\n"
    return texto
