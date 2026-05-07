"""
Input V4 Adapter — Bridges GenerationInputV4 to the legacy GenerationInput.

This adapter ensures backward compatibility with the existing orchestrator
while we incrementally upgrade the pipeline. The orchestrator reads
GenerationInput; this module translates V4 inputs to that format.

The adapter also injects analysis context into additional_notes so that
the existing outline and content generation prompts benefit from the
extracted entities and inferred context.
"""

from typing import Optional

from app.models.generation_input_v4 import (
    GenerationInputV4,
    InputAnalysisResult,
    PresentationPurpose,
    WritingStyle,
)
from app.models.presentation import GenerationInput, PresentationMode


# Map V4 purposes to legacy purpose strings
PURPOSE_MAP: dict[PresentationPurpose, str] = {
    PresentationPurpose.PITCH_DECK: "pitch",
    PresentationPurpose.INVESTOR_UPDATE: "investor_update",
    PresentationPurpose.SALES_DECK: "sales",
    PresentationPurpose.PRODUCT_LAUNCH: "pitch",
    PresentationPurpose.QUARTERLY_REVIEW: "report",
    PresentationPurpose.BOARD_MEETING: "report",
    PresentationPurpose.CONFERENCE_TALK: "educational",
    PresentationPurpose.TRAINING: "educational",
    PresentationPurpose.PROJECT_PROPOSAL: "pitch",
    PresentationPurpose.CASE_STUDY: "report",
    PresentationPurpose.COMPANY_OVERVIEW: "pitch",
    PresentationPurpose.DEMO_DAY: "demo_day",
    PresentationPurpose.EDUCATIONAL: "educational",
    PresentationPurpose.INTERNAL_MEMO: "internal",
    PresentationPurpose.CUSTOM: "pitch",
}

# Map V4 writing styles to legacy style strings
STYLE_MAP: dict[WritingStyle, str] = {
    WritingStyle.YC_CRISP: "yc_pitch",
    WritingStyle.NARRATIVE: "narrative",
    WritingStyle.EXECUTIVE: "executive",
    WritingStyle.PERSUASIVE: "persuasive",
    WritingStyle.ANALYTICAL: "analytical",
    WritingStyle.CONVERSATIONAL: "conversational",
    WritingStyle.TECHNICAL: "technical",
    WritingStyle.ACADEMIC: "academic",
    WritingStyle.MINIMALIST: "minimalist",
    WritingStyle.STORYTELLING: "storytelling",
}


