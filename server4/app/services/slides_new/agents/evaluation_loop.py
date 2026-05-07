"""
Self-Evaluation Loop: Generate -> QA -> Learn -> Regenerate.

Implements the yoyo-evolve pattern where the Code Agent:
1. Generates DSL for a slide using current skill state
2. QA evaluates the output (per-gate scoring + structured feedback)
3. If score >= threshold: skill learns from success (best example)
4. If score < threshold: skill records failure + regenerates (max N rounds)
5. Returns the best output after all attempts

This is the core learning mechanism of Phase 3.
"""

import json
from typing import Any, Dict, List, Optional

import structlog

from app.services.slides_new.dsl.dsl_generator import DSLGenerator, DSLGenerationResult
from app.services.slides_new.skills.models import (
    QAFeedback,
    SkillFailurePattern,
)
from app.services.slides_new.skills.skill_store import SkillStore

logger = structlog.get_logger()

# Maximum evaluation rounds before giving up
MAX_EVAL_ROUNDS = 3

# Minimum improvement between rounds to keep iterating
MIN_IMPROVEMENT_DELTA = 5.0


class EvalRound:
    """Result of a single evaluation round."""

    __slots__ = (
        "round_num",
        "dsl_result",
        "qa_feedback",
        "score",
        "passed",
    )

    def __init__(
        self,
        round_num: int,
        dsl_result: DSLGenerationResult,
        qa_feedback: QAFeedback,
        score: float,
        passed: bool,
    ):
        self.round_num = round_num
        self.dsl_result = dsl_result
        self.qa_feedback = qa_feedback
        self.score = score
        self.passed = passed


class EvaluationResult:
    """Final result of the full evaluation loop."""

    __slots__ = (
        "success",
        "best_result",
        "best_score",
        "total_rounds",
        "rounds",
        "skill_updated",
    )

    def __init__(
        self,
        success: bool,
        best_result: Optional[DSLGenerationResult],
        best_score: float,
        total_rounds: int,
        rounds: List[EvalRound],
        skill_updated: bool,
    ):
        self.success = success
        self.best_result = best_result
        self.best_score = best_score
        self.total_rounds = total_rounds
        self.rounds = rounds
        self.skill_updated = skill_updated


