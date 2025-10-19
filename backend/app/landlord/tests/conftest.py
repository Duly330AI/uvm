"""
Shared pytest fixtures for landlord tests
"""
import pytest
from landlord.models import Issue, Property, Tenant, Unit, Vendor


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
        primary_email="tenant@example.com"
    )


@pytest.fixture
def vendor_demo(db):
    """Demo vendor for testing"""
    return Vendor.objects.create(
        name="Krach GmbH",
        email="vendor@example.com",
        trade="Sanitär"
    )


# ============================================================================
# FACTORY FIXTURES (for tests that need to create multiple objects)
# ============================================================================

@pytest.fixture
def property_factory(db):
    """Factory for creating Property instances"""
    created_properties = []
    
    def _create_property(**kwargs):
        defaults = {
            "name": "Test Property",
            "street": "Test Street 1",
            "postal_code": "12345",
            "city": "Test City"
        }
        defaults.update(kwargs)
        prop = Property.objects.create(**defaults)
        created_properties.append(prop)
        return prop
    
    yield _create_property
    
    # Cleanup
    for prop in created_properties:
        prop.delete()


@pytest.fixture
def unit_factory(db, property_factory):
    """Factory for creating Unit instances"""
    created_units = []
    
    def _create_unit(property=None, **kwargs):
        if property is None:
            property = property_factory()
        
        defaults = {
            "property": property,
            "unit_label": f"Unit-{len(created_units) + 1}",
        }
        defaults.update(kwargs)
        unit = Unit.objects.create(**defaults)
        created_units.append(unit)
        return unit
    
    yield _create_unit
    
    # Cleanup
    for unit in created_units:
        unit.delete()


@pytest.fixture
def tenant_factory(db, unit_factory):
    """Factory for creating Tenant instances"""
    created_tenants = []
    counter = [0]  # Use list to allow modification in nested function
    
    def _create_tenant(unit=None, **kwargs):
        if unit is None:
            unit = unit_factory()
        
        counter[0] += 1
        defaults = {
            "unit": unit,
            "primary_email": f"tenant{counter[0]}@example.com",
            "is_active": True,
        }
        defaults.update(kwargs)
        tenant = Tenant.objects.create(**defaults)
        created_tenants.append(tenant)
        return tenant
    
    yield _create_tenant
    
    # Cleanup
    for tenant in created_tenants:
        tenant.delete()


@pytest.fixture
def vendor_factory(db):
    """Factory for creating Vendor instances"""
    created_vendors = []
    counter = [0]
    
    def _create_vendor(**kwargs):
        counter[0] += 1
        defaults = {
            "name": f"Vendor {counter[0]}",
            "email": f"vendor{counter[0]}@example.com",
            "trade": "General",
        }
        defaults.update(kwargs)
        vendor = Vendor.objects.create(**defaults)
        created_vendors.append(vendor)
        return vendor
    
    yield _create_vendor
    
    # Cleanup
    for vendor in created_vendors:
        vendor.delete()


@pytest.fixture
def issue_factory(db, tenant_factory, unit_factory):
    """Factory for creating Issue instances"""
    created_issues = []
    counter = [0]
    
    def _create_issue(tenant=None, unit=None, **kwargs):
        if tenant is None and unit is None:
            unit = unit_factory()
            tenant = tenant_factory(unit=unit)
        elif tenant is None:
            tenant = tenant_factory(unit=unit)
        elif unit is None:
            unit = tenant.unit
        
        counter[0] += 1
        defaults = {
            "tenant": tenant,
            "unit": unit,
            "summary": f"Test Issue {counter[0]}",
            "category": Issue.Category.OTHER,
            "status": Issue.Status.NEW,
            "severity": 3,
        }
        defaults.update(kwargs)
        issue = Issue.objects.create(**defaults)
        created_issues.append(issue)
        return issue
    
    yield _create_issue
    
    # Cleanup
    for issue in created_issues:
        issue.delete()
