"""
Configuración Maestra del Sistema GeoAUV2 (GeoMineral AI v2 Web Platform)
Integra la metodología multisensor y de IA geocientífica de M.Sc. Edwin Calle Condori (@eddycc66):
- Sentinel-2 L2A (10m-20m) + ASTER L1T (VNIR/SWIR/TIR) + Landsat 8/9 OLI/TIRS
- 15 Índices Espectrales ASTER v2 corregidos + Índices Sentinel-2 / Landsat + Compuestos RGB
- Clasificación No Supervisada (K-Means++) y Supervisada tipo DZetsaka (Random Forest + SVM + Majority/Sieve)
- Similitud Coseno Semisupervisada (AlphaEarth LOO)
- Magnetometría Terrestre 2D/3D y Detección de Vacíos Magnéticos Hidrotermales
- Validación Estadística (Matriz de Confusión, Kappa de Cohen, Ganancia Espacial)
- Servicios Oficiales SGC (Colombia), ANM (Catastro Minero) y Persistencia en Supabase
"""
import os
from typing import Dict, Any, List

APP_NAME = "GeoAUV2"
APP_TITLE = "GeoAUV2 — GeoMineral AI v2 Plataforma Multisensor"
APP_VERSION = "2.0.0"

SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8000"))

# Credenciales de Supabase leídas desde variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
).strip()
CRON_SECRET = os.getenv("CRON_SECRET", "").strip()

# Servicios Oficiales Servicio Geológico Colombiano (SGC) - ArcGIS REST Mapa Geológico 2023
SGC_BASE_MAPSERVER = "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Geologico_Colombia/Mapa_Geologico_Colombia_2023/MapServer"
SGC_FALLAS_URL = f"{SGC_BASE_MAPSERVER}/12"
SGC_LITOLOGIA_URL = f"{SGC_BASE_MAPSERVER}/22"

SGC_METALOGENICO_BASE = "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Metalogenico_Colombia/Mapa_Metalogenico_Colombia_2020/MapServer"
SGC_DEPOSITOS_URL = f"{SGC_METALOGENICO_BASE}/0"
SGC_ANOMALIAS_GEOQ_URL = f"{SGC_METALOGENICO_BASE}/4"
SGC_GEOFISICA_LINEAMIENTOS_URL = f"{SGC_METALOGENICO_BASE}/8"

# Agencia Nacional de Minería (ANM - Anna Minería)
ANM_TITULOS_URL = "https://annamineria.anm.gov.co/sigm/rest/services/VisorPublico/CatastroMinero/MapServer/0"
ANM_SOLICITUDES_URL = "https://annamineria.anm.gov.co/sigm/rest/services/VisorPublico/CatastroMinero/MapServer/1"

# Catálogo STAC Público y Mosaicos Ópticos Reales
EARTH_SEARCH_STAC_URL = "https://earth-search.aws.element84.com/v1/search"
EOX_S2_WMS_URL = "https://tiles.maps.eox.at/wms"
ESRI_WORLD_IMAGERY_EXPORT_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

# Fecha crítica de falla del detector SWIR de ASTER (28 de abril de 2008)
ASTER_SWIR_FAILURE_DATE = "2008-04-28"

