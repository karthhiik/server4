"""
Pitch Deck Debate Loop — Multi-agent challenge process.

For investor/pitch/fundraising decks, evidence goes through a 3-agent
debate before content generation:
1. CEO proposes thesis from evidence
2. CTO challenges technical feasibility
3. Finance challenges numbers
4. Resolution with citations

Max 3 rounds. Each round uses progressively cheaper models.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import (
    ContentEvent,
    DebateOutcome,
    FactPacket,
    RejectedClaim,
    SlideEvidenceBundle,
    SlideKind,
)
from app.mcp.brain_mcp.research.content_events import ContentEventEmitter
from app.services.llm.model_router import TaskType

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# DEBATE PROMPTS
# ═══════════════════════════════════════════════════════════════════════

CEO_THESIS_PROMPT = """You are a visionary startup CEO preparing an investor pitch.
Given this evidence, propose the strongest investable thesis.

Evidence:
{evidence}

Slide type: {slide_kind}
Topic: {topic}

Return ONLY valid JSON (no markdown, no commentary):
{{
    "thesis": "one-sentence investment thesis",
    "proposed_claims": [
        {{"fact_id": "fp_xxx", "usage": "how this fact supports the thesis"}}
    ],
    "narrative_angle": "the emotional/logical hook for investors",
    "confidence": 0.85
}}"""

CTO_CHALLENGE_PROMPT = """You are a skeptical CTO and technical due diligence expert.
Challenge the CEO's thesis for technical feasibility and moat realism.

CEO's Thesis: {thesis}
Proposed Claims:
{claims}

Available Evidence:
{evidence}

For each claim, either APPROVE or REJECT with reason.
Return ONLY valid JSON (no markdown, no commentary):
{{
    "challenges": [
        {{"fact_id": "fp_xxx", "verdict": "approve", "reason": "...", "alternative": null}},
        {{"fact_id": "fp_yyy", "verdict": "reject", "reason": "...", "alternative": "suggestion"}}
    ],
    "technical_feasibility": 0.75,
    "moat_assessment": "moderate",
    "confidence": 0.8
}}"""

FINANCE_CHALLENGE_PROMPT = """You are a financial analyst doing investor due diligence.
Challenge the thesis for financial credibility.

CEO's Thesis: {thesis}
Remaining Claims (post-CTO review):
{claims}

Available Evidence:
{evidence}

For each numeric claim, verify it has a credible source. Reject unsourced numbers.
Return ONLY valid JSON (no markdown, no commentary):
{{
    "challenges": [
        {{"fact_id": "fp_xxx", "verdict": "approve", "reason": "...", "alternative": null}},
        {{"fact_id": "fp_yyy", "verdict": "reject", "reason": "...", "alternative": "fix"}}
    ],
    "financial_credibility": 0.7,
    "unit_economics_valid": true,
    "confidence": 0.75
}}"""

RESOLUTION_PROMPT = """You are a Research Chief resolving a debate.
Map each surviving claim to its FactPacket source.

Surviving claims after CEO/CTO/Finance debate:
{surviving_claims}

All available evidence:
{evidence}

