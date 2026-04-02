# Server 4 — Complete Implementation Plan

> **Consolidated from**: Brain.md, SERVER4_PLAN.md, SLIDE_CONTENT_GENERATION_PLAN.md
> **Updated**: 2026-04-01
> **Architecture decision**: 3 MCPs (Brain + Design + Render) as stdio subprocesses in a single Docker container on Azure App Service (Canada Central)

---

## 1. Architecture Overview (v1)

```
Frontend (lliveupdatedstreaming)
    | REST + WebSocket
    v
┌─────────────────────────────────────────────────────── DOCKER ─┐
│  Server 4 (FastAPI, port 8003)                                │
│                                                                 │
│  ┌───────────────────────────────────────┐                     │
│  │  Orchestrator (crash-proof state)     │                     │
│  │  • State → MongoDB (survives restart) │                     │
│  │  • Progress → WebSocket               │                     │
│  │  • Falls back across all MCPs         │                     │
│  └──────┬──────────┬──────────┬──────────┘                     │
│         |  |  |                                                   │
│  ┌──────▼──┐  ┌─────▼───────┐  ┌────────────▼─────────┐         │
│  │ BRAIN   │  │ DESIGN      │  │ RENDER               │         │
│  │ MCP     │  │ MCP         │  │ MCP                  │         │
│  │         │  │             │  │                      │         │
│  │•Research│  │•Generative  │  │•PPTX Builder         │         │
│  │•Market  │  │  Themes     │  │•PDF Builder           │         │
│  │•Outline │  │•Layout      │  │•HTML/Reveal           │         │
│  │•Content │  │  Solver     │  │•PNG Export            │         │
│  │•Notes   │  │•Color Math  │  │•Thumbnails            │         │
│  │•Charts  │  │•Brand Spec  │  │•Azure Blob Upload     │         │
│  │•Refine  │  │•WCAG Check  │  │                      │         │
│  │•Template│  │             │  │                      │         │
│  └─────────┘  └─────────────┘  └──────────────────────┘         │
│                                                                 │
│  Shared Infra:                                                  │
│  • Celery Worker (async exports)                                │
│  • Redis (cache + broker)                                       │
│  • MongoDB → Azure Cosmos DB                                    │
│  • Azure Blob Storage (file exports)                           │
└─────────────────────────────────────────────────────────────────┘
```

### Two Generation Modes

**Mode A — AI Generation**: topic → research → outline → content → design → preview → edit → export

**Mode B — Template Generation**: pick template → fill placeholders with AI + user data → design → preview → edit → export

---

## 2. Complete File Inventory (what exists, what's built)

### 2a. Foundation — Already Built (86+ files)

