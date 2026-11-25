import re
import unicodedata
from dataclasses import dataclass, replace
from urllib.parse import parse_qsl, urlsplit

from .offer import Offer

SPAIN = (
    "España", "Spain", "Madrid", "Barcelona", "Valencia", "Sevilla", "Seville", "Málaga",
    "Bilbao", "Alicante", "Granada", "Zaragoza", "Murcia", "Palma", "Vigo", "A Coruña",
    "Oviedo", "Santander", "Valladolid", "Pamplona", "Girona", "Tarragona", "Cádiz",
    "Córdoba", "Gijón", "Salamanca", "San Sebastián", "Canarias", "Canary Islands", "Tenerife",
    "Las Palmas", "Cataluña", "Catalonia", "Andalucía", "Galicia", "Basque Country", "País Vasco",
)
REMOTE = r"\b(?:remote|remot[oa]|teletrabajo)\b"
HYBRID = r"\b(?:hybrid|hibrid[oa])\b"
ONSITE = r"\b(?:on[ -]?site|presencial|in[ -]office)\b"
BROAD_REMOTE = r"\b(?:emea|europe|europa|eu|european union|worldwide|anywhere|global|international|internacional|mundial)\b"
REMOTE_LABEL = r"\b(?:fully|100|work|from|anywhere|worldwide|based|trabajo|desde|todo el mundo|position|role)\b"
COUNTRY_CODE = r"(?:\(es\)|,\s*es$|\bes[- ]remote\b|\bremote[- ]es\b)"


@dataclass(frozen=True)
class Match:
    offer: Offer
    reason: str
    geography: str
    modality: str
    pending: bool
    priority: int
    sources: tuple[str, ...]


def normalize(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def contains(term, value):
    pattern = re.escape(normalize(term))
    return bool(re.search(rf"(?<!\w){pattern}(?!\w)", value))


def modality_of(title, location, description):
    for value in (location, title):
        for modality, pattern in (("hybrid", HYBRID), ("onsite", ONSITE), ("remote", REMOTE)):
            if re.search(pattern, value):
                return modality
    if re.search(rf"{HYBRID}\s+(?:work|role|position|model|working|schedule|de trabajo)", description):
        return "hybrid"
    if re.search(rf"(?:{REMOTE_LABEL}\s+{REMOTE}|{REMOTE}\s+{REMOTE_LABEL})", description):
        return "remote"
    if re.search(rf"{ONSITE}\s+(?:role|position|only|en oficina)", description):
        return "onsite"
    return "unknown"


def geography_of(location, description, modality, region, country_code):
    spanish_scope = normalize(region) in {"espana", "spain", "es"}
    aliases = SPAIN if spanish_scope else (region,)
    places = "|".join(re.escape(normalize(place)) for place in aliases)
    target = rf"(?<!\w)(?:{places})(?!\w)"
    if modality == "remote" and re.search(
        rf"\b(?:excluding|except|excluye|excepto)\s+(?:candidates (?:in|from)\s+)?{target}"
        rf"|\b{target}\s+(?:is excluded|is not eligible|no es elegible)\b",
        f"{location} {description}",
    ):
        return None
    if re.search(target, location) or (spanish_scope and (country_code == "ES" or location == "es" or re.search(COUNTRY_CODE, location))):
        return f"Ubicación indicada en {region}", False
    if modality != "remote":
        return None

    # Other concrete locations in the listing take precedence over shared
    # descriptions that may also advertise separate openings in Spain.
    rest = re.sub(rf"{REMOTE}|{BROAD_REMOTE}|\b(?:fully|100|work from|anywhere|only)\b", "", location)
    broad = re.search(BROAD_REMOTE, location)
    if re.search(r"\w", rest) and not broad:
        return None
    if re.search(
        rf"\b(?:based in|located in|work from|remote (?:in|from)|remot[oa] (?:en|desde)"
        rf"|trabajar desde|ubicad[oa] en|eligible countries include)\s+{target}",
        description,
    ):
        return f"El anuncio indica que se puede trabajar desde {region}", False
    if re.search(r"\b(?:worldwide|anywhere in the world|todo el mundo)\b", location):
        return "Remota mundial según la ubicación del anuncio", False

    return f"Pendiente de confirmar si admite trabajar desde {region}", True


def find_matches(offers, criteria):
    terms = [term.strip() for term in criteria.keywords.split(",") if term.strip()]
    results = []
    labels = {"remote": "Remota", "hybrid": "Híbrida", "onsite": "Presencial", "unknown": "Modalidad sin indicar"}
    for offer in offers:
        title, location, description = map(normalize, (offer.title, offer.location, offer.description))
        title_hits = [term for term in terms if contains(term, title)]
        hits = [term for term in terms if term in title_hits or contains(term, description)]
        if not hits:
            continue
        modality = offer.modality or modality_of(title, location, description)
        if criteria.modality not in {"all", modality}:
            continue
        geography = geography_of(location, description, modality, criteria.location, offer.country_code)
        if geography is None:
            continue
        geography_label, pending = geography
        priority = (
            2 * len(title_hits) + len(hits)
            + 2 * bool(re.search(r"\b(?:junior|jr)\b", title))
            - 2 * bool(re.search(r"\b(?:senior|staff|principal|lead|manager|director)\b", title))
        )
        results.append(Match(offer, ", ".join(hits), geography_label, labels[modality], pending, priority, (offer.source,)))
    results.sort(key=lambda match: (match.pending, -match.priority, match.offer.title.casefold()))

    unique = {}
    for match in results:
        key = posting_key(match.offer.url)
        existing = unique.get(key)
        if existing is None:
            unique[key] = match
        elif match.offer.source not in existing.sources:
            unique[key] = replace(existing, sources=(*existing.sources, match.offer.source))
    return list(unique.values())


def posting_key(url):
    parsed = urlsplit(url)
    default_port = 443 if parsed.scheme == "https" else 80
    port = None if parsed.port == default_port else parsed.port
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"gh_src", "lever-source"}
    ]
    return parsed.scheme, parsed.hostname, port, parsed.path, tuple(sorted(query, key=lambda item: item[0]))
