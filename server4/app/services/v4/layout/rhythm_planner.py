"""Deck-level layout rhythm planner for Plan 10.

The planner chooses among deterministic top candidates to avoid repetitive
adjacent kits while respecting content compatibility. It never forces a slide
into a kit that the intent engine did not consider eligible.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from app.services.v4.layout.intent_engine import LayoutCandidate, select_layout_candidates


def plan_layout_rhythm(
    *,
    slides: list[Any],
    deck_purpose: str = "",
    image_urls: Optional[Mapping[int, str]] = None,
    creative_directions: Optional[Mapping[int, Mapping[str, Any]]] = None,
) -> dict[int, LayoutCandidate]:
    image_urls = image_urls or {}
    creative_directions = creative_directions or {}
    selected: dict[int, LayoutCandidate] = {}
    previous_layouts: list[str] = []
    density_streak = 0
    last_density = ""

    for deck_index, slide in enumerate(slides):
        candidates = select_layout_candidates(
            slide=slide,
            deck_purpose=deck_purpose or getattr(slide, "purpose", "") or "",
            deck_index=deck_index,
            deck_total=len(slides),
            previous_layouts=tuple(previous_layouts),
            image_available=bool(image_urls.get(getattr(slide, "index", deck_index))),
            limit=4,
        )
        slide_index = int(getattr(slide, "index", deck_index) or deck_index)
        direction = creative_directions.get(slide_index) or {}
        chosen = _choose_candidate(
            candidates,
            previous_layouts,
            density_streak,
            last_density,
            direction,
        )
        selected[slide_index] = chosen
        previous_layouts.append(chosen.key)
        density = chosen.features.density
        density_streak = density_streak + 1 if density == last_density else 1
        last_density = density
    return selected


def _choose_candidate(
    candidates: list[LayoutCandidate],
    previous_layouts: list[str],
    density_streak: int,
    last_density: str,
    creative_direction: Optional[Mapping[str, Any]] = None,
) -> LayoutCandidate:
    if not candidates:
        raise ValueError("rhythm planner requires at least one candidate")
    if not previous_layouts:
        return candidates[0]
    last_key = previous_layouts[-1]
    last_kit = last_key.split(":", 1)[0]
    preferred_kits = tuple(
        str(k)
        for k in (creative_direction or {}).get("preferred_kits", ())
        if str(k).strip()
    )

    if preferred_kits:
        for candidate in candidates:
            if candidate.kit_id not in preferred_kits:
                continue
            if candidate.key == last_key:
                continue
            if candidate.kit_id == last_kit and len(candidates) > 1:
                continue
            if density_streak >= 2 and candidate.features.density == last_density:
                continue
            return candidate

    for candidate in candidates:
        if candidate.key == last_key:
            continue
        if candidate.kit_id == last_kit and len(candidates) > 1:
            continue
        if density_streak >= 2 and candidate.features.density == last_density:
            continue
        return candidate
    for candidate in candidates:
        if candidate.key != last_key:
            return candidate
    return candidates[0]
