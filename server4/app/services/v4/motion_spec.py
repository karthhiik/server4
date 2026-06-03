"""Deterministic motion contract for Barise V4 slides.

This module sits above ``animation_ir``. AnimationIR describes primitive
effects; MotionSpec describes the product contract around those effects:
intent-aware preset, seek protocol, poster frame, QA sample frames, and
deterministic layer metadata for render/export tooling.

The shape is intentionally JSON-only so it can travel through MongoDB,
websocket events, static HTML export, future video export workers, and tests
without importing a browser runtime.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


_SCHEMA_VERSION = 1
_DEFAULT_FPS = 30


_INTENT_PRESETS: dict[str, dict[str, Any]] = {
    "title": {
        "preset": "founder-cover-reveal",
        "tone": "confident",
        "transition": "editorial-zoom",
        "hold_ms": 720,
        "poster_bias": 0.92,
        "adapter": "css",
    },
    "problem": {
        "preset": "problem-tension-reveal",
        "tone": "urgent",
        "transition": "fade-cross",
        "hold_ms": 560,
        "poster_bias": 0.88,
        "adapter": "css",
    },
    "solution": {
        "preset": "solution-build",
        "tone": "confident",
        "transition": "slide-up",
        "hold_ms": 620,
        "poster_bias": 0.9,
        "adapter": "css",
    },
    "architecture": {
        "preset": "architecture-trace",
        "tone": "technical",
        "transition": "diagram-draw",
        "hold_ms": 760,
        "poster_bias": 0.95,
        "adapter": "waapi",
    },
    "benchmark": {
        "preset": "benchmark-evidence-build",
        "tone": "evidence",
        "transition": "data-draw",
        "hold_ms": 700,
        "poster_bias": 0.94,
        "adapter": "waapi",
    },
    "market": {
        "preset": "market-proof-reveal",
        "tone": "analytical",
        "transition": "data-reveal",
        "hold_ms": 640,
        "poster_bias": 0.9,
        "adapter": "css",
    },
    "competition": {
        "preset": "comparison-column-reveal",
        "tone": "decisive",
        "transition": "column-stagger",
        "hold_ms": 680,
        "poster_bias": 0.91,
        "adapter": "css",
    },
    "ask": {
        "preset": "ask-milestone-focus",
        "tone": "direct",
        "transition": "fade-cross",
        "hold_ms": 560,
        "poster_bias": 0.86,
        "adapter": "css",
    },
    "closing": {
        "preset": "closing-confidence",
        "tone": "calm",
        "transition": "soft-fade",
        "hold_ms": 620,
        "poster_bias": 0.88,
        "adapter": "css",
    },
    "default": {
        "preset": "content-stagger",
        "tone": "professional",
        "transition": "fade-cross",
        "hold_ms": 560,
        "poster_bias": 0.88,
        "adapter": "css",
    },
}


def canonical_motion_intent(
    intent: str | None,
    kit: str | None = None,
    layout: str | None = None,
) -> str:
    """Collapse free-form slide intents into motion intent families."""
    text = f"{intent or ''} {kit or ''} {layout or ''}".strip().lower()
    if any(term in text for term in ("title", "cover", "hero")):
        return "title"
    if any(term in text for term in ("problem", "pain", "risk", "urgent")):
        return "problem"
    if any(term in text for term in ("solution", "product", "value_prop", "value prop")):
        return "solution"
    if any(term in text for term in (
        "architecture", "diagram", "system", "workflow", "proof_flow",
        "process", "hardware", "integration", "consensus", "flow",
    )):
        return "architecture"
    if any(term in text for term in (
        "performance", "benchmark", "latency", "scalability", "scale",
        "traction", "metrics", "financial",
    )):
        return "benchmark"
    if any(term in text for term in ("market", "tam", "sam", "som", "buyer", "gtm", "go to market")):
        return "market"
    if any(term in text for term in ("competition", "competitive", "moat", "differentiation")):
        return "competition"
    if any(term in text for term in ("ask", "funding", "capital", "cta")):
        return "ask"
    if any(term in text for term in ("closing", "thank", "diligence", "contact")):
        return "closing"
    return "default"


def build_layer_metadata(
    *,
    slide_id: str,
    kit: str,
    engine_artifact: Mapping[str, Any] | None,
    animation_ir: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Create stable, HTML-exportable metadata for render layers.

    Layer positions come from the engine artifact because that is already the
    deterministic primitive render substrate. We do not infer missing layers.
    """
    ir = animation_ir if isinstance(animation_ir, Mapping) else {}
    anim_targets = {
        str(entry.get("target") or ""): f"ir-anim-{entry.get('id')}"
        for entry in ir.get("entries") or []
        if isinstance(entry, Mapping) and entry.get("target") and entry.get("id")
    }
    layers: list[dict[str, Any]] = []
    raw_layers = []
    if isinstance(engine_artifact, Mapping):
        raw_layers = engine_artifact.get("layers") or []
    for z_index, layer in enumerate(raw_layers):
        if not isinstance(layer, Mapping):
            continue
        layer_id = str(layer.get("id") or f"layer-{z_index:02d}").strip() or f"layer-{z_index:02d}"
        bounds = {
            "x": _round_unit(layer.get("x")),
            "y": _round_unit(layer.get("y")),
            "w": _round_unit(layer.get("w"), default=1.0),
            "h": _round_unit(layer.get("h"), default=1.0),
        }
        anim_id = layer.get("anim_id") or anim_targets.get(layer_id)
        selector = (
            f"#{slide_id} .{_css_class_escape(str(anim_id))}"
            if anim_id
            else f'#{slide_id} [data-layer-id="{_css_attr_escape(layer_id)}"]'
        )
        meta: dict[str, Any] = {
            "id": layer_id,
            "type": str(layer.get("type") or "unknown"),
            "role": str(layer.get("role") or layer.get("type") or "content"),
            "selector": selector,
            "engine_layer_id": layer_id,
            "z_index": z_index,
            "paint_order": z_index,
            "bounds": bounds,
            "safe_for_poster": layer.get("type") != "error",
        }
        if anim_id:
            meta["anim_id"] = str(anim_id)
        if layer.get("color_token"):
            meta["color_token"] = str(layer.get("color_token"))
        layers.append(meta)

    out: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "version": _SCHEMA_VERSION,
        "slide_id": slide_id,
        "kit": kit,
        "source": "engine_artifact",
        "layer_count": len(layers),
        "coordinate_space": "normalized_16_9",
        "layers": layers,
    }
    out["fingerprint"] = _fingerprint(out)
    return out


