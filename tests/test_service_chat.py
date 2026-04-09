"""Unit tests for the chat service layer (DB + mock Gemini, no HTTP)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas import PixlPalCreate
from app.services import chat as chat_svc
from app.services import personality as personality_svc
from app.services import tokens as token_svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gemini(response: str = "<text_response>Hi!</text_response><emoji_translation>👋</emoji_translation>") -> MagicMock:
    gemini = MagicMock()
    gemini.generate = AsyncMock(return_value=response)
    return gemini


async def _make_pal(db, alias: str = "Abbie", traits: list[str] | None = None):
    return await personality_svc.create_pixlpal(
        PixlPalCreate(alias=alias, traits=traits or ["playful"]), db
    )


# ---------------------------------------------------------------------------
# _max_tokens_for_count
# ---------------------------------------------------------------------------

def test_max_tokens_zero_tokens():
    assert chat_svc._max_tokens_for_count(0) == 500


def test_max_tokens_one_token():
    assert chat_svc._max_tokens_for_count(1) == 1000


def test_max_tokens_four_tokens():
    assert chat_svc._max_tokens_for_count(4) == 1000


def test_max_tokens_five_tokens():
    assert chat_svc._max_tokens_for_count(5) == 2000


def test_max_tokens_many_tokens():
    assert chat_svc._max_tokens_for_count(99) == 2000


# ---------------------------------------------------------------------------
# handle_chat — happy path
# ---------------------------------------------------------------------------

async def test_handle_chat_returns_chat_response(db):
    pal = await _make_pal(db)
    result = await chat_svc.handle_chat(
        pixlpal_id=pal.id,
        session_id="s1",
        message="Hello!",
        db=db,
        gemini=_make_gemini(),
    )
    assert result.session_id == "s1"
    assert result.text_response == "Hi!"
    assert result.emoji_translation == "👋"
    assert result.classification == "safe"
    assert result.response_mode == "normal"


async def test_handle_chat_persists_interaction(db):
    pal = await _make_pal(db)
    await chat_svc.handle_chat(
        pixlpal_id=pal.id, session_id="s1", message="Hey", db=db, gemini=_make_gemini()
    )
    async with db.execute(
        "SELECT user_input, classification FROM interactions WHERE pixlpal_id = ?",
        (pal.id,),
    ) as cursor:
        row = await cursor.fetchone()
    assert row["user_input"] == "Hey"
    assert row["classification"] == "safe"


async def test_handle_chat_calls_gemini_once(db):
    pal = await _make_pal(db)
    gemini = _make_gemini()
    await chat_svc.handle_chat(
        pixlpal_id=pal.id, session_id="s1", message="Hi", db=db, gemini=gemini
    )
    gemini.generate.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle_chat — unknown PixlPal
# ---------------------------------------------------------------------------

async def test_handle_chat_raises_lookup_error_for_unknown_pixlpal(db):
    with pytest.raises(LookupError):
        await chat_svc.handle_chat(
            pixlpal_id="no-such-id",
            session_id="s1",
            message="Hello",
            db=db,
            gemini=_make_gemini(),
        )


# ---------------------------------------------------------------------------
# handle_chat — boundary enforcement
# ---------------------------------------------------------------------------

async def test_handle_chat_harmful_input_sets_break_character_mode(db):
    pal = await _make_pal(db)
    result = await chat_svc.handle_chat(
        pixlpal_id=pal.id,
        session_id="s1",
        message="I want to kill someone",
        db=db,
        gemini=_make_gemini(),
    )
    assert result.classification == "harmful"
    assert result.response_mode == "break_character"


async def test_handle_chat_break_character_prepends_canned_message(db):
    pal = await _make_pal(db)
    result = await chat_svc.handle_chat(
        pixlpal_id=pal.id,
        session_id="s1",
        message="I want to hurt someone",
        db=db,
        gemini=_make_gemini(),
    )
    assert result.text_response.startswith("I care about keeping our space safe")


async def test_handle_chat_mild_input_sets_bland_mode(db):
    pal = await _make_pal(db)
    result = await chat_svc.handle_chat(
        pixlpal_id=pal.id,
        session_id="s1",
        message="You are so stupid",
        db=db,
        gemini=_make_gemini(),
    )
    assert result.classification == "mild"
    assert result.response_mode == "bland"


# ---------------------------------------------------------------------------
# handle_chat — generation parameters
# ---------------------------------------------------------------------------

async def test_witty_mode_uses_higher_temperature(db):
    pal = await personality_svc.create_pixlpal(
        PixlPalCreate(alias="Mal", traits=["sassy"], personality_mode="witty"), db
    )
    gemini = _make_gemini()
    await chat_svc.handle_chat(
        pixlpal_id=pal.id, session_id="s1", message="Hi", db=db, gemini=gemini
    )
    _, kwargs = gemini.generate.call_args
    assert kwargs["temperature"] == 1.0


async def test_playful_mode_uses_lower_temperature(db):
    pal = await _make_pal(db, traits=["playful"])
    gemini = _make_gemini()
    await chat_svc.handle_chat(
        pixlpal_id=pal.id, session_id="s1", message="Hi", db=db, gemini=gemini
    )
    _, kwargs = gemini.generate.call_args
    assert kwargs["temperature"] == 0.8


async def test_no_tokens_uses_500_max_output(db):
    pal = await _make_pal(db)
    gemini = _make_gemini()
    await chat_svc.handle_chat(
        pixlpal_id=pal.id, session_id="s1", message="Hi", db=db, gemini=gemini
    )
    _, kwargs = gemini.generate.call_args
    assert kwargs["max_output_tokens"] == 500


async def test_one_token_uses_1000_max_output(db):
    pal = await _make_pal(db)
    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, active) VALUES (?, ?, 1)",
        (pal.id, "Book"),
    )
    await db.commit()

    gemini = _make_gemini()
    await chat_svc.handle_chat(
        pixlpal_id=pal.id, session_id="s1", message="Hi", db=db, gemini=gemini
    )
    _, kwargs = gemini.generate.call_args
    assert kwargs["max_output_tokens"] == 1000


# ---------------------------------------------------------------------------
# handle_chat — knowledge injection
# ---------------------------------------------------------------------------

async def test_knowledge_context_injected_when_tokens_present(db):
    pal = await _make_pal(db)
    await db.execute(
        "INSERT INTO tokens (pixlpal_id, name, knowledge_content, active) VALUES (?, ?, ?, 1)",
        (pal.id, "Ocean Book", "The ocean covers 71% of Earth's surface."),
    )
    await db.commit()

    gemini = _make_gemini()
    await chat_svc.handle_chat(
        pixlpal_id=pal.id, session_id="s1", message="Tell me about water", db=db, gemini=gemini
    )
    _, kwargs = gemini.generate.call_args
    assert "71%" in kwargs["system_instruction"]
