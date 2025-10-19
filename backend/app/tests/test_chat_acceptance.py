import re
import uuid

import pytest
from django.test import override_settings
from django.utils import timezone
from landlord.models import IdempotencyKey, Issue


def _csrf(client):
    r = client.get("/chat/")
    return {"HTTP_X_CSRFTOKEN": r.client.cookies.get("csrftoken").value}


@pytest.mark.django_db
@pytest.mark.throttle
@override_settings(REST_FRAMEWORK={
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"chat": "5/min"},
})
def test_global_throttle_429(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    v = 0
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
    for _ in range(3):  # allow for minute boundary edge
        r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "text": "x"}, **csrf)
        statuses.append(r.status_code)
        if r.status_code == 200:
            v = r.json()["version"]
    assert 429 in statuses


@pytest.mark.django_db
@pytest.mark.throttle
def test_burst_per_session_429(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    with override_settings(REST_FRAMEWORK={
        "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
        "DEFAULT_THROTTLE_CLASSES": ["landlord.throttles.ChatRateThrottle"],
        "DEFAULT_THROTTLE_RATES": {"chat": "100/min"},
    }, CHAT_DISABLE_BURST_THROTTLE=False, CHAT_BURST_LIMIT=5):
        from unittest.mock import patch

        from django.utils import timezone as tz
        fixed = tz.now().replace(microsecond=0)
        with patch("landlord.views.timezone.now", return_value=fixed):
            v = 0
            statuses = []
            for _ in range(6):
                r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "text": "x"}, **csrf)
                statuses.append(r.status_code)
                if r.status_code == 200:
                    v = r.json()["version"]
        assert 429 in statuses


@pytest.mark.django_db
def test_state_version_conflict_409(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    r1 = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Strom weg"}, **csrf)
    assert r1.status_code == 200
    r2 = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Strom weg"}, **csrf)
    assert r2.status_code == 409 and r2.json().get("code") == "STATE_VERSION_CONFLICT"


@pytest.mark.django_db
def test_state_mismatch_409(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    r1 = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Heizung defekt"}, **csrf)
    assert r1.status_code == 200
    r2 = client.post(f"/api/chat/sessions/{sid}/message", {"version": r1.json()["version"], "severity": 3}, **csrf)
    assert r2.status_code == 409
    body = r2.json()
    assert body["code"] == "STATE_MISMATCH" and body["expected"] in {"CAPTURE_OCCURRED_AT", "CAPTURE_LOCATION"}


@pytest.mark.django_db
def test_idempotency_confirm_same_issue(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Wasser"}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "occurred_at": timezone.now().isoformat()}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "location": "Bad"}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "severity": 2}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v}, **csrf).json()["version"]
    _ = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "contact": "+49 111 222"}, **csrf)
    key = str(uuid.uuid4())
    r1 = client.post(f"/api/chat/sessions/{sid}/confirm", **{**csrf, "HTTP_IDEMPOTENCY_KEY": key})
    r2 = client.post(f"/api/chat/sessions/{sid}/confirm", **{**csrf, "HTTP_IDEMPOTENCY_KEY": key})
    assert r1.status_code == r2.status_code == 200
    j1, j2 = r1.json(), r2.json()
    assert j1["issue_id"] == j2["issue_id"] and re.match(r"^TCK-\d{4}-\d{5}$", j1["ticket_no"]) is not None
    assert Issue.objects.count() == 1
    idem = IdempotencyKey.objects.get(scope="chat_confirm")
    assert idem.issue_id == j1["issue_id"]


@pytest.mark.django_db
def test_happy_path_ticket_and_payload(client):
    csrf = _csrf(client)
    sid = client.post("/api/chat/sessions/", {}, **csrf).json()["id"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Wasserleck in Küche"}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "occurred_at": timezone.now().isoformat()}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "location": "Küche"}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "severity": 4}, **csrf).json()["version"]
    v = client.post(f"/api/chat/sessions/{sid}/message", {"version": v}, **csrf).json()["version"]
    _ = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "contact": "user@example.com"}, **csrf)
    r = client.post(f"/api/chat/sessions/{sid}/confirm", **csrf)
    assert r.status_code == 200
    body = r.json()
    assert re.match(r"^TCK-\d{4}-\d{5}$", body["ticket_no"]) is not None
    issue = Issue.objects.get(id=body["issue_id"])
    ds = issue.description_struct
    assert "occurred_at" in ds and ds.get("location_hint") == "Küche" and ds.get("severity") in {4, 5}
