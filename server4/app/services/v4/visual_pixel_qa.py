"""Rendered screenshot + pixel QA for V4 decks.

The checks here are free/local: Playwright captures the existing Studio
presentation route, then Pillow inspects the PNG pixels. No OCR, LLM, or paid
API is used, so the report never invents visual facts.
"""

from __future__ import annotations

import io
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Sequence

from app.config import settings
from app.services.v4.slide_screenshot import capture_deck_screenshots


_SCHEMA_VERSION = 1
_MIN_WIDTH = 1200
_MIN_HEIGHT = 675


@dataclass(frozen=True)
class PixelQaIssue:
    code: str
    severity: str
    slide_index: int
    message: str
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SlidePixelQaReport:
    slide_index: int
    passed: bool
    score: int
    width: int
    height: int
    mean_luminance: float
    luminance_stddev: float
    edge_ink_ratio: float
    right_edge_artifact_score: float
    issues: list[PixelQaIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_index": self.slide_index,
            "passed": self.passed,
            "score": self.score,
            "width": self.width,
            "height": self.height,
            "mean_luminance": round(self.mean_luminance, 2),
            "luminance_stddev": round(self.luminance_stddev, 2),
            "edge_ink_ratio": round(self.edge_ink_ratio, 4),
            "right_edge_artifact_score": round(self.right_edge_artifact_score, 4),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class DeckPixelQaReport:
    schema_version: int
    status: str
    passed: bool
    score: int
    summary: str
    captured_at: str
    frontend_origin: str
    slide_reports: list[SlidePixelQaReport]
    issues: list[PixelQaIssue]
    capture_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "passed": self.passed,
            "score": self.score,
            "summary": self.summary,
            "captured_at": self.captured_at,
            "frontend_origin": self.frontend_origin,
            "slide_reports": [report.to_dict() for report in self.slide_reports],
            "issues": [issue.to_dict() for issue in self.issues],
            "capture_error": self.capture_error,
        }


