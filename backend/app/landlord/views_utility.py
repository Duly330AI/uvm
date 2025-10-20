"""
M14: Nebenkostenabrechnung Views
M17: Utility Meter Default Prefill API
"""
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from landlord.models import Property, Unit, UtilityReading
from landlord.services.utility_calculator import UtilityCostCalculator
from landlord.services.utility_meter_service import get_default_meter, get_last_reading

# ============================================================================
# M17: UTILITY METER PREFILL API
# ============================================================================

@login_required
@require_http_methods(["GET"])
def api_get_default_meter(request):
    """
    M17: API endpoint to get the default meter for a scope + meter_type.

    Query params:
        - scope_type: 'property' or 'unit'
        - scope_id: ID of the Property or Unit
        - meter_type: 'cold_water', 'hot_water', 'electricity', 'gas'

    Returns:
        {
            meter_id: int or null,
            serial_number: str or null,
            has_multiple: bool,
            initial_reading_value: float or null,
            meters: [] (only if has_multiple=true)
        }
    """
    scope_type = request.GET.get('scope_type')
    scope_id = request.GET.get('scope_id')
    meter_type = request.GET.get('meter_type')

    # Validation
    if not all([scope_type, scope_id, meter_type]):
        return JsonResponse({
            'error': 'Missing required parameters: scope_type, scope_id, meter_type'
        }, status=400)

    if scope_type not in ['property', 'unit']:
        return JsonResponse({
            'error': 'Invalid scope_type. Must be "property" or "unit"'
        }, status=400)

    try:
        scope_id = int(scope_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid scope_id. Must be an integer'}, status=400)

    # Call service
    try:
        result = get_default_meter(scope_type, scope_id, meter_type)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_last_reading(request):
    """
    M17: API endpoint to get the last reading for a meter.

    Query params:
        - meter_id: ID of the UtilityMeter

    Returns:
        {
            previous_value: float or null,
            reading_date: str (ISO) or null,
            is_initial: bool
        }
    """
    meter_id = request.GET.get('meter_id')

    if not meter_id:
        return JsonResponse({'error': 'Missing required parameter: meter_id'}, status=400)

    try:
        meter_id = int(meter_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid meter_id. Must be an integer'}, status=400)

    # Call service
    try:
        result = get_last_reading(meter_id)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# M14: UTILITY READINGS VIEWS
# ============================================================================


@login_required
def utility_readings_list(request):
    """
    M14: Liste aller Zählerstände mit Filter-Optionen
    """
    readings = UtilityReading.objects.select_related(
        'unit', 'unit__property', 'recorded_by'
    ).all()

    # Filter by property
    property_id = request.GET.get('property')
    if property_id:
        readings = readings.filter(unit__property_id=property_id)

    # Filter by unit
    unit_id = request.GET.get('unit')
    if unit_id:
        readings = readings.filter(unit_id=unit_id)

    # Filter by meter type
    meter_type = request.GET.get('meter_type')
    if meter_type:
        readings = readings.filter(meter_type=meter_type)

    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        readings = readings.filter(reading_date__gte=start_date)
    if end_date:
        readings = readings.filter(reading_date__lte=end_date)

    # Get filter options
    properties = Property.objects.all()
    units = Unit.objects.filter(is_active=True).select_related('property')

    context = {
        'readings': readings[:100],  # Limit for performance
        'properties': properties,
        'units': units,
        'meter_types': UtilityReading.MeterType.choices,
        'filters': {
            'property': property_id,
            'unit': unit_id,
            'meter_type': meter_type,
            'start_date': start_date,
            'end_date': end_date,
        }
    }

    return render(request, 'portal/utility_readings_list.html', context)


@login_required
def utility_reading_create(request):
    """
    M14: Neuen Zählerstand erfassen (HTMX)
    """
    if request.method == 'POST':
        unit_id = request.POST.get('unit_id')  # Fixed: was 'unit', should be 'unit_id'
        meter_type = request.POST.get('meter_type')
        reading_date = request.POST.get('reading_date')
        current_value = request.POST.get('current_value')
        meter_number = request.POST.get('meter_number', '')
        notes = request.POST.get('notes', '')

        try:
            unit = Unit.objects.get(id=unit_id)

            reading = UtilityReading.objects.create(
                unit=unit,
                meter_type=meter_type,
                reading_date=reading_date,
                current_value=Decimal(current_value),
                meter_number=meter_number,
                notes=notes,
                recorded_by=request.user
            )

            messages.success(
                request,
                f'✓ Zählerstand erfasst: {reading.get_meter_type_display()} - {unit.unit_label}'
            )

            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'message': 'Zählerstand erfasst',
                    'reading_id': reading.id
                })

            return redirect('portal_utility_readings')

        except Exception as e:
            messages.error(request, f'Fehler: {str(e)}')
            if request.headers.get('HX-Request'):
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            return redirect('portal_utility_readings')

    # GET: Show form
    # Order: "Allgemein/Gebäude" units first, then regular units
    units = Unit.objects.filter(is_active=True).select_related('property').order_by(
        '-unit_label',  # "Allgemein" and "Gebäude" come first (reverse alphabetical)
        'property__name',
        'unit_label'
    )
    context = {
        'units': units,
        'meter_types': UtilityReading.MeterType.choices,
        'today': date.today().isoformat()  # ISO format for HTML5 date input
    }
    return render(request, 'portal/utility_reading_form.html', context)


