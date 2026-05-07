"""
deck_viewer.py — Generates a deck against the running server4 (port 8003),
then serves an inspectable HTML page showing every field the pipeline produced.

Usage:
    python tools/deck_viewer.py --mode standard --port 5017
    python tools/deck_viewer.py --mode premium  --port 5018

The two modes ship with real, rich sample inputs — structured premium input
uses full company/team/financials/market/fundraising data so the team-fetching,
logo-fetching, chart and table paths all exercise.

This is a test harness — it calls the real backend, no mocks, no dummy data.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

try:
    import httpx
except ImportError:
    print("Missing httpx. Install with: pip install httpx", file=sys.stderr)
    sys.exit(1)


SERVER = "http://127.0.0.1:8003"

# ── Rich real inputs ────────────────────────────────────────────────

STANDARD_INPUT = {
    "mode": "standard",
    "input_method": "prompt",
    "standard_input": {
        "prompt": (
            "Create a 10-slide Series A pitch deck for Northwind AI — a B2B SaaS "
            "platform that uses agentic LLM workflows to automate enterprise "
            "procurement. Founded 2023 in San Francisco, team of 18. Current "
            "traction: $2.4M ARR growing 28% MoM, 47 enterprise customers "
            "including 4 Fortune 500 (Walmart, Pfizer, Chevron, HP). CAC is "
            "$8.2K, LTV $340K, gross margin 82%. Competitors are Coupa, Ivalua, "
            "and SAP Ariba but none have agentic AI. We're raising $15M Series A "
            "to expand into EU (France, Germany, UK) and grow GTM team from 6 "
            "to 24. Lead by Sequoia, participation from existing investors "
            "Accel and General Catalyst. Audience: institutional VCs."
        ),
        "purpose": "pitch_deck",
        "audience": "Series A institutional VCs",
        "slide_count": 10,
        "language": "English",
        "writing_style": "yc_crisp",
        "generate_images": True,
        "generate_notes": True,
    },
}

PREMIUM_INPUT = {
    "mode": "premium",
    "input_method": "structured",
    "premium_structured_input": {
        "topic": "Series A fundraise for Northwind AI — Agentic procurement platform",
        "description": (
            "Northwind AI turns every enterprise procurement decision into an "
            "agentic LLM workflow. We analyze RFPs, negotiate with suppliers, "
            "surface risk flags, and auto-generate purchase orders. Built for "
            "Fortune 500 procurement teams drowning in supplier emails, PDF RFPs, "
            "and compliance overhead. We're $2.4M ARR at 28% MoM growth."
        ),
        "purpose": "pitch_deck",
        "audience": "Series A VCs (Sequoia, a16z, Founders Fund)",
        "audience_sophistication": "investor",
        "company": {
            "name": "Northwind AI",
            "tagline": "Agentic procurement for the Fortune 500",
            "industry": "Enterprise SaaS / Procurement automation",
            "founded_year": 2023,
            "location": "San Francisco, CA",
            "website_url": "https://northwind.ai",
            "stage": "series_a",
            "team_size": 18,
        },
        "financials": {
            "arr": 2_400_000,
            "mrr": 210_000,
            "revenue_growth_pct": 28.0,
            "burn_rate": 420_000,
            "runway_months": 14,
            "gross_margin_pct": 82.0,
            "cac": 8_200,
            "ltv": 340_000,
            "total_funding_raised": 5_800_000,
            "customers_count": 47,
            "users_count": 1_240,
        },
        "competitors": [
            {
                "name": "Coupa",
                "description": "Legacy procurement suite, public company.",
                "strengths": ["Enterprise trust", "Integrations", "Market share"],
                "weaknesses": ["No agentic AI", "Slow product velocity", "Clunky UX"],
                "differentiator": "We replace humans in the loop; Coupa augments them.",
            },
            {
                "name": "Ivalua",
                "description": "European procurement platform, configurable.",
                "strengths": ["Configurable workflows", "Strong EU presence"],
                "weaknesses": ["Heavy implementation", "No LLM-native features"],
                "differentiator": "5-day implementation vs 6-month average.",
            },
            {
                "name": "SAP Ariba",
                "description": "Dominant incumbent bundled with SAP ERP.",
                "strengths": ["SAP lock-in", "Supplier network scale"],
                "weaknesses": ["Poor user experience", "Innovation stalled"],
                "differentiator": "Agentic negotiation actually closes deals.",
            },
        ],
        "traction": {
            "key_milestones": [
                "Q1 2024: Launched closed beta with 5 pilot customers",
                "Q3 2024: $1M ARR milestone crossed",
                "Q1 2025: First Fortune 500 (Walmart) signed",
                "Q3 2025: $2M ARR, 40+ enterprise customers",
                "Q4 2025: 4 Fortune 500 logos (Walmart, Pfizer, Chevron, HP)",
            ],
            "notable_customers": ["Walmart", "Pfizer", "Chevron", "HP", "Stripe", "Figma", "Notion"],
            "partnerships": ["AWS Select Partner", "SAP PartnerEdge"],
            "press_mentions": ["TechCrunch", "Bloomberg", "The Information"],
            "awards": ["Gartner Cool Vendor 2025"],
            "growth_metrics": {"mom_growth_pct": 28, "net_revenue_retention_pct": 142, "logo_retention_pct": 97},
        },
        "team": [
            {
                "name": "Maya Chen",
                "role": "Co-founder & CEO",
                "bio": "Former VP Product at Coupa (scaled from $100M to $800M ARR). Stanford MBA, ex-McKinsey.",
                "notable_credentials": ["Ex-Coupa VP Product", "Stanford MBA", "YC W21"],
            },
            {
                "name": "Rahul Mehta",
                "role": "Co-founder & CTO",
                "bio": "Former tech lead on Google DeepMind's agentic systems team. PhD CS Stanford.",
                "notable_credentials": ["Ex-DeepMind", "PhD Stanford", "3x NeurIPS papers"],
            },
            {
                "name": "Sarah Okonkwo",
                "role": "VP Engineering",
                "bio": "Scaled engineering at Ramp from 20 to 200 engineers. Principal Engineer at Stripe prior.",
                "notable_credentials": ["Ex-Ramp", "Ex-Stripe", "MIT CS"],
            },
            {
                "name": "David Park",
                "role": "Head of Sales",
                "bio": "Built enterprise GTM at Airtable — grew from $10M to $100M ARR in 24 months.",
                "notable_credentials": ["Ex-Airtable", "Ex-Salesforce", "$100M ARR scaled"],
            },
        ],
        "fundraising": {
            "amount": 15_000_000,
            "round_type": "Series A",
            "use_of_funds": [
                "Expand GTM team from 6 to 24 (40% of capital)",
                "Open EU HQ in London (20% of capital)",
                "Scale ML infrastructure for agentic workflows (25% of capital)",
                "Compliance certifications: SOC 2 Type II, ISO 27001, FedRAMP (10%)",
                "Strategic partnerships and BD (5%)",
            ],
            "timeline": "Targeting close in Q2 2026, term sheet signed Q1",
            "previous_investors": ["Accel", "General Catalyst", "YC", "South Park Commons"],
            "valuation_cap": 120_000_000,
        },
        "market": {
            "tam": "$120B (global enterprise procurement software)",
            "sam": "$18B (North America + EU F500 procurement)",
            "som": "$340M (F500 procurement-transformation spend 2026)",
            "market_growth_rate": "14% CAGR through 2030",
            "target_segment": "Fortune 500 CPOs with $500M+ annual supplier spend",
            "sources": ["Gartner Magic Quadrant 2025", "IDC Procurement Market 2025", "Deloitte CPO Survey 2025"],
        },
        "slide_count": 12,
        "language": "English",
        "writing_style": "yc_crisp",
        "content_directives": {
            "include_slides": ["title", "problem", "solution", "product", "market", "traction", "business_model", "competition", "team", "financials", "ask", "vision"],
            "emphasis": ["traction", "team credentials", "unit economics"],
            "tone_keywords": ["confident", "data-backed", "visionary"],
            "key_messages": [
                "Agentic AI is the only way procurement can keep up with supplier complexity",
                "We have real enterprise traction, not just pilots",
                "Team has done this playbook before at Coupa/Airtable",
            ],
        },
        "generate_images": True,
        "generate_notes": True,
    },
}


# ── Pipeline orchestration ──────────────────────────────────────────


def fire_generation(payload: dict[str, Any]) -> str:
    """POST /api/v4/generate. Returns project_id."""
    r = httpx.post(f"{SERVER}/api/v4/generate", json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    pid = data["project_id"]
    print(f"[fire] project_id={pid} ws={data.get('ws_url')}", flush=True)
    return pid


def poll_until_done(project_id: str, max_seconds: int = 2400) -> dict[str, Any]:
    """Poll /api/v4/generation/{id} until terminal state or timeout."""
    start = time.time()
    last_stage = None
    while True:
        elapsed = time.time() - start
        if elapsed > max_seconds:
            raise TimeoutError(f"Generation did not complete in {max_seconds}s")
        try:
            r = httpx.get(f"{SERVER}/api/v4/generation/{project_id}", timeout=30)
            r.raise_for_status()
            status_doc = r.json()
        except Exception as e:
            print(f"[poll] error: {e}", flush=True)
            time.sleep(3)
            continue

        status = status_doc.get("status", "?")
        progress = status_doc.get("progress", 0)
        msg = status_doc.get("message", "")
        recent = status_doc.get("progress_log", [])
        stage = recent[-1].get("stage", "?") if recent else "—"
        if stage != last_stage:
            print(f"[{elapsed:5.1f}s] status={status} progress={progress}% stage={stage} msg={msg}", flush=True)
            last_stage = stage

        if status in {"completed", "ready", "ready_for_editing"}:
            return status_doc
        if status in {"failed"}:
            raise RuntimeError(f"Generation failed: {status_doc.get('error')}")
        time.sleep(3)


def fetch_slides(project_id: str) -> dict[str, Any]:
    r = httpx.get(f"{SERVER}/api/v4/projects/{project_id}/slides", timeout=30)
    r.raise_for_status()
    return r.json()


# ── HTML rendering ──────────────────────────────────────────────────


def _fmt_json(obj: Any) -> str:
    return html.escape(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _extract_theme(status_doc: dict[str, Any]) -> dict[str, Any]:
    """Pull the resolved design_tokens out of the progress_log.

    The `design_resolver` stage emits a payload containing `design_tokens`
    (palette, fonts, spacing, type_scale). We scan for it and fall back to
    sane neutrals if absent.
    """
    tokens: dict[str, Any] = {}
    for entry in status_doc.get("progress_log", []) or []:
        payload = entry.get("payload") or {}
        dt = payload.get("design_tokens")
        if isinstance(dt, dict) and dt:
            tokens = dt
            break
    palette = tokens.get("palette") or {}
    fonts = tokens.get("fonts") or {}
    type_scale = tokens.get("type_scale") or {}
    return {
        "primary": palette.get("primary") or "#2563eb",
        "accent": palette.get("accent") or "#7c3aed",
        "bg": palette.get("background") or "#0b1020",
        "surface": palette.get("surface") or "#141a2e",
        "text": palette.get("text") or "#e8ecf1",
        "muted": palette.get("muted") or "#94a3b8",
        "chart": palette.get("chart") or [palette.get("primary") or "#2563eb",
                                          palette.get("accent") or "#7c3aed",
                                          "#10b981", "#f59e0b", "#ef4444"],
        "heading_font": fonts.get("heading") or "Inter, ui-sans-serif, system-ui",
        "body_font": fonts.get("body") or "Inter, ui-sans-serif, system-ui",
        "h1_pt": type_scale.get("h1") or 44,
        "h2_pt": type_scale.get("h2") or 30,
        "body_pt": type_scale.get("body") or 16,
    }


def _render_stat_blocks(stats: list[dict], theme: dict) -> str:
    if not stats:
        return ""
    cells = "".join(
        f'''<div class="stat">
             <div class="stat-value" style="color:{theme['primary']}">{html.escape(str(s.get('value','')))}</div>
             <div class="stat-label">{html.escape(str(s.get('label','')))}</div>
           </div>'''
        for s in stats
    )
    return f'<div class="stats-row">{cells}</div>'


def _render_bullets(bullets: list, theme: dict) -> str:
    if not bullets:
        return ""
    items = "".join(f'<li>{html.escape(str(b))}</li>' for b in bullets)
    return f'<ul class="bullets" style="color:{theme["text"]}">{items}</ul>'


def _render_table(tbl: dict, theme: dict) -> str:
    if not tbl:
        return ""
    headers = tbl.get("headers") or []
    rows = tbl.get("rows") or []
    caption = tbl.get("caption") or ""
    thead = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>"
        for r in rows
    )
    cap = f'<caption>{html.escape(caption)}</caption>' if caption else ""
    return f'<table class="preview-table" style="border-color:{theme["primary"]}33">{cap}<thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>'


def _render_chart(chart: dict, theme: dict) -> str:
    if not chart:
        return ""
    data = chart.get("data") or []
    ctype = (chart.get("type") or "bar").lower()
    if not data:
        return ""
    labels = [str(d.get("label", "")) for d in data]
    values = [float(d.get("value", 0) or 0) for d in data]
    if not values:
        return ""
    maxv = max(values) or 1.0
    w, h = 560, 220
    pad = 40
    bw = (w - pad * 2) / max(len(values), 1)
    colors = theme["chart"]
    if ctype == "line":
        pts = " ".join(
            f"{pad + i * bw + bw / 2},{h - pad - (v / maxv) * (h - pad * 2)}"
            for i, v in enumerate(values)
        )
        circles = "".join(
            f'<circle cx="{pad + i * bw + bw / 2}" cy="{h - pad - (v / maxv) * (h - pad * 2)}" r="4" fill="{colors[0]}"/>'
            for i, v in enumerate(values)
        )
        labels_svg = "".join(
            f'<text x="{pad + i * bw + bw / 2}" y="{h - pad + 16}" fill="{theme["muted"]}" font-size="11" text-anchor="middle">{html.escape(lbl)}</text>'
            for i, lbl in enumerate(labels)
        )
        body = f'<polyline fill="none" stroke="{colors[0]}" stroke-width="2.5" points="{pts}"/>{circles}{labels_svg}'
    else:  # bar
        bars = ""
        for i, v in enumerate(values):
            bh = (v / maxv) * (h - pad * 2)
            x = pad + i * bw + bw * 0.15
            y = h - pad - bh
            bars += (
                f'<rect x="{x}" y="{y}" width="{bw * 0.7}" height="{bh}" fill="{colors[i % len(colors)]}" rx="3"/>'
                f'<text x="{x + bw * 0.35}" y="{h - pad + 16}" fill="{theme["muted"]}" font-size="11" text-anchor="middle">{html.escape(labels[i])}</text>'
                f'<text x="{x + bw * 0.35}" y="{y - 6}" fill="{theme["text"]}" font-size="11" text-anchor="middle">{html.escape(str(values[i]))}</text>'
            )
        body = bars
    axis = f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" stroke="{theme["muted"]}" stroke-width="1"/>'
    return f'<svg class="preview-chart" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{axis}{body}</svg>'


def _render_diagram(diagram: dict, theme: dict) -> str:
    if not diagram:
        return ""
    nodes = diagram.get("nodes") or []
    edges = diagram.get("edges") or []
    if not nodes:
        return ""
    # lay out horizontally
    w, h = 720, 200
    nx = len(nodes)
    box_w, box_h = 150, 60
    gap = (w - box_w * nx) / max(nx + 1, 1)
    positions = {}
    boxes = ""
    for i, n in enumerate(nodes):
        x = gap + i * (box_w + gap)
        y = (h - box_h) / 2
        positions[n.get("id") or str(i)] = (x + box_w / 2, y + box_h / 2, x, y)
        label = html.escape(str(n.get("label", "")))
        boxes += (
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="8" '
            f'fill="{theme["surface"]}" stroke="{theme["primary"]}" stroke-width="1.5"/>'
            f'<text x="{x + box_w / 2}" y="{y + box_h / 2 + 4}" fill="{theme["text"]}" '
            f'font-size="12" font-weight="600" text-anchor="middle">{label[:22]}</text>'
        )
    arrows = ""
    for e in edges:
        src = positions.get(e.get("from"))
        dst = positions.get(e.get("to"))
        if not src or not dst:
            continue
        x1 = src[2] + box_w
        y1 = src[1]
        x2 = dst[2]
        y2 = dst[1]
        elabel = html.escape(str(e.get("label", "")))
        midx = (x1 + x2) / 2
        arrows += (
            f'<line x1="{x1}" y1="{y1}" x2="{x2 - 6}" y2="{y2}" stroke="{theme["accent"]}" stroke-width="2" marker-end="url(#arr)"/>'
            f'<text x="{midx}" y="{y1 - 8}" fill="{theme["muted"]}" font-size="10" text-anchor="middle">{elabel}</text>'
        )
    defs = (
        f'<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{theme["accent"]}"/></marker></defs>'
    )
    return f'<svg class="preview-diagram" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{defs}{arrows}{boxes}</svg>'


def _render_team(members: list[dict], theme: dict) -> str:
    if not members:
        return ""
    cards = ""
    for m in members:
        photo = m.get("photo_url") or ""
        name = html.escape(str(m.get("name", "")))
        role = html.escape(str(m.get("role", "")))
        bio = html.escape(str(m.get("bio") or ""))[:140]
        img = f'<img src="{html.escape(photo)}" alt="{name}"/>' if photo else '<div class="avatar-fallback"></div>'
        cards += f'''<div class="team-card" style="border-color:{theme['primary']}33">
          {img}
          <div class="team-name">{name}</div>
          <div class="team-role" style="color:{theme['muted']}">{role}</div>
          {f'<div class="team-bio">{bio}</div>' if bio else ''}
        </div>'''
    return f'<div class="team-row">{cards}</div>'


def _render_citations(citations: list[dict], theme: dict) -> str:
    if not citations:
        return ""
    items = "".join(
        f'<a href="{html.escape(c.get("url",""))}" target="_blank" rel="noopener">'
        f'{html.escape(c.get("title") or c.get("url",""))[:60]}</a>'
        for c in citations if c.get("url")
    )
    if not items:
        return ""
    return f'<div class="citations" style="color:{theme["muted"]}">Sources: {items}</div>'


def render_slide_card(s: dict, theme: dict, idx: int, total: int) -> str:
    """Render one slide as a 16:9 visual card using ONLY fields present on `s`."""
    intent = s.get("intent", "slide")
    layout = s.get("layout", "two-column")
    headline = html.escape(str(s.get("headline") or ""))
    sub = html.escape(str(s.get("subheadline") or ""))
    body = html.escape(str(s.get("body") or ""))
    bullets = s.get("bullets") or []
    stats = s.get("stat_blocks") or []
    team = s.get("team_members") or []
    table = s.get("table")
    chart = s.get("chart")
    diagram = s.get("diagram")
    quote = s.get("quote")
    citations = s.get("citations") or []
    image_url = s.get("image_url") or (s.get("render_decision") or {}).get("image_url")

    # Layout-specific body
    center_html = ""
    if layout == "title-only":
        center_html = f'''
          <div class="title-only">
            <div class="big-headline" style="font-size:{theme['h1_pt']+8}pt">{headline}</div>
            <div class="big-sub" style="color:{theme['muted']}">{sub}</div>
          </div>'''
    elif layout == "stat-hero":
        center_html = f'''
          <div class="stat-hero">
            {_render_stat_blocks(stats, theme)}
            {f'<p class="body">{body}</p>' if body else ''}
            {_render_bullets(bullets, theme)}
          </div>'''
    elif layout == "diagram":
        center_html = f'''
          <div class="diagram-block">
            {_render_diagram(diagram, theme)}
            {f'<p class="body">{body}</p>' if body else ''}
            {_render_bullets(bullets, theme)}
          </div>'''
    elif layout == "table":
        center_html = f'''<div class="table-block">{_render_table(table, theme)}{_render_bullets(bullets, theme)}</div>'''
    elif layout in ("grid-3", "grid"):
        cells = "".join(
            f'<div class="grid-cell" style="border-color:{theme["primary"]}55">'
            f'<div class="grid-n" style="color:{theme["primary"]}">{i+1:02d}</div>'
            f'<div class="grid-t">{html.escape(str(b))}</div></div>'
            for i, b in enumerate(bullets[:6])
        )
        center_html = f'<div class="grid-3">{cells}</div>'
    elif layout == "image-full":
        bg = (
            f'background-image:url({image_url});background-size:cover;background-position:center;'
            if image_url else
            f'background:linear-gradient(135deg,{theme["primary"]} 0%,{theme["accent"]} 100%);'
        )
        center_html = f'''
          <div class="image-full" style="{bg}">
            <div class="image-full-overlay">
              <div class="big-headline" style="font-size:{theme['h1_pt']+6}pt">{headline}</div>
              <div class="big-sub" style="color:#e8ecf1dd">{sub}</div>
              {_render_bullets(bullets, theme) if bullets else ''}
            </div>
          </div>'''
    elif layout == "two-column":
        right_block = ""
        if stats:
            right_block = _render_stat_blocks(stats, theme)
        elif team:
            right_block = _render_team(team, theme)
        elif chart:
            right_block = _render_chart(chart, theme)
        elif table:
            right_block = _render_table(table, theme)
        elif diagram:
            right_block = _render_diagram(diagram, theme)
        elif bullets:
            right_block = _render_bullets(bullets, theme)
        else:
            right_block = f'<div class="kicker" style="color:{theme["muted"]}">{html.escape(intent).upper()}</div>'
        left_body = f'<p class="body">{body}</p>' if body else ""
        if not body and bullets and right_block != _render_bullets(bullets, theme):
            left_body = _render_bullets(bullets, theme)
        center_html = f'''
          <div class="two-col">
            <div class="tc-left">
              {left_body}
            </div>
            <div class="tc-right">{right_block}</div>
          </div>'''
    else:
        center_html = f'''
          <div class="fallback">
            {f'<p class="body">{body}</p>' if body else ''}
            {_render_bullets(bullets, theme)}
            {_render_stat_blocks(stats, theme)}
            {_render_table(table, theme) if table else ''}
            {_render_chart(chart, theme) if chart else ''}
            {_render_diagram(diagram, theme) if diagram else ''}
            {_render_team(team, theme) if team else ''}
          </div>'''

    # Header (headline + subheadline) — skip for title-only/image-full which render their own
    header = ""
    if layout not in ("title-only", "image-full"):
        header = f'''
          <div class="slide-header">
            <div class="headline" style="font-size:{theme['h1_pt']}pt;color:{theme['text']};font-family:{theme['heading_font']}">{headline}</div>
            {f'<div class="sub" style="color:{theme["muted"]}">{sub}</div>' if sub else ''}
          </div>'''

    quote_html = ""
    if quote and isinstance(quote, dict) and quote.get("text"):
        qt = html.escape(str(quote.get("text", "")))
        qa = html.escape(str(quote.get("author") or ""))
        quote_html = f'<blockquote class="quote" style="border-color:{theme["accent"]}"><p>“{qt}”</p>{f"<cite>— {qa}</cite>" if qa else ""}</blockquote>'

    footer = f'''
      <div class="slide-footer">
        <span class="badge" style="background:{theme['primary']}22;color:{theme['primary']}">#{idx+1}/{total} · {html.escape(intent)} · {html.escape(layout)}</span>
        {_render_citations(citations, theme)}
      </div>'''

    return f'''
      <div class="slide-frame" style="background:{theme['bg']}">
        <article class="slide-card" style="background:{theme['bg']};color:{theme['text']};font-family:{theme['body_font']}">
          {header}
          {center_html}
          {quote_html}
          {footer}
        </article>
      </div>'''


def _field_row(label: str, value: Any, *, is_code: bool = False) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return f'<tr><td class="lbl">{html.escape(label)}</td><td class="empty">— empty —</td></tr>'
    if is_code or isinstance(value, (dict, list)):
        return f'<tr><td class="lbl">{html.escape(label)}</td><td><pre>{_fmt_json(value)}</pre></td></tr>'
    return f'<tr><td class="lbl">{html.escape(label)}</td><td>{html.escape(str(value))}</td></tr>'


def render_html(mode: str, project_id: str, status_doc: dict[str, Any], slides_doc: dict[str, Any]) -> str:
    project = slides_doc.get("project", {})
    slides = slides_doc.get("slides", [])
    log = status_doc.get("progress_log", [])
    trace = status_doc.get("llm_trace_summary", [])
    theme = _extract_theme(status_doc)

    # Rendered slide cards — the visual preview the user wants
    rendered_cards = "".join(
        render_slide_card(s, theme, i, len(slides)) for i, s in enumerate(slides)
    )

    # Slide feature coverage — what the user explicitly asked for
    feature_counts = {
        "with_image_prompt": sum(1 for s in slides if s.get("image_prompt")),
        "with_image_url": sum(1 for s in slides if s.get("image_url") or (s.get("render_decision") or {}).get("image_url")),
        "with_chart": sum(1 for s in slides if s.get("chart")),
        "with_table": sum(1 for s in slides if s.get("table")),
        "with_diagram": sum(1 for s in slides if s.get("diagram")),
        "with_timeline": sum(1 for s in slides if s.get("timeline")),
        "with_comparison": sum(1 for s in slides if s.get("comparison")),
        "with_quote": sum(1 for s in slides if s.get("quote")),
        "with_team": sum(1 for s in slides if s.get("team_members")),
        "with_stats": sum(1 for s in slides if s.get("stat_blocks")),
        "with_notes": sum(1 for s in slides if s.get("speaker_notes")),
        "with_citations": sum(1 for s in slides if s.get("citations")),
    }

    chips = " ".join(
        f'<span class="chip {"ok" if v else "zero"}">{html.escape(k)}: {v}</span>'
        for k, v in feature_counts.items()
    )

    slide_html_parts: list[str] = []
    for i, s in enumerate(slides):
        rows = "".join([
            _field_row("index", s.get("index")),
            _field_row("intent", s.get("intent")),
            _field_row("layout", s.get("layout")),
            _field_row("headline", s.get("headline")),
            _field_row("subheadline", s.get("subheadline")),
            _field_row("body", s.get("body")),
            _field_row("bullets", s.get("bullets")),
            _field_row("stat_blocks", s.get("stat_blocks")),
            _field_row("quote", s.get("quote")),
            _field_row("chart", s.get("chart")),
            _field_row("table", s.get("table")),
            _field_row("timeline", s.get("timeline")),
            _field_row("comparison", s.get("comparison")),
            _field_row("diagram", s.get("diagram")),
            _field_row("team_members", s.get("team_members")),
            _field_row("company_icon_url", s.get("company_icon_url")),
            _field_row("image_prompt", s.get("image_prompt")),
            _field_row("image_url", s.get("image_url") or (s.get("render_decision") or {}).get("image_url")),
            _field_row("render_decision", s.get("render_decision")),
            _field_row("speaker_notes", s.get("speaker_notes")),
            _field_row("citations", s.get("citations")),
            _field_row("rationale", s.get("rationale")),
        ])
        slide_html_parts.append(f'''
<section class="slide">
  <h2>#{i + 1} · {html.escape(str(s.get("intent", "slide")))} <small>({html.escape(str(s.get("layout", "")))})</small></h2>
  <table>{rows}</table>
</section>
''')

    log_rows = "".join(
        f'<tr><td>{html.escape(str(e.get("stage", "")))}</td>'
        f'<td><pre>{_fmt_json({k: v for k, v in e.items() if k != "stage"})}</pre></td></tr>'
        for e in log
    )
    trace_rows = "".join(
        f'<tr><td>{html.escape(str(t.get("model", "")))}</td>'
        f'<td>{html.escape(str(t.get("role", "")))}</td>'
        f'<td>{html.escape(str(t.get("phase", "")))}</td>'
        f'<td>{t.get("latency_ms", "-")}</td>'
        f'<td>{t.get("tokens_in", "-")}/{t.get("tokens_out", "-")}</td></tr>'
        for t in trace
    )

    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Deck {mode} · {project_id}</title>
<style>
 body{{font:14px/1.4 system-ui,sans-serif;background:#0b0d10;color:#e8ecf1;margin:0;padding:24px;max-width:1200px;margin:0 auto}}
 h1{{color:#fff;border-bottom:2px solid #3b82f6;padding-bottom:8px}}
 h2{{color:#60a5fa;margin-top:28px}} h2 small{{color:#94a3b8;font-weight:400;font-size:13px}}
 section.slide{{background:#141820;border:1px solid #222833;border-radius:8px;padding:16px 20px;margin:14px 0}}
 table{{width:100%;border-collapse:collapse}}
 td{{padding:6px 10px;vertical-align:top;border-bottom:1px solid #222833}}
 td.lbl{{width:180px;color:#94a3b8;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px}}
 td.empty{{color:#6b7280;font-style:italic}}
 pre{{background:#0a0c10;padding:10px;border-radius:4px;overflow-x:auto;margin:0;font-size:12px;color:#cbd5e1}}
 .meta{{background:#141820;border:1px solid #222833;padding:12px 16px;border-radius:8px;margin-bottom:16px}}
 .chip{{display:inline-block;padding:2px 8px;margin:2px;border-radius:3px;font-size:12px;font-family:ui-monospace,monospace}}
 .chip.ok{{background:#064e3b;color:#6ee7b7}} .chip.zero{{background:#1f2937;color:#6b7280}}
 nav{{margin:10px 0 20px}} nav a{{color:#60a5fa;margin-right:12px}}

 /* ── Rendered slide preview ───────────────────────────────── */
 .deck-preview{{display:flex;flex-direction:column;gap:28px;margin:16px 0 32px}}
 /* Each slide is a scalable 1280x720 design surface. The outer .slide-frame
    keeps the 16:9 aspect ratio at the container width; the inner .slide-card
    is a fixed 1280x720 box that we scale down to fit. */
 .slide-frame{{width:100%;max-width:1120px;aspect-ratio:16/9;position:relative;
   border-radius:14px;overflow:hidden;box-shadow:0 20px 60px #000a,0 2px 0 #ffffff0a inset;
   container-type:inline-size}}
 .slide-card{{width:1280px;height:720px;transform-origin:top left;
   transform:scale(calc(100cqw / 1280px));
   padding:56px 72px;display:flex;flex-direction:column;gap:22px;
   position:relative;overflow:hidden;box-sizing:border-box}}
 .slide-card .slide-header{{display:flex;flex-direction:column;gap:6px}}
 .slide-card .headline{{font-weight:700;line-height:1.1;letter-spacing:-0.01em}}
 .slide-card .sub{{font-size:16pt;line-height:1.35;max-width:900px}}
 .slide-card .body{{font-size:14pt;line-height:1.5;margin:0;max-width:780px}}
 .slide-card ul.bullets{{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:10px}}
 .slide-card ul.bullets li{{position:relative;padding-left:22px;font-size:13pt;line-height:1.4}}
 .slide-card ul.bullets li:before{{content:"";position:absolute;left:0;top:8px;width:10px;height:10px;border-radius:2px;background:currentColor;opacity:.6}}
 .slide-card .two-col{{display:grid;grid-template-columns:1.1fr 1fr;gap:40px;flex:1;min-height:0}}
 .slide-card .tc-left,.slide-card .tc-right{{display:flex;flex-direction:column;justify-content:center;gap:14px;min-width:0}}
 .slide-card .stats-row{{display:flex;gap:32px;flex-wrap:wrap;align-items:flex-end}}
 .slide-card .stat{{display:flex;flex-direction:column;gap:4px;min-width:140px}}
 .slide-card .stat-value{{font-size:44pt;font-weight:800;line-height:1;letter-spacing:-0.02em}}
 .slide-card .stat-label{{font-size:12pt;opacity:.75;text-transform:uppercase;letter-spacing:.08em}}
 .slide-card .stat-hero{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:22px}}
 .slide-card .stat-hero .stat-value{{font-size:60pt}}
 .slide-card .title-only{{flex:1;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;gap:18px}}
 .slide-card .big-headline{{font-weight:800;line-height:1.05;letter-spacing:-0.02em;max-width:95%}}
 .slide-card .big-sub{{font-size:18pt;max-width:90%;line-height:1.35}}
 .slide-card .image-full{{flex:1;margin:-44px -56px;position:relative;display:flex;align-items:flex-end}}
 .slide-card .image-full-overlay{{padding:44px 56px 40px;width:100%;
   background:linear-gradient(transparent,#000000bb);color:#fff;display:flex;flex-direction:column;gap:12px}}
 .slide-card .grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;flex:1}}
 .slide-card .grid-cell{{border:1px solid;border-radius:10px;padding:20px;display:flex;flex-direction:column;gap:10px;justify-content:space-between}}
 .slide-card .grid-n{{font-size:14pt;font-weight:800;letter-spacing:.05em}}
 .slide-card .grid-t{{font-size:13pt;line-height:1.35}}
 .slide-card .preview-table{{width:100%;border-collapse:collapse;border:1px solid;border-radius:6px;overflow:hidden}}
 .slide-card .preview-table th,.slide-card .preview-table td{{padding:10px 14px;text-align:left;font-size:12pt;border:none;border-bottom:1px solid #ffffff14}}
 .slide-card .preview-table th{{background:#ffffff10;font-weight:700;font-size:11pt;text-transform:uppercase;letter-spacing:.05em}}
 .slide-card .preview-table caption{{caption-side:bottom;font-size:11pt;padding:8px;opacity:.7;text-align:left}}
 .slide-card .preview-chart{{width:100%;max-width:640px;height:auto}}
 .slide-card .preview-diagram{{width:100%;height:auto;max-height:260px}}
 .slide-card .diagram-block{{display:flex;flex-direction:column;gap:14px;flex:1;justify-content:center}}
 .slide-card .team-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;flex:1}}
 .slide-card .team-card{{border:1px solid;border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:6px;align-items:flex-start}}
 .slide-card .team-card img,.slide-card .avatar-fallback{{width:56px;height:56px;border-radius:50%;object-fit:cover;background:#ffffff18}}
 .slide-card .team-name{{font-weight:700;font-size:13pt}}
 .slide-card .team-role{{font-size:11pt}}
 .slide-card .team-bio{{font-size:10.5pt;opacity:.8;line-height:1.35}}
 .slide-card .quote{{border-left:4px solid;padding:6px 18px;margin:0;font-size:15pt;font-style:italic;line-height:1.4}}
 .slide-card .quote cite{{display:block;font-size:12pt;font-style:normal;margin-top:8px;opacity:.75}}
 .slide-card .slide-footer{{margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;gap:16px;font-size:10.5pt;flex-wrap:wrap}}
 .slide-card .badge{{padding:4px 10px;border-radius:4px;font-family:ui-monospace,monospace;font-size:10pt;font-weight:600}}
 .slide-card .citations a{{color:inherit;text-decoration:underline;margin-right:10px;font-size:10pt;opacity:.75}}
 .slide-card .kicker{{font-size:11pt;font-weight:700;letter-spacing:.12em}}
 .slide-card .fallback{{display:flex;flex-direction:column;gap:12px;flex:1}}
</style></head><body>
<h1>Deck Viewer — <em>{html.escape(mode)}</em> mode</h1>
<nav>
  <a href="#preview">Rendered preview</a>
  <a href="#summary">Summary</a>
  <a href="#features">Feature coverage</a>
  <a href="#slides">Slides (fields)</a>
  <a href="#log">Pipeline log</a>
  <a href="#trace">LLM trace</a>
  <a href="#raw">Raw JSON</a>
</nav>

<h2 id="preview">Rendered slides <small>— 16:9 preview, theme from design_resolver, data from this run only</small></h2>
<div class="deck-preview">
{rendered_cards if slides else "<p><i>No slides to render.</i></p>"}
</div>

<div class="meta" id="summary">
<b>project_id:</b> {html.escape(project_id)}<br>
<b>title:</b> {html.escape(str(project.get("title", "—")))}<br>
<b>mode (server):</b> {html.escape(str(project.get("mode", "—")))}<br>
<b>purpose:</b> {html.escape(str(project.get("purpose", "—")))}<br>
<b>slide_count:</b> {project.get("slide_count", len(slides))}<br>
<b>company_name:</b> {html.escape(str(project.get("company_name") or "—"))}<br>
<b>company_icon_url:</b> {html.escape(str(project.get("company_icon_url") or "—"))}<br>
<b>narrative_arc:</b> {html.escape(str(project.get("narrative_arc", "—")))[:500]}<br>
<b>intent_summary:</b> {html.escape(", ".join(project.get("intent_summary") or []))}<br>
<b>status:</b> {html.escape(str(status_doc.get("status")))} · <b>overall_score:</b> {status_doc.get("overall_score")} · <b>duration:</b> {status_doc.get("duration_ms")} ms
</div>

<h2 id="features">Feature coverage — are images/charts/tables/teams present?</h2>
<div class="meta">{chips}</div>

<h2 id="slides">Slides ({len(slides)})</h2>
{"".join(slide_html_parts) if slides else "<p><i>No slides returned.</i></p>"}

<h2 id="log">Pipeline progress log (last {len(log)} events)</h2>
<table><thead><tr><td class="lbl">stage</td><td class="lbl">payload</td></tr></thead><tbody>{log_rows}</tbody></table>

<h2 id="trace">LLM trace ({len(trace)} calls)</h2>
<table><thead><tr><td class="lbl">model</td><td class="lbl">role</td><td class="lbl">phase</td><td class="lbl">lat(ms)</td><td class="lbl">tok in/out</td></tr></thead><tbody>{trace_rows}</tbody></table>

<h2 id="raw">Raw slides JSON</h2>
<pre>{_fmt_json(slides_doc)}</pre>

</body></html>
'''


# ── HTTP server ─────────────────────────────────────────────────────


def serve(port: int, html_provider) -> None:
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if self.path in ("/", "/index.html"):
                body = html_provider().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/raw.json":
                body = html_provider.__self__.raw_json.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, fmt, *args):
            sys.stdout.write(f"[http:{port}] {fmt % args}\n")

    HTTPServer(("127.0.0.1", port), H).serve_forever()


class State:
    def __init__(self):
        self.phase = "starting"
        self.pid = None
        self.html = None
        self.raw_json = "{}"
        self.err = None

    def current_html(self) -> str:
        if self.phase == "starting":
            return "<h1>Booting...</h1><script>setTimeout(()=>location.reload(),2000)</script>"
        if self.phase == "generating":
            return f"""
            <html><head><style>
            body {{ font-family: system-ui; background: #fafafa; padding: 2rem; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            </style></head>
            <body>
            <h1>Generating... project_id={self.pid}</h1>
            <p>WebSocket live stream initialized.</p>
            <div id="slides"></div>
            <script>
                const ws = new WebSocket("ws://127.0.0.1:8003/ws/v4/progress/{self.pid}");
                ws.onmessage = (e) => {{
                    try {{
                        const msg = JSON.parse(e.data);
                        if (msg.stage === "slide_drafted" && msg.payload && msg.payload.compiled) {{
                            const container = document.getElementById("slides");
                            const div = document.createElement("div");
                            div.className = "card";
                            const slide = msg.payload.compiled;
                            div.innerHTML = "<h3>" + (slide.kit_component || "Slide") + ": " + (slide.headline || msg.payload.headline) + "</h3>" +
                                            "<pre style='font-size: 10px;'>" + JSON.stringify(slide, null, 2) + "</pre>";
                            container.appendChild(div);
                        }} else if (msg.type === "status" && (msg.status === "completed" || msg.status === "failed")) {{
                            setTimeout(() => location.reload(), 1000);
                        }}
                    }} catch (err) {{}}
                }};
            </script>
            </body></html>
            """
        if self.phase == "error":
            return f"<h1>Error</h1><pre>{html.escape(str(self.err))}</pre>"
        return self.html  # done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["standard", "premium"], required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--reuse-project-id", default=None,
                    help="Skip generation and render an existing completed project by id.")
    args = ap.parse_args()

    payload = STANDARD_INPUT if args.mode == "standard" else PREMIUM_INPUT
    state = State()

    def run():
        try:
            if args.reuse_project_id:
                state.pid = args.reuse_project_id
                state.phase = "generating"
                print(f"[reuse] project_id={state.pid} — skipping generation", flush=True)
                status_doc = poll_until_done(state.pid, max_seconds=2400)
            else:
                state.phase = "generating"
                state.pid = fire_generation(payload)
                status_doc = poll_until_done(state.pid, max_seconds=1800)
            slides_doc = fetch_slides(state.pid)
            state.html = render_html(args.mode, state.pid, status_doc, slides_doc)
            state.raw_json = json.dumps({"status": status_doc, "slides": slides_doc}, indent=2, default=str)
            state.phase = "done"
            print(f"[done] {args.mode} deck ready at http://127.0.0.1:{args.port}/", flush=True)
        except Exception as e:
            state.err = f"{type(e).__name__}: {e}"
            state.phase = "error"
            import traceback
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    print(f"[serve] http://127.0.0.1:{args.port}/  (mode={args.mode})", flush=True)
    serve(args.port, state.current_html)


if __name__ == "__main__":
    main()
