"""
Servicio de Consulta al Catastro Minero ANM (Anna Minería) — GeoAUV2
"""
from concurrent.futures import ThreadPoolExecutor
import json
import ssl
from typing import Any, Dict, List, Tuple
import urllib.parse
import urllib.request

from backend.config import ANM_SOLICITUDES_URL, ANM_TITULOS_URL


class ANMService:
    @staticmethod
    def _is_in_colombia(bbox: List[float]) -> bool:
        c_lon = 0.5 * (bbox[0] + bbox[2])
        c_lat = 0.5 * (bbox[1] + bbox[3])
        return (-82.0 <= c_lon <= -66.5) and (-4.5 <= c_lat <= 13.8)

    @staticmethod
    def _fetch_anm_layer(endpoint_url: str, bbox: List[float], timeout_sec: float = 4.0) -> List[Dict[str, Any]]:
        min_lon, min_lat, max_lon, max_lat = bbox
        params = {
            "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
        }
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            url = f"{endpoint_url}/query?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "GeoAUV2/2.0"})
            with urllib.request.urlopen(req, timeout=timeout_sec, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("features") or []
        except Exception:
            try:
                params["f"] = "json"
                url = f"{endpoint_url}/query?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={"User-Agent": "GeoAUV2/2.0"})
                with urllib.request.urlopen(req, timeout=timeout_sec, context=ctx) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                    feats = []
                    for f_raw in raw.get("features", []):
                        geom = f_raw.get("geometry") or {}
                        if "rings" in geom:
                            feats.append({
                                "type": "Feature",
                                "properties": f_raw.get("attributes") or {},
                                "geometry": {"type": "Polygon", "coordinates": geom["rings"]},
                            })
                    return feats
            except Exception:
                return []

    @staticmethod
    def get_cadastre_data(bbox: List[float]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if not ANMService._is_in_colombia(bbox):
            return (
                {
                    "status_summary": "Jurisdicción Internacional (Fuera de Catastro ANM Colombia)",
                    "active_titles_count": 0,
                    "applications_count": 0,
                    "restricted_areas_count": 0,
                    "titles_details": [],
                },
                {
                    "titulos_vigentes": {"type": "FeatureCollection", "features": []},
                    "solicitudes_vigentes": {"type": "FeatureCollection", "features": []},
                },
            )

        with ThreadPoolExecutor(max_workers=2) as ex:
            f_tit = ex.submit(ANMService._fetch_anm_layer, ANM_TITULOS_URL, bbox, 4.0)
            f_sol = ex.submit(ANMService._fetch_anm_layer, ANM_SOLICITUDES_URL, bbox, 4.0)
            titulos = f_tit.result()
            solicitudes = f_sol.result()

        details = []
        for t in titulos[:20]:
            p = t.get("properties") or {}
            try:
                area_v = round(float(p.get("AREA_HA") or 0.0), 2)
            except Exception:
                area_v = 0.0
            details.append({
                "expediente": str(p.get("CODIGO_EXPEDIENTE") or p.get("NUMERO_EXPEDIENTE") or "N/A"),
                "titular": str(p.get("NOMBRE_DE_TITULAR") or p.get("TITULAR") or "Concesionario Minero"),
                "estado": str(p.get("ESTADO") or "Vigente"),
                "etapa": str(p.get("ETAPA") or "Exploración / Explotación"),
                "minerales": str(p.get("MINERALES") or "Metales Preciosos"),
                "area_ha": area_v,
            })

        if len(titulos) > 0:
            summary = f"Área Titulada ({len(titulos)} Título(s) Vigente(s) en ANNA Minería)"
        elif len(solicitudes) > 0:
            summary = f"Área con {len(solicitudes)} Solicitud(es) de Concesión en Trámite"
        else:
            summary = "Área Libre de Títulos y Solicitudes Registradas (ANM)"

        return (
            {
                "status_summary": summary,
                "active_titles_count": len(titulos),
                "applications_count": len(solicitudes),
                "restricted_areas_count": 0,
                "titles_details": details,
            },
            {
                "titulos_vigentes": {"type": "FeatureCollection", "features": titulos},
                "solicitudes_vigentes": {"type": "FeatureCollection", "features": solicitudes},
            },
        )
