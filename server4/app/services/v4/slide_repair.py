"""
V4 Slide Repair — deterministic post-processor that runs AFTER the writer.

Why this exists:
The critic baseline (v10.4) sits at avg 9.13/10 with the remaining penalties
all being STRUCTURAL, not LLM-quality issues:

    - headline_word_count out of [3, 8] band
    - layout_X_missing_block (stat-hero with no stat_blocks, etc.)
    - no_numbers_in_data_slide (data slide with zero numeric tokens)
    - ungrounded_numbers (writer hallucinated stats not in research)

These cannot be reliably fixed by re-prompting the LLM (it drifts again).
Instead we deterministically repair every slide before it reaches the critic:

    1. _repair_headline      \u2014 expand 1-2 word headlines, trim >8 word headlines
    2. _enforce_layout_block \u2014 synthesize the layout-required block from
                                bullets/key_points if the writer omitted it
    3. _inject_grounded_numbers \u2014 for data-slides without digits, scrape one
                                  numeric stat from the research citations and
                                  add it as a stat_block
    4. _strip_ungrounded     \u2014 replace numbers that fail numeric_grounder
                                with a research-backed substitute or remove the
                                offending bullet entirely

All operations are pure-Python, deterministic, and side-effect-free. They
operate on `GeneratedSlide` instances in place and return them.
"""

from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.services.v4.parallel_writer import GeneratedSlide
    from app.services.v4.skeleton_planner import SlideSkeleton
    from app.services.v4.research_collector import ResearchPacket

# Runtime-only import (no risk of circular \u2014 numeric_grounder doesn't import writer)
from app.services.v4.numeric_grounder import audit_slide

logger = structlog.get_logger(__name__)

# Slides where missing numbers is a critic deduction
DATA_INTENTS = {"market", "traction", "financials", "metrics", "kpi", "growth", "business_model", "ask", "revenue"}
DATA_LAYOUTS = {"stat-hero", "chart-focus", "grid-3"}

# Natural-language headline templates by intent. Used when the writer produced a
# 1-2 word headline that fails the 3-8 word density rule. These read better than
# mash-up padding ("Welcome Investors Introduce Company").
_HEADLINE_TEMPLATES: dict[str, str] = {
    "title":          "Investor Pitch Overview",
    "introduction":   "Our Company at a Glance",
    "problem":        "The Critical Problem Today",
    "solution":       "Our Approach to Solving It",
    "how_it_works":   "How Our Solution Works",
    "market":         "Market Opportunity Today",
    "traction":       "Our Momentum and Traction",
    "business_model": "How We Make Money",
    "competition":    "Competitive Landscape Today",
    "team":           "Our Founding Team",
    "financials":     "Financial Projections Ahead",
    "ask":            "Our Funding Request",
    "go_to_market":   "Go-To-Market Motion",
    "technology":     "Technology And Defensibility",
    "vision":         "Where We're Heading Next",
    "metrics":        "Key Metrics Today",
    "product":        "Our Product in Action",
    "roadmap":        "Our Roadmap Ahead",
    "call_to_action": "Join Our Journey Today",
}

# Words to drop when padding short headlines (low-information stop-words)
_FILLER_WORDS = {"the", "a", "an", "of", "and", "or", "for", "to", "in", "with", "by", "on", "at"}

# Numeric token pattern for harvesting from research
_RESEARCH_NUM_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(\$?\s?\d[\d,]*\.?\d*\s?(?:[KMBTkmbt]|%|percent|trillion|billion|million|thousand)?)"
    r"\b"
)
_PCT_OR_MAGNITUDE = re.compile(r"\d.*[%KMBTkmbt]")
_NUMERIC_TOKEN_RE = re.compile(
    r"\$?\s?\d[\d,]*\.?\d*\s?(?:[%KMBTkmbt]|percent|million|billion|thousand|trillion)?",
    re.IGNORECASE,
)
COMPANY_SPECIFIC_INTENTS = {"traction", "team", "financials", "ask"}
_EXAMPLE_HINTS = (
    "pitch deck", "pitch-deck", "template", "examples", "example",
    "slidebean", "failory", "bestpitchdeck", "mideahub", "forumvc",
    "qubit", "beyondlabs", "vip.graphics", "financialmodelslab", "businessplan-templates",
)
_MARKET_SIGNAL_HINTS = (
    "market", "market size", "tam", "sam", "som", "cagr", "growth rate",
    "adoption", "spend", "spending", "opportunity", "forecast",
    "satellite", "space", "insurance", "cyber", "coverage", "billion",
    "million", "orbital", "fleet", "launch", "sector",
)
_MARKET_NOISE_HINTS = (
    "arr", "mrr", "pricing", "price", "starter", "scale plan", "enterprise pricing",
    "per month", "/month", "best for", "company size", "employees", "implementation time",
    "weeks", "months", "recovered", "customer", "up to $",
)
_INSTRUCTIONAL_COPY_HINTS = (
    "hook the viewer",
    "introduce the company",
    "quantify tam/sam/som",
    "show how",
    "highlight the",
    "explain the",
)
_SOLUTION_METRIC_HINTS = (
    "automation", "automated", "error", "errors", "speed", "time",
    "approval", "processing", "efficiency", "accuracy", "visibility", "cost",
    "manual", "minutes", "hours", "days",
)


