"""
Tests for Payment Views (M12b)
"""
import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from io import BytesIO

from landlord.models import PaymentTransaction, Contract, Unit, Tenant, Property

User = get_user_model()


@pytest.mark.django_db
class TestPaymentListView:
    """Test payments list view"""

    def test_payments_list_requires_auth(self, client):
        """Test that list view requires authentication"""
        response = client.get(reverse('portal_payments'))
        assert response.status_code == 302  # Redirect to login

    def test_payments_list_display(self, client):
        """Test payments list displays all payments"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

        # Create test data
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
            status=PaymentTransaction.Status.RECEIVED
        )

        response = client.get(reverse('portal_payments'))
        
        assert response.status_code == 200
        assert payment in response.context['payments']
        assert b'500' in response.content

    def test_payments_list_filter_by_contract(self, client):
        """Test filtering payments by contract"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit1 = Unit.objects.create(property=prop, unit_label="A1")
        unit2 = Unit.objects.create(property=prop, unit_label="A2")
        tenant1 = Tenant.objects.create(
            unit=unit1, primary_email="tenant1@example.com", is_active=True
        )
        tenant2 = Tenant.objects.create(
            unit=unit2, primary_email="tenant2@example.com", is_active=True
        )

        contract1 = Contract.objects.create(
            unit=unit1,
            tenant=tenant1,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )
        contract2 = Contract.objects.create(
            unit=unit2,
            tenant=tenant2,
            start_date=date.today(),
            rent_amount=Decimal("600.00"),
            status=Contract.Status.ACTIVE
        )

        PaymentTransaction.objects.create(
            contract=contract1,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        PaymentTransaction.objects.create(
            contract=contract2,
            amount=Decimal("600.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )

        # Filter by contract1
        response = client.get(reverse('portal_payments') + f'?contract={contract1.id}')
        assert response.status_code == 200
        payments = response.context['payments']
        assert len(payments) == 1
        assert payments[0].contract == contract1

    def test_payments_list_filter_by_type(self, client):
        """Test filtering payments by payment type"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

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

        # Create different payment types
        PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("1500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.DEPOSIT,
            status=PaymentTransaction.Status.RECEIVED
        )

        # Filter for rent only
        response = client.get(reverse('portal_payments') + '?payment_type=rent')
        assert response.status_code == 200
        payments = response.context['payments']
        assert len(payments) == 1
        assert payments[0].payment_type == PaymentTransaction.Type.RENT

    def test_payments_list_filter_by_status(self, client):
        """Test filtering payments by status"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

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

        PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.PENDING
        )

        # Filter for received only
        response = client.get(reverse('portal_payments') + '?status=received')
        assert response.status_code == 200
        payments = response.context['payments']
        assert len(payments) == 1
        assert payments[0].status == PaymentTransaction.Status.RECEIVED

    def test_payments_list_total_sum(self, client):
        """Test that total sum is calculated correctly"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

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

        PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )
        PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )

        response = client.get(reverse('portal_payments'))
        assert response.status_code == 200
        assert response.context['total_sum'] == Decimal("1000.00")


@pytest.mark.django_db
class TestPaymentCSVUpload:
    """Test CSV upload functionality"""

    def test_csv_upload_requires_auth(self, client):
        """Test that CSV upload requires authentication"""
        response = client.post(reverse('portal_payment_csv_upload'))
        assert response.status_code == 302  # Redirect to login

    def test_csv_upload_get_shows_form(self, client):
        """Test GET request shows upload modal/form"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

        response = client.get(reverse('portal_payment_csv_upload'))
        # Should redirect to payments list (GET not allowed for upload)
        assert response.status_code in [200, 302]

    def test_csv_upload_without_file(self, client):
        """Test CSV upload without file returns error"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

        response = client.post(reverse('portal_payment_csv_upload'), {})
        assert response.status_code in [200, 302]  # Error or redirect

    def test_csv_upload_invalid_file_type(self, client):
        """Test CSV upload with non-CSV file"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

        # Create fake PDF file
        fake_file = BytesIO(b"%PDF-1.4 fake pdf")
        fake_file.name = 'not_a_csv.pdf'

        response = client.post(
            reverse('portal_payment_csv_upload'),
            {'csv_file': fake_file}
        )
        assert response.status_code in [200, 302]
