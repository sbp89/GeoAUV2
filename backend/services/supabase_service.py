"""
Cliente REST PostgREST para Persistencia Geocientífica en Supabase — GeoAuV2
Opera exclusivamente mediante variables de entorno (`SUPABASE_URL`, `SUPABASE_KEY`) y respeta RLS.
"""
from typing import Any, Dict, List
import httpx

from backend.config import SUPABASE_KEY, SUPABASE_URL


class SupabaseService:
    @staticmethod
    def is_configured() -> bool:
        return bool(SUPABASE_URL and SUPABASE_KEY)

    @staticmethod
    def _headers(prefer: str = "return=representation") -> Dict[str, str]:
        return {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        }

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        if not cls.is_configured():
            return {"connected": False, "reason": "Variables SUPABASE_URL / SUPABASE_KEY no configuradas"}
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_mineral_deposits?select=code,name&limit=3"
            with httpx.Client(timeout=4.5) as client:
                r = client.get(url, headers=cls._headers("return=minimal"))
                if r.status_code == 200:
                    rows = r.json()
                    return {"connected": True, "benchmark_deposits_sample": len(rows)}
                return {"connected": False, "status_code": r.status_code}
        except Exception as exc:
            return {"connected": False, "reason": str(exc)}

    @classmethod
    def get_reference_deposits(cls, bbox: List[float] | None = None) -> List[Dict[str, Any]]:
        if not cls.is_configured():
            return []
        try:
            base = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_mineral_deposits?select=*"
            if bbox and len(bbox) == 4:
                min_lon, min_lat, max_lon, max_lat = bbox
                pad = 0.08
                base += (
                    f"&lat=gte.{min_lat - pad}&lat=lte.{max_lat + pad}"
                    f"&lon=gte.{min_lon - pad}&lon=lte.{max_lon + pad}"
                )
            with httpx.Client(timeout=4.5) as client:
                r = client.get(base + "&limit=50", headers=cls._headers())
                return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    @classmethod
    def save_analysis_run(
        cls,
        run_payload: Dict[str, Any],
        targets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not cls.is_configured():
            return {"saved": False, "reason": "unconfigured"}
        try:
            url_runs = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_analysis_runs"
            with httpx.Client(timeout=5.5) as client:
                resp = client.post(url_runs, headers=cls._headers(), json=run_payload)
                if resp.status_code not in (200, 201):
                    return {"saved": False, "status_code": resp.status_code, "detail": resp.text[:200]}
                created = resp.json()
                run_id = created[0]["id"] if isinstance(created, list) and created else None

                saved_targets = 0
                if run_id and targets:
                    target_rows = [
                        {
                            "run_id": run_id,
                            "target_rank": int(t["rank"]),
                            "priority": t["priority"],
                            "priority_code": t["priority_code"],
                            "area_ha": float(t["area_ha"]),
                            "score_max": float(t["score_max"]),
                            "score_mean": float(t["score_mean"]),
                            "dominant_alteration": t.get("dominant_alteration"),
                            "lat": float(t["lat"]),
                            "lon": float(t["lon"]),
                            "geom_geojson": t["geometry"],
                        }
                        for t in targets[:25]
                    ]
                    url_tgts = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_targets"
                    rt = client.post(url_tgts, headers=cls._headers("return=minimal"), json=target_rows)
                    if rt.status_code in (200, 201):
                        saved_targets = len(target_rows)

                return {"saved": True, "run_id": run_id, "targets_saved": saved_targets}
        except Exception as exc:
            return {"saved": False, "reason": str(exc)}

    @classmethod
    def list_recent_runs(cls, limit: int = 15) -> List[Dict[str, Any]]:
        if not cls.is_configured():
            return []
        try:
            url = (
                f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_analysis_runs"
                f"?select=id,quadrant_key,district_name,sensor_mode,deposit_model,ml_method,"
                f"center_lat,center_lon,roi_size_km,mpi_score,classification_code,targets_count,"
                f"p1_targets_count,validation_kappa,spatial_gain,created_at"
                f"&order=created_at.desc&limit={int(limit)}"
            )
            with httpx.Client(timeout=4.5) as client:
                r = client.get(url, headers=cls._headers())
                return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    @classmethod
    def save_project(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not cls.is_configured():
            return {"saved": False, "reason": "unconfigured"}
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_projects"
            with httpx.Client(timeout=5.0) as client:
                r = client.post(url, headers=cls._headers(), json=payload)
                if r.status_code in (200, 201):
                    rows = r.json()
                    return {"saved": True, "project": rows[0] if rows else payload}
                return {"saved": False, "status_code": r.status_code, "detail": r.text[:200]}
        except Exception as exc:
            return {"saved": False, "reason": str(exc)}

    @classmethod
    def list_projects(cls, limit: int = 20) -> List[Dict[str, Any]]:
        if not cls.is_configured():
            return []
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_projects?select=*&order=created_at.desc&limit={int(limit)}"
            with httpx.Client(timeout=4.5) as client:
                r = client.get(url, headers=cls._headers())
                return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    @classmethod
    def save_magnetometry_survey(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not cls.is_configured():
            return {"saved": False}
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_magnetometry_surveys"
            with httpx.Client(timeout=5.0) as client:
                r = client.post(url, headers=cls._headers(), json=payload)
                if r.status_code in (200, 201):
                    rows = r.json()
                    return {"saved": True, "id": rows[0]["id"] if rows else None}
                return {"saved": False, "status_code": r.status_code}
        except Exception:
            return {"saved": False}

    @classmethod
    def upsert_cadastre_records(cls, records: List[Dict[str, Any]]) -> int:
        if not cls.is_configured() or not records:
            return 0
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_mining_cadastre?on_conflict=expediente"
            headers = cls._headers("resolution=merge-duplicates,return=minimal")
            with httpx.Client(timeout=8.0) as client:
                r = client.post(url, headers=headers, json=records)
                return len(records) if r.status_code in (200, 201, 204) else 0
        except Exception:
            return 0

    @classmethod
    def log_sync(cls, source: str, records_synced: int, status: str, details: str) -> None:
        if not cls.is_configured():
            return
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/geoauv2_sync_logs"
            with httpx.Client(timeout=4.0) as client:
                client.post(
                    url,
                    headers=cls._headers("return=minimal"),
                    json={"source": source[:100], "records_synced": max(0, int(records_synced)), "status": status, "details": details},
                )
        except Exception:
            pass
