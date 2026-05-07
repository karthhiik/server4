"""
Phase 12 — Few-shot prompt injection.

Curated reference slide outputs the writer can use as SHAPE anchors
(headline cadence, subheadline framing, bullet density, body voice,
structured-block populations). They are **not** templates: every anchor
is wrapped in an explicit "REFERENCE EXAMPLE — illustrative shape only,
DO NOT copy facts, names, or numbers" block so the LLM cannot leak the
example data into the user's actual slide.

Design constraints:
- Anchors are keyed by `intent` (and optionally `layout_hint`) and
  return at most ONE anchor per writer call to keep token cost flat.
- Numbers and company names in anchors are **publicly known reference
  facts** (e.g. Stripe scale, Slack story arc) used here only to
  demonstrate cadence — never as content the model should emit.
- The anchor block is appended to the USER message (after the design
  brief, before the closing instruction), so it never mutates the
  shared system prefix used for the LLM provider's prompt cache.

No fake/dummy data:
- The writer's system prompt already enforces "STRUCTURED USER INPUT
  is authoritative". The few-shot anchor block adds a second layer of
  defence: every anchor explicitly says "DO NOT copy these names or
  numbers".
- `format_few_shot()` returns "" when no anchor matches — the slide
  is then written without an anchor (graceful degradation).
"""
from __future__ import annotations

import json
from typing import Optional


# ── Anchor library ─────────────────────────────────────────────────
# Each entry: {
#   "intent": str,                # canonical intent
#   "layouts": tuple[str, ...],   # layout_hints this anchor fits best
#   "skeleton": dict,             # mock skeleton echoed in the prompt
#   "output": dict,               # the ideal slide JSON
# }
# Anchors are intentionally short — the writer should learn *cadence*
# from them, not paragraph length.

