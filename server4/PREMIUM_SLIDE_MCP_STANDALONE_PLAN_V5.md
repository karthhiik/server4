# Premium Slide Generation MCP — Standalone Implementation Plan

## Version 5.0 — Complete Standalone Architecture

**Document Version**: 5.0 (Standalone Implementation Plan)
**Created**: 2026-04-02
**Status**: Ready for Implementation
**Architecture**: Production-Grade MCP Server with 6 Specialized Agents + Reflective Loop

---

## Table of Contents

1. Executive Summary
2. Architecture Overview
3. Agent System (6 Specialized Agents)
4. Slide DSL Specification
5. Technology Stack
6. PreTeXt Integration Architecture
7. Reflective Generation Loop
8. Visual Style Discovery System
9. Pitch Deck Domain Intelligence
10. Enhanced Export Pipeline
11. Agent Communication Protocol
12. Tool Specification (55+ Tools)
13. Theme System (16 Color Schemes + 12 Style Presets)
14. Implementation Phases (14 Weeks)
15. Success Metrics
16. Risk Assessment
17. Differentiation Summary

---

## 1. Executive Summary

This is a **complete standalone implementation plan** for a world-class Premium Slide Generation MCP Server. The plan addresses 18 critical gaps identified through:

1. Deep research of 30+ GitHub repositories
2. Analysis of YC/Sequoia pitch deck best practices
3. DocSend investor behavior analytics
4. Evaluation of PreTeXt, OpenPencil, yoyo-evolve reference repositories
5. Frontend Slides pattern analysis (visual style discovery)

### Key Differentiators

- **6 Specialized Agents** including new Code Agent for React/Tailwind generation
- **Reflective Generation Loop** (PPTAgent V2 inspired) with 2-3 iteration cycles
- **PreTeXt DOM-free text measurement** for precise layout validation
- **Visual Style Discovery UX** (3 preview options, user selects)
- **Pitch Deck Domain Intelligence** encoding YC/Sequoia/DocSend rules
- **Anti-AI-Slop Design** via 12 curated style presets

### Technology Foundation

Based on reference analysis:
- **PreTeXt** (32.2k⭐): DOM-free text measurement, two-phase API (prepare/layout)
- **OpenPencil** (3.9k⭐): 90+ MCP tools, Yoga WASM layout, design-to-code export
- **yoyo-evolve** (1.4k⭐): Multi-provider support (12 providers), subagent pattern, streaming REPL

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     PREMIUM SLIDE GENERATION MCP SERVER                            │
│                                                                                     │
│   Protocol: Model Context Protocol (MCP) — JSON-RPC over stdio/HTTP+SSE          │
│   Framework: FastMCP (FastAPI) + Node.js Code Agent                               │
│   Language: Python 3.11+ (Core) + TypeScript (Code Agent)                         │
│   Storage: Chroma (Vector) + MongoDB (Document) + Redis (Cache)                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   ORCHESTRATOR       │   │   AGENT SWARM        │   │   DESIGN ENGINE      │
│   (Supervisor)       │   │   (6 Specialized)     │   │   (Theme + Quality)  │
│                       │   │                       │   │                       │
│ • Task Decomposition  │   │ 1. CEO/Strategist    │   │ • Theme System       │
│ • Agent Coordination  │   │ 2. Researcher/Analyst │   │ • 16 Color Schemes   │
│ • Context Management  │   │ 3. Designer/Creative │   │ • 12 Style Presets   │
│ • Quality Gates       │   │ 4. Assembler/Engineer│   │ • Visual Discovery   │
│ • Reflective Loop     │   │ 5. Code Agent (NEW)  │   │ • PreTeXt Validation │
│ • Error Recovery     │   │ 6. QA Lead/Reviewer   │   • Anti-AI-Slop      │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
        │                                   │                                   │
        ▼                                   ▼                                   ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   KNOWLEDGE LAYER    │   │   TOOL LAYER          │   │   RENDER LAYER       │
