from dataclasses import asdict
from uuid import uuid4

from django.db import transaction
from django.utils import formats, timezone

from .matching import posting_identity
from .models import SearchSnapshot, SeenPosting


@transaction.atomic
def save_search(criteria, matches, failures, consulted):
    observed_at = timezone.now()
    search_id = uuid4()
    grouped_keys = [
        (match, {
            posting_identity(url)
            for _, url in match.links
        })
        for match in matches
    ]
    all_keys = {key for _, keys in grouped_keys for key in keys}
    seen = SeenPosting.objects.in_bulk(all_keys)
    new_observations = []
    results = []
    for match, keys in grouped_keys:
        observation = min(
            (seen[key] for key in keys if key in seen),
            key=lambda posting: posting.first_seen_at,
            default=None,
        )
        first_seen = observation.first_seen_at if observation else observed_at
        first_search = observation.first_search if observation else search_id
        new_observations.extend(
            SeenPosting(key=key, first_seen_at=first_seen, first_search=first_search)
            for key in keys if key not in seen
        )
        result = asdict(match)
        del result["offer"]["description"]
        result.update(
            is_new=first_search == search_id,
            first_seen=formats.date_format(timezone.localtime(first_seen), "SHORT_DATE_FORMAT"),
        )
        results.append(result)
    SeenPosting.objects.bulk_create(new_observations, ignore_conflicts=True)
    snapshot = SearchSnapshot(pk=1, data={
        "criteria": [criteria.keywords, criteria.location, criteria.modality],
        "matches": results,
        "failures": failures,
        "consulted": consulted,
    })
    SearchSnapshot.objects.bulk_create(
        [snapshot], update_conflicts=True, update_fields=["data"], unique_fields=["id"],
    )
