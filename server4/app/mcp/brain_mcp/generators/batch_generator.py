"""
Batch slide generator — generates multiple slides in parallel with concurrency control.

Updated 2026-05-08 (Premium Mode):
- Added council_mode parameter for multi-model LLM council voting
- Added council_models parameter for custom model selection
"""

import asyncio
from typing import Optional, List

import structlog

from app.mcp.brain_mcp.generators.slide_generator import SlideGenerator
from app.mcp.brain_mcp.config import MAX_PARALLEL_SLIDES
from app.models.content import PresentationOutline
from app.models.slide import SlideContent

logger = structlog.get_logger()


class BatchGenerator:
    """Generates content for all slides in a presentation with parallelism."""

    def __init__(self):
        self.slide_gen = SlideGenerator()

    async def generate_all_slides(
        self,
        outline: PresentationOutline,
        research_context: str = "",
        writing_style: str = "yc_pitch",
        presentation_purpose: str = "pitch",
        presentation_id: Optional[str] = None,
        progress_callback=None,
        council_mode: bool = False,
        council_models: Optional[List[str]] = None,
    ) -> list[SlideContent]:
        """Generate content for all slides with bounded parallelism."""
        semaphore = asyncio.Semaphore(MAX_PARALLEL_SLIDES)
        results: list[Optional[SlideContent]] = [None] * len(outline.slides)

        # Build presentation context from outline
        pres_context = "\n".join(
            f"Slide {i+1}: {s.title} ({s.suggested_layout})"
            for i, s in enumerate(outline.slides)
        )

        async def _generate_one(index: int):
            slide_def = outline.slides[index]
            async with semaphore:
                try:
                    content = await self.slide_gen.generate_slide_content(
                        layout=slide_def.suggested_layout,
                        title=slide_def.title,
                        purpose=slide_def.purpose,
                        content_hints=slide_def.content_hints,
                        research_context=research_context if slide_def.needs_research else "",
                        presentation_context=pres_context,
                        writing_style=writing_style,
                        presentation_purpose=presentation_purpose,
                        presentation_id=presentation_id,
                        council_mode=council_mode,
                        council_models=council_models,
                    )
                    results[index] = content
                    logger.info(
                        "slide_generated",
                        index=index,
                        title=slide_def.title[:30],
                        council_mode=council_mode,
                    )

                    if progress_callback:
                        await progress_callback(index, len(outline.slides))

                except Exception as e:
                    logger.error("slide_generation_failed", index=index, error=str(e))
                    # Fallback content
                    results[index] = SlideContent(
                        title=slide_def.title,
                        body_text=f"Content for: {slide_def.purpose}",
                        bullets=[slide_def.content_hints] if slide_def.content_hints else None,
                    )

        tasks = [_generate_one(i) for i in range(len(outline.slides))]
        await asyncio.gather(*tasks)

        return [r for r in results if r is not None]
