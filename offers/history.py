import json
from dataclasses import asdict
from hashlib import sha256
from uuid import uuid4

from django.db import transaction
from django.utils import formats, timezone

from .matching import posting_key
from .models import SearchSnapshot, SeenPosting


@transaction.atomic
def save_search(criteria, matches, failures, consulted):
    observed_at = timezone.now()
    search_id = uuid4()
    by_key = {
        sha256(json.dumps(posting_key(match.offer.url)).encode()).hexdigest(): match
        for match in matches
    }
    SeenPosting.objects.bulk_create([
        SeenPosting(key=key, first_seen_at=observed_at, first_search=search_id)
        for key in by_key
    ], ignore_conflicts=True)
    seen = SeenPosting.objects.in_bulk(by_key)
    results = []
    for key, match in by_key.items():
        observation = seen[key]
        result = asdict(match)
        del result["offer"]["description"]
        result.update(
            is_new=observation.first_search == search_id,
            first_seen=formats.date_format(timezone.localtime(observation.first_seen_at), "SHORT_DATE_FORMAT"),
        )
        results.append(result)
    snapshot = SearchSnapshot(pk=1, data={
        "criteria": [criteria.keywords, criteria.location, criteria.modality],
        "matches": results,
        "failures": failures,
        "consulted": consulted,
    })
    SearchSnapshot.objects.bulk_create(
        [snapshot], update_conflicts=True, update_fields=["data"], unique_fields=["id"],
    )
