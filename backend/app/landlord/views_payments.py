"""
Payment Management Views (M12b)
"""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from landlord.models import Contract, PaymentTransaction


@staff_member_required
def payments_list(request):
    """
    M12b: List all payment transactions

    Phase 2.2 - Performance Optimization (2025-10-22):
    - Added pagination (50 per page) to prevent OOM with >1000 payments
    - Use DB aggregates (Sum, Count) instead of Python sum()
    - Order by transaction_date DESC for recent-first display
    """
    # Build queryset with filters
    payments_qs = PaymentTransaction.objects.select_related(
        'contract',
        'contract__unit',
        'contract__tenant'
    ).order_by('-transaction_date', '-id')  # Recent first

    # Filters
    contract_id = request.GET.get('contract')
    payment_type = request.GET.get('payment_type')
    status = request.GET.get('status')

    if contract_id:
        payments_qs = payments_qs.filter(contract_id=contract_id)
    if payment_type:
        payments_qs = payments_qs.filter(payment_type=payment_type)
    if status:
        payments_qs = payments_qs.filter(status=status)

    # Phase 2.2: DB-side aggregates (before pagination)
    totals = payments_qs.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )

    # Phase 2.2: Pagination (50 per page)
    paginator = Paginator(payments_qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'payments': page_obj.object_list,  # For template compatibility
        'total_amount': totals['total_amount'] or 0,
        'total_sum': totals['total_amount'] or 0,  # Alias for backwards compatibility with tests
        'total_count': totals['total_count'] or 0,
        'contracts': Contract.objects.all(),
        'payment_type_choices': PaymentTransaction.Type.choices,
        'status_choices': PaymentTransaction.Status.choices,
        'filters': {
            'contract': contract_id,
            'payment_type': payment_type,
            'status': status,
        },
        'paginator': paginator,
    }
    return render(request, 'portal/payments_list.html', context)


@staff_member_required
@transaction.atomic
def payment_csv_upload(request):
    """
    M12b: Upload CSV with payment transactions

    Phase 2.1 - Performance Optimization (2025-10-22):
    - Preload all active contracts once: O(N) instead of O(N×M)
    - Build in-memory lookup dictionaries for fast matching
    - Reduces 2000 rows × 1000 contracts from minutes to seconds

    Expected CSV format (flexible):
    - Date (Datum, Buchungstag, Valuta)
    - Amount (Betrag)
    - Reference (Verwendungszweck, Buchungstext)
    - Sender Name (Auftraggeber, Sender)
    - Sender IBAN (optional)
    """
    if request.method != 'POST':
        return redirect('portal_payments')

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        messages.error(request, "Keine Datei hochgeladen.")
        return redirect('portal_payments')

    # File size limit: 5 MB
    if csv_file.size > 5 * 1024 * 1024:
        messages.error(request, "Datei zu groß (max. 5 MB).")
        return redirect('portal_payments')

    # Parse CSV
    try:
        decoded_file = csv_file.read().decode('utf-8-sig')  # Handle BOM
        csv_reader = csv.DictReader(io.StringIO(decoded_file), delimiter=';')

        # Phase 2.1: Preload all active contracts ONCE (single DB query)
        active_contracts = list(
            Contract.objects.filter(
                status__in=[Contract.Status.ACTIVE, Contract.Status.DRAFT]
            ).select_related('tenant', 'unit')
        )

        # Build lookup dictionaries for O(1) matching
        contract_lookup = _build_contract_lookup(active_contracts)

        imported_count = 0
        skipped_count = 0
        errors = []

        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (after header)
            try:
                # Extract data (flexible column names)
                transaction_date = _parse_date(row)
                amount = _parse_amount(row)
                reference = _get_value(row, ['Verwendungszweck', 'Buchungstext', 'Reference', 'Text'])
                sender_name = _get_value(row, ['Auftraggeber', 'Sender', 'Name'])
                sender_iban = _get_value(row, ['IBAN', 'Kontonummer'])

                if not transaction_date or not amount:
                    skipped_count += 1
                    errors.append(f"Zeile {row_num}: Datum oder Betrag fehlt")
                    continue

                # Try to match to contract (using cached lookup)
                contract = _match_contract_cached(sender_name, amount, reference, contract_lookup)

                if not contract:
                    skipped_count += 1
                    errors.append(f"Zeile {row_num}: Kein passender Vertrag gefunden ({sender_name}, €{amount})")
                    continue

                # Create payment transaction
                PaymentTransaction.objects.create(
                    contract=contract,
                    amount=amount,
                    transaction_date=transaction_date,
                    reference=reference or '',
                    sender_name=sender_name or '',
                    sender_iban=sender_iban or '',
                    payment_type=PaymentTransaction.Type.RENT,  # Default
                    status=PaymentTransaction.Status.RECEIVED,
                    csv_import_date=timezone.now(),
                    csv_row_data=dict(row),  # Store original for debugging
                )
                imported_count += 1

            except Exception as e:
                skipped_count += 1
                errors.append(f"Zeile {row_num}: {str(e)}")

        # Show results
        if imported_count > 0:
            messages.success(request, f"✅ {imported_count} Zahlungen importiert.")
        if skipped_count > 0:
            messages.warning(request, f"⚠️ {skipped_count} Zeilen übersprungen.")
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                messages.error(request, error)
            if len(errors) > 5:
                messages.error(request, f"... und {len(errors) - 5} weitere Fehler.")

    except Exception as e:
        messages.error(request, f"CSV-Fehler: {str(e)}")

    return redirect('portal_payments')


