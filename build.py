#!/usr/bin/env python3
"""
Build the static West Virginia Real Estate Report for GitHub Pages.

Reuses the data pipeline (data/clean.py) and the flat county projection
(data/geo.py) to write a self-contained, dependency-free docs/ site:

    docs/index.html            the full report — navy masthead + strip plot, a
                               switchable Atlas choropleth with a county profile,
                               a 2x2 county-trends grid, the construction section,
                               a sortable all-counties table, and the footer
    docs/embeds/<fips>.html    one standalone per-county detail page (KPIs + the
                               four trend charts), embeddable in an iframe
    docs/embeds/map-*.html     each statewide measure as a standalone map page

The whole site is inline SVG + vanilla JS driven by ONE JSON payload (`D`) — no
charting library, no CDN. Presentation markup, CSS and interaction logic live in
assets/report_body.html, assets/report.css and assets/report.js (copied from the
design reference); this module emits the design tokens (from data/constants.py),
builds the payload, and stitches the pages together. The Streamlit app (app.py)
and the Plotly builders in components/* are unaffected and keep using Plotly.

Every chart is exposed to assistive tech as a single role="img" node with a
concise aria-label and is paired with a collapsible data table (the WCAG 1.1.1
text alternative). The site targets WCAG 2.1 AA (WVU / ADA Title II).

Usage:
    python build.py                  # fetch fresh (CI); REPORT_OFFLINE=1 for cache
"""
from __future__ import annotations

import html as _html
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data.clean import (
    fhfa_series, latest_summary, load_data, permit_series, realtor_series,
)
from data.constants import (
    COUNTIES, CSS_TOKENS_DARK, CSS_TOKENS_LIGHT, GOOGLE_FONTS_IMPORT, SOURCES,
)
from data.geo import project_counties

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "docs"
EMBED_DIR = DOCS_DIR / "embeds"
ASSETS_DIR = ROOT / "assets"

# Presentation assets (verbatim from the design reference); read once.
REPORT_CSS = (ASSETS_DIR / "report.css").read_text()
REPORT_BODY = (ASSETS_DIR / "report_body.html").read_text()
REPORT_JS = (ASSETS_DIR / "report.js").read_text()


# ── Design-token CSS (single source of truth: data/constants.py) ──────────────

def _token_css() -> str:
    """The :root light block, the dark @media block, and the [data-theme] overrides."""
    return (
        ":root {\n" + CSS_TOKENS_LIGHT + "\n}\n"
        "@media (prefers-color-scheme: dark) {\n"
        '  :root:not([data-theme="light"]) {\n' + CSS_TOKENS_DARK + "\n  }\n}\n"
        ':root[data-theme="dark"] {\n' + CSS_TOKENS_DARK + "\n}\n"
    )


def _head(title: str, extra_css: str = "") -> list[str]:
    return [
        "<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_html.escape(title)}</title>",
        GOOGLE_FONTS_IMPORT,
        "<style>", _token_css(), REPORT_CSS, extra_css, "</style>",
        "</head>",
    ]


# ── Payload ───────────────────────────────────────────────────────────────────

