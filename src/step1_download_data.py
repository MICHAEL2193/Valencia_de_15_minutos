import pandas as pd
import geopandas as gpd
import osmnx as ox

from config import (
    PLACE_NAME,
    OSM_TAGS,
    CRS_WGS84,
    CRS_METRIC,
    DATA_RAW,
    DATA_PROCESSED,
)

def classify_service(row):
    shop = row.get("shop")
    amenity = row.get("amenity")
    leisure = row.get("leisure")
    highway = row.get("highway")
    railway = row.get("railway")

    if shop in ["supermarket", "convenience"]:
        return "alimentacion"
    if amenity == "pharmacy":
        return "farmacia"
    if amenity in ["clinic", "hospital"]:
        return "salud"
    if amenity in ["school", "library"]:
        return "educacion"
    if leisure == "park":
        return "parque"
    if highway == "bus_stop" or railway in ["station", "tram_stop", "subway_entrance"]:
        return "transporte"
    return "otros"

def main():
    print("1) Descargando límite de Valencia...")
    city_boundary = ox.geocode_to_gdf(PLACE_NAME).to_crs(CRS_WGS84)
    city_boundary.to_file(DATA_RAW / "valencia_boundary.geojson", driver="GeoJSON")
    print("   OK -> data/raw/valencia_boundary.geojson")

    print("2) Descargando servicios desde OpenStreetMap...")
    pois = ox.features_from_place(PLACE_NAME, tags=OSM_TAGS)
    pois = pois.reset_index()

    # Asegurar que existan columnas aunque no vengan en todos los registros
    for col in ["shop", "amenity", "leisure", "highway", "railway", "name"]:
        if col not in pois.columns:
            pois[col] = None

    print(f"   Total elementos descargados: {len(pois)}")

    print("3) Clasificando servicios...")
    pois["categoria"] = pois.apply(classify_service, axis=1)
    pois = pois[pois["categoria"] != "otros"].copy()

    # Pasar a CRS métrico y convertir todo a puntos representativos
    pois = pois.to_crs(CRS_METRIC)
    pois["geometry"] = pois.geometry.representative_point()
    pois = pois.to_crs(CRS_WGS84)

    # Quedarnos solo con columnas útiles
    pois_clean = pois[["name", "categoria", "geometry"]].copy()
    pois_clean["lat"] = pois_clean.geometry.y
    pois_clean["lon"] = pois_clean.geometry.x

    pois_clean.to_file(DATA_PROCESSED / "services.geojson", driver="GeoJSON")
    pois_clean.drop(columns="geometry").to_csv(DATA_PROCESSED / "services.csv", index=False)

    print("4) Conteo por categoría:")
    print(pois_clean["categoria"].value_counts())

    print("   OK -> data/processed/services.geojson")
    print("   OK -> data/processed/services.csv")

if __name__ == "__main__":
    main()