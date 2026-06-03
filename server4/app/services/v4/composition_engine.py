"""
Visual Composition Engine v2

Analyzes slide layout candidates for:
- Golden ratio alignment (phi-based proportions)
- Visual weight balance (symmetry vs intentional asymmetry)
- Whitespace ratio (information density vs breathing room)
- Alignment quality (grid adherence)
- Focal point strength (visual hierarchy concentration)

Scores are deterministic (no LLM). Used by layout intent engine
to rank candidates and by critic for post-generation validation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional


# Golden ratio
_PHI = (1 + math.sqrt(5)) / 2  # ~1.618


@dataclass
class CompositionScore:
    golden_ratio: float      # 0-1: how close to phi proportions
    balance: float           # 0-1: visual weight distribution
    whitespace: float        # 0-1: appropriate negative space
    alignment: float         # 0-1: grid adherence quality
    focal_point: float       # 0-1: clear hierarchy center
    overall: float           # 0-1: weighted composite


def rhythm_window_score(kit_sequence: list[str], *, window_size: int = 5) -> dict[str, Any]:
    """Score deck-level kit variety for rolling windows.

    Slice 9's generation bar is at least three distinct kit components in any
    five-slide window. This helper is deterministic and side-effect free so the
    compiler, gate, and tests can share the same definition.
    """
    clean = [str(kit or "").strip() for kit in kit_sequence]
    windows: list[dict[str, Any]] = []
    if window_size <= 0:
        window_size = 5
    for start in range(0, max(0, len(clean) - window_size + 1)):
        window = [kit for kit in clean[start:start + window_size] if kit]
        distinct = len(set(window))
        windows.append(
            {
                "start": start,
                "end": start + window_size - 1,
                "distinct_components": distinct,
                "passes": distinct >= 3,
                "components": window,
            }
        )
    return {
        "passes": all(window["passes"] for window in windows) if windows else True,
        "window_size": window_size,
        "windows": windows,
    }


def score_composition(
    *,
    kit_id: str,
    variant: str,
    content_density: float = 0.5,  # 0=sparse, 1=dense
    has_image: bool = False,
    has_text: bool = True,
    element_count: int = 3,
    visual_direction: Optional[str] = None,
) -> CompositionScore:
    """Score a layout candidate's compositional quality."""

    # Golden ratio scoring based on known layout types
    golden = _golden_ratio_score(kit_id, variant, has_image)

    # Balance: different layouts have different ideal balance profiles
    balance = _balance_score(kit_id, variant, has_image, element_count)

    # Whitespace: context-dependent ideal ratio
    whitespace = _whitespace_score(
        kit_id, variant, content_density, visual_direction
    )

    # Alignment: structured layouts score higher on grid adherence
    alignment = _alignment_score(kit_id, variant)

    # Focal point: hero/title layouts need strong focal points
    focal = _focal_point_score(kit_id, variant, element_count)

    # Weighted composite: balance and whitespace most important
    overall = (
        golden * 0.15 +
        balance * 0.25 +
        whitespace * 0.25 +
        alignment * 0.15 +
        focal * 0.20
    )

    return CompositionScore(
        golden_ratio=round(golden, 3),
        balance=round(balance, 3),
        whitespace=round(whitespace, 3),
        alignment=round(alignment, 3),
        focal_point=round(focal, 3),
        overall=round(overall, 3),
    )


def _golden_ratio_score(kit_id: str, variant: str, has_image: bool) -> float:
    """Score how well the layout uses golden ratio proportions."""
    # EditorialImage asymmetric splits are near phi
    if kit_id == "EditorialImage":
        return 0.92 if has_image else 0.65
    # SplitContent and similar 2-column layouts
    if kit_id in {"SplitContent", "ComparisonBlock"}:
        return 0.78
    # CinematicHero uses full-bleed (no ratio needed)
    if kit_id == "CinematicHero":
        return 0.85
    # BentoGrid naturally creates phi-like proportions
    if kit_id == "BentoGrid":
        return 0.88
    # StatHero with 3 stats creates 1:1:1 (not phi)
    if kit_id == "StatHero":
        return 0.70
    # DataTable uses a strong header/body rectangle with proportional columns
    if kit_id == "DataTable":
        return 0.82
    # TitleHero is center-weighted (no ratio)
    if kit_id == "TitleHero":
        return 0.75
    return 0.72


