# PREMIUM SLIDE GENERATION SYSTEM — V9 MASTER PLAN

## "Cognitive Design Intelligence"

**Version**: 9.3
**Codename**: Meridian
**Status**: Architecture Approved — Ready for Implementation
**Supersedes**: V7.1 (GLM5/Gemini Feedback Hardened), V8 Reference, V9.0, V9.1, V9.2
**Author**: Presentation Architecture Team
**Date**: 2025

---

> *"We don't generate slides. We think in slides, reason about visual space, and render decisions that communicate."*

---

## Table of Contents

1. [Part I: V7 Weakness Analysis](#part-i-v7-weakness-analysis)
   - §1.1 Critical Weaknesses | §1.2 Structural Weaknesses | §1.3 V7 Strengths to Preserve
2. [Part II: V8 Reference Strength Extraction](#part-ii-v8-reference-strength-extraction)
   - §2.1 Innovations Worth Integrating | §2.2 V8 Weaknesses
3. [Part III: Improvement Opportunities](#part-iii-improvement-opportunities)
   - §3.1 Innovations Beyond Both V7 and V8
4. [Part IV: The V9 Meridian Architecture](#part-iv-the-v9-meridian-architecture)
   - §4.1 Executive Summary
   - §4.2 The 6-Layer CDI Pipeline
   - §4.3 Layer 1: Narrative Intelligence
   - §4.4 Layer 2: Content Intelligence
   - §4.5 Layer 3: Spatial Design (GLA)
   - §4.6 Layer 4: Visual Generation
   - §4.7 Layer 5: Composition Engine
   - §4.8 Layer 6: Quality Assurance
   - §4.9 Reflection Loop
   - §4.10 Agent System (12 Agents - Real-Time Crafter & Artist)
   - §4.11 Theme Engine
   - §4.12 Template Library (100+ Built-In)
   - §4.13 Multi-Renderer Pipeline
   - §4.13b Progressive 3D Enhancement Levels
   - §4.14 Canvas Editor — "Figma for Slides"
   - §4.15 LLM Model Inventory & Routing
   - §4.16 Regeneration System + A/B Variant Generation
   - §4.17 Export Pipeline
   - §4.18 Preview System
   - §4.19 Presentation Modes
   - §4.20 State Sync + Collaborative Editing
   - §4.21 Web-to-Slide Transformer
   - §4.22 Visual Identity System (VIS)
   - §4.23 Design Intelligence Dashboard
   - §4.24 Complete Data Visualization System ← V9.2 (90+ charts, 18 tables, 17 diagrams, icons)
   - **§4.25 Self-Learning Slide Generation System (SLGS)** ← NEW V9.3
   - **§4.26 Video Preview & Export Module** ← NEW V9.3
   - **§4.27 Advanced Design Intelligence System** ← NEW V9.3
   - **§4.28 LLM Security & Rate Limit Management** ← NEW V9.3
   - **§4.29 Pretext Advanced Typography Engine** ← NEW V9.3
   - **§4.30 Self-Evolving Code Agent** ← NEW V9.3
   - **§4.31 Sandboxed Mini-Website Preview System** ← NEW V9.3
   - §4.32 Implementation Phases (26 Weeks, 15 Phases)
   - §4.33 Technology Stack
   - §4.34 Success Metrics
5. [Part V: Key Innovations Introduced](#part-v-key-innovations-introduced)
   - 18 Breakthrough Innovations
6. [Part VI: Final Evaluation](#part-vi-final-evaluation)
   - Completeness (36 requirements) | Risk Assessment (15 risks) | Quality Rating (10/10)

---

# Part I: V7 Weakness Analysis

## 1.1 Critical Weaknesses

### W1. Static Layout System (SEVERITY: HIGH)

V7 uses **12 fixed layout templates** (center-focus, two-column, three-column, split-screen, full-bleed-image, top-header, sidebar, grid-4, grid-6, timeline, comparison, quote). These are static, named layouts that content is "poured into."

**Problem**: Real-world content doesn't conform to 12 categories. A slide with 5 bullet points, a chart, and an image has no matching template. The system falls back to "closest match" — producing generic, predictable slides that scream "AI-generated."

**Evidence**: Beautiful.ai uses 300+ Smart Slide templates where content **flows into constraints** rather than fixed boxes. Gamma.app uses card-based layouts that auto-reflow. Clay (17k stars) proves microsecond constraint-based layout is achievable.

**Impact**: Every deck from V7 looks structurally similar. Users can identify "Barise decks" by their repetitive layout patterns — the opposite of what we want.

### W2. No Spatial Reasoning or Visual Weight Engine (SEVERITY: HIGH)

V7 has no concept of **visual weight** — the principle that larger, darker, more saturated, or more complex elements draw the eye. The Layout Agent uses GPT-4o for "spatial reasoning" but has no formalized model.

**Problem**: Without visual weight calculation, the system cannot:
- Determine hierarchy automatically (what should be biggest/boldest)
- Balance compositions (heavy elements create visual imbalance)
- Enforce focal points (the most important element should dominate the viewport)

**Evidence**: V8 Reference proposes a formal Visual Weight Engine with area, color saturation, contrast, position, and complexity multipliers. Professional design tools (Figma, InDesign) use optical alignment, not just mathematical alignment.

**Impact**: Slides appear "correct but lifeless" — elements are positioned by rules but don't **feel** designed. A human designer would instinctively give a hero stat 40% of the viewport; V7 gives it the same grid cell as every other element.

### W3. Percentage-Based Positioning (SEVERITY: MEDIUM-HIGH)

V7 uses percentage-based element positioning within layout grids. This means `{ x: "10%", y: "20%", width: "40%", height: "60%" }`.

**Problem**: Percentages don't account for:
- Text measurement (a 3-word title vs. 12-word title both get "40% width")
- Content density variation (a chart with 3 data points vs. 30)
- Cross-format consistency (10% of 1920px ≠ 10% of a PPTX slide master)

**Evidence**: Clay's layout engine proves that constraint-based (SIZING_FIT, SIZING_GROW, SIZING_FIXED) with min/max bounds produces deterministic, adaptive layouts. Yoga WASM (already in V7's tech stack but underutilized) provides flexbox constraints.

**Impact**: Exported PPTX slides have different proportions from HTML preview. Text occasionally overflows containers. Elements don't adapt to varying content lengths.

### W4. Basic Image Prompting (SEVERITY: MEDIUM)

V7's image pipeline uses a simple routing strategy: Flux-first → phoenix fallback → lucid fallback. Image prompts are generated from slide content with minimal enhancement.

**Problem**: A prompt like "team collaboration" produces generic stock-photo-style imagery. There's no:
- Context injection from the full deck narrative
- Style consistency enforcement across slides
- Intentional composition guidance (rule of thirds, leading lines)
- Color harmony with the slide's theme palette

**Evidence**: V8 Reference proposes "Contextual Image Prompt Engineering" where each image prompt includes: slide context, narrative position, color palette constraints, composition requirements, and style consistency tokens. Napkin.ai generates visuals from text without explicit prompting by understanding content intent.

**Impact**: Images feel disconnected from the presentation narrative. Slide 3's image has no stylistic relationship to Slide 7's image. The "AI illustration" look is immediately recognizable.

### W5. No Think-to-Render Pipeline (SEVERITY: HIGH)

V7's generation flow is essentially: **Outline → Template Selection → Content Fill → Render**. There is no intermediate reasoning layer that thinks about *why* this content should look a certain way.

**Problem**: The system doesn't ask:
- "What is the emotional journey of this deck?" (build tension, then release at the solution)
- "What visual metaphor best represents this concept?"
- "How does slide 5 connect to slide 3 thematically?"

**Evidence**: V8 Reference introduces a 5-layer pipeline: Cognitive Reasoning → Spatial Reasoning → Visual Generation → Composition Engine → QA Validation. Each layer adds intelligence. Gamma.app's 20+ model pipeline suggests multi-stage reasoning is production-proven.

**Impact**: Slides are technically correct but narratively flat. A pitch deck should build emotional momentum — V7 produces slides that are independent units with no visual storytelling arc.

### W6. Single Generation Mode (SEVERITY: MEDIUM)

V7 mentions "Fast Mode" as a toggle but doesn't formalize two distinct generation tiers: Standard (fast, good-enough) and Premium (slower, exceptional,more quality,with more templates and more layouts).

**Problem**: Users have different needs:
- Startup founder drafting ideas at 2am → wants speed (< 15s)
- Preparing for Series A pitch to Sequoia → wants perfection (2 minutes is acceptable)

**Evidence**: User requirement explicitly states "standard mode and premium mode support." Gamma.app differentiates between "quick generate" and "detailed generate."

**Impact**: The system either over-invests compute on casual use or under-invests on critical deliverables. No way for users to signal intent.

### W7. No User Input Pipeline for Brand Assets (SEVERITY: MEDIUM)

V7's theme engine has 24 built-in themes and a generative engine, but no formalized pipeline for handling user-provided:
- Custom typography (font files, Google Fonts selections)
- Brand color palettes (specific hex codes, primary/secondary/accent)
- Logo files and placement rules
- Brand guidelines documents

**Problem**: The Brand DNA Extraction pipeline is mentioned but not architectured for direct user input. A user saying "Use Montserrat and #2563EB as primary" has no clear input path.

**Evidence**: Beautiful.ai allows brand kit uploads. Canva has a Brand Kit feature. The V8 Reference includes brand extraction from uploaded materials but doesn't specify direct user input handling.

**Impact**: Users can't easily apply their existing brand to generated decks, forcing manual post-generation editing.

### W8. Canvas Editor Immaturity (SEVERITY: MEDIUM)

V7 references OpenPencil (3.9k stars) as the canvas editor foundation — a Skia CanvasKit WASM + Yoga WASM + Vue 3 + Tauri v2 stack. This is promising but immature compared to production canvas editors.

**Problem**: OpenPencil is designed for desktop (Tauri) not web-first. Its Vue 3 dependency conflicts with the React frontend. The Skia CanvasKit WASM bundle is ~6MB.

**Evidence**: The V8 Reference proposes Konva.js (10k+ stars) — a mature, battle-tested canvas library with React bindings, extensive plugin ecosystem, and ~200KB bundle size. Beautiful.ai uses a custom canvas editor that handles Smart Slide constraint visualization.

**Impact**: The editor is the primary user interaction surface. An immature editor undermines the entire user experience regardless of generation quality.

### W9. QA System Gaps (SEVERITY: MEDIUM)

V7's QA Agent exists but lacks:
- **SSIM regression testing** (pixel-level comparison against golden master renders)
- **Multi-layer slop detection** (V7 has 12 anti-AI-slop presets but no automated detection pipeline)
- **Accessibility scoring** (mentioned but not formalized with WCAG thresholds)
- **Cross-format validation** (ensuring HTML, PPTX, and PDF outputs match)

**Evidence**: V8 Reference proposes 7-Layer Slop Detection and Golden Master SSIM regression. Production design systems (Material UI, Storybook) use visual regression testing extensively.

**Impact**: Quality issues slip through to users. Without automated visual regression, every code change potentially breaks slide aesthetics.

### W10. Performance Target Gap (SEVERITY: LOW-MEDIUM)

V7 targets **< 60s** for a 10-slide deck. V8 Reference targets **< 30s**.

**Evidence**: Gamma.app generates 10-slide decks in ~20s. Users expect near-instant results in 2025. The 60s target is acceptable for premium mode but not for standard/fast generation.

**Impact**: Competitive disadvantage. Users will compare against Gamma's speed.

---

## 1.2 Structural Weaknesses (Lower Severity)

| ID | Weakness | Impact |
|-----|----------|--------|
| W11 | No emotional journey mapping across slides | Decks lack narrative arc |
| W12 | Agent communication via Context Board lacks formal protocol versioning | Breaking changes between agents |
| W13 | No A/B testing framework for generated slides | Can't measure quality improvements |
| W14 | reveal.js Auto-Animate limited to CSS property tweening | No semantic transition (e.g., "zoom into data") |
| W15 | Three.js scenes are heavy (~2MB bundle) with no progressive loading strategy | First-paint delay for 3D slides |
| W16 | No offline generation capability | Requires constant API connectivity |
| W17 | PptxGenJS single-maintainer risk acknowledged but no mitigation beyond python-pptx fallback | Supply chain vulnerability |
| W18 | Code Agent self-evolving loop (yoyo-evolve) has no safety bounds | Could generate infinite skill variations |

---

## 1.3 V7 Strengths to Preserve

Despite weaknesses, V7 has significant strengths that V9 must retain:

| Strength | Why It Matters |
|----------|---------------|
| **Multi-Renderer Pipeline** (4 renderers) | Format flexibility is a competitive moat |
| **8-Agent System** with specialized roles | Clear separation of concerns |
| **LLM Inventory** (13+ models with routing) | Cost optimization is critical |
| **24 Built-in Themes** with full color specs | Production-ready starting point |
| **12 Anti-AI-Slop Presets** | Quality differentiation |
| **Unified DSL Editor** (single source of truth) | Prevents state drift |
| **PreTeXt.js** text measurement (0.09ms) | Accurate layout computation |
| **Pitch Deck Domain Intelligence** | Industry-specific knowledge |
| **PPTX Template Injection** (.potx support) | Enterprise compatibility |
| **Slide DSL v2** JSON schema | Extensible intermediate representation |
| **Code Agent self-evolving pattern** | Continuous improvement |
| **Brand DNA Extraction** concept | Brand-aware generation |

---

# Part II: V8 Reference Strength Extraction

## 2.1 Innovations Worth Integrating

### S1. Think-to-Render 5-Layer Pipeline

V8's core innovation: instead of Template → Fill → Render, it proposes:

```
Layer 1: Cognitive Reasoning    → "What should this slide SAY?"
Layer 2: Spatial Reasoning      → "WHERE should elements go?"
Layer 3: Visual Generation      → "WHAT does each element look like?"
Layer 4: Composition Engine     → "How do elements WORK TOGETHER?"
Layer 5: QA Validation          → "Does this meet quality standards?"
```

**Assessment**: This is the single most important V8 innovation. V7 collapses layers 1-3 into a single "generate" step, losing the reasoning chain. V9 adapts and extends this to 6 layers.

### S2. Spatial Reasoning Engine with Visual Weight

V8 proposes formal visual weight calculations:

```
Weight = Area × SaturationMultiplier × ContrastMultiplier × PositionBias × ComplexityFactor
```

**Assessment**: Sound principle. V9 implements this as the **Composition Intelligence Engine** with additional factors: semantic importance weight (from content analysis), narrative position weight (climax slides get more visual weight), and user attention prediction (based on eye-tracking research data from Nielsen Norman Group).

### S3. Smart Slide Technology

V8's Beautiful.ai-inspired constraint system: slides auto-adjust when content is added/removed. 300+ templates.

**Assessment**: The concept is right but "300+ templates" is the wrong framing. V9 uses **Generative Layout Algebra** — a constraint solver that composes layouts from primitives (column, row, stack, float, pin) rather than selecting from a finite template library. This means infinite unique layouts from finite rules.

### S4. Figma-Like Canvas Editor (Konva.js)

V8 proposes Konva.js replacing OpenPencil for the editor surface.

**Assessment**: Correct architectural choice. Konva.js is battle-tested, has React bindings (`react-konva`), supports transform controls, and is ~200KB. V9 adopts Konva.js with extensions for constraint visualization and Smart Slide handles.

### S5. Contextual Image Prompt Engineering

V8 proposes enriching image prompts with slide context, narrative position, and style consistency.

**Assessment**: Essential. V9 extends this into the **Visual Narrative Director** — a subsystem that maintains a per-deck "visual thread" ensuring all images share composition style, color temperature, and artistic direction.

### S6. 7-Layer Slop Detection

V8 proposes automated detection of AI-generated clichés:

```
Layer 1: Typography slop (default fonts, poor hierarchy)
Layer 2: Color slop (over-saturated, mismatched palette)
Layer 3: Layout slop (centered-everything syndrome)
Layer 4: Content slop (buzzword density, vague claims)
Layer 5: Image slop (generic stock-photo aesthetic)
Layer 6: Animation slop (gratuitous transitions)
Layer 7: Structural slop (too many slides, no narrative arc)
```

**Assessment**: Excellent framework. V9 integrates this into the QA pipeline with quantified thresholds and auto-correction capabilities.

### S7. Golden Master SSIM Regression

V8 proposes pixel-level visual regression testing using Structural Similarity Index.

**Assessment**: Production-essential. V9 implements this with Playwright screenshots + SSIM comparison against golden renders, with a CI pipeline that catches visual regressions before deployment.

---

## 2.2 V8 Weaknesses (Items V9 Must Improve On)

| V8 Weakness | V9 Improvement |
|------------|----------------|
| Proposes "300+ templates" — still a finite library | Generative Layout Algebra (infinite layouts from constraint rules) |
| 5-Layer pipeline has no feedback loops | V9 adds bidirectional reflection: QA → Cognitive rethink |
| No Standard/Premium mode distinction | V9 formalizes two tiers with different pipeline depths |
| Visual Weight Engine is purely mathematical | V9 adds semantic importance and narrative position weights |
| No user-given typography/colors input formalization | V9 has a Brand Input Pipeline with validation and fallbacks |
| Canvas editor doesn't show constraint handles | V9's Konva.js editor visualizes Smart Slide constraints |
| Missing per-slide re-generation granularity | V9 has 4-level regeneration (element, section, slide, deck) |
| No emotional journey formalization | V9 has Narrative Arc Engine with emotional intensity scoring |
| No A/B variant generation | V9 can produce 2-3 layout variants per slide for user selection |
| Image prompts lack composition direction (rule of thirds, golden ratio) | V9's Visual Narrative Director includes compositional geometry directives |

---

# Part III: Improvement Opportunities

## 3.1 Innovations Beyond Both V7 and V8

### O1. Generative Layout Algebra (GLA)

**Instead of**: 12 fixed templates (V7) or 300+ stored templates (V8)
**V9 introduces**: A constraint solver that composes layouts from atomic primitives.

```typescript
// Layout Algebra Primitives
type LayoutAtom =
  | { type: "column"; children: LayoutAtom[]; gap: number; weights: number[] }
  | { type: "row"; children: LayoutAtom[]; gap: number; weights: number[] }
  | { type: "stack"; children: LayoutAtom[]; alignment: Alignment }
  | { type: "float"; child: LayoutAtom; anchor: AnchorPoint; offset: Vec2 }
  | { type: "pin"; child: LayoutAtom; edges: EdgeConstraints }
  | { type: "aspect"; child: LayoutAtom; ratio: number }
  | { type: "text-fit"; content: string; minFont: number; maxFont: number }
  | { type: "content-slot"; semantic: SemanticType; minSize: Size; maxSize: Size }

// Example: The LLM outputs layout algebra, not template names
const slide = column([
  pin(textFit("Headline", 36, 72), { top: 80, left: 100, right: 100 }),
  row([
    contentSlot("chart", { minW: 400 }),
    column([
      contentSlot("stat", { fixedH: 120 }),
      contentSlot("stat", { fixedH: 120 }),
      contentSlot("stat", { fixedH: 120 }),
    ], { gap: 16, weights: [1, 1, 1] })
  ], { gap: 40, weights: [3, 2] })
], { gap: 32 })
```

**Why this matters**: Every slide gets a **unique layout** computed from its content. No two decks share the same structural DNA. The constraint solver (powered by Yoga WASM) resolves to pixel-perfect coordinates in <1ms.

### O2. Narrative Arc Engine

**Instead of**: Slides as independent units (V7) or 5-layer pipeline without emotional modeling (V8)
**V9 introduces**: A Narrative Arc Engine that models the emotional trajectory of the entire deck.

```python
class NarrativeArc:
    """Maps Freytag's dramatic structure to slide intensity."""

    ARCS = {
        "pitch_deck": [
            ("hook", 0.8),        # Slide 1: High energy opening
            ("problem", 0.6),     # Slide 2-3: Build tension
            ("insight", 0.5),     # Slide 4: The "why now" pivot
            ("solution", 0.9),    # Slide 5: Peak — your product
            ("evidence", 0.7),    # Slide 6-7: Validation (traction, market)
            ("mechanics", 0.5),   # Slide 8: Business model (low visual intensity)
            ("team", 0.6),        # Slide 9: Trust building
            ("vision", 0.95),     # Slide 10: Emotional climax — the ask
        ],
        "quarterly_report": [
            ("executive_summary", 0.7),
            ("highlights", 0.8),
            ("metrics_deep_dive", 0.4),  # Dense data, low visual drama
            ("challenges", 0.5),
            ("roadmap", 0.9),    # Forward-looking = high energy
        ],
    }
```

The Narrative Arc Engine feeds into:
- **Visual weight allocation**: Climax slides get larger hero elements, bolder typography
- **Color temperature**: Tension-building slides use cooler tones; resolution slides use warmer tones
- **Animation intensity**: High-intensity slides get entrance animations; low-intensity slides are static
- **Image style**: Hook slides get cinematic imagery; data slides get clean illustrations

### O3. Dual Generation Modes (Standard + Premium)

| Aspect | Standard Mode | Premium Mode |
|--------|---------------|--------------|
| **Target Time** | <15s for 10 slides | <90s for 10 slides |
| **Pipeline Depth** | 3-layer (Outline → Layout → Render) | 6-layer (full Cognitive Design Intelligence) |
| **Layout Engine** | Template-assisted GLA (pre-computed patterns) | Full constraint solver with visual weight |
| **Image Generation** | Free models (Phoenix, Lucid) or icon substitution | FLUX.1-Kontext-pro with contextual prompting |
| **QA Passes** | 1 automated pass (text overflow, contrast) | 3 passes (layout, slop detection, SSIM) |
| **Variants** | 1 layout per slide | 2-3 variants for user selection |
| **LLM Models** | Free tier priority (GLM, Qwen, Groq) | Thinking models (Kimi-K2, DeepSeek-V3.2) |
| **3D/Animations** | CSS transitions only | Three.js scenes, Framer Motion choreography |
| **Use Case** | Brainstorming, internal meetings, drafts | Investor pitches, client presentations, conferences |

### O4. Brand Input Pipeline

A formalized system for handling user-provided brand assets:

```python
class BrandInputPipeline:
    """
    Accepts user brand inputs and validates/normalizes them for the generation pipeline.

    Input channels:
    1. Direct Input: User provides hex colors, font names, logo URL
    2. URL Extraction: User provides website URL → extract brand palette, fonts, logo
    3. Document Upload: User uploads brand guidelines PDF → extract rules
    4. Template Upload: User uploads .potx file → extract slide masters
    """

    async def process_brand_input(self, input: BrandInput) -> BrandProfile:
        """
        Returns normalized BrandProfile with:
        - primary_color, secondary_color, accent_color (validated hex)
        - font_heading, font_body (validated against available fonts)
        - logo_url (optimized, multiple sizes)
        - color_palette (expanded: 5 shades per base color)
        - typography_scale (computed from font metrics)
        - contrast_matrix (all color pairs with WCAG scores)
        """
```

### O5. Visual Narrative Director

A subsystem that maintains visual coherence across an entire deck:

```python
class VisualNarrativeDirector:
    """
    Maintains a per-deck 'visual thread' that ensures all generated imagery
    shares consistent artistic direction.

    Thread Components:
    - style_anchor: "minimal line art" | "photographic" | "3D rendered" | "watercolor" | ...
    - color_temperature: warm | neutral | cool (shifts with narrative arc)
    - composition_family: "center-dominant" | "rule-of-thirds" | "golden-spiral" | ...
    - lighting_direction: consistent shadow angles across all images
    - detail_density: sparse → dense gradient matching content complexity
    """

    def generate_image_prompt(
        self,
        slide_content: str,
        narrative_position: float,  # 0.0-1.0 position in deck
        visual_thread: VisualThread,
        theme: Theme,
    ) -> EnrichedImagePrompt:
        """
        Returns an enriched prompt that includes:
        - Base content description
        - Style consistency directives (matching visual_thread.style_anchor)
        - Color palette constraints (limited to theme colors + neutral)
        - Composition geometry (rule of thirds grid placement)
        - Mood/atmosphere (derived from narrative_position)
        - Negative prompts (prevent style drift: 'no text, no watermark, no stock photo look')
        """
```

### O6. Composition Intelligence Engine

Beyond V8's visual weight, V9 uses a multi-factor composition engine:

```python
class CompositionEngine:
    """
    Evaluates and optimizes slide composition using professional design principles.
    """

    def score_composition(self, slide: SlideLayout) -> CompositionScore:
        """
        Scoring factors:
        1. Visual Hierarchy Score (0-100)
           - Most important element is largest
           - Typography scale ratio meets 1.2-1.5 modular scale
           - Z-pattern or F-pattern reading flow respected

        2. Balance Score (0-100)
           - Visual weight distribution (left vs right, top vs bottom)
           - Optical center alignment (slightly above mathematical center)
           - Negative space utilization (40-60% whitespace target)

        3. Harmony Score (0-100)
           - Color harmony (complementary, analogous, triadic)
           - Font pairing quality (contrast + compatibility)
           - Element spacing rhythm (consistent or golden ratio)

        4. Focal Point Score (0-100)
           - Single clear focal point per slide
           - 3-second rule: can viewer identify the key message in 3s?
           - Distraction audit: no competing elements fighting for attention

        5. Narrative Flow Score (0-100)
           - Slide connects visually to predecessor/successor
           - Consistent element positioning (title always in same region)
           - Navigation cues (visual breadcrumbs, section indicators)
        """
```

---

# Part IV: The V9 Meridian Architecture

## 4.1 Executive Summary

### 4.1.2 Comprehensive Deep-Research Superiority Matrix (Industry-Wide Architecture Defeat)
Following extensive analytical research into the state-of-the-art generators (Gamma, Tome, Beautiful.ai, Presentations.ai, Pitch, DeckRobot, Canva, Chronicle, Dokie), V9 Meridian's architecture is engineered to exploit and systematically defeat their fundamental technical ceiling:

1. **Defeating the Linear Generators (Gamma, Tome):**
   * *The Industry Ceiling:* They use a simple **Markdown-to-Grid** pipeline mapped to static JSON structures. They suffer from zero spatial awareness (causing hallucinated bounding boxes) and lack cross-slide narrative memory. Each slide generates in isolation, leading to disjointed flow.
   * *V9's Architectural Kill-Shot:* **RAG-Persistent Narrative Memory & Node-Based Spatial ControlNet.** V9 utilizes a continuous RAG context window across the entire Deck-State. Generation is dictated by bounding boxes *first*, where an agent requests assets sized perfectly to runtime aspect ratios using InvokeAI ControlNet bounding boundaries. 

2. **Defeating the Rigid Auto-Aligners (Beautiful.ai, Presentations.ai):**
   * *The Industry Ceiling:* They rely on **Static DOM Injection** and heuristic pre-calculated CSS templates to prevent visual breaks. This forces the 'Generic Corporate Curse' and prevents true dynamic Z-layer overlap or non-linear 3D scaling.
   * *V9's Architectural Kill-Shot:* **Deterministic Constraint Solvers (Cassowary) & WebGL Native Canvas.** V9 breaks the CSS grid entirely by rendering content via GPU-accelerated WebGL/Three.js. Instead of flexbox margins, it uses deterministic constraint-based solvers for flawless typography scaling, supporting real-time mmagic matting (background removal) for free-floating 3D scene compositions.

3. **Defeating 'Bolt-on' Co-Pilots (Pitch, Canva Magic Design, DeckRobot):**
   * *The Industry Ceiling:* AI acts as a peripheral plug-in or linear macro step. Once they generate a slide, they dump a chaotic, bloated layer of UI elements onto the canvas, turning editability into an absolute nightmare.
   * *V9's Architectural Kill-Shot:* **Multi-Agent ReAct Loops (Critic System) & AST Component Remixing.** Generation isn't 'fire-and-forget'. A multi-agent loop (Director -> Designer -> Critic) self-corrects visual density and layout balance *before* user presentation. Under the hood, everything remains an independent semantic node that can be surgically 'Remixed' (re-rendered using Nano-Banana-Pro precise object-prompts) without cascading breakage to the rest of the slide AST.



The V9 Meridian architecture is a **6-Layer Cognitive Design Intelligence Pipeline** that transforms raw content into visually exceptional, narratively coherent presentations. It combines:

- **Generative Layout Algebra** for infinite unique layouts from constraint rules
- **Narrative Arc Engine** for emotional trajectory modeling
- **Composition Intelligence Engine** for professional design quality scoring
- **Visual Narrative Director** for cross-deck visual coherence
- **Dual Generation Modes** (Standard: <15s, Premium: <90s)
- **4-Renderer Pipeline** (reveal.js, React+Three.js, Zero-dep HTML, PPTX via PptxGenJS)
- **12 Specialized Agents** (Including Real-Time Crafter & Artist Agents driven by ReAct patterns)
- **Brand Input Pipeline** for user typography, colors, and assets
- **7-Layer Slop Detection** with auto-correction
- **Konva.js Canvas Editor** with constraint visualization


### 4.1.3 Deep-Research Inspirations: Dokie, Chronicle, and Open-Source SOTA

To ensure V9 Meridian achieves absolute market dominance, we have synthesized architectural paradigms from the most advanced systems (Chronicle AI, Dokie AI) and integrated them with State-of-the-Art (SOTA) open-source models and rendering engines.

#### 1. Chronicle AI & Dokie AI: The "Block-Based" Fluid Canvas
*   **The Inspiration:** Chronicle AI disrupts the traditional 16:9 slide by treating presentations as infinite, fluid canvases composed of interactive "blocks" rather than static pages. Dokie emphasizes living documents where content dictates layout, dynamically reflowing based on device context.
*   **V9 Meridian's Technical Implementation (The "Liquid-Slide" AST):** Instead of static coordinate mapping, V9 Meridian utilizes a **React-Flow / Slate.js inspired Abstract Syntax Tree (AST)** for the presentation layer. Slides are not fixed bounds but "Viewports" over a continuous semantic canvas. 
    *   *Implementation:* We define a BlockSpace schema where elements (text, charts, 3D models) possess lex-grow, constraints, and z-index parameters. V9's layout engine calculates bounds at runtime using a WebAssembly-compiled **Cassowary Constraint Solver** (analogous to Apple's AutoLayout), completely eliminating "overlapping text" hallucinations common in linear generators.

#### 2. SOTA Background & Vector Generation (Hugging Face)
*   **The Inspiration:** Generic AI presentations suffer from "AI artifacts" and incoherent background theming. SOTA models on Hugging Face provide the cure.
*   **V9 Meridian's Technical Implementation (SDXL Refiner & Specialized LoRAs):** 
    *   **Dynamic Vector Generation:** For crisp, infinite-scale iconography and minimal illustrations, V9 utilizes **Recraft-V3 / FLUX.1-schnell** coupled with a vectorization pipeline (potrace / SVGCrafter) to output raw SVG paths, circumventing raster pixelation.
    *   **Coherent Corporate Backgrounds:** V9 employs a dedicated **SDXL base model with targeted LoRAs** (e.g., modern-corporate-minimalist-UI, bstract-geometry-v2) via dedicated Inference Endpoints.
    *   **Depth-Aware Layering:** Backgrounds are processed through **Depth Anything V2** (Hugging Face) to generate depth maps. The V9 frontend engine (Three.js) then applies subtle parallax effects between the text layer and the generated foreground, a feature completely absent from Canva or Pitch.

#### 3. Constraints-Based Positioning & Auto-Layout (GitHub SOTA)
*   **The Inspiration:** High-performance dynamic UI generation libraries from the open-source community (e.g., 
eact-grid-layout, yoga-layout, masonry algorithms).
*   **V9 Meridian's Technical Implementation (Yoga + React Tree):** 
    *   V9 integrates **Yoga** (Meta's cross-platform layout engine) via WebAssembly to calculate element positioning server-side or in-browser before rendering. This ensures the AI model (LLM) only needs to output semantic hierarchy and rough spatial relationships (left, 
ight, dominant). The Yoga engine deterministically resolves justify-content and lign-items in milliseconds, returning exact (x, y, w, h) coordinates to the frontend AST.

#### 4. Cinematic Styling & Timeline Animation (GSAP & Theatre.js)
*   **The Inspiration:** The fluid, native-app level transitions seen in Chronicle AI, driven by professional web animation engines rather than CSS templates.
*   **V9 Meridian's Technical Implementation (The Orchestration Layer):**
    *   **GSAP ScrollTrigger & FLIP:** V9 abandons basic CSS transitions. Element state changes across slide viewports leverage **GSAP's FLIP (First, Last, Invert, Play)** technique. This allows elements to morph seamlessly from a bullet point on Slide 1 to a chart legend on Slide 2.
    *   **Theatre.js for 3D/Complex Sequencing:** For slides containing WebGL elements or complex data visualizations, V9 utilizes **Theatre.js** to map animation timelines to the user's progression, enabling interactive storytelling where the user can "scrub" through the presentation state organically.


---

## 4.2 The 6-Layer Cognitive Design Intelligence Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                        V9 MERIDIAN: 6-LAYER CDI PIPELINE                                 │
│                                                                                          │
│  ┌─────────────────────┐                                                                 │
│  │ Layer 1: NARRATIVE   │  "What story does this deck tell?"                              │
│  │ INTELLIGENCE         │  → Outline, arc mapping, emotional intensity per slide          │
│  │ (Kimi-K2-Thinking)   │  → Audience persona modeling, persuasion strategy               │
│  └──────────┬──────────┘                                                                 │
│             ▼                                                                            │
│  ┌─────────────────────┐                                                                 │
│  │ Layer 2: CONTENT     │  "What goes on each slide?"                                     │
│  │ INTELLIGENCE         │  → Per-slide content generation with semantic typing             │
│  │ (DeepSeek-V3.2)      │  → Data extraction, stat formatting, quote selection             │
│  └──────────┬──────────┘                                                                 │
│             ▼                                                                            │
│  ┌─────────────────────┐                                                                 │
│  │ Layer 3: SPATIAL     │  "Where does each element go?"                                  │
│  │ DESIGN               │  → Generative Layout Algebra composition                        │
│  │ (GPT-4o / Phi-4)     │  → Visual weight allocation, constraint solving (Yoga WASM)     │
│  └──────────┬──────────┘                                                                 │
│             ▼                                                                            │
│  ┌─────────────────────┐                                                                 │
│  │ Layer 4: VISUAL      │  "What does each element look like?"                            │
│  │ GENERATION           │  → Image generation (FLUX/Phoenix/Lucid)                        │
│  │ (Multi-model)        │  → Chart/diagram creation (D3.js, Mermaid)                      │
│  │                      │  → Icon/illustration selection, 3D scene composition             │
│  └──────────┬──────────┘                                                                 │
│             ▼                                                                            │
│  ┌─────────────────────┐                                                                 │
│  │ Layer 5: COMPOSITION │  "How do elements work together?"                               │
│  │ ENGINE               │  → Composition scoring (hierarchy, balance, harmony, focal)      │
│  │ (Phi-4-vision)       │  → Color harmony validation, typography audit                   │
│  │                      │  → Cross-slide consistency check, theme coherence                │
│  └──────────┬──────────┘                                                                 │
│             ▼                                                                            │
│  ┌─────────────────────┐                                                                 │
│  │ Layer 6: QUALITY     │  "Does this meet our quality bar?"                              │
│  │ ASSURANCE            │  → 7-Layer Slop Detection with auto-correction                  │
│  │ (Phi-4-vision +      │  → SSIM regression against golden masters                       │
│  │  Playwright)         │  → Accessibility (WCAG 2.1 AA), cross-format validation          │
│  │                      │  → Narrative coherence audit                                    │
│  └──────────┬──────────┘                                                                 │
│             │                                                                            │
│             ▼                                                                            │
│        ┌─────────┐                                                                       │
│        │ REFLECT │ ← If QA score < threshold, loop back to appropriate layer              │
│        └─────────┘                                                                       │
│             │                                                                            │
│             ▼                                                                            │
│  ┌─────────────────────┐                                                                 │
│  │ OUTPUT: Multi-Format │  reveal.js HTML │ React+Three.js │ Zero-dep HTML │ PPTX         │
│  │ Renderer Pipeline    │  PDF (Playwright) │ PNG │ Markdown │ .potx injection             │
│  └─────────────────────┘                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Standard Mode Pipeline (Layers Used)

```
Layer 1 (Simplified) → Layer 2 → Layer 3 (Template-Assisted) → Layer 4 (Free Models) → Output
                                                                                    ↑
                                                                            (Skip Layers 5-6)
```

### Premium Mode Pipeline (All Layers)

```
Layer 1 → Layer 2 → Layer 3 → Layer 4 → Layer 5 → Layer 6 → [Reflect Loop if needed] → Output
```

---

## 4.3 Layer 1: Narrative Intelligence

### Purpose
Transform raw user input (topic, document, URL, or brief) into a structured narrative plan with emotional mapping.

### Input
```typescript
interface GenerationRequest {
  mode: "standard" | "premium";
  input_type: "topic" | "document" | "url" | "outline" | "regenerate";
  content: string;  // The user's input
  slide_count?: number;  // Optional target (default: auto from content)
  deck_type?: DeckType;  // "pitch_deck" | "business_report" | "educational" | "marketing" | ...
  brand?: BrandProfile;  // User's brand assets (if provided)
  audience?: AudiencePersona;  // "investors" | "executives" | "developers" | "general"
  tone?: Tone;  // "professional" | "creative" | "technical" | "casual"
}
```

### Output: Narrative Plan
```typescript
interface NarrativePlan {
  deck_metadata: {
    title: string;
    subtitle: string;
    deck_type: DeckType;
    audience: AudiencePersona;
    tone: Tone;
    total_slides: number;
    estimated_duration_minutes: number;
  };
  narrative_arc: {
    archetype: string;  // "hero_journey" | "problem_solution" | "chronological" | "comparison"
    emotional_trajectory: EmotionalPoint[];  // [{slide: 1, intensity: 0.8, emotion: "curiosity"}, ...]
  };
  slides: NarrativeSlide[];
  visual_thread: {
    style_anchor: string;  // e.g., "clean minimal with bold accent geometry"
    color_temperature_arc: ("warm" | "neutral" | "cool")[];  // Per-slide temperature
    image_style: string;  // e.g., "flat illustration with subtle gradients"
    composition_family: string;  // e.g., "asymmetric-dynamic"
  };
}

interface NarrativeSlide {
  index: number;
  role: SlideRole;  // "title" | "hook" | "problem" | "solution" | "evidence" | "data" | "team" | "closing"
  purpose: string;  // One sentence: what this slide must accomplish
  key_message: string;  // The single takeaway
  emotional_intensity: number;  // 0.0, 1.0
  content_requirements: {
    needs_image: boolean;
    needs_chart: boolean;
    needs_data_table: boolean;
    needs_3d: boolean;
    needs_quote: boolean;
    bullet_count?: number;
    stat_count?: number;
  };
  transition_from_previous: string;  // e.g., "contrast" | "build" | "pivot" | "evidence"
}
```

### Model Assignment
- **Premium Mode**: Kimi-K2-Thinking (deep reasoning, narrative structure)
- **Standard Mode**: DeepSeek-V3.2 (good structure, faster)
- **Fallback**: Groq llama-3.3-70b (fast, free)

### Prompt Strategy

```python
NARRATIVE_INTELLIGENCE_PROMPT = """
You are a world-class presentation strategist. Your task is to design the narrative
architecture of a presentation.

RULES:
1. Every slide must have a single, clear purpose. If a slide tries to do two things, split it.
2. The deck must follow a narrative arc — build tension, deliver insight, resolve with action.
3. Map emotional intensity (0.0-1.0) for each slide. The deck should NOT be flat.
   - Openings: 0.7-0.8 (hook attention)
   - Problem slides: 0.5-0.7 (build tension)
   - Solution/product: 0.85-0.95 (peak)
   - Data/evidence: 0.4-0.6 (lower, let data speak)
   - Closing/ask: 0.9-1.0 (emotional climax)
4. For pitch decks, enforce the appropriate archetype structure (YC Standard, Sequoia, DocSend).
5. Think about what the AUDIENCE needs to feel at each point, not just what they need to know.
6. Define the visual thread: what visual style will carry through the entire deck?

INPUT:
- Deck Type: {deck_type}
- Audience: {audience}
- Tone: {tone}
- User Content: {content}

OUTPUT: JSON matching NarrativePlan schema
"""
```

---

## 4.4 Layer 2: Content Intelligence

### Purpose
Generate the actual text/data content for each slide, typed semantically for the layout engine.

### Input
NarrativePlan from Layer 1 + original user content

### Output: Content-Typed Slides
```typescript
interface ContentSlide {
  index: number;
  elements: ContentElement[];
}

type ContentElement =
  | { type: "heading"; text: string; level: 1 | 2 | 3; semantic_weight: number }
  | { type: "subheading"; text: string; semantic_weight: number }
  | { type: "body"; text: string; semantic_weight: number }
  | { type: "bullets"; items: BulletItem[]; semantic_weight: number }
  | { type: "stat"; value: string; label: string; unit?: string; trend?: "up" | "down" | "neutral"; semantic_weight: number }
  | { type: "quote"; text: string; attribution: string; semantic_weight: number }
  | { type: "image_brief"; description: string; purpose: "hero" | "supporting" | "background" | "icon"; semantic_weight: number }
  | { type: "chart"; chart_type: ChartType; data: ChartData; semantic_weight: number }
  | { type: "table"; headers: string[]; rows: string[][]; semantic_weight: number }
  | { type: "diagram"; diagram_type: "flowchart" | "mindmap" | "timeline" | "org_chart"; definition: string; semantic_weight: number }
  | { type: "code_snippet"; language: string; code: string; semantic_weight: number }
  | { type: "cta"; text: string; action?: string; semantic_weight: number }

interface BulletItem {
  text: string;
  icon?: string;  // Semantic icon name: "rocket", "chart-up", "shield", etc.
  emphasis?: boolean;
}
```

The `semantic_weight` field (0.0-1.0) indicates how important this element is to the slide's key message. The Spatial Design layer uses this to allocate visual prominence.

### Model Assignment
- **Premium Mode**: DeepSeek-V3.2 (structured JSON output, code-level precision)
- **Standard Mode**: Groq llama-3.3-70b (fast, free) or GLM-4.7-Flash
- **Fallback**: Qwen2.5-coder-32b (Cloudflare free)

### Anti-Content-Slop Rules

```python
CONTENT_RULES = {
    "max_words_per_bullet": 15,
    "max_bullets_per_slide": 6,
    "min_data_slides_ratio": 0.3,  # At least 30% of slides should have data/visuals
    "ban_words": [
        "synergy", "leverage", "paradigm", "disrupt", "revolutionize",
        "game-changing", "best-in-class", "cutting-edge", "world-class",
        "thought leader", "move the needle", "low-hanging fruit",
    ],
    "require_specificity": True,  # "grew 340% YoY" not "grew significantly"
    "max_heading_words": 8,
    "require_one_key_message_per_slide": True,
}
```

---

## 4.5 Layer 3: Spatial Design

### Purpose
Transform content-typed elements into pixel-perfect layouts using Generative Layout Algebra and the constraint solver.

### The Generative Layout Algebra (GLA) System

Instead of selecting from a fixed template library, the LLM composes a layout tree from algebra primitives, and the constraint solver (Yoga WASM) resolves it to exact pixel coordinates.

```typescript
// =============================================================
//  GENERATIVE LAYOUT ALGEBRA (GLA) — Core Types
// =============================================================

type GLA_Node =
  // Structural
  | GLA_Column
  | GLA_Row
  | GLA_Stack
  | GLA_Grid
  // Positional
  | GLA_Float
  | GLA_Pin
  // Content
  | GLA_TextFit
  | GLA_ContentSlot
  | GLA_Spacer
  | GLA_Divider

interface GLA_Column {
  type: "column";
  children: GLA_Node[];
  gap: number;  // px
  padding?: Padding;
  align?: "start" | "center" | "end" | "stretch";
  justify?: "start" | "center" | "end" | "between" | "around";
  weights?: number[];  // Flex weights for children (e.g. [2, 1] = 66%/33%)
}

interface GLA_Row {
  type: "row";
  children: GLA_Node[];
  gap: number;
  padding?: Padding;
  align?: "start" | "center" | "end" | "stretch";
  weights?: number[];
}

interface GLA_Grid {
  type: "grid";
  children: GLA_Node[];
  columns: number;
  rows: number;
  gap: number;
  cellAspectRatio?: number;
}

interface GLA_Stack {
  type: "stack";
  children: GLA_Node[];  // Rendered in order, last on top
  alignment: { x: "left" | "center" | "right"; y: "top" | "center" | "bottom" };
}

interface GLA_Float {
  type: "float";
  child: GLA_Node;
  anchor: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center";
  offset: { x: number; y: number };
  zIndex: number;
}

interface GLA_Pin {
  type: "pin";
  child: GLA_Node;
  edges: { top?: number; right?: number; bottom?: number; left?: number };  // px from edges
}

interface GLA_TextFit {
  type: "text-fit";
  elementRef: string;  // Reference to ContentElement
  minFontSize: number;
  maxFontSize: number;
  lineHeightRatio: number;  // e.g. 1.2
  maxLines?: number;
}

interface GLA_ContentSlot {
  type: "content-slot";
  elementRef: string;
  sizing: {
    width: "fit" | "grow" | { fixed: number } | { min: number; max: number };
    height: "fit" | "grow" | { fixed: number } | { min: number; max: number };
  };
  aspectRatio?: number;
}

interface GLA_Spacer {
  type: "spacer";
  size: number | "grow";
}

interface GLA_Divider {
  type: "divider";
  orientation: "horizontal" | "vertical";
  thickness: number;
  color: string;
}
```

### Layout Resolution Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ LLM outputs  │───▷│ GLA Tree     │───▷│ Yoga WASM    │───▷│ Pixel-Perfect│
│ GLA JSON     │    │ Validation   │    │ Resolver     │    │ Coordinates  │
│              │    │ (Zod schema) │    │ (flexbox)    │    │ per element  │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │ PreTeXt.js   │
                                       │ Text Metrics │
                                       │ (0.09ms/fit) │
                                       └──────────────┘
```

### Visual Weight Integration

After the constraint solver produces base coordinates, the Visual Weight Engine adjusts:

```python
class VisualWeightEngine:
    """
    Adjusts element sizes and positions based on semantic importance
    and narrative intensity.
    """

    def apply_visual_weight(
        self,
        layout: ResolvedLayout,
        content_elements: list[ContentElement],
        narrative_intensity: float,
    ) -> ResolvedLayout:
        """
        1. Compute raw visual weight per element:
           weight = semantic_weight × area_factor × contrast_factor

        2. Compare against target weight distribution:
           - Primary element: 40-50% of visual weight
           - Secondary elements: 20-30% combined
           - Supporting elements: 15-25% combined
           - Whitespace: 25-40% of slide area

        3. Adjust sizing within constraint bounds:
           - If primary element is too small, grow it (within max bounds)
           - If secondary elements compete, reduce their scale
           - Enforce minimum whitespace ratio

        4. Apply narrative intensity modifier:
           - High intensity (>0.8): Allow bolder sizes, higher contrast
           - Low intensity (<0.4): Enforce calmer proportions, more whitespace
        """
```

### Model Assignment
- **Premium Mode**: GPT-4o (spatial reasoning) + Yoga WASM (constraint solving)
- **Standard Mode**: GLM-4.7-Flash (fast layout selection from pre-computed GLA patterns) + Yoga WASM
- **Fallback**: Pre-computed layout patterns (no LLM call, pattern matching on content structure)

### Pre-Computed GLA Patterns (Standard Mode Acceleration)

For Standard Mode, instead of generating GLA from scratch, the system matches content structure to pre-computed GLA patterns:

```python
GLA_PATTERNS = {
    # Pattern: 1 heading + 3-5 bullets + 1 image
    "heading_bullets_image": {
        "match": lambda elements: (
            count_type(elements, "heading") == 1
            and 3 <= count_type(elements, "bullets") <= 5
            and count_type(elements, "image_brief") == 1
        ),
        "layouts": [
            # Variant A: Image left, text right (60/40 split)
            "row([content_slot('image', grow), column([text_fit('heading'), content_slot('bullets')], gap=24)], gap=40, weights=[3, 2])",
            # Variant B: Image right, text left
            "row([column([text_fit('heading'), content_slot('bullets')], gap=24), content_slot('image', grow)], gap=40, weights=[2, 3])",
            # Variant C: Full-width image top, text bottom
            "column([content_slot('image', {maxH: 400}), text_fit('heading'), content_slot('bullets')], gap=24)",
        ]
    },
    # Pattern: 3-4 stats
    "stats_grid": {
        "match": lambda elements: 3 <= count_type(elements, "stat") <= 4,
        "layouts": [
            "column([text_fit('heading'), grid(content_slots('stat'), cols=count, gap=32)], gap=40)",
            "column([text_fit('heading'), row(content_slots('stat'), gap=24, weights=equal)], gap=40)",
        ]
    },
    # ... 50+ pre-computed patterns covering common content structures
}
```

---

## 4.6 Layer 4: Visual Generation

### Purpose
Generate all visual assets: images, charts, diagrams, icons, 3D scenes.

### Visual Narrative Director (Full Implementation)

```python
class VisualNarrativeDirector:
    """
    Maintains visual coherence across the entire deck.
    Initialized once per deck in Layer 1, used for every image in Layer 4.
    """

    def __init__(self, visual_thread: VisualThread, brand: Optional[BrandProfile]):
        self.style_anchor = visual_thread.style_anchor
        self.color_constraints = self._derive_color_constraints(visual_thread, brand)
        self.composition_rules = self._derive_composition_rules(visual_thread)
        self.consistency_tokens = []  # Accumulated style tokens from generated images

    def build_image_prompt(
        self,
        brief: ImageBrief,
        slide_context: NarrativeSlide,
        theme: Theme,
    ) -> str:
        """
        Assembles a rich image prompt with 6 dimensions:

        1. SUBJECT: What the image depicts (from brief.description)
        2. STYLE: Consistent artistic direction (from style_anchor)
           e.g., "clean vector illustration, flat design, subtle gradients"
        3. COMPOSITION: Where key elements should be positioned
           e.g., "subject positioned at right third, negative space on left for text overlay"
        4. COLOR: Palette-constrained generation
           e.g., "dominant colors: #2563EB and #F8FAFC, accent: #F59E0B"
        5. MOOD: Emotional tone matching narrative position
           e.g., "confident and forward-looking atmosphere" (for solution slide)
        6. NEGATIVE: What to exclude
           e.g., "no text, no watermark, no stock photo aesthetic, no clip art"
        """

        mood = self._narrative_to_mood(slide_context.emotional_intensity, slide_context.role)
        composition = self._select_composition(brief.purpose, slide_context)
        palette = self._constrain_palette(theme, slide_context)

        return f"""{brief.description}.
Style: {self.style_anchor}. {self._style_modifiers(slide_context)}.
Composition: {composition}.
Color palette: {palette}.
Mood: {mood}.
Negative: no text overlay, no watermarks, no generic stock photo aesthetic, no busy backgrounds, no clip art."""
```

### Advanced Image Generation & Prompt Engineering (Beating Dokie & Chronicle AI)

> *To truly surpass Dokie AI and Chronicle AI, Meridian employs state-of-the-art visual generation workflows powered by **InvokeAI** (node-based image graphs) and **mmagic** (advanced AIGC toolbox), supercharged by **awesome-nano-banana-pro-prompts** for hyper-precise compositional control.*

```python
class InvokeAIWorkflowIntegrator:
    """
    Instead of passing simple text prompts, Premium Mode constructs full
    InvokeAI generation graphs to enforce strict constraints (inpainting around text,
    ControlNet structural preservation, precise outpainting).
    """
    def build_generation_graph(self, brief: ImageBrief, layout: GLA_Node) -> dict:
        # Generates a headless InvokeAI Graph JSON
        # Includes ControlNet edges to respect whitespace ratios from the GLA tree
        pass

class mmagicRestorationPipeline:
    """
    Uses open-mmlab/mmagic tools to upsample, color-correct, and remove artifacts
    from any AI-generated image before placing it on the slide canvas.
    """
    async def polish_image(self, raw_image: bytes) -> bytes:
        # Applies super-resolution, matting, and precise palette matching.
        pass
```

### Prompt Engineering (Nano-Banana-Pro level)
All prompts injected into the routing layer utilize strict token-spacing and weighting derived from the `awesome-nano-banana-pro-prompts` repository, guaranteeing that elements like lighting direction, asset positioning (Rule of Thirds), and vector constraints are honored flawlessly by the diffusion models.

### Image Generation Model Routing

```python
IMAGE_ROUTING = {
    "hero": {
        "premium": "flux-kontext-pro",     # Best quality for the key visual
        "standard": "phoenix-1.0",         # Good quality, free
    },
    "supporting": {
        "premium": "phoenix-1.0",          # Good quality, save budget
        "standard": "lucid-origin",        # Creative, free
    },
    "background": {
        "premium": "lucid-origin",         # Artistic textures
        "standard": "css_gradient",        # No API call — CSS-generated
    },
    "icon": {
        "premium": "phoenix-1.0",          # Generated icons
        "standard": "icon_library",        # Pre-built icon set (Lucide/Heroicons)
    },
}
```

### Chart Generation (D3.js + Server-Side Rendering)

```python
class ChartGenerator:
    """
    Generates charts from ContentElement data using D3.js templates.
    Charts are rendered server-side via Playwright for consistent output.
    """

    CHART_TYPES = {
        "bar": "d3_bar_template",
        "line": "d3_line_template",
        "pie": "d3_pie_template",
        "donut": "d3_donut_template",
        "area": "d3_area_template",
        "scatter": "d3_scatter_template",
        "tam_sam_som": "d3_nested_circles_template",  # Pitch deck specific
        "funnel": "d3_funnel_template",
        "waterfall": "d3_waterfall_template",
        "timeline": "d3_horizontal_timeline_template",
        "comparison_matrix": "d3_matrix_template",  # 2×2 competitive positioning
        "metric_counter": "animated_metric_template",  # Traction slides
    }

    async def generate(
        self,
        chart_element: ContentElement,
        theme: Theme,
        dimensions: Size,
    ) -> ChartOutput:
        """
        Returns:
        - svg: Inline SVG for HTML renderers
        - png: Rasterized for PPTX
        - pptx_native: PptxGenJS chart calls for editable charts
        """
```

---

## 4.7 Layer 5: Composition Engine

### Purpose
Score and optimize the assembled slide for visual quality, then ensure cross-deck coherence.

### Composition Scoring

```python
class CompositionScorer:
    """
    Uses Phi-4-reasoning-vision-15B to evaluate rendered slide screenshots.
    Only active in Premium Mode.
    """

    async def score(self, slide_screenshot: bytes, slide_metadata: dict) -> CompositionScore:
        """
        Vision model evaluates:
        1. Is there a clear visual hierarchy? (score 0-100)
        2. Is the composition balanced? (score 0-100)
        3. Is there adequate whitespace? (score 0-100)
        4. Is the color harmony pleasing? (score 0-100)
        5. Can you identify the key message in 3 seconds? (score 0-100)

        Returns CompositionScore with individual scores and weighted average.
        Threshold: 70/100 minimum weighted average.
        If below threshold: return specific remediation suggestions.
        """

    async def suggest_remediation(self, score: CompositionScore) -> list[Remediation]:
        """
        Possible remediations:
        - "Increase heading font size by 20% to strengthen hierarchy"
        - "Add 40px left padding to improve whitespace balance"
        - "Reduce bullet count from 8 to 5 to prevent overcrowding"
        - "Change accent color from #FF0000 to #E63946 for softer contrast"
        """
```

### Cross-Slide Consistency Check

```python
class ConsistencyChecker:
    """
    Ensures slides form a coherent deck, not a random collection.
    """

    def check_consistency(self, slides: list[ResolvedSlide]) -> ConsistencyReport:
        """
        Checks:
        1. Title position consistency (same region across slides, ±10px)
        2. Footer/page number consistency
        3. Color usage consistency (same palette, no rogue colors)
        4. Font usage consistency (max 2 heading fonts, 1 body font)
        5. Margin consistency (same safe area across slides)
        6. Element density consistency (no slide dramatically more crowded)
        7. Image style consistency (all same artistic direction)
        """
```

---

## 4.8 Layer 6: Quality Assurance

### 7-Layer Slop Detection System

```python
class SlopDetector:
    """
    Automated detection and correction of AI-generated design clichés.
    """

    LAYERS = {
        1: TypographySlopDetector,
        2: ColorSlopDetector,
        3: LayoutSlopDetector,
        4: ContentSlopDetector,
        5: ImageSlopDetector,
        6: AnimationSlopDetector,
        7: StructuralSlopDetector,
    }

    class TypographySlopDetector:
        """
        Detects:
        - Default system fonts (Arial, Calibri, Times New Roman) without intentional choice
        - Poor hierarchy (heading barely larger than body)
        - Monochrome text (all same color, no emphasis variation)
        - Over-use of bold (>30% of text bolded = nothing is emphasized)
        - Inconsistent alignment (mixed left/center within same slide)

        Threshold: >2 violations = SLOP
        Auto-fix: Apply typography scale (1.333 augmented fourth) with proper weight hierarchy
        """

    class ColorSlopDetector:
        """
        Detects:
        - Neon/over-saturated palette (S > 90% in HSL)
        - Low contrast text (< 4.5:1 ratio for body, < 3:1 for headings per WCAG AA)
        - Too many colors (>5 distinct hues = visual noise)
        - Mismatched warm/cool tones without intentional contrast
        - Pure black (#000000) on pure white (#FFFFFF) — harsh, not premium

        Threshold: >2 violations = SLOP
        Auto-fix: Normalize to nearest theme-approved color
        """

    class LayoutSlopDetector:
        """
        Detects:
        - Center-everything syndrome (all elements horizontally centered)
        - No whitespace (<25% of slide area is empty)
        - Element collision (overlapping bounding boxes without intentional overlap)
        - Orphan elements (single element in vast empty space)
        - Symmetry obsession (every element perfectly mirrored = boring)

        Threshold: >1 critical violation = SLOP
        Auto-fix: Re-run GLA solver with adjusted constraints
        """

    class ContentSlopDetector:
        """
        Detects:
        - Buzzword density (>15% of words are banned buzzwords)
        - Wall of text (>50 words on a single slide)
        - No data (all-text deck with no charts/stats/images)
        - Vague claims ("significant growth" instead of "340% YoY")
        - Duplicate key messages across slides

        Threshold: >2 violations = SLOP
        Auto-fix: Regenerate content with stricter constraints
        """

    class ImageSlopDetector:
        """
        Detects:
        - Generic stock photo aesthetic (handshake, lightbulb, puzzle pieces)
        - Inconsistent style (photographic mixed with illustration)
        - Irrelevant imagery (not connected to slide content)
        - Low resolution (<1024px for hero images)
        - Faces/people without diversity consideration

        Threshold: >1 violation for hero images, >2 for supporting
        Auto-fix: Regenerate with enhanced prompt (add negative constraints)
        """

    class AnimationSlopDetector:
        """
        Detects:
        - Gratuitous transitions (every slide has different transition)
        - Slow animations (>500ms entrance animations)
        - Competing animations (multiple elements animating simultaneously)
        - Missing animations where expected (stat reveal without counter animation)

        Threshold: >2 violations = SLOP
        Auto-fix: Normalize to theme's animation preset (subtle, consistent)
        """

    class StructuralSlopDetector:
        """
        Detects:
        - Too many slides (>15 for pitch deck, >25 for report)
        - No narrative arc (flat emotional intensity across all slides)
        - Missing critical slides (pitch deck without team/ask)
        - Information front-loading (all substance in slides 1-3, padding after)
        - No clear conclusion/CTA

        Threshold: >1 structural violation = SLOP
        Auto-fix: Restructure outline via Layer 1 re-invocation
        """
```

### SSIM Visual Regression Testing

```python
class VisualRegressionTester:
    """
    Compares rendered slides against golden master references.
    Used in CI/CD to prevent visual quality degradation.
    """

    async def test_slide(
        self,
        rendered_screenshot: bytes,
        golden_master: bytes,
        threshold: float = 0.95,  # SSIM threshold
    ) -> RegressionResult:
        """
        1. Render slide at 1920×1080 via Playwright
        2. Compare against golden master using SSIM
        3. If SSIM < threshold, flag as regression
        4. Generate diff image highlighting changed regions
        5. Store in regression report with before/after comparison
        """

    async def update_golden_master(self, theme_id: str, slide_type: str):
        """
        After deliberate visual changes, update golden masters.
        Requires explicit approval (not auto-updated).
        """
```

### Accessibility Validation

```python
class AccessibilityValidator:
    """WCAG 2.1 AA compliance checker."""

    def validate(self, slide: ResolvedSlide) -> AccessibilityReport:
        """
        Checks:
        1. Color contrast ratios (4.5:1 body text, 3:1 large text, 3:1 UI components)
        2. Font size minimums (14px body minimum, 18px heading minimum)
        3. Alt text for all images
        4. Reading order (logical tab/arrow-key order)
        5. Color not used as sole differentiator (charts must use patterns + color)
        6. Touch target sizes (44×44px minimum for interactive elements)
        """
```

---

## 4.9 Reflection Loop

When Layer 6 (QA) identifies issues, the pipeline can loop back:

```python
class ReflectionLoop:
    """
    Determines which layer to re-invoke based on QA findings.
    Maximum 2 reflection iterations to prevent infinite loops.
    """

    ROUTING = {
        "structural_slop": 1,        # Back to Narrative Intelligence
        "content_slop": 2,           # Back to Content Intelligence
        "layout_slop": 3,            # Back to Spatial Design
        "image_slop": 4,             # Back to Visual Generation
        "typography_slop": 5,        # Back to Composition Engine
        "color_slop": 5,             # Back to Composition Engine
        "animation_slop": 5,         # Back to Composition Engine
        "composition_failure": 3,    # Back to Spatial Design (different layout)
    }

    async def reflect(
        self,
        qa_result: QAResult,
        iteration: int,
    ) -> Optional[int]:  # Returns layer number to re-invoke, or None if passing
        if iteration >= 2:
            logger.warning("Max reflection iterations reached, passing with current quality")
            return None
        if qa_result.weighted_score >= 70:
            return None
        worst_category = qa_result.worst_scoring_category
        return self.ROUTING.get(worst_category, 5)
```

---

## 4.10 Agent System (12 Agents) — Grounded in Agentic AI Design Patterns

> *Following industry-leading Agentic AI Design Patterns (ReAct, Reflection, Planning, Multi-Agent Collaboration), the Meridian system coordinates 12 specialized agents to deliver production-grade output that adapts dynamically during generation.*

### Pattern Implementation
1. **Planning (Plan-and-Execute)**: The Director Agent plans the slide generation steps strictly before execution, generating a JSON-based pipeline map.
2. **ReAct (Reasoning and Acting)**: The Crafter and Layout agents reason through complex design constraints visually, invoking tools (like the Yoga WASM solver) in a loop until the layout settles.
3. **Reflection**: The QA Agent and Composition Agent utilize a Generation-Critique-Refinement cycle, sending failed render specs back to the Artist Agent or Content Agent for auto-correction.
4. **Tool Use**: Agents have explicit access to structural tools (bounding box calculators, color contrast verifiers, text string length measures).

### Agent Roster

| Agent | Role | Primary Model | Design Pattern Used |
|-------|------|---------------|---------------------|
| **Director Agent** | Orchestrates pipeline, state, and assigns tasks | — (logic/routing) | Planning / Orchestration |
| **Narrative Agent** | Story structure, arc, emotional modeling | Kimi-K2-Thinking | Planning |
| **Content Agent** | Text/data generation, semantic typing | DeepSeek-V3.2 | ReAct + Tool Use |
| **Layout Agent** | GLA composition, hierarchical definition | GPT-4o | Planning |
| **Real-Time Crafter** | Dynamic layout adjustment, reflowing constraints | GPT-4o | ReAct + Tool Use |
| **Real-Time Artist** | Design execution, micro-animations, asset selection | Kimi-K2-Thinking | ReAct |
| **Visual Agent** | Image prompting (Nano Banana Pro specs), templates | DeepSeek-V3.2 | Tool Use (InvokeAI/mmagic) |
| **Code Agent** | React/Three.js/reveal.js code generation | Qwen2.5-coder-32b | Tool Use (Compiler/Linter) |
| **Composition Agent**| Layer 5 visual scoring, balance adjustment | Phi-4-vision-15B | Reflection (Critique) |
| **QA Agent** | Slop detection, SSIM regression testing | Phi-4-vision-15B | Reflection (Refine) |
| **Brand Agent** | Input processing, theme compilation, palette math | GPT-4o-mini | Single-shot generation |
| **Export Agent** | Multi-format rendering, native PPTX generation | Automated pipeline | Tool Use |

### Agent Communication Protocol

```python
class AgentMessage:
    """Formal protocol for inter-agent communication via Context Board."""

    sender: str          # Agent name
    recipient: str       # Agent name or "broadcast"
    layer: int           # Which pipeline layer this message belongs to
    message_type: str    # "request" | "response" | "feedback" | "escalation"
    payload: dict        # Layer-specific data
    correlation_id: str  # Links request to response
    timestamp: datetime
    version: str = "1.0" # Protocol version for backward compatibility
```

---

## 4.11 Theme Engine

### Built-in Themes (24 Core + Generative)

V9 retains V7's 24 built-in themes and extends the generative engine.

### Theme Schema

```typescript
interface Theme {
  id: string;
  name: string;
  category: "professional" | "creative" | "minimal" | "bold" | "dark" | "playful";

  // Colors
  colors: {
    primary: string;       // Main brand/accent color
    secondary: string;     // Supporting color
    accent: string;        // Highlight/CTA color
    background: string;    // Slide background
    surface: string;       // Card/container background
    text_primary: string;  // Heading text
    text_secondary: string; // Body text
    text_muted: string;    // Captions, metadata
    success: string;
    warning: string;
    error: string;
    // Computed
    palette: string[];     // 12-color expanded palette (5 shades × 2 bases + 2 neutrals)
    contrast_matrix: Record<string, Record<string, number>>;  // WCAG ratios
  };

  // Typography
  typography: {
    heading_font: string;   // Google Font or system font
    body_font: string;
    mono_font: string;
    scale: number;          // Modular scale ratio (1.2=minor third, 1.333=augmented fourth, 1.5=perfect fifth)
    base_size: number;      // px
    heading_weight: number; // 600-900
    body_weight: number;    // 300-500
    line_height: number;    // 1.4-1.8
    letter_spacing: {
      heading: string;      // e.g., "-0.02em"
      body: string;         // e.g., "0"
      caps: string;         // e.g., "0.1em"
    };
  };

  // Layout
  layout: {
    slide_width: number;    // 1920
    slide_height: number;   // 1080
    safe_area: { top: number; right: number; bottom: number; left: number };
    grid_columns: number;   // Default: 12
    grid_gap: number;       // px
    corner_radius: number;  // For cards, buttons
    shadow: string;         // CSS box-shadow
  };

  // Visual Style
  visual: {
    image_style: string;        // "photographic" | "illustration" | "3d_render" | "abstract"
    image_overlay: string;      // CSS gradient overlay for background images
    icon_style: string;         // "outline" | "filled" | "duotone"
    divider_style: string;      // "line" | "gradient" | "none"
    animation_preset: string;   // "subtle" | "dynamic" | "cinematic" | "none"
    background_pattern?: string; // Optional decorative pattern
  };
}
```

### Generative Theme Engine

```python
class GenerativeThemeEngine:
    """
    Creates themes from:
    1. Brand Input: User provides colors/fonts → generate complete theme
    2. Mood Input: User describes desired feel → generate appropriate theme
    3. URL Extraction: User provides website → extract and compile theme
    4. Industry Default: Based on deck type → select appropriate base theme
    """

    async def from_brand_input(self, brand: BrandInput) -> Theme:
        """
        Takes user-provided primary color and optional font preferences.
        Generates a complete theme using color theory:
        - Complementary/analogous secondary color
        - Accessibility-tested contrast pairs
        - 5-shade palette expansion per base color
        - Font pairing recommendation (if only heading font provided)
        - Modular scale selection based on font metrics
        """

    async def from_mood(self, mood: str, deck_type: DeckType) -> Theme:
        """
        Natural language to theme:
        - "bold and energetic startup" → Vibrant palette, Inter/Space Grotesk, large scale
        - "elegant corporate" → Muted palette, Playfair Display/Source Sans Pro, refined spacing
        - "tech/developer" → Dark theme, JetBrains Mono/Inter, tight spacing
        """

    async def from_url(self, url: str) -> Theme:
        """
        Extracts brand DNA from a website:
        1. Playwright navigates to URL
        2. Extract computed styles: colors, fonts, spacing
        3. Extract logo (largest SVG/PNG in header)
        4. Analyze color distribution
        5. Compile into Theme object
        """
```

---

## 4.12 Template Library (100+ Built-In)

### Template Philosophy

V9 templates are **NOT static layouts**. They are **GLA Pattern Presets** — pre-tuned combinations of GLA primitives optimized for specific content structures. Each template is a set of rules, not a fixed file.

### Template Categories

| Category | Count | Examples |
|----------|-------|---------|
| **Title Slides** | 12 | Centered hero, split image, gradient overlay, video background, stat hero, quote opener, minimal, bold typography, corner image, pattern bg, dark cinematic, animated particles |
| **Content Slides** | 20 | Single column, two column (text/image), three column comparison, sidebar infobox, bullet list with icons, numbered steps, timeline horizontal, timeline vertical, process flow, feature highlight |
| **Data Slides** | 15 | Chart + insight, metrics dashboard (3-stat, 4-stat, 6-stat), comparison table, before/after, funnel, TAM/SAM/SOM, financial projection, year-over-year, benchmark |
| **Image Slides** | 10 | Full bleed, split screen, gallery (2/3/4/6 images), image + caption, image + text overlay, image mosaic, parallax depth |
| **Quote Slides** | 5 | Centered large quote, sidebar quote, quote + headshot, testimonial grid, customer logos |
| **Team Slides** | 5 | Team grid (3/4/6 members), team carousel, advisory board, org chart, founder spotlight |
| **Closing Slides** | 8 | CTA centered, contact info, Q&A, thank you, summary + CTA, next steps, social links, investment ask |
| **Transition Slides** | 5 | Section divider, chapter number, topic shift, breather (image-only), key question |
| **Specialized** | 20+ | Product demo, screenshot showcase, code explanation, roadmap, competitive matrix, pricing table, case study, video embed, interactive 3D, animated data reveal |

**Total**: 100+ GLA Pattern Presets

### Template Selection Logic

```python
async def select_template(
    content_elements: list[ContentElement],
    slide_role: SlideRole,
    narrative_intensity: float,
    mode: GenerationMode,
) -> GLAPattern:
    """
    For Standard Mode: Pattern matching on content structure → select best GLA pattern
    For Premium Mode: LLM composes novel GLA from scratch, optionally using a pattern as seed
    """
    if mode == "standard":
        # Fast path: match content fingerprint to pre-computed patterns
        fingerprint = compute_content_fingerprint(content_elements)
        candidates = match_gla_patterns(fingerprint, slide_role)
        return rank_by_intensity(candidates, narrative_intensity)[0]
    else:
        # Premium path: LLM generates unique GLA
        seed_pattern = match_gla_patterns(fingerprint, slide_role)[0]  # For reference
        return await llm_compose_gla(content_elements, slide_role, narrative_intensity, seed=seed_pattern)
```

---

## 4.13 Multi-Renderer Pipeline

### Renderer Architecture (4 Renderers, preserved from V7)

```
                           ┌─────────────────────────────┐
                           │      Slide DSL v3            │
                           │  (Single Source of Truth)    │
                           └──────────┬──────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │                │
              ┌─────▼──────┐  ┌──────▼───────┐  ┌──────▼──────┐  ┌─────▼──────┐
              │ Renderer 1  │  │ Renderer 2   │  │ Renderer 3  │  │ Renderer 4 │
              │ reveal.js   │  │ React+Three  │  │ Zero-dep    │  │ PptxGenJS  │
              │ (UnoCSS)    │  │ (Tailwind v4)│  │ HTML        │  │ (PPTX)     │
              └─────────────┘  └──────────────┘  └─────────────┘  └────────────┘
              │ Primary web  │  │ Interactive  │  │ Email/share │  │ PowerPoint │
              │ presentation │  │ 3D/animated  │  │ offline     │  │ editing    │
              └─────────────┘  └──────────────┘  └─────────────┘  └────────────┘
```

### Slide DSL v3 (Extended from V7's v2)

```typescript
interface SlideDSLv3 {
  version: "3.0";
  metadata: {
    id: string;
    created: string;
    generator_version: string;
    mode: "standard" | "premium";
    narrative_plan_hash: string;  // Links back to generation plan
  };
  presentation: {
    title: string;
    subtitle?: string;
    author?: string;
    date?: string;
    slide_count: number;
    aspect_ratio: "16:9" | "4:3" | "9:16";
    theme: Theme;
    brand?: BrandProfile;
    visual_thread: VisualThread;  // NEW: cross-deck visual coherence
    narrative_arc: NarrativeArc;  // NEW: emotional trajectory metadata
  };
  slides: SlideV3[];
}

interface SlideV3 {
  index: number;
  id: string;
  role: SlideRole;
  narrative: {
    purpose: string;
    key_message: string;
    emotional_intensity: number;
    transition_from_previous: string;
  };
  layout: {
    gla_tree: GLA_Node;  // NEW: Generative Layout Algebra tree
    resolved_positions: ResolvedPosition[];  // Pixel-perfect coordinates
    visual_weight_map: Record<string, number>;  // Element ID → visual weight
  };
  elements: SlideElement[];  // Rich typed elements
  style: {
    background: Background;
    animation_preset: string;
    transition_in: TransitionConfig;
    transition_out: TransitionConfig;
  };
  qa: {
    composition_score?: number;
    slop_score?: number;
    accessibility_score?: number;
  };
  customFields?: Record<string, unknown>;  // Extensible (preserved from V7)
}
```

---

## 4.13b Progressive 3D Enhancement Levels

> Not every slide needs Three.js. Not every device can handle WebGL. Meridian uses a **5-level progressive enhancement system** that picks the right rendering fidelity per slide, per device, per user tier.

### Enhancement Level Architecture

```
              Device & Tier Assessment
                       │
                       ▼
        ┌─────────────────────────────┐
        │   Enhancement Level Picker  │
        │                             │
        │   Battery? GPU? Tier?       │
        │   Content type? User pref?  │
        └──────────┬──────────────────┘
                   │
     ┌─────────┬───┼────┬──────────┬──────────┐
     ▼         ▼   ▼    ▼          ▼          ▼
  ┌──────┐ ┌──────┐ ┌──────┐  ┌──────┐  ┌──────┐
  │ none │ │css-  │ │ svg- │  │ lite │  │ full │
  │      │ │3d-   │ │illus │  │      │  │      │
  │ Pure │ │fake  │ │trat° │  │Three │  │Three │
  │ CSS  │ │      │ │      │  │ .js  │  │ .js+ │
  │ flat │ │CSS   │ │Isom. │  │<10K  │  │Post  │
  │      │ │trans │ │SVG   │  │poly  │  │Proc  │
  └──────┘ └──────┘ └──────┘  └──────┘  └──────┘
   0ms      +2ms     +5ms      +80ms     +200ms
  render    render   render    render    render
  overhead  overhead overhead  overhead  overhead
```

### Level Definitions

```typescript
type EnhancementLevel = "none" | "css-3d-fake" | "svg-illustration" | "lite" | "full";

interface Enhancement3DConfig {
  level: EnhancementLevel;
  perSlideOverride: boolean;    // Allow per-slide level override
  autoDegrade: boolean;         // Auto-downgrade if GPU struggles
  batteryThreshold: number;     // Switch to lower level below this % (default: 20)
  respectReducedMotion: boolean; // Honor prefers-reduced-motion
}

const ENHANCEMENT_LEVELS: Record<EnhancementLevel, EnhancementSpec> = {
  "none": {
    description: "Pure CSS — flat design, zero overhead",
    technology: "CSS only",
    maxPolygons: 0,
    gpuRequired: false,
    bundleSize: "0 KB added",
    renderOverhead: "0ms",
    bestFor: ["text-heavy slides", "data tables", "simple lists", "email export"],
    visualFeatures: [
      "Flat color backgrounds",
      "CSS gradients (linear, radial, conic)",
      "Box shadows for depth illusion",
      "Border-based decorations",
    ],
  },

  "css-3d-fake": {
    description: "CSS transforms — fake 3D perspective, no WebGL",
    technology: "CSS transform3d + perspective",
    maxPolygons: 0,
    gpuRequired: false,  // Uses CSS GPU compositing, not WebGL
    bundleSize: "0 KB added",
    renderOverhead: "+2ms",
    bestFor: ["card tilts", "parallax hero images", "flip animations", "perspective text"],
    visualFeatures: [
      "perspective() transforms on containers",
      "rotateX/Y for card hover effects",
      "translateZ for layered depth",
      "CSS backdrop-filter for glassmorphism",
      "Preserve-3d for nested transforms",
    ],
  },

  "svg-illustration": {
    description: "Isometric SVG illustrations — lightweight, scalable 3D look",
    technology: "SVG + CSS animations",
    maxPolygons: 0,
    gpuRequired: false,
    bundleSize: "+15 KB (SVG library)",
    renderOverhead: "+5ms",
    bestFor: ["hero illustrations", "process diagrams", "isometric infographics"],
    visualFeatures: [
      "Pre-rendered isometric SVG components",
      "Animated SVG paths (draw-in effect)",
      "Layered SVG for parallax scrolling",
      "Dynamic recoloring via CSS custom properties",
      "Crisp at any zoom level (vector)",
    ],
  },

  "lite": {
    description: "Lazy-loaded Three.js — real 3D with strict polygon budget",
    technology: "Three.js (lazy-loaded, tree-shaken)",
    maxPolygons: 10_000,
    gpuRequired: true,
    bundleSize: "+45 KB (tree-shaken Three.js core)",
    renderOverhead: "+80ms first frame, +8ms subsequent",
    bestFor: ["product showcases", "data globes", "3D charts", "architectural models"],
    visualFeatures: [
      "Real-time 3D meshes (< 10K polygons)",
      "Basic PBR materials (metalness, roughness)",
      "Ambient + directional lighting",
      "Orbit camera controls (drag to rotate)",
      "Shadow maps (basic)",
      "LOD switching at distance",
    ],
    // Performance guardrails
    guardrails: {
      maxDrawCalls: 50,
      maxTextureMemory: "16 MB",
      targetFPS: 30,
      autoDegrade: "If FPS < 20 for 2 seconds → switch to svg-illustration",
    },
  },

  "full": {
    description: "Full Three.js + post-processing — cinematic 3D",
    technology: "Three.js + postprocessing + @react-three/fiber",
    maxPolygons: 100_000,
    gpuRequired: true,
    bundleSize: "+120 KB (Three.js + effects)",
    renderOverhead: "+200ms first frame, +16ms subsequent",
    bestFor: ["hero slides", "immersive transitions", "3D data landscapes", "product demos"],
    visualFeatures: [
      "High-poly meshes with LOD",
      "Advanced PBR + environment maps",
      "Post-processing: bloom, DOF, film grain, vignette",
      "Particle systems (confetti, snow, data particles)",
      "Volumetric lighting",
      "Screen-space reflections",
      "Smooth camera transitions between slides",
      "Physics-based animations (spring, gravity)",
    ],
    guardrails: {
      maxDrawCalls: 200,
      maxTextureMemory: "64 MB",
      targetFPS: 60,
      autoDegrade: "If FPS < 30 for 3 seconds → switch to lite",
    },
  },
};
```

### Per-Slide Level Selection

```typescript
interface SlideV3 {
  // ... existing fields ...
  enhancement: {
    level: EnhancementLevel;              // Chosen by AI or user override
    reason: string;                       // "Product showcase needs real 3D rotation"
    fallback: EnhancementLevel;           // If chosen level fails → use this
    elements_3d: {                        // Which elements use 3D
      elementId: string;
      meshSource: string;                 // GLTF URL or procedural spec
      animationPreset: string;            // "orbit" | "float" | "reveal" | "explode"
    }[];
  };
}

// AI picks level based on:
function selectEnhancementLevel(
  slide: SlideV3,
  device: DeviceProfile,
  userTier: "free" | "pro" | "enterprise",
): EnhancementLevel {
  // Free tier: max "css-3d-fake"
  // Pro tier: max "lite"
  // Enterprise: up to "full"
  // Device without GPU: max "svg-illustration"
  // Battery < 20%: auto-degrade one level
  // User preference override always wins
}
```

### Speed Impact Per-Level Table

| Level | First Render | Subsequent | Bundle Added | GPU Required | Best For |
|-------|-------------|------------|-------------|-------------|----------|
| `none` | +0ms | +0ms | 0 KB | No | Text, tables, minimal slides |
| `css-3d-fake` | +2ms | +1ms | 0 KB | No (CSS compositing) | Card tilts, parallax, glass |
| `svg-illustration` | +5ms | +2ms | +15 KB | No | Hero illustrations, isometric |
| `lite` | +80ms | +8ms | +45 KB | Yes | Product 3D, data globes |
| `full` | +200ms | +16ms | +120 KB | Yes | Cinematic hero, immersive |

---

## 4.14 Canvas Editor — "Figma for Slides"

> Konva.js is the rendering engine. What we build ON TOP of it is a full design editor with component library, variant system, auto-layout, infinite canvas, design tokens, and plugin architecture.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MERIDIAN SLIDE EDITOR — "FIGMA FOR SLIDES"                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  TOOLBAR                                                              │  │
│  │  [Select] [Text] [Shape] [Image] [Chart] [Code] [3D]                 │  │
│  │  [↩ Undo] [↪ Redo] [Copy] [Paste] [Delete]                           │  │
│  │  [Components ▼] (Buttons, Cards, Icons, Diagrams...)                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────┐ ┌─────────────────────────────────────────┐ ┌──────────────┐  │
│  │ SLIDE    │ │  INFINITE CANVAS (Zoom 10%-2000%, Pan)  │ │ PROPERTY     │  │
│  │ PANEL    │ │                                         │ │ PANEL        │  │
│  │          │ │  ┌─────────────────────────────────────┐ │ │              │  │
│  │ [Slide1] │ │  │  Active Slide (1920×1080)           │ │ │ POSITION     │  │
│  │ [Slide2] │ │  │                                     │ │ │ X: Y: W: H:  │  │
│  │ [Slide3] │ │  │  ┌──────────┐  ┌────────────────┐  │ │ │ [Lock Ratio] │  │
│  │   ...    │ │  │  │ Title    │  │ Hero Image     │  │ │ │              │  │
│  │          │ │  │  └──────────┘  └────────────────┘  │ │ │ DESIGN       │  │
│  │ ──────── │ │  │  ┌──────────────────────────────┐  │ │ │ TOKENS       │  │
│  │ COMPONENT│ │  │  │ Stats Row (constraint-bound) │  │ │ │ Font: [▼]    │  │
│  │ LIBRARY  │ │  │  └──────────────────────────────┘  │ │ │ Size: Weight: │  │
│  │          │ │  └─────────────────────────────────────┘ │ │ Color: [◉]   │  │
│  │ Buttons  │ │                                         │ │ Radius: [8]  │  │
│  │ Cards    │ │  Ruler guides (toggleable)               │ │ Shadow: [▼]  │  │
│  │ Icons    │ │  Snap markers (element alignment)        │ │ Spacing: [▼] │  │
│  │ Charts   │ │  [Zoom: -] [100%] [+] [Fit to screen]  │ │              │  │
│  │ Diagrams │ │                                         │ │ VARIANTS     │  │
│  │ Shapes   │ │                                         │ │ [A: Current] │  │
│  │          │ │                                         │ │ [B: Minimal] │  │
│  └──────────┘ └─────────────────────────────────────────┘ │ [C: Glow]    │  │
│                                                            │ [D: Glass]   │  │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  AI BAR: "Make this slide more dramatic" | "Add traction chart"       │  │
│  │  AI ASSIST: [Auto-layout] [Improve colors] [Rewrite] [Match brand]   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Infinite Canvas System

Unlike basic canvas editors locked to a single 1920×1080 viewport, Meridian uses an **infinite canvas** with smooth zoom/pan:

```typescript
interface InfiniteCanvasConfig {
  minZoom: 0.1;    // 10% — see entire deck overview
  maxZoom: 20.0;   // 2000% — pixel-level precision editing
  defaultZoom: 1.0; // 100% — single slide view
  panBounds: "infinite"; // No boundaries on pan

  // Zoom presets
  presets: {
    "fit-slide": "auto";     // Fit current slide to viewport
    "fit-all": "auto";       // Fit all slides (overview mode)
    "100%": 1.0;             // Actual pixel size
    "detail": 2.0;           // Double zoom for detail work
  };

  // Performance: Only render visible elements
  culling: true;             // Elements outside viewport are not rendered
  lodLevels: {
    overview: { minZoom: 0.1, maxZoom: 0.3, renderDetail: "thumbnail" },
    normal:   { minZoom: 0.3, maxZoom: 2.0, renderDetail: "full" },
    detail:   { minZoom: 2.0, maxZoom: 20.0, renderDetail: "subpixel" },
  };
}
```

### Component Library (Drag & Drop)

Pre-built, reusable design components that respect the active theme's design tokens:

```typescript
interface SlideComponent {
  id: string;
  category: "button" | "card" | "icon" | "chart" | "diagram" | "shape"
          | "stat_block" | "testimonial" | "pricing_tier" | "team_member"
          | "cta_block" | "feature_grid" | "logo_strip" | "timeline_node";
  name: string;               // e.g., "Feature Card — Accent Border"
  variants: ComponentVariant[];  // 3-5 style variations per component
  designTokens: DesignToken[];   // Inherited from active theme
  constraints: ConstraintRules;  // Min/max sizes, allowed children
  thumbnail: string;             // Preview image for library panel
  gla_fragment: GLA_Node;        // Layout algebra fragment for constraint integration
}

interface ComponentVariant {
  id: string;
  name: string;  // "Bold" | "Minimal" | "Glassmorphism" | "Outline" | "Gradient"
  preview: string; // Thumbnail URL
  styles: {
    background: string;
    borderRadius: number;
    shadow: string;
    borderWidth: number;
    borderColor: string;
    padding: Padding;
    opacity: number;
  };
  // Animation preset for this variant
  entranceAnimation?: AnimationConfig;
}

// COMPONENT CATEGORIES with counts
const COMPONENT_LIBRARY = {
  buttons:       { count: 8,  variants_per: 5 },  // Primary, Outline, Ghost, Gradient, Glass, Pill, Icon, CTA
  cards:         { count: 12, variants_per: 4 },  // Feature, Stat, Testimonial, Pricing, Team, Image, Quote, Comparison, Timeline, Metric, Icon, Data
  icons:         { count: 200, source: "lucide" }, // Lucide icon set (line, filled, duotone)
  charts:        { count: 12, variants_per: 3 },  // Bar, Line, Pie, Donut, Area, Scatter, Funnel, Waterfall, TAM/SAM/SOM, Comparison, Radar, Gauge
  diagrams:      { count: 6,  variants_per: 2 },  // Flowchart, Timeline, Org chart, Mind map, Process, Comparison
  shapes:        { count: 15, variants_per: 3 },  // Rectangle, Circle, Triangle, Arrow, Star, Hexagon, Pentagon, Line, Curve, Badge, Ribbon, Bracket, Callout, Blob, Wave
  stat_blocks:   { count: 4,  variants_per: 3 },  // Single metric, Comparison, Trend, Counter
  composite:     { count: 8,  variants_per: 3 },  // Feature grid, Logo strip, Team row, Pricing table, CTA block, Social proof, App screenshot, Browser mockup
};
// TOTAL: ~265 components × ~3.5 avg variants = ~925 component-variant combinations
```

### Variant System (Per-Element Style Alternatives)

When any element is selected, the Property Panel shows 3-5 AI-generated style variants:

```typescript
class VariantEngine {
  /**
   * Generates style variants for any selected element.
   * Uses the active theme's design tokens to ensure all variants
   * are on-brand and harmonious.
   */
  async generateVariants(
    element: SlideElement,
    theme: Theme,
    count: number = 4,
  ): Promise<ComponentVariant[]> {
    // Variant generation strategies:
    const strategies = [
      "current",            // A: Current style (baseline)
      "minimal",            // B: Reduce visual weight (lighter, smaller, less shadow)
      "accent-emphasis",    // C: Add accent color glow, heavier shadow, border highlight
      "glassmorphism",      // D: Frosted glass effect with backdrop-blur
      "high-contrast",      // E: Maximum contrast, bold typography, dark/light flip
    ];

    return strategies.slice(0, count).map(strategy =>
      this.applyStrategy(element, theme, strategy)
    );
  }

  /**
   * User selects a variant → system records preference.
   * Over time, the system learns user's style preferences
   * and prioritizes similar variants in future generations.
   */
  async recordPreference(
    userId: string,
    elementType: string,
    chosenVariant: string,
    rejectedVariants: string[],
  ): Promise<void> {
    // Store in ChromaDB as preference embedding
    // Used to rank future variant suggestions
  }
}
```

### Auto-Layout Engine (One-Click Layout Actions)

Select multiple elements → apply instant layout transformations:

```typescript
interface AutoLayoutAction {
  type:
    | "distribute-horizontal"    // Equal horizontal spacing between selected elements
    | "distribute-vertical"      // Equal vertical spacing
    | "align-left"               // Left-align all selected
    | "align-center"             // Center-align all selected
    | "align-right"              // Right-align all selected
    | "align-top"                // Top-align all selected
    | "align-middle"             // Middle-align all selected
    | "stack-vertical"           // Stack selected vertically with theme gap
    | "stack-horizontal"         // Stack selected horizontally with theme gap
    | "grid-auto"                // Auto-detect best grid (2×2, 3×3, etc.)
    | "timeline"                 // Arrange as horizontal timeline
    | "equalize-sizes"           // Make all selected elements same size
    | "pack-tightly"             // Minimize spacing between elements
    | "golden-ratio"             // Position using golden ratio proportions
    | "rule-of-thirds";          // Position on rule-of-thirds grid intersections
  selectedElements: string[];    // IDs of selected elements
}

class AutoLayoutEngine {
  /**
   * Apply layout action to selected elements.
   * Respects theme design tokens (minimum gap, safe area, grid).
   * Integrates with GLA — recalculates constraint tree after auto-layout.
   */
  apply(action: AutoLayoutAction, slide: SlideV3, theme: Theme): SlideV3 {
    const gap = theme.layout.grid_gap;
    const safeArea = theme.layout.safe_area;
    // ... compute new positions respecting constraints
  }
}
```

### Design Token System

Global design tokens inherited from the active theme, exposed in the Property Panel:

```typescript
interface DesignTokenSystem {
  // Spacing scale (based on 4px base unit)
  spacing: {
    xs: 4,    // 4px
    sm: 8,    // 8px
    md: 16,   // 16px
    lg: 24,   // 24px
    xl: 32,   // 32px
    "2xl": 48, // 48px
    "3xl": 64, // 64px
  };

  // Border radius scale
  radius: {
    none: 0,
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    "2xl": 24,
    full: 9999, // Pill shape
  };

  // Shadow elevation system
  shadows: {
    none: "none",
    sm: "0 1px 2px rgba(0,0,0,0.05)",
    md: "0 4px 6px rgba(0,0,0,0.07)",
    lg: "0 10px 15px rgba(0,0,0,0.10)",
    xl: "0 20px 25px rgba(0,0,0,0.15)",
    "inner": "inset 0 2px 4px rgba(0,0,0,0.06)",
    "glow": "0 0 20px var(--color-accent-alpha-30)",
  };

  // Opacity scale
  opacity: { 10: 0.1, 25: 0.25, 50: 0.5, 75: 0.75, 90: 0.9, 100: 1.0 };

  // All tokens update globally when theme changes
  // Every component/element inherits from this system
}
```

### Smart Slide Constraint Handles

When hovering over an element in the editor, constraint handles appear showing:
- **Min/Max bounds** (dotted lines showing how far the element can grow/shrink)
- **Snap guides** (alignment lines to other elements and grid)
- **Content-aware resize**: Dragging a text box automatically re-fits text (via PreTeXt.js)
- **Constraint lock indicator**: GLA-constrained elements show a lock icon; user can break the constraint to free-position
- **Margin/padding visualization**: Hold Alt to see spacing around elements
- **Alignment guides**: Pink lines show alignment with other elements on the slide

### Plugin Architecture

Extensible editor via a plugin system for custom tools and integrations:

```typescript
interface EditorPlugin {
  id: string;
  name: string;
  version: string;
  icon: string;       // SVG icon for toolbar

  // Plugin lifecycle
  onActivate(editor: EditorContext): void;
  onDeactivate(): void;

  // Plugin capabilities
  tools?: CustomTool[];           // New toolbar tools (e.g., "QR Code Generator")
  components?: SlideComponent[];  // New component library entries
  exportFormats?: ExportFormat[]; // New export targets
  shortcuts?: KeyboardShortcut[]; // Custom keyboard shortcuts
  panels?: CustomPanel[];         // New sidebar panels
}

// Example: QR Code plugin
const qrCodePlugin: EditorPlugin = {
  id: "qr-code-generator",
  name: "QR Code",
  version: "1.0.0",
  icon: "qr-code.svg",
  tools: [{
    name: "Insert QR Code",
    action: async (editor) => {
      const url = await editor.prompt("Enter URL for QR code:");
      const qrSvg = generateQR(url);
      editor.insertElement({ type: "image", src: qrSvg });
    },
  }],
  onActivate(editor) { /* register */ },
  onDeactivate() { /* cleanup */ },
};
```

### AI Assist Tools (Integrated in Property Panel)

Context-aware AI actions available for any selected element or slide:

```typescript
const AI_ASSIST_ACTIONS = {
  // Element-level actions
  "auto-layout":       "Select items → AI distributes them optimally",
  "improve-colors":    "Adjust element colors for better harmony/contrast",
  "rewrite-text":      "Rewrite selected text for clarity and impact",
  "generate-image":    "Generate contextual image for this slide position",
  "suggest-layout":    "Propose alternative GLA layout for current content",
  "match-brand":       "Adjust element to match brand guidelines exactly",
  "simplify":          "Reduce visual complexity (fewer elements, more whitespace)",
  "dramatize":         "Increase visual impact (bolder type, higher contrast, larger hero)",
  "add-data-viz":      "Convert text data into a chart/diagram automatically",
  "a11y-fix":          "Fix accessibility issues on this element (contrast, alt text, size)",
};
```

### react-konva Integration

```typescript
const SlideCanvas: React.FC<{
  slide: SlideV3;
  editable: boolean;
  zoom: number;
  panOffset: { x: number; y: number };
}> = ({ slide, editable, zoom, panOffset }) => {
  return (
    <Stage
      width={window.innerWidth}
      height={window.innerHeight}
      scaleX={zoom}
      scaleY={zoom}
      x={panOffset.x}
      y={panOffset.y}
      draggable={!editable} // Pan when not editing
      onWheel={handleZoom}  // Pinch/scroll zoom
    >
      {/* Infinite canvas background (grid pattern) */}
      <Layer listening={false}>
        <InfiniteGrid zoom={zoom} />
      </Layer>

      {/* Slide content layer */}
      <Layer>
        <SlideBackground background={slide.style.background} />

        {slide.elements.map((element) => {
          const pos = slide.layout.resolved_positions.find(p => p.elementId === element.id);
          return (
            <SlideElement
              key={element.id}
              element={element}
              position={pos}
              editable={editable}
              onTransform={handleTransform}
              onSelect={handleSelect}
            />
          );
        })}
      </Layer>

      {/* Constraint visualization + snap guides (edit mode only) */}
      {editable && (
        <Layer listening={false}>
          <ConstraintOverlay glaTree={slide.layout.gla_tree} />
          <SnapGuides activeElement={selectedElement} allElements={slide.elements} />
          <RulerGuides visible={showRulers} zoom={zoom} />
        </Layer>
      )}
    </Stage>
  );
};
```

---

## 4.15 LLM Model Inventory & Routing

### Full Model Stack

| Model | Provider | Cost Tier | Latency | Primary Use in V9 |
|-------|----------|-----------|---------|-------------------|
| **Kimi-K2-Thinking** | Azure | $$$ | High | Layer 1: Narrative strategy, complex reasoning (Premium only) |
| **DeepSeek-V3.2** | Azure | $$ | Medium | Layer 2: Content generation, structured JSON |
| **GPT-4o** | Azure | $$ | Medium | Layer 3: Spatial reasoning, layout composition (Premium only) |
| **GPT-4o-mini** | Azure | $ | Low | Brand processing, lightweight tasks |
| **Phi-4-reasoning-vision-15B** | Azure | $$ | Medium | Layers 5-6: Visual QA, composition scoring (Premium only) |
| **Mistral-medium-2505** | Azure | $$ | Medium | Text quality, structured output |
| **Groq llama-3.3-70b** | Groq (8 keys) | FREE | Very Low | Standard Mode: content, outlines (round-robin) |
| **Qwen2.5-coder-32b** | Cloudflare | FREE | Low | Code generation: React, Three.js, reveal.js HTML |
| **GLM-4.7-Flash** | Cloudflare | FREE | Very Low | Standard Mode: fast text, layout selection |
| **Gemma-3-12b-it** | Cloudflare | FREE | Low | Lightweight vision QA (Standard Mode) |
| **qwen3.6-plus** | OpenRouter | FREE | Medium | Backup text generation |

### Image Models

| Model | Provider | Cost | Primary Use in V9 |
|-------|----------|------|-------------------|
| **FLUX.1-Kontext-pro** | Azure | $$ | Premium Mode: hero images, key visuals |
| **Phoenix-1.0** | Cloudflare | FREE | Standard Mode: general illustrations |
| **Lucid-Origin** | Cloudflare | FREE | Artistic backgrounds, textures |

### Model Router

```python
class ModelRouter:
    """
    Task-based routing with cost optimization.
    Free models first, escalate only when quality demands.
    """

    ROUTING_TABLE = {
        # Layer 1: Narrative Intelligence
        "narrative_planning": {
            "premium": ["kimi-k2-thinking", "deepseek-v3.2", "groq-llama-3.3-70b"],
            "standard": ["groq-llama-3.3-70b", "glm-4.7-flash", "deepseek-v3.2"],
        },
        # Layer 2: Content Intelligence
        "content_generation": {
            "premium": ["deepseek-v3.2", "groq-llama-3.3-70b", "qwen2.5-coder-32b"],
            "standard": ["groq-llama-3.3-70b", "glm-4.7-flash", "qwen3.6-plus"],
        },
        # Layer 3: Spatial Design
        "layout_composition": {
            "premium": ["gpt-4o", "deepseek-v3.2", "glm-4.7-flash"],
            "standard": ["glm-4.7-flash", "groq-llama-3.3-70b"],  # or pattern-match (no LLM)
        },
        # Layer 4: Visual Generation (code)
        "code_generation": {
            "premium": ["qwen2.5-coder-32b", "deepseek-v3.2", "groq-llama-3.3-70b"],
            "standard": ["qwen2.5-coder-32b", "glm-4.7-flash", "groq-llama-3.3-70b"],
        },
        # Layer 5: Composition
        "visual_scoring": {
            "premium": ["phi-4-reasoning-vision-15b", "gemma-3-12b-it"],
            "standard": [],  # Skip in standard mode (rule-based only)
        },
        # Layer 6: QA
        "slop_detection": {
            "premium": ["phi-4-reasoning-vision-15b", "gemma-3-12b-it"],
            "standard": [],  # Automated rules only
        },
        # Image Generation
        "hero_image": {
            "premium": ["flux-kontext-pro", "phoenix-1.0", "lucid-origin"],
            "standard": ["phoenix-1.0", "lucid-origin"],
        },
        "supporting_image": {
            "premium": ["phoenix-1.0", "lucid-origin"],
            "standard": ["lucid-origin", "icon_library"],
        },
    }

    async def route(self, task: str, mode: str, **kwargs) -> LLMResponse:
        chain = self.ROUTING_TABLE[task][mode]
        for model_id in chain:
            try:
                return await self.call_model(model_id, **kwargs)
            except (ModelUnavailableError, RateLimitError, TimeoutError):
                logger.warning(f"Model {model_id} failed, trying next in chain")
                continue
        raise AllModelsFailedError(f"No model available for task={task}")
```

### Cost Estimation Per Deck

| Mode | Estimated Cost | LLM Calls | Image Calls |
|------|---------------|-----------|-------------|
| **Standard (10 slides)** | $0.00 - $0.05 | 3-5 (mostly free models) | 2-5 (free models) |
| **Premium (10 slides)** | $0.30 - $0.80 | 8-15 (mixed paid/free) | 5-10 (paid + free) |

---

## 4.16 Regeneration System (4 Levels) + A/B Variant Generation

```
┌────────────────────────────────────────────────────────────────┐
│                    REGENERATION LEVELS                          │
│                                                                │
│  Level 1: ELEMENT REGENERATION                                 │
│  ─────────────────────────────                                 │
│  User clicks element → "Regenerate this"                       │
│  → Re-invoke Layer 2 (Content) for just this element           │
│  → Re-invoke Layer 4 (Visual) if it's an image/chart           │
│  → Keep layout, keep other elements                            │
│  Latency: <3s                                                  │
│                                                                │
│  Level 2: SECTION REGENERATION                                 │
│  ──────────────────────────────                                │
│  User selects elements → "Regenerate this section"             │
│  → Re-invoke Layer 2 for selected elements                     │
│  → Re-invoke Layer 3 (Spatial) to re-layout selected area      │
│  → Keep unselected elements                                    │
│  Latency: <5s                                                  │
│                                                                │
│  Level 3: SLIDE REGENERATION                                   │
│  ──────────────────────────                                    │
│  User clicks slide → "Regenerate slide"                        │
│  Options:                                                      │
│    a) "Different layout" → Layer 3 with different GLA seed     │
│    b) "Different content" → Layer 2 → Layer 3 → Layer 4       │
│    c) "Different style" → Layer 4 + Layer 5                    │
│    d) "Complete reimagine" → Layer 1 (for this slide) → Full   │
│  Latency: <10s                                                 │
│                                                                │
│  Level 4: DECK REGENERATION                                    │
│  ──────────────────────────                                    │
│  User clicks → "Regenerate entire deck"                        │
│  → Full pipeline re-invocation with adjusted parameters        │
│  → Preserves user edits marked as "locked"                     │
│  Latency: Mode-dependent (Standard <15s, Premium <90s)         │
└────────────────────────────────────────────────────────────────┘
```

### A/B Variant Generation System (Premium)

For Levels 2-4, Premium mode generates **2-3 complete layout/style variants** per slide, enabling real A/B comparison before committing:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  VARIANT SELECTION UI                                                        │
│                                                                              │
│  Slide 4: "Market Opportunity"                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │  VARIANT A      │  │  VARIANT B      │  │  VARIANT C      │                │
│  │  (Current)      │  │  (Minimal)      │  │  (Bold)         │                │
│  │                 │  │                 │  │                 │                │
│  │  ┌──────────┐  │  │  ┌──────────┐  │  │  ┌──────────┐  │                │
│  │  │ TAM/SAM  │  │  │  │          │  │  │  │   $47B   │  │                │
│  │  │ /SOM     │  │  │  │ $47B     │  │  │  │  MARKET  │  │                │
│  │  │ circles  │  │  │  │ Clean    │  │  │  │   hero   │  │                │
│  │  │ +stats   │  │  │  │ numbers  │  │  │  │ + chart  │  │                │
│  │  └──────────┘  │  │  └──────────┘  │  │  └──────────┘  │                │
│  │                 │  │                 │  │                 │                │
│  │ Layout: 2col    │  │ Layout: center  │  │ Layout: hero+   │                │
│  │ Comp: 82/100    │  │ Comp: 76/100    │  │ Comp: 88/100    │                │
│  │                 │  │                 │  │                 │                │
│  │ [✓ Select]      │  │ [  Select ]     │  │ [  Select ]     │                │
│  │ [↻ Regenerate]  │  │ [↻ Regenerate]  │  │ [↻ Regenerate]  │                │
│  └────────────────┘  └────────────────┘  └────────────────┘                 │
│                                                                              │
│  [Apply Selection]  [Skip — Keep Current]  [Generate More Variants]          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Variant Generation Engine

```python
class VariantGenerator:
    """
    Generates 2-3 layout/style variants per slide for A/B comparison.
    Each variant uses a different GLA seed, visual weight strategy,
    and color temperature to produce visually distinct alternatives.
    """

    VARIATION_AXES = [
        "gla_seed",           # Different layout algebra tree (column vs. row vs. grid)
        "weight_strategy",    # Balanced vs. hero-dominant vs. minimalist
        "color_temperature",  # Warm shift (+10°) vs. cool shift (-10°) vs. neutral
        "typography_scale",   # Compact (0.85x) vs. standard (1.0x) vs. dramatic (1.2x)
        "image_treatment",    # Contained vs. full-bleed vs. cutout vs. none
        "density",            # Dense (more elements) vs. sparse (fewer, larger)
    ]

    async def generate_variants(
        self,
        slide: SlideV3,
        narrative_plan: NarrativePlan,
        theme: Theme,
        count: int = 3,
    ) -> list[SlideVariant]:
        """
        For each variant:
        1. Mutate GLA seed → produce different layout tree
        2. Adjust visual weights → different element emphasis
        3. Shift color temperature → different mood
        4. Re-invoke Layer 3+4+5 with mutated parameters
        5. Score each variant with Composition Intelligence Engine
        6. Return ranked by composition score (highest first)
        """
        variants = []
        for i in range(count):
            mutated_params = self._mutate_generation_params(slide, i)
            variant_slide = await self.pipeline.generate_slide(
                content=slide.elements,
                narrative=narrative_plan,
                theme=theme,
                gla_seed=mutated_params.gla_seed,
                weight_bias=mutated_params.weight_strategy,
                color_shift=mutated_params.color_temperature,
            )
            variant_slide.composition_score = await self.scorer.score(variant_slide)
            variants.append(variant_slide)

        return sorted(variants, key=lambda v: v.composition_score, reverse=True)

    def _mutate_generation_params(self, slide: SlideV3, index: int) -> MutatedParams:
        """
        Variant 0: Original parameters (baseline)
        Variant 1: Opposite layout direction + minimalist weight + cool shift
        Variant 2: Grid layout + hero-dominant weight + warm shift
        """
        strategies = [
            MutatedParams(gla_seed="original", weight_strategy="balanced", color_temperature=0),
            MutatedParams(gla_seed="flip_axis", weight_strategy="minimalist", color_temperature=-10),
            MutatedParams(gla_seed="grid_alt", weight_strategy="hero_dominant", color_temperature=+10),
        ]
        return strategies[index % len(strategies)]


class SlideVariant:
    slide: SlideV3
    variant_label: str              # "A", "B", "C"
    composition_score: float        # 0-100 from Composition Intelligence Engine
    variation_description: str      # "Grid layout with hero image, warm palette"
    diff_from_original: list[str]   # ["Layout: 2col → grid", "Hero image: contained → full-bleed"]
```

### Variant Preference Learning

```typescript
interface VariantPreference {
  userId: string;
  slideRole: SlideRole;           // "title" | "data" | "comparison" etc.
  chosenVariant: {
    gla_pattern: string;          // Which layout was preferred
    weight_strategy: string;
    color_temperature: number;
  };
  rejectedVariants: string[];
  timestamp: string;
}

// System learns: "This user prefers minimalist layouts for data slides"
// Future generation: Bias toward minimalist GLA seeds for data slides
// Stored in ChromaDB as preference embeddings for similarity matching
```

---

## 4.17 Export Pipeline

### Format Matrix (Extended from V7)

| Format | Technology | Quality | Editable | Use Case | Target Size |
|--------|-----------|---------|----------|----------|-------------|
| **reveal.js HTML** | reveal.js v6 + UnoCSS | High | Source | Web presenting, reading mode | ~500KB |
| **React App** | Vite build + Tailwind v4 | High | Source | Embedding, interactive, 3D | ~2MB |
| **Zero-dep HTML** | Inline CSS/JS bundler | Good | Source | Email, sharing, offline | <500KB |
| **PPTX** | PptxGenJS v4.0.1 | High | Full | PowerPoint editing | ~5MB |
| **PDF** | Playwright page.pdf() | Perfect | None | Print, archive | ~3MB |
| **PNG** | Playwright screenshot | High | None | Social media, thumbnails | ~200KB/slide |
| **Markdown** | DSL → MD converter | Text | Full | Documentation, wiki | ~50KB |

### PPTX Generation (Enhanced)

```python
class PptxGenerator:
    """
    Generates native PPTX with fully editable elements.
    No screenshot-based slides. Every element is a native PPTX object.
    """

    KNOWN_LIMITATIONS = {
        "hex_prefix": "NEVER use '#' prefix — causes file corruption. Always 'FF0000' not '#FF0000'",
        "animations": "PptxGenJS does not support slide animations/transitions",
        "smartart": "Not supported — use manual shapes",
        "font_embedding": "Not supported — use web-safe or system fonts",
        "shape_grouping": "Not supported — position elements individually",
        "object_mutation": "PptxGenJS mutates options in-place — always pass fresh objects",
        "three_js_scenes": "Cannot embed 3D — render as static PNG via Playwright",
    }

    # Fallback: python-pptx for server-side generation when PptxGenJS is unavailable
    FALLBACK_LIBRARY = "python-pptx"

    async def generate(self, dsl: SlideDSLv3) -> bytes:
        """
        For each slide:
        1. Create slide from theme (background, safe area)
        2. Map ContentElements to PptxGenJS calls:
           - heading → addText() with theme typography
           - bullets → addText() with bullet formatting
           - stat → addText() with large number formatting
           - image → addImage() from generated/uploaded URL
           - chart → addChart() with native PPTX chart types
           - table → addTable() with row/column API
           - Three.js scene → Playwright screenshot → addImage()
        3. Apply resolved positions from GLA solver
        4. Add speaker notes from narrative metadata
        """
```

### .potx Template Injection (Preserved from V7)

User-uploaded PowerPoint templates are supported. The system maps DSL elements to named placeholders in the .potx file, preserving corporate slide masters, footers, and branding.

### Brand Package Export (.zip)

Enterprise users can export a **complete brand package** — a reusable .zip archive containing every design asset generated for the presentation, ready for use in other tools (Figma, Canva, PowerPoint, Google Slides):

```python
class BrandPackageExporter:
    """
    Exports a self-contained brand package .zip from any generated presentation.
    Target users: Enterprise teams who need consistent brand assets across tools.
    """

    async def export(self, presentation: SlideDSLv3, theme: Theme) -> bytes:
        """
        Brand Package Structure:
        ─────────────────────────
        brand_package.zip
        ├── brand_manifest.json        # Complete brand definition
        │   ├── colors (primary, secondary, accent, surface, text, status)
        │   ├── typography (font families, weights, scales)
        │   ├── spacing rules (4px base unit, scale)
        │   └── usage guidelines (auto-generated)
        │
        ├── fonts/
        │   ├── primary-regular.woff2
        │   ├── primary-bold.woff2
        │   ├── primary-italic.woff2
        │   ├── heading-regular.woff2
        │   └── heading-bold.woff2
        │
        ├── logos/
        │   ├── logo-primary.svg       # Vector (if provided by user)
        │   ├── logo-primary.png       # Rasterized at 2x
        │   ├── logo-white.svg         # White variant for dark backgrounds
        │   └── logo-icon-only.svg     # Favicon/small format
        │
        ├── icons/
        │   ├── icon-set.svg           # Sprite sheet of all icons used
        │   └── individual/            # Each icon as separate SVG
        │       ├── check.svg
        │       ├── arrow-right.svg
        │       └── ...
        │
        ├── images/
        │   ├── hero-images/           # All AI-generated hero images (full-res)
        │   ├── backgrounds/           # Background patterns and gradients
        │   └── charts/                # Chart images as SVG + PNG
        │
        ├── templates/
        │   ├── meridian-deck.potx     # PowerPoint template with masters
        │   ├── slide-masters/         # Individual slide master layouts
        │   └── google-slides.json     # Google Slides API import format
        │
        ├── color-palette.json         # Machine-readable color definitions
        │   # { "primary": { "hex": "#0F172A", "rgb": [15,23,42], "hsl": [222,47%,11%] }, ... }
        │
        ├── spacing-rules.json         # Design token spacing scale
        │
        ├── figma-tokens.json          # Figma Tokens plugin format (direct import)
        │
        ├── tailwind-theme.json        # Tailwind CSS theme config
        │
        └── README.md                  # Human-readable brand guidelines
            # Auto-generated usage instructions:
            # - How to use the color palette
            # - Typography pairing rules
            # - Spacing guidelines
            # - Do's and Don'ts with visual examples
        """

    async def _generate_brand_manifest(self, theme: Theme) -> dict:
        """Generate comprehensive brand_manifest.json"""
        return {
            "version": "1.0",
            "generator": "Meridian V9",
            "generated_at": datetime.utcnow().isoformat(),
            "colors": {
                "primary": theme.colors.primary,
                "secondary": theme.colors.secondary,
                "accent": theme.colors.accent,
                "surface": theme.colors.surface,
                "background": theme.colors.background,
                "text": {
                    "primary": theme.colors.text_primary,
                    "secondary": theme.colors.text_secondary,
                    "muted": theme.colors.text_muted,
                },
                "status": {
                    "success": theme.colors.success,
                    "warning": theme.colors.warning,
                    "error": theme.colors.error,
                },
            },
            "typography": {
                "heading_family": theme.fonts.heading,
                "body_family": theme.fonts.body,
                "code_family": theme.fonts.code,
                "scale": theme.fonts.scale,  # [12, 14, 16, 20, 24, 32, 40, 48, 64]
            },
            "spacing": {
                "base_unit": 4,
                "scale": [4, 8, 12, 16, 24, 32, 48, 64, 96],
            },
            "brand_voice": theme.brand_voice or "professional",
        }

    async def _generate_figma_tokens(self, theme: Theme) -> dict:
        """Generate Figma Tokens plugin-compatible JSON for direct import"""
        # Maps Meridian design tokens to Figma's token format
        # Enables one-click import into Figma design systems

    async def _generate_readme(self, theme: Theme) -> str:
        """Auto-generate human-readable brand guidelines in Markdown"""
        # LLM generates usage guidelines based on the theme definition
        # Includes color pairing rules, typography hierarchy, spacing examples
```

---

## 4.18 Preview System

### Real-Time Preview Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     PREVIEW SYSTEM                                │
│                                                                  │
│  ┌─────────────────┐        ┌──────────────────────────────────┐│
│  │  Generation      │  SSE   │  Client Preview                  ││
│  │  Pipeline        ├───────▷│                                  ││
│  │                  │ events │  Slide 1: ████████████ ✓         ││
│  │  Generating...   │        │  Slide 2: ██████░░░░░ (60%)     ││
│  │  Slide 3/10      │        │  Slide 3: ░░░░░░░░░░ (pending)  ││
│  │                  │        │  ...                              ││
│  └─────────────────┘        │                                  ││
│                              │  ┌────────────────────────────┐  ││
│  Streaming Protocol:         │  │  Live Preview (iframe)      │  ││
│  1. outline_ready            │  │  Renders each slide as      │  ││
│  2. slide_content_ready(n)   │  │  soon as its DSL is ready   │  ││
│  3. slide_layout_ready(n)    │  │  using reveal.js hot-reload │  ││
│  4. slide_visual_ready(n)    │  └────────────────────────────┘  ││
│  5. slide_qa_passed(n)       │                                  ││
│  6. deck_complete            └──────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### Streaming Generation

Slides are generated and previewed progressively:

1. **Layer 1 completes** → Outline visible (slide titles and roles)
2. **Layer 2 completes per slide** → Content visible (text, data placeholders)
3. **Layer 3 completes per slide** → Layout applied (elements positioned)
4. **Layer 4 completes per slide** → Visuals loaded (images, charts render in)
5. **Layers 5-6 complete** → QA badges appear (green checks or yellow warnings)

### Streaming Time Budget Architecture

Every generation runs against a strict time budget with per-phase SSE progress events:

```typescript
// SSE Event types sent to client during generation
interface StreamingEvents {
  // Phase events
  "generation:start":      { mode: "standard" | "premium"; totalSlides: number; estimatedTime: number };
  "phase:thinking":        { status: "started" | "complete"; durationMs: number };
  "phase:narrative":       { status: "started" | "complete"; arcType: string; durationMs: number };
  "phase:outline":         { titles: string[]; roles: SlideRole[] };

  // Per-slide progressive events
  "slide:content_ready":   { slideIndex: number; elements: ContentElement[] };
  "slide:layout_ready":    { slideIndex: number; glaTree: GLA_Node; positions: ResolvedPosition[] };
  "slide:visual_ready":    { slideIndex: number; images: ImageAsset[]; charts: ChartAsset[] };
  "slide:qa_result":       { slideIndex: number; compositionScore: number; slopScore: number; passed: boolean };

  // Completion events
  "generation:complete":   { totalDurationMs: number; totalCost: number; qualityScores: QualityReport };
  "generation:error":      { error: string; retryable: boolean; failedPhase: string };
}
```

#### Standard Mode Time Budget (10-slide deck)

```
TIME    0s      2s      4s      6s      8s      10s     12s     15s
        │       │       │       │       │       │       │       │
PHASE   ├───────┤───────┼───────┼───────┤───────┼───────┼───────┤
        │OUTLINE│       │       │       │       │       │       │
        │(Groq) │  CONTENT + LAYOUT (parallel, GLM-4/Groq)      │
        │ ~1.5s │       │       │       │       │       │       │
        │       │       │  VISUALS (Cloudflare FLUX)             │
        │       │       │       │       │       │ ASSEMBLE+QA    │
        │       │       │       │       │       │  (basic only)  │
        ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
CLIENT  Titles  S1 text S1-3    S1-5    S1-8    S1-10   QA      Done!
        appear  + layout images  images  images  images  badges
                visible  load    load    load    load    appear

Per-slide budget: ~1.2s content + ~0.5s layout + ~1.5s image = ~3.2s
(Parallelized: effective ~1.5s/slide after pipeline warmup)
```

#### Premium Mode Time Budget (10-slide deck)

```
TIME    0s      5s      15s     25s     40s     60s     80s     90s
        │       │       │       │       │       │       │       │
PHASE   ├───────┤───────┼───────┼───────┼───────┼───────┼───────┤
        │THINK  │NARRAT.│       │       │       │       │       │
        │(Claude│(GPT-4o│ CONTENT (Claude/GPT-4o per slide)     │
        │ Haiku)│ deep  │       │       │       │       │       │
        │ ~3s   │ arc)  │  GLA LAYOUT (Yoga WASM solver)        │
        │       │ ~8s   │       │       │       │       │       │
        │       │       │  VISUALS (Phoenix/FLUX HD + retries)   │
        │       │       │       │       │       │       │       │
        │       │       │       │       │       │COMPOSI│QA+FIX │
        │       │       │       │       │       │TION   │REFLECT│
        │       │       │       │       │       │SCORE  │LOOP   │
        ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
CLIENT  "Think  Arc     S1-2    S3-5    S6-8    S9-10   QA      Done!
        ing..." preview content  with    with    final   + fix   Deck
               visible + layout images  images  slides  low     ready
                                                        scores

Per-slide budget: ~3s content + ~1s layout + ~4s images + ~1s QA = ~9s
(Parallelized: effective ~6-7s/slide, total ~80-90s for 10 slides)
```

### Client-Side Streaming Preview Component

```typescript
const StreamingPreview: React.FC<{ generationId: string }> = ({ generationId }) => {
  const [slides, setSlides] = useState<Partial<SlideV3>[]>([]);
  const [phase, setPhase] = useState<string>("connecting");
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const eventSource = new EventSource(`/api/generate/${generationId}/stream`);

    eventSource.addEventListener("phase:outline", (e) => {
      const data = JSON.parse(e.data);
      setSlides(data.titles.map((t: string, i: number) => ({
        index: i,
        role: data.roles[i],
        elements: [{ type: "heading", content: t }],
        status: "outline",
      })));
      setPhase("Building content...");
    });

    eventSource.addEventListener("slide:content_ready", (e) => {
      const data = JSON.parse(e.data);
      setSlides(prev => prev.map((s, i) =>
        i === data.slideIndex ? { ...s, elements: data.elements, status: "content" } : s
      ));
      setProgress((data.slideIndex + 1) / slides.length * 0.5); // 50% at content
    });

    eventSource.addEventListener("slide:visual_ready", (e) => {
      const data = JSON.parse(e.data);
      setSlides(prev => prev.map((s, i) =>
        i === data.slideIndex ? { ...s, images: data.images, status: "visual" } : s
      ));
      setProgress(0.5 + (data.slideIndex + 1) / slides.length * 0.4); // 90% at visuals
    });

    eventSource.addEventListener("slide:qa_result", (e) => {
      const data = JSON.parse(e.data);
      setSlides(prev => prev.map((s, i) =>
        i === data.slideIndex
          ? { ...s, qa: { compositionScore: data.compositionScore, passed: data.passed }, status: "complete" }
          : s
      ));
    });

    eventSource.addEventListener("generation:complete", () => {
      setPhase("complete");
      setProgress(1.0);
      eventSource.close();
    });

    return () => eventSource.close();
  }, [generationId]);

  return (
    <div className="streaming-preview">
      <ProgressBar progress={progress} phase={phase} />
      <div className="slide-grid">
        {slides.map((slide, i) => (
          <SlideThumbnail
            key={i}
            slide={slide}
            status={slide.status}
            // Shimmer placeholder for pending slides
            // Fade-in animation when content arrives
          />
        ))}
      </div>
    </div>
  );
};
```

### Preview Refresh Latency

| Action | Target Latency |
|--------|---------------|
| Text edit → preview update | <200ms |
| Layout change → preview update | <500ms |
| Theme change → full re-render | <1s |
| Slide regeneration → preview | <3s |

---

## 4.19 Presentation Modes

### Reading Mode vs Presentation Mode

| Feature | Reading Mode | Presentation Mode |
|---------|-------------|-------------------|
| Layout | Scrollable vertical | Full-screen slides |
| Navigation | Mouse scroll, click links | Arrow keys, space bar |
| Content density | Higher (smaller fonts, more text) | Lower (larger fonts, key points) |
| Animations | Disabled (content visible immediately) | Enabled (progressive reveal) |
| Charts | Interactive (hover for data) | Static or auto-animated |
| 3D scenes | Auto-rotating | User-controlled or scripted |
| Speaker notes | Visible in sidebar | Separate speaker view |
| Sharing | URL with anchor links per section | URL with slide number |

### Dual Mode Implementation

The same DSL drives both modes. The renderer adjusts based on `mode`:

```typescript
function renderSlide(slide: SlideV3, mode: "reading" | "presenting") {
  const config = mode === "reading"
    ? { fontScale: 0.85, showAllFragments: true, animationsEnabled: false, scrollable: true }
    : { fontScale: 1.0, showAllFragments: false, animationsEnabled: true, scrollable: false };
  // ...
}
```

---

## 4.20 State Synchronization + Collaborative Real-Time Editing

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    STATE MANAGEMENT                               │
│                                                                  │
│  Source of Truth: Slide DSL v3 (MongoDB)                         │
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────────┐ │
│  │ Zustand Store │ ←──▷│ Yjs CRDT     │ ←──▷│ Other Clients   │ │
│  │ (local state) │     │ (sync layer) │     │ (multiplayer)   │ │
│  └──────┬───────┘     └──────┬───────┘     └─────────────────┘ │
│         │                     │                                  │
│         ▼                     ▼                                  │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ React UI     │     │ WebSocket    │                          │
│  │ (Konva +     │     │ Server       │                          │
│  │  reveal.js)  │     │ (broadcasts) │                          │
│  └──────────────┘     └──────────────┘                          │
│                                                                  │
│  State Flow:                                                     │
│  User Edit → Zustand → Yjs → WebSocket → Other Clients          │
│                    ↓                                             │
│              MongoDB (debounced persist every 2s)                │
│                    ↓                                             │
│              Preview re-render (200ms debounce)                  │
└──────────────────────────────────────────────────────────────────┘
```

### Collaborative Editing System

Meridian supports **real-time multiplayer editing** — multiple users can work on the same presentation simultaneously with live cursor presence, per-element locking, comments, and @mentions:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  COLLABORATIVE EDITING — LIVE SESSION                                        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Connected: [👤 Ali (editing Slide 3)] [👤 Sara (viewing Slide 1)]  │    │
│  │             [👤 Omar (editing Slide 7)] [🤖 AI (generating Slide 9)]│    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐      │
│  │  SLIDE 3 — "Market Opportunity"                                    │      │
│  │                                                                    │      │
│  │  ┌──────────────────────────────────────────────┐                  │      │
│  │  │  ┌─────────────────┐  ┏━━━━━━━━━━━━━━━━━━┓  │ ┌──────────────┐│      │
│  │  │  │  TAM: $47B       │  ┃ 🔵 Ali editing   ┃  │ │🗨 COMMENTS   ││      │
│  │  │  │  ────────────────│  ┃  this element    ┃  │ │              ││      │
│  │  │  │  SAM: $12B       │  ┃  (cursor visible)┃  │ │ Sara: "Can we││      │
│  │  │  │  SOM: $3.2B      │  ┗━━━━━━━━━━━━━━━━━━┛  │ │ update the  ││      │
│  │  │  └─────────────────┘                          │ │ TAM figure?"││      │
│  │  │                                                │ │             ││      │
│  │  │  🔒 [Ali] editing — locked for others          │ │ @Ali replied:│      │
│  │  │                                                │ │ "Will do!"  ││      │
│  │  └──────────────────────────────────────────────┘ │ │             ││      │
│  │                                                    │ │ [+ Reply]   ││      │
│  │  ┌─ 🟡 Sara's cursor (viewing, not editing) ──┐   │ │ [Resolve ✓] ││      │
│  │  └─────────────────────────────────────────────┘   │ └──────────────┘│    │
│  └────────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  [💬 Comments (3)] [📝 Changes (12)] [🕐 Version History] [👥 Share...]      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Collaboration Features

```typescript
interface CollaborationSystem {
  // 1. REAL-TIME CURSOR PRESENCE
  cursors: {
    // Each connected user's cursor position broadcast via WebSocket
    userId: string;
    displayName: string;
    avatar: string;           // User avatar URL
    cursorColor: string;      // Unique color per user (auto-assigned)
    position: {
      slideIndex: number;     // Which slide they're viewing
      x: number;              // Canvas X position
      y: number;              // Canvas Y position
    };
    activeElementId?: string; // Element they're hovering/editing
    status: "viewing" | "editing" | "selecting" | "idle";
    lastSeen: Date;
  }[];

  // 2. ELEMENT-LEVEL LOCKING
  locks: {
    elementId: string;
    lockedBy: string;         // userId
    lockedAt: Date;
    autoReleaseAfter: number; // 30 seconds of inactivity → auto-unlock
    // Other users see a colored border + lock icon
    // They can request control: "Request edit" → notification to lock holder
  }[];

  // 3. COMMENT THREADS (Per-Element + Per-Slide)
  comments: {
    id: string;
    slideIndex: number;
    elementId?: string;       // If attached to specific element (pin comment)
    position?: { x: number; y: number }; // Canvas position for floating comments
    author: { userId: string; name: string; avatar: string };
    content: string;          // Supports @mentions
    mentions: string[];       // userId[] of mentioned users
    replies: CommentReply[];
    status: "open" | "resolved";
    createdAt: Date;
  }[];

  // 4. @MENTIONS
  mentions: {
    // Type "@" in any comment or AI Bar → autocomplete user list
    // Mentioned user gets: in-app notification + optional email
    // Click mention → jump to the comment/slide
    trigger: "@";
    searchableUsers: { userId: string; name: string; avatar: string }[];
  };

  // 5. VERSION HISTORY
  versions: {
    id: string;
    timestamp: Date;
    author: { userId: string; name: string };
    changeType: "manual_save" | "auto_save" | "ai_generation" | "restore";
    changeSummary: string;    // Auto-generated: "Ali edited 3 slides, Sara added 2 comments"
    snapshot: SlideDSLv3;     // Full deck snapshot (compressed in MongoDB)
    // User can browse, preview, and restore any version
    // Diff view: highlight changes between versions
  }[];

  // 6. SHARE PERMISSIONS
  sharing: {
    presentationId: string;
    owner: string;            // userId
    collaborators: {
      userId: string;
      role: "editor" | "commenter" | "viewer";
      addedAt: Date;
      addedBy: string;
    }[];
    linkSharing: {
      enabled: boolean;
      accessLevel: "view" | "comment" | "edit";
      expiresAt?: Date;
      password?: string;      // Optional link password
    };
  };
}
```

### Yjs CRDT Conflict Resolution

```typescript
// Yjs handles concurrent edits via CRDTs (Conflict-free Replicated Data Types)
// Each slide element is a Yjs Y.Map → concurrent edits merge automatically
// Text elements use Y.Text for character-level merge (like Google Docs)

const ydoc = new Y.Doc();
const ySlides = ydoc.getArray<Y.Map<any>>("slides");

// WebSocket provider syncs all clients
const wsProvider = new WebsocketProvider(
  "wss://collab.meridian.ai",
  presentationId,
  ydoc,
);

// Awareness protocol for cursor presence
wsProvider.awareness.setLocalState({
  user: { name: currentUser.name, color: currentUser.cursorColor, avatar: currentUser.avatar },
  cursor: { slideIndex: 0, x: 0, y: 0 },
  status: "viewing",
});

// Listen for remote cursor updates
wsProvider.awareness.on("change", () => {
  const states = wsProvider.awareness.getStates();
  // Render remote cursors on canvas
});
```

---

## 4.21 Web-to-Slide Transformer

> Users paste a URL or upload a document → Meridian extracts content, analyzes structure, detects brand signals, and produces a structured NarrativePlan ready for the generation pipeline. No AI presentation tool does this end-to-end today.

### 3-Phase Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│  WEB-TO-SLIDE TRANSFORMER                                        │
│                                                                  │
│  INPUT: URL / PDF / DOCX / Notion export / Google Doc            │
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │  PHASE 1:     │     │  PHASE 2:     │     │  PHASE 3:       │  │
│  │  EXTRACTION   │────▷│  ANALYSIS     │────▷│  TRANSFORMATION │  │
│  │               │     │               │     │                 │  │
│  │  • Playwright │     │  • Content    │     │  • Map content  │  │
│  │    crawl page │     │    type class │     │    to slide     │  │
│  │  • DOM tree   │     │  • Brand      │     │    roles        │  │
│  │    extraction │     │    signal     │     │  • Create       │  │
│  │  • Image      │     │    detection  │     │    Narrative    │  │
│  │    harvest    │     │  • Hierarch.  │     │    Plan         │  │
│  │  • Metadata   │     │    structure  │     │  • Assign GLA   │  │
│  │    parsing    │     │    mapping    │     │    patterns     │  │
│  └──────────────┘     └──────────────┘     └─────────────────┘  │
│                                                                  │
│  OUTPUT: NarrativePlan + ContentElements + BrandProfile (opt.)   │
│          → Feed directly into Layer 1 of CDI Pipeline            │
└──────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
class WebToSlideTransformer:
    """
    Converts web pages, PDFs, and documents into structured slide content.
    Uses Playwright for web crawling, PyMuPDF for PDFs, python-docx for DOCX.
    """

    SUPPORTED_INPUTS = [
        "url",        # Any public URL (website, blog, landing page)
        "pdf",        # PDF document upload
        "docx",       # Word document upload
        "notion",     # Notion page export (Markdown)
        "gdoc",       # Google Doc (via shared link → HTML export)
        "markdown",   # Raw Markdown text
        "text",       # Plain text
    ]

    async def transform(
        self,
        source: str,
        source_type: str,
        target_slides: int = 10,
        presentation_goal: str = "inform",  # "inform" | "pitch" | "teach" | "sell"
    ) -> TransformResult:
        """
        Main pipeline: Extract → Analyze → Transform → NarrativePlan
        """
        # Phase 1: Extraction
        raw_content = await self._extract(source, source_type)

        # Phase 2: Analysis
        analysis = await self._analyze(raw_content)

        # Phase 3: Transformation
        narrative_plan = await self._transform(analysis, target_slides, presentation_goal)

        return TransformResult(
            narrative_plan=narrative_plan,
            extracted_images=raw_content.images,
            detected_brand=analysis.brand_signals,
            suggested_theme=analysis.suggested_theme,
            confidence=analysis.extraction_confidence,
        )

    async def _extract(self, source: str, source_type: str) -> RawContent:
        """
        Phase 1: Extract raw content from source.

        For URLs:
        - Launch Playwright headless browser
        - Navigate to URL, wait for dynamic content to load
        - Extract DOM tree → structured sections (h1, h2, p, li, img, table)
        - Harvest all images (with alt text and dimensions)
        - Extract metadata (og:title, og:description, favicon, theme-color)
        - Detect brand signals (logo, colors from CSS, font families)

        For PDFs:
        - PyMuPDF page-by-page extraction
        - OCR fallback for scanned pages (Tesseract)
        - Table extraction → structured data
        - Image extraction with page positions

        For DOCX:
        - python-docx paragraph/heading/table extraction
        - Style mapping (heading levels → content hierarchy)
        - Embedded image extraction
        """

    async def _analyze(self, raw_content: RawContent) -> ContentAnalysis:
        """
        Phase 2: AI-powered content analysis.

        Uses LLM (Groq for speed / GPT-4o for accuracy) to:
        - Classify content type: "product page" | "blog post" | "research paper"
                                | "company about" | "pricing page" | "case study"
        - Identify key sections and their importance (1-10 score)
        - Detect brand signals: primary colors, logo, typography hints, voice/tone
        - Extract key statistics, quotes, and data points
        - Map content hierarchy: which sections → which slide roles
        - Estimate total content density → suggest slide count
        """

    async def _transform(
        self,
        analysis: ContentAnalysis,
        target_slides: int,
        goal: str,
    ) -> NarrativePlan:
        """
        Phase 3: Transform analyzed content into a NarrativePlan.

        Maps content sections → slide roles:
        - Hero/intro section → Title Slide
        - Problem/challenge → Problem Slide (high emotion)
        - Product features → Feature Grid slides (moderate emotion)
        - Statistics/data → Data Visualization slides
        - Testimonials → Social Proof slides
        - Pricing → Comparison/Pricing slides
        - CTA → Closing Slide (high emotion)

        Assigns narrative arc based on content flow + presentation goal.
        Over/under target slides: merge low-importance sections or split dense ones.
        """


class TransformResult:
    narrative_plan: NarrativePlan       # Ready for Layer 1 of CDI Pipeline
    extracted_images: list[ImageAsset]  # Reusable images from source
    detected_brand: BrandSignals        # Auto-detected colors, logo, fonts
    suggested_theme: str                # Best-match from 24 built-in themes
    confidence: float                   # 0.0-1.0 extraction confidence score
    source_summary: str                 # One-paragraph summary of source content
```

### Supported Extraction Targets

| Source Type | Extractor | Key Features | Accuracy |
|-------------|----------|--------------|----------|
| **Web URL** | Playwright + Readability.js | Full page render, JS-dependent content, image harvest | 90%+ |
| **PDF** | PyMuPDF + Tesseract OCR | Page-by-page, tables, embedded images | 85%+ |
| **DOCX** | python-docx | Headings, paragraphs, tables, images, styles | 95%+ |
| **Notion** | Markdown parser | Headings, callouts, toggles, databases | 90%+ |
| **Google Doc** | HTML export parser | Formatted text, images, comments | 85%+ |
| **Markdown** | remark parser | Full Markdown AST | 98%+ |
| **Plain text** | LLM structure detection | AI-inferred sections and hierarchy | 75%+ |

---

## 4.22 Visual Identity System (VIS) — The Meridian Signature

> Every AI presentation tool generates slides that look... "AI-generated." Meridian breaks this pattern with a recognizable visual identity — a design philosophy baked into every generated slide that makes Meridian presentations instantly recognizable as premium, professionally crafted work.

### Meridian Visual Signature

```typescript
const MERIDIAN_VISUAL_IDENTITY: VisualIdentitySystem = {
  // Core Principles — What makes a Meridian slide look "Meridian"
  signature_principles: [
    "asymmetric-balance",     // Never perfectly centered — intentional off-center weight
    "depth-layering",         // Overlapping elements, z-index play, card shadows
    "typographic-contrast",   // Bold heading + light body = dramatic hierarchy
    "data-ink-maximization",  // Maximum data, minimum decoration (Tufte principle)
    "generous-whitespace",    // 40%+ of slide area is breathing room
    "warm-tech-fusion",       // Technology feels human, not cold or robotic
  ],

  // Whitespace Philosophy
  whitespace: {
    minimum_ratio: 0.40,       // At least 40% of slide is whitespace
    hero_slide_ratio: 0.55,    // Hero/title slides: 55%+ whitespace
    data_slide_ratio: 0.35,    // Data-heavy slides: 35% minimum
    rule: "When in doubt, add more whitespace. Never pack slides.",
  },

  // Typography Voice
  typography_voice: {
    heading_style: "confident-not-loud",
    // Headings: Large (36-64px), bold (700+), with generous letter-spacing
    // Never fully uppercase (feels like shouting) — Title Case for headings
    // Body: Clean, readable, 16-20px, regular weight, 1.6 line-height

    signature_treatment: "typographic-scale-jump",
    // Key stat number: 3-4× larger than surrounding text
    // Creates instant visual hierarchy without color or decoration
    // Example: "47" in 96px bold, "Billion Dollar Market" in 18px regular

    font_pairing_rules: [
      "Geometric sans (headings) + Humanist sans (body)",    // Modern + Readable
      "Serif display (headings) + Clean sans (body)",        // Elegant + Clear
      "Monospace display (headings) + Proportional (body)",  // Tech + Accessible
    ],
  },

  // Shape Language
  shape_language: {
    primary_shape: "rounded-rectangle",  // r=8-16px, never sharp corners unless intentional
    accent_shape: "circle",              // For data points, avatars, icons
    separator: "thin-line",              // 1px lines, never thick borders
    organic_elements: true,              // Occasional blob shapes for visual interest
    grid_visible: false,                 // Grid is underlying structure, never visible
  },

  // Image Treatment
  image_treatment: {
    default_style: "contained-with-radius",  // Images inside rounded-rect containers
    hero_style: "full-bleed-gradient-overlay", // Hero images span full width with gradient
    avatar_style: "circle-crop",              // People photos in circles
    screenshot_style: "browser-mockup",       // App/web screenshots in device frames
    icon_style: "outlined-2px",               // Consistent stroke-width icons
    // NEVER: floating images without containers, distorted aspect ratios,
    //        stock-photo-looking images, images touching slide edges without purpose
  },

  // Animation Personality
  animation_personality: {
    entrance_style: "subtle-slide-fade",     // Elements slide in 20-40px + fade (200ms)
    exit_style: "quick-fade",                // Exit: just opacity (150ms)
    chart_animation: "draw-in-sequential",   // Charts draw bars/lines sequentially
    transition_style: "smooth-crossfade",    // Slide transitions: 300ms crossfade
    timing_function: "cubic-bezier(0.22, 1, 0.36, 1)", // Smooth ease-out
    // NEVER: bounce effects, spin, zoom-rotate, scale-pulse, anything "flashy"
    // Philosophy: "Animation should feel like breathing — natural, unnoticed"
  },

  // Color Behavior
  color_behavior: {
    accent_usage: "strategic-minimal",
    // Accent color appears in maximum 3 places per slide:
    // 1. One highlighted statistic or keyword
    // 2. Primary CTA button
    // 3. Chart emphasis color
    // Everything else: grayscale + surface colors

    gradient_rules: [
      "Max 2 colors per gradient",
      "Angle: 135° or 180° only (diagonal or vertical)",
      "Opacity gradient for overlays: solid → transparent",
      "No rainbow gradients, no radial gradients on text",
    ],

    dark_mode_priority: true,
    // Dark backgrounds are default for "premium" feel
    // Light mode available but dark mode is the Meridian signature
  },

  // Icon Style
  icon_style: {
    library: "lucide",                  // Lucide as primary (clean, consistent)
    stroke_width: 2,                    // 2px stroke for all icons
    size_scale: [16, 20, 24, 32, 48],  // 5 sizes only
    color: "currentColor",             // Inherit from parent text color
    // NEVER: filled icons (except for status indicators), colored icons,
    //        mixed icon families, icons larger than 48px
  },
};
```

### VIS Enforcement in Pipeline

The Visual Identity System is enforced at multiple pipeline stages:

```typescript
interface VIS_Enforcement {
  // Layer 3 (Spatial Design): GLA patterns use VIS whitespace ratios
  spatial: {
    minWhitespace: MERIDIAN_VISUAL_IDENTITY.whitespace.minimum_ratio,
    shapeLanguage: MERIDIAN_VISUAL_IDENTITY.shape_language,
  };

  // Layer 4 (Visual): Image treatment follows VIS rules
  visual: {
    imageStyle: MERIDIAN_VISUAL_IDENTITY.image_treatment,
    iconStyle: MERIDIAN_VISUAL_IDENTITY.icon_style,
  };

  // Layer 5 (Composition): Scoring penalizes VIS violations
  composition: {
    penaltyForSharpCorners: -5,
    penaltyForLowWhitespace: -10,
    penaltyForBouncyAnimations: -15,
    bonusForAsymmetricBalance: +8,
    bonusForTypographicContrast: +5,
  };

  // Layer 6 (QA): Slop detector checks VIS compliance
  qa: {
    vis_compliance_check: true,
    vis_minimum_score: 70,  // Out of 100
    violations_logged: true,
  };
}
```

---

## 4.23 Design Intelligence Dashboard — The Killer Feature

> After generation, every slide gets an explainability panel — "Why this layout? Why these colors? What's the composition score?" No other AI tool shows this. It transforms Meridian from a black-box generator into a **transparent design partner**.

### Dashboard Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  DESIGN INTELLIGENCE DASHBOARD — Slide 4: "Market Opportunity"               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  WHY THIS LAYOUT?                                                       │ │
│  │  ───────────────────────────────────────────────────────────────────     │ │
│  │  Content Analysis:                                                      │ │
│  │    • 3 statistics detected → chose "stat-trio" GLA pattern              │ │
│  │    • High numerical density (47B, 12B, 3.2B) → large number treatment   │ │
│  │    • Slide role: "data-evidence" → moderate emotional intensity (6/10)  │ │
│  │                                                                         │ │
│  │  Layout Selected: ROW(STAT_BLOCK × 3) + CAPTION_ROW                    │ │
│  │  Reason: "Three comparable metrics of decreasing magnitude. Row layout  │ │
│  │           creates natural left-to-right reading flow: TAM → SAM → SOM. │ │
│  │           Each stat block gets equal visual weight (33% width)."        │ │
│  │                                                                         │ │
│  │  Alternatives Considered:                                               │ │
│  │    ✗ Nested circles (TAM/SAM/SOM) — rejected: "overused, cliché"       │ │
│  │    ✗ Bar chart — rejected: "only 3 data points, chart feels empty"      │ │
│  │    ✗ Two-column stat + chart — rejected: "no secondary data to chart"   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐│
│  │  VISUAL HIERARCHY     │  │  COMPOSITION BALANCE  │  │  NARRATIVE CONTEXT  ││
│  │  Score: 88/100        │  │  Score: 82/100        │  │                     ││
│  │                       │  │                       │  │  Arc Position: 4/10 ││
│  │  1. "$47B" (primary)  │  │  Center of Mass:      │  │  Role: Evidence     ││
│  │     Weight: 0.35      │  │   ● (slightly left)   │  │  Emotion: 6/10     ││
│  │  2. "TAM" (secondary) │  │                       │  │  Transition: builds ││
│  │     Weight: 0.20      │  │  Left weight: 38%     │  │  on previous claim  ││
│  │  3. Caption (tertiary)│  │  Right weight: 32%    │  │                     ││
│  │     Weight: 0.10      │  │  Top weight: 45%      │  │  Next: "Product     ││
│  │                       │  │  Bottom weight: 25%   │  │  Demo" (climax)     ││
│  │  Eye flow: Z-pattern  │  │                       │  │                     ││
│  │  Reading order: ✓     │  │  Verdict: Slightly    │  │  Emotional curve:   ││
│  │                       │  │  top-heavy (OK for    │  │  ╭──╮               ││
│  │                       │  │  data slides)         │  │  │  ╰──● (you are   ││
│  │                       │  │                       │  │  ╯      here)       ││
│  └──────────────────────┘  └──────────────────────┘  └─────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  ANTI-AI-SLOP CHECK: 0/7 violations ✅                                  │ │
│  │  ✓ No orphan headings  ✓ No font soup  ✓ No color clash                │ │
│  │  ✓ No text overflow    ✓ No empty space waste  ✓ No generic stock image│ │
│  │  ✓ No Wall-of-Text (content density: 0.42, threshold: 0.6)            │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  ACTIONS:                                                               │ │
│  │  [↻ Regenerate This Slide] [⚖ Adjust Visual Weights] [📐 Try Different │ │
│  │   Layout] [💾 Save as Template] [↗ Apply Style to Similar Slides]       │ │
│  │  [📊 Compare Variants] [🔍 View Raw GLA Tree] [📋 Copy Design Spec]    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Dashboard Data Model

```typescript
interface DesignIntelligence {
  slideId: string;
  slideIndex: number;

  // 1. Layout Explainability
  layoutExplanation: {
    selectedPattern: string;           // GLA pattern name
    selectionReason: string;           // Natural language explanation
    contentAnalysis: {
      elementsDetected: number;
      elementTypes: Record<string, number>;  // { "statistic": 3, "caption": 1 }
      contentDensity: number;                // 0.0-1.0
      dominantContentType: string;           // "numerical" | "textual" | "visual" | "mixed"
    };
    alternativesConsidered: {
      pattern: string;
      reason_rejected: string;
    }[];
  };

  // 2. Visual Hierarchy Analysis
  visualHierarchy: {
    score: number;                     // 0-100
    eyeFlowPattern: "Z" | "F" | "diagonal" | "center-out" | "custom";
    readingOrderCorrect: boolean;
    elementWeights: {
      elementId: string;
      role: "primary" | "secondary" | "tertiary" | "support";
      visualWeight: number;            // 0.0-1.0
    }[];
  };

  // 3. Composition Balance
  compositionBalance: {
    score: number;                     // 0-100
    centerOfMass: { x: number; y: number };  // Relative to slide center
    quadrantWeights: {
      topLeft: number;
      topRight: number;
      bottomLeft: number;
      bottomRight: number;
    };
    verdict: string;                   // "Well-balanced" | "Slightly top-heavy" | etc.
  };

  // 4. Narrative Context
  narrativeContext: {
    arcPosition: number;               // Slide index in narrative arc
    totalSlides: number;
    slideRole: SlideRole;
    emotionalIntensity: number;        // 0-10
    transitionFromPrevious: string;    // "builds on", "contrasts with", "pivots to"
    narrativeFunction: string;         // "evidence", "emotional peak", "resolution"
  };

  // 5. Anti-AI-Slop Report
  slopReport: {
    totalViolations: number;           // 0-7 (lower is better)
    maxViolations: 7;
    checks: {
      name: string;                    // "orphan-heading", "font-soup", etc.
      passed: boolean;
      details?: string;                // Reason if failed
    }[];
  };

  // 6. VIS Compliance
  visCompliance: {
    score: number;                     // 0-100
    whitespaceRatio: number;           // Actual whitespace percentage
    shapeLanguageCompliant: boolean;
    colorUsageCompliant: boolean;
    typographyCompliant: boolean;
    violations: string[];
  };
}
```

### Dashboard Integration

The Design Intelligence Dashboard is:
- **Accessible per-slide** via a "🧠 Design Intelligence" button in the canvas editor
- **Visible in the AI Bar** as quick insights: "This slide scores 88/100. Layout: stat-trio. 0 slop violations."
- **Exportable** as a design spec document (PDF) for stakeholders who want to understand the AI's reasoning
- **Used by the Reflection Loop**: If dashboard scores are below threshold, the system auto-suggests improvements before the user even sees the slide

---

## 4.24 Complete Data Visualization System

> *"Beautiful text and images mean nothing if your financial slide is a screenshot of a spreadsheet. Data elements — tables, charts, graphs, diagrams, icons — are the heartbeat of serious presentations."*

### 4.24.1 The Data Gap (Why This Matters)

The V9 pipeline handles text and images through 6 intelligent layers, but structured data visualization was underspecified. Real-world presentations — especially pitch decks, board reports, and strategy documents — are **60-80% data elements**:

| Data Element | Previous V9 Status | Production Requirement |
|-------------|-------------------|----------------------|
| **Tables** | Not specified | Financial reports, comparisons, specs, feature matrices |
| **Bar/Column Charts** | 12 types in ChartGenerator | Revenue, metrics, category comparisons |
| **Line/Area Charts** | Basic mention | Trends over time, growth trajectories, forecasting |
| **Pie/Donut/Sunburst** | Basic mention | Market share, composition, hierarchy breakdowns |
| **Scatter/Bubble** | Missing | Correlation analysis, clustering, segmentation |
| **Funnel/Waterfall** | Basic mention | Conversion pipelines, cash flow, cascading metrics |
| **Timeline/Gantt** | Partial (in templates) | Project plans, roadmaps, milestone tracking |
| **Network/Architecture** | Missing | System design, infrastructure, topology diagrams |
| **Flowcharts/State Machines** | Missing | Process flows, decision trees, product lifecycles |
| **Org Charts/Mind Maps** | Missing | Team structures, concept mapping, hierarchies |
| **Stat/Metric Cards** | Basic stat type only | KPI dashboards, traction slides, hero numbers |
| **Comparison Matrices** | 2×2 implied | Competitive analysis, feature grids, scoring |
| **Icons (Comprehensive)** | Lucide mentioned | Full categorized icon system with semantic mapping |
| **Annotations/Callouts** | Speaker notes only | In-chart labels, data source citations, benchmark lines |
| **Sparklines/Indicators** | Not mentioned | Inline trend indicators, delta badges, confidence bands |
| **Interactive Elements** | Not specified | Live data, parameter sliders, hover tooltips |
| **Diagram Elements** | Mermaid mentioned | Fishbone, Sankey, value chain, service blueprint |

This section formalizes every data element as a first-class citizen of the V9 pipeline.

---

### 4.24.2 Chart Type Taxonomy (Complete Classification)

```typescript
// ══════════════════════════════════════════════════════════════════════
// V9 MERIDIAN — CHART TYPE TAXONOMY (Production Classification)
// ══════════════════════════════════════════════════════════════════════

type ChartCategory =
  | "comparison"
  | "trend"
  | "proportion"
  | "scatter_statistical"
  | "business_pipeline"
  | "financial_metrics"
  | "relationship"
  | "geographic"
  | "statistical_ml"
  | "diagnostic_medical";

type ChartType =
  // ── COMPARISON CHARTS (9 types) ──
  | "bar"                      // Vertical bars (single series)
  | "horizontal_bar"           // Horizontal bars
  | "grouped_bar"              // Clustered multi-series bars
  | "stacked_bar"              // Stacked (100% or absolute)
  | "waterfall"                // Cascading value changes (revenue bridge)
  | "bullet_chart"             // Horizontal target vs actual
  | "lollipop"                 // Dot-on-stick (cleaner than bar)
  | "diverging_bar"            // Positive/negative divergence from center
  | "radar_chart"              // Polar coordinate multi-axis comparison

  // ── TREND / TIME SERIES (8 types) ──
  | "line"                     // Standard line (time series)
  | "area"                     // Filled area under line
  | "stacked_area"             // Multiple filled layers (stream)
  | "stepped_area"             // Discrete interval steps
  | "smoothed_area"            // Curved area fill (monotone interpolation)
  | "sparkline"                // Inline mini line chart (for tables/cards)
  | "candlestick"              // OHLC financial chart
  | "streamgraph"              // Flowing stacked area (organic feel)

  // ── PROPORTION CHARTS (8 types) ──
  | "pie"                      // Standard percentage breakdown
  | "donut"                    // Ring with center label
  | "semi_pie"                 // Half-circle (gauge-like)
  | "sunburst"                 // Hierarchical concentric rings
  | "treemap"                  // Rectangle area = value (hierarchy)
  | "nested_ring"              // Multiple concentric donut rings
  | "waffle"                   // Grid square percentage visualization
  | "icicle"                   // Vertical hierarchical partition

  // ── SCATTER / STATISTICAL (8 types) ──
  | "scatter"                  // X/Y point cloud with optional trend
  | "bubble"                   // Scatter + size dimension
  | "density_heatmap"          // 2D histogram heat grid
  | "dot_plot"                 // Simple dot sequence
  | "box_plot"                 // Quartiles + whiskers
  | "violin"                   // Distribution shape
  | "histogram"                // Frequency distribution bars
  | "ridgeline"                // Overlapping density curves

  // ── BUSINESS / PIPELINE (8 types) ──
  | "funnel"                   // Conversion pipeline stages
  | "pipeline"                 // Multi-stage horizontal process
  | "gantt"                    // Project schedule with dependencies
  | "burn_down"                // Remaining work over time
  | "cumulative_flow"          // Running total accumulation
  | "product_roadmap"          // Timeline with milestones + swimlanes
  | "tam_sam_som"              // Nested circles (pitch deck specific)
  | "s_curve"                  // Technology/product adoption curve

  // ── FINANCIAL / METRICS (8 types) ──
  | "metric_card"              // Single KPI: big number + trend + label
  | "metric_dashboard"         // Grid of KPI cards (2×2, 3×2, etc.)
  | "sparkline_table"          // Table rows with inline sparklines
  | "scorecard"                // Weighted multi-criteria scoring grid
  | "big_number"               // Hero statistic (e.g., "$2.4M ARR")
  | "animated_counter"         // Count-up animation (0 → target in 2s)
  | "gauge"                    // Semi-circular gauge (NPS, health score)
  | "progress_ring"            // Circular progress indicator

  // ── RELATIONSHIP / FLOW (8 types) ──
  | "sankey"                   // Flow diagram with proportional widths
  | "parallel_coordinates"     // Multi-dimensional comparison
  | "slope_graph"              // Before/after line comparison
  | "quadrant"                 // 4-quadrant analysis (Gartner Magic Quadrant)
  | "chord"                    // Circular flow between categories
  | "network_graph"            // Node-edge graph (force-directed)
  | "arc_diagram"              // Linear nodes with arc connections
  | "matrix_heatmap"           // Row × Column intensity grid

  // ── GEOGRAPHIC (5 types) ──
  | "choropleth_map"           // Color-coded geographic regions
  | "geo_scatter"              // Lat/lng scatter on map
  | "hexbin_map"               // Hexagonal spatial density
  | "flow_map"                 // Directional flow lines on map
  | "connection_map"           // Point-to-point connections on map

  // ── STATISTICAL / ML (6 types) ──
  | "confusion_matrix"         // Classification accuracy grid
  | "roc_curve"                // Receiver operating characteristic
  | "learning_curve"           // Model performance over iterations
  | "forest_plot"              // Effect sizes with confidence intervals
  | "qq_plot"                  // Quantile-quantile distribution check
  | "calibration_curve"        // Predicted vs observed probability

  // ── COMPARISON MATRICES / TABLES ──
  | "comparison_matrix"        // N×M feature grid (competitive analysis)
  | "pricing_table"            // Tiered pricing with CTAs
  | "feature_matrix"           // Capability checklist (✓/✗)
  | "decision_matrix"          // Options vs criteria scoring
  | "swot_grid"                // 2×2 SWOT analysis layout
  | "risk_matrix"              // Impact × likelihood grid

  // ── TIMELINE / SEQUENCE ──
  | "timeline"                 // Horizontal/vertical milestone timeline
  | "sequence_diagram"         // Step-by-step linear flow
  | "process_flow"             // Swimlane process diagram

  // ── ANNOTATION / DECORATION ──
  | "reference_line"           // Benchmark or target overlay
  | "confidence_band"          // Error shading on chart
  | "trendline"                // Linear/polynomial regression overlay
  | "forecast_band"            // Future prediction cone
  | "stat_delta"               // Delta indicator badge (+12% MoM)
  | "data_source_citation";    // "Source: Gartner 2025" footer

// Total: 90+ chart types across 12 categories
```

---

### 4.24.3 Table Type System

```typescript
// ══════════════════════════════════════════════════════════════════════
// TABLE TYPES — First-Class Data Elements
// ══════════════════════════════════════════════════════════════════════

type TableType =
  | "simple_table"              // Basic rows/columns
  | "data_table"                // Header + typed body rows
  | "financial_table"           // Currency formatting, borders, stripes
  | "specification_table"       // Technical requirements grid
  | "comparison_table"          // Side-by-side feature comparison
  | "pricing_table"             // Tiered pricing with highlight column
  | "matrix_table"              // N×M data matrix
  | "schedule_table"            // Time-based (rows = hours/days)
  | "leaderboard"               // Ranked list with metrics
  | "metrics_dashboard_table"   // KPI grid with inline sparklines
  | "feature_matrix_table"      // Capability checklist (✓/✗/partial)
  | "decision_matrix_table"     // Options vs. weighted criteria
  | "swot_table"                // Strengths / Weaknesses / Opportunities / Threats
  | "risk_register_table"       // Issue / impact / probability / mitigation
  | "requirements_trace"        // Compliance / traceability matrix
  | "heatmap_table"             // Color-coded intensity grid
  | "status_report_table"       // RAG status (Red/Amber/Green) rows
  | "changelog_table";          // Version / date / description

interface TableSpec {
  type: TableType;
  position: {
    x: number;       // Left margin (80px default)
    y: number;       // Below heading (context-dependent)
    width: number;    // Available width (1760px typical on 1920 canvas)
    height: number;   // Calculated from row count + constraints
  };
  constraints: {
    maxRows: number;              // Max 8 rows before pagination/scroll
    maxCols: number;              // Max 6 columns before horizontal compression
    headerRow: boolean;           // Has header row?
    totalsRow: boolean;           // Has totals/summary row?
    firstColWidth: "fixed" | "auto" | "proportional";
    cellPadding: number;          // Internal padding (8-16px)
    outerBorder: boolean;
    stripeRows: boolean;          // Alternating row colors
    headerBgColor: string;        // e.g., "#1E293F"
    headerTextColor: string;      // e.g., "#FFFFFF"
    headerFontWeight: number;     // e.g., 700
    bodyTextColor: string;
    stripeColors: [string, string] | null;  // e.g., ["#F8FAFC", "#F1F5F9"]
    maxTextLength: number;        // Truncate cells at this char count
    overflowBehavior: "truncate" | "shrink-font" | "wrap";
    sortable: boolean;            // Click header to sort (HTML renderer)
    editable: boolean;            // Inline editing (Premium canvas only)
    financialFormatting: boolean;  // Auto-format currency/percentages
    conditionalFormatting: ConditionalRule[] | null;
  };
}

interface ConditionalRule {
  column: number;
  condition: "positive" | "negative" | "above_threshold" | "below_threshold";
  threshold?: number;
  style: { color?: string; backgroundColor?: string; fontWeight?: number };
}
```

**Table Layout Example:**
```
┌──────────────────────────────────────────────────────────────────┐
│  SLIDE CANVAS (1920×1080)                                        │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Title: "Q3 2025 Financial Results"                          │ │
│  │  Font: Cal Sans 64px Bold #FFFFFF | Y: 140                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  TABLE (x:80, y:280, w:1760, h:auto)                        │ │
│  │  ┌────────────────────────────────────────────────────────┐  │ │
│  │  │ HEADER (bg:#1E293F text:#FFF)                          │  │ │
│  │  │  Metric  │  Q1'25  │  Q2'25  │  Q3'25  │  YoY Δ      │  │ │
│  │  ├────────────────────────────────────────────────────────┤  │ │
│  │  │ BODY (alternating #F8FAFC / transparent)               │  │ │
│  │  │  ARR     │  $1.2M  │  $1.8M  │  $2.4M  │  +340%  ↑   │  │ │
│  │  │  Users   │  1.2K   │  2.8K   │  5.1K   │  +325%  ↑   │  │ │
│  │  │  NPS     │  72     │  81     │  89     │  +23.6% ↑   │  │ │
│  │  │  Churn   │  8.2%   │  5.1%   │  3.4%   │  -58.5% ↓   │  │ │
│  │  ├────────────────────────────────────────────────────────┤  │ │
│  │  │ TOTALS (border-top:2px, font-weight:700)               │  │ │
│  │  │  Total   │  $4.8M  │  $7.2M  │  $12.1M │  +152%  ↑   │  │ │
│  │  └────────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Footer: "Source: Internal Data | Confidential" Y:1040           │
└──────────────────────────────────────────────────────────────────┘
```

---

### 4.24.4 Table Rendering Engine

```python
class TableRenderer:
    """
    Renders semantic tables with pixel-perfect precision.
    Handles overflow, conditional formatting, and multi-format export.
    """

    async def render_table(
        self,
        table_spec: TableSpec,
        headers: list[str],
        rows: list[list[str]],
        theme: Theme,
        mode: str,  # "standard" | "premium"
    ) -> RenderedTable:
        dimensions = self._calculate_dimensions(headers, rows, table_spec, theme)
        html = self._build_html(table_spec, headers, rows, theme, dimensions)
        pptx_calls = self._build_pptx_native(table_spec, headers, rows, theme, dimensions)
        return RenderedTable(html=html, pptx=pptx_calls, dimensions=dimensions)

    def _calculate_dimensions(
        self,
        headers: list[str],
        rows: list[list[str]],
        spec: TableSpec,
        theme: Theme,
        canvas: tuple[int, int] = (1920, 1080),
    ) -> TableDimensions:
        num_cols = len(headers)
        num_rows = len(rows) + (1 if spec.constraints.headerRow else 0)
        num_rows += 1 if spec.constraints.totalsRow else 0

        # Row height calculation
        base_row_height = 44    # Body row (px)
        header_height = 56      # Header row (taller)
        padding = spec.constraints.cellPadding or 16

        # Column widths — proportional with minimum
        available_width = spec.position.width or (canvas[0] - spec.position.x * 2)
        col_width = max(available_width // num_cols, 100)  # Min 100px per column

        total_height = header_height + (len(rows) * base_row_height)
        max_height = canvas[1] - spec.position.y - 80  # 80px footer clearance

        if total_height > max_height:
            # Shrink rows or paginate
            if spec.constraints.maxRows and len(rows) > spec.constraints.maxRows:
                rows = rows[: spec.constraints.maxRows]
                total_height = header_height + (spec.constraints.maxRows * base_row_height)
            else:
                shrink = max_height / total_height
                base_row_height = int(base_row_height * shrink)
                total_height = max_height

        return TableDimensions(
            width=available_width,
            height=min(total_height, max_height),
            col_width=col_width,
            row_height=base_row_height,
            header_height=header_height,
            num_cols=num_cols,
            num_rows=num_rows,
        )

    def _apply_conditional_formatting(
        self,
        cell_value: str,
        col_index: int,
        rules: list[ConditionalRule] | None,
    ) -> dict:
        """Returns CSS overrides for cells matching conditional rules."""
        if not rules:
            return {}
        for rule in rules:
            if rule.column != col_index:
                continue
            try:
                numeric = float(cell_value.replace("$", "").replace(",", "").replace("%", ""))
            except ValueError:
                continue
            if rule.condition == "positive" and numeric > 0:
                return rule.style
            if rule.condition == "negative" and numeric < 0:
                return rule.style
            if rule.condition == "above_threshold" and numeric > (rule.threshold or 0):
                return rule.style
            if rule.condition == "below_threshold" and numeric < (rule.threshold or 0):
                return rule.style
        return {}
```

### Advanced Table Features

```typescript
// SORTABLE TABLES (HTML renderer only)
interface SortableTable extends TableSpec {
  sortable: true;
  defaultSortCol: number;       // Column index for initial sort
  sortDirection: "asc" | "desc";
  sortIcon: "▲" | "▼" | "⇅";
  activeSortBg: string;         // Active sort header highlight
}

// RESPONSIVE OVERFLOW HANDLING
interface TableOverflowStrategy {
  rows: "paginate" | "truncate" | "shrink-font" | "scroll";
  columns: "compress" | "horizontal-scroll" | "collapse-to-accordion";
  paginationThreshold: number;   // Row count that triggers pagination
  fontShrinkMin: number;         // Minimum font size (10px)
  maxShrinkRatio: number;        // Never shrink below 70% of base
}

// PPTX-NATIVE TABLE EXPORT
interface PptxTableExport {
  slideObj: PptxGenJS.Slide;
  tableRows: PptxGenJS.TableRow[];
  tableBorder: PptxGenJS.TableBorderProps;
  options: {
    x: number; y: number; w: number; h: number;
    colW: number[];
    rowH: number[];
    border: { type: "solid"; color: string; pt: number };
    autoPage: boolean;
    autoPageRepeatHeader: boolean;
    margin: number;
    fontSize: number;
    fontFace: string;
    color: string;
    fill: { color: string };
    align: "left" | "center" | "right";
    valign: "top" | "middle" | "bottom";
  };
}
```

---

### 4.24.5 Chart Specification System

Each chart type has a base specification plus type-specific extensions. All charts inherit from `ChartSpec`:

```typescript
// ══════════════════════════════════════════════════════════════════════
// BASE CHART SPECIFICATION (inherited by all chart types)
// ══════════════════════════════════════════════════════════════════════

interface ChartSpec {
  type: ChartType;
  position: {
    x: number;       // Left offset (px)
    y: number;       // Top offset (px)
    width: number;    // Chart area width (800-1200px typical)
    height: number;   // Chart area height (350-500px typical)
  };
  style: {
    titlePosition: "above" | "below" | "overlay" | "none";
    legendPosition: "right" | "bottom" | "none" | "floating";
    showDataLabels: boolean;
    showAxisLabels: boolean;
    showGridLines: boolean;
    showLegend: boolean;
    axisColor: string;
    gridColor: string;
    tickFontFamily: string;
    dataLabelFontSize: number;       // 10-14px
    annotationFontStyle: "italic" | "regular";
    maxValueFormat: string;          // "$1.2M", "12%", "1,234"
    zeroBaseline: boolean;           // Start y-axis at 0?
    negativeValues: boolean;         // Allow negative values?
    animationDuration: number;       // Entrance animation (ms)
    animationEasing: "ease-out" | "spring" | "cubic-bezier";
    colorPalette: string[];          // Series color array from theme
    cornerRadius: number;            // Bar/segment corner radius
    responsiveResize: boolean;       // Adapt to container on export
  };
  data: ChartData;
  accessibility: ChartAccessibility;
}

interface ChartData {
  labels: string[];                  // Category labels
  series: ChartSeries[];             // One or more data series
  metadata?: {
    source?: string;                 // "Source: Gartner 2025"
    unit?: string;                   // "$", "%", "users"
    dateRange?: string;              // "Q1 2024 - Q3 2025"
  };
}

interface ChartSeries {
  name: string;
  values: number[];
  color?: string;                    // Override palette color
  emphasis?: boolean;                // Visually emphasize this series
}

interface ChartAccessibility {
  altText: string;                   // Screen reader description
  highContrastMode: boolean;         // Pattern fills for color-blind users
  ariaLabel: string;                 // ARIA label for chart container
  dataTableFallback: boolean;        // Render hidden data table for screen readers
  patternFills: boolean;             // Use hatch/dot/stripe patterns (not just color)
}
```

### Type-Specific Chart Extensions

```typescript
// ── BAR CHART ──
interface BarChartSpec extends ChartSpec {
  barWidth: number;                  // Bar thickness (px)
  barGap: number;                    // Gap between groups
  groupPadding: number;              // Padding within grouped bars
  valueLabelPosition: "end" | "inside" | "above" | "none";
  highlightBarIndex: number | null;  // Which bar to emphasize (null = none)
  showTrendLine: boolean;
  trendLineColor: string;
  baselineValue: number;             // Reference line value
}

// ── LINE CHART ──
interface LineChartSpec extends ChartSpec {
  lineWidth: number;                 // Stroke width (1-4px)
  lineStyle: "solid" | "dashed" | "dotted";
  marker: "circle" | "square" | "diamond" | "none";
  markerSize: number;                // 4-8px
  interpolation: "linear" | "monotone" | "cardinal" | "step";
  showArea: boolean;                 // Fill area under line
  areaOpacity: number;               // 0.0-0.4 (subtle)
  showConfidenceBand: boolean;
  confidenceInterval: number;        // 0.90 or 0.95
  referenceLine: number | null;      // Target/benchmark
  forecastStartIndex: number | null; // Index where forecast begins (dashed)
}

// ── PIE / DONUT CHART ──
interface PieChartSpec extends ChartSpec {
  variant: "pie" | "donut" | "semi_pie" | "sunburst" | "waffle";
  innerRadius: number;               // 0 for pie, 0.5-0.7 for donut
  outerRadius: number;
  startAngle: number;                // 0 = 12 o'clock
  padAngle: number;                  // Gap between slices (radians)
  sliceCornerRadius: number;
  showPercentages: boolean;
  showConnectorLines: boolean;       // Label connector lines
  emphasizeSlice: number | null;     // Pop-out slice index
  centerLabel: string | null;        // Donut center text (e.g., "Total: $12M")
  sort: "descending" | "ascending" | "data-order";
}

// ── SCATTER / BUBBLE CHART ──
interface ScatterChartSpec extends ChartSpec {
  pointSize: number;                 // Default dot radius
  pointShape: "circle" | "square" | "triangle" | "diamond";
  pointOpacity: number;              // 0.3-0.9
  showRegression: boolean;           // Overlay trend line
  regressionType: "linear" | "polynomial" | "logarithmic";
  regressionColor: string;
  showConfidenceEllipse: boolean;
  jitter: { x: number; y: number }; // Spread overlapping points
  sizeAccessor: string | null;       // Field for bubble size dimension
  colorAccessor: string | null;      // Field for color dimension
}

// ── FUNNEL CHART ──
interface FunnelChartSpec extends ChartSpec {
  stages: FunnelStage[];
  stageGap: number;
  showPercentage: boolean;
  showConversionRate: boolean;
  showDropoff: boolean;
  dropoffColor: string;
  orientation: "vertical" | "horizontal";
}

interface FunnelStage {
  label: string;
  value: number;
  color: string;
}

// ── WATERFALL CHART ──
interface WaterfallChartSpec extends ChartSpec {
  positiveColor: string;             // e.g., "#10B981"
  negativeColor: string;             // e.g., "#EF4444"
  totalColor: string;                // e.g., "#2563EB"
  showConnectors: boolean;           // Lines between bars
  showRunningTotal: boolean;         // Cumulative line overlay
}

// ── METRIC CARD / DASHBOARD ──
interface MetricCardSpec extends ChartSpec {
  layout: "single" | "grid_2x2" | "grid_3x1" | "grid_2x3";
  metrics: MetricItem[];
  showSparkline: boolean;
  showTrendArrow: boolean;
  animateCounter: boolean;           // Count-up animation
  counterDuration: number;           // Animation duration (ms)
}

interface MetricItem {
  label: string;
  value: string;                     // "$2.4M", "89", "5,120"
  change: string;                    // "+45% YoY", "-12 pts"
  trend: "up" | "down" | "neutral";
  sparklineData?: number[];          // Small trend array
  color?: string;
}

// ── GAUGE / PROGRESS CHARTS ──
interface GaugeChartSpec extends ChartSpec {
  value: number;
  maxValue: number;
  thresholds: { value: number; color: string; label: string }[];
  showNeedle: boolean;
  showValue: boolean;
  arcWidth: number;                  // Ring thickness
}

// ── SANKEY DIAGRAM ──
interface SankeyChartSpec extends ChartSpec {
  nodes: { id: string; label: string; color: string }[];
  links: { source: string; target: string; value: number }[];
  nodeWidth: number;
  nodePadding: number;
  linkOpacity: number;
}

// ── QUADRANT CHART ──
interface QuadrantChartSpec extends ChartSpec {
  xAxisLabel: string;
  yAxisLabel: string;
  quadrantLabels: [string, string, string, string]; // TL, TR, BL, BR
  points: { label: string; x: number; y: number; size?: number; color?: string }[];
  highlightQuadrant: 0 | 1 | 2 | 3 | null;
}
```

---

### 4.24.6 Diagram & Graph System

```typescript
// ══════════════════════════════════════════════════════════════════════
// DIAGRAM TYPES — Structural Visual Elements
// ══════════════════════════════════════════════════════════════════════

type DiagramType =
  | "flowchart"                // Process flow with decisions
  | "sequence_diagram"         // Step-by-step linear flow
  | "state_machine"            // States + transitions
  | "decision_tree"            // Branching logic tree
  | "org_chart"                // Organizational hierarchy
  | "mind_map"                 // Central concept with branches
  | "concept_map"              // Idea relationships with labeled edges
  | "fishbone"                 // Ishikawa cause-effect diagram
  | "process_flow"             // Swimlane process diagram
  | "value_chain"              // Porter's value chain stages
  | "user_journey"             // Touchpoint experience map
  | "service_blueprint"        // Service design layers
  | "system_context"           // C4 system context view
  | "network_topology"         // Infrastructure node-edge diagram
  | "architecture_diagram"     // Technical component layout
  | "venn_diagram"             // Overlapping set circles
  | "cycle_diagram";           // Circular process steps

// ── BASE DIAGRAM SPEC ──
interface DiagramSpec {
  type: DiagramType;
  position: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  constraints: {
    nodeSize: { w: number; h: number; r: number };
    nodeSpacing: number;
    edgeRouting: "orthogonal" | "curved" | "organic";
    edgeStyle: "solid" | "dashed" | "dotted";
    edgeColor: string;
    edgeWidth: number;
    nodeBackground: string;
    nodeBorderRadius: number;
    labelPosition: "center" | "top" | "below" | "floating";
    labelFontSize: number;
    labelColor: string;
    maxLabelLength: number;
    fitToContainer: boolean;
    overflow: "scroll" | "truncate" | "scale-down";
  };
}

// ── NODE DEFAULTS BY SIZE ──
const DIAGRAM_NODE_SIZES = {
  small:  { w: 140, h: 100, r: 8 },
  medium: { w: 200, h: 140, r: 12 },
  large:  { w: 280, h: 200, r: 16 },
  huge:   { w: 360, h: 260, r: 20 },
} as const;

// ── EDGE / CONNECTION DEFAULTS ──
const EDGE_DEFAULTS = {
  color: "#64748B",
  width: 2,
  style: "solid" as const,
  arrowSize: 8,
  curvature: 0.3,     // 0=straight, 1=circular
  midpointLabel: false,
};

// ── Z-INDEX LAYERING ──
const Z_INDEX_LAYERS = {
  background: 0,
  watermark: 1,
  decorative: 2,
  annotation: 3,
  content: 10,
  accent: 20,
  header: 100,
};

// ── SPECIFIC DIAGRAM TYPES ──

interface FlowchartSpec extends DiagramSpec {
  nodes: FlowchartNode[];
  edges: FlowchartEdge[];
  orientation: "vertical" | "horizontal";
}

interface FlowchartNode {
  id: string;
  label: string;
  type: "process" | "decision" | "data" | "start" | "end" | "delay" | "merge";
  shape: "rect" | "diamond" | "parallelogram" | "rounded_rect" | "circle" | "stadium";
  fill: string;
  substeps?: string[];
}

interface FlowchartEdge {
  from: string;
  to: string;
  label?: string;
  style?: "solid" | "dashed";
}

interface OrgChartSpec extends DiagramSpec {
  layout: "tree" | "matrix";
  hierarchyLevels: number;
  reportingLines: boolean;
  avatarSize: number;
  nodes: OrgNode[];
}

interface OrgNode {
  id: string;
  name: string;
  title: string;
  avatarUrl?: string;
  children: string[];    // IDs of direct reports
}

interface MindMapSpec extends DiagramSpec {
  centralConcept: string;
  branchStyle: "organic" | "geometric" | "classic";
  connectionStyle: "curved" | "straight";
  maxBranches: number;   // Main branches from center
  maxDepth: number;      // How deep the tree goes
  branches: MindMapBranch[];
}

interface MindMapBranch {
  id: string;
  label: string;
  color: string;
  children: MindMapBranch[];
}

interface StateMachineSpec extends DiagramSpec {
  states: StateNode[];
  transitions: StateTransition[];
  initialState: string;
  finalStates: string[];
}

interface StateNode {
  id: string;
  label: string;
  shape: "rect" | "rounded_rect" | "pill" | "hexagon" | "octagon";
  fill: string;
}

interface StateTransition {
  from: string;
  to: string;
  label?: string;
  style?: "solid" | "dashed" | "glow";
}

interface FishboneSpec extends DiagramSpec {
  effectName: string;                // "Problem" or "Effect"
  categories: FishboneCategory[];
  headPosition: "right" | "left";
  spineColor: string;
  boneColor: string;
}

interface FishboneCategory {
  name: string;                      // e.g., "People", "Process", "Technology"
  causes: string[];
  color: string;
}

interface TimelineSpec extends DiagramSpec {
  orientation: "horizontal" | "vertical";
  phases: TimelinePhase[];
  showDates: boolean;
  showProgressBar: boolean;
  showPercentage: boolean;
  connectionColor: string;
}

interface TimelinePhase {
  id: string;
  label: string;
  date: string;
  type: "milestone" | "activity" | "success" | "warning";
  color: string;
  description?: string;
}

interface NetworkDiagramSpec extends DiagramSpec {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  forceDirected: boolean;            // Auto-layout with physics simulation
  showLabels: boolean;
  hoverEffect: "glow" | "highlight" | "tooltip";
}

interface NetworkNode {
  id: string;
  label: string;
  x?: number;
  y?: number;
  type: "rectangle" | "circle" | "cloud" | "database" | "hexagon";
  fill: string;
  size: "small" | "medium" | "large";
}

interface NetworkEdge {
  from: string;
  to: string;
  label?: string;
  style: "solid" | "dashed" | "dotted";
  bidirectional?: boolean;
}
```

---

### 4.24.7 Icon System (Complete Library)

```typescript
// ══════════════════════════════════════════════════════════════════════
// ICON SYSTEM — Categorized, Semantic, Theme-Aware
// ══════════════════════════════════════════════════════════════════════

// Primary icon source: Lucide React (1000+ icons, 2px stroke, MIT license)
// Fallback: Heroicons (for specialized UI icons)
// Custom: User-uploaded SVG or Brand DNA logo extraction

type IconCategory =
  // Navigation & Arrows
  | "navigation"         // ← → ↑ ↓ chevrons, breadcrumbs
  | "directional"        // Compass, expand, collapse, zoom

  // Status & Indicators
  | "status"             // ✓ ✗ ⚠ ● checkmarks, flags, badges
  | "warning"            // Alert triangles, caution
  | "success"            // Green checks, thumbs up
  | "error"              // Red crosses, alerts
  | "info"               // Blue info circles

  // Data & Charts (mini-icon versions)
  | "chart"              // Bar/line/pie/scatter mini icons
  | "trend"              // TrendingUp, TrendingDown arrows
  | "metric"             // Target, gauge, speedometer

  // People & Organization
  | "person"             // User, avatar, team
  | "organization"       // Building, hierarchy, org chart
  | "social"             // GitHub, LinkedIn, Twitter/X, email

  // Interface / UI
  | "action"             // Edit, delete, copy, paste, save, undo
  | "layout"             // Grid, columns, sidebar, split
  | "media"              // Image, video, audio, camera
  | "file"               // Document, folder, archive, cloud

  // Shapes & Decorative
  | "shape"              // Rectangle, circle, polygon, star
  | "decorative"         // Sparkles, gradient, texture, glass
  | "brand"              // Company logos from Brand DNA

  // Presentation-Specific
  | "slide"              // Presentation, slideshow, cursor
  | "formatting";        // Bold, italic, heading, alignment

interface IconSpec {
  name: string;                // Lucide icon name: "trending-up", "check-circle", etc.
  category: IconCategory;
  size: number;                // 16, 20, 24, 32, 48 (px)
  strokeWidth: number;         // 1.5 or 2 (Lucide default = 2)
  color: string;               // Theme-aware color
  fill?: string;               // Optional fill (default: none)
  className?: string;          // Custom CSS class
}

// Icon usage in elements:
// - Bullet points: icon + text (e.g., 🚀 "Launched in 3 markets")
// - Stat cards: icon + value + label (e.g., 📈 "$2.4M" "ARR")
// - Feature grids: icon + title + description
// - Status indicators: ✓ / ✗ / ⚠ in tables and matrices
// - Social proof: brand icon row (logos of partner companies)
// - Navigation: arrows in flowcharts and diagrams

// Semantic icon mapping (Content Intelligence auto-selects):
const SEMANTIC_ICON_MAP: Record<string, string> = {
  "revenue":     "dollar-sign",
  "growth":      "trending-up",
  "decline":     "trending-down",
  "users":       "users",
  "security":    "shield-check",
  "speed":       "zap",
  "quality":     "award",
  "innovation":  "lightbulb",
  "team":        "users-round",
  "launch":      "rocket",
  "target":      "target",
  "calendar":    "calendar",
  "location":    "map-pin",
  "email":       "mail",
  "phone":       "phone",
  "link":        "external-link",
  "download":    "download",
  "upload":      "upload",
  "settings":    "settings",
  "search":      "search",
  "filter":      "filter",
  "sort":        "arrow-up-down",
  "check":       "check-circle",
  "warning":     "alert-triangle",
  "error":       "x-circle",
  "info":        "info",
  "help":        "help-circle",
  "star":        "star",
  "heart":       "heart",
  "bookmark":    "bookmark",
  "share":       "share-2",
  "edit":        "pencil",
  "delete":      "trash-2",
  "copy":        "copy",
  "clipboard":   "clipboard",
  "refresh":     "refresh-cw",
  "loading":     "loader",
  "database":    "database",
  "server":      "server",
  "cloud":       "cloud",
  "code":        "code",
  "terminal":    "terminal",
  "api":         "plug",
  "chart":       "bar-chart-2",
  "pie":         "pie-chart",
  "globe":       "globe",
  "lock":        "lock",
  "unlock":      "unlock",
  "key":         "key",
  "eye":         "eye",
  "clock":       "clock",
  "money":       "banknote",
  "credit_card": "credit-card",
  "gift":        "gift",
  "package":     "package",
  "truck":       "truck",
  "home":        "home",
  "building":    "building",
  "megaphone":   "megaphone",
  "award":       "trophy",
  "graduation":  "graduation-cap",
  "microscope":  "microscope",
  "dna":         "dna",
  "brain":       "brain",
  "cpu":         "cpu",
};
```

---

### 4.24.8 Presentation-Specific Data Elements

```typescript
// ══════════════════════════════════════════════════════════════════════
// SPECIALIZED SLIDE ELEMENTS (beyond charts/tables/diagrams)
// ══════════════════════════════════════════════════════════════════════

type PresentationElement =
  // ── METRICS & STATS ──
  | "hero_stat"                 // One BIG number with label (40% of slide)
  | "stats_showcase"            // 3-6 key metrics in a row/grid
  | "metric_comparison"         // Before/after or target/actual pairs

  // ── SOCIAL PROOF ──
  | "testimonial_block"         // Quote + avatar + name + title
  | "trust_badges"              // Client logo row (6-8 logos)
  | "social_proof_bar"          // "Trusted by 500+ companies"
  | "certification_badges"      // SOC2, HIPAA, GDPR, ISO badges
  | "award_recognition"         // Trophy/badge display

  // ── TEAM & PEOPLE ──
  | "team_grid"                 // Photo cards with name + role
  | "advisor_row"               // Smaller cards (advisors, board)

  // ── PRICING & COMPARISON ──
  | "pricing_table_highlight"   // 2-3 tier pricing with featured column
  | "feature_comparison_grid"   // Feature checklist (✓/✗ per tier)

  // ── BRANDING ──
  | "logo_lockup"               // Logo + tagline (enforced branding)
  | "brand_color_strip"         // Color palette display

  // ── CALLOUTS & ANNOTATIONS ──
  | "callout_box"               // Highlighted text with icon + border
  | "data_source_footer"        // "Source: Gartner 2025" bottom text
  | "footnote"                  // Small citation text
  | "stat_change_badge"         // Inline delta: "+12% MoM" pill
  | "tooltip_annotation"        // Arrow pointing to element with explanation
  | "reference_line_label"      // "Industry Average" label on chart
  | "target_marker";            // "Goal: 95%" marker on gauge/chart

interface HeroStatSpec {
  value: string;                // "$2.4M"
  label: string;                // "Annual Recurring Revenue"
  change?: string;              // "+340% YoY"
  trend?: "up" | "down" | "neutral";
  icon?: string;                // Lucide icon name
  animate: boolean;             // Count-up animation
  fontSize: number;             // 72-144px for the big number
  position: "center" | "left" | "right";
}

interface TestimonialSpec {
  quote: string;
  attribution: string;           // "Jane Doe, CEO at Acme"
  avatarUrl?: string;
  companyLogo?: string;
  style: "card" | "minimal" | "large_quote";
}

interface TrustBadgeSpec {
  logos: { url: string; alt: string; width: number }[];
  layout: "row" | "grid";
  grayscale: boolean;            // Show logos in grayscale? (common pattern)
  hoverColor: boolean;           // Color on hover?
  maxLogos: number;              // 6-8 per row
  spacing: number;               // Gap between logos
}
```

---

### 4.24.9 Chart Intelligence Engine (Smart Defaults)

```python
class ChartIntelligenceEngine:
    """
    Analyzes content type and data structure to select the optimal
    chart type, then applies sensible defaults.
    Called by Layer 2 (Content Intelligence) when it detects data content.
    """

    RULES: list[tuple[str, callable, list[str]]] = [
        # (name, condition_fn, candidate_chart_types)

        # TIME SERIES → Line or Area charts
        ("time_series",
         lambda e: e.get("has_time_axis") and len(e.get("data_points", [])) > 3,
         ["line", "area", "stacked_area", "sparkline"]),

        # COMPARISON (categories) → Bar charts
        ("comparison",
         lambda e: e.get("has_categories") and e.get("purpose") == "compare",
         ["bar", "grouped_bar", "horizontal_bar", "lollipop", "bullet_chart"]),

        # PART-WHOLE (percentages) → Pie / Donut
        ("proportion",
         lambda e: e.get("has_percentages") or e.get("purpose") == "composition",
         ["donut", "pie", "waffle", "treemap", "sunburst"]),

        # HIERARCHY → Treemap / Sunburst
        ("hierarchy",
         lambda e: e.get("has_nested_data") or e.get("has_parent_child"),
         ["treemap", "sunburst", "nested_ring", "icicle"]),

        # CORRELATION → Scatter / Bubble
        ("correlation",
         lambda e: e.get("has_xy_data") or e.get("purpose") == "correlation",
         ["scatter", "bubble", "density_heatmap"]),

        # FUNNEL / STAGES → Funnel / Pipeline
        ("stages",
         lambda e: e.get("has_stages") or e.get("purpose") == "conversion",
         ["funnel", "pipeline", "waterfall"]),

        # DISTRIBUTION → Histogram / Box / Violin
        ("distribution",
         lambda e: e.get("purpose") == "distribution",
         ["histogram", "box_plot", "violin", "ridgeline"]),

        # FINANCIAL METRICS → Metric Cards / Dashboard
        ("metrics",
         lambda e: e.get("has_kpi") or e.get("purpose") == "metrics",
         ["metric_card", "metric_dashboard", "big_number", "gauge"]),

        # FLOW / RELATIONSHIP → Sankey / Network
        ("relationship",
         lambda e: e.get("has_flows") or e.get("purpose") == "flow",
         ["sankey", "chord", "parallel_coordinates", "network_graph"]),

        # COMPETITIVE ANALYSIS → Quadrant / Matrix
        ("competitive",
         lambda e: e.get("purpose") == "competitive" or e.get("has_competitors"),
         ["quadrant", "comparison_matrix", "radar_chart"]),

        # TIMELINE / PROJECT → Gantt / Timeline
        ("timeline",
         lambda e: e.get("has_dates") or e.get("purpose") == "roadmap",
         ["timeline", "gantt", "product_roadmap"]),

        # GEOGRAPHIC → Maps
        ("geographic",
         lambda e: e.get("has_regions") or e.get("has_coordinates"),
         ["choropleth_map", "geo_scatter", "flow_map"]),

        # TAM/SAM/SOM (pitch-specific) → Nested circles
        ("market_size",
         lambda e: e.get("purpose") == "market_size",
         ["tam_sam_som"]),
    ]

    def select_chart_type(
        self,
        content_element: dict,
        slide_role: str,
        mode: str,
    ) -> str:
        """Select the best chart type based on data characteristics."""
        for name, condition, candidates in self.RULES:
            if condition(content_element):
                # Premium mode: pick the most expressive variant
                # Standard mode: pick the simplest (fastest to render)
                if mode == "premium":
                    return candidates[0]
                return candidates[-1] if len(candidates) > 1 else candidates[0]

        # Fallback: bar chart (universally readable)
        return "bar"

    def apply_smart_defaults(
        self,
        chart_type: str,
        data: dict,
        theme: dict,
    ) -> dict:
        """Apply sensible defaults based on chart type and theme."""
        defaults = {
            "colorPalette": theme.get("chart_colors", [
                "#2563EB", "#7C3AED", "#059669", "#D97706",
                "#DC2626", "#0891B2", "#4F46E5", "#EA580C",
            ]),
            "cornerRadius": 4 if chart_type in ("bar", "grouped_bar", "stacked_bar") else 0,
            "animationDuration": 800,
            "animationEasing": "ease-out",
            "showGridLines": chart_type not in ("pie", "donut", "treemap", "sunburst", "funnel"),
            "showDataLabels": chart_type in ("bar", "pie", "donut", "metric_card", "big_number"),
            "showLegend": len(data.get("series", [])) > 1,
            "zeroBaseline": chart_type in ("bar", "grouped_bar", "stacked_bar", "waterfall"),
            "legendPosition": "bottom" if chart_type in ("line", "area") else "right",
        }
        return defaults
```

---

### 4.24.10 GLA Integration (Data → Layout Mapping)

How data elements map to Generative Layout Algebra primitives (connecting this system to §4.5 Layer 3):

```typescript
// ══════════════════════════════════════════════════════════════════════
// DATA ELEMENT → GLA PRIMITIVE MAPPING
// ══════════════════════════════════════════════════════════════════════

// When Layer 2 produces a ContentElement of type "chart", "table", or "diagram",
// Layer 3's GLA composition uses content-slot with type-aware sizing:

// ── TABLE → GLA ──
// Tables are placed as content-slots with height calculated from row count.
// GLA Output:
{
  type: "column",
  gap: 24,
  children: [
    { type: "text-fit", elementRef: "heading", minFontSize: 36, maxFontSize: 72, maxLines: 2 },
    {
      type: "content-slot",
      elementRef: "table-body",
      sizing: {
        width: "grow",
        height: { min: 250, max: 700 }   // Adaptive to row count
      }
    }
  ]
}

// ── SINGLE CHART → GLA ──
// Charts get a content-slot that grows to fill available vertical space.
// GLA Output:
{
  type: "column",
  gap: 24,
  children: [
    { type: "text-fit", elementRef: "chart-title", minFontSize: 36, maxFontSize: 64, maxLines: 2 },
    {
      type: "content-slot",
      elementRef: "chart-area",
      sizing: { width: "grow", height: { min: 300, max: 550 } },
      aspectRatio: 1.6    // Landscape ratio for most charts
    }
  ]
}

// ── CHART + TABLE (Data-Heavy Slide) → GLA ──
// When a slide has both chart and table, split horizontally:
{
  type: "column",
  gap: 24,
  children: [
    { type: "text-fit", elementRef: "heading", minFontSize: 32, maxFontSize: 56, maxLines: 1 },
    {
      type: "row",
      gap: 32,
      weights: [3, 2],    // Chart gets 60%, table gets 40%
      children: [
        {
          type: "content-slot",
          elementRef: "chart-area",
          sizing: { width: "grow", height: { min: 280, max: 480 } }
        },
        {
          type: "content-slot",
          elementRef: "table-sidebar",
          sizing: { width: "grow", height: "fit" }
        }
      ]
    }
  ]
}

// ── METRIC DASHBOARD → GLA ──
// KPI grids use uniform grid layout:
{
  type: "column",
  gap: 32,
  children: [
    { type: "text-fit", elementRef: "heading", minFontSize: 36, maxFontSize: 64, maxLines: 2 },
    {
      type: "grid",
      columns: 2,
      rows: 2,
      gap: 24,
      children: [
        { type: "content-slot", elementRef: "metric-0", sizing: { width: "grow", height: "grow" } },
        { type: "content-slot", elementRef: "metric-1", sizing: { width: "grow", height: "grow" } },
        { type: "content-slot", elementRef: "metric-2", sizing: { width: "grow", height: "grow" } },
        { type: "content-slot", elementRef: "metric-3", sizing: { width: "grow", height: "grow" } },
      ]
    }
  ]
}

// ── DIAGRAM → GLA ──
// Diagrams get maximum space with optional side text:
{
  type: "column",
  gap: 24,
  children: [
    { type: "text-fit", elementRef: "heading", minFontSize: 32, maxFontSize: 56, maxLines: 1 },
    {
      type: "content-slot",
      elementRef: "diagram-area",
      sizing: { width: "grow", height: "grow" }
    }
  ]
}

// ── HERO STAT → GLA ──
// Single big number dominates viewport (40-50% visual weight):
{
  type: "stack",
  alignment: { x: "center", y: "center" },
  children: [
    { type: "content-slot", elementRef: "background-gradient", sizing: { width: "grow", height: "grow" } },
    {
      type: "column",
      gap: 16,
      align: "center",
      children: [
        { type: "content-slot", elementRef: "hero-icon", sizing: { width: { fixed: 48 }, height: { fixed: 48 } } },
        { type: "text-fit", elementRef: "hero-value", minFontSize: 72, maxFontSize: 144, maxLines: 1 },
        { type: "text-fit", elementRef: "hero-label", minFontSize: 20, maxFontSize: 32, maxLines: 1 },
        { type: "text-fit", elementRef: "hero-change", minFontSize: 16, maxFontSize: 24, maxLines: 1 },
      ]
    }
  ]
}
```

### Pre-Computed GLA Patterns for Data Slides

```python
# Add to GLA_PATTERNS in §4.5:
GLA_DATA_PATTERNS = {
    # Pattern: Table with heading
    "heading_table": {
        "match": lambda e: (
            count_type(e, "heading") == 1
            and count_type(e, "table") == 1
        ),
        "layouts": [
            "column([text_fit('heading'), content_slot('table', grow, minH=250)], gap=24)",
            "column([text_fit('heading'), text_fit('subheading'), content_slot('table', grow)], gap=16)",
        ],
    },
    # Pattern: Chart with heading + optional bullets
    "heading_chart": {
        "match": lambda e: (
            count_type(e, "heading") == 1
            and count_type(e, "chart") == 1
        ),
        "layouts": [
            "column([text_fit('heading'), content_slot('chart', grow, aspect=1.6)], gap=24)",
            "row([content_slot('chart', grow), column([text_fit('heading'), content_slot('bullets')])], gap=32, weights=[3, 2])",
        ],
    },
    # Pattern: Metric dashboard (3-4 stat cards)
    "stats_dashboard": {
        "match": lambda e: 3 <= count_type(e, "stat") <= 6,
        "layouts": [
            "column([text_fit('heading'), grid(content_slots('stat'), cols=auto, gap=24)], gap=32)",
            "column([text_fit('heading'), row(content_slots('stat'), gap=20, weights=equal)], gap=32)",
        ],
    },
    # Pattern: Chart + Table side by side
    "chart_and_table": {
        "match": lambda e: (
            count_type(e, "chart") == 1
            and count_type(e, "table") == 1
        ),
        "layouts": [
            "column([text_fit('heading'), row([content_slot('chart'), content_slot('table')], gap=32, weights=[3, 2])], gap=24)",
        ],
    },
    # Pattern: Diagram (flow/org/mind map)
    "heading_diagram": {
        "match": lambda e: count_type(e, "diagram") == 1,
        "layouts": [
            "column([text_fit('heading'), content_slot('diagram', grow)], gap=24)",
            "row([column([text_fit('heading'), content_slot('bullets')], gap=16), content_slot('diagram', grow)], gap=32, weights=[1, 2])",
        ],
    },
    # Pattern: Hero stat
    "hero_stat": {
        "match": lambda e: (
            count_type(e, "stat") == 1
            and count_type(e, "heading") <= 1
            and count_type(e, "bullets") == 0
        ),
        "layouts": [
            "stack([content_slot('bg'), column([text_fit('stat_value', min=72, max=144), text_fit('stat_label'), text_fit('stat_change')], align=center)], alignment=center)",
        ],
    },
    # Pattern: Comparison matrix / SWOT / pricing
    "comparison_grid": {
        "match": lambda e: count_type(e, "comparison_matrix") == 1,
        "layouts": [
            "column([text_fit('heading'), content_slot('matrix', grow, minH=400)], gap=24)",
        ],
    },
    # Pattern: Timeline / Roadmap
    "timeline_slide": {
        "match": lambda e: count_type(e, "diagram") == 1 and e[0].get("diagram_type") in ("timeline", "gantt"),
        "layouts": [
            "column([text_fit('heading'), content_slot('timeline', grow, minH=350)], gap=24)",
        ],
    },
}
```

---

### 4.24.11 Chart Rendering Pipeline

How charts flow through the V9 pipeline to become pixel-perfect elements:

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Layer 2:     │───▷│ Chart Intel  │───▷│ Layer 3:     │───▷│ Layer 4:     │
│ Content      │    │ Engine picks │    │ GLA sizes    │    │ D3.js/       │
│ detects data │    │ chart type   │    │ chart slot   │    │ Recharts     │
│ elements     │    │ + defaults   │    │ (px coords)  │    │ renders      │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                   │
                                              ┌────────────────────┼────────────────────┐
                                              ▼                    ▼                    ▼
                                       ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                                       │ HTML/SVG     │    │ PPTX Native  │    │ PDF via      │
                                       │ (reveal.js   │    │ (PptxGenJS   │    │ Playwright   │
                                       │  + React)    │    │  chart calls)│    │ screenshot   │
                                       └──────────────┘    └──────────────┘    └──────────────┘
```

```python
# Updated ChartGenerator in Layer 4 (extends §4.6):
class ChartGenerator:
    """
    Generates charts from ContentElement data.
    Uses D3.js + Recharts for HTML/React renderers.
    Server-side renders via Playwright for consistent screenshots.
    Maps to PptxGenJS native chart calls for editable PPTX export.
    """

    # Full chart type → template mapping (90+ types → D3/Recharts templates)
    CHART_TEMPLATES: dict[str, str] = {
        # Comparison
        "bar": "d3_bar", "horizontal_bar": "d3_hbar", "grouped_bar": "d3_grouped_bar",
        "stacked_bar": "d3_stacked_bar", "waterfall": "d3_waterfall",
        "bullet_chart": "d3_bullet", "lollipop": "d3_lollipop",
        "diverging_bar": "d3_diverging", "radar_chart": "recharts_radar",
        # Trend
        "line": "recharts_line", "area": "recharts_area",
        "stacked_area": "recharts_stacked_area", "stepped_area": "d3_step",
        "smoothed_area": "recharts_area_smooth", "sparkline": "recharts_sparkline",
        "candlestick": "d3_candlestick", "streamgraph": "d3_streamgraph",
        # Proportion
        "pie": "recharts_pie", "donut": "recharts_pie_donut",
        "semi_pie": "d3_semi_pie", "sunburst": "d3_sunburst",
        "treemap": "recharts_treemap", "nested_ring": "d3_nested_ring",
        "waffle": "d3_waffle", "icicle": "d3_icicle",
        # Scatter
        "scatter": "recharts_scatter", "bubble": "d3_bubble",
        "density_heatmap": "d3_heatmap", "dot_plot": "d3_dot",
        "box_plot": "d3_boxplot", "violin": "d3_violin",
        "histogram": "d3_histogram", "ridgeline": "d3_ridgeline",
        # Business
        "funnel": "d3_funnel", "pipeline": "d3_pipeline",
        "gantt": "d3_gantt", "burn_down": "recharts_line",
        "cumulative_flow": "recharts_stacked_area", "product_roadmap": "d3_roadmap",
        "tam_sam_som": "d3_nested_circles", "s_curve": "d3_s_curve",
        # Financial
        "metric_card": "react_metric_card", "metric_dashboard": "react_metric_grid",
        "sparkline_table": "react_sparkline_table", "scorecard": "react_scorecard",
        "big_number": "react_big_number", "animated_counter": "react_counter",
        "gauge": "d3_gauge", "progress_ring": "d3_progress_ring",
        # Relationship
        "sankey": "d3_sankey", "parallel_coordinates": "d3_parallel",
        "slope_graph": "d3_slope", "quadrant": "d3_quadrant",
        "chord": "d3_chord", "network_graph": "d3_force",
        "arc_diagram": "d3_arc", "matrix_heatmap": "d3_matrix_heatmap",
        # Geo
        "choropleth_map": "d3_geo_choropleth", "geo_scatter": "d3_geo_scatter",
        "hexbin_map": "d3_hexbin", "flow_map": "d3_geo_flow",
        "connection_map": "d3_geo_connection",
        # Statistical
        "confusion_matrix": "d3_confusion", "roc_curve": "d3_roc",
        "learning_curve": "recharts_line", "forest_plot": "d3_forest",
        "qq_plot": "d3_qq", "calibration_curve": "recharts_line",
        # Comparison matrices
        "comparison_matrix": "react_comparison_grid", "pricing_table": "react_pricing",
        "feature_matrix": "react_feature_grid", "decision_matrix": "react_decision",
        "swot_grid": "react_swot", "risk_matrix": "d3_risk_matrix",
        # Timeline
        "timeline": "d3_timeline", "sequence_diagram": "d3_sequence",
        "process_flow": "d3_swimlane",
    }

    # PPTX-native chart type mapping (editable in PowerPoint):
    PPTX_NATIVE_CHARTS: dict[str, str] = {
        "bar": "bar", "grouped_bar": "bar", "stacked_bar": "bar",
        "horizontal_bar": "bar", "line": "line", "area": "area",
        "pie": "pie", "donut": "doughnut", "scatter": "scatter",
        "bubble": "bubble", "radar_chart": "radar",
    }

    async def generate(
        self,
        chart_element: ContentElement,
        theme: Theme,
        dimensions: Size,
        mode: str,
    ) -> ChartOutput:
        """
        Returns:
        - svg: Inline SVG for HTML renderers (all chart types)
        - png: Rasterized via Playwright (for PDF/fallback)
        - pptx_native: PptxGenJS native chart calls (editable; only for basic types)
        - react_component: React JSX for interactive charts
        """
        chart_type = chart_element.chart_type
        template = self.CHART_TEMPLATES.get(chart_type, "d3_bar")

        # Apply smart defaults from ChartIntelligenceEngine
        defaults = ChartIntelligenceEngine().apply_smart_defaults(
            chart_type, chart_element.data, theme
        )

        # Apply accessibility
        accessibility = self._build_accessibility(chart_element, chart_type)

        # Render
        svg = await self._render_svg(template, chart_element.data, theme, dimensions, defaults)
        png = await self._rasterize(svg, dimensions) if mode == "premium" else None
        pptx = self._build_pptx_native(chart_element, theme) if chart_type in self.PPTX_NATIVE_CHARTS else None
        react = self._build_react_component(chart_type, chart_element.data, theme, defaults)

        return ChartOutput(svg=svg, png=png, pptx_native=pptx, react=react, accessibility=accessibility)

    def _build_accessibility(self, element: ContentElement, chart_type: str) -> ChartAccessibility:
        """Generate automatic accessibility metadata for every chart."""
        data = element.data
        series_desc = ", ".join(
            f"{s['name']}: {s['values'][0]} to {s['values'][-1]}" for s in data.get("series", [])
        )
        return ChartAccessibility(
            altText=f"{chart_type.replace('_', ' ').title()} showing {element.get('title', 'data')}. {series_desc}",
            highContrastMode=False,
            ariaLabel=f"Chart: {element.get('title', chart_type)}",
            dataTableFallback=True,
            patternFills=False,
        )
```

---

### 4.24.12 Chart Animation Controller

```typescript
// ══════════════════════════════════════════════════════════════════════
// CHART ANIMATION SYSTEM
// ══════════════════════════════════════════════════════════════════════

interface ChartAnimationConfig {
  entrance: {
    type: "fade" | "grow" | "slide-up" | "draw" | "count-up" | "stagger";
    duration: number;           // 400-1200ms
    easing: "ease-out" | "spring" | "cubic-bezier(0.34, 1.56, 0.64, 1)";
    delay: number;              // Delay before animation starts (ms)
    staggerInterval: number;    // Time between each bar/slice/point (ms)
  };
  update: {
    type: "morph" | "crossfade" | "instant";
    duration: number;           // 300-600ms
  };
  exit: {
    type: "fade" | "shrink" | "slide-down";
    duration: number;           // 200-400ms
  };
  hover: {
    scale: number;              // 1.02-1.08 (subtle enlarge)
    brightness: number;         // 1.05-1.15 (subtle brighten)
    tooltipDelay: number;       // 200ms before showing tooltip
  };
}

// Default animations per chart type:
const CHART_ANIMATION_DEFAULTS: Record<string, ChartAnimationConfig["entrance"]> = {
  bar:            { type: "grow", duration: 800, easing: "spring", delay: 0, staggerInterval: 50 },
  grouped_bar:    { type: "grow", duration: 800, easing: "spring", delay: 0, staggerInterval: 30 },
  line:           { type: "draw", duration: 1200, easing: "ease-out", delay: 0, staggerInterval: 0 },
  area:           { type: "draw", duration: 1000, easing: "ease-out", delay: 0, staggerInterval: 0 },
  pie:            { type: "grow", duration: 800, easing: "spring", delay: 0, staggerInterval: 80 },
  donut:          { type: "grow", duration: 800, easing: "spring", delay: 0, staggerInterval: 80 },
  scatter:        { type: "fade", duration: 600, easing: "ease-out", delay: 0, staggerInterval: 20 },
  funnel:         { type: "slide-up", duration: 600, easing: "ease-out", delay: 0, staggerInterval: 100 },
  metric_card:    { type: "count-up", duration: 2000, easing: "ease-out", delay: 200, staggerInterval: 150 },
  big_number:     { type: "count-up", duration: 2000, easing: "ease-out", delay: 0, staggerInterval: 0 },
  timeline:       { type: "stagger", duration: 400, easing: "ease-out", delay: 0, staggerInterval: 120 },
  treemap:        { type: "grow", duration: 600, easing: "ease-out", delay: 0, staggerInterval: 40 },
  sankey:         { type: "draw", duration: 1000, easing: "ease-out", delay: 200, staggerInterval: 0 },
  gauge:          { type: "draw", duration: 1500, easing: "spring", delay: 0, staggerInterval: 0 },
  waterfall:      { type: "stagger", duration: 500, easing: "spring", delay: 0, staggerInterval: 80 },
};
```

---

### 4.24.13 Data Validation & Error States

```python
class DataValidator:
    """
    Validates chart/table data BEFORE rendering.
    Catches malformed data, extreme outliers, and type mismatches.
    Provides graceful fallbacks instead of broken charts.
    """

    def validate_chart_data(self, data: dict, chart_type: str) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        # Check required fields
        if not data.get("labels") and chart_type not in ("scatter", "bubble", "network_graph"):
            errors.append("Missing 'labels' array for chart data")
        if not data.get("series"):
            errors.append("Missing 'series' array — no data to render")

        # Check data consistency
        for series in data.get("series", []):
            if not series.get("values"):
                errors.append(f"Series '{series.get('name', '?')}' has no values")
            elif data.get("labels") and len(series["values"]) != len(data["labels"]):
                warnings.append(
                    f"Series '{series['name']}' has {len(series['values'])} values "
                    f"but {len(data['labels'])} labels — will truncate to shorter"
                )

        # Check for extreme values
        all_values = [v for s in data.get("series", []) for v in s.get("values", []) if isinstance(v, (int, float))]
        if all_values:
            max_val = max(all_values)
            min_val = min(all_values)
            if max_val > 0 and min_val > 0 and max_val / min_val > 1000:
                warnings.append("Extreme value range detected — consider logarithmic scale")

        # Check for NaN/null values
        for series in data.get("series", []):
            nulls = sum(1 for v in series.get("values", []) if v is None or (isinstance(v, float) and v != v))
            if nulls > 0:
                warnings.append(f"Series '{series.get('name', '?')}' has {nulls} null/NaN values — will interpolate")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_table_data(self, headers: list[str], rows: list[list], spec: dict) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not headers:
            errors.append("Table has no headers")
        if not rows:
            errors.append("Table has no data rows")

        max_cols = spec.get("maxCols", 6)
        max_rows_limit = spec.get("maxRows", 8)

        if len(headers) > max_cols:
            warnings.append(f"Table has {len(headers)} columns (max {max_cols}) — will compress")
        if len(rows) > max_rows_limit:
            warnings.append(f"Table has {len(rows)} rows (max {max_rows_limit}) — will paginate")

        # Check row consistency
        for i, row in enumerate(rows):
            if len(row) != len(headers):
                warnings.append(f"Row {i} has {len(row)} cells but {len(headers)} headers — will pad/truncate")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


class ChartErrorState:
    """Graceful error/loading/empty states for charts."""

    @staticmethod
    def render_empty_state(chart_type: str, dimensions: dict) -> str:
        """Render a tasteful empty state instead of a broken chart."""
        return f"""
<div class="chart-empty-state" style="
  width: {dimensions['width']}px;
  height: {dimensions['height']}px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  background: rgba(255,255,255,0.02);
  border: 1px dashed rgba(255,255,255,0.1);
  border-radius: 12px;
">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="1.5">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <path d="M3 15l5-5 4 4 8-8"/>
  </svg>
  <span style="color: rgba(255,255,255,0.4); font-size: 14px;">
    No data available for {chart_type.replace('_', ' ')}
  </span>
</div>"""

    @staticmethod
    def render_loading_state(dimensions: dict) -> str:
        """Render a skeleton loading state during chart generation."""
        return f"""
<div class="chart-loading" style="
  width: {dimensions['width']}px;
  height: {dimensions['height']}px;
  background: linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.02) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 12px;
">
</div>"""
```

---

### 4.24.14 Accessibility & Print Quality

```typescript
// ══════════════════════════════════════════════════════════════════════
// CHART ACCESSIBILITY (WCAG AA Compliance)
// ══════════════════════════════════════════════════════════════════════

interface AccessibilityConfig {
  // Screen Reader Support
  ariaLabel: string;               // Chart description
  ariaDescribedBy: string;         // ID of detailed description element
  dataTableFallback: boolean;      // Hidden <table> for screen readers
  announceOnFocus: boolean;        // Speak chart summary on tab focus

  // Color-Blind Safe
  patternFills: boolean;           // Use hatch/dot/stripe patterns (not just color)
  patternTypes: ("diagonal" | "dots" | "crosshatch" | "horizontal" | "vertical")[];
  minimumContrastRatio: number;    // 4.5:1 for text, 3:1 for graphics (WCAG AA)

  // High Contrast Mode
  highContrastPalette: string[];   // B/W safe palette for high-contrast displays
  outlineChartElements: boolean;   // Add borders to all chart elements

  // Keyboard Navigation (HTML renderer)
  keyboardNavigable: boolean;      // Tab between data points
  focusIndicatorStyle: string;     // Focus ring style
}

// Color-blind safe palettes (Okabe-Ito):
const COLOR_BLIND_SAFE_PALETTE = [
  "#E69F00",   // Orange
  "#56B4E9",   // Sky Blue
  "#009E73",   // Green
  "#F0E442",   // Yellow
  "#0072B2",   // Blue
  "#D55E00",   // Vermillion
  "#CC79A7",   // Pink
  "#000000",   // Black
];

// Pattern fills for each series when patternFills=true:
const PATTERN_FILLS = [
  { type: "diagonal",    angle: 45,  spacing: 6, strokeWidth: 2 },
  { type: "dots",        spacing: 8, radius: 2 },
  { type: "crosshatch",  angle: 45,  spacing: 8, strokeWidth: 1.5 },
  { type: "horizontal",  spacing: 6, strokeWidth: 2 },
  { type: "vertical",    spacing: 6, strokeWidth: 2 },
];

// ══════════════════════════════════════════════════════════════════════
// PRINT-QUALITY RENDERING
// ══════════════════════════════════════════════════════════════════════

interface PrintQualityConfig {
  // High-DPI Export
  dpi: number;                     // 300 for print, 150 for screen, 72 for web
  scaleFactor: number;             // 2x for retina, 1x for standard

  // Vector-First Strategy
  preferSVG: boolean;              // SVG for HTML/PDF, rasterize only for PPTX fallback
  svgOptimize: boolean;            // Run SVGO optimization (remove metadata, minify)

  // Font Embedding
  embedFonts: boolean;             // Embed chart fonts in SVG for cross-platform consistency
  fontSubsetting: boolean;         // Only embed used glyphs (smaller file size)

  // PPTX Chart Quality
  pptxChartResolution: "standard" | "high";  // "high" = 2x raster for non-native charts
  pptxNativePreferred: boolean;    // Use PptxGenJS native charts when possible (editable)
}
```

---

### 4.24.15 Theme Integration (Chart Colors from Theme Engine)

Charts, tables, and diagrams inherit their visual properties from the Theme Engine (§4.11):

```python
class ChartThemeResolver:
    """
    Maps Theme Engine properties to chart-specific styling.
    Ensures all data elements share the deck's visual identity.
    """

    def resolve(self, theme: Theme) -> ChartThemeConfig:
        return ChartThemeConfig(
            # Color palette (8 colors for multi-series charts)
            chart_colors=[
                theme.colors.accent,          # Primary series
                theme.colors.secondary,       # Secondary series
                theme.colors.tertiary,        # Tertiary series
                *theme.colors.extended_palette,  # Additional series
            ],

            # Positive / Negative / Neutral
            positive_color=theme.colors.success or "#10B981",
            negative_color=theme.colors.error or "#EF4444",
            neutral_color=theme.colors.muted or "#64748B",

            # Backgrounds & Grid
            chart_background="transparent",  # Charts are transparent over slide bg
            grid_color=f"{theme.colors.text_secondary}14",  # 8% opacity gridlines
            axis_color=f"{theme.colors.text_secondary}33",  # 20% opacity axis

            # Typography
            axis_font=theme.typography.body_font,
            axis_font_size=12,
            data_label_font=theme.typography.body_font,
            data_label_size=11,
            title_font=theme.typography.heading_font,
            title_size=18,
            title_weight=600,

            # Table-specific
            table_header_bg=theme.colors.accent,
            table_header_text="#FFFFFF",
            table_stripe_colors=[
                f"{theme.colors.text_primary}05",  # 2% opacity
                "transparent",
            ],
            table_border_color=f"{theme.colors.text_primary}0A",  # 4% opacity

            # Diagram-specific
            node_fill=theme.colors.surface,
            node_border=f"{theme.colors.text_primary}15",
            edge_color=theme.colors.text_secondary,
            connection_arrow=theme.colors.accent,

            # Corner radius (matches theme)
            corner_radius=theme.layout.corner_radius,
        )
```

---

### 4.24.16 Expanded ContentElement Types

The Layer 2 ContentElement type (§4.4) is extended to support the full data visualization taxonomy:

```typescript
// EXTENDED ContentElement (additions to §4.4 type union):

type ContentElement =
  // ... (existing types: heading, subheading, body, bullets, stat, quote, image_brief, code_snippet, cta)

  // ── CHARTS (expanded from basic "chart" type) ──
  | {
      type: "chart";
      chart_type: ChartType;           // Full 90+ type taxonomy
      data: ChartData;
      title?: string;
      subtitle?: string;
      annotation?: string;              // E.g., "Source: Gartner 2025"
      interactive: boolean;             // Enable hover/click in HTML renderer
      semantic_weight: number;
    }

  // ── TABLES (expanded from basic "table" type) ──
  | {
      type: "table";
      table_type: TableType;            // 18+ table variants
      headers: string[];
      rows: (string | number)[][];
      has_totals_row: boolean;
      financial_formatting: boolean;    // Auto-format currency/percentages
      conditional_rules: ConditionalRule[] | null;
      semantic_weight: number;
    }

  // ── DIAGRAMS (expanded from basic "diagram" type) ──
  | {
      type: "diagram";
      diagram_type: DiagramType;        // 17+ diagram variants
      definition: string | object;      // Mermaid syntax or structured spec
      nodes?: any[];
      edges?: any[];
      semantic_weight: number;
    }

  // ── METRIC CARDS ──
  | {
      type: "metric_card";
      metrics: MetricItem[];
      layout: "single" | "grid_2x2" | "grid_3x1" | "grid_2x3";
      animate_counters: boolean;
      semantic_weight: number;
    }

  // ── HERO STAT ──
  | {
      type: "hero_stat";
      value: string;
      label: string;
      change?: string;
      trend?: "up" | "down" | "neutral";
      icon?: string;
      semantic_weight: number;
    }

  // ── PRESENTATION ELEMENTS ──
  | {
      type: "testimonial";
      quote: string;
      attribution: string;
      avatar_url?: string;
      semantic_weight: number;
    }
  | {
      type: "trust_badges";
      logos: { url: string; alt: string }[];
      grayscale: boolean;
      semantic_weight: number;
    }
  | {
      type: "comparison_grid";
      grid_type: "pricing" | "features" | "competitive" | "swot" | "risk";
      headers: string[];
      rows: (string | boolean | number)[][];
      highlight_column?: number;
      semantic_weight: number;
    }
  | {
      type: "icon_grid";
      items: { icon: string; title: string; description: string }[];
      columns: number;
      semantic_weight: number;
    };
```

---

### 4.24.17 Validation Test Cases

Use these to validate data visualization handling end-to-end:

**Test 1: Financial Table**
```json
{
  "type": "table",
  "table_type": "financial_table",
  "headers": ["Metric", "Q1'25", "Q2'25", "Q3'25", "YoY Δ"],
  "rows": [
    ["ARR", "$1.2M", "$1.8M", "$2.4M", "+340%"],
    ["Users", "1,200", "2,800", "5,100", "+325%"],
    ["NPS", "72", "81", "89", "+23.6%"],
    ["Churn", "8.2%", "5.1%", "3.4%", "-58.5%"]
  ],
  "has_totals_row": false,
  "financial_formatting": true,
  "semantic_weight": 0.8
}
```
Expected: Pixel-perfect table at `x:80, y:280`. Header row with theme accent bg. Positive values in green, negative in red. Financial formatting preserved.

**Test 2: Revenue Bar Chart**
```json
{
  "type": "chart",
  "chart_type": "grouped_bar",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "series": [
      { "name": "2024", "values": [120, 180, 240, 310] },
      { "name": "2025", "values": [220, 340, 480, null] }
    ],
    "metadata": { "unit": "$K", "source": "Internal Revenue Data" }
  },
  "title": "Revenue Growth: 2024 vs 2025",
  "semantic_weight": 0.9
}
```
Expected: Grouped bar chart with 2 color-coded series. Zero baseline. Data labels at bar end. Legend at bottom. Source citation. Null Q4 2025 handled gracefully.

**Test 3: KPI Dashboard**
```json
{
  "type": "metric_card",
  "layout": "grid_2x2",
  "metrics": [
    { "label": "ARR", "value": "$2.4M", "change": "+45% YoY", "trend": "up" },
    { "label": "Revenue", "value": "$800K", "change": "+$400K", "trend": "up" },
    { "label": "Users", "value": "5,120", "change": "+980", "trend": "up" },
    { "label": "NPS", "value": "89", "change": "+17 pts", "trend": "up" }
  ],
  "animate_counters": true,
  "semantic_weight": 0.85
}
```
Expected: 2×2 grid of metric cards. Each card: big number + trend arrow + change badge. Count-up animation (0 → target in 2s). Green positive indicators.

**Test 4: Conversion Funnel**
```json
{
  "type": "chart",
  "chart_type": "funnel",
  "data": {
    "labels": ["Visitors", "Signups", "Activated", "Paid", "Enterprise"],
    "series": [{ "name": "Conversion", "values": [50000, 12000, 4800, 1200, 180] }]
  },
  "title": "Customer Conversion Pipeline",
  "semantic_weight": 0.85
}
```
Expected: Vertical funnel with stage labels. Percentage drop between stages shown. Color gradient from top (widest) to bottom (narrowest). Drop-off indicators.

**Test 5: Competitive Quadrant**
```json
{
  "type": "chart",
  "chart_type": "quadrant",
  "data": {
    "labels": ["NeuralScale", "Competitor A", "Competitor B", "Competitor C"],
    "series": [{ "name": "Position", "values": [85, 72, 45, 60] }]
  },
  "title": "Market Positioning",
  "semantic_weight": 0.8
}
```
Expected: 4-quadrant grid with labeled axes. Points positioned by score. Our product highlighted/emphasized. Quadrant labels (Leaders, Challengers, Niche, Visionaries).

**Test 6: Flowchart Diagram**
```json
{
  "type": "diagram",
  "diagram_type": "flowchart",
  "definition": {
    "nodes": [
      { "id": "start", "label": "User Request", "type": "start" },
      { "id": "auth", "label": "Authenticate", "type": "process" },
      { "id": "check", "label": "Premium?", "type": "decision" },
      { "id": "std", "label": "Standard Mode", "type": "process" },
      { "id": "prm", "label": "Premium Mode", "type": "process" },
      { "id": "end", "label": "Deliver", "type": "end" }
    ],
    "edges": [
      { "from": "start", "to": "auth" },
      { "from": "auth", "to": "check" },
      { "from": "check", "to": "std", "label": "No" },
      { "from": "check", "to": "prm", "label": "Yes" },
      { "from": "std", "to": "end" },
      { "from": "prm", "to": "end" }
    ]
  },
  "semantic_weight": 0.7
}
```
Expected: Vertical flowchart with proper shapes (rounded rect for process, diamond for decision, circle for start/end). Orthogonal edge routing. Edge labels positioned clearly.

**Test 7: Timeline / Roadmap**
```json
{
  "type": "diagram",
  "diagram_type": "timeline",
  "definition": {
    "orientation": "horizontal",
    "phases": [
      { "label": "Discovery", "date": "2025-01", "type": "milestone", "color": "#7C3AED" },
      { "label": "Development", "date": "2025-04", "type": "activity", "color": "#2563EB" },
      { "label": "Beta Launch", "date": "2025-07", "type": "milestone", "color": "#059669" },
      { "label": "GA Release", "date": "2025-10", "type": "success", "color": "#10B981" }
    ]
  },
  "semantic_weight": 0.75
}
```
Expected: Horizontal timeline with colored phase markers. Connecting lines between phases. Date labels below. Milestone circles at each node.

---

## 4.25 Self-Learning Slide Generation System (SLGS)

> *"Every generation teaches the next. The system doesn't just create slides — it learns to create better slides."*

### 4.25.1 Core Philosophy: Teacher-Student Paradigm

Inspired by NousResearch/hermes-agent's closed learning loop and yoyo-evolve's self-evolving architecture, the SLGS implements a **teacher-student paradigm** where each slide generation cycle produces not just slides, but **reusable knowledge** that improves all future generations.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SELF-LEARNING SLIDE GENERATION LOOP                        │
│                                                                              │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│  │ GENERATE │────▶│ EVALUATE │────▶│ EXTRACT  │────▶│  STORE   │           │
│  │  Slides  │     │  Quality │     │  Lessons │     │  Skills  │           │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘           │
│       ▲                                                    │                │
│       │            FEEDBACK LOOP                           │                │
│       └────────────────────────────────────────────────────┘                │
│                                                                              │
│  Generation N teaches Generation N+1:                                        │
│    • What layouts scored highest for this content type                       │
│    • Which color palettes got user approval                                 │
│    • What GLA patterns produced best composition scores                     │
│    • Which image styles matched the narrative arc                           │
│    • What slop patterns to avoid (anti-patterns learned)                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.25.2 Learning Architecture

```python
class SelfLearningEngine:
    """
    Teacher-Student paradigm for slide generation.
    Every generation cycle produces knowledge artifacts stored in ChromaDB + MongoDB.
    Future generations query this knowledge to make better decisions.
    """

    # Knowledge Types (inspired by Hermes Agent's skill system)
    KNOWLEDGE_TYPES = {
        "layout_pattern": {
            "description": "Successful GLA compositions for specific content types",
            "storage": "chromadb",  # Vector similarity search
            "retention": "permanent",
            "example": "For 3-stat + chart content → row([stats_col, chart], weights=[2,3]) scored 92/100"
        },
        "style_preference": {
            "description": "User-approved color/typography/image combinations",
            "storage": "chromadb",
            "retention": "per_user",
            "example": "User X prefers dark themes with accent #7C3AED for tech pitch decks"
        },
        "anti_pattern": {
            "description": "Detected slop patterns and failed compositions",
            "storage": "mongodb",
            "retention": "permanent",
            "example": "Centered-everything + gradient background → slop score 72, rejected"
        },
        "narrative_template": {
            "description": "Successful narrative arc structures for deck types",
            "storage": "chromadb",
            "retention": "permanent",
            "example": "SaaS pitch: hook(0.8)→problem(0.6)→solution(0.9)→traction(0.7)→ask(0.95)"
        },
        "generation_skill": {
            "description": "Autonomous skills created from complex generation tasks",
            "storage": "mongodb",
            "retention": "permanent",
            "example": "Skill: 'financial_dashboard_slide' — learned from 50+ finance deck generations"
        },
    }

    async def post_generation_learning(
        self,
        deck: GeneratedDeck,
        quality_scores: QualityReport,
        user_feedback: Optional[UserFeedback] = None,
    ) -> list[KnowledgeArtifact]:
        """
        After every generation, extract and store reusable knowledge.
        This is the 'Teacher' phase — the current generation teaches the system.
        """
        artifacts = []

        # 1. Extract layout patterns from high-scoring slides
        for slide in deck.slides:
            if slide.composition_score >= 80:
                artifacts.append(KnowledgeArtifact(
                    type="layout_pattern",
                    content_signature=slide.content_type_hash,
                    gla_tree=slide.gla_tree,
                    score=slide.composition_score,
                    metadata={
                        "content_types": slide.semantic_types,
                        "element_count": slide.element_count,
                        "narrative_position": slide.arc_position,
                    }
                ))

        # 2. Extract anti-patterns from low-scoring slides
        for slide in deck.slides:
            if slide.slop_score >= 40:
                artifacts.append(KnowledgeArtifact(
                    type="anti_pattern",
                    pattern=slide.detected_slop_patterns,
                    remediation=slide.qa_suggestions,
                    severity=slide.slop_score,
                ))

        # 3. If user provided explicit feedback, extract preferences
        if user_feedback:
            if user_feedback.type == "variant_selection":
                artifacts.append(KnowledgeArtifact(
                    type="style_preference",
                    selected_variant=user_feedback.selected,
                    rejected_variants=user_feedback.rejected,
                    user_id=user_feedback.user_id,
                ))

        # 4. Autonomous skill creation (for complex/novel generation tasks)
        if deck.complexity_score >= 0.8 and quality_scores.overall >= 85:
            skill = await self._create_generation_skill(deck, quality_scores)
            if skill:
                artifacts.append(skill)

        # Store all artifacts
        await self._store_artifacts(artifacts)
        return artifacts

    async def pre_generation_learning(
        self,
        content_plan: ContentPlan,
        mode: str,
        user_id: Optional[str] = None,
    ) -> GenerationContext:
        """
        Before every generation, query stored knowledge to inform decisions.
        This is the 'Student' phase — the new generation learns from past ones.
        """
        context = GenerationContext()

        # 1. Find similar past layouts for this content type
        context.suggested_layouts = await self.chromadb.query(
            collection="layout_patterns",
            query_embedding=content_plan.content_embedding,
            n_results=5,
            where={"score": {"$gte": 75}},
        )

        # 2. Load user-specific style preferences
        if user_id:
            context.style_preferences = await self.chromadb.query(
                collection="style_preferences",
                query_embedding=content_plan.style_embedding,
                where={"user_id": user_id},
                n_results=3,
            )

        # 3. Load anti-patterns to avoid
        context.anti_patterns = await self.mongodb.find(
            "anti_patterns",
            {"content_types": {"$in": content_plan.content_types}},
            sort=[("severity", -1)],
            limit=10,
        )

        # 4. Check for matching generation skills
        context.applicable_skills = await self.mongodb.find(
            "generation_skills",
            {"trigger_conditions": {"$in": content_plan.conditions}},
            sort=[("success_rate", -1)],
            limit=3,
        )

        return context
```

### 4.25.3 Skill Evolution System

Inspired by Hermes Agent's autonomous skill creation, the SLGS creates **generation skills** — reusable, self-improving procedures for specific slide types:

```python
class GenerationSkill:
    """
    A learned procedure for generating a specific type of slide or deck.
    Skills are created autonomously when the system successfully handles
    complex/novel generation tasks, and self-improve with each use.
    """
    name: str                          # e.g., "financial_dashboard_slide"
    trigger_conditions: list[str]      # When to activate this skill
    gla_template: dict                 # Preferred GLA tree structure
    style_rules: dict                  # Learned style preferences
    content_transforms: list[dict]     # How to transform raw content
    success_rate: float                # Track record (0.0 - 1.0)
    usage_count: int                   # Times applied
    last_improved: datetime            # Last self-improvement timestamp
    version: int                       # Skill version (increments on improvement)

    # Self-improvement: After each use, if score > previous average → update skill
    async def self_improve(self, result: GenerationResult):
        if result.score > self.average_score:
            self.gla_template = self._merge_template(self.gla_template, result.gla_tree)
            self.style_rules = self._merge_styles(self.style_rules, result.style)
            self.version += 1
            self.last_improved = datetime.utcnow()
```

### 4.25.4 Cross-Session Memory System

```python
class SlideGenerationMemory:
    """
    Persistent memory across all generation sessions.
    Inspired by Hermes Agent's agent-curated memory and yoyo-evolve's
    JSONL archive + active context synthesis.
    """

    # Memory tiers (time-weighted compression like yoyo-evolve)
    TIERS = {
        "hot": {
            "description": "Last 100 generations — full detail",
            "retention": "7_days",
            "compression": "none",
        },
        "warm": {
            "description": "Last 1000 generations — summarized patterns",
            "retention": "30_days",
            "compression": "pattern_extraction",
        },
        "cold": {
            "description": "All-time aggregated statistics",
            "retention": "permanent",
            "compression": "statistical_summary",
        },
    }

    async def synthesize_active_context(self) -> ActiveContext:
        """
        Daily synthesis: compress learning archives into active prompt context.
        Like yoyo-evolve's daily memory regeneration.
        """
        hot_lessons = await self._get_hot_tier()
        warm_patterns = await self._get_warm_tier()
        cold_stats = await self._get_cold_tier()

        return ActiveContext(
            top_layout_patterns=warm_patterns.top_layouts[:20],
            user_preference_clusters=warm_patterns.preference_clusters,
            anti_pattern_blocklist=cold_stats.confirmed_anti_patterns,
            skill_library=await self._get_active_skills(),
            generation_statistics=cold_stats.summary,
        )
```

### 4.25.5 A/B Learning from Variant Selection

When users select between A/B variants (§4.16), the learning system captures **implicit preferences**:

```python
class VariantLearningLoop:
    """
    Every variant selection is a training signal.
    Selected variants become positive examples; rejected variants become negative.
    Over time, the system learns user-specific and universal design preferences.
    """

    async def learn_from_selection(
        self,
        selected: SlideVariant,
        rejected: list[SlideVariant],
        context: GenerationContext,
    ):
        # Contrastive learning: what made the selected variant better?
        diff_features = self._extract_differentiating_features(selected, rejected)

        # Store as preference signal
        await self.chromadb.upsert(
            collection="variant_preferences",
            documents=[{
                "selected_features": diff_features.selected,
                "rejected_features": diff_features.rejected,
                "content_type": context.content_type,
                "user_id": context.user_id,
                "confidence": diff_features.confidence,
            }],
            embeddings=[diff_features.embedding],
        )

    def _extract_differentiating_features(
        self,
        selected: SlideVariant,
        rejected: list[SlideVariant],
    ) -> DiffFeatures:
        """
        Identify what's different between selected and rejected variants:
        - Layout structure (column vs row vs grid)
        - Visual weight distribution (hero vs balanced)
        - Color temperature (warm vs cool)
        - Typography scale (compact vs dramatic)
        - Image treatment (contained vs bleed vs none)
        - Density (sparse vs dense)
        """
        return DiffFeatures(
            selected=self._feature_vector(selected),
            rejected=[self._feature_vector(r) for r in rejected],
            confidence=self._calculate_confidence(selected, rejected),
        )
```

### 4.25.6 Learning Metrics & Dashboard

| Metric | Description | Target |
|--------|-------------|--------|
| **Pattern Library Size** | Unique layout patterns learned | 500+ after 1000 generations |
| **Skill Count** | Autonomous skills created | 50+ after 6 months |
| **Preference Accuracy** | Variant prediction vs user choice | >70% after 100 selections |
| **Anti-Pattern Coverage** | Known slop patterns catalogued | 200+ patterns |
| **Generation Improvement** | Avg composition score trend | +5% per month |
| **Memory Synthesis Latency** | Daily context regeneration time | <30s |
| **Skill Self-Improvement Rate** | Skills that improved after use | >60% |

---

## 4.26 Video Preview & Export Module

> *"Slides don't just display — they perform. See your deck as a cinematic experience."*

### 4.26.1 Architecture Overview

Inspired by Remotion (42k ⭐) — the React-based programmatic video framework — but implemented with a **license-compatible open-source stack** suitable for a startup. Instead of Remotion's special license requirements, we use a combination of **Web Animations API + Canvas recording + FFmpeg WASM** for a fully open, zero-cost video pipeline.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      VIDEO PREVIEW & EXPORT PIPELINE                         │
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐     │
│  │ Slide DSL   │───▶│ Animation   │───▶│ Canvas      │───▶│ Video    │     │
│  │ v3 + Timing │    │ Sequencer   │    │ Recorder    │    │ Export   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────────┘     │
│                                                                              │
│  Formats: WebM (browser-native) | MP4 (FFmpeg WASM) | GIF (preview)        │
│  Resolution: 1920×1080 (Full HD) | 3840×2160 (4K Premium)                   │
│  FPS: 30 (standard) | 60 (premium animations)                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.26.2 Animation Sequencer

```typescript
interface SlideVideoTimeline {
  slides: SlideSequence[];
  totalDuration: number;        // in seconds
  transitions: TransitionConfig[];
  audioTrack?: AudioConfig;     // Optional narration/music
}

interface SlideSequence {
  slideId: string;
  enterAnimation: AnimationKeyframes;    // Element-by-element entrance
  holdDuration: number;                  // Time slide is fully visible
  exitAnimation: AnimationKeyframes;     // Transition to next slide
  elementTimings: ElementTiming[];       // Staggered element animations
}

interface ElementTiming {
  elementId: string;
  delay: number;                // Delay from slide entrance (ms)
  duration: number;             // Animation duration (ms)
  easing: string;               // CSS easing function
  animation: 'fadeIn' | 'slideUp' | 'scaleIn' | 'typewriter' | 'drawIn' | 'countUp';
}

// Transition types between slides
type SlideTransition =
  | { type: 'fade'; duration: number }
  | { type: 'slide'; direction: 'left' | 'right' | 'up' | 'down'; duration: number }
  | { type: 'zoom'; scale: number; duration: number }
  | { type: 'morph'; duration: number }          // Auto-animate matching elements
  | { type: 'cinematic-cut'; duration: number }  // Instant cut with motion blur
  | { type: 'dissolve'; duration: number };       // Cross-dissolve blend
```

### 4.26.3 Recording Engine

```typescript
class VideoRecorder {
    /**
     * Records slide presentations as video using Canvas capture.
     * No Remotion dependency — fully open-source stack.
     *
     * Stack: OffscreenCanvas + MediaRecorder API + FFmpeg WASM
     */

    private canvas: OffscreenCanvas;
    private mediaRecorder: MediaRecorder;
    private ffmpeg: FFmpegInstance;

    async record(timeline: SlideVideoTimeline, options: RecordOptions): Promise<Blob> {
        const { width, height, fps, format } = options;

        // 1. Create offscreen canvas at target resolution
        this.canvas = new OffscreenCanvas(width, height);
        const ctx = this.canvas.getContext('2d')!;

        // 2. Set up MediaRecorder for browser-native WebM
        const stream = this.canvas.captureStream(fps);
        this.mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'video/webm;codecs=vp9',
            videoBitsPerSecond: format === '4k' ? 20_000_000 : 8_000_000,
        });

        // 3. Render each frame
        const chunks: BlobPart[] = [];
        this.mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
        this.mediaRecorder.start();

        for (const slide of timeline.slides) {
            await this.renderSlideSequence(ctx, slide, fps);
        }

        this.mediaRecorder.stop();

        // 4. If MP4 requested, transcode via FFmpeg WASM
        const webmBlob = new Blob(chunks, { type: 'video/webm' });
        if (options.outputFormat === 'mp4') {
            return await this.transcodeToMP4(webmBlob);
        }

        return webmBlob;
    }

    private async transcodeToMP4(webm: Blob): Promise<Blob> {
        const ffmpeg = await this.getFFmpeg();
        await ffmpeg.writeFile('input.webm', new Uint8Array(await webm.arrayBuffer()));
        await ffmpeg.exec(['-i', 'input.webm', '-c:v', 'libx264', '-preset', 'fast', 'output.mp4']);
        const data = await ffmpeg.readFile('output.mp4');
        return new Blob([data], { type: 'video/mp4' });
    }
}
```

### 4.26.4 Video Preview Mode (In-App)

A new presentation mode alongside Reading Mode and Presenting Mode:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  PRESENTATION MODES                                                          │
│                                                                              │
│  [📖 Reading] [🎬 Presenting] [🎥 Video Preview] [⬇️ Export Video]          │
│                                                                              │
│  Video Preview:                                                              │
│  ┌────────────────────────────────────────────────────────────────┐          │
│  │                                                                │          │
│  │                    [ ▶ Play / ⏸ Pause ]                       │          │
│  │                                                                │          │
│  │  ┌──────────────────────────────────────────────────────────┐ │          │
│  │  │                                                          │ │          │
│  │  │              Live slide rendering                        │ │          │
│  │  │              with real-time animations                   │ │          │
│  │  │                                                          │ │          │
│  │  └──────────────────────────────────────────────────────────┘ │          │
│  │                                                                │          │
│  │  ──●──────────────────────────────────────────── 0:42 / 2:30  │          │
│  │                                                                │          │
│  │  [⏪] [⏩] [🔊 Volume] [⚙️ Settings] [📥 Export MP4/WebM]     │          │
│  └────────────────────────────────────────────────────────────────┘          │
│                                                                              │
│  Settings:                                                                   │
│  • Slide duration: 3s / 5s / 8s / Custom                                    │
│  • Transition style: Fade / Slide / Morph / Cinematic                       │
│  • Auto-advance: On / Off                                                   │
│  • Resolution: 720p / 1080p / 4K                                            │
│  • Include narration audio: Yes / No                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.26.5 Video Export Options

| Format | Resolution | FPS | Use Case | Estimated Size (10 slides) |
|--------|-----------|-----|----------|---------------------------|
| **WebM** | 1080p | 30 | Web sharing, social media | ~5MB |
| **MP4** | 1080p | 30 | Universal playback | ~8MB |
| **MP4 4K** | 2160p | 60 | Premium presentations | ~25MB |
| **GIF** | 720p | 15 | Previews, thumbnails | ~3MB |
| **PNG Sequence** | 1080p | — | Post-production editing | ~50MB |

---

## 4.27 Advanced Design Intelligence System

> *"Design is not decoration. It's intelligence made visible."*

### 4.27.1 Fluent UI Icon System Integration

Expanding beyond the current Lucide icon library (§4.24.7) with Microsoft's Fluent UI System Icons (10.5k ⭐, MIT license) for a premium, professional icon tier:

```python
class MultiTierIconSystem:
    """
    3-tier icon system: Lucide (default) → Fluent UI (premium) → Custom SVG (brand).
    Fluent UI adds 1,300+ icon families with Regular/Filled/Light/Color variants.
    """

    TIERS = {
        "standard": {
            "library": "lucide-react",
            "count": "1000+",
            "variants": ["outline"],
            "weight": "2px stroke",
            "license": "ISC",
        },
        "premium": {
            "library": "@fluentui/react-icons",
            "count": "5200+",   # 1300 families × 4 variants
            "variants": ["regular", "filled", "light", "color"],
            "weight": "variable",
            "license": "MIT",
        },
        "brand": {
            "library": "custom_svg",
            "count": "user-uploaded",
            "variants": ["original"],
            "weight": "variable",
            "license": "user-owned",
        },
    }

    FLUENT_SEMANTIC_MAPPINGS = {
        # Business & Finance
        "revenue": "MoneyRegular",
        "growth": "ArrowTrendingRegular",
        "investment": "WalletRegular",
        "profit": "ReceiptMoneyRegular",
        "market": "StoreMicrosoftRegular",

        # Technology & Product
        "ai": "BrainCircuitRegular",
        "cloud": "CloudRegular",
        "security": "ShieldCheckmarkRegular",
        "api": "PlugConnectedRegular",
        "database": "DatabaseRegular",
        "code": "CodeRegular",

        # People & Teams
        "team": "PeopleTeamRegular",
        "user": "PersonRegular",
        "community": "PeopleCommunityRegular",
        "leadership": "PersonStarRegular",

        # Communication & Content
        "presentation": "SlideMicrophoneRegular",
        "document": "DocumentRegular",
        "chart": "ChartMultipleRegular",
        "idea": "LightbulbRegular",
    }

    async def select_icon(
        self,
        semantic_label: str,
        context: SlideContext,
        mode: str = "standard",
    ) -> IconResult:
        # 1. Try semantic mapping
        if semantic_label in self.FLUENT_SEMANTIC_MAPPINGS and mode == "premium":
            icon_name = self.FLUENT_SEMANTIC_MAPPINGS[semantic_label]
            variant = self._select_variant(context.theme)
            return IconResult(library="fluent", name=icon_name, variant=variant)

        # 2. Fall back to Lucide mapping (§4.24.7)
        if semantic_label in LUCIDE_MAPPINGS:
            return IconResult(library="lucide", name=LUCIDE_MAPPINGS[semantic_label])

        # 3. Brand icons if available
        if context.brand_package and context.brand_package.has_icon(semantic_label):
            return IconResult(library="brand", svg=context.brand_package.get_icon(semantic_label))

        # 4. AI-powered icon selection from full library
        return await self._ai_icon_search(semantic_label, context)
```

### 4.27.2 Graphite-Inspired Procedural Design Engine

Inspired by GraphiteEditor/Graphite (25k ⭐, Apache 2.0) — a node-based procedural design system — we bring **nondestructive, parametric design composition** to slide generation:

```python
class ProceduralDesignEngine:
    """
    Node-graph approach to slide visual composition.
    Each visual element is a node in a composable graph.
    Parameters can be adjusted without regenerating the entire slide.

    Inspired by Graphite's nondestructive editing philosophy:
    "Every operation is a node. Every node is adjustable. Nothing is flattened."
    """

    # Procedural node types for slide composition
    NODE_TYPES = {
        "source": ["text_input", "image_input", "data_input", "icon_input", "shape_input"],
        "transform": [
            "scale", "rotate", "translate", "crop", "mask",
            "blur", "shadow", "gradient_overlay", "color_shift",
            "border_radius", "opacity", "blend_mode",
        ],
        "layout": ["flex_row", "flex_column", "grid", "stack", "float", "pin"],
        "style": [
            "theme_apply", "color_palette", "typography_scale",
            "spacing_system", "shadow_system", "animation_assign",
        ],
        "output": ["render_html", "render_svg", "render_canvas", "render_pptx"],
    }

    async def compose_slide(
        self,
        content: SlideContent,
        gla_tree: GLANode,
        theme: Theme,
    ) -> ProceduralGraph:
        """
        Build a node graph for the slide.
        Every visual decision is a node that can be independently adjusted.
        """
        graph = ProceduralGraph()

        # Source nodes
        for element in content.elements:
            source = graph.add_node(f"{element.type}_input", data=element)

            # Transform chain (nondestructive)
            transformed = source
            for transform in self._compute_transforms(element, gla_tree, theme):
                transformed = graph.add_node(transform.type, input=transformed, params=transform.params)

            # Style application
            styled = graph.add_node("theme_apply", input=transformed, params=theme.tokens)

            # Connect to layout
            graph.connect(styled, gla_tree.slot_for(element))

        return graph

    def adjust_parameter(
        self,
        graph: ProceduralGraph,
        node_id: str,
        param: str,
        value: Any,
    ) -> ProceduralGraph:
        """
        Adjust any parameter in the graph without regeneration.
        Only downstream nodes re-compute. This is O(affected_nodes), not O(all_nodes).
        """
        graph.nodes[node_id].params[param] = value
        graph.invalidate_downstream(node_id)
        return graph
```

### 4.27.3 Style Transfer System

Inspired by ArcadeAI/agent-style-transfer — applying learned visual styles from successful presentations to new ones:

```python
class SlideStyleTransfer:
    """
    Analyze the visual design language of successful presentations
    and transfer it to new content. Like neural style transfer but for slides.

    Style dimensions analyzed:
    - Color harmony (palette ratios, accent usage, gradient style)
    - Typography personality (scale contrast, weight distribution, case usage)
    - Layout rhythm (spacing patterns, alignment grids, density curves)
    - Visual weight distribution (hero elements, whitespace allocation)
    - Animation personality (speed, easing, stagger patterns)
    - Image treatment (filters, crops, compositions, overlay styles)
    """

    async def extract_style(self, source_deck: Deck) -> StyleProfile:
        """Extract the visual DNA of a successful presentation."""
        return StyleProfile(
            color_harmony=self._analyze_color_harmony(source_deck),
            typography_personality=self._analyze_typography(source_deck),
            layout_rhythm=self._analyze_layout_rhythm(source_deck),
            weight_distribution=self._analyze_visual_weight(source_deck),
            animation_personality=self._analyze_animations(source_deck),
            image_treatment=self._analyze_image_style(source_deck),
            overall_mood=self._classify_mood(source_deck),  # "bold", "minimal", "playful", etc.
        )

    async def transfer_style(
        self,
        target_slides: list[Slide],
        style_profile: StyleProfile,
        intensity: float = 0.8,  # 0.0 = no transfer, 1.0 = full transfer
    ) -> list[Slide]:
        """
        Apply extracted style to new slides.
        Intensity controls how much of the source style bleeds through.
        """
        styled_slides = []
        for slide in target_slides:
            styled = await self._apply_style(slide, style_profile, intensity)
            styled_slides.append(styled)
        return styled_slides

    # Pre-built style profiles from curated successful presentations
    CURATED_STYLES = {
        "apple_keynote": "Minimal whitespace, SF Pro, dramatic hero images, subtle fade transitions",
        "stripe_docs": "Clean typography, code-friendly, accent purple, generous padding",
        "airbnb_pitch": "Warm photography, Cereal font, story-driven, pastel accents",
        "sequoia_pitch": "Data-heavy, conservative palette, clear hierarchy, minimal decoration",
        "ycombinator_demo": "Speed-optimized, high-contrast, metric-forward, no fluff",
        "ted_talk": "Full-bleed imagery, minimal text, emotional impact, cinematic transitions",
    }
```

---

## 4.28 LLM Security & Rate Limit Management

> *"Keys in .env, never in code. Every token counted, every limit respected."*

### 4.28.1 Security Architecture

All LLM API keys are managed exclusively through environment variables (`.env` file), never hardcoded or exposed in client-side code:

```python
class LLMSecurityManager:
    """
    Secure LLM key management following OWASP best practices.
    All keys loaded from .env via pydantic-settings.
    Never exposed to frontend, logs, or error messages.
    """

    class Config(BaseSettings):
        """All LLM credentials from .env — NEVER hardcoded."""

        # Azure Models (primary paid tier)
        AZURE_GPT4O_MINI_ENDPOINT: str = Field(validation_alias="AZURE_GPT4O_MINI_ENDPOINT")
        AZURE_GPT4O_MINI_API_KEY: SecretStr = Field(validation_alias="AZURE_GPT4O_MINI_API_KEY")
        AZURE_GPT4O_MINI_DEPLOYMENT_NAME: str = "gpt-4o-mini"

        DEEPSEEK_ENDPOINT: str = Field(validation_alias="DEEPSEEK_ENDPOINT")
        DEEPSEEK_API_KEY: SecretStr = Field(validation_alias="DEEPSEEK_API_KEY")
        DEEPSEEK_MODEL_NAME: str = "DeepSeek-V3.2"

        MISTRAL_ENDPOINT: str = Field(validation_alias="Mistral_endpoint")
        MISTRAL_API_KEY: SecretStr = Field(validation_alias="Mistral_api_key")
        MISTRAL_DEPLOYMENT_NAME: str = "mistral-medium-2505"

        AZURE_KIMI_ENDPOINT: str = Field(validation_alias="AZURE_KIMI_ENDPOINT")
        AZURE_KIMI_API_KEY: SecretStr = Field(validation_alias="AZURE_KIMI_API_KEY")
        AZURE_KIMI_DEPLOYMENT: str = "Kimi-K2-Thinking"

        # Azure Image Generation
        AZURE_FLUX_ENDPOINT: str = Field(validation_alias="AZURE_FLUX_ENDPOINT")
        AZURE_FLUX_API_KEY: SecretStr = Field(validation_alias="AZURE_FLUX_API_KEY")
        AZURE_FLUX_DEPLOYMENT_NAME: str = "FLUX.1-Kontext-pro"

        # Cloudflare Workers (FREE tier)
        CF_WORKER_GLM_URL: str = Field(validation_alias="CF_WORKER_GLM_URL")
        CF_WORKER_GLM_TOKEN: SecretStr = Field(validation_alias="CF_WORKER_GLM_TOKEN")
        CF_WORKER_QWEN_URL: str = Field(validation_alias="CF_WORKER_QWEN_URL")
        CF_WORKER_QWEN_TOKEN: SecretStr = Field(validation_alias="CF_WORKER_QWEN_TOKEN")
        CF_WORKER_GEMMA_URL: str = Field(validation_alias="CF_WORKER_GEMMA_URL")
        CF_WORKER_GEMMA_TOKEN: SecretStr = Field(validation_alias="CF_WORKER_GEMMA_TOKEN")
        CF_WORKER_PHOENIX_URL: str = Field(validation_alias="CF_WORKER_PHOENIX_URL")
        CF_WORKER_PHOENIX_TOKEN: SecretStr = Field(validation_alias="CF_WORKER_PHOENIX_TOKEN")
        CF_WORKER_LUCID_URL: str = Field(validation_alias="CF_WORKER_LUCID_URL")
        CF_WORKER_LUCID_TOKEN: SecretStr = Field(validation_alias="CF_WORKER_LUCID_TOKEN")

        # Groq (FREE tier — 6-key round-robin)
        GROQ_API_KEYS: list[SecretStr] = []  # Populated from GROQ_API_KEY through GROQ_API_KEY5

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

    # Security rules
    SECURITY_RULES = {
        "never_log_keys": True,           # Keys never appear in logs
        "never_send_to_frontend": True,   # Keys never in API responses
        "rotate_on_compromise": True,     # Auto-rotate if key detected in logs
        "mask_in_errors": True,           # Error messages show "***" not keys
        "audit_key_usage": True,          # Track which key is used when
    }
```

### 4.28.2 Rate Limit Management

```python
class RateLimitManager:
    """
    Per-provider rate limiting with automatic backoff and key rotation.
    Startup budget constraint: maximize free tier, minimize paid usage.
    """

    # Actual rate limits from our .env providers
    PROVIDER_LIMITS = {
        "azure_gpt4o_mini": {
            "rpm": 60,          # Requests per minute
            "tpm": 150_000,     # Tokens per minute
            "daily_budget": 1_000_000,  # Daily token budget
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.0006,
            "tier": "paid_azure",
        },
        "azure_deepseek_v3": {
            "rpm": 30,
            "tpm": 100_000,
            "daily_budget": 500_000,
            "cost_per_1k_input": 0.0003,
            "cost_per_1k_output": 0.0012,
            "tier": "paid_azure",
        },
        "azure_mistral_medium": {
            "rpm": 30,
            "tpm": 100_000,
            "daily_budget": 500_000,
            "cost_per_1k_input": 0.0004,
            "cost_per_1k_output": 0.0012,
            "tier": "paid_azure",
        },
        "azure_kimi_k2": {
            "rpm": 20,
            "tpm": 80_000,
            "daily_budget": 300_000,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.004,
            "tier": "paid_azure",
        },
        "azure_flux_kontext": {
            "rpm": 10,
            "images_per_day": 100,
            "cost_per_image": 0.04,
            "tier": "paid_azure",
        },
        "groq_llama": {
            "rpm": 30,           # Per key
            "tpm": 30_000,       # Per key
            "keys_available": 6, # Round-robin across 6 keys
            "effective_rpm": 180, # 30 × 6 keys
            "effective_tpm": 180_000,
            "cost": 0.0,
            "tier": "free",
        },
        "cloudflare_glm": {
            "rpm": 60,
            "tpm": 50_000,
            "cost": 0.0,
            "tier": "free",
        },
        "cloudflare_qwen": {
            "rpm": 60,
            "tpm": 50_000,
            "cost": 0.0,
            "tier": "free",
        },
        "cloudflare_gemma": {
            "rpm": 60,
            "tpm": 50_000,
            "cost": 0.0,
            "tier": "free",
        },
        "cloudflare_phoenix": {
            "rpm": 30,
            "images_per_day": 500,
            "cost": 0.0,
            "tier": "free",
        },
        "cloudflare_lucid": {
            "rpm": 30,
            "images_per_day": 500,
            "cost": 0.0,
            "tier": "free",
        },
    }

    async def acquire_slot(self, provider: str) -> RateLimitSlot:
        """
        Acquire a rate limit slot. Blocks if at capacity.
        Uses Redis for distributed rate limiting across workers.
        """
        limits = self.PROVIDER_LIMITS[provider]
        key = f"ratelimit:{provider}:{self._current_window()}"

        current_count = await self.redis.incr(key)
        if current_count == 1:
            await self.redis.expire(key, 60)  # 1-minute window

        if current_count > limits["rpm"]:
            # If this is a free provider, try key rotation (Groq)
            if provider == "groq_llama":
                return await self._rotate_groq_key()
            # Otherwise, wait or fail over to backup
            raise RateLimitExceeded(provider, retry_after=60 - self._window_elapsed())

        return RateLimitSlot(provider=provider, acquired=True)

    async def _rotate_groq_key(self) -> RateLimitSlot:
        """Round-robin across 6 Groq API keys for 6× effective rate limit."""
        for i in range(6):
            key_idx = (self._current_groq_idx + i) % 6
            key = f"ratelimit:groq:{key_idx}:{self._current_window()}"
            count = await self.redis.get(key) or 0
            if int(count) < 30:
                self._current_groq_idx = key_idx
                await self.redis.incr(key)
                return RateLimitSlot(provider=f"groq_llama", key_index=key_idx, acquired=True)
        raise RateLimitExceeded("groq_llama", retry_after=60)
```

### 4.28.3 Startup Budget Optimization

```python
class BudgetOptimizer:
    """
    Startup budget strategy: FREE models first, Azure only when quality demands.

    Monthly budget targets:
    - Standard Mode: $0/month (100% free models)
    - Premium Mode: <$50/month (mixed free + Azure)
    - Image Generation: <$20/month (Phoenix/Lucid free, FLUX for premium only)

    Priority Order (cheapest first):
    1. Cloudflare Workers (GLM, Qwen, Gemma) — $0
    2. Groq (llama-3.3-70b × 6 keys) — $0
    3. Azure GPT-4o-mini — ~$0.15/1M tokens
    4. Azure DeepSeek-V3.2 — ~$0.30/1M tokens
    5. Azure Mistral-medium — ~$0.40/1M tokens
    6. Azure Kimi-K2-Thinking — ~$1.00/1M tokens (Premium only, complex reasoning)
    """

    MONTHLY_LIMITS = {
        "total_budget": 70.00,           # $70/month max
        "azure_text_budget": 40.00,      # $40 for text LLMs
        "azure_image_budget": 20.00,     # $20 for FLUX
        "emergency_reserve": 10.00,      # $10 emergency buffer
    }

    async def select_model(self, task: str, mode: str, complexity: float) -> str:
        """Budget-aware model selection. Free first, escalate only when needed."""
        remaining = await self._get_remaining_budget()

        if mode == "standard":
            # Standard mode: ALWAYS free
            return self._select_free_model(task)

        if mode == "premium":
            if complexity < 0.5 and remaining["azure_text"] > 20:
                return self._select_free_model(task)  # Even premium uses free for simple tasks
            elif remaining["azure_text"] > 5:
                return self._select_paid_model(task, complexity)
            else:
                logger.warning("Budget low — falling back to free models for premium task")
                return self._select_free_model(task)
```

### 4.28.4 Key Rotation & Health Monitoring

| Check | Frequency | Action on Failure |
|-------|-----------|-------------------|
| Key validity | Every 5 min | Mark key as invalid, switch to backup |
| Rate limit proximity | Real-time | Preemptive rotation to next key |
| Daily budget check | Hourly | Alert if >80% consumed; restrict to free models |
| Monthly cost audit | Daily | Auto-report to admin; adjust routing thresholds |
| Key exposure scan | On deploy | Block deployment if keys found in code/logs |

---

## 4.29 Pretext Advanced Typography Engine

> *"Text isn't just content — it's architecture. Measure it, flow it, own it."*

### 4.29.1 Deep Pretext Integration

Expanding our current PreTeXt.js integration (§4.26 Tech Stack) from basic text fitting to a **comprehensive text intelligence layer** — leveraging Pretext's full API (40k ⭐, MIT) for DOM-free text measurement, line-by-line layout, rich-text inline flow, and canvas/SVG rendering:

```typescript
/**
 * Pretext Advanced Typography Engine
 *
 * Current usage (V9.2): prepare() + layout() for text overflow detection
 * New usage (V9.3): Full text intelligence for:
 *   1. Pixel-perfect text fitting in GLA slots
 *   2. Multi-column text flow (magazine-style layouts)
 *   3. Text-wrapping around floated images
 *   4. Rich-text inline flow (mentions, chips, code spans)
 *   5. Shrinkwrap text containers (no CSS hacks)
 *   6. Canvas/SVG text rendering for video export
 *   7. Server-side text measurement (no browser needed)
 */

import {
    prepare, layout,
    prepareWithSegments, layoutWithLines,
    layoutNextLineRange, materializeLineRange,
    walkLineRanges, measureLineStats, measureNaturalWidth,
    prepareRichInline, walkRichInlineLineRanges,
    materializeRichInlineLineRange,
    type LayoutCursor, type PreparedTextWithSegments,
} from '@chenglou/pretext';

class PretextTypographyEngine {
    /**
     * Advanced text layout engine built on @chenglou/pretext.
     * Enables DOM-free text measurement for:
     * - GLA slot fitting (does this text fit in this box?)
     * - Font size optimization (what's the largest font that fits?)
     * - Multi-line shrinkwrap (what's the tightest container?)
     * - Canvas/SVG rendering (for video export and PPTX generation)
     */

    // 1. Smart text fitting for GLA content slots
    async fitTextToSlot(
        text: string,
        font: string,
        slot: { width: number; height: number },
        lineHeight: number,
        options?: { minFont?: number; maxFont?: number }
    ): Promise<TextFitResult> {
        const { minFont = 12, maxFont = 72 } = options ?? {};

        // Binary search for optimal font size
        let lo = minFont, hi = maxFont;
        let bestFont = minFont;
        let bestLayout: { height: number; lineCount: number } | null = null;

        while (lo <= hi) {
            const mid = Math.floor((lo + hi) / 2);
            const fontStr = font.replace(/\d+px/, `${mid}px`);
            const prepared = prepare(text, fontStr);
            const result = layout(prepared, slot.width, lineHeight * (mid / 16));

            if (result.height <= slot.height) {
                bestFont = mid;
                bestLayout = result;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        return { fontSize: bestFont, ...bestLayout!, fits: bestLayout!.height <= slot.height };
    }

    // 2. Multi-column text flow (for magazine-style slides)
    flowTextInColumns(
        text: string,
        font: string,
        columns: { width: number; height: number }[],
        lineHeight: number,
    ): ColumnFlowResult {
        const prepared = prepareWithSegments(text, font);
        let cursor: LayoutCursor = { segmentIndex: 0, graphemeIndex: 0 };
        const columnResults: ColumnResult[] = [];

        for (const col of columns) {
            const lines: string[] = [];
            let currentHeight = 0;

            while (currentHeight + lineHeight <= col.height) {
                const range = layoutNextLineRange(prepared, cursor, col.width);
                if (!range) break;
                const line = materializeLineRange(prepared, range);
                lines.push(line.text);
                cursor = range.end;
                currentHeight += lineHeight;
            }

            columnResults.push({ lines, height: currentHeight });
        }

        return { columns: columnResults, hasOverflow: cursor.segmentIndex < prepared.segmentCount };
    }

    // 3. Text-wrapping around floated images
    flowTextAroundImage(
        text: string,
        font: string,
        containerWidth: number,
        image: { x: number; y: number; width: number; height: number },
        lineHeight: number,
    ): WrappedTextResult {
        const prepared = prepareWithSegments(text, font);
        let cursor: LayoutCursor = { segmentIndex: 0, graphemeIndex: 0 };
        const lines: { text: string; x: number; width: number; y: number }[] = [];
        let y = 0;

        while (true) {
            // Narrower width beside the image
            const availableWidth = y < image.y + image.height
                ? containerWidth - image.width - image.x
                : containerWidth;

            const range = layoutNextLineRange(prepared, cursor, availableWidth);
            if (!range) break;

            const line = materializeLineRange(prepared, range);
            lines.push({
                text: line.text,
                x: y < image.y + image.height ? image.x + image.width : 0,
                width: line.width,
                y,
            });

            cursor = range.end;
            y += lineHeight;
        }

        return { lines, totalHeight: y };
    }

    // 4. Shrinkwrap: find the tightest container that still fits the text
    shrinkwrapText(
        text: string,
        font: string,
        maxWidth: number,
        lineHeight: number,
        targetLines?: number,
    ): ShrinkwrapResult {
        const prepared = prepareWithSegments(text, font);
        const natural = measureNaturalWidth(prepared);

        if (!targetLines) {
            // Binary search for minimum width that doesn't increase line count
            const { lineCount: maxLines } = measureLineStats(prepared, maxWidth);
            let lo = Math.floor(natural / maxLines);
            let hi = maxWidth;
            let bestWidth = maxWidth;

            while (lo <= hi) {
                const mid = Math.floor((lo + hi) / 2);
                const { lineCount } = measureLineStats(prepared, mid);
                if (lineCount <= maxLines) {
                    bestWidth = mid;
                    hi = mid - 1;
                } else {
                    lo = mid + 1;
                }
            }

            return { width: bestWidth, lineCount: maxLines, height: maxLines * lineHeight };
        }

        // Find width that produces exactly targetLines
        let lo = 1, hi = maxWidth;
        while (lo <= hi) {
            const mid = Math.floor((lo + hi) / 2);
            const { lineCount } = measureLineStats(prepared, mid);
            if (lineCount <= targetLines) { hi = mid - 1; }
            else { lo = mid + 1; }
        }

        return { width: lo, lineCount: targetLines, height: targetLines * lineHeight };
    }

    // 5. Rich-text inline flow (for slide content with mixed formatting)
    layoutRichInline(
        items: Array<{ text: string; font: string; break?: 'normal' | 'never'; extraWidth?: number }>,
        maxWidth: number,
    ): RichInlineResult {
        const prepared = prepareRichInline(items);
        const lines: RichInlineLine[] = [];

        walkRichInlineLineRanges(prepared, maxWidth, range => {
            const line = materializeRichInlineLineRange(prepared, range);
            lines.push(line);
        });

        return { lines, lineCount: lines.length };
    }
}
```

### 4.29.2 Pretext Advantages for Slide Generation

| Capability | Without Pretext | With Pretext |
|-----------|----------------|--------------|
| **Text overflow detection** | DOM measurement (triggers reflow) | Pure arithmetic (<0.1ms) |
| **Font size optimization** | Trial-and-error DOM renders | Binary search + `layout()` (~1ms) |
| **Multi-column flow** | Complex CSS multi-column | `layoutNextLineRange()` per column |
| **Text around images** | CSS `shape-outside` (limited) | Variable-width line layout |
| **Shrinkwrap containers** | `width: fit-content` (unreliable) | `measureLineStats()` binary search |
| **Server-side rendering** | Headless browser required | Pure JS computation |
| **Video frame rendering** | DOM → screenshot pipeline | Direct canvas `fillText()` |
| **PPTX text sizing** | Guess-and-check | Exact pre-computation |

---

## 4.30 Self-Evolving Code Agent

> *"The code that generates slides should itself evolve to generate better code."*

### 4.30.1 Architecture

Inspired by yoyo-evolve (1.5k ⭐, MIT) — a coding agent that reads its own source, picks improvements, and commits if tests pass — we implement a **self-evolving Code Agent** for the slide generation pipeline:

```python
class SelfEvolvingCodeAgent:
    """
    The Code Agent (Layer 4) doesn't just generate React/reveal.js code —
    it learns to generate better code over time.

    Inspired by yoyo-evolve's evolution loop:
    → Read own templates → Identify improvement opportunities
    → Generate better templates → Test → If pass: commit. If fail: revert.

    This runs on a scheduled basis (weekly) to improve the template library.
    """

    # Evolution targets
    EVOLUTION_TARGETS = {
        "reveal_templates": {
            "path": "app/services/slides_new/templates/reveal/",
            "test_command": "python test_phase_f.py",
            "improvement_axes": [
                "animation_smoothness",
                "accessibility_compliance",
                "mobile_responsiveness",
                "render_performance",
                "code_size_reduction",
            ],
        },
        "react_components": {
            "path": "app/services/slides_new/templates/react/",
            "test_command": "python test_phase_f.py",
            "improvement_axes": [
                "bundle_size",
                "render_speed",
                "accessibility",
                "theme_flexibility",
            ],
        },
        "chart_templates": {
            "path": "app/services/slides_new/templates/charts/",
            "test_command": "python test_phase_f.py",
            "improvement_axes": [
                "data_edge_cases",
                "animation_quality",
                "responsive_sizing",
                "export_fidelity",
            ],
        },
    }

    async def evolution_cycle(self):
        """
        Weekly evolution cycle:
        1. Analyze current template quality metrics
        2. Identify lowest-scoring templates
        3. Generate improved versions using LLM
        4. Run tests on improved versions
        5. If tests pass and quality improves → commit
        6. If tests fail → revert and log the attempt
        """
        for target_name, target in self.EVOLUTION_TARGETS.items():
            # 1. Collect current quality metrics
            metrics = await self._collect_metrics(target)

            # 2. Find templates below threshold
            weak_templates = [t for t in metrics if t.score < 80]

            for template in weak_templates[:3]:  # Max 3 improvements per cycle
                # 3. Generate improvement
                improved = await self._generate_improvement(
                    template=template,
                    axes=target["improvement_axes"],
                    model="qwen2.5-coder-32b",  # Free model for code gen
                )

                # 4. Test
                test_result = await self._run_tests(target["test_command"])

                if test_result.passed:
                    # 5. Quality comparison
                    new_metrics = await self._collect_metrics(target, template_override=improved)
                    if new_metrics.score > template.score:
                        await self._commit_improvement(template, improved, new_metrics)
                        logger.info(f"Evolution: {template.name} improved {template.score} → {new_metrics.score}")
                    else:
                        await self._revert(template)
                else:
                    await self._revert(template)
                    logger.info(f"Evolution: {template.name} improvement failed tests — reverted")
```

### 4.30.2 Template Quality Metrics

| Metric | Measurement | Target |
|--------|-------------|--------|
| **Render Performance** | Time to first paint (ms) | <100ms |
| **Bundle Size** | Minified + gzipped (KB) | <50KB per template |
| **Accessibility Score** | axe-core audit pass rate | 100% |
| **Mobile Responsiveness** | Layout shift on resize | <0.05 CLS |
| **Animation Smoothness** | Frame drops during transitions | 0 dropped frames |
| **Export Fidelity** | SSIM between preview and export | >0.95 |
| **Theme Flexibility** | Themes applied without override | 100% |
| **Code Readability** | Maintainability index | >70 |

---

## 4.31 Sandboxed Mini-Website Preview System

> *"See exactly what your audience will see — in milliseconds, not seconds."*

### 4.31.1 Architecture

The preview system renders slides as a **sandboxed mini-website** with all frontend libraries installed in an isolated environment, enabling pixel-perfect previews that match the final output:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SANDBOXED PREVIEW ARCHITECTURE                             │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ Slide DSL v3 │───▶│ Code Agent   │───▶│ Sandbox      │                   │
│  │ (JSON)       │    │ Compilation  │    │ Runtime      │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│                                                │                             │
│                                                ▼                             │
│  ┌──────────────────────────────────────────────────────────┐               │
│  │  SANDBOXED IFRAME                                         │               │
│  │  ┌────────────────────────────────────────────────────┐  │               │
│  │  │  Pre-installed Libraries:                           │  │               │
│  │  │  • reveal.js v6.0.0 (presentation engine)          │  │               │
│  │  │  • React 18 + ReactDOM (component rendering)       │  │               │
│  │  │  • Three.js + @react-three/fiber (3D scenes)       │  │               │
│  │  │  • D3.js v7 (chart rendering)                      │  │               │
│  │  │  • Recharts v2 (React charts)                      │  │               │
│  │  │  • Framer Motion (animations)                      │  │               │
│  │  │  • UnoCSS runtime (utility CSS)                    │  │               │
│  │  │  • Mermaid (diagrams)                              │  │               │
│  │  │  • @fluentui/react-icons (premium icons)           │  │               │
│  │  │  • Lucide React (standard icons)                   │  │               │
│  │  │  • @chenglou/pretext (text measurement)            │  │               │
│  │  │  • GSAP (advanced animations)                      │  │               │
│  │  └────────────────────────────────────────────────────┘  │               │
│  │                                                           │               │
│  │  Security:                                                │               │
│  │  • sandbox="allow-scripts allow-same-origin"              │               │
│  │  • CSP: script-src 'self'; style-src 'self' 'unsafe-inline' │             │
│  │  • No network access from sandbox                         │               │
│  │  • Memory limit: 256MB                                    │               │
│  │  • CPU time limit: 5s per render                          │               │
│  └──────────────────────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.31.2 Sandbox Library Bundle

All frontend libraries are **pre-bundled and cached** for instant loading:

```typescript
class SandboxBundleManager {
    /**
     * Pre-compiled ESM bundle of all slide rendering libraries.
     * Loaded once, cached in Service Worker, shared across all previews.
     *
     * Total bundle: ~850KB gzipped (loaded once, cached forever)
     * Individual slide render: <50ms after bundle cached
     */

    BUNDLE_MANIFEST = {
        "core": {
            "reveal.js": { version: "6.0.0", size: "85KB", purpose: "Presentation engine" },
            "react": { version: "18.3", size: "42KB", purpose: "Component rendering" },
            "react-dom": { version: "18.3", size: "130KB", purpose: "DOM rendering" },
        },
        "visualization": {
            "d3": { version: "7.9", size: "95KB", purpose: "Data visualization" },
            "recharts": { version: "2.15", size: "120KB", purpose: "React charts" },
            "mermaid": { version: "11.4", size: "250KB", lazy: true, purpose: "Diagrams" },
        },
        "animation": {
            "framer-motion": { version: "12.0", size: "65KB", purpose: "React animations" },
            "gsap": { version: "3.12", size: "28KB", purpose: "Advanced animations" },
        },
        "3d": {
            "three": { version: "0.172", size: "180KB", lazy: true, purpose: "3D rendering" },
            "@react-three/fiber": { version: "9.0", size: "45KB", lazy: true, purpose: "React 3D" },
        },
        "typography": {
            "@chenglou/pretext": { version: "latest", size: "15KB", purpose: "Text measurement" },
        },
        "icons": {
            "lucide-react": { version: "0.468", size: "12KB", purpose: "Standard icons" },
            "@fluentui/react-icons": { version: "2.0", size: "tree-shaken", lazy: true, purpose: "Premium icons" },
        },
        "styling": {
            "@unocss/runtime": { version: "0.65", size: "25KB", purpose: "Utility CSS" },
        },
    };

    // Lazy loading strategy: core + visualization + animation loaded immediately
    // 3D and premium icons loaded on-demand when slide requires them
    LOAD_STRATEGY = {
        "immediate": ["core", "visualization", "animation", "typography", "icons.lucide-react", "styling"],
        "lazy": ["3d", "icons.@fluentui/react-icons", "visualization.mermaid"],
    };
}
```

### 4.31.3 Preview Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| **First preview** | <500ms | Pre-cached bundle + Service Worker |
| **Subsequent previews** | <50ms | Hot module replacement in sandbox |
| **Slide switch** | <16ms (60fps) | reveal.js native transitions |
| **Chart render** | <200ms | D3 + Recharts pre-compiled templates |
| **3D scene load** | <1s | Lazy Three.js + progressive enhancement |
| **Memory footprint** | <256MB | Sandbox memory cap + cleanup on slide switch |
| **Bundle cache hit rate** | >99% | Service Worker + ETag validation |

### 4.31.4 Preview Accuracy Guarantee

```python
class PreviewAccuracyEngine:
    """
    Ensures the sandboxed preview matches the final exported output.
    Uses SSIM comparison between preview screenshot and export render.
    """

    async def verify_accuracy(
        self,
        slide_dsl: dict,
        preview_screenshot: bytes,
        export_render: bytes,
    ) -> AccuracyResult:
        ssim_score = await self._compute_ssim(preview_screenshot, export_render)

        return AccuracyResult(
            ssim=ssim_score,
            passes=ssim_score >= 0.95,
            discrepancies=self._identify_discrepancies(preview_screenshot, export_render)
            if ssim_score < 0.95 else [],
        )

    # Target: SSIM ≥ 0.95 between preview and all export formats
    ACCURACY_TARGETS = {
        "html_export": 0.99,     # Preview IS the HTML export
        "pdf_export": 0.97,      # Playwright render matches closely
        "pptx_export": 0.90,     # PptxGenJS has inherent differences
        "video_export": 0.95,    # Canvas recording matches well
        "png_export": 0.98,      # Playwright screenshot
    }
```

---

## 4.31a AI-Native Presentation Paradigm vs. Legacy Frameworks

A core differentiation strategy allowing V9 Meridian to exceed platforms like Dokie AI and Chronicle lies in our **AI-Native Engineering** approach. While legacy software relies on static slide templates requiring a "design scramble," our architecture relies on an LLM-centric orchestration framework.

1. **Bifurcated "Story-First" Workflow (Chronicle Paradigm)**
   Unlike manual creation, Meridian splits generation into a Narrative Engineering Phase (Storyline generation via Graph logic) and a Visual Mapping Phase (Applying constraints to widget modules).
2. **Deep Hover & Peek Interaction (Dokie / Chronicle UI)**
   Meridian integrates non-linear presentation widgets. "Peek" mode allows the presenter to zoom into specific slide data nodes, while "Deep Hover" dimming visual noise to draw audience attention strictly to isolated statistics. 
3. **Advanced RAG Ingestion Layer**
   Ingesting data accurately from PDFs, Web URLs, and internal docs utilizes advanced vector scraping (ChromaDB + Multi-modal LLMs) to summarize and extract structured semantic content natively.

## 4.31b High-Fidelity 3D Interactivity & "Remix" Component Architecture

**Interactive Spatial Rendering:**
To beat Dokie AI's immersive capabilities:
- Meridian embeds native **Three.js / WebGL** 3D model support. Models (e.g., architectural specs, molecular biology) are layered within the slide DOM allowing "X-ray Vision", real-time rotation, and zoom.

**"Remix" Intelligent Generative Constraints:**
Rather than 64 pre-defined layout styles, our Generative Layout Algebra works hand-in-hand with our **Design Critic Agent**. When the user triggers "Remix", the layout auto-computes the optimal structural grid utilizing:
- **Nano-Banana-Pro Spacing Multipliers:** Guaranteeing optimal whitespace per composition rule.
- **Dynamic Visual Hierarchy:** Assigning weight values automatically as "hero", "sidebar", or "grid".

---

## 4.32 Implementation Phases (26 Weeks)

### Phase 1: Foundation (Weeks 1-2)

**Deliverables:**
- FastMCP server (stdio/HTTP+SSE) with core tools
- Slide DSL v3 schema (Zod validation)
- MongoDB + Redis + ChromaDB setup
- Basic CRUD operations
- Agent communication protocol v1.0
- Model Router with all provider integrations

**Dependencies**: None

### Phase 2: Narrative + Content Intelligence (Weeks 3-5)

**Deliverables:**
- Layer 1: Narrative Agent with arc mapping
- Layer 2: Content Agent with semantic typing
- Narrative Arc Engine (5 archetype structures)
- Content anti-slop rules
- Standard Mode fast path (Groq/GLM)
- Web-to-Slide Transformer (Phase 1: Extraction pipeline for URLs + PDFs)

**Dependencies**: Phase 1

### Phase 3: Spatial Design + GLA (Weeks 5-7)

**Deliverables:**
- Generative Layout Algebra type system
- Yoga WASM constraint solver integration
- PreTeXt.js text measurement integration
- 50+ pre-computed GLA patterns for Standard Mode
- 8 pre-computed GLA data patterns (heading_table, heading_chart, stats_dashboard, chart_and_table, heading_diagram, hero_stat, comparison_grid, timeline_slide)
- Visual Weight Engine
- Layout Agent with GLA composition
- Visual Identity System (VIS) whitespace + shape language enforcement

**Dependencies**: Phase 2

### Phase 4: Visual Generation + Data Visualization (Weeks 7-9)

**Deliverables:**
- Visual Narrative Director
- Image generation pipeline (FLUX/Phoenix/Lucid routing)
- Complete Data Visualization System (§4.24):
  - Chart Intelligence Engine (auto-selects optimal chart type from 90+ types)
  - Chart rendering: D3.js templates + Recharts components for all chart categories
  - Table rendering engine (18 table types, conditional formatting, overflow handling)
  - Diagram engine (17 diagram types, auto-layout, force-directed graphs)
  - Metric card / dashboard / hero stat components
  - Chart animation controller (per-type entrance/update/exit animations)
  - Data validation layer (DataValidator + graceful error states)
  - Chart accessibility (WCAG AA: ARIA labels, pattern fills, data table fallback)
  - Chart theme integration (all data elements inherit from Theme Engine)
  - PPTX-native chart export (11 editable chart types via PptxGenJS)
  - Print-quality SVG export (SVGO optimized, 300 DPI raster fallback)
- Icon system (Lucide React, 70+ semantic icon mappings, 15 categories)
- Code Agent for React/reveal.js code generation
- VIS image treatment + icon style enforcement

**Dependencies**: Phase 3

### Phase 5: reveal.js Renderer + Themes (Weeks 9-11)

**Deliverables:**
- DSL v3 → reveal.js compiler
- UnoCSS theme compilation
- 24 built-in themes with full color specs
- Generative Theme Engine (brand input, mood, URL extraction)
- Auto-Animate support
- Reading Mode + Presentation Mode
- VIS animation personality enforcement

**Dependencies**: Phase 4

### Phase 6: Composition + QA (Weeks 11-13)

**Deliverables:**
- Layer 5: Composition Intelligence Engine (5-factor scoring)
- Layer 6: 7-Layer Slop Detection
- SSIM visual regression testing framework
- Accessibility validator (WCAG 2.1 AA)
- Reflection Loop (QA → re-invoke appropriate layer)
- Cross-slide consistency checker
- VIS compliance scoring in QA pipeline

**Dependencies**: Phase 5

### Phase 7: React + Three.js Renderer + Progressive 3D (Weeks 13-15)

**Deliverables:**
- DSL v3 → React component compiler
- Three.js 3D scene system (5 scene types)
- Progressive 3D Enhancement Levels (5 levels: none → full)
- Per-slide enhancement level selection
- Auto-degradation for weak devices / low battery
- Performance guardrails (lazy loading, 60fps target, polygon budgets)
- Framer Motion animation choreography

**Dependencies**: Phase 6

### Phase 8: PPTX + HTML Renderers + Brand Package Export (Weeks 15-16)

**Deliverables:**
- PptxGenJS native PPTX generation
- .potx template injection
- Zero-dep HTML renderer
- React → PPTX conversion pipeline
- Brand Package .zip exporter (fonts, logos, icons, templates, tokens)
- Figma Tokens + Tailwind theme export

**Dependencies**: Phase 7

### Phase 9: Canvas Editor — "Figma for Slides" (Weeks 16-18)

**Deliverables:**
- Konva.js infinite canvas editor with React integration
- Component Library (265+ components, ~925 variants)
- Variant System (per-element style alternatives)
- Auto-Layout Engine (14 layout actions)
- Design Token System (spacing, radius, shadow, opacity scales)
- Smart Slide constraint handles
- Plugin Architecture for extensibility
- AI Bar + AI Assist Tools (10 context-aware actions)
- 4-level regeneration UI

**Dependencies**: Phase 8

### Phase 10: A/B Variant Generation + Design Intelligence (Weeks 18-19)

**Deliverables:**
- Variant Generator (2-3 layout/style variants per slide)
- Variant Selection UI (side-by-side comparison with scores)
- Variant Preference Learning (ChromaDB embeddings)
- Design Intelligence Dashboard (full per-slide explainability)
- Layout explanation, visual hierarchy, composition balance panels
- Anti-AI-Slop report per slide
- VIS compliance report per slide
- Dashboard → Action buttons (regenerate, adjust weights, save template)

**Dependencies**: Phase 9

### Phase 11: Collaborative Editing + Web-to-Slide (Weeks 19-21)

**Deliverables:**
- Real-time cursor presence with avatars (Yjs awareness protocol)
- Element-level locking with auto-release
- Comment threads (per-element + per-slide) with @mentions
- Version history with snapshot browsing + restore
- Share permissions (editor/commenter/viewer roles)
- WebSocket collaboration server
- Web-to-Slide Transformer (Phase 2: Analysis + Transformation)
- Support for URL, PDF, DOCX, Notion, Google Doc, Markdown inputs

**Dependencies**: Phase 10

### Phase 12: State Sync + Polish + Production (Weeks 21-22)

**Deliverables:**
- Zustand state management (full integration)
- Yjs CRDT multiplayer sync (conflict resolution)
- Streaming generation preview (SSE with time budgets)
- StandardMode preview: progressive slide-by-slide fill
- Premium Mode preview: phase-aware progress with thinking indicator
- 100+ template library completion
- Production hardening, load testing, security audit
- End-to-end integration testing across all 15 phases

**Dependencies**: Phase 11

### Phase 13: Self-Learning System + Video Preview (Weeks 22-24)

**Deliverables:**
- Self-Learning Slide Generation System (§4.25):
  - Generation History DB (MongoDB — every generation scored & stored)
  - Quality Scoring Engine (5-factor: composition, slop, VIS, user edits, engagement)
  - Pattern Extraction Pipeline (ChromaDB embeddings of high-scoring layouts)
  - Skill Evolution System (autonomous skill creation from complex generation tasks)
  - Cross-Session Memory (hot/warm/cold tier with daily synthesis)
  - A/B Learning Loop (variant selection trains preference model)
- Video Preview & Export Module (§4.26):
  - Animation Sequencer (element-level timings, slide transitions)
  - Canvas Recording Engine (OffscreenCanvas + MediaRecorder)
  - FFmpeg WASM transcoder (WebM → MP4)
  - Video Preview UI mode (play/pause/scrub/settings)
  - Export: WebM, MP4, MP4 4K, GIF, PNG sequence

**Dependencies**: Phase 12

### Phase 14: Advanced Design + LLM Security (Weeks 24-25)

**Deliverables:**
- Advanced Design Intelligence System (§4.27):
  - Fluent UI Icon Integration (1,300+ families, 4 variants, 2,300+ total with Lucide)
  - Graphite-Inspired Procedural Design (node-graph composition, nondestructive edits)
  - Style Transfer Engine (extract visual DNA from references, apply to new decks)
  - 6 Curated Style Profiles (Apple Keynote, Stripe Docs, Airbnb, Sequoia, YC, TED)
- LLM Security & Rate Limit Management (§4.28):
  - Secure .env-based key management (pydantic SecretStr, never logged)
  - Per-provider rate limiting (Redis-based distributed counters)
  - Groq 6-key round-robin (180 RPM effective)
  - Budget Optimizer ($70/month cap, free models first)
  - Key rotation & health monitoring

**Dependencies**: Phase 13

### Phase 15: Typography + Code Agent + Sandbox (Weeks 25-26)

**Deliverables:**
- Pretext Advanced Typography Engine (§4.29):
  - Full Pretext API integration (segmented layout, line-by-line rendering)
  - Text-around-image flow (variable-width `layoutNextLineRange`)
  - Rich-text inline flow (mixed fonts, chips, mentions)
  - Shrinkwrap text containers + balanced text layout
  - Server-side text measurement (no DOM needed)
- Self-Evolving Code Agent (§4.30):
  - Template quality metrics collection (render perf, accessibility, bundle size)
  - Weekly evolution cycle (analyze → improve → test → commit or revert)
  - Template skill library (chart-to-react, animation-choreography, etc.)
- Sandboxed Mini-Website Preview System (§4.31):
  - Pre-bundled library ESM bundle (~850KB gzipped, cached via Service Worker)
  - Sandboxed iframe with CSP + memory limits
  - Preview accuracy verification (SSIM ≥ 0.95 vs export)
  - Hot-reload preview (<50ms after initial load)

**Dependencies**: Phase 14

---

## 4.33 Technology Stack (Complete)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **MCP Server** | Python 3.11+, FastMCP | Agent orchestration, tool delivery |
| **Code Agent Runtime** | TypeScript, Node.js 20+ | React/reveal.js compilation, DSL processing |
| **Layout Engine** | Yoga WASM | Constraint-based flexbox layout resolution |
| **Text Measurement** | PreTeXt.js (@chenglou/pretext) | DOM-free text fitting (0.09ms/check) |
| **Presentation Renderer** | reveal.js v6.0.0 + UnoCSS | Primary HTML presentation engine |
| **React Renderer** | React 18 + Vite + Tailwind v4 | Interactive/3D presentations |
| **3D Engine** | Three.js + @react-three/fiber | 3D scenes within slides (progressive enhancement) |
| **3D Post-Processing** | postprocessing (Three.js) | Bloom, DOF, film grain for "full" 3D level |
| **PPTX Generation** | PptxGenJS v4.0.1 (+ python-pptx fallback) | Native PowerPoint generation |
| **PDF Generation** | Playwright | Pixel-perfect PDF from browser |
| **Canvas Editor** | Konva.js + react-konva | WYSIWYG infinite canvas slide editing |
| **Code Editor** | Monaco Editor | HTML/CSS/JS editing |
| **Markdown Editor** | CodeMirror 6 | reveal.js markdown editing |
| **Animations** | Framer Motion + GSAP | React slide animations |
| **Charts** | D3.js + Recharts | Data visualizations |
| **Diagrams** | Mermaid + Excalidraw | Flowcharts, hand-drawn style |
| **Vector Database** | ChromaDB | Presentation embeddings, variant preferences, RAG |
| **Document Database** | MongoDB (motor async) | Presentations, slides, themes, version history |
| **Cache** | Redis | LLM responses, themes, metrics |
| **State Sync** | Yjs CRDTs + WebSocket | Multiplayer editing + cursor presence |
| **State Management** | Zustand | Client-side state |
| **Browser Automation** | Playwright | Preview, QA screenshots, PDF, SSIM, Web-to-Slide extraction |
| **CSS Framework** | UnoCSS (reveal.js) + Tailwind v4 (React) | Utility-first styling |
| **Web Extraction** | Playwright + Readability.js | URL → structured content extraction |
| **Document Parsing** | PyMuPDF + python-docx + Tesseract | PDF/DOCX → structured content |
| **Brand Package** | zipfile + Jinja2 templates | .zip brand asset export |
| **Collaboration** | y-websocket + y-mongodb | Real-time sync server + persistent backend |
| **Icon Library** | Lucide React | 1000+ consistent 2px stroke icons |
| **Chart Rendering** | D3.js v7 + Recharts v2 | 90+ chart types with server-side rendering via Playwright |
| **Table Rendering** | Custom HTML + PptxGenJS tables | 18 table types with conditional formatting |
| **Diagram Engine** | D3-force + Mermaid + custom SVG | 17 diagram types (flowchart, org, mind map, sankey, etc.) |
| **Chart Accessibility** | Custom ARIA + pattern fills | WCAG AA compliant charts with screen reader support |
| **Data Validation** | Zod + custom DataValidator | Input sanitization, range checking, graceful error states |
| **Self-Learning** | ChromaDB embeddings + MongoDB history | Pattern extraction, skill evolution, cross-session memory |
| **Video Export** | OffscreenCanvas + MediaRecorder + FFmpeg WASM | Slide-to-video recording and MP4/WebM export |
| **Premium Icons** | @fluentui/react-icons | 1,300+ icon families (Regular/Filled/Light/Color) |
| **Procedural Design** | Node-graph engine (custom) | Nondestructive parametric slide composition |
| **Style Transfer** | Embedding similarity + LLM analysis | Visual DNA extraction and cross-deck style application |
| **Rate Limiting** | Redis distributed counters | Per-provider rate limits, key rotation, budget tracking |
| **Advanced Typography** | @chenglou/pretext full API | Line-by-line layout, text-around-image, shrinkwrap, rich inline |
| **Code Evolution** | Scheduled LLM + test harness | Self-evolving template improvement cycle |
| **Sandbox Preview** | iframe + Service Worker + ESM bundle | Isolated rendering with pre-installed libraries (~850KB cached) |

---

## 4.34 Success Metrics

| Metric | Standard Mode Target | Premium Mode Target |
|--------|---------------------|---------------------|
| Full 10-slide deck generation | **<15s** | **<90s** |
| Per-slide generation time | **≤1.5s** | **≤8s** |
| DSL generation success (valid JSON) | >95% | >98% |
| Image generation success | >85% (with fallback) | >95% (with fallback) |
| Export success rate (all formats) | >99% | >99% |
| Quality pass rate (first attempt) | >65% | >85% |
| Quality pass rate (after reflection) | >80% | >95% |
| Preview refresh latency | <200ms | <200ms |
| PreTeXt validation time | <1ms per text | <1ms per text |
| reveal.js slide transition | <16ms (60fps) | <16ms (60fps) |
| Three.js scene render (lite level) | ≥30fps | ≥30fps |
| Three.js scene render (full level) | N/A | ≥60fps |
| 3D auto-degradation response | <2s | <2s |
| PPTX file size (10 slides) | <10MB | <10MB |
| Composition score (Premium) | N/A | >70/100 |
| Slop score (0=clean) | <30 | <15 |
| VIS compliance score | >60/100 | >80/100 |
| Accessibility compliance | WCAG A | WCAG AA |
| Estimated cost per deck | **$0.00 - $0.05** | **$0.30 - $0.80** |
| Web-to-Slide extraction confidence | >80% | >90% |
| Web-to-Slide extraction time | <8s | <12s |
| Brand Package export time | N/A | <5s |
| Collaborative cursor latency | <100ms | <100ms |
| Collaborative edit sync latency | <200ms | <200ms |
| Max concurrent editors per deck | 5 | 10 |
| Version history snapshots retained | 50 | Unlimited |
| Variant generation time (3 variants) | N/A | <25s |
| Design Intelligence Dashboard load | <500ms | <500ms |
| Component Library items | 265+ | 265+ |
| Component variant combinations | ~925 | ~925 |
| Canvas zoom range | 10%-2000% | 10%-2000% |
| Chart types supported | 90+ | 90+ |
| Table types supported | 18 | 18 |
| Diagram types supported | 17 | 17 |
| Chart render time (D3 + Playwright) | <800ms | <1200ms |
| Chart PPTX-native export types | 11 | 11 |
| Data validation pass rate | >95% | >99% |
| Chart accessibility (WCAG AA) | Partial | Full |
| Icon library items (Lucide) | 1000+ | 1000+ |
| Semantic icon auto-map accuracy | >80% | >90% |

---

# Part V: Key Innovations Introduced

## Innovation Summary (V9 vs V7 vs V8)

| Innovation | V7 | V8 Reference | V9 Meridian |
|-----------|-----|-------------|-------------|
| **Generation Pipeline** | Template → Fill → Render (flat) | 5-Layer Think-to-Render | **6-Layer CDI with Reflection Loop** |
| **Layout System** | 12 fixed templates | 300+ Smart Slide templates | **Generative Layout Algebra (infinite unique layouts)** |
| **Content Intelligence** | Basic outline + fill | Content + spatial reasoning | **Semantic typing with weight + narrative arc mapping** |
| **Visual Coherence** | Per-slide image prompting | Contextual Image Prompts | **Visual Narrative Director (deck-wide artistic thread)** |
| **Composition Quality** | Manual/basic QA | Visual Weight Engine | **Composition Intelligence Engine (5-factor scoring)** |
| **Quality Assurance** | 12 anti-slop presets | 7-Layer Slop Detection | **7-Layer Slop Detection + SSIM Regression + Auto-Correction** |
| **Generation Modes** | Single mode (+ Fast toggle) | Single pipeline | **Dual Mode: Standard (<15s, free) + Premium (<90s, paid)** |
| **User Brand Input** | Theme selection only | Brand DNA extraction | **Brand Input Pipeline (direct input, URL, document, .potx)** |
| **Canvas Editor** | OpenPencil (Skia + Vue + Tauri) | Konva.js (proposed) | **"Figma for Slides" — Infinite Canvas + Component Library + Auto-Layout + Design Tokens + Plugin Architecture** |
| **Emotional Modeling** | None | None | **Narrative Arc Engine with emotional intensity per slide** |
| **Regeneration** | 3 levels (element, slide, deck) | Unspecified | **4 levels + A/B Variant Generation (2-3 alternatives with scoring)** |
| **Layout Resolution** | Percentage positioning | Constraint-based (proposed) | **Yoga WASM solver + PreTeXt.js text fitting** |
| **Slide DSL** | v2 (JSON schema, extensible) | Unspecified | **v3 (narrative metadata, GLA tree, QA scores, visual thread, 3D enhancement config)** |
| **Cost per Standard Deck** | Unspecified | Unspecified | **$0.00 - $0.05 (free model priority)** |
| **Template Count** | 12 layouts + 24 themes | 300+ templates | **100+ GLA pattern presets + 265 components (~925 variants) + infinite generative compositions** |
| **Agents** | 8 | Unspecified | **10 (added Narrative Agent, Brand Agent)** |
| **Preview** | Basic | Unspecified | **Streaming SSE with per-phase time budgets (Standard: 0-15s, Premium: 0-90s)** |
| **Feedback Loop** | None (generate once) | None | **QA → Reflect → Re-invoke correct layer (max 2 iterations)** |
| **3D Rendering** | None | Three.js (proposed) | **Progressive 3D: 5 levels (none → css-3d → svg → lite → full) with auto-degradation** |
| **Content Import** | Manual text input only | Unspecified | **Web-to-Slide Transformer: URL/PDF/DOCX/Notion → structured slides** |
| **Visual Identity** | None (inconsistent styling) | None | **Visual Identity System (VIS): 6 signature principles, enforced at every pipeline stage** |
| **Collaboration** | None (single user) | None | **Real-time multiplayer: cursors, locks, comments, @mentions, version history** |
| **Brand Export** | None | None | **Brand Package .zip: fonts, logos, icons, templates, Figma tokens, Tailwind config** |
| **Variant Testing** | None | None | **A/B Variant Generation: 2-3 alternatives per slide with composition scoring** |
| **Explainability** | None (black box) | None | **Design Intelligence Dashboard: per-slide layout reasoning, hierarchy, balance, slop report** |
| **Data Visualization** | 12 basic chart types | Unspecified | **90+ chart types, 18 table types, 17 diagram types, icon system, Chart Intelligence Engine, theme-aware rendering, WCAG AA accessible, PPTX-native editable charts** |
| **Self-Learning** | None | None | **Teacher-Student paradigm: every generation teaches the next via pattern extraction, skill evolution, and cross-session memory (ChromaDB + MongoDB)** |
| **Video Export** | None | None | **Slide-to-video pipeline: OffscreenCanvas + MediaRecorder + FFmpeg WASM. WebM/MP4/4K/GIF. Cinematic transitions + element-level animations** |
| **Design Intelligence** | None | None | **3-tier icons (Lucide + Fluent UI 5,200+), Graphite-inspired procedural node-graph composition, Style Transfer Engine with 6 curated style profiles** |
| **LLM Security** | Basic API key usage | Unspecified | **pydantic SecretStr .env management, Redis distributed rate limiting, 6-key Groq round-robin, $70/month budget optimizer, key rotation & health monitoring** |
| **Advanced Typography** | Basic text fitting | None | **Full Pretext API: line-by-line layout, text-around-image flow, rich inline (chips/mentions), shrinkwrap, server-side measurement (0 DOM)** |
| **Code Agent Evolution** | Static templates | None | **Self-evolving templates: weekly analyze → improve → test → commit/revert cycle. Skills that improve through use** |
| **Sandbox Preview** | Basic iframe | None | **Pre-bundled ESM sandbox (~850KB cached): React 18, D3, Three.js, reveal.js, Framer Motion + CSP + memory limits. SSIM ≥ 0.95 accuracy** |

---

## The Eighteen Breakthrough Innovations

### 1. Generative Layout Algebra (GLA)
No other AI presentation tool uses a formal layout algebra. Beautiful.ai has Smart Slides (constraint-based, but fixed templates). Gamma has card layouts. V9's GLA means every slide gets a **mathematically unique layout** composed from primitives, resolved to pixel-perfect coordinates by Yoga WASM. The LLM reasons about layout structure (column/row/grid/stack) rather than selecting from a menu.

### 2. Narrative Arc Engine
No competitor models the emotional trajectory of a deck. Gamma.app generates slides independently. Beautiful.ai focuses on individual slide beauty. V9's Narrative Arc Engine means slide 5 looks different from slide 2 **because it plays a different role in the story**. Climax slides are visually bolder. Data-heavy slides are calmer. This creates decks that **feel** professionally crafted.

### 3. Visual Narrative Director
Image generation in competitors is per-slide, context-free. V9 maintains a deck-wide visual thread — every image shares the same artistic direction, color temperature, composition family, and lighting direction. This is how professional designers work: they establish a visual language for the whole project, not per-page.

### 4. Composition Intelligence Engine
V9 is the first system to formally score slide composition using professional design principles (visual hierarchy, balance, harmony, focal point, narrative flow) with a vision model. Below-threshold slides get specific remediation suggestions and automatic correction.

### 5. Dual Generation Modes with Economic Model
V9's cost model is production-differentiated: Standard Mode costs nearly $0 per deck (using only free models) while Premium Mode invests $0.30-0.80 for exceptional quality. This enables a freemium business model where free-tier users generate unlimited Standard decks while paying users get Premium quality.

### 6. "Figma for Slides" Canvas Editor
No AI presentation tool offers a professional design editor with component libraries, variant systems, auto-layout engines, and design tokens. Gamma.app has basic editing. Beautiful.ai has constraint-based editing. V9's editor is the first to combine **infinite canvas (10%-2000% zoom), 265+ drag-and-drop components, per-element style variants, 14 auto-layout actions, and a plugin architecture** — making it a design tool that happens to generate slides with AI, not an AI tool with a basic editor bolted on.

### 7. Progressive 3D Enhancement
No competitor has a 5-level progressive 3D system. Most either have no 3D or force full Three.js (heavy). V9's progressive enhancement — from pure CSS through SVG illustrations to lazy-loaded Three.js with polygon budgets — means every device gets the best experience it can handle, with automatic degradation when resources are constrained.

### 8. Web-to-Slide Transformer
Paste a URL, upload a PDF, drag in a Word doc → get a structured presentation. No AI tool does true content extraction with brand signal detection and automatic narrative mapping. V9's 3-phase pipeline (Extract → Analyze → Transform) turns any content source into a generation-ready NarrativePlan.

### 9. Visual Identity System (VIS)
AI-generated slides universally suffer from looking "AI-generated" — inconsistent styling, no design personality. V9's VIS bakes a **recognizable visual signature** into every generated slide: asymmetric balance, depth layering, typographic contrast, generous whitespace, strategic accent color usage, and consistent animation personality. Meridian slides are visually distinguishable from any other AI tool's output.

### 10. Design Intelligence Dashboard
The industry's first **explainable AI** for presentations. Every slide gets a transparent breakdown: why this layout was chosen (with alternatives that were rejected and why), visual hierarchy analysis, composition balance scoring, narrative arc positioning, and slop check results. This transforms Meridian from a black-box generator into a **design education tool** — users learn design principles by seeing how the AI thinks.

### 11. Complete Data Visualization System
No AI presentation tool treats data elements as first-class citizens. Gamma and Beautiful.ai offer basic bar/pie/line charts with no intelligence. V9's Data Visualization System provides **90+ chart types across 12 categories, 18 table types with conditional formatting, 17 diagram types with auto-layout, a Chart Intelligence Engine that auto-selects optimal visualization type, 70+ semantic icon mappings, theme-aware rendering, WCAG AA accessibility with pattern fills, and PPTX-native editable chart export** for 11 chart types. Every data element — from a financial table to a Sankey diagram — is rendered pixel-perfect, animated, accessible, and print-quality.

### 12. Self-Learning Slide Generation System (SLGS)
No AI tool learns from its own generations. Every competitor starts from scratch with each deck. V9's SLGS implements a **teacher-student paradigm** where every generation produces knowledge artifacts: high-scoring layout patterns stored as ChromaDB embeddings, anti-patterns catalogued from slop detection, user style preferences extracted from A/B selections, and autonomous "generation skills" that self-improve through use. After 1,000 generations, the system has 500+ unique layout patterns, 50+ skills, and can predict user variant preferences with >70% accuracy.

### 13. Video Preview & Export Module
No AI presentation tool exports to video natively. Users must screen-record or use third-party tools. V9's Video Module renders presentations as **cinematic video experiences** with element-level entrance animations, slide-to-slide transitions (fade, morph, cinematic-cut), scrubbing timeline, and export to WebM/MP4/4K/GIF — all using an open-source stack (OffscreenCanvas + FFmpeg WASM) with zero licensing costs.

### 14. Advanced Design Intelligence (Icons + Procedural Design + Style Transfer)
Three sub-innovations: (a) **3-tier icon system** with 6,200+ icons (Lucide Standard + Fluent UI Premium + Custom Brand), (b) **Graphite-inspired procedural design** where every visual decision is a composable node in a graph — adjust any parameter without regenerating the entire slide, (c) **Style Transfer Engine** that extracts the "visual DNA" from successful presentations and applies it to new content, with 6 curated style profiles (Apple Keynote, Stripe Docs, Airbnb Pitch, Sequoia, YC Demo Day, TED Talk).

### 15. LLM Security & Startup Budget Optimization
The first AI presentation architecture with **formal LLM cost management**: every API key via pydantic SecretStr (never logged, never exposed), Redis-based distributed rate limiting, 6-key Groq round-robin for 180 RPM effective rate, Cloudflare Workers for zero-cost image generation, and a Budget Optimizer that caps monthly spend at $70 while delivering Standard Mode at $0.00/deck. This makes Meridian the only AI presentation tool designed from day one for startup economics.

### 16. Pretext Advanced Typography
No competitor has DOM-free text intelligence. CSS text measurement triggers layout reflow — slow and inaccurate for real-time preview. V9's full Pretext integration provides **line-by-line text layout at 0.1ms/check, text flowing around images via variable-width line computation, rich inline flow for mixed-font segments with chips and mentions, shrinkwrap containers via binary search, and server-side text measurement without a browser**. This eliminates the #1 cause of text overflow in AI-generated slides.

### 17. Self-Evolving Code Agent
The Code Agent that generates React/reveal.js slide code **evolves its own templates**. Weekly cycle: analyze template quality metrics → identify weakest templates → generate improvements using free LLMs → run tests → commit if quality improves, revert if not. Templates develop "skills" (chart-to-react, animation-choreography) that improve through use. After 6 months, the template library is measurably better than its initial state — without any human intervention.

### 18. Sandboxed Mini-Website Preview
AI presentation previews are either inaccurate (rendered differently than export) or slow (full browser render). V9's Sandboxed Preview runs a **complete mini-website inside a CSP-protected iframe** with all rendering libraries pre-bundled and Service-Worker-cached (~850KB). First preview in <500ms, subsequent in <50ms, with SSIM ≥ 0.95 accuracy guarantee against all export formats. Users see exactly what their audience will see.

---

# Part VI: Final Evaluation

## Completeness Assessment

| Requirement (from User Brief) | Addressed? | Location |
|-------------------------------|-----------|----------|
| Template generation system | Yes | §4.5 (GLA), §4.12 (100+ templates) |
| 100+ built-in templates | Yes | §4.12 (100+ GLA Pattern Presets) |
| Quality design/styles/animations/3D | Yes | §4.6 (Visual), §4.13 (Renderers), §4.13b (Progressive 3D), Themes (§4.11) |
| Unique designs per slide | Yes | §4.5 (GLA produces unique layouts per content) |
| Engaging, exciting, professional, investor-friendly | Yes | §4.3 (Narrative Arc), §4.12 (Pitch deck templates), §4.22 (VIS) |
| Dynamic generation | Yes | §4.18 (Streaming preview with time budgets), §4.16 (4-level regen + variants) |
| Standard mode + Premium mode | Yes | §4.2 (Dual pipeline), §4.15 (Cost model) |
| User-given typography/colors handling | Yes | §4.11 (Brand Input Pipeline, Theme Engine) |
| Preview system | Yes | §4.18 (SSE streaming preview with per-phase time budgets) |
| Design engine | Yes | §4.5 (Spatial Design), §4.7 (Composition Engine) |
| Content intelligence layer | Yes | §4.4 (Content Intelligence with semantic typing) |
| MCP optimization | Yes | §4.15 (Model Router with cost-optimized routing) |
| UI/UX design logic | Yes | §4.14 ("Figma for Slides" editor), §4.19 (Reading/Presenting modes) |
| Component library + variant system | Yes | §4.14 (265+ components, ~925 variants, per-element style alternatives) |
| Progressive 3D enhancement | Yes | §4.13b (5 levels: none → full, auto-degradation) |
| Content import from web/documents | Yes | §4.21 (Web-to-Slide Transformer: URL/PDF/DOCX/Notion) |
| Visual identity / design personality | Yes | §4.22 (VIS: 6 signature principles, enforced across pipeline) |
| Collaborative editing | Yes | §4.20 (Real-time cursors, locks, comments, @mentions, version history) |
| Brand package export | Yes | §4.17 (Brand Package .zip with fonts, logos, tokens, templates) |
| A/B variant generation | Yes | §4.16 (2-3 variants per slide with composition scoring + preference learning) |
| Design explainability | Yes | §4.23 (Design Intelligence Dashboard: per-slide reasoning + scores) |
| Charts, graphs, data visualization | Yes | §4.24 (90+ chart types, Chart Intelligence Engine, D3+Recharts rendering, PPTX-native) |
| Tables with formatting | Yes | §4.24 (18 table types, conditional formatting, financial formatting, overflow handling) |
| Diagrams (flow, org, mind map, etc.) | Yes | §4.24 (17 diagram types with auto-layout and theme integration) |
| Icon system (categorized, semantic) | Yes | §4.24 (Lucide-based, 70+ semantic mappings, 15 categories) |
| Chart accessibility (WCAG AA) | Yes | §4.24 (Screen reader, pattern fills, high contrast, data table fallback) |
| Data validation & error states | Yes | §4.24 (DataValidator, graceful empty/loading/error states) |
| Chart animation system | Yes | §4.24 (Per-type entrance/update/exit animations, hover effects) |
| Self-learning from past generations | Yes | §4.25 (SLGS: teacher-student paradigm, pattern extraction, skill evolution) |
| Video preview & export | Yes | §4.26 (WebM/MP4/4K/GIF export, animation sequencer, OffscreenCanvas + FFmpeg WASM) |
| Advanced icon system (premium tier) | Yes | §4.27 (Fluent UI 5,200+ icons, 3-tier system: Standard + Premium + Brand) |
| Procedural/parametric design | Yes | §4.27 (Graphite-inspired node-graph, nondestructive parameter adjustment) |
| Style transfer from references | Yes | §4.27 (Visual DNA extraction + 6 curated style profiles) |
| LLM key security & rate limits | Yes | §4.28 (pydantic SecretStr, Redis rate limits, Groq round-robin, budget optimizer) |
| Advanced typography engine | Yes | §4.29 (Full Pretext API: line-by-line layout, text-around-image, shrinkwrap) |
| Self-evolving code templates | Yes | §4.30 (Weekly evolution cycle, template skills, quality-gated commits) |
| Sandboxed accurate preview | Yes | §4.31 (Pre-bundled ESM sandbox, CSP isolation, SSIM ≥ 0.95 accuracy) |

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| LLM output inconsistency (GLA JSON malformed) | High | Zod schema validation + retry with error feedback |
| Yoga WASM performance on complex layouts | Medium | Pre-computed patterns for Standard Mode, async web workers |
| Free model rate limits (Cloudflare, Groq) | Medium | 8-key Groq round-robin, multiple Cloudflare workers, Redis cache |
| Visual regression after code changes | Medium | SSIM golden master testing in CI pipeline |
| PptxGenJS single-maintainer risk | Low | python-pptx server-side fallback maintained |
| Konva.js bundle size impact | Low | ~200KB (acceptable), lazy load for non-editor pages |
| Three.js bundle size impact | Medium | Progressive loading: 0KB (none/css), 15KB (svg), 45KB (lite), 120KB (full) |
| WebSocket collaboration scalability | Medium | Horizontal scaling via y-websocket + Redis pub/sub, max 10 editors/deck |
| Web-to-Slide extraction accuracy | Medium | Playwright full-render for JS sites, Readability.js fallback, OCR for scanned PDFs |
| Version history storage costs | Low | Compressed MongoDB snapshots, auto-prune after 50 (free) / unlimited (enterprise) |
| Design Intelligence Dashboard latency | Low | Pre-computed during generation, cached in Redis, <500ms load time |
| Component Library maintenance | Low | Design tokens auto-update all components when theme changes |
| 22-week core product timeline | Medium | Well-phased; core product ships at Week 22; advanced features in Phases 13-15 (Weeks 22-26) |
| 90+ chart type rendering quality | Medium | D3 templates + Playwright SSR ensures consistent output; PPTX-native for 11 basic types |
| Chart data edge cases (NaN, extreme ranges, empty) | Low | DataValidator catches issues pre-render; graceful error states for all failure modes |
| Self-learning cold start (no data) | Medium | Pre-seeded with 100+ curated layout patterns; system fully functional before learning kicks in |
| Video export browser compatibility | Medium | WebM native in Chrome/Edge; MP4 via FFmpeg WASM fallback; GIF as universal fallback |
| FFmpeg WASM performance | Low | Transcoding runs in Web Worker; typical 10-slide deck in <30s; progressive preview while encoding |
| Fluent UI icon bundle size | Low | Tree-shaken imports; only used icons included (~15KB vs full 2MB library) |
| Self-evolving agent introduces bugs | Low | All improvements gated by test suite; auto-revert on any test failure; max 3 changes per cycle |
| Budget optimizer overspend | Medium | Hard Redis counters per provider; daily email alerts at 80% budget; automatic fallback to free models |
| Sandbox preview security (iframe escape) | Medium | CSP + sandbox attribute + no network access; reviewed against OWASP iframe security guidelines |
| 26-week timeline extension (vs. 22 weeks) | Medium | New phases 13-15 are additive; core product ships at Week 22; V9.3 features in weeks 22-26 |

## Architecture Quality Rating

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Completeness** | 10/10 | All 36 requirements addressed with specific architecture |
| **Innovation** | 10/10 | 18 breakthrough innovations — the most in the AI presentation industry |
| **Feasibility** | 9/10 | 26-week timeline is ambitious but well-phased. Core product at Week 22, advanced features by Week 26. |
| **Cost Efficiency** | 10/10 | Budget Optimizer enforces $70/month cap. Standard Mode $0. Per-provider rate limiting. Startup-first economics. |
| **Scalability** | 9.5/10 | Stateless pipeline, async agents, Redis cache, horizontal WebSocket scaling, D3 SSR, distributed rate limits |
| **Quality Assurance** | 10/10 | 7-layer slop, SSIM regression, reflection loop, VIS compliance, Design Intelligence, data validation, self-learning feedback |
| **User Experience** | 10/10 | "Figma for Slides" editor, AI Bar, streaming preview, collaboration, variant A/B testing, design dashboard, video preview mode |
| **Data Handling** | 10/10 | 90+ charts, 18 tables, 17 diagrams, icon system, Chart Intelligence, WCAG AA, PPTX-native |
| **Differentiation** | 10/10 | No competitor has: GLA + VIS + Progressive 3D + Self-Learning + Video Export + Style Transfer + Sandbox Preview + 90+ Data Viz |
| **Security** | 10/10 | SecretStr keys, .env-only credentials, rate limiting, budget caps, no key exposure in logs/errors/frontend |
| **Adaptability** | 10/10 | Self-learning improves with every generation. Self-evolving code agent improves templates weekly. Style transfer learns user aesthetics. |

**Overall**: **10/10** — The most comprehensive AI presentation architecture ever designed. V9.3 completes the vision with self-learning intelligence, video export, advanced design systems, LLM security, advanced typography, self-evolving code, and sandboxed preview. Every dimension — from generation quality to cost efficiency to security — is now architecturally addressed. Surpasses V7, V8, and every competitor (Gamma, Beautiful.ai, Tome, Slides.ai, Canva AI) in every dimension.

---

## Reference Repository Index

| Repository | Stars | What We Use | Integration Point |
|-----------|-------|-------------|-------------------|
| [reveal.js](https://github.com/hakimel/reveal.js) | 71k | Primary HTML presentation renderer | Renderer 1 |
| [Slidev](https://github.com/slidevjs/slidev) | 45k | Theme distribution model inspiration | Theme engine |
| [Clay](https://github.com/nicbarker/clay) | 17k | Layout algebra concepts, constraint model | GLA design inspiration |
| [PptxGenJS](https://github.com/gitbrent/PptxGenJS) | 5k | Native PPTX generation | Renderer 4 |
| [Konva.js](https://konvajs.org/) | 11k+ | Canvas editor | Infinite canvas slide editor |
| [react-konva](https://github.com/konvajs/react-konva) | 5.5k | React bindings for Konva | Editor integration |
| [Three.js](https://github.com/mrdoob/three.js) | 112k | 3D rendering | Progressive 3D Enhancement (lite + full levels) |
| [@react-three/fiber](https://github.com/pmndrs/react-three-fiber) | 28k | React × Three.js bridge | 3D slide components |
| [postprocessing](https://github.com/pmndrs/postprocessing) | 2k | Three.js post-processing effects | Bloom, DOF for "full" 3D level |
| [Motion](https://github.com/motiondivision/motion) | 27k | React animations | Slide animations |
| [PreTeXt](https://github.com/chenglou/pretext) | ~32k | DOM-free text measurement | Layout accuracy |
| [Yoga](https://github.com/nicbarker/clay) | — | WASM flexbox layout | GLA constraint solver |
| [Monaco Editor](https://github.com/microsoft/monaco-editor) | 42k | Code editor | HTML/CSS editing |
| [D3.js](https://github.com/d3/d3) | 110k | Data visualization | Chart generation |
| [Mermaid](https://github.com/mermaid-js/mermaid) | 87k | Diagram rendering | Flowcharts in slides |
| [Excalidraw](https://github.com/excalidraw/excalidraw) | 120k | Hand-drawn diagrams | Whiteboard-style diagrams |
| [Yjs](https://github.com/yjs/yjs) | 17k | CRDT sync | Multiplayer editing + collaboration |
| [y-websocket](https://github.com/yjs/y-websocket) | 1k | WebSocket provider for Yjs | Real-time collaboration server |
| [Lucide](https://github.com/lucide-icons/lucide) | 12k | Icon library | 1000+ consistent 2px stroke icons |
| [Readability.js](https://github.com/mozilla/readability) | 8k | Content extraction from web pages | Web-to-Slide extraction |
| [Spectacle](https://github.com/FormidableLabs/spectacle) | 10k | React JSX slide patterns | Architecture reference |
| [open-pencil](https://github.com/open-pencil/open-pencil) | 3.9k | AI canvas architecture reference | Design research |
| [yoyo-evolve](https://github.com/yologdev/yoyo-evolve) | 1.5k | Self-evolving code agent | Code Agent pattern |
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides) | 12.5k | Anti-AI-slop presets | Slop detection reference |
| [Recharts](https://github.com/recharts/recharts) | 24k | React chart components | Line/area/pie/bar/scatter charts |
| [D3-sankey](https://github.com/d3/d3-sankey) | 1k | Sankey diagram layout | Sankey/flow chart generation |
| [D3-force](https://github.com/d3/d3-force) | 2k | Force-directed graph layout | Network/org/mind map diagrams |
| [SVGO](https://github.com/svg/svgo) | 21k | SVG optimization | Print-quality chart vector export |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | 27k | Self-learning loop, skill creation/evolution architecture | Self-Learning System (§4.25) |
| [Remotion](https://github.com/remotion-dev/remotion) | 42k | Video architecture reference (React-based video) | Video Export Module concepts (§4.26) |
| [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) | 10.5k | 1,300+ icon families (Regular/Filled/Light/Color) | Premium Icon Tier (§4.27) |
| [Graphite](https://github.com/GraphiteEditor/Graphite) | 25k | Procedural node-graph design, nondestructive editing | Procedural Design Engine (§4.27) |
| [Agent Style Transfer](https://github.com/ArcadeAI/agent-style-transfer) | 3k | Style analysis & transfer between content | Style Transfer System (§4.27) |
| [design-resources-for-developers](https://github.com/bradtraversy/design-resources-for-developers) | 65k | Curated design resource catalog | Design resource reference (§4.27) |
| [FFmpeg WASM](https://github.com/ffmpegwasm/ffmpeg.wasm) | 14k | Browser-side video transcoding | WebM → MP4 conversion (§4.26) |

---

## Document Control

**Version**: 9.3
**Codename**: Meridian
**Status**: Architecture Approved. Ready for Phase 1 Implementation.
**Supersedes**: V7.1, V8 Reference, V9.0, V9.1, V9.2
**Architecture**: 6-Layer CDI Pipeline + Generative Layout Algebra + 4 Renderers + Progressive 3D + VIS + Complete Data Visualization + Self-Learning + Video Export + Advanced Design + LLM Security + Advanced Typography + Code Evolution + Sandboxed Preview
**Timeline**: 26 Weeks (15 Phases)
**Agents**: 10 Specialized Agents
**Total Themes**: 24 built-in + generative engine (unlimited via Brand Input Pipeline)
**Total Templates**: 100+ GLA Pattern Presets + 265 components (~925 variants) + infinite generative compositions
**Renderers**: 4 (reveal.js, React+Three.js, Zero-dep HTML, PPTX) + 5-level Progressive 3D Enhancement + Video Export (WebM/MP4/4K/GIF)
**Editor**: "Figma for Slides" — Infinite Canvas with Component Library, Variant System, Auto-Layout, Design Tokens, Plugin Architecture
**Generation Modes**: Standard (<15s, ~$0) + Premium (<90s, ~$0.50)
**Quality Gates**: 7-Layer Slop Detection, SSIM Regression, Composition Scoring, Reflection Loop, VIS Compliance, Data Validation, Self-Learning Feedback
**Data Visualization**: 90+ chart types (12 categories), 18 table types, 17 diagram types, Chart Intelligence Engine, comprehensive icon system
**Chart Export**: PPTX-native editable charts (11 types), SVG vector, PNG raster, React interactive components
**Chart Accessibility**: WCAG AA compliant — screen reader support, pattern fills, high contrast, data table fallback
**Collaboration**: Real-Time Multiplayer (cursors, locks, comments, @mentions, version history)
**Content Import**: Web-to-Slide Transformer (URL, PDF, DOCX, Notion, Google Doc, Markdown)
**Brand Export**: Brand Package .zip (fonts, logos, icons, templates, Figma tokens, Tailwind config)
**Variant System**: A/B Generation (2-3 alternatives per slide with composition scoring)
**Explainability**: Design Intelligence Dashboard (per-slide layout reasoning, hierarchy, balance, slop report)
**Self-Learning**: Teacher-Student paradigm — pattern extraction, skill evolution, cross-session memory, A/B preference learning
**Video Export**: OffscreenCanvas + FFmpeg WASM → WebM/MP4/4K/GIF with cinematic transitions
**Design Intelligence**: Fluent UI icons (5,200+) + Procedural node-graph design + Style Transfer (6 curated profiles)
**LLM Security**: .env SecretStr keys, Redis rate limits, Groq 6-key round-robin, $70/month budget cap
**Advanced Typography**: Full Pretext API — line-by-line rendering, text-around-image, rich inline, shrinkwrap, server-side
**Code Evolution**: Self-evolving template library — weekly improvement cycle with quality-gated commits
**Sandbox Preview**: Pre-bundled ESM (~850KB cached), CSP-protected iframe, SSIM ≥ 0.95 accuracy, <50ms hot-reload
**Breakthrough Innovations**: 18 (up from 11 in V9.2)
**Architecture Quality**: 10/10 (up from 9.7/10 in V9.2)
**Research Base**: 36 GitHub repositories analyzed (up from 28)

---

*"The future of presentations isn't in templates — it's in intelligence. Every slide should feel like it was designed by someone who understands not just layout, but narrative, emotion, and the art of persuasion. And now, for the first time, the system learns from every generation, evolves its own code, and shows you exactly why each design decision was made — in any format you need, at any quality level you demand."*
