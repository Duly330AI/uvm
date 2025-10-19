"""
Contract Management Views (M12a)
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from landlord.models import Contract, Tenant, Unit


@staff_member_required
def contracts_list(request):
    """M12a: List all contracts with filters"""
    contracts = Contract.objects.select_related(
        'unit',
        'unit__property',
        'tenant',
        'document'
    ).all()

    # Filters
    status = request.GET.get('status')
    unit_id = request.GET.get('unit')
    tenant_id = request.GET.get('tenant')
    search = request.GET.get('search', '').strip()

    if status:
        contracts = contracts.filter(status=status)
    if unit_id:
        contracts = contracts.filter(unit_id=unit_id)
    if tenant_id:
        contracts = contracts.filter(tenant_id=tenant_id)
    if search:
        contracts = contracts.filter(
            tenant__primary_email__icontains=search
        ) | contracts.filter(
            unit__unit_label__icontains=search
        )

    # Order by most recent first
    contracts = contracts.order_by('-created_at')

    context = {
        'contracts': contracts,
        'status_choices': Contract.Status.choices,
        'units': Unit.objects.filter(is_active=True).select_related('property').order_by('property__name', 'unit_label'),
        'tenants': Tenant.objects.filter(is_active=True).order_by('primary_email'),
        'filters': {
            'status': status,
            'unit': unit_id,
            'tenant': tenant_id,
            'search': search,
        }
    }
    return render(request, 'portal/contracts_list.html', context)


@staff_member_required
def contract_detail(request, pk: int):
    """M12a: Contract detail view"""
    contract = get_object_or_404(
        Contract.objects.select_related(
            'unit',
            'unit__property',
            'tenant',
            'document'
        ).prefetch_related('payments'),
        pk=pk
    )

    # Get document version history if document exists
    document_versions = []
    if contract.document:
        document_versions = contract.document.versions.select_related('uploaded_by').all()

    # Get payment statistics (M12b)
    payments = contract.payments.all()
    total_payments = sum(p.amount for p in payments)

    context = {
        'contract': contract,
        'document_versions': document_versions,
        'payments': payments,
        'total_payments': total_payments,
    }
    return render(request, 'portal/contract_detail.html', context)
