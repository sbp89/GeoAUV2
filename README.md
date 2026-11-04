# GeoAuV2 v2.3 — Plataforma Científica de Prefactibilidad y Prospección Aurífera

Plataforma web integral de **Prefactibilidad y Prospección Aurífera Multisensor, Reflectancia Superficial 16-bit Real, Elevación Radar 30 m, Inteligencia Artificial Espectral y Geofísica 3D**, diseñada para estudios de exploración temprana (*Greenfield / Brownfield*) de depósitos de oro primario (vetas orogénicas, sistemas epitermales y pórfidos Au-Cu) y secundario (placeres y terrazas aluviales).

## Arquitectura y Capacidades Principales

1. **Rigor Radiométrico y Topográfico de Prefactibilidad**:
   - Ingesta directa en servidor de reflectancia superficial real **Sentinel-2 L2A COG BOA (16-bit)** (`B02..B12` + clasificación de escena `SCL`) mediante lecturas HTTP Range nativas, con mosaico multi-escena para relleno limpio de nubes.
   - Modelo digital de elevación oficial **Copernicus DEM GLO-30 (`float32`, 30 m)** para cálculo riguroso de pendientes y densidad de lineamientos estructurales.
   - Separación estricta entre **capas base visuales 8-bit** (`Google Satellite HD z20`, `Google Hybrid z20`, `EOX Sentinel-2 Cloudless 2024`, `ESRI World Imagery`) y el **cubo espectral analítico 16-bit**, respetando físicamente la ventana operativa SWIR histórica de ASTER (`<= 2008-04-28`).
   - Exclusión automática de techos/infraestructura urbana (`mask_urban`), preservación estricta de evidencia observada (`NaN` bajo bosque denso o nubes sin extrapolar targets falsos), compuerta física de amplitud mineralógica (`P90`) y aislamiento exclusivo del índice `ALLUVIAL_POWER` para el modelo `aluvial_placer` en llanuras (`pendiente <= 9.5°`).

2. **Transparencia Metodológica ("🔬 ¿Qué se está usando?")**:
   - Auditoría en tiempo real (`methodology_audit`) integrada en la cabecera (`🔬 Qué se usa`), panel ejecutivo, módulos laterales y reporte PDF/HTML imprimible.
   - Desglose porcentual exacto de cobertura superficial analizada (`Roca/Suelo Expuesto`, `Vegetación Enmascarada`, `Urbano Excluido`, `Agua`, `Nubes/Sombras`), ecuaciones espectrales activas, hiperparámetros de IA y alcance normativo de prefactibilidad.

3. **Visualización Avanzada y Experiencia Móvil / Escritorio**:
   - Capa principal **`🔥 Focos y Vetas de Oro`** con convolución normalizada sin sangrado de bordes (`NaN`-safe), barra rápida flotante de 1 clic (`#quickLayerBar`) y botón **`👁️ Ver Roca Base`** (*Hold-to-Peek* o tecla `Espacio`) para inspeccionar afloramientos reales bajo la anomalía.
   - Interfaz responsiva nativa (`100dvh`) para **móviles y tablets** con navegación inferior táctil (`🗺️ Mapa`, `⚙️ Módulos`, `📊 Resumen Au`, `🔬 Qué se usa`) y rotación táctil 3D en magnetometría.

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
