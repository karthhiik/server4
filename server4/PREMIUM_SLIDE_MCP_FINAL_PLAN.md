# 🎯 Premium Slide Generation MCP — Final Comprehensive Plan
## Version 3.0 — World-Class Standalone MCP Server for AI Presentation Generation

---

## Executive Summary

This is a **real-world production-grade MCP server** designed to be the world's most advanced slide generation system. Built on deep research of 30+ GitHub repositories, multiple reference plans, and current industry best practices, this MCP integrates:

1. **Office-PowerPoint-MCP-Server** (1,610⭐) — exhaustive PPTX manipulation with 34+ tools
2. **GStack Framework** — persistent browser-daemon for live preview & QA
3. **Presenton Architecture** — multi-provider LLM, local/Ollama support, API-first
4. **PPTist Canvas** — full WYSIWYG web editor with element-level control
5. **Multi-Agent Orchestration** — Supervisor-Worker pattern with 5 specialized agents

**Key Differentiator**: This is NOT a simple PPTX wrapper. It's a **standalone engineering team** that researches, designs, generates, reviews, and exports presentations autonomously — with built-in quality gates, brand compliance, and real-time preview.

---

## 🔬 Gap Analysis — What Both Plans Identified

### From ChatGPT Plan (MCP_chatgpt_plan.md):
| Gap | Description |
|-----|-------------|
| G1 | No true multi-agent orchestration (only single-prompt pipelines) |
| G2 | Limited real-time collaboration |
| G3 | Weak offline/local-first capabilities |
| G4 | No integrated design QA (contrast, brand compliance) |
| G5 | No canvas editing with AI assistance |
| G6 | Quality guards are basic/absent |

### From Gemini Plan (MCP_plan_from gemmin_ai.md):
| Gap | Description |
|-----|-------------|
| G7 | No persistent browser session for live preview (GStack missing) |
| G8 | No intelligent layout selection (AI Template Selector) |
| G9 | No auto-layout engine with text fitting |
| G10 | No four professional color schemes built-in |
| G11 | No deployment archetypes (Pitch Deck, Consulting, Academic) |
| G12 | No security layers (local context isolation, audit logging) |

### Combined Gaps to Address:
**12 critical gaps** that make existing solutions incomplete. This plan addresses ALL of them.

---

## 🏗️ Final Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     PREMIUM SLIDE GENERATION MCP SERVER                            │
│                                                                                     │
│   Protocol: Model Context Protocol (MCP) — JSON-RPC over stdio/HTTP+SSE           │
│   Framework: FastMCP (FastAPI) + GStack Daemon                                    │
│   Language: Python 3.11+ (Production Grade)                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        ▼                                 ▼                                 ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   ORCHESTRATOR       │   │   AGENT SWARM        │   │   DESIGN ENGINE      │
│   (Supervisor)       │   │   (5 Specialized)     │   │   (Theme + Quality)   │
│                       │   │                       │   │                       │
│ • Task Decomposition  │   │ • CEO/Strategist     │   │ • Theme System       │
│ • Agent Coordination  │   │ • Researcher/Analyst │   │ • 40+ Built-in        │
│ • Context Management │   │ • Designer/Creative  │   │ • Custom Brand       │
│ • Quality Gates      │   │ • Assembler/Engineer  │   │ • AI Template Select │
│ • Error Recovery     │   │ • QA Lead/Reviewer    │   │ • Auto-Layout Engine │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
        │                                 │                                 │
        ▼                                 ▼                                 ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   KNOWLEDGE LAYER    │   │   TOOL LAYER          │   │   RENDER LAYER       │
│   (Storage + RAG)    │   │   (40+ MCP Tools)     │   │   (Multi-Format)     │
│                       │   │                       │   │                       │
│ • Vector Store       │   │ • Presentation CRUD  │   │ • HTML/Tailwind      │
│ • Document Store    │   │ • Slide Operations   │   • PPTX (python-pptx) │
│ • Object Storage    │   │ • Content Generation │   • PDF (WeasyPrint)   │
│ • Redis Cache       │   │ • Image Generation   │   • Canvas (Web)      │
│ • File System       │   │ • Chart/Table/Shape  │   • Images Export     │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │   GStack DAEMON (Browser)       │
                         │   (Persistent Session)           │
                         │                                 │
                         │ • Live Preview Rendering        │
                         │ • Visual QA & Layout Verification│
                         │ • Screenshot Capture            │
                         │ • Interactive Element Testing   │
                         └─────────────────────────────────┘
