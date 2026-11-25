import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import TestCase, override_settings
from django.urls import reverse

from .connectors.common import BoardError
from .connectors.greenhouse import fetch_board
from .offer import Offer
from .models import Criteria


@override_settings(GREENHOUSE_BOARDS={"example": "Ejemplo", "unavailable": "Sin conexión"}, LEVER_BOARDS={})
class SearchTests(TestCase):
    def setUp(self):
        self.url = reverse("search")
        self.criteria = {"keywords": "Python, API", "location": "España", "modality": "all"}

    def test_default_form_and_saved_criteria_survive_new_client(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["form"].initial["location"], "España")
        self.assertEqual(response.context["form"].initial["modality"], "all")
        criteria = self.criteria | {"location": "Bilbao", "modality": "hybrid"}
        with patch("offers.views.greenhouse.fetch_board") as fetch:
            self.assertRedirects(self.client.post(self.url, criteria | {"action": "save"}), self.url)
            fetch.assert_not_called()
        self.assertEqual(Criteria.objects.count(), 1)
        self.assertEqual(self.client_class().get(self.url).context["form"].initial, criteria)

    def test_search_normalizes_matches_and_keeps_results_on_partial_failure(self):
        url = "https://job-boards.greenhouse.io/example/jobs/42"
        jobs = [
            {"title": "Backend Junior", "location": {"name": "Madrid"}, "absolute_url": url,
             "content": "&lt;p&gt;Python y &lt;b&gt;API&lt;/b&gt;&lt;/p&gt;"},
            {"title": "Python Developer", "location": {"name": "Spain (Remote)"}, "absolute_url": url},
            {"title": "Python Engineer", "location": {"name": "Remote – EMEA"}, "absolute_url": url},
            {"title": "Python Specialist", "location": {"name": "Remote"}, "absolute_url": url,
             "content": "You can work from Spain."},
            {"title": "Python Developer Germany", "location": {"name": "Germany (Remote)"}, "absolute_url": url,
             "content": "A separate opening is remote in Spain."},
            {"title": "Python Engineer No Spain", "location": {"name": "Remote – Europe"}, "absolute_url": url,
             "content": "Candidates are eligible throughout Europe, excluding Spain."},
        ]

        for job_id, job in enumerate(jobs[1:], start=43):
            job["absolute_url"] = f"https://job-boards.greenhouse.io/example/jobs/{job_id}"

        def get_board(token, company, timeout):
            if token == "unavailable":
                raise BoardError("Se agotó el tiempo de espera.")
            return fetch_board(token, company, timeout)

        with (
            patch("offers.views.greenhouse.fetch_board", side_effect=get_board),
            patch("offers.connectors.common.urlopen", return_value=io.BytesIO(json.dumps({"jobs": jobs}).encode())) as request,
        ):
            response = self.client.post(self.url, self.criteria | {"action": "search"})

        request.assert_called_once_with(
            "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true", timeout=5
        )
        matches = response.context["matches"]
        self.assertEqual(len(matches), 4)
        self.assertEqual(matches[0].offer.title, "Backend Junior")
        self.assertEqual(matches[0].reason, "Python, API")
        self.assertTrue(matches[-1].pending)
        self.assertContains(response, f'href="{url}" target="_blank" rel="noopener"')
        self.assertContains(response, "Sin conexión")
        self.assertContains(response, "Pendiente de confirmar")
        self.assertEqual(Criteria.objects.get().keywords, "Python, API")

    def test_specific_modality_and_no_matches(self):
        with patch("offers.views.greenhouse.fetch_board", return_value=[
            Offer("Python Developer", "Ejemplo", "Madrid", "Greenhouse", "https://example.org/jobs/1"),
        ]):
            response = self.client.post(self.url, self.criteria | {"modality": "remote", "action": "search"})
        self.assertContains(response, "Ninguna oferta")

    def test_all_boards_fail(self):
        with patch("offers.views.greenhouse.fetch_board", side_effect=BoardError("Servicio no disponible.")):
            response = self.client.post(self.url, self.criteria | {"action": "search"})
        self.assertContains(response, "Vuelve a buscar")
        self.assertNotContains(response, "Ninguna oferta")

    def test_invalid_keywords_do_not_trigger_search(self):
        with patch("offers.views.greenhouse.fetch_board") as fetch:
            response = self.client.post(self.url, self.criteria | {"keywords": ", ,", "action": "search"})
        fetch.assert_not_called()
        self.assertContains(response, "Introduce al menos un término")

@override_settings(GREENHOUSE_BOARDS={"example": "Company A"}, LEVER_BOARDS={"example": ("Company B", "eu")})
class MultiSourceSearchTests(TestCase):
    greenhouse_url = "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true"
    lever_url = "https://api.eu.lever.co/v0/postings/example?mode=json"
    posting_url = "https://careers.example.org/jobs?id=42"

    def setUp(self):
        self.criteria = {"keywords": "Python", "location": "España", "modality": "remote", "action": "search"}
        self.greenhouse_job = {
            "title": "Python Engineer",
            "absolute_url": self.posting_url + "&utm_source=greenhouse",
            "location": {"name": "Madrid (Remote)"},
        }
        self.lever_job = {
            "text": "Backend Engineer",
            "hostedUrl": self.posting_url + "&lever-source=careers#description",
            "categories": {"location": "Milan", "allLocations": ["Milan", "Madrid"]},
            "workplaceType": "remote",
            "country": "IT",
            "lists": [{"text": "Skills", "content": "<li>Python</li>"}],
        }

    def run_search(self, *, greenhouse=None, lever=None, failed_url=None):
        payloads = {
            self.greenhouse_url: {"jobs": [self.greenhouse_job] if greenhouse is None else greenhouse},
            self.lever_url: [self.lever_job] if lever is None else lever,
        }

        def request(url, *, timeout):
            self.assertEqual(timeout, 5)
            if url == failed_url:
                raise HTTPError(url, 503, "Service unavailable", None, None)
            return io.BytesIO(json.dumps(payloads[url]).encode())

        with patch("offers.connectors.common.urlopen", side_effect=request) as fetch:
            response = self.client.post(reverse("search"), self.criteria)
        self.assertEqual({call.args[0] for call in fetch.call_args_list}, {self.greenhouse_url, self.lever_url})
        return response

    def test_shared_filters_and_clear_duplicate(self):
        distinct_job = self.lever_job | {
            "text": self.greenhouse_job["title"],
            "hostedUrl": self.posting_url.replace("42", "43"),
        }
        excluded_job = self.lever_job | {
            "hostedUrl": self.posting_url.replace("42", "44"),
            "workplaceType": "hybrid",
        }
        response = self.run_search(lever=[self.lever_job, distinct_job, excluded_job])
        matches = response.context["matches"]
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].sources, ("Greenhouse", "Lever"))
        self.assertEqual(matches[1].sources, ("Lever",))
        self.assertEqual(matches[1].offer.location, "Milan / Madrid")
        self.assertContains(response, "Greenhouse / Lever")

    def test_one_provider_can_fail_without_losing_the_other(self):
        for failed_url, provider, company, remaining in [
            (self.lever_url, "Lever", "Company B", "Greenhouse"),
            (self.greenhouse_url, "Greenhouse", "Company A", "Lever"),
        ]:
            with self.subTest(provider=provider):
                response = self.run_search(failed_url=failed_url)
                self.assertEqual(response.context["consulted"], 1)
                self.assertEqual(response.context["matches"][0].sources, (remaining,))
                self.assertContains(response, f"{provider} · {company}. El servicio respondió con HTTP 503.")
