import pytest
from django.contrib.auth.models import User
from landlord.models import Issue, IssueNote, Property, Tenant, Unit


@pytest.mark.django_db
def test_tenant_export_and_erase(client):
    admin = User.objects.create_superuser("a","a@example.com","x")
    client.force_login(admin)

    p = Property.objects.create(name="Haus", street="S", postal_code="1", city="B")
    u = Unit.objects.create(property=p, unit_label="WE 1")
    t = Tenant.objects.create(unit=u, primary_email="tenant@example.com")
    i = Issue.objects.create(ticket_no="TCK-2025-00010", status="NEW", summary="Wasser", tenant=t, unit=u)

    r = client.get(f"/api/admin/tenants/{t.id}/export")
    assert r.status_code == 200
    data = r.json()
    assert data["tenant"]["primary_email"] == "tenant@example.com"
    assert any(it["ticket_no"] == "TCK-2025-00010" for it in data["issues"])  # type: ignore[index]

    r2 = client.post(f"/api/admin/tenants/{t.id}/erase")
    assert r2.status_code == 200

    t.refresh_from_db()
    assert t.primary_email in (None, "erased@example.invalid")

    assert IssueNote.objects.filter(issue=i).exists()
