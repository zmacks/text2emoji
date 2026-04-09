"""Smoke tests for the /health endpoint."""


async def test_health_returns_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200


async def test_health_body(client):
    r = await client.get("/health")
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