│   (Storage + RAG)    │   │   (55+ MCP Tools)    │   │   (Multi-Format)     │
│                       │   │                       │   │                       │
│ • Chroma Vector Store│   │ • Presentation CRUD   │   │ • React Components   │
│ • MongoDB Documents  │   │ • Slide Operations   │   │ • PPTX (PptxGenJS)   │
│ • Redis Cache        │   │ • Content Generation │   │ • PDF (Puppeteer)    │
│ • File System        │   │ • Image Generation   │   │ • HTML (Zero-dep)    │
│                       │   │ • Code Agent Tools   │   │ • Google Slides      │
│                       │   │ • Diagram Integration│   │ • Images Export     │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
                                            │
                                            ▼
                          ┌─────────────────────────────────┐
                          │   BROWSER DAEMON               │
                          │   (Playwright-based)           │
                          │                                 │
                          │ • Live Preview Rendering        │
                          │ • Visual QA & Screenshots      │
                          │ • Layout Verification          │
                          │ • PreTeXt Client Validation    │
                          └─────────────────────────────────┘
```

---

## 3. Agent System (6 Specialized Agents)

### Agent 1: CEO / Strategist Agent

**Purpose**: Narrative blueprinting, validates presentation necessity
- **Framework**: SCQA, Pyramid Principle, YC Pitch Deck Structure
- **Tools**: analyze_presentation, validate_strategy, select_archetype
- **Workflow**:
  1. Challenge premise: "Why this presentation?"
  2. Determine archetype: Pitch Deck / Consulting / Academic / Report / Sales
  3. Define narrative arc: Problem-Solution, Timeline, Comparison
  4. Activate Pitch Deck Domain Intelligence if investor deck
  5. Output: Strategic Outline with purpose, audience, slide order

### Agent 2: Researcher / Analyst Agent

**Purpose**: Gather source-backed evidence and data
- **Framework**: Grounded Research, Fact-Checking
- **Tools**: research_topic, extract_document, search_web, analyze_data, validate_sources
- **Workflow**:
  1. Generate search queries from topic
  2. Execute parallel web searches
  3. Parse uploaded documents (PDF/DocX/PPT/Excel)
  4. Ingest to vector DB for similarity search
  5. Synthesize with citations and data points

### Agent 3: Designer / Creative Agent

**Purpose**: Visual identity, theme application, layout optimization
- **Framework**: Cognitive Load Theory, Visual Hierarchy, Anti-AI-Slop
- **Tools**: apply_theme, generate_theme, analyze_design_quality, list_themes, discover_style
- **Workflow**:
  1. Activate Visual Style Discovery (generate 3 previews)
  2. User selects preferred style
  3. Apply color scheme (16 built-in palettes)
  4. Optimize layout per slide (AI Template Selector)
  5. Run accessibility checks (contrast ≥4.5:1)
  6. Apply anti-AI-slop processing

### Agent 4: Assembler / Engineer Agent

**Purpose**: Programmatic building of PPTX file using python-pptx
- **Framework**: Open XML Standards
- **Tools**: create_presentation, add_slide, add_chart, add_table, add_image
- **Workflow**:
  1. Initialize presentation with template
  2. Add slides with master layouts
  3. Populate content with placeholders
  4. Insert charts, tables, shapes
  5. Apply styling (fonts, colors, spacing)
  6. Set core properties

### Agent 5: Code Agent (NEW - Primary Addition)

**Purpose**: Generate React/Tailwind slide components, multi-format export
- **Framework**: Component-Driven Architecture, Slide DSL
- **Tools**: generate_slide_dsl, compile_react_slides, measure_text_fit, validate_slide_dsl, export_to_pptx, export_to_pdf, export_to_html, generate_diagram, preview_slides, apply_anti_slop
- **Workflow**:
  1. Receive content from CEO + Researcher
  2. Generate Slide DSL (structured JSON)
  3. PreTeXt validation for text fitting
  4. Compile to React components with Tailwind
  5. Apply anti-AI-slop styling
  6. Add interactive elements (diagrams, charts)
  7. Multi-format export (PPTX, PDF, HTML, React)

### Agent 6: QA Lead / Reviewer Agent

**Purpose**: Quality assurance, visual verification, reflective iteration
- **Framework**: E2E Testing, Aesthetic Audits, Reflective Loop
- **Tools**: validate_content, check_branding, validate_sources, get_improvements, browse, snapshot, screenshot
- **Workflow**:
  1. Render presentation in browser
  2. Capture screenshots for visual QA
  3. Verify layout integrity (PreTeXt + visual)
  4. Check for anti-AI-slop compliance
  5. Validate content against quality gates
  6. **Initiate Reflective Loop if needed** (return to agent for refinement)
  7. Report issues or pass verdict

---

## 4. Slide DSL Specification

The Slide DSL is the core abstraction that enables reliable LLM generation. Rather than generating raw code, the Code Agent generates structured JSON that a deterministic compiler transforms into React components.

```json
{
  "version": "5.0",
  "presentation": {
    "id": "deck_abc123",
    "title": "NeuralScale AI Infrastructure",
    "archetype": "investor-pitch",
    "theme": {
      "id": "modern-blue",
      "variant": "dark",
      "preset": "bold-signal"
    },
    "aspectRatio": "16:9",
    "dimensions": { "width": 1280, "height": 720 }
  },
  "slides": [
    {
      "index": 0,
      "type": "title-slide",
      "layout": "center-focus",
      "content": {
        "title": "NeuralScale",
        "subtitle": "AI Infrastructure for the Next Billion Parameters",
        "presenter": "Jane Doe, CEO",
        "tagline": "Series A — $12M"
      },
      "style": {
        "background": "gradient-radial",
        "accentColor": "#FF6B35"
      }
    },
    {
      "index": 1,
      "type": "problem-slide",
      "layout": "two-column",
      "content": {
        "heading": "The AI Infrastructure Crisis",
        "leftColumn": {
          "bullets": [
            "GPU clusters cost $50K/month",
            "Model training downtime costs $100K/hr",
            "No unified deployment pipeline"
          ]
        },
        "rightColumn": {
          "chart": {
            "type": "bar",
            "data": [
              {"label": "2023", "value": 45},
              {"label": "2024", "value": 78},
              {"label": "2025", "value": 120}
            ]
          }
        }
      }
    }
  ]
}
```

### DSL Schema Validation

- Zod schemas for runtime validation
- PreTeXt text measurement before DSL finalization
- Quality gates check DSL compliance

---

## 5. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Core MCP Server** | Python 3.11+, FastMCP | Agent orchestration, tool delivery |
| **Code Agent** | TypeScript, Node.js | React component generation, DSL compilation |
| **PPTX Generation** | PptxGenJS (native objects) | Editable PPTX with native objects |
| **PDF Generation** | Puppeteer (headless Chrome) | Pixel-perfect PDF from HTML |
| **HTML Export** | Inline bundler (zero deps) | Self-contained single HTML file |
| **Text Measurement** | PreTeXt (@chenglou/pretext) | DOM-free text fitting, overflow detection |
| **Layout Engine** | Yoga WASM (OpenPencil fork) | Server-side flexbox computation |
| **Styling** | Tailwind CSS v4 + @tailwindcss/typography | Utility-first design system |
| **Canvas Editor** | Konva.js + react-konva | Interactive WYSIWYG editing |
| **Browser Automation** | Playwright | Live preview, visual QA, screenshots |
| **Vector Store** | Chroma (embedded) | Presentation embeddings, similarity search |
| **Document Store** | MongoDB | Presentations, slides, themes |
| **Cache** | Redis | LLM responses, theme configs, sessions |
| **LLM Clients** | yoyo-evolve pattern (12 providers) | OpenAI, Claude, Gemini, Ollama, DeepSeek, Groq, etc. |
| **Diagrams** | Excalidraw npm + Mermaid | Hand-drawn diagrams, flowchart generation |
| **Charts** | D3.js / Recharts | TAM/SAM/SOM, financial projections |

---

## 6. PreTeXt Integration Architecture

PreTeXt is integrated at three critical points, following the reference architecture from chenglou/pretext:

### Phase 1: During DSL Generation (Code Agent Step 2)

```python
from pretext import prepare, layout

