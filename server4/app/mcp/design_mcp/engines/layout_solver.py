"""
Layout solver — determines optimal layout for content and validates fits.
Also analyzes existing slides and suggests layout improvements.
"""

import re
from typing import Optional

import structlog

from app.mcp.design_mcp.config import LAYOUT_CONSTRAINTS, FONT_SIZE_MINIMUMS

logger = structlog.get_logger()


# Layout scoring weights per content characteristic
LAYOUT_SCORES = {
    "title-hero": {
        "has_title": 10,
        "is_opening": 20,
        "is_closing": 15,
        "has_bullets": -10,
    },
    "two-column": {"has_comparison": 15, "has_left_right": 20, "has_long_text": 10},
    "bullets": {"has_bullets": 20, "has_many_points": 15, "has_title": 5},
    "bullets-with-image": {"has_bullets": 15, "has_image": 20, "has_few_bullets": 10},
    "full-image": {"has_image": 25, "is_visual": 20, "has_minimal_text": 10},
    "chart": {"has_data": 25, "has_numbers": 20, "needs_visualization": 15},
    "comparison": {"has_comparison": 25, "has_vs": 20, "has_two_options": 15},
    "timeline": {"has_dates": 25, "has_sequence": 20, "has_milestones": 15},
    "quote": {"has_quote": 25, "has_testimonial": 20, "is_inspirational": 10},
    "team-grid": {"has_people": 25, "has_team": 20, "has_bios": 15},
    "kpi-dashboard": {"has_metrics": 25, "has_numbers": 20, "has_kpis": 15},
    "blank": {},  # Fallback
}

# Comparison keywords
_COMPARISON_KWS = [
    "vs",
    "versus",
    "compare",
    "compared to",
    "before",
    "after",
    "pros and cons",
    "advantages",
    "disadvantages",
    "better than",
]

# Timeline/date patterns
_DATE_PATTERNS = [
    r"\b(?:q[1-4]|january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\b",
    r"\b20\d{2}\b",
    r"\b(?:phase|stage|step|milestone)\s+\d+\b",
]

# Number pattern for data extraction
_NUMBER_PATTERN = re.compile(r"[\$]?[\d,]+(?:\.\d+)?[%]?")


