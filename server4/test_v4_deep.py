#!/usr/bin/env python3
"""
V4 Content Pipeline — Deep Real-World Test Harness.

Tests both Standard and Premium modes against the LIVE pipeline using real
LLMs (Groq / GPT-4o-mini / DeepSeek / Kimi / Phi-4) and real research APIs
(Tavily / Serper / NewsAPI / NewsData / Reddit / GitHub / Finnhub).

Six scenarios:
  STD-1  Standard / clear B2B SaaS pitch
  STD-2  Standard / vague unclear input  ("make some cool slides")
  STD-3  Standard / minimal one-word seed ("fintech")
  PRM-1  Premium / clear pitch + explicit YC slide types
  PRM-2  Premium / clear pitch, AUTO slide types (let planner decide)
  PRM-3  Premium / unclear seed (stress narrative inference)

Captures per scenario:
  - per-stage timing (research / skeleton / writers / critic)
  - research depth (citations, news, sources used, cache hit)
  - skeleton structure (intents, narrative arc, slide count)
  - generated slides (headline, bullets, stat blocks, citations)
  - critic scores per slide and overall
  - quality assertions (density caps, headline length, citation grounding)
  - failure mode classification + traceback

Outputs:
  test_v4_deep_report.md   (human-readable founder report)
  test_v4_deep_raw.json    (full raw payload for archival / re-analysis)

Run from server4/:
    python test_v4_deep.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── env loading + path setup ────────────────────────────────────────
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
except Exception:
    pass

# ── pipeline imports (after sys.path) ───────────────────────────────
from app.database import connect_db, close_db, get_db  # noqa: E402
from app.services.v4 import V4ContentPipeline  # noqa: E402
from app.services.v4.content_pipeline import V4PipelineResult  # noqa: E402


# ── Scenario definitions ────────────────────────────────────────────

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "STD-1",
        "label": "Standard / clear B2B SaaS pitch",
        "mode": "standard",
        "user_query": (
            "Create a 10-slide pitch deck for Northwind AI, a B2B SaaS that uses "
            "agentic LLM workflows to automate enterprise procurement. Target audience "
            "is seed-stage VCs. Series-Seed raise of $3M."
        ),
        "analysis": {
            "purpose": "investor_pitch",
            "audience": "seed-stage VCs",
            "industry": "enterprise SaaS / procurement automation",
            "company": "Northwind AI",
            "tone": "confident, data-backed",
            "suggested_slide_types": [],
        },
        "purpose": "investor_pitch",
        "industry": "enterprise SaaS",
        "company_name": "Northwind AI",
        "user_slide_types": None,
        "target_slide_count": 8,
        "timeout_s": 240,
    },
    {
        "id": "STD-2",
        "label": "Standard / vague unclear input",
        "mode": "standard",
        "user_query": "make some cool slides about something",
        "analysis": {
            "purpose": "general",
            "audience": "unknown",
            "industry": "unknown",
            "tone": "neutral",
            "suggested_slide_types": [],
        },
        "purpose": "general",
        "industry": None,
        "company_name": None,
        "user_slide_types": None,
        "target_slide_count": 6,
        "timeout_s": 180,
    },
    {
        "id": "STD-3",
        "label": "Standard / minimal one-word seed",
        "mode": "standard",
        "user_query": "fintech",
        "analysis": {
            "purpose": "general",
            "audience": "unknown",
            "industry": "fintech",
            "tone": "neutral",
            "suggested_slide_types": [],
        },
        "purpose": "general",
        "industry": "fintech",
        "company_name": None,
        "user_slide_types": None,
        "target_slide_count": 5,
        "timeout_s": 180,
    },
    {
        "id": "PRM-1",
        "label": "Premium / clear pitch with explicit YC slide types",
        "mode": "premium",
        "user_query": (
            "Investor pitch deck for VoltGrid, a fast-charging EV network operator "
            "deploying 350kW chargers across European A-roads. Series A, raising $25M "
            "to scale from 40 to 250 stations across DE/FR/NL. Profitable per-station "
            "unit economics with 18-month payback. Strategic partnership with Shell "
            "Recharge."
        ),
        "analysis": {
            "purpose": "investor_pitch",
            "audience": "Series A VCs (European climate funds)",
            "industry": "EV charging infrastructure",
            "company": "VoltGrid",
            "tone": "ambitious, evidence-led",
            "suggested_slide_types": [],
        },
        "purpose": "investor_pitch",
        "industry": "EV charging",
        "company_name": "VoltGrid",
        "user_slide_types": [
            "title", "problem", "solution", "market",
            "traction", "business_model", "team", "ask",
        ],
        "target_slide_count": 8,
        "timeout_s": 300,
    },
    {
        "id": "PRM-2",
        "label": "Premium / clear pitch, AUTO slide types (planner decides)",
        "mode": "premium",
        "user_query": (
            "Pitch deck for Helio Diagnostics — AI-powered radiology second-opinion "
            "service. We screen mammograms and chest CTs and flag missed cancers. "
            "FDA 510(k) cleared Q1 2026. 14 hospital pilot customers, $480k ARR, "
            "growing 22% MoM. Raising $8M Series A from healthtech VCs."
        ),
        "analysis": {
            "purpose": "investor_pitch",
            "audience": "healthtech Series A VCs",
            "industry": "medical imaging AI",
            "company": "Helio Diagnostics",
            "tone": "clinical, credible, data-rich",
            "suggested_slide_types": [],
        },
        "purpose": "investor_pitch",
        "industry": "medical imaging",
        "company_name": "Helio Diagnostics",
        "user_slide_types": None,
        "target_slide_count": 8,
        "timeout_s": 300,
    },
    {
        "id": "PRM-3",
        "label": "Premium / unclear seed (stress narrative inference)",
        "mode": "premium",
        "user_query": "something about my startup idea — quantum stuff",
        "analysis": {
            "purpose": "investor_pitch",
            "audience": "unknown",
            "industry": "quantum computing",
            "tone": "exploratory",
            "suggested_slide_types": [],
        },
        "purpose": "investor_pitch",
        "industry": "quantum computing",
        "company_name": None,
        "user_slide_types": None,
        "target_slide_count": 6,
        "timeout_s": 240,
    },
]


# ── Progress capture ────────────────────────────────────────────────

def make_capturing_emitter(events: list[dict[str, Any]]):
    async def _emit(stage: str, payload: dict[str, Any]) -> None:
        events.append({
            "stage": stage,
            "payload": payload,
            "ts": datetime.now(timezone.utc).isoformat(),
            "t_perf": time.perf_counter(),
        })
    return _emit


# ── Quality assertions ──────────────────────────────────────────────

def assess_slide_quality(slide_dict: dict[str, Any]) -> dict[str, Any]:
    """Founder-level rubric: density, specificity, citation discipline."""
    issues: list[str] = []
    headline = (slide_dict.get("headline") or "").strip()
    headline_words = len(headline.split())
    if headline_words < 3:
        issues.append(f"headline_too_short ({headline_words} words)")
    if headline_words > 8:
        issues.append(f"headline_too_long ({headline_words} words)")

    bullets = slide_dict.get("bullets") or []
    if len(bullets) > 4:
        issues.append(f"too_many_bullets ({len(bullets)})")
    long_bullets = [b for b in bullets if len(str(b).split()) > 10]
    if long_bullets:
        issues.append(f"bullets_over_10_words ({len(long_bullets)})")

    has_numbers = any(ch.isdigit() for ch in headline) or any(
        any(ch.isdigit() for ch in str(b)) for b in bullets
    ) or bool(slide_dict.get("stat_blocks"))
    citations = slide_dict.get("citations") or []
    intent = slide_dict.get("intent") or ""

    if intent in {"market", "traction", "financials", "competition"} and not has_numbers:
        issues.append("data_slide_missing_numbers")
    if intent in {"market", "traction", "financials"} and len(citations) == 0:
        issues.append("data_slide_missing_citations")

    return {
        "headline_words": headline_words,
        "n_bullets": len(bullets),
        "max_bullet_words": max((len(str(b).split()) for b in bullets), default=0),
        "has_numbers": has_numbers,
        "n_citations": len(citations),
        "n_stat_blocks": len(slide_dict.get("stat_blocks") or []),
        "issues": issues,
        "passes": len(issues) == 0,
    }


def assess_deck_quality(slides: list[dict[str, Any]]) -> dict[str, Any]:
    per_slide = [assess_slide_quality(s) for s in slides]
    n = len(per_slide)
    n_pass = sum(1 for p in per_slide if p["passes"])

    layouts = [s.get("layout") for s in slides]
    adjacent_dups = sum(
        1 for i in range(1, n)
        if layouts[i] and layouts[i] == layouts[i - 1]
    )

    intents = [s.get("intent") for s in slides]
    n_unique_intents = len(set(i for i in intents if i))

    total_citations = sum(p["n_citations"] for p in per_slide)
    grounded_pct = round(
        100.0 * sum(1 for p in per_slide if p["n_citations"] > 0) / max(n, 1), 1,
    )

    return {
        "slide_count": n,
        "slides_passing": n_pass,
        "pass_rate_pct": round(100.0 * n_pass / max(n, 1), 1),
        "adjacent_layout_duplicates": adjacent_dups,
        "unique_intents": n_unique_intents,
        "total_citations_used": total_citations,
        "citation_grounded_slide_pct": grounded_pct,
        "per_slide": per_slide,
    }


# ── Run one scenario ────────────────────────────────────────────────

async def run_scenario(pipeline: V4ContentPipeline, scenario: dict[str, Any]) -> dict[str, Any]:
    sid = scenario["id"]
    print(f"\n{'='*70}\n>> {sid}: {scenario['label']}\n{'='*70}")

    events: list[dict[str, Any]] = []
    emitter = make_capturing_emitter(events)
    project_id = f"v4test-{sid.lower()}-{int(time.time())}"

    started = time.perf_counter()
    started_iso = datetime.now(timezone.utc).isoformat()

    try:
        result: V4PipelineResult = await asyncio.wait_for(
            pipeline.generate(
                project_id=project_id,
                user_id="test-founder",
                user_query=scenario["user_query"],
                analysis=scenario["analysis"],
                mode=scenario["mode"],
                purpose=scenario["purpose"],
                industry=scenario.get("industry"),
                company_name=scenario.get("company_name"),
                user_slide_types=scenario.get("user_slide_types"),
                target_slide_count=scenario.get("target_slide_count"),
                progress=emitter,
            ),
            timeout=scenario.get("timeout_s", 300),
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        slide_dicts = [asdict(s) for s in result.slides]
        deck_quality = assess_deck_quality(slide_dicts)

        # Per-stage durations from emitted events
        stage_durations: dict[str, int] = {}
        for ev in events:
            if ev["stage"] == "stage_complete":
                st = ev["payload"].get("stage")
                d = ev["payload"].get("duration_ms")
                if st and d is not None:
                    stage_durations[st] = d

        record = {
            "id": sid,
            "label": scenario["label"],
            "status": "PASS",
            "mode": scenario["mode"],
            "user_query": scenario["user_query"],
            "user_slide_types": scenario.get("user_slide_types"),
            "target_slide_count": scenario.get("target_slide_count"),
            "started_at": started_iso,
            "duration_ms_total": elapsed_ms,
            "stage_durations_ms": stage_durations,
            "deck_title": result.deck_title,
            "narrative_arc": result.narrative_arc,
            "skeleton": {
                "n_slides": len(result.skeleton.slides),
                "intents": [s.intent for s in result.skeleton.slides],
                "layouts_planned": [s.layout_hint for s in result.skeleton.slides],
                "density_targets": [s.density_target for s in result.skeleton.slides],
            },
            "research": {
                "n_citations": len(result.research.citations),
                "n_news": len(result.research.news_citations),
                "duration_ms": result.research.duration_ms,
                "cache_hit": result.research.cache_hit,
                "sources_used": sorted({c.source for c in result.research.citations + result.research.news_citations}),
                "top_5_citations": [
                    {
                        "title": c.title[:140],
                        "source": c.source,
                        "url": c.url,
                        "authority": c.source_authority,
                    }
                    for c in result.research.top_citations(5)
                ],
                "has_financial": bool(result.research.financial_data),
                "has_social": bool(result.research.social_signals),
            },
            "critic": {
                "overall": round(result.critic.overall, 2),
                "needs_rewrite_indices": result.critic.needs_rewrite_indices,
                "slide_scores": [
                    {
                        "index": s.index,
                        "overall": round(s.overall, 2),
                        "narrative_fit": round(s.narrative_fit, 2),
                        "specificity": round(s.specificity, 2),
                        "variety": round(s.variety, 2),
                        "density_compliance": round(s.density_compliance, 2),
                        "coherence": round(s.coherence, 2),
                        "issues": s.issues,
                        "needs_rewrite": s.needs_rewrite,
                    }
                    for s in result.critic.slide_scores
                ],
            },
            "deck_quality_audit": deck_quality,
            "slides": slide_dicts,
            "events": events,
            "generation_id": result.generation_id,
        }

        print(f"  [PASS] {elapsed_ms}ms -- {len(result.slides)} slides, score {round(result.critic.overall,2)}/10")
        return record
    except asyncio.TimeoutError:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        print(f"  [TIMEOUT] {elapsed_ms}ms -- scenario exceeded {scenario.get('timeout_s', 300)}s budget", flush=True)
        return {
            "id": sid,
            "label": scenario["label"],
            "status": "TIMEOUT",
            "mode": scenario["mode"],
            "user_query": scenario["user_query"],
            "started_at": started_iso,
            "duration_ms_total": elapsed_ms,
            "error_type": "TimeoutError",
            "error_message": f"Exceeded {scenario.get('timeout_s', 300)}s wall-clock budget",
            "traceback": "",
            "events": events,
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        tb = traceback.format_exc()
        print(f"  [FAIL] {elapsed_ms}ms -- {type(exc).__name__}: {exc}")
        return {
            "id": sid,
            "label": scenario["label"],
            "status": "FAIL",
            "mode": scenario["mode"],
            "user_query": scenario["user_query"],
            "started_at": started_iso,
            "duration_ms_total": elapsed_ms,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": tb,
            "events": events,
        }


# ── Markdown report renderer ────────────────────────────────────────

def render_markdown(records: list[dict[str, Any]], env_summary: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    n_total = len(records)
    n_pass = sum(1 for r in records if r["status"] == "PASS")
    n_fail = n_total - n_pass

    lines: list[str] = []
    lines.append("# V4 Content Generation — Deep Test Report\n")
    lines.append(f"**Generated:** {now}\n")
    lines.append(f"**Workspace:** server4 (Meridian V4 pipeline)\n")
    lines.append("")
    lines.append("## Executive Summary\n")
    lines.append(f"- **Scenarios run:** {n_total}")
    lines.append(f"- **Passed:** {n_pass}")
    lines.append(f"- **Failed:** {n_fail}")
    if records:
        passed = [r for r in records if r["status"] == "PASS"]
        if passed:
            avg_dur = sum(r["duration_ms_total"] for r in passed) / len(passed)
            avg_score = sum(r["critic"]["overall"] for r in passed) / len(passed)
            lines.append(f"- **Avg generation time (passing):** {int(avg_dur)} ms")
            lines.append(f"- **Avg critic score (passing):** {round(avg_score, 2)}/10")
    lines.append("")
    lines.append("## Environment Snapshot\n")
    lines.append("| Provider key | Configured |")
    lines.append("|---|---|")
    for k, v in env_summary.items():
        lines.append(f"| `{k}` | {'✅' if v else '❌'} |")
    lines.append("")

    # Per-scenario sections
    for r in records:
        lines.append(f"## {r['id']} — {r['label']}\n")
        lines.append(f"**Status:** {r['status']}  |  **Mode:** `{r['mode']}`  |  "
                     f"**Total duration:** {r['duration_ms_total']} ms\n")
        lines.append(f"**User query:** {r['user_query']}\n")
        if r.get("user_slide_types"):
            lines.append(f"**Explicit slide types:** `{r['user_slide_types']}`\n")
        if r.get("target_slide_count"):
            lines.append(f"**Target slide count:** {r['target_slide_count']}\n")

        if r["status"] == "FAIL":
            lines.append(f"### ❌ Failure\n")
            lines.append(f"- **Error type:** `{r['error_type']}`")
            lines.append(f"- **Message:** {r['error_message']}\n")
            lines.append("```")
            lines.append(r["traceback"])
            lines.append("```\n")
            continue

        # Stage timings
        sd = r.get("stage_durations_ms", {})
        lines.append("### Stage Timings\n")
        lines.append("| Stage | Duration (ms) |")
        lines.append("|---|---:|")
        for st in ("research", "skeleton", "writers", "critic"):
            lines.append(f"| {st} | {sd.get(st, '—')} |")
        lines.append(f"| **total** | **{r['duration_ms_total']}** |\n")

        # Research
        rs = r["research"]
        lines.append("### Research Quality\n")
        lines.append(f"- **Citations:** {rs['n_citations']}  |  "
                     f"**News:** {rs['n_news']}  |  "
                     f"**Sources used:** `{rs['sources_used']}`")
        lines.append(f"- **Cache hit:** {rs['cache_hit']}  |  "
                     f"**Research stage time:** {rs['duration_ms']} ms")
        lines.append(f"- **Has financial data:** {rs['has_financial']}  |  "
                     f"**Has social signals:** {rs['has_social']}")
        if rs["top_5_citations"]:
            lines.append("\n**Top citations:**\n")
            for c in rs["top_5_citations"]:
                lines.append(f"  - [{c['source']} | auth {c['authority']}] {c['title']} — {c['url']}")
        lines.append("")

        # Skeleton
        sk = r["skeleton"]
        lines.append("### Skeleton Plan\n")
        lines.append(f"- **Deck title:** {r['deck_title']}")
        lines.append(f"- **Narrative arc:** `{r['narrative_arc']}`")
        lines.append(f"- **Slides planned:** {sk['n_slides']}")
        lines.append("")
        lines.append("| # | Intent | Layout hint | Density |")
        lines.append("|---|---|---|---|")
        for i, (intent, layout, dens) in enumerate(zip(
            sk["intents"], sk["layouts_planned"], sk["density_targets"]
        )):
            lines.append(f"| {i} | {intent} | {layout} | {dens} |")
        lines.append("")

        # Critic
        cr = r["critic"]
        lines.append("### Critic Scores\n")
        lines.append(f"- **Overall:** **{cr['overall']}/10**  |  "
                     f"**Re-written slides:** {cr['needs_rewrite_indices'] or 'none'}\n")
        lines.append("| # | Overall | Narrative | Specificity | Variety | Density | Coherence | Issues |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
        for s in cr["slide_scores"]:
            issues = "; ".join(s["issues"][:3]) if s["issues"] else "—"
            lines.append(
                f"| {s['index']} | {s['overall']} | {s['narrative_fit']} | "
                f"{s['specificity']} | {s['variety']} | {s['density_compliance']} | "
                f"{s['coherence']} | {issues} |"
            )
        lines.append("")

        # Deck quality audit (founder rubric)
        dq = r["deck_quality_audit"]
        lines.append("### Founder Quality Audit\n")
        lines.append(f"- **Slide count:** {dq['slide_count']}  |  "
                     f"**Pass rate:** {dq['pass_rate_pct']}%  ({dq['slides_passing']}/{dq['slide_count']})")
        lines.append(f"- **Adjacent layout duplicates:** {dq['adjacent_layout_duplicates']}")
        lines.append(f"- **Unique intents:** {dq['unique_intents']}")
        lines.append(f"- **Citation-grounded slides:** {dq['citation_grounded_slide_pct']}%  "
                     f"|  **Total citations used:** {dq['total_citations_used']}\n")

        # Generated slide content
        lines.append("### Generated Slide Content\n")
        for i, slide in enumerate(r["slides"]):
            lines.append(f"#### Slide {i} — `{slide.get('intent')}` / `{slide.get('layout')}`")
            lines.append(f"**Headline:** {slide.get('headline','')}")
            if slide.get("subheadline"):
                lines.append(f"**Subheadline:** {slide['subheadline']}")
            bullets = slide.get("bullets") or []
            if bullets:
                lines.append("**Bullets:**")
                for b in bullets:
                    lines.append(f"  - {b}")
            sb = slide.get("stat_blocks") or []
            if sb:
                lines.append("**Stat blocks:**")
                for s in sb:
                    lines.append(f"  - **{s.get('value','?')}** — {s.get('label','')}")
            if slide.get("body"):
                lines.append(f"**Body:** {slide['body']}")
            if slide.get("quote"):
                q = slide["quote"]
                lines.append(f"**Quote:** “{q.get('text','')}” — {q.get('attribution','')}")
            cits = slide.get("citations") or []
            if cits:
                lines.append("**Citations:**")
                for c in cits[:5]:
                    lines.append(f"  - {c.get('title','?')} — {c.get('url','')}")
            audit = dq["per_slide"][i]
            lines.append(f"_Audit: headline={audit['headline_words']}w · "
                         f"bullets={audit['n_bullets']} (max {audit['max_bullet_words']}w) · "
                         f"citations={audit['n_citations']} · "
                         f"issues={audit['issues'] or 'none'}_\n")

        # Event log (compact)
        lines.append("### Event Log\n")
        lines.append("| Time (s) | Stage | Summary |")
        lines.append("|---:|---|---|")
        if r.get("events"):
            t0 = r["events"][0]["t_perf"]
            for ev in r["events"]:
                summary = json.dumps(ev["payload"], default=str)[:140]
                lines.append(f"| {round(ev['t_perf'] - t0, 2)} | `{ev['stage']}` | {summary} |")
        lines.append("")

    # Final analysis
    lines.append("## Cross-Scenario Analysis\n")
    if n_pass:
        passing = [r for r in records if r["status"] == "PASS"]
        std = [r for r in passing if r["mode"] == "standard"]
        prm = [r for r in passing if r["mode"] == "premium"]
        if std:
            lines.append(f"- **Standard mode** avg time: "
                         f"{int(sum(r['duration_ms_total'] for r in std)/len(std))} ms · "
                         f"avg score: {round(sum(r['critic']['overall'] for r in std)/len(std), 2)}/10")
        if prm:
            lines.append(f"- **Premium mode** avg time: "
                         f"{int(sum(r['duration_ms_total'] for r in prm)/len(prm))} ms · "
                         f"avg score: {round(sum(r['critic']['overall'] for r in prm)/len(prm), 2)}/10")
        # Research depth differences
        if std and prm:
            avg_std_cit = sum(r["research"]["n_citations"] + r["research"]["n_news"] for r in std) / len(std)
            avg_prm_cit = sum(r["research"]["n_citations"] + r["research"]["n_news"] for r in prm) / len(prm)
            lines.append(f"- **Research depth** — Standard avg {avg_std_cit:.1f} sources · "
                         f"Premium avg {avg_prm_cit:.1f} sources")

    lines.append("\n---\n_Report generated by `test_v4_deep.py`._\n")
    return "\n".join(lines)


# ── env summary helper ─────────────────────────────────────────────

def env_summary() -> dict[str, bool]:
    keys = [
        "TAVILY_API_KEY", "SERPER_API_KEY", "EXA_API_KEY", "JINA_API_KEY",
        "YOU_COM_API_KEY", "NEWSAPI_KEY", "NEWSDATA_API_KEY", "GUARDIAN_API_KEY",
        "REDDIT_USER_AGENT", "GITHUB_TOKEN", "FINNHUB_API_KEY",
        "GROQ_API_KEY", "DEEPSEEK_API_KEY", "AZURE_KIMI_API_KEY",
        "AZURE_GPT4O_MINI_API_KEY", "MONGODB_URI", "REDIS_HOST",
    ]
    return {k: bool(os.getenv(k)) for k in keys}


# ── main ────────────────────────────────────────────────────────────

async def main() -> None:
    print(f"\n{'#'*70}\n#  V4 DEEP TEST -- Standard + Premium Content Generation\n{'#'*70}")

    env = env_summary()
    print("\nEnvironment configured:")
    for k, v in env.items():
        print(f"  {'[OK]' if v else '[--]'}  {k}")

    print("\nConnecting to MongoDB…")
    try:
        await connect_db()
        db = get_db()
        await db.command("ping")
        print("  [OK] Mongo connected.")
    except Exception as e:
        print(f"  [FAIL] Mongo connect failed: {e}")
        # Pipeline can still run; learning store/research cache will degrade gracefully.

    pipeline = V4ContentPipeline()

    records: list[dict[str, Any]] = []
    md_path = HERE / "test_v4_deep_report.md"
    json_path = HERE / "test_v4_deep_raw.json"

    for scenario in SCENARIOS:
        rec = await run_scenario(pipeline, scenario)
        records.append(rec)
        # Incremental save after each scenario so a later hang doesn't lose data.
        try:
            md_path.write_text(render_markdown(records, env), encoding="utf-8")
            json_path.write_text(
                json.dumps(records, indent=2, default=str), encoding="utf-8",
            )
            print(f"  [SAVED] {md_path.name} + {json_path.name}", flush=True)
        except Exception as e:
            print(f"  [SAVE_FAIL] {e}", flush=True)
        # small breather between scenarios so rate limits don't bite
        await asyncio.sleep(1.5)

    try:
        await close_db()
    except Exception:
        pass

    # final write (already written incrementally, but ensure latest is on disk)
    md_path.write_text(render_markdown(records, env), encoding="utf-8")
    json_path.write_text(
        json.dumps(records, indent=2, default=str), encoding="utf-8",
    )

    print(f"\n{'='*70}")
    print(f"REPORT  → {md_path}")
    print(f"RAW     → {json_path}")
    n_pass = sum(1 for r in records if r["status"] == "PASS")
    print(f"RESULT  → {n_pass}/{len(records)} scenarios passed.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
