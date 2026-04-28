import html
import pandas as pd
import folium
import geopandas as gpd

from config import (
    DATA_PROCESSED,
    OUTPUT_MAPS,
    CITY_CENTER,
    CATEGORY_COLORS,
)


SERVICE_ICONS = {
    "alimentacion": "🛒",
    "farmacia": "💊",
    "salud": "🏥",
    "educacion": "📚",
    "parque": "🌳",
    "transporte": "🚌",
}


def score_color(score):
    """
    Devuelve color según el score de accesibilidad.
    """
    if pd.isna(score):
        return "#cccccc"

    if score >= 80:
        return "#1a9850"  # verde oscuro
    elif score >= 60:
        return "#91cf60"  # verde claro
    elif score >= 40:
        return "#fdae61"  # naranja
    else:
        return "#d73027"  # rojo


def safe_number(value, default=0):
    """
    Convierte valores a número de forma segura.
    """
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def icon_marker(category):
    """
    Crea un icono con emoji para cada tipo de servicio.
    """
    emoji = SERVICE_ICONS.get(category, "📍")

    return folium.DivIcon(
        html=f"""
        <div style="
            font-size: 20px;
            text-align: center;
            line-height: 20px;
        ">
            {emoji}
        </div>
        """
    )


def build_tooltip(row, score_col):
    """
    Construye el tooltip HTML de cada barrio.
    """
    zone_id = html.escape(str(row.get("zone_id", "")))
    zone_name = html.escape(str(row.get("zone_name", "Sin nombre")))

    selected_score = safe_number(row.get(score_col, 0))
    general_score = safe_number(row.get("score_15min", 0))
    services_count = safe_number(row.get("services_count", 0))

    cluster_value = row.get("cluster", None)
    if pd.notna(cluster_value):
        try:
            cluster_text = str(int(cluster_value))
        except Exception:
            cluster_text = str(cluster_value)
    else:
        cluster_text = "N/A"

    parts = [
        f"<b>Zona:</b> {zone_id}",
        f"<b>Barrio:</b> {zone_name}",
        f"<b>{score_col}:</b> {selected_score:.1f}",
        f"<b>Score general:</b> {general_score:.1f}",
        f"<b>Servicios cercanos:</b> {int(services_count)}",
        f"<b>Cluster:</b> {cluster_text}",
    ]

    if "score_familia" in row and pd.notna(row.get("score_familia")):
        parts.append(f"<b>Familia:</b> {safe_number(row.get('score_familia')):.1f}")

    if "score_estudiante" in row and pd.notna(row.get("score_estudiante")):
        parts.append(f"<b>Estudiante:</b> {safe_number(row.get('score_estudiante')):.1f}")

    if "score_persona_mayor" in row and pd.notna(row.get("score_persona_mayor")):
        parts.append(
            f"<b>Persona mayor:</b> {safe_number(row.get('score_persona_mayor')):.1f}"
        )

    if "rent_eur_m2" in row and pd.notna(row.get("rent_eur_m2")):
        parts.append(f"<b>Alquiler:</b> {safe_number(row.get('rent_eur_m2')):.2f} €/m²")

    if "sale_eur_m2" in row and pd.notna(row.get("sale_eur_m2")):
        parts.append(f"<b>Compra:</b> {safe_number(row.get('sale_eur_m2')):.0f} €/m²")

    if "housing_data_status" in row and pd.notna(row.get("housing_data_status")):
        status = html.escape(str(row.get("housing_data_status")))
        parts.append(f"<b>Datos vivienda:</b> {status}")

    return "<br>".join(parts)


def add_zone_layer(m, zones, score_col, layer_name, show=False):
    """
    Añade una capa de polígonos coloreados por score.
    """
    fg = folium.FeatureGroup(name=layer_name, show=show)

    for _, row in zones.iterrows():
        score = row.get(score_col, row.get("score_15min", 0))

        folium.GeoJson(
            row["geometry"],
            style_function=lambda feature, score=score: {
                "fillColor": score_color(score),
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.55,
            },
            tooltip=folium.Tooltip(build_tooltip(row, score_col), sticky=True),
        ).add_to(fg)

    fg.add_to(m)