| Component | Files | Location | Status |
|--------|-------|----------|--------|
| 6-tier LLM Router | `model_router.py`, `azure_client.py`, `groq_client.py`, `cloudflare_client.py` | `app/services/llm/` | ✅ DONE |
| Crash-proof State Machine | `state_machine.py`, `progress_tracker.py`, `fallback_handler.py` | `app/services/orchestrator/` | ✅ DONE |
| WebSocket Progress | `websocket.py` | `app/routers/` | ✅ DONE |
| Presentations CRUD | `presentations.py` | `app/routers/` | ✅ DONE |
| Slide Editing (CRUD + undo/redo + AI actions) | `slides.py` | `app/routers/` | ✅ DONE |
| Templates | `templates.py` | `app/routers/` | ✅ DONE |
| Themes | `themes.py` | `app/routers/` | ✅ DONE |
| Export (skeleton) | `export.py` | `app/routers/` | ⚠️ HAS TODO |
| 7 Research Engines | `search_engine.py`, `market_engine.py`, `news_engine.py`, `social_engine.py`, `financial_engine.py`, `scraper_engine.py`, `academic_engine.py` | `app/mcp/brain_mcp/engines/` | ✅ DONE |
| 6 Generators | `outline_generator.py`, `slide_generator.py`, `batch_generator.py`, `template_filler.py`, `chart_generator.py`, `notes_generator.py` | `app/mcp/brain_mcp/generators/` | ✅ DONE |
| 3 Refiners | `content_refiner.py`, `content_fitter.py`, `narrative_checker.py` | `app/mcp/brain_mcp/refiners/` | ✅ DONE |
| Design MCP (engines) | `theme_engine.py`, `layout_solver.py`, `color_engine.py`, `chart_styler.py`, `accessibility.py` | `app/mcp/design_mcp/engines/` | ✅ DONE |
| Render MCP (builders) | `pptx_builder.py`, `pdf_builder.py`, `html_builder.py`, `chart_builder.py`, `image_builder.py`, `thumbnail_builder.py` | `app/mcp/render_mcp/builders/` | ✅ DONE |
| Prompt Engine + 12 Writing Styles + Quality Guards | 5 new files | `app/mcp/brain_mcp/prompts/` | ✅ DONE |
| Generator Wiring (PromptEngine in all 6 generators) | 6 files modified | `app/mcp/brain_mcp/generators/` | ✅ DONE |
| Refiner Rewritten (style_rewrite + get_available_styles) | 1 file rewritten | `app/mcp/brain_mcp/refiners/content_refiner.py` | ✅ DONE |
| Model Updates (writing_style in AISlideAction + GenerationInput) | 2 files modified | `app/models/` | ✅ DONE |
| Style API Endpoints | 2 endpoints added | `app/routers/slides.py` | ✅ DONE |
| 4 New YC/Investor Templates | 4 new templates added | `main.py` | ✅ DONE |
| 8 Built-in Themes | 8 seeded themes | `main.py` | ✅ DONE |

### 2b. Still Needs to Be Built

| Component | Files | Reason |
|--------|-------|--------|
| **Orchestrator still uses basic prompts** | `orchestrator.py` | Has 4 inline hardcoded prompts instead of PromptEngine |
| **Export endpoint is a TODO** | `export.py` | Returns placeholder job, no actual file generation |
| **writing_style not piped through generation** | `generation.py` + `orchestrator.py` | GenerationInput has field but pipeline ignores it |
| **Celery export tasks missing** | `celery_worker.py` | No HTML/PNG async export tasks defined |
| **Design intelligence minimal** | `theme_engine.py`, `layout_solver.py` | No AI theme suggestions or content-aware layout analysis |
| **Research engines not wired into orchestrator** | `orchestrator.py` | Research is one generic call instead of structured engine use |

---

## 3. Implementation Phases (Remaining)

### PHASE B: Wire PromptEngine into the Orchestrator

**Why first**: Everything we just built (PromptEngine, 12 writing styles, quality guards, YC/investor domain layers) fires in individual generators but NOT in the orchestrator's main generation pipeline. Phase B connects it all end-to-end.

#### Phase B1 — `_do_research()` Upgrade
**File**: `app/services/orchestrator/orchestrator.py` lines 227-262

| Current State | Target State |
|--------|--------|
| One generic system prompt: "You are a research assistant..." | Structured research using `RESEARCH_PLANNER_SYSTEM` from `brain_mcp/prompts/research_planner.py` |
| Returns raw text | Returns structured research: key facts, sourced numbers (with attribution), competitor names, market data |
| Same prompt regardless of purpose | Purpose-aware scoping: pitch → search for TAM/SAM/SOM + competitors + traction benchmarks. Internal → search for KPI frameworks + best practices |
| Single LLM call | Two passes: research planning (RESEARCH_PLANNER_SYSTEM) + data extraction (DATA_EXTRACTOR_SYSTEM) |

```python
# New imports needed
from app.mcp.brain_mcp.prompts.research_planner import (
    RESEARCH_PLANNER_SYSTEM, RESEARCH_SYNTHESIS_SYSTEM, DATA_EXTRACTOR_SYSTEM
)

# Current: generic prompt (~20 chars)
system_prompt = "You are a research assistant..."

# Target: purpose-aware research scoping
system_prompt = RESEARCH_PLANNER_SYSTEM  # + append purpose-specific research tasks
user_prompt = f"Research strategy for: {topic}\nPurpose: {purpose}\nMode: {mode}"
```

