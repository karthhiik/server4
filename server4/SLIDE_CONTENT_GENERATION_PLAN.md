# Slide Content Generation System — Implementation Plan (v2 — Founder's Cut)

> **v2 Revision:** Incorporates all founder feedback. Simplified for v1 launch velocity.
> Merged Research+Content into Brain MCP. Added editing, layout switching, template generation,
> crash-proof state machine, observability, undo/redo, prompt sanitization.
> Designed for Azure Docker deployment from day one.

---

## Founder's Architecture Decision

> "Build a reliable car first. The Ferrari comes later."

**v1 Launch:** 3 MCPs (Brain + Design + Render) — ship fast, validate the magic.
**v2 Scale:** Split Brain → Researcher + Content. Add Image Gen MCP. Add advanced templates.

---

## System Architecture (v1 — Azure Docker Ready)

```
                              ┌──────────────────────────────┐
                              │        Frontend               │
                              │   (lliveupdatedstreaming)      │
                              │   /presentations route         │
                              │                                │
                              │  Modes: AI Generation          │
                              │         Template Generation    │
                              │                                │
                              │  Post-Gen: Slide Editor        │
                              │    • Edit text/images          │
                              │    • Change layouts            │
                              │    • Reorder/add/delete        │
                              │    • Undo/redo                 │
                              └──────────────┬─────────────────┘
                                             │ REST + WebSocket
                                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     DOCKER CONTAINER: server4                            │
│                     Azure App Service (Linux)                            │
│                     Port 8003                                            │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Gateway (main.py)                        │  │
│  │                                                                    │  │
│  │  Routers:                                                          │  │
│  │  /api/presentations/*     → CRUD + History                        │  │
│  │  /api/generate/*          → AI Generation (Brain MCP)             │  │
│  │  /api/templates/*         → Template Generation + Library         │  │
│  │  /api/slides/*            → Slide Editing + Layout Change         │  │
│  │  /api/themes/*            → Theme Management                      │  │
│  │  /api/export/*            → Export (PPTX, PDF, HTML, PNG)         │  │
│  │  /ws/generation/{id}      → Progress Streaming                    │  │
│  │                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │              ORCHESTRATOR SERVICE                             │  │  │
│  │  │              (Crash-Proof State Machine)                      │  │  │
│  │  │                                                              │  │  │
│  │  │  • State persisted to MongoDB (survives restart)             │  │  │
│  │  │  • Routes to correct MCP via subprocess                      │  │  │
│  │  │  • Streams progress via WebSocket                            │  │  │
│  │  │  • Handles fallbacks across all MCPs                         │  │  │
│  │  │  • OpenTelemetry tracing on every LLM/API call               │  │  │
│  │  └──────────┬──────────────────┬──────────────────┬─────────────┘  │  │
│  │             │                  │                  │                 │  │
│  └─────────────┼──────────────────┼──────────────────┼─────────────────┘  │
│                │                  │                  │                    │
│       ┌────────▼────────┐ ┌──────▼───────┐ ┌───────▼────────┐           │
│       │  BRAIN MCP      │ │ DESIGN MCP   │ │ RENDER MCP     │           │
│       │  (subprocess)   │ │ (subprocess) │ │ (subprocess)   │           │
│       │                 │ │              │ │                │           │
│       │ • Web Research  │ │ • Generative │ │ • PPTX Builder │           │
│       │ • Market Data   │ │   Themes     │ │ • PDF Builder  │           │
│       │ • Outline Gen   │ │ • Layout     │ │ • HTML/Reveal  │           │
│       │ • Slide Content │ │   Solver     │ │ • PNG Export   │           │
│       │ • Speaker Notes │ │ • Color Math │ │ • Thumbnails   │           │
│       │ • Chart Data    │ │ • Brand Spec │ │ • Azure Blob   │           │
│       │ • Refinement    │ │ • WCAG Check │ │   Upload       │           │
│       │ • Translation   │ │              │ │                │           │
│       └─────────────────┘ └──────────────┘ └────────────────┘           │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  SHARED INFRA (in-container)                                        │ │
│  │  • Celery Worker (async exports)                                    │ │
│  │  • Redis (cache + Celery broker) ← Azure Cache for Redis in prod   │ │
│  │  • MongoDB client → Azure Cosmos DB (MongoDB API)                   │ │
│  │  • Azure Blob Storage client (for file exports)                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### Why 3 MCPs (not 5) for v1?

| v1 (Launch) | v2 (Scale) | Reason |
|-------------|------------|--------|
| **Brain MCP** (Research + Content) | Split → Researcher MCP + Content MCP | Research passes directly to outline in-memory. 40% less inter-process latency. |
| **Design MCP** | Design MCP + Image Gen MCP | Image gen is Premium-only. Ship Standard first. |
| **Render MCP** | Render MCP (unchanged) | Rendering is stable. No need to split. |

### Azure Docker Deployment (Single Container)

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system deps for WeasyPrint + Playwright
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev shared-mime-info && \
    playwright install chromium --with-deps

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Single entrypoint: FastAPI starts MCPs as subprocesses
# MCPs communicate via stdio (no network ports needed)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
```

**Key Decision:** MCPs run as **stdio subprocesses** inside the same container.
No separate ports. No cross-container networking. The Orchestrator spawns them
via `subprocess.Popen` and communicates via stdin/stdout (MCP stdio transport).

In production, if you need to scale a specific MCP independently, switch that
one to SSE transport on its own container. But for v1, stdio-in-one-container is simpler.

---

## Two Generation Modes

### Mode A: AI Slide Generation
```
User Input (topic, audience, purpose)
    → Brain MCP: Research → Outline → Content
    → Design MCP: Theme + Layout
    → Render MCP: Thumbnail preview
    → User: Edit slides (text, layout, reorder, add/delete)
    → Export (PPTX / PDF / HTML / PNG)
```

### Mode B: Template-Based Generation
```
User picks template from library (e.g., "Investor Pitch", "Quarterly Report")
    → Template loaded with placeholder structure (10 slides, predefined layouts)
    → User provides: company name, key data, images
    → Brain MCP: Replace template placeholders with AI-generated content
        • Title slide: Company name + tagline
        • Problem slide: AI writes problem statement from user input
        • Market slide: AI fetches real market data via research engine
        • Team slide: User-provided names/roles + AI-generated bios
        • Financial slide: User-provided numbers → AI creates chart data
    → Design MCP: Apply user's brand colors to template theme
    → User: Edit slides (same editor as Mode A)
    → Export
```

### Template Library Structure

```python
# Template definition (stored in MongoDB, not static JSON files)
{
    "_id": "investor-pitch-v1",
    "name": "Investor Pitch Deck",
    "category": "fundraising",
    "description": "10-slide standard investor pitch format",
    "thumbnail_url": "...",
    "slide_count": 10,
    "mode_available": ["standard", "premium"],
    "slides": [
        {
            "index": 0,
            "layout": "title-hero",
            "purpose": "Company introduction",
            "placeholders": {
                "title": "{{company_name}}",
                "subtitle": "{{tagline}}",
                "background": "{{hero_image_or_gradient}}"
            },
            "ai_instructions": "Generate a compelling tagline if not provided"
        },
        {
            "index": 1,
            "layout": "two-column",
            "purpose": "Problem statement",
            "placeholders": {
                "title": "The Problem",
                "left_content": "{{problem_description}}",
                "right_content": "{{market_pain_point_stats}}"
            },
            "ai_instructions": "Research real statistics about this problem. Use Serper/Tavily."
        },
        {
            "index": 2,
            "layout": "bullets-with-image",
            "purpose": "Solution overview",
            "placeholders": {
                "title": "Our Solution",
                "bullets": "{{solution_points}}",
                "image": "{{product_screenshot_or_ai_generated}}"
            },
            "ai_instructions": "Write 3-4 concise solution points. Generate product mockup if no image."
        },
        # ... 7 more slides (Market Size, Business Model, Traction, Team, Competition, Financials, Ask)
    ],
    "default_theme": "corporate-blue",
    "created_at": "2026-03-31",
    "usage_count": 0,
    "avg_rating": null
}
```

