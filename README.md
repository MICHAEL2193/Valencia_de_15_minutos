# Valencia ciudad de 15 minutos

## Objetivo
Analizar la accesibilidad urbana a servicios básicos en Valencia.

## Datos
OpenStreetMap.

## Servicios analizados
- alimentación
- farmacia
- salud
- educación
- parque
- transporte

## Metodología
- descarga de datos
- creación de zonas
- cálculo de distancias
- score de accesibilidad
- clustering
- mapa y dashboard

## Limitaciones
(...)

## Ejecución
python3 src/step1_download_data.py
...
streamlit run app/dashboard.py