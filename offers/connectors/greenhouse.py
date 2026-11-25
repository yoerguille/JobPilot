import json
import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import urlopen

from django.utils.html import strip_tags

from ..offer import Offer


class BoardError(Exception):
    pass


def fetch_board(token, company, timeout):
    endpoint = f"https://boards-api.greenhouse.io/v1/boards/{quote(token, safe='')}/jobs?content=true"
    try:
        with urlopen(endpoint, timeout=timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError("Invalid jobs response")
    except HTTPError as error:
        raise BoardError(f"Greenhouse respondió con HTTP {error.code}.") from error
    except (OSError, URLError) as error:
        raise BoardError("No se pudo conectar o se agotó el tiempo de espera.") from error
    except ValueError as error:
        raise BoardError("La respuesta de Greenhouse no tiene el formato esperado.") from error

    offers = []
    for job in payload["jobs"]:
        if not isinstance(job, dict):
            raise BoardError("La respuesta contiene un anuncio con formato inesperado.")
        location = job.get("location")
        location = location.get("name") if isinstance(location, dict) else None
        url, title = job.get("absolute_url"), job.get("title")
        if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
            continue
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            continue
        content = job.get("content")
        description = unescape(strip_tags(re.sub(r"<[^>]+>", " ", unescape(content)))) if isinstance(content, str) else ""
        offers.append(Offer(title, company, location if isinstance(location, str) else "", "Greenhouse", url, description))
    return offers
