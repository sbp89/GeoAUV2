"""
Lector Nativo Cloud-Optimized GeoTIFF (COG) vía HTTP Range — GeoAuV2
Permite consultar en tiempo real reflectancia calibrada de superficie de 16 bits (Sentinel-2 L2A BOA)
y topografía radar oficial de 30 metros (Copernicus DEM GLO-30 float32) descargando únicamente
las teselas internas del cuadrante de estudio sin requerir binarios GDAL pesados en entorno serverless.
"""
from concurrent.futures import ThreadPoolExecutor
import math
import ssl
import struct
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import zlib

import numpy as np
from PIL import Image
from pyproj import Transformer


_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 12: 8}
_TYPE_FMTS = {1: "B", 3: "H", 4: "I", 12: "d"}


def _ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_range_get(url: str, start: int, end_inclusive: int, timeout: float = 4.2) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Range": f"bytes={start}-{end_inclusive}",
            "User-Agent": "GeoAuV2/2.3 ScientificCOGReader",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
        return resp.read()


def _parse_tiff_ifds(header_bytes: bytes) -> List[Dict[int, Any]]:
    """Extrae la cadena de directorios IFD (resolución nativa + pirámides internas) de un archivo COG."""
    if len(header_bytes) < 16:
        return []
    magic = header_bytes[:2]
    if magic not in (b"II", b"MM"):
        return []
    endian = "<" if magic == b"II" else ">"
    ver, ifd_off = struct.unpack(endian + "HI", header_bytes[2:8])
    if ver != 42:
        return []

    ifds: List[Dict[int, Any]] = []
    visited = set()
    while 0 < ifd_off < len(header_bytes) - 2 and ifd_off not in visited:
        visited.add(ifd_off)
        num_entries = struct.unpack(endian + "H", header_bytes[ifd_off : ifd_off + 2])[0]
        pos = ifd_off + 2
        if pos + num_entries * 12 + 4 > len(header_bytes):
            break
        tags: Dict[int, Any] = {"_endian": endian}
        for _ in range(num_entries):
            tag, typ, cnt, val_off = struct.unpack(endian + "HHII", header_bytes[pos : pos + 12])
            pos += 12
            byte_len = _TYPE_SIZES.get(typ, 1) * cnt
            if byte_len <= 4:
                raw = struct.pack(endian + "I", val_off)[:byte_len]
            elif val_off + byte_len <= len(header_bytes):
                raw = header_bytes[val_off : val_off + byte_len]
            else:
                continue
            fmt = _TYPE_FMTS.get(typ)
            if fmt:
                vals = struct.unpack(endian + str(cnt) + fmt, raw)
                tags[tag] = vals if cnt > 1 else vals[0]
        ifds.append(tags)
        next_ifd = struct.unpack(endian + "I", header_bytes[pos : pos + 4])[0]
        ifd_off = next_ifd
    return ifds


def _decode_cog_tile(
    compressed_bytes: bytes,
    tw: int,
    th: int,
    bits_per_sample: int,
    sample_format: int,
    predictor: int,
    endian: str,
) -> np.ndarray:
    """Descomprime una tesela Deflate y revierte predictores horizontales enteros (2) o flotantes (3)."""
    raw = zlib.decompress(compressed_bytes)
    if bits_per_sample == 32 and sample_format == 3:
        if predictor == 3:
            row_bytes = np.frombuffer(raw, dtype=np.uint8).reshape(th, tw * 4)
            accum = np.cumsum(row_bytes, axis=1, dtype=np.uint8)
            planes = accum.reshape(th, 4, tw)
            if endian == "<":
                planes = planes[:, ::-1, :]
            reordered = planes.transpose(0, 2, 1).copy()
            return reordered.view(endian + "f4").reshape(th, tw).astype(np.float32)
        return np.frombuffer(raw, dtype=endian + "f4").reshape(th, tw).astype(np.float32)

    dt = np.dtype(endian + ("u2" if bits_per_sample == 16 else "u1"))
    arr = np.frombuffer(raw, dtype=dt).reshape(th, tw)
    if predictor == 2:
        arr = np.cumsum(arr, axis=1, dtype=dt)
    return arr.astype(np.float32)


