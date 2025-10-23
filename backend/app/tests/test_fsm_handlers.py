"""
Phase 3.3 - Test Coverage (2025-10-23):
Tests for FSM handlers to improve coverage from 76% → 90%+

Tests individual state handlers in isolation.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from landlord.fsm_handlers import (
    _detect_category,
    handle_capture_contact,
    handle_capture_location,
    handle_capture_media,
    handle_capture_occurred_at,
    handle_capture_severity,
    handle_capture_summary,
    handle_confirm,
    handle_create_issue,
    handle_done,
    handle_greeting,
)


class TestCategoryDetection:
    """Test category detection from German keywords."""

    @pytest.mark.parametrize("text,expected", [
        ("Die Heizung funktioniert nicht", "heating"),  # "heizung" → heating
        ("Es ist kalt in der Wohnung", "heating"),
        ("Wasser läuft aus dem Bad", "water"),
        ("Leck in der Leitung", "water"),  # "leck" keyword
        ("Strom ist ausgefallen", "electricity"),
        ("Stromschlag", "electricity"),  # Simple keyword
        ("Wand hat Risse", "structural"),
        ("Decke hat Schimmel", "structural"),
        ("Müll wurde nicht abgeholt", None),  # No category
    ])
    def test_category_detection(self, text, expected):
        result = _detect_category(text)
        if expected:
            assert result == expected
        else:
            assert result is None


class TestGreetingHandler:
    """Test GREETING state handler."""

    def test_greeting_with_text_advances_to_occurred_at(self):
        """Providing text in greeting should skip CAPTURE_SUMMARY."""
        message = {"text": "Die Heizung ist kaputt"}
        next_state, prompt, delta, warnings = handle_greeting(message, {})

        assert next_state == "CAPTURE_OCCURRED_AT"
        assert "summary" in delta
        assert delta["summary"] == "Die Heizung ist kaputt"
        assert warnings == []

    def test_greeting_with_heating_keyword_sets_category(self):
        """Heating keywords should set category."""
        message = {"text": "Heizung defekt"}
        next_state, prompt, delta, warnings = handle_greeting(message, {})

        assert delta.get("category") == "heating"

    def test_greeting_without_text_asks_for_summary(self):
        """No text should advance to CAPTURE_SUMMARY."""
        message = {"text": ""}
        next_state, prompt, delta, warnings = handle_greeting(message, {})

        assert next_state == "CAPTURE_SUMMARY"
        assert delta == {}


class TestCaptureSummaryHandler:
    """Test CAPTURE_SUMMARY state handler."""

    def test_summary_with_occurred_at_skips_ahead(self):
        """Providing occurred_at should skip to CAPTURE_LOCATION."""
        occurred = timezone.now() - timedelta(hours=2)
        message = {"occurred_at": occurred}

        next_state, prompt, delta, warnings = handle_capture_summary(message, {})

        assert next_state == "CAPTURE_LOCATION"
        assert "occurred_at" in delta

    def test_summary_empty_text_raises(self):
        """Empty text should raise validation error."""
        message = {"text": ""}

        with pytest.raises(ValueError, match="VALIDATION:summary:required"):
            handle_capture_summary(message, {})

    def test_summary_with_water_keyword(self):
        """Water keywords should set category."""
        message = {"text": "Wasser läuft aus der Leitung"}

        next_state, prompt, delta, warnings = handle_capture_summary(message, {})

        assert next_state == "CAPTURE_OCCURRED_AT"
        assert delta["summary"] == "Wasser läuft aus der Leitung"
        assert delta.get("category") == "water"


class TestCaptureOccurredAtHandler:
    """Test CAPTURE_OCCURRED_AT state handler."""

    def test_future_date_rejected(self):
        """Future dates should be rejected."""
        tomorrow = timezone.now() + timedelta(days=1)
        message = {"occurred_at": tomorrow}

        with pytest.raises(ValueError, match="VALIDATION:occurred_at:future"):
            handle_capture_occurred_at(message, {})

    def test_past_date_accepted(self):
        """Past dates should be accepted."""
        yesterday = timezone.now() - timedelta(days=1)
        message = {"occurred_at": yesterday}

        next_state, prompt, delta, warnings = handle_capture_occurred_at(message, {})

        assert next_state == "CAPTURE_LOCATION"
        assert "occurred_at" in delta
        assert warnings == []

    def test_missing_occurred_at_raises(self):
        """Missing occurred_at should raise validation error."""
        message = {}

        with pytest.raises(ValueError, match="VALIDATION:occurred_at:required"):
            handle_capture_occurred_at(message, {})


class TestCaptureLocationHandler:
    """Test CAPTURE_LOCATION state handler."""

    def test_location_required(self):
        """Location is required."""
        message = {"location": ""}

        with pytest.raises(ValueError, match="VALIDATION:location:required"):
            handle_capture_location(message, {})

    def test_location_max_length(self):
        """Location should be max 120 chars."""
        message = {"location": "x" * 121}

        with pytest.raises(ValueError, match="VALIDATION:location:maxlen"):
            handle_capture_location(message, {})

    def test_valid_location(self):
        """Valid location should advance to CAPTURE_SEVERITY."""
        message = {"location": "Badezimmer"}

        next_state, prompt, delta, warnings = handle_capture_location(message, {})

        assert next_state == "CAPTURE_SEVERITY"
        assert delta["location_hint"] == "Badezimmer"


class TestCaptureSeverityHandler:
    """Test CAPTURE_SEVERITY state handler."""

    def test_severity_range_validation(self):
        """Severity must be 1-5."""
        with pytest.raises(ValueError, match="VALIDATION:severity:range"):
            handle_capture_severity({"severity": 0}, {})

        with pytest.raises(ValueError, match="VALIDATION:severity:range"):
            handle_capture_severity({"severity": 6}, {})

        with pytest.raises(ValueError, match="VALIDATION:severity:range"):
            handle_capture_severity({"severity": "high"}, {})

    def test_danger_keyword_boosts_severity(self):
        """Danger keywords should boost severity to 5."""
        message = {"severity": 2, "text": "Es riecht nach Gas!"}

        next_state, prompt, delta, warnings = handle_capture_severity(message, {})

        assert delta["severity"] == 5
        assert any("gas" in w.lower() for w in warnings)

    def test_valid_severity(self):
        """Valid severity should advance to CAPTURE_MEDIA."""
        message = {"severity": 3}

        next_state, prompt, delta, warnings = handle_capture_severity(message, {})

        assert next_state == "CAPTURE_MEDIA"
        assert delta["severity"] == 3


class TestCaptureMediaHandler:
    """Test CAPTURE_MEDIA state handler."""

    def test_media_transitions_to_contact(self):
        """CAPTURE_MEDIA should always transition to CAPTURE_CONTACT."""
        next_state, prompt, delta, warnings = handle_capture_media({}, {})

        assert next_state == "CAPTURE_CONTACT"
        assert delta == {}
        assert warnings == []


class TestCaptureContactHandler:
    """Test CAPTURE_CONTACT state handler."""

    def test_contact_optional(self):
        """Contact is optional."""
        next_state, prompt, delta, warnings = handle_capture_contact({}, {})

        assert next_state == "CONFIRM"
        assert delta == {}

    def test_contact_provided(self):
        """Contact should be stored in delta."""
        message = {"contact": "Erreichbar abends ab 18 Uhr"}

        next_state, prompt, delta, warnings = handle_capture_contact(message, {})

        assert next_state == "CONFIRM"
        assert delta["contact_times"] == "Erreichbar abends ab 18 Uhr"


class TestConfirmHandler:
    """Test CONFIRM state handler."""

    def test_confirm_transitions_to_create_issue(self):
        """CONFIRM should transition to CREATE_ISSUE."""
        next_state, prompt, delta, warnings = handle_confirm({}, {})

        assert next_state == "CREATE_ISSUE"
        assert "erstellt" in prompt.lower()


class TestCreateIssueHandler:
    """Test CREATE_ISSUE state handler."""

    def test_create_issue_transitions_to_done(self):
        """CREATE_ISSUE should transition to DONE."""
        next_state, prompt, delta, warnings = handle_create_issue({}, {})

        assert next_state == "DONE"
        assert "dank" in prompt.lower()


class TestDoneHandler:
    """Test DONE state handler."""

    def test_done_stays_done(self):
        """DONE should stay in DONE state."""
        next_state, prompt, delta, warnings = handle_done({}, {})

        assert next_state == "DONE"
        assert "abgeschlossen" in prompt.lower()
