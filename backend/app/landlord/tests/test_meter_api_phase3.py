"""
Utility Meter API Tests - Phase 3
Tests for nested Meter CRUD under Property
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from landlord.models import Property, UtilityMeter

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin', email='admin@test.com',
        password='test123', is_staff=True, is_superuser=True
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='user', email='user@test.com', password='test123'
    )


@pytest.fixture
def sample_property(db):
    return Property.objects.create(
        name="Test Property",
        street="Test St 1",
        postal_code="12345",
        city="Berlin",
        country="DE"
    )


@pytest.fixture
def sample_meter(db, sample_property):
    return UtilityMeter.objects.create(
        scope_type='property',
        property=sample_property,
        meter_type='cold_water',
        serial_number='ABC123',
        is_default=True
    )


@pytest.mark.django_db
class TestPropertyMeterListAPI:
    def test_list_requires_auth(self, api_client, sample_property):
        url = reverse('portal-property-meters-list', kwargs={'property_id': sample_property.pk})
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_list_returns_meters(self, api_client, regular_user, sample_property, sample_meter):
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-property-meters-list', kwargs={'property_id': sample_property.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


@pytest.mark.django_db
class TestPropertyMeterCreateAPI:
    def test_create_requires_admin(self, api_client, regular_user, sample_property):
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-property-meters-create', kwargs={'property_id': sample_property.pk})
        data = {
            'scope_type': 'property',
            'property': sample_property.pk,
            'meter_type': 'cold_water',
            'serial_number': 'NEW123'
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_success_admin(self, api_client, admin_user, sample_property):
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-property-meters-create', kwargs={'property_id': sample_property.pk})
        data = {
            'scope_type': 'property',
            'property': sample_property.pk,
            'meter_type': 'cold_water',
            'serial_number': 'NEW123',
            'is_default': True
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert UtilityMeter.objects.filter(serial_number='NEW123').exists()


@pytest.mark.django_db
class TestPropertyMeterUpdateAPI:
    def test_update_sets_default_clears_others(self, api_client, admin_user, sample_property, sample_meter):
        # Create second meter
        meter2 = UtilityMeter.objects.create(
            scope_type='property',
            property=sample_property,
            meter_type='cold_water',
            serial_number='DEF456',
            is_default=False
        )
        
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-property-meters-update', kwargs={
            'property_id': sample_property.pk,
            'pk': meter2.pk
        })
        data = {'is_default': True}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify only meter2 is default now
        sample_meter.refresh_from_db()
        meter2.refresh_from_db()
        assert sample_meter.is_default is False
        assert meter2.is_default is True


@pytest.mark.django_db
class TestPropertyMeterDeleteAPI:
    def test_delete_success_no_readings(self, api_client, admin_user, sample_property, sample_meter):
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-property-meters-delete', kwargs={
            'property_id': sample_property.pk,
            'pk': sample_meter.pk
        })
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UtilityMeter.objects.filter(pk=sample_meter.pk).exists()
