"""
QA Agent - Quality Assurance & Validation (Phase 3 Enhanced)
Agent 5: Validates presentation quality, runs quality gates, provides
structured feedback for the self-evaluation loop.

Phase 3 additions:
- evaluate_slide() for per-slide QA in the evaluation loop
- Structured failure output (QAFeedback model)
- Regeneration trigger
- Iteration tracking
- Per-gate failure data for skill learning
"""

from typing import Any, Dict, List, Optional

import json
import structlog

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)
from app.services.slides_new.skills.models import QAFeedback

logger = structlog.get_logger()

class QAAgent(BaseAgent):
    """
    Agent 5: Quality assurance and validation.

    Responsibilities:
    - Validate presentation completeness
    - Check for factual errors
    - Verify consistency across slides
    - Validate against original requirements
    - Run quality gates
    - Provide feedback for improvements

    Implements multi-stage quality checks.
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    FALLBACK_MODELS = ["deepseek-v3", "mistral-medium"]

    QUALITY_GATES = {
        "content_completeness": {
            "description": "All slides have required content",
            "check": "slide has title and at least some content",
            "weight": 20,
        },
        "design_consistency": {
            "description": "Design system applied consistently",
            "check": "all slides use preset colors and fonts",
            "weight": 15,
        },
        "no_generic_content": {
            "description": "Content is specific, not generic",
            "check": "no placeholder text or generic statements",
            "weight": 20,
        },
        "factual_accuracy": {
            "description": "Data and statistics are properly sourced",
            "check": "all stats have sources",
            "weight": 15,
        },
        "visual_balance": {
            "description": "Slides have balanced visual hierarchy",
            "check": "headings and body text properly sized",
            "weight": 15,
        },
        "coherence": {
            "description": "Presentation flows logically",
            "check": "narrative arc makes sense",
            "weight": 15,
        },
    }

    # Extended anti-AI-slop phrase list for comprehensive detection
    CORPORATE_SLOP_PHRASES = [
        "in today's world", "cutting-edge", "game-changing", "revolutionary",
        "leverage", "synergy", "paradigm shift", "circle back",
        "move the needle", "low-hanging fruit", "think outside the box",
        "best-in-class", "world-class", "next-generation", "state-of-the-art",
        "robust solution", "scalable platform", "seamless integration",
        "holistic approach", "deep dive", "at the end of the day",
        "it goes without saying", "needless to say", "without further ado",
        "innovative solution", "disruptive technology", "value proposition",
    ]

    @property
    def agent_type(self) -> AgentType:
        return AgentType.QA

    async def execute(self) -> AgentOutput:
        """
        Execute QA Agent - validate presentation quality.

        Steps:
        1. Get assembled presentation
        2. Run automated quality gates
        3. Validate against requirements
        4. Check consistency and coherence
        5. Provide validation report
        6. If failed, mark for regeneration
        """
        self.log_progress("Starting QA Agent execution")

        # Get assembled presentation
        assembler_output = self.context.previous_outputs.get(AgentType.ASSEMBLER)
        if not assembler_output or not assembler_output.success:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=["Assembler output not available"],
            )

        presentation = assembler_output.output
        slides = presentation.get("slides", [])

        # Run quality checks
        quality_report = await self._run_quality_gates(presentation)

        # Check requirements
        requirements_check = self._validate_requirements(presentation)

        # Compile QA output
        qa_output = {
            "quality_score": quality_report["score"],
            "quality_grade": self._calculate_grade(quality_report["score"]),
            "gates_passed": quality_report["passed"],
            "gates_failed": quality_report["failed"],
            "gate_details": quality_report["details"],
            "requirements_met": requirements_check["met"],
            "requirements_missing": requirements_check["missing"],
            "issues": quality_report["issues"],
            "recommendations": quality_report["recommendations"],
            "passed": quality_report["score"] >= 70,
            "presentation": presentation if quality_report["score"] >= 70 else None,
        }

        self.log_progress(
            f"QA complete: {qa_output['quality_score']}% - {'PASSED' if qa_output['passed'] else 'FAILED'}"
        )

        warnings = []
        if not qa_output["passed"]:
            warnings.append(
                f"Quality gates failed - score: {qa_output['quality_score']}%"
            )

        return AgentOutput(
            success=True,
            agent_type=self.agent_type,
            output=qa_output,
            warnings=warnings,
        )

    async def _run_quality_gates(self, presentation: Dict) -> Dict[str, Any]:
        """Run all quality gates on presentation"""
        slides = presentation.get("slides", [])
        design = presentation.get("design_system", {})

        passed = []
        failed = []
        issues = []
        recommendations = []
        total_weight = 0
        earned_weight = 0

        for gate_name, gate_config in self.QUALITY_GATES.items():
            total_weight += gate_config["weight"]

            # Run the specific check
            check_result = await self._run_gate_check(
                gate_name, gate_config, slides, design
            )

            # Handle both old and new response formats
            if check_result.get("passed", True):
                passed.append(gate_name)
                earned_weight += gate_config["weight"]
            else:
                failed.append(gate_name)
                issues.extend(check_result.get("issues", []))
                recommendations.extend(check_result.get("recommendations", []))

        # Calculate score
        score = int((earned_weight / total_weight) * 100) if total_weight > 0 else 0

        return {
            "score": score,
            "passed": passed,
            "failed": failed,
            "details": {g: self.QUALITY_GATES[g] for g in passed + failed},
            "issues": issues,
            "recommendations": recommendations,
        }

    async def _run_gate_check(
        self, gate_name: str, gate_config: Dict, slides: List[Dict], design: Dict
    ) -> Dict[str, Any]:
        """Run a specific quality gate check"""
        prompt = f"""Run quality gate check: {gate_name}

