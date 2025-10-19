import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from landlord.models import Issue, Property, Tenant, Unit


@pytest.mark.django_db
def test_admin_issues_filter_search_order(client):
    admin = User.objects.create_superuser("admin","a@x.de","pw")
    client.force_login(admin)
    prop = Property.objects.create(name="Haus A", street="x", postal_code="1", city="B")
    unit = Unit.objects.create(property=prop, unit_label="WE 1")
    t = Tenant.objects.create(unit=unit, primary_email="mieter@example.com")
    i1 = Issue.objects.create(ticket_no="TCK-2025-00010", unit=unit, tenant=t, status="NEW", severity=3, summary="Wasser")
    i2 = Issue.objects.create(ticket_no="TCK-2025-00011", unit=unit, tenant=t, status="IN_PROGRESS", severity=5, summary="Heizung")

    url = reverse("admin-issues-list")
    r = client.get(url, {"status":"NEW", "property":prop.id, "search":"00010", "ordering":"-created_at"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["results"][0]["ticket_no"] == i1.ticket_no
