#!/usr/bin/env python3
"""
Build the static West Virginia Regional Real Estate Report for GitHub Pages.

Reuses the data pipeline (data/clean.py) and the chart builders (components/*)
to write a self-contained docs/ site:

    docs/index.html            main dashboard — statewide maps, the permit
                               distribution, a full county table, and a county
                               selector that loads per-county detail in an iframe
    docs/embeds/<fips>.html    one accessible detail page per county (KPI card,
                               price trends, permit history, affordability)
    docs/embeds/map-*.html     each statewide map as a standalone embeddable page

Every chart is exposed to assistive tech as a single role="img" node with a
concise aria-label and is paired with a collapsible data table (the WCAG 1.1.1
text alternative). The whole site targets WCAG 2.1 AA (WVU / ADA Title II).

Usage:
    python build.py                  # fetch fresh (CI); REPORT_OFFLINE=1 for cache
"""
from __future__ import annotations

import html as _html
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from components.affordability import AFFORDABILITY_NOTE, build_affordability
from components.county_kpi import build_kpi_card_html
from components.maps import (
    MAP_METHODOLOGY, home_value_map, hpi_yoy_map, permits_map, ppsf_map,
)
from components.permits import (
    PERMITS_NOTE, build_permit_distribution, build_permit_history,
)
from components.trends import (
    TRENDS_NOTE, build_hpi_trend, build_list_price_trend,
)
from data.clean import (
    fhfa_series, latest_summary, load_data, permit_series, realtor_series,
)
from data.constants import (
    COOPERS_GRAY, COUNTIES, GOOGLE_FONTS_IMPORT, NOT_QUITE_WHITE, PLOTLY_FONT,
    RATTLER_GRAY, SOURCES, WVU_BLUE, WVU_BORDER, WVU_FONT_FAMILY, WVU_GOLD,
    WVU_GOLD_DARK, WVU_LINK, WVU_MUTED,
)
from utils.formatting import fmt_currency, fmt_number, fmt_signed_pct

DOCS_DIR = Path(__file__).parent / "docs"
EMBED_DIR = DOCS_DIR / "embeds"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

# ── CSS ───────────────────────────────────────────────────────────────────────

BASE_CSS = GOOGLE_FONTS_IMPORT + """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: """ + WVU_FONT_FAMILY + """;
    background-color: #FFFFFF;
    color: """ + RATTLER_GRAY + """;
    line-height: 1.6;
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem 2rem;
}
h1, h2, h3, h4 { color: """ + WVU_BLUE + """; }
.main-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; }
.main-subtitle { font-size: 1.05rem; margin-top: 0.25rem; color: """ + RATTLER_GRAY + """; }
.data-badge {
    display: inline-block; background-color: """ + WVU_GOLD + """;
    color: #1B222D; padding: 0.25rem 0.85rem; border-radius: 20px;
    font-size: 0.85rem; font-weight: 600; margin: 1rem 0;
}
section { margin: 2rem 0; }
section > p { margin-bottom: 0.75rem; }
.map-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
.plotly-chart { width: 100%; }
figure.chart-figure { margin: 0; }
figure.chart-figure > figcaption { font-weight: 600; margin-bottom: 0.4rem; color: """ + WVU_BLUE + """; }
.county-card {
    background: linear-gradient(135deg, """ + NOT_QUITE_WHITE + """ 0%, #FFFFFF 100%);
    border-radius: 12px; padding: 1.5rem; border-left: 5px solid;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 1rem;
}
.county-card h3 { margin: 0 0 0.8rem 0; font-size: 1.3rem; }
.kpi-row { display: flex; justify-content: space-between; gap: 0.8rem; }
.kpi-item { flex: 1; text-align: center; }
.kpi-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.5px;
    margin-bottom: 0.2rem; min-height: 2.2rem; line-height: 1.1rem; }
.kpi-value { font-size: 1.4rem; font-weight: 700; color: """ + WVU_BLUE + """; }
.kpi-delta { font-size: 0.8rem; margin-top: 0.1rem; }
.kpi-delta.positive { color: #1F6F3F; }
.kpi-delta.negative { color: #8D4638; }
.kpi-row.secondary { margin-top: 0.9rem; padding-top: 0.7rem;
    border-top: 1px solid """ + WVU_BORDER + """; }
.selector-row { margin: 1rem 0; }
.selector-row label { font-weight: 600; margin-right: 0.5rem; }
.selector-row select { font-family: inherit; font-size: 1rem; padding: 0.35rem 0.5rem;
    border: 1px solid """ + WVU_BORDER + """; border-radius: 4px; }
iframe.county-frame { width: 100%; border: 1px solid """ + WVU_BORDER + """;
    border-radius: 8px; min-height: 900px; }
.footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid """ + WVU_BORDER + """;
    font-size: 0.85rem; }
"""