_ANCHORS: list[dict] = [
    # ── title ────────────────────────────────────────────────────
    {
        "intent": "title",
        "layouts": ("title-slide", "title-only"),
        "skeleton": {
            "intent": "title",
            "headline_target": "Open the deck with a thesis-shaped value prop",
            "key_points": ["company_name", "one-line value prop"],
            "density_target": "low",
            "layout_hint": "title-slide",
        },
        "output": {
            "headline": "Stripe — Payments Infrastructure For The Internet",
            "subheadline": "Programmable APIs that move money for millions of businesses globally.",
            "body": (
                "Stripe builds the economic infrastructure that lets companies "
                "accept payments, send payouts, and run financial operations through "
                "a single set of APIs — replacing brittle in-house billing stacks."
            ),
            "speaker_notes": (
                "Open by anchoring on the category (payments infrastructure) and the "
                "scale (millions of businesses). Then transition into the problem we "
                "solve for the next builder generation."
            ),
        },
    },
    # ── problem ──────────────────────────────────────────────────
    {
        "intent": "problem",
        "layouts": ("bullet-points", "two-column", "title-only"),
        "skeleton": {
            "intent": "problem",
            "headline_target": "Make the pain concrete and quantified",
            "key_points": [
                "manual workflow waste",
                "error-prone reconciliation",
                "weeks-long close cycles",
            ],
            "density_target": "medium",
            "layout_hint": "bullet-points",
        },
        "output": {
            "headline": "Finance Closes Take 12 Days, Not 2",
            "subheadline": "SMBs lose a full work-week every month to manual reconciliation.",
            "bullets": [
                "Spreadsheets and bank exports break under multi-entity reporting demands.",
                "Mismatched ledgers force CFOs to redo close work three times a quarter.",
                "Founders trade growth hours for bookkeeping and audit prep weekly.",
            ],
            "body": (
                "Modern SMBs operate across Stripe, Shopify, payroll, and three banks — "
                "yet their finance stack still ends in a spreadsheet. The result is a "
                "monthly close that drags into the second week and produces numbers "
                "leadership cannot trust."
            ),
            "speaker_notes": (
                "Anchor the pain in the close cycle delta (12 days vs 2). Make the "
                "audience feel the cost: founders trading growth hours for ledger work."
            ),
        },
    },
    # ── solution ─────────────────────────────────────────────────
    {
        "intent": "solution",
        "layouts": ("two-column", "bullet-points", "image-right"),
        "skeleton": {
            "intent": "solution",
            "headline_target": "State the solution as a concrete capability",
            "key_points": [
                "automated reconciliation",
                "real-time ledger",
                "audit-ready exports",
            ],
            "density_target": "medium",
            "layout_hint": "two-column",
        },
        "output": {
            "headline": "Real-Time Books, Closed In Minutes",
            "subheadline": "One ledger pulls every payment rail and reconciles continuously.",
            "bullets": [
                "Direct connectors to Stripe, Shopify, banks, and payroll providers.",
                "Continuous reconciliation eliminates month-end matching marathons.",
                "Audit-ready exports generated on demand for any reporting period.",
            ],
            "body": (
                "Instead of a once-a-month batch job, the platform reconciles "
                "transactions as they land. CFOs see a live trial balance, and the "
                "monthly close becomes a sign-off — not a project."
            ),
            "speaker_notes": (
                "Frame the shift from batch close to continuous close. The audience "
                "should leave understanding that the close is no longer an event."
            ),
        },
    },
    # ── how_it_works ─────────────────────────────────────────────
    {
        "intent": "how_it_works",
        "layouts": ("timeline", "process", "diagram"),
        "skeleton": {
            "intent": "how_it_works",
            "headline_target": "Show the mechanism in 3 ordered steps",
            "key_points": ["connect data", "auto-reconcile", "publish reports"],
            "density_target": "medium",
            "layout_hint": "timeline",
        },
        "output": {
            "headline": "From Connection To Close In Three Steps",
            "subheadline": "Connect your stack once; the ledger maintains itself thereafter.",
            "timeline": {
                "orientation": "horizontal",
                "events": [
                    {
                        "date": "Step 1",
                        "title": "Connect",
                        "description": "OAuth into bank, payments, payroll, and commerce systems in one click.",
                    },
                    {
                        "date": "Step 2",
                        "title": "Reconcile",
                        "description": "Matching engine pairs transactions to ledger entries continuously.",
                    },
                    {
                        "date": "Step 3",
                        "title": "Report",
                        "description": "Audit-ready financials publish automatically every period.",
                    },
                ],
            },
            "speaker_notes": (
                "Walk through the three steps quickly — Connect, Reconcile, Report. "
                "Emphasize that step three happens with no human in the loop."
            ),
        },
    },
    # ── market ───────────────────────────────────────────────────
    {
        "intent": "market",
        "layouts": ("stat-hero", "chart-focus"),
        "skeleton": {
            "intent": "market",
            "headline_target": "Quantify TAM/SAM/SOM with credible sources",
            "key_points": ["TAM", "growth rate", "segment of focus"],
            "density_target": "low",
            "layout_hint": "stat-hero",
        },
        "output": {
            "headline": "$72B SMB Accounting, 11% YoY",
            "subheadline": "32M SMBs in target geographies still operate on spreadsheet-led close.",
            "stat_blocks": [
                {"value": "$72B", "label": "Global SMB accounting TAM"},
                {"value": "11%", "label": "YoY market growth (2020-2024)"},
                {"value": "32M", "label": "SMBs in addressable segment"},
            ],
            "speaker_notes": (
                "Lead with TAM, follow with growth rate, then narrow to the addressable "
                "SMB segment we actually serve. Cite the source the analyst will check."
            ),
            "citations": [
                {"url": "https://example-research.org/smb-accounting-2024", "title": "SMB accounting market sizing"}
            ],
        },
    },
    # ── traction ────────────────────────────────────────────────
    {
        "intent": "traction",
        "layouts": ("stat-hero", "chart-focus"),
        "skeleton": {
            "intent": "traction",
            "headline_target": "Lead with the metric that compounds",
            "key_points": ["ARR", "growth rate", "logo count"],
            "density_target": "low",
            "layout_hint": "stat-hero",
        },
        "output": {
            "headline": "$4.1M ARR, 18% MoM Growth",
            "subheadline": "240 paying SMBs, net revenue retention above 130 percent.",
            "stat_blocks": [
                {"value": "$4.1M", "label": "ARR (current)"},
                {"value": "18%", "label": "MoM growth (last 6 mo)"},
                {"value": "131%", "label": "Net revenue retention"},
            ],
            "speaker_notes": (
                "Open with ARR, then growth rate, then NRR. Investors read these three "
                "numbers as a compound proof point — do not bury them in prose."
            ),
        },
    },
    # ── business_model ───────────────────────────────────────────
    {
        "intent": "business_model",
        "layouts": ("two-column", "bullet-points", "table"),
        "skeleton": {
            "intent": "business_model",
            "headline_target": "Show pricing, buyer, and revenue logic",
            "key_points": ["pricing tier", "buyer persona", "expansion motion"],
            "density_target": "medium",
            "layout_hint": "two-column",
        },
        "output": {
            "headline": "Per-Seat SaaS, Expansion By Module",
            "subheadline": "CFOs sign on a base plan; finance teams expand into payroll and AP.",
            "bullets": [
                "Base plan at $299/month covers ledger and reconciliation core.",
                "AP automation and payroll add-ons drive 60% of net new revenue.",
                "Annual contracts default after a 14-day proof-of-value pilot.",
            ],
            "body": (
                "The CFO is the entry buyer because reconciliation pain is acute and "
                "the ROI is easy to model. Once live, individual function leads pull "
                "in adjacent modules — turning seat growth into module growth."
            ),
            "speaker_notes": (
                "Tell the land-and-expand story: CFO lands on close pain, function "
                "leads expand into AP and payroll. Mention the 14-day pilot."
            ),
        },
    },
    # ── competition ──────────────────────────────────────────────
    {
        "intent": "competition",
        "layouts": ("comparison", "table", "two-column"),
        "skeleton": {
            "intent": "competition",
            "headline_target": "Show the differentiated position",
            "key_points": ["incumbent", "new entrants", "our edge"],
            "density_target": "medium",
            "layout_hint": "comparison",
        },
        "output": {
            "headline": "Continuous Close Beats Batch Tools",
            "subheadline": "Incumbents export reports; we maintain the ledger in real time.",
            "comparison": {
                "columns": [
                    {
                        "title": "Legacy ERPs",
                        "items": [
                            "Monthly batch close",
                            "Manual reconciliation",
                            "Implementation in months",
                        ],
                        "highlight": False,
                    },
                    {
                        "title": "Spreadsheet stacks",
                        "items": [
                            "Free but error-prone",
                            "No audit trail",
                            "Breaks past 5 entities",
                        ],
                        "highlight": False,
                    },
                    {
                        "title": "Our platform",
                        "items": [
                            "Continuous reconciliation",
                            "Audit-ready by default",
                            "Live in 14 days",
                        ],
                        "highlight": True,
                    },
                ],
            },
            "speaker_notes": (
                "Position against legacy ERPs (slow, batch) and spreadsheet stacks "
                "(free, brittle). End on the live-in-14-days proof point."
            ),
        },
    },
    # ── go_to_market ─────────────────────────────────────────────
    {
        "intent": "go_to_market",
        "layouts": ("bullet-points", "two-column", "process"),
        "skeleton": {
            "intent": "go_to_market",
            "headline_target": "Show the customer acquisition motion",
            "key_points": ["channel", "ICP", "CAC payback"],
            "density_target": "medium",
            "layout_hint": "bullet-points",
        },
        "output": {
            "headline": "Bottom-Up Through Finance Communities",
            "subheadline": "Inbound from accountant networks, expansion via product-led trials.",
            "bullets": [
                "Top of funnel from CFO Slack groups and accounting marketplaces.",
                "Self-serve trial converts at 22 percent within 14 days.",
                "Outbound layered on enterprise accounts above 200-employee threshold.",
            ],
            "body": (
                "Acquisition starts where buyers already discuss tooling — finance "
                "communities and accountant marketplaces. The 14-day product trial "
                "carries the load, and outbound only fires for accounts large enough "
                "to need a sales-assisted motion."
            ),
            "speaker_notes": (
                "Lead with the inbound channel where buyers already gather, then "
                "show the 22 percent trial conversion before mentioning outbound."
            ),
        },
    },
    # ── technology ───────────────────────────────────────────────
    {
        "intent": "technology",
        "layouts": ("bullet-points", "diagram", "two-column"),
        "skeleton": {
            "intent": "technology",
            "headline_target": "Explain the moat or automation engine",
            "key_points": ["matching engine", "data graph", "ML feedback loop"],
            "density_target": "medium",
            "layout_hint": "bullet-points",
        },
        "output": {
            "headline": "Matching Engine Compounds With Every Ledger",
            "subheadline": "Per-tenant graph plus shared model lifts accuracy as we scale.",
            "bullets": [
                "Per-tenant transaction graph captures vendor, GL code, and timing patterns.",
                "Shared matching model trained across anonymized ledger graphs.",
                "Every confirmed match feeds the model nightly, lifting precision.",
            ],
            "body": (
                "Each customer's ledger is a private graph. The matching engine learns "
                "from confirmed matches across all tenants in an anonymized form — so "
                "accuracy improves for every customer as the network grows."
            ),
            "speaker_notes": (
                "Stress the network effect: accuracy compounds as more ledgers join. "
                "This is the moat: data scale that no incumbent can replicate."
            ),
        },
    },
    # ── team ─────────────────────────────────────────────────────
    {
        "intent": "team",
        "layouts": ("two-column", "bullet-points", "grid-3"),
        "skeleton": {
            "intent": "team",
            "headline_target": "Show founder/market fit",
            "key_points": ["founder backgrounds", "domain depth", "exits"],
            "density_target": "medium",
            "layout_hint": "two-column",
        },
        "output": {
            "headline": "Built Finance Tools At Stripe And Square",
            "subheadline": "Engineering and product leaders shipped reconciliation at scale before.",
            "bullets": [
                "CEO led Stripe's revenue recognition platform across 30+ markets.",
                "CTO ran ledger infrastructure at Square; one prior fintech exit.",
                "Head of Product owned QuickBooks SMB onboarding for four years.",
            ],
            "body": (
                "Three founders with a decade-plus building exactly the systems this "
                "product replaces. The team has lived the close-cycle pain at "
                "internet-scale fintechs and has shipped the technology before."
            ),
            "speaker_notes": (
                "Anchor on prior-art credibility: Stripe, Square, QuickBooks. End "
                "with the one-line 'we have shipped this before' takeaway."
            ),
        },
    },
    # ── financials ───────────────────────────────────────────────
    {
        "intent": "financials",
        "layouts": ("chart-focus", "table", "stat-hero"),
        "skeleton": {
            "intent": "financials",
            "headline_target": "Forward projection grounded in unit economics",
            "key_points": ["ARR projection", "gross margin", "burn"],
            "density_target": "medium",
            "layout_hint": "chart-focus",
        },
        "output": {
            "headline": "Path To $40M ARR By Year Three",
            "subheadline": "Gross margin holds above 78 percent across the projection window.",
            "chart": {
                "type": "bar",
                "data": [
                    {"label": "Y1", "value": 4.1},
                    {"label": "Y2", "value": 14.0},
                    {"label": "Y3", "value": 40.0},
                ],
            },
            "body": (
                "ARR projection compounds from $4.1M today to $40M by year three, "
                "driven by 18 percent monthly net new ARR and module expansion. "
                "Gross margin stays north of 78 percent across the window."
            ),
            "speaker_notes": (
                "Walk the bars left to right. Anchor each year on the underlying "
                "growth rate and the gross-margin floor."
            ),
        },
    },
    # ── ask ──────────────────────────────────────────────────────
    {
        "intent": "ask",
        "layouts": ("bullet-points", "stat-hero", "two-column"),
        "skeleton": {
            "intent": "ask",
            "headline_target": "What we want and what it unlocks",
            "key_points": ["round size", "use of funds", "milestone"],
            "density_target": "medium",
            "layout_hint": "bullet-points",
        },
        "output": {
            "headline": "Raising $12M To Reach $20M ARR",
            "subheadline": "Series A capital funds the 24 months of ARR compounding ahead.",
            "bullets": [
                "60 percent into go-to-market — sales, partnerships, accountant network.",
                "30 percent into engineering on the matching engine and AP module.",
                "10 percent reserved for senior finance and security hires.",
            ],
            "body": (
                "The round funds 24 months of disciplined growth: ARR from $4M to "
                "$20M, gross margin held above 78 percent, and the AP module shipped "
                "to the full base. We close the round with a Series B-ready story."
            ),
            "speaker_notes": (
                "Tie the dollar amount to the milestone (4M to 20M ARR). Walk the "
                "use-of-funds split. End on the Series B-ready exit state."
            ),
        },
    },
]


