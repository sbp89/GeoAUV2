"""
Motor de Índices Espectrales Multisensor, Máscaras y Renderizado Científico — GeoAUV2
Implementa fielmente las ecuaciones corregidas de GeoMineral AI v2 (INDICES.md) y tutoriales GEONORT:
- División segura sdiv(num, den) con umbral |den| <= 1e-6 -> NaN (sin distorsión +0.001)
- 15 Índices ASTER v2 (VNIR + SWIR + TIR)
- 9 Índices Sentinel-2 MSI (10m-20m)
- 3 Índices Landsat 8/9 OLI Collection 2
- 6 Compuestos RGB multisensor
"""
import base64
import io
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image


EPS = 1e-6


def sdiv(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """División segura elemento a elemento: retorna NaN donde |den| <= 1e-6 o entradas no finitas."""
    n = np.asarray(num, dtype=np.float64)
    d = np.asarray(den, dtype=np.float64)
    out = np.full(np.broadcast(n, d).shape, np.nan, dtype=np.float64)
    valid = np.isfinite(n) & np.isfinite(d) & (np.abs(d) > EPS)
    np.divide(n, d, out=out, where=valid)
    return out


INDICES_CATALOG: Dict[str, Dict[str, str]] = {
    # --- ASTER v2 (15 índices corregidos) ---
    "alunita": {
        "name": "Índice de Alunita (ALI)",
        "sensor": "ASTER SWIR",
        "formula": "(B7 / B5) * (B7 / B8)",
        "group": "Argílica Avanzada",
        "mineral": "Alunita / Pirofilita",
    },
    "aaa_rbd5": {
        "name": "Alteración Argílica Avanzada (RBD5)",
        "sensor": "ASTER SWIR",
        "formula": "(B4 + B6) / (2 * B5)",
        "group": "Argílica Avanzada",
        "mineral": "Alunita-Caolinita-Dickita (2.16 µm)",
    },
    "caolinita": {
        "name": "Índice de Caolinita (KLI)",
        "sensor": "ASTER SWIR",
        "formula": "(B4 / B5) * (B8 / B6)",
        "group": "Argílica",
        "mineral": "Caolinita / Esmectita",
    },
    "sericita": {
        "name": "Índice de Sericita / Muscovita (RBD6)",
        "sensor": "ASTER SWIR",
        "formula": "(B5 + B7) / (2 * B6)",
        "group": "Fílica",
        "mineral": "Sericita / Illita / Muscovita (2.20 µm)",
    },
    "ohi": {
        "name": "Índice Hidroxilo Al-OH (OHI)",
        "sensor": "ASTER SWIR",
        "formula": "(B7 / B6) * (B4 / B6)",
        "group": "Fílica / Argílica",
        "mineral": "Minerales Hidroxilados Al-OH",
    },
    "mgoh_co3": {
        "name": "Índice Mg-OH / Carbonatos (RBD8)",
        "sensor": "ASTER SWIR",
        "formula": "(B7 + B9) / (2 * B8)",
        "group": "Propilítica / Carbonatos",
        "mineral": "Clorita / Epidota / Calcita (2.33 µm)",
    },
    "clorita": {
        "name": "Índice de Clorita / Epidota",
        "sensor": "ASTER SWIR",
        "formula": "(B6 + B9) / (B7 + B8)",
        "group": "Propilítica",
        "mineral": "Clorita-Epidota-Actinolita",
    },
    "calcita": {
        "name": "Índice de Calcita (CLI)",
        "sensor": "ASTER SWIR",
        "formula": "(B6 / B8) * (B9 / B8)",
        "group": "Carbonatación",
        "mineral": "Calcita / Dolomita",
    },
    "fe3": {
        "name": "Óxidos Férricos Fe³⁺",
        "sensor": "ASTER VNIR",
        "formula": "B2 / B1",
        "group": "Óxidos de Hierro",
        "mineral": "Hematita / Goethita",
    },
    "fe2": {
        "name": "Silicatos / Carbonatos Ferrosos Fe²⁺",
        "sensor": "ASTER VNIR+SWIR",
        "formula": "(B5 / B3) + (B1 / B2)",
        "group": "Óxidos / Ferrosos",
        "mineral": "Siderita / Pirita Parcial / Clorita Fe",
    },
    "gossan": {
        "name": "Sombrero de Hierro (Gossan)",
        "sensor": "ASTER VNIR+SWIR",
        "formula": "B4 / B2",
        "group": "Gossan / Lixiviación",
        "mineral": "Jarosita / Limonita / Goethita",
    },
    "cuarzo": {
        "name": "Índice de Cuarzo (QI)",
        "sensor": "ASTER TIR",
        "formula": "(B11 * B11) / (B10 * B12)",
        "group": "Silicificación",
        "mineral": "Cuarzo Hidrotermal / Vetas",
    },
    "silice": {
        "name": "Índice de Sílice Total",
        "sensor": "ASTER TIR",
        "formula": "B13 / B10",
        "group": "Silicificación",
        "mineral": "Sílice Vuggy / Calcedonia / Ópalo",
    },
    "carbonatos": {
        "name": "Índice Térmico de Carbonatos (CI)",
        "sensor": "ASTER TIR",
        "formula": "B13 / B14",
        "group": "Carbonatación",
        "mineral": "Caliza / Mármol / Skarn",
    },
    "mafico": {
        "name": "Índice Máfico-Ultramáfico (MI)",
        "sensor": "ASTER TIR",
        "formula": "(B12 * B14³) / B13⁴",
        "group": "Litológico",
        "mineral": "Rocas Máficas vs. Félsicas",
    },
    # --- Sentinel-2 MSI ---
    "s2_feox": {
        "name": "Óxidos de Hierro Sentinel-2 (IOI)",
        "sensor": "Sentinel-2 MSI",
        "formula": "B4 / B2",
        "group": "Óxidos de Hierro",
        "mineral": "Hematita / Goethita (10m)",
    },
    "s2_ferroso": {
        "name": "Minerales Ferrosos Sentinel-2",
        "sensor": "Sentinel-2 MSI",
        "formula": "(B12 / B8A) + (B3 / B4)",
        "group": "Óxidos / Ferrosos",
        "mineral": "Fe²⁺ / Sulfuros Oxidados",
    },
    "s2_arcilla_cai": {
        "name": "Arcillas Hidrotermales Al-OH (CAI)",
        "sensor": "Sentinel-2 MSI",
        "formula": "B11 / B12",
        "group": "Fílica / Argílica",
        "mineral": "Caolinita / Sericita / Alunita (20m)",
    },
    "s2_pai": {
        "name": "Alteración Fílica / Pirítica (PAI)",
        "sensor": "Sentinel-2 MSI",
        "formula": "B8A / B11",
        "group": "Fílica",
        "mineral": "Zona Cuarzo-Sericita-Pirita",
    },
    "s2_gossan": {
        "name": "Índice Gossan Compuesto Sentinel-2",
        "sensor": "Sentinel-2 MSI",
        "formula": "(B11 / B4) * (B4 / B2)",
        "group": "Gossan / Lixiviación",
        "mineral": "Sombrero de Hierro Oxidado",
    },
    "s2_aluvial_turbidez": {
        "name": "Índice Sedimentos y Placeres Aluviales",
        "sensor": "Sentinel-2 MSI",
        "formula": "(B4 + B11) / (B2 + B8)",
        "group": "Aluvial / Placer",
        "mineral": "Barras de Grava / Terrazas Activas Q-al",
    },
    "ndvi": {
        "name": "Índice de Vegetación (NDVI)",
        "sensor": "Sentinel-2 MSI",
        "formula": "(B8 - B4) / (B8 + B4)",
        "group": "Máscaras Ambientales",
        "mineral": "Vigor fotosintético vegetal",
    },
    "ndwi": {
        "name": "Índice de Agua Superficial (NDWI)",
        "sensor": "Sentinel-2 MSI",
        "formula": "(B3 - B8) / (B3 + B8)",
        "group": "Máscaras Ambientales",
        "mineral": "Cuerpos de agua y drenajes",
    },
    "ndbi": {
        "name": "Índice de Suelo Expuesto / Construido (NDBI)",
        "sensor": "Sentinel-2 MSI",
        "formula": "(B11 - B8) / (B11 + B8)",
        "group": "Máscaras Ambientales",
        "mineral": "Roca expuesta / infraestructura",
    },
    # --- Landsat 8/9 OLI ---
    "l8_feox": {
        "name": "Óxidos de Hierro Landsat 8/9",
        "sensor": "Landsat 8/9 OLI",
        "formula": "SR_B4 / SR_B2",
        "group": "Respaldo Regional 30m",
        "mineral": "Óxidos Férricos Regionales",
    },
    "l8_arcilla": {
        "name": "Arcillas / Hidroxilos Landsat 8/9",
        "sensor": "Landsat 8/9 OLI",
        "formula": "SR_B6 / SR_B7",
        "group": "Respaldo Regional 30m",
        "mineral": "Arcillas Hidrotermales 30m",
    },
    "l8_hidrotermal": {
        "name": "Compuesto Hidrotermal Abrams Landsat",
        "sensor": "Landsat 8/9 OLI",
        "formula": "(SR_B6 / SR_B7) * (SR_B4 / SR_B2)",
        "group": "Respaldo Regional 30m",
        "mineral": "Coincidencia Arcilla + FeOx",
    },
}


def compute_all_indices(
    cube: Dict[str, np.ndarray],
    sensor_mode: str = "multisensor",
    aster_swir_available: bool = True,
) -> Dict[str, np.ndarray]:
    """Calcula el conjunto completo de índices espectrales según los sensores disponibles."""
    idx: Dict[str, np.ndarray] = {}

    # Sentinel-2
    b2 = cube["S2_B2"]
    b3 = cube["S2_B3"]
    b4 = cube["S2_B4"]
    b8 = cube["S2_B8"]
    b8a = cube["S2_B8A"]
    b11 = cube["S2_B11"]
    b12 = cube["S2_B12"]

    idx["ndvi"] = sdiv(b8 - b4, b8 + b4)
    idx["ndwi"] = sdiv(b3 - b8, b3 + b8)
    idx["ndbi"] = sdiv(b11 - b8, b11 + b8)

    if sensor_mode in ("multisensor", "sentinel2"):
        idx["s2_feox"] = sdiv(b4, b2)
        idx["s2_ferroso"] = sdiv(b12, b8a) + sdiv(b3, b4)
        idx["s2_arcilla_cai"] = sdiv(b11, b12)
        idx["s2_pai"] = sdiv(b8a, b11)
        idx["s2_gossan"] = sdiv(b11, b4) * sdiv(b4, b2)
        idx["s2_aluvial_turbidez"] = sdiv(b4 + b11, b2 + b8)

    # Landsat 8/9
    if sensor_mode == "multisensor" and "L8_B2" in cube:
        idx["l8_feox"] = sdiv(cube["L8_B4"], cube["L8_B2"])
        idx["l8_arcilla"] = sdiv(cube["L8_B6"], cube["L8_B7"])
        idx["l8_hidrotermal"] = idx["l8_arcilla"] * idx["l8_feox"]

    # ASTER VNIR + SWIR + TIR
    if sensor_mode in ("multisensor", "aster") and "AST_B1" in cube:
        ab1, ab2, ab3 = cube["AST_B1"], cube["AST_B2"], cube["AST_B3"]
        idx["fe3"] = sdiv(ab2, ab1)

        if aster_swir_available and "AST_B4" in cube:
            ab4, ab5, ab6 = cube["AST_B4"], cube["AST_B5"], cube["AST_B6"]
            ab7, ab8, ab9 = cube["AST_B7"], cube["AST_B8"], cube["AST_B9"]
            idx["alunita"] = sdiv(ab7, ab5) * sdiv(ab7, ab8)
            idx["aaa_rbd5"] = sdiv(ab4 + ab6, 2.0 * ab5)
            idx["caolinita"] = sdiv(ab4, ab5) * sdiv(ab8, ab6)
            idx["sericita"] = sdiv(ab5 + ab7, 2.0 * ab6)
            idx["ohi"] = sdiv(ab7, ab6) * sdiv(ab4, ab6)
            idx["mgoh_co3"] = sdiv(ab7 + ab9, 2.0 * ab8)
            idx["clorita"] = sdiv(ab6 + ab9, ab7 + ab8)
            idx["calcita"] = sdiv(ab6, ab8) * sdiv(ab9, ab8)
            idx["fe2"] = sdiv(ab5, ab3) + sdiv(ab1, ab2)
            idx["gossan"] = sdiv(ab4, ab2)

        if "AST_B10" in cube:
            ab10, ab11, ab12 = cube["AST_B10"], cube["AST_B11"], cube["AST_B12"]
            ab13, ab14 = cube["AST_B13"], cube["AST_B14"]
            idx["cuarzo"] = sdiv(ab11 * ab11, ab10 * ab12)
            idx["silice"] = sdiv(ab13, ab10)
            idx["carbonatos"] = sdiv(ab13, ab14)
            idx["mafico"] = sdiv(ab12 * (ab14 ** 3), ab13 ** 4)

    return idx


def build_environmental_mask(
    cube: Dict[str, np.ndarray],
    indices: Dict[str, np.ndarray],
    mask_vegetation: bool = True,
    ndvi_threshold: float = 0.45,
    mask_water: bool = True,
    ndwi_threshold: float = 0.15,
    mask_shadows: bool = True,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Construye máscara booleana de píxeles válidos para exploración mineral:
    True = roca/suelo analizable; False = enmascarado por vegetación densa, agua o sombra.
    """
    ndvi = indices["ndvi"]
    ndwi = indices["ndwi"]
    albedo = (cube["S2_B2"] + cube["S2_B3"] + cube["S2_B4"]) / 3.0

    veg_masked = (ndvi > ndvi_threshold) if mask_vegetation else np.zeros_like(ndvi, dtype=bool)
    water_masked = (ndwi > ndwi_threshold) if mask_water else np.zeros_like(ndwi, dtype=bool)
    shadow_masked = (albedo < 0.025) if mask_shadows else np.zeros_like(albedo, dtype=bool)

    valid_mask = ~(veg_masked | water_masked | shadow_masked) & np.isfinite(ndvi)

    # Salvaguarda de cascada: si la máscara elimina >92% del ROI tropical, relajar umbral NDVI suavemente
    total = max(valid_mask.size, 1)
    if np.sum(valid_mask) / total < 0.08 and mask_vegetation:
        relaxed_veg = ndvi > min(0.78, ndvi_threshold + 0.22)
        valid_mask = ~(relaxed_veg | water_masked | shadow_masked) & np.isfinite(ndvi)
        veg_masked = relaxed_veg

    mask_stats = {
        "valid_rock_soil_pct": round(100.0 * float(np.sum(valid_mask)) / total, 2),
        "vegetation_masked_pct": round(100.0 * float(np.sum(veg_masked)) / total, 2),
        "water_masked_pct": round(100.0 * float(np.sum(water_masked)) / total, 2),
        "shadow_masked_pct": round(100.0 * float(np.sum(shadow_masked)) / total, 2),
    }
    return valid_mask, mask_stats


def apply_mask_to_indices(
    indices: Dict[str, np.ndarray],
    valid_mask: np.ndarray,
    exempt_keys: Tuple[str, ...] = ("ndvi", "ndwi", "ndbi"),
) -> Dict[str, np.ndarray]:
    """Aplica la máscara ambiental asignando NaN a píxeles no válidos en índices mineralógicos."""
    masked: Dict[str, np.ndarray] = {}
    for k, arr in indices.items():
        if k in exempt_keys:
            masked[k] = arr.copy()
        else:
            cp = arr.copy()
            cp[~valid_mask] = np.nan
            masked[k] = cp
    return masked


# Paletas científicas vectorizadas [0..1] -> RGB
COLORMAPS: Dict[str, np.ndarray] = {
    "inferno_gold": np.array([
        [18, 14, 36],
        [68, 22, 84],
        [142, 36, 92],
        [208, 72, 48],
        [243, 156, 18],
        [255, 225, 86],
        [255, 252, 204],
    ], dtype=np.float64),
    "turbo_alteration": np.array([
        [24, 52, 128],
        [32, 132, 188],
        [58, 196, 142],
        [172, 222, 68],
        [246, 168, 36],
        [228, 68, 34],
        [156, 14, 36],
    ], dtype=np.float64),
    "viridis": np.array([
        [68, 1, 84],
        [59, 82, 139],
        [33, 145, 140],
        [94, 201, 98],
        [253, 231, 37],
    ], dtype=np.float64),
    "ndvi_green": np.array([
        [139, 90, 43],
        [210, 180, 110],
        [168, 214, 92],
        [58, 168, 62],
        [14, 98, 34],
    ], dtype=np.float64),
}


def render_scalar_png_b64(
    arr_01: np.ndarray,
    cmap_name: str = "inferno_gold",
    alpha_valid: int = 210,
    upscale_to: int = 256,
) -> str:
    """Convierte una matriz normalizada [0, 1] con soporte NaN a Data URI PNG RGBA."""
    data = np.asarray(arr_01, dtype=np.float64)
    h, w = data.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    valid = np.isfinite(data)
    if np.any(valid):
        stops = COLORMAPS.get(cmap_name, COLORMAPS["inferno_gold"])
        n_stops = len(stops)
        scaled = np.clip(data[valid], 0.0, 1.0) * (n_stops - 1)
        idx0 = np.floor(scaled).astype(int)
        idx1 = np.minimum(idx0 + 1, n_stops - 1)
        frac = (scaled - idx0)[:, None]
        rgb = stops[idx0] * (1.0 - frac) + stops[idx1] * frac
        rgba[valid, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        # Mayor opacidad para anomalías intensas
        dyn_alpha = np.clip(115 + data[valid] * (alpha_valid - 95), 95, 238).astype(np.uint8)
        rgba[valid, 3] = dyn_alpha

    img = Image.fromarray(rgba, mode="RGBA")
    if upscale_to and (h < upscale_to or w < upscale_to):
        img = img.resize((upscale_to, upscale_to), resample=Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _stretch_channel_p2_p98(ch: np.ndarray) -> np.ndarray:
    valid = np.isfinite(ch)
    if not np.any(valid):
        return np.zeros_like(ch, dtype=np.uint8)
    p2, p98 = np.percentile(ch[valid], [2, 98])
    span = max(float(p98 - p2), 1e-6)
    stretched = np.clip((ch - p2) / span, 0.0, 1.0)
    # Corrección gamma suave para visualización satelital
    stretched = np.power(stretched, 0.88)
    out = np.zeros_like(ch, dtype=np.uint8)
    out[valid] = np.clip(stretched[valid] * 255.0, 0, 255).astype(np.uint8)
    return out


def render_rgb_composite_b64(
    r: np.ndarray,
    g: np.ndarray,
    b: np.ndarray,
    upscale_to: int = 256,
    alpha: int = 235,
) -> str:
    """Renderiza un compuesto RGB de 3 bandas con estiramiento robusto P2-P98 (siempre visible)."""
    h, w = r.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    valid = np.isfinite(r) & np.isfinite(g) & np.isfinite(b)
    rgba[:, :, 0] = _stretch_channel_p2_p98(r)
    rgba[:, :, 1] = _stretch_channel_p2_p98(g)
    rgba[:, :, 2] = _stretch_channel_p2_p98(b)
    rgba[valid, 3] = alpha

    img = Image.fromarray(rgba, mode="RGBA")
    if upscale_to and (h < upscale_to or w < upscale_to):
        img = img.resize((upscale_to, upscale_to), resample=Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def render_categorical_png_b64(
    labels: np.ndarray,
    palette: Dict[int, str],
    upscale_to: int = 256,
    alpha: int = 205,
) -> str:
    """Renderiza un mapa temático de clases discretas (K-Means / Random Forest / SVM) con bordes nítidos."""
    h, w = labels.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    for cid, hex_col in palette.items():
        hx = hex_col.lstrip("#")
        if len(hx) == 6:
            rgb = (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
        else:
            rgb = (243, 156, 18)
        mask = labels == cid
        if np.any(mask):
            rgba[mask, 0] = rgb[0]
            rgba[mask, 1] = rgb[1]
            rgba[mask, 2] = rgb[2]
            rgba[mask, 3] = alpha

    img = Image.fromarray(rgba, mode="RGBA")
    if upscale_to and (h < upscale_to or w < upscale_to):
        img = img.resize((upscale_to, upscale_to), resample=Image.Resampling.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
