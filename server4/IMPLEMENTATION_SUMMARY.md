# Server4 — Complete Implementation Summary

> **Generated**: 2026-04-01
> **Scope**: Every file, every change, every feature across Phases B, C, D
> **Source**: Directly from codebase (not from plan documents)

---

## 1. Service Overview

| Property | Value |
|----------|-------|
| Framework | FastAPI 0.117+ |
| Port | 8003 |
| Python | 3.12 |
| DB | MongoDB (Motor async) |
| Cache/Queue | Redis + Celery |
| LLM Tiers | Kimi-K2 → DeepSeek-V3 → GPT-4o-mini → Mistral → Groq (8-key) → Cloudflare Workers (5) |
| Entry Point | `python main.py` (dev) / `uvicorn main:app` (prod) |

---

## 2. Complete File Inventory (What Exists Today)

### 2a. Core Application (12 files)

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | ~250 | FastAPI app, lifespan, router includes, theme/template seeding |
| `celery_worker.py` | ~240 | Celery app, 4 export tasks (PPTX/PDF/HTML/PNG), zombie reaper |
| `app/config.py` | ~160 | Pydantic BaseSettings, all env vars, 6-tier LLM config |
| `app/database.py` | ~40 | Motor MongoDB connection, index creation |
| `app/dependencies.py` | ~80 | Auth deps (require_auth, optional_auth), rate limiter |
| `app/models/presentation.py` | ~100 | GenerationInput, TemplateGenerationInput, GenerationState enum |
| `app/models/slide.py` | ~120 | SlideContent, SlideLayout enum, AISlideAction, writing_style field |
| `app/models/render.py` | ~60 | ExportFormat enum, ExportRequest, ExportJobResponse, ExportStatus |
| `app/models/theme.py` | ~40 | Theme model |

### 2b. Routers (8 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/routers/generation.py` | 175 | POST /api/generate/ai, POST /api/generate/template, status polling |
| `app/routers/presentations.py` | ~200 | CRUD: list, get, update, delete presentations |
| `app/routers/slides.py` | ~300 | CRUD + undo/redo + AI actions (rewrite, expand, translate, style-rewrite) |
| `app/routers/export.py` | ~280 | Export endpoint with sync/async routing, SAS tokens, threshold logic |
| `app/routers/templates.py` | ~100 | Template listing, get |
| `app/routers/themes.py` | ~80 | Theme listing, get |
| `app/routers/websocket.py` | ~120 | WebSocket progress streaming for generation |
| `app/routers/admin.py` | ~60 | Admin endpoints |

### 2c. Brain MCP — Prompts (14 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/mcp/brain_mcp/prompts/prompt_engine.py` | 221 | PromptEngine: compose_slide_prompt, compose_outline_prompt, compose_template_prompt, compose_chart_prompt, compose_notes_prompt, compose_refine_prompt |
| `app/mcp/brain_mcp/prompts/style_system.py` | 270 | 12 writing styles: yc_pitch, narrative, descriptive, persuasive, analytical, conversational, executive, technical, academic, minimalist, storytelling, investor_update |
| `app/mcp/brain_mcp/prompts/domain_layers.py` | 160 | PITCH_DECK_RULES, YC_PRINCIPLES, INVESTOR_PSYCHOLOGY, DATA_PRESENTATION_RULES, COMMON_MISTAKES |
| `app/mcp/brain_mcp/prompts/investor_system.py` | ~350 | YC_PITCH_SYSTEM, SEQUOIA_SYSTEM, INVESTOR_UPDATE_SYSTEM, TRACTION_SLIDE_SYSTEM, MARKET_SIZING_SYSTEM, UNIT_ECONOMICS_SYSTEM |
| `app/mcp/brain_mcp/prompts/quality_guards.py` | 262 | fluff_check, slide_density_check, claim_source_check, investor_readiness_check, consistency_check |
| `app/mcp/brain_mcp/prompts/slide_system.py` | ~200 | BASE_SLIDE_SYSTEM + LAYOUT_PROMPTS for all 12 layouts |
| `app/mcp/brain_mcp/prompts/outline_system.py` | ~150 | OUTLINE_SYSTEM_PROMPT with investor-grade guidance |
| `app/mcp/brain_mcp/prompts/research_planner.py` | ~150 | RESEARCH_PLANNER_SYSTEM, RESEARCH_SYNTHESIS_SYSTEM, DATA_EXTRACTOR_SYSTEM |
| `app/mcp/brain_mcp/prompts/template_system.py` | ~100 | TEMPLATE_FILL_SYSTEM |
| `app/mcp/brain_mcp/prompts/chart_system.py` | ~80 | CHART_DATA_SYSTEM |
| `app/mcp/brain_mcp/prompts/notes_system.py` | ~60 | SPEAKER_NOTES_SYSTEM |
| `app/mcp/brain_mcp/prompts/refine_system.py` | ~80 | REFINE_SYSTEM, EXPAND_SYSTEM, SUMMARIZE_SYSTEM, TRANSLATE_SYSTEM |

