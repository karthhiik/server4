"""Small-table rules for executive slides."""

from __future__ import annotations

from typing import Any


def simplify_table(table: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(table, dict):
        return table
    headers = list(table.get("headers") or [])[:4]
    rows = list(table.get("rows") or [])[:5]
    simplified_rows = []
    for row in rows:
        if isinstance(row, list):
            simplified_rows.append(row[: len(headers) or 4])
        else:
            simplified_rows.append(row)
    return {
        **table,
        "headers": headers,
        "rows": simplified_rows,
        "highlightColumn": table.get("highlightColumn", 0),
    }
