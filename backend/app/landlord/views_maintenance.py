"""
M15: Wartungskalender Views
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from landlord.models import MaintenanceItem, Property, Unit


@login_required
def maintenance_list(request):
    """
    M15: Liste aller Wartungsaufgaben
    """
    items = MaintenanceItem.objects.select_related(
        'property', 'unit', 'assigned_to', 'completed_by'
    ).all()

    # Filters
    status = request.GET.get('status')
    if status:
        items = items.filter(status=status)

    category = request.GET.get('category')
    if category:
        items = items.filter(category=category)

    property_id = request.GET.get('property')
    if property_id:
        items = items.filter(
            Q(property_id=property_id) | Q(unit__property_id=property_id)
        )

    # Mark overdue items
    today = date.today()
    for item in items:
        if item.status == MaintenanceItem.Status.PENDING and item.due_date < today:
            item.is_overdue_flag = True
        else:
            item.is_overdue_flag = False

    context = {
        'items': items[:50],  # Limit for performance
        'statuses': MaintenanceItem.Status.choices,
        'categories': MaintenanceItem.Category.choices,
        'properties': Property.objects.all(),
        'filters': {
            'status': status,
            'category': category,
            'property': property_id,
        },
        'today': today,
    }

    return render(request, 'portal/maintenance_list.html', context)


@login_required
def maintenance_create(request):
    """
    M15: Neue Wartungsaufgabe erstellen
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        category = request.POST.get('category')
        due_date = request.POST.get('due_date')
        property_id = request.POST.get('property')
        unit_id = request.POST.get('unit')
        estimated_cost = request.POST.get('estimated_cost')

        try:
            item = MaintenanceItem.objects.create(
                title=title,
                description=description,
                category=category,
                due_date=due_date,
                property_id=property_id if property_id else None,
                unit_id=unit_id if unit_id else None,
                assigned_to=request.user,
                estimated_cost=estimated_cost if estimated_cost else None,
                status=MaintenanceItem.Status.PENDING
            )

            messages.success(
                request,
                f'✓ Wartungsaufgabe "{title}" erstellt (fällig: {due_date})'
            )

            return redirect('portal_maintenance_detail', pk=item.id)

        except Exception as e:
            messages.error(request, f'Fehler: {str(e)}')
            return redirect('portal_maintenance_list')

    # GET: Show form
    properties = Property.objects.all()
    units = Unit.objects.filter(is_active=True).select_related('property')

    context = {
        'properties': properties,
        'units': units,
        'categories': MaintenanceItem.Category.choices,
        'today': date.today(),
    }

    return render(request, 'portal/maintenance_create.html', context)


@login_required
def maintenance_detail(request, pk: int):
    """
    M15: Detail-Ansicht einer Wartungsaufgabe
    """
    item = get_object_or_404(
        MaintenanceItem.objects.select_related(
            'property', 'unit', 'assigned_to', 'completed_by'
        ),
        pk=pk
    )

    # Check if overdue
    is_overdue = (
        item.status == MaintenanceItem.Status.PENDING
        and item.due_date < date.today()
    )

    days_diff = (item.due_date - date.today()).days

    context = {
        'item': item,
        'is_overdue': is_overdue,
        'days_until_due': days_diff,
        'today': date.today(),
    }

    return render(request, 'portal/maintenance_detail.html', context)


@login_required
def maintenance_complete(request, pk: int):
    """
    M15: Wartungsaufgabe als erledigt markieren
    """
    item = get_object_or_404(MaintenanceItem, pk=pk)

    if request.method == 'POST':
        from django.utils import timezone

        actual_cost = request.POST.get('actual_cost')
        notes = request.POST.get('notes', '')

        item.status = MaintenanceItem.Status.COMPLETED
        item.completed_at = timezone.now()
        item.completed_by = request.user

        if actual_cost:
            item.actual_cost = actual_cost

        if notes:
            item.notes = f"{item.notes}\n\n[Abgeschlossen {timezone.now().strftime('%d.%m.%Y')}]\n{notes}".strip()

        item.save()

        messages.success(
            request,
            f'✓ Wartungsaufgabe "{item.title}" wurde als erledigt markiert!'
        )

        return redirect('portal_maintenance_detail', pk=pk)

    # GET: Confirmation page
    context = {
        'item': item,
    }

    return render(request, 'portal/maintenance_complete_confirm.html', context)


@login_required
def maintenance_edit(request, pk: int):
    """
    M15: Wartungsaufgabe bearbeiten
    """
    item = get_object_or_404(MaintenanceItem, pk=pk)

    if request.method == 'POST':
        item.title = request.POST.get('title', item.title)
        item.description = request.POST.get('description', item.description)
        item.category = request.POST.get('category', item.category)
        item.due_date = request.POST.get('due_date', item.due_date)

        property_id = request.POST.get('property')
        unit_id = request.POST.get('unit')

        item.property_id = property_id if property_id else None
        item.unit_id = unit_id if unit_id else None

        estimated_cost = request.POST.get('estimated_cost')
        if estimated_cost:
            item.estimated_cost = estimated_cost

        item.save()

        messages.success(request, f'✓ Wartungsaufgabe "{item.title}" aktualisiert')
        return redirect('portal_maintenance_detail', pk=pk)

    # GET: Show form
    properties = Property.objects.all()
    units = Unit.objects.filter(is_active=True).select_related('property')

    context = {
        'item': item,
        'properties': properties,
        'units': units,
        'categories': MaintenanceItem.Category.choices,
    }

    return render(request, 'portal/maintenance_edit.html', context)


@login_required
def maintenance_delete(request, pk: int):
    """
    M15: Wartungsaufgabe löschen
    """
    item = get_object_or_404(MaintenanceItem, pk=pk)

    if request.method == 'POST':
        title = item.title
        item.delete()

        messages.success(request, f'✓ Wartungsaufgabe "{title}" gelöscht')
        return redirect('portal_maintenance_list')

    context = {
        'item': item,
    }

    return render(request, 'portal/maintenance_delete_confirm.html', context)