def add_zone_name_labels(m, zones_gdf, name_col="zone_name", show=True):
    """
    Añade etiquetas con el nombre de cada barrio sobre el mapa.

    Usa representative_point() en lugar de centroid para intentar colocar
    el nombre dentro del polígono, incluso en geometrías irregulares.
    """
    labels_group = folium.FeatureGroup(
        name="🏷️ Nombres de barrios",
        show=show,
    )

    zones_labels = zones_gdf.copy()

    if zones_labels.crs is not None:
        zones_labels = zones_labels.to_crs("EPSG:4326")

    zones_labels["label_point"] = zones_labels.geometry.representative_point()

    for _, row in zones_labels.iterrows():
        if name_col not in row or pd.isna(row[name_col]):
            continue

        barrio = html.escape(str(row[name_col]).title())

        point = row["label_point"]
        lat = point.y
        lon = point.x

        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                icon_size=(150, 30),
                icon_anchor=(75, 15),
                html=f"""
                <div style="
                    font-size: 9px;
                    font-weight: 700;
                    color: #111827;
                    text-align: center;
                    white-space: nowrap;
                    pointer-events: none;
                    text-shadow:
                        -1px -1px 0 #ffffff,
                         1px -1px 0 #ffffff,
                        -1px  1px 0 #ffffff,
                         1px  1px 0 #ffffff;
                ">
                    {barrio}
                </div>
                """,
            ),
        ).add_to(labels_group)

    labels_group.add_to(m)

    return m


def add_services_layer(m, services):
    """
    Añade servicios como marcadores con iconos.
    """
    for category, color in CATEGORY_COLORS.items():
        fg = folium.FeatureGroup(
            name=f"{SERVICE_ICONS.get(category, '📍')} {category}",
            show=False,
        )

        sub = services[services["categoria"] == category]

        for _, row in sub.iterrows():
            service_name = html.escape(str(row.get("name", "Sin nombre")))
            service_category = html.escape(str(category))

            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                icon=icon_marker(category),
                popup=f"<b>{service_name}</b><br>{service_category}",
            ).add_to(fg)

        fg.add_to(m)


def main():
    OUTPUT_MAPS.mkdir(parents=True, exist_ok=True)

    print("1) Cargando zonas...")

    enriched_path = DATA_PROCESSED / "zones_enriched.geojson"
    clustered_path = DATA_PROCESSED / "zones_clustered.geojson"

    if enriched_path.exists():
        print("   Usando zonas enriquecidas con vivienda/alquiler...")
        zones = gpd.read_file(enriched_path).to_crs("EPSG:4326")
    elif clustered_path.exists():
        print("   Usando zonas con clustering...")
        zones = gpd.read_file(clustered_path).to_crs("EPSG:4326")
    else:
        raise FileNotFoundError(
            "No existe zones_enriched.geojson ni zones_clustered.geojson. "
            "Ejecuta antes step3_accessibility.py, step4_clustering.py "
            "y, si aplica, step7_join_housing.py."
        )

    print("2) Cargando servicios...")

    services_path = DATA_PROCESSED / "services.geojson"

    if not services_path.exists():
        raise FileNotFoundError(
            "No existe data/processed/services.geojson. "
            "Ejecuta primero src/step1_download_data.py."
        )

    services = gpd.read_file(services_path).to_crs("EPSG:4326")

    print("3) Creando mapa base...")

    m = folium.Map(
        location=CITY_CENTER,
        zoom_start=12,
        tiles="CartoDB positron",
        control_scale=True,
    )

    print("4) Añadiendo capas de accesibilidad...")

    add_zone_layer(
        m,
        zones,
        score_col="score_15min",
        layer_name="Score general 15 minutos",
        show=True,
    )

    if "score_familia" in zones.columns:
        add_zone_layer(
            m,
            zones,
            score_col="score_familia",
            layer_name="Score perfil familia",
            show=False,
        )

    if "score_estudiante" in zones.columns:
        add_zone_layer(
            m,
            zones,
            score_col="score_estudiante",
            layer_name="Score perfil estudiante",
            show=False,
        )

    if "score_persona_mayor" in zones.columns:
        add_zone_layer(
            m,
            zones,
            score_col="score_persona_mayor",
            layer_name="Score perfil persona mayor",
            show=False,
        )

    print("5) Añadiendo nombres de barrios...")

    m = add_zone_name_labels(
        m=m,
        zones_gdf=zones,
        name_col="zone_name",
        show=True,
    )

    print("6) Añadiendo servicios con iconos...")

    add_services_layer(m, services)

    print("7) Añadiendo control de capas...")

    folium.LayerControl(collapsed=False).add_to(m)

    output_path = OUTPUT_MAPS / "valencia_15min_map.html"
    m.save(output_path)

    print(f"   OK -> {output_path}")


if __name__ == "__main__":
    main()