# Distritos Mineros y Casos de Estudio de Referencia (Colombia + Bolivia @eddycc66 + Estándar Mundial)
DISTRICT_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "segovia",
        "name": "Segovia - Remedios (Antioquia, COL)",
        "country": "Colombia",
        "lat": 7.0792,
        "lon": -74.6988,
        "roi_size_km": 4.0,
        "deposit_model": "orogenico_vetas",
        "sensor_mode": "multisensor",
        "description": "Vetas mesotermales de cuarzo-oro-pirita de alta ley en el Batolito de Segovia (El Silencio, Sandra K, Providencia).",
        "known_occurrences": [
            {"name": "Veta Sandra K", "lat": 7.0812, "lon": -74.6985, "mineral": "Au-Ag", "grade_gt": 13.8},
            {"name": "Mina El Silencio", "lat": 7.0745, "lon": -74.7042, "mineral": "Au", "grade_gt": 11.4},
            {"name": "Veta Providencia", "lat": 7.0884, "lon": -74.6910, "mineral": "Au-Ag", "grade_gt": 12.1},
        ],
    },
    {
        "id": "buritica",
        "name": "Buriticá - Yaraguá (Antioquia, COL)",
        "country": "Colombia",
        "lat": 6.7165,
        "lon": -75.9105,
        "roi_size_km": 4.0,
        "deposit_model": "epitermal_bs",
        "sensor_mode": "multisensor",
        "description": "Sistema epitermal de sulfuración intermedia / carbonato-metal base de clase mundial en el Cinturón del Cauca Medio.",
        "known_occurrences": [
            {"name": "Sistema Yaraguá", "lat": 6.7195, "lon": -75.9082, "mineral": "Au-Ag-Zn", "grade_gt": 8.9},
            {"name": "Sistema Veta Sur", "lat": 6.7128, "lon": -75.9140, "mineral": "Au-Ag", "grade_gt": 7.6},
        ],
    },
    {
        "id": "marmato",
        "name": "Marmato - Zona Alta / MDZ (Caldas, COL)",
        "country": "Colombia",
        "lat": 5.4745,
        "lon": -75.6010,
        "roi_size_km": 4.0,
        "deposit_model": "porfido",
        "sensor_mode": "multisensor",
        "description": "Transición epitermal de sulfuración intermedia a pórfido aurífero profundo en el Stock Dacítico de Marmato.",
        "known_occurrences": [
            {"name": "Marmato Zona Alta", "lat": 5.4762, "lon": -75.5994, "mineral": "Au-Ag", "grade_gt": 3.4},
            {"name": "Marmato Deep Zone", "lat": 5.4710, "lon": -75.6038, "mineral": "Au-Cu", "grade_gt": 2.95},
        ],
    },
    {
        "id": "cerro_rico",
        "name": "Cerro Rico de Potosí (BOL — Caso @eddycc66)",
        "country": "Bolivia",
        "lat": -19.6185,
        "lon": -65.7497,
        "roi_size_km": 4.5,
        "deposit_model": "polimetalico",
        "sensor_mode": "multisensor",
        "description": "Domo volcánico dacítico con zonación clásica: núcleo de sílice vuggy + alunita, halo cuarzo-sericita y gossan de jarosita/goethita.",
        "known_occurrences": [
            {"name": "Domo Central Cerro Rico", "lat": -19.6185, "lon": -65.7497, "mineral": "Ag-Sn", "grade_gt": 4.5},
            {"name": "Flanco Pailaviri", "lat": -19.6118, "lon": -65.7475, "mineral": "Ag-Sn-Zn", "grade_gt": 3.8},
            {"name": "Veta Mendieta Sur", "lat": -19.6238, "lon": -65.7524, "mineral": "Ag-Pb", "grade_gt": 3.2},
        ],
    },
    {
        "id": "pongo_quinuma",
        "name": "Pongo Quinuma (Altiplano, BOL — Caso @eddycc66)",
        "country": "Bolivia",
        "lat": -17.3620,
        "lon": -67.4520,
        "roi_size_km": 6.0,
        "deposit_model": "epitermal_as",
        "sensor_mode": "multisensor",
        "description": "Área piloto del curso multisensor GEONORT / Colegio de Topógrafos: fusión Sentinel-2 + ASTER + Landsat sobre ambiente semiárido.",
        "known_occurrences": [
            {"name": "Anomalía Central Quinuma", "lat": -17.3620, "lon": -67.4520, "mineral": "Au-Ag-Cu", "grade_gt": 2.2},
            {"name": "Estructura Norte Quinuma", "lat": -17.3545, "lon": -67.4465, "mineral": "Au-Ag", "grade_gt": 1.8},
        ],
    },
    {
        "id": "santurban",
        "name": "California - Vetas (Santander, COL)",
        "country": "Colombia",
        "lat": 7.3694,
        "lon": -72.9312,
        "roi_size_km": 4.0,
        "deposit_model": "epitermal_as",
        "sensor_mode": "multisensor",
        "description": "Alteración argílica avanzada (alunita-pirofilita-caolinita) y brechas hidrotermales de alta sulfuración en el Macizo de Santander.",
        "known_occurrences": [
            {"name": "Sector Angostura / California", "lat": 7.3694, "lon": -72.9312, "mineral": "Au-Ag-Cu", "grade_gt": 2.4},
        ],
    },
    {
        "id": "la_colosa",
        "name": "La Colosa - Cajamarca (Tolima, COL)",
        "country": "Colombia",
        "lat": 4.4628,
        "lon": -75.4981,
        "roi_size_km": 4.5,
        "deposit_model": "porfido",
        "sensor_mode": "multisensor",
        "description": "Pórfido aurífero mioceno en la Cordillera Central con alteración potásica-sódico-cálcica y halo propilítico.",
        "known_occurrences": [
            {"name": "Stock Central La Colosa", "lat": 4.4628, "lon": -75.4981, "mineral": "Au", "grade_gt": 0.86},
        ],
    },
    {
        "id": "bajo_cauca",
        "name": "El Bagre - Río Nechí (Bajo Cauca, COL)",
        "country": "Colombia",
        "lat": 7.6030,
        "lon": -74.8080,
        "roi_size_km": 5.0,
        "deposit_model": "aluvial_placer",
        "sensor_mode": "sentinel2",
        "description": " Terrazas cuaternarias (Q-al) y paleocanales auríferos aluviales de llanura de inundación en el Río Nechí.",
        "known_occurrences": [
            {"name": "Placeres Río Nechí", "lat": 7.6042, "lon": -74.8095, "mineral": "Au-Pt", "grade_gt": 0.45},
        ],
    },
    {
        "id": "choco_quito",
        "name": "Río Quito - Atrato (Chocó, COL)",
        "country": "Colombia",
        "lat": 5.5240,
        "lon": -76.7210,
        "roi_size_km": 5.0,
        "deposit_model": "aluvial_placer",
        "sensor_mode": "sentinel2",
        "description": "Depósitos aluviales de oro y platino en terrazas fluviales cuaternarias con alta cobertura nubosa tropical.",
        "known_occurrences": [
            {"name": "Terrazas Río Quito", "lat": 5.5240, "lon": -76.7210, "mineral": "Au-Pt", "grade_gt": 0.38},
        ],
    },
    {
        "id": "cuprite",
        "name": "Cuprite District (Nevada, USA — Estándar ASTER)",
        "country": "Estados Unidos",
        "lat": 37.5322,
        "lon": -117.1856,
        "roi_size_km": 5.5,
        "deposit_model": "epitermal_as",
        "sensor_mode": "multisensor",
        "description": "Laboratorio mundial de calibración espectral USGS/NASA para alunita, caolinita, sílice opalina y calcita sin vegetación.",
        "known_occurrences": [
            {"name": "Eastern Alunite Hill", "lat": 37.5322, "lon": -117.1856, "mineral": "Au-Sílice", "grade_gt": 1.1},
            {"name": "Silica Cap Center", "lat": 37.5365, "lon": -117.1912, "mineral": "Sílice-Au", "grade_gt": 0.9},
        ],
    },
    {
        "id": "bogota_control",
        "name": "Sabana de Bogotá (Control Negativo)",
        "country": "Colombia",
        "lat": 4.7500,
        "lon": -74.1200,
        "roi_size_km": 4.0,
        "deposit_model": "epitermal_as",
        "sensor_mode": "multisensor",
        "description": "Control negativo geocientífico en relleno lacustre cuaternario sin alteración hidrotermal aurífera.",
        "known_occurrences": [],
    },
]

