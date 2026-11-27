from concurrent.futures import ThreadPoolExecutor
from functools import partial

from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .applications import (
    ConflictingApplications, application_links, change_application_status, mark_application_submitted,
    record_application,
)
from .connectors import greenhouse, lever
from .connectors.common import BoardError
from .cv import CVOfferDraftForm, get_or_create_cv_version
from .cv_ai import CVGenerationError, CVGenerationForm, CVTextForm, generate_cv_text, text_sections
from .forms import ApplicationStatusForm, CriteriaForm, SentCVVersionForm
from .history import save_search
from .matching import find_matches, posting_identity
from .models import (
    Application, ApplicationPosting, ApplicationStatus, Criteria, CVOfferDraft, CVProfile, CVVersion, SearchSnapshot,
)


def search(request):
    criteria = Criteria.objects.filter(pk=1).first() or Criteria(pk=1)
    form = CriteriaForm(request.POST if request.method == "POST" else None, instance=criteria)
    boards = [
        ("Greenhouse", company, partial(greenhouse.fetch_board, token, company, settings.GREENHOUSE_TIMEOUT))
        for token, company in settings.GREENHOUSE_BOARDS.items()
    ] + [
        ("Lever", company, partial(lever.fetch_board, token, company, region, settings.LEVER_TIMEOUT))
        for token, (company, region) in settings.LEVER_BOARDS.items()
    ]
    source_companies = {}
    for source, company, _ in boards:
        source_companies.setdefault(source, []).append(company)
    context = {"form": form, "source_companies": source_companies}

    if request.method != "POST":
        snapshot = SearchSnapshot.objects.filter(pk=1).first()
        if snapshot and snapshot.data["criteria"] == [criteria.keywords, criteria.location, criteria.modality]:
            result_filter = request.GET.get("resultados", "todas")
            if result_filter not in {"todas", "nuevas", "anteriores"}:
                result_filter = "todas"
            results = snapshot.data["matches"]
            new_count = sum(result["is_new"] for result in results)
            visible = results if result_filter == "todas" else [
                result for result in results if result["is_new"] == (result_filter == "nuevas")
            ]
            keyed_results = [
                (result, {posting_identity(url) for _, url in application_links(result)})
                for result in visible
            ]
            known = ApplicationPosting.objects.in_bulk({key for _, keys in keyed_results for key in keys})
            for result, keys in keyed_results:
                result["posting_identity"] = posting_identity(result["offer"]["url"])
                result["application_ids"] = sorted({known[key].application_id for key in keys if key in known})
            context.update(
                searched=True,
                matches=visible,
                result_filter=result_filter,
                total_count=len(results),
                new_count=new_count,
                previous_count=len(results) - new_count,
                failures=snapshot.data["failures"],
                consulted=snapshot.data["consulted"],
            )
        return render(request, "offers/search.html", context)
    if not form.is_valid():
        return render(request, "offers/search.html", context)

    criteria = form.save()
    if request.POST.get("action") == "save":
        return redirect("search")

    offers, failures = [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        requests = [(source, company, executor.submit(fetch)) for source, company, fetch in boards]
        for source, company, result in requests:
            try:
                offers.extend(result.result())
            except BoardError as error:
                failures.append((source, company, str(error)))

    save_search(criteria, find_matches(offers, criteria), failures, len(boards) - len(failures))
    return redirect("search")


@require_POST
def mark_application(request, posting):
    return save_search_application(posting, interested=False)


@require_POST
def save_interested_offer(request, posting):
    return save_search_application(posting, interested=True)


def save_search_application(posting, *, interested):
    snapshot = get_object_or_404(SearchSnapshot, pk=1)
    for match in snapshot.data["matches"]:
        if posting_identity(match["offer"]["url"]) == posting:
            try:
                application = record_application(match, interested=interested)
            except ConflictingApplications:
                return HttpResponse("Esta vacante coincide con varias candidaturas guardadas.", status=409)
            if interested and application.status == ApplicationStatus.INTERESTED:
                return redirect("pending_applications")
            return redirect("application_detail", pk=application.pk)
    raise Http404("La oferta ya no está en los resultados de la última búsqueda.")


def application_list(request):
    status = request.GET.get("estado", "")
    statuses = ApplicationStatus.submitted_choices()
    applications = Application.objects.exclude(status=ApplicationStatus.INTERESTED).order_by("-applied_at", "-pk")
    if status in dict(statuses):
        applications = applications.filter(status=status)
    else:
        status = ""
    return render(request, "offers/application_list.html", {
        "applications": applications,
        "selected_status": status,
        "statuses": statuses,
    })


def pending_applications(request):
    return render(request, "offers/application_list.html", {
        "applications": Application.objects.filter(status=ApplicationStatus.INTERESTED).order_by("-pk"),
        "pending": True,
    })


def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    post_data = request.POST if request.method == "POST" else None
    action = post_data.get("action") if post_data is not None else None
    if application.status == ApplicationStatus.INTERESTED:
        return pending_application_detail(request, application, post_data, action)

    if action == "mark_applied":
        return redirect("application_detail", pk=pk)

    updating_cv = action == "save_cv_version"
    form = ApplicationStatusForm(
        None if updating_cv else post_data,
        initial={"status": application.status},
    )
    cv_form = SentCVVersionForm(post_data if updating_cv else None, application=application)
    if updating_cv and cv_form.is_valid():
        application.sent_cv_version = cv_form.cleaned_data["sent_cv_version"]
        application.save(update_fields=["sent_cv_version"])
        return redirect("application_detail", pk=application.pk)

    if form.is_valid():
        change_application_status(application.pk, form.cleaned_data["status"])
        if request.POST.get("return_to") == "application_list":
            status_filter = request.POST.get("estado", "")
            query = {"estado": status_filter} if status_filter in dict(ApplicationStatus.submitted_choices()) else None
            return redirect(reverse("application_list", query=query))
        return redirect("application_detail", pk=application.pk)

    return render(request, "offers/application_detail.html", {
        "application": application,
        "status_form": form,
        "cv_form": cv_form,
        "has_cv_versions": cv_form.fields["sent_cv_version"].queryset.exists(),
    })


def pending_application_detail(request, application, post_data, action):
    if action == "mark_applied":
        mark_application_submitted(application.pk)
        return redirect("application_detail", pk=application.pk)

    snapshot = application.offer_snapshot
    profile = CVProfile.objects.filter(pk=1).first()
    context = {"application": application, "pending": True}
    if profile is not None:
        prepared = None
        if application.prepared_cv_version_id:
            prepared = CVVersion.objects.only("content").get(pk=application.prepared_cv_version_id).content
        ai_content = prepared if prepared and "text_sections" in prepared else None
        generation = CVGenerationForm(
            post_data if action == "generate_ai_cv" else None,
            initial={"language": (
                post_data.get("language") if action in {"preview_ai_cv", "save_ai_cv"}
                else ai_content["language"] if ai_content else ""
            )},
        )
        context["generation_form"] = generation
        editor = None
        if action in {"preview_ai_cv", "save_ai_cv"}:
            editor = CVTextForm(post_data)
            if editor.is_valid():
                content = editor.content(profile)
                if action == "save_ai_cv":
                    return save_prepared_cv(application, content)
                context.update(content, cv_sections=text_sections(content), show_preview=True)
        elif ai_content:
            editor = CVTextForm(initial=ai_content["text_sections"] | {
                "headline": ai_content["profile"]["headline"], "cv_language": ai_content["language"],
            })
        if action == "generate_ai_cv":
            if post_data.get("cv_language"):
                editor = CVTextForm(post_data)
            if generation.is_valid():
                try:
                    generated = generate_cv_text(profile, application, generation.cleaned_data["language"])
                except CVGenerationError as error:
                    generation.add_error(None, str(error))
                else:
                    editor = CVTextForm(initial=generated)
        context["text_form"] = editor

        editing = action in {"preview_cv", "save_prepared_cv"}
        draft_form = CVOfferDraftForm(
            post_data if editing else None, profile, {"title": application.title, **snapshot},
        )
        if prepared and not ai_content:
            draft_form.load_selection(prepared)
        elif not prepared:
            draft = CVOfferDraft.objects.filter(pk=snapshot["posting_key"]).first()
            if draft:
                draft_form.load_selection(draft.content)
        selection = draft_form.initial
        if draft_form.is_valid():
            selection = draft_form.cleaned_data
            if action == "save_prepared_cv":
                return save_prepared_cv(application, draft_form.content(profile, selection))
        context["draft_form"] = draft_form
        context["manual_editing"] = editing
        if action == "preview_cv" and not draft_form.errors:
            context.update(draft_form.content(profile, selection), show_preview=True)
    return render(request, "offers/application_detail.html", context)


def save_prepared_cv(application, content):
    with transaction.atomic():
        version = get_or_create_cv_version(
            application.offer_snapshot["posting_key"], application.title, application.company, content,
        )
        updated = Application.objects.filter(pk=application.pk, status=ApplicationStatus.INTERESTED).update(
            prepared_cv_version=version,
        )
        if not updated:
            transaction.set_rollback(True)
    return redirect(reverse("application_detail", args=[application.pk]) + "#cv")
