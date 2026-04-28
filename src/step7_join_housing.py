import unicodedata
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from config import DATA_RAW, DATA_PROCESSED, OUTPUT_PLOTS, CRS_WGS84


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def normalize_name(value):
    """
    Normaliza nombres de barrios para facilitar el cruce entre datasets.

    Ejemplos:
    - "L'AMISTAT" -> "AMISTAT"
    - "El Carme" -> "CARME"
    - "Sant Marcel·lí" -> "SANT MARCELLI"
    """
    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    # Quitar acentos
    value = unicodedata.normalize("NFKD", value)
    value = "".join([c for c in value if not unicodedata.combining(c)])

    replacements = {
        "L'": "",
        "D'": "",
        "L´": "",
        "D´": "",
        "LA ": "",
        "EL ": "",
        "ELS ": "",
        "LES ": "",
        "LOS ": "",
        "LAS ": "",
        "-": " ",
        "_": " ",
        ".": "",
        ",": "",
        "'": "",
        "’": "",
        "·": "",
        "  ": " ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = " ".join(value.split())

    return value


def clean_numeric_column(series):
    """
    Convierte una columna a numérica aunque venga con coma decimal,
    espacios o símbolos.
    """
    return (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace(" ", "", regex=False)
        .replace(["nan", "None", "", "NaN"], pd.NA)
        .pipe(pd.to_numeric, errors="coerce")
    )


def load_zones():
    """
    Carga el dataset de zonas más avanzado disponible.

    Prioridad:
    1. zones_clustered.geojson
    2. zones_accessibility.geojson
    """
    clustered_path = DATA_PROCESSED / "zones_clustered.geojson"
    accessibility_path = DATA_PROCESSED / "zones_accessibility.geojson"

    if clustered_path.exists():
        print("   Usando data/processed/zones_clustered.geojson")
        return gpd.read_file(clustered_path).to_crs(CRS_WGS84)

    if accessibility_path.exists():
        print("   Usando data/processed/zones_accessibility.geojson")
        return gpd.read_file(accessibility_path).to_crs(CRS_WGS84)

    raise FileNotFoundError(
        "No se encontró zones_clustered.geojson ni zones_accessibility.geojson. "
        "Ejecuta antes step3_accessibility.py y step4_clustering.py."
    )


def load_housing():
    """
    Carga el dataset de vivienda preparado desde Data Enhance UV.

    Espera un CSV con columnas:
    - zone_name
    - rent_eur_m2
    - sale_eur_m2
    """
    housing_path = DATA_RAW / "housing_prices.csv"

    if not housing_path.exists():
        raise FileNotFoundError(
            "No existe data/raw/housing_prices.csv.\n"
            "Primero ejecuta src/step0_prepare_housing_dataset.py "
            "o crea el CSV manualmente."
        )

    housing = pd.read_csv(housing_path)

    required_cols = ["zone_name", "rent_eur_m2", "sale_eur_m2"]

    missing_cols = [col for col in required_cols if col not in housing.columns]

    if missing_cols:
        raise ValueError(
            f"El CSV de vivienda no tiene las columnas requeridas: {missing_cols}\n"
            "Debe contener al menos: zone_name,rent_eur_m2,sale_eur_m2"
        )

    housing["rent_eur_m2"] = clean_numeric_column(housing["rent_eur_m2"])
    housing["sale_eur_m2"] = clean_numeric_column(housing["sale_eur_m2"])

    return housing


def create_housing_status_columns(merged):
    """
    Crea columnas para indicar si una zona tiene datos de vivienda o no.
    """
    merged["has_housing_data"] = (
        merged["rent_eur_m2"].notna() | merged["sale_eur_m2"].notna()
    ).astype(int)

    merged["housing_data_status"] = merged["has_housing_data"].map(
        {
            1: "Con datos de vivienda",
            0: "Sin datos de vivienda",
        }
    )

    return merged


def create_clean_housing_columns(merged):
    """
    Crea columnas limpias para gráficos, sin eliminar los datos originales.

    rent_eur_m2:
    - dato original de alquiler

    rent_eur_m2_clean:
    - dato usado para gráficos
    - valores sospechosamente bajos se marcan como NA

    Esto permite mantener la trazabilidad del dato original.
    """
    merged["rent_eur_m2_clean"] = merged["rent_eur_m2"]
    merged["sale_eur_m2_clean"] = merged["sale_eur_m2"]

    # Alquileres menores a 5 €/m² se consideran sospechosos para análisis visual.
    # Ejemplo detectado: Torrefiel con 3 €/m².
    merged.loc[
        merged["rent_eur_m2_clean"].notna() & (merged["rent_eur_m2_clean"] < 5),
        "rent_eur_m2_clean",
    ] = pd.NA

    return merged


def print_merge_quality(merged):
    """
    Muestra un resumen de la calidad del cruce.
    """
    total = len(merged)

    with_rent = merged["rent_eur_m2"].notna().sum()
    with_sale = merged["sale_eur_m2"].notna().sum()
    with_any = merged["has_housing_data"].sum()

    print("\n5) Calidad del cruce con vivienda:")
    print(f"   Total zonas del proyecto: {total}")
    print(f"   Zonas con alquiler: {with_rent}/{total}")
    print(f"   Zonas con compra: {with_sale}/{total}")
    print(f"   Zonas con algún dato económico: {with_any}/{total}")

    print("\n6) Zonas sin datos de vivienda:")
    missing = merged[merged["has_housing_data"] == 0]

    cols = ["zone_id", "zone_name"]

    cols = [col for col in cols if col in missing.columns]

    if len(missing) == 0:
        print("   Todas las zonas tienen algún dato de vivienda.")
    else:
        print(missing[cols].to_string(index=False))

    print("\n7) Posibles valores anómalos de alquiler original:")
    outliers = merged[
        merged["rent_eur_m2"].notna() & (merged["rent_eur_m2"] < 5)
    ]

    if len(outliers) == 0:
        print("   No se detectaron alquileres por debajo de 5 €/m².")
    else:
        cols = ["zone_id", "zone_name", "rent_eur_m2", "sale_eur_m2"]
        cols = [col for col in cols if col in outliers.columns]
        print(outliers[cols].to_string(index=False))


def save_outputs(merged):
    """
    Guarda el dataset enriquecido en GeoJSON y CSV.
    """
    output_geojson = DATA_PROCESSED / "zones_enriched.geojson"
    output_csv = DATA_PROCESSED / "zones_enriched.csv"

    merged.to_file(output_geojson, driver="GeoJSON")
    merged.drop(columns="geometry").to_csv(output_csv, index=False)

    print("\n8) Archivos guardados:")
    print(f"   OK -> {output_geojson}")
    print(f"   OK -> {output_csv}")


def create_housing_plots(merged):
    """
    Crea gráficos de accesibilidad vs alquiler/compra.
    """
    OUTPUT_PLOTS.mkdir(parents=True, exist_ok=True)

    if "score_15min" not in merged.columns:
        print("\n⚠️ No existe score_15min. No se crearán gráficos de vivienda.")
        return

    print("\n9) Creando gráficos de vivienda...")

    # --------------------------------------------------------
    # Gráfico: score vs alquiler limpio
    # --------------------------------------------------------
    rent_df = merged[
        merged["rent_eur_m2_clean"].notna() & merged["score_15min"].notna()
    ].copy()

    if len(rent_df) > 0:
        plt.figure(figsize=(8, 6))
        plt.scatter(rent_df["rent_eur_m2_clean"], rent_df["score_15min"])
        plt.title("Relación entre alquiler y accesibilidad 15 minutos")
        plt.xlabel("Alquiler limpio €/m²")
        plt.ylabel("Score 15 minutos")
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOTS / "06_score_vs_rent.png")
        plt.close()

        print("   OK -> outputs/plots/06_score_vs_rent.png")
    else:
        print("   No hay datos suficientes para gráfico de alquiler.")

    # --------------------------------------------------------
    # Gráfico: score vs compra
    # --------------------------------------------------------
    sale_df = merged[
        merged["sale_eur_m2_clean"].notna() & merged["score_15min"].notna()
    ].copy()

    if len(sale_df) > 0:
        plt.figure(figsize=(8, 6))
        plt.scatter(sale_df["sale_eur_m2_clean"], sale_df["score_15min"])
        plt.title("Relación entre precio de compra y accesibilidad 15 minutos")
        plt.xlabel("Precio compra €/m²")
        plt.ylabel("Score 15 minutos")
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOTS / "07_score_vs_sale.png")
        plt.close()

        print("   OK -> outputs/plots/07_score_vs_sale.png")
    else:
        print("   No hay datos suficientes para gráfico de compra.")

    # --------------------------------------------------------
    # Gráfico: cobertura de datos de vivienda
    # --------------------------------------------------------
    status_counts = merged["housing_data_status"].value_counts()

    plt.figure(figsize=(7, 5))
    status_counts.plot(kind="bar")
    plt.title("Cobertura de datos de vivienda por zona")
    plt.xlabel("Estado del dato")
    plt.ylabel("Número de zonas")
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOTS / "08_housing_data_coverage.png")
    plt.close()

    print("   OK -> outputs/plots/08_housing_data_coverage.png")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():
    print("1) Cargando zonas con accesibilidad y clustering...")
    zones = load_zones()

    if "zone_name" not in zones.columns:
        raise ValueError(
            "El dataset de zonas no tiene columna zone_name. "
            "Revisa step2_create_zones.py."
        )

    print("2) Cargando dataset de vivienda/alquiler...")
    housing = load_housing()

    print("3) Normalizando nombres de barrios para el cruce...")
    zones["zone_key"] = zones["zone_name"].apply(normalize_name)
    housing["zone_key"] = housing["zone_name"].apply(normalize_name)

    print("4) Cruzando accesibilidad con vivienda...")
    merged = zones.merge(
        housing,
        on="zone_key",
        how="left",
        suffixes=("", "_housing"),
    )

    # Si aparece zone_name_housing, no lo necesitamos.
    if "zone_name_housing" in merged.columns:
        merged = merged.drop(columns=["zone_name_housing"])

    # Añadir columnas de estado y limpieza
    merged = create_housing_status_columns(merged)
    merged = create_clean_housing_columns(merged)

    # Mostrar resumen de calidad
    print_merge_quality(merged)

    # Guardar resultados
    save_outputs(merged)

    # Crear gráficos
    create_housing_plots(merged)

    print("\n✅ Proceso completado correctamente.")


if __name__ == "__main__":
    main()