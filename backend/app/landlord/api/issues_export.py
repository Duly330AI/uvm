from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from .issues import IssuesAdminListView


class _Echo:
    def write(self, value):
        return value


def _get_filtered_queryset(request):
    # Reuse IssuesAdminListView filtering logic without pagination/serialization
    view = IssuesAdminListView()
    view.request = request
    return view.get_queryset()


class IssuesExportCsvView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        qs = _get_filtered_queryset(request)
        qs = qs.select_related("unit__property", "tenant")

        import csv

        pseudo_buffer = _Echo()
        writer = csv.writer(pseudo_buffer)

        def _csv_safe(text):
            if text is None:
                return ""
            s = str(text)
            if s[:1] in ("=", "+", "-", "@"):
                return "'" + s
            return s

        def row_iter():
            # Optional BOM for Excel compatibility
            yield "\ufeff"
            yield writer.writerow([
                "ticket_no",
                "status",
                "category",
                "severity",
                "created_at",
                "property",
                "unit",
                "tenant_email",
                "summary",
            ])
            for i in qs.iterator(chunk_size=500):
                prop_name = _csv_safe(getattr(getattr(i.unit, "property", None), "name", "") if i.unit else "")
                unit_label = _csv_safe(getattr(i.unit, "unit_label", "") if i.unit else "")
                tenant_email = _csv_safe(getattr(i.tenant, "primary_email", "") if i.tenant else "")
                summary = _csv_safe((i.summary or "").replace("\r", " ").replace("\n", " "))
                created = i.created_at.isoformat() if i.created_at else ""
                yield writer.writerow([
                    i.ticket_no or "",
                    i.status or "",
                    i.category or "",
                    i.severity or "",
                    created,
                    prop_name,
                    unit_label,
                    tenant_email,
                    summary,
                ])

        filename = f"issues_{timezone.now().strftime('%Y%m%d')}.csv"
        resp = StreamingHttpResponse(row_iter(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