# Modelos de Yacimiento y Pesos de Favorabilidad Espectral (GeoMineral AI v2)
DEPOSIT_MODELS: Dict[str, Dict[str, Any]] = {
    "epitermal_as": {
        "label": "Epitermal de Alta Sulfuración (Au-Ag-Cu)",
        "description": "Prioriza núcleo de sílice vuggy/residual, alunita, caolinita y sombrero de hierro (gossan).",
        "aster_weights": {
            "alunita": 0.26,
            "caolinita": 0.18,
            "silice": 0.20,
            "gossan": 0.18,
            "fe3": 0.10,
            "sericita": 0.08,
        },
        "fallback_weights": {
            "s2_arcilla_cai": 0.35,
            "s2_feox": 0.25,
            "s2_gossan": 0.20,
            "l8_arcilla": 0.20,
        },
        "integrated_weights": {
            "favorability": 0.45,
            "structural": 0.25,
            "geological_sgc": 0.20,
            "geophysical": 0.10,
        },
    },
    "epitermal_bs": {
        "label": "Epitermal de Baja / Intermedia Sulfuración (Au-Ag)",
        "description": "Prioriza vetas de cuarzo-adularia-sericita/illita, silicificación estructural y halo propilítico.",
        "aster_weights": {
            "sericita": 0.28,
            "cuarzo": 0.22,
            "ohi": 0.18,
            "fe3": 0.16,
            "clorita": 0.16,
        },
        "fallback_weights": {
            "s2_arcilla_cai": 0.38,
            "s2_pai": 0.22,
            "s2_feox": 0.22,
            "l8_arcilla": 0.18,
        },
        "integrated_weights": {
            "favorability": 0.40,
            "structural": 0.32,
            "geological_sgc": 0.18,
            "geophysical": 0.10,
        },
    },
    "porfido": {
        "label": "Pórfido Cu-Au-Mo",
        "description": "Zonación concéntrica fílica (cuarzo-sericita-pirita), argílica intermedia y halo propilítico externo (clorita-epidota).",
        "aster_weights": {
            "sericita": 0.26,
            "ohi": 0.18,
            "gossan": 0.20,
            "clorita": 0.20,
            "fe2": 0.16,
        },
        "fallback_weights": {
            "s2_arcilla_cai": 0.34,
            "s2_gossan": 0.24,
            "s2_ferroso": 0.22,
            "l8_hidrotermal": 0.20,
        },
        "integrated_weights": {
            "favorability": 0.42,
            "structural": 0.22,
            "geological_sgc": 0.20,
            "geophysical": 0.16,
        },
    },
    "orogenico_vetas": {
        "label": "Orogénico / Vetas Mesotermales (Au-Ag)",
        "description": "Fuerte control por cizallas y fallas regionales con vetas de cuarzo-sericita-carbonato y oxidación férrica.",
        "aster_weights": {
            "cuarzo": 0.25,
            "sericita": 0.25,
            "fe3": 0.20,
            "gossan": 0.15,
            "mgoh_co3": 0.15,
        },
        "fallback_weights": {
            "s2_feox": 0.30,
            "s2_arcilla_cai": 0.32,
            "s2_ferroso": 0.20,
            "l8_feox": 0.18,
        },
        "integrated_weights": {
            "favorability": 0.35,
            "structural": 0.35,
            "geological_sgc": 0.20,
            "geophysical": 0.10,
        },
    },
    "polimetalico": {
        "label": "Domo Polimetálico Xenotermal (Ag-Sn-Au — Tipo Cerro Rico)",
        "description": "Jerarquía mineralógica de Edwin Calle (@eddycc66): Alunita/Sílice apical, Cuarzo-Sericita intenso y Jarosita/Gossan.",
        "aster_weights": {
            "alunita": 0.24,
            "sericita": 0.24,
            "gossan": 0.22,
            "silice": 0.18,
            "fe3": 0.12,
        },
        "fallback_weights": {
            "s2_arcilla_cai": 0.36,
            "s2_gossan": 0.28,
            "s2_feox": 0.20,
            "l8_arcilla": 0.16,
        },
        "integrated_weights": {
            "favorability": 0.46,
            "structural": 0.24,
            "geological_sgc": 0.18,
            "geophysical": 0.12,
        },
    },
    "aluvial_placer": {
        "label": "Placeres Aluviales y Paleocanales Cuaternarios (Au-Pt)",
        "description": "Prioriza terrazas cuaternarias (Q-al), baja pendiente geomorfológica (<6°), sedimentos expuestos y óxidos detríticos.",
        "aster_weights": {
            "cuarzo": 0.28,
            "fe3": 0.24,
            "caolinita": 0.22,
            "fe2": 0.26,
        },
        "fallback_weights": {
            "s2_aluvial_turbidez": 0.36,
            "s2_feox": 0.28,
            "s2_ferroso": 0.20,
            "l8_feox": 0.16,
        },
        "integrated_weights": {
            "favorability": 0.38,
            "structural": 0.28,
            "geological_sgc": 0.26,
            "geophysical": 0.08,
        },
    },
}