class LayoutSolver:
    """Determines optimal layout and validates content fits."""

    def suggest_layout(self, content_analysis: dict) -> str:
        """Suggest the best layout based on content characteristics."""
        scores = {}
        for layout, weights in LAYOUT_SCORES.items():
            score = sum(
                weight
                for trait, weight in weights.items()
                if content_analysis.get(trait, False)
            )
            scores[layout] = score

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "bullets"  # Safe default
        return best

    def analyze_content(self, content: dict, purpose: str = "") -> dict:
        """Analyze content to determine characteristics for layout selection."""
        text = str(content).lower()
        purpose_lower = purpose.lower()

        return {
            "has_title": bool(content.get("title")),
            "is_opening": any(
                w in purpose_lower for w in ["intro", "opening", "title", "cover"]
            ),
            "is_closing": any(
                w in purpose_lower
                for w in ["close", "end", "thank", "conclusion", "cta"]
            ),
            "has_bullets": isinstance(content.get("bullets"), list)
            and len(content.get("bullets", [])) > 0,
            "has_many_points": len(content.get("bullets", [])) > 4,
            "has_few_bullets": 1 <= len(content.get("bullets", [])) <= 4,
            "has_comparison": any(
                w in text for w in ["vs", "versus", "compare", "before", "after"]
            ),
            "has_left_right": bool(
                content.get("left_content") or content.get("left_items")
            ),
            "has_long_text": len(content.get("body_text", "")) > 200,
            "has_image": bool(content.get("image_url") or content.get("image_prompt")),
            "is_visual": any(
                w in purpose_lower for w in ["visual", "image", "photo", "hero"]
            ),
            "has_minimal_text": len(content.get("body_text", "")) < 50
            and not content.get("bullets"),
            "has_data": bool(content.get("chart_data")),
            "has_numbers": any(c.isdigit() for c in text[:200]),
            "needs_visualization": any(
                w in text for w in ["growth", "trend", "market size", "revenue"]
            ),
            "has_dates": any(
                w in text for w in ["q1", "q2", "q3", "q4", "2024", "2025", "2026"]
            ),
            "has_sequence": any(
                w in text for w in ["step", "phase", "stage", "milestone"]
            ),
            "has_milestones": any(
                w in purpose_lower for w in ["roadmap", "timeline", "milestone"]
            ),
            "has_quote": bool(content.get("quote_text")),
            "has_testimonial": "testimonial" in purpose_lower,
            "is_inspirational": any(
                w in purpose_lower for w in ["vision", "mission", "inspire"]
            ),
            "has_people": bool(content.get("members")),
            "has_team": "team" in purpose_lower,
            "has_bios": any(m.get("bio") for m in content.get("members", [])),
            "has_metrics": bool(content.get("metrics")),
            "has_kpis": any(
                w in purpose_lower for w in ["kpi", "metric", "traction", "result"]
            ),
            "has_two_options": bool(
                content.get("left_items") and content.get("right_items")
            ),
            "has_vs": "vs" in text or "versus" in text,
        }

    def analyze_slide(self, slide_content: dict) -> list[dict]:
        """Analyze slide content and suggest layout improvements.

        Returns a list of suggestion dicts with:
        - type: "layout_suggestion"
        - severity: "warning" | "info"
        - message: human-readable explanation
        - suggested_layout: recommended layout ID
        - actionable: bool (whether data supports the suggestion)
        """
        suggestions = []
        title = slide_content.get("title", "")
        bullets = slide_content.get("bullets", [])
        current_layout = slide_content.get("layout", "bullets")
        full_text = title + " " + " ".join(str(b) for b in bullets)
        full_text_lower = full_text.lower()

        # 1. Bullet overload check
        if len(bullets) > 6:
            has_numbers = any(self._has_number(b) for b in bullets)
            suggestions.append(
                {
                    "type": "layout_suggestion",
                    "severity": "warning",
                    "message": (
                        f"{len(bullets)} bullets detected (max 6). "
                        f"Consider splitting into 2 slides or using "
                        f"{'a chart layout' if has_numbers else 'a two-column layout'}."
                    ),
                    "suggested_layout": "chart" if has_numbers else "two-column",
                    "actionable": True,
                }
            )

        # 2. Number density → chart suggestion (with parseability check)
        number_count = sum(1 for b in bullets if self._has_number(b))
        if number_count >= 3 and current_layout not in ("chart", "kpi-dashboard"):
            parsed_data = self._extract_data_points(bullets)
            if parsed_data:
                suggestions.append(
                    {
                        "type": "layout_suggestion",
                        "severity": "info",
                        "message": (
                            f"{number_count} data points detected with extractable "
                            f"key-value pairs. Consider chart layout for better visualization."
                        ),
                        "suggested_layout": "chart",
                        "actionable": True,
                        "parsed_data": parsed_data,
                    }
                )
            else:
                # Numbers present but unstructured — suggest KPI or two-column instead
                suggestions.append(
                    {
                        "type": "layout_suggestion",
                        "severity": "info",
                        "message": (
                            f"{number_count} data points detected but data is unstructured prose. "
                            f"Consider KPI dashboard or two-column layout instead of chart."
                        ),
                        "suggested_layout": "kpi-dashboard",
                        "actionable": True,
                    }
                )

        # 3. Comparison detection
        if any(kw in full_text_lower for kw in _COMPARISON_KWS):
            if current_layout not in ("comparison", "two-column"):
                suggestions.append(
                    {
                        "type": "layout_suggestion",
                        "severity": "info",
                        "message": (
                            "Comparison content detected. Consider comparison layout "
                            "for side-by-side clarity."
                        ),
                        "suggested_layout": "comparison",
                        "actionable": True,
                    }
                )

        # 4. Timeline detection
        if self._detect_timeline(full_text):
            if current_layout != "timeline":
                suggestions.append(
                    {
                        "type": "layout_suggestion",
                        "severity": "info",
                        "message": (
                            "Chronological/sequential content detected. "
                            "Consider timeline layout for better flow."
                        ),
                        "suggested_layout": "timeline",
                        "actionable": True,
                    }
                )

        # 5. Single insight → title-hero
        if len(bullets) == 1 and len(bullets[0].split()) <= 10 and not title:
            if current_layout != "title-hero":
                suggestions.append(
                    {
                        "type": "layout_suggestion",
                        "severity": "info",
                        "message": (
                            "Single key insight detected. Consider title-hero layout "
                            "for maximum impact."
                        ),
                        "suggested_layout": "title-hero",
                        "actionable": True,
                    }
                )

        # 6. Team content detection
        if self._detect_team_content(bullets, full_text_lower):
            if current_layout != "team-grid":
                suggestions.append(
                    {
                        "type": "layout_suggestion",
                        "severity": "info",
                        "message": (
                            "Team/people content detected. Consider team-grid layout."
                        ),
                        "suggested_layout": "team-grid",
                        "actionable": True,
                    }
                )

        # 7. KPI content detection
        if self._detect_kpi_content(bullets, full_text_lower):
            if current_layout not in ("kpi-dashboard", "chart"):
                suggestions.append(
                    {
                        "type": "layout_suggestion",
                        "severity": "info",
                        "message": (
                            "KPI/metrics content detected. Consider KPI dashboard layout."
                        ),
                        "suggested_layout": "kpi-dashboard",
                        "actionable": True,
                    }
                )

        return suggestions

    def _extract_data_points(self, bullets: list[str]) -> list[dict] | None:
        """Try to extract structured key-value pairs from bullet text.

        Returns list of {label, value} dicts if parseable, None if unstructured.
        Supports patterns like:
        - "Revenue: $2.3M"
        - "Growth — 34%"
        - "Users = 50,000"
        - "$180B market size"
        """
        parsed = []
        for bullet in bullets:
            # Pattern: "Label: Value" or "Label — Value" or "Label = Value"
            kv_match = re.match(
                r"([A-Za-z][A-Za-z\s]{1,30})[:\-=]\s*(.+)", bullet.strip()
            )
            if kv_match:
                parsed.append(
                    {
                        "label": kv_match.group(1).strip(),
                        "value": kv_match.group(2).strip(),
                    }
                )
                continue

            # Pattern: "Value Label" (e.g., "$180B market size")
            num_match = re.match(
                r"([\$\d,]+(?:\.\d+)?[%]?)\s+([A-Za-z\s]{2,30})", bullet.strip()
            )
            if num_match:
                parsed.append(
                    {
                        "label": num_match.group(2).strip(),
                        "value": num_match.group(1).strip(),
                    }
                )
                continue

        # Only return if we parsed at least 60% of bullets
        if len(parsed) >= max(2, len(bullets) * 0.6):
            return parsed
        return None

    def _has_number(self, text: str) -> bool:
        """Check if text contains a meaningful number (not just a year)."""
        matches = _NUMBER_PATTERN.findall(text)
        # Filter out standalone years (2024, 2025, etc.) — those are timeline markers
        non_year_numbers = [m for m in matches if not re.match(r"^20\d{2}$", m)]
        return len(non_year_numbers) > 0

    def _detect_timeline(self, text: str) -> bool:
        """Detect chronological/sequential content."""
        date_matches = 0
        for pattern in _DATE_PATTERNS:
            date_matches += len(re.findall(pattern, text, re.IGNORECASE))
        sequence_words = sum(
            1
            for w in ["step", "phase", "stage", "milestone", "then", "next", "finally"]
            if w in text.lower()
        )
        return date_matches >= 2 or sequence_words >= 2

    def _detect_team_content(self, bullets: list[str], text: str) -> bool:
        """Detect team/people content."""
        team_kws = [
            "founder",
            "ceo",
            "cto",
            "cfo",
            "coo",
            "vp",
            "director",
            "engineer",
            "designer",
            "team",
            "member",
            "head of",
        ]
        name_pattern = re.compile(r"\b[A-Z][a-z]{2,15}\s+[A-Z][a-z]{2,15}\b")
        name_matches = len(name_pattern.findall(text))
        kw_matches = sum(1 for kw in team_kws if kw in text)
        return name_matches >= 2 or kw_matches >= 2

    def _detect_kpi_content(self, bullets: list[str], text: str) -> bool:
        """Detect KPI/metrics content."""
        kpi_kws = [
            "mrr",
            "arr",
            "burn rate",
            "runway",
            "cac",
            "ltv",
            "churn",
            "retention",
            "conversion",
            "roi",
            "margin",
            "revenue",
            "growth",
            "month",
            "quarter",
            "year-over-year",
            "yoy",
        ]
        kw_count = sum(1 for kw in kpi_kws if kw in text)
        number_count = sum(1 for b in bullets if self._has_number(b))
        return kw_count >= 2 or (kw_count >= 1 and number_count >= 3)

    def get_constraints(self, layout: str) -> dict:
        """Get layout constraints for a given layout type."""
        return LAYOUT_CONSTRAINTS.get(layout, LAYOUT_CONSTRAINTS.get("blank", {}))

    def calculate_font_sizes(self, layout: str, content: dict) -> dict:
        """Calculate appropriate font sizes based on content length and layout."""
        sizes = dict(FONT_SIZE_MINIMUMS)

        # Adjust title size based on length
        title = content.get("title", "")
        if len(title) > 40:
            sizes["title"] = max(24, sizes["title"] - 4)
        elif len(title) < 15:
            sizes["title"] = min(48, sizes["title"] + 8)

        # Adjust bullet size based on count
        bullets = content.get("bullets", [])
        if len(bullets) > 6:
            sizes["bullet"] = max(12, sizes["bullet"] - 2)

        return sizes