async def run_project_visual_pixel_qa(
    *,
    project_id: str,
    slide_count: int,
    frontend_origin: str | None = None,
    auth_token: str | None = None,
    per_slide_timeout_s: float = 8.0,
    capture: Callable[..., Awaitable[list[bytes]]] = capture_deck_screenshots,
) -> DeckPixelQaReport:
    """Capture the real presentation route and inspect screenshots."""

    origin = (frontend_origin or settings.FRONTEND_ORIGIN or "http://localhost:8080").rstrip("/")
    if slide_count <= 0:
        return DeckPixelQaReport(
            schema_version=_SCHEMA_VERSION,
            status="not_run",
            passed=False,
            score=0,
            summary="Visual pixel QA did not run because the deck has no slides.",
            captured_at=_now(),
            frontend_origin=origin,
            slide_reports=[],
            issues=[],
            capture_error="slide_count must be positive",
        )

    try:
        pages = await capture(
            project_id=project_id,
            slide_count=slide_count,
            frontend_origin=origin,
            viewport=(1920, 1080),
            auth_token=auth_token,
            per_slide_timeout_s=per_slide_timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        return DeckPixelQaReport(
            schema_version=_SCHEMA_VERSION,
            status="capture_failed",
            passed=False,
            score=0,
            summary="Visual pixel QA could not capture rendered slides.",
            captured_at=_now(),
            frontend_origin=origin,
            slide_reports=[],
            issues=[],
            capture_error=str(exc)[:500],
        )

    slide_reports = analyze_screenshot_pngs(pages)
    deck_issues = [issue for report in slide_reports for issue in report.issues]
    score = _deck_score(slide_reports)
    passed = bool(slide_reports) and score >= 75 and not any(
        issue.severity == "blocker" for issue in deck_issues
    )
    status = "passed" if passed else "needs_review"
    summary = (
        f"Rendered pixel QA passed with score {score}/100."
        if passed
        else f"Rendered pixel QA found {len(deck_issues)} issue(s); review before investor export."
    )
    return DeckPixelQaReport(
        schema_version=_SCHEMA_VERSION,
        status=status,
        passed=passed,
        score=score,
        summary=summary,
        captured_at=_now(),
        frontend_origin=origin,
        slide_reports=slide_reports,
        issues=deck_issues,
    )


def analyze_screenshot_pngs(pages: Sequence[bytes]) -> list[SlidePixelQaReport]:
    return [analyze_screenshot_png(page, index) for index, page in enumerate(pages)]


def analyze_screenshot_png(png: bytes, slide_index: int) -> SlidePixelQaReport:
    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        issue = PixelQaIssue(
            code="pillow_unavailable",
            severity="blocker",
            slide_index=slide_index,
            message="Pillow is unavailable, so screenshot pixels could not be inspected.",
            recommendation="Install Pillow in the server4 environment.",
        )
        return _failed_report(slide_index, issue, str(exc))

    try:
        with Image.open(io.BytesIO(png)) as image:
            image = image.convert("RGB")
            width, height = image.size
            sample = image.resize((96, 54))
            pixels = list(sample.getdata())
    except Exception as exc:  # noqa: BLE001
        issue = PixelQaIssue(
            code="png_decode_failed",
            severity="blocker",
            slide_index=slide_index,
            message="Screenshot PNG could not be decoded.",
            recommendation="Re-run capture and verify the presentation route returns a real slide.",
        )
        return _failed_report(slide_index, issue, str(exc))

    lums = [_lum(pixel) for pixel in pixels]
    mean = sum(lums) / max(1, len(lums))
    variance = sum((value - mean) ** 2 for value in lums) / max(1, len(lums))
    stddev = math.sqrt(variance)
    edge_ratio = _edge_ink_ratio(pixels, 96, 54)
    right_artifact = _right_edge_artifact_score(pixels, 96, 54)
    issues: list[PixelQaIssue] = []

    if width < _MIN_WIDTH or height < _MIN_HEIGHT:
        issues.append(
            PixelQaIssue(
                code="low_capture_resolution",
                severity="warn",
                slide_index=slide_index,
                message=f"Screenshot resolution is {width}x{height}, below the expected 16:9 QA capture size.",
                recommendation="Run QA with a 1920x1080 viewport before export.",
            )
        )
    if stddev < 4.0:
        issues.append(
            PixelQaIssue(
                code="near_blank_render",
                severity="blocker",
                slide_index=slide_index,
                message="Rendered slide appears near blank based on pixel variance.",
                recommendation="Open the slide in Studio and regenerate or repair rendering.",
            )
        )
    if mean < 8.0 and stddev < 18.0:
        issues.append(
            PixelQaIssue(
                code="too_dark_low_detail",
                severity="warn",
                slide_index=slide_index,
                message="Rendered slide is extremely dark with little visible detail.",
                recommendation="Increase contrast or add a stronger text/background separation.",
            )
        )
    if mean > 247.0 and stddev < 18.0:
        issues.append(
            PixelQaIssue(
                code="too_light_low_detail",
                severity="warn",
                slide_index=slide_index,
                message="Rendered slide is extremely light with little visible detail.",
                recommendation="Increase contrast before sharing or exporting.",
            )
        )
    if edge_ratio > 0.34:
        issues.append(
            PixelQaIssue(
                code="possible_content_cropped_at_edge",
                severity="warn",
                slide_index=slide_index,
                message="High amount of non-background pixels appears near the slide edge.",
                recommendation="Check safe areas; important text or controls may be clipped.",
            )
        )
    if right_artifact > 0.72:
        issues.append(
            PixelQaIssue(
                code="possible_right_edge_artifact",
                severity="warn",
                slide_index=slide_index,
                message="A strong vertical artifact appears near the right edge.",
                recommendation="Inspect presentation navigation/overlay controls and remove unintended side rails.",
            )
        )

    score = _slide_score(issues)
    return SlidePixelQaReport(
        slide_index=slide_index,
        passed=score >= 75 and not any(issue.severity == "blocker" for issue in issues),
        score=score,
        width=width,
        height=height,
        mean_luminance=mean,
        luminance_stddev=stddev,
        edge_ink_ratio=edge_ratio,
        right_edge_artifact_score=right_artifact,
        issues=issues,
    )


def _failed_report(slide_index: int, issue: PixelQaIssue, detail: str) -> SlidePixelQaReport:
    return SlidePixelQaReport(
        slide_index=slide_index,
        passed=False,
        score=0,
        width=0,
        height=0,
        mean_luminance=0,
        luminance_stddev=0,
        edge_ink_ratio=0,
        right_edge_artifact_score=0,
        issues=[
            PixelQaIssue(
                code=issue.code,
                severity=issue.severity,
                slide_index=slide_index,
                message=f"{issue.message} {detail[:160]}".strip(),
                recommendation=issue.recommendation,
            )
        ],
    )


def _lum(pixel: tuple[int, int, int]) -> float:
    r, g, b = pixel
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _edge_ink_ratio(pixels: Sequence[tuple[int, int, int]], width: int, height: int) -> float:
    corners = [pixels[0], pixels[width - 1], pixels[-width], pixels[-1]]
    bg = tuple(int(sum(channel) / len(corners)) for channel in zip(*corners))
    edge_pixels: list[tuple[int, int, int]] = []
    band = max(2, int(width * 0.04))
    row_band = max(2, int(height * 0.04))
    for y in range(height):
        for x in range(width):
            if x < band or x >= width - band or y < row_band or y >= height - row_band:
                edge_pixels.append(pixels[y * width + x])
    changed = sum(1 for pixel in edge_pixels if _rgb_distance(pixel, bg) > 34)
    return changed / max(1, len(edge_pixels))


def _right_edge_artifact_score(pixels: Sequence[tuple[int, int, int]], width: int, height: int) -> float:
    start = int(width * 0.80)
    best = 0.0
    for x in range(start, width - 1):
        strong = 0
        for y in range(height):
            left = pixels[y * width + x]
            right = pixels[y * width + x + 1]
            if _rgb_distance(left, right) > 48:
                strong += 1
        best = max(best, strong / max(1, height))
    return best


def _rgb_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((av - bv) ** 2 for av, bv in zip(a, b)))


def _slide_score(issues: Sequence[PixelQaIssue]) -> int:
    score = 100
    for issue in issues:
        score -= 35 if issue.severity == "blocker" else 12
    return max(0, min(100, score))


def _deck_score(slide_reports: Sequence[SlidePixelQaReport]) -> int:
    if not slide_reports:
        return 0
    return int(round(sum(report.score for report in slide_reports) / len(slide_reports)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
