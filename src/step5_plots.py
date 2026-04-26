import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from config import DATA_PROCESSED, OUTPUT_PLOTS

def main():
    OUTPUT_PLOTS.mkdir(parents=True, exist_ok=True)
    print("1) Cargando datos...")
    services = pd.read_csv(DATA_PROCESSED / "services.csv")
    zones = pd.read_csv(DATA_PROCESSED / "zones_clustered.csv")

    print("2) Conteo de servicios por categoría...")
    counts = services["categoria"].value_counts().sort_values(ascending=False)
    plt.figure(figsize=(8, 5))
    counts.plot(kind="bar")
    plt.title("Número de servicios por categoría")
    plt.xlabel("Categoría")
    plt.ylabel("Cantidad")
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOTS / "01_service_counts.png")
    plt.close()

    print("3) Histograma del score...")
    plt.figure(figsize=(8, 5))
    plt.hist(zones["score_15min"], bins=10)
    plt.title("Distribución del score de accesibilidad")
    plt.xlabel("Score 15 min")
    plt.ylabel("Número de zonas")
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOTS / "02_score_histogram.png")
    plt.close()

    print("4) Top 10 zonas...")
    label_col = "zone_name" if "zone_name" in zones.columns else "zone_id"

    top10 = zones.sort_values("score_15min", ascending=False).head(10)
    plt.figure(figsize=(10, 6))
    plt.barh(top10[label_col], top10["score_15min"])

    plt.title("Top 10 zonas con mejor accesibilidad")
    plt.xlabel("Score 15 min")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOTS / "03_top10_zones.png")
    plt.close()

    print("5) Peores 10 zonas...")
    bottom10 = zones.sort_values("score_15min", ascending=True).head(10)
    plt.figure(figsize=(10, 6))
    plt.barh(bottom10[label_col], bottom10["score_15min"])

    plt.title("10 zonas con peor accesibilidad")
    plt.xlabel("Score 15 min")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOTS / "04_bottom10_zones.png")
    plt.close()

    print("6) Zonas por cluster...")
    cluster_counts = zones["cluster"].value_counts().sort_index()
    plt.figure(figsize=(8, 5))
    cluster_counts.plot(kind="bar")
    plt.title("Número de zonas por cluster")
    plt.xlabel("Cluster")
    plt.ylabel("Cantidad de zonas")
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOTS / "05_cluster_counts.png")
    plt.close()

    print("   OK -> outputs/plots/")
    print("   Archivos generados:")
    print("   - 01_service_counts.png")
    print("   - 02_score_histogram.png")
    print("   - 03_top10_zones.png")
    print("   - 04_bottom10_zones.png")
    print("   - 05_cluster_counts.png")

if __name__ == "__main__":
    main()