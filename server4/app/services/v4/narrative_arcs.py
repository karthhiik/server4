"""Purpose-aware narrative arcs for V4 standard-mode planning.

Plan 03 \u2014 see ``docs/founder-plans/03-purpose-aware-narrative.md``.

This module is the single source of truth that maps every value of
``app.models.generation_input_v4.PresentationPurpose`` to:

  1. An ordered list of ``NarrativeSlot`` objects defining the canonical
     deck shape for that purpose (title \u2192 body \u2192 close).
  2. A ``VoiceProfile`` describing tone (formality, technicality,
     persuasiveness, urgency, empathy) so the planner can match the
     register expected for that purpose.
  3. A ``forbidden_intents`` set used post-parse to detect cross-purpose
     contamination (e.g. an ``educational`` deck slipping a
     ``competition`` slide in).

Design constraints (from plan 03 + GLM-5.1V research feedback, selectively
adopted):

  * Every arc covers a *real* ``PresentationPurpose`` enum value. No
     invented purposes \u2014 the surface is what the API already exposes.
  * Slot priorities (``must``/``important``/``optional``) drive
     ``scale_arc()`` so requested counts above or below the canonical
     length are honoured *exactly* without dropping anchor slots.
  * The arc is *guidance*, not a prison: the planner LLM still authors
     thesis lines, key points, evidence pointers. It only fills the
     skeleton. This matches Gamma.app's adapt-and-remix philosophy that
     beats both pure-template and pure-blank-canvas tools.
  * Premium mode is **not** affected. The premium planner has its own
     scaffold + research path; per the founder spec we do not touch it.

This module is pure: no I/O, no LLM calls, no globals mutated. Safe to
import from anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, Optional

import structlog

logger = structlog.get_logger(__name__)


SlotPriority = Literal["must", "important", "optional"]


@dataclass(frozen=True)
class NarrativeSlot:
    """A single slot in a purpose's canonical narrative arc."""

    intent: str
    """Slide intent label (lowercase, snake_case) \u2014 e.g. ``problem``,
    ``traction``, ``concept_1``. Matches ``SlideSkeleton.intent``."""

    suggested_layout: str
    """Default layout hint the planner should use unless it has stronger
    evidence for another. Must be a value the slide compiler / sandbox
    kit understands (``two-column``, ``stat-hero``, ``image-full``,
    ``grid-3``, ``chart-focus``, ``comparison``, ``table``,
    ``timeline``, ``quote``, ``bullet-points``, ``diagram``,
    ``process``, ``title-only``)."""

    brief: str
    """Short human-language description of what content fills this slot."""

    priority: SlotPriority = "important"
    """``must`` slots are never trimmed when scaling down; ``optional``
    slots are dropped first; ``important`` slots are dropped second."""

    voice_guidance: str = ""
    """One-line tone hint surfaced to the planner so it can phrase the
    thesis line in the right register. E.g. ``\"confident, visionary\"``
    for a pitch ``problem``, ``\"direct, executive-summary\"`` for an
    internal-memo recommendation."""


@dataclass(frozen=True)
class VoiceProfile:
    """Five-axis tone descriptor for a purpose.

    All axes are floats in ``[0.0, 1.0]``. Values are surfaced verbatim
    to the planner LLM as numeric guidance \u2014 we deliberately keep them
    machine-friendly so prompt engineers can tune one axis at a time.
    """

    formality: float = 0.5
    """0 = conversational, 1 = formal."""

    technicality: float = 0.5
    """0 = layperson, 1 = subject-matter expert."""

    persuasiveness: float = 0.5
    """0 = informative only, 1 = explicitly selling."""

    urgency: float = 0.5
    """0 = exploratory, 1 = action-required."""

    empathy: float = 0.5
    """0 = facts-only, 1 = emotionally resonant."""

    def as_dict(self) -> dict[str, float]:
        return {
            "formality": self.formality,
            "technicality": self.technicality,
            "persuasiveness": self.persuasiveness,
            "urgency": self.urgency,
            "empathy": self.empathy,
        }


# \u2550\u2550 NARRATIVE ARC LIBRARY \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#
# Keys MUST match values of ``PresentationPurpose`` (string Enum).
# When adding a new purpose to that Enum, add its arc here too \u2014 the
# resolver falls back to ``custom`` when a key is missing, but every
# real purpose deserves a hand-crafted arc.

_PITCH_DECK: list[NarrativeSlot] = [
    NarrativeSlot("title",          "title-only",  "Company name + tagline + logo",            "must",      "confident, visionary"),
    NarrativeSlot("problem",        "two-column",  "Pain point + market evidence",             "must",      "urgent, relatable"),
    NarrativeSlot("solution",       "image-full",  "Product + how it solves the pain",         "must",      "clear, transformative"),
    NarrativeSlot("market",         "stat-hero",   "TAM / SAM / SOM with sources",             "important", "data-driven, ambitious"),
    NarrativeSlot("how_it_works",   "process",     "Three-step mechanism / product flow",      "important", "concrete, demonstrable"),
    NarrativeSlot("traction",       "chart-focus", "MRR / users / growth curve",               "must",      "proof-backed, momentum"),
    NarrativeSlot("business_model", "grid-3",      "Pricing tiers + unit economics",           "important", "logical, sustainable"),
    NarrativeSlot("competition",    "comparison",  "Feature matrix vs incumbents",             "optional",  "differentiated, respectful"),
    NarrativeSlot("team",           "grid-3",      "Founder bios + relevant wins",             "important", "credible, mission-aligned"),
    NarrativeSlot("financials",     "table",       "Projection + assumptions",                 "optional",  "realistic, transparent"),
    NarrativeSlot("ask",            "stat-hero",   "Raise size + use of funds",                "must",      "clear, actionable"),
    NarrativeSlot("contact",        "title-only",  "Thank-you + contact info",                 "must",      "grateful, open"),
]

_INVESTOR_UPDATE: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Period + company + headline metric",   "must",      "transparent, executive"),
    NarrativeSlot("highlights",       "stat-hero",   "Top 3 wins this period",               "must",      "celebratory, factual"),
    NarrativeSlot("kpis",             "chart-focus", "Revenue / growth / retention vs plan", "must",      "data-first"),
    NarrativeSlot("product",          "two-column",  "Shipped + roadmap",                    "important", "informative"),
    NarrativeSlot("customers",        "grid-3",      "Logos / case wins / churn signals",    "important", "evidence-led"),
    NarrativeSlot("team",             "grid-3",      "Hires / departures / org changes",     "optional",  "human, candid"),
    NarrativeSlot("challenges",       "bullet-points","Blockers + how we are responding",    "important", "transparent, owning"),
    NarrativeSlot("asks",             "title-only",  "Specific intros / advice requested",   "must",      "direct, actionable"),
    NarrativeSlot("close",            "title-only",  "Thank-you + next update date",         "must",      "warm, professional"),
]

_SALES_DECK: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Buyer-tailored cover",                 "must",      "warm, prepared"),
    NarrativeSlot("buyer_pain",       "two-column",  "Their pain in their words",            "must",      "empathetic, specific"),
    NarrativeSlot("reframe",          "diagram",     "Reframe the problem (challenger lens)","important", "insightful, teaching"),
    NarrativeSlot("solution",         "image-full",  "Our product as the answer",            "must",      "benefit-led"),
    NarrativeSlot("differentiators",  "grid-3",      "Why us vs status quo / others",        "important", "distinct, confident"),
    NarrativeSlot("case_study",       "quote",       "Customer outcome + quote",             "must",      "credible, authentic"),
    NarrativeSlot("pricing",          "table",       "Pricing tiers + total cost",           "important", "transparent"),
    NarrativeSlot("next_steps",       "title-only",  "Concrete next-step + owner",           "must",      "action-oriented"),
]