def build_motion_spec(
    *,
    intent: str | None,
    layout: str | None,
    kit: str,
    animation_plan: Mapping[str, Any] | None,
    animation_ir: Mapping[str, Any] | None,
    layer_metadata: Mapping[str, Any] | None,
    effects: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic motion spec consumed by preview/export/QA."""
    ir = animation_ir if isinstance(animation_ir, Mapping) else {}
    plan = animation_plan if isinstance(animation_plan, Mapping) else {}
    motion_intent = canonical_motion_intent(intent, kit, layout)
    preset = dict(_INTENT_PRESETS.get(motion_intent) or _INTENT_PRESETS["default"])
    normalized_effects = _normalize_effects(effects, motion_intent=motion_intent)

    total_entry_ms = _coerce_int(ir.get("total_entry_ms"), 0)
    duration_ms = max(900, total_entry_ms + _coerce_int(preset.get("hold_ms"), 560))
    duration_ms = min(duration_ms, 8_000)
    active_entry_end = _active_entry_end_ms(ir)
    poster_ms = int(round(max(active_entry_end + 160, duration_ms * float(preset.get("poster_bias") or 0.9))))
    poster_policy = normalized_effects["pdfPosterFrame"]
    if poster_policy == "start":
        poster_ms = 0
    elif poster_policy == "middle":
        poster_ms = max(active_entry_end, duration_ms // 2)
    elif poster_policy == "final":
        poster_ms = duration_ms
    poster_ms = max(240, min(poster_ms, duration_ms))
    if poster_policy == "start":
        poster_ms = 0

    layer_count = 0
    layer_ids: list[str] = []
    if isinstance(layer_metadata, Mapping):
        raw_layers = layer_metadata.get("layers") or []
        layer_ids = [
            str(layer.get("id"))
            for layer in raw_layers
            if isinstance(layer, Mapping) and layer.get("id")
        ]
        layer_count = len(layer_ids)

    snapshots = _snapshot_frames(duration_ms, poster_ms)
    capture_times = [int(frame["time_ms"]) for frame in snapshots]
    spec: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "version": _SCHEMA_VERSION,
        "protocol": "barise.motion.v1",
        "seek_protocol": {
            "global": "window.__bariseSlide",
            "duration_field": "duration",
            "seek_method": "seek",
            "fps": _DEFAULT_FPS,
            "deterministic": True,
            "html_to_video_compatible": True,
        },
        "intent": motion_intent,
        "source_intent": intent or "",
        "layout": layout or "",
        "kit": kit,
        "preset": motion_intent,
        "style_preset": preset["preset"],
        "tone": preset["tone"],
        "adapter": preset["adapter"],
        "allowed_adapters": _allowed_adapters_for(kit, motion_intent),
        "transition": normalized_effects["transition"] or plan.get("transition") or preset["transition"],
        "effects": normalized_effects,
        "reveal": normalized_effects["reveal"],
        "chart_motion": normalized_effects["chartMotion"],
        "image_motion": normalized_effects["imageMotion"],
        "duration_ms": duration_ms,
        "poster_frame": {
            "time_ms": poster_ms,
            "progress": _progress(poster_ms, duration_ms),
            "reason": f"pdf_poster_frame_{poster_policy}",
            "purpose": "pdf_export_and_static_preview",
        },
        "snapshot_plan": snapshots,
        "qa_snapshots": snapshots,
        "render_qa": {
            "required": True,
            "capture_times_ms": capture_times,
            "checks": [
                "non_blank_canvas",
                "text_not_clipped",
                "contrast_readable",
                "assets_loaded",
                "no_layer_overlap_regression",
            ],
        },
        "pdf_export": {
            "mode": "poster_frame",
            "time_ms": poster_ms,
            "freeze_animations": True,
            "poster_frame_policy": poster_policy,
        },
        "accessibility": {
            "reduced_motion_safe": normalized_effects["reducedMotionSafe"],
            "autoplay": normalized_effects["autoplay"],
            "pause_stop_hide_required": bool(normalized_effects["autoplay"] and duration_ms > 5000),
            "wcag_reference": "WCAG 2.2.2 Pause, Stop, Hide",
        },
        "layer_summary": {
            "count": layer_count,
            "ids": layer_ids[:24],
            "fingerprint": layer_metadata.get("fingerprint") if isinstance(layer_metadata, Mapping) else None,
        },
        "animation_ir_fingerprint": ir.get("fingerprint") or "",
        "video_export": {
            "status": "planned",
            "container_targets": ["mp4", "webm"],
            "requires": ["chromium", "ffmpeg"],
            "recommended_fps": _DEFAULT_FPS,
            "compatible_with": "hyperframes-style-seek-protocol",
        },
    }
    spec["fingerprint"] = _fingerprint(spec)
    return spec


def build_render_qa_plan(
    *,
    motion_spec: Mapping[str, Any],
    layer_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Return planned render-QA snapshots without invoking a browser."""
    snapshots = []
    for frame in motion_spec.get("qa_snapshots") or []:
        if not isinstance(frame, Mapping):
            continue
        snapshots.append({
            "label": frame.get("label"),
            "time_ms": frame.get("time_ms"),
            "progress": frame.get("progress"),
            "status": "planned",
            "checks": [
                "non_blank_canvas",
                "text_not_clipped",
                "contrast_readable",
                "assets_loaded",
                "no_layer_overlap_regression",
            ],
        })
    plan: dict[str, Any] = {
        "version": _SCHEMA_VERSION,
        "mode": "planned_multi_frame",
        "engine": "chromium_snapshot",
        "poster_frame_ms": (motion_spec.get("poster_frame") or {}).get("time_ms"),
        "layer_fingerprint": layer_metadata.get("fingerprint"),
        "snapshots": snapshots,
    }
    plan["fingerprint"] = _fingerprint(plan)
    return plan


def build_seek_runtime_js(motion_spec: Mapping[str, Any], animation_ir: Mapping[str, Any]) -> str:
    """Generate a tiny deterministic seek bridge for standalone HTML.

    The bridge pauses CSS animations and offsets each AnimationIR class by
    ``entry.delay_ms - seek_ms``. This gives the screenshot/PDF/video worker a
    stable poster frame instead of whatever frame the browser happened to paint.
    """
    entries = [
        {
            "id": entry.get("id"),
            "target": entry.get("target"),
            "delay_ms": _coerce_int(entry.get("delay_ms"), 0),
            "duration_ms": _coerce_int(entry.get("duration_ms"), 0),
        }
        for entry in (animation_ir.get("entries") or [])
        if isinstance(entry, Mapping) and entry.get("id")
    ] if isinstance(animation_ir, Mapping) else []
    duration_ms = _coerce_int(motion_spec.get("duration_ms"), 1000, lo=1)
    poster_ms = _coerce_int((motion_spec.get("poster_frame") or {}).get("time_ms"), duration_ms)
    payload = {
        "duration_ms": duration_ms,
        "poster_ms": poster_ms,
        "motion_spec": {
            "protocol": motion_spec.get("protocol"),
            "preset": motion_spec.get("preset"),
            "style_preset": motion_spec.get("style_preset"),
            "poster_frame": motion_spec.get("poster_frame"),
            "snapshot_plan": motion_spec.get("snapshot_plan") or motion_spec.get("qa_snapshots"),
        },
        "entries": entries,
    }
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    return f"""
(function() {{
  var spec = {payload_json};
  function clampTime(ms) {{
    var value = Number(ms);
    if (!Number.isFinite(value)) value = 0;
    return Math.max(0, Math.min(spec.duration_ms, value));
  }}
  function seek(ms) {{
    var time = clampTime(ms);
    document.documentElement.style.setProperty('--barise-seek-ms', time + 'ms');
    document.body.setAttribute('data-barise-seek', 'true');
    (spec.entries || []).forEach(function(entry) {{
      if (!entry || !entry.id) return;
      var nodes = document.querySelectorAll('.ir-anim-' + entry.id);
      nodes.forEach(function(node) {{
        node.style.animationPlayState = 'paused';
        node.style.animationFillMode = 'both';
        node.style.animationDelay = (Number(entry.delay_ms || 0) - time) + 'ms';
      }});
    }});
    return time / 1000;
  }}
  window.__bariseSlide = {{
    duration: spec.duration_ms / 1000,
    posterFrame: spec.poster_ms / 1000,
    motionSpec: spec.motion_spec || {{}},
    seek: function(seconds) {{ return seek(Number(seconds || 0) * 1000); }},
    seekMs: seek
  }};
  if (document.documentElement.getAttribute('data-barise-poster') === 'true') {{
    seek(spec.poster_ms);
  }}
}})();
""".strip()


def _snapshot_frames(duration_ms: int, poster_ms: int) -> list[dict[str, Any]]:
    mid_ms = max(1, min(duration_ms, poster_ms // 2 if poster_ms > 1 else duration_ms // 2))
    candidates = [
        ("initial", 0),
        ("mid_motion", mid_ms),
        ("poster", poster_ms),
        ("final", duration_ms),
    ]
    seen: set[int] = set()
    frames: list[dict[str, Any]] = []
    for label, time_ms in candidates:
        if time_ms in seen:
            continue
        seen.add(time_ms)
        frames.append({
            "label": label,
            "time_ms": int(time_ms),
            "progress": _progress(time_ms, duration_ms),
        })
    return frames


def _normalize_effects(
    effects: Mapping[str, Any] | None,
    *,
    motion_intent: str,
) -> dict[str, Any]:
    provided = isinstance(effects, Mapping) and bool(effects)
    raw = effects if isinstance(effects, Mapping) else {}
    default_style = {
        "architecture": "diagram-draw",
        "benchmark": "data-reveal",
        "market": "data-reveal",
        "title": "editorial",
    }.get(motion_intent, "minimal")
    style = _choice(raw.get("style"), {
        "minimal", "editorial", "cinematic", "technical", "data-reveal", "diagram-draw",
    }, default_style)
    transition = _choice(raw.get("transition"), {"fade", "slide", "zoom", "wipe", "morph"}, "")
    reveal = _choice(raw.get("reveal"), {
        "none", "stagger", "bullet-by-bullet", "section-by-section",
    }, "stagger")
    chart_motion = _choice(raw.get("chartMotion"), {"none", "draw", "count-up", "bar-grow"}, "draw" if style == "data-reveal" else "none")
    image_motion = _choice(raw.get("imageMotion"), {"none", "ken-burns", "parallax", "soft-zoom"}, "none")
    intensity = _choice(raw.get("intensity"), {"low", "medium", "high"}, "low")
    poster = _choice(raw.get("pdfPosterFrame"), {"start", "middle", "final"}, "auto")
    return {
        "style": style,
        "transition": transition,
        "reveal": reveal,
        "chartMotion": chart_motion,
        "imageMotion": image_motion,
        "intensity": intensity,
        "autoplay": bool(raw.get("autoplay", False)) if provided else False,
        "reducedMotionSafe": bool(raw.get("reducedMotionSafe", True)),
        "pdfPosterFrame": poster,
        "userSelected": provided,
    }


def _choice(value: Any, allowed: set[str], default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in allowed else default


def _allowed_adapters_for(kit: str, intent: str) -> list[str]:
    adapters = ["css", "waapi"]
    if kit in {"DiagramBlock", "ChartBlock"} or intent in {"architecture", "benchmark"}:
        adapters.append("svg")
    if kit in {"FullBleedImage", "CinematicHero", "DuotoneHero"}:
        adapters.append("media")
    if kit in {"AppMockup", "DiagramBlock"}:
        adapters.append("three")
    return adapters


def _active_entry_end_ms(animation_ir: Mapping[str, Any]) -> int:
    """Return the end of foreground entry motion, ignoring long media loops."""
    if not isinstance(animation_ir, Mapping):
        return 0
    ends: list[int] = []
    for entry in animation_ir.get("entries") or []:
        if not isinstance(entry, Mapping):
            continue
        target = str(entry.get("target") or "").lower()
        effect = str(entry.get("effect") or "").lower()
        if effect in {"ken-burns"} or target in {"image", "background"}:
            continue
        delay = _coerce_int(entry.get("delay_ms"), 0)
        duration = _coerce_int(entry.get("duration_ms"), 0)
        ends.append(delay + duration)
    return max(ends) if ends else _coerce_int(animation_ir.get("total_entry_ms"), 0)


def _coerce_int(value: Any, default: int, *, lo: int = 0, hi: int = 120_000) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, out))


def _progress(time_ms: int, duration_ms: int) -> float:
    if duration_ms <= 0:
        return 0.0
    return round(max(0.0, min(1.0, time_ms / duration_ms)), 4)


def _round_unit(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(1.0, number)), 4)


def _css_attr_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _css_class_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(" ", "\\ ")


def _fingerprint(payload: Mapping[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if k != "fingerprint"}
    serialized = json.dumps(clean, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()[:12]