### 2d. Brain MCP — Generators (6 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/mcp/brain_mcp/generators/slide_generator.py` | 139 | generate_slide_content() with PromptEngine + quality guards |
| `app/mcp/brain_mcp/generators/outline_generator.py` | ~100 | Outline generation with PromptEngine |
| `app/mcp/brain_mcp/generators/batch_generator.py` | ~80 | Batch slide generation |
| `app/mcp/brain_mcp/generators/template_filler.py` | ~100 | Template placeholder filling |
| `app/mcp/brain_mcp/generators/chart_generator.py` | ~80 | Chart data generation |
| `app/mcp/brain_mcp/generators/notes_generator.py` | ~60 | Speaker notes generation |

### 2e. Brain MCP — Refiners (3 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/mcp/brain_mcp/refiners/content_refiner.py` | ~150 | rewrite, expand, summarize, translate, style_rewrite, get_available_styles |
| `app/mcp/brain_mcp/refiners/content_fitter.py` | ~80 | Content resize/fit |
| `app/mcp/brain_mcp/refiners/narrative_checker.py` | ~60 | Narrative flow validation |

### 2f. Brain MCP — Engines (7 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/mcp/brain_mcp/engines/search_engine.py` | ~80 | Web search |
| `app/mcp/brain_mcp/engines/market_engine.py` | 127 | Market data (FRED, Alpha Vantage, Finnhub) |
| `app/mcp/brain_mcp/engines/news_engine.py` | ~60 | Industry news/trends |
| `app/mcp/brain_mcp/engines/social_engine.py` | ~60 | Competitor analysis |
| `app/mcp/brain_mcp/engines/financial_engine.py` | ~60 | Financial benchmarks |
| `app/mcp/brain_mcp/engines/scraper_engine.py` | ~60 | Web scraping |
| `app/mcp/brain_mcp/engines/academic_engine.py` | ~60 | Academic paper search |

### 2g. Design MCP (5 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/mcp/design_mcp/engines/theme_engine.py` | ~370 | HSL color math, theme generation, suggest_theme() with tie-breaker logic |
| `app/mcp/design_mcp/engines/layout_solver.py` | ~230 | suggest_layout, analyze_content, analyze_slide() with 8 detection rules |
| `app/mcp/design_mcp/engines/color_engine.py` | ~80 | Color palette generation |
| `app/mcp/design_mcp/engines/chart_styler.py` | ~60 | Chart styling |
| `app/mcp/design_mcp/engines/accessibility.py` | ~60 | WCAG contrast checking |

### 2h. Render MCP (6 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/mcp/render_mcp/builders/pptx_builder.py` | 486 | Full PPTX generation: 12 layouts, native Excel charts, speaker notes |
| `app/mcp/render_mcp/builders/pdf_builder.py` | 123 | WeasyPrint HTML→PDF pipeline |
| `app/mcp/render_mcp/builders/html_builder.py` | ~550 | Premium HTML: Tailwind CSS, animations, keyboard nav, offline detection, Chart.js, all 12 layouts |
| `app/mcp/render_mcp/builders/image_builder.py` | 82 | Playwright slide-to-PNG rendering |
| `app/mcp/render_mcp/builders/thumbnail_builder.py` | 36 | Thumbnail generation wrapper |
| `app/mcp/render_mcp/builders/chart_builder.py` | ~60 | Chart rendering |

### 2i. LLM Services (5 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/services/llm/model_router.py` | ~200 | 6-tier model router with 3-deep fallback chain |
| `app/services/llm/azure_client.py` | ~80 | Azure OpenAI client |
| `app/services/llm/groq_client.py` | ~80 | Groq client (8-key round-robin) |
| `app/services/llm/cloudflare_client.py` | ~180 | CF Workers client: 3 modes (openai/text/image), generate_image() |
| `app/services/llm/base_client.py` | ~40 | BaseLLMClient abstract class |

