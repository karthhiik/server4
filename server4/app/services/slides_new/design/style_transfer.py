"""
Style Transfer Intelligence — Phase 13 Integration.

Adapted from ArcadeAI/agent-style-transfer patterns:
- Style inference: Extract tone, formality, vocabulary, personality from reference content
- Style evaluation: 6-dimension scoring (fidelity, preservation, quality, audience fit,
  inference accuracy, rule usefulness)
- Specificity scoring: Adapted from gabelul/stitch-kit — score how specific a design
  request is to decide whether to run full ideation or skip to generation

Combined with stitch-kit patterns:
- Structured prompt format: [Context][Layout][Components]
- Specificity scoring to route vague vs precise requests

This module enhances DesignerAgent style discovery and TeacherAgent evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE INFERENCE — Adapted from ArcadeAI/agent-style-transfer
# ═══════════════════════════════════════════════════════════════════════════════


class Tone(str, Enum):
    """Presentation tone categories."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    AUTHORITATIVE = "authoritative"
    INSPIRATIONAL = "inspirational"
    TECHNICAL = "technical"
    PLAYFUL = "playful"
    URGENT = "urgent"
    EMPATHETIC = "empathetic"


class SentenceStructure(str, Enum):
    """Content structure patterns for slides."""
    SHORT_PUNCHY = "short_punchy"         # Headline-driven, few words per slide
    BALANCED = "balanced"                   # Mix of headlines and body text
    NARRATIVE = "narrative"                 # Story-driven, longer text blocks
    DATA_DRIVEN = "data_driven"            # Charts, stats, minimal text
    BULLET_HEAVY = "bullet_heavy"          # List-based content layout


class VocabularyLevel(str, Enum):
    """Content vocabulary complexity."""
    SIMPLE = "simple"           # General audience, plain language
    MODERATE = "moderate"       # Business audience, some jargon
    TECHNICAL = "technical"     # Domain experts, technical terms
    EXECUTIVE = "executive"     # C-suite, strategic language


@dataclass
class InferredStyle:
    """
    Inferred presentation style from user input.
    Adapted from ArcadeAI's ReferenceStyle schema.
    """
    tone: Tone = Tone.PROFESSIONAL
    formality_level: float = 0.7  # 0.0 (casual) → 1.0 (formal)
    sentence_structure: SentenceStructure = SentenceStructure.BALANCED
    vocabulary_level: VocabularyLevel = VocabularyLevel.MODERATE
    personality_traits: list[str] = field(default_factory=lambda: ["confident", "clear"])
    writing_patterns: dict[str, Any] = field(default_factory=dict)

    # Visual style implications
    visual_energy: float = 0.6    # 0.0 (calm/minimal) → 1.0 (high-energy/bold)
    color_warmth: float = 0.5     # 0.0 (cool/corporate) → 1.0 (warm/friendly)
    whitespace_ratio: float = 0.5  # 0.0 (dense) → 1.0 (spacious)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE EVALUATION — 6+1 Dimension Scoring
# Adapted from ArcadeAI evaluation.py + our TeacherAgent dimensions
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class StyleEvaluationDimension:
    """Single evaluation dimension with score and feedback."""
    name: str
    score: float = 0.0       # 0.0 to 1.0
    weight: float = 1.0      # Relative importance
    feedback: str = ""
    suggestions: list[str] = field(default_factory=list)


