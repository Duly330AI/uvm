"""
Phase 3.2 - Chat View Helpers (2025-10-23):
Extract complex logic from ChatMessageView to reduce CC 40 → <15

Helpers for:
- Session validation
- State mismatch detection
- Error response building
- Message payload preparation
"""
from __future__ import annotations

from typing import Any

from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response


def check_session_expired(session) -> Response | None:
    """
    Check if chat session has expired.
    
    Returns:
        Response with 410 if expired, None otherwise
    """
    from django.utils import timezone
    
    if session.expires_at and session.expires_at < timezone.now():
        return Response({"code": "SESSION_EXPIRED"}, status=status.HTTP_410_GONE)
    
    return None


def check_version_conflict(session, request_version: int | None) -> Response | None:
    """
    Early version conflict detection (CAS - Compare-And-Swap).
    
    Args:
        session: ChatSession instance
        request_version: Version number from client request
        
    Returns:
        Response with 409 if conflict, None otherwise
    """
    if request_version is not None and request_version != int(session.version):
        return Response(
            {"code": "STATE_VERSION_CONFLICT"},
            status=status.HTTP_409_CONFLICT
        )
    
    return None


def check_state_mismatch_early(session, data: dict) -> Response | None:
    """
    Early state mismatch detection before serializer.
    
    Prevents 400 validation errors when client sends fields from wrong step.
    
    Args:
        session: ChatSession instance
        data: Request data dict
        
    Returns:
        Response with 409 if mismatch, None otherwise
    """
    st = session.state
    
    if st == "CAPTURE_OCCURRED_AT":
        if "occurred_at" not in data and any(
            k in data for k in ("text", "severity", "location", "contact")
        ):
            return Response(
                {"code": "STATE_MISMATCH", "expected": "CAPTURE_OCCURRED_AT"},
                status=status.HTTP_409_CONFLICT
            )
    
    if st == "CAPTURE_LOCATION":
        if "location" not in data and any(
            k in data for k in ("text", "severity", "occurred_at", "contact")
        ):
            return Response(
                {"code": "STATE_MISMATCH", "expected": "CAPTURE_LOCATION"},
                status=status.HTTP_409_CONFLICT
            )
    
    return None


def check_state_mismatch_validated(session, validated_data: dict, raw_data: dict) -> Response | None:
    """
    State mismatch check after serializer validation.
    
    More thorough check with validated + raw data.
    
    Args:
        session: ChatSession instance
        validated_data: Serializer validated_data
        raw_data: Original request data
        
    Returns:
        Response with 409 if mismatch, None otherwise
    """
    st = session.state
    vd = validated_data
    raw_keys = set(raw_data.keys())
    
    def any_other_fields(keys):
        return any(k in vd for k in keys)
    
    if st == "CAPTURE_OCCURRED_AT":
        if "occurred_at" not in vd and (
            any_other_fields(["severity", "location", "contact", "text"]) 
            or ("text" in raw_keys)
        ):
            return Response(
                {"code": "STATE_MISMATCH", "expected": "CAPTURE_OCCURRED_AT"},
                status=status.HTTP_409_CONFLICT
            )
    
    if st == "CAPTURE_LOCATION":
        if "location" not in vd and (
            any_other_fields(["severity", "occurred_at", "contact", "text"]) 
            or ("text" in raw_keys)
        ):
            return Response(
                {"code": "STATE_MISMATCH", "expected": "CAPTURE_LOCATION"},
                status=status.HTTP_409_CONFLICT
            )
    
    return None


def prepare_message_payload(session, validated_data: dict, raw_data: dict) -> dict:
    """
    Prepare message payload for FSM service.
    
    Merges validated data with raw text/occurred_at fields that may be omitted.
    
    Args:
        session: ChatSession instance
        validated_data: Serializer validated_data
        raw_data: Original request data
        
    Returns:
        Message payload dict for FSM
    """
    msg_payload = dict(validated_data)
    
    # Ensure 'text' is forwarded if present
    raw_text = (raw_data.get("text") or "").strip()
    if raw_text:
        msg_payload["text"] = raw_text
        # Map text to summary for FSM steps GREETING/CAPTURE_SUMMARY
        if session.state in ("GREETING", "CAPTURE_SUMMARY") and "summary" not in msg_payload:
            msg_payload["summary"] = raw_text
    
    # Parse occurred_at if present in raw data
    if "occurred_at" not in msg_payload and raw_data.get("occurred_at"):
        dt = parse_datetime(raw_data.get("occurred_at"))
        if dt is not None:
            msg_payload["occurred_at"] = dt
    
    return msg_payload


def handle_service_error(error: Exception) -> Response:
    """
    Convert service exceptions to appropriate HTTP responses.
    
    Args:
        error: Exception from service layer
        
    Returns:
        Response with appropriate status code
    """
    if isinstance(error, RuntimeError):
        if str(error) == "STATE_VERSION_CONFLICT":
            return Response(
                {"code": "STATE_VERSION_CONFLICT"},
                status=status.HTTP_409_CONFLICT
            )
        return Response({"code": "ERROR"}, status=status.HTTP_400_BAD_REQUEST)
    
    if isinstance(error, ValueError):
        msg = str(error)
        
        # FSM validation errors
        if msg.startswith("VALIDATION:"):
            _, field, detail = msg.split(":", 2)
            return Response(
                {"code": "VALIDATION_ERROR", "field": field, "detail": detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Payload size errors
        if msg.startswith("PAYLOAD_TOO_LARGE"):
            return Response(
                {"code": "PAYLOAD_TOO_LARGE"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        
        # Media type errors
        if msg.startswith("UNSUPPORTED_MEDIA_TYPE"):
            return Response(
                {"code": "UNSUPPORTED_MEDIA_TYPE"},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            )
        
        # Generic state mismatch
        return Response(
            {"code": "STATE_MISMATCH"},
            status=status.HTTP_409_CONFLICT
        )
    
    # Unknown error
    return Response({"code": "ERROR"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
