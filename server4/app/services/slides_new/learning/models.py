"""
Learning System Models — Data structures for the self-evolving presentation engine.

Inspired by Hermes Agent's closed learning loop:
- DesignLesson: A discrete insight learned from a generation (like Hermes memory entries)
- DesignPattern: A recurring design pattern detected across generations (like Hermes skills)
- TeacherFeedback: Structured evaluation from the Teacher Agent (like Hermes background review)
- LearningSnapshot: Point-in-time snapshot of learning state (like Hermes memory flush)
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LessonCategory(str, Enum):
    """Categories of design lessons the system can learn."""

    COLOR_PALETTE = "color_palette"
    TYPOGRAPHY = "typography"
    LAYOUT = "layout"
    BACKGROUND = "background"
    ANIMATION = "animation"
    VISUAL_HIERARCHY = "visual_hierarchy"
    CONTENT_DENSITY = "content_density"
    IMAGERY = "imagery"
    BRAND_COHESION = "brand_cohesion"
    SLIDE_TRANSITIONS = "slide_transitions"
    CHART_DESIGN = "chart_design"
    SPACING = "spacing"
    CONTRAST = "contrast"
    READABILITY = "readability"
    EMOTIONAL_IMPACT = "emotional_impact"
    AUDIENCE_FIT = "audience_fit"


class LessonSentiment(str, Enum):
    """Whether the lesson is positive (do this) or negative (avoid this)."""

    POSITIVE = "positive"  # "This worked well"
    NEGATIVE = "negative"  # "This should be avoided"
    NEUTRAL = "neutral"  # Observation without value judgment


class PatternStrength(str, Enum):
    """How strong/reliable a detected pattern is."""

    EMERGING = "emerging"  # Seen 2-3 times
    ESTABLISHED = "established"  # Seen 4-9 times
    PROVEN = "proven"  # Seen 10+ times with consistent quality
    DECLINING = "declining"  # Was established but recent failures


class DesignLesson(BaseModel):
    """
    A discrete design insight learned from a single generation.
    Analogous to a Hermes memory entry — an atomic fact about what works or doesn't.

    Examples:
    - "Gradient-mesh backgrounds scored 12% higher than solid backgrounds on title slides"
    - "3-column layouts with team photos need minimum 1200px width or faces crop badly"
    - "VC audience prefers dark themes with accent highlights over bright corporate themes"
    """

    id: str = Field(default_factory=lambda: f"lesson_{uuid.uuid4().hex[:12]}")
    category: LessonCategory
    sentiment: LessonSentiment
    summary: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Concise lesson text",
    )
    details: Optional[str] = Field(
        default=None,
        description="Extended explanation with context",
    )
    slide_type: Optional[str] = Field(
        default=None,
        description="Specific slide type this lesson applies to (or None for global)",
    )
    audience_type: Optional[str] = Field(
        default=None,
        description="Audience type this lesson applies to",
    )
    purpose: Optional[str] = Field(
        default=None,
        description="Presentation purpose this applies to",
    )
    quality_delta: float = Field(
        default=0.0,
        description="Quality score impact observed (-100 to +100)",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How confident we are in this lesson",
    )
    source_presentation_id: Optional[str] = Field(
        default=None,
        description="Which presentation this was learned from",
    )
    source_quality_score: float = Field(
        default=0.0,
        description="Quality score of the presentation that taught this",
    )
    times_applied: int = Field(
        default=0,
        description="How many times this lesson was used in generation",
    )
    times_validated: int = Field(
        default=0,
        description="How many times applying this lesson improved quality",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def effectiveness_rate(self) -> float:
        """How often applying this lesson actually helps."""
        if self.times_applied == 0:
            return 0.0
        return self.times_validated / self.times_applied

    def to_prompt_line(self) -> str:
        """Convert to a concise prompt injection line."""
        prefix = "DO" if self.sentiment == LessonSentiment.POSITIVE else "AVOID"
        scope = f" [{self.slide_type}]" if self.slide_type else ""
        return f"- {prefix}{scope}: {self.summary} (confidence: {self.confidence:.0%})"


class DesignPattern(BaseModel):
    """
    A recurring design pattern detected across multiple generations.
    Analogous to Hermes skills — a reusable capability that improves over time.

    Examples:
    - "Dark gradient + glass card" combo for fintech pitches
    - "Timeline with icon markers" pattern for traction slides
    - "Metric dashboard grid" layout for KPI slides
    """

    id: str = Field(default_factory=lambda: f"pattern_{uuid.uuid4().hex[:12]}")
    name: str = Field(..., description="Short pattern name")
    description: str = Field(..., description="What this pattern does")
    categories: List[LessonCategory] = Field(default_factory=list)
    strength: PatternStrength = Field(default=PatternStrength.EMERGING)

    # Pattern specification
    design_spec: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured design specification (colors, layout, etc.)",
    )
    applicable_slide_types: List[str] = Field(
        default_factory=list,
        description="Slide types this pattern works well for",
    )
    applicable_audiences: List[str] = Field(
        default_factory=list,
        description="Audience types this pattern suits",
    )
    applicable_purposes: List[str] = Field(
        default_factory=list,
        description="Purposes this pattern suits",
    )

    # Evolution tracking
    version: int = Field(default=1)
    occurrence_count: int = Field(default=1)
    avg_quality_score: float = Field(default=0.0)
    quality_scores: List[float] = Field(
        default_factory=list,
        description="Quality scores from presentations using this pattern",
    )
    contributing_lessons: List[str] = Field(
        default_factory=list,
        description="IDs of lessons that formed this pattern",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def record_usage(self, quality_score: float) -> None:
        """Record a usage of this pattern with its quality outcome."""
        self.occurrence_count += 1
        self.quality_scores.append(quality_score)
        # Keep last 50 scores
        if len(self.quality_scores) > 50:
            self.quality_scores = self.quality_scores[-50:]
        self.avg_quality_score = (
            sum(self.quality_scores) / len(self.quality_scores)
        )
        self._update_strength()
        self.updated_at = datetime.now(timezone.utc)

    def _update_strength(self) -> None:
        """Update pattern strength based on usage and quality."""
        if self.occurrence_count >= 10 and self.avg_quality_score >= 75:
            self.strength = PatternStrength.PROVEN
        elif self.occurrence_count >= 4:
            # Check if recent quality is declining
            recent = self.quality_scores[-5:]
            if len(recent) >= 3 and all(s < 70 for s in recent):
                self.strength = PatternStrength.DECLINING
            else:
                self.strength = PatternStrength.ESTABLISHED
        else:
            self.strength = PatternStrength.EMERGING


class TeacherDimension(BaseModel):
    """A single dimension of the Teacher's evaluation."""

    name: str
    score: float = Field(..., ge=0.0, le=100.0)
    grade: str = Field(..., description="A-F grade")
    observations: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class TeacherFeedback(BaseModel):
    """
    Structured evaluation from the Teacher Agent.
    Analogous to Hermes _spawn_background_review() output —
    a comprehensive review that extracts lessons and patterns.
    """

    id: str = Field(default_factory=lambda: f"teach_{uuid.uuid4().hex[:12]}")
    presentation_id: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    overall_grade: str

    # Multi-dimensional evaluation
    dimensions: List[TeacherDimension] = Field(default_factory=list)

    # Extracted lessons
    lessons_learned: List[DesignLesson] = Field(default_factory=list)

    # Cross-slide analysis
    cohesion_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="How well slides work together as a coherent deck",
    )
    narrative_flow_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="How well the visual design supports the narrative arc",
    )
    brand_consistency_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="How consistent brand elements are across slides",
    )

    # Improvement directives for future generations
    style_directives: List[str] = Field(
        default_factory=list,
        description="Specific style rules to apply in future generations",
    )
    anti_patterns: List[str] = Field(
        default_factory=list,
        description="Specific anti-patterns to avoid",
    )

    # Comparison with past performance
    improvement_over_baseline: Optional[float] = Field(
        default=None,
        description="Quality delta vs historical average for this type",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_prompt_context(self) -> str:
        """Convert feedback into context that can be injected into future prompts."""
        lines = [
            "## Teacher Feedback from Previous Generations",
            f"Overall Quality: {self.overall_grade} ({self.overall_score:.0f}/100)",
            f"Design Cohesion: {self.cohesion_score:.0f}/100",
            f"Narrative Flow: {self.narrative_flow_score:.0f}/100",
            "",
        ]
        if self.style_directives:
            lines.append("### Style Rules (Learned)")
            for d in self.style_directives[:10]:
                lines.append(f"- {d}")
            lines.append("")
        if self.anti_patterns:
            lines.append("### Anti-Patterns (Avoid)")
            for a in self.anti_patterns[:10]:
                lines.append(f"- {a}")
        return "\n".join(lines)


class LearningSnapshot(BaseModel):
    """
    Point-in-time snapshot of the learning system's state.
    Analogous to Hermes flush_memories() — captures current knowledge.
    """

    id: str = Field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:12]}")
    total_presentations_analyzed: int = 0
    total_lessons: int = 0
    total_patterns: int = 0
    avg_quality_all_time: float = 0.0
    avg_quality_recent: float = Field(
        default=0.0,
        description="Average quality of last 20 presentations",
    )
    quality_trend: str = Field(
        default="stable",
        description="improving | stable | declining",
    )
    top_patterns: List[str] = Field(
        default_factory=list,
        description="Names of top-performing patterns",
    )
    most_impactful_lessons: List[str] = Field(
        default_factory=list,
        description="Summaries of most impactful lessons",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class GenerationRecord(BaseModel):
    """
    A record of a completed presentation generation for the learning system.
    This is what the Teacher reviews and learns from.
    """

    presentation_id: str
    user_id: str
    topic: str
    purpose: str
    audience: str
    slide_count: int
    quality_score: float
    quality_passed: bool

    # Agent outputs summary
    strategy_summary: Optional[str] = None
    design_choices: Dict[str, Any] = Field(default_factory=dict)
    layout_choices: Dict[str, Any] = Field(default_factory=dict)
    slide_types_used: List[str] = Field(default_factory=list)

    # Metrics
    total_latency_ms: int = 0
    qa_iterations: int = 0
    agent_metrics: Dict[str, Any] = Field(default_factory=dict)

    # QA feedback
    qa_issues: List[str] = Field(default_factory=list)
    qa_recommendations: List[str] = Field(default_factory=list)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
