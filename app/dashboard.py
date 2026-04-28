import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_MAPS = PROJECT_ROOT / "outputs" / "maps"

st.set_page_config(
    page_title="Valencia ciudad de 15 minutos",
    page_icon="🏙️",
    layout="wide",
)


# ============================================================
# FUNCIONES DE CARGA Y LIMPIEZA
# ============================================================

def dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina columnas duplicadas manteniendo la primera aparición."""
    return df.loc[:, ~df.columns.duplicated()].copy()


def dedupe_column_list(cols: list, df: pd.DataFrame) -> list:
    """Devuelve columnas existentes, sin duplicados y manteniendo el orden."""
    clean_cols = []

    for col in cols:
        if col in df.columns and col not in clean_cols:
            clean_cols.append(col)

    return clean_cols


@st.cache_data
def load_zones_data() -> pd.DataFrame:
    """
    Carga el dataset más completo disponible.

    Prioridad:
    1. zones_enriched.csv      -> accesibilidad + clustering + vivienda
    2. zones_clustered.csv     -> accesibilidad + clustering
    3. zones_accessibility.csv -> accesibilidad
    """
    enriched_path = DATA_PROCESSED / "zones_enriched.csv"
    clustered_path = DATA_PROCESSED / "zones_clustered.csv"
    accessibility_path = DATA_PROCESSED / "zones_accessibility.csv"

    if enriched_path.exists():
        return dedupe_columns(pd.read_csv(enriched_path))

    if clustered_path.exists():
        return dedupe_columns(pd.read_csv(clustered_path))

    if accessibility_path.exists():
        return dedupe_columns(pd.read_csv(accessibility_path))

    st.error(
        "No se encontró ningún archivo de zonas procesadas. "
        "Ejecuta primero los scripts del proyecto."
    )
    st.stop()


@st.cache_data
def load_services_data() -> pd.DataFrame:
    """Carga el dataset de servicios obtenido desde OpenStreetMap."""
    services_path = DATA_PROCESSED / "services.csv"

    if not services_path.exists():
        st.error(
            "No se encontró data/processed/services.csv. "
            "Ejecuta primero src/step1_download_data.py."
        )
        st.stop()

    return dedupe_columns(pd.read_csv(services_path))


def format_score(value):
    """Formatea valores numéricos con un decimal."""
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "N/A"


def safe_float(value):
    """Convierte valores a float de forma segura."""
    try:
        if pd.isna(value):
            return np.nan
        return float(value)
    except Exception:
        return np.nan


def get_available_profile_scores(zones: pd.DataFrame) -> dict:
    """Devuelve los scores disponibles para el selector de perfil."""
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


def get_housing_columns(zones: pd.DataFrame):
    """
    Devuelve columnas de vivienda para gráficos.

    Se prefieren columnas limpias si existen:
    - rent_eur_m2_clean
    - sale_eur_m2_clean
    """
    rent_col = None
    sale_col = None

    if "rent_eur_m2_clean" in zones.columns:
        rent_col = "rent_eur_m2_clean"
    elif "rent_eur_m2" in zones.columns:
        rent_col = "rent_eur_m2"

    if "sale_eur_m2_clean" in zones.columns:
        sale_col = "sale_eur_m2_clean"
    elif "sale_eur_m2" in zones.columns:
        sale_col = "sale_eur_m2"

    return rent_col, sale_col


def get_display_columns(zones: pd.DataFrame, selected_score_col: str) -> list:
    """Columnas para tablas principales."""
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
        "rent_eur_m2_clean",
        "sale_eur_m2_clean",
        "has_housing_data",
        "housing_data_status",
    ]

    return dedupe_column_list(cols, zones)


# ============================================================
# FUNCIONES PARA ANALIZAR PATRONES DE CLUSTERS
# ============================================================

SERVICE_LABELS = {
    "alimentacion": "Alimentación",
    "farmacia": "Farmacia",
    "salud": "Salud",
    "educacion": "Educación",
    "parque": "Parques",
    "transporte": "Transporte",
}


def get_cluster_distance_columns(df: pd.DataFrame) -> list:
    """
    Detecta las columnas de distancia disponibles.

    Prioridad:
    1. walkdist_*  -> distancias reales caminando
    2. dist_*      -> distancias calculadas anteriormente
    """
    walk_cols = [col for col in df.columns if col.startswith("walkdist_")]
    dist_cols = [col for col in df.columns if col.startswith("dist_")]

    if walk_cols:
        return walk_cols

    return dist_cols


def clean_service_name(distance_col: str) -> str:
    """Convierte una columna técnica en un nombre de servicio legible."""
    service = distance_col.replace("walkdist_", "").replace("dist_", "")
    return SERVICE_LABELS.get(service, service.capitalize())


def build_cluster_distance_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea una matriz con la distancia media de cada servicio por cluster.

    Filas:
    - cluster

    Columnas:
    - alimentación
    - farmacia
    - salud
    - educación
    - parques
    - transporte
    """
    if "cluster" not in df.columns:
        return pd.DataFrame()

    distance_cols = get_cluster_distance_columns(df)

    if not distance_cols:
        return pd.DataFrame()

    work_df = df.copy()
    work_df["cluster"] = pd.to_numeric(work_df["cluster"], errors="coerce")
    work_df = work_df.dropna(subset=["cluster"])
    work_df["cluster"] = work_df["cluster"].astype(int)

    for col in distance_cols:
        work_df[col] = pd.to_numeric(work_df[col], errors="coerce")

    matrix = (
        work_df
        .groupby("cluster")[distance_cols]
        .mean()
        .reset_index()
    )

    rename_map = {
        col: clean_service_name(col)
        for col in distance_cols
    }

    matrix = matrix.rename(columns=rename_map)

    return matrix


