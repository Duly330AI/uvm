"""
Phase 4.2 - Audit Logging Tests (2025-10-23):
Tests for audit trail functionality.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from landlord.models import Property, Tenant, Unit
from landlord.models_audit import AuditLog
from landlord.services.audit import (
    log_audit,
    log_contract_change,
    log_gdpr_erase,
    log_permission_change,
    log_property_archive,
)

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing."""
    return User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='test123',
        is_staff=True
    )


@pytest.fixture
def test_property(db):
    """Create test property."""
    return Property.objects.create(
        name="Test Property",
        street="Test Street 1",
        postal_code="12345",
        city="Test City"
    )


@pytest.fixture
def test_unit(db, test_property):
    """Create test unit."""
    return Unit.objects.create(
        property=test_property,
        unit_label="A101"
    )


@pytest.fixture
def test_tenant(db, test_unit):
    """Create test tenant."""
    return Tenant.objects.create(
        primary_email="tenant@example.com",
        unit=test_unit
    )


@pytest.fixture
def mock_request(admin_user):
    """Create mock request."""
    factory = RequestFactory()
    request = factory.get('/')
    request.user = admin_user
    request.META['REMOTE_ADDR'] = '127.0.0.1'
    request.META['HTTP_USER_AGENT'] = 'TestAgent/1.0'
    return request


class TestAuditLogModel:
    """Test AuditLog model constraints."""

    def test_audit_log_creation(self, admin_user, test_tenant):
        """Audit log can be created."""
        log = AuditLog.objects.create(
            user=admin_user,
            user_email=admin_user.email,
            action=AuditLog.ACTION_CREATE,
            content_type=ContentType.objects.get_for_model(test_tenant),
            object_id=test_tenant.pk,
            resource_repr=str(test_tenant),
            details={'test': 'data'}
        )

        assert log.pk is not None
        assert log.user == admin_user
        assert log.action == AuditLog.ACTION_CREATE

    def test_audit_log_immutable_after_creation(self, admin_user, test_tenant):
        """Audit logs cannot be modified after creation."""
        log = AuditLog.objects.create(
            user=admin_user,
            user_email=admin_user.email,
            action=AuditLog.ACTION_CREATE,
            resource_repr=str(test_tenant)
        )

        log.action = AuditLog.ACTION_DELETE

        with pytest.raises(ValueError, match="cannot be modified"):
            log.save()

    def test_audit_log_cannot_be_deleted(self, admin_user):
        """Audit logs cannot be deleted."""
        log = AuditLog.objects.create(
            user=admin_user,
            user_email=admin_user.email,
            action=AuditLog.ACTION_CREATE,
            resource_repr="Test"
        )

        with pytest.raises(ValueError, match="cannot be deleted"):
            log.delete()

    def test_audit_log_string_representation(self, admin_user):
        """Audit log has readable string representation."""
        log = AuditLog.objects.create(
            user=admin_user,
            user_email=admin_user.email,
            action=AuditLog.ACTION_GDPR_ERASE,
            resource_repr="Tenant: John Doe"
        )

        log_str = str(log)
        assert admin_user.email in log_str
        assert "GDPR Data Erasure" in log_str
        assert "Tenant: John Doe" in log_str


class TestAuditService:
    """Test audit service functions."""

    def test_log_audit_basic(self, admin_user, test_tenant):
        """log_audit creates audit log with basic info."""
        log = log_audit(
            user=admin_user,
            action=AuditLog.ACTION_UPDATE,
            resource=test_tenant,
            details={'field': 'name', 'old': 'Old Name', 'new': 'New Name'}
        )

        assert log.user == admin_user
        assert log.user_email == admin_user.email
        assert log.action == AuditLog.ACTION_UPDATE
        assert log.resource == test_tenant
        assert log.details['field'] == 'name'

    def test_log_audit_with_request_context(self, admin_user, test_tenant, mock_request):
        """log_audit captures request context."""
        log = log_audit(
            user=admin_user,
            action=AuditLog.ACTION_DELETE,
            resource=test_tenant,
            request=mock_request
        )

        assert log.ip_address == '127.0.0.1'
        assert 'TestAgent' in log.user_agent

    def test_log_audit_without_resource(self, admin_user):
        """log_audit works without resource (system actions)."""
        log = log_audit(
            user=admin_user,
            action=AuditLog.ACTION_EXPORT,
            resource_repr="System backup"
        )

        assert log.content_type is None
        assert log.object_id is None
        assert log.resource_repr == "System backup"

    def test_log_audit_system_action(self, test_tenant):
        """log_audit works without user (system actions)."""
        log = log_audit(
            user=None,
            action=AuditLog.ACTION_CREATE,
            resource=test_tenant
        )

        assert log.user is None
        assert log.user_email == 'system@localhost'


