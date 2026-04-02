"""
Image Builder — renders slides as PNG images using Playwright.
"""

import asyncio
from typing import Optional

import structlog

from app.mcp.render_mcp.builders.html_builder import HtmlBuilder
from app.mcp.render_mcp.config import SLIDE_RENDER_WIDTH, SLIDE_RENDER_HEIGHT

logger = structlog.get_logger()


class ImageBuilder:
    """Renders individual slides or full presentations as PNG images."""

    def __init__(self):
        self.html_builder = HtmlBuilder()

    async def render_slide_image(
        self,
        slide: dict,
        theme: dict,
        width: int = SLIDE_RENDER_WIDTH,
        height: int = SLIDE_RENDER_HEIGHT,
    ) -> bytes:
        """Render a single slide as a PNG image."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Install with: pip install playwright && playwright install chromium")

        html_content = self.html_builder.build([slide], theme)

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": width, "height": height})
            await page.set_content(html_content)
            await page.wait_for_load_state("networkidle")

            screenshot = await page.screenshot(type="png", full_page=False)
            await browser.close()

        logger.info("slide_image_rendered", size_kb=len(screenshot) // 1024)
        return screenshot

    async def render_all_slides(
        self,
        slides: list[dict],
        theme: dict,
        width: int = SLIDE_RENDER_WIDTH,
        height: int = SLIDE_RENDER_HEIGHT,
    ) -> list[bytes]:
        """Render all slides as PNG images (sequentially to avoid memory issues)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed")

        images = []

        async with async_playwright() as p:
            browser = await p.chromium.launch()

            for i, slide in enumerate(slides):
                html_content = self.html_builder.build([slide], theme)
                page = await browser.new_page(viewport={"width": width, "height": height})
                await page.set_content(html_content)
                await page.wait_for_load_state("networkidle")

                screenshot = await page.screenshot(type="png", full_page=False)
                images.append(screenshot)
                await page.close()

                logger.debug("slide_rendered", index=i, size_kb=len(screenshot) // 1024)

            await browser.close()

        logger.info("all_slides_rendered", count=len(images))
        return images
