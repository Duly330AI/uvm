import pytest
from django.contrib.auth.models import User
from landlord.models import Issue, IssueNote, Property, Tenant, Unit


@pytest.mark.django_db
def test_tenant_erase_idempotent(client):
    admin = User.objects.create_superuser("a","a@example.com","x")
    client.force_login(admin)

    p = Property.objects.create(name="Haus", street="S", postal_code="1", city="B")
    u = Unit.objects.create(property=p, unit_label="WE 1")
    t = Tenant.objects.create(unit=u, primary_email="tenant@example.com")
    i = Issue.objects.create(ticket_no="TCK-2025-00011", status="NEW", summary="Wasser", tenant=t, unit=u)

    r1 = client.post(f"/api/admin/tenants/{t.id}/erase")
    assert r1.status_code == 200
    r2 = client.post(f"/api/admin/tenants/{t.id}/erase")
    assert r2.status_code == 200

    t.refresh_from_db()
    assert t.primary_email in (None, "erased@example.invalid")

    # Exactly one audit marker per issue
    marker_count = IssueNote.objects.filter(issue=i, text__icontains="PII erased for tenant").count()
    assert marker_count == 1
