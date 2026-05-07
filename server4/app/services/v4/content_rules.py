"""V4 Content Rules — single source of truth for content-quality gates.

This module is imported by:
  - skeleton_planner  (pre-write template gate on planner headlines)
  - parallel_writer   (post-write template gate on writer headlines)
  - consensus/prompts (persona prompts quote the banned patterns)
  - critic_engine     (deterministic penalties and rewrite triggers)
  - slide_compiler    (hard gates for structural failures)

Rationale:
  Before this module existed, each stage shipped its own banned-phrase list,
  its own density rules, and its own data-slide checks. Drift across four
  prompt surfaces was the root cause of generic headlines like
  "Market Opportunity Today" and "Our Business Model" shipping to
  investors even when the premium writer prompt forbade them.

Design guarantees:
  * Pure Python, no LLM calls. Safe to call from any stage at any time.
  * Data-only dependencies (regex, typing, dataclasses). No project imports
    that would create cycles with the rest of v4.
  * Every pattern is case-insensitive.
  * Every function is total — no exceptions for bad input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional


# ── 1. Banned headline patterns ─────────────────────────────────────
# Headlines matching any of these regexes are "template headlines": they
# could belong to any startup, which is the exact failure mode we are
# trying to eliminate. Each entry is (compiled_regex, short_label, fix_hint).
# Labels feed into critic issues; fix_hints feed into rewrite prompts.

_BANNED_HEADLINE_RAW: list[tuple[str, str, str]] = [
    # Generic category labels the planner frequently emits.
    (r"^\s*market\s+opportunity(\s+today)?\s*$",
     "generic_market_headline",
     "Replace with a quantified market thesis (e.g. '$4.2B SMB Payments, Growing 18% YoY')."),
    (r"^\s*(our|the)\s+market(\s+opportunity)?\s*$",
     "generic_market_headline",
     "Replace with a quantified market thesis using user or research numbers."),
    (r"^\s*(our|the)\s+business\s+model\s*$",
     "generic_business_model_headline",
     "Replace with the concrete revenue mechanic (e.g. '$99/seat SaaS, 65% gross margin')."),
    (r"^\s*how\s+(it|the\s+product|we)\s+works?\s*$",
     "generic_how_it_works_headline",
     "Replace with the product's 3-step mechanism headlined by its outcome."),
    (r"^\s*(investor|pitch\s+deck|fundraising)\s+(pitch|overview|introduction)\s*$",
     "generic_title_headline",
     "Replace with company name + one concrete value prop."),
    (r"^\s*introduction\s*$",
     "generic_intro_headline",
     "Replace with company name + one concrete value prop."),
    (r"^\s*join\s+(us|our\s+journey)\s*$",
     "generic_ask_headline",
     "Replace with the concrete amount + milestone unlocked."),
    (r"^\s*(the\s+)?team\s*$",
     "generic_team_headline",
     "Replace with a thesis about founder-market fit (e.g. 'Built Payments At Stripe And Square')."),
    (r"^\s*(our|the)\s+solution\s*$",
     "generic_solution_headline",
     "Replace with the solution's concrete outcome (e.g. 'Close Invoices In 90 Seconds')."),
    (r"^\s*(the\s+)?problem\s*$",
     "generic_problem_headline",
     "Replace with a quantified pain statement."),
    (r"^\s*competitive\s+landscape(\s+today)?\s*$",
     "generic_competition_headline",
     "Replace with our one-line positioning vs. the top competitor."),
    (r"^\s*(our\s+)?competition\s*$",
     "generic_competition_headline",
     "Replace with our one-line positioning vs. the top competitor."),
    (r"^\s*(our\s+|the\s+)?vision\s*$",
     "generic_vision_headline",
     "Replace with a concrete future state and a date."),
    (r"^\s*(our\s+|the\s+)?traction\s*$",
     "generic_traction_headline",
     "Replace with a specific momentum metric (e.g. '3x Quarterly Revenue Growth')."),
    (r"^\s*(our\s+|the\s+)?financials\s*$",
     "generic_financials_headline",
     "Replace with the revenue inflection (e.g. 'Path To $10M ARR By Q4 2026')."),
    (r"^\s*(the\s+)?ask\s*$",
     "generic_ask_headline",
     "Replace with amount + milestone unlocked."),
    (r"^\s*what\s+capital\s+unlocks\s*$",
     "generic_ask_headline",
     "Replace with concrete amount + specific unlock."),
    (r"^\s*early\s+validation\s+signals\s*$",
     "generic_traction_headline",
     "Replace with the single strongest traction metric."),
    (r"^\s*projected\s+financial\s+path\s*$",
     "generic_financials_headline",
     "Replace with a specific revenue target + date."),
    (r"^\s*how\s+(the\s+)?workflow\s+runs\s*$",
     "generic_how_it_works_headline",
     "Replace with the outcome the workflow delivers."),
    (r"^\s*why\s+(invoice\s+work|this\s+team)\s+(breaks|wins)\s*$",
     "generic_template_headline",
     "Replace with the specific, evidenced argument."),
    (r"^\s*(our|the)?\s*go[- ]to[- ]market\s*(motion)?\s*$",
     "generic_gtm_headline",
     "Replace with the concrete acquisition channel + CAC or conversion."),
    (r"^\s*technology\s+and\s+defensibility\s*$",
     "generic_tech_headline",
     "Replace with the specific technical moat or unique capability."),
]

_BANNED_HEADLINE_COMPILED: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(pat, re.IGNORECASE), label, hint)
    for (pat, label, hint) in _BANNED_HEADLINE_RAW
]


# ── 2. Generic in-body phrases ──────────────────────────────────────
# These phrases leak through from weak writer or consensus prompts.
# They describe nothing concrete and trigger a specificity penalty.

_GENERIC_PHRASES: tuple[str, ...] = (
    "our ai-powered solution",
    "ai-powered solution",
    "ai-powered platform",
    "revolutionizing",
    "revolutionize the industry",
    "transforming industries",
    "industry-leading",
    "cutting-edge",
    "best-in-class",
    "world-class",
    "next-generation",
    "game-changer",
    "game-changing",
    "disrupt the industry",
    "growing demand for automation",
    "join us on this journey",
    "join our journey",
    "investment opportunity",
    "huge opportunity",
    "massive market",
    "proven track record",
    "significant growth",
    "substantial returns",
)


# ── 3. Required quantitative signals per intent ─────────────────────
# For a data-slide to be allowed to ship, it must carry at least
# `min_numbers` numeric tokens across headline/subheadline/bullets/body
# AND satisfy its structural requirement (stat_blocks OR chart OR table
# OR comparison rows >= min_rows). These are COMPILER-level gates.

@dataclass(frozen=True)
class QuantRequirement:
    min_numbers: int
    requires_structured_block: bool
    min_comparison_rows: int = 0


QUANT_REQUIREMENTS: dict[str, QuantRequirement] = {
    "market":        QuantRequirement(min_numbers=3, requires_structured_block=True),
    "traction":      QuantRequirement(min_numbers=3, requires_structured_block=True),
    "financials":    QuantRequirement(min_numbers=3, requires_structured_block=True),
    "competition":   QuantRequirement(min_numbers=0, requires_structured_block=True,
                                      min_comparison_rows=2),
    "ask":           QuantRequirement(min_numbers=1, requires_structured_block=False),
    "business_model": QuantRequirement(min_numbers=1, requires_structured_block=False),
}


# ── 4. Template detection ───────────────────────────────────────────

@dataclass(frozen=True)
class TemplateDetection:
    is_template: bool
    label: str = ""
    fix_hint: str = ""

    @property
    def ok(self) -> bool:  # convenience
        return not self.is_template


def detect_template_headline(headline: Optional[str]) -> TemplateDetection:
    """Return TemplateDetection(is_template=True, ...) if the headline
    matches any banned pattern. This is the core gate used by planner,
    writer, critic, and compiler.
    """
    if not headline:
        # Missing headline isn't a "template" per se — it's a structural
        # failure handled by a different gate. Don't flag it here.
        return TemplateDetection(is_template=False)
    text = headline.strip()
    if not text:
        return TemplateDetection(is_template=False)
    for (pattern, label, hint) in _BANNED_HEADLINE_COMPILED:
        if pattern.match(text):
            return TemplateDetection(is_template=True, label=label, fix_hint=hint)
    return TemplateDetection(is_template=False)


# ── 5. Generic phrase detection ─────────────────────────────────────

def detect_generic_phrases(*texts: Optional[str]) -> list[str]:
    """Return the list of banned phrases that appear in any of the
    provided text fragments. Case-insensitive, substring match.

    Used by the critic to penalize specificity, and by the writer repair
    step to trigger a targeted rewrite.
    """
    hits: list[str] = []
    haystack = " ".join((t or "").lower() for t in texts)
    if not haystack.strip():
        return hits
    for phrase in _GENERIC_PHRASES:
        if phrase in haystack:
            hits.append(phrase)
    return hits


# ── 6. Numeric + structured content counters ───────────────────────

_NUM_RE = re.compile(r"\b\d+(?:[\.,]\d+)?%?\b|\$\s*\d[\d,\.]*|\b\d+[kmb](?:n)?\b", re.IGNORECASE)


def count_numeric_tokens(*texts: Optional[str]) -> int:
    """Count distinct numeric-looking tokens across all text fragments.

    Tokens counted: plain integers/decimals, percentages, dollar amounts,
    and k/m/b-suffixed shorthand (e.g. '4.2B', '350k'). Duplicates across
    texts are counted once so the same "$4.2B" in headline + body is a
    single signal, not two.
    """
    seen: set[str] = set()
    for t in texts:
        if not t:
            continue
        for m in _NUM_RE.findall(t):
            seen.add(m.lower())
    return len(seen)


def count_slide_numeric_tokens(slide: Mapping[str, Any]) -> int:
    """Count numeric tokens across headline/subheadline/bullets/body
    and primary structured fields (stat_blocks, chart data, table rows).
    """
    fragments: list[str] = []
    fragments.append(str(slide.get("headline") or ""))
    fragments.append(str(slide.get("subheadline") or ""))
    fragments.append(str(slide.get("body") or ""))
    for b in (slide.get("bullets") or []):
        fragments.append(str(b))
    for sb in (slide.get("stat_blocks") or []):
        if isinstance(sb, dict):
            fragments.append(str(sb.get("value") or ""))
            fragments.append(str(sb.get("label") or ""))
    chart = slide.get("chart") or {}
    if isinstance(chart, dict):
        for d in (chart.get("data") or []):
            if isinstance(d, dict):
                fragments.append(str(d.get("value") or ""))
                fragments.append(str(d.get("label") or ""))
    table = slide.get("table") or {}
    if isinstance(table, dict):
        for row in (table.get("rows") or []):
            if isinstance(row, list):
                for cell in row:
                    fragments.append(str(cell))
    return count_numeric_tokens(*fragments)


def has_structured_block(slide: Mapping[str, Any]) -> bool:
    """True if the slide carries any quant-bearing structured block."""
    if slide.get("stat_blocks"):
        blocks = slide.get("stat_blocks") or []
        if any(isinstance(b, dict) and (b.get("value") or b.get("label")) for b in blocks):
            return True
    chart = slide.get("chart") or {}
    if isinstance(chart, dict) and (chart.get("data") or []):
        return True
    table = slide.get("table") or {}
    if isinstance(table, dict) and (table.get("rows") or []):
        return True
    return False


def comparison_row_count(slide: Mapping[str, Any]) -> int:
    """Return the number of rows in a competition/comparison block.

    Two valid shapes are supported:
      1. slide["comparison"]["columns"] — each column has items[].
         Rows are the max length of any column's items.
      2. slide["comparison"]["rows"]    — direct row list.
    Returns 0 when the field is missing or malformed.
    """
    comp = slide.get("comparison")
    if not isinstance(comp, dict):
        return 0
    rows = comp.get("rows")
    if isinstance(rows, list):
        return len(rows)
    cols = comp.get("columns")
    if isinstance(cols, list) and cols:
        max_items = 0
        for col in cols:
            if isinstance(col, dict):
                # Shape (b): {items:[...]}
                items = col.get("items") or []
                if isinstance(items, list):
                    max_items = max(max_items, len(items))
                # Shape (a): {rows:[{feature,value}, ...]} — inline rows on
                # each column. The compiler flattens these by feature, so
                # the row count is the max over columns.
                col_rows = col.get("rows") or []
                if isinstance(col_rows, list):
                    max_items = max(max_items, len(col_rows))
        return max_items
    return 0


# ── 7. Data-slide validation ────────────────────────────────────────

@dataclass
class DataSlideIssue:
    code: str
    detail: str


def validate_data_slide(
    *,
    intent: str,
    slide: Mapping[str, Any],
) -> list[DataSlideIssue]:
    """Validate that a data-heavy slide carries the minimum evidence its
    intent promises. Returns a list of issues (empty = passes).

    Called by the critic (soft penalty) AND the compiler (hard gate).
    """
    issues: list[DataSlideIssue] = []
    intent_key = (intent or "").strip().lower()
    req = QUANT_REQUIREMENTS.get(intent_key)
    if req is None:
        return issues

    n_numbers = count_slide_numeric_tokens(slide)
    if n_numbers < req.min_numbers:
        issues.append(DataSlideIssue(
            code=f"{intent_key}_needs_{req.min_numbers}_numbers_has_{n_numbers}",
            detail=f"Intent '{intent_key}' requires at least {req.min_numbers} "
                   f"grounded numeric signals; slide has {n_numbers}.",
        ))

    if req.requires_structured_block:
        if intent_key == "competition":
            n_rows = comparison_row_count(slide)
            if n_rows < req.min_comparison_rows:
                issues.append(DataSlideIssue(
                    code=f"competition_rows_{n_rows}_below_min_{req.min_comparison_rows}",
                    detail=f"Competition slide carries {n_rows} rows; needs at least "
                           f"{req.min_comparison_rows}.",
                ))
        elif not has_structured_block(slide):
            issues.append(DataSlideIssue(
                code=f"{intent_key}_missing_structured_block",
                detail=f"Intent '{intent_key}' requires a stat_blocks / chart / table "
                       f"element; none present.",
            ))

    return issues


# ── 8. Banned-phrase summary for prompts ────────────────────────────
# Persona and writer prompts quote this block verbatim so every model
# sees the exact same taboo list. Keep it compact and scannable.

BANNED_HEADLINE_PROMPT_BLOCK: str = (
    "BANNED HEADLINES (these are category labels, not slide thesis lines — "
    "NEVER output any of these or close variants):\n"
    "  * 'Market Opportunity' / 'Market Opportunity Today' / 'Our Market'\n"
    "  * 'Our Business Model' / 'The Business Model'\n"
    "  * 'How It Works' / 'How We Work' / 'How The Workflow Runs'\n"
    "  * 'Investor Pitch' / 'Pitch Overview' / 'Fundraising Introduction' / 'Introduction'\n"
    "  * 'Join Us' / 'Join Our Journey' / 'The Ask' / 'What Capital Unlocks'\n"
    "  * 'The Team' / 'Our Team' (must argue founder-market fit)\n"
    "  * 'Our Solution' / 'The Problem' (must state the concrete outcome / pain)\n"
    "  * 'Competitive Landscape' / 'Our Competition'\n"
    "  * 'Vision' / 'Our Vision' / 'Traction' / 'Financials'\n"
    "  * 'Early Validation Signals' / 'Projected Financial Path'\n"
    "  * 'Why Invoice Work Breaks' / 'Why This Team Wins' (same category-label issue)\n"
    "  * 'Go-To-Market Motion' / 'Technology And Defensibility'\n"
    "Every headline must be a THESIS that only makes sense for THIS company "
    "with THESE numbers. If the same headline could be pasted onto any other "
    "startup's deck, it fails."
)


BANNED_PHRASES_PROMPT_BLOCK: str = (
    "BANNED PHRASES (delete and rewrite if any appear):\n"
    "  * 'AI-powered', 'AI-powered solution', 'AI-powered platform'\n"
    "  * 'revolutionizing', 'revolutionize', 'transforming industries'\n"
    "  * 'industry-leading', 'cutting-edge', 'best-in-class', 'world-class'\n"
    "  * 'next-generation', 'game-changer', 'game-changing', 'disrupt the industry'\n"
    "  * 'join us on this journey', 'investment opportunity'\n"
    "  * 'huge opportunity', 'massive market', 'proven track record'\n"
    "  * 'significant growth', 'substantial returns'\n"
)


def prompt_rules_block() -> str:
    """One concatenated block ready to inject into any system prompt."""
    return (
        BANNED_HEADLINE_PROMPT_BLOCK
        + "\n\n"
        + BANNED_PHRASES_PROMPT_BLOCK
    )


# ── 9. Public export summary ────────────────────────────────────────

__all__ = [
    "TemplateDetection",
    "detect_template_headline",
    "detect_generic_phrases",
    "count_numeric_tokens",
    "count_slide_numeric_tokens",
    "has_structured_block",
    "comparison_row_count",
    "validate_data_slide",
    "QuantRequirement",
    "QUANT_REQUIREMENTS",
    "BANNED_HEADLINE_PROMPT_BLOCK",
    "BANNED_PHRASES_PROMPT_BLOCK",
    "prompt_rules_block",
]