def build_cluster_pattern_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye una tabla interpretativa por cluster.

    Incluye:
    - número de barrios
    - score medio
    - servicios medios accesibles
    - servicio más cercano de media
    - servicio más lejano de media
    - tipo de patrón
    - posibles carencias
    - barrios ejemplo
    """
    if "cluster" not in df.columns:
        return pd.DataFrame()

    distance_cols = get_cluster_distance_columns(df)

    if not distance_cols:
        return pd.DataFrame()

    work_df = df.copy()
    work_df["cluster"] = pd.to_numeric(work_df["cluster"], errors="coerce")
    work_df = work_df.dropna(subset=["cluster"])
    work_df["cluster"] = work_df["cluster"].astype(int)

    for col in distance_cols:
        work_df[col] = pd.to_numeric(work_df[col], errors="coerce")

    if "score_15min" in work_df.columns:
        work_df["score_15min"] = pd.to_numeric(
            work_df["score_15min"],
            errors="coerce",
        )

    if "services_count" in work_df.columns:
        work_df["services_count"] = pd.to_numeric(
            work_df["services_count"],
            errors="coerce",
        )

    rows = []

    for cluster_id, group in work_df.groupby("cluster"):
        row = {}
        row["cluster"] = int(cluster_id)
        row["barrios"] = len(group)

        if "score_15min" in group.columns:
            row["score_medio"] = round(group["score_15min"].mean(), 1)
        else:
            row["score_medio"] = np.nan

        if "services_count" in group.columns:
            row["servicios_medios_accesibles"] = round(
                group["services_count"].mean(),
                1,
            )
        else:
            row["servicios_medios_accesibles"] = np.nan

        service_distances = {}

        for col in distance_cols:
            service_name = clean_service_name(col)
            service_distances[service_name] = group[col].mean()

        valid_distances = {
            service: value
            for service, value in service_distances.items()
            if pd.notna(value)
        }

        if valid_distances:
            closest_service = min(valid_distances, key=valid_distances.get)
            farthest_service = max(valid_distances, key=valid_distances.get)

            row["servicio_mas_cercano_media"] = (
                f"{closest_service} ({valid_distances[closest_service]:.0f} m)"
            )

            row["servicio_mas_lejano_media"] = (
                f"{farthest_service} ({valid_distances[farthest_service]:.0f} m)"
            )
        else:
            row["servicio_mas_cercano_media"] = "No disponible"
            row["servicio_mas_lejano_media"] = "No disponible"

        score = row["score_medio"]

        far_services = [
            service
            for service, value in valid_distances.items()
            if pd.notna(value) and value > 1200
        ]

        if pd.isna(score):
            row["tipo_patron"] = "Sin patrón definido"
        elif score >= 85 and len(far_services) == 0:
            row["tipo_patron"] = "Alta accesibilidad equilibrada"
        elif score >= 85 and len(far_services) > 0:
            row["tipo_patron"] = "Alta accesibilidad con alguna carencia puntual"
        elif score >= 65:
            row["tipo_patron"] = "Accesibilidad media-alta"
        elif score >= 40:
            row["tipo_patron"] = "Accesibilidad desigual"
        elif score >= 20:
            row["tipo_patron"] = "Baja accesibilidad"
        else:
            row["tipo_patron"] = "Muy baja accesibilidad / zona periférica"

        if far_services:
            row["posibles_carencias"] = ", ".join(far_services)
        else:
            row["posibles_carencias"] = "Sin carencias medias superiores a 1.200 m"

        if "zone_name" in group.columns:
            row["barrios_ejemplo"] = ", ".join(
                group["zone_name"]
                .dropna()
                .astype(str)
                .head(8)
            )
        else:
            row["barrios_ejemplo"] = ""

        rows.append(row)

    result = pd.DataFrame(rows)

    return result.sort_values("cluster").reset_index(drop=True)


def build_cluster_distance_long_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea una tabla larga con:
    - cluster
    - servicio
    - distancia media
    - distancia mínima
    - distancia máxima
    """
    if "cluster" not in df.columns:
        return pd.DataFrame()

    distance_cols = get_cluster_distance_columns(df)

    if not distance_cols:
        return pd.DataFrame()

    work_df = df.copy()
    work_df["cluster"] = pd.to_numeric(work_df["cluster"], errors="coerce")
    work_df = work_df.dropna(subset=["cluster"])
    work_df["cluster"] = work_df["cluster"].astype(int)

    rows = []

    for cluster_id, group in work_df.groupby("cluster"):
        for col in distance_cols:
            service_name = clean_service_name(col)
            values = pd.to_numeric(group[col], errors="coerce").dropna()

            if len(values) == 0:
                continue

            rows.append(
                {
                    "cluster": int(cluster_id),
                    "servicio": service_name,
                    "distancia_media_m": round(values.mean(), 0),
                    "distancia_minima_m": round(values.min(), 0),
                    "distancia_maxima_m": round(values.max(), 0),
                }
            )

    return pd.DataFrame(rows)


