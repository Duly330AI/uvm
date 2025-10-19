"""
Shared pytest fixtures for landlord tests
"""
import pytest
from landlord.models import Property, Tenant, Unit, Vendor


@pytest.fixture
def prop_demo(db):
    """Demo property for testing"""
    return Property.objects.create(
        name="Demo Property",
        street="Test Street 123",
        postal_code="12345",
        city="Test City"
    )


@pytest.fixture
def unit_a(db, prop_demo):
    """Demo unit A for testing"""
    return Unit.objects.create(
        property=prop_demo,
        unit_label="A"
    )


@pytest.fixture
def tenant_demo(db, unit_a):
    """Demo tenant for testing"""
    return Tenant.objects.create(
        unit=unit_a,
        primary_email="tenant@example.com",
        first_name="Test",
        last_name="Tenant"
    )


@pytest.fixture
def vendor_demo(db):
    """Demo vendor for testing"""
    return Vendor.objects.create(
        name="Krach GmbH",
        email="vendor@example.com",
        trade="Sanitär"
    )