def _num(v):
    """A JSON-safe float, or None for missing values (never fabricated)."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return float(v)


def _int(v):
    n = _num(v)
    return None if n is None else int(round(n))


def build_payload(data, summary, proj) -> dict:
    """One JSON blob (`D`) that drives every page. Missing metrics stay null."""
    counties = []
    for fips, name in COUNTIES.items():
        row = summary[summary["fips"] == fips].iloc[0]

        perm = permit_series(data, fips)
        perm_rows = ([[int(r.year), int(r.units_1u), int(r.units_multifamily)]
                      for r in perm.itertuples()] if not perm.empty else [])
        psf = int(perm.iloc[-1].units_1u) if not perm.empty else None

        fh = fhfa_series(data, fips)
        hpi_rows = ([[int(r.year), round(float(r.hpi_2000base), 1)]
                     for r in fh.dropna(subset=["hpi_2000base"]).itertuples()]
                    if not fh.empty else [])

        lp = realtor_series(data, fips, "median_list_price")
        lps_rows = [[d.strftime("%Y-%m"), float(v)] for d, v in lp.items()
                    if pd.notna(v)]

        fmr_row = data.fmr[data.fmr["fips"] == fips]
        if not fmr_row.empty:
            fr = fmr_row.iloc[0]
            fmr = [_num(fr.get(f"fmr_{b}br")) for b in ("0", "1", "2", "3", "4")]
        else:
            fmr = []

        counties.append({
            "f": fips, "n": name, "c": proj["centroids"].get(fips, [0, 0]),
            "hv": _num(row.get("median_home_value")),
            "ppsf": _num(row.get("median_list_ppsf")),
            "g": _num(row.get("hpi_yoy_pct")),
            "pt": _int(row.get("permits_latest")),
            "psf": psf,
            "rent": _num(row.get("median_gross_rent")),
            "own": _num(row.get("ownership_rate")),
            "vac": _num(row.get("vacancy_rate")),
            "built": _int(row.get("median_year_built")),
            "dom": _num(row.get("median_days_on_market")),
            "hpi": hpi_rows, "lps": lps_rows, "perm": perm_rows, "fmr": fmr,
        })

    acs_year = (int(data.acs["acs_year"].dropna().iloc[0])
                if not data.acs.empty and data.acs["acs_year"].notna().any() else "")
    fmr_year = (int(data.fmr["fmr_year"].dropna().max())
                if not data.fmr.empty and data.fmr["fmr_year"].notna().any() else "")

    return {
        "W": proj["W"], "H": proj["H"], "paths": proj["paths"],
        "acsYear": acs_year, "fmrYear": fmr_year, "counties": counties,
    }


# ── Main report page ──────────────────────────────────────────────────────────

def build_index(payload: dict) -> str:
    build_ts = datetime.now(timezone.utc).strftime("%B %d, %Y")
    body_html = REPORT_BODY.replace("Updated September 10, 2026", f"Updated {build_ts}")
    body = body_html + (
        "<script>\n"
        f"const D = {json.dumps(payload)};\n"
        + REPORT_JS +
        "\n</script>"
    )
    return "\n".join(_head("West Virginia Real Estate Report")
                     + ["<body>", body, "</body>", "</html>"])


# ── Per-county detail embeds (standalone, same tokens, no library) ────────────

# Self-contained charting for the embed pages: the helper + chart primitives are
# copied from assets/report.js (deliberate small duplication so index.html stays
# byte-faithful to the reference and an embed can never break the main page).
EMBED_JS = r"""
const $ = id => document.getElementById(id);
const money = v => v == null ? '—' : '$' + Math.round(v).toLocaleString('en-US');
const kMoney = v => '$' + (v >= 1000 ? Math.round(v / 1000) + 'k' : v);
const pct = v => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1) + '%';
const int = v => v == null ? '—' : Math.round(v).toLocaleString('en-US');
const esc = s => String(s).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const ym = s => MON[+s.slice(5) - 1] + ' ' + s.slice(0, 4);

