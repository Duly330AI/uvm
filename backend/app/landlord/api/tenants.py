from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from ..models import Issue, IssueAttachment, IssueNote, Tenant

REDACTED_EMAIL = "erased@example.invalid"


def _attachment_meta(a: IssueAttachment):
    f = getattr(a, "file", None)
    size = None
    if getattr(f, "size", None) is not None:
        try:
            size = int(f.size)
        except Exception:
            size = None
    return {
        "id": a.id,
        "name": getattr(f, "name", "") if f else "",
        "size": size,
        "content_type": getattr(a, "content_type", "") or "",
        "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else "",
    }


class TenantExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, id: int, *args, **kwargs):
        tenant = get_object_or_404(Tenant.objects.select_related("unit__property"), id=id)
        issues = (
            Issue.objects.filter(tenant=tenant)
            .select_related("unit__property", "tenant")
            .order_by("-created_at", "-id")
        )
        notes = IssueNote.objects.filter(issue__tenant=tenant).select_related("issue", "author")
        atts = IssueAttachment.objects.filter(issue__tenant=tenant).select_related("issue")

        data = {
            "tenant": {
                "id": tenant.id,
                "unit_id": getattr(tenant.unit, "id", None),
                "unit_label": getattr(tenant.unit, "unit_label", None),
                "property": getattr(getattr(tenant.unit, "property", None), "name", None),
                "primary_email": getattr(tenant, "primary_email", None),
                "created_at": getattr(tenant, "created_at", None).isoformat()
                if getattr(tenant, "created_at", None)
                else "",
            },
            "issues": [
                {
                    "id": i.id,
                    "ticket_no": i.ticket_no,
                    "status": i.status,
                    "category": i.category,
                    "severity": i.severity,
                    "summary": i.summary,
                    "created_at": i.created_at.isoformat() if i.created_at else "",
                }
                for i in issues
            ],
            "notes": [
                {
                    "id": n.id,
                    "issue_id": n.issue_id,
                    "author_id": getattr(n.author, "id", None),
                    "text": n.text,
                    "created_at": n.created_at.isoformat() if n.created_at else "",
                    "visibility": getattr(n, "visibility", None),
                }
                for n in notes
            ],
            "attachments": [_attachment_meta(a) for a in atts],
            "exported_at": timezone.now().isoformat(),
        }
        return JsonResponse(data, status=200)


class TenantEraseView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, id: int, *args, **kwargs):
        tenant = get_object_or_404(Tenant.objects.select_for_update(), id=id)

        # Minimal PII redaction without schema changes (idempotent)
        updated_fields = []
        if hasattr(tenant, "primary_email"):
            try:
                field = Tenant._meta.get_field("primary_email")
                current = getattr(tenant, "primary_email", None)
                already_erased = current in (None, REDACTED_EMAIL)
                if not already_erased:
                    if getattr(field, "null", True):
                        tenant.primary_email = None
                    else:
                        tenant.primary_email = REDACTED_EMAIL
                    updated_fields.append("primary_email")
            except Exception:
                pass

        for fld in ("phone", "mobile", "contact_name"):
            if hasattr(tenant, fld):
                try:
                    field = Tenant._meta.get_field(fld)
                    setattr(tenant, fld, None if getattr(field, "null", True) else "")
                    updated_fields.append(fld)
                except Exception:
                    continue

        if updated_fields:
            tenant.save(update_fields=updated_fields)

        # Audit note per issue (avoid duplicates)
        marker = "PII erased for tenant"
        for i in Issue.objects.filter(tenant=tenant).only("id", "ticket_no"):
            if not IssueNote.objects.filter(issue=i, text__icontains=marker).exists():
                IssueNote.objects.create(
                    issue=i,
                    text=f"{marker} by admin at {timezone.now().isoformat()}",
                    visibility=getattr(IssueNote, "VISIBILITY_INTERNAL", "internal"),
                )

        return JsonResponse({"ok": True}, status=200)