_PRODUCT_LAUNCH: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Product name + launch date",           "must",      "energetic"),
    NarrativeSlot("market_problem",   "two-column",  "Why we are launching now",             "must",      "urgent"),
    NarrativeSlot("product_reveal",   "image-full",  "What it is, hero shot",                "must",      "exciting"),
    NarrativeSlot("key_features",     "grid-3",      "Three flagship capabilities",          "must",      "concrete"),
    NarrativeSlot("differentiation",  "comparison",  "How it differs from prior art",        "important", "confident"),
    NarrativeSlot("target_audience",  "two-column",  "Who it is for + buyer persona",        "important", "specific"),
    NarrativeSlot("go_to_market",     "timeline",    "Channels + launch sequence",           "important", "structured"),
    NarrativeSlot("success_metrics",  "stat-hero",   "What we will measure",                 "important", "data-led"),
    NarrativeSlot("call_to_action",   "title-only",  "Where to try / buy / learn more",      "must",      "direct"),
]

_QUARTERLY_REVIEW: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Quarter + team + theme",               "must",      "factual"),
    NarrativeSlot("executive_summary","stat-hero",   "Top-line result + verdict",            "must",      "decisive"),
    NarrativeSlot("kpi_dashboard",    "chart-focus", "Quantitative results vs targets",      "must",      "data-driven"),
    NarrativeSlot("wins",             "grid-3",      "Top achievements",                     "important", "celebratory"),
    NarrativeSlot("misses",           "bullet-points","Targets missed + reasons",            "important", "candid"),
    NarrativeSlot("learnings",        "two-column",  "What we learned",                      "optional",  "reflective"),
    NarrativeSlot("next_quarter",     "process",     "Priorities + bets",                    "must",      "forward-looking"),
    NarrativeSlot("asks",             "title-only",  "Cross-team support needed",            "important", "direct"),
]

_BOARD_MEETING: list[NarrativeSlot] = [
    # Pyramid principle \u2014 answer first, then support.
    NarrativeSlot("executive_summary","stat-hero",   "Decisions needed + recommendations",   "must",      "decisive, executive"),
    NarrativeSlot("financial_performance","chart-focus","Revenue / burn / runway vs plan",   "must",      "transparent"),
    NarrativeSlot("strategic_milestones","process",  "OKRs + flagship progress",             "must",      "progress-focused"),
    NarrativeSlot("market_competitive","comparison", "Market trends + competitive moves",    "important", "strategic"),
    NarrativeSlot("risks_issues",     "bullet-points","Material risks + mitigations",        "must",      "proactive"),
    NarrativeSlot("people",           "grid-3",      "Hiring / org changes",                 "optional",  "human"),
    NarrativeSlot("decisions_requested","title-only","Voting items / approvals",             "must",      "specific"),
]

_CONFERENCE_TALK: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Talk title + speaker",                 "must",      "intriguing"),
    NarrativeSlot("hook",             "quote",       "Opening provocation / story",          "must",      "captivating"),
    NarrativeSlot("agenda",           "bullet-points","What we will cover",                  "optional",  "clear"),
    NarrativeSlot("context",          "two-column",  "Background the audience needs",        "important", "accessible"),
    NarrativeSlot("idea_1",           "diagram",     "First main idea + evidence",           "must",      "concrete"),
    NarrativeSlot("idea_2",           "diagram",     "Second main idea + evidence",          "must",      "concrete"),
    NarrativeSlot("idea_3",           "diagram",     "Third main idea + evidence",           "important", "concrete"),
    NarrativeSlot("application",      "image-full",  "What the audience should do Monday",   "must",      "practical"),
    NarrativeSlot("close",            "title-only",  "Memorable closing line + thanks",      "must",      "resonant"),
    NarrativeSlot("q_and_a",          "title-only",  "Q&A + contact",                        "important", "open"),
]

_TRAINING: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Module name + audience",               "must",      "warm, clear"),
    NarrativeSlot("learning_objectives","bullet-points","What you will be able to do",       "must",      "specific"),
    NarrativeSlot("prerequisites",    "two-column",  "Background needed + tools",            "optional",  "matter-of-fact"),
    NarrativeSlot("concept_1",        "diagram",     "First concept",                        "must",      "pedagogical"),
    NarrativeSlot("worked_example_1", "image-full",  "Worked example for concept 1",         "important", "practical"),
    NarrativeSlot("concept_2",        "diagram",     "Second concept",                       "must",      "pedagogical"),
    NarrativeSlot("worked_example_2", "image-full",  "Worked example for concept 2",         "important", "practical"),
    NarrativeSlot("exercise",         "bullet-points","Try-it-yourself activity",            "important", "interactive"),
    NarrativeSlot("recap",            "bullet-points","Key takeaways",                       "must",      "synthesizing"),
    NarrativeSlot("resources",        "title-only",  "Further reading + support",            "important", "supportive"),
]

_PROJECT_PROPOSAL: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Proposal name + sponsor",              "must",      "professional"),
    NarrativeSlot("background",       "two-column",  "Context + why now",                    "must",      "informative"),
    NarrativeSlot("objectives",       "bullet-points","What we will deliver",                "must",      "specific"),
    NarrativeSlot("approach",         "process",     "Phased plan",                          "must",      "logical"),
    NarrativeSlot("scope",            "comparison",  "In-scope vs out-of-scope",             "important", "boundary-setting"),
    NarrativeSlot("timeline",         "timeline",    "Milestones + dates",                   "important", "structured"),
    NarrativeSlot("team_resources",   "grid-3",      "Team + tooling required",              "important", "credible"),
    NarrativeSlot("budget",           "table",       "Cost breakdown",                       "must",      "transparent"),
    NarrativeSlot("risks",            "bullet-points","Risks + mitigations",                 "important", "candid"),
    NarrativeSlot("decision",         "title-only",  "Approval requested",                   "must",      "direct"),
]

_CASE_STUDY: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Client + outcome headline",            "must",      "success-focused"),
    NarrativeSlot("client_context",   "two-column",  "Who the client is",                    "important", "credible"),
    NarrativeSlot("challenge",        "bullet-points","Pain points + stakes",                "must",      "vivid, empathetic"),
    NarrativeSlot("approach",         "process",     "Methodology + why chosen",             "important", "expert"),
    NarrativeSlot("solution",         "image-full",  "What was implemented",                 "must",      "concrete"),
    NarrativeSlot("results",          "stat-hero",   "Quantified outcome + timeline",        "must",      "data-driven"),
    NarrativeSlot("testimonial",      "quote",       "Client quote",                         "important", "authentic"),
    NarrativeSlot("lessons",          "bullet-points","Key transferable insights",           "optional",  "reflective"),
    NarrativeSlot("conclusion",       "title-only",  "CTA for similar prospects",            "must",      "inviting"),
]

