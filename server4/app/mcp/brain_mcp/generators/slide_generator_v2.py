"""
Slide Generator V2 -- Evidence-based content generation.

Key differences from V1:
- Accepts SlideEvidenceBundle instead of flat research string
- Outputs SlideContentContract with dual modes
- Uses debate-approved claims only
- Applies style profiles
- Generates citations inline
"""

import asyncio
import json
import logging
import time
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    BodySection,
    BudgetMode,
    Citation,
    ClaimType,
    FactPacket,
    GenerationMetadata,
    PresentationContent,
    ReadingContent,
    SlideContentContract,
    SlideEvidenceBundle,
    SlideKind,
    StyleProfile,
)
from app.mcp.brain_mcp.research.citation_guard import CitationGuard
from app.mcp.brain_mcp.prompts.mode_transformers import ModeTransformer
from app.mcp.brain_mcp.generators.chart_data_synthesizer import ChartDataSynthesizer
from app.mcp.brain_mcp.generators.image_prompt_generator import ImagePromptGenerator
from app.services.llm.model_router import ModelRouter, TaskType

logger = logging.getLogger(__name__)

# Slide kinds that benefit from chart data
_CHART_SLIDE_KINDS = {
    SlideKind.traction,
    SlideKind.financial,
    SlideKind.market,
    SlideKind.competition,
}

# Slide kinds that benefit from image prompts
_IMAGE_SLIDE_KINDS = {
    SlideKind.title,
    SlideKind.problem,
    SlideKind.solution,
    SlideKind.why_now,
    SlideKind.product_demo,
}