class EvaluationLoop:
    """
    Self-evaluation loop for the Code Agent.

    Lifecycle per slide:
    1. generate(slide_type, brief, context) via DSLGenerator
    2. evaluate(dsl) → QAFeedback with per-gate scores
    3. if passed: record_quality (success path) → return
    4. if failed: record_quality (failure path) → regenerate with
       enriched context (previous failures injected)
    5. After MAX_EVAL_ROUNDS, return best output regardless
    """

    def __init__(
        self,
        dsl_generator: DSLGenerator,
        skill_store: SkillStore,
        qa_evaluator: Optional[Any] = None,
        max_rounds: int = MAX_EVAL_ROUNDS,
        quality_threshold: float = 85.0,
    ) -> None:
        self._generator = dsl_generator
        self._store = skill_store
        self._qa = qa_evaluator
        self._max_rounds = max_rounds
        self._threshold = quality_threshold

    async def run(
        self,
        slide_type: str,
        slide_brief: Dict[str, Any],
        context: Dict[str, Any],
        presentation_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Run the full evaluation loop for a single slide.

        Returns EvaluationResult with the best DSL output.
        """
        rounds: List[EvalRound] = []
        best_result: Optional[DSLGenerationResult] = None
        best_score: float = 0.0
        skill_updated: bool = False
        # Accumulate failure context for subsequent rounds
        accumulated_failures: List[str] = []

        for round_num in range(1, self._max_rounds + 1):
            # Inject accumulated failures into context
            round_context = dict(context)
            if accumulated_failures:
                round_context["_previous_failures"] = accumulated_failures

            # 1. Generate DSL
            dsl_result = await self._generator.generate(
                slide_type=slide_type,
                slide_brief=slide_brief,
                context=round_context,
                presentation_id=presentation_id,
            )

            if not dsl_result.success:
                # Generation itself failed — record and try next round
                qa_feedback = QAFeedback(
                    score=0.0,
                    grade="F",
                    issues=[dsl_result.error or "Generation failed"],
                    regenerate=True,
                )
                rounds.append(
                    EvalRound(
                        round_num=round_num,
                        dsl_result=dsl_result,
                        qa_feedback=qa_feedback,
                        score=0.0,
                        passed=False,
                    )
                )
                accumulated_failures.append(
                    f"Round {round_num}: Generation failed — {dsl_result.error}"
                )
                continue

            # 2. Evaluate the output
            qa_feedback = await self._evaluate_dsl(dsl_result, slide_type, slide_brief)

            score = qa_feedback.score
            passed = score >= self._threshold

            # Track best
            if score > best_score:
                best_score = score
                best_result = dsl_result

            rounds.append(
                EvalRound(
                    round_num=round_num,
                    dsl_result=dsl_result,
                    qa_feedback=qa_feedback,
                    score=score,
                    passed=passed,
                )
            )

            logger.info(
                "eval_round_complete",
                slide_type=slide_type,
                round=round_num,
                score=round(score, 1),
                passed=passed,
                presentation_id=presentation_id,
            )

            # 3. Record quality in skill store (learn from attempt)
            if dsl_result.raw_json:
                try:
                    skill = await self._store.record_quality(
                        skill_name=slide_type,
                        score=score,
                        dsl_output=dsl_result.raw_json,
                        qa_feedback=qa_feedback,
                        slide_type=slide_type,
                        layout=(
                            dsl_result.dsl.layout.value
                            if dsl_result.dsl
                            else ""
                        ),
                        topic_hint=context.get("topic", ""),
                    )
                    skill_updated = True
                except ValueError:
                    # Skill doesn't exist yet — non-fatal
                    logger.debug(
                        "eval_skill_not_found",
                        slide_type=slide_type,
                    )

            # 4. Decide whether to continue
            if passed:
                logger.info(
                    "eval_loop_passed",
                    slide_type=slide_type,
                    round=round_num,
                    score=round(score, 1),
                )
                break

            # Check if improvement delta is too small to justify another round
            if round_num > 1 and rounds[-2].score > 0:
                delta = score - rounds[-2].score
                if delta < MIN_IMPROVEMENT_DELTA and round_num >= 2:
                    logger.info(
                        "eval_loop_plateau",
                        slide_type=slide_type,
                        delta=round(delta, 1),
                    )
                    break

            # Build failure context for next round
            for issue in qa_feedback.issues[:3]:
                accumulated_failures.append(
                    f"Round {round_num}: {issue}"
                )
            for sf in qa_feedback.structured_failures[:2]:
                reason = sf.get("reason", "")
                suggestion = sf.get("suggestion", "")
                if reason:
                    accumulated_failures.append(
                        f"Round {round_num} gate '{sf.get('gate', '?')}': "
                        f"{reason}. Fix: {suggestion}"
                    )

        return EvaluationResult(
            success=best_result is not None and best_score >= self._threshold,
            best_result=best_result,
            best_score=best_score,
            total_rounds=len(rounds),
            rounds=rounds,
            skill_updated=skill_updated,
        )

    async def _evaluate_dsl(
        self,
        dsl_result: DSLGenerationResult,
        slide_type: str,
        slide_brief: Dict[str, Any],
    ) -> QAFeedback:
        """
        Evaluate a DSL output using the QA evaluator.

        If no QA evaluator is injected, performs a structural validation
        as a fallback scoring mechanism.
        """
        if self._qa is not None:
            return await self._qa.evaluate_slide(
                dsl_result=dsl_result,
                slide_type=slide_type,
                slide_brief=slide_brief,
            )

        # Structural validation fallback
        return self._structural_evaluate(dsl_result, slide_type, slide_brief)

    def _structural_evaluate(
        self,
        dsl_result: DSLGenerationResult,
        slide_type: str,
        slide_brief: Dict[str, Any],
    ) -> QAFeedback:
        """
        Structural evaluation — checks DSL quality without LLM.
        Used when no QA agent is available.
        """
        dsl = dsl_result.dsl
        if dsl is None:
            return QAFeedback(
                score=0.0,
                grade="F",
                issues=["No valid DSL produced"],
                regenerate=True,
            )

        score = 100.0
        gates_passed = []
        gates_failed = []
        issues = []
        structured_failures = []

        # Gate 1: Content completeness
        content = dsl.content
        if not content.title or not content.title.strip():
            score -= 25
            gates_failed.append("content_completeness")
            issues.append("Missing slide title")
            structured_failures.append({
                "gate": "content_completeness",
                "reason": "Slide has no title",
                "suggestion": "Generate a concise, impactful title",
            })
        else:
            gates_passed.append("content_completeness")

        # Gate 2: Title length (anti-AI-slop)
        if content.title and len(content.title.split()) > 12:
            score -= 10
            gates_failed.append("no_generic_content")
            issues.append("Title too long (>12 words)")
            structured_failures.append({
                "gate": "no_generic_content",
                "reason": "Title exceeds 12 words",
                "suggestion": "Shorten to 6-8 impactful words",
            })
        else:
            gates_passed.append("no_generic_content")

        # Gate 3: Speaker notes present
        if not dsl.speakerNotes or len(dsl.speakerNotes.strip()) < 20:
            score -= 10
            issues.append("Missing or very short speaker notes")
        else:
            gates_passed.append("speaker_notes")

        # Gate 4: Content depth
        has_substance = bool(
            content.bullets
            or content.body_text
            or content.chart_data
            or content.kpi_metrics
            or content.team_members
            or content.timeline_items
            or content.comparison_items
        )
        if not has_substance:
            score -= 20
            gates_failed.append("visual_balance")
            issues.append("Slide lacks substantive content (no bullets, charts, etc.)")
            structured_failures.append({
                "gate": "visual_balance",
                "reason": "No substantive content elements",
                "suggestion": f"Add bullets, data, or rich content for {slide_type}",
            })
        else:
            gates_passed.append("visual_balance")

        # Gate 5: Layout-content alignment
        expected_layouts = {
            "market": ["chart", "kpi-dashboard"],
            "traction": ["kpi-dashboard", "timeline"],
            "team": ["team-grid"],
            "competition": ["comparison", "grid-2x2"],
            "financials": ["chart", "kpi-dashboard"],
        }
        if slide_type in expected_layouts:
            if dsl.layout.value not in expected_layouts[slide_type]:
                score -= 5
                issues.append(
                    f"Layout '{dsl.layout.value}' may not be ideal for {slide_type}"
                )

        # Clamp score
        score = max(0.0, min(100.0, score))

        # Calculate grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return QAFeedback(
            score=score,
            grade=grade,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            issues=issues,
            recommendations=[],
            regenerate=score < self._threshold,
            structured_failures=structured_failures,
        )