# Prepare text for measurement (one-time expensive operation)
prepared = prepare(
    "AI Infrastructure for the Next Billion Parameters",
    "bold 32px Inter"
)

# Fast layout computation (0.09ms per call)
{ height, lineCount } = layout(prepared, containerWidth, 40)

# If text overflows, either:
# - Suggest shorter copy
# - Switch to larger layout
# - Reduce font size within bounds
```

### Phase 2: During Component Compilation (Code Agent Step 3)

- PreTeXt measurements inform font-size decisions
- Automatic font reduction if text is close to overflow
- Minimum 24pt enforced (YC guidance)
- walkLineRanges() enables shrink-wrap layouts around images

### Phase 3: During Visual Validation (QA Agent Step 2)

- Fast pre-check (0.09ms) catches obvious overflow issues
- Runs before slower browser render step (~3s)
- Catches layout issues without DOM access

### Key PreTeXt APIs Used

| API | Purpose |
| :--- | :--- |
| `prepare(text, font)` | One-time text analysis + measurement |
| `layout(prepared, width, lineHeight)` | Fast height calculation |
| `prepareWithSegments()` | Rich segment structure for manual layout |
| `walkLineRanges()` | Binary search for optimal width |
| `layoutNextLine()` | Variable width line-by-line layout |

---

## 7. Reflective Generation Loop

Inspired by PPTAgent V2 (EMNLP 2025), the reflective loop replaces single-pass generation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REFLECTIVE GENERATION LOOP                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│   │ Generate │ -> │ Evaluate │ -> │  Refine  │ -> │Validate  │    │
│   │  (Agent)│    │  (QA)    │    │  (Agent) │    │  (Gate)  │    │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘    │
│        │               │               │               │              │
│        ▼               ▼               ▼               ▼              │
│   Output v1       Quality         Output v2      Quality            │
│                   Report                                Score        │
│        │               │               │               │              │
│        └───────────────┴───────────────┴───────────────┘              │
│                           │                                          │
│                           ▼                                          │
│                    Max 3 iterations                                   │
│                    or until 85% quality                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Loop Implementation

1. **Generation**: Orchestrator dispatches work to agents
2. **Evaluation**: QA Agent produces structured quality report with specific issues
3. **Refinement**: If quality < 85%, Orchestrator routes specific issues back to responsible agent
4. **Validation**: Check quality gates again
5. **Iteration**: Repeat up to 3 cycles
6. **Output**: Best version + improvement log

### Quality Report Structure

```json
{
  "qualityScore": 72,
  "issues": [
    {
      "type": "text-overflow",
      "location": "slide-3, bullet-2",
      "severity": "high",
      "suggestion": "Reduce text from 45 chars to 30 chars"
    },
    {
      "type": "contrast",
      "location": "slide-5, heading",
      "severity": "medium",
      "suggestion": "Increase contrast ratio to 4.5:1"
    }
  ],
  "iteration": 2,
  "antiAislopCompliance": true
}
```

---

## 8. Visual Style Discovery System

Adopted from Frontend Slides (10k⭐), this transforms theme selection:

```
┌─────────────────────────────────────────────────────────────────────┐
│                  VISUAL STYLE DISCOVERY UX                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   User: "Create pitch deck for AI startup"                          │
│                                                                      │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│   │  Preview A  │  │  Preview B  │  │  Preview C  │               │
│   │             │  │             │  │             │               │
│   │ Bold Signal │  │ Electric    │  │ Swiss       │               │
│   │ (Dark)      │  │ Studio      │  │ Modern      │               │
│   │             │  │ (Dark)      │  │ (Light)     │               │
│   └─────────────┘  └─────────────┘  └─────────────┘               │
│        ✓              ○                ○                            │
│      [SELECT]                                                     │
│                                                                      │
│   → System applies selected style across all slides               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Implementation

