import geopandas as gpd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

from config import DATA_PROCESSED, CATEGORIES, WALK_RADIUS_METERS, CRS_WGS84

def main():
    print("1) Cargando zonas con accesibilidad...")
    zones = gpd.read_file(DATA_PROCESSED / "zones_accessibility.geojson")

    feature_cols = [f"dist_{cat}" for cat in CATEGORIES]

    X = zones[feature_cols].fillna(WALK_RADIUS_METERS * 2)

    print("2) Escalando variables...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("3) Aplicando KMeans...")
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    zones["cluster"] = kmeans.fit_predict(X_scaled)

    zones.to_file(DATA_PROCESSED / "zones_clustered.geojson", driver="GeoJSON")
    zones.drop(columns="geometry").to_csv(DATA_PROCESSED / "zones_clustered.csv", index=False)

    print("4) Zonas por cluster:")
    print(zones["cluster"].value_counts().sort_index())

    print("   OK -> data/processed/zones_clustered.geojson")
    print("   OK -> data/processed/zones_clustered.csv")

if __name__ == "__main__":
    main()