"""
Constants for the West Virginia Regional Real Estate Report.

FIPS codes, data-source endpoints, ACS variables, and the WVU color palette.
Architecture and conventions adapted from the Upper Peninsula Regional Economic
Report (github.com/joshuaingber/upper-peninsula-economic-report). Geography here
is all 55 counties of West Virginia (state FIPS 54); branding follows the West
Virginia University brand.

Scope is RESIDENTIAL real estate. Free, county-level commercial real estate data
(rents, vacancy, cap rates, CRE prices) is not publicly available, so it is out
of scope by design — not omitted by oversight.
"""
from __future__ import annotations

from datetime import date

# ── Geography ─────────────────────────────────────────────────────────────────
# All 55 counties of West Virginia (state FIPS 54; county codes are the odd
# numbers 001–109). FIPS → name, ordered alphabetically for the county dropdown.
# This is the canonical, stable list — hardcoded rather than fetched so the app
# has no network dependency just to enumerate its own geography.
STATE_FIPS = "54"

COUNTIES = {
    "54001": "Barbour",
    "54003": "Berkeley",
    "54005": "Boone",
    "54007": "Braxton",
    "54009": "Brooke",
    "54011": "Cabell",
    "54013": "Calhoun",
    "54015": "Clay",
    "54017": "Doddridge",
    "54019": "Fayette",
    "54021": "Gilmer",
    "54023": "Grant",
    "54025": "Greenbrier",
    "54027": "Hampshire",
    "54029": "Hancock",
    "54031": "Hardy",
    "54033": "Harrison",
    "54035": "Jackson",
    "54037": "Jefferson",
    "54039": "Kanawha",
    "54041": "Lewis",
    "54043": "Lincoln",
    "54045": "Logan",
    "54047": "McDowell",
    "54049": "Marion",
    "54051": "Marshall",
    "54053": "Mason",
    "54055": "Mercer",
    "54057": "Mineral",
    "54059": "Mingo",
    "54061": "Monongalia",
    "54063": "Monroe",
    "54065": "Morgan",
    "54067": "Nicholas",
    "54069": "Ohio",
    "54071": "Pendleton",
    "54073": "Pleasants",
    "54075": "Pocahontas",
    "54077": "Preston",
    "54079": "Putnam",
    "54081": "Raleigh",
    "54083": "Randolph",
    "54085": "Ritchie",
    "54087": "Roane",
    "54089": "Summers",
    "54091": "Taylor",
    "54093": "Tucker",
    "54095": "Tyler",
    "54097": "Upshur",
    "54099": "Wayne",
    "54101": "Webster",
    "54103": "Wetzel",
    "54105": "Wirt",
    "54107": "Wood",
    "54109": "Wyoming",
}

# County boundary geometry: the standard plotly US-counties GeoJSON keyed on
# 5-digit FIPS, filtered to state 54 so the map frames West Virginia tightly.
GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)

# ── West Virginia University color palette ───────────────────────────────────
# Web-optimized WVU brand hex (scm.wvu.edu/brand). "Gold and Blue," in that order.
#   WVU Blue #002855 — very high contrast on white (~12:1); the primary data ink.
#   WVU Gold #EEAA00 — ~1.7:1 on white: FILLS AND LARGE SHAPES ONLY, never thin
#                      lines or text. Gold-on-blue is the signature pairing.
WVU_BLUE = "#002855"
WVU_GOLD = "#EEAA00"

# Secondary / neutral brand hues.
SAFETY_BLUE = "#0062A3"   # secondary blue
WOODBURN = "#8D4638"      # warm brick — the "decline / negative" emphasis color
RATTLER_GRAY = "#554741"  # axes, labels, captions
COOPERS_GRAY = "#BFB8B3"  # decorative droplines, faded "before" marks (not text)
WILD_FLOUR = "#F2E6C2"    # pale region fill
NOT_QUITE_WHITE = "#FAF9F8"
COAL = "#1B222D"

# ── Accessible-contrast tokens (WCAG 2.1 AA) ─────────────────────────────────
# Brand hues that fail contrast on white are replaced, in text/UI/data-bearing
# roles, by these. Ratios are against #FFFFFF.
WVU_LINK = WVU_BLUE          # ~12:1 — link text (also underlined, never color-only)
WVU_MUTED = "#595959"        # ~7:1  — captions, sources, footer
WVU_BORDER = "#767676"       # ~4.5:1 — structural UI borders and focus rings
WVU_GOLD_DARK = "#7F6310"    # WVU "Old Gold" (web) ~5.4:1 — gold hue in text/data roles
SEMANTIC_RED = WOODBURN      # negative deltas / decline (paired with a redundant cue)

# Diverging scale for choropleths shaded by a year-over-year CHANGE (e.g. HPI
# growth): decline (Woodburn) → ≈flat (gold, the zmid) → growth (WVU Blue).
# A single map border color can't clear 3:1 against both the pale-gold midtone
# and the dark ends, so black borders are the best-effort separation cue and the
# data table remains the normative fallback (WCAG 1.1.1).
MAP_DIVERGING_SCALE = [
    [0.0, WOODBURN],
    [0.5, WVU_GOLD],
    [1.0, WVU_BLUE],
]

