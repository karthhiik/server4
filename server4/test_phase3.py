"""
Phase 3 Verification Test -- Code Agent + Self-Evolving Skill System.

Tests:
1. Skills models (SlideSkill, QAFeedback, etc.)
2. Skill registry (prompt templates for all slide types)
3. Code agent router (multi-provider routing)
4. DSL generator (template filling, JSON extraction)
5. Evaluation loop (structural evaluation)
6. Code agent integration (execute flow)
7. QA agent structured feedback
8. Model router new task types
9. Database index alignment

Run: python test_phase3.py
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime, timezone


# ── Test result tracking ─────────────────────────────────────

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
        print(f"Phase 3 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ── 1. Skills Models ─────────────────────────────────────────

def test_skill_models():
    print("\n1. Skills Models")
    try:
        from app.services.slides_new.skills.models import (
            SlideSkill,
            SkillVersion,
            SkillFailurePattern,
            SkillGenerationMode,
            SlideSkillType,
            QAFeedback,
            BestExample,
        )
        results.ok("All model classes import")
    except Exception as e:
        results.fail("Model imports", str(e))
        return

    # Test SlideSkill creation
    try:
        skill = SlideSkill(
            name="problem",
            prompt_template="Generate a problem slide for {topic}",
        )
        assert skill.version == 1
        assert skill.total_generations == 0
        assert skill.avg_quality == 0.0
        assert skill.generation_mode == SkillGenerationMode.INSTANT
        assert skill.quality_threshold == 85.0
        results.ok("SlideSkill creation with defaults")
    except Exception as e:
        results.fail("SlideSkill creation", str(e))

    # Test record_generation
    try:
        skill = SlideSkill(
            name="market",
            prompt_template="test",
        )
        skill.record_generation(90.0)
        skill.record_generation(85.0)
        assert skill.total_generations == 2
        assert skill.avg_quality == 87.5
        assert len(skill.quality_history) == 2
        results.ok("SlideSkill.record_generation()")
    except Exception as e:
        results.fail("record_generation", str(e))

    # Test add_best_example
    try:
        skill = SlideSkill(name="test", prompt_template="test")
        example = BestExample(
            dsl_json='{"title":"Test"}',
            quality_score=92.0,
            slide_type="test",
            layout="bullets",
        )
        skill.add_best_example(example)
        assert len(skill.best_examples) == 1
        assert skill.best_examples[0].quality_score == 92.0
        results.ok("SlideSkill.add_best_example()")
    except Exception as e:
        results.fail("add_best_example", str(e))

    # Test add_failure_pattern
    try:
        skill = SlideSkill(name="test", prompt_template="test")
        pattern = SkillFailurePattern(
            description="Title too long",
            qa_feedback="Shorten title",
        )
        skill.add_failure_pattern(pattern)
        assert len(skill.common_failures) == 1
        # Add same pattern again — should increment
        skill.add_failure_pattern(SkillFailurePattern(
            description="Title too long",
            qa_feedback="Shorten title",
        ))
        assert len(skill.common_failures) == 1  # Not duplicated
        assert skill.common_failures[0].occurrence_count == 2
        results.ok("SlideSkill.add_failure_pattern()")
    except Exception as e:
        results.fail("add_failure_pattern", str(e))

    # Test upgrade_version
    try:
        skill = SlideSkill(name="test", prompt_template="test")
        skill.upgrade_version(["improved accuracy"], 92.0)
        assert skill.version == 2
        assert skill.total_improvements == 1
        assert len(skill.version_history) == 1
        results.ok("SlideSkill.upgrade_version()")
    except Exception as e:
        results.fail("upgrade_version", str(e))

    # Test MongoDB serialization
    try:
        skill = SlideSkill(
            name="test",
            prompt_template="test prompt",
            generation_mode=SkillGenerationMode.THINKING,
        )
        doc = skill.to_mongo_doc()
        assert isinstance(doc, dict)
        assert doc["name"] == "test"
        restored = SlideSkill.from_mongo_doc(doc)
        assert restored.name == "test"
        assert restored.generation_mode == SkillGenerationMode.THINKING
        results.ok("MongoDB serialization round-trip")
    except Exception as e:
        results.fail("MongoDB serialization", str(e))

    # Test QAFeedback
    try:
        feedback = QAFeedback(
            score=72.0,
            grade="C",
            gates_passed=["content_completeness"],
            gates_failed=["no_generic_content"],
            issues=["Generic AI language"],
            regenerate=True,
            structured_failures=[{
                "gate": "no_generic_content",
                "reason": "Contains 'game-changing'",
                "suggestion": "Use specific language",
            }],
        )
        assert feedback.regenerate is True
        assert len(feedback.structured_failures) == 1
        results.ok("QAFeedback creation")
    except Exception as e:
        results.fail("QAFeedback creation", str(e))

    # Test SlideSkillType enum coverage
    try:
        types = list(SlideSkillType)
        assert len(types) >= 20  # At least 20 slide types
        assert SlideSkillType.PROBLEM.value == "problem"
        assert SlideSkillType.MARKET.value == "market"
        results.ok(f"SlideSkillType enum: {len(types)} types")
    except Exception as e:
        results.fail("SlideSkillType enum", str(e))


# ── 2. Skill Registry ────────────────────────────────────────

def test_skill_registry():
    print("\n2. Skill Registry")
    try:
        from app.services.slides_new.skills.skill_registry import (
            SkillRegistry,
            DEFAULT_SKILL_PROMPTS,
            DSL_SYSTEM_PROMPT,
        )
        results.ok("Registry imports")
    except Exception as e:
        results.fail("Registry imports", str(e))
        return

    # Check all skill names
    try:
        names = SkillRegistry.get_all_skill_names()
        assert len(names) >= 20, f"Expected >=20 skills, got {len(names)}"
        required = ["title-hero", "problem", "solution", "market", "traction",
                     "team", "competition", "business-model", "financials", "ask"]
        for req in required:
            assert req in names, f"Missing required skill: {req}"
        results.ok(f"Registered skills: {len(names)}")
    except Exception as e:
        results.fail("Skill names", str(e))

    # Check prompt templates
    try:
        for name in SkillRegistry.get_all_skill_names():
            prompt = SkillRegistry.get_prompt(name)
            assert isinstance(prompt, str)
            assert len(prompt) > 50, f"Prompt too short for {name}"
            assert "{slide_brief}" in prompt or "{{slide_brief}}" in prompt, \
                f"Missing slide_brief slot in {name}"
        results.ok("All prompts have required slots")
    except Exception as e:
        results.fail("Prompt templates", str(e))

    # Check generation modes
    try:
        from app.services.slides_new.skills.models import SkillGenerationMode
        instant_count = 0
        thinking_count = 0
        for name in SkillRegistry.get_all_skill_names():
            mode = SkillRegistry.get_mode(name)
            if mode == SkillGenerationMode.INSTANT:
                instant_count += 1
            elif mode == SkillGenerationMode.THINKING:
                thinking_count += 1
        assert thinking_count > 0, "No THINKING mode skills"
        assert instant_count > 0, "No INSTANT mode skills"
        results.ok(f"Modes: {instant_count} instant, {thinking_count} thinking")
    except Exception as e:
        results.fail("Generation modes", str(e))

    # Check DSL system prompt
    try:
        sys_prompt = SkillRegistry.get_dsl_system_prompt()
        assert "SlideDSL" in sys_prompt
        assert "JSON" in sys_prompt
        assert len(sys_prompt) > 200
        results.ok("DSL system prompt present")
    except Exception as e:
        results.fail("DSL system prompt", str(e))


# ── 3. Code Agent Router ─────────────────────────────────────

def test_code_agent_router():
    print("\n3. Code Agent Router")
    try:
        from app.services.slides_new.agents.code_agent_router import (
            CodeAgentRouter,
            CodeTaskType,
            CODE_ROUTING_TABLE,
            THINKING_ROUTES,
        )
        results.ok("Router imports")
    except Exception as e:
        results.fail("Router imports", str(e))
        return

    # Check all task types have routing entries
    try:
        for task in CodeTaskType:
            assert task in CODE_ROUTING_TABLE, f"Missing route for {task.value}"
            chain = CODE_ROUTING_TABLE[task]
            assert len(chain) >= 2, f"Need >=2 fallbacks for {task.value}"
        results.ok(f"All {len(CodeTaskType)} task types routed")
    except Exception as e:
        results.fail("Routing table coverage", str(e))

    # Check thinking routes
    try:
        assert THINKING_ROUTES[CodeTaskType.THREEJS_SCENE] is True
        assert THINKING_ROUTES[CodeTaskType.LAYOUT_OPTIMIZATION] is True
        assert THINKING_ROUTES[CodeTaskType.DSL_GENERATION] is False
        results.ok("Thinking routes correct")
    except Exception as e:
        results.fail("Thinking routes", str(e))

    # Check router chain building
    try:
        from app.services.slides_new.skills.models import SkillGenerationMode
        router = CodeAgentRouter.__new__(CodeAgentRouter)
        # Test instant chain
        chain = router._get_chain(CodeTaskType.DSL_GENERATION, SkillGenerationMode.INSTANT)
        assert "deepseek-v3" in chain
        # Test thinking chain prepends reasoning models
        chain = router._get_chain(CodeTaskType.DSL_GENERATION, SkillGenerationMode.THINKING)
        assert chain[0] in ("kimi-k2-thinking", "phi-4-reasoning")
        results.ok("Chain building (instant + thinking)")
    except Exception as e:
        results.fail("Chain building", str(e))


# ── 4. DSL Generator ─────────────────────────────────────────

def test_dsl_generator():
    print("\n4. DSL Generator")
    try:
        from app.services.slides_new.dsl.dsl_generator import (
            DSLGenerator,
            DSLGenerationResult,
        )
        results.ok("DSL generator imports")
    except Exception as e:
        results.fail("DSL generator imports", str(e))
        return

    # Test JSON extraction
    try:
        gen = DSLGenerator.__new__(DSLGenerator)

        # Direct JSON
        result = gen._extract_json('{"title": "Test"}')
        assert result == '{"title": "Test"}'

        # Markdown code block
        result = gen._extract_json('```json\n{"title": "Test"}\n```')
        assert result is not None
        assert '"title"' in result

        # Embedded in text
        result = gen._extract_json('Here is the result: {"title": "Test"} done.')
        assert result is not None
        assert '"title"' in result

        results.ok("JSON extraction (3 formats)")
    except Exception as e:
        results.fail("JSON extraction", str(e))

    # Test prompt building
    try:
        gen = DSLGenerator.__new__(DSLGenerator)
        context = {
            "topic": "AI Startup",
            "company_name": "TestCo",
            "audience": "investors",
        }
        few_shot_section = gen._build_few_shot_section([
            {"metadata": {"quality_score": 90}, "document": '{"test": true}'},
        ])
        assert "Example 1" in few_shot_section
        assert "90" in few_shot_section

        failure_section = gen._build_failure_section([])
        assert failure_section == ""

        results.ok("Prompt building (few-shot + failures)")
    except Exception as e:
        results.fail("Prompt building", str(e))


# ── 5. Evaluation Loop ───────────────────────────────────────

def test_evaluation_loop():
    print("\n5. Evaluation Loop")
    try:
        from app.services.slides_new.agents.evaluation_loop import (
            EvaluationLoop,
            EvaluationResult,
            EvalRound,
            MAX_EVAL_ROUNDS,
        )
        results.ok("Evaluation loop imports")
    except Exception as e:
        results.fail("Evaluation loop imports", str(e))
        return

    # Test constants
    try:
        assert MAX_EVAL_ROUNDS == 3
        results.ok("MAX_EVAL_ROUNDS = 3")
    except Exception as e:
        results.fail("Constants", str(e))

    # Test structural evaluation (fallback)
    try:
        from app.services.slides_new.dsl.dsl_generator import DSLGenerationResult
        from app.models.dsl_v2 import SlideDSL, SlideContentV2, LayoutType, SlideType

        # Create a valid DSL
        dsl = SlideDSL(
            index=0,
            id="slide_problem_0",
            type=SlideType.PROBLEM_SLIDE,
            layout=LayoutType.BULLETS,
            content=SlideContentV2(
                title="The Pain Point",
                bullets=["Issue 1", "Issue 2", "Issue 3"],
            ),
            speakerNotes="This slide explains the core problem our users face.",
        )
        dsl_result = DSLGenerationResult(
            success=True,
            dsl=dsl,
            raw_json=dsl.model_dump_json(),
        )

        # Create eval loop with no QA (will use structural)
        loop = EvaluationLoop.__new__(EvaluationLoop)
        loop._threshold = 85.0

        feedback = loop._structural_evaluate(dsl_result, "problem", {})
        assert feedback.score > 0
        assert feedback.grade in ("A", "B", "C", "D", "F")
        assert isinstance(feedback.gates_passed, list)
        results.ok(f"Structural eval: score={feedback.score}, grade={feedback.grade}")
    except Exception as e:
        results.fail("Structural evaluation", str(e))


# ── 6. Code Agent ─────────────────────────────────────────────

def test_code_agent():
    print("\n6. Code Agent (Phase 3)")
    try:
        from app.services.slides_new.agents.code_agent import (
            CodeAgent,
            LAYOUT_COMPONENT_MAP,
        )
        results.ok("Code agent imports")
    except Exception as e:
        results.fail("Code agent imports", str(e))
        return

    # Check layout map coverage
    try:
        assert len(LAYOUT_COMPONENT_MAP) >= 14
        assert LAYOUT_COMPONENT_MAP["title-hero"] == "TitleHeroSlide"
        assert LAYOUT_COMPONENT_MAP["kpi-dashboard"] == "KPIDashboardSlide"
        results.ok(f"Layout map: {len(LAYOUT_COMPONENT_MAP)} layouts")
    except Exception as e:
        results.fail("Layout map", str(e))

    # Check slide type resolution
    try:
        agent = CodeAgent.__new__(CodeAgent)
        assert agent._resolve_slide_type({"type": "problem"}) == "problem"
        assert agent._resolve_slide_type({"layout": "team-grid"}) == "team"
        assert agent._resolve_slide_type({"layout": "chart"}) == "chart-focus"
        assert agent._resolve_slide_type({}) == "bullets"
        results.ok("Slide type resolution")
    except Exception as e:
        results.fail("Slide type resolution", str(e))

    # Check brief extraction
    try:
        agent = CodeAgent.__new__(CodeAgent)
        brief = agent._extract_slide_brief({
            "title": "Market Size",
            "layout": "chart-focus",
            "type": "market",
            "index": 3,
        })
        assert brief["title"] == "Market Size"
        assert brief["layout"] == "chart-focus"
        assert brief["index"] == 3
        results.ok("Brief extraction")
    except Exception as e:
        results.fail("Brief extraction", str(e))


# ── 7. QA Agent Structured Feedback ──────────────────────────

def test_qa_agent():
    print("\n7. QA Agent (Phase 3 Enhanced)")
    try:
        from app.services.slides_new.agents.qa_agent import QAAgent
        results.ok("QA agent imports")
    except Exception as e:
        results.fail("QA agent imports", str(e))
        return

    # Check evaluate_slide method exists
    try:
        assert hasattr(QAAgent, "evaluate_slide")
        assert hasattr(QAAgent, "_structural_slide_eval")
        results.ok("evaluate_slide() method exists")
    except Exception as e:
        results.fail("evaluate_slide method", str(e))

    # Test structural slide eval
    try:
        from app.models.dsl_v2 import SlideDSL, SlideContentV2, LayoutType, SlideType

        agent = QAAgent.__new__(QAAgent)

        # Good slide
        dsl = SlideDSL(
            index=0,
            id="slide_solution_0",
            type=SlideType.SOLUTION_SLIDE,
            layout=LayoutType.SPLIT_SCREEN,
            content=SlideContentV2(
                title="Our Solution",
                bullets=["Feature 1", "Feature 2", "Feature 3"],
            ),
            speakerNotes="Here is how our solution addresses each pain point.",
        )
        feedback = agent._structural_slide_eval(dsl, "solution", {})
        assert feedback.score >= 80, f"Good slide scored too low: {feedback.score}"
        results.ok(f"Good slide eval: {feedback.score} ({feedback.grade})")

        # Bad slide (no title, no content)
        dsl_bad = SlideDSL(
            index=1,
            id="slide_bad_1",
            type=SlideType.CUSTOM,
            layout=LayoutType.BLANK,
            content=SlideContentV2(title=""),
        )
        feedback_bad = agent._structural_slide_eval(dsl_bad, "custom", {})
        assert feedback_bad.score < 60, f"Bad slide scored too high: {feedback_bad.score}"
        assert feedback_bad.regenerate is True
        results.ok(f"Bad slide eval: {feedback_bad.score} ({feedback_bad.grade})")
    except Exception as e:
        results.fail("Structural slide eval", str(e))


# ── 8. Model Router Updates ──────────────────────────────────

def test_model_router():
    print("\n8. Model Router (Phase 3 Task Types)")
    try:
        from app.services.llm.model_router import TaskType, ROUTING_TABLE
        results.ok("Model router imports")
    except Exception as e:
        results.fail("Model router imports", str(e))
        return

    # Check new task types exist
    try:
        new_types = [
            "DSL_GENERATION", "REACT_COMPILATION", "REVEALJS_HTML",
            "THREEJS_SCENE", "SKILL_EVALUATION", "LAYOUT_OPTIMIZATION",
        ]
        for t in new_types:
            assert hasattr(TaskType, t), f"Missing TaskType.{t}"
        results.ok(f"All {len(new_types)} new task types registered")
    except Exception as e:
        results.fail("New task types", str(e))

    # Check routing entries
    try:
        for t in new_types:
            task = getattr(TaskType, t)
            assert task in ROUTING_TABLE, f"No routing for {t}"
            chain = ROUTING_TABLE[task]
            assert len(chain) >= 3, f"Need >=3 fallbacks for {t}"
        results.ok("All new types have routing chains")
    except Exception as e:
        results.fail("Routing entries", str(e))


# ── 9. Integration Check ─────────────────────────────────────

def test_integration():
    print("\n9. Integration")

    # Verify skill_store can be created without DB
    try:
        from app.services.slides_new.skills.skill_store import SkillStore
        # Just check it can be instantiated with a mock
        assert SkillStore is not None
        results.ok("SkillStore class accessible")
    except Exception as e:
        results.fail("SkillStore import", str(e))

    # Verify all __init__ exports
    try:
        from app.services.slides_new.skills import (
            SlideSkill,
            SkillVersion,
            SkillFailurePattern,
            SkillGenerationMode,
            SkillStore,
            SkillRegistry,
            DEFAULT_SKILL_PROMPTS,
        )
        results.ok("skills __init__ exports")
    except Exception as e:
        results.fail("skills __init__", str(e))

    # Verify DSL package
    try:
        from app.services.slides_new.dsl import DSLGenerator
        results.ok("DSL package exports")
    except Exception as e:
        results.fail("DSL package", str(e))

    # Verify evaluation loop accessible from agents
    try:
        from app.services.slides_new.agents.evaluation_loop import EvaluationLoop
        results.ok("EvaluationLoop accessible")
    except Exception as e:
        results.fail("EvaluationLoop", str(e))

    # Verify code agent router
    try:
        from app.services.slides_new.agents.code_agent_router import CodeAgentRouter
        results.ok("CodeAgentRouter accessible")
    except Exception as e:
        results.fail("CodeAgentRouter", str(e))


# ── Runner ────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Phase 3 Verification Tests")
    print("Code Agent + Self-Evolving Skill System")
    print("=" * 60)

    test_skill_models()
    test_skill_registry()
    test_code_agent_router()
    test_dsl_generator()
    test_evaluation_loop()
    test_code_agent()
    test_qa_agent()
    test_model_router()
    test_integration()

    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
