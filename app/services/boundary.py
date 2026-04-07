"""Boundary / content safety service — Phase 2 implementation.

Responsibilities:
- check_input: keyword/pattern classification (safe / mild / harmful)
- get_response_mode: escalation level based on session violation history
- Bland mode: override generation params (temp=0.3, max_tokens=100, neutral)
- Break-character mode: prepend canned boundary message

The MVP uses deterministic keyword patterns.  A ML-based classifier is a
post-MVP upgrade.
"""

from __future__ import annotations

from typing import Literal

import aiosqlite

Classification = Literal["safe", "mild", "harmful"]
ResponseMode = Literal["normal", "bland", "break_character"]


# ---------------------------------------------------------------------------
# Keyword / pattern lists (MVP — extend in Phase 2)
# ---------------------------------------------------------------------------

_HARMFUL_KEYWORDS: frozenset[str] = frozenset(
    {
        "kill", "hurt", "harm", "die", "death", "violence", "abuse",
        "suicide", "self-harm", "weapon", "bomb", "drug",
    }
)

_MILD_KEYWORDS: frozenset[str] = frozenset(
    {
        "stupid", "idiot", "dumb", "hate", "ugly", "loser", "shut up",
    }
)


def check_input(text: str) -> Classification:
    """Classify user input as 'safe', 'mild', or 'harmful'.

    Uses simple lowercased token matching for the MVP.
    """
    lower = text.lower()
    tokens = set(lower.split())

    if tokens & _HARMFUL_KEYWORDS or any(kw in lower for kw in _HARMFUL_KEYWORDS):
        return "harmful"
    if tokens & _MILD_KEYWORDS or any(kw in lower for kw in _MILD_KEYWORDS):
        return "mild"
    return "safe"


async def get_response_mode(
    pixlpal_id: str,
    session_id: str,
    classification: Classification,
    db: aiosqlite.Connection,
) -> ResponseMode:
    """Determine escalation level for this session.

    Escalation logic (Phase 2):
    - 0 violations → normal
    - 1–2 violations → bland
    - 3+ violations → break_character

    Current stub: returns mode based solely on current classification.
    """
    if classification == "harmful":
        return "break_character"
    if classification == "mild":
        return "bland"
    return "normal"


# ---------------------------------------------------------------------------
# Response overrides
# ---------------------------------------------------------------------------

BREAK_CHARACTER_PREFIX = (
    "I care about keeping our space safe and friendly. "
    "Let's steer our conversation in a more positive direction! "
)

BLAND_SYSTEM_SUFFIX = (
    "\n\nIMPORTANT: The user's message was flagged. "
    "Respond very briefly and neutrally. Do not engage with the flagged content."
)
