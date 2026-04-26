import pandas as pd
import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_PLOTS = PROJECT_ROOT / "outputs" / "plots"
OUTPUT_MAPS = PROJECT_ROOT / "outputs" / "maps"

st.set_page_config(page_title="Valencia 15 Minutos", layout="wide")

st.title("🏙️ Valencia ciudad de 15 minutos")
st.write(
    """
    Este dashboard analiza la accesibilidad urbana en Valencia
    a partir de servicios básicos obtenidos desde OpenStreetMap.
    """
)

zones = pd.read_csv(DATA_PROCESSED / "zones_clustered.csv")
services = pd.read_csv(DATA_PROCESSED / "services.csv")

col1, col2, col3 = st.columns(3)
col1.metric("Número de zonas", len(zones))
col2.metric("Número de servicios", len(services))
col3.metric("Score medio", f"{zones['score_15min'].mean():.1f}")

st.subheader("📊 Resumen")
st.write("Top 10 zonas con mejor accesibilidad")
st.dataframe(zones.sort_values("score_15min", ascending=False).head(10))

st.write("10 zonas con peor accesibilidad")
st.dataframe(zones.sort_values("score_15min", ascending=True).head(10))

st.subheader("🧩 Distribución por cluster")
cluster_counts = zones["cluster"].value_counts().sort_index()
st.bar_chart(cluster_counts)

st.subheader("🖼️ Gráficos")
st.image(str(OUTPUT_PLOTS / "01_service_counts.png"))
st.image(str(OUTPUT_PLOTS / "02_score_histogram.png"))
st.image(str(OUTPUT_PLOTS / "03_top10_zones.png"))
st.image(str(OUTPUT_PLOTS / "04_bottom10_zones.png"))
st.image(str(OUTPUT_PLOTS / "05_cluster_counts.png"))

st.subheader("🗺️ Mapa interactivo")
html_map = (OUTPUT_MAPS / "valencia_15min_map.html").read_text(encoding="utf-8")
components.html(html_map, height=700, scrolling=True)

st.subheader("📝 Conclusiones orientativas")
st.markdown(
    """
- Las zonas con mayor score tienen más servicios básicos a distancia caminable.
- Las zonas con menor score presentan menor cobertura de servicios.
- El clustering permite agrupar áreas urbanas con patrones de accesibilidad similares.
- El modelo usa una aproximación de 1.200 metros como equivalente a 15 minutos caminando.
"""
)