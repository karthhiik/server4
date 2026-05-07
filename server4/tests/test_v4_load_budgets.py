from __future__ import annotations

import time

import pytest

from app.services.image_pipeline.pipeline_router import ImageModelTier, ImagePipelineRouter
from app.services.image_pipeline.prompt_builder import PromptContext
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.slide_compiler import compile_slides


def test_backend_compile_budget_is_deterministic_and_no_llm() -> None:
    slides = [
        GeneratedSlide(
            index=index,
            intent="solution" if index % 2 else "problem",
            layout="two-column",
            headline=f"Verified workflow slide {index}",
            bullets=["Evidence stays attached", "No fake customer data is invented"],
        )
        for index in range(8)
    ]

    start = time.perf_counter()
    compiled = compile_slides(slides=slides, deck_title="Load Budget Deck")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(compiled) == 8
    assert elapsed_ms < 1500.0
    assert all(slide["artifacts"]["kit_jsx"]["props_json"] for slide in compiled)


@pytest.mark.asyncio
async def test_image_pipeline_terminal_gradient_fallback_is_fast_and_honest() -> None:
    router = ImagePipelineRouter()
    result = await router.generate(
        PromptContext(title="Verified fallback visual", slide_index=1, primary_color="#2458ff", accent_color="#14b8a6"),
        preferred_tier=ImageModelTier.GRADIENT_SVG,
        skip_tiers=[
            ImageModelTier.AZURE_FLUX,
            ImageModelTier.NVIDIA_SD3,
            ImageModelTier.CF_PHOENIX,
            ImageModelTier.CF_LUCID,
            ImageModelTier.POLLINATIONS,
        ],
    )

    assert result is not None
    assert result.tier == ImageModelTier.GRADIENT_SVG
    assert result.provider == "synthetic"
    assert result.latency_ms <= 10
    assert b"<svg" in result.image_bytes
