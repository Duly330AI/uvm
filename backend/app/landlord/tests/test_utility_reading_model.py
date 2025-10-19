"""
Tests for UtilityReading Model (M14)
"""
import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model

from landlord.models import UtilityReading, Unit, Property

User = get_user_model()


@pytest.mark.django_db
class TestUtilityReadingModel:
    """Test UtilityReading Model functionality"""

    def test_create_utility_reading(self):
        """Test creating a basic utility reading"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        reading = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.WATER_COLD,
            reading_date=date.today(),
            current_value=Decimal("150.50"),
            meter_number="WZ12345"
        )
        
        assert reading.pk is not None
        assert reading.unit == unit
        assert reading.meter_type == UtilityReading.MeterType.WATER_COLD
        assert reading.current_value == Decimal("150.50")
        assert reading.meter_number == "WZ12345"
        assert reading.consumption is None  # No previous value

    def test_auto_calculate_consumption(self):
        """Test automatic consumption calculation"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        # Create reading with previous value
        reading = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.HEATING,
            reading_date=date.today(),
            current_value=Decimal("500.00"),
            previous_value=Decimal("450.00")
        )
        
        assert reading.consumption == Decimal("50.00")

    def test_auto_set_previous_value_from_last_reading(self):
        """Test automatic previous_value from last reading"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        # First reading
        reading1 = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.ELECTRICITY,
            reading_date=date(2025, 1, 1),
            current_value=Decimal("1000.00")
        )
        assert reading1.previous_value is None
        assert reading1.consumption is None
        
        # Second reading - should auto-set previous_value
        reading2 = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.ELECTRICITY,
            reading_date=date(2025, 2, 1),
            current_value=Decimal("1050.00")
        )
        assert reading2.previous_value == Decimal("1000.00")
        assert reading2.consumption == Decimal("50.00")

    def test_different_meter_types_independent(self):
        """Test that different meter types are independent"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        # Create water reading
        water = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.WATER_COLD,
            reading_date=date(2025, 1, 1),
            current_value=Decimal("100.00")
        )
        
        # Create electricity reading - should not use water as previous
        electricity = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.ELECTRICITY,
            reading_date=date(2025, 1, 1),
            current_value=Decimal("200.00")
        )
        
        assert electricity.previous_value is None

    def test_unique_constraint_unit_type_date(self):
        """Test unique constraint: one reading per unit/type/date"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        # First reading
        UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.GAS,
            reading_date=date(2025, 1, 1),
            current_value=Decimal("500.00")
        )
        
        # Try duplicate - should fail
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            UtilityReading.objects.create(
                unit=unit,
                meter_type=UtilityReading.MeterType.GAS,
                reading_date=date(2025, 1, 1),
                current_value=Decimal("600.00")
            )

    def test_reading_with_recorded_by(self):
        """Test reading with recorded_by user"""
        user = User.objects.create_user(username='staff', password='test123')
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        reading = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.HEATING,
            reading_date=date.today(),
            current_value=Decimal("300.00"),
            recorded_by=user
        )
        
        assert reading.recorded_by == user

    def test_str_representation(self):
        """Test __str__ method"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        reading = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.WATER_HOT,
            reading_date=date(2025, 10, 19),
            current_value=Decimal("75.25")
        )
        
        str_repr = str(reading)
        assert "Warmwasser" in str_repr
        assert "A1" in str_repr
        assert "2025-10-19" in str_repr
        assert "75.25" in str_repr

    def test_ordering_by_date(self):
        """Test default ordering (newest first)"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        
        reading1 = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.HEATING,
            reading_date=date(2025, 1, 1),
            current_value=Decimal("100.00")
        )
        reading2 = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.HEATING,
            reading_date=date(2025, 3, 1),
            current_value=Decimal("200.00")
        )
        reading3 = UtilityReading.objects.create(
            unit=unit,
            meter_type=UtilityReading.MeterType.HEATING,
            reading_date=date(2025, 2, 1),
            current_value=Decimal("150.00")
        )
        
        # Should be ordered newest first
        readings = list(UtilityReading.objects.all())
        assert readings[0] == reading2  # March (newest)
        assert readings[1] == reading3  # February
        assert readings[2] == reading1  # January (oldest)
