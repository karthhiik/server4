"""
Generation Input V4 — Intelligent Input Pipeline.

Two input modes for Premium:
  1. Structured Input: Field-by-field company data, financials, competitors, etc.
  2. Prompt Input:     Raw text that the AI parses into structured data.

Standard mode uses a streamlined prompt-first interface with smart defaults.

Innovation:
  - Intent classification (pitch / report / sales / educational)
  - Entity extraction from raw prompts (company name, metrics, competitors)
  - Audience profiling (investor sophistication, technical depth)
  - Narrative arc suggestion based on purpose + audience
  - Missing-context detection ("You didn't mention traction — should we include it?")
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════

class PresentationPurpose(str, Enum):
    """Exhaustive purpose taxonomy — each maps to a narrative framework."""
    PITCH_DECK = "pitch_deck"
    INVESTOR_UPDATE = "investor_update"
    SALES_DECK = "sales_deck"
    PRODUCT_LAUNCH = "product_launch"
    QUARTERLY_REVIEW = "quarterly_review"
    BOARD_MEETING = "board_meeting"
    CONFERENCE_TALK = "conference_talk"
    TRAINING = "training"
    PROJECT_PROPOSAL = "project_proposal"
    CASE_STUDY = "case_study"
    COMPANY_OVERVIEW = "company_overview"
    DEMO_DAY = "demo_day"
    EDUCATIONAL = "educational"
    INTERNAL_MEMO = "internal_memo"
    CUSTOM = "custom"


class WritingStyle(str, Enum):
    """Voice/tone presets that flow through the entire generation pipeline."""
    YC_CRISP = "yc_crisp"             # Short, punchy, data-driven
    NARRATIVE = "narrative"            # Story-driven, longer prose
    EXECUTIVE = "executive"            # C-suite brevity, strategic
    PERSUASIVE = "persuasive"          # Sales-oriented, benefit-focused
    ANALYTICAL = "analytical"          # Data-heavy, evidence-first
    CONVERSATIONAL = "conversational"  # Friendly, approachable
    TECHNICAL = "technical"            # Deep technical detail
    ACADEMIC = "academic"              # Formal, citation-heavy
    MINIMALIST = "minimalist"          # Ultra-sparse, zen-like slides
    STORYTELLING = "storytelling"      # Long-arc narrative, emotional hooks


class InputMethod(str, Enum):
    """How the user provided their input."""
    PROMPT = "prompt"         # Raw text prompt (standard default)
    STRUCTURED = "structured" # Field-by-field form (premium option)
    HYBRID = "hybrid"         # Prompt + some structured fields
    FILE_UPLOAD = "file_upload"  # PDF/DOCX/PPTX parsed into structured data
    URL_IMPORT = "url_import"    # Website/article parsed


class FundingStage(str, Enum):
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C_PLUS = "series_c_plus"
    BOOTSTRAPPED = "bootstrapped"
    PUBLIC = "public"
    NOT_APPLICABLE = "n/a"


class AudienceSophistication(str, Enum):
    """Determines content depth and jargon level."""
    GENERAL = "general"          # Non-technical, everyday language
    BUSINESS = "business"        # Business-literate, understands KPIs
    INVESTOR = "investor"        # Knows unit economics, TAM/SAM/SOM, etc.
    TECHNICAL = "technical"      # Engineers, developers, deep tech
    EXECUTIVE = "executive"      # C-suite, board-level, strategic
    MIXED = "mixed"              # Diverse audience


# ═══════════════════════════════════════════════════════════════════
# PREMIUM STRUCTURED DATA BLOCKS
# ═══════════════════════════════════════════════════════════════════

class CompanyData(BaseModel):
    """Structured company info for Premium mode — investors expect precision."""
    name: str = Field(..., min_length=1, max_length=200, description="Company or project name")
    tagline: Optional[str] = Field(default=None, max_length=300, description="One-line value proposition")
    industry: Optional[str] = Field(default=None, max_length=100, description="e.g. FinTech, HealthTech, SaaS")
    founded_year: Optional[int] = Field(default=None, ge=1900, le=2030)
    location: Optional[str] = Field(default=None, max_length=200)
    website_url: Optional[str] = Field(default=None, max_length=500)
    stage: FundingStage = FundingStage.NOT_APPLICABLE
    team_size: Optional[int] = Field(default=None, ge=1, le=100000)
    logo_url: Optional[str] = Field(default=None, max_length=500, description="URL to logo image")


class FinancialData(BaseModel):
    """Key financial metrics — real numbers, not vague claims."""
    arr: Optional[float] = Field(default=None, ge=0, description="Annual Recurring Revenue (USD)")
    mrr: Optional[float] = Field(default=None, ge=0, description="Monthly Recurring Revenue (USD)")
    revenue_growth_pct: Optional[float] = Field(default=None, description="YoY or MoM revenue growth %")
    burn_rate: Optional[float] = Field(default=None, ge=0, description="Monthly burn rate (USD)")
    runway_months: Optional[int] = Field(default=None, ge=0, description="Remaining runway in months")
    gross_margin_pct: Optional[float] = Field(default=None, ge=-100, le=100)
    cac: Optional[float] = Field(default=None, ge=0, description="Customer Acquisition Cost (USD)")
    ltv: Optional[float] = Field(default=None, ge=0, description="Customer Lifetime Value (USD)")
    total_funding_raised: Optional[float] = Field(default=None, ge=0, description="Total capital raised (USD)")
    customers_count: Optional[int] = Field(default=None, ge=0, description="Number of paying customers")
    users_count: Optional[int] = Field(default=None, ge=0, description="Total registered users")
    custom_metrics: Optional[dict[str, Any]] = Field(default=None, description="Domain-specific KPIs")


class CompetitorEntry(BaseModel):
    """Structured competitor data for positioning slides."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    strengths: Optional[list[str]] = Field(default=None, max_length=5)
    weaknesses: Optional[list[str]] = Field(default=None, max_length=5)
    differentiator: Optional[str] = Field(default=None, max_length=300, description="How we differ from them")