**Built-in Templates (v1):**

| Template | Slides | Category | Layouts Used |
|----------|--------|----------|-------------|
| Investor Pitch | 10 | Fundraising | title-hero, two-column, bullets, chart, team-grid |
| Sales Deck | 8 | Sales | title-hero, problem-solution, comparison, pricing, cta |
| Quarterly Report | 12 | Internal | title, kpi-dashboard, chart, timeline, bullets |
| Product Launch | 10 | Marketing | title-hero, features, demo, pricing, roadmap |
| Startup Overview | 6 | General | title, problem, solution, market, team, contact |
| Workshop/Training | 15 | Education | title, agenda, content, exercise, summary |
| Company Profile | 8 | Corporate | title, about, services, team, clients, contact |
| Project Proposal | 10 | Business | title, background, objectives, timeline, budget, team |

---

## Slide Editing System (Post-Generation)

### What the Editor Supports

After AI generates slides (or template fills them), the user enters the **Slide Editor**:

```
┌──────────────────────────────────────────────────────────────────────┐
│  SLIDE EDITOR                                                         │
│                                                                       │
│  ┌─────────────────────────────────┬─────────────────────────────┐   │
│  │                                 │  EDIT PANEL                  │   │
│  │                                 │                              │   │
│  │     SLIDE PREVIEW               │  📝 Title: [editable]       │   │
│  │     (live render)               │  📝 Content: [editable]     │   │
│  │                                 │  📝 Speaker Notes: [edit]   │   │
│  │                                 │                              │   │
│  │                                 │  🎨 Layout: [dropdown]      │   │
│  │                                 │    ○ Title Hero              │   │
│  │                                 │    ○ Two Column              │   │
│  │                                 │    ○ Bullets + Image         │   │
│  │                                 │    ○ Full Image              │   │
│  │                                 │    ○ Chart                   │   │
│  │                                 │    ○ Comparison              │   │
│  │                                 │    ○ Timeline                │   │
│  │                                 │    ○ Quote                   │   │
│  │                                 │    ○ Team Grid               │   │
│  │                                 │    ○ KPI Dashboard           │   │
│  │                                 │                              │   │
│  │                                 │  🖼️ Image: [upload/AI gen]  │   │
│  │                                 │  📊 Chart: [edit data]      │   │
│  │                                 │                              │   │
│  │                                 │  🤖 AI Actions:             │   │
│  │                                 │    [Rewrite] [Expand]       │   │
│  │                                 │    [Summarize] [Translate]  │   │
│  │                                 │                              │   │
│  └─────────────────────────────────┴─────────────────────────────┘   │
│                                                                       │
│  THUMBNAIL STRIP (drag to reorder)                                    │
│  [1]  [2]  [3]  [4]  [5]  [+Add]  [🗑️ Delete]                      │
│                                                                       │
│  ↩️ Undo  ↪️ Redo  |  💾 Auto-saved  |  [Export ▾]                   │
└──────────────────────────────────────────────────────────────────────┘
```

### Editing API Endpoints

```
# Slide-level editing
PUT    /api/slides/{slide_id}                    # Update slide content (title, text, notes)
PUT    /api/slides/{slide_id}/layout             # Change layout (triggers re-layout)
PUT    /api/slides/{slide_id}/image              # Upload/replace image
PUT    /api/slides/{slide_id}/chart              # Update chart data

# Presentation-level editing
PUT    /api/presentations/{id}/slides/reorder    # Drag-to-reorder
POST   /api/presentations/{id}/slides            # Add new slide (blank or AI-generated)
DELETE /api/presentations/{id}/slides/{slide_id}  # Delete slide

# AI-assisted editing
POST   /api/slides/{slide_id}/rewrite            # AI rewrites content
POST   /api/slides/{slide_id}/expand             # AI expands bullet points
POST   /api/slides/{slide_id}/summarize          # AI condenses content
POST   /api/slides/{slide_id}/translate          # Translate to another language

# Undo/Redo
POST   /api/slides/{slide_id}/undo               # Revert to previous version
POST   /api/slides/{slide_id}/redo               # Re-apply reverted change
GET    /api/slides/{slide_id}/history             # Get version history
```

### Layout Changing

When user changes layout, the backend:

1. Takes existing slide content (title, bullets, body, image, chart)
2. Applies new layout constraints (what fits where)
3. Re-flows content to match new layout
4. Returns updated slide with new layout applied

```python
# PUT /api/slides/{slide_id}/layout
# Request: { "layout": "two-column" }

async def change_slide_layout(slide_id: str, new_layout: str):
    slide = await db.slides.find_one({"_id": slide_id})

    # Design MCP solves the layout transition
    reshaped = await design_mcp.transition_layout(
        content=slide["content"],
        from_layout=slide["layout"],
        to_layout=new_layout,
    )

    # If content doesn't fit (e.g., 10 bullets → title-hero layout),
    # Brain MCP summarizes to fit
    if reshaped.overflow:
        reshaped.content = await brain_mcp.fit_content(
            content=reshaped.content,
            max_bullets=reshaped.layout_constraints.max_bullets,
            max_chars=reshaped.layout_constraints.max_chars,
        )

    # Save as new version (for undo)
    await save_slide_version(slide_id, slide)  # snapshot old version
    await db.slides.update_one(
        {"_id": slide_id},
        {"$set": {"layout": new_layout, "content": reshaped.content}}
    )

    return reshaped
```

### Available Layouts (10 types)

| Layout | Description | Content Zones |
|--------|-------------|---------------|
| `title-hero` | Full-screen title with background | title, subtitle, background |
| `two-column` | Split left/right | title, left_content, right_content |
| `bullets` | Title + bullet points | title, bullets (3-8) |
| `bullets-with-image` | Bullets left, image right | title, bullets, image |
| `full-image` | Full-bleed image with overlay text | title, image, caption |
| `chart` | Title + chart visualization | title, chart_data, subtitle |
| `comparison` | Side-by-side comparison | title, left_label, left_items, right_label, right_items |
| `timeline` | Horizontal/vertical timeline | title, events (3-6) |
| `quote` | Large quote with attribution | quote_text, author, role |
| `team-grid` | Team member cards | title, members (2-6) |
| `kpi-dashboard` | Key metrics cards | title, metrics (3-6) |
| `blank` | Empty slide for custom content | freeform |

---

## Undo/Redo & Version History

### Data Model (per-slide versioning)

