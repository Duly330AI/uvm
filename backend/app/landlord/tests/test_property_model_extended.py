"""
Property Model Extended Tests
Tests for Phase 1, Task 1.1: Archive Fields

Tests cover:
- Archive field creation (is_archived, archived_at, archived_by)
- archive() method behavior
- Idempotency
"""
import pytest
from django.contrib.auth import get_user_model
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
            country="Deutschland",
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
