"""V4 slide → CompiledSlide adapter (template-bound v1).

This module is the bridge between the V4 content pipeline's
`GeneratedSlide` dataclass and the sandbox's `CompiledSlide` wire
shape declared in `lliveupdatedstreaming/src/lib/sandboxProtocol.ts`.

Design decisions:
- Template-bound ONLY. We never emit freeform JSX in v1 — every slide
  maps to one of the 10 kit components with a JSON `/* PROPS */`
  fence consumed by `SlideRuntime.parsePropsFromJsx()`.
- Zero LLM calls. This is a pure data transform. Deterministic,
  testable, fast (<5ms per slide).
- All kit component names and prop shapes MUST match the kit modules
  under `lliveupdatedstreaming/sandbox/src/kit/`. Any mismatch here
  surfaces as a "slide compile error" in the sandbox frame.
- Intent → kit mapping chooses the BEST visual for the slide's
  dominant content. If a slide has both bullets and a chart, we
  prefer ChartBlock (data beats text).
- Imagery: we pass `imageUrl` through when the image pipeline has
  already resolved it. If the image is still generating, we emit an
  image-less variant and the frontend patches it in when the
  `slide_image_ready` event arrives.

Security: `_js_string(value)` JSON-encodes every embedded string so
a malicious headline like `</script><script>alert(1)` cannot escape
the PROPS block. The sandbox consumes PROPS via `JSON.parse`, not
`eval`.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Optional

from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4 import content_rules
from app.services.v4.animation_ir import build_animation_ir
from app.services.v4.html_transformer import build_html_css_js
from app.services.v4.engine_transformer import build_engine
from app.services.v4.reveal_legacy_transformer import build_reveal_legacy
from app.services.v4.layout.intent_engine import LayoutCandidate, select_layout
from app.services.v4.layout.rhythm_planner import plan_layout_rhythm
from app.config import settings

# ── v3-final Phase 1 — multi-target artifacts schema ────────────────
# Day 1 lands the wire-shape; only `artifacts.kit_jsx` is populated in
# this commit (from existing real data — never dummy values). The
# other three slots stay `None` until their owning phase ships:
#     html_css_js  → Phase 4  (HTML transformer, Day 6-7)
#     engine       → Phase 5  (Custom Presentation Engine, Day 9-10)
#     reveal_legacy→ Phase 5  (Reveal-legacy section, Day 9-10)
# `quality_score` stays `None` until Phase 4.5 (Day 8) populates it.
# `enrichment`     stays `None` until Phase 7.5 (Day 15).
# Keeping `None` (not empty stubs) makes "is this artifact ready?"
# trivially detectable in downstream callers — no truthiness traps.

# Bumped on every recompile of a slide; used as the cache key in the
# frontend useCompiledDeck hook (Phase 7) and as the artifact-freshness
# token for the upcoming hot-swap WS event (Phase 6).
_ARTIFACT_SCHEMA_VERSION = 1

# ── Kit component names (MUST stay in sync with
#     lliveupdatedstreaming/sandbox/src/kit/index.ts)  ──────────────

KIT_TITLE_HERO = "TitleHero"
KIT_STAT_HERO = "StatHero"
KIT_CHART_BLOCK = "ChartBlock"
KIT_TIMELINE_BLOCK = "TimelineBlock"
KIT_COMPARISON_BLOCK = "ComparisonBlock"
KIT_FEATURE_GRID = "FeatureGrid"
KIT_TEAM_GRID = "TeamGrid"
KIT_QUOTE_BLOCK = "QuoteBlock"
KIT_FULL_BLEED_IMAGE = "FullBleedImage"
KIT_DIAGRAM_BLOCK = "DiagramBlock"

_KIT_SET = {
    KIT_TITLE_HERO,
    KIT_STAT_HERO,
    KIT_CHART_BLOCK,
    KIT_TIMELINE_BLOCK,
    KIT_COMPARISON_BLOCK,
    KIT_FEATURE_GRID,
    KIT_TEAM_GRID,
    KIT_QUOTE_BLOCK,
    KIT_FULL_BLEED_IMAGE,
    KIT_DIAGRAM_BLOCK,
}


# ── Intent canonicalization ────────────────────────────────────────
# Real writer output uses free-form intent verbs in standard mode
# ("Introduction", "Introduce", "Explore", "Inform", "Engage",
# "Conclude") and canonical YC slugs in premium mode ("title",
# "problem", "market", "team"). The dispatcher only understands YC
# slugs, so free-form intents fall through to FeatureGrid — which is
# the exact template-stamp failure mode. Canonicalize here so both
# tiers reach the right kit.

_INTENT_ALIASES: dict[str, str] = {
    # title / cover
    "introduction": "title",
    "introductions": "title",
    "introduce": "title",
    "intro": "title",
    "opener": "title",
    "cover": "title",
    "welcome": "title",
    "title": "title",
    # closing family
    "conclude": "closing",
    "conclusion": "closing",
    "closing": "closing",
    "wrap-up": "closing",
    "wrap up": "closing",
    "thanks": "thanks",
    "thank you": "thanks",
    "ask": "ask",
    "call-to-action": "ask",
    "call to action": "ask",
    # team
    "team": "team",
    "the team": "team",
    "founders": "team",
    "leadership": "team",
    # metrics / traction
    "traction": "traction",
    "metrics": "metrics",
    "kpi": "metrics",
    "kpis": "metrics",
    "highlight": "metrics",
    "highlights": "metrics",
}


def _canonical_intent(raw: Optional[str]) -> str:
    if not raw:
        return ""
    key = raw.strip().lower()
    return _INTENT_ALIASES.get(key, key)


# ── Public API ────────────────────────────────────────────────────


def compile_slides(
    *,
    slides: list[GeneratedSlide],
    image_urls: Optional[Mapping[int, str]] = None,
    deck_title: Optional[str] = None,
    company_icon_url: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Turn a list of GeneratedSlide → list of CompiledSlide dicts.

    `image_urls` is an optional map of slide_index → resolved image
    URL. Slides whose index is not present in the map are compiled
    without an image (and will be patched later by the frontend when
    `slide_image_ready` arrives over the SSE stream).
    """
    image_urls = image_urls or {}
    clean_deck_title = _display_title(deck_title)
    compiled: list[dict[str, Any]] = []
    selected_layouts: list[str] = []
    deck_total = len(slides)
    rhythm_plan: dict[int, LayoutCandidate] = {}
    if settings.ENABLE_LAYOUT_RHYTHM_GATE and deck_total > 1:
        try:
            rhythm_plan = plan_layout_rhythm(
                slides=slides,
                deck_purpose=getattr(slides[0], "purpose", "") if slides else "",
                image_urls=image_urls,
            )
        except Exception:
            rhythm_plan = {}
    for deck_index, s in enumerate(slides):
        image_url = image_urls.get(s.index)
        compiled_slide = _compile_one(
            slide=s,
            image_url=image_url,
            deck_title=clean_deck_title,
            company_icon_url=company_icon_url or s.company_icon_url,
            deck_index=deck_index,
            deck_total=deck_total,
            previous_layouts=tuple(selected_layouts),
            layout_candidate=rhythm_plan.get(s.index),
        )
        layout_key = (compiled_slide.get("layout_intent") or {}).get("key")
        if isinstance(layout_key, str) and layout_key:
            selected_layouts.append(layout_key)
        compiled.append(compiled_slide)
    return compiled


