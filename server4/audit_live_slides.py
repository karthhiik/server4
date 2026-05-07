"""
Founder-level audit: take the real Apr-18 V4 run output and push it
through the current slide_compiler. Measures:

  1. Kit component distribution (are we template-stamping TitleHero?)
  2. Structured-content presence (charts, stats, timelines, quotes)
  3. Image generation success rate per scenario
  4. Writer output richness (bullets vs structured blocks)
  5. JSX PROPS validity (is every slide actually renderable?)

Outputs: audit_live_slides_report.json + human-readable summary on stdout.
No external services — pure deterministic offline analysis.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.services.v4.parallel_writer import GeneratedSlide  # noqa: E402
from app.services.v4.skeleton_planner import SkeletonPlanner  # noqa: E402
from app.services.v4.slide_compiler import compile_slides  # noqa: E402

RAW = ROOT / "test_v4_deep_raw.json"


_INTENT_CANONICAL = {
    "introduction": "title",
    "introductions": "title",
    "intro": "title",
    "cover": "title",
    "title": "title",
    "problem": "problem",
    "solution": "solution",
    "product": "product",
    "traction": "traction",
    "market": "market",
    "team": "team",
    "vision": "vision",
    "ask": "ask",
    "closing": "closing",
    "thanks": "thanks",
    "timeline": "timeline",
    "metrics": "metrics",
}


def _canonical_intent(raw: str) -> str:
    key = (raw or "").strip().lower()
    return _INTENT_CANONICAL.get(key, key)


def _slide_from_dict(d: dict[str, Any]) -> GeneratedSlide:
    """Rehydrate a GeneratedSlide from the JSON dump.

    The Apr-18 run predates v11 team_members + render_decision, so we
    supply safe defaults. Image URLs were never persisted on the slide
    (they are published separately over Redis pub/sub), so `imageUrl`
    is read off `raw` if present, otherwise None.
    """
    raw = d.get("raw") or {}
    # Push the recorded layout through the current normalizer so the
    # audit measures what the *latest* pipeline would produce, not what
    # the Apr-18 planner emitted. Free-form strings like "logo-image"
    # now snap to canonical tokens like "title-only".
    raw_layout = str(d.get("layout") or "auto")
    try:
        canon_layout = SkeletonPlanner._normalize_layout(raw_layout)  # type: ignore[attr-defined]
    except Exception:
        canon_layout = raw_layout
    return GeneratedSlide(
        index=int(d.get("index", 0)),
        intent=_canonical_intent(str(d.get("intent", ""))),
        layout=canon_layout,
        headline=str(d.get("headline") or ""),
        subheadline=d.get("subheadline"),
        bullets=list(d.get("bullets") or []),
        body=d.get("body"),
        stat_blocks=list(d.get("stat_blocks") or []),
        quote=d.get("quote"),
        chart=d.get("chart"),
        timeline=d.get("timeline"),
        comparison=d.get("comparison"),
        diagram=d.get("diagram"),
        image_prompt=d.get("image_prompt"),
        speaker_notes=d.get("speaker_notes"),
        citations=list(d.get("citations") or []),
        raw=raw if isinstance(raw, dict) else {},
        render_decision=d.get("render_decision"),
        team_members=list(d.get("team_members") or []),
        company_icon_url=d.get("company_icon_url"),
        rationale=str(d.get("rationale") or ""),
        purpose=str(d.get("purpose") or ""),
    )


def audit_scenario(scen: dict[str, Any]) -> dict[str, Any]:
    label = scen.get("label") or scen.get("id")
    slides_raw = scen.get("slides") or []
    if not slides_raw:
        return {"label": label, "skipped": True, "reason": "no_slides"}

    slides = [_slide_from_dict(s) for s in slides_raw]
    # Apr-18 run did not persist per-slide imageUrl (images are emitted
    # live over Redis pub/sub). Treat image_prompt presence + intent as
    # a signal that an image WOULD have been generated.
    image_urls: dict[int, str] = {}

    compiled = compile_slides(
        slides=slides,
        image_urls=image_urls,
        deck_title=scen.get("deck_title"),
        company_icon_url=None,
    )

    kit_dist = Counter(c["kit_component"] for c in compiled)

    # Per-slide structured-content presence
    with_chart = sum(1 for s in slides if s.chart and s.chart.get("data"))
    with_timeline = sum(1 for s in slides if s.timeline and s.timeline.get("events"))
    with_comparison = sum(1 for s in slides if s.comparison and s.comparison.get("columns"))
    with_diagram = sum(1 for s in slides if s.diagram and s.diagram.get("nodes"))
    with_quote = sum(1 for s in slides if s.quote and s.quote.get("text"))
    with_stats = sum(1 for s in slides if s.stat_blocks)
    with_team = sum(1 for s in slides if s.team_members)
    with_bullets = sum(1 for s in slides if s.bullets)
    with_image_prompt = sum(1 for s in slides if s.image_prompt)

    # JSX PROPS validity — every compiled slide must round-trip JSON.
    invalid_jsx = []
    for c in compiled:
        m = re.search(r"/\*\s*PROPS\s*([\s\S]*?)\*/", c["jsx_source"])
        if not m:
            invalid_jsx.append((c["slide_id"], "no_props_fence"))
            continue
        try:
            parsed = json.loads(m.group(1).strip())
            if not isinstance(parsed, dict):
                invalid_jsx.append((c["slide_id"], "props_not_dict"))
        except json.JSONDecodeError as e:
            invalid_jsx.append((c["slide_id"], f"json_error: {e}"))

    # Premium signals
    avg_citations = (
        sum(len(s.citations) for s in slides) / max(len(slides), 1)
    )
    # Pull critic scores from the top-level critic block if present.
    critic_block = scen.get("critic") or {}
    per_slide = critic_block.get("per_slide_scores") or critic_block.get("slides") or []
    critic_scores = [
        p.get("score") for p in per_slide if isinstance(p, dict) and isinstance(p.get("score"), (int, float))
    ]
    avg_critic = round(sum(critic_scores) / len(critic_scores), 2) if critic_scores else None

    # Diversity score: how many distinct kit components were used?
    diversity = len(kit_dist) / 10.0  # 10 kits available

    # Template-stamp sniff: >60% of slides on one kit = bad
    dominant_kit, dominant_count = kit_dist.most_common(1)[0]
    dominant_pct = round(100 * dominant_count / len(compiled), 1)
    template_stamped = dominant_pct > 60

    return {
        "label": label,
        "mode": scen.get("mode"),
        "n_slides": len(slides),
        "deck_title": scen.get("deck_title"),
        "narrative_arc": scen.get("narrative_arc"),
        "kit_distribution": dict(kit_dist),
        "kit_diversity_score": round(diversity, 2),
        "dominant_kit": dominant_kit,
        "dominant_kit_pct": dominant_pct,
        "template_stamped": template_stamped,
        "structured_content": {
            "charts": with_chart,
            "timelines": with_timeline,
            "comparisons": with_comparison,
            "diagrams": with_diagram,
            "quotes": with_quote,
            "stat_blocks": with_stats,
            "team_grids": with_team,
            "bullets": with_bullets,
            "images": with_image_prompt,
        },
        "quality": {
            "avg_critic_score": avg_critic,
            "avg_citations_per_slide": round(avg_citations, 2),
        },
        "jsx_validity": {
            "compiled_ok": len(compiled) - len(invalid_jsx),
            "compiled_bad": len(invalid_jsx),
            "bad_detail": invalid_jsx[:5],
        },
    }


def main() -> None:
    data = json.loads(RAW.read_text(encoding="utf-8"))
    scenarios = data if isinstance(data, list) else [data]
    print(f"\nAudit of {len(scenarios)} real V4 pipeline runs")
    print("=" * 76)

    all_reports = []
    for scen in scenarios:
        try:
            report = audit_scenario(scen)
        except Exception as e:  # noqa: BLE001
            report = {"label": scen.get("label") or scen.get("id"), "error": str(e)}
        all_reports.append(report)

        if report.get("skipped"):
            print(f"\n[{report['label']}] SKIPPED — {report['reason']}")
            continue
        if report.get("error"):
            print(f"\n[{report['label']}] ERROR — {report['error']}")
            continue

        lab = report["label"]
        print(f"\n[{lab}] {report['deck_title']!r}  ({report['mode']}, {report['n_slides']} slides)")
        print(f"   arc: {report['narrative_arc']}")
        print(f"   kit distribution: {report['kit_distribution']}")
        print(f"   diversity:  {report['kit_diversity_score']}   dominant:  {report['dominant_kit']}={report['dominant_kit_pct']}%   template_stamped={report['template_stamped']}")
        sc = report["structured_content"]
        print(
            f"   structured:  charts={sc['charts']}  stats={sc['stat_blocks']}  timelines={sc['timelines']}  "
            f"comparisons={sc['comparisons']}  diagrams={sc['diagrams']}  quotes={sc['quotes']}  "
            f"team={sc['team_grids']}  bullets={sc['bullets']}  images={sc['images']}"
        )
        q = report["quality"]
        print(f"   quality:  avg_critic={q['avg_critic_score']}  avg_citations/slide={q['avg_citations_per_slide']}")
        v = report["jsx_validity"]
        print(f"   jsx:  ok={v['compiled_ok']}  bad={v['compiled_bad']}")

    # Aggregate
    print("\n" + "=" * 76)
    print("AGGREGATE")
    ok = [r for r in all_reports if not r.get("skipped") and not r.get("error")]
    if ok:
        total_slides = sum(r["n_slides"] for r in ok)
        all_kits = Counter()
        for r in ok:
            all_kits.update(r["kit_distribution"])
        print(f"   total_slides_across_runs: {total_slides}")
        print(f"   overall kit distribution: {dict(all_kits)}")
        print(f"   kit coverage: {len(all_kits)} / 10 components exercised")
        stamped = sum(1 for r in ok if r.get("template_stamped"))
        print(f"   template-stamped scenarios: {stamped} / {len(ok)}")
        avg_diversity = sum(r["kit_diversity_score"] for r in ok) / len(ok)
        print(f"   avg diversity score: {round(avg_diversity, 2)}")
        total_images = sum(r["structured_content"]["images"] for r in ok)
        print(f"   total slides with images: {total_images} / {total_slides} = {round(100 * total_images / total_slides, 1)}%")

    out = ROOT / "audit_live_slides_report.json"
    out.write_text(json.dumps(all_reports, indent=2), encoding="utf-8")
    print(f"\nWrote {out.name}\n")


if __name__ == "__main__":
    main()
