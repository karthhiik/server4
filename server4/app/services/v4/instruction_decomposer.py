"""
Instruction Decomposer — Solves the long-instruction hallucination problem.

LLMs struggle with prompts >2000 tokens because:
  1. Attention dilution — later instructions get less weight
  2. Conflicting rules — one rule can contradict another
  3. Instruction amnesia — model forgets early constraints by output time

Solution: Decompose the monolithic system prompt into a layered architecture:
  - Layer 1 (CORE): Identity + output format (always present, ~200 tokens)
  - Layer 2 (INTENT): Intent-specific rules (only the rules for THIS slide type)
  - Layer 3 (GUARD): Anti-hallucination checks (short, imperative)

This reduces effective prompt length by 60-70% per call while maintaining
all quality constraints. Each slide only sees rules relevant to its intent.
"""

from __future__ import annotations

from typing import Any, Optional


MODERN_INVESTOR_PROOF_BAR = """MODERN INVESTOR BAR:
- Investors are bored by boilerplate TAM, MVP demos, pilot logos, and "we use AI".
- Prefer proof signals: proprietary data, revenue momentum, production deployments,
  gross-margin trajectory, and compounding loops.
- If proof is missing, show the validation path honestly. Do not invent metrics.
"""


PROFESSIONAL_UNIQUENESS_BAR = """PROFESSIONAL UNIQUENESS BAR (real-world founders read this):
- Headline must be a thesis statement only THIS company could honestly claim.
  Generic patterns like "Transforming X with AI" or "The Future of Y" must be
  rewritten with specific evidence — a metric, a verb the user actually uses,
  or a concrete buyer description.
- Subheadline must add NEW signal, not restate the headline. Treat it as the
  one-sentence elevator the founder would say after the headline lands.
- Bullets must each carry one fact / one number / one proof point. No
  three-word labels. Aim for 8-18 words per bullet so the slide reads like an
  investor memo, not a feature checklist.
- Speaker notes are how a sharp founder would defend the slide in diligence:
  what the strongest investor objection is and how the slide answers it.
- Image prompts must reference the actual product, sector, and tone from the
  deck. Do not write "abstract gradient with floating cubes" when the deck is
  about logistics or healthcare.
"""


# ── Layer 1: Core Identity (always present, ~150 tokens) ──

CORE_IDENTITY = """You write ONE slide for an investor-grade pitch deck.
Role: Founder & CEO. Write in first person (We/Our/Us).
Never mention competitors on solution slides. Never fabricate data.
Every headline = specific thesis (3-8 words). Never generic labels.
Subheadline REQUIRED (6-14 words). Speaker notes REQUIRED (2-3 sentences).
"""

CORE_IDENTITY_STANDARD = """You write ONE slide for a professional pitch deck.
Role: Founder & CEO. First person (We/Our/Us). No fabricated data.
Headline = specific thesis (3-8 words). Subheadline REQUIRED. Speaker notes REQUIRED.
"""


# ── Layer 2: Intent-Specific Rules ──
# Each intent gets ONLY its relevant constraints (~100-200 tokens each)

