# 🏙️ Valencia ciudad de 15 minutos

## 📌 Descripción del proyecto

Este proyecto analiza la **accesibilidad urbana de los barrios de Valencia** bajo el enfoque de la **ciudad de 15 minutos**.

La idea principal es estudiar si desde cada barrio es posible acceder caminando a servicios básicos como alimentación, farmacias, salud, educación, parques y transporte. Para ello se utilizan datos abiertos, análisis geoespacial, clustering y visualizaciones interactivas.

Además, el análisis se cruza con datos de vivienda para observar si existe alguna relación visual entre la accesibilidad urbana y los precios de alquiler o compra por metro cuadrado.

El resultado final es un **dashboard interactivo en Streamlit** y un **mapa interactivo en Folium** que permiten explorar los resultados de forma visual.

---

## 🎯 Objetivo

El objetivo principal del proyecto es responder a la siguiente pregunta:

> ¿Qué barrios de Valencia tienen mejor acceso caminando a servicios básicos y cómo se relaciona esa accesibilidad con los precios de vivienda?

Para responder esta pregunta se han desarrollado varias partes:

- Análisis de servicios urbanos obtenidos desde OpenStreetMap.
- Uso de barrios oficiales como unidad territorial.
- Cálculo de distancias caminables a servicios básicos.
- Creación de un score general de accesibilidad.
- Creación de scores específicos por perfil de usuario.
- Agrupación de barrios mediante clustering.
- Cruce con precios de alquiler y compra.
- Visualización de resultados mediante dashboard y mapa interactivo.

---

## 🧠 Concepto de ciudad de 15 minutos

La ciudad de 15 minutos es un modelo urbano que propone que las personas puedan acceder a los servicios esenciales de su vida diaria en un tiempo aproximado de 15 minutos caminando o en bicicleta.

En este proyecto se adapta esa idea para analizar barrios de Valencia, usando una distancia caminable aproximada compatible con ese concepto.

No se pretende medir la accesibilidad exacta desde cada vivienda, sino construir una aproximación territorial por barrio.

---

## 👥 ¿A quién puede beneficiar este proyecto?

Este análisis puede ser útil para:

- 👨‍👩‍👧 Familias que buscan barrios con colegios, parques, salud y servicios básicos cerca.
- 🎓 Estudiantes que necesitan transporte, alimentación y servicios educativos próximos.
- 👴 Personas mayores que necesitan farmacias, centros de salud y transporte accesible.
- 🏠 Personas que buscan vivienda y quieren comparar accesibilidad con precio.
- 🏛️ Administraciones públicas interesadas en detectar desigualdades urbanas.
- 📊 Analistas de datos urbanos que quieran trabajar con datos abiertos y geoespaciales.

---

## 📚 Fuentes de datos

### 🌍 OpenStreetMap

Se utilizó OpenStreetMap para obtener servicios urbanos y red caminable.

Servicios analizados:

- 🛒 Alimentación
- 💊 Farmacia
- 🏥 Salud
- 📚 Educación
- 🌳 Parques
- 🚌 Transporte

Acceso técnico:

- OpenStreetMap mediante la librería `osmnx`.
- Procesamiento geoespacial con `geopandas`.

---

### 🗺️ Barrios oficiales de Valencia

Fuente:

- Ayuntamiento de València.
- Portal de Datos Abiertos / Geoportal de València.
- Dataset: `Barris / Barrios`.
- Identificador habitual: `barris-barrios`.
- Formato utilizado: GeoJSON.

Uso en el proyecto:

- Definir los polígonos oficiales de los barrios.
- Trabajar con 88 barrios como unidad territorial del análisis.
- Calcular un punto representativo para cada barrio.

---

### 🏠 Datos de vivienda

Fuente:

- Data Enhance UV — Universitat de València.
- Dataset: `Precios de Compra y Alquiler de vivienda en los barrios de Valencia`.
- Autor: Javier Mora Jiménez.
- Fecha de publicación: 10 de mayo de 2024.
- Origen de los datos: Ayuntamiento de València + Idealista.

Uso en el proyecto:

- Añadir precio medio de alquiler por metro cuadrado.
- Añadir precio medio de compra por metro cuadrado.
- Cruzar accesibilidad urbana con vivienda.

Nota importante:

No todos los barrios tienen datos completos de vivienda. Por eso en algunos análisis aparecen barrios sin valor de alquiler o compra.

---

## 🛠️ Stack tecnológico

El proyecto utiliza principalmente herramientas del ecosistema Python para análisis de datos, geodatos, machine learning y visualización.