@dataclass
class StyleEvaluation:
    """
    Multi-dimensional style evaluation result.
    Combines ArcadeAI's 6 dimensions with our presentation-specific metrics.
    """
    # ArcadeAI-inspired dimensions
    style_fidelity: StyleEvaluationDimension = field(
        default_factory=lambda: StyleEvaluationDimension(
            name="style_fidelity",
            weight=1.2,
            feedback="How well the output matches the intended style"
        )
    )
    content_preservation: StyleEvaluationDimension = field(
        default_factory=lambda: StyleEvaluationDimension(
            name="content_preservation",
            weight=1.0,
            feedback="Key information retained without distortion"
        )
    )
    output_quality: StyleEvaluationDimension = field(
        default_factory=lambda: StyleEvaluationDimension(
            name="output_quality",
            weight=1.0,
            feedback="Overall polish and professionalism"
        )
    )
    audience_fit: StyleEvaluationDimension = field(
        default_factory=lambda: StyleEvaluationDimension(
            name="audience_fit",
            weight=1.1,
            feedback="Appropriateness for target audience"
        )
    )
    style_inference_accuracy: StyleEvaluationDimension = field(
        default_factory=lambda: StyleEvaluationDimension(
            name="style_inference_accuracy",
            weight=0.8,
            feedback="How accurately the style was inferred from input"
        )
    )
    visual_cohesion: StyleEvaluationDimension = field(
        default_factory=lambda: StyleEvaluationDimension(
            name="visual_cohesion",
            weight=1.3,
            feedback="Consistent visual language across all slides"
        )
    )
    # Presentation-specific dimension
    narrative_support: StyleEvaluationDimension = field(
        default_factory=lambda: StyleEvaluationDimension(
            name="narrative_support",
            weight=1.0,
            feedback="Visual design reinforces the story arc"
        )
    )

    @property
    def dimensions(self) -> list[StyleEvaluationDimension]:
        """All evaluation dimensions."""
        return [
            self.style_fidelity,
            self.content_preservation,
            self.output_quality,
            self.audience_fit,
            self.style_inference_accuracy,
            self.visual_cohesion,
            self.narrative_support,
        ]

    @property
    def weighted_score(self) -> float:
        """Weighted average across all dimensions."""
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight == 0:
            return 0.0
        return sum(d.score * d.weight for d in self.dimensions) / total_weight

    @property
    def grade(self) -> str:
        """Letter grade from weighted score."""
        s = self.weighted_score
        if s >= 0.9:
            return "A"
        elif s >= 0.8:
            return "B"
        elif s >= 0.7:
            return "C"
        elif s >= 0.6:
            return "D"
        return "F"


# ═══════════════════════════════════════════════════════════════════════════════
# SPECIFICITY SCORING — Adapted from stitch-kit
# Determines whether a request needs full ideation or can skip to generation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SpecificityScore:
    """
    How specific a design request is.
    High score → skip ideation, go straight to generation.
    Low score → run full ideation pipeline (CEO → research → design discovery).
    """
    total: float = 0.0            # 0.0 (vague) → 1.0 (fully specified)
    has_colors: bool = False       # User provided hex colors or palette name
    has_layout: bool = False       # User specified layout preferences
    has_typography: bool = False   # User specified fonts or font style
    has_audience: bool = False     # Clear target audience identified
    has_purpose: bool = False      # Clear business purpose
    has_industry: bool = False     # Specific industry context
    has_style_ref: bool = False    # References a visual style
    has_brand: bool = False        # Company branding provided
    reasoning: str = ""

    @property
    def needs_ideation(self) -> bool:
        """Whether this request should go through full ideation."""
        return self.total < 0.5

    @property
    def ideation_depth(self) -> str:
        """Recommended ideation depth."""
        if self.total >= 0.7:
            return "minimal"   # Quick style selection
        elif self.total >= 0.4:
            return "standard"  # Normal discovery flow
        return "deep"          # Full research + ideation


# ═══════════════════════════════════════════════════════════════════════════════
# INFERENCE ENGINE — Stateless functions
# ═══════════════════════════════════════════════════════════════════════════════


# Keyword signals for style inference
_TONE_KEYWORDS: dict[Tone, list[str]] = {
    Tone.PROFESSIONAL: ["enterprise", "corporate", "business", "b2b", "saas"],
    Tone.CASUAL: ["fun", "creative", "community", "social", "casual"],
    Tone.AUTHORITATIVE: ["research", "data", "analysis", "scientific", "study"],
    Tone.INSPIRATIONAL: ["vision", "mission", "change", "impact", "future"],
    Tone.TECHNICAL: ["api", "sdk", "developer", "infrastructure", "architecture"],
    Tone.PLAYFUL: ["game", "app", "mobile", "consumer", "entertainment"],
    Tone.URGENT: ["urgent", "critical", "crisis", "problem", "pain"],
    Tone.EMPATHETIC: ["health", "wellness", "care", "patient", "support"],
}

