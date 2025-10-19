from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from landlord.models import Appointment, Issue, Property, Tenant, Unit, Vendor
from landlord.tasks import send_appointment_invite


@pytest.mark.django_db
def test_send_appointment_invite_includes_ics(use_locmem_email_backend, settings):
    settings.SITE_DOMAIN = "localhost"
    prop = Property.objects.create(name="Haus 1", street="Str", postal_code="12345", city="Berlin")
    unit = Unit.objects.create(property=prop, unit_label="WE 1")
    tenant = Tenant.objects.create(unit=unit, primary_email="tenant@example.com")
    issue = Issue.objects.create(ticket_no="TCK-2025-00043", summary="Heizung kalt", tenant=tenant, unit=unit)
    vendor = Vendor.objects.create(name="Krach", trade="Sanitär")
    start = timezone.now() + timedelta(days=1)
    end = start + timedelta(hours=1)
    appt = Appointment.objects.create(issue=issue, vendor=vendor, start=start, end=end)

    send_appointment_invite(appt.id)

    assert len(mail.outbox) == 1
    m = mail.outbox[0]
    cal = next((a for a in m.attachments if isinstance(a, tuple) and str(a[2]).split(";")[0].strip() == "text/calendar"), None)
    ics_bytes = None
    if cal is not None:
        filename, content, mime = cal
        ics_bytes = content if isinstance(content, (bytes, bytearray)) else str(content).encode("utf-8")
    else:
        # Fallback: walk MIME parts
        em = m.message()
        for part in em.walk():
            if part.get_content_type() == "text/calendar":
                ics_bytes = part.get_payload(decode=True)
                break
    assert ics_bytes, "ICS-Anhang fehlt"
    body = ics_bytes.decode("utf-8", "ignore")
    assert "METHOD:REQUEST" in body
    assert "UID:" in body
    assert "DTSTART:" in body and "DTEND:" in body
    assert "\r\nEND:VCALENDAR\r\n" in body