GATE: {gate_config["description"]}
CHECK: {gate_config["check"]}

SLIDES COUNT: {len(slides)}
DESIGN PRESET: {design.get("preset", "unknown")}

## EVALUATION METHODOLOGY:
1. Check EVERY slide against this gate's criteria (not just a sample)
2. For each failing slide, provide the specific slide index and reason
3. Distinguish between CRITICAL issues (must fix) and MINOR issues (nice to have)
4. Score on a curve: 1-2 minor issues can still pass; 1+ critical issue fails

## ANTI-AI-SLOP DETECTION (for no_generic_content gate):
Flag these phrases: {", ".join(self.CORPORATE_SLOP_PHRASES[:10])}
Also flag: vague statistics without sources, placeholder text like "Lorem ipsum" or "Company X"

Check each slide and provide JSON result:
{{
  "passed": true/false,
  "issues": ["CRITICAL: slide 3 has no title", "MINOR: slide 5 uses generic phrasing"],
  "recommendations": ["recommendation 1"],
  "failing_slides": [3, 5]
}}

Be a tough but fair critic. Focus on finding real issues, not generic praise."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.2,
            max_tokens=1500,
            system_prompt="You are a world-class presentation quality auditor who has reviewed decks for YC Demo Day, Sequoia Capital, and TED. You have zero tolerance for generic content, placeholder data, or AI-generated filler. Every slide must earn its place. Be rigorous — real quality comes from honest feedback.",
        )

        if result.success:
            return result.output

        # Default pass if check fails
        return {"passed": True, "issues": [], "recommendations": []}

    def _validate_requirements(self, presentation: Dict) -> Dict[str, Any]:
        """Validate presentation meets original requirements"""
        met = []
        missing = []

        # Check slide count
        slide_count = presentation.get("metadata", {}).get("slide_count", 0)
        if slide_count > 0:
            met.append(f"slide_count: {slide_count}")
        else:
            missing.append("slide_count")

        # Check required sections
        slides = presentation.get("slides", [])
        if len(slides) > 0:
            met.append("has_slides")
        else:
            missing.append("slides")

        # Check design system
        if presentation.get("design_system"):
            met.append("has_design_system")
        else:
            missing.append("design_system")

        return {"met": met, "missing": missing}

    def _calculate_grade(self, score: int) -> str:
        """Calculate letter grade from score"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    # ── PHASE 3: Per-Slide Evaluation for Self-Eval Loop ──────

    async def evaluate_slide(
        self,
        dsl_result: Any,
        slide_type: str,
        slide_brief: Dict[str, Any],
    ) -> QAFeedback:
        """
        Evaluate a single slide's DSL output for the evaluation loop.

        Returns structured QAFeedback that the skill system uses to:
        - Record success (best examples)
        - Record failure (failure patterns)
        - Decide whether to regenerate

        Uses LLM to run quality checks on a single slide.
        """
        if dsl_result is None or not dsl_result.success:
            return QAFeedback(
                score=0.0,
                grade="F",
                issues=["DSL generation failed"],
                regenerate=True,
            )

        dsl = dsl_result.dsl
        if dsl is None:
            return QAFeedback(
                score=0.0,
                grade="F",
                issues=["No valid DSL object"],
                regenerate=True,
            )

        # Run LLM-based quality evaluation
        prompt = f"""Evaluate this slide DSL output for quality.