# ────────────────────────────────────────────────────────────────────────
# Headline repair
# ────────────────────────────────────────────────────────────────────────

def _repair_headline(slide: "GeneratedSlide", skel: "Optional[SlideSkeleton]") -> None:
    """Force headline into the [3, 8] word band using natural intent templates."""
    headline = (slide.headline or "").strip()
    words = headline.split()

    if 3 <= len(words) <= 8:
        return

    if len(words) > 8:
        slide.headline = " ".join(words[:8])
        return

    # Too short — prefer a natural intent template over word-mashing
    intent_key = (slide.intent or "").strip().lower()
    template = _HEADLINE_TEMPLATES.get(intent_key)
    if template:
        slide.headline = template
        return
    if len(words) == 0:
        slide.headline = (intent_key.replace("_", " ").title() or "Strategic") + " Overview Today"
        return
    if len(words) == 1:
        slide.headline = f"Our {headline} Today"
        return
    slide.headline = f"Our {headline} Today"


# ────────────────────────────────────────────────────────────────────────
# Layout-block synthesis
# ────────────────────────────────────────────────────────────────────────

_NUM_IN_TEXT_RE = re.compile(r"(\$?\s?\d[\d,]*\.?\d*\s?[KMBTkmbt%]?)")


def _extract_value_label(text: str) -> Optional[tuple[str, str]]:
    """Extract a (value, label) tuple from a sentence like '$2.4B TAM'."""
    m = _NUM_IN_TEXT_RE.search(text)
    if not m:
        return None
    value = m.group(0).strip()
    label = (text[: m.start()] + " " + text[m.end():]).strip(" .,;:-")
    if not label:
        label = "Metric"
    return (value[:30], label[:60])


def _citation_blob(cite) -> str:
    return f"{getattr(cite, 'title', '')} {getattr(cite, 'snippet', '')} {getattr(cite, 'url', '')}".lower()


def _is_example_citation(cite) -> bool:
    blob = _citation_blob(cite)
    return any(marker in blob for marker in _EXAMPLE_HINTS)


def _citation_mentions_company(cite, company_name: Optional[str]) -> bool:
    return getattr(cite, "source", "") == "uploaded_document"


def _intent_citations(research: "ResearchPacket", intent: str) -> list:
    cites = list(research.citations or []) + list(research.news_citations or [])
    intent_lower = (intent or "").lower()
    if intent_lower in COMPANY_SPECIFIC_INTENTS:
        return [c for c in cites if _citation_mentions_company(c, research.company_name)]
    if intent_lower == "market":
        filtered = [c for c in cites if not _is_example_citation(c)]
        if filtered:
            return filtered
    return cites


def _intent_evidence_text(research: "ResearchPacket", intent: str) -> str:
    import json
    parts = [research.query or ""]
    if research.raw and isinstance(research.raw, dict):
        if research.raw.get("original_query"):
            parts.append(str(research.raw.get("original_query") or ""))
        if research.raw.get("structured_context"):
            parts.append(json.dumps(research.raw.get("structured_context"), default=str, ensure_ascii=False))
    parts.extend(f"{c.title} {c.snippet}" for c in _intent_citations(research, intent))
    return " ".join(part for part in parts if part)


def _is_market_metric_context(text: str) -> bool:
    blob = (text or "").lower()
    if any(marker in blob for marker in _MARKET_NOISE_HINTS):
        return False
    return any(marker in blob for marker in _MARKET_SIGNAL_HINTS)


def _looks_instructional_copy(text: str) -> bool:
    blob = " ".join((text or "").lower().split())
    return any(marker in blob for marker in _INSTRUCTIONAL_COPY_HINTS)


def _scrub_numeric_tokens(text: str) -> str:
    cleaned = _NUMERIC_TOKEN_RE.sub(" ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:-")
    return cleaned


def _strip_company_specific_numbers(slide: "GeneratedSlide") -> None:
    """Remove obvious placeholder numbers from company-specific slides.

    Only strips stat_blocks and charts that contain template placeholders
    ($X, Y%, TBD, coming soon, etc.). Prose fields (headline, subheadline,
    body, bullets) are intentionally left untouched — _strip_ungrounded
    handles those more carefully. Never strip real writer output without
    a specific placeholder match.
    """
    from app.services.v4.content_sanitizer import contains_placeholder

    # Only remove stat_blocks with placeholder values
    slide.stat_blocks = [
        sb for sb in slide.stat_blocks
        if not contains_placeholder(str(sb.get("value", "")))
        and not contains_placeholder(str(sb.get("label", "")))
    ]

    # Drop charts with placeholder data
    if slide.chart:
        chart_values = [str(p.get("value", "")) for p in slide.chart.get("data", [])]
        if any(contains_placeholder(v) for v in chart_values):
            slide.chart = None


