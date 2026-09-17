"""Regression tests.

The expected values here were computed directly from the CSVs. They exist so
that a change to the data layer that quietly alters a published figure fails
loudly, and so the two data traps described in ``analytics`` stay fixed.

Run with:  python manage.py test information
"""

from unittest.mock import MagicMock, patch
from urllib.parse import unquote

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from . import analytics
from .constant import GOALS


class DatasetShapeTests(SimpleTestCase):

    def setUp(self):
        self.data = analytics.get_dataset()

    def test_entity_counts(self):
        self.assertEqual(len(self.data.countries), 166)
        self.assertEqual(len(self.data.aggregates), 14)
        self.assertEqual(len(self.data.entities), 180)

    def test_year_coverage(self):
        self.assertEqual(self.data.first_year, 2000)
        self.assertEqual(self.data.latest_year, 2022)
        self.assertEqual(self.data.baseline_year, 2015)
        self.assertEqual(len(self.data.years), 23)
        self.assertEqual(len(self.data.index), 180 * 23)

    def test_aggregates_never_enter_a_ranking(self):
        for name in self.data.aggregates:
            self.assertNotIn(name, self.data.ranked.index)
        self.assertEqual(len(self.data.ranked), 166)

    def test_goal_assessment_counts(self):
        self.assertEqual(self.data.counted["goal_1_score"], 151)
        self.assertEqual(self.data.counted["goal_10_score"], 149)
        self.assertEqual(self.data.counted["goal_14_score"], 126)
        for goal in GOALS:
            if goal["number"] not in {1, 10, 14}:
                self.assertEqual(self.data.counted[f"goal_{goal['number']}_score"], 166)

    def test_region_counts(self):
        self.assertEqual(
            self.data.region_counts,
            {
                "OECD": 38,
                "E. Europe & C. Asia": 23,
                "LAC": 23,
                "East & South Asia": 19,
                "MENA": 16,
                "Oceania": 2,
                "Sub-Saharan Africa": 45,
            },
        )


class MissingDataTests(SimpleTestCase):
    """Missing must never be read as zero, and zero must never be read as missing."""

    def setUp(self):
        self.data = analytics.get_dataset()

    def test_not_assessed_series_is_masked(self):
        # Goal 14 is not assessed for landlocked countries.
        series = self.data.series("Austria", "goal_14_score")
        self.assertEqual(len(series), 23)
        self.assertTrue(all(point["value"] is None for point in series))

    def test_genuine_zero_series_is_preserved(self):
        # These two sit on an all-zero series but the 2023 report scores them
        # 0.0, so they are real results, not gaps.
        for country, column in [("Burundi", "goal_1_score"), ("Qatar", "goal_13_score")]:
            series = self.data.series(country, column)
            self.assertTrue(
                all(point["value"] == 0.0 for point in series),
                f"{country} {column} should be a real zero series",
            )

    def test_genuine_zero_scores_render_as_zero(self):
        for country, number in [
            ("Malawi", 1),
            ("Burundi", 1),
            ("South Sudan", 1),
            ("South Africa", 10),
            ("Qatar", 13),
        ]:
            profile = analytics.country_profile(country)
            goal = next(g for g in profile["goals"] if g["number"] == number)
            self.assertTrue(goal["assessed"], f"{country} goal {number} must be assessed")
            self.assertEqual(goal["score"], 0.0)

    def test_not_assessed_goals_are_flagged(self):
        profile = analytics.country_profile("Austria")
        self.assertEqual([g["number"] for g in profile["not_assessed"]], [14])
        self.assertEqual(profile["goals_assessed"], 16)

    def test_goal_14_gap_is_explained(self):
        detail = analytics.goal_detail(14)
        self.assertEqual(len(detail["not_assessed"]), 40)
        self.assertTrue(detail["not_applicable"])


