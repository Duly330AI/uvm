"""
Unit API Serializers for Portal
Phase 4: API Endpoints - Units
"""
from landlord.models import Unit
from rest_framework import serializers


class UnitListSerializer(serializers.ModelSerializer):
    """Serializer for Unit list view (GET /api/portal/units/)"""

    property_name = serializers.CharField(source='property.name', read_only=True)
    property_id = serializers.IntegerField(source='property.id', read_only=True)
    meters_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Unit
        fields = [
            'id',
            'property_id',
            'property_name',
            'unit_label',
            'floor',
            'rooms',
            'area_sqm',
            'is_active',
            'is_archived',
            'meters_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'meters_count']


class UnitDetailSerializer(serializers.ModelSerializer):
    """Serializer for Unit detail view (GET /api/portal/units/{id}/)"""

    property_name = serializers.CharField(source='property.name', read_only=True)
    property_id = serializers.IntegerField(source='property.id', read_only=True)
    meters = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = [
            'id',
            'property_id',
            'property_name',
            'unit_label',
            'floor',
            'rooms',
            'area_sqm',
            'notes',
            'is_active',
            'is_archived',
            'archived_at',
            'archived_by',
            'meters',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'archived_at', 'archived_by']

    def get_meters(self, obj):
        """Get all meters for this unit"""
        from landlord.api.properties_serializers import UtilityMeterSerializer
        meters = obj.utility_meters.all()
        return UtilityMeterSerializer(meters, many=True).data


class UnitCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Unit"""

    class Meta:
        model = Unit
        fields = [
            'property',
            'unit_label',
            'floor',
            'rooms',
            'area_sqm',
            'notes',
            'is_active',
        ]

    def validate_property(self, value):
        """Validate that property exists and is not archived"""
        if value.is_archived:
            raise serializers.ValidationError(
                'Wohnungen können nicht zu archivierten Gebäuden hinzugefügt werden.'
            )
        return value


class UnitUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an existing Unit"""

    class Meta:
        model = Unit
        fields = [
            'property',
            'unit_label',
            'floor',
            'rooms',
            'area_sqm',
            'notes',
            'is_active',
        ]

    def validate_property(self, value):
        """Validate that property exists and is not archived"""
        if value.is_archived:
            raise serializers.ValidationError(
                'Wohnungen können nicht zu archivierten Gebäuden zugeordnet werden.'
            )
        return value
