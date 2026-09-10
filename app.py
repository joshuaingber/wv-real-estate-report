"""
West Virginia Regional Real Estate Report — interactive Streamlit app.

The live counterpart to the static build (build.py). Same data pipeline and
chart builders; here they drive an interactive county selector and hover maps.
For fast iteration without re-hitting the APIs, run with REPORT_OFFLINE=1 to read
the committed parquet caches:

    REPORT_OFFLINE=1 streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from components import county_kpi
from components.affordability import build_affordability
from components.maps import home_value_map, hpi_yoy_map, permits_map, ppsf_map
from components.permits import build_permit_distribution, build_permit_history
from components.trends import build_hpi_trend, build_list_price_trend
from data.clean import (
    fhfa_series, latest_summary, load_data, permit_series, realtor_series,
)
from data.constants import COUNTIES, WVU_BLUE

st.set_page_config(page_title="WV Regional Real Estate Report",
                   page_icon="🏡", layout="wide")


@st.cache_data(show_spinner="Loading West Virginia housing data …")
def _load():
    data = load_data()
    return data, latest_summary(data)


data, summary = _load()

st.title("West Virginia Regional Real Estate Report")
st.caption("Residential housing indicators for all 55 counties — home prices, "
           "price per square foot, new construction, and affordability.")

# ── Statewide maps ────────────────────────────────────────────────────────────
st.header("West Virginia at a Glance")
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(home_value_map(summary, data.geojson), use_container_width=True)
    st.plotly_chart(hpi_yoy_map(summary, data.geojson), use_container_width=True)
with c2:
    st.plotly_chart(ppsf_map(summary, data.geojson), use_container_width=True)
    st.plotly_chart(permits_map(summary, data.geojson), use_container_width=True)

dist = build_permit_distribution(data.permits)
if dist is not None:
    st.header("Residential Construction")
    st.plotly_chart(dist, use_container_width=True)

# ── County detail ─────────────────────────────────────────────────────────────
st.header("Explore a County")
name_to_fips = {v: k for k, v in COUNTIES.items()}
choice = st.selectbox("Choose a county", list(COUNTIES.values()))
fips = name_to_fips[choice]
row = summary[summary["fips"] == fips].iloc[0]

county_kpi.render(row)

col1, col2 = st.columns(2)
with col1:
    hpi = build_hpi_trend(fhfa_series(data, fips), choice)
    if hpi is not None:
        st.plotly_chart(hpi, use_container_width=True)
    ph = build_permit_history(permit_series(data, fips), choice)
    if ph is not None:
        st.plotly_chart(ph, use_container_width=True)
with col2:
    lp = build_list_price_trend(realtor_series(data, fips, "median_list_price"), choice)
    if lp is not None:
        st.plotly_chart(lp, use_container_width=True)
    fmr_row = data.fmr[data.fmr["fips"] == fips]
    acs_row = data.acs[data.acs["fips"] == fips]
    aff = build_affordability(
        fmr_row.iloc[0] if not fmr_row.empty else None,
        acs_row.iloc[0] if not acs_row.empty else None, choice)
    if aff is not None:
        st.plotly_chart(aff, use_container_width=True)

st.divider()
st.subheader("All Counties")
st.dataframe(summary, use_container_width=True, hide_index=True)
st.caption("Sources: FHFA HPI, U.S. Census (ACS, Building Permits Survey), "
           "Realtor.com via FRED, HUD Fair Market Rents. Residential only.")
