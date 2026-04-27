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
    if pd.isna(score):
        return "#cccccc"
    if score >= 80:
        return "#1a9850"
    elif score >= 60:
        return "#91cf60"
    elif score >= 40:
        return "#fdae61"
    else:
        return "#d73027"

def icon_marker(category):
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
    parts = [
        f"Zona: {row.get('zone_id', '')}",
        f"Nombre: {row.get('zone_name', 'Sin nombre')}",
        f"{score_col}: {row.get(score_col, 0):.1f}",
        f"Score general: {row.get('score_15min', 0):.1f}",
        f"Servicios cercanos: {int(row.get('services_count', 0))}",
        f"Cluster: {int(row.get('cluster', -1))}",
    ]

    if "score_familia" in row:
        parts.append(f"Familia: {row.get('score_familia', 0):.1f}")

    if "score_estudiante" in row:
        parts.append(f"Estudiante: {row.get('score_estudiante', 0):.1f}")

    if "score_persona_mayor" in row:
        parts.append(f"Persona mayor: {row.get('score_persona_mayor', 0):.1f}")

    if "rent_eur_m2" in row and pd.notna(row.get("rent_eur_m2")):
        parts.append(f"Alquiler: {row.get('rent_eur_m2'):.2f} €/m²")

    if "sale_eur_m2" in row and pd.notna(row.get("sale_eur_m2")):
        parts.append(f"Compra: {row.get('sale_eur_m2'):.0f} €/m²")

    return "<br>".join(parts)

def add_zone_layer(m, zones, score_col, layer_name, show=False):
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
            tooltip=folium.Tooltip(build_tooltip(row, score_col)),
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
    else:
        print("   Usando zonas con clustering...")
        zones = gpd.read_file(clustered_path).to_crs("EPSG:4326")

    print("2) Cargando servicios...")
    services = gpd.read_file(DATA_PROCESSED / "services.geojson").to_crs("EPSG:4326")

    print("3) Creando mapa base...")
    m = folium.Map(location=CITY_CENTER, zoom_start=12, tiles="CartoDB positron")

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

    print("5) Añadiendo servicios con iconos...")
    for category, color in CATEGORY_COLORS.items():
        fg = folium.FeatureGroup(name=f"{SERVICE_ICONS.get(category, '📍')} {category}", show=False)
        sub = services[services["categoria"] == category]

        for _, row in sub.iterrows():
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                icon=icon_marker(category),
                popup=f"{row.get('name', 'Sin nombre')}<br>{category}",
            ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    output_path = OUTPUT_MAPS / "valencia_15min_map.html"
    m.save(output_path)

    print(f"   OK -> {output_path}")

if __name__ == "__main__":
    main()