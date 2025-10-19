import pytest
from django.contrib.auth.models import User
from landlord.models import Issue, Property, Tenant, Unit


@pytest.mark.django_db
def test_issues_export_csv_filters_and_headers(client):
    admin = User.objects.create_superuser("a","a@example.com","x")
    client.force_login(admin)

    prop = Property.objects.create(name="Haus 1", street="S", postal_code="12345", city="Berlin")
    unit = Unit.objects.create(property=prop, unit_label="WE 1")
    t = Tenant.objects.create(unit=unit, primary_email="mieter@example.com")
    Issue.objects.create(ticket_no="TCK-2025-00001", status="NEW", severity=4, summary="Wasser", unit=unit, tenant=t)
    Issue.objects.create(ticket_no="TCK-2025-00002", status="DONE", severity=2, summary="Heizung", unit=unit, tenant=t)

    r = client.get("/api/admin/issues/export.csv?status=NEW")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/csv")
    body = r.content.decode()
    lines = [ln for ln in body.splitlines() if ln.strip()]
    assert "ticket_no,status,category,severity,created_at,property,unit,tenant_email,summary" in lines[0]
    assert any("TCK-2025-00001" in ln for ln in lines[1:])
    assert all("TCK-2025-00002" not in ln for ln in lines[1:])