1. CEO Agent determines archetype (Pitch Deck)
2. Designer Agent generates 3 preview slides with different presets
3. User selects preferred style via MCP tool
4. System applies style consistently across deck
5. Anti-AI-slop processor ensures non-generic aesthetics

---

## 9. Pitch Deck Domain Intelligence

Encodes YC/Sequoia/DocSend rules as first-class constraints:

### YC Structure (10 Slides)

1. Title/One-Liner
2. Problem
3. Solution
4. Why Now
5. Market Size (bottom-up only)
6. Product/Demo
7. Traction
8. Business Model
9. Competition
10. Team
11. Ask
12. Appendix

### DocSend Analytics Rules

| Rule | Source | Action |
| :--- | :--- | :--- |
| Avg viewing time 2m24s | DocSend | Front-load key info |
| Team slide gets 1m2s | DocSend | Enhanced team slide generation |
| 10-15 slides optimal | DocSend | Cap at 15, prefer 10-12 |
| Data-rich = 3x engagement | DocSend | 30%+ slides need charts/data |
| Real screenshots > mockups | DocSend | Prioritize product images |

### Anti-Pitfall Rules

| Pitfall | Rule |
| :--- | :--- |
| Too much text | Max 6 bullets/slide, 15 words/bullet |
| Jargon | Generalist-readable language |
| "No competition" | Require competitive positioning |
| Top-down market | Bottom-up only (SAM/SOM calculation) |
| Missing "Why Now" | Mandatory slide for investor decks |
| Weak team | Credentials + photos required |
| Animations | YC: No transitions |