_PURPOSE_FORMALITY: dict[str, float] = {
    "fundraising": 0.8,
    "investor": 0.85,
    "board": 0.9,
    "internal": 0.5,
    "sales": 0.7,
    "marketing": 0.6,
    "education": 0.6,
    "general": 0.5,
    "conference": 0.65,
    "demo": 0.55,
}

_AUDIENCE_VOCABULARY: dict[str, VocabularyLevel] = {
    "investors": VocabularyLevel.EXECUTIVE,
    "vcs": VocabularyLevel.EXECUTIVE,
    "board": VocabularyLevel.EXECUTIVE,
    "developers": VocabularyLevel.TECHNICAL,
    "engineers": VocabularyLevel.TECHNICAL,
    "technical": VocabularyLevel.TECHNICAL,
    "general": VocabularyLevel.SIMPLE,
    "consumers": VocabularyLevel.SIMPLE,
    "students": VocabularyLevel.SIMPLE,
    "business": VocabularyLevel.MODERATE,
    "managers": VocabularyLevel.MODERATE,
}

# Hex color pattern for specificity detection
_HEX_PATTERN_CHARS = set("0123456789abcdefABCDEF#")


def infer_style(
    topic: str,
    purpose: str = "",
    audience: str = "",
    description: str = "",
    company_name: str | None = None,
) -> InferredStyle:
    """
    Infer presentation style from user input.
    Adapted from ArcadeAI's writing_style_inferrer pattern.

    Uses keyword matching + heuristics (no LLM call needed).
    """
    combined = f"{topic} {purpose} {audience} {description}".lower()
    style = InferredStyle()

    # -- Tone inference
    best_tone = Tone.PROFESSIONAL
    best_score = 0
    for tone, keywords in _TONE_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in combined)
        if matches > best_score:
            best_score = matches
            best_tone = tone
    style.tone = best_tone

    # -- Formality level from purpose
    purpose_lower = purpose.lower()
    for key, level in _PURPOSE_FORMALITY.items():
        if key in purpose_lower:
            style.formality_level = level
            break

    # -- Vocabulary from audience
    audience_lower = audience.lower()
    for key, vocab in _AUDIENCE_VOCABULARY.items():
        if key in audience_lower:
            style.vocabulary_level = vocab
            break

    # -- Sentence structure from content type
    if any(kw in combined for kw in ["data", "metrics", "chart", "analytics"]):
        style.sentence_structure = SentenceStructure.DATA_DRIVEN
    elif any(kw in combined for kw in ["story", "journey", "narrative", "case study"]):
        style.sentence_structure = SentenceStructure.NARRATIVE
    elif any(kw in combined for kw in ["pitch", "investor", "startup"]):
        style.sentence_structure = SentenceStructure.SHORT_PUNCHY

    # -- Personality traits
    traits = []
    if style.tone in (Tone.PROFESSIONAL, Tone.AUTHORITATIVE):
        traits.extend(["confident", "precise"])
    if style.tone in (Tone.INSPIRATIONAL, Tone.EMPATHETIC):
        traits.extend(["warm", "visionary"])
    if style.tone in (Tone.PLAYFUL, Tone.CASUAL):
        traits.extend(["approachable", "energetic"])
    if style.tone == Tone.TECHNICAL:
        traits.extend(["methodical", "detail-oriented"])
    style.personality_traits = traits or ["confident", "clear"]

    # -- Visual energy from purpose/audience
    if any(kw in combined for kw in ["startup", "launch", "pitch", "game"]):
        style.visual_energy = 0.8
    elif any(kw in combined for kw in ["board", "financial", "research", "analysis"]):
        style.visual_energy = 0.3

    # -- Color warmth from audience
    if any(kw in combined for kw in ["health", "wellness", "education", "community"]):
        style.color_warmth = 0.7
    elif any(kw in combined for kw in ["enterprise", "finance", "legal", "corporate"]):
        style.color_warmth = 0.3

    # -- Whitespace from vocabulary level
    if style.vocabulary_level == VocabularyLevel.EXECUTIVE:
        style.whitespace_ratio = 0.7  # Executives want clean, spacious
    elif style.vocabulary_level == VocabularyLevel.TECHNICAL:
        style.whitespace_ratio = 0.3  # Dense information ok
    elif style.vocabulary_level == VocabularyLevel.SIMPLE:
        style.whitespace_ratio = 0.6

    # -- Writing patterns
    style.writing_patterns = {
        "brand_mentioned": company_name is not None,
        "topic_length": len(topic.split()),
        "has_description": bool(description.strip()),
    }

    return style