#### Phase B2 — `_do_outline()` Upgrade
**File**: `orchestrator.py` lines 264-316

| Current State | Target State |
|--------|--------|
| Hardcoded 200-word "presentation architect" prompt | `PromptEngine.compose_outline_prompt(style, purpose)` |
| No style awareness | Style voice auto-applied (yc_pitch → short punchy sentences. narrative → story arc framing) |
| No domain expertise | For pitch/demo_day → YC principles + pitch deck rules + common mistakes auto-added |
| Outline structure same regardless of mode | Minimalist style → fewer slides. Analytical → more chart slides |

```python
# New wiring
from app.mcp.brain_mcp.prompts.prompt_engine import PromptEngine

# In generate_presentation():
self.prompt_engine = PromptEngine()

# In _do_outline():
system_prompt = self.prompt_engine.compose_outline_prompt(
    style=writing_style,  # passed from GenerationInput
    purpose=purpose,
)
```

#### Phase B3 — `_generate_single_slide()` Upgrade (biggest change)
**File**: `orchestrator.py` lines 346-414

| Current State | Target State |
|--------|--------|
| Generic "professional slide content writer" prompt (~300 words, no domain expertise) | `PromptEngine.compose_slide_prompt(layout, style, purpose, slide_purpose)` |
| Same quality bar for all layouts | Investor overrides auto-selected: chart+traction → TRACTION_SLIDE_SYSTEM, chart+market → MARKET_SIZING_SYSTEM |
| No voice consistency | Style voice (yc_pitch / narrative / analytical) auto-applied to every slide |
| No quality guards after generation | Optional quality check runs after JSON parse; warn if fluff/missing sources found |

```python
# Current
system_prompt = "You are a professional slide content writer..."

# Target
system_prompt = self.prompt_engine.compose_slide_prompt(
    layout=layout,
    style=writing_style,
    purpose=purpose,
    slide_purpose=slide_purpose,
)
```

#### Phase B4 — `_fill_template_slide()` Upgrade
**File**: `orchestrator.py` lines 416-482

| Current State | Target State |
|--------|--------|
| Generic "filling in a presentation template" prompt (~50 words) | `PromptEngine.compose_template_prompt(template_category, style)` |
| No template style awareness | Uses template's `default_writing_style` from seed data (investor-pitch → yc_pitch, sequoia-pitch → analytical) |
| Category ignored for domain layers | fundraising → YC principles + pitch deck rules. sales → persuasion principles. internal → data presentation rules |

```python
# In _fill_template_slide():
template_style = template.get("default_writing_style", "yc_pitch")
template_cat = template.get("category", "general")
system_prompt = self.prompt_engine.compose_template_prompt(
    template_category=template_cat,
    style=template_style,
)
```

#### Phase B5 — writing_style Flow Through Entire Pipeline
**Files**: `generation.py` (router) + `orchestrator.py`

| Step | Change |
|------|--------|
| Generation endpoint receives `GenerationInput` | Already has `writing_style: str = "yc_pitch"` field ✅ |
| Pass `writing_style` from input to orchestrator | Add parameter to `orchestrator.generate_presentation()` |
| Orchestrator distributes to all steps | `_do_research()`, `_do_outline()`, `_generate_single_slide()` all receive it |
| Template generation | Read `default_writing_style` from template doc; pass to `_fill_template_slide()` |

---

### PHASE C: Complete Export Pipeline

**Why second**: PPTX/PDF export is P0 — customers expect to download their decks. Currently the endpoint has placeholder logic that returns a fake completed job. The builders (`PptxBuilder`, `PdfBuilder`) exist but nobody calls them from the endpoint.

#### Phase C1 — Wire PptxBuilder
**File**: `app/routers/export.py`