# Sequential scale for choropleths shaded by a LEVEL (e.g. median $/sqft): pale
# blue → WVU Blue. On-brand and colorblind-safe.
MAP_SEQUENTIAL_BLUE = [
    [0.0, "#E6ECF2"],
    [0.5, SAFETY_BLUE],
    [1.0, WVU_BLUE],
]

# ── Typography ───────────────────────────────────────────────────────────────
# The static report (build.py → docs/) uses three freely-embeddable Google Fonts,
# loaded from a <link> in the document head:
#   Archivo (variable width)  — display / headings (font-stretch 105–125%, 750–900)
#   Public Sans               — body text
#   IBM Plex Mono             — labels, FIPS codes, axis ticks, source lines
# All three degrade to a system stack if the CDN is unreachable. The Streamlit app
# and the Plotly builders (components/*) fall back to the same stacks.
GOOGLE_FONTS_IMPORT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Archivo:wdth,wght@62..125,400..900&"
    "family=IBM+Plex+Mono:wght@400;500&"
    'family=Public+Sans:ital,wght@0,400..700;1,400&display=swap">'
)
WVU_FONT_FAMILY = '"Public Sans", "Helvetica Neue", Helvetica, Arial, sans-serif'
PLOTLY_FONT = "Public Sans, Helvetica Neue, Helvetica, Arial, sans-serif"

# ── Web design tokens (static report) ─────────────────────────────────────────
# The full light/dark palette that drives the inline-SVG report. Copied verbatim
# from the redesign reference's :root (light) and prefers-color-scheme: dark
# blocks so the CSS custom properties are a single source of truth here.
# build.py emits these as :root, a dark @media block, and [data-theme] overrides.
# Roles: heading/link ink, gold FILLS only (--gold), gold TEXT on light (--gold-text
# = Old Gold #7F6310, ~5.4:1), decline (--neg = Woodburn), navy masthead (--band-*),
# chart marks (--line/--area/--sf/--mf/--sel-*), and the two 7-stop choropleth
# ramps: --s0…--s6 (sequential, levels) and --g0…--g6 (growth), one set per theme.
CSS_TOKENS_LIGHT = """\
  --ground:#F3F5F8; --surface:#FFFFFF; --ink:#12213A; --ink-2:#34425A; --muted:#55617A;
  --rule:#D6DDE6; --rule-strong:#8E99AB;
  --heading:#002855; --link:#002855; --gold:#EEAA00; --gold-text:#7F6310;
  --neg:#8D4638; --pos:#1F6F3F; --focus:#002855;
  --band:#002855; --band-ink:#FFFFFF; --band-muted:#B8C7DB; --band-line:#2B4C77; --band-shape:#0D3A6B; --band-tick:#9FB4CF;
  --line:#002855; --area:rgba(0,40,85,.08); --sf:#002855; --mf:#EEAA00; --hatch:#A9B4C3; --hatch-bg:#EEF1F5;
  --sel-halo:#EEAA00; --sel-core:#12213A; --map-edge:#FFFFFF; --tip-bg:#12213A; --tip-ink:#FFFFFF;
  --s0:#E4EAF1; --s1:#C4D3E4; --s2:#95B3D2; --s3:#6190BF; --s4:#3169A3; --s5:#114782; --s6:#002855;
  --g0:#8D4638; --g1:#F1CF6B; --g2:#CAD7E7; --g3:#90AFD1; --g4:#5282B6; --g5:#215790; --g6:#002855;
  --display:"Archivo","Arial Narrow",Arial,sans-serif;
  --body:"Public Sans","Helvetica Neue",Helvetica,Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;"""

CSS_TOKENS_DARK = """\
  --ground:#07111E; --surface:#0D1B2E; --ink:#E6EBF2; --ink-2:#C3CCD9; --muted:#97A4B7;
  --rule:#1D2E46; --rule-strong:#56667E;
  --heading:#E6EBF2; --link:#9CC2EA; --gold-text:#EEAA00; --neg:#E28B77; --pos:#6CC08E; --focus:#EEAA00;
  --band:#0A2140; --band-ink:#FFFFFF; --band-muted:#A9BAD0; --band-line:#223F66; --band-shape:#14375F; --band-tick:#8FA7C6;
  --line:#9CC2EA; --area:rgba(156,194,234,.12); --sf:#6E9FD6; --mf:#EEAA00; --hatch:#35465E; --hatch-bg:#0D1B2E;
  --sel-halo:#EEAA00; --sel-core:#FFFFFF; --map-edge:#07111E; --tip-bg:#E6EBF2; --tip-ink:#07111E;
  --s0:#17294A; --s1:#1F3B63; --s2:#2A5387; --s3:#3C6EA8; --s4:#5A90C8; --s5:#88B4DF; --s6:#C4DCF3;
  --g0:#D27561; --g1:#C9971F; --g2:#213A5C; --g3:#325A8C; --g4:#4C7EBA; --g5:#7AA9DC; --g6:#BDD8F3;"""

