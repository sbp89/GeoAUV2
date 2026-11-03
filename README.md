# GeoAuV2 — Plataforma Inteligente de Prospección Aurífera

Plataforma web integral de **Prospección Aurífera Multisensor, Inteligencia Artificial Espectral, Cartografía Satelital Libre de Nubes y Geofísica 3D**, diseñada para la identificación de depósitos de oro primario (vetas orogénicas, sistemas epitermales y pórfidos Au-Cu) y secundario (placeres y terrazas aluviales).

## Arquitectura y Capacidades Principales

1. **Cartografía Satelital HD Libre de Nubes**:
   - Mosaicos ópticos actualizados de alta resolución (`Google Satellite HD z20`, `Google Hybrid z20`, `EOX Sentinel-2 Cloudless 2024`, `ESRI World Imagery`, `OpenTopoMap` y `CARTO Dark`).
   - Capa conmutable de etiquetas territoriales (`CARTO Voyager Labels` + píldoras interactivas de municipios y ríos auríferos) y buscador omnibox con autocompletado local + OpenStreetMap Nominatim + soporte directo de coordenadas decimales y grados-minutos-segundos (`GMS / DMS`).
   - Síntesis radiométrica en servidor mediante teselas satelitales libres de nubes con cascada multi-anual y rechazo automático de aguas oceánicas abiertas.

2. **Visualización Avanzada de Depósitos de Oro**:
   - Capa principal **`🔥 Focos y Vetas de Oro`** con fondo estéril 100% transparente (`< 0.36`), interpolación bicúbica suave (`320×320`) e isocontornos luminosos de alta ley (`0.66` y `0.80`).
   - Capas especializadas: **`🌡️ Mapa Térmico Au`**, **`🌈 Prospectividad Continua`**, **`🟡 Vetas & Gossan`** y **`🌊 Placeres Aluviales`**.
   - Pines pulsantes numerados (`🎯 #1 · %`) en el punto exacto de máxima anomalía (`peak_lat`, `peak_lon`), diferenciados de minas de referencia (`🪙`), con estado legal ANM, coordenadas decimales/GMS, copia en 1 clic y enlace directo a Google Maps.
   - Visor espectral en vivo al pasar el cursor con veredicto geológico instantáneo (`🔥 NÚCLEO AURÍFERO P1`, `🌊 TERRAZA / PLACER ALUVIAL`, `⚡ VETA / HALO HIDROTERMAL`).

3. **Motor Multisensor (28 Índices Espectrales) y Normalización Robusta**:
   - Integración de **Sentinel-2 L2A** (10–20 m), **ASTER L1T** (VNIR + SWIR histórico pre-2008 + TIR) y **Landsat 8/9 OLI** (30 m).
   - División segura `sdiv(num, den)` con preservación de `NaN` y normalización por percentiles `P2–P98`, `P5–P95` o `Min-Max` con histograma de 24 intervalos.
   - Índice especializado de **Placeres Aluviales y Turbidez Activa (`ALLUVIAL_POWER` / `s2_aluvial_turbidez`)** para barras de grava cuaternarias, dragas y llanuras aluviales.

4. **Inteligencia Artificial Espectral y Geofísica 3D**:
   - **K-Means++ Estandarizado** con interpretación automática de firmas `z-score`.
   - **Clasificación Supervisada Interactiva (`Random Forest` y `RBF-SVM`)** con captura de muestras en el mapa, **Filtro Mayoritario (Modal)**, **Filtro Sieve (Tamizado)** y **Matriz de Confusión**.
   - **Similitud Espectral Coseno** con coherencia *Leave-One-Out* (`LOO`).
   - **Laboratorio de Magnetometría Terrestre 2D/3D**: Intensidad total $B = \sqrt{B_x^2 + B_y^2 + B_z^2}$ ($\mu\text{T}$), anomalía residual y detección de **Vacíos Magnéticos Hidrotermales** por destrucción de magnetita.

5. **Geología Oficial SGC, Cruce Catastral ANM por Target y Corte Topográfico–Aurífero A–B**:
   - Consultas espaciales en cascada al **Servicio Geológico Colombiano (SGC)** y **ANNA Minería (ANM)**.
   - Intersección geométrica individual de cada polígono prospectivo contra títulos y solicitudes vigentes (`🟢 Área Libre (Solicitable)` vs `🔵 Titulada ANM`).
   - **Radar Ejecutivo de 4 Pilares** (`Alteración`, `Estructural`, `Litología`, `Geofísica`) y **Corte Topográfico–Aurífero A–B** interactivo.

6. **Validación Estadística UTM y Exportación Directa a Campo**:
   - Proyección métrica UTM (`pyproj`), Precisión Global (`OA`), **Kappa de Cohen** y **Ganancia Espacial**.
   - Exportación directa en **`.GPX`** (navegadores GPS Garmin y móviles), **`.KML`** (Google Earth 3D), **`.GeoJSON`**, **`.CSV`**, proyecto **`.geoau`**, **Reporte Técnico HTML/PDF** y scripts para **Google Earth Engine (GEE)** con máscara de nubes `SCL`.

## Ejecución Local

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

## Pruebas Automatizadas

```bash
pytest -v
```
