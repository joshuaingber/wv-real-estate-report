"""
Shared fetch helpers.

Offline mode: set REPORT_OFFLINE=1 to make every fetcher read its committed
parquet cache and skip the network entirely. Use it for fast local iteration and
for the Streamlit app, so editing a chart doesn't re-hit 275 FRED endpoints. The
scheduled CI build leaves it unset, so it always fetches fresh.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


def offline() -> bool:
    return os.environ.get("REPORT_OFFLINE") == "1"


def offline_cache(cache_path: Path) -> pd.DataFrame | None:
    """Return the cached parquet if offline mode is on and the cache exists."""
    if offline() and cache_path.exists():
        return pd.read_parquet(cache_path)
    return None