def score_specificity(
    topic: str,
    purpose: str = "",
    audience: str = "",
    description: str = "",
    custom_theme: dict[str, Any] | None = None,
    company_name: str | None = None,
) -> SpecificityScore:
    """
    Score how specific a design request is.
    Adapted from stitch-kit's specificity scoring system.

    High score → skip ideation, design directly.
    Low score → run full ideation (CEO brainstorming, research, style discovery).
    """
    combined = f"{topic} {purpose} {audience} {description}".lower()
    score = SpecificityScore()
    points = 0.0
    max_points = 8.0

    # Check for hex colors
    words = combined.split()
    for word in words:
        clean = word.strip(".,;:")
        if (
            len(clean) in (4, 7)
            and clean.startswith("#")
            and all(c in _HEX_PATTERN_CHARS for c in clean)
        ):
            score.has_colors = True
            points += 1.0
            break

    # Check custom theme
    if custom_theme:
        if custom_theme.get("colors") or custom_theme.get("palette"):
            score.has_colors = True
            points += 1.0
        if custom_theme.get("fonts") or custom_theme.get("typography"):
            score.has_typography = True
            points += 1.0

    # Layout keywords
    layout_kw = ["grid", "sidebar", "split", "columns", "layout", "header", "hero"]
    if any(kw in combined for kw in layout_kw):
        score.has_layout = True
        points += 1.0

    # Font/typography keywords
    font_kw = ["font", "serif", "sans-serif", "monospace", "inter", "roboto", "poppins"]
    if any(kw in combined for kw in font_kw):
        score.has_typography = True
        points += 1.0

    # Audience
    if audience.strip():
        score.has_audience = True
        points += 1.0

    # Purpose
    if purpose.strip():
        score.has_purpose = True
        points += 1.0

    # Industry signals
    industry_kw = [
        "fintech", "healthtech", "edtech", "saas", "e-commerce", "biotech",
        "real-estate", "logistics", "automotive", "energy", "media", "gaming",
    ]
    if any(kw in combined for kw in industry_kw):
        score.has_industry = True
        points += 1.0

    # Style references
    style_kw = [
        "minimal", "bold", "dark", "light", "modern", "retro", "neon",
        "gradient", "glass", "brutalist", "swiss", "art deco", "bauhaus",
    ]
    if any(kw in combined for kw in style_kw):
        score.has_style_ref = True
        points += 1.0

    # Brand/company
    if company_name:
        score.has_brand = True
        points += 1.0

    score.total = min(points / max_points, 1.0)

    # Build reasoning
    present = []
    missing = []
    for attr, label in [
        ("has_colors", "colors"), ("has_layout", "layout"), ("has_typography", "typography"),
        ("has_audience", "audience"), ("has_purpose", "purpose"), ("has_industry", "industry"),
        ("has_style_ref", "style reference"), ("has_brand", "brand"),
    ]:
        if getattr(score, attr):
            present.append(label)
        else:
            missing.append(label)

    score.reasoning = (
        f"Specificity {score.total:.0%}. "
        f"Present: {', '.join(present) or 'none'}. "
        f"Missing: {', '.join(missing) or 'none'}. "
        f"Ideation: {score.ideation_depth}."
    )

    return score


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURED PROMPT FORMAT — Adapted from stitch-kit
# [Context][Layout][Components] pattern for designer prompts
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class StructuredDesignPrompt:
    """
    Structured design prompt following stitch-kit's [Context][Layout][Components] pattern.
    Produces better results than unstructured prompts for LLM-based design generation.
    """
    # [Context] section
    topic: str = ""
    purpose: str = ""
    audience: str = ""
    industry: str = ""
    mood: str = ""

    # [Layout] section
    slide_type: str = ""
    layout_preference: str = ""
    content_density: str = "medium"  # low, medium, high
    grid: str = ""

    # [Components] section
    components: list[str] = field(default_factory=list)
    icon_style: str = "outline"   # outline, filled, light
    chart_type: str = ""
    image_style: str = ""

    # Style inference
    inferred_style: InferredStyle | None = None

    def to_prompt_string(self) -> str:
        """Convert to structured prompt string for LLM consumption."""
        sections = []

        # [Context]
        ctx_parts = []
        if self.topic:
            ctx_parts.append(f"Topic: {self.topic}")
        if self.purpose:
            ctx_parts.append(f"Purpose: {self.purpose}")
        if self.audience:
            ctx_parts.append(f"Audience: {self.audience}")
        if self.industry:
            ctx_parts.append(f"Industry: {self.industry}")
        if self.mood:
            ctx_parts.append(f"Mood: {self.mood}")
        if self.inferred_style:
            ctx_parts.append(f"Tone: {self.inferred_style.tone.value}")
            ctx_parts.append(f"Formality: {self.inferred_style.formality_level:.1f}")
            ctx_parts.append(f"Visual Energy: {self.inferred_style.visual_energy:.1f}")
        if ctx_parts:
            sections.append("[Context]\n" + "\n".join(ctx_parts))

        # [Layout]
        layout_parts = []
        if self.slide_type:
            layout_parts.append(f"Slide Type: {self.slide_type}")
        if self.layout_preference:
            layout_parts.append(f"Layout: {self.layout_preference}")
        if self.content_density:
            layout_parts.append(f"Content Density: {self.content_density}")
        if self.grid:
            layout_parts.append(f"Grid: {self.grid}")
        if layout_parts:
            sections.append("[Layout]\n" + "\n".join(layout_parts))

        # [Components]
        comp_parts = []
        if self.components:
            comp_parts.append(f"Required: {', '.join(self.components)}")
        if self.icon_style:
            comp_parts.append(f"Icon Style: {self.icon_style}")
        if self.chart_type:
            comp_parts.append(f"Chart: {self.chart_type}")
        if self.image_style:
            comp_parts.append(f"Image: {self.image_style}")
        if comp_parts:
            sections.append("[Components]\n" + "\n".join(comp_parts))

        return "\n\n".join(sections)


