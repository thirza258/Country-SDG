# SDG Country Profiles

A Django site that answers one question for every country in the dataset: **how is it doing on
each of the 17 Sustainable Development Goals?**

Every figure comes from two CSV files in `data/`. Nothing is modelled, estimated or filled in, and
no external service is needed to produce a single score on the site.

## What the site shows

**Home** — the world SDG Index score and how it has moved since 2015 and since 2000; the world
score on each of the 17 goals with its change since the goals were adopted; the highest and lowest
scoring countries; the biggest gains and the biggest falls; a region table that shows the plain
average of a region's countries next to the region's own published aggregate; and the full ranked
list of all 166 countries, filterable.

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

Search accepts everyday names: `south korea`, `turkey`, `ivory coast`, `USA`, `DR Congo` and ISO
codes such as `IDN` all resolve to the right profile.

## Search engines

`/sitemap.xml` lists every page — home, about, the 17 goals, the 166 countries and the regional
and income aggregates. `/robots.txt` points crawlers at it and keeps them out of `/search/`,
`/api/`, `/healthz` and `/admin/`. Behind the TLS-terminating proxy both advertise `https://`
URLs automatically.

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
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

## Running it with Docker

```bash
docker compose up --build
```

The site is on <http://localhost:9011/>. To change the port, set `HOST_PORT`.

Or without Compose:

```bash
docker build -t sdg-country-profiles .
docker run --rm -p 9011:9011 \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  -e DJANGO_ALLOWED_HOSTS=sdg.nevatal.id,localhost,127.0.0.1 \
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
| `PORT` | `9011` | Port gunicorn binds. |
| `OPENROUTER_API_KEY` | unset | Optional, see below. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Optional, custom OpenAI/OpenRouter endpoint. |
| `OPENROUTER_MODEL` | `google/gemini-2.0-flash-001` | Optional, model to request via OpenRouter. |
| `NEWS_API_KEY` | unset | Optional, see below. |

## The optional extras

A country page can also show a one-paragraph summary written via OpenRouter (using the OpenAI client) from that country's own
computed figures, and a few recent news headlines. Both are optional and clearly labelled where
they appear.

Neither produces or influences any score. With no keys set, those two sections do not render and
every other part of the page is identical. Both calls are wrapped so that a missing package, an
expired key, a rate limit or a timeout degrades to "no section" rather than an error page, and
results — including failures — are cached.

## Project layout

```
data/                                CSV sources
information/
  analytics.py                       parses both CSVs once, computes every rank and trend
  constant.py                        the 17 goals, regions, name aliases, source credits
  services.py                        the two optional integrations, each fully guarded
  views.py                           thin views: look up, render
  sitemaps.py                        sitemap for every static, goal and country page
  templates/                         base, home, country, goal, about, no-match, 404, 500
  static/css/styles.css              the whole design system, light and dark
  static/js/charts.js                SVG line charts and sparklines, no external library
unsdg/                               Django project settings
Dockerfile, docker-compose.yml       container build and local orchestration
docker-entrypoint.sh                 migrate, then gunicorn
```

## Data sources

Sustainable Development Report 2023 and SDG Index 2000–2022, published by the Sustainable
Development Solutions Network (Sachs, J., Lafortune, G., Fuller, G., Drumm, E. et al.).

The Sustainable Development Goals are a United Nations framework. This site is an independent
presentation of published SDG data and is not affiliated with the United Nations, and the figures
it shows are not United Nations statistics.
