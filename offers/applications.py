from django.db import transaction

from .matching import posting_identity
from .models import Application, ApplicationPosting, ApplicationStatus, ApplicationStatusEvent


class ConflictingApplications(Exception):
    pass


def application_links(match):
    offer = match["offer"]
    return match.get("links") or [(offer["source"], offer["url"])]


@transaction.atomic
def record_application(match):
    """Save an applied posting from a search snapshot and register all known URLs."""
    offer = match["offer"]
    links = application_links(match)
    keys = {posting_identity(url) for _, url in links}
    known = ApplicationPosting.objects.in_bulk(keys)
    application_ids = {posting.application_id for posting in known.values()}
    if len(application_ids) > 1:
        raise ConflictingApplications("The posting links belong to different applications.")

    if application_ids:
        application = Application.objects.get(pk=application_ids.pop())
        original_links = list(dict.fromkeys(tuple(link) for link in [*application.original_links, *links]))
        if len(original_links) != len(application.original_links):
            application.original_links = original_links
            application.save(update_fields=["original_links"])
    else:
        application = Application.objects.create(
            title=offer["title"],
            company=offer["company"],
            location=offer["location"],
            original_links=links,
        )
        application.status_history.create(status=application.status, occurred_at=application.applied_at)

    ApplicationPosting.objects.bulk_create([
        ApplicationPosting(key=key, application=application) for key in keys - known.keys()
    ])
    return application


@transaction.atomic
def change_application_status(application_id, status):
    status = ApplicationStatus(status)
    updated = Application.objects.filter(pk=application_id).exclude(status=status).update(status=status)
    if updated:
        ApplicationStatusEvent.objects.create(application_id=application_id, status=status)
