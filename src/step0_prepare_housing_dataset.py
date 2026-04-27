import pandas as pd
import geopandas as gpd
from pathlib import Path


# ============================================================
# RUTAS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

INPUT_GPKG = DATA_RAW / "precio_compra_alquiler.gpkg"
OUTPUT_CSV = DATA_RAW / "housing_prices.csv"
OUTPUT_GEOJSON = DATA_PROCESSED / "housing_prices.geojson"


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def detect_column(df, candidates):
    """
    Busca una columna dentro del DataFrame usando una lista de nombres posibles.
    """
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def clean_numeric_column(series):
    """
    Convierte columnas numéricas que puedan venir como texto,
    con coma decimal o caracteres extraños.
    """
    return (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace(" ", "", regex=False)
        .replace(["nan", "None", ""], pd.NA)
        .pipe(pd.to_numeric, errors="coerce")
    )


def main():
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    if not INPUT_GPKG.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {INPUT_GPKG}\n"
            "Descarga el dataset GPKG desde Data Enhance UV y guárdalo en data/raw/"
        )

    print("1) Leyendo dataset GPKG de compra y alquiler...")
    gdf = gpd.read_file(INPUT_GPKG)

    print("\n2) Columnas encontradas:")
    for col in gdf.columns:
        print(f"   - {col}")

    print(f"\n3) Número de registros: {len(gdf)}")

    # Columnas esperadas según la descripción del dataset Data Enhance UV
    barrio_col = detect_column(
        gdf,
        [
            "barrio",
            "BARRIO",
            "barri",
            "BARRI",
            "zone_name",
            "nombre",
            "NOMBRE",
            "nom_barri",
            "NOM_BARRI",
        ],
    )

    distrito_col = detect_column(
        gdf,
        [
            "distrito",
            "DISTRITO",
            "districte",
            "DISTRICTE",
            "nom_districte",
            "NOM_DISTRICTE",
        ],
    )

    compra_col = detect_column(
        gdf,
        [
            "Precio_Compra_2022",
            "precio_compra_2022",
            "PRECIO_COMPRA_2022",
            "precio_2022",
            "Precio Compra 2022",
            "sale_eur_m2",
        ],
    )

    alquiler_col = detect_column(
        gdf,
        [
            "Precio_Alquiler_2022",
            "precio_alquiler_2022",
            "PRECIO_ALQUILER_2022",
            "Precio_2022 (Euros/m2)",
            "Precio Alquiler 2022",
            "rent_eur_m2",
        ],
    )

    if barrio_col is None:
        raise ValueError(
            "No se pudo detectar la columna del barrio. "
            "Revisa las columnas impresas arriba."
        )

    if compra_col is None:
        raise ValueError(
            "No se pudo detectar la columna de precio de compra. "
            "Revisa las columnas impresas arriba."
        )

    if alquiler_col is None:
        raise ValueError(
            "No se pudo detectar la columna de precio de alquiler. "
            "Revisa las columnas impresas arriba."
        )

    print("\n4) Columnas detectadas:")
    print(f"   Barrio: {barrio_col}")
    print(f"   Distrito: {distrito_col}")
    print(f"   Compra €/m²: {compra_col}")
    print(f"   Alquiler €/m²: {alquiler_col}")

    # Crear CSV limpio para el proyecto
    cols_to_keep = [barrio_col, compra_col, alquiler_col]

    if distrito_col is not None:
        cols_to_keep.insert(1, distrito_col)

    df = gdf[cols_to_keep].copy()

    rename_map = {
        barrio_col: "zone_name",
        compra_col: "sale_eur_m2",
        alquiler_col: "rent_eur_m2",
    }

    if distrito_col is not None:
        rename_map[distrito_col] = "district_name"

    df = df.rename(columns=rename_map)

    df["zone_name"] = df["zone_name"].astype(str).str.strip()
    df["sale_eur_m2"] = clean_numeric_column(df["sale_eur_m2"])
    df["rent_eur_m2"] = clean_numeric_column(df["rent_eur_m2"])

    df["source"] = "Data Enhance UV / Ayuntamiento València / Idealista"
    df["notes"] = "Precios de compra y alquiler por metro cuadrado en barrios de Valencia"

    # El dataset de Data Enhance ya elimina nulos, pero volvemos a asegurar limpieza
    df = df.dropna(subset=["zone_name"])
    df = df.drop_duplicates(subset=["zone_name"])

    print("\n5) Vista previa del CSV final:")
    print(df.head(10))

    print("\n6) Guardando CSV para cruce con el proyecto...")
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"   OK -> {OUTPUT_CSV}")

    # Guardar también una copia geográfica para evidencia/mapas opcionales
    print("\n7) Guardando GeoJSON del dataset de vivienda...")
    gdf_out = gdf.copy()
    gdf_out.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

    print(f"   OK -> {OUTPUT_GEOJSON}")

    print("\n8) Resumen numérico:")
    print(df[["rent_eur_m2", "sale_eur_m2"]].describe())


if __name__ == "__main__":
    main()
