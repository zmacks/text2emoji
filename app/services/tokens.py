"""Token service — Phase 2 implementation.

Responsibilities:
- gift_knowledge: summarise content → create token → check thresholds
- get_active_knowledge: concatenate knowledge_content up to budget for prompt injection
- get_progress: count tokens + next threshold lookup
- list_tokens: return active token list for a PixlPal
"""

from __future__ import annotations

import aiosqlite

from app.core.gemini import GeminiClient
from app.models.schemas import GiftRequest, GiftResponse, TokenCountResponse, TokenResponse


async def list_tokens(
    pixlpal_id: str,
    db: aiosqlite.Connection,
) -> list[TokenResponse]:
    """Return all active tokens for a PixlPal."""
    async with db.execute(
        """
        SELECT id, token_type, name, description, knowledge_content, acquired_at, active
        FROM tokens
        WHERE pixlpal_id = ? AND active = 1
        ORDER BY acquired_at DESC
        """,
        (pixlpal_id,),
    ) as cursor:
        rows = await cursor.fetchall()

    return [
        TokenResponse(
            id=row["id"],
            token_type=row["token_type"],
            name=row["name"],
            description=row["description"],
            knowledge_content=row["knowledge_content"],
            acquired_at=row["acquired_at"],
            active=bool(row["active"]),
        )
        for row in rows
    ]


async def get_token_count(
    pixlpal_id: str,
    db: aiosqlite.Connection,
) -> TokenCountResponse:
    """Return current token count and the next threshold unlock."""
    async with db.execute(
        "SELECT COUNT(*) FROM tokens WHERE pixlpal_id = ? AND active = 1",
        (pixlpal_id,),
    ) as cursor:
        row = await cursor.fetchone()
    count = row[0] if row else 0

    async with db.execute(
        """
        SELECT token_count, description FROM token_thresholds
        WHERE token_count > ?
        ORDER BY token_count ASC
        LIMIT 1
        """,
        (count,),
    ) as cursor:
        threshold_row = await cursor.fetchone()

    return TokenCountResponse(
        count=count,
        next_threshold=threshold_row["token_count"] if threshold_row else None,
        next_unlock=threshold_row["description"] if threshold_row else None,
    )


async def gift_knowledge(
    pixlpal_id: str,
    payload: GiftRequest,
    db: aiosqlite.Connection,
    gemini: GeminiClient,
) -> GiftResponse:
    """Persist a knowledge token and check for threshold unlocks.  Implemented in Phase 2."""
    raise NotImplementedError("Gift knowledge is not yet implemented (Phase 2).")


async def get_active_knowledge(
    pixlpal_id: str,
    db: aiosqlite.Connection,
    budget: int = 2000,
) -> str:
    """Concatenate active token knowledge_content up to ``budget`` characters.

    Tokens are returned newest-first so the most recently gifted knowledge is
    prioritised when the budget is tight.  Returns an empty string when the
    PixlPal has no active tokens with knowledge content.
    """
    async with db.execute(
        """
        SELECT knowledge_content FROM tokens
        WHERE pixlpal_id = ? AND active = 1 AND knowledge_content IS NOT NULL
        ORDER BY acquired_at DESC
        """,
        (pixlpal_id,),
    ) as cursor:
        rows = await cursor.fetchall()

    parts: list[str] = []
    remaining = budget
    for row in rows:
        content: str = row[0] or ""
        if not content:
            continue
        if len(content) >= remaining:
            # Take what fits and stop
            parts.append(content[:remaining])
            break
        parts.append(content)
        remaining -= len(content)

    return "\n\n".join(parts)
