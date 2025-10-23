"""
Phase 4.2 - Audit Service (2025-10-23):
Helper functions for audit logging.

Usage:
    from landlord.services.audit import log_audit
    
    log_audit(
        user=request.user,
        action=AuditLog.ACTION_DELETE,
        resource=tenant,
        details={'reason': 'GDPR request'},
        request=request
    )
"""
from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from landlord.models_audit import AuditLog


def log_audit(
    user,
    action: str,
    resource: Any = None,
    resource_repr: str = None,
    details: dict = None,
    request: HttpRequest = None,
) -> AuditLog:
    """
    Create an audit log entry.
    
    Args:
        user: Django User instance (can be None for system actions)
        action: Action type (use AuditLog.ACTION_* constants)
        resource: Django model instance being acted upon (optional)
        resource_repr: String representation (auto-generated if not provided)
        details: Additional context as dict (optional)
        request: HttpRequest for IP/user-agent capture (optional)
    
    Returns:
        Created AuditLog instance
    
    Example:
        >>> log_audit(
        ...     user=request.user,
        ...     action=AuditLog.ACTION_GDPR_ERASE,
        ...     resource=tenant,
        ...     details={'reason': 'User request', 'ticket': 'GDPR-123'},
        ...     request=request
        ... )
    """
    # Prepare data
    data = {
        'user': user,
        'user_email': user.email if user else 'system@localhost',
        'action': action,
        'details': details or {},
    }
    
    # Resource info (GenericForeignKey)
    if resource is not None:
        data['content_type'] = ContentType.objects.get_for_model(resource)
        data['object_id'] = resource.pk
        data['resource_repr'] = resource_repr or str(resource)
    else:
        data['resource_repr'] = resource_repr or 'N/A'
    
    # Request context
    if request is not None:
        # Get client IP (handle proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            data['ip_address'] = x_forwarded_for.split(',')[0].strip()
        else:
            data['ip_address'] = request.META.get('REMOTE_ADDR')
        
        data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:1000]
        
        # Request ID (if middleware sets it)
        data['request_id'] = getattr(request, 'id', '')
    
    # Create immutable audit log
    return AuditLog.objects.create(**data)


def log_gdpr_erase(user, tenant, request: HttpRequest = None) -> AuditLog:
    """
    Convenience function for GDPR data erasure.
    
    Args:
        user: User performing the erasure
        tenant: Tenant being erased
        request: HttpRequest (optional)
    
    Returns:
        Created AuditLog instance
    """
    return log_audit(
        user=user,
        action=AuditLog.ACTION_GDPR_ERASE,
        resource=tenant,
        details={
            'tenant_email': tenant.primary_email,
            'unit': str(tenant.unit) if tenant.unit else 'N/A',
        },
        request=request
    )


def log_property_archive(user, property_obj, archived: bool, request: HttpRequest = None) -> AuditLog:
    """
    Convenience function for property archive/unarchive.
    
    Args:
        user: User performing the action
        property_obj: Property being archived/unarchived
        archived: True for archive, False for unarchive
        request: HttpRequest (optional)
    
    Returns:
        Created AuditLog instance
    """
    action = AuditLog.ACTION_ARCHIVE if archived else AuditLog.ACTION_UNARCHIVE
    
    return log_audit(
        user=user,
        action=action,
        resource=property_obj,
        details={
            'property_name': property_obj.name,
            'property_address': f"{property_obj.street}, {property_obj.city}",
        },
        request=request
    )


def log_permission_change(user, target_user, changes: dict, request: HttpRequest = None) -> AuditLog:
    """
    Convenience function for user permission changes.
    
    Args:
        user: User performing the change
        target_user: User whose permissions are being changed
        changes: Dict describing the changes (e.g., {'is_staff': True})
        request: HttpRequest (optional)
    
    Returns:
        Created AuditLog instance
    """
    return log_audit(
        user=user,
        action=AuditLog.ACTION_PERMISSION_CHANGE,
        resource=target_user,
        resource_repr=f"User: {target_user.email}",
        details={
            'target_user_email': target_user.email,
            'changes': changes,
        },
        request=request
    )


def log_contract_change(user, contract, change_type: str, details: dict = None, request: HttpRequest = None) -> AuditLog:
    """
    Convenience function for contract changes.
    
    Args:
        user: User performing the change
        contract: Contract being modified
        change_type: 'create', 'update', or 'delete'
        details: Additional details (optional)
        request: HttpRequest (optional)
    
    Returns:
        Created AuditLog instance
    """
    action_map = {
        'create': AuditLog.ACTION_CREATE,
        'update': AuditLog.ACTION_UPDATE,
        'delete': AuditLog.ACTION_DELETE,
    }
    
    return log_audit(
        user=user,
        action=action_map.get(change_type, AuditLog.ACTION_UPDATE),
        resource=contract,
        details={
            'tenant': str(contract.tenant),
            'unit': str(contract.unit),
            'rent_amount': str(contract.rent_amount),
            **(details or {}),
        },
        request=request
    )
