"""
V4 JSON Repair — safe parsing of LLM JSON output.

LLMs frequently return malformed JSON: trailing commas, single quotes,
unescaped newlines inside strings, code-fence wrapping, leading prose.
This module gives a single `safe_json_loads()` that tries:

  1. Plain `json.loads`
  2. Strip code fences and prose, then `json.loads`
  3. `dirtyjson.loads` (forgiving parser)
  4. Bracket-balanced extraction + `dirtyjson.loads`
  5. Raise `JSONRepairFailedError`

Used by skeleton_planner._parse_planner_output and parallel_writer._parse_writer_output.
"""

from __future__ import annotations

import json
import re
from typing import Any

import dirtyjson  # type: ignore[import-untyped]
import structlog

from app.services.v4.errors import V4PipelineError

logger = structlog.get_logger(__name__)


class JSONRepairFailedError(V4PipelineError):
    """Every repair strategy failed."""


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _strip_fences(raw: str) -> str:
    return _FENCE_RE.sub("", raw).strip()


def _extract_balanced(raw: str) -> str | None:
    """Return the largest balanced {...} or [...] substring, or None."""
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        if start < 0:
            continue
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(raw)):
            ch = raw[i]
            if esc:
                esc = False
                continue
            if ch == "\\" and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return raw[start : i + 1]
    return None


def safe_json_loads(raw: str, *, context: str = "llm") -> Any:
    """Return parsed JSON or raise JSONRepairFailedError.

    `context` is a label included in logs for telemetry.
    """
    if raw is None:
        raise JSONRepairFailedError(f"{context}: input is None")
    text = raw.strip()
    if not text:
        raise JSONRepairFailedError(f"{context}: empty input")

    # 1. Plain
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip fences + prose
    stripped = _strip_fences(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 3. dirtyjson on stripped
    try:
        return _to_plain(dirtyjson.loads(stripped))
    except Exception:
        pass

    # 4. Extract balanced block, then dirtyjson
    extracted = _extract_balanced(stripped)
    if extracted:
        try:
            return _to_plain(dirtyjson.loads(extracted))
        except Exception:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass

    logger.warning(
        "json_repair.failed",
        context=context,
        head=text[:200],
        length=len(text),
    )
    raise JSONRepairFailedError(
        f"{context}: could not parse JSON after 4 strategies (len={len(text)})"
    )


def _to_plain(obj: Any) -> Any:
    """Convert dirtyjson's AttributedDict / AttributedList to plain dict/list."""
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(x) for x in obj]
    return obj