# Per-county identity colors for single-county trend lines. Thin marks on white
# must clear WCAG 1.4.11 (>=3:1), so bright gold is swapped for its dark token.
_COUNTY_PALETTE = [
    WVU_BLUE, WVU_GOLD_DARK, SAFETY_BLUE, WOODBURN, RATTLER_GRAY,
]
COUNTY_COLORS = {
    name: _COUNTY_PALETTE[i % len(_COUNTY_PALETTE)]
    for i, name in enumerate(COUNTIES.values())
}

# ── Data-source endpoints ─────────────────────────────────────────────────────
# NOTE ON VERIFICATION: exact download URLs and FRED series IDs below are
# resolved / confirmed against the live source by the fetchers (data/fetch_*.py)
# before use. Anything a fetcher can't confirm is skipped and the affected panel
# degrades to "—" rather than showing a fabricated number.

# FHFA House Price Index — annual, county-level, all-transactions (public domain).
# The developmental county file. VERIFIED 2026-09: the .xlsx below returns a
# 5 MB workbook; the older .csv paths 404. The fetcher tries these in order and
# verifies the response content before caching.
FHFA_HPI_COUNTY_CANDIDATES = [
    "https://www.fhfa.gov/document/hpi_at_bdl_county.xlsx",
]

# Census Data API — American Community Survey 5-year (county housing profile).
# 5-year estimates are used because they cover every county, including the small
# ones. The fetcher walks back from the newest year until the API responds.
# VERIFIED 2026-09: the API REQUIRES a key — a keyless call redirects to
# missing_key.html. Get a free instant key at
# https://api.census.gov/data/key_signup.html and put it in .env (CENSUS_API_KEY).
CENSUS_API_BASE = "https://api.census.gov/data"
ACS_DATASET = "acs/acs5"
ACS_START_YEAR = date.today().year - 1  # newest plausible ACS5 vintage; fetcher steps back
# Variable → friendly column name.
ACS_VARIABLES = {
    "B25077_001E": "median_home_value",   # Median value (owner-occupied units)
    "B25064_001E": "median_gross_rent",   # Median gross rent
    "B25003_001E": "occupied_units",       # Occupied housing units (denominator)
    "B25003_002E": "owner_occupied_units", # Owner-occupied (→ ownership rate)
    "B25001_001E": "total_housing_units",  # Total housing units
    "B25035_001E": "median_year_built",    # Median year structure built
    "B25002_002E": "occupied_total",       # Occupied (for vacancy rate denom)
    "B25002_003E": "vacant_units",         # Vacant housing units
}

# FRED API — monthly Realtor.com county listing series (public domain via FRED).
# County series follow the pattern <METRIC-PREFIX> + <5-digit FIPS>. The naming
# is IRREGULAR across metrics (price series take no infix; count series take a
# "COU" infix), so these prefixes were VERIFIED individually against the live
# FRED API on 2026-09 for WV counties. The fetcher still validates each
# constructed series ID and skips any that 400 (coverage is sparse for the
# smallest counties, e.g. Wirt 54105 has none).
FRED_API_BASE = "https://api.stlouisfed.org/fred"
FRED_REALTOR_COUNTY_PREFIXES = {
    "median_list_price":       "MEDLISPRI",           # $  — Median Listing Price
    "median_list_ppsf":        "MEDLISPRIPERSQUFEE",  # $  — Median Listing Price / Sq Ft
    "median_days_on_market":   "MEDDAYONMAR",         # days — Median Days on Market
    "active_listings":         "ACTLISCOU",           # count — Active Listing Count
    "new_listings":            "NEWLISCOU",           # count — New Listing Count
}
# Units per metric, for axis/hover formatting downstream.
FRED_REALTOR_UNITS = {
    "median_list_price":     "usd",
    "median_list_ppsf":      "usd",
    "median_days_on_market": "days",
    "active_listings":       "count",
    "new_listings":          "count",
}

# Census Building Permits Survey — county residential permits (public domain).
# Annual county files live at .../County/co{YYYY}a.txt. The fetcher pulls a span
# of recent years and verifies each file before use.
BPS_COUNTY_BASE = "https://www2.census.gov/econ/bps/County"
BPS_START_YEAR = 2000

# HUD USER Fair Market Rents API (federal public data; free bearer token).
# County entity id = state FIPS + county FIPS + "99999".
HUD_FMR_BASE = "https://www.huduser.gov/hudapi/public/fmr"

# ── Data-source display metadata (for on-page citations) ──────────────────────
SOURCES = {
    "fhfa":    ("FHFA House Price Index", "https://www.fhfa.gov/data/hpi", "Annual"),
    "acs":     ("U.S. Census Bureau, ACS 5-Year", "https://www.census.gov/programs-surveys/acs", "Annual"),
    "realtor": ("Realtor.com via FRED", "https://fred.stlouisfed.org", "Monthly"),
    "bps":     ("U.S. Census Bureau, Building Permits Survey", "https://www.census.gov/construction/bps", "Monthly / Annual"),
    "hud":     ("HUD Fair Market Rents", "https://www.huduser.gov/portal/datasets/fmr.html", "Annual"),
}
