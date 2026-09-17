"""Contracts for external data, freshness, and retaining observations on failure."""
from datetime import datetime, timezone
from unittest.mock import patch

from django.core.cache import caches
from django.test import SimpleTestCase, override_settings
import requests

from . import live_data


LIVE_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "test-default"},
    "live_data": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "test-sdg-sources"},
}


def series(*, area="IDN", years=None, values=None, **dimensions):
    return {
        "DATABASE_ID": "UN_SDG", "INDICATOR": "UN_SDG_SH_STA_MAL", "REF_AREA": area,
        "SEX": "_T", "AGE": "_T", "URBANISATION": "_T", "COMP_BREAKDOWN_1": "UN_SDG_MAL_WAS",
        "COMP_BREAKDOWN_2": "_Z", "COMP_BREAKDOWN_3": "_Z", "UNIT_MEASURE": "PT_POP_Y_LE5",
        "UNIT_MULT": 0, "data": {"xAxis": years or ["2021", "2023", "2024"],
                                 "yAxis": values if values is not None else ["2", "0", None]},
        **dimensions,
    }


class ObservationTests(SimpleTestCase):
    def test_latest_nonmissing_year_keeps_zero(self):
        result = live_data._observations([series()], live_data.INDICATORS[0])
        self.assertEqual(result["observations"]["IDN"], {"value": 0.0, "year": 2023})

    def test_years_are_compared_numerically_not_by_response_order(self):
        result = live_data._observations([
            series(years=["2024", "2020", "2023"], values=["4", "1", "2"])
        ], live_data.INDICATORS[0])
        self.assertEqual(result["observations"]["IDN"], {"value": 4.0, "year": 2024})

    def test_disaggregations_units_and_nonfinite_values_cannot_replace_totals(self):
        rows = [series(), series(SEX="F", values=["70", "80", "90"]),
                series(COMP_BREAKDOWN_1="UN_SDG_MAL_OWT", values=["70", "80", "90"]),
                series(UNIT_MULT=3, values=["70", "80", "90"]),
                series(UNIT_MEASURE="NUMBER", values=["70", "80", "90"]),
                series(values=["NaN", "Infinity", "<2.5"])]
        result = live_data._observations(rows, live_data.INDICATORS[0])
        self.assertEqual(result["observations"]["IDN"], {"value": 0.0, "year": 2023})

    def test_empty_invalid_or_conflicting_results_do_not_replace_saved_data(self):
        for payload in [[], {"error": "unavailable"}, [None],
                        [series(data=None)], [series(data={"xAxis": "2024", "yAxis": "1234"})],
                        [series(years=["2024"], values=["2", "3"])],
                        [series(), series(values=["2", "3", None])]]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                live_data._observations(payload, live_data.INDICATORS[0])

    @patch("information.live_data.requests.get")
    def test_portal_response_accepts_the_real_utf8_bom(self, get):
        get.return_value.content = b'\xef\xbb\xbf[{"data": {"xAxis": [], "yAxis": []}}]'
        self.assertEqual(live_data._json_get("https://example.com"), [{"data": {"xAxis": [], "yAxis": []}}])
        get.return_value.raise_for_status.assert_called_once()

    @patch("information.live_data._json_get")
    def test_hub_routes_come_from_public_slugs(self, get):
        get.return_value = {"results": [
            {"title": "Ignore management page", "typeKeywords": []},
            {"title": "Ignore invalid route", "typeKeywords": ["slug|sdg|../private"]},
            {"title": "A geographic resource", "modified": 1767225600000,
             "typeKeywords": ["slug|sdg|geographic-resource"], "url": "javascript:alert(1)"},
        ]}
        self.assertEqual(live_data._fetch_hubs()["items"], [{
            "title": "A geographic resource", "modified": "2026-01-01",
            "url": "https://www.sdg.org/pages/geographic-resource",
        }])


@override_settings(CACHES=LIVE_CACHES, SDG_REFRESH_SECONDS=86400)
class SourceRefreshTests(SimpleTestCase):
    def setUp(self):
        caches["live_data"].clear()
        self.now = datetime.now(timezone.utc).timestamp()
        observations = {"observations": {"IDN": {"value": 0, "year": 2023}},
                        "latest_year": 2023, "earliest_year": 2023}
        self.snapshot = {
            key: {"data": data, "fetched_at": self.now - 100, "retry_at": self.now + 86400}
            for key, data in {
                "world_bank": {"published_at": "2026-09-01"},
                "hubs": {"items": [{"title": "SDG", "url": "https://www.sdg.org/", "modified": "2026-01-01"}]},
                **{indicator["id"]: observations for indicator in live_data.INDICATORS},
            }.items()
        }
        caches["live_data"].set("sources-v1", self.snapshot, None)

    def tearDown(self):
        caches["live_data"].clear()

    @patch("information.live_data.requests.get")
    def test_fresh_cache_and_initial_html_never_fetch_sources(self, get):
        result = live_data.landing_sources(refresh=True)
        self.assertTrue(all(item["status"] == "fresh" for item in result["indicators"]))
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2023 report")
        self.assertContains(response, "UN SDG")
        get.assert_not_called()

    @patch("information.live_data._fetch_indicator")
    def test_only_expired_source_refreshes(self, fetch):
        self.snapshot["wasting"]["retry_at"] = self.now - 1
        caches["live_data"].set("sources-v1", self.snapshot, None)
        fetch.return_value = {"observations": {"IDN": {"value": 4.2, "year": 2024}}, "latest_year": 2024}
        result = live_data.landing_sources(refresh=True)
        fetch.assert_called_once_with(live_data.INDICATORS[0])
        self.assertEqual(result["indicators"][0]["observations"]["IDN"]["year"], 2024)
        self.assertEqual(result["indicators"][0]["status"], "fresh")

    @patch("information.live_data._fetch_indicator", side_effect=requests.Timeout("timeout"))
    def test_failure_preserves_values_and_retrieval_date_then_backs_off(self, fetch):
        self.snapshot["wasting"]["retry_at"] = self.now - 1
        original = self.snapshot["wasting"]["fetched_at"]
        caches["live_data"].set("sources-v1", self.snapshot, None)
        result = live_data.landing_sources(refresh=True)["indicators"][0]
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["observations"]["IDN"]["value"], 0)
        self.assertEqual(datetime.fromisoformat(result["fetched_at"]).timestamp(), original)
        live_data.landing_sources(refresh=True)
        fetch.assert_called_once()

    @patch("information.live_data.requests.get", side_effect=requests.Timeout("timeout"))
    def test_first_run_failure_has_no_invented_observations(self, get):
        caches["live_data"].set("sources-v1", {}, None)
        result = live_data.landing_sources(refresh=True)
        self.assertTrue(all(row["status"] == "unavailable" for row in result["indicators"]))
        self.assertTrue(all(row["observations"] == {} for row in result["indicators"]))

    @patch("information.live_data._fetch_indicator", side_effect=ValueError("malformed upstream data"))
    def test_malformed_update_keeps_last_success(self, fetch):
        self.snapshot["wasting"]["retry_at"] = self.now - 1
        caches["live_data"].set("sources-v1", self.snapshot, None)
        result = live_data.landing_sources(refresh=True)
        self.assertEqual(result["indicators"][0]["status"], "stale")
        self.assertEqual(result["indicators"][0]["latest_year"], 2023)

    def test_source_api_is_read_only_and_returns_freshness(self):
        response = self.client.get("/api/sources/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response.json()["indicators"][0]["status"], "fresh")
        self.assertEqual(self.client.post("/api/sources/").status_code, 405)
