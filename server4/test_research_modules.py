"""Quick verification test for the 3 new research pipeline modules."""

import asyncio
from app.mcp.brain_mcp.research.models import (
    SlideKind, BudgetMode, FactPacket, ClaimType, SourceType, FreshnessClass,
    MissingDataItem, SlideEvidenceBundle, SourceMix,
)
from app.mcp.brain_mcp.research.query_planner import QueryPlanner
from app.mcp.brain_mcp.research.evidence_assembler import EvidenceAssembler
from app.mcp.brain_mcp.research.research_router import ResearchRouter, _BUDGET_LIMITS


async def test_query_planner():
    planner = QueryPlanner(model_router=None)
    for kind in SlideKind:
        queries = await planner.plan_queries(
            topic="AI SaaS Platform",
            description="AI productivity platform",
            slide_kind=kind,
            sector="SaaS",
        )
        assert len(queries) >= 1, f"No queries for {kind.value}"
        for q in queries:
            assert "{topic}" not in q, f"Unresolved placeholder in: {q}"
            assert "{sector_q}" not in q, f"Unresolved placeholder in: {q}"
        print(f"  {kind.value}: {len(queries)} queries")

    kw = planner._provider_query_format("What is the market size for AI SaaS?", "serper")
    nl = planner._provider_query_format("AI SaaS market size", "tavily")
    assert nl.endswith("?"), f"Expected ?, got: {nl}"
    print("  Provider formatting OK")
    print("QueryPlanner: ALL PASSED")


def test_evidence_assembler():
    assembler = EvidenceAssembler()
    packets = [
        FactPacket(
            id="fp_001",
            claim="Global SaaS market is 200B with 18 pct CAGR",
            claim_type=ClaimType.numeric,
            source_url=None,
            source_name="Gartner",
            source_type=SourceType.industry_report,
            date_published="2026-01-15",
            date_retrieved="2026-04-04",
            freshness_class=FreshnessClass.current,
            confidence=0.85,
            numeric_value=200.0,
            numeric_unit="USD billion",
            extraction_method="llm_extracted",
            provider="serper",
        ),
        FactPacket(
            id="fp_002",
            claim="TAM for AI productivity tools is 45B",
            claim_type=ClaimType.numeric,
            source_url=None,
            source_name="IDC",
            source_type=SourceType.industry_report,
            date_published="2025-12-01",
            date_retrieved="2026-04-04",
            freshness_class=FreshnessClass.dated,
            confidence=0.80,
            numeric_value=45.0,
            numeric_unit="USD billion",
            extraction_method="api_structured",
            provider="tavily",
        ),
        FactPacket(
            id="fp_003",
            claim="SaaS market growing at 18 pct CAGR trend up",
            claim_type=ClaimType.trend,
            source_url=None,
            source_name="Statista",
            source_type=SourceType.web_extracted,
            date_published=None,
            date_retrieved="2026-04-04",
            freshness_class=FreshnessClass.undated,
            confidence=0.65,
            numeric_value=18.0,
            numeric_unit="pct",
            extraction_method="scraped",
            provider="serper",
        ),
        FactPacket(
            id="fp_004",
            claim="Reddit users praise Notion AI for productivity",
            claim_type=ClaimType.testimonial,
            source_url="https://reddit.com/r/saas",
            source_name="Reddit",
            source_type=SourceType.social_signal,
            date_published="2026-03-28",
            date_retrieved="2026-04-04",
            freshness_class=FreshnessClass.recent,
            confidence=0.50,
            numeric_value=None,
            numeric_unit=None,
            extraction_method="scraped",
            provider="reddit",
        ),
    ]

    bundle = assembler.assemble("slide_market_01", SlideKind.market, packets)
    assert isinstance(bundle, SlideEvidenceBundle)
    assert bundle.slide_id == "slide_market_01"
    assert bundle.slide_kind == SlideKind.market
    assert len(bundle.evidence_packets) >= 1
    assert 0.0 <= bundle.evidence_score <= 1.0
    assert 0.0 <= bundle.cross_validation_score <= 1.0
    assert isinstance(bundle.source_mix, SourceMix)
    assert isinstance(bundle.missing_data, list)

    print(f"  Bundle: {len(bundle.evidence_packets)} packets, "
          f"score={bundle.evidence_score:.2f}, "
          f"cross_val={bundle.cross_validation_score:.2f}, "
          f"missing={len(bundle.missing_data)}")
    print(f"  Source mix: det={len(bundle.source_mix.deterministic)}, "
          f"llm={len(bundle.source_mix.llm_extracted)}, "
          f"social={len(bundle.source_mix.social)}, "
          f"academic={len(bundle.source_mix.academic)}")
    for m in bundle.missing_data:
        print(f"  Missing [{m.severity}]: {m.what}")

    for kind in [SlideKind.market, SlideKind.problem, SlideKind.competition,
                 SlideKind.financial, SlideKind.traction]:
        b = assembler.assemble("test", kind, [])
        assert len(b.missing_data) >= 2, f"{kind.value} should have >= 2 missing items, got {len(b.missing_data)}"
        print(f"  {kind.value} empty: {len(b.missing_data)} missing items")

    print("EvidenceAssembler: ALL PASSED")


def test_budget():
    for mode in BudgetMode:
        limits = _BUDGET_LIMITS[mode]
        assert "max_providers_per_evidence_type" in limits
        assert "max_parallel" in limits
        assert "max_depth" in limits
        prov = limits["max_providers_per_evidence_type"]
        par = limits["max_parallel"]
        depth = limits["max_depth"]
        print(f"  {mode.value}: providers={prov}, parallel={par}, depth={depth}")
    print("BudgetLimits: ALL PASSED")


def test_serialisation():
    """Verify bundles serialise to dict and back."""
    assembler = EvidenceAssembler()
    fp = FactPacket(
        id="fp_ser_001",
        claim="Test claim for serialisation",
        claim_type=ClaimType.qualitative,
        source_url=None,
        source_name="test",
        source_type=SourceType.web_extracted,
        date_published=None,
        date_retrieved="2026-04-04",
        freshness_class=FreshnessClass.undated,
        confidence=0.70,
        numeric_value=None,
        numeric_unit=None,
        extraction_method="scraped",
        provider="serper",
    )
    bundle = assembler.assemble("slide_test", SlideKind.problem, [fp])
    d = bundle.to_dict()
    restored = SlideEvidenceBundle.from_dict(d)
    assert restored.slide_id == bundle.slide_id
    assert restored.evidence_score == bundle.evidence_score
    assert len(restored.evidence_packets) == len(bundle.evidence_packets)
    print("Serialisation: PASSED")


if __name__ == "__main__":
    asyncio.run(test_query_planner())
    test_evidence_assembler()
    test_budget()
    test_serialisation()
    print()
    print("=" * 50)
    print(" ALL 3 MODULES VERIFIED SUCCESSFULLY ")
    print("=" * 50)
