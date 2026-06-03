"""Design Memory — persistent design context for slide regeneration.

Remembers the last-used design tokens, visual direction, kit preferences,
and user overrides per presentation. On regeneration, restores the full
design context so the new slide matches the deck's existing aesthetic."""
from __future__ import annotations
from typing import Any, Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class DesignMemory:
    visual_direction: str
    design_tokens: dict[str, Any]
    kit_preferences: list[str]  # kits user explicitly picked
    color_overrides: dict[str, str]
    font_overrides: dict[str, str]
    last_updated: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DesignMemory":
        return cls(
            visual_direction=d.get("visual_direction", "minimal_dark"),
            design_tokens=d.get("design_tokens", {}),
            kit_preferences=d.get("kit_preferences", []),
            color_overrides=d.get("color_overrides", {}),
            font_overrides=d.get("font_overrides", {}),
            last_updated=d.get("last_updated"),
        )


def extract_design_memory(
    *,
    design_tokens: dict[str, Any],
    kit_id: Optional[str] = None,
    user_overrides: Optional[dict[str, Any]] = None,
) -> DesignMemory:
    """Build a DesignMemory snapshot from a generation context."""
    user_overrides = user_overrides or {}
    return DesignMemory(
        visual_direction=design_tokens.get("visual_direction", "minimal_dark"),
        design_tokens=design_tokens,
        kit_preferences=[kit_id] if kit_id else [],
        color_overrides=user_overrides.get("colors", {}),
        font_overrides=user_overrides.get("fonts", {}),
    )


def apply_design_memory(
    memory: DesignMemory,
    base_tokens: dict[str, Any],
) -> dict[str, Any]:
    """Merge stored memory into base tokens for regeneration."""
    merged = {**base_tokens}
    # Restore visual direction
    if memory.visual_direction:
        merged["visual_direction"] = memory.visual_direction
    # Restore color overrides
    if memory.color_overrides and "palette" in merged:
        merged["palette"] = {**merged.get("palette", {}), **memory.color_overrides}
    # Restore font overrides
    if memory.font_overrides and "fonts" in merged:
        merged["fonts"] = {**merged.get("fonts", {}), **memory.font_overrides}
    # Restore kit preferences as hints
    if memory.kit_preferences:
        merged["_preferred_kits"] = memory.kit_preferences
    return merged
