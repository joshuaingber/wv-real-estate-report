"""
Per-county KPI card.

Renders one county's headline numbers as a branded card (for the static build)
or Streamlit metrics (for the app). Every metric degrades to "—" when its source
has no value for the county, so a card always renders for all 55 counties.
"""
from __future__ import annotations

import html as _html

import pandas as pd

from data.constants import WVU_BLUE
from utils.formatting import fmt_currency, fmt_number, fmt_pct, fmt_signed_pct


def _kpi_item(label: str, value: str, delta: str | None = None,
              delta_positive: bool | None = None) -> str:
    delta_html = ""
    if delta is not None:
        cls = "positive" if delta_positive else "negative"
        delta_html = f'<div class="kpi-delta {cls}">{_html.escape(delta)}</div>'
    return (
        '<div class="kpi-item">'
        f'<div class="kpi-label">{_html.escape(label)}</div>'
        f'<div class="kpi-value">{_html.escape(value)}</div>'
        f"{delta_html}</div>"
    )


def build_kpi_card_html(row: pd.Series, *, color: str = WVU_BLUE,
                        heading_level: int = 3) -> str:
    """A branded KPI card for one county's latest-summary row."""
    name = row["county_name"]

    def g(col):
        v = row.get(col)
        return None if (v is None or pd.isna(v)) else v

    value = g("median_home_value")
    ppsf = g("median_list_ppsf")
    hpi_yoy = g("hpi_yoy_pct")
    rent = g("median_gross_rent")
    own = g("ownership_rate")
    permits = g("permits_latest")

    primary = "".join([
        _kpi_item("Median Home Value",
                  fmt_currency(value) if value is not None else "—"),
        _kpi_item("Price / Sq Ft",
                  f"${ppsf:,.0f}" if ppsf is not None else "—"),
        _kpi_item("Home-Price Growth (YoY)",
                  fmt_signed_pct(hpi_yoy) if hpi_yoy is not None else "—",
                  delta=None if hpi_yoy is None else fmt_signed_pct(hpi_yoy),
                  delta_positive=None if hpi_yoy is None else hpi_yoy >= 0),
    ])
    secondary = "".join([
        _kpi_item("Median Gross Rent",
                  fmt_currency(rent) if rent is not None else "—"),
        _kpi_item("Owner-Occupied",
                  fmt_pct(own) if own is not None else "—"),
        _kpi_item("Permits (Latest Yr)",
                  fmt_number(permits) if permits is not None else "—"),
    ])

    h = heading_level
    return (
        f'<div class="county-card" style="border-left-color: {color};">'
        f'<h{h}>{_html.escape(name)} County</h{h}>'
        f'<div class="kpi-row">{primary}</div>'
        f'<div class="kpi-row secondary">{secondary}</div>'
        "</div>"
    )


def render(row: pd.Series):
    """Streamlit KPI card for one county."""
    import streamlit as st

    def g(col):
        v = row.get(col)
        return None if (v is None or pd.isna(v)) else v

    st.markdown(f"### {row['county_name']} County")
    c1, c2, c3 = st.columns(3)
    c1.metric("Median Home Value",
              fmt_currency(g("median_home_value")) if g("median_home_value") else "—")
    c2.metric("Price / Sq Ft",
              f"${g('median_list_ppsf'):,.0f}" if g("median_list_ppsf") else "—")
    hpi = g("hpi_yoy_pct")
    c3.metric("Home Value", "",
              delta=fmt_signed_pct(hpi) if hpi is not None else None)
    c4, c5, c6 = st.columns(3)
    c4.metric("Median Gross Rent",
              fmt_currency(g("median_gross_rent")) if g("median_gross_rent") else "—")
    c5.metric("Owner-Occupied",
              fmt_pct(g("ownership_rate")) if g("ownership_rate") else "—")
    c6.metric("Permits (Latest Yr)",
              fmt_number(g("permits_latest")) if g("permits_latest") else "—")
