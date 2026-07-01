#!/usr/bin/env python
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.utils import timezone  # noqa: E402
from landlord.models import TenantAuthToken  # noqa: E402

token_id = '00000000-0000-0000-0000-000000000000'

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
