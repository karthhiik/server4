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
DATA_INTENTS = {"market", "traction", "financials", "metrics", "kpi", "growth"}
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
    parts = [research.query or ""]
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
    """Remove unsupported numbers from company-specific slides.

    This prevents generic pitch-deck example amounts from leaking into traction,
    financials, or ask slides for a company that has no grounded metrics in the
    prompt, uploaded docs, or research.
    """
    slide.headline = _scrub_numeric_tokens(slide.headline) or slide.headline
    if slide.subheadline:
        slide.subheadline = _scrub_numeric_tokens(slide.subheadline) or slide.subheadline
    if slide.body:
        slide.body = _scrub_numeric_tokens(slide.body) or slide.body
    slide.bullets = [b for b in slide.bullets if not any(ch.isdigit() for ch in b)]
    slide.stat_blocks = []
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
    """Remove or neutralize numeric tokens that aren't backed by research."""
    if not evidence_text:
        return
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
            text = text.replace(tok, "").replace("  ", " ").strip(" .,;:")
        return text

    # Headline / subheadline / body \u2014 just scrub the offending tokens
    slide.headline = _scrub(slide.headline) or slide.headline
    if slide.subheadline:
        slide.subheadline = _scrub(slide.subheadline) or slide.subheadline
    if slide.body:
        slide.body = _scrub(slide.body) or slide.body

    # Bullets containing ungrounded numbers \u2014 drop the whole bullet
    slide.bullets = [b for b in slide.bullets if not any(tok in b for tok in bad_tokens)]

    # stat_blocks containing ungrounded numbers \u2014 drop the block
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
    if not trustworthy_stats:
        # DOMAIN-AWARE fallback — never inject finance-domain boilerplate.
        # Source of truth (in priority order):
        #   1. Planner's key_points for this slide
        #   2. Writer's existing bullets (stripped of fake numbers)
        #   3. Research citation titles paraphrased into demand-driver claims
        #   4. User query rephrased into a single demand statement
        slide.stat_blocks = []
        slide.chart = None
        if (slide.layout or "").lower() in {"market-size-graph", "grid-3", "stat-hero", "chart-focus"}:
            slide.layout = "two-column"
        if re.search(r"\d", slide.headline or "") or any(
            marker in (slide.headline or "").lower() for marker in ("arr", "mrr", "product-market fit")
        ):
            slide.headline = "Market Opportunity Today"

        candidate_bullets: list[str] = []
        # 1. Planner's own key_points (they were drafted with domain context)
        if skel and skel.key_points:
            for kp in skel.key_points:
                kp_clean = _scrub_numeric_tokens(kp) or kp
                kp_clean = kp_clean.strip(" .,;:-")
                if kp_clean and len(kp_clean.split()) >= 3 and not _looks_instructional_copy(kp_clean):
                    candidate_bullets.append(kp_clean[:140])
                if len(candidate_bullets) >= 3:
                    break
        # 2. Writer's surviving bullets
        if len(candidate_bullets) < 3:
            for b in (slide.bullets or []):
                b_clean = _scrub_numeric_tokens(b).strip(" .,;:-")
                if (
                    b_clean
                    and b_clean not in candidate_bullets
                    and len(b_clean.split()) >= 3
                    and not _looks_instructional_copy(b_clean)
                ):
                    candidate_bullets.append(b_clean[:140])
                if len(candidate_bullets) >= 3:
                    break
        # 3. Research citation titles, paraphrased into demand statements
        if len(candidate_bullets) < 3:
            cites = _intent_citations(research, "market")
            for cite in cites[:10]:
                title = " ".join(((cite.title or "")[:120]).split())
                title = re.sub(r"[|\-—].*$", "", title).strip()
                title = _scrub_numeric_tokens(title).strip(" .,;:-")
                if (
                    title
                    and len(title.split()) >= 4
                    and title not in candidate_bullets
                    and not _looks_instructional_copy(title)
                ):
                    candidate_bullets.append(title[:140])
                if len(candidate_bullets) >= 3:
                    break
        # 4. Last-resort: derive a single statement from the user query
        if not candidate_bullets:
            q = " ".join((research.query or "").split())[:140]
            if q:
                candidate_bullets.append(q)

        slide.bullets = candidate_bullets[:5]
        # Subheadline — derive from skel.purpose or keep writer's existing one
        if skel and (skel.purpose or "").strip():
            slide.subheadline = " ".join(skel.purpose.split()[:18])[:200]
        elif not slide.subheadline:
            slide.subheadline = "Where demand is concentrated and why it grows"
        # Body — conservative paraphrase; never finance-domain default
        if not slide.body:
            company = (research.company_name or "").strip()
            topic = (research.query or "").strip().split(".")[0][:160]
            if company and topic:
                slide.body = (
                    f"{company} operates in a market where buyers increasingly seek specialized "
                    f"solutions. {topic}."
                )
            elif topic:
                slide.body = f"Buyers increasingly seek specialized solutions in this market. {topic}."
        return
    slide.stat_blocks = trustworthy_stats
    slide.chart = None
    if (slide.layout or "").lower() not in {"grid-3", "stat-hero"}:
        slide.layout = "grid-3" if len(trustworthy_stats) > 1 else "stat-hero"


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
    populated. Source of truth is the planner's `purpose` and `key_points` —
    we never invent new facts, only paraphrase what the skeleton already
    committed to."""
    purpose = ((skel.purpose if skel else "") or "").strip()
    key_points = list((skel.key_points if skel else []) or [])

    # Subheadline — derive from purpose if empty
    if not (slide.subheadline and slide.subheadline.strip()):
        if purpose:
            words = purpose.split()
            slide.subheadline = " ".join(words[:14])[:200]
        elif key_points:
            slide.subheadline = " ".join(key_points[0].split()[:14])[:200]

    # Body — synthesize for body-friendly layouts when missing
    layout_lower = (slide.layout or "").lower()
    if (not (slide.body and slide.body.strip())
            and layout_lower in _BODY_FRIENDLY_LAYOUTS):
        sentences: list[str] = []
        if purpose:
            sentences.append(_clean_sentence(purpose))
        for bp in (key_points or slide.bullets or [])[:2]:
            s = _clean_sentence(str(bp))
            if s and s not in sentences:
                sentences.append(s)
        body = " ".join(sentences).strip()
        if body:
            slide.body = body[:1200]

    # Speaker notes — fall back to purpose
    if not (slide.speaker_notes and slide.speaker_notes.strip()):
        if purpose:
            slide.speaker_notes = _clean_sentence(purpose)[:1500]
        elif slide.body:
            slide.speaker_notes = slide.body[:1500]


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

    # Final defensive trims (bullets may be slightly longer for descriptiveness)
    slide.bullets = [b[:200] for b in slide.bullets][:4]
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
