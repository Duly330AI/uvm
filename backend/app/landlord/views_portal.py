from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from landlord.models import (
    Appointment,
    Issue,
    IssueNote,
    Property,
    Tenant,
    Unit,
    Vendor,
)
from landlord.services.issues import update_status
from landlord.tasks import send_appointment_invite


def _status_choices():
    return ["NEW", "IN_PROGRESS", "WAITING_VENDOR", "WAITING_TENANT", "DONE"]


@staff_member_required
def dashboard(request):
    qs_open = Issue.objects.filter(status__in=["NEW", "IN_PROGRESS", "WAITING_VENDOR", "WAITING_TENANT"])
    # Show only open tickets in "Neueste Tickets" (consistent with count)
    recent = qs_open.select_related("unit", "tenant").order_by("-created_at")[:10]
    return render(request, "portal/dashboard.html", {
        "open_count": qs_open.count(),
        "recent": recent,
    })


@staff_member_required
def issues_list(request):
    qs = Issue.objects.select_related("unit__property", "tenant").order_by("-created_at")
    s = request.GET.get("s")
    if s:
        qs = qs.filter(summary__icontains=s) | qs.filter(ticket_no__icontains=s)
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    urgent = request.GET.get("urgent")
    if urgent == "true":
        qs = qs.filter(severity__gte=4)

    prop = request.GET.get("property")
    if prop:
        qs = qs.filter(unit__property__id=prop)

    pg = Paginator(qs, 20)
    page = pg.get_page(request.GET.get("page") or 1)
    return render(request, "portal/issues_list.html", {
        "page": page,
        "status_choices": _status_choices(),
        "q": s or "",
        "status_val": status or "",
        "urgent_val": urgent or "",
        "properties": Property.objects.all().order_by("name"),
        "prop_val": prop or "",
    })


@staff_member_required
def issue_detail(request, pk: int):
    issue = get_object_or_404(Issue.objects.select_related("unit__property", "tenant"), pk=pk)
    notes = IssueNote.objects.filter(issue=issue).order_by("-created_at")[:50]
    appts = Appointment.objects.filter(issue=issue).order_by("start")
    vendors = Vendor.objects.all().order_by("name")
    attachments = issue.attachments.all().order_by("created_at")
    vendor_uploads = issue.vendor_attachments.select_related("vendor").order_by("-created_at")
    return render(request, "portal/issue_detail.html", {
        "issue": issue, "notes": notes, "appts": appts,
        "status_choices": _status_choices(), "vendors": vendors,
        "attachments": attachments, "vendor_uploads": vendor_uploads
    })


@staff_member_required
@transaction.atomic
def issue_set_status(request, pk: int):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    new = request.POST.get("status")
    if new not in _status_choices():
        return HttpResponseBadRequest("invalid")
    issue = get_object_or_404(Issue, pk=pk)
    update_status(issue, new)
    return render(request, "portal/partials/status_badge.html", {"issue": issue})


@staff_member_required
@transaction.atomic
def issue_add_note(request, pk: int):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    text = (request.POST.get("text") or "").strip()
    is_internal = request.POST.get("is_internal") == "on"
    if not text:
        return HttpResponseBadRequest("empty")
    issue = get_object_or_404(Issue, pk=pk)
    visibility = "internal" if is_internal else "tenant"
    IssueNote.objects.create(issue=issue, text=text, visibility=visibility)
    notes = IssueNote.objects.filter(issue=issue).order_by("-created_at")[:50]
    return render(request, "portal/partials/notes_list.html", {"notes": notes})


@staff_member_required
@transaction.atomic
def issue_assign_vendor(request, pk: int):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    issue = get_object_or_404(Issue, pk=pk)
    vendor_id = request.POST.get("vendor_id")
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    start = timezone.now() + timedelta(days=2)
    end = start + timedelta(hours=1)
    appt = Appointment.objects.create(issue=issue, vendor=vendor, start=start, end=end)
    update_status(issue, "WAITING_VENDOR")

    # Send notifications
    try:
        send_appointment_invite.delay(appt.id)
    except Exception:
        pass

    # Send vendor assignment email
    if vendor and vendor.email:
        from landlord.tasks import send_vendor_assignment_email
        try:
            send_vendor_assignment_email.delay(appt.id)
        except Exception:
            pass

    appts = Appointment.objects.filter(issue=issue).order_by("start")
    return render(request, "portal/partials/appointments_list.html", {"appts": appts})


@staff_member_required
@transaction.atomic
def issue_add_appointment(request, pk: int):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    issue = get_object_or_404(Issue, pk=pk)
    vendor_id = request.POST.get("vendor_id")
    start = request.POST.get("start")
    end = request.POST.get("end")
    vendor = get_object_or_404(Vendor, pk=vendor_id) if vendor_id else None
    if not (start and end):
        return HttpResponseBadRequest("start/end required")
    appt = Appointment.objects.create(issue=issue, vendor=vendor, start=start, end=end)

    # Send notifications
    try:
        send_appointment_invite.delay(appt.id)
    except Exception:
        pass

    # Send vendor assignment email
    if vendor and vendor.email:
        from landlord.tasks import send_vendor_assignment_email
        try:
            send_vendor_assignment_email.delay(appt.id)
        except Exception:
            pass

    appts = Appointment.objects.filter(issue=issue).order_by("start")
    return render(request, "portal/partials/appointments_list.html", {"appts": appts})


