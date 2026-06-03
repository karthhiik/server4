"""HuggingFace Inference API Client for image generation fallback.

Uses HuggingFace's free inference API for image generation as a fallback
when primary providers fail. Downloads images locally to avoid storage costs.
"""

from __future__ import annotations

import asyncio
import io
import time
from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class HuggingFaceImageResponse:
    """Response from HuggingFace image generation."""
    image_bytes: bytes
    model: str
    latency_ms: int
    content_type: str = "image/png"


class HuggingFaceClient:
    """Client for HuggingFace Inference API image generation.

    Uses free inference API models for image generation with local download.
    """

    def __init__(self):
        """Initialize the HuggingFace client."""
        self.api_token = settings.HUGGINGFACE_API_TOKEN
        # Free inference API models that support image generation
        self.models = [
            "stabilityai/stable-diffusion-3-medium",  # SD3 Medium
            "black-forest-labs/FLUX.1-dev",  # FLUX.1 Dev
            "stabilityai/stable-diffusion-xl-base-1.0",  # SDXL
            "runwayml/stable-diffusion-v1-5",  # SD 1.5
        ]
        self.current_model_index = 0
        self.base_url = "https://api-inference.huggingface.co/models"

    def _get_model(self) -> str:
        """Get current model with round-robin."""
        model = self.models[self.current_model_index]
        self.current_model_index = (self.current_model_index + 1) % len(self.models)
        return model

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        width: int = 1024,
        height: int = 576,  # 16:9 aspect ratio
    ) -> Optional[HuggingFaceImageResponse]:
        """Generate an image using HuggingFace Inference API.

        Args:
            prompt: Text prompt for image generation
            model: Specific model to use (optional, defaults to round-robin)
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            HuggingFaceImageResponse on success, None on failure
        """
        if not self.api_token:
            logger.warning("huggingface_no_api_token")
            return None

        model = model or self._get_model()
        url = f"{self.base_url}/{model}"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
            },
        }

        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                latency_ms = int((time.perf_counter() - t0) * 1000)

                if response.status_code == 200:
                    # Response is raw image bytes
                    image_bytes = response.content

                    logger.info(
                        "huggingface_image_generated",
                        model=model,
                        size_kb=len(image_bytes) // 1024,
                        latency_ms=latency_ms,
                    )

                    return HuggingFaceImageResponse(
                        image_bytes=image_bytes,
                        model=model,
                        latency_ms=latency_ms,
                        content_type=response.headers.get("content-type", "image/png"),
                    )
                elif response.status_code == 503:
                    # Model is loading, wait and retry
                    logger.warning("huggingface_model_loading", model=model)
                    await asyncio.sleep(10)
                    return None
                else:
                    logger.error(
                        "huggingface_api_error",
                        status=response.status_code,
                        response=response.text[:200],
                    )
                    return None

        except Exception as e:
            logger.error("huggingface_generation_failed", model=model, error=str(e))
            return None

    async def generate_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        model: Optional[str] = None,
    ) -> Optional[HuggingFaceImageResponse]:
        """Generate with retry on model loading or rate limits.

        Args:
            prompt: Text prompt for image generation
            max_retries: Maximum number of retry attempts
            model: Specific model to use

        Returns:
            HuggingFaceImageResponse on success, None on failure
        """
        for attempt in range(max_retries):
            result = await self.generate(prompt, model=model)
            if result:
                return result

            # Try next model on failure
            if attempt < max_retries - 1:
                logger.info("huggingface_retry_next_model", attempt=attempt)
                await asyncio.sleep(2)

        logger.error("huggingface_all_models_failed", max_retries=max_retries)
        return None