Return ONLY valid JSON (no markdown, no commentary):
{{
    "approved_claims": ["fp_xxx", "fp_yyy"],
    "final_thesis": "refined one-sentence thesis",
    "debate_summary": "what was challenged and why",
    "confidence": 0.8
}}"""

# Model selection per debate round (progressively cheaper)
ROUND_TASK_TYPES: dict[int, dict[str, TaskType]] = {
    1: {
        "ceo": TaskType.OUTLINE_PLANNING,
        "cto": TaskType.TECHNICAL_CODE,
        "finance": TaskType.STRUCTURED_JSON,
    },
    2: {
        "ceo": TaskType.NARRATIVE_STORYTELLING,
        "cto": TaskType.GENERAL,
        "finance": TaskType.STRUCTURED_JSON,
    },
    3: {
        "ceo": TaskType.GENERAL,
        "cto": TaskType.GENERAL,
        "finance": TaskType.GENERAL,
    },
}

# Regex for stripping markdown fences from LLM JSON output
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


class DebateLoop:
    """Manages the CEO/CTO/Finance debate process for pitch decks."""

    MAX_ROUNDS = 3
    CEO_CONFIDENCE_THRESHOLD = 0.7
    CTO_CONFIDENCE_THRESHOLD = 0.6

    def __init__(self, model_router: Any, emitter: Optional[ContentEventEmitter] = None):
        self._router = model_router
        self._emitter = emitter

    # ── Public API ──────────────────────────────────────────────

    async def run_debate(
        self,
        evidence_bundle: SlideEvidenceBundle,
        topic: str,
        slide_kind: SlideKind,
    ) -> DebateOutcome:
        """
        Run the full debate loop. Returns DebateOutcome with approved/rejected claims.

        Process per round:
        1. CEO proposes thesis from evidence
        2. CTO challenges technical claims
        3. Finance challenges numbers
        4. Resolution — map surviving claims to sources
        5. If confidence too low, iterate (max 3 rounds)
        """
        packets = evidence_bundle.evidence_packets
        if not packets:
            logger.warning("Debate skipped: no evidence packets for slide %s", evidence_bundle.slide_id)
            return DebateOutcome(
                approved_claims=[],
                rejected_claims=[],
                iteration_count=0,
                final_thesis="",
                debate_summary="No evidence available for debate.",
            )

        outcome = DebateOutcome()
        all_rejected: list[RejectedClaim] = []
        round_num = 0

        for round_num in range(1, self.MAX_ROUNDS + 1):
            start_time = time.monotonic()
            logger.info("Debate round %d starting for slide %s", round_num, evidence_bundle.slide_id)

            # Phase 1: CEO proposes thesis
            ceo_result = await self._run_ceo_phase(packets, topic, slide_kind, round_num)
            await self._emit_event(
                ContentEvent.CEO_THESIS_READY,
                evidence_bundle.slide_id,
                {"round": round_num, "thesis": ceo_result.get("thesis", ""), "confidence": ceo_result.get("confidence", 0.0)},
                f"CEO thesis proposed (round {round_num})",
            )

            # Phase 2: CTO challenges
            cto_result = await self._run_cto_phase(ceo_result, packets, round_num)
            await self._emit_event(
                ContentEvent.CTO_CHALLENGE_READY,
                evidence_bundle.slide_id,
                {
                    "round": round_num,
                    "technical_feasibility": cto_result.get("technical_feasibility", 0.0),
                    "moat_assessment": cto_result.get("moat_assessment", "unknown"),
                },
                f"CTO review complete (round {round_num})",
            )

            # Build post-CTO surviving claims
            cto_challenges = cto_result.get("challenges", [])
            cto_rejected_ids: set[str] = set()
            for ch in cto_challenges:
                if ch.get("verdict", "").lower() == "reject":
                    fid = ch.get("fact_id", "")
                    cto_rejected_ids.add(fid)
                    all_rejected.append(RejectedClaim(
                        fact_packet_id=fid,
                        reason=ch.get("reason", "CTO rejection"),
                        rejected_by="cto",
                        alternative_suggestion=ch.get("alternative"),
                    ))

            post_cto_claims = [
                c for c in ceo_result.get("proposed_claims", [])
                if c.get("fact_id", "") not in cto_rejected_ids
            ]

            # Phase 3: Finance challenges
            finance_result = await self._run_finance_phase(ceo_result, post_cto_claims, packets, round_num)
            await self._emit_event(
                ContentEvent.FINANCE_CHALLENGE_READY,
                evidence_bundle.slide_id,
                {
                    "round": round_num,
                    "financial_credibility": finance_result.get("financial_credibility", 0.0),
                    "unit_economics_valid": finance_result.get("unit_economics_valid", False),
                },
                f"Finance review complete (round {round_num})",
            )

            # Track finance rejections
            fin_challenges = finance_result.get("challenges", [])
            fin_rejected_ids: set[str] = set()
            for ch in fin_challenges:
                if ch.get("verdict", "").lower() == "reject":
                    fid = ch.get("fact_id", "")
                    fin_rejected_ids.add(fid)
                    all_rejected.append(RejectedClaim(
                        fact_packet_id=fid,
                        reason=ch.get("reason", "Finance rejection"),
                        rejected_by="finance",
                        alternative_suggestion=ch.get("alternative"),
                    ))

            # Build surviving claims for resolution
            surviving = [
                c for c in post_cto_claims
                if c.get("fact_id", "") not in fin_rejected_ids
            ]

            # Phase 4: Resolution
            resolution = await self._run_resolution(surviving, packets)

            elapsed_ms = (time.monotonic() - start_time) * 1000
            await self._emit_event(
                ContentEvent.DEBATE_ROUND_COMPLETE,
                evidence_bundle.slide_id,
                {
                    "round": round_num,
                    "approved_count": len(resolution.get("approved_claims", [])),
                    "rejected_count": len(all_rejected),
                    "elapsed_ms": round(elapsed_ms, 1),
                },
                f"Debate round {round_num} complete",
            )

            # Update outcome
            outcome.approved_claims = resolution.get("approved_claims", [])
            outcome.final_thesis = resolution.get("final_thesis", ceo_result.get("thesis", ""))
            outcome.debate_summary = resolution.get("debate_summary", "")
            outcome.ceo_confidence = ceo_result.get("confidence", 0.0)
            outcome.cto_confidence = cto_result.get("confidence", 0.0)
            outcome.finance_confidence = finance_result.get("confidence", 0.0)
            outcome.iteration_count = round_num

            # Check if we should iterate
            if not self._should_iterate(outcome.ceo_confidence, outcome.cto_confidence):
                break

            # If iterating, filter evidence to only approved claims for next round
            approved_set = set(outcome.approved_claims)
            packets = [p for p in packets if p.id in approved_set] or packets

        # Finalize
        outcome.rejected_claims = all_rejected

        await self._emit_event(
            ContentEvent.DEBATE_RESOLVED,
            evidence_bundle.slide_id,
            {
                "total_rounds": outcome.iteration_count,
                "approved": len(outcome.approved_claims),
                "rejected": len(outcome.rejected_claims),
                "final_thesis": outcome.final_thesis,
            },
            "Debate resolved",
        )

        logger.info(
            "Debate complete for slide %s: %d rounds, %d approved, %d rejected",
            evidence_bundle.slide_id,
            outcome.iteration_count,
            len(outcome.approved_claims),
            len(outcome.rejected_claims),
        )
        return outcome

    # ── Phase runners ───────────────────────────────────────────

    async def _run_ceo_phase(
        self,
        evidence: list[FactPacket],
        topic: str,
        slide_kind: SlideKind,
        round_num: int,
    ) -> dict:
        """CEO proposes thesis from evidence."""
        task_type = ROUND_TASK_TYPES.get(round_num, ROUND_TASK_TYPES[3])["ceo"]
        prompt = CEO_THESIS_PROMPT.format(
            evidence=self._format_evidence(evidence),
            slide_kind=slide_kind.value,
            topic=topic,
        )
        return await self._call_llm(task_type, prompt, "CEO thesis", round_num)

    async def _run_cto_phase(
        self,
        thesis: dict,
        evidence: list[FactPacket],
        round_num: int,
    ) -> dict:
        """CTO challenges thesis for technical feasibility."""
        task_type = ROUND_TASK_TYPES.get(round_num, ROUND_TASK_TYPES[3])["cto"]
        claims_text = json.dumps(thesis.get("proposed_claims", []), indent=2)
        prompt = CTO_CHALLENGE_PROMPT.format(
            thesis=thesis.get("thesis", ""),
            claims=claims_text,
            evidence=self._format_evidence(evidence),
        )
        return await self._call_llm(task_type, prompt, "CTO challenge", round_num)

    async def _run_finance_phase(
        self,
        thesis: dict,
        post_cto_claims: list,
        evidence: list[FactPacket],
        round_num: int,
    ) -> dict:
        """Finance challenges numbers and financial credibility."""
        task_type = ROUND_TASK_TYPES.get(round_num, ROUND_TASK_TYPES[3])["finance"]
        claims_text = json.dumps(post_cto_claims, indent=2)
        prompt = FINANCE_CHALLENGE_PROMPT.format(
            thesis=thesis.get("thesis", ""),
            claims=claims_text,
            evidence=self._format_evidence(evidence),
        )
        return await self._call_llm(task_type, prompt, "Finance challenge", round_num)

    async def _run_resolution(
        self,
        surviving_claims: list,
        evidence: list[FactPacket],
    ) -> dict:
        """Map approved claims to evidence sources."""
        prompt = RESOLUTION_PROMPT.format(
            surviving_claims=json.dumps(surviving_claims, indent=2),
            evidence=self._format_evidence(evidence),
        )
        return await self._call_llm(TaskType.STRUCTURED_JSON, prompt, "Resolution", 1)

    # ── LLM call helper ────────────────────────────────────────

    async def _call_llm(self, task_type: TaskType, user_prompt: str, label: str, round_num: int) -> dict:
        """Call model router and parse JSON response. Returns empty dict on failure."""
        messages = [
            {"role": "system", "content": "You are a pitch deck analysis agent. Return ONLY valid JSON."},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = await self._router.complete(
                task_type=task_type,
                messages=messages,
                temperature=max(0.3, 0.7 - (round_num * 0.1)),
                max_tokens=2048,
                response_format={"type": "json_object"},
                phase=f"debate_{label.lower().replace(' ', '_')}",
            )
            return self._parse_json_response(response.content)
        except Exception as exc:
            logger.error("Debate LLM call failed [%s round %d]: %s", label, round_num, exc)
            return {}

    # ── Helpers ─────────────────────────────────────────────────

    def _format_evidence(self, packets: list[FactPacket]) -> str:
        """Format FactPackets for LLM consumption."""
        if not packets:
            return "(no evidence available)"
        lines: list[str] = []
        for fp in packets:
            parts = [
                f"[{fp.id}]",
                f"Claim: {fp.claim}",
                f"Type: {fp.claim_type.value}",
                f"Source: {fp.source_name}",
                f"Confidence: {fp.confidence:.2f}",
            ]
            if fp.numeric_value is not None:
                parts.append(f"Value: {fp.numeric_value} {fp.numeric_unit or ''}")
            if fp.date_published:
                parts.append(f"Date: {fp.date_published}")
            if fp.cross_validated:
                parts.append(f"Cross-validated: {', '.join(fp.cross_validation_sources)}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    def _parse_json_response(self, raw: str) -> dict:
        """Robustly parse JSON from LLM response, stripping fences/extras."""
        if not raw:
            return {}

        text = raw.strip()

        # Strip markdown code fences
        fence_match = _JSON_FENCE_RE.search(text)
        if fence_match:
            text = fence_match.group(1).strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find the first { ... } block
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse debate JSON response: %.200s", text)
        return {}

    def _should_iterate(self, ceo_confidence: float, cto_confidence: float) -> bool:
        """Check if debate needs another round based on confidence thresholds."""
        if ceo_confidence >= self.CEO_CONFIDENCE_THRESHOLD and cto_confidence >= self.CTO_CONFIDENCE_THRESHOLD:
            return False
        # If both are zero (parse failure), don't loop forever
        if ceo_confidence == 0.0 and cto_confidence == 0.0:
            return False
        return True

    async def _emit_event(
        self,
        event: ContentEvent,
        slide_id: Optional[str],
        data: dict,
        message: str,
    ) -> None:
        """Emit a debate event if emitter is available."""
        if self._emitter is not None:
            try:
                await self._emitter.emit(event=event, slide_id=slide_id, data=data, message=message)
            except Exception as exc:
                logger.warning("Failed to emit debate event %s: %s", event.value, exc)
