# SDG Country Profiles

A Django site that answers one question for every country in the dataset: **how is it doing on
each of the 17 Sustainable Development Goals?**

Country scores come from the bundled Sustainable Development Report datasets. The landing page
also refreshes selected UN SDG indicators from World Bank Data360 and recent resources from
SDG.org. It keeps the sources, units and observation years distinct.

## What the site shows

**Home** — a UN-blue world map, country search, 17-goal directory and filterable report rankings.
The map switches between the historical 2023 SDG Index and three live Goal 2 measures: child
wasting, sustainable agriculture and local livestock breeds at risk. Each country shows its
latest available observation year. Source checks and saved-data fallback are labelled.

**Country page** (`/country/<name>/`) — the headline score with global and regional rank, change
since 2015 and since 2000, and the regional average; a 2000–2022 trend chart of the country
against its region and the world; the goals it is closest to and furthest from; where it has
gained and lost ground since 2015; and a card for each of the 17 goals carrying the score, its
rank among the countries assessed, its quartile position, the change since 2015, comparison marks
for the regional and all-country averages, and a sparkline of the full series.

**Goal page** (`/goal/<1-17>/`) — one goal across every country: the world score and its trend,
regional averages, the distribution of scores, the biggest gains and falls since 2015, the full
ranked table, and the list of countries not assessed on that goal.

**About the data** (`/about/`) — what a score means, how the published index handles missing
goals, why regional averages appear twice, and what the site deliberately does not claim.

**JSON** (`/api/country/<name>/`) — the same profile the page is built from.
`/api/sources/` returns the live landing-page sources and their freshness status.

Search accepts everyday names: `south korea`, `turkey`, `ivory coast`, `USA`, `DR Congo` and ISO
codes such as `IDN` all resolve to the right profile.

## Handling of the data

Two details in these files will produce wrong pages if they are taken at face value.

**Missing is not zero.** The 2000–2022 file has no empty cells: it writes `0.0` where a goal is
not assessed. The 2023 file leaves those cells blank. For the 166 countries the 2023 blanks decide
the question. Reading "all zeros" as "missing" instead would be wrong, because the report also
contains five genuine zero scores, two of which sit on a series that is zero throughout (Burundi
on Goal 1, Qatar on Goal 13). Those are real results and the site shows them as `0.0`. Aggregates
have no 2023 row, so there the all-zero test is used as a fallback. Nothing that is not assessed
is ever plotted, ranked or averaged as a zero.

**The 17 goals do not average to the headline.** The published overall score fills each missing
goal with that country's regional average for that goal before averaging. Reproducing that
matches every published score to within 6×10⁻⁹; a plain average of the goals present diverges by
up to 3.46 points. The site therefore displays the published score and never recomputes it.

Both points, and the rest of the method, are on the `/about/` page.

## Running it locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # optional, see below
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

## Running it with Docker

```bash
docker compose up --build
```

The site is on <http://localhost:8000/>. To change the port, set `HOST_PORT`.

Or without Compose:

```bash
docker build -t sdg-country-profiles .
docker run --rm -p 8000:8000 \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
  sdg-country-profiles
```

The image is a two-stage build on `python:3.12-slim`. It runs as a non-root user, collects static
files at build time, serves them through WhiteNoise, runs `migrate` on start, and exposes a
liveness endpoint at `/healthz` that reports how many countries and years parsed.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `SECRET_KEY` | insecure dev key | **Set this in production.** |
| `DJANGO_DEBUG` | `True` | Set to `False` when deployed. |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma separated. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma separated, with scheme. |
| `DJANGO_BEHIND_PROXY` | unset | Set to `1` behind a TLS-terminating proxy: enables the forwarded-proto header, HTTPS redirect and secure cookies. |
| `DJANGO_DB_PATH` | `db.sqlite3` | Only Django's own admin/session tables; the site's content is read-only CSV. |
| `WEB_CONCURRENCY` | `3` | Gunicorn workers. |
| `PORT` | `8000` | Port gunicorn binds. |
| `GEMINI_API_KEY` | unset | Optional, see below. |
| `NEWS_API_KEY` | unset | Optional, see below. |
| `SDG_REFRESH_SECONDS` | `86400` | Refresh expired public sources on the next visit; minimum 300 seconds. |
| `SDG_CACHE_DIR` | `var/sdg-cache` | Writable persistent directory for live source snapshots. |

## Automatic source updates

