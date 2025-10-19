import re
import uuid

import pytest
from django.test import override_settings
from django.utils import timezone
from landlord.models import IdempotencyKey, Issue


def _csrf(client):
    r = client.get("/chat/")
    return {"HTTP_X_CSRFTOKEN": r.client.cookies.get("csrftoken").value}


@pytest.mark.throttle
@pytest.mark.django_db
@override_settings(REST_FRAMEWORK={
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"chat": "5/min"},
})
def test_global_throttle_429(client, monkeypatch):
    # Ensure burst throttle is active for this test regardless of prior env
    monkeypatch.setenv("CHAT_DISABLE_BURST_THROTTLE", "0")
    # Freeze DRF SimpleRateThrottle.timer to keep within same minute bucket
    import time as _time
    fixed = int(_time.time())
    monkeypatch.setattr("rest_framework.throttling.SimpleRateThrottle.timer", lambda self: fixed, raising=True)
    # Also freeze app-side timezone to a fixed second so burst window is deterministic
    from django.utils import timezone as _tz
    fixed_dt = _tz.now().replace(microsecond=0)
    monkeypatch.setattr("landlord.views.timezone.now", lambda: fixed_dt, raising=True)
    # Stub Redis client used by burst throttle to be deterministic (no fail-open)
    class _FakePipe:
        def __init__(self, store):
            self.store = store
            self._key = None
        def incr(self, key, amount=1):
            self._key = key
            self.store[key] = self.store.get(key, 0) + amount
            return self
        def expire(self, key, seconds):
            # no-op for test
            return self
        def execute(self):
            return [self.store.get(self._key, 0), True]
    class _FakeRedis:
        def __init__(self):
            self.store = {}
        def pipeline(self):
            return _FakePipe(self.store)
        def incr(self, key, amount=1):
            self.store[key] = self.store.get(key, 0) + amount
            return self.store[key]
        def expire(self, key, seconds):
            return True
    monkeypatch.setattr("landlord.views._r", _FakeRedis(), raising=True)
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    v = 0
    # 5 valid steps then 6th throttled
    steps = [
        {"text": "x"},
        {"occurred_at": timezone.now().isoformat()},
        {"location": "Bad"},
        {"severity": 3},
        {},
    ]
    for p in steps:
        r_ok = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, **p}, **csrf)
        assert r_ok.status_code == 200
        v = r_ok.json()["version"]
    statuses = []
    for _ in range(3):  # try a few extra to avoid minute boundary edge
        r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "text": "x"}, **csrf)
        statuses.append(r.status_code)
        if r.status_code == 200:
            v = r.json()["version"]
    assert 429 in statuses, f"expected 429 after exceeding 5/min, got {statuses}"


@pytest.mark.throttle
@pytest.mark.django_db
def test_burst_per_session_429(client, monkeypatch):
    # Ensure burst throttle is active in this test process
    monkeypatch.setenv("CHAT_DISABLE_BURST_THROTTLE", "0")
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    with override_settings(REST_FRAMEWORK={
        "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
        "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
        "DEFAULT_THROTTLE_RATES": {"chat": "100/min"},
    }, CHAT_DISABLE_BURST_THROTTLE=False, CHAT_BURST_LIMIT=5):
        from django.utils import timezone as tz
        fixed = tz.now().replace(microsecond=0)
        # lock time so all posts fall into the same 1s bucket for burst
        monkeypatch.setattr("landlord.views.timezone.now", lambda: fixed, raising=True)
        # Stub Redis client to ensure increments happen deterministically
        class _FakePipe:
            def __init__(self, store):
                self.store = store
                self._key = None
            def incr(self, key, amount=1):
                self._key = key
                self.store[key] = self.store.get(key, 0) + amount
                return self
            def expire(self, key, seconds):
                return self
            def execute(self):
                return [self.store.get(self._key, 0), True]
        class _FakeRedis:
            def __init__(self):
                self.store = {}
            def pipeline(self):
                return _FakePipe(self.store)
            def incr(self, key, amount=1):
                self.store[key] = self.store.get(key, 0) + amount
                return self.store[key]
            def expire(self, key, seconds):
                return True
        monkeypatch.setattr("landlord.views._r", _FakeRedis(), raising=True)
        v = 0
        statuses = []
        # Send 5 valid, state-consistent messages quickly within 1s
        steps = [
            {"text": "x"},
            {"occurred_at": fixed.isoformat()},
            {"location": "Bad"},
            {"severity": 3},
            {},
        ]
        for p in steps:
            r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, **p}, **csrf)
            statuses.append(r.status_code)
            assert r.status_code == 200
            v = r.json()["version"]
        # Sixth request in the same second should be throttled by burst
        r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "contact": "+49 111 222"}, **csrf)
        statuses.append(r.status_code)
        assert 429 in statuses, f"expected 429 from burst throttle, got {statuses}"


