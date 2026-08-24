"""Optional extras: an AI commentary paragraph and related news headlines.

Both are strictly optional.  The site's content comes from the CSVs, so if a
key is missing, a package is not installed, or a call fails, these return
``None``/``[]`` and the page renders exactly as it otherwise would.
"""

from __future__ import annotations

import logging
import os

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_SECONDS = 60 * 60 * 6


def _describe(profile: dict) -> str:
    """The country's computed figures, as compact text for the model."""
    lines = [
        f"Country or group: {profile['name']}",
        f"{profile['snapshot']['label']}: {profile['snapshot']['score']}",
    ]
    if profile["snapshot"]["rank"]:
        lines.append(
            f"Global rank: {profile['snapshot']['rank']} of {profile['snapshot']['of']} countries"
        )
    if profile["region_name"]:
        lines.append(
            f"Region: {profile['region_name']} "
            f"(rank {profile['region_rank']} of {profile['region_of']}, "
            f"regional average {profile['region_mean']})"
        )
    if profile["index_change"] is not None:
        lines.append(
            f"SDG Index score {profile['index_first_year']}-{profile['index_latest_year']}: "
            f"{profile['index_first_score']} to {profile['index_latest_score']} "
            f"({profile['index_change']:+})"
        )
    lines.append("Goal scores (0-100, higher is better):")
    for goal in profile["goals"]:
        if not goal["assessed"]:
            lines.append(f"  Goal {goal['number']} {goal['title']}: not assessed")
            continue
        change = "" if goal["change"] is None else f", change since 2000 {goal['change']:+}"
        rank = "" if goal["rank"] is None else f", rank {goal['rank']}/{goal['of']}"
        lines.append(f"  Goal {goal['number']} {goal['title']}: {goal['score']}{rank}{change}")
    return "\n".join(lines)


def ai_commentary(profile: dict) -> str | None:
    """One paragraph interpreting this country's figures, or None."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    cache_key = f"sdg:ai:{profile['name']}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    try:
        import google.generativeai as genai
    except ImportError:
        logger.info("google-generativeai is not installed; skipping AI commentary")
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.4,
                "top_p": 0.95,
                "max_output_tokens": 512,
                "response_mime_type": "text/plain",
            },
            system_instruction=(
                "You summarise Sustainable Development Goal performance for one country. "
                "You are given that country's scores from the Sustainable Development Report "
                "dataset. Write exactly one paragraph of at most 120 words that interprets "
                "THESE numbers: name the goals it scores highest and lowest on, note the "
                "direction of travel since 2000, and say how it compares with its region. "
                "Do not invent statistics that are not in the input, do not repeat the whole "
                "list of scores, and do not use bullet points or headings."
            ),
        )
        response = model.generate_content(
            _describe(profile),
            # Gunicorn's worker timeout is the real ceiling; stay well inside it.
            request_options={"timeout": 8},
        )
        text = (response.text or "").strip()
    except Exception as error:  # any SDK/network/quota failure
        logger.warning("AI commentary unavailable for %s: %s", profile["name"], error)
        cache.set(cache_key, "", 60 * 10)
        return None

    cache.set(cache_key, text, CACHE_SECONDS)
    return text or None


NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
NEWS_TIMEOUT = 4


def related_news(country_name: str, limit: int = 6) -> list[dict]:
    """Recent SDG-related headlines for the country, or an empty list.

    Called with ``requests`` directly rather than through newsapi-python,
    whose 30 second timeout is not adjustable and would outlast the worker.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return []

    cache_key = f"sdg:news:{country_name}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        import requests
    except ImportError:
        logger.info("requests is not installed; skipping news")
        return []

    query = (
        f'"{country_name}" AND ("sustainable development" OR "SDG" OR "United Nations" OR '
        '"climate change" OR "renewable energy" OR "poverty" OR "food security" OR '
        '"gender equality" OR "clean water" OR "biodiversity")'
    )

    try:
        response = requests.get(
            NEWS_ENDPOINT,
            params={"q": query, "language": "en", "sortBy": "relevancy", "pageSize": 20},
            headers={"X-Api-Key": api_key},
            timeout=NEWS_TIMEOUT,
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
    except Exception as error:
        logger.warning("News unavailable for %s: %s", country_name, error)
        cache.set(cache_key, [], 60 * 10)
        return []

    news = [
        {
            "title": article.get("title"),
            "source": (article.get("source") or {}).get("name"),
            "url": article.get("url"),
            "description": article.get("description"),
            "image": article.get("urlToImage"),
            "published": (article.get("publishedAt") or "")[:10],
        }
        for article in articles
        if article.get("title") and article.get("url")
    ][:limit]

    cache.set(cache_key, news, CACHE_SECONDS)
    return news