```python
# slides collection — one document per slide
{
    "_id": ObjectId("..."),
    "presentation_id": ObjectId("..."),
    "index": 3,                          # Position in deck
    "layout": "two-column",
    "content": {
        "title": "Market Opportunity",
        "left_content": "The global SaaS market...",
        "right_content": "TAM: $380B by 2028...",
        "speaker_notes": "Emphasize the 15% YoY growth...",
        "chart_data": null,
        "image_url": null
    },
    "version": 5,                        # Current version number
    "created_at": "2026-03-31T10:00:00Z",
    "updated_at": "2026-03-31T10:35:00Z"
}

# slide_versions collection — one document per version snapshot
{
    "_id": ObjectId("..."),
    "slide_id": ObjectId("..."),         # FK to slides._id
    "version": 4,                        # Which version this snapshot is
    "layout": "bullets",                 # Layout at that version
    "content": { ... },                  # Content at that version
    "change_type": "layout_change",      # What changed (edit, layout_change, ai_rewrite, etc.)
    "created_at": "2026-03-31T10:30:00Z"
}
```

**Undo:** Load version N-1 from `slide_versions`, replace current slide content.
**Redo:** Load version N+1 from `slide_versions` (if exists).
**History:** Show timeline of all versions with `change_type` labels.

---

## Database Schema (Normalized — Cosmos DB)

### Why Normalized (not embedded)?

The original plan stored `list[dict]` of slides inside one presentation document.
Problems: 16MB document limit, can't query single slides, can't do incremental updates.

**Fix:** Separate collections with foreign keys.

```
┌─────────────────────────────────────────────────────────────────┐
│                        COSMOS DB SCHEMA                          │
│                                                                  │
│  presentations              slides                slide_versions │
│  ─────────────              ──────                ────────────── │
│  _id                        _id                   _id            │
│  user_id                    presentation_id (FK)  slide_id (FK)  │
│  title                      index                 version        │
│  description                layout                layout         │
│  mode (standard/premium)    content {}            content {}     │
│  theme_id                   version               change_type    │
│  status (draft/complete)    created_at            created_at     │
│  generation_state           updated_at                           │
│  generation_error                                                │
│  slide_count                                                     │
│  thumbnail_url              templates                            │
│  created_from (ai/template) ─────────                            │
│  template_id (nullable)     _id                                  │
│  created_at                 name                                 │
│  updated_at                 category                             │
│                             description                          │
│  themes                     slide_definitions []                 │
│  ──────                     default_theme                        │
│  _id                        usage_count                          │
│  name                       avg_rating                           │
│  type (builtin/generated/   created_at                           │
│        custom)                                                   │
│  colors {}                  template_analytics                   │
│  fonts {}                   ──────────────────                   │
│  generated_from (nullable)  template_id                          │
│  created_at                 layout_changes {}                    │
│                             completion_rate                      │
│  generation_logs            most_edited_slides                   │
│  ───────────────            avg_time_to_complete                 │
│  _id                                                             │
│  presentation_id                                                 │
│  phase                                                           │
│  model_used                                                      │
│  provider                                                        │
│  latency_ms                                                      │
│  tokens_used                                                     │
│  success (bool)                                                  │
│  error (nullable)                                                │
│  created_at                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Available LLM Arsenal & Strategic Routing

### Model Tier Map

| Tier | Model | Provider | Best For | Latency | Cost |
|------|-------|----------|----------|---------|------|
| T0 (Thinker) | **Kimi-K2-Thinking** | Azure AI | Planning, outline reasoning, complex decisions | ~8-15s | Medium |
| T1 (Storyteller) | **DeepSeek-V3.2** | Azure AI | Slide narrative, storytelling, long-form content | ~3-8s | Low |
| T2 (Workhorse) | **GPT-4o-mini** | Azure OpenAI | Fast structured JSON, refinement, layout decisions | ~1-3s | Low |
| T3 (Coder) | **Mistral-medium-2505** | Azure AI | Code slides, technical content, data formatting | ~2-5s | Low |
| T4 (Speed) | **Groq (8 keys)** | Groq Cloud | Ultra-fast: translations, summaries, quick edits | ~0.3-1s | Free tier |
| T5 (Fallback) | **CF Workers** (GLM/Qwen/Gemma) | Cloudflare | Emergency fallback if all above fail | ~2-4s | Free |
| T6 (Local) | **TinyLlama/Flan-T5/Phi-2** | HuggingFace Local | Offline mode, simple completions | ~1-5s | Free |

### Image Generation (v2 — Premium)

| Tier | Model | Best For |
|------|-------|----------|
| Primary | **Flux-Pro-2** (Azure) | Professional slide backgrounds, hero images |
| Fallback-1 | **CF Phoenix Worker** | Quick generation when Flux is slow |
| Fallback-2 | **CF Gemma Worker** | Simple patterns, backgrounds |

### Research API Routing (Round-Robin + Fallback)

| Category | Primary | Fallback-1 | Fallback-2 |
|----------|---------|------------|------------|
| Web Search | **Serper** (3 keys) | **Tavily** | **SerpAPI** (2 keys) |
| Deep Search | **Exa.ai** | **You.com** | **Jina.ai** |
| Web Scraping | **Firecrawl** | **Jina Reader** | Raw httpx |
| Financial | **Alpha Vantage** | **Finnhub** | **Polygon** + **FRED** |
| Market Size | **Census** + **World Bank** | **Financial Modeling Prep** | Cached data |
| News/Trends | **NewsAPI** | **NewsData** | **Guardian** + **World News** |
| Social | **Reddit** | **ProductHunt** | **YouTube** |
| Academic | **CORE API** | **arXiv** (free) | Cached papers |

### LLM Router Decision Tree

```python
class ModelRouter:
    """
    Routes to optimal LLM based on task type.
    Every call has a 3-deep fallback chain.
    Every call is logged to generation_logs for observability.
    """

    ROUTING_TABLE = {
        "outline_planning": {
            "primary": "kimi-k2-thinking",    # Deep reasoning
            "fallback_1": "deepseek-v3",
            "fallback_2": "gpt-4o-mini",
        },
        "narrative_storytelling": {
            "primary": "deepseek-v3",          # Best storyteller
            "fallback_1": "kimi-k2-thinking",
            "fallback_2": "gpt-4o-mini",
        },
        "structured_json": {
            "primary": "gpt-4o-mini",          # Fastest JSON output
            "fallback_1": "groq",
            "fallback_2": "deepseek-v3",
        },
        "technical_code": {
            "primary": "mistral-medium",       # Code fluency
            "fallback_1": "gpt-4o-mini",
            "fallback_2": "deepseek-v3",
        },
        "translation_quick_edit": {
            "primary": "groq",                 # Sub-second, 8-key round-robin
            "fallback_1": "gpt-4o-mini",
            "fallback_2": "cf-qwen",
        },
        "template_fill": {
            "primary": "gpt-4o-mini",          # Fast + follows instructions
            "fallback_1": "deepseek-v3",
            "fallback_2": "groq",
        },
        "content_fit_resize": {
            "primary": "groq",                 # Quick summarize/expand
            "fallback_1": "gpt-4o-mini",
            "fallback_2": "cf-glm",
        },
    }
```

---

## Brain MCP (Research + Content — Merged for v1)

### Purpose
The "brain" of the system. Handles ALL intelligence work: web research, data gathering,
outline generation, slide content writing, speaker notes, chart data, refinement, translation.

### Tools (14 tools)

```python
# ═══════════════════════════════════════════
# RESEARCH TOOLS (6)
# ═══════════════════════════════════════════

@tool("search_web")
async def search_web(
    query: str,
    search_type: str = "general",  # general | news | academic | financial
    max_results: int = 10,
) -> ResearchResult:
    """Multi-source web search. Serper (3 keys) → Tavily → SerpAPI."""

@tool("analyze_market")
async def analyze_market(
    industry: str,
    geography: str = "global",
    metrics: list[str] = ["tam", "growth_rate", "key_players"],
) -> MarketAnalysis:
    """Market data from Census, World Bank, FRED, Financial Modeling Prep."""