_COMPANY_OVERVIEW: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Company + tagline",                    "must",      "confident"),
    NarrativeSlot("mission",          "stat-hero",   "Why we exist",                         "must",      "purposeful"),
    NarrativeSlot("what_we_do",       "two-column",  "Products / services overview",         "must",      "clear"),
    NarrativeSlot("customers",        "grid-3",      "Who we serve + logos",                 "important", "credible"),
    NarrativeSlot("traction",         "chart-focus", "Scale + key metrics",                  "important", "data-led"),
    NarrativeSlot("differentiation",  "comparison",  "What sets us apart",                   "important", "distinct"),
    NarrativeSlot("team",             "grid-3",      "Leadership + culture",                 "important", "human"),
    NarrativeSlot("milestones",       "timeline",    "History + roadmap",                    "optional",  "narrative"),
    NarrativeSlot("contact",          "title-only",  "How to engage",                        "must",      "open"),
]

_DEMO_DAY: list[NarrativeSlot] = [
    # Sub-3-minute YC-style demo day pacing.
    NarrativeSlot("title",            "title-only",  "Company + one-liner",                  "must",      "punchy"),
    NarrativeSlot("problem",          "two-column",  "Pain in one sentence",                 "must",      "urgent"),
    NarrativeSlot("solution",         "image-full",  "What we built",                        "must",      "concrete"),
    NarrativeSlot("traction",         "stat-hero",   "Single most impressive metric",        "must",      "high-impact"),
    NarrativeSlot("market",           "stat-hero",   "Market size signal",                   "important", "ambitious"),
    NarrativeSlot("team",             "grid-3",      "Why this team",                        "important", "credible"),
    NarrativeSlot("ask",              "title-only",  "What we need + how to reach us",       "must",      "direct"),
]

_EDUCATIONAL: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Topic + learning objective",           "must",      "engaging"),
    NarrativeSlot("agenda",           "bullet-points","What we will cover",                  "important", "structured"),
    NarrativeSlot("context",          "two-column",  "Background + why it matters",          "important", "relatable"),
    NarrativeSlot("concept_1",        "diagram",     "First key concept",                    "must",      "pedagogical"),
    NarrativeSlot("concept_2",        "diagram",     "Second key concept (builds on 1)",     "must",      "progressive"),
    NarrativeSlot("worked_example",   "image-full",  "Concrete worked example",              "must",      "practical"),
    NarrativeSlot("common_pitfalls",  "bullet-points","Frequent mistakes to avoid",          "optional",  "candid"),
    NarrativeSlot("recap",            "bullet-points","Key takeaways",                       "must",      "synthesizing"),
    NarrativeSlot("q_and_a",          "title-only",  "Questions + further reading",          "important", "open"),
]

_INTERNAL_MEMO: list[NarrativeSlot] = [
    # Pyramid principle \u2014 answer first, then support.
    NarrativeSlot("title",            "title-only",  "Memo subject + decision required",     "must",      "concise"),
    NarrativeSlot("executive_summary","bullet-points","TL;DR up front",                      "must",      "direct, no-fluff"),
    NarrativeSlot("context",          "two-column",  "Background + why now",                 "important", "efficient"),
    NarrativeSlot("analysis",         "table",       "Data + options considered",            "important", "objective"),
    NarrativeSlot("recommendation",   "stat-hero",   "Proposed path forward",                "must",      "decisive"),
    NarrativeSlot("implications",     "comparison",  "Pros / cons / risks",                  "important", "balanced"),
    NarrativeSlot("next_steps",       "bullet-points","Actions + owners + deadlines",        "must",      "accountable"),
]

_CUSTOM: list[NarrativeSlot] = [
    # Generic but coherent fallback when the user's purpose does not
    # match any specific arc above. Mirrors the SCQA framework
    # (Situation \u2192 Complication \u2192 Question \u2192 Answer).
    NarrativeSlot("title",            "title-only",  "Topic + author",                       "must",      "clear"),
    NarrativeSlot("situation",        "two-column",  "Where we stand today",                 "must",      "factual"),
    NarrativeSlot("complication",     "stat-hero",   "What changed / what is at stake",      "must",      "concrete"),
    NarrativeSlot("analysis",         "two-column",  "Key considerations",                   "important", "structured"),
    NarrativeSlot("answer",           "image-full",  "Proposed direction",                   "must",      "decisive"),
    NarrativeSlot("evidence",         "grid-3",      "Supporting facts",                     "important", "credible"),
    NarrativeSlot("next_steps",       "title-only",  "What happens next",                    "must",      "actionable"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# STANDARD MODE PITCH DECK PURPOSES (15+ new purposes for Standard Mode)
# ═══════════════════════════════════════════════════════════════════════════════

_DEEP_TECH: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Technology + company name",              "must",      "technical, precise"),
    NarrativeSlot("architecture",      "diagram",     "System architecture overview",           "must",      "structural, detailed"),
    NarrativeSlot("technical_problem", "two-column", "Technical challenge being solved",       "must",      "problem-focused"),
    NarrativeSlot("solution",          "image-full",  "Technical solution implementation",      "must",      "concrete, demonstrable"),
    NarrativeSlot("performance",      "chart-focus", "Benchmarks + performance metrics",      "must",      "data-driven, quantitative"),
    NarrativeSlot("scalability",      "process",     "How system scales",                      "important", "architectural"),
    NarrativeSlot("security",         "bullet-points","Security measures + compliance",        "important", "security-focused"),
    NarrativeSlot("integration",      "diagram",     "API + integration patterns",             "optional",  "technical"),
    NarrativeSlot("deployment",       "process",     "Deployment + infrastructure",            "optional",  "operational"),
    NarrativeSlot("team",             "grid-3",      "Technical team expertise",                "important", "credibility-focused"),
    NarrativeSlot("roadmap",          "timeline",    "Technical roadmap",                       "important", "forward-looking"),
    NarrativeSlot("contact",         "title-only",  "Technical contact + docs",                "must",      "accessible"),
]

_VC_PITCH: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Company + one-liner",                    "must",      "punchy, visionary"),
    NarrativeSlot("problem",         "two-column",  "Market pain + opportunity",               "must",      "urgent, compelling"),
    NarrativeSlot("solution",         "image-full",  "Product + how it solves",                 "must",      "clear, transformative"),
    NarrativeSlot("market",           "stat-hero",   "TAM / SAM / SOM with sources",             "must",      "ambitious, data-backed"),
    NarrativeSlot("traction",         "chart-focus", "Growth metrics + momentum",               "must",      "proof-backed, exciting"),
    NarrativeSlot("business_model",  "grid-3",      "Revenue model + unit economics",          "must",      "logical, sustainable"),
    NarrativeSlot("competition",     "comparison",  "Competitive positioning",                 "important", "differentiated"),
    NarrativeSlot("team",            "grid-3",      "Founders + key hires",                    "must",      "credibility, mission-aligned"),
    NarrativeSlot("financials",      "table",       "Projections + key assumptions",            "important", "realistic"),
    NarrativeSlot("ask",             "stat-hero",   "Raise amount + use of funds",             "must",      "clear, actionable"),
    NarrativeSlot("timeline",        "timeline",    "Milestones + use of proceeds",             "important", "strategic"),
    NarrativeSlot("contact",         "title-only",  "Thank-you + contact",                     "must",      "grateful, open"),
]

_EXECUTIVE_BRIEF: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Topic + executive summary",              "must",      "concise, executive"),
    NarrativeSlot("executive_summary","stat-hero", "Bottom-line recommendation",              "must",      "decisive, direct"),
    NarrativeSlot("context",          "two-column",  "Background + why this matters",           "important", "efficient"),
    NarrativeSlot("analysis",         "table",       "Data + key findings",                     "must",      "objective, data-driven"),
    NarrativeSlot("options",          "comparison",  "Strategic options evaluated",              "important", "balanced"),
    NarrativeSlot("recommendation",   "stat-hero",   "Recommended path forward",                "must",      "decisive"),
    NarrativeSlot("risks",            "bullet-points","Key risks + mitigations",                "important", "candid, proactive"),
    NarrativeSlot("financial_impact", "chart-focus", "ROI / cost-benefit analysis",             "must",      "quantitative"),
    NarrativeSlot("next_steps",      "title-only",  "Actions + owners + timeline",             "must",      "accountable"),
]