INTENT_RULES: dict[str, str] = {
    "title": (
        "TITLE SLIDE: Include company name in headline. "
        "Body = 1-2 sentence elevator pitch. No bullets needed. "
        "If company_icon_url provided, note it for rendering."
    ),
    "problem": (
        "PROBLEM SLIDE: Describe the pain the customer feels TODAY. "
        "Use specific examples, not abstract claims. "
        "Bullets: 3-4 concrete pain points with metrics when available. "
        "Never mention your solution here — this is about the PROBLEM only."
    ),
    "solution": (
        "SOLUTION SLIDE: Describe YOUR product capabilities only. "
        "NEVER name competitors or compare. This is about WHAT YOU BUILT. "
        "Bullets: 3-4 specific features with outcomes. "
        "Body: How it works in 2-3 sentences."
    ),
    "market": (
        "MARKET SLIDE: Prefer stat_blocks with TAM/SAM/SOM or market size only when sourced. "
        "Every number over $1M needs source: '$2.5B (Gartner, 2024)'. "
        "If no sourced number is available, use a buyer-segment table or demand-driver bullets. "
        "Never invent market sizes — use 'estimated' qualifier when uncertain."
    ),
    "business_model": (
        "BUSINESS MODEL SLIDE: Include pricing/MRR/ARPU stat_blocks only when grounded. "
        "Map how money flows: pricing tiers, unit economics, expansion revenue. "
        "Bullets: specific revenue mechanics, buyer, value metric, and gross-margin proof path."
    ),
    "traction": (
        "TRACTION SLIDE: ONLY use numbers from user input or research. "
        "NEVER import metrics from other startups. Use stat_blocks/charts only for real metrics. "
        "If no real metrics are available, show a validation path without fabricating."
    ),
    "competition": (
        "COMPETITION SLIDE: Name REAL competitors (not 'Traditional Players'). "
        "Use comparison layout. Each column = specific company or category. "
        "Highlight YOUR differentiation in the last column."
    ),
    "team": (
        "TEAM SLIDE: NEVER fabricate names, bios, or credentials. "
        "Use ONLY data from structured input or user-provided team info. "
        "If team data not provided, acknowledge slide needs user input. "
        "Include linkedin_url, x_url (Twitter), and photo_url from team_members data when available."
    ),
    "ask": (
        "ASK/FUNDRAISING SLIDE: Include raise/runway/equity stat_blocks only when provided. "
        "MUST include use-of-funds breakdown where lines total the raise amount. "
        "If no raise amount provided, do NOT invent one — frame around milestones. "
        "Be specific: '$2M → Engineering (50%), GTM (30%), Ops (20%)'"
    ),
    "financials": (
        "FINANCIALS SLIDE: ONLY use numbers from user input. "
        "Use stat_blocks/charts only when numbers are grounded. Never copy numbers from other startups. "
        "If minimal data: show revenue trajectory narrative without fabricating."
    ),
    "go_to_market": (
        "GTM SLIDE: Describe specific channels and acquisition strategies. "
        "Bullets: concrete actions (not 'leverage partnerships'). "
        "Include metrics if available: CAC, LTV, conversion rates."
    ),
    "vision": (
        "VISION SLIDE: Where the company is going in 3-5 years. "
        "Be ambitious but grounded. Connect vision to current traction. "
        "Body: narrative paragraph about the future state."
    ),
    "closing": (
        "CLOSING SLIDE: Strong call-to-action. Contact info if available. "
        "Headline = memorable thesis. Keep minimal and impactful."
    ),
}

# Default for unknown intents
_DEFAULT_INTENT_RULE = (
    "Write specific, factual content grounded in the research provided. "
    "Include stat_blocks when quantitative data is available. "
    "Every bullet = 6-14 words, concrete claim (not vague opinion)."
)


# ── Layer 3: Anti-Hallucination Guards ──
# Short, imperative, always-present checklist

ANTI_HALLUCINATION_GUARD = """GUARDS (violating ANY = FAILURE):
- NO invented statistics or sources
- NO placeholder text ($X, TBD, Y%)
- NO instruction parroting (never echo "Cover", "Explain", "Demonstrate")
- NO website title copying (synthesize insights, don't copy headlines)
- NO topic drift (every word relates to THIS company)
- NO generic labels as headlines (Market Opportunity, Our Team, etc.)
- Source every number >$1M or >10%: "value (Source, year)"
"""

ANTI_HALLUCINATION_GUARD_PREMIUM = """GUARDS (violating ANY = FAILURE):
- NO invented statistics, sources, or citation URLs
- NO placeholder text ($X, TBD, Y%, "Coming soon")
- NO instruction parroting (never echo system directives as content)
- NO website title/SEO description copying
- NO topic drift — every word about THIS specific company
- NO generic headline labels
- Every number >$1M: "value (Source, year)" — if unsourced, write "estimated"
- Every bullet = specific quantified fact, not vague opinion
- Competitor names MUST be real companies, never "Traditional Players"
- If a number lacks source evidence, omit the number instead of labeling it estimated
"""


# ── Composer Functions ──

