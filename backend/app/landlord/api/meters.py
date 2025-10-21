"""
Utility Meter API Views for Portal - Phase 3
Nested under Property endpoints

Implements CRUD for UtilityMeter with:
- List meters per property
- Create, Update, Delete meters
- Default constraint handling (transactional)
- Reading dependency check before delete
"""
from django.db import transaction
from rest_framework import serializers as drf_serializers, status
from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    RetrieveAPIView,
    UpdateAPIView,
    DestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from landlord.models import UtilityMeter
from .properties import PortalReadThrottle, PortalWriteThrottle
from .properties_serializers import (
    UtilityMeterSerializer,
    UtilityMeterCreateSerializer,
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
    
    def get_queryset(self):
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
    
    @transaction.atomic
    def perform_create(self, serializer):
        """Save the new meter and handle default constraint"""
        meter = serializer.save()
        
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
        meter = serializer.save()
        
        # If is_default changed to True, clear other defaults
        if 'is_default' in serializer.validated_data and meter.is_default:
            UtilityMeter.objects.filter(
                scope_type=meter.scope_type,
                property_id=meter.property_id if meter.scope_type == 'property' else None,
                unit_id=meter.unit_id if meter.scope_type == 'unit' else None,
                meter_type=meter.meter_type,
                is_default=True
            ).exclude(id=meter.id).update(is_default=False)
        
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
        # Check if meter has readings
        if hasattr(instance, 'utilityreading_set') and instance.utilityreading_set.exists():
            # Cannot delete - has readings
            raise drf_serializers.ValidationError({
                'detail': 'Zähler kann nicht gelöscht werden, da bereits Zählerstände existieren.',
                'suggestion': 'Bitte deaktivieren Sie den Zähler stattdessen (is_active=false).',
                'readings_count': instance.utilityreading_set.count()
            })
        
        # No readings - safe to delete
        instance.delete()
