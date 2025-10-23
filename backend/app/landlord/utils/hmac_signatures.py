"""
HMAC Signature Utilities for Celery Task Security

Security Fix (2025-10-23): Prevent task payload tampering.

When dispatching Celery tasks with sensitive data (file paths, user IDs),
a compromised message broker (Redis) could inject malicious payloads.

Solution: Sign task payloads with HMAC-SHA256 using SECRET_KEY.
Task verifies signature before processing.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from django.conf import settings


def sign_payload(payload: dict[str, Any]) -> str:
    """
    Create HMAC signature for task payload.

    Args:
        payload: Dictionary to sign (must be JSON-serializable)

    Returns:
        Hex-encoded HMAC signature (64 chars)

    Example:
        >>> payload = {"file": "/tmp/upload.jpg", "user_id": 123}
        >>> sig = sign_payload(payload)
        >>> len(sig)
        64
    """
    # Canonical JSON (sorted keys for consistent hashing)
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))

    # HMAC-SHA256 with SECRET_KEY
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_payload(payload: dict[str, Any], signature: str) -> bool:
    """
    Verify HMAC signature for task payload.

    Args:
        payload: Dictionary to verify
        signature: Hex-encoded HMAC signature

    Returns:
        True if signature is valid, False otherwise

    Raises:
        ValueError: If signature verification fails (for security logging)

    Example:
        >>> payload = {"file": "/tmp/upload.jpg"}
        >>> sig = sign_payload(payload)
        >>> verify_payload(payload, sig)
        True
        >>> verify_payload(payload, "invalid")
        False
    """
    expected_sig = sign_payload(payload)

    # Constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(signature, expected_sig)

    if not is_valid:
        # Log for security monitoring
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"HMAC verification failed for payload: {payload.keys()}. "
            f"Possible tampering detected!"
        )
        raise ValueError("Invalid signature - task payload may be tampered")

    return True


def sign_task_args(*args, **kwargs) -> tuple[tuple, dict, str]:
    """
    Sign Celery task arguments.

    Convenience function for task.delay(sign_task_args(*args, **kwargs)).

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Tuple of (args, kwargs, signature)

    Example:
        >>> args, kwargs, sig = sign_task_args(file_path="/tmp/file", user_id=123)
        >>> task.delay(*args, **kwargs, signature=sig)
    """
    payload = {
        'args': args,
        'kwargs': kwargs
    }
    signature = sign_payload(payload)

    return args, kwargs, signature


def verify_task_args(signature: str, *args, **kwargs) -> bool:
    """
    Verify Celery task arguments signature.

    Args:
        signature: HMAC signature from task
        *args: Positional arguments
        **kwargs: Keyword arguments (excluding 'signature')

    Returns:
        True if valid

    Raises:
        ValueError: If signature invalid

    Example:
        >>> @shared_task
        >>> def my_task(file_path, user_id, signature):
        >>>     verify_task_args(signature, file_path=file_path, user_id=user_id)
        >>>     # Process task...
    """
    payload = {
        'args': args,
        'kwargs': kwargs
    }
    return verify_payload(payload, signature)
