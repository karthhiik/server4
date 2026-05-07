"""
Slide Skill Models — Data structures for the self-evolving Code Agent.

Each slide type (title, problem, solution, etc.) is a learnable skill
that improves over time through quality feedback loops.

Based on the yoyo-evolve pattern from the V7 plan.
"""

import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SkillGenerationMode(str, Enum):
    """Whether the Code Agent should use reasoning or fast completion."""

    INSTANT = "instant"  # Fast, no reasoning — simple slide types
    THINKING = "thinking"  # Deep reasoning — complex layouts, 3D, charts


class SlideSkillType(str, Enum):
    """Known slide types that map to learnable skills."""

    TITLE_HERO = "title-hero"
    TITLE_CONTENT = "title-content"
    PROBLEM = "problem"
    SOLUTION = "solution"
    MARKET = "market"
    TRACTION = "traction"
    TEAM = "team"
    COMPETITION = "competition"
    BUSINESS_MODEL = "business-model"
    FINANCIALS = "financials"
    ASK = "ask"
    CLOSING = "closing"
    BULLETS = "bullets"
    TWO_COLUMN = "two-column"
    IMAGE_LEFT = "image-left"
    IMAGE_RIGHT = "image-right"
    CHART_FOCUS = "chart-focus"
    KPI_DASHBOARD = "kpi-dashboard"
    TIMELINE = "timeline"
    QUOTE = "quote"
    COMPARISON = "comparison"
    SECTION_HEADER = "section-header"
    CUSTOM = "custom"


class SkillFailurePattern(BaseModel):
    """
    A known failure pattern that the Code Agent should avoid.
    Stored per-skill and injected into the prompt as negative examples.
    """

    id: str = Field(default_factory=lambda: f"fail_{uuid.uuid4().hex[:8]}")
    description: str = Field(
        ..., description="What went wrong (e.g. 'Title truncated on 1080p')"
    )
    qa_feedback: str = Field(
        ..., description="Structured feedback from the QA Agent"
    )
    occurrence_count: int = Field(
        default=1, description="How many times this failure was seen"
    )
    severity: str = Field(
        default="medium", description="low | medium | high | critical"
    )
    mitigation: Optional[str] = Field(
        default=None,
        description="How to avoid this failure in future generations",
    )
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SkillVersion(BaseModel):
    """
    A single version snapshot of a skill. Every time the skill improves
    (QA score >= threshold), a new version is created.
    """

    version: int = Field(..., ge=1)
    prompt_template: str = Field(
        ..., description="The LLM prompt used at this version"
    )
    quality_score: float = Field(
        ..., ge=0.0, le=100.0, description="QA score at version time"
    )
    improvements: List[str] = Field(
        default_factory=list,
        description="What changed from previous version",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QAFeedback(BaseModel):
    """Structured feedback from QA Agent for the self-evaluation loop."""

    score: float = Field(..., ge=0.0, le=100.0)
    grade: str = Field(..., description="A-F letter grade")
    gates_passed: List[str] = Field(default_factory=list)
    gates_failed: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    regenerate: bool = Field(
        default=False, description="Whether QA recommends regeneration"
    )
    structured_failures: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Per-gate structured failure data: [{gate, reason, suggestion}]",
    )


