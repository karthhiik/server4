"""Free/local production-readiness checks for compiled V4 decks.

This module is intentionally deterministic. It does not call paid APIs or
invent missing evidence; it annotates the generated deck with concrete risks
that downstream UI, export, and tests can inspect.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from app.services.v4.narrative_arcs import get_arc_for_purpose
from app.services.v4.composition_engine import rhythm_window_score
from app.services.v4.uiux_advisor import evaluate_anti_patterns
from app.services.v4.validators import validate_compiled_slide


_SCHEMA_VERSION = 1
_NUMERIC_CLAIM_RE = re.compile(
    r"(?:[$]\s*\d[\d,.]*|\b\d+(?:\.\d+)?\s*(?:%|x|k|m|b|bn|mn|million|billion|trillion|ms|sec|days|months|years)\b)",
    re.IGNORECASE,
)
_ASSUMPTION_TERMS = (
    "assumption",
    "assumed",
    "estimate",
    "estimated",
    "projected",
    "projection",
    "target",
    "pending",
    "requires input",
    "needs input",
)
_PLACEHOLDER_TERMS = (
    "placeholder",
    "lorem ipsum",
    "metric pending",
    "insert ",
    "your company",
    "company name",
    "tbd",
)


@dataclass(frozen=True)
class ProductionGateIssue:
    code: str
    severity: str
    slide_index: int | None
    message: str
    target: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SlideProductionReport:
    slide_index: int
    passed: bool
    blocked: bool
    score: int
    issues: list[ProductionGateIssue] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_index": self.slide_index,
            "passed": self.passed,
            "blocked": self.blocked,
            "score": self.score,
            "issues": [issue.to_dict() for issue in self.issues],
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class DeckProductionReport:
    schema_version: int
    passed: bool
    blocked: bool
    score: int
    summary: str
    issue_totals: dict[str, int]
    slide_reports: list[SlideProductionReport]
    issues: list[ProductionGateIssue]
    checks: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "passed": self.passed,
            "blocked": self.blocked,
            "score": self.score,
            "summary": self.summary,
            "issue_totals": self.issue_totals,
            "slide_reports": [report.to_dict() for report in self.slide_reports],
            "issues": [issue.to_dict() for issue in self.issues],
            "checks": self.checks,
        }


def evaluate_production_quality(
    *,
    compiled_slides: Sequence[Mapping[str, Any]],
    source_slides: Sequence[Any] | None = None,
    design_tokens: Mapping[str, Any] | None = None,
    mode: str | None = "standard",
    user_query: str = "",
) -> DeckProductionReport:
    """Evaluate a compiled deck using only local deterministic signals."""

    source_by_index = _source_by_index(source_slides or [])
    slide_reports: list[SlideProductionReport] = []
    deck_issues: list[ProductionGateIssue] = []
    kit_sequence: list[str] = []
    layout_sequence: list[str] = []
    gate_mode = _gate_mode(mode)

    for position, compiled in enumerate(compiled_slides):
        slide_index = _slide_index(compiled, position)
        source = source_by_index.get(slide_index)
        report = _evaluate_slide(
            compiled=compiled,
            source=source,
            slide_index=slide_index,
            design_tokens=design_tokens or {},
            mode=gate_mode,
            user_query=user_query,
        )
        slide_reports.append(report)
        kit_sequence.append(str(compiled.get("kit_component") or ""))
        layout_intent = compiled.get("layout_intent")
        layout_sequence.append(
            str(layout_intent.get("key") or "") if isinstance(layout_intent, Mapping) else ""
        )

    deck_issues.extend(_deck_rhythm_issues(kit_sequence, layout_sequence))
    deck_issues.extend(
        _deck_quality_teeth_issues(
            compiled_slides=compiled_slides,
            slide_reports=slide_reports,
            mode=gate_mode,
        )
    )
    score = _deck_score(slide_reports, deck_issues)
    blocked = any(report.blocked for report in slide_reports) or any(
        issue.severity == "blocker" for issue in deck_issues
    )
    passed = not blocked and score >= 75
    totals = _issue_totals(
        [issue for report in slide_reports for issue in report.issues] + deck_issues
    )
    summary = _summary(passed=passed, blocked=blocked, score=score, totals=totals)
    all_issues = [issue for report in slide_reports for issue in report.issues] + deck_issues

    def _check_clear(*codes: str) -> bool:
        return not any(
            issue.severity == "blocker"
            and any(str(issue.code).startswith(code) for code in codes)
            for issue in all_issues
        )

    return DeckProductionReport(
        schema_version=_SCHEMA_VERSION,
        passed=passed,
        blocked=blocked,
        score=score,
        summary=summary,
        issue_totals=totals,
        slide_reports=slide_reports,
        issues=deck_issues,
        checks={
            "compiled_contract": _check_clear("compiled_"),
            "evidence_provenance": _check_clear("unsupported_numeric_claims"),
            "layout_density": _check_clear("layout_", "density_", "placeholder_text_visible"),
            "deck_visual_rhythm": _check_clear("deck_", "rhythm_", "duplicate_"),
            "slide_quality_teeth": _check_clear("ai_style_", "anti_pattern_", "image_pending_before_delivery"),
            "export_readiness_metadata": True,
        },
    )


def attach_production_quality_gate(
    *,
    compiled_slides: list[dict[str, Any]],
    source_slides: Sequence[Any] | None = None,
    design_tokens: Mapping[str, Any] | None = None,
    mode: str | None = "standard",
    user_query: str = "",
) -> DeckProductionReport:
    report = evaluate_production_quality(
        compiled_slides=compiled_slides,
        source_slides=source_slides,
        design_tokens=design_tokens,
        mode=mode,
        user_query=user_query,
    )
    by_index = {slide.slide_index: slide for slide in report.slide_reports}
    for position, compiled in enumerate(compiled_slides):
        if not isinstance(compiled, dict):
            continue
        slide_index = _slide_index(compiled, position)
        slide_report = by_index.get(slide_index)
        if slide_report:
            compiled["production_quality_gate"] = slide_report.to_dict()
    return report


def summarize_production_quality_gate(compiled_slides: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    reports = [
        slide.get("production_quality_gate")
        for slide in compiled_slides
        if isinstance(slide, Mapping) and isinstance(slide.get("production_quality_gate"), Mapping)
    ]
    if not reports:
        return {
            "schema_version": _SCHEMA_VERSION,
            "passed": False,
            "blocked": True,
            "score": 0,
            "summary": "Production quality gate has not run; export readiness is unknown.",
            "issue_totals": {},
            "slide_reports": [],
            "issues": [],
            "checks": {
                "compiled_contract": False,
                "evidence_provenance": False,
                "layout_density": False,
                "deck_visual_rhythm": False,
                "slide_quality_teeth": False,
                "export_readiness_metadata": False,
            },
        }
    issues: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
    scores: list[int] = []
    blocked = False
    for report in reports:
        scores.append(int(report.get("score") or 0))
        blocked = blocked or bool(report.get("blocked"))
        for issue in report.get("issues") or []:
            if isinstance(issue, Mapping):
                severity = str(issue.get("severity") or "warn")
                totals[severity] = totals.get(severity, 0) + 1
                issues.append(dict(issue))
    score = int(round(sum(scores) / max(1, len(scores))))
    passed = not blocked and score >= 75
    return {
        "schema_version": _SCHEMA_VERSION,
        "passed": passed,
        "blocked": blocked,
        "score": score,
        "summary": _summary(passed=passed, blocked=blocked, score=score, totals=totals),
        "issue_totals": totals,
        "slide_reports": list(reports),
        "issues": issues,
        "checks": {
            "compiled_contract": True,
            "evidence_provenance": True,
            "layout_density": True,
            "deck_visual_rhythm": False,
            "export_readiness_metadata": True,
        },
    }


def _evaluate_slide(
    *,
    compiled: Mapping[str, Any],
    source: Any,
    slide_index: int,
    design_tokens: Mapping[str, Any],
    mode: str,
    user_query: str = "",
) -> SlideProductionReport:
    issues: list[ProductionGateIssue] = []
    props = _props(compiled)
    l1 = validate_compiled_slide(compiled)
    for issue in l1.issues:
        issues.append(
            ProductionGateIssue(
                code=f"compiled_{issue.code}",
                severity="blocker" if issue.severity == "error" else "warn",
                slide_index=slide_index,
                message=issue.message,
                target=issue.target,
                recommendation="Regenerate or repair this slide before export." if issue.severity == "error" else "Review this slide in Studio.",
            )
        )

    _append_density_issues(props, slide_index, issues)
    for anti_pattern in evaluate_anti_patterns(compiled, design_tokens):
        issues.append(
            ProductionGateIssue(
                code=anti_pattern.code,
                severity=_teeth_severity(mode),
                slide_index=slide_index,
                message=anti_pattern.message,
                target=anti_pattern.target,
                recommendation=f"Why this matters: {anti_pattern.rule_id}. Replace the style with catalog-backed tokens.",
            )
        )
    provenance = _provenance(source=source, compiled=compiled, props=props, user_query=user_query)
    if provenance["numeric_claim_count"] and provenance["status"] == "unsupported_numeric_claims":
        issues.append(
            ProductionGateIssue(
                code="unsupported_numeric_claims",
                severity="blocker",
                slide_index=slide_index,
                message="Numeric claims are present without citations, links, user-provided evidence, or clear assumption wording.",
                target="claims",
                recommendation="Attach a source, mark the number as an assumption, or request founder input.",
            )
        )

    if _contains_placeholder(_visible_text(props)):
        issues.append(
            ProductionGateIssue(
                code="placeholder_text_visible",
                severity="blocker",
                slide_index=slide_index,
                message="Placeholder-style text is visible in the compiled slide.",
                target="visible_text",
                recommendation="Replace placeholder wording with user-provided or sourced content.",
            )
        )

    if compiled.get("pending_image") and not _has_image_url(props, compiled):
        issues.append(
            ProductionGateIssue(
                code="image_pending_before_delivery",
                severity="warn",
                slide_index=slide_index,
                message="The slide expects imagery but has no resolved image URL yet.",
                target="image",
                recommendation="Keep the slide editable and avoid exporting until the image pipeline finishes.",
            )
        )

    if not compiled.get("render_qa"):
        issues.append(
            ProductionGateIssue(
                code="render_qa_missing",
                severity="warn",
                slide_index=slide_index,
                message="Render QA metadata is missing for this compiled slide.",
                target="render_qa",
                recommendation="Recompile the slide so export and presentation checks have stable timing metadata.",
            )
        )

    quality_score = compiled.get("quality_score")
    if isinstance(quality_score, Mapping) and int(quality_score.get("overall") or 0) < 70:
        issues.append(
            ProductionGateIssue(
                code="low_local_visual_score",
                severity="warn",
                slide_index=slide_index,
                message="Local contrast/alignment/density score is below the production threshold.",
                target="quality_score",
                recommendation="Use Studio visual regeneration or reduce content density.",
            )
        )

    score = _slide_score(issues, quality_score, design_tokens)
    blocked = any(issue.severity == "blocker" for issue in issues)
    return SlideProductionReport(
        slide_index=slide_index,
        passed=not blocked and score >= 75,
        blocked=blocked,
        score=score,
        issues=issues,
        provenance=provenance,
    )


def _append_density_issues(
    props: Mapping[str, Any],
    slide_index: int,
    issues: list[ProductionGateIssue],
) -> None:
    headline = str(props.get("headline") or props.get("title") or "")
    if len(headline.split()) > 12:
        issues.append(
            ProductionGateIssue(
                code="headline_too_long_for_slide",
                severity="warn",
                slide_index=slide_index,
                message="Headline is likely too long for projector-safe rendering.",
                target="headline",
                recommendation="Compress the headline into a sharper investor-grade claim.",
            )
        )
    words = _visible_word_count(props)
    if words > 135:
        issues.append(
            ProductionGateIssue(
                code="slide_text_density_high",
                severity="warn",
                slide_index=slide_index,
                message="Visible text density is high for a single professional slide.",
                target="props",
                recommendation="Split this into two slides or convert detail into chart/table structure.",
            )
        )


def _provenance(*, source: Any, compiled: Mapping[str, Any], props: Mapping[str, Any], user_query: str = "") -> dict[str, Any]:
    visible = _visible_text(props)
    numeric_claims = _NUMERIC_CLAIM_RE.findall(visible)
    citations = list(getattr(source, "citations", []) or [])
    links = list(getattr(source, "links", []) or [])
    requires_input = bool(getattr(source, "requires_user_input", False))
    source_slide = compiled.get("source_slide")
    if not isinstance(source_slide, Mapping):
        artifacts = compiled.get("artifacts")
        kit = artifacts.get("kit_jsx") if isinstance(artifacts, Mapping) else None
        source_slide = kit.get("source_slide") if isinstance(kit, Mapping) and isinstance(kit.get("source_slide"), Mapping) else {}
    raw_citations = list(source_slide.get("citations") or []) if isinstance(source_slide, Mapping) else []
    assumption_marked = any(term in visible.lower() for term in _ASSUMPTION_TERMS)
    citation_count = len(citations) + len(raw_citations)
    link_count = len(links)

    # Check if the numeric claims are present in the user query (case-insensitive, normalised)
    user_query_normalized = re.sub(r"[\s,$]", "", user_query.lower()) if user_query else ""
    all_numeric_claims_in_user_query = True
    if numeric_claims and user_query_normalized:
        for claim in numeric_claims:
            claim_norm = re.sub(r"[\s,$]", "", claim.lower())
            if claim_norm not in user_query_normalized:
                all_numeric_claims_in_user_query = False
                break
    else:
        all_numeric_claims_in_user_query = False

    if not numeric_claims:
        status = "no_numeric_claims"
    elif citation_count or link_count:
        status = "source_backed"
    elif all_numeric_claims_in_user_query:
        status = "source_backed"
    elif assumption_marked or requires_input:
        status = "marked_assumption_or_input_needed"
    else:
        status = "unsupported_numeric_claims"

    return {
        "status": status,
        "numeric_claim_count": len(numeric_claims),
        "numeric_claims_preview": numeric_claims[:5],
        "citation_count": citation_count,
        "link_count": link_count,
        "requires_user_input": requires_input,
        "assumption_marked": assumption_marked,
    }


def _deck_rhythm_issues(kit_sequence: Sequence[str], layout_sequence: Sequence[str]) -> list[ProductionGateIssue]:
    issues: list[ProductionGateIssue] = []
    rhythm = rhythm_window_score(list(kit_sequence), window_size=5)
    for window in rhythm.get("windows") or []:
        if not window.get("passes"):
            issues.append(
                ProductionGateIssue(
                    code="deck_kit_rhythm_flat",
                    severity="warn",
                    slide_index=int(window.get("end") or 0),
                    message="Five-slide window uses fewer than three distinct kit components.",
                    target="kit_sequence",
                    recommendation="Regenerate one slide in this window to restore boardroom visual rhythm.",
                )
            )
            break
    for label, sequence in (("kit", kit_sequence), ("layout", layout_sequence)):
        streak_value = ""
        streak = 0
        for idx, value in enumerate(sequence):
            if value and value == streak_value:
                streak += 1
            else:
                streak_value = value
                streak = 1
            if streak >= 4:
                issues.append(
                    ProductionGateIssue(
                        code=f"deck_{label}_repetition",
                        severity="warn",
                        slide_index=idx,
                        message=f"Four adjacent slides use the same {label} pattern.",
                        target=f"{label}_sequence",
                        recommendation="Regenerate visuals for one of these slides to improve deck rhythm.",
                    )
                )
                break
    return issues


def _gate_mode(mode: str | None) -> str:
    return "premium" if str(mode or "").lower() == "premium" else "standard"


def _teeth_severity(mode: str) -> str:
    return "blocker" if mode == "premium" else "warn"


def _headline_duplication(compiled_slides: Sequence[Mapping[str, Any]]) -> tuple[float, list[str]]:
    counts: dict[str, int] = {}
    for compiled in compiled_slides:
        props = _props(compiled)
        headline = _normalize_headline(str(props.get("headline") or props.get("title") or ""))
        if not headline:
            continue
        counts[headline] = counts.get(headline, 0) + 1
    duplicates = [headline for headline, count in counts.items() if count > 1]
    duplicate_instances = sum(count - 1 for count in counts.values() if count > 1)
    denominator = max(1, len([1 for compiled in compiled_slides if _props(compiled)]))
    return duplicate_instances / denominator, duplicates


def _normalize_headline(headline: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", headline.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _narrative_flow_score(compiled_slides: Sequence[Mapping[str, Any]]) -> int:
    if len(compiled_slides) < 4:
        return 100
    expected = [slot.intent for slot in get_arc_for_purpose("pitch_deck")]
    rank = {intent: idx for idx, intent in enumerate(expected)}
    observed: list[int] = []
    for compiled in compiled_slides:
        intent = _slide_intent(compiled)
        if not intent:
            continue
        observed.append(_intent_rank(intent, rank))
    observed = [value for value in observed if value is not None]
    if len(observed) < 4:
        return 100
    inversions = sum(1 for left, right in zip(observed, observed[1:]) if right < left)
    max_inversions = max(1, len(observed) - 1)
    score = 100 - int(round((inversions / max_inversions) * 100))
    return max(0, min(100, score))


def _slide_intent(compiled: Mapping[str, Any]) -> str:
    for key in ("intent", "slide_intent", "narrative_role"):
        value = compiled.get(key)
        if value:
            return str(value).lower()
    layout_intent = compiled.get("layout_intent")
    if isinstance(layout_intent, Mapping):
        for key in ("intent", "key", "role"):
            value = layout_intent.get(key)
            if value:
                return str(value).lower()
    props = _props(compiled)
    value = props.get("intent") if isinstance(props, Mapping) else None
    return str(value or "").lower()


def _intent_rank(intent: str, rank: Mapping[str, int]) -> int | None:
    normalized = intent.lower().replace("-", "_").strip()
    if normalized in rank:
        return rank[normalized]
    aliases = {
        "cover": "title",
        "close": "contact",
        "closing": "contact",
        "cta": "ask",
        "funding": "ask",
        "go_to_market": "business_model",
        "gtm": "business_model",
        "how_it_works": "how_it_works",
        "architecture": "how_it_works",
    }
    alias = aliases.get(normalized)
    if alias:
        return rank.get(alias)
    for key, value in rank.items():
        if key in normalized or normalized in key:
            return value
    return None


def _deck_quality_teeth_issues(
    *,
    compiled_slides: Sequence[Mapping[str, Any]],
    slide_reports: Sequence[SlideProductionReport],
    mode: str,
) -> list[ProductionGateIssue]:
    issues: list[ProductionGateIssue] = []
    severity = _teeth_severity(mode)
    total = max(1, len(compiled_slides))

    duplicate_ratio, duplicate_titles = _headline_duplication(compiled_slides)
    if duplicate_ratio > 0.10:
        issues.append(
            ProductionGateIssue(
                code="headline_duplication",
                severity=severity,
                slide_index=None,
                message=(
                    f"{len(duplicate_titles)} repeated headline pattern(s) cover "
                    f"{int(round(duplicate_ratio * 100))}% of the deck."
                ),
                target="headlines",
                recommendation="Why this matters: ux.headline_diversity. Rewrite repeated slide titles as distinct claims.",
            )
        )

    narrative_score = _narrative_flow_score(compiled_slides)
    if narrative_score < 70:
        issues.append(
            ProductionGateIssue(
                code="narrative_flow_weak",
                severity=severity,
                slide_index=None,
                message=f"Deck narrative flow score is {narrative_score}/100.",
                target="slide_intents",
                recommendation="Why this matters: narrative.arc_order. Reorder or regenerate slides around a clear pitch arc.",
            )
        )

    dense_count = sum(
        1
        for report in slide_reports
        for issue in report.issues
        if issue.code == "slide_text_density_high"
    )
    if dense_count / total > 0.25:
        issues.append(
            ProductionGateIssue(
                code="density_violations",
                severity=severity,
                slide_index=None,
                message=f"{dense_count} slide(s) exceed boardroom-safe text density.",
                target="visible_text",
                recommendation="Why this matters: ux.data_density. Split dense slides or convert detail into structured visuals.",
            )
        )

    placeholder_count = sum(
        1
        for report in slide_reports
        for issue in report.issues
        if issue.code == "placeholder_text_visible"
    )
    if placeholder_count and not any(issue.code == "placeholder_text_visible" for issue in issues):
        issues.append(
            ProductionGateIssue(
                code="placeholder_text_visible",
                severity=severity,
                slide_index=None,
                message=f"{placeholder_count} slide(s) contain visible placeholder text.",
                target="visible_text",
                recommendation="Why this matters: ux.error_clarity. Replace all placeholders before presenting.",
            )
        )
    return issues


def _slide_score(
    issues: Sequence[ProductionGateIssue],
    quality_score: Any,
    design_tokens: Mapping[str, Any],
) -> int:
    score = 100
    for issue in issues:
        if issue.severity == "blocker":
            score -= 28
        elif issue.severity == "error":
            score -= 20
        else:
            score -= 8
    if isinstance(quality_score, Mapping):
        score = min(score, max(0, int(quality_score.get("overall") or score)))
    if not design_tokens:
        score -= 4
    return max(0, min(100, score))


def _deck_score(slide_reports: Sequence[SlideProductionReport], deck_issues: Sequence[ProductionGateIssue]) -> int:
    if not slide_reports:
        return 0
    base = sum(report.score for report in slide_reports) / len(slide_reports)
    penalty = sum(12 if issue.severity == "blocker" else 4 for issue in deck_issues)
    return max(0, min(100, int(round(base - penalty))))


def _issue_totals(issues: Sequence[ProductionGateIssue]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for issue in issues:
        totals[issue.severity] = totals.get(issue.severity, 0) + 1
    return totals


def _summary(*, passed: bool, blocked: bool, score: int, totals: Mapping[str, int]) -> str:
    if passed:
        return f"Production-ready local quality gate passed with score {score}/100."
    if blocked:
        return f"Production gate found {totals.get('blocker', 0)} blocker(s); deck remains editable but needs review before investor export."
    return f"Production gate score is {score}/100; review warnings before high-stakes sharing."


def _source_by_index(source_slides: Sequence[Any]) -> dict[int, Any]:
    out: dict[int, Any] = {}
    for position, slide in enumerate(source_slides):
        try:
            index = int(getattr(slide, "index"))
        except Exception:
            index = position
        out[index] = slide
    return out


def _slide_index(compiled: Mapping[str, Any], fallback: int) -> int:
    for key in ("slide_index", "index"):
        try:
            return int(compiled.get(key))
        except Exception:
            continue
    slide_id = str(compiled.get("slide_id") or "")
    match = re.search(r"(\d+)$", slide_id)
    if match:
        return int(match.group(1))
    return fallback


def _props(compiled: Mapping[str, Any]) -> Mapping[str, Any]:
    artifacts = compiled.get("artifacts")
    if isinstance(artifacts, Mapping):
        kit = artifacts.get("kit_jsx")
        if isinstance(kit, Mapping) and isinstance(kit.get("props_json"), Mapping):
            return kit["props_json"]
    render_props = compiled.get("render_props")
    if isinstance(render_props, Mapping):
        return render_props
    return {}


def _visible_word_count(value: Any) -> int:
    if isinstance(value, str):
        return len(value.split())
    if isinstance(value, Mapping):
        return sum(
            _visible_word_count(v)
            for key, v in value.items()
            if key not in {"designTokens", "imageUrl", "watermark", "sources", "links"}
        )
    if isinstance(value, list):
        return sum(_visible_word_count(v) for v in value)
    return 0


def _visible_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(
            _visible_text(v)
            for key, v in value.items()
            if key not in {"designTokens", "imageUrl", "watermark", "sources", "links"}
        )
    if isinstance(value, list):
        return " ".join(_visible_text(v) for v in value)
    return ""


def _contains_placeholder(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in _PLACEHOLDER_TERMS)


def _has_image_url(props: Mapping[str, Any], compiled: Mapping[str, Any]) -> bool:
    if props.get("imageUrl") or props.get("image_url"):
        return True
    assets = compiled.get("assets")
    return isinstance(assets, list) and any(isinstance(asset, Mapping) and asset.get("url") for asset in assets)


# ── Slice 1 (Trust Honesty) ────────────────────────────────────────
# Convert a deck-level production gate into a small, frontend-safe
# export-readiness verdict. This is purely additive: callers that only
# read `production_quality_gate` keep working unchanged.
#
# Keys returned:
#   export_ready    bool   — true when the deck is safe to export by default.
#   quality_state   str    — "ready" | "ready_with_warnings" | "blocked"
#                            | "unknown" (gate has not run).
#   export_blockers list   — compact list of {slide_index, code, message}
#                            describing the blocker issues only. Capped at 12
#                            so the UI never has to render an essay.
#
# A deck is `ready` when:
#   - it ran the gate (`schema_version` present), AND
#   - it has no blocker issues (`blocked` is false), AND
#   - the deck-level score is >= 75.
# Any of those failing yields `ready_with_warnings` (gate ran but warns)
# or `blocked` (gate ran and found blocker issues).

_EXPORT_BLOCKER_LIMIT = 12


def compute_export_readiness(
    deck_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Project an export-readiness verdict from a deck production report.

    Accepts either:
      * the dict produced by ``DeckProductionReport.to_dict()`` (called from
        the live pipeline), or
      * the dict produced by ``summarize_production_quality_gate(...)``
        (called when the deck is rehydrated from Mongo).

    Returns a stable, JSON-safe dict the frontend and export router can rely on
    without re-implementing the logic.
    """
    if not isinstance(deck_report, Mapping) or not deck_report:
        return {
            "export_ready": False,
            "quality_state": "unknown",
            "export_blockers": [],
            "score": 0,
            "summary": "Production quality gate has not run.",
        }

    blocked = bool(deck_report.get("blocked"))
    try:
        score = int(deck_report.get("score") or 0)
    except (TypeError, ValueError):
        score = 0
    summary = str(deck_report.get("summary") or "")

    blockers: list[dict[str, Any]] = []

    def _add(issue: Mapping[str, Any]) -> None:
        if len(blockers) >= _EXPORT_BLOCKER_LIMIT:
            return
        if str(issue.get("severity") or "").lower() != "blocker":
            return
        blockers.append({
            "slide_index": issue.get("slide_index"),
            "code": str(issue.get("code") or ""),
            "message": str(issue.get("message") or ""),
            "target": str(issue.get("target") or ""),
            "recommendation": str(issue.get("recommendation") or ""),
        })

    for slide_report in deck_report.get("slide_reports") or []:
        if not isinstance(slide_report, Mapping):
            continue
        for issue in slide_report.get("issues") or []:
            if isinstance(issue, Mapping):
                _add(issue)
    for issue in deck_report.get("issues") or []:
        if isinstance(issue, Mapping):
            _add(issue)

    if blocked or blockers:
        quality_state = "blocked"
        export_ready = False
    elif score < 75:
        quality_state = "ready_with_warnings"
        export_ready = True
    else:
        quality_state = "ready"
        export_ready = True

    return {
        "export_ready": export_ready,
        "quality_state": quality_state,
        "export_blockers": blockers,
        "score": score,
        "summary": summary,
    }
