"""
V4 Hot-Swap — Phase 6 of v3-final plan.

Detects low-quality compiled slides (via Phase 4.5 quality scores) and
attempts deterministic, no-LLM remediation. Real fixes only:

  * **Density overshoot** (density score < 70 with char_count > target_max):
    truncate the longest text fields proportionally until the slide
    falls back inside its kit's density band.
  * **Alignment defects** that are removable (not invented):
      - DiagramBlock: drop edges referencing missing nodes.
      - ChartBlock:   drop series with no data points; drop rows where
                      every numeric column is null.
      - StatHero:     drop entries missing both `value` and `label`.
      - ComparisonBlock: drop rows with empty `values` arrays.
      - FeatureGrid:  drop features with no `title` AND no
                      `description`.

If the deterministic pass raises the slide's overall score to
``>= 70`` we recompile its four artifacts in place (kit_jsx,
html_css_js, engine, reveal_legacy), re-score, and emit a
``slide_hotswap_succeeded`` event. If not, we emit
``slide_hotswap_skipped`` so Phase 12 LLM-retry can pick it up.

NO fabricated data. NO defaults invented. If a slide has fewer real
items after cleanup, the slide carries fewer items — the user sees
exactly what the upstream stages produced minus the broken pieces.

Wire shape of events (forwarded verbatim through the existing
``v4:progress:{project_id}`` Redis pub/sub channel):

    {"stage": "quality_summary",
     "payload": {"n_slides": 8, "n_passing": 6, "n_low": 2,
                 "low_slide_ids": ["slide-003", "slide-005"]}}

    {"stage": "slide_hotswap_started",
     "payload": {"slide_id": "slide-003", "reason": "density_overshoot",
                 "before_score": 58}}

    {"stage": "slide_hotswap_succeeded",
     "payload": {"slide_id": "slide-003",
                 "before_score": 58, "after_score": 84,
                 "fixes_applied": ["truncate:headline", "truncate:bullets[1]"]}}

    {"stage": "slide_hotswap_skipped",
     "payload": {"slide_id": "slide-005",
                 "score": 42, "reason": "alignment_unfixable",
                 "issues": ["TitleHero missing required prop: headline"]}}

    {"stage": "hot_swap_complete",
     "payload": {"n_attempted": 2, "n_succeeded": 1, "n_skipped": 1,
                 "duration_ms": 14}}

Module is sync + dependency-free aside from the four transformer
modules already on the import graph.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, Awaitable, Callable, Mapping, Sequence

import structlog

from app.services.v4.engine_transformer import build_engine
from app.services.v4.html_transformer import build_html_css_js
from app.services.v4.motion_spec import build_layer_metadata, build_motion_spec, build_render_qa_plan
from app.services.v4.slide_intelligence import build_slide_intelligence_spec
from app.services.v4.quality_scorer import (
    _DENSITY_TARGETS,
    _collect_visible_text,
    score_slide,
)
from app.services.v4.reveal_legacy_transformer import build_reveal_legacy

logger = structlog.get_logger(__name__)

ProgressCallback = Callable[[str, dict[str, Any]], Awaitable[None]]

# Threshold below which we consider a slide low-quality. Mirrors
# `passes_threshold` in quality_scorer (>= 70).
_PASS_THRESHOLD = 70

# Hard cap on truncation iterations to guarantee termination even on
# pathological prop trees.
_MAX_TRUNCATION_PASSES = 12


# ── Public API ───────────────────────────────────────────────────────


async def hot_swap_low_quality_slides(
    *,
    compiled_slides: list[dict[str, Any]],
    design_tokens: Mapping[str, Any] | None,
    emit: ProgressCallback | None = None,
) -> dict[str, Any]:
    """
    Walk every compiled slide; for each one whose ``quality_score`` is
    below threshold, attempt deterministic remediation and recompile
    artifacts in place. Returns a summary report.
    """
    started_ms = time.perf_counter()
    tokens = design_tokens if isinstance(design_tokens, Mapping) else {}

    # First pass — compute the quality summary so the frontend can
    # show "2 of 8 slides need attention" before per-slide work
    # finishes.
    low_slides = _find_low_quality_slides(compiled_slides)
    summary_payload = {
        "n_slides": len(compiled_slides),
        "n_passing": len(compiled_slides) - len(low_slides),
        "n_low": len(low_slides),
        "low_slide_ids": [s.get("slide_id") for s in low_slides],
    }
    await _safe_emit(emit, "quality_summary", summary_payload)

    n_succeeded = 0
    n_skipped = 0

    for slide in low_slides:
        slide_id = slide.get("slide_id") or ""
        before_score = _overall(slide)
        reason = _diagnose(slide)

        await _safe_emit(emit, "slide_hotswap_started", {
            "slide_id": slide_id,
            "reason": reason,
            "before_score": before_score,
        })

        outcome = _attempt_remediate(slide=slide, tokens=tokens)

        if outcome["status"] == "succeeded":
            n_succeeded += 1
            await _safe_emit(emit, "slide_hotswap_succeeded", {
                "slide_id": slide_id,
                "before_score": before_score,
                "after_score": outcome["after_score"],
                "fixes_applied": outcome["fixes_applied"],
                "artifact_version": slide.get("artifact_version"),
            })
        else:
            n_skipped += 1
            await _safe_emit(emit, "slide_hotswap_skipped", {
                "slide_id": slide_id,
                "score": before_score,
                "reason": outcome["reason"],
                "issues": outcome["issues"],
            })

    duration_ms = int((time.perf_counter() - started_ms) * 1000)
    report = {
        "n_attempted": len(low_slides),
        "n_succeeded": n_succeeded,
        "n_skipped": n_skipped,
        "duration_ms": duration_ms,
    }
    await _safe_emit(emit, "hot_swap_complete", report)
    return {**report, "summary": summary_payload}


# ── Detection ────────────────────────────────────────────────────────


def _find_low_quality_slides(
    compiled_slides: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """A slide is low-quality if its overall is below threshold OR
    any individual dimension is below threshold. The second clause
    lets us clean up alignment defects (dangling edges, empty rows)
    even when contrast and density mask the overall score above 70.
    """
    out: list[dict[str, Any]] = []
    for slide in compiled_slides:
        if not isinstance(slide, dict):
            continue
        qs = slide.get("quality_score")
        if not isinstance(qs, Mapping):
            continue
        overall = qs.get("overall")
        is_low_overall = (
            isinstance(overall, (int, float))
            and int(overall) < _PASS_THRESHOLD
        )
        is_low_dim = False
        dims = qs.get("dimensions")
        if isinstance(dims, Mapping):
            for name in ("alignment", "density", "contrast"):
                d = dims.get(name)
                if isinstance(d, Mapping):
                    s = d.get("score")
                    if isinstance(s, (int, float)) and int(s) < _PASS_THRESHOLD:
                        is_low_dim = True
                        break
        if is_low_overall or is_low_dim:
            out.append(slide)
    return out


def _overall(slide: Mapping[str, Any]) -> int:
    qs = slide.get("quality_score")
    if isinstance(qs, Mapping):
        v = qs.get("overall")
        if isinstance(v, (int, float)):
            return int(v)
    return 0


def _diagnose(slide: Mapping[str, Any]) -> str:
    """Return the dominant failing dimension for the started event."""
    qs = slide.get("quality_score")
    if not isinstance(qs, Mapping):
        return "unknown"
    dims = qs.get("dimensions") or {}
    if not isinstance(dims, Mapping):
        return "unknown"
    worst_key = None
    worst_score = 101
    for name in ("alignment", "density", "contrast"):
        d = dims.get(name)
        if isinstance(d, Mapping):
            s = d.get("score")
            if isinstance(s, (int, float)) and int(s) < worst_score:
                worst_score = int(s)
                worst_key = name
    if worst_key is None:
        return "unknown"
    if worst_key == "density":
        # Distinguish overshoot from undershoot — only overshoot is
        # deterministically fixable.
        d = dims.get("density") or {}
        cc = d.get("char_count")
        hi = d.get("target_max")
        if isinstance(cc, int) and isinstance(hi, int) and cc > hi:
            return "density_overshoot"
        return "density_undershoot"
    if worst_key == "alignment":
        return "alignment_defect"
    return "low_contrast"


# ── Remediation ──────────────────────────────────────────────────────


def _attempt_remediate(
    *,
    slide: dict[str, Any],
    tokens: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Try deterministic fixes. Returns either:
        {"status": "succeeded", "after_score": int, "fixes_applied": [...]}
    or:
        {"status": "skipped", "reason": str, "issues": [str, ...]}
    """
    artifacts = slide.get("artifacts")
    if not isinstance(artifacts, dict):
        return _skip("no_artifacts", ["slide.artifacts missing"])
    kit_jsx = artifacts.get("kit_jsx")
    if not isinstance(kit_jsx, dict):
        return _skip("no_kit_jsx_artifact", ["artifacts.kit_jsx missing"])
    kit = slide.get("kit_component") or kit_jsx.get("kit_component") or ""
    if kit not in _DENSITY_TARGETS:
        return _skip("unknown_kit", [f"kit={kit!r} not in registry"])

    props_json = kit_jsx.get("props_json")
    if not isinstance(props_json, dict):
        return _skip("no_props_json", ["kit_jsx.props_json missing"])

    # Deep copy so partial fixes don't corrupt the live artifact on
    # skip-paths.
    props = json.loads(json.dumps(props_json, ensure_ascii=False))
    fixes: list[str] = []

    # 1) Alignment fixes — surgical removal of broken sub-items.
    align_fixes = _apply_alignment_fixes(kit=kit, props=props)
    fixes.extend(align_fixes)

    # 2) Density truncation — only when overshooting the band.
    density_fixes = _apply_density_truncation(kit=kit, props=props)
    fixes.extend(density_fixes)

    if not fixes:
        # Nothing deterministic to try → leave for LLM retry.
        return _skip(
            "no_deterministic_fix",
            _alignment_unfixable_issues(slide),
        )

    # Re-score against the new props using the real Phase 4.5 scorer.
    new_score = score_slide(kit=kit, props=props, design_tokens=tokens)
    if new_score["overall"] < _PASS_THRESHOLD:
        # Improved but still below threshold — surface as skipped so
        # Phase 12 can take over. Leave the live artifact untouched.
        return _skip(
            "fixes_insufficient",
            [f"after_score={new_score['overall']} still < {_PASS_THRESHOLD}"]
            + fixes,
        )

    # Commit the new props + recompile every artifact slot.
    _commit_remediated_props(slide=slide, kit=kit, props=props, new_score=new_score)
    return {
        "status": "succeeded",
        "after_score": int(new_score["overall"]),
        "fixes_applied": fixes,
    }


