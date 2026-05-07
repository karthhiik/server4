#!/usr/bin/env python3
"""Focused live local runner for validating the planner layout-normalization fix.

Runs only the two previously-template-stamped Standard scenarios (STD-1 and
STD-3) against the real pipeline. Emits a small JSON report we can feed back
into audit_live_slides.py for kit distribution / diversity measurement.

Why just these two: premium scenarios already showed healthy diversity (0.4-0.5)
pre-fix. The gain we need to prove is on Standard mode, where the writer was
receiving free-form layout strings and defaulting to bullet walls.

Run:
    cd server4 && python test_v4_live_local.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
except Exception:
    pass

from app.database import close_db, connect_db, get_db  # noqa: E402
from app.services.v4 import V4ContentPipeline  # noqa: E402


SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "STD-1",
        "label": "Standard / clear B2B SaaS pitch (Northwind AI)",
        "mode": "standard",
        "user_query": (
            "Create a 10-slide pitch deck for Northwind AI, a B2B SaaS that uses "
            "agentic LLM workflows to automate enterprise procurement. Target "
            "audience is seed-stage VCs. Series-Seed raise of $3M."
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
    },
    {
        "id": "STD-3",
        "label": "Standard / minimal one-word seed (fintech)",
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
    },
    {
        "id": "STD-4",
        "label": "Standard / enterprise quarterly business review",
        "mode": "standard",
        "user_query": (
            "Q3 2026 Quarterly Business Review for Acme Cloud. Cover revenue "
            "performance vs plan, customer retention metrics, top three "
            "operational risks, and Q4 roadmap. Audience: executive "
            "leadership team."
        ),
        "analysis": {
            "purpose": "business_review",
            "audience": "executive leadership",
            "industry": "enterprise SaaS / cloud infrastructure",
            "company": "Acme Cloud",
            "tone": "data-led, candid",
            "suggested_slide_types": [],
        },
        "purpose": "business_review",
        "industry": "enterprise SaaS",
        "company_name": "Acme Cloud",
        "user_slide_types": None,
        "target_slide_count": 10,
    },
    {
        "id": "STD-5",
        "label": "Standard / academic research presentation",
        "mode": "standard",
        "user_query": (
            "Research presentation summarizing findings from a meta-analysis "
            "of 42 randomized controlled trials on GLP-1 receptor agonists "
            "for type 2 diabetes management. Cover methodology, primary "
            "outcomes, subgroup analyses, limitations, and clinical "
            "implications. Audience: medical conference attendees."
        ),
        "analysis": {
            "purpose": "educational",
            "audience": "clinical researchers",
            "industry": "healthcare / endocrinology",
            "tone": "rigorous, evidence-based",
            "suggested_slide_types": [],
        },
        "purpose": "educational",
        "industry": "healthcare",
        "company_name": None,
        "user_slide_types": None,
        "target_slide_count": 8,
    },
    {
        "id": "STD-6",
        "label": "Standard / marketing one-pager (concise)",
        "mode": "standard",
        "user_query": (
            "Five-slide product overview for Trailhead — a backcountry "
            "navigation app for hikers. Slides: hook, key features, social "
            "proof, pricing, CTA. Audience: outdoor enthusiasts."
        ),
        "analysis": {
            "purpose": "sales_pitch",
            "audience": "outdoor enthusiasts",
            "industry": "consumer mobile / outdoor",
            "company": "Trailhead",
            "tone": "energetic, accessible",
            "suggested_slide_types": [],
        },
        "purpose": "sales_pitch",
        "industry": "consumer mobile",
        "company_name": "Trailhead",
        "user_slide_types": None,
        "target_slide_count": 5,
    },
    {
        "id": "STD-7",
        "label": "Standard / non-English (Spanish) prompt",
        "mode": "standard",
        "user_query": (
            "Presentación de seis diapositivas para Lumina Energía, una "
            "startup que ofrece paneles solares por suscripción a hogares "
            "en España. Incluir problema, solución, mercado, modelo de "
            "negocio, tracción y equipo. Audiencia: inversores ángel."
        ),
        "analysis": {
            "purpose": "investor_pitch",
            "audience": "inversores ángel",
            "industry": "energía solar / suscripción",
            "company": "Lumina Energía",
            "tone": "confiado, data-driven",
            "suggested_slide_types": [],
        },
        "purpose": "investor_pitch",
        "industry": "renewable energy",
        "company_name": "Lumina Energía",
        "user_slide_types": None,
        "target_slide_count": 6,
    },
    {
        "id": "STD-8",
        "label": "Standard / long-form paste (multi-paragraph context)",
        "mode": "standard",
        "user_query": (
            "Build a deck for Northbeam Robotics. We design and manufacture "
            "autonomous mobile robots for warehouse fulfillment. Founded in "
            "2023, we have shipped 280 units to 14 enterprise customers "
            "including two Fortune 500 logistics companies. ARR is $4.2M "
            "growing 18% month over month. The warehouse automation market "
            "is projected to reach $51B by 2030 (CAGR 14%). Our key "
            "differentiation is a swarm-coordination algorithm that lets up "
            "to 200 robots collaborate without central scheduling, cutting "
            "deployment time from weeks to days. We compete with Locus "
            "Robotics and 6 River Systems but win on deployment speed and "
            "total cost of ownership. We are raising a $15M Series A led "
            "by tier-1 deep-tech investors. Use of funds: 40% R&D for "
            "outdoor variant, 35% sales expansion to EMEA, 25% "
            "manufacturing scale-up. Founders: Priya Shah (CEO, ex-Boston "
            "Dynamics), Marcus Lee (CTO, ex-Amazon Robotics), Elena "
            "Volkov (VP Eng, ex-Locus). Generate a 10-slide pitch deck."
        ),
        "analysis": {
            "purpose": "investor_pitch",
            "audience": "Series-A deep-tech VCs",
            "industry": "robotics / warehouse automation",
            "company": "Northbeam Robotics",
            "tone": "confident, technical, data-rich",
            "suggested_slide_types": [],
        },
        "purpose": "investor_pitch",
        "industry": "robotics",
        "company_name": "Northbeam Robotics",
        "user_slide_types": None,
        "target_slide_count": 10,
    },
]


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


async def run_one(pipeline: V4ContentPipeline, s: dict[str, Any]) -> dict[str, Any]:
    print(f"\n{'='*70}\n▶ {s['id']} — {s['label']}\n{'='*70}", flush=True)
    t0 = time.time()
    try:
        result = await pipeline.generate(
            project_id=f"live-local-{s['id']}",
            user_id="live-local-test",
            user_query=s["user_query"],
            analysis=s["analysis"],
            mode=s["mode"],
            target_slide_count=s["target_slide_count"],
            user_slide_types=s["user_slide_types"],
            company_name=s["company_name"],
            industry=s["industry"],
            purpose=s["purpose"],
        )
        elapsed = round(time.time() - t0, 2)
        slides = getattr(result, "slides", []) or []
        layouts = [getattr(sl, "layout", "") for sl in slides]
        intents = [getattr(sl, "intent", "") for sl in slides]
        print(f"  OK in {elapsed}s — {len(slides)} slides", flush=True)
        print(f"  layouts: {layouts}", flush=True)
        print(f"  intents: {intents}", flush=True)
        return {
            "id": s["id"],
            "label": s["label"],
            "status": "PASS",
            "elapsed_s": elapsed,
            "slide_count": len(slides),
            "layouts": layouts,
            "intents": intents,
            "slides": [_to_jsonable(sl) for sl in slides],
        }
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        tb = traceback.format_exc()
        print(f"  FAIL in {elapsed}s — {e}\n{tb}", flush=True)
        return {
            "id": s["id"],
            "label": s["label"],
            "status": "FAIL",
            "elapsed_s": elapsed,
            "error": str(e),
            "traceback": tb,
        }


async def main() -> None:
    print("Connecting to MongoDB…", flush=True)
    try:
        await connect_db()
        db = get_db()
        await db.command("ping")
        print("  [OK] Mongo connected.", flush=True)
    except Exception as e:
        print(f"  [WARN] Mongo connect failed: {e} — running anyway.", flush=True)

    pipeline = V4ContentPipeline()
    out_path = HERE / "test_v4_live_local_raw.json"
    records: list[dict[str, Any]] = []

    for scen in SCENARIOS:
        rec = await run_one(pipeline, scen)
        records.append(rec)
        # incremental save
        out_path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
        print(f"  [SAVED] {out_path.name}", flush=True)
        await asyncio.sleep(1.0)

    try:
        await close_db()
    except Exception:
        pass

    # Summary
    print(f"\n{'#'*70}\nSUMMARY\n{'#'*70}", flush=True)
    for r in records:
        if r["status"] == "PASS":
            print(f"  [PASS] {r['id']} {r['elapsed_s']}s  slides={r['slide_count']}  layouts={r['layouts']}")
        else:
            print(f"  [FAIL] {r['id']} {r['elapsed_s']}s  err={r.get('error','')[:120]}")
    print(f"\nRaw: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
