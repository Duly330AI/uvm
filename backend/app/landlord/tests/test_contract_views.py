"""
Tests for Contract Views (M12a)
"""
import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse

from landlord.models import Contract, Unit, Tenant, Property, Document

User = get_user_model()


@pytest.mark.django_db
class TestContractListView:
    """Test contracts list view"""

    def test_contracts_list_requires_auth(self, client):
        """Test that list view requires authentication"""
        response = client.get(reverse('portal_contracts'))
        assert response.status_code == 302  # Redirect to login

    def test_contracts_list_display(self, client):
        """Test contracts list displays all contracts"""
        # Create staff user
        staff_user = User.objects.create_user(
            username='staff',
            password='test123',
            is_staff=True
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

        # Get list
        response = client.get(reverse('portal_contracts'))
        
        assert response.status_code == 200
        assert contract in response.context['contracts']
        assert b'A1' in response.content
        assert b'test@example.com' in response.content

    def test_contracts_list_filter_by_status(self, client):
        """Test filtering contracts by status"""
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

        # Active contract
        Contract.objects.create(
            unit=unit1,
            tenant=tenant1,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        # Draft contract
        Contract.objects.create(
            unit=unit2,
            tenant=tenant2,
            start_date=date.today(),
            rent_amount=Decimal("600.00"),
            status=Contract.Status.DRAFT
        )

        # Filter for active
        response = client.get(reverse('portal_contracts') + '?status=active')
        assert response.status_code == 200
        contracts = response.context['contracts']
        assert len(contracts) == 1
        assert contracts[0].status == Contract.Status.ACTIVE

    def test_contracts_list_filter_by_unit(self, client):
        """Test filtering contracts by unit"""
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

        Contract.objects.create(
            unit=unit1,
            tenant=tenant1,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )
        Contract.objects.create(
            unit=unit2,
            tenant=tenant2,
            start_date=date.today(),
            rent_amount=Decimal("600.00"),
            status=Contract.Status.ACTIVE
        )

        # Filter by unit1
        response = client.get(reverse('portal_contracts') + f'?unit={unit1.id}')
        assert response.status_code == 200
        contracts = response.context['contracts']
        assert len(contracts) == 1
        assert contracts[0].unit == unit1


@pytest.mark.django_db
class TestContractDetailView:
    """Test contract detail view"""

    def test_contract_detail_requires_auth(self, client):
        """Test that detail view requires authentication"""
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

        response = client.get(reverse('portal_contract_detail', args=[contract.pk]))
        assert response.status_code == 302  # Redirect to login

    def test_contract_detail_display(self, client):
        """Test contract detail shows all information"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

        prop = Property.objects.create(
            name="Test Property",
            street="Test St",
            postal_code="12345",
            city="Test"
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
            phone="+49 123 456789",
            is_active=True
        )
        
        contract = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date(2025, 1, 1),
            rent_amount=Decimal("500.00"),
            additional_costs=Decimal("100.00"),
            deposit_amount=Decimal("1500.00"),
            payment_day=3,
            status=Contract.Status.ACTIVE
        )

        response = client.get(reverse('portal_contract_detail', args=[contract.pk]))
        
        assert response.status_code == 200
        assert response.context['contract'] == contract
        
        # Check content
        content = response.content.decode()
        assert 'A1' in content
        assert 'test@example.com' in content
        assert '500' in content  # Rent
        assert '100' in content  # Additional costs
        assert '1500' in content  # Deposit

    def test_contract_detail_with_document(self, client):
        """Test contract detail shows linked document"""
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
        
        # Create document
        doc = Document.objects.create(
            name="Mietvertrag.pdf",
            category=Document.Category.CONTRACT,
            unit=unit,
            size_bytes=1024
        )

        contract = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            document=doc,
            start_date=date.today(),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE
        )

        response = client.get(reverse('portal_contract_detail', args=[contract.pk]))
        
        assert response.status_code == 200
        assert 'Mietvertrag.pdf' in response.content.decode()

    def test_contract_detail_with_payments(self, client):
        """Test contract detail shows payment history"""
        from landlord.models import PaymentTransaction
        
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

        # Create payment
        PaymentTransaction.objects.create(
            contract=contract,
            amount=Decimal("500.00"),
            transaction_date=date.today(),
            payment_type=PaymentTransaction.Type.RENT,
            status=PaymentTransaction.Status.RECEIVED
        )

        response = client.get(reverse('portal_contract_detail', args=[contract.pk]))
        
        assert response.status_code == 200
        assert 'payments' in response.context
        assert response.context['total_payments'] == Decimal("500.00")

    def test_contract_detail_404_for_nonexistent(self, client):
        """Test 404 for non-existent contract"""
        staff_user = User.objects.create_user(
            username='staff', password='test123', is_staff=True
        )
        client.force_login(staff_user)

        response = client.get(reverse('portal_contract_detail', args=[99999]))
        assert response.status_code == 404
