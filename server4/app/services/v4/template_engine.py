"""
Template Engine — Barise Presentation SaaS

Loads professional templates from template_definitions.json and provides
resolution, categorization, search, and recommendation APIs.

Usage:
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()
    templates = engine.get_by_category("pitch")
    resolved = engine.resolve_template("yc_pitch")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class TemplateDefinition:
    """A single template definition from the JSON registry."""

    id: str
    name: str
    category: str
    description: str
    slide_count_range: list[int]
    layout_structure: dict[str, Any]
    compatible_themes: list[str]
    tags: list[str] = field(default_factory=list)
    placeholder_rules: dict[str, Any] = field(default_factory=dict)
    thumbnail_theme: str = "midnight_navy"
    preview_content: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateDefinition":
        range_val = data.get("slide_count_range", [8, 12])
        if not isinstance(range_val, list) or len(range_val) < 2:
            range_val = [8, 12]
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            description=data.get("description", ""),
            slide_count_range=range_val,
            layout_structure=data.get("layout_structure", {"zones": []}),
            compatible_themes=data.get("compatible_themes", []),
            tags=data.get("tags", []),
            placeholder_rules=data.get("placeholder_rules", {}),
            thumbnail_theme=data.get("thumbnail_theme", "midnight_navy"),
            preview_content=data.get("preview_content", {}),
        )

    @property
    def min_slides(self) -> int:
        return self.slide_count_range[0]

    @property
    def max_slides(self) -> int:
        return self.slide_count_range[1] if len(self.slide_count_range) > 1 else self.slide_count_range[0]

    @property
    def required_zones(self) -> list[dict[str, Any]]:
        zones = self.layout_structure.get("zones", [])
        return [z for z in zones if z.get("required", False)]

    @property
    def optional_zones(self) -> list[dict[str, Any]]:
        zones = self.layout_structure.get("zones", [])
        return [z for z in zones if not z.get("required", False)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to API-friendly dict."""
        preview_content = self.preview_content or self._derived_preview_content()
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "slide_count_range": self.slide_count_range,
            "layout_structure": self.layout_structure,
            "compatible_themes": self.compatible_themes,
            "tags": self.tags,
            "placeholder_rules": self.placeholder_rules,
            "min_slides": self.min_slides,
            "max_slides": self.max_slides,
            "thumbnail_theme": self.thumbnail_theme,
            "preview_content": preview_content,
        }

    def get_kit_components(self) -> list[str]:
        """Return all kit component IDs used by this template."""
        zones = self.layout_structure.get("zones", [])
        return list({z.get("kit_component", "") for z in zones if z.get("kit_component")})

    def _derived_preview_content(self) -> dict[str, Any]:
        """Build a structural preview from the template contract itself.

        Some supplemental templates intentionally ship only layout zones.
        The frontend still needs a preview contract, so we expose those real
        zones as lightweight slide descriptors instead of hiding the template
        or inventing unsupported business content.
        """
        zones = self.layout_structure.get("zones", [])
        slides = []
        for index, zone in enumerate(zones[:4]):
            if not isinstance(zone, dict):
                continue
            zone_id = str(zone.get("id") or f"zone_{index + 1}")
            kit_component = str(zone.get("kit_component") or "TitleHero")
            slides.append(
                {
                    "type": zone_id,
                    "kit_component": kit_component,
                    "data": {
                        "eyebrow": self.category.replace("_", " ").title(),
                        "headline": zone_id.replace("_", " ").title(),
                        "subheadline": kit_component,
                    },
                }
            )
        return {"slides": slides}


