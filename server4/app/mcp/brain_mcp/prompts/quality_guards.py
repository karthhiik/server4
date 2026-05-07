"""
Quality guard pipeline — validates generated slide content before returning.
Catches fluff, missing sources, density violations, and investor-readiness issues.
"""

import re
from typing import Optional

import structlog

logger = structlog.get_logger()

# ── Fluff words that signal weak writing ────────────────────
FLUFF_WORDS = [
    "revolutionary", "disruptive", "cutting-edge", "best-in-class",
    "world-class", "game-changer", "synergy", "holistic", "leverage",
    "paradigm shift", "next-generation", "state-of-the-art", "scalable solution",
    "innovative", "groundbreaking", "seamless", "robust",
    "empower", "unlock", "supercharge",
]

# Compiled regex for performance
FLUFF_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in FLUFF_WORDS) + r')\b',
    re.IGNORECASE,
)

# Numbers that need sources (anything $1M+ or percentages claiming market data)
UNSOURCED_CLAIM_PATTERN = re.compile(
    r'(?:\$[\d,.]+\s*[BMTbmt](?:illion)?|\d+(?:\.\d+)?%\s*(?:CAGR|growth|market|revenue|increase|decrease))',
    re.IGNORECASE,
)

SOURCE_INDICATORS = [
    "(", "source:", "according to", "per ", "based on", "data from",
    "report", "research", "survey", "study", "internal data",
    "McKinsey", "Gartner", "Forrester", "Statista", "Grand View",
    "CB Insights", "PitchBook", "Crunchbase",
]


class QualityGuardResult:
    """Result of running quality guards on content."""

    def __init__(self):
        self.passed = True
        self.warnings: list[str] = []
        self.fluff_found: list[str] = []
        self.unsourced_claims: list[str] = []
        self.density_issues: list[str] = []
        self.investor_issues: list[str] = []

    @property
    def has_issues(self) -> bool:
        return bool(self.warnings or self.fluff_found or self.unsourced_claims
                     or self.density_issues or self.investor_issues)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "warnings": self.warnings,
            "fluff_found": self.fluff_found,
            "unsourced_claims": self.unsourced_claims,
            "density_issues": self.density_issues,
            "investor_issues": self.investor_issues,
        }


def run_quality_guards(
    content: dict,
    layout: str = "",
    purpose: str = "",
    is_investor_deck: bool = False,
) -> QualityGuardResult:
    """Run all quality guards on slide content. Returns QualityGuardResult."""
    result = QualityGuardResult()

    fluff_check(content, result)
    slide_density_check(content, layout, result)
    claim_source_check(content, result)

    if is_investor_deck:
        investor_readiness_check(content, layout, purpose, result)

    if result.has_issues:
        result.passed = False
        logger.info(
            "quality_guard_flagged",
            fluff=len(result.fluff_found),
            unsourced=len(result.unsourced_claims),
            density=len(result.density_issues),
            investor=len(result.investor_issues),
        )

    return result


def fluff_check(content: dict, result: QualityGuardResult) -> None:
    """Detect fluff words that weaken pitch deck content."""
    text = _extract_text(content)
    matches = FLUFF_PATTERN.findall(text)
    if matches:
        unique = list(set(m.lower() for m in matches))
        result.fluff_found = unique
        result.warnings.append(
            f"Fluff detected: {', '.join(unique)}. Replace with concrete language."
        )


def slide_density_check(content: dict, layout: str, result: QualityGuardResult) -> None:
    """Check that slide content fits reasonable density constraints."""
    title = content.get("title", "")
    if title and len(title.split()) > 10:
        result.density_issues.append(f"Title too long ({len(title.split())} words). Target 3-8 words.")

    bullets = content.get("bullets", [])
    if bullets:
        if len(bullets) > 6:
            result.density_issues.append(f"Too many bullets ({len(bullets)}). Max 6 per slide.")
        for i, b in enumerate(bullets):
            words = len(str(b).split())
            if words > 20:
                result.density_issues.append(f"Bullet {i+1} too long ({words} words). Target ≤15 words.")

    body = content.get("body_text", "")
    if body and len(body.split()) > 60:
        result.density_issues.append(f"Body text too long ({len(body.split())} words). Slides ≠ documents.")

    left = content.get("left_content", "")
    right = content.get("right_content", "")
    for side, text in [("Left column", left), ("Right column", right)]:
        if text and len(str(text).split()) > 50:
            result.density_issues.append(f"{side} too dense ({len(str(text).split())} words).")


