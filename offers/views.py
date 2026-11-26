from concurrent.futures import ThreadPoolExecutor
from functools import partial

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .applications import ConflictingApplications, application_links, record_application
from .connectors import greenhouse, lever
from .connectors.common import BoardError
from .forms import CriteriaForm
from .history import save_search
from .matching import find_matches, posting_identity
from .models import Application, ApplicationPosting, ApplicationStatus, Criteria, SearchSnapshot


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
    snapshot = get_object_or_404(SearchSnapshot, pk=1)
    for match in snapshot.data["matches"]:
        if posting_identity(match["offer"]["url"]) == posting:
            try:
                application = record_application(match)
            except ConflictingApplications:
                return HttpResponse("Esta vacante coincide con varias candidaturas guardadas.", status=409)
            return redirect("application_detail", pk=application.pk)
    raise Http404("La oferta ya no está en los resultados de la última búsqueda.")


def application_list(request):
    status = request.GET.get("estado", "")
    applications = Application.objects.order_by("-applied_at", "-pk")
    if status in ApplicationStatus.values:
        applications = applications.filter(status=status)
    else:
        status = ""
    return render(request, "offers/application_list.html", {
        "applications": applications,
        "selected_status": status,
        "statuses": ApplicationStatus.choices,
    })


def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    return render(request, "offers/application_detail.html", {"application": application})