def build_design_prompt(
    topic: str,
    purpose: str = "",
    audience: str = "",
    slide_type: str = "",
    components: list[str] | None = None,
    description: str = "",
    company_name: str | None = None,
) -> StructuredDesignPrompt:
    """
    Build a structured design prompt from user inputs.
    Combines style inference with stitch-kit structured format.
    """
    style = infer_style(topic, purpose, audience, description, company_name)
    specificity = score_specificity(topic, purpose, audience, description, company_name=company_name)

    # Determine mood from style
    mood_map = {
        Tone.PROFESSIONAL: "polished, trustworthy",
        Tone.CASUAL: "relaxed, approachable",
        Tone.AUTHORITATIVE: "commanding, credible",
        Tone.INSPIRATIONAL: "uplifting, visionary",
        Tone.TECHNICAL: "precise, structured",
        Tone.PLAYFUL: "fun, dynamic",
        Tone.URGENT: "intense, action-oriented",
        Tone.EMPATHETIC: "warm, supportive",
    }

    # Determine content density from style
    density_map = {
        SentenceStructure.SHORT_PUNCHY: "low",
        SentenceStructure.BALANCED: "medium",
        SentenceStructure.NARRATIVE: "high",
        SentenceStructure.DATA_DRIVEN: "medium",
        SentenceStructure.BULLET_HEAVY: "high",
    }

    return StructuredDesignPrompt(
        topic=topic,
        purpose=purpose,
        audience=audience,
        mood=mood_map.get(style.tone, "professional"),
        slide_type=slide_type,
        content_density=density_map.get(style.sentence_structure, "medium"),
        components=components or [],
        inferred_style=style,
    )
