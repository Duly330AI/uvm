"""
UtilityMeter Model Tests for Phase 1
Tests for Tasks 1.5 & 1.6

Tests cover:
- Task 1.5: Partial Unique Constraint (already exists, verify it works)
- Task 1.6: Serial number normalization to uppercase
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from landlord.models import Property, UtilityMeter


@pytest.mark.django_db
class TestUtilityMeterPartialUniqueConstraint:
    """Test suite for Partial Unique Constraint (Task 1.5)"""

    def test_only_one_default_per_property_meter_type(self):
        """Test 1.5: Only one default allowed per property + meter_type"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        # Create first default meter
        meter1 = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='cold_water',
            is_default=True
        )
        assert meter1.is_default is True

        # Try to create second default meter of same type → should fail
        with pytest.raises(IntegrityError) as exc_info:
            UtilityMeter.objects.create(
                scope_type='property',
                property=property,
                meter_type='cold_water',
                is_default=True
            )
        assert 'unique_default_meter_property' in str(exc_info.value)

    def test_multiple_non_default_meters_allowed(self):
        """Test that multiple non-default meters of same type are OK"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        # Create multiple non-default meters
        meter1 = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='cold_water',
            is_default=False,
            serial_number='ABC-123'
        )
        meter2 = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='cold_water',
            is_default=False,
            serial_number='DEF-456'
        )

        assert meter1.pk != meter2.pk
        assert meter1.is_default is False
        assert meter2.is_default is False

    def test_default_meters_different_types_allowed(self):
        """Test that different meter types can each have a default"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        # Create default meters for different types
        cold_water = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='cold_water',
            is_default=True
        )
        hot_water = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='hot_water',
            is_default=True
        )
        electricity = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='electricity',
            is_default=True
        )

        assert cold_water.is_default is True
        assert hot_water.is_default is True
        assert electricity.is_default is True


@pytest.mark.django_db
class TestUtilityMeterSerialNormalization:
    """Test suite for Serial Number Normalization (Task 1.6)"""

    def test_serial_number_normalized_to_uppercase(self):
        """Test 1.6: Serial numbers are automatically uppercased"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='cold_water',
            serial_number='abc-123-xyz'  # lowercase input
        )

        meter.refresh_from_db()
        assert meter.serial_number == 'ABC-123-XYZ'  # Should be uppercase

    def test_serial_number_mixed_case_normalized(self):
        """Test that mixed case is normalized"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='hot_water',
            serial_number='AbC-123-XyZ'  # Mixed case
        )

        meter.refresh_from_db()
        assert meter.serial_number == 'ABC-123-XYZ'

    def test_serial_number_with_whitespace_trimmed(self):
        """Test that whitespace is trimmed"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='electricity',
            serial_number='  abc-123  '  # With whitespace
        )

        meter.refresh_from_db()
        assert meter.serial_number == 'ABC-123'  # Trimmed and uppercase

    def test_serial_number_empty_string_allowed(self):
        """Test that empty/blank serial numbers are allowed"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='gas',
            serial_number=''  # Empty
        )

        assert meter.serial_number == ''

    def test_serial_number_update_also_normalized(self):
        """Test that updates also normalize serial numbers"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=property,
            meter_type='cold_water',
            serial_number='OLD-123'
        )

        # Update with lowercase
        meter.serial_number = 'new-456'
        meter.save()

        meter.refresh_from_db()
        assert meter.serial_number == 'NEW-456'

    def test_serial_number_validation_alphanumeric_dash_slash(self):
        """Test that serial number validator works (alphanumeric + dash + slash)"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        # Valid serial numbers
        valid_serials = [
            'ABC123',
            'ABC-123',
            'ABC/123',
            'ABC-123/XYZ',
            '123456',
        ]

        for serial in valid_serials:
            meter = UtilityMeter(
                scope_type='property',
                property=property,
                meter_type='cold_water',
                serial_number=serial
            )
            # full_clean() should not raise
            meter.full_clean()
            # Delete to avoid constraint violations in loop
            if meter.pk:
                meter.delete()

    def test_serial_number_validation_rejects_invalid_chars(self):
        """Test that invalid characters in serial number are rejected"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        # Invalid serial numbers (contain special chars)
        invalid_serials = [
            'ABC@123',
            'ABC#123',
            'ABC 123',  # space
            'ABC_123',  # underscore
        ]

        for serial in invalid_serials:
            meter = UtilityMeter(
                scope_type='property',
                property=property,
                meter_type='cold_water',
                serial_number=serial
            )
            with pytest.raises(ValidationError) as exc_info:
                meter.full_clean()
            assert 'serial_number' in exc_info.value.error_dict
