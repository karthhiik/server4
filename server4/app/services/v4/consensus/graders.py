"""
V4 Consensus — parallel binary graders.

Based on LangGraph CRAG: a retrieval-augmented answer is graded with a
binary_score model (pass/fail) before being shipped. We run three graders
in parallel against the final consensus draft:

    * Fact grader       — gpt-4o-mini      (fast, good at citation checks)
    * Design grader     — cf-glm           (design-token aware)
    * Narrative grader  — deepseek-v3      (thesis/narrative coherence)

If ANY grader returns pass=false, we trigger ONE regeneration pass (pass
the grader issues back to the aggregator). After that, we ship even if
graders still fail — but we stamp ``council_degraded=true`` so the caller
knows quality fell below the bar.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.consensus.prompts import (
    DESIGN_GRADER_SYSTEM,
    FACT_GRADER_SYSTEM,
    NARRATIVE_GRADER_SYSTEM,
    build_grader_user_message,
)
from app.services.v4.llm_safe import safe_complete

logger = structlog.get_logger(__name__)


@dataclass
class GraderVerdict:
    name: str
    passed: bool = False
    score: int = 0
    reason: str = ""
    issues: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.passed and self.score >= 3


def _parse_grader_json(raw: str, name: str) -> dict[str, Any]:
    """Parse grader output; fall back to pass=True if unparseable (we don't
    want grader failures to kill the pipeline — they're advisory)."""
    if not raw:
        return {"pass": True, "score": 3, "reason": f"{name}: empty response"}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Extract first {...} block as a last-ditch attempt
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return {"pass": True, "score": 3, "reason": f"{name}: unparseable"}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"pass": True, "score": 3, "reason": f"{name}: unparseable"}
    if not isinstance(data, dict):
        return {"pass": True, "score": 3, "reason": f"{name}: non-object"}
    return data


async def _run_one_grader(
    *,
    router: ModelRouter,
    task: TaskType,
    system: str,
    user_msg: str,
    project_id: str,
    phase: str,
    timeout_s: float,
    name: str,
) -> GraderVerdict:
    try:
        resp = await safe_complete(
            router=router,
            primary_task=task,
            # Founder fix (Apr 2026): graders never fall back to a
            # classifier model — a rubric judge needs reasoning, not
            # intent-class detection. REFINEMENT chain is gpt-4o-mini /
            # mistral-medium / nv-glm-4.7, all suited to scoring tasks.
            fallback_task=TaskType.REFINEMENT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
            presentation_id=project_id,
            phase=phase,
            timeout_s=timeout_s,
            fallback_timeout_s=max(4.0, timeout_s * 0.6),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("consensus_grader_failed",
                       name=name, error=str(e)[:200])
        return GraderVerdict(name=name, passed=True, score=3,
                             reason=f"grader_error: {type(e).__name__}")

    data = _parse_grader_json(resp.content or "", name)
    passed = bool(data.get("pass", True))
    score = int(data.get("score", 3)) if isinstance(data.get("score"), (int, float)) else 3
    issues_raw = (
        data.get("issues")
        or data.get("unsupported_claims")
        or data.get("problems")
        or []
    )
    issues = [str(x) for x in issues_raw if x][:6] if isinstance(issues_raw, list) else []

    return GraderVerdict(
        name=name,
        passed=passed,
        score=max(0, min(5, score)),
        reason=str(data.get("reason", ""))[:240],
        issues=issues,
        raw=data,
    )


async def run_graders_parallel(
    *,
    router: ModelRouter,
    draft_json: str,
    scoped_evidence: str,
    skeleton_json: str,
    design_context: str,
    project_id: str,
    phase: str,
    budget_s: float = 10.0,
) -> list[GraderVerdict]:
    """Run fact + design + narrative graders in parallel under a wall-clock
    budget. Graders that exceed their share of the budget return a neutral
    pass verdict so they don't block shipping."""
    per_grader_timeout = max(3.0, budget_s)

    user_msg = build_grader_user_message(
        draft_json=draft_json,
        scoped_evidence=scoped_evidence,
        skeleton_json=skeleton_json,
        design_context=design_context,
    )

    fact_task = _run_one_grader(
        router=router,
        task=TaskType.REFINEMENT,
        system=FACT_GRADER_SYSTEM,
        user_msg=user_msg,
        project_id=project_id,
        phase=f"{phase}_grader_fact",
        timeout_s=per_grader_timeout,
        name="fact",
    )
    design_task = _run_one_grader(
        router=router,
        task=TaskType.REFINEMENT,
        system=DESIGN_GRADER_SYSTEM,
        user_msg=user_msg,
        project_id=project_id,
        phase=f"{phase}_grader_design",
        timeout_s=per_grader_timeout,
        name="design",
    )
    narrative_task = _run_one_grader(
        router=router,
        task=TaskType.REFINEMENT,
        system=NARRATIVE_GRADER_SYSTEM,
        user_msg=user_msg,
        project_id=project_id,
        phase=f"{phase}_grader_narrative",
        timeout_s=per_grader_timeout,
        name="narrative",
    )

    try:
        verdicts = await asyncio.wait_for(
            asyncio.gather(fact_task, design_task, narrative_task,
                           return_exceptions=True),
            timeout=budget_s + 2.0,  # small grace period beyond per-grader cap
        )
    except asyncio.TimeoutError:
        logger.warning("consensus_grader_bundle_timeout", phase=phase)
        return [
            GraderVerdict(name="fact", passed=True, score=3, reason="bundle_timeout"),
            GraderVerdict(name="design", passed=True, score=3, reason="bundle_timeout"),
            GraderVerdict(name="narrative", passed=True, score=3, reason="bundle_timeout"),
        ]

    out: list[GraderVerdict] = []
    defaults = ["fact", "design", "narrative"]
    for i, v in enumerate(verdicts):
        if isinstance(v, BaseException):
            out.append(GraderVerdict(name=defaults[i], passed=True, score=3,
                                     reason=f"exception: {type(v).__name__}"))
        else:
            out.append(v)
    return out


def any_failed(verdicts: list[GraderVerdict]) -> bool:
    return any(not v.passed or v.score < 3 for v in verdicts)


def consolidated_issues(verdicts: list[GraderVerdict]) -> list[str]:
    """Flatten all grader issues into one bulleted list the aggregator
    can use on the regeneration pass."""
    out: list[str] = []
    for v in verdicts:
        if v.ok:
            continue
        tag = v.name
        if v.reason:
            out.append(f"[{tag}] {v.reason}")
        for i in v.issues:
            out.append(f"[{tag}] {i}")
    # dedupe, keep order
    seen: set[str] = set()
    dedup: list[str] = []
    for s in out:
        k = s.lower().strip()
        if k and k not in seen:
            seen.add(k)
            dedup.append(s)
    return dedup[:12]