_TRUST_COMPLIANCE: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Trust + compliance overview",             "must",      "authoritative, reassuring"),
    NarrativeSlot("compliance_landscape","two-column","Regulatory environment",                "must",      "informative"),
    NarrativeSlot("security_framework","diagram",    "Security architecture",                   "must",      "technical, detailed"),
    NarrativeSlot("certifications",   "grid-3",      "Compliance certifications + audits",      "must",      "credibility-focused"),
    NarrativeSlot("data_protection",  "process",     "Data protection measures",                "must",      "privacy-focused"),
    NarrativeSlot("incident_response","bullet-points","Incident response procedures",             "important", "prepared"),
    NarrativeSlot("third_party",      "comparison",  "Third-party validations",                  "important", "independent"),
    NarrativeSlot("risk_mitigation",  "table",       "Risk assessment + mitigation",            "must",      "comprehensive"),
    NarrativeSlot("contact",         "title-only",  "Compliance contact + resources",          "must",      "accessible"),
]

_CINEMATIC_KEYNOTE: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Single powerful phrase",                   "must",      "poetic, minimalist"),
    NarrativeSlot("hook",             "quote",       "Opening emotional hook",                  "must",      "captivating"),
    NarrativeSlot("vision",           "image-full",  "Future vision visualization",              "must",      "inspiring"),
    NarrativeSlot("story",            "two-column",  "Narrative arc + human impact",             "must",      "emotional"),
    NarrativeSlot("moment",           "stat-hero",   "Defining moment + impact",                 "must",      "high-impact"),
    NarrativeSlot("insight",          "diagram",     "Key insight revealed",                     "important", "revealing"),
    NarrativeSlot("journey",          "timeline",    "The journey so far",                       "important", "narrative"),
    NarrativeSlot("possibility",     "image-full",  "What becomes possible",                   "must",      "aspirational"),
    NarrativeSlot("call_to_action",  "title-only",  "Single powerful call to action",           "must",      "inspiring"),
]

_SEED_ROUND: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Company + vision statement",               "must",      "visionary, founder-led"),
    NarrativeSlot("founder_story",    "two-column",  "Why we started + personal journey",        "must",      "authentic, narrative"),
    NarrativeSlot("problem",          "two-column",  "Problem we're solving",                    "must",      "relatable, urgent"),
    NarrativeSlot("solution",         "image-full",  "Our solution + early traction",            "must",      "clear, exciting"),
    NarrativeSlot("market",           "stat-hero",   "Market opportunity",                       "must",      "ambitious, validated"),
    NarrativeSlot("traction",         "chart-focus", "Early metrics + validation",               "must",      "proof-backed"),
    NarrativeSlot("team",            "grid-3",      "Founders + why this team",                 "must",      "credibility-focused"),
    NarrativeSlot("ask",             "stat-hero",   "Seed round ask + use of funds",            "must",      "clear, specific"),
    NarrativeSlot("roadmap",         "timeline",    "18-month roadmap",                         "important", "realistic"),
    NarrativeSlot("contact",         "title-only",  "Thank-you + contact",                     "must",      "grateful"),
]

_SERIES_A: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Company + growth headline",                "must",      "data-driven, confident"),
    NarrativeSlot("traction",         "chart-focus", "Growth metrics + momentum",               "must",      "proof-backed, impressive"),
    NarrativeSlot("problem",          "two-column",  "Market pain + opportunity",               "must",      "urgent, validated"),
    NarrativeSlot("solution",         "image-full",  "Product + differentiation",                "must",      "clear, compelling"),
    NarrativeSlot("market",           "stat-hero",   "TAM / SAM / SOM + growth",                 "must",      "ambitious, data-backed"),
    NarrativeSlot("unit_economics",  "grid-3",      "CAC / LTV / payback period",               "must",      "financial, rigorous"),
    NarrativeSlot("business_model",   "process",     "Revenue model + monetization",             "must",      "logical"),
    NarrativeSlot("competition",     "comparison",  "Competitive positioning",                 "important", "differentiated"),
    NarrativeSlot("team",            "grid-3",      "Team + key hires",                        "must",      "credibility-focused"),
    NarrativeSlot("financials",      "table",       "Projections + assumptions",                "must",      "realistic, detailed"),
    NarrativeSlot("ask",             "stat-hero",   "Series A ask + use of funds",              "must",      "clear, actionable"),
    NarrativeSlot("contact",         "title-only",  "Thank-you + contact",                     "must",      "professional"),
]

_PARTNERSHIP: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Partnership opportunity",                  "must",      "collaborative, professional"),
    NarrativeSlot("about_us",         "two-column",  "Who we are + what we do",                 "must",      "clear, credible"),
    NarrativeSlot("about_you",        "two-column",  "Understanding your business",             "must",      "partner-focused"),
    NarrativeSlot("synergy",          "diagram",     "How we fit together",                     "must",      "mutual benefit"),
    NarrativeSlot("value_proposition","grid-3",     "Value for both parties",                   "must",      "win-win"),
    NarrativeSlot("integration",      "process",     "Technical integration path",               "important", "concrete"),
    NarrativeSlot("business_model",   "comparison",  "Revenue sharing model",                    "must",      "transparent"),
    NarrativeSlot("success_metrics",  "chart-focus", "Shared success metrics",                   "important", "aligned"),
    NarrativeSlot("next_steps",       "title-only",  "Path to partnership",                     "must",      "actionable"),
]

_CUSTOMER_CASE: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Customer + success headline",              "must",      "success-focused"),
    NarrativeSlot("customer_profile", "two-column",  "Who the customer is",                      "must",      "credible"),
    NarrativeSlot("challenge",        "bullet-points","Pain points + stakes",                     "must",      "vivid, empathetic"),
    NarrativeSlot("solution",         "image-full",  "What we implemented",                      "must",      "concrete"),
    NarrativeSlot("implementation",  "process",     "How we worked together",                   "important", "collaborative"),
    NarrativeSlot("results",          "stat-hero",   "Quantified outcomes + timeline",            "must",      "data-driven"),
    NarrativeSlot("testimonial",      "quote",       "Customer quote",                           "important", "authentic"),
    NarrativeSlot("lessons",          "bullet-points","Key learnings",                            "optional",  "reflective"),
    NarrativeSlot("next_steps",       "title-only",  "Future collaboration",                     "must",      "forward-looking"),
]

_FUNDRAISING_ROADSHOW: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Company + fundraising round",               "must",      "confident, prepared"),
    NarrativeSlot("executive_summary","stat-hero", "Investment thesis in one slide",            "must",      "compelling"),
    NarrativeSlot("market",           "stat-hero",   "TAM / SAM / SOM + growth rate",             "must",      "ambitious, data-backed"),
    NarrativeSlot("traction",         "chart-focus", "Growth metrics + momentum",                 "must",      "impressive"),
    NarrativeSlot("product",          "image-full",  "Product + differentiation",                 "must",      "clear, compelling"),
    NarrativeSlot("unit_economics",  "grid-3",      "CAC / LTV / payback",                       "must",      "financial, rigorous"),
    NarrativeSlot("business_model",   "process",     "Revenue model + monetization",              "must",      "logical"),
    NarrativeSlot("competition",     "comparison",  "Competitive landscape",                    "important", "positioned"),
    NarrativeSlot("team",            "grid-3",      "Team + advisors",                          "must",      "credibility-focused"),
    NarrativeSlot("financials",      "table",       "Projections + assumptions",                "must",      "realistic"),
    NarrativeSlot("ask",             "stat-hero",   "Round size + use of funds",                 "must",      "clear"),
    NarrativeSlot("contact",         "title-only",  "Thank-you + next steps",                    "must",      "professional"),
]

