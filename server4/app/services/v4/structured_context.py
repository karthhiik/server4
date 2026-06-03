"""
V4 Structured Context — extracts Premium structured input into a single
authoritative payload that flows through the pipeline (planner + writer +
team resolver). This is the fix for the "premium input is dropped" bug where
rich team/financials/competitors/market/fundraising data never reached the
writer prompts.

Design contract:
  - StructuredContext is a plain dict (JSON-safe, easy to pass through
    Celery/Redis/WebSocket if needed)
  - Every section is Optional; pipeline stages check presence before using
  - Writer injects ONLY the relevant section per intent (not the whole blob)
    to stay inside token budgets
  - All output is deterministic text — no LLM calls here
"""

from __future__ import annotations

from typing import Any, Optional


def build_structured_context(premium_input_dict: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Normalize a PremiumStructuredInput.model_dump() into a flat context.

    Returns an empty dict when no structured input is provided — downstream
    callers can use `bool(ctx)` to check presence.
    """
    if not premium_input_dict:
        return {}
    out: dict[str, Any] = {}
    for key in (
        "topic", "description", "audience", "audience_sophistication",
        "language", "writing_style", "slide_count",
    ):
        val = premium_input_dict.get(key)
        if val not in (None, "", []):
            out[key] = val
    for section in (
        "company", "financials", "competitors", "traction",
        "team", "fundraising", "market", "content_directives",
    ):
        val = premium_input_dict.get(section)
        if val:
            out[section] = val
    return out


# ─────────────────────────────────────────────────────────────────
# Per-intent writer injection — what the slide writer actually sees
# ─────────────────────────────────────────────────────────────────

# Intents → which structured sections are authoritative source-of-truth
# for that slide. The writer MUST use these facts verbatim.
_INTENT_SECTIONS: dict[str, tuple[str, ...]] = {
    "title":          ("company",),
    "problem":        ("company", "market"),
    "solution":       ("company",),
    "product":        ("company",),
    "how_it_works":   ("company",),
    "market":         ("market", "company"),
    "traction":       ("traction", "financials", "company"),
    "business_model": ("financials", "company"),
    "competition":    ("competitors", "company"),
    "team":           ("team", "company"),
    "financials":     ("financials", "traction"),
    "ask":            ("fundraising", "company"),
    "thank_you":      ("company",),
    "vision":         ("company",),
    "go_to_market":   ("market", "company"),
    "technology":     ("company",),
}


def _fmt_currency(val: Any) -> str:
    try:
        n = float(val)
    except (TypeError, ValueError):
        return str(val)
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n:,.0f}"


def _fmt_company(c: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if c.get("name"):
        lines.append(f"  name: {c['name']}")
    if c.get("tagline"):
        lines.append(f"  tagline: {c['tagline']}")
    if c.get("industry"):
        lines.append(f"  industry: {c['industry']}")
    if c.get("stage"):
        lines.append(f"  stage: {c['stage']}")
    if c.get("founded_year"):
        lines.append(f"  founded: {c['founded_year']}")
    if c.get("location"):
        lines.append(f"  location: {c['location']}")
    if c.get("team_size"):
        lines.append(f"  team_size: {c['team_size']}")
    if c.get("website_url"):
        lines.append(f"  website: {c['website_url']}")
    return lines


def _fmt_financials(f: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    mapping = [
        ("arr", "ARR", _fmt_currency),
        ("mrr", "MRR", _fmt_currency),
        ("revenue_growth_pct", "Growth", lambda v: f"{v}% MoM/YoY"),
        ("gross_margin_pct", "Gross margin", lambda v: f"{v}%"),
        ("cac", "CAC", _fmt_currency),
        ("ltv", "LTV", _fmt_currency),
        ("burn_rate", "Burn rate", lambda v: f"{_fmt_currency(v)} /mo"),
        ("runway_months", "Runway", lambda v: f"{v} months"),
        ("customers_count", "Customers", lambda v: f"{v:,}"),
        ("users_count", "Users", lambda v: f"{v:,}"),
        ("total_funding_raised", "Total raised to date", _fmt_currency),
    ]
    for key, label, fmt in mapping:
        v = f.get(key)
        if v is not None:
            try:
                lines.append(f"  {label}: {fmt(v)}")
            except Exception:
                lines.append(f"  {label}: {v}")
    custom = f.get("custom_metrics") or {}
    for k, v in custom.items():
        lines.append(f"  {k}: {v}")
    return lines


def _fmt_market(m: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, label in (
        ("tam", "TAM"), ("sam", "SAM"), ("som", "SOM"),
        ("market_growth_rate", "Growth rate"),
        ("target_segment", "Target segment"),
    ):
        v = m.get(key)
        if v:
            # Format currency values with proper currency formatting
            if key in ("tam", "sam", "som"):
                formatted = _fmt_currency(v)
            else:
                formatted = str(v)
            lines.append(f"  {label}: {formatted}")
    sources = m.get("sources") or []
    if sources:
        lines.append(f"  sources: {', '.join(sources[:5])}")
    return lines


def _fmt_competitors(comps: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for c in comps[:8]:
        parts = [c.get("name") or "unknown"]
        if c.get("description"):
            parts.append(c["description"])
        lines.append(f"  - {' — '.join(parts)}")
        if c.get("strengths"):
            lines.append(f"      strengths: {', '.join(c['strengths'][:5])}")
        if c.get("weaknesses"):
            lines.append(f"      weaknesses: {', '.join(c['weaknesses'][:5])}")
        if c.get("differentiator"):
            lines.append(f"      our differentiator: {c['differentiator']}")
    return lines


def _fmt_traction(t: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if t.get("key_milestones"):
        lines.append("  milestones:")
        for m in t["key_milestones"][:8]:
            lines.append(f"    - {m}")
    if t.get("notable_customers"):
        lines.append(f"  notable_customers: {', '.join(t['notable_customers'][:12])}")
    if t.get("partnerships"):
        lines.append(f"  partnerships: {', '.join(t['partnerships'][:8])}")
    if t.get("press_mentions"):
        lines.append(f"  press: {', '.join(t['press_mentions'][:6])}")
    if t.get("awards"):
        lines.append(f"  awards: {', '.join(t['awards'][:6])}")
    gm = t.get("growth_metrics") or {}
    for k, v in gm.items():
        lines.append(f"  {k}: {v}")
    return lines


def _fmt_team(team: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for m in team[:8]:
        role = f" ({m['role']})" if m.get("role") else ""
        lines.append(f"  - {m.get('name', '')}{role}")
        if m.get("bio"):
            lines.append(f"      bio: {m['bio']}")
        if m.get("linkedin_url"):
            lines.append(f"      linkedin: {m['linkedin_url']}")
        if m.get("x_url"):
            lines.append(f"      x_url: {m['x_url']}")
        if m.get("photo_url"):
            lines.append(f"      photo: {m['photo_url']}")
        if m.get("notable_credentials"):
            lines.append(f"      credentials: {', '.join(m['notable_credentials'][:5])}")
    return lines


def _fmt_fundraising(f: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if f.get("amount"):
        lines.append(f"  raising: {_fmt_currency(f['amount'])}")
    if f.get("round_type"):
        lines.append(f"  round: {f['round_type']}")
    if f.get("timeline"):
        lines.append(f"  timeline: {f['timeline']}")
    if f.get("valuation_cap"):
        lines.append(f"  valuation_cap: {_fmt_currency(f['valuation_cap'])}")
    if f.get("previous_investors"):
        lines.append(f"  previous_investors: {', '.join(f['previous_investors'][:8])}")
    if f.get("use_of_funds"):
        lines.append("  use_of_funds:")
        for u in f["use_of_funds"][:8]:
            lines.append(f"    - {u}")
    return lines


_SECTION_FORMATTERS = {
    "company":      _fmt_company,
    "financials":   _fmt_financials,
    "market":       _fmt_market,
    "competitors":  _fmt_competitors,
    "traction":     _fmt_traction,
    "team":         _fmt_team,
    "fundraising":  _fmt_fundraising,
}


def format_for_writer(intent: str, ctx: dict[str, Any]) -> str:
    """Produce the writer-facing text block for a specific slide intent.

    Returns '' if no structured data applies to this intent. When present,
    the block is marked AUTHORITATIVE and the writer must prefer these
    numbers over any research evidence.
    """
    if not ctx:
        return ""

    sections = _INTENT_SECTIONS.get((intent or "").lower(), ("company",))
    blocks: list[str] = []
    for section in sections:
        data = ctx.get(section)
        if not data:
            continue
        fmt = _SECTION_FORMATTERS.get(section)
        if fmt is None:
            continue
        lines = fmt(data)
        if lines:
            blocks.append(f"{section}:\n" + "\n".join(lines))

    # Content directives — key_messages and emphasis apply to every slide.
    directives = ctx.get("content_directives") or {}
    directive_lines: list[str] = []
    if directives.get("key_messages"):
        directive_lines.append("  key_messages (every slide should advance at least one):")
        for k in directives["key_messages"][:6]:
            directive_lines.append(f"    - {k}")
    if directives.get("tone_keywords"):
        directive_lines.append(f"  tone: {', '.join(directives['tone_keywords'][:6])}")
    if directives.get("emphasis"):
        directive_lines.append(f"  emphasis: {', '.join(directives['emphasis'][:6])}")
    if directives.get("avoid_topics"):
        directive_lines.append(f"  avoid: {', '.join(directives['avoid_topics'][:6])}")
    if directive_lines:
        blocks.append("directives:\n" + "\n".join(directive_lines))

    if not blocks:
        return ""

    return (
        "\n\nSTRUCTURED USER INPUT (AUTHORITATIVE — these facts are ground truth;\n"
        "use them verbatim on the slide; NEVER contradict or paraphrase numbers;\n"
        "when a metric is listed here, PUT IT IN A stat_block OR chart, not prose):\n"
        + "\n".join(blocks)
        + "\n"
    )


def team_user_answer(ctx: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Shape the structured team[] into the dict that team_resolver expects.

    Returns None when no team data provided, which lets the resolver fall
    through to its existing resolution chain (docs → preflight → search).
    """
    team = ctx.get("team") or []
    if not team:
        return None
    members: list[dict[str, Any]] = []
    for m in team:
        if not isinstance(m, dict):
            continue
        name = (m.get("name") or "").strip()
        if not name:
            continue
        bio_parts: list[str] = []
        if m.get("bio"):
            bio_parts.append(str(m["bio"]))
        if m.get("notable_credentials"):
            bio_parts.append(" · ".join(m["notable_credentials"][:5]))
        members.append({
            "name": name,
            "role": (m.get("role") or "").strip(),
            "bio": " — ".join(bio_parts) if bio_parts else None,
            "linkedin_url": m.get("linkedin_url"),
            "x_url": m.get("x_url"),
            "photo_url": m.get("photo_url"),
        })
    if not members:
        return None
    return {"members": members}
