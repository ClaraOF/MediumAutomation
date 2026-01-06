# %%
from pathlib import Path
from ai_news_digest.config import Settings
from ai_news_digest.pipeline import collect_articles, rank_and_select, summarize_and_build
from datetime import datetime

# %%
# Parámetros de corrida
DAYS = 30
TOP_N = 20 ##15
#ENSURE_SOURCES = [] 
ENSURE_SOURCES = ['Kdnuggets.com']
MONTH_NAME = "Diciembre"
LANG = "es"

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_PATH = "outputs/Highlights_AI" + "_"+ MONTH_NAME + "_" + ts +".txt"
print(f"Output path: {OUT_PATH}")

settings = Settings()

# %%
settings

# %%
print("🔎 [1/4] Recolectando artículos...")
df_all = collect_articles(settings, days=DAYS)
print(f"   → Artículos recolectados: {len(df_all)}")
if df_all.empty:
        print("   ⚠️  No se encontraron artículos.")

df_all.head(5)

# %%
df_all.fuente.value_counts()

# %%
print("📊 [2/4] Rankeando artículos por relevancia...")
df_top = rank_and_select(df_all, settings, top_n=TOP_N, ensure_source=ENSURE_SOURCES)
print(f"   → Seleccionados top {len(df_top)} artículos")

# %%
df_top.fuente.value_counts()

# %%
df_top

# %%
print("📝 [3/4] Generando resúmenes y armando artículo...")
article, df_res = summarize_and_build(df_top, settings, month_name=MONTH_NAME, lang=LANG)
print("   → Resúmenes generados")

# %%
df_res.resumen

# %%
article

# %%
print("💾 [4/4] Guardando resultados...")
Path(OUT_PATH).write_text(article, encoding="utf-8")
csv_path = Path(OUT_PATH).with_suffix(".csv")
csv_path.write_text(df_res.to_csv(index=False), encoding="utf-8")
print(f"   → Guardado {OUT_PATH} y {csv_path.name}")

print("✅ Pipeline finalizado con éxito.")