@pytest.mark.django_db
@override_settings(CHAT_BURST_LIMIT=999, REST_FRAMEWORK={
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"chat": "1000/min"},
})
def test_state_version_conflict_409(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    r1 = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Strom weg"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"})
    assert r1.status_code == 200
    r2 = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Strom weg"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"})
    assert r2.status_code == 409 and r2.json()["code"] == "STATE_VERSION_CONFLICT"


@pytest.mark.django_db
@override_settings(CHAT_BURST_LIMIT=999, REST_FRAMEWORK={
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"chat": "1000/min"},
})
def test_state_mismatch_409(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    # first message advances to CAPTURE_OCCURRED_AT
    r1 = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Heizung defekt"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"})
    assert r1.status_code == 200
    # send wrong field for next state (severity instead of occurred_at)
    r2 = client.post(f"/api/chat/sessions/{sid}/message", {"version": r1.json()["version"], "severity": 3}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"})
    assert r2.status_code == 409
    body = r2.json()
    assert body["code"] == "STATE_MISMATCH" and body["expected"] in {"CAPTURE_OCCURRED_AT", "CAPTURE_LOCATION"}


@pytest.mark.django_db
@override_settings(CHAT_BURST_LIMIT=999, REST_FRAMEWORK={
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"chat": "1000/min"},
})
def test_idempotency_confirm_same_issue(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    # Happy path minimal to reach confirm quickly
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Wasser"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "occurred_at": timezone.now().isoformat()}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "location": "Bad"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "severity": 2}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    _ = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "contact": "+49 111 222"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"})

    key = str(uuid.uuid4())
    r1 = client.post(f"/api/chat/sessions/{sid}/confirm", **{**csrf, "HTTP_IDEMPOTENCY_KEY": key})
    r2 = client.post(f"/api/chat/sessions/{sid}/confirm", **{**csrf, "HTTP_IDEMPOTENCY_KEY": key})
    assert r1.status_code == r2.status_code == 200
    j1, j2 = r1.json(), r2.json()
    assert j1["issue_id"] == j2["issue_id"] and re.match(r"^TCK-\d{4}-\d{5}$", j1["ticket_no"]) is not None
    # Exactly one Issue and one IdempotencyKey with issue set
    assert Issue.objects.count() == 1
    idem = IdempotencyKey.objects.get(scope="chat_confirm")
    assert idem.issue_id == j1["issue_id"]


@pytest.mark.django_db
@override_settings(CHAT_BURST_LIMIT=999, REST_FRAMEWORK={
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"chat": "1000/min"},
})
def test_happy_path_ticket_and_payload(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Wasserleck in Küche"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "occurred_at": timezone.now().isoformat()}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "location": "Küche"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "severity": 4}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"}).json()["version"]
    _ = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "contact": "user@example.com"}, **{**csrf, "HTTP_X_NO_THROTTLE": "1"})
    r = client.post(f"/api/chat/sessions/{sid}/confirm", **csrf)
    assert r.status_code == 200
    body = r.json()
    assert re.match(r"^TCK-\d{4}-\d{5}$", body["ticket_no"]) is not None
    issue = Issue.objects.get(id=body["issue_id"])
    ds = issue.description_struct
    assert "occurred_at" in ds and ds.get("location_hint") == "Küche" and ds.get("severity") in {4, 5}
