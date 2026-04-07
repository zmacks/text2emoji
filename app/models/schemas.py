"""Pydantic request and response models for the PixlPal API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# PixlPal
# ---------------------------------------------------------------------------

class PixlPalCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=64, examples=["Abbie"])
    traits: list[str] = Field(
        default=["playful", "curious"],
        examples=[["playful", "curious", "honest"]],
    )
    personality_mode: Literal["playful", "witty"] = "playful"


class PixlPalUpdate(BaseModel):
    traits: list[str] | None = None
    personality_mode: Literal["playful", "witty"] | None = None


class PixlPalResponse(BaseModel):
    id: str
    alias: str
    traits: list[str]
    personality_mode: Literal["playful", "witty"]
    token_count: int = 0
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, examples=["session-abc123"])
    message: str = Field(..., min_length=1, max_length=2000, examples=["Tell me about your favourite food!"])


class ChatResponse(BaseModel):
    session_id: str
    text_response: str
    emoji_translation: str
    classification: Literal["safe", "mild", "harmful"]
    response_mode: Literal["normal", "bland", "break_character"]


# ---------------------------------------------------------------------------
# Teach
# ---------------------------------------------------------------------------

class TeachRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    instruction: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="An explicit teaching instruction for the PixlPal.",
        examples=["Always greet with a wave emoji"],
    )


class TeachResponse(BaseModel):
    session_id: str
    text_response: str
    emoji_translation: str
    trait_discovered: str | None = None


# ---------------------------------------------------------------------------
# Gift / Knowledge tokens
# ---------------------------------------------------------------------------

class GiftRequest(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Text content (book passage, article, fact) to gift.",
    )
    source_type: Literal["book", "discovery", "mystery", "default"] = "default"
    name: str = Field(..., min_length=1, max_length=128, examples=["The Little Prince"])
    description: str | None = None


class TokenResponse(BaseModel):
    id: int
    token_type: Literal["default", "book", "discovery", "mystery"]
    name: str
    description: str | None
    knowledge_content: str | None
    acquired_at: datetime
    active: bool


class GiftResponse(BaseModel):
    token: TokenResponse
    new_token_count: int
    unlocks: list[str] = Field(
        default_factory=list,
        description="Descriptions of any thresholds crossed by this gift.",
    )


# ---------------------------------------------------------------------------
# Token progress
# ---------------------------------------------------------------------------

class TokenCountResponse(BaseModel):
    count: int
    next_threshold: int | None
    next_unlock: str | None


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class InteractionRecord(BaseModel):
    id: int
    session_id: str
    user_input: str
    text_response: str | None
    emoji_translation: str | None
    classification: Literal["safe", "mild", "harmful"]
    response_mode: Literal["normal", "bland", "break_character"]
    created_at: datetime


class HistoryResponse(BaseModel):
    pixlpal_id: str
    interactions: list[InteractionRecord]
    total: int
