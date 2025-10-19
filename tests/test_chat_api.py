import time
import uuid

import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_chat_create_session(client):
    # prime CSRF
    r = client.get("/chat/")
    csrftoken = r.client.cookies.get("csrftoken").value
    resp = client.post("/api/chat/sessions/", {}, HTTP_X_CSRFTOKEN=csrftoken)
    assert resp.status_code == 201
    data = resp.json()
    assert data["state"] == "GREETING"
    assert "id" in data


@pytest.mark.django_db
def test_chat_flow_confirm_idempotent(client):
    # create session
    r0 = client.get("/chat/")
    csrftoken = r0.client.cookies.get("csrftoken").value
    r = client.post("/api/chat/sessions/", {}, HTTP_X_CSRFTOKEN=csrftoken)
    sid = r.json()["id"]

    # greeting -> summary
    r = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": 0, "text": "Wasser läuft"},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r.status_code == 200
    v = r.json()["version"]

    # occurred_at
    now = timezone.now().isoformat()
    r = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": v, "occurred_at": now},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r.status_code == 200
    v = r.json()["version"]

    # location
    r = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": v, "location": "Bad"},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r.status_code == 200
    v = r.json()["version"]

    # severity
    r = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": v, "severity": 3},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r.status_code == 200
    v = r.json()["version"]

    # media (skip files)
    r = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": v},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r.status_code == 200
    v = r.json()["version"]

    # contact (sleep to avoid per-session 5/sec burst throttle window)
    time.sleep(2.0)
    r = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": v, "contact": "+49 123 456"},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r.status_code == 200

    # confirm with idempotency
    key = str(uuid.uuid4())
    r1 = client.post(
        f"/api/chat/sessions/{sid}/confirm",
        **{"HTTP_IDEMPOTENCY_KEY": key, "HTTP_X_CSRFTOKEN": csrftoken},
    )
    r2 = client.post(
        f"/api/chat/sessions/{sid}/confirm",
        **{"HTTP_IDEMPOTENCY_KEY": key, "HTTP_X_CSRFTOKEN": csrftoken},
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["issue_id"] == r2.json()["issue_id"]


@pytest.mark.django_db
def test_version_conflict_on_message(client):
    # create session
    r0 = client.get("/chat/")
    csrftoken = r0.client.cookies.get("csrftoken").value
    r = client.post("/api/chat/sessions/", {}, HTTP_X_CSRFTOKEN=csrftoken)
    sid = r.json()["id"]
    # first message using version 0
    r1 = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": 0, "text": "Strom weg"},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r1.status_code == 200
    # replay with old version 0 should be 409
    r2 = client.post(
        f"/api/chat/sessions/{sid}/message",
        {"version": 0, "text": "Strom weg"},
        HTTP_X_CSRFTOKEN=csrftoken,
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "STATE_VERSION_CONFLICT"
