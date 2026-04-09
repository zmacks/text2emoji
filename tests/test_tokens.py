"""Route-level tests for token endpoints."""

_CREATE = {"alias": "Abbie", "traits": ["playful"]}


async def _make_pal(client) -> str:
    return (await client.post("/api/pixlpal", json=_CREATE)).json()["id"]


# ---------------------------------------------------------------------------
# GET /api/pixlpal/{id}/tokens
# ---------------------------------------------------------------------------

async def test_list_tokens_empty_for_new_pixlpal(client):
    pid = await _make_pal(client)
    r = await client.get(f"/api/pixlpal/{pid}/tokens")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_tokens_unknown_pixlpal_returns_empty(client):
    """No 404 expected — service returns an empty list for unknown IDs."""
    r = await client.get("/api/pixlpal/ghost/tokens")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /api/pixlpal/{id}/tokens/count
# ---------------------------------------------------------------------------

async def test_token_count_is_zero_for_new_pixlpal(client):
    pid = await _make_pal(client)
    r = await client.get(f"/api/pixlpal/{pid}/tokens/count")
    assert r.status_code == 200
    assert r.json()["count"] == 0


async def test_token_count_first_threshold_is_1(client):
    """Seed data: first unlock at 1 token."""
    pid = await _make_pal(client)
    body = (await client.get(f"/api/pixlpal/{pid}/tokens/count")).json()
    assert body["next_threshold"] == 1


async def test_token_count_first_unlock_description(client):
    pid = await _make_pal(client)
    body = (await client.get(f"/api/pixlpal/{pid}/tokens/count")).json()
    assert body["next_unlock"] == "PixlPal can give longer responses (up to 1000 tokens)"


# ---------------------------------------------------------------------------
# POST /api/pixlpal/{id}/gift — Phase 2 stub
# ---------------------------------------------------------------------------

async def test_gift_returns_501(client):
    pid = await _make_pal(client)
    r = await client.post(
        f"/api/pixlpal/{pid}/gift",
        json={"content": "Once upon a time…", "name": "The Little Prince"},
    )
    assert r.status_code == 501
