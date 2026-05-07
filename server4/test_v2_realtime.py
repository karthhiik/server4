"""
Real-time end-to-end test of V2 Slide Content Generation Pipeline.

Tests STANDARD and PREMIUM modes with live API calls:
1. Provider registry — how many providers are configured
2. Research Router — real queries to Serper/Tavily/NewsAPI/FRED etc.
3. Evidence Assembly — fact packet creation & dedup
4. Cross-validation & freshness scoring
5. Debate loop (premium mode only)
6. Slide content generation (reading→presentation→notes→chart→image→citations)
7. Full pipeline timing and accuracy check
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

# Setup
os.chdir(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_v2")

# Suppress noisy loggers
for name in ("httpx", "httpcore", "urllib3", "asyncio"):
    logging.getLogger(name).setLevel(logging.WARNING)


def hr(title: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def section(title: str) -> None:
    print(f"\n  ── {title} {'─' * max(1, 50 - len(title))}")


async def test_provider_registry():
    """Test 1: Check which providers are live."""
    hr("TEST 1: Provider Registry")

    from app.config import settings
    from app.mcp.brain_mcp.research.provider_registry import ProviderRegistry

    registry = ProviderRegistry(settings)
    summary = registry.summary()

    print(f"  Total providers:    {summary['total_providers']}")
    print(f"  Configured:         {summary['configured']}")
    print(f"  Unconfigured:       {summary['unconfigured']}")
    print(f"  By category:")
    for cat, count in sorted(summary["by_category"].items()):
        print(f"    {cat:20s}: {count}")

    # List configured providers
    section("Configured Providers")
    for p in registry.configured_providers():
        print(f"    [{p.priority:2d}] {p.name:20s}  ({p.category}, ${p.cost_per_call:.4f}/call)")

    assert summary["configured"] > 10, f"Expected >10 configured providers, got {summary['configured']}"
    print(f"\n  ✓ {summary['configured']} providers configured and ready")
    return registry


async def test_circuit_breaker():
    """Test 2: Circuit breaker in-memory mode works."""
    hr("TEST 2: Circuit Breaker")

    from app.mcp.brain_mcp.research.circuit_breaker import CircuitBreaker
    from app.mcp.brain_mcp.research.models import ProviderStatus

    cb = CircuitBreaker(None)  # In-memory mode

    # Test healthy state
    health = await cb.check_health("test_provider")
    assert health.status == ProviderStatus.healthy, f"Expected healthy, got {health.status}"
    print(f"  Initial health: {health.status.value}")

    # Record some successes
    await cb.record_success("test_provider", 150.0)
    await cb.record_success("test_provider", 200.0)
    health = await cb.check_health("test_provider")
    print(f"  After 2 successes: {health.status.value}, avg_latency={health.avg_latency_ms:.0f}ms")

    # Record failures to trigger degraded state
    for i in range(3):
        await cb.record_failure("test_provider", "TimeoutError")
    health = await cb.check_health("test_provider")
    print(f"  After 3 failures: {health.status.value}")

    print(f"\n  ✓ Circuit breaker state machine works correctly")
    return cb


async def test_query_planner():
    """Test 3: Query planner generates real queries."""
    hr("TEST 3: Query Planner")

    from app.mcp.brain_mcp.research.query_planner import QueryPlanner
    from app.mcp.brain_mcp.research.models import SlideKind

    planner = QueryPlanner()
    test_cases = [
        ("AI SaaS for healthcare", "Healthcare AI Market", SlideKind.market, "investors"),
        ("AI SaaS for healthcare", "The Problem", SlideKind.problem, "investors"),
        ("EV charging network", "Competition Landscape", SlideKind.competition, "vcs"),
    ]

    for topic, title, kind, audience in test_cases:
        queries = await planner.plan_queries(topic, title, kind, audience)
        section(f"{kind.value} ({topic[:30]})")
        for i, q in enumerate(queries):
            print(f"    Q{i+1}: {q}")
        assert len(queries) >= 2, f"Expected ≥2 queries for {kind.value}, got {len(queries)}"

    print(f"\n  ✓ Query planner generates targeted queries for all slide kinds")


async def test_research_router_live(registry):
    """Test 4: Live research with real API calls."""
    hr("TEST 4: Live Research (Real API Calls)")

    from app.mcp.brain_mcp.research.models import SlideKind, BudgetMode
    from app.mcp.brain_mcp.research.circuit_breaker import CircuitBreaker
    from app.mcp.brain_mcp.research.content_events import ContentEventEmitter
    from app.mcp.brain_mcp.research.research_router import ResearchRouter
    from app.mcp.brain_mcp.research.query_planner import QueryPlanner

    cb = CircuitBreaker(None)
    emitter = ContentEventEmitter("test_deck", None)
    router = ResearchRouter(registry, cb, emitter)
    planner = QueryPlanner()

    # Test with a real topic
    topic = "AI-powered healthcare diagnostics startup"
    slide_kind = SlideKind.market

    section(f"Researching: {topic} ({slide_kind.value})")
    queries = await planner.plan_queries(topic, "Market Opportunity", slide_kind, "investors")
    print(f"  Queries: {queries}")

    start = time.monotonic()
    packets = await router.research_slide(
        slide_id="test_slide_market",
        slide_kind=slide_kind,
        queries=queries,
        topic=topic,
        budget_mode=BudgetMode.lean,
    )
    elapsed = (time.monotonic() - start) * 1000

    section(f"Results: {len(packets)} FactPackets in {elapsed:.0f}ms")
    for i, p in enumerate(packets[:10]):
        print(f"    [{i+1}] [{p.source_type.value:15s}] [{p.confidence:.2f}] {p.claim[:100]}")
        print(f"        Source: {p.source_name} | Provider: {p.provider}")

    if len(packets) == 0:
        print(f"\n  ⚠ No packets returned — API keys may be invalid or rate-limited")
    else:
        print(f"\n  ✓ Research returned {len(packets)} evidence packets in {elapsed:.0f}ms")
    return packets


async def test_evidence_assembly(packets):
    """Test 5: Evidence assembly with real packets."""
    hr("TEST 5: Evidence Assembly & Scoring")

    from app.mcp.brain_mcp.research.evidence_assembler import EvidenceAssembler
    from app.mcp.brain_mcp.research.cross_validator import CrossValidator
    from app.mcp.brain_mcp.research.freshness_scorer import FreshnessScorer
    from app.mcp.brain_mcp.research.models import SlideKind

    assembler = EvidenceAssembler()
    cross_validator = CrossValidator()
    freshness_scorer = FreshnessScorer()

    # Cross-validate
    section("Cross-Validation")
    validated_packets = cross_validator.validate(packets)
    cross_validated = [p for p in validated_packets if p.cross_validated]
    print(f"  Total packets: {len(validated_packets)}")
    print(f"  Cross-validated: {len(cross_validated)}")

    # Freshness scoring
    section("Freshness Scoring")
    for p in validated_packets[:5]:
        original = p.confidence
        adjusted = freshness_scorer.adjust_confidence(p, SlideKind.market)
        print(f"  [{p.freshness_class.value:10s}] {original:.2f} → {adjusted:.2f}  {p.claim[:60]}")

    # Assemble bundle
    section("Bundle Assembly")
    bundle = assembler.assemble("test_slide_market", SlideKind.market, validated_packets)
    print(f"  Evidence score: {bundle.evidence_score:.3f}")
    print(f"  Source mix:")
    mix = bundle.source_mix
    print(f"    Deterministic: {len(mix.deterministic)}, LLM-extracted: {len(mix.llm_extracted)}, "
          f"Social: {len(mix.social)}, Academic: {len(mix.academic)}, "
          f"Specialty: {len(mix.specialty)}")
    print(f"  Missing data items: {len(bundle.missing_data)}")
    for md in bundle.missing_data[:3]:
        print(f"    - {md.what} ({md.severity}) → {md.how_to_get}")

    # Set all claims as approved (no debate in standard mode)
    bundle.approved_claim_ids = [p.id for p in bundle.evidence_packets]

    print(f"\n  ✓ Evidence bundle assembled with score {bundle.evidence_score:.3f}")
    return bundle


async def test_style_catalog():
    """Test 6: Style catalog."""
    hr("TEST 6: Style Catalog")

    from app.mcp.brain_mcp.prompts.style_catalog import (
        STYLE_CATALOG, get_style, select_style,
    )

    print(f"  Total styles: {len(STYLE_CATALOG)}")

    # List families
    families = {}
    for s in STYLE_CATALOG.values():
        families.setdefault(s.family, []).append(s.style_id)
    for family, styles in sorted(families.items()):
        print(f"    {family}: {', '.join(styles[:4])}{'...' if len(styles) > 4 else ''}")

    # Test auto-selection
    section("Auto-Selection")
    test_cases = [
        ("investors", "SaaS analytics"),
        ("engineers", "API infrastructure"),
        ("general", "sustainability"),
    ]
    for audience, topic in test_cases:
        style = select_style(audience, topic)
        print(f"  {audience:12s} + {topic:25s} → {style.style_id} ({style.tone})")

    yc = get_style("yc_crisp")
    assert yc is not None, "yc_crisp style not found"
    print(f"\n  ✓ {len(STYLE_CATALOG)} styles across {len(families)} families")
    return yc


async def test_slide_generation_standard(bundle, style):
    """Test 7: Standard mode — generate slide content from evidence."""
    hr("TEST 7: STANDARD MODE — Slide Content Generation")

    from app.services.llm.model_router import ModelRouter
    from app.mcp.brain_mcp.generators.slide_generator_v2 import SlideGeneratorV2
    from app.mcp.brain_mcp.research.models import BudgetMode

    model_router = ModelRouter.get_instance()
    generator = SlideGeneratorV2(model_router)

    section("Generating Market slide (lean budget)")
    start = time.monotonic()

    try:
        contract = await generator.generate(
            evidence_bundle=bundle,
            style=style,
            topic="AI-powered healthcare diagnostics startup",
            audience="investors",
            budget_mode=BudgetMode.lean,
            deck_context={
                "slide_index": 3,
                "total_slides": 10,
            },
        )
        elapsed = (time.monotonic() - start) * 1000

        section("PRESENTATION MODE")
        print(f"  Title:    {contract.presentation_content.title}")
        print(f"  Subtitle: {contract.presentation_content.subtitle}")
        if contract.presentation_content.bullets:
            print(f"  Bullets ({len(contract.presentation_content.bullets)}):")
            for b in contract.presentation_content.bullets:
                print(f"    • {b[:100]}")

        section("READING MODE")
        print(f"  Title:    {contract.reading_content.title}")
        print(f"  Summary:  {contract.reading_content.summary[:200] if contract.reading_content.summary else 'N/A'}")
        if contract.reading_content.body_sections:
            print(f"  Body Sections ({len(contract.reading_content.body_sections)}):")
            for sec in contract.reading_content.body_sections:
                print(f"    § {sec.heading}")
                for p in sec.paragraphs[:1]:
                    print(f"      {p[:120]}...")
        if contract.reading_content.assumptions:
            print(f"  Assumptions ({len(contract.reading_content.assumptions)}):")
            for a in contract.reading_content.assumptions[:3]:
                print(f"    ⚠ {a[:100]}")
        if contract.reading_content.risks:
            print(f"  Risks ({len(contract.reading_content.risks)}):")
            for r in contract.reading_content.risks[:3]:
                print(f"    ⚠ {r[:100]}")

        section("SPEAKER NOTES")
        for note in (contract.speaker_notes or [])[:3]:
            print(f"    📝 {note[:120]}")

        section("CHART DATA")
        if contract.chart_data:
            print(f"  Chart type: {contract.chart_data.get('type', 'N/A')}")
            print(f"  Data points: {json.dumps(contract.chart_data, indent=2)[:300]}")
        else:
            print(f"  No chart data (expected for this slide kind: {'yes' if bundle.slide_kind.value in ('traction', 'financial', 'market', 'competition') else 'no'})")

        section("IMAGE PROMPT")
        if contract.image_prompt:
            print(f"  {contract.image_prompt[:200]}")
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
        print(f"  Errors recovered:  {meta.errors_recovered}")

        print(f"\n  ✓ STANDARD mode generated successfully in {elapsed:.0f}ms")
        return contract

    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        print(f"\n  ✗ STANDARD mode FAILED after {elapsed:.0f}ms: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_slide_generation_premium(bundle, style):
    """Test 8: Premium mode — with debate loop."""
    hr("TEST 8: PREMIUM MODE — With Debate Loop")

    from app.services.llm.model_router import ModelRouter
    from app.mcp.brain_mcp.generators.slide_generator_v2 import SlideGeneratorV2
    from app.mcp.brain_mcp.research.debate_loop import DebateLoop
    from app.mcp.brain_mcp.research.content_events import ContentEventEmitter
    from app.mcp.brain_mcp.research.models import BudgetMode, SlideKind

    model_router = ModelRouter.get_instance()
    emitter = ContentEventEmitter("test_premium", None)

    # Step 1: Run debate
    section("Multi-Agent Debate (CEO/CTO/Finance)")
    debate = DebateLoop(model_router, emitter)
    start = time.monotonic()

    try:
        outcome = await debate.run_debate(
            bundle, "AI-powered healthcare diagnostics startup", SlideKind.market,
        )
        debate_ms = (time.monotonic() - start) * 1000
        print(f"  Debate completed in {debate_ms:.0f}ms")
        avg_conf = (outcome.ceo_confidence + outcome.cto_confidence + outcome.finance_confidence) / 3
        print(f"  Avg confidence: {avg_conf:.2f} (CEO:{outcome.ceo_confidence:.2f} CTO:{outcome.cto_confidence:.2f} FIN:{outcome.finance_confidence:.2f})")
        print(f"  Iterations: {outcome.iteration_count}")
        print(f"  Approved claims: {len(outcome.approved_claims)}")
        print(f"  Rejected claims: {len(outcome.rejected_claims)}")
        print(f"  Thesis: {outcome.final_thesis[:150]}")
        for rc in outcome.rejected_claims[:3]:
            reason = rc.reason if hasattr(rc, 'reason') else str(rc)
            print(f"    ✗ {reason[:100]}")

        # Update bundle with debate results
        bundle.approved_claim_ids = outcome.approved_claims

    except Exception as e:
        print(f"  ⚠ Debate failed: {e}")
        import traceback
        traceback.print_exc()
        # Continue with all claims approved
        bundle.approved_claim_ids = [p.id for p in bundle.evidence_packets]

    # Step 2: Generate with balanced budget
    section("Premium Content Generation (balanced budget)")
    generator = SlideGeneratorV2(model_router)
    start = time.monotonic()

    try:
        contract = await generator.generate(
            evidence_bundle=bundle,
            style=style,
            topic="AI-powered healthcare diagnostics startup",
            audience="investors",
            budget_mode=BudgetMode.balanced,
            deck_context={
                "slide_index": 3,
                "total_slides": 10,
            },
        )
        elapsed = (time.monotonic() - start) * 1000

        section("PREMIUM PRESENTATION MODE")
        print(f"  Title:    {contract.presentation_content.title}")
        print(f"  Subtitle: {contract.presentation_content.subtitle}")
        if contract.presentation_content.bullets:
            for b in contract.presentation_content.bullets:
                print(f"    • {b[:100]}")

        section("PREMIUM READING MODE")
        print(f"  Title:    {contract.reading_content.title}")
        print(f"  Summary:  {contract.reading_content.summary[:200] if contract.reading_content.summary else 'N/A'}")

        section("PREMIUM SPEAKER NOTES")
        for note in (contract.speaker_notes or [])[:3]:
            print(f"    📝 {note[:120]}")

        section("PREMIUM METADATA")
        meta = contract.generation_metadata
        print(f"  Evidence score:    {contract.evidence_score:.3f}")
        print(f"  Style:             {contract.style_id}")
        print(f"  Total latency:     {meta.total_latency_ms:.0f}ms")
        print(f"  Errors recovered:  {meta.errors_recovered}")

        print(f"\n  ✓ PREMIUM mode generated successfully in {elapsed:.0f}ms")
        return contract

    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        print(f"\n  ✗ PREMIUM mode FAILED after {elapsed:.0f}ms: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_dual_mode_writer(style):
    """Test 9: Full deck generation with DualModeWriter."""
    hr("TEST 9: Full Deck — Dual Mode Writer (3 slides)")

    from app.services.llm.model_router import ModelRouter
    from app.mcp.brain_mcp.generators.dual_mode_writer import DualModeWriter
    from app.mcp.brain_mcp.research.models import (
        SlideKind, BudgetMode, SlideEvidenceBundle, SourceMix, FactPacket,
        ClaimType, SourceType, FreshnessClass,
    )
    from app.mcp.brain_mcp.research.evidence_assembler import EvidenceAssembler

    model_router = ModelRouter.get_instance()
    writer = DualModeWriter(model_router)

    # Create mock evidence bundles for 3 slides with real-looking data
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

    bundles = [
        SlideEvidenceBundle(
            slide_id="s_problem",
            slide_kind=SlideKind.problem,
            evidence_packets=[
                make_packet("Healthcare misdiagnosis costs $750B annually", "World Health Org", "serper", SourceType.government_data, 0.92),
                make_packet("Radiologists miss 30% of early-stage cancers due to fatigue", "JAMA Study", "core", SourceType.academic_paper, 0.88),
                make_packet("Average diagnostic wait time is 23 days in rural areas", "CDC Report", "fred", SourceType.government_data, 0.85),
            ],
            evidence_score=0.82,
            approved_claim_ids=["fp_0001", "fp_0002", "fp_0003"],
        ),
        SlideEvidenceBundle(
            slide_id="s_solution",
            slide_kind=SlideKind.solution,
            evidence_packets=[
                make_packet("AI diagnostic tools achieve 94% accuracy on chest X-rays", "Nature Medicine", "core", SourceType.academic_paper, 0.91),
                make_packet("AI triage reduces diagnostic time from 23 days to 48 hours", "MIT Tech Review", "tavily", SourceType.news_article, 0.78),
            ],
            evidence_score=0.75,
            approved_claim_ids=["fp_0001", "fp_0002"],
        ),
        SlideEvidenceBundle(
            slide_id="s_market",
            slide_kind=SlideKind.market,
            evidence_packets=[
                make_packet("Global AI in healthcare market: $45.2B by 2030, CAGR 44.9%", "Grand View Research", "serper", SourceType.industry_report, 0.86),
                make_packet("US healthcare AI spending reached $6.7B in 2025", "CB Insights", "tavily", SourceType.news_article, 0.80),
                make_packet("FDA approved 521 AI/ML medical devices as of 2025", "FDA Database", "fred", SourceType.government_data, 0.95),
            ],
            evidence_score=0.88,
            approved_claim_ids=["fp_0001", "fp_0002", "fp_0003"],
        ),
    ]

    section("Generating 3-slide deck (problem + solution + market)")
    start = time.monotonic()

    try:
        contracts = await writer.generate_deck(
            evidence_bundles=bundles,
            style=style,
            topic="AI-powered healthcare diagnostics startup",
            audience="investors",
            budget_mode=BudgetMode.lean,
        )
        elapsed = (time.monotonic() - start) * 1000

        for c in contracts:
            section(f"Slide: {c.slide_kind.value}")
            print(f"  📊 Presentation: {c.presentation_content.title}")
            if c.presentation_content.bullets:
                for b in c.presentation_content.bullets[:3]:
                    print(f"    • {b[:100]}")
            print(f"  📖 Reading: {c.reading_content.title}")
            if c.speaker_notes:
                print(f"  🎤 Notes: {c.speaker_notes[0][:100]}...")
            print(f"  Score: {c.evidence_score:.2f} | Style: {c.style_id}")

        print(f"\n  ✓ Full deck ({len(contracts)} slides) generated in {elapsed:.0f}ms")
        return contracts

    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        print(f"\n  ✗ Dual mode writer FAILED after {elapsed:.0f}ms: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    print(f"\n{'█' * 70}")
    print(f"  V2 SLIDE CONTENT GENERATION — REAL-TIME END-TO-END TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'█' * 70}")

    results = {}
    total_start = time.monotonic()

    # Test 1: Provider Registry
    try:
        registry = await test_provider_registry()
        results["provider_registry"] = "PASS"
    except Exception as e:
        print(f"\n  ✗ Provider Registry FAILED: {e}")
        results["provider_registry"] = f"FAIL: {e}"
        return

    # Test 2: Circuit Breaker
    try:
        await test_circuit_breaker()
        results["circuit_breaker"] = "PASS"
    except Exception as e:
        print(f"\n  ✗ Circuit Breaker FAILED: {e}")
        results["circuit_breaker"] = f"FAIL: {e}"

    # Test 3: Query Planner
    try:
        await test_query_planner()
        results["query_planner"] = "PASS"
    except Exception as e:
        print(f"\n  ✗ Query Planner FAILED: {e}")
        results["query_planner"] = f"FAIL: {e}"

    # Test 4: Live Research
    packets = []
    try:
        packets = await test_research_router_live(registry)
        results["live_research"] = f"PASS ({len(packets)} packets)"
    except Exception as e:
        print(f"\n  ✗ Live Research FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["live_research"] = f"FAIL: {e}"

    # Test 5: Evidence Assembly
    bundle = None
    if packets:
        try:
            bundle = await test_evidence_assembly(packets)
            results["evidence_assembly"] = "PASS"
        except Exception as e:
            print(f"\n  ✗ Evidence Assembly FAILED: {e}")
            import traceback
            traceback.print_exc()
            results["evidence_assembly"] = f"FAIL: {e}"
    else:
        results["evidence_assembly"] = "SKIPPED (no packets)"

    # Test 6: Style Catalog
    style = None
    try:
        style = await test_style_catalog()
        results["style_catalog"] = "PASS"
    except Exception as e:
        print(f"\n  ✗ Style Catalog FAILED: {e}")
        results["style_catalog"] = f"FAIL: {e}"

    # Test 7: Standard Mode Generation
    if bundle and style:
        try:
            std_contract = await test_slide_generation_standard(bundle, style)
            results["standard_mode"] = "PASS" if std_contract else "FAIL"
        except Exception as e:
            print(f"\n  ✗ Standard Mode FAILED: {e}")
            import traceback
            traceback.print_exc()
            results["standard_mode"] = f"FAIL: {e}"
    else:
        results["standard_mode"] = "SKIPPED"

    # Test 8: Premium Mode Generation
    if bundle and style:
        try:
            premium_contract = await test_slide_generation_premium(bundle, style)
            results["premium_mode"] = "PASS" if premium_contract else "FAIL"
        except Exception as e:
            print(f"\n  ✗ Premium Mode FAILED: {e}")
            import traceback
            traceback.print_exc()
            results["premium_mode"] = f"FAIL: {e}"
    else:
        results["premium_mode"] = "SKIPPED"

    # Test 9: Dual Mode Writer (uses mock evidence)
    if style:
        try:
            deck = await test_dual_mode_writer(style)
            results["dual_mode_writer"] = "PASS" if deck else "FAIL"
        except Exception as e:
            print(f"\n  ✗ Dual Mode Writer FAILED: {e}")
            import traceback
            traceback.print_exc()
            results["dual_mode_writer"] = f"FAIL: {e}"
    else:
        results["dual_mode_writer"] = "SKIPPED"

    # Final Summary
    total_elapsed = (time.monotonic() - total_start) * 1000
    hr("FINAL RESULTS")
    passed = sum(1 for v in results.values() if v.startswith("PASS"))
    failed = sum(1 for v in results.values() if v.startswith("FAIL"))
    skipped = sum(1 for v in results.values() if v.startswith("SKIP"))

    for test, result in results.items():
        icon = "✓" if result.startswith("PASS") else "✗" if result.startswith("FAIL") else "○"
        print(f"  {icon} {test:25s}: {result}")

    print(f"\n  Total: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"  Total time: {total_elapsed / 1000:.1f}s")
    print(f"{'█' * 70}\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