class BestExample(BaseModel):
    """A high-scoring output stored for few-shot retrieval."""

    id: str = Field(default_factory=lambda: f"ex_{uuid.uuid4().hex[:8]}")
    dsl_json: str = Field(..., description="The DSL output as JSON string")
    quality_score: float = Field(..., ge=0.0, le=100.0)
    slide_type: str
    layout: str
    topic_hint: str = Field(
        default="", description="Brief topic for semantic search matching"
    )
    version_at_creation: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SlideSkill(BaseModel):
    """
    A learnable skill for generating a specific slide type.
    This is the core object of the self-evolving Code Agent.

    Lifecycle:
    1. Skill created with v1 default prompt + no examples
    2. Code Agent generates slide → QA scores it
    3. If score >= threshold: version++, output → best_examples
    4. If score < threshold: failure → common_failures, regenerate
    5. Over time, the skill accumulates patterns that make it better
    """

    id: str = Field(
        default_factory=lambda: f"skill_{uuid.uuid4().hex[:12]}"
    )
    name: str = Field(..., description="Skill name matching SlideSkillType value")
    version: int = Field(default=1, ge=1)
    prompt_template: str = Field(
        ..., description="Current LLM prompt template for this slide type"
    )
    quality_history: List[float] = Field(
        default_factory=list,
        description="Chronological list of QA scores for this skill",
    )
    best_examples: List[BestExample] = Field(
        default_factory=list,
        description="Top-scoring outputs for few-shot retrieval (max 10)",
    )
    common_failures: List[SkillFailurePattern] = Field(
        default_factory=list,
        description="Known failure patterns to avoid (max 20)",
    )
    version_history: List[SkillVersion] = Field(
        default_factory=list,
        description="Full version history of this skill",
    )
    generation_mode: SkillGenerationMode = Field(
        default=SkillGenerationMode.INSTANT,
        description="Whether this skill needs reasoning or fast mode",
    )
    avg_quality: float = Field(
        default=0.0, description="Running average quality score"
    )
    total_generations: int = Field(
        default=0, description="Total number of times this skill has been used"
    )
    total_improvements: int = Field(
        default=0, description="Number of successful version upgrades"
    )
    quality_threshold: float = Field(
        default=85.0,
        description="Minimum QA score to consider output good enough to learn from",
    )
    max_best_examples: int = Field(
        default=10, description="Maximum best examples to keep per skill"
    )
    max_failure_patterns: int = Field(
        default=20, description="Maximum failure patterns to track"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def record_generation(self, score: float) -> None:
        """Record a generation attempt and update running average."""
        self.quality_history.append(score)
        self.total_generations += 1
        self.avg_quality = sum(self.quality_history[-50:]) / min(
            len(self.quality_history), 50
        )
        self.updated_at = datetime.now(timezone.utc)

    def add_best_example(self, example: BestExample) -> None:
        """Add a best example, keeping only top N by score."""
        example.version_at_creation = self.version
        self.best_examples.append(example)
        # Sort by quality (highest first) and trim
        self.best_examples.sort(key=lambda x: x.quality_score, reverse=True)
        self.best_examples = self.best_examples[: self.max_best_examples]
        self.updated_at = datetime.now(timezone.utc)

    def add_failure_pattern(self, pattern: SkillFailurePattern) -> None:
        """Add or increment a failure pattern."""
        # Check if similar failure exists (by description prefix match)
        for existing in self.common_failures:
            if existing.description == pattern.description:
                existing.occurrence_count += 1
                existing.last_seen = datetime.now(timezone.utc)
                self.updated_at = datetime.now(timezone.utc)
                return

        self.common_failures.append(pattern)
        # Keep only top N by occurrence
        self.common_failures.sort(
            key=lambda x: x.occurrence_count, reverse=True
        )
        self.common_failures = self.common_failures[: self.max_failure_patterns]
        self.updated_at = datetime.now(timezone.utc)

    def upgrade_version(self, improvements: List[str], new_score: float) -> None:
        """Increment version when quality threshold is met."""
        # Save current state to history
        self.version_history.append(
            SkillVersion(
                version=self.version,
                prompt_template=self.prompt_template,
                quality_score=new_score,
                improvements=improvements,
            )
        )
        self.version += 1
        self.total_improvements += 1
        self.updated_at = datetime.now(timezone.utc)

    def get_top_examples(self, n: int = 3) -> List[BestExample]:
        """Get the top N examples by quality score."""
        return self.best_examples[:n]

    def get_recent_failures(self, n: int = 5) -> List[SkillFailurePattern]:
        """Get the most recent/frequent failure patterns."""
        return sorted(
            self.common_failures,
            key=lambda x: (x.occurrence_count, x.last_seen.timestamp()),
            reverse=True,
        )[:n]

    def to_mongo_doc(self) -> Dict[str, Any]:
        """Serialize for MongoDB storage."""
        doc = self.model_dump()
        # Convert datetimes to ISO strings for MongoDB compatibility
        doc["created_at"] = self.created_at.isoformat()
        doc["updated_at"] = self.updated_at.isoformat()
        for ex in doc.get("best_examples", []):
            if isinstance(ex.get("created_at"), datetime):
                ex["created_at"] = ex["created_at"].isoformat()
        for fp in doc.get("common_failures", []):
            if isinstance(fp.get("first_seen"), datetime):
                fp["first_seen"] = fp["first_seen"].isoformat()
            if isinstance(fp.get("last_seen"), datetime):
                fp["last_seen"] = fp["last_seen"].isoformat()
        for vh in doc.get("version_history", []):
            if isinstance(vh.get("created_at"), datetime):
                vh["created_at"] = vh["created_at"].isoformat()
        return doc

    @classmethod
    def from_mongo_doc(cls, doc: Dict[str, Any]) -> "SlideSkill":
        """Deserialize from MongoDB document."""
        if doc.get("_id"):
            doc.pop("_id", None)
        return cls.model_validate(doc)