class TestConvenienceFunctions:
    """Test convenience functions for common audit scenarios."""

    def test_log_gdpr_erase(self, admin_user, test_tenant, mock_request):
        """log_gdpr_erase logs tenant erasure."""
        log = log_gdpr_erase(
            user=admin_user,
            tenant=test_tenant,
            request=mock_request
        )

        assert log.action == AuditLog.ACTION_GDPR_ERASE
        assert log.resource == test_tenant
        assert log.details['tenant_email'] == test_tenant.primary_email

    def test_log_property_archive(self, admin_user, test_property, mock_request):
        """log_property_archive logs property archiving."""
        log = log_property_archive(
            user=admin_user,
            property_obj=test_property,
            archived=True,
            request=mock_request
        )

        assert log.action == AuditLog.ACTION_ARCHIVE
        assert log.resource == test_property
        assert log.details['property_name'] == test_property.name

    def test_log_property_unarchive(self, admin_user, test_property):
        """log_property_archive logs property unarchiving."""
        log = log_property_archive(
            user=admin_user,
            property_obj=test_property,
            archived=False
        )

        assert log.action == AuditLog.ACTION_UNARCHIVE

    def test_log_permission_change(self, admin_user, db):
        """log_permission_change logs user permission changes."""
        target_user = User.objects.create_user(
            username='target',
            email='target@example.com'
        )

        log = log_permission_change(
            user=admin_user,
            target_user=target_user,
            changes={'is_staff': True, 'is_superuser': False}
        )

        assert log.action == AuditLog.ACTION_PERMISSION_CHANGE
        assert log.details['target_user_email'] == target_user.email
        assert log.details['changes']['is_staff'] is True

    def test_log_contract_change_create(self, admin_user, test_tenant, test_unit):
        """log_contract_change logs contract creation."""
        from decimal import Decimal

        from landlord.models import Contract

        contract = Contract.objects.create(
            tenant=test_tenant,
            unit=test_unit,
            rent_amount=Decimal('1000.00'),
            start_date='2025-01-01'
        )

        log = log_contract_change(
            user=admin_user,
            contract=contract,
            change_type='create'
        )

        assert log.action == AuditLog.ACTION_CREATE
        assert log.resource == contract
        assert log.details['tenant'] == str(test_tenant)


class TestAuditLogQuerying:
    """Test querying audit logs."""

    def test_filter_by_action(self, admin_user, test_tenant):
        """Can filter audit logs by action type."""
        log_audit(admin_user, AuditLog.ACTION_CREATE, test_tenant)
        log_audit(admin_user, AuditLog.ACTION_UPDATE, test_tenant)
        log_audit(admin_user, AuditLog.ACTION_DELETE, test_tenant)

        create_logs = AuditLog.objects.filter(action=AuditLog.ACTION_CREATE)
        assert create_logs.count() == 1

    def test_filter_by_user(self, admin_user, db):
        """Can filter audit logs by user."""
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com'
        )

        log_audit(admin_user, AuditLog.ACTION_CREATE)
        log_audit(other_user, AuditLog.ACTION_CREATE)

        admin_logs = AuditLog.objects.filter(user=admin_user)
        assert admin_logs.count() == 1

    def test_filter_by_resource_type(self, admin_user, test_tenant, test_property):
        """Can filter audit logs by resource type."""
        log_audit(admin_user, AuditLog.ACTION_UPDATE, test_tenant)
        log_audit(admin_user, AuditLog.ACTION_UPDATE, test_property)

        tenant_ct = ContentType.objects.get_for_model(Tenant)
        tenant_logs = AuditLog.objects.filter(content_type=tenant_ct)

        assert tenant_logs.count() == 1
        assert tenant_logs.first().resource == test_tenant
