"""Field-level provenance guard for Plan 10.

The guard is intentionally deterministic. It never asks an LLM to decide
whether a business-critical claim is true; it only preserves facts that are
user-provided or visible in available evidence, and marks the rest unresolved.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Optional

from app.services.v4.numeric_grounder import audit_slide
from app.services.v4.research_collector import ResearchPacket


CRITICAL_INTENTS = {
    "market",
    "traction",
    "financials",
    "ask",
    "team",
    "competition",
    "business_model",
}


@dataclass(frozen=True)
class ProvenanceIssue:
    slide_index: int
    field: str
    token: str
    category: str
    action: str


def evidence_text(
    *,
    research: ResearchPacket,
    user_query: str = "",
    structured_context: Optional[dict[str, Any]] = None,
) -> str:
    chunks: list[str] = [user_query or ""]
    if structured_context:
        chunks.append(json.dumps(structured_context, default=str, ensure_ascii=False))
    for citation in list(research.citations or []) + list(research.news_citations or []):
        chunks.append(f"{citation.title or ''} {citation.snippet or ''} {citation.url or ''}")
    return "\n".join(chunks)


def apply_provenance_guard(
    slides: list[Any],
    *,
    research: ResearchPacket,
    user_query: str = "",
    structured_context: Optional[dict[str, Any]] = None,
) -> list[ProvenanceIssue]:
    evidence = evidence_text(
        research=research,
        user_query=user_query,
        structured_context=structured_context,
    )
    issues: list[ProvenanceIssue] = []
    for slide in slides:
        issues.extend(_guard_slide(slide, evidence=evidence))
    return issues


def _guard_slide(slide: Any, *, evidence: str) -> list[ProvenanceIssue]:
    intent = str(getattr(slide, "intent", "") or "").lower().strip()
    raw = getattr(slide, "raw", None)
    if not isinstance(raw, dict):
        raw = {}
        setattr(slide, "raw", raw)

    provenance = raw.setdefault("provenance", {})
    provenance["critical_intent"] = intent in CRITICAL_INTENTS
    provenance["field_categories"] = _field_categories(slide)

    if intent not in CRITICAL_INTENTS:
        return []

    report = audit_slide(_slide_dict(slide), evidence_text=evidence, slide_index=getattr(slide, "index", 0))
    if report.is_clean:
        provenance["unsupported_numeric_count"] = 0
        return []

    tokens = [t.token for t in report.ungrounded]
    issues: list[ProvenanceIssue] = []
    for token in tokens:
        issues.append(ProvenanceIssue(
            slide_index=int(getattr(slide, "index", 0) or 0),
            field="numeric_claim",
            token=token,
            category="unsupported",
            action="removed_or_marked_unresolved",
        ))

    _remove_unsupported_numeric_content(slide, tokens)
    provenance["unsupported_numeric_count"] = len(tokens)
    provenance["unsupported_numeric_tokens"] = tokens[:12]
    provenance["action"] = "unsupported numeric claims removed; slide marked unresolved"
    setattr(slide, "requires_user_input", True)
    if not getattr(slide, "user_input_kind", None):
        setattr(slide, "user_input_kind", "evidence")
    if not getattr(slide, "user_input_reason", None):
        setattr(slide, "user_input_reason", "unsupported_business_claims")
    return issues


def _slide_dict(slide: Any) -> dict[str, Any]:
    return {
        "headline": getattr(slide, "headline", None),
        "subheadline": getattr(slide, "subheadline", None),
        "body": getattr(slide, "body", None),
        "speaker_notes": getattr(slide, "speaker_notes", None),
        "bullets": getattr(slide, "bullets", None) or [],
        "stat_blocks": getattr(slide, "stat_blocks", None) or [],
        "quote": getattr(slide, "quote", None),
        "chart": getattr(slide, "chart", None),
    }


def _field_categories(slide: Any) -> dict[str, str]:
    categories: dict[str, str] = {}
    citations = getattr(slide, "citations", None) or []
    has_upload = any(str(c.get("url") if isinstance(c, dict) else c).startswith("upload://") for c in citations)
    has_url = bool(citations)
    source = "uploaded_doc" if has_upload else "research_url" if has_url else "model_inferred"
    for field in ("headline", "subheadline", "body", "bullets", "stat_blocks", "chart", "table", "timeline", "comparison"):
        value = getattr(slide, field, None)
        if value not in (None, "", [], {}):
            categories[field] = source
    if getattr(slide, "team_members", None):
        categories["team_members"] = "user_provided_or_verified_source"
    return categories


def _contains_token(value: Any, tokens: Iterable[str]) -> bool:
    text = str(value or "")
    return any(token and token in text for token in tokens)


def _remove_unsupported_numeric_content(slide: Any, tokens: list[str]) -> None:
    bullets = [b for b in (getattr(slide, "bullets", None) or []) if not _contains_token(b, tokens)]
    setattr(slide, "bullets", bullets)

    stat_blocks = []
    for block in getattr(slide, "stat_blocks", None) or []:
        if isinstance(block, dict) and not _contains_token(block.get("value"), tokens):
            stat_blocks.append(block)
    setattr(slide, "stat_blocks", stat_blocks)

    chart = getattr(slide, "chart", None)
    if isinstance(chart, dict) and isinstance(chart.get("data"), list):
        data = [point for point in chart["data"] if not _contains_token(point.get("value") if isinstance(point, dict) else point, tokens)]
        setattr(slide, "chart", {**chart, "data": data} if data else None)

    for field in ("headline", "subheadline", "body", "speaker_notes"):
        value = getattr(slide, field, None)
        if not isinstance(value, str) or not _contains_token(value, tokens):
            continue
        if field == "headline":
            setattr(slide, field, _honest_unresolved_headline(getattr(slide, "intent", "")))
        elif field == "subheadline":
            setattr(slide, field, "Unsupported numbers need user-provided evidence before export")
        else:
            setattr(slide, field, _drop_sentences_with_tokens(value, tokens))


def _drop_sentences_with_tokens(text: str, tokens: list[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text or "")
    kept = [s for s in sentences if not _contains_token(s, tokens)]
    return " ".join(s.strip() for s in kept if s.strip())[:1200]


def _honest_unresolved_headline(intent: str) -> str:
    label = str(intent or "claim").replace("_", " ").strip().title() or "Claim"
    return f"{label} Needs Verification"


def issues_to_dicts(issues: list[ProvenanceIssue]) -> list[dict[str, Any]]:
    return [asdict(issue) for issue in issues]