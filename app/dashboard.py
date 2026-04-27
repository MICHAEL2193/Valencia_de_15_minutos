import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_PLOTS = PROJECT_ROOT / "outputs" / "plots"
OUTPUT_MAPS = PROJECT_ROOT / "outputs" / "maps"

st.set_page_config(
    page_title="Valencia ciudad de 15 minutos",
    page_icon="🏙️",
    layout="wide",
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def dedupe_columns(cols: list, dataframe: pd.DataFrame) -> list:
    """
    Devuelve una lista de columnas existentes en el DataFrame
    eliminando duplicados y manteniendo el orden.
    """
    clean_cols = []

    for col in cols:
        if col in dataframe.columns and col not in clean_cols:
            clean_cols.append(col)

    return clean_cols


def load_zones_data() -> pd.DataFrame:
    """
    Carga el dataset más completo disponible.

    Prioridad:
    1. zones_enriched.csv      -> accesibilidad + clustering + vivienda/alquiler
    2. zones_clustered.csv     -> accesibilidad + clustering
    3. zones_accessibility.csv -> solo accesibilidad
    """
    enriched_path = DATA_PROCESSED / "zones_enriched.csv"
    clustered_path = DATA_PROCESSED / "zones_clustered.csv"
    accessibility_path = DATA_PROCESSED / "zones_accessibility.csv"

    if enriched_path.exists():
        return pd.read_csv(enriched_path)

    if clustered_path.exists():
        return pd.read_csv(clustered_path)

    if accessibility_path.exists():
        return pd.read_csv(accessibility_path)

    st.error(
        "No se encontró ningún archivo de zonas procesadas. "
        "Ejecuta primero los scripts de procesamiento."
    )
    st.stop()


def load_services_data() -> pd.DataFrame:
    """
    Carga los servicios descargados desde OpenStreetMap.
    """
    services_path = DATA_PROCESSED / "services.csv"

    if not services_path.exists():
        st.error(
            "No se encontró data/processed/services.csv. "
            "Ejecuta primero src/step1_download_data.py."
        )
        st.stop()

    return pd.read_csv(services_path)


def show_image_if_exists(image_path: Path, caption: str):
    """
    Muestra una imagen solo si existe.
    """
    if image_path.exists():
        st.image(str(image_path), caption=caption, use_container_width=True)


def format_score(value):
    """
    Formatea un score numérico.
    """
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "N/A"


def get_available_profile_scores(zones: pd.DataFrame) -> dict:
    """
    Devuelve los scores disponibles para selector de perfil.
    """
    profile_options = {
        "General": "score_15min",
        "Familia": "score_familia",
        "Estudiante": "score_estudiante",
        "Persona mayor": "score_persona_mayor",
    }

    return {
        profile_name: column
        for profile_name, column in profile_options.items()
        if column in zones.columns
    }


def get_display_columns(zones: pd.DataFrame, selected_score_col: str) -> list:
    """
    Selecciona columnas importantes para mostrar en tablas,
    evitando columnas duplicadas.
    """
    cols = [
        "zone_id",
        "zone_name",
        selected_score_col,
        "score_15min",
        "score_familia",
        "score_estudiante",
        "score_persona_mayor",
        "services_count",
        "cluster",
        "rent_eur_m2",
        "sale_eur_m2",
    ]

    return dedupe_columns(cols, zones)


def get_housing_display_columns(zones: pd.DataFrame, selected_score_col: str) -> list:
    """
    Selecciona columnas para la sección de vivienda/alquiler,
    evitando duplicados.
    """
    cols = [
        "zone_id",
        "zone_name",
        selected_score_col,
        "score_15min",
        "rent_eur_m2",
        "sale_eur_m2",
    ]

    return dedupe_columns(cols, zones)


def get_zone_label(row: pd.Series) -> str:
    """
    Devuelve un nombre legible para una zona.
    """
    if "zone_name" in row and pd.notna(row["zone_name"]):
        return str(row["zone_name"])

    if "zone_id" in row and pd.notna(row["zone_id"]):
        return str(row["zone_id"])

    return "Zona sin nombre"


# ============================================================
# CARGA DE DATOS
# ============================================================

zones = load_zones_data()
services = load_services_data()

available_profiles = get_available_profile_scores(zones)

if not available_profiles:
    st.error(
        "No se encontró ninguna columna de score. "
        "Revisa que existan columnas como score_15min, score_familia, etc."
    )
    st.stop()


# ============================================================
# CABECERA
# ============================================================

st.title("🏙️ Valencia ciudad de 15 minutos")

st.markdown(
    """
Este dashboard analiza la **accesibilidad urbana en Valencia** a partir de servicios básicos
obtenidos desde **OpenStreetMap**.

El objetivo es comprobar qué zonas tienen acceso cercano a servicios esenciales como:

🛒 alimentación · 💊 farmacias · 🏥 salud · 📚 educación · 🌳 parques · 🚌 transporte
"""
)

st.divider()


# ============================================================
# MÉTRICAS PRINCIPALES
# ============================================================

st.subheader("📌 Resumen general del proyecto")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Zonas analizadas", len(zones))
col2.metric("Servicios detectados", len(services))

if "score_15min" in zones.columns:
    col3.metric("Score medio general", f"{zones['score_15min'].mean():.1f}")
else:
    col3.metric("Score medio general", "N/A")

if "cluster" in zones.columns:
    col4.metric("Clusters", zones["cluster"].nunique())
else:
    col4.metric("Clusters", "N/A")


# ============================================================
# SELECTOR DE PERFIL
# ============================================================

st.divider()
st.subheader("👤 Análisis según perfil de usuario")

selected_profile = st.selectbox(
    "Selecciona el perfil para analizar la accesibilidad:",
    list(available_profiles.keys()),
)

selected_score_col = available_profiles[selected_profile]

st.markdown(
    f"""
Perfil seleccionado: **{selected_profile}**  
Columna usada para ordenar resultados: `{selected_score_col}`
"""
)

profile_col1, profile_col2, profile_col3 = st.columns(3)

profile_col1.metric(
    f"Score medio - {selected_profile}",
    format_score(zones[selected_score_col].mean()),
)

profile_col2.metric(
    f"Mejor score - {selected_profile}",
    format_score(zones[selected_score_col].max()),
)

profile_col3.metric(
    f"Peor score - {selected_profile}",
    format_score(zones[selected_score_col].min()),
)


# ============================================================
# TOP Y BOTTOM ZONAS
# ============================================================

st.divider()
st.subheader("🏆 Zonas con mejor y peor accesibilidad")

display_cols = get_display_columns(zones, selected_score_col)

left_col, right_col = st.columns(2)

with left_col:
    st.markdown(f"### ✅ Top 10 zonas para perfil: {selected_profile}")

    top10 = zones.sort_values(
        selected_score_col,
        ascending=False,
    )[display_cols].head(10)

    st.dataframe(top10, use_container_width=True)

with right_col:
    st.markdown(f"### ⚠️ 10 zonas con menor accesibilidad para perfil: {selected_profile}")

    bottom10 = zones.sort_values(
        selected_score_col,
        ascending=True,
    )[display_cols].head(10)

    st.dataframe(bottom10, use_container_width=True)


# ============================================================
# SERVICIOS POR CATEGORÍA
# ============================================================

st.divider()
st.subheader("🧾 Servicios detectados por categoría")

if "categoria" in services.columns:
    service_counts = services["categoria"].value_counts().sort_values(ascending=False)

    col_chart, col_table = st.columns([2, 1])

    with col_chart:
        st.bar_chart(service_counts)

    with col_table:
        service_counts_df = (
            service_counts
            .rename("cantidad")
            .reset_index()
            .rename(columns={"index": "categoria"})
        )

        st.dataframe(service_counts_df, use_container_width=True)
else:
    st.warning("No existe la columna 'categoria' en services.csv.")


# ============================================================
# CLUSTERS
# ============================================================

st.divider()
st.subheader("🧩 Clustering de zonas")

if "cluster" in zones.columns:
    cluster_counts = zones["cluster"].value_counts().sort_index()

    col_cluster_chart, col_cluster_table = st.columns([2, 1])

    with col_cluster_chart:
        st.bar_chart(cluster_counts)

    with col_cluster_table:
        cluster_counts_df = (
            cluster_counts
            .rename("zonas")
            .reset_index()
            .rename(columns={"index": "cluster"})
        )

        st.dataframe(cluster_counts_df, use_container_width=True)

    st.markdown(
        """
Los clusters agrupan zonas con patrones similares de accesibilidad.  
Por ejemplo, puede haber zonas muy completas, zonas con buen transporte pero menos parques,
o zonas con peor cobertura general.
"""
    )
else:
    st.warning("Todavía no existe la columna 'cluster'. Ejecuta src/step4_clustering.py.")


# ============================================================
# ANÁLISIS CON VIVIENDA / ALQUILER
# ============================================================

st.divider()
st.subheader("🏠 Cruce con precio de vivienda o alquiler")

housing_cols = [col for col in ["rent_eur_m2", "sale_eur_m2"] if col in zones.columns]

if housing_cols:
    st.markdown(
        """
Este apartado cruza la accesibilidad urbana con datos de precio de alquiler o compra.
La idea es observar si las zonas con mejor accesibilidad también tienden a tener mayor coste residencial.
"""
    )

    housing_display_cols = get_housing_display_columns(zones, selected_score_col)

    housing_df = zones[housing_display_cols].copy()

    st.dataframe(
        housing_df.sort_values(selected_score_col, ascending=False),
        use_container_width=True,
    )

    if "rent_eur_m2" in zones.columns:
        valid_rent = zones[zones["rent_eur_m2"].notna()].copy()

        if len(valid_rent) > 0:
            st.markdown("### 📈 Relación entre alquiler y accesibilidad")
            st.scatter_chart(
                valid_rent,
                x="rent_eur_m2",
                y=selected_score_col,
            )
        else:
            st.info("No hay datos válidos de alquiler para mostrar el gráfico.")

    if "sale_eur_m2" in zones.columns:
        valid_sale = zones[zones["sale_eur_m2"].notna()].copy()

        if len(valid_sale) > 0:
            st.markdown("### 📈 Relación entre precio de compra y accesibilidad")
            st.scatter_chart(
                valid_sale,
                x="sale_eur_m2",
                y=selected_score_col,
            )
        else:
            st.info("No hay datos válidos de precio de compra para mostrar el gráfico.")
else:
    st.info(
        "Todavía no se han añadido datos de vivienda o alquiler. "
        "Cuando exista data/processed/zones_enriched.csv con columnas "
        "`rent_eur_m2` o `sale_eur_m2`, aparecerá aquí el análisis."
    )


# ============================================================
# GRÁFICOS GENERADOS
# ============================================================

st.divider()
st.subheader("🖼️ Gráficos generados")

plot_files = [
    ("01_service_counts.png", "Número de servicios por categoría"),
    ("02_score_histogram.png", "Distribución del score general de accesibilidad"),
    ("03_top10_zones.png", "Top 10 zonas con mejor accesibilidad"),
    ("04_bottom10_zones.png", "10 zonas con menor accesibilidad"),
    ("05_cluster_counts.png", "Número de zonas por cluster"),
    ("06_score_vs_rent.png", "Relación entre alquiler y accesibilidad"),
    ("07_score_vs_sale.png", "Relación entre precio de compra y accesibilidad"),
]

existing_plots = [
    (file_name, caption)
    for file_name, caption in plot_files
    if (OUTPUT_PLOTS / file_name).exists()
]

if existing_plots:
    for file_name, caption in existing_plots:
        show_image_if_exists(OUTPUT_PLOTS / file_name, caption)
else:
    st.info(
        "No se encontraron gráficos generados. "
        "Ejecuta src/step5_plots.py y, si aplica, src/step7_join_housing.py."
    )


# ============================================================
# MAPA INTERACTIVO
# ============================================================

st.divider()
st.subheader("🗺️ Mapa interactivo")

map_path = OUTPUT_MAPS / "valencia_15min_map.html"

if map_path.exists():
    html_map = map_path.read_text(encoding="utf-8")
    components.html(html_map, height=750, scrolling=True)
else:
    st.warning(
        "No se encontró el mapa interactivo. "
        "Ejecuta primero src/step6_build_map.py."
    )


# ============================================================
# TABLA COMPLETA
# ============================================================

st.divider()
st.subheader("📋 Dataset completo de zonas")

with st.expander("Ver tabla completa"):
    st.dataframe(zones, use_container_width=True)


# ============================================================
# METODOLOGÍA
# ============================================================

st.divider()
st.subheader("🧠 Metodología")

st.markdown(
    """
### 1. Extracción de datos
Se descargaron servicios urbanos desde OpenStreetMap, clasificándolos en categorías:
alimentación, farmacia, salud, educación, parque y transporte.

### 2. Zonas de análisis
El análisis se realiza sobre zonas oficiales de Valencia, como barrios o distritos,
según la configuración del proyecto.

### 3. Accesibilidad
Para cada zona se calcula la distancia al servicio más cercano de cada categoría.
En la versión avanzada, estas distancias se calculan usando rutas reales caminando
sobre la red peatonal de OpenStreetMap.

### 4. Score general
El score general indica cuántas categorías de servicios están accesibles dentro del umbral
definido como ciudad de 15 minutos.

### 5. Score por perfil
Se calculan scores ponderados para distintos perfiles:
- 👨‍👩‍👧 Familia
- 🎓 Estudiante
- 👴 Persona mayor

Cada perfil da más importancia a determinados servicios.

### 6. Clustering
Se aplica KMeans para agrupar zonas con patrones similares de accesibilidad.

### 7. Vivienda y alquiler
Cuando existen datos disponibles, se cruza la accesibilidad con precios de alquiler
o compra por metro cuadrado.

### 8. Visualización
Los resultados se presentan mediante tablas, gráficos y un mapa interactivo.
"""
)


# ============================================================
# LIMITACIONES
# ============================================================

st.divider()
st.subheader("⚠️ Limitaciones del proyecto")

st.markdown(
    """
- OpenStreetMap puede tener datos incompletos o mal etiquetados.
- La calidad de los resultados depende de la calidad de los datos abiertos.
- No se analiza la calidad del servicio, solo su existencia y cercanía.
- No siempre se consideran horarios, capacidad o saturación de los servicios.
- El análisis de vivienda depende de la disponibilidad y calidad de los datos por barrio.
- Las ponderaciones por perfil son una simplificación y podrían mejorarse con encuestas reales.
- La ruta peatonal real puede no capturar barreras urbanas, obras, seguridad o percepción ciudadana.
"""
)


# ============================================================
# MEJORAS FUTURAS
# ============================================================

st.divider()
st.subheader("🚀 Mejoras futuras")

st.markdown(
    """
- Usar datos oficiales de barrios, población y renta media.
- Añadir datos demográficos por barrio.
- Cruzar accesibilidad con renta media, edad media o densidad de población.
- Permitir que el usuario ajuste las ponderaciones de cada perfil.
- Añadir más servicios: centros deportivos, mercados, cultura, zonas verdes, bancos, etc.
- Comparar Valencia con otras ciudades.
- Incorporar horarios de apertura y calidad percibida de servicios.
- Crear una app pública desplegada en Streamlit Cloud.
"""
)