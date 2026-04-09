"""Route-level tests for POST/GET /api/pixlpal and its stubs."""

import pytest

_CREATE = {"alias": "Abbie", "traits": ["playful", "curious"]}


# ---------------------------------------------------------------------------
# POST /api/pixlpal — create
# ---------------------------------------------------------------------------

async def test_create_returns_201(client):
    r = await client.post("/api/pixlpal", json=_CREATE)
    assert r.status_code == 201


async def test_create_response_shape(client):
    r = await client.post("/api/pixlpal", json=_CREATE)
    body = r.json()
    assert body["alias"] == "Abbie"
    assert body["traits"] == ["playful", "curious"]
    assert body["personality_mode"] == "playful"
    assert body["token_count"] == 0
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_default_traits(client):
    """Traits field is optional; defaults to ["playful", "curious"]."""
    r = await client.post("/api/pixlpal", json={"alias": "Mal"})
    assert r.status_code == 201
    assert r.json()["traits"] == ["playful", "curious"]


async def test_create_witty_mode(client):
    r = await client.post(
        "/api/pixlpal",
        json={"alias": "Mal", "traits": ["sassy"], "personality_mode": "witty"},
    )
    assert r.status_code == 201
    assert r.json()["personality_mode"] == "witty"


async def test_create_missing_alias_returns_422(client):
    r = await client.post("/api/pixlpal", json={"traits": ["playful"]})
    assert r.status_code == 422


async def test_create_empty_alias_returns_422(client):
    r = await client.post("/api/pixlpal", json={"alias": ""})
    assert r.status_code == 422


async def test_create_invalid_personality_mode_returns_422(client):
    r = await client.post(
        "/api/pixlpal", json={"alias": "X", "personality_mode": "chaotic"}
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/pixlpal/{id}
# ---------------------------------------------------------------------------

async def test_get_returns_200(client):
    pixlpal_id = (await client.post("/api/pixlpal", json=_CREATE)).json()["id"]
    r = await client.get(f"/api/pixlpal/{pixlpal_id}")
    assert r.status_code == 200


async def test_get_returns_correct_pixlpal(client):
    created = (await client.post("/api/pixlpal", json=_CREATE)).json()
    fetched = (await client.get(f"/api/pixlpal/{created['id']}")).json()
    assert fetched["id"] == created["id"]
    assert fetched["alias"] == "Abbie"


async def test_get_unknown_id_returns_404(client):
    r = await client.get("/api/pixlpal/no-such-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Phase 2 stubs
# ---------------------------------------------------------------------------

async def test_update_personality_returns_501(client):
    pixlpal_id = (await client.post("/api/pixlpal", json=_CREATE)).json()["id"]
    r = await client.patch(
        f"/api/pixlpal/{pixlpal_id}/personality",
        json={"traits": ["funny"]},
    )
    assert r.status_code == 501


async def test_get_history_returns_501(client):
    pixlpal_id = (await client.post("/api/pixlpal", json=_CREATE)).json()["id"]
    r = await client.get(f"/api/pixlpal/{pixlpal_id}/history")
    assert r.status_code == 501
