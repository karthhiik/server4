"""Schema guardrails for V4 planner and writer model output.

These checks sit between model JSON mode and the permissive normalizers in
the planner/writer. They intentionally validate only the shipment-critical
contract: JSON object/list shape, non-empty headline, and at least one real
content signal. Normalization still belongs to the existing parser modules.
"""

from __future__ import annotations

from typing import Any

from app.services.v4.json_repair import JSONRepairFailedError, safe_json_loads


class SchemaValidationError(ValueError):
    """Raised when an LLM response is parseable but not a usable slide/deck."""


def load_json_root(raw: str, *, context: str) -> Any:
    try:
        return safe_json_loads(raw, context=context)
    except JSONRepairFailedError as exc:
        raise SchemaValidationError(f"{context}: invalid JSON") from exc


def validate_writer_output(raw: str, *, slide_index: int) -> dict[str, Any]:
    data = load_json_root(raw or "", context=f"writer:slide={slide_index}")
    if not isinstance(data, dict):
        raise SchemaValidationError(f"writer slide {slide_index}: root must be an object")

    headline = data.get("headline")
    if not isinstance(headline, str) or not headline.strip():
        raise SchemaValidationError(f"writer slide {slide_index}: missing headline")

    _assert_optional_list(data, "bullets", slide_index)
    _assert_optional_list(data, "stat_blocks", slide_index)
    _assert_optional_list(data, "citations", slide_index)
    for key in ("quote", "chart", "table", "timeline", "comparison", "diagram"):
        _assert_optional_dict(data, key, slide_index)

    if not _has_visible_content(data):
        raise SchemaValidationError(f"writer slide {slide_index}: no visible content")

    return data


def validate_planner_slides(slides_raw: Any, *, project_id: str) -> list[dict[str, Any]]:
    if not isinstance(slides_raw, list) or not slides_raw:
        raise SchemaValidationError(f"planner {project_id}: slides must be a non-empty list")

    out: list[dict[str, Any]] = []
    for index, item in enumerate(slides_raw):
        if not isinstance(item, dict):
            raise SchemaValidationError(f"planner {project_id}: slide {index} must be an object")
        if not _has_planner_signal(item):
            raise SchemaValidationError(f"planner {project_id}: slide {index} has no planning fields")
        if "key_points" in item and item.get("key_points") is not None and not isinstance(item.get("key_points"), list):
            raise SchemaValidationError(f"planner {project_id}: slide {index} key_points must be a list")
        if "evidence_refs" in item and item.get("evidence_refs") is not None and not isinstance(item.get("evidence_refs"), list):
            raise SchemaValidationError(f"planner {project_id}: slide {index} evidence_refs must be a list")
        out.append(item)
    return out


def _assert_optional_list(data: dict[str, Any], key: str, slide_index: int) -> None:
    value = data.get(key)
    if value is not None and not isinstance(value, list):
        raise SchemaValidationError(f"writer slide {slide_index}: {key} must be a list")


def _assert_optional_dict(data: dict[str, Any], key: str, slide_index: int) -> None:
    value = data.get(key)
    if value is not None and not isinstance(value, dict):
        raise SchemaValidationError(f"writer slide {slide_index}: {key} must be an object")


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value)


def _non_empty_dict(value: Any) -> bool:
    return isinstance(value, dict) and any(v not in (None, "", [], {}) for v in value.values())


def _has_visible_content(data: dict[str, Any]) -> bool:
    if _non_empty_text(data.get("subheadline")) or _non_empty_text(data.get("body")):
        return True
    if _non_empty_list(data.get("bullets")) or _non_empty_list(data.get("stat_blocks")):
        return True
    if _non_empty_text(data.get("image_prompt")):
        return True
    return any(
        _non_empty_dict(data.get(key))
        for key in ("quote", "chart", "table", "timeline", "comparison", "diagram")
    )


def _has_planner_signal(item: dict[str, Any]) -> bool:
    return any(
        _non_empty_text(item.get(key))
        for key in ("intent", "purpose", "headline_target", "headline", "title", "layout_hint")
    ) or _non_empty_list(item.get("key_points"))