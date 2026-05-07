"""
Visual Style Discovery Engine -- Phase 5.

Implements the Visual Style Discovery UX flow from the V7 plan:
1. Analyze user request / topic / purpose
2. Select 3 candidate style presets from different aesthetic families
3. Generate preview data for each candidate (colors, typography, mock layout)
4. User picks one, system applies across entire deck

Also includes the AI Template Selector (Section 12.2 of the plan):
- Analyzes content density, slide position, slide type, theme, and variety
- Selects optimal layout + typography + animation rules per slide

Based on frontend-slides anti-AI-slop presets (12 curated styles).
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.services.slides_new.themes.theme_models import (
    BuiltInThemes,
    ThemeDefinition,
    ThemeTier,
)
from app.services.slides_new.themes.css_compiler import CSSCompiler
from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine


# -- Style Preset Catalog ------------------------------------------------


class StyleFamily(str, Enum):
    """Aesthetic families for style discovery."""
    DARK_BOLD = "dark_bold"
    DARK_SUBTLE = "dark_subtle"
    LIGHT_CLEAN = "light_clean"
    LIGHT_WARM = "light_warm"
    SPECIALTY = "specialty"
    CREATIVE = "creative"


@dataclass
class StylePreview:
    """Preview data for a single style candidate."""
    preset_id: str
    preset_name: str
    family: StyleFamily
    theme: ThemeDefinition
    preview_css: str
    character: str
    when_to_use: str
    sample_colors: list[str]
    sample_fonts: dict[str, str]
    confidence: float = 0.0  # How well this matches the request


@dataclass
class StyleDiscoveryResult:
    """Result of the Visual Style Discovery process."""
    previews: list[StylePreview]
    recommended_index: int = 0  # Index of the recommended preview
    topic: str = ""
    purpose: str = ""
    reasoning: str = ""


# -- Style Preset Definitions ------------------------------------------------


# Maps each preset to metadata for intelligent selection
STYLE_PRESETS: dict[str, dict[str, Any]] = {
    # Dark presets
    "bold_signal": {
        "family": StyleFamily.DARK_BOLD,
        "character": "High contrast, dynamic, startup energy",
        "when_to_use": "Startup pitch, product launch, Series A",
        "keywords": ["startup", "pitch", "launch", "product", "energy", "bold"],
        "industries": ["tech", "saas", "fintech", "startup"],
        "audience": ["investors", "vcs", "board"],
    },
    "electric_studio": {
        "family": StyleFamily.DARK_BOLD,
        "character": "Futuristic, neon accents, tech aesthetic",
        "when_to_use": "AI/ML, deep tech, developer tools",
        "keywords": ["ai", "ml", "tech", "futuristic", "developer", "api"],
        "industries": ["ai", "ml", "devtools", "cloud", "infrastructure"],
        "audience": ["developers", "technical", "engineers"],
    },
    "dark_developer": {
        "family": StyleFamily.DARK_SUBTLE,
        "character": "Developer tools, code-first, terminal aesthetic",
        "when_to_use": "Developer tooling, open source, infrastructure",
        "keywords": ["developer", "code", "terminal", "devops", "infrastructure"],
        "industries": ["devtools", "open_source", "infrastructure"],
        "audience": ["developers", "engineers", "cto"],
    },
    "dark_botanical": {
        "family": StyleFamily.DARK_SUBTLE,
        "character": "Organic shapes, natural textures, earthy tones",
        "when_to_use": "Sustainability, health, wellness",
        "keywords": ["sustainability", "health", "wellness", "organic", "green"],
        "industries": ["healthtech", "sustainability", "biotech"],
        "audience": ["general", "consumers"],
    },
    "neon_cyber": {
        "family": StyleFamily.CREATIVE,
        "character": "Cyberpunk, gaming, high energy",
        "when_to_use": "Gaming, entertainment, esports",
        "keywords": ["gaming", "entertainment", "esports", "cyber", "neon"],
        "industries": ["gaming", "entertainment", "media"],
        "audience": ["gamers", "consumers", "media"],
    },
    "creative_voltage": {
        "family": StyleFamily.CREATIVE,
        "character": "Creative, energetic, bold geometry",
        "when_to_use": "Creative industry, design, media",
        "keywords": ["creative", "design", "media", "agency", "branding"],
        "industries": ["creative", "design", "media", "advertising"],
        "audience": ["creatives", "marketing", "brand"],
    },
    # Light presets
    "swiss_modern": {
        "family": StyleFamily.LIGHT_CLEAN,
        "character": "Minimal, grid, Helvetica, precise spacing",
        "when_to_use": "Finance, legal, institutional",
        "keywords": ["finance", "legal", "institutional", "banking", "consulting"],
        "industries": ["finance", "legal", "consulting", "government"],
        "audience": ["executives", "institutional", "board"],
    },
    "notebook_tabs": {
        "family": StyleFamily.LIGHT_CLEAN,
        "character": "Organized, tabbed, clean structure",
        "when_to_use": "Consulting, business plans, reports",
        "keywords": ["consulting", "report", "business_plan", "strategy", "organized"],
        "industries": ["consulting", "management", "professional_services"],
        "audience": ["executives", "clients", "stakeholders"],
    },
    "pastel_geometry": {
        "family": StyleFamily.LIGHT_WARM,
        "character": "Soft, approachable, friendly shapes",
        "when_to_use": "Education, consumer apps, community",
        "keywords": ["education", "consumer", "community", "friendly", "approachable"],
        "industries": ["edtech", "consumer", "community", "social"],
        "audience": ["students", "consumers", "community"],
    },
    "vintage_editorial": {
        "family": StyleFamily.LIGHT_WARM,
        "character": "Classic, editorial, serif typography",
        "when_to_use": "Luxury brands, fashion, heritage",
        "keywords": ["luxury", "fashion", "heritage", "editorial", "premium"],
        "industries": ["luxury", "fashion", "lifestyle", "publishing"],
        "audience": ["consumers", "luxury", "premium"],
    },
    # Specialty presets
    "terminal_green": {
        "family": StyleFamily.SPECIALTY,
        "character": "Phosphor green, monospace, hacker aesthetic",
        "when_to_use": "Cybersecurity, developer tooling, CLI products",
        "keywords": ["security", "cybersecurity", "hacker", "terminal", "cli"],
        "industries": ["security", "devtools", "infrastructure"],
        "audience": ["developers", "security", "engineers"],
    },
    "paper_and_ink": {
        "family": StyleFamily.SPECIALTY,
        "character": "Editorial, ink texture, classic look",
        "when_to_use": "Publishing, media, journalism, academic",
        "keywords": ["publishing", "academic", "journalism", "research", "paper"],
        "industries": ["publishing", "media", "academia", "research"],
        "audience": ["academics", "researchers", "media"],
    },
}


# -- Style Intelligence Engine ------------------------------------------------


class StyleIntelligenceEngine:
    """
    AI-powered style selection engine.

    Analyzes the user's topic, purpose, audience, and industry to
    recommend the best visual style presets.

    Scoring algorithm:
    1. Keyword match (topic/description words against preset keywords)
    2. Industry match (detected industry against preset industries)
    3. Audience match (target audience against preset audiences)
    4. Family diversity (ensure 3 picks span different families)
    """

    def __init__(self):
        self._themes = BuiltInThemes()
        self._css = CSSCompiler()
        self._engine = GenerativeThemeEngine()

    def discover_styles(
        self,
        topic: str = "",
        purpose: str = "",
        audience: str = "",
        industry: str = "",
        mood: str = "",
        count: int = 3,
    ) -> StyleDiscoveryResult:
        """
        Run Visual Style Discovery.

        Returns `count` style previews ranked by relevance.
        Ensures diversity across style families.

        Args:
            topic: Presentation topic (e.g., "AI Infrastructure Platform")
            purpose: Purpose (e.g., "investor pitch", "sales deck")
            audience: Target audience (e.g., "VCs", "developers")
            industry: Industry vertical (optional)
            mood: Desired mood (optional override)
            count: Number of previews to generate (default 3)

        Returns:
            StyleDiscoveryResult with ranked previews
        """
        # Tokenize inputs for matching
        query_tokens = _tokenize(f"{topic} {purpose} {audience} {industry} {mood}")

        # Score each preset
        scored: list[tuple[str, float, dict[str, Any]]] = []
        for preset_id, meta in STYLE_PRESETS.items():
            score = self._score_preset(preset_id, meta, query_tokens, purpose)
            scored.append((preset_id, score, meta))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        # Ensure family diversity in top picks
        selected = self._select_diverse(scored, count)

        # Build previews
        previews = []
        for preset_id, score, meta in selected:
            theme = self._get_or_build_theme(preset_id)
            css = self._css.compile(theme) if theme else ""
            previews.append(StylePreview(
                preset_id=preset_id,
                preset_name=preset_id.replace("_", " ").title(),
                family=meta["family"],
                theme=theme,
                preview_css=css[:500],  # Truncated preview
                character=meta["character"],
                when_to_use=meta["when_to_use"],
                sample_colors=[
                    theme.colors.primary,
                    theme.colors.accent,
                    theme.colors.background,
                ] if theme else [],
                sample_fonts={
                    "heading": theme.typography.heading_font if theme else "Inter",
                    "body": theme.typography.body_font if theme else "Inter",
                },
                confidence=round(score, 3),
            ))

        # Best match reasoning
        best = selected[0] if selected else ("unknown", 0, {})
        reasoning = (
            f"Recommended '{best[0]}' based on "
            f"topic='{topic}', purpose='{purpose}', audience='{audience}'. "
            f"Score: {best[1]:.2f}"
        )

        return StyleDiscoveryResult(
            previews=previews,
            recommended_index=0,
            topic=topic,
            purpose=purpose,
            reasoning=reasoning,
        )

    def _score_preset(
        self,
        preset_id: str,
        meta: dict[str, Any],
        query_tokens: set[str],
        purpose: str,
    ) -> float:
        """Score a preset against the query."""
        score = 0.0

        # Keyword match (0-40 points)
        keywords = set(meta.get("keywords", []))
        keyword_overlap = len(query_tokens & keywords)
        score += keyword_overlap * 10
        if keyword_overlap > 0:
            score += 5  # bonus for any match

        # Industry match (0-20 points)
        industries = set(meta.get("industries", []))
        industry_overlap = len(query_tokens & industries)
        score += industry_overlap * 10

        # Audience match (0-15 points)
        audiences = set(meta.get("audience", []))
        audience_overlap = len(query_tokens & audiences)
        score += audience_overlap * 5

        # Purpose bonus (0-15 points)
        purpose_lower = purpose.lower()
        if "pitch" in purpose_lower and "pitch" in " ".join(meta.get("keywords", [])):
            score += 15
        elif "sales" in purpose_lower and "sales" in " ".join(meta.get("keywords", [])):
            score += 15
        elif "consulting" in purpose_lower and "consulting" in " ".join(meta.get("keywords", [])):
            score += 15

        # Small random jitter for tie-breaking (0-2 points)
        seed = hashlib.md5(f"{preset_id}{query_tokens}".encode()).hexdigest()
        jitter = int(seed[:2], 16) / 128  # 0-2
        score += jitter

        return score

    def _select_diverse(
        self,
        scored: list[tuple[str, float, dict[str, Any]]],
        count: int,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """Select top-N with family diversity constraint."""
        selected = []
        families_used: set[StyleFamily] = set()

        # First pass: pick top from each unique family
        for item in scored:
            family = item[2]["family"]
            if family not in families_used:
                selected.append(item)
                families_used.add(family)
                if len(selected) >= count:
                    break

        # Second pass: fill remaining from top scores
        if len(selected) < count:
            for item in scored:
                if item not in selected:
                    selected.append(item)
                    if len(selected) >= count:
                        break

        return selected[:count]

    def _get_or_build_theme(self, preset_id: str) -> Optional[ThemeDefinition]:
        """Get theme for a preset — from built-in or generate."""
        # Try built-in themes first
        theme = self._themes.get(preset_id)
        if theme:
            return theme

        # Map preset to closest built-in by name similarity
        all_themes = self._themes.list_all()
        for t in all_themes:
            if preset_id.replace("_", "").lower() in t.id.replace("_", "").lower():
                return t

        # Fallback: return first available theme
        return all_themes[0] if all_themes else None


# -- Layout Template Selector ------------------------------------------------


class LayoutDecision:
    """Decision output from the AI Template Selector."""

    def __init__(
        self,
        layout: str,
        typography_scale: str = "default",
        animation_preset: str = "subtle",
        reasoning: str = "",
    ):
        self.layout = layout
        self.typography_scale = typography_scale
        self.animation_preset = animation_preset
        self.reasoning = reasoning

    def to_dict(self) -> dict[str, str]:
        return {
            "layout": self.layout,
            "typography_scale": self.typography_scale,
            "animation_preset": self.animation_preset,
            "reasoning": self.reasoning,
        }


# Typography rules from V7 plan Section 12.1
TYPOGRAPHY_RULES: dict[str, dict[str, str]] = {
    "professional": {"heading": "Inter", "body": "Inter", "mono": "JetBrains Mono"},
    "editorial": {"heading": "Playfair Display", "body": "Source Serif 4", "mono": "Fira Code"},
    "modern": {"heading": "Cal Sans", "body": "Inter", "mono": "Fira Code"},
    "playful": {"heading": "Nunito", "body": "Nunito Sans", "mono": "Fira Code"},
    "minimal": {"heading": "Helvetica Neue", "body": "Helvetica Neue", "mono": "SF Mono"},
    "tech": {"heading": "Space Grotesk", "body": "IBM Plex Sans", "mono": "IBM Plex Mono"},
}

# Animation rules from V7 plan Section 12.1
ANIMATION_RULES: dict[str, dict[str, Any]] = {
    "subtle": {
        "entrance": "fade-in",
        "duration": 0.3,
        "stagger": 0.1,
        "easing": "ease-out",
    },
    "dynamic": {
        "entrance": "slide-up",
        "duration": 0.5,
        "stagger": 0.15,
        "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
    },
    "cinematic": {
        "entrance": "scale-fade",
        "duration": 0.8,
        "stagger": 0.2,
        "easing": "cubic-bezier(0.22, 1, 0.36, 1)",
    },
    "none": {
        "entrance": "none",
        "duration": 0,
        "stagger": 0,
        "easing": "linear",
    },
}


class AITemplateSelector:
    """
    Layout Agent template selector (V7 plan Section 12.2).

    Analyzes content and selects optimal layout + typography + animation for
    each slide. Uses rule-based heuristics (no LLM call needed for basic decisions).

    Decision factors:
    1. Content density (words, bullets, images, charts)
    2. Slide position in deck (opening = dramatic, middle = informative)
    3. Slide type (title, content, data, closing)
    4. Previous slide layout (variety principle)
    5. User's selected theme (constrains style)
    """

    # Layout rules from V7 plan Section 12.1
    LAYOUT_RULES: dict[str, dict[str, Any]] = {
        "title-slide": {
            "conditions": {"has_subtitle": True},
            "layout": "center-focus",
            "animation": "cinematic",
        },
        "content-heavy": {
            "conditions": {"bullet_count_gt": 6, "has_image": False},
            "layout": "two-column",
            "animation": "subtle",
        },
        "visual-emphasis": {
            "conditions": {"has_hero_image": True, "word_count_lt": 30},
            "layout": "full-bleed",
            "animation": "dynamic",
        },
        "data-heavy": {
            "conditions": {"has_chart": True},
            "layout": "chart",
            "animation": "subtle",
        },
        "comparison": {
            "conditions": {"has_comparison": True},
            "layout": "comparison",
            "animation": "subtle",
        },
        "team": {
            "conditions": {"is_team": True},
            "layout": "team-grid",
            "animation": "dynamic",
        },
        "kpi": {
            "conditions": {"has_kpi": True},
            "layout": "kpi-dashboard",
            "animation": "dynamic",
        },
        "timeline": {
            "conditions": {"has_timeline": True},
            "layout": "timeline",
            "animation": "subtle",
        },
        "quote": {
            "conditions": {"is_quote": True},
            "layout": "quote",
            "animation": "cinematic",
        },
    }

    def select_layout(
        self,
        slide_content: dict[str, Any],
        slide_type: str = "custom",
        slide_index: int = 0,
        total_slides: int = 10,
        previous_layout: str = "",
    ) -> LayoutDecision:
        """
        Select optimal layout for a slide based on content analysis.

        Args:
            slide_content: Dict with content info (title, bullets, images, etc.)
            slide_type: SlideType value (title_slide, problem_slide, etc.)
            slide_index: Position in deck
            total_slides: Total deck size
            previous_layout: Layout of previous slide (for variety)

        Returns:
            LayoutDecision with layout, typography, and animation choices
        """
        # Analyze content
        features = self._extract_features(slide_content, slide_type)

        # Match against layout rules
        layout, animation = self._match_rules(features, slide_type)

        # Variety constraint: avoid repeating previous layout
        if layout == previous_layout and previous_layout:
            alternatives = self._get_alternative_layouts(features)
            for alt in alternatives:
                if alt != previous_layout:
                    layout = alt
                    break

        # Position-based overrides
        if slide_index == 0:
            animation = "cinematic"  # Opening slides are dramatic
        elif slide_index == total_slides - 1:
            animation = "cinematic"  # Closing slides are dramatic
        elif slide_index <= 2:
            animation = "dynamic"  # Early slides build energy

        # Typography scale
        if slide_index == 0:
            typo = "hero"
        elif features.get("is_data_heavy"):
            typo = "minimal"  # Smaller text for data-heavy slides
        else:
            typo = "default"

        reasoning = (
            f"Selected '{layout}' for {slide_type} slide "
            f"(position {slide_index + 1}/{total_slides}, "
            f"features: {list(k for k, v in features.items() if v)})"
        )

        return LayoutDecision(
            layout=layout,
            typography_scale=typo,
            animation_preset=animation,
            reasoning=reasoning,
        )

    def _extract_features(
        self,
        content: dict[str, Any],
        slide_type: str,
    ) -> dict[str, bool]:
        """Extract content features for rule matching."""
        bullets = content.get("bullets", [])
        body = content.get("body", "")
        title = content.get("title", "")
        subtitle = content.get("subtitle", "")
        images = content.get("images", [])
        charts = content.get("charts", [])
        kpis = content.get("kpis", [])

        word_count = len(body.split()) + sum(len(b.split()) for b in bullets)

        return {
            "has_subtitle": bool(subtitle),
            "bullet_count_gt": len(bullets) > 6,
            "has_image": bool(images),
            "has_hero_image": len(images) >= 1 and word_count < 30,
            "word_count_lt": word_count < 30,
            "has_chart": bool(charts),
            "has_kpi": bool(kpis) or slide_type == "traction_slide",
            "has_comparison": slide_type == "competition_slide",
            "has_timeline": "timeline" in str(content).lower(),
            "is_team": slide_type == "team_slide",
            "is_quote": "quote" in str(content).lower(),
            "is_data_heavy": bool(charts) or bool(kpis) or len(bullets) > 4,
        }

    def _match_rules(
        self,
        features: dict[str, bool],
        slide_type: str,
    ) -> tuple[str, str]:
        """Match features against layout rules and return (layout, animation)."""
        # Direct slide type matches
        type_layout_map = {
            "title_slide": ("center-focus", "cinematic"),
            "problem_slide": ("split-screen", "dynamic"),
            "solution_slide": ("text-left-visual-right", "dynamic"),
            "market_slide": ("chart", "subtle"),
            "traction_slide": ("kpi-dashboard", "dynamic"),
            "business_model_slide": ("grid-2x2", "subtle"),
            "team_slide": ("team-grid", "dynamic"),
            "financial_slide": ("chart", "subtle"),
            "competition_slide": ("comparison", "subtle"),
            "closing_slide": ("center-focus", "cinematic"),
        }

        if slide_type in type_layout_map:
            return type_layout_map[slide_type]

        # Feature-based matching (priority order)
        for rule_name, rule in self.LAYOUT_RULES.items():
            conditions = rule["conditions"]
            if all(features.get(k, False) == v for k, v in conditions.items()):
                return rule["layout"], rule.get("animation", "subtle")

        # Default
        if features.get("has_chart"):
            return "chart", "subtle"
        if features.get("has_image"):
            return "text-left-visual-right", "subtle"
        if features.get("bullet_count_gt"):
            return "two-column", "subtle"

        return "bullets", "subtle"

    def _get_alternative_layouts(
        self,
        features: dict[str, bool],
    ) -> list[str]:
        """Get alternative layouts compatible with the content."""
        alternatives = []

        if features.get("has_image"):
            alternatives.extend(["split-screen", "text-right-visual-left", "full-bleed"])
        if features.get("has_chart"):
            alternatives.extend(["top-bottom", "split-screen"])
        if features.get("bullet_count_gt"):
            alternatives.extend(["bullets", "grid-2x2"])
        if features.get("has_kpi"):
            alternatives.extend(["grid-3x1", "top-bottom"])

        alternatives.extend(["center-focus", "bullets", "top-bottom"])

        return alternatives


# -- Helpers ------------------------------------------------------------------


def _tokenize(text: str) -> set[str]:
    """Simple whitespace + punctuation tokenizer."""
    import re
    tokens = re.findall(r"[a-z0-9_]+", text.lower())
    return set(tokens)
