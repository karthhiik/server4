"""
Visual Regression Engine — Phase 11.

Implements Golden-Master based visual regression testing using
Structural Similarity Index (SSIM). The SSIM algorithm measures
perceptual similarity between two images across three dimensions:
luminance, contrast, and structural information.

Core capabilities:
- Pure-Python SSIM computation (no external image lib dependency)
- Golden Master storage, versioning, and comparison
- Diff-map generation identifying changed regions
- Threshold-based pass/fail determination
- Batch regression across all slides in a presentation
- Screenshot abstraction for headless capture (Playwright integration point)

SSIM Formula:
    SSIM(x,y) = (2*μx*μy + C1)(2*σxy + C2) / ((μx² + μy² + C1)(σx² + σy² + C2))

Where:
    μx, μy = pixel sample means
    σx², σy² = sample variances
    σxy = sample covariance
    C1 = (K1*L)², C2 = (K2*L)²  (stabilization constants)
    L = dynamic range (255 for 8-bit), K1 = 0.01, K2 = 0.03
"""

from __future__ import annotations

import hashlib
import math
import struct
import time
import uuid
from typing import Any, Optional

import structlog

from app.services.slides_new.quality.models import (
    DiffMapEntry,
    DiffRegion,
    GoldenMaster,
    PixelStats,
    RegressionStatus,
    SSIMResult,
    VisualRegressionResult,
)

logger = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════
# SSIM COMPUTATION ENGINE (Pure Python, production-grade)
# ═══════════════════════════════════════════════════════════════════