A11Y_CSS = """
.source, .footer, figure.chart-figure figcaption .note { color: """ + WVU_MUTED + """; }
.source { font-size: 0.82rem; margin-top: 0.25rem; color: """ + WVU_MUTED + """; }
.source a, .footer a { color: """ + WVU_LINK + """; text-decoration: underline; }
a:focus-visible, button:focus-visible, summary:focus-visible, select:focus-visible,
[tabindex]:focus-visible { outline: 3px solid """ + WVU_BLUE + """; outline-offset: 2px; border-radius: 2px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
    overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.data-table-details { margin: 0.25rem 0 0.75rem; }
.data-table-details > summary { cursor: pointer; font-size: 0.9rem; font-weight: 600;
    color: """ + WVU_BLUE + """; padding: 0.35rem 0; }
.data-table-details > summary:hover { text-decoration: underline; }
.table-scroll { overflow-x: auto; }
table.data-table { border-collapse: collapse; width: 100%; font-size: 0.85rem; margin-top: 0.5rem; }
table.data-table caption { text-align: left; font-size: 0.85rem; color: """ + WVU_MUTED + """; padding-bottom: 0.35rem; }
table.data-table th, table.data-table td { border: 1px solid """ + WVU_BORDER + """; padding: 0.3rem 0.55rem; text-align: right; }
table.data-table thead th { background: """ + WVU_BLUE + """; color: #FFFFFF; }
table.data-table th[scope="row"] { text-align: left; }
@media (max-width: 768px) { .map-grid { grid-template-columns: 1fr; } body { padding: 1rem; } }
"""

# ── Rendering helpers (accessibility-first) ───────────────────────────────────


def _fig_json(fig):
    return json.loads(fig.to_json())


def _chart_div(div_id, aria_label):
    return (f'<div id="{div_id}" class="plotly-chart" role="img" '
            f'aria-label="{_html.escape(aria_label)}"></div>')


