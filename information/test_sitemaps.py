from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

from django.test import SimpleTestCase
from django.urls import reverse

from . import analytics, live_data
from .constant import GOALS


NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def entries(response):
    return {
        unquote(urlparse(row.find("s:loc", NS).text).path): row.find("s:lastmod", NS).text
        for row in ET.fromstring(response.content).findall("s:url", NS)
    }


class SitemapTests(SimpleTestCase):
    def test_all_canonical_pages_are_in_valid_xml(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertIn("no-cache", response["Cache-Control"])
        rows = entries(response)
        self.assertEqual(len(rows), 2 + len(analytics.get_dataset().entities) + len(GOALS))
        for name in analytics.get_dataset().entities:
            self.assertIn(unquote(reverse("country", args=[name])), rows)
        for goal in GOALS:
            self.assertIn(reverse("goal", args=[goal["number"]]), rows)
        self.assertNotIn("/country/south korea/", rows)
        self.assertFalse(any(path.startswith(("/api/", "/search/", "/info_score/")) for path in rows))
        self.assertTrue(all(datetime.fromisoformat(value) for value in rows.values()))

    @patch("information.live_data.requests.get")
    def test_sitemap_requires_no_network_and_is_stable_between_reads(self, get):
        first = entries(self.client.get("/sitemap.xml"))
        second = entries(self.client.get("/sitemap.xml"))
        self.assertEqual(first, second)
        get.assert_not_called()

    @patch("information.sitemaps.analytics.get_dataset")
    def test_new_profiles_are_discovered_without_a_sitemap_rebuild(self, dataset):
        dataset.return_value = SimpleNamespace(entities=["A New Country", "World"])
        response = self.client.get("/sitemap.xml")
        self.assertIn("/country/A New Country/", entries(response))
        self.assertIn("/country/World/", entries(response))
        self.assertNotIn("/country/Finland/", entries(response))

    @patch("information.sitemaps.landing_sources")
    def test_source_content_changes_advance_only_landing_lastmod(self, sources):
        changed = datetime.now(timezone.utc) + timedelta(days=1)
        sources.return_value = {"world_bank": {"changed_at": changed.isoformat()}, "hubs": {}, "indicators": []}
        first = entries(self.client.get("/sitemap.xml"))
        changed += timedelta(days=1)
        sources.return_value["world_bank"]["changed_at"] = changed.isoformat()
        second = entries(self.client.get("/sitemap.xml"))
        self.assertGreater(second["/"], first["/"])
        self.assertEqual(second["/country/Indonesia/"], first["/country/Indonesia/"])
        self.assertEqual(second["/goal/2/"], first["/goal/2/"])

    def test_robots_discovers_sitemap_on_request_origin(self):
        response = self.client.get("/robots.txt", secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sitemap: https://testserver/sitemap.xml", html=False)
        self.assertContains(response, "Disallow: /admin/", html=False)
        xml = ET.fromstring(self.client.get("/sitemap.xml", secure=True).content)
        self.assertTrue(all(node.text.startswith("https://testserver/") for node in xml.findall("s:url/s:loc", NS)))

    def test_repeat_source_checks_do_not_invent_a_new_content_date(self):
        previous = {"data": {"published_at": "2026-09-01"}, "fetched_at": 100, "changed_at": 90}
        _, result = live_data._refresh_one("world_bank", lambda: {"published_at": "2026-09-01"}, previous, 200)
        self.assertEqual(result["changed_at"], 90)
        self.assertEqual(result["fetched_at"], 200)
        _, changed = live_data._refresh_one("world_bank", lambda: {"published_at": "2026-10-01"}, result, 300)
        self.assertEqual(changed["changed_at"], 300)