def claim_source_check(content: dict, result: QualityGuardResult) -> None:
    """Check that large numeric claims have source attribution."""
    text = _extract_text(content)
    claims = UNSOURCED_CLAIM_PATTERN.findall(text)

    for claim in claims:
        # Check if there's a source indicator near this claim
        claim_pos = text.lower().find(claim.lower())
        if claim_pos < 0:
            continue
        # Look within 200 chars after the claim for a source
        context_after = text[claim_pos:claim_pos + 200].lower()
        has_source = any(indicator.lower() in context_after for indicator in SOURCE_INDICATORS)
        if not has_source:
            result.unsourced_claims.append(claim)

    if result.unsourced_claims:
        result.warnings.append(
            f"Unsourced claims: {', '.join(result.unsourced_claims)}. Add source attribution."
        )


def investor_readiness_check(
    content: dict, layout: str, purpose: str, result: QualityGuardResult
) -> None:
    """Check investor-specific quality requirements."""
    purpose_lower = purpose.lower()

    # Traction slides must show trajectory
    if "traction" in purpose_lower:
        if layout not in ("chart", "kpi-dashboard"):
            result.investor_issues.append(
                "Traction should use chart layout to show trajectory (graph going up-right)."
            )
        chart_data = content.get("chart_data", {})
        if layout == "chart" and not chart_data:
            result.investor_issues.append("Traction chart slide has no chart data.")

    # Market slides must have TAM/SAM/SOM
    if "market" in purpose_lower and ("opportunity" in purpose_lower or "size" in purpose_lower):
        text = _extract_text(content).lower()
        has_tam = "tam" in text or "total addressable" in text
        has_sam = "sam" in text or "serviceable addressable" in text
        has_som = "som" in text or "serviceable obtainable" in text
        if not (has_tam and has_sam):
            result.investor_issues.append(
                "Market slide should include TAM/SAM/SOM breakdown."
            )

    # Ask slides must have use-of-funds
    if "ask" in purpose_lower or "funding" in purpose_lower:
        text = _extract_text(content).lower()
        has_amount = "$" in text or "raise" in text or "funding" in text
        has_use = "hire" in text or "engineering" in text or "marketing" in text or "use of funds" in text
        if has_amount and not has_use:
            result.investor_issues.append(
                "Ask slide has a funding amount but no use-of-funds breakdown."
            )

    # Competition slides should not say "no competitors"
    if "compet" in purpose_lower:
        text = _extract_text(content).lower()
        if "no direct competitor" in text or "no competitor" in text:
            result.investor_issues.append(
                "Never say 'no competitors.' Position on a comparison matrix instead."
            )


def consistency_check(slides: list[dict]) -> list[str]:
    """Check cross-slide consistency (company name, numbers, tense)."""
    issues = []

    # Extract all company-name-like references
    company_names = set()
    for slide in slides:
        text = _extract_text(slide.get("content", {}))
        # Look for title-case multi-word phrases that appear in title positions
        title = slide.get("content", {}).get("title", "")
        if title and title[0].isupper():
            company_names.add(title.strip())

    # Check for number contradictions across slides
    # (basic: collect all dollar amounts and check for impossible combinations)
    all_revenue_mentions = []
    for slide in slides:
        text = _extract_text(slide.get("content", {}))
        revenue_matches = re.findall(r'\$[\d,.]+[KMBkmb]?\s*(?:MRR|ARR|revenue)', text, re.IGNORECASE)
        all_revenue_mentions.extend(revenue_matches)

    if len(all_revenue_mentions) > 1:
        # Just flag for manual review if multiple revenue figures
        unique_amounts = list(set(all_revenue_mentions))
        if len(unique_amounts) > 2:
            issues.append(
                f"Multiple revenue figures found across slides: {', '.join(unique_amounts)}. Verify consistency."
            )

    return issues


def _extract_text(content: dict) -> str:
    """Extract all text from slide content for analysis."""
    parts = []
    for key in ["title", "subtitle", "body_text", "left_content", "right_content",
                 "quote_text", "caption", "source_attribution"]:
        val = content.get(key)
        if val and isinstance(val, str):
            parts.append(val)

    for key in ["bullets", "left_items", "right_items"]:
        items = content.get(key)
        if items and isinstance(items, list):
            parts.extend(str(item) for item in items)

    for member in content.get("members", []):
        if isinstance(member, dict):
            parts.extend(str(v) for v in member.values())

    for metric in content.get("metrics", []):
        if isinstance(metric, dict):
            parts.extend(str(v) for v in metric.values())

    for event in content.get("events", []):
        if isinstance(event, dict):
            parts.extend(str(v) for v in event.values())

    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════
# CROSS-SLIDE CONSISTENCY CHECKS
# ═══════════════════════════════════════════════════════════════════════

