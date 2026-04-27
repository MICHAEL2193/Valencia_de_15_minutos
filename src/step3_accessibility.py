import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from sklearn.neighbors import NearestNeighbors

from config import (
    PLACE_NAME,
    DATA_RAW,
    DATA_PROCESSED,
    CATEGORIES,
    WALK_RADIUS_METERS,
    MAX_PROFILE_DISTANCE_METERS,
    K_NEAREST_CANDIDATES,
    WALK_GRAPH_PATH,
    PROFILE_WEIGHTS,
    CRS_METRIC,
    CRS_WGS84,
)

def load_or_download_walk_graph():
    """
    Descarga o carga desde caché la red peatonal de Valencia.
    Esta red se usa para calcular rutas reales caminando.
    """
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(DATA_RAW.parent.parent / "cache")

    if WALK_GRAPH_PATH.exists():
        print("   Cargando red peatonal desde archivo local...")
        return ox.load_graphml(WALK_GRAPH_PATH)

    print("   Descargando red peatonal desde OpenStreetMap...")
    G = ox.graph_from_place(PLACE_NAME, network_type="walk", simplify=True)

    print("   Guardando red peatonal para no descargarla otra vez...")
    ox.save_graphml(G, WALK_GRAPH_PATH)

    return G

def get_nearest_service_candidates(zone_points_m, services_cat_m, k):
    """
    Devuelve los índices de los k servicios más cercanos en línea recta.
    Luego sobre esos candidatos calcularemos ruta real.
    """
    if services_cat_m.empty:
        return None

    n_neighbors = min(k, len(services_cat_m))

    origin_coords = np.column_stack(
        (zone_points_m.geometry.x, zone_points_m.geometry.y)
    )

    service_coords = np.column_stack(
        (services_cat_m.geometry.x, services_cat_m.geometry.y)
    )

    model = NearestNeighbors(n_neighbors=n_neighbors)
    model.fit(service_coords)

    _, candidate_indices = model.kneighbors(origin_coords)

    return candidate_indices

