"""
Phase 8 — Image Generation Pipeline.

4-tier multi-provider image routing with fallback chain,
advanced prompt engineering, image processing (resize/optimize/format),
and asset management with Redis caching + Azure Blob CDN.

Architecture (verified 2026-04-05):
    Tier 1: Azure FLUX.1-Kontext-pro (highest quality, ~17s, paid)
    Tier 2: Nvidia SD3 Medium (free, good quality, ~5s)
    Tier 3: CF Phoenix (free, fast, ~5s)
    Tier 4: CF Lucid (free, artistic, ~6s)

Components:
    - AzureFluxClient: Azure FLUX.1-Kontext-pro image gen
    - NvidiaSD3Client: Nvidia Stable Diffusion 3 Medium
    - ImagePipelineRouter: 4-tier routing with circuit breakers
    - AdvancedPromptBuilder: DSL-aware, theme-aware prompt engineering
    - ImageProcessor: Resize, crop, optimize, format conversion
    - ImageAssetManager: Redis cache + Blob CDN + batch ops
"""

from app.services.image_pipeline.azure_flux_client import (
    AzureFluxClient,
    FluxImageResponse,
)
from app.services.image_pipeline.nvidia_sd3_client import (
    NvidiaSD3Client,
    NvidiaImageResponse,
)
from app.services.image_pipeline.pipeline_router import (
    ImageModelTier,
    ImagePipelineRouter,
    ImageGenerationResult,
    ImageProviderStatus,
)
from app.services.image_pipeline.prompt_builder import (
    AdvancedPromptBuilder,
    ImageIntent,
    PromptContext,
)
from app.services.image_pipeline.image_processor import (
    ImageProcessor,
    ImageFormat,
    ProcessedImage,
    ResizeMode,
)
from app.services.image_pipeline.asset_manager import (
    ImageAssetManager,
    AssetRecord,
    AssetStats,
)

__all__ = [
    # Azure Flux
    "AzureFluxClient",
    "FluxImageResponse",
    # Nvidia SD3
    "NvidiaSD3Client",
    "NvidiaImageResponse",
    # Pipeline Router
    "ImageModelTier",
    "ImagePipelineRouter",
    "ImageGenerationResult",
    "ImageProviderStatus",
    # Prompt Builder
    "AdvancedPromptBuilder",
    "ImageIntent",
    "PromptContext",
    # Image Processor
    "ImageProcessor",
    "ImageFormat",
    "ProcessedImage",
    "ResizeMode",
    # Asset Manager
    "ImageAssetManager",
    "AssetRecord",
    "AssetStats",
]
