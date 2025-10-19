"""
Django signals for automatic SLA tracking (M9)
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from landlord.models import Issue


@receiver(pre_save, sender=Issue)
def track_sla_timestamps(sender, instance, **kwargs):
    """Automatically set first_response_at and done_at"""
    if not instance.pk:
        # New issue, skip
        return

    try:
        old = Issue.objects.get(pk=instance.pk)
    except Issue.DoesNotExist:
        return

    # Track first response (when status changes from NEW)
    if old.status == 'NEW' and instance.status != 'NEW' and not instance.first_response_at:
        instance.first_response_at = timezone.now()

    # Track resolution (when status changes to RESOLVED)
    if instance.status in ['RESOLVED', 'DONE'] and old.status not in ['RESOLVED', 'DONE'] and not instance.done_at:
        instance.done_at = timezone.now()
