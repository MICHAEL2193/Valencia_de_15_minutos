from pathlib import Path

# Rutas del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_MAPS = PROJECT_ROOT / "outputs" / "maps"
OUTPUT_PLOTS = PROJECT_ROOT / "outputs" / "plots"

# Parámetros generales
PLACE_NAME = "Valencia, Spain"
CITY_CENTER = [39.4699, -0.3763]

# CRS
CRS_WGS84 = "EPSG:4326"   # lat/lon
CRS_METRIC = "EPSG:25830" # metros, útil para España peninsular

# Aproximación de 15 minutos caminando
WALK_RADIUS_METERS = 1200

# Tamaño de cada celda de la cuadrícula (en metros)
GRID_SIZE_METERS = 1000

# Categorías a analizar
CATEGORIES = [
    "alimentacion",
    "farmacia",
    "salud",
    "educacion",
    "parque",
    "transporte",
]

# Colores por categoría
CATEGORY_COLORS = {
    "alimentacion": "blue",
    "farmacia": "purple",
    "salud": "red",
    "educacion": "darkgreen",
    "parque": "green",
    "transporte": "gray",
}

# Etiquetas OSM para descargar
OSM_TAGS = {
    "shop": ["supermarket", "convenience"],
    "amenity": ["pharmacy", "school", "library", "clinic", "hospital"],
    "leisure": ["park"],
    "highway": ["bus_stop"],
    "railway": ["station", "tram_stop", "subway_entrance"],
}

# -----------------------------
# Zonas oficiales de Valencia
# -----------------------------

# Opciones: "barrios" o "distritos"
ZONE_LEVEL = "barrios"

OFFICIAL_ZONES_URLS = {
    "barrios": "https://geoportal.valencia.es/server/rest/services/OPENDATA/UrbanismoEInfraestructuras/MapServer/224/query?where=1=1&outFields=%2A&f=geojson",
    "distritos": "https://geoportal.valencia.es/server/rest/services/OPENDATA/UrbanismoEInfraestructuras/MapServer/225/query?where=1=1&outFields=%2A&f=geojson",
}