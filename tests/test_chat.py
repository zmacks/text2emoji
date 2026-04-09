"""Route-level tests for chat/teach endpoints (all Phase 2 stubs → 501)."""

_CREATE = {"alias": "Abbie", "traits": ["playful"]}


async def _make_pal(client) -> str:
    return (await client.post("/api/pixlpal", json=_CREATE)).json()["id"]


async def test_chat_returns_501(client):
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/chat",
        json={"session_id": "sess-1", "message": "Hello!"},
    )
    assert r.status_code == 501


async def test_teach_returns_501(client):
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/teach",
        json={"session_id": "sess-1", "instruction": "Always greet with a wave emoji"},
    )
    assert r.status_code == 501


async def test_chat_missing_message_returns_422(client):
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/chat",
        json={"session_id": "sess-1"},
    )
    assert r.status_code == 422


async def test_chat_empty_message_returns_422(client):
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/chat",
        json={"session_id": "sess-1", "message": ""},
    )
    assert r.status_code == 422
