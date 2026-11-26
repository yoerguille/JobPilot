from urllib.parse import quote

from ..offer import Offer
from .common import as_text, fetch_json, html_to_text, is_posting_url, validate_postings


def fetch_board(token, company, timeout):
    endpoint = f"https://boards-api.greenhouse.io/v1/boards/{quote(token, safe='')}/jobs?content=true"
    payload = fetch_json(endpoint, timeout)
    jobs = validate_postings(payload.get("jobs") if isinstance(payload, dict) else None)

    offers = []
    for job in jobs:
        title, url = as_text(job.get("title")), as_text(job.get("absolute_url"))
        if not title or not is_posting_url(url):
            continue
        location = job.get("location")
        location = as_text(location.get("name")) if isinstance(location, dict) else ""
        reference = job.get("requisition_id")
        offers.append(Offer(
            title, company, location, "Greenhouse", url, html_to_text(job.get("content")),
            vacancy_reference=str(reference).strip() if type(reference) in (int, str) else "",
        ))
    return offers
