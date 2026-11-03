"""
Favorabilidad Mineral Ponderada, Prospectividad Aurífera Integrada y Plan Exploratorio — GeoAuV2
- Suma ponderada normalizada Σ(wi*xi)/Σ(wi) sin doble normalización posterior.
- Modo estricto (strict_nan=True) vs tolerante (strict_nan=False).
- Redistribución automática de pesos en cascada cuando ASTER SWIR no está disponible.
- Detección dual: Sistemas de Veta/Pórfido/Epitermal en roca + Sistemas de Placeres Aluviales (terrazas Q-al y pozas).
- Rechazo automático de cuerpos marinos abiertos (0% potencial aurífero).
"""
from typing import Any, Dict, Tuple
import numpy as np

from backend.config import DEPOSIT_MODELS


def compute_mineral_favorability(
    norm_indices: Dict[str, np.ndarray],
    deposit_model: str = "orogenico_vetas",
    aster_swir_available: bool = True,
    custom_weights: Dict[str, float] | None = None,
    strict_nan: bool = False,
) -> Tuple[np.ndarray, Dict[str, float], str]:
    """
    Calcula el mapa de Favorabilidad Espectral Mineral [0, 1] evitando doble normalización
    para que las zonas estériles conserven puntajes genuinamente bajos.
    """
    model_cfg = DEPOSIT_MODELS.get(deposit_model, DEPOSIT_MODELS["orogenico_vetas"])

    if custom_weights:
        raw_weights = {k: float(v) for k, v in custom_weights.items() if v is not None and float(v) > 0}
        weight_source = "Pesos Personalizados por el Usuario"
    elif aster_swir_available and any(k in norm_indices for k in model_cfg["aster_weights"]):
        raw_weights = dict(model_cfg["aster_weights"])
        weight_source = f"Modelo {model_cfg['label']} (Fusión Completa ASTER SWIR/TIR + Sentinel-2)"
    else:
        raw_weights = dict(model_cfg["fallback_weights"])
        weight_source = f"Cascada Multisensor {model_cfg['label']} (Pesos Redistribuidos S2 + Landsat)"

    active_weights = {k: w for k, w in raw_weights.items() if k in norm_indices and w > 0}
    if not active_weights:
        for k in ("s2_arcilla_cai", "s2_feox", "fe3"):
            if k in norm_indices:
                active_weights[k] = 1.0

    total_w = sum(active_weights.values()) or 1.0
    norm_w = {k: round(w / total_w, 4) for k, w in active_weights.items()}

    sample_arr = next(iter(norm_indices.values()))
    h, w_px = sample_arr.shape

    if strict_nan:
        fav = np.zeros((h, w_px), dtype=np.float64)
        for k, weight in norm_w.items():
            fav = fav + weight * norm_indices[k]
    else:
        weighted_sum = np.zeros((h, w_px), dtype=np.float64)
        weight_mask_sum = np.zeros((h, w_px), dtype=np.float64)
        for k, weight in norm_w.items():
            arr = norm_indices[k]
            valid = np.isfinite(arr)
            weighted_sum[valid] += weight * arr[valid]
            weight_mask_sum[valid] += weight
        fav = np.full((h, w_px), np.nan, dtype=np.float64)
        ok = weight_mask_sum > 1e-6
        fav[ok] = weighted_sum[ok] / weight_mask_sum[ok]

    return np.clip(fav, 0.0, 1.0), norm_w, weight_source


