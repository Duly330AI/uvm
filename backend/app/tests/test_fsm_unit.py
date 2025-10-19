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
