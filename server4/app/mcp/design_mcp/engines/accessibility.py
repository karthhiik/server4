"""
Accessibility engine — WCAG compliance checks for presentation design.
"""

from app.mcp.design_mcp.config import MIN_CONTRAST_RATIO, FONT_SIZE_MINIMUMS
from app.mcp.design_mcp.engines.theme_engine import ThemeEngine


class AccessibilityChecker:
    """Validates presentation elements against WCAG AA guidelines."""

    def __init__(self):
        self.theme_engine = ThemeEngine()

    def check_slide_accessibility(self, slide: dict, theme: dict) -> dict:
        """Run accessibility checks on a single slide."""
        issues = []
        warnings = []

        colors = theme.get("colors", {})
        bg = colors.get("background", "#ffffff")
        text_primary = colors.get("text_primary", "#000000")
        text_secondary = colors.get("text_secondary", "#666666")

        # Check text contrast
        primary_ratio = self.theme_engine._contrast_ratio(text_primary, bg)
        if primary_ratio < MIN_CONTRAST_RATIO:
            issues.append({
                "type": "contrast",
                "message": f"Primary text contrast {primary_ratio:.1f}:1 below {MIN_CONTRAST_RATIO}:1 minimum",
                "element": "text_primary",
            })

        secondary_ratio = self.theme_engine._contrast_ratio(text_secondary, bg)
        if secondary_ratio < 3.0:  # AA for large text
            issues.append({
                "type": "contrast",
                "message": f"Secondary text contrast {secondary_ratio:.1f}:1 too low",
                "element": "text_secondary",
            })

        # Check font sizes
        content = slide.get("content", {})
        title = content.get("title", "")
        if title and len(title) > 60:
            warnings.append({
                "type": "readability",
                "message": "Title exceeds 60 characters — may be hard to read on screen",
                "element": "title",
            })

        bullets = content.get("bullets", [])
        if len(bullets) > 7:
            warnings.append({
                "type": "cognitive_load",
                "message": f"{len(bullets)} bullets may overwhelm the audience (recommend ≤6)",
                "element": "bullets",
            })

        # Check for alt text on images
        if content.get("image_url") and not content.get("image_prompt") and not content.get("caption"):
            warnings.append({
                "type": "alt_text",
                "message": "Image has no description or caption for screen readers",
                "element": "image",
            })

        return {
            "accessible": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "contrast_ratios": {
                "primary_text": round(primary_ratio, 1),
                "secondary_text": round(secondary_ratio, 1),
            },
        }

    def check_presentation_accessibility(self, slides: list[dict], theme: dict) -> dict:
        """Run accessibility checks on entire presentation."""
        all_issues = []
        all_warnings = []

        for i, slide in enumerate(slides):
            result = self.check_slide_accessibility(slide, theme)
            for issue in result["issues"]:
                issue["slide_index"] = i
                all_issues.append(issue)
            for warning in result["warnings"]:
                warning["slide_index"] = i
                all_warnings.append(warning)

        return {
            "accessible": len(all_issues) == 0,
            "total_issues": len(all_issues),
            "total_warnings": len(all_warnings),
            "issues": all_issues,
            "warnings": all_warnings,
            "score": max(0, 100 - len(all_issues) * 20 - len(all_warnings) * 5),
        }

    def suggest_fixes(self, issues: list[dict], theme: dict) -> list[dict]:
        """Suggest fixes for accessibility issues."""
        fixes = []
        colors = theme.get("colors", {})
        bg = colors.get("background", "#ffffff")

        for issue in issues:
            if issue["type"] == "contrast":
                element = issue["element"]
                current_color = colors.get(element, "#000000")
                fixed_color = self.theme_engine.adjust_for_contrast(current_color, bg, MIN_CONTRAST_RATIO)
                fixes.append({
                    "element": element,
                    "current": current_color,
                    "suggested": fixed_color,
                    "reason": issue["message"],
                })

        return fixes
