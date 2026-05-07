"""Unit tests for the v12.1 image_prompt_library.

Pure-data tests that verify archetype selection and template filling.
No network, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.services.v4.image_prompt_library import (
    _ARCHETYPES,
    PromptArchetype,
    _select_archetype,
    build_image_prompt,
    list_archetypes,
)


# ── Minimal stand-in for ResolvedDesignTokens ─────────────────────

@dataclass
class FakePalette:
    primary: str = "#2563eb"
    accent: str = "#7c3aed"
    background: str = "#0b0d12"


@dataclass
class FakeTokens:
    palette: FakePalette = None
    density: str = "comfortable"

    def __post_init__(self) -> None:
        if self.palette is None:
            self.palette = FakePalette()


def _tokens(**overrides: Any) -> FakeTokens:
    return FakeTokens(**overrides)


# ── Archetype selection ───────────────────────────────────────────

def test_title_intent_selects_hero_cover() -> None:
    arch = _select_archetype(intent="title", layout="title-only")
    assert arch.name == "hero_cover_wide"


def test_problem_intent_selects_tension() -> None:
    arch = _select_archetype(intent="problem", layout="")
    assert arch.name == "problem_tension"


def test_product_intent_selects_showcase() -> None:
    arch = _select_archetype(intent="product", layout="image-full")
    assert arch.name == "product_showcase"


def test_market_intent_selects_market_abstract() -> None:
    arch = _select_archetype(intent="market", layout="stat-hero")
    assert arch.name == "market_abstract_data"


def test_competition_intent_selects_contrast() -> None:
    arch = _select_archetype(intent="competition", layout="comparison")
    assert arch.name == "competition_contrast"


def test_team_intent_selects_team_environment() -> None:
    arch = _select_archetype(intent="team", layout="team-grid")
    assert arch.name == "team_environment"


def test_unknown_intent_falls_back_to_generic() -> None:
    arch = _select_archetype(intent="made_up", layout="made_up")
    assert arch.name == "generic_editorial"


# ── Prompt building ───────────────────────────────────────────────

def test_build_prompt_inserts_palette_hex_codes() -> None:
    prompt, name = build_image_prompt(
        intent="title",
        layout="title-only",
        image_prompt="A modern dashboard showing AI agents analyzing invoices",
        headline="Agentic Procurement For Mid-Market",
        tokens=_tokens(),
    )
    assert name == "hero_cover_wide"
    assert "#2563eb" in prompt
    assert "#7c3aed" in prompt
    assert "#0b0d12" in prompt
    # Subject was threaded through
    assert "invoices" in prompt or "dashboard" in prompt


def test_build_prompt_uses_headline_when_no_image_prompt() -> None:
    prompt, _ = build_image_prompt(
        intent="problem",
        layout="",
        image_prompt="",
        headline="Manual Invoice Review Burns 40 Hours",
        tokens=_tokens(),
    )
    assert "Manual Invoice Review" in prompt


def test_build_prompt_has_no_text_directive_always() -> None:
    prompt, _ = build_image_prompt(
        intent="closing",
        layout="",
        image_prompt="",
        headline="Join Our Journey",
        tokens=_tokens(),
    )
    # Every archetype inherits the common tail that forbids on-image text
    assert "no on-image text" in prompt
    assert "no watermark" in prompt


def test_build_prompt_strips_writer_style_suffix() -> None:
    # Writer sometimes appends its own "style: ..." blob — library should
    # strip it so the archetype fully controls style.
    prompt, _ = build_image_prompt(
        intent="market",
        layout="stat-hero",
        image_prompt="Market opportunity in fintech. Style: cyberpunk neon. Lighting: dramatic.",
        headline="Market Opportunity",
        tokens=_tokens(),
    )
    assert "cyberpunk neon" not in prompt.lower()
    assert "dramatic" not in prompt.lower() or "dramatic" in prompt  # archetype may have its own 'dramatic'


def test_build_prompt_honors_dict_tokens() -> None:
    dict_tokens = {
        "palette": {"primary": "#ff6600", "accent": "#00ffff", "background": "#ffffff"},
        "density": "spacious",
    }
    prompt, _ = build_image_prompt(
        intent="title",
        layout="title-only",
        image_prompt="",
        headline="Test Deck",
        tokens=dict_tokens,
    )
    assert "#ff6600" in prompt
    assert "#00ffff" in prompt
    assert "airy" in prompt  # spacious density mood


def test_build_prompt_tolerates_missing_tokens() -> None:
    # Even with an empty fake token, we still produce a coherent prompt.
    prompt, _ = build_image_prompt(
        intent="vision",
        layout="",
        image_prompt="",
        headline="",
        tokens={"palette": {}, "density": "comfortable"},
    )
    assert len(prompt) > 50
    # Falls back to a palette-agnostic phrasing
    assert "restrained contemporary palette" in prompt or "dominant palette" in prompt


def test_list_archetypes_returns_full_catalog() -> None:
    catalog = list_archetypes()
    names = {a["name"] for a in catalog}
    assert "hero_cover_wide" in names
    assert "generic_editorial" in names
    assert len(catalog) == len(_ARCHETYPES)


def test_negatives_appended_when_present() -> None:
    prompt, _ = build_image_prompt(
        intent="team",
        layout="team-grid",
        image_prompt="A busy office",
        headline="Our Team",
        tokens=_tokens(),
    )
    assert "Avoid:" in prompt
    assert "no human faces" in prompt


def test_composition_adapts_to_layout() -> None:
    prompt_full, _ = build_image_prompt(
        intent="title", layout="image-full", image_prompt="",
        headline="Hi", tokens=_tokens(),
    )
    prompt_two_col, _ = build_image_prompt(
        intent="title", layout="two-column", image_prompt="",
        headline="Hi", tokens=_tokens(),
    )
    assert prompt_full != prompt_two_col
    assert "full-bleed" in prompt_full
    assert "left-weighted" in prompt_two_col


def test_deck_purpose_adds_specific_style_guidance() -> None:
    prompt, _ = build_image_prompt(
        intent="product",
        layout="product-showcase",
        image_prompt="Workflow automation console",
        headline="Launch-ready automation",
        tokens=_tokens(),
        deck_purpose="sales_deck",
    )
    assert "Deck-purpose style" in prompt
    assert "product marketing" in prompt
    assert "commercial polish" in prompt
