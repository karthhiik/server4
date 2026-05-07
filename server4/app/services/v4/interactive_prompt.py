"""
V4 Interactive Prompt — pause the pipeline mid-generation to ask the user a
small structured question (currently: team-member details, optional company
icon upload).

Mechanism:

  1. Pipeline emits a progress event: stage="awaiting_input", payload contains
     a `question_id`, `kind`, `schema` (form fields), `deadline_ts`, and
     `optional` flag. Frontend listens for this event and renders a form.

  2. Pipeline polls Redis key `v4:answer:{project_id}:{question_id}` (set by
     POST /api/v4/generation/{project_id}/answer). When a value appears, it's
     parsed as JSON and returned. If the user skips, frontend posts
     `{"skipped": true}` and we return None.

    3. If no answer arrives within `timeout_s` we return None and the caller
         proceeds with an honest unresolved state, never invented data.

Only use this in stages where pausing is acceptable. Team-member collection is
handled by the editor after generation because missing founder profiles must not
delay the first usable deck.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)

ProgressCallback = Callable[[str, dict[str, Any]], Awaitable[None]]

POLL_INTERVAL_S = 0.75
ANSWER_KEY = "v4:answer:{project_id}:{question_id}"
ANSWER_TTL_S = 300


async def _redis():
    try:
        from app.utils.rate_limiter import get_redis
        return await get_redis()
    except Exception:
        return None


async def store_answer(project_id: str, question_id: str, payload: dict[str, Any]) -> bool:
    r = await _redis()
    if r is None:
        return False
    key = ANSWER_KEY.format(project_id=project_id, question_id=question_id)
    try:
        await r.setex(key, ANSWER_TTL_S, json.dumps(payload, default=str))
        return True
    except Exception as e:
        logger.warning("v4_store_answer_failed", error=str(e))
        return False


async def _poll_answer(project_id: str, question_id: str, deadline: float) -> Optional[dict[str, Any]]:
    r = await _redis()
    if r is None:
        return None
    key = ANSWER_KEY.format(project_id=project_id, question_id=question_id)
    while time.monotonic() < deadline:
        try:
            raw = await r.get(key)
            if raw:
                # Consume the answer so it can't be re-used.
                await r.delete(key)
                return json.loads(raw)
        except Exception as e:
            logger.debug("v4_poll_answer_error", error=str(e))
        await asyncio.sleep(POLL_INTERVAL_S)
    return None


async def ask(
    *,
    project_id: str,
    emit: ProgressCallback,
    kind: str,
    schema: dict[str, Any],
    optional: bool = True,
    timeout_s: float = 60.0,
    prefill: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Emit an `awaiting_input` event and wait for the answer.

    Returns the parsed answer payload, or None if the user skipped or timed out.
    """
    question_id = uuid4().hex[:12]
    deadline_ts = datetime.fromtimestamp(time.time() + timeout_s, tz=timezone.utc).isoformat()
    await emit("awaiting_input", {
        "question_id": question_id,
        "kind": kind,
        "schema": schema,
        "optional": optional,
        "timeout_s": timeout_s,
        "deadline_ts": deadline_ts,
        "prefill": prefill or {},
        "answer_endpoint": f"/api/v4/generation/{project_id}/answer",
    })
    deadline = time.monotonic() + timeout_s
    answer = await _poll_answer(project_id, question_id, deadline)
    await emit("input_resolved", {
        "question_id": question_id,
        "kind": kind,
        "skipped": answer is None or bool(answer.get("skipped")),
    })
    if answer is None:
        return None
    if answer.get("skipped"):
        return None
    return answer


# ── Schemas ────────────────────────────────────────────────────────


def team_question_schema(suggested_size: int = 3) -> dict[str, Any]:
    return {
        "title": "Add your team",
        "description": "We could not find verified team-member details. Add 1-6 founders/leads, "
                   "or skip and we'll leave this team slide unresolved for editing later.",
        "fields": [
            {
                "name": "members",
                "type": "list",
                "min_items": 1,
                "max_items": 6,
                "suggested_items": suggested_size,
                "item_schema": {
                    "name": {"type": "string", "required": True, "max_length": 80},
                    "role": {"type": "string", "required": True, "max_length": 80,
                             "examples": ["CEO", "CTO", "Co-founder", "VP Engineering"]},
                    "linkedin_url": {"type": "url", "required": False},
                    "bio": {"type": "string", "required": False, "max_length": 240},
                    "photo_url": {"type": "url", "required": False,
                                  "help": "Optional. Leave empty to auto-fetch."},
                },
            },
        ],
    }


def company_icon_question_schema() -> dict[str, Any]:
    return {
        "title": "Upload your company icon",
        "description": "Optional — if you upload a logo we'll use it on the title and team slides. "
                       "Otherwise we'll skip the icon.",
        "fields": [
            {
                "name": "icon",
                "type": "file_upload",
                "required": False,
                "accept": ["image/png", "image/svg+xml", "image/jpeg", "image/webp"],
                "max_bytes": 2 * 1024 * 1024,
                "upload_endpoint": "/api/v4/projects/{project_id}/company-icon",
            },
        ],
    }