@tool("research_competitors")
async def research_competitors(
    company_or_product: str,
    industry: str,
) -> CompetitorReport:
    """Competitor intel from Serper + Exa.ai + Reddit + ProductHunt."""

@tool("fetch_statistics")
async def fetch_statistics(
    topic: str,
    stat_type: str = "market",
) -> StatisticsBundle:
    """Fetches labeled data points for charts. FRED, Alpha Vantage, etc."""

@tool("scan_trends")
async def scan_trends(
    topic: str,
    sources: list[str] = ["news", "social"],
) -> TrendReport:
    """Trending analysis from NewsAPI, Reddit, ProductHunt, YouTube."""

@tool("deep_research")
async def deep_research(
    topic: str,
    depth: str = "standard",  # quick | standard | comprehensive
) -> DeepResearchReport:
    """
    Multi-step research pipeline:
    1. Kimi-K2 plans research strategy
    2. Parallel web searches (Serper/Tavily/Exa)
    3. Firecrawl/Jina deep page extraction
    4. DeepSeek-V3 synthesizes findings
    5. GPT-4o-mini extracts key data points

    Returns pre-contextualized data (not raw JSON) with confidence scores
    and source attribution — optimized for LLM consumption (profitelligence pattern).
    """

# ═══════════════════════════════════════════
# CONTENT GENERATION TOOLS (8)
# ═══════════════════════════════════════════

@tool("generate_outline")
async def generate_outline(
    topic: str,
    audience: str,
    purpose: str,
    slide_count: int = 10,
    research_context: Optional[str] = None,
    mode: str = "standard",
) -> PresentationOutline:
    """
    Premium: Kimi-K2 → DeepSeek review → GPT-4o-mini validate (3-pass)
    Standard: DeepSeek-V3 single pass
    """

@tool("generate_slide_content")
async def generate_slide_content(
    slide_title: str,
    slide_purpose: str,
    slide_layout: str,
    context: str,
    research_data: Optional[str] = None,
    previous_slide: Optional[str] = None,  # Narrative continuity
) -> SlideContent:
    """
    Routes by content type:
    - Narrative → DeepSeek-V3
    - Data/charts → GPT-4o-mini
    - Technical → Mistral-medium
    """

@tool("batch_generate_slides")
async def batch_generate_slides(
    outline: PresentationOutline,
    research_data: Optional[str] = None,
    mode: str = "standard",
) -> list[SlideContent]:
    """
    Parallel generation using asyncio.gather.
    Groups slides by type → routes to optimal model per group.
    Post-pass: DeepSeek-V3 checks narrative continuity across all slides.
    """

@tool("fill_template")
async def fill_template(
    template_id: str,
    user_inputs: dict,     # Company name, data, images provided by user
    mode: str = "standard",
) -> list[SlideContent]:
    """
    Template-based generation:
    1. Load template definition from MongoDB
    2. For each slide placeholder:
       - If user provided content → use it
       - If placeholder needs research → call search_web/analyze_market
       - If placeholder needs AI text → call generate_slide_content
    3. Replace all {{placeholders}} with real content
    4. Return filled slides ready for design phase
    """

@tool("generate_speaker_notes")
async def generate_speaker_notes(
    slide_content: dict,
    audience: str,
    duration_per_slide: int = 90,
) -> SpeakerNotes:
    """DeepSeek-V3 for narrative speaking points. Premium only."""

@tool("generate_chart_data")
async def generate_chart_data(
    chart_type: str,
    data_description: str,
    research_data: Optional[str] = None,
) -> ChartData:
    """GPT-4o-mini for structured chart JSON. Includes source attribution."""

@tool("refine_content")
async def refine_content(
    current_content: dict,
    instruction: str,  # "make concise" / "add data" / "change tone"
    mode: str = "standard",
) -> RefinedContent:
    """
    Standard: GPT-4o-mini single pass
    Premium: Kimi-K2 analyzes → DeepSeek rewrites → GPT-4o-mini validates

    IMPORTANT: instruction goes through PromptSanitizer before LLM call.
    """

@tool("translate_content")
async def translate_content(
    content: dict,
    target_language: str,
) -> TranslatedContent:
    """Groq (8-key round-robin) for ultra-fast translation. Fallback: GPT-4o-mini."""
```

### Prompt Sanitization (Security)

```python
# brain_mcp/security/prompt_sanitizer.py

class PromptSanitizer:
    """
    Prevents prompt injection in user-provided refinement instructions.

    Strips/flags:
    - "ignore previous instructions"
    - "system prompt" / "you are now"
    - "print" / "output" / "reveal" + "password" / "key" / "secret" / "env"
    - Base64 encoded suspicious strings
    - Excessive special characters that might be injection attempts
    """

    BLOCKLIST_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now\s+a",
        r"system\s*prompt",
        r"(print|output|reveal|show|display).*(password|key|secret|env|token|api)",
        r"(forget|disregard|override).*(rules|instructions|prompt)",
    ]

    def sanitize(self, user_input: str) -> str:
        for pattern in self.BLOCKLIST_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise PromptInjectionError(f"Suspicious input detected")
        return user_input.strip()
```

### Internal Architecture

```
brain_mcp/
├── server.py                  # MCP server entry (stdio transport)
├── tools.py                   # 14 tool definitions
├── security/
│   └── prompt_sanitizer.py    # Prompt injection prevention
├── engines/
│   ├── search_engine.py       # Multi-provider search (round-robin + fallback)
│   ├── market_engine.py       # Census, FRED, World Bank, FMP
│   ├── news_engine.py         # NewsAPI, NewsData, Guardian
│   ├── social_engine.py       # Reddit, ProductHunt, YouTube
│   ├── financial_engine.py    # Alpha Vantage, Finnhub, Polygon
│   ├── scraper_engine.py      # Firecrawl, Jina, raw httpx
│   └── academic_engine.py     # CORE, arXiv
├── generators/
│   ├── outline_generator.py   # Outline generation
│   ├── slide_generator.py     # Single slide content
│   ├── batch_generator.py     # Parallel batch generation
│   ├── template_filler.py     # Template placeholder replacement
│   ├── chart_generator.py     # Chart data generation
│   └── notes_generator.py     # Speaker notes
├── refiners/
│   ├── content_refiner.py     # Content improvement pipeline
│   ├── narrative_checker.py   # Cross-slide narrative flow
│   └── content_fitter.py      # Resize content to fit layout constraints
├── models/
│   ├── research_models.py     # ResearchResult, MarketAnalysis, etc.
│   └── content_models.py      # SlideContent, Outline, ChartData, etc.
├── prompts/
│   ├── research_planner.py    # Kimi-K2 research planning prompts
│   ├── data_synthesizer.py    # DeepSeek synthesis prompts
│   ├── outline_system.py      # Per-purpose outline prompts
│   ├── slide_system.py        # Per-layout slide prompts
│   ├── template_system.py     # Template filling prompts
│   ├── refine_system.py       # Refinement prompts
│   └── chart_system.py        # Chart data prompts
└── config.py
```

---

## Design MCP — Generative Themes (Not Static JSON)

### Key Change from v1 Plan
Old: 8 static JSON theme files picked from a list.
New: **Generative theme engine** that creates themes on-the-fly from brand input.

### Tools (7 tools)

```python
@tool("apply_theme")
async def apply_theme(
    slides: list[dict],
    theme_id: str,              # builtin ID or custom theme ID
    custom_overrides: Optional[dict] = None,
) -> ThemedSlides:
    """Apply existing theme. Loads from MongoDB (not static files)."""

