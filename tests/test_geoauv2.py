"""
Suite de Pruebas Científicas, Visuales, Prefactibilidad e Integración End-to-End — GeoAuV2 v2.3
"""
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
import numpy as np

from backend.core.gee_exporter import generate_gee_javascript
from backend.core.indices import (
    build_environmental_mask,
    compute_all_indices,
    render_alluvial_placer_png_b64,
    render_gold_classic_glow_png_b64,
    render_gold_hotspots_png_b64,
    sdiv,
)
from backend.core.ml_engine import (
    apply_majority_filter_2d,
    apply_sieve_filter_2d,
    cosine_similarity_spectral,
    kmeans_classify_stack,
    supervised_classify_spectral,
)
from backend.core.multisensor_scene import build_multisensor_cube
from backend.core.normalize import normalize_array
from backend.core.prospectivity import compute_integrated_prospectivity
from backend.core.structural import (
    analyze_magnetometry_survey,
    compute_slope_and_lineaments,
    generate_demo_magnetometry_points,
)
from backend.core.targets_validation import (
    extract_prioritized_targets,
    validate_targets_statistically,
)
from backend.main import app


class TestGeoAuV2CoreAndAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_safe_division_sdiv_preserves_nan(self) -> None:
        num = np.array([[2.0, 4.0], [1.0, np.nan]])
        den = np.array([[1.0, 0.0], [1e-9, 2.0]])
        out = sdiv(num, den)
        self.assertAlmostEqual(float(out[0, 0]), 2.0)
        self.assertTrue(np.isnan(out[0, 1]))
        self.assertTrue(np.isnan(out[1, 0]))
        self.assertTrue(np.isnan(out[1, 1]))

    def test_normalization_and_28_multisensor_plus_alluvial_indices(self) -> None:
        bbox = [-74.718, 7.060, -74.680, 7.098]
        cube, diag = build_multisensor_cube(bbox=bbox, sensor_mode="multisensor", start_date="2005-01-01", grid_size=48)
        self.assertTrue(diag["aster_swir_available"])
        idx = compute_all_indices(cube, sensor_mode="multisensor", aster_swir_available=True)
        expected_aster = {
            "alunita", "aaa_rbd5", "caolinita", "sericita", "ohi",
            "mgoh_co3", "clorita", "calcita", "fe3", "fe2",
            "gossan", "cuarzo", "silice", "carbonatos", "mafico",
        }
        self.assertTrue(expected_aster.issubset(set(idx.keys())))
        self.assertIn("s2_arcilla_cai", idx)
        self.assertIn("s2_aluvial_turbidez", idx)
        self.assertIn("l8_arcilla", idx)

        arr = idx["alunita"].copy()
        arr[0, 0] = np.nan
        norm, stats = normalize_array(arr, method="p2_p98")
        self.assertTrue(np.isnan(norm[0, 0]))
        finite_vals = norm[np.isfinite(norm)]
        self.assertGreaterEqual(float(np.min(finite_vals)), 0.0)
        self.assertLessEqual(float(np.max(finite_vals)), 1.0)
        self.assertEqual(len(stats["histogram"]["counts"]), 24)

    def test_ml_kmeans_rf_svm_filters_and_spectral_similarity(self) -> None:
        bbox = [-65.770, -19.638, -65.730, -19.598]
        cube, _ = build_multisensor_cube(
            bbox=bbox,
            sensor_mode="multisensor",
            start_date="2004-01-01",
            known_occurrences=[{"name": "Domo Central", "lat": -19.6185, "lon": -65.7497}],
            grid_size=40,
        )
        raw_idx = compute_all_indices(cube, sensor_mode="multisensor", aster_swir_available=True)
        norm_idx = {k: normalize_array(v)[0] for k, v in raw_idx.items()}
        stack_keys = ["alunita", "sericita", "gossan", "fe3", "s2_arcilla_cai"]

        lbl_km, km_meta = kmeans_classify_stack(norm_idx, stack_keys, n_clusters=5)
        self.assertEqual(lbl_km.shape, (40, 40))
        self.assertEqual(len(km_meta["clusters"]), 5)

        lbl_rf, rf_meta = supervised_classify_spectral(norm_idx, cube, bbox, stack_keys, classifier="random_forest")
        self.assertEqual(lbl_rf.shape, (40, 40))
        self.assertGreater(rf_meta["accuracy_metrics"]["overall_accuracy"], 0.55)

        lbl_svm, svm_meta = supervised_classify_spectral(norm_idx, cube, bbox, stack_keys, classifier="svm")
        self.assertEqual(lbl_svm.shape, (40, 40))
        self.assertGreater(svm_meta["accuracy_metrics"]["overall_accuracy"], 0.55)

        noisy = np.ones((10, 10), dtype=np.int32) * 2
        noisy[5, 5] = 4
        cleaned_maj = apply_majority_filter_2d(noisy, window_size=3)
        cleaned_sieve = apply_sieve_filter_2d(noisy, min_pixels=4)
        self.assertEqual(int(cleaned_maj[5, 5]), 2)
        self.assertEqual(int(cleaned_sieve[5, 5]), 2)

        sim_map, sim_meta = cosine_similarity_spectral(
            norm_idx, bbox, stack_keys, anchors=[{"lat": -19.6185, "lon": -65.7497}]
        )
        self.assertEqual(sim_map.shape, (40, 40))
        self.assertIn("loo_coherence", sim_meta)

    def test_magnetometry_hydrothermal_voids_and_structural_dem(self) -> None:
        pts = generate_demo_magnetometry_points(7.0792, -74.6988)
        res = analyze_magnetometry_survey(pts)
        self.assertEqual(res["points_count"], 64)
        self.assertGreater(res["void_zones_count"], 0)
        self.assertLess(res["min_b_ut"], res["regional_baseline_ut"] - 1.5)
        self.assertEqual(len(res["grid_3d"]["b_total_ut"]), 28)

        yy, xx = np.mgrid[0:32, 0:32]
        dem = 1200.0 + 15.0 * xx + 8.0 * np.sin(yy)
        slope, lin, st = compute_slope_and_lineaments(dem, [-74.72, 7.06, -74.68, 7.10])
        self.assertEqual(slope.shape, (32, 32))
        self.assertEqual(lin.shape, (32, 32))
        self.assertGreater(st["slope_mean_deg"], 0.1)

    def test_targets_peak_coords_anm_intersection_and_utm_validation(self) -> None:
        bbox = [-74.72, 7.06, -74.68, 7.10]
        yy, xx = np.mgrid[0:50, 0:50] / 50.0
        prosp = np.exp(-(((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.02))

        # 1. Sin títulos ANM -> Área Libre Solicitable
        targets_free, fc, csv_txt = extract_prioritized_targets(prosp, bbox, threshold=0.68, min_area_ha=1.0)
        self.assertGreaterEqual(len(targets_free), 1)
        self.assertEqual(targets_free[0]["priority_code"], "P1")
        self.assertEqual(targets_free[0]["id"], "AU-01")
        self.assertIn("peak_lat", targets_free[0])
        self.assertIn("peak_lon", targets_free[0])
        self.assertTrue(targets_free[0]["is_free_area"])
        self.assertIn("Libre", targets_free[0]["legal_state"])
        self.assertIn("Prioridad 1", csv_txt)

        # 2. Con polígono ANM superpuesto -> Titulada ANM
        mock_anm = {
            "titulos_vigentes": {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {"EXPEDIENTE": "HJJ-08001"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-74.71, 7.07],
                            [-74.69, 7.07],
                            [-74.69, 7.09],
                            [-74.71, 7.09],
                            [-74.71, 7.07],
                        ]],
                    },
                }],
            },
            "solicitudes_vigentes": {"type": "FeatureCollection", "features": []},
        }
        targets_titled, _, _ = extract_prioritized_targets(
            prosp, bbox, threshold=0.68, min_area_ha=1.0, anm_vectors=mock_anm
        )
        self.assertFalse(targets_titled[0]["is_free_area"])
        self.assertIn("Titulada ANM", targets_titled[0]["legal_state"])

        val = validate_targets_statistically(
            targets=targets_free,
            prospectivity_01=prosp,
            bbox=bbox,
            known_occurrences=[{"name": "Mina Centro", "lat": 7.08, "lon": -74.70}],
            buffer_m=250.0,
        )
        self.assertEqual(val["confusion_matrix"]["tp"], 1)
        self.assertEqual(val["control_points"][0]["distance_to_target_m"], 0.0)
        self.assertGreater(val["spatial_gain"], 1.5)

    def test_gold_hotspot_and_alluvial_renderers(self) -> None:
        yy, xx = np.mgrid[0:48, 0:48] / 48.0
        prosp = np.exp(-(((xx - 0.55) ** 2 + (yy - 0.45) ** 2) / 0.03))
        b64_hot = render_gold_hotspots_png_b64(prosp, cutoff=0.36)
        b64_cls = render_gold_classic_glow_png_b64(prosp)
        b64_alv = render_alluvial_placer_png_b64(prosp, prosp * 0.5)
        self.assertTrue(b64_hot.startswith("data:image/png;base64,"))
        self.assertTrue(b64_cls.startswith("data:image/png;base64,"))
        self.assertTrue(b64_alv.startswith("data:image/png;base64,"))

    def test_open_ocean_rejection_and_alluvial_district(self) -> None:
        # Océano Pacífico abierto debe ser rechazado como estéril (Q4, MPI <= 5)
        r_ocean = self.client.post("/api/analyze", json={
            "lat": 4.5000,
            "lon": -79.5000,
            "roi_size_km": 4.0,
            "save_to_cloud": False,
        })
        self.assertEqual(r_ocean.status_code, 200)
        d_ocean = r_ocean.json()
        self.assertTrue(d_ocean["diagnostics"]["is_open_ocean"])
        self.assertLessEqual(d_ocean["prospectivity_summary"]["mpi"], 5.0)
        self.assertEqual(d_ocean["prospectivity_summary"]["classification_code"], "Q4")

        # Distrito aluvial Bajo Cauca debe activar capa aluvial y prospectividad alta
        r_alv = self.client.post("/api/analyze", json={
            "preset_id": "bajo_cauca",
            "lat": 7.5920,
            "lon": -74.8120,
            "deposit_model": "aluvial_placer",
            "roi_size_km": 5.0,
            "save_to_cloud": False,
        })
        self.assertEqual(r_alv.status_code, 200)
        d_alv = r_alv.json()
        self.assertIn("alluvial_placer", d_alv["raster_overlays"])
        self.assertIn("gold_hotspots", d_alv["raster_overlays"])
        self.assertGreater(d_alv["prospectivity_summary"]["mpi"], 45.0)

    def test_api_endpoints_and_cascade_vs_negative_control(self) -> None:
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.json()["system"], "GeoAuV2")
        self.assertEqual(r_health.json()["version"], "2.3.0")

        r_cat = self.client.get("/api/catalog")
        self.assertEqual(r_cat.status_code, 200)
        self.assertGreaterEqual(len(r_cat.json()["presets"]), 12)

        r_seg = self.client.post("/api/analyze", json={
            "preset_id": "segovia",
            "lat": 7.0792,
            "lon": -74.6988,
            "roi_size_km": 4.0,
            "ml_method": "random_forest",
            "save_to_cloud": False,
        })
        self.assertEqual(r_seg.status_code, 200)
        d_seg = r_seg.json()
        self.assertIn("elevation_m", d_seg["pixel_inspector"])
        self.assertIn("spectral_similarity", d_seg["ml_summary"])

        r_neg = self.client.post("/api/analyze", json={
            "preset_id": "bogota_control",
            "lat": 4.7500,
            "lon": -74.1200,
            "roi_size_km": 4.0,
            "save_to_cloud": False,
        })
        self.assertEqual(r_neg.status_code, 200)
        d_neg = r_neg.json()
        self.assertGreater(d_seg["prospectivity_summary"]["mpi"], d_neg["prospectivity_summary"]["mpi"] + 20.0)

        r_casc = self.client.post("/api/analyze", json={
            "lat": -17.3620,
            "lon": -67.4520,
            "sensor_mode": "multisensor",
            "start_date": "2024-06-01",
            "end_date": "2026-10-01",
            "save_to_cloud": False,
        })
        self.assertEqual(r_casc.status_code, 200)
        self.assertFalse(r_casc.json()["diagnostics"]["aster_swir_available"])
        self.assertGreaterEqual(r_casc.json()["diagnostics"]["cascade_level"], 2)

        for tpl in ("sentinel2_descarga", "multisensor_6modulos", "supervisado_rf_svm"):
            g = generate_gee_javascript(tpl, "Segovia_Test", [-74.72, 7.06, -74.68, 7.10])
            self.assertIn("ee.ImageCollection", g["code"])

        r_mag = self.client.post("/api/magnetometry/analyze", json={"use_demo_dataset": True, "save_to_cloud": False})
        self.assertEqual(r_mag.status_code, 200)
        self.assertEqual(r_mag.json()["points_count"], 64)

        r_fav = self.client.get("/favicon.svg")
        self.assertEqual(r_fav.status_code, 200)
        self.assertIn("<svg", r_fav.text)

        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("GeoAuV2", r_root.text)
        self.assertIn("methodologyModal", r_root.text)
        self.assertIn("mobileBottomNav", r_root.text)

    def test_prefeasibility_rigor_nan_urban_alluvial_isolation_and_audit(self) -> None:
        # 1. Máscara urbana: mitad roca alterada expuesta, mitad concreto/techo urbano brillante
        h, w = 20, 20
        cube = {
            "S2_B2": np.full((h, w), 0.06),
            "S2_B3": np.full((h, w), 0.08),
            "S2_B4": np.full((h, w), 0.14),
            "S2_B8": np.full((h, w), 0.16),
            "S2_B8A": np.full((h, w), 0.17),
            "S2_B11": np.full((h, w), 0.28),
            "S2_B12": np.full((h, w), 0.18),
        }
        # Mitad derecha: firma urbana plana de alto albedo azul
        cube["S2_B2"][:, 10:] = 0.18
        cube["S2_B3"][:, 10:] = 0.19
        cube["S2_B4"][:, 10:] = 0.20
        cube["S2_B8"][:, 10:] = 0.18
        cube["S2_B8A"][:, 10:] = 0.18
        cube["S2_B11"][:, 10:] = 0.22
        cube["S2_B12"][:, 10:] = 0.20

        idx = compute_all_indices(cube, sensor_mode="sentinel2", aster_swir_available=False)
        valid_mask, m_stats = build_environmental_mask(cube, idx, mask_urban=True)
        self.assertTrue(np.all(valid_mask[:, :10]))
        self.assertFalse(np.any(valid_mask[:, 10:]))
        self.assertAlmostEqual(float(m_stats["urban_masked_pct"]), 50.0, places=1)

        # 2. Preservación estricta de NaN y aislamiento de ALLUVIAL_POWER en roca dura
        fav = np.full((h, w), 0.72)
        fav[:6, :6] = np.nan  # Dosel denso o nube enmascarada
        slope = np.full((h, w), 6.0)
        lin = np.full((h, w), 0.65)
        sgc_m = {"litho_favorability": 0.75, "fault_favorability": 0.70}

        prosp_orog_alv1, _ = compute_integrated_prospectivity(
            fav, slope, lin, "orogenico_vetas", sgc_m,
            alluvial_power=np.ones((h, w)), alluvial_active_pct=40.0, strict_evidence_mask=True,
        )
        prosp_orog_alv0, _ = compute_integrated_prospectivity(
            fav, slope, lin, "orogenico_vetas", sgc_m,
            alluvial_power=np.zeros((h, w)), alluvial_active_pct=0.0, strict_evidence_mask=True,
        )
        # NaN bajo bosque/nube jamás debe extrapolarse cuando strict_evidence_mask=True
        self.assertTrue(np.all(np.isnan(prosp_orog_alv1[:6, :6])))
        # En vetas orogénicas, alluvial_power no debe alterar ni un decimal de la prospectividad
        self.assertTrue(np.allclose(prosp_orog_alv1, prosp_orog_alv0, equal_nan=True))

        # En modelo aluvial_placer sí debe activarse el aporte geomorfológico aluvial
        prosp_placer_hi, _ = compute_integrated_prospectivity(
            fav, slope, lin, "aluvial_placer", sgc_m,
            alluvial_power=np.ones((h, w)), alluvial_active_pct=35.0, strict_evidence_mask=True,
        )
        prosp_placer_lo, _ = compute_integrated_prospectivity(
            fav, slope, lin, "aluvial_placer", sgc_m,
            alluvial_power=np.zeros((h, w)), alluvial_active_pct=0.0, strict_evidence_mask=True,
        )
        self.assertGreater(float(np.nanmean(prosp_placer_hi)), float(np.nanmean(prosp_placer_lo)) + 0.05)

        # 3. Verificación de methodology_audit y trazabilidad en API y reporte HTML
        r_an = self.client.post("/api/analyze", json={
            "preset_id": "segovia",
            "lat": 7.0792,
            "lon": -74.6988,
            "roi_size_km": 4.0,
            "mask_urban": True,
            "strict_evidence_mask": True,
            "save_to_cloud": False,
        })
        self.assertEqual(r_an.status_code, 200)
        body = r_an.json()
        self.assertIn("methodology_audit", body)
        audit = body["methodology_audit"]
        self.assertIn("sources_active", audit)
        self.assertIn("surface_breakdown", audit)
        self.assertIn("active_equations", audit)
        self.assertIn("prefeasibility_scope", audit)
        self.assertGreaterEqual(len(audit["sources_active"]), 4)
        self.assertIn("Trazabilidad Científica", body["standalone_report_html"])

    def test_zero_external_system_traces_in_repository(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        forbidden_tokens = [
            "geo" + "mineral",
            "mineral" + "exploration" + "ai",
            "eddy" + "cc66",
            "edwin" + " calle",
            "geo" + "nort",
            "spatial" + "mind",
            "dzet" + "saka",
            "alpha" + "earth",
            "alpha_" + "earth",
            ".geo" + "miner",
        ]
        exts = {".py", ".html", ".css", ".js", ".md", ".sql", ".toml", ".json", ".svg"}
        skip_dirs = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules"}

        violations = []
        for path in repo_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in exts:
                continue
            if any(part in skip_dirs for part in path.parts):
                continue
            txt = path.read_text(encoding="utf-8", errors="ignore").lower()
            for tok in forbidden_tokens:
                if tok in txt:
                    violations.append(f"{path.relative_to(repo_root)} -> '{tok}'")
        self.assertEqual(violations, [], f"Se detectaron rastros externos prohibidos: {violations}")


if __name__ == "__main__":
    unittest.main()
