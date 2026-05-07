"""
Phase 8 — thin-slice edit operations.

Goal: let the user edit a single prop on a compiled slide
(`stats.0.value`, `bullets.2`, `headline`) without re-running the
writer or paid research APIs. Pure local transform → recompile that
slide's artifacts → re-score → bump artifact_version → emit
`slide_updated` over the existing pipeline channel.

Why this matters
----------------
The standing user mandate is "no fake/dummy data". A slice edit
preserves exactly what the user typed; we never invent or auto-fill
anything. If the user clears a field, the field becomes empty (not
"sample text").

Path syntax
-----------
Dotted paths over the kit_jsx props_json:
    "headline"
    "subheadline"
    "stats.0.value"
    "bullets.2"
    "team.0.name"

Operations supported
--------------------
* ``replace`` (default) — set the leaf at `path` to `value`. Path must
    already exist; type of `value` must match the existing leaf
    (str↔str, number↔number, bool↔bool, list↔list, dict↔dict).
* ``insert`` — insert one item into an allowlisted list path.
* ``remove`` — remove an allowlisted list item or clear an optional leaf.
* ``move`` — reorder an item within the same allowlisted sibling list.
* ``swap-image`` — set an approved uploaded/stored image URL.
* ``set-crop`` — store non-destructive crop/focal metadata.
* ``set-layout-variant`` — update compiler-supported enum variants.

Refusal modes (no fabrication, no shape escapes):
    - Path empty / does not resolve → 422.
    - Type mismatch → 422.
    - Path tries to create a new top-level key → 422.
    - Value beyond hard size cap (str > 4000, list > 100) → 422.

Public API
----------
    apply_slice_ops(
        *,
        slide=<compiled_slide_dict>,
        ops=[{"path": "headline", "value": "New title"}, ...],
        design_tokens={...},
    ) -> {"slide": updated_dict, "fields_changed": [...], "diff": [...]}

The function MUTATES `slide` in place AND returns it inside the
result envelope so callers can pick whichever style they prefer.
"""

from __future__ import annotations

import copy
import hashlib
import json
from urllib.parse import urlparse
from typing import Any, Mapping, Sequence

import structlog

from app.config import LOCALHOST_CORS_ORIGINS, settings
from app.services.v4.engine_transformer import build_engine
from app.services.v4.html_transformer import build_html_css_js
from app.services.v4.quality_scorer import score_slide
from app.services.v4.reveal_legacy_transformer import build_reveal_legacy

logger = structlog.get_logger(__name__)

# Hard caps — protect Mongo doc size and downstream renderers.
_MAX_STRING_LEN = 4000
_MAX_LIST_LEN = 100
_MAX_OPS_PER_REQUEST = 25
_MAX_URL_LEN = 1200

_SUPPORTED_OPS = {
    "replace",
    "insert",
    "remove",
    "move",
    "swap-image",
    "set-crop",
    "set-layout-variant",
}

_LIST_PATHS_BY_KIT: dict[str, set[str]] = {
    "StatHero": {"stats"},
    "FeatureGrid": {"features"},
    "TimelineBlock": {"milestones"},
    "ComparisonBlock": {"columns", "rows"},
    "TeamGrid": {"members"},
    "ChartBlock": {"data", "yKeys"},
    "DiagramBlock": {"nodes", "edges"},
}

_LIST_REQUIRED_KEYS: dict[str, set[str]] = {
    "stats": {"value", "label"},
    "features": {"title", "description"},
    "milestones": {"date", "title"},
    "columns": {"name"},
    "rows": {"feature", "values"},
    "members": {"name", "role"},
    "data": set(),
    "nodes": {"id", "label", "x", "y"},
    "edges": {"from", "to"},
}

