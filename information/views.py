import difflib

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from . import analytics
from .constant import GOALS, SOURCES
from .services import ai_commentary, related_news


def _shell(active=""):
    """Context every page needs: the search control and the source credit."""
    options = analytics.entity_options()
    return {
        "active": active,
        "countries": options["countries"],
        "aggregates": options["aggregates"],
        "sources": SOURCES,
        "goals": GOALS,
    }


def home(request):
    summary = analytics.home_summary()
    chart_data = {
        "world": {
            "series": [
                {"label": "World", "color": "#0A97D9", "points": summary["world_series"]}
            ],
            "ariaLabel": "World SDG Index score, 2000 to 2022",
        }
    }
    return render(
        request,
        "home.html",
        {**_shell("home"), "summary": summary, "chart_data": chart_data},
    )


def country(request, country_name):
    profile = analytics.country_profile(country_name)
    if profile is None:
        raise Http404(f"No SDG data for {country_name!r}")

    # The canonical spelling lives in the data; redirect if the URL differs.
    if profile["name"] != country_name:
        return redirect("country", country_name=profile["name"], permanent=True)

    series = [
        {"label": profile["name"], "color": "#0A97D9", "points": profile["index_series"]},
    ]
    if profile["region_series"]:
        series.append(
            {
                "label": f"{profile['region_name']} average",
                "color": "#DDA63A",
                "points": profile["region_series"],
                "dashed": True,
            }
        )
    if not profile["is_aggregate"] or profile["name"] != "World":
        series.append(
            {
                "label": "World",
                "color": "#8C97A8",
                "points": profile["world_series"],
                "dashed": True,
            }
        )

    chart_data = {
        "trend": {"series": series, "yLabel": "SDG Index score"},
        "sparklines": {str(goal["number"]): goal["series"] for goal in profile["goals"]},
    }

    return render(
        request,
        "country.html",
        {
            **_shell("country"),
            "profile": profile,
            "chart_data": chart_data,
            "commentary": ai_commentary(profile),
            "news": related_news(profile["name"]),
        },
    )


def search(request):
    """Resolve whatever was typed into the search box to a country page."""
    query = (request.GET.get("q") or "").strip()
    if not query:
        return redirect("home")

    profile = analytics.country_profile(query)
    if profile is not None:
        return redirect("country", country_name=profile["name"])

    options = analytics.entity_options()
    names = options["countries"] + options["aggregates"]
    lowered = {name.casefold(): name for name in names}

    partial = [name for key, name in lowered.items() if query.casefold() in key]
    close = difflib.get_close_matches(query, names, n=6, cutoff=0.5)

    suggestions = list(dict.fromkeys(partial + close))[:8]
    if len(suggestions) == 1:
        return redirect("country", country_name=suggestions[0])

    return render(
        request,
        "no_match.html",
        {**_shell(), "query": query, "suggestions": suggestions},
        status=404,
    )


def info_score(request, country_name):
    """The original URL, kept working."""
    return redirect("country", country_name=country_name, permanent=True)


def goal(request, number):
    detail = analytics.goal_detail(number)
    if detail is None:
        raise Http404(f"There is no SDG {number}")

    chart_data = {
        "trend": {
            "series": [
                {
                    "label": f"World, Goal {number}",
                    "color": detail["goal"]["color"],
                    "points": detail["world_series"],
                }
            ]
        },
        "regions": [
            {"label": row["name"], "value": row["mean"], "color": detail["goal"]["color"]}
            for row in detail["region_means"]
        ],
    }

    return render(
        request,
        "goal.html",
        {**_shell("goals"), "detail": detail, "chart_data": chart_data},
    )


def about(request):
    data = analytics.get_dataset()
    return render(
        request,
        "about.html",
        {
            **_shell("about"),
            "country_count": len(data.countries),
            "aggregate_count": len(data.aggregates),
            "first_year": data.first_year,
            "latest_year": data.latest_year,
            "report_year": analytics.REPORT_YEAR,
        },
    )


def not_found(request, exception=None):
    """404 handler.

    Django's default passes no context, so a template extending base.html
    would render with an empty search list and an empty footer.
    """
    return render(request, "404.html", _shell(), status=404)


def healthz(request):
    """Liveness probe: confirms the CSVs parsed and the site can answer."""
    data = analytics.get_dataset()
    return JsonResponse(
        {
            "status": "ok",
            "countries": len(data.countries),
            "aggregates": len(data.aggregates),
            "years": [data.first_year, data.latest_year],
        }
    )


def country_api(request, country_name):
    """The same profile as JSON, for anyone who wants the numbers directly."""
    profile = analytics.country_profile(country_name)
    if profile is None:
        return JsonResponse({"error": f"No SDG data for {country_name}"}, status=404)
    return JsonResponse(profile)
