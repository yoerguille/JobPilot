from concurrent.futures import ThreadPoolExecutor
from functools import partial

from django.conf import settings
from django.shortcuts import redirect, render

from .connectors import greenhouse, lever
from .connectors.common import BoardError
from .forms import CriteriaForm
from .matching import find_matches
from .models import Criteria


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

    if request.method != "POST" or not form.is_valid():
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

    context.update(
        searched=True,
        matches=find_matches(offers, criteria),
        failures=failures,
        consulted=len(boards) - len(failures),
    )
    return render(request, "offers/search.html", context)
