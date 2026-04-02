# Phase C — Export Pipeline Implementation Plan

> **Owner**: Founder
> **Status**: Approved with mandatory changes (SAS Tokens + Slide Threshold)
> **Date**: 2026-04-01
> **Priority**: P0 — Critical for user-facing delivery

---

## 1. Current State (What Exists)

| Component | Status | Issue |
|-----------|--------|-------|
| `app/routers/export.py` | ⚠️ Stub | Only creates job records. No actual rendering. `TODO: Phase 3` comment present. |
| `celery_worker.py` | ✅ Tasks defined | 4 tasks exist (`generate_pptx_task`, `generate_pdf_task`, `generate_html_task`, `generate_png_task`) but never dispatched from export endpoint. |
| `PptxBuilder` | ✅ Complete | 486 lines. All 12 layouts supported. Native Excel-backed charts. Speaker notes. |
| `PdfBuilder` | ✅ Complete | 123 lines. WeasyPrint-based. Print-optimized HTML. |
| `HtmlBuilder` | ⚠️ Basic | 236 lines. Minimal Reveal.js wrapper. No animations, no responsive design, no keyboard nav. |
| `ImageBuilder` | ✅ Complete | 82 lines. Playwright-based. Sequential rendering to avoid memory issues. |
| `BlobStorageService` | ⚠️ Missing SAS | Uploads work but download URLs are raw blob URIs — no expiry, no access control. |
| `CloudflareWorkerClient` | ⚠️ Wrong format | Sends `{"messages": [...]}` (OpenAI format) but `pp.py` shows CF Workers expect `{"message": "..."}` (simple text). |

---

## 2. Reference Repo Insights

