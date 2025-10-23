"""
Phase 4.2 - Audit Logging (2025-10-23):
Audit trail for GDPR compliance and security monitoring.

Logs critical admin actions:
- Tenant data deletion (GDPR)
- Property archive/unarchive
- Contract changes
- User permission changes
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """
    Audit trail for compliance and security monitoring.
    
    Records critical administrative actions with full context.
    Immutable - never modified or deleted once created.
    """
    
    # Action categories for filtering
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_ARCHIVE = 'archive'
    ACTION_UNARCHIVE = 'unarchive'
    ACTION_GDPR_ERASE = 'gdpr_erase'
    ACTION_EXPORT = 'export'
    ACTION_PERMISSION_CHANGE = 'permission_change'
    
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_ARCHIVE, 'Archive'),
        (ACTION_UNARCHIVE, 'Unarchive'),
        (ACTION_GDPR_ERASE, 'GDPR Data Erasure'),
        (ACTION_EXPORT, 'Data Export'),
        (ACTION_PERMISSION_CHANGE, 'Permission Change'),
    ]
    
    # Who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="User who performed the action"
    )
    user_email = models.EmailField(
        max_length=255,
        help_text="Email stored for reference even if user is deleted"
    )
    
    # What action was performed
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        help_text="Type of action performed"
    )
    
    # What resource was affected (using GenericForeignKey for flexibility)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = GenericForeignKey('content_type', 'object_id')
    
    # Additional context
    resource_repr = models.CharField(
        max_length=255,
        help_text="String representation of resource at time of action"
    )
    
    # Structured details (JSON)
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data about the action"
    )
    
    # When & where
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the action occurred"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string from request"
    )
    
    # Request context
    request_id = models.CharField(
        max_length=36,
        blank=True,
        help_text="Request ID for correlation with application logs"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
    
    def __str__(self):
        return f"{self.timestamp.isoformat()} - {self.user_email} - {self.get_action_display()} - {self.resource_repr}"
    
    def save(self, *args, **kwargs):
        """Override save to make logs immutable after creation."""
        if self.pk is not None:
            raise ValueError("AuditLog entries cannot be modified once created")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of audit logs."""
        raise ValueError("AuditLog entries cannot be deleted")