_IMAGE_FIELD_NAMES = {"imageUrl", "logoUrl", "photoUrl", "image_url", "logo_url", "photo_url"}
_APPROVED_IMAGE_PATH_PREFIXES = ("/api/v4/images/", "/uploads/team_photos/", "/uploads/slide_images/")
_OPTIONAL_CLEAR_LEAVES = {
    "subheadline", "eyebrow", "footer", "source", "caption", "role", "bio",
    "delta", "tagline", "description", "imageIntent", "image_intent",
    *_IMAGE_FIELD_NAMES,
}
_CROP_TOP_LEVEL_PATHS = {"crop", "imageCrop", "mediaCrop", "image_crop", "media_crop"}
_CROP_NUMBER_RANGES = {
    "x": (0.0, 1.0),
    "y": (0.0, 1.0),
    "width": (0.0, 1.0),
    "height": (0.0, 1.0),
    "focalX": (0.0, 1.0),
    "focalY": (0.0, 1.0),
    "scale": (0.1, 5.0),
    "zoom": (0.1, 5.0),
    "rotation": (-180.0, 180.0),
}
_LAYOUT_VARIANTS_BY_KIT: dict[str, dict[str, set[Any]]] = {
    "TitleHero": {"variant": {"solid", "gradient", "image"}},
    "FullBleedImage": {
        "overlay": {"none", "scrim-bottom", "scrim-full", "duotone"},
        "align": {"left", "center", "right", "bottom-left", "bottom-right"},
    },
    "QuoteBlock": {"variant": {"default", "accent"}},
    "StatHero": {"align": {"left", "center"}},
    "TimelineBlock": {"orientation": {"horizontal", "vertical"}},
    "FeatureGrid": {"columns": {2, 3, 4}},
    "TeamGrid": {"columns": {2, 3, 4}},
    "ChartBlock": {"type": {"bar", "line", "area", "pie", "radar"}},
    "DiagramBlock": {"nodes.*.variant": {"primary", "secondary", "muted"}},
}


class SliceEditError(ValueError):
    """Raised on invalid ops; carries an HTTP-friendly message."""

    def __init__(self, message: str, *, path: str = "", code: str = "invalid_op") -> None:
        super().__init__(message)
        self.path = path
        self.code = code


# ── Path parsing ─────────────────────────────────────────────────


def _parse_path(path: str) -> list[str | int]:
    """Dotted path → list of steps. Numeric segments become ints so
    list indexing works. Rejects empty segments."""
    if not isinstance(path, str) or not path.strip():
        raise SliceEditError("path is required", path=path or "", code="empty_path")
    parts = path.split(".")
    out: list[str | int] = []
    for seg in parts:
        if seg == "":
            raise SliceEditError(
                f"path {path!r} contains an empty segment", path=path, code="empty_segment"
            )
        if seg.lstrip("-").isdigit():
            out.append(int(seg))
        else:
            out.append(seg)
    return out


def _resolve_existing(root: Any, path: Sequence[str | int]) -> Any:
    """Walk `path` from `root`. Raises SliceEditError if the path
    does not resolve to an existing node."""
    cursor: Any = root
    for step in path:
        if isinstance(step, int):
            if not isinstance(cursor, list):
                raise SliceEditError(
                    f"path step {step} expects a list",
                    path=_render_path(path), code="not_a_list",
                )
            if step < 0 or step >= len(cursor):
                raise SliceEditError(
                    f"index {step} out of range",
                    path=_render_path(path), code="index_out_of_range",
                )
            cursor = cursor[step]
        else:
            if not isinstance(cursor, dict):
                raise SliceEditError(
                    f"path step {step!r} expects a dict",
                    path=_render_path(path), code="not_a_dict",
                )
            if step not in cursor:
                raise SliceEditError(
                    f"key {step!r} does not exist",
                    path=_render_path(path), code="unknown_key",
                )
            cursor = cursor[step]
    return cursor