def create_cluster_distance_heatmap(df: pd.DataFrame):
    """
    Crea un heatmap con la distancia media por servicio y cluster.
    """
    matrix = build_cluster_distance_matrix(df)

    if matrix.empty:
        return None

    matrix_plot = matrix.copy()
    matrix_plot = matrix_plot.set_index("cluster")

    z_values = matrix_plot.values
    x_labels = matrix_plot.columns.tolist()
    y_labels = matrix_plot.index.astype(str).tolist()

    text_values = np.vectorize(lambda x: f"{x:.0f} m")(z_values)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            text=text_values,
            texttemplate="%{text}",
            colorscale="RdYlGn_r",
            colorbar=dict(title="Distancia media"),
            hovertemplate=(
                "<b>Cluster:</b> %{y}<br>"
                "<b>Servicio:</b> %{x}<br>"
                "<b>Distancia media:</b> %{z:.0f} m"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="Distancia media por servicio y cluster",
        template="plotly_white",
        height=430,
        margin=dict(l=20, r=20, t=70, b=40),
    )

    fig.update_xaxes(title_text="Servicio")
    fig.update_yaxes(title_text="Cluster")

    return fig


# ============================================================
# FUNCIONES DE GRÁFICOS
# ============================================================

def build_price_hover(row, price_label, price_col, selected_profile, selected_score_col):
    """Tooltip informativo para gráficos de vivienda."""
    zone_name = row.get("zone_name", "Sin nombre")
    zone_id = row.get("zone_id", "N/A")
    price_value = safe_float(row.get(price_col, np.nan))
    score_value = safe_float(row.get(selected_score_col, np.nan))
    score_general = safe_float(row.get("score_15min", np.nan))
    services_count = row.get("services_count", "N/A")
    cluster = row.get("cluster", "N/A")
    rent_original = safe_float(row.get("rent_eur_m2", np.nan))
    sale_original = safe_float(row.get("sale_eur_m2", np.nan))

    hover = (
        f"<b>Barrio:</b> {zone_name}<br>"
        f"<b>ID zona:</b> {zone_id}<br>"
        f"<b>{price_label}:</b> {price_value:.2f} €/m²<br>"
        f"<b>Accesibilidad {selected_profile}:</b> {score_value:.2f}/100<br>"
    )

    if pd.notna(score_general):
        hover += f"<b>Accesibilidad general:</b> {score_general:.2f}/100<br>"

    hover += f"<b>Servicios cercanos:</b> {services_count}<br>"
    hover += f"<b>Cluster:</b> {cluster}<br>"

    if pd.notna(rent_original):
        hover += f"<b>Alquiler original:</b> {rent_original:.2f} €/m²<br>"

    if pd.notna(sale_original):
        hover += f"<b>Compra original:</b> {sale_original:.2f} €/m²<br>"

    return hover


