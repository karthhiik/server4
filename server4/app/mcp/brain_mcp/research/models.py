"""
V7 Slide Content Research Pipeline — Core Data Models.

Every module in the research pipeline imports from here.
Defines the canonical data contracts for evidence, content, streaming,
debate, provider health, and style profiles.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════


class ClaimType(str, Enum):
    """Kind of factual claim carried by a FactPacket."""

    numeric = "numeric"
    qualitative = "qualitative"
    trend = "trend"
    comparison = "comparison"
    citation = "citation"
    testimonial = "testimonial"
    regulatory = "regulatory"


class FreshnessClass(str, Enum):
    """How fresh the underlying data is relative to retrieval time."""

    real_time = "real_time"      # < 1 hour
    breaking = "breaking"        # 1-24 hours
    recent = "recent"            # 1-7 days
    current = "current"          # 1-4 weeks
    dated = "dated"              # 1-12 months
    archival = "archival"        # > 1 year
    undated = "undated"          # publication date unknown


class SourceType(str, Enum):
    """Origin category for a FactPacket."""

    government_data = "government_data"
    financial_api = "financial_api"
    academic_paper = "academic_paper"
    news_article = "news_article"
    social_signal = "social_signal"
    industry_report = "industry_report"
    company_filing = "company_filing"
    web_extracted = "web_extracted"


class SlideKind(str, Enum):
    """Canonical slide types for pitch decks and presentations."""

    title = "title"
    problem = "problem"
    solution = "solution"
    market = "market"
    competition = "competition"
    gtm = "gtm"
    traction = "traction"
    financial = "financial"
    team = "team"
    ask = "ask"
    why_now = "why_now"
    product_demo = "product_demo"
    appendix = "appendix"


class BudgetMode(str, Enum):
    """Cost tier for a generation run."""

    lean = "lean"
    balanced = "balanced"
    hero = "hero"


class ResearchPriority(str, Enum):
    """Depth of research effort for a slide."""

    minimal = "minimal"
    standard = "standard"
    hero = "hero"


class ProviderStatus(str, Enum):
    """Circuit-breaker state for an external provider."""

    healthy = "healthy"
    degraded = "degraded"
    open_circuit = "open_circuit"


class SlideFailureType(str, Enum):
    """Why a slide could not be generated to the quality bar."""

    no_evidence = "no_evidence"
    weak_evidence = "weak_evidence"
    conflicting_evidence = "conflicting_evidence"
    generation_failed = "generation_failed"
    debate_rejected = "debate_rejected"
    citation_failed = "citation_failed"


class ContentEvent(str, Enum):
    """30 streaming events emitted during slide content generation."""

    # ── Research phase ──────────────────────────────────────────
    DECK_CONTEXT_READY = "deck_context_ready"
    INTENT_CLASSIFIED = "intent_classified"
    RESEARCH_PLAN_READY = "research_plan_ready"
    SLIDE_RESEARCH_PLANNED = "slide_research_planned"
    PROVIDER_SELECTED = "provider_selected"
    PROVIDER_SKIPPED = "provider_skipped"
    SOURCE_FETCHING = "source_fetching"
    SOURCE_FETCHED = "source_fetched"
    SOURCE_FAILED = "source_failed"
    QUERY_REWRITTEN = "query_rewritten"

    # ── Evidence phase ──────────────────────────────────────────
    FACT_PACKET_CREATED = "fact_packet_created"
    FACT_PACKET_REJECTED = "fact_packet_rejected"
    CROSS_VALIDATION_RESULT = "cross_validation_result"
    EVIDENCE_GRAPH_UPDATED = "evidence_graph_updated"
    COMMUNITY_SUMMARY_READY = "community_summary_ready"
    EVIDENCE_BUNDLE_READY = "evidence_bundle_ready"

    # ── Debate phase (pitch decks) ──────────────────────────────
    CEO_THESIS_READY = "ceo_thesis_ready"
    CTO_CHALLENGE_READY = "cto_challenge_ready"
    FINANCE_CHALLENGE_READY = "finance_challenge_ready"
    DEBATE_ROUND_COMPLETE = "debate_round_complete"
    DEBATE_RESOLVED = "debate_resolved"

    # ── Generation phase ────────────────────────────────────────
    SLIDE_BRIEF_READY = "slide_brief_ready"
    PRESENTATION_COPY_READY = "presentation_copy_ready"
    READING_COPY_READY = "reading_copy_ready"
    SPEAKER_NOTES_READY = "speaker_notes_ready"
    CHART_DATA_READY = "chart_data_ready"
    IMAGE_PROMPT_READY = "image_prompt_ready"
    CITATIONS_VERIFIED = "citations_verified"

    # ── Final ───────────────────────────────────────────────────
    SLIDE_CONTENT_READY = "slide_content_ready"
    SLIDE_CONTENT_BLOCKED = "slide_content_blocked"
    DECK_CONTENT_COMPLETE = "deck_content_complete"


# ═══════════════════════════════════════════════════════════════════════
# CORE EVIDENCE DATACLASSES
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class FactPacket:
    """Atomic unit of evidence.  Everything in the pipeline traces back here."""

    id: str
    claim: str
    claim_type: ClaimType
    source_url: Optional[str]
    source_name: str
    source_type: SourceType
    date_published: Optional[str]
    date_retrieved: str
    freshness_class: FreshnessClass
    confidence: float
    numeric_value: Optional[float]
    numeric_unit: Optional[str]
    extraction_method: str  # "api_structured"|"llm_extracted"|"manual"|"scraped"
    provider: str
    cross_validated: bool = False
    cross_validation_sources: list[str] = field(default_factory=list)
    slide_relevance: dict[str, float] = field(default_factory=dict)
    raw_snippet: Optional[str] = None
    citation_label: Optional[str] = None
    provider_request_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be 0.0-1.0, got {self.confidence}"
            )
        valid_methods = ("api_structured", "llm_extracted", "manual", "scraped")
        if self.extraction_method not in valid_methods:
            raise ValueError(
                f"extraction_method must be one of {valid_methods}, "
                f"got {self.extraction_method!r}"
            )
        if not self.id:
            self.id = f"fp_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim": self.claim,
            "claim_type": self.claim_type.value,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "date_published": self.date_published,
            "date_retrieved": self.date_retrieved,
            "freshness_class": self.freshness_class.value,
            "confidence": self.confidence,
            "numeric_value": self.numeric_value,
            "numeric_unit": self.numeric_unit,
            "extraction_method": self.extraction_method,
            "provider": self.provider,
            "cross_validated": self.cross_validated,
            "cross_validation_sources": list(self.cross_validation_sources),
            "slide_relevance": dict(self.slide_relevance),
            "raw_snippet": self.raw_snippet,
            "citation_label": self.citation_label,
            "provider_request_id": self.provider_request_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactPacket:
        return cls(
            id=data["id"],
            claim=data["claim"],
            claim_type=ClaimType(data["claim_type"]),
            source_url=data.get("source_url"),
            source_name=data["source_name"],
            source_type=SourceType(data["source_type"]),
            date_published=data.get("date_published"),
            date_retrieved=data["date_retrieved"],
            freshness_class=FreshnessClass(data["freshness_class"]),
            confidence=data["confidence"],
            numeric_value=data.get("numeric_value"),
            numeric_unit=data.get("numeric_unit"),
            extraction_method=data["extraction_method"],
            provider=data["provider"],
            cross_validated=data.get("cross_validated", False),
            cross_validation_sources=data.get("cross_validation_sources", []),
            slide_relevance=data.get("slide_relevance", {}),
            raw_snippet=data.get("raw_snippet"),
            citation_label=data.get("citation_label"),
            provider_request_id=data.get("provider_request_id"),
        )


@dataclass
class MissingDataItem:
    """Describes evidence the system wanted but could not obtain."""

    what: str
    how_to_get: str
    suggested_provider: str
    severity: str  # "critical"|"important"|"nice_to_have"

    def __post_init__(self) -> None:
        valid = ("critical", "important", "nice_to_have")
        if self.severity not in valid:
            raise ValueError(
                f"severity must be one of {valid}, got {self.severity!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "what": self.what,
            "how_to_get": self.how_to_get,
            "suggested_provider": self.suggested_provider,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissingDataItem:
        return cls(**data)


@dataclass
class SourceMix:
    """Evidence grouped by extraction origin."""

    deterministic: list[FactPacket] = field(default_factory=list)
    llm_extracted: list[FactPacket] = field(default_factory=list)
    social: list[FactPacket] = field(default_factory=list)
    academic: list[FactPacket] = field(default_factory=list)
    specialty: list[FactPacket] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.deterministic)
            + len(self.llm_extracted)
            + len(self.social)
            + len(self.academic)
            + len(self.specialty)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "deterministic": [fp.to_dict() for fp in self.deterministic],
            "llm_extracted": [fp.to_dict() for fp in self.llm_extracted],
            "social": [fp.to_dict() for fp in self.social],
            "academic": [fp.to_dict() for fp in self.academic],
            "specialty": [fp.to_dict() for fp in self.specialty],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceMix:
        return cls(
            deterministic=[FactPacket.from_dict(d) for d in data.get("deterministic", [])],
            llm_extracted=[FactPacket.from_dict(d) for d in data.get("llm_extracted", [])],
            social=[FactPacket.from_dict(d) for d in data.get("social", [])],
            academic=[FactPacket.from_dict(d) for d in data.get("academic", [])],
            specialty=[FactPacket.from_dict(d) for d in data.get("specialty", [])],
        )


# ═══════════════════════════════════════════════════════════════════════
# DEBATE DATACLASSES
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class RejectedClaim:
    """A FactPacket that did not survive the debate loop."""

    fact_packet_id: str
    reason: str
    rejected_by: str  # "cto"|"finance"|"citation_guard"
    alternative_suggestion: Optional[str] = None

    def __post_init__(self) -> None:
        valid_rejectors = ("cto", "finance", "citation_guard")
        if self.rejected_by not in valid_rejectors:
            raise ValueError(
                f"rejected_by must be one of {valid_rejectors}, "
                f"got {self.rejected_by!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_packet_id": self.fact_packet_id,
            "reason": self.reason,
            "rejected_by": self.rejected_by,
            "alternative_suggestion": self.alternative_suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RejectedClaim:
        return cls(**data)


@dataclass
class DebateOutcome:
    """Result of the CEO / CTO / Finance debate loop."""

    approved_claims: list[str] = field(default_factory=list)
    rejected_claims: list[RejectedClaim] = field(default_factory=list)
    iteration_count: int = 0
    ceo_confidence: float = 0.0
    cto_confidence: float = 0.0
    finance_confidence: float = 0.0
    final_thesis: str = ""
    debate_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved_claims": list(self.approved_claims),
            "rejected_claims": [rc.to_dict() for rc in self.rejected_claims],
            "iteration_count": self.iteration_count,
            "ceo_confidence": self.ceo_confidence,
            "cto_confidence": self.cto_confidence,
            "finance_confidence": self.finance_confidence,
            "final_thesis": self.final_thesis,
            "debate_summary": self.debate_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebateOutcome:
        return cls(
            approved_claims=data.get("approved_claims", []),
            rejected_claims=[
                RejectedClaim.from_dict(rc) for rc in data.get("rejected_claims", [])
            ],
            iteration_count=data.get("iteration_count", 0),
            ceo_confidence=data.get("ceo_confidence", 0.0),
            cto_confidence=data.get("cto_confidence", 0.0),
            finance_confidence=data.get("finance_confidence", 0.0),
            final_thesis=data.get("final_thesis", ""),
            debate_summary=data.get("debate_summary", ""),
        )


# ═══════════════════════════════════════════════════════════════════════
# SLIDE EVIDENCE BUNDLE
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SlideEvidenceBundle:
    """Complete evidence package for a single slide."""

    slide_id: str
    slide_kind: SlideKind
    evidence_packets: list[FactPacket] = field(default_factory=list)
    source_mix: SourceMix = field(default_factory=SourceMix)
    missing_data: list[MissingDataItem] = field(default_factory=list)
    evidence_score: float = 0.0
    approved_claim_ids: list[str] = field(default_factory=list)
    rejected_claims: list[RejectedClaim] = field(default_factory=list)
    cross_validation_score: float = 0.0
    debate_approved: bool = False
    research_depth_used: int = 1

    def __post_init__(self) -> None:
        if not 0.0 <= self.evidence_score <= 1.0:
            raise ValueError(
                f"evidence_score must be 0.0-1.0, got {self.evidence_score}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "slide_kind": self.slide_kind.value,
            "evidence_packets": [fp.to_dict() for fp in self.evidence_packets],
            "source_mix": self.source_mix.to_dict(),
            "missing_data": [md.to_dict() for md in self.missing_data],
            "evidence_score": self.evidence_score,
            "approved_claim_ids": list(self.approved_claim_ids),
            "rejected_claims": [rc.to_dict() for rc in self.rejected_claims],
            "cross_validation_score": self.cross_validation_score,
            "debate_approved": self.debate_approved,
            "research_depth_used": self.research_depth_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlideEvidenceBundle:
        return cls(
            slide_id=data["slide_id"],
            slide_kind=SlideKind(data["slide_kind"]),
            evidence_packets=[
                FactPacket.from_dict(fp) for fp in data.get("evidence_packets", [])
            ],
            source_mix=SourceMix.from_dict(data.get("source_mix", {})),
            missing_data=[
                MissingDataItem.from_dict(md) for md in data.get("missing_data", [])
            ],
            evidence_score=data.get("evidence_score", 0.0),
            approved_claim_ids=data.get("approved_claim_ids", []),
            rejected_claims=[
                RejectedClaim.from_dict(rc) for rc in data.get("rejected_claims", [])
            ],
            cross_validation_score=data.get("cross_validation_score", 0.0),
            debate_approved=data.get("debate_approved", False),
            research_depth_used=data.get("research_depth_used", 1),
        )


# ═══════════════════════════════════════════════════════════════════════
# CONTENT OUTPUT DATACLASSES
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class BodySection:
    """One section inside a reading-mode document."""

    heading: str
    paragraphs: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "heading": self.heading,
            "paragraphs": list(self.paragraphs),
            "source_refs": list(self.source_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BodySection:
        return cls(
            heading=data["heading"],
            paragraphs=data.get("paragraphs", []),
            source_refs=data.get("source_refs", []),
        )


@dataclass
class Citation:
    """A rendered citation that appears in the slide footer / appendix."""

    label: str  # e.g. "[M1]"
    source_name: str
    source_url: Optional[str] = None
    date: Optional[str] = None
    claim_type: ClaimType = ClaimType.qualitative
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "date": self.date,
            "claim_type": self.claim_type.value,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Citation:
        return cls(
            label=data["label"],
            source_name=data["source_name"],
            source_url=data.get("source_url"),
            date=data.get("date"),
            claim_type=ClaimType(data.get("claim_type", "qualitative")),
            confidence=data.get("confidence", 0.0),
        )


@dataclass
class PresentationContent:
    """Slide content optimised for the projection / deck view."""

    title: str
    subtitle: Optional[str] = None
    bullets: list[str] = field(default_factory=list)
    hero_stat: Optional[str] = None
    annotation: Optional[str] = None

    def __post_init__(self) -> None:
        if len(self.title.split()) > 12:
            # Soft limit — truncate to first 8 words but don't crash
            pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "bullets": list(self.bullets),
            "hero_stat": self.hero_stat,
            "annotation": self.annotation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresentationContent:
        return cls(
            title=data["title"],
            subtitle=data.get("subtitle"),
            bullets=data.get("bullets", []),
            hero_stat=data.get("hero_stat"),
            annotation=data.get("annotation"),
        )


@dataclass
class ReadingContent:
    """Slide content optimised for the reading / document view."""

    title: str
    summary: str
    body_sections: list[BodySection] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "body_sections": [bs.to_dict() for bs in self.body_sections],
            "assumptions": list(self.assumptions),
            "risks": list(self.risks),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReadingContent:
        return cls(
            title=data["title"],
            summary=data["summary"],
            body_sections=[
                BodySection.from_dict(bs) for bs in data.get("body_sections", [])
            ],
            assumptions=data.get("assumptions", []),
            risks=data.get("risks", []),
        )


@dataclass
class GenerationMetadata:
    """Telemetry about a single slide or deck generation run."""

    total_providers_queried: int = 0
    total_fact_packets: int = 0
    approved_claims: int = 0
    rejected_claims: int = 0
    evidence_score: float = 0.0
    models_used: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    budget_mode: BudgetMode = BudgetMode.balanced
    style_applied: str = ""
    errors_recovered: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_providers_queried": self.total_providers_queried,
            "total_fact_packets": self.total_fact_packets,
            "approved_claims": self.approved_claims,
            "rejected_claims": self.rejected_claims,
            "evidence_score": self.evidence_score,
            "models_used": list(self.models_used),
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "budget_mode": self.budget_mode.value,
            "style_applied": self.style_applied,
            "errors_recovered": self.errors_recovered,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationMetadata:
        return cls(
            total_providers_queried=data.get("total_providers_queried", 0),
            total_fact_packets=data.get("total_fact_packets", 0),
            approved_claims=data.get("approved_claims", 0),
            rejected_claims=data.get("rejected_claims", 0),
            evidence_score=data.get("evidence_score", 0.0),
            models_used=data.get("models_used", []),
            total_tokens=data.get("total_tokens", 0),
            total_latency_ms=data.get("total_latency_ms", 0.0),
            budget_mode=BudgetMode(data.get("budget_mode", "balanced")),
            style_applied=data.get("style_applied", ""),
            errors_recovered=data.get("errors_recovered", 0),
        )


# ═══════════════════════════════════════════════════════════════════════
# SLIDE CONTENT CONTRACT (final output per slide)
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SlideContentContract:
    """The final output object consumed by the V7 renderer for one slide."""

    slide_id: str
    slide_kind: SlideKind
    style_id: str
    presentation_content: PresentationContent
    reading_content: ReadingContent
    speaker_notes: list[str] = field(default_factory=list)
    chart_data: Optional[dict] = None
    image_prompt: Optional[str] = None
    citations: list[Citation] = field(default_factory=list)
    evidence_score: float = 0.0
    generation_metadata: GenerationMetadata = field(default_factory=GenerationMetadata)

    def __post_init__(self) -> None:
        if not 0.0 <= self.evidence_score <= 1.0:
            raise ValueError(
                f"evidence_score must be 0.0-1.0, got {self.evidence_score}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "slide_kind": self.slide_kind.value,
            "style_id": self.style_id,
            "presentation_content": self.presentation_content.to_dict(),
            "reading_content": self.reading_content.to_dict(),
            "speaker_notes": list(self.speaker_notes),
            "chart_data": self.chart_data,
            "image_prompt": self.image_prompt,
            "citations": [c.to_dict() for c in self.citations],
            "evidence_score": self.evidence_score,
            "generation_metadata": self.generation_metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlideContentContract:
        return cls(
            slide_id=data["slide_id"],
            slide_kind=SlideKind(data["slide_kind"]),
            style_id=data["style_id"],
            presentation_content=PresentationContent.from_dict(
                data["presentation_content"]
            ),
            reading_content=ReadingContent.from_dict(data["reading_content"]),
            speaker_notes=data.get("speaker_notes", []),
            chart_data=data.get("chart_data"),
            image_prompt=data.get("image_prompt"),
            citations=[
                Citation.from_dict(c) for c in data.get("citations", [])
            ],
            evidence_score=data.get("evidence_score", 0.0),
            generation_metadata=GenerationMetadata.from_dict(
                data.get("generation_metadata", {})
            ),
        )


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER HEALTH
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ProviderHealth:
    """Live health snapshot for a single external provider."""

    provider: str
    status: ProviderStatus = ProviderStatus.healthy
    consecutive_failures: int = 0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    avg_latency_ms: float = 0.0
    total_calls_today: int = 0
    total_calls_month: int = 0
    circuit_open_until: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status.value,
            "consecutive_failures": self.consecutive_failures,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "avg_latency_ms": self.avg_latency_ms,
            "total_calls_today": self.total_calls_today,
            "total_calls_month": self.total_calls_month,
            "circuit_open_until": self.circuit_open_until,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProviderHealth:
        return cls(
            provider=data["provider"],
            status=ProviderStatus(data.get("status", "healthy")),
            consecutive_failures=data.get("consecutive_failures", 0),
            last_success=data.get("last_success"),
            last_failure=data.get("last_failure"),
            avg_latency_ms=data.get("avg_latency_ms", 0.0),
            total_calls_today=data.get("total_calls_today", 0),
            total_calls_month=data.get("total_calls_month", 0),
            circuit_open_until=data.get("circuit_open_until"),
        )


# ═══════════════════════════════════════════════════════════════════════
# SLIDE FAILURE STATE
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SlideFailureState:
    """Structured failure report when a slide cannot meet the quality bar."""

    slide_id: str
    failure_type: SlideFailureType
    attempted_providers: list[str] = field(default_factory=list)
    partial_evidence: list[FactPacket] = field(default_factory=list)
    recovery_attempted: bool = False
    user_message: str = ""
    user_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "failure_type": self.failure_type.value,
            "attempted_providers": list(self.attempted_providers),
            "partial_evidence": [fp.to_dict() for fp in self.partial_evidence],
            "recovery_attempted": self.recovery_attempted,
            "user_message": self.user_message,
            "user_actions": list(self.user_actions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlideFailureState:
        return cls(
            slide_id=data["slide_id"],
            failure_type=SlideFailureType(data["failure_type"]),
            attempted_providers=data.get("attempted_providers", []),
            partial_evidence=[
                FactPacket.from_dict(fp)
                for fp in data.get("partial_evidence", [])
            ],
            recovery_attempted=data.get("recovery_attempted", False),
            user_message=data.get("user_message", ""),
            user_actions=data.get("user_actions", []),
        )


# ═══════════════════════════════════════════════════════════════════════
# STREAMING EVENT PAYLOAD
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ContentEventPayload:
    """Wire-format payload pushed to Redis pub/sub and forwarded via WebSocket."""

    event: str  # ContentEvent value or raw string for backward compat
    slide_id: Optional[str] = None
    timestamp: str = ""
    data: dict = field(default_factory=dict)
    progress: float = 0.0
    stage: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError(
                f"progress must be 0.0-1.0, got {self.progress}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "slide_id": self.slide_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "progress": self.progress,
            "stage": self.stage,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentEventPayload:
        return cls(
            event=data["event"],
            slide_id=data.get("slide_id"),
            timestamp=data.get("timestamp", ""),
            data=data.get("data", {}),
            progress=data.get("progress", 0.0),
            stage=data.get("stage", ""),
            message=data.get("message", ""),
        )


# ═══════════════════════════════════════════════════════════════════════
# STYLE PROFILE
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class StyleProfile:
    """Full writing-style specification consumed by the content generators."""

    style_id: str
    family: str  # e.g. "investor", "corporate", "creative"
    headline_mode: str  # "question"|"statement"|"metric"|"provocative"
    sentence_density: str  # "sparse"|"moderate"|"dense"
    bullet_tempo: str  # "staccato"|"flowing"|"mixed"
    tone: str  # "bold"|"measured"|"conversational"|"academic"
    evidence_density: str  # "light"|"moderate"|"heavy"
    preferred_slide_types: list[str] = field(default_factory=list)
    presentation_rules: dict = field(default_factory=dict)
    reading_rules: dict = field(default_factory=dict)
    fluff_tolerance: float = 0.0
    number_format: str = "abbreviated"  # "abbreviated"|"full"|"scientific"
    citation_style: str = "inline"  # "inline"|"footnote"|"appendix"
    visual_preference: str = "chart"  # "chart"|"icon"|"image"|"minimal"
    max_bullets_presentation: int = 5
    max_words_per_bullet: int = 15

    def __post_init__(self) -> None:
        if not 0.0 <= self.fluff_tolerance <= 1.0:
            raise ValueError(
                f"fluff_tolerance must be 0.0-1.0, got {self.fluff_tolerance}"
            )
        if self.max_bullets_presentation < 1:
            raise ValueError("max_bullets_presentation must be >= 1")
        if self.max_words_per_bullet < 1:
            raise ValueError("max_words_per_bullet must be >= 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_id": self.style_id,
            "family": self.family,
            "headline_mode": self.headline_mode,
            "sentence_density": self.sentence_density,
            "bullet_tempo": self.bullet_tempo,
            "tone": self.tone,
            "evidence_density": self.evidence_density,
            "preferred_slide_types": list(self.preferred_slide_types),
            "presentation_rules": dict(self.presentation_rules),
            "reading_rules": dict(self.reading_rules),
            "fluff_tolerance": self.fluff_tolerance,
            "number_format": self.number_format,
            "citation_style": self.citation_style,
            "visual_preference": self.visual_preference,
            "max_bullets_presentation": self.max_bullets_presentation,
            "max_words_per_bullet": self.max_words_per_bullet,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleProfile:
        return cls(
            style_id=data["style_id"],
            family=data["family"],
            headline_mode=data["headline_mode"],
            sentence_density=data["sentence_density"],
            bullet_tempo=data["bullet_tempo"],
            tone=data["tone"],
            evidence_density=data["evidence_density"],
            preferred_slide_types=data.get("preferred_slide_types", []),
            presentation_rules=data.get("presentation_rules", {}),
            reading_rules=data.get("reading_rules", {}),
            fluff_tolerance=data.get("fluff_tolerance", 0.0),
            number_format=data.get("number_format", "abbreviated"),
            citation_style=data.get("citation_style", "inline"),
            visual_preference=data.get("visual_preference", "chart"),
            max_bullets_presentation=data.get("max_bullets_presentation", 5),
            max_words_per_bullet=data.get("max_words_per_bullet", 15),
        )