_TITLE_LABEL_LINE = re.compile(
    r"^\s*(topic|audience|goal|context|purpose|brief|ask|stage)\s*:",
    re.IGNORECASE,
)


def _display_title(raw: Optional[str]) -> Optional[str]:
    """Return a display-friendly deck title.

    - Strip leading ``Topic:/Audience:/Goal:`` label lines — those describe
      the brief, not the deck.
    - Collapse internal newlines/whitespace.
    - Cap at 120 chars on a word boundary (no mid-word ellipsis).
    """
    if not raw:
        return raw
    text = str(raw).replace("\r", "\n")
    kept: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or _TITLE_LABEL_LINE.match(stripped):
            continue
        kept.append(stripped)
    cleaned = " ".join(kept) if kept else " ".join(text.split())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:-")
    if not cleaned:
        return None
    if len(cleaned) <= 120:
        return cleaned
    cut = cleaned[:120].rsplit(" ", 1)[0]
    return (cut or cleaned[:120]).rstrip(" ,;:-") + "…"


def compile_slide(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str] = None,
    deck_title: Optional[str] = None,
    company_icon_url: Optional[str] = None,
) -> dict[str, Any]:
    """Single-slide convenience wrapper (used by incremental patches)."""
    return _compile_one(
        slide=slide,
        image_url=image_url,
        deck_title=deck_title,
        company_icon_url=company_icon_url or slide.company_icon_url,
    )


# ── Internal ──────────────────────────────────────────────────────


def _compile_one(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
    deck_index: int = 0,
    deck_total: int = 1,
    previous_layouts: tuple[str, ...] = (),
    layout_candidate: Optional[LayoutCandidate] = None,
) -> dict[str, Any]:
    if layout_candidate is None:
        layout_candidate = select_layout(
            slide=slide,
            deck_purpose=getattr(slide, "purpose", "") or "",
            deck_index=deck_index,
            deck_total=deck_total,
            previous_layouts=previous_layouts,
            image_available=bool(image_url),
        )
    kit, props = _choose_kit_and_props(
        slide=slide,
        image_url=image_url,
        deck_title=deck_title,
        company_icon_url=company_icon_url,
        layout_candidate=layout_candidate,
    )
    assert kit in _KIT_SET, f"internal: kit {kit!r} not in registry"

    pending_image = _image_pending(slide=slide, image_url=image_url)
    if pending_image:
        props["pendingImage"] = True
        image_intent = getattr(slide, "image_intent", None) or (slide.render_decision or {}).get("renderer")
        if image_intent:
            props["imageIntent"] = str(image_intent)

    # Uniformly attach grounding sources so every kit can render a
    # "Sources" footer. Only include when the slide actually has citations;
    # otherwise leave the prop absent (kits treat missing sources as hidden).
    sources = _sources_from_slide(slide)
    if sources:
        props["sources"] = sources

    slide_id = f"slide-{slide.index:03d}"
    jsx = _render_jsx(kit=kit, props=props)

    # Phase 3 (Day 4-5) — unified AnimationIR feeds all four targets.
    # Built deterministically from the legacy animation_plan; stored
    # both at the top level (legacy back-compat) AND on every artifact
    # blob so transformers don't need to re-derive it.
    animation_plan = _default_animation_plan(
        intent=slide.intent,
        layout=slide.layout or "",
        kit=kit,
    )
    animation_ir = build_animation_ir(animation_plan)

    # Phase 1 — populate artifacts.kit_jsx from real generation output.
    # The other three artifact slots stay None until their owning phase
    # ships (see header comment for the schedule).
    kit_jsx_artifact = {
        "source": jsx,
        "kit_component": kit,
        "layout_intent": {
            **layout_candidate.to_dict(),
            "key": layout_candidate.key,
            "resolved_kit": kit,
        },
        # Deep-copy props so downstream mutation (e.g. image patching)
        # does not corrupt the cached artifact.
        "props_json": json.loads(json.dumps(props, ensure_ascii=False)),
        # 12-char SHA1 prefix is enough to disambiguate cache entries
        # without bloating the wire payload.
        "fingerprint": hashlib.sha1(jsx.encode("utf-8")).hexdigest()[:12],
    }

    # Phase 4 (Day 6-7) — HTML/CSS/JS transformer artifact.
    # Built deterministically from the same (kit, props, animation_ir)
    # tuple. design_system is left out at this level because the
    # snapshot lives at deck scope; content_pipeline wraps each compiled
    # slide with the snapshot's CSS during the post-compile pass.
    html_css_js_artifact = build_html_css_js(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
        deck_title=deck_title,
    )

    # Phase 5 (Day 9-10) — Custom engine artifact (T1 preview ops).
    engine_artifact = build_engine(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )

    # Phase 5 (Day 9-10) — Reveal-legacy artifact (legacy HTML export).
    reveal_legacy_artifact = build_reveal_legacy(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )

    return {
        "slide_id": slide_id,
        "slide_index": slide.index,
        # Legacy mirror — top-level `jsx_source` continues to feed the
        # current sandbox runtime path. Removed in a later release once
        # all consumers read from `artifacts.kit_jsx.source`.
        "jsx_source": jsx,
        "imports": {"@kit": "1.0.0"},
        "assets": _collect_assets(slide=slide, image_url=image_url),
        "pending_image": pending_image,
        "layout_intent": {
            **layout_candidate.to_dict(),
            "key": layout_candidate.key,
            "resolved_kit": kit,
        },
        "animation_plan": animation_plan,
        "animation_ir": animation_ir,
        "kit_component": kit,
        # ── v3-final Phase 1 schema additions ──────────────────────
        "artifacts": {
            "kit_jsx": kit_jsx_artifact,
            "html_css_js": html_css_js_artifact,  # Phase 4 (Day 6-7) ✓
            "engine": engine_artifact,            # Phase 5 (Day 9-10) ✓
            "reveal_legacy": reveal_legacy_artifact,  # Phase 5 (Day 9-10) ✓
        },
        "artifact_version": _ARTIFACT_SCHEMA_VERSION,
        # FK to the deck-level design system (Phase 2, Day 2). Filled by
        # content_pipeline once Phase 2 lands; until then None is the
        # honest answer.
        "design_system_version": None,
        # Phase 5 Quality Gate (Day 8+).
        "quality_score": _compute_quality_score(
            slide=slide, kit=kit, props=props,
            image_url=image_url or "", animation_ir=animation_ir
        ),
        # Filled by Phase 7.5 RAG enrichment (Day 15) when a slide
        # contains data placeholders that get web-search-resolved.
        "enrichment": None,
    }


# ── Phase 5: Quality Gate Implementation ────────────────────────────

