"""
V4 Content Pipeline — Orchestrates the full slide generation process.

This is the single entry point called by the V4 generation router.
It orchestrates:
  1. Conversational Q&A pre-flight (standard mode, low-richness inputs)
  2. Company pre-flight signals extraction
  3. Deep research collection
  4. Design token resolution
  5. Skeleton planning (Skeleton-of-Thought)
  6. Parallel slide writing
  7. Quality critic evaluation
  8. Slide compilation (JSX/design-token resolved)

Returns a PipelineResult dataclass consumed by the router for MongoDB
persistence and WebSocket progress emission.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

import structlog

from app.services.v4.skeleton_planner import SkeletonPlanner, DeckSkeleton
from app.services.v4.parallel_writer import ParallelWriter, GeneratedSlide
from app.services.v4.slide_compiler import compile_slides
from app.services.v4.critic_engine import CriticEngine, CriticReport
from app.services.v4.research_collector import ResearchCollector, ResearchPacket
from app.services.v4.design_resolver import resolve_design_tokens

logger = structlog.get_logger(__name__)

# Type alias for the progress callback
ProgressCallback = Callable[[str, Dict[str, Any]], Awaitable[None]]


# ── Pipeline Result ───────────────────────────────────────────────
@dataclass
class PipelineResult:
    """Result object returned by V4ContentPipeline.generate().

    The generation_v4 router accesses every field by attribute, so all
    fields must be present even when empty/default.
    """
    slides: list[GeneratedSlide]
    deck_title: str
    narrative_arc: str
    skeleton: DeckSkeleton
    research: ResearchPacket
    mode: str
    critic: CriticReport
    duration_ms: int
    generation_id: str
    design_tokens: dict[str, Any]
    compiled_slides: list[dict[str, Any]]
    design_system: Optional[dict[str, Any]] = None
    brand_kit: Optional[dict[str, Any]] = None


# ── Redis Progress Emitter ────────────────────────────────────────

def make_redis_progress_emitter(project_id: str) -> ProgressCallback:
    """Create a progress callback that publishes to Redis pub/sub and
    appends to a progress log list for late-joining WebSocket clients.

    Matches the channel naming convention used by the v4_progress WebSocket
    handler: ``v4:progress:{project_id}``.
    """
    async def _emit(stage: str, payload: Dict[str, Any]) -> None:
        try:
            from app.utils.rate_limiter import get_redis
            r = await get_redis()
            if r is None:
                return
            event = {
                "stage": stage,
                "payload": payload,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            event_json = json.dumps(event, default=str)
            # Publish to the live channel (consumed by WS handler)
            await r.publish(f"v4:progress:{project_id}", event_json)
            # Append to the log list (consumed by polling fallback)
            await r.rpush(f"v4:progress_log:{project_id}", event_json)
            # Auto-expire the log after 2 hours
            await r.expire(f"v4:progress_log:{project_id}", 7200)
        except Exception as e:
            logger.warning("redis_progress_emit_failed", error=str(e)[:200])

    return _emit


# ── V4 Content Pipeline ──────────────────────────────────────────

class V4ContentPipeline:
    """Main content pipeline for V4 slide generation.

    Orchestrates: research → skeleton → parallel-write → critic → compile.
    Emits progress events at each stage via the provided callback.
    """

    def __init__(self) -> None:
        self.planner = SkeletonPlanner()
        self.writer = ParallelWriter()
        self.critic = CriticEngine()

    async def generate(
        self,
        *,
        project_id: str,
        user_id: str,
        user_query: str,
        analysis: Dict[str, Any],
        mode: str,
        purpose: str,
        industry: Optional[str] = None,
        company_name: Optional[str] = None,
        user_slide_types: Optional[List[str]] = None,
        target_slide_count: Optional[int] = None,
        company_icon_url: Optional[str] = None,
        design_profile: Optional[Dict[str, Any]] = None,
        structured_context: Optional[Dict[str, Any]] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> PipelineResult:
        """Run the full V4 generation pipeline.

        Args:
            project_id: Unique project identifier.
            user_id: Authenticated user ID.
            user_query: The user's presentation prompt.
            analysis: Serialized InputAnalysisResult dict.
            mode: 'standard' or 'premium'.
            purpose: Presentation purpose (pitch_deck, custom, etc.).
            industry: Detected or user-provided industry.
            company_name: Detected or user-provided company name.
            user_slide_types: Premium user-selected slide type order.
            target_slide_count: Desired number of slides.
            company_icon_url: URL of uploaded company icon (premium).
            design_profile: User's design preferences (theme, brand).
            structured_context: Premium structured input data.
            progress: Async callback for emitting progress events.

        Returns:
            PipelineResult with all data the router needs.
        """
        start_time = time.monotonic()
        generation_id = str(uuid.uuid4())[:12]

        async def emit(stage: str, payload: Dict[str, Any]) -> None:
            if progress:
                try:
                    await progress(stage, payload)
                except Exception:
                    pass

        try:
            # ──────────────────────────────────────────────────────────
            # Stage 0.5: Conversational Q&A (standard mode only)
            # ──────────────────────────────────────────────────────────
            if mode == "standard":
                richness = analysis.get("input_richness_score", 1.0)
                if richness < 0.7:
                    await self._conversational_qa(
                        project_id=project_id,
                        analysis=analysis,
                        emit=emit,
                    )

            # ──────────────────────────────────────────────────────────
            # Stage 1: Company pre-flight (extract signals from website)
            # ──────────────────────────────────────────────────────────
            await emit("stage_start", {"stage": "company_preflight"})
            company_signals: Dict[str, Any] = {}
            try:
                from app.services.v4.company_preflight import run_preflight
                company_signals = await run_preflight(
                    company_name=company_name,
                    industry=industry,
                    user_query=user_query,
                    structured_context=structured_context,
                )
            except Exception as e:
                logger.warning("company_preflight_failed", error=str(e)[:200])
            await emit("stage_complete", {"stage": "company_preflight"})

            # ──────────────────────────────────────────────────────────
            # Stage 2: Research collection
            # ──────────────────────────────────────────────────────────
            await emit("stage_start", {"stage": "research"})
            collector = ResearchCollector()
            research = await collector.collect(
                query=user_query,
                industry=industry,
                company_name=company_name,
                mode=mode,
                purpose=purpose,
            )
            await emit("stage_complete", {"stage": "research"})
            logger.info(
                "v4_research_complete",
                project_id=project_id,
                citations=len(research.citations),
                news=len(research.news_citations),
                duration_ms=research.duration_ms,
            )

            # ──────────────────────────────────────────────────────────
            # Stage 3: Design token resolution
            # ──────────────────────────────────────────────────────────
            resolved_tokens = resolve_design_tokens(
                design_profile=design_profile,
                purpose=purpose,
                industry=industry,
            )
            design_tokens_dict = resolved_tokens.to_dict()

            # ──────────────────────────────────────────────────────────
            # Stage 4: Skeleton planning
            # ──────────────────────────────────────────────────────────
            await emit("stage_start", {"stage": "skeleton"})
            skeleton = await self.planner.plan(
                project_id=project_id,
                user_query=user_query,
                research=research,
                slide_count=target_slide_count,
                narrative_arc=purpose if purpose != "custom" else "investor_pitch",
            )

            # Apply user-selected slide types for premium mode
            if user_slide_types and skeleton:
                skeleton = self._reorder_skeleton(skeleton, user_slide_types)

            await emit("skeleton_ready", {
                "slides": [
                    {
                        "index": s.index,
                        "intent": s.intent,
                        "headline_target": s.headline_target,
                    }
                    for s in skeleton.slides
                ],
            })
            await emit("stage_complete", {"stage": "skeleton"})
            logger.info(
                "v4_skeleton_complete",
                project_id=project_id,
                n_slides=len(skeleton.slides),
                title=skeleton.title[:80],
            )

            # ──────────────────────────────────────────────────────────
            # Stage 5: Parallel slide writing
            # ──────────────────────────────────────────────────────────
            await emit("stage_start", {
                "stage": "writers",
                "n_slides": len(skeleton.slides),
            })

            async def _on_slide_done(slide: GeneratedSlide) -> None:
                """Callback for each drafted slide — emit live progress."""
                await emit("slide_drafted", {
                    "index": slide.index,
                    "intent": slide.intent,
                    "headline": slide.headline,
                    "layout": slide.layout,
                })

            slides = await self.writer.write_all(
                skeleton=skeleton,
                research=research,
                mode=mode,
                purpose=purpose,
                design_tokens=design_tokens_dict,
                structured_context=structured_context,
                on_slide_done=_on_slide_done,
            )

            # Stamp company icon on title and team slides
            if company_icon_url:
                for s in slides:
                    if s.intent in {"title", "team"}:
                        s.company_icon_url = company_icon_url

            await emit("stage_complete", {"stage": "writers"})
            logger.info(
                "v4_writers_complete",
                project_id=project_id,
                n_slides=len(slides),
            )

            # ──────────────────────────────────────────────────────────
            # Stage 6: Critic evaluation
            # ──────────────────────────────────────────────────────────
            await emit("stage_start", {"stage": "critic"})
            critic_report = await self.critic.evaluate(
                slides=slides,
                skeleton=skeleton,
                research=research,
                mode=mode,
            )
            await emit("stage_complete", {"stage": "critic"})
            logger.info(
                "v4_critic_complete",
                project_id=project_id,
                overall=critic_report.overall,
            )

            # ──────────────────────────────────────────────────────────
            # Stage 7: Compile slides (resolved JSX + design tokens)
            # ──────────────────────────────────────────────────────────
            compiled_slides = compile_slides(
                slides=slides,
                image_urls=None,
                deck_title=skeleton.title,
                company_icon_url=company_icon_url,
            )

            # ──────────────────────────────────────────────────────────
            # Stage 8: Assemble result
            # ──────────────────────────────────────────────────────────
            duration_ms = int((time.monotonic() - start_time) * 1000)

            result = PipelineResult(
                slides=slides,
                deck_title=skeleton.title,
                narrative_arc=skeleton.narrative_arc,
                skeleton=skeleton,
                research=research,
                mode=mode,
                critic=critic_report,
                duration_ms=duration_ms,
                generation_id=generation_id,
                design_tokens=design_tokens_dict,
                compiled_slides=compiled_slides,
                design_system=None,  # Populated by Phase 2 (future)
                brand_kit=None,      # Populated by Phase 2.2 (future)
            )

            await emit("complete", {
                "n_slides": len(slides),
                "overall_score": round(critic_report.overall, 2),
                "duration_ms": duration_ms,
            })

            logger.info(
                "v4_pipeline_complete",
                project_id=project_id,
                mode=mode,
                n_slides=len(slides),
                overall_score=critic_report.overall,
                duration_ms=duration_ms,
            )

            return result

        except Exception as e:
            logger.error(
                "v4_pipeline_failed",
                project_id=project_id,
                error=str(e)[:500],
                exc_info=True,
            )
            await emit("error", {"error": str(e)[:500]})
            raise

    # ── Conversational Q&A pre-flight ─────────────────────────────

    async def _conversational_qa(
        self,
        *,
        project_id: str,
        analysis: Dict[str, Any],
        emit: ProgressCallback,
    ) -> None:
        """Standard mode only: generate clarifying questions if the input
        is too sparse. Uses the existing WebSocket awaiting_input mechanism.
        """
        try:
            from app.services.v4.question_generator import ConversationalQuestionGenerator
            from app.services.v4.interactive_prompt import ask
            from app.models.generation_input_v4 import InputAnalysisResult

            qg = ConversationalQuestionGenerator()
            # Reconstruct the analysis result for the question generator
            analysis_result = InputAnalysisResult(**analysis)
            questions = await qg.generate(analysis_result)

            if not questions:
                return

            await emit("stage_start", {"stage": "conversational_qa"})

            # Ask via the interactive prompt system (polls Redis for answer)
            answer = await ask(
                project_id=project_id,
                emit=emit,
                kind="conversational_qa",
                schema={"questions": questions},
                optional=True,
                timeout_s=300,
            )

            if answer:
                logger.info(
                    "v4_qa_answered",
                    project_id=project_id,
                    n_questions=len(questions),
                )

            await emit("stage_complete", {"stage": "conversational_qa"})

        except Exception as e:
            logger.warning("v4_conversational_qa_failed", error=str(e)[:200])

    # ── Skeleton reordering ───────────────────────────────────────

    @staticmethod
    def _reorder_skeleton(
        skeleton: DeckSkeleton,
        user_slide_types: List[str],
    ) -> DeckSkeleton:
        """Reorder skeleton slides to match user-selected slide type order.

        This is a best-effort mapping — user_slide_types are intent strings
        like ["title", "problem", "solution", "market", ...]. The planner
        may have generated slightly different intents; we match by substring.
        """
        intent_map: Dict[str, Any] = {}
        remaining = list(skeleton.slides)

        for slide in skeleton.slides:
            intent_map.setdefault(slide.intent.lower(), []).append(slide)

        ordered = []
        for user_type in user_slide_types:
            ut = user_type.lower().strip()
            candidates = intent_map.get(ut, [])
            if candidates:
                ordered.append(candidates.pop(0))
                remaining = [s for s in remaining if s not in ordered]
            else:
                # Fuzzy match
                for s in remaining:
                    if ut in s.intent.lower() or s.intent.lower() in ut:
                        ordered.append(s)
                        remaining.remove(s)
                        break

        # Append any remaining slides not matched
        ordered.extend(remaining)

        # Re-index
        for i, s in enumerate(ordered):
            s.index = i

        return DeckSkeleton(
            project_id=skeleton.project_id,
            title=skeleton.title,
            narrative_arc=skeleton.narrative_arc,
            slides=ordered,
            raw_planner_output=skeleton.raw_planner_output,
        )

    # ── Single-slide editing ──────────────────────────────────────

    async def edit_slide(
        self,
        project_id: str,
        slide_id: str,
        edits: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Edit a specific slide (delegated to regen_engine)."""
        try:
            from app.services.v4.regen_engine import edit_single_slide
            return await edit_single_slide(
                project_id=project_id,
                slide_id=slide_id,
                edits=edits,
                context=context,
            )
        except Exception as e:
            logger.error(f"Slide edit failed: {e}", exc_info=True)
            raise

    async def regenerate_slide(
        self,
        project_id: str,
        slide_id: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Regenerate a specific slide (delegated to regen_engine)."""
        try:
            from app.services.v4.regen_engine import regenerate_single_slide
            return await regenerate_single_slide(
                project_id=project_id,
                slide_id=slide_id,
                reason=reason,
                context=context,
            )
        except Exception as e:
            logger.error(f"Slide regeneration failed: {e}", exc_info=True)
            raise
