"""
Rental affordability context for one county.

Fair Market Rents by bedroom count (HUD) as bars, with the ACS median gross
rent drawn as a reference line. Both sources require a free key/token; when
neither is loaded the panel is skipped by the build.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from data.constants import PLOTLY_FONT, SAFETY_BLUE, WVU_BLUE

_BR_LABELS = [
    ("fmr_0br", "Studio"),
    ("fmr_1br", "1 BR"),
    ("fmr_2br", "2 BR"),
    ("fmr_3br", "3 BR"),
    ("fmr_4br", "4 BR"),
]


def build_affordability(fmr_row: pd.Series | None,
                        acs_row: pd.Series | None,
                        county_name: str) -> go.Figure | None:
    labels, values = [], []
    if fmr_row is not None:
        for col, label in _BR_LABELS:
            v = fmr_row.get(col)
            if v is not None and not pd.isna(v):
                labels.append(label)
                values.append(float(v))
    if not values:
        return None

    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=WVU_BLUE,
        hovertemplate="%{x}<br>$%{y:,.0f}/mo<extra></extra>",
        name="Fair Market Rent",
    ))
    if acs_row is not None:
        rent = acs_row.get("median_gross_rent")
        if rent is not None and not pd.isna(rent):
            fig.add_hline(
                y=float(rent), line=dict(color=SAFETY_BLUE, width=2, dash="dash"),
                annotation_text=f"ACS median gross rent ${float(rent):,.0f}",
                annotation_position="top left",
                annotation_font_color=SAFETY_BLUE,
            )
    fig.update_layout(
        title=dict(text=f"{county_name} County — Fair Market Rents",
                   x=0.02, font=dict(size=15)),
        height=320, margin=dict(t=44, b=40, l=60, r=20),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=PLOTLY_FONT),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="Monthly rent", tickprefix="$", gridcolor="#EEEEEE"),
        showlegend=False,
    )
    return fig


AFFORDABILITY_NOTE = (
    "HUD Fair Market Rents (typically the 40th percentile of area rents) set "
    "payment standards for housing assistance; shown here as a rent benchmark. "
    "The dashed line is the ACS median gross rent for the county."
)