def _compute_quality_score(
    *,
    slide: GeneratedSlide,
    kit: str,
    props: Mapping[str, Any],
    image_url: str,
    animation_ir: Optional[Any] = None,
) -> Optional[float]:
    """Compute quality score (0-10) for compiled slide.
    
    Returns None if quality check is disabled or not applicable.
    Scores:
      - 10.0 = Perfect (all checks pass)
      - 7.0+ = Good (minor issues)
      - 4.0+ = Acceptable (some issues)
      - < 4.0 = Poor (major issues)
    """
    score = 10.0
    issues: list[str] = []

    # 1. Content density check
    headline = (props.get("headline") or "").strip()
    body = (props.get("body_text") or "").strip()
    bullets = props.get("bullets") or []
    has_chart = bool(props.get("chartData"))
    has_image = bool(image_url)

    if not headline:
        issues.append("MISSING_HEADLINE")
        score -= 2.0
    
    if not body and not bullets and not has_chart:
        issues.append("LOW_CONTENT")
        score -= 1.5
    
    # 2. Image-content alignment (Phase 3C)
    image_intent = getattr(slide, "image_intent", None)
    if image_intent and not has_image:
        issues.append("IMAGE_MISSING_FOR_INTENT")
        score -= 1.5
    
    if has_image and headline:
        # Basic check: image should relate to headline
        headline_lower = headline.lower()
        if any(word in headline_lower for word in ["chart", "graph", "data", "metric"]):
            if "chart" not in image_url.lower() and "graph" not in image_url.lower():
                issues.append("IMAGE_CONTENT_MISMATCH")
                score -= 1.0
    
    # 3. Layout rhythm check (Phase 2B)
    # Check for 16:9 compliance using passed animation_ir
    if animation_ir:
        canvas = (animation_ir if isinstance(animation_ir, dict) else {}).get("canvas", {})
        width = canvas.get("width", 0)
        height = canvas.get("height", 0)
        if width > 0 and height > 0:
            ratio = width / height
            expected = 16.0 / 9.0
            if abs(ratio - expected) > 0.05:  # > 5% deviation
                issues.append("NOT_16_9")
                score -= 1.0
    
    # 4. "Numbers Don't Lie" rule (Phase 3B)
    if image_intent and "stat" in str(image_intent).lower():
        has_numbers = any(char.isdigit() for char in headline)
        if not has_numbers:
            issues.append("NUMBERS_RULE_VIOLATION")
            score -= 1.5
    
    # 5. Design system compliance
    if "fontSize" in props:
        font_size = props["fontSize"]
        if isinstance(font_size, (int, float)) and font_size < 16:
            issues.append("FONT_TOO_SMALL")
            score -= 0.5
    
    # Clamp score
    score = max(0.0, min(10.0, score))
    
    # Log issues for debugging
    if issues:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Quality gate: score={score:.1f}, issues={issues}")
    
    return round(score, 1)





def _render_jsx(*, kit: str, props: Mapping[str, Any]) -> str:
    """Emit the template-bound JSX source.

    Format consumed by `SlideRuntime.parsePropsFromJsx()`:
        /* PROPS
        {...JSON...}
        */
        import { <Kit> } from "@kit";
        export default function Slide(props) { return <Kit {...props} />; }
    """
    # sort_keys → deterministic output; stable output hashing for
    # caching / cache-busting in the sandbox.
    props_json = json.dumps(props, indent=2, sort_keys=True, ensure_ascii=False).replace("*/", "*\\/")
    return (
        "/* PROPS\n"
        f"{props_json}\n"
        "*/\n"
        f'import {{ {kit} }} from "@kit";\n'
        "export default function Slide(props) {\n"
        f"  return <{kit} {{...props}} />;\n"
        "}\n"
    )


def _collect_assets(
    *, slide: GeneratedSlide, image_url: Optional[str]
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    if image_url:
        assets.append(
            {
                "kind": "image",
                "id": f"slide-{slide.index}-primary",
                "url": image_url,
                "alt": (slide.image_prompt or slide.headline or "")[:200],
            }
        )
    if slide.company_icon_url:
        assets.append(
            {
                "kind": "logo",
                "id": "company-logo",
                "url": slide.company_icon_url,
                "alt": "company logo",
            }
        )
    return assets


def _image_pending(*, slide: GeneratedSlide, image_url: Optional[str]) -> bool:
    if image_url:
        return False
    decision = getattr(slide, "render_decision", None) or {}
    return str(decision.get("modality") or "").lower() == "image"


def _sources_from_slide(slide: GeneratedSlide, max_n: int = 4) -> list[dict[str, str]]:
    """Compile the slide's grounding citations into the display ``sources`` shape.

    The writer stores citations as ``[{'url': ..., 'title': ...}]`` or raw
    URLs. We normalise, de-duplicate on hostname+path, and clip to ``max_n``.
    Every kit component's props include this array so the sandbox can render
    a small "Sources" footer with clickable links — critical for investor
    trust and for meeting the critic's citation-presence rule.
    """
    raw = getattr(slide, "citations", None) or []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        url: Optional[str] = None
        title: Optional[str] = None
        if isinstance(item, str):
            url = item
        elif isinstance(item, Mapping):
            url = str(item.get("url") or item.get("href") or "").strip() or None
            title = str(item.get("title") or item.get("name") or "").strip() or None
        if not url:
            continue
        key = re.sub(r"[#?].*$", "", url).lower()
        if key in seen:
            continue
        seen.add(key)
        entry: dict[str, str] = {"url": url[:500]}
        if title:
            entry["title"] = title[:160]
        else:
            # Derive a short label from the hostname when the writer didn't
            # provide a title.
            try:
                host = re.sub(r"^https?://(www\.)?", "", url).split("/", 1)[0]
                if host:
                    entry["title"] = host[:80]
            except Exception:  # noqa: BLE001
                pass
        out.append(entry)
        if len(out) >= max_n:
            break
    return out


def _default_animation_plan(*, intent: str, layout: str = "", kit: str = "") -> dict[str, Any]:
    """Produce a deterministic, intent-aware animation plan.

    The frontend sandbox ``SlideRuntime`` consumes this map and drives Motion
    One / Framer Motion entry/emphasis/hover/exit primitives. Empty arrays
    used to render static slides; now every slide ships with tuned defaults
    so the deck feels alive without any LLM call.
    """
    intent_key = (intent or "").lower()
    layout_key = (layout or "").lower()
    kit_key = (kit or "").strip()

    transition = "fade"
    if intent_key in {"traction", "metrics", "financials"}:
        transition = "slide"
    elif intent_key in {"vision", "title", "thanks", "cover"}:
        transition = "zoom"
    elif intent_key in {"how_it_works", "process"}:
        transition = "wipe"

    # Entry choreography per kit component. Stagger delays are multiples of 80ms
    # to stay under the 400ms perceived-instant threshold.
    entry: list[dict[str, Any]] = []
    if kit_key == "TitleHero":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 520, "delay_ms": 80,  "easing": "ease-out"},
            {"target": "subheadline",  "effect": "fade-up",    "duration_ms": 480, "delay_ms": 240, "easing": "ease-out"},
            {"target": "eyebrow",      "effect": "fade",       "duration_ms": 360, "delay_ms": 40,  "easing": "linear"},
        ]
    elif kit_key == "StatHero":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 440, "delay_ms": 80,  "easing": "ease-out"},
            {"target": "subheadline",  "effect": "fade",       "duration_ms": 360, "delay_ms": 200, "easing": "linear"},
            {"target": "stats",        "effect": "count-up",   "duration_ms": 900, "delay_ms": 320, "stagger_ms": 120, "easing": "ease-out"},
        ]
    elif kit_key == "ChartBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "chart",        "effect": "draw",       "duration_ms": 900, "delay_ms": 240, "easing": "ease-in-out"},
        ]
    elif kit_key == "FeatureGrid":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "features",     "effect": "fade-up",    "duration_ms": 420, "delay_ms": 200, "stagger_ms": 80,  "easing": "ease-out"},
        ]
    elif kit_key == "TeamGrid":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "members",      "effect": "fade-up",    "duration_ms": 460, "delay_ms": 200, "stagger_ms": 100, "easing": "ease-out"},
        ]
    elif kit_key == "DiagramBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "nodes",        "effect": "pop",        "duration_ms": 360, "delay_ms": 200, "stagger_ms": 100, "easing": "ease-out"},
            {"target": "edges",        "effect": "draw",       "duration_ms": 600, "delay_ms": 600, "easing": "ease-in-out"},
        ]
    elif kit_key == "TimelineBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "milestones",   "effect": "slide-in",   "duration_ms": 420, "delay_ms": 200, "stagger_ms": 120, "easing": "ease-out"},
        ]
    elif kit_key == "ComparisonBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "columns",      "effect": "fade-up",    "duration_ms": 420, "delay_ms": 200, "stagger_ms": 140, "easing": "ease-out"},
        ]
    elif kit_key == "QuoteBlock":
        entry = [
            {"target": "quote",        "effect": "fade-up",    "duration_ms": 560, "delay_ms": 120, "easing": "ease-out"},
            {"target": "attribution",  "effect": "fade",       "duration_ms": 360, "delay_ms": 520, "easing": "linear"},
        ]
    elif kit_key == "FullBleedImage":
        entry = [
            {"target": "image",        "effect": "ken-burns",  "duration_ms": 7000, "delay_ms": 0,   "easing": "ease-in-out"},
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 520,  "delay_ms": 240, "easing": "ease-out"},
        ]

    emphasis: list[dict[str, Any]] = []
    if kit_key == "StatHero":
        emphasis = [{"target": "stats", "effect": "pulse", "duration_ms": 600, "trigger": "on-enter"}]
    elif kit_key == "ChartBlock":
        emphasis = [{"target": "chart", "effect": "highlight-peak", "duration_ms": 600, "trigger": "on-visible"}]

    hover: list[dict[str, Any]] = []
    if kit_key in {"FeatureGrid", "TeamGrid", "ComparisonBlock"}:
        hover = [{"target": "card", "effect": "lift", "duration_ms": 180, "easing": "ease-out"}]

    exit_plan: list[dict[str, Any]] = [
        {"target": "all", "effect": "fade", "duration_ms": 220, "easing": "ease-in"},
    ]

    return {
        "entry": entry,
        "emphasis": emphasis,
        "hover": hover,
        "exit": exit_plan,
        "transition": transition,
    }


