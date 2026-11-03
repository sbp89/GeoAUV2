"""
Motor de Inteligencia Artificial y Machine Learning Geocientífico — GeoAuV2
Integra tres paradigmas complementarios de clasificación mineralógica orbital:
1. No Supervisado: K-Means++ Estandarizado + Intérprete Mineralógico Automático de Centroides Z-Score.
2. Supervisado: Random Forest & RBF-SVM + Filtro Modal Espacial + Tamizado Sieve + Matriz de Confusión (OA y Kappa).
3. Semisupervisado: Similitud Coseno Multibanda + Coherencia Leave-One-Out (LOO) + Discriminación sobre Fondo.
"""
from typing import Any, Dict, List, Tuple
import numpy as np
from scipy.ndimage import generic_filter, label as nd_label


ALTERATION_PALETTE: Dict[int, str] = {
    1: "#e74c3c",  # Argílica Avanzada / Alunita-Sílice (Rojo Intenso)
    2: "#f39c12",  # Fílica / Cuarzo-Sericita (Ámbar Dorado)
    3: "#d35400",  # Gossan / Óxidos de Hierro Fe3+ (Naranja Óxido)
    4: "#2ecc71",  # Propilítica / Clorita-Epidota (Verde Esmeralda)
    5: "#9b59b6",  # Silicificación / Vetas Cuarzo (Violeta)
    6: "#5d6d7e",  # Fondo Litológico / Roca Fresca (Gris Pizarra)
    7: "#27ae60",  # Cobertura Vegetal Residual
    8: "#2980b9",  # Humedad / Drenajes
}


def apply_majority_filter_2d(labels: np.ndarray, window_size: int = 3) -> np.ndarray:
    """Filtro modal espacial para eliminar ruido aislado tipo 'sal y pimienta'."""
    win = 5 if window_size >= 5 else 3

    def _mode_func(values: np.ndarray) -> float:
        valid = values[values > 0].astype(np.int32)
        if valid.size == 0:
            return 0.0
        counts = np.bincount(valid)
        return float(np.argmax(counts))

    filtered = generic_filter(labels.astype(np.float64), _mode_func, size=win, mode="nearest")
    out = filtered.astype(np.int32)
    out[labels == 0] = 0
    return out


def apply_sieve_filter_2d(labels: np.ndarray, min_pixels: int = 6) -> np.ndarray:
    """
    Filtro Sieve (tamizado espacial): reemplaza parches aislados menores a `min_pixels`
    por la clase vecina dominante.
    """
    if min_pixels <= 1:
        return labels.copy()
    out = labels.copy()
    h, w = out.shape
    structure = np.ones((3, 3), dtype=int)

    for cid in np.unique(out):
        if cid <= 0:
            continue
        comp, n_comp = nd_label(out == cid, structure=structure)
        if n_comp == 0:
            continue
        sizes = np.bincount(comp.ravel())
        small_ids = np.where((sizes > 0) & (sizes < min_pixels))[0]
        for sid in small_ids:
            if sid == 0:
                continue
            ys, xs = np.where(comp == sid)
            y0, y1 = max(0, ys.min() - 1), min(h, ys.max() + 2)
            x0, x1 = max(0, xs.min() - 1), min(w, xs.max() + 2)
            patch = out[y0:y1, x0:x1]
            neighbors = patch[(patch > 0) & (patch != cid)]
            if neighbors.size > 0:
                replacement = int(np.argmax(np.bincount(neighbors)))
                out[comp == sid] = replacement
    return out


