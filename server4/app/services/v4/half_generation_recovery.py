"""Half-Generation Recovery System.

Detects and recovers from partial slide generation failures:
  - Incomplete slides (missing headline, body, or visual elements)
  - JSON parse failures from writer output
  - Timeout-induced partial content
  - Visual element generation failures

This module integrates with:
  - content_pipeline.py (post-critic auto-recovery)
  - regen_engine.py (targeted regeneration)
  - slide_compiler.py (fallback layouts)

Design principles:
  - Non-blocking: recovery runs asynchronously
  - Targeted: only regenerate failed slides, not the whole deck
  - Graceful degradation: if recovery fails, use fallback layout
  - Observable: all recovery attempts are logged with context
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable

import structlog

from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.content_rules import validate_data_slide

logger = structlog.get_logger(__name__)

# Recovery budget constants
MAX_RECOVERY_ATTEMPTS = 2
RECOVERY_TIMEOUT_SECONDS = 25.0
MIN_HEADLINE_LENGTH = 10
MIN_BODY_LENGTH = 20


@dataclass
class SlideHealthCheck:
    """Result of checking a slide's structural health."""
    index: int
    healthy: bool
    issues: list[str] = field(default_factory=list)
    severity: str = "none"  # "none", "warning", "critical"
    can_recover: bool = True
    recovery_strategy: Optional[str] = None


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    slide_index: int
    success: bool
    attempts: int
    recovered_slide: Optional[GeneratedSlide] = None
    fallback_used: bool = False
    error: Optional[str] = None
    duration_ms: int = 0


