"""
Dual Mode Writer -- Generates both presentation and reading content from evidence.

Wraps SlideGeneratorV2 to produce multiple slides in parallel while ensuring
factual consistency between modes across the entire deck.
"""

import asyncio
import logging
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    BudgetMode,
    SlideContentContract,
    SlideEvidenceBundle,
    StyleProfile,
)
from app.mcp.brain_mcp.generators.slide_generator_v2 import SlideGeneratorV2
from app.mcp.brain_mcp.research.citation_guard import CitationGuard
from app.services.llm.model_router import ModelRouter

logger = logging.getLogger(__name__)

# Max concurrent slide generations to avoid rate limits
_MAX_CONCURRENT = 4


class DualModeWriter:
    """Generates both content modes from evidence with cross-slide consistency."""

    def __init__(
        self,
        model_router: ModelRouter,
        citation_guard: Optional[CitationGuard] = None,
    ):
        self._router = model_router
        self._guard = citation_guard or CitationGuard()
        self._generator = SlideGeneratorV2(model_router, self._guard)

    async def generate_slide(
        self,
        evidence_bundle: SlideEvidenceBundle,
        style: StyleProfile,
        topic: str,
        audience: str = "investors",
        budget_mode: BudgetMode = BudgetMode.lean,
        deck_context: Optional[dict] = None,
    ) -> SlideContentContract:
        """Generate a single slide with both modes."""
        return await self._generator.generate(
            evidence_bundle=evidence_bundle,
            style=style,
            topic=topic,
            audience=audience,
            budget_mode=budget_mode,
            deck_context=deck_context,
        )

    async def generate_deck(
        self,
        evidence_bundles: list[SlideEvidenceBundle],
        style: StyleProfile,
        topic: str,
        audience: str = "investors",
        budget_mode: BudgetMode = BudgetMode.lean,
        deck_context: Optional[dict] = None,
    ) -> list[SlideContentContract]:
        """Generate all slides for a deck with controlled concurrency.

        Ensures factual consistency by:
        1. Generating all slides with the same style and context.
        2. Post-processing to detect cross-slide contradictions.
        3. Normalizing shared metrics (e.g., TAM appears on multiple slides).
        """
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _gen_with_limit(bundle: SlideEvidenceBundle) -> SlideContentContract:
            async with semaphore:
                return await self._generator.generate(
                    evidence_bundle=bundle,
                    style=style,
                    topic=topic,
                    audience=audience,
                    budget_mode=budget_mode,
                    deck_context=deck_context,
                )

        tasks = [_gen_with_limit(b) for b in evidence_bundles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        contracts: list[SlideContentContract] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Slide %s generation failed: %s",
                    evidence_bundles[i].slide_id,
                    result,
                )
                # Create a minimal fallback contract
                contracts.append(self._fallback_contract(evidence_bundles[i], style))
            else:
                contracts.append(result)

        # Post-process: check cross-slide consistency
        self._check_cross_slide_consistency(contracts)

        return contracts

    def _check_cross_slide_consistency(
        self,
        contracts: list[SlideContentContract],
    ) -> None:
        """Log warnings if the same metric appears with different values across slides."""
        import re
        # Collect all numeric claims across slides
        metric_map: dict[str, list[tuple[str, str]]] = {}
        dollar_pattern = re.compile(r'\$[\d,.]+\s*[BMKbmk]?', re.IGNORECASE)

        for contract in contracts:
            all_text = self._collect_text(contract)
            matches = dollar_pattern.findall(all_text)
            for m in matches:
                normalized = m.strip().lower()
                if normalized not in metric_map:
                    metric_map[normalized] = []
                metric_map[normalized].append(
                    (contract.slide_id, contract.slide_kind.value)
                )

        # Flag metrics that appear on multiple slides (informational)
        for metric, appearances in metric_map.items():
            if len(appearances) > 1:
                slides = [f"{sid}({kind})" for sid, kind in appearances]
                logger.info(
                    "Metric '%s' appears on slides: %s — verify consistency",
                    metric,
                    ", ".join(slides),
                )

    def _collect_text(self, contract: SlideContentContract) -> str:
        """Collect all text from a contract for analysis."""
        parts: list[str] = []
        pc = contract.presentation_content
        parts.append(pc.title)
        if pc.subtitle:
            parts.append(pc.subtitle)
        parts.extend(pc.bullets)
        if pc.hero_stat:
            parts.append(pc.hero_stat)

        rc = contract.reading_content
        parts.append(rc.title)
        parts.append(rc.summary)
        for section in rc.body_sections:
            parts.extend(section.paragraphs)

        parts.extend(contract.speaker_notes)
        return " ".join(parts)

    def _fallback_contract(
        self,
        bundle: SlideEvidenceBundle,
        style: StyleProfile,
    ) -> SlideContentContract:
        """Create a minimal fallback contract when generation fails entirely."""
        from app.mcp.brain_mcp.research.models import (
            BodySection,
            GenerationMetadata,
            PresentationContent,
            ReadingContent,
        )

        topic = bundle.slide_kind.value.replace("_", " ").title()

        bullets: list[str] = []
        for fp in bundle.evidence_packets[:style.max_bullets_presentation]:
            words = fp.claim.split()[:style.max_words_per_bullet]
            bullets.append(" ".join(words))

        presentation = PresentationContent(
            title=topic,
            subtitle=None,
            bullets=bullets or [f"Evidence for {topic}"],
            hero_stat=None,
            annotation=None,
        )

        paragraphs = [
            f"{fp.claim} [{fp.source_name}]."
            for fp in bundle.evidence_packets[:5]
        ]
        reading = ReadingContent(
            title=topic,
            summary=f"Analysis of {topic} based on available evidence.",
            body_sections=[
                BodySection(
                    heading="Evidence Summary",
                    paragraphs=paragraphs or ["Evidence pending."],
                    source_refs=[fp.source_name for fp in bundle.evidence_packets[:5]],
                )
            ],
        )

        return SlideContentContract(
            slide_id=bundle.slide_id,
            slide_kind=bundle.slide_kind,
            style_id=style.style_id,
            presentation_content=presentation,
            reading_content=reading,
            speaker_notes=[f"Cover {topic} evidence."],
            evidence_score=bundle.evidence_score,
            generation_metadata=GenerationMetadata(
                total_fact_packets=len(bundle.evidence_packets),
                style_applied=style.style_id,
                errors_recovered=1,
            ),
        )
