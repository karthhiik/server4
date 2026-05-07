"""
V4 DSL Validators — Normalize and bound-check the new content block types.

Adds four content blocks beyond the v10.1 DSL (stat_blocks, quote, chart):

  table       — tabular data, rendered as <table> by the frontend.
                {"caption": str?, "headers": [str], "rows": [[cell, ...], ...]}
  timeline    — sequential events, rendered as a horizontal/vertical timeline.
                {"orientation": "horizontal|vertical"?, "events": [{"date": str, "title": str, "description": str?}]}
  comparison  — 2-3 parallel columns (us/them, before/after, options).
                {"columns": [{"title": str, "items": [str], "highlight": bool?}]}
  diagram     — node-edge graph, React-Flow-compatible.
                {"layout": "flow|tree|cycle"?, "nodes": [{"id": str, "label": str, "type": str?}],
                 "edges": [{"from": str, "to": str, "label": str?}]}

These are the visual block types the writer can emit and the renderer must support.
The Visual Decider in v10.3 will decide whether each is rendered as code (HTML/React)
or as an image fallback.

All validators are defensive: they return None when input is unusable so the writer's
output never breaks downstream rendering.
"""

from __future__ import annotations

from typing import Any, Optional

# ── Bounds (kept tight to enforce density discipline) ───────────────

MAX_TABLE_COLS = 6
MAX_TABLE_ROWS = 8
MAX_CELL_LEN = 80

MAX_TIMELINE_EVENTS = 8
MAX_EVENT_TITLE_LEN = 60
MAX_EVENT_DESC_LEN = 160

MAX_COMPARE_COLS = 4
MAX_COMPARE_ITEMS = 6
MAX_COMPARE_TITLE_LEN = 40
MAX_COMPARE_ITEM_LEN = 100

MAX_DIAGRAM_NODES = 12
MAX_DIAGRAM_EDGES = 20
MAX_NODE_LABEL_LEN = 40
MAX_EDGE_LABEL_LEN = 30


def _trim(s: Any, n: int) -> str:
    return str(s if s is not None else "")[:n]


def normalize_table(data: Any) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    headers_raw = data.get("headers") or data.get("columns") or []
    rows_raw = data.get("rows") or data.get("data") or []
    if not isinstance(headers_raw, list) or not isinstance(rows_raw, list):
        return None
    headers = [_trim(h, MAX_CELL_LEN) for h in headers_raw[:MAX_TABLE_COLS] if h is not None]
    if not headers:
        return None
    rows: list[list[str]] = []
    for r in rows_raw[:MAX_TABLE_ROWS]:
        if not isinstance(r, list):
            continue
        row = [_trim(c, MAX_CELL_LEN) for c in r[: len(headers)]]
        # Right-pad short rows to header length so the renderer doesn't choke
        while len(row) < len(headers):
            row.append("")
        rows.append(row)
    if not rows:
        return None
    out: dict[str, Any] = {"headers": headers, "rows": rows}
    cap = data.get("caption")
    if isinstance(cap, str) and cap.strip():
        out["caption"] = _trim(cap, 120)
    return out


def normalize_timeline(data: Any) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    events_raw = data.get("events") or data.get("items") or []
    if not isinstance(events_raw, list):
        return None
    events: list[dict[str, str]] = []
    for ev in events_raw[:MAX_TIMELINE_EVENTS]:
        if not isinstance(ev, dict):
            continue
        title = _trim(ev.get("title") or ev.get("label") or "", MAX_EVENT_TITLE_LEN)
        date = _trim(ev.get("date") or ev.get("year") or ev.get("when") or "", 30)
        if not title and not date:
            continue
        item: dict[str, str] = {"date": date, "title": title}
        desc = ev.get("description") or ev.get("detail")
        if isinstance(desc, str) and desc.strip():
            item["description"] = _trim(desc, MAX_EVENT_DESC_LEN)
        events.append(item)
    if len(events) < 2:
        return None
    out: dict[str, Any] = {"events": events}
    orient = data.get("orientation")
    if orient in ("horizontal", "vertical"):
        out["orientation"] = orient
    return out


def normalize_comparison(data: Any) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    cols_raw = data.get("columns") or data.get("groups") or []
    if not isinstance(cols_raw, list):
        return None
    columns: list[dict[str, Any]] = []
    for col in cols_raw[:MAX_COMPARE_COLS]:
        if not isinstance(col, dict):
            continue
        title = _trim(col.get("title") or col.get("label") or "", MAX_COMPARE_TITLE_LEN)
        items_raw = col.get("items") or col.get("points") or col.get("rows") or []
        if not isinstance(items_raw, list):
            continue
        items = [_trim(it, MAX_COMPARE_ITEM_LEN) for it in items_raw[:MAX_COMPARE_ITEMS] if it]
        if not title or not items:
            continue
        c: dict[str, Any] = {"title": title, "items": items}
        if col.get("highlight") is True:
            c["highlight"] = True
        columns.append(c)
    if len(columns) < 2:
        return None
    return {"columns": columns}


def normalize_diagram(data: Any) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    nodes_raw = data.get("nodes") or []
    edges_raw = data.get("edges") or data.get("links") or []
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
        return None
    nodes: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for n in nodes_raw[:MAX_DIAGRAM_NODES]:
        if not isinstance(n, dict):
            continue
        nid = _trim(n.get("id") or n.get("name") or "", 40)
        label = _trim(n.get("label") or n.get("name") or nid, MAX_NODE_LABEL_LEN)
        if not nid or nid in seen_ids:
            continue
        seen_ids.add(nid)
        node: dict[str, str] = {"id": nid, "label": label}
        ntype = n.get("type")
        if isinstance(ntype, str) and ntype.strip():
            node["type"] = _trim(ntype, 30)
        nodes.append(node)
    if len(nodes) < 2:
        return None
    edges: list[dict[str, str]] = []
    for e in edges_raw[:MAX_DIAGRAM_EDGES]:
        if not isinstance(e, dict):
            continue
        src = _trim(e.get("from") or e.get("source") or "", 40)
        dst = _trim(e.get("to") or e.get("target") or "", 40)
        if not src or not dst or src not in seen_ids or dst not in seen_ids:
            continue
        edge: dict[str, str] = {"from": src, "to": dst}
        lbl = e.get("label")
        if isinstance(lbl, str) and lbl.strip():
            edge["label"] = _trim(lbl, MAX_EDGE_LABEL_LEN)
        edges.append(edge)
    out: dict[str, Any] = {"nodes": nodes, "edges": edges}
    layout = data.get("layout")
    if layout in ("flow", "tree", "cycle"):
        out["layout"] = layout
    return out