_GROWTH_DECK: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Growth strategy + company",                "must",      "metrics-driven, ambitious"),
    NarrativeSlot("current_state",    "stat-hero",   "Where we are today",                       "must",      "factual"),
    NarrativeSlot("growth_metrics",   "chart-focus", "Key growth KPIs",                          "must",      "data-heavy"),
    NarrativeSlot("growth_drivers",  "grid-3",      "What drives growth",                       "must",      "strategic"),
    NarrativeSlot("strategy",        "process",     "Growth strategy",                          "must",      "structured"),
    NarrativeSlot("experiments",     "two-column",  "Growth experiments + learnings",            "important", "data-driven"),
    NarrativeSlot("market_expansion", "comparison",  "Expansion opportunities",                   "important", "ambitious"),
    NarrativeSlot("team",            "grid-3",      "Growth team structure",                    "important", "operational"),
    NarrativeSlot("resource_needs",  "table",       "Resources to execute",                      "must",      "realistic"),
    NarrativeSlot("timeline",        "timeline",    "Growth timeline",                          "must",      "structured"),
    NarrativeSlot("next_steps",      "title-only",  "Immediate actions",                        "must",      "actionable"),
]

_MARKET_ANALYSIS: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Market analysis + focus",                   "must",      "research-driven, analytical"),
    NarrativeSlot("executive_summary","stat-hero", "Key market insights",                       "must",      "decisive"),
    NarrativeSlot("market_size",      "chart-focus", "TAM / SAM / SOM + CAGR",                    "must",      "data-driven"),
    NarrativeSlot("market_trends",    "grid-3",      "Key market trends",                        "must",      "insightful"),
    NarrativeSlot("customer_segments","comparison",  "Target customer segments",                 "must",      "segmented"),
    NarrativeSlot("competitive_landscape","diagram", "Competitive landscape",                     "must",      "comprehensive"),
    NarrativeSlot("market_dynamics",  "two-column",  "Market forces + dynamics",                 "important", "analytical"),
    NarrativeSlot("opportunities",    "bullet-points","Market opportunities",                    "must",      "strategic"),
    NarrativeSlot("threats",         "bullet-points","Market threats + risks",                   "important", "candid"),
    NarrativeSlot("recommendations", "title-only",  "Strategic recommendations",                 "must",      "actionable"),
]

_COMPETITIVE_ANALYSIS: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Competitive analysis + company",            "must",      "positioning-focused"),
    NarrativeSlot("market_overview",  "stat-hero",   "Market position summary",                   "must",      "strategic"),
    NarrativeSlot("competitors",      "grid-3",      "Key competitors overview",                 "must",      "comprehensive"),
    NarrativeSlot("feature_matrix",   "comparison",  "Feature comparison matrix",                 "must",      "detailed"),
    NarrativeSlot("positioning",      "diagram",     "Competitive positioning",                   "must",      "strategic"),
    NarrativeSlot("differentiators",  "two-column",  "Our unique differentiators",                "must",      "clear, compelling"),
    NarrativeSlot("moat",            "process",     "Competitive moat",                         "must",      "strategic"),
    NarrativeSlot("threats",          "bullet-points","Competitive threats",                      "important", "candid"),
    NarrativeSlot("opportunities",    "bullet-points","Competitive opportunities",                "must",      "strategic"),
    NarrativeSlot("next_steps",      "title-only",  "Strategic next steps",                      "must",      "actionable"),
]

_TEAM_DECK: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Team + company",                           "must",      "credibility-focused"),
    NarrativeSlot("mission",         "stat-hero",   "Company mission + vision",                 "must",      "inspiring"),
    NarrativeSlot("founders",        "grid-3",      "Founders + backgrounds",                    "must",      "credibility-focused"),
    NarrativeSlot("leadership",      "grid-3",      "Leadership team",                          "must",      "credibility-focused"),
    NarrativeSlot("org_structure",   "diagram",     "Organizational structure",                  "important", "clear"),
    NarrativeSlot("culture",         "two-column",  "Company culture + values",                  "important", "authentic"),
    NarrativeSlot("advisors",        "grid-3",      "Advisory board",                           "optional",  "credibility"),
    NarrativeSlot("hiring_plan",     "timeline",    "Hiring roadmap",                            "important", "forward-looking"),
    NarrativeSlot("contact",         "title-only",  "Team contact + opportunities",             "must",      "open"),
]

_FINANCIAL_PROJECTION: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Financial projections + company",            "must",      "financial, professional"),
    NarrativeSlot("executive_summary","stat-hero", "Financial summary",                         "must",      "decisive"),
    NarrativeSlot("assumptions",      "bullet-points","Key assumptions",                         "must",      "transparent"),
    NarrativeSlot("revenue",          "chart-focus", "Revenue projections",                      "must",      "data-driven"),
    NarrativeSlot("expenses",        "table",       "Expense breakdown",                        "must",      "detailed"),
    NarrativeSlot("unit_economics",  "grid-3",      "Unit economics analysis",                   "must",      "rigorous"),
    NarrativeSlot("cash_flow",       "chart-focus", "Cash flow projections",                     "must",      "critical"),
    NarrativeSlot("sensitivity",     "comparison",  "Sensitivity analysis",                      "important", "comprehensive"),
    NarrativeSlot("scenarios",       "table",       "Best / base / worst case",                   "important", "realistic"),
    NarrativeSlot("funding_needs",   "stat-hero",   "Funding requirements",                      "must",      "clear"),
    NarrativeSlot("contact",         "title-only",  "Financial contact",                         "must",      "accessible"),
]

_PRODUCT_ROADMAP: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Product roadmap + company",                 "must",      "visionary, strategic"),
    NarrativeSlot("vision",          "stat-hero",   "Product vision + strategy",                 "must",      "inspiring"),
    NarrativeSlot("current_state",    "two-column",  "Current product state",                    "must",      "factual"),
    NarrativeSlot("near_term",       "timeline",    "3-month roadmap",                          "must",      "concrete"),
    NarrativeSlot("mid_term",        "timeline",    "6-12 month roadmap",                        "must",      "strategic"),
    NarrativeSlot("long_term",       "timeline",    "12-24 month roadmap",                       "important", "visionary"),
    NarrativeSlot("prioritization",  "process",     "Prioritization framework",                   "important", "strategic"),
    NarrativeSlot("resource_needs",  "grid-3",      "Resources to execute",                      "must",      "realistic"),
    NarrativeSlot("risks",           "bullet-points","Risks + mitigations",                       "important", "candid"),
    NarrativeSlot("contact",         "title-only",  "Product contact",                          "must",      "accessible"),
]