class PublishedValueTests(SimpleTestCase):
    """Figures the site displays must match the published data exactly."""

    def test_top_and_bottom_of_the_table(self):
        summary = analytics.home_summary()
        self.assertEqual(
            [(row["rank"], row["country"], row["score"]) for row in summary["top"][:3]],
            [(1, "Finland", 86.8), (2, "Sweden", 86.0), (3, "Denmark", 85.7)],
        )
        self.assertEqual(summary["bottom"][-1]["country"], "South Sudan")
        self.assertEqual(summary["bottom"][-1]["rank"], 166)

    def test_scores_are_rounded_not_truncated(self):
        # Finland's Goal 1 score is 99.575: int() would show 99.
        profile = analytics.country_profile("Finland")
        goal_one = next(g for g in profile["goals"] if g["number"] == 1)
        self.assertEqual(goal_one["score"], 99.6)

    def test_country_headline(self):
        profile = analytics.country_profile("Indonesia")
        self.assertEqual(profile["snapshot"]["score"], 70.2)
        self.assertEqual(profile["snapshot"]["rank"], 75)
        self.assertEqual(profile["snapshot"]["of"], 166)
        self.assertEqual(profile["region_name"], "East & South Asia")

    def test_world_series(self):
        summary = analytics.home_summary()
        self.assertEqual(summary["world_score"], 66.7)
        self.assertEqual(summary["world_baseline_score"], 63.8)
        self.assertEqual(summary["world_change_since_baseline"], 2.9)
        self.assertEqual(summary["world_change"], 7.6)

    def test_world_goes_backwards_on_two_goals_since_2015(self):
        summary = analytics.home_summary()
        self.assertEqual(
            [(g["number"], g["change_since_baseline"]) for g in summary["world_goals_backwards"]],
            [(16, -1.6), (15, -0.3)],
        )

    def test_movers_since_the_goals_were_adopted(self):
        summary = analytics.home_summary()
        self.assertEqual(
            [(row["country"], row["change"]) for row in summary["improved"][:3]],
            [("Cote d'Ivoire", 7.7), ("Afghanistan", 7.4), ("Benin", 7.3)],
        )
        self.assertEqual(summary["declined"][0]["change"], -1.4)

    def test_region_average_is_not_the_published_aggregate(self):
        summary = analytics.home_summary()
        oceania = next(row for row in summary["regions"] if row["name"] == "Oceania")
        self.assertEqual(oceania["mean"], 63.2)
        self.assertEqual(oceania["published"], 52.7)


class NameResolutionTests(SimpleTestCase):
    def setUp(self):
        self.data = analytics.get_dataset()

    def test_everyday_names_resolve(self):
        cases = {
            "south korea": "Korea, Rep.",
            "Turkey": "Türkiye",
            "ivory coast": "Cote d'Ivoire",
            "Côte d’Ivoire": "Cote d'Ivoire",
            "USA": "United States",
            "dr congo": "Congo, Dem. Rep.",
            "russia": "Russian Federation",
            "czech republic": "Czechia",
        }
        for typed, expected in cases.items():
            self.assertEqual(self.data.resolve(typed), expected, typed)

    def test_country_codes_resolve(self):
        self.assertEqual(self.data.resolve("IDN"), "Indonesia")
        self.assertEqual(self.data.resolve("_World"), "World")

    def test_unknown_names_do_not_resolve(self):
        self.assertIsNone(self.data.resolve("Atlantis"))
        self.assertIsNone(analytics.country_profile("Atlantis"))


