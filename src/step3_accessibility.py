import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.neighbors import NearestNeighbors

from config import (
    DATA_PROCESSED,
    CATEGORIES,
    WALK_RADIUS_METERS,
    CRS_METRIC,
    CRS_WGS84,
)

def nearest_distance(source_gdf, target_gdf):
    if target_gdf.empty:
        return pd.Series([np.nan] * len(source_gdf), index=source_gdf.index)

    source_coords = np.column_stack((source_gdf.geometry.x, source_gdf.geometry.y))
    target_coords = np.column_stack((target_gdf.geometry.x, target_gdf.geometry.y))

    model = NearestNeighbors(n_neighbors=1)
    model.fit(target_coords)
    distances, _ = model.kneighbors(source_coords)

    return pd.Series(distances[:, 0], index=source_gdf.index)

def main():
    print("1) Cargando zonas y servicios...")
    zones = gpd.read_file(DATA_PROCESSED / "zones.geojson").to_crs(CRS_METRIC)
    zone_points = gpd.read_file(DATA_PROCESSED / "zone_points.geojson").to_crs(CRS_METRIC)
    services = gpd.read_file(DATA_PROCESSED / "services.geojson").to_crs(CRS_METRIC)

    print("2) Calculando distancias mínimas por categoría...")
    for category in CATEGORIES:
        services_cat = services[services["categoria"] == category].copy()

        zones[f"dist_{category}"] = nearest_distance(zone_points, services_cat)
        zones[f"access_{category}"] = (zones[f"dist_{category}"] <= WALK_RADIUS_METERS).astype(int)

    access_cols = [f"access_{cat}" for cat in CATEGORIES]
    zones["services_count"] = zones[access_cols].sum(axis=1)
    zones["score_15min"] = zones["services_count"] / len(CATEGORIES) * 100

    zones = zones.to_crs(CRS_WGS84)
    zones.to_file(DATA_PROCESSED / "zones_accessibility.geojson", driver="GeoJSON")

    # CSV sin geometría
    zones_df = zones.drop(columns="geometry")
    zones_df.to_csv(DATA_PROCESSED / "zones_accessibility.csv", index=False)

    print("3) Resumen del score:")
    print(zones_df["score_15min"].describe())

    print("   OK -> data/processed/zones_accessibility.geojson")
    print("   OK -> data/processed/zones_accessibility.csv")

if __name__ == "__main__":
    main()