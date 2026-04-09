"""Property-based tests using Hypothesis.

Each test states a universal claim about a function and lets Hypothesis
find counter-examples via random input generation.  Failures are
automatically shrunk to a minimal reproducing case and saved to
.hypothesis/ so they replay on the next run.

Run with:
    make test-property        # this file only, verbose
    make test                 # all tests including these
"""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.core.database import init_db
from app.prompts.composer import compose_system_prompt
from app.services.boundary import (
    _HARMFUL_KEYWORDS,
    _MILD_KEYWORDS,
    check_input,
)
from app.services.chat import _max_tokens_for_count, parse_response
from app.services.tokens import get_active_knowledge


# ---------------------------------------------------------------------------
# parse_response
# ---------------------------------------------------------------------------
# Invariant family: the function always returns two strings, and whenever
# a known XML tag is present the correct region is extracted.

@given(st.text())
def test_parse_response_always_two_strings(raw: str) -> None:
    text, emoji = parse_response(raw)
    assert isinstance(text, str)
    assert isinstance(emoji, str)


@given(
    content=st.text().filter(lambda s: "</text_response>" not in s),
    prefix=st.text().filter(lambda s: "<text_response>" not in s),
)
def test_parse_response_text_tag_extracted(content: str, prefix: str) -> None:
    raw = f"{prefix}<text_response>{content}</text_response>"
    text, _ = parse_response(raw)
    assert text == content.strip()


@given(
    content=st.text().filter(lambda s: "</emoji_translation>" not in s),
    prefix=st.text().filter(lambda s: "<emoji_translation>" not in s),
)
def test_parse_response_emoji_tag_extracted(content: str, prefix: str) -> None:
    raw = f"{prefix}<emoji_translation>{content}</emoji_translation>"
    _, emoji = parse_response(raw)
    assert emoji == content.strip()


@given(st.text().filter(lambda s: "<text_response>" not in s))
def test_parse_response_no_text_tag_falls_back_to_raw(raw: str) -> None:
    text, _ = parse_response(raw)
    assert text == raw.strip()


@given(st.text().filter(lambda s: "<emoji_translation>" not in s))
def test_parse_response_no_emoji_tag_is_empty(raw: str) -> None:
    _, emoji = parse_response(raw)
    assert emoji == ""


# ---------------------------------------------------------------------------
# check_input
# ---------------------------------------------------------------------------
# Invariants: result is always a valid classification; known harmful/mild
# keywords reliably produce the right label when standing alone.

@given(st.text())
def test_check_input_always_valid_classification(text: str) -> None:
    assert check_input(text) in ("safe", "mild", "harmful")


@given(st.sampled_from(sorted(_HARMFUL_KEYWORDS)))
def test_check_input_harmful_keyword_alone_is_harmful(keyword: str) -> None:
    assert check_input(keyword) == "harmful"


@given(st.sampled_from(sorted(_MILD_KEYWORDS)))
def test_check_input_mild_keyword_alone_is_mild(keyword: str) -> None:
    # A mild keyword in isolation should not trigger the harmful branch.
    # (All mild keywords are confirmed to be non-substrings of harmful ones.)
    assert check_input(keyword) == "mild"


@given(
    st.text().filter(
        lambda s: not any(kw in s.lower() for kw in _HARMFUL_KEYWORDS | _MILD_KEYWORDS)
    )
)
def test_check_input_text_with_no_keywords_is_safe(text: str) -> None:
    assert check_input(text) == "safe"


# ---------------------------------------------------------------------------
# _max_tokens_for_count
# ---------------------------------------------------------------------------
# Invariants: output is always in {500, 1000, 2000}; the mapping is
# deterministic and monotonically non-decreasing.

@given(st.integers())
def test_max_tokens_always_valid_value(count: int) -> None:
    assert _max_tokens_for_count(count) in (500, 1000, 2000)


@given(st.integers(max_value=0))
def test_max_tokens_zero_or_below_is_500(count: int) -> None:
    assert _max_tokens_for_count(count) == 500


@given(st.integers(min_value=1, max_value=4))
def test_max_tokens_one_to_four_is_1000(count: int) -> None:
    assert _max_tokens_for_count(count) == 1000