### 2j. Orchestrator & Infrastructure (4 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/services/orchestrator/orchestrator.py` | ~1200 | Full pipeline: research (asyncio.gather), outline, content, template, design quality pass |
| `app/services/orchestrator/state_machine.py` | ~100 | Crash-proof state machine (MongoDB-persisted) |
| `app/services/orchestrator/progress_tracker.py` | ~80 | WebSocket progress streaming |
| `app/services/storage/blob_service.py` | ~100 | Azure Blob: upload, SAS-protected download URLs |

---

## 3. Phase B — PromptEngine in Orchestrator (IMPLEMENTED)

### What Was Built

**B1: `_do_research()` — Purpose-Aware Research with asyncio.gather**
- File: `orchestrator.py` lines 254-525
- Replaced generic LLM research with engine routing matrix
- pitch/fundraising/investor → MarketEngine + SocialEngine (parallel via asyncio.gather)
- quarterly/internal → FinancialEngine + NewsEngine (parallel)
- sales/marketing → SearchEngine + SocialEngine (parallel)
- academic/research → AcademicEngine + ScraperEngine (parallel)
- All engines run in parallel via `asyncio.gather(*tasks, return_exceptions=True)`
- Graceful fallback to LLM research if all engines fail
- Structured data extraction pass after synthesis

**B2: `_do_outline()` — PromptEngine.compose_outline_prompt()**
- File: `orchestrator.py` lines 659-720
- Uses `self.prompt_engine.compose_outline_prompt(style=writing_style, purpose=purpose)`
- Layers: base outline + style voice + PITCH_DECK_RULES + YC_PRINCIPLES (for pitch/demo_day) + COMMON_MISTAKES

**B3: `_generate_single_slide()` — PromptEngine.compose_slide_prompt() + Quality Guards**
- File: `orchestrator.py` lines 720-850
- Uses `self.prompt_engine.compose_slide_prompt(layout, style, purpose, slide_purpose)`
- Investor layout overrides: TRACTION_SLIDE_SYSTEM, MARKET_SIZING_SYSTEM
- `run_quality_guards()` after JSON parse: fluff detection, source checks, density checks, investor-specific checks

**B4: `_fill_template_slide()` — PromptEngine.compose_template_prompt()**
- File: `orchestrator.py` lines 161-250
- Uses `self.prompt_engine.compose_template_prompt(template_category, template_style)`
- Reads `default_writing_style` from template doc
- Category-aware: fundraising → YC principles, sales → persuasion, internal → data rules

**B5: writing_style Flow End-to-End**
- `writing_style` extracted from GenerationInput (default: "yc_pitch")
- Flows through: `_do_research()` → `_do_outline()` → `_generate_single_slide()`
- Template mode: reads `template.get("default_writing_style", "yc_pitch")`
- Design quality pass uses style-aware thresholds

### Files Modified
- `app/services/orchestrator/orchestrator.py` — Major rewrite of research, outline, content generation
- `app/routers/generation.py` — GenerationInput with writing_style field

### Tests
- `test_orchestrator_phase_b.py` — 7 tests, all passing

---

## 4. Phase C — Export Pipeline (IMPLEMENTED)

### What Was Built

**C1: SAS Token Generation**
- File: `app/services/storage/blob_service.py`
- `upload_file()` returns blob name (not raw URL)
- `generate_sas_download_url(blob_name, expiry_hours=1)` — time-limited SAS tokens
- `_parse_connection_string()` — extracts account_name/account_key for SAS signing
- Container stays private; links self-destruct after expiry

**C2/C3: Export Endpoint with Dynamic Threshold**
- File: `app/routers/export.py`
- `SLIDE_COUNT_THRESHOLD = 12`
- ≤12 slides: PPTX/PDF run sync (instant feedback, ~3-8s)
- >12 slides: PPTX/PDF route to Celery async (avoids HTTP timeout)
- HTML/PNG: always async (Playwright needs 15-60s)
- POST /api/export/{id} → returns completed job (sync) or pending job_id (async)
- GET /api/export/status/{job_id} → polls status, regenerates SAS token if completed
- GET /api/export/download/{job_id} → returns fresh SAS URL