@tool("generate_theme")
async def generate_theme(
    brand_colors: list[str],    # ["#2563EB", "#1E40AF"]
    brand_vibe: str = "corporate",  # corporate | playful | minimal | bold | tech
    font_preference: str = "modern",
) -> GeneratedTheme:
    """
    GENERATIVE theme creation. Not picking from a list — BUILDING one.

    1. color_engine.py: HSL math to generate harmonious palette from brand colors
       - Primary, secondary, accent, background, text, muted
       - Auto light/dark variants
       - Chart color sequence (6-8 colors that work together)
    2. GPT-4o-mini: Select font pairing (heading + body) from web-safe fonts
    3. Validate WCAG AA contrast for all color combinations
    4. Save to MongoDB as custom theme

    No LLM needed for color math. LLM only for font selection edge cases.
    """

@tool("solve_layout")
async def solve_layout(
    slide_content: dict,
    target_layout: str,
    constraints: Optional[dict] = None,
) -> LayoutSolution:
    """
    Constraint-based layout solver.
    Determines text block sizes, image zones, margins, font hierarchy.
    Mostly algorithmic. LLM only for complex custom layouts.
    """

@tool("transition_layout")
async def transition_layout(
    content: dict,
    from_layout: str,
    to_layout: str,
) -> LayoutTransition:
    """
    Layout switching for the editor.
    Maps content zones from old layout → new layout.
    Flags overflow if content doesn't fit new layout.
    """

@tool("apply_brand_spec")  # Premium
async def apply_brand_spec(
    slides: list[dict],
    brand_spec: dict,  # { logo_url, colors, fonts, guidelines }
) -> BrandedSlides:
    """Custom branding. GPT-4o-mini for intelligent logo placement."""

@tool("validate_design")
async def validate_design(
    slides: list[dict],
    theme: dict,
) -> DesignValidation:
    """
    WCAG AA contrast, font size minimums, text overflow,
    image resolution, brand consistency. Algorithmic — no LLM.
    """

@tool("style_chart")
async def style_chart(
    chart_data: dict,
    theme: dict,
) -> StyledChart:
    """Theme-consistent chart colors, fonts, sizes."""
```

### Built-in Themes (stored in MongoDB, seeded on first run)

| Theme | Vibe | Primary | Accent | Font |
|-------|------|---------|--------|------|
| Corporate Blue | Professional | #2563EB | #1E40AF | Inter / Roboto |
| Startup Gradient | Energetic | #7C3AED | #EC4899 | Poppins / Open Sans |
| Minimal Mono | Clean | #18181B | #71717A | IBM Plex / System |
| Bold Dark | Impact | #F97316 | #EF4444 | Montserrat / DM Sans |
| Nature Earth | Organic | #059669 | #84CC16 | Merriweather / Lato |
| Tech Neon | Futuristic | #06B6D4 | #8B5CF6 | Space Grotesk / JetBrains Mono |
| Warm Sunset | Friendly | #F59E0B | #EF4444 | Nunito / Source Sans |
| Ocean Calm | Trustworthy | #0369A1 | #0EA5E9 | Libre Baskerville / Raleway |

### Internal Architecture

```
design_mcp/
├── server.py
├── tools.py                   # 7 tools
├── engines/
│   ├── theme_engine.py        # Theme CRUD + generative theme builder
│   ├── layout_solver.py       # Constraint-based layout algorithm
│   ├── layout_transition.py   # Layout change logic (zone mapping + overflow detection)
│   ├── color_engine.py        # HSL palette generation (pure math, no LLM)
│   ├── chart_styler.py        # Chart styling
│   ├── brand_engine.py        # Brand spec enforcement
│   └── accessibility.py       # WCAG contrast checking
├── models/
│   └── design_models.py
└── config.py
```

---

## Render MCP — All Export Formats

### Why ALL formats matter

| Format | Who needs it | Priority |
|--------|-------------|----------|
| **PPTX** | Everyone. VCs expect .pptx. Editable in PowerPoint/Google Slides. | **P0 — Must have** |
| **PDF** | Sharing via email, printing. Universal read-only format. | **P0 — Must have** |
| **HTML/Reveal.js** | Web presentations, embedding on websites. | **P1 — Premium** |
| **PNG images** | Social media slides, thumbnails, previews. | **P1 — Premium** |

### Tools (7 tools)

```python
@tool("render_pptx")
async def render_pptx(
    slides: list[dict],
    theme: dict,
    metadata: dict,
    include_notes: bool = False,
) -> RenderedFile:
    """
    Build .pptx using python-pptx.

    Features:
    - Master slide layouts per layout type
    - Native embedded charts (Excel-backed, editable in PowerPoint)
    - Image embedding from URLs
    - Speaker notes on each slide (Premium)
    - Slide transitions
    - Theme fonts and colors applied to master

    Upload to Azure Blob Storage → return download URL.
    """

@tool("render_pdf")
async def render_pdf(
    slides: list[dict],
    theme: dict,
    quality: str = "standard",
) -> RenderedFile:
    """
    WeasyPrint HTML→PDF pipeline.
    One page per slide, matching PPTX dimensions (16:9).
    """

@tool("render_html")  # Premium
async def render_html(
    slides: list[dict],
    theme: dict,
    interactive: bool = True,
) -> RenderedFile:
    """
    reveal.js interactive HTML presentation.
    Keyboard nav, transitions, embedded Chart.js charts,
    responsive, fullscreen. Exported as .zip.
    """

@tool("render_images")  # Premium
async def render_images(
    slides: list[dict],
    theme: dict,
    resolution: str = "1920x1080",
) -> list[RenderedFile]:
    """
    Playwright headless Chromium → PNG per slide.
    Pillow post-processing (optimization).
    """

@tool("generate_thumbnail")
async def generate_thumbnail(
    first_slide: dict,
    theme: dict,
) -> RenderedFile:
    """Quick 400x225 thumbnail for gallery preview."""

@tool("validate_deck")
async def validate_deck(
    slides: list[dict],
) -> ValidationReport:
    """Pre-render validation: required fields, content limits, data integrity."""

@tool("render_chart_native")
async def render_chart_native(
    chart_data: dict,
    output_format: str = "pptx",  # pptx | image | chartjs
) -> ChartRendered:
    """
    Smart chart rendering:
    - PPTX: Native Excel-backed chart (editable in PowerPoint!)
    - HTML: Chart.js/ECharts JSON config (interactive!)
    - Image: Matplotlib PNG (for PDF/PNG exports)

    This means charts are NOT just static images — they're editable.
    """
```

### PPTX Native Charts (Key Differentiator)

```python
# render_mcp/builders/pptx_builder.py

from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

def add_native_chart(slide, chart_data, theme):
    """
    Creates EDITABLE Excel-backed chart in PowerPoint.
    User can modify data directly in PowerPoint after export.

    This is a massive UX win vs competitors who export static images.
    """
    chart_type_map = {
        "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
        "line": XL_CHART_TYPE.LINE,
        "pie": XL_CHART_TYPE.PIE,
        "donut": XL_CHART_TYPE.DOUGHNUT,
        "area": XL_CHART_TYPE.AREA,
    }

    cd = CategoryChartData()
    cd.categories = chart_data["labels"]
    for dataset in chart_data["datasets"]:
        cd.add_series(dataset["label"], dataset["values"])

    chart_frame = slide.shapes.add_chart(
        chart_type_map[chart_data["chart_type"]],
        left, top, width, height, cd
    )

    # Apply theme colors to chart
    chart = chart_frame.chart
    for i, series in enumerate(chart.series):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = theme["chart_colors"][i]
