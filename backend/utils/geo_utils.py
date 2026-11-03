"""
Utilidades Geoespaciales Métricas para GeoAUV2
"""
import math
from typing import List, Dict, Any


def point_to_bbox(lat: float, lon: float, size_km: float = 4.0) -> List[float]:
    """Convierte un punto central (lat, lon) y lado en km a [min_lon, min_lat, max_lon, max_lat]."""
    half_km = max(float(size_km), 0.2) / 2.0
    d_lat = half_km / 111.32
    cos_lat = max(math.cos(math.radians(lat)), 0.05)
    d_lon = half_km / (111.32 * cos_lat)
    return [
        round(lon - d_lon, 6),
        round(lat - d_lat, 6),
        round(lon + d_lon, 6),
        round(lat + d_lat, 6),
    ]


def bbox_to_geojson_polygon(bbox: List[float], properties: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Genera un Feature GeoJSON rectangular a partir de [min_lon, min_lat, max_lon, max_lat]."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]],
        },
    }


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia geodésica Haversine en kilómetros."""
    r_earth = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lon1)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    )
    return 2.0 * r_earth * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def bbox_area_km2(bbox: List[float]) -> float:
    """Área aproximada en km² corrigiendo convergencia meridiana."""
    min_lon, min_lat, max_lon, max_lat = bbox
    mean_lat = 0.5 * (min_lat + max_lat)
    height_km = abs(max_lat - min_lat) * 111.32
    width_km = abs(max_lon - min_lon) * 111.32 * max(math.cos(math.radians(mean_lat)), 0.05)
    return max(height_km * width_km, 0.001)


def calculate_line_density(features: List[Dict[str, Any]], bbox: List[float]) -> float:
    """Calcula densidad lineal (km / km²) de trazas estructurales o geofísicas dentro del ROI."""
    area = bbox_area_km2(bbox)
    total_km = 0.0
    for feat in features:
        geom = feat.get("geometry") or {}
        gtype = geom.get("type", "")
        coords = geom.get("coordinates") or []
        lines = []
        if gtype == "LineString":
            lines = [coords]
        elif gtype == "MultiLineString":
            lines = coords
        for line in lines:
            for i in range(len(line) - 1):
                p1, p2 = line[i], line[i + 1]
                if len(p1) >= 2 and len(p2) >= 2:
                    total_km += calculate_distance_km(p1[1], p1[0], p2[1], p2[0])
    return round(total_km / area, 3)


def utm_epsg_for_lonlat(lon: float, lat: float) -> int:
    """Determina el código EPSG UTM métrico WGS84 para cualquier coordenada terrestre."""
    zone = int((lon + 180.0) // 6.0) + 1
    zone = max(1, min(60, zone))
    return (32600 + zone) if lat >= 0 else (32700 + zone)