def _balance_score(
    kit_id: str, variant: str, has_image: bool, element_count: int
) -> float:
    """Score visual weight distribution."""
    # Asymmetric layouts with images are intentionally unbalanced
    if kit_id == "EditorialImage" and has_image:
        return 0.88  # Intentional asymmetry is good
    # CinematicHero is bottom-heavy (intentional)
    if kit_id == "CinematicHero":
        return 0.90
    # GlassCard grid is evenly distributed
    if kit_id == "GlassCard":
        return 0.92
    # Tables distribute visual weight evenly across rows and columns
    if kit_id == "DataTable":
        return 0.90
    # Single-stat is perfectly centered
    if kit_id == "StatHero" and element_count <= 2:
        return 0.95
    # FeatureGrid with many items can feel unbalanced
    if kit_id == "FeatureGrid" and element_count > 4:
        return 0.72
    # TitleHero is typically well-balanced
    if kit_id == "TitleHero":
        return 0.88
    return 0.80


def _whitespace_score(
    kit_id: str,
    variant: str,
    content_density: float,
    visual_direction: Optional[str],
) -> float:
    """Score appropriate use of negative space."""
    # Swiss/editorial directions need more whitespace
    spacious_bonus = 0.12 if visual_direction in {
        "swiss_editorial", "warm_narrative", "luxury_gold",
        "earth_organic", "sage_calm",
    } else 0.0

    # Compact directions tolerate less whitespace
    compact_penalty = -0.10 if visual_direction in {
        "bold_contrast", "neon_futurism", "obsidian_tech",
    } else 0.0

    # CinematicHero is intentionally spacious
    if kit_id == "CinematicHero":
        base = 0.92
    # GlassCard needs moderate whitespace for glass effect
    elif kit_id == "GlassCard":
        base = 0.85
    # EditorialImage uses whitespace as a design element
    elif kit_id == "EditorialImage":
        base = 0.88
    # TitleHero with low density is good
    elif kit_id == "TitleHero":
        base = 0.90 if content_density < 0.4 else 0.72
    # StatHero needs breathing room around big numbers
    elif kit_id == "StatHero":
        base = 0.85
    # Data tables are dense by design, but still need a clear header/body split
    elif kit_id == "DataTable":
        base = 0.82
    else:
        base = 0.78

    return min(1.0, max(0.0, base + spacious_bonus + compact_penalty))


def _alignment_score(kit_id: str, variant: str) -> float:
    """Score grid adherence and alignment quality."""
    # Swiss editorial is grid-locked
    if kit_id in {"EditorialImage", "SplitContent"}:
        return 0.92
    # GlassCard uses strict grid
    if kit_id == "GlassCard":
        return 0.90
    # DataTable is the strictest grid component in the kit
    if kit_id == "DataTable":
        return 0.94
    # BentoGrid is inherently grid-aligned
    if kit_id == "BentoGrid":
        return 0.88
    # CinematicHero is intentionally freeform
    if kit_id == "CinematicHero":
        return 0.75
    # TitleHero is typically center or left aligned
    if kit_id == "TitleHero":
        return 0.82
    return 0.78


def _focal_point_score(kit_id: str, variant: str, element_count: int) -> float:
    """Score clarity of visual hierarchy center."""
    # CinematicHero has very strong focal point (big headline)
    if kit_id == "CinematicHero":
        return 0.95
    # EditorialImage has image as focal point
    if kit_id == "EditorialImage":
        return 0.88
    # StatHero numbers are strong focal points
    if kit_id == "StatHero":
        return 0.92 if element_count <= 2 else 0.78
    # TitleHero headline is the focal point
    if kit_id == "TitleHero":
        return 0.90
    # GlassCard distributes focus across cards (weaker single focal)
    if kit_id == "GlassCard":
        return 0.72
    # FeatureGrid similar
    if kit_id == "FeatureGrid":
        return 0.70
    # DataTable hierarchy is the header row plus first-column labels
    if kit_id == "DataTable":
        return 0.82
    return 0.75


def golden_ratio_split(total: float) -> tuple[float, float]:
    """Split a dimension into golden ratio proportions."""
    a = total / _PHI
    b = total - a
    return a, b


def is_near_golden_ratio(a: float, b: float, tolerance: float = 0.08) -> bool:
    """Check if two values are in approximately golden ratio."""
    if a <= 0 or b <= 0:
        return False
    ratio = max(a, b) / min(a, b)
    return abs(ratio - _PHI) <= tolerance
