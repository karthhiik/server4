"""
Thumbnail Builder — generates small preview images of slides.
"""

import asyncio
from typing import Optional

import structlog

from app.mcp.render_mcp.builders.image_builder import ImageBuilder
from app.mcp.render_mcp.config import THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT

logger = structlog.get_logger()


class ThumbnailBuilder:
    """Generates thumbnails for slide previews."""

    def __init__(self):
        self.image_builder = ImageBuilder()

    async def generate_thumbnail(self, slide: dict, theme: dict) -> bytes:
        """Generate a small thumbnail for a single slide."""
        return await self.image_builder.render_slide_image(
            slide, theme,
            width=THUMBNAIL_WIDTH * 2,  # Render at 2x for quality
            height=THUMBNAIL_HEIGHT * 2,
        )

    async def generate_all_thumbnails(self, slides: list[dict], theme: dict) -> list[bytes]:
        """Generate thumbnails for all slides."""
        return await self.image_builder.render_all_slides(
            slides, theme,
            width=THUMBNAIL_WIDTH * 2,
            height=THUMBNAIL_HEIGHT * 2,
        )
