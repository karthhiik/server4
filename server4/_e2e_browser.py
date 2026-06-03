"""
Drive the editorial frontend through brief -> machine -> edit -> studio -> press
with a real backend generation. Capture screenshots and DOM snapshots at every
stage so we can see exactly where 'default slides' appear vs real content.

This runs the same flow a human user would. Headless Chromium via Playwright.

Usage:
    python _e2e_browser.py
"""

import asyncio
import json
import os
import sys
import time

from playwright.async_api import async_playwright

FE_URL = "http://localhost:8080"
OUT_DIR = "_e2e_browser_out"


async def wait_idle(page, ms=1500):
    try:
        await page.wait_for_load_state("networkidle", timeout=ms)
    except Exception:
        pass


async def shot(page, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.png")
    await page.screenshot(path=path, full_page=True)
    print(f"  saved {path}")


async def dump_html(page, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.html")
    html = await page.content()
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  saved {path}")


async def seed_localstorage_and_navigate(page):
    """Seed the brief + payload localStorage entries the FE uses so we can
    skip the brief-form step. Matches BRIEF_STORAGE_KEY / PAYLOAD_STORAGE_KEY
    in src/lib/server4.ts.
    """
    await page.goto(f"{FE_URL}/", wait_until="domcontentloaded")
    await wait_idle(page)
    brief = {
        "mode": "standard",
        "premiumInputMode": "prompt",
        "topic": "AI invoice automation for mid-market finance teams",
        "description": (
            "Pitch deck for an AI-powered finance automation platform that cuts "
            "invoice processing time from days to minutes. Target audience is "
            "seed-stage investors. Highlight the problem of manual approvals, "
            "the AI-driven solution, market traction, and a credible team."
        ),
        "targetAudience": "Seed-stage VCs",
        "purpose": "seed_round",
        "slideCount": 6,
        "language": "English",
        "companyName": "Acme",
        "companyTagline": "",
        "industry": "FinTech",
        "websiteUrl": "",
        "fundingStage": "seed",
        "audienceSophistication": "investor",
        "writingStyle": "yc_crisp",
        "templateId": "",
        "themeId": "",
        "visualDirection": "",
        "effects": {
            "style": "minimal",
            "transition": "fade",
            "reveal": "stagger",
            "chartMotion": "none",
            "imageMotion": "none",
            "intensity": "low",
            "autoplay": False,
            "reducedMotionSafe": True,
            "pdfPosterFrame": "final",
        },
        "generateImages": False,
        "generateNotes": False,
        "logoUrl": "",
        "primaryColor": "",
        "secondaryColor": "",
        "accentColor": "",
        "backgroundColor": "",
        "fontHeading": "",
        "fontBody": "",
        "brandGuidelines": "",
        "visualAssetBrief": "",
        "iconStyle": "",
        "marketTam": "",
        "marketSam": "",
        "marketSom": "",
        "targetSegment": "",
        "marketSources": "",
        "keyMetrics": "",
        "competitors": "",
        "traction": "",
        "partnerships": "",
        "team": "",
        "fundraisingAmount": "",
        "fundraisingRound": "Seed",
        "useOfFunds": "",
        "includeSlides": "",
        "excludeSlides": "",
        "keyMessages": "",
        "avoidTopics": "",
        "toneKeywords": "clear, evidence-first, founder-grade",
    }
    payload = {
        "mode": "standard",
        "input_method": "prompt",
        "standard_input": {
            "prompt": brief["description"],
            "slide_count": brief["slideCount"],
            "purpose": brief["purpose"],
            "language": brief["language"],
            "generate_images": False,
            "generate_notes": False,
        },
    }
    js = (
        "(args) => { localStorage.setItem('barise.server4.brief.v1', JSON.stringify(args.brief));"
        " localStorage.setItem('barise.server4.payload.v1', JSON.stringify(args.payload)); }"
    )
    await page.evaluate(js, {"brief": brief, "payload": payload})


async def trigger_generation_via_api(page):
    """Hit the backend /api/v4/generate directly so we don't depend on the FE
    brief-form to be 100% wired. Then seed localStorage with the project_id
    so /machine page picks it up. This isolates the rendering stages from
    any brief-form bugs.
    """
    import requests as _r
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
    resp = _r.post(
        "http://127.0.0.1:8003/api/v4/generate",
        json=payload,
        timeout=60,
    )
    body = resp.json()
    print(f"  generate status={resp.status_code} project_id={body.get('project_id')}")
    return body["project_id"]


async def wait_until_completed(page, project_id, timeout_s=240):
    """Poll generation status. Use stdlib requests instead of page.request
    because page.request has a hardcoded 30s wall clock; long generations
    routinely take 60-120s and we don't want to fail the harness on that."""
    import requests
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            r = requests.get(
                f"http://127.0.0.1:8003/api/v4/generation/{project_id}",
                timeout=15,
            )
            data = r.json()
        except Exception as exc:
            print(f"  poll_failed: {exc}")
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


async def seed_session_with_project(page, project_id):
    """Seed barise.server4.deckSession.v1 so the /edit and /studio pages
    can fetch slides for the just-generated project. We pre-fetch slides
    so the machine page short-circuits the auto-start branch (which only
    triggers when a completed session has no slides cached)."""
    import requests
    try:
        r = requests.get(
            f"http://127.0.0.1:8003/api/v4/projects/{project_id}/slides",
            timeout=15,
        )
        slides_payload = r.json() if r.status_code == 200 else None
    except Exception as exc:
        print(f"  prefetch_slides_failed: {exc}")
        slides_payload = None

    snap = (
        "(args) => { const next = { project_id: args.pid, status: 'completed', "
        "updated_at: new Date().toISOString(), contract_version: 3 };"
        " if (args.slidesPayload) {"
        "   next.project = args.slidesPayload.project;"
        "   next.slides = args.slidesPayload.slides;"
        "   next.title = args.slidesPayload.project && args.slidesPayload.project.title;"
        "   next.mode = args.slidesPayload.project && args.slidesPayload.project.mode;"
        " }"
        " localStorage.setItem('barise.server4.deckSession.v1', JSON.stringify(next)); }"
    )
    await page.evaluate(
        snap,
        {"pid": project_id, "slidesPayload": slides_payload},
    )
    if slides_payload:
        print(
            f"  seeded session with {len(slides_payload.get('slides', []))} slides"
        )


async def inspect_machine_stage(page, project_id):
    print("== MACHINE STAGE ==")
    await page.goto(f"{FE_URL}/machine", wait_until="domcontentloaded")
    await wait_idle(page, ms=4000)
    await asyncio.sleep(2)
    await shot(page, "01_machine")
    await dump_html(page, "01_machine")
    # extract any visible headlines on screen
    text = await page.evaluate("() => document.body.innerText")
    lines = [t.strip() for t in text.split("\n") if t.strip()][:50]
    print("    visible head lines:")
    for line in lines[:30]:
        print(f"      | {line}")


async def inspect_edit_stage(page):
    print("== EDIT STAGE ==")
    await page.goto(f"{FE_URL}/edit", wait_until="domcontentloaded")
    await wait_idle(page, ms=4000)
    await asyncio.sleep(2)
    await shot(page, "02_edit")
    await dump_html(page, "02_edit")
    text = await page.evaluate("() => document.body.innerText")
    lines = [t.strip() for t in text.split("\n") if t.strip()][:60]
    print("    visible head lines:")
    for line in lines[:40]:
        print(f"      | {line}")


async def inspect_studio_stage(page):
    print("== STUDIO STAGE ==")
    await page.goto(f"{FE_URL}/studio", wait_until="domcontentloaded")
    await wait_idle(page, ms=4000)
    await asyncio.sleep(2)
    await shot(page, "03_studio")
    await dump_html(page, "03_studio")
    text = await page.evaluate("() => document.body.innerText")
    lines = [t.strip() for t in text.split("\n") if t.strip()][:60]
    print("    visible head lines:")
    for line in lines[:40]:
        print(f"      | {line}")


async def inspect_press_stage(page):
    print("== PRESS STAGE ==")
    await page.goto(f"{FE_URL}/press", wait_until="domcontentloaded")
    await wait_idle(page, ms=4000)
    await asyncio.sleep(2)
    await shot(page, "04_press")


async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        page.on("console", lambda msg: print(f"  [{msg.type}] {msg.text[:200]}"))
        page.on(
            "pageerror",
            lambda err: print(f"  [pageerror] {str(err)[:300]}"),
        )

        await seed_localstorage_and_navigate(page)
        project_id = await trigger_generation_via_api(page)
        await seed_session_with_project(page, project_id)
        await wait_until_completed(page, project_id)
        # Re-seed after completion in case status check overwrote storage.
        await seed_session_with_project(page, project_id)

        await inspect_machine_stage(page, project_id)
        await inspect_edit_stage(page)
        await inspect_studio_stage(page)
        await inspect_press_stage(page)

        print(f"\nPROJECT_ID={project_id}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
