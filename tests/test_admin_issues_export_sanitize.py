import pytest
from django.contrib.auth.models import User
from landlord.models import Issue, Property, Tenant, Unit


@pytest.mark.django_db
def test_issues_export_csv_sanitizes_text(client):
    admin = User.objects.create_superuser("a","a@example.com","x")
    client.force_login(admin)

    prop = Property.objects.create(name="=PROP", street="S", postal_code="12345", city="Berlin")
    unit = Unit.objects.create(property=prop, unit_label="+UNIT")
    t = Tenant.objects.create(unit=unit, primary_email="-evil@example.com")
    Issue.objects.create(ticket_no="TCK-2025-09999", status="NEW", severity=4, summary="@=cmd",
                         unit=unit, tenant=t)

    r = client.get("/api/admin/issues/export.csv?status=NEW")
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")  # handle BOM
    # Expect leading ' added
    assert "'=PROP" in text
    assert "'+UNIT" in text
    assert "'-evil@example.com" in text
    assert "'@=cmd" in text
