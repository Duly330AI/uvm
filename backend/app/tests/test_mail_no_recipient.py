import pytest
from django.core import mail
from landlord.models import Issue, Property, Unit
from landlord.tasks import send_issue_created


@pytest.mark.django_db
def test_no_recipient_no_email(use_locmem_email_backend):
    prop = Property.objects.create(name="Haus 1", street="Str", postal_code="12345", city="Berlin")
    unit = Unit.objects.create(property=prop, unit_label="WE 1")
    issue = Issue.objects.create(ticket_no="TCK-2025-00045", summary="Kein Strom", unit=unit)
    send_issue_created(issue.id)
    assert len(mail.outbox) == 0
