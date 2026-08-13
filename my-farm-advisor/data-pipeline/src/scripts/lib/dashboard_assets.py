#!/usr/bin/env python3
"""Dashboard asset management: Plotly.js bundling and satellite tile acquisition.

This module downloads and caches build-time assets so generated dashboards have
zero runtime external dependencies.
"""

from __future__ import annotations

import base64
import io
import math
from pathlib import Path

_PLOTLY_VERSION = "2.27.0"
_PLOTLY_CDN_URL = f"https://cdn.plot.ly/plotly-{_PLOTLY_VERSION}.min.js"

_ESRI_TILE_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)

_TILE_SIZE = 256
_EARTH_RADIUS = 6378137.0
_WORLD_MERCATOR_WIDTH = _EARTH_RADIUS * 2 * math.pi


def _asset_cache_dir() -> Path:
    from paths import SHARED_ROOT

    cache = SHARED_ROOT / "dashboard_assets"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _plotly_cache_path() -> Path:
    return _asset_cache_dir() / f"plotly-{_PLOTLY_VERSION}.min.js"


def get_plotly_bundle(*, allow_download: bool = True, timeout: int = 60) -> str:
    """Return the Plotly.js bundle as a string, downloading if necessary.

    Args:
        allow_download: If False and the bundle is not cached, raise RuntimeError.
        timeout: HTTP request timeout in seconds.

    Returns:
        The JavaScript source as a single string.
    """
    cache_path = _plotly_cache_path()
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    if not allow_download:
        raise RuntimeError(
            f"Plotly bundle not cached at {cache_path} and download disabled. "
            "Run with network access once to populate the cache, or place the "
            "bundle manually."
        )

    import requests

    print(f"Downloading Plotly.js v{_PLOTLY_VERSION} ...")
    response = requests.get(_PLOTLY_CDN_URL, timeout=timeout)
    response.raise_for_status()
    js = response.text
    if not js or len(js) < 1000:
        raise RuntimeError("Downloaded Plotly bundle appears empty or corrupted")
    cache_path.write_text(js, encoding="utf-8")
    return js


def _lonlat_to_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Project WGS84 lon/lat to Web Mercator (EPSG:3857)."""
    x = math.radians(lon) * _EARTH_RADIUS
    y = math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0)) * _EARTH_RADIUS
    return (x, y)


def _mercator_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Project Web Mercator to WGS84 lon/lat."""
    lon = math.degrees(x / _EARTH_RADIUS)
    lat = math.degrees(2.0 * math.atan(math.exp(y / _EARTH_RADIUS)) - math.pi / 2.0)
    return (lon, lat)


def _mercator_tile_xy(x: float, y: float, zoom: int) -> tuple[int, int]:
    """Return tile X/Y indices for a Mercator coordinate at a given zoom."""
    n = 2.0 ** zoom
    tile_size = _WORLD_MERCATOR_WIDTH / n
    xtile = int((x + _WORLD_MERCATOR_WIDTH / 2.0) / tile_size)
    ytile = int((_WORLD_MERCATOR_WIDTH / 2.0 - y) / tile_size)
    return (xtile, ytile)