class InputV4Adapter:
    """Converts GenerationInputV4 → GenerationInput for the existing pipeline."""

    @staticmethod
    def to_legacy(
        v4: GenerationInputV4,
        analysis: Optional[InputAnalysisResult] = None,
    ) -> GenerationInput:
        """
        Convert V4 input to legacy format.

        Injects analysis context (extracted entities, detected industry, etc.)
        into additional_notes so the existing prompt engine benefits from
        the richer understanding without needing to be rewritten yet.
        """
        # ── Extract core fields from whichever variant is active ──
        if v4.standard_input:
            return InputV4Adapter._from_standard(v4.standard_input, analysis)
        elif v4.premium_structured_input:
            return InputV4Adapter._from_structured(v4.premium_structured_input, analysis)
        elif v4.premium_prompt_input:
            return InputV4Adapter._from_prompt(v4.premium_prompt_input, analysis)

        # Should not reach here due to model validation
        raise ValueError("No valid input variant found in GenerationInputV4")

    @staticmethod
    def _from_standard(
        inp,
        analysis: Optional[InputAnalysisResult],
    ) -> GenerationInput:
        """Convert StandardGenerationInput → GenerationInput."""
        purpose = PURPOSE_MAP.get(inp.purpose, "pitch")
        style = STYLE_MAP.get(inp.writing_style, "yc_pitch")

        # Build enhanced notes from analysis
        notes = _build_analysis_context(analysis)

        return GenerationInput(
            topic=inp.prompt[:500],
            description=inp.prompt,
            audience=inp.audience or (analysis.detected_audience if analysis else "General audience"),
            purpose=purpose,
            slide_count=inp.slide_count or (analysis.suggested_slide_count if analysis else 10),
            language=inp.language,
            additional_notes=notes or None,
            mode=PresentationMode.STANDARD,
            writing_style=style,
            theme_id=inp.theme_id,
            generate_images=inp.generate_images,
            generate_notes=inp.generate_notes,
        )

    @staticmethod
    def _from_structured(
        inp,
        analysis: Optional[InputAnalysisResult],
    ) -> GenerationInput:
        """Convert PremiumStructuredInput → GenerationInput with enriched context."""
        purpose = PURPOSE_MAP.get(inp.purpose, "pitch")
        style = STYLE_MAP.get(inp.writing_style, "yc_pitch")

        # Build rich context from structured data
        context_parts: list[str] = []

        if inp.company:
            parts = [f"Company: {inp.company.name}"]
            if inp.company.tagline:
                parts.append(f"Tagline: {inp.company.tagline}")
            if inp.company.industry:
                parts.append(f"Industry: {inp.company.industry}")
            if inp.company.stage:
                parts.append(f"Stage: {inp.company.stage.value}")
            if inp.company.team_size:
                parts.append(f"Team size: {inp.company.team_size}")
            context_parts.append("\n".join(parts))

        if inp.financials:
            metrics = []
            if inp.financials.arr is not None:
                metrics.append(f"ARR: ${inp.financials.arr:,.0f}")
            if inp.financials.mrr is not None:
                metrics.append(f"MRR: ${inp.financials.mrr:,.0f}")
            if inp.financials.revenue_growth_pct is not None:
                metrics.append(f"Revenue growth: {inp.financials.revenue_growth_pct}%")
            if inp.financials.customers_count is not None:
                metrics.append(f"Customers: {inp.financials.customers_count}")
            if inp.financials.users_count is not None:
                metrics.append(f"Users: {inp.financials.users_count:,}")
            if inp.financials.cac is not None:
                metrics.append(f"CAC: ${inp.financials.cac:,.0f}")
            if inp.financials.ltv is not None:
                metrics.append(f"LTV: ${inp.financials.ltv:,.0f}")
            if inp.financials.gross_margin_pct is not None:
                metrics.append(f"Gross margin: {inp.financials.gross_margin_pct}%")
            if inp.financials.burn_rate is not None:
                metrics.append(f"Monthly burn: ${inp.financials.burn_rate:,.0f}")
            if inp.financials.runway_months is not None:
                metrics.append(f"Runway: {inp.financials.runway_months} months")
            if metrics:
                context_parts.append("Financial metrics:\n" + "\n".join(f"  - {m}" for m in metrics))

        if inp.competitors:
            comp_lines = []
            for c in inp.competitors:
                line = f"  - {c.name}"
                if c.differentiator:
                    line += f" (our differentiator: {c.differentiator})"
                comp_lines.append(line)
            context_parts.append("Competitors:\n" + "\n".join(comp_lines))

        if inp.traction:
            trac_parts = []
            if inp.traction.key_milestones:
                trac_parts.append("Milestones: " + "; ".join(inp.traction.key_milestones[:5]))
            if inp.traction.notable_customers:
                trac_parts.append("Notable customers: " + ", ".join(inp.traction.notable_customers[:10]))
            if inp.traction.partnerships:
                trac_parts.append("Partnerships: " + ", ".join(inp.traction.partnerships[:5]))
            if trac_parts:
                context_parts.append("Traction:\n" + "\n".join(f"  - {t}" for t in trac_parts))

        if inp.team:
            team_lines = []
            for m in inp.team[:5]:
                line = f"  - {m.name}, {m.role}"
                if m.notable_credentials:
                    line += f" ({', '.join(m.notable_credentials[:2])})"
                team_lines.append(line)
            context_parts.append("Team:\n" + "\n".join(team_lines))

        if inp.fundraising:
            ask_parts = []
            if inp.fundraising.amount is not None:
                ask_parts.append(f"Raising: ${inp.fundraising.amount:,.0f}")
            if inp.fundraising.round_type:
                ask_parts.append(f"Round: {inp.fundraising.round_type}")
            if inp.fundraising.use_of_funds:
                ask_parts.append("Use of funds: " + "; ".join(inp.fundraising.use_of_funds[:5]))
            if ask_parts:
                context_parts.append("Fundraising:\n" + "\n".join(f"  - {a}" for a in ask_parts))

        if inp.market:
            mkt_parts = []
            if inp.market.tam:
                mkt_parts.append(f"TAM: {inp.market.tam}")
            if inp.market.sam:
                mkt_parts.append(f"SAM: {inp.market.sam}")
            if inp.market.som:
                mkt_parts.append(f"SOM: {inp.market.som}")
            if inp.market.target_segment:
                mkt_parts.append(f"Target segment: {inp.market.target_segment}")
            if mkt_parts:
                context_parts.append("Market:\n" + "\n".join(f"  - {m}" for m in mkt_parts))

        # Content directives
        if inp.content_directives:
            dir_parts = []
            if inp.content_directives.key_messages:
                dir_parts.append("Key messages: " + "; ".join(inp.content_directives.key_messages))
            if inp.content_directives.emphasis:
                dir_parts.append("Emphasize: " + ", ".join(inp.content_directives.emphasis))
            if inp.content_directives.tone_keywords:
                dir_parts.append("Tone: " + ", ".join(inp.content_directives.tone_keywords))
            if dir_parts:
                context_parts.append("Content directives:\n" + "\n".join(f"  - {d}" for d in dir_parts))

        notes = "\n\n".join(context_parts) if context_parts else None

        # Add analysis context
        analysis_ctx = _build_analysis_context(analysis)
        if analysis_ctx and notes:
            notes = notes + "\n\n" + analysis_ctx
        elif analysis_ctx:
            notes = analysis_ctx

        return GenerationInput(
            topic=inp.topic,
            description=inp.description,
            audience=inp.audience,
            purpose=purpose,
            slide_count=inp.slide_count or (analysis.suggested_slide_count if analysis else 12),
            language=inp.language,
            additional_notes=notes[:3000] if notes else None,
            mode=PresentationMode.PREMIUM,
            writing_style=style,
            theme_id=inp.theme_id,
            generate_images=inp.generate_images,
            generate_notes=inp.generate_notes,
        )

    @staticmethod
    def _from_prompt(
        inp,
        analysis: Optional[InputAnalysisResult],
    ) -> GenerationInput:
        """Convert PremiumPromptInput → GenerationInput with extracted context."""
        purpose = PURPOSE_MAP.get(inp.purpose, "pitch")
        style = STYLE_MAP.get(inp.writing_style, "yc_pitch")

        # For prompt mode, the analysis context is critical
        notes = _build_analysis_context(analysis)

        # Add content directives if present
        if inp.content_directives:
            dir_parts = []
            if inp.content_directives.key_messages:
                dir_parts.append("Key messages: " + "; ".join(inp.content_directives.key_messages))
            if inp.content_directives.emphasis:
                dir_parts.append("Emphasize: " + ", ".join(inp.content_directives.emphasis))
            if inp.content_directives.exclude_slides:
                dir_parts.append("Exclude: " + ", ".join(inp.content_directives.exclude_slides))
            if dir_parts:
                directive_text = "\nContent directives:\n" + "\n".join(f"  - {d}" for d in dir_parts)
                notes = (notes + directive_text) if notes else directive_text

        # Detect topic and audience from analysis
        topic = inp.prompt[:500]
        if analysis and analysis.detected_company_name:
            topic = analysis.detected_company_name

        audience = "Investors"
        if analysis:
            audience = analysis.detected_audience

        return GenerationInput(
            topic=topic,
            description=inp.prompt,
            audience=audience,
            purpose=purpose,
            slide_count=inp.slide_count or (analysis.suggested_slide_count if analysis else 10),
            language=inp.language,
            additional_notes=notes[:3000] if notes else None,
            mode=PresentationMode.PREMIUM,
            writing_style=style,
            generate_images=inp.generate_images,
            generate_notes=inp.generate_notes,
        )


