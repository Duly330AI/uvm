"""
Tenant (Mieter) Portal Views - Magic-Link Auth
"""
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from landlord.models import Issue, IssueAttachment, IssueNote, Tenant
from landlord.services.tenant_auth import (
    create_magic_link_token,
    verify_magic_link_token,
)
from landlord.tasks import send_tenant_magic_link


def _get_client_ip(request):
    """Get client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR', '')


def _check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """Check if rate limit is exceeded. Returns True if OK, False if exceeded."""
    current = cache.get(key, 0)
    if current >= max_requests:
        return False
    cache.set(key, current + 1, window_seconds)
    return True


def login_page(request):
    """Show login form"""
    return render(request, "tenant/login.html")


@require_http_methods(["POST"])
def request_magic_link(request):
    """Send magic-link to tenant email (with rate limiting)"""
    email = request.POST.get("email", "").strip().lower()
    if not email:
        messages.error(request, "Bitte E-Mail-Adresse eingeben.")
        return redirect("tenant_login")

    # Rate limiting: 3 requests per 30 min per email
    email_key = f"magic_link_email:{email}"
    if not _check_rate_limit(email_key, max_requests=3, window_seconds=1800):
        messages.error(request, "Zu viele Anfragen. Bitte warten Sie 30 Minuten.")
        return redirect("tenant_login")

    # Rate limiting: 10 requests per 30 min per IP
    ip = _get_client_ip(request)
    ip_key = f"magic_link_ip:{ip}"
    if not _check_rate_limit(ip_key, max_requests=10, window_seconds=1800):
        messages.error(request, "Zu viele Anfragen von dieser IP-Adresse.")
        return redirect("tenant_login")

    # Create token
    token_id = create_magic_link_token(email, request.META)

    # Send email (async)
    try:
        send_tenant_magic_link.delay(email, token_id)
    except Exception:
        pass  # Don't reveal if email exists

    messages.success(request, f"Anmelde-Link wurde an {email} gesendet (falls registriert).")
    return redirect("tenant_login")


def verify_magic_link(request, token_id: str):
    """Verify magic-link token and log in tenant"""
    tenant = verify_magic_link_token(token_id)

    if not tenant:
        messages.error(request, "Ungültiger oder abgelaufener Link.")
        return redirect("tenant_login")

    # Store tenant ID in session (simple session-based auth)
    request.session["tenant_id"] = tenant.id
    request.session["tenant_email"] = tenant.primary_email

    messages.success(request, f"Willkommen, {tenant.primary_email}!")
    return redirect("tenant_my_issues")


def _require_tenant_login(request):
    """Check if tenant is logged in, return tenant or None"""
    tenant_id = request.session.get("tenant_id")
    if not tenant_id:
        return None
    try:
        return Tenant.objects.get(id=tenant_id, is_active=True)
    except Tenant.DoesNotExist:
        return None


def my_issues(request):
    """List all issues for logged-in tenant"""
    tenant = _require_tenant_login(request)
    if not tenant:
        messages.error(request, "Bitte melden Sie sich an.")
        return redirect("tenant_login")

    issues = Issue.objects.filter(tenant=tenant).select_related("unit__property").order_by("-created_at")
    return render(request, "tenant/my_issues.html", {"tenant": tenant, "issues": issues})


def issue_detail(request, pk: int):
    """Show issue detail for logged-in tenant"""
    tenant = _require_tenant_login(request)
    if not tenant:
        messages.error(request, "Bitte melden Sie sich an.")
        return redirect("tenant_login")

    issue = get_object_or_404(Issue.objects.select_related("unit__property"), pk=pk)

    # Security: only show if belongs to tenant
    if issue.tenant_id != tenant.id:
        return HttpResponseForbidden("Zugriff verweigert")

    notes = IssueNote.objects.filter(issue=issue, visibility="tenant").order_by("-created_at")[:50]
    attachments = issue.attachments.all().order_by("created_at")

    return render(request, "tenant/issue_detail.html", {
        "tenant": tenant,
        "issue": issue,
        "notes": notes,
        "attachments": attachments,
    })


@require_http_methods(["POST"])
@transaction.atomic
def add_note(request, pk: int):
    """Add tenant note to issue"""
    tenant = _require_tenant_login(request)
    if not tenant:
        return HttpResponseForbidden("Nicht angemeldet")

    issue = get_object_or_404(Issue, pk=pk)
    if issue.tenant_id != tenant.id:
        return HttpResponseForbidden("Zugriff verweigert")

    text = (request.POST.get("text") or "").strip()
    if not text:
        messages.error(request, "Notiz darf nicht leer sein.")
        return redirect("tenant_issue_detail", pk=pk)

    IssueNote.objects.create(
        issue=issue,
        text=text,
        visibility="tenant"  # visible to tenant & staff
    )

    messages.success(request, "Notiz hinzugefügt.")
    return redirect("tenant_issue_detail", pk=pk)


@require_http_methods(["POST"])
@transaction.atomic
def add_attachment(request, pk: int):
    """Upload attachment to issue"""
    tenant = _require_tenant_login(request)
    if not tenant:
        return HttpResponseForbidden("Nicht angemeldet")

    issue = get_object_or_404(Issue, pk=pk)
    if issue.tenant_id != tenant.id:
        return HttpResponseForbidden("Zugriff verweigert")

    file = request.FILES.get("file")
    if not file:
        messages.error(request, "Keine Datei ausgewählt.")
        return redirect("tenant_issue_detail", pk=pk)

    # File size limit: 10 MB
    if file.size > 10 * 1024 * 1024:
        messages.error(request, "Datei zu groß (max. 10 MB).")
        return redirect("tenant_issue_detail", pk=pk)

    # MIME whitelist
    allowed_types = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    if file.content_type not in allowed_types:
        messages.error(request, f"Dateityp nicht erlaubt: {file.content_type}")
        return redirect("tenant_issue_detail", pk=pk)

    # Check total size for issue (40 MB limit)
    total_size = sum(a.size_bytes or 0 for a in issue.attachments.all())
    if total_size + file.size > 40 * 1024 * 1024:
        messages.error(request, "Gesamtgröße aller Anhänge überschreitet 40 MB.")
        return redirect("tenant_issue_detail", pk=pk)

    IssueAttachment.objects.create(
        issue=issue,
        file=file,
        mime=file.content_type,
        size_bytes=file.size,
        uploader_role=IssueAttachment.UploaderRole.TENANT
    )

    messages.success(request, f"Datei '{file.name}' hochgeladen.")
    return redirect("tenant_issue_detail", pk=pk)


def logout(request):
    """Logout tenant"""
    request.session.flush()
    messages.success(request, "Sie wurden abgemeldet.")
    return redirect("tenant_login")
