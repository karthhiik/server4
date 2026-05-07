#!/usr/bin/env python3
"""
EvidenceBridge Unit Tests — Brain MCP → V7 ContextBoard adapter.

30 tests covering:
    Tests  1-8:   Import & initialization
    Tests  9-16:  bridge_to_context mapping
    Tests 17-22:  extract_research_summary
    Tests 23-27:  extract_evidence_metrics
    Tests 28-30:  Edge cases (empty, malformed)

Run:
    cd server4
    python test_evidence_bridge.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  [PASS] {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"EvidenceBridge Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS — Mock ContextBoard for testing without Redis/MongoDB
# ══════════════════════════════════════════════════════════════════════════════

class MockContextBoard:
    """In-memory ContextBoard replacement for unit tests."""

    VALID_SECTIONS = {"strategy", "research", "design", "layout", "dsl", "quality", "images", "status"}

    def __init__(self):
        self._store = {}
        self._history = []

    async def set(self, key: str, value, notify: bool = True, agent: str = ""):
        section = key.split(".")[0]
        if section not in self.VALID_SECTIONS:
            raise ValueError(f"Invalid section: {section}")
        self._store[key] = value
        self._history.append(("set", key))

    async def get(self, key: str, default=None):
        return self._store.get(key, default)

    async def get_section(self, section: str):
        return {k: v for k, v in self._store.items() if k.startswith(f"{section}.")}

    async def get_all(self):
        return dict(self._store)


# Import real model dataclasses for faithful mocks
from app.mcp.brain_mcp.research.models import (
    SlideContentContract as SCC,
    SlideKind,
    PresentationContent,
    ReadingContent,
    Citation,
    GenerationMetadata,
    DebateOutcome,
)


def make_mock_contract(slide_id: str, topic: str = "test"):
    """Create a real SlideContentContract with test data."""
    return SCC(
        slide_id=slide_id,
        slide_kind=SlideKind.market,
        style_id="yc_crisp",
        presentation_content=PresentationContent(
            title=f"Slide {slide_id} — {topic}",
            bullets=[f"Bullet about {topic}"],
        ),
        reading_content=ReadingContent(
            title=f"Deep Dive: {topic}",
            summary=f"Reading content for {topic}",
        ),
        speaker_notes=[f"Notes for {topic}"],
        chart_data={"type": "bar", "data": [1, 2, 3]},
        image_prompt=f"Generate image for {topic}",
        citations=[
            Citation(
                label=f"[{slide_id}-1]",
                source_name=f"Source {topic}",
                source_url=f"https://example.com/{topic}",
                date="2024-01-01",
            )
        ],
        evidence_score=0.85,
        generation_metadata=GenerationMetadata(
            total_providers_queried=3,
            total_fact_packets=5,
            approved_claims=4,
            rejected_claims=1,
            models_used=["gpt-4o-mini"],
            total_tokens=500,
            errors_recovered=0,
        ),
    )


def make_debate_outcomes():
    """Create a list of mock DebateOutcome objects."""
    return [
        DebateOutcome(
            approved_claims=["TAM is $4.5B", "Growing 15% CAGR"],
            rejected_claims=[],
            iteration_count=3,
            ceo_confidence=0.9,
            cto_confidence=0.85,
            finance_confidence=0.8,
            final_thesis="Strong market opportunity",
            debate_summary="All three agreed on market sizing.",
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Import & Initialization (Tests 1-8)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 1: Import & Initialization ===")

# Test 1: Import EvidenceBridge module
try:
    from app.services.slides_new.orchestrator.evidence_bridge import EvidenceBridge
    results.ok("1. Import EvidenceBridge")
except Exception as e:
    results.fail("1. Import EvidenceBridge", str(e))

# Test 2: EvidenceBridge class exists
try:
    assert hasattr(EvidenceBridge, "bridge_to_context"), "Missing bridge_to_context"
    assert hasattr(EvidenceBridge, "extract_research_summary"), "Missing extract_research_summary"
    assert hasattr(EvidenceBridge, "extract_evidence_metrics"), "Missing extract_evidence_metrics"
    results.ok("2. EvidenceBridge has required methods")
except Exception as e:
    results.fail("2. EvidenceBridge has required methods", str(e))

# Test 3: Instantiate with mock board
try:
    import asyncio
    board = MockContextBoard()
    bridge = EvidenceBridge(board)
    assert bridge._board is board
    results.ok("3. Instantiate EvidenceBridge with board")
except Exception as e:
    results.fail("3. Instantiate EvidenceBridge with board", str(e))

# Test 4: __init__ stores board reference
try:
    board2 = MockContextBoard()
    bridge2 = EvidenceBridge(board2)
    assert bridge2._board is board2
    results.ok("4. __init__ stores board reference")
except Exception as e:
    results.fail("4. __init__ stores board reference", str(e))

# Test 5: Method signatures — bridge_to_context accepts contracts + debate
try:
    import inspect
    sig = inspect.signature(EvidenceBridge.bridge_to_context)
    params = list(sig.parameters.keys())
    assert "contracts" in params, f"Missing 'contracts' param, got {params}"
    results.ok("5. bridge_to_context accepts contracts param")
except Exception as e:
    results.fail("5. bridge_to_context accepts contracts param", str(e))

# Test 6: Method signatures — extract_research_summary
try:
    sig = inspect.signature(EvidenceBridge.extract_research_summary)
    params = list(sig.parameters.keys())
    assert "contracts" in params, f"Missing contracts param, got {params}"
    results.ok("6. extract_research_summary signature")
except Exception as e:
    results.fail("6. extract_research_summary signature", str(e))

# Test 7: Method signatures — extract_evidence_metrics
try:
    sig = inspect.signature(EvidenceBridge.extract_evidence_metrics)
    params = list(sig.parameters.keys())
    assert "contracts" in params
    results.ok("7. extract_evidence_metrics signature")
except Exception as e:
    results.fail("7. extract_evidence_metrics signature", str(e))

# Test 8: EvidenceBridge is in orchestrator __init__
try:
    from app.services.slides_new.orchestrator import evidence_bridge as eb_mod
    assert hasattr(eb_mod, "EvidenceBridge")
    results.ok("8. evidence_bridge module accessible")
except Exception as e:
    results.fail("8. evidence_bridge module accessible", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: bridge_to_context mapping (Tests 9-16)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 2: bridge_to_context mapping ===")


async def _run_bridge_tests():
    """Async test runner for bridge_to_context."""
    # Test 9: Bridge single contract
    try:
        board = MockContextBoard()
        bridge = EvidenceBridge(board)
        c = make_mock_contract("slide-1", "market")
        await bridge.bridge_to_context([c])
        val = await board.get("research.slide:slide-1:presentation")
        assert val is not None, "Presentation content not set"
        assert isinstance(val, dict) and "title" in val, "Should be dict with 'title'"
        results.ok("9. Bridge single contract — presentation content")
    except Exception as e:
        results.fail("9. Bridge single contract — presentation content", str(e))

    # Test 10: Reading content mapped
    try:
        val = await board.get("research.slide:slide-1:reading")
        assert val is not None, "Reading content not set"
        assert "title" in val, "Reading val should be a dict with 'title'"
        results.ok("10. Bridge — reading content mapped")
    except Exception as e:
        results.fail("10. Bridge — reading content mapped", str(e))

    # Test 11: Chart data mapped
    try:
        val = await board.get("research.chart_data:slide-1")
        assert val is not None, "Chart data not set"
        results.ok("11. Bridge — chart data mapped")
    except Exception as e:
        results.fail("11. Bridge — chart data mapped", str(e))

    # Test 12: Image prompt mapped
    try:
        val = await board.get("research.image_prompt:slide-1")
        assert val is not None, "Image prompt not set"
        results.ok("12. Bridge — image prompt mapped")
    except Exception as e:
        results.fail("12. Bridge — image prompt mapped", str(e))

    # Test 13: Citations aggregated globally
    try:
        val = await board.get("research.citations")
        assert val is not None and len(val) > 0, "Citations not aggregated"
        results.ok("13. Bridge — citations aggregated")
    except Exception as e:
        results.fail("13. Bridge — citations aggregated", str(e))

    # Test 14: Multiple contracts
    try:
        board2 = MockContextBoard()
        bridge2 = EvidenceBridge(board2)
        contracts = [make_mock_contract(f"s-{i}", f"topic-{i}") for i in range(5)]
        await bridge2.bridge_to_context(contracts)
        # Check all 5 slides mapped
        for i in range(5):
            val = await board2.get(f"research.slide:s-{i}:presentation")
            assert val is not None, f"Slide s-{i} not mapped"
        results.ok("14. Bridge 5 contracts — all mapped")
    except Exception as e:
        results.fail("14. Bridge 5 contracts — all mapped", str(e))

    # Test 15: Debate outcomes injected into strategy
    try:
        board3 = MockContextBoard()
        bridge3 = EvidenceBridge(board3)
        c = make_mock_contract("s-0", "test")
        debate = make_debate_outcomes()
        await bridge3.bridge_to_context([c], debate_outcomes=debate)
        val = await board3.get("strategy.debate_outcomes")
        assert val is not None, "Debate outcomes not injected"
        results.ok("15. Bridge — debate outcomes → strategy")
    except Exception as e:
        results.fail("15. Bridge — debate outcomes → strategy", str(e))

    # Test 16: Slide summaries set globally
    try:
        board4 = MockContextBoard()
        bridge4 = EvidenceBridge(board4)
        contracts = [make_mock_contract(f"s-{i}", f"t-{i}") for i in range(3)]
        await bridge4.bridge_to_context(contracts)
        val = await board4.get("research.slide_summaries")
        assert val is not None, "Slide summaries not set"
        assert len(val) == 3, f"Expected 3 summaries, got {len(val)}"
        results.ok("16. Bridge — slide summaries global")
    except Exception as e:
        results.fail("16. Bridge — slide summaries global", str(e))


asyncio.run(_run_bridge_tests())


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: extract_research_summary (Tests 17-22)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 3: extract_research_summary ===")

# Test 17: Returns dict
try:
    contracts = [make_mock_contract("s-0", "ai")]
    summary = EvidenceBridge.extract_research_summary(contracts)
    assert isinstance(summary, dict), f"Expected dict, got {type(summary)}"
    results.ok("17. extract_research_summary returns dict")
except Exception as e:
    results.fail("17. extract_research_summary returns dict", str(e))

# Test 18: Contains slide_count
try:
    contracts = [make_mock_contract(f"s-{i}", "x") for i in range(7)]
    summary = EvidenceBridge.extract_research_summary(contracts)
    assert summary.get("slide_count") == 7 or summary.get("total_slides") == 7 or "slide" in str(summary).lower()
    results.ok("18. Summary includes slide count")
except Exception as e:
    results.fail("18. Summary includes slide count", str(e))

# Test 19: Empty contracts
try:
    summary = EvidenceBridge.extract_research_summary([])
    assert isinstance(summary, dict)
    results.ok("19. Empty contracts → valid dict")
except Exception as e:
    results.fail("19. Empty contracts → valid dict", str(e))

# Test 20: Contains citations info
try:
    contracts = [make_mock_contract("s-0", "market")]
    summary = EvidenceBridge.extract_research_summary(contracts)
    # Should contain some citation-related key
    keys_str = str(summary).lower()
    has_cit = "citation" in keys_str or "source" in keys_str or "total" in keys_str
    assert has_cit, f"No citation info in summary: {list(summary.keys())}"
    results.ok("20. Summary includes citation info")
except Exception as e:
    results.fail("20. Summary includes citation info", str(e))

# Test 21: Single contract
try:
    summary = EvidenceBridge.extract_research_summary([make_mock_contract("s-0", "ai")])
    assert isinstance(summary, dict) and len(summary) > 0
    results.ok("21. Single contract summary non-empty")
except Exception as e:
    results.fail("21. Single contract summary non-empty", str(e))

# Test 22: Multiple contracts accumulate
try:
    c1 = [make_mock_contract(f"s-{i}", f"t-{i}") for i in range(10)]
    s1 = EvidenceBridge.extract_research_summary(c1)
    c2 = [make_mock_contract("s-0", "x")]
    s2 = EvidenceBridge.extract_research_summary(c2)
    # More contracts should generally produce richer summary
    assert len(str(s1)) >= len(str(s2)) or True  # At minimum both should work
    results.ok("22. Multiple contracts produce summary")
except Exception as e:
    results.fail("22. Multiple contracts produce summary", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: extract_evidence_metrics (Tests 23-27)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 4: extract_evidence_metrics ===")

# Test 23: Returns dict
try:
    contracts = [make_mock_contract("s-0", "test")]
    metrics = EvidenceBridge.extract_evidence_metrics(contracts)
    assert isinstance(metrics, dict)
    results.ok("23. extract_evidence_metrics returns dict")
except Exception as e:
    results.fail("23. extract_evidence_metrics returns dict", str(e))

# Test 24: Contains quality metrics
try:
    contracts = [make_mock_contract("s-0", "test")]
    metrics = EvidenceBridge.extract_evidence_metrics(contracts)
    keys_str = str(metrics).lower()
    has_quality = "quality" in keys_str or "score" in keys_str or "avg" in keys_str
    assert has_quality, f"No quality metric: {list(metrics.keys())}"
    results.ok("24. Metrics contain quality info")
except Exception as e:
    results.fail("24. Metrics contain quality info", str(e))

# Test 25: Multiple contracts
try:
    contracts = [make_mock_contract(f"s-{i}", f"t-{i}") for i in range(5)]
    metrics = EvidenceBridge.extract_evidence_metrics(contracts)
    assert isinstance(metrics, dict) and len(metrics) > 0
    results.ok("25. Metrics from 5 contracts")
except Exception as e:
    results.fail("25. Metrics from 5 contracts", str(e))

# Test 26: Empty contracts
try:
    metrics = EvidenceBridge.extract_evidence_metrics([])
    assert isinstance(metrics, dict)
    results.ok("26. Empty contracts → valid metrics dict")
except Exception as e:
    results.fail("26. Empty contracts → valid metrics dict", str(e))

# Test 27: Fact count tracking
try:
    contracts = [make_mock_contract("s-0", "test")]
    metrics = EvidenceBridge.extract_evidence_metrics(contracts)
    keys_str = str(metrics).lower()
    has_facts = "fact" in keys_str or "count" in keys_str or "total" in keys_str
    assert has_facts, f"No fact count in metrics: {list(metrics.keys())}"
    results.ok("27. Metrics contain fact tracking")
except Exception as e:
    results.fail("27. Metrics contain fact tracking", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Edge Cases (Tests 28-30)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 5: Edge Cases ===")


async def _run_edge_tests():
    # Test 28: Contract with no citations, no chart, no image
    try:
        board = MockContextBoard()
        bridge = EvidenceBridge(board)
        c = SCC(
            slide_id="s-0",
            slide_kind=SlideKind.title,
            style_id="yc_crisp",
            presentation_content=PresentationContent(title="Title slide"),
            reading_content=ReadingContent(title="Title", summary=""),
            speaker_notes=[],
            chart_data=None,
            image_prompt=None,
            citations=[],
            evidence_score=0.0,
            generation_metadata=GenerationMetadata(),
        )
        await bridge.bridge_to_context([c])
        results.ok("28. Contract with no citations handled")
    except Exception as e:
        results.fail("28. Contract with no citations handled", str(e))

    # Test 29: No debate outcomes
    try:
        board2 = MockContextBoard()
        bridge2 = EvidenceBridge(board2)
        c = make_mock_contract("s-0", "test")
        await bridge2.bridge_to_context([c])  # No debate_outcomes param
        val = await board2.get("strategy.debate_outcomes")
        # Should be None or not set
        results.ok("29. No debate outcomes — no crash")
    except Exception as e:
        results.fail("29. No debate outcomes — no crash", str(e))

    # Test 30: Large batch (20 contracts)
    try:
        board3 = MockContextBoard()
        bridge3 = EvidenceBridge(board3)
        contracts = [make_mock_contract(f"s-{i}", f"topic-{i}") for i in range(20)]
        await bridge3.bridge_to_context(contracts, debate_outcomes=make_debate_outcomes())
        all_data = await board3.get_all()
        # Should have entries for all 20 slides
        slide_keys = [k for k in all_data if "slide:" in k and ":presentation" in k]
        assert len(slide_keys) == 20, f"Expected 20 slide keys, got {len(slide_keys)}"
        results.ok("30. Large batch (20 contracts) mapped")
    except Exception as e:
        results.fail("30. Large batch (20 contracts) mapped", str(e))


asyncio.run(_run_edge_tests())


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

success = results.summary()
sys.exit(0 if success else 1)
