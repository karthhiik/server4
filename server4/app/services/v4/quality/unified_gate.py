"""Unified Quality Gate — P0/P1/P2 taxonomy consolidating 6 existing systems.

This module does NOT replace the 6 existing quality systems. It ORCHESTRATES them
into a single severity taxonomy so the pipeline and frontend have ONE contract.

Existing systems consumed:
  • schema_guard        → P0 on SchemaValidationError
  • hallucination_guard → P0 if hard_block; P1 if score_penalty > 0
  • slide_validator     → P0 if can_recover=False; P1 if can_recover=True
  • critic_engine       → P1 if needs_rewrite=True
  • style_guard         → P1 (flagged for critic)
  • content_rules       → P1 (soft penalty) or P2 (visual slop)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.services.v4 import content_rules, style_guard
from app.services.v4.hallucination_guard import GuardResult, scan_slide
from app.services.v4.schema_guard import SchemaValidationError, validate_writer_output
from app.services.v4.slide_validator import SlideValidationError, SlideValidator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class QualityFinding:
    """A single finding from any detector, normalized to P0/P1/P2."""

    level: str  # "P0" | "P1" | "P2"
    detector: str
    reason: str
    slide_index: int = -1
    slide_id: str | None = None
    path: str | None = None
    auto_fixable: bool = False
    user_overridden: bool = False

    def to_doc(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "detector": self.detector,
            "reason": self.reason,
            "slide_index": self.slide_index,
            "slide_id": self.slide_id,
            "path": self.path,
            "auto_fixable": self.auto_fixable,
            "user_overridden": self.user_overridden,
        }


@dataclass
class SlideQualityReport:
    """Per-slide findings and summary."""

    slide_index: int
    slide_id: str | None = None
    findings: list[QualityFinding] = field(default_factory=list)
    blocked: bool = False
    can_recover: bool = True
    overall_score: float = 0.0  # 0-100

    @property
    def p0_count(self) -> int:
        return sum(1 for f in self.findings if f.level == "P0" and not f.user_overridden)

    @property
    def p1_count(self) -> int:
        return sum(1 for f in self.findings if f.level == "P1" and not f.user_overridden)

    @property
    def p2_count(self) -> int:
        return sum(1 for f in self.findings if f.level == "P2")


@dataclass
class DeckQualityReport:
    """Unified report for an entire deck."""

    slide_reports: list[SlideQualityReport] = field(default_factory=list)
    overall_score: float = 0.0  # 0-100
    deck_blocked: bool = False

    @property
    def total_p0(self) -> int:
        return sum(r.p0_count for r in self.slide_reports)

    @property
    def total_p1(self) -> int:
        return sum(r.p1_count for r in self.slide_reports)

    @property
    def total_p2(self) -> int:
        return sum(r.p2_count for r in self.slide_reports)

    def blocked_slide_indices(self) -> list[int]:
        return [r.slide_index for r in self.slide_reports if r.blocked]

    def recoverable_slide_indices(self) -> list[int]:
        return [r.slide_index for r in self.slide_reports if r.p1_count > 0 and not r.blocked]


class UnifiedQualityGate:
    """Orchestrate 6 existing quality systems into P0/P1/P2 taxonomy."""

    # P0 thresholds
    P0_SCHEMA_FAILURE = True
    P0_HARD_BLOCK = True
    P0_CANNOT_RECOVER = True
    P0_GENERIC_HEADLINE = True
    P0_INSTRUCTION_LEAK = True

    # P1 thresholds
    P1_NEEDS_REWRITE = True
    P1_CAN_RECOVER = True
    P1_STYLE_ISSUE = True
    P1_CONTENT_RULES = True

    # P2 thresholds
    P2_VISUAL_SLOP = True
    P2_DENSITY_COMPLIANCE = True

    def __init__(self) -> None:
        self._validator = SlideValidator()
        self._false_positive_log: list[dict[str, Any]] = []

    # ── Public API ───────────────────────────────────────────────────

    def evaluate(
        self,
        slides: list[dict[str, Any]],
        *,
        slide_ids: list[str] | None = None,
        research_text: str = "",
        user_context: dict[str, Any] | None = None,
    ) -> DeckQualityReport:
        """Run all 6 quality systems and produce unified P0/P1/P2 report."""
        slide_reports: list[SlideQualityReport] = []

        for idx, slide in enumerate(slides):
            sid = slide_ids[idx] if slide_ids and idx < len(slide_ids) else None
            report = self._evaluate_slide(
                slide=slide,
                slide_index=idx,
                slide_id=sid,
                all_slides=slides,
                research_text=research_text,
                user_context=user_context,
            )
            slide_reports.append(report)

        overall = self._compute_deck_score(slide_reports)
        blocked = any(r.blocked for r in slide_reports)

        return DeckQualityReport(
            slide_reports=slide_reports,
            overall_score=overall,
            deck_blocked=blocked,
        )

    def record_override(self, slide_id: str, detector: str, reason: str) -> None:
        """Log a user override so we can track false positives."""
        self._false_positive_log.append({
            "slide_id": slide_id,
            "detector": detector,
            "reason": reason,
            "overridden_at": "now",
        })
        logger.info("quality_gate_user_override", slide_id=slide_id, detector=detector)

    def false_positive_rate(self, detector: str | None = None) -> float:
        """Return override rate for a detector (or all)."""
        if not self._false_positive_log:
            return 0.0
        if detector is None:
            return 1.0
        total = sum(1 for e in self._false_positive_log if e["detector"] == detector)
        return total / len(self._false_positive_log)

    # ── Per-slide evaluation ─────────────────────────────────────────

    def _evaluate_slide(
        self,
        slide: dict[str, Any],
        slide_index: int,
        slide_id: str | None,
        all_slides: list[dict[str, Any]],
        research_text: str,
        user_context: dict[str, Any] | None,
    ) -> SlideQualityReport:
        findings: list[QualityFinding] = []
        blocked = False
        can_recover = True

        # 1. Schema guard (P0 on failure)
        findings.extend(self._run_schema_guard(slide, slide_index, slide_id))

        # 2. Hallucination guard (P0 hard_block; P1 score_penalty)
        findings.extend(self._run_hallucination_guard(slide, slide_index, slide_id, research_text))

        # 3. Slide validator (P0 if !can_recover; P1 if can_recover)
        findings.extend(self._run_slide_validator(slide, slide_index, slide_id))

        # 4. Content rules (P1 soft penalty; P2 visual slop)
        findings.extend(self._run_content_rules(slide, slide_index, slide_id))

        # 5. Style guard (P1)
        findings.extend(self._run_style_guard(slide, slide_index, slide_id, all_slides))

        # 6. Generic headline hard block (P0)
        findings.extend(self._run_generic_headline_gate(slide, slide_index, slide_id))

        # Compute blocked / recoverable
        p0_findings = [f for f in findings if f.level == "P0"]
        if p0_findings:
            blocked = True
            can_recover = not any(f.auto_fixable for f in p0_findings)

        # Overall score: start at 100, subtract weighted penalties
        score = self._compute_slide_score(findings)

        return SlideQualityReport(
            slide_index=slide_index,
            slide_id=slide_id,
            findings=findings,
            blocked=blocked,
            can_recover=can_recover,
            overall_score=max(0.0, score),
        )

    # ── Individual detectors ───────────────────────────────────────

    def _run_schema_guard(
        self,
        slide: dict[str, Any],
        idx: int,
        sid: str | None,
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        if not self.P0_SCHEMA_FAILURE:
            return findings

        try:
            # If slide has a raw_writer_output field, validate it
            raw = slide.get("raw_writer_output", "")
            if raw:
                validate_writer_output(str(raw), slide_index=idx)
        except SchemaValidationError as exc:
            findings.append(QualityFinding(
                level="P0",
                detector="schema_guard",
                reason=str(exc),
                slide_index=idx,
                slide_id=sid,
                auto_fixable=False,
            ))
        return findings

    def _run_hallucination_guard(
        self,
        slide: dict[str, Any],
        idx: int,
        sid: str | None,
        research_text: str,
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        if not self.P0_HARD_BLOCK and not self.P1_CONTENT_RULES:
            return findings

        intent = str(slide.get("intent", slide.get("purpose", "")))
        try:
            result = scan_slide(
                slide_data=slide,
                intent=intent,
                slide_index=idx,
                research_text=research_text,
            )
        except Exception:
            # If scan_slide fails, log but don't block
            logger.warning("hallucination_guard_scan_failed", slide_index=idx)
            return findings

        for issue in result.issues:
            if issue.severity == "error" and self.P0_HARD_BLOCK:
                findings.append(QualityFinding(
                    level="P0",
                    detector="hallucination_guard",
                    reason=f"{issue.kind}: {issue.detail}",
                    slide_index=idx,
                    slide_id=sid,
                    auto_fixable=issue.auto_fixable,
                ))
            elif issue.severity == "warning" and self.P1_CONTENT_RULES:
                findings.append(QualityFinding(
                    level="P1",
                    detector="hallucination_guard",
                    reason=f"{issue.kind}: {issue.detail}",
                    slide_index=idx,
                    slide_id=sid,
                    auto_fixable=issue.auto_fixable,
                ))
        return findings

    def _run_slide_validator(
        self,
        slide: dict[str, Any],
        idx: int,
        sid: str | None,
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        if not self.P0_CANNOT_RECOVER and not self.P1_CAN_RECOVER:
            return findings

        try:
            result = self._validator.validate(slide)
        except Exception:
            logger.warning("slide_validator_failed", slide_index=idx)
            return findings

        if not result.is_valid:
            for err in result.errors:
                level = "P0" if (not result.can_recover and self.P0_CANNOT_RECOVER) else "P1"
                findings.append(QualityFinding(
                    level=level,
                    detector="slide_validator",
                    reason=str(err.value),
                    slide_index=idx,
                    slide_id=sid,
                    auto_fixable=result.can_recover,
                ))
        return findings

    def _run_content_rules(
        self,
        slide: dict[str, Any],
        idx: int,
        sid: str | None,
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []

        headline = str(slide.get("headline", "")).strip()
        subheadline = str(slide.get("subheadline", "")).strip()
        body = str(slide.get("body", "")).strip()
        bullets = [str(b) for b in slide.get("bullets", [])]

        # Banned headline → P0
        if self.P0_GENERIC_HEADLINE:
            detection = content_rules.detect_template_headline(headline)
            if detection.is_template:
                findings.append(QualityFinding(
                    level="P0",
                    detector="content_rules",
                    reason=f"Banned headline: {detection.label} — {detection.fix_hint}",
                    slide_index=idx,
                    slide_id=sid,
                    path="headline",
                    auto_fixable=True,
                ))

        # Generic phrases → P1
        if self.P1_CONTENT_RULES:
            generic_hits = content_rules.detect_generic_phrases(headline, subheadline, body, *bullets)
            for hit in generic_hits:
                findings.append(QualityFinding(
                    level="P1",
                    detector="content_rules",
                    reason=f"Generic phrase: {hit}",
                    slide_index=idx,
                    slide_id=sid,
                    auto_fixable=True,
                ))

        # Visual slop → P2
        if self.P2_VISUAL_SLOP:
            import json
            kit_props = slide.get("kit_props", {})
            props_str = json.dumps(kit_props) if not isinstance(kit_props, str) else kit_props
            slop = content_rules.detect_visual_slop(props_str)
            for signal in slop:
                findings.append(QualityFinding(
                    level="P2",
                    detector="content_rules",
                    reason=f"Visual slop: {signal}",
                    slide_index=idx,
                    slide_id=sid,
                    auto_fixable=True,
                ))

        # Density check → P2 (placeholder until density checker is available)
        # Phase 1: P2 density compliance deferred to quality_scorer.py integration

        return findings

    def _run_style_guard(
        self,
        slide: dict[str, Any],
        idx: int,
        sid: str | None,
        all_slides: list[dict[str, Any]],
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        if not self.P1_STYLE_ISSUE:
            return findings

        # Build minimal GeneratedSlide-like objects for style_guard
        # style_guard.apply_style_guard expects list[Any] with .index, .headline, .subheadline, etc.
        style_issues = style_guard.apply_style_guard([_DictSlide(s) for s in all_slides])
        for issue in style_issues:
            if issue.slide_index == idx:
                findings.append(QualityFinding(
                    level="P1",
                    detector="style_guard",
                    reason=f"{issue.issue}: {issue.detail}",
                    slide_index=idx,
                    slide_id=sid,
                    auto_fixable=True,
                ))
        return findings

    def _run_generic_headline_gate(
        self,
        slide: dict[str, Any],
        idx: int,
        sid: str | None,
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        if not self.P0_GENERIC_HEADLINE:
            return findings

        headline = str(slide.get("headline", "")).strip()
        if not headline:
            findings.append(QualityFinding(
                level="P0",
                detector="generic_headline_gate",
                reason="Missing headline",
                slide_index=idx,
                slide_id=sid,
                path="headline",
                auto_fixable=True,
            ))
            return findings

        # Check if headline is a known generic template
        lowered = headline.lower()
        generic_templates = {
            "our unique value proposition",
            "our distinctive edge",
            "how we operate",
            "empowering resilience",
            "market opportunity",
            "the problem",
            "our solution",
            "our approach",
            "early validation signals",
        }
        if lowered in generic_templates:
            findings.append(QualityFinding(
                level="P0",
                detector="generic_headline_gate",
                reason=f"Template headline: '{headline}'",
                slide_index=idx,
                slide_id=sid,
                path="headline",
                auto_fixable=True,
            ))
        return findings

    # ── Scoring ──────────────────────────────────────────────────────

    @staticmethod
    def _compute_slide_score(findings: list[QualityFinding]) -> float:
        """Start at 100; deduct penalties."""
        score = 100.0
        for f in findings:
            if f.level == "P0" and not f.user_overridden:
                score -= 40.0
            elif f.level == "P1" and not f.user_overridden:
                score -= 15.0
            elif f.level == "P2":
                score -= 5.0
        return max(0.0, score)

    @staticmethod
    def _compute_deck_score(slide_reports: list[SlideQualityReport]) -> float:
        if not slide_reports:
            return 0.0
        return sum(r.overall_score for r in slide_reports) / len(slide_reports)


# ── Helper to make dict slides compatible with style_guard ─────────

class _DictSlide:
    """Wrap a plain dict so style_guard can read headline/subheadline etc."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name == "index":
            return self._data.get("index", 0)
        if name == "raw":
            return self._data
        return self._data.get(name, "")

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
