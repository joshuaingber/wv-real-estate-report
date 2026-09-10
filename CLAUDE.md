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
  (`county_kpi.py`, returns HTML + a Streamlit `render`).
- `app.py` — Streamlit app. `build.py` — static generator → `docs/`.
- `utils/` — formatting + narrative helpers. `data/analysis.py` — STL trend +
  projection (monthly).

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

- Add a metric: extend the relevant fetcher + `latest_summary()`, then a builder
  in `components/` and a block in `build.py` (+ `app.py`).
- Re-brand: edit the palette block in `constants.py`.
- New data vintage: fetchers auto-detect the newest year; just rerun `build.py`.
