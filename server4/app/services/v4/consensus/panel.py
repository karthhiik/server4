"""
V4 Consensus — Panel orchestrator.

Two operating modes:

STANDARD (15s budget)
    1. writer draft A     — deepseek-v3  (NARRATIVE_STORYTELLING)
    2. critic             — gpt-4o-mini  (REFINEMENT)      — binary verdict
    3. IF any score < 4: writer draft B with fixes         — deepseek-v3 again
    4. judge picks winner — nv-step-3.5-flash              — fast tiebreaker

PREMIUM (25s budget)
    1. Parallel persona drafts (3–4 drafters via asyncio.gather)
         P1 Visionary   — NARRATIVE_STORYTELLING  (kimi-k2-thinking chain)
         P2 Analyst     — GENERAL                 (deepseek-v3 chain)
         P3 Designer    — VISUAL_COMPOSITION      (nv-glm-4.7 chain)
         P4 Investor    — OUTLINE_PLANNING        (gpt-oss-120b chain, optional)
    2. Debate round (construct_message pattern)
    3. Aggregator         — mistral-medium        (REFINEMENT)
    4. Parallel graders (fact + design + narrative)
    5. ONE regen pass if any grader fails, then ship

Quorum rule: if fewer than 2 drafters return successfully, degrade to
standard mode mid-flight (don't fail — real-time UX is paramount).

Every step is wrapped in asyncio.wait_for with a per-stage cap that sums to
the mode's outer budget. If the outer budget is exceeded, we return whatever
we have with ``council_degraded=True``.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.consensus import graders as grader_mod
from app.services.v4.consensus.prompts import (
    AGGREGATOR_SYSTEM,
    ANALYST_SYSTEM,
    DEBATE_SYSTEM,
    DESIGNER_SYSTEM,
    INVESTOR_SYSTEM,
    STANDARD_CRITIC_SYSTEM,
    STANDARD_JUDGE_SYSTEM,
    STANDARD_WRITER_SYSTEM,
    VISIONARY_SYSTEM,
    build_aggregator_user_message,
    build_debate_user_message,
    compact_skeleton,
)
from app.services.v4.consensus.vote import (
    agreement_ratio,
    quorum_reached,
    weighted_merge,
)
from app.services.v4.llm_safe import safe_complete

logger = structlog.get_logger(__name__)


# ── Result container ─────────────────────────────────────────────

@dataclass
class ConsensusResult:
    """Return value from run_consensus. ``content`` is a JSON string the
    caller feeds into the writer's existing ``_parse_writer_output``."""
    content: str
    mode: str  # "standard" | "premium"
    drafts: list[str] = field(default_factory=list)
    grader_scores: dict[str, int] = field(default_factory=dict)
    grader_issues: list[str] = field(default_factory=list)
    agreement: dict[str, float] = field(default_factory=dict)
    council_degraded: bool = False
    regen_triggered: bool = False
    latency_ms: int = 0
    tokens_used: int = 0
    drafters_used: list[str] = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────

def _safe_json_parse(raw: str) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def _json_or_empty(raw: str) -> str:
    parsed = _safe_json_parse(raw)
    return json.dumps(parsed, ensure_ascii=False) if parsed else ""


# ── Standard mode ────────────────────────────────────────────────

