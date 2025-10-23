import pytest
from django.utils import timezone
from landlord.fsm import ChatFSM


def test_fsm_normal_flow():
    fsm = ChatFSM()
    state = "GREETING"
    state, prompt, delta, warnings = fsm.next(state, {}, {})
    assert state == "CAPTURE_SUMMARY"
    state, _, delta, _ = fsm.next(state, {"text": "Heizung defekt"}, {})
    assert state == "CAPTURE_OCCURRED_AT" and (delta.get("category") in {None, "heating", "water", "electricity", "structural"})
    dt = timezone.now()
    state, _, delta, _ = fsm.next(state, {"occurred_at": dt}, {})
    assert state == "CAPTURE_LOCATION"
    state, _, delta, _ = fsm.next(state, {"location": "Küche"}, {})
    assert state == "CAPTURE_SEVERITY"
    state, _, delta, _ = fsm.next(state, {"severity": 3}, {})
    assert state == "CAPTURE_MEDIA"
    state, _, delta, _ = fsm.next(state, {}, {})
    assert state == "CAPTURE_CONTACT"
    state, _, delta, _ = fsm.next(state, {"contact": "+49 111 222"}, {})
    assert state == "CONFIRM"


def test_fsm_occurred_at_future_raises():
    fsm = ChatFSM()
    with pytest.raises(ValueError):
        fsm.next("CAPTURE_OCCURRED_AT", {"occurred_at": timezone.now() + timezone.timedelta(days=1)}, {})


def test_fsm_severity_out_of_range():
    fsm = ChatFSM()
    with pytest.raises(ValueError):
        fsm.next("CAPTURE_SEVERITY", {"severity": 6}, {})


def test_fsm_text_too_long():
    """
    Security Fix (2025-10-23 P2-1): Prevent log flooding with huge messages.
    """
    fsm = ChatFSM()

    # Text over 5000 chars should raise
    huge_text = "A" * 5001

    with pytest.raises(ValueError, match="too_long"):
        fsm.next("CAPTURE_SUMMARY", {"text": huge_text}, {})


def test_fsm_payload_too_large():
    """
    Security Fix (2025-10-23 P2-1): Prevent memory exhaustion with huge payloads.
    """
    fsm = ChatFSM()

    # Build a payload >50KB
    huge_payload = {f"key_{i}": "X" * 1000 for i in range(60)}  # ~60KB

    with pytest.raises(ValueError, match="too_large"):
        fsm.next("CAPTURE_SUMMARY", {"text": "Test"}, huge_payload)


def test_fsm_normal_length_accepted():
    """Verify normal-sized messages are accepted."""
    fsm = ChatFSM()

    # 4999 chars should be OK
    normal_text = "A" * 4999
    state, _, _, _ = fsm.next("CAPTURE_SUMMARY", {"text": normal_text}, {})

    assert state == "CAPTURE_OCCURRED_AT"