class SSIMEngine:
    """
    Structural Similarity Index computation engine.

    Implements the Wang et al. (2004) SSIM algorithm with windowed
    computation. Works on raw grayscale pixel arrays for portability.

    Default parameters:
        window_size = 11 (standard Gaussian window)
        K1 = 0.01
        K2 = 0.03
        L = 255 (8-bit dynamic range)
    """

    def __init__(
        self,
        window_size: int = 11,
        k1: float = 0.01,
        k2: float = 0.03,
        dynamic_range: int = 255,
    ):
        self.window_size = window_size
        self.k1 = k1
        self.k2 = k2
        self.dynamic_range = dynamic_range

        # Pre-compute stabilization constants
        self.c1 = (k1 * dynamic_range) ** 2
        self.c2 = (k2 * dynamic_range) ** 2
        self.c3 = self.c2 / 2.0

    def compute(
        self,
        image_a: list[int],
        image_b: list[int],
        width: int,
        height: int,
    ) -> SSIMResult:
        """
        Compute SSIM between two grayscale images.

        Args:
            image_a: Flat array of grayscale pixel values (0-255), length = width*height
            image_b: Flat array of grayscale pixel values (0-255), length = width*height
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            SSIMResult with overall score and component breakdowns
        """
        start = time.time()

        if len(image_a) != width * height or len(image_b) != width * height:
            return SSIMResult(
                score=0.0,
                computation_time_ms=(time.time() - start) * 1000,
            )

        if len(image_a) == 0:
            return SSIMResult(
                score=1.0,
                luminance=1.0,
                contrast=1.0,
                structure=1.0,
                computation_time_ms=(time.time() - start) * 1000,
            )

        # Windowed SSIM: slide window across image, average results
        half_w = self.window_size // 2
        ssim_values = []
        luminance_values = []
        contrast_values = []
        structure_values = []

        # Step size for performance (stride 1 = exact, higher = faster approx)
        step = max(1, min(4, min(width, height) // 32))

        y = half_w
        while y < height - half_w:
            x = half_w
            while x < width - half_w:
                # Extract window pixels
                win_a = []
                win_b = []
                for wy in range(y - half_w, y + half_w + 1):
                    for wx in range(x - half_w, x + half_w + 1):
                        idx = wy * width + wx
                        win_a.append(image_a[idx])
                        win_b.append(image_b[idx])

                l, c, s, ssim = self._window_ssim(win_a, win_b)
                ssim_values.append(ssim)
                luminance_values.append(l)
                contrast_values.append(c)
                structure_values.append(s)

                x += step
            y += step

        if not ssim_values:
            # Image smaller than window — compute global SSIM
            l, c, s, ssim = self._window_ssim(image_a, image_b)
            ssim_values = [ssim]
            luminance_values = [l]
            contrast_values = [c]
            structure_values = [s]

        # Mean SSIM across all windows
        mean_ssim = sum(ssim_values) / len(ssim_values)
        mean_l = sum(luminance_values) / len(luminance_values)
        mean_c = sum(contrast_values) / len(contrast_values)
        mean_s = sum(structure_values) / len(structure_values)

        elapsed = (time.time() - start) * 1000

        return SSIMResult(
            score=mean_ssim,
            luminance=mean_l,
            contrast=mean_c,
            structure=mean_s,
            window_size=self.window_size,
            k1=self.k1,
            k2=self.k2,
            dynamic_range=self.dynamic_range,
            computation_time_ms=elapsed,
        )

    def _window_ssim(
        self, win_a: list[int], win_b: list[int]
    ) -> tuple[float, float, float, float]:
        """
        Compute SSIM components for a single window.

        Returns: (luminance, contrast, structure, ssim)
        """
        n = len(win_a)
        if n == 0:
            return 1.0, 1.0, 1.0, 1.0

        # Mean
        mu_a = sum(win_a) / n
        mu_b = sum(win_b) / n

        # Variance and covariance (Bessel-corrected)
        denom = max(n - 1, 1)
        sigma_a_sq = sum((p - mu_a) ** 2 for p in win_a) / denom
        sigma_b_sq = sum((p - mu_b) ** 2 for p in win_b) / denom
        sigma_ab = sum(
            (a - mu_a) * (b - mu_b) for a, b in zip(win_a, win_b)
        ) / denom

        sigma_a = math.sqrt(max(sigma_a_sq, 0.0))
        sigma_b = math.sqrt(max(sigma_b_sq, 0.0))

        # Luminance comparison
        luminance = (2 * mu_a * mu_b + self.c1) / (mu_a ** 2 + mu_b ** 2 + self.c1)

        # Contrast comparison
        contrast = (2 * sigma_a * sigma_b + self.c2) / (
            sigma_a_sq + sigma_b_sq + self.c2
        )

        # Structure comparison
        denom_s = sigma_a * sigma_b + self.c3
        structure = (sigma_ab + self.c3) / denom_s if denom_s > 0 else 1.0

        # Combined SSIM (α=β=γ=1 simplification)
        ssim = (2 * mu_a * mu_b + self.c1) * (2 * sigma_ab + self.c2) / (
            (mu_a ** 2 + mu_b ** 2 + self.c1) * (sigma_a_sq + sigma_b_sq + self.c2)
        )

        return luminance, contrast, structure, ssim

    @staticmethod
    def rgb_to_grayscale(r: int, g: int, b: int) -> int:
        """Convert RGB to grayscale using ITU-R BT.601 luma."""
        return int(0.299 * r + 0.587 * g + 0.114 * b)

    @staticmethod
    def pixels_to_grayscale(
        rgb_data: list[tuple[int, int, int]],
    ) -> list[int]:
        """Convert list of (R, G, B) tuples to grayscale values."""
        return [
            int(0.299 * r + 0.587 * g + 0.114 * b)
            for r, g, b in rgb_data
        ]

    @staticmethod
    def flat_rgb_to_grayscale(flat_rgb: list[int]) -> list[int]:
        """Convert flat [R,G,B,R,G,B,...] array to grayscale."""
        gray = []
        for i in range(0, len(flat_rgb) - 2, 3):
            gray.append(
                int(0.299 * flat_rgb[i] + 0.587 * flat_rgb[i + 1] + 0.114 * flat_rgb[i + 2])
            )
        return gray


# ═══════════════════════════════════════════════════════════════════
# DIFF MAP GENERATOR
# ═══════════════════════════════════════════════════════════════════


class DiffMapGenerator:
    """
    Generate visual diff maps between two images.

    Divides images into grid cells and classifies changes
    by type (layout shift, color change, structural, etc.).
    """

    def __init__(self, cell_size: int = 32, diff_threshold: float = 0.15):
        self.cell_size = cell_size
        self.diff_threshold = diff_threshold

    def generate(
        self,
        image_a: list[int],
        image_b: list[int],
        width: int,
        height: int,
    ) -> list[DiffMapEntry]:
        """
        Generate diff map between two grayscale images.

        Returns list of DiffMapEntry for regions that differ significantly.
        """
        if len(image_a) != len(image_b):
            return [DiffMapEntry(
                region=DiffRegion.STRUCTURAL,
                severity=1.0,
                description="Image dimensions mismatch",
            )]

        diffs: list[DiffMapEntry] = []
        cols = max(1, width // self.cell_size)
        rows = max(1, height // self.cell_size)

        for row in range(rows):
            for col in range(cols):
                x0 = col * self.cell_size
                y0 = row * self.cell_size
                x1 = min(x0 + self.cell_size, width)
                y1 = min(y0 + self.cell_size, height)

                # Extract cell pixels
                cell_a = []
                cell_b = []
                for y in range(y0, y1):
                    for x in range(x0, x1):
                        idx = y * width + x
                        if idx < len(image_a):
                            cell_a.append(image_a[idx])
                            cell_b.append(image_b[idx])

                if not cell_a:
                    continue

                # Compute cell-level statistics
                mean_a = sum(cell_a) / len(cell_a)
                mean_b = sum(cell_b) / len(cell_b)
                pixel_diffs = [abs(a - b) for a, b in zip(cell_a, cell_b)]
                mean_diff = sum(pixel_diffs) / len(pixel_diffs)

                # Normalized severity (0-1)
                severity = mean_diff / 255.0

                if severity < self.diff_threshold:
                    continue

                # Classify the type of change
                region = self._classify_change(
                    cell_a, cell_b, mean_a, mean_b, severity
                )

                diffs.append(DiffMapEntry(
                    region=region,
                    x=x0, y=y0,
                    width=x1 - x0, height=y1 - y0,
                    severity=severity,
                    description=self._describe_change(region, severity),
                ))

        return diffs

    def compute_pixel_diff_percentage(
        self,
        image_a: list[int],
        image_b: list[int],
        threshold: int = 10,
    ) -> float:
        """Compute % of pixels that differ beyond threshold."""
        if not image_a or not image_b or len(image_a) != len(image_b):
            return 100.0
        different = sum(1 for a, b in zip(image_a, image_b) if abs(a - b) > threshold)
        return (different / len(image_a)) * 100.0

    def _classify_change(
        self,
        cell_a: list[int],
        cell_b: list[int],
        mean_a: float,
        mean_b: float,
        severity: float,
    ) -> DiffRegion:
        """Classify the type of visual change in a cell."""
        # Large mean shift → color change
        mean_shift = abs(mean_a - mean_b) / 255.0
        if mean_shift > 0.3:
            return DiffRegion.COLOR_CHANGE

        # Variance change → structural change
        var_a = sum((p - mean_a) ** 2 for p in cell_a) / max(len(cell_a), 1)
        var_b = sum((p - mean_b) ** 2 for p in cell_b) / max(len(cell_b), 1)
        var_ratio = abs(var_a - var_b) / max(var_a, var_b, 1.0)

        if var_ratio > 0.5:
            return DiffRegion.STRUCTURAL

        # Check if one cell is near-uniform (missing element)
        if var_a < 100 and var_b > 1000:
            return DiffRegion.ELEMENT_ADDED
        if var_a > 1000 and var_b < 100:
            return DiffRegion.ELEMENT_MISSING

        # Default: layout shift
        if severity > 0.4:
            return DiffRegion.LAYOUT_SHIFT

        return DiffRegion.TEXT_CHANGE

    @staticmethod
    def _describe_change(region: DiffRegion, severity: float) -> str:
        """Human-readable description of detected change."""
        sev = "significant" if severity > 0.5 else "moderate" if severity > 0.25 else "subtle"
        descriptions = {
            DiffRegion.COLOR_CHANGE: f"{sev.capitalize()} color shift detected",
            DiffRegion.LAYOUT_SHIFT: f"{sev.capitalize()} layout displacement",
            DiffRegion.TEXT_CHANGE: f"{sev.capitalize()} text content change",
            DiffRegion.ELEMENT_MISSING: "Element appears to be removed",
            DiffRegion.ELEMENT_ADDED: "New element detected in region",
            DiffRegion.STRUCTURAL: f"{sev.capitalize()} structural change",
        }
        return descriptions.get(region, f"{sev.capitalize()} visual difference")


# ═══════════════════════════════════════════════════════════════════
# GOLDEN MASTER STORE
# ═══════════════════════════════════════════════════════════════════


class GoldenMasterStore:
    """
    In-memory store for golden master reference images.

    Production-ready: supports versioning, per-slide + per-renderer
    masters, and batch operations.
    """

    def __init__(self, max_masters: int = 500):
        self.max_masters = max_masters
        self._masters: dict[str, GoldenMaster] = {}     # key = composite key
        self._by_presentation: dict[str, list[str]] = {}  # pres_id → [keys]

    @staticmethod
    def _make_key(presentation_id: str, slide_id: str, renderer: str) -> str:
        """Create composite key for a golden master."""
        return f"{presentation_id}:{slide_id}:{renderer}"

    def store(self, master: GoldenMaster) -> str:
        """Store a golden master, return its composite key."""
        key = self._make_key(
            master.presentation_id, master.slide_id, master.renderer
        )

        # Evict oldest if at capacity
        if len(self._masters) >= self.max_masters and key not in self._masters:
            oldest_key = min(
                self._masters, key=lambda k: self._masters[k].created_at
            )
            self._remove(oldest_key)

        self._masters[key] = master

        if master.presentation_id not in self._by_presentation:
            self._by_presentation[master.presentation_id] = []
        if key not in self._by_presentation[master.presentation_id]:
            self._by_presentation[master.presentation_id].append(key)

        return key

    def get(
        self,
        presentation_id: str,
        slide_id: str,
        renderer: str,
    ) -> Optional[GoldenMaster]:
        """Retrieve a golden master by composite key."""
        key = self._make_key(presentation_id, slide_id, renderer)
        return self._masters.get(key)

    def exists(
        self,
        presentation_id: str,
        slide_id: str,
        renderer: str,
    ) -> bool:
        key = self._make_key(presentation_id, slide_id, renderer)
        return key in self._masters

    def get_for_presentation(
        self, presentation_id: str
    ) -> list[GoldenMaster]:
        """Get all golden masters for a presentation."""
        keys = self._by_presentation.get(presentation_id, [])
        return [self._masters[k] for k in keys if k in self._masters]

    def remove(
        self,
        presentation_id: str,
        slide_id: str,
        renderer: str,
    ) -> bool:
        key = self._make_key(presentation_id, slide_id, renderer)
        return self._remove(key)

    def _remove(self, key: str) -> bool:
        if key not in self._masters:
            return False
        master = self._masters.pop(key)
        pres_keys = self._by_presentation.get(master.presentation_id, [])
        if key in pres_keys:
            pres_keys.remove(key)
        return True

    def clear_presentation(self, presentation_id: str) -> int:
        """Remove all masters for a presentation."""
        keys = self._by_presentation.pop(presentation_id, [])
        removed = 0
        for key in keys:
            if key in self._masters:
                del self._masters[key]
                removed += 1
        return removed

    @property
    def total_masters(self) -> int:
        return len(self._masters)

    @property
    def total_presentations(self) -> int:
        return len(self._by_presentation)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_masters": self.total_masters,
            "total_presentations": self.total_presentations,
            "max_masters": self.max_masters,
            "memory_usage_bytes": sum(
                len(m.pixel_data) for m in self._masters.values()
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# VISUAL REGRESSION SERVICE
# ═══════════════════════════════════════════════════════════════════


class VisualRegressionService:
    """
    Complete visual regression testing service.

    Integrates SSIM engine, diff map generator, and golden master
    store to provide end-to-end regression testing for slide renders.

    Flow:
    1. Capture/receive current slide render as pixel data
    2. Look up golden master for (presentation, slide, renderer)
    3. If no master exists → store as new baseline
    4. If master exists → compute SSIM, generate diff map
    5. Return pass/fail based on threshold
    """

    DEFAULT_THRESHOLD = 0.85

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        window_size: int = 11,
        max_masters: int = 500,
    ):
        self.threshold = threshold
        self.ssim_engine = SSIMEngine(window_size=window_size)
        self.diff_generator = DiffMapGenerator()
        self.master_store = GoldenMasterStore(max_masters=max_masters)
        self._comparison_count = 0
        self._pass_count = 0
        self._fail_count = 0
        self._new_baseline_count = 0

    def compare_slide(
        self,
        presentation_id: str,
        slide_id: str,
        renderer: str,
        current_pixels: list[int],
        width: int,
        height: int,
        theme_id: str = "",
    ) -> VisualRegressionResult:
        """
        Compare a slide render against its golden master.

        If no golden master exists, the current render becomes
        the new baseline (NEW_BASELINE status).

        Args:
            presentation_id: Deck identifier
            slide_id: Slide identifier
            renderer: Renderer type (reveal.js, react, html, pptx)
            current_pixels: Grayscale pixel array of current render
            width: Render width
            height: Render height
            theme_id: Theme identifier for the render

        Returns:
            VisualRegressionResult with SSIM score and diff details
        """
        self._comparison_count += 1

        # Auto-detect RGB data and convert to grayscale
        expected_pixels = width * height
        if len(current_pixels) == expected_pixels * 3:
            current_pixels = self.ssim_engine.flat_rgb_to_grayscale(current_pixels)

        # Look up golden master
        master = self.master_store.get(presentation_id, slide_id, renderer)

        if master is None:
            # No baseline — store as new golden master
            new_master = GoldenMaster(
                slide_id=slide_id,
                presentation_id=presentation_id,
                renderer=renderer,
                resolution=(width, height),
                pixel_data=bytes(current_pixels),
                theme_id=theme_id,
            )
            self.master_store.store(new_master)
            self._new_baseline_count += 1

            logger.info(
                "golden_master_created",
                presentation_id=presentation_id,
                slide_id=slide_id,
                renderer=renderer,
            )

            return VisualRegressionResult(
                slide_id=slide_id,
                status=RegressionStatus.NEW_BASELINE,
                golden_master_id=new_master.id,
                threshold=self.threshold,
            )

        # Compare against golden master
        try:
            master_pixels = list(master.pixel_data)

            # Auto-detect RGB data in stored master and convert
            master_w, master_h = master.resolution
            expected_master_pixels = master_w * master_h
            if len(master_pixels) == expected_master_pixels * 3:
                master_pixels = self.ssim_engine.flat_rgb_to_grayscale(master_pixels)

            # Handle resolution mismatch
            master_w, master_h = master.resolution
            if master_w != width or master_h != height:
                return VisualRegressionResult(
                    slide_id=slide_id,
                    status=RegressionStatus.FAIL,
                    golden_master_id=master.id,
                    threshold=self.threshold,
                    error=f"Resolution mismatch: master={master_w}x{master_h}, current={width}x{height}",
                )

            # Compute SSIM
            ssim_result = self.ssim_engine.compute(
                master_pixels, current_pixels, width, height
            )

            # Generate diff map
            diff_regions = self.diff_generator.generate(
                master_pixels, current_pixels, width, height
            )

            # Pixel diff percentage
            pixel_diff = self.diff_generator.compute_pixel_diff_percentage(
                master_pixels, current_pixels
            )

            # Determine pass/fail
            passed = ssim_result.score >= self.threshold
            status = RegressionStatus.PASS if passed else RegressionStatus.FAIL

            if passed:
                self._pass_count += 1
            else:
                self._fail_count += 1
                logger.warning(
                    "visual_regression_failed",
                    slide_id=slide_id,
                    ssim=round(ssim_result.score, 4),
                    threshold=self.threshold,
                    diff_regions=len(diff_regions),
                )

            return VisualRegressionResult(
                slide_id=slide_id,
                status=status,
                ssim=ssim_result,
                diff_regions=diff_regions,
                golden_master_id=master.id,
                threshold=self.threshold,
                pixel_diff_percentage=pixel_diff,
            )

        except Exception as e:
            self._fail_count += 1
            logger.error("visual_regression_error", error=str(e))
            return VisualRegressionResult(
                slide_id=slide_id,
                status=RegressionStatus.ERROR,
                golden_master_id=master.id,
                threshold=self.threshold,
                error=str(e),
            )

    def update_baseline(
        self,
        presentation_id: str,
        slide_id: str,
        renderer: str,
        new_pixels: list[int],
        width: int,
        height: int,
        theme_id: str = "",
    ) -> GoldenMaster:
        """Update (or create) a golden master baseline."""
        # Auto-detect RGB and convert to grayscale
        expected_pixels = width * height
        if len(new_pixels) == expected_pixels * 3:
            new_pixels = self.ssim_engine.flat_rgb_to_grayscale(new_pixels)

        new_master = GoldenMaster(
            slide_id=slide_id,
            presentation_id=presentation_id,
            renderer=renderer,
            resolution=(width, height),
            pixel_data=bytes(new_pixels),
            theme_id=theme_id,
        )
        self.master_store.store(new_master)
        logger.info(
            "golden_master_updated",
            presentation_id=presentation_id,
            slide_id=slide_id,
        )
        return new_master

    def batch_compare(
        self,
        presentation_id: str,
        slides: list[dict[str, Any]],
        renderer: str,
    ) -> list[VisualRegressionResult]:
        """
        Compare all slides in a presentation against golden masters.

        Each slide dict must contain:
            slide_id, pixels (list[int]), width, height
        """
        results = []
        for slide_data in slides:
            result = self.compare_slide(
                presentation_id=presentation_id,
                slide_id=slide_data["slide_id"],
                renderer=renderer,
                current_pixels=slide_data["pixels"],
                width=slide_data["width"],
                height=slide_data["height"],
                theme_id=slide_data.get("theme_id", ""),
            )
            results.append(result)
        return results

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_comparisons": self._comparison_count,
            "pass_count": self._pass_count,
            "fail_count": self._fail_count,
            "new_baseline_count": self._new_baseline_count,
            "pass_rate": (
                round(self._pass_count / max(self._comparison_count, 1) * 100, 1)
            ),
            "threshold": self.threshold,
            "master_store": self.master_store.get_stats(),
        }


# ═══════════════════════════════════════════════════════════════════
# SCREENSHOT CAPTURE ABSTRACTION
# ═══════════════════════════════════════════════════════════════════


class ScreenshotCapture:
    """
    Abstraction for headless screenshot capture.

    In production, this wraps Playwright for browser-based rendering.
    For testing and standalone use, provides in-memory simulation.

    Screenshot pipeline:
    1. Render HTML to headless browser (Playwright)
    2. Capture viewport screenshot as PNG
    3. Convert to grayscale pixel array
    4. Return for SSIM comparison
    """

    def __init__(self, viewport_width: int = 1920, viewport_height: int = 1080):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._playwright_available = False
        self._capture_count = 0

        # Check Playwright availability
        try:
            import playwright  # noqa: F401
            self._playwright_available = True
        except ImportError:
            self._playwright_available = False

    @property
    def playwright_available(self) -> bool:
        return self._playwright_available

    async def capture_html(
        self,
        html_content: str,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Capture a screenshot of rendered HTML content.

        Uses Playwright if available, returns metadata only otherwise.
        """
        vw = viewport_width or self.viewport_width
        vh = viewport_height or self.viewport_height
        self._capture_count += 1

        if self._playwright_available:
            return await self._playwright_capture(html_content, vw, vh)
        else:
            return self._simulate_capture(html_content, vw, vh)

    async def _playwright_capture(
        self, html: str, width: int, height: int
    ) -> dict[str, Any]:
        """Capture using Playwright headless browser."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={"width": width, "height": height}
                )
                await page.set_content(html, wait_until="networkidle")
                screenshot_bytes = await page.screenshot(type="png")
                await browser.close()

                return {
                    "success": True,
                    "png_bytes": screenshot_bytes,
                    "width": width,
                    "height": height,
                    "method": "playwright",
                }
        except Exception as e:
            logger.error("playwright_capture_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "width": width,
                "height": height,
                "method": "playwright",
            }

    @staticmethod
    def _simulate_capture(html: str, width: int, height: int) -> dict[str, Any]:
        """Generate simulated capture metadata (for testing without Playwright)."""
        content_hash = hashlib.sha256(html.encode()).hexdigest()[:16]
        return {
            "success": True,
            "content_hash": content_hash,
            "width": width,
            "height": height,
            "method": "simulated",
            "html_length": len(html),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "capture_count": self._capture_count,
            "playwright_available": self._playwright_available,
            "viewport": f"{self.viewport_width}x{self.viewport_height}",
        }
