"""
Social Media Export Service — export slides as social media assets.

Supports:
- LinkedIn: Optimized images for LinkedIn posts
- Instagram: Square and story formats
- X (Twitter): Optimized for timeline
- GIF: Animated slide sequences
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class SocialPlatform(Enum):
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    X = "x"
    INSTAGRAM_STORY = "instagram_story"


class ExportFormat(Enum):
    PNG = "png"
    JPG = "jpg"
    GIF = "gif"
    MP4 = "mp4"


@dataclass
class SocialExportConfig:
    platform: SocialPlatform
    format: ExportFormat
    width: int
    height: int
    quality: int = 95
    duration: Optional[float] = None  # For GIF/MP4


@dataclass
class SocialExportResult:
    success: bool
    file_path: Optional[str]
    error: Optional[str]
    metadata: dict


class SocialMediaExporter:
    """Export presentation slides for social media platforms."""

    # Platform-specific dimensions
    DIMENSIONS = {
        SocialPlatform.LINKEDIN: (1200, 627),  # LinkedIn post
        SocialPlatform.INSTAGRAM: (1080, 1080),  # Instagram square
        SocialPlatform.X: (1200, 675),  # X (Twitter)
        SocialPlatform.INSTAGRAM_STORY: (1080, 1920),  # Instagram story
    }

    def __init__(self):
        pass

    def export_slide(
        self,
        slide_data: dict,
        config: SocialExportConfig,
        output_dir: str,
    ) -> SocialExportResult:
        """Export a single slide for social media."""
        try:
            # Validate dimensions for platform
            expected_dims = self.DIMENSIONS.get(config.platform)
            if expected_dims and (config.width, config.height) != expected_dims:
                logger.warning(
                    "social_export.dimension_mismatch",
                    platform=config.platform.value,
                    expected=expected_dims,
                    provided=(config.width, config.height),
                )

            # Generate export based on format
            if config.format == ExportFormat.GIF:
                return self._export_gif(slide_data, config, output_dir)
            elif config.format == ExportFormat.MP4:
                return self._export_video(slide_data, config, output_dir)
            else:
                return self._export_image(slide_data, config, output_dir)

        except Exception as e:
            logger.error("social_export.failed", error=str(e), platform=config.platform.value)
            return SocialExportResult(
                success=False,
                file_path=None,
                error=str(e),
                metadata={"platform": config.platform.value},
            )

    def _export_image(
        self,
        slide_data: dict,
        config: SocialExportConfig,
        output_dir: str,
    ) -> SocialExportResult:
        """Export slide as static image (PNG/JPG)."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Create image with specified dimensions
            img = Image.new("RGB", (config.width, config.height), color="white")
            draw = ImageDraw.Draw(img)

            # Extract slide content
            title = slide_data.get("title", "")
            content = slide_data.get("content", "")

            # Simple rendering (in production, use proper slide rendering)
            try:
                font_title = ImageFont.truetype("arial.ttf", 48)
                font_content = ImageFont.truetype("arial.ttf", 32)
            except:
                font_title = ImageFont.load_default()
                font_content = ImageFont.load_default()

            # Draw title
            draw.text((50, 50), title, fill="black", font=font_title)

            # Draw content (wrapped)
            y_offset = 150
            words = content.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                if draw.textlength(test_line, font=font_content) < config.width - 100:
                    line = test_line
                else:
                    draw.text((50, y_offset), line, fill="gray", font=font_content)
                    line = word + " "
                    y_offset += 50
            draw.text((50, y_offset), line, fill="gray", font=font_content)

            # Save image
            output_path = Path(output_dir) / f"social_{config.platform.value}.{config.format.value}"
            img.save(output_path, quality=config.quality)

            return SocialExportResult(
                success=True,
                file_path=str(output_path),
                error=None,
                metadata={
                    "platform": config.platform.value,
                    "format": config.format.value,
                    "dimensions": (config.width, config.height),
                },
            )

        except ImportError:
            return SocialExportResult(
                success=False,
                file_path=None,
                error="PIL not installed; add Pillow to requirements",
                metadata={"platform": config.platform.value},
            )
        except Exception as e:
            return SocialExportResult(
                success=False,
                file_path=None,
                error=str(e),
                metadata={"platform": config.platform.value},
            )

    def _export_gif(
        self,
        slide_data: dict,
        config: SocialExportConfig,
        output_dir: str,
    ) -> SocialExportResult:
        """Export slide sequence as animated GIF."""
        try:
            from PIL import Image, ImageDraw

            duration = config.duration or 3.0  # Default 3 seconds
            frames = int(duration * 10)  # 10 frames per second

            images = []
            for i in range(frames):
                # Create frame with progressive fade-in
                img = Image.new("RGB", (config.width, config.height), color="white")
                draw = ImageDraw.Draw(img)

                # Calculate opacity for this frame
                opacity = min(1.0, (i + 1) / (frames * 0.7))

                # Draw slide content with opacity
                title = slide_data.get("title", "")
                if title:
                    try:
                        font = ImageFont.truetype("arial.ttf", 48)
                    except:
                        font = ImageFont.load_default()
                    
                    # Simple opacity simulation via gray level
                    gray_value = int(255 * (1 - opacity))
                    draw.text((50, 50), title, fill=(gray_value, gray_value, gray_value), font=font)

                images.append(img)

            # Save as GIF
            output_path = Path(output_dir) / f"social_{config.platform.value}.gif"
            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:],
                duration=int(duration * 1000 / frames),
                loop=0,
            )

            return SocialExportResult(
                success=True,
                file_path=str(output_path),
                error=None,
                metadata={
                    "platform": config.platform.value,
                    "format": "gif",
                    "duration": duration,
                    "frames": frames,
                },
            )

        except ImportError:
            return SocialExportResult(
                success=False,
                file_path=None,
                error="PIL not installed; add Pillow to requirements",
                metadata={"platform": config.platform.value},
            )
        except Exception as e:
            return SocialExportResult(
                success=False,
                file_path=None,
                error=str(e),
                metadata={"platform": config.platform.value},
            )

    def _export_video(
        self,
        slide_data: dict,
        config: SocialExportConfig,
        output_dir: str,
    ) -> SocialExportResult:
        """Export slide as video (MP4)."""
        # Video export requires additional dependencies (ffmpeg, imageio)
        # For now, return a placeholder result
        return SocialExportResult(
            success=False,
            file_path=None,
            error="Video export not yet implemented; requires ffmpeg and imageio",
            metadata={"platform": config.platform.value, "format": "mp4"},
        )

    def get_preferred_config(self, platform: SocialPlatform) -> SocialExportConfig:
        """Get recommended export config for a platform."""
        dims = self.DIMENSIONS.get(platform, (1200, 627))
        
        if platform == SocialPlatform.INSTAGRAM_STORY:
            return SocialExportConfig(
                platform=platform,
                format=ExportFormat.MP4,
                width=dims[0],
                height=dims[1],
                duration=15.0,
            )
        elif platform == SocialPlatform.INSTAGRAM:
            return SocialExportConfig(
                platform=platform,
                format=ExportFormat.JPG,
                width=dims[0],
                height=dims[1],
                quality=95,
            )
        else:
            return SocialExportConfig(
                platform=platform,
                format=ExportFormat.PNG,
                width=dims[0],
                height=dims[1],
                quality=95,
            )
