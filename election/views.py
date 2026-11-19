"""Public election views. Existing Bincom tables remain unchanged."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import NewPollingUnitResultsForm
from .models import AnnouncedPuResult, Lga, Party, PollingUnit, Ward


def _reporting_unit_ids():
    """IDs are stored as strings in AnnouncedPuResult, integers in PollingUnit."""
    raw_ids = AnnouncedPuResult.objects.values_list(
        "polling_unit_uniqueid", flat=True
    ).distinct()
    return {int(value) for value in raw_ids if value and value.isdecimal()}


def _lga_names():
    """The original schema uses external Lga.lga_id for polling units."""
    return dict(Lga.objects.values_list("lga_id", "lga_name"))


def dashboard(request):
    reported_ids = _reporting_unit_ids()
    lga_names = _lga_names()

    recent_units = list(
        PollingUnit.objects.filter(uniqueid__in=reported_ids)
        .order_by("-uniqueid")[:5]
    )
    for unit in recent_units:
        unit.display_lga = lga_names.get(unit.lga_id, "LGA not recorded")

    return render(request, "election/dashboard.html", {
        "lga_count": Lga.objects.count(),
        "ward_count": Ward.objects.count(),
        "polling_unit_count": PollingUnit.objects.count(),
        "reporting_count": len(reported_ids),
        "recent_units": recent_units,
    })


def polling_units(request):
    """Question 1 discovery: search for a unit instead of guessing an ID."""
    query = request.GET.get("q", "").strip()[:80]
    lga_filter = request.GET.get("lga", "").strip()
    scope = request.GET.get("scope", "reported")
    if scope not in {"reported", "all"}:
        scope = "reported"

    reporting_ids = _reporting_unit_ids()
    units = PollingUnit.objects.all()

    if scope == "reported":
        units = units.filter(uniqueid__in=reporting_ids)

    if lga_filter.isdecimal():
        selected_lga = Lga.objects.filter(uniqueid=int(lga_filter)).first()
        if selected_lga:
            units = units.filter(lga_id=selected_lga.lga_id)
        else:
            lga_filter = ""
    else:
        lga_filter = ""

    if query:
        match = Q(polling_unit_name__icontains=query) | Q(
            polling_unit_number__icontains=query
        )
        if query.isdecimal():
            match |= Q(uniqueid=int(query))
        units = units.filter(match)

    unit_count = units.count()
    page = Paginator(units.order_by("uniqueid"), 12).get_page(
        request.GET.get("page")
    )

    lga_names = _lga_names()
    for unit in page.object_list:
        unit.display_lga = lga_names.get(unit.lga_id, "LGA not recorded")
        unit.has_results = unit.uniqueid in reporting_ids

    return render(request, "election/polling_units.html", {
        "page_obj": page,
        "unit_count": unit_count,
        "query": query,
        "lga_filter": lga_filter,
        "scope": scope,
        "lgas": Lga.objects.order_by("lga_name"),
    })


def polling_result(request, unit_id):
    poll_unit = get_object_or_404(PollingUnit, uniqueid=unit_id)
    results = list(
        AnnouncedPuResult.objects.filter(
            polling_unit_uniqueid=str(poll_unit.uniqueid)
        ).order_by("party_abbreviation", "result_id")
    )

    selected_lga = Lga.objects.filter(lga_id=poll_unit.lga_id).first()
    ward = Ward.objects.filter(uniqueid=poll_unit.uniquewardid).first()
    # Historical rows occasionally contradict their referenced ward.
    if ward and (ward.lga_id != poll_unit.lga_id or ward.ward_id != poll_unit.ward_id):
        ward = None

    return render(request, "election/poll_results.html", {
        "polling_unit": poll_unit,
        "poll_results": results,
        "selected_lga": selected_lga,
        "ward": ward,
        "total_votes": sum(r.party_score for r in results),
        "entry_count": len(results),
        "party_count": len({r.party_abbreviation for r in results}),
    })


def lga_result(request):
    """Question 2: derive LGA totals from polling-unit results, never LGA totals."""
    lgas = Lga.objects.all().order_by("lga_name")
    context = {"lgas": lgas}

    lga_name = request.GET.get("lga")
    if lga_name:
        lga = get_object_or_404(Lga, lga_name=lga_name)
        ids = list(
            PollingUnit.objects.filter(lga_id=lga.lga_id)
            .values_list("uniqueid", flat=True)
        )
        result_rows = AnnouncedPuResult.objects.filter(
            polling_unit_uniqueid__in=[str(pk) for pk in ids]
        )
        totals = list(
            result_rows.values("party_abbreviation")
            .annotate(total_votes=Sum("party_score"))
            .order_by("-total_votes", "party_abbreviation")
        )
        total_votes = sum(item["total_votes"] or 0 for item in totals)
        for item in totals:
            item["share"] = (item["total_votes"] or 0) * 100 / total_votes if total_votes else 0

        context.update(
            selected_lga=lga,
            lga_results=totals,
            polling_unit_count=len(ids),
            reporting_units=result_rows.values("polling_unit_uniqueid").distinct().count(),
            total_votes=total_votes,
        )

    return render(request, "election/lga_results.html", context)


def create_poll_result(request):
    # Show LABOUR from the party table, but save LABO to the legacy results.
    parties = list(Party.objects.order_by("id"))
    form = NewPollingUnitResultsForm(request.POST or None, parties=parties)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        lga, ward = data["lga"], data["ward"]
        timestamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
        ip_address = (request.META.get("REMOTE_ADDR") or "unknown")[:50]

        with transaction.atomic():
            polling_unit = PollingUnit.objects.create(
                polling_unit_id=data["polling_unit_id"],
                polling_unit_name=data["polling_unit_name"],
                polling_unit_number=data["polling_unit_number"] or None,
                lga_id=lga.lga_id,  # NOT lga.uniqueid
                ward_id=ward.ward_id,
                uniquewardid=ward.uniqueid,
                entered_by_user=data["entered_by_user"],
                date_entered=timestamp,
                user_ip_address=ip_address,
            )
            results = []
            for party in parties:
                code = "LABO" if party.partyid == "LABOUR" else party.partyid
                results.append(AnnouncedPuResult(
                    polling_unit_uniqueid=str(polling_unit.uniqueid),
                    party_abbreviation=code,
                    party_score=data[f"score_{party.pk}"],
                    entered_by_user=data["entered_by_user"],
                    date_entered=timestamp,
                    user_ip_address=ip_address,
                ))
            AnnouncedPuResult.objects.bulk_create(results)

        messages.success(
            request,
            f"Saved {polling_unit.polling_unit_name} and its {len(results)} party results successfully.",
        )
        return redirect("polling_unit_result", unit_id=polling_unit.uniqueid)

    # A ModelChoiceField POSTs Lga.uniqueid. Ward.lga_id holds Lga.lga_id.
    lga_id_to_pk = dict(Lga.objects.values_list("lga_id", "uniqueid"))
    ward_lga_map = {
        str(pk): str(lga_id_to_pk[lga_id])
        for pk, lga_id in Ward.objects.values_list("uniqueid", "lga_id")
        if lga_id in lga_id_to_pk
    }

    return render(request, "election/create_poll_result.html", {
        "form": form,
        "ward_lga_map": ward_lga_map,
        "party_count": len(parties),
    })
