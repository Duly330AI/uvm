"""
Tests for Contract Model (M12a)
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import date, timedelta
from django.db import IntegrityError

from landlord.models import Contract, Unit, Tenant, Property, Document


@pytest.mark.django_db
class TestContractModel:
    """Test Contract Model basic functionality"""

    def test_create_contract(self):
        """Test creating a basic contract"""
        # Setup
        prop = Property.objects.create(
            name="Test Property",
            street="Test St 1",
            postal_code="12345",
            city="Test City"
        )
        unit = Unit.objects.create(
            property=prop,
            unit_label="A1",
            rooms=2,
            area_sqm=Decimal("50.00")
        )
        tenant = Tenant.objects.create(
            unit=unit,
            primary_email="test@example.com",
            is_active=True
        )

        # Create contract
        contract = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            additional_costs=Decimal("100.00"),
            deposit_amount=Decimal("1500.00"),
            payment_day=3,
            status=Contract.Status.ACTIVE
        )

        # Assert
        assert contract.pk is not None
        assert contract.unit == unit
        assert contract.tenant == tenant
        assert contract.rent_amount == Decimal("500.00")
        assert contract.total_rent == 600.00  # 500 + 100
        assert contract.is_active is True
        assert contract.is_unlimited is True  # No end_date

    def test_contract_total_rent_calculation(self):
        """Test total_rent property calculation"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        tenant = Tenant.objects.create(
            unit=unit, primary_email="test@example.com", is_active=True
        )

        contract = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date.today(),
            rent_amount=Decimal("800.00"),
            additional_costs=Decimal("150.00"),
            status=Contract.Status.DRAFT
        )

        assert contract.total_rent == 950.00

    def test_contract_is_unlimited(self):
        """Test is_unlimited property"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        tenant = Tenant.objects.create(
            unit=unit, primary_email="test@example.com", is_active=True
        )

        # Unlimited contract (no end_date)
        contract1 = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )
        assert contract1.is_unlimited is True

        # Limited contract (with end_date)
        contract1.status = Contract.Status.ENDED
        contract1.save()
        
        contract2 = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )
        assert contract2.is_unlimited is False

    def test_only_one_active_contract_per_unit(self):
        """Test unique constraint: Only 1 active contract per unit"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        tenant1 = Tenant.objects.create(
            unit=unit, primary_email="tenant1@example.com", is_active=True
        )

        # Create first active contract
        Contract.objects.create(
            unit=unit,
            tenant=tenant1,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        # Try to create second active contract - should fail
        with pytest.raises(IntegrityError):
            Contract.objects.create(
                unit=unit,
                tenant=tenant1,
                start_date=date.today(),
                rent_amount=Decimal("600.00"),
                status=Contract.Status.ACTIVE
            )

    def test_multiple_draft_contracts_allowed(self):
        """Test that multiple draft contracts per unit are allowed"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        tenant = Tenant.objects.create(
            unit=unit, primary_email="test@example.com", is_active=True
        )

        # Create multiple draft contracts - should work
        contract1 = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.DRAFT
        )
        contract2 = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date.today() + timedelta(days=30),
            rent_amount=Decimal("550.00"),
            status=Contract.Status.DRAFT
        )

        assert contract1.status == Contract.Status.DRAFT
        assert contract2.status == Contract.Status.DRAFT

    def test_contract_with_document(self):
        """Test contract with linked document"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        tenant = Tenant.objects.create(
            unit=unit, primary_email="test@example.com", is_active=True
        )
        
        # Create document
        doc = Document.objects.create(
            name="Mietvertrag.pdf",
            category=Document.Category.CONTRACT,
            unit=unit,
            size_bytes=1024
        )

        # Create contract with document
        contract = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            document=doc,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        assert contract.document == doc
        assert contract.document.category == Document.Category.CONTRACT

    def test_contract_str_representation(self):
        """Test __str__ method"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(property=prop, unit_label="A1")
        tenant = Tenant.objects.create(
            unit=unit, primary_email="test@example.com", is_active=True
        )

        contract = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date(2025, 1, 1),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        str_repr = str(contract)
        assert "A1" in str_repr
        assert "test@example.com" in str_repr
        assert "2025-01-01" in str_repr