function niceTicks(lo, hi, n) {
  const span = hi - lo, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(s => s * mag).find(s => span / s <= n) || 10 * mag;
  const t = [], end = Math.ceil(hi / step - 1e-9) * step; for (let v = Math.floor(lo / step + 1e-9) * step; v <= end + 1e-9; v += step) t.push(+v.toFixed(6));
  return t;
}
function frame(el, h) { const w = Math.max(el.clientWidth, 260); return { w, h, svg: s => `<svg viewBox="0 0 ${w} ${h}" height="${h}">${s}</svg>` }; }
function table(id, head, rows) {
  $(id).innerHTML = `<details class="dt"><summary>Data table</summary><div class="tscroll"><table><thead><tr>${head.map(h => `<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(v => `<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
}
function empty(el, msg) { el.innerHTML = `<div class="empty">${msg}</div>`; }
function lineChart(el, pts, { yFmt, xTicks, xLab, base, endFmt }) {
  const F = frame(el, 230), L = 48, R = 14, T = 16, B = 26;
  const ys = pts.map(p => p[1]), lo0 = Math.min(...ys, base ?? Infinity), hi0 = Math.max(...ys, base ?? -Infinity);
  const yt = niceTicks(lo0, hi0 + (hi0 - lo0) * .06, 4);
  const y0 = yt[0], y1 = yt[yt.length - 1], x0 = pts[0][0], x1 = pts[pts.length - 1][0];
  const X = v => L + (v - x0) / (x1 - x0) * (F.w - L - R), Y = v => T + (1 - (v - y0) / (y1 - y0)) * (F.h - T - B);
  let s = yt.map(v => `<line class="grid" x1="${L}" x2="${F.w - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${yFmt(v)}</text>`).join('');
  s += xTicks.map(v => `<text x="${X(v)}" y="${F.h - 6}" text-anchor="middle">${xLab(v)}</text>`).join('');
  if (base != null) s += `<line class="base" x1="${L}" x2="${F.w - R}" y1="${Y(base)}" y2="${Y(base)}"/>`;
  const d = pts.map((p, i) => (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1)).join('');
  s += `<path class="ar" d="${d}L${X(x1)},${Y(y0)}L${X(x0)},${Y(y0)}Z"/><path class="ln" d="${d}"/>`;
  const e = pts[pts.length - 1];
  s += `<circle class="dot" cx="${X(e[0])}" cy="${Y(e[1])}" r="4.5"/><text class="lab" x="${X(e[0]) - 8}" y="${Y(e[1]) - 10}" text-anchor="end">${endFmt(e[1])}</text>`;
  el.innerHTML = F.svg(s);
}

function kpi(c) {
  const lpLast = c.lps.length ? c.lps[c.lps.length - 1][0] : null;
  const g = c.g == null ? '<span class="dash">—</span>' : `<span class="${c.g >= 0 ? 'up' : 'down'}">${c.g >= 0 ? '▲' : '▼'} ${pct(c.g)}</span>`;
  const kp = [
    ['Median home value', money(c.hv), `ACS ${M.acsYear}`],
    ['Price per sq ft', c.ppsf == null ? '<span class="dash">—</span>' : '$' + Math.round(c.ppsf), c.ppsf == null ? 'not published' : (lpLast ? ym(lpLast) : '')],
    ['Price growth', g, 'FHFA 2023'],
    ['Median gross rent', money(c.rent), `ACS ${M.acsYear}`],
    ['Owner-occupied', c.own == null ? '—' : c.own.toFixed(1) + '%', 'of occupied homes'],
    ['Units authorized', c.pt == null ? '<span class="dash">—</span>' : int(c.pt), c.pt == null ? 'no 2025 report' : '2025 permits'],
    ['Vacancy rate', c.vac == null ? '—' : c.vac.toFixed(1) + '%', 'of all units'],
    ['Median year built', c.built == null ? '—' : c.built, 'housing stock'],
    ['Days on market', c.dom == null ? '<span class="dash">—</span>' : int(c.dom), c.dom == null ? 'not published' : (lpLast ? ym(lpLast) : '')],
  ];
  $('kpis').innerHTML = kp.map(([l, v, s]) => `<div><dt>${l}</dt><dd>${v}<small>${s}</small></dd></div>`).join('');
}

function chartsFor(c) {
  const lpLast = c.lps.length ? c.lps[c.lps.length - 1][0] : null;
  // HPI
  const eh = $('c-hpi');
  if (c.hpi.length > 2) {
    const first = c.hpi[0][0], last = c.hpi[c.hpi.length - 1][0];
    const xt = []; for (let y = Math.ceil(first / 5) * 5; y <= last; y += 5) xt.push(y);
    lineChart(eh, c.hpi, { yFmt: v => v, xTicks: xt, xLab: v => v, base: 100, endFmt: v => `${last}: ${v.toFixed(0)}` });
    eh.setAttribute('aria-label', `Line chart: ${c.n} County house price index rose from 100 in 2000 to ${c.hpi[c.hpi.length - 1][1].toFixed(0)} in ${last}.`);
    table('d-hpi', ['Year', 'Index (2000 = 100)'], c.hpi.slice().reverse().map(r => [r[0], r[1].toFixed(1)]));
  } else { empty(eh, `FHFA does not publish a county index for ${esc(c.n)} County.`); eh.setAttribute('aria-label', 'No data'); $('d-hpi').innerHTML = ''; }
  // Listing price
  const el = $('c-lp');
  if (c.lps.length) {
    const pts = c.lps.filter(p => p[1] != null).map(p => [+p[0].slice(0, 4) + (+p[0].slice(5) - 1) / 12, p[1]]);
    const xt = []; for (let y = Math.ceil(pts[0][0]); y <= pts[pts.length - 1][0]; y += (el.clientWidth < 420 ? 3 : 2)) xt.push(y);
    lineChart(el, pts, { yFmt: kMoney, xTicks: xt, xLab: v => v, endFmt: v => `${ym(lpLast)}: ${money(v)}` });
    el.setAttribute('aria-label', `Line chart: ${c.n} County median listing price by month, latest ${money(pts[pts.length - 1][1])}.`);
    table('d-lp', ['Month', 'Median listing price'], c.lps.slice().reverse().map(r => [ym(r[0]), money(r[1])]));
  } else { empty(el, `Realtor.com publishes no listing series for ${esc(c.n)} County. Coverage is limited to the 12 counties with the most listings.`); el.setAttribute('aria-label', 'No data'); $('d-lp').innerHTML = ''; }
  // Permits
  const ep = $('c-perm'), P = c.perm;
  if (P.length) {
    const F = frame(ep, 230), L = 44, R = 8, T = 14, B = 26, mx = Math.max(...P.map(r => r[1] + r[2]), 4);
    const yt = niceTicks(0, mx * 1.05, 4), y1 = yt[yt.length - 1], n = P.length, bw = (F.w - L - R) / n;
    const X = i => L + i * bw, Y = v => T + (1 - v / y1) * (F.h - T - B);
    let s = yt.map(v => `<line class="grid" x1="${L}" x2="${F.w - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${int(v)}</text>`).join('');
    P.forEach((r, i) => {
      const g = Math.max(bw * .22, 1), x = X(i) + g / 2, w = bw - g;
      s += `<rect class="sf" x="${x}" width="${w}" y="${Y(r[1])}" height="${Y(0) - Y(r[1])}"/>`;
      if (r[2]) s += `<rect class="mf" x="${x}" width="${w}" y="${Y(r[1] + r[2])}" height="${Y(r[1]) - Y(r[1] + r[2])}"/>`;
      if (r[0] % 5 === 0) s += `<text x="${X(i) + bw / 2}" y="${F.h - 6}" text-anchor="middle">${r[0]}</text>`;
    });
    ep.innerHTML = F.svg(s);
    ep.setAttribute('aria-label', `Stacked bar chart of residential units authorized in ${c.n} County, ${P[0][0]} to ${P[n - 1][0]}.`);
    table('d-perm', ['Year', 'Single-family', 'Multifamily', 'Total'], P.slice().reverse().map(r => [r[0], int(r[1]), int(r[2]), int(r[1] + r[2])]));
  } else { empty(ep, `No building-permit series for ${esc(c.n)} County.`); ep.setAttribute('aria-label', 'No data'); $('d-perm').innerHTML = ''; }
  // FMR
  const ef = $('c-fmr');
  if (c.fmr.length) {
    const F = frame(ef, 230), L = 44, R = 8, T = 22, B = 26, labs = ['Studio', '1 BR', '2 BR', '3 BR', '4 BR'];
    const mx = Math.max(...c.fmr, c.rent || 0), yt = niceTicks(0, mx * 1.12, 4), y1 = yt[yt.length - 1], bw = (F.w - L - R) / 5;
    const Y = v => T + (1 - v / y1) * (F.h - T - B);
    let s = yt.map(v => `<line class="grid" x1="${L}" x2="${F.w - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${kMoney(v).replace(/^\$0k$/, '$0')}</text>`).join('');
    c.fmr.forEach((v, i) => {
      const x = L + i * bw + bw * .16, w = bw * .68;
      s += `<rect class="bar" x="${x}" width="${w}" y="${Y(v)}" height="${Y(0) - Y(v)}"/><text class="inlab" x="${x + w / 2}" y="${Y(v) + 16}" text-anchor="middle">${money(v)}</text>`;
      s += `<text x="${x + w / 2}" y="${F.h - 6}" text-anchor="middle">${labs[i]}</text>`;
    });
    if (c.rent) s += `<line class="rent" x1="${L}" x2="${F.w - R}" y1="${Y(c.rent)}" y2="${Y(c.rent)}"/><text class="rentlab" x="${L + 4}" y="${Y(c.rent) - 6}">ACS median ${money(c.rent)}</text>`;
    ef.innerHTML = F.svg(s);
    ef.setAttribute('aria-label', `Bar chart of HUD Fair Market Rents in ${c.n} County: ${c.fmr.map((v, i) => labs[i] + ' ' + money(v)).join(', ')}.`);
    table('d-fmr', ['Unit', 'Fair Market Rent'], c.fmr.map((v, i) => [labs[i], money(v)]).concat([['ACS median gross rent', money(c.rent)]]));
  } else { empty(ef, `No HUD Fair Market Rents for ${esc(c.n)} County.`); ef.setAttribute('aria-label', 'No data'); $('d-fmr').innerHTML = ''; }
}

kpi(EC); chartsFor(EC);
let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(() => chartsFor(EC), 120); }).observe(document.body);
"""

_TREND_FIGURES = """
<div class="charts">
  <figure class="chart"><figcaption><b>House price index</b><span>Repeat-sales index, 2000 = 100. Tracks change, not dollar level.</span></figcaption>
    <div class="plot" id="c-hpi" role="img"></div><div id="d-hpi"></div>
    <p class="src">Source: <a href="https://www.fhfa.gov/data/hpi">FHFA House Price Index</a>, annual</p></figure>
  <figure class="chart"><figcaption><b>Median listing price</b><span>Monthly asking price, Realtor.com. Published for 12 larger counties.</span></figcaption>
    <div class="plot" id="c-lp" role="img"></div><div id="d-lp"></div>
    <p class="src">Source: <a href="https://fred.stlouisfed.org">Realtor.com via FRED</a>, monthly</p></figure>
  <figure class="chart"><figcaption><b>Homes authorized by permit</b><span>New residential units per year, single-family vs. multifamily.</span></figcaption>
    <div class="plot" id="c-perm" role="img"></div>
    <div class="key"><span><i style="background:var(--sf)"></i>Single-family</span><span><i style="background:var(--mf)"></i>Multifamily (2+ units)</span></div>
    <div id="d-perm"></div>
    <p class="src">Source: <a href="https://www.census.gov/construction/bps">Census Building Permits Survey</a>. Authorized, not necessarily built.</p></figure>
  <figure class="chart"><figcaption><b>Fair Market Rent by bedroom</b><span>HUD benchmark (about the 40th percentile of local rents), FY{fmrY}.</span></figcaption>
    <div class="plot" id="c-fmr" role="img"></div><div id="d-fmr"></div>
    <p class="src">Source: <a href="https://www.huduser.gov/portal/datasets/fmr.html">HUD Fair Market Rents</a>. Dashed line: ACS median gross rent.</p></figure>
