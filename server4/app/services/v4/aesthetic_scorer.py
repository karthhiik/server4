"""Aesthetic Quality Scorer v2 — deterministic rule-based slide evaluation."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AestheticScore:
    typography: float; color: float; composition: float
    complexity: float; motion: float; overall: float
    critique: list[str] = field(default_factory=list)

def score_slide_aesthetic(*, slide: dict[str, Any], design_tokens: dict[str, Any],
                          kit_id: str, variant: str, element_count: int = 0) -> AestheticScore:
    critique: list[str] = []
    typography = _score_typography(design_tokens, kit_id, slide)
    color = _score_color(design_tokens)
    from .composition_engine import score_composition
    comp = score_composition(kit_id=kit_id, variant=variant,
        content_density=_density(slide), has_image=_has_image(slide),
        has_text=_has_text(slide), element_count=element_count,
        visual_direction=design_tokens.get("visual_direction"))
    composition = comp.overall * 10
    complexity = _score_complexity(kit_id, element_count, slide)
    motion = _score_motion(design_tokens, kit_id)
    overall = typography*0.20 + color*0.20 + composition*0.25 + complexity*0.15 + motion*0.20
    for name, val in [("Typography", typography), ("Color", color), ("Composition", composition),
                      ("Complexity", complexity), ("Motion", motion)]:
        if val < 7.0:
            critique.append(f"{name} {val:.1f}: needs improvement")
    return AestheticScore(round(typography,1), round(color,1), round(composition,1),
                            round(complexity,1), round(motion,1), round(overall,1), critique)

def _score_typography(tokens: dict[str, Any], kit_id: str, slide: dict[str, Any]) -> float:
    w = tokens.get("weights", {}); contrast = w.get("heading",700) - w.get("body",400)
    s = tokens.get("scale", {}); ratio = s.get("display",57)/max(s.get("body",14),1)
    score = 7.0 + (1.5 if contrast>=300 else 0.8 if contrast>=200 else -1.0)
    score += (1.0 if ratio>=4 else 0.5 if ratio>=3 else -0.8)
    if kit_id in {"CinematicHero","EditorialImage"}: score += 0.3
    hl = slide.get("headline",""); score -= (1.0 if len(hl)>80 else 0.5 if len(hl)>60 else 0)
    return min(10.0, max(0.0, score))

def _score_color(tokens: dict[str, Any]) -> float:
    p = tokens.get("palette",{}); score = 7.0
    # Check for sufficient contrast between primary and background
    bg = p.get("background","#ffffff")
    if bg.startswith("#") and len(bg) >= 6:
        is_dark = sum(int(bg[i:i+2],16) for i in (1,3,5)) < 384
        if is_dark and p.get("primary","#3b82f6").startswith("#"):
            score += 0.5  # Dark theme with colored primary
    # Check accent contrast
    accent = p.get("accent","#f59e0b")
    if accent and accent != p.get("primary"): score += 0.5
    return min(10.0, score)

def _score_complexity(kit_id: str, element_count: int, slide: dict[str, Any]) -> float:
    bullets = len(slide.get("bullets", []))
    ideal = {"CinematicHero": 2, "EditorialImage": 3, "GlassCard": 4, "TitleHero": 2, "StatHero": 2}
    target = ideal.get(kit_id, 4)
    deviation = abs(element_count - target)
    score = 8.0 - (deviation * 0.8) - (bullets * 0.15 if bullets > 6 else 0)
    return min(10.0, max(3.0, score))

def _score_motion(tokens: dict[str, Any], kit_id: str) -> float:
    anim = tokens.get("animation", {})
    entry = anim.get("entry_duration_ms", 600)
    score = 7.0
    if 400 <= entry <= 800: score += 1.0
    elif entry > 1200: score -= 1.5
    # Kinetic directions get motion bonus
    if tokens.get("visual_direction") in {"neon_futurism", "coral_energy"}:
        score += 0.5
    if kit_id == "CinematicHero": score += 0.5
    return min(10.0, max(0.0, score))

def _density(slide: dict[str, Any]) -> float:
    txt = len(slide.get("headline","")) + len(slide.get("body","")) + sum(len(b) for b in slide.get("bullets",[]))
    return min(1.0, txt / 500)

def _has_image(slide: dict[str, Any]) -> bool:
    return bool(slide.get("imageUrl") or slide.get("image_url"))

def _has_text(slide: dict[str, Any]) -> bool:
    return bool(slide.get("headline") or slide.get("body") or slide.get("bullets"))
