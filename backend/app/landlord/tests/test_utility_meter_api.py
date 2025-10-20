"""
Tests for UtilityMeter API Endpoints (M17 Phase 5)
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from landlord.models import Property, Unit, UtilityMeter, UtilityReading

User = get_user_model()


@pytest.mark.django_db
class TestUtilityMeterAPI:
    """Test API endpoints for utility meter prefill"""

    @pytest.fixture
    def user(self):
        """Create a test user"""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @pytest.fixture
    def property_with_meters(self):
        """Create test data: Property with meters"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        # Default electricity meter
        meter1 = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='ELEC-001',
            is_default=True,
            is_active=True,
            initial_reading_value=Decimal('1000.00')
        )

        # Non-default gas meter
        meter2 = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='gas',
            serial_number='GAS-001',
            is_default=False,
            is_active=True
        )

        return {'property': prop, 'meter1': meter1, 'meter2': meter2}

    def test_api_get_default_meter_success(self, client, user, property_with_meters):
        """Test GET /api/utility/meters/default with valid params"""
        client.force_login(user)
        prop = property_with_meters['property']

        response = client.get(reverse('api_get_default_meter'), {
            'scope_type': 'property',
            'scope_id': prop.id,
            'meter_type': 'electricity'
        })

        assert response.status_code == 200
        data = response.json()

        assert data['serial_number'] == 'ELEC-001'
        assert data['has_multiple'] is False
        assert data['initial_reading_value'] == 1000.00

    def test_api_get_default_meter_missing_params(self, client, user):
        """Test API with missing parameters"""
        client.force_login(user)

        response = client.get(reverse('api_get_default_meter'), {
            'scope_type': 'property',
            # missing scope_id and meter_type
        })

        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'Missing required parameters' in data['error']

    def test_api_get_default_meter_invalid_scope_type(self, client, user):
        """Test API with invalid scope_type"""
        client.force_login(user)

        response = client.get(reverse('api_get_default_meter'), {
            'scope_type': 'invalid',
            'scope_id': '1',
            'meter_type': 'electricity'
        })

        assert response.status_code == 400
        data = response.json()
        assert 'Invalid scope_type' in data['error']

    def test_api_get_default_meter_invalid_scope_id(self, client, user):
        """Test API with invalid scope_id"""
        client.force_login(user)

        response = client.get(reverse('api_get_default_meter'), {
            'scope_type': 'property',
            'scope_id': 'not-a-number',
            'meter_type': 'electricity'
        })

        assert response.status_code == 400
        data = response.json()
        assert 'Invalid scope_id' in data['error']

    def test_api_get_default_meter_no_meter_found(self, client, user, property_with_meters):
        """Test API when no meter exists for the given params"""
        client.force_login(user)
        prop = property_with_meters['property']

        response = client.get(reverse('api_get_default_meter'), {
            'scope_type': 'property',
            'scope_id': prop.id,
            'meter_type': 'hot_water'  # No meter for this type
        })

        assert response.status_code == 200
        data = response.json()

        assert data['meter_id'] is None
        assert data['serial_number'] is None
        assert data['has_multiple'] is False

    def test_api_get_default_meter_multiple_meters(self, client, user):
        """Test API with multiple active meters, no default"""
        client.force_login(user)
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")

        # Two active meters, no default
        UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            serial_number='WATER-1',
            is_default=False,
            is_active=True
        )

        UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            serial_number='WATER-2',
            is_default=False,
            is_active=True
        )

        response = client.get(reverse('api_get_default_meter'), {
            'scope_type': 'unit',
            'scope_id': unit.id,
            'meter_type': 'cold_water'
        })

        assert response.status_code == 200
        data = response.json()

        assert data['has_multiple'] is True
        assert len(data['meters']) == 2
        assert data['meters'][0]['serial_number'] in ['WATER-1', 'WATER-2']

    def test_api_get_last_reading_success(self, client, user, property_with_meters):
        """Test GET /api/utility/meters/last-reading with existing readings"""
        client.force_login(user)
        prop = property_with_meters['property']
        unit = Unit.objects.create(property=prop, unit_label="1A")

        meter = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            is_active=True
        )

        # Create a reading
        UtilityReading.objects.create(
            unit=unit,
            meter_type='water_cold',
            reading_date=date(2024, 6, 1),
            current_value=Decimal('150.50')
        )

        response = client.get(reverse('api_get_last_reading'), {
            'meter_id': meter.id
        })

        assert response.status_code == 200
        data = response.json()

        assert data['previous_value'] == 150.50
        assert data['reading_date'] == '2024-06-01'
        assert data['is_initial'] is False

    def test_api_get_last_reading_with_initial_value(self, client, user, property_with_meters):
        """Test API with no readings but initial_reading_value set"""
        client.force_login(user)
        prop = property_with_meters['property']
        unit = Unit.objects.create(property=prop, unit_label="1A")

        meter = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            is_active=True,
            initial_reading_value=Decimal('500.00'),
            installed_at=date(2024, 1, 15)
        )

        response = client.get(reverse('api_get_last_reading'), {
            'meter_id': meter.id
        })

        assert response.status_code == 200
        data = response.json()

        assert data['previous_value'] == 500.00
        assert data['reading_date'] == '2024-01-15'
        assert data['is_initial'] is True  # UI should show "Erstwert aus Stammdaten"

    def test_api_get_last_reading_missing_meter_id(self, client, user):
        """Test API with missing meter_id"""
        client.force_login(user)

        response = client.get(reverse('api_get_last_reading'))

        assert response.status_code == 400
        data = response.json()
        assert 'Missing required parameter' in data['error']

    def test_api_get_last_reading_invalid_meter_id(self, client, user):
        """Test API with invalid meter_id"""
        client.force_login(user)

        response = client.get(reverse('api_get_last_reading'), {
            'meter_id': 'not-a-number'
        })

        assert response.status_code == 400
        data = response.json()
        assert 'Invalid meter_id' in data['error']

    def test_api_get_last_reading_nonexistent_meter(self, client, user):
        """Test API with nonexistent meter_id"""
        client.force_login(user)

        response = client.get(reverse('api_get_last_reading'), {
            'meter_id': '99999'
        })

        assert response.status_code == 200
        data = response.json()

        assert data['previous_value'] is None
        assert data['reading_date'] is None
        assert data['is_initial'] is False

    def test_api_requires_authentication(self, client, property_with_meters):
        """Test that API endpoints require authentication"""
        prop = property_with_meters['property']

        # Try without login
        response = client.get(reverse('api_get_default_meter'), {
            'scope_type': 'property',
            'scope_id': prop.id,
            'meter_type': 'electricity'
        })

        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.url
