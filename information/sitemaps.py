"""Generate canonical page URLs from the same data used to render the site."""
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.utils.functional import cached_property
from django.urls import reverse

from . import analytics
from .constant import GOALS
from .live_data import landing_sources


def _modified(*paths):
    return max(datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc) for path in paths)


class ProfileSitemap(Sitemap):
    def items(self):
        # No static country list: new profiles and goals appear automatically.
        return [
            ("home", None),
            ("about", None),
            *(("country", name) for name in analytics.get_dataset().entities),
            *(("goal", goal["number"]) for goal in GOALS),
        ]

    def location(self, item):
        name, value = item
        return reverse(name, args=[value] if value is not None else [])

    @cached_property
    def modified(self):
        app = settings.BASE_DIR / "information"
        templates = app / "templates"
        shared = _modified(templates / "base.html", app / "constant.py", app / "analytics.py")
        reports = _modified(analytics.REPORT_FILE, analytics.INDEX_FILE)
        dates = {
            name: max(shared, reports, _modified(templates / f"{name}.html"))
            for name in ("home", "about", "country", "goal")
        }
        sources = landing_sources()  # Reads the last successful snapshot; no network call.
        for source in [sources["world_bank"], sources["hubs"], *sources["indicators"]]:
            if source.get("changed_at"):
                dates["home"] = max(dates["home"], datetime.fromisoformat(source["changed_at"]))
        return dates

    def lastmod(self, item):
        return self.modified[item[0]]

    def changefreq(self, item):
        return "daily" if item[0] == "home" else "monthly"


sitemaps = {
    "profiles": ProfileSitemap,
}
