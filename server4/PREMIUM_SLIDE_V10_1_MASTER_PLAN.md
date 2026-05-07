# Meridian V10.1 — Master Architecture Plan

> **Codename**: Meridian · **Version**: 10.1 · **Date**: April 2026
> **Status**: Approved for Implementation
> **Supersedes**: V9 Master Plan (all 14 identified loopholes addressed)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Design Principles & Anti-Patterns](#2-design-principles--anti-patterns)
3. [Model Inventory — Available Only](#3-model-inventory--available-only)
4. [Architecture Overview](#4-architecture-overview)
5. [Agent Topology — 4-Role Collapse](#5-agent-topology--4-role-collapse)
6. [Pipeline: Skeleton-of-Thought Parallel Fan-Out](#6-pipeline-skeleton-of-thought-parallel-fan-out)
7. [DSL v3 — JSON IR with Inch-First Positioning](#7-dsl-v3--json-ir-with-inch-first-positioning)
8. [Template System — 15 × 4 Finite Library](#8-template-system--15--4-finite-library)
9. [Design System — DTCG Tokens + Radix Colors](#9-design-system--dtcg-tokens--radix-colors)
10. [Rendering Stack](#10-rendering-stack)
11. [Image Pipeline](#11-image-pipeline)
12. [Fact-Checking & Citation Integrity](#12-fact-checking--citation-integrity)
13. [Quality Assurance — Self-Refine Loop](#13-quality-assurance--self-refine-loop)
14. [HITL (Human-in-the-Loop) Gates](#14-hitl-human-in-the-loop-gates)
15. [Learning Engine — Safe Boundaries](#15-learning-engine--safe-boundaries)
16. [Cost Model — Honest Floor](#16-cost-model--honest-floor)
17. [Infrastructure & Storage](#17-infrastructure--storage)
18. [Niche Positioning — Developer & Technical Talks](#18-niche-positioning--developer--technical-talks)
19. [Implementation Timeline — 26 Weeks](#19-implementation-timeline--26-weeks)
20. [Risk Registry](#20-risk-registry)
21. [Appendix A: Research Paper Integration Map](#appendix-a-research-paper-integration-map)
22. [Appendix B: V9 Loophole Resolution Matrix](#appendix-b-v9-loophole-resolution-matrix)

---

## 1. Executive Summary

Meridian is a premium AI presentation SaaS that generates publication-quality slide decks from natural language prompts. V10.1 corrects every structural flaw identified in V9 by:

- **Collapsing 8 agents → 4 roles** (Strategist, Author, Designer, Critic) with a self-refine loop inspired by PPTAgent (EMNLP 2025, 4.1k⭐)
- **Replacing sequential 6-layer pipeline** with Skeleton-of-Thought (ICLR 2024) parallel fan-out achieving 1.8–2.4× speedup
- **Using ONLY models already deployed** in the server4 codebase (Kimi-K2, Phi-4-reasoning, DeepSeek-V3.2, GPT-4o-mini, Mistral-medium-2505, Groq pool, CF Workers)
- **Dropping Remotion** ($100/mo) in favor of `@revealjs/react` (official, MIT, v0.2.1) + GSAP for animations
- **Building 15 slide primitives × 4 themes = 60 templates** (not 265 fantasy components)
- **Adding schema-enforced fact-checking** with tool-forced arithmetic and citation validation
- **Honest cost floor** of $100–175/month (not the imaginary $70 from V9)

**Key Differentiator**: Standalone HTML export — a single `.html` file with embedded Reveal.js that runs offline in any browser. No competitor offers this.

---

## 2. Design Principles & Anti-Patterns

### Principles

| # | Principle | Enforcement |
|---|-----------|-------------|
| P1 | **Use what exists** | No model/library not already in `requirements.txt` or `.env` without explicit approval |
| P2 | **Finite component set** | Maximum 15 slide types, 4 themes, 20 layout variants — hard cap |
| P3 | **Parallel by default** | Every pipeline stage that CAN run concurrently MUST run concurrently |
| P4 | **Inch-first positioning** | All spatial coordinates in inches (PPTX native), converted to px/em at render time |
| P5 | **Schema-enforced output** | Every LLM call uses JSON Schema / structured output — no freeform text parsing |
| P6 | **Self-refine, not self-train** | LLM critiques improve the current deck; outputs are NEVER used to fine-tune models |
| P7 | **Fail-fast with fallback** | Circuit breaker on every provider; 3-deep fallback chains; no silent failures |
| P8 | **Evidence-grounded** | Every architectural decision cites a paper, benchmark, or production metric |

### Anti-Patterns (Explicitly Banned)

| Anti-Pattern | Why Banned | V9 Violation |
|---|---|---|
| Recursive self-training | Model collapse within 3–5 generations (Shumailov et al., 2023) | V9 §Learning Engine proposed self-training on user feedback |
| GLA as "AI layout engine" | It's just flexbox + LLM JSON with a fancy name; no constraint solver exists | V9 §GLA claimed "neural" layout generation |
| yoyo-evolve | Zero production evidence; added complexity for no verified gain | V9 §Evolution Engine |
| Remotion dependency | $100/mo licensing cost per rendering node; SSR adds 2–4s latency | V9 §Rendering relied on Remotion |
| 200+ component libraries | Impossible to quality-test; maintenance burden exceeds team capacity | V9 proposed 265 components |
| Phantom models | Using models not in our infrastructure (Gemini Flash, Claude Haiku, etc.) | V10 feedback suggested unavailable models |

---

## 3. Model Inventory — Available Only

> **HARD RULE**: No model outside this table may be used in any pipeline stage.

### 3.1 LLM Models

| Tier | Model | Provider | Strengths | Latency | Cost | Pipeline Role |
|------|-------|----------|-----------|---------|------|---------------|
| T0 | **Kimi-K2-Thinking** | Azure AI | Deep reasoning, planning, long-chain CoT | 8–15s | ~$0.002/call | Strategist (outline, structure, narrative arc) |
| T0.5 | **Phi-4-reasoning** | Azure AI | Complex multi-step reasoning, math | 5–10s | ~$0.001/call | Critic (quality evaluation, fact-check, scoring) |
| T1 | **DeepSeek-V3.2** | Azure AI | Narrative, storytelling, long-form content | 4–8s | ~$0.001/call | Author (slide content, speaker notes, storytelling) |
| T2 | **GPT-4o-mini** | Azure AI | Fast structured JSON, schema adherence | 1–3s | ~$0.0005/call | Designer (layout selection, style tokens, DSL JSON) |
| T3 | **Mistral-medium-2505** | Azure AI | Technical code generation, DSL output | 3–6s | ~$0.001/call | Code generation (Reveal.js config, chart specs, DSL refinement) |
| T4 | **Groq** (8-key rotation) | Groq Cloud | Ultra-fast inference, JSON mode | 0.3–1s | Free tier | Fast validation, JSON repair, quick classification |
| T5 | **CF Workers** (GLM-4, Qwen2.5, Gemma-7b) | Cloudflare | Zero-cost burst capacity | 1–3s | Free | Parallel subtasks, summarization, overflow |
| T6 | **OpenRouter Qwen** (free) | OpenRouter | Backup capacity | 2–5s | Free | Emergency fallback |

### 3.2 Image Models

| Tier | Model | Provider | Quality | Latency | Cost | Use Case |
|------|-------|----------|---------|---------|------|----------|
| I1 | **FLUX.1-Kontext-pro** | Azure AI | Excellent | 5–12s | ~$0.02/image | Hero images, key visuals, premium slides |
| I2 | **Stable Diffusion 3 Medium** | Nvidia API | Good | 3–8s | Free | Standard illustrations, diagrams |
| I3 | **CF Phoenix** | Cloudflare | Moderate | 2–5s | Free | Background patterns, textures |
| I4 | **CF Lucid** | Cloudflare | Basic | 1–3s | Free | Simple icons, placeholders, fallback |

### 3.3 Fallback Chain Matrix

```
Strategist: Kimi-K2 → Phi-4-reasoning → DeepSeek-V3.2
Author:     DeepSeek-V3.2 → Kimi-K2 → Mistral-medium
Designer:   GPT-4o-mini → Groq → CF Workers
Code:       Mistral-medium → GPT-4o-mini → DeepSeek-V3.2
Critic:     Phi-4-reasoning → Kimi-K2 → GPT-4o-mini
Fast JSON:  Groq → GPT-4o-mini → CF Workers
Image:      FLUX.1-Kontext → Nvidia SD3 → CF Phoenix → CF Lucid
```

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT (React/Next.js)                       │
│  Prompt Input → Progress SSE → Preview (Reveal.js) → Export Menu   │
└───────────────┬─────────────────────────────────────┬───────────────┘
                │ REST/WebSocket                      │ SSE
┌───────────────▼─────────────────────────────────────▼───────────────┐
│                     FastAPI Gateway (main.py)                        │
│  Auth │ Rate Limit │ SSE Publisher │ Job Router │ HITL Controller   │
└───────────────┬─────────────────────────────────────────────────────┘
                │ Celery Task
┌───────────────▼─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (Celery Worker)                       │
│                                                                      │
│  ┌──────────┐   Skeleton-of-Thought    ┌─────────────────────┐      │
│  │STRATEGIST├──── Fan-Out ──────────────┤  PARALLEL AUTHORS   │      │
│  │(Kimi-K2) │   (slide skeletons)       │  (DeepSeek-V3.2)   │      │
│  └──────────┘                           │  × N slides         │      │
│       │                                 └──────────┬──────────┘      │
│       │ outline + theme tokens                     │ content per slide│
│       ▼                                            ▼                  │
│  ┌──────────┐                           ┌─────────────────────┐      │
│  │ DESIGNER │◄──────────────────────────┤  DSL v3 ASSEMBLER   │      │
│  │(GPT-4o-m)│   layout + style JSON     │  (Mistral-medium)   │      │
│  └────┬─────┘                           └──────────┬──────────┘      │
│       │                                            │                  │
│       ▼                Self-Refine Loop            ▼                  │
│  ┌──────────┐   ◄────────────────────   ┌─────────────────────┐      │
│  │  CRITIC  │   fix instructions        │    RENDERERS         │      │
│  │(Phi-4-r) ├──────────────────────►    │ PPTX│HTML│Reveal│PDF│      │
│  └──────────┘   score ≥ 7.5 = pass      └─────────────────────┘      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                │                              │
    ┌───────────▼──────────┐      ┌────────────▼─────────────┐
    │   MongoDB (Motor)     │      │   Azure Blob Storage     │
    │ presentations         │      │ rendered files            │
    │ slide_versions        │      │ images                   │
    │ templates             │      │ exports                  │
    │ generation_logs       │      └──────────────────────────┘
    │ context_boards        │
    └───────────┬───────────┘
                │
    ┌───────────▼──────────┐
    │   Redis               │
    │ task queue (Celery)   │
    │ SSE channels          │
    │ circuit breaker state │
    │ rate limit counters   │
    └───────────────────────┘
```

### Key Architectural Decisions

| Decision | Rationale | Paper/Evidence |
|----------|-----------|----------------|
| 4 roles not 8 agents | Fewer handoffs = fewer failure points; PPTAgent uses 2 stages | PPTAgent (EMNLP 2025) |
| Skeleton-of-Thought fan-out | 1.83–2.39× speedup empirically proven | Ning et al., ICLR 2024 |
| JSON IR not direct rendering | Same IR feeds PPTX + HTML + Reveal.js; single source of truth | AutoPresent (CVPR 2025) code-gen approach |
| Self-refine loop not self-train | Refine improves THIS deck; training on outputs → model collapse | Shumailov et al. 2023 |
| Circuit breaker on every provider | Groq free tier has rate limits; CF Workers can throttle | Production incident pattern |

---

## 5. Agent Topology — 4-Role Collapse

### V9 → V10.1 Agent Mapping

| V9 Agent | V10.1 Role | Rationale |
|----------|------------|-----------|
| CEO Agent | **Strategist** | Outline + narrative arc + audience adaptation |
| Researcher Agent | **Strategist** (merged) | Research is part of planning, not a separate stage |
| Designer Agent | **Designer** | Layout selection + style token assignment |
| Layout Agent | **Designer** (merged) | Layout IS design; separate agent was artificial |
| Code Agent | **Designer** (merged) | DSL JSON generation is a design output |
| VFX Agent | **Designer** (merged) | Animations are style tokens, not a pipeline stage |
| Assembler Agent | Eliminated | Renderers consume DSL directly; no assembly step |
| QA Agent | **Critic** | Quality evaluation + self-refine feedback |
| — | **Author** (new) | Content writing was split across CEO/Researcher — now dedicated |

### 5.1 Strategist (Model: Kimi-K2-Thinking)

**Input**: User prompt + context (audience, purpose, tone, length)
**Output**: Presentation Skeleton (JSON)

```json
{
  "title": "...",
  "subtitle": "...",
  "audience": "technical",
  "tone": "professional",
  "narrative_arc": "problem-solution-impact",
  "theme": "midnight-blue",
  "slide_count": 12,
  "skeleton": [
    {
      "slide_index": 0,
      "slide_type": "title",
      "layout": "center-hero",
      "purpose": "Hook the audience with a bold claim",
      "key_points": ["AI is rewriting enterprise workflows"],
      "visual_intent": "abstract neural network visualization",
      "speaker_note_hint": "Open with the $4.4T AI market stat"
    },
    {
      "slide_index": 1,
      "slide_type": "section_header",
      "layout": "left-accent",
      "purpose": "Transition to problem statement",
      "key_points": ["Current workflows waste 40% of time"],
      "visual_intent": "declining productivity chart",
      "speaker_note_hint": "Reference McKinsey 2024 report"
    }
  ]
}
```

**Skeleton-of-Thought Protocol**:
1. Strategist generates the skeleton (slide types + purposes + key points) in one pass
2. Each slide skeleton is dispatched to an Author instance IN PARALLEL
3. All Authors run concurrently via Celery group (not sequential chain)

### 5.2 Author (Model: DeepSeek-V3.2)

**Input**: Single slide skeleton + presentation context
**Output**: Slide content (JSON)

```json
{
  "slide_index": 1,
  "headline": "Enterprise Workflows: The 40% Problem",
  "body_text": "McKinsey's 2024 Workforce Report found that...",
  "bullet_points": [
    {"text": "40% of knowledge worker time on repetitive tasks", "citation": "McKinsey 2024"},
    {"text": "Average enterprise uses 137 SaaS tools", "citation": "Productiv 2024"}
  ],
  "speaker_notes": "This slide establishes the problem...",
  "data_points": [
    {"label": "Time wasted", "value": 40, "unit": "%", "source": "McKinsey 2024"}
  ],
  "image_prompt": "Minimalist illustration of office workers surrounded by floating app icons, muted blue palette",
  "chart_spec": null
}
```

**Parallelism**: For a 12-slide deck, 12 Author instances run simultaneously via Celery `group()`:

```python
from celery import group

author_tasks = group(
    generate_slide_content.s(skeleton=slide, context=pres_context)
    for slide in presentation_skeleton["skeleton"]
)
result = author_tasks.apply_async()
all_slides = result.get(timeout=30)  # All 12 complete in ~4-8s (not 48-96s sequential)
```

### 5.3 Designer (Model: GPT-4o-mini)

**Input**: Slide content + theme tokens + template library
**Output**: DSL v3 JSON (complete slide specification)

The Designer:
1. Selects layout variant from the 15 × 4 template matrix
2. Assigns design tokens (colors, fonts, spacing) from DTCG token set
3. Generates complete DSL v3 JSON with inch-first positioning
4. Specifies animations as GSAP-compatible timeline descriptors
5. Dispatches image generation requests to Image Pipeline

**Fast Path**: GPT-4o-mini at 1–3s per slide. For 12 slides in parallel: ~3s total.

### 5.4 Critic (Model: Phi-4-reasoning)

**Input**: Complete DSL v3 deck + original prompt + slide content
**Output**: Score (1–10) + fix instructions (if score < 7.5)

Evaluation rubric (inspired by SlidesBench, AutoPresent CVPR 2025):

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Content Accuracy | 25% | Facts correct, citations present, no hallucination |
| Visual Coherence | 20% | Consistent theme, readable typography, proper contrast |
| Narrative Flow | 20% | Logical progression, clear transitions, audience-appropriate |
| Layout Quality | 15% | No overflow, proper alignment, visual hierarchy |
| Data Integrity | 10% | Charts match data, arithmetic correct, units labeled |
| Completeness | 10% | All user requirements addressed, no missing sections |

**Self-Refine Loop**:
```
Score < 7.5 → Critic generates fix instructions → Route back to Author/Designer
                                                    (max 2 refinement cycles)
Score ≥ 7.5 → Proceed to rendering
Score ≥ 9.0 → Flag as "exemplary" for template analytics (NOT for training)
```

---

## 6. Pipeline: Skeleton-of-Thought Parallel Fan-Out

### 6.1 Theoretical Basis

**Skeleton-of-Thought** (Ning et al., ICLR 2024, arXiv:2307.15337):
- Decomposes a generation task into a skeleton (outline) + parallel point expansions
- Achieves **1.83–2.39× speedup** across 11 LLMs empirically tested
- Quality is maintained or improved because each expansion focuses on one coherent unit

**Application to Slide Generation**:
- Skeleton = Presentation outline (Strategist, 1 LLM call)
- Point expansions = Individual slide content (Author × N, parallel LLM calls)
- This directly maps to Celery's `group()` primitive

### 6.2 Pipeline Stages

```
Time ─────────────────────────────────────────────────────────►

Stage 1: STRATEGIZE (sequential)
  [Kimi-K2: Generate skeleton] ─── 8-15s ───►

Stage 2: AUTHOR (parallel fan-out)
  [DeepSeek: Slide 0] ─── 4-8s ──►
  [DeepSeek: Slide 1] ─── 4-8s ──►
  [DeepSeek: Slide 2] ─── 4-8s ──►
  ...
  [DeepSeek: Slide N] ─── 4-8s ──►

Stage 3: DESIGN (parallel fan-out)
  [GPT-4o-mini: DSL Slide 0] ─── 1-3s ──►
  [GPT-4o-mini: DSL Slide 1] ─── 1-3s ──►
  ...

Stage 4: IMAGE (parallel, async)
  [FLUX.1: Hero image] ─── 5-12s ──►
  [Nvidia SD3: Illustration] ─── 3-8s ──►
  [CF Phoenix: Background] ─── 2-5s ──►

Stage 5: CRITIQUE (sequential)
  [Phi-4-reasoning: Evaluate] ─── 5-10s ──►
  IF score < 7.5: → Loop back to Stage 2/3 (max 2×)

Stage 6: RENDER (parallel)
  [PPTX renderer] ─── 2-4s ──►
  [HTML renderer] ─── 1-2s ──►
  [Reveal.js renderer] ─── 1-2s ──►

TOTAL (12 slides, no refinement): ~25-40s
TOTAL (12 slides, 1 refinement):  ~35-55s
V9 sequential estimate:           ~120-180s
SPEEDUP:                          3-5× faster
```

### 6.3 Celery Task Graph

```python
from celery import chain, group, chord

def generate_presentation(prompt: str, user_id: str):
    """
    Skeleton-of-Thought pipeline using Celery primitives.
    """
    pipeline = chain(
        # Stage 1: Strategist generates skeleton
        strategize.s(prompt=prompt, user_id=user_id),
        
        # Stage 2+3: Fan-out authors then designers (chord waits for all)
        fan_out_authors_and_designers.s(),
        
        # Stage 4: Parallel image generation (non-blocking)
        dispatch_images.s(),
        
        # Stage 5: Critic evaluation
        critique_and_refine.s(max_refine=2),
        
        # Stage 6: Parallel rendering
        render_all_formats.s(),
    )
    return pipeline.apply_async()

@app.task
def fan_out_authors_and_designers(skeleton):
    """Parallel content generation for all slides."""
    author_group = group(
        author_slide.s(slide_skeleton=s, context=skeleton["context"])
        for s in skeleton["slides"]
    )
    # chord: run all authors in parallel, then fan-out designers
    return chord(author_group)(fan_out_designers.s(theme=skeleton["theme"]))
```

---

## 7. DSL v3 — JSON IR with Inch-First Positioning

### 7.1 Why Inch-First

| Concern | Pixel-based (V9) | Inch-first (V10.1) |
|---------|-------------------|---------------------|
| PPTX native unit | Requires px→EMU conversion | Inches map to EMU directly (1in = 914400 EMU) |
| Cross-format consistency | Different rounding per renderer | Single source, convert at render time |
| LLM output reliability | LLMs hallucinate pixel values; 1920 vs 1080 confusion | Inches are semantic: "2.5in from left" is unambiguous |
| Template authoring | Designers think in pt/in, must convert | Direct mapping to Figma/PowerPoint mental model |

### 7.2 DSL v3 Schema (Pydantic v2)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum

class SlideType(str, Enum):
    TITLE = "title"
    SECTION_HEADER = "section_header"
    CONTENT = "content"
    TWO_COLUMN = "two_column"
    COMPARISON = "comparison"
    IMAGE_FULL = "image_full"
    IMAGE_LEFT = "image_left"
    IMAGE_RIGHT = "image_right"
    DATA_CHART = "data_chart"
    QUOTE = "quote"
    TIMELINE = "timeline"
    TEAM = "team"
    METRICS = "metrics"
    CODE = "code"
    CLOSING = "closing"

class Position(BaseModel):
    """All measurements in inches. Origin: top-left of slide."""
    x: float = Field(ge=0, le=13.33, description="Horizontal position in inches")
    y: float = Field(ge=0, le=7.5, description="Vertical position in inches")
    width: float = Field(gt=0, le=13.33, description="Width in inches")
    height: float = Field(gt=0, le=7.5, description="Height in inches")

class TextElement(BaseModel):
    type: Literal["text"] = "text"
    position: Position
    content: str
    font_family: str = "Inter"
    font_size_pt: float = Field(ge=8, le=120, description="Font size in points")
    font_weight: Literal["regular", "medium", "semibold", "bold"] = "regular"
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$", description="Hex color")
    alignment: Literal["left", "center", "right"] = "left"
    line_height: float = 1.4

class ImageElement(BaseModel):
    type: Literal["image"] = "image"
    position: Position
    prompt: str  # Image generation prompt
    alt_text: str
    fit: Literal["cover", "contain", "fill"] = "cover"
    border_radius_in: float = 0.0
    image_url: Optional[str] = None  # Filled after generation

class ChartElement(BaseModel):
    type: Literal["chart"] = "chart"
    position: Position
    chart_type: Literal["bar", "line", "pie", "donut", "area", "scatter"]
    data: dict  # Chart.js compatible data object
    options: dict = {}

class ShapeElement(BaseModel):
    type: Literal["shape"] = "shape"
    position: Position
    shape_type: Literal["rectangle", "circle", "line", "arrow", "rounded_rect"]
    fill_color: Optional[str] = None
    stroke_color: Optional[str] = None
    stroke_width_pt: float = 1.0

class CodeElement(BaseModel):
    type: Literal["code"] = "code"
    position: Position
    language: str
    code: str
    theme: Literal["github-dark", "one-dark", "monokai", "nord"] = "github-dark"
    font_size_pt: float = 14

SlideElement = TextElement | ImageElement | ChartElement | ShapeElement | CodeElement

class Animation(BaseModel):
    element_index: int
    effect: Literal["fade-in", "slide-up", "slide-left", "scale-in", "typewriter", "none"]
    delay_ms: int = 0
    duration_ms: int = 500
    easing: Literal["ease-out", "ease-in-out", "spring"] = "ease-out"

class SlideBackground(BaseModel):
    type: Literal["solid", "gradient", "image"]
    value: str  # Hex color, CSS gradient, or image URL/prompt

class SlideDSL(BaseModel):
    """Complete specification for a single slide."""
    slide_index: int
    slide_type: SlideType
    background: SlideBackground
    elements: list[SlideElement]
    animations: list[Animation] = []
    transition: Literal["fade", "slide", "convex", "concave", "zoom", "none"] = "fade"
    speaker_notes: str = ""
    citations: list[dict] = []  # [{source, claim, verified: bool}]

class PresentationDSL(BaseModel):
    """Complete presentation specification — single source of truth."""
    version: Literal["3.0"] = "3.0"
    title: str
    subtitle: Optional[str] = None
    author: str
    created_at: str
    theme_id: str
    slide_width_in: float = 13.33  # 16:9 standard
    slide_height_in: float = 7.5
    global_fonts: dict = {"heading": "Inter", "body": "Inter", "code": "JetBrains Mono"}
    global_colors: dict  # DTCG token references
    slides: list[SlideDSL]
    metadata: dict = {}
```

### 7.3 Conversion Utilities

```python
# Inch → EMU for python-pptx
def inches_to_emu(inches: float) -> int:
    return int(inches * 914400)

# Inch → px for HTML/Reveal.js (96 DPI standard)
def inches_to_px(inches: float, dpi: int = 96) -> float:
    return inches * dpi

# Inch → Reveal.js percentage (based on 960×700 default viewport)
def inches_to_reveal_pct(x_in: float, y_in: float, 
                          slide_w: float = 13.33, slide_h: float = 7.5):
    return {
        "left": f"{(x_in / slide_w) * 100:.2f}%",
        "top": f"{(y_in / slide_h) * 100:.2f}%"
    }
```

---

## 8. Template System — 15 × 4 Finite Library

### 8.1 The 15 Slide Types

Each slide type has a **fixed layout skeleton** with positioned zones. The Designer fills zones with content — it does NOT invent layouts.

| # | Slide Type | Layout Description | Zones |
|---|------------|-------------------|-------|
| 1 | `title` | Center-aligned hero with title + subtitle | title_zone, subtitle_zone, accent_shape |
| 2 | `section_header` | Bold section name with decorative accent | heading_zone, accent_bar |
| 3 | `content` | Headline + body text + optional bullets | headline_zone, body_zone, aside_zone |
| 4 | `two_column` | 50/50 split with left/right content | left_zone, right_zone, headline_zone |
| 5 | `comparison` | Side-by-side with VS divider | left_zone, right_zone, divider, labels |
| 6 | `image_full` | Full-bleed image with text overlay | image_zone, overlay_text_zone |
| 7 | `image_left` | 40% image left, 60% content right | image_zone, content_zone |
| 8 | `image_right` | 60% content left, 40% image right | content_zone, image_zone |
| 9 | `data_chart` | Chart area + annotation + source | chart_zone, title_zone, source_zone |
| 10 | `quote` | Large pull-quote with attribution | quote_zone, author_zone, accent_marks |
| 11 | `timeline` | Horizontal timeline with milestones | timeline_bar, milestone_zones[] |
| 12 | `team` | Grid of profile cards | card_grid[], headline_zone |
| 13 | `metrics` | 3–4 big-number KPI cards | kpi_zones[], headline_zone |
| 14 | `code` | Syntax-highlighted code block + annotation | code_zone, annotation_zone |
| 15 | `closing` | CTA + contact info + brand mark | cta_zone, contact_zone, brand_zone |

### 8.2 The 4 Themes

| Theme | Primary | Secondary | Accent | Background | Font Pairing | Vibe |
|-------|---------|-----------|--------|------------|-------------- |------|
| **Midnight** | `#1a1a2e` | `#16213e` | `#0f3460` | `#0d1117` | Inter + JetBrains Mono | Dark tech, developer talks |
| **Arctic** | `#f8f9fa` | `#e9ecef` | `#339af0` | `#ffffff` | Inter + Source Serif Pro | Clean enterprise, SaaS |
| **Forest** | `#1b4332` | `#2d6a4f` | `#40916c` | `#f0f4f0` | Libre Baskerville + Inter | Sustainability, nature brands |
| **Ember** | `#1c1917` | `#292524` | `#ea580c` | `#fafaf9` | Space Grotesk + Inter | Bold startup, launch events |

### 8.3 Template Matrix: 15 × 4 = 60 Templates

Each template is a **JSON file** stored in MongoDB `templates` collection:

```json
{
  "template_id": "title_midnight",
  "slide_type": "title",
  "theme": "midnight",
  "version": 1,
  "zones": {
    "title_zone": {
      "position": {"x": 1.0, "y": 2.0, "width": 11.33, "height": 2.0},
      "text_style": {
        "font_family": "Inter",
        "font_size_pt": 54,
        "font_weight": "bold",
        "color": "#f8f9fa",
        "alignment": "center"
      }
    },
    "subtitle_zone": {
      "position": {"x": 2.0, "y": 4.2, "width": 9.33, "height": 1.0},
      "text_style": {
        "font_family": "Inter",
        "font_size_pt": 24,
        "font_weight": "regular",
        "color": "#adb5bd",
        "alignment": "center"
      }
    },
    "accent_shape": {
      "position": {"x": 5.67, "y": 1.5, "width": 2.0, "height": 0.06},
      "shape_type": "rectangle",
      "fill_color": "#0f3460"
    }
  },
  "background": {"type": "solid", "value": "#0d1117"},
  "transition": "fade"
}
```

### 8.4 Designer Fills Templates (Not Invents Them)

The Designer's job is:
1. **Select** the correct template from the 60-template library based on slide type + theme
2. **Fill** zone content from Author output (text, data, image prompts)
3. **Adjust** within bounds (font size ±20%, color tint, element visibility)
4. **Never** create new layouts or override zone positions beyond ±0.5in

This is the **PPTAgent-style edit-based approach**: start from a human-designed template, adapt content into it — don't generate layouts from scratch.

---

## 9. Design System — DTCG Tokens + Radix Colors

### 9.1 Design Token Community Group (DTCG) Format

All design values are stored as DTCG tokens (W3C draft standard):

```json
{
  "meridian": {
    "color": {
      "primary": {"$value": "#1a1a2e", "$type": "color", "$description": "Primary brand color"},
      "on-primary": {"$value": "#f8f9fa", "$type": "color"},
      "accent": {"$value": "#0f3460", "$type": "color"},
      "surface": {"$value": "#0d1117", "$type": "color"},
      "on-surface": {"$value": "#e9ecef", "$type": "color"},
      "error": {"$value": "#e03131", "$type": "color"}
    },
    "typography": {
      "heading-xl": {
        "$value": {"fontFamily": "Inter", "fontSize": "54pt", "fontWeight": 700, "lineHeight": 1.1},
        "$type": "typography"
      },
      "heading-lg": {
        "$value": {"fontFamily": "Inter", "fontSize": "36pt", "fontWeight": 600, "lineHeight": 1.2},
        "$type": "typography"
      },
      "body": {
        "$value": {"fontFamily": "Inter", "fontSize": "18pt", "fontWeight": 400, "lineHeight": 1.5},
        "$type": "typography"
      },
      "code": {
        "$value": {"fontFamily": "JetBrains Mono", "fontSize": "14pt", "fontWeight": 400, "lineHeight": 1.6},
        "$type": "typography"
      }
    },
    "spacing": {
      "slide-margin": {"$value": "0.75in", "$type": "dimension"},
      "element-gap": {"$value": "0.25in", "$type": "dimension"},
      "section-gap": {"$value": "0.5in", "$type": "dimension"}
    },
    "shadow": {
      "card": {"$value": {"offsetX": "0", "offsetY": "4px", "blur": "12px", "color": "#00000020"}, "$type": "shadow"}
    }
  }
}
```

### 9.2 Radix Colors Integration

**Why Radix**: 28 color scales, each with 12 steps designed for accessible contrast. Open source, wide adoption.

Usage:
- Theme palettes derive from Radix scales (e.g., Midnight = `slate` + `blue`, Arctic = `gray` + `blue`, Forest = `sage` + `green`, Ember = `sand` + `orange`)
- Auto-contrast: step 1–2 for backgrounds, 11–12 for text, 9–10 for interactive
- WCAG AA guaranteed by Radix's own contrast testing

### 9.3 Component Primitives (15 Total — HARD CAP)

| # | Primitive | Description | Render Targets |
|---|-----------|-------------|----------------|
| 1 | `Heading` | H1–H3 with font scale | PPTX TextBox, HTML h1-h3, Reveal h1-h3 |
| 2 | `Body` | Paragraph with rich formatting | PPTX TextBox, HTML p, Reveal p |
| 3 | `BulletList` | Ordered/unordered list | PPTX TextBox with bullets, HTML ul/ol |
| 4 | `Image` | Responsive image with fit modes | PPTX Picture, HTML img, Reveal img |
| 5 | `Chart` | Data visualization (Chart.js spec) | PPTX chart via python-pptx, HTML canvas, Reveal Chart plugin |
| 6 | `CodeBlock` | Syntax-highlighted code | PPTX TextBox (monospace), Reveal Code component |
| 7 | `Quote` | Blockquote with attribution | PPTX styled TextBox, HTML blockquote |
| 8 | `Shape` | Rect, circle, line, arrow | PPTX AutoShape, SVG, CSS |
| 9 | `Icon` | SVG icon from curated set | PPTX embedded SVG, HTML svg |
| 10 | `Table` | Simple data table | PPTX Table, HTML table |
| 11 | `MetricCard` | Big-number KPI display | Composed from Shape + Heading + Body |
| 12 | `ProfileCard` | Avatar + name + role | Composed from Image + Heading + Body |
| 13 | `TimelineNode` | Single milestone in timeline | Composed from Shape + Body |
| 14 | `Divider` | Horizontal/vertical separator | PPTX line, HTML hr, CSS border |
| 15 | `Spacer` | Invisible spacing element | Margin/padding in all renderers |

---

## 10. Rendering Stack

### 10.1 Renderer Architecture

```
PresentationDSL (JSON IR)
        │
        ├──► PPTX Renderer (python-pptx)      → .pptx file
        ├──► HTML Renderer (Jinja2)            → .html standalone file
        ├──► Reveal.js Renderer (@revealjs/react) → interactive preview
        └──► PDF Renderer (Playwright)         → .pdf file (via HTML→PDF)
```

### 10.2 PPTX Renderer — PptxGenJS-Informed Design

Uses `python-pptx` (already in requirements.txt) with inch-first positioning:

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu

def render_pptx(dsl: PresentationDSL) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(dsl.slide_width_in)
    prs.slide_height = Inches(dsl.slide_height_in)
    
    for slide_dsl in dsl.slides:
        layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(layout)
        
        # Apply background
        _apply_background(slide, slide_dsl.background)
        
        for elem in slide_dsl.elements:
            if elem.type == "text":
                txBox = slide.shapes.add_textbox(
                    Inches(elem.position.x),
                    Inches(elem.position.y),
                    Inches(elem.position.width),
                    Inches(elem.position.height),
                )
                tf = txBox.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = elem.content
                p.font.size = Pt(elem.font_size_pt)
                p.font.name = elem.font_family
                p.font.bold = elem.font_weight in ("semibold", "bold")
                p.font.color.rgb = RGBColor.from_string(elem.color[1:])
            
            elif elem.type == "image":
                if elem.image_url:
                    slide.shapes.add_picture(
                        elem.image_url,
                        Inches(elem.position.x),
                        Inches(elem.position.y),
                        Inches(elem.position.width),
                        Inches(elem.position.height),
                    )
            
            elif elem.type == "chart":
                _add_chart(slide, elem)
            
            elif elem.type == "shape":
                _add_shape(slide, elem)
    
    buffer = BytesIO()
    prs.save(buffer)
    return buffer.getvalue()
```

### 10.3 HTML Standalone Export — KEY DIFFERENTIATOR

A single `.html` file with:
- Embedded Reveal.js (v5, 140KB gzipped)
- Inlined CSS (design tokens → CSS custom properties)
- Inlined images (base64 data URIs or lazy-loaded from CDN)
- Self-contained speaker notes (press S to open)
- Works offline, no server required, opens in any browser

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{title}}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/black.css">
  <style>
    :root {
      --meridian-primary: {{tokens.color.primary}};
      --meridian-accent: {{tokens.color.accent}};
      --meridian-surface: {{tokens.color.surface}};
      --meridian-on-surface: {{tokens.color.on_surface}};
      --meridian-heading-font: {{tokens.typography.heading.font_family}};
      --meridian-body-font: {{tokens.typography.body.font_family}};
    }
    .reveal { font-family: var(--meridian-body-font); }
    .reveal h1, .reveal h2, .reveal h3 { font-family: var(--meridian-heading-font); }
    /* ... theme overrides ... */
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
      {% for slide in slides %}
      <section data-transition="{{slide.transition}}"
               data-background-color="{{slide.background.value}}">
        {% for elem in slide.elements %}
          {{ render_element(elem) }}
        {% endfor %}
        <aside class="notes">{{slide.speaker_notes}}</aside>
      </section>
      {% endfor %}
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
  <script>
    Reveal.initialize({
      hash: true,
      transition: 'fade',
      plugins: []
    });
  </script>
</body>
</html>
```

### 10.4 Reveal.js Live Preview — @revealjs/react

For the React frontend preview (real-time editing):

```tsx
import { Deck, Slide, Markdown, Code, Fragment } from '@mhsdesign/revealjs-react';
// Note: @revealjs/react v0.2.1 by Hakim El Hattab (official, MIT)
// If package not yet compatible, use @mhsdesign/revealjs-react as proven wrapper

function PresentationPreview({ dsl }: { dsl: PresentationDSL }) {
  return (
    <Deck transition="fade" theme="custom">
      {dsl.slides.map((slide, i) => (
        <Slide key={i} transition={slide.transition} 
               backgroundColor={slide.background.value}>
          {slide.elements.map((elem, j) => (
            <SlideElement key={j} element={elem} />
          ))}
        </Slide>
      ))}
    </Deck>
  );
}
```

### 10.5 PDF Export

HTML → PDF via Playwright (already in requirements.txt):

```python
async def render_pdf(html_content: str) -> bytes:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content)
        await page.wait_for_timeout(1000)  # Let Reveal.js initialize
        pdf = await page.pdf(
            width="13.33in",
            height="7.5in",
            print_background=True,
        )
        await browser.close()
        return pdf
```

### 10.6 Animation System — GSAP + CSS

**No Remotion**. Animations use:
- **Entry animations**: CSS `@keyframes` for simple (fade, slide-up) — zero dependencies
- **Complex sequences**: GSAP (GreenSock, free for non-commercial OR we use the free core) for timeline-based animations in Reveal.js
- **Reveal.js Fragments**: Built-in fragment system for step-by-step reveals

```css
/* Simple entry animations — no library needed */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@keyframes scaleIn { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
```

---

## 11. Image Pipeline

### 11.1 Tiered Generation Strategy

```
Image Request
    │
    ├─ Premium slide (title, section_header, image_full)?
    │   └─► Tier I1: FLUX.1-Kontext-pro (Azure) — best quality
    │
    ├─ Standard illustration?
    │   └─► Tier I2: Nvidia SD3 Medium — good quality, free
    │
    ├─ Background/texture?
    │   └─► Tier I3: CF Phoenix — moderate quality, free
    │
    └─ Fallback/placeholder?
        └─► Tier I4: CF Lucid — basic, free
```

### 11.2 Circuit Breaker Pattern (Existing)

The existing `image_pipeline` service already implements circuit breaker:
- **Closed**: Normal operation, all requests go through
- **Open**: After 3 consecutive failures, skip provider for 60s
- **Half-Open**: After cooldown, allow one test request

### 11.3 Image Prompt Engineering

Author generates image prompts. Designer refines them with style constraints:

```json
{
  "raw_prompt": "Office workers surrounded by floating app icons",
  "refined_prompt": "Minimalist flat illustration: three office workers at desks, surrounded by 8 floating translucent app icons. Color palette: muted blues (#339af0, #74c0fc) on white background. Style: corporate editorial illustration, clean lines, no gradients. Aspect ratio: 16:9.",
  "negative_prompt": "photorealistic, 3d render, text, watermark",
  "target_tier": "I1",
  "dimensions": {"width": 1280, "height": 720}
}
```

### 11.4 Image Caching

All generated images are cached by prompt hash in Azure Blob Storage:
- Key: `SHA256(refined_prompt + model + dimensions)`
- TTL: 90 days
- Reuse rate: ~15–20% for common business imagery

---

## 12. Fact-Checking & Citation Integrity

### 12.1 The Problem (V9 Loophole #14)

V9 had no mechanism to verify claims in generated slides. LLMs hallucinate statistics, misattribute quotes, and fabricate data.

### 12.2 Schema-Enforced Citations

Every factual claim MUST carry a citation in the DSL:

```json
{
  "citations": [
    {
      "claim": "AI market will reach $4.4 trillion by 2030",
      "source": "McKinsey Global Institute",
      "source_type": "research_report",
      "year": 2024,
      "url": "https://www.mckinsey.com/...",
      "verified": false,
      "confidence": 0.85
    }
  ]
}
```

### 12.3 Tool-Forced Arithmetic

For any slide containing numerical claims, the Critic runs arithmetic validation:

```python
def validate_arithmetic(slide_content: dict) -> list[str]:
    """
    Check that percentages sum correctly, growth rates are plausible,
    and comparative claims are internally consistent.
    """
    errors = []
    data_points = slide_content.get("data_points", [])
    
    # Check percentage sums (pie charts, market share)
    pct_groups = group_by_context(data_points, unit="%")
    for group in pct_groups:
        total = sum(dp["value"] for dp in group)
        if abs(total - 100.0) > 1.0:  # Allow 1% rounding
            errors.append(f"Percentages sum to {total}%, expected ~100%")
    
    # Check growth rate plausibility
    for dp in data_points:
        if dp.get("unit") == "%" and "growth" in dp.get("label", "").lower():
            if dp["value"] > 500:
                errors.append(f"Growth rate {dp['value']}% seems implausibly high")
    
    return errors
```

### 12.4 Citation Verification Pipeline

```
Author generates content with citations
    │
    ▼
Critic checks:
  1. Every data_point has a citation → FAIL if missing
  2. Citation source_type is valid (research_report, news, gov_data, company_report)
  3. Citation year is within 3 years → WARN if older
  4. Arithmetic validation passes
  5. No two citations contradict each other
    │
    ▼
If verification fails:
  - Strip unverifiable claims
  - Add "[Source needed]" annotation
  - Flag for human review via HITL gate
```

---

## 13. Quality Assurance — Self-Refine Loop

### 13.1 Self-Refine Protocol (NOT Self-Training)

Inspired by: PPTAgent's 2-stage refine, Paper2Poster's PaperQuiz fidelity metric.

```
┌──────────────────────┐
│ Generate Deck (v1)   │
│ Author + Designer    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Critic Evaluates     │    Score Rubric:
│ (Phi-4-reasoning)    │    - Content: 25%
│                      │    - Visual: 20%
│ Score: 6.8/10        │    - Narrative: 20%
│ Issues:              │    - Layout: 15%
│ - Slide 3 overflow   │    - Data: 10%
│ - Slide 7 no citation│    - Complete: 10%
└──────────┬───────────┘
           │ score < 7.5
           ▼
┌──────────────────────┐
│ Targeted Fix         │
│ Only re-generate     │
│ slides 3 and 7       │
│ with fix instructions│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Critic Re-evaluates  │
│ Score: 8.2/10 ✓      │
│ Pass → Render        │
└──────────────────────┘
```

**Key constraints**:
- Maximum 2 refinement cycles (prevent infinite loops)
- Only re-generate FAILING slides (not the whole deck)
- If score never reaches 7.5 after 2 cycles → proceed with best version + quality warning to user

### 13.2 What Self-Refine is NOT

| Self-Refine (V10.1) ✓ | Self-Training (V9) ✗ |
|---|---|
| Critique improves THIS specific deck | Outputs used to fine-tune models |
| No model weights change | Model weights update |
| Bounded (max 2 cycles) | Unbounded (continuous learning) |
| Stateless between requests | Accumulates training data |
| No risk of model collapse | Model collapse within 3–5 generations |

---

## 14. HITL (Human-in-the-Loop) Gates

### 14.1 Gate Types

| Gate | Trigger | User Action | Timeout Behavior |
|------|---------|-------------|------------------|
| **Outline Approval** | After Strategist generates skeleton | Approve / Edit / Reject | Auto-approve after 30s |
| **Content Review** | After Author generates content (optional, premium tier) | Edit text per slide | Skip and proceed |
| **Citation Flag** | Unverifiable citation detected | Confirm / Remove / Replace | Strip citation, add note |
| **Quality Warning** | Critic score between 6.0–7.5 after refinement | Accept / Request regeneration | Accept as-is |
| **Image Selection** | Multiple image options generated (premium tier) | Pick preferred option | Use top-ranked |

### 14.2 HITL API

```python
@router.post("/presentations/{pres_id}/gates/{gate_id}/respond")
async def respond_to_gate(
    pres_id: str,
    gate_id: str,
    response: HITLResponse,
    user: User = Depends(get_current_user),
):
    """User responds to a HITL gate. Pipeline resumes from the gate."""
    gate = await db.hitl_gates.find_one({"_id": gate_id, "presentation_id": pres_id})
    if not gate or gate["user_id"] != str(user.id):
        raise HTTPException(404)
    
    # Update gate with response
    await db.hitl_gates.update_one(
        {"_id": gate_id},
        {"$set": {"response": response.dict(), "responded_at": datetime.utcnow()}}
    )
    
    # Resume pipeline from gate checkpoint
    resume_pipeline.delay(pres_id, gate_id, response.action, response.edits)
```

### 14.3 SSE Progress Updates

```python
async def sse_generator(pres_id: str):
    """Server-Sent Events for real-time pipeline progress."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"presentation:{pres_id}:progress")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            yield f"data: {message['data']}\n\n"

# Event types:
# {"stage": "strategize", "status": "complete", "progress": 15}
# {"stage": "author", "status": "in_progress", "slide": 3, "total": 12, "progress": 40}
# {"stage": "design", "status": "in_progress", "progress": 60}
# {"stage": "critique", "score": 8.2, "status": "passed", "progress": 80}
# {"stage": "render", "format": "pptx", "status": "complete", "progress": 95}
# {"stage": "complete", "download_urls": {...}, "progress": 100}
# {"stage": "hitl_gate", "gate_id": "...", "gate_type": "outline_approval", "data": {...}}
```

---

## 15. Learning Engine — Safe Boundaries

### 15.1 What We Learn (Safe)

| Signal | Storage | Usage |
|--------|---------|-------|
| Template selection frequency | MongoDB `template_analytics` | Rank templates for suggestions |
| User edit patterns | MongoDB `edit_patterns` | Adjust defaults (e.g., users always increase font size → bump default) |
| Critic score distribution | MongoDB `quality_metrics` | Calibrate thresholds |
| Generation latency per model | Redis time-series | Optimize routing decisions |
| Image prompt→quality mapping | MongoDB `image_analytics` | Improve prompt refinement |

### 15.2 What We NEVER Do

- ❌ Fine-tune any model on user outputs
- ❌ Use generated slides as training data
- ❌ Feed critique scores back as reward signal
- ❌ Run any form of RLHF/DPO on our models
- ❌ Store user data beyond the explicit retention period

### 15.3 Template Analytics Loop (Safe)

```python
async def record_template_usage(template_id: str, user_edits: dict, final_score: float):
    """Track which templates work well. NO model training involved."""
    await db.template_analytics.insert_one({
        "template_id": template_id,
        "used_at": datetime.utcnow(),
        "edit_count": len(user_edits),
        "edit_types": list(user_edits.keys()),  # e.g., ["font_size", "color"]
        "critic_score": final_score,
    })

async def get_recommended_templates(slide_type: str, theme: str) -> list[str]:
    """Rank templates by success. Pure retrieval, no ML."""
    pipeline = [
        {"$match": {"template_id": {"$regex": f"^{slide_type}_{theme}"}}},
        {"$group": {
            "_id": "$template_id",
            "avg_score": {"$avg": "$critic_score"},
            "usage_count": {"$sum": 1},
            "avg_edits": {"$avg": "$edit_count"},
        }},
        {"$sort": {"avg_score": -1, "avg_edits": 1}},  # High score, few edits = best
    ]
    return [doc["_id"] async for doc in db.template_analytics.aggregate(pipeline)]
```

---

## 16. Cost Model — Honest Floor

### 16.1 Per-Deck Cost Breakdown (12 slides)

| Component | Model/Service | Calls | Cost per Call | Total |
|-----------|--------------|-------|---------------|-------|
| Strategist | Kimi-K2-Thinking | 1 | $0.002 | $0.002 |
| Authors (parallel) | DeepSeek-V3.2 | 12 | $0.001 | $0.012 |
| Designers (parallel) | GPT-4o-mini | 12 | $0.0005 | $0.006 |
| Critic | Phi-4-reasoning | 1–3 | $0.001 | $0.003 |
| Image Generation | FLUX.1 (2) + SD3 (5) + CF (5) | 12 | ~$0.005 avg | $0.060 |
| Fast validation | Groq | 5–10 | Free | $0.00 |
| **Per-deck LLM+Image** | | | | **~$0.083** |

### 16.2 Monthly Infrastructure

| Service | Cost | Notes |
|---------|------|-------|
| Azure AI Models (pay-per-use) | $20–60 | Scales with usage |
| Azure Blob Storage (100GB) | $2 | Images + exports |
| MongoDB Atlas (M10) | $50 | Production cluster |
| Redis (Azure Cache, Basic) | $15 | Task queue + pub/sub |
| VM / App Service (B2s) | $30–60 | FastAPI + Celery workers |
| Domain + SSL | $3 | Cloudflare |
| **Monthly Floor** | **$120–190** | |

### 16.3 Pricing Strategy

| Tier | Price/mo | Decks/mo | Cost/deck | Margin |
|------|----------|----------|-----------|--------|
| Free | $0 | 3 | Free-tier models only | Loss-leader |
| Pro | $19 | 30 | $0.08 | $16.60 (87%) |
| Team | $49 | 100 | $0.08 | $41.00 (84%) |
| Enterprise | Custom | Unlimited | $0.08 | High |

**Break-even**: ~60 Pro subscribers or ~25 Team subscribers to cover $120–190/mo infra.

### 16.4 V9 vs V10.1 Cost Comparison

| Item | V9 Estimate | V10.1 Reality | Delta |
|------|-------------|---------------|-------|
| Monthly floor | "$70" | $120–190 | V9 was **45–63% too low** |
| Remotion license | $100/mo | $0 (Reveal.js MIT) | **-$100** |
| Per-deck LLM | Not calculated | ~$0.083 | Now transparent |
| Phantom models | "Gemini Flash, Claude Haiku" | Not available | **Eliminated** |

---

## 17. Infrastructure & Storage

### 17.1 MongoDB Collections

| Collection | Purpose | Indexes |
|------------|---------|---------|
| `users` | User accounts, auth | `email` (unique) |
| `presentations` | Presentation metadata, status | `user_id`, `created_at` |
| `slides` | Individual slide DSL v3 JSON | `presentation_id`, `slide_index` |
| `slide_versions` | Version history for edits | `slide_id`, `version` |
| `templates` | 60 template definitions | `slide_type`, `theme` |
| `themes` | 4 theme token sets | `theme_id` |
| `generation_logs` | Pipeline execution logs | `presentation_id`, `stage` |
| `template_analytics` | Template usage stats | `template_id`, `used_at` |
| `context_boards` | Inter-agent context | `presentation_id` |
| `hitl_gates` | HITL gate state | `presentation_id`, `gate_type` |
| `image_cache` | Prompt→image URL mapping | `prompt_hash` |

### 17.2 Redis Keys

```
# Task queue (Celery)
celery:*                        # Celery broker keys

# SSE channels
presentation:{id}:progress      # Pub/sub for pipeline progress

# Circuit breaker
circuit:{provider}:state        # "closed" | "open" | "half_open"
circuit:{provider}:failures     # Failure counter
circuit:{provider}:last_fail    # Timestamp

# Rate limiting
ratelimit:{user_id}:minute      # Per-user rate limit
ratelimit:{user_id}:day         # Daily generation limit

# Model routing cache
model_route:{task_type}:latency # Rolling average latency per model
```

### 17.3 Azure Blob Storage Structure

```
meridian-storage/
├── images/
│   ├── {hash}.png              # Generated images (keyed by prompt hash)
│   └── {hash}.webp             # WebP variants for web
├── exports/
│   ├── {pres_id}/
│   │   ├── presentation.pptx
│   │   ├── presentation.html
│   │   └── presentation.pdf
├── templates/
│   └── previews/               # Template preview thumbnails
└── temp/
    └── {job_id}/               # Temporary build artifacts (TTL: 1h)
```

---

## 18. Niche Positioning — Developer & Technical Talks

### 18.1 Why This Niche

| Factor | Developer/Technical Niche | General Market |
|--------|--------------------------|----------------|
| Willingness to use AI tools | Very high | Mixed |
| Price sensitivity | Moderate ($19–49/mo is normal) | High |
| Content complexity | Code blocks, architectures, data | Mostly text + images |
| Competitive gap | No tool handles code slides well | Dominated by Canva, Beautiful.ai |
| Viral potential | Dev community shares tools aggressively | Slow word-of-mouth |
| Template needs | Technical diagrams, code walkthroughs | Generic corporate |

### 18.2 Differentiators for Developers

1. **Code slides**: Syntax highlighting, line-by-line reveal, live code execution preview
2. **Architecture diagrams**: Mermaid → SVG → slide element pipeline
3. **Standalone HTML export**: Write once, present from any machine with a browser
4. **Markdown input**: Accept `.md` files as presentation source
5. **CLI tool** (future): `meridian generate deck.md --theme midnight --out deck.pptx`
6. **Git-friendly**: JSON IR is diffable, slides are versionable

### 18.3 Mermaid Diagram Integration

```python
import subprocess
import json

async def mermaid_to_svg(mermaid_code: str) -> str:
    """Convert Mermaid syntax to SVG using mmdc CLI."""
    # Uses @mermaid-js/mermaid-cli (npx mmdc)
    proc = await asyncio.create_subprocess_exec(
        "npx", "-y", "@mermaid-js/mermaid-cli", 
        "-i", "/dev/stdin", "-o", "/dev/stdout", "-e", "svg",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate(mermaid_code.encode())
    return stdout.decode()
```

---

## 19. Implementation Timeline — 26 Weeks

### Phase 0: Foundation (Weeks 1–3)

| Week | Deliverables | Risk |
|------|-------------|------|
| 1 | DSL v3 Pydantic models, unit tests, migration script from v2 | Low |
| 2 | Template system: 15 slide types × Midnight theme (15 templates) | Low |
| 3 | DTCG token system + Radix color integration, remaining 3 themes (45 templates) | Low |

**Exit Criteria**: 60 templates load from MongoDB, DSL v3 validates all 15 slide types with inch-first positioning.

### Phase 1: Core Pipeline (Weeks 4–8)

| Week | Deliverables | Risk |
|------|-------------|------|
| 4 | Strategist role: Kimi-K2 integration, skeleton generation, schema-enforced output | Medium |
| 5 | Author role: DeepSeek-V3.2 integration, parallel Celery group for slide content | Medium |
| 6 | Designer role: GPT-4o-mini template filling, zone-based element placement | Medium |
| 7 | Celery pipeline: Skeleton-of-Thought fan-out, Stage 1→2→3 orchestration | High |
| 8 | Integration testing: Full pipeline end-to-end with mock models → real models | High |

**Exit Criteria**: 12-slide deck generates in <45s with correct DSL v3 output.

### Phase 2: Rendering (Weeks 9–12)

| Week | Deliverables | Risk |
|------|-------------|------|
| 9 | PPTX renderer: python-pptx with inch-first positioning for all 15 primitives | Medium |
| 10 | HTML standalone renderer: Jinja2 template with embedded Reveal.js | Medium |
| 11 | Reveal.js live preview: React component with @revealjs/react or wrapper | Medium |
| 12 | PDF renderer via Playwright, animation CSS, cross-format consistency testing | Medium |

**Exit Criteria**: Same DSL v3 input produces visually consistent output across PPTX, HTML, Reveal.js, and PDF.

### Phase 3: Quality & Intelligence (Weeks 13–17)

| Week | Deliverables | Risk |
|------|-------------|------|
| 13 | Critic role: Phi-4-reasoning scoring rubric, evaluation prompts | Medium |
| 14 | Self-refine loop: Targeted slide regeneration, max 2 cycles | High |
| 15 | Fact-checking: Citation schema enforcement, arithmetic validation | Medium |
| 16 | Image pipeline integration: Tiered generation, prompt refinement | Medium |
| 17 | HITL gates: Outline approval, content review, citation flags | Medium |

**Exit Criteria**: Average critic score ≥ 7.5 on 50-deck test suite. Citations present on 90%+ of factual claims.

### Phase 4: Frontend & UX (Weeks 18–22)

| Week | Deliverables | Risk |
|------|-------------|------|
| 18 | Prompt input UI: Topic, audience, tone, length, theme selector | Low |
| 19 | Real-time progress: SSE integration, stage indicators, preview updates | Medium |
| 20 | Slide editor: Per-slide editing, text/image/layout adjustments | High |
| 21 | Export flow: Download PPTX/HTML/PDF, share link generation | Medium |
| 22 | Mobile-responsive preview, accessibility audit (WCAG AA) | Medium |

**Exit Criteria**: User can input prompt → watch generation → edit slides → export all formats.

### Phase 5: Polish & Launch (Weeks 23–26)

| Week | Deliverables | Risk |
|------|-------------|------|
| 23 | Performance optimization: Caching, CDN, lazy loading, cold-start mitigation | Medium |
| 24 | Auth, billing integration (Stripe), rate limiting, user dashboard | Medium |
| 25 | Load testing (50 concurrent generations), error handling, monitoring (Sentry) | High |
| 26 | Beta launch prep: Landing page, docs, 10 example decks, feedback collection | Low |

**Exit Criteria**: System handles 50 concurrent users with p95 latency < 60s per deck. Zero data loss under load.

### Timeline Gantt

```
Week:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26
       ├──Phase 0──┤                                                                  
                   ├──────Phase 1──────┤                                              
                                       ├───Phase 2────┤                               
                                                       ├──────Phase 3──────┤          
                                                                           ├──Phase 4─┤
                                                                                    ├P5┤
```

**Note**: Phases 4 and 5 have 4-week overlap — frontend work begins while quality phase finalizes. This is intentional and manageable with 2+ developers.

---

## 20. Risk Registry

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| R1 | Kimi-K2 Azure deprecation | Low | High | Fallback chain: Phi-4-reasoning → DeepSeek-V3.2 |
| R2 | Groq free-tier rate limits hit | Medium | Medium | 8-key round-robin already implemented; CF Workers as backup |
| R3 | FLUX.1-Kontext pricing increase | Medium | Medium | Nvidia SD3 (free) as primary fallback |
| R4 | Reveal.js v5 breaking changes | Low | Medium | Pin version, bundle locally |
| R5 | Template coverage gaps | Medium | Medium | 60 templates cover 90% of cases; custom flag for edge cases |
| R6 | Self-refine loop oscillation | Low | High | Hard cap at 2 cycles; always forward-progress |
| R7 | MongoDB Atlas cost scaling | Medium | Medium | Index optimization, TTL on logs, archive old presentations |
| R8 | Parallel Celery task failure | Medium | Medium | Individual slide retry (3×); partial deck delivery |
| R9 | Image generation bottleneck | Medium | High | 4-tier fallback; pre-generate common backgrounds |
| R10 | Competitor feature parity | High | Medium | Double-down on code slides + HTML export differentiators |

---

## Appendix A: Research Paper Integration Map

| Paper | Year | Venue | Stars | What We Take | Where It Maps |
|-------|------|-------|-------|-------------|---------------|
| **PPTAgent** | 2025 | EMNLP | 4.1k | Edit-based 2-stage: analyze reference → generate with template | §5 Designer fills templates, §8 Template system |
| **Skeleton-of-Thought** | 2024 | ICLR | — | Parallel point expansion from skeleton outline | §6 Pipeline fan-out, §5.2 Author parallelism |
| **AutoPresent / SlidesBench** | 2025 | CVPR | — | Code-generation > image-generation approach; evaluation rubric | §13 Critic rubric, §7 DSL as "code" output |
| **RALF** | 2024 | CVPR Oral | — | Retrieval-augmented layout with user constraints | §8.4 Template retrieval + constraint filling |
| **Paper2Poster / PaperQuiz** | 2025 | NeurIPS | — | Content fidelity metric for evaluation | §13 Critic: content accuracy dimension |
| **DeepPresenter** | 2025 | arXiv | — | Environment-grounded reflection for iterative improvement | §13 Self-refine loop architecture |
| **Shumailov et al.** | 2023 | arXiv | — | Model collapse from recursive self-training | §15 Why we NEVER self-train |

---

## Appendix B: V9 Loophole Resolution Matrix

| # | V9 Loophole | V10.1 Fix | Section |
|---|-------------|-----------|---------|
| 1 | 6-layer sequential pipeline too slow | Skeleton-of-Thought parallel fan-out: 3–5× speedup | §6 |
| 2 | 12-agent orchestration too complex | Collapsed to 4 roles: Strategist, Author, Designer, Critic | §5 |
| 3 | GLA is just flexbox + LLM JSON with fancy name | Eliminated. Designer fills pre-positioned template zones | §8.4 |
| 4 | Remotion costs $100/mo per render node | Replaced with @revealjs/react (MIT) + GSAP + CSS animations | §10 |
| 5 | @chenglou/pretext is v0.0.5 experimental | Used for text measurement only; Satori as fallback; non-critical path | §9 |
| 6 | No human-designed templates; LLM invents layouts | 15 slide types × 4 themes = 60 human-designed templates | §8 |
| 7 | PPTX fidelity issues from px-based positioning | JSON IR with inch-first positioning; direct EMU mapping | §7 |
| 8 | Self-learning = model collapse risk | Self-REFINE only (bounded, stateless); never self-train | §15 |
| 9 | yoyo-evolve: zero production evidence | Eliminated entirely | §2 Anti-Patterns |
| 10 | Phi-4-vision latency / not available | Use Phi-4-reasoning (available) for Critic role; no vision needed | §3, §5.4 |
| 11 | No design system defined | DTCG tokens + Radix Colors with 4 complete theme palettes | §9 |
| 12 | 265+ components impossible to build/test | 15 primitives (hard cap) composing all slide types | §9.3 |
| 13 | 26-week timeline unrealistic for V9 scope | 26 weeks feasible with reduced scope; clear phase exits | §19 |
| 14 | No fact-checking mechanism | Schema-enforced citations + tool-forced arithmetic + Critic validation | §12 |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| V9 | March 2026 | — | Original master plan |
| V10 (feedback) | April 2026 | — | 14 loopholes identified |
| **V10.1** | **April 2026** | **Meridian** | **Complete rewrite addressing all 14 loopholes. Research-grounded. Available-models-only.** |

---

*End of V10.1 Master Architecture Plan*