def _skip(reason: str, issues: Sequence[str]) -> dict[str, Any]:
    return {"status": "skipped", "reason": reason, "issues": list(issues)}


def _alignment_unfixable_issues(slide: Mapping[str, Any]) -> list[str]:
    qs = slide.get("quality_score") or {}
    dims = qs.get("dimensions") or {}
    align = dims.get("alignment") if isinstance(dims, Mapping) else None
    if isinstance(align, Mapping):
        issues = align.get("issues") or []
        if isinstance(issues, list):
            return [str(i) for i in issues]
    return []


# ── Alignment fixes (surgical removal only) ──────────────────────────


def _apply_alignment_fixes(*, kit: str, props: dict[str, Any]) -> list[str]:
    """Remove broken sub-items the writer produced. Never invents data."""
    fixes: list[str] = []

    if kit == "DiagramBlock":
        nodes = props.get("nodes") or []
        edges = props.get("edges") or []
        if isinstance(nodes, list) and isinstance(edges, list):
            valid_ids = {
                n.get("id") for n in nodes
                if isinstance(n, dict) and isinstance(n.get("id"), str)
            }
            kept: list[Any] = []
            dropped = 0
            for e in edges:
                if not isinstance(e, dict):
                    dropped += 1
                    continue
                if e.get("from") in valid_ids and e.get("to") in valid_ids:
                    kept.append(e)
                else:
                    dropped += 1
            if dropped > 0:
                props["edges"] = kept
                fixes.append(f"drop_dangling_edges:{dropped}")

    if kit == "ChartBlock":
        data = props.get("data")
        y_keys = props.get("yKeys")
        if isinstance(data, list) and isinstance(y_keys, list) and y_keys:
            cleaned: list[Any] = []
            dropped = 0
            for row in data:
                if not isinstance(row, dict):
                    dropped += 1
                    continue
                # Keep rows that have at least one non-null numeric value
                # in any yKey.
                has_value = any(
                    isinstance(row.get(k), (int, float)) for k in y_keys
                )
                if has_value:
                    cleaned.append(row)
                else:
                    dropped += 1
            if dropped > 0:
                props["data"] = cleaned
                fixes.append(f"drop_empty_chart_rows:{dropped}")

    if kit == "StatHero":
        stats = props.get("stats")
        if isinstance(stats, list):
            cleaned = [
                s for s in stats
                if isinstance(s, dict)
                and (
                    (isinstance(s.get("value"), str) and s["value"].strip())
                    or (isinstance(s.get("label"), str) and s["label"].strip())
                )
            ]
            dropped = len(stats) - len(cleaned)
            if dropped > 0:
                props["stats"] = cleaned
                fixes.append(f"drop_empty_stats:{dropped}")

    if kit == "ComparisonBlock":
        rows = props.get("rows")
        if isinstance(rows, list):
            cleaned = [
                r for r in rows
                if isinstance(r, dict)
                and isinstance(r.get("values"), list)
                and len(r["values"]) > 0
            ]
            dropped = len(rows) - len(cleaned)
            if dropped > 0:
                props["rows"] = cleaned
                fixes.append(f"drop_empty_comparison_rows:{dropped}")

    if kit == "FeatureGrid":
        feats = props.get("features")
        if isinstance(feats, list):
            cleaned = [
                f for f in feats
                if isinstance(f, dict)
                and (
                    (isinstance(f.get("title"), str) and f["title"].strip())
                    or (isinstance(f.get("description"), str) and f["description"].strip())
                )
            ]
            dropped = len(feats) - len(cleaned)
            if dropped > 0:
                props["features"] = cleaned
                fixes.append(f"drop_empty_features:{dropped}")

    if kit == "TeamGrid":
        members = props.get("members")
        if isinstance(members, list):
            cleaned = [
                m for m in members
                if isinstance(m, dict)
                and isinstance(m.get("name"), str)
                and m["name"].strip()
            ]
            dropped = len(members) - len(cleaned)
            if dropped > 0:
                props["members"] = cleaned
                fixes.append(f"drop_empty_team_members:{dropped}")

    if kit == "TimelineBlock":
        miles = props.get("milestones")
        if isinstance(miles, list):
            cleaned = [
                m for m in miles
                if isinstance(m, dict)
                and (
                    (isinstance(m.get("date"), str) and m["date"].strip())
                    or (isinstance(m.get("label"), str) and m["label"].strip())
                )
            ]
            dropped = len(miles) - len(cleaned)
            if dropped > 0:
                props["milestones"] = cleaned
                fixes.append(f"drop_empty_milestones:{dropped}")

    return fixes


