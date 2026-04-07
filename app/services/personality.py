"""Personality service — Phase 2 implementation.

Responsibilities:
- CRUD on traits list (stored as JSON in SQLite)
- Auto-regenerate description when traits change
- Personality mode toggle (playful ↔ witty) — unlocked by token threshold
- Trait discovery: after every N interactions, roll for a new random trait
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Literal

import aiosqlite

from app.models.schemas import PixlPalCreate, PixlPalResponse


async def create_pixlpal(
    payload: PixlPalCreate,
    db: aiosqlite.Connection,
) -> PixlPalResponse:
    """Persist a new PixlPal and return its full representation."""
    pixlpal_id = str(uuid.uuid4())
    traits_json = json.dumps(payload.traits)
    now = datetime.now(timezone.utc)

    await db.execute(
        """
        INSERT INTO pixlpals (id, alias, traits, personality_mode, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (pixlpal_id, payload.alias, traits_json, payload.personality_mode, now, now),
    )
    await db.commit()

    return PixlPalResponse(
        id=pixlpal_id,
        alias=payload.alias,
        traits=payload.traits,
        personality_mode=payload.personality_mode,
        token_count=0,
        created_at=now,
        updated_at=now,
    )


async def get_pixlpal(
    pixlpal_id: str,
    db: aiosqlite.Connection,
) -> PixlPalResponse | None:
    """Fetch a PixlPal by ID.  Returns None if not found."""
    async with db.execute(
        "SELECT id, alias, traits, personality_mode, created_at, updated_at FROM pixlpals WHERE id = ?",
        (pixlpal_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        return None

    # Count active tokens
    async with db.execute(
        "SELECT COUNT(*) FROM tokens WHERE pixlpal_id = ? AND active = 1",
        (pixlpal_id,),
    ) as cursor:
        count_row = await cursor.fetchone()

    token_count = count_row[0] if count_row else 0

    return PixlPalResponse(
        id=row["id"],
        alias=row["alias"],
        traits=json.loads(row["traits"]),
        personality_mode=row["personality_mode"],
        token_count=token_count,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def update_personality(
    pixlpal_id: str,
    traits: list[str] | None,
    personality_mode: Literal["playful", "witty"] | None,
    db: aiosqlite.Connection,
) -> PixlPalResponse | None:
    """Patch traits and/or personality_mode.  Implemented in Phase 2."""
    raise NotImplementedError("Personality update is not yet implemented (Phase 2).")
