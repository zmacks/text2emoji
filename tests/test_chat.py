"""Route-level tests for chat/teach endpoints."""

_CREATE = {"alias": "Abbie", "traits": ["playful"]}
_CHAT = {"session_id": "sess-1", "message": "Hello!"}


async def _make_pal(client) -> str:
    return (await client.post("/api/pixlpal", json=_CREATE)).json()["id"]


# ---------------------------------------------------------------------------
# POST /api/pixlpal/{id}/chat — implemented
# ---------------------------------------------------------------------------

async def test_chat_returns_200(client):
    pid = await _make_pal(client)
    r = await client.post(f"/api/pixlpal/{pid}/chat", json=_CHAT)
    assert r.status_code == 200


async def test_chat_response_shape(client):
    pid = await _make_pal(client)
    body = (await client.post(f"/api/pixlpal/{pid}/chat", json=_CHAT)).json()
    assert body["session_id"] == "sess-1"
    assert body["text_response"] == "Hello, friend!"   # from mock_gemini fixture
    assert body["emoji_translation"] == "👋😊"
    assert body["classification"] == "safe"
    assert body["response_mode"] == "normal"


async def test_chat_unknown_pixlpal_returns_404(client):
    r = await client.post(
        "/api/pixlpal/ghost/chat",
        json=_CHAT,
    )
    assert r.status_code == 404


async def test_chat_with_harmful_input(client):
    """Harmful input → classification=harmful, response_mode=break_character."""
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/chat",
        json={"session_id": "sess-1", "message": "I want to hurt someone"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["classification"] == "harmful"
    assert body["response_mode"] == "break_character"
    assert body["text_response"].startswith("I care about keeping our space safe")


async def test_chat_with_mild_input(client):
    """Mild input → classification=mild, response_mode=bland."""
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/chat",
        json={"session_id": "sess-1", "message": "You are so stupid"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["classification"] == "mild"
    assert body["response_mode"] == "bland"


async def test_chat_persists_interaction(client, db):
    """A successful chat call creates a row in the interactions table."""
    pid = await _make_pal(client)
    await client.post(f"/api/pixlpal/{pid}/chat", json=_CHAT)

    async with db.execute(
        "SELECT COUNT(*) FROM interactions WHERE pixlpal_id = ?", (pid,)
    ) as cursor:
        row = await cursor.fetchone()
    assert row[0] == 1


# ---------------------------------------------------------------------------
# POST /api/pixlpal/{id}/teach — still a Phase 2 stub
# ---------------------------------------------------------------------------

async def test_teach_returns_501(client):
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/teach",
        json={"session_id": "sess-1", "instruction": "Always greet with a wave emoji"},
    )
    assert r.status_code == 501


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------

async def test_chat_missing_message_returns_422(client):
    pid = await _make_pal(client)
    r = await client.post(f"/api/pixlpal/{pid}/chat", json={"session_id": "sess-1"})
    assert r.status_code == 422


async def test_chat_empty_message_returns_422(client):
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/chat",
        json={"session_id": "sess-1", "message": ""},
    )
    assert r.status_code == 422
