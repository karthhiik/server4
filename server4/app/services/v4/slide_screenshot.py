"""
V4 slide-screenshot service.

Renders each slide of a project against the live frontend's presentation
view in headless Chromium and returns a list of high-resolution PNG
bytes (one per slide) plus the deck title. The screenshots feed every
press-stage export format (PDF, PPTX, DOCX) so what the user downloads
matches exactly what they review in /studio.

Public API::

    pages = await capture_deck_screenshots(
        project_id=...,
        slide_count=8,
        frontend_origin="http://localhost:8080",
        viewport=(1920, 1080),
    )
    # pages: list[bytes]   one PNG per slide, in order

Implementation notes
~~~~~~~~~~~~~~~~~~~~

* Playwright is invoked on a dedicated worker thread that owns its own
  ``ProactorEventLoop`` (Windows-required for chromium spawn). The host
  event loop is unaffected.
* Each slide is rendered at full HD (1920x1080) by default. Higher
  viewport settings are respected so callers can request retina captures.
* The frontend's ``/studio?presentation=1&slide=N&exporting=1`` route is
  used. ``exporting=1`` causes the frontend to skip motion / fullscreen
  prompts so the screenshot is deterministic.
* Network errors / timeouts fall back to a clean placeholder PNG so the
  export never fails outright. The caller can decide whether to surface
  the partial result.
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import time
from typing import Optional, Sequence

import structlog

logger = structlog.get_logger(__name__)


_DEFAULT_FRONTEND = os.environ.get("FRONTEND_ORIGIN", "http://localhost:8080")


def _placeholder_png(message: str, width: int, height: int) -> bytes:
    """Return a minimal PNG saying ``message`` so the export never fails
    silently. Uses Pillow which is already a transitive dependency of
    python-pptx via Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:  # noqa: BLE001
        # 1x1 transparent PNG fallback
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
            b"\x89\x00\x00\x00\rIDATx\x9cc\xfa\xcf\x00\x00\x00\x02\x00\x01"
            b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    img = Image.new("RGB", (width, height), color="#0b0f1a")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = None
    draw.text(
        (width // 2 - 200, height // 2 - 12),
        message[:120],
        fill="#e2e8f0",
        font=font,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def capture_deck_screenshots(
    *,
    project_id: str,
    slide_count: int,
    frontend_origin: Optional[str] = None,
    viewport: tuple[int, int] = (1920, 1080),
    auth_token: Optional[str] = None,
    per_slide_timeout_s: float = 15.0,
) -> list[bytes]:
    """Async-friendly entry. Always offloads chromium to a worker thread."""
    if slide_count <= 0:
        return []

    origin = (frontend_origin or _DEFAULT_FRONTEND).rstrip("/")
    args = (project_id, slide_count, origin, viewport, auth_token, per_slide_timeout_s)
    pages = await asyncio.to_thread(_capture_isolated, *args)
    return pages


def _capture_isolated(
    project_id: str,
    slide_count: int,
    origin: str,
    viewport: tuple[int, int],
    auth_token: Optional[str],
    per_slide_timeout_s: float,
) -> list[bytes]:
    """Worker-thread Playwright runner with a dedicated event loop."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright_not_available_for_screenshot")
        return [
            _placeholder_png(
                "Screenshot unavailable (Playwright not installed)",
                viewport[0], viewport[1],
            )
            for _ in range(slide_count)
        ]

    async def _drive() -> list[bytes]:
        results: list[bytes] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                context = await browser.new_context(
                    viewport={"width": viewport[0], "height": viewport[1]},
                    device_scale_factor=2,  # retina-quality screenshots
                )
                if auth_token:
                    await context.add_cookies([{
                        "name": "barise_auth",
                        "value": auth_token,
                        "domain": origin.replace("https://", "").replace("http://", "").split(":")[0],
                        "path": "/",
                    }])
                page = await context.new_page()
                # Auth handoff: when the export route minted a capture
                # token for the requesting user, propagate it to the
                # studio frontend so the slides API call inside the
                # browser sees the correct identity. Without this the
                # studio fell back to `dev-test-user`, which 404s on
                # any project owned by a real user and produced
                # identical "no project loaded" PNGs for every page.
                token_qs = f"&capture_token={auth_token}" if auth_token else ""
                for index in range(slide_count):
                    target = (
                        f"{origin}/studio?project_id={project_id}"
                        f"&presentation=1&slide={index}&exporting=1{token_qs}"
                    )
                    try:
                        await page.goto(target, wait_until="domcontentloaded", timeout=int(per_slide_timeout_s * 1000))
                        # Wait for the slide canvas to render. The studio
                        # page sets data-slide-ready=true once hydration
                        # completes; fall back to a hard timeout so a
                        # slow slide never blocks the entire export.
                        try:
                            await page.wait_for_selector(
                                "[data-slide-ready='true'], .barise-slide-motion",
                                timeout=int(per_slide_timeout_s * 1000),
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        # Brief pause for any final layout settle.
                        await page.wait_for_timeout(400)
                        png = await page.screenshot(
                            type="png",
                            full_page=False,
                            omit_background=False,
                        )
                        results.append(png)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "slide_screenshot_failed",
                            project_id=project_id,
                            index=index,
                            error=str(exc)[:200],
                        )
                        results.append(_placeholder_png(
                            f"Slide {index + 1} render failed",
                            viewport[0], viewport[1],
                        ))
            finally:
                await browser.close()
        return results

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_drive())
    finally:
        try:
            loop.close()
        except Exception:  # noqa: BLE001
            pass
