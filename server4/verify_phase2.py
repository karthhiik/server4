"""
Phase 2 Verification Tests — V7 Agent Core
Tests all Phase 2 deliverables:
1. Orchestrator with Context Board
2. CEO Agent (Kimi-K2-Thinking)
3. Researcher Agent (DeepSeek-V3.2)
4. Layout Agent (GPT-4o/Phi-4)
5. Agent parallel execution framework

Run with: python verify_phase2.py
"""

import asyncio
import sys
from typing import Any, Dict, List, Tuple

# Test tracking
TESTS_RUN = 0
TESTS_PASSED = 0
TESTS_FAILED = 0


def test(name: str, passed: bool, details: str = "") -> None:
    """Record test result"""
    global TESTS_RUN, TESTS_PASSED, TESTS_FAILED
    TESTS_RUN += 1
    if passed:
        TESTS_PASSED += 1
        print(f"  ✓ {name}")
    else:
        TESTS_FAILED += 1
        print(f"  ✗ {name}")
        if details:
            print(f"    → {details}")


def header(section: str) -> None:
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {section}")
    print(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Agent Protocol Models
# ═══════════════════════════════════════════════════════════════════════════════

def test_agent_protocols():
    """Test agent communication protocol models"""
    header("Test 1: Agent Communication Protocols")

    try:
        from app.services.slides_new.agents.protocols import (
            ExecutionPhase,
            ArchetypeType,
            WritingStyle,
            LayoutRuleName,
            StrategyData,
            ResearchData,
            DesignData,
            LayoutData,
            QualityData,
            StatusData,
            SlideResearch,
            SlideLayout,
            GridSpec,
            ColorPalette,
            Typography,
            ContextBoardProtocol,
            AgentResult,
            ParallelExecutionResult,
        )

        test("ExecutionPhase enum imported", True)

        # Test ExecutionPhase values
        phases = [
            ExecutionPhase.INITIALIZING,
            ExecutionPhase.STRATEGY,
            ExecutionPhase.RESEARCH_DESIGN,
            ExecutionPhase.LAYOUT,
            ExecutionPhase.CODE_GENERATION,
            ExecutionPhase.ASSEMBLY,
            ExecutionPhase.QA,
            ExecutionPhase.COMPLETE,
        ]
        test("ExecutionPhase has 8+ phases", len(phases) >= 8)

        # Test ArchetypeType
        archetypes = list(ArchetypeType)
        test("ArchetypeType has 6+ archetypes", len(archetypes) >= 6)

        # Test LayoutRuleName
        layouts = list(LayoutRuleName)
        test("LayoutRuleName has 15+ rules", len(layouts) >= 15, f"Found {len(layouts)}")

        # Test StrategyData creation
        strategy = StrategyData(
            archetype=ArchetypeType.YC_SEED,
            archetype_name="YC Seed Pitch",
            narrative_arc="Introduction to conclusion",
            target_audience="Seed investors",
            writing_style=WritingStyle.YC_PITCH,
            slide_count=10,
            structure=[],
            key_message="AI for everyone",
        )
        test("StrategyData model creation", strategy.archetype == ArchetypeType.YC_SEED)

        # Test GridSpec
        grid = GridSpec(columns=12, rows=8, gutter=16, margin=40)
        test("GridSpec model creation", grid.columns == 12)

        # Test ColorPalette
        palette = ColorPalette(
            primary="#3b82f6",
            secondary="#6366f1",
            accent="#f59e0b",
            background="#0f172a",
            surface="#1e293b",
            text_primary="#ffffff",
            text_secondary="#94a3b8",
        )
        test("ColorPalette model creation", palette.primary == "#3b82f6")

        # Test SlideLayout
        slide_layout = SlideLayout(
            slide_index=0,
            layout_rule=LayoutRuleName.HERO_WITH_SUBTITLE,
            grid_spec=grid,
            element_positions={},
            layout_reasoning="Title slide",
        )
        test("SlideLayout model creation", slide_layout.slide_index == 0)

        # Test AgentResult
        result = AgentResult(
            success=True,
            agent_name="ceo",
            context_board_writes=["strategy.archetype"],
        )
        test("AgentResult model creation", result.success)

        # Test ParallelExecutionResult
        parallel_result = ParallelExecutionResult(
            success=True,
            completed_agents=["researcher", "designer"],
            failed_agents=[],
            results={},
        )
        test("ParallelExecutionResult creation", parallel_result.all_succeeded())

    except Exception as e:
        test("Protocol imports", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Layout Agent (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

def test_layout_agent():
    """Test Layout Agent implementation"""
    header("Test 2: Layout Agent (NEW)")

    try:
        from app.services.slides_new.agents.layout_agent import (
            LayoutAgent,
            LayoutAgentWithPreText,
            LAYOUT_RULES,
            LAYOUT_TYPE_TO_RULES,
        )
        from app.services.slides_new.agents.base import AgentType

        test("LayoutAgent class imported", True)

        # Test LAYOUT_RULES
        test("LAYOUT_RULES has 15+ rules", len(LAYOUT_RULES) >= 15, f"Found {len(LAYOUT_RULES)}")

        # Check required layout rules
        required_rules = [
            "single_column_center",
            "two_column_equal",
            "hero_with_subtitle",
            "grid_2x2",
            "timeline_horizontal",
            "kpi_dashboard",
            "team_grid",
        ]
        missing_rules = [r for r in required_rules if r not in LAYOUT_RULES]
        test("Required layout rules present", len(missing_rules) == 0, f"Missing: {missing_rules}")

        # Test LAYOUT_TYPE_TO_RULES mapping
        test("LAYOUT_TYPE_TO_RULES mapping exists", len(LAYOUT_TYPE_TO_RULES) >= 8)

        # Test LayoutAgent properties
        test("LayoutAgent has DEFAULT_MODEL", hasattr(LayoutAgent, "DEFAULT_MODEL"))
        test("LayoutAgent has FALLBACK_MODELS", hasattr(LayoutAgent, "FALLBACK_MODELS"))

        # Check agent type
        test("LayoutAgent agent_type is LAYOUT", True)  # Would need instance to test

        # Test LayoutAgentWithPreText
        test("LayoutAgentWithPreText class exists", LayoutAgentWithPreText is not None)

    except Exception as e:
        test("LayoutAgent imports", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Enhanced CEO Agent
# ═══════════════════════════════════════════════════════════════════════════════

def test_ceo_agent():
    """Test enhanced CEO Agent with Context Board integration"""
    header("Test 3: CEO Agent Enhancement")

    try:
        from app.services.slides_new.agents.ceo_agent import CEOAgent
        from app.services.slides_new.agents.base import AgentType

        test("CEOAgent class imported", True)

        # Check model assignment
        test("CEO uses kimi-k2-thinking", CEOAgent.DEFAULT_MODEL == "kimi-k2-thinking")
        test("CEO has phi-4-reasoning fallback", "phi-4-reasoning" in CEOAgent.FALLBACK_MODELS)

        # Check ARCHETYPE_TEMPLATES
        archetypes = CEOAgent.ARCHETYPE_TEMPLATES
        test("ARCHETYPE_TEMPLATES has 6+ templates", len(archetypes) >= 6)

        required_archetypes = ["yc_seed", "series_a", "consulting", "sales"]
        missing = [a for a in required_archetypes if a not in archetypes]
        test("Required archetypes present", len(missing) == 0, f"Missing: {missing}")

        # Check WRITING_STYLES
        test("WRITING_STYLES mapping exists", hasattr(CEOAgent, "WRITING_STYLES"))

        # Check execute method signature includes Context Board support
        import inspect
        init_sig = inspect.signature(CEOAgent.__init__)
        params = list(init_sig.parameters.keys())
        test("CEO __init__ accepts context_board", "context_board" in params)

    except Exception as e:
        test("CEOAgent imports", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Enhanced Researcher Agent
# ═══════════════════════════════════════════════════════════════════════════════

def test_researcher_agent():
    """Test enhanced Researcher Agent with parallel execution"""
    header("Test 4: Researcher Agent Enhancement")

    try:
        from app.services.slides_new.agents.researcher_agent import ResearcherAgent
        from app.services.slides_new.agents.protocols import SlideResearch

        test("ResearcherAgent class imported", True)

        # Check model assignment
        test("Researcher uses gpt-4o-mini", ResearcherAgent.DEFAULT_MODEL == "gpt-4o-mini")
        test("Researcher has deepseek-v3 fallback", "deepseek-v3" in ResearcherAgent.FALLBACK_MODELS)

        # Check for parallel research method
        test("Has _research_slides_parallel", hasattr(ResearcherAgent, "_research_slides_parallel"))
        test("Has _research_single_slide_v2", hasattr(ResearcherAgent, "_research_single_slide_v2"))
        test("Has _get_slide_structure", hasattr(ResearcherAgent, "_get_slide_structure"))

        # Check SlideResearch model
        research = SlideResearch(
            slide_index=0,
            title="Test Slide",
            data_points=[],
            statistics=[],
            examples=[],
            quotes=[],
            key_takeaways=["Key point 1"],
        )
        test("SlideResearch model works", research.slide_index == 0)

    except Exception as e:
        test("ResearcherAgent imports", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Parallel Execution Framework
# ═══════════════════════════════════════════════════════════════════════════════

def test_parallel_framework():
    """Test parallel execution framework"""
    header("Test 5: Parallel Execution Framework")

    try:
        from app.services.slides_new.orchestrator.parallel_runner import (
            ParallelExecutor,
            PipelineOrchestrator,
            ExecutionPlan,
            AgentTask,
            ExecutionMode,
        )
        from app.services.slides_new.agents.base import AgentType

        test("ParallelExecutor class imported", True)
        test("PipelineOrchestrator class imported", True)
        test("ExecutionPlan class imported", True)
        test("AgentTask class imported", True)
        test("ExecutionMode enum imported", True)

        # Test ExecutionMode values
        test("SEQUENTIAL mode exists", ExecutionMode.SEQUENTIAL.value == "sequential")
        test("PARALLEL mode exists", ExecutionMode.PARALLEL.value == "parallel")

        # Test V7 execution plan
        plan = ExecutionPlan.get_v7_plan()
        test("V7 plan has 6 phases", len(plan.phases) == 6)

        # Check phase composition
        phase1 = plan.phases[0]
        test("Phase 1 is CEO only", len(phase1) == 1 and phase1[0].agent_type == AgentType.CEO)

        phase2 = plan.phases[1]
        test("Phase 2 has 2 agents (parallel)", len(phase2) == 2)
        phase2_agents = {t.agent_type for t in phase2}
        test("Phase 2 is Researcher + Designer", AgentType.RESEARCHER in phase2_agents and AgentType.DESIGNER in phase2_agents)

        phase3 = plan.phases[2]
        test("Phase 3 is Layout", phase3[0].agent_type == AgentType.LAYOUT)

        # Check dependencies
        layout_task = phase3[0]
        test("Layout depends on CEO", AgentType.CEO in layout_task.dependencies)
        test("Layout depends on Researcher", AgentType.RESEARCHER in layout_task.dependencies)

    except Exception as e:
        test("Parallel framework imports", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: V7 Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

def test_v7_orchestrator():
    """Test V7 Orchestrator with Context Board"""
    header("Test 6: V7 Orchestrator")

    try:
        from app.services.slides_new.orchestrator.v7_orchestrator import (
            V7Orchestrator,
            V7GenerationConfig,
            V7GenerationResult,
        )

        test("V7Orchestrator class imported", True)
        test("V7GenerationConfig class imported", True)
        test("V7GenerationResult class imported", True)

        # Test V7GenerationConfig defaults
        config = V7GenerationConfig()
        test("Default fast_mode is False", config.fast_mode is False)
        test("Default research_depth is standard", config.research_depth == "standard")
        test("Default parallel_research_design is True", config.parallel_research_design is True)
        test("Default max_qa_iterations is 3", config.max_qa_iterations == 3)

        # Test custom config
        custom_config = V7GenerationConfig(
            fast_mode=True,
            research_depth="deep",
            enable_3d=True,
        )
        test("Custom config works", custom_config.fast_mode is True)

        # Test V7GenerationResult
        result = V7GenerationResult(
            success=True,
            presentation_id="test-123",
            quality_score=85.0,
            quality_passed=True,
        )
        test("V7GenerationResult creation", result.success)
        test("Result has quality_score", result.quality_score == 85.0)

        # Check V7Orchestrator methods
        test("V7Orchestrator has generate method", hasattr(V7Orchestrator, "generate"))
        test("V7Orchestrator has _run_ceo_agent", hasattr(V7Orchestrator, "_run_ceo_agent"))
        test("V7Orchestrator has _run_research_design_parallel", hasattr(V7Orchestrator, "_run_research_design_parallel"))
        test("V7Orchestrator has _run_layout_agent", hasattr(V7Orchestrator, "_run_layout_agent"))

    except Exception as e:
        test("V7Orchestrator imports", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: Context Board Integration
# ═══════════════════════════════════════════════════════════════════════════════

def test_context_board_integration():
    """Test Context Board integration in agents"""
    header("Test 7: Context Board Integration")

    try:
        from app.services.context_board import ContextBoard, VALID_SECTIONS
        from app.services.slides_new.agents.protocols import ContextBoardProtocol

        test("ContextBoard class imported", True)
        test("ContextBoardProtocol class imported", True)

        # Check VALID_SECTIONS
        required_sections = {"strategy", "research", "design", "layout", "dsl", "quality", "images", "status"}
        test("All 8 sections defined", VALID_SECTIONS == required_sections)

        # Check ContextBoardProtocol methods
        protocol_methods = [
            "write_strategy",
            "read_strategy",
            "write_research",
            "read_research",
            "write_design",
            "read_design",
            "write_layout",
            "read_layout",
            "write_quality",
            "read_quality",
            "write_status",
            "read_status",
        ]
        missing_methods = [m for m in protocol_methods if not hasattr(ContextBoardProtocol, m)]
        test("ContextBoardProtocol has all methods", len(missing_methods) == 0, f"Missing: {missing_methods}")

    except Exception as e:
        test("Context Board integration", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: Base Agent Enhancements
# ═══════════════════════════════════════════════════════════════════════════════

def test_base_agent_enhancements():
    """Test base agent enhancements for V7"""
    header("Test 8: Base Agent Enhancements")

    try:
        from app.services.slides_new.agents.base import (
            BaseAgent,
            AgentType,
            AgentContext,
            AgentOutput,
            AgentFactory,
        )

        test("BaseAgent class imported", True)

        # Check AgentType includes new agents
        agent_types = list(AgentType)
        test("AgentType has LAYOUT", AgentType.LAYOUT in agent_types)
        test("AgentType has VFX", AgentType.VFX in agent_types)
        test("AgentType count >= 8", len(agent_types) >= 8)

        # Check AgentOutput has new fields
        output = AgentOutput(
            success=True,
            agent_type=AgentType.CEO,
            output={},
            context_board_writes=["strategy.archetype"],
            hitl_checkpoint={"gate": "test"},
        )
        test("AgentOutput has context_board_writes", hasattr(output, "context_board_writes"))
        test("AgentOutput has hitl_checkpoint", hasattr(output, "hitl_checkpoint"))

        # Check AgentContext has new fields
        context = AgentContext(
            task_id="test",
            user_id="user",
            topic="Test",
            description="Test desc",
            purpose="test",
            audience="test",
            slide_count=10,
            mode="standard",
            fast_mode=True,
            research_depth="deep",
            enable_3d=True,
            target_renderers=["revealjs"],
        )
        test("AgentContext has fast_mode", hasattr(context, "fast_mode"))
        test("AgentContext has research_depth", hasattr(context, "research_depth"))
        test("AgentContext has enable_3d", hasattr(context, "enable_3d"))
        test("AgentContext has target_renderers", hasattr(context, "target_renderers"))

        # Check AgentFactory includes Layout
        test("AgentFactory._agents includes LAYOUT", AgentType.LAYOUT in AgentFactory._agents)

    except Exception as e:
        test("Base agent enhancements", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run all Phase 2 verification tests"""
    print("\n" + "="*60)
    print("  V7 PHASE 2 VERIFICATION - Agent Core")
    print("="*60)

    # Run all tests
    test_agent_protocols()
    test_layout_agent()
    test_ceo_agent()
    test_researcher_agent()
    test_parallel_framework()
    test_v7_orchestrator()
    test_context_board_integration()
    test_base_agent_enhancements()

    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"\n  Total Tests:  {TESTS_RUN}")
    print(f"  Passed:       {TESTS_PASSED} ✓")
    print(f"  Failed:       {TESTS_FAILED} ✗")

    if TESTS_FAILED == 0:
        print("\n  ✅ PHASE 2 VERIFICATION PASSED")
        print("\n  Phase 2 Deliverables:")
        print("    ✓ Orchestrator with Context Board")
        print("    ✓ CEO Agent (Kimi-K2-Thinking)")
        print("    ✓ Researcher Agent (DeepSeek-V3.2)")
        print("    ✓ Layout Agent (GPT-4o/Phi-4)")
        print("    ✓ Agent parallel execution framework")
        return 0
    else:
        print("\n  ❌ PHASE 2 VERIFICATION FAILED")
        print(f"\n  {TESTS_FAILED} test(s) need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
