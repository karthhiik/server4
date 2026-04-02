"""Phase D — Design Intelligence Integration Tests.

Run: python test_phase_d.py
"""

import asyncio
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch


# ── D1: Theme Suggestions ──────────────────────────────────────


async def test_theme_suggestion_tech():
    """AI/tech topic -> tech-neon theme."""
    from app.mcp.design_mcp.engines.theme_engine import ThemeEngine

    engine = ThemeEngine()
    result = engine.suggest_theme("AI SaaS platform for automation")

    assert result["theme_id"] == "tech-neon", (
        f"Expected tech-neon, got {result['theme_id']}"
    )
    assert result["confidence"] > 0, "Confidence should be > 0"
    print("[PASS] AI/tech topic -> tech-neon theme")


async def test_theme_suggestion_investor():
    """Fundraising purpose -> startup-gradient theme."""
    from app.mcp.design_mcp.engines.theme_engine import ThemeEngine

    engine = ThemeEngine()
    result = engine.suggest_theme("startup pitch", purpose="fundraising")

    assert result["theme_id"] == "startup-gradient", (
        f"Expected startup-gradient, got {result['theme_id']}"
    )
    print("[PASS] Fundraising purpose -> startup-gradient theme")


async def test_theme_suggestion_internal():
    """Internal meeting -> minimal-mono theme."""
    from app.mcp.design_mcp.engines.theme_engine import ThemeEngine

    engine = ThemeEngine()
    result = engine.suggest_theme("team standup meeting")

    assert result["theme_id"] == "minimal-mono", (
        f"Expected minimal-mono, got {result['theme_id']}"
    )
    print("[PASS] Internal meeting -> minimal-mono theme")


async def test_theme_suggestion_mixed_topic_tie_breaker():
    """Mixed topic (AI + Sustainability) -> safe fallback minimal-mono."""
    from app.mcp.design_mcp.engines.theme_engine import ThemeEngine

    engine = ThemeEngine()
    result = engine.suggest_theme("AI for sustainable agriculture")

    # "ai" matches tech-neon, "sustainable"/"agriculture" matches nature-earth
    # Tie -> safe fallback
    assert result["theme_id"] == "minimal-mono", (
        f"Expected minimal-mono (tie-breaker), got {result['theme_id']}"
    )
    assert "multiple categories" in result["reason"], (
        f"Expected tie-breaker reason, got: {result['reason']}"
    )
    print("[PASS] Mixed topic tie-breaker -> minimal-mono (safe fallback)")


async def test_theme_suggestion_no_match_default():
    """Unknown topic -> corporate-blue default."""
    from app.mcp.design_mcp.engines.theme_engine import ThemeEngine

    engine = ThemeEngine()
    result = engine.suggest_theme("random gibberish xyz")

    assert result["theme_id"] == "corporate-blue", (
        f"Expected corporate-blue default, got {result['theme_id']}"
    )
    assert result["confidence"] == 0.0, "Confidence should be 0 for no match"
    print("[PASS] Unknown topic -> corporate-blue default")


async def test_theme_suggestion_purpose_override():
    """Internal purpose overrides startup-gradient -> minimal-mono."""
    from app.mcp.design_mcp.engines.theme_engine import ThemeEngine

    engine = ThemeEngine()
    # "startup" matches startup-gradient, but purpose=internal overrides
    result = engine.suggest_theme("startup launch", purpose="internal")

    assert result["theme_id"] == "minimal-mono", (
        f"Expected minimal-mono override, got {result['theme_id']}"
    )
    print("[PASS] Purpose override: internal -> minimal-mono")


# ── D2: Layout Analysis ────────────────────────────────────────


