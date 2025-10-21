"""
Unit Model Tests - Phase 6
Tests for Unit model functionality

Tests cover:
- Archive fields (is_archived, archived_at, archived_by)
- archive() method behavior
- Validators (area_sqm >= 0)
- Model relationships (Property FK)
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from landlord.models import Property, Unit

User = get_user_model()


@pytest.mark.django_db
class TestUnitModel:
    """Test suite for Unit model"""

    def test_unit_create_with_all_fields(self):
        """Unit can be created with all fields"""
        property = Property.objects.create(
            name="Test Gebäude",
            street="Teststraße 123",
            postal_code="12345",
            city="Berlin",
            country="DE"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1",
            floor="EG",
            rooms=3,
            area_sqm=Decimal("85.50"),
            notes="Test Unit",
            is_active=True
        )

        assert unit.id is not None
        assert unit.property == property
        assert unit.unit_label == "A1"
        assert unit.floor == "EG"
        assert unit.rooms == 3
        assert unit.area_sqm == Decimal("85.50")
        assert unit.is_active is True
        assert unit.is_archived is False
        assert unit.archived_at is None
        assert unit.archived_by is None

    def test_unit_archive_sets_fields(self):
        """archive() method sets all three archive fields"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1"
        )

        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        before_archive = timezone.now()
        unit.archive(user)
        after_archive = timezone.now()

        unit.refresh_from_db()

        assert unit.is_archived is True
        assert unit.archived_at is not None
        assert before_archive <= unit.archived_at <= after_archive
        assert unit.archived_by == user

    def test_unit_archive_idempotent(self):
        """archive() is idempotent - can be called multiple times"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1"
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

        # First archive
        unit.archive(user1)
        unit.refresh_from_db()
        first_archived_at = unit.archived_at
        assert unit.archived_by == user1

        # Second archive (should update fields)
        unit.archive(user2)
        unit.refresh_from_db()

        assert unit.is_archived is True
        assert unit.archived_at >= first_archived_at
        assert unit.archived_by == user2

    def test_unit_area_sqm_validation_positive(self):
        """area_sqm accepts positive values"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1",
            area_sqm=Decimal("100.00")
        )

        unit.full_clean()  # Should not raise
        assert unit.area_sqm == Decimal("100.00")

    def test_unit_area_sqm_validation_zero(self):
        """area_sqm accepts zero"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1",
            area_sqm=Decimal("0.00")
        )

        unit.full_clean()  # Should not raise
        assert unit.area_sqm == Decimal("0.00")

    def test_unit_area_sqm_validation_negative(self):
        """area_sqm rejects negative values"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit(
            property=property,
            unit_label="A1",
            area_sqm=Decimal("-10.00")
        )

        with pytest.raises(ValidationError) as exc_info:
            unit.full_clean()

        assert 'area_sqm' in exc_info.value.error_dict

    def test_unit_str_representation(self):
        """__str__ returns unit_label @ property.name"""
        property = Property.objects.create(
            name="Gebäude A",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="Whg 3"
        )

        assert str(unit) == "Whg 3 @ Gebäude A"

    def test_unit_property_relationship(self):
        """Unit has correct ForeignKey to Property"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1"
        )

        assert unit.property == property
        assert unit in property.units.all()

    def test_unit_cascade_delete_with_property(self):
        """Unit is deleted when Property is deleted (CASCADE)"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1"
        )

        unit_id = unit.id
        property.delete()

        assert not Unit.objects.filter(id=unit_id).exists()

    def test_unit_optional_fields(self):
        """Unit can be created with only required fields"""
        property = Property.objects.create(
            name="Test Property",
            street="Main St",
            postal_code="12345",
            city="Berlin"
        )

        unit = Unit.objects.create(
            property=property,
            unit_label="A1"
        )

        assert unit.floor == ""
        assert unit.rooms is None
        assert unit.area_sqm is None
        assert unit.notes == ""
        assert unit.is_active is True

    def test_unit_is_archived_index(self):
        """is_archived field has database index"""
        from django.db import connection

        # Get table name
        table_name = Unit._meta.db_table

        # Check indexes
        with connection.cursor() as cursor:
            # Get all indexes for the table
            cursor.execute(f"""
                SELECT indexname FROM pg_indexes
                WHERE tablename = '{table_name}'
                AND indexname LIKE '%is_arch%'
            """)
            indexes = cursor.fetchall()

        # Should have at least one index on is_archived
        assert len(indexes) > 0
