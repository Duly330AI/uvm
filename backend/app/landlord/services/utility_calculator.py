"""
M14: Nebenkostenabrechnung - Calculation Service

Berechnet Nebenkosten basierend auf verschiedenen Umlageschlüsseln:
- Nach Fläche (m²)
- Nach Personenzahl
- Nach Verbrauch (Zählerstände)
- Gleichmäßig nach Anzahl Wohnungen
"""
from datetime import date
from decimal import Decimal
from typing import Dict

from django.db.models import Q, Sum
from landlord.models import Contract, Property, Unit, UtilityReading


class UtilityCostCalculator:
    """
    Berechnet Nebenkosten für einen Abrechnungszeitraum
    """

    def __init__(self, property_id: int, start_date: date, end_date: date):
        """
        Initialize calculator for a property and period.

        Args:
            property_id: ID des Objekts
            start_date: Start der Abrechnungsperiode
            end_date: Ende der Abrechnungsperiode
        """
        self.property_id = property_id
        self.start_date = start_date
        self.end_date = end_date
        self.property = Property.objects.get(id=property_id)

        # Get all active contracts in this period
        self.contracts = Contract.objects.filter(
            unit__property_id=property_id,
            status=Contract.Status.ACTIVE,
            start_date__lte=end_date
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=start_date)
        ).select_related('unit', 'tenant')

    def calculate_all_costs(
        self,
        total_heating: Decimal,
        total_water: Decimal,
        total_waste: Decimal,
        total_property_tax: Decimal,
        total_other: Decimal = Decimal('0.00')
    ) -> Dict[int, Dict]:
        """
        Calculate all utility costs for all units.

        Args:
            total_heating: Gesamte Heizkosten für die Periode
            total_water: Gesamte Wasserkosten
            total_waste: Gesamte Müllkosten
            total_property_tax: Grundsteuer
            total_other: Sonstige Kosten

        Returns:
            Dict mit contract_id -> Kostenaufstellung
        """
        results = {}

        for contract in self.contracts:
            unit_costs = self._calculate_unit_costs(
                contract=contract,
                total_heating=total_heating,
                total_water=total_water,
                total_waste=total_waste,
                total_property_tax=total_property_tax,
                total_other=total_other
            )
            results[contract.id] = unit_costs

        return results

    def _calculate_unit_costs(
        self,
        contract: Contract,
        total_heating: Decimal,
        total_water: Decimal,
        total_waste: Decimal,
        total_property_tax: Decimal,
        total_other: Decimal
    ) -> Dict:
        """
        Calculate costs for a single unit/contract.

        Returns:
            Dict with detailed cost breakdown
        """
        allocation_key = contract.allocation_key

        # Calculate heating (usually 30% fixed + 70% consumption)
        heating_costs = self._calculate_heating_costs(
            contract, total_heating
        )

        # Water based on consumption if available, otherwise allocation key
        water_costs = self._calculate_water_costs(
            contract, total_water
        )

        # Waste and property tax based on allocation key
        waste_costs = self._allocate_by_key(
            contract, total_waste, allocation_key
        )
        property_tax_costs = self._allocate_by_key(
            contract, total_property_tax, allocation_key
        )
        other_costs = self._allocate_by_key(
            contract, total_other, allocation_key
        )

        total = (
            heating_costs['total'] +
            water_costs['total'] +
            waste_costs +
            property_tax_costs +
            other_costs
        )

        # Calculate prepayments (additional_costs from contract)
        months_in_period = self._months_in_period(contract)
        prepayment = contract.additional_costs * Decimal(str(months_in_period))
        balance = total - prepayment

        return {
            'contract_id': contract.id,
            'unit': contract.unit.unit_label,
            'unit_full': f"{contract.unit.property.name} - {contract.unit.unit_label}",
            'tenant': contract.tenant.primary_email,
            'area_sqm': contract.unit.area_sqm,  # Add area for display
            'occupants_count': contract.occupants_count,  # Add occupants for display
            'heating': heating_costs,
            'water': water_costs,
            'waste': waste_costs,
            'property_tax': property_tax_costs,
            'other': other_costs,
            'total_costs': total,
            'prepayment': prepayment,
            'balance': balance,  # Positive = Nachzahlung, Negative = Guthaben
            'allocation_key': contract.get_allocation_key_display(),
        }

    def _calculate_heating_costs(
        self, contract: Contract, total_heating: Decimal
    ) -> Dict:
        """
        Calculate heating costs (30% fixed + 70% consumption-based)
        German law: HeizkostenV
        """
        # 30% Grundkosten nach Fläche
        fixed_portion = total_heating * Decimal('0.30')
        fixed_costs = self._allocate_by_key(
            contract, fixed_portion, Contract.AllocationKey.AREA
        )

        # 70% nach Verbrauch
        consumption_portion = total_heating * Decimal('0.70')

        # Get heating consumption for this unit
        consumption = self._get_consumption(
            contract.unit, UtilityReading.MeterType.HEATING
        )

        if consumption > 0:
            # Calculate based on actual consumption
            total_consumption = self._get_total_property_consumption(
                UtilityReading.MeterType.HEATING
            )
            if total_consumption > 0:
                consumption_costs = (
                    consumption_portion *
                    (Decimal(str(consumption)) / Decimal(str(total_consumption)))
                )
            else:
                # Fallback to area-based if no consumption data
                consumption_costs = self._allocate_by_key(
                    contract, consumption_portion, Contract.AllocationKey.AREA
                )
        else:
            # No consumption data, use area-based allocation
            consumption_costs = self._allocate_by_key(
                contract, consumption_portion, Contract.AllocationKey.AREA
            )

        return {
            'fixed': fixed_costs,
            'consumption': consumption_costs,
            'total': fixed_costs + consumption_costs,
            'meter_reading': consumption
        }

    def _calculate_water_costs(
        self, contract: Contract, total_water: Decimal
    ) -> Dict:
        """Calculate water costs based on consumption or allocation key"""
        cold_water = self._get_consumption(
            contract.unit, UtilityReading.MeterType.WATER_COLD
        )
        hot_water = self._get_consumption(
            contract.unit, UtilityReading.MeterType.WATER_HOT
        )
        total_consumption = cold_water + hot_water

        if total_consumption > 0:
            # Use consumption-based allocation
            property_total = (
                self._get_total_property_consumption(UtilityReading.MeterType.WATER_COLD) +
                self._get_total_property_consumption(UtilityReading.MeterType.WATER_HOT)
            )
            if property_total > 0:
                costs = (
                    total_water *
                    (Decimal(str(total_consumption)) / Decimal(str(property_total)))
                )
            else:
                costs = self._allocate_by_key(contract, total_water, contract.allocation_key)
        else:
            # Fallback to allocation key
            costs = self._allocate_by_key(contract, total_water, contract.allocation_key)

        return {
            'cold_water': cold_water,
            'hot_water': hot_water,
            'total': costs
        }

    def _allocate_by_key(
        self, contract: Contract, total_amount: Decimal, allocation_key: str
    ) -> Decimal:
        """
        Allocate costs based on allocation key.

        Args:
            contract: Contract to calculate for
            total_amount: Total amount to allocate
            allocation_key: How to allocate (area, persons, consumption, units)

        Returns:
            Allocated amount for this unit
        """
        if allocation_key == Contract.AllocationKey.AREA:
            return self._allocate_by_area(contract, total_amount)
        elif allocation_key == Contract.AllocationKey.PERSONS:
            return self._allocate_by_persons(contract, total_amount)
        elif allocation_key == Contract.AllocationKey.UNITS:
            return self._allocate_by_units(contract, total_amount)
        elif allocation_key == Contract.AllocationKey.CONSUMPTION:
            # For generic consumption (not specific meter type)
            return self._allocate_by_area(contract, total_amount)  # Fallback
        else:
            return self._allocate_by_units(contract, total_amount)  # Fallback

    def _allocate_by_area(self, contract: Contract, total_amount: Decimal) -> Decimal:
        """Allocate by square meters"""
        unit_area = contract.unit.area_sqm or Decimal('0')
        if unit_area == 0:
            return Decimal('0')

        # Calculate total area of all units in property
        total_area = Unit.objects.filter(
            property_id=self.property_id,
            is_active=True
        ).aggregate(total=Sum('area_sqm'))['total'] or Decimal('0')

        if total_area == 0:
            return Decimal('0')

        return total_amount * (unit_area / total_area)

    def _allocate_by_persons(self, contract: Contract, total_amount: Decimal) -> Decimal:
        """Allocate by number of occupants"""
        occupants = contract.occupants_count or 1

        # Calculate total occupants in property
        total_occupants = Contract.objects.filter(
            unit__property_id=self.property_id,
            status=Contract.Status.ACTIVE
        ).aggregate(
            total=Sum('occupants_count')
        )['total'] or 0

        if total_occupants == 0:
            total_occupants = self.contracts.count()  # Assume 1 per unit

        return total_amount * (Decimal(str(occupants)) / Decimal(str(total_occupants)))

    def _allocate_by_units(self, contract: Contract, total_amount: Decimal) -> Decimal:
        """Allocate equally among all units"""
        unit_count = self.contracts.count()
        if unit_count == 0:
            return Decimal('0')
        return total_amount / Decimal(str(unit_count))

    def _get_consumption(self, unit: Unit, meter_type: str) -> float:
        """
        Get total consumption for a unit and meter type in the period.

        Returns:
            Consumption value (float)
        """
        readings = UtilityReading.objects.filter(
            unit=unit,
            meter_type=meter_type,
            reading_date__gte=self.start_date,
            reading_date__lte=self.end_date
        ).aggregate(total=Sum('consumption'))

        return float(readings['total'] or 0)

    def _get_total_property_consumption(self, meter_type: str) -> float:
        """
        Get total consumption for entire property and meter type.

        Returns:
            Total consumption (float)
        """
        readings = UtilityReading.objects.filter(
            unit__property_id=self.property_id,
            meter_type=meter_type,
            reading_date__gte=self.start_date,
            reading_date__lte=self.end_date
        ).aggregate(total=Sum('consumption'))

        return float(readings['total'] or 0)

    def _months_in_period(self, contract: Contract) -> int:
        """
        Calculate number of months the contract was active in the period.
        """
        # Simple implementation: assume full period
        # TODO: Calculate exact months considering start/end dates
        return 12  # Assuming annual billing

    def get_summary(self) -> Dict:
        """
        Get summary statistics for the calculation period.

        Returns:
            Dict with summary data
        """
        return {
            'property': str(self.property),
            'period_start': self.start_date,
            'period_end': self.end_date,
            'units_count': self.contracts.count(),
            'total_area': Unit.objects.filter(
                property_id=self.property_id,
                is_active=True
            ).aggregate(total=Sum('area_sqm'))['total'],
            'total_occupants': Contract.objects.filter(
                unit__property_id=self.property_id,
                status=Contract.Status.ACTIVE
            ).aggregate(total=Sum('occupants_count'))['total']
        }