# Catálogo de Combinaciones RGB Sentinel-2 / Multisensor (Tutoriales GEONORT)
RGB_COMPOSITES_CATALOG: Dict[str, Dict[str, str]] = {
    "rgb_natural_432": {
        "name": "Color Natural (B4 - B3 - B2)",
        "bands": "B4, B3, B2",
        "use": "Inspección fotointerpretativa base, geomorfología y accesos.",
    },
    "rgb_infrarrojo_843": {
        "name": "Falso Color Infrarrojo (B8 - B4 - B3)",
        "bands": "B8, B4, B3",
        "use": "Discriminación vigorosa de vegetación (rojo intenso) frente a afloramientos desnudos.",
    },
    "rgb_swir_12_8a_4": {
        "name": "Compuesto SWIR Exploración (B12 - B8A - B4)",
        "bands": "B12, B8A, B4",
        "use": "Contraste litológico, humedad estructural y alteraciones hidrotermales.",
    },
    "rgb_geologia_12_11_2": {
        "name": "Geología Estructural y Litología (B12 - B11 - B2)",
        "bands": "B12, B11, B2",
        "use": "Combinación clásica GEONORT para resaltar arcillas Al-OH, intrusivos y contactos litológicos.",
    },
    "rgb_agricultura_11_8_2": {
        "name": "Cobertura Vegetal / Suelo (B11 - B8 - B2)",
        "bands": "B11, B8, B2",
        "use": "Separación entre suelos agrícolas, pastizales y roca expuesta para enmascaramiento.",
    },
    "rgb_mineralogico": {
        "name": "Ternario Mineralógico (R: Arcilla/Alunita, G: Sericita/OH, B: FeOx)",
        "bands": "Al-OH, Sericita, Fe3+",
        "use": "Mapa hidrotermal directo: tonos blancos/amarillos indican coincidencia de arcillas + óxidos de hierro.",
    },
}

