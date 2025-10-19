import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_chat_create_session(client: APIClient):
    resp = client.post("/api/chat/sessions/", {})
    assert resp.status_code == 201
    data = resp.json()
    assert data["state"] == "GREETING"
    assert "id" in data


@pytest.mark.django_db
def test_chat_flow_confirm_idempotent(client: APIClient):
    # create session
    r = client.post("/api/chat/sessions/", {})
    sid = r.json()["id"]

    # greeting -> summary
    r = client.post(f"/api/chat/sessions/{sid}/message", {"version": 0, "text": "Wasser läuft"})
    assert r.status_code == 200
    v = r.json()["version"]

    # occurred_at
    now = timezone.now().isoformat()
    r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "occurred_at": now})
    assert r.status_code == 200
    v = r.json()["version"]

    # location
    r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "location": "Bad"})
    assert r.status_code == 200
    v = r.json()["version"]

    # severity
    r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "severity": 3})
    assert r.status_code == 200
    v = r.json()["version"]

    # media (skip files)
    r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v})
    assert r.status_code == 200
    v = r.json()["version"]

    # contact
    r = client.post(f"/api/chat/sessions/{sid}/message", {"version": v, "contact": "+49 123 456"})
    assert r.status_code == 200

    # confirm with idempotency
    key = str(uuid.uuid4())
    r1 = client.post(f"/api/chat/sessions/{sid}/confirm", **{"HTTP_IDEMPOTENCY_KEY": key})
    r2 = client.post(f"/api/chat/sessions/{sid}/confirm", **{"HTTP_IDEMPOTENCY_KEY": key})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["issue_id"] == r2.json()["issue_id"]
