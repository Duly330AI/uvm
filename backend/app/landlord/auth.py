"""
Tenant authentication decorators and utilities
"""
from functools import wraps

from django.shortcuts import redirect
from django.urls import reverse


def tenant_login_required(view_func):
    """
    Decorator for views that require tenant authentication.
    Checks if tenant_id exists in session.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('tenant_id'):
            # Redirect to tenant login page
            return redirect(reverse('tenant_login'))
        return view_func(request, *args, **kwargs)
    return wrapper


def get_tenant_from_session(request):
    """
    Get Tenant object from session, or None if not authenticated.
    """
    tenant_id = request.session.get('tenant_id')
    if not tenant_id:
        return None

    from landlord.models import Tenant
    try:
        return Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        # Session is stale, clear it
        request.session.pop('tenant_id', None)
        return None
