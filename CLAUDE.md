# CLAUDE.md — West Virginia Regional Real Estate Report

Codebase notes for future work. Architecture is cloned from the Upper Peninsula
Regional Economic Report; the geography is West Virginia's 55 counties (FIPS 54)
and the domain is **residential real estate** (commercial is out of scope — no
free county-level data exists).

## Layout

- `data/constants.py` — single source of truth: 55-county FIPS map, WVU palette
  (+ WCAG tokens), data-source URLs, ACS variables, verified FRED series prefixes.
  Re-skin or re-scope from here.
- `data/fetch_*.py` — one fetcher per source; each caches a parquet in
  `data/cache/` and degrades to that cache (or empty) on failure. `data/geo.py`
  loads the WV-filtered county GeoJSON. `data/clean.py` merges everything into a
  `RealEstateData` container and `latest_summary()` (one row per county).
- `components/*` — chart builders returning `plotly.graph_objects.Figure`
  (`maps.py`, `trends.py`, `permits.py`, `affordability.py`) and the KPI card
  (`county_kpi.py`, returns HTML + a Streamlit `render`). **Used only by the
  Streamlit app now** — the static build no longer imports them.
- `app.py` — Streamlit app (still Plotly). `build.py` — static generator → `docs/`.
- `utils/` — formatting + narrative helpers. `data/analysis.py` — STL trend +
  projection (monthly).

## Static build (docs/) — inline SVG, no Plotly

The `docs/` site is a token-driven, dependency-free redesign (inline SVG + vanilla
JS, no charting library, no CDN). `build.py` does three things: emit the design
tokens, build **one JSON payload** (`D`), and stitch pages from three verbatim
presentation assets.

- `assets/report.css`, `assets/report_body.html`, `assets/report.js` — the design
  reference's style, markup and interaction logic, copied verbatim. Edit these to
  change the page's look/behavior; `build.py` only injects data. `index.html` is
  `<token CSS> + report.css + report_body.html + <script>const D=…; report.js`.
- **Payload** (`build_payload`): per county `{f,n,c(centroid),hv,ppsf,g,pt,psf,
  rent,own,vac,built,dom, hpi[],lps[],perm[],fmr[]}` + `paths` (from
  `data.geo.project_counties`, an equirectangular projection of the cached
  GeoJSON to a shared pixel box) + `W,H,acsYear,fmrYear`. Missing → `null`.
- **Tokens** live in `constants.py` as `CSS_TOKENS_LIGHT` / `CSS_TOKENS_DARK`
  (verbatim from the reference `:root` + dark blocks); `build.py::_token_css()`
  emits `:root`, a dark `@media` block, and `[data-theme]` overrides.
- **Embeds** (`docs/embeds/`): per-county pages render inline (no iframe) with a
  self-contained `EMBED_JS` copy of the chart primitives; map pages are
  server-rendered static SVG (`_map_embed`). Fixed class breaks + measure specs
  are duplicated in `build.py::MAP_METRICS` to match `report.js`'s `METRICS`.
- **Vintage labels are hardcoded in `assets/report.js`** to the reference's data
  (FHFA growth "2022 to 2023", permits "2025"); ACS/FMR years are dynamic (from
  `D`). When FHFA/permits publish a newer year, bump those literal strings in
  `report.js` and the `MAP_METRICS` titles.
- **Fonts:** Archivo (display) / Public Sans (body) / IBM Plex Mono (labels), via
  `GOOGLE_FONTS_IMPORT` (a head `<link>`) in `constants.py`.

## Data-source facts (verified 2026-09)

- **FHFA county HPI**: xlsx at `fhfa.gov/document/hpi_at_bdl_county.xlsx`, header
  on row 7, "." = missing. Covers **41 of 55** WV counties. Annual.
- **FRED Realtor.com**: county series naming is irregular — price series are
  `MEDLISPRI{fips}` / `MEDLISPRIPERSQUFEE{fips}` / `MEDDAYONMAR{fips}` (no infix),
  count series are `ACTLISCOU{fips}` / `NEWLISCOU{fips}` (with "COU"). Covers
  **12 of 55** counties (larger ones only). Monthly. Needs `FRED_API_KEY`.
- **Census ACS5**: REST API, **requires** `CENSUS_API_KEY` (keyless →
  missing_key.html). All 55 counties. `fetch_census_acs.py` walks back to the
  newest published vintage.
- **Census BPS**: annual county files `www2.census.gov/econ/bps/County/co{YYYY}a.txt`,
  two-row header + blank line, positional columns. All 55 counties. No key.
- **HUD FMR**: `huduser.gov/hudapi/public/fmr/data/{fips}99999`, needs
  `HUD_TOKEN`. All 55 counties.

## Conventions

- Never fabricate a value to fill a coverage gap. Missing → NaN → "—" / uncolored.
- Every chart in the build ships `role="img"` + `aria-label` + a `<details>` data
  table + a source link. The pa11y gate (`npm run a11y`) blocks any WCAG 2.1 AA
  violation and gates the weekly refresh.
- WVU Gold (`#EEAA00`) fails contrast on white — fills/large shapes only, never
  thin lines or text. Use `WVU_BLUE`, `WOODBURN`, or the `WVU_*_DARK` tokens for
  data-bearing marks.
- `REPORT_OFFLINE=1` makes every fetcher read its cache and skip the network —
  use for local iteration; CI leaves it unset to fetch fresh.

## Common tasks

- Add a metric: extend the relevant fetcher + `latest_summary()`, then add it to
  the payload in `build.py::build_payload`, a `METRICS` entry in
  `assets/report.js` (map + profile), and a Plotly builder in `components/` for
  `app.py`.
- Re-skin the static site: edit `CSS_TOKENS_*` in `constants.py` (colors) and
  `assets/report.css` (layout); re-brand Plotly for the app via the palette hexes.
- New data vintage: fetchers auto-detect the newest year; rerun `build.py`. Bump
  the hardcoded FHFA/permit year labels in `assets/report.js` + `MAP_METRICS` if
  the vintage rolled over.