No API keys are needed. HTML renders immediately from a local snapshot, then the browser calls
`/api/sources/`. Sources older than 24 hours refresh independently through the current Data360
`/data360/portal/v1/data` and `/metadata` APIs and the public catalogue group declared by
[SDG.org](https://www.sdg.org/). The browser checks again every five minutes while visible and
when the tab becomes active; fresh server responses are reused without upstream calls.

Data360 currently contains a subset of UN SDG indicators. The selected live observations are
percentages, **not SDG Index scores**. The importer filters exact disaggregations, preserves
zero, skips null and nonnumeric values, rejects conflicting observations, and selects the latest
numeric year for each area. It never averages observations into a world score or rewrites the
historical country rankings. Source coverage can differ between indicators and countries.

A small verified snapshot is bundled in `data/live_sources.json` for first launch or offline use.
New successful responses persist in `SDG_CACHE_DIR` across workers and restarts. Failed refreshes
retain the original retrieval date and data, display a saved-data status, and retry after 15
minutes. Source checks, dataset release dates, observation years and SDG.org page modification
dates have different meanings and are shown separately. SDG.org updates link directly to public
pages from its ArcGIS Hub catalogue; the site does not scrape its rendered HTML at runtime.

Refresh on demand, or run this from your scheduler for updates even without visitors:

```bash
python manage.py refresh_sdg_data
# Example daily cron (use your deployment's absolute paths):
# 0 3 * * * cd /app && /opt/venv/bin/python manage.py refresh_sdg_data
```

The command exits nonzero if a source fails while retaining successful results. Docker Compose
persists the cache in the existing `/app/var` volume. No scheduler is required for visit-triggered
updates, and none is installed automatically.

## Automatically generated sitemap

`/sitemap.xml` is generated on every request from the current profiles and the 17-goal catalogue.
It includes the home and methodology pages, all country and aggregate profiles, and all goals.
`/robots.txt` advertises its absolute URL using the current host and scheme (including the
configured HTTPS proxy headers). No static sitemap file, manual rebuild or domain hardcoding is
needed. API endpoints, search results and old redirect URLs are excluded.

Modification dates come from the relevant report files and page templates. The landing page also
uses the last time source content changed. Checking an unchanged source or requesting the sitemap
does not invent a new modification date. Sitemap requests read local source snapshots and never
wait for third-party APIs. Source refreshes become visible in the next sitemap response.

## Verification

```bash
python manage.py collectstatic --noinput
python manage.py test information
```

Tests cover report regressions, exact indicator disaggregation, missing and zero observations,
source timeouts, malformed responses, freshness and retry backoff. Browser checks cover the map,
search, country filter, responsive layout and source rendering.

## The optional extras

A country page can also show a one-paragraph summary written by Gemini from that country's own
computed figures, and a few recent news headlines. Both are optional and clearly labelled where
they appear.

Neither produces or influences any score. With no keys set, those two sections do not render and
every other part of the page is identical. Both calls are wrapped so that a missing package, an
expired key, a rate limit or a timeout degrades to "no section" rather than an error page, and
results — including failures — are cached.

## Project layout

```
data/                                CSV sources, map geometry and initial live snapshot
information/
  analytics.py                       parses both CSVs once, computes every rank and trend
  constant.py                        the 17 goals, regions, name aliases, source credits
  services.py                        the two optional integrations, each fully guarded
  live_data.py                       public source fetching, validation and persistent cache
  maps.py                            bundled boundaries and canonical country links
  sitemaps.py                        automatic canonical URLs and content modification dates
  management/commands/refresh_sdg_data.py  optional scheduled/manual refresh
  views.py                           thin views: look up, render
  templates/                         base, home, country, goal, about, no-match, 404, 500
  static/css/styles.css              shared design system, light and dark
  static/css/home.css                restrained UN-blue landing page
  static/js/home.js                  map, filters and automatic source refresh
  static/js/charts.js                SVG line charts and sparklines, no external library
unsdg/                               Django project settings
Dockerfile, docker-compose.yml       container build and local orchestration
docker-entrypoint.sh                 migrate, then gunicorn
```

## Data sources

Sustainable Development Report 2023 and SDG Index 2000–2022, published by the Sustainable
Development Solutions Network (Sachs, J., Lafortune, G., Fuller, G., Drumm, E. et al.).

The Sustainable Development Goals are a United Nations framework. This site is an independent
presentation of published SDG data and is not affiliated with the United Nations. Its SDG Index
rankings are SDSN report scores. The separate live indicators are sourced from the UN SDG dataset
via World Bank Data360.

Live sources: [UN SDG on World Bank Data360](https://data360.worldbank.org/en/dataset/UN_SDG)
and the [SDG Data Alliance](https://www.sdg.org/). Report rankings retain the 2023 edition.

Map geometry is derived from [Natural Earth 1:110m countries](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/),
public domain. It is bundled locally; there is no map SDK, map API key or third-party tile request.
Rebuild it with `python scripts/build_world_map.py`. Small territories may not be visible at this
map scale; all available country profiles remain searchable in the table.