**C3a: HtmlBuilder Rewrite — Premium Interactive HTML**
- File: `app/mcp/render_mcp/builders/html_builder.py` (~550 lines)
- Tailwind CSS via CDN with theme-aware config
- CSS animations: fade-in, slide-up, slide-left, zoom-in
- Keyboard navigation: arrow keys, space, Home/End, Escape
- Touch swipe support for mobile
- Progress bar + slide counter + navigation buttons
- Speaker notes toggle (press 'N')
- Fullscreen mode (press 'F')
- Chart.js integration with theme colors
- Print-friendly @media print rules
- Offline detection: if CDN fails, injects minimal fallback CSS + alerts user
- All 12 layouts rendered with Tailwind classes
- Responsive breakpoints for tablet/phone

**C4: Celery Tasks with Error Handling**
- File: `celery_worker.py`
- 4 export tasks: generate_pptx_task, generate_pdf_task, generate_html_task, generate_png_task
- Each task: PENDING → PROCESSING → COMPLETED/FAILED
- MongoDB job updates via sync pymongo (Celery runs in sync context)
- `_upload_and_complete()` helper: upload → SAS URL → mark completed
- `_find_job_id()` helper: locate pending job for presentation
- `worker_max_tasks_per_child=50` for memory safety
- `task_time_limit=300` (5 min hard limit)

**C5: Zombie Reaper**
- File: `celery_worker.py`
- `reap_stale_jobs()` Celery task runs every 5 minutes via Beat
- Kills jobs stuck in PROCESSING > 10 minutes
- Marks as FAILED with retry message

**C6: Cloudflare Client Fix (Noise Removal)**
- File: `app/services/llm/cloudflare_client.py`
- 3 modes: "openai" (messages/choices), "text" (message/response from pp.py), "image" (prompt→bytes)
- Response hardening: checks response/content/output keys with fallback
- `generate_image()` method for Phoenix/Lucid workers
- Factory functions: create_cf_glm_client, create_cf_qwen_client, create_cf_gemma_client, create_cf_phoenix_client, create_cf_lucid_client

**C7: Design Quality Pass (Style-Aware)**
- File: `app/services/orchestrator/orchestrator.py`
- `_run_design_quality_pass()` — runs after content generation
- Style-aware thresholds: yc_pitch/minimalist strict (15 words), academic/technical relaxed (35 words)
- Purpose-specific checks: market slide needs TAM/SAM/SOM, traction needs trajectory, ask needs amount
- Warnings included in generation response

### Files Modified
- `app/services/storage/blob_service.py` — SAS tokens
- `app/routers/export.py` — Complete rewrite (~280 lines)
- `celery_worker.py` — Complete rewrite (~240 lines)
- `app/mcp/render_mcp/builders/html_builder.py` — Complete rewrite (~550 lines)
- `app/services/llm/cloudflare_client.py` — Complete rewrite (~180 lines)
- `app/services/orchestrator/orchestrator.py` — Added quality pass

### Tests
- `test_phase_c.py` — 17 tests, all passing

---

## 5. Phase D — Design Intelligence (IMPLEMENTED)

### What Was Built

**D1: AI-Driven Theme Suggestions with Tie-Breaker**
- File: `app/mcp/design_mcp/engines/theme_engine.py`
- `_TOPIC_THEME_MAP` — 8 theme categories with 80+ keywords
- `suggest_theme(topic, purpose, audience)` — keyword matching with scoring
- Tie-breaker logic: if scores equal → safe fallback to "minimal-mono"
- Purpose overrides: investor → startup-gradient, internal → minimal-mono, quarterly → corporate-blue
- Zero LLM cost — pure rule-based matching

**D2: Content-Aware Layout Analysis with Data Parseability**
- File: `app/mcp/design_mcp/engines/layout_solver.py`
- `analyze_slide()` — 8 detection rules:
  1. Bullet overload (>6 bullets → split/chart suggestion)
  2. Number density → chart suggestion WITH data parseability check
  3. Comparison detection ("vs", "versus" → comparison layout)
  4. Timeline detection (dates/sequence → timeline layout)
  5. Single insight (1 short bullet → title-hero)
  6. Team content detection (names + roles → team-grid)
  7. KPI content detection (metrics → kpi-dashboard)
  8. Unstructured numbers → KPI dashboard instead of chart
- `_extract_data_points()` — extracts key-value pairs from bullet text
- Returns `actionable: bool` — only suggests layouts when data supports them

**D3: Research Engine Integration with asyncio.gather**
- File: `app/services/orchestrator/orchestrator.py`
- Purpose-aware engine routing with parallel execution
- `asyncio.gather(*tasks, return_exceptions=True)` — all engines run simultaneously
- Engine wrappers: _run_market_engine, _run_social_engine, _run_financial_engine, _run_news_engine, _run_search_engine, _run_academic_engine, _run_scraper_engine
- Graceful fallback to LLM research if all engines fail
- Results formatted into structured research brief

