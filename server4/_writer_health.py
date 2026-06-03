"""Live writer health audit.

Triggers a real generation against the backend and reports:
  - Did writers fail or succeed for each slide?
  - Was actual LLM content produced, or fallback-skeleton text?

The previous turn confirmed every writer in standard mode was timing out
(``failed_calls: 6``) so the deck shipped with hardcoded fallback strings.
After the dead-model filter and chain reorder, this script is the proof
that the LLMs are actually responding.
"""

import json
import time
import requests


def main():
    payload = {
        "mode": "standard",
        "input_method": "prompt",
        "standard_input": {
            "prompt": (
                "AI invoice automation for mid-market finance teams. Pitch deck "
                "for an AI-powered finance automation platform that cuts invoice "
                "processing time from days to minutes. Target audience is "
                "seed-stage investors. Highlight problem, solution, market, "
                "traction, team, ask."
            ),
            "slide_count": 6,
            "purpose": "seed_round",
            "language": "English",
            "generate_images": False,
            "generate_notes": False,
        },
    }
    r = requests.post(
        "http://127.0.0.1:8003/api/v4/generate",
        json=payload,
        timeout=60,
    )
    body = r.json()
    project_id = body["project_id"]
    print(f"project_id={project_id}")

    # Poll
    deadline = time.monotonic() + 240
    last_status = None
    last_data = None
    while time.monotonic() < deadline:
        try:
            sr = requests.get(
                f"http://127.0.0.1:8003/api/v4/generation/{project_id}",
                timeout=15,
            )
            data = sr.json()
        except Exception as exc:
            print(f"  poll_failed: {exc}")
            time.sleep(3)
            continue
        cur = data.get("status")
        if cur != last_status:
            print(
                f"  status={cur} progress={data.get('progress')} "
                f"drafted={data.get('drafted_slide_count')}/{data.get('target_slide_count')}"
            )
            last_status = cur
            last_data = data
        if cur in ("completed", "succeeded", "ready", "done"):
            last_data = data
            break
        if cur in ("failed", "error"):
            print(f"  GENERATION FAILED: {data.get('error')}")
            return
        time.sleep(4)

    print()
    print("== TOKEN USAGE ==")
    if last_data:
        token_usage = last_data.get("token_usage") or {}
        print(json.dumps(token_usage, indent=2, default=str))

    # Pull the slides
    sr = requests.get(
        f"http://127.0.0.1:8003/api/v4/projects/{project_id}/slides",
        timeout=20,
    )
    slides_payload = sr.json()
    slides = slides_payload["slides"]
    print()
    print(f"== SLIDES ({len(slides)}) ==")
    fallback_phrases = [
        "Investor proof centers on proprietary data access",
        "Production deployments, revenue momentum, and gross margin",
        "Compounding loops are shown with operating data",
        "Market sizing stays sourced and traceable",
    ]
    fallback_hits = 0
    for s in slides:
        head = s.get("headline") or "<empty>"
        sub = (s.get("subheadline") or "").strip()
        body = (s.get("body") or "").strip()
        bullets = s.get("bullets") or []
        intent = s.get("intent")
        layout = s.get("layout")
        kit = (s.get("compiled_slide") or {}).get("kit_component")
        print(f"  [{s.get('index')}] intent={intent!r:<28} layout={layout!r:<14} kit={kit}")
        print(f"      headline:    {head}")
        if sub:
            print(f"      subheadline: {sub}")
            for phrase in fallback_phrases:
                if phrase in sub:
                    fallback_hits += 1
                    print(f"      [FALLBACK PHRASE DETECTED] '{phrase}'")
        if body:
            print(f"      body:        {body[:160]}")
        if bullets:
            print(f"      bullets:     {len(bullets)} items")
            for b in bullets[:4]:
                print(f"        - {b}")

    print()
    print(f"fallback-phrase hits: {fallback_hits}")
    print(f"PROJECT_ID={project_id}")


if __name__ == "__main__":
    main()