# ── Kit dispatcher ────────────────────────────────────────────────


def _choose_kit_and_props(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
    layout_candidate: LayoutCandidate,
) -> tuple[str, dict[str, Any]]:
    """Pick the best kit component for this slide and assemble its props.

    Plan 06 routes through the layout intent engine first. The engine is
    still bounded by the same hard validity gates as the old dispatcher:
    a ChartBlock needs chart data, a ComparisonBlock needs rows, and so on.
    If a candidate cannot be rendered safely, we fall back to the previous
    structured-content priority order.
    """
    intent = _canonical_intent(slide.intent)
    layout = (getattr(slide, "layout", "") or "").lower()

    if intent == "team" and getattr(slide, "requires_user_input", False):
        return KIT_TEAM_GRID, _team_props(slide)

    chosen = _props_for_candidate(
        slide=slide,
        image_url=image_url,
        deck_title=deck_title,
        company_icon_url=company_icon_url,
        candidate=layout_candidate,
        layout=layout,
    )
    if chosen is not None:
        kit, props = chosen
        return kit, _apply_layout_variant_props(
            kit=kit,
            props=props,
            candidate=layout_candidate,
            image_url=image_url,
        )

    # Defensive fallback: explicit structured payloads take priority over
    # intent tags if the candidate was not renderable.
    if slide.team_members:
        return KIT_TEAM_GRID, _apply_layout_variant_props(
            kit=KIT_TEAM_GRID, props=_team_props(slide), candidate=layout_candidate, image_url=image_url
        )
    if slide.chart and _chart_has_data(slide.chart):
        return KIT_CHART_BLOCK, _apply_layout_variant_props(
            kit=KIT_CHART_BLOCK, props=_chart_props(slide), candidate=layout_candidate, image_url=image_url
        )
    if slide.timeline and slide.timeline.get("events"):
        return KIT_TIMELINE_BLOCK, _apply_layout_variant_props(
            kit=KIT_TIMELINE_BLOCK, props=_timeline_props(slide), candidate=layout_candidate, image_url=image_url
        )
    # Founder replan — ComparisonBlock hard gate: MUST carry >= 2 rows across
    # its columns. A zero-row comparison renders as an empty box in the
    # sandbox and is worse than falling through to a different kit.
    if (
        slide.comparison
        and slide.comparison.get("columns")
        and content_rules.comparison_row_count(
            {"comparison": slide.comparison}
        ) >= 2
    ):
        return KIT_COMPARISON_BLOCK, _apply_layout_variant_props(
            kit=KIT_COMPARISON_BLOCK, props=_comparison_props(slide), candidate=layout_candidate, image_url=image_url
        )
    if slide.diagram and slide.diagram.get("nodes"):
        return KIT_DIAGRAM_BLOCK, _apply_layout_variant_props(
            kit=KIT_DIAGRAM_BLOCK, props=_diagram_props(slide), candidate=layout_candidate, image_url=image_url
        )
    if slide.quote and slide.quote.get("text"):
        return KIT_QUOTE_BLOCK, _apply_layout_variant_props(
            kit=KIT_QUOTE_BLOCK, props=_quote_props(slide), candidate=layout_candidate, image_url=image_url
        )
    # Founder replan — StatHero hard gate: at least one stat block MUST have
    # a non-empty value, else the kit renders as empty chrome.
    if slide.stat_blocks and any(
        isinstance(b, dict) and str(b.get("value") or "").strip()
        for b in slide.stat_blocks
    ):
        return KIT_STAT_HERO, _apply_layout_variant_props(
            kit=KIT_STAT_HERO, props=_stat_props(slide), candidate=layout_candidate, image_url=image_url
        )

    # 1b. LAYOUT-HINT RESCUE — writers often encode structural intent in
    # the `layout` string ("Quote with background image", "Step-by-step
    # guide", "Competitive matrix", "Revenue projection") but fail to
    # populate the corresponding structured field. We detect these
    # hints and synthesize structure from body/bullets so the deck
    # doesn't collapse into a wall of FeatureGrids.
    rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
    if rescued is not None:
        kit, props = rescued
        return kit, _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 2. Intent-driven fallbacks.
    if intent in {"title", "cover"}:
        return KIT_TITLE_HERO, _apply_layout_variant_props(
            kit=KIT_TITLE_HERO,
            props=_title_props(
            slide=slide,
            image_url=image_url,
            deck_title=deck_title,
            company_icon_url=company_icon_url,
            ),
            candidate=layout_candidate,
            image_url=image_url,
        )
    if intent == "team":
        return KIT_TEAM_GRID, _apply_layout_variant_props(
            kit=KIT_TEAM_GRID, props=_team_props(slide), candidate=layout_candidate, image_url=image_url
        )
    if intent in {"thanks", "ask", "closing"} and image_url:
        return KIT_FULL_BLEED_IMAGE, _apply_layout_variant_props(
            kit=KIT_FULL_BLEED_IMAGE,
            props=_full_bleed_props(slide=slide, image_url=image_url),
            candidate=layout_candidate,
            image_url=image_url,
        )

    # 2c. Numeric bullets → StatHero (promotes "87% reduction / $2.4B TAM"
    # out of a bullet list into a big-number block).
    promoted_stats = _promote_numeric_bullets(slide.bullets)
    if promoted_stats and len(promoted_stats) >= 2:
        return KIT_STAT_HERO, _apply_layout_variant_props(
            kit=KIT_STAT_HERO,
            props={
            "headline": slide.headline or "",
            "stats": promoted_stats,
            **({"subheadline": slide.subheadline} if slide.subheadline else {}),
            },
            candidate=layout_candidate,
            image_url=image_url,
        )

    # 3. Bullets → FeatureGrid if they look like features (short),
    #    otherwise keep them in a TitleHero-style layout.
    if slide.bullets and _looks_like_feature_list(slide.bullets):
        return KIT_FEATURE_GRID, _apply_layout_variant_props(
            kit=KIT_FEATURE_GRID, props=_feature_grid_props(slide), candidate=layout_candidate, image_url=image_url
        )

    # 4. Image-forward slide with no richer structure.
    if (image_url or _image_pending(slide=slide, image_url=image_url)) and not slide.bullets and not slide.body:
        return KIT_FULL_BLEED_IMAGE, _apply_layout_variant_props(
            kit=KIT_FULL_BLEED_IMAGE,
            props=_full_bleed_props(slide=slide, image_url=image_url),
            candidate=layout_candidate,
            image_url=image_url,
        )

    # 5. Last resort: TitleHero absorbs any content-light slide.
    return KIT_TITLE_HERO, _apply_layout_variant_props(
        kit=KIT_TITLE_HERO,
        props=_title_props(
        slide=slide,
        image_url=image_url,
        deck_title=deck_title,
        company_icon_url=company_icon_url,
        ),
        candidate=layout_candidate,
        image_url=image_url,
    )


