"""Unit tests for chat.parse_response (pure synchronous function)."""

from app.services.chat import parse_response


def test_parses_both_tags():
    raw = "<text_response>Hello!</text_response><emoji_translation>👋</emoji_translation>"
    text, emoji = parse_response(raw)
    assert text == "Hello!"
    assert emoji == "👋"


def test_strips_whitespace_inside_tags():
    raw = "<text_response>  Hello!  </text_response><emoji_translation>  👋  </emoji_translation>"
    text, emoji = parse_response(raw)
    assert text == "Hello!"
    assert emoji == "👋"


def test_multiline_text_response():
    raw = "<text_response>\nLine one\nLine two\n</text_response><emoji_translation>🌟</emoji_translation>"
    text, emoji = parse_response(raw)
    assert "Line one" in text
    assert "Line two" in text
    assert emoji == "🌟"


def test_missing_text_tag_falls_back_to_raw():
    raw = "Just a plain string with no tags."
    text, emoji = parse_response(raw)
    assert text == raw.strip()
    assert emoji == ""


def test_missing_emoji_tag_returns_empty_string():
    raw = "<text_response>Hello!</text_response>"
    text, emoji = parse_response(raw)
    assert text == "Hello!"
    assert emoji == ""


def test_both_tags_missing_returns_raw_and_empty():
    raw = "No XML here at all."
    text, emoji = parse_response(raw)
    assert text == "No XML here at all."
    assert emoji == ""


def test_empty_string_input():
    text, emoji = parse_response("")
    assert text == ""
    assert emoji == ""


def test_emoji_tag_only():
    raw = "<emoji_translation>🎉</emoji_translation>"
    text, emoji = parse_response(raw)
    # No text tag → falls back to full raw string
    assert "<emoji_translation>" in text
    assert emoji == "🎉"