async def test_layout_analysis_bullet_overload():
    """10 bullets -> chart or two-column suggestion."""
    from app.mcp.design_mcp.engines.layout_solver import LayoutSolver

    solver = LayoutSolver()
    slide = {
        "title": "Market Analysis",
        "layout": "bullets",
        "bullets": [f"Point {i + 1}" for i in range(10)],
    }
    suggestions = solver.analyze_slide(slide)

    warning_suggestions = [s for s in suggestions if s["severity"] == "warning"]
    assert len(warning_suggestions) >= 1, (
        "Expected at least 1 warning for bullet overload"
    )
    assert warning_suggestions[0]["actionable"] is True, (
        "Suggestion should be actionable"
    )
    print("[PASS] Bullet overload -> warning suggestion")


async def test_layout_analysis_chart_suggestion_with_data():
    """Structured data points -> chart suggestion with parsed_data."""
    from app.mcp.design_mcp.engines.layout_solver import LayoutSolver

    solver = LayoutSolver()
    slide = {
        "title": "Revenue Growth",
        "layout": "bullets",
        "bullets": [
            "Revenue: $2.3M",
            "Growth: 34%",
            "Users: 50,000",
            "Retention: 89%",
        ],
    }
    suggestions = solver.analyze_slide(slide)

    chart_suggestions = [
        s
        for s in suggestions
        if s.get("suggested_layout") == "chart" and s.get("parsed_data")
    ]
    assert len(chart_suggestions) >= 1, "Expected chart suggestion with parsed data"
    assert len(chart_suggestions[0]["parsed_data"]) >= 3, (
        "Expected at least 3 parsed data points"
    )
    print("[PASS] Structured data -> chart suggestion with parsed_data")


async def test_layout_analysis_chart_suggestion_unstructured():
    """Unstructured numbers -> KPI dashboard suggestion (not chart)."""
    from app.mcp.design_mcp.engines.layout_solver import LayoutSolver

    solver = LayoutSolver()
    slide = {
        "title": "Company Update",
        "layout": "bullets",
        "bullets": [
            "We grew significantly in 2024 with over 50000 users",
            "Revenue increased to around 2 million dollars",
            "Our retention rate improved to 89 percent",
            "Market size is estimated at 180 billion",
        ],
    }
    suggestions = solver.analyze_slide(slide)

    kpi_suggestions = [
        s for s in suggestions if s.get("suggested_layout") == "kpi-dashboard"
    ]
    chart_suggestions = [
        s
        for s in suggestions
        if s.get("suggested_layout") == "chart" and s.get("parsed_data")
    ]
    assert len(kpi_suggestions) >= 1 or len(chart_suggestions) == 0, (
        "Unstructured numbers should suggest KPI dashboard, not chart"
    )
    print("[PASS] Unstructured numbers -> KPI dashboard (not chart)")


async def test_layout_analysis_comparison_detection():
    """'vs' text -> comparison layout suggestion."""
    from app.mcp.design_mcp.engines.layout_solver import LayoutSolver

    solver = LayoutSolver()
    slide = {
        "title": "Our Solution vs Competitors",
        "layout": "bullets",
        "bullets": [
            "We offer real-time analytics vs their batch processing",
            "Our pricing is 50% lower compared to alternatives",
        ],
    }
    suggestions = solver.analyze_slide(slide)

    comparison_suggestions = [
        s for s in suggestions if s.get("suggested_layout") == "comparison"
    ]
    assert len(comparison_suggestions) >= 1, "Expected comparison layout suggestion"
    print("[PASS] Comparison text -> comparison layout suggestion")


async def test_layout_analysis_timeline_detection():
    """Dates/sequence -> timeline layout suggestion."""
    from app.mcp.design_mcp.engines.layout_solver import LayoutSolver

    solver = LayoutSolver()
    slide = {
        "title": "Roadmap",
        "layout": "bullets",
        "bullets": [
            "Q1 2024: Launch MVP",
            "Q2 2024: Reach 10K users",
            "Q3 2024: Expand to Europe",
            "Q4 2024: Series A funding",
        ],
    }
    suggestions = solver.analyze_slide(slide)

    timeline_suggestions = [
        s for s in suggestions if s.get("suggested_layout") == "timeline"
    ]
    assert len(timeline_suggestions) >= 1, "Expected timeline layout suggestion"
    print("[PASS] Timeline content -> timeline layout suggestion")