| Step | Detail |
|------|--------|
| Import `PptxBuilder` from `app/mcp/render_mcp/builders/pptx_builder.py` | Builder takes `slides: list[dict]`, `theme: dict`, `metadata: dict` → returns `bytes` |
| In the PPTX export flow: fetch all slides from DB (by `presentation_id`, sorted by `index`) | `cursor = db.slides.find({"presentation_id": pid}).sort("index", 1).to_list(100)` |
| Fetch theme from DB | `theme = await db.themes.find_one({"_id": presentation.theme_id})` |
| Build presentation | `pptx_bytes = PptxBuilder().build(slides, theme, metadata)` |
| Upload to Azure Blob Storage | `url = await azure_blob.upload_blob(filename=f"{job_id}.pptx", data=pptx_bytes)` |
| Mark job COMPLETED with `download_url` | `db.export_jobs.update_one({"_id": job_id}, {"$set": {"status": "completed", "file_url": url, "file_size": len(pptx_bytes)}})` |

#### Phase C2 — Wire PdfBuilder
**File**: `app/routers/export.py`

| Step | Detail |
|------|--------|
| Import `PdfBuilder` from `app/mcp/render_mcp/builders/pdf_builder.py` | Uses WeasyPrint HTML→PDF pipeline |
| Fetch slides + theme (same pattern as C1) | Same DB queries |
| Build PDF | `pdf_bytes = PdfBuilder().build(slides, theme)` |
| Upload to Azure Blob + mark COMPLETED | Same pattern as C1 |

#### Phase C3 — Async Exports (Celery) for HTML + PNG
**Files**: `app/routers/export.py` + `celery_worker.py`

| Step | Detail |
|------|--------|
| PPTX and PDF are fast (~3-5 seconds) | Synchronous in HTTP endpoint is acceptable |
| HTML/PNG need Playwright (~15-30 seconds) | Must be async — dispatch to Celery, return job_id immediately |
| Create `export_html_task` in celery_worker.py | Fetches slides, calls `html_builder.build()`, uploads to Blob, updates job COMPLETED |
| Create `export_png_task` in celery_worker.py | Fetches slides, calls `image_builder.build()` for each slide, uploads zipped, updates job COMPLETED |
| Client polls `GET /api/export/status/{job_id}` | Returns: `{status, file_url (if completed), error_message (if failed)}` |

#### Phase C4 — Export Job State Machine
**File**: `app/routers/export.py`

| State | Trigger |
|-------|---------|
| `PENDING` | Job created, not yet started |
| `PROCESSING` | Worker has started rendering |
| `COMPLETED` | File built, uploaded to Blob, `file_url` set |
| `FAILED` | Error during render/upload, `error_message` set |

#### Phase C5 — Download Endpoint
**File**: `app/routers/export.py`

| Detail | 
|--------|
| `GET /api/export/download/{job_id}` — look up export job, stream file from Azure Blob with `Content-Disposition: attachment` header, return 404 if expired/missing |

---

### PHASE D: Design Intelligence + Research Integration

**Why third**: These are quality improvements on top of a working pipeline. Phase B makes the generation pipeline actually intelligent, Phase C makes exports work. Phase D makes everything feel premium.

#### Phase D1 — AI-Driven Theme Suggestions
**File**: `design_mcp/engines/theme_engine.py`

| Capability | Detail |
|------------|--------|
| `suggest_theme(topic, purpose, audience)` | Returns recommended theme_id from built-in themes |
| Logic: topic → mood → theme mapping | Tech/AI → tech-neon. Sales → startup-gradient. Internal → minimal-mono. Investor → corporate-blue. Health/green → nature-earth |
| Implementation: LLM-free for v1 (rule-based mapping based on keywords + purpose). Phase D1a: simple keyword match. Phase D1b: LLM-enhanced for custom/vague inputs |

#### Phase D2 — Content-Aware Layout Suggestions
**File**: `design_mcp/engines/layout_solver.py`

