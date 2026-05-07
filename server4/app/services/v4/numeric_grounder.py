"""
V4 Numeric Grounder — anti-hallucination guard for slide stats.

LLMs love to invent numbers. ("$2.4B TAM growing at 24% CAGR" — beautiful,
often fictional.) This module:

  1. Extracts every numeric/percent/currency token from a generated slide
     (headline, subheadline, bullets, body, stat_blocks).
  2. Checks each token against the research evidence corpus (citation
     titles + snippets concatenated).
  3. Returns a `NumericAuditReport` listing ungrounded tokens with their
     containing field, so the critic can request a rewrite.

Tolerance:
  - Tokens are normalised: "$2.4B" -> "2.4b", "24%" -> "24%", "10,000" -> "10000"
  - Match is substring-on-normalised: if the research mentions "2.4B" anywhere,
    the slide can claim "$2.4B" without flagging.
  - Tiny ints (0-9) and years (1900-2100) are whitelisted by default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

import structlog

logger = structlog.get_logger(__name__)


# Token patterns
_CURRENCY_RE = re.compile(r"\$\s?\d[\d,]*\.?\d*\s?[KMBTkmbt]?")
_PERCENT_RE = re.compile(r"\d[\d,]*\.?\d*\s?%")
_MAGNITUDE_RE = re.compile(r"\b\d[\d,]*\.?\d*\s?[KMBTkmbt](?![a-zA-Z])")  # 2.4B, 10K, 1.2T
_PLAIN_NUM_RE = re.compile(r"\b\d[\d,]*\.?\d*\b")

_PATTERNS = [_CURRENCY_RE, _PERCENT_RE, _MAGNITUDE_RE, _PLAIN_NUM_RE]


@dataclass
class UngroundedToken:
    field: str             # "headline" | "bullet[2]" | "stat_blocks[0].value" | etc.
    token: str             # raw token as it appeared
    normalised: str        # normalised form used for matching


@dataclass
class NumericAuditReport:
    slide_index: int
    total_tokens: int = 0
    grounded_tokens: int = 0
    ungrounded: list[UngroundedToken] = field(default_factory=list)
    grounding_score: float = 1.0  # 1.0 = all grounded; 0.0 = all hallucinated

    @property
    def is_clean(self) -> bool:
        return not self.ungrounded


def _normalise(token: str) -> str:
    t = token.strip().lower().replace(" ", "").replace("$", "").replace(",", "")
    return t


def _is_whitelisted(normalised: str) -> bool:
    """Tiny integers (0-9) and 4-digit years are not worth grounding."""
    bare = normalised.rstrip("%kmbt").rstrip(".")
    try:
        f = float(bare)
    except ValueError:
        return False
    if 0 <= f <= 9 and "." not in bare:
        return True
    if 1900 <= f <= 2100 and "." not in bare and "%" not in normalised:
        return True
    return False


def _extract_tokens(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    seen_spans: list[tuple[int, int]] = []
    for pat in _PATTERNS:
        for m in pat.finditer(text):
            span = (m.start(), m.end())
            # Avoid double-counting nested matches (e.g. plain-num inside currency)
            if any(s <= span[0] and e >= span[1] for s, e in seen_spans):
                continue
            seen_spans.append(span)
            found.append(m.group(0))
    return found


def _iter_slide_text_fields(slide: dict) -> Iterable[tuple[str, str]]:
    """Yield (field_label, text) tuples for every textual field of a slide."""
    for k in ("headline", "subheadline", "body", "speaker_notes"):
        v = slide.get(k)
        if isinstance(v, str) and v.strip():
            yield (k, v)
    for i, b in enumerate(slide.get("bullets") or []):
        if isinstance(b, str) and b.strip():
            yield (f"bullets[{i}]", b)
    for i, sb in enumerate(slide.get("stat_blocks") or []):
        if isinstance(sb, dict):
            v = sb.get("value")
            lbl = sb.get("label")
            if isinstance(v, str) and v.strip():
                yield (f"stat_blocks[{i}].value", v)
            if isinstance(lbl, str) and lbl.strip():
                yield (f"stat_blocks[{i}].label", lbl)
    q = slide.get("quote")
    if isinstance(q, dict) and isinstance(q.get("text"), str):
        yield ("quote.text", q["text"])
    chart = slide.get("chart")
    if isinstance(chart, dict):
        for i, p in enumerate(chart.get("data") or []):
            if isinstance(p, dict):
                v = p.get("value")
                if v is not None:
                    yield (f"chart.data[{i}].value", str(v))


def audit_slide(slide: dict, *, evidence_text: str, slide_index: int = 0) -> NumericAuditReport:
    """Return a numeric-grounding report for one slide.

    `evidence_text` should be the concatenated titles+snippets of the research
    citations available to this slide.
    """
    haystack = _normalise(evidence_text)
    report = NumericAuditReport(slide_index=slide_index)

    for field_label, text in _iter_slide_text_fields(slide):
        for tok in _extract_tokens(text):
            normalised = _normalise(tok)
            if not normalised:
                continue
            report.total_tokens += 1
            if _is_whitelisted(normalised):
                report.grounded_tokens += 1
                continue
            # Match against haystack (substring)
            bare = normalised.rstrip("%")
            if bare and bare in haystack:
                report.grounded_tokens += 1
            else:
                report.ungrounded.append(
                    UngroundedToken(field=field_label, token=tok, normalised=normalised)
                )

    if report.total_tokens > 0:
        report.grounding_score = report.grounded_tokens / report.total_tokens
    return report


def audit_deck(slides: list[dict], evidence_text: str) -> list[NumericAuditReport]:
    return [
        audit_slide(s, evidence_text=evidence_text, slide_index=i)
        for i, s in enumerate(slides)
    ]
