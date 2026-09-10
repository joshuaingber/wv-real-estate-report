"""
Residential building permits (Census Building Permits Survey).

  - build_permit_history: one county's authorized units per year, stacked
    single-family vs. multifamily — the county-level "new builds" time series.
  - build_permit_distribution: the latest year's total permitted units across
    all 55 counties, as a ranked bar — how new construction is distributed
    statewide.

Residential only; the survey excludes commercial/nonresidential construction.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from data.constants import PLOTLY_FONT, WVU_BLUE, WVU_GOLD_DARK


def build_permit_history(permits_county: pd.DataFrame, county_name: str) -> go.Figure | None:
    df = permits_county.sort_values("year")
    if df.empty or df["units_total"].sum() == 0:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["year"], y=df["units_1u"], name="Single-family (1-unit)",
        marker_color=WVU_BLUE,
        hovertemplate="%{x}<br>Single-family: %{y:,} units<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["year"], y=df["units_multifamily"], name="Multifamily (2+ units)",
        marker_color=WVU_GOLD_DARK,
        hovertemplate="%{x}<br>Multifamily: %{y:,} units<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        title=dict(text=f"{county_name} County — Residential Permits by Year",
                   x=0.02, font=dict(size=15)),
        height=360, margin=dict(t=44, b=84, l=60, r=20),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=PLOTLY_FONT),
        xaxis=dict(title="Year", showgrid=False),
        yaxis=dict(title="Units authorized", gridcolor="#EEEEEE"),
        # Legend below the plot so it never collides with the title at the top.
        legend=dict(orientation="h", yanchor="top", y=-0.28, x=0.5,
                    xanchor="center"),
    )
    return fig


def build_permit_distribution(permits: pd.DataFrame, year: int | None = None) -> go.Figure | None:
    if permits.empty:
        return None
    year = year or int(permits["year"].max())
    df = (permits[permits["year"] == year]
          .sort_values("units_total", ascending=True))
    df = df[df["units_total"] > 0]
    if df.empty:
        return None
    fig = go.Figure(go.Bar(
        x=df["units_total"], y=df["county_name"], orientation="h",
        marker_color=WVU_BLUE,
        hovertemplate="%{y} County<br>%{x:,} units<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Residential Units Authorized by County, {year}",
                   x=0.02, font=dict(size=15)),
        height=max(420, 16 * len(df)),
        margin=dict(t=44, b=40, l=110, r=20),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=PLOTLY_FONT),
        xaxis=dict(title="Units authorized", gridcolor="#EEEEEE"),
        yaxis=dict(title="", automargin=True),
    )
    return fig


PERMITS_NOTE = (
    "New privately-owned residential units authorized by building permits "
    "(U.S. Census Bureau, Building Permits Survey). Permits authorized, not "
    "necessarily started or completed. The survey covers residential "
    "construction only."
)
