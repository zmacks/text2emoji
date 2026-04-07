"""PixlPal FastAPI server.

Entry point:
    uv run uvicorn app.server:app --reload

Lifespan:
    - Opens a single aiosqlite connection (WAL mode, FK enforcement, migrations)
    - Creates a single GeminiClient instance shared across all requests
    - Pre-loads prompt fragment cache so the first request isn't slower
    - Tears everything down cleanly on shutdown
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_pixlpal import router as pixlpal_router
from app.api.routes_tokens import router as tokens_router
from app.core.config import settings
from app.core.database import close_db, open_db
from app.core.gemini import GeminiClient
from app.prompts.composer import prime_cache

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: startup + shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage shared resources for the lifetime of the application."""
    logger.info("Starting PixlPal server…")

    # 1. Database
    app.state.db = await open_db()

    # 2. Gemini client (one per process)
    app.state.gemini = GeminiClient()

    # 3. Prompt fragment cache
    prime_cache()

    logger.info("PixlPal server ready.")
    yield

    # Shutdown
    logger.info("Shutting down PixlPal server…")
    await close_db(app.state.db)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="PixlPal API",
        description=(
            "Backend API for the PixlPal companion app.  "
            "Players can interact, teach, and customise their PixlPal companion."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — open for now; tighten in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(pixlpal_router)
    app.include_router(chat_router)
    app.include_router(tokens_router)

    @app.get("/health", tags=["meta"], summary="Health check")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    return app


app = create_app()
