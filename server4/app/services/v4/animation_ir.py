"""
V4 Animation IR — Phase 3 (Day 4-5) of v3-final plan.

Single source of truth for slide motion, consumed by ALL FOUR render
targets:

    kit_jsx       → reads `motion_props` (framer-motion declarative)
    html_css_js   → reads `css` (keyframes + class assignments)
    engine        → reads `motion_props` + `morph_ids` (custom engine)
    reveal_legacy → reads `reveal_fragments` (data-fragment-index)

Input: the existing `animation_plan` dict produced by
`slide_compiler._default_animation_plan` — shape:

    {
      "entry":      [{target, effect, duration_ms, delay_ms, easing, stagger_ms?}],
      "emphasis":   [{target, effect, duration_ms, trigger?}],
      "hover":      [{target, effect, duration_ms, easing?}],
      "exit":       [{target, effect, duration_ms, easing?}],
      "transition": "fade" | "slide" | "zoom" | "wipe" | …,
    }

Output: an `AnimationIR` dict with these top-level keys:

    {
      "version":              1,
      "fingerprint":          "<sha1[:12]>",
      "entries":              [<NormalizedAnim>, …],   # entry phase, expanded
      "emphasis":             [<NormalizedAnim>, …],
      "hover":                [<NormalizedAnim>, …],
      "exit":                 [<NormalizedAnim>, …],
      "transition":           "<slide-level transition>",
      "total_entry_ms":       <int>,    # sum of max(delay+duration) over entries
      "css":                  "<CSS keyframes + classes>",
      "motion_props":         { "<target>": { initial, animate, transition } },
      "reveal_fragments":     [{ index, target, fragment_class }],
      "morph_ids":            [<deterministic morph ids per target>],
    }

Design principles:
  - **Deterministic.** Same input → same fingerprint. No LLM, no time-based
    seeding, no randomness.
  - **No fake data.** Every IR field traces to either a value in the input
    plan or a documented default constant. Unknown effects FALL THROUGH to
    a safe `fade` rather than being faked as something fancier.
  - **Reduced-motion aware.** A second public function `to_reduced_motion`
    produces a flattened version (instant fades only) for users with
    `prefers-reduced-motion: reduce`.
  - **Stagger expansion.** When an entry has `stagger_ms`, the IR expands
    it into N normalized entries (one per child) so transformers don't
    have to re-implement stagger math.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


_SCHEMA_VERSION = 1


# ── Effect → CSS keyframe library ────────────────────────────────
# Keyframes are written with translate3d so GPU compositing is forced
# (avoids layout thrashing). Opacity transitions use simple 0→1.
# All transforms are GPU-friendly: translate, scale, rotate, opacity.
#
# These are the CANONICAL definitions every render target follows.
# Adding a new effect requires registering it here AND in
# `_EFFECT_MOTION_PROPS` below — the IR refuses unknown effects.

_EFFECT_KEYFRAMES: dict[str, str] = {
    "fade": (
        "@keyframes ir-fade {"
        " from { opacity: 0; }"
        " to { opacity: 1; }"
        " }"
    ),
    "fade-up": (
        "@keyframes ir-fade-up {"
        " from { opacity: 0; transform: translate3d(0, 16px, 0); }"
        " to { opacity: 1; transform: translate3d(0, 0, 0); }"
        " }"
    ),
    "fade-down": (
        "@keyframes ir-fade-down {"
        " from { opacity: 0; transform: translate3d(0, -16px, 0); }"
        " to { opacity: 1; transform: translate3d(0, 0, 0); }"
        " }"
    ),
    "slide-in": (
        "@keyframes ir-slide-in {"
        " from { opacity: 0; transform: translate3d(-24px, 0, 0); }"
        " to { opacity: 1; transform: translate3d(0, 0, 0); }"
        " }"
    ),
    "slide-in-right": (
        "@keyframes ir-slide-in-right {"
        " from { opacity: 0; transform: translate3d(24px, 0, 0); }"
        " to { opacity: 1; transform: translate3d(0, 0, 0); }"
        " }"
    ),
    "scale-in": (
        "@keyframes ir-scale-in {"
        " from { opacity: 0; transform: scale(0.94); }"
        " to { opacity: 1; transform: scale(1); }"
        " }"
    ),
    "pop": (
        "@keyframes ir-pop {"
        " 0% { opacity: 0; transform: scale(0.85); }"
        " 60% { opacity: 1; transform: scale(1.04); }"
        " 100% { transform: scale(1); }"
        " }"
    ),
    "blur-in": (
        "@keyframes ir-blur-in {"
        " from { opacity: 0; filter: blur(10px); }"
        " to { opacity: 1; filter: blur(0); }"
        " }"
    ),
    "ken-burns": (
        "@keyframes ir-ken-burns {"
        " from { transform: scale(1) translate3d(0, 0, 0); }"
        " to { transform: scale(1.08) translate3d(-1.5%, -1%, 0); }"
        " }"
    ),
    "draw": (
        # SVG-only — consumers add stroke-dasharray/offset; this keyframe
        # animates the offset to 0.
        "@keyframes ir-draw {"
        " from { stroke-dashoffset: var(--draw-length, 1000); }"
        " to { stroke-dashoffset: 0; }"
        " }"
    ),
    "count-up": (
        # Count-up is a JS-driven animation; the keyframe is a no-op
        # placeholder so HTML output still has a class to hook onto.
        "@keyframes ir-count-up {"
        " from { opacity: 0.85; }"
        " to { opacity: 1; }"
        " }"
    ),
    "pulse": (
        "@keyframes ir-pulse {"
        " 0%, 100% { transform: scale(1); }"
        " 50% { transform: scale(1.04); }"
        " }"
    ),
    "highlight-peak": (
        "@keyframes ir-highlight-peak {"
        " 0%, 100% { filter: brightness(1); }"
        " 50% { filter: brightness(1.18); }"
        " }"
    ),
    "lift": (
        "@keyframes ir-lift {"
        " from { transform: translate3d(0, 0, 0); box-shadow: var(--lift-shadow-from, 0 0 0 rgba(0,0,0,0)); }"
        " to { transform: translate3d(0, -3px, 0); box-shadow: var(--lift-shadow-to, 0 8px 18px rgba(0,0,0,0.18)); }"
        " }"
    ),
}

# ── Effect → framer-motion declarative props ─────────────────────
# `initial` and `animate` shapes match framer-motion `motion.div` API.
# Consumers (engine + kit_jsx) feed `transition` separately (delay + duration
# are added at IR-expansion time so each target gets a self-contained blob).

_EFFECT_MOTION_PROPS: dict[str, dict[str, Any]] = {
    "fade": {
        "initial": {"opacity": 0},
        "animate": {"opacity": 1},
    },
    "fade-up": {
        "initial": {"opacity": 0, "y": 16},
        "animate": {"opacity": 1, "y": 0},
    },
    "fade-down": {
        "initial": {"opacity": 0, "y": -16},
        "animate": {"opacity": 1, "y": 0},
    },
    "slide-in": {
        "initial": {"opacity": 0, "x": -24},
        "animate": {"opacity": 1, "x": 0},
    },
    "slide-in-right": {
        "initial": {"opacity": 0, "x": 24},
        "animate": {"opacity": 1, "x": 0},
    },
    "scale-in": {
        "initial": {"opacity": 0, "scale": 0.94},
        "animate": {"opacity": 1, "scale": 1},
    },
    "pop": {
        "initial": {"opacity": 0, "scale": 0.85},
        "animate": {"opacity": 1, "scale": 1},
    },
    "blur-in": {
        "initial": {"opacity": 0, "filter": "blur(10px)"},
        "animate": {"opacity": 1, "filter": "blur(0px)"},
    },
    "ken-burns": {
        "initial": {"scale": 1.0},
        "animate": {"scale": 1.08},
    },
    "draw": {
        "initial": {"pathLength": 0},
        "animate": {"pathLength": 1},
    },
    "count-up": {
        # Consumed by a custom CountUp component, not framer-motion. We
        # still emit a fade-in so static fallback isn't blank.
        "initial": {"opacity": 0.85},
        "animate": {"opacity": 1},
    },
    "pulse": {
        "initial": {"scale": 1},
        "animate": {"scale": [1, 1.04, 1]},
    },
    "highlight-peak": {
        "initial": {"filter": "brightness(1)"},
        "animate": {"filter": ["brightness(1)", "brightness(1.18)", "brightness(1)"]},
    },
    "lift": {
        "initial": {"y": 0},
        "animate": {"y": -3},
    },
}

# ── Easing alias map (CSS ↔ framer-motion) ───────────────────────

_EASING_TO_CSS: dict[str, str] = {
    "linear": "linear",
    "ease": "ease",
    "ease-in": "ease-in",
    "ease-out": "ease-out",
    "ease-in-out": "ease-in-out",
}

_EASING_TO_BEZIER: dict[str, list[float]] = {
    # framer-motion accepts both string ("easeOut") and cubic-bezier arrays.
    # Arrays travel cleanly through JSON; strings can be re-mapped sandbox-side.
    "linear": [0.0, 0.0, 1.0, 1.0],
    "ease": [0.25, 0.1, 0.25, 1.0],
    "ease-in": [0.42, 0.0, 1.0, 1.0],
    "ease-out": [0.0, 0.0, 0.58, 1.0],
    "ease-in-out": [0.42, 0.0, 0.58, 1.0],
}


def _normalize_easing(raw: str | None) -> str:
    e = (raw or "ease-out").strip().lower()
    return e if e in _EASING_TO_CSS else "ease-out"


def _safe_effect(raw: str | None) -> str:
    """Fall back to `fade` for any unknown effect — never silently invent
    a fancier animation than what the input asked for."""
    e = (raw or "").strip().lower()
    return e if e in _EFFECT_KEYFRAMES else "fade"


def _coerce_int(value: Any, default: int, *, lo: int = 0, hi: int = 30_000) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _slug(text: str) -> str:
    """ASCII-safe identifier suitable for CSS class names."""
    out = []
    for ch in (text or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in "-_ ":
            out.append("-")
    s = "".join(out).strip("-")
    return s or "el"


def _expand_stagger(
    item: dict[str, Any],
    *,
    phase: str,
) -> list[dict[str, Any]]:
    """
    If an animation item has `stagger_ms` AND `stagger_count` (>1), expand
    it into N normalized children with deterministic ids and incrementally
    delayed start times. Otherwise return a single normalized item.
    """
    target = (item.get("target") or "el").strip() or "el"
    effect = _safe_effect(item.get("effect"))
    duration_ms = _coerce_int(item.get("duration_ms"), 400, lo=0, hi=20_000)
    base_delay = _coerce_int(item.get("delay_ms"), 0, lo=0, hi=20_000)
    easing = _normalize_easing(item.get("easing"))
    stagger_ms = _coerce_int(item.get("stagger_ms"), 0, lo=0, hi=2_000)
    # `stagger_count` is OPTIONAL — when absent, we still emit ONE item but
    # mark `stagger_ms` so consumers that own the child collection (kit_jsx,
    # engine) can apply per-child delays themselves.
    stagger_count = _coerce_int(item.get("stagger_count"), 0, lo=0, hi=64)

    base = {
        "target": target,
        "effect": effect,
        "duration_ms": duration_ms,
        "easing": easing,
        "phase": phase,
    }
    if "trigger" in item and isinstance(item["trigger"], str):
        base["trigger"] = item["trigger"]

    if stagger_ms > 0 and stagger_count > 1:
        out: list[dict[str, Any]] = []
        for i in range(stagger_count):
            child = dict(base)
            child["target"] = f"{target}.{i}"
            child["delay_ms"] = base_delay + (i * stagger_ms)
            child["stagger_index"] = i
            child["stagger_ms"] = stagger_ms
            child["id"] = f"{phase}-{_slug(target)}-{i}"
            out.append(child)
        return out

    single = dict(base)
    single["delay_ms"] = base_delay
    if stagger_ms > 0:
        # Consumer-side stagger: pass through so the kit can use it on
        # children it generates dynamically.
        single["stagger_ms"] = stagger_ms
    single["id"] = f"{phase}-{_slug(target)}"
    return [single]


def _phase(plan: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = plan.get(key)
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.extend(_expand_stagger(item, phase=key))
    return out


# ── Per-target compilation ───────────────────────────────────────

def _build_css(entries: Iterable[dict[str, Any]]) -> str:
    """
    Produce a self-contained CSS string with:
      - `@keyframes` blocks for every effect referenced (deduped)
      - one `.ir-anim-<id>` class per entry binding it to its keyframe,
        delay, duration, and easing
      - a `@media (prefers-reduced-motion: reduce)` override that flattens
        every animation to a 0.001s instant.
    """
    seen_effects: set[str] = set()
    blocks: list[str] = []
    classes: list[str] = []

    for e in entries:
        effect = e["effect"]
        if effect not in seen_effects:
            seen_effects.add(effect)
            blocks.append(_EFFECT_KEYFRAMES[effect])

        duration_s = e["duration_ms"] / 1000.0
        delay_s = e["delay_ms"] / 1000.0
        css_easing = _EASING_TO_CSS[e["easing"]]
        # `forwards` retains the animated end-state — without it the
        # element would snap back to its `initial` styles after the
        # animation completes.
        classes.append(
            f".ir-anim-{e['id']} {{"
            f" animation: ir-{effect} {duration_s:.3f}s {css_easing} {delay_s:.3f}s 1 both;"
            f" }}"
        )

    reduced = (
        "@media (prefers-reduced-motion: reduce) {"
        " [class*='ir-anim-'] { animation-duration: 0.001s !important;"
        " animation-delay: 0s !important; } }"
    )

    return "\n".join(blocks + classes + [reduced]) + "\n"


def _build_motion_props(entries: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Map { target → framer-motion declarative blob }.
    `transition.delay` and `transition.duration` are baked into each blob
    so consumers can spread it directly onto a `<motion.div>`.
    """
    out: dict[str, dict[str, Any]] = {}
    for e in entries:
        effect = e["effect"]
        base = _EFFECT_MOTION_PROPS[effect]
        out[e["target"]] = {
            "initial": base["initial"],
            "animate": base["animate"],
            "transition": {
                "duration": round(e["duration_ms"] / 1000.0, 3),
                "delay": round(e["delay_ms"] / 1000.0, 3),
                "ease": _EASING_TO_BEZIER[e["easing"]],
            },
        }
    return out