class TractionData(BaseModel):
    """Evidence of product-market fit and momentum."""
    key_milestones: Optional[list[str]] = Field(default=None, max_length=10, description="Timeline milestones")
    notable_customers: Optional[list[str]] = Field(default=None, max_length=20, description="Customer names or logos")
    partnerships: Optional[list[str]] = Field(default=None, max_length=10)
    press_mentions: Optional[list[str]] = Field(default=None, max_length=10)
    awards: Optional[list[str]] = Field(default=None, max_length=10)
    growth_metrics: Optional[dict[str, Any]] = Field(default=None, description="Key growth data points")


class TeamMember(BaseModel):
    """Team member info for team slides."""
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    photo_url: Optional[str] = Field(default=None, max_length=500)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    notable_credentials: Optional[list[str]] = Field(default=None, max_length=5, description="e.g. 'Ex-Google', 'YC W21'")


class FundraisingAsk(BaseModel):
    """The ask slide data — specific, not vague."""
    amount: Optional[float] = Field(default=None, ge=0, description="Amount raising (USD)")
    round_type: Optional[str] = Field(default=None, max_length=50, description="e.g. Seed, Series A")
    use_of_funds: Optional[list[str]] = Field(default=None, max_length=8, description="How capital will be deployed")
    timeline: Optional[str] = Field(default=None, max_length=200, description="Funding timeline / close date")
    previous_investors: Optional[list[str]] = Field(default=None, max_length=10)
    valuation_cap: Optional[float] = Field(default=None, ge=0, description="Pre/post-money valuation cap")


class MarketData(BaseModel):
    """Market sizing and opportunity data."""
    tam: Optional[str] = Field(default=None, max_length=200, description="Total Addressable Market")
    sam: Optional[str] = Field(default=None, max_length=200, description="Serviceable Addressable Market")
    som: Optional[str] = Field(default=None, max_length=200, description="Serviceable Obtainable Market")
    market_growth_rate: Optional[str] = Field(default=None, max_length=100)
    target_segment: Optional[str] = Field(default=None, max_length=300)
    sources: Optional[list[str]] = Field(default=None, max_length=5, description="Data sources for market claims")


