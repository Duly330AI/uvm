from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.shortcuts import render
from django.utils import timezone

from .models import Issue


@staff_member_required
def issue_report(request):
    days = int(request.GET.get("days", "30"))
    since = timezone.now() - timedelta(days=days)

    OPEN = ["NEW","IN_PROGRESS","WAITING_VENDOR","WAITING_TENANT"]
    open_by_property = (
        Issue.objects.filter(status__in=OPEN)
        .values("unit__property__id", "unit__property__name")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    aging_expr = ExpressionWrapper(timezone.now() - F("created_at"), output_field=DurationField())
    aging_by_status = (
        Issue.objects.filter(created_at__gte=since)
        .values("status")
        .annotate(avg_age=Avg(aging_expr))
        .order_by("status")
    )

    top_categories = (
        Issue.objects.filter(created_at__gte=since)
        .values("category")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    return render(request, "admin/landlord/reports.html", {
        "days": days,
        "open_by_property": open_by_property,
        "aging_by_status": aging_by_status,
        "top_categories": top_categories,
    })
