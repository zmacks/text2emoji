"""Chat service.

Generation pipeline
-------------------
user_input
  → boundary.check_input(text)              → classification
  → boundary.get_response_mode(...)         → response_mode
  → personality_svc.get_pixlpal(id, db)     → pxl  (raises LookupError if missing)
  → token_svc.get_active_knowledge(id, db)  → knowledge_context
  → composer.compose_system_prompt(...)     → system_instruction
    (+ bland/break_character suffix if flagged)
  → gemini.generate(system_instruction, user_input, ...)  → raw
  → parse_response(raw)                     → text_response, emoji_translation
  → _save_interaction(...)
  → return ChatResponse

Token-scaled generation limits (per MVP_PLAN §2.1)
---------------------------------------------------
  0 tokens  → max_output_tokens = 500
  1-4 tokens → 1 000
  5+ tokens  → 2 000

Temperature by personality mode
--------------------------------
  playful → 0.8
  witty   → 1.0
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import aiosqlite

from app.core.gemini import GeminiClient
from app.models.schemas import ChatResponse
from app.prompts.composer import compose_system_prompt
from app.services import personality as personality_svc
from app.services import tokens as token_svc
from app.services.boundary import (
    BLAND_SYSTEM_SUFFIX,
    BREAK_CHARACTER_PREFIX,
    check_input,
    get_response_mode,
)


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def parse_response(raw: str) -> tuple[str, str]:
    """Extract <text_response> and <emoji_translation> from Gemini output.

    Returns (text_response, emoji_translation).  Falls back to the full raw
    string as text_response and an empty string for the emoji part if either
    tag is absent.
    """
    text_match = re.search(
        r"<text_response>(.*?)</text_response>", raw, re.DOTALL
    )
    emoji_match = re.search(
        r"<emoji_translation>(.*?)</emoji_translation>", raw, re.DOTALL
    )
    text = text_match.group(1).strip() if text_match else raw.strip()
    emoji = emoji_match.group(1).strip() if emoji_match else ""
    return text, emoji


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _max_tokens_for_count(token_count: int) -> int:
    """Scale max_output_tokens with the PixlPal's token count."""
    if token_count >= 5:
        return 2000
    if token_count >= 1:
        return 1000
    return 500


async def _save_interaction(
    *,
    pixlpal_id: str,
    session_id: str,
    user_input: str,
    text_response: str,
    emoji_translation: str,
    classification: str,
    response_mode: str,
    db: aiosqlite.Connection,
) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        """
        INSERT INTO interactions
            (pixlpal_id, session_id, user_input, text_response, emoji_translation,
             classification, response_mode, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pixlpal_id, session_id, user_input, text_response,
            emoji_translation, classification, response_mode, now,
        ),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def handle_chat(
    pixlpal_id: str,
    session_id: str,
    message: str,
    db: aiosqlite.Connection,
    gemini: GeminiClient,
) -> ChatResponse:
    """Full chat generation pipeline."""
    # 1. Classify the input
    classification = check_input(message)

    # 2. Determine response mode (escalation level)
    response_mode = await get_response_mode(pixlpal_id, session_id, classification, db)

    # 3. Fetch PixlPal state — raises LookupError for unknown IDs
    pxl = await personality_svc.get_pixlpal(pixlpal_id, db)
    if pxl is None:
        raise LookupError(f"PixlPal '{pixlpal_id}' not found")

    # 4. Gather knowledge context from active tokens
    knowledge_context = await token_svc.get_active_knowledge(pixlpal_id, db)

    # 5. Compose system prompt
    system_instruction = compose_system_prompt(
        alias=pxl.alias,
        traits=pxl.traits,
        personality_mode=pxl.personality_mode,
        knowledge_context=knowledge_context,
    )
    if response_mode in ("bland", "break_character"):
        system_instruction += BLAND_SYSTEM_SUFFIX

    # 6. Generate — scale limits with token count and personality mode
    temperature = 1.0 if pxl.personality_mode == "witty" else 0.8
    max_output_tokens = _max_tokens_for_count(pxl.token_count)

    raw = await gemini.generate(
        system_instruction=system_instruction,
        user_input=message,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    # 7. Parse XML tags out of the raw response
    text_response, emoji_translation = parse_response(raw)

    # 8. Prepend canned message for break_character mode
    if response_mode == "break_character":
        text_response = BREAK_CHARACTER_PREFIX + text_response

    # 9. Persist the interaction
    await _save_interaction(
        pixlpal_id=pixlpal_id,
        session_id=session_id,
        user_input=message,
        text_response=text_response,
        emoji_translation=emoji_translation,
        classification=classification,
        response_mode=response_mode,
        db=db,
    )

    return ChatResponse(
        session_id=session_id,
        text_response=text_response,
        emoji_translation=emoji_translation,
        classification=classification,
        response_mode=response_mode,
    )
