"""
Utility Meter API Views for Portal - Phase 3
Nested under Property endpoints

Implements CRUD for UtilityMeter with:
- List meters per property
- Create, Update, Delete meters
- Default constraint handling (transactional)
- Reading dependency check before delete
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from landlord.models import UtilityMeter
from rest_framework import serializers as drf_serializers

if TYPE_CHECKING:
    from django.db.models import QuerySet
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


class PropertyMeterListAPIView(ListAPIView):
    """
    GET /api/portal/properties/{property_id}/meters/

    List all utility meters for a property.
    """
    serializer_class = UtilityMeterSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]

    def get_queryset(self) -> QuerySet[UtilityMeter]:  # type: ignore[override]
        """Return meters for specific property"""
        property_id = self.kwargs.get('property_id')
        return UtilityMeter.objects.filter(
            scope_type='property',
            property_id=property_id
        ).order_by('meter_type', '-is_default', '-is_active')


class PropertyMeterCreateAPIView(CreateAPIView):
    """
    POST /api/portal/properties/{property_id}/meters/

    Create a new utility meter for a property.
    """
    serializer_class = UtilityMeterCreateSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]

    def get_serializer_context(self):
        """Add property_id from URL to serializer context"""
        context = super().get_serializer_context()
        context['property_id'] = self.kwargs.get('property_id')
        return context

    @transaction.atomic
    def perform_create(self, serializer):
        """Save the new meter and handle default constraint"""
        # Get property_id from URL kwargs
        property_id = self.kwargs.get('property_id')
        meter = serializer.save(property_id=property_id)

        # If this is set as default, clear other defaults of same type
        if meter.is_default:
            UtilityMeter.objects.filter(
                scope_type=meter.scope_type,
                property_id=meter.property_id if meter.scope_type == 'property' else None,
                unit_id=meter.unit_id if meter.scope_type == 'unit' else None,
                meter_type=meter.meter_type,
                is_default=True
            ).exclude(id=meter.id).update(is_default=False)


class PropertyMeterDetailAPIView(RetrieveAPIView):
    """
    GET /api/portal/properties/{property_id}/meters/{pk}/

    Retrieve details of a specific utility meter.
    """
    serializer_class = UtilityMeterSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]
    queryset = UtilityMeter.objects.all()
    lookup_field = 'pk'


class PropertyMeterUpdateAPIView(UpdateAPIView):
    """
    PUT/PATCH /api/portal/properties/{property_id}/meters/{pk}/

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
                scope_type=meter.scope_type,
                property_id=meter.property_id if meter.scope_type == 'property' else None,
                unit_id=meter.unit_id if meter.scope_type == 'unit' else None,
                meter_type=meter.meter_type,
                is_default=True
            ).exclude(id=meter.id).update(is_default=False)

        meter = serializer.save()

        # If is_active set to False and removed_at is None, set removed_at
        if 'is_active' in serializer.validated_data and not meter.is_active and not meter.removed_at:
            from django.utils import timezone
            meter.removed_at = timezone.now().date()
            meter.save(update_fields=['removed_at'])


class PropertyMeterDeleteAPIView(DestroyAPIView):
    """
    DELETE /api/portal/properties/{property_id}/meters/{pk}/

    Delete a utility meter.

    Note: Cannot delete if readings exist. Deactivate instead.
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = UtilityMeter.objects.all()
    lookup_field = 'pk'

    def perform_destroy(self, instance):
        """Delete meter, but check for readings first"""
        from landlord.models import UtilityReading

        # Check if meter has readings (only for unit meters)
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
                readings_count = UtilityReading.objects.filter(
                    unit=instance.unit,
                    meter_type=reading_type
                ).count()

                if readings_count > 0:
                    # Cannot delete - has readings
                    raise drf_serializers.ValidationError({
                        'detail': 'Zähler kann nicht gelöscht werden, da bereits Zählerstände existieren.',
                        'suggestion': 'Bitte deaktivieren Sie den Zähler stattdessen (is_active=false).',
                        'readings_count': readings_count
                    })

        # No readings - safe to delete (or property meter without reading support)
        instance.delete()
