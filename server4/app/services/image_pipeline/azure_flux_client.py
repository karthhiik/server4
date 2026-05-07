"""
Azure FLUX.1-Kontext-pro — Primary high-quality image generation provider.

API: OpenAI-compatible image generation endpoint.
Response: JSON with data[0].b64_json (base64 PNG).
Verified: 2026-04-05, ~17s latency, ~1MB output, 1024x1024 PNG.
"""

import base64
import time
from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


@dataclass
class FluxImageResponse:
    """Result from Azure Flux image generation."""
    image_bytes: bytes
    revised_prompt: str
    latency_ms: int
    model: str = "FLUX.1-Kontext-pro"
    provider: str = "azure"
    content_type: str = "image/png"


class AzureFluxClient:
    """
    Azure FLUX.1-Kontext-pro image generation client.

    Endpoint pattern:
        {base}/openai/deployments/{deployment}/images/generations?api-version={ver}
    Auth: api-key header.
    Response: { data: [{ b64_json, revised_prompt, ... }] }
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        self.endpoint = (endpoint or settings.AZURE_FLUX_ENDPOINT).rstrip("/")
        self.api_key = api_key or settings.AZURE_FLUX_API_KEY
        self.deployment = deployment or settings.AZURE_FLUX_DEPLOYMENT_NAME
        self.api_version = api_version or settings.AZURE_FLUX_VERSION
        self.name = "azure-flux"
        self.provider = "azure"

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def _build_url(self) -> str:
        """Build the full Azure OpenAI image generation URL.

        Handles multiple endpoint formats:
        1. Full URL with deployment already included.
        2. Base URL with `/openai/v1` suffix (Azure's new "v1" surface) —
           strip it so the legacy `/openai/deployments/...` path can be
           appended cleanly. Without this normalization the caller ends
           up with `.../openai/v1/openai/deployments/...` → HTTP 404.
        3. Plain base URL (`https://{resource}.openai.azure.com`) needing
           the full `/openai/deployments/...` path appended.
        """
        endpoint = self.endpoint
        if "/images/generations" in endpoint:
            return endpoint
        if f"/deployments/{self.deployment}" in endpoint:
            return f"{endpoint}/images/generations?api-version={self.api_version}"
        # Normalize away the `/openai/v1` suffix if present — Azure's v1
        # surface uses a different routing convention and we want the
        # deployments path.
        for suffix in ("/openai/v1", "/openai/v1/", "/v1", "/v1/"):
            if endpoint.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                break
        endpoint = endpoint.rstrip("/")
        return (
            f"{endpoint}/openai/deployments/{self.deployment}"
            f"/images/generations?api-version={self.api_version}"
        )

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        quality: str = "standard",
    ) -> FluxImageResponse:
        """
        Generate an image via Azure FLUX.1-Kontext-pro.

        Args:
            prompt: Image generation prompt.
            size: Image dimensions (default 1024x1024).
            n: Number of images to generate.
            quality: Image quality tier.

        Returns:
            FluxImageResponse with decoded image bytes.

        Raises:
            ConnectionError: If client not configured.
            httpx.HTTPStatusError: On API errors.
        """
        if not self.is_configured:
            raise ConnectionError("Azure Flux client not configured")

        url = self._build_url()
        payload = {
            "prompt": prompt,
            "n": n,
            "size": size,
        }

        start = time.monotonic()

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = int((time.monotonic() - start) * 1000)

        # Extract b64_json from response. The Azure FLUX endpoint
        # sometimes returns `revised_prompt: null` even on success, so
        # we coalesce to the original prompt before any len()/log call
        # — otherwise the success-path log raises
        # `object of type 'NoneType' has no len()` and the whole tier
        # is mistakenly recorded as a failure.
        image_data = data.get("data", [{}])[0] or {}
        b64_str = image_data.get("b64_json") or ""
        if not b64_str:
            raise ValueError("Azure Flux response missing b64_json field")

        image_bytes = base64.b64decode(b64_str)
        revised_prompt = image_data.get("revised_prompt") or prompt

        logger.info(
            "azure_flux_generated",
            size_kb=len(image_bytes) // 1024,
            latency_ms=elapsed,
            revised_prompt_len=len(revised_prompt or ""),
        )

        return FluxImageResponse(
            image_bytes=image_bytes,
            revised_prompt=revised_prompt,
            latency_ms=elapsed,
        )

    async def health_check(self) -> bool:
        """Quick health check via minimal generation."""
        try:
            result = await self.generate("A simple blue circle on white background")
            return len(result.image_bytes) > 1024
        except Exception:
            return False
