import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from landlord.models import Issue, Property, Tenant, Unit
from landlord.models import Issue as IssueModel


@pytest.mark.django_db
def test_admin_action_mark_in_progress(client):
    admin = User.objects.create_superuser("admin", "admin@example.com", "pw")
    client.force_login(admin)

    prop = Property.objects.create(name="Haus 1", street="Str", postal_code="12345", city="Berlin")
    unit = Unit.objects.create(property=prop, unit_label="WE 1")
    tenant = Tenant.objects.create(unit=unit, primary_email="tenant@example.com")
    issue = Issue.objects.create(ticket_no="TCK-2025-00044", status=IssueModel.Status.NEW, summary="Test", unit=unit, tenant=tenant)

    url = reverse("admin:landlord_issue_changelist")
    res = client.post(
        url,
        {
            "action": "mark_in_progress",
            "_selected_action": [issue.id],
            "select_across": 0,
            "index": 0,
        },
        follow=True,
    )
    assert res.status_code == 200
    issue.refresh_from_db()
    assert issue.status == IssueModel.Status.IN_PROGRESS
