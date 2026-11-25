import json
import re
from html import unescape
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

from django.utils.html import strip_tags


class BoardError(Exception):
    pass


def fetch_json(endpoint, timeout):
    try:
        with urlopen(endpoint, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        raise BoardError(f"El servicio respondió con HTTP {error.code}.") from error
    except OSError as error:
        raise BoardError("No se pudo conectar o se agotó el tiempo de espera.") from error
    except ValueError as error:
        raise BoardError("La respuesta del servicio no tiene el formato esperado.") from error


def validate_postings(postings):
    if not isinstance(postings, list) or any(not isinstance(posting, dict) for posting in postings):
        raise BoardError("La respuesta del servicio no tiene el formato esperado.")
    return postings


def is_posting_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme in {"https", "http"}
            and bool(parsed.hostname)
            and parsed.username is None
            and (parsed.port is None or parsed.port > 0)
        )
    except ValueError:
        return False


def as_text(value):
    return value.strip() if isinstance(value, str) else ""


def html_to_text(value):
    return unescape(strip_tags(re.sub(r"<[^>]+>", " ", unescape(as_text(value)))))
