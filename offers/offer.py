from dataclasses import dataclass


@dataclass(frozen=True)
class Offer:
    title: str
    company: str
    location: str
    source: str
    url: str
    description: str = ""
