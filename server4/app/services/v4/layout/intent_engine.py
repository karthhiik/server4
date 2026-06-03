"""Plan 06 layout intent engine.

The engine maps writer output to a kit + layout variant using only real
slide fields. It is intentionally deterministic and sub-millisecond: no
network calls, no LLM calls, no embeddings. The goal is to encode the
designer judgement that was previously scattered across shallow compiler
branches: content density, structured media, deck position, purpose, and
recent repetition should all influence layout selection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from app.services.v4.layout.library import LAYOUT_LIBRARY, LayoutSpec
from app.services.v4.composition_engine import score_composition


_INTENT_ALIASES = {
    "introduction": "title",
    "introduce": "title",
    "intro": "title",
    "cover": "title",
    "opener": "title",
    "thank you": "thanks",
    "call-to-action": "ask",
    "call to action": "ask",
    "kpi": "metrics",
    "kpis": "metrics",
    "highlight": "metrics",
    "highlights": "metrics",
    "founders": "team",
    "leadership": "team",
}

_NUMBER_RE = re.compile(
    r"(?:[$£€]?\d[\d,]*(?:\.\d+)?\s*[%KMBT]?\b|\d+\s*x)",
    re.IGNORECASE,
)

_TIMELINE_HINT_RE = re.compile(
    r"^(?:q[1-4]\s*\d{2,4}|\d{4}|phase\s*\d+|step\s*\d+|month\s*\d+)\s*[:\-–—]",
    re.IGNORECASE,
)

_QUOTE_RE = re.compile(r'["“”].{8,240}?["“”]', re.DOTALL)

_COMPARISON_WORDS = ("compar", " vs ", "versus", "matrix", "side-by-side", "side by side")
_DIAGRAM_WORDS = ("diagram", "architecture", "system map", "network", "flywheel", "loop")
_TIMELINE_WORDS = ("timeline", "roadmap", "milestone", "phase", "step", "process", "journey")

_TEMPLATE_KIT_TO_LAYOUT_KITS: dict[str, tuple[str, ...]] = {
    "TitleHero": ("TitleHero", "CinematicHero", "DuotoneHero"),
    "CoverSlide": ("TitleHero", "CinematicHero", "DuotoneHero"),
    "CinematicHero": ("CinematicHero", "TitleHero"),
    "DuotoneHero": ("DuotoneHero", "TitleHero"),
    "FullBleedImage": ("FullBleedImage",),
    "EditorialImage": ("EditorialImage", "SplitOverlap", "FullBleedImage"),
    "SplitContent": ("FeatureGrid", "EditorialImage", "SplitOverlap"),
    "SplitOverlap": ("SplitOverlap", "EditorialImage"),
    "ValuePropGrid": ("FeatureGrid", "BentoGrid", "GlassCard"),
    "FeatureGrid": ("FeatureGrid", "BentoGrid", "GlassCard"),
    "BentoGrid": ("BentoGrid", "FeatureGrid"),
    "GlassCard": ("GlassCard", "FeatureGrid"),
    "ProblemSolution": ("ComparisonBlock", "FeatureGrid"),
    "BeforeAfter": ("ComparisonBlock",),
    "ComparisonBlock": ("ComparisonBlock",),
    "MetricsDashboard": ("StatHero", "ChartBlock", "FloatingStat"),
    "StatHero": ("StatHero", "FloatingStat"),
    "FloatingStat": ("FloatingStat", "StatHero"),
    "StatHighlight": ("StatHero", "FloatingStat"),
    "ChartBlock": ("ChartBlock", "StatHero"),
    "AnimatedChartBlock": ("ChartBlock",),
    "DataTable": ("ChartBlock", "ComparisonBlock"),
    "Roadmap": ("TimelineBlock",),
    "TimelineBlock": ("TimelineBlock",),
    "ProcessFlow": ("TimelineBlock", "DiagramBlock"),
    "DiagramBlock": ("DiagramBlock",),
    "TeamGrid": ("TeamGrid",),
    "TeamMemberStrip": ("TeamGrid",),
    "QuoteBlock": ("QuoteBlock",),
    "QuoteHighlight": ("QuoteBlock",),
    "TestimonialCard": ("QuoteBlock",),
    "SocialProof": ("BentoGrid", "FeatureGrid", "QuoteBlock"),
    "LogoMarquee": ("FeatureGrid",),
    "PricingTable": ("ComparisonBlock", "FeatureGrid"),
    "AppMockup": ("FullBleedImage", "EditorialImage", "SplitOverlap"),
}


@dataclass(frozen=True)
class LayoutFeatures:
    intent: str
    raw_intent: str
    layout_hint: str
    purpose: str
    word_count: int
    bullet_count: int
    avg_bullet_words: float
    has_chart: bool
    has_timeline: bool
    has_comparison: bool
    has_diagram: bool
    has_quote: bool
    has_team: bool
    has_stats: bool
    has_image: bool
    wants_image: bool
    has_features: bool
    template_kit_component: str
    density: str
    position: str
    signals: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "raw_intent": self.raw_intent,
            "layout_hint": self.layout_hint,
            "purpose": self.purpose,
            "word_count": self.word_count,
            "bullet_count": self.bullet_count,
            "avg_bullet_words": round(self.avg_bullet_words, 2),
            "template_kit_component": self.template_kit_component,
            "density": self.density,
            "position": self.position,
            "signals": list(self.signals),
        }


@dataclass(frozen=True)
class LayoutCandidate:
    kit_id: str
    layout_variant: str
    score: float
    rationale: str
    features: LayoutFeatures

    @property
    def key(self) -> str:
        return f"{self.kit_id}:{self.layout_variant}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kit_id": self.kit_id,
            "layout_variant": self.layout_variant,
            "score": round(self.score, 2),
            "rationale": self.rationale,
            "features": self.features.to_dict(),
        }


def _canonical_intent(raw: str | None) -> str:
    key = (raw or "").strip().lower().replace("_", " ")
    return _INTENT_ALIASES.get(key, key).replace(" ", "_")


def _words(text: str | None) -> list[str]:
    return re.findall(r"[A-Za-z0-9$£€%\.]+", text or "")


def _chart_has_data(chart: Any) -> bool:
    return isinstance(chart, Mapping) and isinstance(chart.get("data"), list) and bool(chart.get("data"))


def _timeline_has_events(timeline: Any) -> bool:
    return isinstance(timeline, Mapping) and bool(timeline.get("events"))


def _comparison_has_rows(comparison: Any) -> bool:
    if not isinstance(comparison, Mapping):
        return False
    columns = comparison.get("columns") or []
    if not isinstance(columns, list) or len(columns) < 2:
        return False
    row_count = 0
    for col in columns:
        if not isinstance(col, Mapping):
            continue
        row_count = max(row_count, len(col.get("rows") or []), len(col.get("items") or []))
    return row_count >= 2 or len(comparison.get("features") or []) >= 2


def _diagram_has_nodes(diagram: Any) -> bool:
    return isinstance(diagram, Mapping) and isinstance(diagram.get("nodes"), list) and bool(diagram.get("nodes"))


def _quote_present(quote: Any, body: str, bullets: Sequence[str]) -> bool:
    if isinstance(quote, Mapping) and (quote.get("text") or quote.get("quote")):
        return True
    return bool(_QUOTE_RE.search(body or "") or any(_QUOTE_RE.search(str(b)) for b in bullets))


def _comparison_hint(layout_hint: str, bullets: Sequence[str]) -> bool:
    if any(word in layout_hint for word in _COMPARISON_WORDS):
        return True
    rows = 0
    for bullet in bullets:
        text = str(bullet or "").lower()
        if ":" in text and (" vs " in text or " | " in text):
            rows += 1
    return rows >= 2


def _timeline_hint(layout_hint: str, bullets: Sequence[str]) -> bool:
    if any(word in layout_hint for word in _TIMELINE_WORDS):
        return True
    return sum(1 for bullet in bullets if _TIMELINE_HINT_RE.search(str(bullet or ""))) >= 2


def _diagram_hint(layout_hint: str) -> bool:
    return any(word in layout_hint for word in _DIAGRAM_WORDS)


def _numeric_bullet_count(bullets: Sequence[str]) -> int:
    return sum(1 for bullet in bullets if _NUMBER_RE.search(str(bullet or "")))


def _position(deck_index: int, deck_total: int) -> str:
    total = max(deck_total, 1)
    if deck_index <= 0:
        return "opening"
    if deck_index >= total - 1:
        return "closing"
    ratio = deck_index / max(total - 1, 1)
    if ratio < 0.34:
        return "early"
    if ratio > 0.72:
        return "late"
    return "middle"


def _density(word_count: int, bullet_count: int, avg_bullet_words: float) -> str:
    if word_count <= 34 and bullet_count <= 2:
        return "sparse"
    if word_count >= 170 or bullet_count >= 6 or avg_bullet_words > 18:
        return "dense"
    return "balanced"


def _density_float(word_count: int, bullet_count: int, avg_bullet_words: float) -> float:
    """Return 0..1 content density for composition engine."""
    d = _density(word_count, bullet_count, avg_bullet_words)
    return {"sparse": 0.25, "balanced": 0.55, "dense": 0.85}.get(d, 0.5)


def extract_features(
    slide: Any,
    *,
    deck_purpose: str = "",
    deck_index: int = 0,
    deck_total: int = 1,
    image_available: bool | None = None,
) -> LayoutFeatures:
    bullets = [str(b).strip() for b in (getattr(slide, "bullets", None) or []) if str(b).strip()]
    body = str(getattr(slide, "body", None) or "")
    layout_hint = str(getattr(slide, "layout", None) or "").strip().lower()
    raw_intent = str(getattr(slide, "intent", None) or "")
    intent = _canonical_intent(raw_intent)
    purpose = (deck_purpose or getattr(slide, "purpose", "") or "").strip().lower()
    headline = str(getattr(slide, "headline", None) or "")
    subheadline = str(getattr(slide, "subheadline", None) or "")
    word_count = len(_words(" ".join([headline, subheadline, body, " ".join(bullets)])))
    avg_bullet_words = sum(len(_words(b)) for b in bullets) / max(len(bullets), 1)
    numeric_count = _numeric_bullet_count(bullets)
    has_chart = _chart_has_data(getattr(slide, "chart", None))
    has_timeline = _timeline_has_events(getattr(slide, "timeline", None)) or _timeline_hint(layout_hint, bullets)
    has_comparison = _comparison_has_rows(getattr(slide, "comparison", None)) or _comparison_hint(layout_hint, bullets)
    has_diagram = _diagram_has_nodes(getattr(slide, "diagram", None)) or _diagram_hint(layout_hint)
    has_quote = _quote_present(getattr(slide, "quote", None), body, bullets)
    has_team = bool(getattr(slide, "team_members", None))
    has_stats = bool(getattr(slide, "stat_blocks", None)) or numeric_count >= 2
    render_decision = getattr(slide, "render_decision", None) or {}
    wants_image = (
        bool(getattr(slide, "image_prompt", None))
        or str(render_decision.get("modality") or "").lower() == "image"
        or "image" in layout_hint
        or "photo" in layout_hint
    )
    has_image = bool(image_available) or bool(getattr(slide, "image_url", None)) or wants_image
    has_features = len(bullets) >= 2 and avg_bullet_words <= 18
    template_kit_component = str(getattr(slide, "template_kit_component", None) or "")
    signals: list[str] = []
    for name, active in (
        ("chart", has_chart),
        ("timeline", has_timeline),
        ("comparison", has_comparison),
        ("diagram", has_diagram),
        ("quote", has_quote),
        ("team", has_team),
        ("stats", has_stats),
        ("image", has_image),
        ("features", has_features),
    ):
        if active:
            signals.append(name)
    return LayoutFeatures(
        intent=intent,
        raw_intent=raw_intent,
        layout_hint=layout_hint,
        purpose=purpose,
        word_count=word_count,
        bullet_count=len(bullets),
        avg_bullet_words=avg_bullet_words,
        has_chart=has_chart,
        has_timeline=has_timeline,
        has_comparison=has_comparison,
        has_diagram=has_diagram,
        has_quote=has_quote,
        has_team=has_team,
        has_stats=has_stats,
        has_image=has_image,
        wants_image=wants_image,
        has_features=has_features,
        template_kit_component=template_kit_component,
        density=_density(word_count, len(bullets), avg_bullet_words),
        position=_position(deck_index, deck_total),
        signals=tuple(signals),
    )


def _has_required(features: LayoutFeatures, requirement: str) -> bool:
    return {
        "chart": features.has_chart,
        "timeline": features.has_timeline,
        "comparison": features.has_comparison,
        "diagram": features.has_diagram,
        "quote": features.has_quote,
        "team": features.has_team,
        "stats": features.has_stats,
        "image": features.has_image,
        "features": features.has_features,
    }.get(requirement, False)


def _eligible(spec: LayoutSpec, features: LayoutFeatures) -> bool:
    if features.word_count < spec.min_words or features.word_count > spec.max_words:
        return False
    if features.bullet_count < spec.min_bullets or features.bullet_count > spec.max_bullets:
        return False
    if spec.requires and not all(_has_required(features, req) for req in spec.requires):
        return False
    return True


def _density_score(spec: LayoutSpec, features: LayoutFeatures) -> float:
    if spec.density:
        return 10.0 if features.density in spec.density else -4.0
    target = (spec.min_words + spec.max_words) / 2
    span = max(spec.max_words - spec.min_words, 1)
    distance = abs(features.word_count - target) / span
    return max(0.0, 10.0 - distance * 18.0)


def _repeat_penalty(spec: LayoutSpec, previous_layouts: Sequence[str]) -> float:
    if not previous_layouts:
        return 0.0
    penalty = 0.0
    last_key = previous_layouts[-1]
    last_kit = last_key.split(":", 1)[0]
    if last_key == spec.key:
        penalty += 18.0
    elif last_kit == spec.kit_id:
        penalty += 6.0
    if len(previous_layouts) >= 2:
        recent = list(previous_layouts[-2:])
        if recent.count(spec.key) == 2:
            penalty += 28.0
        if all(item.split(":", 1)[0] == spec.kit_id for item in recent):
            penalty += 12.0
    return penalty


def _score_spec(spec: LayoutSpec, features: LayoutFeatures, previous_layouts: Sequence[str], template_id: str | None = None) -> tuple[float, list[str]]:
    score = 42.0
    reasons: list[str] = []
    template_kit = features.template_kit_component
    if template_kit:
        preferred_kits = _TEMPLATE_KIT_TO_LAYOUT_KITS.get(template_kit, (template_kit,))
        if spec.kit_id in preferred_kits:
            score += 22.0
            reasons.append(f"template-kit:{template_kit}")
    if template_id and getattr(spec, 'template_ids', None):
        if template_id in spec.template_ids:
            score += 16.0
            reasons.append(f"template:{template_id}")
        else:
            score -= 4.0
            reasons.append("template-mismatch")
    if features.intent and features.intent in spec.intents:
        score += 26.0
        reasons.append(f"intent:{features.intent}")
    elif spec.intents and any(token and token in features.intent for token in spec.intents):
        score += 12.0
        reasons.append("partial-intent")

    if spec.layout_keywords and any(keyword in features.layout_hint for keyword in spec.layout_keywords):
        score += 18.0
        reasons.append("layout-hint")
    if spec.positions and features.position in spec.positions:
        score += 10.0
        reasons.append(f"position:{features.position}")
    if spec.purposes and features.purpose in spec.purposes:
        score += 7.0
        reasons.append(f"purpose:{features.purpose}")
    for req in spec.requires:
        score += 9.0
        reasons.append(f"requires:{req}")
    for pref in spec.prefers:
        if _has_required(features, pref):
            score += 5.0
            reasons.append(f"prefers:{pref}")
    score += _density_score(spec, features)
    # v2: composition quality bonus for premium kits
    if spec.kit_id in {"CinematicHero", "GlassCard", "EditorialImage", "BentoGrid"}:
        comp = score_composition(
            kit_id=spec.kit_id,
            variant=spec.variant,
            content_density=_density_float(features.word_count, features.bullet_count, features.avg_bullet_words),
            has_image=features.has_image,
            element_count=features.bullet_count + (1 if features.has_chart else 0) + (1 if features.has_stats else 0),
        )
        comp_bonus = comp.overall * 6.0  # up to +6 points for excellent composition
        score += comp_bonus
        reasons.append(f"composition:+{comp_bonus:.1f}")
    penalty = _repeat_penalty(spec, previous_layouts)
    if penalty:
        score -= penalty
        reasons.append(f"diversity:-{int(penalty)}")
    return score, reasons


def _fallback_candidate(features: LayoutFeatures) -> LayoutCandidate:
    if features.has_stats:
        kit_id, variant = "StatHero", "kpi-strip"
    elif features.has_features:
        kit_id, variant = "FeatureGrid", "capabilities-scan"
    elif features.has_image:
        kit_id, variant = "FullBleedImage", "editorial-bleed-left"
    else:
        kit_id, variant = "TitleHero", "thesis-left"
    return LayoutCandidate(
        kit_id=kit_id,
        layout_variant=variant,
        score=30.0,
        rationale="fallback from available content signals",
        features=features,
    )


def select_layout(
    *,
    slide: Any,
    deck_purpose: str = "",
    deck_index: int = 0,
    deck_total: int = 1,
    previous_layouts: Sequence[str] = (),
    image_available: bool | None = None,
    template_id: str | None = None,
) -> LayoutCandidate:
    candidates = select_layout_candidates(
        slide=slide,
        deck_purpose=deck_purpose,
        deck_index=deck_index,
        deck_total=deck_total,
        previous_layouts=previous_layouts,
        image_available=image_available,
        template_id=template_id,
        limit=1,
    )
    return candidates[0]


def select_layout_candidates(
    *,
    slide: Any,
    deck_purpose: str = "",
    deck_index: int = 0,
    deck_total: int = 1,
    previous_layouts: Sequence[str] = (),
    image_available: bool | None = None,
    template_id: str | None = None,
    limit: int = 3,
) -> list[LayoutCandidate]:
    features = extract_features(
        slide,
        deck_purpose=deck_purpose,
        deck_index=deck_index,
        deck_total=deck_total,
        image_available=image_available,
    )
    scored: list[tuple[float, int, LayoutSpec, list[str]]] = []
    for index, spec in enumerate(LAYOUT_LIBRARY):
        if not _eligible(spec, features):
            continue
        score, reasons = _score_spec(spec, features, previous_layouts, template_id=template_id)
        scored.append((score, index, spec, reasons))
    if not scored:
        return [_fallback_candidate(features)]
    out: list[LayoutCandidate] = []
    for score, _, spec, reasons in sorted(scored, key=lambda item: (item[0], -item[1]), reverse=True):
        rationale = ", ".join(reasons[:5]) or "best density and rhythm fit"
        out.append(LayoutCandidate(
            kit_id=spec.kit_id,
            layout_variant=spec.variant,
            score=score,
            rationale=rationale,
            features=features,
        ))
        if len(out) >= max(1, limit):
            break
    return out
