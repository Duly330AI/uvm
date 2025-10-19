from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Appointment, Issue
from .utils.ics import build_ics


def _plain_from_html(html: str) -> str:
    # Very simple plaintext fallback
    try:
        import re
        return re.sub(r"<[^>]+>", "", html)
    except Exception:
        return html


@shared_task(
    autoretry_for=(Exception,), retry_backoff=2, max_retries=5, acks_late=True, time_limit=30
)
def send_issue_created(issue_id: int) -> None:
    from landlord.utils.public_link import make_token

    issue = Issue.objects.select_related("tenant", "unit").get(id=issue_id)
    subject = f"[{issue.ticket_no}] Meldung eingegangen"
    status_url = f"http://{settings.SITE_DOMAIN}/t/{make_token(issue.ticket_no)}/"
    ctx = {
        "issue": issue,
        "site_domain": getattr(settings, "SITE_DOMAIN", "localhost"),
        "status_url": status_url,
    }
    html = render_to_string("emails/issue_created.html", ctx)
    body = strip_tags(html) or _plain_from_html(html)
    to_email = [issue.tenant.primary_email] if issue.tenant and issue.tenant.primary_email else []
    if not to_email:
        return
    msg = EmailMultiAlternatives(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, to=to_email)
    msg.attach_alternative(html, "text/html")
    msg.send()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=2, max_retries=5, acks_late=True, time_limit=30
)
def send_status_changed(issue_id: int, old: str, new: str) -> None:
    issue = Issue.objects.select_related("tenant").get(id=issue_id)
    subject = f"[{issue.ticket_no}] Status geändert: {old} → {new}"
    html = f"<p>Status geändert von <b>{old}</b> auf <b>{new}</b> für Ticket <b>{issue.ticket_no}</b>.</p>"
    body = strip_tags(html) or _plain_from_html(html)
    to_email = [issue.tenant.primary_email] if issue.tenant and issue.tenant.primary_email else []
    if not to_email:
        return
    msg = EmailMultiAlternatives(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, to=to_email)
    msg.attach_alternative(html, "text/html")
    msg.send()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=2, max_retries=5, acks_late=True, time_limit=30
)
def send_appointment_invite(appointment_id: int) -> None:
    appt = Appointment.objects.select_related("issue__tenant", "vendor").get(id=appointment_id)
    issue = appt.issue
    subject = f"[{issue.ticket_no}] Terminvorschlag"
    to_email = [issue.tenant.primary_email] if issue.tenant and issue.tenant.primary_email else []
    if not to_email:
        return
    # Build ICS
    ics_bytes = build_ics(appt, getattr(settings, "SITE_DOMAIN", "localhost"))
    # Compose mail
    html = f"<p>Terminvorschlag für Ticket <b>{issue.ticket_no}</b>: {appt.start.isoformat()} – {appt.end.isoformat()}</p>"
    body = strip_tags(html) or _plain_from_html(html)
    msg = EmailMultiAlternatives(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, to=to_email)
    msg.attach_alternative(html, "text/html")
    msg.attach("appointment.ics", ics_bytes, "text/calendar; method=REQUEST; charset=UTF-8")
    # Optional Outlook header
    msg.extra_headers = {"Content-Class": "urn:content-classes:calendarmessage"}
    msg.send()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=2, max_retries=5, acks_late=True, time_limit=30
)
def send_tenant_magic_link(email: str, token_id: str) -> None:
    """Send magic-link email to tenant"""
    subject = "Ihr Anmelde-Link (UVM)"
    magic_url = f"http://{settings.SITE_DOMAIN}/tenant/magic/{token_id}/"

    html = f"""
    <html>
    <body>
        <p>Guten Tag,</p>
        <p>Sie haben einen Anmelde-Link für das Mieter-Portal angefordert.</p>
        <p style="margin: 20px 0;">
            <a href="{magic_url}"
               style="background:#2563eb;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;display:inline-block;">
                Zum Mieter-Portal
            </a>
        </p>
        <p>Dieser Link ist <strong>15 Minuten</strong> gültig und kann nur einmal verwendet werden.</p>
        <p>Falls Sie diesen Link nicht angefordert haben, ignorieren Sie diese E-Mail.</p>
        <p>Alternativ-Link: <a href="{magic_url}">{magic_url}</a></p>
        <p>– {settings.SITE_DOMAIN}</p>
    </body>
    </html>
    """

    body = strip_tags(html) or _plain_from_html(html)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=2, max_retries=5, acks_late=True, time_limit=30
)
def send_tenant_welcome(tenant_id: int) -> None:
    """Send welcome email to newly created tenant with magic-link"""
    from datetime import timedelta

    from django.utils import timezone

    from landlord.models import Tenant, TenantAuthToken

    try:
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return

    # Create magic-link token
    token = TenantAuthToken.objects.create(
        tenant=tenant,  # ✅ SET TENANT!
        email=tenant.primary_email,
        expires_at=timezone.now() + timedelta(minutes=15)
    )

    subject = "Willkommen im Mieter-Portal (UVM)"
    magic_url = f"http://{settings.SITE_DOMAIN}/tenant/magic/{token.id}/"

    unit_info = f"{tenant.unit.property.name} - Wohnung {tenant.unit.unit_label}"

    html = f"""
    <html>
    <body>
        <h2>Willkommen im Mieter-Portal!</h2>
        <p>Guten Tag,</p>
        <p>Sie wurden als Mieter in unserem System registriert:</p>
        <p><strong>{unit_info}</strong></p>

        <p>Sie können jetzt Ihr Mieter-Portal aktivieren und Anliegen melden:</p>

        <p style="margin: 20px 0;">
            <a href="{magic_url}"
               style="background:#2563eb;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;display:inline-block;">
                Portal aktivieren
            </a>
        </p>

        <p><strong>Was können Sie im Portal machen?</strong></p>
        <ul>
            <li>Anliegen und Schäden melden (mit Fotos)</li>
            <li>Status Ihrer Tickets verfolgen</li>
            <li>Mit dem Vermieter kommunizieren</li>
            <li>Dokumente einsehen</li>
        </ul>

        <p>Dieser Link ist <strong>15 Minuten</strong> gültig. Bei Bedarf können Sie unter
           <a href="http://{settings.SITE_DOMAIN}/tenant/">http://{settings.SITE_DOMAIN}/tenant/</a>
           jederzeit einen neuen Link anfordern.</p>

        <p>Alternativ-Link: <a href="{magic_url}">{magic_url}</a></p>

        <p>Mit freundlichen Grüßen<br>
        Ihre Hausverwaltung</p>
    </body>
    </html>
    """

    body = strip_tags(html) or _plain_from_html(html)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[tenant.primary_email]
    )
    msg.attach_alternative(html, "text/html")
    msg.send()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=2, max_retries=5, acks_late=True, time_limit=30
)
def send_vendor_assignment_email(appointment_id: int) -> None:
    """Send email to vendor when assigned to an issue"""
    from landlord.models import Appointment, VendorAuthToken

    try:
        appointment = Appointment.objects.select_related(
            'vendor', 'issue', 'issue__unit', 'issue__unit__property'
        ).get(id=appointment_id)
    except Appointment.DoesNotExist:
        return

    if not appointment.vendor or not appointment.vendor.email:
        return

    # Generate auth token for vendor
    vendor = appointment.vendor
    token = VendorAuthToken.objects.create(
        vendor=vendor,
        email=vendor.email,
        purpose=VendorAuthToken.Purpose.INVITE,
        expires_at=timezone.now() + timedelta(hours=24)  # 24h validity
    )

    issue = appointment.issue
    property_info = f"{issue.unit.property.name} - {issue.unit.unit_label}"

    subject = f"Neuer Auftrag: {issue.ticket_no} - {issue.get_category_display()}"
    vendor_url = f"http://{settings.SITE_DOMAIN}/vendor/auth/{token.id}/"

    html = f"""
    <html>
    <body>
        <h2>Neuer Auftrag zugewiesen</h2>
        <p>Hallo {vendor.name},</p>
        <p>Sie wurden einem neuen Auftrag zugewiesen:</p>

        <div style="background:#f3f4f6;padding:16px;border-radius:8px;margin:20px 0;">
            <p><strong>Ticket:</strong> {issue.ticket_no}</p>
            <p><strong>Kategorie:</strong> {issue.get_category_display()}</p>
            <p><strong>Objekt:</strong> {property_info}</p>
            <p><strong>Beschreibung:</strong> {issue.summary}</p>
            {f'<p><strong>Termin:</strong> {appointment.start.strftime("%d.%m.%Y %H:%M")} Uhr</p>' if appointment.start else ''}
        </div>

        <p>Bitte klicken Sie auf den folgenden Link, um den Auftrag anzunehmen und Details einzusehen:</p>

        <p style="margin: 20px 0;">
            <a href="{vendor_url}"
               style="background:#2563eb;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;display:inline-block;">
                Zum Handwerker-Portal
            </a>
        </p>

        <p>Dieser Link ist <strong>24 Stunden</strong> gültig. Bei Bedarf können Sie jederzeit einen neuen Link über die Hausverwaltung anfordern.</p>

        <p>Alternativ-Link: <a href="{vendor_url}">{vendor_url}</a></p>

        <p>Mit freundlichen Grüßen<br>
        Ihre Hausverwaltung</p>
    </body>
    </html>
    """

    body = strip_tags(html) or _plain_from_html(html)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[vendor.email]
    )
    msg.attach_alternative(html, "text/html")
    msg.send()