```

### Internal Architecture

```
render_mcp/
├── server.py
├── tools.py                   # 7 tools
├── builders/
│   ├── pptx_builder.py        # python-pptx with native charts
│   ├── pdf_builder.py         # WeasyPrint HTML→PDF
│   ├── html_builder.py        # reveal.js + Chart.js assembly
│   ├── image_builder.py       # Playwright screenshots
│   ├── thumbnail_builder.py   # Quick previews
│   └── chart_builder.py       # Native charts (PPTX), Chart.js (HTML), Matplotlib (image)
├── templates/
│   ├── pptx/                  # Master .pptx templates per theme
│   ├── html/                  # reveal.js base templates
│   └── pdf/                   # PDF CSS templates
├── storage/
│   └── blob_storage.py        # Azure Blob upload/download
├── models/
│   └── render_models.py
└── config.py
```

---

## Crash-Proof Orchestrator (State Machine)

### Problem
If the server restarts mid-generation, the user loses progress.

### Solution
Persist generation state to MongoDB. On restart, resume from last saved phase.

```python
# app/services/orchestrator/state_machine.py

from enum import Enum
from datetime import datetime

class GenerationState(str, Enum):
    IDLE = "idle"
    RESEARCHING = "researching"
    OUTLINING = "outlining"
    GENERATING_CONTENT = "generating_content"
    FILLING_TEMPLATE = "filling_template"       # For template mode
    DESIGNING = "designing"
    RENDERING_PREVIEW = "rendering_preview"
    READY_FOR_EDITING = "ready_for_editing"     # User is in editor
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"

class GenerationStateMachine:
    def __init__(self, project_id: str, db, ws_manager):
        self.project_id = project_id
        self.db = db
        self.ws_manager = ws_manager
        self.current_state = GenerationState.IDLE

    async def transition_to(self, new_state: GenerationState, progress: int = 0, message: str = ""):
        self.current_state = new_state

        # PERSIST TO DB (survives server crash)
        await self.db.presentations.update_one(
            {"_id": self.project_id},
            {"$set": {
                "generation_state": new_state.value,
                "generation_progress": progress,
                "generation_message": message,
                "updated_at": datetime.utcnow(),
            }}
        )

        # STREAM TO FRONTEND (real-time progress)
        await self.ws_manager.broadcast(self.project_id, {
            "type": "progress",
            "state": new_state.value,
            "progress": progress,
            "message": message,
        })

    async def handle_failure(self, error: str, phase: str):
        await self.transition_to(GenerationState.FAILED, message=error)

        # LOG FOR OBSERVABILITY
        await self.db.generation_logs.insert_one({
            "presentation_id": self.project_id,
            "phase": phase,
            "error": error,
            "model_used": self._last_model,
            "provider": self._last_provider,
            "created_at": datetime.utcnow(),
        })

    async def can_resume(self) -> bool:
        """Check if a failed/interrupted generation can be resumed."""
        doc = await self.db.presentations.find_one({"_id": self.project_id})
        return doc and doc.get("generation_state") not in [
            GenerationState.COMPLETED.value,
            GenerationState.IDLE.value,
        ]

    async def resume(self):
        """Resume from last saved state after server restart."""
        doc = await self.db.presentations.find_one({"_id": self.project_id})
        last_state = doc.get("generation_state")

        # Skip already-completed phases
        if last_state == "researching":
            return self._run_from_research()
        elif last_state == "outlining":
            return self._run_from_outline()
        elif last_state == "generating_content":
            return self._run_from_content()
        # ... etc
```

---

## Observability (OpenTelemetry)

### Why
You need to know: which model failed? Which API returned empty? How long did each phase take?

### Implementation

```python
# app/services/observability.py

import structlog
from datetime import datetime

logger = structlog.get_logger()

class LLMCallTracker:
    """
    Logs every LLM and API call to generation_logs collection.
    Provides dashboard data for monitoring.
    """

    async def track_call(
        self,
        presentation_id: str,
        phase: str,           # "research" | "outline" | "content" | "design" | "render"
        model: str,           # "kimi-k2-thinking" | "deepseek-v3" | etc.
        provider: str,        # "azure" | "groq" | "cloudflare" | "serper" | etc.
        latency_ms: int,
        tokens_used: int,
        success: bool,
        error: Optional[str] = None,
    ):
        await self.db.generation_logs.insert_one({
            "presentation_id": presentation_id,
            "phase": phase,
            "model": model,
            "provider": provider,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "success": success,
            "error": error,
            "created_at": datetime.utcnow(),
        })

        if not success:
            logger.warning(
                "llm_call_failed",
                model=model, provider=provider, error=error,
                presentation_id=presentation_id,
            )

    async def get_provider_health(self) -> dict:
        """
        Returns success rate per provider in last hour.
        Feed this into a Grafana dashboard or admin endpoint.
        """
        pipeline = [
            {"$match": {"created_at": {"$gte": one_hour_ago}}},
            {"$group": {
                "_id": "$provider",
                "total": {"$sum": 1},
                "failures": {"$sum": {"$cond": [{"$eq": ["$success", False]}, 1, 0]}},
                "avg_latency": {"$avg": "$latency_ms"},
            }},
        ]
        return await self.db.generation_logs.aggregate(pipeline).to_list()
```

---

## Template Analytics (Learning Loop)

```python
# Tracks which layouts/themes users actually keep vs change
# Over time, improves default recommendations

{
    "template_id": "investor-pitch-v1",
    "total_uses": 347,
    "completion_rate": 0.72,          # 72% export after generation
    "avg_time_to_export": 480,        # seconds
    "most_edited_slides": [1, 4, 7],  # Slides users change most
    "layout_changes": {
        "slide_1": {"from": "title-hero", "to": "two-column", "count": 23},
        "slide_4": {"from": "bullets", "to": "chart", "count": 45},
    },
    "theme_switches": {
        "corporate-blue → minimal-mono": 18,
        "corporate-blue → bold-dark": 12,
    },
}

