"""
Theme Engine — Barise Presentation SaaS

Loads 100+ professional themes from theme_definitions.json and provides
resolution, categorization, search, and recommendation APIs.

Usage:
    from app.services.v4.theme_engine import ThemeEngine
    engine = ThemeEngine()
    themes = engine.get_by_category("startup")
    resolved = engine.resolve_theme("midnight_navy")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ThemeDefinition:
    """A single theme definition from the JSON registry."""

    id: str
    name: str
    categories: list[str]
    primary: str
    accent: str
    background: str
    heading_font: str
    body_font: str
    density: str = "comfortable"
    motion_style: str = "minimal"
    layout_posture: str = "structured"
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThemeDefinition":
        return cls(
            id=data["id"],
            name=data["name"],
            categories=data.get("categories", []),
            primary=data["primary"],
            accent=data["accent"],
            background=data["background"],
            heading_font=data["heading_font"],
            body_font=data["body_font"],
            density=data.get("density", "comfortable"),
            motion_style=data.get("motion_style", "minimal"),
            layout_posture=data.get("layout_posture", "structured"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )

    def to_visual_direction_dict(self) -> dict[str, Any]:
        """Convert to the existing VisualDirection shape used by design_resolver."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "primary": self.primary,
            "accent": self.accent,
            "background": self.background,
            "heading_font": self.heading_font,
            "body_font": self.body_font,
            "density": self.density,
            "motion_style": self.motion_style,
            "layout_posture": self.layout_posture,
            "anti_patterns": self._derive_anti_patterns(),
        }

    def _derive_anti_patterns(self) -> list[str]:
        """Derive anti-patterns from layout posture and motion style."""
        patterns: list[str] = []
        if self.layout_posture == "swiss":
            patterns.extend([
                "shadows", "rounded corners > 4px", "gradients",
                "more than 3 font weights", "centered body text",
            ])
        elif self.layout_posture == "expressive":
            patterns.extend([
                "pastel colors", "thin font weights < 400",
                "small type < 14pt", "busy backgrounds behind text",
            ])
        elif self.layout_posture == "editorial":
            patterns.extend([
                "neon colors", "tech gradients", "monospace body text",
                "more than 4 bullets per slide",
            ])
        elif self.layout_posture == "structured":
            patterns.extend([
                "gradients on text", "rounded cards with shadows",
                "more than 2 colors per slide", "decorative illustrations",
            ])

        if self.motion_style == "minimal":
            patterns.extend(["overly complex animations", "parallax effects"])
        elif self.motion_style == "kinetic":
            patterns.extend(["static layouts", "no visual movement"])

        return patterns

    @property
    def is_dark(self) -> bool:
        """Heuristic: dark theme if background luminance < 0.5 (approx)."""
        bg = self.background.lstrip("#")
        if len(bg) == 6:
            r = int(bg[0:2], 16) / 255
            g = int(bg[2:4], 16) / 255
            b = int(bg[4:6], 16) / 255
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return luminance < 0.5
        return False


