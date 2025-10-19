from __future__ import annotations

from django.db import transaction

from ..models import Issue
from ..tasks import send_status_changed


def update_status(issue: Issue, new_status: str) -> Issue:
    old = issue.status
    if old == new_status:
        return issue
    with transaction.atomic():
        issue.status = new_status
        issue.save(update_fields=["status", "updated_at"])
    # fire and forget
    try:
        send_status_changed.delay(issue.id, old, new_status)
    except Exception:
        pass
    return issue
