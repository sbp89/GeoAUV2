"""
Configuración Maestra de GeoAuV2
Plataforma Inteligente de Prospección Aurífera Multisensor, IA Geocientífica y Geofísica 3D:
- Fusión orbital Sentinel-2 L2A (10m-20m) + ASTER L1T (VNIR/SWIR/TIR) + Landsat 8/9 OLI/TIRS
- 27 Índices Espectrales Mineralógicos + 6 Compuestos RGB + Detección Aluvial de Terrazas y Pozas
- Clasificación No Supervisada (K-Means++), Supervisada (Random Forest + RBF-SVM + Majority/Sieve) y Similitud Coseno LOO
- Magnetometría Terrestre 2D/3D y Detección de Vacíos Magnéticos Hidrotermales
- Delineación de Blancos Auríferos (P1/P2/P3), Cruce Catastral por Blanco y Validación Estadística UTM (Kappa, Ganancia Espacial)
- Integración Resiliente SGC (Colombia), ANM (Catastro Minero) y Persistencia Cloud en Supabase
"""
import os
from typing import Any, Dict, List

APP_NAME = "GeoAuV2"
APP_TITLE = "GeoAuV2 — Plataforma Inteligente de Prospección Aurífera"
APP_VERSION = "2.3.0"

SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8000"))

# Credenciales Cloud leídas exclusivamente desde variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
).strip()
CRON_SECRET = os.getenv("CRON_SECRET", "").strip()

# Servicios Oficiales Servicio Geológico Colombiano (SGC) con Respaldo Multicapa
SGC_FALLAS_URLS: List[str] = [
    "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Geologico_Colombia/Mapa_Geologico_Colombia_V2023/MapServer/704",
    "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Geologico_Colombia/Mapa_Geologico_Colombia_2023/MapServer/12",
]
SGC_LITOLOGIA_URLS: List[str] = [
    "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Geologico_Colombia/Mapa_Geologico_Colombia_V2023/MapServer/733",
    "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Geologico_Colombia/Mapa_Geologico_Colombia_2023/MapServer/22",
]
SGC_DEPOSITOS_URLS: List[str] = [
    "https://srvags.sgc.gov.co/arcgis/rest/services/Anomalias_Geoquimica/Depositos_Minerales/MapServer/0",
    "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Metalogenico_Colombia/Mapa_Metalogenico_Colombia_2020/MapServer/0",
]
SGC_ANOMALIAS_GEOQ_URLS: List[str] = [
    "https://srvags.sgc.gov.co/arcgis/rest/services/Anomalias_Geoquimica/Anomalias_Geoquimicas_y_Potencial_Geoquimico/MapServer/0",
    "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Metalogenico_Colombia/Mapa_Metalogenico_Colombia_2020/MapServer/4",
]
SGC_GEOFISICA_LINEAMIENTOS_URLS: List[str] = [
    "https://srvags.sgc.gov.co/arcgis/rest/services/Geofisica/Anomalias_Geofisicas_V2022/MapServer/6",
    "https://srvags.sgc.gov.co/arcgis/rest/services/Mapa_Metalogenico_Colombia/Mapa_Metalogenico_Colombia_2020/MapServer/8",
]

# Compatibilidad directa para importaciones unitarias
SGC_FALLAS_URL = SGC_FALLAS_URLS[0]
SGC_LITOLOGIA_URL = SGC_LITOLOGIA_URLS[0]
SGC_DEPOSITOS_URL = SGC_DEPOSITOS_URLS[0]
SGC_ANOMALIAS_GEOQ_URL = SGC_ANOMALIAS_GEOQ_URLS[0]
SGC_GEOFISICA_LINEAMIENTOS_URL = SGC_GEOFISICA_LINEAMIENTOS_URLS[0]

