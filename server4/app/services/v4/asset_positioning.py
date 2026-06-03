"""
Asset Positioning Agent — Barise Presentation SaaS

Intelligently positions images, icons, and decorative assets within
slide layouts based on content density, visual hierarchy, and design
token constraints. Produces deterministic crop/zoom/focal-point data
for kit components.

Usage:
    from app.services.v4.asset_positioning import AssetPositioningAgent
    agent = AssetPositioningAgent()
    result = agent.position_image(
        image_url="...",
        slide_layout="content_with_image_right",
        content_density="medium",
        text_regions=[{"x": 0, "y": 0, "w": 800, "h": 1080}],
    )
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class FocalPoint:
    """Normalized focal point (0..1) for image cropping."""

    x: float = 0.5
    y: float = 0.5
    scale: float = 1.0

    def to_crop_dict(self) -> dict[str, float]:
        return {"focalX": self.x, "focalY": self.y, "scale": self.scale}


@dataclass(frozen=True)
class PositionedAsset:
    """Result of asset positioning — ready for kit component props."""

    image_url: str
    focal_point: FocalPoint
    crop_region: Optional[dict[str, int]] = None
    overlay_suggested: bool = False
    scrim_intensity: float = 0.0
    layout_zone: str = ""
    sizing_mode: str = "cover"  # cover | contain | fill

    def to_props(self) -> dict[str, Any]:
        return {
            "imageUrl": self.image_url,
            "imageCrop": self.focal_point.to_crop_dict(),
            "crop_region": self.crop_region,
            "overlay_suggested": self.overlay_suggested,
            "scrim_intensity": self.scrim_intensity,
            "sizing_mode": self.sizing_mode,
        }


class AssetPositioningAgent:
    """
    Positions assets on slides using heuristics + optional LLM guidance.

    Two modes:
        1. Heuristic mode (fast, deterministic, no API call)
        2. Vision mode (analyzes actual image content via vision model)
    """

    # Pre-computed focal points per layout archetype
    _LAYOUT_FOCALS: dict[str, FocalPoint] = {
        # When image is on the right, weight focal to the left side
        "content_with_image_right": FocalPoint(x=0.35, y=0.5, scale=1.1),
        # When image is on the left, weight focal to the right side
        "content_with_image_left": FocalPoint(x=0.65, y=0.5, scale=1.1),
        # Full-bleed hero: center, slight zoom
        "hero_with_subtitle": FocalPoint(x=0.5, y=0.4, scale=1.15),
        # Cover slide: top-weighted for text overlay at bottom
        "cover_slide": FocalPoint(x=0.5, y=0.35, scale=1.2),
        # Bento grid card: center
        "bento_card": FocalPoint(x=0.5, y=0.5, scale=1.0),
        # Team member: face is usually upper-center
        "team_portrait": FocalPoint(x=0.5, y=0.3, scale=1.05),
        # Product mockup: center with moderate zoom
        "app_mockup": FocalPoint(x=0.5, y=0.5, scale=1.0),
        # Social proof / logos: center
        "logo_marquee": FocalPoint(x=0.5, y=0.5, scale=0.9),
        # Quote highlight background: center, pulled back
        "quote_background": FocalPoint(x=0.5, y=0.5, scale=1.3),
        # Comparison: depends on side, default center
        "before_after": FocalPoint(x=0.5, y=0.5, scale=1.0),
        # Roadmap / process: decorative, center
        "process_decorative": FocalPoint(x=0.5, y=0.5, scale=1.2),
    }

    # Scrim intensity per layout (0..1)
    _SCRIM_MAP: dict[str, float] = {
        "hero_with_subtitle": 0.45,
        "cover_slide": 0.55,
        "quote_background": 0.35,
        "content_with_image_right": 0.0,
        "content_with_image_left": 0.0,
    }

    def __init__(self, vision_enabled: bool = False) -> None:
        self.vision_enabled = vision_enabled

    def position_image(
        self,
        image_url: str,
        slide_layout: str,
        content_density: str = "medium",
        text_regions: Optional[list[dict[str, int]]] = None,
        image_analysis: Optional[dict[str, Any]] = None,
    ) -> PositionedAsset:
        """
        Position a single image asset within a slide layout.

        Args:
            image_url: URL of the image asset.
            slide_layout: Layout archetype name.
            content_density: "low" | "medium" | "high" — affects crop aggressiveness.
            text_regions: List of text bounding boxes to avoid overlapping.
            image_analysis: Optional pre-computed vision analysis (faces, objects, saliency).

        Returns:
            PositionedAsset with crop/zoom/focal data.
        """
        focal = self._LAYOUT_FOCALS.get(slide_layout, FocalPoint(x=0.5, y=0.5, scale=1.0))
        scrim = self._SCRIM_MAP.get(slide_layout, 0.0)
        overlay = scrim > 0.0

        # Adjust scale based on content density
        density_scale = {"low": 0.9, "medium": 1.0, "high": 1.15}.get(content_density, 1.0)
        adjusted_focal = FocalPoint(
            x=focal.x,
            y=focal.y,
            scale=min(focal.scale * density_scale, 2.0),
        )

        # If text regions provided, nudge focal point away from dense text
        if text_regions:
            adjusted_focal = self._avoid_text_regions(adjusted_focal, text_regions)

        # If vision analysis available, refine focal point
        if image_analysis and self.vision_enabled:
            adjusted_focal = self._refine_with_analysis(adjusted_focal, image_analysis)

        return PositionedAsset(
            image_url=image_url,
            focal_point=adjusted_focal,
            overlay_suggested=overlay,
            scrim_intensity=scrim,
            layout_zone=slide_layout,
        )

    def position_multiple(
        self,
        assets: list[dict[str, Any]],
        slide_layout: str,
    ) -> list[PositionedAsset]:
        """Position multiple assets on a single slide with collision avoidance."""
        results: list[PositionedAsset] = []
        occupied: list[dict[str, int]] = []

        for asset in assets:
            positioned = self.position_image(
                image_url=asset["url"],
                slide_layout=asset.get("zone", slide_layout),
                content_density=asset.get("density", "medium"),
                text_regions=occupied if occupied else None,
            )
            results.append(positioned)
            # Approximate image region as occupying space
            occupied.append({"x": 0, "y": 0, "w": 200, "h": 200})

        return results

    def _avoid_text_regions(self, focal: FocalPoint, regions: list[dict[str, int]]) -> FocalPoint:
        """Heuristic: nudge focal point away from text-heavy areas."""
        if not regions:
            return focal

        # Compute text density per vertical half
        top_weight = sum(r.get("y", 0) + r.get("h", 0) / 2 < 540 for r in regions)
        bottom_weight = len(regions) - top_weight

        # If text is predominantly in top half, pull focal down
        if top_weight > bottom_weight * 1.5:
            return FocalPoint(x=focal.x, y=min(focal.y + 0.15, 0.85), scale=focal.scale)
        # If text is predominantly in bottom half, pull focal up
        if bottom_weight > top_weight * 1.5:
            return FocalPoint(x=focal.x, y=max(focal.y - 0.15, 0.15), scale=focal.scale)

        return focal

    def _refine_with_analysis(self, focal: FocalPoint, analysis: dict[str, Any]) -> FocalPoint:
        """Refine focal point using vision analysis (faces, saliency)."""
        faces = analysis.get("faces", [])
        if faces:
            # Center on first detected face
            face = faces[0]
            cx = face.get("x", 0.5) + face.get("width", 0) / 2
            cy = face.get("y", 0.5) + face.get("height", 0) / 2
            # Blend with layout default (70% face, 30% layout)
            return FocalPoint(
                x=0.7 * cx + 0.3 * focal.x,
                y=0.7 * cy + 0.3 * focal.y,
                scale=focal.scale,
            )

        saliency = analysis.get("saliency_map")
        if saliency:
            # Use highest-saliency point if available
            max_point = saliency.get("max_point", {"x": 0.5, "y": 0.5})
            return FocalPoint(
                x=0.6 * max_point["x"] + 0.4 * focal.x,
                y=0.6 * max_point["y"] + 0.4 * focal.y,
                scale=focal.scale,
            )

        return focal

    # ── Team photo grid positioning ─────────────────────────────
    def position_team_photos(
        self,
        members: list[dict[str, Any]],
        layout_archetype: str = "grid-3",
    ) -> list[PositionedAsset]:
        """Position a list of team-member photos for a team slide.

        Each photo uses the `team_portrait` focal (face upper-center) but
        we vary the scale slightly across slots to avoid the "every
        member looks identically cropped" effect that makes generated
        team grids feel template-stamped. The tiny perturbation reads as
        photographic variation rather than misalignment.

        Layout archetype hints how dense the grid is:
            grid-2 / grid-3 — equal cells; standard portrait crop
            grid-4 / grid-5 — denser cells; pull focal slightly higher
            bento-team       — mixed sizes; first member is the hero

        `members` is a list of dicts with at least `photo_url` (string).
        Members without a `photo_url` are skipped — caller is responsible
        for supplying placeholder photos before this call if desired.
        """
        results: list[PositionedAsset] = []
        if not members:
            return results

        is_dense = layout_archetype in ("grid-4", "grid-5", "grid-6")
        is_bento = layout_archetype == "bento-team"

        for idx, member in enumerate(members):
            photo_url = member.get("photo_url")
            if not photo_url:
                continue

            # Slight per-slot scale variation: 0.95–1.10 range, evenly
            # distributed using a low-discrepancy sequence so neighbors
            # don't share the same scale.
            slot_jitter = 0.95 + 0.15 * ((idx * 0.618) % 1.0)

            if is_bento and idx == 0:
                # Hero slot — pull focal slightly down so the face sits in
                # the upper third, and zoom in for impact.
                focal = FocalPoint(x=0.5, y=0.32, scale=1.18)
            elif is_dense:
                # Tight cells — face higher, slight zoom-in to fill cell.
                focal = FocalPoint(x=0.5, y=0.28, scale=1.12 * slot_jitter)
            else:
                base = self._LAYOUT_FOCALS["team_portrait"]
                focal = FocalPoint(x=base.x, y=base.y, scale=base.scale * slot_jitter)

            results.append(
                PositionedAsset(
                    image_url=photo_url,
                    focal_point=focal,
                    overlay_suggested=False,
                    scrim_intensity=0.0,
                    layout_zone="team_portrait",
                    sizing_mode="cover",
                )
            )

        logger.info(
            "team_photos_positioned",
            n_members=len(members),
            n_positioned=len(results),
            layout=layout_archetype,
        )
        return results

    # ── Brand icon (company logo) positioning ──────────────────
    def position_brand_icon(
        self,
        icon_url: str,
        slide_layout: str,
        is_cover: bool = False,
        theme_is_dark: bool = False,
    ) -> dict[str, Any]:
        """Return placement props for a company brand icon on a slide.

        Coordinates are normalized 0..1 against the 1920x1080 stage so
        kit components can use them with `position: absolute` + `top/left`
        as percentages, or feed them straight into PPTX exports. We pick:

            - Cover/title slides: top-left, prominent (12% of slide width)
            - Content slides: bottom-right, restrained (5% of width)
            - Quote/full-bleed: top-right, watermark-mode (low opacity)

        The returned dict is meant to be merged into the slide's kit
        component props under a stable key (e.g. `brandIcon`).
        """
        url = (icon_url or "").strip()
        if not url:
            return {}

        if is_cover or slide_layout in ("cover_slide", "hero_with_subtitle"):
            placement = {
                "anchor": "top-left",
                "x_pct": 0.04,
                "y_pct": 0.05,
                "width_pct": 0.12,
                "opacity": 1.0,
                "background_chip": False,
            }
        elif slide_layout in ("quote_background", "image-full"):
            placement = {
                "anchor": "top-right",
                "x_pct": 0.92,
                "y_pct": 0.05,
                "width_pct": 0.06,
                "opacity": 0.6,
                "background_chip": True,
            }
        else:
            placement = {
                "anchor": "bottom-right",
                "x_pct": 0.92,
                "y_pct": 0.92,
                "width_pct": 0.05,
                "opacity": 0.85,
                "background_chip": False,
            }

        # Brand chip background — ensures the icon stays legible over
        # busy backgrounds. Only applied on watermark-mode placements.
        if placement["background_chip"]:
            placement["chip_color"] = "#000000" if not theme_is_dark else "#ffffff"
            placement["chip_alpha"] = 0.18

        return {
            "imageUrl": url,
            "placement": placement,
            "alt": "Company logo",
        }

    def suggest_background_treatment(
        self,
        slide_layout: str,
        has_text_overlay: bool = True,
        theme_is_dark: bool = False,
    ) -> dict[str, Any]:
        """Suggest background image treatment for a slide layout."""
        scrim = self._SCRIM_MAP.get(slide_layout, 0.35 if has_text_overlay else 0.0)
        return {
            "use_background_image": slide_layout in ("hero_with_subtitle", "cover_slide", "quote_background"),
            "scrim_intensity": scrim,
            "scrim_color": "#000000" if theme_is_dark else "#ffffff",
            "scrim_gradient": slide_layout in ("hero_with_subtitle", "cover_slide"),
            "text_safe_zone": "bottom" if slide_layout == "cover_slide" else "center",
        }


# Convenience singleton
_agent = AssetPositioningAgent()


def position_image(
    image_url: str,
    slide_layout: str,
    content_density: str = "medium",
    text_regions: Optional[list[dict[str, int]]] = None,
) -> PositionedAsset:
    return _agent.position_image(image_url, slide_layout, content_density, text_regions)


def position_multiple(
    assets: list[dict[str, Any]],
    slide_layout: str,
) -> list[PositionedAsset]:
    return _agent.position_multiple(assets, slide_layout)
