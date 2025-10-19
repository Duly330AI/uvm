"""
Vendor Portal Views - Handwerker Interface
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from landlord.models import Appointment, Issue, Vendor
from landlord.services.vendor_auth import verify_vendor_token


def vendor_auth_required(view_func):
    """Decorator to require vendor authentication"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get("vendor_id"):
            return redirect("vendor_login")
        return view_func(request, *args, **kwargs)
    return wrapper


def vendor_login(request):
    """Vendor login page (request magic-link)"""
    return render(request, "vendor/login.html")


def vendor_magic_link(request, token_id: str):
    """Verify vendor magic-link token and log in"""
    vendor = verify_vendor_token(token_id)

    if not vendor:
        messages.error(request, "Ungültiger oder abgelaufener Link.")
        return redirect("vendor_login")

    # Store vendor ID in session
    request.session["vendor_id"] = vendor.id
    request.session["vendor_email"] = vendor.email

    messages.success(request, f"Willkommen, {vendor.name}!")
    return redirect("vendor_issues")


@vendor_auth_required
def vendor_issues(request):
    """List of issues assigned to this vendor"""
    vendor_id = request.session.get("vendor_id")
    vendor = get_object_or_404(Vendor, id=vendor_id)

    # Get appointments for this vendor
    appointments = Appointment.objects.filter(
        vendor=vendor
    ).select_related(
        "issue", "issue__unit", "issue__unit__property"
    ).order_by("-created_at")

    context = {
        "vendor": vendor,
        "appointments": appointments,
    }
    return render(request, "vendor/issues.html", context)


@vendor_auth_required
def vendor_issue_detail(request, pk: int):
    """Issue detail view for vendor"""
    vendor_id = request.session.get("vendor_id")
    vendor = get_object_or_404(Vendor, id=vendor_id)

    issue = get_object_or_404(Issue, pk=pk)

    # Check if vendor is assigned to this issue
    appointment = Appointment.objects.filter(
        issue=issue, vendor=vendor
    ).select_related("issue__unit__property").first()

    if not appointment:
        messages.error(request, "Sie haben keinen Zugriff auf dieses Ticket.")
        return redirect("vendor_issues")

    context = {
        "vendor": vendor,
        "issue": issue,
        "appointment": appointment,
    }
    return render(request, "vendor/issue_detail.html", context)


@vendor_auth_required
@require_http_methods(["POST"])
def vendor_upload_file(request, pk: int):
    """Upload PDF file (estimate or invoice)"""
    from landlord.models import VendorAttachment

    vendor_id = request.session.get("vendor_id")
    vendor = get_object_or_404(Vendor, id=vendor_id)
    issue = get_object_or_404(Issue, pk=pk)

    # Check if vendor is assigned to this issue
    appointment = Appointment.objects.filter(issue=issue, vendor=vendor).first()
    if not appointment:
        messages.error(request, "Sie haben keinen Zugriff auf dieses Ticket.")
        return redirect("vendor_issues")

    # Get uploaded file
    uploaded_file = request.FILES.get("file")
    category = request.POST.get("category")
    notes = request.POST.get("notes", "")

    if not uploaded_file:
        messages.error(request, "Keine Datei ausgewählt.")
        return redirect("vendor_issue_detail", pk=pk)

    # Validate file type
    if not uploaded_file.content_type == "application/pdf":
        messages.error(request, "Nur PDF-Dateien sind erlaubt.")
        return redirect("vendor_issue_detail", pk=pk)

    # Validate file size (10MB max)
    if uploaded_file.size > 10 * 1024 * 1024:
        messages.error(request, "Datei zu groß. Maximum: 10MB")
        return redirect("vendor_issue_detail", pk=pk)

    # Create attachment
    VendorAttachment.objects.create(
        issue=issue,
        vendor=vendor,
        category=category,
        file=uploaded_file,
        mime=uploaded_file.content_type,
        size_bytes=uploaded_file.size,
        notes=notes
    )

    messages.success(request, f"{VendorAttachment.Category(category).label} erfolgreich hochgeladen.")
    return redirect("vendor_issue_detail", pk=pk)


@vendor_auth_required
@require_http_methods(["POST"])
def vendor_logout(request):
    """Log out vendor"""
    request.session.flush()
    messages.success(request, "Sie wurden abgemeldet.")
    return redirect("vendor_login")
