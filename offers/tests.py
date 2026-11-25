import io
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .connectors.greenhouse import BoardError, fetch_board
from .offer import Offer
from .models import Criteria


@override_settings(GREENHOUSE_BOARDS={"example": "Ejemplo", "unavailable": "Sin conexión"})
class SearchTests(TestCase):
    def setUp(self):
        self.url = reverse("search")
        self.criteria = {"keywords": "Python, API", "location": "España", "modality": "all"}

    def test_default_form_and_saved_criteria_survive_new_client(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["form"].initial["location"], "España")
        self.assertEqual(response.context["form"].initial["modality"], "all")
        criteria = self.criteria | {"location": "Bilbao", "modality": "hybrid"}
        with patch("offers.views.fetch_board") as fetch:
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

        def get_board(token, company, timeout):
            if token == "unavailable":
                raise BoardError("Se agotó el tiempo de espera.")
            return fetch_board(token, company, timeout)

        with (
            patch("offers.views.fetch_board", side_effect=get_board),
            patch("offers.connectors.greenhouse.urlopen", return_value=io.BytesIO(json.dumps({"jobs": jobs}).encode())) as request,
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
        self.assertContains(response, f'href="{url}"')
        self.assertContains(response, "Sin conexión")
        self.assertContains(response, "Pendiente de confirmar")
        self.assertEqual(Criteria.objects.get().keywords, "Python, API")

    def test_specific_modality_and_no_matches(self):
        with patch("offers.views.fetch_board", return_value=[
            Offer("Python Developer", "Ejemplo", "Madrid", "Greenhouse", "https://example.org/jobs/1"),
        ]):
            response = self.client.post(self.url, self.criteria | {"modality": "remote", "action": "search"})
        self.assertContains(response, "Ninguna oferta")

    def test_all_boards_fail(self):
        with patch("offers.views.fetch_board", side_effect=BoardError("Servicio no disponible.")):
            response = self.client.post(self.url, self.criteria | {"action": "search"})
        self.assertContains(response, "Vuelve a buscar")
        self.assertNotContains(response, "Ninguna oferta")

    def test_invalid_keywords_do_not_trigger_search(self):
        with patch("offers.views.fetch_board") as fetch:
            response = self.client.post(self.url, self.criteria | {"keywords": ", ,", "action": "search"})
        fetch.assert_not_called()
        self.assertContains(response, "Introduce al menos un término")
