"""
Tests for HMAC Signature Utilities
Security Fix (2025-10-23 P1-2): Verify task payload signing.
"""
from __future__ import annotations

import pytest
from landlord.utils.hmac_signatures import sign_payload, verify_payload


class TestHMACSignatures:
    """Test HMAC signature utilities for task security."""

    def test_sign_payload_returns_64_char_hex(self):
        """Signature is 64-character hex string (SHA256 output)."""
        payload = {"file": "/tmp/test.jpg", "user_id": 123}
        sig = sign_payload(payload)

        assert isinstance(sig, str)
        assert len(sig) == 64
        assert all(c in '0123456789abcdef' for c in sig)

    def test_verify_payload_valid_signature(self):
        """Valid signature passes verification."""
        payload = {"file": "/tmp/test.jpg"}
        sig = sign_payload(payload)

        # Should not raise
        assert verify_payload(payload, sig) is True

    def test_verify_payload_invalid_signature_raises(self):
        """Invalid signature raises ValueError."""
        payload = {"file": "/tmp/test.jpg"}

        with pytest.raises(ValueError, match="Invalid signature"):
            verify_payload(payload, "invalid_signature_12345678" * 2)  # 64 chars but wrong

    def test_signature_changes_with_payload(self):
        """Different payloads produce different signatures."""
        payload1 = {"file": "/tmp/file1.jpg"}
        payload2 = {"file": "/tmp/file2.jpg"}

        sig1 = sign_payload(payload1)
        sig2 = sign_payload(payload2)

        assert sig1 != sig2

    def test_signature_deterministic(self):
        """Same payload always produces same signature."""
        payload = {"file": "/tmp/test.jpg", "user_id": 123}

        sig1 = sign_payload(payload)
        sig2 = sign_payload(payload)

        assert sig1 == sig2

    def test_signature_key_order_independent(self):
        """Signature is same regardless of dict key order (canonical JSON)."""
        payload1 = {"file": "/tmp/test.jpg", "user_id": 123}
        payload2 = {"user_id": 123, "file": "/tmp/test.jpg"}  # Different order

        sig1 = sign_payload(payload1)
        sig2 = sign_payload(payload2)

        assert sig1 == sig2

    def test_tampered_payload_fails_verification(self):
        """Tampering with payload after signing fails verification."""
        payload = {"file": "/tmp/test.jpg"}
        sig = sign_payload(payload)

        # Attacker modifies payload
        payload["file"] = "/etc/passwd"  # Path traversal attack!

        with pytest.raises(ValueError, match="Invalid signature"):
            verify_payload(payload, sig)

    def test_signature_uses_secret_key(self, settings):
        """Changing SECRET_KEY changes signature."""
        payload = {"file": "/tmp/test.jpg"}

        # Sign with current key
        sig1 = sign_payload(payload)

        # Change SECRET_KEY
        original_key = settings.SECRET_KEY
        settings.SECRET_KEY = "different_secret_key_12345"

        try:
            sig2 = sign_payload(payload)
            assert sig1 != sig2

            # Old signature won't verify with new key
            with pytest.raises(ValueError):
                verify_payload(payload, sig1)
        finally:
            # Restore original key
            settings.SECRET_KEY = original_key

    def test_real_world_task_payload(self):
        """Test with realistic Celery task payload."""
        task_payload = {
            "issue_id": 42,
            "staged_files": [
                {"name": "/tmp/chat/123/photo.jpg", "mime": "image/jpeg", "size": 2048576},
                {"name": "/tmp/chat/123/video.mp4", "mime": "video/mp4", "size": 5242880},
            ]
        }

        sig = sign_payload(task_payload)
        assert verify_payload(task_payload, sig) is True

        # Attacker tries to inject malicious file
        task_payload["staged_files"].append(
            {"name": "/etc/passwd", "mime": "text/plain", "size": 1024}
        )

        with pytest.raises(ValueError, match="Invalid signature"):
            verify_payload(task_payload, sig)
