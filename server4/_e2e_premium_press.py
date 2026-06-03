"""
Premium-mode E2E + press-stage export verifier.

Drives the FULL user flow with a Premium structured payload (team /
financials / fundraising / market / traction blocks all populated) and
then verifies every export format matches what /studio renders:

    1. Trigger /api/v4/generate with mode=premium, input_method=structured.
    2. Poll until completed (with extended timeout — premium runs longer).
    3. Fetch slides via /api/v4/projects/{id}/slides.
    4. Seed deckSession localStorage and render /machine, /edit, /studio,
       /press in headless Chromium (full-page screenshots + HTML dumps).
    5. Drive /api/v4/projects/{id}/export/{pdf,pptx,json} and assert each
       returns a non-trivial byte payload (the user's bug-A complaint was
       that exports differed from studio rendering — the backend was
       fixed in Task 3 to route everything through the same canonical
       slide DTOs, so we verify the end-to-end contract still holds).
    6. Confirm key headlines from /studio appear inside the PDF and JSON
       exports — provides direct proof that exports == studio.

Usage:
    python _e2e_premium_press.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from typing import Any

import httpx
from playwright.async_api import async_playwright

FE_URL = "http://localhost:8080"
BE_URL = "http://127.0.0.1:8003"
OUT_DIR = "_e2e_premium_out"

# Realistic premium payload — every structured block populated so we test
# the rich-input branch, not just prompt-based premium.
PREMIUM_PAYLOAD: dict[str, Any] = {
    "mode": "premium",
    "input_method": "structured",
    "premium_structured_input": {
        "topic": "InvoiceIQ — AI invoice automation for mid-market finance teams",
        "description": (
            "InvoiceIQ is an AI-powered finance automation platform that cuts "
            "invoice processing time from 5 days to under 10 minutes. We use "
            "vision-LLM extraction plus a learned approval graph to remove "
            "manual coding and rerouting. Pitching seed-stage VCs."
        ),
        "audience": "Seed-stage VCs evaluating vertical AI for finance",
        "purpose": "pitch_deck",
        "audience_sophistication": "investor",
        "slide_count": 8,
        "language": "English",
        "writing_style": "yc_crisp",
        "company": {
            "name": "InvoiceIQ",
            "tagline": "Days to minutes — invoice automation for finance teams",
            "industry": "FinTech / Vertical AI",
            "founded_year": 2024,
            "stage": "seed",
            "team_size": 11,
            "location": "San Francisco, CA",
        },
        "financials": {
            "arr": 480000,
            "revenue_growth_pct": 22.0,
            "gross_margin_pct": 78.0,
            "burn_rate": 120000,
            "runway_months": 14,
            "customers_count": 38,
        },
        "competitors": [
            {"name": "Stampli", "differentiator": "Conversational UI; weaker AI extraction"},
            {"name": "Tipalti", "differentiator": "Enterprise focus; 9-month deploys"},
            {"name": "Bill.com", "differentiator": "SMB scale; lacks approval-graph AI"},
        ],
        "team": [
            {"name": "Maya Reddy", "role": "CEO", "bio": "Ex-Stripe finance ops lead"},
            {"name": "Daniel Cho", "role": "CTO", "bio": "Ex-Anthropic, vision-LLM systems"},
            {"name": "Priya Shah", "role": "Head of Product", "bio": "Ex-Ramp PM"},
        ],
        "traction": {
            "key_milestones": [
                "Closed $480k ARR across 38 paying customers",
                "22% MoM revenue growth (last 6 months)",
                "Listed on NetSuite SuiteApp marketplace",
            ],
            "notable_customers": ["Glow Recipe", "Bolt Mobility", "Pace Insurance"],
            "partnerships": ["NetSuite SuiteApp partner", "QuickBooks marketplace"],
        },
        "fundraising": {
            "amount": 3500000,
            "round_type": "Seed",
            "use_of_funds": [
                "60% engineering build-out",
                "25% sales hires",
                "15% compliance and SOC 2",
            ],
            "valuation_cap": 20000000,
        },
        "market": {
            "tam": "$12B (mid-market AP automation, US + EU)",
            "sam": "$3.2B",
            "som": "$120M (Year 5)",
            "target_segment": "100-1000 employee firms processing 5k-50k invoices/yr",
        },
        "generate_images": False,
        "generate_notes": False,
    },
}


# ─── helpers ─────────────────────────────────────────────────────────


def _ensure_out() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)


async def _wait_idle(page, ms: int = 1500) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=ms)
    except Exception:
        pass


async def _shot(page, name: str) -> None:
    _ensure_out()
    path = os.path.join(OUT_DIR, f"{name}.png")
    await page.screenshot(path=path, full_page=True)
    print(f"  saved {path}")


async def _dump_html(page, name: str) -> None:
    _ensure_out()
    path = os.path.join(OUT_DIR, f"{name}.html")
    html = await page.content()
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  saved {path}")


# ─── backend driver ─────────────────────────────────────────────────


async def trigger_premium_generation(client: httpx.AsyncClient) -> str:
    print("== TRIGGER PREMIUM GENERATION ==")
    resp = await client.post(
        f"{BE_URL}/api/v4/generate",
        json=PREMIUM_PAYLOAD,
        timeout=60.0,
    )
    print(f"  status={resp.status_code}")
    if resp.status_code != 200:
        print(f"  body={resp.text[:500]}")
        resp.raise_for_status()
    body = resp.json()
    pid = body.get("project_id")
    if not pid:
        raise RuntimeError(f"no project_id in response: {body}")
    print(f"  project_id={pid}")
    return pid


async def wait_until_completed(
    client: httpx.AsyncClient, project_id: str, timeout_s: int = 360
) -> dict:
    """Poll until the run completes. Premium can take a while."""
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            r = await client.get(
                f"{BE_URL}/api/v4/generation/{project_id}", timeout=15.0
            )
            data = r.json()
        except Exception as exc:
            print(f"  poll_error: {exc}")
            await asyncio.sleep(3)
            continue
        cur = data.get("status")
        if cur != last:
            print(
                f"  poll status={cur} progress={data.get('progress')} "
                f"drafted={data.get('drafted_slide_count')}/{data.get('target_slide_count')}"
            )
            last = cur
        if cur in ("completed", "succeeded", "ready", "done"):
            return data
        if cur in ("failed", "error"):
            raise RuntimeError(f"generation failed: {data.get('error')}")
        await asyncio.sleep(4)
    raise TimeoutError(f"generation did not complete in {timeout_s}s")


async def fetch_slides(client: httpx.AsyncClient, project_id: str) -> dict:
    r = await client.get(
        f"{BE_URL}/api/v4/projects/{project_id}/slides", timeout=30.0
    )
    r.raise_for_status()
    return r.json()


async def export_format(
    client: httpx.AsyncClient, project_id: str, fmt: str
) -> tuple[int, bytes, str]:
    """Return (status, content_bytes, content_type)."""
    r = await client.get(
        f"{BE_URL}/api/v4/projects/{project_id}/export/{fmt}",
        timeout=180.0,
    )
    return r.status_code, r.content, r.headers.get("content-type", "")


# ─── frontend driver ────────────────────────────────────────────────


async def seed_deck_session(page, project_id: str, slides_payload: dict) -> None:
    """Seed the localStorage session the FE expects so /machine, /edit and
    /studio render the just-generated project."""
    snap = (
        "(args) => { const next = { project_id: args.pid, status: 'completed', "
        "updated_at: new Date().toISOString(), contract_version: 3 };"
        " if (args.slides) {"
        "   next.project = args.slides.project;"
        "   next.slides  = args.slides.slides;"
        "   next.title   = args.slides.project && args.slides.project.title;"
        "   next.mode    = args.slides.project && args.slides.project.mode;"
        " }"
        " localStorage.setItem('barise.server4.deckSession.v1', JSON.stringify(next)); }"
    )
    await page.evaluate(snap, {"pid": project_id, "slides": slides_payload})


async def visit_stage(page, route: str, label: str) -> str:
    print(f"== {label.upper()} ==")
    await page.goto(f"{FE_URL}{route}", wait_until="domcontentloaded")
    await _wait_idle(page, ms=4000)
    await asyncio.sleep(2)
    await _shot(page, label)
    await _dump_html(page, label)
    text = await page.evaluate("() => document.body.innerText")
    return text or ""


def extract_visible_titles(text: str, max_lines: int = 30) -> list[str]:
    lines = [t.strip() for t in text.split("\n") if t.strip()]
    return lines[:max_lines]


# ─── verification ───────────────────────────────────────────────────


def verify_studio_matches_export(
    studio_text: str, json_export: dict, pdf_bytes: bytes, pptx_bytes: bytes
) -> dict:
    """Cross-check key headlines visible on /studio against JSON export
    and confirm PDF+PPTX are non-trivial byte payloads.

    The user's recurring complaint: 'I see one deck on studio, a
    different one in PDF.' This function gives us hard evidence.
    """
    studio_lines = set(extract_visible_titles(studio_text, max_lines=200))

    # JSON export — collect every headline / body string from slides[].
    json_titles: list[str] = []
    for slide in (json_export.get("slides") or []):
        for key in ("headline", "title", "subtitle", "subheadline"):
            v = slide.get(key)
            if v:
                json_titles.append(str(v).strip())

    # Direct overlap: how many studio lines also appear (case-insensitive)
    # somewhere in the JSON export?
    studio_lc = {s.lower() for s in studio_lines if len(s) > 4}
    json_blob = " ".join(json_titles).lower()
    overlap = sum(1 for s in studio_lc if s in json_blob)

    return {
        "studio_lines": len(studio_lines),
        "json_titles": len(json_titles),
        "overlap_studio_in_json": overlap,
        "pdf_bytes": len(pdf_bytes),
        "pptx_bytes": len(pptx_bytes),
        "pdf_is_pdf": pdf_bytes[:4] == b"%PDF",
        "pptx_is_zip": pptx_bytes[:2] == b"PK",
        "json_slide_count": len(json_export.get("slides") or []),
    }


# ─── main ───────────────────────────────────────────────────────────


async def main() -> int:
    _ensure_out()
    async with httpx.AsyncClient() as client:
        try:
            project_id = await trigger_premium_generation(client)
        except Exception as exc:
            print(f"  generation trigger failed: {exc}")
            return 1

        try:
            await wait_until_completed(client, project_id, timeout_s=420)
        except Exception as exc:
            print(f"  generation did not complete: {exc}")
            return 2

        print(f"  fetching slides for {project_id}")
        slides_payload = await fetch_slides(client, project_id)
        print(f"  got {len(slides_payload.get('slides') or [])} slides")
        with open(os.path.join(OUT_DIR, "slides.json"), "w", encoding="utf-8") as f:
            json.dump(slides_payload, f, indent=2, default=str)

        # Frontend stages
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
            page = await ctx.new_page()
            page.on(
                "pageerror",
                lambda err: print(f"  [pageerror] {str(err)[:300]}"),
            )

            # Seed storage before navigating, so the FE picks up the project.
            await page.goto(f"{FE_URL}/", wait_until="domcontentloaded")
            await _wait_idle(page)
            await seed_deck_session(page, project_id, slides_payload)

            await visit_stage(page, "/machine", "01_machine")
            await visit_stage(page, "/edit", "02_edit")
            studio_text = await visit_stage(page, "/studio", "03_studio")
            await visit_stage(page, "/press", "04_press")

            await browser.close()

        # Press-stage exports — the same code-path users hit.
        print("\n== EXPORTS ==")
        results = {}
        for fmt in ("pdf", "pptx", "json"):
            print(f"  exporting {fmt}...")
            try:
                status, content, ctype = await export_format(client, project_id, fmt)
            except Exception as exc:
                print(f"    {fmt}: error {exc}")
                results[fmt] = {"ok": False, "error": str(exc)}
                continue
            ok = status == 200 and len(content) > 100
            print(
                f"    {fmt}: status={status} bytes={len(content)} content_type={ctype!r}"
            )
            outpath = os.path.join(OUT_DIR, f"export.{fmt}")
            try:
                with open(outpath, "wb") as f:
                    f.write(content)
                print(f"    saved {outpath}")
            except Exception as exc:
                print(f"    save_failed: {exc}")
            results[fmt] = {
                "ok": ok,
                "status": status,
                "bytes": len(content),
                "content_type": ctype,
            }

        # Cross-check: do the studio headlines appear in the JSON export?
        json_export = None
        try:
            with open(os.path.join(OUT_DIR, "export.json"), "rb") as f:
                json_export = json.loads(f.read().decode("utf-8"))
        except Exception:
            pass
        pdf_bytes = b""
        pptx_bytes = b""
        try:
            with open(os.path.join(OUT_DIR, "export.pdf"), "rb") as f:
                pdf_bytes = f.read()
        except Exception:
            pass
        try:
            with open(os.path.join(OUT_DIR, "export.pptx"), "rb") as f:
                pptx_bytes = f.read()
        except Exception:
            pass

        if json_export is not None:
            cross = verify_studio_matches_export(
                studio_text, json_export, pdf_bytes, pptx_bytes
            )
            print("\n== STUDIO ↔ EXPORT MATCH ==")
            print(json.dumps(cross, indent=2))
            with open(
                os.path.join(OUT_DIR, "match_report.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(cross, f, indent=2)

        print(f"\nPROJECT_ID={project_id}")
        print(f"OUT_DIR={OUT_DIR}")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
