"""Unit tests for the token service layer (no HTTP, DB only)."""

import pytest

from app.models.schemas import PixlPalCreate
from app.services import personality as personality_svc
from app.services import tokens as token_svc


async def _make_pal(db, alias: str = "Abbie"):
    return await personality_svc.create_pixlpal(
        PixlPalCreate(alias=alias, traits=["playful"]), db
    )


# ---------------------------------------------------------------------------
# list_tokens
# ---------------------------------------------------------------------------

async def test_list_tokens_empty_initially(db):
    pal = await _make_pal(db)
    assert await token_svc.list_tokens(pal.id, db) == []


async def test_list_tokens_returns_active_only(db):
    pal = await _make_pal(db)

    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, active) VALUES (?, ?, ?)",
        (pal.id, "Active", 1),
    )
    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, active) VALUES (?, ?, ?)",
        (pal.id, "Inactive", 0),
    )
    await db.commit()

    tokens = await token_svc.list_tokens(pal.id, db)
    assert len(tokens) == 1
    assert tokens[0].name == "Active"


# ---------------------------------------------------------------------------
# get_token_count
# ---------------------------------------------------------------------------

async def test_token_count_is_zero_initially(db):
    pal = await _make_pal(db)
    result = await token_svc.get_token_count(pal.id, db)
    assert result.count == 0


async def test_token_count_next_threshold_is_1(db):
    """First seeded threshold is at 1 token."""
    pal = await _make_pal(db)
    result = await token_svc.get_token_count(pal.id, db)
    assert result.next_threshold == 1


async def test_token_count_next_unlock_message(db):
    pal = await _make_pal(db)
    result = await token_svc.get_token_count(pal.id, db)
    assert result.next_unlock == "PixlPal can give longer responses (up to 1000 tokens)"


async def test_token_count_advances_threshold_after_token(db):
    """After 1 token, next threshold should jump to 3."""
    pal = await _make_pal(db)

    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, active) VALUES (?, ?, ?)",
        (pal.id, "Book Token", 1),
    )
    await db.commit()

    result = await token_svc.get_token_count(pal.id, db)
    assert result.count == 1
    assert result.next_threshold == 3


async def test_token_count_no_threshold_after_max(db):
    """Beyond the last threshold (15), next_threshold and next_unlock are None."""
    pal = await _make_pal(db)

    for i in range(15):
        await db.execute(
            "INSERT INTO tokens (pixlpal_id, name, active) VALUES (?, ?, ?)",
            (pal.id, f"Token {i}", 1),
        )
    await db.commit()

    result = await token_svc.get_token_count(pal.id, db)
    assert result.count == 15
    assert result.next_threshold is None
    assert result.next_unlock is None


# ---------------------------------------------------------------------------
# Phase 2 stubs
# ---------------------------------------------------------------------------

async def test_gift_knowledge_raises_not_implemented(db):
    from unittest.mock import MagicMock
    from app.models.schemas import GiftRequest

    pal = await _make_pal(db)
    with pytest.raises(NotImplementedError):
        await token_svc.gift_knowledge(
            pal.id,
            GiftRequest(content="Some text", name="A Book"),
            db,
            MagicMock(),
        )


async def test_get_active_knowledge_empty_with_no_tokens(db):
    pal = await _make_pal(db)
    result = await token_svc.get_active_knowledge(pal.id, db)
    assert result == ""


async def test_get_active_knowledge_returns_content(db):
    pal = await _make_pal(db)
    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, knowledge_content, active) VALUES (?, ?, ?, ?)",
        (pal.id, "Book", "The ocean covers 71% of Earth's surface.", 1),
    )
    await db.commit()

    result = await token_svc.get_active_knowledge(pal.id, db)
    assert "71%" in result


async def test_get_active_knowledge_respects_budget(db):
    pal = await _make_pal(db)
    long_content = "x" * 300
    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, knowledge_content, active) VALUES (?, ?, ?, ?)",
        (pal.id, "Big Book", long_content, 1),
    )
    await db.commit()

    result = await token_svc.get_active_knowledge(pal.id, db, budget=100)
    assert len(result) == 100


async def test_get_active_knowledge_skips_inactive_tokens(db):
    pal = await _make_pal(db)
    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, knowledge_content, active) VALUES (?, ?, ?, ?)",
        (pal.id, "Hidden", "Secret knowledge", 0),
    )
    await db.commit()

    result = await token_svc.get_active_knowledge(pal.id, db)
    assert result == ""
