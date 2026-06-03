"""Premium-only boardroom rehearsal judge for V4 decks.

The judge is disabled by default. When enabled, it performs one cheap
structured-JSON LLM call, caches the verdict on the deck row, and can merge a
low narrative score into the existing production quality gate shape.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Sequence

import structlog

from app.config import settings
from app.services.llm.model_router import TaskType, get_model_router
from app.services.v4.llm_safe import safe_complete


logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BoardroomJudgeResult:
    enabled: bool
    cached: bool
    score: int | None
    summary: str = ""
    blocker: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def merge_boardroom_judge_into_gate(
    production_gate: Mapping[str, Any] | None,
    judge_result: Mapping[str, Any] | BoardroomJudgeResult | None,
    *,
    mode: str = "premium",
) -> dict[str, Any]:
    """Return a copy of the production gate with judge blocker merged."""

    gate = dict(production_gate or {})
    if not gate:
        gate = {
            "schema_version": 1,
            "passed": False,
            "blocked": False,
            "score": 0,
            "summary": "Production quality gate has not run.",
            "issue_totals": {},
            "slide_reports": [],
            "issues": [],
            "checks": {},
        }
    result = judge_result.to_dict() if isinstance(judge_result, BoardroomJudgeResult) else dict(judge_result or {})
    blocker = result.get("blocker") if isinstance(result, Mapping) else None
    if str(mode).lower() != "premium" or not isinstance(blocker, Mapping):
        return gate
    issues = list(gate.get("issues") or [])
    if not any(isinstance(issue, Mapping) and issue.get("code") == "narrative_flow_weak" for issue in issues):
        issues.append(dict(blocker))
    totals = dict(gate.get("issue_totals") or {})
    totals["blocker"] = totals.get("blocker", 0) + 1
    gate["issues"] = issues
    gate["issue_totals"] = totals
    gate["blocked"] = True
    gate["passed"] = False
    gate["checks"] = {**dict(gate.get("checks") or {}), "boardroom_rehearsal": True}
    gate["summary"] = "Boardroom rehearsal found a narrative-flow blocker."
    return gate


async def run_boardroom_judge(
    *,
    deck_doc: MutableMapping[str, Any],
    db: Any | None = None,
    project_id: str | None = None,
    mode: str = "premium",
    force_refresh: bool = False,
) -> BoardroomJudgeResult:
    """Run or load the cached boardroom judge result.

    The function never runs for standard mode or when the kill-switch is off.
    Tests can pass a mutable ``deck_doc`` without a database; production callers
    may pass Mongo ``db`` and ``project_id`` to persist the cache.
    """

    if str(mode).lower() != "premium" or not settings.ENABLE_BOARDROOM_JUDGE:
        return BoardroomJudgeResult(enabled=False, cached=False, score=None)

    cached = deck_doc.get("boardroom_judge")
    if isinstance(cached, Mapping) and not force_refresh:
        score = _coerce_score(cached.get("score"))
        blocker = _blocker_for_score(score, str(cached.get("summary") or ""))
        return BoardroomJudgeResult(
            enabled=True,
            cached=True,
            score=score,
            summary=str(cached.get("summary") or ""),
            blocker=blocker,
        )

    slides = deck_doc.get("compiled_slides") or deck_doc.get("slides") or []
    prompt = _build_prompt(slides)
    try:
        response = await safe_complete(
            router=get_model_router(),
            primary_task=TaskType.STRUCTURED_JSON,
            fallback_task=TaskType.REFINEMENT,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a boardroom rehearsal judge for investor-grade decks. "
                        "Return only JSON with keys score (0-100) and summary."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            timeout_s=18.0,
            fallback_timeout_s=18.0,
            presentation_id=project_id,
            phase="boardroom_judge",
        )
        parsed = _parse_response(getattr(response, "content", ""))
    except Exception as err:  # noqa: BLE001
        logger.warning(
            "boardroom_judge_failed",
            project_id=project_id,
            error=type(err).__name__,
        )
        parsed = {"score": 100, "summary": "Boardroom judge unavailable; local quality gate remains authoritative."}

    score = _coerce_score(parsed.get("score"))
    summary = str(parsed.get("summary") or "")
    cache_doc = {
        "enabled": True,
        "score": score,
        "summary": summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    deck_doc["boardroom_judge"] = cache_doc
    if db is not None and project_id:
        try:
            await db.presentations.update_one(
                {"id": project_id},
                {"$set": {"boardroom_judge": cache_doc}},
            )
        except Exception as err:  # noqa: BLE001
            logger.warning(
                "boardroom_judge_cache_failed",
                project_id=project_id,
                error=type(err).__name__,
            )
    return BoardroomJudgeResult(
        enabled=True,
        cached=False,
        score=score,
        summary=summary,
        blocker=_blocker_for_score(score, summary),
    )


def _blocker_for_score(score: int | None, summary: str) -> dict[str, Any] | None:
    if score is None or score >= 70:
        return None
    return {
        "code": "narrative_flow_weak",
        "severity": "blocker",
        "slide_index": None,
        "message": f"Boardroom rehearsal score is {score}/100.",
        "target": "deck_narrative",
        "recommendation": f"Why this matters: boardroom.rehearsal. {summary}".strip(),
    }


def _build_prompt(slides: Sequence[Any]) -> str:
    lines = []
    for idx, slide in enumerate(slides[:20]):
        if isinstance(slide, Mapping):
            props = _props(slide)
            headline = props.get("headline") or props.get("title") or slide.get("headline") or ""
            intent = slide.get("intent") or slide.get("slide_intent") or ""
        else:
            headline = getattr(slide, "headline", "")
            intent = getattr(slide, "intent", "")
        lines.append(f"{idx + 1}. intent={intent}; headline={headline}")
    return (
        "Score this deck's boardroom narrative flow from 0-100. "
        "Evaluate whether the story has a clear opening, pain, answer, proof, and ask.\n"
        + "\n".join(lines)
    )


def _props(slide: Mapping[str, Any]) -> Mapping[str, Any]:
    artifacts = slide.get("artifacts")
    if isinstance(artifacts, Mapping):
        kit = artifacts.get("kit_jsx")
        if isinstance(kit, Mapping) and isinstance(kit.get("props_json"), Mapping):
            return kit["props_json"]
    render_props = slide.get("render_props")
    if isinstance(render_props, Mapping):
        return render_props
    return {}


def _parse_response(content: str) -> dict[str, Any]:
    text = str(content or "").strip()
    if not text:
        return {"score": 100, "summary": "Empty judge response."}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    score_match = re.search(r"\b(\d{1,3})\b", text)
    return {
        "score": _coerce_score(score_match.group(1) if score_match else 100),
        "summary": text[:280],
    }


def _coerce_score(value: Any) -> int | None:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, score))


__all__ = [
    "BoardroomJudgeResult",
    "merge_boardroom_judge_into_gate",
    "run_boardroom_judge",
]
