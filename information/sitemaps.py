from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from . import analytics
from .constant import GOALS


class StaticViewSitemap(Sitemap):
    """Sitemap for static/fixed site pages like Home and About."""

    def items(self):
        return ["home", "about"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "home" else 0.8

    def changefreq(self, item):
        return "weekly" if item == "home" else "monthly"


class GoalSitemap(Sitemap):
    """Sitemap for the 17 SDG goal pages."""

    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return [goal["number"] for goal in GOALS]

    def location(self, item):
        return reverse("goal", kwargs={"number": item})


class CountrySitemap(Sitemap):
    """Sitemap for individual country profile pages."""

    changefreq = "monthly"
    priority = 0.9

    def items(self):
        return analytics.get_dataset().countries

    def location(self, item):
        return reverse("country", kwargs={"country_name": item})


class AggregateSitemap(Sitemap):
    """Sitemap for regional and income aggregate pages (World, OECD members, etc.)."""

    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return analytics.get_dataset().aggregates

    def location(self, item):
        return reverse("country", kwargs={"country_name": item})


sitemaps = {
    "static": StaticViewSitemap,
    "goals": GoalSitemap,
    "countries": CountrySitemap,
    "aggregates": AggregateSitemap,
}