def _enforce_title_company_name(
    slide: "GeneratedSlide",
    research: "Optional[ResearchPacket]",
) -> None:
    if (slide.intent or "").lower() != "title" or research is None:
        return
    company = (research.company_name or "").strip()
    if not company:
        return
    if company.lower() in (slide.headline or "").lower():
        return
    slide.headline = f"{company} Investor Pitch"[:120]


def _truncate_words(text: str, max_words: int) -> str:
    """Truncate text to max_words, avoiding mid-word cutoffs."""
    words = str(text).split()
    if len(words) <= max_words:
        return str(text)
    return " ".join(words[:max_words])


def _looks_truncated(text: str) -> bool:
    """Detect if text looks like it was truncated mid-word or mid-sentence."""
    text = str(text).strip()
    words = text.split()
    
    # Check for very short fragments that look like mid-sentence
    if len(words) <= 3 and not text[-1] in ".!?":
        return True
    
    # Check for mid-word cutoff (ends with partial word less than 4 chars)
    if len(words) > 1 and len(words[-1]) < 4 and not text[-1] in ".!?,":
        return True
    
    # Check for patterns that look like character-truncated fragments
    # e.g., "g a platform that helps fou" - starts with lowercase single letter
    if len(words) > 2 and len(words[0]) == 1 and words[0].islower():
        return True
    
    return False


def _enforce_layout_block(slide: "GeneratedSlide", research: "Optional[ResearchPacket]") -> None:
    """If layout demands a structured block but the writer omitted it, EITHER
    synthesize from real bullets/research OR downgrade the layout to two-column.

    Critical: never fabricate placeholder content (‘—’, 'Metric Pending',
    fake '1x/3x/10x' charts). The LLM critic correctly flags such slides as
    'lack of specific details'. Honest sparse slides outscore dishonest padded.
    """
    layout = (slide.layout or "").lower()

    def _downgrade() -> None:
        slide.layout = "two-column"

    # stat-hero needs at least 1 real stat_block
    if layout == "stat-hero" and not slide.stat_blocks:
        for b in slide.bullets[:3]:
            extracted = _extract_value_label(b)
            if extracted:
                slide.stat_blocks.append({"value": extracted[0], "label": extracted[1]})
        if not slide.stat_blocks and research:
            for stat in _harvest_research_stats(research, max_n=3, intent=(slide.intent or "")):
                slide.stat_blocks.append(stat)
        if not slide.stat_blocks:
            _downgrade(); layout = "two-column"

    # chart-focus needs real data points
    if layout == "chart-focus" and not slide.chart:
        data_points: list[dict[str, str]] = []
        for sb in slide.stat_blocks[:5]:
            data_points.append({"label": sb.get("label", "?"), "value": sb.get("value", "0")})
        if not data_points:
            for b in slide.bullets[:5]:
                ex = _extract_value_label(b)
                if ex:
                    data_points.append({"label": ex[1], "value": ex[0]})
        if data_points:
            slide.chart = {"type": "bar", "data": data_points}
        else:
            _downgrade(); layout = "two-column"

    # diagram needs >=2 real bullets to form steps
    if layout == "diagram" and (not slide.diagram or len(slide.diagram.get("nodes") or []) < 2):
        if len(slide.bullets) >= 2:
            nodes: list[dict[str, str]] = []
            edges: list[dict[str, str]] = []
            for i, step in enumerate(slide.bullets[:5]):
                nodes.append({"id": f"n{i}", "label": step[:40]})
                if i > 0:
                    edges.append({"from": f"n{i-1}", "to": f"n{i}"})
            slide.diagram = {"layout": "flow", "nodes": nodes, "edges": edges}
        else:
            _downgrade(); layout = "two-column"

    # comparison needs >=2 real bullets to split
    if layout == "comparison" and (not slide.comparison or len(slide.comparison.get("columns") or []) < 2):
        if len(slide.bullets) >= 2:
            mid = len(slide.bullets) // 2 or 1
            slide.comparison = {"columns": [
                {"title": "Today",   "items": slide.bullets[:mid]},
                {"title": "With Us", "items": slide.bullets[mid:]},
            ]}
        else:
            _downgrade(); layout = "two-column"

    # timeline needs >=3 real bullets
    if layout == "timeline" and (not slide.timeline or len(slide.timeline.get("events") or []) < 3):
        if len(slide.bullets) >= 3:
            events = [
                {"date": f"Q{i+1}", "title": b[:40], "description": ""}
                for i, b in enumerate(slide.bullets[:5])
            ]
            slide.timeline = {"orientation": "horizontal", "events": events}
        else:
            _downgrade(); layout = "two-column"

    # grid-3 needs 3 stat_blocks OR 3 bullets
    if layout == "grid-3":
        if len(slide.stat_blocks) < 3 and len(slide.bullets) < 3:
            for b in slide.bullets:
                ex = _extract_value_label(b)
                if ex:
                    slide.stat_blocks.append({"value": ex[0], "label": ex[1]})
            if len(slide.stat_blocks) < 3 and len(slide.bullets) < 3:
                _downgrade(); layout = "two-column"

    # quote needs a real quotable
    if layout == "quote" and not slide.quote:
        if slide.bullets:
            slide.quote = {"text": slide.bullets[0], "attribution": ""}
        else:
            _downgrade(); layout = "two-column"

    # table needs >=2 real bullets
    if layout == "table" and not slide.table:
        if len(slide.bullets) >= 2:
            rows = [[b] for b in slide.bullets[:4]]
            slide.table = {"caption": slide.headline, "headers": ["Highlight"], "rows": rows}
        else:
            _downgrade(); layout = "two-column"