</div>
"""


def build_county_embed(payload: dict, county: dict) -> tuple[str, str]:
    """One standalone per-county detail page. Returns (filename, html)."""
    name, fips = county["n"], county["f"]
    body = (
        '<main class="wrap embed">'
        f'<h1 class="sr-only">{_html.escape(name)} County real estate detail</h1>'
        '<div class="sec-head" style="margin-top:1.4rem">'
        '<p class="eyebrow">County trends</p>'
        f'<h2>{_html.escape(name)} County</h2>'
        f'<p class="mono" style="color:var(--muted)">FIPS {fips}</p></div>'
        '<dl class="kpis" id="kpis" style="margin-bottom:1.8rem"></dl>'
        + _TREND_FIGURES.replace("{fmrY}", str(payload["fmrYear"]))
        + "</main>"
        "<script>\n"
        f"const EC = {json.dumps(county)};\n"
        f'const M = {{acsYear: {json.dumps(payload["acsYear"])}, fmrYear: {json.dumps(payload["fmrYear"])}}};\n'
        + EMBED_JS +
        "\n</script>"
    )
    extra = ".embed{max-width:1000px;} .kpis{border-top:1px solid var(--rule);}"
    html_doc = "\n".join(
        _head(f"{name} County — WV Real Estate", extra)
        + ["<body>", body, "</body>", "</html>"])
    return f"{fips}.html", html_doc


# ── Statewide map embeds (static, server-rendered SVG) ────────────────────────

def _money(v):  return "—" if v is None else "$" + f"{round(v):,}"
def _dollar(v): return "—" if v is None else "$" + str(round(v))
def _pct(v):    return "—" if v is None else ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.1f}%"
def _units(v):  return "—" if v is None else f"{round(v):,} units"
def _kmoney(v): return "$" + (f"{round(v / 1000)}k" if v >= 1000 else str(v))


# Measure specs mirror the METRICS block in assets/report.js — same fixed class
# breaks, ramps and coverage columns — so the map embeds match the main Atlas.
MAP_METRICS = {
    "hv":   dict(col="median_home_value", title="Median home value", ramp="s",
                 breaks=[100000, 125000, 150000, 175000, 225000, 275000],
                 fmt=_money, blab=_kmoney, src="acs",
                 note="Median value of owner-occupied homes, Census ACS 5-year estimates."),
    "ppsf": dict(col="median_list_ppsf", title="Median listing price per square foot", ramp="s",
                 breaks=[115, 125, 135, 150, 170, 190],
                 fmt=_dollar, blab=lambda v: "$" + str(v), src="realtor",
                 note="Realtor.com median asking price per square foot. Published only for the 12 counties with enough listings."),
    "g":    dict(col="hpi_yoy_pct", title="Home-price growth, 2022 to 2023", ramp="g",
                 breaks=[0, 3, 6, 10, 15, 20],
                 fmt=_pct, blab=lambda v: ("+" if v > 0 else "") + str(v) + "%", src="fhfa",
                 note="One-year change in the FHFA all-transactions index, latest published year. Small counties swing widely year to year."),
    "pt":   dict(col="permits_latest", title="Residential units authorized, 2025", ramp="s",
                 breaks=[10, 25, 50, 100, 250, 1000],
                 fmt=_units, blab=lambda v: f"{round(v):,}", src="bps",
                 note="New privately owned housing units authorized by building permit in 2025. Authorized, not necessarily started."),
}
_MAP_FILES = {"hv": "map-home-value", "ppsf": "map-price-per-sqft",
              "g": "map-price-growth", "pt": "map-permits"}


def _bin(v, breaks):
    i = 0
    while i < len(breaks) and v >= breaks[i]:
        i += 1
    return i


def _legend_html(spec) -> str:
    b, ramp = spec["breaks"], spec["ramp"]
    labels = ", ".join(spec["blab"](v) for v in b)
    swatches = "".join(f'<i style="background:var(--{ramp}{i})"></i>' for i in range(7))
    edges = "".join(
        f'<span class="edge" style="left:{(i + 1) / 7 * 100:.4f}%"></span>'
        f'<small style="left:{(i + 1) / 7 * 100:.4f}%">{_html.escape(spec["blab"](v))}</small>'
        for i, v in enumerate(b))
    return (
        f'<div class="legend"><div class="ramp" role="img" '
        f'aria-label="Legend: seven bands with breaks at {_html.escape(labels)}">'
        f"{swatches}{edges}</div>"
        f'<div class="na-key"><i></i><small>No data</small></div></div>')


def _map_embed(payload: dict, summary: pd.DataFrame, key: str) -> tuple[str, str]:
    spec = MAP_METRICS[key]
    by_val = {r["fips"]: (None if pd.isna(r.get(spec["col"])) else float(r[spec["col"]]))
              for _, r in summary.iterrows()}
    names = dict(COUNTIES)

    paths = []
    for fips, d in payload["paths"].items():
        v = by_val.get(fips)
        if v is None:
            cls, style = "cty na", ""
        else:
            cls, style = "cty", f'style="fill:var(--{spec["ramp"]}{_bin(v, spec["breaks"])})"'
        paths.append(f'<path class="{cls}" {style} d="{d}">'
                     f'<title>{_html.escape(names.get(fips, fips))} County</title></path>')

    have = sum(1 for v in by_val.values() if v is not None)
    W, H = payload["W"], payload["H"]
    svg = (f'<svg id="map" role="img" viewBox="-6 -6 {W + 12} {H + 12}" '
           f'aria-label="Choropleth of {_html.escape(spec["title"].lower())} by West Virginia county.">'
           '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<rect width="6" height="6" fill="var(--hatch-bg)"/>'
           '<line x1="0" y1="0" x2="0" y2="6" stroke="var(--hatch)" stroke-width="1.6"/></pattern></defs>'
           f'<g>{"".join(paths)}</g></svg>')

    ordered = summary.sort_values("county_name")
    rows = [(f'{r["county_name"]} County', spec["fmt"](None if pd.isna(r.get(spec["col"])) else float(r[spec["col"]])))
            for _, r in ordered.iterrows()]
    tbl = _data_table_html(f"{spec['title']} by county", ["County", "Value"], rows)
    src_name, src_url, _ = SOURCES[spec["src"]]

    body = (
        '<main class="wrap embed">'
        f'<h1 class="sr-only">{_html.escape(spec["title"])} — West Virginia</h1>'
        '<div class="atlas-map" style="border:0;padding:0">'
        f'<div class="map-meta"><h3>{_html.escape(spec["title"])}</h3>'
        f'<span class="cov">{have} of 55 counties reporting</span></div>'
        f'<div class="map-box">{svg}</div>'
        f"{_legend_html(spec)}"
        f'<p class="map-note">{_html.escape(spec["note"])}</p>'
        f'<p class="src">Source: <a href="{src_url}">{_html.escape(src_name)}</a></p>'
        f"{tbl}</div></main>")
    extra = (".embed{max-width:900px;} #map .na{fill:url(#hatch);} "
             "#map .cty{stroke:var(--map-edge);stroke-width:.8;}")
    html_doc = "\n".join(
        _head(f"{spec['title']} — WV", extra) + ["<body>", body, "</body>", "</html>"])
    return f"{_MAP_FILES[key]}.html", html_doc


def _data_table_html(caption, columns, rows) -> str:
    head = "".join(f'<th scope="col">{_html.escape(str(c))}</th>' for c in columns)
    body = []
    for row in rows:
        cells = [f'<th scope="row">{_html.escape(str(row[0]))}</th>']
        cells += [f"<td>{_html.escape(str(v))}</td>" for v in row[1:]]
        body.append("<tr>" + "".join(cells) + "</tr>")
    cap = _html.escape(caption)
    return ('<details class="dt" style="margin-top:1rem"><summary>Show data table</summary>'
            f'<div class="tscroll"><table><caption class="sr-only">{cap}</caption>'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div></details>")


# ── Orchestration ─────────────────────────────────────────────────────────────

def main():
    print("Loading data …")
    data = load_data()
    summary = latest_summary(data)
    if data.geojson is None:
        raise SystemExit("Could not load county geometry — aborting build.")
    proj = project_counties(data.geojson)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()

    payload = build_payload(data, summary, proj)
    by_fips = {c["f"]: c for c in payload["counties"]}

    print("Writing index.html …")
    (DOCS_DIR / "index.html").write_text(build_index(payload))

    print("Writing per-county embeds …")
    for fips in COUNTIES:
        fname, html_doc = build_county_embed(payload, by_fips[fips])
        (EMBED_DIR / fname).write_text(html_doc)

    print("Writing statewide map embeds …")
    for key in MAP_METRICS:
        fname, html_doc = _map_embed(payload, summary, key)
        (EMBED_DIR / fname).write_text(html_doc)

    n_pages = len(list(EMBED_DIR.glob("*.html"))) + 1
    print(f"Done. {n_pages} pages written to {DOCS_DIR}")


if __name__ == "__main__":
    main()