| Repo | Stars | Key Pattern | Applied To |
|------|-------|-------------|------------|
| [**frontend-slides**](https://github.com/zarazhangrui/frontend-slides) | 11.9k | Zero-dependency single HTML files. Inline CSS/JS. Visual style presets. Anti-AI-slop. Viewport-based responsive CSS. CSS animation patterns. | Our HTML export: self-contained, Tailwind-like utilities, CSS animations, no build tools |
| [**open-pencil**](https://github.com/open-pencil/open-pencil) | 3.9k | Design-to-code export (JSX/Tailwind). 90+ design tools. Token extraction. Design linting. | PPTX builder: theme token extraction, design consistency validation |
| [**pretext**](https://github.com/chenglou/pretext) | 29.2k | Pure JS text measurement without DOM reflow. Canvas-based font metrics. Multi-language support. | HTML builder: text fitting, overflow prevention, proper typography |

---

## 3. Architecture Decisions

### Export Routing Strategy (With Dynamic Threshold)

```
                    ┌─────────────────────────────────────────────────────┐
                    │              POST /api/export/{id}                  │
                    │              format: pptx | pdf | html | png        │
                    └──────────────────────┬──────────────────────────────┘
                                           │
                              ┌────────────┴────────────┐
                              │  Check slide_count      │
                              │  vs threshold (12)      │
                              └────────────┬────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
    ┌─────────▼──────────┐       ┌─────────▼──────────┐       ┌────────▼────────┐
    │  slide_count ≤ 12  │       │  slide_count > 12  │       │  HTML / PNG     │
    │  PPTX / PDF        │       │  PPTX / PDF        │       │  (always async) │
    │  SYNC (< 10s)      │       │  ASYNC (Celery)    │       │  ASYNC (Celery) │
    └─────────┬──────────┘       └─────────┬──────────┘       └────────┬────────┘
              │                            │                            │
    ┌─────────▼──────────┐       ┌─────────▼──────────┐       ┌────────▼────────┐
    │ PptxBuilder        │       │  Celery dispatch   │       │  Celery dispatch│
    │ PdfBuilder         │       │  PENDING→PROCESSING│       │  PENDING→PROC.  │
    │ (in-proc, instant) │       │  →COMPLETED/FAILED │       │  →COMPLETED/FL. │
    └─────────┬──────────┘       └─────────┬──────────┘       └────────┬────────┘
              │                            │                            │
    ┌─────────▼──────────┐       ┌─────────▼──────────┐       ┌────────▼────────┐
    │ Azure Blob + SAS   │       │ Azure Blob + SAS   │       │ Azure Blob + SAS│
    │ Return URL + SAS   │       │ Return URL + SAS   │       │ Return URL+SAS  │
    │ immediately        │       │ via poll/WebSocket  │       │ via poll/WS     │
    └────────────────────┘       └────────────────────┘       └─────────────────┘
```

### Why Dynamic Threshold?
- **≤ 12 slides**: PPTX ~3-5s, PDF ~5-8s. Instant feedback, no Celery overhead.
- **> 12 slides**: PPTX could take 20-30s (50-slide batch deck). HTTP timeout risk (Nginx/Azure LB = 30s-60s). Route to Celery to avoid 504 errors.
- **HTML/PNG**: Always async — Playwright needs 15-60s regardless of slide count.

### Why SAS Tokens?
- **Security risk**: Raw Azure Blob URLs expose confidential pitch decks to anyone with the link.
- **Solution**: Generate SAS tokens with 1-hour expiry. Container stays private. Links self-destruct.
- **Compliance**: Even if users share links, they die shortly after. Audit trail preserved.

---

## 4. Phase C Steps (7 Steps, 7 Files)

### C1: Add SAS Token Generation to BlobStorageService

**File**: `app/services/storage/blob_service.py`

**Strategy**: Add `generate_sas_download_url()` method that creates time-limited access tokens.

**Changes**:
```python
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

class BlobStorageService:
    def generate_sas_download_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generate a SAS-protected download URL with configurable expiry."""
        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
        )
        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
```

**Upload flow changes**:
- `upload_file()` returns the blob name (not the full URL)
- `generate_sas_download_url()` creates the time-limited URL on demand
- Download endpoint generates fresh SAS token each time (so re-downloads work within the window)

---

### C2: Wire PptxBuilder into Export Endpoint (Sync with Threshold)

**File**: `app/routers/export.py`

**Strategy**: PPTX runs synchronously for ≤12 slides, routes to Celery for >12 slides.

**Changes**:
1. Define `SLIDE_COUNT_THRESHOLD = 12`
2. In `create_export_job()`, when format is PPTX:
   - Check `presentation["slide_count"]` against threshold
   - If ≤ 12: Run sync (fetch → build → upload → SAS URL → COMPLETED)
   - If > 12: Dispatch to Celery (PENDING → return job_id)

**Code Pattern**:
```python
SLIDE_COUNT_THRESHOLD = 12

if body.format == ExportFormat.PPTX:
    slide_count = pres.get("slide_count", 0)

    if slide_count > SLIDE_COUNT_THRESHOLD:
        # Large deck — route to Celery to avoid HTTP timeout
        task = celery_app.send_task(
            "export.generate_pptx",
            args=[presentation_id, theme, slides, {"title": pres.get("title")}],
        )
        await db.export_jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "pending", "celery_task_id": task.id}}
        )
        return ExportJobResponse(..., status=ExportStatus.PENDING)

    # Small deck — run sync for instant feedback
    slides = await db.slides.find(
        {"presentation_id": presentation_id}
    ).sort("index", 1).to_list(None)

    pptx_bytes = PptxBuilder().build(slides, theme, {"title": pres.get("title")})

    blob_service = BlobStorageService()
    blob_name = f"exports/{presentation_id}/presentation.pptx"
    await blob_service.upload_file(file_data=pptx_bytes, blob_name=blob_name, ...)
    download_url = blob_service.generate_sas_download_url(blob_name, expiry_hours=1)

    await db.export_jobs.update_one(
        {"_id": job_id},
        {"$set": {
            "status": "completed",
            "download_url": download_url,
            "file_size": len(pptx_bytes),
            "completed_at": datetime.utcnow(),
        }}
    )
```

---

### C3: Wire PdfBuilder into Export Endpoint (Sync with Threshold)

**File**: `app/routers/export.py`

**Strategy**: Same threshold logic as PPTX. PDF via WeasyPrint is fast for small decks but can exceed 30s for 50-slide decks.

**Changes**:
1. Same `SLIDE_COUNT_THRESHOLD = 12` check
2. If ≤ 12: Sync (fetch → build → upload → SAS URL → COMPLETED)
3. If > 12: Async (Celery dispatch → PENDING)
4. Content-Type: `application/pdf`

---

### C4: Celery Tasks for HTML + PNG (Async)

**Files**: `app/routers/export.py` + `celery_worker.py`

**Strategy**: HTML and PNG always async (Playwright dependency). Dispatch to Celery, return job_id immediately. Client polls `GET /api/export/status/{job_id}`.

**Changes to `app/routers/export.py`**:
```python
if body.format in (ExportFormat.HTML, ExportFormat.PNG):
    task_name = "export.generate_html" if body.format == ExportFormat.HTML else "export.generate_png"
    task = celery_app.send_task(
        task_name,
        args=[presentation_id, theme, slides, {"title": pres.get("title")}],
    )
    await db.export_jobs.update_one(
        {"_id": job_id},
        {"$set": {"status": "pending", "celery_task_id": task.id}}
    )
    return ExportJobResponse(..., status=ExportStatus.PENDING, ...)
```

**Changes to `celery_worker.py`**:
- `generate_html_task` — already exists. Wire with error handling and MongoDB job updates.
- `generate_png_task` — already exists. Wire with error handling and MongoDB job updates.
- Add `_update_job_status()` helper to update MongoDB job record from Celery task.
- Add `reap_stale_jobs()` periodic task (see C6).

---

### C4a: Rewrite HtmlBuilder — Advanced HTML with Tailwind CSS + JS + Offline Detection

**File**: `app/mcp/render_mcp/builders/html_builder.py`

**Strategy**: Inspired by `frontend-slides` — create a **premium, self-contained HTML presentation** with offline detection.

#### Features (from reference repos)

| Feature | Source | Implementation |
|---------|--------|----------------|
| Zero-dependency single HTML | frontend-slides | All CSS/JS inline, no build tools |
| Tailwind CSS utilities | open-pencil | Tailwind CDN + custom utility classes |
| Viewport-based sizing | frontend-slides `viewport-base.css` | `vh`/`vw` units, no scroll |
| CSS animations | frontend-slides `animation-patterns.md` | Fade-in, slide-left, slide-up, zoom-in |
| Keyboard navigation | Reveal.js pattern | Arrow keys, space, Escape for overview |
| Touch swipe support | Mobile-first | `touchstart`/`touchend` event handlers |
| Progress bar | Reveal.js pattern | Bottom bar with percentage fill |
| Slide counter | Standard | "3 / 10" indicator |
| Speaker notes toggle | Reveal.js | Press 'N' to show/hide notes panel |
| Fullscreen mode | Standard | Press 'F' for fullscreen API |
| Chart.js integration | Existing | Interactive charts with theme colors |
| Print-friendly | Standard | `@media print` rules, one slide per page |
| Responsive | Mobile-first | Breakpoints for tablet/phone |
| Theme-aware | Existing | Uses presentation colors + fonts |
| **Offline detection** | **Founder feedback** | **JS check: if CDN fails, inject fallback stylesheet + alert** |

#### Offline/Error Handling (Mandatory)

```javascript
// At the top of the HTML, before any CDN loads:
(function() {
  var cdnCheckInterval = setInterval(function() {
    if (typeof tailwind === 'undefined' || typeof Chart === 'undefined') {
      // CDN failed — inject minimal fallback stylesheet
      var style = document.createElement('style');
      style.textContent =
        '.slide{display:block!important;padding:2rem;font-family:sans-serif;}' +
        '.slide:not(.active){display:none!important;}' +
        'body{background:#fff;color:#111;margin:0;}' +
        'h1,h2{margin:0.5em 0;} ul{padding-left:1.5em;}';
      document.head.appendChild(style);
      clearInterval(cdnCheckInterval);
      if (!navigator.onLine) {
        alert('This presentation requires an internet connection for styles and charts.\n\nPlease connect to the internet and reload.');
      }
    }
  }, 2000);
  // Stop checking after 10 seconds (CDNs should load by then)
  setTimeout(function() { clearInterval(cdnCheckInterval); }, 10000);
})();
```

#### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <!-- Offline detection script (runs before CDNs) -->
  <script>/* offline detection JS (see above) */</script>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: { primary: '{{ primary }}', accent: '{{ accent }}', ... },
          fontFamily: { heading: ['{{ heading_font }}', 'sans-serif'], body: ['{{ body_font }}', 'sans-serif'] }
        }
      }
    }
  </script>
  <style>
    /* Viewport-based slide sizing */
    .slide { width: 100vw; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    .slide:not(.active) { display: none; }
    /* Animation classes */
    .fade-in { animation: fadeIn 0.6s ease-out; }
    .slide-left { animation: slideLeft 0.5s ease-out; }
    /* Progress bar */
    #progress { position: fixed; bottom: 0; left: 0; height: 4px; background: var(--primary); transition: width 0.3s; }
    /* Print rules */
    @media print { .slide { display: block !important; page-break-after: always; } #progress, #nav { display: none; } }
  </style>
</head>
<body class="bg-white font-body text-gray-900">
  <div id="slides">
    <!-- Each slide: <div class="slide active" data-layout="...">...</div> -->
  </div>
  <div id="progress"></div>
  <div id="nav">...</div>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <script>
    // Keyboard nav, touch swipe, progress bar, fullscreen, speaker notes
  </script>
</body>
</html>
```

#### Layout Renderers (all 12 layouts)

Each layout gets a rich HTML template with Tailwind classes:
- `title-hero` → Full-bleed gradient background, centered title + subtitle, animated entrance
- `bullets` → Title + bullet list with staggered fade-in, proper typography scale
- `bullets-with-image` → Two-column grid, image with rounded corners + shadow
- `two-column` → Equal-width columns with clean typography
- `chart` → Chart.js canvas with theme colors, source attribution
- `comparison` → Side-by-side with check/X icons, color-coded columns
- `timeline` → Horizontal timeline with dots and connecting line
- `quote` → Large centered quote with decorative quotation marks, author attribution
- `team-grid` → Responsive grid with avatar placeholders, name, role, bio
- `kpi-dashboard` → Card grid with large numbers, change indicators, labels
- `full-image` → Background image with overlay text, parallax effect
- `blank` → Minimal centered content area

---

### C5: Export Job State Machine + Zombie Reaper

**File**: `app/routers/export.py` + `celery_worker.py`

**Strategy**: Implement proper state transitions with zombie task prevention.

```
PENDING → PROCESSING → COMPLETED
                      → FAILED
```

| State | When Set | By Whom |
|-------|----------|---------|
| `PENDING` | Job created, not yet started | Export endpoint |
| `PROCESSING` | Worker has started rendering | Celery task (on_start) |
| `COMPLETED` | File built, uploaded to Blob, SAS URL set | Celery task (on_success) |
| `FAILED` | Error during render/upload | Celery task (on_failure) |
| `FAILED` (zombie) | Stuck in PROCESSING > 10 min | Reaper cron task |

**Changes**:
- Update job status to PROCESSING when Celery task starts
- Update to COMPLETED/FAILED when task finishes
- Add error handling with proper error messages
- Add `celery_task_id` field to job document for tracking
- Add retry logic for transient failures (Blob upload timeout, etc.)

**Zombie Reaper** (`celery_worker.py`):
```python
@celery_app.task(name="export.reap_stale_jobs")
def reap_stale_jobs():
    """Kill jobs stuck in PROCESSING for > 10 minutes (crashed workers)."""
    from datetime import datetime, timedelta
    from app.database import get_db

    timeout = datetime.utcnow() - timedelta(minutes=10)
    db = get_db()
    result = db.export_jobs.update_many(
        {"status": "processing", "updated_at": {"$lt": timeout}},
        {"$set": {
            "status": "failed",
            "error": "Generation timed out (worker crash or OOM). Please retry.",
            "updated_at": datetime.utcnow(),
        }}
    )
    if result.modified_count > 0:
        logger.warning("zombie_jobs_reaped", count=result.modified_count)
    return result.modified_count
```

**Celery Beat Schedule** (add to `celery_worker.py`):
```python
celery_app.conf.beat_schedule = {
    "reap-stale-jobs": {
        "task": "export.reap_stale_jobs",
        "schedule": 300.0,  # Every 5 minutes
    },
}
```

---

### C6: Download Endpoint with SAS Token Regeneration

**File**: `app/routers/export.py`

**Strategy**: The existing `/api/export/download/{job_id}` endpoint returns JSON with `download_url`. Enhance it to:

1. **Regenerate SAS token** on each request (so expired tokens get refreshed within the download window)
2. **Direct streaming** (optional): If file is small (< 50MB), stream it directly from Azure Blob through the API with proper `Content-Disposition: attachment` header
3. **Redirect**: For large files, redirect to the SAS-protected Azure Blob URL
4. **Error handling**: Handle expired/missing files gracefully with 410 Gone

**Code Pattern**:
```python
@router.get("/download/{job_id}")
async def download_export(job_id: str, user: dict = Depends(require_auth), db = Depends(lambda: get_db())):
    job = await db.export_jobs.find_one({"_id": job_id, "user_id": user["user_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Export not ready. Status: {job['status']}")

    blob_name = job.get("blob_name")
    if not blob_name:
        raise HTTPException(status_code=500, detail="Export file metadata missing")

    # Regenerate fresh SAS token (user may have old expired link)
    blob_service = BlobStorageService()
    fresh_url = blob_service.generate_sas_download_url(blob_name, expiry_hours=1)

    # For small files, stream directly; for large, redirect to SAS URL
    if job.get("file_size", 0) < 50 * 1024 * 1024:  # < 50MB
        return {"download_url": fresh_url, "filename": f"presentation.{job['format']}"}
    return {"download_url": fresh_url, "filename": f"presentation.{job['format']}"}
```

---

### C7: Cloudflare Client Fix (Noise Removal + Response Hardening)

**File**: `app/services/llm/cloudflare_client.py`

**Problem**: Current client sends `{"messages": [...]}` (OpenAI format) but `pp.py` shows CF Workers expect `{"message": "..."}` (simple text). Response parsing also assumes OpenAI format.

**Evidence from `pp.py`**:
```python
# pp.py line 75-76: GLM/Qwen/Gemma workers
payload = {"message": "Give me a complete html,css and js for creating a slide..."}
response = requests.post(f"{WORKER_URL}/", headers=headers, json=payload)

# pp.py line 14-16: Phoenix image worker
data = {"prompt": "futuristic AI robot standing in neon cyberpunk city"}
response = requests.post(url, json=data, headers=headers)
```

**Fix**: Add a `mode` flag to `CloudflareWorkerClient` that switches between:

| Mode | Request Format | Response Format | Used By |
|------|---------------|-----------------|---------|
| `openai` (default) | `{"messages": [...]}` | `data["choices"][0]["message"]["content"]` | Standard LLM workers |
| `text` (from pp.py) | `{"message": "..."}` | `data.get("response") or data.get("content") or data.get("output") or str(data)` | GLM, Qwen, Gemma workers |
| `image` (from pp.py) | `{"prompt": "..."}` | Raw image bytes (base64 or binary) | Phoenix, Lucid workers |

**New Implementation**:
```python
class CloudflareWorkerClient(BaseLLMClient):
    def __init__(self, name: str, worker_url: str, token: str, mode: str = "openai"):
        self.name = name
        self.provider = "cloudflare"
        self._url = worker_url
        self._token = token
        self.mode = mode  # "openai" | "text" | "image"

    async def complete(self, messages, temperature=0.7, max_tokens=4096, ...):
        if self.mode == "text":
            # Flatten messages to single prompt string (pp.py pattern)
            prompt = "\n".join(m["content"] for m in messages)
            payload = {"message": prompt}
        else:
            # OpenAI-compatible format
            payload = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._url, json=payload, headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            })
            resp.raise_for_status()
            data = resp.json()

        # Response parsing per mode
        if self.mode == "text":
            # Text workers return response in various keys
            content = (
                data.get("response") or
                data.get("content") or
                data.get("output") or
                str(data)
            )
        else:
            # OpenAI-compatible
            content = data["choices"][0]["message"]["content"]

        return LLMResponse(content=content, model=self.name, provider=self.provider, ...)

    async def generate_image(self, prompt: str) -> bytes:
        """Generate image via Phoenix/Lucid workers (pp.py pattern)."""
        payload = {"prompt": prompt}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self._url, json=payload, headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            })
            resp.raise_for_status()
            return resp.content  # Raw image bytes
