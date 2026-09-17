"""Refresh the landing page from the public Data360 and SDG.org catalogues.

Report scores stay in analytics.py. UN indicators are observations in their own
units, never replacements for (or averages into) the SDSN SDG Index.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import re
from threading import Lock

import requests
from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)
API = "https://data360api.worldbank.org/data360/portal/v1"
WORLD_BANK_URL = "https://data360.worldbank.org/en/dataset/UN_SDG"
SDG_URL = "https://www.sdg.org/"
# The public catalogue group declared by www.sdg.org's ArcGIS Hub configuration.
SDG_GROUP = "a64ea13493d34df5b24e0f471401b601"
INDICATORS = (
    {
        "id": "wasting", "code": "UN_SDG_SH_STA_MAL", "sdg": "2.2.2",
        "title": "Child wasting", "unit": "%", "unit_code": "PT_POP_Y_LE5",
        "description": "Children under five affected by wasting. Both sexes; latest available observation.",
        "breakdown": "UN_SDG_MAL_WAS", "sex": "_T",
    },
    {
        "id": "agriculture", "code": "UN_SDG_AG_LND_SUST", "sdg": "2.4.1",
        "title": "Sustainable agriculture", "unit": "%", "unit_code": "PT",
        "description": "Agricultural area under productive and sustainable agriculture; latest available observation.",
        "breakdown": "_Z", "sex": "_Z",
    },
    {
        "id": "biodiversity", "code": "UN_SDG_ER_RSK_LBREDS", "sdg": "2.5.2",
        "title": "Local breeds at risk", "unit": "%", "unit_code": "PT",
        "description": "Local livestock breeds classified as at risk of extinction; latest available observation.",
        "breakdown": "_Z", "sex": "_Z",
    },
)
_refresh_lock = Lock()


def _json_get(url, **params):
    response = requests.get(url, params=params, timeout=(3, 8))
    response.raise_for_status()
    # Data360's portal data response includes a UTF-8 BOM.
    return json.loads(response.content.decode("utf-8-sig"))


def _observations(payload, indicator):
    """Select one explicit disaggregation and the latest numeric year per area."""
    if not isinstance(payload, list):
        raise ValueError("Expected Data360 time series")
    observations = {}
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("Invalid time series row")
        if any(row.get(key) != value for key, value in {
            "DATABASE_ID": "UN_SDG", "INDICATOR": indicator["code"],
            "SEX": indicator["sex"], "AGE": "_T", "URBANISATION": "_T",
            "COMP_BREAKDOWN_1": indicator["breakdown"],
            "COMP_BREAKDOWN_2": "_Z", "COMP_BREAKDOWN_3": "_Z",
            "UNIT_MEASURE": indicator["unit_code"],
        }.items()) or str(row.get("UNIT_MULT")) != "0":
            continue
        area = row.get("REF_AREA")
        series = row.get("data", {})
        if not isinstance(series, dict):
            raise ValueError("Invalid time series data")
        years, values = series.get("xAxis", []), series.get("yAxis", [])
        if (not isinstance(area, str) or not area or not isinstance(years, list)
                or not isinstance(values, list) or len(years) != len(values)):
            raise ValueError("Invalid observation dimensions")
        for year, value in zip(years, values):
            if value is None or isinstance(value, bool):
                continue
            try:
                year, value = int(year), float(value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value) or not 0 <= value <= 100:
                continue
            if not 1900 <= year <= datetime.now(timezone.utc).year:
                continue
            old = observations.get(area)
            if old and old["year"] == year and old["value"] != value:
                raise ValueError("Ambiguous values for the same area and year")
            if old is None or year > old["year"]:
                observations[area] = {"value": value, "year": year}
    if not observations:
        raise ValueError("No usable observations returned")
    years = [item["year"] for item in observations.values()]
    return {"observations": observations, "latest_year": max(years), "earliest_year": min(years)}


def _fetch_indicator(indicator):
    # This endpoint returns the complete arrays of years and values per series.
    # It does not use the obsolete /data endpoint's top/skip pagination.
    payload = _json_get(f"{API}/data", database_id="UN_SDG", indicator_id=indicator["code"])
    return _observations(payload, indicator)


def _fetch_metadata():
    payload = _json_get(f"{API}/metadata", type="dataset", id="UN_SDG")
    description = payload["data"]["database_description"]
    if description["title_statement"]["idno"] != "UN_SDG":
        raise ValueError("Unexpected dataset")
    versions = [row["date"] for row in description.get("version", []) if row.get("date")]
    dates = [datetime.fromisoformat(value).date().isoformat() for value in versions]
    return {"published_at": max(dates) if dates else None}


def _fetch_hubs():
    payload = _json_get(
        "https://sdg.maps.arcgis.com/sharing/rest/search", f="json",
        q=f'group:{SDG_GROUP} AND type:"Hub Page"',
        sortField="modified", sortOrder="desc", num=20,
    )
    if "error" in payload or not isinstance(payload.get("results"), list):
        raise ValueError("SDG.org catalogue unavailable")
    items = []
    for row in payload["results"]:
        # Hub pages identify their public route in the catalogue, even when
        # ArcGIS's generic `url` field is empty. Never use management URLs.
        slugs = [keyword.rsplit("|", 1)[-1] for keyword in row.get("typeKeywords", [])
                 if keyword.startswith("slug|sdg|")]
        if not slugs or not re.fullmatch(r"[a-zA-Z0-9-]+", slugs[0]):
            continue
        items.append({
            "title": row["title"], "url": f"https://www.sdg.org/pages/{slugs[0]}",
            "modified": datetime.fromtimestamp(row["modified"] / 1000, timezone.utc).date().isoformat(),
        })
        if len(items) == 3:
            break
    if not items:
        raise ValueError("No public SDG.org updates returned")
    return {"items": items}


def _snapshot():
    cached = caches["live_data"].get("sources-v1")
    if cached is not None:
        return cached
    path = Path(settings.BASE_DIR) / "data" / "live_sources.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _refresh_one(key, fetcher, previous, now):
    try:
        data = fetcher()
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError, OverflowError) as error:
        logger.warning("SDG source %s unavailable: %s", key, error)
        return key, {**previous, "checked_at": now, "failed": True, "retry_at": now + 900}
    changed = previous.get("changed_at", previous.get("fetched_at", now)) if previous.get("data") == data else now
    return key, {"data": data, "fetched_at": now, "changed_at": changed, "checked_at": now,
                 "retry_at": now + settings.SDG_REFRESH_SECONDS, "failed": False}


def landing_sources(*, refresh=False, force=False):
    """Fast local reads for HTML; the JSON route refreshes expired sources."""
    now = datetime.now(timezone.utc).timestamp()
    snapshot = _snapshot()
    if refresh and _refresh_lock.acquire(blocking=False):
        try:
            snapshot = _snapshot()
            fetchers = {"world_bank": _fetch_metadata, "hubs": _fetch_hubs}
            fetchers.update({item["id"]: lambda item=item: _fetch_indicator(item) for item in INDICATORS})
            pending = [(key, fetcher) for key, fetcher in fetchers.items()
                       if force or now >= snapshot.get(key, {}).get("retry_at", 0)]
            if pending:
                with ThreadPoolExecutor(max_workers=5) as pool:
                    futures = [pool.submit(_refresh_one, key, fetcher, snapshot.get(key, {}), now)
                               for key, fetcher in pending]
                    for future in futures:
                        key, result = future.result()
                        snapshot[key] = result
                caches["live_data"].set("sources-v1", snapshot, timeout=None)
        finally:
            _refresh_lock.release()

    def resource(key):
        row = snapshot.get(key, {})
        fetched = row.get("fetched_at")
        changed = row.get("changed_at", fetched)
        return {
            **row.get("data", {}),
            "status": ("unavailable" if not fetched else
                       "stale" if row.get("failed") or now - fetched >= settings.SDG_REFRESH_SECONDS else "fresh"),
            "fetched_at": datetime.fromtimestamp(fetched, timezone.utc).isoformat() if fetched else None,
            "changed_at": datetime.fromtimestamp(changed, timezone.utc).isoformat() if changed else None,
        }

    indicators = []
    for item in INDICATORS:
        result = {**item, **resource(item["id"])}
        result.setdefault("observations", {})
        result["area_count"] = len(result["observations"])
        result["url"] = f"https://data360.worldbank.org/en/indicator/{item['code']}"
        indicators.append(result)
    return {
        "indicators": indicators,
        "world_bank": {**resource("world_bank"), "url": WORLD_BANK_URL},
        "hubs": {**resource("hubs"), "url": SDG_URL},
        "refresh_seconds": settings.SDG_REFRESH_SECONDS,
    }
