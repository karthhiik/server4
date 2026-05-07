"""
Content event emitter for WebSocket / SSE streaming.

Publishes ContentEventPayload objects to Redis pub/sub on channel
``deck:{deck_id}:events``.  Falls back to structured logging when
Redis is unavailable so no events are silently lost.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import (
    ContentEvent,
    ContentEventPayload,
    FactPacket,
    SlideContentContract,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# STAGE → PROGRESS WEIGHT MAP
# ═══════════════════════════════════════════════════════════════════════

_STAGE_WEIGHTS: dict[str, tuple[float, float]] = {
    # (stage_start, stage_end)  — fraction of the overall 0-1 progress bar
    "research":      (0.00, 0.30),
    "evidence":      (0.30, 0.50),
    "debate":        (0.50, 0.60),
    "generation":    (0.60, 0.90),
    "verification":  (0.90, 1.00),
}

_EVENT_TO_STAGE: dict[ContentEvent, str] = {
    ContentEvent.DECK_CONTEXT_READY:       "research",
    ContentEvent.INTENT_CLASSIFIED:        "research",
    ContentEvent.RESEARCH_PLAN_READY:      "research",
    ContentEvent.SLIDE_RESEARCH_PLANNED:   "research",
    ContentEvent.PROVIDER_SELECTED:        "research",
    ContentEvent.PROVIDER_SKIPPED:         "research",
    ContentEvent.SOURCE_FETCHING:          "research",
    ContentEvent.SOURCE_FETCHED:           "research",
    ContentEvent.SOURCE_FAILED:            "research",
    ContentEvent.QUERY_REWRITTEN:          "research",

    ContentEvent.FACT_PACKET_CREATED:      "evidence",
    ContentEvent.FACT_PACKET_REJECTED:     "evidence",
    ContentEvent.CROSS_VALIDATION_RESULT:  "evidence",
    ContentEvent.EVIDENCE_GRAPH_UPDATED:   "evidence",
    ContentEvent.COMMUNITY_SUMMARY_READY:  "evidence",
    ContentEvent.EVIDENCE_BUNDLE_READY:    "evidence",

    ContentEvent.CEO_THESIS_READY:         "debate",
    ContentEvent.CTO_CHALLENGE_READY:      "debate",
    ContentEvent.FINANCE_CHALLENGE_READY:  "debate",
    ContentEvent.DEBATE_ROUND_COMPLETE:    "debate",
    ContentEvent.DEBATE_RESOLVED:          "debate",

    ContentEvent.SLIDE_BRIEF_READY:        "generation",
    ContentEvent.PRESENTATION_COPY_READY:  "generation",
    ContentEvent.READING_COPY_READY:       "generation",
    ContentEvent.SPEAKER_NOTES_READY:      "generation",
    ContentEvent.CHART_DATA_READY:         "generation",
    ContentEvent.IMAGE_PROMPT_READY:       "generation",
    ContentEvent.CITATIONS_VERIFIED:       "generation",

    ContentEvent.SLIDE_CONTENT_READY:      "verification",
    ContentEvent.SLIDE_CONTENT_BLOCKED:    "verification",
    ContentEvent.DECK_CONTENT_COMPLETE:    "verification",
}


class ContentEventEmitter:
    """
    Publishes slide-content pipeline events to Redis pub/sub channel
    ``deck:{deck_id}:events``.

    Every event is also stored in a Redis list ``deck:{deck_id}:log``
    (capped at 500 entries) so that late-connecting WebSocket clients
    can replay missed events.
    """

    _LOG_CAP: int = 500

    def __init__(self, deck_id: str, redis_client: Any = None) -> None:
        self._deck_id = deck_id
        self._redis = redis_client
        self._channel = f"deck:{deck_id}:events"
        self._log_key = f"deck:{deck_id}:log"
        self._event_count: int = 0

    # ── Core emit ───────────────────────────────────────────────

    async def emit(
        self,
        event: ContentEvent,
        slide_id: Optional[str] = None,
        data: dict | None = None,
        progress: float | None = None,
        stage: str | None = None,
        message: str = "",
    ) -> None:
        """
        Build a ContentEventPayload, publish to Redis pub/sub, and
        append to the replay log list.
        """
        self._event_count += 1

        resolved_stage = stage or _EVENT_TO_STAGE.get(event, "research")

        if progress is None:
            progress = self._compute_progress_auto(event, resolved_stage)

        payload = ContentEventPayload(
            event=event.value,
            slide_id=slide_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data or {},
            progress=max(0.0, min(1.0, progress)),
            stage=resolved_stage,
            message=message,
        )

        payload_json = json.dumps(payload.to_dict(), default=str)

        if self._redis is not None:
            try:
                await self._redis.publish(self._channel, payload_json)
                await self._redis.rpush(self._log_key, payload_json)
                await self._redis.ltrim(self._log_key, -self._LOG_CAP, -1)
            except Exception as exc:
                logger.warning(
                    "Redis publish/log failed for %s: %s",
                    event.value,
                    exc,
                )
                self._log_fallback(payload)
        else:
            self._log_fallback(payload)

    def _log_fallback(self, payload: ContentEventPayload) -> None:
        logger.info(
            "[%s] event=%s slide=%s progress=%.2f stage=%s msg=%s",
            self._deck_id,
            payload.event,
            payload.slide_id or "-",
            payload.progress,
            payload.stage,
            payload.message,
        )

    def _compute_progress_auto(
        self, event: ContentEvent, stage: str
    ) -> float:
        """
        Estimate overall progress based on stage and the event's position
        within that stage's known event set.
        """
        stage_start, stage_end = _STAGE_WEIGHTS.get(stage, (0.0, 1.0))
        stage_span = stage_end - stage_start

        # Count how many events belong to this stage
        events_in_stage = [
            e for e, s in _EVENT_TO_STAGE.items() if s == stage
        ]
        try:
            idx = events_in_stage.index(event)
        except ValueError:
            idx = 0
        total = max(len(events_in_stage), 1)

        return stage_start + stage_span * ((idx + 1) / total)

    # ── Progress with slide tracking ────────────────────────────

    def _compute_progress(
        self,
        stage: str,
        slide_index: int,
        total_slides: int,
    ) -> float:
        """
        Compute overall progress incorporating per-slide position.

        ``slide_index`` is 0-based.  Returns a float in [0.0, 1.0].
        """
        stage_start, stage_end = _STAGE_WEIGHTS.get(stage, (0.0, 1.0))
        stage_span = stage_end - stage_start

        if total_slides <= 0:
            return stage_start

        slide_frac = (slide_index + 1) / total_slides
        return stage_start + stage_span * slide_frac

    # ── Convenience methods for all 30 events ───────────────────

    # ── Research phase ──────────────────────────────────────────

    async def deck_context_ready(self, data: dict) -> None:
        await self.emit(
            ContentEvent.DECK_CONTEXT_READY,
            data=data,
            message="User brief parsed and deck context assembled",
        )

    async def intent_classified(self, data: dict) -> None:
        await self.emit(
            ContentEvent.INTENT_CLASSIFIED,
            data=data,
            message=f"Deck type: {data.get('deck_type', 'unknown')}, "
                    f"audience: {data.get('audience', 'unknown')}",
        )

    async def research_plan_ready(self, data: dict) -> None:
        await self.emit(
            ContentEvent.RESEARCH_PLAN_READY,
            data=data,
            message=f"Research plan ready — {data.get('total_queries', 0)} queries planned",
        )

    async def slide_research_planned(
        self, slide_id: str, data: dict
    ) -> None:
        await self.emit(
            ContentEvent.SLIDE_RESEARCH_PLANNED,
            slide_id=slide_id,
            data=data,
            message=f"Research plan for {slide_id}",
        )

    async def provider_selected(
        self, slide_id: str, provider: str, reason: str = ""
    ) -> None:
        await self.emit(
            ContentEvent.PROVIDER_SELECTED,
            slide_id=slide_id,
            data={"provider": provider, "reason": reason},
            message=f"Selected provider: {provider}",
        )

    async def provider_skipped(
        self, slide_id: str, provider: str, reason: str
    ) -> None:
        await self.emit(
            ContentEvent.PROVIDER_SKIPPED,
            slide_id=slide_id,
            data={"provider": provider, "reason": reason},
            message=f"Skipped {provider}: {reason}",
        )

    async def source_fetching(
        self, slide_id: str, provider: str
    ) -> None:
        await self.emit(
            ContentEvent.SOURCE_FETCHING,
            slide_id=slide_id,
            data={"provider": provider},
            message=f"Fetching from {provider}…",
        )

    async def source_fetched(
        self, slide_id: str, provider: str, results_count: int
    ) -> None:
        await self.emit(
            ContentEvent.SOURCE_FETCHED,
            slide_id=slide_id,
            data={"provider": provider, "results_count": results_count},
            message=f"{provider} returned {results_count} results",
        )

    async def source_failed(
        self, slide_id: str, provider: str, error: str, recovery: str
    ) -> None:
        await self.emit(
            ContentEvent.SOURCE_FAILED,
            slide_id=slide_id,
            data={
                "provider": provider,
                "error": error,
                "recovery_action": recovery,
            },
            message=f"{provider} failed: {error}. Recovery: {recovery}",
        )

    async def query_rewritten(
        self,
        slide_id: str,
        original: str,
        rewritten: str,
        reason: str,
    ) -> None:
        await self.emit(
            ContentEvent.QUERY_REWRITTEN,
            slide_id=slide_id,
            data={
                "original_query": original,
                "rewritten_query": rewritten,
                "reason": reason,
            },
            message=f"Query rewritten: {rewritten[:60]}…",
        )

    # ── Evidence phase ──────────────────────────────────────────

    async def fact_packet_created(
        self, slide_id: str, fact: FactPacket
    ) -> None:
        await self.emit(
            ContentEvent.FACT_PACKET_CREATED,
            slide_id=slide_id,
            data={
                "fact_id": fact.id,
                "claim": fact.claim[:120],
                "provider": fact.provider,
                "claim_type": fact.claim_type.value,
                "confidence": fact.confidence,
                "citation_label": fact.citation_label,
            },
            message=f"Evidence from {fact.provider}: {fact.claim[:80]}…",
        )

    async def fact_packet_rejected(
        self,
        slide_id: str,
        fact_id: str,
        reason: str,
    ) -> None:
        await self.emit(
            ContentEvent.FACT_PACKET_REJECTED,
            slide_id=slide_id,
            data={"fact_id": fact_id, "reason": reason},
            message=f"Rejected fact {fact_id}: {reason}",
        )

    async def cross_validation_result(
        self,
        slide_id: str,
        fact_id: str,
        validated: bool,
        sources: list[str],
    ) -> None:
        await self.emit(
            ContentEvent.CROSS_VALIDATION_RESULT,
            slide_id=slide_id,
            data={
                "fact_id": fact_id,
                "validated": validated,
                "sources": sources,
            },
            message=(
                f"Cross-validated {fact_id} across {len(sources)} sources"
                if validated
                else f"Cross-validation failed for {fact_id}"
            ),
        )

    async def evidence_graph_updated(
        self, slide_id: str, data: dict
    ) -> None:
        await self.emit(
            ContentEvent.EVIDENCE_GRAPH_UPDATED,
            slide_id=slide_id,
            data=data,
            message="Evidence graph updated",
        )

    async def community_summary_ready(self, data: dict) -> None:
        await self.emit(
            ContentEvent.COMMUNITY_SUMMARY_READY,
            data=data,
            message="Global theme summaries ready",
        )

    async def evidence_bundle_ready(
        self, slide_id: str, evidence_score: float, total_facts: int
    ) -> None:
        await self.emit(
            ContentEvent.EVIDENCE_BUNDLE_READY,
            slide_id=slide_id,
            data={
                "evidence_score": evidence_score,
                "total_facts": total_facts,
            },
            message=f"Evidence bundle ready (score={evidence_score:.2f}, {total_facts} facts)",
        )

    # ── Debate phase ────────────────────────────────────────────

    async def ceo_thesis_ready(
        self, slide_id: str, thesis: str
    ) -> None:
        await self.emit(
            ContentEvent.CEO_THESIS_READY,
            slide_id=slide_id,
            data={"thesis": thesis},
            message=f"CEO thesis: {thesis[:80]}…",
        )

    async def cto_challenge_ready(
        self, slide_id: str, challenges: list[str]
    ) -> None:
        await self.emit(
            ContentEvent.CTO_CHALLENGE_READY,
            slide_id=slide_id,
            data={"challenges": challenges},
            message=f"CTO raised {len(challenges)} challenge(s)",
        )

    async def finance_challenge_ready(
        self, slide_id: str, challenges: list[str]
    ) -> None:
        await self.emit(
            ContentEvent.FINANCE_CHALLENGE_READY,
            slide_id=slide_id,
            data={"challenges": challenges},
            message=f"Finance raised {len(challenges)} challenge(s)",
        )

    async def debate_round_complete(
        self,
        slide_id: str,
        round_number: int,
        approved: int,
        rejected: int,
    ) -> None:
        await self.emit(
            ContentEvent.DEBATE_ROUND_COMPLETE,
            slide_id=slide_id,
            data={
                "round": round_number,
                "approved": approved,
                "rejected": rejected,
            },
            message=f"Debate round {round_number}: {approved} approved, {rejected} rejected",
        )

    async def debate_resolved(
        self,
        slide_id: str,
        total_approved: int,
        total_rejected: int,
        iterations: int,
    ) -> None:
        await self.emit(
            ContentEvent.DEBATE_RESOLVED,
            slide_id=slide_id,
            data={
                "total_approved": total_approved,
                "total_rejected": total_rejected,
                "iterations": iterations,
            },
            message=f"Debate resolved: {total_approved} claims approved after {iterations} rounds",
        )

    # ── Generation phase ────────────────────────────────────────

    async def slide_brief_ready(
        self, slide_id: str, data: dict
    ) -> None:
        await self.emit(
            ContentEvent.SLIDE_BRIEF_READY,
            slide_id=slide_id,
            data=data,
            message=f"Slide brief assembled for {slide_id}",
        )

    async def presentation_copy_ready(
        self, slide_id: str, title: str
    ) -> None:
        await self.emit(
            ContentEvent.PRESENTATION_COPY_READY,
            slide_id=slide_id,
            data={"title": title},
            message=f"Presentation copy ready: {title}",
        )

    async def reading_copy_ready(self, slide_id: str) -> None:
        await self.emit(
            ContentEvent.READING_COPY_READY,
            slide_id=slide_id,
            data={},
            message=f"Reading mode copy ready for {slide_id}",
        )

    async def speaker_notes_ready(
        self, slide_id: str, notes_count: int
    ) -> None:
        await self.emit(
            ContentEvent.SPEAKER_NOTES_READY,
            slide_id=slide_id,
            data={"notes_count": notes_count},
            message=f"Speaker notes ready ({notes_count} notes)",
        )

    async def chart_data_ready(
        self, slide_id: str, chart_type: str
    ) -> None:
        await self.emit(
            ContentEvent.CHART_DATA_READY,
            slide_id=slide_id,
            data={"chart_type": chart_type},
            message=f"Chart data synthesised ({chart_type})",
        )

    async def image_prompt_ready(
        self, slide_id: str, prompt: str
    ) -> None:
        await self.emit(
            ContentEvent.IMAGE_PROMPT_READY,
            slide_id=slide_id,
            data={"prompt": prompt[:200]},
            message=f"Image prompt generated for {slide_id}",
        )

    async def citations_verified(
        self, slide_id: str, total_citations: int, verified: int
    ) -> None:
        await self.emit(
            ContentEvent.CITATIONS_VERIFIED,
            slide_id=slide_id,
            data={
                "total_citations": total_citations,
                "verified": verified,
            },
            message=f"Citations verified: {verified}/{total_citations}",
        )

    # ── Final ───────────────────────────────────────────────────

    async def slide_content_ready(
        self, slide_id: str, contract: SlideContentContract
    ) -> None:
        await self.emit(
            ContentEvent.SLIDE_CONTENT_READY,
            slide_id=slide_id,
            data={
                "slide_kind": contract.slide_kind.value,
                "evidence_score": contract.evidence_score,
                "style_id": contract.style_id,
                "citations_count": len(contract.citations),
            },
            progress=None,
            message=f"Slide ready: {contract.presentation_content.title}",
        )

    async def slide_content_blocked(
        self,
        slide_id: str,
        failure_type: str,
        user_message: str,
    ) -> None:
        await self.emit(
            ContentEvent.SLIDE_CONTENT_BLOCKED,
            slide_id=slide_id,
            data={
                "failure_type": failure_type,
                "user_message": user_message,
            },
            message=f"Slide blocked: {user_message}",
        )

    async def deck_content_complete(
        self, total_slides: int, total_time_ms: float
    ) -> None:
        await self.emit(
            ContentEvent.DECK_CONTENT_COMPLETE,
            data={
                "total_slides": total_slides,
                "total_time_ms": total_time_ms,
            },
            progress=1.0,
            message=(
                f"All {total_slides} slides complete in "
                f"{total_time_ms / 1000:.1f}s"
            ),
        )
