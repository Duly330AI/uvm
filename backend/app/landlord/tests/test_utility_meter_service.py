"""
Tests for UtilityMeterService (M17: Default Meter Prefill)
"""
import pytest
from decimal import Decimal
from datetime import date

from landlord.models import Property, Unit, UtilityMeter, UtilityReading
from landlord.services.utility_meter_service import (
    UtilityMeterService,
    get_default_meter,
    get_last_reading
)


@pytest.mark.django_db
class TestUtilityMeterService:
    """Test UtilityMeterService business logic"""
    
    def test_get_default_meter_case_a_default_exists(self):
        """
        Case A: Default vorhanden → return default meter
        Spec Kap. 3.3.2.A
        """
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        
        # Create default meter
        meter_default = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='DEFAULT-001',
            is_default=True,
            is_active=True,
            initial_reading_value=Decimal('14155.50')
        )
        
        # Create another active meter (not default)
        UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='OTHER-002',
            is_default=False,
            is_active=True
        )
        
        result = get_default_meter('property', prop.id, 'electricity')
        
        assert result['meter_id'] == meter_default.id
        assert result['serial_number'] == 'DEFAULT-001'
        assert result['has_multiple'] is False
        assert result['initial_reading_value'] == Decimal('14155.50')
        assert result['meters'] == []
    
    def test_get_default_meter_case_b_single_active(self):
        """
        Case B: Kein Default, genau 1 aktiver → return aktiver
        Spec Kap. 3.3.2.B
        """
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")
        
        # Create single active meter (no default)
        meter = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            serial_number='WATER-001',
            is_default=False,
            is_active=True
        )
        
        result = get_default_meter('unit', unit.id, 'cold_water')
        
        assert result['meter_id'] == meter.id
        assert result['serial_number'] == 'WATER-001'
        assert result['has_multiple'] is False
        assert result['meters'] == []
    
    def test_get_default_meter_case_c_multiple_active(self):
        """
        Case C: Mehrere aktive, kein Default → return list
        Spec Kap. 3.3.2.C
        """
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")
        
        # Create multiple active meters (no default)
        meter1 = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='hot_water',
            serial_number='HEAT-001',
            is_default=False,
            is_active=True,
            installed_at=date(2024, 1, 15)
        )
        
        meter2 = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='hot_water',
            serial_number='HEAT-002',
            is_default=False,
            is_active=True,
            installed_at=date(2024, 6, 20)
        )
        
        result = get_default_meter('unit', unit.id, 'hot_water')
        
        assert result['meter_id'] is None  # User must choose
        assert result['serial_number'] is None
        assert result['has_multiple'] is True
        assert len(result['meters']) == 2
        
        # Check meters list format (spec Kap. 3.3 Dropdown-Format)
        assert result['meters'][0]['meter_id'] in [meter1.id, meter2.id]
        assert 'serial_number' in result['meters'][0]
        assert 'meter_type_label' in result['meters'][0]
        assert 'installed_at' in result['meters'][0]
    
    def test_get_default_meter_case_d_no_meter(self):
        """
        Case D: Kein Zähler gefunden → return None
        Spec Kap. 3.3.2.D
        """
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        
        result = get_default_meter('property', prop.id, 'gas')
        
        assert result['meter_id'] is None
        assert result['serial_number'] is None
        assert result['has_multiple'] is False
        assert result['initial_reading_value'] is None
        assert result['meters'] == []
    
    def test_get_default_meter_ignores_inactive_meters(self):
        """Test that inactive meters are not considered"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        
        # Create inactive meter
        UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='INACTIVE-001',
            is_default=True,
            is_active=False  # ← inactive!
        )
        
        result = get_default_meter('property', prop.id, 'electricity')
        
        # Should return Case D (no meter found)
        assert result['meter_id'] is None
        assert result['has_multiple'] is False
    
    def test_get_last_reading_with_existing_readings(self):
        """
        Test get_last_reading when readings exist
        Spec Kap. 3.3: Vorheriger Zählerstand
        """
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")
        
        meter = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            is_active=True
        )
        
        # Create readings
        UtilityReading.objects.create(
            unit=unit,
            meter_type='water_cold',
            reading_date=date(2024, 1, 1),
            current_value=Decimal('100.00')
        )
        
        last_reading = UtilityReading.objects.create(
            unit=unit,
            meter_type='water_cold',
            reading_date=date(2024, 6, 1),
            current_value=Decimal('150.50')
        )
        
        result = get_last_reading(meter.id)
        
        assert result['previous_value'] == 150.50
        assert result['reading_date'] == '2024-06-01'
        assert result['is_initial'] is False
    
    def test_get_last_reading_with_initial_value_only(self):
        """
        Test get_last_reading when no readings exist, but initial_reading_value is set
        Spec Kap. 3.3: "einmalig als vorheriger Stand"
        """
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")
        
        meter = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            is_active=True,
            initial_reading_value=Decimal('14155.50'),
            installed_at=date(2024, 1, 15)
        )
        
        # No readings exist yet
        result = get_last_reading(meter.id)
        
        assert result['previous_value'] == 14155.50
        assert result['reading_date'] == '2024-01-15'
        assert result['is_initial'] is True  # UI should show "Erstwert aus Stammdaten"
    
    def test_get_last_reading_no_readings_no_initial(self):
        """Test get_last_reading when neither readings nor initial_value exist"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")
        
        meter = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            is_active=True
        )
        
        result = get_last_reading(meter.id)
        
        assert result['previous_value'] is None
        assert result['reading_date'] is None
        assert result['is_initial'] is False
    
    def test_get_last_reading_nonexistent_meter(self):
        """Test get_last_reading with invalid meter_id"""
        result = get_last_reading(99999)
        
        assert result['previous_value'] is None
        assert result['reading_date'] is None
        assert result['is_initial'] is False
    
    def test_empty_serial_number_handled(self):
        """Test that meters with empty serial_number are handled correctly"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        
        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='',  # Empty!
            is_default=True,
            is_active=True
        )
        
        result = get_default_meter('property', prop.id, 'electricity')
        
        assert result['meter_id'] == meter.id
        assert result['serial_number'] == ''  # Empty string, not None
        assert result['has_multiple'] is False