def _interpret_centroid_zscores(z_vec: np.ndarray, stack_keys: List[str]) -> Tuple[str, str, str]:
    """
    Asigna etiqueta geológica, hidrotermal o aluvial automática según firma z-score del centroide.
    """
    scores = {k: float(z_vec[i]) for i, k in enumerate(stack_keys)}
    peak_z = max(scores.values()) if scores else 0.0

    arg_adv = max(scores.get("alunita", -9.0), scores.get("aaa_rbd5", -9.0), scores.get("caolinita", -9.0))
    phyllic = max(scores.get("sericita", -9.0), scores.get("ohi", -9.0), scores.get("s2_arcilla_cai", -9.0), scores.get("s2_pai", -9.0))
    silica = max(scores.get("silice", -9.0), scores.get("cuarzo", -9.0))
    iron = max(scores.get("gossan", -9.0), scores.get("fe3", -9.0), scores.get("s2_feox", -9.0), scores.get("s2_gossan", -9.0))
    prop = max(scores.get("clorita", -9.0), scores.get("mgoh_co3", -9.0), scores.get("calcita", -9.0), scores.get("s2_ferroso", -9.0))
    alluv = scores.get("s2_aluvial_turbidez", -9.0)

    if peak_z < 0.32:
        return "Fondo Litológico / Roca Fresca", "#5d6d7e", "Baja"

    conf = "Alta" if peak_z >= 1.15 else ("Media" if peak_z >= 0.65 else "Moderada")
    candidates = [
        (arg_adv, "Argílica Avanzada (Alunita-Caolinita)", "#e74c3c"),
        (phyllic, "Alteración Fílica (Cuarzo-Sericita)", "#f39c12"),
        (silica, "Silicificación / Núcleo de Cuarzo", "#9b59b6"),
        (iron, "Óxidos de Fe³⁺ / Sombrero Gossan", "#d35400"),
        (alluv, "Terraza / Grava Aluvial Activa", "#eab308"),
        (prop, "Halo Propilítico (Clorita-Epidota-CO₃)", "#2ecc71"),
    ]
    candidates.sort(key=lambda t: t[0], reverse=True)
    best_val, best_label, best_color = candidates[0]
    if best_val < 0.30:
        return "Transición Litológica Débil", "#7f8c8d", "Baja"
    return best_label, best_color, conf


