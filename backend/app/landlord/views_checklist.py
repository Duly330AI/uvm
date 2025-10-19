"""
M16: Checklisten Views
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from landlord.models import Checklist, ChecklistItem, ChecklistTemplate, Tenant, Unit


@login_required
def checklist_templates_list(request):
    """
    M16: Liste aller Checklisten-Vorlagen
    """
    templates = ChecklistTemplate.objects.filter(is_active=True)

    # Filter by type
    template_type = request.GET.get('type')
    if template_type:
        templates = templates.filter(template_type=template_type)

    context = {
        'templates': templates,
        'template_types': ChecklistTemplate.TemplateType.choices,
        'current_type': template_type,
    }

    return render(request, 'portal/checklist_templates_list.html', context)


@login_required
def checklists_list(request):
    """
    M16: Liste aller Checklisten
    """
    checklists = Checklist.objects.select_related(
        'unit', 'tenant', 'template', 'conducted_by'
    ).all()

    # Filters
    unit_id = request.GET.get('unit')
    if unit_id:
        checklists = checklists.filter(unit_id=unit_id)

    status = request.GET.get('status')
    if status:
        checklists = checklists.filter(status=status)

    checklist_type = request.GET.get('type')
    if checklist_type:
        checklists = checklists.filter(checklist_type=checklist_type)

    context = {
        'checklists': checklists[:50],  # Limit for performance
        'units': Unit.objects.filter(is_active=True),
        'statuses': Checklist.Status.choices,
        'types': ChecklistTemplate.TemplateType.choices,
        'filters': {
            'unit': unit_id,
            'status': status,
            'type': checklist_type,
        }
    }

    return render(request, 'portal/checklists_list.html', context)


@login_required
def checklist_create(request):
    """
    M16: Neue Checkliste erstellen (aus Template oder blank)
    """
    if request.method == 'POST':
        template_id = request.POST.get('template')
        unit_id = request.POST.get('unit')
        tenant_id = request.POST.get('tenant')
        title = request.POST.get('title')
        checklist_type = request.POST.get('checklist_type')
        checklist_date = request.POST.get('checklist_date')

        try:
            unit = Unit.objects.get(id=unit_id)

            # Create checklist
            checklist = Checklist.objects.create(
                unit=unit,
                tenant_id=tenant_id if tenant_id else None,
                title=title,
                checklist_type=checklist_type,
                checklist_date=checklist_date,
                conducted_by=request.user,
                status=Checklist.Status.DRAFT
            )

            # If template selected, create items from template
            if template_id:
                template = ChecklistTemplate.objects.get(id=template_id)
                checklist.template = template
                checklist.save()

                # Create items from template's default_items
                if template.default_items:
                    for item_data in template.default_items:
                        ChecklistItem.objects.create(
                            checklist=checklist,
                            category=item_data.get('category', 'Allgemein'),
                            name=item_data['name'],
                            order=item_data.get('order', 0)
                        )

            messages.success(
                request,
                f'✓ Checkliste "{title}" erstellt mit {checklist.items.count()} Prüfpunkten'
            )

            return redirect('portal_checklist_detail', pk=checklist.id)

        except Exception as e:
            messages.error(request, f'Fehler: {str(e)}')
            return redirect('portal_checklists')

    # GET: Show form
    templates = ChecklistTemplate.objects.filter(is_active=True)
    units = Unit.objects.filter(is_active=True).select_related('property')
    tenants = Tenant.objects.filter(is_active=True)

    context = {
        'templates': templates,
        'units': units,
        'tenants': tenants,
        'types': ChecklistTemplate.TemplateType.choices,
        'today': date.today(),
    }

    return render(request, 'portal/checklist_create.html', context)


@login_required
def checklist_detail(request, pk: int):
    """
    M16: Checklisten-Details mit allen Items
    """
    checklist = get_object_or_404(
        Checklist.objects.select_related('unit', 'tenant', 'template'),
        pk=pk
    )

    # Group items by category
    items = checklist.items.all()
    items_by_category = {}
    for item in items:
        if item.category not in items_by_category:
            items_by_category[item.category] = []
        items_by_category[item.category].append(item)

    context = {
        'checklist': checklist,
        'items_by_category': items_by_category,
        'total_items': items.count(),
        'checked_items': items.filter(is_checked=True).count(),
    }

    return render(request, 'portal/checklist_detail.html', context)


@login_required
def checklist_item_update(request, pk: int):
    """
    M16: Update einzelner Checklist-Item (HTMX)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    item = get_object_or_404(ChecklistItem, pk=pk)

    # Update fields
    item.is_checked = request.POST.get('is_checked') == 'true'
    item.condition = request.POST.get('condition', '')
    item.notes = request.POST.get('notes', '')

    # Handle photo upload
    if 'photo' in request.FILES:
        item.photo = request.FILES['photo']

    item.save()

    # Update checklist status if all items checked
    checklist = item.checklist
    if checklist.items.count() > 0:
        all_checked = checklist.items.filter(is_checked=False).count() == 0
        if all_checked and checklist.status == Checklist.Status.DRAFT:
            checklist.status = Checklist.Status.IN_PROGRESS
            checklist.save()

    if request.headers.get('HX-Request'):
        return JsonResponse({
            'success': True,
            'item_id': item.id,
            'is_checked': item.is_checked,
            'completion': checklist.completion_percentage
        })

    return redirect('portal_checklist_detail', pk=item.checklist.id)


@login_required
def checklist_complete(request, pk: int):
    """
    M16: Checkliste als abgeschlossen markieren
    """
    checklist = get_object_or_404(Checklist, pk=pk)

    if request.method == 'POST':
        from django.utils import timezone

        checklist.status = Checklist.Status.COMPLETED
        checklist.completed_at = timezone.now()
        checklist.save()

        messages.success(
            request,
            f'✓ Checkliste "{checklist.title}" wurde abgeschlossen!'
        )

        return redirect('portal_checklist_detail', pk=pk)

    # GET: Confirmation page
    context = {
        'checklist': checklist,
        'completion': checklist.completion_percentage,
        'total_items': checklist.items.count(),
        'checked_items': checklist.items.filter(is_checked=True).count(),
    }

    return render(request, 'portal/checklist_complete_confirm.html', context)


@login_required
def checklist_export_pdf(request, pk: int):
    """
    M16: Checkliste als PDF exportieren
    """
    checklist = get_object_or_404(
        Checklist.objects.select_related('unit', 'tenant'),
        pk=pk
    )

    # For now, simple HTML-to-PDF approach
    # TODO: Implement proper PDF generation with ReportLab or WeasyPrint

    items = checklist.items.all()
    items_by_category = {}
    for item in items:
        if item.category not in items_by_category:
            items_by_category[item.category] = []
        items_by_category[item.category].append(item)

    context = {
        'checklist': checklist,
        'items_by_category': items_by_category,
    }

    # Simple HTML response for now (browser can print to PDF)
    response = render(request, 'portal/checklist_pdf.html', context)
    response['Content-Type'] = 'text/html; charset=utf-8'

    return response