def _data_table_html(caption, columns, rows):
    head = "".join(f'<th scope="col">{_html.escape(str(c))}</th>' for c in columns)
    body = []
    for row in rows:
        cells = [f'<th scope="row">{_html.escape(str(row[0]))}</th>']
        cells += [f"<td>{_html.escape(str(v))}</td>" for v in row[1:]]
        body.append("<tr>" + "".join(cells) + "</tr>")
    cap = _html.escape(caption)
    return ('<details class="data-table-details">'
            f"<summary>Show data table — {cap}</summary>"
            f'<div class="table-scroll"><table class="data-table"><caption>{cap}</caption>'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div></details>")


def _source_html(key):
    name, url, freq = SOURCES[key]
    return f'<p class="source">Source: <a href="{url}">{_html.escape(name)}</a> — {freq}</p>'


def _figure_block(div_id, figcaption, aria_label, source_key, note, table_html):
    """A full accessible chart block: figure + caption + chart + table + source."""
    note_html = f'<p class="source"><em>{_html.escape(note)}</em></p>' if note else ""
    return (
        '<figure class="chart-figure">'
        f"<figcaption>{_html.escape(figcaption)}</figcaption>"
        f"{_chart_div(div_id, aria_label)}"
        f"{table_html}"
        f"{_source_html(source_key)}{note_html}"
        "</figure>"
    )


# ── Data tables for specific charts ───────────────────────────────────────────


def _fmt_or_dash(v, kind):
    if v is None or pd.isna(v):
        return "—"
    if kind == "usd":
        return f"${v:,.0f}"
    if kind == "usd2":
        return f"${v:,.2f}"
    if kind == "pct":
        return fmt_signed_pct(v)
    if kind == "count":
        return f"{v:,.0f}"
    return str(v)


def _statewide_table(summary):
    ordered = summary.sort_values("county_name")
    rows = []
    for _, r in ordered.iterrows():
        rows.append((
            f'{r["county_name"]} County',
            _fmt_or_dash(r.get("median_home_value"), "usd"),
            _fmt_or_dash(r.get("median_list_ppsf"), "usd2"),
            _fmt_or_dash(r.get("hpi_yoy_pct"), "pct"),
            _fmt_or_dash(r.get("permits_latest"), "count"),
        ))
    return _data_table_html(
        "West Virginia counties — median home value, median listing price per "
        "square foot, year-over-year home-price growth, and residential permits",
        ["County", "Median Value", "$/Sq Ft", "Home-Price Growth (YoY)",
         "Permits (Latest Yr)"],
        rows)


# ── Embed shell (standalone iframe pages) ─────────────────────────────────────

EMBED_JS_TEMPLATE = """
Object.keys(figureData).forEach(function(divId) {
    var fig = figureData[divId];
    if (document.getElementById(divId)) {
        Plotly.newPlot(divId, fig.data, fig.layout, {responsive: true, displayModeBar: false});
    }
});
(function() {
  var lastHeight = 0, timer;
  function postHeight() {
    clearTimeout(timer);
    timer = setTimeout(function() {
      var h = document.documentElement.scrollHeight;
      if (h === lastHeight) return;
      lastHeight = h;
      window.parent.postMessage({type: 'wvre-resize', height: h}, '*');
    }, 100);
  }
  window.addEventListener('load', postHeight);
  window.addEventListener('resize', postHeight);
  setTimeout(postHeight, 800);
  document.querySelectorAll('.plotly-chart').forEach(function(el) {
    el.on && el.on('plotly_afterplot', postHeight);
  });
})();
"""


def _embed_page(title, body_html, figures):
    return "\n".join([
        "<!DOCTYPE html>", '<html lang="en">', "<head>", '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"<title>{_html.escape(title)}</title>",
        f'<script src="{PLOTLY_CDN}"></script>',
        "<style>", BASE_CSS, A11Y_CSS, "body{max-width:none;padding:0.75rem;}", "</style>",
        "</head>", "<body>", "<main>",
        f'<h1 class="sr-only">{_html.escape(title)}</h1>',
        body_html, "</main>", "<script>",
        f"var figureData = {json.dumps(figures)};", EMBED_JS_TEMPLATE,
        "</script>", "</body>", "</html>",
    ])


# ── Per-county detail embed ───────────────────────────────────────────────────


def build_county_embed(data, fips, summary_row):
    """Build one county's detail embed page. Returns (filename, html)."""
    name = COUNTIES[fips]
    figures = {}
    blocks = [build_kpi_card_html(summary_row, color=WVU_BLUE, heading_level=2)]

    # Price trends: FHFA HPI (annual) + Realtor.com list price (monthly).
    hpi_fig = build_hpi_trend(fhfa_series(data, fips), name)
    if hpi_fig is not None:
        did = "hpi-trend"
        figures[did] = _fig_json(hpi_fig)
        fdf = fhfa_series(data, fips).dropna(subset=["hpi_2000base"])
        tbl = _data_table_html(
            f"{name} County — FHFA House Price Index by year (2000 = 100)",
            ["Year", "HPI (2000=100)", "Annual Change"],
            [(int(r.year), f'{r.hpi_2000base:.1f}', _fmt_or_dash(r.annual_change_pct, "pct"))
             for r in fdf.itertuples()])
        blocks.append(_figure_block(
            did, "House Price Index (FHFA)",
            f"Line chart of the FHFA House Price Index for {name} County by year.",
            "fhfa", TRENDS_NOTE, tbl))

    price = realtor_series(data, fips, "median_list_price")
    lp_fig = build_list_price_trend(price, name)
    if lp_fig is not None:
        did = "listprice-trend"
        figures[did] = _fig_json(lp_fig)
        pdf = price.dropna()
        tbl = _data_table_html(
            f"{name} County — monthly median listing price",
            ["Month", "Median List Price"],
            [(d.strftime("%Y-%m"), f"${v:,.0f}") for d, v in pdf.items()])
        blocks.append(_figure_block(
            did, "Median Listing Price (monthly)",
            f"Line chart of the monthly median listing price for {name} County "
            f"with an STL trend and short projection.",
            "realtor", None, tbl))

    # Permit history.
    perm = permit_series(data, fips)
    ph_fig = build_permit_history(perm, name)
    if ph_fig is not None:
        did = "permit-history"
        figures[did] = _fig_json(ph_fig)
        tbl = _data_table_html(
            f"{name} County — residential units authorized by year",
            ["Year", "Single-family", "Multifamily", "Total"],
            [(int(r.year), f"{int(r.units_1u):,}", f"{int(r.units_multifamily):,}",
              f"{int(r.units_total):,}") for r in perm.itertuples()])
        blocks.append(_figure_block(
            did, "Residential Building Permits by Year",
            f"Stacked bar chart of residential units authorized in {name} County "
            f"by year, split single-family and multifamily.",
            "bps", PERMITS_NOTE, tbl))

    # Affordability (FMR) — only if HUD data present.
    fmr_row = data.fmr[data.fmr["fips"] == fips]
    acs_row = data.acs[data.acs["fips"] == fips]
    aff_fig = build_affordability(
        fmr_row.iloc[0] if not fmr_row.empty else None,
        acs_row.iloc[0] if not acs_row.empty else None, name)
    if aff_fig is not None:
        did = "affordability"
        figures[did] = _fig_json(aff_fig)
        fr = fmr_row.iloc[0]
        tbl = _data_table_html(
            f"{name} County — Fair Market Rents by bedroom count",
            ["Bedrooms", "Fair Market Rent"],
            [("Studio", _fmt_or_dash(fr.get("fmr_0br"), "usd")),
             ("1 BR", _fmt_or_dash(fr.get("fmr_1br"), "usd")),
             ("2 BR", _fmt_or_dash(fr.get("fmr_2br"), "usd")),
             ("3 BR", _fmt_or_dash(fr.get("fmr_3br"), "usd")),
             ("4 BR", _fmt_or_dash(fr.get("fmr_4br"), "usd"))])
        blocks.append(_figure_block(
            did, "Fair Market Rents",
            f"Bar chart of HUD Fair Market Rents by bedroom count for {name} County.",
            "hud", AFFORDABILITY_NOTE, tbl))

    if len(blocks) == 1:  # KPI card only — note the data gap honestly.
        blocks.append(
            '<p class="source"><em>No time-series data is currently published '
            f'for {_html.escape(name)} County across the available free sources '
            "(FHFA, Realtor.com, and building permits). This county appears on the "
            "statewide maps and table where data exists.</em></p>")

    body = f'<h2 class="sr-only">{_html.escape(name)} County detail</h2>' + "".join(blocks)
    return f"{fips}.html", _embed_page(f"{name} County — WV Real Estate", body, figures)


# ── Statewide map embeds ──────────────────────────────────────────────────────


def _map_embeds(summary, geojson):
    """Each statewide map as its own embeddable page. Returns {filename: html}."""
    specs = [
        ("map-home-value", "home_value_map", home_value_map, "acs",
         "median_home_value", "Choropleth of median home value by West Virginia county."),
        ("map-price-per-sqft", "ppsf_map", ppsf_map, "realtor",
         "median_list_ppsf", "Choropleth of median listing price per square foot by county."),
        ("map-price-growth", "hpi_yoy_map", hpi_yoy_map, "fhfa",
         "hpi_yoy_pct", "Choropleth of year-over-year home-price growth by county."),
        ("map-permits", "permits_map", permits_map, "bps",
         "permits_latest", "Choropleth of residential permits by county, latest year."),
    ]
    out = {}
    for fname, methkey, builder, src, col, aria in specs:
        fig = builder(summary, geojson)
        did = fname
        tbl = _map_table_for(summary, col)
        body = _figure_block(did, fig.layout.title.text, aria, src,
                             MAP_METHODOLOGY[methkey], tbl)
        out[f"{fname}.html"] = _embed_page(
            f"{fig.layout.title.text} — WV", body, {did: _fig_json(fig)})
    return out


def _map_table_for(summary, col):
    kind = {"median_home_value": "usd", "median_list_ppsf": "usd2",
            "hpi_yoy_pct": "pct", "permits_latest": "count"}[col]
    ordered = summary.sort_values("county_name")
    rows = [(f'{r["county_name"]} County', _fmt_or_dash(r.get(col), kind))
            for _, r in ordered.iterrows()]
    return _data_table_html("County values", ["County", "Value"], rows)


# ── Main dashboard page ───────────────────────────────────────────────────────

MAIN_JS_TEMPLATE = """
Object.keys(figureData).forEach(function(divId) {
    var fig = figureData[divId];
    if (document.getElementById(divId)) {
        Plotly.newPlot(divId, fig.data, fig.layout, {responsive: true, displayModeBar: false});
    }
});
function loadCounty(fips) {
    var frame = document.getElementById('county-frame');
    var name = document.querySelector('#county-select option[value="' + fips + '"]').textContent;
    frame.src = 'embeds/' + fips + '.html';
    frame.title = name + ' County real estate detail';
}
window.addEventListener('message', function(e) {
    if (e.data && e.data.type === 'wvre-resize') {
        var frame = document.getElementById('county-frame');
        if (frame) frame.style.height = (e.data.height + 20) + 'px';
    }
});
"""


def build_index(data, summary, geojson, default_fips):
    figures = {}

    # Statewide maps grid.
    map_specs = [
        (home_value_map, "home_value_map", "acs", "median_home_value", "map-home-value",
         "Choropleth of median home value by West Virginia county."),
        (ppsf_map, "ppsf_map", "realtor", "median_list_ppsf", "map-ppsf",
         "Choropleth of median listing price per square foot by county."),
        (hpi_yoy_map, "hpi_yoy_map", "fhfa", "hpi_yoy_pct", "map-growth",
         "Choropleth of year-over-year home-price growth by county."),
        (permits_map, "permits_map", "bps", "permits_latest", "map-permits",
         "Choropleth of residential permits by county, latest year."),
    ]
    map_blocks = []
    for builder, methkey, src, col, did, aria in map_specs:
        fig = builder(summary, geojson)
        figures[did] = _fig_json(fig)
        tbl = _map_table_for(summary, col)
        map_blocks.append(_figure_block(did, fig.layout.title.text, aria, src,
                                        MAP_METHODOLOGY[methkey], tbl))

    # Permit distribution.
    dist_fig = build_permit_distribution(data.permits)
    dist_block = ""
    if dist_fig is not None:
        figures["permit-dist"] = _fig_json(dist_fig)
        year = int(data.permits["year"].max())
        dd = data.permits[data.permits["year"] == year].sort_values(
            "units_total", ascending=False)
        tbl = _data_table_html(
            f"Residential units authorized by county, {year}",
            ["County", "Units Authorized"],
            [(f'{r.county_name} County', f"{int(r.units_total):,}")
             for r in dd.itertuples()])
        dist_block = _figure_block(
            "permit-dist", dist_fig.layout.title.text,
            "Ranked bar chart of residential units authorized by county in the "
            "latest year.", "bps", PERMITS_NOTE, tbl)

    # County selector options.
    options = "\n".join(
        f'<option value="{fips}"{" selected" if fips == default_fips else ""}>'
        f"{_html.escape(name)}</option>"
        for fips, name in COUNTIES.items())

    build_ts = datetime.now(timezone.utc).strftime("%B %d, %Y")
    covered_hpi = int(summary["hpi_yoy_pct"].notna().sum()) if "hpi_yoy_pct" in summary else 0
    covered_psf = int(summary["median_list_ppsf"].notna().sum()) if "median_list_ppsf" in summary else 0

    body = f"""
<header>
  <h1 class="main-title">West Virginia Regional Real Estate Report</h1>
  <p class="main-subtitle">Residential housing indicators for all 55 counties — home
  prices, price per square foot, new construction, and affordability.</p>
  <span class="data-badge">Updated {build_ts} · public data, automatically refreshed</span>
</header>

<section aria-labelledby="maps-h">
  <h2 id="maps-h">West Virginia at a Glance</h2>
  <p>Hover any county for its value. Home-price growth (FHFA) covers
  {covered_hpi} of 55 counties and listing price per square foot (Realtor.com)
  covers {covered_psf}; counties without a published figure appear uncolored.
  Every number is in the data table beneath each map.</p>
  <div class="map-grid">
    {''.join(map_blocks)}
  </div>
</section>

<section aria-labelledby="permits-h">
  <h2 id="permits-h">Residential Construction</h2>
  {dist_block}
</section>

<section aria-labelledby="county-h">
  <h2 id="county-h">Explore a County</h2>
  <div class="selector-row">
    <label for="county-select">Choose a county:</label>
    <select id="county-select" onchange="loadCounty(this.value)">
      {options}
    </select>
  </div>
  <iframe id="county-frame" class="county-frame" title="{_html.escape(COUNTIES[default_fips])} County real estate detail"
          src="embeds/{default_fips}.html" loading="lazy"></iframe>
</section>

<section aria-labelledby="table-h">
  <h2 id="table-h">All Counties — Data Table</h2>
  <p>The full county cross-section. Cells show "—" where a source has no
  published value for that county.</p>
  {_statewide_table(summary)}
</section>

<footer class="footer">
  <p>Built from public data: FHFA House Price Index, U.S. Census Bureau (American
  Community Survey and Building Permits Survey), Realtor.com via FRED, and HUD
  Fair Market Rents. This report is residential only — free county-level
  commercial real estate data is not publicly available. County boundaries: U.S.
  Census / plotly. Not affiliated with or endorsed by any listed source.</p>
  <p>Modeled on the Upper Peninsula Regional Economic Report. Built for West
  Virginia University. Accessibility target: WCAG 2.1 AA.</p>
</footer>
"""

    return "\n".join([
        "<!DOCTYPE html>", '<html lang="en">', "<head>", '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "<title>West Virginia Regional Real Estate Report</title>",
        f'<script src="{PLOTLY_CDN}"></script>',
        "<style>", BASE_CSS, A11Y_CSS, "</style>", "</head>", "<body>",
        body, "<script>", f"var figureData = {json.dumps(figures)};",
        MAIN_JS_TEMPLATE, "</script>", "</body>", "</html>",
    ])


# ── Orchestration ─────────────────────────────────────────────────────────────


def main():
    print("Loading data …")
    data = load_data()
    summary = latest_summary(data)
    geojson = data.geojson
    if geojson is None:
        raise SystemExit("Could not load county geometry — aborting build.")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()

    # Default county for the selector: the one with the most recent permits.
    default_fips = (summary.sort_values("permits_latest", ascending=False)
                    .iloc[0]["fips"] if "permits_latest" in summary else
                    list(COUNTIES)[0])

    print("Writing per-county embeds …")
    for fips in COUNTIES:
        row = summary[summary["fips"] == fips].iloc[0]
        fname, html_doc = build_county_embed(data, fips, row)
        (EMBED_DIR / fname).write_text(html_doc)

    print("Writing statewide map embeds …")
    for fname, html_doc in _map_embeds(summary, geojson).items():
        (EMBED_DIR / fname).write_text(html_doc)

    print("Writing index.html …")
    (DOCS_DIR / "index.html").write_text(build_index(data, summary, geojson, default_fips))

    n_pages = len(list(EMBED_DIR.glob("*.html"))) + 1
    print(f"Done. {n_pages} pages written to {DOCS_DIR}")


if __name__ == "__main__":
    main()