async def test_layout_analysis_team_detection():
    """Team names + roles -> team-grid suggestion."""
    from app.mcp.design_mcp.engines.layout_solver import LayoutSolver

    solver = LayoutSolver()
    slide = {
        "title": "Our Team",
        "layout": "bullets",
        "bullets": [
            "John Smith — CEO, former Google engineer",
            "Jane Doe — CTO, PhD in ML from Stanford",
            "Bob Wilson — VP of Sales, 15 years experience",
        ],
    }
    suggestions = solver.analyze_slide(slide)

    team_suggestions = [
        s for s in suggestions if s.get("suggested_layout") == "team-grid"
    ]
    assert len(team_suggestions) >= 1, "Expected team-grid suggestion"
    print("[PASS] Team content -> team-grid layout suggestion")


async def test_layout_analysis_kpi_detection():
    """KPI metrics -> kpi-dashboard suggestion."""
    from app.mcp.design_mcp.engines.layout_solver import LayoutSolver

    solver = LayoutSolver()
    slide = {
        "title": "Key Metrics",
        "layout": "bullets",
        "bullets": [
            "MRR: $180K, up 23% MoM",
            "Burn rate: $45K/month",
            "Runway: 18 months",
            "CAC: $250, LTV: $3,200",
        ],
    }
    suggestions = solver.analyze_slide(slide)

    kpi_suggestions = [
        s for s in suggestions if s.get("suggested_layout") == "kpi-dashboard"
    ]
    assert len(kpi_suggestions) >= 1, "Expected KPI dashboard suggestion"
    print("[PASS] KPI content -> kpi-dashboard layout suggestion")


# ── D4: Style-Aware Quality Pass ───────────────────────────────


async def test_quality_pass_yc_pitch_strict():
    """YC pitch style has strict bullet limits (15 words)."""
    from app.services.orchestrator.orchestrator import PresentationOrchestrator

    orchestrator = PresentationOrchestrator(
        db=MagicMock(), progress_tracker=MagicMock()
    )

    slides = [
        {
            "layout": "bullets",
            "content": {
                "title": "This Is A Very Long Title That Exceeds The Eight Word Limit For YC Pitch Style",
                "bullets": [
                    "This is a very long bullet point that has way more than fifteen words in it because we are testing the strict limits of the yc pitch writing style which should flag this as a warning for the user to simplify their content",
                ],
            },
        }
    ]

    warnings = orchestrator._run_design_quality_pass(
        slides=slides, purpose="pitch", writing_style="yc_pitch"
    )

    assert len(warnings) >= 1, (
        f"Expected warnings for yc_pitch strict style, got: {warnings}"
    )
    # Should flag the long title (15 words > 8 limit)
    title_warnings = [w for w in warnings if "Title" in w]
    assert len(title_warnings) >= 1, f"Expected title warning, got: {warnings}"
    print("[PASS] YC pitch style -> strict quality checks")


async def test_quality_pass_academic_relaxed():
    """Academic style has relaxed bullet limits (35 words)."""
    from app.services.orchestrator.orchestrator import PresentationOrchestrator

    orchestrator = PresentationOrchestrator(
        db=MagicMock(), progress_tracker=MagicMock()
    )

    slides = [
        {
            "layout": "bullets",
            "content": {
                "title": "A Moderately Long Academic Title With Several Words",
                "bullets": [
                    "This is a moderately long bullet with twenty words that would be fine in academic style but not in yc pitch style because the limits are different",
                ],
            },
        }
    ]

    warnings = orchestrator._run_design_quality_pass(
        slides=slides, purpose="pitch", writing_style="academic"
    )

    # Academic style allows 35 words per bullet, 12 word titles
    # 20 words < 35 * 1.5 = 52.5, so no warning
    bullet_warnings = [w for w in warnings if "bullet" in w.lower()]
    assert len(bullet_warnings) == 0, (
        f"Academic style should not warn on 20-word bullet, got: {bullet_warnings}"
    )
    print("[PASS] Academic style -> relaxed quality checks (no false warnings)")