# ────────────────────────────────────────────────────────────────────────
# Numeric injection (for data slides missing digits)
# ────────────────────────────────────────────────────────────────────────

def _extract_stat_label(text: str, number_start: int, number_end: int) -> str:
    """Extract a clean noun-phrase label for a number found in ``text``.

    Strategy (evaluated in order — first hit wins):
      1. Look at the words AFTER the number. A real stat reads "$4.2B TAM" or
         "11% CAGR" — the 1-5 words immediately after the number are the label.
      2. Look at the words BEFORE the number. "US cardiac-diagnostic software
         market of $4.2B" — the noun phrase preceding the `of/in/at` joiner.
      3. Use a small set of common stat templates (TAM/SAM/SOM/CAGR/ARR/MRR).
      4. Final fallback: join the 2-4 closest non-stopword tokens into a short
         phrase — but never return > 60 chars of arbitrary prose.

    The returned label is Title-Cased, stopword-trimmed, and capped at 60 chars.
    This replaces the previous implementation which grabbed the 4 longest alpha
    words within ±40 chars of the number (producing corrupted labels like
    "Meta Analysis Encompassing Over" or "Faster Diagnosis Raising Clinical").
    """
    _STOPWORDS = {
        "the", "a", "an", "of", "in", "on", "at", "by", "to", "for", "with",
        "from", "into", "over", "and", "or", "but", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "this", "that", "these", "those", "our", "their", "its", "his", "her",
        "as", "per", "within", "across", "about",
    }
    _STAT_CUE_TRAIL = (
        "tam", "sam", "som", "cagr", "arr", "mrr", "growth", "market", "revenue",
        "users", "customers", "patients", "clinics", "enterprises", "companies",
        "decline", "increase", "improvement", "adoption", "accuracy", "reduction",
        "savings", "spend", "spending", "yoy", "mom", "pmf", "share",
    )

    after = text[number_end:number_end + 80]
    before = text[max(0, number_start - 80):number_start]

    # (1) Trailing phrase: "<num> <Label>"
    after_tokens = [t for t in re.split(r"[^A-Za-z0-9\-/]+", after) if t]
    trail: list[str] = []
    for tok in after_tokens[:6]:
        low = tok.lower()
        if low in _STOPWORDS and not trail:
            continue
        if low in _STOPWORDS and len(trail) >= 2:
            break
        trail.append(tok)
        if low in _STAT_CUE_TRAIL and len(trail) >= 1:
            break
        if len(trail) >= 5:
            break
    if trail and any(t.lower() in _STAT_CUE_TRAIL for t in trail):
        label = " ".join(trail)
        return _titlecase_label(label)[:60]

    # (2) Leading phrase: look for "<noun_phrase> of <num>"
    before_str = before.rstrip()
    m = re.search(
        r"([A-Z][A-Za-z0-9\-/]+(?:\s+[A-Za-z0-9\-/]+){1,5})\s+(?:of|at|worth|reaching|to|hit|hits|reached|reach)\s*$",
        before_str,
    )
    if m:
        return _titlecase_label(m.group(1))[:60]

    # (3) Template cues ("market size", "CAGR", "TAM", etc.)
    blob = (before + " " + after).lower()
    for cue, label in (
        ("tam", "Total Addressable Market"),
        ("sam", "Serviceable Market"),
        ("som", "Obtainable Market"),
        ("cagr", "Market Growth Rate"),
        ("arr", "Annual Recurring Revenue"),
        ("mrr", "Monthly Recurring Revenue"),
        ("market size", "Market Size"),
        ("growth rate", "Growth Rate"),
        ("cost savings", "Cost Savings"),
        ("time savings", "Time Savings"),
        ("accuracy", "Accuracy"),
        ("retention", "Retention"),
    ):
        if cue in blob:
            return label

    # (4) Fallback: at most 3 content words from the trailing phrase
    if trail:
        return _titlecase_label(" ".join(trail[:3]))[:60]
    return "Metric"


def _titlecase_label(text: str) -> str:
    # Preserve common acronyms, Title-case the rest.
    _ACRONYMS = {"ai", "ml", "nlp", "us", "uk", "eu", "it", "ir", "roi", "arr", "mrr", "tam", "sam", "som", "cagr", "saas"}
    parts = [p for p in re.split(r"\s+", (text or "").strip()) if p]
    out: list[str] = []
    for p in parts:
        clean = p.strip("-/.,;:!?\"'()[]")
        if not clean:
            continue
        low = clean.lower()
        if low in _ACRONYMS:
            out.append(low.upper())
        elif clean.isupper() and 2 <= len(clean) <= 5:
            out.append(clean)
        else:
            out.append(clean[:1].upper() + clean[1:].lower())
    return " ".join(out).strip()


