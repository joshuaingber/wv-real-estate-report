"""
West Virginia county boundary geometry.

Loads the standard plotly US-counties GeoJSON (keyed on 5-digit FIPS), filtered
to state 54, with a disk + in-process cache. Returns None if the geometry can't
be obtained (no network, no cache), in which case maps degrade to a message.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import requests

from data.constants import GEOJSON_URL, STATE_FIPS

_CACHE_DIR = Path(__file__).resolve().parent / "cache"
_GEOJSON_CACHE = _CACHE_DIR / "wv_counties.geojson"

_memo: dict | None = None


def load_wv_geojson() -> dict | None:
    """Load the WV-filtered county FeatureCollection, memoized + disk-cached."""
    global _memo
    if _memo is not None:
        return _memo

    raw = None
    if _GEOJSON_CACHE.exists():
        try:
            raw = json.loads(_GEOJSON_CACHE.read_text())
            # Already filtered to WV on a previous run.
            if raw.get("features"):
                _memo = raw
                return _memo
        except Exception:
            raw = None

    try:
        resp = requests.get(GEOJSON_URL, timeout=60)
        resp.raise_for_status()
        full = resp.json()
    except Exception:
        return None

    wv = [f for f in full.get("features", [])
          if str(f.get("id", "")).startswith(STATE_FIPS)]
    fc = {"type": "FeatureCollection", "features": wv}
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _GEOJSON_CACHE.write_text(json.dumps(fc))
    _memo = fc
    return _memo


# ── Flat projection for the inline-SVG report ─────────────────────────────────
# The static report draws counties as inline SVG paths in a shared pixel box
# instead of shipping a mapping library. project_counties() turns the lon/lat
# FeatureCollection into pre-projected 2-D paths + centroids for build.py to embed
# in its one JSON payload. This is a pure function (no network) so the build stays
# reproducible from the cached geometry alone.

_PROJ_WIDTH = 800.0   # target pixel width of the map/silhouette box
_PROJ_PAD = 8.0       # inner margin, in the same pixel units


def _rings(geometry: dict) -> list[list[list[float]]]:
    """Every coordinate ring of a Polygon or MultiPolygon, outer + holes alike."""
    t = geometry.get("type")
    if t == "Polygon":
        return list(geometry.get("coordinates", []))
    if t == "MultiPolygon":
        return [ring for poly in geometry.get("coordinates", []) for ring in poly]
    return []


def _polygons(geometry: dict) -> list[list[list[float]]]:
    """Each polygon's outer ring (index 0), used for area-weighted centroids."""
    t = geometry.get("type")
    if t == "Polygon":
        coords = geometry.get("coordinates", [])
        return [coords[0]] if coords else []
    if t == "MultiPolygon":
        return [poly[0] for poly in geometry.get("coordinates", []) if poly]
    return []


def _ring_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """Signed-area centroid of one ring in projected units. Returns (cx, cy, area)."""
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n - 1):
        x0, y0 = ring[i]
        x1, y1 = ring[i + 1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(a) < 1e-12:                       # degenerate ring → bbox center
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return (sum(xs) / len(xs), sum(ys) / len(ys), 0.0)
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a), abs(a))


def project_counties(geojson: dict) -> dict:
    """Project WV counties to a flat pixel box for inline-SVG rendering.

    Equirectangular: longitude is cosine-corrected at the state's mid-latitude,
    latitude is flipped (SVG y grows downward), then the whole state is scaled to
    fit a `_PROJ_WIDTH`-wide box with a `_PROJ_PAD` margin. Returns:

        {"W", "H", "paths": {fips: "M…Z"}, "centroids": {fips: [cx, cy]}}

    Paths and centroids share one coordinate system, so a county's label sits
    inside its own shape. Empty dict if the geometry is missing.
    """
    feats = (geojson or {}).get("features", [])
    if not feats:
        return {"W": _PROJ_WIDTH, "H": _PROJ_WIDTH, "paths": {}, "centroids": {}}

    # Mid-latitude for the longitude correction, from the overall bounding box.
    lats = [pt[1] for f in feats for ring in _rings(f["geometry"]) for pt in ring]
    lat0 = math.radians((min(lats) + max(lats)) / 2)
    kx = math.cos(lat0)

    def raw(lon, lat):
        return (lon * kx, -lat)

    xs = [raw(pt[0], pt[1])[0] for f in feats for ring in _rings(f["geometry"]) for pt in ring]
    ys = [raw(pt[0], pt[1])[1] for f in feats for ring in _rings(f["geometry"]) for pt in ring]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    scale = (_PROJ_WIDTH - 2 * _PROJ_PAD) / (maxx - minx)
    height = (maxy - miny) * scale + 2 * _PROJ_PAD

    def to_px(lon, lat):
        rx, ry = raw(lon, lat)
        return ((rx - minx) * scale + _PROJ_PAD, (ry - miny) * scale + _PROJ_PAD)

    paths: dict[str, str] = {}
    centroids: dict[str, list[float]] = {}
    for f in feats:
        fips = str(f.get("id", ""))
        geom = f["geometry"]
        segs = []
        for ring in _rings(geom):
            pts = [to_px(pt[0], pt[1]) for pt in ring]
            d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"
            segs.append(d)
        paths[fips] = "".join(segs)
        # Area-weighted centroid across outer rings (in projected px space).
        acc_x = acc_y = acc_a = 0.0
        for ring in _polygons(geom):
            px = [to_px(pt[0], pt[1]) for pt in ring]
            cx, cy, area = _ring_centroid(px)
            acc_x += cx * area
            acc_y += cy * area
            acc_a += area
        if acc_a > 0:
            centroids[fips] = [round(acc_x / acc_a, 1), round(acc_y / acc_a, 1)]
        else:
            all_px = [to_px(pt[0], pt[1]) for ring in _rings(geom) for pt in ring]
            centroids[fips] = [
                round(sum(p[0] for p in all_px) / len(all_px), 1),
                round(sum(p[1] for p in all_px) / len(all_px), 1),
            ]

    return {"W": round(_PROJ_WIDTH, 1), "H": round(height, 1),
            "paths": paths, "centroids": centroids}


if __name__ == "__main__":
    fc = load_wv_geojson()
    print(f"WV county features: {len(fc['features']) if fc else 'FAILED'}")
    if fc:
        proj = project_counties(fc)
        print(f"projected {len(proj['paths'])} counties into {proj['W']}×{proj['H']}")
