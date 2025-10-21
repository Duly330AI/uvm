"""
Unit API Tests - Phase 6
Tests for all Unit API endpoints with RBAC, validation, pagination, etc.
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from landlord.models import Property, Unit, UtilityMeter
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def regular_user(db):
    """Create regular authenticated user"""
    return User.objects.create_user(
        username='user',
        email='user@test.com',
        password='testpass123'
    )


@pytest.fixture
def sample_property(db):
    """Create sample property"""
    return Property.objects.create(
        name="Test Gebäude",
        street="Teststraße 123",
        postal_code="12345",
        city="Berlin",
        country="DE"
    )


@pytest.fixture
def sample_units(db, sample_property):
    """Create sample units for testing"""
    units = []
    units.append(Unit.objects.create(
        property=sample_property,
        unit_label="A1",
        floor="EG",
        rooms=3,
        area_sqm=Decimal("85.50"),
        is_active=True
    ))
    units.append(Unit.objects.create(
        property=sample_property,
        unit_label="A2",
        floor="1. OG",
        rooms=2,
        area_sqm=Decimal("65.00"),
        is_active=True
    ))
    units.append(Unit.objects.create(
        property=sample_property,
        unit_label="B1",
        floor="EG",
        rooms=4,
        area_sqm=Decimal("120.00"),
        is_active=False
    ))
    return units


@pytest.mark.django_db
class TestUnitListAPI:
    """Tests for GET /api/portal/units/"""

    def test_list_requires_authentication(self, api_client):
        """Unauthenticated requests are rejected"""
        url = reverse('portal-units-list')
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_returns_200_authenticated(self, api_client, regular_user, sample_units):
        """Authenticated users can list units"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_list_pagination_default_25(self, api_client, regular_user, sample_property, db):
        """Default pagination is 25 items per page"""
        # Create 30 units
        for i in range(30):
            Unit.objects.create(
                property=sample_property,
                unit_label=f"Unit {i}"
            )

        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 25
        assert response.data['count'] == 30

    def test_list_filter_by_property(self, api_client, regular_user, sample_units, sample_property):
        """Filter by property_id"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-list')
        response = api_client.get(url, {'property_id': sample_property.id})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3
        for unit in response.data['results']:
            assert unit['property_id'] == sample_property.id

    def test_list_filter_by_is_active(self, api_client, regular_user, sample_units):
        """Filter by is_active status"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-list')

        # Filter for active
        response = api_client.get(url, {'is_active': 'true'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

        # Filter for inactive
        response = api_client.get(url, {'is_active': 'false'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_list_filter_archived_false_default(self, api_client, regular_user, sample_units, admin_user):
        """Archived units are excluded by default"""
        # Archive one unit
        unit = sample_units[0]
        unit.archive(admin_user)

        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2  # 3 - 1 archived

    def test_list_search_by_unit_label(self, api_client, regular_user, sample_units):
        """Search by unit_label"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-list')
        response = api_client.get(url, {'query': 'A1'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['unit_label'] == 'A1'

    def test_list_sort_by_unit_label(self, api_client, regular_user, sample_units):
        """Sort by unit_label"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-list')
        response = api_client.get(url, {'sort': 'unit_label', 'order': 'asc'})

        assert response.status_code == status.HTTP_200_OK
        labels = [u['unit_label'] for u in response.data['results']]
        assert labels == sorted(labels)


@pytest.mark.django_db
class TestUnitDetailAPI:
    """Tests for GET /api/portal/units/{id}/"""

    def test_detail_requires_authentication(self, api_client, sample_units):
        """Unauthenticated requests are rejected"""
        url = reverse('portal-units-detail', kwargs={'pk': sample_units[0].id})
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_detail_returns_200_authenticated(self, api_client, regular_user, sample_units):
        """Authenticated users can view unit details"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-detail', kwargs={'pk': sample_units[0].id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_detail_includes_all_fields(self, api_client, regular_user, sample_units):
        """Detail response includes all unit fields"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-detail', kwargs={'pk': sample_units[0].id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert 'id' in data
        assert 'property_id' in data
        assert 'property_name' in data
        assert 'unit_label' in data
        assert 'floor' in data
        assert 'rooms' in data
        assert 'area_sqm' in data
        assert 'notes' in data
        assert 'is_active' in data
        assert 'is_archived' in data
        assert 'meters' in data

    def test_detail_includes_meters(self, api_client, regular_user, sample_units):
        """Detail includes nested meters list"""
        unit = sample_units[0]

        # Create a meter for this unit
        UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            is_default=True,
            is_active=True
        )

        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-detail', kwargs={'pk': unit.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'meters' in response.data
        assert len(response.data['meters']) == 1
        assert response.data['meters'][0]['meter_type'] == 'cold_water'


@pytest.mark.django_db
class TestUnitCreateAPI:
    """Tests for POST /api/portal/units/create/"""

    def test_create_requires_authentication(self, api_client, sample_property):
        """Unauthenticated requests are rejected"""
        url = reverse('portal-units-create')
        data = {
            'property': sample_property.id,
            'unit_label': 'New Unit'
        }
        response = api_client.post(url, data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_requires_admin(self, api_client, regular_user, sample_property):
        """Regular users cannot create units"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-create')
        data = {
            'property': sample_property.id,
            'unit_label': 'New Unit'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_success_admin(self, api_client, admin_user, sample_property):
        """Admin can create units"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-create')
        data = {
            'property': sample_property.id,
            'unit_label': 'New Unit',
            'floor': '2. OG',
            'rooms': 3,
            'area_sqm': '75.00',
            'is_active': True
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Unit.objects.filter(unit_label='New Unit').exists()

    def test_create_validation_required_fields(self, api_client, admin_user):
        """Create fails without required fields"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-create')
        data = {}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'property' in response.data or 'unit_label' in response.data

    def test_create_validation_archived_property(self, api_client, admin_user, sample_property):
        """Cannot create unit for archived property"""
        # Archive property
        sample_property.archive(admin_user)

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-create')
        data = {
            'property': sample_property.id,
            'unit_label': 'New Unit'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'property' in response.data


@pytest.mark.django_db
class TestUnitUpdateAPI:
    """Tests for PATCH /api/portal/units/{id}/update/"""

    def test_update_requires_admin(self, api_client, regular_user, sample_units):
        """Regular users cannot update units"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-units-update', kwargs={'pk': sample_units[0].id})
        data = {'unit_label': 'Updated'}
        response = api_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_success_admin(self, api_client, admin_user, sample_units):
        """Admin can update units"""
        unit = sample_units[0]
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-update', kwargs={'pk': unit.id})
        data = {'unit_label': 'Updated Label'}
        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        unit.refresh_from_db()
        assert unit.unit_label == 'Updated Label'


@pytest.mark.django_db
class TestUnitArchiveAPI:
    """Tests for POST /api/portal/units/{id}/archive/"""

    def test_archive_success_admin(self, api_client, admin_user, sample_units):
        """Admin can archive units"""
        unit = sample_units[0]
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-archive', kwargs={'pk': unit.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        unit.refresh_from_db()
        assert unit.is_archived is True
        assert unit.archived_by == admin_user

    def test_archive_already_archived(self, api_client, admin_user, sample_units):
        """Cannot archive already archived unit"""
        unit = sample_units[0]
        unit.archive(admin_user)

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-archive', kwargs={'pk': unit.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUnitUnarchiveAPI:
    """Tests for POST /api/portal/units/{id}/unarchive/"""

    def test_unarchive_success_admin(self, api_client, admin_user, sample_units):
        """Admin can unarchive units"""
        unit = sample_units[0]
        unit.archive(admin_user)

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-unarchive', kwargs={'pk': unit.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        unit.refresh_from_db()
        assert unit.is_archived is False

    def test_unarchive_archived_property_fails(self, api_client, admin_user, sample_units, sample_property):
        """Cannot unarchive unit if property is archived"""
        unit = sample_units[0]
        unit.archive(admin_user)
        sample_property.archive(admin_user)

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-unarchive', kwargs={'pk': unit.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'reason' in response.data


@pytest.mark.django_db
class TestUnitDeleteAPI:
    """Tests for DELETE /api/portal/units/{id}/delete/"""

    def test_delete_success_admin(self, api_client, admin_user, sample_property):
        """Admin can delete unit without dependencies"""
        unit = Unit.objects.create(
            property=sample_property,
            unit_label="Delete Me"
        )

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-delete', kwargs={'pk': unit.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Unit.objects.filter(id=unit.id).exists()

    def test_delete_with_meters_fails(self, api_client, admin_user, sample_units):
        """Cannot delete unit with meters"""
        unit = sample_units[0]

        # Create a meter
        UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water'
        )

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-units-delete', kwargs={'pk': unit.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'dependencies' in response.data
        assert Unit.objects.filter(id=unit.id).exists()