_MILESTONE_DECK: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Milestones + company",                      "must",      "achievement-focused"),
    NarrativeSlot("executive_summary","stat-hero", "Key achievements summary",                   "must",      "celebratory"),
    NarrativeSlot("year_overview",    "chart-focus", "Year at a glance metrics",                   "must",      "data-driven"),
    NarrativeSlot("product_milestones","timeline",  "Product milestones",                        "must",      "chronological"),
    NarrativeSlot("business_milestones","timeline", "Business milestones",                       "must",      "chronological"),
    NarrativeSlot("team_milestones",  "grid-3",      "Team achievements",                         "important", "human-focused"),
    NarrativeSlot("customer_wins",    "grid-3",      "Customer milestones",                       "must",      "credibility"),
    NarrativeSlot("awards",          "bullet-points","Awards + recognition",                      "optional",  "credibility"),
    NarrativeSlot("lessons",          "two-column",  "Key learnings",                             "important", "reflective"),
    NarrativeSlot("next_steps",      "title-only",  "Next milestones",                           "must",      "forward-looking"),
]

_CRISIS_MANAGEMENT: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Crisis response + company",                 "must",      "transparent, accountable"),
    NarrativeSlot("situation",        "stat-hero",   "Current situation",                        "must",      "factual, direct"),
    NarrativeSlot("timeline",        "timeline",    "What happened when",                       "must",      "chronological"),
    NarrativeSlot("impact",           "two-column",  "Impact assessment",                        "must",      "comprehensive"),
    NarrativeSlot("root_cause",       "bullet-points","Root cause analysis",                     "must",      "analytical"),
    NarrativeSlot("response",         "process",     "Immediate response actions",                "must",      "actionable"),
    NarrativeSlot("remediation",     "grid-3",      "Remediation steps",                        "must",      "structured"),
    NarrativeSlot("prevention",      "bullet-points","Prevention measures",                      "must",      "proactive"),
    NarrativeSlot("communication",   "two-column",  "Communication plan",                       "must",      "transparent"),
    NarrativeSlot("commitment",      "title-only",  "Commitment to resolution",                  "must",      "accountable"),
]

_EXPANSION_PLAN: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Expansion plan + company",                  "must",      "ambitious, strategic"),
    NarrativeSlot("executive_summary","stat-hero", "Expansion opportunity summary",              "must",      "compelling"),
    NarrativeSlot("current_footprint","chart-focus", "Current market footprint",                  "must",      "data-driven"),
    NarrativeSlot("expansion_markets","grid-3",     "Target expansion markets",                  "must",      "strategic"),
    NarrativeSlot("market_entry",     "process",     "Market entry strategy",                     "must",      "structured"),
    NarrativeSlot("resource_needs",  "table",       "Resources for expansion",                   "must",      "realistic"),
    NarrativeSlot("timeline",        "timeline",    "Expansion timeline",                       "must",      "structured"),
    NarrativeSlot("risks",           "bullet-points","Expansion risks + mitigations",             "important", "candid"),
    NarrativeSlot("success_metrics",  "chart-focus", "Success metrics",                          "must",      "measurable"),
    NarrativeSlot("next_steps",      "title-only",  "Immediate actions",                        "must",      "actionable"),
]

_ADVISORY_BOARD: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Advisory board + company",                  "must",      "credibility-focused"),
    NarrativeSlot("company_overview", "two-column",  "Company + mission",                         "must",      "clear"),
    NarrativeSlot("advisory_mission","stat-hero",   "Advisory board mission",                     "must",      "strategic"),
    NarrativeSlot("advisors",         "grid-3",      "Advisors + backgrounds",                    "must",      "credibility-focused"),
    NarrativeSlot("value_add",       "two-column",  "Value advisors bring",                      "must",      "clear"),
    NarrativeSlot("engagement",      "process",     "Advisor engagement model",                  "important", "structured"),
    NarrativeSlot("structure",        "diagram",     "Advisory board structure",                  "important", "clear"),
    NarrativeSlot("compensation",    "table",       "Advisor compensation",                      "optional",  "transparent"),
    NarrativeSlot("contact",         "title-only",  "Advisory contact",                          "must",      "accessible"),
]

_STRATEGIC_PARTNERSHIP: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Strategic partnership + companies",         "must",      "enterprise, professional"),
    NarrativeSlot("about_us",         "two-column",  "Who we are + capabilities",                "must",      "credibility-focused"),
    NarrativeSlot("about_you",        "two-column",  "Partner company overview",                  "must",      "partner-focused"),
    NarrativeSlot("strategic_fit",   "diagram",     "Strategic alignment",                       "must",      "mutual benefit"),
    NarrativeSlot("partnership_model","process",     "Partnership structure",                     "must",      "clear"),
    NarrativeSlot("value_proposition","grid-3",     "Value for both parties",                    "must",      "win-win"),
    NarrativeSlot("integration",      "diagram",     "Technical + business integration",          "important", "concrete"),
    NarrativeSlot("governance",      "bullet-points","Governance structure",                     "important", "structured"),
    NarrativeSlot("financials",      "table",       "Financial terms",                          "important", "transparent"),
    NarrativeSlot("next_steps",      "title-only",  "Path to partnership",                      "must",      "actionable"),
]

_PRE_SEED_PITCH: list[NarrativeSlot] = [
    NarrativeSlot("title",            "title-only",  "Company + founding vision",                 "must",      "visionary, founder-led"),
    NarrativeSlot("founder_story",   "two-column",  "Why we started + personal journey",         "must",      "authentic, narrative"),
    NarrativeSlot("problem",          "two-column",  "Problem we're solving",                    "must",      "relatable, urgent"),
    NarrativeSlot("insight",          "stat-hero",   "Unique insight + opportunity",              "must",      "compelling"),
    NarrativeSlot("solution",         "image-full",  "Our solution concept",                      "must",      "clear, exciting"),
    NarrativeSlot("market",          "stat-hero",   "Market opportunity",                       "must",      "ambitious"),
    NarrativeSlot("traction",         "chart-focus", "Early validation + proof points",            "must",      "proof-backed"),
    NarrativeSlot("team",            "grid-3",      "Founders + why this team",                 "must",      "credibility-focused"),
    NarrativeSlot("ask",             "stat-hero",   "Pre-seed ask + use of funds",               "must",      "clear, specific"),
    NarrativeSlot("roadmap",         "timeline",    "12-month roadmap",                          "important", "realistic"),
    NarrativeSlot("contact",         "title-only",  "Thank-you + contact",                      "must",      "grateful"),
]


NARRATIVE_ARCS: dict[str, list[NarrativeSlot]] = {
    "pitch_deck":       _PITCH_DECK,
    "investor_update":  _INVESTOR_UPDATE,
    "sales_deck":       _SALES_DECK,
    "product_launch":   _PRODUCT_LAUNCH,
    "quarterly_review": _QUARTERLY_REVIEW,
    "board_meeting":    _BOARD_MEETING,
    "conference_talk":  _CONFERENCE_TALK,
    "training":         _TRAINING,
    "project_proposal": _PROJECT_PROPOSAL,
    "case_study":       _CASE_STUDY,
    "company_overview": _COMPANY_OVERVIEW,
    "demo_day":         _DEMO_DAY,
    "educational":      _EDUCATIONAL,
    "internal_memo":    _INTERNAL_MEMO,
    "custom":           _CUSTOM,
    # Standard Mode Pitch Deck Purposes
    "deep_tech":        _DEEP_TECH,
    "vc_pitch":         _VC_PITCH,
    "executive_brief":  _EXECUTIVE_BRIEF,
    "trust_compliance": _TRUST_COMPLIANCE,
    "cinematic_keynote": _CINEMATIC_KEYNOTE,
    "seed_round":       _SEED_ROUND,
    "series_a":         _SERIES_A,
    "partnership":      _PARTNERSHIP,
    "customer_case":    _CUSTOMER_CASE,
    "fundraising_roadshow": _FUNDRAISING_ROADSHOW,
    "growth_deck":      _GROWTH_DECK,
    "market_analysis":  _MARKET_ANALYSIS,
    "competitive_analysis": _COMPETITIVE_ANALYSIS,
    "team_deck":        _TEAM_DECK,
    "financial_projection": _FINANCIAL_PROJECTION,
    "product_roadmap":  _PRODUCT_ROADMAP,
    "milestone_deck":   _MILESTONE_DECK,
    "crisis_management": _CRISIS_MANAGEMENT,
    "expansion_plan":   _EXPANSION_PLAN,
    "advisory_board":   _ADVISORY_BOARD,
    "strategic_partnership": _STRATEGIC_PARTNERSHIP,
    "pre_seed_pitch":   _PRE_SEED_PITCH,
}