---

## 10. Enhanced Export Pipeline

| Format | Technology | Quality | Editability | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **PPTX (native)** | PptxGenJS | High | Full | Editable, investor sharing |
| **PPTX (visual)** | Puppeteer + PptxGenJS | Very High | None (images) | Design-critical |
| **PDF** | Puppeteer page.pdf() | Perfect | None | Read-only, printing |
| **HTML** | Inline bundler | High | Full source | Web sharing |
| **React** | Compiled from DSL | High | Full source | Canvas editor, embedding |
| **PNG** | Puppeteer screenshot | High | None | Social media |
| **Google Slides** | Google API | High | Full | Enterprise |

### Export Quality Priority

1. **PptxGenJS** for PPTX (native objects, not screenshots)
2. **Puppeteer** for PDF (pixel-perfect from HTML)
3. **Inline bundler** for HTML (zero-dependency, self-contained)

---

## 11. Agent Communication Protocol

Uses a **Context Board** (shared JSON document):

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTEXT BOARD STRUCTURE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   {                                                                 │
│     "orchestrator": { "task": "...", "status": "running" },         │
│     "ceo_agent": { "outline": {...}, "archetype": "pitch-deck" },   │
│     "researcher": { "findings": [...], "citations": [...] },         │
│     "designer": { "theme": "...", "preset": "bold-signal" },        │
│     "assembler": { "pptx_status": "complete" },                    │
│     "code_agent": { "dsl_status": "generating", "components": [] },│
│     "qa_agent": { "quality_score": 78, "issues": [...] }            │
│   }                                                                 │
│                                                                      │
│   Priority System:                                                  │
│   1. Domain rules (pitch deck constraints) > aesthetic preferences  │
│   2. User requirements > auto-generated suggestions                │
│   3. Quality gate failures > completion signals                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **Async polling**: Agents poll Context Board for new inputs
2. **Parallel execution**: Researcher and Designer can work simultaneously
3. **Ordering guarantees**: Assembler waits for CEO outline + Researcher data
4. **Conflict resolution**: Orchestrator mediates via priority system

---

## 12. Tool Specification (55+ Tools)

### Category 1: Presentation Lifecycle (6)
- create_presentation, open_presentation, save_presentation
- get_presentation_info, set_core_properties, delete_presentation

### Category 2: Slide Operations (8)
- add_slide, delete_slide, reorder_slides, duplicate_slide
- set_slide_background, get_slide_content, set_transition, set_notes

