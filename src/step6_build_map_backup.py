import folium
import geopandas as gpd

from config import DATA_PROCESSED, OUTPUT_MAPS, CITY_CENTER, CATEGORY_COLORS

def score_color(score):
    if score >= 80:
        return "#1a9850"   # verde fuerte
    elif score >= 60:
        return "#91cf60"   # verde claro
    elif score >= 40:
        return "#fdae61"   # naranja
    else:
        return "#d73027"   # rojo

def main():
    print("1) Cargando datos...")
    zones = gpd.read_file(DATA_PROCESSED / "zones_clustered.geojson").to_crs("EPSG:4326")
    services = gpd.read_file(DATA_PROCESSED / "services.geojson").to_crs("EPSG:4326")

    print("2) Creando mapa base...")
    m = folium.Map(location=CITY_CENTER, zoom_start=12, tiles="CartoDB positron")

    print("3) Añadiendo zonas...")
    for _, row in zones.iterrows():
        folium.GeoJson(
            row["geometry"],
            style_function=lambda feature, score=row["score_15min"]: {
                "fillColor": score_color(score),
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.5,
            },
            tooltip=folium.Tooltip(
                f"Zona: {row['zone_id']}<br>"
                f"Score: {row['score_15min']:.1f}<br>"
                f"Servicios cercanos: {int(row['services_count'])}<br>"
                f"Cluster: {int(row['cluster'])}"
            )
        ).add_to(m)

    print("4) Añadiendo capas de servicios...")
    for category, color in CATEGORY_COLORS.items():
        fg = folium.FeatureGroup(name=category, show=False)
        sub = services[services["categoria"] == category]

        for _, row in sub.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=3,
                color=color,
                fill=True,
                fill_opacity=0.8,
                popup=f"{row.get('name', 'Sin nombre')}<br>{category}"
            ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl().add_to(m)

    output_path = OUTPUT_MAPS / "valencia_15min_map.html"
    m.save(output_path)

    print(f"   OK -> {output_path}")

if __name__ == "__main__":
    main()