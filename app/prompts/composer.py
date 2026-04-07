"""Data-driven prompt composer.

Reads fragment files once at startup and caches them.  The public entry
point is `compose_system_prompt`, which accepts a PixlPal data dict so it
stays decoupled from the legacy `PixlPal` class.

Fragment files live in `app/prompts/fragments/` (unchanged from the
original layout).  The template engine uses `string.Template` safe_substitute
so unknown placeholders are left in place rather than raising.
"""

from __future__ import annotations

import logging
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fragment registry — ordered list of (placeholder, filename) pairs
# ---------------------------------------------------------------------------

_FRAGMENTS_DIR = Path(__file__).parent / "fragments"

# Maps placeholder name → fragment filename (relative to _FRAGMENTS_DIR)
_FRAGMENT_MAP: dict[str, str] = {
    "INTRO":      "intro.txt",
    "DIRECTIVE":  "directive.txt",
    "RULES":      "rules.txt",
    "FORMAT":     "format.txt",
    "EXAMPLES":   "examples.txt",
}

# Cache: populated on first call or at startup
_fragment_cache: dict[str, str] = {}


def _load_fragments() -> None:
    """Read all fragment files into the cache.  Idempotent."""
    if _fragment_cache:
        return
    for placeholder, filename in _FRAGMENT_MAP.items():
        path = _FRAGMENTS_DIR / filename
        try:
            _fragment_cache[placeholder] = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Prompt fragment not found: %s — using empty string", path)
            _fragment_cache[placeholder] = ""
    logger.debug("Loaded %d prompt fragments", len(_fragment_cache))


def prime_cache() -> None:
    """Call this at server startup to pre-load all fragments."""
    _load_fragments()


# ---------------------------------------------------------------------------
# Public composer
# ---------------------------------------------------------------------------

def _build_objective(alias: str, description: str) -> str:
    """Render the objective fragment with PixlPal-specific values."""
    try:
        raw = (_FRAGMENTS_DIR / "objective.txt").read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("objective.txt not found; using fallback")
        raw = "Your task is to engage with users as $PP_ALIAS. $PP_DESCRIPTION"

    t = Template(raw)
    return t.safe_substitute(PP_ALIAS=alias, PP_DESCRIPTION=description)


def compose_system_prompt(
    alias: str,
    traits: list[str],
    personality_mode: str = "playful",
    knowledge_context: str = "",
) -> str:
    """Assemble the full system prompt for a PixlPal chat turn.

    Args:
        alias:             The PixlPal's name (e.g. "Abbie").
        traits:            List of personality trait strings.
        personality_mode:  'playful' or 'witty'.
        knowledge_context: Optional string of token knowledge to inject.

    Returns:
        Rendered system prompt string ready for the Gemini API.
    """
    _load_fragments()

    # Build description from traits
    if not traits:
        description = f"{alias} is a friendly companion."
    elif len(traits) == 1:
        description = f"{alias} is {traits[0]}."
    elif len(traits) == 2:
        description = f"{alias} is {traits[0]} and {traits[1]}."
    else:
        description = f"{alias} is {', '.join(traits)}."

    objective = _build_objective(alias, description)

    # Knowledge context block (injected only when tokens exist)
    knowledge_block = ""
    if knowledge_context.strip():
        knowledge_block = (
            "\n\n**Knowledge you have learned:**\n"
            f"{knowledge_context.strip()}\n"
            "Draw on this knowledge naturally when it is relevant.\n"
        )

    # Personality mode note
    mode_note = (
        "Your personality is playful, warm, and enthusiastic."
        if personality_mode == "playful"
        else "Your personality is witty, dry, and cleverly sarcastic."
    )

    # Load base template
    template_path = _FRAGMENTS_DIR / "system_prompt.txt"
    try:
        base = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("system_prompt.txt missing — using inline fallback")
        base = (
            "$INTRO\n\n**Objective:**\n$OBJECTIVE\n\n**Directive:**\n$DIRECTIVE\n\n"
            "**Format:**\n$FORMAT\n\n**Rules:**\n$RULES\n\n**Examples:**\n$EXAMPLES"
        )

    substitutions = {
        **_fragment_cache,
        "OBJECTIVE": objective,
    }

    rendered = Template(base).safe_substitute(substitutions)

    # Append personality mode note and knowledge context after main body
    rendered = rendered + f"\n\n**Personality Mode:** {mode_note}" + knowledge_block

    return rendered
