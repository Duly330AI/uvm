"""
Tests for UtilityMeter Model (M17: Default Meter Prefill)
"""
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from landlord.models import Property, Unit, UtilityMeter


@pytest.mark.django_db
class TestUtilityMeterModel:
    """Test UtilityMeter model basics"""

    def test_create_property_meter(self):
        """Test creating a meter for a property (building-level)"""
        prop = Property.objects.create(
            name="Test Building",
            street="Test St",
            postal_code="12345",
            city="Test City"
        )

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='ABC123',
            is_default=True,
            is_active=True
        )

        assert meter.scope_type == 'property'
        assert meter.property == prop
        assert meter.unit is None
        assert meter.serial_number == 'ABC123'
        assert meter.is_default is True
        assert str(meter).startswith('Strom')

    def test_create_unit_meter(self):
        """Test creating a meter for a unit (apartment-level)"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="1A")

        meter = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water',
            serial_number='WATER-001',
            is_default=True
        )

        assert meter.scope_type == 'unit'
        assert meter.unit == unit
        assert meter.property is None
        assert meter.get_reading_unit() == 'm³'

    def test_multiple_meters_per_medium_allowed(self):
        """Test that multiple meters per medium are allowed (e.g., complex heating systems)"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")

        # Create first meter (default)
        meter1 = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='heating',
            serial_number='HEAT-001',
            is_default=True
        )

        # Create second meter (not default) - should work
        meter2 = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='heating',
            serial_number='HEAT-002',
            is_default=False
        )

        assert UtilityMeter.objects.filter(unit=unit, meter_type='heating').count() == 2

    def test_only_one_default_per_scope_and_type_constraint(self):
        """Test DB constraint: only ONE default per (scope_type, scope_id, meter_type)"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        # Create first default meter
        UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            is_default=True
        )

        # Try to create second default - should fail
        with pytest.raises(IntegrityError):
            UtilityMeter.objects.create(
                scope_type='property',
                property=prop,
                meter_type='electricity',
                is_default=True
            )

    def test_clean_validation_scope_consistency(self):
        """Test clean() validation for scope consistency"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")

        # Property scope WITHOUT property - should fail
        meter = UtilityMeter(
            scope_type='property',
            meter_type='electricity'
        )
        with pytest.raises(ValidationError, match="Property-Zuordnung"):
            meter.clean()

        # Unit scope WITHOUT unit - should fail
        meter = UtilityMeter(
            scope_type='unit',
            meter_type='electricity'
        )
        with pytest.raises(ValidationError, match="Unit-Zuordnung"):
            meter.clean()

        # Property scope WITH unit (and no property) - should fail with first error
        meter = UtilityMeter(
            scope_type='property',
            unit=unit,
            meter_type='electricity'
        )
        with pytest.raises(ValidationError):  # Will fail on missing property first
            meter.clean()

        # Unit scope WITH property (and no unit) - should fail with first error
        meter = UtilityMeter(
            scope_type='unit',
            property=prop,
            meter_type='electricity'
        )
        with pytest.raises(ValidationError):  # Will fail on missing unit first
            meter.clean()

    def test_clean_validation_default_uniqueness(self):
        """Test clean() validation for default uniqueness"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        # Create first default
        meter1 = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='gas',
            is_default=True
        )

        # Try to create second default via clean()
        meter2 = UtilityMeter(
            scope_type='property',
            property=prop,
            meter_type='gas',
            is_default=True
        )

        with pytest.raises(ValidationError, match="nur ein Standardzähler"):
            meter2.clean()

    def test_initial_reading_value(self):
        """Test initial_reading_value field"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='ELEC-001',
            initial_reading_value=Decimal('14155.50')
        )

        assert meter.initial_reading_value == Decimal('14155.50')

    def test_installed_and_removed_dates(self):
        """Test installed_at and removed_at fields"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            installed_at=date(2024, 1, 15),
            removed_at=None,
            is_active=True
        )

        assert meter.installed_at == date(2024, 1, 15)
        assert meter.removed_at is None
        assert meter.is_active is True

    def test_reading_unit_property(self):
        """Test get_reading_unit() method"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        # Water meters → m³
        meter_water = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='cold_water'
        )
        assert meter_water.get_reading_unit() == 'm³'

        # Electricity → kWh
        meter_elec = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity'
        )
        assert meter_elec.get_reading_unit() == 'kWh'

        # Gas → kWh (spec: Gas in kWh!)
        meter_gas = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='gas'
        )
        assert meter_gas.get_reading_unit() == 'kWh'

    def test_get_scope_object(self):
        """Test get_scope_object() method"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")

        # Property meter
        meter_prop = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity'
        )
        assert meter_prop.get_scope_object() == prop

        # Unit meter
        meter_unit = UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='cold_water'
        )
        assert meter_unit.get_scope_object() == unit
