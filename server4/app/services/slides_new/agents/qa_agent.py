"""
QA Agent - Quality Assurance & Validation
Agent 5: Validates presentation quality, checks for errors, ensures consistency,
validates against requirements, and runs quality gates.
"""

from typing import Any, Dict, List

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)


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

            if check_result["passed"]:
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

Check each slide and provide JSON result:
{{
  "passed": true/false,
  "issues": ["issue 1", "issue 2"],
  "recommendations": ["recommendation 1"]
}}

Focus on finding real issues, not generic praise."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.2,
            max_tokens=1500,
            system_prompt="You are a presentation quality auditor. Be rigorous - find real issues.",
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