class BrandAssets(BaseModel):
    """User-provided brand customization.

    Every field is optional. When omitted, the generation pipeline falls back
    to an AI-chosen default derived from purpose, industry, and audience.
    Available for both Standard and Premium modes — treat as a lightweight
    design-profile payload rather than a premium-only brand kit.
    """
    # ── Palette ──
    primary_color: Optional[str] = Field(default=None, max_length=30, description="Hex color, e.g. #2563EB")
    secondary_color: Optional[str] = Field(default=None, max_length=30)
    accent_color: Optional[str] = Field(default=None, max_length=30)
    background_color: Optional[str] = Field(default=None, max_length=30)

    # ── Typography families ──
    font_heading: Optional[str] = Field(default=None, max_length=100, description="Google Font name or custom")
    font_body: Optional[str] = Field(default=None, max_length=100)

    # ── Typography scale & rhythm (all optional; AI picks if absent) ──
    font_size_scale: Optional[str] = Field(
        default=None,
        pattern="^(compact|comfortable|spacious)$",
        description="Overall type-size rhythm: compact | comfortable | spacious",
    )
    heading_weight: Optional[int] = Field(
        default=None, ge=100, le=900,
        description="Heading font weight (100-900, nearest-100 step)",
    )
    body_weight: Optional[int] = Field(
        default=None, ge=100, le=900,
        description="Body font weight (100-900, nearest-100 step)",
    )
    line_height_scale: Optional[float] = Field(
        default=None, ge=1.0, le=2.5,
        description="Base line-height multiplier applied to body text",
    )
    letter_spacing_em: Optional[float] = Field(
        default=None, ge=-0.1, le=0.3,
        description="Letter spacing in em (tracking)",
    )

    # ── Brand identity ──
    logo_url: Optional[str] = Field(default=None, max_length=500)
    brand_guidelines_text: Optional[str] = Field(default=None, max_length=2000, description="Free-text brand rules")


class ContentDirective(BaseModel):
    """User-driven content preferences for a specific slide or the whole deck."""
    include_slides: Optional[list[str]] = Field(
        default=None, max_length=30,
        description="Slide types to include, e.g. ['problem', 'solution', 'traction', 'team', 'ask']"
    )
    exclude_slides: Optional[list[str]] = Field(
        default=None, max_length=20,
        description="Slide types to exclude, e.g. ['competition']"
    )
    emphasis: Optional[list[str]] = Field(
        default=None, max_length=5,
        description="Areas to emphasize, e.g. ['traction', 'product_demo']"
    )
    tone_keywords: Optional[list[str]] = Field(
        default=None, max_length=10,
        description="Tone descriptors, e.g. ['confident', 'data-driven', 'visionary']"
    )
    key_messages: Optional[list[str]] = Field(
        default=None, max_length=10,
        description="Core messages that MUST appear in the deck"
    )
    avoid_topics: Optional[list[str]] = Field(
        default=None, max_length=10,
        description="Topics to deliberately avoid"
    )


# ═══════════════════════════════════════════════════════════════════
# MAIN INPUT MODELS
# ═══════════════════════════════════════════════════════════════════

class StandardGenerationInput(BaseModel):
    """
    Standard Mode Input — Pitch Deck Only, Prompt-first.

    The user provides ONLY a prompt describing their startup and optionally
    a slide count. The AI handles everything else: purpose is always
    PITCH_DECK, audience is always Investors, style is always YC_CRISP.

    A conversational Q&A flow (≤8 questions) may fire if the prompt is
    too thin (input_richness_score < 0.7), powered by the
    ConversationalQuestionGenerator service.
    """
    # ── Core (required) ──
    prompt: str = Field(
        ..., min_length=10, max_length=5000,
        description="Describe your startup. "
                    "e.g. 'AI hiring platform for SaaS companies, $2M ARR, raising Series A'"
    )

    # ── Slide count (optional — user can pick how many slides) ──
    slide_count: Optional[int] = Field(
        default=None, ge=1, le=50,
        description="Number of slides to generate. If None, auto-determined (typically 10-12 for pitch decks)."
    )

    # ── Language (optional — defaults to English) ──
    language: str = Field(default="English", max_length=50)

    # ── Hardcoded pitch-deck defaults (not exposed to the user) ──
    @property
    def purpose(self) -> "PresentationPurpose":
        """Standard mode is ALWAYS pitch_deck."""
        return PresentationPurpose.PITCH_DECK

    @property
    def audience(self) -> str:
        """Standard mode always targets investors."""
        return "Investors"

    @property
    def writing_style(self) -> "WritingStyle":
        """Standard mode always uses YC-crisp style."""
        return WritingStyle.YC_CRISP

    @property
    def theme_id(self) -> None:
        """Standard mode auto-selects theme."""
        return None

    @property
    def brand(self) -> None:
        """Standard mode does not accept brand assets."""
        return None

    @property
    def generate_images(self) -> bool:
        """Standard mode skips image generation for speed."""
        return False

    @property
    def generate_notes(self) -> bool:
        """Standard mode skips speaker notes for speed."""
        return False

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace")
        return v.strip()


