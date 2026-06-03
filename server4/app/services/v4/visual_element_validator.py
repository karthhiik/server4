"""Visual Element Validator — ensures chart/table/diagram data is render-ready.

This module validates that visual elements (charts, tables, diagrams, timelines,
comparisons) have complete and correctly structured data before the slide compiler
attempts to render them. Invalid or incomplete visual elements are either fixed
or rejected to prevent broken renders.

Design principles:
  - Pure Python validation, no LLM calls
  - Total functions — never raises, returns validation result
  - Used by parallel_writer (post-write) and slide_compiler (pre-compile)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass
class VisualElementValidation:
    """Result of validating a visual element."""
    valid: bool
    element_type: str
    issues: list[str] = field(default_factory=list)
    fixed_data: Optional[dict[str, Any]] = None
    can_render: bool = True  # True if element can still render (possibly degraded)


# ── Chart Validation ───────────────────────────────────────────────────────

VALID_CHART_TYPES = {"bar", "line", "area", "pie", "radar", "scatter", "donut"}


def validate_chart(chart: Optional[Mapping[str, Any]]) -> VisualElementValidation:
    """Validate a chart block has minimum required data.
    
    Requirements:
      - type: must be a valid chart type (bar, line, pie, etc.)
      - data: must be a non-empty list
      - data items: must have at least one numeric value
      - xKey/x_key or nameKey: must exist for labeling
    """
    issues: list[str] = []
    fixed_data: Optional[dict[str, Any]] = None
    
    if not chart:
        return VisualElementValidation(
            valid=False,
            element_type="chart",
            issues=["chart is None or empty"],
            can_render=False,
        )
    
    chart_dict = dict(chart) if isinstance(chart, Mapping) else {}
    
    # Validate type
    chart_type = str(chart_dict.get("type") or "bar").lower()
    if chart_type not in VALID_CHART_TYPES:
        issues.append(f"invalid chart type '{chart_type}', defaulting to 'bar'")
        chart_type = "bar"
    
    # Validate data
    data = chart_dict.get("data") or []
    if not isinstance(data, list):
        issues.append("chart data is not a list")
        data = []
    elif len(data) == 0:
        issues.append("chart data is empty")
        return VisualElementValidation(
            valid=False,
            element_type="chart",
            issues=issues,
            can_render=False,
        )
    
    # Validate data items have required structure
    valid_items = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            issues.append(f"data[{i}] is not a dict, skipping")
            continue
        
        # Check for at least one numeric value
        has_numeric = any(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in item.values()
        )
        if not has_numeric:
            issues.append(f"data[{i}] has no numeric values, skipping")
            continue
        
        valid_items.append(item)
    
    if not valid_items:
        issues.append("no valid data items after filtering")
        return VisualElementValidation(
            valid=False,
            element_type="chart",
            issues=issues,
            can_render=False,
        )
    
    # Validate keys
    x_key = chart_dict.get("xKey") or chart_dict.get("x_key") or "name"
    y_keys = chart_dict.get("yKeys") or chart_dict.get("y_keys") or []
    
    # Auto-detect keys from first valid item if not specified
    if not y_keys and valid_items:
        first_item = valid_items[0]
        y_keys = [
            k for k, v in first_item.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        ][:2]  # Take up to 2 numeric columns
    
    # Determine if pie/radar need valueKey
    value_key = chart_dict.get("valueKey") or chart_dict.get("value_key")
    if chart_type in {"pie", "radar", "donut"} and not value_key:
        if valid_items and y_keys:
            value_key = y_keys[0]
    
    # Build fixed data if there were issues
    if issues:
        fixed_data = {
            "type": chart_type,
            "data": valid_items,
            "xKey": x_key,
        }
        if y_keys:
            fixed_data["yKeys"] = y_keys
        if value_key:
            fixed_data["valueKey"] = value_key
        if chart_dict.get("source"):
            fixed_data["source"] = str(chart_dict["source"])
    
    return VisualElementValidation(
        valid=len(issues) == 0,
        element_type="chart",
        issues=issues,
        fixed_data=fixed_data,
        can_render=True,
    )


# ── Table Validation ────────────────────────────────────────────────────────

MAX_TABLE_COLS = 8
MAX_TABLE_ROWS = 12


def validate_table(table: Optional[Mapping[str, Any]]) -> VisualElementValidation:
    """Validate a table block has required structure.
    
    Requirements:
      - headers: list of strings (max 8)
      - rows: list of lists (max 12 rows)
      - each row length matches headers length
    """
    issues: list[str] = []
    fixed_data: Optional[dict[str, Any]] = None
    
    if not table:
        return VisualElementValidation(
            valid=False,
            element_type="table",
            issues=["table is None or empty"],
            can_render=False,
        )
    
    table_dict = dict(table) if isinstance(table, Mapping) else {}
    
    # Validate headers
    headers = table_dict.get("headers") or []
    if not isinstance(headers, list):
        issues.append("table headers is not a list")
        headers = []
    elif not headers:
        issues.append("table headers is empty")
        return VisualElementValidation(
            valid=False,
            element_type="table",
            issues=issues,
            can_render=False,
        )
    
    # Convert headers to strings
    headers = [str(h) for h in headers[:MAX_TABLE_COLS]]
    if len(headers) > MAX_TABLE_COLS:
        issues.append(f"truncated headers from {len(headers)} to {MAX_TABLE_COLS}")
    
    # Validate rows
    rows = table_dict.get("rows") or []
    if not isinstance(rows, list):
        issues.append("table rows is not a list")
        rows = []
    
    if not rows:
        issues.append("table rows is empty")
        return VisualElementValidation(
            valid=False,
            element_type="table",
            issues=issues,
            can_render=False,
        )
    
    # Validate and fix row lengths
    valid_rows = []
    for i, row in enumerate(rows[:MAX_TABLE_ROWS]):
        if not isinstance(row, list):
            issues.append(f"row[{i}] is not a list, converting")
            row = [row] if row else [""] * len(headers)
        
        # Pad or truncate row to match headers
        row_list = [str(cell) if cell is not None else "" for cell in row]
        if len(row_list) < len(headers):
            row_list.extend([""] * (len(headers) - len(row_list)))
            issues.append(f"row[{i}] padded to match headers")
        elif len(row_list) > len(headers):
            row_list = row_list[:len(headers)]
            issues.append(f"row[{i}] truncated to match headers")
        
        valid_rows.append(row_list)
    
    if len(rows) > MAX_TABLE_ROWS:
        issues.append(f"truncated rows from {len(rows)} to {MAX_TABLE_ROWS}")
    
    if not valid_rows:
        issues.append("no valid rows after filtering")
        return VisualElementValidation(
            valid=False,
            element_type="table",
            issues=issues,
            can_render=False,
        )
    
    # Build fixed data if there were issues
    if issues:
        fixed_data = {
            "headers": headers,
            "rows": valid_rows,
        }
        if table_dict.get("caption"):
            fixed_data["caption"] = str(table_dict["caption"])
    
    return VisualElementValidation(
        valid=len(issues) == 0,
        element_type="table",
        issues=issues,
        fixed_data=fixed_data,
        can_render=True,
    )


# ── Diagram Validation ──────────────────────────────────────────────────────

MAX_DIAGRAM_NODES = 15
MAX_DIAGRAM_EDGES = 25


def validate_diagram(diagram: Optional[Mapping[str, Any]]) -> VisualElementValidation:
    """Validate a diagram block has required structure.
    
    Requirements:
      - nodes: list with id and label (max 15)
      - edges: list with from and to (max 25)
      - all edge references must point to valid node IDs
    """
    issues: list[str] = []
    fixed_data: Optional[dict[str, Any]] = None
    
    if not diagram:
        return VisualElementValidation(
            valid=False,
            element_type="diagram",
            issues=["diagram is None or empty"],
            can_render=False,
        )
    
    diagram_dict = dict(diagram) if isinstance(diagram, Mapping) else {}
    
    # Validate nodes
    raw_nodes = diagram_dict.get("nodes") or []
    if not isinstance(raw_nodes, list):
        issues.append("diagram nodes is not a list")
        raw_nodes = []
    
    if not raw_nodes:
        issues.append("diagram has no nodes")
        return VisualElementValidation(
            valid=False,
            element_type="diagram",
            issues=issues,
            can_render=False,
        )
    
    # Validate and fix nodes
    valid_nodes = []
    node_ids = set()
    for i, node in enumerate(raw_nodes[:MAX_DIAGRAM_NODES]):
        if not isinstance(node, dict):
            issues.append(f"node[{i}] is not a dict, skipping")
            continue
        
        node_id = str(node.get("id") or f"n{i}")
        label = str(node.get("label") or node.get("name") or node_id)
        
        # Validate coordinates (0-1 range)
        x = node.get("x")
        y = node.get("y")
        if not isinstance(x, (int, float)):
            x = (i + 1) / (len(raw_nodes) + 1)  # Auto-layout horizontal
        if not isinstance(y, (int, float)):
            y = 0.5
        
        valid_nodes.append({
            "id": node_id,
            "label": label,
            "x": float(x),
            "y": float(y),
        })
        node_ids.add(node_id)
    
    if len(raw_nodes) > MAX_DIAGRAM_NODES:
        issues.append(f"truncated nodes from {len(raw_nodes)} to {MAX_DIAGRAM_NODES}")
    
    if not valid_nodes:
        issues.append("no valid nodes after filtering")
        return VisualElementValidation(
            valid=False,
            element_type="diagram",
            issues=issues,
            can_render=False,
        )
    
    # Validate edges
    raw_edges = diagram_dict.get("edges") or []
    if not isinstance(raw_edges, list):
        issues.append("diagram edges is not a list")
        raw_edges = []
    
    valid_edges = []
    for i, edge in enumerate(raw_edges[:MAX_DIAGRAM_EDGES]):
        if not isinstance(edge, dict):
            continue
        
        from_id = str(edge.get("from") or edge.get("source") or "")
        to_id = str(edge.get("to") or edge.get("target") or "")
        
        # Skip edges with invalid references
        if from_id not in node_ids:
            issues.append(f"edge[{i}] has invalid 'from' node: {from_id}")
            continue
        if to_id not in node_ids:
            issues.append(f"edge[{i}] has invalid 'to' node: {to_id}")
            continue
        
        edge_data = {"from": from_id, "to": to_id}
        if edge.get("label"):
            edge_data["label"] = str(edge["label"])
        if edge.get("style") in {"solid", "dashed"}:
            edge_data["style"] = edge["style"]
        
        valid_edges.append(edge_data)
    
    if len(raw_edges) > MAX_DIAGRAM_EDGES:
        issues.append(f"truncated edges from {len(raw_edges)} to {MAX_DIAGRAM_EDGES}")
    
    # Build fixed data if there were issues
    if issues:
        fixed_data = {
            "nodes": valid_nodes,
            "edges": valid_edges,
        }
        if diagram_dict.get("layout"):
            fixed_data["layout"] = str(diagram_dict["layout"])
    
    return VisualElementValidation(
        valid=len(issues) == 0,
        element_type="diagram",
        issues=issues,
        fixed_data=fixed_data,
        can_render=True,
    )


# ── Timeline Validation ──────────────────────────────────────────────────────

MAX_TIMELINE_EVENTS = 10


def validate_timeline(timeline: Optional[Mapping[str, Any]]) -> VisualElementValidation:
    """Validate a timeline block has required structure.
    
    Requirements:
      - events: list with date and title (max 10)
    """
    issues: list[str] = []
    fixed_data: Optional[dict[str, Any]] = None
    
    if not timeline:
        return VisualElementValidation(
            valid=False,
            element_type="timeline",
            issues=["timeline is None or empty"],
            can_render=False,
        )
    
    timeline_dict = dict(timeline) if isinstance(timeline, Mapping) else {}
    
    # Validate events
    events = timeline_dict.get("events") or []
    if not isinstance(events, list):
        issues.append("timeline events is not a list")
        events = []
    
    if not events:
        issues.append("timeline has no events")
        return VisualElementValidation(
            valid=False,
            element_type="timeline",
            issues=issues,
            can_render=False,
        )
    
    valid_events = []
    for i, event in enumerate(events[:MAX_TIMELINE_EVENTS]):
        if not isinstance(event, dict):
            issues.append(f"event[{i}] is not a dict, skipping")
            continue
        
        date = str(event.get("date") or event.get("when") or "")
        title = str(event.get("title") or event.get("name") or "")
        
        if not title:
            issues.append(f"event[{i}] has no title, skipping")
            continue
        
        valid_event = {"date": date, "title": title}
        if event.get("description"):
            valid_event["description"] = str(event["description"])
        if event.get("done") is True:
            valid_event["done"] = True
        
        valid_events.append(valid_event)
    
    if len(events) > MAX_TIMELINE_EVENTS:
        issues.append(f"truncated events from {len(events)} to {MAX_TIMELINE_EVENTS}")
    
    if not valid_events:
        issues.append("no valid events after filtering")
        return VisualElementValidation(
            valid=False,
            element_type="timeline",
            issues=issues,
            can_render=False,
        )
    
    # Build fixed data if there were issues
    if issues:
        orientation = str(timeline_dict.get("orientation") or "horizontal").lower()
        if orientation not in {"horizontal", "vertical"}:
            orientation = "horizontal"
        
        fixed_data = {
            "orientation": orientation,
            "events": valid_events,
        }
    
    return VisualElementValidation(
        valid=len(issues) == 0,
        element_type="timeline",
        issues=issues,
        fixed_data=fixed_data,
        can_render=True,
    )


# ── Comparison Validation ────────────────────────────────────────────────────

MIN_COMPARISON_COLS = 2
MAX_COMPARISON_COLS = 4
MIN_COMPARISON_ROWS = 2


def validate_comparison(comparison: Optional[Mapping[str, Any]]) -> VisualElementValidation:
    """Validate a comparison block has required structure.
    
    Requirements:
      - columns: list with title and items (2-4 columns)
      - at least 2 rows across columns
    """
    issues: list[str] = []
    fixed_data: Optional[dict[str, Any]] = None
    
    if not comparison:
        return VisualElementValidation(
            valid=False,
            element_type="comparison",
            issues=["comparison is None or empty"],
            can_render=False,
        )
    
    comp_dict = dict(comparison) if isinstance(comparison, Mapping) else {}
    
    # Validate columns
    columns = comp_dict.get("columns") or []
    if not isinstance(columns, list):
        issues.append("comparison columns is not a list")
        columns = []
    top_level_rows = comp_dict.get("rows") or []
    if not isinstance(top_level_rows, list):
        issues.append("comparison rows is not a list")
        top_level_rows = []
    
    if len(columns) < MIN_COMPARISON_COLS:
        issues.append(f"comparison has {len(columns)} columns, needs at least {MIN_COMPARISON_COLS}")
        return VisualElementValidation(
            valid=False,
            element_type="comparison",
            issues=issues,
            can_render=False,
        )
    
    valid_columns = []
    max_rows = 0
    
    for i, col in enumerate(columns[:MAX_COMPARISON_COLS]):
        if not isinstance(col, dict):
            issues.append(f"column[{i}] is not a dict, skipping")
            continue
        
        title = str(col.get("title") or col.get("name") or f"Column {i+1}")
        items = col.get("items") or []
        inline_rows = col.get("rows") or []
        inline_features = col.get("features") or []
        if not items and isinstance(top_level_rows, list):
            row_items = []
            for row in top_level_rows:
                if not isinstance(row, dict) or not (row.get("feature") or row.get("name")):
                    continue
                values = row.get("values")
                value = None
                if isinstance(values, list) and i < len(values):
                    value = values[i]
                elif isinstance(values, dict):
                    value = values.get(title) or values.get(col.get("name")) or values.get(col.get("title"))
                if value:
                    row_items.append(value)
            if row_items:
                items = row_items
        if not items and isinstance(inline_rows, list):
            items = [
                row.get("value")
                for row in inline_rows
                if isinstance(row, dict) and (row.get("feature") or row.get("name"))
            ]
        if not items and isinstance(inline_features, list):
            items = [
                row.get("value")
                for row in inline_features
                if isinstance(row, dict) and (row.get("label") or row.get("feature") or row.get("name"))
            ]
        
        if not isinstance(items, list):
            items = []
        
        # Convert items to strings
        items = [str(item) if item else "" for item in items]
        
        fixed_col = {
            "title": title,
            "items": items,
        }
        if col.get("highlight"):
            fixed_col["highlight"] = True
        if isinstance(inline_rows, list) and inline_rows:
            fixed_col["rows"] = inline_rows
        if isinstance(inline_features, list) and inline_features:
            fixed_col["features"] = inline_features
        valid_columns.append(fixed_col)
        max_rows = max(max_rows, len(items))
    
    if len(columns) > MAX_COMPARISON_COLS:
        issues.append(f"truncated columns from {len(columns)} to {MAX_COMPARISON_COLS}")
    
    if len(valid_columns) < MIN_COMPARISON_COLS:
        issues.append(f"only {len(valid_columns)} valid columns, needs {MIN_COMPARISON_COLS}")
        return VisualElementValidation(
            valid=False,
            element_type="comparison",
            issues=issues,
            can_render=False,
        )
    
    if max_rows < MIN_COMPARISON_ROWS:
        issues.append(f"comparison has {max_rows} rows, needs at least {MIN_COMPARISON_ROWS}")
        return VisualElementValidation(
            valid=False,
            element_type="comparison",
            issues=issues,
            can_render=False,
        )
    
    # Build fixed data if there were issues
    if issues:
        fixed_data = {"columns": valid_columns}
        if top_level_rows:
            fixed_data["rows"] = top_level_rows
    
    return VisualElementValidation(
        valid=len(issues) == 0,
        element_type="comparison",
        issues=issues,
        fixed_data=fixed_data,
        can_render=True,
    )


# ── Unified Validation Entry Point ──────────────────────────────────────────

def validate_visual_element(
    element_type: str,
    data: Optional[Mapping[str, Any]],
) -> VisualElementValidation:
    """Validate any visual element by type.
    
    Args:
        element_type: One of 'chart', 'table', 'diagram', 'timeline', 'comparison'
        data: The element data dict
    
    Returns:
        VisualElementValidation with valid flag, issues, and fixed_data
    """
    validators = {
        "chart": validate_chart,
        "table": validate_table,
        "diagram": validate_diagram,
        "timeline": validate_timeline,
        "comparison": validate_comparison,
    }
    
    validator = validators.get(element_type.lower())
    if not validator:
        return VisualElementValidation(
            valid=False,
            element_type=element_type,
            issues=[f"unknown element type: {element_type}"],
            can_render=False,
        )
    
    return validator(data)


def ensure_valid_visual_element(
    element_type: str,
    data: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    """Validate and return fixed data, or None if unfixable.
    
    This is a convenience function for use in the compiler:
      - If valid: returns original data
      - If fixable: returns fixed_data
      - If unfixable: returns None (caller should skip this element)
    """
    result = validate_visual_element(element_type, data)
    
    if result.valid:
        return dict(data) if data else None
    
    if result.can_render and result.fixed_data:
        return result.fixed_data
    
    return None