def _build_analysis_context(analysis: Optional[InputAnalysisResult]) -> Optional[str]:
    """Build an enriched context string from the input analysis."""
    if not analysis:
        return None

    parts: list[str] = []

    # Detected context
    ctx_parts = []
    if analysis.detected_industry:
        ctx_parts.append(f"Industry: {analysis.detected_industry}")
    if analysis.detected_company_name:
        ctx_parts.append(f"Company: {analysis.detected_company_name}")
    if analysis.detected_stage:
        ctx_parts.append(f"Stage: {analysis.detected_stage.value}")
    if analysis.audience_sophistication:
        ctx_parts.append(f"Audience sophistication: {analysis.audience_sophistication.value}")
    if ctx_parts:
        parts.append("[AI-detected context]\n" + "\n".join(ctx_parts))

    # Extracted entities
    if analysis.entities:
        entity_lines = []
        for e in analysis.entities[:15]:
            entity_lines.append(f"  - [{e.type}] {e.value}")
        if entity_lines:
            parts.append("[Extracted entities]\n" + "\n".join(entity_lines))

    # Narrative arc suggestion
    if analysis.suggested_narrative_arc:
        parts.append(f"[Suggested narrative arc] {analysis.suggested_narrative_arc}")

    # Slide composition suggestion
    if analysis.suggested_slide_types:
        parts.append("[Suggested slide order]\n" + ", ".join(analysis.suggested_slide_types))

    return "\n\n".join(parts) if parts else None
