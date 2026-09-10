"""
American Community Survey (ACS) 5-year — county housing profile, via Census API.

Median home value, median gross rent, owner-occupancy, housing units, median
year built, vacancy. 5-year estimates cover every county, including the small
ones. Public domain (attribution required).

VERIFIED 2026-09: the Census API requires a key — a keyless call redirects to
missing_key.html. Set CENSUS_API_KEY in .env (free, instant:
https://api.census.gov/data/key_signup.html). Without it this fetcher serves the
committed cache if present, else empty, and the ACS panels degrade to "—".
"""
from __future__ import annotations

import os
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
    ACS_DATASET,
    ACS_START_YEAR,
    ACS_VARIABLES,
    CENSUS_API_BASE,
    COUNTIES,
    STATE_FIPS,
)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE = CACHE_DIR / "wv_acs_housing.parquet"


def _api_key() -> str:
    return os.environ.get("CENSUS_API_KEY", "").strip()


def key_configured() -> bool:
    return bool(_api_key())


def _fetch_year(year: int, api_key: str) -> pd.DataFrame | None:
    url = f"{CENSUS_API_BASE}/{year}/{ACS_DATASET}"
    get_vars = "NAME," + ",".join(ACS_VARIABLES)
    params = {"get": get_vars, "for": "county:*", "in": f"state:{STATE_FIPS}",
              "key": api_key}
    try:
        r = requests.get(url, params=params, timeout=45)
        if r.status_code != 200 or not r.headers.get("Content-Type", "").startswith("application/json"):
            return None
        rows = r.json()
    except Exception:
        return None

    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["fips"] = df["state"] + df["county"]
    df = df[df["fips"].isin(COUNTIES)].copy()
    df = df.rename(columns=ACS_VARIABLES)
    for col in ACS_VARIABLES.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["county_name"] = df["fips"].map(COUNTIES)
    df["acs_year"] = year

    # Derived indicators.
    df["ownership_rate"] = (df["owner_occupied_units"] / df["occupied_units"]) * 100
    denom = df["occupied_total"] + df["vacant_units"]
    df["vacancy_rate"] = (df["vacant_units"] / denom) * 100

    keep = ["fips", "county_name", "acs_year", "median_home_value",
            "median_gross_rent", "ownership_rate", "vacancy_rate",
            "total_housing_units", "median_year_built"]
    return df[keep].sort_values("county_name").reset_index(drop=True)


def fetch_acs(force: bool = False) -> pd.DataFrame:
    """WV county ACS housing profile. Walks back to the newest published vintage."""
    cached = offline_cache(CACHE)
    if cached is not None:
        return cached
    api_key = _api_key()
    if api_key:
        for year in range(ACS_START_YEAR, 2013, -1):
            df = _fetch_year(year, api_key)
            if df is not None and not df.empty:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                df.to_parquet(CACHE, index=False)
                return df
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    return pd.DataFrame(columns=[
        "fips", "county_name", "acs_year", "median_home_value",
        "median_gross_rent", "ownership_rate", "vacancy_rate",
        "total_housing_units", "median_year_built"])


if __name__ == "__main__":
    df = fetch_acs()
    if df.empty:
        print("empty (no CENSUS_API_KEY and no cache)")
    else:
        print(f"ACS5 {int(df['acs_year'].iloc[0])}: {len(df)} WV counties")
        print(df.sort_values("median_home_value", ascending=False)
              .head(6)[["county_name", "median_home_value", "median_gross_rent",
                        "ownership_rate"]].to_string(index=False))
