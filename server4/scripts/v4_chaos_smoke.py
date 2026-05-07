from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.image_pipeline.pipeline_router import ImageModelTier, ImagePipelineRouter
from app.services.image_pipeline.prompt_builder import PromptContext
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.provenance_guard import apply_provenance_guard
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.schema_guard import SchemaValidationError, validate_writer_output


def _research_without_evidence() -> ResearchPacket:
    return ResearchPacket(
        query="chaos smoke",
        industry=None,
        company_name=None,
        citations=[],
        news_citations=[],
        financial_data={},
        social_signals={},
        duration_ms=0,
    )


async def main() -> int:
    try:
        validate_writer_output('{"headline":"","bullets":[]}', slide_index=0)
        raise AssertionError("invalid writer output was accepted")
    except SchemaValidationError:
        pass

    slide = GeneratedSlide(
        index=1,
        intent="traction",
        layout="stat-hero",
        headline="Revenue reached $77M",
        stat_blocks=[{"value": "$77M", "label": "unverified revenue"}],
    )
    issues = apply_provenance_guard([slide], research=_research_without_evidence(), user_query="deck", structured_context={})
    if not issues or slide.stat_blocks or not slide.requires_user_input:
        raise AssertionError("unsupported numeric claim was not converted to unresolved input")

    router = ImagePipelineRouter()
    result = await router.generate(
        PromptContext(title="Chaos smoke no external provider", slide_index=2),
        skip_tiers=[
            ImageModelTier.AZURE_FLUX,
            ImageModelTier.NVIDIA_SD3,
            ImageModelTier.CF_PHOENIX,
            ImageModelTier.CF_LUCID,
            ImageModelTier.POLLINATIONS,
            ImageModelTier.GRADIENT_SVG,
        ],
    )
    if result is not None:
        raise AssertionError("image router fabricated a result when every tier was skipped")

    print("v4 chaos smoke passed: schema, provenance, and image exhaustion stayed honest")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
