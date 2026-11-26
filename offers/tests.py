import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import TestCase, override_settings
from django.urls import reverse

from .applications import record_application
from .connectors.common import BoardError
from .connectors.greenhouse import fetch_board
from .experience import experience_of
from .matching import normalize
from .models import Criteria, SeenPosting
from .offer import Offer


class ApplicationTrackingTests(TestCase):
    def test_records_application_and_recognizes_grouped_posting_links(self):
        original = "https://careers.example.org/jobs/42"
        alternative = "https://jobs.lever.co/example/backend"
        offer = {
            "title": "Backend Developer", "company": "Example", "location": "Madrid",
            "source": "Greenhouse", "url": original,
        }
        application = record_application({"offer": offer})
        grouped = record_application({
            "offer": offer,
            "links": [["Greenhouse", original], ["Lever", alternative]],
        })
        alias = record_application({
            "offer": offer | {"source": "Lever", "url": alternative + "?utm_source=feed"},
        })

        self.assertEqual(grouped.pk, application.pk)
        self.assertEqual(alias.pk, application.pk)
        application.refresh_from_db()
        self.assertIn(["Lever", alternative], application.original_links)
        event = application.status_history.get()
        self.assertEqual(application.status, "applied")
        self.assertEqual(event.status, application.status)
        self.assertEqual(event.occurred_at, application.applied_at)


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
            response = self.client.post(self.url, self.criteria | {"action": "search"}, follow=True)

        request.assert_called_once_with(
            "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true", timeout=5
        )
        matches = response.context["matches"]
        self.assertEqual(len(matches), 4)
        self.assertEqual(matches[0]["offer"]["title"], "Backend Junior")
        self.assertEqual(matches[0]["reason"], "Python, API")
        self.assertTrue(matches[-1]["pending"])
        self.assertContains(response, f'href="{url}" target="_blank" rel="noopener"')
        self.assertContains(response, "Sin conexión")
        self.assertContains(response, "Pendiente de confirmar")
        self.assertEqual(Criteria.objects.get().keywords, "Python, API")

    def test_specific_modality_and_no_matches(self):
        with patch("offers.views.greenhouse.fetch_board", return_value=[
            Offer("Python Developer", "Ejemplo", "Madrid", "Greenhouse", "https://example.org/jobs/1"),
        ]):
            response = self.client.post(self.url, self.criteria | {"modality": "remote", "action": "search"}, follow=True)
        self.assertContains(response, "Ninguna oferta")

    def test_all_boards_fail(self):
        with patch("offers.views.greenhouse.fetch_board", side_effect=BoardError("Servicio no disponible.")):
            response = self.client.post(self.url, self.criteria | {"action": "search"}, follow=True)
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
            response = self.client.post(reverse("search"), self.criteria, follow=True)
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
        self.assertEqual(matches[0]["sources"], ["Greenhouse", "Lever"])
        self.assertEqual(matches[1]["sources"], ["Lever"])
        self.assertEqual(matches[1]["offer"]["location"], "Milan / Madrid")
        self.assertContains(response, "Greenhouse / Lever")

    def test_one_provider_can_fail_without_losing_the_other(self):
        for failed_url, provider, company, remaining in [
            (self.lever_url, "Lever", "Company B", "Greenhouse"),
            (self.greenhouse_url, "Greenhouse", "Company A", "Lever"),
        ]:
            with self.subTest(provider=provider):
                response = self.run_search(failed_url=failed_url)
                self.assertEqual(response.context["consulted"], 1)
                self.assertEqual(response.context["matches"][0]["sources"], [remaining])
                self.assertContains(response, f"{provider} · {company}. El servicio respondió con HTTP 503.")

    @override_settings(LEVER_BOARDS={"example": ("Company A", "eu")})
    def test_cross_source_duplicate_keeps_both_links_and_history(self):
        description = (
            "Build Python APIs for our payments platform. Maintain integrations with banking providers "
            "and improve the reliability of transaction processing. Work with the backend team to "
            "review changes and monitor production performance during weekly releases."
        )
        greenhouse = self.greenhouse_job | {"content": description}
        lever = self.lever_job | {
            "text": greenhouse["title"],
            "hostedUrl": "https://jobs.lever.co/example/payments",
            "categories": {"location": "Madrid (Remote)"},
            "country": "ES",
            "descriptionPlain": description.replace("improve", "increase"),
            "lists": [],
        }
        distinct = lever | {
            "hostedUrl": "https://jobs.lever.co/example/analytics",
            "descriptionPlain": description.replace("payments platform", "analytics suite").replace(
                "banking providers", "advertising partners"
            ),
        }
        first = self.run_search(greenhouse=[greenhouse], lever=[])
        self.assertEqual(first.context["new_count"], 1)
        grouped = self.run_search(greenhouse=[greenhouse], lever=[lever, distinct])
        self.assertEqual(grouped.context["total_count"], 2)
        self.assertEqual(grouped.context["previous_count"], 1)
        self.assertContains(grouped, "Ver anuncio original en Greenhouse")
        self.assertContains(grouped, "Ver anuncio original en Lever")
        self.assertContains(grouped, lever["hostedUrl"])
        lever_only = self.run_search(greenhouse=[], lever=[lever])
        self.assertEqual(lever_only.context["previous_count"], 1)

    def test_matching_vacancy_references_group_distinct_posting_urls(self):
        first = self.greenhouse_job | {"requisition_id": "PAY-42"}
        duplicate = first | {"absolute_url": self.posting_url.replace("42", "43")}
        distinct = first | {"absolute_url": self.posting_url.replace("42", "44"), "requisition_id": "PAY-44"}
        response = self.run_search(greenhouse=[first, duplicate, distinct], lever=[])
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["matches"][0]["links"], [
            ["Greenhouse", first["absolute_url"]],
            ["Greenhouse", duplicate["absolute_url"]],
        ])

    def test_history_survives_partial_failure_and_refresh_does_not_search(self):
        extra = self.lever_job | {"hostedUrl": self.posting_url.replace("42", "99"), "text": "Python Developer"}
        first_response = self.run_search(lever=[self.lever_job, extra])
        self.assertEqual(first_response.context["new_count"], 2)
        first_seen = dict(SeenPosting.objects.values_list("key", "first_seen_at"))

        partial = self.run_search(failed_url=self.lever_url)
        self.assertEqual(partial.context["new_count"], 0)
        self.assertEqual(partial.context["previous_count"], 1)
        self.assertEqual(dict(SeenPosting.objects.values_list("key", "first_seen_at")), first_seen)

        added = self.greenhouse_job | {"absolute_url": self.posting_url.replace("42", "100")}
        resumed = self.run_search(greenhouse=[self.greenhouse_job, added], lever=[self.lever_job, extra])
        self.assertEqual(resumed.context["new_count"], 1)
        self.assertContains(resumed, "Vista por primera vez")

        with patch("offers.connectors.common.urlopen") as fetch:
            fresh_client = self.client_class()
            new = fresh_client.get(reverse("search"), {"resultados": "nuevas"})
            previous = fresh_client.get(reverse("search"), {"resultados": "anteriores"})
            refreshed = fresh_client.get(reverse("search"))
            fetch.assert_not_called()
        self.assertEqual(len(new.context["matches"]), 1)
        self.assertTrue(new.context["matches"][0]["is_new"])
        self.assertEqual(len(previous.context["matches"]), 2)
        self.assertTrue(all(not item["is_new"] for item in previous.context["matches"]))
        self.assertEqual(refreshed.context["matches"], resumed.context["matches"])
        self.assertEqual(SeenPosting.objects.count(), 3)

    def test_graduates_title_receives_junior_priority(self):
        graduate_job = self.lever_job | {
            "text": "Math, Physics & Engineering Graduates",
            "hostedUrl": self.posting_url.replace("42", "43"),
        }
        response = self.run_search(lever=[graduate_job])
        matches = response.context["matches"]
        self.assertEqual(matches[0]["offer"]["title"], graduate_job["text"])
        self.assertEqual(matches[0]["ranking_reason"], "perfil junior en el título")
        self.assertGreater(matches[0]["priority"], matches[1]["priority"])

    def test_experience_labels_junior_ranking_and_senior_exclusion(self):
        senior = self.greenhouse_job | {
            "title": "Senior Backend Python Engineer",
            "absolute_url": self.posting_url.replace("42", "43"),
            "content": "5 years of professional experience with APIs.",
        }
        ambiguous = self.greenhouse_job | {
            "title": "Python Developer",
            "absolute_url": self.posting_url.replace("42", "44"),
            "content": "Ideally 2–3 years of experience.",
        }
        junior = self.greenhouse_job | {
            "title": "Junior Python Developer",
            "absolute_url": self.posting_url.replace("42", "45"),
            "content": "2–3 years of experience with APIs.",
        }
        response = self.run_search(greenhouse=[senior, ambiguous, junior], lever=[])
        self.assertEqual(response.context["matches"][0]["offer"]["title"], "Junior Python Developer")
        self.assertContains(response, "Experiencia indicada: 2–3 años")
        self.assertNotContains(response, senior["title"])
        self.assertContains(response, "Experiencia en años por confirmar")
        self.assertContains(response, "perfil junior en el título")

    def test_experience_wording(self):
        for description, expected, preferred in [
            ("At least 3 years of experience.", "Experiencia indicada: 3 años o más", True),
            ("Dos años de experiencia.", "Experiencia indicada: 2 años", True),
            ("3–5 years of experience.", "Experiencia indicada: 3–5 años", False),
            ("Python experience is a plus.", "Experiencia en años sin indicar", False),
            ("No 2 years of experience required.", "Experiencia en años por confirmar", False),
            ("Preferred qualifications: 3 years of experience.", "Experiencia en años por confirmar", False),
            ("2.5 years of experience.", "Experiencia en años por confirmar", False),
            ("2 years of experience. 5 years of professional experience with Python.", "Experiencia en años por confirmar", False),
        ]:
            with self.subTest(description=description):
                result = experience_of(normalize(description))
                self.assertEqual((result.label, result.preferred_range), (expected, preferred))