@override_settings(SECURE_SSL_REDIRECT=False)
@patch.dict("os.environ", {"OPENROUTER_API_KEY": "", "NEWS_API_KEY": ""}, clear=False)
class PageTests(TestCase):
    """Every page must render with no API keys configured."""

    def test_core_pages(self):
        for path in ["/", "/about/", "/healthz"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b"Traceback", response.content)

    def test_every_goal_page(self):
        for goal in GOALS:
            with self.subTest(goal=goal["number"]):
                response = self.client.get(f"/goal/{goal['number']}/")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, goal["title"])

    def test_awkward_country_names(self):
        for name in [
            "Finland",
            "Austria",
            "World",
            "Türkiye",
            "Congo, Dem. Rep.",
            "Cote d'Ivoire",
            "Bahamas, The",
            "Lower & Lower-middle Income",
        ]:
            with self.subTest(name=name):
                response = self.client.get(f"/country/{name}/")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b"None%", response.content)

    def test_every_entity_renders(self):
        data = analytics.get_dataset()
        for name in data.entities:
            response = self.client.get(f"/country/{name}/")
            self.assertEqual(response.status_code, 200, name)

    def test_unknown_country_is_a_404(self):
        response = self.client.get("/country/Atlantis/")
        self.assertEqual(response.status_code, 404)

    def test_404_page_renders_the_full_shell(self):
        # Django's default 404 handler passes no context, which would leave the
        # search list and the footer empty.
        with self.settings(DEBUG=False):
            response = self.client.get("/country/Atlantis/")
        self.assertEqual(response.status_code, 404)
        body = response.content.decode()
        self.assertIn("Sustainable Development Report 2023", body)
        self.assertIn("Partnerships for the Goals", body)
        self.assertIn('value="Indonesia"', body)

    def test_unknown_goal_is_a_404(self):
        self.assertEqual(self.client.get("/goal/18/").status_code, 404)
        self.assertEqual(self.client.get("/goal/0/").status_code, 404)

    def test_search_redirects_to_the_canonical_name(self):
        response = self.client.get("/search/", {"q": "south korea"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(unquote(response["Location"]), "/country/Korea, Rep./")

    def test_search_offers_suggestions_when_nothing_matches(self):
        response = self.client.get("/search/", {"q": "Atlantis"})
        self.assertEqual(response.status_code, 404)

    def test_original_url_still_works(self):
        response = self.client.get("/info_score/Kenya")
        self.assertEqual(response.status_code, 301)

    def test_json_api(self):
        response = self.client.get("/api/country/Indonesia/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["name"], "Indonesia")
        self.assertEqual(len(payload["goals"]), 17)
        # Missing values must be null in the payload, never zero.
        austria = self.client.get("/api/country/Austria/").json()
        goal_14 = next(g for g in austria["goals"] if g["number"] == 14)
        self.assertIsNone(goal_14["score"])
        self.assertTrue(all(point["value"] is None for point in goal_14["series"]))


class OptionalServiceTests(SimpleTestCase):
    """The extras must stay silent rather than break a page."""

    def tearDown(self):
        cache.clear()

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "", "NEWS_API_KEY": ""}, clear=False)
    def test_no_keys_means_no_extras(self):
        from . import services

        profile = analytics.country_profile("Kenya")
        self.assertIsNone(services.ai_commentary(profile))
        self.assertEqual(services.related_news("Kenya"), [])

    @patch.dict(
        "os.environ",
        {
            "OPENROUTER_API_KEY": "sk-or-test12345",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_MODEL": "google/gemini-2.0-flash-001",
        },
        clear=False,
    )
    @patch("openai.OpenAI")
    def test_openrouter_commentary_success(self, mock_openai_cls):
        from . import services

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Kenya has shown solid progress on several SDGs."
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        profile = analytics.country_profile("Kenya")
        result = services.ai_commentary(profile)

        self.assertEqual(result, "Kenya has shown solid progress on several SDGs.")
        mock_openai_cls.assert_called_once_with(
            api_key="sk-or-test12345",
            base_url="https://openrouter.ai/api/v1",
            timeout=8.0,
        )
        mock_client.chat.completions.create.assert_called_once()
        create_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs["model"], "google/gemini-2.0-flash-001")
        self.assertEqual(create_kwargs["temperature"], 0.4)
        self.assertEqual(create_kwargs["top_p"], 0.95)
        self.assertEqual(create_kwargs["max_tokens"], 512)

    @patch.dict(
        "os.environ",
        {
            "OPENROUTER_API_KEY": "sk-or-test",
            "OPENROUTER_BASE_URL": "https://custom.openrouter.ai/v1",
            "OPENROUTER_MODEL": "meta-llama/llama-3.3-70b-instruct",
        },
    )
    @patch("openai.OpenAI")
    def test_openrouter_custom_config(self, mock_openai_cls):
        from . import services

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Custom model output."
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        profile = analytics.country_profile("Kenya")
        result = services.ai_commentary(profile)

        self.assertEqual(result, "Custom model output.")
        mock_openai_cls.assert_called_once_with(
            api_key="sk-or-test",
            base_url="https://custom.openrouter.ai/v1",
            timeout=8.0,
        )
        create_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs["model"], "meta-llama/llama-3.3-70b-instruct")

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"})
    @patch("openai.OpenAI")
    def test_openrouter_api_error_returns_none(self, mock_openai_cls):
        from . import services

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("API Rate Limit")

        profile = analytics.country_profile("Kenya")
        result = services.ai_commentary(profile)

        self.assertIsNone(result)


@override_settings(SECURE_SSL_REDIRECT=False)
class SeoTests(SimpleTestCase):
    """Tests for robots.txt and sitemap.xml SEO configurations."""

    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        content = response.content.decode("utf-8")
        self.assertIn("User-agent: *", content)
        self.assertIn("Allow: /", content)
        self.assertIn("Disallow: /admin/", content)
        self.assertIn("Disallow: /search/", content)
        self.assertIn("Disallow: /api/", content)
        self.assertIn("Disallow: /healthz", content)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", content)

    def test_sitemap_xml(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        content = response.content.decode("utf-8")
        self.assertIn("<loc>http://testserver/</loc>", content)
        self.assertIn("<loc>http://testserver/about/</loc>", content)
        self.assertIn("<loc>http://testserver/goal/1/</loc>", content)
        self.assertIn("<loc>http://testserver/goal/17/</loc>", content)
        self.assertIn("<loc>http://testserver/country/Finland/</loc>", content)
        self.assertIn("<loc>http://testserver/country/World/</loc>", content)
        # Total URLs: 2 static + 17 goals + 166 countries + 14 aggregates = 199
        self.assertEqual(content.count("<url>"), 199)

    def test_https_urls_behind_the_proxy(self):
        # In production a TLS proxy forwards https and the SEO files must
        # advertise https URLs, or search engines would be told to crawl http.
        with override_settings(
            SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https")
        ):
            sitemap = self.client.get(
                "/sitemap.xml",
                HTTP_X_FORWARDED_PROTO="https",
                SERVER_NAME="sdg.nevatal.id",
                SERVER_PORT=443,
            )
            robots = self.client.get(
                "/robots.txt",
                HTTP_X_FORWARDED_PROTO="https",
                SERVER_NAME="sdg.nevatal.id",
                SERVER_PORT=443,
            )
        self.assertIn(b"<loc>https://sdg.nevatal.id/</loc>", sitemap.content)
        self.assertNotIn(b"<loc>http://", sitemap.content)
        self.assertIn(b"Sitemap: https://sdg.nevatal.id/sitemap.xml", robots.content)


