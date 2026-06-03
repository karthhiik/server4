"""Headline Quality Gate — Validates headlines before slide acceptance.

CEO-identified issue: Template headlines like "Our Unique Value Proposition"
were shipping to investors. The critic gave 9.35/10 for a deck with these
headlines, proving the critic wasn't reading the content.

This module provides a HARD GATE that runs BEFORE a slide is accepted.
If the headline fails, the slide is immediately rejected and regenerated.

Usage:
    from app.services.v4.headline_quality_gate import HeadlineQualityGate

    gate = HeadlineQualityGate()
    result = gate.validate(slide, user_input_keywords, company_name, industry)

    if not result.passed:
        # Trigger regeneration with specific feedback
        regenerate_with_feedback(result.issues, result.suggestions)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.v4 import content_rules


@dataclass
class HeadlineGateResult:
    """Result of headline quality gate validation."""
    passed: bool
    headline: str
    score: float  # 0-10
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    is_template: bool = False
    is_generic: bool = False
    has_contamination: bool = False
    missing_user_input: bool = False
    must_regenerate: bool = False  # True when score < 5.0


class HeadlineQualityGate:
    """Validates headline quality before slide acceptance.

    A headline PASSES if:
      1. It is NOT a template phrase (banned pattern)
      2. It contains company name OR industry-specific term
      3. It contains at least one specific claim (number or user input keyword)
      4. It does NOT contain cross-industry contamination
      5. Score >= 5.0

    A headline FAILS and triggers regeneration if:
      - It's a template headline (score = 0)
      - It contains cross-industry contamination (score -= 5)
      - It's too generic (no company/industry term AND no numbers)
      - Score < 5.0
    """

    # Critical intents where headline quality is NON-NEGOTIABLE
    CRITICAL_INTENTS = {
        "title", "traction", "ask", "market", "competition"
    }

    # Template headlines that ALWAYS trigger regeneration
    ALWAYS_REJECT_TEMPLATES = {
        "our unique value proposition",
        "our distinctive edge",
        "how we operate",
        "empowering resilience",
        "market opportunity",
        "the problem",
        "our solution",
        "our approach",
        "early validation signals",
    }

    def validate(
        self,
        headline: str,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
        user_input_keywords: Optional[list[str]] = None,
        intent: Optional[str] = None,
    ) -> HeadlineGateResult:
        """Validate a headline for quality.

        Args:
            headline: The headline to validate
            company_name: Company name (should appear in headline)
            industry: Industry (industry terms should appear)
            user_input_keywords: Specific facts from user input
            intent: Slide intent (some intents have stricter rules)

        Returns:
            HeadlineGateResult with pass/fail status and details
        """
        issues: list[str] = []
        suggestions: list[str] = []
        score = 10.0

        if not headline or not headline.strip():
            return HeadlineGateResult(
                passed=False,
                headline=headline or "",
                score=0.0,
                issues=["headline_empty"],
                suggestions=["Write a specific thesis headline, not a category label."],
                must_regenerate=True,
            )

        headline_lower = headline.strip().lower()

        # 1. Check for template headline (ALWAYS REJECT)
        is_template = False
        for template in self.ALWAYS_REJECT_TEMPLATES:
            if template in headline_lower:
                is_template = True
                score = 0.0
                issues.append(f"template_headline: '{headline}' is a PowerPoint placeholder")
                suggestions.append(
                    f"Replace with a specific thesis. Example: '2 State-Level Pilots + 1 Patent Pending' "
                    f"instead of 'Our Unique Value Proposition'."
                )
                break

        # Also use content_rules template detector
        template_det = content_rules.detect_template_headline(headline)
        if template_det.is_template and not is_template:
            is_template = True
            score = max(0.0, score - 5.0)
            issues.append(f"template_headline:{template_det.label}")
            if template_det.fix_hint:
                suggestions.append(template_det.fix_hint)

        # 2. Check for company name or industry term
        company_present = company_name and company_name.lower() in headline_lower
        industry_terms = content_rules._INDUSTRY_VOCABULARY.get((industry or "").lower(), {}).get("expected", [])
        industry_present = any(term in headline_lower for term in industry_terms)

        is_generic = False
        if not company_present and not industry_present:
            is_generic = True
            score = max(0.0, score - 2.0)
            issues.append("headline_too_generic")
            suggestions.append(
                f"Include company name '{company_name}' or industry term "
                f"(e.g., {', '.join(industry_terms[:3]) if industry_terms else 'relevant terminology'})."
            )

        # 3. Check for specific claim (number or user input keyword)
        has_number = bool(content_rules._NUM_RE.search(headline))
        user_keywords = user_input_keywords or []
        has_user_keyword = any(kw.lower() in headline_lower for kw in user_keywords)

        if not has_number and not has_user_keyword:
            score = max(0.0, score - 2.0)
            issues.append("headline_lacks_specificity")
            suggestions.append(
                "Add a specific metric, number, or concrete claim from your input data."
            )

        # 4. Check for cross-industry contamination
        contamination = content_rules.detect_cross_industry_contamination(headline, industry)
        has_contamination = bool(contamination)
        if has_contamination:
            score = max(0.0, score - 5.0)
            issues.append(f"cross_industry_contamination:{','.join(contamination[:3])}")
            suggestions.append(
                f"Remove terminology from other industries: {', '.join(contamination[:3])}."
            )

        # 5. Check for generic fluff phrases
        generic_hits = content_rules.detect_generic_phrases(headline)
        if generic_hits:
            score = max(0.0, score - min(3.0, len(generic_hits) * 1.0))
            issues.append(f"generic_phrases:{','.join(generic_hits[:3])}")
            suggestions.append("Replace generic phrases with specific claims.")

        # 6. Intent-specific checks
        intent_lower = (intent or "").lower()
        if intent_lower in self.CRITICAL_INTENTS:
            # Critical slides (traction, ask) MUST use user input
            if intent_lower == "traction" and user_keywords:
                if not has_user_keyword:
                    score = max(0.0, score - 3.0)
                    issues.append("traction_slide_missing_user_data")
                    suggestions.append(
                        f"Traction slide MUST mention user's actual metrics. "
                        f"User provided: {', '.join(user_keywords[:5])}. "
                        f"Use at least one in the headline."
                    )

            if intent_lower == "ask" and user_keywords:
                if not has_user_keyword:
                    score = max(0.0, score - 3.0)
                    issues.append("ask_slide_missing_funding_amount")
                    suggestions.append(
                        f"Ask slide MUST mention the funding amount and use of funds. "
                        f"User provided: {', '.join(user_keywords[:5])}."
                    )

        # Determine if regeneration is required
        must_regenerate = score < 5.0 or is_template or has_contamination
        passed = score >= 5.0 and not is_template

        return HeadlineGateResult(
            passed=passed,
            headline=headline,
            score=score,
            issues=issues,
            suggestions=suggestions,
            is_template=is_template,
            is_generic=is_generic,
            has_contamination=has_contamination,
            must_regenerate=must_regenerate,
        )

    def validate_slide(
        self,
        slide: Any,  # GeneratedSlide
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
        user_input_keywords: Optional[list[str]] = None,
    ) -> HeadlineGateResult:
        """Validate a GeneratedSlide's headline.

        Convenience method that extracts relevant fields from the slide.
        """
        return self.validate(
            headline=slide.headline,
            company_name=company_name or getattr(slide, "company_name", None),
            industry=industry or getattr(slide, "industry", None),
            user_input_keywords=user_input_keywords or getattr(slide, "user_input_keywords", None),
            intent=slide.intent,
        )


def run_headline_gate(
    slides: list[Any],  # list[GeneratedSlide]
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
    user_input_keywords: Optional[list[str]] = None,
) -> tuple[list[int], list[HeadlineGateResult]]:
    """Run headline quality gate on all slides.

    Args:
        slides: List of GeneratedSlide objects
        company_name: Company name
        industry: Industry
        user_input_keywords: Specific facts from user input

    Returns:
        Tuple of (failed_indices, results_for_all_slides)
    """
    gate = HeadlineQualityGate()
    failed_indices: list[int] = []
    results: list[HeadlineGateResult] = []

    for slide in slides:
        result = gate.validate_slide(
            slide,
            company_name=company_name,
            industry=industry,
            user_input_keywords=user_input_keywords,
        )
        results.append(result)

        if result.must_regenerate:
            failed_indices.append(slide.index)

    return failed_indices, results


def build_regeneration_instruction(result: HeadlineGateResult) -> str:
    """Build a regeneration instruction for a failed headline.

    This instruction is passed to the writer for targeted regeneration.
    """
    if result.passed:
        return ""

    lines = [
        "HEADLINE QUALITY GATE FAILED — REGENERATION REQUIRED",
        f"Current headline: '{result.headline}'",
        f"Quality score: {result.score:.1f}/10",
        "",
        "Issues detected:",
    ]

    for issue in result.issues:
        lines.append(f"  - {issue}")

    lines.append("")
    lines.append("Required fixes:")
    for suggestion in result.suggestions:
        lines.append(f"  - {suggestion}")

    lines.append("")
    lines.append(
        "CRITICAL: The new headline must pass the 'could this only be about [company]?' test. "
        "Generic headlines like 'Our Unique Value Proposition' will be rejected again."
    )

    return "\n".join(lines)
