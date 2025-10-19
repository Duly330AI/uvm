"""
Tests for PaymentTransaction Model (M12b)
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from landlord.models import PaymentTransaction, Contract, Unit, Tenant, Property


@pytest.mark.django_db
class TestPaymentTransactionModel:
    """Test PaymentTransaction Model functionality"""

    def test_create_payment(self):
        """Test creating a basic payment transaction"""
        # Setup
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
            rent_amount=Decimal("500.00"),
            additional_costs=Decimal("100.00"),
            status=Contract.Status.ACTIVE
        )

        # Create payment
        payment = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("600.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )

        # Assert
        assert payment.pk is not None
        assert payment.contract == contract
        assert payment.amount == Decimal("600.00")
        assert payment.payment_type == PaymentTransaction.Type.RENT
        assert payment.status == PaymentTransaction.Status.RECEIVED
        assert payment.is_overdue is False

    def test_payment_with_bank_details(self):
        """Test payment with bank details from CSV import"""
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
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        payment = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED,
            reference="Miete Oktober 2025",
            sender_name="Max Mustermann",
            sender_iban="DE89370400440532013000"
        )

        assert payment.reference == "Miete Oktober 2025"
        assert payment.sender_name == "Max Mustermann"
        assert payment.sender_iban == "DE89370400440532013000"

    def test_payment_is_overdue(self):
        """Test is_overdue property"""
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
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        # Payment with past due_date and pending status = overdue
        payment_overdue = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            due_date=date.today() - timedelta(days=5),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.PENDING
        )
        assert payment_overdue.is_overdue is True

        # Payment with future due_date = not overdue
        payment_ok = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            due_date=date.today() + timedelta(days=5),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.PENDING
        )
        assert payment_ok.is_overdue is False

        # Payment received = not overdue (even if past due_date)
        payment_received = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            due_date=date.today() - timedelta(days=5),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        assert payment_received.is_overdue is False

    def test_payment_types(self):
        """Test different payment types"""
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
            rent_amount=Decimal("500.00"),
            deposit_amount=Decimal("1500.00"),
            status=Contract.Status.ACTIVE
        )

        # Rent payment
        rent = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        assert rent.get_payment_type_display() == "Miete"

        # Deposit payment
        deposit = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("1500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.DEPOSIT,
            status=PaymentTransaction.Status.RECEIVED
        )
        assert deposit.get_payment_type_display() == "Kaution"

        # Additional costs payment
        additional = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("100.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.ADDITIONAL_COSTS,
            status=PaymentTransaction.Status.RECEIVED
        )
        assert additional.get_payment_type_display() == "Nebenkosten"

    def test_payment_csv_import_metadata(self):
        """Test CSV import metadata storage"""
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
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        csv_row = {
            "Datum": "18.10.2025",
            "Betrag": "500,00",
            "Verwendungszweck": "Miete Oktober",
            "Auftraggeber": "Max Mustermann"
        }

        payment = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date(2025, 10, 18),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED,
            csv_import_date=timezone.now(),
            csv_row_data=csv_row
        )

        assert payment.csv_import_date is not None
        assert payment.csv_row_data == csv_row
        assert payment.csv_row_data["Datum"] == "18.10.2025"

    def test_payment_str_representation(self):
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
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        payment = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date(2025, 10, 18),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )

        str_repr = str(payment)
        assert "Miete" in str_repr
        assert "€500" in str_repr
        assert "A1" in str_repr
        assert "2025-10-18" in str_repr

    def test_payment_ordering(self):
        """Test default ordering (newest first)"""
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
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        # Create payments in random order
        payment1 = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date(2025, 10, 1),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        payment3 = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date(2025, 10, 15),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        payment2 = PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date(2025, 10, 8),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )

        # Should be ordered by transaction_date DESC
        payments = list(PaymentTransaction.objects.all())
        assert payments[0] == payment3  # 15th (newest)
        assert payments[1] == payment2  # 8th
        assert payments[2] == payment1  # 1st (oldest)
