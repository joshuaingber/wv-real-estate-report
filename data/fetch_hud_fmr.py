"""
HUD Fair Market Rents (FMR) — annual, county-level, via the HUD USER API.

FMRs by bedroom count (0–4), a rental-affordability benchmark. Federal public
data. Requires a free bearer token (register, then create one:
https://www.huduser.gov/portal/dataset/fmr-api.html). Set HUD_TOKEN in .env.
Without it this fetcher serves the committed cache if present, else empty, and
the FMR rows degrade to "—".

County entity id = state FIPS + county FIPS + "99999" (e.g. 5403999999).
"""
from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from data._sources import offline_cache
from data.constants import COUNTIES, HUD_FMR_BASE

CACHE_DIR = Path(__file__).parent / "cache"
CACHE = CACHE_DIR / "wv_fmr.parquet"

_GAP = 0.2  # seconds between county requests


def _token() -> str:
    return os.environ.get("HUD_TOKEN", "").strip()


def token_configured() -> bool:
    return bool(_token())


def _fetch_county(fips: str, year: int, token: str) -> dict | None:
    entity = f"{fips}99999"
    try:
        r = requests.get(
            f"{HUD_FMR_BASE}/data/{entity}",
            params={"year": year},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        payload = r.json().get("data", {})
    except Exception:
        return None

    # County payloads carry a top-level "basicdata" dict of FMR-by-bedroom.
    basic = payload.get("basicdata")
    if isinstance(basic, list):  # some entities return a list of subareas
        basic = basic[0] if basic else {}
    if not basic:
        return None
    return {
        "fips": fips,
        "county_name": COUNTIES[fips],
        "fmr_year": payload.get("year", year),
        "fmr_0br": basic.get("Efficiency"),
        "fmr_1br": basic.get("One-Bedroom"),
        "fmr_2br": basic.get("Two-Bedroom"),
        "fmr_3br": basic.get("Three-Bedroom"),
        "fmr_4br": basic.get("Four-Bedroom"),
    }


def fetch_fmr(year: int | None = None, force: bool = False) -> pd.DataFrame:
    """WV county Fair Market Rents for `year` (defaults to the current year)."""
    cached = offline_cache(CACHE)
    if cached is not None:
        return cached
    token = _token()
    year = year or date.today().year
    if token:
        rows = []
        for i, fips in enumerate(COUNTIES):
            if i:
                time.sleep(_GAP)
            rec = _fetch_county(fips, year, token)
            if rec:
                rows.append(rec)
        if rows:
            df = pd.DataFrame(rows)
            for c in ["fmr_0br", "fmr_1br", "fmr_2br", "fmr_3br", "fmr_4br"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.sort_values("county_name").reset_index(drop=True)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(CACHE, index=False)
            return df
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    return pd.DataFrame(columns=["fips", "county_name", "fmr_year",
                                 "fmr_0br", "fmr_1br", "fmr_2br",
                                 "fmr_3br", "fmr_4br"])


if __name__ == "__main__":
    df = fetch_fmr()
    if df.empty:
        print("empty (no HUD_TOKEN and no cache)")
    else:
        print(f"FMR {df['fmr_year'].iloc[0]}: {len(df)} WV counties")
        print(df.head(6)[["county_name", "fmr_1br", "fmr_2br", "fmr_3br"]]
              .to_string(index=False))