def kmeans_classify_stack(
    norm_indices: Dict[str, np.ndarray],
    stack_keys: List[str],
    n_clusters: int = 6,
    apply_majority: bool = True,
    majority_window: int = 3,
    apply_sieve: bool = True,
    sieve_min_pixels: int = 6,
    seed: int = 42,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Ejecuta K-Means++ con estandarización previa z-score sobre los píxeles válidos comunes del stack
    e interpreta geológicamente cada dominio mineralógico.
    """
    keys = [k for k in stack_keys if k in norm_indices]
    if not keys:
        keys = list(norm_indices.keys())[:5]

    arrays = [np.asarray(norm_indices[k], dtype=np.float64) for k in keys]
    h, w = arrays[0].shape
    stack_3d = np.stack(arrays, axis=-1)
    valid_mask = np.all(np.isfinite(stack_3d), axis=-1)
    X_raw = stack_3d[valid_mask]

    if X_raw.shape[0] < max(n_clusters * 3, 12):
        labels_2d = np.zeros((h, w), dtype=np.int32)
        return labels_2d, {"method": "K-Means++ Estandarizado GeoAuV2", "clusters": [], "palette": {}, "stack_keys": keys}

    means = np.mean(X_raw, axis=0)
    stds = np.where(np.std(X_raw, axis=0) > 1e-8, np.std(X_raw, axis=0), 1.0)
    X = (X_raw - means) / stds

    rng = np.random.default_rng(seed)
    k = min(n_clusters, X.shape[0])

    best_inertia = np.inf
    best_labels = None
    best_centroids = None

    for _ in range(3):
        centroids = np.empty((k, X.shape[1]), dtype=np.float64)
        first_idx = int(rng.integers(0, X.shape[0]))
        centroids[0] = X[first_idx]
        dist_sq = np.sum((X - centroids[0]) ** 2, axis=1)

        for c in range(1, k):
            total_d = float(np.sum(dist_sq))
            if total_d <= 1e-12:
                idx_next = int(rng.integers(0, X.shape[0]))
            else:
                probs = dist_sq / total_d
                idx_next = int(rng.choice(X.shape[0], p=probs))
            centroids[c] = X[idx_next]
            new_dist_sq = np.sum((X - centroids[c]) ** 2, axis=1)
            dist_sq = np.minimum(dist_sq, new_dist_sq)

        for _ in range(35):
            dists = np.sum((X[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
            lbl = np.argmin(dists, axis=1)
            new_centroids = centroids.copy()
            for c in range(k):
                members = X[lbl == c]
                if len(members) > 0:
                    new_centroids[c] = np.mean(members, axis=0)
            if np.max(np.abs(new_centroids - centroids)) < 1e-4:
                centroids = new_centroids
                break
            centroids = new_centroids

        final_dists = np.sum((X - centroids[lbl]) ** 2)
        if final_dists < best_inertia:
            best_inertia = float(final_dists)
            best_labels = lbl
            best_centroids = centroids

    labels_2d = np.zeros((h, w), dtype=np.int32)
    labels_2d[valid_mask] = best_labels + 1

    if apply_majority:
        labels_2d = apply_majority_filter_2d(labels_2d, window_size=majority_window)
    if apply_sieve:
        labels_2d = apply_sieve_filter_2d(labels_2d, min_pixels=sieve_min_pixels)

    total_valid = max(int(np.sum(labels_2d > 0)), 1)
    clusters_meta: List[Dict[str, Any]] = []
    palette: Dict[int, str] = {}
    used_colors: set[str] = set()
    fallback_colors = ["#e74c3c", "#f39c12", "#9b59b6", "#d35400", "#2ecc71", "#3498db", "#1abc9c", "#95a5a6"]

    for cid in range(1, k + 1):
        z_vec = best_centroids[cid - 1]
        geo_label, color_hex, conf = _interpret_centroid_zscores(z_vec, keys)
        if color_hex in used_colors:
            for fc in fallback_colors:
                if fc not in used_colors:
                    color_hex = fc
                    break
        used_colors.add(color_hex)
        palette[cid] = color_hex
        px_count = int(np.sum(labels_2d == cid))
        clusters_meta.append({
            "cluster_id": cid,
            "geological_zone": geo_label,
            "color": color_hex,
            "confidence": conf,
            "pixel_count": px_count,
            "area_pct": round(100.0 * px_count / total_valid, 2),
            "centroid_zscores": {keys[i]: round(float(z_vec[i]), 3) for i in range(len(keys))},
        })

    clusters_meta.sort(key=lambda item: max(item["centroid_zscores"].values()), reverse=True)
    return labels_2d, {
        "method": "K-Means++ Estandarizado GeoAuV2",
        "n_clusters": k,
        "inertia": round(best_inertia, 2),
        "stack_keys": keys,
        "clusters": clusters_meta,
        "palette": palette,
        "postprocessing": {
            "majority_filter": apply_majority,
            "majority_window": majority_window,
            "sieve_filter": apply_sieve,
            "sieve_min_pixels": sieve_min_pixels,
        },
    }


def _fit_predict_random_forest(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_all: np.ndarray,
    n_trees: int = 35,
    max_depth: int = 5,
    seed: int = 42,
) -> np.ndarray:
    """
    Bosque Aleatorio (Random Forest) vectorizado en NumPy:
    Entrena `n_trees` árboles de decisión con bootstrap y subespacio aleatorio de bandas (`sqrt(B)`).
    """
    rng = np.random.default_rng(seed)
    classes = np.unique(y_train)
    n_classes = int(np.max(classes)) + 1
    n_samples, n_features = X_train.shape
    mtry = max(1, int(np.sqrt(n_features)))

    def build_tree(X_sub: np.ndarray, y_sub: np.ndarray, depth: int) -> Dict[str, Any]:
        counts = np.bincount(y_sub, minlength=n_classes)
        pred_cls = int(np.argmax(counts))
        if depth >= max_depth or len(y_sub) < 6 or len(np.unique(y_sub)) == 1:
            return {"leaf": True, "cls": pred_cls}

        feat_candidates = rng.choice(n_features, size=min(mtry + 1, n_features), replace=False)
        best_gini = 1e9
        best_feat = -1
        best_thr = 0.0

        for f in feat_candidates:
            vals = X_sub[:, f]
            vmin, vmax = float(np.min(vals)), float(np.max(vals))
            if vmax - vmin <= 1e-7:
                continue
            thresholds = np.quantile(vals, [0.25, 0.5, 0.75])
            for thr in thresholds:
                left_y = y_sub[vals <= thr]
                right_y = y_sub[vals > thr]
                if len(left_y) < 2 or len(right_y) < 2:
                    continue
                p_l = np.bincount(left_y, minlength=n_classes) / len(left_y)
                p_r = np.bincount(right_y, minlength=n_classes) / len(right_y)
                gini = (len(left_y) * (1.0 - np.sum(p_l ** 2)) + len(right_y) * (1.0 - np.sum(p_r ** 2))) / len(y_sub)
                if gini < best_gini:
                    best_gini = float(gini)
                    best_feat = int(f)
                    best_thr = float(thr)

        if best_feat < 0:
            return {"leaf": True, "cls": pred_cls}

        mask_l = X_sub[:, best_feat] <= best_thr
        return {
            "leaf": False,
            "feat": best_feat,
            "thr": best_thr,
            "left": build_tree(X_sub[mask_l], y_sub[mask_l], depth + 1),
            "right": build_tree(X_sub[~mask_l], y_sub[~mask_l], depth + 1),
        }

    def eval_tree(node: Dict[str, Any], X_eval: np.ndarray, idx_arr: np.ndarray, out_arr: np.ndarray) -> None:
        if idx_arr.size == 0:
            return
        if node["leaf"]:
            out_arr[idx_arr] = node["cls"]
            return
        cond = X_eval[idx_arr, node["feat"]] <= node["thr"]
        eval_tree(node["left"], X_eval, idx_arr[cond], out_arr)
        eval_tree(node["right"], X_eval, idx_arr[~cond], out_arr)

    votes = np.zeros((X_all.shape[0], n_classes), dtype=np.int32)
    all_idx = np.arange(X_all.shape[0])

    for _ in range(n_trees):
        boot_idx = rng.integers(0, n_samples, size=n_samples)
        tree = build_tree(X_train[boot_idx], y_train[boot_idx], 0)
        preds = np.zeros(X_all.shape[0], dtype=np.int32)
        eval_tree(tree, X_all, all_idx, preds)
        votes[all_idx, preds] += 1

    return np.argmax(votes, axis=1).astype(np.int32)


def _fit_predict_rbf_svm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_all: np.ndarray,
    gamma: float = 0.45,
    reg_lambda: float = 0.08,
) -> np.ndarray:
    """
    Clasificador multiclase con Kernel Radial (RBF-SVM / LS-SVM One-vs-Rest) en NumPy/SciPy:
    K(x, x') = exp(-gamma * ||x - x'||²), resolviendo (K + lambda*I) alpha = Y_onehot.
    """
    classes = np.unique(y_train)
    sq_train = np.sum((X_train[:, None, :] - X_train[None, :, :]) ** 2, axis=2)
    K_train = np.exp(-gamma * sq_train)

    Y = np.full((X_train.shape[0], len(classes)), -1.0, dtype=np.float64)
    for idx_c, cid in enumerate(classes):
        Y[y_train == cid, idx_c] = 1.0

    A = K_train + reg_lambda * np.eye(X_train.shape[0])
    alphas = np.linalg.solve(A, Y)

    preds = np.empty(X_all.shape[0], dtype=np.int32)
    batch = 1024
    for start in range(0, X_all.shape[0], batch):
        end = min(start + batch, X_all.shape[0])
        sq_eval = np.sum((X_all[start:end, None, :] - X_train[None, :, :]) ** 2, axis=2)
        K_eval = np.exp(-gamma * sq_eval)
        scores = K_eval @ alphas
        preds[start:end] = classes[np.argmax(scores, axis=1)]
    return preds


def _generate_auto_training_rois(
    norm_indices: Dict[str, np.ndarray],
    cube: Dict[str, np.ndarray],
) -> Tuple[np.ndarray, Dict[int, Dict[str, str]]]:
    """
    Genera píxeles semilla de entrenamiento supervisado siguiendo jerarquía paragenética:
      Clase 1: Argílica Avanzada / Alunita-Sílice
      Clase 2: Alteración Fílica / Cuarzo-Sericita
      Clase 3: Sombrero de Hierro / Gossan (Fe3+)
      Clase 4: Halo Propilítico (Clorita-Epidota)
      Clase 5: Roca Fresca / Suelo o Grava Expuesta
      Clase 6: Cobertura Vegetal
    """
    ndvi = norm_indices.get("ndvi", np.zeros_like(cube["S2_B4"]))
    clay = norm_indices.get("alunita", norm_indices.get("s2_arcilla_cai", np.zeros_like(ndvi)))
    sericite = norm_indices.get("sericita", norm_indices.get("s2_pai", clay))
    gossan = norm_indices.get("gossan", norm_indices.get("s2_feox", np.zeros_like(ndvi)))
    prop = norm_indices.get("clorita", norm_indices.get("s2_ferroso", np.zeros_like(ndvi)))

    h, w = ndvi.shape
    roi_map = np.zeros((h, w), dtype=np.int32)

    c6 = np.isfinite(ndvi) & (ndvi >= np.nanpercentile(ndvi, 86))
    c5 = np.isfinite(clay) & (clay <= np.nanpercentile(clay, 22)) & (gossan <= np.nanpercentile(gossan, 28)) & (~c6)
    c4 = np.isfinite(prop) & (prop >= np.nanpercentile(prop, 86))
    c3 = np.isfinite(gossan) & (gossan >= np.nanpercentile(gossan, 87))
    c2 = np.isfinite(sericite) & (sericite >= np.nanpercentile(sericite, 88))
    c1 = np.isfinite(clay) & (clay >= np.nanpercentile(clay, 90))

    roi_map[c6] = 6
    roi_map[c5] = 5
    roi_map[c4] = 4
    roi_map[c3] = 3
    roi_map[c2] = 2
    roi_map[c1] = 1

    classes_info = {
        1: {"name": "Argílica Avanzada (Alunita / Sílice)", "color": "#e74c3c"},
        2: {"name": "Alteración Fílica (Cuarzo-Sericita)", "color": "#f39c12"},
        3: {"name": "Gossan / Óxidos Fe³⁺ (Jarosita-Goethita)", "color": "#d35400"},
        4: {"name": "Halo Propilítico (Clorita-Epidota)", "color": "#2ecc71"},
        5: {"name": "Roca Fresca / Suelo Expuesto", "color": "#5d6d7e"},
        6: {"name": "Cobertura Vegetal", "color": "#27ae60"},
    }
    return roi_map, classes_info


def supervised_classify_spectral(
    norm_indices: Dict[str, np.ndarray],
    cube: Dict[str, np.ndarray],
    bbox: List[float],
    stack_keys: List[str],
    classifier: str = "random_forest",  # random_forest | svm
    user_samples: List[Dict[str, Any]] | None = None,
    apply_majority: bool = True,
    majority_window: int = 3,
    apply_sieve: bool = True,
    sieve_min_pixels: int = 6,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Ejecuta clasificación mineralógica supervisada (Random Forest o RBF-SVM):
    - Incorpora semillas automáticas + ROIs interactivas marcadas en el mapa
    - Aplica Filtro Mayoritario + Tamizado Sieve
    - Calcula Matriz de Confusión, Precisión Global (OA) e Índice Kappa en validación 70/30.
    """
    keys = [k for k in stack_keys if k in norm_indices]
    if "ndvi" in norm_indices and "ndvi" not in keys:
        keys = keys + ["ndvi"]

    arrays = []
    for k in keys:
        arr = np.asarray(norm_indices[k], dtype=np.float64).copy()
        med = float(np.nanmedian(arr)) if np.any(np.isfinite(arr)) else 0.5
        arr[~np.isfinite(arr)] = med
        arrays.append(arr)

    h, w = arrays[0].shape
    stack_3d = np.stack(arrays, axis=-1)
    means = np.mean(stack_3d.reshape(-1, len(keys)), axis=0)
    stds = np.where(np.std(stack_3d.reshape(-1, len(keys)), axis=0) > 1e-8, np.std(stack_3d.reshape(-1, len(keys)), axis=0), 1.0)
    X_full = (stack_3d.reshape(-1, len(keys)) - means) / stds

    roi_map, classes_info = _generate_auto_training_rois(norm_indices, cube)

    min_lon, min_lat, max_lon, max_lat = bbox
    if user_samples:
        for smp in user_samples:
            cid = int(smp.get("class_id", 1))
            cname = str(smp.get("class_name", f"Clase {cid}"))
            ccol = str(smp.get("class_color", ALTERATION_PALETTE.get(cid, "#f39c12")))
            classes_info[cid] = {"name": cname, "color": ccol}
            col = int((float(smp["lon"]) - min_lon) / max(max_lon - min_lon, 1e-6) * (w - 1))
            row = int((max_lat - float(smp["lat"])) / max(max_lat - min_lat, 1e-6) * (h - 1))
            if 0 <= row < h and 0 <= col < w:
                roi_map[max(0, row - 1):min(h, row + 2), max(0, col - 1):min(w, col + 2)] = cid

    sample_coords = np.where(roi_map.ravel() > 0)[0]
    rng = np.random.default_rng(2026)
    if len(sample_coords) > 650:
        sample_coords = rng.choice(sample_coords, size=650, replace=False)

    X_samples = X_full[sample_coords]
    y_samples = roi_map.ravel()[sample_coords]

    perm = rng.permutation(len(sample_coords))
    split = max(int(0.70 * len(sample_coords)), len(np.unique(y_samples)) * 2)
    split = min(split, len(sample_coords) - 4)
    tr_idx, val_idx = perm[:split], perm[split:]

    X_train, y_train = X_samples[tr_idx], y_samples[tr_idx]
    X_val, y_val = X_samples[val_idx], y_samples[val_idx]

    if classifier == "svm":
        val_preds = _fit_predict_rbf_svm(X_train, y_train, X_val)
        all_preds = _fit_predict_rbf_svm(X_samples, y_samples, X_full)
        algo_label = "Support Vector Machine (RBF-SVM Multiclase GeoAuV2)"
    else:
        val_preds = _fit_predict_random_forest(X_train, y_train, X_val, n_trees=35)
        all_preds = _fit_predict_random_forest(X_samples, y_samples, X_full, n_trees=35)
        algo_label = "Random Forest Mineralógico (35 Árboles GeoAuV2)"

    labels_2d = all_preds.reshape(h, w)
    if apply_majority:
        labels_2d = apply_majority_filter_2d(labels_2d, window_size=majority_window)
    if apply_sieve:
        labels_2d = apply_sieve_filter_2d(labels_2d, min_pixels=sieve_min_pixels)

    active_cids = sorted(list(np.unique(np.concatenate([y_val, val_preds, labels_2d.ravel()]))))
    active_cids = [int(c) for c in active_cids if c > 0]
    cid_to_pos = {c: i for i, c in enumerate(active_cids)}
    cm = np.zeros((len(active_cids), len(active_cids)), dtype=int)
    for yt, yp in zip(y_val, val_preds):
        if int(yt) in cid_to_pos and int(yp) in cid_to_pos:
            cm[cid_to_pos[int(yt)], cid_to_pos[int(yp)]] += 1

    n_val = max(int(np.sum(cm)), 1)
    oa = float(np.trace(cm)) / n_val
    row_sums = np.sum(cm, axis=1)
    col_sums = np.sum(cm, axis=0)
    pe = float(np.sum(row_sums * col_sums)) / float(n_val * n_val)
    kappa = (oa - pe) / max(1.0 - pe, 1e-6)

    total_px = labels_2d.size
    palette = {cid: classes_info.get(cid, {"color": "#f39c12"})["color"] for cid in active_cids}
    class_summary = []
    for idx_c, cid in enumerate(active_cids):
        px_c = int(np.sum(labels_2d == cid))
        prod_acc = float(cm[idx_c, idx_c]) / max(int(row_sums[idx_c]), 1)
        user_acc = float(cm[idx_c, idx_c]) / max(int(col_sums[idx_c]), 1)
        meta = classes_info.get(cid, {"name": f"Clase {cid}", "color": "#f39c12"})
        class_summary.append({
            "cluster_id": cid,
            "geological_zone": meta["name"],
            "color": meta["color"],
            "confidence": "Alta" if user_acc >= 0.80 else "Media",
            "pixel_count": px_c,
            "area_pct": round(100.0 * px_c / total_px, 2),
            "producer_accuracy": round(prod_acc, 3),
            "user_accuracy": round(user_acc, 3),
        })

    return labels_2d, {
        "method": algo_label,
        "classifier_code": classifier,
        "stack_keys": keys,
        "clusters": class_summary,
        "palette": palette,
        "accuracy_metrics": {
            "overall_accuracy": round(oa, 4),
            "kappa": round(kappa, 4),
            "validation_samples": n_val,
            "training_samples": int(len(X_train)),
            "confusion_matrix": cm.tolist(),
            "class_labels": [classes_info.get(c, {"name": f"C{c}"})["name"] for c in active_cids],
        },
        "postprocessing": {
            "majority_filter": apply_majority,
            "majority_window": majority_window,
            "sieve_filter": apply_sieve,
            "sieve_min_pixels": sieve_min_pixels,
        },
    }


def cosine_similarity_spectral(
    norm_indices: Dict[str, np.ndarray],
    bbox: List[float],
    stack_keys: List[str],
    anchors: List[Dict[str, Any]] | None = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Exploración Semisupervisada por Similitud Coseno Multibanda y Coherencia Leave-One-Out (LOO)
    frente a minas u ocurrencias conocidas de referencia.
    """
    keys = [k for k in stack_keys if k in norm_indices]
    arrays = [np.asarray(norm_indices[k], dtype=np.float64) for k in keys]
    h, w = arrays[0].shape
    stack_3d = np.stack(arrays, axis=-1)
    valid_mask = np.all(np.isfinite(stack_3d), axis=-1)

    min_lon, min_lat, max_lon, max_lat = bbox
    anchor_vecs: List[np.ndarray] = []

    if anchors:
        for anc in anchors:
            col = int((float(anc["lon"]) - min_lon) / max(max_lon - min_lon, 1e-6) * (w - 1))
            row = int((max_lat - float(anc["lat"])) / max(max_lat - min_lat, 1e-6) * (h - 1))
            if 0 <= row < h and 0 <= col < w and valid_mask[row, col]:
                v = stack_3d[row, col]
                nrm = np.linalg.norm(v)
                if nrm > 1e-8:
                    anchor_vecs.append(v / nrm)

    if len(anchor_vecs) < 2 and np.any(valid_mask):
        flat_valid = stack_3d[valid_mask]
        mag = np.mean(flat_valid, axis=1)
        top_idx = np.argsort(mag)[-4:]
        for idx_p in top_idx:
            v = flat_valid[idx_p]
            nrm = np.linalg.norm(v)
            if nrm > 1e-8:
                anchor_vecs.append(v / nrm)

    if not anchor_vecs:
        return np.full((h, w), np.nan), {"loo_coherence": 0.0, "discrimination_delta": 0.0, "verdict": "SIN DATOS"}

    A = np.stack(anchor_vecs, axis=0)
    mean_dir = np.mean(A, axis=0)
    mean_dir = mean_dir / max(float(np.linalg.norm(mean_dir)), 1e-8)

    loo_scores = []
    if len(A) >= 2:
        for i in range(len(A)):
            others = np.delete(A, i, axis=0)
            ref = np.mean(others, axis=0)
            ref = ref / max(float(np.linalg.norm(ref)), 1e-8)
            loo_scores.append(float(np.dot(A[i], ref)))
    else:
        loo_scores = [1.0]
    loo_mean = float(np.mean(loo_scores))

    sim_map = np.full((h, w), np.nan, dtype=np.float64)
    flat_v = stack_3d[valid_mask]
    norms = np.linalg.norm(flat_v, axis=1, keepdims=True)
    norms = np.where(norms > 1e-8, norms, 1.0)
    cos_vals = (flat_v / norms) @ mean_dir
    sim_01 = np.clip((cos_vals - np.min(cos_vals)) / max(np.ptp(cos_vals), 1e-6), 0.0, 1.0)
    sim_map[valid_mask] = sim_01

    bg_mean = float(np.mean(cos_vals))
    disc = loo_mean - bg_mean
    if loo_mean >= 0.85 and disc >= 0.05:
        verdict = "EXCELENTE — Ocurrencias ancla espectralmente coherentes y alta discriminación sobre el fondo."
    elif loo_mean >= 0.72:
        verdict = "BUENO — Coherencia consistente entre ocurrencias auríferas de referencia."
    else:
        verdict = "MODERADO — Múltiples estilos de alteración en las anclas; revisar separación por dominio."

    return sim_map, {
        "anchors_used": len(A),
        "loo_coherence": round(loo_mean, 4),
        "background_similarity": round(bg_mean, 4),
        "discrimination_delta": round(disc, 4),
        "verdict": verdict,
    }
