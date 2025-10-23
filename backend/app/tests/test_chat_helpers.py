"""
Phase 3.3 - Test Coverage (2025-10-23):
Tests for Chat View helpers to improve coverage from 63% → 85%+

Tests individual helper functions for ChatMessageView.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from landlord.models import ChatSession, Property, Unit
from landlord.views_chat_helpers import (
    check_session_expired,
    check_state_mismatch_early,
    check_state_mismatch_validated,
    check_version_conflict,
    handle_service_error,
    prepare_message_payload,
)
from rest_framework import status


@pytest.fixture
def chat_session(db):
    """Create a test chat session."""
    prop = Property.objects.create(
        name="Test Property",
        street="Teststraße 1",
        city="Berlin",
        postal_code="10115"
    )
    unit = Unit.objects.create(property=prop, unit_label="A101")
    session = ChatSession.objects.create(
        unit=unit,
        state="GREETING",
        version=1,
        expires_at=timezone.now() + timedelta(hours=1)
    )
    return session


class TestCheckSessionExpired:
    """Test session expiry check."""

    def test_expired_session_returns_410(self, chat_session):
        """Expired session should return 410 GONE."""
        chat_session.expires_at = timezone.now() - timedelta(hours=1)
        chat_session.save()

        response = check_session_expired(chat_session)

        assert response is not None
        assert response.status_code == status.HTTP_410_GONE
        assert response.data["code"] == "SESSION_EXPIRED"

    def test_valid_session_returns_none(self, chat_session):
        """Valid session should return None."""
        response = check_session_expired(chat_session)

        assert response is None

    def test_session_without_expiry_returns_none(self, chat_session):
        """Session without expiry should return None."""
        chat_session.expires_at = None
        chat_session.save()

        response = check_session_expired(chat_session)

        assert response is None


class TestCheckVersionConflict:
    """Test version conflict detection (CAS)."""

    def test_version_mismatch_returns_409(self, chat_session):
        """Version mismatch should return 409 CONFLICT."""
        chat_session.version = 5

        response = check_version_conflict(chat_session, request_version=3)

        assert response is not None
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["code"] == "STATE_VERSION_CONFLICT"

    def test_version_match_returns_none(self, chat_session):
        """Matching version should return None."""
        chat_session.version = 5

        response = check_version_conflict(chat_session, request_version=5)

        assert response is None

    def test_no_request_version_returns_none(self, chat_session):
        """No request version should return None."""
        response = check_version_conflict(chat_session, request_version=None)

        assert response is None


class TestCheckStateMismatchEarly:
    """Test early state mismatch detection."""

    def test_occurred_at_state_with_wrong_field_returns_409(self, chat_session):
        """CAPTURE_OCCURRED_AT with wrong field should return 409."""
        chat_session.state = "CAPTURE_OCCURRED_AT"
        data = {"text": "some text", "severity": 3}

        response = check_state_mismatch_early(chat_session, data)

        assert response is not None
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["code"] == "STATE_MISMATCH"
        assert response.data["expected"] == "CAPTURE_OCCURRED_AT"

    def test_location_state_with_wrong_field_returns_409(self, chat_session):
        """CAPTURE_LOCATION with wrong field should return 409."""
        chat_session.state = "CAPTURE_LOCATION"
        data = {"severity": 3}

        response = check_state_mismatch_early(chat_session, data)

        assert response is not None
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_correct_field_returns_none(self, chat_session):
        """Correct field for state should return None."""
        chat_session.state = "CAPTURE_OCCURRED_AT"
        data = {"occurred_at": "2024-10-20T10:00:00Z"}

        response = check_state_mismatch_early(chat_session, data)

        assert response is None


class TestCheckStateMismatchValidated:
    """Test state mismatch check after validation."""

    def test_occurred_at_state_without_occurred_at_returns_409(self, chat_session):
        """CAPTURE_OCCURRED_AT without occurred_at in validated data should return 409."""
        chat_session.state = "CAPTURE_OCCURRED_AT"
        validated_data = {"text": "some text"}
        raw_data = {"text": "some text"}

        response = check_state_mismatch_validated(chat_session, validated_data, raw_data)

        assert response is not None
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_location_state_without_location_returns_409(self, chat_session):
        """CAPTURE_LOCATION without location should return 409."""
        chat_session.state = "CAPTURE_LOCATION"
        validated_data = {"severity": 3}
        raw_data = {"severity": 3}

        response = check_state_mismatch_validated(chat_session, validated_data, raw_data)

        assert response is not None

    def test_correct_validated_data_returns_none(self, chat_session):
        """Correct validated data should return None."""
        chat_session.state = "CAPTURE_OCCURRED_AT"
        validated_data = {"occurred_at": "2024-10-20T10:00:00Z"}
        raw_data = {"occurred_at": "2024-10-20T10:00:00Z"}

        response = check_state_mismatch_validated(chat_session, validated_data, raw_data)

        assert response is None


class TestPrepareMessagePayload:
    """Test message payload preparation."""

    def test_raw_text_included_in_payload(self, chat_session):
        """Raw text should be included in payload."""
        validated_data = {"version": 1}
        raw_data = {"text": "Heizung kaputt", "version": 1}

        payload = prepare_message_payload(chat_session, validated_data, raw_data)

        assert payload["text"] == "Heizung kaputt"

    def test_text_mapped_to_summary_in_greeting(self, chat_session):
        """Text should be mapped to summary in GREETING state."""
        chat_session.state = "GREETING"
        validated_data = {"version": 1}
        raw_data = {"text": "Heizung kaputt", "version": 1}

        payload = prepare_message_payload(chat_session, validated_data, raw_data)

        assert payload["summary"] == "Heizung kaputt"

    def test_text_mapped_to_summary_in_capture_summary(self, chat_session):
        """Text should be mapped to summary in CAPTURE_SUMMARY state."""
        chat_session.state = "CAPTURE_SUMMARY"
        validated_data = {"version": 1}
        raw_data = {"text": "Wasser läuft", "version": 1}

        payload = prepare_message_payload(chat_session, validated_data, raw_data)

        assert payload["summary"] == "Wasser läuft"

    def test_occurred_at_parsed_from_raw_data(self, chat_session):
        """occurred_at should be parsed from raw data if not in validated."""

        validated_data = {"version": 1}
        raw_data = {"occurred_at": "2024-10-20T10:00:00Z", "version": 1}

        payload = prepare_message_payload(chat_session, validated_data, raw_data)

        assert "occurred_at" in payload
        assert payload["occurred_at"] is not None


class TestHandleServiceError:
    """Test service error handling."""

    def test_runtime_error_state_version_conflict(self):
        """RuntimeError 'STATE_VERSION_CONFLICT' should return 409."""
        error = RuntimeError("STATE_VERSION_CONFLICT")

        response = handle_service_error(error)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["code"] == "STATE_VERSION_CONFLICT"

    def test_runtime_error_generic(self):
        """Generic RuntimeError should return 400."""
        error = RuntimeError("Something went wrong")

        response = handle_service_error(error)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "ERROR"

    def test_validation_error(self):
        """ValueError with VALIDATION: prefix should return 400 with details."""
        error = ValueError("VALIDATION:summary:required")

        response = handle_service_error(error)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "VALIDATION_ERROR"
        assert response.data["field"] == "summary"
        assert response.data["detail"] == "required"

    def test_payload_too_large_error(self):
        """ValueError 'PAYLOAD_TOO_LARGE' should return 413."""
        error = ValueError("PAYLOAD_TOO_LARGE:file")

        response = handle_service_error(error)

        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert response.data["code"] == "PAYLOAD_TOO_LARGE"

    def test_unsupported_media_type_error(self):
        """ValueError 'UNSUPPORTED_MEDIA_TYPE' should return 415."""
        error = ValueError("UNSUPPORTED_MEDIA_TYPE:file")

        response = handle_service_error(error)

        assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        assert response.data["code"] == "UNSUPPORTED_MEDIA_TYPE"

    def test_generic_value_error(self):
        """Generic ValueError should return 409."""
        error = ValueError("Some validation failed")

        response = handle_service_error(error)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["code"] == "STATE_MISMATCH"

    def test_unknown_error_returns_500(self):
        """Unknown exception should return 500."""
        error = Exception("Unexpected error")

        response = handle_service_error(error)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["code"] == "ERROR"