**D4: Style-Aware Design Quality Pass**
- File: `app/services/orchestrator/orchestrator.py`
- `_run_design_quality_pass()` — validates slides after generation
- `_get_bullet_word_limit()` — style-aware limits (yc_pitch=15, academic=35, default=20)
- Title length check (relaxed for academic/technical)
- Bullet count check (relaxed for academic/technical)
- Bullet word length check (only warns if 1.5x over limit)
- Purpose-specific checks: market slide TAM/SAM/SOM, traction trajectory, ask amount
- Warnings returned in generation response

### Files Modified
- `app/mcp/design_mcp/engines/theme_engine.py` — +190 lines
- `app/mcp/design_mcp/engines/layout_solver.py` — +125 lines
- `app/services/orchestrator/orchestrator.py` — +200 lines

### Tests
- `test_phase_d.py` — 18 tests, all passing

---

## 6. Complete Test Suite

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_orchestrator_phase_b.py` | 7 | ✅ All passing |
| `test_phase_c.py` | 17 | ✅ All passing |
| `test_phase_d.py` | 18 | ✅ All passing |
| **Total** | **42** | **✅ 42/42** |

---

## 7. Architecture Diagram (As-Built)

```
Frontend
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Server4 FastAPI (port 8003)                                │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Routers                                             │    │
│  │  generation.py → POST /api/generate/ai              │    │
│  │  slides.py → CRUD + AI actions + style-rewrite      │    │
│  │  export.py → PPTX/PDF/HTML/PNG with SAS tokens     │    │
│  │  presentations.py → CRUD                            │    │
│  │  websocket.py → progress streaming                  │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  PresentationOrchestrator                            │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │ _do_research() — asyncio.gather engines     │    │    │
│  │  │ _do_outline() — PromptEngine.compose()      │    │    │
│  │  │ _do_content_generation() — per-slide        │    │    │
│  │  │   └─ SlideGenerator.generate_slide_content()│    │    │
│  │  │       └─ PromptEngine.compose_slide_prompt()│    │    │
│  │  │       └─ run_quality_guards()               │    │    │
│  │  │ _run_design_quality_pass() — post-content   │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  Brain MCP                                           │    │
│  │  Prompts: PromptEngine + 12 styles + domain layers  │    │
│  │  Generators: slide, outline, batch, template, chart │    │
│  │  Refiners: content_refiner (style_rewrite)          │    │
│  │  Engines: search, market, news, social, financial   │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  Design MCP                                          │    │
│  │  ThemeEngine: suggest_theme() + HSL color math      │    │
│  │  LayoutSolver: analyze_slide() + 8 detection rules  │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  Render MCP                                          │    │
│  │  PptxBuilder (486 lines, 12 layouts, Excel charts)  │    │
│  │  PdfBuilder (WeasyPrint)                            │    │
│  │  HtmlBuilder (Tailwind, animations, offline detect) │    │
│  │  ImageBuilder (Playwright)                          │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │  LLM Router (6 tiers, 3-deep fallback)              │    │
│  │  T0: Kimi-K2 → T1: DeepSeek → T2: GPT-4o-mini      │    │
│  │  T3: Mistral → T4: Groq (8-key) → T5: CF Workers   │    │
│  │  CF Workers: openai/text/image modes                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Celery Worker (async exports)                      │    │
│  │  PPTX/PDF/HTML/PNG tasks + zombie reaper            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
    │                    │                    │
    ▼                    ▼                    ▼
  MongoDB            Redis               Azure Blob
  (presentations,    (cache,             (PPTX/PDF/
   slides, themes,    Celery)             HTML/PNG
   templates)                              exports)
```

---

## 8. What's NOT Yet Implemented (Future Phases)

| Feature | Status | Notes |
|---------|--------|-------|
| AI Image Generation (Phoenix/Lucid) | ❌ Not started | Phase E planned |
| Smart image placement in slides | ❌ Not started | Phase E |
| Thumbnail generation for gallery | ❌ Not started | Phase E |
| Image caching (Redis) | ❌ Not started | Phase E |
| Frontend integration | ❌ Out of scope | Handled by separate team |
| Flux image generation (premium) | ❌ Out of scope | Premium v2 |
| Microservices split | ❌ Out of scope | All MCPs in one container |