def _build_reveal_fragments(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Reveal.js represents staged reveals via `data-fragment-index` (integer
    ordering) plus a CSS class describing the visual style ("fade-up",
    "fade-in-then-out", etc.).

    We sort entries by (delay_ms, stagger_index, target) so the reveal
    order matches the visual order on screen. Effect names map to
    Reveal-supported classes; unknowns fall back to `fade-in`.
    """
    reveal_class_map = {
        "fade": "fade-in",
        "fade-up": "fade-up",
        "fade-down": "fade-down",
        "slide-in": "fade-right",
        "slide-in-right": "fade-left",
        "scale-in": "zoom-in",
        "pop": "zoom-in",
        "blur-in": "fade-in",
        "ken-burns": "fade-in",
        "draw": "fade-in",
        "count-up": "fade-in",
        "pulse": "highlight-current-blue",
        "highlight-peak": "highlight-current-blue",
        "lift": "fade-in",
    }

    sorted_entries = sorted(
        entries,
        key=lambda x: (
            x.get("delay_ms", 0),
            x.get("stagger_index", 0),
            x.get("target", ""),
        ),
    )

    out: list[dict[str, Any]] = []
    for index, e in enumerate(sorted_entries):
        out.append({
            "index": index,
            "target": e["target"],
            "fragment_class": reveal_class_map.get(e["effect"], "fade-in"),
            "id": e["id"],
        })
    return out


def _build_morph_ids(entries: Iterable[dict[str, Any]]) -> list[str]:
    """
    Morph IDs are stable identifiers the Phase 5 custom engine uses for
    cross-slide element morphing (FLIP-style). One per unique non-stagger
    target; for staggered groups we use the parent target sans index.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for e in entries:
        # strip ".N" stagger suffix to get the parent group
        target = e["target"].split(".")[0]
        morph = f"morph-{_slug(target)}"
        if morph not in seen_set:
            seen_set.add(morph)
            seen.append(morph)
    return seen


# ── Public API ────────────────────────────────────────────────────

def build_animation_ir(animation_plan: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a slide's `animation_plan` (slide_compiler output) into a
    target-agnostic AnimationIR that all four render transformers consume.

    Args:
        animation_plan: Output of `slide_compiler._default_animation_plan`.
                        Tolerates partial / missing keys (defensive).

    Returns:
        AnimationIR dict — see module docstring for the full shape.
    """
    if not isinstance(animation_plan, dict):
        animation_plan = {}

    entries = _phase(animation_plan, "entry")
    emphasis = _phase(animation_plan, "emphasis")
    hover = _phase(animation_plan, "hover")
    exit_ = _phase(animation_plan, "exit")

    # CSS spans every phase — even hover/exit, because the HTML transformer
    # binds them to data-state attributes.
    all_phases = entries + emphasis + hover + exit_

    css = _build_css(all_phases)
    motion_props = _build_motion_props(entries)  # entry-only on purpose
    reveal_fragments = _build_reveal_fragments(entries)
    morph_ids = _build_morph_ids(entries)

    total_entry_ms = max(
        (e["delay_ms"] + e["duration_ms"] for e in entries),
        default=0,
    )

    transition = animation_plan.get("transition")
    if not isinstance(transition, str) or not transition.strip():
        transition = "fade"

    ir = {
        "version": _SCHEMA_VERSION,
        "entries": entries,
        "emphasis": emphasis,
        "hover": hover,
        "exit": exit_,
        "transition": transition,
        "total_entry_ms": total_entry_ms,
        "css": css,
        "motion_props": motion_props,
        "reveal_fragments": reveal_fragments,
        "morph_ids": morph_ids,
    }

    # Fingerprint EXCLUDES `css` since it's content-derived (its hash would
    # change with any whitespace tweak in keyframes); we hash the IR's
    # semantic data only.
    fingerprint_input = json.dumps(
        {
            "version": _SCHEMA_VERSION,
            "entries": entries,
            "emphasis": emphasis,
            "hover": hover,
            "exit": exit_,
            "transition": transition,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    ir["fingerprint"] = hashlib.sha1(fingerprint_input.encode("utf-8")).hexdigest()[:12]
    return ir


def to_reduced_motion(ir: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a flattened reduced-motion variant: every duration → 0,
    every delay → 0, every effect → 'fade'. Returns a NEW dict; original
    IR is untouched.

    Used by the engine when the parent frame signals
    `prefers-reduced-motion: reduce` after IR has been computed.
    """
    def _flatten(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for item in items:
            f = dict(item)
            f["effect"] = "fade"
            f["duration_ms"] = 0
            f["delay_ms"] = 0
            out.append(f)
        return out

    flat_entries = _flatten(ir.get("entries", []))
    flat_emphasis = _flatten(ir.get("emphasis", []))
    flat_hover = _flatten(ir.get("hover", []))
    flat_exit = _flatten(ir.get("exit", []))

    return {
        "version": ir.get("version", _SCHEMA_VERSION),
        "entries": flat_entries,
        "emphasis": flat_emphasis,
        "hover": flat_hover,
        "exit": flat_exit,
        "transition": "none",
        "total_entry_ms": 0,
        "css": _build_css(flat_entries + flat_emphasis + flat_hover + flat_exit),
        "motion_props": _build_motion_props(flat_entries),
        "reveal_fragments": _build_reveal_fragments(flat_entries),
        "morph_ids": ir.get("morph_ids", []),
        "fingerprint": ir.get("fingerprint", "") + "-rm",
    }
