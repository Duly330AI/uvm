"""
Property API Serializers for Portal
Phase 2: API Endpoints - Properties
"""
from rest_framework import serializers
from landlord.models import Property, UtilityMeter


class PropertyListSerializer(serializers.ModelSerializer):
    """Serializer for Property list view (GET /api/portal/properties/)"""
    
    meters_count = serializers.SerializerMethodField()
    country_display = serializers.CharField(source='get_country_display', read_only=True)
    
    class Meta:
        model = Property
        fields = [
            'id',
            'name',
            'street',
            'city',
            'postal_code',
            'country',
            'country_display',
            'is_archived',
            'meters_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_meters_count(self, obj):
        """Return count of utility meters for this property"""
        return obj.utility_meters.count()


class UtilityMeterSerializer(serializers.ModelSerializer):
    """Serializer for UtilityMeter (nested in PropertyDetailSerializer)"""
    
    meter_type_display = serializers.CharField(source='get_meter_type_display', read_only=True)
    scope_type_display = serializers.CharField(source='get_scope_type_display', read_only=True)
    
    class Meta:
        model = UtilityMeter
        fields = [
            'id',
            'scope_type',
            'scope_type_display',
            'meter_type',
            'meter_type_display',
            'serial_number',
            'is_default',
            'is_active',
            'initial_reading_value',
            'installed_at',
            'removed_at',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Serializer for Property detail view (GET /api/portal/properties/{id}/)"""
    
    meters = UtilityMeterSerializer(source='utility_meters', many=True, read_only=True)
    country_display = serializers.CharField(source='get_country_display', read_only=True)
    archived_by_email = serializers.EmailField(source='archived_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Property
        fields = [
            'id',
            'name',
            'street',
            'postal_code',
            'city',
            'country',
            'country_display',
            'geo_lat',
            'geo_lng',
            'notes',
            'is_archived',
            'archived_at',
            'archived_by',
            'archived_by_email',
            'meters',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_archived', 'archived_at', 'archived_by', 'created_at', 'updated_at']


class PropertyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Property (POST /api/portal/properties/)"""
    
    class Meta:
        model = Property
        fields = [
            'name',
            'street',
            'postal_code',
            'city',
            'country',
            'geo_lat',
            'geo_lng',
            'notes',
        ]
    
    def validate(self, data):
        """Custom validation for Property creation"""
        # Country must be in allowed choices
        if 'country' in data:
            valid_countries = [choice[0] for choice in Property._meta.get_field('country').choices]
            if data['country'] not in valid_countries:
                raise serializers.ValidationError({
                    'country': f"Must be one of: {', '.join(valid_countries)}"
                })
        
        return data


class PropertyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a Property (PUT/PATCH /api/portal/properties/{id}/)"""
    
    class Meta:
        model = Property
        fields = [
            'name',
            'street',
            'postal_code',
            'city',
            'country',
            'geo_lat',
            'geo_lng',
            'notes',
        ]
    
    def validate(self, data):
        """Custom validation for Property updates"""
        # Country must be in allowed choices
        if 'country' in data:
            valid_countries = [choice[0] for choice in Property._meta.get_field('country').choices]
            if data['country'] not in valid_countries:
                raise serializers.ValidationError({
                    'country': f"Must be one of: {', '.join(valid_countries)}"
                })
        
        return data