## Slide Type: {slide_type}
## Original Brief:
```json
{json.dumps(slide_brief, indent=2) if isinstance(slide_brief, dict) else str(slide_brief)}
```

## Generated DSL:
```json
{dsl_result.raw_json or ""}
```

## Quality Gates to Check:
1. content_completeness (20%): Slide has title and relevant content
2. design_consistency (15%): Layout matches slide type expectations
3. no_generic_content (20%): Content is specific, not AI filler
4. factual_accuracy (15%): Data/stats are plausible with sources
5. visual_balance (15%): Content fills layout without overcrowding
6. coherence (15%): Content matches the brief and flows logically

## Output JSON format:
{{
  "score": 0-100,
  "grade": "A-F",
  "gates_passed": ["gate1", "gate2"],
  "gates_failed": ["gate3"],
  "issues": ["issue 1", "issue 2"],
  "recommendations": ["fix 1", "fix 2"],
  "regenerate": true/false,
  "structured_failures": [
    {{"gate": "gate_name", "reason": "why it failed", "suggestion": "how to fix"}}
  ]
}}

Be rigorous. Score honestly. If content is generic or missing, fail it."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.2,
            max_tokens=2048,
            system_prompt=(
                "You are a slide quality auditor. Score each gate rigorously. "
                "Output ONLY valid JSON matching the specified format."
            ),
        )

        if result.success and isinstance(result.output, dict):
            return QAFeedback(
                score=float(result.output.get("score", 50)),
                grade=str(result.output.get("grade", "C")),
                gates_passed=result.output.get("gates_passed", []),
                gates_failed=result.output.get("gates_failed", []),
                issues=result.output.get("issues", []),
                recommendations=result.output.get("recommendations", []),
                regenerate=result.output.get("regenerate", False),
                structured_failures=result.output.get(
                    "structured_failures", []
                ),
            )

        # Fallback: structural evaluation without LLM
        return self._structural_slide_eval(dsl, slide_type, slide_brief)

    def _structural_slide_eval(
        self,
        dsl: Any,
        slide_type: str,
        slide_brief: Dict[str, Any],
    ) -> QAFeedback:
        """Structural slide evaluation without LLM (fallback)."""
        score = 100.0
        gates_passed: List[str] = []
        gates_failed: List[str] = []
        issues: List[str] = []
        structured_failures: List[Dict[str, str]] = []

        content = dsl.content

        # Gate 1: content_completeness
        if not content.title or not content.title.strip():
            score -= 25
            gates_failed.append("content_completeness")
            issues.append("Missing title")
            structured_failures.append({
                "gate": "content_completeness",
                "reason": "No title",
                "suggestion": "Add a concise title",
            })
        else:
            gates_passed.append("content_completeness")

        # Gate 2: no_generic_content
        generic_phrases = [
            "in today's world",
            "game-changing",
            "revolutionary",
            "cutting-edge",
            "leverage",
            "synergy",
            "paradigm shift",
            "circle back",
            "move the needle",
            "best-in-class",
            "world-class",
            "next-generation",
            "state-of-the-art",
            "seamless integration",
            "holistic approach",
            "innovative solution",
            "disruptive technology",
        ]
        title_lower = (content.title or "").lower()
        body_lower = (content.body_text or "").lower()
        for phrase in generic_phrases:
            if phrase in title_lower or phrase in body_lower:
                score -= 5
                if "no_generic_content" not in gates_failed:
                    gates_failed.append("no_generic_content")
                    issues.append(f"Generic AI phrase detected: '{phrase}'")
                    structured_failures.append({
                        "gate": "no_generic_content",
                        "reason": f"Contains '{phrase}'",
                        "suggestion": "Replace with specific language",
                    })
        if "no_generic_content" not in gates_failed:
            gates_passed.append("no_generic_content")

        # Gate 3: visual_balance
        has_substance = bool(
            content.bullets
            or content.body_text
            or content.chart_data
            or content.kpi_metrics
            or content.team_members
            or content.timeline_items
        )
        if not has_substance:
            score -= 15
            gates_failed.append("visual_balance")
            issues.append("No substantive content")
        else:
            gates_passed.append("visual_balance")

        # Gate 4: coherence (speaker notes)
        if not dsl.speakerNotes or len(dsl.speakerNotes.strip()) < 20:
            score -= 10
            issues.append("Missing or short speaker notes")
        else:
            gates_passed.append("coherence")

        score = max(0.0, min(100.0, score))
        grade = self._calculate_grade(int(score))

        return QAFeedback(
            score=score,
            grade=grade,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            issues=issues,
            recommendations=[],
            regenerate=score < 85.0,
            structured_failures=structured_failures,
        )

    async def check_cross_slide_coherence(
        self, slides: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Cross-slide coherence check — validates narrative flow across ALL slides.

        Checks:
        1. Do slide titles form a logical progression?
        2. Are there data contradictions between slides?
        3. Is there content repetition or redundancy?
        4. Does the narrative arc build to a climax?
        5. Is the ask/CTA properly set up by preceding slides?
        """
        if not slides or len(slides) < 3:
            return {"coherent": True, "issues": [], "score": 100}

        titles = [s.get("title", s.get("purpose", f"Slide {i}"))
                  for i, s in enumerate(slides)]

        prompt = f"""Evaluate this presentation's cross-slide coherence.

SLIDE TITLES (in order):
{json.dumps(titles, indent=2)}

## CHECK THESE DIMENSIONS:
1. **Narrative Flow**: Do these slides tell a story with a beginning, middle, and climax?
2. **Logical Progression**: Would a skeptical audience follow this order without confusion?
3. **Data Consistency**: Could any slide contradict or undermine another?
4. **Redundancy**: Are any slides saying the same thing twice?
5. **Build-Up**: Does the presentation properly set up its conclusion/ask?
6. **Attention Curve**: Is the strongest content placed where attention peaks (slides 2-4)?

Output JSON:
{{
  "coherent": true/false,
  "narrative_score": 0-100,
  "issues": ["specific issue 1", "specific issue 2"],
  "suggested_reorder": [0, 1, 2, 3] or null if order is fine,
  "redundant_slides": [] or [indices of redundant slides],
  "attention_peak_slide": index of the most impactful slide
}}

Be specific. Don't just say "good flow" — explain why or where it breaks."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.2,
            max_tokens=1500,
            system_prompt="You are a presentation narrative expert who reviews decks for consistent story flow. Think like an audience member seeing these slides for the first time.",
        )

        if result.success and isinstance(result.output, dict):
            return result.output

        return {"coherent": True, "issues": [], "score": 80}

    def detect_corporate_slop(self, text: str) -> List[str]:
        """Detect and return all corporate jargon/AI slop phrases found in text."""
        text_lower = text.lower()
        return [phrase for phrase in self.CORPORATE_SLOP_PHRASES
                if phrase in text_lower]
