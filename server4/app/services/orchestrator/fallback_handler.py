"""Cross-MCP fallback logic and error recovery."""

import structlog

logger = structlog.get_logger()


class FallbackHandler:
    """
    Handles graceful degradation when MCPs or their dependencies fail.

    Rules:
    1. Never return nothing — always give the user something.
    2. Degrade quality, not availability.
    3. Log every fallback for observability.
    """

    @staticmethod
    async def handle_research_failure(topic: str, error: str) -> str:
        """If research fails, return a basic context from LLM knowledge."""
        logger.warning("research_fallback", topic=topic, error=error)
        return (
            f"Research data unavailable. Using general knowledge about: {topic}. "
            f"Note: Statistics may not be current. Error: {error}"
        )

    @staticmethod
    async def handle_outline_failure(topic: str, slide_count: int, error: str) -> list[dict]:
        """If outline generation fails, return a generic outline structure."""
        logger.warning("outline_fallback", topic=topic, error=error)
        return [
            {"title": topic, "purpose": "Introduction", "suggested_layout": "title-hero"},
            {"title": "Overview", "purpose": "Topic overview", "suggested_layout": "bullets"},
            {"title": "Key Points", "purpose": "Main arguments", "suggested_layout": "two-column"},
            {"title": "Details", "purpose": "Supporting evidence", "suggested_layout": "bullets-with-image"},
            {"title": "Summary", "purpose": "Conclusion", "suggested_layout": "title-hero"},
        ][:slide_count]

    @staticmethod
    async def handle_content_failure(slide_title: str, layout: str, error: str) -> dict:
        """If content generation fails for a slide, return placeholder content."""
        logger.warning("content_fallback", title=slide_title, error=error)
        return {
            "layout": layout,
            "content": {
                "title": slide_title,
                "bullets": [
                    "Content generation temporarily unavailable.",
                    "Please edit this slide manually.",
                    "You can use the AI rewrite feature to regenerate.",
                ],
            },
        }

    @staticmethod
    async def handle_design_failure(error: str) -> dict:
        """If design fails, return default corporate-blue theme."""
        logger.warning("design_fallback", error=error)
        return {
            "primary": "#2563EB",
            "secondary": "#1E40AF",
            "accent": "#3B82F6",
            "background": "#FFFFFF",
            "text": "#0F172A",
        }
