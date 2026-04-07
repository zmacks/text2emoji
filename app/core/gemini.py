"""Async Gemini text generation client.

A single `GeminiClient` instance is created during app startup (via
lifespan) and shared across all requests through `app.state.gemini`.
This avoids the overhead of re-initialising the SDK on every request.

The synchronous `generate_content` SDK call is offloaded to a thread-pool
executor so it never blocks the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Thin async wrapper around the google-genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key or settings.gemini_api_key)
        self.model = model or settings.gemini_model
        logger.info("GeminiClient initialised (model=%s)", self.model)

    # ------------------------------------------------------------------
    # Core async generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        system_instruction: str,
        user_input: str,
        *,
        temperature: float = 0.8,
        top_p: float = 0.95,
        top_k: int = 20,
        max_output_tokens: int = 500,
        stop_sequences: list[str] | None = None,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        seed: int | None = None,
    ) -> str:
        """Generate a response asynchronously.

        The underlying SDK call is synchronous; we run it in the default
        thread-pool executor so it never blocks the event loop.
        """
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            candidate_count=1,
            seed=seed,
            max_output_tokens=max_output_tokens,
            stop_sequences=stop_sequences or [],
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
        )

        contents = types.Content(
            parts=[types.Part.from_text(text=f"<user_input>{user_input}</user_input>")],
            role="user",
        )

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                self._client.models.generate_content,
                model=self.model,
                config=config,
                contents=contents,
            ),
        )

        return response.candidates[0].content.parts[0].text
