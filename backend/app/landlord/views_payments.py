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
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from landlord.models import Contract, PaymentTransaction


@staff_member_required
def payments_list(request):
    """M12b: List all payment transactions"""
    payments = PaymentTransaction.objects.select_related(
        'contract',
        'contract__unit',
        'contract__tenant'
    ).all()

    # Filters
    contract_id = request.GET.get('contract')
    payment_type = request.GET.get('payment_type')
    status = request.GET.get('status')

    if contract_id:
        payments = payments.filter(contract_id=contract_id)
    if payment_type:
        payments = payments.filter(payment_type=payment_type)
    if status:
        payments = payments.filter(status=status)

    # Calculate totals
    total_amount = sum(p.amount for p in payments)

    context = {
        'payments': payments,
        'total_amount': total_amount,
        'total_sum': total_amount,  # Alias for backwards compatibility with tests
        'contracts': Contract.objects.all(),
        'payment_type_choices': PaymentTransaction.Type.choices,
        'status_choices': PaymentTransaction.Status.choices,
        'filters': {
            'contract': contract_id,
            'payment_type': payment_type,
            'status': status,
        }
    }
    return render(request, 'portal/payments_list.html', context)


@staff_member_required
@transaction.atomic
def payment_csv_upload(request):
    """
    M12b: Upload CSV with payment transactions

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

                # Try to match to contract
                contract = _match_contract(sender_name, amount, reference)

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


def _match_contract(sender_name: str, amount: Decimal, reference: str) -> Optional[Contract]:
    """
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
