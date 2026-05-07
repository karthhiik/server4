"""
Input Analyzer — AI-powered input understanding service.

This is the FIRST thing that runs when a user submits input.
It transforms raw user input into a rich, structured understanding
that the Strategist can use to plan the deck.

Innovation:
  - Uses fast Groq models for < 2s analysis
  - Extracts entities (company, metrics, competitors) from raw text
  - Detects missing critical context and generates clarification suggestions
  - Infers purpose, audience, industry from minimal input
  - Suggests narrative arc and slide composition
  - Scores input richness to determine how much the AI needs to fill in

Pipeline:
  User Input → InputAnalyzer → InputAnalysisResult → Strategist
"""

import json
from typing import Optional

import structlog

from app.models.generation_input_v4 import (
    AudienceSophistication,
    ContentDirective,
    ExtractedEntity,
    FundingStage,
    GenerationInputV4,
    InputAnalysisResult,
    InputMethod,
    MissingContext,
    PresentationPurpose,
    PremiumPromptInput,
    PremiumStructuredInput,
    StandardGenerationInput,
    WritingStyle,
)
from app.services.llm import ModelRouter, TaskType

logger = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════

INPUT_ANALYSIS_SYSTEM_PROMPT = """\
You are an expert presentation analyst. Given a user's input about a presentation \
they want to create, you MUST analyze it and produce a structured JSON response.

Your job:
1. DETECT the presentation purpose (pitch_deck, sales_deck, conference_talk, etc.)
2. DETECT the target audience and their sophistication level
3. EXTRACT all entities: company names, financial metrics, competitor names, team members, technologies
4. INFER the industry and company stage from context clues
5. SUGGEST the best narrative arc for this presentation
6. SUGGEST which slide types should be included and in what order
7. IDENTIFY what critical information is MISSING from the input
8. SCORE the input richness (how much detail the user provided)

Respond ONLY with valid JSON matching this schema:
{
  "detected_purpose": "pitch_deck|investor_update|sales_deck|product_launch|quarterly_review|board_meeting|conference_talk|training|project_proposal|case_study|company_overview|demo_day|educational|internal_memo|custom",
  "detected_audience": "string describing the audience",
  "audience_sophistication": "general|business|investor|technical|executive|mixed",
  "detected_industry": "string or null",
  "detected_company_name": "string or null",
  "detected_stage": "pre_seed|seed|series_a|series_b|series_c_plus|bootstrapped|public|n/a|null",
  "entities": [
    {"type": "company|metric|competitor|person|technology|market|product", "value": "string", "confidence": 0.0-1.0}
  ],
  "suggested_narrative_arc": "problem_solution|vision_roadmap|data_story|case_study|demo_walkthrough|status_update|educational_flow",
  "suggested_slide_count": 10,
  "suggested_slide_types": ["title", "problem", "solution", "market", "traction", "team", "ask"],
  "missing_context": [
    {"field": "string", "importance": "critical|recommended|optional", "suggestion": "friendly suggestion"}
  ],
  "input_richness_score": 0.0-1.0,
  "confidence": 0.0-1.0
}

Rules:
- Be SPECIFIC with entity extraction — exact numbers, exact names
- For pitch decks: traction, team, and financials are CRITICAL if missing
- For sales decks: product features and pricing are CRITICAL if missing
- Suggested slide types should follow the canonical structure for the detected purpose
- input_richness_score: 0.0 = just a topic, 0.5 = topic + some context, 1.0 = very detailed input with data
"""

# Purpose-specific slide type suggestions
CANONICAL_SLIDE_STRUCTURES: dict[str, list[str]] = {
    "pitch_deck": [
        "title", "problem", "solution", "how_it_works", "market",
        "traction", "business_model", "competition", "team",
        "financials", "ask", "closing",
    ],
    "investor_update": [
        "title", "highlights", "kpi_dashboard", "revenue",
        "product_updates", "customers", "challenges", "roadmap",
        "ask_help", "closing",
    ],
    "sales_deck": [
        "title", "pain_point", "solution_overview", "features",
        "demo", "social_proof", "pricing", "roi", "next_steps",
    ],
    "product_launch": [
        "title", "vision", "problem_context", "product_reveal",
        "feature_1", "feature_2", "feature_3", "demo",
        "availability", "closing",
    ],
    "conference_talk": [
        "title", "hook", "context", "insight_1", "insight_2",
        "insight_3", "demo_or_example", "takeaways", "qa",
    ],
    "quarterly_review": [
        "title", "executive_summary", "kpi_dashboard", "revenue",
        "customers", "product", "challenges", "next_quarter", "resources",
    ],
    "board_meeting": [
        "title", "executive_summary", "financials", "kpis",
        "strategic_updates", "risks", "decisions_needed", "closing",
    ],
    "training": [
        "title", "objectives", "agenda", "topic_1", "exercise_1",
        "topic_2", "exercise_2", "summary", "resources",
    ],
}