# \u2550\u2550 VOICE PROFILES \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

VOICE_PROFILES: dict[str, VoiceProfile] = {
    "pitch_deck":       VoiceProfile(0.7, 0.55, 0.90, 0.70, 0.45),
    "investor_update":  VoiceProfile(0.8, 0.60, 0.40, 0.55, 0.30),
    "sales_deck":       VoiceProfile(0.65, 0.55, 0.95, 0.75, 0.55),
    "product_launch":   VoiceProfile(0.65, 0.60, 0.85, 0.80, 0.50),
    "quarterly_review": VoiceProfile(0.85, 0.65, 0.30, 0.50, 0.20),
    "board_meeting":    VoiceProfile(0.90, 0.70, 0.30, 0.65, 0.15),
    "conference_talk":  VoiceProfile(0.55, 0.65, 0.50, 0.40, 0.60),
    "training":         VoiceProfile(0.55, 0.55, 0.20, 0.40, 0.55),
    "project_proposal": VoiceProfile(0.85, 0.65, 0.55, 0.60, 0.25),
    "case_study":       VoiceProfile(0.75, 0.45, 0.65, 0.30, 0.40),
    "company_overview": VoiceProfile(0.75, 0.45, 0.55, 0.30, 0.45),
    "demo_day":         VoiceProfile(0.55, 0.45, 0.95, 0.90, 0.55),
    "educational":      VoiceProfile(0.55, 0.55, 0.15, 0.20, 0.50),
    "internal_memo":    VoiceProfile(0.85, 0.65, 0.25, 0.85, 0.10),
    "custom":           VoiceProfile(0.65, 0.55, 0.45, 0.45, 0.40),
    # Standard Mode Pitch Deck Purposes
    "deep_tech":        VoiceProfile(0.60, 0.95, 0.30, 0.40, 0.20),
    "vc_pitch":         VoiceProfile(0.60, 0.50, 0.95, 0.85, 0.40),
    "executive_brief":  VoiceProfile(0.95, 0.60, 0.40, 0.70, 0.15),
    "trust_compliance": VoiceProfile(0.95, 0.70, 0.25, 0.50, 0.10),
    "cinematic_keynote": VoiceProfile(0.30, 0.40, 0.80, 0.60, 0.90),
    "seed_round":       VoiceProfile(0.55, 0.45, 0.90, 0.70, 0.60),
    "series_a":         VoiceProfile(0.70, 0.55, 0.85, 0.65, 0.30),
    "partnership":      VoiceProfile(0.75, 0.55, 0.60, 0.50, 0.40),
    "customer_case":    VoiceProfile(0.70, 0.40, 0.55, 0.30, 0.50),
    "fundraising_roadshow": VoiceProfile(0.80, 0.55, 0.90, 0.75, 0.25),
    "growth_deck":      VoiceProfile(0.60, 0.50, 0.70, 0.80, 0.20),
    "market_analysis":  VoiceProfile(0.85, 0.70, 0.30, 0.50, 0.15),
    "competitive_analysis": VoiceProfile(0.75, 0.60, 0.40, 0.50, 0.20),
    "team_deck":        VoiceProfile(0.65, 0.40, 0.50, 0.40, 0.50),
    "financial_projection": VoiceProfile(0.90, 0.70, 0.30, 0.60, 0.10),
    "product_roadmap":  VoiceProfile(0.60, 0.55, 0.50, 0.65, 0.30),
    "milestone_deck":   VoiceProfile(0.70, 0.45, 0.55, 0.50, 0.60),
    "crisis_management": VoiceProfile(0.85, 0.60, 0.20, 0.95, 0.30),
    "expansion_plan":   VoiceProfile(0.75, 0.60, 0.70, 0.70, 0.25),
    "advisory_board":   VoiceProfile(0.80, 0.50, 0.40, 0.50, 0.20),
    "strategic_partnership": VoiceProfile(0.85, 0.60, 0.50, 0.60, 0.25),
    "pre_seed_pitch":   VoiceProfile(0.50, 0.40, 0.95, 0.80, 0.70),
}


# \u2550\u2550 PURPOSE BOUNDARIES \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#
# Intents that must NEVER appear in the output deck for the given
# purpose. Used post-parse to detect cross-purpose contamination
# (LLMs trained heavily on pitch decks often slip ``competition`` or
# ``ask`` into educational / training / memo decks). The validator
# logs and downgrades \u2014 it does not raise \u2014 so a single contaminated
# slide does not abort the whole generation.

_PITCH_INTENTS = {"problem", "solution", "market", "traction", "ask",
                  "competition", "business_model", "financials"}

FORBIDDEN_INTENTS_BY_PURPOSE: dict[str, frozenset[str]] = {
    "educational":      frozenset({"competition", "ask", "traction",
                                   "business_model", "financials",
                                   "fundraising"}),
    "training":         frozenset({"competition", "ask", "traction",
                                   "business_model", "financials",
                                   "fundraising"}),
    "internal_memo":    frozenset({"testimonial", "ask", "competition",
                                   "fundraising"}),
    "case_study":       frozenset({"ask", "fundraising"}),
    "company_overview": frozenset({"ask", "fundraising"}),
    "conference_talk":  frozenset({"ask", "fundraising", "competition"}),
    # Pitch-shaped purposes have no forbidden set — they may legitimately
    # use any of the canonical pitch intents.
    "pitch_deck":       frozenset(),
    "investor_update":  frozenset(),
    "sales_deck":       frozenset({"ask", "fundraising"}),
    "product_launch":   frozenset({"ask", "fundraising"}),
    "quarterly_review": frozenset({"ask", "fundraising"}),
    "board_meeting":    frozenset({"ask", "fundraising"}),
    "demo_day":         frozenset(),
    "project_proposal": frozenset({"fundraising"}),
    "custom":           frozenset(),
    # Standard Mode Pitch Deck Purposes
    "deep_tech":        frozenset(),
    "vc_pitch":         frozenset(),
    "executive_brief":  frozenset({"fundraising"}),
    "trust_compliance": frozenset({"fundraising", "ask"}),
    "cinematic_keynote": frozenset(),
    "seed_round":       frozenset(),
    "series_a":         frozenset(),
    "partnership":      frozenset({"fundraising"}),
    "customer_case":    frozenset({"fundraising"}),
    "fundraising_roadshow": frozenset(),
    "growth_deck":      frozenset(),
    "market_analysis":  frozenset(),
    "competitive_analysis": frozenset(),
    "team_deck":        frozenset(),
    "financial_projection": frozenset(),
    "product_roadmap":  frozenset(),
    "milestone_deck":   frozenset(),
    "crisis_management": frozenset(),
    "expansion_plan":   frozenset(),
    "advisory_board":   frozenset(),
    "strategic_partnership": frozenset(),
    "pre_seed_pitch":   frozenset(),
}


