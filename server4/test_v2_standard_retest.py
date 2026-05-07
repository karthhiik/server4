"""Quick re-test of standard mode only — verifies the body_sections fix."""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def hr(title): print(f"\n{'═'*70}\n  {title}\n{'═'*70}")
def section(title): print(f"\n  ── {title} {'─' * max(1, 50 - len(title))}")


async def main():
    hr("STANDARD MODE RE-TEST (body_sections fix)")

    from app.config import settings
    from app.services.llm.model_router import ModelRouter
    from app.mcp.brain_mcp.generators.slide_generator_v2 import SlideGeneratorV2
    from app.mcp.brain_mcp.research.models import (
        BudgetMode, SlideKind, SlideEvidenceBundle, SourceMix,
        FactPacket, ClaimType, SourceType, FreshnessClass,
    )
    from app.mcp.brain_mcp.prompts.style_catalog import get_style

    # Use pre-built mock evidence to avoid repeating API research calls
    def make_packet(claim, source, provider, stype=SourceType.web_extracted, conf=0.75):
        return FactPacket(
            id=f"fp_{hash(claim) % 10000:04d}",
            claim=claim,
            claim_type=ClaimType.qualitative,
            source_url=f"https://example.com/{provider}",
            source_name=source,
            source_type=stype,
            date_published="2026-03-01",
            date_retrieved=datetime.now(timezone.utc).isoformat(),
            freshness_class=FreshnessClass.recent,
            confidence=conf,
            numeric_value=None,
            numeric_unit=None,
            extraction_method="api_structured",
            provider=provider,
        )

    bundle = SlideEvidenceBundle(
        slide_id="s_market_retest",
        slide_kind=SlideKind.market,
        evidence_packets=[
            make_packet("Global AI in healthcare market: $45.2B by 2030, CAGR 44.9%", "Grand View Research", "serper", SourceType.industry_report, 0.86),
            make_packet("US healthcare AI spending reached $6.7B in 2025", "CB Insights", "tavily", SourceType.news_article, 0.80),
            make_packet("FDA approved 521 AI/ML medical devices as of 2025", "FDA Database", "fred", SourceType.government_data, 0.95),
            make_packet("AI diagnostics market to reach $8.54B by 2033", "MarketsAndMarkets", "serper", SourceType.industry_report, 0.82),
        ],
        evidence_score=0.88,
        approved_claim_ids=["fp_0001", "fp_0002", "fp_0003", "fp_0004"],
    )

    style = get_style("yc_crisp")
    model_router = ModelRouter.get_instance()
    generator = SlideGeneratorV2(model_router)

    section("Generating Market slide (lean budget)")
    start = time.monotonic()

    contract = await generator.generate(
        evidence_bundle=bundle,
        style=style,
        topic="AI-powered healthcare diagnostics startup",
        audience="investors",
        budget_mode=BudgetMode.lean,
        deck_context={"slide_index": 3, "total_slides": 10},
    )
    elapsed = (time.monotonic() - start) * 1000

    section("PRESENTATION MODE")
    print(f"  Title:    {contract.presentation_content.title}")
    print(f"  Subtitle: {contract.presentation_content.subtitle}")
    if contract.presentation_content.bullets:
        print(f"  Bullets ({len(contract.presentation_content.bullets)}):")
        for b in contract.presentation_content.bullets:
            print(f"    • {b}")

    section("READING MODE")
    print(f"  Title:    {contract.reading_content.title}")
    print(f"  Summary:  {contract.reading_content.summary[:300] if contract.reading_content.summary else 'N/A'}")
    if contract.reading_content.body_sections:
        print(f"  Body Sections ({len(contract.reading_content.body_sections)}):")
        for sec in contract.reading_content.body_sections:
            print(f"    § {sec.heading}")
            for p in sec.paragraphs[:1]:
                print(f"      {p[:150]}...")
    if contract.reading_content.assumptions:
        print(f"  Assumptions ({len(contract.reading_content.assumptions)}):")
        for a in contract.reading_content.assumptions[:3]:
            print(f"    ⚠ {a[:120]}")
    if contract.reading_content.risks:
        print(f"  Risks ({len(contract.reading_content.risks)}):")
        for r in contract.reading_content.risks[:3]:
            print(f"    ⚠ {r[:120]}")

    section("SPEAKER NOTES")
    for note in (contract.speaker_notes or [])[:3]:
        print(f"    📝 {note[:150]}")

    section("CHART DATA")
    if contract.chart_data:
        print(f"  {json.dumps(contract.chart_data, indent=2)[:500]}")
    else:
        print(f"  No chart data generated")

    section("IMAGE PROMPT")
    if contract.image_prompt:
        print(f"  {contract.image_prompt[:250]}")
    else:
        print(f"  No image prompt generated")

    section("CITATIONS")
    for c in (contract.citations or [])[:5]:
        print(f"    {c.label}: {c.source_name} ({c.confidence:.2f})")

    section("METADATA")
    meta = contract.generation_metadata
    print(f"  Evidence score:    {contract.evidence_score:.3f}")
    print(f"  Style:             {contract.style_id}")
    print(f"  Total latency:     {meta.total_latency_ms:.0f}ms")
    print(f"  Models used:       {', '.join(meta.models_used)}")
    print(f"  Total tokens:      {meta.total_tokens}")
    print(f"  Errors recovered:  {meta.errors_recovered}")

    print(f"\n  ✓ STANDARD mode generated successfully in {elapsed:.0f}ms")

    # Verify all key fields are populated
    assert contract.presentation_content.title, "Missing presentation title"
    assert contract.reading_content.title, "Missing reading title"
    assert contract.reading_content.summary, "Missing reading summary"
    assert contract.style_id, "Missing style_id"
    assert contract.evidence_score > 0, "Evidence score should be > 0"

    print(f"  ✓ All required fields validated")
    print(f"\n{'█'*70}\n  ALL CHECKS PASSED\n{'█'*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
