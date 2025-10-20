"""
Django signals for:
- Automatic SLA tracking (M9)
- UtilityMeter cache invalidation (M17)
"""
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache

from landlord.models import Issue, UtilityMeter


# ============================================================================
# M9: SLA TRACKING
# ============================================================================

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


# ============================================================================
# M17: UTILITY METER CACHE INVALIDATION
# ============================================================================

def _get_meter_cache_key(scope_type: str, scope_id: int, meter_type: str) -> str:
    """Generate cache key for meter lookup (same as in utility_meter_service)"""
    return f"utility_meter:{scope_type}:{scope_id}:{meter_type}"


@receiver(post_save, sender=UtilityMeter)
def invalidate_meter_cache_on_save(sender, instance, **kwargs):
    """
    Invalidate cache when a UtilityMeter is saved.
    
    Cache invalidation strategy (Spec Kap. 5):
    - Invalidate the specific cache key for the changed meter's scope+type
    - This ensures fresh data on next lookup after admin changes
    """
    scope_id = instance.property_id if instance.scope_type == 'property' else instance.unit_id
    cache_key = _get_meter_cache_key(instance.scope_type, scope_id, instance.meter_type)
    cache.delete(cache_key)


@receiver(post_delete, sender=UtilityMeter)
def invalidate_meter_cache_on_delete(sender, instance, **kwargs):
    """Invalidate cache when a UtilityMeter is deleted."""
    scope_id = instance.property_id if instance.scope_type == 'property' else instance.unit_id
    cache_key = _get_meter_cache_key(instance.scope_type, scope_id, instance.meter_type)
    cache.delete(cache_key)