### Category 3: Content & Text (6)
- populate_placeholder, add_bullet_points, manage_text
- add_text_box, find_replace, extract_slide_text

### Category 4: Visual Elements (8)
- add_image, add_shape, add_chart, add_table
- apply_picture_effects, crop_image, set_shape_style, add_hyperlink

### Category 5: Theme & Design (6)
- apply_theme, generate_theme, create_custom_theme
- list_themes, extract_theme, discover_style (NEW)

### Category 6: Image Generation (4)
- generate_image, generate_hero_image, search_stock_images, upload_custom_image

### Category 7: Research & Data (4)
- research_topic, extract_document, search_web, analyze_data

### Category 8: Quality & Validation (4)
- validate_content, check_branding, validate_sources, get_improvements

### Category 9: Code Agent (10) (NEW)
- generate_slide_dsl, compile_react_slides, measure_text_fit
- validate_slide_dsl, export_to_pptx, export_to_pdf, export_to_html
- generate_diagram, preview_slides, apply_anti_slop

### Category 10: Diagram Integration (3) (NEW)
- create_excalidraw_diagram, create_mermaid_diagram, embed_diagram_in_slide

### Category 11: Export Formats (6) (NEW)
- export_pptx, export_pdf, export_google_slides
- export_revealjs, export_slidev, export_images

---

## 13. Theme System

### 16 Color Schemes (Expanded)

| Theme | Primary | Secondary | Accent | Best For |
| :--- | :--- | :--- | :--- | :--- |
| Modern Blue | #0078D4 | #106EBE | #FFB900 | Tech, SaaS |
| Corporate Gray | #605E5C | #323130 | #0078D4 | Consulting |
| Elegant Green | #107C10 | #0B6A43 | #00B294 | Sustainability |
| Warm Red | #D83B01 | #A4262C | #FF8C00 | Sales |
| Dark Developer | #0F172A | #1E293B | #38BDF8 | Dev tools |
| Bold Signal | #FF6B35 | #004E98 | #1A936F | Startup |
| Electric Studio | #7B2FF7 | #C000FF | #00F5FF | Futuristic |
| Neon Cyber | #FF00FF | #00FFFF | #FFFF00 | Gaming |
| ... | ... | ... | ... | ... |

### 12 Curated Style Presets (Anti-AI-Slop)

| Preset | Category | Character |
| :--- | :--- | :--- |
| **Bold Signal** | Dark | High contrast, dynamic, accent glows |
| **Electric Studio** | Dark | Futuristic, tech, neon accents |
| **Dark Botanical** | Dark | Natural, sophisticated, organic shapes |
| **Notebook Tabs** | Light | Organized, clean, tab dividers |
| **Pastel Geometry** | Light | Soft, approachable, geometric |
| **Swiss Modern** | Specialty | Minimal, precise, grid system |
| **Terminal Green** | Specialty | Technical, hacker, phosphor |
| **Paper and Ink** | Specialty | Editorial, classic, ink texture |
| **Neon Cyber** | Specialty | Cyberpunk, gaming aesthetic |
| **Creative Voltage** | Dark | Creative, high energy |
| **Vintage Editorial** | Light | Classic, publication-style |
| **Split Pastel** | Light | Modern, dual-tone |

---

## 14. Implementation Phases (14 Weeks)