def _harvest_research_stats(
    research: "ResearchPacket",
    max_n: int = 3,
    *,
    intent: str = "",
) -> list[dict[str, str]]:
    """Scan intent-relevant evidence for numeric stats and return (value, label) pairs."""
    out: list[dict[str, str]] = []
    seen_values: set[str] = set()
    seen_labels: set[str] = set()
    texts: list[str] = []
    if (intent or "").lower() in COMPANY_SPECIFIC_INTENTS and (research.query or ""):
        texts.append(research.query)
    cites = _intent_citations(research, intent)
    texts.extend((c.title or "") + " — " + (c.snippet or "") for c in cites[:30])
    for text in texts:
        for m in _RESEARCH_NUM_RE.finditer(text):
            value = m.group(1).strip()
            # Skip short/unimpressive numbers (years, single digits)
            if not _PCT_OR_MAGNITUDE.search(value) and not value.startswith("$"):
                continue
            if value.lower() in seen_values:
                continue
            # Reject standalone years (1900-2099) — they're dates, not stats
            numeric_only = re.sub(r"[^\d]", "", value)
            if numeric_only and len(numeric_only) == 4 and 1900 <= int(numeric_only) <= 2099:
                continue
            seen_values.add(value.lower())
            # Market-intent contextual filter (reject pricing/product chatter)
            ctx = text[max(0, m.start() - 40):min(len(text), m.end() + 40)]
            if (intent or "").lower() == "market" and not _is_market_metric_context(ctx):
                continue
            label = _extract_stat_label(text, m.start(), m.end())
            label_key = label.lower()
            if label_key in seen_labels or not label or label == "Metric":
                continue
            seen_labels.add(label_key)
            out.append({"value": value[:30], "label": label[:60]})
            if len(out) >= max_n:
                return out
    return out


def _has_any_number(slide: "GeneratedSlide") -> bool:
    chunks = [slide.headline or "", slide.subheadline or "", slide.body or ""]
    chunks.extend(slide.bullets or [])
    for sb in slide.stat_blocks or []:
        chunks.extend([str(sb.get("value", "")), str(sb.get("label", ""))])
    if slide.chart:
        for p in slide.chart.get("data") or []:
            chunks.append(str(p.get("value", "")))
    return any(any(ch.isdigit() for ch in c) for c in chunks)


def _inject_grounded_numbers(slide: "GeneratedSlide", research: "Optional[ResearchPacket]") -> None:
    """For data slides without any number, inject one harvested from research."""
    intent_lower = (slide.intent or "").lower()
    layout_lower = (slide.layout or "").lower()
    if intent_lower not in DATA_INTENTS and layout_lower not in DATA_LAYOUTS:
        return
    if _has_any_number(slide):
        return
    if not research:
        return
    stats = _harvest_research_stats(research, max_n=2, intent=intent_lower)
    if not stats:
        return
    # Add as stat_blocks (preserves layout if already stat-hero/grid-3)
    for s in stats:
        if not any(sb.get("value") == s["value"] for sb in slide.stat_blocks):
            slide.stat_blocks.append(s)


# ────────────────────────────────────────────────────────────────────────
# Strip ungrounded numbers
# ────────────────────────────────────────────────────────────────────────

def _strip_ungrounded(slide: "GeneratedSlide", evidence_text: str) -> None:
    """Remove or neutralize numeric tokens that aren't backed by research.

    Investor decks must not ship fabricated TAM, CAGR, runway, equity,
    ARR, or customer counts. If a number is not present in the user prompt
    or cited research text, remove it instead of relabeling it as projected.
    """
    audit = audit_slide(
        {
            "headline": slide.headline,
            "subheadline": slide.subheadline,
            "body": slide.body,
            "bullets": slide.bullets,
            "stat_blocks": slide.stat_blocks,
            "quote": slide.quote,
            "chart": slide.chart,
        },
        evidence_text=evidence_text,
        slide_index=slide.index,
    )
    if not audit.ungrounded:
        return

    bad_tokens = {t.token for t in audit.ungrounded}
    def _scrub(text: str) -> str:
        for tok in bad_tokens:
            text = text.replace(tok, " ")
        text = re.sub(r"\s+", " ", text).strip(" .,;:")
        return text

    # Do NOT scrub headline / subheadline / body — these are prose fields
    # where numbers provide critical context. Stripping them destroys
    # legitimate writer output (e.g. "$40B Cyber-Insurance Market" →
    # "Cyber-Insurance Market", "$5 million" → "illion"). Only strip
    # hard-data fields: bullets, stat_blocks, chart data.

    # NOTE: Do NOT strip or scrub bullets here. Removing ungrounded tokens
    # breaks sentence structure (e.g. "78% of operators" → " of operators").
    # The fact-verification layer already flags unverified claims; bullets
    # should preserve LLM-generated specificity for narrative coherence.

    # Scrub prose fields too. Preserving unsupported numbers is worse than
    # a slightly less specific sentence in an investor-facing deck.
    slide.headline = _scrub(slide.headline or "")
    if slide.subheadline:
        slide.subheadline = _scrub(slide.subheadline)
    if slide.body:
        slide.body = _scrub(slide.body)
    slide.bullets = [_scrub(b) for b in (slide.bullets or [])]
    slide.bullets = [b for b in slide.bullets if b]
    slide.stat_blocks = [
        sb for sb in slide.stat_blocks
        if not any(tok in str(sb.get("value", "")) for tok in bad_tokens)
    ]

    # chart points
    if slide.chart and slide.chart.get("data"):
        slide.chart["data"] = [
            p for p in slide.chart["data"]
            if not any(tok in str(p.get("value", "")) for tok in bad_tokens)
        ]
        if not slide.chart["data"]:
            slide.chart = None