# Agencia Nacional de Minería (ANM - Servicios WebGIS y Catastro Minero) con Respaldo Dual
ANM_TITULOS_URLS: List[str] = [
    "https://geo.anm.gov.co/webgis/rest/services/ANM/ServiciosANM/MapServer/4",
    "https://annamineria.anm.gov.co/sigm/rest/services/VisorPublico/CatastroMinero/MapServer/0",
]
ANM_SOLICITUDES_URLS: List[str] = [
    "https://geo.anm.gov.co/webgis/rest/services/ANM/ServiciosANM/MapServer/2",
    "https://annamineria.anm.gov.co/sigm/rest/services/VisorPublico/CatastroMinero/MapServer/1",
]
ANM_RESERVA_URLS: List[str] = [
    "https://geo.anm.gov.co/webgis/rest/services/ANM/ServiciosANM/MapServer/11",
]

ANM_TITULOS_URL = ANM_TITULOS_URLS[0]
ANM_SOLICITUDES_URL = ANM_SOLICITUDES_URLS[0]

# Catálogos Satelitales STAC y Mosaicos Ópticos Libres de Nubes Actualizados
EARTH_SEARCH_STAC_URL = "https://earth-search.aws.element84.com/v1/search"
EOX_S2_WMS_URL = "https://tiles.maps.eox.at/wms"
EOX_CLOUDLESS_LAYERS: List[str] = ["s2cloudless-2024", "s2cloudless-2023", "s2cloudless-2021"]
GOOGLE_SAT_TILE_URL = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
ESRI_WORLD_IMAGERY_EXPORT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

# Fecha de corte operativo del detector SWIR de ASTER (28 de abril de 2008)
ASTER_SWIR_FAILURE_DATE = "2008-04-28"

