from __future__ import annotations

from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

from django.core.files.storage import default_storage
from django.db import IntegrityError, connection, transaction
from django.db.models import F
from django.utils.dateparse import parse_datetime
from landlord.fsm import ChatFSM
from landlord.models import ChatSession, IdempotencyKey, Issue

ALLOWED_MIME = {"image/jpeg", "image/png", "video/mp4", "application/pdf"}
MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 40 * 1024 * 1024


def _stage_files(session: ChatSession, files) -> Tuple[List[Dict], int]:
    staged: List[Dict] = []
    total = 0
    if not files:
        return staged, total
    tmp_dir = PurePosixPath("tmp") / "chat" / str(session.id)
    for up in files:
        if up.size > MAX_FILE:
            raise ValueError("PAYLOAD_TOO_LARGE:file")
        if up.content_type not in ALLOWED_MIME:
            raise ValueError("UNSUPPORTED_MEDIA_TYPE:file")
        total += up.size
        if total > MAX_TOTAL:
            raise ValueError("PAYLOAD_TOO_LARGE:total")
        name = default_storage.save(str(tmp_dir / up.name), up)
        staged.append({"name": name, "mime": up.content_type, "size": up.size})
    return staged, total


def message(session_id, version: int, state: str, message: Dict, files=None) -> Tuple[str, str, Dict, List[str], int]:
    # optimistic lock on version; first validate state machine
    fsm = ChatFSM()
    new_state, prompt, delta, warnings = fsm.next(state, message, {})
    with transaction.atomic():
        rows = (
            ChatSession.objects
            .filter(id=session_id, version=version)
            .update(state=new_state, payload=F("payload"), version=F("version") + 1)
        )
        if rows == 0:
            raise RuntimeError("STATE_VERSION_CONFLICT")
        session = ChatSession.objects.select_for_update().get(id=session_id)
        # merge payload in python (ensures no lost updates to nested dict)
        payload = dict(session.payload or {})
        payload.update(delta)
        if files:
            staged, _ = _stage_files(session, files)
            payload.setdefault("temp_files", []).extend(staged)
        session.payload = payload
        session.state = new_state
        session.version = F("version")  # already incremented
        session.save(update_fields=["payload", "state"])  # version increment committed by update
    # fetch new version
    session = ChatSession.objects.get(id=session_id)
    return new_state, prompt, delta, warnings, session.version


def confirm(session_id, idempotency_key=None, tenant=None) -> Tuple[int, str]:
    """
    Confirm chat session and create Issue.

    Args:
        session_id: ChatSession UUID
        idempotency_key: Optional key for idempotent operations
        tenant: Tenant object if authenticated, None otherwise
    """
    with transaction.atomic():
        session = (
            ChatSession.objects
            .select_for_update()
            .get(id=session_id)
        )
        if session.issue_id:
            # fetch ticket_no without outer join in locked query
            issue = Issue.objects.only("ticket_no").get(id=session.issue_id)
            return issue.id, issue.ticket_no

        scope = "chat_confirm"
        key = None
        if idempotency_key:
            try:
                with transaction.atomic():
                    key, _created = IdempotencyKey.objects.select_for_update().get_or_create(
                        key=idempotency_key, scope=scope, defaults={"session": session}
                    )
            except IntegrityError:
                with transaction.atomic():
                    key = IdempotencyKey.objects.select_for_update().get(key=idempotency_key, scope=scope)
            if key.issue_id:
                return key.issue_id, key.issue.ticket_no or ""

        # build Issue
        payload = session.payload or {}
        severity = payload.get("severity") or 3
        occurred_at_val: Optional[str] = payload.get("occurred_at")
        occurred_dt = None
        if isinstance(occurred_at_val, str):
            occurred_dt = parse_datetime(occurred_at_val)
        elif occurred_at_val:
            occurred_dt = occurred_at_val

        issue = Issue.objects.create(
            tenant=tenant,  # ✅ Tenant from request context
            unit=session.unit,
            category=payload.get("category") or "other",
            severity=severity,
            status="NEW",
            summary=payload.get("summary") or "",
            description_struct=payload,
            occurred_at=occurred_dt,
            location_hint=payload.get("location_hint") or "",
            created_via="chat",
        )

        # ticket number from sequence
        from django.utils import timezone as _tz
        with connection.cursor() as cur:
            cur.execute("SELECT nextval('issue_ticket_seq')")
            seq = cur.fetchone()[0]
        issue.ticket_no = f"TCK-{_tz.now():%Y}-{seq:05d}"
        issue.save(update_fields=["ticket_no"])

        # Phase 2.3 - Async file processing (2025-10-23):
        # Dispatch file processing to background task instead of blocking HTTP thread
        #
        # Security Fix (2025-10-23 P1-2): HMAC signature to prevent payload tampering
        # If Redis/broker is compromised, attacker can't inject arbitrary file paths
        staged = payload.get("temp_files") or []
        if staged:
            from landlord.tasks import finalize_chat_attachments
            from landlord.utils.hmac_signatures import sign_payload
            
            # Sign the payload to prevent tampering
            task_payload = {
                "issue_id": issue.id,
                "staged_files": staged
            }
            signature = sign_payload(task_payload)
            
            # Fire-and-forget: Don't wait for file processing
            try:
                finalize_chat_attachments.delay(issue.id, staged, signature)
            except Exception as e:
                # If task dispatch fails, log to Sentry and audit
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to dispatch chat attachment task for issue {issue.id}: {e}",
                    exc_info=True,
                    extra={"issue_id": issue.id, "file_count": len(staged)}
                )
                # Files remain in temp storage for manual recovery

        session.issue = issue
        session.state = "DONE"
        session.save(update_fields=["issue", "state"])

        if key is not None:
            key.issue = issue
            key.save(update_fields=["issue"])

        return issue.id, issue.ticket_no
