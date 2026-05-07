"""
Evidence Bridge — Maps Brain MCP SlideContentContracts into V7 ContextBoard.

This adapter is the one-way bridge that feeds premium evidence (from the
Brain MCP research pipeline) into the V7 orchestrator's inter-agent
communication layer.  When evidence_contracts are provided, the V7
ResearcherAgent is SKIPPED because all research data is already available
on the ContextBoard in the exact format downstream agents expect.

Key mappings:
  SlideContentContract.presentation_content → research.slide:{id}:presentation
  SlideContentContract.reading_content      → research.slide:{id}:reading
  SlideContentContract.citations            → research.citations
  SlideContentContract.chart_data           → research.chart_data:{id}
  DebateOutcome (if any)                    → strategy.debate_outcomes
  Evidence metrics                          → research.evidence_metrics
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.services.context_board import ContextBoard
from app.mcp.brain_mcp.research.models import (
    SlideContentContract,
    DebateOutcome,
)

logger = logging.getLogger(__name__)


class EvidenceBridge:
    """
    One-way adapter: Brain MCP SlideContentContracts → V7 ContextBoard.

    After calling ``bridge_to_context()``, all downstream V7 agents
    (Layout, Code, Assembler, QA) can read the pre-researched evidence
    as though the ResearcherAgent produced it.
    """

    def __init__(self, board: ContextBoard) -> None:
        self._board = board

    # ── Main entry point ─────────────────────────────────────

    async def bridge_to_context(
        self,
        contracts: list[SlideContentContract],
        debate_outcomes: Optional[list[DebateOutcome]] = None,
    ) -> None:
        """
        Write all evidence from *contracts* into the ContextBoard so
        that downstream agents can consume them.

        Args:
            contracts: List of SlideContentContracts from the Brain MCP
                       research pipeline.
            debate_outcomes: Optional list of debate results to inject
                             into strategy section.
        """
        if not contracts:
            logger.warning("evidence_bridge_no_contracts")
            return

        # ── Per-slide data ───────────────────────────────────
        all_citations: list[dict] = []
        slide_summaries: list[dict] = []

        for contract in contracts:
            sid = contract.slide_id

            # Presentation content → research section
            await self._board.set(
                f"research.slide:{sid}:presentation",
                contract.presentation_content.to_dict(),
                agent="evidence_bridge",
            )

            # Reading content → research section
            await self._board.set(
                f"research.slide:{sid}:reading",
                contract.reading_content.to_dict(),
                agent="evidence_bridge",
            )

            # Speaker notes
            if contract.speaker_notes:
                await self._board.set(
                    f"research.slide:{sid}:speaker_notes",
                    contract.speaker_notes,
                    agent="evidence_bridge",
                )

            # Chart data → for Code Agent
            if contract.chart_data:
                await self._board.set(
                    f"research.chart_data:{sid}",
                    contract.chart_data,
                    agent="evidence_bridge",
                )

            # Image prompt → for Image / VFX Agent
            if contract.image_prompt:
                await self._board.set(
                    f"research.image_prompt:{sid}",
                    contract.image_prompt,
                    agent="evidence_bridge",
                )

            # Collect citations for global list
            for cit in contract.citations:
                all_citations.append(cit.to_dict())

            # Slide summary for researcher output format
            slide_summaries.append({
                "slide_id": sid,
                "slide_kind": contract.slide_kind.value,
                "title": contract.presentation_content.title,
                "evidence_score": contract.evidence_score,
                "style_id": contract.style_id,
                "has_chart": contract.chart_data is not None,
                "has_image_prompt": contract.image_prompt is not None,
                "citation_count": len(contract.citations),
            })

        # ── Global data ──────────────────────────────────────

        # All citations aggregated
        await self._board.set(
            "research.citations",
            all_citations,
            agent="evidence_bridge",
        )

        # Slide summaries (researcher-format output)
        await self._board.set(
            "research.slide_summaries",
            slide_summaries,
            agent="evidence_bridge",
        )

        # Evidence metrics (telemetry)
        metrics = self.extract_evidence_metrics(contracts)
        await self._board.set(
            "research.evidence_metrics",
            metrics,
            agent="evidence_bridge",
        )

        # Research summary (compact dict matching ResearcherAgent output)
        summary = self.extract_research_summary(contracts)
        await self._board.set(
            "research.summary",
            summary,
            agent="evidence_bridge",
        )

        # Debate outcomes → strategy section
        if debate_outcomes:
            await self._board.set(
                "strategy.debate_outcomes",
                [d.to_dict() for d in debate_outcomes],
                agent="evidence_bridge",
            )

        logger.info(
            "evidence_bridge_complete",
            slides=len(contracts),
            citations=len(all_citations),
            metrics=metrics,
        )

    # ── Summary extractors ───────────────────────────────────

    @staticmethod
    def extract_research_summary(contracts: list[SlideContentContract]) -> dict:
        """
        Produce a compact research dict matching what the ResearcherAgent
        normally writes to ContextBoard under ``research.summary``.
        """
        total_facts = 0
        total_approved = 0
        total_rejected = 0
        models_used: set[str] = set()
        styles_used: set[str] = set()

        for c in contracts:
            meta = c.generation_metadata
            total_facts += meta.total_fact_packets
            total_approved += meta.approved_claims
            total_rejected += meta.rejected_claims
            models_used.update(meta.models_used)
            styles_used.add(c.style_id)

        return {
            "source": "brain_mcp_premium",
            "total_slides": len(contracts),
            "total_fact_packets": total_facts,
            "approved_claims": total_approved,
            "rejected_claims": total_rejected,
            "models_used": sorted(models_used),
            "styles_applied": sorted(styles_used),
            "avg_evidence_score": round(
                sum(c.evidence_score for c in contracts) / max(len(contracts), 1),
                3,
            ),
        }

    @staticmethod
    def extract_evidence_metrics(contracts: list[SlideContentContract]) -> dict:
        """
        Aggregate telemetry from all contracts for monitoring/reporting.
        """
        total_providers = 0
        total_facts = 0
        total_approved = 0
        total_rejected = 0
        total_tokens = 0
        total_errors_recovered = 0
        all_models: set[str] = set()
        evidence_scores: list[float] = []

        for c in contracts:
            meta = c.generation_metadata
            total_providers += meta.total_providers_queried
            total_facts += meta.total_fact_packets
            total_approved += meta.approved_claims
            total_rejected += meta.rejected_claims
            total_tokens += meta.total_tokens
            total_errors_recovered += meta.errors_recovered
            all_models.update(meta.models_used)
            evidence_scores.append(c.evidence_score)

        avg_ev = sum(evidence_scores) / max(len(evidence_scores), 1)

        return {
            "total_providers_queried": total_providers,
            "total_fact_packets": total_facts,
            "approved_claims": total_approved,
            "rejected_claims": total_rejected,
            "total_tokens": total_tokens,
            "errors_recovered": total_errors_recovered,
            "models_used": sorted(all_models),
            "avg_evidence_score": round(avg_ev, 3),
            "slide_count": len(contracts),
        }