# Index for fast lookup. We key primarily on intent; layout is a tiebreaker.
_BY_INTENT: dict[str, list[dict]] = {}
for _a in _ANCHORS:
    _BY_INTENT.setdefault(_a["intent"], []).append(_a)


def _select_anchor(
    intent: str, layout_hint: Optional[str]
) -> Optional[dict]:
    """Pick the best anchor for a given (intent, layout_hint) pair.

    Returns None when no anchor is registered for the intent — the writer
    will then run without a few-shot block (graceful degradation).
    """
    if not intent:
        return None
    candidates = _BY_INTENT.get(intent.strip().lower())
    if not candidates:
        return None
    if layout_hint:
        layout_norm = layout_hint.strip().lower()
        for c in candidates:
            if layout_norm in c.get("layouts", ()):
                return c
    return candidates[0]


def format_few_shot(
    intent: str,
    layout_hint: Optional[str] = None,
) -> str:
    """Render the few-shot anchor block to be appended to the user message.

    Returns "" when no anchor is found. The caller decides whether to
    include the block; we always wrap the example in an unmistakable
    "DO NOT COPY" guard so the LLM cannot mistake the anchor data for
    the user's slide content.
    """
    anchor = _select_anchor(intent, layout_hint)
    if not anchor:
        return ""

    # Compact the JSON so the anchor block stays short (~250-400 tokens).
    skeleton_json = json.dumps(anchor["skeleton"], ensure_ascii=False)
    output_json = json.dumps(anchor["output"], ensure_ascii=False)

    block = (
        "\n--- REFERENCE EXAMPLE — illustrative SHAPE only ---\n"
        "The block below is a SHAPE reference for cadence and structure.\n"
        "DO NOT copy any company name, person name, dollar amount, "
        "percentage, or product detail from this example into the "
        "actual slide. Your slide MUST use the user's real company "
        "data and the scoped evidence above. The example exists only "
        "to show the style of headline, subheadline length, bullet "
        "voice, and which structured block to populate.\n"
        f"reference_skeleton: {skeleton_json}\n"
        f"reference_output: {output_json}\n"
        "--- END REFERENCE EXAMPLE ---\n"
    )
    return block


__all__ = ["format_few_shot", "_select_anchor", "_ANCHORS", "_BY_INTENT"]
