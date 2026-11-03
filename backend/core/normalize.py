"""
Normalización Robusta por Percentiles y Estadística Descriptiva — GeoAUV2
Basado en MineralExplorationAI/core/normalize.py (M.Sc. Edwin Calle Condori)
"""
from typing import Dict, Any, Tuple
import numpy as np


def normalize_array(
    arr: np.ndarray,
    method: str = "p2_p98",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Normaliza una matriz 2D al rango [0, 1] preservando NaN en píxeles enmascarados o inválidos.
    Métodos soportados: 'p2_p98' (por defecto robusto), 'p5_p95', 'minmax'.
    """
    data = np.asarray(arr, dtype=np.float64)
    valid_mask = np.isfinite(data)
    total_px = data.size
    valid_count = int(np.sum(valid_mask))
    nodata_pct = round(100.0 * (1.0 - (valid_count / max(total_px, 1))), 2)

    if valid_count == 0:
        return np.full_like(data, np.nan), {
            "min": 0.0,
            "p2": 0.0,
            "median": 0.0,
            "p98": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "nodata_pct": 100.0,
            "valid_pixels": 0,
            "histogram": {"bins": [], "counts": []},
        }

    vals = data[valid_mask]
    vmin = float(np.min(vals))
    vmax = float(np.max(vals))
    p2, p5, med, p95, p98 = [float(x) for x in np.percentile(vals, [2, 5, 50, 95, 98])]
    vmean = float(np.mean(vals))
    vstd = float(np.std(vals))

    if method == "p5_p95":
        low, high = p5, p95
    elif method == "minmax":
        low, high = vmin, vmax
    else:
        low, high = p2, p98

    out = np.full_like(data, np.nan, dtype=np.float64)
    span = high - low
    if abs(span) <= 1e-9:
        fallback_span = vmax - vmin
        if abs(fallback_span) <= 1e-9:
            out[valid_mask] = 0.5
        else:
            out[valid_mask] = np.clip((vals - vmin) / fallback_span, 0.0, 1.0)
    else:
        out[valid_mask] = np.clip((vals - low) / span, 0.0, 1.0)

    norm_vals = out[valid_mask]
    counts, bin_edges = np.histogram(norm_vals, bins=24, range=(0.0, 1.0))
    centers = [round(0.5 * float(bin_edges[i] + bin_edges[i + 1]), 3) for i in range(len(counts))]

    stats = {
        "min": round(vmin, 4),
        "p2": round(p2, 4),
        "median": round(med, 4),
        "p98": round(p98, 4),
        "max": round(vmax, 4),
        "mean": round(vmean, 4),
        "std": round(vstd, 4),
        "nodata_pct": nodata_pct,
        "valid_pixels": valid_count,
        "method": method,
        "histogram": {
            "bins": centers,
            "counts": [int(c) for c in counts],
        },
    }
    return out, stats
