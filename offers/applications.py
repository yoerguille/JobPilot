from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .matching import posting_identity
from .models import Application, ApplicationPosting, ApplicationStatus, ApplicationStatusEvent


class ConflictingApplications(Exception):
    pass


def application_links(match):
    offer = match["offer"]
    return match.get("links") or [(offer["source"], offer["url"])]


@transaction.atomic
def record_application(match, *, interested=False):
    """Save a posting from a search snapshot and register all known URLs."""
    offer = match["offer"]
    links = application_links(match)
    keys = {posting_identity(url) for _, url in links}
    known = ApplicationPosting.objects.in_bulk(keys)
    application_ids = {posting.application_id for posting in known.values()}
    if len(application_ids) > 1:
        raise ConflictingApplications("The posting links belong to different applications.")

    snapshot = {
        "posting_key": posting_identity(offer["url"]),
        "description": offer.get("description", ""),
        "modality": match.get("modality", ""),
        "geography": match.get("geography", ""),
        "experience": match.get("experience", ""),
    }
    if application_ids:
        application = Application.objects.get(pk=application_ids.pop())
        original_links = list(dict.fromkeys(tuple(link) for link in [*application.original_links, *links]))
        if len(original_links) != len(application.original_links):
            application.original_links = original_links
            application.save(update_fields=["original_links"])
        if not application.offer_snapshot:
            application.offer_snapshot = snapshot
            application.save(update_fields=["offer_snapshot"])
    else:
        application = Application.objects.create(
            title=offer["title"],
            company=offer["company"],
            location=offer["location"],
            original_links=links,
            offer_snapshot=snapshot,
            status=ApplicationStatus.INTERESTED if interested else ApplicationStatus.APPLIED,
            applied_at=None if interested else timezone.now(),
        )
        if application.applied_at:
            application.status_history.create(status=application.status, occurred_at=application.applied_at)

    ApplicationPosting.objects.bulk_create([
        ApplicationPosting(key=key, application=application) for key in keys - known.keys()
    ])
    return application


@transaction.atomic
def mark_application_submitted(application_id):
    applied_at = timezone.now()
    updated = Application.objects.filter(pk=application_id, status=ApplicationStatus.INTERESTED).update(
        status=ApplicationStatus.APPLIED, applied_at=applied_at, sent_cv_version=F("prepared_cv_version"),
    )
    if updated:
        ApplicationStatusEvent.objects.create(
            application_id=application_id, status=ApplicationStatus.APPLIED, occurred_at=applied_at,
        )


@transaction.atomic
def change_application_status(application_id, status):
    status = ApplicationStatus(status)
    if status == ApplicationStatus.INTERESTED:
        return
    updated = Application.objects.filter(pk=application_id).exclude(
        status__in=[status, ApplicationStatus.INTERESTED],
    ).update(status=status)
    if updated:
        ApplicationStatusEvent.objects.create(application_id=application_id, status=status)
