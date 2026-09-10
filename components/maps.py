"""
West Virginia county choropleth maps.

A single builder shades all 55 counties by any column of the latest_summary()
table. Two color modes:
  - "sequential" (WVU pale→blue) for a LEVEL, e.g. median home value or $/sqft;
  - "diverging" (Woodburn→gold→WVU blue) for a YEAR-OVER-YEAR CHANGE.
Counties with no value for the chosen metric render uncolored and hover "N/A"
(FHFA covers 41 of 55 counties; FRED listing metrics are sparse for the
smallest counties) — nothing is fabricated to fill the map.

Ported from the Upper Peninsula report's county_map.py.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from data.constants import (
    MAP_DIVERGING_SCALE,
    MAP_SEQUENTIAL_BLUE,
    PLOTLY_FONT,
)


def _fmt(val, kind: str) -> str:
    if val is None or pd.isna(val):
        return "N/A"
    if kind == "usd":
        return f"${val:,.0f}"
    if kind == "usd2":
        return f"${val:,.2f}"
    if kind == "pct":
        sign = "+" if val >= 0 else "−"
        return f"{sign}{abs(val):.1f}%"
    if kind == "count":
        return f"{val:,.0f}"
    if kind == "index":
        return f"{val:,.1f}"
    return str(val)


def build_choropleth(
    summary: pd.DataFrame,
    geojson: dict,
    value_col: str,
    *,
    title: str,
    colorbar_title: str,
    value_kind: str = "usd",
    mode: str = "sequential",
) -> go.Figure:
    """Choropleth of WV counties shaded by `value_col` of `summary`.

    `summary` is latest_summary() (one row per county); `geojson` is the
    WV-filtered FeatureCollection from data.geo.load_wv_geojson().
    """
    # A source with no key/data may not contribute its column at all — treat a
    # missing column as an all-missing metric so the map renders uncolored
    # rather than raising.
    col = summary[value_col] if value_col in summary.columns else pd.Series(
        [None] * len(summary), index=summary.index)
    z = [None if pd.isna(v) else v for v in col]
    customdata = [
        [f"{name} County", _fmt(v, value_kind)]
        for name, v in zip(summary["county_name"], col)
    ]
    scale = MAP_DIVERGING_SCALE if mode == "diverging" else MAP_SEQUENTIAL_BLUE
    colorbar = dict(title=dict(text=colorbar_title, side="right"),
                    thickness=14, len=0.7)
    if value_kind == "pct":
        colorbar["ticksuffix"] = "%"
    elif value_kind in ("usd", "usd2"):
        colorbar["tickprefix"] = "$"

    kwargs = dict(
        geojson=geojson,
        featureidkey="id",
        locations=summary["fips"],
        z=z,
        colorscale=scale,
        marker_line_color="black",
        marker_line_width=0.8,
        customdata=customdata,
        colorbar=colorbar,
        hovertemplate="<b>%{customdata[0]}</b><br>" + colorbar_title
        + ": %{customdata[1]}<extra></extra>",
    )
    if mode == "diverging":
        kwargs["zmid"] = 0

    fig = go.Figure(go.Choropleth(**kwargs))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="white",
                    showlakes=False)
    fig.update_layout(
        title=dict(text=title, x=0.02, font=dict(size=15)),
        height=460,
        margin=dict(t=44, b=10, l=10, r=10),
        paper_bgcolor="white",
        geo=dict(bgcolor="white"),
        dragmode=False,
        font=dict(family=PLOTLY_FONT),
    )
    return fig


# ── Named maps used by the dashboard ─────────────────────────────────────────

def home_value_map(summary, geojson):
    return build_choropleth(
        summary, geojson, "median_home_value",
        title="Median Home Value by County",
        colorbar_title="Median value",
        value_kind="usd", mode="sequential")


def ppsf_map(summary, geojson):
    return build_choropleth(
        summary, geojson, "median_list_ppsf",
        title="Median Listing Price per Square Foot",
        colorbar_title="$ / sq ft",
        value_kind="usd2", mode="sequential")


def hpi_yoy_map(summary, geojson):
    return build_choropleth(
        summary, geojson, "hpi_yoy_pct",
        title="Home-Price Growth, Year over Year (FHFA HPI)",
        colorbar_title="YoY change",
        value_kind="pct", mode="diverging")


def permits_map(summary, geojson):
    return build_choropleth(
        summary, geojson, "permits_latest",
        title="Residential Building Permits, Latest Year",
        colorbar_title="Units authorized",
        value_kind="count", mode="sequential")


MAP_METHODOLOGY = {
    "home_value_map": (
        "Counties shaded by median value of owner-occupied homes (U.S. Census "
        "Bureau, ACS 5-year). Uncolored counties are not yet loaded (requires a "
        "Census API key)."),
    "ppsf_map": (
        "Counties shaded by the median listing price per square foot "
        "(Realtor.com via FRED, latest month). Uncolored counties have no "
        "published listing series — coverage is sparse for the smallest counties."),
    "hpi_yoy_map": (
        "Counties shaded by the one-year change in the FHFA all-transactions "
        "House Price Index (latest published year). The FHFA county index covers "
        "41 of West Virginia's 55 counties; the rest render uncolored."),
    "permits_map": (
        "Counties shaded by new privately-owned residential units authorized in "
        "the latest year (U.S. Census Bureau, Building Permits Survey). "
        "Residential permits only — the survey excludes commercial construction."),
}