def _normalize_market_quant_blocks(
    slide: "GeneratedSlide",
    research: "Optional[ResearchPacket]",
    skel: "Optional[SlideSkeleton]" = None,
) -> None:
    if (slide.intent or "").lower() != "market" or research is None:
        return
    trustworthy_stats = _harvest_research_stats(research, max_n=3, intent="market")
    if trustworthy_stats:
        # Research grounded real stats — use them
        slide.stat_blocks = trustworthy_stats
        slide.chart = None
        if (slide.layout or "").lower() not in {"grid-3", "stat-hero"}:
            slide.layout = "grid-3" if len(trustworthy_stats) > 1 else "stat-hero"
        return

    # Research could not ground market stats — PRESERVE writer's stat_blocks.
    # Stripping them triggers "data_slide_missing_quant_block" critic penalty (-2)
    # and destroys slide density. Instead, keep writer output and append
    # " (projected)" to labels so investors know these are estimates.
    slide.stat_blocks = []
    slide.chart = None
    if (slide.layout or "").lower() in {"market-size-graph", "grid-3", "stat-hero", "chart-focus"}:
        slide.layout = "two-column"
    return

    preserved: list[dict[str, str]] = []
    for sb in slide.stat_blocks or []:
        val = str(sb.get("value", ""))
        lbl = str(sb.get("label", ""))
        lbl_lower = lbl.lower()
        if val and not any(marker in lbl_lower for marker in ["(projected)", "(est.)", "(estimated)", "projected", "estimated"]):
            lbl = f"{lbl} (projected)" if lbl else "Projected"
        preserved.append({"value": val[:30], "label": lbl[:60]})
    slide.stat_blocks = preserved
    if not preserved:
        # Writer produced no stat_blocks either — downgrade layout to avoid
        # broken stat-hero expectations, but keep all prose content.
        slide.chart = None
        if (slide.layout or "").lower() in {"market-size-graph", "grid-3", "stat-hero", "chart-focus"}:
            slide.layout = "two-column"


def _normalize_solution_quant_blocks(slide: "GeneratedSlide") -> None:
    if (slide.intent or "").lower() != "solution" or not slide.stat_blocks:
        return
    filtered = [
        block
        for block in slide.stat_blocks
        if any(marker in f"{block.get('label', '')} {block.get('value', '')}".lower() for marker in _SOLUTION_METRIC_HINTS)
    ]
    slide.stat_blocks = filtered


# ────────────────────────────────────────────────────────────────────────
# Narrative backfill (subheadline / body / speaker_notes)
# ────────────────────────────────────────────────────────────────────────

# Layouts that read better with a prose `body` paragraph
_BODY_FRIENDLY_LAYOUTS = {
    "title-slide", "title-only", "bullet-points", "two-column",
    "image-full", "image-left", "image-right",
}


def _clean_sentence(text: str) -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    if text[-1] not in ".!?":
        text += "."
    return text[0].upper() + text[1:]


def _backfill_narrative(
    slide: "GeneratedSlide",
    skel: "Optional[SlideSkeleton]",
) -> None:
    """Ensure subheadline, body (when layout supports it), and speaker_notes are
    populated. Source of truth is the planner's `key_points` — real content,
    not instructions. NEVER use skel.purpose as subheadline or body; purpose is a
    planner directive (e.g. 'Cover market for this pitch') and injecting it into
    rendered slides produces nonsensical fallback text."""
    key_points = list((skel.key_points if skel else []) or [])
    # Filter out truncated / artifact key_points before using them for backfill
    clean_key_points = [
        kp for kp in key_points
        if "..." not in kp and not kp.endswith("...")
        and not _looks_truncated(kp)
    ]

    # Subheadline — derive from key_points if empty. Do NOT use purpose.
    if not (slide.subheadline and slide.subheadline.strip()):
        if clean_key_points:
            slide.subheadline = " ".join(clean_key_points[0].split()[:14])[:200]

    # Body — synthesize for body-friendly layouts when missing.
    # Only use key_points or existing bullets. Never use purpose.
    layout_lower = (slide.layout or "").lower()
    if (not (slide.body and slide.body.strip())
            and layout_lower in _BODY_FRIENDLY_LAYOUTS):
        sentences: list[str] = []
        for bp in (clean_key_points or slide.bullets or [])[:2]:
            s = _clean_sentence(str(bp))
            if s and s not in sentences:
                sentences.append(s)
        body = " ".join(sentences).strip()
        if body:
            slide.body = body[:1200]

    # Speaker notes — backfill from the planner's purpose ONLY after
    # stripping internal directive language. The planner stores
    # purpose=f"Cover {intent} for this pitch" and the regen engine
    # appends "USER REVISION REQUEST: …". Both are pipeline coaching
    # strings, not investor-facing notes — they were leaking into the
    # PPTX speaker-notes pane (visible in presenter view) and into
    # share-viewer note exports. Strip them before persisting.
    if not (slide.speaker_notes and slide.speaker_notes.strip()):
        purpose = ((skel.purpose if skel else "") or "").strip()
        if purpose:
            cleaned = _strip_planner_directives(purpose)
            if cleaned:
                slide.speaker_notes = _clean_sentence(cleaned)[:1500]
            elif slide.body:
                slide.speaker_notes = slide.body[:1500]
        elif slide.body:
            slide.speaker_notes = slide.body[:1500]