def _set_at_path(root: Any, path: Sequence[str | int], value: Any) -> None:
    """Set the leaf at `path` to `value`. Caller must have validated
    the path resolves first; we still defend in depth here."""
    if not path:
        raise SliceEditError("empty path", code="empty_path")
    cursor: Any = root
    for step in path[:-1]:
        cursor = cursor[step]
    last = path[-1]
    cursor[last] = value


def _render_path(path: Sequence[str | int]) -> str:
    parts: list[str] = []
    for step in path:
        if isinstance(step, int):
            parts.append(f".{step}" if parts else str(step))
        else:
            parts.append(f".{step}" if parts else step)
    return "".join(parts)


def _bucket(v: Any) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int) or isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    if v is None:
        return "null"
    return type(v).__name__


def _top_level_key_exists_or_allowed(props: Mapping[str, Any], path: Sequence[str | int], path_str: str) -> None:
    first = path[0]
    if isinstance(first, str) and first not in props:
        raise SliceEditError(
            f"top-level key {first!r} does not exist on this slide",
            path=path_str, code="unknown_top_level",
        )


def _is_image_leaf(path: Sequence[str | int]) -> bool:
    return bool(path and isinstance(path[-1], str) and path[-1] in _IMAGE_FIELD_NAMES)


def _parent_path(path: Sequence[str | int]) -> list[str | int]:
    if len(path) < 2:
        raise SliceEditError("operation requires a parent path", path=_render_path(path), code="missing_parent")
    return list(path[:-1])


def _last_index_for_list_op(path: Sequence[str | int], *, allow_append: bool = False) -> int | str:
    if not path:
        raise SliceEditError("empty path", code="empty_path")
    last = path[-1]
    if last == "-" and allow_append:
        return "-"
    if not isinstance(last, int):
        raise SliceEditError(
            "list operation path must end in an array index",
            path=_render_path(path), code="bad_list_index",
        )
    return last


def _list_parent_for_op(root: Any, path: Sequence[str | int], *, allow_append: bool = False) -> tuple[list[Any], int | str, str]:
    index = _last_index_for_list_op(path, allow_append=allow_append)
    parent_steps = _parent_path(path)
    parent = _resolve_existing(root, parent_steps)
    parent_path = _render_path(parent_steps)
    if not isinstance(parent, list):
        raise SliceEditError(
            f"path {parent_path!r} is not a list",
            path=parent_path, code="not_a_list",
        )
    return parent, index, parent_path


def _ensure_list_path_allowed(kit: str, parent_path: str) -> None:
    allowed = _LIST_PATHS_BY_KIT.get(kit, set())
    if parent_path not in allowed:
        raise SliceEditError(
            f"list path {parent_path!r} is not editable for kit {kit!r}",
            path=parent_path, code="path_not_allowlisted",
        )


def _check_insert_item_shape(parent_path: str, parent: list[Any], value: Any, path: str) -> None:
    _check_size_cap(value, path)
    if parent:
        exemplar = parent[0]
        _check_value_compat(exemplar, value, path)
        if isinstance(exemplar, dict) and isinstance(value, dict):
            allowed_keys = set(exemplar.keys())
            unknown = sorted(set(value.keys()) - allowed_keys)
            if unknown:
                raise SliceEditError(
                    f"insert at {path} has unsupported keys: {unknown[:6]}",
                    path=path, code="unknown_item_key",
                )
            required = {
                key for key in allowed_keys
                if key not in _OPTIONAL_CLEAR_LEAVES and exemplar.get(key) is not None
            }
            missing = sorted(required - set(value.keys()))
            if missing:
                raise SliceEditError(
                    f"insert at {path} is missing required keys: {missing[:6]}",
                    path=path, code="missing_item_key",
                )
            for key, next_value in value.items():
                if key in exemplar:
                    _check_value_compat(exemplar.get(key), next_value, f"{path}.{key}")
                    _check_size_cap(next_value, f"{path}.{key}")
        return

    list_name = parent_path.split(".")[-1]
    required_keys = _LIST_REQUIRED_KEYS.get(list_name)
    if required_keys is None:
        return
    if list_name in {"data"}:
        if not isinstance(value, dict):
            raise SliceEditError(f"{parent_path} items must be objects", path=path, code="type_mismatch")
        return
    if list_name == "yKeys":
        if not isinstance(value, str):
            raise SliceEditError(f"{parent_path} items must be strings", path=path, code="type_mismatch")
        return
    if not isinstance(value, dict):
        raise SliceEditError(f"{parent_path} items must be objects", path=path, code="type_mismatch")
    missing = sorted(required_keys - set(value.keys()))
    if missing:
        raise SliceEditError(
            f"insert at {path} is missing required keys: {missing[:6]}",
            path=path, code="missing_item_key",
        )


