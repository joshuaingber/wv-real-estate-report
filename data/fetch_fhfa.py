"""
FHFA House Price Index — annual, county-level, all-transactions (developmental).

Public domain. One workbook covers every U.S. county; we filter to West Virginia
(FIPS 54) and cache a tidy parquet. Missing values are published as ".".

Data layout (VERIFIED 2026-09): a title block, then a header on the 7th row
(State, County, FIPS code, Year, Annual Change (%), HPI, HPI with 1990 base,
HPI with 2000 base), then one row per county-year back to the 1980s.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

from data._sources import offline_cache
from data.constants import COUNTIES, FHFA_HPI_COUNTY_CANDIDATES, STATE_FIPS

CACHE_DIR = Path(__file__).parent / "cache"
CACHE = CACHE_DIR / "wv_fhfa_hpi.parquet"

# Header is the 7th row of the workbook (index 6); data follows.
_HEADER_ROW = 6


def _download() -> bytes | None:
    for url in FHFA_HPI_COUNTY_CANDIDATES:
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            # Guard against an HTML error page served with a 200.
            if r.content[:2] == b"PK" or "spreadsheet" in r.headers.get("Content-Type", ""):
                return r.content
        except Exception:
            continue
    return None


def _parse(content: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(content), header=_HEADER_ROW, dtype=str)
    df = df.rename(columns={
        "FIPS code": "fips",
        "Year": "year",
        "Annual Change (%)": "annual_change_pct",
        "HPI": "hpi",
        "HPI with 2000 base": "hpi_2000base",
    })
    df["fips"] = df["fips"].str.strip()
    wv = df[df["fips"].str.startswith(STATE_FIPS, na=False)].copy()
    wv = wv[wv["fips"].isin(COUNTIES)]

    for col in ["year", "annual_change_pct", "hpi", "hpi_2000base"]:
        # "." marks a suppressed value → NaN.
        wv[col] = pd.to_numeric(wv[col].replace(".", pd.NA), errors="coerce")
    wv["year"] = wv["year"].astype("Int64")
    wv["county_name"] = wv["fips"].map(COUNTIES)
    return (wv[["fips", "county_name", "year", "annual_change_pct",
                "hpi", "hpi_2000base"]]
            .dropna(subset=["year"])
            .sort_values(["county_name", "year"])
            .reset_index(drop=True))


def fetch_fhfa_hpi(force: bool = False) -> pd.DataFrame:
    """Return WV county FHFA HPI (long). Fresh download, cache as fallback."""
    cached = offline_cache(CACHE)
    if cached is not None:
        return cached
    content = _download()
    if content is not None:
        df = _parse(content)
        if not df.empty:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(CACHE, index=False)
            return df
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    return pd.DataFrame(
        columns=["fips", "county_name", "year", "annual_change_pct",
                 "hpi", "hpi_2000base"])


if __name__ == "__main__":
    df = fetch_fhfa_hpi()
    print(f"rows: {len(df)}; counties: {df['county_name'].nunique()}; "
          f"years: {int(df['year'].min())}–{int(df['year'].max())}")
    print(df[df["county_name"] == "Monongalia"].tail(4).to_string(index=False))
