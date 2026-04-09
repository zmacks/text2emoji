"""Unit tests for the prompt composer (pure synchronous functions)."""

from app.prompts.composer import compose_system_prompt


def test_returns_a_string():
    result = compose_system_prompt("Abbie", ["playful", "curious"])
    assert isinstance(result, str)
    assert len(result) > 0


def test_alias_present_in_output():
    result = compose_system_prompt("Abbie", ["playful"])
    assert "Abbie" in result


def test_single_trait_description():
    result = compose_system_prompt("Mal", ["witty"])
    assert "witty" in result


def test_two_trait_description():
    result = compose_system_prompt("Abbie", ["playful", "curious"])
    assert "playful" in result
    assert "curious" in result


def test_many_traits_description():
    result = compose_system_prompt("Abbie", ["playful", "curious", "honest", "sincere"])
    assert "Abbie" in result


def test_empty_traits_fallback():
    result = compose_system_prompt("Abbie", [])
    assert "Abbie" in result
    assert isinstance(result, str)


def test_playful_mode_note():
    result = compose_system_prompt("Abbie", ["playful"], personality_mode="playful")
    assert "playful" in result.lower()


def test_witty_mode_note():
    result = compose_system_prompt("Mal", ["witty"], personality_mode="witty")
    assert "witty" in result.lower()


def test_knowledge_context_injected():
    result = compose_system_prompt(
        "Abbie", ["playful"], knowledge_context="Facts about the ocean"
    )
    assert "Facts about the ocean" in result


def test_empty_knowledge_context_not_injected():
    result = compose_system_prompt("Abbie", ["playful"], knowledge_context="")
    assert "Knowledge you have learned" not in result


def test_whitespace_only_knowledge_context_not_injected():
    result = compose_system_prompt("Abbie", ["playful"], knowledge_context="   ")
    assert "Knowledge you have learned" not in result