def _props_for_candidate(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
    candidate: LayoutCandidate,
    layout: str,
) -> Optional[tuple[str, dict[str, Any]]]:
    kit = candidate.kit_id
    if kit == KIT_TEAM_GRID and slide.team_members:
        return kit, _team_props(slide)
    if kit == KIT_CHART_BLOCK and slide.chart and _chart_has_data(slide.chart):
        return kit, _chart_props(slide)
    if kit == KIT_TIMELINE_BLOCK:
        if slide.timeline and slide.timeline.get("events"):
            return kit, _timeline_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_TIMELINE_BLOCK:
            return rescued
    if kit == KIT_COMPARISON_BLOCK:
        if (
            slide.comparison
            and slide.comparison.get("columns")
            and content_rules.comparison_row_count({"comparison": slide.comparison}) >= 2
        ):
            return kit, _comparison_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_COMPARISON_BLOCK:
            return rescued
    if kit == KIT_DIAGRAM_BLOCK:
        if slide.diagram and slide.diagram.get("nodes"):
            return kit, _diagram_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_DIAGRAM_BLOCK:
            return rescued
    if kit == KIT_QUOTE_BLOCK:
        if slide.quote and (slide.quote.get("text") or slide.quote.get("quote")):
            return kit, _quote_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_QUOTE_BLOCK:
            return rescued
    if kit == KIT_STAT_HERO:
        if slide.stat_blocks and any(isinstance(b, dict) and str(b.get("value") or "").strip() for b in slide.stat_blocks):
            return kit, _stat_props(slide)
        stats = _promote_numeric_bullets(slide.bullets)
        if stats:
            props: dict[str, Any] = {"headline": slide.headline or "", "stats": stats}
            if slide.subheadline:
                props["subheadline"] = slide.subheadline
            return kit, props
    if kit == KIT_FEATURE_GRID and slide.bullets and _looks_like_feature_list(slide.bullets):
        return kit, _feature_grid_props(slide)
    if kit == KIT_FULL_BLEED_IMAGE and (image_url or _image_pending(slide=slide, image_url=image_url)):
        return kit, _full_bleed_props(slide=slide, image_url=image_url)
    if kit == KIT_TITLE_HERO:
        strong_signals = {
            "chart", "timeline", "comparison", "diagram", "quote",
            "team", "stats", "features", "image",
        }
        if (
            candidate.features.intent not in {"title", "cover"}
            and strong_signals.intersection(candidate.features.signals)
        ):
            return None
        return kit, _title_props(
            slide=slide,
            image_url=image_url,
            deck_title=deck_title,
            company_icon_url=company_icon_url,
        )
    return None


def _apply_layout_variant_props(
    *,
    kit: str,
    props: dict[str, Any],
    candidate: LayoutCandidate,
    image_url: Optional[str],
) -> dict[str, Any]:
    variant = candidate.layout_variant
    if kit == KIT_STAT_HERO:
        if variant in {"centered-stat", "market-scale"} or len(props.get("stats") or []) == 1:
            props["align"] = "center"
    elif kit == KIT_TIMELINE_BLOCK:
        if variant in {"roadmap-vertical"}:
            props["orientation"] = "vertical"
        elif variant in {"roadmap-horizontal", "process-flow"}:
            props["orientation"] = "horizontal"
    elif kit == KIT_QUOTE_BLOCK:
        if variant in {"testimonial-accent"}:
            props["variant"] = "accent"
    elif kit == KIT_FULL_BLEED_IMAGE:
        if variant == "editorial-bleed-right":
            props["align"] = "bottom-right"
            props["overlay"] = "scrim-bottom"
        elif variant == "duotone-proof":
            props["overlay"] = "duotone"
            props["align"] = "center"
        else:
            props.setdefault("overlay", "scrim-bottom")
            props.setdefault("align", "bottom-left")
        if image_url:
            props["imageUrl"] = image_url
    elif kit == KIT_FEATURE_GRID:
        if variant in {"benefits-two-col", "issue-solution-grid"}:
            props["columns"] = 2
        elif variant == "feature-cards-4":
            props["columns"] = 4
        elif variant == "feature-cards-3":
            props["columns"] = 3
    return props


# ── Prop builders ─────────────────────────────────────────────────