async def _run_standard(
    *,
    router: ModelRouter,
    system: str,
    user_msg: str,
    project_id: str,
    phase: str,
    temperature: float,
    max_tokens: int,
    skeleton_json: str,
    budget_s: float,
) -> ConsensusResult:
    t0 = time.monotonic()
    tokens = 0
    drafts: list[str] = []

    # --- Round 1: draft A ---
    try:
        draft_a = await safe_complete(
            router=router,
            primary_task=TaskType.NARRATIVE_STORYTELLING,
            fallback_task=TaskType.TEMPLATE_FILL,
            messages=[
                {"role": "system", "content": system or STANDARD_WRITER_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            presentation_id=project_id,
            phase=f"{phase}_std_writer_a",
            timeout_s=min(9.0, budget_s * 0.55),
            fallback_timeout_s=6.0,
            resumable=True,
            slot=f"consensus_std_a_{phase}",
        )
        tokens += draft_a.tokens_used or 0
        drafts.append(draft_a.content)
    except Exception as e:  # noqa: BLE001
        logger.warning("consensus_standard_draft_a_failed", phase=phase, error=str(e)[:200])
        elapsed = int((time.monotonic() - t0) * 1000)
        return ConsensusResult(
            content="", mode="standard", drafts=[], council_degraded=True,
            latency_ms=elapsed, tokens_used=tokens, drafters_used=[],
        )

    # Budget left?
    if (time.monotonic() - t0) > budget_s:
        elapsed = int((time.monotonic() - t0) * 1000)
        return ConsensusResult(
            content=drafts[0], mode="standard", drafts=drafts,
            council_degraded=True, latency_ms=elapsed, tokens_used=tokens,
            drafters_used=["writer_a"],
        )

    # --- Round 2: critic ---
    critic_msg = (
        f"Skeleton:\n{skeleton_json}\n\n"
        f"Draft A:\n{drafts[0]}\n\n"
        "Produce your critic verdict JSON now."
    )
    critic_scores: dict[str, int] = {}
    try:
        critic_resp = await safe_complete(
            router=router,
            primary_task=TaskType.REFINEMENT,
            # Founder fix (Apr 2026): keep critic in the REFINEMENT tier
            # on retry rather than collapsing to a classifier model.
            fallback_task=TaskType.REFINEMENT,
            messages=[
                {"role": "system", "content": STANDARD_CRITIC_SYSTEM},
                {"role": "user", "content": critic_msg},
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
            presentation_id=project_id,
            phase=f"{phase}_std_critic",
            timeout_s=5.0,
            fallback_timeout_s=4.0,
        )
        tokens += critic_resp.tokens_used or 0
        critic_data = _safe_json_parse(critic_resp.content) or {}
        critic_scores = {
            k: int(v) for k, v in (critic_data.get("scores") or {}).items()
            if isinstance(v, (int, float))
        }
        critic_fixes = critic_data.get("fixes") or []
        critic_blockers = critic_data.get("blockers") or []
    except Exception as e:  # noqa: BLE001
        logger.warning("consensus_standard_critic_failed", phase=phase, error=str(e)[:200])
        critic_data, critic_fixes, critic_blockers = {}, [], []

    # Decide if we regen
    min_score = min(critic_scores.values()) if critic_scores else 5
    needs_regen = bool(critic_blockers) or min_score < 4
    regen_triggered = False
    final = drafts[0]

    if needs_regen and (time.monotonic() - t0) < budget_s * 0.75:
        # --- Round 3: draft B with fixes ---
        fixes_block = "\n".join(f"- {s}" for s in (critic_fixes + critic_blockers))
        writer_b_msg = (
            f"{user_msg}\n\n"
            f"Your previous draft had these critic fixes:\n{fixes_block}\n\n"
            "Produce an improved JSON slide that addresses every fix."
        )
        try:
            draft_b = await safe_complete(
                router=router,
                primary_task=TaskType.NARRATIVE_STORYTELLING,
                fallback_task=TaskType.TEMPLATE_FILL,
                messages=[
                    {"role": "system", "content": system or STANDARD_WRITER_SYSTEM},
                    {"role": "user", "content": writer_b_msg},
                ],
                temperature=min(temperature + 0.1, 0.9),
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                presentation_id=project_id,
                phase=f"{phase}_std_writer_b",
                timeout_s=min(8.0, max(3.0, budget_s - (time.monotonic() - t0) - 2.0)),
                fallback_timeout_s=5.0,
                resumable=True,
                slot=f"consensus_std_b_{phase}",
            )
            tokens += draft_b.tokens_used or 0
            drafts.append(draft_b.content)
            regen_triggered = True
        except Exception as e:  # noqa: BLE001
            logger.warning("consensus_standard_draft_b_failed", phase=phase, error=str(e)[:200])
            drafts.append("")

        # --- Judge pick ---
        if drafts[-1]:
            judge_msg = (
                f"Skeleton:\n{skeleton_json}\n\n"
                f"Draft A:\n{drafts[0]}\n\nDraft B:\n{drafts[1]}\n\n"
                "Pick the winner. Return strict JSON."
            )
            try:
                judge_resp = await safe_complete(
                    router=router,
                    primary_task=TaskType.REFINEMENT,
                    # Founder fix (Apr 2026): judge stays in REFINEMENT tier.
                    fallback_task=TaskType.REFINEMENT,
                    messages=[
                        {"role": "system", "content": STANDARD_JUDGE_SYSTEM},
                        {"role": "user", "content": judge_msg},
                    ],
                    temperature=0.1,
                    max_tokens=200,
                    response_format={"type": "json_object"},
                    presentation_id=project_id,
                    phase=f"{phase}_std_judge",
                    timeout_s=3.5,
                    fallback_timeout_s=2.5,
                )
                tokens += judge_resp.tokens_used or 0
                judge_data = _safe_json_parse(judge_resp.content) or {}
                winner = str(judge_data.get("winner", "B")).upper().strip()
                final = drafts[1] if winner == "B" else drafts[0]
            except Exception as e:  # noqa: BLE001
                logger.warning("consensus_standard_judge_failed", phase=phase, error=str(e)[:200])
                # Default to B (post-fix version is usually better)
                final = drafts[1]

    elapsed = int((time.monotonic() - t0) * 1000)
    degraded = (time.monotonic() - t0) > budget_s or not final
    return ConsensusResult(
        content=final or drafts[0],
        mode="standard",
        drafts=drafts,
        grader_scores=critic_scores,
        grader_issues=critic_blockers + critic_fixes,
        council_degraded=degraded,
        regen_triggered=regen_triggered,
        latency_ms=elapsed,
        tokens_used=tokens,
        drafters_used=["writer_a"] + (["writer_b"] if regen_triggered else []),
    )


# ── Premium mode ─────────────────────────────────────────────────

_PERSONAS_PREMIUM: list[tuple[str, str, TaskType]] = [
    # (persona_name, system_prompt, router task — shapes the model chain)
    ("visionary", VISIONARY_SYSTEM, TaskType.NARRATIVE_STORYTELLING),
    ("analyst", ANALYST_SYSTEM, TaskType.GENERAL),
    ("designer", DESIGNER_SYSTEM, TaskType.DESIGNER_LAYOUT),
    ("investor", INVESTOR_SYSTEM, TaskType.OUTLINE_PLANNING),
]


async def _drafter(
    *,
    router: ModelRouter,
    persona: str,
    system: str,
    task: TaskType,
    user_msg: str,
    project_id: str,
    phase: str,
    temperature: float,
    max_tokens: int,
    timeout_s: float,
) -> tuple[str, str, int]:
    """Run one persona drafter. Returns (persona, content, tokens_used)."""
    try:
        resp = await safe_complete(
            router=router,
            primary_task=task,
            fallback_task=TaskType.TEMPLATE_FILL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            presentation_id=project_id,
            phase=f"{phase}_prem_drafter_{persona}",
            timeout_s=timeout_s,
            fallback_timeout_s=max(4.0, timeout_s * 0.55),
            resumable=True,
            slot=f"consensus_prem_{persona}_{phase}",
        )
        return persona, resp.content or "", resp.tokens_used or 0
    except Exception as e:  # noqa: BLE001
        logger.warning("consensus_drafter_failed",
                       persona=persona, phase=phase, error=str(e)[:200])
        return persona, "", 0


async def _run_premium(
    *,
    router: ModelRouter,
    system: str,
    user_msg: str,
    project_id: str,
    phase: str,
    temperature: float,
    max_tokens: int,
    skeleton_json: str,
    scoped_evidence: str,
    design_context: str,
    budget_s: float,
) -> ConsensusResult:
    _ = system  # premium mode uses its own persona systems, but keep the param
    t0 = time.monotonic()
    tokens = 0
    drafters_used: list[str] = []

    # ── Stage 1: parallel persona drafts ─────────────────────────
    # Budget allocation:
    #   drafters:   9.0s    (parallel, each capped at 9.0)
    #   debate:     8.0s    (parallel, each capped at 6.0)
    #   aggregator: 4.0s
    #   graders:    3.0s    (parallel)
    #   regen:      up to (remaining budget)
    drafter_timeout = min(9.0, budget_s * 0.36)

    drafter_tasks = [
        _drafter(
            router=router,
            persona=name,
            system=sys_prompt,
            task=task,
            user_msg=user_msg,
            project_id=project_id,
            phase=phase,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=drafter_timeout,
        )
        for (name, sys_prompt, task) in _PERSONAS_PREMIUM
    ]

    try:
        drafter_results = await asyncio.wait_for(
            asyncio.gather(*drafter_tasks, return_exceptions=False),
            timeout=drafter_timeout + 3.0,
        )
    except asyncio.TimeoutError:
        drafter_results = []
        logger.warning("consensus_premium_drafter_bundle_timeout", phase=phase)

    drafts: list[str] = []
    persona_of: list[str] = []
    for persona, content, tk in drafter_results:
        tokens += tk
        if content and content.strip():
            drafts.append(content)
            persona_of.append(persona)
            drafters_used.append(persona)

    # Quorum gate: need ≥2 non-empty drafts. If not, degrade to standard.
    parsed_drafts = [d for d in (_json_or_empty(x) for x in drafts) if d]
    if len(parsed_drafts) < 2:
        logger.warning("consensus_premium_no_quorum", n=len(parsed_drafts), phase=phase)
        std_res = await _run_standard(
            router=router,
            system=system,
            user_msg=user_msg,
            project_id=project_id,
            phase=f"{phase}_degraded",
            temperature=temperature,
            max_tokens=max_tokens,
            skeleton_json=skeleton_json,
            budget_s=max(6.0, budget_s - (time.monotonic() - t0)),
        )
        std_res.council_degraded = True
        std_res.mode = "premium_degraded"
        std_res.drafters_used = drafters_used + std_res.drafters_used
        std_res.tokens_used += tokens
        std_res.latency_ms = int((time.monotonic() - t0) * 1000)
        return std_res

    # ── Stage 2: debate round (parallel, construct_message) ──────
    debate_timeout = min(7.0, max(3.0, (budget_s - (time.monotonic() - t0)) * 0.4))
    debate_tasks = []
    for i, own in enumerate(parsed_drafts):
        others = [d for j, d in enumerate(parsed_drafts) if j != i]
        debate_msg = build_debate_user_message(
            own_draft_json=own,
            other_drafts_json=others,
            scoped_evidence=scoped_evidence,
        )
        debate_tasks.append(
            safe_complete(
                router=router,
                primary_task=TaskType.REFINEMENT,
                fallback_task=TaskType.TEMPLATE_FILL,
                messages=[
                    {"role": "system", "content": DEBATE_SYSTEM},
                    {"role": "user", "content": debate_msg},
                ],
                temperature=max(0.3, temperature - 0.1),
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                presentation_id=project_id,
                phase=f"{phase}_prem_debate_{persona_of[i]}",
                timeout_s=debate_timeout,
                fallback_timeout_s=max(3.0, debate_timeout * 0.55),
            )
        )

    debate_drafts: list[str] = []
    try:
        debate_results = await asyncio.wait_for(
            asyncio.gather(*debate_tasks, return_exceptions=True),
            timeout=debate_timeout + 3.0,
        )
        for r in debate_results:
            if isinstance(r, BaseException):
                continue
            if r and getattr(r, "content", None):
                tokens += r.tokens_used or 0
                debate_drafts.append(r.content)
    except asyncio.TimeoutError:
        logger.warning("consensus_premium_debate_timeout", phase=phase)

    # If debate produced ≥2 refined drafts, use them; else keep the originals
    refined_drafts = debate_drafts if len(debate_drafts) >= 2 else parsed_drafts

    # ── Stage 3: aggregator ──────────────────────────────────────
    parsed_refined_objs = [_safe_json_parse(d) or {} for d in refined_drafts]
    agreement = {
        f: agreement_ratio(parsed_refined_objs, f)
        for f in ("layout", "density_target", "headline")
    }

    agg_user = build_aggregator_user_message(
        drafts_json=refined_drafts,
        scoped_evidence=scoped_evidence,
        skeleton_json=skeleton_json,
    )
    agg_timeout = min(5.0, max(2.5, (budget_s - (time.monotonic() - t0)) * 0.25))
    final_content = ""
    try:
        agg_resp = await safe_complete(
            router=router,
            primary_task=TaskType.REFINEMENT,
            fallback_task=TaskType.TEMPLATE_FILL,
            messages=[
                {"role": "system", "content": AGGREGATOR_SYSTEM},
                {"role": "user", "content": agg_user},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            presentation_id=project_id,
            phase=f"{phase}_prem_aggregator",
            timeout_s=agg_timeout,
            fallback_timeout_s=max(2.0, agg_timeout * 0.6),
        )
        tokens += agg_resp.tokens_used or 0
        final_content = agg_resp.content or ""
    except Exception as e:  # noqa: BLE001
        logger.warning("consensus_premium_aggregator_failed", phase=phase, error=str(e)[:200])

    if not final_content:
        # Aggregator failed — fall back to weighted_merge of refined drafts
        merged = weighted_merge(parsed_refined_objs)
        final_content = json.dumps(merged, ensure_ascii=False)

    # ── Stage 4: parallel graders ────────────────────────────────
    grader_budget = min(8.0, max(3.0, budget_s - (time.monotonic() - t0)))
    verdicts: list[grader_mod.GraderVerdict] = []
    grader_issues: list[str] = []
    if grader_budget >= 3.0:
        verdicts = await grader_mod.run_graders_parallel(
            router=router,
            draft_json=final_content,
            scoped_evidence=scoped_evidence,
            skeleton_json=skeleton_json,
            design_context=design_context,
            project_id=project_id,
            phase=phase,
            budget_s=grader_budget,
        )
        grader_issues = grader_mod.consolidated_issues(verdicts)

    # ── Stage 5: regen once if any grader failed ────────────────
    regen_triggered = False
    if verdicts and grader_mod.any_failed(verdicts):
        remaining = budget_s - (time.monotonic() - t0)
        if remaining >= 4.0:
            regen_msg = (
                f"{agg_user}\n\n"
                "Graders flagged these issues in the previous aggregate — "
                "fix ALL of them in the regenerated slide:\n- "
                + "\n- ".join(grader_issues or ["(unspecified)"])
                + "\n\nReturn the improved slide JSON now."
            )
            try:
                regen_resp = await safe_complete(
                    router=router,
                    primary_task=TaskType.REFINEMENT,
                    fallback_task=TaskType.NARRATIVE_STORYTELLING,
                    messages=[
                        {"role": "system", "content": AGGREGATOR_SYSTEM},
                        {"role": "user", "content": regen_msg},
                    ],
                    temperature=0.35,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    presentation_id=project_id,
                    phase=f"{phase}_prem_regen",
                    timeout_s=min(6.0, remaining - 1.5),
                    fallback_timeout_s=min(4.0, max(2.0, remaining - 2.5)),
                )
                if regen_resp.content and regen_resp.content.strip():
                    final_content = regen_resp.content
                    tokens += regen_resp.tokens_used or 0
                    regen_triggered = True
            except Exception as e:  # noqa: BLE001
                logger.warning("consensus_premium_regen_failed", phase=phase, error=str(e)[:200])

    elapsed = int((time.monotonic() - t0) * 1000)
    degraded = (time.monotonic() - t0) > budget_s
    return ConsensusResult(
        content=final_content,
        mode="premium",
        drafts=refined_drafts,
        grader_scores={v.name: v.score for v in verdicts},
        grader_issues=grader_issues,
        agreement=agreement,
        council_degraded=degraded,
        regen_triggered=regen_triggered,
        latency_ms=elapsed,
        tokens_used=tokens,
        drafters_used=drafters_used,
    )


# ── Public entry point ───────────────────────────────────────────

async def run_consensus(
    *,
    router: ModelRouter,
    mode: str,
    system: str,
    user_msg: str,
    project_id: str,
    phase: str,
    temperature: float = 0.6,
    max_tokens: int = 1200,
    skeleton: Optional[dict[str, Any]] = None,
    scoped_evidence: str = "",
    design_context: str = "",
    budget_s: Optional[float] = None,
) -> ConsensusResult:
    """Run the multi-model consensus panel for a single slide.

    Parameters
    ----------
    mode : "standard" | "premium"
    system : str
        Base writer system prompt. Used as-is in standard mode; persona
        prompts override in premium mode.
    user_msg : str
        The full user message (skeleton + scoped evidence + design block
        + structured context) — same string the single-model writer used.
    skeleton : dict, optional
        Compact skeleton fields, passed to graders/judge/aggregator. When
        omitted we build it from the user_msg.
    scoped_evidence : str
        Evidence chunks block — repeated to debate/aggregator/graders
        so they can validate claims without reparsing user_msg.
    design_context : str
        Design tokens block — required by the design grader.
    budget_s : float, optional
        Outer wall-clock cap. Default: 15.0 standard / 25.0 premium.

    Returns
    -------
    ConsensusResult with ``content`` as a JSON string ready for
    ``_parse_writer_output``.
    """
    skel_json = compact_skeleton(skeleton) if skeleton else "{}"
    budget = budget_s if budget_s is not None else (25.0 if mode == "premium" else 15.0)

    if mode == "premium":
        return await _run_premium(
            router=router,
            system=system,
            user_msg=user_msg,
            project_id=project_id,
            phase=phase,
            temperature=temperature,
            max_tokens=max_tokens,
            skeleton_json=skel_json,
            scoped_evidence=scoped_evidence,
            design_context=design_context,
            budget_s=budget,
        )
    return await _run_standard(
        router=router,
        system=system,
        user_msg=user_msg,
        project_id=project_id,
        phase=phase,
        temperature=temperature,
        max_tokens=max_tokens,
        skeleton_json=skel_json,
        budget_s=budget,
    )