def read_cog_Projected_window(
    url: str,
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    out_size: int = 88,
    target_res_m: float = 20.0,
    is_categorical: bool = False,
    timeout: float = 4.2,
) -> Optional[np.ndarray]:
    """
    Lee la ventana proyectada [xmin, ymin, xmax, ymax] desde un archivo COG remoto,
    eligiendo la pirámide interna óptima que preserve el co-registro espacial sin sobrecarga de red.
    """
    hdr = _http_range_get(url, 0, 32767, timeout=timeout)
    ifds = _parse_tiff_ifds(hdr)
    if not ifds or 33550 not in ifds[0] or 33922 not in ifds[0]:
        return None

    base = ifds[0]
    base_w, base_h = int(base[256]), int(base[257])
    base_px_x, base_px_y = float(base[33550][0]), float(base[33550][1])
    tie = base[33922]
    origin_x, origin_y = float(tie[3]), float(tie[4])

    # Seleccionar pirámide interna con resolución <= target_res_m para evitar descargar megabytes innecesarios
    chosen = base
    for cand in ifds:
        if 256 not in cand or 324 not in cand or 325 not in cand:
            continue
        cw = int(cand[256])
        factor = base_w / max(cw, 1)
        cand_res = base_px_x * factor
        if cand_res <= target_res_m * 1.15:
            chosen = cand
        else:
            break

    w_img, h_img = int(chosen[256]), int(chosen[257])
    tw, th = int(chosen[322]), int(chosen[323])
    bps = int(chosen[258]) if not isinstance(chosen[258], tuple) else int(chosen[258][0])
    sfmt = int(chosen.get(339, 1)) if not isinstance(chosen.get(339, 1), tuple) else int(chosen[339][0])
    pred = int(chosen.get(317, 1))
    endian = chosen["_endian"]

    scale_x = base_px_x * (base_w / max(w_img, 1))
    scale_y = base_px_y * (base_h / max(h_img, 1))

    c0 = int(math.floor((min(xmin, xmax) - origin_x) / scale_x))
    c1 = int(math.ceil((max(xmin, xmax) - origin_x) / scale_x))
    r0 = int(math.floor((origin_y - max(ymin, ymax)) / scale_y))
    r1 = int(math.ceil((origin_y - min(ymin, ymax)) / scale_y))

    if c1 < 0 or r1 < 0 or c0 >= w_img or r0 >= h_img:
        return None

    c0_cl, c1_cl = max(0, c0), min(w_img - 1, max(0, c1))
    r0_cl, r1_cl = max(0, r0), min(h_img - 1, max(0, r1))
    if c1_cl <= c0_cl or r1_cl <= r0_cl:
        return None

    tx0, tx1 = c0_cl // tw, c1_cl // tw
    ty0, ty1 = r0_cl // th, r1_cl // th
    if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 9:
        return None

    tiles_across = (w_img + tw - 1) // tw
    offs = chosen[324] if isinstance(chosen[324], tuple) else (chosen[324],)
    bcs = chosen[325] if isinstance(chosen[325], tuple) else (chosen[325],)

    canvas = np.full(((ty1 - ty0 + 1) * th, (tx1 - tx0 + 1) * tw), np.nan, dtype=np.float32)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            t_idx = ty * tiles_across + tx
            if t_idx < 0 or t_idx >= len(offs):
                continue
            off, bc = int(offs[t_idx]), int(bcs[t_idx])
            if bc <= 0:
                continue
            comp = _http_range_get(url, off, off + bc - 1, timeout=timeout)
            tile_arr = _decode_cog_tile(comp, tw, th, bps, sfmt, pred, endian)
            y_slice = slice((ty - ty0) * th, (ty - ty0 + 1) * th)
            x_slice = slice((tx - tx0) * tw, (tx - tx0 + 1) * tw)
            canvas[y_slice, x_slice] = tile_arr

    sub = canvas[r0_cl - ty0 * th : r1_cl - ty0 * th + 1, c0_cl - tx0 * tw : c1_cl - tx0 * tw + 1]
    if sub.size == 0:
        return None

    if is_categorical:
        rr = np.linspace(0, sub.shape[0] - 1, out_size).round().astype(int)
        cc = np.linspace(0, sub.shape[1] - 1, out_size).round().astype(int)
        return sub[np.ix_(rr, cc)].astype(np.float64)

    # Remuestreo con Convolución Normalizada (evita sangrado de NaN/0 en bordes)
    valid = np.isfinite(sub)
    if not np.any(valid):
        return None
    clean_vals = np.where(valid, sub, 0.0).astype(np.float32)
    clean_w = valid.astype(np.float32)
    num_rs = np.asarray(
        Image.fromarray(clean_vals, mode="F").resize((out_size, out_size), Image.Resampling.BILINEAR),
        dtype=np.float64,
    )
    den_rs = np.asarray(
        Image.fromarray(clean_w, mode="F").resize((out_size, out_size), Image.Resampling.BILINEAR),
        dtype=np.float64,
    )
    out = np.full((out_size, out_size), np.nan, dtype=np.float64)
    ok = den_rs > 0.25
    out[ok] = num_rs[ok] / den_rs[ok]
    return out


