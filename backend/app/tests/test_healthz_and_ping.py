from django.test import Client


def test_api_ping():
    client = Client()
    resp = client.get("/api/ping/")
    assert resp.status_code == 200
    assert resp.json() == {"pong": True}

def test_healthz(db, monkeypatch):
    client = Client()

    # Healthz responds 200; db and redis depend on env/availability. Here we only check shape.
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"status", "db", "redis"}
    assert data["status"] == "ok"
