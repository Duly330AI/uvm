"""
Property Model Extended Tests
Tests for Phase 1, Tasks 1.1, 1.2, 1.3

Tests cover:
- Task 1.1: Archive fields (is_archived, archived_at, archived_by)
- Task 1.1: archive() method behavior
- Task 1.1: Idempotency
- Task 1.2: Geo-coordinate validation (lat/lng ranges)
- Task 1.3: Country choices and validation
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from landlord.models import Property

User = get_user_model()
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from landlord.models import Property

User = get_user_model()


@pytest.mark.django_db
class TestPropertyArchiveFields:
    """Test suite for Property archive functionality (Task 1.1)"""

    def test_property_create_with_all_fields(self):
        """Test 1.1.6: Property can be created with all fields"""
        property = Property.objects.create(
            name="Test Gebäude",
            street="Teststraße 123",
            postal_code="12345",
            city="Berlin",
            country="DE",  # Updated to use country code
            notes="Test notes"
        )
        assert property.id is not None
        assert property.is_archived is False
        assert property.archived_at is None
        assert property.archived_by is None

    def test_property_archive_sets_fields(self):
        """Test 1.1.6: archive() method sets all three fields"""
        # Create property
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        # Create user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        # Archive property
        before_archive = timezone.now()
        property.archive(user)
        after_archive = timezone.now()

        # Refresh from DB
        property.refresh_from_db()

        # Assert all fields are set
        assert property.is_archived is True
        assert property.archived_at is not None
        assert before_archive <= property.archived_at <= after_archive
        assert property.archived_by == user

    def test_property_archive_by_user(self):
        """Test 1.1.7: archive() correctly stores the user who archived"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass123"
        )
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123"
        )

        # User1 archives
        property.archive(user1)
        property.refresh_from_db()

        assert property.archived_by == user1
        assert property.archived_by != user2

    def test_property_archive_idempotent(self):
        """Test 1.1.7: Archiving twice doesn't cause errors (idempotent)"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass123"
        )

        # Archive first time
        property.archive(user)

        # Archive second time (should just update fields)
        property.archive(user)
        property.refresh_from_db()

        # Still archived, timestamp may be updated
        assert property.is_archived is True
        assert property.archived_by == user
        # archived_at may be newer due to re-archiving

    def test_property_default_not_archived(self):
        """Test that newly created properties are not archived by default"""
        property = Property.objects.create(
            name="New Property",
            street="New St",
            postal_code="12345",
            city="Berlin"
        )

        assert property.is_archived is False
        assert property.archived_at is None
        assert property.archived_by is None

    def test_property_archived_by_cascades_on_user_delete(self):
        """Test that archived_by is set to NULL when user is deleted (SET_NULL)"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        user = User.objects.create_user(
            username="tempuser",
            email="temp@example.com",
            password="pass123"
        )

        property.archive(user)
        property.refresh_from_db()
        assert property.archived_by == user

        # Delete user
        user_id = user.id
        user.delete()

        # Property should still exist, but archived_by should be NULL
        property.refresh_from_db()
        assert property.is_archived is True  # Still archived
        assert property.archived_at is not None  # Timestamp preserved
        assert property.archived_by is None  # User reference cleared

    def test_user_archived_properties_related_name(self):
        """Test that User has 'archived_properties' related name"""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass123"
        )

        # Create 3 properties, archive 2 of them
        p1 = Property.objects.create(name="P1", street="St1", postal_code="12345", city="Berlin")
        p2 = Property.objects.create(name="P2", street="St2", postal_code="12345", city="Berlin")
        p3 = Property.objects.create(name="P3", street="St3", postal_code="12345", city="Berlin")

        p1.archive(user)
        p2.archive(user)

        # User should have 2 archived properties
        assert user.archived_properties.count() == 2
        assert p1 in user.archived_properties.all()
        assert p2 in user.archived_properties.all()
        assert p3 not in user.archived_properties.all()