```

**Config Changes** (`app/config.py`):
```python
# Add missing CF worker image URLs
CF_WORKER_PHOENIX_URL: str = Field(default="", validation_alias=AliasChoices("CF_WORKER_PHOENIX_URL"))
CF_WORKER_PHOENIX_TOKEN: str = Field(default="", validation_alias=AliasChoices("CF_WORKER_PHOENIX_TOKEN"))
CF_WORKER_LUCID_URL: str = Field(default="", validation_alias=AliasChoices("CF_WORKER_LUCID_URL"))
CF_WORKER_LUCID_TOKEN: str = Field(default="", validation_alias=AliasChoices("CF_WORKER_LUCID_TOKEN"))
```

---

## 5. File Change Summary

| File | Action | Est. Lines | Purpose |
|------|--------|-----------|---------|
| `app/services/storage/blob_service.py` | **MODIFY** | +30 lines | Add SAS token generation for secure downloads |
| `app/routers/export.py` | **REWRITE** | ~113 → ~400 | Wire PPTX/PDF sync+threshold, HTML/PNG async, state machine, SAS download |
| `celery_worker.py` | **MODIFY** | +80 lines | Wire tasks properly, add error handling, MongoDB job updates, zombie reaper |
| `app/mcp/render_mcp/builders/html_builder.py` | **REWRITE** | ~236 → ~650+ | Tailwind CSS, animations, keyboard nav, responsive, offline detection, all 12 layouts |
| `app/services/llm/cloudflare_client.py` | **MODIFY** | ~96 → ~200 | Fix payload format (pp.py pattern), add response hardening, image generation |
| `app/config.py` | **MODIFY** | +4 lines | Add CF worker image URLs (Phoenix, Lucid) |
| `app/mcp/render_mcp/builders/pdf_builder.py` | **MINOR** | +30 lines | Add chart/image support for print HTML |

**Total: 1 rewrite + 4 modifications + 1 minor + 1 config = 7 file touches**

---

## 6. Implementation Order

```
Step 1: Add SAS tokens to BlobStorageService (C1)   — Security foundation
Step 2: Fix cloudflare_client.py (C7)               — Foundation fix, unblocks LLM fallbacks
Step 3: Rewrite html_builder.py (C4a)               — Core asset, needed by Celery HTML task
Step 4: Wire PptxBuilder in export.py (C2, threshold)— P0 export, fastest path to value
Step 5: Wire PdfBuilder in export.py (C3, threshold) — P0 export, second most-used format
Step 6: Wire Celery HTML/PNG tasks (C4, async)      — P1 export, premium features
Step 7: Zombie reaper + state machine (C5)           — Reliability, prevents stuck jobs
Step 8: Download endpoint with SAS (C6)              — UX, secure file delivery
```

---

## 7. Testing Strategy

### Unit Tests
| Test | What | How |
|------|------|-----|
| `test_sas_token_generation` | SAS URL has expiry, is not raw blob URL | Mock Azure SDK, verify URL contains `?sv=` and `se=` params |
| `test_pptx_export_sync_small` | ≤12 slides runs sync, returns SAS URL | Mock DB (10 slides), mock Blob, verify status=completed |
| `test_pptx_export_async_large` | >12 slides routes to Celery | Mock DB (20 slides), mock Celery, verify status=pending |
| `test_pdf_export_sync_small` | ≤12 slides runs sync, returns SAS URL | Mock DB (10 slides), mock Blob, verify status=completed |
| `test_pdf_export_async_large` | >12 slides routes to Celery | Mock DB (50 slides), mock Celery, verify status=pending |
| `test_html_export_async` | HTML dispatches to Celery | Mock Celery, verify status=pending |
| `test_png_export_async` | PNG dispatches to Celery | Mock Celery, verify status=pending |
| `test_cf_client_text_mode` | CF Worker text mode: `{"message": "..."}` | Mock httpx, verify request payload |
| `test_cf_client_image_mode` | CF Worker image mode: `{"prompt": "..."}` | Mock httpx, verify raw bytes returned |
| `test_zombie_reaper` | Stale jobs marked FAILED | Insert PROCESSING job with old timestamp, run reaper, verify FAILED |

### Integration Tests
| Test | What | How |
|------|------|-----|
| `test_full_export_flow_pptx` | End-to-end PPTX export | Create presentation → export → download SAS URL |
| `test_full_export_flow_html` | End-to-end HTML export | Create presentation → export → poll → download |
| `test_html_render_quality` | HTML output quality | Verify Tailwind classes, animations, keyboard nav, offline detection present |

---

## 8. Risk Areas & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| HtmlBuilder rewrite breaks Celery task | Low | High | Keep `build()` signature identical. Only change internal HTML generation. |
| Azure Blob not configured in dev | High | Medium | Fallback to local file storage with configurable path. Use `settings.ENV == "development"` check. |
| Playwright memory leaks in Celery | Medium | Medium | Already has `worker_max_tasks_per_child=50` for restart. Monitor memory usage. |
| PPTX/PDF sync timeout on large decks | Low | Medium | **Slide count threshold (>12 → Celery)** prevents this entirely. |
| CF Worker format mismatch | High | Low | Add `mode` flag with graceful fallback. Log actual response format for debugging. |
| Tailwind CDN unavailable | Low | Medium | **Offline detection script** injects minimal fallback CSS. Text remains readable. |
| Chart.js breaks in offline mode | Low | Low | **Offline detection** alerts user. Charts degrade to static data tables. |
| SAS token expiry during download | Low | Low | Download endpoint regenerates fresh SAS token on each request (1-hour window). |
| Zombie jobs stuck in PROCESSING | Medium | Medium | **Reaper task** runs every 5 minutes, kills jobs > 10 min old. |
| Container accidentally made public | Low | Critical | SAS tokens protect files even if container is public. Defense in depth. |

---

## 9. Dependencies

| Dependency | Current | Required | Notes |
|-----------|---------|----------|-------|
| `python-pptx` | ✅ Installed | ✅ | PPTX generation |
| `weasyprint` | ✅ Installed | ✅ | PDF generation |
| `playwright` | ✅ Installed | ✅ | PNG rendering |
| `celery[redis]` | ✅ Installed | ✅ | Async task queue + beat |
| `azure-storage-blob` | ✅ Installed | ✅ | File storage + SAS tokens |
| `tailwindcss` (CDN) | ❌ Not used | ✅ | HTML styling (CDN, no install) |
| `chart.js` (CDN) | ✅ Used | ✅ | Interactive charts (CDN) |

**No new pip dependencies required.** All new features use CDN-loaded JavaScript. SAS tokens use existing `azure-storage-blob` package.

---

## 10. Success Criteria

- [ ] PPTX export returns SAS-protected download URL within 10 seconds for ≤12 slide deck
- [ ] PPTX export routes to Celery for >12 slide decks (no HTTP timeout)
- [ ] PDF export returns SAS-protected download URL within 15 seconds for ≤12 slide deck
- [ ] PDF export routes to Celery for >12 slide decks (no HTTP timeout)
- [ ] HTML export produces a single self-contained file with animations, keyboard nav, responsive design, offline detection
- [ ] PNG export produces zip file with one image per slide at 1920×1080
- [ ] Cloudflare Workers respond correctly with `{"message": "..."}` format (text mode)
- [ ] SAS tokens expire after 1 hour; raw blob URLs never exposed
- [ ] Zombie reaper kills stuck jobs within 10 minutes
- [ ] All 10 Phase C unit tests pass
- [ ] No breaking changes to existing Phase B functionality
