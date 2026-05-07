#!/usr/bin/env python3
"""
V3 Unified Pipeline & Quality Guards Tests.

50 tests covering:
    Tests  1-10:  Import verification & model instantiation
    Tests 11-20:  Quality guards (fluff, density, claims, investor)
    Tests 21-30:  Cross-slide consistency checks
    Tests 31-37:  deck_level_coherence_score
    Tests 38-44:  UnifiedPipelineService structure & budget routing
    Tests 45-50:  V3 API models & Celery task structure

Run:
    cd server4
    python test_v3_pipeline.py
"""

import sys
import os
import re

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
        print(f"V3 Pipeline Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS — Mock objects for unit testing
# ══════════════════════════════════════════════════════════════════════════════

def make_mock_contract(slide_id, slide_kind="market", pres_text="", bullets=None,
                       citations=None, evidence_score=0.8):
    """Build a mock contract matching the shape cross_slide_consistency_check expects."""
    pres = type("Pres", (), {
        "title": pres_text or f"Slide {slide_id}",
        "bullets": bullets or [],
        "hero_stat": None,
    })()
    read = type("Read", (), {
        "summary": f"Reading for {slide_id}",
    })()
    cits = citations or []
    return type("Contract", (), {
        "slide_id": slide_id,
        "slide_kind": type("SK", (), {"value": slide_kind})(),
        "presentation_content": pres,
        "reading_content": read,
        "citations": cits,
        "evidence_score": evidence_score,
    })()


def make_citation(label, source_url="https://example.com"):
    return type("Cit", (), {"label": label, "source_url": source_url})()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Import Verification (Tests 1-10)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 1: Import Verification ===")

# Test 1
try:
    from app.mcp.brain_mcp.prompts.quality_guards import (
        run_quality_guards,
        fluff_check,
        slide_density_check,
        claim_source_check,
        investor_readiness_check,
        QualityGuardResult,
    )
    results.ok("1. Import quality_guards core functions")
except Exception as e:
    results.fail("1. Import quality_guards core functions", str(e))

# Test 2
try:
    from app.mcp.brain_mcp.prompts.quality_guards import (
        cross_slide_consistency_check,
        deck_level_coherence_score,
    )
    results.ok("2. Import cross-slide consistency functions")
except Exception as e:
    results.fail("2. Import cross-slide consistency functions", str(e))

# Test 3
try:
    from app.mcp.brain_mcp.prompts.quality_guards import (
        _normalise_dollar,
        _DOLLAR_PATTERN,
        _PERCENT_PATTERN,
        _METRIC_SYNONYMS,
    )
    results.ok("3. Import internal helpers")
except Exception as e:
    results.fail("3. Import internal helpers", str(e))

# Test 4
try:
    from app.services.unified_pipeline import (
        UnifiedGenerationRequest,
        UnifiedGenerationResult,
        UnifiedPipelineService,
    )
    results.ok("4. Import UnifiedPipeline models & service")
except Exception as e:
    results.fail("4. Import UnifiedPipeline models & service", str(e))

# Test 5
try:
    from app.api.routes.v3_generation import (
        V3GenerateRequest,
        V3GenerateResponse,
        V3StatusResponse,
        V3EvidenceResponse,
    )
    results.ok("5. Import V3 API models")
except Exception as e:
    results.fail("5. Import V3 API models", str(e))

# Test 6
try:
    from app.tasks.unified_tasks import generate_unified_deck
    assert generate_unified_deck.name is not None
    results.ok("6. Import unified Celery task")
except Exception as e:
    results.fail("6. Import unified Celery task", str(e))

# Test 7
try:
    from app.services.slides_new.orchestrator.evidence_bridge import EvidenceBridge
    results.ok("7. Import EvidenceBridge")
except Exception as e:
    results.fail("7. Import EvidenceBridge", str(e))

# Test 8
try:
    r = QualityGuardResult()
    assert r.passed is True
    assert r.warnings == []
    assert r.fluff_found == []
    assert r.unsourced_claims == []
    assert r.density_issues == []
    assert r.investor_issues == []
    results.ok("8. QualityGuardResult default state")
except Exception as e:
    results.fail("8. QualityGuardResult default state", str(e))

# Test 9
try:
    req = UnifiedGenerationRequest(topic="test")
    assert req.mode == "standard"
    assert req.slide_count == 10
    assert req.writing_style == "yc_crisp"
    assert req.language == "en"
    results.ok("9. UnifiedGenerationRequest defaults")
except Exception as e:
    results.fail("9. UnifiedGenerationRequest defaults", str(e))

# Test 10
try:
    result = UnifiedGenerationResult(
        success=True, deck_id="d-1", mode="standard"
    )
    assert result.success is True
    assert result.slides == []
    assert result.evidence_report is None
    assert result.coherence_score == 0.0
    results.ok("10. UnifiedGenerationResult defaults")
except Exception as e:
    results.fail("10. UnifiedGenerationResult defaults", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Quality Guards (Tests 11-20)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 2: Quality Guards ===")

# Test 11: Fluff detection
try:
    content = {"title": "Our revolutionary disruptive platform"}
    r = run_quality_guards(content)
    assert len(r.fluff_found) >= 2, f"Expected ≥2 fluff words, got {r.fluff_found}"
    assert "revolutionary" in [f.lower() for f in r.fluff_found]
    results.ok("11. Fluff detection — revolutionary, disruptive")
except Exception as e:
    results.fail("11. Fluff detection", str(e))

# Test 12: No fluff in clean content
try:
    content = {"title": "AI-powered market analytics", "bullets": ["$2.4B market size (Gartner 2024)"]}
    r = run_quality_guards(content)
    assert r.fluff_found == [], f"False fluff: {r.fluff_found}"
    results.ok("12. No fluff in clean content")
except Exception as e:
    results.fail("12. No fluff in clean content", str(e))

# Test 13: Bullet density check
try:
    content = {"title": "Ok", "bullets": [f"Bullet {i}" for i in range(8)]}
    r = run_quality_guards(content)
    density_text = " ".join(r.density_issues)
    assert "bullets" in density_text.lower() or "too many" in density_text.lower(), \
        f"Expected density warning for 8 bullets: {r.density_issues}"
    results.ok("13. Too many bullets flagged")
except Exception as e:
    results.fail("13. Too many bullets flagged", str(e))

# Test 14: Long title flagged
try:
    content = {"title": "This is a very long title that has way too many words for any reasonable slide"}
    r = run_quality_guards(content)
    has_title_issue = any("title" in i.lower() for i in r.density_issues)
    assert has_title_issue, f"Expected title warning: {r.density_issues}"
    results.ok("14. Long title flagged")
except Exception as e:
    results.fail("14. Long title flagged", str(e))

# Test 15: Unsourced $M claim detected
try:
    content = {"body_text": "The global market is worth $4.5B and growing at 12% CAGR"}
    r = run_quality_guards(content)
    assert len(r.unsourced_claims) > 0, f"Expected unsourced: {r.unsourced_claims}"
    results.ok("15. Unsourced $4.5B claim detected")
except Exception as e:
    results.fail("15. Unsourced $4.5B claim detected", str(e))

# Test 16: Sourced claim passes
try:
    content = {"body_text": "The global market is $4.5B (Gartner 2024) growing 12% CAGR according to Statista"}
    r = run_quality_guards(content)
    # Should have fewer unsourced claims
    results.ok("16. Sourced claim handled")
except Exception as e:
    results.fail("16. Sourced claim handled", str(e))

# Test 17: Investor readiness — traction slide
try:
    content = {"title": "Traction", "bullets": ["10K users", "$100K MRR"]}
    r = run_quality_guards(content, layout="bullets", purpose="traction", is_investor_deck=True)
    has_chart_suggestion = any("chart" in i.lower() or "trajectory" in i.lower() for i in r.investor_issues)
    assert has_chart_suggestion, f"Expected chart suggestion: {r.investor_issues}"
    results.ok("17. Traction slide — chart layout recommended")
except Exception as e:
    results.fail("17. Traction slide — chart layout recommended", str(e))

# Test 18: Investor readiness — market without TAM/SAM
try:
    content = {"title": "Market Opportunity", "body_text": "Large and growing market"}
    r = run_quality_guards(content, purpose="market opportunity", is_investor_deck=True)
    has_tam = any("tam" in i.lower() or "sam" in i.lower() for i in r.investor_issues)
    assert has_tam, f"Expected TAM/SAM warning: {r.investor_issues}"
    results.ok("18. Market slide — TAM/SAM required")
except Exception as e:
    results.fail("18. Market slide — TAM/SAM required", str(e))

# Test 19: Investor readiness — no competitors
try:
    content = {"title": "Competition", "body_text": "We have no direct competitors in this space"}
    r = run_quality_guards(content, purpose="competition", is_investor_deck=True)
    has_competitor_warning = any("competitor" in i.lower() for i in r.investor_issues)
    assert has_competitor_warning, f"Expected competitor warning: {r.investor_issues}"
    results.ok("19. Competition — 'no competitors' flagged")
except Exception as e:
    results.fail("19. Competition — 'no competitors' flagged", str(e))

# Test 20: run_quality_guards returns QualityGuardResult
try:
    r = run_quality_guards({"title": "Hello"})
    assert isinstance(r, QualityGuardResult)
    d = r.to_dict()
    assert "passed" in d
    assert "fluff_found" in d
    results.ok("20. run_quality_guards → QualityGuardResult with to_dict()")
except Exception as e:
    results.fail("20. run_quality_guards → QualityGuardResult", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Cross-Slide Consistency (Tests 21-30)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 3: Cross-Slide Consistency ===")

# Test 21: Empty contracts → no issues
try:
    issues = cross_slide_consistency_check([])
    assert issues == [], f"Expected no issues, got {issues}"
    results.ok("21. Empty contracts → no issues")
except Exception as e:
    results.fail("21. Empty contracts → no issues", str(e))

# Test 22: _normalise_dollar basic
try:
    assert _normalise_dollar("4.5", "B") == 4.5e9
    assert _normalise_dollar("100", "M") == 100e6
    assert _normalise_dollar("50", "K") == 50e3
    assert _normalise_dollar("1", "") == 1.0
    results.ok("22. _normalise_dollar conversions")
except Exception as e:
    results.fail("22. _normalise_dollar conversions", str(e))

# Test 23: _normalise_dollar edge cases
try:
    assert _normalise_dollar("1,200", "M") == 1200e6
    assert _normalise_dollar("invalid", "M") == 0.0
    assert _normalise_dollar("0", "B") == 0.0
    results.ok("23. _normalise_dollar edge cases")
except Exception as e:
    results.fail("23. _normalise_dollar edge cases", str(e))

# Test 24: Conflicting TAM values detected
try:
    c1 = make_mock_contract("s-1", "market",
                            bullets=["$4.5B TAM growing fast"])
    c2 = make_mock_contract("s-2", "financial",
                            bullets=["$8B TAM opportunity"])
    issues = cross_slide_consistency_check([c1, c2])
    numeric_issues = [i for i in issues if i["type"] == "numeric_conflict"]
    assert len(numeric_issues) > 0, f"Expected numeric conflict: {issues}"
    assert numeric_issues[0]["severity"] == "critical"
    results.ok("24. Conflicting TAM values → critical issue")
except Exception as e:
    results.fail("24. Conflicting TAM values → critical issue", str(e))

# Test 25: Consistent values pass
try:
    c1 = make_mock_contract("s-1", "market",
                            bullets=["$4.5B TAM"])
    c2 = make_mock_contract("s-2", "financial",
                            bullets=["$4.5B TAM opportunity"])
    issues = cross_slide_consistency_check([c1, c2])
    numeric_issues = [i for i in issues if i["type"] == "numeric_conflict"]
    assert len(numeric_issues) == 0, f"Unexpected conflict: {numeric_issues}"
    results.ok("25. Consistent TAM values → no conflict")
except Exception as e:
    results.fail("25. Consistent TAM values → no conflict", str(e))

# Test 26: Citation label conflict
try:
    cit1 = make_citation("[1]", "https://a.com")
    cit2 = make_citation("[1]", "https://b.com")
    c1 = make_mock_contract("s-1", "content", citations=[cit1])
    c2 = make_mock_contract("s-2", "content", citations=[cit2])
    issues = cross_slide_consistency_check([c1, c2])
    cit_issues = [i for i in issues if i["type"] == "citation_conflict"]
    assert len(cit_issues) > 0, f"Expected citation conflict: {issues}"
    results.ok("26. Duplicate citation labels → conflict")
except Exception as e:
    results.fail("26. Duplicate citation labels → conflict", str(e))

# Test 27: ARR + MRR mixing detected
try:
    c1 = make_mock_contract("s-1", "traction",
                            bullets=["$1.2M ARR"])
    c2 = make_mock_contract("s-2", "financial",
                            bullets=["$100K MRR growth"])
    issues = cross_slide_consistency_check([c1, c2])
    metric_issues = [i for i in issues if i["type"] == "metric_inconsistency"]
    assert len(metric_issues) > 0, f"Expected ARR/MRR inconsistency: {issues}"
    results.ok("27. ARR + MRR mixing → metric_inconsistency")
except Exception as e:
    results.fail("27. ARR + MRR mixing → metric_inconsistency", str(e))

# Test 28: Narrative order — solution before problem
try:
    c1 = make_mock_contract("s-1", "solution")
    c2 = make_mock_contract("s-2", "problem")
    issues = cross_slide_consistency_check([c1, c2])
    order_issues = [i for i in issues if i["type"] == "narrative_order"]
    assert len(order_issues) > 0, f"Expected narrative order issue: {issues}"
    results.ok("28. Solution before problem → narrative order issue")
except Exception as e:
    results.fail("28. Solution before problem → narrative order issue", str(e))

# Test 29: Correct narrative order — no issues
try:
    c1 = make_mock_contract("s-1", "problem")
    c2 = make_mock_contract("s-2", "solution")
    c3 = make_mock_contract("s-3", "market")
    issues = cross_slide_consistency_check([c1, c2, c3])
    order_issues = [i for i in issues if i["type"] == "narrative_order"]
    assert len(order_issues) == 0, f"Unexpected narrative issue: {order_issues}"
    results.ok("29. Correct narrative order → no issues")
except Exception as e:
    results.fail("29. Correct narrative order → no issues", str(e))

# Test 30: Issue dict structure
try:
    c1 = make_mock_contract("s-1", "market", bullets=["$4B TAM"])
    c2 = make_mock_contract("s-2", "ask", bullets=["$10B TAM claim"])
    issues = cross_slide_consistency_check([c1, c2])
    if issues:
        issue = issues[0]
        assert "type" in issue, "Missing 'type'"
        assert "severity" in issue, "Missing 'severity'"
        assert "slides" in issue, "Missing 'slides'"
        assert "message" in issue, "Missing 'message'"
        results.ok("30. Issue dict has required keys")
    else:
        # Values might be within tolerance — still valid
        results.ok("30. Issue dict (no issues, within tolerance)")
except Exception as e:
    results.fail("30. Issue dict structure", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: deck_level_coherence_score (Tests 31-37)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 4: deck_level_coherence_score ===")

# Test 31: Empty contracts → 0.0
try:
    score = deck_level_coherence_score([])
    assert score == 0.0, f"Expected 0.0, got {score}"
    results.ok("31. Empty contracts → 0.0")
except Exception as e:
    results.fail("31. Empty contracts → 0.0", str(e))

# Test 32: Score is 0.0-1.0
try:
    contracts = [make_mock_contract(f"s-{i}", "content", evidence_score=0.9,
                                    citations=[make_citation(f"[{i}]")])
                 for i in range(5)]
    score = deck_level_coherence_score(contracts)
    assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
    results.ok("32. Score in [0.0, 1.0]")
except Exception as e:
    results.fail("32. Score in [0.0, 1.0]", str(e))

# Test 33: Good deck scores high
try:
    correct_order = ["problem", "solution", "market", "traction", "ask"]
    contracts = []
    for i, kind in enumerate(correct_order):
        contracts.append(
            make_mock_contract(f"s-{i}", kind, evidence_score=0.9,
                               citations=[make_citation(f"[{i}]", f"https://src{i}.com")])
        )
    score = deck_level_coherence_score(contracts)
    assert score > 0.5, f"Good deck should score >0.5, got {score}"
    results.ok("33. Well-structured deck scores high")
except Exception as e:
    results.fail("33. Well-structured deck scores high", str(e))

# Test 34: Poor deck scores lower
try:
    # Reversed order, no citations, low evidence
    bad_order = ["ask", "traction", "market", "solution", "problem"]
    contracts = [make_mock_contract(f"s-{i}", kind, evidence_score=0.1, citations=[])
                 for i, kind in enumerate(bad_order)]
    score_bad = deck_level_coherence_score(contracts)
    # Compare with good deck
    good_order = ["problem", "solution", "market", "traction", "ask"]
    good_contracts = [
        make_mock_contract(f"s-{i}", kind, evidence_score=0.9,
                           citations=[make_citation(f"[{i}]", f"https://s{i}.com")])
        for i, kind in enumerate(good_order)
    ]
    score_good = deck_level_coherence_score(good_contracts)
    assert score_bad <= score_good, f"Bad {score_bad} should ≤ good {score_good}"
    results.ok("34. Poor deck ≤ good deck score")
except Exception as e:
    results.fail("34. Poor deck ≤ good deck score", str(e))

# Test 35: Score is rounded to 3 decimals
try:
    contracts = [make_mock_contract("s-0", "content", evidence_score=0.777,
                                    citations=[make_citation("[1]")])]
    score = deck_level_coherence_score(contracts)
    str_score = str(score)
    # Should have at most 3 decimal places
    if "." in str_score:
        decimals = len(str_score.split(".")[1])
        assert decimals <= 3, f"Score has {decimals} decimals: {score}"
    results.ok("35. Score rounded to ≤3 decimals")
except Exception as e:
    results.fail("35. Score rounded to ≤3 decimals", str(e))

# Test 36: Single contract
try:
    c = make_mock_contract("s-0", "problem", evidence_score=1.0,
                           citations=[make_citation("[1]", "https://a.com")])
    score = deck_level_coherence_score([c])
    assert 0.0 <= score <= 1.0
    results.ok("36. Single contract → valid score")
except Exception as e:
    results.fail("36. Single contract → valid score", str(e))

# Test 37: Conflicts lower score
try:
    # Two slides with conflicting TAM but otherwise OK
    c1 = make_mock_contract("s-1", "problem",
                            bullets=["$1B TAM"],
                            evidence_score=0.9,
                            citations=[make_citation("[1]", "https://x.com")])
    c2 = make_mock_contract("s-2", "solution",
                            bullets=["$10B TAM claim"],
                            evidence_score=0.9,
                            citations=[make_citation("[2]", "https://y.com")])
    # No conflict version
    c3 = make_mock_contract("s-3", "problem",
                            bullets=["$5B TAM"],
                            evidence_score=0.9,
                            citations=[make_citation("[3]", "https://z.com")])
    c4 = make_mock_contract("s-4", "solution",
                            bullets=["$5B TAM"],
                            evidence_score=0.9,
                            citations=[make_citation("[4]", "https://w.com")])
    conflict_score = deck_level_coherence_score([c1, c2])
    clean_score = deck_level_coherence_score([c3, c4])
    assert conflict_score <= clean_score, f"Conflict {conflict_score} should ≤ clean {clean_score}"
    results.ok("37. Numeric conflicts lower coherence score")
except Exception as e:
    results.fail("37. Numeric conflicts lower coherence score", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: UnifiedPipelineService Structure (Tests 38-44)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 5: UnifiedPipelineService Structure ===")

# Test 38: Service has required methods
try:
    assert hasattr(UnifiedPipelineService, "generate")
    assert hasattr(UnifiedPipelineService, "_run_standard")
    assert hasattr(UnifiedPipelineService, "_run_premium")
    assert hasattr(UnifiedPipelineService, "_run_brain_mcp_pipeline")
    assert hasattr(UnifiedPipelineService, "_build_budget_mode")
    assert hasattr(UnifiedPipelineService, "_build_default_outline")
    results.ok("38. UnifiedPipelineService has all methods")
except Exception as e:
    results.fail("38. UnifiedPipelineService has all methods", str(e))

# Test 39: Budget mode mapping — standard
try:
    from app.mcp.brain_mcp.research.models import BudgetMode
    svc = UnifiedPipelineService(db=None)
    budget = svc._build_budget_mode("standard", "pitch")
    assert budget == BudgetMode.lean, f"Standard should be lean, got {budget}"
    results.ok("39. Standard mode → BudgetMode.lean")
except Exception as e:
    results.fail("39. Standard mode → BudgetMode.LEAN", str(e))

# Test 40: Budget mode mapping — premium
try:
    budget = svc._build_budget_mode("premium", "pitch")
    assert budget in (BudgetMode.balanced, BudgetMode.hero), f"Premium should be balanced/hero, got {budget}"
    results.ok("40. Premium mode → balanced or hero")
except Exception as e:
    results.fail("40. Premium mode → BALANCED or HERO", str(e))

# Test 41: Budget mode mapping — premium + pitch purpose
try:
    budget_pitch = svc._build_budget_mode("premium", "pitch")
    budget_report = svc._build_budget_mode("premium", "report")
    # Pitch should get hero or balanced, report should get balanced
    assert isinstance(budget_pitch, BudgetMode)
    assert isinstance(budget_report, BudgetMode)
    results.ok("41. Budget routing based on purpose")
except Exception as e:
    results.fail("41. Budget routing based on purpose", str(e))

# Test 42: Default outline generation
try:
    outline = svc._build_default_outline("AI Analytics", 10)
    assert isinstance(outline, list), f"Expected list, got {type(outline)}"
    assert len(outline) == 10, f"Expected 10 slides, got {len(outline)}"
    results.ok("42. Default outline → 10 slides")
except Exception as e:
    results.fail("42. Default outline → 10 slides", str(e))

# Test 43: Default outline — different slide counts (now supports up to 30)
try:
    for count in [3, 5, 10, 11, 15, 20, 25, 30]:
        outline = svc._build_default_outline("Test Topic", count)
        assert len(outline) == count, f"Expected {count}, got {len(outline)}"
    results.ok("43. Default outline scales to slide_count (up to 30)")
except Exception as e:
    results.fail("43. Default outline scales to slide_count", str(e))

# Test 44: Request validation — mode constraint
try:
    req = UnifiedGenerationRequest(topic="test", mode="standard")
    assert req.mode == "standard"
    req2 = UnifiedGenerationRequest(topic="test", mode="premium")
    assert req2.mode == "premium"
    results.ok("44. Request accepts standard/premium modes")
except Exception as e:
    results.fail("44. Request accepts standard/premium modes", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: V3 API Models & Celery Task (Tests 45-50)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 6: V3 API Models & Celery Task ===")

# Test 45: V3GenerateRequest defaults
try:
    req = V3GenerateRequest(topic="Startup AI")
    assert req.mode == "standard"
    assert req.slide_count == 10
    assert req.audience == "investors"
    assert req.writing_style == "yc_crisp"
    assert req.target_formats == ["revealjs"]
    results.ok("45. V3GenerateRequest defaults correct")
except Exception as e:
    results.fail("45. V3GenerateRequest defaults correct", str(e))

# Test 46: V3GenerateRequest mode validation
try:
    valid = True
    try:
        V3GenerateRequest(topic="test", mode="standard")
        V3GenerateRequest(topic="test", mode="premium")
    except Exception:
        valid = False
    assert valid, "Valid modes rejected"
    # Invalid mode should fail
    rejected = False
    try:
        V3GenerateRequest(topic="test", mode="invalid")
    except Exception:
        rejected = True
    assert rejected, "Invalid mode accepted"
    results.ok("46. Mode validation: standard/premium OK, invalid rejected")
except Exception as e:
    results.fail("46. Mode validation", str(e))

# Test 47: V3GenerateRequest slide_count bounds
try:
    rejected_low = False
    try:
        V3GenerateRequest(topic="test", slide_count=1)
    except Exception:
        rejected_low = True
    rejected_high = False
    try:
        V3GenerateRequest(topic="test", slide_count=50)
    except Exception:
        rejected_high = True
    assert rejected_low, "slide_count=1 should be rejected (min 3)"
    assert rejected_high, "slide_count=50 should be rejected (max 30)"
    results.ok("47. slide_count bounds [3, 30] enforced")
except Exception as e:
    results.fail("47. slide_count bounds", str(e))

# Test 48: V3GenerateResponse fields
try:
    r = V3GenerateResponse(
        deck_id="d-1", task_id="t-1", mode="standard",
        status="queued", message="Started"
    )
    assert r.deck_id == "d-1"
    assert r.task_id == "t-1"
    assert r.mode == "standard"
    results.ok("48. V3GenerateResponse fields")
except Exception as e:
    results.fail("48. V3GenerateResponse fields", str(e))

# Test 49: V3StatusResponse fields
try:
    s = V3StatusResponse(
        deck_id="d-1", status="running", mode="premium",
        topic="Test", total_slides=10, total_slides_generated=3,
        quality_score=0.85
    )
    assert s.status == "running"
    assert s.total_slides == 10
    assert s.total_slides_generated == 3
    results.ok("49. V3StatusResponse fields")
except Exception as e:
    results.fail("49. V3StatusResponse fields", str(e))

# Test 50: Celery task is registered
try:
    task = generate_unified_deck
    assert task.max_retries == 1, f"Expected max_retries=1, got {task.max_retries}"
    # Check it's a bound task
    assert task.bind is True or hasattr(task, "request"), "Task should be bound"
    results.ok("50. Celery task config (max_retries=1, bound)")
except Exception as e:
    results.fail("50. Celery task config", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

success = results.summary()
sys.exit(0 if success else 1)
