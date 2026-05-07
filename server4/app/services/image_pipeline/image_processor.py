"""
Image Processor — Resize, optimize, format conversion for generated images.

Handles:
- Resize to target dimensions (fit, fill, cover modes)
- JPEG/PNG/WebP format conversion
- Quality optimization with size constraints
- File size validation (min 5KB, max 2MB)
- Thumbnail generation for previews
"""

import io
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import structlog

logger = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────────

MIN_IMAGE_SIZE = 5 * 1024  # 5KB — below is likely blank/error
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB — above needs compression
THUMBNAIL_SIZE = (256, 144)  # 16:9 thumbnail


class ImageFormat(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"


class ResizeMode(str, Enum):
    FIT = "fit"  # Fit within bounds, preserving aspect ratio
    FILL = "fill"  # Fill exactly, may crop
    COVER = "cover"  # Cover area, may have excess


@dataclass
class ProcessedImage:
    """Result of image processing."""
    image_bytes: bytes
    width: int
    height: int
    format: ImageFormat
    original_size: int
    processed_size: int
    content_type: str

    @property
    def was_compressed(self) -> bool:
        return self.processed_size < self.original_size

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return 1.0 - (self.processed_size / self.original_size)


class ImageProcessor:
    """
    Image processing pipeline for generated slide images.

    Resizes, optimizes, and converts generated images to
    the appropriate format and size for presentation rendering.
    """

    def validate(self, image_bytes: bytes) -> bool:
        """
        Validate that image bytes represent a valid image.

        Returns True if valid, False otherwise.
        """
        if len(image_bytes) < MIN_IMAGE_SIZE:
            logger.warning(
                "image_too_small",
                size_bytes=len(image_bytes),
                min_bytes=MIN_IMAGE_SIZE,
            )
            return False

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            return True
        except Exception as e:
            logger.warning("image_validation_failed", error=str(e))
            return False

    def process(
        self,
        image_bytes: bytes,
        target_width: int = 1920,
        target_height: int = 1080,
        output_format: ImageFormat = ImageFormat.JPEG,
        quality: int = 85,
        max_size: int = MAX_IMAGE_SIZE,
        resize_mode: ResizeMode = ResizeMode.FIT,
    ) -> ProcessedImage:
        """
        Process image: resize + optimize + convert format.

        Args:
            image_bytes: Raw image bytes from generation.
            target_width: Target width in pixels.
            target_height: Target height in pixels.
            output_format: Desired output format.
            quality: JPEG/WebP quality (1-100).
            max_size: Maximum output size in bytes.
            resize_mode: How to handle aspect ratio mismatch.

        Returns:
            ProcessedImage with optimized bytes and metadata.
        """
        from PIL import Image

        original_size = len(image_bytes)
        img = Image.open(io.BytesIO(image_bytes))

        # Convert modes for format compatibility
        if output_format == ImageFormat.JPEG and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        elif output_format == ImageFormat.PNG and img.mode == "P":
            img = img.convert("RGBA")

        # Resize
        img = self._resize(img, target_width, target_height, resize_mode)

        # Export with quality optimization
        result_bytes = self._export_with_size_limit(
            img, output_format, quality, max_size
        )

        content_type = {
            ImageFormat.JPEG: "image/jpeg",
            ImageFormat.PNG: "image/png",
            ImageFormat.WEBP: "image/webp",
        }[output_format]

        processed = ProcessedImage(
            image_bytes=result_bytes,
            width=img.width,
            height=img.height,
            format=output_format,
            original_size=original_size,
            processed_size=len(result_bytes),
            content_type=content_type,
        )

        logger.info(
            "image_processed",
            original_kb=original_size // 1024,
            processed_kb=processed.processed_size // 1024,
            dimensions=f"{img.width}x{img.height}",
            format=output_format.value,
            compressed=processed.was_compressed,
        )

        return processed

    def generate_thumbnail(
        self,
        image_bytes: bytes,
        size: tuple[int, int] = THUMBNAIL_SIZE,
    ) -> bytes:
        """Generate a small thumbnail for preview purposes."""
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.thumbnail(size, Image.Resampling.LANCZOS)

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=70)
        return output.getvalue()

    def _resize(
        self,
        img: "Image.Image",
        target_w: int,
        target_h: int,
        mode: ResizeMode,
    ) -> "Image.Image":
        """Resize image according to the specified mode."""
        from PIL import Image

        if mode == ResizeMode.FIT:
            img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            return img

        elif mode == ResizeMode.FILL:
            # Scale to fill, then crop to exact size
            ratio_w = target_w / img.width
            ratio_h = target_h / img.height
            scale = max(ratio_w, ratio_h)
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Crop to target size from center
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            return img.crop((left, top, left + target_w, top + target_h))

        elif mode == ResizeMode.COVER:
            ratio_w = target_w / img.width
            ratio_h = target_h / img.height
            scale = min(ratio_w, ratio_h)
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        return img

    def _export_with_size_limit(
        self,
        img: "Image.Image",
        fmt: ImageFormat,
        quality: int,
        max_size: int,
    ) -> bytes:
        """Export image, reducing quality if needed to stay under max_size."""
        pil_format = fmt.value.upper()
        if pil_format == "JPEG":
            pil_format = "JPEG"

        output = io.BytesIO()

        while quality >= 20:
            output.seek(0)
            output.truncate()

            if fmt == ImageFormat.PNG:
                # PNG ignores quality — use optimize flag
                img.save(output, format="PNG", optimize=True)
                result = output.getvalue()
                if len(result) <= max_size:
                    return result
                # PNG can't be compressed further via quality, convert to JPEG
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                fmt = ImageFormat.JPEG
                pil_format = "JPEG"
                continue

            img.save(output, format=pil_format, quality=quality, optimize=True)
            result = output.getvalue()
            if len(result) <= max_size:
                return result
            quality -= 10

        # Return whatever we have even if over size
        return output.getvalue()
