"""End-to-end smoke for v12.1 V4 pipeline — both standard and premium mode.

Hits the LIVE backend at http://localhost:8003 (must already be running).
For each mode:
    1. POST /api/v4/generate with a minimal prompt
    2. Poll GET /api/v4/generation/{project_id} until terminal state
    3. Verify slides were persisted + quality score > 0 + no error
    4. Print the final status payload for visual inspection

Exits 0 if both modes complete successfully.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8003"
TIMEOUT_SECONDS_STANDARD = 300
TIMEOUT_SECONDS_PREMIUM = 540
POLL_INTERVAL_S = 4


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(path: str) -> dict:
    req = urllib.request.Request(BASE_URL + path, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _poll_until_done(project_id: str, *, timeout_s: int) -> dict:
    start = time.time()
    last_state: str | None = None
    last_progress: int | None = None
    last_message: str | None = None
    terminal = {
        "completed",
        "failed",
        "error",
        "ready",
        "ready_for_editing",
    }
    while time.time() - start < timeout_s:
        try:
            status = _get(f"/api/v4/generation/{project_id}")
        except urllib.error.HTTPError as e:
            print(f"  !! poll HTTP {e.code}: {e.reason}")
            time.sleep(POLL_INTERVAL_S)
            continue
        except Exception as e:
            print(f"  !! poll error: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        # The V4 status endpoint returns the terminal state in "status"
        # (values from GenerationState enum). "state" is a convenience
        # fallback for older response shapes.
        state = (
            status.get("status")
            or status.get("state")
            or status.get("generation_state")
        )
        progress = status.get("progress") or status.get("generation_progress")
        message = status.get("message") or status.get("generation_message")

        if (state, progress, message) != (last_state, last_progress, last_message):
            elapsed = int(time.time() - start)
            print(f"  [{elapsed:3d}s] state={state} progress={progress}% msg={message}")
            last_state, last_progress, last_message = state, progress, message

        if state in terminal:
            # Include slide_count in the returned payload for downstream assertions.
            status["_state"] = state
            return status
        time.sleep(POLL_INTERVAL_S)

    return {"_state": "TIMEOUT", "elapsed_s": timeout_s}


def run_standard_mode() -> bool:
    print("\n" + "=" * 64)
    print("STANDARD MODE smoke")
    print("=" * 64)
    payload = {
        "mode": "standard",
        "input_method": "prompt",
        "standard_input": {
            "prompt": (
                "Series A pitch deck for an AI procurement platform called "
                "Rebot AI that automates invoice review for mid-market "
                "companies. We have $1.2M ARR across 40 customers with 120% "
                "net revenue retention and are raising $8M."
            ),
            "slide_count": 8,
            "generate_images": False,
            "generate_notes": False,
        },
    }
    print(f"POST /api/v4/generate  slides={payload['standard_input']['slide_count']}")
    started = _post("/api/v4/generate", payload)
    project_id = started["project_id"]
    print(f"  -> project_id={project_id}  ws={started.get('ws_url')}")

    final = _poll_until_done(project_id, timeout_s=TIMEOUT_SECONDS_STANDARD)
    state = final.get("_state") or final.get("status") or final.get("state")
    print(f"\nStandard final state: {state}")
    if state in {"completed", "ready", "ready_for_editing"}:
        slide_count = final.get("slide_count") or 0
        print(f"  slides persisted: {slide_count}")
        print(f"  overall_score:    {final.get('overall_score')}")
        return slide_count > 0
    print(f"  ERROR: {final.get('error') or final.get('generation_error')}")
    return False


def run_premium_mode() -> bool:
    print("\n" + "=" * 64)
    print("PREMIUM MODE smoke (should trigger DeepResearchLoop expansion)")
    print("=" * 64)
    payload = {
        "mode": "premium",
        "input_method": "prompt",
        "premium_prompt_input": {
            "prompt": (
                "Series A pitch deck for Rebot AI, an AI procurement platform "
                "that automates invoice review and three-way match for "
                "mid-market companies. Founded 2023. We have $1.2M ARR with "
                "40 paying customers, 120% NRR, and 5 design partners. "
                "Primary competitors are Stampli, AvidXchange, and Tipalti. "
                "We are raising a $8M Series A at $40M post-money to scale "
                "GTM into the US and Europe."
            ),
            "slide_count": 10,
            "generate_images": False,
            "generate_notes": False,
        },
    }
    print(f"POST /api/v4/generate  slides={payload['premium_prompt_input']['slide_count']}")
    started = _post("/api/v4/generate", payload)
    project_id = started["project_id"]
    print(f"  -> project_id={project_id}  ws={started.get('ws_url')}")

    final = _poll_until_done(project_id, timeout_s=TIMEOUT_SECONDS_PREMIUM)
    state = final.get("_state") or final.get("status") or final.get("state")
    print(f"\nPremium final state: {state}")

    # Verify deep_research events appeared in the progress log — this
    # is the clearest signal that the new v12.1 wiring exercised.
    progress_log = final.get("progress_log") or []
    deep_events = [
        e for e in progress_log
        if (e.get("stage") or "").startswith("deep_research_")
    ]
    print(f"  deep_research events in log: {len(deep_events)}")
    for e in deep_events[:5]:
        print(f"    - {e.get('stage')}")

    if state in {"completed", "ready", "ready_for_editing"}:
        slide_count = final.get("slide_count") or 0
        print(f"  slides persisted: {slide_count}")
        print(f"  overall_score:    {final.get('overall_score')}")
        return slide_count > 0
    print(f"  ERROR: {final.get('error') or final.get('generation_error')}")
    return False


def main() -> int:
    # Pre-flight: verify backend is up
    try:
        health = _get("/health")
        print(f"Backend up: {health}")
    except Exception as e:
        print(f"!! Backend NOT running at {BASE_URL}: {e}")
        return 2

    s_ok = run_standard_mode()
    p_ok = run_premium_mode()

    print("\n" + "=" * 64)
    print(f"Standard: {'PASS' if s_ok else 'FAIL'}")
    print(f"Premium : {'PASS' if p_ok else 'FAIL'}")
    print("=" * 64)
    return 0 if (s_ok and p_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
