# GeoAUV2 — GeoMineral AI v2 Web Platform

Plataforma web integral de **Exploración Mineral Multisensor, Inteligencia Artificial Geocientífica y Magnetometría 3D**, recreada y evolucionada a partir de la metodología de **M.Sc. Edwin Calle Condori (`@eddycc66` / GEONORT / SpatialMind S.R.L.)** y el motor **GeoMineral AI v2**.

## Capacidades Científicas y Operativas (Flujo de 9 Pasos)

1. **Configuración Multisensor & Diagnóstico en Cascada**:
   - Integración de **Sentinel-2 L2A** (10–20 m), **ASTER L1T** (VNIR + SWIR histórico pre-2008 + TIR) y **Landsat 8/9 OLI** (30 m).
   - Relajación automática en cascada del filtro de nubosidad STAC y redistribución automática de pesos cuando la ventana temporal cae posterior a la falla del detector SWIR de ASTER (`2008-04-28`).
   - Enmascaramiento ambiental de vegetación (`NDVI`), cuerpos de agua (`NDWI`) y sombras topográficas.
2. **Índices Espectrales Corregidos (27) y Normalización Robusta**:
   - División segura `sdiv(num, den)` con umbral `|den| <= 1e-6 -> NaN` sin distorsión artificial.
   - **15 índices ASTER v2** (`alunita`, `aaa_rbd5`, `caolinita`, `sericita`, `ohi`, `mgoh_co3`, `clorita`, `calcita`, `fe3`, `fe2`, `gossan`, `cuarzo`, `silice`, `carbonatos`, `mafico`) + **9 índices Sentinel-2** + **3 índices Landsat 8/9** + **6 compuestos RGB** (`4-3-2`, `8-4-3`, `12-8A-4`, `12-11-2`, `11-8-2`, Ternario Mineralógico).
   - Normalización por percentiles `P2–P98`, `P5–P95` o `Min-Max` con histograma interactivo de 24 intervalos.
3. **Stack Multibanda ML**: Selección dinámica de bandas normalizadas `[0, 1]` con huella de memoria.
4. **IA Geocientífica (No Supervisada, Supervisada DZetsaka y Semisupervisada AlphaEarth)**:
   - **K-Means++ Estandarizado** con intérprete geológico automático de firmas `z-score`.
   - **Clasificación Supervisada Web estilo DZetsaka**: **Random Forest** y **Support Vector Machine (RBF-SVM)** con captura interactiva de muestras en el mapa, jerarquía mineralógica tipo Cerro Rico de Potosí, **Filtro Mayoritario (Modal)**, **Filtro Sieve (Tamizado)** y **Matriz de Confusión**.
   - **Similitud Coseno AlphaEarth**: Coherencia *Leave-One-Out* (`LOO`) y discriminación frente al fondo.
   - Catálogo técnico de arquitecturas **YOLO** aplicadas a testigos y afloramientos (`ME-YOLOv8`, `DW-YOLO`, `YOLOv8-SBI`, `YOLO-LDB`, `OreYOLO`).
5. **Favorabilidad Espectral Mineral**: Modelos genéticos preconfigurados (`epitermal_as`, `epitermal_bs`, `porfido`, `orogenico_vetas`, `polimetalico`, `aluvial_placer`) sin doble normalización.
6. **Prospectividad Integrada, Geología Oficial SGC, Catastro ANM & Magnetometría 3D**:
   - Pendiente métrica corregida por latitud $\cos(\varphi)$ y densidad circular de lineamientos Sobel (4 acimuts).
   - Consultas espaciales concurrentes al **Servicio Geológico Colombiano (SGC)** y **ANNA Minería (ANM)**.
   - **Laboratorio de Magnetometría Terrestre 2D/3D**: Cálculo de intensidad total $B = \sqrt{B_x^2 + B_y^2 + B_z^2}$ ($\mu\text{T}$), anomalía residual y detección de **Vacíos Magnéticos Hidrotermales ("Valles Azules")** por destrucción de magnetita.
7. **Targets Priorizados (`P1 / P2 / P3`)**: Componentes conexos de 8 vecinos, área geodésica en hectáreas y exportación GeoJSON / CSV.
8. **Validación Estadística Rigurosa**: Proyección métrica UTM (`pyproj`), distancia exacta al borde del polígono (`0 m` en interior), Precisión Global (`OA`), **Kappa de Cohen** con escala de **Landis & Koch (1977)** y **Ganancia Espacial**.
9. **Reportes Técnicos, Persistencia Supabase & Google Earth Engine (GEE)**:
   - Plan de exploración en 3 fases del **Asesor GeoAI**, reporte autónomo HTML/PDF imprimible, archivos `.geominer` y generador dinámico de scripts **Google Earth Engine** (`Descarga Sentinel-2`, `Multisensor 6 Módulos`, `Clasificación Supervisada RF+SVM`).

## Ejecución Local

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

## Pruebas Automatizadas

```bash
pytest -v
```