| Phase | Weeks | Deliverables | Dependencies |
| :--- | :--- | :--- | :--- |
| **Phase 1: Foundation** | 1-2 | FastMCP server (stdio/HTTP+SSE); 34 core tools; basic CRUD; Chroma setup | None |
| **Phase 2: Agent Core** | 3-5 | Orchestrator with Context Board; CEO Agent; Researcher Agent; Agent Communication Protocol | Phase 1 |
| **Phase 3: Design Intelligence** | 5-7 | Designer Agent; 16 color schemes; 12 style presets; Visual Style Discovery; AI Template Selector | Phase 2 |
| **Phase 4: Code Agent** | 7-9 | Slide DSL schema (Zod); React compiler; PreTeXt integration; PptxGenJS export; Puppeteer PDF; Zero-dep HTML | Phase 2 + 3 |
| **Phase 5: Quality & Preview** | 9-11 | QA Agent; Browser daemon (Playwright); Live preview; Reflective Loop (2-3 cycles); Anti-AI-slop | Phase 3 + 4 |
| **Phase 6: Diagrams** | 11-12 | Excalidraw integration; Mermaid diagrams; D3.js/Recharts for data viz | Phase 4 |
| **Phase 7: Domain Intelligence** | 12-13 | Pitch Deck rules (YC, DocSend); Canvas editor (Konva.js); Deployment archetypes | Phase 5 |
| **Phase 8: Production** | 13-14 | Error handling; Performance; Testing; Documentation; Docker deployment | All phases |

---

## 15. Success Metrics

| Metric | Target |
| :--- | :--- |
| JSON validity (LLM output) | >95% |
| Image generation success | >90% (with fallback) |
| Export success rate | >99% |
| Quality pass rate (first attempt) | >75% |
| Quality pass rate (after reflective loop) | >90% |
| Content generation time | ≤5s/slide |
| Full deck generation (10 slides) | <60s |
| PreTeXt validation time | <1ms/text |
| Browser preview latency | <1s/command |

---

## 16. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| PreTeXt SSR not available | High | Medium | Use for client-side validation; Playwright fallback |
| GStack dependency | Medium | High | Use raw Playwright instead |
| Python/Node hybrid complexity | Medium | Medium | Clear interface boundaries |
| PptxGenJS vs python-pptx choice | Low | Medium | PptxGenJS for Code Agent; python-pptx for Assembler |
| Quality gate false positives | Medium | Low | Tunable threshold, user override |

---

## 17. Differentiation Summary

| Feature | Our MCP | Gamma | Beautiful.ai | Presenton |
| :--- | :--- | :--- | :--- | :--- |
| **Agent Orchestration** | 6 specialized | Single prompt | Single prompt | Multi-agent |
| **Code Agent** | React/Tailwind | None | None | None |
| **Reflective Loop** | 2-3 iterations | None | None | None |
| **PreTeXt Integration** | DOM-free measurement | None | None | None |
| **Visual Discovery** | 3-preview selection | Basic | Basic | None |
| **Anti-AI-Slop** | 12 curated presets | None | None | None |
| **Pitch Deck Domain** | YC/Sequoia/DocSend rules | Generic | Generic | Generic |
| **Format Support** | PPTX/PDF/HTML/React/Google | PPTX/PDF | PPTX | PPTX/HTML |
| **Open Source** | Full | No | No | Yes |

---

## 18. Reference Integration

| Reference | What Was Adopted |
| :--- | :--- |
| **PreTeXt** (32.2k⭐) | DOM-free text measurement; two-phase API; walkLineRanges for shrink-wrap |
| **OpenPencil** (3.9k⭐) | 90+ MCP tools benchmark; Yoga WASM; design-to-code export pattern |
| **yoyo-evolve** (1.4k⭐) | Multi-provider architecture (12 providers); streaming REPL; subagent pattern |
| **Frontend Slides** (10k⭐) | Visual Style Discovery; 12 curated presets; anti-AI-slop design |
| **PPTAgent V2** (EMNLP 2025) | Reflective generation loop; generate-evaluate-refine cycle |

---

## 19. Next Steps

1. Initialize project structure (Python MCP server + TypeScript Code Agent)
2. Implement core MCP tools (34 tools, Phase 1)
3. Integrate PreTeXt for text measurement
4. Build Agent Communication Protocol
5. Develop Slide DSL schema
6. Implement Visual Style Discovery
7. Add Reflective Generation Loop
8. Test with real-world pitch deck scenarios

---

**Document Version**: 5.0 (Standalone Implementation Plan)
**Status**: Ready for Implementation
**Architecture**: Production-Grade MCP Server with 6 Specialized Agents + Reflective Loop + PreTeXt Integration