class TemplateEngine:
    """Registry and resolution engine for all Barise templates."""

    _instance: Optional["TemplateEngine"] = None
    _templates: dict[str, TemplateDefinition] = {}
    _categories: list[dict[str, Any]] = []

    def __new__(cls) -> "TemplateEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        import structlog
        _logger = structlog.get_logger(__name__)
        
        # Load legacy templates
        path = os.path.join(os.path.dirname(__file__), "template_definitions.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._categories = data.get("categories", [])
            self._templates = {
                t["id"]: TemplateDefinition.from_dict(t)
                for t in data.get("templates", [])
            }
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            _logger.error("template_definitions_load_failed", path=path, error=str(e))
            self._categories = []
            self._templates = {}

        # Load Barise v27 templates (supplement/override)
        v27_path = os.path.join(os.path.dirname(__file__), "barise_templates_v27.json")
        if os.path.exists(v27_path):
            try:
                with open(v27_path, "r", encoding="utf-8") as f:
                    v27_data = json.load(f)

                # Merge categories (avoid duplicates by id)
                existing_cat_ids = {c["id"] for c in self._categories}
                for cat in v27_data.get("categories", []):
                    if cat["id"] not in existing_cat_ids:
                        self._categories.append(cat)

                # Merge templates (v27 overrides legacy on id conflict)
                for t in v27_data.get("templates", []):
                    self._templates[t["id"]] = TemplateDefinition.from_dict(t)
            except (json.JSONDecodeError, KeyError) as e:
                _logger.error("barise_templates_v27_load_failed", path=v27_path, error=str(e))

        # Load Barise v28 templates (vertical pitch supplement)
        v28_path = os.path.join(os.path.dirname(__file__), "barise_templates_v28.json")
        if os.path.exists(v28_path):
            try:
                with open(v28_path, "r", encoding="utf-8") as f:
                    v28_data = json.load(f)

                existing_cat_ids = {c["id"] for c in self._categories}
                for cat in v28_data.get("categories", []):
                    if cat["id"] not in existing_cat_ids:
                        self._categories.append(cat)

                for t in v28_data.get("templates", []):
                    self._templates[t["id"]] = TemplateDefinition.from_dict(t)
            except (json.JSONDecodeError, KeyError) as e:
                _logger.error("barise_templates_v28_load_failed", path=v28_path, error=str(e))

        # Load Barise v29 templates (content-first / YC / investor-friendly /
        # designed) plus their visual-system pairings.
        self._visual_systems: list[dict[str, Any]] = []
        v29_path = os.path.join(os.path.dirname(__file__), "barise_templates_v29.json")
        if os.path.exists(v29_path):
            try:
                with open(v29_path, "r", encoding="utf-8") as f:
                    v29_data = json.load(f)

                existing_cat_ids = {c["id"] for c in self._categories}
                for cat in v29_data.get("categories", []):
                    if cat["id"] not in existing_cat_ids:
                        self._categories.append(cat)

                for t in v29_data.get("templates", []):
                    self._templates[t["id"]] = TemplateDefinition.from_dict(t)

                # Visual systems pair templates with cohesive token sets.
                vs = v29_data.get("_visual_systems", {}).get("systems", [])
                if isinstance(vs, list):
                    self._visual_systems = vs
            except (json.JSONDecodeError, KeyError) as e:
                _logger.error("barise_templates_v29_load_failed", path=v29_path, error=str(e))
        
        # Defensive: ensure categories is always a list
        if self._categories is None:
            self._categories = []
        if self._templates is None:
            self._templates = {}

    # ── Public API ──────────────────────────────────────────────

    def get(self, template_id: str) -> Optional[TemplateDefinition]:
        return self._templates.get(template_id)

    def get_all(self) -> list[TemplateDefinition]:
        return list(self._templates.values())

    def get_by_category(self, category_id: str) -> list[TemplateDefinition]:
        return [t for t in self._templates.values() if t.category == category_id]

    def get_categories(self) -> list[dict[str, Any]]:
        return self._categories

    def get_visual_systems(self) -> list[dict[str, Any]]:
        """Return curated visual systems pairing templates with token sets.

        Each system is::

            {
              "id": str,         # stable id used in deck-session storage
              "label": str,      # human-readable name
              "direction": str,  # primary visual direction id
              "accent": str,     # secondary direction used for accents
              "templates": list[str]  # template ids that pair well
            }

        Defined in ``barise_templates_v29.json``. Returns ``[]`` if v29
        wasn't loaded (e.g. file missing) so callers degrade cleanly.
        """
        return list(getattr(self, "_visual_systems", []) or [])

    def search(self, query: str) -> list[TemplateDefinition]:
        q = query.lower()
        results = []
        for t in self._templates.values():
            if q in t.name.lower() or q in t.description.lower():
                results.append(t)
                continue
            if any(q in tag.lower() for tag in t.tags):
                results.append(t)
                continue
            if q in t.category.lower():
                results.append(t)
        return results

    def recommend(
        self,
        purpose: Optional[str] = None,
        industry: Optional[str] = None,
        slide_count: Optional[int] = None,
    ) -> list[TemplateDefinition]:
        """Recommend templates based on purpose, industry, and slide count."""

        purpose_map = {
            "pitch": ["pitch"],
            "investor": ["pitch"],
            "sales": ["sales"],
            "keynote": ["keynote"],
            "report": ["data", "report"],
            "product": ["product"],
            "demo": ["product", "sales"],
            "training": ["education", "training"],
            "conference": ["keynote"],
            "company": ["company"],
            "creative": ["creative"],
            "portfolio": ["creative"],
            "agency": ["creative", "company"],
            "workshop": ["education"],
            "course": ["education"],
        }

        industry_map = {
            "tech": ["product", "pitch", "keynote"],
            "software": ["saas", "product", "company", "data"],
            "healthcare": ["data", "education", "company"],
            "finance": ["pitch", "data"],
            "education": ["education", "company"],
            "security": ["data"],
            "gaming": ["product", "creative"],
            "agency": ["company", "sales", "creative"],
            "nonprofit": ["company", "education"],
            "design": ["creative"],
            "startup": ["pitch", "product", "company"],
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

        scored: list[tuple[float, TemplateDefinition]] = []
        for t in self._templates.values():
            score = 0.0
            if t.category in matched_cats:
                score += 2.0
            if slide_count is not None:
                if t.min_slides <= slide_count <= t.max_slides:
                    score += 1.5
                elif slide_count >= t.min_slides - 2 and slide_count <= t.max_slides + 2:
                    score += 0.5

            if score > 0:
                scored.append((score, t))

        scored.sort(key=lambda x: (-x[0], x[1].name))
        return [t for _, t in scored]

    def resolve_template(self, template_id: str) -> Optional[dict[str, Any]]:
        """Resolve a template to its full definition dict."""
        template = self._templates.get(template_id)
        if not template:
            return None
        return template.to_dict()

    def get_template_count(self) -> int:
        return len(self._templates)

    def validate_slide_count(self, template_id: str, slide_count: int) -> tuple[bool, str]:
        """Check if a slide count is valid for a template."""
        template = self._templates.get(template_id)
        if not template:
            return False, f"Template '{template_id}' not found"
        if slide_count < template.min_slides:
            return False, f"Minimum {template.min_slides} slides required for this template"
        if slide_count > template.max_slides:
            return False, f"Maximum {template.max_slides} slides allowed for this template"
        return True, "Valid"


# Convenience functions for direct import
_engine = TemplateEngine()


def get_template(template_id: str) -> Optional[TemplateDefinition]:
    return _engine.get(template_id)


def get_all_templates() -> list[TemplateDefinition]:
    return _engine.get_all()


def get_templates_by_category(category_id: str) -> list[TemplateDefinition]:
    return _engine.get_by_category(category_id)


def search_templates(query: str) -> list[TemplateDefinition]:
    return _engine.search(query)


def recommend_templates(
    purpose: Optional[str] = None,
    industry: Optional[str] = None,
    slide_count: Optional[int] = None,
) -> list[TemplateDefinition]:
    return _engine.recommend(purpose, industry, slide_count)


def resolve_template(template_id: str) -> Optional[dict[str, Any]]:
    return _engine.resolve_template(template_id)


def validate_slide_count(template_id: str, slide_count: int) -> tuple[bool, str]:
    return _engine.validate_slide_count(template_id, slide_count)
