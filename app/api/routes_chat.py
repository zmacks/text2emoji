"""Chat and teach routes.

Phase 1 endpoints (stub → 501):
    POST /api/pixlpal/{id}/chat    → send message, get text + emoji response
    POST /api/pixlpal/{id}/teach   → teaching interaction
    POST /api/pixlpal/{id}/gift    → gift knowledge item, earn tokens
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.core.database import db_conn
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    GiftRequest,
    GiftResponse,
    TeachRequest,
    TeachResponse,
)
from app.services import chat as chat_svc
from app.services import tokens as token_svc

router = APIRouter(prefix="/api/pixlpal", tags=["chat"])


@router.post(
    "/{pixlpal_id}/chat",
    response_model=ChatResponse,
    summary="Send a message, receive text + emoji response",
)
async def chat(
    pixlpal_id: str,
    payload: ChatRequest,
    request: Request,
) -> ChatResponse:
    async with db_conn(request.app) as db:
        try:
            return await chat_svc.handle_chat(
                pixlpal_id=pixlpal_id,
                session_id=payload.session_id,
                message=payload.message,
                db=db,
                gemini=request.app.state.gemini,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            )
        except NotImplementedError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Chat service is not yet implemented.",
            )


@router.post(
    "/{pixlpal_id}/teach",
    response_model=TeachResponse,
    summary="Teaching interaction  [Phase 2]",
)
async def teach(
    pixlpal_id: str,
    payload: TeachRequest,
    request: Request,
) -> TeachResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Teach endpoint is not yet implemented (Phase 2).",
    )


@router.post(
    "/{pixlpal_id}/gift",
    response_model=GiftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gift a knowledge item (book/data), earn tokens  [Phase 2]",
)
async def gift(
    pixlpal_id: str,
    payload: GiftRequest,
    request: Request,
) -> GiftResponse:
    async with db_conn(request.app) as db:
        try:
            return await token_svc.gift_knowledge(
                pixlpal_id=pixlpal_id,
                payload=payload,
                db=db,
                gemini=request.app.state.gemini,
            )
        except NotImplementedError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Gift endpoint is not yet implemented (Phase 2).",
            )