def route_distance_meters(G, origin_node, destination_node):
    """
    Calcula distancia de ruta real caminando entre dos nodos de la red.
    Si no hay ruta, devuelve NaN.
    """
    try:
        return nx.shortest_path_length(
            G,
            source=origin_node,
            target=destination_node,
            weight="length",
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return np.nan

def calculate_category_walk_distances(
    G,
    zone_points_wgs,
    zone_points_m,
    services_wgs,
    services_m,
    category,
):
    """
    Para cada zona calcula la distancia real caminando al servicio más cercano
    de una categoría concreta.
    """
    services_cat_wgs = services_wgs[services_wgs["categoria"] == category].copy()
    services_cat_m = services_m[services_m["categoria"] == category].copy()

    if services_cat_wgs.empty:
        print(f"   ⚠️ No hay servicios para categoría: {category}")
        return pd.Series([np.nan] * len(zone_points_wgs), index=zone_points_wgs.index)

    services_cat_wgs = services_cat_wgs.reset_index(drop=True)
    services_cat_m = services_cat_m.reset_index(drop=True)

    print(f"   Categoría '{category}': {len(services_cat_wgs)} servicios")

    # Nodo más cercano a cada punto de zona
    origin_nodes = ox.distance.nearest_nodes(
        G,
        X=zone_points_wgs.geometry.x.values,
        Y=zone_points_wgs.geometry.y.values,
    )

    # Nodo más cercano a cada servicio de esa categoría
    service_nodes = ox.distance.nearest_nodes(
        G,
        X=services_cat_wgs.geometry.x.values,
        Y=services_cat_wgs.geometry.y.values,
    )

    candidate_indices = get_nearest_service_candidates(
        zone_points_m,
        services_cat_m,
        K_NEAREST_CANDIDATES,
    )

    distances = []

    for zone_idx, origin_node in enumerate(origin_nodes):
        best_distance = np.nan

        for service_idx in candidate_indices[zone_idx]:
            destination_node = service_nodes[service_idx]

            dist = route_distance_meters(G, origin_node, destination_node)

            if pd.notna(dist):
                if pd.isna(best_distance) or dist < best_distance:
                    best_distance = dist

        distances.append(best_distance)

    return pd.Series(distances, index=zone_points_wgs.index)

def proximity_score(distance_m):
    """
    Convierte una distancia en una puntuación de proximidad entre 0 y 1.

    - 0 m      -> 1.0
    - 1200 m   -> todavía accesible
    - 2400 m+  -> 0.0
    """
    if pd.isna(distance_m):
        return 0.0

    score = 1 - (distance_m / MAX_PROFILE_DISTANCE_METERS)
    return max(0.0, min(1.0, score))

def calculate_profile_scores(zones):
    """
    Calcula scores personalizados según perfil:
    familia, estudiante y persona mayor.
    """
    for profile_name, weights in PROFILE_WEIGHTS.items():
        weighted_sum = 0
        total_weight = 0

        for category, weight in weights.items():
            proximity_col = f"proximity_{category}"

            if proximity_col in zones.columns:
                weighted_sum += zones[proximity_col] * weight
                total_weight += weight

        zones[f"score_{profile_name}"] = (weighted_sum / total_weight) * 100

    return zones

def main():
    print("1) Cargando zonas y servicios...")
    zones = gpd.read_file(DATA_PROCESSED / "zones.geojson").to_crs(CRS_WGS84)
    zone_points_wgs = gpd.read_file(DATA_PROCESSED / "zone_points.geojson").to_crs(CRS_WGS84)
    services_wgs = gpd.read_file(DATA_PROCESSED / "services.geojson").to_crs(CRS_WGS84)

    zones = zones.reset_index(drop=True)
    zone_points_wgs = zone_points_wgs.reset_index(drop=True)
    services_wgs = services_wgs.reset_index(drop=True)

    zone_points_m = zone_points_wgs.to_crs(CRS_METRIC)
    services_m = services_wgs.to_crs(CRS_METRIC)

    print("2) Cargando o descargando red peatonal...")
    G = load_or_download_walk_graph()

    print("3) Calculando distancias reales caminando por categoría...")

    for category in CATEGORIES:
        distances = calculate_category_walk_distances(
            G=G,
            zone_points_wgs=zone_points_wgs,
            zone_points_m=zone_points_m,
            services_wgs=services_wgs,
            services_m=services_m,
            category=category,
        )

        # Mantenemos el nombre dist_ para que los pasos siguientes sigan funcionando.
        zones[f"dist_{category}"] = distances
        zones[f"walkdist_{category}"] = distances

        # Accesibilidad binaria a 15 minutos
        zones[f"access_{category}"] = (
            zones[f"walkdist_{category}"] <= WALK_RADIUS_METERS
        ).astype(int)

        # Puntuación gradual de proximidad
        zones[f"proximity_{category}"] = zones[f"walkdist_{category}"].apply(proximity_score)

    print("4) Calculando score general de ciudad de 15 minutos...")
    access_cols = [f"access_{cat}" for cat in CATEGORIES]

    zones["services_count"] = zones[access_cols].sum(axis=1)
    zones["score_15min"] = zones["services_count"] / len(CATEGORIES) * 100

    print("5) Calculando scores personalizados por perfil...")
    zones = calculate_profile_scores(zones)

    print("6) Guardando resultados...")
    zones = zones.to_crs(CRS_WGS84)

    zones.to_file(DATA_PROCESSED / "zones_accessibility.geojson", driver="GeoJSON")
    zones.drop(columns="geometry").to_csv(
        DATA_PROCESSED / "zones_accessibility.csv",
        index=False,
    )

    print("7) Resumen del score general:")
    print(zones["score_15min"].describe())

    print("\n8) Resumen de scores por perfil:")
    profile_cols = [col for col in zones.columns if col.startswith("score_")]
    print(zones[profile_cols].describe())

    print("\n   OK -> data/processed/zones_accessibility.geojson")
    print("   OK -> data/processed/zones_accessibility.csv")

if __name__ == "__main__":
    main()