def _parse_date(row: dict) -> Optional[datetime.date]:
    """Parse date from CSV row (flexible column names)"""
    date_str = _get_value(row, ['Datum', 'Buchungstag', 'Valuta', 'Date', 'Buchungsdatum'])
    if not date_str:
        return None

    # Try common date formats
    for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d.%m.%y', '%d/%m/%Y']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def _parse_amount(row: dict) -> Optional[Decimal]:
    """Parse amount from CSV row"""
    amount_str = _get_value(row, ['Betrag', 'Amount', 'Umsatz'])
    if not amount_str:
        return None

    # Clean amount string (remove currency, thousands separator)
    amount_str = amount_str.replace('€', '').replace('EUR', '').replace('.', '').replace(',', '.').strip()

    try:
        amount = Decimal(amount_str)
        return abs(amount)  # Always positive
    except (InvalidOperation, ValueError):
        return None


def _get_value(row: dict, possible_keys: list) -> str:
    """Get value from row using multiple possible column names"""
    for key in possible_keys:
        # Try exact match
        if key in row and row[key]:
            return str(row[key]).strip()

        # Try case-insensitive match
        for row_key in row.keys():
            if row_key.lower() == key.lower() and row[row_key]:
                return str(row[row_key]).strip()

    return ''


def _build_contract_lookup(contracts: list) -> dict:
    """
    Phase 2.1: Build lookup dictionaries for O(1) contract matching.

    Returns dict with:
    - 'by_email': {email -> contract}
    - 'by_rent': {amount_str -> [contracts]}
    - 'by_unit': {unit_label -> contract}
    """
    by_email = {}
    by_rent = {}
    by_unit = {}

    for contract in contracts:
        # Email-based lookup
        if contract.tenant and contract.tenant.primary_email:
            email_key = contract.tenant.primary_email.lower()
            by_email[email_key] = contract

        # Rent-based lookup (allow multiple contracts with same rent)
        rent_key = f"{contract.total_rent:.2f}"
        if rent_key not in by_rent:
            by_rent[rent_key] = []
        by_rent[rent_key].append(contract)

        # Unit label lookup
        if contract.unit and contract.unit.unit_label:
            label_key = contract.unit.unit_label.lower()
            by_unit[label_key] = contract

    return {
        'by_email': by_email,
        'by_rent': by_rent,
        'by_unit': by_unit,
    }


def _match_contract_cached(sender_name: str, amount: Decimal, reference: str, lookup: dict) -> Optional[Contract]:
    """
    Phase 2.1: Match payment to contract using pre-built lookup dictionaries.

    O(1) lookup instead of O(M) iteration over all contracts.

    Matching strategy:
    1. Try exact rent + email match
    2. Try exact rent + unit label match
    3. Fallback: email-only match
    """
    sender_lower = sender_name.lower() if sender_name else ''
    reference_lower = reference.lower() if reference else ''
    rent_key = f"{float(amount):.2f}"

    # Strategy 1: Exact rent match + email/unit verification
    if rent_key in lookup['by_rent']:
        candidates = lookup['by_rent'][rent_key]

        # Try email match first
        for contract in candidates:
            if contract.tenant and contract.tenant.primary_email:
                email = contract.tenant.primary_email.lower()
                if email in sender_lower:
                    return contract

        # Try unit label match
        for contract in candidates:
            if contract.unit and contract.unit.unit_label:
                label = contract.unit.unit_label.lower()
                if label in reference_lower:
                    return contract

    # Strategy 2: Email-only fallback (for partial payments or different amounts)
    for email, contract in lookup['by_email'].items():
        if email in sender_lower:
            return contract

    # Strategy 3: Unit label fallback
    for label, contract in lookup['by_unit'].items():
        if label in reference_lower:
            return contract

    return None


def _match_contract(sender_name: str, amount: Decimal, reference: str) -> Optional[Contract]:
    """
    DEPRECATED: Old O(N×M) implementation kept for backward compatibility.
    Use _match_contract_cached() instead.

    Try to match payment to a contract based on:
    1. Sender name matches tenant email or name
    2. Amount matches expected rent
    3. Reference contains unit label
    """
    # Get all active contracts
    contracts = Contract.objects.filter(
        status__in=[Contract.Status.ACTIVE, Contract.Status.DRAFT]
    ).select_related('tenant', 'unit')

    # Try exact rent match first
    for contract in contracts:
        if abs(contract.total_rent - float(amount)) < 0.01:  # Within 1 cent
            # Check if sender name matches tenant email
            if sender_name and contract.tenant.primary_email.lower() in sender_name.lower():
                return contract
            # Check if reference contains unit label
            if reference and contract.unit.unit_label.lower() in reference.lower():
                return contract

    # Fallback: Match by tenant name/email only
    for contract in contracts:
        if sender_name and contract.tenant.primary_email.lower() in sender_name.lower():
            return contract

    return None
