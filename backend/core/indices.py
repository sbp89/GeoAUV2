"""
Motor de Índices Espectrales Multisensor, Máscaras Ambientales y Renderizado Cartográfico — GeoAuV2
- División segura sdiv(num, den) con umbral |den| <= 1e-6 -> NaN sin sesgos aditivos.
- 15 Índices ASTER (VNIR + SWIR + TIR), 9 Índices Sentinel-2 MSI (10m-20m) y 3 Índices Landsat 8/9 OLI.
- Renderizadores RGBA de ultra-contraste con transparencia selectiva de fondo estéril e isolíneas auríferas.
"""
import base64
import io
from typing import Any, Dict, Tuple
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion


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
    # --- ASTER (15 índices minerales) ---
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
        "name": "Compuesto Hidrotermal Landsat",
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

    if sensor_mode == "multisensor" and "L8_B2" in cube:
        idx["l8_feox"] = sdiv(cube["L8_B4"], cube["L8_B2"])
        idx["l8_arcilla"] = sdiv(cube["L8_B6"], cube["L8_B7"])
        idx["l8_hidrotermal"] = idx["l8_arcilla"] * idx["l8_feox"]

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
    mask_urban: bool = True,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Construye máscara booleana rigurosa de píxeles válidos para exploración mineral:
    True = roca/suelo/grava genuinamente observable;
    False = enmascarado por nubes/sombra SCL (NaN), vegetación densa, agua, sombra topográfica o infraestructura urbana.
    """
    ndvi = indices["ndvi"]
    ndwi = indices["ndwi"]
    ndbi = indices["ndbi"]
    b2 = cube["S2_B2"]
    albedo = (b2 + cube["S2_B3"] + cube["S2_B4"]) / 3.0

    cloud_nodata = ~np.isfinite(ndvi)
    veg_masked = (np.isfinite(ndvi) & (ndvi > ndvi_threshold)) if mask_vegetation else np.zeros_like(ndvi, dtype=bool)
    water_masked = (np.isfinite(ndwi) & (ndwi > ndwi_threshold)) if mask_water else np.zeros_like(ndwi, dtype=bool)
    shadow_masked = (np.isfinite(albedo) & (albedo < 0.025)) if mask_shadows else np.zeros_like(albedo, dtype=bool)

    cai_u = indices.get("s2_arcilla_cai")
    if cai_u is None:
        cai_u = sdiv(cube["S2_B11"], cube["S2_B12"])
    feox_u = indices.get("s2_feox")
    if feox_u is None:
        feox_u = sdiv(cube["S2_B4"], b2)

    if mask_urban:
        urban_masked = (
            np.isfinite(b2)
            & (b2 > 0.105)
            & np.isfinite(cai_u)
            & (cai_u < 1.38)
            & np.isfinite(feox_u)
            & (feox_u < 1.62)
            & np.isfinite(ndbi)
            & (ndbi > -0.02)
            & np.isfinite(ndvi)
            & (ndvi < 0.25)
        )
    else:
        urban_masked = np.zeros_like(ndvi, dtype=bool)

    valid_mask = ~(cloud_nodata | veg_masked | water_masked | shadow_masked | urban_masked)

    total = max(valid_mask.size, 1)
    veg_relaxed = False
    effective_ndvi_thr = round(float(ndvi_threshold), 3)
    if (
        np.sum(valid_mask) / total < 0.06
        and mask_vegetation
        and np.sum(~cloud_nodata) / total >= 0.12
    ):
        effective_ndvi_thr = round(min(0.72, float(ndvi_threshold) + 0.18), 3)
        relaxed_veg = np.isfinite(ndvi) & (ndvi > effective_ndvi_thr)
        valid_mask = ~(cloud_nodata | relaxed_veg | water_masked | shadow_masked | urban_masked)
        veg_masked = relaxed_veg
        veg_relaxed = True

    mask_stats: Dict[str, Any] = {
        "valid_rock_soil_pct": round(100.0 * float(np.sum(valid_mask)) / total, 2),
        "vegetation_masked_pct": round(100.0 * float(np.sum(veg_masked)) / total, 2),
        "cloud_nodata_pct": round(100.0 * float(np.sum(cloud_nodata)) / total, 2),
        "water_masked_pct": round(100.0 * float(np.sum(water_masked)) / total, 2),
        "urban_masked_pct": round(100.0 * float(np.sum(urban_masked)) / total, 2),
        "shadow_masked_pct": round(100.0 * float(np.sum(shadow_masked)) / total, 2),
        "veg_relaxed_warning": veg_relaxed,
        "effective_ndvi_threshold": effective_ndvi_thr,
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


COLORMAPS: Dict[str, np.ndarray] = {
    "inferno_gold": np.array([
        [20, 14, 40],
        [85, 25, 118],
        [180, 45, 115],
        [240, 105, 38],
        [255, 195, 28],
        [255, 238, 110],
        [255, 253, 215],
    ], dtype=np.float64),
    "thermal_rainbow": np.array([
        [6, 182, 212],
        [34, 197, 94],
        [234, 179, 8],
        [249, 115, 22],
        [244, 63, 94],
        [255, 235, 160],
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
        [220, 68, 52],
        [234, 179, 8],
        [132, 204, 22],
        [34, 168, 68],
        [16, 102, 42],
    ], dtype=np.float64),
}


def _rgba_to_b64_png(rgba: np.ndarray) -> str:
    img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _upscale_scalar_smooth(arr_01: np.ndarray, upscale_to: int = 320) -> Tuple[np.ndarray, np.ndarray]:
    """
    Remuestrea mediante Convolución Normalizada (resample(val*mask) / resample(mask))
    preservando de forma exacta los bordes NaN (bosque, nubes SCL, agua, infraestructura)
    sin filtrar medianas artificiales ni difuminar vetas estrechas de 10-20 m.
    """
    data = np.asarray(arr_01, dtype=np.float64)
    valid = np.isfinite(data)
    if not np.any(valid):
        return np.zeros((upscale_to, upscale_to), dtype=np.float64), np.zeros((upscale_to, upscale_to), dtype=bool)

    num_f = np.where(valid, np.clip(data, 0.0, 1.0), 0.0).astype(np.float32)
    den_f = valid.astype(np.float32)

    num_up = np.asarray(
        Image.fromarray(num_f, mode="F").resize((upscale_to, upscale_to), Image.Resampling.BILINEAR),
        dtype=np.float64,
    )
    den_up = np.asarray(
        Image.fromarray(den_f, mode="F").resize((upscale_to, upscale_to), Image.Resampling.BILINEAR),
        dtype=np.float64,
    )
    valid_up = den_up >= 0.42
    val_up = np.zeros((upscale_to, upscale_to), dtype=np.float64)
    val_up[valid_up] = np.clip(num_up[valid_up] / den_up[valid_up], 0.0, 1.0)
    return val_up, valid_up


def render_scalar_png_b64(
    arr_01: np.ndarray,
    cmap_name: str = "inferno_gold",
    alpha_valid: int = 215,
    upscale_to: int = 320,
    transparent_below: float = 0.22,
) -> str:
    """
    Convierte una matriz normalizada [0, 1] con soporte NaN a Data URI PNG RGBA de alta definición,
    dejando transparente el fondo estéril bajo `transparent_below` para no oscurecer la imagen satelital.
    """
    val_up, valid = _upscale_scalar_smooth(arr_01, upscale_to=upscale_to)
    rgba = np.zeros((upscale_to, upscale_to, 4), dtype=np.uint8)

    if cmap_name == "ndvi_green":
        transparent_below = -1.0

    active = valid & (val_up >= transparent_below)
    if np.any(active):
        stops = COLORMAPS.get(cmap_name, COLORMAPS["inferno_gold"])
        n_stops = len(stops)
        scaled = np.clip(val_up[active], 0.0, 1.0) * (n_stops - 1)
        idx0 = np.floor(scaled).astype(int)
        idx1 = np.minimum(idx0 + 1, n_stops - 1)
        frac = (scaled - idx0)[:, None]
        rgb = stops[idx0] * (1.0 - frac) + stops[idx1] * frac
        rgba[active, :3] = np.clip(rgb, 0, 255).astype(np.uint8)

        if transparent_below > 0.0:
            span = max(1.0 - transparent_below, 1e-4)
            rel = np.clip((val_up[active] - transparent_below) / span, 0.0, 1.0)
            dyn_alpha = np.clip(np.power(rel, 0.78) * alpha_valid + 22.0, 0.0, 245.0).astype(np.uint8)
        else:
            dyn_alpha = np.full(np.sum(active), alpha_valid, dtype=np.uint8)
        rgba[active, 3] = dyn_alpha

    return _rgba_to_b64_png(rgba)


def render_gold_hotspots_png_b64(
    prospectivity_01: np.ndarray,
    cutoff: float = 0.36,
    upscale_to: int = 320,
) -> str:
    """
    Renderizador especializado de Focos y Vetas Auríferas sobre Fondo Satelital Limpio:
    - Píxeles enmascarados (NaN) o < cutoff: 100% transparentes (deja ver nítido el relieve satelital).
    - Convolución normalizada sin gaussiana destructiva para preservar afloramientos angostos (10-20m).
    - Isolíneas luminosas calculadas estrictamente al interior de la máscara válida (sin anillos de borde).
    """
    val_up, valid = _upscale_scalar_smooth(prospectivity_01, upscale_to=upscale_to)
    rgba = np.zeros((upscale_to, upscale_to, 4), dtype=np.uint8)

    xp = [cutoff, 0.48, 0.62, 0.74, 0.85, 0.94, 1.0]
    r_st = [16, 34, 234, 249, 244, 255, 255]
    g_st = [185, 197, 179, 115, 48, 215, 252]
    b_st = [129, 94, 8, 22, 68, 0, 190]

    active = valid & (val_up >= cutoff)
    if np.any(active):
        v = val_up[active]
        rgba[active, 0] = np.interp(v, xp, r_st).astype(np.uint8)
        rgba[active, 1] = np.interp(v, xp, g_st).astype(np.uint8)
        rgba[active, 2] = np.interp(v, xp, b_st).astype(np.uint8)

        rel = np.clip((v - cutoff) / max(1.0 - cutoff, 1e-4), 0.0, 1.0)
        alpha = np.clip(np.power(rel, 0.72) * 228.0 + 24.0, 0.0, 248.0).astype(np.uint8)
        rgba[active, 3] = alpha

        # Isolíneas estrictamente al interior de roca observable para evitar falsos bordes de bosque
        interior = binary_erosion(valid, iterations=2)
        if np.any(interior):
            gy, gx = np.gradient(val_up)
            grad_mag = np.hypot(gx, gy)
            iso_66 = interior & (np.abs(val_up - 0.66) <= np.maximum(grad_mag * 0.85, 0.005))
            iso_80 = interior & (np.abs(val_up - 0.80) <= np.maximum(grad_mag * 0.95, 0.006))

            rgba[iso_66] = [253, 224, 71, 235]   # Contorno dorado brillante
            rgba[iso_80] = [255, 255, 240, 252]  # Contorno blanco-oro incandescente

    return _rgba_to_b64_png(rgba)


def render_gold_classic_glow_png_b64(
    prospectivity_01: np.ndarray,
    cutoff: float = 0.30,
    upscale_to: int = 320,
) -> str:
    """Escala Dorada Clásica (Glow Ámbar -> Oro Brillante) con fondo satelital transparente."""
    val_up, valid = _upscale_scalar_smooth(prospectivity_01, upscale_to=upscale_to)
    rgba = np.zeros((upscale_to, upscale_to, 4), dtype=np.uint8)
    active = valid & (val_up >= cutoff)
    if np.any(active):
        v = val_up[active]
        rel = np.clip((v - cutoff) / max(1.0 - cutoff, 1e-4), 0.0, 1.0)
        rgba[active, 0] = np.clip(180 + rel * 75, 0, 255).astype(np.uint8)
        rgba[active, 1] = np.clip(95 + rel * 155, 0, 255).astype(np.uint8)
        rgba[active, 2] = np.clip(np.where(rel > 0.65, (rel - 0.65) * 420, 12), 0, 255).astype(np.uint8)
        rgba[active, 3] = np.clip(np.power(rel, 0.82) * 235 + 18, 0, 246).astype(np.uint8)
    return _rgba_to_b64_png(rgba)


def render_alluvial_placer_png_b64(
    alluvial_power: np.ndarray,
    turbid_water: np.ndarray,
    upscale_to: int = 320,
) -> str:
    """
    Visualizador de Placeres Aluviales, Terrazas de Grava (Ámbar/Oro) y Pozas de Lavado con Sedimentos (Cian).
    """
    aluv_up, valid = _upscale_scalar_smooth(alluvial_power, upscale_to=upscale_to)
    turb_up, _ = _upscale_scalar_smooth(turbid_water, upscale_to=upscale_to)
    rgba = np.zeros((upscale_to, upscale_to, 4), dtype=np.uint8)

    gravel = valid & (aluv_up >= 0.25)
    if np.any(gravel):
        v = np.clip((aluv_up[gravel] - 0.25) / 0.75, 0.0, 1.0)
        rgba[gravel, 0] = np.clip(215 + v * 40, 0, 255).astype(np.uint8)
        rgba[gravel, 1] = np.clip(140 + v * 95, 0, 255).astype(np.uint8)
        rgba[gravel, 2] = np.clip(18 + v * 45, 0, 255).astype(np.uint8)
        rgba[gravel, 3] = np.clip(v * 215 + 35, 0, 240).astype(np.uint8)

    ponds = turb_up >= 0.45
    if np.any(ponds):
        rgba[ponds] = [14, 215, 255, 225]

    return _rgba_to_b64_png(rgba)


def _stretch_channel_p2_p98(ch: np.ndarray) -> np.ndarray:
    valid = np.isfinite(ch)
    if not np.any(valid):
        return np.zeros_like(ch, dtype=np.uint8)
    p2, p98 = np.percentile(ch[valid], [2, 98])
    span = max(float(p98 - p2), 1e-6)
    stretched = np.clip((ch - p2) / span, 0.0, 1.0)
    stretched = np.power(stretched, 0.88)
    out = np.zeros_like(ch, dtype=np.uint8)
    out[valid] = np.clip(stretched[valid] * 255.0, 0, 255).astype(np.uint8)
    return out


def render_rgb_composite_b64(
    r: np.ndarray,
    g: np.ndarray,
    b: np.ndarray,
    upscale_to: int = 320,
    alpha: int = 238,
) -> str:
    """Renderiza un compuesto RGB de 3 bandas con estiramiento robusto P2-P98."""
    h, w = r.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    valid = np.isfinite(r) & np.isfinite(g) & np.isfinite(b)
    rgba[:, :, 0] = _stretch_channel_p2_p98(r)
    rgba[:, :, 1] = _stretch_channel_p2_p98(g)
    rgba[:, :, 2] = _stretch_channel_p2_p98(b)
    rgba[valid, 3] = alpha

    img = Image.fromarray(rgba, mode="RGBA")
    if upscale_to and (h < upscale_to or w < upscale_to):
        img = img.resize((upscale_to, upscale_to), resample=Image.Resampling.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def render_categorical_png_b64(
    labels: np.ndarray,
    palette: Dict[int, str],
    upscale_to: int = 320,
    alpha: int = 205,
    transparent_background_classes: Tuple[int, ...] = (0, 6, 7, 8),
) -> str:
    """
    Renderiza un mapa temático de dominios minerales IA con bordes definidos,
    atenuando las clases de fondo/vegetación para resaltar nítidamente los dominios de alteración.
    """
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
            rgba[mask, 3] = 55 if cid in transparent_background_classes else alpha

    img = Image.fromarray(rgba, mode="RGBA")
    if upscale_to and (h < upscale_to or w < upscale_to):
        img = img.resize((upscale_to, upscale_to), resample=Image.Resampling.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