class PremiumPromptInput(BaseModel):
    """
    Premium Mode — Prompt-Based Input.
    User writes a rich prompt; AI extracts structured data from it.
    The system asks clarifying questions if critical data is missing.
    """
    prompt: str = Field(
        ..., min_length=10, max_length=10000,
        description="Rich natural language prompt. Can include company details, "
                    "metrics, competitors, goals — AI will parse everything."
    )
    purpose: PresentationPurpose = Field(default=PresentationPurpose.PITCH_DECK)
    slide_count: Optional[int] = Field(default=None, ge=1, le=50)
    language: str = Field(default="English", max_length=50)
    writing_style: WritingStyle = Field(default=WritingStyle.YC_CRISP)
    content_directives: Optional[ContentDirective] = None
    brand: Optional[BrandAssets] = None
    theme_id: Optional[str] = None
    generate_images: bool = Field(default=True)
    generate_notes: bool = Field(default=True)

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace")
        return v.strip()


class PremiumStructuredInput(BaseModel):
    """
    Premium Mode — Structured Input.
    Field-by-field form for maximum precision and control.
    Every structured block feeds directly into specific slide types.
    """
    # ── Core (required) ──
    topic: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=10, max_length=10000)
    purpose: PresentationPurpose = Field(default=PresentationPurpose.PITCH_DECK)
    audience: str = Field(default="Investors", max_length=300)
    audience_sophistication: AudienceSophistication = Field(default=AudienceSophistication.INVESTOR)

    # ── Structured data blocks (optional — each enriches specific slides) ──
    company: Optional[CompanyData] = None
    financials: Optional[FinancialData] = None
    competitors: Optional[list[CompetitorEntry]] = Field(default=None, max_length=10)
    traction: Optional[TractionData] = None
    team: Optional[list[TeamMember]] = Field(default=None, max_length=20)
    fundraising: Optional[FundraisingAsk] = None
    market: Optional[MarketData] = None

    # ── Presentation controls ──
    slide_count: Optional[int] = Field(default=None, ge=1, le=50)
    language: str = Field(default="English", max_length=50)
    writing_style: WritingStyle = Field(default=WritingStyle.YC_CRISP)
    content_directives: Optional[ContentDirective] = None
    brand: Optional[BrandAssets] = None
    generate_images: bool = Field(default=True)
    generate_notes: bool = Field(default=True)
    theme_id: Optional[str] = None