def _validate_image_url(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SliceEditError("image URL must be a non-empty string", path=path, code="bad_image_url")
    url = value.strip()
    if len(url) > _MAX_URL_LEN:
        raise SliceEditError(f"image URL exceeds {_MAX_URL_LEN} chars", path=path, code="url_too_long")
    if url.startswith(_APPROVED_IMAGE_PATH_PREFIXES):
        return url
    parsed = urlparse(url)
    if (
        parsed.scheme in {"http", "https"}
        and parsed.path.startswith(_APPROVED_IMAGE_PATH_PREFIXES)
        and _is_allowed_image_host(parsed.netloc)
    ):
        return url
    raise SliceEditError(
        "image URL must point to a stored /api/v4/images or uploaded /uploads asset",
        path=path, code="unapproved_image_url",
    )


def _is_allowed_image_host(netloc: str) -> bool:
    if not netloc:
        return True
    allowed: set[str] = {"localhost", "127.0.0.1", "localhost:8003", "127.0.0.1:8003"}
    for raw in [settings.PUBLIC_BASE_URL, *LOCALHOST_CORS_ORIGINS]:
        parsed = urlparse(raw or "")
        if parsed.netloc:
            allowed.add(parsed.netloc.lower())
    return netloc.lower() in allowed


def _validate_crop_payload(value: Any, path: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise SliceEditError("crop payload must be an object", path=path, code="bad_crop_payload")
    if not value:
        raise SliceEditError("crop payload cannot be empty", path=path, code="bad_crop_payload")
    unknown = sorted(set(value.keys()) - set(_CROP_NUMBER_RANGES.keys()))
    if unknown:
        raise SliceEditError(
            f"crop payload has unsupported keys: {unknown[:6]}",
            path=path, code="unknown_crop_key",
        )
    out: dict[str, float] = {}
    for key, raw in value.items():
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise SliceEditError(f"crop value {key!r} must be numeric", path=path, code="bad_crop_value")
        lo, hi = _CROP_NUMBER_RANGES[str(key)]
        number = float(raw)
        if number < lo or number > hi:
            raise SliceEditError(
                f"crop value {key!r} must be between {lo} and {hi}",
                path=path, code="crop_out_of_range",
            )
        out[str(key)] = number
    return out


def _layout_variant_key(path: Sequence[str | int]) -> str:
    if len(path) == 1 and isinstance(path[0], str):
        return path[0]
    if len(path) == 3 and isinstance(path[0], str) and isinstance(path[1], int) and isinstance(path[2], str):
        return f"{path[0]}.*.{path[2]}"
    return _render_path(path)


def _validate_layout_variant(kit: str, path: Sequence[str | int], value: Any, path_str: str) -> Any:
    variants = _LAYOUT_VARIANTS_BY_KIT.get(kit, {})
    key = _layout_variant_key(path)
    allowed = variants.get(key)
    if not allowed:
        raise SliceEditError(
            f"layout variant path {path_str!r} is not supported for kit {kit!r}",
            path=path_str, code="variant_not_supported",
        )
    normalized = value
    if all(isinstance(item, int) for item in allowed):
        if isinstance(value, bool):
            raise SliceEditError("layout variant must be numeric", path=path_str, code="bad_variant")
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise SliceEditError("layout variant must be numeric", path=path_str, code="bad_variant") from exc
    elif isinstance(value, str):
        normalized = value.strip()
    if normalized not in allowed:
        raise SliceEditError(
            f"unsupported layout variant {value!r}; allowed={sorted(allowed)}",
            path=path_str, code="variant_not_allowed",
        )
    return normalized


# ── Type / size validation ────────────────────────────────────────


def _check_value_compat(existing: Any, value: Any, path: str) -> None:
    """Reject ops that would change a leaf's runtime type. This keeps
    the kit components from rendering NaN-ish junk when, e.g., a
    user replaces a number with a list."""
    eb = _bucket(existing)
    nb = _bucket(value)
    # null-out is allowed only on optional-looking fields; we err on
    # the side of strictness — the editor explicitly chose this leaf,
    # so it should know its type. The exception is `string` ↔ `null`,
    # which is how kits represent "field cleared".
    if eb == nb:
        return
    if {eb, nb} == {"string", "null"}:
        return
    if {eb, nb} == {"number", "null"}:
        return
    raise SliceEditError(
        f"type mismatch at {path}: existing={eb}, incoming={nb}",
        path=path, code="type_mismatch",
    )


def _check_size_cap(value: Any, path: str) -> None:
    if isinstance(value, str) and len(value) > _MAX_STRING_LEN:
        raise SliceEditError(
            f"string at {path} exceeds {_MAX_STRING_LEN} chars",
            path=path, code="string_too_long",
        )
    if isinstance(value, list) and len(value) > _MAX_LIST_LEN:
        raise SliceEditError(
            f"list at {path} exceeds {_MAX_LIST_LEN} items",
            path=path, code="list_too_long",
        )


def _apply_replace(root: dict[str, Any], raw_op: Mapping[str, Any], path: list[str | int], path_str: str) -> dict[str, Any] | None:
    _top_level_key_exists_or_allowed(root, path, path_str)
    existing = _resolve_existing(root, path)
    new_value = raw_op.get("value", None)
    _check_value_compat(existing, new_value, path_str)
    _check_size_cap(new_value, path_str)
    if existing == new_value:
        return None
    _set_at_path(root, path, new_value)
    return {"path": path_str, "before": copy.deepcopy(existing), "after": copy.deepcopy(new_value)}


def _apply_insert(kit: str, root: dict[str, Any], raw_op: Mapping[str, Any], path: list[str | int], path_str: str) -> dict[str, Any] | None:
    parent, index, parent_path = _list_parent_for_op(root, path, allow_append=True)
    _ensure_list_path_allowed(kit, parent_path)
    if len(parent) >= _MAX_LIST_LEN:
        raise SliceEditError(f"list at {parent_path} is already at max length", path=parent_path, code="list_too_long")
    insert_at = len(parent) if index == "-" else int(index)
    if insert_at < 0 or insert_at > len(parent):
        raise SliceEditError("insert index out of range", path=path_str, code="index_out_of_range")
    value = raw_op.get("value", None)
    _check_insert_item_shape(parent_path, parent, value, path_str)
    parent.insert(insert_at, copy.deepcopy(value))
    return {"path": parent_path, "before": None, "after": copy.deepcopy(parent)}


def _apply_remove(kit: str, root: dict[str, Any], path: list[str | int], path_str: str) -> dict[str, Any] | None:
    if path and isinstance(path[-1], int):
        parent, index, parent_path = _list_parent_for_op(root, path)
        _ensure_list_path_allowed(kit, parent_path)
        remove_at = int(index)
        if remove_at < 0 or remove_at >= len(parent):
            raise SliceEditError("remove index out of range", path=path_str, code="index_out_of_range")
        before_item = copy.deepcopy(parent[remove_at])
        parent.pop(remove_at)
        return {"path": parent_path, "before": before_item, "after": copy.deepcopy(parent)}

    _top_level_key_exists_or_allowed(root, path, path_str)
    existing = _resolve_existing(root, path)
    leaf = path[-1] if path else None
    if not isinstance(leaf, str) or leaf not in _OPTIONAL_CLEAR_LEAVES:
        raise SliceEditError(
            "remove is only allowed for list items or optional leaves",
            path=path_str, code="remove_not_allowed",
        )
    if existing is None:
        return None
    _set_at_path(root, path, None)
    return {"path": path_str, "before": copy.deepcopy(existing), "after": None}


def _apply_move(kit: str, root: dict[str, Any], raw_op: Mapping[str, Any], path: list[str | int], path_str: str) -> dict[str, Any] | None:
    from_value = raw_op.get("from_path") or raw_op.get("from")
    from_path_str = str(from_value or "")
    from_path = _parse_path(from_path_str)
    to_parent, to_index, to_parent_path = _list_parent_for_op(root, path, allow_append=True)
    from_parent, from_index, from_parent_path = _list_parent_for_op(root, from_path)
    _ensure_list_path_allowed(kit, to_parent_path)
    if from_parent_path != to_parent_path or from_parent is not to_parent:
        raise SliceEditError("move only supports reordering within the same sibling list", path=path_str, code="move_cross_parent")
    move_from = int(from_index)
    if move_from < 0 or move_from >= len(to_parent):
        raise SliceEditError("move source index out of range", path=from_path_str, code="index_out_of_range")
    moving = to_parent.pop(move_from)
    move_to = len(to_parent) if to_index == "-" else int(to_index)
    if move_to < 0 or move_to > len(to_parent):
        to_parent.insert(move_from, moving)
        raise SliceEditError("move destination index out of range", path=path_str, code="index_out_of_range")
    if move_to == move_from:
        to_parent.insert(move_from, moving)
        return None
    to_parent.insert(move_to, moving)
    return {"path": to_parent_path, "before": from_path_str, "after": path_str}


def _apply_swap_image(root: dict[str, Any], raw_op: Mapping[str, Any], path: list[str | int], path_str: str) -> dict[str, Any] | None:
    if not _is_image_leaf(path):
        raise SliceEditError("swap-image can only target image/logo/photo URL fields", path=path_str, code="not_image_path")
    new_url = _validate_image_url(raw_op.get("value", None), path_str)
    try:
        existing = _resolve_existing(root, path)
    except SliceEditError as exc:
        if exc.code not in {"unknown_key"}:
            raise
        parent = _resolve_existing(root, _parent_path(path)) if len(path) > 1 else root
        if not isinstance(parent, dict):
            raise
        existing = None
    if existing is not None and not isinstance(existing, str):
        raise SliceEditError("image URL field must be a string or null", path=path_str, code="type_mismatch")
    if existing == new_url:
        return None
    parent = _resolve_existing(root, _parent_path(path)) if len(path) > 1 else root
    if not isinstance(parent, dict):
        raise SliceEditError("image URL parent must be an object", path=path_str, code="not_a_dict")
    parent[path[-1]] = new_url
    return {"path": path_str, "before": copy.deepcopy(existing), "after": new_url}


def _apply_set_crop(root: dict[str, Any], raw_op: Mapping[str, Any], path: list[str | int], path_str: str) -> dict[str, Any] | None:
    leaf = path[-1] if path else None
    if not isinstance(leaf, str) or (leaf not in _CROP_TOP_LEVEL_PATHS and not leaf.lower().endswith("crop")):
        raise SliceEditError("set-crop can only target crop metadata fields", path=path_str, code="not_crop_path")
    crop = _validate_crop_payload(raw_op.get("value", None), path_str)
    if len(path) == 1 and leaf not in root:
        existing = None
        root[leaf] = crop
        return {"path": path_str, "before": existing, "after": copy.deepcopy(crop)}
    try:
        existing = _resolve_existing(root, path)
    except SliceEditError as exc:
        if exc.code != "unknown_key":
            raise
        parent = _resolve_existing(root, _parent_path(path))
        if not isinstance(parent, dict):
            raise SliceEditError("crop parent must be an object", path=path_str, code="not_a_dict") from exc
        existing = None
        parent[leaf] = crop
        return {"path": path_str, "before": existing, "after": copy.deepcopy(crop)}
    if existing is not None and not isinstance(existing, Mapping):
        raise SliceEditError("existing crop metadata must be an object", path=path_str, code="type_mismatch")
    if existing == crop:
        return None
    _set_at_path(root, path, crop)
    return {"path": path_str, "before": copy.deepcopy(existing), "after": copy.deepcopy(crop)}


def _apply_layout_variant(kit: str, root: dict[str, Any], raw_op: Mapping[str, Any], path: list[str | int], path_str: str) -> dict[str, Any] | None:
    _top_level_key_exists_or_allowed(root, path, path_str)
    existing = _resolve_existing(root, path)
    next_value = _validate_layout_variant(kit, path, raw_op.get("value", None), path_str)
    _check_value_compat(existing, next_value, path_str)
    if existing == next_value:
        return None
    _set_at_path(root, path, next_value)
    return {"path": path_str, "before": copy.deepcopy(existing), "after": copy.deepcopy(next_value)}


def _apply_one_op(kit: str, root: dict[str, Any], raw_op: Mapping[str, Any]) -> dict[str, Any] | None:
    op_kind = str(raw_op.get("op") or "replace")
    if op_kind not in _SUPPORTED_OPS:
        raise SliceEditError(
            f"unsupported op {op_kind!r}",
            code="unsupported_op",
        )
    path_str = str(raw_op.get("path") or "")
    path = _parse_path(path_str)
    if op_kind == "replace":
        return _apply_replace(root, raw_op, path, path_str)
    if op_kind == "insert":
        return _apply_insert(kit, root, raw_op, path, path_str)
    if op_kind == "remove":
        return _apply_remove(kit, root, path, path_str)
    if op_kind == "move":
        return _apply_move(kit, root, raw_op, path, path_str)
    if op_kind == "swap-image":
        return _apply_swap_image(root, raw_op, path, path_str)
    if op_kind == "set-crop":
        return _apply_set_crop(root, raw_op, path, path_str)
    if op_kind == "set-layout-variant":
        return _apply_layout_variant(kit, root, raw_op, path, path_str)
    raise SliceEditError(f"unsupported op {op_kind!r}", code="unsupported_op")


# ── Artifact rebuild (single slide) ───────────────────────────────


def _rebuild_artifacts(*, slide: dict, kit: str, props: dict) -> None:
    """Rebuild kit_jsx + html_css_js + engine + reveal_legacy on the
    given slide using the new props. Mirrors
    `hot_swap._commit_remediated_props` so both paths stay in lock-
    step on artifact shape."""
    from app.services.v4.slide_compiler import _render_jsx  # local: avoid cycle

    artifacts = slide.setdefault("artifacts", {})
    animation_ir = slide.get("animation_ir")
    slide_id = slide.get("slide_id")

    new_jsx = _render_jsx(kit=kit, props=props)
    artifacts["kit_jsx"] = {
        "source": new_jsx,
        "kit_component": kit,
        "props_json": json.loads(json.dumps(props, ensure_ascii=False)),
        "fingerprint": hashlib.sha1(new_jsx.encode("utf-8")).hexdigest()[:12],
    }
    # Legacy mirror — current sandbox runtime path still reads this.
    slide["jsx_source"] = new_jsx

    artifacts["html_css_js"] = build_html_css_js(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
        deck_title=None,
    )
    artifacts["engine"] = build_engine(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )
    artifacts["reveal_legacy"] = build_reveal_legacy(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )


# ── Public entry point ───────────────────────────────────────────


def apply_slice_ops(
    *,
    slide: dict[str, Any],
    ops: Sequence[Mapping[str, Any]],
    design_tokens: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply a sequence of slice edits. Returns:

        {
          "slide": <updated dict>,
          "fields_changed": ["headline", "stats.0.value", ...],
          "artifact_version": <new int>,
          "quality_score": <new score dict>,
        }

    Mutates `slide` in place. Raises `SliceEditError` on any invalid
    op — we never partially-apply: if op N fails, the slide is left
    untouched (we work on a copy of props until all ops succeed).
    """
    if not isinstance(slide, dict):
        raise SliceEditError("slide must be a dict", code="bad_slide")
    if not isinstance(ops, Sequence) or len(ops) == 0:
        raise SliceEditError("ops must be a non-empty list", code="empty_ops")
    if len(ops) > _MAX_OPS_PER_REQUEST:
        raise SliceEditError(
            f"too many ops in one request (>{_MAX_OPS_PER_REQUEST})",
            code="too_many_ops",
        )

    artifacts = slide.get("artifacts") or {}
    kit_jsx = artifacts.get("kit_jsx") if isinstance(artifacts, Mapping) else None
    if not isinstance(kit_jsx, Mapping):
        raise SliceEditError("slide is missing artifacts.kit_jsx", code="no_kit_jsx")
    kit = kit_jsx.get("kit_component") or slide.get("kit_component") or ""
    if not kit:
        raise SliceEditError("slide is missing kit_component", code="no_kit")
    src_props = kit_jsx.get("props_json")
    if not isinstance(src_props, Mapping):
        raise SliceEditError("slide is missing kit_jsx.props_json", code="no_props")

    # Stage all ops on a deep-copy first; only commit on success.
    staged_props: dict[str, Any] = copy.deepcopy(dict(src_props))
    fields_changed: list[str] = []
    diff: list[dict[str, Any]] = []

    for raw_op in ops:
        if not isinstance(raw_op, Mapping):
            raise SliceEditError("op must be an object", code="bad_op")
        op_diff = _apply_one_op(kit, staged_props, raw_op)
        if op_diff is None:
            continue
        path_str = str(op_diff["path"])
        fields_changed.append(path_str)
        diff.append(op_diff)

    if not fields_changed:
        # Nothing actually changed — return early without touching
        # artifacts or version.
        return {
            "slide": slide,
            "fields_changed": [],
            "artifact_version": slide.get("artifact_version"),
            "quality_score": slide.get("quality_score"),
            "diff": [],
            "noop": True,
        }

    # Commit: rebuild artifacts + re-score + bump version.
    _rebuild_artifacts(slide=slide, kit=kit, props=staged_props)
    new_score = score_slide(
        kit=kit,
        props=staged_props,
        design_tokens=design_tokens or {},
    )
    slide["quality_score"] = new_score

    cur_version = slide.get("artifact_version")
    if not isinstance(cur_version, int) or cur_version < 1:
        cur_version = 1
    slide["artifact_version"] = cur_version + 1

    logger.info(
        "v4_slice_edit_applied",
        slide_id=slide.get("slide_id"),
        fields_changed=fields_changed,
        new_quality=new_score.get("overall"),
        new_version=slide["artifact_version"],
    )
    return {
        "slide": slide,
        "fields_changed": fields_changed,
        "artifact_version": slide["artifact_version"],
        "quality_score": new_score,
        "diff": diff,
        "noop": False,
    }


__all__ = [
    "apply_slice_ops",
    "SliceEditError",
    "_parse_path",
    "_resolve_existing",
    "_check_value_compat",
    "_check_size_cap",
    "_rebuild_artifacts",
    "_validate_image_url",
    "_validate_crop_payload",
]