@given(st.integers(min_value=5))
def test_max_tokens_five_or_more_is_2000(count: int) -> None:
    assert _max_tokens_for_count(count) == 2000


@given(st.integers(), st.integers())
def test_max_tokens_monotonic(a: int, b: int) -> None:
    """More tokens should never yield a smaller output budget."""
    assume(a <= b)
    assert _max_tokens_for_count(a) <= _max_tokens_for_count(b)


# ---------------------------------------------------------------------------
# compose_system_prompt
# ---------------------------------------------------------------------------
# Invariants: always returns a non-empty string; the alias always appears
# verbatim; knowledge context is injected when non-empty.

@given(
    alias=st.text(min_size=1, max_size=64).filter(str.strip),
    traits=st.lists(st.text(min_size=1, max_size=32), max_size=6),
    mode=st.sampled_from(["playful", "witty"]),
)
def test_compose_always_non_empty_string(alias: str, traits: list[str], mode: str) -> None:
    result = compose_system_prompt(alias, traits, personality_mode=mode)
    assert isinstance(result, str)
    assert len(result) > 0


@given(alias=st.text(min_size=1, max_size=64).filter(str.strip))
def test_compose_alias_in_output(alias: str) -> None:
    assert alias in compose_system_prompt(alias, ["playful"])


@given(
    alias=st.text(min_size=1, max_size=32).filter(str.strip),
    knowledge=st.text(min_size=1, max_size=200).filter(str.strip),
)
def test_compose_knowledge_context_injected(alias: str, knowledge: str) -> None:
    result = compose_system_prompt(alias, ["playful"], knowledge_context=knowledge)
    assert knowledge.strip() in result


@given(alias=st.text(min_size=1, max_size=32).filter(str.strip))
def test_compose_empty_knowledge_not_injected(alias: str) -> None:
    result = compose_system_prompt(alias, ["playful"], knowledge_context="")
    assert "Knowledge you have learned" not in result


# ---------------------------------------------------------------------------
# get_active_knowledge
# ---------------------------------------------------------------------------
# Invariants: result length never exceeds the budget; inactive tokens never
# contribute to the output.  Each run creates its own in-memory DB so
# Hypothesis examples are fully isolated.

@given(
    contents=st.lists(
        st.one_of(st.none(), st.text(max_size=150)),
        min_size=0,
        max_size=8,
    ),
    budget=st.integers(min_value=1, max_value=500),
)
@settings(max_examples=50)
async def test_get_active_knowledge_never_exceeds_budget(
    contents: list[str | None], budget: int
) -> None:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await init_db(conn)
    try:
        pxl_id = "prop-pal"
        now = datetime.now(timezone.utc)
        await conn.execute(
            "INSERT INTO pixlpals (id, alias, traits, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (pxl_id, "Test", '["playful"]', now, now),
        )
        for i, content in enumerate(contents):
            await conn.execute(
                "INSERT INTO tokens (pixlpal_id, name, knowledge_content, active)"
                " VALUES (?, ?, ?, 1)",
                (pxl_id, f"T{i}", content),
            )
        await conn.commit()

        result = await get_active_knowledge(pxl_id, conn, budget=budget)
        assert len(result) <= budget
    finally:
        await conn.close()


@given(
    contents=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=6),
)
@settings(max_examples=50)
async def test_get_active_knowledge_inactive_tokens_ignored(
    contents: list[str],
) -> None:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await init_db(conn)
    try:
        pxl_id = "prop-pal"
        now = datetime.now(timezone.utc)
        await conn.execute(
            "INSERT INTO pixlpals (id, alias, traits, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (pxl_id, "Test", '["playful"]', now, now),
        )
        for i, content in enumerate(contents):
            await conn.execute(
                "INSERT INTO tokens (pixlpal_id, name, knowledge_content, active)"
                " VALUES (?, ?, ?, 0)",  # active = 0
                (pxl_id, f"T{i}", content),
            )
        await conn.commit()

        result = await get_active_knowledge(pxl_id, conn, budget=2000)
        assert result == ""
    finally:
        await conn.close()