# Future: If users constantly switch slide 4 to "chart" layout,
# update the template to default to "chart" for that slide.
```

---

## Complete Directory Structure (v2)

```
server4/
├── main.py                              # FastAPI entry point
├── requirements.txt
├── .env
├── Dockerfile
├── celery_worker.py                     # Celery for async exports
│
├── app/
│   ├── __init__.py
│   ├── config.py                        # Pydantic Settings (all .env vars)
│   ├── database.py                      # MongoDB (Motor async)
│   ├── dependencies.py                  # FastAPI DI (auth, db, etc.)
│   │
│   ├── models/                          # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── presentation.py              # Presentation, CreateRequest, etc.
│   │   ├── slide.py                     # Slide, SlideVersion, SlideUpdate
│   │   ├── template.py                  # Template, TemplateFill, TemplateAnalytics
│   │   ├── theme.py                     # Theme, GeneratedTheme, ColorPalette
│   │   ├── research.py                  # ResearchResult, MarketAnalysis
│   │   ├── content.py                   # SlideContent, Outline, ChartData
│   │   ├── render.py                    # RenderedFile, ExportJob
│   │   └── user.py                      # User preferences
│   │
│   ├── routers/                         # FastAPI routes
│   │   ├── __init__.py
│   │   ├── presentations.py             # CRUD + history + duplicate
│   │   ├── generation.py                # AI generation (outline → slides)
│   │   ├── templates.py                 # Template library + template-based generation
│   │   ├── slides.py                    # Slide editing + layout change + undo/redo
│   │   ├── themes.py                    # Theme management + generative themes
│   │   ├── export.py                    # Export (PPTX, PDF, HTML, PNG)
│   │   ├── websocket.py                 # WS progress streaming
│   │   └── admin.py                     # Provider health dashboard
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orchestrator/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py          # Main pipeline coordination
│   │   │   ├── state_machine.py         # Crash-proof state (persisted to MongoDB)
│   │   │   ├── mcp_client.py            # MCP subprocess manager (stdio)
│   │   │   ├── progress_tracker.py      # WebSocket streaming
│   │   │   └── fallback_handler.py      # Cross-MCP fallback logic
│   │   │
│   │   ├── llm/                         # LLM abstraction layer
│   │   │   ├── __init__.py
│   │   │   ├── model_router.py          # Task-based routing (7 task types)
│   │   │   ├── azure_client.py          # GPT-4o-mini, DeepSeek, Kimi, Mistral
│   │   │   ├── groq_client.py           # 8-key round-robin
│   │   │   ├── cloudflare_client.py     # CF Workers fallback
│   │   │   └── base_client.py           # Abstract base
│   │   │
│   │   ├── observability.py             # LLM/API call tracking + provider health
│   │   │
│   │   └── storage/
│   │       └── blob_service.py          # Azure Blob Storage
│   │
│   ├── mcp/                             # 3 Specialized MCP Servers (v1)
│   │   ├── __init__.py
│   │   │
│   │   ├── brain_mcp/                  # MCP 1: Research + Content (merged)
│   │   │   ├── server.py
│   │   │   ├── tools.py                # 14 tools
│   │   │   ├── security/
│   │   │   │   └── prompt_sanitizer.py # Prompt injection prevention
│   │   │   ├── engines/
│   │   │   │   ├── search_engine.py    # Multi-provider search
│   │   │   │   ├── market_engine.py    # Census, FRED, World Bank
│   │   │   │   ├── news_engine.py      # NewsAPI, NewsData, Guardian
│   │   │   │   ├── social_engine.py    # Reddit, ProductHunt, YouTube
│   │   │   │   ├── financial_engine.py # Alpha Vantage, Finnhub, Polygon
│   │   │   │   ├── scraper_engine.py   # Firecrawl, Jina, httpx
│   │   │   │   └── academic_engine.py  # CORE, arXiv
│   │   │   ├── generators/
│   │   │   │   ├── outline_generator.py
│   │   │   │   ├── slide_generator.py
│   │   │   │   ├── batch_generator.py
│   │   │   │   ├── template_filler.py  # Template placeholder replacement
│   │   │   │   ├── chart_generator.py
│   │   │   │   └── notes_generator.py
│   │   │   ├── refiners/
│   │   │   │   ├── content_refiner.py
│   │   │   │   ├── narrative_checker.py
│   │   │   │   └── content_fitter.py   # Resize content for layout changes
│   │   │   ├── models/
│   │   │   │   ├── research_models.py
│   │   │   │   └── content_models.py
│   │   │   ├── prompts/
│   │   │   │   ├── research_planner.py
│   │   │   │   ├── data_synthesizer.py
│   │   │   │   ├── outline_system.py
│   │   │   │   ├── slide_system.py
│   │   │   │   ├── template_system.py
│   │   │   │   ├── refine_system.py
│   │   │   │   └── chart_system.py
│   │   │   └── config.py
│   │   │
│   │   ├── design_mcp/                 # MCP 2: Design + Generative Themes
│   │   │   ├── server.py
│   │   │   ├── tools.py                # 7 tools
│   │   │   ├── engines/
│   │   │   │   ├── theme_engine.py     # Generative + CRUD
│   │   │   │   ├── layout_solver.py
│   │   │   │   ├── layout_transition.py # Layout change logic
│   │   │   │   ├── color_engine.py     # HSL math (no LLM)
│   │   │   │   ├── chart_styler.py
│   │   │   │   ├── brand_engine.py
│   │   │   │   └── accessibility.py    # WCAG validation
│   │   │   ├── models/
│   │   │   │   └── design_models.py
│   │   │   └── config.py
│   │   │
│   │   └── render_mcp/                 # MCP 3: All Export Formats
│   │       ├── server.py
│   │       ├── tools.py                # 7 tools
│   │       ├── builders/
│   │       │   ├── pptx_builder.py     # python-pptx + native Excel charts
│   │       │   ├── pdf_builder.py      # WeasyPrint
│   │       │   ├── html_builder.py     # reveal.js + Chart.js
│   │       │   ├── image_builder.py    # Playwright screenshots
│   │       │   ├── thumbnail_builder.py
│   │       │   └── chart_builder.py    # Native PPTX charts, Chart.js, Matplotlib
│   │       ├── templates/
│   │       │   ├── pptx/              # Master .pptx per theme
│   │       │   ├── html/              # reveal.js templates
│   │       │   └── pdf/               # PDF CSS
│   │       ├── storage/
│   │       │   └── blob_storage.py
│   │       ├── models/
│   │       │   └── render_models.py
│   │       └── config.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── auth.py                      # JWT validation (DI pattern from Server1)
│   │   └── rate_limiter.py
│   │
│   └── middleware/
│       ├── __init__.py
│       ├── cors.py
│       ├── rate_limit.py
│       └── auth_middleware.py
│
└── tests/
    ├── test_orchestrator.py
    ├── test_brain_mcp.py
    ├── test_design_mcp.py
    ├── test_render_mcp.py
    ├── test_editing.py
    └── test_templates.py
