import unicodedata
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from config import DATA_RAW, DATA_PROCESSED, OUTPUT_PLOTS, CRS_WGS84

def normalize_name(value):
    """
    Normaliza nombres para poder cruzar barrios aunque tengan acentos,
    mayúsculas, guiones o apóstrofes.
    """
    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    value = unicodedata.normalize("NFKD", value)
    value = "".join([c for c in value if not unicodedata.combining(c)])

    replacements = {
        "L'": "",
        "LA ": "",
        "EL ": "",
        "ELS ": "",
        "LES ": "",
        "-": " ",
        "_": " ",
        ".": "",
        ",": "",
        "'": "",
        "’": "",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = " ".join(value.split())

    return value

def main():
    OUTPUT_PLOTS.mkdir(parents=True, exist_ok=True)

    zones_path = DATA_PROCESSED / "zones_clustered.geojson"
    housing_path = DATA_RAW / "housing_prices.csv"

    print("1) Cargando zonas con accesibilidad y clustering...")
    zones = gpd.read_file(zones_path).to_crs(CRS_WGS84)

    if not housing_path.exists():
        print("⚠️ No existe data/raw/housing_prices.csv")
        print("Crea ese archivo con columnas:")
        print("zone_name,rent_eur_m2,sale_eur_m2")
        return

    print("2) Cargando datos de vivienda/alquiler...")
    housing = pd.read_csv(housing_path)

    if "zone_name" not in housing.columns:
        raise ValueError("El CSV de vivienda debe tener una columna zone_name")

    zones["zone_key"] = zones["zone_name"].apply(normalize_name)
    housing["zone_key"] = housing["zone_name"].apply(normalize_name)

    print("3) Cruzando datos por nombre de barrio...")
    merged = zones.merge(
        housing,
        on="zone_key",
        how="left",
        suffixes=("", "_housing"),
    )

    # Limpiar columnas duplicadas
    if "zone_name_housing" in merged.columns:
        merged = merged.drop(columns=["zone_name_housing"])

    matched = merged["rent_eur_m2"].notna().sum() if "rent_eur_m2" in merged.columns else 0
    total = len(merged)

    print(f"   Barrios cruzados con alquiler: {matched}/{total}")

    print("4) Guardando dataset enriquecido...")
    merged.to_file(DATA_PROCESSED / "zones_enriched.geojson", driver="GeoJSON")
    merged.drop(columns="geometry").to_csv(
        DATA_PROCESSED / "zones_enriched.csv",
        index=False,
    )

    print("5) Creando gráfico score vs alquiler...")
    if "rent_eur_m2" in merged.columns:
        plot_df = merged[merged["rent_eur_m2"].notna()].copy()

        if len(plot_df) > 0:
            plt.figure(figsize=(8, 6))
            plt.scatter(plot_df["rent_eur_m2"], plot_df["score_15min"])
            plt.title("Relación entre alquiler y accesibilidad 15 minutos")
            plt.xlabel("Alquiler €/m²")
            plt.ylabel("Score 15 minutos")
            plt.tight_layout()
            plt.savefig(OUTPUT_PLOTS / "06_score_vs_rent.png")
            plt.close()

    print("6) Creando gráfico score vs precio de compra...")
    if "sale_eur_m2" in merged.columns:
        plot_df = merged[merged["sale_eur_m2"].notna()].copy()

        if len(plot_df) > 0:
            plt.figure(figsize=(8, 6))
            plt.scatter(plot_df["sale_eur_m2"], plot_df["score_15min"])
            plt.title("Relación entre precio de compra y accesibilidad 15 minutos")
            plt.xlabel("Precio compra €/m²")
            plt.ylabel("Score 15 minutos")
            plt.tight_layout()
            plt.savefig(OUTPUT_PLOTS / "07_score_vs_sale.png")
            plt.close()

    print("\n   OK -> data/processed/zones_enriched.geojson")
    print("   OK -> data/processed/zones_enriched.csv")
    print("   OK -> outputs/plots/06_score_vs_rent.png")
    print("   OK -> outputs/plots/07_score_vs_sale.png")

if __name__ == "__main__":
    main()
