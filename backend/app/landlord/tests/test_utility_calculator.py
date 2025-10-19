"""
Tests for UtilityCostCalculator Service (M14)
"""
from datetime import date
from decimal import Decimal

import pytest
from landlord.models import Contract, Property, Tenant, Unit
from landlord.services.utility_calculator import UtilityCostCalculator


@pytest.mark.django_db
class TestUtilityCostCalculator:
    """Test UtilityCostCalculator Service"""

    def test_calculator_initialization(self):
        """Test calculator can be initialized"""
        prop = Property.objects.create(
            name="Test Property",
            street="Test St",
            postal_code="12345",
            city="Test"
        )

        calculator = UtilityCostCalculator(
            property_id=prop.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        assert calculator.property == prop
        assert calculator.start_date == date(2024, 1, 1)
        assert calculator.end_date == date(2024, 12, 31)

    def test_calculate_costs_with_no_contracts(self):
        """Test calculation with no active contracts"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        calculator = UtilityCostCalculator(
            property_id=prop.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        results = calculator.calculate_all_costs(
            total_heating=Decimal("1000.00"),
            total_water=Decimal("500.00"),
            total_waste=Decimal("200.00"),
            total_property_tax=Decimal("300.00"),
            total_other=Decimal("100.00")
        )

        assert results == {}

    def test_allocate_by_area(self):
        """Test allocation by square meters"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        # Unit 1: 50 m²
        unit1 = Unit.objects.create(
            property=prop,
            unit_label="A1",
            area_sqm=Decimal("50.00")
        )
        tenant1 = Tenant.objects.create(
            unit=unit1,
            primary_email="tenant1@example.com",
            is_active=True
        )
        contract1 = Contract.objects.create(
            unit=unit1,
            tenant=tenant1,
            start_date=date(2024, 1, 1),
            rent_amount=Decimal("500.00"),
            additional_costs=Decimal("100.00"),
            status=Contract.Status.ACTIVE,
            allocation_key=Contract.AllocationKey.AREA
        )

        # Unit 2: 100 m² (double of unit1)
        unit2 = Unit.objects.create(
            property=prop,
            unit_label="A2",
            area_sqm=Decimal("100.00")
        )
        tenant2 = Tenant.objects.create(
            unit=unit2,
            primary_email="tenant2@example.com",
            is_active=True
        )
        contract2 = Contract.objects.create(
            unit=unit2,
            tenant=tenant2,
            start_date=date(2024, 1, 1),
            rent_amount=Decimal("800.00"),
            additional_costs=Decimal("150.00"),
            status=Contract.Status.ACTIVE,
            allocation_key=Contract.AllocationKey.AREA
        )

        calculator = UtilityCostCalculator(
            property_id=prop.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        results = calculator.calculate_all_costs(
            total_heating=Decimal("1500.00"),
            total_water=Decimal("0.00"),
            total_waste=Decimal("0.00"),
            total_property_tax=Decimal("0.00"),
            total_other=Decimal("0.00")
        )

        # Total area: 150 m²
        # Unit 1 (50m²) should get 1/3 of costs
        # Unit 2 (100m²) should get 2/3 of costs

        # Heating: 30% fixed + 70% consumption (no readings, so area-based)
        # Unit1: 1500 * (50/150) = 500
        # Unit2: 1500 * (100/150) = 1000

        assert len(results) == 2
        result1 = results[contract1.id]
        result2 = results[contract2.id]

        # Unit1 should have ~500 in heating costs
        assert abs(result1['heating']['total'] - 500) < 1

        # Unit2 should have ~1000 in heating costs
        assert abs(result2['heating']['total'] - 1000) < 1

    def test_allocate_by_persons(self):
        """Test allocation by occupants"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )

        # Unit 1: 2 persons
        unit1 = Unit.objects.create(property=prop, unit_label="A1")
        tenant1 = Tenant.objects.create(
            unit=unit1, primary_email="tenant1@example.com", is_active=True
        )
        contract1 = Contract.objects.create(
            unit=unit1,
            tenant=tenant1,
            start_date=date(2024, 1, 1),
            rent_amount=Decimal("500.00"),
            additional_costs=Decimal("100.00"),
            status=Contract.Status.ACTIVE,
            allocation_key=Contract.AllocationKey.PERSONS,
            occupants_count=2
        )

        # Unit 2: 4 persons (double)
        unit2 = Unit.objects.create(property=prop, unit_label="A2")
        tenant2 = Tenant.objects.create(
            unit=unit2, primary_email="tenant2@example.com", is_active=True
        )
        contract2 = Contract.objects.create(
            unit=unit2,
            tenant=tenant2,
            start_date=date(2024, 1, 1),
            rent_amount=Decimal("800.00"),
            additional_costs=Decimal("150.00"),
            status=Contract.Status.ACTIVE,
            allocation_key=Contract.AllocationKey.PERSONS,
            occupants_count=4
        )

        calculator = UtilityCostCalculator(
            property_id=prop.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        results = calculator.calculate_all_costs(
            total_heating=Decimal("0.00"),
            total_water=Decimal("600.00"),
            total_waste=Decimal("0.00"),
            total_property_tax=Decimal("0.00"),
            total_other=Decimal("0.00")
        )

        # Total: 6 persons
        # Unit1 (2): 600 * (2/6) = 200
        # Unit2 (4): 600 * (4/6) = 400

        result1 = results[contract1.id]
        result2 = results[contract2.id]

        assert abs(result1['water']['total'] - 200) < 1
        assert abs(result2['water']['total'] - 400) < 1

    def test_prepayment_and_balance_calculation(self):
        """Test prepayment and balance calculation"""
        prop = Property.objects.create(
            street="Test St", postal_code="12345", city="Test"
        )
        unit = Unit.objects.create(
            property=prop,
            unit_label="A1",
            area_sqm=Decimal("50.00")
        )
        tenant = Tenant.objects.create(
            unit=unit,
            primary_email="tenant@example.com",
            is_active=True
        )

        # Contract with 100€/month additional costs = 1200€/year prepayment
        contract = Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date(2024, 1, 1),
            rent_amount=Decimal("500.00"),
            additional_costs=Decimal("100.00"),  # 100/month = 1200/year
            status=Contract.Status.ACTIVE,
            allocation_key=Contract.AllocationKey.UNITS
        )

        calculator = UtilityCostCalculator(
            property_id=prop.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        # Total costs: 1500€
        results = calculator.calculate_all_costs(
            total_heating=Decimal("1000.00"),
            total_water=Decimal("300.00"),
            total_waste=Decimal("100.00"),
            total_property_tax=Decimal("100.00"),
            total_other=Decimal("0.00")
        )

        result = results[contract.id]

        # Total costs should be 1500
        assert result['total_costs'] == Decimal("1500.00")

        # Prepayment: 100/month * 12 = 1200
        assert result['prepayment'] == Decimal("1200.00")

        # Balance: 1500 - 1200 = 300 (Nachzahlung)
        assert result['balance'] == Decimal("300.00")

    def test_get_summary(self):
        """Test get_summary method"""
        prop = Property.objects.create(
            name="Test Property",
            street="Test St",
            postal_code="12345",
            city="Test"
        )
        unit = Unit.objects.create(
            property=prop,
            unit_label="A1",
            area_sqm=Decimal("50.00")
        )
        tenant = Tenant.objects.create(
            unit=unit,
            primary_email="tenant@example.com",
            is_active=True
        )
        Contract.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date(2024, 1, 1),
            rent_amount=Decimal("500.00"),
            status=Contract.Status.ACTIVE,
            occupants_count=2
        )

        calculator = UtilityCostCalculator(
            property_id=prop.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        summary = calculator.get_summary()

        assert 'property' in summary
        assert 'units_count' in summary
        assert 'total_area' in summary
        assert 'total_occupants' in summary

        assert summary['units_count'] == 1
        assert summary['total_area'] == Decimal("50.00")
        assert summary['total_occupants'] == 2