def create_price_accessibility_scatter(
    df: pd.DataFrame,
    price_col: str,
    price_label: str,
    selected_score_col: str,
    selected_profile: str,
    show_trend: bool,
):
    """
    Gráfico de dispersión:
    X = precio alquiler/compra
    Y = accesibilidad.

    Cada punto representa un barrio.
    """
    if price_col not in df.columns or selected_score_col not in df.columns:
        return None

    plot_df = df.copy()
    plot_df[price_col] = pd.to_numeric(plot_df[price_col], errors="coerce")
    plot_df[selected_score_col] = pd.to_numeric(
        plot_df[selected_score_col],
        errors="coerce",
    )

    plot_df = plot_df.dropna(
        subset=[price_col, selected_score_col, "zone_name"]
    ).copy()

    if len(plot_df) == 0:
        return None

    plot_df = plot_df.sort_values(price_col).copy()

    hover_texts = [
        build_price_hover(
            row=row,
            price_label=price_label,
            price_col=price_col,
            selected_profile=selected_profile,
            selected_score_col=selected_score_col,
        )
        for _, row in plot_df.iterrows()
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df[price_col],
            y=plot_df[selected_score_col],
            mode="markers",
            name="Barrio",
            marker=dict(
                size=12,
                color="#3366CC",
                opacity=0.78,
                line=dict(width=0.8, color="white"),
            ),
            hovertext=hover_texts,
            hoverinfo="text",
            cliponaxis=False,
        )
    )

    if show_trend and len(plot_df) >= 6:
        trend_df = plot_df[[price_col, selected_score_col]].dropna()
        trend_df = trend_df.sort_values(price_col).copy()

        window = max(3, min(9, len(trend_df) // 5))
        trend_df["trend"] = trend_df[selected_score_col].rolling(
            window=window,
            center=True,
        ).mean()

        trend_df = trend_df.dropna(subset=["trend"])

        if len(trend_df) > 1:
            fig.add_trace(
                go.Scatter(
                    x=trend_df[price_col],
                    y=trend_df["trend"],
                    mode="lines",
                    name="Tendencia suavizada",
                    line=dict(width=3, color="#F28E2B"),
                    hovertemplate=(
                        f"<b>{price_label}:</b> %{{x:.2f}} €/m²<br>"
                        f"<b>Tendencia accesibilidad:</b> %{{y:.2f}}/100"
                        "<extra></extra>"
                    ),
                    cliponaxis=False,
                )
            )

    fig.update_layout(
        title=f"{price_label} vs accesibilidad ({selected_profile})",
        template="plotly_white",
        height=560,
        margin=dict(l=30, r=30, t=90, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(
        title_text=f"{price_label} (€/m²)",
        showgrid=True,
        automargin=True,
    )

    fig.update_yaxes(
        title_text=f"Accesibilidad {selected_profile} (0-100)",
        range=[-5, 105],
        showgrid=True,
        automargin=True,
    )

    return fig


def create_combined_price_score_chart(
    df: pd.DataFrame,
    price_col: str,
    price_label: str,
    selected_score_col: str,
    selected_profile: str,
    top_n: int,
    sort_by: str,
):
    """
    Gráfico combinado:
    - Barras: accesibilidad del perfil
    - Línea: precio de vivienda.
    """
    required_cols = ["zone_name", selected_score_col, price_col]

    if any(col not in df.columns for col in required_cols):
        return None

    plot_df = df.copy()
    plot_df[selected_score_col] = pd.to_numeric(
        plot_df[selected_score_col],
        errors="coerce",
    )
    plot_df[price_col] = pd.to_numeric(plot_df[price_col], errors="coerce")

    plot_df = plot_df.dropna(subset=required_cols).copy()

    if len(plot_df) == 0:
        return None

    sort_map = {
        "Accesibilidad del perfil": selected_score_col,
        "Accesibilidad general": (
            "score_15min" if "score_15min" in plot_df.columns else selected_score_col
        ),
        "Precio": price_col,
        "Nombre barrio": "zone_name",
    }

    sort_col = sort_map.get(sort_by, selected_score_col)

    if sort_by == "Nombre barrio":
        plot_df = plot_df.sort_values(sort_col, ascending=True)
    else:
        plot_df = plot_df.sort_values(sort_col, ascending=False)

    plot_df = plot_df.head(top_n).copy()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    bar_hover = [
        build_price_hover(
            row=row,
            price_label=price_label,
            price_col=price_col,
            selected_profile=selected_profile,
            selected_score_col=selected_score_col,
        )
        for _, row in plot_df.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=plot_df["zone_name"],
            y=plot_df[selected_score_col],
            name=f"Accesibilidad {selected_profile}",
            marker=dict(color="rgba(99, 110, 250, 0.72)"),
            hovertext=bar_hover,
            hoverinfo="text",
        ),
        secondary_y=False,
    )

    line_hover = [
        build_price_hover(
            row=row,
            price_label=price_label,
            price_col=price_col,
            selected_profile=selected_profile,
            selected_score_col=selected_score_col,
        )
        for _, row in plot_df.iterrows()
    ]

    fig.add_trace(
        go.Scatter(
            x=plot_df["zone_name"],
            y=plot_df[price_col],
            mode="lines+markers",
            name=price_label,
            line=dict(width=3, color="#E45756"),
            marker=dict(size=8),
            hovertext=line_hover,
            hoverinfo="text",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=f"Accesibilidad {selected_profile} vs {price_label}",
        template="plotly_white",
        height=580,
        margin=dict(l=20, r=20, t=70, b=130),
        xaxis=dict(tickangle=-45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_yaxes(
        title_text=f"Accesibilidad {selected_profile} (0-100)",
        secondary_y=False,
        range=[0, 100],
    )

    fig.update_yaxes(
        title_text=f"{price_label} (€/m²)",
        secondary_y=True,
    )

    fig.update_xaxes(title_text="Barrio")

    return fig


def create_normalized_housing_chart(
    df: pd.DataFrame,
    selected_score_col: str,
    selected_profile: str,
    rent_col: str,
    sale_col: str,
    top_n: int,
):
    """
    Gráfico normalizado 0-100 para comparar tendencias relativas.
    """
    required_cols = ["zone_name", selected_score_col, rent_col, sale_col]

    if any(col not in df.columns for col in required_cols):
        return None

    plot_df = df.copy()

    for col in [selected_score_col, rent_col, sale_col]:
        plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")

    plot_df = plot_df.dropna(subset=required_cols).copy()

    if len(plot_df) == 0:
        return None

    plot_df = plot_df.sort_values(
        selected_score_col,
        ascending=False,
    ).head(top_n).copy()

    def minmax_scale(series):
        min_val = series.min()
        max_val = series.max()

        if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
            return pd.Series([50] * len(series), index=series.index)

        return 100 * (series - min_val) / (max_val - min_val)

    plot_df["access_norm"] = minmax_scale(plot_df[selected_score_col])
    plot_df["rent_norm"] = minmax_scale(plot_df[rent_col])
    plot_df["sale_norm"] = minmax_scale(plot_df[sale_col])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df["zone_name"],
            y=plot_df["access_norm"],
            mode="lines+markers",
            name=f"Accesibilidad {selected_profile}",
            hovertemplate=(
                "<b>Barrio:</b> %{x}<br>"
                "<b>Accesibilidad normalizada:</b> %{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["zone_name"],
            y=plot_df["rent_norm"],
            mode="lines+markers",
            name="Alquiler normalizado",
            hovertemplate=(
                "<b>Barrio:</b> %{x}<br>"
                "<b>Alquiler normalizado:</b> %{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["zone_name"],
            y=plot_df["sale_norm"],
            mode="lines+markers",
            name="Compra normalizada",
            hovertemplate=(
                "<b>Barrio:</b> %{x}<br>"
                "<b>Compra normalizada:</b> %{y:.2f}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=f"Comparación normalizada: accesibilidad, alquiler y compra ({selected_profile})",
        template="plotly_white",
        height=520,
        margin=dict(l=20, r=20, t=70, b=130),
        xaxis=dict(tickangle=-45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(title_text="Barrio")
    fig.update_yaxes(title_text="Valor normalizado (0-100)", range=[0, 100])

    return fig


def create_profile_comparison_chart(df: pd.DataFrame, top_n: int):
    """Comparación de scores por perfil."""
    profile_cols = [
        col for col in [
            "score_15min",
            "score_familia",
            "score_estudiante",
            "score_persona_mayor",
        ]
        if col in df.columns
    ]

    if not profile_cols or "zone_name" not in df.columns:
        return None

    plot_df = df.copy().dropna(subset=["zone_name"])

    if "score_15min" in plot_df.columns:
        plot_df = plot_df.sort_values(
            "score_15min",
            ascending=False,
        ).head(top_n)
    else:
        plot_df = plot_df.head(top_n)

    rename_map = {
        "score_15min": "General",
        "score_familia": "Familia",
        "score_estudiante": "Estudiante",
        "score_persona_mayor": "Persona mayor",
    }

    fig = go.Figure()

    for col in profile_cols:
        fig.add_trace(
            go.Bar(
                x=plot_df["zone_name"],
                y=plot_df[col],
                name=rename_map.get(col, col),
                hovertemplate=(
                    "<b>Barrio:</b> %{x}<br>"
                    f"<b>{rename_map.get(col, col)}:</b> %{{y:.2f}}/100"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Comparación de accesibilidad por perfil",
        template="plotly_white",
        barmode="group",
        height=550,
        margin=dict(l=20, r=20, t=70, b=130),
        xaxis=dict(tickangle=-45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(title_text="Barrio")
    fig.update_yaxes(title_text="Accesibilidad (0-100)", range=[0, 100])

    return fig


# ============================================================
# CARGA DE DATOS
# ============================================================

zones = load_zones_data()
services = load_services_data()

zones = dedupe_columns(zones)
services = dedupe_columns(services)

available_profiles = get_available_profile_scores(zones)

if not available_profiles:
    st.error(
        "No se encontró ninguna columna de accesibilidad. "
        "Revisa que existan columnas como score_15min, score_familia, etc."
    )
    st.stop()

rent_col, sale_col = get_housing_columns(zones)


# ============================================================
# CABECERA
# ============================================================

st.title("🏙️ Valencia ciudad de 15 minutos")

st.markdown(
    """
Este dashboard analiza la **accesibilidad urbana en Valencia** a partir de servicios obtenidos
desde **OpenStreetMap** y la cruza con **datos de vivienda** por barrio.

En este proyecto, **accesibilidad** significa la facilidad de llegar caminando desde un barrio
a servicios básicos como alimentación, farmacias, salud, educación, parques y transporte.
"""
)

st.divider()


# ============================================================
# MÉTRICAS PRINCIPALES
# ============================================================

st.subheader("📌 Resumen general")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Barrios analizados", len(zones))
col2.metric("Servicios detectados", len(services))

if "score_15min" in zones.columns:
    col3.metric("Accesibilidad media", f"{zones['score_15min'].mean():.1f}")
else:
    col3.metric("Accesibilidad media", "N/A")

if "cluster" in zones.columns:
    col4.metric("Clusters", zones["cluster"].nunique())
else:
    col4.metric("Clusters", "N/A")

if "has_housing_data" in zones.columns:
    col5.metric("Barrios con datos vivienda", int(zones["has_housing_data"].sum()))
else:
    col5.metric("Barrios con datos vivienda", "N/A")


# ============================================================
# ANÁLISIS SEGÚN PERFIL
# ============================================================

st.divider()
st.subheader("👤 Análisis según perfil")

selected_profile = st.selectbox(
    "Selecciona el perfil:",
    list(available_profiles.keys()),
)

selected_score_col = available_profiles[selected_profile]

metric1, metric2, metric3 = st.columns(3)

metric1.metric(
    f"Puntuación media - {selected_profile}",
    format_score(zones[selected_score_col].mean()),
)

metric2.metric(
    f"Mejor puntuación - {selected_profile}",
    format_score(zones[selected_score_col].max()),
)

metric3.metric(
    f"Puntuación mínima - {selected_profile}",
    format_score(zones[selected_score_col].min()),
)

st.caption(
    "La puntuación va de 0 a 100. Una puntuación alta indica mejor acceso caminando "
    "a servicios básicos para el perfil seleccionado."
)


# ============================================================
# RANKINGS
# ============================================================

st.divider()
st.subheader("🏆 Ranking de barrios")

display_cols = get_display_columns(zones, selected_score_col)

left_col, right_col = st.columns(2)

with left_col:
    st.markdown(f"### ✅ Top 10 barrios para perfil: {selected_profile}")
    top10 = zones.sort_values(
        selected_score_col,
        ascending=False,
    )[display_cols].head(10)
    st.dataframe(top10, use_container_width=True)

with right_col:
    st.markdown(f"### ⚠️ 10 barrios con menor puntuación para perfil: {selected_profile}")
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
        fig_services = go.Figure(
            data=[
                go.Bar(
                    x=service_counts.index,
                    y=service_counts.values,
                    text=service_counts.values,
                    textposition="outside",
                    hovertemplate=(
                        "<b>Categoría:</b> %{x}<br>"
                        "<b>Cantidad:</b> %{y}"
                        "<extra></extra>"
                    ),
                )
            ]
        )

        fig_services.update_layout(
            title="Número de servicios por categoría",
            template="plotly_white",
            height=450,
            margin=dict(l=20, r=20, t=70, b=20),
        )

        fig_services.update_xaxes(title_text="Categoría")
        fig_services.update_yaxes(title_text="Número de servicios")

        st.plotly_chart(fig_services, use_container_width=True)

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
st.subheader("🧩 Clustering de barrios")

st.markdown(
    """
Los clusters agrupan barrios con patrones similares de accesibilidad.
Indica qué barrios se parecen en sus distancias para acceder a los servicios básicos.
"""
)

if "cluster" in zones.columns:
    cluster_counts = zones["cluster"].value_counts().sort_index()

    # --------------------------------------------------------
    # DISTRIBUCIÓN DE BARRIOS POR CLUSTER
    # --------------------------------------------------------
    st.markdown("### 📊 Distribución de barrios por cluster")

    fig_clusters = go.Figure(
        data=[
            go.Bar(
                x=cluster_counts.index.astype(str),
                y=cluster_counts.values,
                text=cluster_counts.values,
                textposition="outside",
                hovertemplate=(
                    "<b>Cluster:</b> %{x}<br>"
                    "<b>Número de barrios:</b> %{y}"
                    "<extra></extra>"
                ),
            )
        ]
    )

    fig_clusters.update_layout(
        title="Distribución de barrios por cluster",
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=70, b=40),
    )

    fig_clusters.update_xaxes(title_text="Cluster")
    fig_clusters.update_yaxes(title_text="Número de barrios")

    st.plotly_chart(fig_clusters, use_container_width=True)

    # --------------------------------------------------------
    # TABLA DE PATRONES POR CLUSTER
    # --------------------------------------------------------
    st.markdown("### 🧠 Patrones de accesibilidad por cluster")

    cluster_pattern_df = build_cluster_pattern_table(zones)

    if not cluster_pattern_df.empty:
        st.dataframe(
            cluster_pattern_df,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Esta tabla interpreta cada cluster usando el score medio, "
            "el número medio de servicios accesibles y las distancias medias "
            "a cada tipo de servicio."
        )
    else:
        st.info("No se pudo construir la tabla de patrones por cluster.")

    # --------------------------------------------------------
    # HEATMAP DE DISTANCIAS MEDIAS
    # --------------------------------------------------------
    st.markdown("### 📏 Distancia media de cada servicio por cluster")

    fig_cluster_heatmap = create_cluster_distance_heatmap(zones)

    if fig_cluster_heatmap is not None:
        st.plotly_chart(fig_cluster_heatmap, use_container_width=True)
    else:
        st.info("No se pudo crear el mapa de calor de distancias por cluster.")

   

    # --------------------------------------------------------
    # TABLA DETALLADA POR SERVICIO
    # --------------------------------------------------------
    with st.expander("Ver detalle: media, mínimo y máximo por servicio y cluster"):
        cluster_distance_long_df = build_cluster_distance_long_table(zones)

        if not cluster_distance_long_df.empty:
            st.dataframe(
                cluster_distance_long_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No hay detalle de distancias disponible.")

    # --------------------------------------------------------
    # BARRIOS POR CLUSTER
    # --------------------------------------------------------
    with st.expander("Ver barrios que pertenecen a cada cluster"):
        cols_detail = [
            "cluster",
            "zone_id",
            "zone_name",
            "score_15min",
            "score_familia",
            "score_estudiante",
            "score_persona_mayor",
            "services_count",
        ]

        cols_detail = [col for col in cols_detail if col in zones.columns]

        cluster_detail_df = zones[cols_detail].copy()
        cluster_detail_df["cluster"] = pd.to_numeric(
            cluster_detail_df["cluster"],
            errors="coerce",
        )
        cluster_detail_df = cluster_detail_df.dropna(subset=["cluster"])
        cluster_detail_df["cluster"] = cluster_detail_df["cluster"].astype(int)

        if "score_15min" in cluster_detail_df.columns:
            cluster_detail_df["score_15min"] = pd.to_numeric(
                cluster_detail_df["score_15min"],
                errors="coerce",
            )
            cluster_detail_df = cluster_detail_df.sort_values(
                ["cluster", "score_15min"],
                ascending=[True, False],
            )
        else:
            cluster_detail_df = cluster_detail_df.sort_values("cluster")

        st.dataframe(
            cluster_detail_df,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info("No existe la columna cluster. Ejecuta src/step4_clustering.py.")


# ============================================================
# ANÁLISIS DE VIVIENDA
# ============================================================

st.divider()
st.subheader("🏠 Alquiler, compra y accesibilidad")

if rent_col or sale_col:
    st.markdown(
        """
Esta sección cruza la accesibilidad urbana con precios de vivienda.

- **Alquiler vs accesibilidad:** permite observar si los barrios más accesibles son también más caros para alquilar.
- **Compra vs accesibilidad:** permite observar si los barrios más accesibles tienen mayor precio de compra.
- La línea naranja de tendencia suavizada es solo una ayuda visual, no demuestra causalidad.
"""
    )

    valid_housing = zones.copy()

    if rent_col and sale_col:
        valid_housing = valid_housing[
            valid_housing[rent_col].notna() | valid_housing[sale_col].notna()
        ]
    elif rent_col:
        valid_housing = valid_housing[valid_housing[rent_col].notna()]
    elif sale_col:
        valid_housing = valid_housing[valid_housing[sale_col].notna()]

    max_top_n = max(1, min(len(valid_housing), 100))

    control1, control2, control3 = st.columns(3)

    with control1:
        top_n_combined = st.slider(
            "Número de barrios a mostrar en gráficos comparativos",
            min_value=5 if max_top_n >= 5 else 1,
            max_value=max_top_n,
            value=min(20, max_top_n),
            step=1,
        )

    with control2:
        sort_by_combined = st.selectbox(
            "Ordenar diagramas combinados por:",
            [
                "Accesibilidad del perfil",
                "Accesibilidad general",
                "Precio",
                "Nombre barrio",
            ],
        )

    with control3:
        show_trend = st.checkbox(
            "Mostrar tendencia suavizada",
            value=True,
            help=(
                "La tendencia suavizada es una media móvil orientativa. "
                "Sirve para ver el patrón general, pero no demuestra causalidad."
            ),
        )

    # --------------------------------------------------------
    # DISPERSIÓN
    # --------------------------------------------------------
    st.markdown("### 🔎 Gráficos de dispersión")

    scatter_col1, scatter_col2 = st.columns(2)

    with scatter_col1:
        if rent_col:
            fig_rent_scatter = create_price_accessibility_scatter(
                df=zones,
                price_col=rent_col,
                price_label="Alquiler",
                selected_score_col=selected_score_col,
                selected_profile=selected_profile,
                show_trend=show_trend,
            )

            if fig_rent_scatter is not None:
                st.plotly_chart(fig_rent_scatter, use_container_width=True)
            else:
                st.info("No hay datos suficientes para el gráfico de alquiler.")

    with scatter_col2:
        if sale_col:
            fig_sale_scatter = create_price_accessibility_scatter(
                df=zones,
                price_col=sale_col,
                price_label="Compra",
                selected_score_col=selected_score_col,
                selected_profile=selected_profile,
                show_trend=show_trend,
            )

            if fig_sale_scatter is not None:
                st.plotly_chart(fig_sale_scatter, use_container_width=True)
            else:
                st.info("No hay datos suficientes para el gráfico de compra.")

    # --------------------------------------------------------
    # DIAGRAMAS COMBINADOS
    # --------------------------------------------------------
    st.markdown("### 📊 Diagramas combinados por barrio")

    st.info(
        "Alquiler y compra se muestran en gráficos separados porque tienen escalas muy distintas."
    )

    combined_col1, combined_col2 = st.columns(2)

    with combined_col1:
        if rent_col:
            fig_combined_rent = create_combined_price_score_chart(
                df=zones,
                price_col=rent_col,
                price_label="Alquiler",
                selected_score_col=selected_score_col,
                selected_profile=selected_profile,
                top_n=top_n_combined,
                sort_by=sort_by_combined,
            )

            if fig_combined_rent is not None:
                st.plotly_chart(fig_combined_rent, use_container_width=True)
            else:
                st.info("No hay datos suficientes para el diagrama combinado de alquiler.")

    with combined_col2:
        if sale_col:
            fig_combined_sale = create_combined_price_score_chart(
                df=zones,
                price_col=sale_col,
                price_label="Compra",
                selected_score_col=selected_score_col,
                selected_profile=selected_profile,
                top_n=top_n_combined,
                sort_by=sort_by_combined,
            )

            if fig_combined_sale is not None:
                st.plotly_chart(fig_combined_sale, use_container_width=True)
            else:
                st.info("No hay datos suficientes para el diagrama combinado de compra.")

    # --------------------------------------------------------
    # NORMALIZADO
    # --------------------------------------------------------
    st.markdown("### 📈 Comparación normalizada de tendencias")

    st.caption(
        "Este gráfico transforma accesibilidad, alquiler y compra a una escala común 0-100. "
        "Sirve para comparar tendencias relativas, no valores absolutos."
    )

    if rent_col and sale_col:
        fig_norm = create_normalized_housing_chart(
            df=zones,
            selected_score_col=selected_score_col,
            selected_profile=selected_profile,
            rent_col=rent_col,
            sale_col=sale_col,
            top_n=top_n_combined,
        )

        if fig_norm is not None:
            st.plotly_chart(fig_norm, use_container_width=True)
        else:
            st.info("No hay suficientes datos para el gráfico normalizado.")

    # --------------------------------------------------------
    # COMPARACIÓN DE PERFILES
    # --------------------------------------------------------
    st.markdown("### 👥 Comparación de accesibilidad por perfil")

    top_n_profiles = st.slider(
        "Número de barrios para comparar perfiles",
        min_value=5 if len(zones) >= 5 else 1,
        max_value=min(25, len(zones)),
        value=min(12, len(zones)),
        step=1,
        key="top_n_profiles",
    )

    fig_profiles = create_profile_comparison_chart(zones, top_n_profiles)

    if fig_profiles is not None:
        st.plotly_chart(fig_profiles, use_container_width=True)

    # --------------------------------------------------------
    # COBERTURA VIVIENDA
    # --------------------------------------------------------
    if "housing_data_status" in zones.columns:
        st.markdown("### 📌 Cobertura de datos de vivienda")

        coverage_counts = zones["housing_data_status"].value_counts()

        fig_coverage = go.Figure(
            data=[
                go.Pie(
                    labels=coverage_counts.index,
                    values=coverage_counts.values,
                    hole=0.45,
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "<b>Barrios:</b> %{value}<br>"
                        "<b>Porcentaje:</b> %{percent}"
                        "<extra></extra>"
                    ),
                )
            ]
        )

        fig_coverage.update_layout(
            title="Cobertura de datos de vivienda",
            template="plotly_white",
            height=420,
            margin=dict(l=20, r=20, t=70, b=20),
        )

        st.plotly_chart(fig_coverage, use_container_width=True)

else:
    st.info(
        "No hay columnas de alquiler o compra. "
        "Ejecuta src/step0_prepare_housing_dataset.py y src/step7_join_housing.py."
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
        "Ejecuta src/step6_build_map.py."
    )


# ============================================================
# DATASET COMPLETO
# ============================================================

st.divider()
st.subheader("📋 Dataset completo")

with st.expander("Ver tabla completa de barrios"):
    st.dataframe(zones, use_container_width=True)


# ============================================================
# METODOLOGÍA
# ============================================================

st.divider()
st.subheader("🧠 Metodología")

st.markdown(
    """
### 1. Extracción de datos
Se descargaron servicios desde OpenStreetMap y se clasificaron en:
alimentación, farmacia, salud, educación, parques y transporte.

### 2. Unidad de análisis
El proyecto trabaja a nivel de **barrios oficiales de Valencia**, no solo distritos,
para obtener un análisis más detallado.

### 3. Accesibilidad urbana
En este proyecto, accesibilidad significa la facilidad de llegar caminando desde un barrio
a servicios básicos. Una mayor puntuación indica mejores condiciones de proximidad.

### 4. Score general y score por perfil
Se generó un score general y también scores específicos para:
- 👨‍👩‍👧 familia
- 🎓 estudiante
- 👴 persona mayor

### 5. Clustering
Se aplicó clustering para identificar barrios con patrones similares de accesibilidad.
Además de contar barrios por cluster, se analizan las distancias medias por servicio
para interpretar qué caracteriza a cada grupo.

### 6. Vivienda
Se cruzó el análisis con datos de compra y alquiler por barrio.

### 7. Visualización
Los resultados se presentan con tablas, mapa interactivo y gráficos profesionales con Plotly.
"""
)


# ============================================================
# LIMITACIONES
# ============================================================

st.divider()
st.subheader("⚠️ Limitaciones")

st.markdown(
    """
- No todos los barrios tienen datos de vivienda disponibles.
- Algunos valores de vivienda pueden ser anómalos y se han tratado de forma cautelosa.
- Los datos dependen de la calidad de OpenStreetMap y del dataset de vivienda utilizado.
- La línea de tendencia suavizada es una ayuda visual y no implica causalidad.
- La interpretación de clusters depende de las variables usadas para agrupar.
- El proyecto es un análisis exploratorio y no sustituye un estudio urbanístico oficial.
"""
)


# ============================================================
# MEJORAS FUTURAS
# ============================================================

st.divider()
st.subheader("🚀 Mejoras futuras")

st.markdown(
    """
- Añadir filtros geográficos más avanzados.
- Permitir comparar varios barrios seleccionados por el usuario.
- Incluir renta media, población y demografía.
- Añadir exportación de gráficos y tablas.
- Incorporar horarios de servicios y calidad percibida.
- Desplegar la aplicación en Streamlit Cloud.
"""
)