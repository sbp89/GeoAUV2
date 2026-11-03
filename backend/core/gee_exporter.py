"""
Generador Dinámico de Scripts Google Earth Engine (GEE) — GeoAUV2
Integra los 3 repositorios y artículos técnicos de M.Sc. Edwin Calle Condori (@eddycc66):
1. `sentinel2_descarga`: Basado en `Descargar_Imagen_sentinel/Descarga Imagen Sentinel.txt`
2. `multisensor_6modulos`: Basado en `Como un satélite puede señalar dónde buscar oro` (S2 + ASTER + Landsat)
3. `dzetsaka_rf_svm`: Basado en `Descarga y clasificación supervisada Sentinel-2` y `machine_learning.js` (RF + SVM + K-Means)
"""
from typing import Dict, List


def generate_gee_javascript(
    template_type: str,
    roi_name: str,
    bbox: List[float],
    start_date: str = "2023-01-01",
    end_date: str = "2026-10-01",
    cloud_cover_max: float = 15.0,
    ndvi_threshold: float = 0.45,
    deposit_model: str = "epitermal_as",
) -> Dict[str, str]:
    min_lon, min_lat, max_lon, max_lat = [round(float(x), 6) for x in bbox]
    safe_name = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in roi_name) or "GeoAUV2_ROI"

    if template_type == "sentinel2_descarga":
        title = "Descarga Compuestos Sentinel-2 L2A (Color Natural, Infrarrojo, SWIR y Geología)"
        code = f"""// ============================================================================
// GeoAUV2 — Módulo GEE 1: Descarga de Imagen Sentinel-2 L2A Armonizada (10 m)
// Basado en: M.Sc. Edwin Calle Condori (@eddycc66) - Descarga Imagen Sentinel.txt
// Región: {roi_name} | Ventana: {start_date} a {end_date}
// ============================================================================

var areaEstudio = ee.Geometry.Rectangle([{min_lon}, {min_lat}, {max_lon}, {max_lat}]);
Map.centerObject(areaEstudio, 13);

// 1. Filtrar colección Sentinel-2 Level-2A (Reflectancia de Superficie BOA)
var coleccionS2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(areaEstudio)
  .filterDate('{start_date}', '{end_date}')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', {cloud_cover_max}));

print('Escenas Sentinel-2 disponibles:', coleccionS2.size());

// 2. Reducción temporal por mediana (elimina nubes residuales y sombras transitorias)
var imagenMediana = coleccionS2.median().clip(areaEstudio).divide(10000);

// 3. Combinaciones de bandas clave (GEONORT)
Map.addLayer(imagenMediana, {{bands: ['B4', 'B3', 'B2'], min: 0.02, max: 0.30}}, '1. Color Natural (4-3-2)');
Map.addLayer(imagenMediana, {{bands: ['B8', 'B4', 'B3'], min: 0.03, max: 0.45}}, '2. Infrarrojo Vegetación (8-4-3)', false);
Map.addLayer(imagenMediana, {{bands: ['B12', 'B8A', 'B4'], min: 0.03, max: 0.42}}, '3. SWIR Alteración (12-8A-4)', false);
Map.addLayer(imagenMediana, {{bands: ['B12', 'B11', 'B2'], min: 0.03, max: 0.40}}, '4. Geología y Litología (12-11-2)', true);

// 4. Exportación a Google Drive a 10 metros en EPSG:4326
var bandasExportar = imagenMediana.select(['B2', 'B3', 'B4', 'B8', 'B8A', 'B11', 'B12']).toFloat();

Export.image.toDrive({{
  image: bandasExportar,
  description: 'S2_Multibanda_{safe_name}',
  folder: 'GeoAUV2_EarthEngine',
  region: areaEstudio,
  scale: 10,
  crs: 'EPSG:4326',
  maxPixels: 1e13
}});
"""
        return {"title": title, "template_type": template_type, "code": code}

    if template_type == "dzetsaka_rf_svm":
        title = "Clasificación Supervisada (Random Forest + SVM + Filtro Mayoritario + Matriz de Confusión)"
        code = f"""// ============================================================================
// GeoAUV2 — Módulo GEE 3: Clasificación Mineralógica Supervisada (RF + SVM + K-Means)
// Basado en: M.Sc. Edwin Calle Condori (@eddycc66) - DZetsaka & Cerro Rico ML
// Región: {roi_name}
// ============================================================================

var roi = ee.Geometry.Rectangle([{min_lon}, {min_lat}, {max_lon}, {max_lat}]);
Map.centerObject(roi, 13);

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(roi)
  .filterDate('{start_date}', '{end_date}')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', {cloud_cover_max}))
  .median()
  .clip(roi)
  .divide(10000);

// Índices diagnósticos para alteración hidrotermal y cobertura
var ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI');
var ndwi = s2.normalizedDifference(['B3', 'B8']).rename('NDWI');
var ndbi = s2.normalizedDifference(['B11', 'B8']).rename('NDBI');
var feox = s2.select('B4').divide(s2.select('B2')).rename('FEOX');
var cai  = s2.select('B11').divide(s2.select('B12')).rename('CAI');
var pai  = s2.select('B8A').divide(s2.select('B11')).rename('PAI');

var stack = s2.select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12'])
  .addBands([ndvi, ndwi, ndbi, feox, cai, pai]);

// Generación de semillas espectrales de entrenamiento con jerarquía mineralógica:
// 1=Argílica/Alunita, 2=Fílica/Sericita, 3=Gossan Fe3+, 4=Roca Fresca, 5=Vegetación
var clasesSemilla = ee.Image(4)
  .where(ndvi.gt({ndvi_threshold}), 5)
  .where(feox.gt(1.65).and(ndvi.lt({ndvi_threshold})), 3)
  .where(pai.gt(1.12).and(ndvi.lt({ndvi_threshold})), 2)
  .where(cai.gt(1.32).and(ndvi.lt({ndvi_threshold})), 1)
  .rename('clase')
  .clip(roi);

var muestras = stack.addBands(clasesSemilla).stratifiedSample({{
  numPoints: 180,
  classBand: 'clase',
  region: roi,
  scale: 20,
  seed: 42,
  geometries: true
}}).randomColumn('split', 42);

var trainSet = muestras.filter(ee.Filter.lt('split', 0.7));
var testSet  = muestras.filter(ee.Filter.gte('split', 0.7));
var bandasML = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'NDVI', 'FEOX', 'CAI', 'PAI'];

// Clasificador 1: Random Forest (100 árboles)
var rfModel = ee.Classifier.smileRandomForest(100).train({{
  features: trainSet,
  classProperty: 'clase',
  inputProperties: bandasML
}});

// Clasificador 2: Support Vector Machine (Kernel RBF)
var svmModel = ee.Classifier.libsvm({{kernelType: 'RBF', gamma: 0.5, cost: 10}}).train({{
  features: trainSet,
  classProperty: 'clase',
  inputProperties: bandasML
}});

// Post-procesamiento estilo DZetsaka: Filtro Mayoritario (focal_mode 3x3)
var mapaRF = stack.select(bandasML).classify(rfModel).focal_mode(1, 'square', 'pixels');
var mapaSVM = stack.select(bandasML).classify(svmModel).focal_mode(1, 'square', 'pixels');

// Validación Estadística: Matriz de Confusión, Precisión Global y Kappa
var validacionRF = testSet.classify(rfModel);
var matrizConfusion = validacionRF.errorMatrix('clase', 'classification');
print('Matriz de Confusión RF:', matrizConfusion);
print('Precisión Global (OA) RF:', matrizConfusion.accuracy());
print('Índice Kappa de Cohen RF:', matrizConfusion.kappa());

var paletaClases = ['#e74c3c', '#f39c12', '#d35400', '#5d6d7e', '#27ae60'];
Map.addLayer(mapaRF, {{min: 1, max: 5, palette: paletaClases}}, 'Clasificación Random Forest (Filtrada)');
Map.addLayer(mapaSVM, {{min: 1, max: 5, palette: paletaClases}}, 'Clasificación RBF-SVM', false);
"""
        return {"title": title, "template_type": template_type, "code": code}

    # Por defecto: multisensor_6modulos
    title = "Exploración Mineral Multisensor en 6 Módulos (Sentinel-2 + ASTER + Landsat + Cascada SWIR)"
    code = f"""// ============================================================================
// GeoAUV2 — Flujo Multisensor de 6 Módulos para Exploración Aurífera y Polimetálica
// Basado en: M.Sc. Edwin Calle Condori (@eddycc66) - GeoMineral AI v2 / GEONORT
// Región: {roi_name} | Modelo: {deposit_model}
// ============================================================================

var roi = ee.Geometry.Rectangle([{min_lon}, {min_lat}, {max_lon}, {max_lat}]);
Map.centerObject(roi, 13);

// MÓDULO 1: Adquisición Sentinel-2 L2A y Máscaras Ambientales
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(roi)
  .filterDate('{start_date}', '{end_date}')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', {cloud_cover_max}))
  .median()
  .clip(roi)
  .divide(10000);

var ndvi = s2.normalizedDifference(['B8', 'B4']);
var ndwi = s2.normalizedDifference(['B3', 'B8']);
var mascaraRoca = ndvi.lt({ndvi_threshold}).and(ndwi.lt(0.15));

// MÓDULO 2: ASTER L1T Histórico (Ventana SWIR funcional 2000 - Abril 2008) + Diagnóstico en Cascada
var asterCol = ee.ImageCollection('ASTER/AST_L1T_003')
  .filterBounds(roi)
  .filterDate('2000-03-01', '2008-04-28')
  .filter(ee.Filter.lt('CLOUDCOVER', 25));

var tieneAsterSWIR = asterCol.size().gt(0);
print('Escenas ASTER pre-2008 con SWIR activo:', asterCol.size());

// MÓDULO 3: Índices Sentinel-2 + Respaldo Landsat 8/9 Collection 2
var s2FeOx = s2.select('B4').divide(s2.select('B2')).updateMask(mascaraRoca).rename('S2_FEOX');
var s2Arcilla = s2.select('B11').divide(s2.select('B12')).updateMask(mascaraRoca).rename('S2_CAI');

var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
  .filterBounds(roi)
  .filterDate('{start_date}', '{end_date}')
  .filter(ee.Filter.lt('CLOUD_COVER', 25))
  .median()
  .clip(roi);
var l8SR = l8.select(['SR_B2', 'SR_B4', 'SR_B6', 'SR_B7']).multiply(0.0000275).add(-0.2);
var l8Arcilla = l8SR.select('SR_B6').divide(l8SR.select('SR_B7')).updateMask(mascaraRoca).rename('L8_CLAY');

// MÓDULO 4: Normalización Robusta por Percentiles P2 - P98
function normalizarP2P98(img, banda) {{
  var p = img.select(banda).reduceRegion({{
    reducer: ee.Reducer.percentile([2, 98]),
    geometry: roi,
    scale: 30,
    maxPixels: 1e9
  }});
  var p2 = ee.Number(p.get(banda + '_p2'));
  var p98 = ee.Number(p.get(banda + '_p98'));
  return img.select(banda).subtract(p2).divide(p98.subtract(p2)).clamp(0, 1);
}}

var nFeOx = normalizarP2P98(s2FeOx, 'S2_FEOX');
var nCAI  = normalizarP2P98(s2Arcilla, 'S2_CAI');
var nL8   = normalizarP2P98(l8Arcilla, 'L8_CLAY');

// MÓDULO 5: Integración Ponderada con Cascada Automática
var prospectividad = ee.Image(ee.Algorithms.If(
  tieneAsterSWIR,
  (function() {{
    var ast = asterCol.median().clip(roi);
    var ali = ast.select('B07').divide(ast.select('B05'))
      .multiply(ast.select('B07').divide(ast.select('B08')))
      .updateMask(mascaraRoca).rename('AST_ALI');
    var nALI = normalizarP2P98(ali, 'AST_ALI');
    return nALI.multiply(0.45).add(nCAI.multiply(0.25)).add(nFeOx.multiply(0.20)).add(nL8.multiply(0.10));
  }})(),
  // Cascada sin ASTER SWIR: redistribuye hacia S2 CAI (45%), S2 FeOx (35%) y Landsat (20%)
  nCAI.multiply(0.45).add(nFeOx.multiply(0.35)).add(nL8.multiply(0.20))
)).rename('PROSPECTIVIDAD');

// MÓDULO 6: Visualización Siempre Visible + Delineación de Targets Prioritarios (> 0.70)
Map.addLayer(s2, {{bands: ['B4', 'B3', 'B2'], min: 0.02, max: 0.28}}, 'Base RGB Sentinel-2 (Siempre Visible)');
Map.addLayer(prospectividad, {{min: 0, max: 1, palette: ['#120e24', '#8e245c', '#f39c12', '#fffccc']}}, 'Prospectividad Mineral');
Map.addLayer(prospectividad.gt(0.70).selfMask(), {{palette: ['#ff3b30']}}, 'Targets Prioridad 1 (> 0.70)');

Export.image.toDrive({{
  image: prospectividad.toFloat(),
  description: 'Prospectividad_GeoAUV2_{safe_name}',
  folder: 'GeoAUV2_EarthEngine',
  region: roi,
  scale: 20,
  crs: 'EPSG:4326',
  maxPixels: 1e13
}});
"""
    return {"title": title, "template_type": template_type, "code": code}
