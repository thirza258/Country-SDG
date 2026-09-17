"""Local map geometry and links to the report's canonical country profiles."""
from functools import lru_cache
import json

from django.conf import settings
from django.urls import reverse

from . import analytics


@lru_cache(maxsize=1)
def _geometry():
    return json.loads((settings.BASE_DIR / "data" / "world_map.json").read_text())


def world_map(summary):
    dataset = analytics.get_dataset()
    scores = {row["country"]: row["score"] for row in summary["leaderboard"]}
    countries = {}
    for code, name in dataset.index[["country_code", "country"]].drop_duplicates().itertuples(index=False):
        if name not in scores:
            continue
        countries[code] = {
            "name": name, "score": scores[name],
            "url": reverse("country", kwargs={"country_name": name}),
        }
    features = []
    palette = ["#dcecf4", "#afd4e6", "#78b4d1", "#398db5", "#00689d"]
    for feature in _geometry():
        country = countries.get(feature["code"], {})
        score = country.get("score")
        features.append({
            **feature, **country,
            "fill": palette[min(4, max(0, int((score - 40) // 10)))] if score is not None else "var(--map-empty)",
        })
    return features, countries
