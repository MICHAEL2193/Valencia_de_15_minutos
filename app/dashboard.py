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

zones_path = DATA_PROCESSED / "zones_clustered.csv"
services_path = DATA_PROCESSED / "services.csv"
map_path = OUTPUT_MAPS / "valencia_15min_map.html"

if not zones_path.exists() or not services_path.exists():
    st.error(
        "No se encontraron los datos procesados. Ejecuta primero los scripts del pipeline."
    )
    st.stop()

zones = pd.read_csv(zones_path)
services = pd.read_csv(services_path)

tab_resumen, tab_graficos, tab_mapa = st.tabs(["📊 Resumen", "🖼️ Gráficos", "🗺️ Mapa"])

with tab_resumen:
    col1, col2, col3 = st.columns(3)
    col1.metric("Número de zonas", len(zones))
    col2.metric("Número de servicios", len(services))

    score_medio = zones["score_15min"].mean() if "score_15min" in zones.columns else 0
    col3.metric("Score medio", f"{score_medio:.1f}")

    display_cols = ["zone_id", "zone_name", "score_15min", "services_count", "cluster"]
    display_cols = [col for col in display_cols if col in zones.columns]

    if "score_15min" in zones.columns and display_cols:
        st.write("Top 10 barrios/distritos con mejor accesibilidad")
        st.dataframe(
            zones.sort_values("score_15min", ascending=False)[display_cols].head(10),
            use_container_width=True,
        )

        st.write("10 barrios/distritos con peor accesibilidad")
        st.dataframe(
            zones.sort_values("score_15min", ascending=True)[display_cols].head(10),
            use_container_width=True,
        )
    else:
        st.warning("No hay columnas suficientes para mostrar el ranking de accesibilidad.")

    st.subheader("🧩 Distribución por cluster")
    if "cluster" in zones.columns:
        cluster_counts = zones["cluster"].value_counts().sort_index()
        st.bar_chart(cluster_counts)
    else:
        st.warning("No se encontró la columna 'cluster' en zonas.")

with tab_graficos:
    plot_files = [
        "01_service_counts.png",
        "02_score_histogram.png",
        "03_top10_zones.png",
        "04_bottom10_zones.png",
        "05_cluster_counts.png",
    ]
    for plot_name in plot_files:
        plot_path = OUTPUT_PLOTS / plot_name
        if plot_path.exists():
            st.image(str(plot_path))
        else:
            st.info(f"No existe aún: {plot_name}")

with tab_mapa:
    if map_path.exists():
        html_map = map_path.read_text(encoding="utf-8")
        components.html(html_map, height=700, scrolling=True)
    else:
        st.warning("No existe el mapa interactivo. Ejecuta `src/step6_build_map.py`.")

st.subheader("📝 Conclusiones orientativas")
st.markdown(
    """
- Las zonas con mayor score tienen más servicios básicos a distancia caminable.
- Las zonas con menor score presentan menor cobertura de servicios.
- El clustering agrupa áreas urbanas con patrones de accesibilidad similares.
- El modelo usa una aproximación de 1.200 metros como equivalente a 15 minutos caminando.
"""
)