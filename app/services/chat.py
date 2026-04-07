"""Chat service — Phase 2 implementation.

Generation path (Phase 2):
    user_input
      → boundary.check_input(text) → classification
      → if harmful: bland/break_character response (short-circuit)
      → tokens.get_active_knowledge(pixlpal_id) → context
      → personality.compose_prompt(pixlpal, tokens_context) → system_instruction
      → gemini.generate(system_instruction, user_input) → raw response
      → parse XML tags → text_response + emoji_translation
      → interactions.save(...)
      → return ChatResponse
"""

from __future__ import annotations

import re

import aiosqlite

from app.core.gemini import GeminiClient
from app.models.schemas import ChatResponse


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


async def handle_chat(
    pixlpal_id: str,
    session_id: str,
    message: str,
    db: aiosqlite.Connection,
    gemini: GeminiClient,
) -> ChatResponse:
    """Full chat generation pipeline.  Implemented in Phase 2."""
    raise NotImplementedError("Chat service is not yet implemented (Phase 2).")
