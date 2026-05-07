"""
Nvidia FLUX.1-schnell — Free-tier image generation provider on the
NVIDIA NIM API.

History:
    Originally targeted `stabilityai/stable-diffusion-3-medium`. NVIDIA
    decommissioned that endpoint in early 2026 (probe returns 404 for
    every `stabilityai/*` SD model). The same `nvapi-…` key still works
    against `black-forest-labs/flux.1-schnell` which is available on
    the same auth surface, so we route here instead.

API: NVIDIA NIM image-generation endpoint.
Request:  POST {endpoint}
          { prompt, width, height, seed, steps }
Response: JSON with `{ artifacts: [{ base64: "…", finishReason, seed }] }`.
Verified: 2026-04-25, ~5-12s latency, ~250KB JPEG output.
"""

import base64
import time
from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

NVIDIA_DEFAULT_ENDPOINT = (
    "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"
)


@dataclass
class NvidiaImageResponse:
    """Result from NVIDIA flux.1-schnell image generation."""
    image_bytes: bytes
    seed: int
    finish_reason: str
    latency_ms: int
    model: str = "flux.1-schnell"
    provider: str = "nvidia"
    content_type: str = "image/jpeg"


class NvidiaSD3Client:
    """
    NVIDIA flux.1-schnell image generation client. Class name kept for
    historical reasons (it used to wrap stable-diffusion-3-medium).

    Endpoint: https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell
    Auth: Bearer token (Nvidia_stable_api_key).
    Payload: { prompt, width, height, seed, steps }
    Response: { artifacts: [{ base64, finishReason, seed }] }
    """

    # 16:9-friendly resolution map. flux.1-schnell accepts arbitrary
    # multiples of 8 in the 256-1536 range.
    _ASPECT_TO_WH: dict[str, tuple[int, int]] = {
        "16:9":  (1344, 768),
        "9:16":  (768, 1344),
        "4:3":   (1152, 896),
        "3:4":   (896, 1152),
        "1:1":   (1024, 1024),
        "21:9":  (1536, 640),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        self.api_key = api_key or settings.NVIDIA_STABLE_API_KEY
        # Force the working endpoint if the legacy SD3 URL is configured.
        configured = endpoint or settings.NVIDIA_STABLE_ENDPOINT
        if "stable-diffusion" in (configured or "") or not configured:
            configured = NVIDIA_DEFAULT_ENDPOINT
        self.endpoint = configured
        self.name = "nvidia-flux-schnell"
        self.provider = "nvidia"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",  # flux.1-schnell ignores this; kept for API parity
        aspect_ratio: str = "16:9",
        cfg_scale: float = 0.0,     # unused on schnell (turbo distilled)
        steps: int = 4,             # schnell is optimized for 4 steps
        seed: int = 0,
    ) -> NvidiaImageResponse:
        """
        Generate an image via NVIDIA flux.1-schnell.

        Args:
            prompt: Image generation prompt.
            negative_prompt: ignored (schnell does not take negatives).
            aspect_ratio: "16:9", "1:1", "4:3", etc. Mapped to width/height.
            cfg_scale: ignored on schnell.
            steps: number of diffusion steps (4 is optimal).
            seed: 0 = random.

        Returns:
            NvidiaImageResponse with decoded image bytes.

        Raises:
            ConnectionError: If client not configured.
            httpx.HTTPStatusError: On API errors.
        """
        if not self.is_configured:
            raise ConnectionError("Nvidia flux.1-schnell client not configured")

        width, height = self._ASPECT_TO_WH.get(aspect_ratio, (1344, 768))

        payload = {
            "prompt": prompt[:1000],  # schnell rejects very long prompts
            "width": width,
            "height": height,
            "seed": int(seed) if seed else 0,
            "steps": max(1, min(8, int(steps))),
        }

        start = time.monotonic()

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = int((time.monotonic() - start) * 1000)

        # New schnell schema: { artifacts: [{ base64, finishReason, seed }] }
        # Tolerate both the old SD3 schema (`image`) and the new schnell
        # schema so we keep working through API revisions.
        b64_str: Optional[str] = None
        finish_reason = ""
        resp_seed = seed
        artifacts = data.get("artifacts")
        if isinstance(artifacts, list) and artifacts:
            first = artifacts[0] or {}
            b64_str = first.get("base64") or first.get("b64_json")
            finish_reason = first.get("finishReason") or first.get("finish_reason") or ""
            resp_seed = first.get("seed", seed)
        else:
            # Legacy SD3 shape, just in case.
            b64_str = data.get("image") or data.get("b64_json")
            finish_reason = data.get("finish_reason", "")
            resp_seed = data.get("seed", seed)

        if not b64_str:
            raise ValueError("Nvidia flux.1-schnell response missing image payload")

        image_bytes = base64.b64decode(b64_str)

        logger.info(
            "nvidia_flux_schnell_generated",
            size_kb=len(image_bytes) // 1024,
            latency_ms=elapsed,
            seed=resp_seed,
            finish_reason=finish_reason,
            width=width,
            height=height,
        )

        return NvidiaImageResponse(
            image_bytes=image_bytes,
            seed=resp_seed if isinstance(resp_seed, int) else seed,
            finish_reason=finish_reason or "",
            latency_ms=elapsed,
        )

    async def health_check(self) -> bool:
        """Quick health check via minimal generation."""
        try:
            result = await self.generate(
                "A simple blue circle on white background",
                steps=10,
            )
            return len(result.image_bytes) > 1024
        except Exception:
            return False
