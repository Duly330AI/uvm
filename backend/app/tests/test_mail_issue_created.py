import pytest
from django.core import mail
from landlord.models import Issue, Property, Tenant, Unit
from landlord.tasks import send_issue_created


@pytest.mark.django_db
def test_send_issue_created_mail(use_locmem_email_backend):
    prop = Property.objects.create(name="Haus 1", street="Str", postal_code="12345", city="Berlin")
    unit = Unit.objects.create(property=prop, unit_label="WE 1")
    tenant = Tenant.objects.create(unit=unit, primary_email="tenant@example.com")
    issue = Issue.objects.create(ticket_no="TCK-2025-00042", summary="Kein Wasser im Bad", tenant=tenant, unit=unit)

    send_issue_created(issue.id)

    assert len(mail.outbox) == 1
    m = mail.outbox[0]
    assert f"[{issue.ticket_no}]" in m.subject
    assert ("Kein Wasser im Bad" in (m.body or "")) or any("Kein Wasser im Bad" in alt for alt, _ in getattr(m, "alternatives", []))