def compute_integrated_prospectivity(
    favorability_01: np.ndarray,
    slope_deg: np.ndarray,
    lineament_01: np.ndarray,
    deposit_model: str,
    sgc_metrics: Dict[str, Any],
    integrated_weights: Dict[str, float] | None = None,
    is_negative_control: bool = False,
    is_open_ocean: bool = False,
    alluvial_power: np.ndarray | None = None,
    alluvial_active_pct: float = 0.0,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Combina Favorabilidad Espectral + Control Morfoestructural DEM + Evidencia Oficial SGC + Geofísica
    en el Mapa de Prospectividad Aurífera Integrada y puntaje MPI [0..100].
    """
    h, w = favorability_01.shape
    model_cfg = DEPOSIT_MODELS.get(deposit_model, DEPOSIT_MODELS["orogenico_vetas"])
    iw = integrated_weights or model_cfg["integrated_weights"]
    w_sum = sum(iw.values()) or 1.0
    w_fav = iw.get("favorability", 0.42) / w_sum
    w_str = iw.get("structural", 0.26) / w_sum
    w_sgc = iw.get("geological_sgc", 0.20) / w_sum
    w_geo = iw.get("geophysical", 0.12) / w_sum

    # Rechazo estricto de océano abierto / cuerpo marino profundo
    if is_open_ocean:
        marine_grid = np.full((h, w), 0.02, dtype=np.float64)
        return marine_grid, {
            "mpi": 2.0,
            "classification_code": "Q4",
            "classification_label": "Cuerpo de Agua Marino / Estéril (Sin Potencial Aurífero)",
            "classification_color": "#3b82f6",
            "confidence": "Alta",
            "favorability_mean": 0.02,
            "prospectivity_mean": 0.02,
            "prospectivity_p90": 0.03,
            "component_scores": {
                "spectral": 2.0,
                "structural": 1.0,
                "geological_sgc": 0.0,
                "geophysical": 2.0,
            },
            "integrated_weights_normalized": {
                "favorability": round(w_fav, 3),
                "structural": round(w_str, 3),
                "geological_sgc": round(w_sgc, 3),
                "geophysical": round(w_geo, 3),
            },
        }

    is_alluvial_context = (deposit_model == "aluvial_placer") or (
        alluvial_active_pct >= 0.45 and sgc_metrics.get("alluvial_geology_present", False)
    )

    if is_alluvial_context:
        slope_factor = np.clip(1.0 - (slope_deg / 18.0), 0.08, 1.0)
        structural_grid = 0.68 * slope_factor + 0.32 * lineament_01
    else:
        slope_factor = np.clip(slope_deg / 32.0, 0.10, 1.0)
        structural_grid = 0.72 * lineament_01 + 0.28 * slope_factor

    # Puntaje geocientífico regional SGC [0..1]
    sgc_score = 0.28
    if sgc_metrics.get("deposit_count", 0) > 0:
        sgc_score += min(0.38, 0.18 + 0.06 * sgc_metrics["deposit_count"])
    if sgc_metrics.get("fault_count", 0) > 0:
        sgc_score += min(0.22, 0.08 + 0.04 * sgc_metrics["fault_count"])
    if sgc_metrics.get("geochemical_anomaly_present"):
        sgc_score += 0.14
    if sgc_metrics.get("alluvial_geology_present") and is_alluvial_context:
        sgc_score += 0.22
    if is_negative_control:
        sgc_score = 0.12
    sgc_score = float(np.clip(sgc_score, 0.05, 0.98))

    mag_cnt = sgc_metrics.get("magnetic_lineament_count", 0)
    geophys_base = min(0.88, 0.34 + 0.10 * mag_cnt) if mag_cnt > 0 else (0.14 if is_negative_control else 0.46)
    geophys_grid = np.clip(0.65 * geophys_base + 0.35 * lineament_01, 0.0, 1.0)

    valid_fav_mask = np.isfinite(favorability_01)
    valid_fav = favorability_01[valid_fav_mask]
    fav_fallback = float(np.median(valid_fav)) * 0.72 if valid_fav.size > 0 else 0.20
    fav_filled = np.where(valid_fav_mask, favorability_01, fav_fallback)

    # Integración espacial de placeres aluviales (bancos de grava y pozas de lavado activas)
    if alluvial_power is not None and not is_negative_control:
        if deposit_model == "aluvial_placer":
            fav_filled = np.maximum(fav_filled, np.clip(0.88 * alluvial_power + 0.12 * fav_filled, 0.0, 1.0))
        elif alluvial_active_pct >= 0.40:
            fav_filled = np.maximum(fav_filled, np.clip(0.76 * alluvial_power + 0.16 * fav_filled, 0.0, 1.0))

    s_linear = (
        w_fav * fav_filled
        + w_str * structural_grid
        + w_sgc * (0.55 * sgc_score + 0.45 * fav_filled)
        + w_geo * geophys_grid
    )
    s_fuzzy_sum = 1.0 - (
        (1.0 - 0.82 * fav_filled)
        * (1.0 - 0.60 * structural_grid)
        * (1.0 - 0.52 * sgc_score)
    )
    prosp_grid = np.clip((s_fuzzy_sum ** 0.80) * (np.maximum(s_linear, 0.01) ** 0.20), 0.0, 1.0)
    if is_negative_control:
        prosp_grid = np.clip(s_linear * 0.42, 0.0, 0.46)

    eval_mask = valid_fav_mask | ((alluvial_power >= 0.35) if alluvial_power is not None else False)
    eval_pixels = prosp_grid[eval_mask] if int(np.sum(eval_mask)) >= 16 else prosp_grid.ravel()
    fav_eval = fav_filled[eval_mask] if int(np.sum(eval_mask)) >= 16 else fav_filled.ravel()

    fav_mean = float(np.mean(fav_eval)) if fav_eval.size > 0 else 0.20
    prosp_p95 = float(np.percentile(eval_pixels, 95))
    prosp_p90 = float(np.percentile(eval_pixels, 90))
    prosp_p85 = float(np.percentile(eval_pixels, 85))
    prosp_mean = float(np.mean(eval_pixels))

    mpi_raw = (0.48 * prosp_p95 + 0.32 * prosp_p85 + 0.20 * sgc_score) * 100.0
    if is_negative_control:
        mpi_raw = min(mpi_raw, 24.5)
    mpi = round(float(np.clip(mpi_raw, 4.0, 98.5)), 2)

    if mpi >= 75.0:
        cls_code, cls_label, cls_color, conf = "Q1", "Potencial Aurífero Muy Alto — Prioridad de Campo / Perforación", "#FFD700", "Alta"
    elif mpi >= 58.0:
        cls_code, cls_label, cls_color, conf = "Q2", "Potencial Aurífero Alto — Anomalía Consistente", "#f39c12", "Alta"
    elif mpi >= 40.0:
        cls_code, cls_label, cls_color, conf = "Q3", "Potencial Moderado — Requiere Muestreo Geoquímico", "#3498db", "Media"
    else:
        cls_code, cls_label, cls_color, conf = "Q4", "Potencial Bajo / Fondo Litológico Estéril", "#7f8c8d", "Alta"

    summary = {
        "mpi": mpi,
        "classification_code": cls_code,
        "classification_label": cls_label,
        "classification_color": cls_color,
        "confidence": conf,
        "favorability_mean": round(fav_mean, 4),
        "prospectivity_mean": round(prosp_mean, 4),
        "prospectivity_p90": round(prosp_p90, 4),
        "component_scores": {
            "spectral": round(float(np.percentile(fav_eval, 85)) * 100.0 if fav_eval.size else 20.0, 1),
            "structural": round(float(np.percentile(structural_grid, 85)) * 100.0, 1),
            "geological_sgc": round(sgc_score * 100.0, 1),
            "geophysical": round(float(np.percentile(geophys_grid, 80)) * 100.0, 1),
        },
        "integrated_weights_normalized": {
            "favorability": round(w_fav, 3),
            "structural": round(w_str, 3),
            "geological_sgc": round(w_sgc, 3),
            "geophysical": round(w_geo, 3),
        },
    }
    return prosp_grid, summary


def build_geoai_exploration_plan(
    deposit_model: str,
    mpi: float,
    targets_count: int,
    p1_count: int,
    aster_swir_available: bool,
    sgc_metrics: Dict[str, Any],
    is_open_ocean: bool = False,
) -> Dict[str, Any]:
    """Genera el Plan Operativo de Exploración Aurífera por Fases del Motor Analítico GeoAuV2."""
    model_cfg = DEPOSIT_MODELS.get(deposit_model, DEPOSIT_MODELS["orogenico_vetas"])
    nearest_dep = sgc_metrics.get("nearest_deposit_name") or "ocurrencias del cinturón metalogénico"

    if is_open_ocean:
        return {
            "model_label": model_cfg["label"],
            "executive_narrative": (
                "El cuadrante seleccionado corresponde a superficie marina abierta sin afloramientos continentales ni "
                "terrazas aluviales emergidas (MPI 2.0/100 — Q4 Estéril). Desplace el visor hacia cuencas continentales o distritos auríferos."
            ),
            "phases": [
                {
                    "phase": "Reubicación de Área de Estudio",
                    "actions": [
                        "Seleccionar un distrito aurífero continental o buscar un municipio/río en el buscador superior.",
                    ],
                }
            ],
        }

    if deposit_model == "aluvial_placer":
        phases = [
            {
                "phase": "Fase 1 — Cartografía Geomorfológica de Terrazas y Muestreo de Batea (1–2 semanas)",
                "actions": [
                    f"Verificar en campo los {max(p1_count, 1)} foco(s) P1 sobre barras puntuales de grava, meandros abandonados y terrazas cuaternarias (Q-al / Q-t).",
                    "Muestreo sistemático de sedimentos activos y concentrados de batea cuantificando granos de oro libre, magnetita detrítica, ilmenita y circón.",
                    "Fotogrametría con dron para delimitar espesores de terraza alta/baja y dinámicas de paleocauce.",
                ],
            },
            {
                "phase": "Fase 2 — Apiques Sistemáticos y Sondeos de Paleocanal (3–5 semanas)",
                "actions": [
                    "Excavación de apiques y sondeos tipo Banka / vibracore en malla 100×100 m hasta alcanzar el contacto con roca fresca (bedrock / peña).",
                    f"Cubicación granulométrica y tenores en mg Au/m³ correlacionados con {nearest_dep}.",
                    "Tomografía de Resistividad Eléctrica (ERT) y refracción sísmica somera para mapear trampas en depresiones del basamento.",
                ],
            },
            {
                "phase": "Fase 3 — Evaluación Hidrometalúrgica Libre de Mercurio y Planeación Minera (2–3 meses)",
                "actions": [
                    "Pruebas de recuperación gravimétrica centrífuga (Knelson / Falcon) y mesas concentradoras libres de mercurio.",
                    "Modelamiento 3D de bloques aluviales, balance hídrico ambiental y validación jurídica ante ANM.",
                ],
            },
        ]
    else:
        phases = [
            {
                "phase": "Fase 1 — Verificación Espectral y Cartografía Estructural de Vetas (1–2 semanas)",
                "actions": [
                    f"Inspeccionar en campo los {max(p1_count, 1)} blanco(s) P1 (pines 🎯 Au) con espectrómetro portátil SWIR confirmando picos de alunita/sericita (2.16–2.20 µm) y sombreros de hierro.",
                    "Levantamiento estructural escala 1:2.500 sobre cruces de fallas, zonas de cizalla y lineamientos de alta densidad.",
                    "Muestreo selectivo de afloramientos de cuarzo-sulfuros oxidados (gossan) y brechas hidrotermales.",
                ],
            },
            {
                "phase": "Fase 2 — Geoquímica Sistemática y Magnetometría Terrestre de Detalle (3–5 semanas)",
                "actions": [
                    "Muestreo por canales (rock-chip) y suelos en malla 100×50 m con ensayo al fuego (Au g/t) + ICP-MS multielemental (Ag, As, Sb, Bi, Te, Cu, Mo, Pb, Zn).",
                    "Malla de magnetometría terrestre cada 50 m para trazar corredores de Vacío Magnético Hidrotermal asociados a sulfidización de magnetita.",
                    f"Calibración geoquímica-estructural frente al depósito de referencia {nearest_dep}.",
                ],
            },
            {
                "phase": "Fase 3 — Polarización Inducida (IP/Resistividad) y Perforación Diamantina DDH (2–4 meses)",
                "actions": [
                    "Secciones de Polarización Inducida (cargabilidad de pirita/sulfuros auríferos) y Resistividad (núcleos silicificados) sobre blancos P1.",
                    "Programa inicial de sondajes diamantinos (DDH inclinados 55°–65°) orientados perpendicularmente al rumbo estructural medido.",
                ],
            },
        ]

    swir_note = (
        "Fusión SWIR/TIR orbital completa activa para discriminación mineralógica fina."
        if aster_swir_available
        else "Cascada multiespectral Sentinel-2 + Landsat activa; se sugiere apoyo de espectrometría portátil SWIR en roca fresca/alterada."
    )

    narrative = (
        f"El motor analítico GeoAuV2 evaluó el cuadrante bajo el modelo {model_cfg['label']}, registrando un Índice de Prospectividad "
        f"Aurífera (MPI) de {mpi}/100 con {targets_count} blanco(s) delimitado(s) ({p1_count} de Prioridad 1 — Alta). {swir_note}"
    )
    return {
        "model_label": model_cfg["label"],
        "executive_narrative": narrative,
        "phases": phases,
    }