```

---

## 🤖 Agent System — Full Implementation

### Agent 1: CEO / Strategist Agent
**Purpose**: Narrative blueprinting, validates presentation necessity
- **Skills**: `/office-hours`, `/plan-ceo-review`
- **Framework**: SCQA, Pyramid Principle
- **Tools**: analyze_presentation, validate_strategy
- **Workflow**:
  1. Challenge premise: "Why this presentation?"
  2. Determine archetype: Pitch Deck / Consulting / Academic / Report
  3. Define narrative arc: Problem-Solution, Timeline, Comparison
  4. Output: Strategic Outline with purpose and audience

### Agent 2: Researcher / Analyst Agent
**Purpose**: Gather source-backed evidence and data
- **Skills**: WebSearch, RAG retrieval, document extraction
- **Framework**: Grounded Research, Fact-Checking
- **Tools**: research_topic, extract_document, search_web, analyze_data
- **Workflow**:
  1. Generate search queries from topic
  2. Execute parallel web searches (Tavily, DuckDuckGo)
  3. Parse uploaded documents (PDF/DocX/PPT/Excel)
  4. Ingest to vector DB for similarity search
  5. Synthesize with citations and data points

### Agent 3: Designer / Creative Agent
**Purpose**: Visual identity, theme application, layout optimization
- **Skills**: Theme selection, color theory, visual hierarchy
- **Framework**: Cognitive Load Theory, Visual Hierarchy
- **Tools**: apply_theme, generate_theme, analyze_design_quality, list_themes
- **Workflow**:
  1. Select theme based on industry/style (40+ built-in)
  2. Apply color scheme (4 professional palettes)
  3. Optimize layout per slide (AI Template Selector)
  4. Place visuals and ensure brand compliance
  5. Run accessibility checks (contrast ≥4.5:1)

### Agent 4: Assembler / Engineer Agent
**Purpose**: Programmatic building of PPTX file
- **Framework**: Open XML Standards, python-pptx
- **Tools**: create_presentation, add_slide, add_chart, add_table, add_image
- **Workflow**:
  1. Initialize presentation with template
  2. Add slides with master layouts
  3. Populate content with placeholders
  4. Insert charts, tables, shapes
  5. Apply styling (fonts, colors, spacing)
  6. Set core properties (title, author, keywords)

### Agent 5: QA Lead / Reviewer Agent
**Purpose**: Quality assurance, visual verification, brand audit
- **Skills**: `/qa`, `/browse` (GStack), visual testing
- **Framework**: E2E Testing, Aesthetic Audits
- **Tools**: browse, snapshot, screenshot, validate_content
- **Workflow**:
  1. Render presentation in headless browser
  2. Capture screenshots via GStack daemon
  3. Verify layout integrity (no overlap, proper alignment)
  4. Check for "AI slop" patterns
  5. Validate content against quality gates
  6. Report issues for revision

---

## 🔧 Complete MCP Tool Specification (45 Tools)

### Category 1: Presentation Lifecycle (6 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `create_presentation` | name, template_path | Initialize new PPTX with optional template |
| `open_presentation` | file_path | Round-trip editing of existing files |
| `save_presentation` | output_path, format | Export to PPTX/PDF/images |
| `get_presentation_info` | presentation_id | Metadata, slide count, statistics |
| `set_core_properties` | title, author, keywords | Enterprise document properties |
| `delete_presentation` | presentation_id | Remove presentation |

### Category 2: Slide Operations (8 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `add_slide` | layout_index, bg_color | Add slide with master layout |
| `delete_slide` | slide_index | Remove slide |
| `reorder_slides` | slide_ids | Reorder slide sequence |
| `duplicate_slide` | slide_index | Clone slide with content |
| `set_slide_background` | slide_index, color/image | Background customization |
| `get_slide_content` | slide_index | Extract text for summarization |
| `set_transition` | slide_index, effect, duration | Animation transitions |
| `set_notes` | slide_index, notes | Speaker notes |

### Category 3: Content & Text (6 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `populate_placeholder` | slide_index, placeholder_name, text | Fill placeholder content |
| `add_bullet_points` | slide_index, bullets, level | Multi-level bullet lists |
| `manage_text` | slide_index, element_id, text_runs | Bold, font, color formatting |
| `add_text_box` | slide_index, text, position, size | Free-position text |
| `find_replace` | slide_index, find, replace | Batch text replacement |
| `extract_slide_text` | slide_index | Read content for AI analysis |

### Category 4: Visual Elements (8 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `add_image` | slide_index, image_path, position | Insert images |
| `add_shape` | slide_index, type, position, size | Flowcharts, arrows, polygons |
| `add_chart` | slide_index, type, data, theme | Bar, Pie, Line, Column, Area |
| `add_table` | slide_index, rows, cols, data | Styled tables |
| `apply_picture_effects` | element_id, effects | Shadows, reflections, frames |
| `crop_image` | element_id, bounds | Image cropping |
| `set_shape_style` | element_id, fill, line, effects | Shape styling |
| `add_hyperlink` | element_id, url, tooltip | Hyperlinks |

### Category 5: Theme & Design (5 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `apply_theme` | presentation_id, theme_id | Apply built-in or custom theme |
| `generate_theme` | brand_colors, industry, style | AI-generated custom theme |
| `create_custom_theme` | theme_config | User-defined theme |
| `list_themes` | category, search | Browse available themes |
| `extract_theme` | pptx_path | Extract theme from existing file |

### Category 6: Image Generation (4 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `generate_image` | prompt, provider, style | AI image generation |
| `generate_hero_image` | presentation_id, topic | Main presentation image |
| `search_stock_images` | query, count | Stock photo search |
| `upload_custom_image` | file_path | User-provided images |

### Category 7: Research & Data (4 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `research_topic` | topic, depth, sources | Comprehensive research |
| `extract_document` | file_path, file_type | Parse PDF/Word/Excel |
| `search_web` | query, num_results | Web search |
| `analyze_data` | data_source, analysis_type | Data visualization prep |

### Category 8: Quality & Validation (4 tools)
| Tool | Parameters | Description |
|------|------------|-------------|
| `validate_content` | content, rules | Content quality check |
| `check_branding` | presentation_id, brand_guidelines | Brand compliance |
| `validate_sources` | content | Citation verification |
| `get_improvements` | presentation_id | AI-suggested fixes |

---

## 🎨 Theme System — Premium Design Intelligence

### 4 Professional Color Schemes (Built-in)

| Theme | Primary | Secondary | Accent | Use Case |
|-------|---------|-----------|--------|----------|
| **Modern Blue** | #0078D4 | #106EBE | #FFB900 | Tech, SaaS, Corporate |
| **Corporate Gray** | #605E5C | #323130 | #0078D4 | Consulting, Finance |
| **Elegant Green** | #107C10 | #0B6A43 | #00B294 | Sustainability, Services |
| **Warm Red** | #D83B01 | #A4262C | #FF8C00 | Sales, Visionary Pitches |

### 40+ Built-in Themes
Categories: Corporate, Creative, Educational, Startup, Nature, Academic

### Theme Configuration Model
```python
class Theme(BaseModel):
    id: str
    name: str
    colors: ThemeColors  # primary, secondary, accent, background, text
    fonts: ThemeFonts    # heading, body, accent
    layouts: Dict[str, LayoutConfig]
    effects: ThemeEffects  # animations, transitions
    industries: List[str]
    is_builtin: bool