| Herramienta | Uso en el proyecto |
|---|---|
| `Python` | Lenguaje principal del proyecto |
| `pandas` | Limpieza, transformación y unión de tablas |
| `geopandas` | Manejo de datos geográficos y polígonos de barrios |
| `osmnx` | Consulta de datos desde OpenStreetMap y red caminable |
| `networkx` | Cálculo de rutas/distancias sobre grafos |
| `numpy` | Operaciones numéricas |
| `scikit-learn` | Clustering no supervisado de barrios |
| `folium` | Creación del mapa interactivo |
| `plotly` | Gráficos interactivos del dashboard |
| `streamlit` | Dashboard web interactivo |
| `GeoJSON` | Formato geográfico para mapas |
| `CSV` | Formato tabular para datos procesados |

---

## 🤖 Uso de aprendizaje no supervisado

En este proyecto se utiliza `scikit-learn` para aplicar clustering.

Se eligió aprendizaje no supervisado porque no se disponía de una variable objetivo etiquetada. Es decir, no existía una etiqueta oficial que dijera si un barrio era “bueno”, “malo”, “accesible” o “no accesible”.

El objetivo era descubrir patrones entre barrios según variables como:

- Distancia a alimentación.
- Distancia a farmacia.
- Distancia a salud.
- Distancia a educación.
- Distancia a parques.
- Distancia a transporte.
- Score de accesibilidad.

Por eso se aplicó clustering para agrupar barrios con comportamientos similares.

---

## 📏 Cómo se calcula la accesibilidad

Como no se dispone de domicilios reales ni de direcciones individuales, el proyecto no calcula la distancia desde cada vivienda.

En su lugar, se realiza una aproximación territorial:

1. Cada barrio se representa como un polígono.
2. A partir de ese polígono se calcula un punto representativo interno.
3. Desde ese punto se busca el servicio más cercano de cada categoría.
4. La distancia se calcula caminando por la red peatonal.
5. Con esas distancias se genera un score de accesibilidad.

El punto representativo se calcula a partir de la geometría del barrio, normalmente con herramientas geoespaciales como `GeoPandas` / `Shapely`.

Este punto no viene definido por OpenStreetMap. OpenStreetMap se utiliza para obtener servicios y red caminable.

---

## ⭐ Score de accesibilidad

El score de accesibilidad resume la proximidad a servicios básicos en una escala de 0 a 100.

Interpretación general:

| Score | Interpretación |
|---:|---|
| 80 - 100 | Alta accesibilidad |
| 60 - 79 | Accesibilidad media-alta |
| 40 - 59 | Accesibilidad intermedia |
| 0 - 39 | Baja accesibilidad |

Un score alto indica que el barrio tiene varios servicios básicos accesibles caminando desde su punto representativo.

---

## 👤 Perfiles de usuario

Además del score general, se crearon scores ponderados para distintos perfiles.

### 👨‍👩‍👧 Perfil familia

Da más importancia a:

- Educación
- Parques
- Salud
- Alimentación

### 🎓 Perfil estudiante

Da más importancia a:

- Transporte
- Educación
- Alimentación

### 👴 Perfil persona mayor

Da más importancia a:

- Salud
- Farmacia
- Transporte
- Alimentación

Esto permite analizar cómo cambia la accesibilidad según las necesidades de cada grupo.

---

## 🧩 Clustering de barrios

El clustering se utiliza para agrupar barrios con patrones similares de accesibilidad.

Es importante aclarar que un cluster no es una ubicación física, ni un nodo, ni un servidor. Un cluster representa un grupo de barrios que se parecen entre sí según sus variables de accesibilidad.

Para interpretar cada cluster se analizan:

- Número de barrios.
- Score medio.
- Servicios medios accesibles.
- Distancia media a cada servicio.
- Servicio más cercano de media.
- Servicio más lejano de media.

Esto permite pasar de una simple lista de barrios a una lectura más clara de patrones urbanos.

---

## 🏠 Vivienda y accesibilidad

El proyecto cruza la accesibilidad con precios de vivienda:

- Alquiler en €/m².
- Compra en €/m².

Los gráficos permiten observar si los barrios más accesibles son también más caros.

En los resultados obtenidos no se observa una relación visual directa fuerte entre accesibilidad general y precio. Esto no significa que la accesibilidad no influya nunca en el precio, sino que en este análisis la accesibilidad medida no explica por sí sola las diferencias de precio entre barrios.

El precio de vivienda puede depender de muchos otros factores:

- Centralidad.
- Cercanía al mar.
- Demanda turística.
- Renta media.
- Calidad de la vivienda.
- Antigüedad del parque inmobiliario.
- Oferta y demanda del mercado.

---

## 📁 Estructura del proyecto

```text
valencia-15min/
├── README.md
├── app/
│   └── dashboard.py
├── cache/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
│   ├── 01_descarga_datos.ipynb
│   ├── 02_analisis_accesibilidad.ipynb
│   └── 03_visualizaciones.ipynb
├── outputs/
│   ├── graficos/
│   ├── mapas/
│   └── tablas/
├── requirements.txt
└── src/
    ├── config.py
    ├── step1_download_data.py
    ├── step2_create_zones.py
    ├── step3_accessibility.py
    ├── step4_clustering.py
    ├── step5_plots.py
    └── step6_build_map.py