```

---

## Implementation Phases (Revised — Magic First)

### Phase 1: Foundation + Orchestrator Skeleton (Week 1)
**Goal:** FastAPI boots, auth works, state machine persists, WebSocket streams progress.

Build the **glue** before the muscles:
1. `app/config.py` — Pydantic Settings loading all .env vars
2. `app/database.py` — MongoDB Motor async + collection indexes
3. `app/models/` — All Pydantic schemas (presentation, slide, template, theme)
4. `app/utils/auth.py` — JWT validation (copy pattern from Server1)
5. `app/middleware/` — CORS, auth, rate limiting
6. `app/services/orchestrator/state_machine.py` — Crash-proof state
7. `app/services/orchestrator/mcp_client.py` — Subprocess MCP manager
8. `app/services/orchestrator/progress_tracker.py` — WebSocket streaming
9. `app/services/llm/` — Complete LLM abstraction (all 6 tiers)
10. `app/routers/websocket.py` — Progress endpoint
11. Basic health + presentations CRUD router

**Deliverable:** Server starts, auth works, state machine persists to MongoDB, LLM routing works.

### Phase 2: Brain MCP — "Topic → Slides" Magic (Week 2-3)
**Goal:** Type a topic, get real slides with real data. THE magic moment.

1. `brain_mcp/engines/search_engine.py` — Serper round-robin + Tavily + SerpAPI
2. `brain_mcp/engines/market_engine.py` — FRED + Census + World Bank
3. `brain_mcp/generators/outline_generator.py` — Kimi-K2 / DeepSeek outlines
4. `brain_mcp/generators/slide_generator.py` — Per-slide content with routing
5. `brain_mcp/generators/batch_generator.py` — Parallel generation
6. `brain_mcp/generators/chart_generator.py` — Chart data
7. `brain_mcp/prompts/` — All system prompts
8. `brain_mcp/security/prompt_sanitizer.py`
9. `brain_mcp/server.py` + `tools.py`
10. `app/services/orchestrator/orchestrator.py` — Full pipeline wiring
11. `app/routers/generation.py` — Generation endpoints
12. `app/services/observability.py` — Call tracking

**Deliverable:** `POST /api/generate/outline` → `POST /api/generate/slides` → real content with research data.

### Phase 3: Render MCP — Actual Files (Week 3-4)
**Goal:** Slides export to PPTX and PDF. User gets downloadable files.

1. `render_mcp/builders/pptx_builder.py` — python-pptx with native charts
2. `render_mcp/builders/pdf_builder.py` — WeasyPrint
3. `render_mcp/builders/thumbnail_builder.py` — Quick previews
4. `render_mcp/builders/chart_builder.py` — Native PPTX charts + Matplotlib
5. `render_mcp/storage/blob_storage.py` — Azure Blob upload
6. `render_mcp/server.py` + `tools.py`
7. `app/routers/export.py` — Export endpoints
8. Celery task for async heavy exports

**Deliverable:** Topic → Research → Slides → Download .pptx/.pdf. End-to-end works.

### Phase 4: Design MCP — Make It Beautiful (Week 4-5)
**Goal:** Generative themes, layout solving, accessibility validation.

1. `design_mcp/engines/color_engine.py` — HSL palette generation
2. `design_mcp/engines/theme_engine.py` — Generative themes + 8 built-ins
3. `design_mcp/engines/layout_solver.py` — Layout constraints
4. `design_mcp/engines/layout_transition.py` — Layout switching
5. `design_mcp/engines/accessibility.py` — WCAG validation
6. `design_mcp/server.py` + `tools.py`
7. `app/routers/themes.py` — Theme endpoints
8. Seed built-in themes to MongoDB

**Deliverable:** Slides get proper theming, layouts, validated for accessibility.

### Phase 5: Editing + Templates (Week 5-6)
**Goal:** Slide editor API + template library + undo/redo.

1. `app/routers/slides.py` — Edit, layout change, undo/redo, reorder, add/delete
2. Slide versioning system (slide_versions collection)
3. `brain_mcp/generators/template_filler.py` — Template placeholder replacement
4. `brain_mcp/refiners/content_fitter.py` — Resize content for layout changes
5. `app/routers/templates.py` — Template CRUD + template-based generation
6. Seed 8 built-in templates to MongoDB
7. AI-assisted editing endpoints (rewrite, expand, summarize, translate)
8. Template analytics tracking

**Deliverable:** Full editing flow + template generation mode.

### Phase 6: Premium Features + Polish (Week 6-7)
**Goal:** Image generation, HTML export, speaker notes, brand specs.

1. Image Generation MCP (Flux-Pro-2 + CF fallback) — add as 4th MCP
2. `render_mcp/builders/html_builder.py` — reveal.js + Chart.js
3. `render_mcp/builders/image_builder.py` — Playwright PNG export
4. Speaker notes generation (Brain MCP already has the tool)
5. Brand spec application (Design MCP already has the tool)
6. Admin dashboard endpoint for provider health
7. End-to-end integration tests

### Phase 7: Frontend Integration (Week 7-8)
**Goal:** Connect real backend to existing frontend module.

1. Add `VITE_API_BASE_URL4` to frontend env config
2. Replace `generateMockSlides()` with real API calls
3. Connect WebSocket progress streaming
4. Connect export endpoints (real file downloads)
5. Add template browser UI in mode selection
6. Real presentation persistence (remove localStorage fallback)
7. Layout change dropdown in slide editor
8. Undo/redo buttons in editor

---

## Caching Strategy

```
Redis Cache Layers:
├── Research Cache (TTL: 30 min)     — Same topic → skip web search
├── Outline Cache (TTL: 1 hour)      — Same inputs → skip regeneration
├── Theme Cache (TTL: 24 hours)      — Theme definitions
├── Render Cache (TTL: 1 hour)       — Same slides+theme → skip re-render
├── Template Cache (TTL: 24 hours)   — Template definitions
└── Provider Health (TTL: 5 min)     — API health status for routing decisions
```

---

## Groq 8-Key Round-Robin

```python
class GroqRoundRobin:
    KEYS = [os.getenv(f"VITE_GROQ_API_KEY{i}") for i in ["", "1", "2", "3", "4", "5", "6", "7"]]

    async def complete(self, messages, model="llama-3.3-70b-versatile"):
        for attempt in range(len(self.KEYS)):
            key = self.KEYS[self._current_index]
            self._current_index = (self._current_index + 1) % len(self.KEYS)
            try:
                return await self._call_groq(key, messages, model)
            except RateLimitError:
                continue
        return await self._fallback_gpt4o_mini(messages)  # All keys exhausted
```

---

## Requirements (Updated)

```txt
# Core
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-multipart>=0.0.6
httpx>=0.27.0
websockets>=12.0

# MCP
mcp[cli]>=1.0.0

# LLM Clients
openai>=1.50.0                    # Azure OpenAI (GPT-4o-mini, DeepSeek, Kimi, Mistral)
groq>=0.9.0                       # Groq 8-key round-robin
huggingface-hub>=0.20.0           # Local model fallback

# Database & Cache
motor>=3.3.0                      # Async MongoDB driver
redis>=5.0.0
celery[redis]>=5.3.0

# PPTX / PDF / HTML Generation
python-pptx>=0.6.23               # PowerPoint with native charts
weasyprint>=61.0                   # PDF generation
Pillow>=10.2.0                     # Image processing
playwright>=1.41.0                 # HTML→PNG rendering
matplotlib>=3.8.0                  # Chart images for PDF/PNG
jinja2>=3.1.0                      # HTML template rendering

# Research APIs
tavily-python>=0.3.0
firecrawl-py>=0.0.16
exa-py>=1.0.0

# Storage
azure-storage-blob>=12.19.0

# Auth & Security
python-jose[cryptography]>=3.3.0

# Observability
structlog>=24.1.0                  # Structured logging

# Utilities
aiofiles>=23.2.0
tenacity>=8.2.0                    # Retry with backoff
```

---

## Summary: What Changed from v1 Plan

| Area | v1 Plan | v2 (Founder's Cut) |
|------|---------|-------------------|
| MCPs | 5 separate MCPs | **3 MCPs** (Brain, Design, Render) — merged Research+Content |
| Deployment | Implied multi-container | **Single Docker container**, MCPs as stdio subprocesses |
| Templates | Not mentioned | **Full template system** with AI placeholder replacement |
| Editing | Not mentioned | **Complete editing API** with layout change, undo/redo |
| Layout | Not mentioned | **12 layout types** with transition logic + content fitting |
| Themes | Static JSON files | **Generative themes** from brand colors (HSL math) |
| Charts | Static images only | **Native Excel-backed PPTX charts** (editable!) + Chart.js for HTML |
| State | In-memory | **MongoDB-persisted** state machine (crash-proof) |
| Data model | Embedded slides in one doc | **Normalized** (presentations + slides + versions collections) |
| Observability | None | **generation_logs** collection + provider health dashboard |
| Security | None | **PromptSanitizer** for injection prevention |
| Versioning | None | **Per-slide version history** with undo/redo |
| Template learning | None | **template_analytics** tracking layout changes + theme switches |
| Phase order | Research first | **Orchestrator first**, then Brain MCP for "magic first" validation |
| Export | Mostly HTML/reveal.js | **PPTX primary**, PDF second, HTML+PNG Premium |
