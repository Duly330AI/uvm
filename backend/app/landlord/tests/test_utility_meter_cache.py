"""
Tests for UtilityMeter Caching (M17 Phase 4)
"""
import pytest
from django.core.cache import cache
from landlord.models import Property, Unit, UtilityMeter
from landlord.services.utility_meter_service import get_default_meter


@pytest.mark.django_db
class TestUtilityMeterCaching:
    """Test caching functionality for UtilityMeterService"""

    def teardown_method(self, method):
        """Clear cache after each test"""
        cache.clear()

    def test_cache_hit_on_second_call(self):
        """Test that second call returns cached result"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='CACHE-001',
            is_default=True,
            is_active=True
        )

        # First call - cache miss
        result1 = get_default_meter('property', prop.id, 'electricity')
        assert result1['serial_number'] == 'CACHE-001'

        # Second call - should be from cache
        result2 = get_default_meter('property', prop.id, 'electricity')
        assert result2['serial_number'] == 'CACHE-001'
        assert result1 == result2

    def test_cache_invalidation_on_save(self):
        """Test that cache is invalidated when meter is saved"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='OLD-SN',
            is_default=True,
            is_active=True
        )

        # First call - cache it
        result1 = get_default_meter('property', prop.id, 'electricity')
        assert result1['serial_number'] == 'OLD-SN'

        # Update meter (should invalidate cache via signal)
        meter.serial_number = 'NEW-SN'
        meter.save()

        # Next call should fetch fresh data
        result2 = get_default_meter('property', prop.id, 'electricity')
        assert result2['serial_number'] == 'NEW-SN'

    def test_cache_invalidation_on_default_change(self):
        """Test cache invalidation when default changes"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        # Create first default meter
        meter1 = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='gas',
            serial_number='METER-1',
            is_default=True,
            is_active=True
        )

        # Cache it
        result1 = get_default_meter('property', prop.id, 'gas')
        assert result1['meter_id'] == meter1.id

        # Create second meter (not default yet)
        meter2 = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='gas',
            serial_number='METER-2',
            is_default=False,
            is_active=True
        )

        # Now change default: meter1 → not default, meter2 → default
        meter1.is_default = False
        meter1.save()  # Should invalidate cache

        meter2.is_default = True
        meter2.save()  # Should also invalidate cache

        # Next call should return meter2
        result2 = get_default_meter('property', prop.id, 'gas')
        assert result2['meter_id'] == meter2.id
        assert result2['serial_number'] == 'METER-2'

    def test_cache_invalidation_on_delete(self):
        """Test that cache is invalidated when meter is deleted"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='DELETE-ME',
            is_default=True,
            is_active=True
        )

        # Cache it
        result1 = get_default_meter('property', prop.id, 'electricity')
        assert result1['meter_id'] == meter.id

        # Delete meter (should invalidate cache via signal)
        meter.delete()

        # Next call should return "no meter found"
        result2 = get_default_meter('property', prop.id, 'electricity')
        assert result2['meter_id'] is None
        assert result2['has_multiple'] is False

    def test_cache_separate_keys_per_scope_and_type(self):
        """Test that different scopes/types have separate cache keys"""
        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")
        unit = Unit.objects.create(property=prop, unit_label="1A")

        # Property electricity meter
        UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='PROP-ELEC',
            is_default=True,
            is_active=True
        )

        # Property gas meter
        UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='gas',
            serial_number='PROP-GAS',
            is_default=True,
            is_active=True
        )

        # Unit electricity meter
        UtilityMeter.objects.create(
            scope_type='unit',
            unit=unit,
            meter_type='electricity',
            serial_number='UNIT-ELEC',
            is_default=True,
            is_active=True
        )

        # All three should be cached separately
        result_prop_elec = get_default_meter('property', prop.id, 'electricity')
        result_prop_gas = get_default_meter('property', prop.id, 'gas')
        result_unit_elec = get_default_meter('unit', unit.id, 'electricity')

        assert result_prop_elec['serial_number'] == 'PROP-ELEC'
        assert result_prop_gas['serial_number'] == 'PROP-GAS'
        assert result_unit_elec['serial_number'] == 'UNIT-ELEC'

    def test_cache_bypass_with_use_cache_false(self):
        """Test that cache can be bypassed with use_cache=False"""
        from landlord.services.utility_meter_service import UtilityMeterService

        prop = Property.objects.create(street="Test", postal_code="12345", city="Test")

        meter = UtilityMeter.objects.create(
            scope_type='property',
            property=prop,
            meter_type='electricity',
            serial_number='BYPASS-TEST',
            is_default=True,
            is_active=True
        )

        # First call with cache
        result1 = UtilityMeterService.get_default_meter('property', prop.id, 'electricity', use_cache=True)
        assert result1['serial_number'] == 'BYPASS-TEST'

        # Update meter
        meter.serial_number = 'UPDATED'
        meter.save()

        # Call with use_cache=True should still return cached (before signal processes)
        # But with use_cache=False should return fresh
        result_nocache = UtilityMeterService.get_default_meter('property', prop.id, 'electricity', use_cache=False)
        assert result_nocache['serial_number'] == 'UPDATED'
