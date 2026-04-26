import math
import geopandas as gpd
from shapely.geometry import box

from config import (
    DATA_RAW,
    DATA_PROCESSED,
    CRS_METRIC,
    CRS_WGS84,
    GRID_SIZE_METERS,
)

def create_grid(boundary_gdf, cell_size):
    minx, miny, maxx, maxy = boundary_gdf.total_bounds

    cols = list(range(int(minx), int(maxx) + cell_size, cell_size))
    rows = list(range(int(miny), int(maxy) + cell_size, cell_size))

    grid_cells = []
    for x in cols[:-1]:
        for y in rows[:-1]:
            grid_cells.append(box(x, y, x + cell_size, y + cell_size))

    grid = gpd.GeoDataFrame({"geometry": grid_cells}, crs=boundary_gdf.crs)
    return grid

def main():
    print("1) Leyendo límite de Valencia...")
    boundary = gpd.read_file(DATA_RAW / "valencia_boundary.geojson").to_crs(CRS_METRIC)

    print("2) Creando cuadrícula...")
    grid = create_grid(boundary, GRID_SIZE_METERS)

    print("3) Recortando cuadrícula al límite de Valencia...")
    zones = gpd.overlay(grid, boundary, how="intersection")

    # Eliminar fragmentos muy pequeños
    zones["area_m2"] = zones.geometry.area
    zones = zones[zones["area_m2"] > 50000].copy()

    zones = zones.reset_index(drop=True)
    zones["zone_id"] = [f"Z{i:03d}" for i in range(1, len(zones) + 1)]

    # Punto representativo para usar luego
    zone_points = zones.copy()
    zone_points["geometry"] = zone_points.geometry.representative_point()

    zones_wgs84 = zones.to_crs(CRS_WGS84)
    zone_points_wgs84 = zone_points.to_crs(CRS_WGS84)

    zones_wgs84.to_file(DATA_PROCESSED / "zones.geojson", driver="GeoJSON")
    zone_points_wgs84.to_file(DATA_PROCESSED / "zone_points.geojson", driver="GeoJSON")

    print(f"   Número de zonas creadas: {len(zones_wgs84)}")
    print("   OK -> data/processed/zones.geojson")
    print("   OK -> data/processed/zone_points.geojson")

if __name__ == "__main__":
    main()