# Distritos Auríferos y Zonas de Calibración Geocientífica
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
        "description": "Vetas mesotermales de cuarzo-oro-pirita de alta ley (>10 g/t Au) en el Batolito de Segovia, controladas por el sistema Otú-Nus.",
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
        "description": "Sistema epitermal de oro de alta ley en carbonato-metal base (Yaraguá y Veta Sur) en el Cinturón del Cauca Medio.",
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
        "description": "Transición epitermal de sulfuración intermedia a pórfido aurífero profundo en el complejo dacítico de Marmato.",
        "known_occurrences": [
            {"name": "Marmato Zona Alta", "lat": 5.4762, "lon": -75.5994, "mineral": "Au-Ag", "grade_gt": 3.4},
            {"name": "Marmato Zona Profunda", "lat": 5.4710, "lon": -75.6038, "mineral": "Au-Cu", "grade_gt": 2.95},
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
        "description": "Terrazas cuaternarias (Q-al), barras de grava aurífera y paleocanales aluviales en la llanura del Río Nechí.",
        "known_occurrences": [
            {"name": "Placeres Río Nechí", "lat": 7.6042, "lon": -74.8095, "mineral": "Au-Pt", "grade_gt": 0.45},
        ],
    },
    {
        "id": "san_lucas",
        "name": "Santa Rosa del Sur - San Lucas (Bolívar, COL)",
        "country": "Colombia",
        "lat": 7.9620,
        "lon": -74.0530,
        "roi_size_km": 4.5,
        "deposit_model": "orogenico_vetas",
        "sensor_mode": "multisensor",
        "description": "Vetas hidrotermales de cuarzo-oro-sulfuros en granitoides jurásicos de la Serranía de San Lucas.",
        "known_occurrences": [
            {"name": "Distrito Vetas San Lucas", "lat": 7.9640, "lon": -74.0510, "mineral": "Au-Ag", "grade_gt": 9.2},
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
        "description": "Alteración argílica avanzada (alunita-pirofilita-caolinita) y brechas hidrotermales de alta sulfuración en Santander.",
        "known_occurrences": [
            {"name": "Sector California - Angostura", "lat": 7.3694, "lon": -72.9312, "mineral": "Au-Ag-Cu", "grade_gt": 2.4},
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
        "description": "Pórfido aurífero mioceno en la Cordillera Central con alteración potásica, sódico-cálcica y halo propilítico.",
        "known_occurrences": [
            {"name": "Stock Central La Colosa", "lat": 4.4628, "lon": -75.4981, "mineral": "Au", "grade_gt": 0.86},
        ],
    },
    {
        "id": "choco_quito",
        "name": "Condoto - Río Quito (Chocó, COL)",
        "country": "Colombia",
        "lat": 5.0950,
        "lon": -76.6500,
        "roi_size_km": 5.0,
        "deposit_model": "aluvial_placer",
        "sensor_mode": "sentinel2",
        "description": "Placeres aluviales de oro y platino en terrazas fluviales cuaternarias asociadas a complejos ultramáficos.",
        "known_occurrences": [
            {"name": "Terrazas Auríferas Condoto", "lat": 5.0965, "lon": -76.6485, "mineral": "Au-Pt", "grade_gt": 0.42},
        ],
    },
    {
        "id": "cerro_rico",
        "name": "Domo Volcánico Potosí (Andes Centrales, BOL)",
        "country": "Bolivia",
        "lat": -19.6185,
        "lon": -65.7497,
        "roi_size_km": 4.5,
        "deposit_model": "polimetalico",
        "sensor_mode": "multisensor",
        "description": "Domo volcánico dacítico con zonación hidrotermal concéntrica: núcleo de sílice vuggy + alunita, halo cuarzo-sericita y gossan.",
        "known_occurrences": [
            {"name": "Domo Central Potosí", "lat": -19.6185, "lon": -65.7497, "mineral": "Ag-Sn-Au", "grade_gt": 4.5},
            {"name": "Flanco Norte Pailaviri", "lat": -19.6118, "lon": -65.7475, "mineral": "Ag-Sn-Zn", "grade_gt": 3.8},
            {"name": "Veta Sur Mendieta", "lat": -19.6238, "lon": -65.7524, "mineral": "Ag-Pb", "grade_gt": 3.2},
        ],
    },
    {
        "id": "pongo_quinuma",
        "name": "Faja Epitermal Altiplano Central (Oruro, BOL)",
        "country": "Bolivia",
        "lat": -17.3620,
        "lon": -67.4520,
        "roi_size_km": 6.0,
        "deposit_model": "epitermal_as",
        "sensor_mode": "multisensor",
        "description": "Complejo volcánico semiárido de alta exposición espectral con alteración argílica avanzada y halo propilítico.",
        "known_occurrences": [
            {"name": "Anomalía Central Quinuma", "lat": -17.3620, "lon": -67.4520, "mineral": "Au-Ag-Cu", "grade_gt": 2.2},
            {"name": "Estructura Norte Quinuma", "lat": -17.3545, "lon": -67.4465, "mineral": "Au-Ag", "grade_gt": 1.8},
        ],
    },
    {
        "id": "cuprite",
        "name": "Distrito Cuprite (Nevada, USA — Calibración USGS)",
        "country": "Estados Unidos",
        "lat": 37.5322,
        "lon": -117.1856,
        "roi_size_km": 5.5,
        "deposit_model": "epitermal_as",
        "sensor_mode": "multisensor",
        "description": "Zona estándar mundial de calibración espectral USGS para alunita, caolinita, sílice opalina y calcita en roca desnuda.",
        "known_occurrences": [
            {"name": "Eastern Alunite Hill", "lat": 37.5322, "lon": -117.1856, "mineral": "Au-Sílice", "grade_gt": 1.1},
            {"name": "Silica Cap Center", "lat": 37.5365, "lon": -117.1912, "mineral": "Sílice-Au", "grade_gt": 0.9},
        ],
    },
    {
        "id": "bogota_control",
        "name": "Sabana de Bogotá (Control Negativo Estéril)",
        "country": "Colombia",
        "lat": 4.7500,
        "lon": -74.1200,
        "roi_size_km": 4.0,
        "deposit_model": "epitermal_as",
        "sensor_mode": "multisensor",
        "description": "Cuenca sedimentaria lacustre cuaternaria sin mineralización aurífera hidrotermal ni aluvial conocida.",
        "known_occurrences": [],
    },
]

# Modelos Metalogénicos de Yacimiento y Pesos de Favorabilidad Espectral
DEPOSIT_MODELS: Dict[str, Dict[str, Any]] = {
    "orogenico_vetas": {
        "label": "Orogénico / Vetas Mesotermales de Oro (Au-Ag)",
        "description": "Fuerte control por zonas de cizalla y fallas regionales con vetas de cuarzo-sericita-pirita y oxidación férrica.",
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
    "epitermal_as": {
        "label": "Epitermal de Alta Sulfuración (Au-Ag-Cu)",
        "description": "Prioriza núcleos de sílice vuggy/residual, alunita, caolinita y sombrero de hierro (gossan).",
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
        "label": "Pórfido Aurífero-Cuprífero (Au-Cu-Mo)",
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
    "aluvial_placer": {
        "label": "Placeres Aluviales, Terrazas y Paleocanales (Au-Pt)",
        "description": "Detecta terrazas cuaternarias (Q-al), llanuras de baja pendiente (<6.5°), barras de grava aurífera y pozas de lavado con sedimentos.",
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
    "polimetalico": {
        "label": "Domo Hidrotermal Polimetálico (Au-Ag-Sn-Zn)",
        "description": "Zonación telescópica en domos subvolcánicos: sílice/alunita apical, halo cuarzo-sericita intenso y sombrero de hierro (jarosita/goethita).",
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
}

# Catálogo de Combinaciones RGB Multisensor
RGB_COMPOSITES_CATALOG: Dict[str, Dict[str, str]] = {
    "rgb_natural_432": {
        "name": "Color Natural (B4 - B3 - B2)",
        "bands": "B4, B3, B2",
        "use": "Inspección fotointerpretativa de alta resolución, drenajes, accesos y descapotes.",
    },
    "rgb_infrarrojo_843": {
        "name": "Falso Color Infrarrojo (B8 - B4 - B3)",
        "bands": "B8, B4, B3",
        "use": "Discriminación nítida de vegetación densa (rojo intenso) frente a afloramientos rocosos y gravas.",
    },
    "rgb_swir_12_8a_4": {
        "name": "Compuesto SWIR de Alteración (B12 - B8A - B4)",
        "bands": "B12, B8A, B4",
        "use": "Contraste litológico estructural y detección de corredores de alteración hidrotermal.",
    },
    "rgb_geologia_12_11_2": {
        "name": "Geología Estructural y Litología (B12 - B11 - B2)",
        "bands": "B12, B11, B2",
        "use": "Resalta arcillas hidrotermales Al-OH, stocks intrusivos y contactos litológicos.",
    },
    "rgb_agricultura_11_8_2": {
        "name": "Cobertura Terrestre y Suelo Desnudo (B11 - B8 - B2)",
        "bands": "B11, B8, B2",
        "use": "Separación entre suelos agrícolas, pastizales y roca mineralizada expuesta.",
    },
    "rgb_mineralogico": {
        "name": "Ternario Mineralógico (R: Al-OH, G: Sericita, B: FeOx)",
        "bands": "Al-OH, Sericita, Fe3+",
        "use": "Síntesis hidrotermal: tonos dorados/blancos brillantes señalan convergencia de arcillas + óxidos de hierro.",
    },
}

# Catálogo de Modelos de Visión Artificial para Testigos de Perforación y Afloramientos
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
        "use_case": "Clasificación rápida de mena vs. estéril en frentes subterráneos con iluminación variable.",
        "innovation": "Convoluciones separables en profundidad para inferencia móvil en campo.",
    },
    {
        "model": "YOLOv8-SBI",
        "precision_map": "94.6%",
        "use_case": "Detección de venillas de cuarzo-sericita y texturas de sílice vuggy en cajas de logueo.",
        "innovation": "Fusión de bordes estructurales con firma de reflectancia óptica cercana.",
    },
    {
        "model": "YOLO-LDB",
        "precision_map": "92.4%",
        "use_case": "Segmentación sobre ortomosaicos de dron (UAV) para mapeo de gossans y brechas hidrotermales.",
        "innovation": "Arquitectura ligera optimizada para vuelos fotogramétricos centimétricos.",
    },
    {
        "model": "OreYOLO",
        "precision_map": "96.1%",
        "use_case": "Selección óptica automatizada (ore sorting) de fragmentos con cuarzo aurífero.",
        "innovation": "Pérdida focal adaptativa ante superposición densa de clastos.",
    },
]