def compose_system_prompt(
    *,
    mode: str,
    intent: str,
    layout_hint: Optional[str] = None,
    include_toon: bool = True,
) -> str:
    """Compose a focused system prompt for a single slide.
    
    Instead of one 3000-token monolithic prompt, this produces a 
    400-800 token focused prompt with only relevant rules.
    
    Args:
        mode: 'standard' or 'premium'
        intent: Slide intent (market, team, solution, etc.)
        layout_hint: Optional layout type for format-specific rules
        include_toon: Whether to append TOON output format instructions
    
    Returns:
        Focused system prompt string (~400-800 tokens vs ~3000 original)
    """
    parts = []
    
    # Layer 1: Core identity
    if mode == "premium":
        parts.append(CORE_IDENTITY)
    else:
        parts.append(CORE_IDENTITY_STANDARD)
    
    # Layer 2: Intent-specific rules
    intent_key = intent.lower().replace("-", "_").replace(" ", "_")
    rule = INTENT_RULES.get(intent_key, _DEFAULT_INTENT_RULE)
    parts.append(f"\n{rule}")
    parts.append(f"\n{MODERN_INVESTOR_PROOF_BAR}")
    # Premium tier earns the extra quality bar — investors and founders pay
    # for this tier expecting deck content that survives diligence. Standard
    # tier skips it to keep the prompt budget tight.
    if mode == "premium":
        parts.append(f"\n{PROFESSIONAL_UNIQUENESS_BAR}")
    
    # Layout format hint
    if layout_hint:
        layout_rule = _get_layout_rule(layout_hint)
        if layout_rule:
            parts.append(f"\nLAYOUT ({layout_hint}): {layout_rule}")
    
    # Layer 3: Anti-hallucination guard
    if mode == "premium":
        parts.append(f"\n{ANTI_HALLUCINATION_GUARD_PREMIUM}")
    else:
        parts.append(f"\n{ANTI_HALLUCINATION_GUARD}")
    
    # Output format
    if include_toon:
        from app.services.v4.toon import TOON_FORMAT_INSTRUCTION
        parts.append(f"\n{TOON_FORMAT_INSTRUCTION}")
    else:
        parts.append(_JSON_OUTPUT_FORMAT)
    
    return "\n".join(parts)


def _get_layout_rule(layout: str) -> str:
    """Get format-specific output shape for a layout."""
    rules = {
        "stat-hero": "Populate stat_blocks (2-3 items: {value, label})",
        "chart-focus": "Populate chart: {type:bar|line|pie, data:[{label,value}]}",
        "comparison": "Populate comparison: {columns:[{title, items[], highlight?}]}",
        "table": "Populate table: {headers:[], rows:[[]]} (max 6 cols, 8 rows)",
        "timeline": "Populate timeline: {events:[{date, title, description?}]} (3-7 items)",
        "diagram": "Populate diagram: {nodes:[{id,label}], edges:[{from,to}]} (max 12 nodes)",
        "quote": "Populate quote: {text, attribution}",
        "grid-3": "Provide exactly 3 items (bullets or stat_blocks)",
        "image-full": "Minimal text + image_prompt describing the visual",
        "title-only": "Headline + subheadline only, no bullets",
    }
    return rules.get(layout, "")


_JSON_OUTPUT_FORMAT = """
OUTPUT: Return ONLY valid JSON with applicable fields:
{headline, subheadline, bullets[], body, stat_blocks[{value,label}],
chart, table, timeline, comparison, diagram, quote,
image_prompt, speaker_notes, citations[{url,title}]}
Omit null/empty fields."""


def estimate_token_savings(mode: str, intent: str) -> dict[str, int]:
    """Estimate token savings from decomposed vs monolithic prompt.
    
    Returns approximate token counts for comparison.
    """
    decomposed = compose_system_prompt(mode=mode, intent=intent, include_toon=True)
    # Rough token estimation: ~4 chars per token for English
    decomposed_tokens = len(decomposed) // 4
    
    # Original monolithic prompts are ~3000 tokens for premium, ~1800 for standard
    original_tokens = 3000 if mode == "premium" else 1800
    
    return {
        "original_tokens": original_tokens,
        "decomposed_tokens": decomposed_tokens,
        "savings_tokens": original_tokens - decomposed_tokens,
        "savings_percent": round((1 - decomposed_tokens / original_tokens) * 100),
    }
