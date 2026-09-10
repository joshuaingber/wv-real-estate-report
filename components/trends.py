"""
Per-county price trends.

Two complementary views of one county's prices:
  - build_hpi_trend: the FHFA all-transactions House Price Index (annual, since
    the 1980s) — the long-run appreciation record.
  - build_list_price_trend: Realtor.com median listing price (monthly, recent),
    with an STL trend overlay and a short linear projection to the current month.

Either returns None when the county has no data for that source, so the build
can skip the panel rather than draw an empty axis.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from data.analysis import deseasonalize_trend, periods_to_current_month, project_trend
from data.constants import COOPERS_GRAY, PLOTLY_FONT, WVU_BLUE, WVU_GOLD_DARK


def build_hpi_trend(fhfa_county: pd.DataFrame, county_name: str) -> go.Figure | None:
    """Annual FHFA HPI (2000 = 100) for one county."""
    df = fhfa_county.dropna(subset=["hpi_2000base"])
    if df.empty:
        return None
    fig = go.Figure(go.Scatter(
        x=df["year"], y=df["hpi_2000base"], mode="lines",
        line=dict(color=WVU_BLUE, width=2.5),
        hovertemplate="%{x}<br>HPI (2000=100): %{y:.1f}<extra></extra>",
        name="HPI",
    ))
    fig.update_layout(
        title=dict(text=f"{county_name} County — House Price Index (FHFA)",
                   x=0.02, font=dict(size=15)),
        height=340, margin=dict(t=44, b=40, l=60, r=20),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=PLOTLY_FONT),
        xaxis=dict(title="Year", showgrid=False),
        yaxis=dict(title="Index (2000 = 100)", gridcolor="#EEEEEE"),
        showlegend=False,
    )
    return fig


def build_list_price_trend(price: pd.Series, county_name: str) -> go.Figure | None:
    """Monthly Realtor.com median listing price with STL trend + projection."""
    price = price.dropna().sort_index()
    if len(price) < 6:
        return None

    trend = deseasonalize_trend(price, period=12, log_transform=True)
    horizon = periods_to_current_month(price.index[-1])
    proj = project_trend(trend, periods=max(horizon, 1), lookback=6, log_transform=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=price.index, y=price.values, mode="markers",
        marker=dict(color=COOPERS_GRAY, size=4),
        name="Monthly median list price",
        hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=trend.index, y=trend.values, mode="lines",
        line=dict(color=WVU_BLUE, width=2.5), name="Trend (STL)",
        hovertemplate="%{x|%b %Y}<br>Trend: $%{y:,.0f}<extra></extra>",
    ))
    if not proj.empty:
        # Connect the last trend point to the projection so the dashed line joins.
        x = [trend.dropna().index[-1], *proj.index]
        y = [trend.dropna().iloc[-1], *proj.values]
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines",
            line=dict(color=WVU_GOLD_DARK, width=2, dash="dash"),
            name="Projection",
            hovertemplate="%{x|%b %Y}<br>Projected: $%{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text=f"{county_name} County — Median Listing Price",
                   x=0.02, font=dict(size=15)),
        height=340, margin=dict(t=44, b=40, l=70, r=20),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=PLOTLY_FONT),
        xaxis=dict(title="Month", showgrid=False),
        yaxis=dict(title="Median list price", tickprefix="$", gridcolor="#EEEEEE"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


TRENDS_NOTE = (
    "The House Price Index measures price changes over time (2000 = 100), not "
    "dollar levels. The listing-price trend is an STL decomposition (period = 12 "
    "months); the dashed projection extrapolates a linear fit through the last "
    "six trend points to the current month, so its horizon shrinks as new data "
    "publishes."
)
