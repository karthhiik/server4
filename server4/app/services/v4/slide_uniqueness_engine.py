"""
V4 slide-uniqueness engine.

Runs *after* compile_slides has produced the canonical compiled-slide
list. Its job is to make every deck visually distinct from every other
deck and every slide visually distinct from every other slide in the
same deck — without changing the slide content.

The compile pass already handles content (research / writer / repair /
truth-guard) and the rhythm planner already prevents adjacent kit
repetition. What this engine adds:

1. **Decorative variation per slide.** Background patterns
   (grid / dots / waves / geometric / lines / radial), accent placement
   (top-right / bottom-left / etc.), gradient angles, decorative styles
   (minimal / tech / editorial / cinematic / geometric) cycle through a
   deterministic deck-scoped sequence so consecutive slides feel
   different without breaking visual cohesion.

2. **Headline alignment / max-width variety.** Title slides use
   center-aligned narrow text, problem slides use left-aligned wider
   text, stat slides use bold full-width treatment, comparison slides
   use balanced two-column max-width. The variety is driven by intent.

3. **Per-slide accent-color rotation.** Every deck has a primary
   palette but on multi-slide decks we cycle the chart palette so
   adjacent stat / chart slides aren't identical in color.

4. **Typography emphasis modes.** Headline / body / display / accent
   weight & tracking varies by slide intent so the deck reads with
   real editorial rhythm instead of one-size-fits-all.

The engine is deterministic — same input → same output — so screenshot
tests and exports stay stable. Variation is driven by ``deck_seed``
(derived from the project_id) plus the slide's intent, not random.

Public API::

    apply_uniqueness_pass(
        compiled_slides,
        deck_seed="64f9a91e",
        deck_purpose="pitch_deck",
        industry="ai",
    ) -> list[dict]   # mutates and returns the list

The function is idempotent: applying it twice produces the same result.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Decorative variation tables ────────────────────────────────────


_BACKGROUND_PATTERNS = ("grid", "dots", "waves", "geometric", "lines", "radial")
_DECORATIVE_STYLES = ("minimal", "tech", "editorial", "cinematic", "geometric")
_ACCENT_PLACEMENTS = ("top-right", "bottom-left", "top-left", "bottom-right")
_GRADIENT_ANGLES = (135, 45, 225, 315, 90, 0)


# ── Per-intent typography & layout signatures ─────────────────────


_INTENT_SIGNATURE: dict[str, dict[str, Any]] = {
    "title": {
        "headline_alignment": "center",
        "headline_max_width_pct": 80,
        "vertical_position": "center",
        "density_level": "minimal",
        "emphasis": "typography",
        "decorative_style": "cinematic",
    },
    "cover": {
        "headline_alignment": "center",
        "headline_max_width_pct": 80,
        "vertical_position": "center",
        "density_level": "minimal",
        "emphasis": "typography",
        "decorative_style": "cinematic",
    },
    "problem": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "top",
        "density_level": "balanced",
        "emphasis": "tension",
        "decorative_style": "editorial",
    },
    "solution": {
        "headline_alignment": "left",
        "headline_max_width_pct": 75,
        "vertical_position": "center",
        "density_level": "balanced",
        "emphasis": "clarity",
        "decorative_style": "tech",
    },
    "product": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "center",
        "density_level": "balanced",
        "emphasis": "clarity",
        "decorative_style": "tech",
    },
    "how_it_works": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "top",
        "density_level": "rich",
        "emphasis": "structure",
        "decorative_style": "tech",
    },
    "architecture": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "top",
        "density_level": "rich",
        "emphasis": "structure",
        "decorative_style": "tech",
    },
    "market": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "top",
        "density_level": "rich",
        "emphasis": "data",
        "decorative_style": "editorial",
    },
    "competition": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "top",
        "density_level": "rich",
        "emphasis": "data",
        "decorative_style": "editorial",
    },
    "traction": {
        "headline_alignment": "left",
        "headline_max_width_pct": 75,
        "vertical_position": "center",
        "density_level": "rich",
        "emphasis": "momentum",
        "decorative_style": "tech",
    },
    "milestones": {
        "headline_alignment": "left",
        "headline_max_width_pct": 75,
        "vertical_position": "center",
        "density_level": "rich",
        "emphasis": "momentum",
        "decorative_style": "tech",
    },
    "performance": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "center",
        "density_level": "rich",
        "emphasis": "data",
        "decorative_style": "tech",
    },
    "performance_metrics": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "center",
        "density_level": "rich",
        "emphasis": "data",
        "decorative_style": "tech",
    },
    "financial": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "top",
        "density_level": "rich",
        "emphasis": "data",
        "decorative_style": "editorial",
    },
    "financials": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "top",
        "density_level": "rich",
        "emphasis": "data",
        "decorative_style": "editorial",
    },
    "team": {
        "headline_alignment": "left",
        "headline_max_width_pct": 70,
        "vertical_position": "center",
        "density_level": "balanced",
        "emphasis": "people",
        "decorative_style": "editorial",
    },
    "ask": {
        "headline_alignment": "center",
        "headline_max_width_pct": 80,
        "vertical_position": "center",
        "density_level": "minimal",
        "emphasis": "decisive",
        "decorative_style": "cinematic",
    },
    "thank_you": {
        "headline_alignment": "center",
        "headline_max_width_pct": 80,
        "vertical_position": "center",
        "density_level": "minimal",
        "emphasis": "warm",
        "decorative_style": "cinematic",
    },
    "closing": {
        "headline_alignment": "center",
        "headline_max_width_pct": 80,
        "vertical_position": "center",
        "density_level": "minimal",
        "emphasis": "warm",
        "decorative_style": "cinematic",
    },
    "quote": {
        "headline_alignment": "center",
        "headline_max_width_pct": 75,
        "vertical_position": "center",
        "density_level": "minimal",
        "emphasis": "editorial",
        "decorative_style": "editorial",
    },
}


_DEFAULT_SIGNATURE: dict[str, Any] = {
    "headline_alignment": "left",
    "headline_max_width_pct": 70,
    "vertical_position": "center",
    "density_level": "balanced",
    "emphasis": "typography",
    "decorative_style": "minimal",
}


# ── Deck-seed helpers ──────────────────────────────────────────────


def _stable_seed(deck_seed: Optional[str]) -> int:
    """Project_id → small integer offset, deterministic across runs."""
    if not deck_seed:
        return 0
    digest = hashlib.sha1(str(deck_seed).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _intent_signature(intent: str) -> dict[str, Any]:
    if not intent:
        return dict(_DEFAULT_SIGNATURE)
    intent_lc = str(intent).lower().strip()
    # Direct match first
    if intent_lc in _INTENT_SIGNATURE:
        return dict(_INTENT_SIGNATURE[intent_lc])
    # Substring fallback so "traction_and_milestones" matches "traction".
    for key, sig in _INTENT_SIGNATURE.items():
        if key in intent_lc:
            return dict(sig)
    return dict(_DEFAULT_SIGNATURE)


# ── Public API ─────────────────────────────────────────────────────


def apply_uniqueness_pass(
    compiled_slides: list[dict[str, Any]],
    *,
    deck_seed: Optional[str] = None,
    deck_purpose: str = "",
    industry: str = "",
) -> list[dict[str, Any]]:
    """Mutate-in-place and return the compiled slide list.

    The pass is purely cosmetic — content (headline, bullets, body,
    table, chart, etc.) is never touched. We only adjust:

    * ``layout_params`` (background pattern, decorative style, accent
      placement, gradient angle, headline alignment / max width,
      vertical position, density level, emphasis)
    * ``palette_signature`` (chart-color rotation index used by the
      preview to vary chart colors per slide)

    The frontend's SlidePreview already reads ``layout_params`` for
    every key we set here, so existing deck artifacts pick up the
    variation without a frontend redeploy.
    """
    if not compiled_slides:
        return compiled_slides

    seed = _stable_seed(deck_seed) if deck_seed else 0
    n = len(compiled_slides)

    # Distinct decorative pattern per slide, cycled so adjacent slides
    # don't share. Seed offset means two decks for the same purpose +
    # industry won't look identical.
    pattern_offset = seed % len(_BACKGROUND_PATTERNS)
    accent_offset = (seed // 7) % len(_ACCENT_PLACEMENTS)
    angle_offset = (seed // 13) % len(_GRADIENT_ANGLES)

    for i, slide in enumerate(compiled_slides):
        # Pull the source slide from the compiled wrapper. compile_slides
        # produces ``{"source_slide": {...}, "artifacts": {...}, ...}``.
        source = slide.get("source_slide") or slide
        intent = str(source.get("intent") or slide.get("intent") or "").lower()

        sig = _intent_signature(intent)
        layout_params = dict(source.get("layout_params") or {})

        # Cycle decorative attributes per deck index. We keep the
        # decorative_style aligned with the intent's editorial mood so
        # the variation never drifts into incongruous territory.
        layout_params["background_pattern"] = _BACKGROUND_PATTERNS[
            (i + pattern_offset) % len(_BACKGROUND_PATTERNS)
        ]
        layout_params["accent_placement"] = _ACCENT_PLACEMENTS[
            (i + accent_offset) % len(_ACCENT_PLACEMENTS)
        ]
        layout_params["gradient_angle"] = _GRADIENT_ANGLES[
            (i + angle_offset) % len(_GRADIENT_ANGLES)
        ]

        # Intent-driven signature wins for the editorial fields.
        for key, value in sig.items():
            layout_params[key] = value

        # Subtle overlay opacity variation so consecutive slides look
        # different but stay readable. Range: 0.06 - 0.16.
        layout_params["overlay_opacity"] = round(
            0.06 + ((i + seed) % 6) * 0.02, 2
        )

        # Chart palette rotation: each slide picks a different starting
        # colour from the 7-stop chart palette so adjacent stat /
        # chart slides aren't twin-coloured.
        chart_palette_offset = (i + seed) % 7
        slide_signature = dict(slide.get("palette_signature") or {})
        slide_signature["chart_palette_offset"] = chart_palette_offset
        slide["palette_signature"] = slide_signature

        # Persist back into both the compiled wrapper and the source
        # slide so renderers that read either path see the change.
        source["layout_params"] = layout_params
        slide["layout_params"] = layout_params
        _sync_layout_params_to_artifacts(slide, layout_params)

    logger.info(
        "uniqueness_pass_applied",
        slide_count=n,
        deck_seed=str(deck_seed)[:12] if deck_seed else None,
        purpose=deck_purpose,
        industry=industry,
    )
    return compiled_slides


def _sync_layout_params_to_artifacts(
    slide: dict[str, Any],
    layout_params: dict[str, Any],
) -> None:
    """Keep compiled kit props in sync with top-level layout params.

    The inline sandbox renders from artifacts.kit_jsx.props_json, while
    export/review paths may read top-level layout_params/source_slide. Syncing
    here preserves preview/export parity without changing visible content.
    """
    artifacts = slide.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    kit_jsx = artifacts.get("kit_jsx")
    if not isinstance(kit_jsx, dict):
        return
    props = kit_jsx.get("props_json")
    if not isinstance(props, dict):
        return
    existing = props.get("layoutParams")
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(layout_params)
    props["layoutParams"] = merged


__all__ = [
    "apply_uniqueness_pass",
]
