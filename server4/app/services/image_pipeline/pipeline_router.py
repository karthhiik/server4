"""
Image Pipeline Router — 6-tier fallback routing with circuit breakers.

Routing chain (verified 2026-04-21, Plan-v4):
    Tier 1: Azure FLUX.1-Kontext-pro    (highest quality, ~17s, paid)
    Tier 2: Nvidia SD3 Medium           (free, good quality, ~5s)
    Tier 3: CF Phoenix                  (free, fast, ~5s)
    Tier 4: CF Lucid                    (free, artistic, ~6s)
    Tier 5: Pollinations                (NEW — free/public, no key, ~3-8s)
    Tier 6: Gradient SVG data-URL       (NEW — always succeeds, synth fallback)

The last two tiers were added to fix the "returns None on exhaustion" bug.
With gradient-SVG as the terminal tier, every slide is guaranteed a visual.

Features:
- Circuit breaker per provider (open after 3 consecutive failures, 60s cooldown)
- Automatic tier fallback on failure
- Provider health tracking with success/failure counters
- Configurable tier preferences per image intent
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx
import structlog

from app.config import settings
from app.services.image_pipeline.azure_flux_client import AzureFluxClient
from app.services.image_pipeline.nvidia_sd3_client import NvidiaSD3Client
from app.services.image_pipeline.huggingface_client import HuggingFaceClient
from app.services.image_pipeline.prompt_builder import (
    AdvancedPromptBuilder,
    ImageIntent,
    PromptContext,
)

logger = structlog.get_logger()


# ── Types ────────────────────────────────────────────────────────

class ImageModelTier(str, Enum):
    """Image generation provider tiers."""
    AZURE_FLUX = "azure-flux"
    NVIDIA_SD3 = "nvidia-sd3"
    CF_PHOENIX = "cf-phoenix"
    CF_LUCID = "cf-lucid"
    POLLINATIONS = "pollinations"
    HUGGINGFACE = "huggingface"  # NEW: HuggingFace free tier fallback
    GRADIENT_SVG = "gradient-svg"


@dataclass
class ImageProviderStatus:
    """Health tracking for a single provider."""
    tier: ImageModelTier
    consecutive_failures: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_failure_time: float = 0.0
    circuit_open: bool = False
    avg_latency_ms: float = 0.0
    _latency_samples: list[float] = field(default_factory=list)

    # Circuit breaker thresholds
    FAILURE_THRESHOLD: int = 3
    COOLDOWN_SECONDS: float = 60.0

    def record_success(self, latency_ms: float) -> None:
        self.consecutive_failures = 0
        self.total_successes += 1
        self.circuit_open = False
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 20:
            self._latency_samples = self._latency_samples[-20:]
        self.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.total_failures += 1
        self.last_failure_time = time.monotonic()
        if self.consecutive_failures >= self.FAILURE_THRESHOLD:
            self.circuit_open = True
            logger.warning(
                "circuit_breaker_opened",
                tier=self.tier.value,
                failures=self.consecutive_failures,
            )

    @property
    def is_available(self) -> bool:
        """Check if provider is available (circuit closed or cooldown expired)."""
        if not self.circuit_open:
            return True
        elapsed = time.monotonic() - self.last_failure_time
        if elapsed >= self.COOLDOWN_SECONDS:
            # Half-open: allow one request
            self.circuit_open = False
            self.consecutive_failures = 0
            logger.info("circuit_breaker_half_open", tier=self.tier.value)
            return True
        return False


@dataclass
class ImageGenerationResult:
    """Result from the image pipeline router."""
    image_bytes: bytes
    provider: str
    model: str
    latency_ms: int
    content_type: str
    prompt_used: str
    tier: ImageModelTier
    fallback_count: int = 0  # How many providers were tried before success


class ImagePipelineRouter:
    """
    Multi-provider image generation with intelligent fallback.

    Routes image requests through a 4-tier provider chain,
    using circuit breakers to skip unhealthy providers and
    fallback automatically on failure.
    """

    def __init__(self):
        # Providers (lazy-initialized)
        self._azure_flux: Optional[AzureFluxClient] = None
        self._nvidia_sd3: Optional[NvidiaSD3Client] = None
        self._huggingface: Optional[HuggingFaceClient] = None

        # Health tracking
        self._status: dict[ImageModelTier, ImageProviderStatus] = {
            tier: ImageProviderStatus(tier=tier)
            for tier in ImageModelTier
        }

        # Prompt builder
        self._prompt_builder = AdvancedPromptBuilder()

        # Default tier ordering
        # HuggingFace added as fallback for free tier (May 2026)
        # Pollinations removed from the production chain (Apr 2026)
        # because the free-tier endpoint stamps a visible watermark
        # on its outputs which then bleeds through into TitleHero /
        # FullBleedImage scrims. Gradient-SVG remains as the
        # zero-failure terminal tier.
        self._default_chain = [
            ImageModelTier.AZURE_FLUX,
            ImageModelTier.NVIDIA_SD3,
            ImageModelTier.CF_PHOENIX,
            ImageModelTier.CF_LUCID,
            ImageModelTier.HUGGINGFACE,  # NEW: Free tier fallback
            ImageModelTier.GRADIENT_SVG,
        ]

    # ── Provider factory (lazy init) ─────────────────────────────

    def _get_azure_flux(self) -> AzureFluxClient:
        if self._azure_flux is None:
            self._azure_flux = AzureFluxClient()
        return self._azure_flux

    def _get_nvidia_sd3(self) -> NvidiaSD3Client:
        if self._nvidia_sd3 is None:
            self._nvidia_sd3 = NvidiaSD3Client()
        return self._nvidia_sd3

    def _get_huggingface(self) -> HuggingFaceClient:
        if self._huggingface is None:
            self._huggingface = HuggingFaceClient()
        return self._huggingface

    # ── Main generation method ───────────────────────────────────

    async def generate(
        self,
        ctx: PromptContext,
        preferred_tier: Optional[ImageModelTier] = None,
        skip_tiers: Optional[list[ImageModelTier]] = None,
    ) -> Optional[ImageGenerationResult]:
        """
        Generate an image with automatic fallback through the tier chain.

        Args:
            ctx: Full presentation slide context for prompt building.
            preferred_tier: Force a specific tier (skips chain ordering).
            skip_tiers: List of tiers to skip (e.g., skip paid tiers).

        Returns:
            ImageGenerationResult on success, None if all tiers fail.
        """
        skip_set = set(skip_tiers or [])
        chain = self._build_chain(preferred_tier, skip_set)

        if not chain:
            logger.error("image_pipeline_no_available_providers")
            return None

        fallback_count = 0
        for tier in chain:
            status = self._status[tier]
            if not status.is_available:
                logger.debug("provider_circuit_open_skipped", tier=tier.value)
                fallback_count += 1
                continue

            try:
                result = await self._generate_with_tier(tier, ctx)
                if result:
                    result.fallback_count = fallback_count
                    status.record_success(result.latency_ms)
                    logger.info(
                        "image_generated",
                        tier=tier.value,
                        latency_ms=result.latency_ms,
                        size_kb=len(result.image_bytes) // 1024,
                        fallback_count=fallback_count,
                    )
                    return result
            except Exception as e:
                status.record_failure()
                logger.warning(
                    "image_tier_failed",
                    tier=tier.value,
                    error=str(e),
                    consecutive_failures=status.consecutive_failures,
                )
                fallback_count += 1

        logger.error(
            "image_pipeline_all_tiers_failed",
            tiers_tried=len(chain),
            context_title=ctx.title,
        )
        return None

    async def generate_with_prompt(
        self,
        prompt: str,
        preferred_tier: Optional[ImageModelTier] = None,
    ) -> Optional[ImageGenerationResult]:
        """
        Generate an image from a raw prompt string (no context building).

        Builds a minimal PromptContext with custom_prompt override.
        """
        ctx = PromptContext(custom_prompt=prompt)
        return await self.generate(ctx, preferred_tier=preferred_tier)

    # ── Batch generation ─────────────────────────────────────────

    async def generate_batch(
        self,
        contexts: list[PromptContext],
        concurrency: int = 3,
    ) -> list[Optional[ImageGenerationResult]]:
        """
        Generate images for multiple slides with bounded concurrency.

        Args:
            contexts: List of slide contexts.
            concurrency: Max parallel generations.

        Returns:
            List of results (None for failures) in same order as contexts.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _gen(ctx: PromptContext) -> Optional[ImageGenerationResult]:
            async with semaphore:
                return await self.generate(ctx)

        tasks = [_gen(ctx) for ctx in contexts]
        return await asyncio.gather(*tasks)

    # ── Provider-specific generation ─────────────────────────────

    async def _generate_with_tier(
        self,
        tier: ImageModelTier,
        ctx: PromptContext,
    ) -> Optional[ImageGenerationResult]:
        """Generate an image using a specific tier."""
        provider_name = tier.value

        if tier == ImageModelTier.AZURE_FLUX:
            return await self._gen_azure_flux(ctx)
        elif tier == ImageModelTier.NVIDIA_SD3:
            return await self._gen_nvidia_sd3(ctx)
        elif tier == ImageModelTier.CF_PHOENIX:
            return await self._gen_cf_phoenix(ctx)
        elif tier == ImageModelTier.CF_LUCID:
            return await self._gen_cf_lucid(ctx)
        elif tier == ImageModelTier.POLLINATIONS:
            return await self._gen_pollinations(ctx)
        elif tier == ImageModelTier.HUGGINGFACE:
            return await self._gen_huggingface(ctx)
        elif tier == ImageModelTier.GRADIENT_SVG:
            return await self._gen_gradient_svg(ctx)

        raise ValueError(f"Unknown tier: {provider_name}")

    async def _gen_azure_flux(self, ctx: PromptContext) -> ImageGenerationResult:
        """Generate via Azure FLUX.1-Kontext-pro."""
        client = self._get_azure_flux()
        if not client.is_configured:
            raise ConnectionError("Azure Flux not configured")

        prompt = self._prompt_builder.build_prompt(ctx, provider="azure-flux")
        result = await client.generate(prompt)

        return ImageGenerationResult(
            image_bytes=result.image_bytes,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
            content_type=result.content_type,
            prompt_used=prompt,
            tier=ImageModelTier.AZURE_FLUX,
        )

    async def _gen_nvidia_sd3(self, ctx: PromptContext) -> ImageGenerationResult:
        """Generate via Nvidia SD3 Medium."""
        client = self._get_nvidia_sd3()
        if not client.is_configured:
            raise ConnectionError("Nvidia SD3 not configured")

        prompt = self._prompt_builder.build_prompt(ctx, provider="nvidia-sd3")
        negative = self._prompt_builder.build_negative_prompt(ctx)

        result = await client.generate(
            prompt=prompt,
            negative_prompt=negative,
            aspect_ratio="16:9",
        )

        return ImageGenerationResult(
            image_bytes=result.image_bytes,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
            content_type=result.content_type,
            prompt_used=prompt,
            tier=ImageModelTier.NVIDIA_SD3,
        )

    async def _gen_cf_phoenix(self, ctx: PromptContext) -> ImageGenerationResult:
        """Generate via Cloudflare Phoenix worker."""
        from app.services.llm.cloudflare_client import create_cf_phoenix_client

        client = create_cf_phoenix_client()
        prompt = self._prompt_builder.build_prompt(ctx, provider="cf-phoenix")

        start = time.monotonic()
        image_bytes = await client.generate_image(prompt)
        elapsed = int((time.monotonic() - start) * 1000)

        return ImageGenerationResult(
            image_bytes=image_bytes,
            provider="cloudflare",
            model="cf-phoenix",
            latency_ms=elapsed,
            content_type="image/jpeg",
            prompt_used=prompt,
            tier=ImageModelTier.CF_PHOENIX,
        )

    async def _gen_cf_lucid(self, ctx: PromptContext) -> ImageGenerationResult:
        """Generate via Cloudflare Lucid worker."""
        from app.services.llm.cloudflare_client import create_cf_lucid_client

        client = create_cf_lucid_client()
        prompt = self._prompt_builder.build_prompt(ctx, provider="cf-lucid")

        start = time.monotonic()
        image_bytes = await client.generate_image(prompt)
        elapsed = int((time.monotonic() - start) * 1000)

        return ImageGenerationResult(
            image_bytes=image_bytes,
            provider="cloudflare",
            model="cf-lucid",
            latency_ms=elapsed,
            content_type="image/jpeg",
            prompt_used=prompt,
            tier=ImageModelTier.CF_LUCID,
        )

    async def _gen_huggingface(self, ctx: PromptContext) -> ImageGenerationResult:
        """Generate via HuggingFace Inference API (free tier fallback)."""
        client = self._get_huggingface()
        prompt = self._prompt_builder.build_prompt(ctx, provider="huggingface")

        result = await client.generate_with_retry(prompt)

        if not result:
            raise ConnectionError("HuggingFace generation failed")

        return ImageGenerationResult(
            image_bytes=result.image_bytes,
            provider="huggingface",
            model=result.model,
            latency_ms=result.latency_ms,
            content_type=result.content_type,
            prompt_used=prompt,
            tier=ImageModelTier.HUGGINGFACE,
        )

    async def _gen_pollinations(self, ctx: PromptContext) -> ImageGenerationResult:
        """Generate via Pollinations.ai public endpoint.

        No API key required. Verified at
        https://image.pollinations.ai/prompt/{url-encoded prompt}?width=W&height=H&nologo=true
        Returns raw image bytes (image/jpeg).
        """
        import urllib.parse

        prompt = self._prompt_builder.build_prompt(ctx, provider="pollinations")
        encoded = urllib.parse.quote(prompt[:1500], safe="")
        # 16:9 default — good for slide bg/hero
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1024&height=576&nologo=true&enhance=true"
        )

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            image_bytes = resp.content
        elapsed = int((time.monotonic() - start) * 1000)

        if not image_bytes or len(image_bytes) < 2048:
            raise RuntimeError(
                f"Pollinations returned undersized payload ({len(image_bytes)}B)"
            )

        content_type = resp.headers.get("content-type", "image/jpeg")
        return ImageGenerationResult(
            image_bytes=image_bytes,
            provider="pollinations",
            model="pollinations-public",
            latency_ms=elapsed,
            content_type=content_type,
            prompt_used=prompt,
            tier=ImageModelTier.POLLINATIONS,
        )

    async def _gen_gradient_svg(self, ctx: PromptContext) -> ImageGenerationResult:
        """Synthesize a 3-stop gradient SVG from the slide palette.

        Zero-failure terminal tier — always succeeds so every slide gets a
        visual. Uses PromptContext.primary_color / accent_color, else
        deterministic hash-derived colors so the same prompt yields the
        same background.
        """
        primary = (getattr(ctx, "primary_color", "") or "").strip()
        accent = (getattr(ctx, "accent_color", "") or "").strip()

        def _valid_hex(c: str) -> bool:
            return bool(c) and c.startswith("#") and len(c) in (4, 7)

        palette: list[str] = [c for c in (primary, accent) if _valid_hex(c)]

        if len(palette) < 2:
            # Hash-derive from title + theme_id for determinism
            seed_src = (
                f"{getattr(ctx, 'title', '')}|{getattr(ctx, 'theme_id', '')}"
                f"|{getattr(ctx, 'slide_index', 0)}"
            ) or "slide"
            h = hashlib.md5(seed_src.encode()).hexdigest()
            hue_a = int(h[0:2], 16)
            hue_b = int(h[2:4], 16)
            palette = [
                f"#{hue_a:02x}{(hue_a * 2) & 0xFF:02x}{(hue_a * 3) & 0xFF:02x}",
                f"#{hue_b:02x}{(hue_b * 2) & 0xFF:02x}{(hue_b * 3) & 0xFF:02x}",
            ]

        c1 = palette[0]
        c2 = palette[1] if len(palette) > 1 else c1
        # Third stop = primary tinted toward accent for smooth transition
        c3 = palette[1] if len(palette) > 1 else c1

        svg = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="1024" height="576" viewBox="0 0 1024 576">'
            '<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">'
            f'<stop offset="0%" stop-color="{c1}"/>'
            f'<stop offset="50%" stop-color="{c2}"/>'
            f'<stop offset="100%" stop-color="{c3}"/>'
            '</linearGradient></defs>'
            '<rect width="1024" height="576" fill="url(#g)"/>'
            '</svg>'
        )
        image_bytes = svg.encode("utf-8")

        return ImageGenerationResult(
            image_bytes=image_bytes,
            provider="synthetic",
            model="gradient-svg",
            latency_ms=1,
            content_type="image/svg+xml",
            prompt_used=f"synthetic_gradient({c1},{c2},{c3})",
            tier=ImageModelTier.GRADIENT_SVG,
        )

    # ── Chain management ─────────────────────────────────────────

    def _build_chain(
        self,
        preferred: Optional[ImageModelTier],
        skip: set[ImageModelTier],
    ) -> list[ImageModelTier]:
        """Build the provider chain, respecting preferences and skips.

        Pollinations is always skipped at chain-build time regardless of
        ``ALLOW_POLLINATIONS_IMAGES``. The free Pollinations endpoint stamps
        a visible watermark that bleeds through TitleHero / FullBleedImage
        scrims, so it must never reach a slide. The legacy env flag and
        ``_gen_pollinations`` method are retained only for backward
        compatibility with existing tests and explicit tier requests on the
        legacy ``/api/images/generate`` endpoint, which already raises 400
        when Pollinations is selected with the flag off.
        """
        skip = set(skip)
        skip.add(ImageModelTier.POLLINATIONS)
        if settings.ALLOW_POLLINATIONS_IMAGES:
            # Operators occasionally re-enable the flag in dev configs; warn
            # so the silent skip is observable in logs.
            logger.warning(
                "pollinations_flag_ignored_in_chain",
                reason="watermarked_provider_banned_in_production",
            )
        if preferred and preferred not in skip:
            # Put preferred first, then rest
            chain = [preferred]
            for tier in self._default_chain:
                if tier != preferred and tier not in skip:
                    chain.append(tier)
            return chain

        return [t for t in self._default_chain if t not in skip]

    # ── Status / health ──────────────────────────────────────────

    def get_provider_status(self) -> dict[str, dict]:
        """Get health status of all providers."""
        result = {}
        for tier, status in self._status.items():
            configured = False
            if tier == ImageModelTier.AZURE_FLUX:
                configured = self._get_azure_flux().is_configured
            elif tier == ImageModelTier.NVIDIA_SD3:
                configured = self._get_nvidia_sd3().is_configured
            elif tier in (ImageModelTier.CF_PHOENIX, ImageModelTier.CF_LUCID):
                from app.config import settings
                if tier == ImageModelTier.CF_PHOENIX:
                    configured = bool(settings.CF_WORKER_PHOENIX_URL and settings.CF_WORKER_PHOENIX_TOKEN)
                else:
                    configured = bool(settings.CF_WORKER_LUCID_URL and settings.CF_WORKER_LUCID_TOKEN)
            elif tier == ImageModelTier.POLLINATIONS:
                configured = bool(settings.ALLOW_POLLINATIONS_IMAGES)
            elif tier == ImageModelTier.GRADIENT_SVG:
                configured = True  # synthetic, always available

            result[tier.value] = {
                "configured": configured,
                "available": status.is_available,
                "circuit_open": status.circuit_open,
                "consecutive_failures": status.consecutive_failures,
                "total_successes": status.total_successes,
                "total_failures": status.total_failures,
                "avg_latency_ms": round(status.avg_latency_ms, 1),
            }
        return result

    async def health_check_all(self) -> dict[str, bool]:
        """Run health checks on all configured providers."""
        results = {}

        # Azure Flux
        try:
            client = self._get_azure_flux()
            results["azure-flux"] = client.is_configured and await client.health_check()
        except Exception:
            results["azure-flux"] = False

        # Nvidia SD3
        try:
            client = self._get_nvidia_sd3()
            results["nvidia-sd3"] = client.is_configured and await client.health_check()
        except Exception:
            results["nvidia-sd3"] = False

        # CF Phoenix
        try:
            from app.services.llm.cloudflare_client import create_cf_phoenix_client
            client = create_cf_phoenix_client()
            image = await client.generate_image("Test blue circle")
            results["cf-phoenix"] = len(image) > 1024
        except Exception:
            results["cf-phoenix"] = False

        # CF Lucid
        try:
            from app.services.llm.cloudflare_client import create_cf_lucid_client
            client = create_cf_lucid_client()
            image = await client.generate_image("Test blue circle")
            results["cf-lucid"] = len(image) > 1024
        except Exception:
            results["cf-lucid"] = False

        return results
