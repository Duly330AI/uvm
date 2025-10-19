#!/usr/bin/env python
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.utils import timezone
from landlord.models import TenantAuthToken

token_id = '8c82df58-4982-4223-acd2-183cf83b11ee'

try:
    token = TenantAuthToken.objects.get(id=token_id)
    print("✓ Token exists")
    print(f"  Email: {token.email}")
    print(f"  Expires: {token.expires_at}")
    print(f"  Now: {timezone.now()}")
    print(f"  Used at: {token.used_at}")
    print(f"  Is expired: {token.expires_at < timezone.now()}")
    print(f"  Is used: {token.used_at is not None}")
except TenantAuthToken.DoesNotExist:
    print("❌ Token does not exist!")
