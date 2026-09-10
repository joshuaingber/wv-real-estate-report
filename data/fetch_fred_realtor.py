"""
Realtor.com monthly county listing metrics, via the FRED API (public domain).

Metrics (per county, monthly): median listing price, median listing price per
square foot, median days on market, active listing count, new listing count.

The FRED series-ID naming is irregular across metrics, so IDs are built from the
verified prefixes in constants and each is validated against the API; a county
whose series doesn't exist (coverage is sparse for the smallest WV counties) is
simply skipped. Retry/backoff honors FRED's 429 Retry-After, mirroring the
Upper Peninsula report's FRED client.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from data._sources import offline_cache
from data.constants import (
    COUNTIES,
    FRED_API_BASE,
    FRED_REALTOR_COUNTY_PREFIXES,
)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE = CACHE_DIR / "wv_realtor.parquet"

_INTER_REQUEST_GAP = 0.4   # seconds between requests (many series → keep it modest)
_MAX_ATTEMPTS = 5
_BACKOFF_BASE = 1.0


def _api_key() -> str:
    return os.environ.get("FRED_API_KEY", "").strip()


def key_configured() -> bool:
    return bool(_api_key())


def _observations(series_id: str, api_key: str) -> pd.DataFrame | None:
    """Fetch one series's observations. Returns None on a 400 (series absent)."""
    delay = _BACKOFF_BASE
    for attempt in range(_MAX_ATTEMPTS):
        try:
            r = requests.get(
                f"{FRED_API_BASE}/series/observations",
                params={"series_id": series_id, "api_key": api_key,
                        "file_type": "json"},
                timeout=20,
            )
            if r.status_code == 400:
                return None  # series does not exist for this county
            if r.status_code == 429:
                ra = (r.headers.get("Retry-After") or "").strip()
                time.sleep(float(ra) if ra.isdigit() else delay)
                delay *= 2
                continue
            r.raise_for_status()
            obs = r.json().get("observations", [])
            df = pd.DataFrame(obs)
            if df.empty:
                return pd.DataFrame(columns=["date", "value"])
            df = df[["date", "value"]]
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            return df.dropna(subset=["value"]).reset_index(drop=True)
        except Exception:
            time.sleep(delay)
            delay *= 2
    return pd.DataFrame(columns=["date", "value"])


def _fetch_fresh(api_key: str) -> pd.DataFrame:
    frames = []
    first = True
    for fips, name in COUNTIES.items():
        for metric, prefix in FRED_REALTOR_COUNTY_PREFIXES.items():
            if not first:
                time.sleep(_INTER_REQUEST_GAP)
            first = False
            series_id = f"{prefix}{fips}"
            obs = _observations(series_id, api_key)
            if obs is None or obs.empty:
                continue
            obs["fips"] = fips
            obs["county_name"] = name
            obs["metric"] = metric
            obs["series_id"] = series_id
            frames.append(obs)
    return (pd.concat(frames, ignore_index=True)
            if frames else pd.DataFrame(
                columns=["date", "value", "fips", "county_name",
                         "metric", "series_id"]))


def fetch_realtor(force: bool = False) -> pd.DataFrame:
    """WV county Realtor.com listing metrics (long). Fresh fetch, cache fallback.

    Without a FRED key, serves the committed cache if present, else empty.
    """
    cached = offline_cache(CACHE)
    if cached is not None:
        return cached
    api_key = _api_key()
    if api_key:
        df = _fetch_fresh(api_key)
        if not df.empty:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(CACHE, index=False)
            return df
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    return pd.DataFrame(columns=["date", "value", "fips", "county_name",
                                 "metric", "series_id"])


if __name__ == "__main__":
    df = fetch_realtor()
    if df.empty:
        print("empty (no FRED key and no cache)")
    else:
        print(f"rows: {len(df)}; counties w/ data: {df['county_name'].nunique()}"
              f"/{len(COUNTIES)}")
        print("metrics per county coverage:")
        print(df.groupby("metric")["fips"].nunique().to_string())
        print("\nlatest median $/sqft by a few counties:")
        psf = df[df["metric"] == "median_list_ppsf"]
        latest = psf.sort_values("date").groupby("county_name").tail(1)
        print(latest[["county_name", "date", "value"]]
              .sort_values("value", ascending=False).head(8).to_string(index=False))
