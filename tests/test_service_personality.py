"""Unit tests for the personality service layer (no HTTP, DB only)."""

import pytest

from app.models.schemas import PixlPalCreate
from app.services import personality as svc


async def test_create_persists_alias(db):
    result = await svc.create_pixlpal(PixlPalCreate(alias="Mal", traits=["witty"]), db)
    assert result.alias == "Mal"


async def test_create_persists_traits(db):
    result = await svc.create_pixlpal(
        PixlPalCreate(alias="Mal", traits=["witty", "sassy"]), db
    )
    assert result.traits == ["witty", "sassy"]


async def test_create_assigns_uuid(db):
    result = await svc.create_pixlpal(PixlPalCreate(alias="Abbie"), db)
    assert result.id is not None
    assert len(result.id) == 36  # standard UUID string length


async def test_create_token_count_starts_at_zero(db):
    result = await svc.create_pixlpal(PixlPalCreate(alias="Abbie"), db)
    assert result.token_count == 0


async def test_create_default_personality_mode(db):
    result = await svc.create_pixlpal(PixlPalCreate(alias="Abbie"), db)
    assert result.personality_mode == "playful"


async def test_get_returns_none_for_missing_id(db):
    result = await svc.get_pixlpal("no-such-id", db)
    assert result is None


async def test_get_returns_created_pixlpal(db):
    created = await svc.create_pixlpal(PixlPalCreate(alias="Abbie"), db)
    fetched = await svc.get_pixlpal(created.id, db)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.alias == "Abbie"


async def test_get_token_count_reflects_active_tokens(db):
    created = await svc.create_pixlpal(PixlPalCreate(alias="Abbie"), db)

    # Seed a token directly into the DB
    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, description) VALUES (?, ?, ?)",
        (created.id, "Test Token", "A test token"),
    )
    await db.commit()

    fetched = await svc.get_pixlpal(created.id, db)
    assert fetched.token_count == 1


async def test_get_does_not_count_inactive_tokens(db):
    created = await svc.create_pixlpal(PixlPalCreate(alias="Abbie"), db)

    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, active) VALUES (?, ?, ?)",
        (created.id, "Inactive Token", 0),
    )
    await db.commit()

    fetched = await svc.get_pixlpal(created.id, db)
    assert fetched.token_count == 0


async def test_update_personality_raises_not_implemented(db):
    created = await svc.create_pixlpal(PixlPalCreate(alias="Abbie"), db)
    with pytest.raises(NotImplementedError):
        await svc.update_personality(created.id, ["funny"], None, db)