class ThemeEngine:
    """Registry and resolution engine for all Barise themes."""

    _instance: Optional["ThemeEngine"] = None
    _themes: dict[str, ThemeDefinition] = {}
    _categories: list[dict[str, Any]] = []

    def __new__(cls) -> "ThemeEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        path = os.path.join(os.path.dirname(__file__), "theme_definitions.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._categories = data.get("categories", [])
        self._themes = {
            t["id"]: ThemeDefinition.from_dict(t)
            for t in data.get("themes", [])
        }

    # ── Public API ──────────────────────────────────────────────

    def get(self, theme_id: str) -> Optional[ThemeDefinition]:
        return self._themes.get(theme_id)

    def get_all(self) -> list[ThemeDefinition]:
        return list(self._themes.values())

    def get_by_category(self, category_id: str) -> list[ThemeDefinition]:
        return [t for t in self._themes.values() if category_id in t.categories]

    def get_categories(self) -> list[dict[str, Any]]:
        return self._categories

    def search(self, query: str) -> list[ThemeDefinition]:
        q = query.lower()
        results = []
        for t in self._themes.values():
            if q in t.name.lower() or q in t.description.lower():
                results.append(t)
                continue
            if any(q in tag.lower() for tag in t.tags):
                results.append(t)
                continue
            if any(q in cat.lower() for cat in t.categories):
                results.append(t)
        return results

    @staticmethod
    def _unique(themes: list[ThemeDefinition]) -> list[ThemeDefinition]:
        """Preserve recommendation order while removing duplicate theme IDs."""
        seen: set[str] = set()
        unique: list[ThemeDefinition] = []
        for theme in themes:
            if theme.id in seen:
                continue
            seen.add(theme.id)
            unique.append(theme)
        return unique

    def recommend(self, purpose: Optional[str] = None, industry: Optional[str] = None) -> list[ThemeDefinition]:
        """Recommend themes based on purpose and industry."""
        if not purpose and not industry:
            # Return top-rated across categories
            return self._unique(self.get_by_category("startup")[:3] + self.get_by_category("enterprise")[:3])

        purpose_map = {
            "pitch": ["startup", "enterprise"],
            "investor": ["startup", "fintech", "enterprise"],
            "sales": ["enterprise", "saas"],
            "keynote": ["modern", "creative"],
            "report": ["enterprise", "minimal"],
            "product": ["startup", "modern"],
            "demo": ["startup", "ai_tech"],
            "training": ["edtech", "minimal"],
            "conference": ["modern", "creative"],
        }

        industry_map = {
            "tech": ["ai_tech", "startup", "saas"],
            "software": ["saas", "enterprise", "ai_tech"],
            "healthcare": ["healthcare", "edtech"],
            "finance": ["fintech", "enterprise"],
            "education": ["edtech", "creative"],
            "security": ["cybersecurity", "enterprise"],
            "gaming": ["gaming", "ai_tech"],
            "agency": ["creative", "modern"],
            "nonprofit": ["edtech", "healthcare"],
        }

        matched_cats: set[str] = set()
        if purpose:
            p = purpose.lower()
            for key, cats in purpose_map.items():
                if key in p:
                    matched_cats.update(cats)
        if industry:
            i = industry.lower()
            for key, cats in industry_map.items():
                if key in i:
                    matched_cats.update(cats)

        if not matched_cats:
            matched_cats = {"startup", "enterprise"}

        scored: list[tuple[float, ThemeDefinition]] = []
        for t in self._themes.values():
            score = sum(1 for cat in t.categories if cat in matched_cats)
            if score > 0:
                scored.append((score, t))

        scored.sort(key=lambda x: (-x[0], x[1].name))
        return self._unique([t for _, t in scored])

    def resolve_theme(self, theme_id: str) -> Optional[dict[str, Any]]:
        """Resolve a theme to the full design-token-compatible dict."""
        theme = self._themes.get(theme_id)
        if not theme:
            return None
        return theme.to_visual_direction_dict()

    def get_theme_count(self) -> int:
        return len(self._themes)


# Convenience functions for direct import
_engine = ThemeEngine()


def get_theme(theme_id: str) -> Optional[ThemeDefinition]:
    return _engine.get(theme_id)


def get_all_themes() -> list[ThemeDefinition]:
    return _engine.get_all()


def get_themes_by_category(category_id: str) -> list[ThemeDefinition]:
    return _engine.get_by_category(category_id)


def search_themes(query: str) -> list[ThemeDefinition]:
    return _engine.search(query)


def recommend_themes(purpose: Optional[str] = None, industry: Optional[str] = None) -> list[ThemeDefinition]:
    return _engine.recommend(purpose, industry)


def resolve_theme(theme_id: str) -> Optional[dict[str, Any]]:
    return _engine.resolve_theme(theme_id)