def _title_props(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
) -> dict[str, Any]:
    variant = "image" if image_url else "gradient"
    eyebrow = (slide.purpose or "").replace("_", " ").upper() or None
    # Prefer deck_title as the footer for cover slides.
    footer = deck_title if (slide.intent or "").lower() in {"title", "cover"} else None
    props = {
        "headline": slide.headline or deck_title or "Untitled",
        "variant": variant,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    if eyebrow:
        props["eyebrow"] = eyebrow
    if footer:
        props["footer"] = footer
    if image_url:
        props["imageUrl"] = image_url
    if company_icon_url:
        props["logoUrl"] = company_icon_url
    return props


def _stat_props(slide: GeneratedSlide) -> dict[str, Any]:
    stats = []
    for sb in slide.stat_blocks[:4]:
        item: dict[str, Any] = {
            "value": str(sb.get("value") or sb.get("number") or ""),
            "label": str(sb.get("label") or sb.get("caption") or ""),
        }
        if sb.get("delta"):
            item["delta"] = str(sb["delta"])
        trend = sb.get("trend")
        if trend in {"up", "down", "flat"}:
            item["trend"] = trend
        stats.append(item)
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "stats": stats,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _chart_props(slide: GeneratedSlide) -> dict[str, Any]:
    chart = slide.chart or {}
    ctype_raw = str(chart.get("type") or "bar").lower()
    if ctype_raw not in {"bar", "line", "area", "pie", "radar"}:
        ctype_raw = "bar"
    data = chart.get("data") or []
    # Normalize to list[dict]. If the LLM produced [{x,y}] already, good.
    if data and isinstance(data[0], (list, tuple)):
        # [[label, value], ...] shape
        data = [{"name": str(r[0]), "value": float(r[1])} for r in data if len(r) >= 2]

    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "type": ctype_raw,
        "data": data,
        "xKey": str(chart.get("x_key") or chart.get("xKey") or "name"),
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    # Pie + radar use value/name keys; bar/line/area use y-keys.
    if ctype_raw in {"pie", "radar"}:
        props["valueKey"] = str(chart.get("value_key") or chart.get("valueKey") or "value")
        props["nameKey"] = props["xKey"]
    else:
        y_keys = chart.get("y_keys") or chart.get("yKeys") or ["value"]
        if isinstance(y_keys, str):
            y_keys = [y_keys]
        props["yKeys"] = list(y_keys)
        if chart.get("series_labels") or chart.get("seriesLabels"):
            props["seriesLabels"] = chart.get("series_labels") or chart.get("seriesLabels")
    if chart.get("source"):
        props["source"] = str(chart["source"])
    return props


def _timeline_props(slide: GeneratedSlide) -> dict[str, Any]:
    timeline = slide.timeline or {}
    events = timeline.get("events") or []
    milestones = []
    for e in events:
        m: dict[str, Any] = {
            "date": str(e.get("date") or e.get("when") or ""),
            "title": str(e.get("title") or e.get("name") or ""),
        }
        if e.get("description"):
            m["description"] = str(e["description"])
        if e.get("done") is True:
            m["done"] = True
        milestones.append(m)
    orientation = str(timeline.get("orientation") or "horizontal").lower()
    if orientation not in {"horizontal", "vertical"}:
        orientation = "horizontal"
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "orientation": orientation,
        "milestones": milestones,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _comparison_props(slide: GeneratedSlide) -> dict[str, Any]:
    cmp = slide.comparison or {}
    raw_cols = cmp.get("columns") or []
    # Two shapes seen in v4 output:
    #   (a) {columns:[{name, highlight?, rows:[{feature,value}]}]}
    #   (b) {columns:[{title, items:[...]}]} + optional features[]
    columns = []
    rows_by_feature: dict[str, dict[str, Any]] = {}
    features: list[str] = list(cmp.get("features") or [])

    for i, c in enumerate(raw_cols):
        col: dict[str, Any] = {"name": str(c.get("name") or c.get("title") or f"Column {i + 1}")}
        if c.get("highlight"):
            col["highlight"] = True
        if c.get("tagline"):
            col["tagline"] = str(c["tagline"])
        columns.append(col)

        # Shape (a): inline rows
        for row in c.get("rows") or []:
            feat = str(row.get("feature") or row.get("name") or "")
            if not feat:
                continue
            rows_by_feature.setdefault(feat, {"feature": feat, "values": [None] * len(raw_cols)})
            rows_by_feature[feat]["values"][i] = row.get("value")

        # Shape (b): items list implicitly mapped to features[]
        for j, item in enumerate(c.get("items") or []):
            if j >= len(features):
                continue
            feat = features[j]
            rows_by_feature.setdefault(feat, {"feature": feat, "values": [None] * len(raw_cols)})
            rows_by_feature[feat]["values"][i] = item

    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "columns": columns,
        "rows": list(rows_by_feature.values()),
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _diagram_props(slide: GeneratedSlide) -> dict[str, Any]:
    dg = slide.diagram or {}
    raw_nodes = dg.get("nodes") or []
    nodes = []
    node_ids = set()
    # Auto-layout fallback: spread nodes along a horizontal line if no
    # coordinates were provided.
    n = max(len(raw_nodes), 1)
    for i, raw in enumerate(raw_nodes):
        nid = str(raw.get("id") or f"n{i}")
        node_ids.add(nid)
        node: dict[str, Any] = {
            "id": nid,
            "label": str(raw.get("label") or raw.get("name") or nid),
            "x": float(raw.get("x")) if raw.get("x") is not None else (i + 1) / (n + 1),
            "y": float(raw.get("y")) if raw.get("y") is not None else 0.5,
        }
        if raw.get("variant") in {"primary", "secondary", "muted"}:
            node["variant"] = raw["variant"]
        nodes.append(node)

    edges = []
    for raw in dg.get("edges") or []:
        f = str(raw.get("from") or raw.get("source") or "")
        t = str(raw.get("to") or raw.get("target") or "")
        if f not in node_ids or t not in node_ids:
            continue
        edge: dict[str, Any] = {"from": f, "to": t}
        if raw.get("label"):
            edge["label"] = str(raw["label"])
        if raw.get("style") in {"solid", "dashed"}:
            edge["style"] = raw["style"]
        edges.append(edge)

    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "nodes": nodes,
        "edges": edges,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _quote_props(slide: GeneratedSlide) -> dict[str, Any]:
    q = slide.quote or {}
    props: dict[str, Any] = {
        "quote": str(q.get("text") or q.get("quote") or ""),
        "attribution": str(q.get("attribution") or q.get("author") or ""),
    }
    if q.get("role"):
        props["role"] = str(q["role"])
    if q.get("photo_url") or q.get("photoUrl"):
        props["photoUrl"] = str(q.get("photo_url") or q.get("photoUrl"))
    return props


def _team_props(slide: GeneratedSlide) -> dict[str, Any]:
    members = []
    for m in slide.team_members[:8]:
        tm: dict[str, Any] = {
            "name": str(m.get("name") or ""),
            "role": str(m.get("role") or ""),
        }
        if m.get("photo_url") and not m.get("is_default_avatar"):
            tm["photoUrl"] = str(m["photo_url"])
        if m.get("bio"):
            tm["bio"] = str(m["bio"])
        if m.get("linkedin_url"):
            tm["linkedInUrl"] = str(m["linkedin_url"])
        members.append(tm)

    # Column count: 2 members → 2, 3 → 3, 4-8 → 4.
    cols = 2 if len(members) <= 2 else (3 if len(members) == 3 else 4)
    props: dict[str, Any] = {
        "headline": slide.headline or "Team",
        "members": members,
        "columns": cols,
    }
    if getattr(slide, "requires_user_input", False):
        props["requiresUserInput"] = True
        if getattr(slide, "user_input_kind", None):
            props["userInputKind"] = str(slide.user_input_kind)
        if getattr(slide, "user_input_reason", None):
            props["userInputReason"] = str(slide.user_input_reason)
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _feature_grid_props(slide: GeneratedSlide) -> dict[str, Any]:
    features = []
    for b in slide.bullets[:6]:
        text = str(b).strip()
        if not text:
            continue
        # Try "Title — description" or "Title: description" split.
        title, _, desc = text.partition("—")
        if not desc:
            title, _, desc = text.partition(":")
        features.append(
            {
                "title": (title or text).strip(),
                "description": desc.strip() or None,
                # Icon hint based on simple keyword detection — the kit
                # falls back to a neutral Target icon when unknown.
                "icon": _guess_icon(title or text),
            }
        )
    cols = 2 if len(features) <= 2 else (3 if len(features) <= 3 else 4)
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "features": features,
        "columns": cols,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _full_bleed_props(
    *, slide: GeneratedSlide, image_url: Optional[str]
) -> dict[str, Any]:
    props: dict[str, Any] = {
        "overlay": "scrim-bottom",
        "align": "bottom-left",
    }
    if image_url:
        props["imageUrl"] = image_url
    if slide.headline:
        props["headline"] = slide.headline
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


# ── Small helpers ─────────────────────────────────────────────────


def _chart_has_data(chart: Mapping[str, Any]) -> bool:
    data = chart.get("data")
    return bool(data) and isinstance(data, list) and len(data) > 0


def _looks_like_feature_list(bullets: list[str]) -> bool:
    """Heuristic: short bullets (<14 words) → grid; long → prose."""
    if len(bullets) < 2:
        return False
    avg_words = sum(len(b.split()) for b in bullets) / max(len(bullets), 1)
    return avg_words <= 14 and len(bullets) <= 6


_ICON_HINTS = {
    # keyword substring → lucide icon name
    "growth": "TrendingUp",
    "revenue": "DollarSign",
    "users": "Users",
    "user": "User",
    "team": "Users",
    "security": "Shield",
    "secure": "Shield",
    "speed": "Zap",
    "fast": "Zap",
    "data": "Database",
    "ai": "Sparkles",
    "automation": "Cpu",
    "global": "Globe",
    "world": "Globe",
    "mobile": "Smartphone",
    "cloud": "Cloud",
    "chart": "BarChart3",
    "analytics": "BarChart3",
    "launch": "Rocket",
    "market": "Target",
    "feedback": "MessageSquare",
    "design": "Palette",
    "code": "Code2",
    "integration": "Plug",
    "money": "DollarSign",
    "cost": "DollarSign",
    "time": "Clock",
    "award": "Award",
    "star": "Star",
    "shield": "Shield",
}


def _guess_icon(text: str) -> str:
    lo = text.lower()
    for kw, icon in _ICON_HINTS.items():
        if kw in lo:
            return icon
    return "Target"


# ── Layout-hint rescue ────────────────────────────────────────────
# Writers routinely encode visual intent in the free-form `layout`
# string ("Quote with background image", "Step-by-step guide",
# "Competitive-matrix", "Revenue-projection") without populating the
# corresponding structured field. We keyword-scan the layout and
# reconstitute the visual from body + bullets so every deck ships with
# real visual diversity instead of 10 identical FeatureGrids.

_LAYOUT_QUOTE_HINTS = ("quote", "testimonial", "citation")
_LAYOUT_TIMELINE_HINTS = ("timeline", "step", "phase", "roadmap", "journey", "process", "milestone")
_LAYOUT_COMPARISON_HINTS = ("compar", "vs.", " vs ", "matrix", "versus", "side-by-side", "side by side")
_LAYOUT_DIAGRAM_HINTS = ("diagram", "flow", "architecture", "system map", "network")
_LAYOUT_STAT_HINTS = ("stat", "metric", "kpi", "big number", "big-number", "numbers")
_LAYOUT_IMAGE_FULL_HINTS = ("full-bleed", "full bleed", "hero image", "image-full", "image full", "background image")
_LAYOUT_TITLE_HINTS = ("title-only", "title only", "cover", "opener")


def _rescue_from_layout_and_bullets(
    *, slide: GeneratedSlide, layout: str
) -> Optional[tuple[str, dict[str, Any]]]:
    """Inspect `slide.layout` and content to rescue a premium kit when
    the writer failed to populate a structured field. Returns None if
    no rescue applies; caller then falls through to the normal path.

    Rescue priority (first match wins):
      1. Quote-layout + detectable quotation content → QuoteBlock
      2. Timeline/step layout + enumerated bullets → TimelineBlock
      3. Comparison/matrix layout + paired bullets → ComparisonBlock
      4. Stats/metric layout + numeric bullets → StatHero
      5. Full-bleed layout + image prompt → FullBleedImage (caller
         supplies image_url separately; rescue only fires when the
         writer EXPLICITLY asked for full-bleed)
      6. Title/cover layout → TitleHero
    """
    bullets = list(slide.bullets or [])
    body = (slide.body or "").strip()

    # 1. Quote rescue
    if any(h in layout for h in _LAYOUT_QUOTE_HINTS):
        q = _extract_quote(body=body, bullets=bullets)
        if q:
            return KIT_QUOTE_BLOCK, q

    # 2. Timeline rescue
    if any(h in layout for h in _LAYOUT_TIMELINE_HINTS):
        milestones = _extract_timeline(bullets=bullets, body=body)
        if len(milestones) >= 2:
            props: dict[str, Any] = {
                "headline": slide.headline or "",
                "orientation": "horizontal" if len(milestones) <= 5 else "vertical",
                "milestones": milestones,
            }
            if slide.subheadline:
                props["subheadline"] = slide.subheadline
            return KIT_TIMELINE_BLOCK, props

    # 3. Comparison rescue
    if any(h in layout for h in _LAYOUT_COMPARISON_HINTS):
        cmp_props = _extract_comparison(slide=slide, bullets=bullets)
        if cmp_props is not None:
            # Founder replan — hard gate: rescued comparison must have >= 2 rows.
            if content_rules.comparison_row_count(
                {"comparison": cmp_props}
            ) >= 2:
                return KIT_COMPARISON_BLOCK, cmp_props

    # 3b. Diagram rescue
    if any(h in layout for h in _LAYOUT_DIAGRAM_HINTS):
        diagram_props = _extract_diagram(slide=slide, bullets=bullets, body=body)
        if diagram_props is not None:
            return KIT_DIAGRAM_BLOCK, diagram_props

    # 4. Stats rescue
    if any(h in layout for h in _LAYOUT_STAT_HINTS):
        stats = _promote_numeric_bullets(bullets)
        if stats:
            props = {
                "headline": slide.headline or "",
                "stats": stats,
            }
            if slide.subheadline:
                props["subheadline"] = slide.subheadline
            return KIT_STAT_HERO, props

    # 5. Title rescue (only fires when the layout EXPLICITLY says so —
    # we never hijack a content slide into a TitleHero).
    if any(h in layout for h in _LAYOUT_TITLE_HINTS):
        # Fall back through to the normal title_props path by returning
        # a hint the caller understands. We can't call _title_props here
        # without the image_url/deck_title, so return None and let the
        # intent-path pick it up (index==0 catches cover anyway).
        return None

    return None


_QUOTE_RE = re.compile(r'["“”](.{8,240}?)["“”](?:\s*[—\-–]\s*(.{2,80}))?', re.DOTALL)


def _extract_quote(*, body: str, bullets: list[str]) -> Optional[dict[str, Any]]:
    """Pull a quote + attribution from body or bullets. Recognises
    curly + straight quotes and em-dash / hyphen attribution."""
    candidates: list[str] = []
    if body:
        candidates.append(body)
    candidates.extend(bullets)
    for text in candidates:
        m = _QUOTE_RE.search(text)
        if m:
            quote_text = m.group(1).strip()
            attrib = (m.group(2) or "").strip()
            out: dict[str, Any] = {
                "quote": quote_text,
                "attribution": attrib,
            }
            return out
    # Fallback: a single long bullet that reads like a quotation
    # (no trailing period + contains a verb-subject pattern). Too
    # heuristic to be reliable — only fire on strong signals.
    return None


_TIMELINE_PREFIX_RE = re.compile(
    r"^(?:"
    r"(?P<d1>Q[1-4]\s*\d{2,4})"           # Q1 2025 / Q3 24
    r"|(?P<d2>\d{4})"                      # 2025
    r"|(?P<d3>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{2,4})"
    r"|(?P<d4>Phase\s*\d+)"               # Phase 1
    r"|(?P<d5>Step\s*\d+)"                # Step 1
    r"|(?P<d6>Month\s*\d+)"               # Month 3
    r")\s*[:\-–—]\s*(?P<rest>.+)$",
    re.IGNORECASE,
)


def _extract_timeline(*, bullets: list[str], body: str) -> list[dict[str, Any]]:
    """Turn 'Q1 2025: ship MVP' / 'Phase 2 — onboard 50 customers'
    bullets into milestone records. Skips bullets that don't match."""
    out: list[dict[str, Any]] = []
    for b in bullets:
        text = (b or "").strip()
        if not text:
            continue
        m = _TIMELINE_PREFIX_RE.match(text)
        if m:
            date = (
                m.group("d1") or m.group("d2") or m.group("d3")
                or m.group("d4") or m.group("d5") or m.group("d6") or ""
            ).strip()
            rest = m.group("rest").strip()
            title_part, _, desc = rest.partition(" — ")
            if not desc:
                title_part, _, desc = rest.partition(": ")
            out.append(
                {
                    "date": date,
                    "title": (title_part or rest)[:80],
                    **({"description": desc} if desc else {}),
                }
            )
    return out


def _extract_comparison(
    *, slide: GeneratedSlide, bullets: list[str]
) -> Optional[dict[str, Any]]:
    """Turn 'Old: slow / New: fast' bullet pairs into a two-column
    comparison. Also handles 'feature: A vs B' patterns."""
    if len(bullets) < 2:
        return None
    rows: list[dict[str, Any]] = []
    col_labels: list[str] = []
    for b in bullets:
        text = (b or "").strip()
        if " vs " in text.lower():
            left, _, right = text.partition(" vs ")
            # "Price vs Quality" is a dimension, not a row — unreliable.
            # Skip for now; only accept key:value:value tuples.
            continue
        # "Label: value_a vs value_b"
        if ":" in text and (" vs " in text.lower() or " | " in text):
            head, _, tail = text.partition(":")
            parts = re.split(r"\s+vs\s+|\s+\|\s+", tail.strip(), maxsplit=1)
            if len(parts) == 2:
                rows.append({"feature": head.strip(), "values": [parts[0].strip(), parts[1].strip()]})
                continue
    if len(rows) < 2:
        return None
    # Derive column labels from the first row's values only if nothing else
    # is available. Falls back to "Option A / Option B" which is legible.
    col_labels = ["Current", "Proposed"]
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "columns": [{"name": col_labels[0]}, {"name": col_labels[1], "highlight": True}],
        "rows": rows,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _extract_diagram(
    *, slide: GeneratedSlide, bullets: list[str], body: str
) -> Optional[dict[str, Any]]:
    """Build a simple left-to-right flow diagram from named bullets.

    The writer already authored the labels; we only infer the flow order.
    This avoids fake structure while rescuing common layouts like
    "architecture flow" where the structured diagram field is missing.
    """
    candidates = [b.strip() for b in bullets if str(b).strip()]
    if len(candidates) < 2 and body:
        candidates = [p.strip() for p in re.split(r"[\n;]+", body) if p.strip()]
    if len(candidates) < 2:
        return None
    candidates = candidates[:6]
    nodes: list[dict[str, Any]] = []
    total = len(candidates)
    for i, text in enumerate(candidates):
        title, _, desc = text.partition(" — ")
        if not desc:
            title, _, desc = text.partition(":")
        nodes.append(
            {
                "id": f"n{i + 1}",
                "label": (title or text).strip()[:64],
                "x": (i + 1) / (total + 1),
                "y": 0.46 if i % 2 == 0 else 0.58,
            }
        )
    edges = [{"from": f"n{i + 1}", "to": f"n{i + 2}"} for i in range(total - 1)]
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "nodes": nodes,
        "edges": edges,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


_NUMBER_IN_TEXT_RE = re.compile(
    r"(?P<num>"
    r"[$£€]?\d[\d,]*(?:\.\d+)?\s*[%KMBT]?\b"   # $2.4B  87%  3.5x
    r"|\d+\s*x"
    r")",
    re.IGNORECASE,
)


def _promote_numeric_bullets(bullets: list[str]) -> list[dict[str, Any]]:
    """Scan bullets for strong numeric leads (e.g. '87% reduction in
    review time') and promote them into StatHero stat_blocks. We keep
    up to 4; if fewer than 2 qualify, return [] and let the caller
    fall through to FeatureGrid."""
    stats: list[dict[str, Any]] = []
    for b in bullets:
        text = (b or "").strip()
        if not text:
            continue
        m = _NUMBER_IN_TEXT_RE.search(text)
        if not m:
            continue
        value = m.group("num").strip().rstrip(".,:;")
        # label = the rest of the bullet, minus the number + noise words
        label = (text[: m.start()] + text[m.end():]).strip(" -—:;,.")
        # Drop generic fillers
        label = re.sub(r"^(of|in|per|with|by)\s+", "", label, flags=re.IGNORECASE)
        label = label[:60].strip()
        if not label:
            continue
        stats.append({"value": value, "label": label})
        if len(stats) >= 4:
            break
    # Quality floor: at least 2 stats AND each stat has a non-empty label.
    if len(stats) < 2:
        return []
    return stats
