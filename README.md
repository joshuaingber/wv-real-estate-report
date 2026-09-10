# West Virginia Regional Real Estate Report

An interactive, automatically updating dashboard of residential real estate
indicators for all 55 West Virginia counties: home prices, price per square
foot, home-price growth, new residential construction, and rental affordability.
Modeled on the [Upper Peninsula Regional Economic Report][up], built for West
Virginia University.

**Live site:** _(enable GitHub Pages on the `docs/` folder — see below)_

## What it shows

- **Statewide maps** — median home value, median listing price per square foot,
  year-over-year home-price growth, and residential permits, each as a
  hover-enabled county choropleth.
- **Residential construction** — permitted units by county and, per county, the
  single-family / multifamily split over time.
- **County detail** — a KPI card plus price trends (long-run FHFA index and
  recent monthly listings), permit history, and Fair Market Rents for every
  county, in an embeddable page.
- **Full data table** and a "source data" link on every chart.

Every chart has a text alternative (a collapsible data table) and the site
targets **WCAG 2.1 AA** (WVU / ADA Title II).

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
