"""Curated layout variants for the V4 layout intent engine.

This is deliberately a small, typed data library rather than an LLM or
embedding dependency. The selector scores these variants against slide
features at compile time, so standard mode keeps the Plan 05 speed budget
while still avoiding the old template-stamp fall-through.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutSpec:
    kit_id: str
    variant: str
    intents: tuple[str, ...] = ()
    layout_keywords: tuple[str, ...] = ()
    min_words: int = 0
    max_words: int = 2400
    min_bullets: int = 0
    max_bullets: int = 99
    requires: tuple[str, ...] = ()
    prefers: tuple[str, ...] = ()
    positions: tuple[str, ...] = ()
    purposes: tuple[str, ...] = ()
    density: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return f"{self.kit_id}:{self.variant}"


LAYOUT_LIBRARY: tuple[LayoutSpec, ...] = (
    LayoutSpec(
        kit_id="TitleHero",
        variant="cover-gradient",
        intents=("title", "cover", "intro"),
        layout_keywords=("title", "cover", "opener", "hero"),
        max_words=90,
        positions=("opening",),
    ),
    LayoutSpec(
        kit_id="TitleHero",
        variant="cover-image",
        intents=("title", "cover", "vision"),
        layout_keywords=("image", "hero", "full-bleed"),
        max_words=110,
        requires=("image",),
        positions=("opening",),
    ),
    LayoutSpec(
        kit_id="TitleHero",
        variant="thesis-left",
        intents=("problem", "solution", "overview", "content", "vision"),
        layout_keywords=("title-and-body", "thesis", "statement"),
        min_words=8,
        max_words=260,
        max_bullets=3,
    ),
    LayoutSpec(
        kit_id="TitleHero",
        variant="section-break",
        intents=("section", "transition", "agenda"),
        layout_keywords=("section", "divider", "transition"),
        max_words=120,
    ),
    LayoutSpec(
        kit_id="TitleHero",
        variant="closing-ask",
        intents=("closing", "ask", "thanks", "thank_you"),
        layout_keywords=("closing", "ask", "cta"),
        max_words=180,
        positions=("closing",),
    ),
    LayoutSpec(
        kit_id="FullBleedImage",
        variant="editorial-bleed-left",
        intents=("vision", "closing", "ask", "cover"),
        layout_keywords=("full-bleed", "background image", "image-full"),
        max_words=180,
        requires=("image",),
    ),
    LayoutSpec(
        kit_id="FullBleedImage",
        variant="editorial-bleed-right",
        intents=("customer", "case_study", "moment", "vision"),
        layout_keywords=("full-bleed", "image-right", "photo"),
        max_words=180,
        requires=("image",),
    ),
    LayoutSpec(
        kit_id="FullBleedImage",
        variant="duotone-proof",
        intents=("traction", "proof", "momentum"),
        layout_keywords=("image", "proof", "momentum"),
        max_words=160,
        requires=("image",),
        prefers=("stats",),
    ),
    LayoutSpec(
        kit_id="StatHero",
        variant="centered-stat",
        intents=("traction", "metrics", "market", "tam", "financials"),
        layout_keywords=("stat", "big number", "metric"),
        max_words=180,
        requires=("stats",),
        density=("sparse",),
    ),
    LayoutSpec(
        kit_id="StatHero",
        variant="kpi-strip",
        intents=("traction", "metrics", "financials", "unit_economics"),
        layout_keywords=("kpi", "metrics", "numbers"),
        max_words=360,
        requires=("stats",),
    ),
    LayoutSpec(
        kit_id="StatHero",
        variant="market-scale",
        intents=("market", "tam", "market_opportunity"),
        layout_keywords=("market", "tam", "sam", "som"),
        max_words=260,
        requires=("stats",),
        purposes=("pitch_deck", "investor_pitch", "investor_update"),
    ),
    LayoutSpec(
        kit_id="ChartBlock",
        variant="chart-focus",
        intents=("market", "traction", "financials", "metrics"),
        layout_keywords=("chart", "graph", "data"),
        max_words=420,
        requires=("chart",),
    ),
    LayoutSpec(
        kit_id="ChartBlock",
        variant="chart-with-thesis",
        intents=("insight", "analysis", "market", "trend"),
        layout_keywords=("chart", "thesis", "data story"),
        min_words=40,
        max_words=650,
        requires=("chart",),
    ),
    LayoutSpec(
        kit_id="ChartBlock",
        variant="financial-model",
        intents=("financials", "revenue", "forecast", "unit_economics"),
        layout_keywords=("financial", "projection", "forecast"),
        max_words=520,
        requires=("chart",),
    ),
    LayoutSpec(
        kit_id="TimelineBlock",
        variant="roadmap-horizontal",
        intents=("roadmap", "timeline", "milestones", "go_to_market"),
        layout_keywords=("timeline", "roadmap", "milestone"),
        max_words=720,
        requires=("timeline",),
    ),
    LayoutSpec(
        kit_id="TimelineBlock",
        variant="roadmap-vertical",
        intents=("implementation", "rollout", "plan"),
        layout_keywords=("vertical timeline", "phases", "rollout"),
        min_words=90,
        max_words=900,
        requires=("timeline",),
    ),
    LayoutSpec(
        kit_id="TimelineBlock",
        variant="process-flow",
        intents=("how_it_works", "process", "workflow"),
        layout_keywords=("step", "phase", "process", "flow"),
        max_words=760,
        requires=("timeline",),
    ),
    LayoutSpec(
        kit_id="ComparisonBlock",
        variant="compare-2col",
        intents=("competition", "comparison", "alternatives", "before_after"),
        layout_keywords=("comparison", "vs", "matrix", "side-by-side"),
        max_words=1000,
        requires=("comparison",),
    ),
    LayoutSpec(
        kit_id="ComparisonBlock",
        variant="compare-3col",
        intents=("competition", "landscape", "pricing", "packages"),
        layout_keywords=("matrix", "landscape", "pricing"),
        min_words=80,
        max_words=1300,
        requires=("comparison",),
    ),
    LayoutSpec(
        kit_id="FeatureGrid",
        variant="feature-cards-3",
        intents=("solution", "features", "benefits", "product"),
        layout_keywords=("feature", "cards", "grid"),
        min_words=24,
        max_words=620,
        min_bullets=2,
        max_bullets=3,
        requires=("features",),
    ),
    LayoutSpec(
        kit_id="FeatureGrid",
        variant="feature-cards-4",
        intents=("solution", "features", "capabilities", "product"),
        layout_keywords=("feature", "cards", "grid"),
        min_words=32,
        max_words=760,
        min_bullets=4,
        max_bullets=6,
        requires=("features",),
    ),
    LayoutSpec(
        kit_id="FeatureGrid",
        variant="benefits-two-col",
        intents=("benefits", "value", "why_now", "problem"),
        layout_keywords=("two-column", "benefits", "value"),
        min_words=28,
        max_words=700,
        min_bullets=2,
        max_bullets=4,
        requires=("features",),
    ),
    LayoutSpec(
        kit_id="FeatureGrid",
        variant="capabilities-scan",
        intents=("overview", "capabilities", "content", "education"),
        layout_keywords=("grid", "overview", "capabilities"),
        min_words=28,
        max_words=840,
        min_bullets=3,
        max_bullets=6,
        requires=("features",),
    ),
    LayoutSpec(
        kit_id="FeatureGrid",
        variant="issue-solution-grid",
        intents=("problem", "solution", "pain_point"),
        layout_keywords=("problem-solution", "issue", "solution"),
        min_words=24,
        max_words=760,
        min_bullets=2,
        max_bullets=6,
        requires=("features",),
    ),
    LayoutSpec(
        kit_id="TeamGrid",
        variant="founder-row",
        intents=("team", "founders", "leadership"),
        layout_keywords=("team", "founder"),
        requires=("team",),
        max_words=700,
    ),
    LayoutSpec(
        kit_id="TeamGrid",
        variant="leadership-grid",
        intents=("team", "advisors", "leadership"),
        layout_keywords=("team", "grid", "leadership"),
        requires=("team",),
        max_words=900,
    ),
    LayoutSpec(
        kit_id="QuoteBlock",
        variant="quote-pull",
        intents=("quote", "testimonial", "customer", "proof"),
        layout_keywords=("quote", "testimonial"),
        max_words=420,
        requires=("quote",),
    ),
    LayoutSpec(
        kit_id="QuoteBlock",
        variant="testimonial-accent",
        intents=("testimonial", "customer", "proof", "traction"),
        layout_keywords=("quote", "accent", "testimonial"),
        max_words=440,
        requires=("quote",),
    ),
    LayoutSpec(
        kit_id="DiagramBlock",
        variant="process-diagram",
        intents=("how_it_works", "workflow", "process"),
        layout_keywords=("diagram", "flow", "process"),
        max_words=680,
        requires=("diagram",),
    ),
    LayoutSpec(
        kit_id="DiagramBlock",
        variant="architecture-map",
        intents=("architecture", "platform", "system"),
        layout_keywords=("architecture", "system map", "network"),
        max_words=760,
        requires=("diagram",),
    ),
    LayoutSpec(
        kit_id="DiagramBlock",
        variant="flywheel",
        intents=("growth", "flywheel", "loop", "strategy"),
        layout_keywords=("flywheel", "loop", "cycle"),
        max_words=680,
        requires=("diagram",),
    ),
)