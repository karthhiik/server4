"""Deterministic slide intelligence contract for editor/regeneration UX.

This module does not generate presentation content. It reads the compiled
slide props that already exist and describes what can be edited, regenerated,
validated, or researched. The frontend can use this contract for Canva-style
layer controls without guessing at kit internals or hardcoding a sample deck.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping


_PROTOCOL = "barise.slide-intelligence.v1"
_SCHEMA_VERSION = 1
_MAX_ELEMENTS = 96

_TEXT_KEYS = {
    "headline",
    "subheadline",
    "eyebrow",
    "footer",
    "caption",
    "source",
    "body",
    "quote",
    "attribution",
    "role",
    "bio",
    "title",
    "description",
    "label",
    "name",
    "date",
    "feature",
    "value",
    "delta",
    "ctaLabel",
    "tagline",
}
_IMAGE_KEYS = {
    "imageUrl",
    "logoUrl",
    "photoUrl",
    "mockupUrl",
    "backgroundImageUrl",
    "image_url",
    "logo_url",
    "photo_url",
}
_ICON_KEYS = {"icon", "iconName"}
_NUMBER_KEYS = {"x", "y", "width", "height", "focalX", "focalY", "scale", "zoom"}

_LIST_LABELS = {
    "stats": "Stat",
    "features": "Feature",
    "items": "Item",
    "cards": "Card",
    "milestones": "Milestone",
    "columns": "Comparison column",
    "rows": "Comparison row",
    "members": "Team member",
    "nodes": "Diagram node",
    "edges": "Diagram edge",
    "data": "Chart datum",
    "links": "Link",
    "sources": "Source",
}

_KIT_VARIANTS: dict[str, dict[str, list[Any]]] = {
    "TitleHero": {"variant": ["solid", "gradient", "image"]},
    "FullBleedImage": {
        "overlay": ["none", "scrim-bottom", "scrim-full", "duotone"],
        "align": ["left", "center", "right", "bottom-left", "bottom-right"],
    },
    "QuoteBlock": {"variant": ["default", "accent"]},
    "StatHero": {"align": ["left", "center"]},
    "TimelineBlock": {"orientation": ["horizontal", "vertical"]},
    "FeatureGrid": {"columns": [2, 3, 4]},
    "TeamGrid": {"columns": [2, 3, 4]},
    "ChartBlock": {"type": ["bar", "line", "area", "pie", "radar"]},
}

_ROLE_ALIASES = {
    "title": {"title", "cover", "intro", "opening"},
    "problem": {"problem", "pain", "pain_point"},
    "solution": {"solution", "product", "value_prop", "value proposition"},
    "architecture": {"architecture", "system", "workflow", "how_it_works", "how it works"},
    "benchmark": {"benchmark", "performance", "metrics", "proof", "latency"},
    "market": {"market", "tam", "sam", "som", "opportunity"},
    "traction": {"traction", "evidence", "customers", "pilot"},
    "business_model": {"business_model", "pricing", "revenue"},
    "competition": {"competition", "competitive", "moat", "differentiation"},
    "gtm": {"gtm", "go_to_market", "sales", "distribution"},
    "ask": {"ask", "funding", "investment"},
    "team": {"team", "founders"},
    "closing": {"closing", "thank_you", "thanks"},
}

_ROLE_VISUALS = {
    "title": "hero",
    "problem": "comparison",
    "solution": "feature-grid",
    "architecture": "diagram",
    "benchmark": "chart",
    "market": "chart",
    "traction": "metrics",
    "business_model": "table",
    "competition": "comparison",
    "gtm": "timeline",
    "ask": "metrics",
    "team": "people",
    "closing": "cta",
}

_KIT_VISUALS = {
    "ChartBlock": "chart",
    "DiagramBlock": "diagram",
    "ComparisonBlock": "comparison",
    "TimelineBlock": "timeline",
    "StatHero": "metrics",
    "DataTable": "table",
    "PricingTable": "table",
    "TeamGrid": "people",
    "FullBleedImage": "image",
    "CinematicHero": "image",
    "TitleHero": "hero",
}


def build_slide_intelligence_spec(
    *,
    slide_id: str,
    slide_index: int,
    intent: str | None,
    layout: str | None,
    kit: str,
    props: Mapping[str, Any],
    layer_metadata: Mapping[str, Any] | None = None,
    motion_spec: Mapping[str, Any] | None = None,
    design_tokens: Mapping[str, Any] | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    """Return an editor-safe intelligence contract for a compiled slide."""

    clean_props = props if isinstance(props, Mapping) else {}
    role = _canonical_role(intent, layout, kit)
    layer_index = _layer_index(layer_metadata)
    elements = _discover_elements(
        slide_id=slide_id,
        kit=kit,
        props=clean_props,
        layer_index=layer_index,
    )
    visual = _required_visual(role=role, kit=kit, props=clean_props)
    evidence = _evidence_level(role=role, kit=kit, props=clean_props)
    spec: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "protocol": _PROTOCOL,
        "slide_id": slide_id,
        "slide_index": slide_index,
        "kit": kit,
        "intent": intent or "",
        "layout": layout or "",
        "template_id": template_id,
        "narrative_role": role,
        "required_visual": visual,
        "visual_density": _visual_density(clean_props, elements),
        "editable_elements": elements,
        "canvas_controls": _canvas_controls(
            kit=kit,
            elements=elements,
            motion_spec=motion_spec,
            design_tokens=design_tokens,
        ),
        "regeneration_actions": _regeneration_actions(role, visual, elements, evidence),
        "research_contract": _research_contract(role, evidence, clean_props),
        "quality_gates": _quality_gates(role, kit, visual, evidence),
    }
    spec["fingerprint"] = _fingerprint(spec)
    return spec


def _canonical_role(intent: str | None, layout: str | None, kit: str) -> str:
    haystack = " ".join(str(v or "").lower().replace("-", "_") for v in (intent, layout, kit))
    for role, aliases in _ROLE_ALIASES.items():
        if any(alias.replace("-", "_") in haystack for alias in aliases):
            return role
    if kit in {"ChartBlock", "StatHero", "MetricsDashboard"}:
        return "benchmark"
    if kit in {"ComparisonBlock", "BeforeAfter", "ProblemSolution"}:
        return "competition"
    if kit in {"TimelineBlock", "Roadmap", "ProcessFlow"}:
        return "gtm"
    if kit in {"DiagramBlock"}:
        return "architecture"
    return "content"


def _required_visual(*, role: str, kit: str, props: Mapping[str, Any]) -> str:
    if kit in _KIT_VISUALS:
        return _KIT_VISUALS[kit]
    if props.get("chart") or _has_nonempty_list(props, "data"):
        return "chart"
    if _has_nonempty_list(props, "nodes"):
        return "diagram"
    if _has_nonempty_list(props, "columns") or _has_nonempty_list(props, "rows"):
        return "comparison"
    if _has_nonempty_list(props, "milestones"):
        return "timeline"
    return _ROLE_VISUALS.get(role, "structured-text")


def _evidence_level(*, role: str, kit: str, props: Mapping[str, Any]) -> str:
    has_sources = _has_nonempty_list(props, "sources") or _has_nonempty_list(props, "links")
    has_chart = kit == "ChartBlock" or _has_nonempty_list(props, "data")
    if role in {"benchmark", "market", "traction", "business_model", "ask"}:
        return "sourced" if has_sources else "required"
    if role in {"competition", "architecture"}:
        return "light" if has_sources or has_chart else "recommended"
    return "present" if has_sources else "none"


def _discover_elements(
    *,
    slide_id: str,
    kit: str,
    props: Mapping[str, Any],
    layer_index: Mapping[str, str],
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(path: str, key: str, value: Any, parent_path: str | None = None, index: int | None = None) -> None:
        if len(elements) >= _MAX_ELEMENTS:
            return
        kind = _kind_for_value(key, value, parent_path)
        if kind is None:
            return
        element_key = f"{kind}:{path}"
        if element_key in seen:
            return
        seen.add(element_key)
        constraints = _constraints_for(path=path, key=key, value=value, kit=kit)
        elements.append(
            {
                "element_id": _element_id(path, kind),
                "slide_id": slide_id,
                "path": path,
                "kind": kind,
                "label": _label_for(path, key, parent_path, index),
                "value": value,
                "parent_path": parent_path,
                "sibling_index": index,
                "capabilities": _capabilities_for(kind, path, key),
                "constraints": constraints,
                "source": "compiled-props",
                "layer_id": _match_layer(path, key, layer_index),
                "prompt_hint": _prompt_hint(kind, key, path),
                "quality_checks": _element_quality_checks(kind, key),
            }
        )

    for key, value in props.items():
        if isinstance(value, list):
            if key in _LIST_LABELS:
                _add_container(elements, seen, slide_id, key, value)
            _walk_list(key, value, add)
        elif isinstance(value, Mapping):
            _walk_mapping(key, value, add)
        else:
            add(key, key, value)

    for path, allowed in (_KIT_VARIANTS.get(kit) or {}).items():
        value = _read_path(props, path)
        if value is not None:
            add(path, path.split(".")[-1], value)
            if elements:
                elements[-1]["kind"] = "layout-variant"
                elements[-1]["capabilities"] = ["set-layout-variant"]
                elements[-1]["constraints"] = {"enum": allowed}

    return elements


def _walk_list(base_path: str, values: list[Any], add) -> None:
    for index, item in enumerate(values[:24]):
        item_path = f"{base_path}.{index}"
        if isinstance(item, Mapping):
            for key, value in item.items():
                child_path = f"{item_path}.{key}"
                if isinstance(value, Mapping):
                    _walk_mapping(child_path, value, add)
                elif isinstance(value, list):
                    _walk_list(child_path, value, add)
                else:
                    add(child_path, key, value, base_path, index)
        else:
            add(item_path, base_path, item, base_path, index)


def _walk_mapping(base_path: str, values: Mapping[str, Any], add) -> None:
    for key, value in values.items():
        child_path = f"{base_path}.{key}"
        if isinstance(value, Mapping):
            _walk_mapping(child_path, value, add)
        elif isinstance(value, list):
            _walk_list(child_path, value, add)
        else:
            add(child_path, key, value, base_path)


def _add_container(
    elements: list[dict[str, Any]],
    seen: set[str],
    slide_id: str,
    path: str,
    values: list[Any],
) -> None:
    if not values or len(elements) >= _MAX_ELEMENTS:
        return
    element_key = f"container:{path}"
    if element_key in seen:
        return
    seen.add(element_key)
    elements.append(
        {
            "element_id": _element_id(path, "container"),
            "slide_id": slide_id,
            "path": path,
            "kind": "container",
            "label": _LIST_LABELS.get(path, path.title()),
            "value": {"count": len(values)},
            "capabilities": ["regenerate", "reorder-sibling"],
            "constraints": {"min": 1, "max": 12},
            "source": "compiled-props",
            "layer_id": "",
            "prompt_hint": f"Improve the {path} structure without changing unsupported facts.",
            "quality_checks": ["content_density", "no_prompt_leakage"],
        }
    )


def _kind_for_value(key: str, value: Any, parent_path: str | None) -> str | None:
    if key in _IMAGE_KEYS:
        return "image"
    if key in _ICON_KEYS:
        return "icon"
    if key in _NUMBER_KEYS and isinstance(value, (int, float)):
        return "number"
    if parent_path == "stats" or parent_path and parent_path.startswith("stats."):
        return "stat" if key in {"value", "label", "delta", "trend"} else None
    if parent_path == "data" or parent_path and parent_path.startswith("data."):
        if isinstance(value, (int, float)):
            return "chart-datum"
        if isinstance(value, str):
            return "chart-series"
    if key in _TEXT_KEYS and isinstance(value, (str, int, float)):
        return "number" if isinstance(value, (int, float)) else "text"
    if isinstance(value, str) and (key.endswith("Url") or key.endswith("_url")):
        return "image"
    return None


def _constraints_for(*, path: str, key: str, value: Any, kit: str) -> dict[str, Any]:
    if path in (_KIT_VARIANTS.get(kit) or {}):
        return {"enum": _KIT_VARIANTS[kit][path]}
    if key in _IMAGE_KEYS:
        return {"max_length": 1200, "pattern": "^(https?://|/api/|/uploads/)"}
    if isinstance(value, (int, float)):
        if key in {"x", "y", "focalX", "focalY"}:
            return {"min": 0, "max": 1}
        if key in {"width", "height"}:
            return {"min": 0, "max": 1}
        return {"min": 0, "max": 1000000000}
    max_len = 160
    if key in {"headline", "title"}:
        max_len = 90
    elif key in {"subheadline", "description", "body", "quote"}:
        max_len = 240
    elif key in {"label", "value", "date", "delta"}:
        max_len = 48
    return {"max_length": max_len}


def _capabilities_for(kind: str, path: str, key: str) -> list[str]:
    if kind in {"text", "rich-text", "bullet", "stat"}:
        caps = ["edit-text", "regenerate", "tone-shift"]
        if path.count(".") >= 1:
            caps.append("reorder-sibling")
        return caps
    if kind == "number":
        return ["edit-number", "regenerate"]
    if kind in {"image", "media"}:
        return ["swap-image", "crop-image", "regenerate"]
    if kind == "icon":
        return ["swap-image", "regenerate"]
    if kind in {"chart-series", "chart-datum"}:
        return ["edit-number" if kind == "chart-datum" else "edit-text", "regenerate"]
    if kind == "layout-variant":
        return ["set-layout-variant"]
    return ["regenerate"]


def _canvas_controls(
    *,
    kit: str,
    elements: list[dict[str, Any]],
    motion_spec: Mapping[str, Any] | None,
    design_tokens: Mapping[str, Any] | None,
) -> dict[str, Any]:
    image_paths = [
        {"path": e["path"], "label": e["label"], "capabilities": e["capabilities"]}
        for e in elements
        if e.get("kind") in {"image", "media"}
    ]
    icon_paths = [
        {"path": e["path"], "label": e["label"]}
        for e in elements
        if e.get("kind") == "icon"
    ]
    palette = {}
    if isinstance(design_tokens, Mapping):
        for key in ("primary", "secondary", "accent", "background", "surface", "text"):
            if isinstance(design_tokens.get(key), str):
                palette[key] = design_tokens[key]
    return {
        "background": {
            "operation_surface": "slide_patch",
            "fields": ["background_color", "background_gradient"],
            "supports_brand_safe_palette": True,
            "palette": palette,
        },
        "brand": {
            "operation_surface": "slide_patch",
            "fields": [
                "company_icon_url",
                "company_icon_hidden",
                "company_icon_position",
                "company_icon_opacity",
            ],
        },
        "images": image_paths,
        "icons": icon_paths,
        "layout": {
            "kit": kit,
            "variant_paths": sorted((_KIT_VARIANTS.get(kit) or {}).keys()),
        },
        "motion": {
            "operation_surface": "slide_patch",
            "preset": (motion_spec or {}).get("preset") if isinstance(motion_spec, Mapping) else None,
            "poster_frame": (motion_spec or {}).get("poster_frame") if isinstance(motion_spec, Mapping) else None,
        },
    }


def _regeneration_actions(
    role: str,
    visual: str,
    elements: list[dict[str, Any]],
    evidence: str,
) -> list[dict[str, Any]]:
    actions = [
        {
            "id": "tighten-copy",
            "scope": "text",
            "label": "Tighten slide copy",
            "requires_research": False,
            "target_paths": [e["path"] for e in elements if e.get("kind") in {"text", "stat"}][:12],
        },
        {
            "id": "improve-visual",
            "scope": "visual",
            "label": f"Improve {visual} treatment",
            "requires_research": False,
            "target_paths": [e["path"] for e in elements if e.get("kind") in {"image", "icon", "chart-datum"}][:12],
        },
    ]
    if evidence in {"required", "recommended"}:
        actions.append(
            {
                "id": "refresh-evidence",
                "scope": "research",
                "label": "Find sourced evidence",
                "requires_research": True,
                "target_paths": [],
            }
        )
    if role in {"architecture", "benchmark", "market", "competition"}:
        actions.append(
            {
                "id": "switch-to-proof-layout",
                "scope": "layout",
                "label": "Use proof-first layout",
                "requires_research": role in {"benchmark", "market"},
                "target_paths": [],
            }
        )
    return actions


def _research_contract(role: str, evidence: str, props: Mapping[str, Any]) -> dict[str, Any]:
    source_count = len(props.get("sources") or []) if isinstance(props.get("sources"), list) else 0
    return {
        "requires_sources": evidence in {"required", "sourced"},
        "evidence_level": evidence,
        "source_count": source_count,
        "reject_unsourced_numbers": role in {"market", "benchmark", "traction", "business_model", "ask"},
        "refresh_strategy": "live_search_then_semantic_filter" if evidence in {"required", "recommended"} else "none",
    }


def _quality_gates(role: str, kit: str, visual: str, evidence: str) -> list[str]:
    gates = [
        "no_placeholder",
        "no_prompt_leakage",
        "dedupe_title_subtitle_body",
        "contrast_check",
        "content_density",
        "exportable_objects_not_screenshot",
    ]
    if evidence in {"required", "sourced"}:
        gates.append("claim_source_traceability")
    if role in {"architecture", "benchmark", "market", "competition"}:
        gates.append(f"{visual}_required_for_role")
    if kit in {"FullBleedImage", "CinematicHero", "TitleHero"}:
        gates.append("image_text_contrast")
    return gates


def _visual_density(props: Mapping[str, Any], elements: list[dict[str, Any]]) -> str:
    text_chars = 0
    for value in _iter_values(props):
        if isinstance(value, str):
            text_chars += len(value)
    if text_chars > 900 or len(elements) > 36:
        return "dense"
    if text_chars > 420 or len(elements) > 18:
        return "moderate"
    return "bold"


def _iter_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _iter_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_values(child)
    else:
        yield value


def _layer_index(layer_metadata: Mapping[str, Any] | None) -> dict[str, str]:
    index: dict[str, str] = {}
    if not isinstance(layer_metadata, Mapping):
        return index
    layers = layer_metadata.get("layers")
    if not isinstance(layers, list):
        return index
    for layer in layers:
        if not isinstance(layer, Mapping):
            continue
        layer_id = str(layer.get("id") or layer.get("layer_id") or "")
        label = str(layer.get("label") or layer.get("role") or layer.get("target") or "")
        if layer_id:
            index[layer_id.lower()] = layer_id
        if label and layer_id:
            index[label.lower()] = layer_id
    return index


def _match_layer(path: str, key: str, layer_index: Mapping[str, str]) -> str:
    if not layer_index:
        return ""
    candidates = [
        path.lower(),
        key.lower(),
        path.split(".")[0].lower(),
        path.replace(".", "-").lower(),
    ]
    for candidate in candidates:
        if candidate in layer_index:
            return layer_index[candidate]
    for candidate in candidates:
        for layer_key, layer_id in layer_index.items():
            if candidate and (candidate in layer_key or layer_key in candidate):
                return layer_id
    return ""


def _label_for(path: str, key: str, parent_path: str | None, index: int | None) -> str:
    base = key.replace("_", " ").replace("Url", " URL").strip().title()
    if parent_path:
        prefix = _LIST_LABELS.get(parent_path.split(".")[0], parent_path.split(".")[0].title())
        if index is not None:
            return f"{prefix} {index + 1} {base}"
        return f"{prefix} {base}"
    if path in _LIST_LABELS:
        return _LIST_LABELS[path]
    return base or path


def _element_id(path: str, kind: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()
    return f"{kind}-{safe or 'root'}"


def _prompt_hint(kind: str, key: str, path: str) -> str:
    if kind == "image":
        return "Swap or regenerate this image while preserving slide meaning and brand tone."
    if kind == "icon":
        return "Use a simple symbolic icon that clarifies the surrounding copy."
    if kind in {"chart-datum", "chart-series"}:
        return "Edit only sourced chart data; do not invent benchmark or market numbers."
    if key in {"headline", "title"}:
        return "Make the point sharper in presenter-ready language."
    if key in {"description", "body", "quote"}:
        return "Improve clarity and specificity without adding unsupported claims."
    return f"Edit {path} without changing verified facts."


def _element_quality_checks(kind: str, key: str) -> list[str]:
    checks = ["no_prompt_leakage", "no_placeholder"]
    if kind in {"text", "stat"}:
        checks.extend(["dedupe_with_headline", "glance_test"])
    if kind in {"chart-datum", "chart-series"}:
        checks.append("source_traceability")
    if kind in {"image", "icon"}:
        checks.append("brand_fit")
    if key in {"headline", "title"}:
        checks.append("headline_length")
    return checks


def _has_nonempty_list(props: Mapping[str, Any], key: str) -> bool:
    value = props.get(key)
    return isinstance(value, list) and bool(value)


def _read_path(props: Mapping[str, Any], path: str) -> Any:
    cursor: Any = props
    for step in path.split("."):
        if isinstance(cursor, Mapping) and step in cursor:
            cursor = cursor[step]
        else:
            return None
    return cursor


def _fingerprint(spec: Mapping[str, Any]) -> str:
    payload = json.dumps(
        {k: v for k, v in spec.items() if k != "fingerprint"},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]