def fetch_sentinel2_l2a_cog_cube(
    stac_features: List[Dict[str, Any]],
    bbox_wgs84: List[float],
    grid_size: int = 88,
) -> Optional[Tuple[Dict[str, np.ndarray], Dict[str, Any]]]:
    """
    Descarga las 7 bandas reflectivas calibradas de 16 bits (B02..B12) + máscara oficial ESA SCL
    desde la mejor escena Sentinel-2 L2A COG. Si hay parches de nube parciales (>8%) y existe una
    segunda escena limpia en el catálogo STAC, rellena los píxeles nubosos con observación real limpia.
    """
    if not stac_features:
        return None

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    roi_width_m = abs(max_lon - min_lon) * 111320.0 * max(math.cos(math.radians(0.5 * (min_lat + max_lat))), 0.1)
    target_res_m = max(20.0, min(60.0, roi_width_m / max(grid_size, 32)))

    band_specs = [
        ("S2_B2", "blue", False),
        ("S2_B3", "green", False),
        ("S2_B4", "red", False),
        ("S2_B8", "nir", False),
        ("S2_B8A", "nir08", False),
        ("S2_B11", "swir16", False),
        ("S2_B12", "swir22", False),
        ("SCL", "scl", True),
    ]

    def _load_single_feature(feat: Dict[str, Any]) -> Optional[Dict[str, np.ndarray]]:
        props = feat.get("properties") or {}
        epsg = props.get("proj:epsg")
        assets = feat.get("assets") or {}
        if not epsg or not all(ak in assets for _, ak, _ in band_specs):
            return None

        tr = Transformer.from_crs("EPSG:4326", f"EPSG:{int(epsg)}", always_xy=True)
        xs, ys = zip(
            tr.transform(min_lon, min_lat),
            tr.transform(max_lon, min_lat),
            tr.transform(max_lon, max_lat),
            tr.transform(min_lon, max_lat),
        )
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)

        def _worker(spec: Tuple[str, str, bool]) -> Tuple[str, Optional[np.ndarray]]:
            out_key, asset_key, is_cat = spec
            asset = assets[asset_key]
            href = asset.get("href", "")
            if not href.startswith("http"):
                return out_key, None
            arr = read_cog_Projected_window(
                url=href,
                xmin=xmin,
                ymin=ymin,
                xmax=xmax,
                ymax=ymax,
                out_size=grid_size,
                target_res_m=target_res_m,
                is_categorical=is_cat,
                timeout=4.0,
            )
            if arr is None:
                return out_key, None
            if is_cat:
                return out_key, arr

            rb = (asset.get("raster:bands") or [{}])[0]
            scale = float(rb.get("scale", 0.0001))
            offset = float(rb.get("offset", 0.0))
            nodata = float(rb.get("nodata", 0.0))

            valid_dn = np.isfinite(arr) & (arr != nodata) & (arr > 0.0)
            refl = np.full_like(arr, np.nan, dtype=np.float64)
            refl[valid_dn] = arr[valid_dn] * scale + offset
            # Descartar sobrecorrección atmosférica Rayleigh Sen2Cor (<= 0.008) o saturación defectuosa (> 1.05)
            bad = (~np.isfinite(refl)) | (refl <= 0.008) | (refl > 1.05)
            refl[bad] = np.nan
            return out_key, np.clip(refl, 0.008, 1.0)

        with ThreadPoolExecutor(max_workers=8) as pool:
            loaded = dict(pool.map(_worker, band_specs))

        if any(loaded.get(k) is None for k, _, _ in band_specs):
            return None
        return {k: v for k, v in loaded.items() if v is not None}

    try:
        primary_feat = stac_features[0]
        primary_data = _load_single_feature(primary_feat)
        if primary_data is None:
            return None

        scl_1 = np.nan_to_num(primary_data["SCL"], nan=0.0).round().astype(int)
        # Clases defectuosas/nubes/sombras de nube ESA SCL: 0=NoData, 1=Saturado, 3=Sombra Nube, 8/9=Nube, 10=Cirro, 11=Nieve
        cloud_or_bad_1 = np.isin(scl_1, [0, 1, 3, 8, 9, 10, 11])
        cloud_pct_initial = 100.0 * float(np.mean(cloud_or_bad_1))
        scenes_composited = 1

        # Si hay parches nubosos (>8%) y contamos con una 2da escena limpia, rellenar píxeles nubosos con reflectancia real
        if cloud_pct_initial > 8.0 and len(stac_features) >= 2:
            sec_data = _load_single_feature(stac_features[1])
            if sec_data is not None:
                scl_2 = np.nan_to_num(sec_data["SCL"], nan=0.0).round().astype(int)
                clean_2 = ~np.isin(scl_2, [0, 1, 3, 8, 9, 10, 11])
                patch_mask = cloud_or_bad_1 & clean_2
                if np.any(patch_mask):
                    for k in ("S2_B2", "S2_B3", "S2_B4", "S2_B8", "S2_B8A", "S2_B11", "S2_B12"):
                        primary_data[k] = np.where(patch_mask, sec_data[k], primary_data[k])
                    primary_data["SCL"] = np.where(patch_mask, sec_data["SCL"], primary_data["SCL"])
                    scenes_composited = 2

        scl_final = np.nan_to_num(primary_data["SCL"], nan=0.0).round().astype(int)
        cloud_final_mask = np.isin(scl_final, [0, 1, 3, 8, 9, 10, 11])

        # Guardar RGB continuo para vista previa visual, pero aplicar máscara estricta SCL=NaN a las bandas analíticas
        rgb_preview = np.stack([
            np.nan_to_num(primary_data["S2_B4"], nan=0.04),
            np.nan_to_num(primary_data["S2_B3"], nan=0.04),
            np.nan_to_num(primary_data["S2_B2"], nan=0.04),
        ], axis=-1)

        for k in ("S2_B2", "S2_B3", "S2_B4", "S2_B8", "S2_B8A", "S2_B11", "S2_B12"):
            arr = primary_data[k].copy()
            arr[cloud_final_mask] = np.nan
            primary_data[k] = arr

        primary_data["RGB_PREVIEW"] = rgb_preview
        meta = {
            "cog_real": True,
            "scenes_composited": scenes_composited,
            "target_res_m": round(target_res_m, 1),
            "scl_cloud_masked_pct": round(100.0 * float(np.mean(cloud_final_mask)), 2),
            "scl_water_pct": round(100.0 * float(np.mean(scl_final == 6)), 2),
            "scl_bare_soil_pct": round(100.0 * float(np.mean(scl_final == 5)), 2),
            "scl_vegetation_pct": round(100.0 * float(np.mean(scl_final == 4)), 2),
        }
        return primary_data, meta
    except Exception:
        return None


