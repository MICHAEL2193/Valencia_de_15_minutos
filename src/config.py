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

# -----------------------------
# Mejora: rutas reales caminando
# -----------------------------
WALK_GRAPH_PATH = DATA_RAW / "valencia_walk.graphml"

# Número de servicios candidatos por categoría.
# Primero buscamos los más cercanos en línea recta y luego calculamos ruta real.
K_NEAREST_CANDIDATES = 8

# Distancia máxima para valorar proximidad.
# 1200 m = accesible en 15 min aprox.
# 2400 m = muy lejos para este análisis.
MAX_PROFILE_DISTANCE_METERS = 2400


# -----------------------------
# Mejora: perfiles de usuario
# -----------------------------
PROFILE_WEIGHTS = {
    "familia": {
        "alimentacion": 1.0,
        "farmacia": 1.0,
        "salud": 1.2,
        "educacion": 1.5,
        "parque": 1.3,
        "transporte": 1.0,
    },
    "estudiante": {
        "alimentacion": 1.2,
        "farmacia": 0.8,
        "salud": 0.8,
        "educacion": 1.5,
        "parque": 0.8,
        "transporte": 1.5,
    },
    "persona_mayor": {
        "alimentacion": 1.3,
        "farmacia": 1.6,
        "salud": 1.6,
        "educacion": 0.4,
        "parque": 1.0,
        "transporte": 1.4,
    },
}