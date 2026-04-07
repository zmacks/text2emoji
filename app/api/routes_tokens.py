"""Token listing and progress routes.

Phase 1 endpoints (implemented):
    GET /api/pixlpal/{id}/tokens        → list active tokens
    GET /api/pixlpal/{id}/tokens/count  → current count + next threshold
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.database import db_conn
from app.models.schemas import TokenCountResponse, TokenResponse
from app.services import tokens as token_svc

router = APIRouter(prefix="/api/pixlpal", tags=["tokens"])


@router.get(
    "/{pixlpal_id}/tokens",
    response_model=list[TokenResponse],
    summary="List active tokens for a PixlPal",
)
async def list_tokens(pixlpal_id: str, request: Request) -> list[TokenResponse]:
    async with db_conn(request.app) as db:
        return await token_svc.list_tokens(pixlpal_id, db)


@router.get(
    "/{pixlpal_id}/tokens/count",
    response_model=TokenCountResponse,
    summary="Current token count + next threshold unlock",
)
async def token_count(pixlpal_id: str, request: Request) -> TokenCountResponse:
    async with db_conn(request.app) as db:
        return await token_svc.get_token_count(pixlpal_id, db)
