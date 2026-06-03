"""
V4 edit-intelligence service.

When the editor receives a partial slide patch (user added a bullet,
inserted a stat block, swapped an image, replaced a chart), the patch
endpoint must do more than overwrite the field — it has to:

  1. Decide whether the new element changes the slide's structural
     identity (a slide that gained a chart should re-layout to a
     chart-focused kit).
  2. Promote the layout if the user added rich content to a layout
     that can't visually carry it (e.g. ``title-only`` + bullets →
     ``two-column`` or ``bullet-points``).
  3. Demote the layout if the user *removed* content (e.g. a
     ``stat-hero`` slide whose stat blocks all got cleared should
     fall back to a content layout instead of rendering an empty
     stat tile).
  4. Preserve the user's explicit layout choice when the patch
     itself sets one — never override an explicit ``layout`` field.

Public API::

    plan = plan_edit_layout(
        current_slide={...},
        patch={...},
    )
    # plan: {
    #   "next_layout": str | None,    # only set when we want to swap
    #   "rationale": str,             # short reason for telemetry
    #   "elements_added": list[str],  # ['chart', 'bullets']
    #   "elements_removed": list[str],
    # }

Pure function — no DB / IO. Safe to call inline inside the patch path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import structlog

logger = structlog.get_logger(__name__)


_ELEMENT_FIELDS: tuple[str, ...] = (
    "headline",
    "subheadline",
    "body",
    "bullets",
    "stat_blocks",
    "chart",
    "table",
    "timeline",
    "comparison",
    "diagram",
    "quote",
    "image_url",
    "image_prompt",
    "team_members",
)

_VISUAL_FIELDS: tuple[str, ...] = (
    "stat_blocks", "chart", "table", "timeline",
    "comparison", "diagram", "quote", "team_members",
    "image_url",
)


# Layout promotions: when a slide gains a rich element it deserves a
# layout that surfaces it. Maps the new element → preferred layout key.
_PROMOTE_FOR_ELEMENT: dict[str, str] = {
    "chart": "chart-focus",
    "table": "table",
    "timeline": "timeline",
    "comparison": "comparison",
    "diagram": "diagram",
    "team_members": "team-grid",
    "stat_blocks": "stat-hero",
    "quote": "quote",
    "image_url": "image-full",
}

# Layout demotions: when a slide *loses* its only structural element,
# fall back to a content layout that doesn't expect that element.
_DEMOTE_FROM_LAYOUT: dict[str, str] = {
    "chart-focus": "two-column",
    "stat-hero": "two-column",
    "table": "two-column",
    "timeline": "bullet-points",
    "comparison": "two-column",
    "diagram": "two-column",
    "image-full": "two-column",
    "team-grid": "two-column",
    "quote": "title-only",
}


# Layouts where adding bullets / body should NOT change the layout — they
# already accept text content fine.
_TEXT_FRIENDLY_LAYOUTS: frozenset[str] = frozenset({
    "two-column", "bullet-points", "feature-grid", "title-only",
    "split-content", "split-overlap",
})


def _has(value: Any) -> bool:
    """Truthy in a typing-loose sense: empty list / dict / string is False."""
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    return True


def _classify(field_name: str, value: Any) -> str:
    """Returns ``"present"`` / ``"absent"`` for the supplied field value."""
    return "present" if _has(value) else "absent"


@dataclass
class EditPlan:
    next_layout: str | None = None
    rationale: str = ""
    elements_added: list[str] = field(default_factory=list)
    elements_removed: list[str] = field(default_factory=list)
    layout_params_patch: dict[str, Any] = field(default_factory=dict)


def plan_edit_layout(
    *,
    current_slide: Mapping[str, Any],
    patch: Mapping[str, Any],
) -> EditPlan:
    """Compute a layout plan for a single-slide patch.

    Args:
      current_slide: the slide as it lives in storage (compiled or raw).
      patch: the fields the user is changing (only the keys that
        appear in patch are considered part of the change).

    Returns:
      EditPlan describing the recommended layout shift, the elements
      that became present / absent because of the patch, and any
      layout_params adjustments to keep the rendering coherent.
    """
    plan = EditPlan()
    if not patch:
        plan.rationale = "no_patch"
        return plan

    explicit_layout = patch.get("layout")
    if isinstance(explicit_layout, str) and explicit_layout.strip():
        plan.next_layout = explicit_layout.strip()
        plan.rationale = "user_set_layout"
        return plan

    current_layout = str(current_slide.get("layout") or "").strip().lower()
    next_slide: dict[str, Any] = {**dict(current_slide), **dict(patch)}

    # Detect element changes (per-field present/absent flip).
    added: list[str] = []
    removed: list[str] = []
    for field_name in _ELEMENT_FIELDS:
        if field_name not in patch:
            continue
        before = _classify(field_name, current_slide.get(field_name))
        after = _classify(field_name, next_slide.get(field_name))
        if before == after:
            continue
        if after == "present":
            added.append(field_name)
        else:
            removed.append(field_name)

    plan.elements_added = added
    plan.elements_removed = removed

    if not added and not removed:
        plan.rationale = "no_structural_change"
        return plan

    # Promotion: if the user added a structural visual that the current
    # layout doesn't surface, swap to a layout designed for that visual.
    for visual in _VISUAL_FIELDS:
        if visual in added:
            preferred = _PROMOTE_FOR_ELEMENT.get(visual)
            if preferred and preferred != current_layout:
                plan.next_layout = preferred
                plan.rationale = f"promote_for_{visual}"
                # When promoting, reset density and emphasis so the new
                # layout doesn't inherit signature meant for prose.
                plan.layout_params_patch = {
                    "density_level": "rich" if visual in {"chart", "table", "timeline", "comparison"} else "balanced",
                    "emphasis": "data" if visual in {"chart", "table", "stat_blocks"} else "structure",
                }
                return plan

    # Demotion: if the user cleared the structural element that gives
    # the current layout its identity, fall back to a content layout.
    for visual in _VISUAL_FIELDS:
        if visual in removed and current_layout in _DEMOTE_FROM_LAYOUT:
            # Only demote if no OTHER structural visual remains on the slide.
            still_has_structural = any(
                _has(next_slide.get(other))
                for other in _VISUAL_FIELDS
                if other != visual
            )
            if not still_has_structural:
                fallback = _DEMOTE_FROM_LAYOUT[current_layout]
                if fallback and fallback != current_layout:
                    plan.next_layout = fallback
                    plan.rationale = f"demote_after_{visual}_removed"
                    plan.layout_params_patch = {
                        "density_level": "balanced",
                        "emphasis": "typography",
                    }
                    return plan

    # Text-only patch (added bullets / body / headline) on a non-text-
    # friendly layout — promote to a content layout that handles it.
    text_only_added = added and all(a in {"bullets", "body", "headline", "subheadline"} for a in added)
    if text_only_added and current_layout and current_layout not in _TEXT_FRIENDLY_LAYOUTS:
        # Skip if the slide still has its primary visual — text additions
        # are fine alongside an existing chart / table / timeline.
        still_has_structural = any(
            _has(next_slide.get(other)) for other in _VISUAL_FIELDS
        )
        if not still_has_structural:
            plan.next_layout = "two-column"
            plan.rationale = "promote_text_to_two_column"
            return plan

    plan.rationale = "structural_change_no_layout_swap"
    return plan


__all__ = ["plan_edit_layout", "EditPlan"]