@pytest.mark.django_db
class TestPropertyGeoCoordinates:
    """Test suite for Property geo-coordinate validation (Task 1.2)"""

    def test_property_geo_lat_valid_range(self):
        """Test 1.2.6: geo_lat accepts valid range -90.0 to +90.0"""
        # Valid minimum
        p1 = Property.objects.create(
            name="North Pole",
            street="Ice St",
            postal_code="12345",
            city="Arctic",
            geo_lat=Decimal('-90.0'),
            geo_lng=Decimal('0.0')
        )
        assert p1.geo_lat == Decimal('-90.0')

        # Valid maximum
        p2 = Property.objects.create(
            name="South Pole",
            street="Ice St",
            postal_code="12345",
            city="Antarctic",
            geo_lat=Decimal('90.0'),
            geo_lng=Decimal('0.0')
        )
        assert p2.geo_lat == Decimal('90.0')

        # Valid middle
        p3 = Property.objects.create(
            name="Berlin",
            street="Main St",
            postal_code="12345",
            city="Berlin",
            geo_lat=Decimal('52.520008'),
            geo_lng=Decimal('13.404954')
        )
        assert p3.geo_lat == Decimal('52.520008')

    def test_property_geo_lat_invalid_too_low(self):
        """Test 1.2.7: geo_lat < -90.0 raises IntegrityError"""
        with pytest.raises(IntegrityError) as exc_info:
            Property.objects.create(
                name="Invalid Low",
                street="St",
                postal_code="12345",
                city="City",
                geo_lat=Decimal('-90.1')
            )
        assert 'property_geo_lat_valid_range' in str(exc_info.value)

    def test_property_geo_lat_invalid_too_high(self):
        """Test 1.2.7: geo_lat > 90.0 raises IntegrityError"""
        with pytest.raises(IntegrityError) as exc_info:
            Property.objects.create(
                name="Invalid High",
                street="St",
                postal_code="12345",
                city="City",
                geo_lat=Decimal('90.1')
            )
        assert 'property_geo_lat_valid_range' in str(exc_info.value)

    def test_property_geo_lng_valid_range(self):
        """Test 1.2.8: geo_lng accepts valid range -180.0 to +180.0"""
        # Valid minimum
        p1 = Property.objects.create(
            name="West Edge",
            street="St",
            postal_code="12345",
            city="City",
            geo_lat=Decimal('0.0'),
            geo_lng=Decimal('-180.0')
        )
        assert p1.geo_lng == Decimal('-180.0')

        # Valid maximum
        p2 = Property.objects.create(
            name="East Edge",
            street="St",
            postal_code="12345",
            city="City",
            geo_lat=Decimal('0.0'),
            geo_lng=Decimal('180.0')
        )
        assert p2.geo_lng == Decimal('180.0')

    def test_property_geo_lng_invalid_too_low(self):
        """Test 1.2.9: geo_lng < -180.0 raises IntegrityError"""
        with pytest.raises(IntegrityError) as exc_info:
            Property.objects.create(
                name="Invalid Low",
                street="St",
                postal_code="12345",
                city="City",
                geo_lng=Decimal('-180.1')
            )
        assert 'property_geo_lng_valid_range' in str(exc_info.value)

    def test_property_geo_lng_invalid_too_high(self):
        """Test 1.2.9: geo_lng > 180.0 raises IntegrityError"""
        with pytest.raises(IntegrityError) as exc_info:
            Property.objects.create(
                name="Invalid High",
                street="St",
                postal_code="12345",
                city="City",
                geo_lng=Decimal('180.1')
            )
        assert 'property_geo_lng_valid_range' in str(exc_info.value)

    def test_property_geo_coordinates_null_allowed(self):
        """Test that geo_lat/geo_lng can be NULL (optional fields)"""
        p = Property.objects.create(
            name="No Geo",
            street="St",
            postal_code="12345",
            city="City"
        )
        assert p.geo_lat is None
        assert p.geo_lng is None

    def test_property_full_call_clean_validators(self):
        """Test that model validators are called via full_clean()"""
        p = Property(
            name="Test",
            street="St",
            postal_code="12345",
            city="City",
            geo_lat=Decimal('91.0')  # Invalid!
        )

        # full_clean() should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            p.full_clean()

        # Check that geo_lat validation failed
        assert 'geo_lat' in exc_info.value.error_dict


@pytest.mark.django_db
class TestPropertyCountryChoices:
    """Test suite for Property country choices and validation (Task 1.3)"""

    def test_property_country_default_is_de(self):
        """Test 1.3.6: Property defaults to 'DE' if no country specified"""
        p = Property.objects.create(
            name="Test",
            street="St",
            postal_code="12345",
            city="Berlin"
        )
        assert p.country == 'DE'

    def test_property_country_valid_choices(self):
        """Test 1.3.7: All valid country codes work (DE, AT, CH)"""
        p_de = Property.objects.create(name="Germany", street="St", postal_code="12345", city="Berlin", country='DE')
        p_at = Property.objects.create(name="Austria", street="St", postal_code="12345", city="Vienna", country='AT')
        p_ch = Property.objects.create(name="Switzerland", street="St", postal_code="12345", city="Zurich", country='CH')
        
        assert p_de.country == 'DE'
        assert p_at.country == 'AT'
        assert p_ch.country == 'CH'

    def test_property_country_get_display(self):
        """Test 1.3.8: get_country_display() returns localized name"""
        p_de = Property.objects.create(name="Test", street="St", postal_code="12345", city="Berlin", country='DE')
        p_at = Property.objects.create(name="Test", street="St", postal_code="12345", city="Vienna", country='AT')
        p_ch = Property.objects.create(name="Test", street="St", postal_code="12345", city="Zurich", country='CH')
        
        assert p_de.get_country_display() == 'Deutschland'
        assert p_at.get_country_display() == 'Österreich'
        assert p_ch.get_country_display() == 'Schweiz'

    def test_property_country_invalid_code_validation(self):
        """Test 1.3.9: Invalid country code raises ValidationError via full_clean()"""
        p = Property(
            name="Test",
            street="St",
            postal_code="12345",
            city="City",
            country='US'  # Invalid!
        )
        
        with pytest.raises(ValidationError) as exc_info:
            p.full_clean()
        
        # Should have validation error on country field
        assert 'country' in exc_info.value.error_dict

    def test_property_country_max_length_2(self):
        """Test that country field is max 2 characters"""
        # This should work (2 chars)
        p = Property.objects.create(
            name="Test",
            street="St",
            postal_code="12345",
            city="City",
            country='DE'
        )
        assert p.country == 'DE'
