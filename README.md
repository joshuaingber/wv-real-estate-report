# West Virginia Regional Real Estate Report

An interactive, automatically updating dashboard of residential real estate
indicators for all 55 West Virginia counties: home prices, price per square
foot, home-price growth, new residential construction, and rental affordability.
Modeled on the [Upper Peninsula Regional Economic Report][up], built for West
Virginia University.

**Live site:** _(enable GitHub Pages on the `docs/` folder — see below)_

## What it shows

- **The Atlas** — one large choropleth with a four-way switch (home value, price
  per square foot, home-price growth, permits). Shading uses fixed dollar/percent
  class breaks, so a color means the same range on every measure. Beside it, a
  county profile: rank, a position strip, and a nine-metric KPI grid.
- **Masthead strip plot** — all 55 county median home values on one dollar axis;
  hovering a tick lights that county on the state silhouette.
- **County trends** — long-run FHFA index, monthly listing price, the
  single-family / multifamily permit split by year, and HUD Fair Market Rents by
  bedroom, for the selected county.
- **Residential construction** — the statewide 2025 total and a ranked bar list.
- **Sortable all-counties table**; selecting a county from any control (map,
  picker, bar row, table row, strip plot) updates everything at once.

The static site (`docs/`) is **inline SVG + vanilla JS driven by one JSON
payload** — no charting library and no CDN, so it renders offline and themes
cleanly in light and dark mode. Every chart has a text alternative (a collapsible
data table), a source link, and a specific `aria-label`; the site targets
**WCAG 2.1 AA** (WVU / ADA Title II). The Streamlit app (`app.py`) still uses
Plotly.

### Design system

- **Type:** Archivo (variable-width display), Public Sans (body), IBM Plex Mono
  (labels, FIPS codes, axis ticks) — loaded from Google Fonts, with system
  fallbacks.
- **Color:** WVU Blue `#002855` for primary ink and the masthead; WVU Gold
  `#EEAA00` for fills only; Old Gold `#7F6310` for gold as text on light; Woodburn
  `#8D4638` for declines. Two seven-stop choropleth ramps (`--s0…--s6` sequential,
  `--g0…--g6` growth), one set per theme. Full light/dark token set lives in
  `data/constants.py` (`CSS_TOKENS_LIGHT` / `CSS_TOKENS_DARK`).

## Data sources (all free, public, and cacheable)

| Source | Metrics | County coverage |
|---|---|---|
| FHFA House Price Index | Annual home-price index + growth | 41 of 55 |
| U.S. Census ACS 5-year | Median home value, rent, ownership | 55 (needs a key) |
| Realtor.com via FRED | Median list price, **$/sq ft**, days on market, listings | 12 of 55 |
| U.S. Census Building Permits Survey | Residential units authorized | 55 |
| HUD Fair Market Rents | Rents by bedroom | 55 (needs a token) |

**Scope is residential.** Free county-level *commercial* real estate data
(rents, vacancy, cap rates, CRE prices) is not publicly available, so it is out
of scope by design. Coverage gaps are shown honestly — a county with no
published value renders uncolored on maps and "—" in tables. No value is ever
fabricated to fill a gap.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then add your free API keys (see below)

streamlit run app.py          # interactive app
python build.py               # regenerate the static docs/ site
```

Add `REPORT_OFFLINE=1` before either command to use the committed data caches
and skip every network call (fast iteration; no keys needed).

### API keys

Put these in `.env` (all free, all instant):

- `FRED_API_KEY` — <https://fredaccount.stlouisfed.org/apikeys> (listing metrics)
- `CENSUS_API_KEY` — <https://api.census.gov/data/key_signup.html> (median home value, rent)
- `HUD_TOKEN` — <https://www.huduser.gov/portal/dataset/fmr-api.html> (Fair Market Rents)

FHFA and building permits need no key. Without a key, the affected panels
degrade to "—" and the rest of the dashboard still works.

## Deploy (GitHub Pages)

The build writes to `docs/`. In the repository settings, set **Pages → Build and
deployment → Source: Deploy from a branch**, branch `main`, folder `/docs`. Every
push that updates `docs/` republishes the site.

The `.github/workflows/update-data.yml` action re-fetches all sources every
Monday, rebuilds `docs/`, runs the accessibility gate, and commits the refresh —
so the dashboard stays current with no manual work. Set the three keys above as
repository secrets (`gh secret set FRED_API_KEY`, etc.) for the action to use.

## Accessibility

```bash
npm install
npm run a11y                   # pa11y-ci over every page, WCAG 2.1 AA
```

The same check runs in CI on every push and gates the weekly data refresh: a
build with any violation is not published.

[up]: https://github.com/joshuaingber/upper-peninsula-economic-report