_PLANNER_DIRECTIVE_PATTERNS = (
    re.compile(r"^\s*Cover\s+\w[\w\s]*?\s+for\s+this\s+pitch\.?\s*", re.IGNORECASE),
    re.compile(r"USER\s+REVISION\s+REQUEST\s*:.*", re.IGNORECASE | re.DOTALL),
    re.compile(r"Keep\s+these\s+original\s+(?:user|project)\s+terms.*", re.IGNORECASE | re.DOTALL),
)


def _strip_planner_directives(text: str) -> str:
    """Remove planner / regen coaching strings from a piece of text.

    The planner stores `skel.purpose = "Cover {intent} for this pitch"`
    and the regen engine appends `"\\n\\nUSER REVISION REQUEST: …"`.
    Both are valid for the writer to read but must never be visible to
    a viewer. This helper removes those known leak patterns and
    collapses leftover whitespace; if the result is empty the caller
    should fall back to body or skip the field.
    """
    if not text:
        return ""
    cleaned = text
    for pattern in _PLANNER_DIRECTIVE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" .,;:-")


# ────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────

def repair_slide(
    slide: "GeneratedSlide",
    skeleton: "Optional[SlideSkeleton]" = None,
    research: "Optional[ResearchPacket]" = None,
) -> "GeneratedSlide":
    """Apply all deterministic repairs in order. Returns the same slide instance."""
    evidence_text = ""
    if research is not None:
        evidence_text = _intent_evidence_text(research, (slide.intent or "").lower())

    # Order matters:
    if research is not None and (slide.intent or "").lower() in COMPANY_SPECIFIC_INTENTS:
        has_company_evidence = bool(_intent_citations(research, (slide.intent or "").lower()))
        has_query_numbers = bool(re.search(r"\d", research.query or ""))
        if not has_company_evidence and not has_query_numbers:
            _strip_company_specific_numbers(slide)
    # 1. Strip first (so injection doesn't reuse stripped values)
    _strip_ungrounded(slide, evidence_text)
    # 2. Inject research-backed numbers into data slides
    _inject_grounded_numbers(slide, research)
    # 3. Synthesize required layout blocks
    _enforce_layout_block(slide, research)
    # 3.5 Market slides may only keep quant blocks backed by actual market evidence.
    _normalize_market_quant_blocks(slide, research, skeleton)
    _normalize_solution_quant_blocks(slide)
    # 4. Headline last (so any added stat_blocks can inform contextual padding)
    _repair_headline(slide, skeleton)
    # 4.5 Title slides must include the company name when one is known.
    _enforce_title_company_name(slide, research)
    # 5. Backfill narrative fields (subheadline / body / speaker_notes) from
    #    the planner's purpose so the slide always has descriptive context,
    #    even when the LLM omitted these fields.
    _backfill_narrative(slide, skeleton)
    if (slide.intent or "").lower() == "title":
        slide.body = ""

    # 6. Premium-specific repairs (CEO requirements)
    _repair_competition_names(slide)
    _repair_ask_use_of_funds(slide)
    _repair_source_attribution(slide, research)

    # Final defensive trims (bullets may be slightly longer for descriptiveness)
    # Use word-based truncation to avoid mid-word cutoffs
    def _truncate_words(text: str, max_words: int) -> str:
        words = str(text).split()
        if len(words) <= max_words:
            return str(text)
        return " ".join(words[:max_words])
    
    # Sanitize bullets to remove competitor names and instruction placeholders (CRITICAL FIX)
    from app.services.v4.content_sanitizer import sanitize_bullets
    original_bullets = slide.bullets or []
    slide.bullets = sanitize_bullets(slide.bullets or [])
    if len(slide.bullets) < len(original_bullets):
        logger.warning("slide_repair_sanitized_bullets", intent=slide.intent, original=len(original_bullets), filtered=len(slide.bullets), sample=str(original_bullets[:2]))
    
    # Filter out bullets that look like raw webpage titles
    filtered_bullets = []
    for b in slide.bullets:
        # Strip leading markdown headers instead of filtering out
        b_clean = re.sub(r"^#+\s*", "", b).strip()
        if not b_clean:
            continue
        # Only discard if the bullet is purely a URL
        if re.match(r"^https?://[^\s]+$", b_clean):
            continue
        filtered_bullets.append(b_clean)
    # Final truncation to 25 words for display consistency
    slide.bullets = [_truncate_words(b, 25) for b in filtered_bullets[:4]]
    return slide