# Default slide structures for purposes not explicitly listed
DEFAULT_SLIDE_STRUCTURE = [
    "title", "overview", "main_point_1", "main_point_2",
    "main_point_3", "summary", "closing",
]


class InputAnalyzer:
    """
    Analyzes user input to produce a rich InputAnalysisResult.

    For Standard mode: parses the prompt to extract everything we can.
    For Premium Prompt: deeper extraction with more entity types.
    For Premium Structured: validates and enriches the structured data.
    """

    def __init__(self):
        self.router = ModelRouter.get_instance()

    async def analyze(self, input_data: GenerationInputV4) -> InputAnalysisResult:
        """
        Main entry point — dispatches to the appropriate analyzer.
        Returns InputAnalysisResult regardless of input method.
        """
        try:
            if input_data.mode == "standard" and input_data.standard_input:
                return await self._analyze_standard(input_data.standard_input)
            elif input_data.mode == "premium":
                if input_data.premium_prompt_input:
                    return await self._analyze_premium_prompt(input_data.premium_prompt_input)
                elif input_data.premium_structured_input:
                    return self._analyze_premium_structured(input_data.premium_structured_input)

            # Fallback
            return self._build_minimal_analysis(input_data)

        except Exception as e:
            logger.error("input_analysis_failed", error=str(e))
            return self._build_minimal_analysis(input_data)

    async def _analyze_standard(self, inp: StandardGenerationInput) -> InputAnalysisResult:
        """
        Standard mode: fast LLM analysis of the prompt.
        Uses Groq for speed (< 2s) or GPT-4o-mini as fallback.

        Standard mode is ALWAYS pitch_deck with Investors audience.
        The purpose and audience are hardcoded — the LLM only needs
        to extract entities, detect missing context, and score richness.
        """
        user_prompt = (
            f"Analyze this PITCH DECK request:\n\n"
            f"Prompt: {inp.prompt}\n"
            f"Purpose: pitch_deck (forced — this is standard mode, always pitch deck)\n"
            f"Audience: Investors\n"
            f"Slide count requested: {inp.slide_count or 'auto'}\n"
            f"Writing style: yc_crisp\n"
            f"\nFocus on extracting startup-related entities (company name, "
            f"financial metrics, competitors, team, traction, market data) and "
            f"identify what CRITICAL pitch deck context is MISSING from the prompt."
        )

        result = await self.router.complete(
            task_type=TaskType.INTENT_CLASSIFICATION,
            messages=[
                {"role": "system", "content": INPUT_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        analysis = self._parse_llm_analysis(
            result.content,
            PresentationPurpose.PITCH_DECK,
            inp.slide_count,
        )
        # Force pitch_deck purpose regardless of what the LLM detected
        analysis.detected_purpose = PresentationPurpose.PITCH_DECK
        analysis.detected_audience = "Investors"
        analysis.audience_sophistication = AudienceSophistication.INVESTOR
        return analysis

    async def _analyze_premium_prompt(self, inp: PremiumPromptInput) -> InputAnalysisResult:
        """
        Premium prompt mode: deeper analysis with more entity extraction.
        Uses a reasoning model for better understanding of complex prompts.
        """
        directive_text = ""
        if inp.content_directives:
            parts = []
            if inp.content_directives.include_slides:
                parts.append(f"Include slides: {', '.join(inp.content_directives.include_slides)}")
            if inp.content_directives.exclude_slides:
                parts.append(f"Exclude slides: {', '.join(inp.content_directives.exclude_slides)}")
            if inp.content_directives.emphasis:
                parts.append(f"Emphasize: {', '.join(inp.content_directives.emphasis)}")
            if inp.content_directives.key_messages:
                parts.append(f"Key messages: {'; '.join(inp.content_directives.key_messages)}")
            directive_text = "\n".join(parts)

        user_prompt = (
            f"Analyze this PREMIUM presentation request in detail:\n\n"
            f"Prompt: {inp.prompt}\n"
            f"Stated purpose: {inp.purpose.value}\n"
            f"Slide count: {inp.slide_count or 'auto'}\n"
            f"Writing style: {inp.writing_style.value}\n"
        )
        if directive_text:
            user_prompt += f"\nContent directives:\n{directive_text}\n"

        user_prompt += (
            "\nExtract ALL entities: company names, financial metrics (exact numbers), "
            "competitor names, team member names, technologies, market data. "
            "Be thorough — this is premium mode."
        )

        result = await self.router.complete(
            task_type=TaskType.ENTITY_EXTRACTION,
            messages=[
                {"role": "system", "content": INPUT_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        return self._parse_llm_analysis(result.content, inp.purpose, inp.slide_count)

    def _analyze_premium_structured(self, inp: PremiumStructuredInput) -> InputAnalysisResult:
        """
        Premium structured mode: no LLM needed — we already have structured data.
        We validate completeness and identify gaps.
        """
        entities: list[ExtractedEntity] = []
        missing: list[MissingContext] = []

        # Extract entities from structured fields
        if inp.company:
            entities.append(ExtractedEntity(type="company", value=inp.company.name, confidence=1.0))
            if inp.company.industry:
                entities.append(ExtractedEntity(type="industry", value=inp.company.industry, confidence=1.0))

        if inp.financials:
            if inp.financials.arr is not None:
                entities.append(ExtractedEntity(type="metric", value=f"ARR: ${inp.financials.arr:,.0f}", confidence=1.0))
            if inp.financials.mrr is not None:
                entities.append(ExtractedEntity(type="metric", value=f"MRR: ${inp.financials.mrr:,.0f}", confidence=1.0))
            if inp.financials.customers_count is not None:
                entities.append(ExtractedEntity(type="metric", value=f"{inp.financials.customers_count} customers", confidence=1.0))

        if inp.competitors:
            for comp in inp.competitors:
                entities.append(ExtractedEntity(type="competitor", value=comp.name, confidence=1.0))

        if inp.team:
            for member in inp.team:
                entities.append(ExtractedEntity(type="person", value=f"{member.name} ({member.role})", confidence=1.0))

        # Detect missing context based on purpose
        is_investor = inp.purpose in (
            PresentationPurpose.PITCH_DECK,
            PresentationPurpose.INVESTOR_UPDATE,
            PresentationPurpose.DEMO_DAY,
        )

        if is_investor:
            if not inp.financials:
                missing.append(MissingContext(
                    field="financials",
                    importance="critical",
                    suggestion="Investors expect key metrics — ARR, MRR, growth rate. Add financial data for a stronger deck."
                ))
            if not inp.traction:
                missing.append(MissingContext(
                    field="traction",
                    importance="critical",
                    suggestion="Show momentum — customers, milestones, partnerships. Traction is what investors look for first."
                ))
            if not inp.team:
                missing.append(MissingContext(
                    field="team",
                    importance="recommended",
                    suggestion="Investors invest in people. Adding your team strengthens credibility."
                ))
            if not inp.fundraising:
                missing.append(MissingContext(
                    field="fundraising",
                    importance="recommended",
                    suggestion="Specify your ask — how much, what round, use of funds."
                ))
            if not inp.market:
                missing.append(MissingContext(
                    field="market",
                    importance="recommended",
                    suggestion="Market sizing (TAM/SAM/SOM) shows investors the opportunity scale."
                ))
            if not inp.competitors:
                missing.append(MissingContext(
                    field="competitors",
                    importance="optional",
                    suggestion="Showing competitive awareness signals market understanding."
                ))

        # Calculate richness score
        filled_blocks = sum(1 for x in [
            inp.company, inp.financials, inp.competitors,
            inp.traction, inp.team, inp.fundraising, inp.market
        ] if x)
        richness = min(1.0, 0.3 + (filled_blocks / 7) * 0.7)

        # Determine slide types from structured data
        purpose_key = inp.purpose.value
        canonical = CANONICAL_SLIDE_STRUCTURES.get(purpose_key, DEFAULT_SLIDE_STRUCTURE)

        # Determine audience sophistication
        aud_soph = inp.audience_sophistication

        # Determine stage
        stage = inp.company.stage if inp.company else FundingStage.NOT_APPLICABLE

        return InputAnalysisResult(
            detected_purpose=inp.purpose,
            detected_audience=inp.audience,
            audience_sophistication=aud_soph,
            detected_industry=inp.company.industry if inp.company else None,
            detected_company_name=inp.company.name if inp.company else None,
            detected_stage=stage,
            entities=entities,
            suggested_narrative_arc="problem_solution" if is_investor else "data_story",
            suggested_slide_count=inp.slide_count or len(canonical),
            suggested_slide_types=canonical,
            missing_context=missing,
            input_richness_score=richness,
            confidence=0.95,  # High confidence since data is structured
        )

    def _parse_llm_analysis(
        self,
        raw_content: str,
        fallback_purpose: PresentationPurpose,
        fallback_slide_count: Optional[int],
    ) -> InputAnalysisResult:
        """Parse LLM JSON response into InputAnalysisResult with robust fallbacks."""
        try:
            # Clean the response — strip markdown code fences if present
            clean = raw_content.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()

            data = json.loads(clean)

            # Parse entities
            entities = []
            for e in data.get("entities", []):
                try:
                    entities.append(ExtractedEntity(
                        type=e.get("type", "unknown"),
                        value=str(e.get("value", "")),
                        confidence=float(e.get("confidence", 0.7)),
                    ))
                except Exception:
                    continue

            # Parse missing context
            missing = []
            for m in data.get("missing_context", []):
                try:
                    importance = m.get("importance", "optional")
                    if importance not in ("critical", "recommended", "optional"):
                        importance = "optional"
                    missing.append(MissingContext(
                        field=m.get("field", "unknown"),
                        importance=importance,
                        suggestion=m.get("suggestion", ""),
                    ))
                except Exception:
                    continue

            # Map purpose string to enum
            purpose_str = data.get("detected_purpose", fallback_purpose.value)
            try:
                detected_purpose = PresentationPurpose(purpose_str)
            except ValueError:
                detected_purpose = fallback_purpose

            # Map audience sophistication
            aud_str = data.get("audience_sophistication", "business")
            try:
                aud_soph = AudienceSophistication(aud_str)
            except ValueError:
                aud_soph = AudienceSophistication.BUSINESS

            # Map stage
            stage_str = data.get("detected_stage")
            detected_stage = None
            if stage_str:
                try:
                    detected_stage = FundingStage(stage_str)
                except ValueError:
                    detected_stage = None

            # Suggested slide types
            suggested_types = data.get("suggested_slide_types", [])
            if not suggested_types:
                suggested_types = CANONICAL_SLIDE_STRUCTURES.get(
                    detected_purpose.value, DEFAULT_SLIDE_STRUCTURE
                )

            return InputAnalysisResult(
                detected_purpose=detected_purpose,
                detected_audience=data.get("detected_audience", "General audience"),
                audience_sophistication=aud_soph,
                detected_industry=data.get("detected_industry"),
                detected_company_name=data.get("detected_company_name"),
                detected_stage=detected_stage,
                entities=entities,
                suggested_narrative_arc=data.get("suggested_narrative_arc", "problem_solution"),
                suggested_slide_count=data.get("suggested_slide_count", fallback_slide_count or 10),
                suggested_slide_types=suggested_types,
                missing_context=missing,
                input_richness_score=float(data.get("input_richness_score", 0.5)),
                confidence=float(data.get("confidence", 0.7)),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("llm_analysis_parse_failed", error=str(e), raw=raw_content[:200])
            return self._build_fallback_analysis(fallback_purpose, fallback_slide_count)

    def _build_minimal_analysis(self, input_data: GenerationInputV4) -> InputAnalysisResult:
        """Build a minimal analysis from the input data without LLM."""
        purpose = input_data.effective_purpose
        canonical = CANONICAL_SLIDE_STRUCTURES.get(purpose.value, DEFAULT_SLIDE_STRUCTURE)

        return InputAnalysisResult(
            detected_purpose=purpose,
            detected_audience="General audience",
            audience_sophistication=AudienceSophistication.BUSINESS,
            suggested_slide_count=input_data.effective_slide_count or len(canonical),
            suggested_slide_types=canonical,
            input_richness_score=0.3,
            confidence=0.4,
        )

    def _build_fallback_analysis(
        self,
        purpose: PresentationPurpose,
        slide_count: Optional[int],
    ) -> InputAnalysisResult:
        """Fallback when LLM parsing fails."""
        canonical = CANONICAL_SLIDE_STRUCTURES.get(purpose.value, DEFAULT_SLIDE_STRUCTURE)
        return InputAnalysisResult(
            detected_purpose=purpose,
            detected_audience="General audience",
            audience_sophistication=AudienceSophistication.BUSINESS,
            suggested_slide_count=slide_count or len(canonical),
            suggested_slide_types=canonical,
            input_richness_score=0.3,
            confidence=0.3,
        )
