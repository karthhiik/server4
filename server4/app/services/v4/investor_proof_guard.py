"""Investor proof guard for V4 pitch decks.

This module is deterministic: it never fabricates metrics, citations, customers,
or competitors. It turns missing proof into explicit diligence structure so the
deck remains useful without pretending the founder supplied data they did not.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


_INVESTOR_TERMS = {
    "pitch", "investor", "vc", "venture", "seed", "series", "fundraising",
    "capital", "underwriter", "partnership", "proposal", "demo day",
}

_FRONTIER_TERMS = {
    "ai", "agent", "agentic", "autonomous", "machine learning", "ml", "llm",
    "quantum", "post-quantum", "cryptography", "cyber", "cybersecurity",
    "space", "satellite", "fintech", "deep tech", "deep-tech", "robotics",
    "biotech", "identity", "zero-trust", "zero trust",
}

_DOMAIN_SPECIFIC_TERMS = {
    "post-quantum",
    "post quantum",
    "lattice-based",
    "lattice based",
    "heritage data",
    "digital vault",
    "harvest now",
    "decrypt later",
    "generational handover",
    "satellite",
    "orbital",
    "space-as-a-service",
    "space as a service",
    "zero-trust",
    "zero trust",
    "decentralized identifier",
    "decentralized identifiers",
}

_OLD_SIGNALS = [
    "Founder pedigree",
    "MVP demo",
    "Pilot logos",
    "TAM slide",
    "\"We use AI\"",
]

_NEW_SIGNALS = [
    "Proprietary data",
    "Revenue momentum",
    "Production deployments",
    "Gross-margin trajectory",
    "Compounding loops",
]

_PLACEHOLDER_TOKENS = {"", "~", "tbd", "n/a", "na", "$x", "y%", "z", "coming soon"}


def is_investor_context(request_text: str, purpose: str | None = None) -> bool:
    text = f"{request_text or ''} {purpose or ''}".lower()
    return any(term in text for term in _INVESTOR_TERMS) or "pitch_deck" in text


def is_frontier_context(request_text: str) -> bool:
    text = f" {request_text or ''} ".lower()
    return any(term in text for term in _FRONTIER_TERMS)


def is_domain_specific_context(request_text: str) -> bool:
    text = f" {request_text or ''} ".lower()
    return any(term in text for term in _DOMAIN_SPECIFIC_TERMS)


def extract_topic_label(request_text: str) -> str:
    text = str(request_text or "").strip()
    match = re.search(r"presentation\s+topic\s*:\s*([^\n.]+)", text, re.IGNORECASE)
    if match:
        return _compact_label(match.group(1))
    first = re.split(r"[\n.]", text, maxsplit=1)[0]
    first = re.sub(r"^(topic|prompt|deck)\s*:\s*", "", first, flags=re.IGNORECASE)
    return _compact_label(first) or "This Company"


def _compact_label(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip(" :-")
    text = re.sub(r"^(a|an|the)\s+", "", text, flags=re.IGNORECASE)
    words = text.split()
    if len(words) > 8:
        text = " ".join(words[:8]).rstrip(" ,;:")
    return text


def _clean_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return "" if text.lower() in _PLACEHOLDER_TOKENS else text


def _dedupe(items: Iterable[str], limit: int = 4) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = _clean_text(item)
        if not clean:
            continue
        sig = re.sub(r"[^a-z0-9]+", " ", clean.lower()).strip()
        if sig in seen:
            continue
        out.append(clean)
        seen.add(sig)
        if len(out) >= limit:
            break
    return out


def _has_structured_block(slide: Any) -> bool:
    return any(
        bool(getattr(slide, field, None))
        for field in ("stat_blocks", "chart", "table", "timeline", "comparison", "diagram", "quote")
    )


def normalize_structured_blocks(slide: Any) -> None:
    """Remove placeholder/empty structured blocks before render decisions."""
    stat_blocks = []
    for block in getattr(slide, "stat_blocks", None) or []:
        if not isinstance(block, dict):
            continue
        value = _clean_text(block.get("value"))
        label = _clean_text(block.get("label"))
        if value and label:
            stat_blocks.append({"value": value[:40], "label": label[:90]})
    slide.stat_blocks = stat_blocks

    if isinstance(getattr(slide, "chart", None), dict):
        data = [
            p for p in (slide.chart.get("data") or [])
            if isinstance(p, dict) and _clean_text(p.get("label")) and p.get("value") not in (None, "")
        ]
        slide.chart = {**slide.chart, "data": data} if data else None

    if isinstance(getattr(slide, "table", None), dict):
        headers = [_clean_text(h) for h in (slide.table.get("headers") or [])]
        headers = [h for h in headers if h]
        rows = []
        for row in slide.table.get("rows") or []:
            if not isinstance(row, (list, tuple)):
                continue
            clean_row = [_clean_text(cell) for cell in row]
            if any(clean_row):
                rows.append(clean_row)
        slide.table = {**slide.table, "headers": headers, "rows": rows} if headers and rows else None

    if isinstance(getattr(slide, "timeline", None), dict):
        events = []
        for event in slide.timeline.get("events") or []:
            if not isinstance(event, dict):
                continue
            title = _clean_text(event.get("title"))
            desc = _clean_text(event.get("description"))
            date = _clean_text(event.get("date"))
            if title or desc:
                events.append({"date": date, "title": title or desc, "description": desc})
        slide.timeline = {**slide.timeline, "events": events} if len(events) >= 2 else None

    if isinstance(getattr(slide, "comparison", None), dict):
        columns = []
        for column in slide.comparison.get("columns") or []:
            if not isinstance(column, dict):
                continue
            title = _clean_text(column.get("title") or column.get("name"))
            items = _dedupe([str(i) for i in (column.get("items") or [])], limit=5)
            if title and items:
                columns.append({"title": title, "items": items, "highlight": bool(column.get("highlight"))})
        slide.comparison = {**slide.comparison, "columns": columns} if len(columns) >= 2 else None

    if isinstance(getattr(slide, "diagram", None), dict):
        nodes = []
        for node in slide.diagram.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            label = _clean_text(node.get("label") or node.get("name"))
            node_id = _clean_text(node.get("id")) or f"n{len(nodes) + 1}"
            if label:
                nodes.append({**node, "id": node_id, "label": label})
        node_ids = {node["id"] for node in nodes}
        edges = [
            edge for edge in (slide.diagram.get("edges") or [])
            if isinstance(edge, dict)
            and str(edge.get("from") or "") in node_ids
            and str(edge.get("to") or "") in node_ids
        ]
        slide.diagram = {**slide.diagram, "nodes": nodes, "edges": edges} if len(nodes) >= 2 else None

    if isinstance(getattr(slide, "quote", None), dict):
        text = _clean_text(slide.quote.get("text") or slide.quote.get("quote"))
        slide.quote = {**slide.quote, "text": text} if text else None


def _signal_shift_comparison(topic_label: str) -> dict[str, Any]:
    return {
        "features": [
            "Defensibility",
            "Momentum",
            "Deployment proof",
            "Economics",
            "Compounding loop",
        ],
        "columns": [
            {"title": "Old Signal", "items": _OLD_SIGNALS, "highlight": False},
            {"title": "What Matters Now", "items": _NEW_SIGNALS, "highlight": True},
            {
                "title": f"{topic_label} Must Prove",
                "items": [
                    "Owned data advantage",
                    "Live deployment evidence",
                    "Revenue-quality path",
                    "Repeatable learning loop",
                ],
                "highlight": False,
            },
        ]
    }


def _generic_architecture_diagram(topic_label: str, request_text: str) -> dict[str, Any]:
    key_points = _extract_key_points(request_text)
    middle = key_points[:3] or ["Domain data", "Decision engine", "Policy workflow"]
    labels = ["User input"] + middle + ["Measurable output"]
    nodes = [
        {"id": f"n{i}", "label": label[:48], "type": "default"}
        for i, label in enumerate(labels, start=1)
    ]
    edges = [
        {"from": nodes[i]["id"], "to": nodes[i + 1]["id"], "label": "flows to"}
        for i in range(len(nodes) - 1)
    ]
    return {"layout": "flow", "nodes": nodes, "edges": edges, "caption": f"{topic_label} operating model"}


def _extract_key_points(request_text: str) -> list[str]:
    match = re.search(r"key\s+points?\s*:\s*([^\n]+)", request_text or "", re.IGNORECASE)
    if match:
        raw = re.split(r",|;|\band\b", match.group(1))
        points = [_compact_label(item) for item in raw if _compact_label(item)]
        if points:
            return points

    desc_match = re.search(r"description\s*:\s*([^\n]+)", request_text or "", re.IGNORECASE)
    if not desc_match:
        return []
    description = desc_match.group(1)
    description = re.split(r"\btarget\s+audience\s*:|\bpurpose\s*:|\bslide\s+count\s*:", description, flags=re.IGNORECASE)[0]
    raw = re.split(r",|;|\band\b|\.\s+", description)
    return [_compact_label(item) for item in raw if _compact_label(item)]


def _proof_table(intent: str, topic_label: str) -> dict[str, Any]:
    intent = (intent or "").lower()
    if any(k in intent for k in ("performance", "benchmark", "latency", "scale", "scalability")):
        return {
            "headers": ["Claim", "How To Prove It", "Investor Check"],
            "rows": [
                ["Performance", "p50/p95/p99 test on target environment", "Benchmark setup and raw results"],
                ["Scalability", "Work per customer/device as load grows", "Complexity and bottleneck evidence"],
                ["Reliability", "Failure-mode and recovery test", "Production readiness review"],
            ],
        }
    if "market" in intent:
        return {
            "headers": ["Buyer Signal", "Why It Matters", "Evidence Rule"],
            "rows": [
                ["Budget owner", "Shows who can buy", "Name ICP and buying trigger"],
                ["Urgent workflow", "Shows why now", "Tie pain to operating risk"],
                ["Market number", "Supports scale", "Use sourced TAM/SAM/SOM only"],
            ],
        }
    if any(k in intent for k in ("business_model", "pricing", "financial", "revenue")):
        return {
            "headers": ["Revenue Lever", "Metric To Attach", "Why Investors Care"],
            "rows": [
                ["Value metric", "Price per seat/device/usage/domain", "Shows pricing power"],
                ["Revenue momentum", "ARR/MRR/pipeline when supplied", "Shows repeatability"],
                ["Gross margin", "COGS and model-cost trajectory", "Shows quality of revenue"],
            ],
        }
    if any(k in intent for k in ("traction", "proof", "milestone")):
        return {
            "headers": ["Proof Signal", "Acceptable Evidence", "Do Not Substitute"],
            "rows": [
                ["Production deployments", "Live users, contracts, or usage logs", "Pilot logos alone"],
                ["Proprietary data", "Data rights, volume, or feedback loop", "Generic public datasets"],
                ["Revenue momentum", "Founder-supplied revenue or pipeline", "Template growth numbers"],
            ],
        }
    if any(k in intent for k in ("ask", "funding", "capital")):
        return {
            "headers": ["Capital Use", "Milestone", "Proof Generated"],
            "rows": [
                ["Product hardening", "Production-grade reliability", "Deployment evidence"],
                ["GTM validation", "Repeatable buyer motion", "Revenue-quality signal"],
                ["Data-room proof", "Benchmarks and model economics", "Diligence readiness"],
            ],
        }
    return {
        "headers": ["Slide Claim", "Proof Needed", "Guardrail"],
        "rows": [
            [topic_label, "Evidence tied to this user's brief", "No borrowed startup metrics"],
            ["Investor readiness", "Specific operating proof", "No generic template claims"],
        ],
    }


def apply_investor_proof_guard(
    slides: list[Any],
    *,
    request_text: str,
    purpose: str | None = None,
    mode: str = "standard",
) -> None:
    if not slides:
        return

    for slide in slides:
        normalize_structured_blocks(slide)
        slide.bullets = _dedupe(getattr(slide, "bullets", []) or [], limit=4)

    if not is_investor_context(request_text, purpose):
        return

    topic_label = extract_topic_label(request_text)
    frontier = is_frontier_context(request_text)
    domain_specific = is_domain_specific_context(request_text)

    # Domain-specific decks have their own content guards upstream
    # (for example, post-quantum vaults, orbital insurance, zero-trust
    # identity). Avoid injecting generic "User input -> measurable output"
    # diagrams or AI-startup signal-shift comparisons that can overwrite
    # domain copy and make the rendered deck disagree with slide_content.
    if domain_specific:
        return

    # Add the modern investor signal-shift once per frontier/startup deck,
    # preferably to an early problem/why-now slide that lacks a richer visual.
    #
    # 2026-05-25: this branch was unconditionally stamping a hardcoded
    # "Old Signal: Founder pedigree, MVP demo, Pilot logos / What Matters
    # Now: Proprietary data, Revenue momentum, Production deployments"
    # comparison onto every frontier deck's problem slide — even when
    # the writer had produced a real comparison or substantive body
    # copy. Users reported these as the "default slides" overriding
    # their actual generated content. The fix: only stamp when the
    # target slide is genuinely empty (no comparison, no real body, no
    # substantive bullets). The signal-shift content is still useful as
    # a true fallback for empty frontier slides; it just must not
    # overwrite real writer output.
    has_signal_shift = "what matters now" in " ".join(
        str(getattr(s, "comparison", "")) for s in slides
    ).lower()
    if frontier and not has_signal_shift:
        target = None
        for s in slides:
            intent_lower = (getattr(s, "intent", "") or "").lower()
            if not any(k in intent_lower for k in ("problem", "why_now", "market", "insight")):
                continue
            if _has_structured_block(s):
                continue
            # Real content gate: skip if writer already produced substantive
            # prose or bullets. Stamping over real content is the bug.
            body_len = len(str(getattr(s, "body", "") or "").strip())
            bullets = list(getattr(s, "bullets", []) or [])
            substantive_bullets = [b for b in bullets if len(str(b).strip()) >= 12]
            if body_len >= 60 or len(substantive_bullets) >= 2:
                continue
            target = s
            break
        if target is not None:
            target.comparison = _signal_shift_comparison(topic_label)
            target.layout = "comparison"
            target.bullets = []

    for slide in slides:
        intent = (getattr(slide, "intent", "") or "").lower()
        if _has_structured_block(slide):
            continue
        # Bug B fix: do NOT stamp a hardcoded table/diagram/comparison onto
        # a slide that already has substantive prose. The user reported decks
        # where every market/traction/ask slide rendered as the same generic
        # 3x3 evidence table even though the writer had produced real bullets
        # and body copy. Forced visualizations should only fill genuinely
        # empty slides, not overwrite the writer's narrative.
        body_len = len(str(getattr(slide, "body", "") or "").strip())
        bullets = list(getattr(slide, "bullets", []) or [])
        substantive_bullets = [
            b for b in bullets if len(str(b).strip()) >= 12
        ]
        writer_has_real_prose = body_len >= 40 or len(substantive_bullets) >= 2
        if writer_has_real_prose:
            continue
        if any(k in intent for k in ("architecture", "platform", "system", "workflow", "how_it_works", "process")):
            slide.diagram = _generic_architecture_diagram(topic_label, request_text)
            slide.layout = "diagram"
            slide.bullets = []
        elif any(k in intent for k in (
            "performance", "benchmark", "latency", "scale", "scalability",
            "market", "business_model", "pricing", "financial", "revenue",
            "traction", "proof", "milestone", "ask", "funding", "capital",
        )):
            slide.table = _proof_table(intent, topic_label)
            slide.layout = "table"
            slide.bullets = []
        elif any(k in intent for k in ("competition", "moat", "differentiation")):
            slide.comparison = {
                "features": ["Positioning", "Delivery", "Data loop"],
                "columns": [
                    {"title": "Generic Alternatives", "items": ["Feature parity", "Services-heavy delivery", "Weak data loop"]},
                    {"title": "Our Proof Path", "items": ["Owned data advantage", "Deployment evidence", "Compounding operating loop"], "highlight": True},
                ]
            }
            slide.layout = "comparison"
            slide.bullets = []

        normalize_structured_blocks(slide)
