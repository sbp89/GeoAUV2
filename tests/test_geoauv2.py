"""
Suite de Pruebas Científicas e Integración End-to-End — GeoAUV2 (GeoMineral AI v2)
"""
import unittest
from fastapi.testclient import TestClient
import numpy as np

from backend.core.gee_exporter import generate_gee_javascript
from backend.core.indices import compute_all_indices, sdiv
from backend.core.ml_engine import (
    apply_majority_filter_2d,
    apply_sieve_filter_2d,
    cosine_similarity_alpha_earth,
    kmeans_classify_stack,
    supervised_classify_dzetsaka,
)
from backend.core.multisensor_scene import build_multisensor_cube
from backend.core.normalize import normalize_array
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


class TestGeoAUV2CoreAndAPI(unittest.TestCase):
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

    def test_normalization_and_15_aster_plus_s2_indices(self) -> None:
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
        self.assertIn("l8_arcilla", idx)

        arr = idx["alunita"].copy()
        arr[0, 0] = np.nan
        norm, stats = normalize_array(arr, method="p2_p98")
        self.assertTrue(np.isnan(norm[0, 0]))
        finite_vals = norm[np.isfinite(norm)]
        self.assertGreaterEqual(float(np.min(finite_vals)), 0.0)
        self.assertLessEqual(float(np.max(finite_vals)), 1.0)
        self.assertEqual(len(stats["histogram"]["counts"]), 24)

    def test_ml_kmeans_rf_svm_filters_and_alpha_earth(self) -> None:
        bbox = [-65.770, -19.638, -65.730, -19.598]  # Cerro Rico de Potosí
        cube, _ = build_multisensor_cube(
            bbox=bbox,
            sensor_mode="multisensor",
            start_date="2004-01-01",
            known_occurrences=[{"name": "Domo Cerro Rico", "lat": -19.6185, "lon": -65.7497}],
            grid_size=40,
        )
        raw_idx = compute_all_indices(cube, sensor_mode="multisensor", aster_swir_available=True)
        norm_idx = {k: normalize_array(v)[0] for k, v in raw_idx.items()}
        stack_keys = ["alunita", "sericita", "gossan", "fe3", "s2_arcilla_cai"]

        lbl_km, km_meta = kmeans_classify_stack(norm_idx, stack_keys, n_clusters=5)
        self.assertEqual(lbl_km.shape, (40, 40))
        self.assertEqual(len(km_meta["clusters"]), 5)

        lbl_rf, rf_meta = supervised_classify_dzetsaka(norm_idx, cube, bbox, stack_keys, classifier="random_forest")
        self.assertEqual(lbl_rf.shape, (40, 40))
        self.assertGreater(rf_meta["accuracy_metrics"]["overall_accuracy"], 0.55)

        lbl_svm, svm_meta = supervised_classify_dzetsaka(norm_idx, cube, bbox, stack_keys, classifier="svm")
        self.assertEqual(lbl_svm.shape, (40, 40))
        self.assertGreater(svm_meta["accuracy_metrics"]["overall_accuracy"], 0.55)

        # Verificar filtros Majority y Sieve sobre un parche sintético aislado
        noisy = np.ones((10, 10), dtype=np.int32) * 2
        noisy[5, 5] = 4  # 1 píxel aislado
        cleaned_maj = apply_majority_filter_2d(noisy, window_size=3)
        cleaned_sieve = apply_sieve_filter_2d(noisy, min_pixels=4)
        self.assertEqual(int(cleaned_maj[5, 5]), 2)
        self.assertEqual(int(cleaned_sieve[5, 5]), 2)

        sim_map, ae_meta = cosine_similarity_alpha_earth(
            norm_idx, bbox, stack_keys, anchors=[{"lat": -19.6185, "lon": -65.7497}]
        )
        self.assertEqual(sim_map.shape, (40, 40))
        self.assertIn("loo_coherence", ae_meta)

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

    def test_targets_and_utm_statistical_validation(self) -> None:
        bbox = [-74.72, 7.06, -74.68, 7.10]
        yy, xx = np.mgrid[0:50, 0:50] / 50.0
        prosp = np.exp(-(((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.02))
        targets, fc, csv_txt = extract_prioritized_targets(prosp, bbox, threshold=0.68, min_area_ha=1.0)
        self.assertGreaterEqual(len(targets), 1)
        self.assertEqual(targets[0]["priority_code"], "P1")
        self.assertIn("TGT-01", targets[0]["id"])
        self.assertIn("Prioridad 1", csv_txt)

        val = validate_targets_statistically(
            targets=targets,
            prospectivity_01=prosp,
            bbox=bbox,
            known_occurrences=[{"name": "Mina Centro", "lat": 7.08, "lon": -74.70}],
            buffer_m=250.0,
        )
        self.assertEqual(val["confusion_matrix"]["tp"], 1)
        self.assertEqual(val["control_points"][0]["distance_to_target_m"], 0.0)
        self.assertGreater(val["spatial_gain"], 1.5)

    def test_api_endpoints_and_cascade_vs_negative_control(self) -> None:
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.json()["system"], "GeoAUV2")

        r_cat = self.client.get("/api/catalog")
        self.assertEqual(r_cat.status_code, 200)
        self.assertGreaterEqual(len(r_cat.json()["presets"]), 10)

        # 1. Distrito mineralizado (Segovia) vs 2. Control Negativo (Sabana de Bogotá)
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

        # 3. Verificar cascada automática cuando start_date >= 2024-01-01 (sin SWIR ASTER histórico)
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

        # 4. GEE Scripts (los 3 templates)
        for tpl in ("sentinel2_descarga", "multisensor_6modulos", "dzetsaka_rf_svm"):
            g = generate_gee_javascript(tpl, "Segovia_Test", [-74.72, 7.06, -74.68, 7.10])
            self.assertIn("ee.ImageCollection", g["code"])

        # 5. Magnetometría endpoint y página raíz
        r_mag = self.client.post("/api/magnetometry/analyze", json={"use_demo_dataset": True, "save_to_cloud": False})
        self.assertEqual(r_mag.status_code, 200)
        self.assertEqual(r_mag.json()["points_count"], 64)

        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("GeoAUV2", r_root.text)


if __name__ == "__main__":
    unittest.main()
