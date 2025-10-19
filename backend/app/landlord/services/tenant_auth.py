"""
Tenant authentication service for magic-link login
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from landlord.models import Tenant, TenantAuthToken


def create_magic_link_token(email: str, request_meta: dict | None = None) -> str:
    """Create a magic-link token for tenant login"""
    # Find tenant by email
    try:
        tenant = Tenant.objects.get(primary_email__iexact=email, is_active=True)
    except Tenant.DoesNotExist:
        tenant = None

    # Create token (even if tenant not found - prevents email enumeration)
    token = TenantAuthToken.objects.create(
        tenant=tenant,
        email=email.lower(),
        purpose=TenantAuthToken.Purpose.LOGIN,
        expires_at=timezone.now() + timedelta(minutes=15),
        ip_hash=_hash_value(request_meta.get("REMOTE_ADDR", "")) if request_meta else "",
        ua_hash=_hash_value(request_meta.get("HTTP_USER_AGENT", "")) if request_meta else "",
    )

    return str(token.id)


def verify_magic_link_token(token_id: str) -> Tenant | None:
    """Verify and consume a magic-link token"""
    try:
        token = TenantAuthToken.objects.select_related("tenant").get(id=token_id)
    except (TenantAuthToken.DoesNotExist, ValueError):
        return None

    if not token.is_valid():
        return None

    if not token.tenant or not token.tenant.is_active:
        return None

    # Mark as used
    with transaction.atomic():
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])

    return token.tenant


def _hash_value(value: str) -> str:
    """Hash a value for privacy (IP, UA)"""
    if not value:
        return ""
    return hashlib.sha256(value.encode()).hexdigest()[:64]
