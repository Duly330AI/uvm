import pytest
from landlord.models import Property, Tenant, Unit


@pytest.mark.django_db
def test_create_property_unit_tenant():
    p = Property.objects.create(street="Teststr. 1", postal_code="00000", city="X")
    u = Unit.objects.create(property=p, unit_label="WE 1")
    t = Tenant.objects.create(primary_email="t@example.com", unit=u)
    assert t.pk is not None
    assert u.property_id == p.id