# Pattern to extract dollar amounts with magnitude suffixes
_DOLLAR_PATTERN = re.compile(
    r'\$\s*([\d,.]+)\s*([KMBTkmbt](?:illion)?)?',
    re.IGNORECASE,
)

# Pattern to extract percentage claims with context
_PERCENT_PATTERN = re.compile(
    r'([\d,.]+)\s*%\s*(CAGR|growth|market|revenue|increase|YoY|MoM)?',
    re.IGNORECASE,
)

# Metric type labels that should be consistent across slides
_METRIC_SYNONYMS = {
    "arr": {"arr", "annual recurring revenue"},
    "mrr": {"mrr", "monthly recurring revenue"},
    "tam": {"tam", "total addressable market"},
    "sam": {"sam", "serviceable addressable market", "serviceable available market"},
    "som": {"som", "serviceable obtainable market"},
    "revenue": {"revenue", "annual revenue", "yearly revenue"},
    "cagr": {"cagr", "compound annual growth rate"},
}


def _normalise_dollar(amount_str: str, suffix: str) -> float:
    """Convert dollar string + suffix to a float for comparison."""
    try:
        base = float(amount_str.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0
    suffix = (suffix or "").upper().rstrip("ILLION")
    multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    return base * multipliers.get(suffix, 1.0)


def cross_slide_consistency_check(contracts: list) -> list[dict]:
    """
    Validate numeric/narrative consistency across all SlideContentContracts.

    Checks:
    1. Conflicting numeric claims (same metric, different numbers)
    2. Citation label uniqueness (no duplicate labels mapping to different sources)
    3. Metric naming consistency (ARR vs MRR must not both appear without context)
    4. Narrative thread coherence (problem→solution→market flow)

    Returns list of issue dicts: [{type, severity, slides, message}]
    """
    issues: list[dict] = []

    if not contracts:
        return issues

    # ── 1) Numeric claim conflicts ───────────────────────────
    # Collect all dollar amounts per metric context
    metric_values: dict[str, list[tuple[str, float, str]]] = {}
    for contract in contracts:
        slide_id = contract.slide_id if hasattr(contract, "slide_id") else str(contract)
        pres = contract.presentation_content if hasattr(contract, "presentation_content") else None
        read = contract.reading_content if hasattr(contract, "reading_content") else None

        texts = []
        if pres:
            texts.append(pres.title if hasattr(pres, "title") else "")
            texts.extend(pres.bullets if hasattr(pres, "bullets") else [])
            if hasattr(pres, "hero_stat") and pres.hero_stat:
                texts.append(pres.hero_stat)
        if read:
            texts.append(read.summary if hasattr(read, "summary") else "")

        full_text = " ".join(str(t) for t in texts)

        # Extract dollar-context pairs
        for match in _DOLLAR_PATTERN.finditer(full_text):
            value = _normalise_dollar(match.group(1), match.group(2))
            # Get surrounding context (30 chars after the match)
            ctx_start = match.end()
            ctx = full_text[ctx_start:ctx_start + 40].lower().strip()
            # Try to find a metric label in context
            metric_key = "unknown"
            for label, synonyms in _METRIC_SYNONYMS.items():
                if any(s in ctx or s in full_text[max(0, match.start() - 30):match.start()].lower()
                       for s in synonyms):
                    metric_key = label
                    break
            if metric_key == "unknown":
                # Use first word of context as key
                words = ctx.split()
                if words:
                    metric_key = words[0]

            if value > 0:
                metric_values.setdefault(metric_key, []).append(
                    (slide_id, value, match.group(0))
                )

    # Check for conflicting values on the same metric
    for metric, entries in metric_values.items():
        if len(entries) < 2:
            continue
        values = [e[1] for e in entries]
        min_val, max_val = min(values), max(values)
        # Allow 10% tolerance for rounding
        if min_val > 0 and (max_val / min_val) > 1.15:
            slide_ids = list(set(e[0] for e in entries))
            raw_values = [e[2] for e in entries]
            issues.append({
                "type": "numeric_conflict",
                "severity": "critical",
                "slides": slide_ids,
                "message": (
                    f"Conflicting '{metric}' values across slides: "
                    f"{', '.join(raw_values)}. "
                    f"Verify consistency — investors will notice."
                ),
            })

    # ── 2) Citation label uniqueness ─────────────────────────
    citation_map: dict[str, set[str]] = {}  # label → set of source_urls
    for contract in contracts:
        citations = contract.citations if hasattr(contract, "citations") else []
        for cit in citations:
            label = cit.label if hasattr(cit, "label") else str(cit)
            source = (cit.source_url if hasattr(cit, "source_url") else "") or ""
            citation_map.setdefault(label, set()).add(source)

    for label, sources in citation_map.items():
        non_empty = {s for s in sources if s}
        if len(non_empty) > 1:
            issues.append({
                "type": "citation_conflict",
                "severity": "important",
                "slides": [],
                "message": (
                    f"Citation label '{label}' maps to {len(non_empty)} different sources. "
                    f"Each label must reference exactly one source."
                ),
            })

    # ── 3) Metric naming consistency ─────────────────────────
    found_metrics: set[str] = set()
    for contract in contracts:
        pres = contract.presentation_content if hasattr(contract, "presentation_content") else None
        read = contract.reading_content if hasattr(contract, "reading_content") else None
        texts = []
        if pres:
            texts.append(pres.title if hasattr(pres, "title") else "")
            texts.extend(pres.bullets if hasattr(pres, "bullets") else [])
        if read:
            texts.append(read.summary if hasattr(read, "summary") else "")
        full = " ".join(str(t) for t in texts).lower()

        if "arr" in full or "annual recurring" in full:
            found_metrics.add("arr")
        if "mrr" in full or "monthly recurring" in full:
            found_metrics.add("mrr")

    if "arr" in found_metrics and "mrr" in found_metrics:
        issues.append({
            "type": "metric_inconsistency",
            "severity": "important",
            "slides": [],
            "message": (
                "Both ARR and MRR are used across the deck. Pick one primary revenue "
                "metric and use the other only in context (e.g. '$1.2M ARR ($100K MRR)')."
            ),
        })

    # ── 4) Narrative thread check ────────────────────────────
    expected_flow = ["problem", "solution", "market", "competition", "traction", "financial", "ask"]
    slide_kinds = []
    for contract in contracts:
        kind = contract.slide_kind if hasattr(contract, "slide_kind") else None
        if kind:
            kind_val = kind.value if hasattr(kind, "value") else str(kind)
            slide_kinds.append(kind_val)

    if slide_kinds:
        # Check that key slides appear in roughly the expected order
        flow_positions = {}
        for idx, kind in enumerate(slide_kinds):
            if kind in expected_flow and kind not in flow_positions:
                flow_positions[kind] = idx

        # Verify ordering for pairs that should be sequential
        order_checks = [
            ("problem", "solution"),
            ("solution", "market"),
            ("traction", "ask"),
        ]
        for before, after in order_checks:
            if before in flow_positions and after in flow_positions:
                if flow_positions[before] > flow_positions[after]:
                    issues.append({
                        "type": "narrative_order",
                        "severity": "important",
                        "slides": [before, after],
                        "message": (
                            f"'{after}' slide appears before '{before}' slide. "
                            f"Investor decks should flow: {' → '.join(expected_flow)}."
                        ),
                    })

    return issues


def deck_level_coherence_score(contracts: list) -> float:
    """
    Score 0.0-1.0 for overall deck coherence across all SlideContentContracts.

    Components:
    - Numeric consistency (0.3 weight)
    - Citation integrity (0.2 weight)
    - Evidence coverage (0.3 weight)
    - Narrative flow (0.2 weight)
    """
    if not contracts:
        return 0.0

    score = 0.0

    # ── Numeric consistency (0.3) ────────────────────────────
    consistency_issues = cross_slide_consistency_check(contracts)
    critical_count = sum(1 for i in consistency_issues if i.get("severity") == "critical")
    important_count = sum(1 for i in consistency_issues if i.get("severity") == "important")
    # Deduct 0.15 per critical, 0.05 per important
    consistency_score = max(0.0, 1.0 - (critical_count * 0.15) - (important_count * 0.05))
    score += consistency_score * 0.3

    # ── Citation integrity (0.2) ─────────────────────────────
    total_citations = 0
    valid_citations = 0
    for contract in contracts:
        citations = contract.citations if hasattr(contract, "citations") else []
        for cit in citations:
            total_citations += 1
            url = cit.source_url if hasattr(cit, "source_url") else None
            if url:
                valid_citations += 1
    citation_ratio = valid_citations / max(total_citations, 1)
    score += citation_ratio * 0.2

    # ── Evidence coverage (0.3) ──────────────────────────────
    slides_with_evidence = 0
    for contract in contracts:
        ev_score = contract.evidence_score if hasattr(contract, "evidence_score") else 0.0
        if ev_score > 0.3:
            slides_with_evidence += 1
    coverage = slides_with_evidence / max(len(contracts), 1)
    score += coverage * 0.3

    # ── Narrative flow (0.2) ─────────────────────────────────
    flow_issues = [i for i in consistency_issues if i.get("type") == "narrative_order"]
    flow_score = max(0.0, 1.0 - len(flow_issues) * 0.25)
    score += flow_score * 0.2

    return round(min(1.0, max(0.0, score)), 3)