def _tile_bounds(
    xtile: int, ytile: int, zoom: int
) -> tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) in Mercator for a tile."""
    n = 2.0 ** zoom
    tile_size = _WORLD_MERCATOR_WIDTH / n
    minx = xtile * tile_size - _WORLD_MERCATOR_WIDTH / 2.0
    maxx = (xtile + 1) * tile_size - _WORLD_MERCATOR_WIDTH / 2.0
    maxy = _WORLD_MERCATOR_WIDTH / 2.0 - ytile * tile_size
    miny = _WORLD_MERCATOR_WIDTH / 2.0 - (ytile + 1) * tile_size
    return (minx, miny, maxx, maxy)


def _choose_zoom_for_width(mercator_width: float, target_px: int = 1500) -> int:
    """Pick a zoom level so the farm extent is roughly target_px wide."""
    ratio = (_WORLD_MERCATOR_WIDTH * target_px) / (_TILE_SIZE * mercator_width)
    z = int(math.log2(ratio))
    return max(0, min(19, z))


def fetch_satellite_basemap(
    bounds_wgs84: tuple[float, float, float, float],
    *,
    buffer_pct: float = 0.15,
    target_width_px: int = 1500,
    max_tiles: int = 256,
    timeout: int = 30,
    retries: int = 2,
) -> tuple[str, tuple[float, float, float, float]] | None:
    """Download and stitch satellite tiles, returning base64 PNG + Mercator bounds.

    Args:
        bounds_wgs84: (min_lon, min_lat, max_lon, max_lat)
        buffer_pct: Buffer fraction around the bounds.
        target_width_px: Desired image width in pixels.
        max_tiles: Hard tile count limit to avoid excessive memory use.
        timeout: Per-tile request timeout in seconds.
        retries: Retries per failed tile.

    Returns:
        (base64_png_string, (minx, miny, maxx, maxy)) or None on failure.
    """
    try:
        from PIL import Image
    except ImportError:
        return None

    min_lon, min_lat, max_lon, max_lat = bounds_wgs84
    min_x, min_y = _lonlat_to_mercator(min_lon, min_lat)
    max_x, max_y = _lonlat_to_mercator(max_lon, max_lat)

    dx = (max_x - min_x) * buffer_pct
    dy = (max_y - min_y) * buffer_pct
    min_x -= dx
    min_y -= dy
    max_x += dx
    max_y += dy

    mercator_width = max_x - min_x
    zoom = _choose_zoom_for_width(mercator_width, target_px=target_width_px)

    x0, y0 = _mercator_tile_xy(min_x, max_y, zoom)
    x1, y1 = _mercator_tile_xy(max_x, min_y, zoom)

    tile_count = (x1 - x0 + 1) * (y1 - y0 + 1)
    if tile_count > max_tiles:
        while zoom > 0 and tile_count > max_tiles:
            zoom -= 1
            x0, y0 = _mercator_tile_xy(min_x, max_y, zoom)
            x1, y1 = _mercator_tile_xy(max_x, min_y, zoom)
            tile_count = (x1 - x0 + 1) * (y1 - y0 + 1)

    if tile_count <= 0 or tile_count > max_tiles:
        return None

    img_width = (x1 - x0 + 1) * _TILE_SIZE
    img_height = (y1 - y0 + 1) * _TILE_SIZE

    if img_width > 8192 or img_height > 8192:
        return None

    stitched = Image.new("RGB", (img_width, img_height))
    import requests

    session = requests.Session()
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            url = _ESRI_TILE_URL.format(z=zoom, x=tx, y=ty)
            tile_img = None
            for attempt in range(retries + 1):
                try:
                    resp = session.get(url, timeout=timeout)
                    resp.raise_for_status()
                    tile_img = Image.open(io.BytesIO(resp.content))
                    break
                except Exception:
                    if attempt == retries:
                        return None
            if tile_img is None:
                return None
            px = (tx - x0) * _TILE_SIZE
            py = (ty - y0) * _TILE_SIZE
            stitched.paste(tile_img, (px, py))
    session.close()

    global_bounds = _tile_bounds(x0, y0, zoom)
    global_minx, global_maxy = global_bounds[0], global_bounds[2]
    mpp = (_WORLD_MERCATOR_WIDTH / (2.0 ** zoom)) / _TILE_SIZE

    crop_left = int((min_x - global_minx) / mpp)
    crop_top = int((global_maxy - max_y) / mpp)
    crop_right = int((max_x - global_minx) / mpp)
    crop_bottom = int((global_maxy - min_y) / mpp)

    crop_left = max(0, min(crop_left, img_width))
    crop_top = max(0, min(crop_top, img_height))
    crop_right = max(crop_left + 1, min(crop_right, img_width))
    crop_bottom = max(crop_top + 1, min(crop_bottom, img_height))

    cropped = stitched.crop((crop_left, crop_top, crop_right, crop_bottom))
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return (b64, (min_x, min_y, max_x, max_y))