def _copernicus_dem_tile_url(lat_floor: int, lon_floor: int) -> str:
    ns = f"N{lat_floor:02d}" if lat_floor >= 0 else f"S{abs(lat_floor):02d}"
    ew = f"E{lon_floor:03d}" if lon_floor >= 0 else f"W{abs(lon_floor):03d}"
    tile_id = f"Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM"
    return f"https://copernicus-dem-30m.s3.amazonaws.com/{tile_id}/{tile_id}.tif"


def fetch_copernicus_dem_30m_cog(
    bbox_wgs84: List[float],
    grid_size: int = 88,
) -> Optional[np.ndarray]:
    """
    Obtiene el Modelo Digital de Elevación Oficial Copernicus GLO-30 (30 m, float32)
    directamente desde su repositorio Cloud-Optimized GeoTIFF público vía HTTP Range.
    """
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    c_lat = int(math.floor(0.5 * (min_lat + max_lat)))
    c_lon = int(math.floor(0.5 * (min_lon + max_lon)))
    target_res_deg = max(0.00028, min(0.0025, abs(max_lon - min_lon) / max(grid_size, 32)))

    # Si el cuadrante está contenido en una sola celda de 1°x1° (caso estándar para ROIs de 1-25 km)
    if math.floor(min_lat) == math.floor(max_lat) and math.floor(min_lon) == math.floor(max_lon):
        url = _copernicus_dem_tile_url(int(math.floor(min_lat)), int(math.floor(min_lon)))
        try:
            dem = read_cog_Projected_window(
                url=url,
                xmin=min_lon,
                ymin=min_lat,
                xmax=max_lon,
                ymax=max_lat,
                out_size=grid_size,
                target_res_m=target_res_deg,
                is_categorical=False,
                timeout=3.8,
            )
            if dem is not None and np.sum(np.isfinite(dem)) >= (grid_size * grid_size * 0.5):
                med = float(np.nanmedian(dem))
                return np.where(np.isfinite(dem), dem, med)
        except Exception:
            return None
        return None

    # Caso borde en frontera de grado entero: consultar celda central
    try:
        url = _copernicus_dem_tile_url(c_lat, c_lon)
        clip_min_lon = max(min_lon, float(c_lon) + 1e-5)
        clip_max_lon = min(max_lon, float(c_lon + 1) - 1e-5)
        clip_min_lat = max(min_lat, float(c_lat) + 1e-5)
        clip_max_lat = min(max_lat, float(c_lat + 1) - 1e-5)
        dem = read_cog_Projected_window(
            url=url,
            xmin=clip_min_lon,
            ymin=clip_min_lat,
            xmax=clip_max_lon,
            ymax=clip_max_lat,
            out_size=grid_size,
            target_res_m=0.00028,
            is_categorical=False,
            timeout=3.8,
        )
        if dem is not None and np.sum(np.isfinite(dem)) >= (grid_size * grid_size * 0.4):
            med = float(np.nanmedian(dem))
            return np.where(np.isfinite(dem), dem, med)
    except Exception:
        return None
    return None