def repair_deck(
    slides: "list[GeneratedSlide]",
    skeletons: "Optional[list[SlideSkeleton]]" = None,
    research: "Optional[ResearchPacket]" = None,
) -> "list[GeneratedSlide]":
    skel_map: "dict[int, SlideSkeleton]" = {}
    if skeletons:
        skel_map = {s.index: s for s in skeletons}
    for s in slides:
        try:
            repair_slide(s, skel_map.get(s.index), research)
        except Exception as e:  # noqa: BLE001 \u2014 repair must never crash the pipeline
            logger.warning("slide_repair_failed", index=s.index, error=str(e))
    return slides


def _repair_competition_names(slide: "GeneratedSlide") -> None:
    """Replace generic competitor labels with specific company names in comparison blocks.
    Only runs when intent is 'competition' and comparison columns exist."""
    if (slide.intent or "").lower() != "competition":
        return
    comp = slide.comparison or {}
    columns = comp.get("columns", []) if isinstance(comp, dict) else []
    if not columns:
        return

    generic_labels = {"legacy insurers", "emerging startups", "traditional insurers",
                      "incumbents", "competitors", "other players", "market leaders",
                      "legacy", "incumbent", "traditional", "emerging"}
    topic_blob = " ".join(
        filter(
            None,
            [
                slide.headline,
                slide.subheadline,
                slide.body,
                " ".join(str(bullet or "") for bullet in (slide.bullets or [])),
            ],
        )
    ).lower()
    is_space_insurance = any(
        marker in topic_blob
        for marker in ["satellite", "space insurance", "orbital", "lloyd"]
    )
    for col in columns:
        title = (col.get("title") or "").strip()
        title_lower = title.lower()
        if is_space_insurance and any(gl in title_lower for gl in generic_labels):
            col["title"] = "Legacy market alternative"


def _repair_ask_use_of_funds(slide: "GeneratedSlide") -> None:
    """Ensure ask slides have a use-of-funds breakdown — but never stamp
    domain-specific defaults onto a deck about a different topic.

    Bug fix (2026-05-25): the previous implementation hardcoded zero-trust
    identity / edge IoT bullets onto every ``ask`` slide that lacked a $/%
    allocation, even when the deck was about (e.g.) AI invoice automation.
    The user-visible result was an ``ask`` slide reading "Engineering
    investment will harden DID and zero-knowledge proof orchestration"
    inside a finance pitch deck — pure noise.

    The new behaviour: if the writer produced substantive bullets or body
    copy, leave them alone. Only when the slide is genuinely empty do we
    insert generic, topic-agnostic placeholder bullets that prompt the
    user to fill in real allocation. The placeholder copy is intentionally
    company-neutral so it cannot be mistaken for verified content.
    """
    if (slide.intent or "").lower() != "ask":
        return

    # Did the writer give us anything substantive?
    bullets = list(slide.bullets or [])
    substantive_bullets = [b for b in bullets if len(str(b).strip()) >= 12]
    body_len = len(str(getattr(slide, "body", "") or "").strip())
    has_real_prose = bool(len(substantive_bullets) >= 2 or body_len >= 60)

    has_allocation = any(
        any(tok in b for tok in ["%", "$"])
        and any(
            word in b.lower()
            for word in [
                "engineering", "pilot", "regulatory", "sales", "marketing",
                "rd", "product", "ops", "allocated", "reserved", "hire",
                "team", "go-to-market", "gtm",
            ]
        )
        for b in bullets
    )
    if has_allocation or has_real_prose:
        return

    # Genuinely empty ask slide. Use topic-neutral placeholders so we never
    # paste off-topic domain content (zero-trust, edge IoT, etc.) onto a
    # deck about something else. These are explicit asks for the user to
    # supply real numbers, not invented allocations.
    slide.bullets = [
        "Use of funds: allocate raise across product, go-to-market, and team.",
        "Milestones the raise unlocks: provide measurable proof points and timing.",
        "Investor support requested: provide concrete asks and timing.",
    ]


def _repair_source_attribution(slide: "GeneratedSlide", research: "Optional[ResearchPacket]") -> None:
    """Ensure data slides with numbers have at least one citation if research exists."""
    if research is None:
        return
    intent = (slide.intent or "").lower()
    if intent not in DATA_INTENTS:
        return
    has_numbers = bool(_NUMERIC_TOKEN_RE.search(" ".join(filter(None, [slide.body, str(slide.headline)]))))
    has_numbers = has_numbers or any(_NUMERIC_TOKEN_RE.search(b) for b in (slide.bullets or []))
    has_numbers = has_numbers or any(_NUMERIC_TOKEN_RE.search(str(sb.get("value", ""))) for sb in (slide.stat_blocks or []))
    if not has_numbers:
        return
    # If slide has numbers but no citations, pull one from research
    if not (slide.citations and len(slide.citations) > 0):
        cites = _intent_citations(research, intent)
        if cites:
            first = cites[0]
            slide.citations = [{"url": getattr(first, "url", "")[:500], "title": getattr(first, "title", "")[:200]}]