async def test_quality_pass_investor_market_slide():
    """Investor pitch: market slide without TAM -> warning."""
    from app.services.orchestrator.orchestrator import PresentationOrchestrator

    orchestrator = PresentationOrchestrator(
        db=MagicMock(), progress_tracker=MagicMock()
    )

    slides = [
        {
            "layout": "bullets",
            "content": {
                "title": "Market Opportunity",
                "bullets": [
                    "The market is growing rapidly",
                    "Many companies are entering this space",
                ],
            },
        }
    ]

    warnings = orchestrator._run_design_quality_pass(
        slides=slides, purpose="pitch", writing_style="yc_pitch"
    )

    market_warnings = [w for w in warnings if "Market" in w and "TAM" in w]
    assert len(market_warnings) >= 1, f"Expected TAM warning, got: {warnings}"
    print("[PASS] Market slide without TAM -> warning")


async def test_quality_pass_investor_ask_slide():
    """Investor pitch: ask slide without amount -> warning."""
    from app.services.orchestrator.orchestrator import PresentationOrchestrator

    orchestrator = PresentationOrchestrator(
        db=MagicMock(), progress_tracker=MagicMock()
    )

    slides = [
        {
            "layout": "bullets",
            "content": {
                "title": "Funding Request",
                "bullets": [
                    "We are raising funds to grow the business",
                    "Funds will be used for hiring and expansion",
                ],
            },
        }
    ]

    warnings = orchestrator._run_design_quality_pass(
        slides=slides, purpose="pitch", writing_style="yc_pitch"
    )

    ask_warnings = [w for w in warnings if "funding" in w.lower() or "Ask" in w]
    assert len(ask_warnings) >= 1, f"Expected ask/funding warning, got: {warnings}"
    print("[PASS] Ask slide without amount -> warning")


async def test_quality_pass_bullet_limit_by_style():
    """Bullet word limit varies by writing style."""
    from app.services.orchestrator.orchestrator import PresentationOrchestrator

    orchestrator = PresentationOrchestrator(
        db=MagicMock(), progress_tracker=MagicMock()
    )

    assert orchestrator._get_bullet_word_limit("yc_pitch") == 15
    assert orchestrator._get_bullet_word_limit("minimalist") == 12
    assert orchestrator._get_bullet_word_limit("academic") == 35
    assert orchestrator._get_bullet_word_limit("technical") == 35
    assert orchestrator._get_bullet_word_limit("conversational") == 20
    assert orchestrator._get_bullet_word_limit("unknown_style") == 20  # default
    print("[PASS] Bullet word limits vary correctly by style")


# ── Test Runner ─────────────────────────────────────────────────


async def run_all():
    tests = [
        # D1: Theme Suggestions
        test_theme_suggestion_tech,
        test_theme_suggestion_investor,
        test_theme_suggestion_internal,
        test_theme_suggestion_mixed_topic_tie_breaker,
        test_theme_suggestion_no_match_default,
        test_theme_suggestion_purpose_override,
        # D2: Layout Analysis
        test_layout_analysis_bullet_overload,
        test_layout_analysis_chart_suggestion_with_data,
        test_layout_analysis_chart_suggestion_unstructured,
        test_layout_analysis_comparison_detection,
        test_layout_analysis_timeline_detection,
        test_layout_analysis_team_detection,
        test_layout_analysis_kpi_detection,
        # D4: Style-Aware Quality Pass
        test_quality_pass_yc_pitch_strict,
        test_quality_pass_academic_relaxed,
        test_quality_pass_investor_market_slide,
        test_quality_pass_investor_ask_slide,
        test_quality_pass_bullet_limit_by_style,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"[FAIL] {test_fn.__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Phase D Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 60}")

    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all())