# Catálogo de Arquitecturas YOLO para Detección Mineral en Testigos/Afloramientos (GEONORT Sep 2026)
YOLO_MINERAL_MODELS: List[Dict[str, Any]] = [
    {
        "model": "ME-YOLOv8",
        "precision_map": "95.2%",
        "use_case": "Identificación de sulfuros auríferos (pirita, calcopirita, arsenopirita) en secciones pulidas y testigos de perforación.",
        "innovation": "Atención multiescala para granos minerales sub-milimétricos.",
    },
    {
        "model": "DW-YOLO",
        "precision_map": "93.8%",
        "use_case": "Clasificación rápida de mena vs. estéril en frentes de explotación subterránea con iluminación deficiente.",
        "innovation": "Convoluciones separables en profundidad para inferencia en dispositivos móviles de campo.",
    },
    {
        "model": "YOLOv8-SBI",
        "precision_map": "94.6%",
        "use_case": "Detección de venillas de cuarzo-sericita y texturas vuggy silica en cajas de logueo geotécnico.",
        "innovation": "Fusión de bordes estructurales con firma de reflectancia RGB cercana.",
    },
    {
        "model": "YOLO-LDB",
        "precision_map": "92.4%",
        "use_case": "Segmentación en tiempo real sobre ortomosaicos de dron (UAV) para mapeo de gossans y brechas.",
        "innovation": "Backbone ligero optimizado para vuelos fotogramétricos de alta resolución.",
    },
    {
        "model": "OreYOLO",
        "precision_map": "96.1%",
        "use_case": "Sorteo óptico automatizado (ore sorting) de fragmentos mineralizados con cuarzo aurífero.",
        "innovation": "Pérdida focal adaptativa ante superposición densa de clastos.",
    },
]