# \u2550\u2550 PUBLIC API \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

_PRIORITY_RANK: dict[SlotPriority, int] = {"must": 0, "important": 1, "optional": 2}


def get_arc_for_purpose(purpose: Optional[str]) -> list[NarrativeSlot]:
    """Return the canonical arc for ``purpose``.

    Falls back to ``custom`` (a generic SCQA arc) when the purpose is
    ``None``, empty, or not present in :data:`NARRATIVE_ARCS`.
    The returned list is a fresh copy \u2014 callers may mutate it freely.
    """
    key = (purpose or "").strip().lower() or "custom"
    arc = NARRATIVE_ARCS.get(key)
    if arc is None:
        logger.info(
            "narrative_arc_fallback_to_custom",
            purpose=purpose,
            reason="unknown_purpose",
        )
        arc = NARRATIVE_ARCS["custom"]
    return list(arc)


def get_voice_profile(purpose: Optional[str]) -> VoiceProfile:
    """Return the voice profile for ``purpose``, or the ``custom`` default."""
    key = (purpose or "").strip().lower() or "custom"
    return VOICE_PROFILES.get(key, VOICE_PROFILES["custom"])


def get_forbidden_intents(purpose: Optional[str]) -> frozenset[str]:
    """Return the set of intents that must not appear for ``purpose``."""
    key = (purpose or "").strip().lower() or "custom"
    return FORBIDDEN_INTENTS_BY_PURPOSE.get(key, frozenset())


def _trim_by_priority(
    arc: list[NarrativeSlot], requested: int
) -> list[NarrativeSlot]:
    """Drop slots in priority order (optional, then important) until
    ``len(arc) == requested``. ``must`` slots are never dropped.

    The original arc order is preserved among kept slots.
    """
    if requested >= len(arc):
        return list(arc)
    if requested <= 0:
        # Defensive: callers should already clamp, but never return empty.
        requested = 1

    # Keep all ``must`` slots regardless. If there are more must-slots
    # than requested, keep the first ``requested`` of them \u2014 better to
    # have a coherent prefix than a truncated tail.
    must_indices = [i for i, s in enumerate(arc) if s.priority == "must"]
    if len(must_indices) >= requested:
        keep = set(must_indices[:requested])
        return [s for i, s in enumerate(arc) if i in keep]

    keep = set(must_indices)
    needed = requested - len(must_indices)

    # Then add ``important`` slots in original order until full.
    for i, s in enumerate(arc):
        if needed <= 0:
            break
        if i in keep:
            continue
        if s.priority == "important":
            keep.add(i)
            needed -= 1

    # Finally, fill with ``optional`` slots if we still need more.
    if needed > 0:
        for i, s in enumerate(arc):
            if needed <= 0:
                break
            if i in keep:
                continue
            if s.priority == "optional":
                keep.add(i)
                needed -= 1

    return [s for i, s in enumerate(arc) if i in keep]


def _expand(arc: list[NarrativeSlot], requested: int) -> list[NarrativeSlot]:
    """Pad ``arc`` to length ``requested`` by duplicating the densest
    middle slots with a numeric suffix so the planner can fill them
    with related-but-distinct content (e.g. ``concept_1`` \u2192
    ``concept_1``, ``concept_1_b``).

    Anchors (first and last slot) are never duplicated.
    """
    if requested <= len(arc):
        return list(arc)

    out: list[NarrativeSlot] = list(arc)
    # Round-robin over the middle slots, skipping the first (title-like)
    # and last (close/CTA) which must stay unique.
    middle_pool: list[int] = list(range(1, max(1, len(arc) - 1)))
    if not middle_pool:
        middle_pool = list(range(len(arc)))

    cursor = 0
    suffix_counts: dict[str, int] = {}
    while len(out) < requested:
        src_idx = middle_pool[cursor % len(middle_pool)]
        src = arc[src_idx]
        suffix_counts[src.intent] = suffix_counts.get(src.intent, 0) + 1
        new_intent = f"{src.intent}_extra_{suffix_counts[src.intent]}"
        new_slot = NarrativeSlot(
            intent=new_intent,
            suggested_layout=src.suggested_layout,
            brief=f"{src.brief} (additional detail)",
            priority="optional",
            voice_guidance=src.voice_guidance,
        )
        # Insert near the source so the narrative stays adjacent.
        # We keep the close-slot (last) at the end.
        insert_at = max(1, len(out) - 1)
        out.insert(insert_at, new_slot)
        cursor += 1
    return out


def scale_arc(
    arc: Iterable[NarrativeSlot], requested_count: int
) -> list[NarrativeSlot]:
    """Return a copy of ``arc`` adjusted to exactly ``requested_count``
    slots, honouring priority tags.

    * ``requested_count == len(arc)`` \u2192 unchanged copy.
    * ``requested_count <  len(arc)`` \u2192 ``_trim_by_priority``.
    * ``requested_count >  len(arc)`` \u2192 ``_expand`` with elaborated slots.

    The function always returns at least one slot. The result length
    equals ``requested_count`` exactly (clamped to ``[1, 50]``).
    """
    arc_list = list(arc)
    if not arc_list:
        # Should never happen \u2014 the library always provides a non-empty
        # arc \u2014 but be defensive so callers never get an empty list.
        arc_list = list(NARRATIVE_ARCS["custom"])

    n = max(1, min(50, int(requested_count)))
    if n == len(arc_list):
        return list(arc_list)
    if n < len(arc_list):
        out = _trim_by_priority(arc_list, n)
    else:
        out = _expand(arc_list, n)

    # Defense-in-depth: enforce the exact length.
    if len(out) > n:
        out = out[:n]
    elif len(out) < n:
        # Pad with the last slot's intent under a "_pad_" suffix.
        # This branch should be unreachable; keep it loud if hit.
        logger.warning(
            "scale_arc_undershoot",
            requested=n,
            actual=len(out),
        )
        last = out[-1]
        i = 1
        while len(out) < n:
            out.insert(
                max(1, len(out) - 1),
                NarrativeSlot(
                    intent=f"{last.intent}_pad_{i}",
                    suggested_layout=last.suggested_layout,
                    brief=last.brief,
                    priority="optional",
                    voice_guidance=last.voice_guidance,
                ),
            )
            i += 1
    return out


def arc_to_planner_payload(
    arc: list[NarrativeSlot],
) -> list[dict[str, str]]:
    """Serialize an arc for inclusion in the planner's user message.

    Keeps only the fields the LLM actually needs \u2014 omits ``priority``
    because by the time we serialize, ``scale_arc`` has already trimmed
    to the exact requested count and the planner's job is purely to
    fill, not to re-prioritize.
    """
    return [
        {
            "intent":           s.intent,
            "suggested_layout": s.suggested_layout,
            "brief":            s.brief,
            "voice":            s.voice_guidance,
        }
        for s in arc
    ]


__all__ = [
    "NarrativeSlot",
    "VoiceProfile",
    "NARRATIVE_ARCS",
    "VOICE_PROFILES",
    "FORBIDDEN_INTENTS_BY_PURPOSE",
    "get_arc_for_purpose",
    "get_voice_profile",
    "get_forbidden_intents",
    "scale_arc",
    "arc_to_planner_payload",
]
