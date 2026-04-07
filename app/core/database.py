"""Async SQLite connection management and schema migrations.

A single aiosqlite connection is shared across the application lifetime and
stored in the FastAPI app state.  WAL mode is enabled at startup to handle
concurrent reads safely.

Usage (inside a route / service):
    async with db_conn(request.app) as db:
        await db.execute(...)
"""

from __future__ import annotations

import contextlib
import logging
from typing import AsyncIterator

import aiosqlite

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL — all schema migrations live here (additive-only)
# ---------------------------------------------------------------------------

_MIGRATIONS: list[str] = [
    # ── PixlPal instances ────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS pixlpals (
        id               TEXT PRIMARY KEY,
        alias            TEXT NOT NULL,
        traits           TEXT NOT NULL DEFAULT '[]',
        personality_mode TEXT NOT NULL DEFAULT 'playful',
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # ── Token inventory ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS tokens (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        pixlpal_id        TEXT    NOT NULL REFERENCES pixlpals(id),
        token_type        TEXT    NOT NULL DEFAULT 'default',
        name              TEXT    NOT NULL,
        description       TEXT,
        knowledge_content TEXT,
        acquired_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        active            INTEGER DEFAULT 1
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_tokens_pixlpal
        ON tokens(pixlpal_id, active)
    """,
    # ── Interaction history ──────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS interactions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        pixlpal_id       TEXT NOT NULL REFERENCES pixlpals(id),
        session_id       TEXT NOT NULL,
        user_input       TEXT NOT NULL,
        text_response    TEXT,
        emoji_translation TEXT,
        classification   TEXT DEFAULT 'safe',
        response_mode    TEXT DEFAULT 'normal',
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_interactions_session
        ON interactions(pixlpal_id, session_id)
    """,
    # ── Token thresholds ─────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS token_thresholds (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        token_count  INTEGER NOT NULL,
        unlock_type  TEXT    NOT NULL,
        unlock_value TEXT    NOT NULL,
        description  TEXT
    )
    """,
]

# Seed rows for token_thresholds (inserted once, idempotent via INSERT OR IGNORE)
_THRESHOLD_SEEDS: list[tuple] = [
    (1,  "interaction",    "extended_responses", "PixlPal can give longer responses (up to 1000 tokens)"),
    (3,  "personality_trait", "mood_swings",     "PixlPal can express more varied emotional states"),
    (5,  "interaction",    "max_responses",      "PixlPal responses expand to 2000 tokens"),
    (10, "personality_trait", "personality_switch", "Unlock witty personality mode"),
    (15, "integration",   "discovery_roll",     "After every 5 interactions, roll for a new random trait"),
]


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------

async def init_db(db: aiosqlite.Connection) -> None:
    """Run migrations and seed data.  Called once during app startup."""
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    for statement in _MIGRATIONS:
        await db.execute(statement)

    # Seed thresholds (INSERT OR IGNORE keeps it idempotent)
    for row in _THRESHOLD_SEEDS:
        await db.execute(
            """
            INSERT OR IGNORE INTO token_thresholds
                (token_count, unlock_type, unlock_value, description)
            VALUES (?, ?, ?, ?)
            """,
            row,
        )

    await db.commit()
    logger.info("Database initialised at %s", settings.db_file)


async def open_db() -> aiosqlite.Connection:
    """Open and configure an aiosqlite connection."""
    db = await aiosqlite.connect(str(settings.db_file))
    db.row_factory = aiosqlite.Row
    await init_db(db)
    return db


async def close_db(db: aiosqlite.Connection) -> None:
    """Close the database connection gracefully."""
    await db.close()
    logger.info("Database connection closed.")


# ---------------------------------------------------------------------------
# Dependency helper — use inside routes/services
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def db_conn(app) -> AsyncIterator[aiosqlite.Connection]:
    """Yield the shared connection stored in app.state.db."""
    yield app.state.db
