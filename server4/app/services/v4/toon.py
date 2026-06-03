"""
TOON — Token-Oriented Object Notation.

A compact serialization format designed for LLM communication that reduces
token consumption by 40-70% compared to JSON by eliminating:
  - Redundant quotes around keys
  - Unnecessary whitespace
  - Verbose punctuation

Format rules:
  - Keys are bare words (no quotes): name:value
  - Strings use single quotes only when they contain special chars
  - Lists use [] with | separator instead of ,
  - Nested objects use {} with ; separator
  - Null/None → ~
  - Boolean → T/F
  - Numbers are bare

Example:
  JSON:  {"headline": "AI Revolution", "bullets": ["Fast", "Smart"], "score": 9.5}
  TOON:  headline:'AI Revolution';bullets:[Fast|Smart];score:9.5

This module provides encode/decode for communication with LLMs.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


# Characters that force quoting in TOON values
_NEEDS_QUOTE = re.compile(r"[;|\[\]{}:~\n\r\t]")


def encode(obj: Any) -> str:
    """Encode a Python object to TOON format.
    
    Reduces token count by ~40-60% vs JSON for typical slide data.
    """
    if obj is None:
        return "~"
    if isinstance(obj, bool):
        return "T" if obj else "F"
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, str):
        return _encode_str(obj)
    if isinstance(obj, list):
        return _encode_list(obj)
    if isinstance(obj, dict):
        return _encode_dict(obj)
    # Fallback
    return _encode_str(str(obj))


def _encode_str(s: str) -> str:
    """Encode a string, quoting only when necessary."""
    if not s:
        return "''"
    if _NEEDS_QUOTE.search(s) or s in ("T", "F", "~"):
        # Escape single quotes within the string
        escaped = s.replace("'", "\\'")
        return f"'{escaped}'"
    # No special chars — bare string (but must not look like a number)
    try:
        float(s)
        return f"'{s}'"  # Looks numeric, quote it
    except ValueError:
        pass
    return s


def _encode_list(lst: list) -> str:
    """Encode a list with | separator."""
    if not lst:
        return "[]"
    items = [encode(item) for item in lst]
    return f"[{' | '.join(items)}]"


def _encode_dict(d: dict) -> str:
    """Encode a dict with ; separator and bare keys, wrapped in {}."""
    if not d:
        return "{}"
    pairs = []
    for k, v in d.items():
        if v is None:
            continue  # Skip null values entirely (saves tokens)
        encoded_v = encode(v)
        pairs.append(f"{k}:{encoded_v}")
    return "{" + ";".join(pairs) + "}"


def decode(toon_str: str) -> Any:
    """Decode a TOON string back to a Python object.
    
    This is a best-effort parser. For LLM responses, we also accept
    JSON as a fallback if the model doesn't produce valid TOON.
    """
    toon_str = toon_str.strip()
    
    if not toon_str:
        return None
    
    # Try JSON first as fallback (LLM might still output JSON)
    if toon_str.startswith("{") and "\"" in toon_str:
        try:
            return json.loads(toon_str)
        except json.JSONDecodeError:
            pass
    
    return _parse_value(toon_str, 0)[0]


def _parse_value(s: str, pos: int) -> tuple[Any, int]:
    """Parse a single TOON value starting at pos."""
    if pos >= len(s):
        return None, pos
    
    ch = s[pos]
    
    # Null
    if ch == "~":
        return None, pos + 1
    
    # Boolean
    if ch == "T" and (pos + 1 >= len(s) or s[pos + 1] in ";|]}\n"):
        return True, pos + 1
    if ch == "F" and (pos + 1 >= len(s) or s[pos + 1] in ";|]}\n"):
        return False, pos + 1
    
    # List
    if ch == "[":
        return _parse_list(s, pos)
    
    # Nested dict (when starting with {)
    if ch == "{":
        return _parse_nested_dict(s, pos)
    
    # Quoted string
    if ch == "'":
        return _parse_quoted(s, pos)
    
    # Bare value (string or number) — read until delimiter
    return _parse_bare(s, pos)


def _parse_quoted(s: str, pos: int) -> tuple[str, int]:
    """Parse a single-quoted string."""
    pos += 1  # skip opening quote
    result = []
    while pos < len(s):
        ch = s[pos]
        if ch == "\\" and pos + 1 < len(s) and s[pos + 1] == "'":
            result.append("'")
            pos += 2
        elif ch == "'":
            return "".join(result), pos + 1
        else:
            result.append(ch)
            pos += 1
    return "".join(result), pos


def _parse_bare(s: str, pos: int) -> tuple[Any, int]:
    """Parse a bare value (number or unquoted string)."""
    start = pos
    while pos < len(s) and s[pos] not in ";|]}\n":
        pos += 1
    raw = s[start:pos].strip()
    
    # Try number
    try:
        if "." in raw:
            return float(raw), pos
        return int(raw), pos
    except ValueError:
        return raw, pos


def _parse_list(s: str, pos: int) -> tuple[list, int]:
    """Parse a [...] list with | separator."""
    pos += 1  # skip [
    items = []
    
    # Skip whitespace
    while pos < len(s) and s[pos] in " \t":
        pos += 1
    
    if pos < len(s) and s[pos] == "]":
        return [], pos + 1
    
    while pos < len(s):
        # Skip whitespace and |
        while pos < len(s) and s[pos] in " \t":
            pos += 1
        
        if pos >= len(s) or s[pos] == "]":
            pos += 1 if pos < len(s) else 0
            break
        
        before_value = pos
        val, pos = _parse_value(s, pos)
        if pos <= before_value:
            # Malformed model output can put delimiters inside a list without
            # quoting them, e.g. [one;two]. _parse_bare then returns an empty
            # value without advancing. Always consume at least one character
            # so a bad TOON response cannot freeze the event loop.
            pos = before_value + 1
            if val in (None, ""):
                continue
        items.append(val)
        
        # Skip whitespace after value
        while pos < len(s) and s[pos] in " \t":
            pos += 1
        
        # Expect | or ]
        if pos < len(s) and s[pos] == "|":
            pos += 1
            while pos < len(s) and s[pos] in " \t":
                pos += 1
        elif pos < len(s) and s[pos] == "]":
            pos += 1
            break
        elif pos < len(s):
            # Unknown separator: consume it and continue best-effort.
            pos += 1
    
    return items, pos


def _parse_nested_dict(s: str, pos: int) -> tuple[dict, int]:
    """Parse a {...} nested dict."""
    pos += 1  # skip {
    result = {}
    
    while pos < len(s) and s[pos] != "}":
        while pos < len(s) and s[pos] in " \t\n":
            pos += 1
        if pos >= len(s) or s[pos] == "}":
            break
        
        # Read key
        key_start = pos
        while pos < len(s) and s[pos] != ":":
            pos += 1
        if pos >= len(s):
            break
        key = s[key_start:pos].strip()
        pos += 1  # skip :
        
        # Read value
        before_value = pos
        val, pos = _parse_value(s, pos)
        if pos <= before_value:
            pos = before_value + 1
        result[key] = val
        
        # Skip ; separator
        if pos < len(s) and s[pos] == ";":
            pos += 1
    
    if pos < len(s) and s[pos] == "}":
        pos += 1
    
    return result, pos


def parse_toon_response(raw: str) -> dict[str, Any]:
    """Parse an LLM response that may be TOON or JSON.

    The LLM might return either format. We try TOON parsing first,
    then fall back to JSON. This ensures backward compatibility.
    """
    raw = raw.strip()

    # If it looks like standard JSON, parse as JSON
    if raw.startswith("{") and raw.endswith("}"):
        if '"' in raw[:50]:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        # Could be TOON wrapped in {} — strip and try TOON below
        raw = raw[1:-1].strip()

    # Try TOON parsing (semicolon-separated key:value pairs)
    if ":" in raw:
        try:
            result = {}
            # Split on top-level semicolons (not inside brackets/quotes)
            pairs = _split_top_level(raw, ";")
            for pair in pairs:
                pair = pair.strip()
                if ":" not in pair:
                    continue
                colon_pos = pair.index(":")
                key = pair[:colon_pos].strip()
                val_str = pair[colon_pos + 1:].strip()
                result[key] = _parse_value(val_str, 0)[0]
            if result:
                return result
        except Exception:
            pass

    # Last resort: try JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw, "_parse_error": True}


def _split_top_level(s: str, delimiter: str) -> list[str]:
    """Split string on delimiter, respecting brackets and quotes."""
    parts = []
    current = []
    depth = 0
    in_quote = False
    
    i = 0
    while i < len(s):
        ch = s[i]
        
        if ch == "\\" and in_quote and i + 1 < len(s):
            current.append(ch)
            current.append(s[i + 1])
            i += 2
            continue
        
        if ch == "'" and not in_quote:
            in_quote = True
        elif ch == "'" and in_quote:
            in_quote = False
        elif not in_quote:
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
            elif ch == delimiter and depth == 0:
                parts.append("".join(current))
                current = []
                i += 1
                continue
        
        current.append(ch)
        i += 1
    
    if current:
        parts.append("".join(current))
    
    return parts


# ── TOON format instruction for LLM prompts ──────────────────────────

TOON_FORMAT_INSTRUCTION = """
OUTPUT FORMAT: TOON (Token-Oriented Object Notation)
Rules: bare keys, single quotes for strings with special chars, | for list items, ; between fields.
Example: headline:AI-Powered Analytics;subheadline:'Real-time insights for growth teams';bullets:[Revenue grew 3x in Q4 | 500+ enterprise customers | 99.9% uptime SLA];stat_blocks:[{value:$4.2B;label:TAM} | {value:18%;label:CAGR}];speaker_notes:'Our analytics platform...'
Null=~, True=T, False=F, skip null fields entirely.
If a value has ;|[]{}:~ chars, wrap in single quotes.
""".strip()


TOON_FORMAT_COMPACT = (
    "OUTPUT=TOON: bare keys;values;[list|items]. "
    "Ex: headline:Growth Engine;bullets:[3x revenue|500 customers];stat_blocks:[{value:$4B;label:TAM}]"
)
