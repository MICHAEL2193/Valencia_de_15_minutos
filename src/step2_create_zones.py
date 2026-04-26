import requests
import geopandas as gpd

from config import (
    DATA_PROCESSED,
    CRS_WGS84,
    CRS_METRIC,
    ZONE_LEVEL,
    OFFICIAL_ZONES_URLS,
)

def download_geojson(url):
    """
    Descarga un GeoJSON desde una URL y lo convierte en GeoDataFrame.
    """
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    data = response.json()

    gdf = gpd.GeoDataFrame.from_features(data["features"])
    gdf = gdf.set_crs(CRS_WGS84, allow_override=True)

    return gdf

def detect_name_column(gdf):
    """
    Intenta detectar automáticamente la columna que contiene el nombre
    del barrio o distrito.
    """
    candidates = [
        "nombre",
        "NOMBRE",
        "nom",
        "NOM",
        "barri",
        "BARRI",
        "barrio",
        "BARRIO",
        "distrito",
        "DISTRITO",
        "NOM_BARRI",
        "NOMBRE_BARRIO",
        "NOM_DISTRICTE",
        "NOMBRE_DISTRITO",
        "Name",
        "name",
    ]

    for col in candidates:
        if col in gdf.columns:
            return col

    # Si no encuentra una columna conocida, intenta usar la primera columna de texto
    text_cols = [
        col for col in gdf.columns
        if col != "geometry" and gdf[col].dtype == "object"
    ]

    if text_cols:
        return text_cols[0]

    return None

def main():
    print(f"1) Descargando zonas oficiales de Valencia: {ZONE_LEVEL}")

    url = OFFICIAL_ZONES_URLS[ZONE_LEVEL]
    zones = download_geojson(url)

    print("2) Columnas encontradas en el dataset oficial:")
    print(list(zones.columns))

    print("3) Limpiando geometrías...")
    zones = zones[zones.geometry.notna()].copy()
    zones = zones[~zones.geometry.is_empty].copy()

    # Pasamos a CRS métrico para limpiar geometrías y calcular áreas
    zones = zones.to_crs(CRS_METRIC)
    zones["geometry"] = zones.geometry.buffer(0)
    zones["area_m2"] = zones.geometry.area

    # Eliminamos geometrías demasiado pequeñas si existieran
    zones = zones[zones["area_m2"] > 1000].copy()

    print("4) Detectando columna de nombre...")
    name_col = detect_name_column(zones)

    if name_col is None:
        print("   No se encontró columna de nombre. Se usará un nombre automático.")
        zones["zone_name"] = [f"{ZONE_LEVEL}_{i+1}" for i in range(len(zones))]
    else:
        print(f"   Columna usada como nombre: {name_col}")
        zones["zone_name"] = zones[name_col].astype(str)

    prefix = "B" if ZONE_LEVEL == "barrios" else "D"
    zones = zones.reset_index(drop=True)
    zones["zone_id"] = [f"{prefix}{i:03d}" for i in range(1, len(zones) + 1)]

    print("5) Creando puntos representativos de cada zona...")
    zone_points = zones[["zone_id", "zone_name", "geometry"]].copy()
    zone_points["geometry"] = zone_points.geometry.representative_point()

    print("6) Guardando archivos...")
    zones_out = zones[["zone_id", "zone_name", "area_m2", "geometry"]].to_crs(CRS_WGS84)
    points_out = zone_points.to_crs(CRS_WGS84)

    zones_out.to_file(DATA_PROCESSED / "zones.geojson", driver="GeoJSON")
    points_out.to_file(DATA_PROCESSED / "zone_points.geojson", driver="GeoJSON")

    zones_out.drop(columns="geometry").to_csv(DATA_PROCESSED / "zones.csv", index=False)

    print(f"   Número de zonas oficiales creadas: {len(zones_out)}")
    print("   OK -> data/processed/zones.geojson")
    print("   OK -> data/processed/zone_points.geojson")
    print("   OK -> data/processed/zones.csv")

    print("\n7) Primeras zonas:")
    print(zones_out[["zone_id", "zone_name", "area_m2"]].head(10))

if __name__ == "__main__":
    main()