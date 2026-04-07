"""PixlPal CRUD routes.

Phase 1 endpoints (implemented):
    POST   /api/pixlpal                   → create
    GET    /api/pixlpal/{id}              → get state
    PATCH  /api/pixlpal/{id}/personality  → update traits/mode (stub → 501)
    GET    /api/pixlpal/{id}/history      → recent interaction history (stub → 501)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.core.database import db_conn
from app.models.schemas import (
    HistoryResponse,
    PixlPalCreate,
    PixlPalResponse,
    PixlPalUpdate,
)
from app.services import personality as personality_svc

router = APIRouter(prefix="/api/pixlpal", tags=["pixlpal"])


@router.post(
    "",
    response_model=PixlPalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new PixlPal",
)
async def create_pixlpal(payload: PixlPalCreate, request: Request) -> PixlPalResponse:
    async with db_conn(request.app) as db:
        return await personality_svc.create_pixlpal(payload, db)


@router.get(
    "/{pixlpal_id}",
    response_model=PixlPalResponse,
    summary="Get PixlPal state (traits, token count, personality)",
)
async def get_pixlpal(pixlpal_id: str, request: Request) -> PixlPalResponse:
    async with db_conn(request.app) as db:
        pxl = await personality_svc.get_pixlpal(pixlpal_id, db)
    if pxl is None:
        raise HTTPException(status_code=404, detail="PixlPal not found")
    return pxl


@router.patch(
    "/{pixlpal_id}/personality",
    response_model=PixlPalResponse,
    summary="Update personality traits / mode  [Phase 2]",
)
async def update_personality(
    pixlpal_id: str,
    payload: PixlPalUpdate,
    request: Request,
) -> PixlPalResponse:
    async with db_conn(request.app) as db:
        try:
            return await personality_svc.update_personality(
                pixlpal_id, payload.traits, payload.personality_mode, db
            )
        except NotImplementedError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Personality update is not yet implemented (Phase 2).",
            )


@router.get(
    "/{pixlpal_id}/history",
    response_model=HistoryResponse,
    summary="Recent interaction history  [Phase 2]",
)
async def get_history(pixlpal_id: str, request: Request) -> HistoryResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Interaction history is not yet implemented (Phase 2).",
    )