class SlideGeneratorV2:
    """Evidence-based slide content generator."""

    def __init__(
        self,
        model_router: ModelRouter,
        citation_guard: Optional[CitationGuard] = None,
    ):
        self._router = model_router
        self._guard = citation_guard or CitationGuard()
        self._transformer = ModeTransformer(model_router)
        self._chart_synth = ChartDataSynthesizer()
        self._image_gen = ImagePromptGenerator()

    async def generate(
        self,
        evidence_bundle: SlideEvidenceBundle,
        style: StyleProfile,
        topic: str,
        audience: str = "investors",
        budget_mode: BudgetMode = BudgetMode.lean,
        deck_context: Optional[dict] = None,
    ) -> SlideContentContract:
        """
        Generate complete slide content from evidence.

        Pipeline:
        1. Build reading mode first (deeper reasoning)
        2. Compress to presentation mode
        3. Generate speaker notes
        4. Generate chart data if needed
        5. Generate image prompt if needed
        6. Verify citations
        7. Assemble SlideContentContract
        """
        start_time = time.monotonic()
        models_used: list[str] = []
        total_tokens = 0
        errors_recovered = 0

        # Filter to approved claims only
        approved_packets = self._filter_approved(evidence_bundle)
        evidence_text = self._format_evidence_for_prompt(evidence_bundle)

        # Step 1: Generate reading mode
        try:
            reading = await self._generate_reading_mode(
                evidence_bundle=evidence_bundle,
                style=style,
                topic=topic,
                audience=audience,
            )
            models_used.append("reading_gen")
        except Exception as e:
            logger.error("Reading mode generation failed: %s", e)
            errors_recovered += 1
            reading = self._fallback_reading(topic, approved_packets)

        # Step 2: Compress to presentation mode
        try:
            presentation = await self._generate_presentation_mode(
                reading=reading,
                evidence_bundle=evidence_bundle,
                style=style,
            )
            models_used.append("presentation_gen")
        except Exception as e:
            logger.error("Presentation mode generation failed: %s", e)
            errors_recovered += 1
            presentation = self._fallback_presentation(reading, style)

        # Step 3-5: Run in parallel for speed
        notes_task = self._generate_speaker_notes(presentation, reading, style)
        chart_task = self._generate_chart_data(evidence_bundle, evidence_bundle.slide_kind)
        image_task = self._generate_image_prompt(
            evidence_bundle.slide_kind, presentation.title, topic, style,
        )

        notes_result, chart_result, image_result = await asyncio.gather(
            notes_task, chart_task, image_task,
            return_exceptions=True,
        )

        # Handle results
        if isinstance(notes_result, Exception):
            logger.error("Speaker notes failed: %s", notes_result)
            errors_recovered += 1
            speaker_notes: list[str] = [f"Key point: {presentation.title}"]
        else:
            speaker_notes = notes_result

        if isinstance(chart_result, Exception):
            logger.error("Chart data failed: %s", chart_result)
            errors_recovered += 1
            chart_data: Optional[dict] = None
        else:
            chart_data = chart_result

        if isinstance(image_result, Exception):
            logger.error("Image prompt failed: %s", image_result)
            errors_recovered += 1
            image_prompt: Optional[str] = None
        else:
            image_prompt = image_result

        # Step 6: Build citations
        citations = self._build_citations(evidence_bundle)

        # Step 7: Assemble contract
        total_latency = (time.monotonic() - start_time) * 1000
        metadata = self._build_metadata(
            evidence_bundle=evidence_bundle,
            style=style,
            budget_mode=budget_mode,
            models_used=models_used,
            total_tokens=total_tokens,
            total_latency_ms=total_latency,
            errors_recovered=errors_recovered,
        )

        contract = SlideContentContract(
            slide_id=evidence_bundle.slide_id,
            slide_kind=evidence_bundle.slide_kind,
            style_id=style.style_id,
            presentation_content=presentation,
            reading_content=reading,
            speaker_notes=speaker_notes,
            chart_data=chart_data,
            image_prompt=image_prompt,
            citations=citations,
            evidence_score=evidence_bundle.evidence_score,
            generation_metadata=metadata,
        )

        # Step 8: Citation verification
        passed, issues = self._guard.verify_contract(
            contract, evidence_bundle.evidence_packets,
        )
        if not passed:
            logger.warning(
                "Citation guard flagged %d issues for slide %s: %s",
                len(issues),
                evidence_bundle.slide_id,
                issues[:3],
            )

        return contract

    async def _generate_reading_mode(
        self,
        evidence_bundle: SlideEvidenceBundle,
        style: StyleProfile,
        topic: str,
        audience: str,
    ) -> ReadingContent:
        """Generate reading mode content using the ModeTransformer."""
        evidence_text = self._format_evidence_for_prompt(evidence_bundle)
        return await self._transformer.generate_reading_content(
            evidence_text=evidence_text,
            style=style,
            slide_kind=evidence_bundle.slide_kind.value,
            topic=topic,
            audience=audience,
        )

    async def _generate_presentation_mode(
        self,
        reading: ReadingContent,
        evidence_bundle: SlideEvidenceBundle,
        style: StyleProfile,
    ) -> PresentationContent:
        """Compress reading mode to presentation using ModeTransformer."""
        evidence_summary = self._format_evidence_summary(evidence_bundle)
        return await self._transformer.reading_to_presentation(
            reading=reading,
            style=style,
            evidence_summary=evidence_summary,
        )

    async def _generate_speaker_notes(
        self,
        presentation: PresentationContent,
        reading: ReadingContent,
        style: StyleProfile,
    ) -> list[str]:
        """Generate speaker notes from both modes."""
        return await self._transformer.generate_speaker_notes(
            presentation=presentation,
            reading=reading,
            style=style,
        )

    async def _generate_chart_data(
        self,
        evidence_bundle: SlideEvidenceBundle,
        slide_kind: SlideKind,
    ) -> Optional[dict]:
        """Generate chart data from evidence FactPackets. Only for chart-appropriate slides."""
        if slide_kind not in _CHART_SLIDE_KINDS:
            return None

        # Collect numeric packets
        numeric_packets = [
            fp for fp in evidence_bundle.evidence_packets
            if fp.numeric_value is not None
        ]
        if len(numeric_packets) < 2:
            return None

        # Select chart type based on slide kind
        chart_type_map = {
            SlideKind.traction: "line",
            SlideKind.financial: "bar",
            SlideKind.market: "pie",
            SlideKind.competition: "bar",
        }
        chart_type = chart_type_map.get(slide_kind, "bar")

        return self._chart_synth.synthesize(
            packets=numeric_packets,
            chart_type=chart_type,
            slide_kind=slide_kind,
        )

    async def _generate_image_prompt(
        self,
        slide_kind: SlideKind,
        title: str,
        topic: str,
        style: StyleProfile,
    ) -> Optional[str]:
        """Generate Azure Flux image prompt for appropriate slides."""
        if slide_kind not in _IMAGE_SLIDE_KINDS:
            return None
        return self._image_gen.generate(
            slide_kind=slide_kind,
            title=title,
            topic=topic,
            style=style,
        )

    def _build_citations(
        self, evidence_bundle: SlideEvidenceBundle,
    ) -> list[Citation]:
        """Build citation objects from evidence packets."""
        citations: list[Citation] = []
        seen_sources: set[str] = set()

        for i, fp in enumerate(evidence_bundle.evidence_packets):
            source_key = f"{fp.source_name}:{fp.source_url or ''}"
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)

            label = fp.citation_label or f"[{i + 1}]"
            citations.append(Citation(
                label=label,
                source_name=fp.source_name,
                source_url=fp.source_url,
                date=fp.date_published,
                claim_type=fp.claim_type,
                confidence=fp.confidence,
            ))

        return citations

    def _build_metadata(
        self,
        evidence_bundle: SlideEvidenceBundle,
        style: StyleProfile,
        budget_mode: BudgetMode,
        models_used: list[str],
        total_tokens: int,
        total_latency_ms: float,
        errors_recovered: int,
    ) -> GenerationMetadata:
        """Build generation metadata."""
        providers_queried = set()
        for fp in evidence_bundle.evidence_packets:
            providers_queried.add(fp.provider)

        return GenerationMetadata(
            total_providers_queried=len(providers_queried),
            total_fact_packets=len(evidence_bundle.evidence_packets),
            approved_claims=len(evidence_bundle.approved_claim_ids),
            rejected_claims=len(evidence_bundle.rejected_claims),
            evidence_score=evidence_bundle.evidence_score,
            models_used=models_used,
            total_tokens=total_tokens,
            total_latency_ms=total_latency_ms,
            budget_mode=budget_mode,
            style_applied=style.style_id,
            errors_recovered=errors_recovered,
        )

    def _filter_approved(
        self, evidence_bundle: SlideEvidenceBundle,
    ) -> list[FactPacket]:
        """Return only debate-approved FactPackets."""
        if not evidence_bundle.approved_claim_ids:
            return evidence_bundle.evidence_packets
        approved_set = set(evidence_bundle.approved_claim_ids)
        return [
            fp for fp in evidence_bundle.evidence_packets
            if fp.id in approved_set
        ]

    def _format_evidence_for_prompt(
        self, evidence: SlideEvidenceBundle,
    ) -> str:
        """Format evidence bundle for LLM prompts."""
        approved = self._filter_approved(evidence)
        if not approved:
            return "No approved evidence available."

        lines: list[str] = []
        for fp in approved:
            parts = [f"[{fp.id}] {fp.claim}"]
            parts.append(f"  Source: {fp.source_name}")
            parts.append(f"  Type: {fp.claim_type.value}")
            parts.append(f"  Confidence: {fp.confidence:.2f}")
            if fp.numeric_value is not None:
                unit = fp.numeric_unit or ""
                parts.append(f"  Value: {fp.numeric_value} {unit}")
            if fp.date_published:
                parts.append(f"  Date: {fp.date_published}")
            if fp.cross_validated:
                parts.append(
                    f"  Cross-validated by: {', '.join(fp.cross_validation_sources)}"
                )
            lines.append("\n".join(parts))

        header = f"=== Evidence for {evidence.slide_kind.value} slide ==="
        header += f"\nTotal packets: {len(approved)}"
        header += f"\nEvidence score: {evidence.evidence_score:.2f}"
        return header + "\n\n" + "\n\n".join(lines)

    def _format_evidence_summary(
        self, evidence: SlideEvidenceBundle,
    ) -> str:
        """Short evidence summary for presentation compression."""
        approved = self._filter_approved(evidence)
        lines: list[str] = []
        for fp in approved[:10]:
            line = f"- {fp.claim}"
            if fp.numeric_value is not None:
                line += f" ({fp.numeric_value} {fp.numeric_unit or ''})"
            lines.append(line)
        return "\n".join(lines)

    def _fallback_reading(
        self,
        topic: str,
        packets: list[FactPacket],
    ) -> ReadingContent:
        """Deterministic fallback when LLM reading generation fails."""
        paragraphs: list[str] = []
        source_refs: list[str] = []
        for fp in packets[:5]:
            paragraphs.append(f"{fp.claim} [{fp.source_name}].")
            if fp.source_name not in source_refs:
                source_refs.append(fp.source_name)

        return ReadingContent(
            title=topic,
            summary=f"Evidence-based analysis of {topic}.",
            body_sections=[
                BodySection(
                    heading="Key Findings",
                    paragraphs=paragraphs or ["No approved evidence available."],
                    source_refs=source_refs,
                ),
            ],
            assumptions=["Based on available evidence at time of generation."],
            risks=["Evidence may be incomplete."],
        )

    def _fallback_presentation(
        self,
        reading: ReadingContent,
        style: StyleProfile,
    ) -> PresentationContent:
        """Deterministic fallback when LLM presentation compression fails."""
        return self._transformer._fallback_compress(reading, style)
