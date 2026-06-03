"""
V4 Visual Decider — Deterministic auto-routing of slide visuals to code or image.

The system (NOT the user) decides the visual rendering modality for every slide.

Decision priority (first match wins):
  1. Slide already has a structured block (chart/table/timeline/comparison/diagram
     /stat_blocks/quote) → render via CODE (HTML/React/Chart.js/React Flow).
  2. Slide intent or layout demands a hero image (title, image-full, hero,
     atmosphere) AND has no structured block → render via IMAGE (Flux/Phoenix).
  3. Slide layout is "icon-grid" or visual_cue is "icon-grid" → render via CODE
     (icon library, no LLM image gen).
  4. Slide is text-only and short (≤60 words total) → no visual needed; rely on
     typography. Modality = "none".
  5. Default fallback for media-light slides → IMAGE (background atmosphere).

Modality returned ∈ {"code", "image", "none"}.
The router/renderer uses this to gate Flux/Phoenix calls (expensive) only when
the slide cannot be rendered with code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.services.v4.visual_element_validator import ensure_valid_visual_element


CODE_BLOCK_FIELDS = ("chart", "table", "timeline", "comparison", "diagram", "stat_blocks", "quote")

IMAGE_INTENTS = {"title", "cover", "hero", "atmosphere", "image", "vision", "closing", "ask"}
IMAGE_LAYOUTS = {"image-full", "full-bleed", "image-dominant", "hero"}
ICON_LAYOUTS = {"icon-grid", "feature-grid"}


@dataclass
class VisualDecision:
    modality: str          # "code" | "image" | "none"
    reason: str            # human-readable why
    code_block: Optional[str] = None    # which structured block to render (if modality=="code")
    suggested_renderer: Optional[str] = None  # "chart.js" | "react-flow" | "html-table" | "css-grid" | "flux" | "phoenix"


def _has(value: Any) -> bool:
    """True if a slide field is present and non-empty."""
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict, str)):
        return len(value) > 0
    return True


def _word_count(slide: dict) -> int:
    parts: list[str] = [str(slide.get("headline") or "")]
    if slide.get("subheadline"):
        parts.append(str(slide["subheadline"]))
    if slide.get("body"):
        parts.append(str(slide["body"]))
    parts.extend(str(b) for b in (slide.get("bullets") or []))
    return sum(len(p.split()) for p in parts)


def _renderer_for(block: str) -> str:
    return {
        "chart": "chart.js",
        "table": "html-table",
        "timeline": "react-timeline",
        "comparison": "css-grid",
        "diagram": "react-flow",
        "stat_blocks": "css-hero",
        "quote": "css-quote",
    }.get(block, "code")


def _renderable_block(block: str, value: Any) -> bool:
    """Return True only when a structured block can actually render."""
    if block in {"chart", "table", "timeline", "comparison", "diagram"}:
        return ensure_valid_visual_element(block, value) is not None
    if block == "stat_blocks":
        if not isinstance(value, list):
            return False
        for item in value:
            if not isinstance(item, dict):
                continue
            val = str(item.get("value", "")).strip().lower()
            label = str(item.get("label", "")).strip().lower()
            raw = f"{val} {label}".strip()
            if (
                raw
                and val not in {"~", "tbd", "n/a", "$x", "y%", "z"}
                and label not in {"~", "tbd", "n/a"}
            ):
                return True
        return False
    if block == "quote":
        return isinstance(value, dict) and bool(value.get("text") or value.get("quote"))
    return _has(value)


def decide_visual(slide: dict) -> VisualDecision:
    """Decide the visual modality for a single slide dict.

    Accepts either the GeneratedSlide dataclass converted to dict, or the
    persisted Mongo slide document — both have the same field names.
    """
    layout = (slide.get("layout") or "").lower()
    intent = (slide.get("intent") or "").lower()
    visual_cue = (slide.get("visual_cue") or "").lower() if slide.get("visual_cue") else ""

    # Rule 1 — any structured block wins
    for block in CODE_BLOCK_FIELDS:
        if _renderable_block(block, slide.get(block)):
            return VisualDecision(
                modality="code",
                reason=f"slide has structured `{block}` block",
                code_block=block,
                suggested_renderer=_renderer_for(block),
            )

    # Rule 3 — icon grid
    if layout in ICON_LAYOUTS or visual_cue == "icon-grid":
        return VisualDecision(
            modality="code",
            reason="layout=icon-grid uses icon library, not image gen",
            code_block="icon-grid",
            suggested_renderer="icon-library",
        )

    # Rule 2 — explicit image intent / layout
    if layout in IMAGE_LAYOUTS or intent in IMAGE_INTENTS or visual_cue == "image":
        return VisualDecision(
            modality="image",
            reason=f"intent/layout demands hero image (intent={intent}, layout={layout})",
            suggested_renderer="flux",
        )

    # Rule 4 — only TRUE single-line title cards skip a visual.
    # Threshold dropped from 60 → 12 (v10.5): a body slide should always have
    # at least an atmospheric background image; otherwise the deck looks
    # un-designed and the renderer dashboard shows None entries.
    wc = _word_count(slide)
    if wc <= 12 and intent in {"title", "section_break", "divider"} and not slide.get("image_prompt"):
        return VisualDecision(
            modality="none",
            reason=f"true title card (words={wc}, intent={intent}); typography is enough",
        )

    # Rule 5 — default: every body slide gets an atmospheric image
    return VisualDecision(
        modality="image",
        reason="body slide — atmospheric background image",
        suggested_renderer="phoenix",
    )


def decide_deck(slides: list[dict]) -> list[VisualDecision]:
    """Apply decide_visual across a deck."""
    return [decide_visual(s) for s in slides]
