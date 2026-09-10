"""
West Virginia county boundary geometry.

Loads the standard plotly US-counties GeoJSON (keyed on 5-digit FIPS), filtered
to state 54, with a disk + in-process cache. Returns None if the geometry can't
be obtained (no network, no cache), in which case maps degrade to a message.
"""
from __future__ import annotations

import json
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


if __name__ == "__main__":
    fc = load_wv_geojson()
    print(f"WV county features: {len(fc['features']) if fc else 'FAILED'}")
