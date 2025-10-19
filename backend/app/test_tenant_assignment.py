#!/usr/bin/env python
"""Test Chat + Tenant Integration"""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.utils import timezone
from landlord.models import ChatSession, Issue, Tenant, Unit
from landlord.services.chat_session import confirm

# Setup
tenant = Tenant.objects.first()
unit = Unit.objects.first()

print(f"Testing with Tenant: {tenant.primary_email}")
print(f"Unit: {unit.property.name} - {unit.unit_label}")

# Create ChatSession
session = ChatSession.objects.create(
    unit=unit,
    state='CONFIRMED',
    payload={
        'summary': 'Test Ticket mit Tenant-Zuweisung',
        'category': 'repair',
        'severity': 3
    },
    expires_at=timezone.now() + timezone.timedelta(minutes=15)
)

print(f"\n✓ ChatSession erstellt: {session.id}")

# Confirm MIT Tenant
issue_id, ticket_no = confirm(session.id, tenant=tenant)

print(f"✓ Issue erstellt: #{issue_id} - {ticket_no}")

# Verify
issue = Issue.objects.get(id=issue_id)

print("\n📋 RESULT:")
print(f"  Issue ID: {issue.pk}")
print(f"  Ticket-Nr: {issue.ticket_no}")
print(f"  Tenant: {issue.tenant.primary_email if issue.tenant else '❌ NONE'}")
print(f"  Expected: {tenant.primary_email}")

if issue.tenant == tenant:
    print("\n🎉 SUCCESS - Issue wurde korrekt dem Tenant zugewiesen!")
else:
    print("\n❌ FAIL - Tenant wurde NICHT zugewiesen!")

# Cleanup
print(f"\n🗑️  Cleanup: Issue #{issue.pk} wird gelöscht...")
issue.delete()
session.delete()
print("✓ Done")