@staff_member_required
@transaction.atomic
def appointment_delete(request, pk: int):
    if request.method != "DELETE":
        return HttpResponseBadRequest("DELETE only")
    appt = get_object_or_404(Appointment, pk=pk)
    issue = appt.issue
    appt.delete()
    appts = Appointment.objects.filter(issue=issue).order_by("start")
    return render(request, "portal/partials/appointments_list.html", {"appts": appts})


# ============================================================================
# TENANT MANAGEMENT (PR 2)
# ============================================================================


@staff_member_required
def tenants_list(request):
    """List all tenants with their units"""
    tenants = Tenant.objects.select_related("unit__property").order_by(
        "unit__property__name", "unit__unit_label", "-is_active"
    )
    return render(request, "portal/tenants_list.html", {
        "tenants": tenants,
    })


@staff_member_required
def tenant_create(request):
    """
    Create new tenant.

    Updated 2025-10-23: Supports first_name, last_name fields.
    """
    if request.method == "POST":
        unit_id = request.POST.get("unit")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("primary_email")
        phone = request.POST.get("phone", "")
        date_of_birth = request.POST.get("date_of_birth") or None
        moved_in = request.POST.get("moved_in_at")
        emergency_contact_name = request.POST.get("emergency_contact_name", "")
        emergency_contact_phone = request.POST.get("emergency_contact_phone", "")
        notes = request.POST.get("notes", "")

        if not unit_id or not email:
            messages.error(request, "Wohneinheit und E-Mail sind erforderlich.")
            return redirect("portal_tenant_create")

        unit = get_object_or_404(Unit, id=unit_id)

        tenant = Tenant.objects.create(
            unit=unit,
            first_name=first_name,
            last_name=last_name,
            primary_email=email,
            phone=phone,
            date_of_birth=date_of_birth,
            moved_in_at=moved_in if moved_in else None,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            notes=notes,
            is_active=True
        )

        # Send welcome email if requested
        if request.POST.get("send_welcome"):
            from landlord.tasks import send_tenant_welcome
            send_tenant_welcome.delay(tenant.id)

        messages.success(request, f"Mieter {tenant} erfolgreich angelegt.")
        return redirect("portal_tenants")

    # GET: Show form
    units = Unit.objects.select_related("property").order_by("property__name", "unit_label")
    return render(request, "portal/tenant_form.html", {
        "units": units,
        "is_edit": False,
    })


@staff_member_required
def tenant_edit(request, pk: int):
    """
    Edit existing tenant.

    Updated 2025-10-23: Supports first_name, last_name fields.
    """
    tenant = get_object_or_404(Tenant, pk=pk)

    if request.method == "POST":
        tenant.first_name = request.POST.get("first_name", "").strip()
        tenant.last_name = request.POST.get("last_name", "").strip()
        tenant.primary_email = request.POST.get("primary_email", tenant.primary_email)
        tenant.phone = request.POST.get("phone", "")
        tenant.date_of_birth = request.POST.get("date_of_birth") or None
        moved_in = request.POST.get("moved_in_at")
        tenant.moved_in_at = moved_in if moved_in else None
        tenant.emergency_contact_name = request.POST.get("emergency_contact_name", "")
        tenant.emergency_contact_phone = request.POST.get("emergency_contact_phone", "")
        tenant.notes = request.POST.get("notes", "")
        tenant.is_active = request.POST.get("is_active") == "on"
        tenant.save()

        messages.success(request, f"Mieter {tenant} erfolgreich aktualisiert.")
        return redirect("portal_tenants")

    # GET: Show form
    units = Unit.objects.select_related("property").order_by("property__name", "unit_label")
    return render(request, "portal/tenant_form.html", {
        "units": units,
        "tenant": tenant,
        "is_edit": True,
    })


@staff_member_required
def tenant_deactivate(request, pk: int):
    """Deactivate tenant (soft delete)"""
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    tenant = get_object_or_404(Tenant, pk=pk)
    tenant.is_active = False
    tenant.moved_out_at = timezone.now()
    tenant.save()

    return redirect("portal_tenants")


@staff_member_required
def tenant_delete(request, pk: int):
    """Delete tenant (hard delete, only if no issues)"""
    if request.method != "DELETE":
        return HttpResponseBadRequest("DELETE only")

    tenant = get_object_or_404(Tenant, pk=pk)

    # Check for issues
    issue_count = Issue.objects.filter(tenant=tenant).count()
    if issue_count > 0:
        return JsonResponse({
            "error": f"Mieter hat {issue_count} Ticket(s). Bitte erst deaktivieren."
        }, status=400)

    tenant.delete()
    return HttpResponse(status=200)

