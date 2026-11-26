import re
from dataclasses import dataclass

NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "un": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
}
NUMBER = rf"(?:\d{{1,2}}(?:[.,]\d+)?|{'|'.join(NUMBERS)})"
QUANTIFIED = re.compile(
    rf"\b(?P<minimum>at least|minimum(?: of)?|al menos|minimo(?: de)?)?\s*"
    rf"(?P<low>{NUMBER})(?:(?:\s*(?:[-–—]|to|a|or|o)\s*)(?P<high>{NUMBER})"
    rf"|(?P<plus>\s*\+))?\s*"
    r"(?:years?\b(?:\s+of)?(?:\s+(?:professional|relevant|hands-on|commercial|software|engineering|work|industry)){0,3}\s+experience\b"
    r"|anos?\b\s+de\s+experiencia\b)"
)
UNCERTAIN = re.compile(
    r"\b(?:preferred|nice to have|ideally|around|approximately|desirable|optional|up to|"
    r"about|more than|less than|no|not|without|idealmente|deseable|opcional|"
    r"aproximadamente|unos|hasta|mas de|menos de|sin)\b"
)
OPTIONAL_HEADING = re.compile(
    r"\b(?:preferred(?: qualifications)?|nice to have|deseable|requisitos deseables)\s*:\s*$"
)
EXPERIENCE_MENTION = re.compile(
    r"\b(?:years?\b[^\n.;:!?]{0,40}\bexperience|anos?\b[^\n.;:!?]{0,40}\bexperiencia)\b"
)


@dataclass(frozen=True)
class Experience:
    label: str
    preferred_range: bool = False


def parse_years(value):
    return NUMBERS[value] if value in NUMBERS else int(value)


def experience_of(description):
    requirements = set()
    ambiguous = False
    for match in QUANTIFIED.finditer(description):
        prefix = description[max(0, match.start() - 40):match.start()]
        before = re.split(r"[\n.;:!?]", prefix)[-1]
        after = re.split(r"[\n.;:!?]", description[match.end():match.end() + 30])[0]
        low, high = match.group("low", "high")
        if (
            UNCERTAIN.search(f"{before} {after}")
            or OPTIONAL_HEADING.search(prefix)
            or re.search(r"\bor\b|\bo\b", match.group())
            or any(value and re.search(r"[.,]", value) for value in (low, high))
        ):
            ambiguous = True
            continue
        minimum = parse_years(low)
        maximum = parse_years(high) if high else None
        if maximum is not None and (minimum > maximum or match.group("minimum")):
            ambiguous = True
            continue
        requirements.add((minimum, maximum, bool(match.group("minimum") or match.group("plus"))))

    if ambiguous or len(requirements) > 1 or (not requirements and EXPERIENCE_MENTION.search(description)):
        return Experience("Experiencia en años por confirmar")
    if not requirements:
        return Experience("Experiencia en años sin indicar")

    minimum, maximum, lower_bound = requirements.pop()
    if maximum is not None:
        label = f"{minimum}–{maximum} años"
    elif lower_bound:
        label = f"{minimum} {'año' if minimum == 1 else 'años'} o más"
    else:
        label = f"{minimum} {'año' if minimum == 1 else 'años'}"
    return Experience(
        f"Experiencia indicada: {label}",
        minimum in {2, 3} and maximum in {None, 2, 3},
    )
