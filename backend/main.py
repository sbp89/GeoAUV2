"""
Servidor Principal FastAPI — GeoAuV2
Plataforma Inteligente de Prospección Aurífera Multisensor, IA Geocientífica, Geofísica 3D y Catastro Minero.
"""
from concurrent.futures import ThreadPoolExecutor
import datetime
import os
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import numpy as np

from backend.config import (
    APP_NAME,
    APP_TITLE,
    APP_VERSION,
    CRON_SECRET,
    DEPOSIT_MODELS,
    DISTRICT_PRESETS,
    RGB_COMPOSITES_CATALOG,
    YOLO_MINERAL_MODELS,
)
from backend.core.gee_exporter import generate_gee_javascript
from backend.core.indices import (
    INDICES_CATALOG,
    apply_mask_to_indices,
    build_environmental_mask,
    compute_all_indices,
    render_alluvial_placer_png_b64,
    render_categorical_png_b64,
    render_gold_classic_glow_png_b64,
    render_gold_hotspots_png_b64,
    render_rgb_composite_b64,
    render_scalar_png_b64,
)
from backend.core.ml_engine import (
    cosine_similarity_spectral,
    kmeans_classify_stack,
    supervised_classify_spectral,
)
from backend.core.multisensor_scene import SPECTRAL_WAVELENGTHS_UM, build_multisensor_cube
from backend.core.normalize import normalize_array
from backend.core.prospectivity import (
    build_geoai_exploration_plan,
    compute_integrated_prospectivity,
    compute_mineral_favorability,
)
from backend.core.report_generator import build_standalone_html_report
from backend.core.structural import (
    analyze_magnetometry_survey,
    compute_slope_and_lineaments,
    fetch_or_synthesize_dem,
    generate_demo_magnetometry_points,
)
from backend.core.targets_validation import (
    extract_prioritized_targets,
    validate_targets_statistically,
)
from backend.models import (
    AnalysisRequest,
    GEEScriptRequest,
    MagnetometryRequest,
    ProjectSaveRequest,
)
from backend.services.anm_service import ANMService
from backend.services.sgc_service import SGCService
from backend.services.supabase_service import SupabaseService
from backend.utils.geo_utils import bbox_to_geojson_polygon, point_to_bbox


