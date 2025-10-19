"""
Vendor Authentication Service
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from landlord.models import Vendor, VendorAuthToken


def verify_vendor_token(token_id: str) -> Vendor | None:
    """
    Verify and consume a vendor auth token.
    Returns the vendor if valid, None otherwise.
    """
    try:
        token = VendorAuthToken.objects.select_related("vendor").get(id=token_id)
    except (VendorAuthToken.DoesNotExist, ValueError):
        return None

    if not token.is_valid():
        return None

    if not token.vendor:
        return None

    # Mark as used
    with transaction.atomic():
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])

    return token.vendor
