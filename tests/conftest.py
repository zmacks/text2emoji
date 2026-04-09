"""Shared pytest fixtures for the PixlPal test suite.

Strategy
--------
httpx's ASGITransport sends only HTTP-scope ASGI events — it never dispatches
the lifespan startup/shutdown events that populate app.state.  Rather than
fighting that, we skip the lifespan entirely and wire state onto the app
instance directly before the client opens.  This is simpler, faster, and
doesn't require patching module-level imports.

  app.state.db     ← our in-memory aiosqlite connection (fully migrated)
  app.state.gemini ← MagicMock; generate() is an AsyncMock so routes that
                     call it don't block or hit the real Gemini API
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import init_db
from app.server import create_app


# ---------------------------------------------------------------------------
# In-memory database — isolated, fully migrated, per-test
# ---------------------------------------------------------------------------

@pytest.fixture
async def db() -> aiosqlite.Connection:
    """Fresh in-memory SQLite DB with schema + seed data applied."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await init_db(conn)
    yield conn
    await conn.close()


# ---------------------------------------------------------------------------
# Gemini mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_gemini() -> MagicMock:
    """Stand-in for GeminiClient; generate() returns tagged XML."""
    gemini = MagicMock()
    gemini.generate = AsyncMock(
        return_value=(
            "<text_response>Hello, friend!</text_response>"
            "<emoji_translation>👋😊</emoji_translation>"
        )
    )
    return gemini


# ---------------------------------------------------------------------------
# HTTP test client — state injected directly, lifespan never invoked
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(db: aiosqlite.Connection, mock_gemini: MagicMock) -> AsyncClient:
    """AsyncClient backed by a fresh app instance with test state injected.

    ASGITransport only dispatches HTTP-scope events, so the lifespan never
    runs.  We set app.state directly to give routes the DB and Gemini client
    they expect.
    """
    _app = create_app()
    _app.state.db = db
    _app.state.gemini = mock_gemini

    async with AsyncClient(
        transport=ASGITransport(app=_app),
        base_url="http://test",
    ) as ac:
        yield ac
