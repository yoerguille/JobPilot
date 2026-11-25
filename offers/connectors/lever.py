from urllib.parse import quote

from ..offer import Offer
from .common import as_text, fetch_json, html_to_text, is_posting_url, validate_postings

API_HOSTS = {"global": "api.lever.co", "eu": "api.eu.lever.co"}
WORKPLACE_TYPES = {"on-site": "onsite", "remote": "remote", "hybrid": "hybrid"}


def fetch_board(token, company, region, timeout):
    endpoint = f"https://{API_HOSTS[region]}/v0/postings/{quote(token, safe='')}?mode=json"
    jobs = validate_postings(fetch_json(endpoint, timeout))

    offers = []
    for job in jobs:
        title, url = as_text(job.get("text")), as_text(job.get("hostedUrl"))
        if not title or not is_posting_url(url):
            continue
        categories = job.get("categories")
        categories = categories if isinstance(categories, dict) else {}
        primary = as_text(categories.get("location"))
        locations = categories.get("allLocations")
        locations = locations if isinstance(locations, list) else []
        location = " / ".join(dict.fromkeys(filter(None, [primary, *map(as_text, locations)])))

        sections = job.get("lists")
        sections = sections if isinstance(sections, list) else []
        description = " ".join(filter(None, [
            as_text(job.get("descriptionPlain")) or html_to_text(job.get("description")),
            *(html_to_text(section.get("content")) for section in sections if isinstance(section, dict)),
            as_text(job.get("additionalPlain")) or html_to_text(job.get("additional")),
        ]))
        offers.append(Offer(
            title=title,
            company=company,
            location=location,
            source="Lever",
            url=url,
            description=description,
            modality=WORKPLACE_TYPES.get(as_text(job.get("workplaceType")), ""),
            country_code=as_text(job.get("country")).upper(),
        ))
    return offers
