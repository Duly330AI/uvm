"""
Service Layer for Utility Meter Default Prefill (M17)

Implements the business logic for:
- getDefaultMeter: Find the appropriate meter for a given scope+type (with caching)
- getLastReading: Get the last reading for a meter (with initial_reading_value fallback)

Caching Strategy (Spec Kap. 5):
- Cache Key: utility_meter:{scope_type}:{scope_id}:{meter_type}
- TTL: 5 minutes
- Invalidation: via signals in landlord.signals (post_save/post_delete)
"""

from typing import Any, Dict

from django.core.cache import cache
from landlord.models import UtilityMeter, UtilityReading

# Cache TTL: 5 minutes (spec Kap. 5)
CACHE_TTL = 300  # seconds


def _get_cache_key(scope_type: str, scope_id: int, meter_type: str) -> str:
    """Generate cache key for meter lookup"""
    return f"utility_meter:{scope_type}:{scope_id}:{meter_type}"


class UtilityMeterService:
    """
    Service for Utility Meter operations (M17: Default Meter Prefill)

    Implements the lookup priority from spec Kap. 3.3:
    A) Default vorhanden → return default
    B) Kein Default, genau 1 aktiver → return aktiver
    C) Mehrere aktive, kein Default → return list (has_multiple=True)
    D) Kein Zähler → return None
    """

    @staticmethod
    def get_default_meter(
        scope_type: str,
        scope_id: int,
        meter_type: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get the default meter for a given scope and meter type.

        Args:
            scope_type: 'property' or 'unit'
            scope_id: ID of the Property or Unit
            meter_type: One of: 'cold_water', 'hot_water', 'electricity', 'gas'
            use_cache: Whether to use cache (default: True)

        Returns:
            {
                'meter_id': int or None,
                'serial_number': str or None,
                'has_multiple': bool,
                'initial_reading_value': Decimal or None,
                'meters': List[Dict] (only if has_multiple=True)
            }

        Lookup Priority (spec Kap. 3.3):
        - A) Default vorhanden → return default meter
        - B) Kein Default, genau 1 aktiver → return aktiver meter
        - C) Mehrere aktive, kein Default → return list of meters
        - D) Kein Zähler gefunden → return None values

        Caching (Spec Kap. 5):
        - Results are cached for 5 minutes
        - Cache is invalidated on UtilityMeter save/delete
        """
        # Check cache first
        if use_cache:
            cache_key = _get_cache_key(scope_type, scope_id, meter_type)
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # Build query filter based on scope_type
        filter_kwargs = {
            'scope_type': scope_type,
            'meter_type': meter_type,
            'is_active': True,
        }

        if scope_type == 'property':
            filter_kwargs['property_id'] = scope_id
        else:  # unit
            filter_kwargs['unit_id'] = scope_id

        # Get all active meters
        active_meters = UtilityMeter.objects.filter(**filter_kwargs).order_by(
            '-is_default',  # Default first
            '-installed_at',  # Then newest installation
            'serial_number'
        )

        meter_count = active_meters.count()

        # Case D: No meter found
        if meter_count == 0:
            result = {
                'meter_id': None,
                'serial_number': None,
                'has_multiple': False,
                'initial_reading_value': None,
                'meters': []
            }
            if use_cache:
                cache.set(_get_cache_key(scope_type, scope_id, meter_type), result, CACHE_TTL)
            return result

        # Case A: Default exists
        default_meter = active_meters.filter(is_default=True).first()
        if default_meter:
            result = {
                'meter_id': default_meter.id,
                'serial_number': default_meter.serial_number or '',
                'has_multiple': False,
                'initial_reading_value': float(default_meter.initial_reading_value) if default_meter.initial_reading_value else None,
                'meters': []
            }
            if use_cache:
                cache.set(_get_cache_key(scope_type, scope_id, meter_type), result, CACHE_TTL)
            return result

        # Case B: No default, exactly 1 active
        if meter_count == 1:
            meter = active_meters.first()
            result = {
                'meter_id': meter.id,
                'serial_number': meter.serial_number or '',
                'has_multiple': False,
                'initial_reading_value': float(meter.initial_reading_value) if meter.initial_reading_value else None,
                'meters': []
            }
            if use_cache:
                cache.set(_get_cache_key(scope_type, scope_id, meter_type), result, CACHE_TTL)
            return result

        # Case C: Multiple active meters, no default
        meters_list = []
        for meter in active_meters:
            meters_list.append({
                'meter_id': meter.id,
                'serial_number': meter.serial_number or '',
                'meter_type_label': meter.get_meter_type_display(),
                'installed_at': meter.installed_at.isoformat() if meter.installed_at else None,
                'initial_reading_value': float(meter.initial_reading_value) if meter.initial_reading_value else None,
            })

        result = {
            'meter_id': None,  # User must choose
            'serial_number': None,
            'has_multiple': True,
            'initial_reading_value': None,
            'meters': meters_list
        }
        if use_cache:
            cache.set(_get_cache_key(scope_type, scope_id, meter_type), result, CACHE_TTL)
        return result

    @staticmethod
    def get_last_reading(meter_id: int) -> Dict[str, Any]:
        """
        Get the last reading for a given meter.

        Args:
            meter_id: ID of the UtilityMeter

        Returns:
            {
                'previous_value': Decimal or None,
                'reading_date': str (ISO) or None,
                'is_initial': bool (True if using initial_reading_value)
            }

        Logic (spec Kap. 3.3):
        - If readings exist: return last reading's current_value
        - If no readings but initial_reading_value set: return initial_reading_value (einmalig)
        - Otherwise: return None
        """
        try:
            meter = UtilityMeter.objects.get(id=meter_id)
        except UtilityMeter.DoesNotExist:
            return {
                'previous_value': None,
                'reading_date': None,
                'is_initial': False
            }

        # Get scope object (Property or Unit)
        scope_obj = meter.get_scope_object()

        # For Unit meters: query UtilityReading by unit
        if meter.scope_type == 'unit':
            last_reading = UtilityReading.objects.filter(
                unit=scope_obj,
                meter_type=_convert_meter_type_to_reading_type(meter.meter_type)
            ).order_by('-reading_date', '-created_at').first()

            if last_reading:
                return {
                    'previous_value': float(last_reading.current_value),
                    'reading_date': last_reading.reading_date.isoformat(),
                    'is_initial': False
                }

        # For Property meters: no UtilityReading support yet (building-level)
        # Fall through to initial_reading_value

        # No readings found - check for initial_reading_value
        if meter.initial_reading_value is not None:
            return {
                'previous_value': float(meter.initial_reading_value),
                'reading_date': meter.installed_at.isoformat() if meter.installed_at else None,
                'is_initial': True  # UI should show "Erstwert aus Stammdaten"
            }

        # No readings, no initial value
        return {
            'previous_value': None,
            'reading_date': None,
            'is_initial': False
        }


def _convert_meter_type_to_reading_type(meter_type: str) -> str:
    """
    Convert UtilityMeter.meter_type to UtilityReading.meter_type

    UtilityMeter uses: cold_water, hot_water, electricity, gas
    UtilityReading uses: water_cold, water_hot, electricity, gas, heating
    """
    mapping = {
        'cold_water': 'water_cold',
        'hot_water': 'water_hot',
        'electricity': 'electricity',
        'gas': 'gas',
    }
    return mapping.get(meter_type, meter_type)


# Convenience functions for direct use
def get_default_meter(scope_type: str, scope_id: int, meter_type: str) -> Dict[str, Any]:
    """Convenience wrapper for UtilityMeterService.get_default_meter"""
    return UtilityMeterService.get_default_meter(scope_type, scope_id, meter_type)


def get_last_reading(meter_id: int) -> Dict[str, Any]:
    """Convenience wrapper for UtilityMeterService.get_last_reading"""
    return UtilityMeterService.get_last_reading(meter_id)

