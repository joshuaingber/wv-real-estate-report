"""
Load and merge every data source into the structures the components consume.

One `load_data()` call fetches (or reads the cached) FHFA, ACS, Realtor.com,
permits, and FMR tables plus the county geometry, and returns them in a single
`RealEstateData` container. `latest_summary()` collapses everything to one row
per county for the maps and KPI cards; the `*_series()` helpers return a single
county's time series for the trend and permit charts.

Every metric is optional: a source without data (a missing API key, a county
FHFA/FRED gap) leaves NaN, which the components render as "—" / uncolored. No
value is ever fabricated to fill a gap.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from data.constants import COUNTIES
from data.fetch_bps import fetch_permits
from data.fetch_census_acs import fetch_acs
from data.fetch_fhfa import fetch_fhfa_hpi
from data.fetch_fred_realtor import fetch_realtor
from data.fetch_hud_fmr import fetch_fmr
from data.geo import load_wv_geojson


@dataclass
class RealEstateData:
    fhfa: pd.DataFrame       # long: fips, county_name, year, annual_change_pct, hpi, hpi_2000base
    acs: pd.DataFrame        # one row/county: median_home_value, rent, ownership_rate, ...
    realtor: pd.DataFrame    # long: fips, county_name, metric, date, value
    permits: pd.DataFrame    # long: fips, county_name, year, units_*, units_total
    fmr: pd.DataFrame        # one row/county: fmr_0br..fmr_4br
    geojson: dict | None


@lru_cache(maxsize=1)
def load_data() -> RealEstateData:
    """Fetch/read all sources once per process."""
    return RealEstateData(
        fhfa=fetch_fhfa_hpi(),
        acs=fetch_acs(),
        realtor=fetch_realtor(),
        permits=fetch_permits(),
        fmr=fetch_fmr(),
        geojson=load_wv_geojson(),
    )


# ── Per-county time series (for trend / permit charts) ────────────────────────

def fhfa_series(data: RealEstateData, fips: str) -> pd.DataFrame:
    """Annual FHFA HPI rows for one county, oldest→newest."""
    if data.fhfa.empty:
        return data.fhfa
    return data.fhfa[data.fhfa["fips"] == fips].sort_values("year")


def realtor_series(data: RealEstateData, fips: str, metric: str) -> pd.Series:
    """Monthly Realtor.com series (date-indexed) for one county + metric."""
    if data.realtor.empty:
        return pd.Series(dtype=float)
    sub = data.realtor[(data.realtor["fips"] == fips)
                       & (data.realtor["metric"] == metric)]
    if sub.empty:
        return pd.Series(dtype=float)
    return sub.set_index("date")["value"].sort_index()


def permit_series(data: RealEstateData, fips: str) -> pd.DataFrame:
    """Annual permit rows (by structure type) for one county, oldest→newest."""
    if data.permits.empty:
        return data.permits
    return data.permits[data.permits["fips"] == fips].sort_values("year")


# ── Latest cross-section (for maps + KPI cards) ───────────────────────────────

def _latest_by_date(df: pd.DataFrame, value_col: str = "value") -> pd.DataFrame:
    """Newest row per (fips, metric) for a long, date-indexed source."""
    if df.empty:
        return df
    idx = df.sort_values("date").groupby(["fips", "metric"]).tail(1)
    wide = idx.pivot_table(index="fips", columns="metric", values=value_col,
                           aggfunc="first")
    return wide


def latest_summary(data: RealEstateData) -> pd.DataFrame:
    """One row per WV county with the latest value of every headline metric.

    Always returns all 55 counties (left-joined onto the canonical list) so the
    map colors every county or explicitly shows it as missing.
    """
    base = pd.DataFrame({"fips": list(COUNTIES), "county_name": list(COUNTIES.values())})

    # FHFA: latest year's HPI + annual change.
    if not data.fhfa.empty:
        fhfa_latest = data.fhfa.sort_values("year").groupby("fips").tail(1)
        base = base.merge(
            fhfa_latest[["fips", "year", "hpi_2000base", "annual_change_pct"]]
            .rename(columns={"year": "hpi_year", "annual_change_pct": "hpi_yoy_pct"}),
            on="fips", how="left")

    # Realtor.com: latest month per metric.
    wide = _latest_by_date(data.realtor)
    if not wide.empty:
        base = base.merge(wide.reset_index(), on="fips", how="left")

    # ACS: single vintage per county.
    if not data.acs.empty:
        base = base.merge(
            data.acs[["fips", "median_home_value", "median_gross_rent",
                      "ownership_rate", "vacancy_rate", "median_year_built",
                      "total_housing_units", "acs_year"]],
            on="fips", how="left")

    # Permits: latest year's total.
    if not data.permits.empty:
        perm_latest = data.permits.sort_values("year").groupby("fips").tail(1)
        base = base.merge(
            perm_latest[["fips", "year", "units_total"]]
            .rename(columns={"year": "permit_year", "units_total": "permits_latest"}),
            on="fips", how="left")

    # FMR: 2-bedroom as the headline affordability number.
    if not data.fmr.empty:
        base = base.merge(data.fmr[["fips", "fmr_2br"]], on="fips", how="left")

    return base


if __name__ == "__main__":
    d = load_data()
    s = latest_summary(d)
    print(f"summary rows: {len(s)}  columns: {list(s.columns)}")
    cols = [c for c in ["county_name", "median_home_value", "median_list_ppsf",
                        "hpi_yoy_pct", "permits_latest"] if c in s.columns]
    print(s[cols].head(10).to_string(index=False))
