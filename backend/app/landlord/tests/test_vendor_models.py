"""
Tests for M10 Vendor Models & Signals (PR 1)
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from landlord.models import Issue, Vendor, VendorAuthToken

User = get_user_model()


@pytest.mark.django_db
class TestVendorAuthToken:
    """Test VendorAuthToken model"""

    def test_create_token(self):
        """Token can be created with expiry"""
        vendor = Vendor.objects.create(name="Test Vendor", email="vendor@test.com")
        token = VendorAuthToken.objects.create(
            vendor=vendor,
            email=vendor.email,
            expires_at=timezone.now() + timedelta(minutes=15),
            purpose=VendorAuthToken.Purpose.LOGIN
        )
        assert token.id is not None
        assert token.is_valid() is True

    def test_token_expires(self):
        """Token becomes invalid after expiry"""
        vendor = Vendor.objects.create(name="Test Vendor", email="vendor@test.com")
        token = VendorAuthToken.objects.create(
            vendor=vendor,
            email=vendor.email,
            expires_at=timezone.now() - timedelta(minutes=1),  # Expired
            purpose=VendorAuthToken.Purpose.LOGIN
        )
        assert token.is_valid() is False

    def test_token_single_use(self):
        """Token becomes invalid after use"""
        vendor = Vendor.objects.create(name="Test Vendor", email="vendor@test.com")
        token = VendorAuthToken.objects.create(
            vendor=vendor,
            email=vendor.email,
            expires_at=timezone.now() + timedelta(minutes=15),
            purpose=VendorAuthToken.Purpose.LOGIN
        )
        # Simulate use
        token.used_at = timezone.now()
        token.save()
        assert token.is_valid() is False


@pytest.mark.django_db
class TestIssueVendorFields:
    """Test Issue vendor-related fields"""

    def test_issue_has_vendor_fields(self, unit_a):
        """Issue model has all vendor tracking fields"""
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Test Issue",
            category="other"
        )
        assert hasattr(issue, 'vendor')
        assert hasattr(issue, 'vendor_first_contact_at')
        assert hasattr(issue, 'vendor_accepted_at')
        assert hasattr(issue, 'quote_document')
        assert hasattr(issue, 'invoice_document')

    def test_vendor_assignment(self, unit_a, vendor_demo):
        """Vendor can be assigned to issue"""
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Test Issue",
            category="other",
            vendor=vendor_demo
        )
        assert issue.vendor == vendor_demo


@pytest.mark.django_db
class TestIssueStatusSignals:
    """Test automatic SLA/status tracking via signals"""

    def test_first_response_at_set_on_status_change(self, unit_a):
        """first_response_at is set when status changes from NEW"""
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Test Signal",
            category="other",
            status="NEW"
        )
        assert issue.first_response_at is None

        # Change status from NEW
        issue.status = "IN_PROGRESS"
        issue.save()
        issue.refresh_from_db()

        assert issue.first_response_at is not None

    def test_first_response_at_not_overwritten(self, unit_a):
        """first_response_at is NOT overwritten on subsequent changes"""
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Test Signal",
            category="other",
            status="NEW"
        )

        # First change
        issue.status = "IN_PROGRESS"
        issue.save()
        issue.refresh_from_db()
        first_time = issue.first_response_at

        # Second change
        issue.status = "WAITING_VENDOR"
        issue.save()
        issue.refresh_from_db()

        assert issue.first_response_at == first_time  # Unchanged

    def test_done_at_set_on_completion(self, unit_a):
        """done_at is set when status changes to DONE"""
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Test Completion",
            category="other",
            status="IN_PROGRESS"
        )
        assert issue.done_at is None

        # Complete the issue
        issue.status = "DONE"
        issue.save()
        issue.refresh_from_db()

        assert issue.done_at is not None

    def test_done_at_preserved_on_reopen(self, unit_a):
        """done_at is preserved if issue reopened"""
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Test Reopen",
            category="other",
            status="IN_PROGRESS"
        )

        # Complete
        issue.status = "DONE"
        issue.save()
        issue.refresh_from_db()
        done_time = issue.done_at

        # Reopen (edge case)
        issue.status = "IN_PROGRESS"
        issue.save()
        issue.refresh_from_db()

        assert issue.done_at == done_time  # Preserved


@pytest.mark.django_db
class TestAutoTicketNumber:
    """Test automatic ticket number generation (M9.5)"""

    def test_auto_generates_ticket_no(self, unit_a):
        """Ticket number is auto-generated if not provided"""
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Auto Ticket Test",
            category="other"
        )
        issue.refresh_from_db()

        assert issue.ticket_no is not None
        assert issue.ticket_no.startswith("TCK-")
        assert len(issue.ticket_no.split("-")) == 3  # TCK-YYYY-xxxxx

    def test_manual_ticket_no_preserved(self, unit_a):
        """Manually set ticket_no is not overwritten"""
        custom_no = "CUSTOM-2025-99999"
        issue = Issue.objects.create(
            unit=unit_a,
            summary="Manual Ticket Test",
            category="other",
            ticket_no=custom_no
        )
        issue.refresh_from_db()

        assert issue.ticket_no == custom_no