# ── Density truncation ───────────────────────────────────────────────


def _char_count(props: Mapping[str, Any]) -> int:
    return sum(len(s) for s in _collect_visible_text(props))


def _apply_density_truncation(*, kit: str, props: dict[str, Any]) -> list[str]:
    band = _DENSITY_TARGETS.get(kit)
    if band is None:
        return []
    _, hi = band
    cc = _char_count(props)
    if cc <= hi:
        return []

    fixes: list[str] = []
    # Iteratively shorten the longest user-visible string field until
    # the slide fits the band, hard-capped to prevent runaway loops.
    for _ in range(_MAX_TRUNCATION_PASSES):
        location = _find_longest_text_location(props)
        if location is None:
            break
        path, current = location
        # Truncate by ~25% (or down to band-fit, whichever is shorter)
        # and append an ellipsis. Never reduce below 24 chars — that's
        # the floor where text remains meaningful.
        overshoot = _char_count(props) - hi
        # Reduce by max(overshoot+3, 25% of current). +3 covers the
        # ellipsis we add.
        reduction = max(overshoot + 3, max(1, len(current) // 4))
        new_len = max(24, len(current) - reduction)
        if new_len >= len(current):
            break
        truncated = current[:new_len].rstrip()
        # Trim a trailing partial-word boundary so we don't cut mid-word
        # when there's a sensible space to break on.
        if " " in truncated[-20:]:
            truncated = truncated.rsplit(" ", 1)[0].rstrip()
        truncated = truncated.rstrip(",.;:- ") + "…"
        if not _set_at_path(props, path, truncated):
            break
        fixes.append(f"truncate:{_render_path(path)}")
        if _char_count(props) <= hi:
            break
    return fixes


def _find_longest_text_location(
    props: Mapping[str, Any],
) -> tuple[list[Any], str] | None:
    """
    Walk the props tree and return ``(path, text)`` of the single
    longest user-visible string. Excludes URL / structural fields per
    the same skip-set the quality scorer uses.
    """
    skip_keys = {
        "imageUrl", "photoUrl", "linkedInUrl", "logoUrl", "iconUrl",
        "variant", "orientation", "overlay", "align", "type",
        "xKey", "yKeys", "nameKey", "valueKey", "icon",
        "id", "from", "to", "style", "trend", "highlight", "done",
        "x", "y", "columns", "seriesLabels", "yKey",
    }
    best: tuple[list[Any], str] | None = None

    def walk(node: Any, path: list[Any], parent_key: str | None):
        nonlocal best
        if isinstance(node, str):
            if parent_key in skip_keys:
                return
            s = node
            if s and (best is None or len(s) > len(best[1])):
                best = (list(path), s)
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in skip_keys:
                    continue
                walk(v, path + [k], k)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, path + [i], parent_key)

    walk(props, [], None)
    return best


def _set_at_path(root: Any, path: Sequence[Any], value: str) -> bool:
    """Mutate ``root`` so the given path resolves to ``value``. Returns False on shape mismatch."""
    if not path:
        return False
    cursor: Any = root
    for step in path[:-1]:
        try:
            cursor = cursor[step]
        except (KeyError, IndexError, TypeError):
            return False
    last = path[-1]
    try:
        cursor[last] = value
        return True
    except (KeyError, IndexError, TypeError):
        return False


def _render_path(path: Sequence[Any]) -> str:
    parts: list[str] = []
    for step in path:
        if isinstance(step, int):
            parts.append(f"[{step}]")
        else:
            if parts:
                parts.append(f".{step}")
            else:
                parts.append(str(step))
    return "".join(parts)


# ── Commit (recompile artifacts) ─────────────────────────────────────


def _commit_remediated_props(
    *,
    slide: dict[str, Any],
    kit: str,
    props: dict[str, Any],
    new_score: dict[str, Any],
) -> None:
    """Rebuild every artifact slot with the cleaned props and bump the version."""
    artifacts = slide["artifacts"]
    animation_ir = slide.get("animation_ir")
    slide_id = slide.get("slide_id")

    # kit_jsx artifact — rebuild source via the existing JSX serialiser
    # in slide_compiler. Importing locally avoids a circular import.
    from app.services.v4.slide_compiler import _render_jsx  # type: ignore

    new_jsx = _render_jsx(kit=kit, props=props)
    artifacts["kit_jsx"] = {
        "source": new_jsx,
        "kit_component": kit,
        "props_json": json.loads(json.dumps(props, ensure_ascii=False)),
        "fingerprint": hashlib.sha1(new_jsx.encode("utf-8")).hexdigest()[:12],
    }
    # The legacy mirror at slide.jsx_source still feeds the runtime
    # path until the frontend Phase 7 hook ships.
    slide["jsx_source"] = new_jsx

    artifacts["engine"] = build_engine(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )
    layer_metadata = build_layer_metadata(
        slide_id=slide_id or "slide-000",
        kit=kit,
        engine_artifact=artifacts["engine"],
        animation_ir=animation_ir,
    )
    motion_spec = slide.get("motion_spec")
    if not isinstance(motion_spec, dict):
        motion_spec = build_motion_spec(
            intent=str(slide.get("intent") or props.get("intent") or ""),
            layout=str(slide.get("layout") or ""),
            kit=kit,
            animation_plan=slide.get("animation_plan") or {},
            animation_ir=animation_ir,
            layer_metadata=layer_metadata,
        )
    slide["motion_spec"] = motion_spec
    slide["html_layer_metadata"] = layer_metadata
    slide["render_qa"] = build_render_qa_plan(
        motion_spec=motion_spec,
        layer_metadata=layer_metadata,
    )
    slide["poster_frame"] = motion_spec.get("poster_frame")
    interaction_spec = build_slide_intelligence_spec(
        slide_id=slide_id or "slide-000",
        slide_index=int(slide.get("slide_index") or 0),
        intent=str(slide.get("intent") or props.get("intent") or ""),
        layout=str(slide.get("layout") or ""),
        kit=kit,
        props=props,
        layer_metadata=layer_metadata,
        motion_spec=motion_spec,
        design_tokens=slide.get("design_tokens") if isinstance(slide.get("design_tokens"), Mapping) else None,
        template_id=str(slide.get("template_id") or "") or None,
    )
    slide["interaction_spec"] = interaction_spec
    artifacts["kit_jsx"]["motion_spec"] = motion_spec
    artifacts["kit_jsx"]["layer_metadata"] = layer_metadata
    artifacts["kit_jsx"]["interaction_spec"] = interaction_spec
    artifacts["html_css_js"] = build_html_css_js(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
        deck_title=None,
        motion_spec=motion_spec,
        layer_metadata=layer_metadata,
    )
    if isinstance(artifacts["html_css_js"], dict):
        artifacts["html_css_js"]["interaction_spec"] = interaction_spec
    artifacts["reveal_legacy"] = build_reveal_legacy(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )

    slide["quality_score"] = new_score
    # Bump the artifact version so the frontend cache invalidates and
    # the hot-swap WS event flips its hash check.
    cur = slide.get("artifact_version") or 1
    if isinstance(cur, int):
        slide["artifact_version"] = cur + 1
    slide["hot_swap"] = {
        "applied": True,
        "score_after": int(new_score["overall"]),
    }


# ── Emit helper ──────────────────────────────────────────────────────


async def _safe_emit(
    emit: ProgressCallback | None,
    stage: str,
    payload: dict[str, Any],
) -> None:
    if emit is None:
        return
    try:
        await emit(stage, payload)
    except Exception as e:  # noqa: BLE001
        logger.warning("v4_hot_swap_emit_failed", stage=stage, error=str(e))
