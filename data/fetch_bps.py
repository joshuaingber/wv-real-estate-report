"""
Census Building Permits Survey — annual county residential permits (public domain).

New privately-owned housing units authorized, by structure type: 1-unit,
2-unit, 3-4 unit, 5+ unit. Commercial/nonresidential permits are NOT part of
this survey, so this is a residential-construction indicator only.

Annual county files live at .../County/co{YYYY}a.txt as CSV with a two-row
header (a category row and a subfield row) then a blank line, then one row per
county. Column order (VERIFIED 2026-09), 0-indexed:
  0 year · 1 state FIPS · 2 county FIPS · 3 region · 4 division · 5 county name
  6/7/8   1-unit   Bldgs/Units/Value
  9/10/11 2-unit   Bldgs/Units/Value
  12/13/14 3-4unit Bldgs/Units/Value
  15/16/17 5+unit  Bldgs/Units/Value
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from data._sources import offline_cache
from data.constants import BPS_COUNTY_BASE, BPS_START_YEAR, COUNTIES, STATE_FIPS

CACHE_DIR = Path(__file__).parent / "cache"
CACHE = CACHE_DIR / "wv_permits.parquet"

# (unit label, Units column index)
_UNIT_COLS = {
    "units_1u": 7,
    "units_2u": 10,
    "units_34": 13,
    "units_5plus": 16,
}


def _fetch_year(year: int) -> pd.DataFrame | None:
    url = f"{BPS_COUNTY_BASE}/co{year}a.txt"
    try:
        r = requests.get(url, timeout=90)
        if r.status_code != 200:
            return None
    except Exception:
        return None

    raw = pd.read_csv(io.StringIO(r.text), header=None, skiprows=2,
                      dtype=str, engine="python", on_bad_lines="skip")
    raw = raw.dropna(subset=[0])
    # Keep genuine data rows (col0 is a 4-digit year).
    raw = raw[raw[0].str.strip().str.fullmatch(r"\d{4}", na=False)]

    raw["state"] = raw[1].str.strip().str.zfill(2)
    raw["county"] = raw[2].str.strip().str.zfill(3)
    raw["fips"] = raw["state"] + raw["county"]
    wv = raw[raw["fips"].isin(COUNTIES)].copy()
    if wv.empty:
        return None

    out = pd.DataFrame({"fips": wv["fips"].values})
    out["year"] = year
    for name, idx in _UNIT_COLS.items():
        out[name] = pd.to_numeric(wv[idx], errors="coerce").fillna(0).astype(int).values
    out["units_total"] = out[list(_UNIT_COLS)].sum(axis=1)
    out["units_multifamily"] = out[["units_2u", "units_34", "units_5plus"]].sum(axis=1)
    out["county_name"] = out["fips"].map(COUNTIES)
    return out


def fetch_permits(force: bool = False) -> pd.DataFrame:
    """WV county residential permits by year and structure type (long).

    Downloads each annual county file from BPS_START_YEAR through the current
    year, skipping years not yet published. Caches the assembled table and falls
    back to it if a run fails entirely.
    """
    cached = offline_cache(CACHE)
    if cached is not None:
        return cached
    frames = []
    for year in range(BPS_START_YEAR, date.today().year + 1):
        df = _fetch_year(year)
        if df is not None and not df.empty:
            frames.append(df)
    if frames:
        out = (pd.concat(frames, ignore_index=True)
               .sort_values(["county_name", "year"]).reset_index(drop=True))
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        out.to_parquet(CACHE, index=False)
        return out
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    return pd.DataFrame(columns=["fips", "county_name", "year", *_UNIT_COLS,
                                 "units_total", "units_multifamily"])


if __name__ == "__main__":
    df = fetch_permits()
    print(f"rows: {len(df)}; counties: {df['county_name'].nunique()}; "
          f"years: {int(df['year'].min())}–{int(df['year'].max())}")
    latest = int(df["year"].max())
    top = (df[df["year"] == latest].sort_values("units_total", ascending=False)
           .head(6)[["county_name", "units_1u", "units_multifamily", "units_total"]])
    print(f"\nTop counties by total permitted units, {latest}:")
    print(top.to_string(index=False))