| Capability | Detail |
|------------|--------|
| Analyze slide content after generation | Count bullets, detect numbers, identify comparison text |
| Suggest layout changes (don't auto-change) | "Slide 3: 10 bullets detected, consider chart layout. Slide 7: single key insight → consider title-hero." |
| Return as warnings alongside validation report | Client displays suggestions for user to accept or ignore |

#### Phase D3 — Research Engine Integration into Orchestrator
**File**: `orchestrator.py`

| Current Research | Target Research |
|-----------------|-----------------|
| Single LLM call, generic prompt | Use specific research engines based on presentation purpose |
| Returns raw text summary | Returns structured bundle: `{key_facts[], sourced_numbers[], competitor_names[], market_data{}, statistics{}}` |

```python
# Phase D3 research routing by purpose
if purpose in ("pitch", "fundraising", "investor"):
    # Market + financial data needed
    market_data = await market_engine.analyze(industry=topic, metrics=["tam", "growth_rate", "key_players"])
    competitor_data = await social_engine.get_competitors(topic)

if purpose in ("quarterly", "internal"):
    # Metrics and framework data
    benchmark_data = await financial_engine.get_benchmarks(topic)
    news = await news_engine.get_trends(topic)
```

#### Phase D4 — Post-Content Design Quality Pass
**File**: `orchestrator.py` — new method after `_do_content_generation()`

| Check | Detail |
|-------|--------|
| Slide density violations | "Slide 3: 10 bullets (max 6). Slide 7: body text 400 chars (max 200)." |
| Missing required elements by slide purpose | "Market slide has no TAM/SAM/SOM data. Traction slide has no chart." |
| Style consistency across slides | "Slides 1-3 use data-backed language, slides 4-6 switched to vague claims." |
| Return as warnings array in generation response | `{"slide_count": 10, "slide_ids": [...], "warnings": [...], "status": "ready_for_editing"}` |

---

## 4. Implementation Order

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE B — Wire PromptEngine into Orchestrator               │
│  (5 steps, 2 files: orchestrator.py, generation.py)          │
├──────────────────────────────────────────────────────────────┤
│  B1. _do_research() — RESEARCH_PLANNER_SYSTEM prompts        │
│  B2. _do_outline() — PromptEngine.compose_outline_prompt()   │
│  B3. _generate_single_slide() — PromptEngine.compose_slide   │
│  B4. _fill_template_slide() — PromptEngine.compose_template  │
│  B5. writing_style flow end-to-end                           │
├──────────────────────────────────────────────────────────────┤
│  PHASE C — Complete Export Pipeline                          │
│  (5 steps, 2 files: export.py, celery_worker.py)             │
├──────────────────────────────────────────────────────────────┤
│  C1. PptxBuilder into export endpoint                        │
│  C2. PdfBuilder into export endpoint                         │
│  C3. Celery tasks for HTML + PNG                             │
│  C4. Export job state machine (PENDING→PROCESSING→DONE/FAIL) │
│  C5. Download endpoint                                       │
├──────────────────────────────────────────────────────────────┤
│  PHASE D — Design Intelligence                               │
│  (4 steps, 3 files: theme_engine.py, layout_solver.py,       │
│   orchestrator.py)                                           │
├──────────────────────────────────────────────────────────────┤
│  D1. AI theme suggestions                                    │
│  D2. Content-aware layout analysis                           │
│  D3. Research engine integration into orchestrator           │
│  D4. Post-content design quality pass                        │
└──────────────────────────────────────────────────────────────┘

Total: 14 steps across 6 files
Estimated blast radius: Phase B modifies orchestrator.py (the busiest file). All other phases are additive.
```

---

## 5. LLM Routing Strategy (as-built)

| Task | Model | Tier | Why |
|------|-------|------|-----|
| Research Planning | Kimi-K2-Thinking | T0 | Complex reasoning for research strategy |
| Research Synthesis | DeepSeek-V3 | T1 | Long-form narrative, analysis |
| Outline Generation | Kimi-K2-Thinking (premium), DeepSeek-V3 (standard) | T0/T1 | Structural reasoning |
| Slide Content (narrative) | DeepSeek-V3 | T1 | Best storyteller |
| Slide Content (data/charts) | GPT-4o-mini | T2 | Fast structured JSON |
| Slide Refinement | GPT-4o-mini (standard), multi-pass (premium) | T2 | Quick edits |
| Translation | Groq (8-key round-robin) | T4 | Sub-second |
| Template Fill | GPT-4o-mini | T2 | Follows instructions well |
| Content Fit/Resize | Groq | T4 | Quick summarize |
| All calls have 3-deep fallback chain | Primary → Alt1 → Cloudflare | |

---

## 6. Export Format Matrix

| Format | Priority | Sync/Async | Builder | Tool |
|--------|----------|------------|---------|------|
| PPTX | P0 — Must have | Sync (~5s) | PptxBuilder | python-pptx |
| PDF | P0 — Must have | Sync (~5s) | PdfBuilder | WeasyPrint |
| HTML | P1 — Premium | Async (Celery) | HtmlBuilder | reveal.js template |
| PNG | P1 — Premium | Async (Celery) | ImageBuilder | Playwright + Pillow |

---

## 7. Database Schema

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `presentations` | Master records | user_id, title, description, mode, theme_id, status, generation_state, slide_count |
| `slides` | Individual slides (normalized) | presentation_id (FK), index, layout, content {}, version |
| `slide_versions` | Undo/redo history | slide_id (FK), version, layout, content {}, change_type, created_at |
| `themes` | Built-in + generated + custom themes | name, type, colors {}, fonts {} |
| `templates` | Built-in presentation templates | name, category, slides [], default_theme, default_writing_style |
| `template_analytics` | Usage tracking | template_id, layout_changes {}, completion_rate |
| `generation_logs` | Cost + performance observability | presentation_id, phase, model, provider, latency_ms, tokens_used |

---

## 8. Content Writing Styles (12)

| Style | ID | Best For | Voice Rule |
|-------|-----|----------|------------|
| YC Pitch | `yc_pitch` | Investor decks, YC applications | Short sentences. Bold claims backed by data. No fluff. |
| Narrative | `narrative` | Keynotes, vision decks | Hero's journey structure. Emotional hooks. |
| Descriptive | `descriptive` | Product demos | Rich adjectives, concrete details. |
| Persuasive | `persuasive` | Sales decks, fundraising | Every slide builds toward an ask. |
| Analytical | `analytical` | Quarterly reports, board decks | Lead with numbers. Every claim sourced. |
| Conversational | `conversational` | Internal decks, workshops | Speaks like a human. Contractions. |
| Executive | `executive` | C-suite, board meetings | Top-line only. 3 bullets max per slide. |
| Technical | `technical` | Engineering reviews | Precise terminology. Architecture described. |
| Academic | `academic` | Research presentations | Formal register. Citations. |
| Minimalist | `minimalist` | Design-forward decks | One idea per slide. 6 words max in title. |
| Storytelling | `storytelling` | Case studies | Customer narratives. "Meet Sarah, a PM at..." |
| Investor Update | `investor_update` | Post-investment updates | Transparent about challenges. Numbers-first. |

---

## 9. Risk Areas

| Risk | Detail | Mitigation |
|------|--------|------------|
| Orchestrator PromptEngine rewrite | Orchestrator is the busiest file. If wiring is wrong, the entire generation pipeline breaks. | Each step (B1-B5) tested independently with `py_compile` after. |
| Export file storage | Where to save before upload: temp disk vs direct to Blob. | PptxBuilder returns bytes → write to tempfile.BytesIO → upload to Azure Blob. |
| Celery complexity for HTML/PNG | Playwright browser rendering is slow and memory-heavy. | Must have explicit timeouts and memory limits on Celery workers. |
| Quality guard performance | Running guards on every slide adds CPU. | Quality guards are rule-based (regex/length checks), zero LLM calls. Safe to run everywhere. |
| Template default_writing_style | Newly added field — existing templates in MongoDB (pre-seed) may not have it. | Use `.get("default_writing_style", "yc_pitch")` with fallback. |

---

## 10. What This Plan Does NOT Cover (Out of Scope for v1)

- Frontend changes (handled by lliveupdatedstreaming separately)
- Image generation via Flux or other AI image models (Premium v2)
- New LLM providers (current 6-tier routing sufficient)
- Microservices split (all 3 MCPs stay as stdio subprocesses in one container)
- Image Gen MCP (v2 Premium feature)
- Split Researcher MCP / Content MCP (v2 scale-up)
