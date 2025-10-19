"""
Tests for Maintenance Models (M15)
"""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from landlord.models import MaintenanceItem, Property, Unit

User = get_user_model()


@pytest.mark.django_db
class TestMaintenanceModels:
    """Test Maintenance Models (M15)"""

    def test_create_maintenance_item_for_property(self):
        """Test creating a maintenance item for a property"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        user = User.objects.create_user(username='staff', password='test123')

        item = MaintenanceItem.objects.create(
            title="Rauchmelder-Prüfung",
            description="Jährliche Prüfung aller Rauchmelder",
            category=MaintenanceItem.Category.SMOKE_DETECTOR,
            property=prop,
            due_date=date.today() + timedelta(days=30),
            assigned_to=user,
            estimated_cost=150.00
        )

        assert item.pk is not None
        assert item.title == "Rauchmelder-Prüfung"
        assert item.category == MaintenanceItem.Category.SMOKE_DETECTOR
        assert item.property == prop
        assert item.status == MaintenanceItem.Status.PENDING
        assert item.assigned_to == user
        assert float(item.estimated_cost) == 150.00

    def test_create_maintenance_item_for_unit(self):
        """Test creating a maintenance item for a unit"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")

        item = MaintenanceItem.objects.create(
            title="Heizungswartung A1",
            category=MaintenanceItem.Category.HEATING,
            unit=unit,
            due_date=date.today() + timedelta(days=60)
        )

        assert item.unit == unit
        assert item.property is None
        assert item.status == MaintenanceItem.Status.PENDING

    def test_maintenance_item_str(self):
        """Test __str__ method"""
        prop = Property.objects.create(
            name="Testhaus",
            street="Test St",
            postal_code="12345",
            city="Test"
        )

        due = date(2025, 12, 31)
        item = MaintenanceItem.objects.create(
            title="Test Task",
            category=MaintenanceItem.Category.INSPECTION,
            property=prop,
            due_date=due
        )

        str_repr = str(item)
        assert "Test Task" in str_repr
        assert "Testhaus" in str_repr or "Test St" in str_repr
        assert "2025-12-31" in str_repr

    def test_maintenance_item_status_completed(self):
        """Test marking item as completed"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        user = User.objects.create_user(username='staff', password='test123')

        item = MaintenanceItem.objects.create(
            title="Test Task",
            category=MaintenanceItem.Category.OTHER,
            property=prop,
            due_date=date.today(),
            estimated_cost=100.00
        )

        assert item.status == MaintenanceItem.Status.PENDING
        assert item.completed_at is None
        assert item.completed_by is None

        # Mark as completed
        from django.utils import timezone
        item.status = MaintenanceItem.Status.COMPLETED
        item.completed_at = timezone.now()
        item.completed_by = user
        item.actual_cost = 120.00
        item.save()

        assert item.status == MaintenanceItem.Status.COMPLETED
        assert item.completed_at is not None
        assert item.completed_by == user
        assert float(item.actual_cost) == 120.00

    def test_maintenance_categories(self):
        """Test all maintenance categories"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        categories = [
            MaintenanceItem.Category.SMOKE_DETECTOR,
            MaintenanceItem.Category.HEATING,
            MaintenanceItem.Category.ELEVATOR,
            MaintenanceItem.Category.FIRE_EXTINGUISHER,
            MaintenanceItem.Category.INSPECTION,
            MaintenanceItem.Category.OTHER,
        ]

        for cat in categories:
            item = MaintenanceItem.objects.create(
                title=f"Test {cat}",
                category=cat,
                property=prop,
                due_date=date.today()
            )
            assert item.category == cat
            assert item.get_category_display()

    def test_maintenance_ordering(self):
        """Test default ordering (due_date, then category)"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        # Create items with different due dates
        item1 = MaintenanceItem.objects.create(
            title="Later Task",
            category=MaintenanceItem.Category.INSPECTION,
            property=prop,
            due_date=date.today() + timedelta(days=30)
        )

        item2 = MaintenanceItem.objects.create(
            title="Urgent Task",
            category=MaintenanceItem.Category.SMOKE_DETECTOR,
            property=prop,
            due_date=date.today() + timedelta(days=7)
        )

        item3 = MaintenanceItem.objects.create(
            title="Today Task",
            category=MaintenanceItem.Category.HEATING,
            property=prop,
            due_date=date.today()
        )

        items = list(MaintenanceItem.objects.all())

        # Should be ordered by due_date (earliest first)
        assert items[0] == item3  # Today
        assert items[1] == item2  # In 7 days
        assert items[2] == item1  # In 30 days

    def test_maintenance_cost_tracking(self):
        """Test cost tracking (estimated vs actual)"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        item = MaintenanceItem.objects.create(
            title="Cost Test",
            category=MaintenanceItem.Category.HEATING,
            property=prop,
            due_date=date.today(),
            estimated_cost=100.00
        )

        assert float(item.estimated_cost) == 100.00
        assert item.actual_cost is None

        # After completion
        item.actual_cost = 150.00
        item.save()

        assert float(item.actual_cost) == 150.00
        assert float(item.estimated_cost) == 100.00

    def test_maintenance_with_no_location(self):
        """Test maintenance item without property or unit"""
        item = MaintenanceItem.objects.create(
            title="General Task",
            category=MaintenanceItem.Category.INSPECTION,
            due_date=date.today()
        )

        assert item.property is None
        assert item.unit is None
        str_repr = str(item)
        assert "General Task" in str_repr
        assert "Allgemein" in str_repr

    def test_maintenance_notes(self):
        """Test notes field"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        item = MaintenanceItem.objects.create(
            title="Test Task",
            category=MaintenanceItem.Category.OTHER,
            property=prop,
            due_date=date.today(),
            notes="Initial notes"
        )

        assert item.notes == "Initial notes"

        # Update notes
        item.notes += "\n\nAdditional notes after completion"
        item.save()

        assert "Initial notes" in item.notes
        assert "Additional notes" in item.notes

    def test_maintenance_status_transitions(self):
        """Test status transitions"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        item = MaintenanceItem.objects.create(
            title="Status Test",
            category=MaintenanceItem.Category.INSPECTION,
            property=prop,
            due_date=date.today()
        )

        # Initial: PENDING
        assert item.status == MaintenanceItem.Status.PENDING

        # Can be COMPLETED
        item.status = MaintenanceItem.Status.COMPLETED
        item.save()
        assert item.status == MaintenanceItem.Status.COMPLETED

        # Create another and cancel it
        item2 = MaintenanceItem.objects.create(
            title="Cancelled Task",
            category=MaintenanceItem.Category.OTHER,
            property=prop,
            due_date=date.today()
        )
        item2.status = MaintenanceItem.Status.CANCELLED
        item2.save()
        assert item2.status == MaintenanceItem.Status.CANCELLED

    def test_maintenance_assigned_to(self):
        """Test assignment to staff user"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        user1 = User.objects.create_user(username='staff1', password='test123')
        user2 = User.objects.create_user(username='staff2', password='test123')

        item = MaintenanceItem.objects.create(
            title="Assignment Test",
            category=MaintenanceItem.Category.HEATING,
            property=prop,
            due_date=date.today(),
            assigned_to=user1
        )

        assert item.assigned_to == user1

        # Reassign
        item.assigned_to = user2
        item.save()
        assert item.assigned_to == user2

        # Can be None
        item.assigned_to = None
        item.save()
        assert item.assigned_to is None
