"""Deterministic style guard for Plan 10.

This guard detects repetitive or generic language and records inspectable
issues. It does not call an LLM or silently rewrite user-provided facts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.services.v4 import content_rules


@dataclass(frozen=True)
class StyleIssue:
    slide_index: int
    issue: str
    detail: str
    action: str = "flagged_for_critic"


def apply_style_guard(slides: list[Any]) -> list[StyleIssue]:
    issues: list[StyleIssue] = []
    seen_headlines: dict[str, int] = {}
    seen_subheads: dict[str, int] = {}

    for slide in slides:
        index = int(getattr(slide, "index", 0) or 0)
        raw = getattr(slide, "raw", None)
        if not isinstance(raw, dict):
            raw = {}
            setattr(slide, "raw", raw)

        headline = str(getattr(slide, "headline", "") or "").strip()
        subheadline = str(getattr(slide, "subheadline", "") or "").strip()
        body = str(getattr(slide, "body", "") or "")
        bullets = [str(b) for b in (getattr(slide, "bullets", None) or [])]

        generic_hits = content_rules.detect_generic_phrases(headline, subheadline, body, *bullets)
        for hit in generic_hits:
            issues.append(StyleIssue(index, "generic_phrase", hit))

        normalized_headline = _normalize(headline)
        if normalized_headline:
            if normalized_headline in seen_headlines:
                issues.append(StyleIssue(
                    index,
                    "repeated_headline",
                    f"matches slide {seen_headlines[normalized_headline]}",
                ))
            else:
                seen_headlines[normalized_headline] = index

        normalized_sub = _normalize(subheadline)
        if normalized_sub:
            if normalized_sub in seen_subheads:
                issues.append(StyleIssue(
                    index,
                    "repeated_subheadline",
                    f"matches slide {seen_subheads[normalized_sub]}",
                ))
            else:
                seen_subheads[normalized_sub] = index

    by_index: dict[int, list[dict[str, str]]] = {}
    for issue in issues:
        by_index.setdefault(issue.slide_index, []).append(asdict(issue))
    for slide in slides:
        slide_issues = by_index.get(int(getattr(slide, "index", 0) or 0), [])
        if slide_issues:
            raw = getattr(slide, "raw", None)
            if isinstance(raw, dict):
                raw["style_issues"] = slide_issues
    return issues


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def issues_to_dicts(issues: list[StyleIssue]) -> list[dict[str, Any]]:
    return [asdict(issue) for issue in issues]