```

### AI Template Selector (Intelligent Layout Selection)
- Analyzes content structure before choosing layout
- Comparison detected → Two-Column layout
- Timeline detected → Process layout with arrows
- Data points → Chart layout
- Team members → Grid layout

### Auto-Layout Engine (Text Fitting)
- Calculates if text will overflow container
- Auto-reduces font size or suggests rewording
- Proactive design assistance for zero manual formatting

---

## 🔄 Quality Gates — Comprehensive Validation

### Content Quality Rules
| Rule | Action |
|------|--------|
| Fluff detection | Block: "revolutionary", "cutting-edge", "game-changing" |
| Source requirement | All data points require citation |
| Density check | Max 6 bullets/slide, 15 words/bullet |
| Investor requirements | TAM/SAM/SOM for market slides |

### Design Quality Rules
| Rule | Action |
|------|--------|
| Contrast ratio | ≥4.5:1 for readability |
| Font consistency | Same fonts across all slides |
| Image resolution | ≥1920×1080 |
| Spacing uniformity | Consistent margins and padding |

### Brand Compliance
| Check | Action |
|-------|--------|
| Color palette | Verify against brand guidelines |
| Logo placement | Check positioning rules |
| Typography | Match brand fonts |
| Tone alignment | Match brand voice |

---

## 🔐 Security Architecture — Enterprise Grade

### Layer 1: Local Context Isolation
- MCP server runs locally (stdio transport)
- Sensitive data processed locally
- Only summaries sent to LLM

### Layer 2: GStack Browser Security
- `localhost-only` binding (no external access)
- Bearer token authentication
- Encrypted cookie management
- 30-minute idle timeout

### Layer 3: Governance & Auditing
- Every tool invocation logged
- STRIDE/OWASP audit capability
- PII detection in generated content

### Layer 4: API Key Management
- Environment variable only
- "Bring Your Own Key" (BYOK) for users
- No hardcoded credentials

---

## 📦 Storage Architecture

| Storage Type | Technology | Purpose |
|--------------|------------|---------|
| Vector Store | Chroma / Pinecone | Presentation embeddings, similarity search |
| Document Store | MongoDB / PostgreSQL | Presentations, slides, themes |
| Object Storage | S3 / MinIO | Generated images, exported files |
| Cache | Redis | LLM responses, theme configs, sessions |
| File System | Local / Network | Template assets, working files |

---

## 🚀 Implementation Phases (12 Weeks)

### Phase 1: Foundation (Weeks 1-2)
- [ ] FastMCP server setup with stdio/HTTP transport
- [ ] 34 core tools from Office-PowerPoint-MCP-Server
- [ ] Basic presentation CRUD operations
- [ ] PPTX export via python-pptx

### Phase 2: Agent System (Weeks 3-4)
- [ ] Orchestrator implementation (Supervisor-Worker pattern)
- [ ] CEO/Strategist Agent with office-hours skill
- [ ] Researcher/Analyst Agent with RAG integration
- [ ] Basic quality gates for content

### Phase 3: Design Intelligence (Weeks 5-6)
- [ ] Designer/Creative Agent implementation
- [ ] 40+ built-in themes with 4 color schemes
- [ ] AI Template Selector (intelligent layout)
- [ ] Auto-Layout Engine with text fitting
- [ ] Brand compliance checking

### Phase 4: Assembly & Rendering (Weeks 7-8)
- [ ] Assembler/Engineer Agent implementation
- [ ] HTML/Tailwind rendering for web preview
- [ ] PDF export with proper styling
- [ ] Image export (PNG, JPG)

### Phase 5: GStack Integration (Weeks 9-10)
- [ ] QA Lead/Reviewer Agent
- [ ] GStack daemon for persistent browser session
- [ ] Live preview rendering
- [ ] Visual QA with screenshot capture
- [ ] Layout verification

### Phase 6: Production Ready (Weeks 11-12)
- [ ] Error handling and retry logic
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation
- [ ] Deployment scripts

---

## 📈 Success Metrics

| Metric | Target |
|--------|--------|
| JSON validity from LLM | >95% |
| Image generation success | >90% (with fallback) |
| Export success rate | >99% |
| Quality pass rate | >85% first attempt |
| Content generation time | ≤5s/slide |
| Full deck generation | <60s for 10 slides |
| Browser session latency | <1s per command |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| MCP Framework | FastMCP (FastAPI) |
| LLM Clients | OpenAI, Claude, Gemini, Ollama, Groq |
| Vector DB | Chroma / Pinecone |
| Document DB | MongoDB / PostgreSQL |
| Cache | Redis |
| Storage | S3 / MinIO |
| PPTX | python-pptx |
| HTML Render | Tailwind CSS + Custom |
| Browser | Playwright (GStack) |
| Testing | pytest, pytest-asyncio |

---

## 📋 Deployment Archetypes

### 1. Investor Pitch Deck (Venture)
- CEO Agent: Problem-Solution-Market flow
- Designer: High-end visuals for "Future Outlook"
- Charts: TAM/SAM/SOM with professional styling

### 2. Strategic Consulting Deck (Enterprise)
- Analyst: Data density and clarity
- Tables: Competitive landscape
- QA: Speaker notes with evidence

### 3. Academic/Technical Defense (Research)
- LaTeX equation support (via Reveal.js)
- Readability audit for accessibility
- Precision-focused layout

### 4. Quarterly Report (Corporate)
- Financial charts and KPIs
- Executive summary emphasis
- Brand-compliant styling

---

## 🔄 Integration with Existing Server4

This MCP is designed to **integrate seamlessly** with the existing Server4 architecture:

```
Existing Server4          →    New Slide Generation MCP
─────────────────────           ─────────────────────────
/api/generate/ai         →    Uses MCP for content generation
orchestrator.py         →    Coordinates MCP agents
theme_engine.py         →    Expanded to 40+ themes
layout_solver.py        →    AI Template Selector
image_service.py        →    Multi-provider image generation
html_builder.py         →    Integrated into Render layer
pptx_builder.py          →    Uses MCP tools for assembly
```

---

## 🎯 Differentiation Summary

| Feature | Our MCP | Others |
|---------|---------|--------|
| **Agent Orchestration** | 5 specialized agents | Single prompt |
| **GStack Integration** | Persistent browser, live QA | None |
| **Theme System** | 40+ built-in, AI selector | 5-10 basic |
| **Quality Gates** | Content + Design + Brand | Basic |
| **Auto-Layout** | Text fitting, intelligent | None |
| **Security** | Local isolation, audit | Cloud only |
| **Offline** | Ollama support | Limited |
| **Format Support** | PPTX/PDF/HTML/Canvas | PPTX only |

---

## 📝 Next Steps

1. Initialize the MCP server project
2. Implement the 34 core tools from Office-PowerPoint-MCP-Server
3. Integrate GStack browse daemon
4. Build agent orchestration layer
5. Create theme system with 40+ themes
6. Implement quality gates
7. Test with real-world presentation scenarios
8. Deploy and iterate

---

**Document Version**: 3.0 (Final)
**Created**: 2026-04-02
**Status**: Ready for Implementation
**Architecture**: Production-Grade MCP Server with Multi-Agent Orchestration