class GenerationInputV4(BaseModel):
    """
    V4 Unified Generation Input — The single entry point.

    Wraps either:
      - StandardGenerationInput (standard mode, prompt-first)
      - PremiumPromptInput (premium mode, AI-parsed prompt)
      - PremiumStructuredInput (premium mode, field-by-field)

    The API route determines which variant based on `mode` + `input_method`.
    """
    mode: str = Field(
        ..., pattern="^(standard|premium)$",
        description="Generation mode: 'standard' or 'premium'"
    )
    input_method: InputMethod = Field(
        default=InputMethod.PROMPT,
        description="How the user provided input"
    )

    # ── Exactly one of these must be populated ──
    standard_input: Optional[StandardGenerationInput] = None
    premium_prompt_input: Optional[PremiumPromptInput] = None
    premium_structured_input: Optional[PremiumStructuredInput] = None

    @model_validator(mode="after")
    def validate_input_variant(self) -> "GenerationInputV4":
        """Ensure exactly one input variant matches the mode."""
        if self.mode == "standard":
            if not self.standard_input:
                raise ValueError("standard_input is required when mode is 'standard'")
            if self.premium_prompt_input or self.premium_structured_input:
                raise ValueError("Premium inputs must be None in standard mode")
        elif self.mode == "premium":
            has_prompt = self.premium_prompt_input is not None
            has_structured = self.premium_structured_input is not None
            if not has_prompt and not has_structured:
                raise ValueError("Either premium_prompt_input or premium_structured_input is required for premium mode")
            if has_prompt and has_structured:
                raise ValueError("Provide only one of premium_prompt_input or premium_structured_input")
        return self

    @property
    def effective_topic(self) -> str:
        """Extract the topic from whichever input variant is active."""
        if self.standard_input:
            # For standard, first 100 chars of prompt or parsed topic
            return self.standard_input.prompt[:100]
        if self.premium_structured_input:
            return self.premium_structured_input.topic
        if self.premium_prompt_input:
            return self.premium_prompt_input.prompt[:100]
        return "Untitled Presentation"

    @property
    def effective_mode_str(self) -> str:
        return self.mode

    @property
    def effective_slide_count(self) -> Optional[int]:
        """Raw user-supplied slide count, or ``None`` if not specified.

        Plan 02 (Slide Count Bug v2): the ONLY legitimate consumer of
        this property is
        ``app.services.v4.slide_count_resolver.resolve_requested_count``
        (via the V4 generation router). Every other layer must read the
        resolved ``int`` from the router — reading this property elsewhere
        re-introduces the original bug where ``None`` silently meant
        "trust whatever the LLM returned".
        """
        if self.standard_input:
            return self.standard_input.slide_count
        if self.premium_structured_input:
            return self.premium_structured_input.slide_count
        if self.premium_prompt_input:
            return self.premium_prompt_input.slide_count
        return None

    @property
    def effective_purpose(self) -> PresentationPurpose:
        if self.standard_input:
            return self.standard_input.purpose
        if self.premium_structured_input:
            return self.premium_structured_input.purpose
        if self.premium_prompt_input:
            return self.premium_prompt_input.purpose
        return PresentationPurpose.PITCH_DECK

    @property
    def effective_writing_style(self) -> WritingStyle:
        if self.standard_input:
            return self.standard_input.writing_style
        if self.premium_structured_input:
            return self.premium_structured_input.writing_style
        if self.premium_prompt_input:
            return self.premium_prompt_input.writing_style
        return WritingStyle.YC_CRISP

    @property
    def effective_language(self) -> str:
        if self.standard_input:
            return self.standard_input.language
        if self.premium_structured_input:
            return self.premium_structured_input.language
        if self.premium_prompt_input:
            return self.premium_prompt_input.language
        return "English"


# ═══════════════════════════════════════════════════════════════════
# INPUT ANALYSIS OUTPUT — produced by InputAnalyzer
# ═══════════════════════════════════════════════════════════════════

class ExtractedEntity(BaseModel):
    """An entity extracted from the user's prompt by the AI."""
    type: str = Field(..., description="Entity type: company, metric, competitor, person, technology, etc.")
    value: str = Field(..., description="The extracted value")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source_span: Optional[str] = Field(default=None, description="The text span this was extracted from")


class MissingContext(BaseModel):
    """A piece of context the AI detected as missing but important."""
    field: str = Field(..., description="What's missing: 'traction', 'team', 'financials', etc.")
    importance: str = Field(..., pattern="^(critical|recommended|optional)$")
    suggestion: str = Field(..., description="Friendly suggestion to the user")


class InputAnalysisResult(BaseModel):
    """
    The output of the InputAnalyzer — rich understanding of the user's intent.
    This feeds into the Strategist role.
    """
    # ── Inferred context ──
    detected_purpose: PresentationPurpose
    detected_audience: str
    audience_sophistication: AudienceSophistication
    detected_industry: Optional[str] = None
    detected_company_name: Optional[str] = None
    detected_stage: Optional[FundingStage] = None

    # ── Extracted entities ──
    entities: list[ExtractedEntity] = Field(default_factory=list)

    # ── Narrative suggestion ──
    suggested_narrative_arc: str = Field(
        default="problem_solution",
        description="Suggested story arc: problem_solution | vision_roadmap | data_story | case_study | demo_walkthrough"
    )
    # ge=1 (not 3) so single-slide standard-mode generations can be
    # analysed. The route layer (generation_v4.py) and StandardGeneration
    # input model already permit slide_count=1; clamping the analyser
    # output at 3 used to crash N=1 / N=2 requests with a Pydantic
    # ValidationError before the planner ever ran.
    suggested_slide_count: int = Field(default=10, ge=1, le=50)
    suggested_slide_types: list[str] = Field(default_factory=list)

    # ── Missing context ──
    missing_context: list[MissingContext] = Field(default_factory=list)

    # ── Quality signals ──
    input_richness_score: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="How much context the user provided (0=bare minimum, 1=very detailed)"
    )
    confidence: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Overall confidence in the analysis"
    )
