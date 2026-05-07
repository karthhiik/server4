#!/usr/bin/env python3
"""Quick inspector for test_v4_live_local_raw.json — measures kit distribution
and structured-content coverage on FRESH live-LLM output using the current
slide_compiler."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
except Exception:
    pass

from app.services.v4.parallel_writer import GeneratedSlide  # noqa: E402
from app.services.v4.skeleton_planner import SkeletonPlanner  # noqa: E402
from app.services.v4.slide_compiler import compile_slides  # noqa: E402

RAW = HERE / "test_v4_live_local_raw.json"


def _slide_from_dict(d: dict) -> GeneratedSlide:
    raw_layout = str(d.get("layout") or "auto")
    try:
        canon_layout = SkeletonPlanner._normalize_layout(raw_layout)  # type: ignore[attr-defined]
    except Exception:
        canon_layout = raw_layout
    return GeneratedSlide(
        index=int(d.get("index", 0)),
        intent=str(d.get("intent") or ""),
        layout=canon_layout,
        headline=str(d.get("headline") or ""),
        subheadline=d.get("subheadline"),
        bullets=list(d.get("bullets") or []),
        body=d.get("body"),
        stat_blocks=list(d.get("stat_blocks") or []),
        quote=d.get("quote"),
        chart=d.get("chart"),
        table=d.get("table"),
        timeline=d.get("timeline"),
        comparison=d.get("comparison"),
        diagram=d.get("diagram"),
        image_prompt=d.get("image_prompt"),
        speaker_notes=d.get("speaker_notes") or "",
        citations=list(d.get("citations") or []),
        raw=d.get("raw") or {},
        render_decision=d.get("render_decision"),
        team_members=list(d.get("team_members") or []),
        company_icon_url=d.get("company_icon_url"),
        rationale=str(d.get("rationale") or ""),
        purpose=str(d.get("purpose") or ""),
    )


def main() -> int:
    if not RAW.exists():
        print(f"missing: {RAW}")
        return 1
    records = json.loads(RAW.read_text(encoding="utf-8"))
    overall: Counter[str] = Counter()
    total_slides = 0
    structured_total = Counter({"chart": 0, "stats": 0, "timeline": 0, "comparison": 0, "diagram": 0, "quote": 0, "team": 0, "bullets": 0, "images": 0})
    print("=" * 78)
    print("LIVE AUDIT (fresh Azure LLM output, post planner-fix)")
    print("=" * 78)
    for r in records:
        if r.get("status") != "PASS":
            print(f"\n[{r.get('id')}] SKIPPED ({r.get('status')}): {r.get('error','')[:100]}")
            continue
        slides = [_slide_from_dict(sd) for sd in r.get("slides") or []]
        compiled = compile_slides(slides=slides)
        kits: Counter[str] = Counter()
        structured = Counter({"chart": 0, "stats": 0, "timeline": 0, "comparison": 0, "diagram": 0, "quote": 0, "team": 0, "bullets": 0, "images": 0})
        for sl, cs in zip(slides, compiled):
            kc = cs.get("kit_component", "?") if isinstance(cs, dict) else getattr(cs, "kit_component", "?")
            kits[kc] += 1
            if sl.chart: structured["chart"] += 1
            if sl.stat_blocks: structured["stats"] += 1
            if sl.timeline: structured["timeline"] += 1
            if sl.comparison: structured["comparison"] += 1
            if sl.diagram: structured["diagram"] += 1
            if sl.quote: structured["quote"] += 1
            if sl.team_members: structured["team"] += 1
            if sl.bullets: structured["bullets"] += 1
            if sl.image_prompt: structured["images"] += 1
        n = len(slides)
        total_slides += n
        overall.update(kits)
        for k, v in structured.items():
            structured_total[k] += v
        dom_kit, dom_cnt = kits.most_common(1)[0] if kits else ("?", 0)
        dom_pct = round(100.0 * dom_cnt / max(1, n), 1)
        diversity = round(len(kits) / 10.0, 2)
        stamped = dom_pct >= 75.0
        print(f"\n[{r['id']}] {r['label']}  ({n} slides)")
        print(f"   kit distribution: {dict(kits)}")
        print(f"   raw layouts: {r.get('layouts')}")
        print(f"   diversity: {diversity}   dominant: {dom_kit}={dom_pct}%   template_stamped={stamped}")
        print(f"   structured: {dict(structured)}")
    print("\n" + "=" * 78)
    print("AGGREGATE")
    print(f"   total slides:    {total_slides}")
    print(f"   kit distribution: {dict(overall)}")
    print(f"   kit coverage:    {len(overall)}/10")
    print(f"   structured total: {dict(structured_total)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