@login_required
def utility_calculation_preview(request):
    """
    M14: Vorschau der Nebenkostenabrechnung
    """
    if request.method == 'POST':
        property_id = request.POST.get('property')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Cost inputs
        total_heating = Decimal(request.POST.get('total_heating', '0'))
        total_water = Decimal(request.POST.get('total_water', '0'))
        total_waste = Decimal(request.POST.get('total_waste', '0'))
        total_property_tax = Decimal(request.POST.get('total_property_tax', '0'))
        total_other = Decimal(request.POST.get('total_other', '0'))

        try:
            # Calculate costs
            calculator = UtilityCostCalculator(
                property_id=int(property_id),
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date)
            )

            results = calculator.calculate_all_costs(
                total_heating=total_heating,
                total_water=total_water,
                total_waste=total_waste,
                total_property_tax=total_property_tax,
                total_other=total_other
            )

            summary = calculator.get_summary()

            # Calculate totals
            total_costs = sum(r['total_costs'] for r in results.values())
            total_prepayment = sum(r['prepayment'] for r in results.values())
            total_balance = sum(r['balance'] for r in results.values())
            average_per_unit = total_costs / len(results) if results else Decimal('0')

            context = {
                'results': results,
                'summary': summary,
                'totals': {
                    'costs': total_costs,
                    'prepayment': total_prepayment,
                    'balance': total_balance,
                },
                'average_per_unit': average_per_unit,
                'inputs': {
                    'property': get_object_or_404(Property, id=property_id),
                    'start_date': date.fromisoformat(start_date),  # Convert string to date for template
                    'end_date': date.fromisoformat(end_date),      # Convert string to date for template
                    'heating': total_heating,
                    'water': total_water,
                    'waste': total_waste,
                    'property_tax': total_property_tax,
                    'other': total_other,
                }
            }

            return render(request, 'portal/utility_calculation_preview.html', context)

        except Exception as e:
            messages.error(request, f'Fehler bei Berechnung: {str(e)}')
            return redirect('portal_utility_calculation')

    # GET: Show form
    properties = Property.objects.all()

    # Suggest period (last year)
    today = date.today()
    suggested_start = date(today.year - 1, 1, 1)
    suggested_end = date(today.year - 1, 12, 31)

    context = {
        'properties': properties,
        'suggested_start': suggested_start.isoformat(),  # ISO format for HTML5 date input
        'suggested_end': suggested_end.isoformat(),      # ISO format for HTML5 date input
    }

    return render(request, 'portal/utility_calculation_form.html', context)


@login_required
def utility_billing_export(request, property_id: int, start_date: str, end_date: str):
    """
    M14: Export Nebenkostenabrechnung als CSV (PDF kommt später)
    """
    import csv

    from django.http import HttpResponse

    # Get calculation data from POST
    if request.method != 'POST':
        messages.error(request, 'Nur POST erlaubt')
        return redirect('portal_utility_calculation')

    total_heating = Decimal(request.POST.get('total_heating', '0'))
    total_water = Decimal(request.POST.get('total_water', '0'))
    total_waste = Decimal(request.POST.get('total_waste', '0'))
    total_property_tax = Decimal(request.POST.get('total_property_tax', '0'))
    total_other = Decimal(request.POST.get('total_other', '0'))

    calculator = UtilityCostCalculator(
        property_id=property_id,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date)
    )

    results = calculator.calculate_all_costs(
        total_heating=total_heating,
        total_water=total_water,
        total_waste=total_waste,
        total_property_tax=total_property_tax,
        total_other=total_other
    )

    # Create CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="nebenkostenabrechnung_{start_date}_{end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Wohnung',
        'Mieter',
        'Heizkosten',
        'Wasser',
        'Müll',
        'Grundsteuer',
        'Sonstiges',
        'Gesamt',
        'Vorauszahlung',
        'Nachzahlung/Guthaben'
    ])

    for result in results.values():
        writer.writerow([
            result['unit'],
            result['tenant'],
            f"{result['heating']['total']:.2f}",
            f"{result['water']['total']:.2f}",
            f"{result['waste']:.2f}",
            f"{result['property_tax']:.2f}",
            f"{result['other']:.2f}",
            f"{result['total_costs']:.2f}",
            f"{result['prepayment']:.2f}",
            f"{result['balance']:.2f}",
        ])

    return response
