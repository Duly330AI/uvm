"""
Unit-Meter API Views for Portal - Phase 5
Nested under Unit endpoints

Implements CRUD for UtilityMeter (unit-scoped) with:
- List meters per unit
- Create, Update, Delete meters
- Default constraint handling (transactional)
- Reading dependency check before delete
"""
from django.db import transaction
from landlord.models import UtilityMeter
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from .properties import PortalReadThrottle, PortalWriteThrottle
from .properties_serializers import (
    UtilityMeterCreateSerializer,
    UtilityMeterSerializer,
    UtilityMeterUpdateSerializer,
)


class UnitMeterListAPIView(ListAPIView):
    """
    GET /api/portal/units/{unit_id}/meters/

    List all utility meters for a unit.
    """
    serializer_class = UtilityMeterSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]

    def get_queryset(self):
        """Return meters for specific unit"""
        unit_id = self.kwargs.get('unit_id')
        return UtilityMeter.objects.filter(
            scope_type='unit',
            unit_id=unit_id
        ).order_by('meter_type', '-is_default', '-is_active')


class UnitMeterCreateAPIView(CreateAPIView):
    """
    POST /api/portal/units/{unit_id}/meters/

    Create a new utility meter for a unit.
    """
    serializer_class = UtilityMeterCreateSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]

    def get_serializer_context(self):
        """Add unit_id from URL to serializer context"""
        context = super().get_serializer_context()
        context['unit_id'] = self.kwargs.get('unit_id')
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        """Save the new meter and handle default constraint"""
        # Get unit_id from URL kwargs
        unit_id = self.kwargs.get('unit_id')
        meter = serializer.save(unit_id=unit_id, scope_type='unit')

        # If this is set as default, clear other defaults of same type
        if meter.is_default:
            UtilityMeter.objects.filter(
                scope_type='unit',
                unit_id=meter.unit_id,
                meter_type=meter.meter_type,
                is_default=True
            ).exclude(id=meter.id).update(is_default=False)


class UnitMeterDetailAPIView(RetrieveAPIView):
    """
    GET /api/portal/units/{unit_id}/meters/{pk}/

    Retrieve details of a specific utility meter.
    """
    serializer_class = UtilityMeterSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]
    queryset = UtilityMeter.objects.all()
    lookup_field = 'pk'


class UnitMeterUpdateAPIView(UpdateAPIView):
    """
    PUT/PATCH /api/portal/units/{unit_id}/meters/{pk}/

    Update an existing utility meter.
    """
    serializer_class = UtilityMeterUpdateSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = UtilityMeter.objects.all()
    lookup_field = 'pk'

    @transaction.atomic
    def perform_update(self, serializer):
        """Save meter and handle default constraint + auto-set removed_at"""
        # If is_default is being set to True, clear other defaults BEFORE saving
        if 'is_default' in serializer.validated_data and serializer.validated_data['is_default']:
            meter = self.get_object()
            UtilityMeter.objects.filter(
                scope_type='unit',
                unit_id=meter.unit_id,
                meter_type=meter.meter_type,
                is_default=True
            ).exclude(id=meter.id).update(is_default=False)

        meter = serializer.save()

        # If is_active set to False and removed_at is None, set removed_at
        if 'is_active' in serializer.validated_data and not meter.is_active and not meter.removed_at:
            from django.utils import timezone
            meter.removed_at = timezone.now().date()
            meter.save(update_fields=['removed_at'])


class UnitMeterDeleteAPIView(DestroyAPIView):
    """
    DELETE /api/portal/units/{unit_id}/meters/{pk}/

    Delete a utility meter.

    Note: Cannot delete if readings exist. Returns 409 with suggestion to deactivate.
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = UtilityMeter.objects.all()
    lookup_field = 'pk'

    def perform_destroy(self, instance):
        """Delete meter, but check for readings first"""
        from landlord.models import UtilityReading

        # Check if meter has readings
        if instance.scope_type == 'unit' and instance.unit:
            # Map meter type to reading type
            meter_to_reading_type = {
                'cold_water': 'water_cold',
                'hot_water': 'water_hot',
                'electricity': 'electricity',
                'gas': 'gas',
            }

            reading_type = meter_to_reading_type.get(instance.meter_type)
            if reading_type:
                readings_exist = UtilityReading.objects.filter(
                    unit=instance.unit,
                    meter_type=reading_type
                ).exists()

                if readings_exist:
                    # Cannot delete - has readings
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({
                        'error': 'Zähler kann nicht gelöscht werden.',
                        'reason': 'Es existieren Zählerstände für diesen Zähler.',
                        'suggestion': 'Bitte deaktivieren Sie den Zähler stattdessen (is_active=false + removed_at).'
                    })

        # No readings or property meter - safe to delete
        instance.delete()
