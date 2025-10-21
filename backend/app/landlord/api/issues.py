from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

if TYPE_CHECKING:
    from django.db.models import QuerySet
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser

from ..models import Issue
from ..serializers import IssueListSerializer

SAFE_ORDER = {"created_at", "-created_at", "severity", "-severity", "status", "-status"}

class IssueAdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

class IssuesAdminListView(ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = IssueListSerializer
    pagination_class = IssueAdminPagination

    def get_queryset(self) -> QuerySet[Issue]:  # type: ignore[override]
        qs = Issue.objects.select_related("tenant", "unit", "unit__property").all()
        p = self.request.query_params  # type: ignore[attr-defined]

        status_param = p.get("status")
        if status_param:
            statuses = [s.strip() for s in status_param.split(",") if s.strip()]
            qs = qs.filter(status__in=statuses)

        if p.get("category"):
            qs = qs.filter(category=p.get("category"))

        if p.get("property"):
            qs = qs.filter(unit__property_id=p.get("property"))
        if p.get("unit"):
            qs = qs.filter(unit_id=p.get("unit"))

        smin = p.get("severity_min")
        smax = p.get("severity_max")
        if smin:
            qs = qs.filter(severity__gte=int(smin))
        if smax:
            qs = qs.filter(severity__lte=int(smax))

        cf = p.get("created_from")
        ct = p.get("created_to")
        def _parse_aware(dt_str: Optional[str]):
            if not dt_str:
                return None
            dt = parse_datetime(dt_str)
            if not dt:
                return None
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            return dt
        dt_from = _parse_aware(cf)
        dt_to = _parse_aware(ct)
        if dt_from:
            qs = qs.filter(created_at__gte=dt_from)
        if dt_to:
            qs = qs.filter(created_at__lte=dt_to)

        s = p.get("search")
        if s:
            qs = qs.filter(
                Q(ticket_no__icontains=s) |
                Q(summary__icontains=s) |
                Q(tenant__primary_email__icontains=s) |
                Q(tenant__user__email__icontains=s)
            )

        urgent = p.get("urgent")
        if urgent and urgent.lower() in {"1", "true", "yes", "y"}:
            qs = qs.filter(severity__gte=4)

        ordering_param = p.get("ordering") or "-created_at"
        parts: List[str] = [o.strip() for o in ordering_param.split(",") if o.strip()]
        safe_parts = [o for o in parts if o in SAFE_ORDER]
        ordering = safe_parts or ["-created_at"]
        qs = qs.order_by(*ordering, "-id")
        return qs