app = FastAPI(
    title=APP_TITLE,
    description=(
        "Plataforma web de prospección aurífera multisensor libre de nubes (Sentinel-2 + ASTER + Landsat 8/9), "
        "clasificación supervisada/no supervisada (K-Means++, Random Forest, RBF-SVM), detección aluvial y de vetas, "
        "magnetometría 3D, cruce catastral ANM/SGC y validación estadística con persistencia en Supabase."
    ),
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
ANALYSIS_GRID_SIZE = 88


@app.get("/api/health")
async def api_health() -> Dict[str, Any]:
    sb_status = SupabaseService.health_check()
    return {
        "status": "online",
        "system": APP_NAME,
        "title": APP_TITLE,
        "version": APP_VERSION,
        "supabase": sb_status,
        "presets_count": len(DISTRICT_PRESETS),
        "indices_count": len(INDICES_CATALOG),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/api/catalog")
async def api_catalog() -> Dict[str, Any]:
    return {
        "presets": DISTRICT_PRESETS,
        "deposit_models": DEPOSIT_MODELS,
        "indices_catalog": INDICES_CATALOG,
        "rgb_composites": RGB_COMPOSITES_CATALOG,
        "yolo_models": YOLO_MINERAL_MODELS,
        "wavelengths_um": SPECTRAL_WAVELENGTHS_UM,
    }


def _default_stack_for_sensor(
    norm_indices: Dict[str, np.ndarray],
    aster_swir: bool,
    deposit_model: str = "orogenico_vetas",
) -> List[str]:
    if deposit_model == "aluvial_placer":
        preferred = ["s2_aluvial_turbidez", "s2_feox", "s2_arcilla_cai", "fe3", "cuarzo", "l8_arcilla", "clorita"]
    elif aster_swir and "alunita" in norm_indices:
        preferred = ["alunita", "caolinita", "sericita", "gossan", "fe3", "cuarzo", "clorita", "s2_arcilla_cai"]
    else:
        preferred = ["s2_arcilla_cai", "s2_feox", "s2_pai", "s2_gossan", "s2_ferroso", "l8_arcilla", "cuarzo"]
    selected = [k for k in preferred if k in norm_indices]
    if len(selected) < 3:
        selected = [k for k in norm_indices.keys() if k not in ("ndvi", "ndwi")][:6]
    return selected


def _downsample_grid(arr: np.ndarray, step: int = 2) -> List[List[float]]:
    sub = arr[::step, ::step]
    clean = np.where(np.isfinite(sub), np.round(sub, 3), -1.0)
    return clean.tolist()


def _build_methodology_audit(
    req: AnalysisRequest,
    diagnostics: Dict[str, Any],
    dem_source: str,
    structural_stats: Dict[str, Any],
    sgc_metrics: Dict[str, Any],
    legal_status: Dict[str, Any],
    ml_summary: Dict[str, Any],
    active_spec_weights: Dict[str, float],
    weight_source: str,
    prosp_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Construye el dictamen de transparencia metodológica ('¿Qué se está usando?') con las fuentes orbitales,
    sensores, resoluciones, ecuaciones, coberturas enmascaradas y alcance de prefactibilidad en tiempo real.
    """
    stac = diagnostics.get("stac_scene") or {}
    cog_real = bool(diagnostics.get("cog_real", False))
    cog_meta = diagnostics.get("cog_meta") or {}
    aster_on = bool(diagnostics.get("aster_swir_available", False))
    mask_stats = diagnostics.get("mask_stats") or {}
    model_cfg = DEPOSIT_MODELS.get(req.deposit_model, DEPOSIT_MODELS["orogenico_vetas"])

    if cog_real:
        s2_status = "activo"
        s2_badge = "COG 16-bit Real"
        s2_detail = (
            f"Escena {stac.get('scene_id', 'S2_L2A')} ({stac.get('date', 'reciente')}, "
            f"nubes {stac.get('cloud_cover_pct', 0)}%) · Bandas B02, B03, B04, B08, B8A, B11, B12 + máscara oficial ESA SCL "
            f"(~{cog_meta.get('target_res_m', 20)} m/px, {cog_meta.get('scenes_composited', 1)} escena(s))."
        )
    else:
        s2_status = "respaldo"
        s2_badge = "Respaldo Óptico"
        s2_detail = f"{diagnostics.get('optical_source', 'Mosaico Sentinel-2 Cloudless')} · Calibración multiespectral."

    if aster_on:
        ast_status = "activo"
        ast_badge = "Archivo 2000–2008"
        ast_detail = "Bandas históricas ASTER L1T VNIR + SWIR (B4–B9, 30 m) + TIR (B10–B14, 90 m) habilitadas para ventana pre-2008."
    else:
        ast_status = "inactivo_fisico"
        ast_badge = "SWIR Inactivo Post-2008"
        ast_detail = (
            "El detector SWIR de ASTER cesó operaciones el 28-abr-2008 (NASA/METI). Por rigor de prefactibilidad no se "
            "sintetizan bandas SWIR artificiales en fechas modernas; los pesos se redistribuyen a reflectancia medida Sentinel-2."
        )

    dem_is_cop = "Copernicus" in dem_source
    sources_active = [
        {
            "id": "optical_swir",
            "category": "Reflectancia Orbital",
            "name": "Sentinel-2 L2A MSI (ESA / Copernicus)",
            "status": s2_status,
            "badge": s2_badge,
            "detail": s2_detail,
        },
        {
            "id": "aster_swir_tir",
            "category": "Espectrometría SWIR/TIR",
            "name": "TERRA ASTER L1T (Archivo Histórico)",
            "status": ast_status,
            "badge": ast_badge,
            "detail": ast_detail,
        },
        {
            "id": "dem_structural",
            "category": "Modelo Digital Elevación",
            "name": dem_source,
            "status": "activo" if dem_is_cop else "respaldo",
            "badge": "30m Float32 COG" if dem_is_cop else "Respaldo DEM",
            "detail": (
                f"Pendiente media {structural_stats.get('slope_mean_deg', 0)}° (máx {structural_stats.get('slope_max_deg', 0)}°) · "
                f"Gradientes morfoestructurales Sobel + Laplaciano."
            ),
        },
        {
            "id": "sgc_geology",
            "category": "Geología y Metalogenia",
            "name": "Servicio Geológico Colombiano (SGC ArcGIS REST)",
            "status": "activo" if sgc_metrics.get("sgc_connected", True) else "respaldo",
            "badge": f"{sgc_metrics.get('fault_count', 0)} Fallas · {sgc_metrics.get('deposit_count', 0)} Yac.",
            "detail": (
                f"Falla más cercana: {sgc_metrics.get('nearest_fault_km', 'N/A')} km · "
                f"Referencia: {sgc_metrics.get('nearest_deposit_name') or 'Consulta regional SGC'}."
            ),
        },
        {
            "id": "anm_cadastre",
            "category": "Catastro Minero",
            "name": "Agencia Nacional de Minería (ANM AnnA Minería)",
            "status": "activo",
            "badge": f"{prosp_summary.get('free_targets_count', 0)} Blancos Libres",
            "detail": legal_status.get("status_summary", "Cruce geométrico por polígono contra títulos y solicitudes vigentes."),
        },
        {
            "id": "ml_engine",
            "category": "Clasificación IA / ML",
            "name": ml_summary.get("method", "K-Means++ Estandarizado"),
            "status": "activo",
            "badge": f"{len(ml_summary.get('clusters', []))} Dominios",
            "detail": (
                f"Stack activo de {len(ml_summary.get('stack_keys', []))} índices normalizados ({req.norm_method}) + "
                f"Similitud Coseno LOO ({ml_summary.get('spectral_similarity', {}).get('loo_coherence', 0)})."
            ),
        },
        {
            "id": "basemap_visual",
            "category": "Cartografía Base Visual",
            "name": "Mosaicos HD Leaflet (Google Satélite / Sentinel-2 Cloudless / ESRI)",
            "status": "activo",
            "badge": "Solo Visualización",
            "detail": "Las teselas RGB de 8 bits se emplean exclusivamente como fondo cartográfico visual; jamás alteran la matemática espectral.",
        },
    ]

    active_equations = []
    for k, w_val in active_spec_weights.items():
        cat = INDICES_CATALOG.get(k, {})
        active_equations.append({
            "key": k,
            "name": cat.get("name", k),
            "sensor": cat.get("sensor", "Multisensor"),
            "formula": cat.get("formula", ""),
            "mineral": cat.get("mineral", ""),
            "weight_pct": round(float(w_val) * 100.0, 1),
        })

    iw_norm = prosp_summary.get("integrated_weights_normalized", {})
    return {
        "data_authenticity_tier": diagnostics.get("data_authenticity_tier", "Reflectancia Multisensor"),
        "cog_real": cog_real,
        "deposit_model_key": req.deposit_model,
        "deposit_model_label": model_cfg["label"],
        "weight_source": weight_source,
        "sources_active": sources_active,
        "surface_breakdown": mask_stats,
        "active_equations": active_equations,
        "integrated_pillars_pct": {
            "spectral": round(float(iw_norm.get("favorability", 0.42)) * 100.0, 1),
            "structural": round(float(iw_norm.get("structural", 0.26)) * 100.0, 1),
            "geological_sgc": round(float(iw_norm.get("geological_sgc", 0.20)) * 100.0, 1),
            "geophysical": round(float(iw_norm.get("geophysical", 0.12)) * 100.0, 1),
        },
        "active_filters": {
            "mask_vegetation": req.mask_vegetation,
            "ndvi_threshold": mask_stats.get("effective_ndvi_threshold", req.ndvi_threshold),
            "mask_water": req.mask_water,
            "ndwi_threshold": req.ndwi_threshold,
            "mask_shadows": req.mask_shadows,
            "mask_urban": req.mask_urban,
            "strict_evidence_mask": req.strict_evidence_mask,
            "norm_method": req.norm_method,
        },
        "prefeasibility_scope": {
            "stage": "Prefactibilidad Temprana / Selección de Blancos (Greenfield & Brownfield)",
            "measures_directly": [
                "Reflectancia superficial calibrada BOA de 16 bits (VNIR-SWIR) sobre afloramientos, claros y drenajes.",
                "Ensamblajes de alteración hidrotermal (arcillas Al-OH 2.19-2.20 µm, óxidos férricos Fe³⁺/gossan, sílice).",
                "Lineamientos morfoestructurales reales sobre radar orbital de 30 m (Copernicus GLO-30) y fallas SGC.",
                "Terrazas de grava cuaternaria y pozas de beneficio en pendientes bajas (exclusivo en modo Placer Aluvial).",
            ],
            "requires_ground_verification": [
                "El sensor óptico/SWIR mide los primeros micrómetros de superficie libre de bosque denso y nubes; no penetra dosel cerrado ni subsuelo profundo.",
                "La alteración hidrotermal indica circulación de fluidos potencialmente mineralizantes, pero la ley económica de oro (g/t Au) sólo se certifica mediante muestreo de roca/canal y ensayo al fuego.",
                "Todo blanco P1/P2 debe verificarse con espectrometría portátil en afloramiento, geoquímica multielemental (Au-Ag-As-Sb-Bi), geofísica terrestre (IP/Magnetometría) y perforación DDH.",
            ],
            "disclaimer": (
                "Estudio geocientífico de priorización satelital para prefactibilidad exploratoria. "
                "Las zonas bajo bosque denso (NDVI alto) o nubes SCL se mantienen enmascaradas (Sin Evidencia Espectral) "
                "sin extrapolar anomalías artificiales; confirme leyes de Au mediante muestreo geoquímico y sondajes."
            ),
        },
    }


@app.post("/api/analyze")
async def api_analyze(req: AnalysisRequest) -> Dict[str, Any]:
    preset_obj = next((p for p in DISTRICT_PRESETS if p["id"] == req.preset_id), None)
    if req.bbox and len(req.bbox) == 4:
        bbox = [float(x) for x in req.bbox]
        center_lon = round(0.5 * (bbox[0] + bbox[2]), 6)
        center_lat = round(0.5 * (bbox[1] + bbox[3]), 6)
    else:
        center_lat = float(req.lat)
        center_lon = float(req.lon)
        bbox = point_to_bbox(center_lat, center_lon, size_km=req.roi_size_km)

    roi_name = req.project_name or (preset_obj["name"] if preset_obj else f"Cuadrante_{center_lat:.4f}_{center_lon:.4f}")
    is_neg_ctrl = (req.preset_id == "bogota_control") or (
        4.60 <= center_lat <= 4.90 and -74.25 <= center_lon <= -73.98
    )

    known_occs: List[Dict[str, Any]] = list(req.known_occurrences or [])
    if not known_occs and preset_obj:
        known_occs.extend(preset_obj.get("known_occurrences", []))
    sb_deps = SupabaseService.get_reference_deposits(bbox)
    for d in sb_deps:
        if not any(abs(o["lat"] - d["lat"]) < 0.002 and abs(o["lon"] - d["lon"]) < 0.002 for o in known_occs):
            known_occs.append({
                "name": d["name"],
                "lat": float(d["lat"]),
                "lon": float(d["lon"]),
                "mineral": d.get("primary_mineral", "Au"),
                "grade_gt": float(d["grade_gt"]) if d.get("grade_gt") is not None else None,
            })

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_sgc = pool.submit(SGCService.get_geological_data, bbox, known_occs)
        fut_anm = pool.submit(ANMService.get_cadastre_data, bbox)
        fut_dem = pool.submit(fetch_or_synthesize_dem, bbox, ANALYSIS_GRID_SIZE)

        sgc_metrics, sgc_vectors = fut_sgc.result()
        legal_status, anm_vectors = fut_anm.result()
        dem_arr, dem_source = fut_dem.result()

    slope_deg, lineament_01, structural_stats = compute_slope_and_lineaments(dem_arr, bbox)

    cube, diagnostics = build_multisensor_cube(
        bbox=bbox,
        sensor_mode=req.sensor_mode,
        start_date=req.start_date,
        end_date=req.end_date,
        cloud_cover_max=req.cloud_cover_max,
        sgc_layers=sgc_vectors,
        sgc_metrics=sgc_metrics,
        known_occurrences=known_occs,
        is_negative_control=is_neg_ctrl,
        grid_size=ANALYSIS_GRID_SIZE,
        slope_deg=slope_deg,
        dem_arr=dem_arr,
    )
    aster_swir = bool(diagnostics["aster_swir_available"])
    is_open_ocean = bool(diagnostics.get("is_open_ocean", False))
    alluvial_active_pct = float(diagnostics.get("alluvial_mining_active_pct", 0.0))

    raw_indices = compute_all_indices(cube, sensor_mode=req.sensor_mode, aster_swir_available=aster_swir)
    valid_mask, mask_stats = build_environmental_mask(
        cube=cube,
        indices=raw_indices,
        mask_vegetation=req.mask_vegetation,
        ndvi_threshold=req.ndvi_threshold,
        mask_water=req.mask_water,
        ndwi_threshold=req.ndwi_threshold,
        mask_shadows=req.mask_shadows,
        mask_urban=req.mask_urban,
    )
    diagnostics["mask_stats"] = mask_stats
    diagnostics["dem_source"] = dem_source

    masked_indices = apply_mask_to_indices(raw_indices, valid_mask)
    norm_indices: Dict[str, np.ndarray] = {}
    indices_stats: Dict[str, Any] = {}
    for k, arr in masked_indices.items():
        norm_arr, st = normalize_array(arr, method=req.norm_method)
        norm_indices[k] = norm_arr
        meta_cat = INDICES_CATALOG.get(k, {"name": k, "sensor": "Multisensor", "formula": "", "group": "General"})
        indices_stats[k] = {**meta_cat, **st}

    stack_keys = (
        [k for k in req.selected_stack_keys if k in norm_indices]
        if req.selected_stack_keys
        else _default_stack_for_sensor(norm_indices, aster_swir, req.deposit_model)
    )
    h_px, w_px = dem_arr.shape
    stack_info = {
        "selected_keys": stack_keys,
        "bands_count": len(stack_keys),
        "dimensions": [h_px, w_px, len(stack_keys)],
        "memory_kb": round((h_px * w_px * len(stack_keys) * 8) / 1024.0, 1),
    }

    user_samples_dicts = [s.model_dump() for s in (req.training_samples or [])]
    if req.ml_method in ("random_forest", "svm"):
        cluster_labels, ml_summary = supervised_classify_spectral(
            norm_indices=norm_indices,
            cube=cube,
            bbox=bbox,
            stack_keys=stack_keys,
            classifier=req.ml_method,
            user_samples=user_samples_dicts,
            apply_majority=req.apply_majority_filter,
            majority_window=req.majority_window,
            apply_sieve=req.apply_sieve_filter,
            sieve_min_pixels=req.sieve_min_pixels,
        )
    else:
        cluster_labels, ml_summary = kmeans_classify_stack(
            norm_indices=norm_indices,
            stack_keys=stack_keys,
            n_clusters=req.n_clusters,
            apply_majority=req.apply_majority_filter,
            majority_window=req.majority_window,
            apply_sieve=req.apply_sieve_filter,
            sieve_min_pixels=req.sieve_min_pixels,
        )

    sim_map, spectral_sim_metrics = cosine_similarity_spectral(
        norm_indices=norm_indices,
        bbox=bbox,
        stack_keys=stack_keys,
        anchors=known_occs,
    )
    ml_summary["spectral_similarity"] = spectral_sim_metrics

    favorability_01, active_spec_weights, weight_source = compute_mineral_favorability(
        norm_indices=norm_indices,
        deposit_model=req.deposit_model,
        aster_swir_available=aster_swir,
        custom_weights=req.custom_spectral_weights,
        strict_nan=req.strict_nan,
        raw_indices=masked_indices,
    )

    iw_dict = req.integrated_weights.model_dump() if req.integrated_weights else None
    prospectivity_01, prosp_summary = compute_integrated_prospectivity(
        favorability_01=favorability_01,
        slope_deg=slope_deg,
        lineament_01=lineament_01,
        deposit_model=req.deposit_model,
        sgc_metrics=sgc_metrics,
        integrated_weights=iw_dict,
        is_negative_control=is_neg_ctrl,
        is_open_ocean=is_open_ocean,
        alluvial_power=cube.get("ALLUVIAL_POWER"),
        alluvial_active_pct=alluvial_active_pct,
        strict_evidence_mask=req.strict_evidence_mask,
    )
    prosp_summary["structural_stats"] = structural_stats

    targets, targets_geojson, targets_csv = extract_prioritized_targets(
        prospectivity_01=prospectivity_01,
        bbox=bbox,
        threshold=req.target_threshold,
        min_area_ha=req.min_target_area_ha,
        cluster_labels=cluster_labels,
        clusters_meta=ml_summary.get("clusters", []),
        anm_vectors=anm_vectors,
        is_open_ocean=is_open_ocean,
    )

    sgc_dep_feats = sgc_vectors.get("depositos", {}).get("features", [])
    validation = validate_targets_statistically(
        targets=targets,
        prospectivity_01=prospectivity_01,
        bbox=bbox,
        known_occurrences=known_occs,
        sgc_deposits=sgc_dep_feats,
        buffer_m=req.validation_buffer_m,
    )

    p1_count = sum(1 for t in targets if t["priority_code"] == "P1")
    free_targets_count = sum(1 for t in targets if t.get("is_free_area", True))
    geoai_plan = build_geoai_exploration_plan(
        deposit_model=req.deposit_model,
        mpi=prosp_summary["mpi"],
        targets_count=len(targets),
        p1_count=p1_count,
        aster_swir_available=aster_swir,
        sgc_metrics=sgc_metrics,
        is_open_ocean=is_open_ocean,
    )
    gee_default = generate_gee_javascript(
        template_type="multisensor_6modulos",
        roi_name=roi_name,
        bbox=bbox,
        start_date=req.start_date,
        end_date=req.end_date,
        cloud_cover_max=req.cloud_cover_max,
        ndvi_threshold=req.ndvi_threshold,
        deposit_model=req.deposit_model,
    )

    clay_key = "alunita" if "alunita" in norm_indices else "s2_arcilla_cai"
    ser_key = "sericita" if "sericita" in norm_indices else ("s2_pai" if "s2_pai" in norm_indices else clay_key)
    fe_key = "fe3" if "fe3" in norm_indices else "s2_feox"
    sil_key = "silice" if "silice" in norm_indices else ("gossan" if "gossan" in norm_indices else "s2_gossan")

    raster_overlays = {
        "gold_hotspots": render_gold_hotspots_png_b64(prospectivity_01, cutoff=0.36),
        "prospectivity_thermal": render_scalar_png_b64(
            prospectivity_01, cmap_name="thermal_rainbow", alpha_valid=225, transparent_below=0.26
        ),
        "prospectivity": render_scalar_png_b64(
            prospectivity_01, cmap_name="inferno_gold", alpha_valid=230, transparent_below=0.25
        ),
        "gold_classic": render_gold_classic_glow_png_b64(prospectivity_01, cutoff=0.30),
        "alluvial_placer": render_alluvial_placer_png_b64(
            cube["ALLUVIAL_POWER"], cube["TURBID_WATER"]
        ),
        "favorability": render_scalar_png_b64(
            favorability_01, cmap_name="turbo_alteration", alpha_valid=215, transparent_below=0.24
        ),
        "ml_clusters": render_categorical_png_b64(cluster_labels, ml_summary.get("palette", {})),
        "cosine_similarity": render_scalar_png_b64(sim_map, cmap_name="viridis", transparent_below=0.30),
        "lineaments": render_scalar_png_b64(lineament_01, cmap_name="viridis", alpha_valid=195, transparent_below=0.22),
        "idx_arcilla": render_scalar_png_b64(norm_indices[clay_key], cmap_name="turbo_alteration", transparent_below=0.25),
        "idx_feox": render_scalar_png_b64(norm_indices[fe_key], cmap_name="inferno_gold", transparent_below=0.25),
        "idx_silice_gossan": render_scalar_png_b64(
            norm_indices.get(sil_key, norm_indices[fe_key]), cmap_name="viridis", transparent_below=0.25
        ),
        "ndvi": render_scalar_png_b64(norm_indices["ndvi"], cmap_name="ndvi_green", alpha_valid=185),
        "rgb_mineralogico": render_rgb_composite_b64(
            np.nan_to_num(norm_indices.get(clay_key, cube["S2_B11"]), nan=0.05),
            np.nan_to_num(norm_indices.get(ser_key, cube["S2_B8A"]), nan=0.05),
            np.nan_to_num(norm_indices.get(fe_key, cube["S2_B4"]), nan=0.05),
        ),
        "rgb_geologia_12_11_2": render_rgb_composite_b64(cube["S2_B12"], cube["S2_B11"], cube["S2_B2"]),
        "rgb_swir_12_8a_4": render_rgb_composite_b64(cube["S2_B12"], cube["S2_B8A"], cube["S2_B4"]),
        "rgb_infrarrojo_843": render_rgb_composite_b64(cube["S2_B8"], cube["S2_B4"], cube["S2_B3"]),
        "rgb_natural_432": (
            render_rgb_composite_b64(
                cube["RGB_PREVIEW"][:, :, 0],
                cube["RGB_PREVIEW"][:, :, 1],
                cube["RGB_PREVIEW"][:, :, 2],
            )
            if "RGB_PREVIEW" in cube
            else render_rgb_composite_b64(cube["S2_B4"], cube["S2_B3"], cube["S2_B2"])
        ),
    }

    spec_bands_grid = {}
    for w_item in SPECTRAL_WAVELENGTHS_UM:
        bname = w_item["band"]
        if bname in cube:
            spec_bands_grid[bname] = _downsample_grid(cube[bname], step=2)

    pixel_inspector = {
        "grid_size": h_px // 2,
        "wavelengths": SPECTRAL_WAVELENGTHS_UM,
        "bands": spec_bands_grid,
        "prospectivity": _downsample_grid(prospectivity_01, step=2),
        "favorability": _downsample_grid(favorability_01, step=2),
        "clay_index": _downsample_grid(norm_indices[clay_key], step=2),
        "feox_index": _downsample_grid(norm_indices[fe_key], step=2),
        "alluvial_power": _downsample_grid(cube["ALLUVIAL_POWER"], step=2),
        "elevation_m": _downsample_grid(dem_arr, step=2),
        "ndvi": _downsample_grid(raw_indices["ndvi"], step=2),
        "cluster_id": cluster_labels[::2, ::2].tolist(),
    }

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    quad_key = f"{center_lat:.3f}_{center_lon:.3f}_{req.roi_size_km:.1f}km_{req.sensor_mode}_{req.deposit_model}"

    cloud_sync = {"saved": False}
    if req.save_to_cloud:
        run_payload = {
            "quadrant_key": quad_key[:150],
            "district_name": roi_name[:180],
            "sensor_mode": req.sensor_mode,
            "deposit_model": req.deposit_model,
            "ml_method": req.ml_method,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "roi_size_km": float(req.roi_size_km),
            "mpi_score": prosp_summary["mpi"],
            "favorability_mean": prosp_summary["favorability_mean"],
            "prospectivity_mean": prosp_summary["prospectivity_mean"],
            "classification_code": prosp_summary["classification_code"],
            "targets_count": len(targets),
            "p1_targets_count": p1_count,
            "validation_oa": validation["overall_accuracy"],
            "validation_kappa": validation["kappa"],
            "spatial_gain": validation["spatial_gain"],
            "cascade_level": int(diagnostics["cascade_level"]),
            "aster_swir_available": aster_swir,
            "summary_metrics": {
                "component_scores": prosp_summary["component_scores"],
                "landis_koch": validation["kappa_interpretation"],
                "legal_summary": legal_status["status_summary"],
                "free_targets_count": free_targets_count,
            },
        }
        cloud_sync = SupabaseService.save_analysis_run(run_payload, targets)

    prosp_summary["free_targets_count"] = free_targets_count
    methodology_audit = _build_methodology_audit(
        req=req,
        diagnostics=diagnostics,
        dem_source=dem_source,
        structural_stats=structural_stats,
        sgc_metrics=sgc_metrics,
        legal_status=legal_status,
        ml_summary=ml_summary,
        active_spec_weights=active_spec_weights,
        weight_source=weight_source,
        prosp_summary=prosp_summary,
    )

    response_payload: Dict[str, Any] = {
        "metadata": {
            "roi_name": roi_name,
            "preset_id": req.preset_id,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "roi_size_km": req.roi_size_km,
            "bbox": bbox,
            "roi_geojson": bbox_to_geojson_polygon(bbox, {"name": roi_name}),
            "timestamp": now_iso,
        },
        "diagnostics": diagnostics,
        "methodology_audit": methodology_audit,
        "indices_stats": indices_stats,
        "stack_info": stack_info,
        "ml_summary": ml_summary,
        "favorability_info": {
            "deposit_model": req.deposit_model,
            "weights_normalized": active_spec_weights,
            "weight_source": weight_source,
            "strict_nan": req.strict_nan,
        },
        "prospectivity_summary": prosp_summary,
        "sgc_metrics": sgc_metrics,
        "legal_status": legal_status,
        "targets": targets,
        "targets_geojson": targets_geojson,
        "targets_csv": targets_csv,
        "validation": validation,
        "geoai_plan": geoai_plan,
        "gee_script_default": gee_default,
        "raster_overlays": raster_overlays,
        "vector_layers": {
            **sgc_vectors,
            **anm_vectors,
            "targets": targets_geojson,
        },
        "pixel_inspector": pixel_inspector,
        "cloud_sync": cloud_sync,
    }
    response_payload["standalone_report_html"] = build_standalone_html_report(response_payload)
    return response_payload


@app.post("/api/magnetometry/analyze")
async def api_magnetometry_analyze(req: MagnetometryRequest) -> Dict[str, Any]:
    if req.points and len(req.points) >= 4 and not req.use_demo_dataset:
        pts_raw = [p.model_dump() for p in req.points]
    else:
        pts_raw = generate_demo_magnetometry_points(req.center_lat, req.center_lon)

    result = analyze_magnetometry_survey(pts_raw)
    cloud_res = {"saved": False}
    if req.save_to_cloud:
        cloud_res = SupabaseService.save_magnetometry_survey({
            "survey_name": req.survey_name[:190],
            "district_name": (req.district_name or "General")[:120],
            "regional_baseline_ut": result["regional_baseline_ut"],
            "min_b_ut": result["min_b_ut"],
            "max_b_ut": result["max_b_ut"],
            "void_zones_count": result["void_zones_count"],
            "points_count": result["points_count"],
            "points_json": result["points"][:120],
            "interpretation": result["interpretation"],
        })
    result["survey_name"] = req.survey_name
    result["cloud_sync"] = cloud_res
    return result


@app.post("/api/gee-script")
async def api_gee_script(req: GEEScriptRequest) -> Dict[str, str]:
    return generate_gee_javascript(
        template_type=req.template_type,
        roi_name=req.roi_name,
        bbox=req.bbox,
        start_date=req.start_date,
        end_date=req.end_date,
        cloud_cover_max=req.cloud_cover_max,
        ndvi_threshold=req.ndvi_threshold,
        deposit_model=req.deposit_model,
    )


@app.post("/api/report/html", response_class=HTMLResponse)
async def api_report_html(analysis_data: Dict[str, Any]) -> HTMLResponse:
    html = build_standalone_html_report(analysis_data)
    return HTMLResponse(content=html)


@app.get("/api/runs")
async def api_list_runs(limit: int = 15) -> Dict[str, Any]:
    rows = SupabaseService.list_recent_runs(limit=min(max(limit, 1), 50))
    return {"count": len(rows), "runs": rows}


@app.get("/api/projects")
async def api_list_projects(limit: int = 20) -> Dict[str, Any]:
    rows = SupabaseService.list_projects(limit=min(max(limit, 1), 50))
    return {"count": len(rows), "projects": rows}


@app.post("/api/projects")
async def api_save_project(req: ProjectSaveRequest) -> Dict[str, Any]:
    res = SupabaseService.save_project(req.model_dump())
    if not res.get("saved") and SupabaseService.is_configured():
        raise HTTPException(status_code=400, detail=res)
    return res


@app.get("/api/cron/sync-mining")
async def api_cron_sync_mining(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    """
    Tarea programada diaria (Vercel Cron `0 6 * * *`) que sincroniza títulos y solicitudes mineras
    sobre distritos auríferos clave de Colombia en `public.geoauv2_mining_cadastre`.
    """
    if CRON_SECRET:
        expected = f"Bearer {CRON_SECRET}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="No autorizado para ejecutar tarea Cron")

    key_districts = [p for p in DISTRICT_PRESETS if p["country"] == "Colombia" and p["id"] != "bogota_control"][:5]
    records_to_upsert: List[Dict[str, Any]] = []

    for dist in key_districts:
        bbox = point_to_bbox(dist["lat"], dist["lon"], size_km=6.0)
        _, layers = ANMService.get_cadastre_data(bbox)
        for t_feat in layers.get("titulos_vigentes", {}).get("features", [])[:15]:
            props = t_feat.get("properties") or {}
            exp = str(props.get("CODIGO_EXPEDIENTE") or props.get("NUMERO_EXPEDIENTE") or props.get("EXPEDIENTE") or "").strip()
            if not exp:
                continue
            records_to_upsert.append({
                "expediente": exp[:95],
                "record_type": "titulo",
                "titular": str(props.get("NOMBRE_DE_TITULAR") or props.get("TITULAR") or "Concesionario")[:180],
                "estado": str(props.get("ESTADO") or "Vigente")[:80],
                "etapa": str(props.get("ETAPA") or "Explotación")[:80],
                "minerales": str(props.get("MINERALES") or "Oro y Metales Preciosos")[:150],
                "area_ha": float(props.get("AREA_HA") or 0.0),
                "departamento": dist["name"].split("(")[-1].rstrip(")"),
                "municipio": dist["name"].split("-")[0].strip(),
                "min_lon": bbox[0],
                "min_lat": bbox[1],
                "max_lon": bbox[2],
                "max_lat": bbox[3],
                "geom_geojson": t_feat.get("geometry"),
            })

    synced_count = SupabaseService.upsert_cadastre_records(records_to_upsert)
    SupabaseService.log_sync(
        source="vercel_cron_anm_sgc",
        records_synced=synced_count,
        status="SUCCESS",
        details=f"Sincronización diaria completada en {len(key_districts)} distritos auríferos ({len(records_to_upsert)} expedientes consultados).",
    )
    return {
        "status": "ok",
        "districts_checked": len(key_districts),
        "records_found": len(records_to_upsert),
        "records_synced_to_supabase": synced_count,
        "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


if os.path.isdir(PUBLIC_DIR):
    css_dir = os.path.join(PUBLIC_DIR, "css")
    js_dir = os.path.join(PUBLIC_DIR, "js")
    if os.path.isdir(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.isdir(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

    @app.get("/favicon.svg", include_in_schema=False)
    async def serve_favicon() -> FileResponse:
        return FileResponse(os.path.join(PUBLIC_DIR, "favicon.svg"))

    @app.get("/", include_in_schema=False)
    async def serve_spa_index() -> FileResponse:
        return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))
