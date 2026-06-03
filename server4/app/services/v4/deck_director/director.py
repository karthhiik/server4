"""Deck Director for narrative pacing, density, and visual rhythm.

This module intentionally works with the existing V4 skeleton model instead
of replacing it. It adds a deterministic deck-level pass before writers run so
each slide has a role in the full story, not just a local layout hint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ARC_INTENTS: dict[str, tuple[str, ...]] = {
    "startup_fundraising": (
        "vision", "problem", "why_now", "solution", "product",
        "market", "traction", "business_model", "go_to_market",
        "competition", "team", "financials", "ask",
    ),
    "investor_pitch": (
        "vision", "problem", "why_now", "solution", "product",
        "market", "traction", "business_model", "go_to_market",
        "competition", "team", "financials", "ask",
    ),
    "pitch_deck": (
        "vision", "problem", "why_now", "solution", "product",
        "market", "traction", "business_model", "go_to_market",
        "competition", "team", "financials", "ask",
    ),
    "product_pitch": (
        "problem", "current_workflow", "pain_points", "product_demo",
        "benefits", "proof", "pricing", "implementation", "cta",
    ),
    "enterprise_sales": (
        "business_challenge", "cost_of_inaction", "solution",
        "architecture", "security", "roi", "case_study",
        "rollout_plan", "next_steps",
    ),
    "investor_update": (
        "highlights", "metrics", "product_updates", "market",
        "team", "financials", "roadmap", "ask",
    ),
}

INTENT_LAYOUTS: dict[str, str] = {
    "vision": "title-only",
    "problem": "comparison",
    "why_now": "stat-hero",
    "solution": "grid-3",
    "product": "diagram",
    "product_demo": "image-full",
    "market": "chart-focus",
    "traction": "chart-focus",
    "business_model": "stat-hero",
    "go_to_market": "timeline",
    "competition": "comparison",
    "financials": "chart-focus",
    "team": "team",
    "ask": "stat-hero",
    "cta": "title-only",
    "architecture": "diagram",
    "security": "diagram",
    "roi": "chart-focus",
    "roadmap": "timeline",
    "metrics": "chart-focus",
    "highlights": "stat-hero",
}

EMOTIONAL_CURVE: tuple[str, ...] = (
    "inspire", "agitate", "urgency", "relief", "excitement",
    "confidence", "proof", "trust", "action",
)

LAYOUT_DENSITY: dict[str, str] = {
    "title-only": "minimal",
    "image-full": "low",
    "quote": "low",
    "stat-hero": "medium",
    "grid-3": "medium",
    "comparison": "high",
    "chart-focus": "high",
    "diagram": "medium",
    "timeline": "medium",
    "team": "medium",
    "two-column": "medium",
}


@dataclass(frozen=True)
class DirectedSlide:
    index: int
    intent: str
    narrative_role: str
    density: str
    emotion: str
    layout_category: str
    rationale: str


@dataclass(frozen=True)
class DeckPlan:
    purpose: str
    arc: str
    slides: list[DirectedSlide] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "arc": self.arc,
            "slides": [s.__dict__.copy() for s in self.slides],
        }


class DeckDirector:
    """Apply deck-level pacing to an existing skeleton."""

    def direct(self, skeleton: Any, *, purpose: str) -> DeckPlan:
        arc = self._resolve_arc(purpose, getattr(skeleton, "narrative_arc", ""))
        slides = list(getattr(skeleton, "slides", []) or [])
        directed: list[DirectedSlide] = []
        last_layout = ""
        density_streak = 0
        last_density = ""

        for i, slide in enumerate(slides):
            intent = self._normalize_intent(getattr(slide, "intent", "") or "")
            layout = self._layout_for(intent, getattr(slide, "layout_hint", ""), last_layout)
            density = self._density_for(layout, i, density_streak, last_density)
            emotion = self._emotion_for(i, len(slides))
            narrative_role = self._narrative_role(i, len(slides), intent)
            rationale = self._rationale(intent, narrative_role, density, emotion)

            slide.layout_hint = layout
            slide.density_target = density
            if not getattr(slide, "purpose", ""):
                slide.purpose = rationale
            slide.raw_director = {
                "narrative_role": narrative_role,
                "density": density,
                "emotion": emotion,
                "layout_category": layout,
            }

            directed.append(
                DirectedSlide(
                    index=int(getattr(slide, "index", i)),
                    intent=intent,
                    narrative_role=narrative_role,
                    density=density,
                    emotion=emotion,
                    layout_category=layout,
                    rationale=rationale,
                )
            )
            density_streak = density_streak + 1 if density == last_density else 1
            last_density = density
            last_layout = layout

        skeleton.raw_planner_output = {
            **(getattr(skeleton, "raw_planner_output", {}) or {}),
            "deck_director": DeckPlan(purpose=purpose, arc=arc, slides=directed).to_dict(),
        }
        return DeckPlan(purpose=purpose, arc=arc, slides=directed)

    def _resolve_arc(self, purpose: str, existing: str) -> str:
        key = (purpose or existing or "investor_pitch").strip().lower()
        if key in ARC_INTENTS:
            return key
        if "sales" in key or "enterprise" in key:
            return "enterprise_sales"
        if "product" in key:
            return "product_pitch"
        if "update" in key:
            return "investor_update"
        return "investor_pitch"

    def _normalize_intent(self, intent: str) -> str:
        text = intent.strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"title", "cover", "intro"}:
            return "vision"
        if text in {"gtm", "go_to_market_strategy"}:
            return "go_to_market"
        if text in {"market_size", "tam", "market_opportunity"}:
            return "market"
        if text in {"closing", "thank_you"}:
            return "ask"
        return text or "content"

    def _layout_for(self, intent: str, current: str, last_layout: str) -> str:
        layout = INTENT_LAYOUTS.get(intent) or current or "two-column"
        if layout == "auto":
            layout = "two-column"
        if layout == last_layout:
            if layout == "chart-focus":
                return "stat-hero"
            if layout == "grid-3":
                return "diagram"
            if layout == "two-column":
                return "comparison"
        return layout

    def _density_for(self, layout: str, index: int, streak: int, last_density: str) -> str:
        density = LAYOUT_DENSITY.get(layout, "medium")
        if index == 0:
            density = "minimal"
        if streak >= 2 and density == last_density:
            if density == "high":
                density = "medium"
            elif density == "medium":
                density = "low"
        return density

    def _emotion_for(self, index: int, total: int) -> str:
        if total <= 1:
            return EMOTIONAL_CURVE[0]
        curve_index = round((index / max(1, total - 1)) * (len(EMOTIONAL_CURVE) - 1))
        return EMOTIONAL_CURVE[curve_index]

    def _narrative_role(self, index: int, total: int, intent: str) -> str:
        if index == 0:
            return "opening_hook"
        if index == total - 1:
            return "closing_action"
        if intent in {"market", "traction", "financials", "metrics"}:
            return "evidence"
        if intent in {"product", "solution", "architecture"}:
            return "explanation"
        if intent in {"problem", "why_now"}:
            return "tension"
        return "story_progression"

    def _rationale(self, intent: str, role: str, density: str, emotion: str) -> str:
        return (
            f"{intent.replace('_', ' ')} slide acts as {role.replace('_', ' ')} "
            f"with {density} density and {emotion} tone."
        )
