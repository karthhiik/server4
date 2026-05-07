# Premium Slide Generation MCP — V7 Master Plan

## Version 7.0 — Multi-Renderer Architecture with Code Agents, 3D, and Canvas Editing

**Document Version**: 7.0 (Complete Rebuild — Supersedes V5)
**Created**: 2026-07-01
**Status**: Ready for Implementation
**Architecture**: Multi-Renderer Pipeline with 8 Specialized Agents + Self-Evolving Code Agent + reveal.js + React+Three.js + Canvas Editor

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The 21 Questions — Direct Answers](#2-the-21-questions--direct-answers)
3. [Architecture Overview](#3-architecture-overview)
4. [Multi-Renderer Pipeline](#4-multi-renderer-pipeline)
5. [Agent System (8 Agents + Self-Evolving Loop)](#5-agent-system)
6. [Code Agent Architecture (yoyo-evolve Pattern)](#6-code-agent-architecture)
7. [reveal.js Integration](#7-revealjs-integration)
8. [React + Three.js + 3D Slides](#8-react--threejs--3d-slides)
9. [Canvas Pro Editor (OpenPencil Architecture)](#9-canvas-pro-editor)
10. [Per-Format Editing Systems](#10-per-format-editing-systems)
11. [Theme Engine (100+ Themes)](#11-theme-engine-100-themes)
12. [Generative Template System](#12-generative-template-system)
13. [Current LLM Inventory & Usage (From Production .env + Code)](#13-current-llm-inventory--usage)
14. [Image Generation Pipeline (Flux-First)](#14-image-generation-pipeline)
15. [Thinking Models Strategy](#15-thinking-models-strategy)
16. [Fast Generation Techniques](#16-fast-generation-techniques)
17. [PreTeXt.js Integration](#17-pretextjs-integration)
18. [Pre-Built Templates (frontend-slides Pattern)](#18-pre-built-templates)
19. [Reading vs Presentation Modes](#19-reading-vs-presentation-modes)
20. [Slide DSL v2 Specification](#20-slide-dsl-v2-specification)
21. [Re-Generation & Layout Changing](#21-re-generation--layout-changing)
22. [Pitch Deck Domain Intelligence](#22-pitch-deck-domain-intelligence)
23. [Export Pipeline](#23-export-pipeline)
24. [Technology Stack](#24-technology-stack)
25. [Implementation Phases (16 Weeks)](#25-implementation-phases)
26. [Success Metrics](#26-success-metrics)
27. [Reference Repository Index](#27-reference-repository-index)

---

## 1. Executive Summary

V7 is a **complete rebuild** of the slide generation architecture, designed to answer 21 critical questions raised during V6 review. The core insight: **a single render path cannot serve all use cases**. V7 introduces a **Multi-Renderer Pipeline** where the same Slide DSL compiles to four distinct output formats, each with its own editing system, presentation mode, and export path.

### What Changed from V5

| Aspect | V5 | V7 |
|--------|-----|-----|
| Renderers | 1 (React + PPTX fallback) | 4 (reveal.js, React+3D, Zero-dep HTML, PPTX) |
| Agents | 6 | 8 + Self-Evolving Code Agent |
| Themes | 16 color schemes + 12 presets | 100+ (24 built-in + Generative Theme Engine) |
| Editing | Konva.js canvas only | Unified DSL Editor + per-renderer views |
| 3D Support | None | Three.js scenes embedded in slides |
| Image Models | Generic | Flux-first (FLUX.1-Kontext-pro primary) |
| Thinking Models | Not specified | Kimi-K2-Thinking + Phi-4-reasoning-vision-15B |
| Presentation Modes | Single | Reading Mode + Presentation Mode |
| Code Agent | Basic DSL generator | Self-evolving agent (yoyo-evolve pattern) |
| reveal.js | Not integrated | First-class renderer with full API |
| Pre-built Templates | None | 12 curated presets (frontend-slides pattern) |
| Re-generation | Full deck only | Per-slide + Per-section + Full deck |
| Layout Changing | Static | Dynamic per-slide + per-deck |

### Core Architecture Principle

```
Content → Slide DSL v2 → Router → [reveal.js | React+3D | HTML | PPTX]
                                        ↓           ↓         ↓       ↓
                                   reveal Editor  React Editor  HTML Editor  PPTX Editor
                                        ↓           ↓         ↓       ↓
                                   Presentation   Interactive  Reading   Download
                                   Mode           Mode         Mode      Mode
```

### Research Foundation

Built on deep analysis of:

| Repository | Stars | What We Use |
|-----------|-------|-------------|
| **reveal.js** | 70.9k | Primary HTML presentation renderer, Auto-Animate, speaker notes |
| **Slidev** | 45.4k | PPTX export pattern, Markdown slides concept, theme gallery |
| **Clay** | 16.9k | Layout computation concepts, flexbox model, transition API |
| **frontend-slides** | 12.5k | Anti-AI-slop style presets (STYLE_PRESETS.md), visual style discovery |
| **Spectacle** | 10.1k | React JSX presentation pattern, live code demos |
| **PptxGenJS** | 4.9k | Native PPTX generation with charts, shapes, HTML-to-PPTX |
| **open-pencil** | 3.9k | Canvas editor architecture: Skia CanvasKit WASM + Yoga WASM layout |
| **yoyo-evolve** | 1.5k | Self-evolving code agent (yologdev/yoyo-evolve), yoagent framework |

---

## 2. The 21 Questions — Direct Answers

### Q1: Code Agents (yoyo-evolve)

**Answer**: The Code Agent adopts yoyo-evolve's **self-evolving pattern** — it generates slides, evaluates quality via the QA Agent, and autonomously iterates. It has a **skills system** where each slide type (title, problem, solution, team, etc.) is a learnable skill that improves over generations. Multi-provider support routes to 8+ LLM providers. See [Section 6](#6-code-agent-architecture).

### Q2: Tailwind + Advanced HTML/JS Usage

**Answer**: All four renderers consume Tailwind-style utility classes for styling. **CRITICAL**: Tailwind CSS v4's aggressive CSS reset (modern-normalize + preflight) destroys reveal.js slide transitions (GitHub Issue #3782). **Mitigation**: Use **UnoCSS** (compatible utility-class engine without the destructive reset) for reveal.js renderer, or scoped Tailwind v3 with `@layer` isolation. The React renderer uses Tailwind v4 + Motion (motiondivision/motion) for animations (no conflict since it doesn't use reveal.js). The HTML renderer generates **zero-dependency single-file HTML** with inline utility classes. Advanced JS is used for:
- Three.js 3D scenes within slides
- D3.js data visualizations
- Mermaid/Excalidraw diagram rendering
- GSAP/Motion animations

### Q3: Canvas Pro-like Editing

**Answer**: The Canvas Editor is built on the **OpenPencil architecture** — using a rendering layer (HTML5 Canvas or SVG) + Yoga WASM for layout computation + a node-based editing model. Users can:
- Drag/drop elements on a slide canvas
- Resize, rotate, reposition any element
- Edit text inline
- Change colors, fonts, spacing visually
- Add/remove elements
- Each format has its own specialized editor. See [Section 9](#9-canvas-pro-editor).

### Q4: Pitch Deck Handling

**Answer**: Pitch decks are a first-class archetype with dedicated:
- YC 10-slide structure enforcement
- Sequoia 15-point framework
- DocSend analytics-driven rules (2m24s avg view time, front-load key info)
- Anti-pitfall rules (max 6 bullets, bottom-up TAM only, no "we have no competition")
- Specialized slide types: TAM/SAM/SOM calculator, traction metrics, competitive matrix
- See [Section 21](#21-pitch-deck-domain-intelligence).

### Q5: reveal.js

**Answer**: reveal.js v6.0.0 (70.9k⭐) is the **primary HTML presentation renderer**. Integration includes:
- Full keyboard navigation (arrow keys, space, ESC for overview)
- Auto-Animate transitions between slides
- Speaker notes with timer
- Nested vertical slides for drill-down
- Markdown content support
- LaTeX math rendering
- Code syntax highlighting with line-by-line animation
- PDF export built-in
- Fragment animations (fade-in, grow, shrink, strike)
- See [Section 7](#7-revealjs-integration).

### Q6: Template Generation & Handling

**Answer**: Templates are **generative rules, not static files**. The system stores layout constraints, typography rules, color algorithms, and animation patterns as code. When a new presentation is requested, the Generative Template Engine computes the optimal layout for the specific content. This means infinite variety — no two decks look the same. Pre-built templates from frontend-slides serve as starting points that the engine can mutate. See [Section 12](#12-generative-template-system).

### Q7: HTML/CSS/JS Preview Speed

**Answer**: Target is **<200ms** preview refresh. Achieved via:
- Hot Module Replacement (HMR) with Vite dev server for React slides
- reveal.js native slide switching (<16ms per transition)
- Incremental DOM updates (only changed slides re-render)
- PreTeXt text measurement (0.09ms per text block, no DOM needed)
- WebSocket-based live preview (server pushes changes to browser)
- See [Section 15](#15-fast-generation-techniques).

### Q8: React + 3D + Three.js + Node.js Possibilities

**Answer**: React slides can embed **Three.js scenes** as slide backgrounds or inline elements:
- 3D data visualizations (bar charts with depth, scatter plots with rotation)
- Animated 3D logos/models
- Particle effects for emphasis moments
- Globe visualizations for market/geo data
- Glass-morphism panels with real depth
- Node.js runs the compilation server (TypeScript → React → rendered HTML)
- See [Section 8](#8-react--threejs--3d-slides).

### Q9: Editing / Adding New Fields

**Answer**: Every slide in the DSL has an extensible `customFields` object. Users can:
- Add custom text fields to any slide
- Insert additional images, charts, or diagrams
- Create custom data visualizations
- Add speaker notes, annotations, footnotes
- The editor surfaces these as drag-and-drop insertion points
- See [Section 19](#19-slide-dsl-v2-specification) for the extensible DSL schema.

### Q10: Each Format Needs Its Own Editing

**Answer**: Yes — this is a core V7 principle. Four distinct editing experiences:

| Format | Editor | Technology | Capabilities |
|--------|--------|-----------|--------------|
| reveal.js | **Reveal Editor** | CodeMirror + reveal.js API | Markdown editing, fragment ordering, speaker notes, transition config |
| React+3D | **Component Editor** | React DevTools-style inspector | Props editing, Three.js scene graph, animation timeline |
| HTML | **HTML Editor** | Monaco Editor (VS Code engine) | Direct HTML/CSS/JS editing, live preview |
| PPTX | **Slide Editor** | Canvas-based (OpenPencil pattern) | Drag/drop, shape tools, text formatting, image placement |

See [Section 10](#10-per-format-editing-systems).

### Q11: Re-generating Slides/Presentations

**Answer**: Three levels of re-generation:
1. **Per-slide**: Right-click → "Regenerate this slide" — preserves deck context, regenerates single slide
2. **Per-section**: "Regenerate Problem section" — regenerates a logical group of slides
3. **Full deck**: "Regenerate entire presentation" — fresh generation with option to keep theme/style
- Context preservation: the re-generation agent receives the current deck state + user feedback
- Version history: every generation creates a snapshot, user can diff/revert
- See [Section 20](#20-re-generation--layout-changing).

### Q12: Layout Changing Per Slide / Per Deck

**Answer**: Dynamic layout system:
- **Per-slide**: Click layout picker → choose from 12+ layout options (center-focus, two-column, three-column, full-bleed image, split-screen, etc.)
- **Per-deck**: Apply a layout template across all slides (consistent column structure, spacing)
- **Smart layout**: AI analyzes content and suggests optimal layout per slide
- Layout changes cascade through the render pipeline — all formats update
- See [Section 20](#20-re-generation--layout-changing).

### Q13: 100+ Themes

**Answer**: Achieved through three tiers:
1. **24 Built-in Themes**: Hand-crafted color schemes covering all major aesthetics (dark/light/specialty)
2. **Generative Theme Engine**: Input brand colors → generates complete theme (palette, typography, spacing, gradients)
3. **Community Themes**: npm-installable themes (following Slidev's theme gallery pattern)
4. **Theme Mutation**: Any built-in theme can be mutated (adjust warmth, contrast, saturation) for infinite variants
- Total: 24 built-in × 5 mutations = 120 base variants + custom generation = effectively unlimited
- See [Section 11](#11-theme-engine-100-themes).

### Q14: Flux for Images

**Answer**: **flux-pro-2** (Azure) is the **primary image generation model** for all slide imagery:
- Hero slides: flux-pro-2 for cinematic quality
- Content illustrations: flux-pro-2 for consistency
- Icons/diagrams: phoenix-1.0 (Cloudflare free) for simple assets
- Background textures: lucid-origin (Cloudflare free) for artistic patterns
- Flux generates at 1024×1024 by default, cropped/resized per slide layout
- See [Section 13](#13-image-generation-pipeline).

### Q15: Thinking Models Usage

**Answer**: Two thinking models with distinct roles:
- **Kimi-K2-Thinking** (Azure): Strategy, architecture, narrative structure, complex reasoning (CEO Agent, Orchestrator)
- **Phi-4-reasoning**: Layout decisions, content-to-visual mapping, design validation (Designer Agent, QA Agent)
- Thinking models are used for **planning steps only** — not for bulk content generation (too slow/expensive)
- See [Section 14](#14-thinking-models-strategy).

### Q16: Fast Generation Techniques

**Answer**: Target is **<60s for a 10-slide deck**:
- Parallel agent execution (Researcher + Designer work simultaneously)
- Streaming generation (slides appear as they're generated, not after completion)
- Progressive rendering (skeleton → content → images → animations)
- PreTeXt pre-measurement eliminates layout reflows
- Redis caching of theme computations, font metrics, common layouts
- Batch LLM calls (generate 3-4 slides per API call)
- See [Section 15](#15-fast-generation-techniques).

### Q17: PreTeXt.js

**Answer**: PreTeXt is integrated at three levels:
1. **During DSL generation**: Text measurement before layout commitment (0.09ms per text block)
2. **During compilation**: Font-size decisions, overflow detection, shrink-wrap layouts
3. **During QA**: Fast pre-check before expensive browser rendering
- Key APIs: `prepare()`, `layout()`, `walkLineRanges()`, `layoutNextLine()`
- See [Section 16](#16-pretextjs-integration).

### Q18: Pre-built Templates (frontend-slides repo)

**Answer**: 12 curated style presets from Frontend Slides pattern:
- Each preset is a complete visual system (colors, typography, spacing, animations, backgrounds)
- Anti-AI-slop design: no generic gradients, no stock-photo aesthetics
- Visual Style Discovery UX: user sees 3 preview slides, picks preferred style
- Presets: Bold Signal, Electric Studio, Dark Botanical, Swiss Modern, Terminal Green, Paper & Ink, Neon Cyber, Creative Voltage, Vintage Editorial, Split Pastel, Notebook Tabs, Pastel Geometry
- See [Section 17](#17-pre-built-templates).

### Q19: OpenPencil for Editing + GitHub Research

**Answer**: The Canvas Editor follows OpenPencil's architecture:
- **Rendering**: HTML5 Canvas (2D context) for PPTX editor, SVG for React editor
- **Layout**: Yoga WASM for flexbox computation (server-side and client-side)
- **AI Tools**: 20+ AI-powered editing tools (auto-align, smart resize, content-aware crop, style transfer)
- **MCP Server**: The editor exposes an MCP server so AI agents can programmatically edit slides
- All GitHub repos researched inform specific components. See [Section 26](#26-reference-repository-index).

### Q20: Reading vs Presentation Modes

**Answer**: Two distinct modes:
- **Reading Mode**: Scrollable document layout, all slides visible, annotations visible, expandable details, dark/light toggle, table of contents sidebar
- **Presentation Mode**: Full-screen, keyboard navigation, speaker notes (separate window), timer, transitions, fragments
- reveal.js natively supports both (overview mode = reading, slideshow = presentation)
- React slides: reading mode = vertical scroll, presentation = fullscreen carousel
- See [Section 18](#18-reading-vs-presentation-modes).

### Q21: Rebuild the Plan

**Answer**: This is V7. The plan is rebuilt from the ground up incorporating every question, every referenced repository, and every technology the user asked about. This is the **strong and standalone plan**.

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                    PREMIUM SLIDE GENERATION MCP SERVER v7                             │
│                                                                                      │
│  Protocol: MCP (JSON-RPC over stdio/HTTP+SSE)                                       │
│  Core: Python 3.11+ (FastMCP) + TypeScript (Code Agent + Renderers)                 │
│  Storage: MongoDB + Redis + ChromaDB                                                │
│  Frontend: React 18 + TypeScript + Vite + UnoCSS/Tailwind v4 (per-renderer)  │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
┌────────────────────┐   ┌─────────────────────────┐   ┌────────────────────┐
│   ORCHESTRATOR     │   │   AGENT SWARM (8)       │   │  RENDER ENGINE     │
│   + Self-Evolve    │   │                         │   │  (4 Renderers)     │
│                    │   │ 1. CEO/Strategist       │   │                    │
│ • Task Decompose   │   │ 2. Researcher/Analyst   │   │ ┌─ reveal.js ────┐│
│ • Agent Coordinate │   │ 3. Designer/Creative    │   │ │  Presentations  ││
│ • Context Board    │   │ 4. Code Agent (evolving)│   │ │  Speaker Notes  ││
│ • Quality Gates    │   │ 5. Assembler/PPTX       │   │ │  Auto-Animate   ││
│ • Reflective Loop  │   │ 6. QA Lead/Reviewer     │   │ └─────────────────┘│
│ • Version Control  │   │ 7. 3D/VFX Agent (NEW)  │   │ ┌─ React+Three ──┐│
│                    │   │ 8. Layout Agent (NEW)   │   │ │  3D Scenes      ││
│                    │   │                         │   │ │  Animations     ││
│                    │   │                         │   │ │  Interactive    ││
│                    │   │                         │   │ └─────────────────┘│
│                    │   │                         │   │ ┌─ HTML (zero-dep)┐│
│                    │   │                         │   │ │  Single File     ││
│                    │   │                         │   │ │  Shareable       ││
│                    │   │                         │   │ └─────────────────┘│
│                    │   │                         │   │ ┌─ PPTX ─────────┐│
│                    │   │                         │   │ │  PptxGenJS      ││
│                    │   │                         │   │ │  Native Objects ││
│                    │   │                         │   │ └─────────────────┘│
└────────────────────┘   └─────────────────────────┘   └────────────────────┘
         │                              │                              │
         ▼                              ▼                              ▼
┌────────────────────┐   ┌─────────────────────────┐   ┌────────────────────┐
│  KNOWLEDGE LAYER   │   │  TOOL LAYER (75+ Tools)│   │  EDITOR LAYER      │
│                    │   │                         │   │  (4 Editors)       │
│ • ChromaDB (RAG)   │   │ • Presentation CRUD    │   │                    │
│ • MongoDB (Docs)   │   │ • Slide Operations     │   │ • Reveal Editor    │
│ • Redis (Cache)    │   │ • Content Generation   │   │ • React Inspector  │
│ • Skills Store     │   │ • Image (Flux-first)   │   │ • HTML/Monaco      │
│ • Theme Store      │   │ • Code Agent Tools     │   │ • Canvas/PPTX      │
│                    │   │ • 3D/VFX Tools         │   │                    │
│                    │   │ • Theme Tools          │   │                    │
│                    │   │ • Export Tools         │   │                    │
└────────────────────┘   └─────────────────────────┘   └────────────────────┘
```

### Data Flow

```
User Request
     │
     ▼
[CEO Agent] ──→ Strategy + Archetype + Narrative Arc
     │
     ├──→ [Researcher Agent] ──→ Data, Citations, Evidence (parallel)
     ├──→ [Designer Agent] ──→ Theme, Style, Visual Identity (parallel)
     │
     ▼
[Layout Agent] ──→ Per-slide layout decisions (using Phi-4-reasoning)
     │
     ▼
[Code Agent] ──→ Slide DSL v2 generation (self-evolving)
     │
     ├──→ [3D/VFX Agent] ──→ Three.js scenes, animations (if needed)
     │
     ▼
[Render Router] ──→ Routes DSL to selected renderer(s)
     │
     ├──→ reveal.js compiler
     ├──→ React+Three.js compiler
     ├──→ Zero-dep HTML compiler
     └──→ PptxGenJS compiler
     │
     ▼
[QA Agent] ──→ Visual verification + Quality scoring
     │
     ├──→ Pass (≥85%) → Deliver to user
     └──→ Fail (<85%) → Reflective Loop (back to Code Agent, max 3 iterations)
```

---

## 4. Multi-Renderer Pipeline

The core architectural innovation of V7. One DSL, four renderers.

### 4.1 Why Multi-Renderer?

Different use cases demand different output:

| Use Case | Best Renderer | Why |
|----------|---------------|-----|
| Investor pitch (in-person) | reveal.js | Keyboard nav, speaker notes, Auto-Animate |
| Interactive product demo | React+Three.js | 3D scenes, live data, animations |
| Email/share a deck | Zero-dep HTML | Single file, works offline, no dependencies |
| Edit in PowerPoint | PPTX (PptxGenJS) | Native objects, enterprise compatibility |
| Print/PDF | reveal.js or HTML | Built-in PDF export |
| Embed in web app | React | Component import |

### 4.2 Renderer Specifications

#### Renderer 1: reveal.js (Primary Presentation Renderer)

```
Technology: reveal.js v6.0.0 (70.9k⭐)
Output: index.html with reveal.js runtime
Features:
  - Horizontal slides (main flow) + vertical slides (drill-down)
  - Auto-Animate: morphing transitions between similar elements
  - Fragment animations: fade-in, grow, shrink, strike, highlight
  - Speaker notes: separate window with next slide preview + timer
  - Overview mode: bird's-eye grid of all slides (reading mode)
  - Code highlighting: highlight.js with line-by-line stepping
  - LaTeX math: KaTeX integration
  - Markdown: per-slide markdown content
  - PDF export: ?print-pdf URL parameter → Chrome print
  - Plugins: search, zoom, notes, math, highlight
  - API: Reveal.slide(h, v), Reveal.next(), Reveal.prev(), etc.
```

**How DSL Maps to reveal.js:**
```html
<!-- Each DSL slide becomes a <section> -->
<section data-auto-animate data-background-color="#0F172A">
  <h1 data-id="title" class="text-5xl font-bold text-white">NeuralScale</h1>
  <p data-id="subtitle" class="text-xl text-gray-300 mt-4">
    AI Infrastructure for Next-Gen Models
  </p>
  <!-- Fragments for progressive reveal -->
  <ul>
    <li class="fragment fade-in">GPU clusters optimized</li>
    <li class="fragment fade-in">Zero-downtime deployment</li>
    <li class="fragment fade-in">Unified pipeline</li>
  </ul>
  <aside class="notes">
    Key talking point: emphasize the $50K/month cost savings...
  </aside>
</section>
```

#### Renderer 2: React + Three.js (Interactive/3D Renderer)

```
Technology: React 18 + Three.js + @react-three/fiber + Framer Motion
Output: React component tree (compilable via Vite)
Features:
  - 3D backgrounds: animated particle fields, gradient meshes, globe
  - Interactive charts: D3.js + Three.js hybrid data visualizations
  - Animated transitions: Framer Motion spring physics
  - Live data: WebSocket-connected real-time data slides
  - Glass-morphism: backdrop-filter blur panels with depth
  - Parallax: scroll-driven depth layers
  - Component library: reusable slide components
```

**How DSL Maps to React+Three.js:**
```tsx
<SlideWrapper theme="dark-developer" layout="split-screen">
  <SlideContent side="left">
    <Heading level={1} animate="slideUp">NeuralScale</Heading>
    <Paragraph animate="fadeIn" delay={0.3}>
      AI Infrastructure for Next-Gen Models
    </Paragraph>
  </SlideContent>
  <SlideVisual side="right">
    <ThreeScene>
      <AnimatedGlobe
        data={marketData}
        highlightRegions={["NA", "EU", "APAC"]}
        rotationSpeed={0.001}
      />
    </ThreeScene>
  </SlideVisual>
</SlideWrapper>
```

#### Renderer 3: Zero-Dependency HTML (Sharing Renderer)

```
Technology: Single HTML file with inline CSS + minimal JS
Output: One .html file (<500KB), works offline
Features:
  - No external dependencies (CDNs, frameworks, libraries)
  - Inline Tailwind utilities (extracted, not full CDN)
  - Keyboard navigation (← → ↑ ↓)
  - Print-friendly layout
  - Dark/light mode toggle
  - Responsive (works on mobile)
  - Anti-AI-slop styles from frontend-slides presets
```

**How DSL Maps to HTML:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <style>/* Extracted Tailwind utilities + theme CSS */</style>
</head>
<body class="bg-slate-950 text-white">
  <div class="slide active" data-index="0">
    <div class="slide-content center-focus">
      <h1 class="text-6xl font-bold tracking-tight">NeuralScale</h1>
      <p class="text-2xl text-slate-400 mt-6">AI Infrastructure for Next-Gen Models</p>
    </div>
  </div>
  <script>/* Minimal ~2KB navigation JS */</script>
</body>
</html>
```

#### Renderer 4: PPTX (Download Renderer)

```
Technology: PptxGenJS v4.0.1 (4.9k⭐)
Output: Standards-compliant .pptx file
Features:
  - Native text boxes (fully editable in PowerPoint)
  - Native charts (bar, line, pie, scatter, area — editable)
  - Native tables (sortable, styleable in PowerPoint)
  - Native shapes (rectangles, circles, arrows, callouts)
  - Slide Masters (consistent branding templates)
  - Images (embedded, not linked)
  - HTML table → PPTX table conversion (single line)
  - Speaker notes
  - Multiple export formats: Blob, base64, Buffer, file
```

**How DSL Maps to PPTX:**
```typescript
import pptxgen from "pptxgenjs";

const pres = new pptxgen();
pres.defineSection({ title: "Main" });

// Slide Master for consistent branding
pres.defineSlideMaster({
  title: "BARISE_MASTER",
  background: { color: "0F172A" },
  objects: [
    { text: { text: "Barise", options: { x: 0.5, y: 7, fontSize: 8, color: "64748B" } } }
  ]
});

// Map each DSL slide to PptxGenJS calls
const slide = pres.addSlide({ masterName: "BARISE_MASTER" });
slide.addText("NeuralScale", {
  x: 1, y: 2, w: 8, h: 1.5,
  fontSize: 44, fontFace: "Inter", color: "FFFFFF", bold: true,
  align: "center"
});
slide.addText("AI Infrastructure for Next-Gen Models", {
  x: 1, y: 3.5, w: 8, h: 0.8,
  fontSize: 20, fontFace: "Inter", color: "94A3B8",
  align: "center"
});

// Native chart (editable in PowerPoint!)
slide.addChart(pres.ChartType.bar, chartData, {
  x: 1, y: 1, w: 8, h: 4,
  showValue: true, catAxisLabelColor: "94A3B8"
});

await pres.writeFile({ fileName: "NeuralScale-Pitch.pptx" });
```

### 4.3 Render Router

The router decides which renderer(s) to activate based on:

```python
class RenderRouter:
    def route(self, dsl: SlideDSL, user_preference: str | None) -> list[Renderer]:
        """Determine which renderers to activate."""

        # User explicitly selected a format
        if user_preference:
            return [self.renderers[user_preference]]

        # Auto-detect based on content
        renderers = []

        # Always generate reveal.js (primary)
        renderers.append(self.renderers["revealjs"])

        # If DSL contains 3D scenes → also generate React+Three.js
        if any(slide.has_3d_elements for slide in dsl.slides):
            renderers.append(self.renderers["react_threejs"])

        # If user wants downloadable → also generate PPTX
        if dsl.export_formats and "pptx" in dsl.export_formats:
            renderers.append(self.renderers["pptx"])

        # If user wants shareable link → also generate HTML
        if dsl.export_formats and "html" in dsl.export_formats:
            renderers.append(self.renderers["html"])

        return renderers
```

---

## 5. Agent System

### 8 Specialized Agents

| # | Agent | Model | Role | Tools |
|---|-------|-------|------|-------|
| 1 | **CEO / Strategist** | Kimi-K2-Thinking | Narrative blueprinting, archetype selection | analyze_presentation, validate_strategy, select_archetype |
| 2 | **Researcher / Analyst** | DeepSeek-V3.2 | Source-backed evidence, data gathering | research_topic, extract_document, search_web, analyze_data |
| 3 | **Designer / Creative** | Phi-4-reasoning-vision-15B | Visual identity, theme, style discovery | apply_theme, generate_theme, discover_style, check_contrast |
| 4 | **Code Agent** | DeepSeek-V3.2 + Qwen2.5-coder-32b | DSL generation, React compilation, self-evolution | generate_dsl, compile_react, compile_revealjs, compile_html |
| 5 | **Assembler / PPTX** | gpt-4o-mini | PptxGenJS orchestration, native object creation | create_pptx, add_chart, add_table, add_shape, add_image |
| 6 | **QA Lead / Reviewer** | Phi-4-reasoning-vision-15B + Playwright | Visual verification, quality scoring, reflective loop | snapshot, screenshot, validate_layout, score_quality |
| 7 | **3D/VFX Agent** (NEW) | DeepSeek-V3.2 | Three.js scenes, particle effects, animations | create_3d_scene, add_particles, animate_element, create_globe |
| 8 | **Layout Agent** (NEW) | GPT-4o / Phi-4-reasoning-vision-15B | Per-slide layout optimization, responsive design | select_layout, optimize_grid, measure_content, validate_fit |

### Agent Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATION                           │
│                                                                  │
│  Phase 1: Strategy (Sequential)                                 │
│  ┌────────┐                                                     │
│  │  CEO   │ → Archetype, Narrative Arc, Slide Order             │
│  └────────┘                                                     │
│                                                                  │
│  Phase 2: Research + Design (Parallel)                          │
│  ┌────────────┐  ┌────────────┐                                 │
│  │ Researcher  │  │  Designer  │  (work simultaneously)         │
│  └────────────┘  └────────────┘                                 │
│                                                                  │
│  Phase 3: Layout + Code (Sequential with feedback)              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │   Layout   │→ │ Code Agent │→ │ 3D/VFX     │  (if needed)   │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                  │
│  Phase 4: Assembly (Parallel per format)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │reveal.js │ │React+3D  │ │  HTML    │ │  PPTX   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  Phase 5: Quality (Sequential, iterative)                       │
│  ┌────────┐  ← Reflective Loop (max 3 iterations) →            │
│  │  QA    │                                                     │
│  └────────┘                                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Human-in-the-Loop (HITL) Checkpoints

> **Why**: Generating a full 10-slide deck in 60s is impressive, but often wrong.
> HITL gates prevent the system from spending expensive GPU/LLM tokens rendering
> 10 slides with the wrong strategic angle.

```
┌─────────────────────────────────────────────────────────────────────┐
│                  HITL CHECKPOINT FLOW                                │
│                                                                      │
│  GATE 1: Narrative Approval                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CEO Agent generates:                                         │  │
│  │  • Presentation archetype (investor-pitch, sales-deck, etc.)  │  │
│  │  • Narrative arc (10-slide outline with titles + key points)  │  │
│  │  • Target audience analysis                                   │  │
│  │                                                                │  │
│  │  → User reviews and approves/edits structure                  │  │
│  │  → User can reorder, add, or remove planned slides            │  │
│  │  → System saves token budget by not generating wrong content  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ▼ (approved)                           │
│  GATE 2: Research & Design Approval                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Researcher + Designer produce:                               │  │
│  │  • Key data points and evidence gathered                      │  │
│  │  • Theme selection (3 previews via Visual Style Discovery)    │  │
│  │  • Brand color palette + typography proposal                  │  │
│  │                                                                │  │
│  │  → User reviews data accuracy and visual direction            │  │
│  │  → User can provide corrections before full render            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ▼ (approved)                           │
│  GATE 3: Full Render (No Gate — Executes Automatically)            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Layout → Code Agent → 3D/VFX → Assembly → QA                │  │
│  │  Full pipeline executes with approved narrative + data        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  FAST MODE (optional):                                              │
│  Skip all gates → full auto pipeline (for drafts/brainstorming)    │
│  User configurable: "I trust the AI" → no gates                    │
│  Default for re-generation: skip Gate 1 (structure preserved)       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Code Agent Architecture

### Self-Evolving Pattern (yoyo-evolve inspired)

The Code Agent is not a static prompt-response system. It has:

#### 6.1 Skills System

Each slide type is a **learnable skill**:

```python
# Skills are stored in MongoDB, versioned, and improved over time
class SlideSkill:
    name: str               # e.g., "title-slide", "problem-slide", "traction-slide"
    version: int            # Incremented on each improvement
    prompt_template: str    # The LLM prompt that generates this slide type
    quality_history: list   # Past quality scores for this skill
    best_examples: list     # Top-scoring outputs (used as few-shot examples)
    common_failures: list   # Known failure patterns to avoid

# Example skill evolution:
# v1: Basic title slide → quality 65%
# v2: Added brand color integration → quality 72%
# v3: Added PreTeXt text fitting → quality 81%
# v4: Added anti-AI-slop processing → quality 88%
```

#### 6.2 Self-Evaluation Loop & Visual Feedback

To address the GLM5 review feedback, the swarm evaluates slides before user review using **Automated Visual Feedback Loops**:

`markdown
1. Structural Regression (QA Agent)
   - Information Density Check: Does this slide have too much text?
   - Title Truncation Test: Will this title fit on a 1920x1080 screen?
   - Narrative Flow: Does slide 5 logically follow slide 4?

2. Visual Regression (Golden Master)
   - Render the slide headlessly (Playwright).
   - Capture a screenshot.
   - Run Structural Similarity Index (SSIM) against Golden Master templates.
   - If the layout is severely broken, force Regeneration.
   - Accessibility Validation: Validate 4.5:1 minimum contrast ratio using the captured screenshot.
`

```
Generate → Evaluate → Learn → Regenerate (if needed)

1. Code Agent generates slide DSL using current skill version
2. QA Agent scores output (0-100)
3. If score < 85%:
   a. QA provides structured feedback (what failed, why, suggestion)
   b. Code Agent updates its skill with the failure pattern
   c. Code Agent regenerates with updated prompt
   d. Repeat up to 3 times
4. If score ≥ 85%:
   a. Skill version incremented
   b. Output added to best_examples for future few-shot
```

#### 6.3 Multi-Provider Routing

Following yoyo-evolve's 12-provider pattern:

```python
class CodeAgentRouter:
    """Routes code generation to optimal provider based on task."""

    ROUTES = {
        "dsl_generation": {
            "primary": "deepseek-v3.2",        # Best for structured JSON
            "fallback": "qwen2.5-coder-32b",   # Free alternative
            "cost": "medium"
        },
        "react_compilation": {
            "primary": "qwen2.5-coder-32b",    # Free, great for code
            "fallback": "deepseek-v3.2",
            "cost": "free"
        },
        "revealjs_html": {
            "primary": "glm-4.7-flash",        # Fast, free, simple HTML
            "fallback": "gpt-4o-mini",
            "cost": "free"
        },
        "threejs_scene": {
            "primary": "deepseek-v3.2",        # Complex 3D code needs strong model
            "fallback": "kimi-k2-thinking",    # Thinking model for complex scenes
            "cost": "medium"
        },
        "layout_optimization": {
            "primary": "phi-4-reasoning",      # Reasoning about spatial layout
            "fallback": "kimi-k2-thinking",
            "cost": "low"
        }
    }
```

---

## 7. reveal.js Integration

### 7.1 Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    reveal.js RENDERER                               │
│                                                                    │
│  Input: Slide DSL v2                                               │
│  Output: Complete reveal.js presentation (index.html + assets)     │
│                                                                    │
│  ┌──────────────────┐    ┌──────────────────┐                     │
│  │  DSL → HTML      │    │  Theme → CSS     │                     │
│  │  Compiler         │    │  Compiler         │                     │
│  │                    │    │                    │                     │
│  │  • <section> tags │    │  • Custom CSS vars │                     │
│  │  • data-auto-anim │    │  • Font imports    │                     │
│  │  • Fragment order │    │  • Color scheme    │                     │
│  │  • Speaker notes  │    │  • Layout rules    │                     │
│  └──────────────────┘    └──────────────────┘                     │
│           │                        │                                │
│           ▼                        ▼                                │
│  ┌─────────────────────────────────────────┐                      │
│  │         reveal.js Runtime                │                      │
│  │                                          │                      │
│  │  Plugins: markdown, highlight, math,    │                      │
│  │           notes, search, zoom           │                      │
│  │                                          │                      │
│  │  Config: {                              │                      │
│  │    hash: true,                          │                      │
│  │    autoAnimateEasing: 'ease-out',       │                      │
│  │    autoAnimateDuration: 0.8,            │                      │
│  │    transition: 'slide',                 │                      │
│  │    backgroundTransition: 'fade',        │                      │
│  │    pdfSeparateFragments: false          │                      │
│  │  }                                      │                      │
│  └─────────────────────────────────────────┘                      │
└────────────────────────────────────────────────────────────────────┘
```

### 7.2 Feature Mapping

| DSL Feature | reveal.js Implementation |
|------------|-------------------------|
| Slide transitions | `data-transition="slide\|fade\|convex\|concave\|zoom"` |
| Progressive reveal | `<li class="fragment fade-in">` |
| Speaker notes | `<aside class="notes">` |
| Two-column layout | CSS Grid within `<section>` |
| Code blocks | `<pre><code data-trim data-line-numbers>` |
| Math equations | KaTeX: `$E = mc^2$` |
| Background images | `data-background-image="url"` |
| Auto-animate | `data-auto-animate` + matching `data-id` attributes |
| Nested slides | Nested `<section>` elements (vertical navigation) |
| Overview / Reading | `Reveal.toggleOverview()` |

### 7.3 reveal.js Theme Integration

Each of our 100+ themes compiles to a reveal.js-compatible CSS file:

```css
/* Generated theme CSS for reveal.js */
:root {
  --r-background-color: #0F172A;
  --r-main-font: 'Inter', sans-serif;
  --r-main-font-size: 42px;
  --r-main-color: #E2E8F0;
  --r-heading-font: 'Cal Sans', sans-serif;
  --r-heading-color: #F8FAFC;
  --r-heading-text-shadow: none;
  --r-heading-letter-spacing: -0.02em;
  --r-link-color: #38BDF8;
  --r-link-color-hover: #7DD3FC;
  --r-selection-background-color: #38BDF8;
  --r-selection-color: #0F172A;
}

/* Anti-AI-slop: no generic gradients, intentional spacing */
.reveal .slides section {
  padding: 2rem 3rem;
  text-align: left; /* Not centered by default — intentional */
}

.reveal .slides h1 {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 1.5rem;
}
```

---

## 8. React + Three.js + 3D Slides

### 8.1 When to Use 3D

The 3D/VFX Agent activates when:
- Slide contains market/geo data → 3D globe
- Slide contains financial projections → 3D bar chart with depth
- Slide type is "hero" or "vision" → particle background
- User explicitly requests 3D/interactive elements
- Pitch deck "traction" slide → animated counter with 3D graph

### 8.2 Three.js Scene Types

```typescript
// Available 3D scene components

// 1. Animated Globe (for market/geo data)
<AnimatedGlobe
  data={[{ lat: 37.7, lng: -122.4, value: 500, label: "SF" }]}
  highlightRegions={["NA", "EU"]}
  rotationSpeed={0.001}
  dotColor="#38BDF8"
  arcColor="#7B2FF7"
/>

// 2. 3D Bar Chart (for financial data)
<ThreeDBarChart
  data={revenueData}
  barColor="#38BDF8"
  depth={0.5}
  cameraAngle={25}
  animate={true}
  animationDuration={1.5}
/>

// 3. Particle Field (hero slide background)
<ParticleField
  count={5000}
  color="#38BDF8"
  speed={0.0005}
  connectionDistance={150}
  mouseInteraction={true}
/>

// 4. Floating Cards (team/feature slides)
<FloatingCards
  cards={teamMembers}
  layout="orbit"
  rotationSpeed={0.003}
  hoverScale={1.1}
/>

// 5. Data Flow Visualization (architecture slides)
<DataFlowViz
  nodes={architectureNodes}
  edges={connections}
  animateFlow={true}
  particleSpeed={2}
/>
```

### 8.3 Performance Guardrails & Lazy Loading

⚠️ **CRITICAL LAZY-LOADING REQUIREMENT:** 
Three.js adds 350-450KB to the bundle size. It MUST be lazily loaded to ensure the presentation loads instantly.
- CSS-only slides and basic UI render immediately.
- 3D content shows a `<Skeleton />` or static image while downloading the Three.js payload.
- Only load `@react-three/fiber` on slides that explicitly require it.

```typescript
const THREE_JS_PERFORMANCE_RULES = {
  maxPolygons: 50_000,           // Per slide scene
  maxParticles: 10_000,          // Per particle system
  targetFPS: 60,                 // Desktop
  mobileTargetFPS: 30,          // Mobile fallback
  maxTextureResolution: 2048,    // Pixels per side
  lazyLoad: true,                // Only init 3D when slide is visible
  fallbackTo2D: true,            // If WebGL not available, render 2D version
  memoryBudget: "50MB",          // Per slide scene
};

// Automatic quality downgrade if FPS drops
function adaptiveQuality(currentFPS: number): QualityLevel {
  if (currentFPS >= 55) return "high";
  if (currentFPS >= 30) return "medium";  // Reduce particles, simplify geometry
  return "low";                            // Disable 3D, show 2D fallback
}
```

---

## 9. Canvas Pro Editor

### 9.1 Architecture (OpenPencil-inspired)

```
┌──────────────────────────────────────────────────────────┐
│                   CANVAS PRO EDITOR                       │
│                                                          │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │  Toolbar      │  │  Canvas       │  │  Properties  │ │
│  │               │  │  (Rendering)  │  │  Panel       │ │
│  │  • Select     │  │               │  │              │ │
│  │  • Text       │  │  HTML5 Canvas │  │  • Position  │ │
│  │  • Shape      │  │  or SVG       │  │  • Size      │ │
│  │  • Image      │  │               │  │  • Color     │ │
│  │  • Chart      │  │  Yoga WASM    │  │  • Font      │ │
│  │  • 3D Scene   │  │  (layout)     │  │  • Animation │ │
│  │  • Line       │  │               │  │  • Style     │ │
│  │  • Export     │  │  Node-based   │  │              │ │
│  │               │  │  element tree │  │              │ │
│  └──────────────┘  └───────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  AI Tools (20+)                                   │   │
│  │  • Auto-align elements    • Smart resize         │   │
│  │  • Content-aware crop     • Style transfer       │   │
│  │  • Generate image here    • Suggest layout       │   │
│  │  • Rewrite text          • Color harmony         │   │
│  │  • Add chart from data    • Create diagram       │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 9.2 Node-Based Element Model

Every element on a slide is a node in a tree:

```typescript
interface SlideNode {
  id: string;
  type: "text" | "image" | "shape" | "chart" | "three_scene" | "group";
  position: { x: number; y: number };
  size: { width: number; height: number };
  rotation: number;
  opacity: number;
  locked: boolean;
  children?: SlideNode[];
  props: Record<string, any>;  // Type-specific properties
}

// The canvas renders this tree, and edits modify the tree
// Changes to the tree re-trigger the render pipeline
```

### 9.3 AI-Powered Editing Tools

| Tool | What It Does | Model Used |
|------|-------------|-----------|
| Auto-align | Snaps elements to grid/alignment guides | Client-side (no AI) |
| Smart resize | Resize while maintaining design quality | Phi-4-reasoning |
| Generate image | "Add image here" → Flux generates contextual image | flux-pro-2 |
| Rewrite text | Rephrase selected text (shorter/longer/more engaging) | glm-4.7-flash |
| Suggest layout | Analyze content and propose better arrangement | Phi-4-reasoning |
| Color harmony | Adjust colors for better contrast/harmony | Client-side algorithm |
| Create chart | Select data → generate chart type recommendation | gpt-4o-mini |
| Remove background | Remove image background | Client-side (remove.bg) |
| Add 3D element | Insert Three.js scene component | DeepSeek-V3.2 |
| Content-aware crop | Crop image keeping the important parts | gemma-3-12b-it (VLM) |

---

## 10. Unified DSL Editor (Replaces Per-Format Editors)

> **Design Decision (from Gemini/GLM5 feedback)**: The original V7 plan had 4 separate editors
> for 4 formats. This creates **State Drift** — the PPTX version and React version of the
> same deck diverge. Users don't want to be a "React Developer" for one slide and a "PPTX
> Editor" for another. **Solution**: One Universal Editor that manipulates the Slide DSL v2
> directly. The 4 renderers act as **Views** of that DSL — you never edit the PPTX; you edit
> the DSL and the PPTX renderer re-compiles in the background.

### 10.1 Architecture: Single Editor, Multiple Views

```
┌──────────────────────────────────────────────────────────────────────┐
│                    UNIFIED DSL EDITOR                                 │
│                                                                      │
│  ┌──────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  Visual Canvas        │  │  Live Preview (switchable)         │  │
│  │  (Figma-lite UX)     │  │                                     │  │
│  │                       │  │  [reveal.js ▼]  [React+3D]        │  │
│  │  • Drag elements     │  │  [HTML]          [PPTX]             │  │
│  │  • Resize handles    │  │                                     │  │
│  │  • Alignment guides  │  │  ┌──────────────────────────────┐  │  │
│  │  • Snap to grid      │  │  │                              │  │  │
│  │  • Double-click text │  │  │   Live rendered slide        │  │  │
│  │  • Property panel    │  │  │   in selected renderer       │  │  │
│  │                       │  │  │                              │  │  │
│  │  Every drag/edit      │  │  └──────────────────────────────┘  │  │
│  │  updates the DSL →   │  │                                     │  │
│  │  all renderers       │  │  Preview auto-updates when DSL     │  │
│  │  re-compile           │  │  changes (debounced 200ms)        │  │
│  └──────────────────────┘  └─────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  DSL Inspector (Advanced Mode — toggle)                    │     │
│  │  JSON tree view of Slide DSL v2 with inline editing       │     │
│  │  • Schema-aware autocompletion                             │     │
│  │  • Live validation (Zod errors shown inline)               │     │
│  │  • CodeMirror 6 for power users who want raw JSON/YAML     │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  AI Tools Panel (20+ tools)                                │     │
│  │  • Auto-align     • Smart resize    • Generate image here  │     │
│  │  • Rewrite text   • Suggest layout  • Color harmony        │     │
│  │  • Create chart   • Add 3D element  • Content-aware crop   │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Slide Thumbnails + Navigation                             │     │
│  │  [1] [2] [3] [4] [5] [6] [7] [8] [+]                     │     │
│  └────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

### 10.2 How It Prevents State Drift

```
                    ┌──────────────────┐
                    │  SLIDE DSL v2    │ ← Single Source of Truth
                    │  (MongoDB)       │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┬──────────────┐
              ▼              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ reveal.js │  │ React+3D │  │   HTML   │  │   PPTX   │
        │  View     │  │  View    │  │  View    │  │  View    │
        └──────────┘  └──────────┘  └──────────┘  └──────────┘

Rule: Edits ALWAYS flow through the DSL, NEVER directly to a renderer.
- User drags a text box → DSL position updates → all renderers re-compile
- User changes font → DSL style updates → all renderers re-compile
- User reorders slides → DSL slide array updates → all renderers re-compile
```

### 10.3 Per-Renderer Affordances (Within the Unified Editor)

While the editor is unified, each renderer preview offers **contextual controls**:

| Renderer Preview | Extra Controls Available |
|-----------------|-------------------------|
| **reveal.js** | Fragment ordering, transition picker, speaker notes, Auto-Animate toggle, vertical slide grouping |
| **React+3D** | Three.js scene inspector, animation timeline, component props panel |
| **HTML** | Raw HTML/CSS view (Monaco toggle), Emmet shortcuts |
| **PPTX** | Placeholder mapping, .potx template selector, PptxGenJS limitations warnings |

### 10.4 Lossy Conversion Transparency (3D → PPTX)

> **Design Decision**: When a user creates a 3D slide (Three.js globe, animated chart),
> the PPTX renderer cannot reproduce the 3D interactivity. Instead of hiding this:

```
┌────────────────────────────────────────────────────────────────────┐
│  PPTX EXPORT TRANSPARENCY                                          │
│                                                                    │
│  When a slide contains 3D/interactive elements:                    │
│                                                                    │
│  1. Auto-capture: High-res screenshot of the 3D scene (1920×1080) │
│  2. Insert as image in PPTX slide with proper positioning          │
│  3. Show user warning:                                             │
│     ┌──────────────────────────────────────────────────────┐      │
│     │  ⚠️ This slide contains interactive 3D elements.     │      │
│     │  In PPTX, these will appear as static images.       │      │
│     │  For full interactivity, use reveal.js or React     │      │
│     │  presentation mode.                                  │      │
│     │  [Customize screenshot angle] [Accept]               │      │
│     └──────────────────────────────────────────────────────┘      │
│                                                                    │
│  4. Add "View interactive version" link in PPTX speaker notes    │
└────────────────────────────────────────────────────────────────────┘
```

### 10.5 Centralized State Sync (WebSocket & CRDT)

To ensure the Unified Editor truly eliminates state drift (especially during multi-user collaboration), the DSL state is managed via:

1. **Centralized Store (Zustand/Redux):** The client holds a single state tree representing the entire presentation DSL.
2. **Yjs CRDTs:** Allows real-time multiplayer editing (like `open-pencil` architecture) without merge conflicts.
3. **WebSocket Broadcasting:** When an agent updates a slide, the patch is broadcasted to all connected clients instantly.
4. **Lineage Tracking:** Every node in the DSL tracks whether it was created by an Agent, a User, or a Template, allowing targeted undo/redo operations.

---

## 11. Theme Engine (100+ Themes)

### 11.1 Theme Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    THEME ENGINE                                     │
│                                                                    │
│  Tier 1: Built-in Themes (24)                                     │
│  ┌──────────────────────────────────────────────────┐             │
│  │ Hand-crafted, tested, anti-AI-slop certified     │             │
│  │ Each theme = colors + typography + spacing +      │             │
│  │              backgrounds + animations + code style │             │
│  └──────────────────────────────────────────────────┘             │
│                                                                    │
│  Tier 2: Generative Theme Engine                                  │
│  ┌──────────────────────────────────────────────────┐             │
│  │ Input: Brand colors (1-3) OR mood keywords       │             │
│  │ Output: Complete theme with all properties        │             │
│  │ Algorithm: Color theory + typography pairing +     │             │
│  │           spacing rules + contrast validation     │             │
│  └──────────────────────────────────────────────────┘             │
│                                                                    │
│  Tier 3: Theme Mutations                                          │
│  ┌──────────────────────────────────────────────────┐             │
│  │ Any theme × 5 mutations = 120+ variants          │             │
│  │ Mutations: warmer, cooler, higher-contrast,       │             │
│  │           more-saturated, desaturated             │             │
│  └──────────────────────────────────────────────────┘             │
│                                                                    │
│  Tier 4: Community Themes (npm packages)                          │
│  ┌──────────────────────────────────────────────────┐             │
│  │ Follow Slidev theme gallery pattern               │             │
│  │ npm install @barise/theme-cyberpunk               │             │
│  │ Users can publish and share themes                │             │
│  └──────────────────────────────────────────────────┘             │
└────────────────────────────────────────────────────────────────────┘
```

### 11.2 Built-in Themes (24)

#### Dark Themes (8)
| # | Name | Primary | Accent | Character |
|---|------|---------|--------|-----------|
| 1 | **Bold Signal** | #FF6B35 | #004E98 | High contrast, dynamic, startup energy |
| 2 | **Electric Studio** | #7B2FF7 | #00F5FF | Futuristic, neon accents, tech |
| 3 | **Dark Developer** | #0F172A / #38BDF8 | #FBBF24 | Developer tools, code-first |
| 4 | **Dark Botanical** | #064E3B | #34D399 | Organic shapes, natural |
| 5 | **Neon Cyber** | #FF00FF | #00FFFF | Cyberpunk, gaming, high energy |
| 6 | **Creative Voltage** | #F59E0B | #8B5CF6 | Creative, energetic, bold |
| 7 | **Midnight Ocean** | #0C4A6E | #06B6D4 | Deep, calm, professional |
| 8 | **Carbon Fiber** | #18181B | #EF4444 | Industrial, sleek, aggressive |

#### Light Themes (8)
| # | Name | Primary | Accent | Character |
|---|------|---------|--------|-----------|
| 9 | **Swiss Modern** | #1A1A1A | #FF0000 | Minimal, grid, Helvetica |
| 10 | **Notebook Tabs** | #F5F5DC | #2563EB | Organized, tabbed, clean |
| 11 | **Pastel Geometry** | #FDE8E8 | #7C3AED | Soft, approachable, shapes |
| 12 | **Split Pastel** | #DBEAFE | #F0ABFC | Dual-tone, modern, fresh |
| 13 | **Vintage Editorial** | #FFF8E7 | #B45309 | Classic, editorial, serif |
| 14 | **Clean Corporate** | #F8FAFC | #0078D4 | Enterprise, trustworthy |
| 15 | **Warm Paper** | #FFFBEB | #D97706 | Warm, inviting, paper texture |
| 16 | **Fresh Green** | #F0FDF4 | #16A34A | Growth, sustainability |

#### Specialty Themes (8)
| # | Name | Primary | Accent | Character |
|---|------|---------|--------|-----------|
| 17 | **Terminal Green** | #0D1117 | #00FF00 | Hacker, monospace, phosphor |
| 18 | **Paper & Ink** | #FAF9F6 | #1A1A1A | Editorial, print, ink texture |
| 19 | **Blueprint** | #1E3A5F | #FFFFFF | Technical, engineering, grid |
| 20 | **Retro Pixel** | #2B2D42 | #EF476F | Retro, pixelated, gaming |
| 21 | **Glassmorphism** | rgba(0,0,0,0.2) | #818CF8 | Frosted glass, depth, blur |
| 22 | **Gradient Mesh** | #667EEA → #764BA2 | Dynamic | Flowing gradients, organic |
| 23 | **Monochrome** | #000000 | #FFFFFF | B&W, photography, stark |
| 24 | **Warm Gradient** | #FF512F → #DD2476 | #FDE68A | Warm, sunset, energy |

### 11.3 Generative Theme Engine

```python
class GenerativeThemeEngine:
    """Generate complete themes from minimal input."""

    def generate_from_brand_colors(
        self,
        primary: str,       # "#FF6B35"
        secondary: str = None,
        accent: str = None,
        mood: str = "professional"  # professional | playful | dark | minimal
    ) -> Theme:
        """
        Algorithm:
        1. Extract hue, saturation, lightness from primary
        2. Generate complementary/analogous colors if secondary/accent not provided
        3. Create 9-shade palette (50-900) for each color
        4. Select typography pair based on mood:
           - professional → Inter + serif heading
           - playful → rounded sans + handwritten accent
           - dark → mono heading + clean body
           - minimal → one font family, weight variations
        5. Compute spacing scale (4px base, 1.5x multiplier)
        6. Generate background patterns (subtle, mood-matched)
        7. Define animation presets (timing, easing)
        8. Validate all color combinations for WCAG AA contrast (≥4.5:1)
        """

    def mutate_theme(self, theme: Theme, mutation: str) -> Theme:
        """
        Mutations:
        - "warmer": shift all hues +15°, increase saturation
        - "cooler": shift all hues -15°, decrease saturation
        - "higher-contrast": darken darks, lighten lights
        - "more-saturated": +20% saturation across palette
        - "desaturated": -30% saturation for muted look
        """
```

### 11.4 Theme Data Structure

```typescript
interface Theme {
  id: string;
  name: string;
  variant: "dark" | "light" | "specialty";
  preset: string;  // Anti-AI-slop preset name

  colors: {
    background: string;
    surface: string;
    primary: string;
    secondary: string;
    accent: string;
    text: string;
    textMuted: string;
    border: string;
    // Full palette (50-900 for each)
    palette: Record<string, Record<number, string>>;
  };

  typography: {
    headingFont: string;
    bodyFont: string;
    monoFont: string;
    scale: number[];  // [12, 14, 16, 18, 20, 24, 30, 36, 48, 60, 72]
    headingWeight: number;
    bodyWeight: number;
    lineHeight: { heading: number; body: number };
    letterSpacing: { heading: string; body: string };
  };

  spacing: {
    base: number;         // 4px
    scale: number[];      // [4, 8, 12, 16, 24, 32, 48, 64, 96, 128]
    slidepadding: number; // Internal slide padding
    elementGap: number;    // Gap between slide elements
  };

  backgrounds: {
    default: string;       // Solid color or gradient
    patterns: string[];    // SVG patterns (subtle texture)
    hero: string;          // Hero slide background variant
  };

  animations: {
    entrance: string;      // "fade-in" | "slide-up" | "scale" | "none"
    transition: string;    // "slide" | "fade" | "zoom" | "convex"
    duration: number;      // seconds
    easing: string;        // "ease-out" | "spring" | "bounce"
  };

  code: {
    theme: string;         // Syntax highlighting theme
    fontFamily: string;
    fontSize: number;
    lineNumbers: boolean;
  };
}
```

---

### 11.6 Accessibility Compliance

All generated output must be accessible, adhering to the following rules:

1. **Color Contrast**: Backgrounds and text pairs are verified against the WCAG AA minimum contrast ratio of 4.5:1 during the generative theme phase.
2. **Screen Reader Shadow DOM**: For HTML and React+3D views, immersive canvas and WebGL content must be shadowed by a visually hidden, semantic HTML DOM tree using ARIA labels (e.g., <div aria-hidden="false" class="sr-only">Financial Projection: </div>).
3. **No Image-Only Content**: Information architecture rules enforce that meaning must not rely solely on images or 3D visuals. 

### 11.5 Brand DNA Extraction (Upload Existing Brand Assets)

> **From Gemini feedback**: "Anti-slop" is currently based on generic design rules.
> Add a "Brand DNA" upload: let the user upload their company's existing PDF/PPTX,
> then use a VLM to extract actual brand identity — not just "blue," but *their* blue.

```python
class BrandDNAExtractor:
    """Extract brand identity from uploaded company materials."""

    async def extract_from_upload(
        self,
        file: UploadedFile,  # .pdf, .pptx, .png, or brand guidelines URL
        vlm_model: str = "phi-4-reasoning-vision-15b"
    ) -> BrandDNA:
        """
        Pipeline:
        1. Convert uploaded file to images (screenshot each page/slide)
        2. Send to VLM (Phi-4-reasoning-vision-15B) with extraction prompt
        3. Extract:
           - Exact brand colors (hex values from actual pixels, not guesses)
           - Typography preferences (font families, weights, sizes)
           - White-space ratios (how much breathing room the brand uses)
           - Logo placement patterns (top-left, centered, with tagline?)
           - Visual style signals (flat, gradient, glassmorphism, minimal)
        4. Generate a BrandDNA object → feed into Generative Theme Engine
        """

    async def generate_brand_theme(self, brand_dna: BrandDNA) -> Theme:
        """Create a theme that matches the user's actual brand identity."""
        return self.theme_engine.generate_from_brand_colors(
            primary=brand_dna.primary_color,
            secondary=brand_dna.secondary_color,
            accent=brand_dna.accent_color,
            mood=brand_dna.detected_mood,
            typography_override={
                "headingFont": brand_dna.heading_font,
                "bodyFont": brand_dna.body_font,
            },
            spacing_ratio=brand_dna.whitespace_ratio,
        )

class BrandDNA(BaseModel):
    primary_color: str          # "#1A73E8" (extracted from actual pixels)
    secondary_color: str | None
    accent_color: str | None
    heading_font: str           # "Montserrat" (detected from slides)
    body_font: str              # "Open Sans"
    whitespace_ratio: float     # 0.35 (35% whitespace detected)
    logo_position: str          # "top-left" | "top-center" | "bottom-right"
    detected_mood: str          # "professional" | "playful" | "corporate"
    visual_style: str           # "flat" | "gradient" | "glassmorphism"
    source_file: str            # Original uploaded file path
```

---

## 12. Generative Template System

### 12.1 Rules, Not Files

Instead of storing 100 static template files, we store **generative rules**:

```python
class LayoutRules:
    """Rules that generate layout based on content analysis."""

    RULES = {
        "title-slide": {
            "conditions": {"has_subtitle": True, "has_tagline": True},
            "layout": "center-focus",
            "grid": {"rows": 3, "columns": 1},
            "element_placement": {
                "title": {"row": 1, "fontSize": "5xl", "fontWeight": 800},
                "subtitle": {"row": 2, "fontSize": "xl", "color": "textMuted"},
                "tagline": {"row": 3, "fontSize": "sm", "color": "accent"}
            }
        },
        "content-heavy": {
            "conditions": {"bullet_count": ">6", "has_image": False},
            "layout": "two-column",
            "grid": {"rows": 1, "columns": 2, "gap": "2rem"},
            "element_placement": {
                "bullets_left": {"column": 1, "items": "first_half"},
                "bullets_right": {"column": 2, "items": "second_half"}
            }
        },
        "visual-emphasis": {
            "conditions": {"has_hero_image": True, "text_count": "<30_words"},
            "layout": "full-bleed-image",
            "grid": {"rows": 1, "columns": 1},
            "element_placement": {
                "image": {"fullCover": True, "overlay": "gradient-bottom"},
                "text": {"position": "bottom-left", "overImage": True}
            }
        }
    }

class TypographyRules:
    """Font pairing algorithms."""

    PAIRINGS = {
        "professional": {"heading": "Inter", "body": "Inter", "mono": "JetBrains Mono"},
        "editorial": {"heading": "Playfair Display", "body": "Source Serif 4", "mono": "Fira Code"},
        "modern": {"heading": "Cal Sans", "body": "Inter", "mono": "Fira Code"},
        "playful": {"heading": "Nunito", "body": "Nunito Sans", "mono": "Fira Code"},
        "minimal": {"heading": "Helvetica Neue", "body": "Helvetica Neue", "mono": "SF Mono"},
        "tech": {"heading": "Space Grotesk", "body": "IBM Plex Sans", "mono": "IBM Plex Mono"},
    }

class AnimationRules:
    """Transition and micro-interaction patterns."""

    PRESETS = {
        "subtle": {
            "entrance": "fade-in",
            "duration": 0.3,
            "stagger": 0.1,
            "easing": "ease-out"
        },
        "dynamic": {
            "entrance": "slide-up",
            "duration": 0.5,
            "stagger": 0.15,
            "easing": "cubic-bezier(0.16, 1, 0.3, 1)"
        },
        "cinematic": {
            "entrance": "scale-fade",
            "duration": 0.8,
            "stagger": 0.2,
            "easing": "cubic-bezier(0.22, 1, 0.36, 1)"
        },
        "none": {
            "entrance": "none",
            "duration": 0,
            "stagger": 0,
            "easing": "linear"
        }
    }
```

### 12.2 AI Template Selector

The Layout Agent uses Phi-4-reasoning to analyze content and select the optimal rule combination:

```python
async def select_template(content: SlideContent) -> LayoutDecision:
    """
    Input: Slide content (text, images, data)
    Output: Layout rules + typography + animation for this specific slide

    Decision factors:
    1. Content density (words, bullets, images, charts)
    2. Slide position in deck (opening slides = more dramatic)
    3. Slide type (title, content, data, closing)
    4. User's selected theme (constrains color/font)
    5. Previous slide layout (variety principle — don't repeat)
    """
```

---

## 13. Current LLM Inventory & Usage (From Production .env + Code)

> **This section documents every LLM model currently configured in the production system**, including how each is initialized, called, and which agents use it. As a startup, we maximize free-tier models and only escalate to paid Azure models when quality demands it.

### 13.1 Complete Model Inventory

The system uses a **tiered model architecture** (T0–T7) with 3-deep fallback chains per request:

| Tier | Internal Name | Actual Model | Provider | Cost | Client Class | Mode |
|------|--------------|--------------|----------|------|-------------|------|
| **T0** | `kimi-k2-thinking` | Kimi-K2-Thinking | Azure AI | $$$ | `AzureKimiClient` | OpenAI-compat |
| **T0.5** | `phi-4-reasoning` | Phi-4-reasoning | Azure AI | $$ | `AzurePhi4Client` | OpenAI-compat (reasoning_content) |
| **T1** | `deepseek-v3` | DeepSeek-V3.2 | Azure AI | $$ | `AzureDeepSeekClient` | OpenAI-compat |
| **T2** | `gpt-4o-mini` | GPT-4o-mini | Azure OpenAI | $ | `AzureGPT4oMiniClient` | OpenAI-compat |
| **T3** | `mistral-medium` | mistral-medium-2505 | Azure OpenAI | $$ | `AzureMistralClient` | OpenAI-compat |
| **T4** | `groq` | llama-3.3-70b-versatile | Groq (8 keys) | **FREE** | `GroqRoundRobinClient` | REST + round-robin |
| **T5** | `cf-glm` | GLM-4.7-Flash | Cloudflare Workers | **FREE** | `CloudflareWorkerClient` | `"text"` mode |
| **T5** | `cf-qwen` | Qwen2.5-Coder-32B-Instruct | Cloudflare Workers | **FREE** | `CloudflareWorkerClient` | `"text"` mode |
| **T5** | `cf-gemma` | Gemma-3-12B-IT | Cloudflare Workers | **FREE** | `CloudflareWorkerClient` | `"text"` mode |
| **T5** | `cf-lucid` | Lucid-Origin | Cloudflare Workers | **FREE** | `CloudflareWorkerClient` | `"image"` mode |
| **T5** | `cf-phoenix` | Phoenix-1.0 | Cloudflare Workers | **FREE** | (configured, workers returning 500 currently) | `"image"` mode |
| **T7** | `openrouter` | qwen/qwen3.6-plus:free | OpenRouter | **FREE** | `OpenRouterClient` | OpenAI-compat |
| **IMG** | `flux-pro-2` | FLUX.1-Kontext-pro | Azure AI | $$ | (config ready, client TBD) | Image gen |

**Free vs Paid Breakdown: 7 FREE models + 5 paid Azure models + 1 image model = startup-friendly**

### 13.2 How Each Provider Is Used (Production Code)

#### Azure Models (T0–T3) — OpenAI SDK with Custom base_url

All Azure models use the standard `openai.AsyncOpenAI` client, NOT the Azure-specific SDK. Each has its own endpoint and deployment name from the .env:

```python
# Pattern used by ALL Azure clients (from azure_client.py)
from openai import AsyncOpenAI

class AzureDeepSeekClient(BaseLLMClient):
    """T1: DeepSeek-V3.2 — Storytelling & narrative content."""
    name = "deepseek-v3"
    provider = "azure-ai"

    def __init__(self):
        # Reads from .env: DEEPSEEK_ENDPOINT, DEEPSEEK_API_KEY
        endpoint = settings.DEEPSEEK_ENDPOINT.strip().strip('"')
        api_key = settings.DEEPSEEK_API_KEY.strip().strip('"')
        self._client = AsyncOpenAI(
            base_url=endpoint.rstrip("/") if endpoint else None,
            api_key=api_key,
        )

    async def complete(self, messages, model=None, temperature=0.7,
                       max_tokens=4096, response_format=None) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=model or settings.DEEPSEEK_MODEL_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.name,
            provider=self.provider,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
        )
```

**Special: Phi-4-reasoning handles `reasoning_content`** — when the main `content` is empty, it extracts the final answer from the model's chain-of-thought:

```python
class AzurePhi4Client(BaseLLMClient):
    """T0.5: Phi-4-reasoning — Reasoning and problem solving."""

    async def complete(self, messages, **kwargs) -> LLMResponse:
        resp = await self._client.chat.completions.create(...)
        content = resp.choices[0].message.content or ""

        # Phi-4 reasoning model returns answer in reasoning_content when content is empty
        if not content and hasattr(resp.choices[0].message, "reasoning_content"):
            reasoning = resp.choices[0].message.reasoning_content
            if reasoning:
                lines = reasoning.split("\n")
                content = lines[-1] if lines else "[See reasoning]"

        return LLMResponse(content=content, ...)
```

#### Groq (T4) — 8-Key Round-Robin, Ultra-Fast, FREE

Groq provides **8 API keys** that rotate via round-robin. On rate limit (429), it advances to the next key. This gives effectively 8× the free-tier quota:

```python
class GroqRoundRobinClient(BaseLLMClient):
    """Round-robin across 8 Groq API keys for ultra-fast inference."""
    name = "groq"
    provider = "groq"

    def __init__(self):
        # Reads GROQ_API_KEY, GROQ_API_KEY1..GROQ_API_KEY7 from .env
        self._keys = settings.groq_keys  # Returns list of non-empty keys
        self._index = 0
        self._lock = threading.Lock()

    def _next_key(self) -> str:
        with self._lock:
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key

    async def complete(self, messages, **kwargs) -> LLMResponse:
        errors = []
        for _attempt in range(len(self._keys)):
            key = self._next_key()
            try:
                return await self._call(key, messages, **kwargs)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    continue  # Rate limited — try next key
                raise
        raise ConnectionError(f"All {len(self._keys)} Groq keys exhausted")

    async def _call(self, api_key, messages, model=None, **kwargs) -> LLMResponse:
        payload = {
            "model": model or "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        return LLMResponse(content=data["choices"][0]["message"]["content"], ...)
```

#### Cloudflare Workers (T5) — FREE, Three Distinct Modes

Each Cloudflare model runs on a **dedicated Worker** (separate URL per model). The `CloudflareWorkerClient` supports three modes:

| Mode | Payload Format | Response Parsing | Used By |
|------|---------------|-----------------|---------|
| `"text"` | `{"message": "prompt"}` | `data["response"]` or `data["content"]` | cf-glm, cf-qwen, cf-gemma |
| `"openai"` | `{"messages": [...], "temperature": ...}` | `data["choices"][0]["message"]["content"]` | (reserved for future) |
| `"image"` | `{"prompt": "description"}` | Raw bytes (image file) | cf-lucid, cf-phoenix |

```python
class CloudflareWorkerClient(BaseLLMClient):
    """Generic Cloudflare Worker LLM client with mode switching."""

    def __init__(self, name: str, worker_url: str, token: str, mode: str = "openai"):
        self.name = name
        self.provider = "cloudflare"
        self._url = worker_url    # Each model has its own Worker URL
        self._token = token       # Bearer token for auth
        self.mode = mode          # "openai" | "text" | "image"

    async def complete(self, messages, **kwargs) -> LLMResponse:
        # Mode determines how we format the request
        if self.mode == "text":
            # pp.py pattern: flatten all messages → single prompt string
            prompt = "\n".join(m["content"] for m in messages)
            payload = {"message": prompt}
        else:
            # Standard OpenAI-compatible format
            payload = {"messages": messages, "temperature": ..., "max_tokens": ...}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        # Mode determines how we parse the response
        if self.mode == "text":
            content = data.get("response") or data.get("content") or data.get("output")
        else:
            if "choices" in data:
                content = data["choices"][0]["message"]["content"]
            elif "result" in data:
                content = data["result"].get("response", str(data["result"]))
            elif "response" in data:
                content = data["response"]

        return LLMResponse(content=content, model=self.name, provider="cloudflare")

    async def generate_image(self, prompt: str) -> bytes:
        """Image mode — sends prompt, returns raw image bytes."""
        payload = {"prompt": prompt}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self._url,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
            )
            resp.raise_for_status()
            return resp.content  # Raw binary image data


# Factory functions — each reads its URL+Token from .env settings
def create_cf_glm_client():
    return CloudflareWorkerClient("cf-glm", settings.CF_WORKER_GLM_URL,
                                   settings.CF_WORKER_GLM_TOKEN, mode="text")

def create_cf_qwen_client():
    return CloudflareWorkerClient("cf-qwen", settings.CF_WORKER_QWEN_URL,
                                   settings.CF_WORKER_QWEN_TOKEN, mode="text")

def create_cf_gemma_client():
    return CloudflareWorkerClient("cf-gemma", settings.CF_WORKER_GEMMA_URL,
                                   settings.CF_WORKER_GEMMA_TOKEN, mode="text")

def create_cf_lucid_client():
    return CloudflareWorkerClient("cf-lucid", settings.CF_WORKER_LUCID_URL,
                                   settings.CF_WORKER_LUCID_TOKEN, mode="image")
```

#### OpenRouter (T7) — FREE Tier

Uses the standard OpenAI SDK pointing to `openrouter.ai/api/v1`:

```python
class OpenRouterClient(BaseLLMClient):
    """T7: OpenRouter free tier — qwen/qwen3.6-plus:free"""
    name = "openrouter"
    provider = "openrouter"

    def __init__(self):
        self._client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTE_SERVICE_API_KEY,
        )
        self._model = "qwen/qwen3.6-plus:free"  # FREE model

    async def complete(self, messages, **kwargs) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
        )
        return LLMResponse(content=resp.choices[0].message.content, ...)
```

### 13.3 Model Router — Task-Based Routing with 3-Deep Fallback

The `ModelRouter` singleton initializes all clients once, then routes by `TaskType`:

```python
class TaskType(str, Enum):
    OUTLINE_PLANNING = "outline_planning"
    NARRATIVE_STORYTELLING = "narrative_storytelling"
    STRUCTURED_JSON = "structured_json"
    TECHNICAL_CODE = "technical_code"
    TRANSLATION_QUICK_EDIT = "translation_quick_edit"
    TEMPLATE_FILL = "template_fill"
    CONTENT_FIT_RESIZE = "content_fit_resize"
    REFINEMENT = "refinement"
    GENERAL = "general"
    DESIGNER_LAYOUT = "designer_layout"

# Routing table — each task has ordered fallback chain
ROUTING_TABLE = {
    TaskType.OUTLINE_PLANNING:       ["kimi-k2-thinking", "phi-4-reasoning", "deepseek-v3"],
    TaskType.NARRATIVE_STORYTELLING: ["deepseek-v3", "mistral-medium", "cf-qwen"],
    TaskType.STRUCTURED_JSON:        ["gpt-4o-mini", "groq", "phi-4-reasoning"],
    TaskType.TECHNICAL_CODE:         ["mistral-medium", "deepseek-v3", "groq"],
    TaskType.TRANSLATION_QUICK_EDIT: ["gpt-4o-mini", "groq", "cf-qwen"],
    TaskType.TEMPLATE_FILL:          ["deepseek-v3", "gpt-4o-mini", "cf-qwen"],
    TaskType.CONTENT_FIT_RESIZE:     ["gpt-4o-mini", "groq", "cf-qwen"],
    TaskType.REFINEMENT:             ["deepseek-v3", "gpt-4o-mini", "mistral-medium"],
    TaskType.GENERAL:                ["deepseek-v3", "gpt-4o-mini", "cf-qwen"],
    TaskType.DESIGNER_LAYOUT:        ["deepseek-v3", "cf-glm", "cf-gemma",
                                       "mistral-medium", "phi-4-reasoning"],
}
```

**Fallback behavior**: Each model gets `MAX_RETRIES_PER_MODEL = 2` attempts. On retry, temperature increases by 0.1 for variety. On exhaustion, moves to next model in chain. Every attempt is logged for observability (`llm_call_success` / `llm_call_failed`).

### 13.4 Current Agent → Model Assignments (Production)

| Agent | DEFAULT_MODEL | FALLBACK_MODELS | Why This Assignment |
|-------|-------------|----------------|---------------------|
| **CEO Agent** | `kimi-k2-thinking` | `phi-4-reasoning`, `deepseek-v3` | Needs deep reasoning for narrative structure |
| **Researcher** | `gpt-4o-mini` | `deepseek-v3`, `cf-qwen` | Fast extraction, falls back to FREE |
| **Designer** | `deepseek-v3` | `cf-glm`, `cf-gemma`, `mistral-medium`, `phi-4-reasoning` | 4-deep fallback prioritizes FREE workers |
| **Code Agent** | `mistral-medium` | `deepseek-v3`, `cf-qwen`, `groq` | Code quality priority, FREE fallbacks |
| **Assembler** | `deepseek-v3` | `mistral-medium`, `gpt-4o-mini` | Reliable structuring |
| **QA Agent** | `gpt-4o-mini` | `deepseek-v3`, `mistral-medium` | Fast validation checks |
| **Base Agent** | `deepseek-v3` | `gpt-4o-mini`, `mistral-medium`, `cf-qwen` | Default for unspecified agents |

### 13.5 Image Models — Current Status

| Model | Provider | Status | Response Format | Use Case |
|-------|----------|--------|----------------|----------|
| **FLUX.1-Kontext-pro** | Azure AI | ✅ Configured (env ready) | TBD (client not yet built) | Hero images, key visuals (PRIMARY) |
| **Lucid-Origin** | Cloudflare Worker | ⚠️ Was returning 500 | `{"prompt": "..."}` → raw bytes | Artistic backgrounds, patterns |
| **Phoenix-1.0** | Cloudflare Worker | ⚠️ Was returning 500 | `{"prompt": "..."}` → raw bytes (saved as .jpg) | General illustrations |

**Current fallback**: When image workers fail, the system generates **gradient placeholders** with theme-aware colors (see `image_service.py`).

### 13.6 V7 New Models to Add to Router

For V7, the following new `TaskType` entries and model assignments are needed:

```python
# NEW task types for V7
class TaskType(str, Enum):
    # ... existing ...
    REVEALJS_HTML = "revealjs_html"           # reveal.js slide HTML generation
    THREEJS_SCENE = "threejs_scene"           # Three.js 3D scene code
    LAYOUT_OPTIMIZATION = "layout_optimization"  # Spatial layout reasoning
    IMAGE_PROMPT = "image_prompt"             # Image prompt engineering
    SLIDE_QA = "slide_qa"                     # Visual QA with VLM

# NEW routing entries for V7
ROUTING_TABLE.update({
    TaskType.REVEALJS_HTML:       ["cf-glm", "gpt-4o-mini", "cf-qwen"],      # FREE first!
    TaskType.THREEJS_SCENE:       ["deepseek-v3", "mistral-medium", "cf-qwen"],
    TaskType.LAYOUT_OPTIMIZATION: ["phi-4-reasoning", "kimi-k2-thinking", "deepseek-v3"],
    TaskType.IMAGE_PROMPT:        ["gpt-4o-mini", "cf-glm", "groq"],          # FREE fallbacks
    TaskType.SLIDE_QA:            ["cf-gemma", "phi-4-reasoning", "gpt-4o-mini"],  # Gemma VLM first (FREE)
})
```

### 13.7 Cost Optimization Strategy (Startup Budget)

```
┌────────────────────────────────────────────────────────────────────┐
│                COST OPTIMIZATION — STARTUP BUDGET                  │
│                                                                    │
│  Rule 1: Default to FREE models (CF Workers, Groq, OpenRouter)   │
│  Rule 2: Escalate to Azure only for quality-critical tasks        │
│  Rule 3: Every routing decision must justify cost vs quality      │
│                                                                    │
│  FREE MODELS (use first):                                         │
│  ├── Groq (llama-3.3-70b-versatile) — 8 keys × round-robin      │
│  ├── cf-glm (GLM-4.7-Flash) — fast text, reveal.js HTML          │
│  ├── cf-qwen (Qwen2.5-Coder-32B) — code generation fallback     │
│  ├── cf-gemma (Gemma-3-12B-IT) — lightweight vision (non-critical)│
│  ├── cf-lucid (Lucid-Origin) — artistic image generation         │
│  ├── cf-phoenix (Phoenix-1.0) — general image generation         │
│  └── openrouter (qwen3.6-plus:free) — extra free fallback        │
│                                                                    │
│  ⚠️ FREE TIER LIMITATIONS (from GLM5 review):                    │
│  ├── CF Workers AI: ~3-10 inferences/day for large models        │
│  │   → UNSUSTAINABLE for production. Plan paid fallbacks.        │
│  ├── Groq 8-key rotation: may violate ToS. Monitor closely.     │
│  ├── Gemma-3-12B: too small (12B params) for reliable visual QA  │
│  │   → Use Phi-4-reasoning-vision-15B for critical QA tasks      │
│  └── All free models: quality varies. NEVER use for hero content │
│                                                                    │
│  PAID MODELS (escalate when needed):                              │
│  ├── gpt-4o-mini ($) — cheap, fast, structured JSON              │
│  ├── deepseek-v3 ($$) — narrative quality                        │
│  ├── mistral-medium ($$) — code quality                          │
│  ├── phi-4-reasoning ($$) — layout reasoning                     │
│  ├── kimi-k2-thinking ($$$) — strategy/planning ONLY             │
│  └── flux-pro-2 ($$) — hero images ONLY                         │
│                                                                    │
│  Example 10-slide pitch deck cost estimate:                       │
│  ├── CEO planning (1 kimi call): $0.03                           │
│  ├── Research (2 gpt-4o-mini calls): $0.01                       │
│  ├── Design (1 deepseek + 2 cf-glm FREE): $0.02                 │
│  ├── Code gen (10 slides × mistral): $0.10                       │
│  ├── Assembly (1 deepseek): $0.02                                │
│  ├── QA (2 gpt-4o-mini + 1 phi-4-vision): $0.04                 │
│  ├── QA retries (avg 1.5 retry passes): $0.06                   │
│  ├── Images (2 flux hero + 3 free cf-lucid): $0.10              │
│  ├── Higher-tier fallbacks (avg 10% escalation): $0.04           │
│  └── TOTAL: ~$0.42 per presentation (realistic range $0.35-$0.50)│
│                                                                    │
│  Previous estimate of $0.29 was overly optimistic — didn't account│
│  for QA retry passes, higher-tier fallbacks, and image generation │
│  costs. The $0.35-$0.50 range is production-realistic.           │
│                                                                    │
│  Without free models: ~$0.85 per presentation (2× more)          │
└────────────────────────────────────────────────────────────────────┘
```

### 13.8 .env Configuration Pattern

All model credentials follow this pattern in the `.env` file (keys redacted):

```bash
# Azure Models — each has: endpoint, api_key, deployment_name
AZURE_GPT4O_MINI_ENDPOINT=https://[region].openai.azure.com/openai/v1/
AZURE_GPT4O_MINI_API_KEY=<redacted>
AZURE_GPT4O_MINI_DEPLOYMENT_NAME=gpt-4o-mini

DEEPSEEK_ENDPOINT=https://[region].services.ai.azure.com/openai/v1/
DEEPSEEK_API_KEY=<redacted>
DEEPSEEK_MODEL_NAME=DeepSeek-V3.2

AZURE_KIMI_ENDPOINT=https://[region].services.ai.azure.com/openai/v1/
AZURE_KIMI_API_KEY=<redacted>
AZURE_KIMI_VERSION_DEPLOYMENT=Kimi-K2-Thinking

Mistral_endpoint=https://[region].openai.azure.com/openai/v1/
Mistral_api_key=<redacted>
Mistral_deployment_name=mistral-medium-2505

Phi-4-reasoning_endpoint=https://[region].openai.azure.com/openai/v1/
Phi-4-reasoning_deployment_name=Phi-4-reasoning
Phi-4-reasoning_api_key=<redacted>

# Cloudflare Workers — each has: URL (unique worker), TOKEN
CF_WORKER_GLM_URL=https://[worker-name].workers.dev
CF_WORKER_GLM_TOKEN=<redacted>
CF_WORKER_QWEN_URL=https://[worker-name].workers.dev
CF_WORKER_QWEN_TOKEN=<redacted>
CF_WORKER_GEMMA_URL=https://[worker-name].workers.dev
CF_WORKER_GEMMA_TOKEN=<redacted>
CF_WORKER_PHOENIX_URL=https://[worker-name].workers.dev/
CF_WORKER_PHOENIX_TOKEN=<redacted>
CF_WORKER_LUCID_URL=https://[worker-name].workers.dev
CF_WORKER_LUCID_TOKEN=<redacted>

# Groq — 8 keys for round-robin
GROQ_API_KEY=<redacted>
GROQ_API_KEY1=<redacted>
# ... through GROQ_API_KEY7

# OpenRouter — free tier
openroute_service_api_key=<redacted>
openroute_model_free=qwen/qwen3.6-plus:free

# Image Generation — Azure Flux
AZURE_FLUX_ENDPOINT=https://[region].openai.azure.com/openai/v1/
AZURE_FLUX_API_KEY=<redacted>
AZURE_FLUX_DEPLOYMENT_NAME=FLUX.1-Kontext-pro
```

### 13.9 Adding a New Model (Checklist)

To add a new model to the system:

1. **Add .env vars**: `MODEL_ENDPOINT`, `MODEL_API_KEY`, `MODEL_DEPLOYMENT_NAME`
2. **Add to `config.py`**: Pydantic `Field()` with `validation_alias` matching .env key
3. **Create client class** in `app/services/llm/`:
   - Extend `BaseLLMClient`
   - Implement `async def complete()` → `LLMResponse`
   - For Cloudflare: use `CloudflareWorkerClient` with appropriate `mode`
4. **Register in `model_router.py`**: Add to `_init_clients()` dict
5. **Add to `ROUTING_TABLE`**: Assign to appropriate `TaskType` chains
6. **Update agent defaults**: Set `DEFAULT_MODEL` / `FALLBACK_MODELS` as needed

---

## 14. Image Generation Pipeline (Flux-First)

### 14.1 Flux-First Strategy

```
┌────────────────────────────────────────────────────────────────────┐
│                IMAGE GENERATION PIPELINE                           │
│                                                                    │
│  Priority Order:                                                   │
│                                                                    │
│  1. flux-pro-2 (Azure) — PRIMARY                                  │
│     • Hero slides, key visuals, product mockups                   │
│     • Quality: Highest, photorealistic                            │
│     • Cost: ~$0.05/image (Azure subscription)                     │
│     • Resolution: 1024×1024 default                               │
│                                                                    │
│  2. phoenix-1.0 (Cloudflare Free) — SECONDARY                    │
│     • Supporting illustrations, icons, backgrounds                 │
│     • Quality: Good, general purpose                              │
│     • Cost: FREE                                                  │
│     • Resolution: 1024×1024                                       │
│                                                                    │
│  3. lucid-origin (Cloudflare Free) — ARTISTIC                    │
│     • Background textures, abstract art, patterns                 │
│     • Quality: Artistic, creative                                 │
│     • Cost: FREE                                                  │
│     • Resolution: 1024×1024                                       │
│                                                                    │
│  Routing Logic:                                                    │
│  if slide.type == "hero" or slide.importance == "high":           │
│      model = "flux-pro-2"                                         │
│  elif slide.needs_artistic_background:                             │
│      model = "lucid-origin"                                       │
│  else:                                                             │
│      model = "phoenix-1.0"                                        │
│                                                                    │
│  Fallback Chain: flux-pro-2 → phoenix-1.0 → lucid-origin         │
└────────────────────────────────────────────────────────────────────┘
```

### 14.2 Image Prompt Engineering

```python
class SlideImagePromptBuilder:
    """Build optimized prompts for slide images."""

    def build_prompt(self, slide: SlideDSL, context: DeckContext) -> str:
        """
        Strategy: Generate images that look INTENTIONAL for presentations.
        Never: stock-photo aesthetic, clip-art, generic business imagery.
        Always: branded colors, consistent style, professional quality.
        """

        base_prompt = f"""
        Professional presentation visual for a {context.archetype} deck.
        Brand colors: {context.theme.colors.primary}, {context.theme.colors.accent}.
        Style: {context.theme.preset} aesthetic.
        Slide topic: {slide.content.heading}.

        Requirements:
        - Clean, modern, professional
        - Consistent with the deck's visual identity
        - No text in the image (text is added as overlay)
        - {context.theme.variant} mode compatible
        - High contrast suitable for projection
        """

        return base_prompt
```

### 14.3 Image Processing Pipeline

```
Generate → Resize → Optimize → Place

1. Generate: flux-pro-2 at 1024×1024
2. Resize: Crop/fit to slide layout dimensions
3. Optimize: WebP compression for HTML, PNG for PPTX
4. Place: Insert at correct position per layout rules
5. Fallback: If generation fails, use gradient background with text overlay
```

---

## 15. Thinking Models Strategy

### 15.1 Model Assignment Matrix

```
┌─────────────────────────────────────────────────────────────────────┐
│                  THINKING MODELS STRATEGY                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Kimi-K2-Thinking (Azure)                                    │   │
│  │  Role: Strategic Thinking & Complex Reasoning                │   │
│  │                                                               │   │
│  │  Used by: CEO Agent, Orchestrator                            │   │
│  │  Tasks:                                                       │   │
│  │    • Narrative structure decisions                            │   │
│  │    • Presentation archetype selection                        │   │
│  │    • Multi-step planning (which slides, what order)          │   │
│  │    • Conflict resolution between agent outputs               │   │
│  │    • Complex content synthesis (merging research findings)    │   │
│  │  Cost: ~$0.01/request (thinking tokens are expensive)        │   │
│  │  When: Only planning phases, never bulk generation           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Phi-4-reasoning-vision-15B (Azure)                         │   │
│  │  Role: Visual/Spatial Reasoning & Design QA (MULTIMODAL)    │   │
│  │                                                               │   │
│  │  Used by: Layout Agent, Designer Agent, QA Agent             │   │
│  │  Tasks:                                                       │   │
│  │    • Visual slide auditing (screenshot → feedback)           │   │
│  │    • Layout quality scoring (visual grounding)               │   │
│  │    • Content-to-visual mapping                               │   │
│  │    • Accessibility validation (contrast, readability)        │   │
│  │    • Anti-AI-slop detection (visual pattern analysis)        │   │
│  │  Note: Phi-4-reasoning (text-only) is for MATH/LOGIC only.  │   │
│  │  For spatial/visual tasks, MUST use the -vision-15B variant  │   │
│  │  which supports GUI grounding with 3,600 visual tokens.     │   │
│  │  Cost: Lower than Kimi, good reasoning at moderate cost      │   │
│  │  When: All visual validation, design QA, layout critique     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Thinking models are NEVER used for:                                │
│    ✗ Bulk text generation (use DeepSeek-V3.2 or glm-4.7-flash)   │
│    ✗ Code generation (use Qwen2.5-coder-32b or DeepSeek-V3.2)    │
│    ✗ Image generation (use Flux/Phoenix/Lucid)                     │
│    ✗ Simple transformations (use gpt-4o-mini)                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 15.2 Full Model Routing Table

| Task | Primary Model | Fallback | Cost |
|------|--------------|----------|------|
| Strategy/Planning | Kimi-K2-Thinking | DeepSeek-V3.2 | $$$ |
| Layout Reasoning | GPT-4o | Phi-4-reasoning-vision-15B | $$ |
| DSL Generation | DeepSeek-V3.2 | Qwen2.5-coder-32b | $$ |
| React Code | Qwen2.5-coder-32b | DeepSeek-V3.2 | FREE |
| reveal.js HTML | glm-4.7-flash | gpt-4o-mini | FREE |
| Three.js Scenes | DeepSeek-V3.2 | Kimi-K2-Thinking | $$ |
| Text Content | glm-4.7-flash | gpt-4o-mini | FREE |
| Summaries | gpt-4o-mini | glm-4.7-flash | $ |
| Image (Hero) | FLUX.1-Kontext-pro | phoenix-1.0 | $$ |
| Image (General) | phoenix-1.0 | lucid-origin | FREE |
| Image (Artistic) | lucid-origin | phoenix-1.0 | FREE |
| Visual QA | Phi-4-reasoning-vision-15B | GPT-4o | $$ |
| Design Scoring | Phi-4-reasoning-vision-15B | GPT-4o | $$ |

---

## 16. Fast Generation Techniques

### 16.1 Target: <60s for 10-slide Deck

```
┌────────────────────────────────────────────────────────────────────┐
│                GENERATION TIMELINE (10 slides)                     │
│                                                                    │
│  0s ─────── 5s ─────── 15s ─────── 30s ─────── 45s ─── 55s      │
│  │          │           │            │            │       │        │
│  ▼          ▼           ▼            ▼            ▼       ▼        │
│  Strategy   Research    DSL Gen      Render       QA     Deliver  │
│  (CEO)      + Design    (Code Agent) (Parallel    Check          │
│             (Parallel)  (Streaming)  renderers)                   │
│                                                                    │
│  Techniques:                                                       │
│  1. Parallel agent execution (Research ∥ Design)                  │
│  2. Streaming DSL (slides appear as generated)                    │
│  3. Progressive rendering (skeleton → content → images → anim)   │
│  4. Parallel renderer execution (all 4 formats simultaneously)    │
│  5. Redis caching (themes, fonts, common layouts)                 │
│  6. Batch LLM calls (3-4 slides per API call)                    │
│  7. PreTeXt pre-measurement (avoid layout reflows)               │
│  8. Image generation parallel with slide content                  │
└────────────────────────────────────────────────────────────────────┘
```

### 16.2 Streaming Architecture

```python
async def generate_presentation_streaming(request: PresentationRequest):
    """
    Stream slides to the frontend as they're generated.
    User sees slides appearing in real-time, not waiting for completion.
    """

    # Phase 1: Strategy (fast, ~2s)
    strategy = await ceo_agent.plan(request)
    yield {"event": "strategy_complete", "data": strategy}

    # Phase 2: Parallel research + design (~8s)
    research_task = asyncio.create_task(researcher_agent.research(strategy))
    design_task = asyncio.create_task(designer_agent.design(strategy))
    research, design = await asyncio.gather(research_task, design_task)
    yield {"event": "design_ready", "data": design.theme}

    # Phase 3: Stream slides as they're generated
    async for slide_dsl in code_agent.generate_slides_streaming(strategy, research, design):
        # Each slide is rendered immediately as it arrives
        rendered = await render_router.render_single(slide_dsl, design.theme)
        yield {"event": "slide_ready", "data": rendered}

    # Phase 4: Quick QA pass
    quality = await qa_agent.quick_check(all_slides)
    yield {"event": "generation_complete", "data": quality}
```

### 16.3 Caching Strategy

```python
CACHE_LAYERS = {
    # Theme computations: expensive color math, cached forever
    "theme:*": {"ttl": None, "storage": "redis"},

    # Font metrics: PreTeXt measurements, cached per font+size
    "font_metrics:*": {"ttl": 86400, "storage": "redis"},

    # Common layouts: frequently used slide templates
    "layout:*": {"ttl": 86400, "storage": "redis"},

    # LLM responses: exact prompt matches (dedup)
    "llm_response:*": {"ttl": 3600, "storage": "redis"},

    # Generated images: reuse across presentations
    "image:*": {"ttl": 604800, "storage": "mongodb_gridfs"},

    # Slide skills: best examples for few-shot (permanent)
    "skill:*": {"ttl": None, "storage": "mongodb"},
}
```

---

## 17. PreTeXt.js Integration

### 17.1 Three Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│               PreTeXt INTEGRATION POINTS                         │
│                                                                  │
│  Point 1: During DSL Generation (Code Agent)                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Before committing text to a slide, measure it:          │   │
│  │                                                           │   │
│  │  prepared = prepare("AI Infrastructure...", "bold 32px") │   │
│  │  { height, lineCount } = layout(prepared, 800, 40)       │   │
│  │                                                           │   │
│  │  if height > container_height:                            │   │
│  │      option_a: reduce_font_size(prepared, min=24)         │   │
│  │      option_b: split_into_two_slides()                    │   │
│  │      option_c: summarize_text(shorter_version)            │   │
│  │                                                           │   │
│  │  Cost: 0.09ms per measurement — negligible                │   │
│  └─────────────────────────────────────────────────────────┘   │

│  ⚠️ MATURITY RISK & FALLBACK (from GLM5 review):             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PreTeXt.js is extremely new (created March 2026).        │   │
│  │  It may have undiscovered edge cases or browser bugs.     │   │
│  │                                                           │   │
│  │  Fallback Strategy:                                       │   │
│  │  If PreTeXt throws errors or fails to load:               │   │
│  │  1. Gracefully degrade to standard canvas.measureText() │   │
│  │  2. Use DOM-based hidden div measurement (slower)         │   │
│  │  3. Fall back to conservative character-count heuristics  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Point 2: During Component Compilation                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Inform font-size decisions:                              │   │
│  │  - Automatic font reduction if close to overflow          │   │
│  │  - Minimum 24pt enforced (investor deck readability)      │   │
│  │  - walkLineRanges() for shrink-wrap layouts               │   │
│  │  - layoutNextLine() for variable-width columns            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Point 3: During QA (Before Browser Render)                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Fast pre-check catches obvious layout issues:            │   │
│  │  - Text overflow detection (0.09ms vs 3s browser check)   │   │
│  │  - Title truncation warnings                              │   │
│  │  - Bullet count validation                                │   │
│  │  - Only proceed to browser if PreTeXt passes             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 17.2 Key APIs

| API | Purpose | Performance |
|-----|---------|-------------|
| `prepare(text, font)` | One-time text analysis + measurement data | ~5ms (one-time) |
| `layout(prepared, width, lineHeight)` | Fast height/lineCount calculation | 0.09ms |
| `prepareWithSegments()` | Rich segment structure for mixed-style text | ~8ms (one-time) |
| `walkLineRanges()` | Binary search for optimal container width | ~1ms |
| `layoutNextLine()` | Variable-width line-by-line layout | 0.05ms/line |

---

## 18. Pre-Built Templates

### 18.1 12 Curated Anti-AI-Slop Presets (from frontend-slides)

Each preset is a **complete visual system** — not just colors, but an entire aesthetic philosophy:

| Preset | Category | Character | When to Use |
|--------|----------|-----------|-------------|
| **Bold Signal** | Dark | High contrast, accent glows, sharp typography | Startup pitch, product launch |
| **Electric Studio** | Dark | Neon accents, tech aesthetic, futuristic | AI/ML, deep tech, developer tools |
| **Dark Botanical** | Dark | Organic shapes, natural textures, earthy tones | Sustainability, health, wellness |
| **Creative Voltage** | Dark | Energetic, warm accents, bold geometry | Creative industry, design, media |
| **Notebook Tabs** | Light | Organized, tab dividers, clean structure | Consulting, business plans, reports |
| **Pastel Geometry** | Light | Soft shapes, approachable, friendly | Education, consumer apps, community |
| **Swiss Modern** | Specialty | Grid system, Helvetica, precise spacing | Finance, legal, institutional |
| **Terminal Green** | Specialty | Phosphor green, monospace, hacker aesthetic | Cybersecurity, developer tooling |
| **Paper & Ink** | Specialty | Editorial, ink texture, classic typography | Publishing, media, journalism |
| **Neon Cyber** | Specialty | Cyberpunk, glitch effects, neon overlay | Gaming, entertainment, esports |
| **Vintage Editorial** | Light | Sepia tones, serif fonts, print aesthetic | Luxury brands, fashion, heritage |
| **Split Pastel** | Light | Dual-tone sections, modern geometry | Consumer products, lifestyle |

### 18.2 Visual Style Discovery UX

```
User Request: "Create a pitch deck for my AI startup"

System generates 3 preview slides, each with a different preset:

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  PREVIEW A  │  │  PREVIEW B  │  │  PREVIEW C  │
│             │  │             │  │             │
│ Bold Signal │  │  Electric   │  │  Dark       │
│ (Dark)      │  │  Studio     │  │  Developer  │
│             │  │  (Dark)     │  │  (Dark)     │
│ AI-focused  │  │  Futuristic │  │  Code-first │
│ startup     │  │  neon       │  │  minimal    │
│ energy      │  │  aesthetic   │  │  technical  │
│             │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
      [A]              [B]              [C]

User selects B → Electric Studio applied across entire deck
```

### 18.3 Anti-AI-Slop Processing

Every generated slide passes through the Anti-AI-Slop filter:

```python
class AntiAISlopProcessor:
    """
    Detects and eliminates generic AI aesthetics.
    Based on frontend-slides' design principles.
    """

    SLOP_INDICATORS = [
        "generic gradient backgrounds (blue→purple default)",
        "stock-photo-style imagery",
        "centered-everything layout",
        "too-perfect symmetry (needs intentional asymmetry)",
        "overuse of icons from a single icon pack",
        "generic sans-serif without personality",
        "equal spacing everywhere (needs visual hierarchy)",
        "no white space (cramped layouts)",
        "rainbow color usage (too many colors)",
    ]

    def process(self, slide: RenderedSlide) -> RenderedSlide:
        """
        For each slop indicator detected:
        1. Flag the issue
        2. Apply the corresponding fix from the active preset
        3. Re-validate
        """
```

---

## 19. Reading vs Presentation Modes

### 19.1 Two Distinct Experiences

```
┌────────────────────────────────────────────────────────────────────┐
│                    MODE COMPARISON                                  │
│                                                                    │
│  ┌─────────────────────────┐  ┌─────────────────────────┐        │
│  │   READING MODE          │  │   PRESENTATION MODE      │        │
│  │                         │  │                         │        │
│  │  ┌───────────────────┐ │  │  ┌───────────────────┐ │        │
│  │  │ Table of Contents │ │  │  │                   │ │        │
│  │  │ 1. Title          │ │  │  │   FULL SCREEN     │ │        │
│  │  │ 2. Problem        │ │  │  │   SLIDE VIEW      │ │        │
│  │  │ 3. Solution       │ │  │  │                   │ │        │
│  │  │ 4. Market         │ │  │  │   NeuralScale     │ │        │
│  │  │ 5. Traction       │ │  │  │   ═══════════     │ │        │
│  │  └───────────────────┘ │  │  │   AI Infra...     │ │        │
│  │                         │  │  │                   │ │        │
│  │  [Slide 1]              │  │  │   [← →]          │ │        │
│  │  ┌───────────────────┐ │  │  └───────────────────┘ │        │
│  │  │ NeuralScale       │ │  │                         │        │
│  │  │ AI Infrastructure │ │  │  Speaker Notes Window:  │        │
│  │  │                   │ │  │  ┌───────────────────┐ │        │
│  │  │ [Expanded notes   │ │  │  │ Key points:       │ │        │
│  │  │  visible inline]  │ │  │  │ • $50K savings    │ │        │
│  │  └───────────────────┘ │  │  │ • Time: 2:30      │ │        │
│  │                         │  │  │ [Next slide ──→]  │ │        │
│  │  [Slide 2]              │  │  └───────────────────┘ │        │
│  │  ┌───────────────────┐ │  │                         │        │
│  │  │ The Problem       │ │  │  Controls:              │        │
│  │  │ • GPU costs $50K  │ │  │  ← → ↑ ↓ Space ESC    │        │
│  │  │ • Downtime $100K  │ │  │  F = fullscreen         │        │
│  │  │ [Chart visible]   │ │  │  O = overview           │        │
│  │  └───────────────────┘ │  │  S = speaker notes      │        │
│  │                         │  │                         │        │
│  │  (Scrollable document)  │  │  (Keyboard navigation)  │        │
│  └─────────────────────────┘  └─────────────────────────┘        │
│                                                                    │
│  Features unique to Reading Mode:     Presentation Mode:           │
│  • Scrollable (no page breaks)        • Full screen                │
│  • TOC sidebar navigation             • Keyboard nav               │
│  • Inline speaker notes               • Speaker notes window       │
│  • Expandable details sections        • Timer                      │
│  • Annotations/comments visible       • Transitions/animations     │
│  • Dark/light mode toggle             • Fragment progressive reveal│
│  • Print-friendly                     • Overview grid (ESC)        │
│  • Search across all slides           • Zoom (Alt+click)           │
└────────────────────────────────────────────────────────────────────┘
```

### 19.2 Implementation Per Renderer

| Renderer | Reading Mode | Presentation Mode |
|----------|-------------|-------------------|
| **reveal.js** | `Reveal.toggleOverview()` + custom scroll CSS | Default slideshow mode |
| **React+3D** | `<VerticalScroll>` wrapper, all slides visible | `<FullscreenCarousel>` with keyboard |
| **HTML** | Default render = scrollable document | `?present=true` URL param → slideshow JS |
| **PPTX** | N/A (PowerPoint has its own) | N/A (PowerPoint has its own) |

---

## 20. Slide DSL v2 Specification

### 20.1 Top-Level Schema

```json
{
  "version": "2.0",
  "presentation": {
    "id": "deck_uuid",
    "title": "NeuralScale",
    "archetype": "investor-pitch",
    "theme": {
      "id": "electric-studio",
      "variant": "dark",
      "preset": "electric-studio",
      "customOverrides": {}
    },
    "aspectRatio": "16:9",
    "dimensions": { "width": 1920, "height": 1080 },
    "renderers": ["revealjs", "pptx"],
    "modes": ["reading", "presentation"],
    "metadata": {
      "author": "Jane Doe",
      "company": "NeuralScale Inc.",
      "date": "2026-07-01",
      "version": 1
    }
  },
  "slides": [
    {
      "index": 0,
      "id": "slide_uuid",
      "type": "title-slide",
      "layout": "center-focus",
      "section": "opening",
      "content": {
        "title": "NeuralScale",
        "subtitle": "AI Infrastructure for the Next Billion Parameters",
        "presenter": "Jane Doe, CEO",
        "tagline": "Series A — $12M"
      },
      "style": {
        "background": { "type": "gradient-radial", "colors": ["#0F172A", "#1E293B"] },
        "accentColor": "#00F5FF",
        "animation": "cinematic"
      },
      "elements": [
        {
          "id": "elem_uuid",
          "type": "text",
          "content": "NeuralScale",
          "position": { "x": 0.1, "y": 0.3 },
          "size": { "width": 0.8, "height": 0.15 },
          "style": { "fontSize": "5xl", "fontWeight": 800, "color": "white" }
        }
      ],
      "speakerNotes": "Welcome everyone. Today I'll show you how NeuralScale...",
      "fragments": [
        { "elementId": "elem_1", "order": 1, "animation": "fade-in" },
        { "elementId": "elem_2", "order": 2, "animation": "slide-up" }
      ],
      "threeScene": null,
      "customFields": {},
      "revealConfig": {
        "transition": "slide",
        "autoAnimate": true,
        "backgroundTransition": "fade"
      }
    }
  ],
  "generationMetadata": {
    "skillVersions": { "title-slide": 4, "problem-slide": 3 },
    "qualityScore": 88,
    "iterations": 2,
    "modelUsage": {
      "strategy": "kimi-k2-thinking",
      "content": "deepseek-v3.2",
      "layout": "phi-4-reasoning",
      "images": "flux-pro-2"
    },
    "totalCost": "$0.23",
    "generationTime": "47s"
  }
}
```

### 20.2 Extensible Custom Fields

Users can add any field to any slide:

```json
{
  "customFields": {
    "brandLogo": { "type": "image", "url": "/assets/logo.svg", "position": "top-right" },
    "footnote": { "type": "text", "content": "Source: Gartner 2026", "position": "bottom-center" },
    "qrCode": { "type": "qr", "url": "https://neuralscale.ai", "position": "bottom-right" },
    "liveMetric": { "type": "data", "source": "api.neuralscale.ai/metrics/users", "refresh": 30 }
  }
}
```

---

### 20.3 Semantic Skill Versioning (Stability Guarantee)

> **From Gemini feedback**: The self-evolving Code Agent is brilliant but dangerous if it
> "evolves" a skill in a way that breaks old decks. Old decks must remain stable.

```
┌────────────────────────────────────────────────────────────────────┐
│  SKILL VERSIONING CONTRACT                                         │
│                                                                    │
│  Every slide in a deck is generated by a specific skill version:   │
│                                                                    │
│  "generationMetadata": {                                           │
│    "skillVersions": {                                              │
│      "title-slide": 4,     ← This deck uses title-slide v4       │
│      "problem-slide": 3,   ← This deck uses problem-slide v3     │
│      "traction-slide": 5   ← This deck uses traction-slide v5    │
│    }                                                               │
│  }                                                                 │
│                                                                    │
│  Rules:                                                            │
│  1. When Code Agent evolves a skill (v4 → v5), old decks         │
│     remain on v4 — they do NOT auto-upgrade                       │
│  2. User sees "Upgrade Available" badge on affected slides         │
│  3. User clicks "Upgrade Slide Design" → regenerates with v5     │
│  4. User can preview v5 side-by-side before committing            │
│  5. Skill versions are immutable once published (append-only)     │
│  6. Rollback: user can manually pin to any previous version       │
│                                                                    │
│  Storage:                                                          │
│  - MongoDB `slide_skills` collection stores all versions          │
│  - Each version includes: prompt_template, quality_history,       │
│    best_examples, common_failures                                  │
│  - Skills are never deleted, only deprecated                      │
└────────────────────────────────────────────────────────────────────┘
```

---

## 21. Re-Generation & Layout Changing

### 21.1 Re-Generation Levels

```
┌────────────────────────────────────────────────────────────────────┐
│                RE-GENERATION SYSTEM                                 │
│                                                                    │
│  Level 1: Per-Slide Regeneration                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  User right-clicks slide → "Regenerate this slide"          │   │
│  │  • Preserves: theme, layout, position in deck               │   │
│  │  • Regenerates: content, images, data visualizations        │   │
│  │  • Context: receives surrounding slides for coherence       │   │
│  │  • User can provide feedback: "make it more data-driven"    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  Level 2: Per-Section Regeneration                                 │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  User: "Regenerate the Problem section"                      │   │
│  │  • Regenerates all slides in a logical section               │   │
│  │  • Preserves: theme, overall deck structure                  │   │
│  │  • Can add/remove slides within the section                  │   │
│  │  • Respects slide count constraints (pitch deck = 10-15)     │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  Level 3: Full Deck Regeneration                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  User: "Regenerate entire presentation"                      │   │
│  │  • Options: keep theme, keep structure, keep nothing         │   │
│  │  • Fresh generation with accumulated feedback                │   │
│  │  • Creates new version (old version preserved in history)    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  Version History:                                                  │
│  v1 → v2 → v3 (each regeneration creates a snapshot)             │
│  User can diff versions and revert to any previous version        │
└────────────────────────────────────────────────────────────────────┘
```

### 21.2 Layout Changing System

```
┌────────────────────────────────────────────────────────────────────┐
│                LAYOUT CHANGING SYSTEM                               │
│                                                                    │
│  Per-Slide Layout Change:                                          │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  Click layout icon → Layout Picker appears:               │     │
│  │                                                           │     │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐     │     │
│  │  │     │ │ █ █ │ │█ █ █│ │ █   │ │     │ │  █  │     │     │
│  │  │  █  │ │     │ │     │ │   █ │ │█████│ │ █ █ │     │     │
│  │  │     │ │     │ │     │ │     │ │     │ │     │     │     │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘     │     │
│  │  Center   2-Col   3-Col   Split  Full-   Triangle      │     │
│  │  Focus                    Screen Bleed   Layout        │     │
│  │                                                           │     │
│  │  Content re-flows automatically into new layout          │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                    │
│  Available Layouts (12):                                           │
│  1. center-focus      — Title/heading centered with subtitle      │
│  2. two-column        — Left/right split (text + visual)          │
│  3. three-column      — Triple column for comparisons             │
│  4. split-screen      — 50/50 image + text                       │
│  5. full-bleed-image  — Full background image with text overlay   │
│  6. top-header        — Large header, content below               │
│  7. sidebar           — Narrow sidebar + main content             │
│  8. grid-4            — 2×2 grid for 4 items                     │
│  9. grid-6            — 2×3 or 3×2 grid for 6 items             │
│  10. timeline         — Horizontal timeline layout                │
│  11. comparison       — Side-by-side comparison                   │
│  12. quote            — Large quote with attribution              │
│                                                                    │
│  Per-Deck Layout Template:                                         │
│  "Apply consistent layout rules across all content slides"        │
│  e.g., "All content slides use two-column layout"                 │
│  (Title and closing slides maintain their specialized layouts)     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 22. Pitch Deck Domain Intelligence

### 22.1 Enforced Structures

| Archetype | Slide Structure | Source |
|-----------|----------------|--------|
| **YC Standard** | Title → Problem → Solution → Why Now → Market → Product → Traction → Business Model → Competition → Team → Ask | Y Combinator |
| **Sequoia Framework** | Company Purpose → Problem → Solution → Why Now → Market Size → Product → Business Model → Team → Financials → Vision | Sequoia Capital |
| **DocSend Optimized** | Front-load key info (2m24s avg), team slide enhanced (1m2s viewed), max 15 slides, 30%+ data slides | DocSend Analytics |

### 22.2 Specialized Slide Types

| Slide Type | Specialized Tools | Data Requirements |
|-----------|-------------------|-------------------|
| TAM/SAM/SOM | Bottom-up calculator (not top-down) | Market data, unit economics |
| Traction | Animated metrics counter, MoM growth graph | Real metrics, dates |
| Competition | 2×2 matrix, feature comparison table | Competitor data |
| Team | Photo grid, credential highlights, advisor grid | Names, titles, photos |
| Financials | 3-year projection, unit economics breakdown | Financial model data |
| Product/Demo | Screenshot gallery, feature highlight cards | Product screenshots |

### 22.3 Anti-Pitfall Rules

| Pitfall | Detection | Correction |
|---------|-----------|------------|
| Too much text | >6 bullets OR >15 words/bullet | Split slide, truncate, summarize |
| No data | 0 charts/tables in deck | Force 30% of slides to have data viz |
| "No competition" | Missing competition slide | Require competitive positioning |
| Top-down TAM | "The market is $X billion" | Force bottom-up: units × price × penetration |
| No "Why Now" | Missing in pitch deck | Add mandatory Why Now slide |
| Weak team slide | No photos, no credentials | Require photos + relevant background |
| Too many slides | >15 slides | Consolidate, suggest merges |
| Animations/transitions | Complex transitions | YC: no transitions (or minimal) |

---

## 23. Export Pipeline

### 23.1 Format Matrix

| Format | Technology | Quality | Editable | Use Case | Size |
|--------|-----------|---------|----------|----------|------|
| **reveal.js HTML** | reveal.js v6.0.0 | High | Source | Presenting, reading | ~500KB |
| **React App** | Vite build | High | Source | Embedding, interactive | ~2MB |
| **Zero-dep HTML** | Inline bundler | Good | Source | Email, sharing | <500KB |
| **PPTX** | PptxGenJS v4.0.1 | High | Full | PowerPoint editing | ~5MB |
| **PDF** | Playwright page.pdf() | Perfect | None | Print, archive | ~3MB |
| **PNG** | Playwright screenshot | High | None | Social media, thumbnails | ~200KB/slide |
| **Markdown** | DSL → Markdown converter | Text | Full | Documentation, wiki | ~50KB |

### 23.2 Export Quality Priority

1. **reveal.js** — Primary delivery format for presentations
2. **PPTX (PptxGenJS)** — Native objects, fully editable; never screenshot-based slides
3. **PDF** — Pixel-perfect from Playwright browser render
4. **HTML** — Self-contained, zero dependencies, works offline
5. **React** — For embedding in web applications
6. **PNG** — For social sharing, thumbnails

### 23.3 PPTX Conversion for React Slides

When React slides need PPTX export:

```
React Component Tree → Extract Content → Map to PptxGenJS Calls

1. Parse React component tree to extract:
   - Text content + styling
   - Image URLs
   - Chart data
   - Layout positions

2. Map to PptxGenJS:
   - <Heading> → slide.addText(text, { fontSize, bold, ... })
   - <Chart data={...}> → slide.addChart(type, data, opts)
   - <Image src={...}> → slide.addImage({ path, x, y, w, h })
   - <ThreeScene> → Playwright screenshot → slide.addImage()

3. Three.js scenes become static images in PPTX (no interactive 3D in PowerPoint)
```

### 23.4 PPTX Template Injection (.potx Support)

> **From Gemini feedback**: Since PPTX is the industry standard for 90% of corporate users,
> make it first-class. Allow users to upload a `.potx` (PowerPoint Template) file and the
> Assembler Agent maps DSL elements to Named Placeholders in the actual PPTX template.

```python
class PptxTemplateInjector:
    """Map DSL content to named placeholders in user-uploaded .potx templates."""

    async def inject(self, dsl: SlideDSL, template_path: str) -> bytes:
        """
        Pipeline:
        1. User uploads company .potx file (their master slides)
        2. Parse .potx to discover named placeholders:
           - "Title", "Subtitle", "Body", "Footer", "Logo", "Chart Area"
        3. Map DSL elements to placeholders by semantic matching:
           - dsl.slide.content.title → placeholder "Title"
           - dsl.slide.content.body → placeholder "Body"
           - dsl.slide.elements[type=chart] → placeholder "Chart Area"
        4. Generate PPTX using template as base (preserves master slide layouts)
        5. Result: native corporate document following company's exact slide masters

        Benefits:
        - Output follows the company's branding guidelines perfectly
        - Slide masters, footers, page numbers inherit from template
        - Users don't need to reformat after AI generation
        """
```

### 23.5 PptxGenJS Known Limitations

> **From GLM5 feedback**: These limitations must be documented so users have correct expectations.

| Feature | PptxGenJS Support | Workaround |
|---------|-------------------|------------|
| Slide Animations | Not supported | N/A (OOXML limitation) |
| Slide Transitions | Not supported | N/A (OOXML limitation) |
| SmartArt | Not supported | Use manual shapes + text |
| Embedded Fonts | Not supported | Use web-safe or system fonts |
| Shape Grouping | Not supported | Position elements individually |
| Hex Color `#` prefix | **CAUSES FILE CORRUPTION** | Always use `"FF0000"`, never `"#FF0000"` |
| HTML-to-PPTX tables | Browser-only (DOM measurement) | Server-side: use row/column API |
| Object mutation | Mutates options objects in-place | Always pass fresh objects via factory functions |

**Fallback**: Maintain `python-pptx` as a server-side alternative for enterprise resilience (single-maintainer risk with PptxGenJS's annual release cadence).

---

## 24. Technology Stack

### 24.1 Full Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **MCP Server** | Python 3.11+, FastMCP | Agent orchestration, tool delivery |
| **Code Agent Runtime** | TypeScript, Node.js 20+ | React compilation, DSL processing |
| **Presentation Renderer** | reveal.js v6.0.0 | Primary HTML presentation engine |
| **React Renderer** | React 18 + Vite + Tailwind v4 | Interactive/3D presentations |
| **3D Engine** | Three.js + @react-three/fiber | 3D scenes within slides |
| **PPTX Generation** | PptxGenJS v4.0.1 | Native PowerPoint generation |
| **PDF Generation** | Playwright | Pixel-perfect PDF from browser |
| **Text Measurement** | PreTeXt (@chenglou/pretext) | DOM-free text fitting |
| **Layout Engine** | Yoga WASM | Server-side flexbox computation |
| **Canvas Editor** | HTML5 Canvas + custom framework | WYSIWYG slide editing |
| **Code Editor** | Monaco Editor (VS Code engine) | HTML/CSS/JS editing |
| **Markdown Editor** | CodeMirror 6 | reveal.js markdown editing |
| **Animations** | Framer Motion + GSAP | React slide animations |
| **Charts** | D3.js + Recharts | Data visualizations |
| **Diagrams** | Mermaid + Excalidraw | Flowcharts, hand-drawn style |
| **Vector Database** | ChromaDB | Presentation embeddings, RAG |
| **Document Database** | MongoDB (motor async) | Presentations, slides, themes |
| **Cache** | Redis | LLM responses, themes, metrics |
| **Browser Automation** | Playwright | Preview, QA, screenshots, PDF |
| **Styling** | UnoCSS (reveal.js) + Tailwind CSS v4 (React) | Utility-first, no CSS reset conflict |

### 24.2 LLM Model Stack

| Model | Provider | Cost | Primary Use |
|-------|----------|------|-------------|
| Kimi-K2-Thinking | Azure | $$$ | Strategy, planning, complex reasoning |
| Phi-4-reasoning-vision-15B | Azure | $$ | Visual QA, layout validation, design scoring |
| DeepSeek-V3.2 | Azure | $$ | Code generation, DSL, Three.js |
| gpt-4o-mini | Azure | $ | Lightweight text, summaries |
| GPT-4o | Azure | $$ | Layout reasoning, multimodal tasks |
| Qwen2.5-coder-32b | Cloudflare | FREE | React/TypeScript code generation |
| glm-4.7-flash | Cloudflare | FREE | Fast text, reveal.js HTML |
| gemma-3-12b-it | Cloudflare | FREE | Lightweight vision (non-critical QA) |
| mistral-medium-2505 | Azure | $$ | Text-only: code quality, structured output |

### 24.3 Image Model Stack

| Model | Provider | Cost | Primary Use |
|-------|----------|------|-------------|
| FLUX.1-Kontext-pro | Azure | $$ | Hero images, key visuals (PRIMARY) |
| phoenix-1.0 | Cloudflare | FREE | General illustrations, icons |
| lucid-origin | Cloudflare | FREE | Artistic backgrounds, textures |

---

## 25. Implementation Phases (Revised: 20 Weeks)

### Phase 1: Foundation (Weeks 1-2)

**Deliverables:**
- FastMCP server (stdio/HTTP+SSE) with 40 core tools
- Slide DSL v2 schema (Zod validation)
- MongoDB + Redis + ChromaDB setup
- Basic CRUD (create/read/update/delete presentations)
- Agent Communication Protocol (Context Board)

**Dependencies:** None

### Phase 2: Agent Core (Weeks 3-5)

**Deliverables:**
- Orchestrator with Context Board
- CEO Agent (Kimi-K2-Thinking / DeepSeek, strategy)
- Researcher Agent (DeepSeek-V3.2, data)
- Layout Agent (GPT-4o, spatial reasoning)
- Agent parallel execution framework

**Dependencies:** Phase 1

### Phase 3: Code Agent + Self-Evolving Loop (Weeks 5-7)

**Deliverables:**
- Code Agent with skills system (yoyo-evolve pattern)
- DSL generation pipeline and Semantic Skill Versioning
- Multi-provider routing (8+ models) with Instant vs Thinking modes
- Self-evaluation loop (generate → evaluate → learn)

**Dependencies:** Phase 2

### Phase 4: reveal.js Renderer & CSS Architecture (Weeks 7-9)

**Deliverables:**
- DSL → reveal.js compiler
- UnoCSS integration (resolving Tailwind v4 conflict for reveal.js)
- Theme → CSS compiler (100+ themes)
- Auto-Animate support and speaker notes

**Dependencies:** Phase 3

### Phase 5: Design Intelligence & Brand DNA (Weeks 9-11)

**Deliverables:**
- Designer Agent (Phi-4-reasoning-vision-15B)
- Theme Engine: 24 built-in themes + Generative Theme Engine
- Brand DNA Extraction pipeline (crawling, logo analysis, rule generation)
- 12 anti-AI-slop presets and Visual Style Discovery UX
- PreTeXt integration with canvas.measureText() fallbacks

**Dependencies:** Phase 4

### Phase 6: React + Three.js Renderer (Weeks 11-13)

**Deliverables:**
- DSL → React component compiler
- 3D/VFX Agent (DeepSeek-V3.2)
- Performance guardrails (lazy-loading of Three.js chunks, 60fps)
- Vite dev server with HMR for hot preview

**Dependencies:** Phase 5

### Phase 7: PPTX & HTML Renderers + Template Injection (Weeks 13-15)

**Deliverables:**
- PptxGenJS integration (native objects)
- PPTX Template Injection (.potx master slide mapping)
- HTML-to-PPTX table conversion
- Zero-dep HTML renderer (inline CSS, minimal JS)
- React → PPTX conversion (Three.js → screenshot fallback transparency UI)

**Dependencies:** Phase 6

### Phase 8: Image Generation Pipeline (Weeks 15-16)

**Deliverables:**
- Flux-first image routing (flux-pro-2 → phoenix → lucid)
- Image resizing/optimizing and asset CDN
- Fallback infrastructure for Cloudflare limits

**Dependencies:** Phase 5

### Phase 9: Unified DSL Editor (Weeks 16-18)

**Deliverables:**
- Single Unified Editor interface replacing 4 isolated editors
- Contextual control panels per renderer view
- HITL (Human-in-the-Loop) Checkpoint gates
- Fast Mode generation toggle

**Dependencies:** Phase 7

### Phase 10: State Synchronization (Weeks 18-19)

**Deliverables:**
- Centralized Zustand/Redux state store 
- Yjs CRDTs for multiplayer editing
- WebSocket broadcasting for real-time agent updates

**Dependencies:** Phase 9

### Phase 11: QA + Polish + Delivery (Weeks 19-20)

**Deliverables:**
- QA Agent with Playwright-based Visual Regression (Golden Master SSIM)
- Accessibility validation (4.5:1 contrast, ARIA DOM)
- Presentation & Reading modes
- Production hardening and load testing

**Dependencies:** Phase 10

---

## 26. Success Metrics

| Metric | Target |
|--------|--------|
| DSL generation success (valid JSON) | >95% |
| Image generation success | >90% (with fallback) |
| Export success rate (all formats) | >99% |
| Quality pass rate (first attempt) | >75% |
| Quality pass rate (after reflective loop) | >90% |
| Per-slide generation time | ≤3s |
| Full 10-slide deck generation | <60s |
| Preview refresh latency | <200ms |
| PreTeXt validation time | <1ms per text |
| reveal.js slide transition | <16ms (60fps) |
| Three.js scene render | ≥30fps on mid-range hardware |
| PPTX file size (10 slides) | <10MB |
| HTML file size (zero-dep) | <500KB |
| Theme compilation time | <100ms |
| Anti-AI-slop compliance | >85% |

---

## 27. Reference Repository Index

| Repository | Stars | What We Use | How We Use It |
|-----------|-------|-------------|---------------|
| [reveal.js](https://github.com/hakimel/reveal.js) | 70.9k | Primary presentation renderer | Renderer 1: HTML presentations with Auto-Animate, speaker notes, fragments |
| [Slidev](https://github.com/slidevjs/slidev) | 45.4k | Theme gallery pattern, PPTX export concept | Theme npm distribution model, Markdown-to-slides concept |
| [Clay](https://github.com/nicbarker/clay) | 16.9k | Layout computation concepts | Flexbox layout model inspiration, transition API patterns |
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides) | 12.5k | Anti-AI-slop style presets | 12 curated STYLE_PRESETS.md presets, visual style discovery UX |
| [Anthropic Frontend Design Skill](https://github.com/openclaw/skills/blob/main/skills/qrucio/anthropic-frontend-design/SKILL.md) | — | Anti-AI-slop design rules | Design guardrails: reject commodity patterns, enforce characterful typography |
| [Spectacle](https://github.com/FormidableLabs/spectacle) | 10.1k | React JSX presentation pattern | React component architecture for slides |
| [PptxGenJS](https://github.com/gitbrent/PptxGenJS) | 4.9k | Native PPTX generation | Renderer 4: charts, shapes, tables, HTML-to-PPTX |
| [open-pencil](https://github.com/open-pencil/open-pencil) | 3.9k | Canvas editor architecture | AI-native design editor: Skia CanvasKit WASM + Yoga WASM + Vue 3 + Tauri v2 + Yjs CRDT |
| [yoyo-evolve](https://github.com/yologdev/yoyo-evolve) | 1.5k | Self-evolving code agent pattern | Code Agent: skills system, self-evaluation, multi-provider (via yoagent framework) |
| [PreTeXt](https://github.com/chenglou/pretext) | ~32k | DOM-free text measurement | Text overflow detection, layout validation (0.09ms/check) |
| [Three.js](https://github.com/mrdoob/three.js) | 112k | 3D rendering engine | 3D slides: globes, charts, particles, animations |
| [@react-three/fiber](https://github.com/pmndrs/react-three-fiber) | 28k | React × Three.js bridge | Embed 3D scenes in React slide components |
| [Motion](https://github.com/motiondivision/motion) | 27k | React animations | Slide entrance animations, micro-interactions (formerly framer/motion) |
| [Monaco Editor](https://github.com/microsoft/monaco-editor) | 42k | Code editor | HTML editor: full IntelliSense, Tailwind autocomplete |
| [CodeMirror](https://github.com/codemirror/dev) | ~4k | Markdown editor | Reveal editor: Markdown editing with live preview |
| [D3.js](https://github.com/d3/d3) | 110k | Data visualization | Charts: TAM/SAM/SOM, financial projections, traction graphs |
| [Mermaid](https://github.com/mermaid-js/mermaid) | 87k | Diagram rendering | Flowcharts, sequence diagrams, mind maps in slides |
| [Excalidraw](https://github.com/excalidraw/excalidraw) | 120k | Hand-drawn diagrams | Whiteboard-style diagrams in slides |

---

## Document Control

**Version**: 7.1 (GLM5/Gemini Feedback Hardened)
**Status**: Architecture Approved. Ready for Phase 1 Implementation.
**Supersedes**: V7.0
**Architecture**: Multi-Renderer Pipeline (4 renderers) + Unified DSL Editor + 8 Agents
**Timeline**: 20 Weeks (11 Phases)
**Total Tools**: 75+
**Total Themes**: 100+ (Brand DNA + 24 built-in + generative)
**Renderers**: 4 (reveal.js [UnoCSS], React+Three.js, Zero-dep HTML, PPTX/PptxGenJS)
**Editor**: 1 Unified DSL Editor (Zero State Drift)
**Image Model**: FLUX.1-Kontext-pro primary
**Thinking Models**: Kimi-K2-Thinking + Phi-4-reasoning-vision-15B + DeepSeek-V3.2
**Quality Gates**: Human-in-the-Loop (HITL), Playwright SSIM Regression, PreTeXt verification
**Research Base**: 16 GitHub repositories analyzed (Verified imports)

---

*"We don't just generate slides; we render success in four formats, each with its own editor, each pushing the boundary of what a presentation can be."*