class HalfGenerationRecovery:
    """Detects and recovers from partial generation failures."""

    def __init__(
        self,
        *,
        regenerate_slide: Callable[[int, Optional[str]], Awaitable[Optional[GeneratedSlide]]],
    ):
        """
        Args:
            regenerate_slide: Async function that regenerates a single slide by index.
                              Takes (slide_index, instruction) and returns a GeneratedSlide or None.
        """
        self._regenerate_slide = regenerate_slide
        self._recovery_history: dict[str, list[RecoveryResult]] = {}

    def check_slide_health(self, slide: GeneratedSlide) -> SlideHealthCheck:
        """Check if a slide has all required content for rendering.

        A healthy slide must have:
          - Non-empty headline (min 10 chars)
          - Either body text or visual elements (chart, table, diagram, etc.)
          - Valid visual element data if present

        Returns:
            SlideHealthCheck with issues list and recovery recommendation.
        """
        issues: list[str] = []
        severity = "none"

        # Check headline
        headline = slide.headline or ""
        if len(headline.strip()) < MIN_HEADLINE_LENGTH:
            issues.append(f"headline_too_short:{len(headline)}")
            severity = "critical"

        # Check content presence
        has_body = bool(slide.body and len(slide.body.strip()) >= MIN_BODY_LENGTH)
        has_bullets = bool(slide.bullets and len(slide.bullets) > 0)
        has_stats = bool(slide.stat_blocks and len(slide.stat_blocks) > 0)
        has_chart = bool(slide.chart and slide.chart.get("data"))
        has_table = bool(slide.table and slide.table.get("rows"))
        has_diagram = bool(slide.diagram and slide.diagram.get("nodes"))
        has_timeline = bool(slide.timeline and slide.timeline.get("events"))
        has_comparison = bool(slide.comparison and slide.comparison.get("columns"))
        has_quote = bool(slide.quote and slide.quote.get("text"))
        has_image = bool(slide.image_url)

        has_content = has_body or has_bullets or has_stats or has_chart or has_table or \
                      has_diagram or has_timeline or has_comparison or has_quote or has_image

        if not has_content:
            issues.append("no_content_blocks")
            severity = "critical"

        # Check visual element validity
        if has_chart:
            chart_data = slide.chart.get("data") or []
            if not isinstance(chart_data, list) or len(chart_data) == 0:
                issues.append("chart_data_empty")
                if severity != "critical":
                    severity = "warning"

        if has_diagram:
            nodes = slide.diagram.get("nodes") or []
            if not isinstance(nodes, list) or len(nodes) == 0:
                issues.append("diagram_nodes_empty")
                severity = "critical"

        # Check data slide requirements
        intent = (slide.intent or "").lower()
        data_issues = validate_data_slide(intent=slide.intent, slide=slide.__dict__)
        for issue in data_issues:
            issues.append(f"data_validation:{issue.code}")
            if severity != "critical":
                severity = "warning"

        # Determine recovery strategy
        recovery_strategy = None
        if severity == "critical":
            if "headline_too_short" in str(issues):
                recovery_strategy = "regenerate_headline"
            elif "no_content_blocks" in str(issues):
                recovery_strategy = "regenerate_content"
            elif "diagram_nodes_empty" in str(issues):
                recovery_strategy = "fallback_to_bullets"
            else:
                recovery_strategy = "full_regenerate"
        elif severity == "warning":
            recovery_strategy = "targeted_fix"

        return SlideHealthCheck(
            index=slide.index,
            healthy=severity == "none",
            issues=issues,
            severity=severity,
            can_recover=recovery_strategy is not None,
            recovery_strategy=recovery_strategy,
        )

    async def recover_slide(
        self,
        slide: GeneratedSlide,
        *,
        project_id: str,
        instruction: Optional[str] = None,
    ) -> RecoveryResult:
        """Attempt to recover a failed slide.

        Args:
            slide: The problematic slide to recover.
            project_id: Project ID for logging/tracking.
            instruction: Optional specific instruction for regeneration.

        Returns:
            RecoveryResult with success status and recovered slide.
        """
        start_time = time.time()
        health = self.check_slide_health(slide)

        if health.healthy:
            return RecoveryResult(
                slide_index=slide.index,
                success=True,
                attempts=0,
                recovered_slide=slide,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        if not health.can_recover:
            logger.warning(
                "half_gen_recovery_not_possible",
                project_id=project_id,
                slide_index=slide.index,
                issues=health.issues,
            )
            return RecoveryResult(
                slide_index=slide.index,
                success=False,
                attempts=0,
                error="unrecoverable",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Build recovery instruction
        recovery_instruction = instruction or self._build_recovery_instruction(health)

        # Attempt regeneration
        last_error: Optional[str] = None
        for attempt in range(1, MAX_RECOVERY_ATTEMPTS + 1):
            try:
                logger.info(
                    "half_gen_recovery_attempt",
                    project_id=project_id,
                    slide_index=slide.index,
                    attempt=attempt,
                    strategy=health.recovery_strategy,
                )

                regenerated = await asyncio.wait_for(
                    self._regenerate_slide(slide.index, recovery_instruction),
                    timeout=RECOVERY_TIMEOUT_SECONDS,
                )

                if regenerated:
                    # Verify the regenerated slide is healthy
                    new_health = self.check_slide_health(regenerated)
                    if new_health.healthy:
                        logger.info(
                            "half_gen_recovery_success",
                            project_id=project_id,
                            slide_index=slide.index,
                            attempts=attempt,
                        )
                        return RecoveryResult(
                            slide_index=slide.index,
                            success=True,
                            attempts=attempt,
                            recovered_slide=regenerated,
                            duration_ms=int((time.time() - start_time) * 1000),
                        )
                    else:
                        # Still has issues, try again
                        last_error = f"still_unhealthy:{new_health.issues}"
                        logger.warning(
                            "half_gen_recovery_still_unhealthy",
                            project_id=project_id,
                            slide_index=slide.index,
                            attempt=attempt,
                            issues=new_health.issues,
                        )

            except asyncio.TimeoutError:
                last_error = "timeout"
                logger.warning(
                    "half_gen_recovery_timeout",
                    project_id=project_id,
                    slide_index=slide.index,
                    attempt=attempt,
                )
            except Exception as e:
                last_error = str(e)[:200]
                logger.error(
                    "half_gen_recovery_error",
                    project_id=project_id,
                    slide_index=slide.index,
                    attempt=attempt,
                    error=last_error,
                )

        # All recovery attempts failed - return failure
        logger.error(
            "half_gen_recovery_failed",
            project_id=project_id,
            slide_index=slide.index,
            attempts=MAX_RECOVERY_ATTEMPTS,
            last_error=last_error,
        )
        return RecoveryResult(
            slide_index=slide.index,
            success=False,
            attempts=MAX_RECOVERY_ATTEMPTS,
            error=last_error,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    def _build_recovery_instruction(self, health: SlideHealthCheck) -> str:
        """Build a targeted recovery instruction based on the issues."""
        issues_str = ", ".join(health.issues)

        if "headline_too_short" in str(health.issues):
            return (
                f"The headline is too short or missing. "
                f"Write a compelling 6-12 word headline that states the slide's main thesis. "
                f"Issues detected: {issues_str}"
            )

        if "no_content_blocks" in str(health.issues):
            return (
                f"The slide has no content. "
                f"Generate complete slide content with headline, body text or bullets, and appropriate visual elements. "
                f"Issues detected: {issues_str}"
            )

        if "chart_data_empty" in str(health.issues):
            return (
                f"The chart has no data. "
                f"Either populate the chart with valid data points or remove the chart and use bullets instead. "
                f"Issues detected: {issues_str}"
            )

        if "diagram_nodes_empty" in str(health.issues):
            return (
                f"The diagram has no nodes. "
                f"Either populate the diagram with valid nodes and edges, or simplify to a bullet list. "
                f"Issues detected: {issues_str}"
            )

        # Generic recovery instruction
        return (
            f"Regenerate this slide with complete, high-quality content. "
            f"Ensure headline, body text, and visual elements are all present and valid. "
            f"Issues detected: {issues_str}"
        )

    async def recover_deck(
        self,
        slides: list[GeneratedSlide],
        *,
        project_id: str,
        max_concurrent: int = 3,
    ) -> list[RecoveryResult]:
        """Check all slides and recover any that are unhealthy.

        Args:
            slides: List of slides to check and potentially recover.
            project_id: Project ID for logging.
            max_concurrent: Maximum concurrent recovery operations.

        Returns:
            List of RecoveryResult for all slides that needed recovery.
        """
        # Identify unhealthy slides
        unhealthy: list[tuple[int, GeneratedSlide, SlideHealthCheck]] = []
        for i, slide in enumerate(slides):
            health = self.check_slide_health(slide)
            if not health.healthy and health.can_recover:
                unhealthy.append((i, slide, health))

        if not unhealthy:
            logger.info(
                "half_gen_deck_healthy",
                project_id=project_id,
                total_slides=len(slides),
            )
            return []

        logger.warning(
            "half_gen_deck_has_unhealthy",
            project_id=project_id,
            total_slides=len(slides),
            unhealthy_count=len(unhealthy),
            unhealthy_indices=[u[0] for u in unhealthy],
        )

        # Recover slides with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)

        async def recover_with_semaphore(
            idx: int, slide: GeneratedSlide, health: SlideHealthCheck
        ) -> RecoveryResult:
            async with semaphore:
                return await self.recover_slide(
                    slide,
                    project_id=project_id,
                    instruction=self._build_recovery_instruction(health),
                )

        results = await asyncio.gather(
            *[recover_with_semaphore(i, s, h) for i, s, h in unhealthy],
            return_exceptions=True,
        )

        # Filter out exceptions and log
        recovery_results: list[RecoveryResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "half_gen_recovery_exception",
                    project_id=project_id,
                    slide_index=unhealthy[i][0],
                    error=str(result)[:200],
                )
                recovery_results.append(RecoveryResult(
                    slide_index=unhealthy[i][0],
                    success=False,
                    attempts=0,
                    error=str(result)[:200],
                ))
            else:
                recovery_results.append(result)

        # Track recovery history
        if project_id not in self._recovery_history:
            self._recovery_history[project_id] = []
        self._recovery_history[project_id].extend(recovery_results)

        return recovery_results

    def get_recovery_stats(self, project_id: str) -> dict[str, Any]:
        """Get recovery statistics for a project."""
        history = self._recovery_history.get(project_id, [])
        if not history:
            return {"total_recoveries": 0}

        successful = [r for r in history if r.success]
        failed = [r for r in history if not r.success]
        avg_duration = sum(r.duration_ms for r in history) / len(history) if history else 0

        return {
            "total_recoveries": len(history),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(history) if history else 0,
            "avg_duration_ms": int(avg_duration),
            "fallback_used": sum(1 for r in history if r.fallback_used),
        }


def create_fallback_slide(index: int, intent: str, headline: str) -> GeneratedSlide:
    """Create a minimal fallback slide when all recovery attempts fail.

    This ensures the deck always has a complete set of slides,
    even if some are simplified fallback versions.
    """
    return GeneratedSlide(
        index=index,
        intent=intent,
        headline=headline or f"Slide {index + 1}",
        subheadline="",
        body="Content generation encountered an issue. Please regenerate this slide.",
        bullets=["Content will be regenerated on next attempt"],
        stat_blocks=[],
        chart=None,
        table=None,
        diagram=None,
        timeline=None,
        comparison=None,
        quote=None,
        team_members=[],
        image_url=None,
        image_prompt=None,
        speaker_notes="",
        citations=[],
        layout="two-column",
        render_decision={"modality": "text", "renderer": "html"},
    )
