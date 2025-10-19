"""
Tests for Checklist Models (M16)
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from landlord.models import (
    Checklist,
    ChecklistItem,
    ChecklistTemplate,
    Property,
    Tenant,
    Unit,
)

User = get_user_model()


@pytest.mark.django_db
class TestChecklistModels:
    """Test Checklist Models (M16)"""

    def test_create_checklist_template(self):
        """Test creating a checklist template"""
        template = ChecklistTemplate.objects.create(
            name="Standard Einzug",
            template_type=ChecklistTemplate.TemplateType.MOVE_IN,
            description="Standard-Prüfpunkte für Einzug",
            default_items=[
                {"name": "Fenster", "category": "Wohnzimmer", "order": 1},
                {"name": "Türen", "category": "Wohnzimmer", "order": 2},
                {"name": "Herd", "category": "Küche", "order": 3},
            ]
        )

        assert template.pk is not None
        assert template.name == "Standard Einzug"
        assert template.template_type == ChecklistTemplate.TemplateType.MOVE_IN
        assert len(template.default_items) == 3
        assert template.is_active is True

    def test_create_checklist(self):
        """Test creating a checklist"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        user = User.objects.create_user(username='staff', password='test123')

        checklist = Checklist.objects.create(
            unit=unit,
            title="Einzug A1 - Mustermann",
            checklist_type=ChecklistTemplate.TemplateType.MOVE_IN,
            checklist_date=date.today(),
            conducted_by=user,
            status=Checklist.Status.DRAFT
        )

        assert checklist.pk is not None
        assert checklist.unit == unit
        assert checklist.status == Checklist.Status.DRAFT
        assert checklist.conducted_by == user

    def test_checklist_completion_percentage(self):
        """Test completion percentage calculation"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")

        checklist = Checklist.objects.create(
            unit=unit,
            title="Test Checklist",
            checklist_type=ChecklistTemplate.TemplateType.INSPECTION,
            checklist_date=date.today()
        )

        # No items = 0%
        assert checklist.completion_percentage == 0.0

        # Create 4 items
        for i in range(4):
            ChecklistItem.objects.create(
                checklist=checklist,
                category="Test",
                name=f"Item {i+1}",
                order=i
            )

        # None checked = 0%
        # Re-fetch to get fresh queryset
        checklist = Checklist.objects.get(pk=checklist.pk)
        assert checklist.completion_percentage == 0.0

        # Check 2 items = 50%
        items = list(checklist.items.all())
        items[0].is_checked = True
        items[0].save()
        items[1].is_checked = True
        items[1].save()

        # Re-fetch to get updated counts
        checklist = Checklist.objects.get(pk=checklist.pk)
        assert checklist.completion_percentage == 50.0

        # Check all = 100%
        for item in ChecklistItem.objects.filter(checklist=checklist):
            item.is_checked = True
            item.save()

        # Re-fetch to get final counts
        checklist = Checklist.objects.get(pk=checklist.pk)
        assert checklist.completion_percentage == 100.0

    def test_checklist_item_with_condition(self):
        """Test checklist item with condition and notes"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")

        checklist = Checklist.objects.create(
            unit=unit,
            title="Test",
            checklist_type=ChecklistTemplate.TemplateType.MOVE_OUT,
            checklist_date=date.today()
        )

        item = ChecklistItem.objects.create(
            checklist=checklist,
            category="Küche",
            name="Herd",
            order=1,
            is_checked=True,
            condition=ChecklistItem.Condition.GOOD,
            notes="Kleine Kratzer auf der Oberfläche"
        )

        assert item.is_checked is True
        assert item.condition == ChecklistItem.Condition.GOOD
        assert "Kratzer" in item.notes

    def test_checklist_with_tenant(self):
        """Test checklist with tenant assignment"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        tenant = Tenant.objects.create(
            unit=unit,
            primary_email="tenant@example.com",
            is_active=True
        )

        checklist = Checklist.objects.create(
            unit=unit,
            tenant=tenant,
            title="Einzug - tenant@example.com",
            checklist_type=ChecklistTemplate.TemplateType.MOVE_IN,
            checklist_date=date.today()
        )

        assert checklist.tenant == tenant
        assert checklist.unit == unit

    def test_checklist_status_is_completed(self):
        """Test is_completed property"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")

        checklist = Checklist.objects.create(
            unit=unit,
            title="Test",
            checklist_type=ChecklistTemplate.TemplateType.INSPECTION,
            checklist_date=date.today(),
            status=Checklist.Status.DRAFT
        )

        assert checklist.is_completed is False

        checklist.status = Checklist.Status.COMPLETED
        checklist.save()

        assert checklist.is_completed is True

    def test_checklist_ordering(self):
        """Test default ordering (newest first)"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")

        checklist1 = Checklist.objects.create(
            unit=unit,
            title="Old Checklist",
            checklist_type=ChecklistTemplate.TemplateType.INSPECTION,
            checklist_date=date(2024, 1, 1)
        )

        checklist2 = Checklist.objects.create(
            unit=unit,
            title="New Checklist",
            checklist_type=ChecklistTemplate.TemplateType.INSPECTION,
            checklist_date=date(2025, 1, 1)
        )

        checklists = list(Checklist.objects.all())
        assert checklists[0] == checklist2  # Newest first
        assert checklists[1] == checklist1

    def test_checklist_item_str(self):
        """Test ChecklistItem __str__ method"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")

        checklist = Checklist.objects.create(
            unit=unit,
            title="Test",
            checklist_type=ChecklistTemplate.TemplateType.INSPECTION,
            checklist_date=date.today()
        )

        item_checked = ChecklistItem.objects.create(
            checklist=checklist,
            category="Bad",
            name="Dusche",
            is_checked=True
        )

        item_unchecked = ChecklistItem.objects.create(
            checklist=checklist,
            category="Bad",
            name="WC",
            is_checked=False
        )

        assert "✓" in str(item_checked)
        assert "Bad" in str(item_checked)
        assert "Dusche" in str(item_checked)

        assert "○" in str(item_unchecked)
        assert "WC" in str(item_unchecked)
