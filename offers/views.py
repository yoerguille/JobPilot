from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.shortcuts import redirect, render

from .connectors.greenhouse import BoardError, fetch_board
from .forms import CriteriaForm
from .matching import find_matches
from .models import Criteria


def search(request):
    criteria = Criteria.objects.filter(pk=1).first() or Criteria(pk=1)
    form = CriteriaForm(request.POST if request.method == "POST" else None, instance=criteria)
    context = {"form": form, "companies": list(settings.GREENHOUSE_BOARDS.values())}
    if request.method != "POST" or not form.is_valid():
        return render(request, "offers/search.html", context)

    criteria = form.save()
    if request.POST.get("action") == "save":
        return redirect("search")

    offers, failures = [], []
    boards = settings.GREENHOUSE_BOARDS
    with ThreadPoolExecutor(max_workers=5) as executor:
        requests = [
            (company, executor.submit(fetch_board, token, company, settings.GREENHOUSE_TIMEOUT))
            for token, company in boards.items()
        ]
        for company, result in requests:
            try:
                offers.extend(result.result())
            except BoardError as error:
                failures.append((company, str(error)))

    context.update(
        searched=True,
        matches=find_matches(offers, criteria),
        failures=failures,
        consulted=len(boards) - len(failures),
    )
    return render(request, "offers/search.html", context)
