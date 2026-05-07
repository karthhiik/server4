# PREMIUM_SLIDE_V10_2_MASTER_PLAN.md

*The definitive architectural reference for a solo-developer AI presentation generation SaaS*
*Version 10.2 — April 2026*

---

## Part I — Executive summary

V10.2 is the first version of this plan that is **actually buildable by a solo developer in 24–28 weeks** without hallucinated dependencies, without frontier-model access that was never confirmed, and without the licensing landmines that V9 and V10 quietly stepped on. The plan retires every speculative branding element ("Generative Layout Algebra," "Self-Evolving Code Agent," "12-agent orchestration") and replaces them with named, verifiable patterns drawn from published papers and production engineering blogs. It commits to a **bounded-canvas Figma-grade editor** (one fixed 1920×1080 frame per slide, full element-level manipulation inside that frame) rather than an infinite-canvas whiteboard, a **hybrid JSON intermediate representation** that lets a slide live in either "template-bound" or "free-primitive" mode with a reversible migration between them, a **Skeleton-of-Thought + PPTAgent-inspired 3–4 agent generation pipeline**, and a **quality-first model stack routed across Azure Foundry, DeepSeek direct, Mistral, Groq, and Cloudflare Workers AI** that explicitly excludes Anthropic Claude, Google Gemini, and frontier OpenAI models.

**What changed from V9/V10/V10.1.** V9 promised an "infinite generative canvas" powered by "layout algebra" that was in practice a LLM-to-Yoga bridge with no unique primitives. V10 doubled the agent count to twelve and added a "self-evolving code agent" that had no evaluation harness. V10.1 kept the twelve-agent structure but admitted the template library did not exist. V10.2 collapses the agent count to four by adopting the empirically validated PPTAgent Planner→Retriever→Writer→Critic pattern (arXiv 2501.03936), replaces the fictional template library with a concrete "15 primitives × 4 themes = 60 rendered layouts" scheme grounded in DTCG v2025.10 tokens, and constrains the custom sandbox to a Konva-based bounded canvas rather than a bespoke vector engine. The model stack is rebuilt from scratch around the specific providers the developer actually has access to, with DeepSeek V3.2's confirmed 90% prompt-cache discount ($0.028/M cached input versus $0.28/M miss) as the core cost lever.

**The five defining bets.** First, **PPTX fidelity as a promise**: a CI harness of LibreOffice + ssim.js holds template exports to mean-SSIM ≥ 0.95 and freeform exports to ≥ 0.88, making "your deck round-trips cleanly into PowerPoint" a defensible enterprise wedge that Chronicle (still rolling out PPT export through 2026), Gamma (criticized for export quality), and Prezi (no PPTX at all) cannot match on the same timeline. Second, **a custom Figma-grade bounded-canvas editor** built on Konva + react-konva + Tiptap, which avoids both tldraw's $6,000/yr SDK fee and Polotno's $199–$399/mo commercial license while giving the product a genuine editor moat. Third, **template-to-free-primitive migration**, a novel UX primitive where the AI-generated slide begins as a slot-filled template for quality and safety, then "ejects" to free absolute-positioned primitives on user demand, with user edits preserved across regeneration via RFC 6902 JSON-Patch. Fourth, **real-time streaming generation** using Skeleton-of-Thought parallel decoding across Groq's 275+ tok/s Llama-3.3-70B and DeepSeek V3.2's cache-discounted fan-out, putting the first slide on screen in under two seconds and a full deck in five to ten. Fifth, **standalone HTML export**, a single self-contained file with inlined GSAP animations (now fully free for commercial use as of April 30, 2025) that ensures decks outlive the SaaS — a trust signal that every lock-in-forward competitor deliberately refuses to ship.

---

## Part II — Fixed loopholes from V9/V10/V10.1

**Loophole 1 — "Generative Layout Algebra" was Yoga plus an LLM.** The V9 branding implied a novel algebraic system; in practice it was a flexbox solver wrapped around a prompt. V10.2 drops the name entirely and replaces it with **Retrieval-Augmented Layout** modelled on RALF (CVPR 2024 Oral, arXiv 2311.13602, github.com/CyberAgentAILab/RALF). Each of the 60 rendered layouts (15 primitives × 4 themes) is embedded along two axes — a DreamSim visual embedding of its rendered PNG and an `text-embedding-3-small` semantic embedding of its role plus slot descriptions — and stored in an HNSW index. Given an outline entry, the pipeline retrieves the top-k layouts and feeds the winner's slot schema into the writer agent as a structural constraint. RALF demonstrated this is the single biggest quality lever for content-aware layout.

**Loophole 2 — The 12-agent orchestration was over-engineered.** V10.2 collapses to four agents matching PPTAgent's two-stage architecture (EMNLP 2025, ~3,300 stars, MIT): a **Planner** (outline generation, one serial call on Kimi-K2-Thinking for complex reasoning or DeepSeek V3.2 for cheaper runs), a **Layout Retriever** (millisecond-latency HNSW search, no LLM cost), N parallel **Writers** (one per slide on DeepSeek V3.2, fan-out pattern from Skeleton-of-Thought arXiv 2307.15337), and a single **Critic** (deterministic DOM checks first, optional Phi-4-Multimodal or Qwen2.5-VL-7B second pass). This matches the empirically successful architectures of PPTAgent v2 "DeepPresenter," Paper2Poster (NeurIPS 2025), and SlideGen (arXiv 2512.04529).

**Loophole 3 — @chenglou/pretext 0.0.5 was a single-author pre-1.0 dependency.** V10.2 uses it opportunistically for pretext-specific flows but falls back to **Satori** (Vercel, MIT, mature) for React-to-SVG rendering when pretext fails, and uses browser `ctx.measureText` as the last resort. Treat pretext as non-critical: all font layout logic must work without it.

**Loophole 4 — The template library did not exist.** V10.2 replaces "curated human-designed templates" with a deterministic generator: **15 slide primitives** (title, section divider, bullet list, two-column, quote, image+text, stats, timeline, comparison table, bar chart, line chart, process flow, team grid, Q&A, agenda) rendered against **4 themes** (Modern Minimal, Editorial Serif, Technical Dark, Corporate Navy) for a **60-layout starting corpus** that can be expanded programmatically. Themes are encoded as DTCG v2025.10 token JSON consumed by Style Dictionary v4.

**Loophole 5 — The PPTX fidelity target was never measured.** V10.2 commits to concrete mean-SSIM thresholds: **≥0.95 for template-bound slides, ≥0.88 for freeform slides** (the 0.88 figure is defensible against production practice per jest-image-snapshot defaults and Percy visual regression). The CI harness is `soffice --headless --convert-to pdf` + `pdftoppm -r 200` + `ssim.js` (the verified npm package, obartra/ssim) with `pixelmatch` for diff visualization on failure.

**Loophole 6 — "yoyo-evolve" Self-Evolving Code Agent is removed.** There was no evaluation harness, no published ablation, no reproducible benchmark. A solo developer cannot simultaneously ship a production editor and maintain a code-evolving agent loop. This is dropped outright.

**Loophole 7 — SLGS (self-learning generation stack) risked model collapse.** V10.2 uses retrieval augmentation only — layout retrieval from a stable curated corpus — never recursive training on the model's own outputs. The distinction is critical: retrieval from human-authored exemplars grounds the generator, whereas recursive training on generated outputs is the documented Shumailov et al. 2024 *Nature* model-collapse regime.

**Loophole 8 — The timeline was fantasy.** V10 claimed 16 weeks. V10.2 commits to **24–28 weeks** with explicit gates and deferred features (see Part IX). This matches realistic solo-dev velocity for editor-class products, consistent with Figma's own admission that building a web design tool took years, not months.

**Loophole 9 — No fact-checking layer.** V10.2 enforces citations via Zod schema (every `stat` or `claim` field carries a `source: { title, url }` object) and routes all arithmetic through a tool-call (`computeMetric({numerator, denominator, format})`) so the LLM never hallucinates percentages. Schema-forced citations, not post-hoc verification, are the defensible anti-hallucination pattern in 2026.

**Loophole 10 — Design system was hand-waving.** V10.2 uses Radix Colors (OKLCH 12-step, published by the Radix UI team under MIT, used by Vercel and Linear) as the color foundation, converted to DTCG v2025.10 tokens (the first stable version, released October 28, 2025) by Style Dictionary v4. Color math goes through **culori** (Evercoder/culori, MIT, comprehensive CSS Color L4 coverage) for theme generation and **@texel/color** (MIT, ~60× faster than culori) for hot render paths.

**Loophole 11 — "Real-time generation" was vague.** V10.2 specifies Skeleton-of-Thought fan-out (1 skeleton call + N parallel writer calls, empirically 1.9–2.4× faster than serial per Ning et al. ICLR 2024) delivered over Server-Sent Events using `best-effort-json-parser` (BSD-2, 80k+ weekly downloads) or `partial-json` (MIT, promplate) for incremental rendering. Target first-slide latency is under two seconds; full deck five to ten seconds.

**Loophole 12 — Remotion licensing risk.** Remotion is dual-licensed; as of 2026 the Company License is required for for-profit organizations above 3 employees, with minimums around $100/mo and telemetry mandatory since v5. V10.2 does not depend on Remotion. Animations inside slides use **GSAP** (Webflow acquisition April 2025 made GSAP including all former Club plugins free for commercial use, confirmed at gsap.com/community/standard-license) and **Motion** (Framer Motion v12, MIT, imported from `motion/react`). Video export, if needed later, uses FFmpeg + Puppeteer rather than Remotion.

**Loophole 13 — Sandbox architecture was undefined.** V10.2 specifies: an iframe on a distinct subdomain (`sandbox.app-domain`), loaded with `sandbox="allow-scripts"` *without* `allow-same-origin` (the only configuration where the child cannot strip its own sandbox attribute, verified per MDN and HackTricks), a strict CSP (`default-src 'self'; script-src 'self' 'wasm-unsafe-eval' https://esm.sh`), esbuild-wasm transpilation in a Web Worker inside the iframe, and a typed `postMessage` protocol with origin validation on both ends. This mirrors Sandpack's architecture (Apache 2.0) without depending on its commercial-restricted Nodebox runtime or on StackBlitz WebContainer (commercial license required above 500 sessions/month).

---

## Part III — The V10.2 architecture

### System overview

```
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js on Vercel Pro or Cloudflare Pages)            │
│  ┌──────────────┐   ┌────────────────────────┐   ┌────────────┐  │
│  │ Thumbnail    │   │  Konva Stage 1920×1080 │   │ Inspector  │  │
│  │ Rail         │   │   ├─ background layer  │   │ panel      │  │
│  │ (tanstack/   │   │   ├─ main edit layer   │   │ (property  │  │
│  │  virtual,    │   │   ├─ drag layer        │   │  forms)    │  │
│  │  @dnd-kit    │   │   └─ guides layer      │   │            │  │
│  │  reorder)    │   │  DOM overlay for       │   │            │  │
│  │              │   │  Tiptap text editor    │   │            │  │
│  └──────────────┘   └────────────────────────┘   └────────────┘  │
│  State: Zustand + immer + command-pattern history                 │
│  Doc: Hybrid JSON IR (template | free | hybrid) in EMU            │
│  Auth: JWT from external auth server, validated server-side       │
└──────────────────┬───────────────────────────────────────────────┘
                   │ SSE (outline, slide.patch, critic.patch)
                   │ REST  (save, export, list)
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  BACKEND (Next.js API routes / Cloudflare Workers)                │
│  ┌──────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Planner  │→ │ Retriever   │→ │ Writers  │→ │ Critic       │   │
│  │ (Kimi or │  │ (HNSW over  │  │ (N par., │  │ (DOM rules + │   │
│  │ DeepSeek)│  │ 60 layouts) │  │ DeepSeek)│  │ optional VLM)│   │
│  └──────────┘  └─────────────┘  └──────────┘  └──────────────┘   │
│  Structured output: Vercel AI SDK streamObject + Zod              │
│  Image gen: FLUX Schnell (CF) default, FLUX Kontext (Azure) hero  │
│  Stock photos: Unsplash → Pexels → Pixabay fallback               │
└──────────────────┬───────────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  STORAGE                                                          │
│  Postgres + pgvector (Supabase Pro or Neon Scale)                 │
│  R2 for assets (images, generated PNGs, exported PPTX)            │
│  Redis (Upstash) for sessions, rate limits, SSE reconnect tokens  │
│  Inngest or BullMQ-self-hosted for background jobs                │
└──────────────────┬───────────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  RENDERING TARGETS                                                │
│  Edit mode:    Konva canvas (interactive Transformer)             │
│  Preview mode: @revealjs/react v6 Deck with PNG per slide         │
│  Present mode: Full @revealjs/react v6 with keyboard + overview   │
│  Export:       PptxGenJS (PPTX), react-pdf (PDF), HTML (inline)   │
└──────────────────────────────────────────────────────────────────┘
```

### The hybrid JSON IR

All coordinates live in **EMU** (English Metric Units: 914,400 per inch, 9,525 per pixel at 96 DPI). This is the same unit PPTX uses internally, so export is a lossless integer translation rather than a DPI-dependent conversion. The default 16:9 slide is 12,192,000 × 6,858,000 EMU (PowerPoint widescreen). Conversion to CSS pixels happens only at render time via a `scale = pxWidth / emuWidth` factor.

The IR models a slide as a discriminated union with three modes. In **template mode**, the slide references a `templateId` and fills named `slots` with structured content; positions are derived from the template definition. In **free mode**, each element carries its own absolute `frame` in EMU plus a z-index; the AI does not modify free elements unless explicitly asked. In **hybrid mode**, some elements are slot-bound and others are free, so the AI can rewrite the title while the user-added annotation arrow persists. Every element carries a stable UUID and optional `userEditedProps` map (property path → timestamp) so RFC 6902 patches can target properties rather than array indices.

```typescript
// Branded EMU type prevents accidental px/EMU mixing at compile time
type EMU = number & { readonly __brand: 'EMU' };
const inToEMU = (v: number) => Math.round(v * 914400) as EMU;
const pxToEMU = (v: number) => Math.round(v * 9525) as EMU;

type ElementId = string; // UUID v4
type SlideId = string;
type DeckId = string;

// DTCG-style token reference; resolved at render time against active theme
type TokenRef = `{${string}}`;
type ColorValue = TokenRef | `#${string}` | `oklch(${string})`;

interface BoundingBoxEMU { x: EMU; y: EMU; w: EMU; h: EMU; rotation?: number }

type ElementKind = 'text' | 'image' | 'shape' | 'line' | 'chart' | 'table' | 'group' | 'code';

interface SlotBinding {
  positionSource: 'template';
  slotId: string;
  role: 'title' | 'subtitle' | 'body' | 'bullets' | 'hero' | 'kpi' | string;
}

interface FreeBinding {
  positionSource: 'free';
  box: BoundingBoxEMU;
  zIndex: number;
}

type Binding = SlotBinding | FreeBinding;

interface BaseElement {
  id: ElementId;
  kind: ElementKind;
  binding: Binding;
  locked?: boolean;                         // user-edit protection flag
  detachedAt?: number;                      // timestamp of template-detach
  originTemplateId?: string;                // traceability after detach
  userEditedProps?: Record<string, number>; // propPath -> edit timestamp
}

interface TextRun {
  text: string;
  font?: { family?: TokenRef; sizePt?: number; weight?: number; italic?: boolean };
  color?: ColorValue;
  href?: string;
}

interface Paragraph {
  runs: TextRun[];
  level?: 0 | 1 | 2 | 3 | 4 | 5;
  align?: 'left' | 'center' | 'right' | 'justify';
  bullet?: { style: 'disc' | 'number' | 'none'; char?: string };
}

interface TextElement extends BaseElement {
  kind: 'text';
  paragraphs: Paragraph[];
  vAlign?: 'top' | 'middle' | 'bottom';
  autoFit?: 'none' | 'shrink' | 'resize';
}

interface ImageElement extends BaseElement {
  kind: 'image';
  assetId: string;
  fit: 'cover' | 'contain' | 'fill';
  alt?: string;
  crop?: BoundingBoxEMU;
}

interface ShapeElement extends BaseElement {
  kind: 'shape';
  preset: 'rect' | 'roundRect' | 'ellipse' | 'triangle' | 'arrow' | string;
  fill?: { color: ColorValue; opacity?: number };
  stroke?: { color: ColorValue; widthPt: number; dash?: 'solid' | 'dash' | 'dot' };
  cornerRadius?: EMU;
}

interface ChartSpec {
  type: 'bar' | 'line' | 'pie' | 'doughnut' | 'scatter' | 'area';
  data: Array<{ label: string; values: number[] }>;
  source?: { title: string; url: string }; // schema-forced citation
}

interface ChartElement extends BaseElement {
  kind: 'chart';
  spec: ChartSpec;
}

interface TableElement extends BaseElement {
  kind: 'table';
  rows: Paragraph[][];
  colWidths: EMU[];
}

interface GroupElement extends BaseElement {
  kind: 'group';
  children: SlideElement[];
}

type SlideElement =
  | TextElement | ImageElement | ShapeElement
  | ChartElement | TableElement | GroupElement;

type SlotValue =
  | { kind: 'text'; paragraphs: Paragraph[] }
  | { kind: 'image'; assetId: string; alt?: string }
  | { kind: 'list'; items: Paragraph[] }
  | { kind: 'table'; rows: Paragraph[][] }
  | { kind: 'chart'; spec: ChartSpec };

interface TemplateSlot {
  id: string;
  role: string;
  allowedKinds: ElementKind[];
  box: BoundingBoxEMU;
  defaultStyle?: Partial<TextRun>;
  maxChildren?: number;
}

interface SlideTemplate {
  id: string;
  name: string;
  primitive: 'title' | 'bullets' | 'two-column' | /* ... 15 total */ string;
  themeId: string;
  canvasSize: { w: EMU; h: EMU };
  slots: TemplateSlot[];
  background?: { color: ColorValue } | { assetId: string };
}

interface SlideCommon {
  id: SlideId;
  order: number;
  notes?: string;
  background?: { color: ColorValue } | { assetId: string };
}

interface TemplateBoundSlide extends SlideCommon {
  mode: 'template';
  templateId: string;
  slots: Record<string, SlotValue>;
}

interface FreePrimitiveSlide extends SlideCommon {
  mode: 'free';
  templateId: string;           // retained for canvas size + theme only
  elements: SlideElement[];
}

interface HybridSlide extends SlideCommon {
  mode: 'hybrid';
  templateId: string;
  slots: Record<string, SlotValue>;
  freeElements: SlideElement[]; // user-added, AI never touches
}

type Slide = TemplateBoundSlide | FreePrimitiveSlide | HybridSlide;

interface Deck {
  id: DeckId;
  schemaVersion: '10.2';
  version: number;              // monotonic, bumped on save
  canvasEMU: { w: EMU; h: EMU };
  theme: ThemeId;
  slides: Slide[];
  templates: SlideTemplate[];
  assets: Array<{ id: string; url: string; kind: 'image' | 'icon' }>;
  meta: { title?: string; createdAt: string; model?: string };
}
```

### The custom sandbox: bounded-canvas editor

The editor renders a single active slide as a `Konva.Stage` sized to the slide's EMU × scale factor, subdivided into four layers. The **background layer** holds theme background fills with `listening: false` for hit-test performance. The **main edit layer** holds all slide elements; each element is a `Konva.Group` wrapping its primitive node so rotation and scale are composable. The **drag layer** is transient: on `dragstart` the dragged node is moved to this layer, which means other shapes do not need to redraw during drag; on `dragend` it is moved back. The **guides layer** is `listening: false` and draws alignment guides during drag operations.

Selection and transform use `Konva.Transformer` natively; for multi-select, a `Konva.Transformer` accepts an array of `nodes()` and produces a single bounding box with shared handles. Marquee selection is implemented via a `mousedown` on empty stage space that tracks a `Konva.Rect`, then on `mouseup` iterates all shape `getClientRect()` values and checks intersection with `Konva.Util.haveIntersection`. **Alignment guides** follow the pattern documented in Konva's Objects_Snapping example: on every `dragmove`, compute stop positions (each other shape contributes 3 vertical stops — left, center, right — and 3 horizontal stops — top, middle, bottom — plus the stage's own edges and centerlines), find the minimum-distance candidate per axis within a threshold (typically 5 stage-pixels), apply an offset to the drag position, and draw a dashed guide as a `Konva.Line` on the guides layer. **Snap-to-grid** is a simple `Math.round(x / gridSize) * gridSize` applied in `dragmove` when grid mode is active.

**Inline text editing** uses the canonical swap-to-DOM pattern. The base state renders a `Konva.Text` node. On `dblclick`, the Konva node is hidden and its Transformer removed; a `<div>` hosting a Tiptap editor is mounted absolutely at the node's screen position (computed from `textNode.absolutePosition()` plus `stage.container().getBoundingClientRect()`), matching font, color, line-height, and rotation via CSS transforms. On blur or Enter-out, `editor.getJSON()` is serialized back into the IR's `Paragraph[]` structure and the Konva node is restored. This pattern keeps Konva's export simplicity (exporting `stage.toDataURL()` gives a canonical PNG) while allowing rich text editing through Tiptap's battle-tested ProseMirror core.

**Undo/redo** uses a hybrid command pattern with immer producers. Every user action is wrapped as a `Command { label, timestamp, redo(state) => state, undo(state) => state }`. Two stacks `undoStack` and `redoStack` are bounded at 200 entries. High-frequency gestures (drag, continuous resize) are **coalesced**: a drag transaction starts on `dragstart` capturing `before`, commits a single command on `dragend` with the final `after`. A `coalesceWith(prev)` hook lets sequential same-kind commands merge within a 500ms window, which keeps the undo stack clean under rapid editing.

**Keyboard shortcuts** use a single document-level listener scoped by `document.activeElement`. When a Tiptap editor has focus, canvas shortcuts are suppressed. The core set is: arrows to nudge (1 EMU-px, Shift+arrow = 10), Delete/Backspace to remove, Ctrl/⌘+C/V/X/D for clipboard + duplicate, Ctrl+A for select-all, Ctrl+G/Shift+Ctrl+G for group/ungroup, `[` and `]` for z-order up/down, Ctrl+`[`/`]` for to-back/to-front, Tab to cycle selection, Escape to deselect.

**Performance** targets are 60fps with 100 elements per slide. Key tactics from Konva's performance documentation: layer separation (background + main + drag + guides), `perfectDrawEnabled: false` on decorative shapes, `shadowForStrokeEnabled: false`, `listening: false` on non-interactive layers, and `node.cache()` on groups of complex shapes. At most ±2 slides around the active slide are mounted as stages; other slides are represented by cached PNG thumbnails in IndexedDB keyed by a JSON hash of slide content. Thumbnails are regenerated with debounced 500ms after any mutation.

**Virtual scrolling** for the thumbnail rail uses `@tanstack/react-virtual` (v3.13+, MIT, ~11M weekly downloads). `@dnd-kit/sortable` handles thumbnail reorder; `dnd-kit` is explicitly *not* used for on-canvas shape dragging since Konva's native drag handling is purpose-built for that case.

### The real-time generation pipeline

The pipeline is a four-stage Skeleton-of-Thought variant. **Stage 1 (Planner, serial)** sends the user brief plus any uploaded source documents to Kimi-K2-Thinking (for complex narrative reasoning) or DeepSeek V3.2 (for simpler cost-sensitive runs) with a schema-forced outline prompt. The outline is streamed via `streamObject` (Vercel AI SDK + Zod) emitting `{ slides: [{ role, objective, bulletHints, suggestedPrimitive }] }`. The UI shows slide placeholders as soon as each outline entry validates, typically 1–2 seconds for a 10-slide deck.

**Stage 2 (Retriever, serial, no LLM)** embeds each outline entry's role plus objective via `text-embedding-3-small`, queries the HNSW template index over the 60-layout corpus, and returns top-k candidates. At millisecond latency this is free compared to the model calls.

**Stage 3 (Writers, N parallel)** issues N simultaneous DeepSeek V3.2 calls (one per slide), each receiving the outline entry plus the retrieved template's slot schema plus the active theme's DTCG tokens. Because the system prompt is identical across the N calls and DeepSeek's automatic prefix caching gives a 90% discount on cache hits ($0.028/M cached input versus $0.28/M miss), the marginal cost of the N–1 parallel calls is near-zero after the first. Each writer streams its slot-filled `TemplateBoundSlide` JSON via `streamObject`; the client applies patches to IR state as they arrive. Parallelism is capped at 6 concurrent calls via `p-limit` to stay within provider rate limits, with burst into Groq Llama-3.3-70B as fallback when DeepSeek rate limits hit.

**Stage 4 (Critic, async, runs after initial render)** renders each completed slide to PNG via headless Chromium, then applies a three-layer cascade. **Layer 1** is deterministic DOM checks: bounding-box overlap detection (IoU > 0.02 triggers a fix), WCAG contrast ratio (< 4.5:1 body text or < 3:1 large text fails), overflow detection (`scrollSize > clientSize` on any container), whitespace percentage (outside 25–55% triggers a warning), font-size sanity (< 14px or > 72pt), and character density (> 350 characters per slide). These catch roughly 80% of real failures at zero LLM cost. **Layer 2** is rule-based heuristics: title present and under 80 characters, bullet count ≤ 6, image aspect within ±10% of slot, colors all resolving to theme tokens. **Layer 3**, invoked only for slides that pass Layers 1 and 2 but still look wrong (or 1-in-10 sampled for QA), sends the slide PNG plus a rubric prompt to Qwen2.5-VL-7B on Hyperbolic or DeepInfra ($0.0005 per slide when triggered) or to self-hosted Phi-4-Multimodal on a shared A100 if the volume justifies it. The critic emits RFC 6902 patches rather than full rewrites, so fixes land incrementally over additional SSE events.

### The template → free-primitive migration

A user confirms an AI-generated template-bound slide and then wants to reposition elements. The migration converts the slide from template mode to free mode in-place without data loss.

```typescript
function ejectSlide(slide: TemplateBoundSlide, tpl: SlideTemplate): FreePrimitiveSlide {
  const elements: SlideElement[] = [];
  let z = 0;
  for (const slot of tpl.slots) {
    const value = slide.slots[slot.id];
    if (!value) continue;
    const elementsFromSlot = renderSlotToElements(slot, value, z++);
    elements.push(...elementsFromSlot);
  }
  return {
    id: slide.id,
    order: slide.order,
    notes: slide.notes,
    background: slide.background,
    mode: 'free',
    templateId: tpl.id,
    elements,
  };
}
```

The inverse `reattachElement(el, tpl, targetSlotId?)` is best-effort: if the element's geometry falls within a slot's box tolerance and its kind matches `slot.allowedKinds`, it reattaches; otherwise it stays free. Unlike Figma's fully one-way instance detach, this per-element reversibility is feasible because each slot has a canonical box and a typed allowed-kind list.

**Edit preservation across regeneration** is the critical invariant. When the user requests "regenerate slide 3" after making local edits, the system computes the user's patch `userEdits = compare(originalAiDoc, currentUserDoc)` via `fast-json-patch` (Starcounter-Jack/JSON-Patch, MIT, ~5M weekly npm downloads), issues the regeneration to get `newAiDoc`, then runs a three-way merge. Paths the AI touched but the user did not are accepted from the AI. Paths the user touched get user-wins resolution. Paths that became invalid (the AI removed an element the user had edited) are surfaced to a conflict-resolution UI ("keep your edit / accept AI / diff"). This is only tractable because every element has a stable UUID: the patch paths are `/slides/{id:abc}/elements/{id:xyz}/text` rather than positional `/slides/0/elements/3/text`, so reordering the array doesn't break preserved edits.

### The hybrid rendering system

The edit mode is pure Konva as described above. The **preview mode** embeds a `@revealjs/react` v6 Deck (verified v6.0 released with official React wrapper, switch from gulp to Vite, ESM paths renamed to `.mjs`) with one `<Slide>` per document slide, each rendering a pre-computed PNG via `stage.toDataURL({ pixelRatio: 1 })`. The **present mode** uses the same reveal.js deck with `controls: true`, full-screen, keyboard navigation, and the reveal.js notes plugin for speaker view. The **export mode** converts the IR to PptxGenJS calls (see Part VIII). Switching between modes is a route change — the edit tree and the reveal tree never coexist — which avoids keyboard conflicts and CSS interference.

---

## Part IV — The model stack routing

Every task in the pipeline is assigned to a primary model and a fallback. The assignments are derived from each model's strengths: Kimi-K2-Thinking's 256K context and deep reasoning for long-horizon planning; DeepSeek V3.2's 90% prompt-cache discount for fan-out; Azure GPT-4o-mini's strict `response_format: json_schema` for schema-critical validation; Groq's 275–300+ tok/s for UX-sensitive drafts; Cloudflare Workers AI's cheap long context (GLM-4.7-Flash at $0.06/M input) for document summarization; Qwen-2.5-Coder-32B on Cloudflare for HTML/JSX generation.

| Task | Primary | Fallback | Rationale |
|---|---|---|---|
| Deck outline (planner, serial) | Kimi-K2-Thinking (Azure) | DeepSeek V3.2 | Long-context reasoning; 256K window handles source PDFs |
| Per-slide writer (fan-out, parallel) | DeepSeek V3.2 (direct) | Groq Llama-3.3-70B | 90% cache discount makes N calls ≈ 1 call cost |
| Schema validation / JSON repair | Azure GPT-4o-mini | Mistral-medium-2505 | Best strict structured outputs in the stack |
| Code slide HTML/JSX | Qwen-2.5-Coder-32B (CF) | GPT-4o-mini | Code-specialized; cheap on Cloudflare |
| Chat / vibe-edit refinement | Groq Llama-3.3-70B | GLM-4.7-Flash (CF) | 275+ tok/s feels real-time |
| PDF / docx summarization | GLM-4.7-Flash (CF) | DeepSeek V3.2 | Cheapest long-context option |
| Deterministic layout check | Headless Chrome | — | Free, instant |
| Vision aesthetics critic | Qwen2.5-VL-7B (DeepInfra) | Pixtral 12B (Mistral) | Only invoked after deterministic fails |
| Hero image | FLUX.1 Kontext pro (Azure) | fal FLUX Kontext | Reference-image consistency |
| Bulk/support images | FLUX Schnell (Cloudflare) | Replicate | ~$0.0005/image on CF |
| Icons | Lucide / Phosphor SDK | — | No API needed |
| Stock photos | Pexels API | Unsplash, Pixabay | Free, no-approval rate limits |

### Prompt caching strategy

DeepSeek V3.2's caching is automatic on shared prefixes and gives a 90% discount on cache hits. The writer prompts are engineered so the first ~80% of tokens are a shared system prompt plus the retrieved template schema (identical across all N parallel calls), and only the last ~20% varies per slide. This converts an N-way fan-out from N×cost into 1×miss + (N-1)×hit_cost, which is approximately 1.1×cost for a 10-slide deck instead of 10×. Azure GPT-4o-mini's caching is also automatic above a 1024-token prefix with a 50% discount; structure system prompts to exceed this threshold.

### Budget optimizer pseudocode

```typescript
async function route(task: Task, payload: Payload): Promise<Response> {
  const budgetRemaining = await getUserMonthlyBudgetRemaining(userId);
  const candidates = ROUTING_TABLE[task.kind].filter(c =>
    c.estimatedCost(payload) <= budgetRemaining &&
    c.health.ok &&
    c.contextWindow >= payload.tokenEstimate
  );
  for (const candidate of candidates) {
    try {
      const response = await candidate.call(payload);
      recordSuccess(candidate, payload);
      return response;
    } catch (err) {
      if (isRateLimit(err) || isTransient(err)) continue;
      throw err;
    }
  }
  throw new Error('All candidates exhausted');
}
```

### Realistic monthly cost

A typical 10-slide deck consumes approximately 26K input tokens (of which ~16K are cached on the second and subsequent decks by the same user thanks to shared theme + schema prefixes), ~10K output tokens, one FLUX Kontext hero image, and two FLUX Schnell support images. Per-deck cost breaks down roughly as: planner ~$0.005, writers ~$0.0015 after cache, validator ~$0.0027, vision critic ~$0.0003 (20% of decks), hero image $0.04, support images $0.001. Total per deck: approximately **$0.050**, of which ~80% is image generation.

At **100 users** averaging 5 decks per month (500 decks), cost is approximately **$25/month** — effectively all image generation, since LLM traffic fits inside Groq's free tier and Cloudflare's 10,000 daily Neurons. At **1,000 users (5,000 decks)**, cost is approximately **$250/month**. At **10,000 users (50,000 decks)**, baseline cost is around **$2,500/month**, but aggressive optimization (default hero to FLUX Schnell, reserve FLUX Kontext for paid tiers only, exploit DeepSeek off-peak pricing 16:30–00:30 UTC, batch vision critic at 1-in-20 sampling) drops this to roughly **$400–800/month**. Infrastructure at 10K users adds another **$1,000–1,500/month** (Vercel Pro with bandwidth overage, Supabase Team, Upstash Production, R2 egress). Total at 10K users: **~$1,500–2,500/month** of costs — sustainable at a $10/mo average ARPU.

---

## Part V — The custom sandbox deep dive

The sandbox runs user-authored React/JSX code slides (e.g., "live data visualization" slides) in an isolated context without giving that code access to user sessions. The architecture is borrowed from Sandpack but self-hosted to avoid commercial license restrictions on Nodebox.

The parent app runs at `app.example.com`. The sandbox iframe is served from `sandbox.example.com` — a distinct origin, which means cookies and localStorage are already isolated by same-origin policy. The iframe carries `sandbox="allow-scripts"` *without* `allow-same-origin`; this is critical because the combination `sandbox="allow-scripts allow-same-origin"` for same-origin content allows the child to execute `top.document.querySelector('iframe').removeAttribute('sandbox')` and escape (documented on HackTricks). Additional protection comes from a strict Content Security Policy served with the iframe document: `default-src 'self'; script-src 'self' 'wasm-unsafe-eval' https://esm.sh; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' https://esm.sh`. If the sandbox needs `SharedArrayBuffer` (for heavier WASM), the parent page sends `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`.

Inside the iframe, **esbuild-wasm** runs in a dedicated Web Worker (initialized once via `esbuild.initialize({ worker: true, wasmURL })`). The iframe registers a **Service Worker** that intercepts import requests like `import 'react'` and rewrites them to `https://esm.sh/react`. Module resolution is driven by an import map plus esbuild's plugin API (`onResolve`/`onLoad`) to fetch from the virtual slide filesystem or from esm.sh.

Parent ↔ iframe communication uses a typed `postMessage` protocol with origin validation on both ends.

```typescript
interface SandboxMsg<T = unknown> { v: 1; id: string; type: string; payload: T }

type ParentToSandbox =
  | { type: 'init';          payload: { files: Record<string,string>; deps: Record<string,string> } }
  | { type: 'render-slide';  payload: { slideId: string; ir: Slide } }
  | { type: 'screenshot';    payload: { slideId: string; dpr: number } };

type SandboxToParent =
  | { type: 'ready';           payload: Record<string, never> }
  | { type: 'compile-error';   payload: { errors: BuildError[] } }
  | { type: 'render-ok';       payload: { slideId: string } }
  | { type: 'screenshot-data'; payload: { slideId: string; pngBase64: string } }
  | { type: 'runtime-error';   payload: { message: string; stack?: string } };

function call<T>(iframe: HTMLIFrameElement, msg: ParentToSandbox, timeoutMs = 5000): Promise<T> {
  return new Promise((resolve, reject) => {
    const id = crypto.randomUUID();
    const handler = (e: MessageEvent) => {
      if (e.origin !== SANDBOX_ORIGIN) return;       // origin validation
      const m = e.data as SandboxMsg;
      if (!m || m.v !== 1 || m.id !== id) return;
      window.removeEventListener('message', handler);
      resolve(m.payload as T);
    };
    window.addEventListener('message', handler);
    iframe.contentWindow!.postMessage({ v: 1, id, ...msg }, SANDBOX_ORIGIN);
    setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error('sandbox timeout'));
    }, timeoutMs);
  });
}
```

Origin must always be an exact URL, never `'*'`. Inbound log and error messages are rate-limited to prevent DoS via log spam.

**Performance targets** for the edit canvas are 60fps with 100 elements per slide at 1080p, measured via `requestAnimationFrame` timing on a mid-tier laptop (M2 MacBook Air baseline, Intel i5-10400 floor). Memory ceiling is 300MB per tab with 100 slides loaded (most represented as cached thumbnails, not live stages). Long-session memory is managed by destroying off-screen Konva stages on navigation and forcing garbage collection via explicit `stage.destroy()` calls; IndexedDB holds the thumbnail cache so reactivating a slide is a PNG-load rather than a re-render.

---

## Part VI — Slide generation pipeline (detailed)

**Phase 1 — Intent parsing.** The user submits a brief plus optional files (PDF, docx, markdown, URL). PDFs are parsed via `unpdf` (Cloudflare Workers-compatible) or `pdf-parse` (Node). Long documents are summarized via GLM-4.7-Flash (131K context, $0.06/M input) to a ~4K-token brief before being fed to the planner. The parsed intent is validated against a Zod schema capturing audience, length target, tone, and brand guidelines.

**Phase 2 — Outline generation.** Kimi-K2-Thinking (primary) or DeepSeek V3.2 (fallback) is called with a schema-forced prompt that enforces `{ title: string; audience: string; slides: Array<{ role: SlideRole; objective: string; bulletHints: string[]; suggestedPrimitive: Primitive; citations?: Citation[] }> }`. Vercel AI SDK's `streamObject` yields partial objects as they validate; the UI renders slide placeholders as each entry completes. Typical latency: 1–3 seconds for a 10-slide outline.

**Phase 3 — Parallel slide body expansion.** For each outline entry, the pipeline retrieves the top-3 matching templates (see Phase 4) and enqueues a DeepSeek V3.2 writer call. All N calls are dispatched via `Promise.all` with `p-limit(6)`; each call receives a prompt structured as `[SHARED SYSTEM | RETRIEVED TEMPLATE SCHEMA | THEME TOKENS | UNIQUE SLIDE CONTEXT]`. The first three segments are identical across N calls, so DeepSeek's prefix cache kicks in after the first call and charges 10% of miss cost on subsequent calls. Each writer streams its filled `TemplateBoundSlide` JSON; partial fills render to canvas progressively using `best-effort-json-parser` on the accumulated SSE buffer.

**Phase 4 — Layout selection.** For each outline entry, a semantic embedding of `role + objective` is computed via `text-embedding-3-small` (cheapest sufficient embedding: $0.02/M tokens). The embedding queries an HNSW index (`hnswlib-node` or Qdrant) over the 60-layout corpus and returns top-5 candidates ranked by cosine similarity. The top-1 is used by default; if the user has a preferred "style," a reranker filters by theme tag. This is the RALF pattern, adapted: retrieval from a stable curated corpus rather than from generated outputs.

**Phase 5 — Image generation dispatch.** Each slide's image slots are fanned out independently. A hero image goes to FLUX.1 Kontext pro on Azure (approximately $0.04/image, sub-second latency) with an optional brand reference image for consistency. Supporting images go to FLUX Schnell on Cloudflare Workers AI (approximately $0.0005/image at 1024² with 4 steps). Icons skip image generation entirely and resolve to Lucide (ISC, ~1,695 icons) or Phosphor (MIT, ~9,000 icons across 6 weights) SVGs by keyword match. Stock-photo slots query Pexels first (200 req/hr free, no approval), then Unsplash (50 req/hr demo, 5,000 req/hr after free production approval), then Pixabay (100 req/60s, CC0-equivalent license). Image generation runs concurrently with Phase 3 so the critical path is `max(writer_latency, image_latency)`.

**Phase 6 — VLM critic pass.** Deterministic DOM checks run immediately on every rendered slide (≤ 50ms per slide). Failures emit RFC 6902 patches that fix specific properties (reduce font size, move element to avoid overlap, swap to a higher-contrast color token). Only if a slide passes deterministic checks but scores poorly on rule-based heuristics does it go to the VLM, which is invoked at 1-in-10 sampling rate by default and on every slide only when the user opts into "premium quality." The VLM receives a 768×512 slide PNG plus a rubric prompt and returns a JSON scorecard `{ readability, balance, hierarchy, issues: string[] }`. Issues become patches.

**Phase 7 — Render to canvas or preview.** As slides complete, the IR is updated reactively (Zustand + immer). The Konva stage for the active slide mounts the filled elements via react-konva; inactive slides cache as PNG thumbnails. The preview mode (same data, different rendering tree) uses `@revealjs/react` v6 with pre-rendered PNGs per slide.

**Phase 8 — PPTX export on demand.** The IR walks recursively through each slide; each element is converted to a PptxGenJS call (see Part VIII for the full conversion table). Charts emit as native `addChart` calls when possible (bar, line, pie, doughnut, scatter, area are all natively supported), tables as `addTable`, text as `addText` with EMU positions directly translated, images as `addImage` with embedded base64 data. Export latency is ~1–3 seconds for a 20-slide deck; the PPTX is streamed back as a Blob over the REST endpoint.

---

## Part VII — Design system (solo dev version)

**Color** is based on **Radix Colors** (radix-ui/colors, MIT), a 12-step OKLCH-designed palette with documented step semantics: steps 1–2 for app and subtle backgrounds, 3–5 for UI element backgrounds (normal, hover, active), 6–8 for borders (subtle, UI, hovered), 9–10 for solid brand backgrounds (the highest-chroma step), 11 for low-contrast text, 12 for high-contrast text. Radix Colors publishes 22 chromatic scales, 6 grays, plus alpha variants. For slide backgrounds, step 1; for body text on light slides, step 12; for accent headlines, step 9 of the brand hue. Contrast is validated against WCAG 2 (4.5:1 body) during the deterministic critic.

**Tokens** follow the **DTCG v2025.10 specification** (the first stable version, announced October 28, 2025), with Style Dictionary v4 as the transform tool. A token file uses `$value`, `$type`, `$description`, and the new v2025.10 advanced color module which natively supports OKLCH, display-p3, and xyz-d50/d65 spaces.

```json
{
  "color": {
    "brand": {
      "9": {
        "$type": "color",
        "$value": { "colorSpace": "oklch", "components": [0.68, 0.18, 250] }
      }
    },
    "text": {
      "primary": { "$type": "color", "$value": "{color.brand.12}" }
    }
  },
  "font": {
    "family": {
      "body":    { "$type": "fontFamily", "$value": ["Inter", "system-ui"] },
      "display": { "$type": "fontFamily", "$value": ["Inter Display", "serif"] }
    },
    "size": {
      "body":    { "$type": "dimension", "$value": { "value": 18, "unit": "pt" } },
      "h3":      { "$type": "dimension", "$value": { "value": 24, "unit": "pt" } },
      "h2":      { "$type": "dimension", "$value": { "value": 32, "unit": "pt" } },
      "h1":      { "$type": "dimension", "$value": { "value": 43, "unit": "pt" } },
      "display": { "$type": "dimension", "$value": { "value": 57, "unit": "pt" } }
    }
  }
}
```

The `font.size` scale uses a **1.333 modular scale (perfect fourth)** anchored at 18pt body, giving a clear hierarchy that reads well on 1920×1080 projection. Color math is performed via **culori** (Evercoder/culori, MIT) for theme generation and **@texel/color** (MIT, ~60× faster than culori) for hot render paths.

**Typography** uses **Inter** (body, Google Fonts, SIL OFL) and **Inter Display** or **Playfair Display** for theme-specific headers. Curated pairings available include Inter + DM Serif Display (modern editorial), Source Sans 3 + Playfair Display (didone drama), Roboto + Poppins (geometric tech), Satoshi + Clash Display from Fontshare (trendy startup), and Space Grotesk + Inter (neutral distinctive). Fonts are loaded with `font-display: swap` and preloaded via `<link rel="preload">`.

**Spacing** uses an 8-point rhythm extended to 4, 8, 16, 24, 32, 48, 64 EMU-pt equivalents. **Shadows** are a 5-tier elevation scale from subtle (2px blur, 4% opacity) to modal (40px blur, 20% opacity) encoded as DTCG shadow composite tokens.

**The 15 slide primitives** are: title (single dominant headline + subtitle), section divider (large display text, brand background), bullet list (title + up to 6 bullets), two-column (title + two content blocks side by side), quote (large italic text + attribution), image+text (hero image + accompanying text block), stats (2–4 large number+label pairs), timeline (horizontal chronological sequence), comparison table (2–4 column tabular comparison), bar chart (native PPT chart + title + source citation), line chart (native PPT chart + legend), process flow (sequence of connected steps), team grid (N portraits + roles), Q&A/thank you (closing slide + CTA), agenda (numbered outline). Each primitive has a typed slot schema used by the writer agent and by PPTX export.

**The 4 themes** are encoded as complete DTCG token files and selectable per deck. **Modern Minimal**: Inter + neutral grays (Radix Slate 1–12) + Blue 9 accent. **Editorial Serif**: Fraunces + warm paper (Radix Sand 1–12) + Tomato 9 accent. **Technical Dark**: JetBrains Mono + dark Radix Slate Dark + Cyan 9 accent. **Corporate Navy**: Source Sans 3 + Radix Indigo Dark + Amber 9 accent. Theme swap is instantaneous because all colors in the IR are TokenRef strings resolved at render.

---

## Part VIII — PPTX export fidelity

**PptxGenJS v4.0.1** (gitbrent/PptxGenJS, ~5,000 stars, MIT, last release June 2025, 220+ dependents) is the core export engine. It supports ~200 shape types, six native chart families (bar/line/pie/doughnut/scatter/area plus variants), master slides with `defineSlideMaster`, tables with auto-paging and merged cells, and image embedding for PNG/JPG/GIF/BMP/base64/SVG. It does *not* support animations or native font embedding out of the box; font embedding is layered via **pptx-embed-fonts** (0.0.6, MIT, single-author — marked verify before production adoption, usable for core fonts but monitored for breakage). Template-based partial exports use **pptx-automizer** (0.8.1, MIT, active) which can load an existing .pptx and selectively modify slides via `modifyElement(name, [modify.setPosition(...), ...])`, combinable with PptxGenJS via `automizer.use('pptxgen', new pptxgen())`.

### Konva → PptxGenJS conversion table

| Konva node | Vector preservation | PptxGenJS call | Rasterize if |
|---|---|---|---|
| `Rect` (cornerRadius=0) | Yes | `addShape(ShapeType.rect, {x,y,w,h,fill,line,rotate})` | — |
| `Rect` (cornerRadius>0) | Yes | `addShape(ShapeType.roundRect, {...,rectRadius})` | — |
| `Circle`, `Ellipse` | Yes | `addShape(ShapeType.ellipse, {x,y,w,h,fill,line})` | — |
| `Line` (straight) | Yes | `addShape(ShapeType.line, {x,y,w,h,line})` | — |
| `Line` (bezier) | Partial | custom `points` with `curve:{type:'cubic'\|'arc'}` | Complex paths |
| `Path` (SVG `d`) | Partial | parse `d` → points; fallback rasterize | Complex SVG |
| `Text` | Yes | `addText(text, {x,y,w,h,fontFace,fontSize,color,bold,italic,align,valign,autoFit})` | — |
| `Image` | Yes | `addImage({data: dataURL, x,y,w,h, sizing})` | — |
| `Group` | Iteration | recursively emit children with offset | Rotated groups with complex layout |
| Fill: linear/radial gradient | No | — | Always rasterize |
| Fill: pattern image | No | — | Always rasterize |
| Filter: blur/mask/composite | No | — | Always rasterize |
| Multiple/colored shadows | No | — | Always rasterize |
| Text on path | No | — | Always rasterize |

**Rasterization** goes through `@resvg/resvg-js` (Rust-backed, fast, MIT) or `node-canvas` at 2× DPI (192dpi target), then `addImage({data: 'data:image/png;base64,...'})`. All chart primitives emit as native `addChart(pptx.charts.BAR, data, opts)` (or LINE/PIE/DOUGHNUT/SCATTER/AREA) rather than rasterized PNG, preserving PowerPoint editability — this is a meaningful differentiator since most competitors export charts as flat images.

### Font metrics drift mitigation

Web text measurement (`ctx.measureText`) uses the web font's glyph metrics; PowerPoint uses whatever the viewer's machine has installed. Mitigations: embed core fonts via `pptx-embed-fonts` (produces OOXML `embeddedFontLst`); set `autoFit: true` on text boxes so PowerPoint rescales; pad text box width by ~5–8% over measured width; pair web fonts with metrics-compatible PowerPoint fallbacks (Inter → Segoe UI, Source Sans → Calibri, Fraunces → Cambria).

### CI fidelity harness

The harness runs on every pull request. For each of the 60 golden template renders plus ~20 freeform test decks, it executes:

```bash
# Headless LibreOffice: pptx → pdf (all slides; --convert-to png exports slide 1 only)
soffice --headless -env:UserInstallation=file:///tmp/lo_$$ \
        --convert-to pdf --outdir ./out input.pptx

# PDF → PNG at 200 DPI (all pages)
pdftoppm -png -r 200 ./out/input.pdf ./out/slide
```

Then Node:

```typescript
import ssim from 'ssim.js';                  // obartra/ssim, verified on npm
import pixelmatch from 'pixelmatch';

for (const slide of slides) {
  const { mssim } = ssim(referencePng[slide.i], candidatePng[slide.i]);
  const threshold = slide.isTemplate ? 0.95 : 0.88;
  expect(mssim).toBeGreaterThanOrEqual(threshold);
  if (mssim < threshold) {
    const diffPng = pixelmatchDiff(reference, candidate);
    uploadCiArtifact(diffPng);
  }
}
```

LibreOffice version is pinned in the CI Docker image (exports shift subtly between 7.x and 24.x); fonts are installed identically to the runtime image; slide numbers and timestamps are masked before SSIM comparison.

**Known limits owned publicly.** Animations are not preserved on export (static snapshot only); the product should present PPTX export as "content + layout fidelity; animations are web-only." Custom fonts fall back to a Microsoft equivalent on viewer machines without the font installed. Complex SVG paths are rasterized, losing PowerPoint shape-level editability. Gradients become PNG. These limits are documented on the export dialog so users aren't surprised.

---

## Part IX — Phased roadmap (solo developer, 24–28 weeks)

**Weeks 1–2: Foundations.** Repo setup, Next.js 15 on Vercel Pro (or Cloudflare Pages if bandwidth projections favor it), Supabase Pro for Postgres + pgvector, Upstash Redis, Cloudflare R2 for asset storage. External auth integration via JWT validation middleware. Stripe billing scaffolding. PostHog telemetry. CI pipeline with typecheck, lint, and unit tests.

**Weeks 3–6: Core generation pipeline.** Planner + Writer agents against DeepSeek V3.2 and Kimi-K2-Thinking with Vercel AI SDK's `streamObject` + Zod. SSE streaming to the client. Partial JSON parsing via `best-effort-json-parser`. The layout retriever is initially a simple lookup table (no embeddings yet); the full HNSW index lands in week 7. No editor yet — output renders to read-only HTML previews. Ship a narrow "paste brief → get deck" demo.

**Weeks 7–10: Konva editor minimum viable.** Konva stage, Transformer, alignment guides, snap-to-grid, multi-select marquee, z-order, undo/redo with command pattern + immer coalescing. Tiptap overlay for inline text editing. `@tanstack/react-virtual` thumbnail rail with `@dnd-kit/sortable` reorder. Ten curated templates hard-coded (not the full 60 — those arrive post-launch). Hard scope cap: no real-time collaboration, no advanced vector operations, no boolean shape operations.

**Weeks 11–14: PPTX fidelity (Bet 1).** PptxGenJS integration. Konva → PptxGenJS conversion walker for every element kind in the IR. Native chart export for bar/line/pie/doughnut. Font embedding via pptx-embed-fonts. The CI fidelity harness with 20 golden test decks. Iterate until SSIM ≥ 0.95 for templates, ≥ 0.88 for freeform.

**Weeks 15–17: Template-to-free-primitive migration (Bet 3).** The `ejectSlide` and `reattachElement` functions. JSON-Patch edit-preservation across regeneration via `fast-json-patch`. Conflict resolution UI for patches that became invalid. This phase is the novel-UX phase; plan at least one week of user testing with 10 beta users.

**Weeks 18–20: Standalone HTML export + real-time streaming polish (Bets 4 and 5).** Self-contained HTML export with inlined GSAP animations and embedded base64 images (single file, works offline). Refine the streaming UX with agent-visibility indicators, cache-hit telemetry dashboard (internal), image placeholder strategy during async image generation.

**Weeks 21–23: Billing, onboarding, growth.** Credit system mirroring Gamma's model (free tier gives N one-time credits, paid tiers unlock streaming). Public gallery for marketing, SEO landing pages per use-case ("AI pitch deck generator," "sales deck generator," etc.). Referral flow. Rate limiting hardening. Abuse prevention (captcha on signup, per-IP throughput caps).

**Weeks 24–26: Private beta and hardening.** Invite 50–200 testers from waitlist. Load test the generation pipeline to 100 concurrent decks. Cost-per-deck instrumentation. Support tooling (Plain for ticketing).

**Weeks 27–28: Public launch.** Product Hunt and Hacker News launch. Docs site with API reference for the export endpoints. Pricing page live. Postmortem plan ready for launch-day issues.

**Explicitly deferred to V2.** Real-time multiplayer collaboration via Yjs + Hocuspocus — instead, offer solo editing with autosave and JSON-Patch version history. Mobile app — responsive web works, native comes later. Enterprise SSO (SAML), SOC 2 certification — start paperwork week 20 for later close. Video export — FFmpeg-based if it ships, Remotion only if revenue justifies the Company License. Full Figma-grade features beyond the bounded canvas (boolean operations, auto-layout, components library). Any 3D slide content.

---

## Part X — Cost model

Per-deck cost at 10 slides with typical content: approximately **$0.045–0.070** in variable costs (LLM + images). Details in Part IV. At $10/mo average ARPU with 5 decks per user, gross margin is ~97%; even a free-tier user costs less than $0.35/month if capped to 5 decks/month free.

Pricing strategy follows Gamma's precedent: a **free tier** with ~400 one-time credits and the generated deck watermark, a **Plus tier** at $10/mo (annual $8/mo) for unlimited AI generation and PPTX export, a **Pro tier** at $20/mo for standalone HTML export, FLUX Kontext hero images, priority generation queue, and API access. A **Team tier** at $20/user/mo bundles shared brand kits, per-seat templates, and admin controls. An **Enterprise tier** priced custom adds SSO, audit logs, and on-prem LLM routing.

Infrastructure monthly cost tracks the user count as documented in Part IV. Key cost-saving tactics: use Cloudflare Workers + R2 for asset serving (much cheaper egress than Vercel), aggressive DeepSeek prompt caching, default image generation to FLUX Schnell on Cloudflare, use Unsplash/Pexels before any generated image, offload long-running jobs to Inngest (or BullMQ self-hosted on Railway/Fly for tighter cost control).

---

## Part XI — The 5 defining bets

**Bet 1: PPTX fidelity as a promise.** The most defensible wedge. Chronicle admits PPT export is still rolling out through 2026; Gamma's export is routinely criticized on forums for formatting drift; Prezi does not offer PPTX at all; Pitch's export is adequate but not a selling point. Committing publicly to "your deck round-trips cleanly into PowerPoint with native charts, native tables, and embedded fonts" — validated by a CI harness with published SSIM thresholds — is a hard-to-copy enterprise signal. Requires 4 weeks of concentrated work (weeks 11–14) but pays back across the entire product lifecycle.

**Bet 2: Custom Figma-grade bounded-canvas editor.** The moat that keeps users from walking. Building on Konva + Tiptap + immer + command pattern avoids the $6,000/yr tldraw SDK fee and the $199–$399/mo Polotno license while still delivering professional interaction quality. The bounded-canvas scope (one 1920×1080 frame per slide, not infinite) is what makes this tractable for a solo developer in 4 weeks (weeks 7–10); infinite-canvas vector editors take teams years. Risk: the editor becomes a sinkhole. Mitigation: hard scope cap on week 10 deliverables, defer anything fancy to V1.5.

**Bet 3: Template-to-free-primitive migration.** The differentiating UX primitive. Every competitor forces a binary choice — rigid templates (Beautiful.ai, Decktopus) or blank canvas (Pitch, Canva). The ability to start inside a safe template, "eject" when the user needs freedom, and preserve user edits across AI regeneration via JSON-Patch three-way merge is genuinely novel. Requires Bet 2 as prerequisite.

**Bet 4: Real-time streaming generation.** Table stakes by mid-2026 (ALLWEONE, Gamma, Presenton all stream), so not a moat on its own. The quality of the stream is the differentiator: first slide visible in <2 seconds, full deck in 5–10 seconds, prompt-prefix caching exploited hard for 90% cost reduction on fan-out. Skeleton-of-Thought parallel decoding is the empirical pattern (1.9–2.4× faster per ICLR 2024 measurements). Ship it because users expect it; don't mistake it for defensibility.

**Bet 5: Standalone HTML export.** Cheap insurance with a strong narrative. A single self-contained HTML file (inlined GSAP animations now fully free per Webflow's April 2025 license change, embedded base64 images, inline CSS) guarantees that the user's deck works even if the SaaS shuts down — a trust signal the lock-in-forward incumbents deliberately refuse. Costs maybe two weeks to implement (part of weeks 18–20). Marketing angle: "your decks aren't hostage." Measurable retention benefit hard to prove, but the signal aligns with privacy-conscious and open-web-aligned buyers.

---

## Part XII — Risks and unsolved problems

**PPTX fidelity regressions break enterprise trust.** Highest-impact risk. Mitigation: the golden-deck regression harness runs on every merge with SSIM thresholds gating deploys; private beta with 20 enterprise-shape decks before public launch; label export as "beta" for the first three months so expectations are calibrated.

**LLM cost blowout from low cache-hit rates or adversarial prompts.** Hard per-user credit caps from day one. Prefix-cache hit-rate telemetry validated in week 4 (target ≥70% across production traffic). Per-request token ceilings. Cloudflare WAF in front for rate-limit enforcement. Budget alerts at 75% of monthly projection.

**Gamma, Canva, or Pitch ships feature parity.** High-probability medium-impact. Gamma already ships most of what V10.2 ships; Canva's Magic Design is formidable. Defense: compete on the axes incumbents can't easily match — PPTX fidelity (they deprioritize it), standalone HTML export (they refuse it), and template-to-primitive migration (they're committed to one or the other, not both).

**Editor scope creep.** The Bet 2 trap: a Figma-grade editor is open-ended. Mitigation: the 4-week cap is enforced at weeks 7–10; any feature not in the MVP spec ships in V1.5 at earliest; user requests triaged against a public "later" list.

**DeepSeek API outage, deprecation, or geopolitical block.** DeepSeek is a Chinese provider; regulatory action is non-zero risk. Mitigation: abstract all LLM calls behind a router (Vercel AI SDK, OpenRouter, or LiteLLM); maintain tested fallback paths to Mistral medium-2505, Kimi-K2, and Groq Llama-3.3-70B; health-check + auto-failover.

**Vercel bandwidth or DDoS bill shock.** Publicly documented cases of $20K+ surprise bills. Mitigation: Cloudflare in front of Vercel for WAF, rate limit, and caching; Vercel spend caps configured at 100% (pauses project rather than billing); evaluate migration to Cloudflare Workers + R2 for heavy traffic paths before the 10K-user milestone.

**FLUX image licensing or content-safety issues.** User prompts can generate problematic images. Mitigation: Azure Foundry's integrated Content Safety filter on all image calls; Cloudflare's llama-guard-3-8b guardrails on LLM prompts; prompt logging for audit; moderation gate before any image is published or embedded in exported decks.

**Solo-dev burnout.** The highest-probability personal risk. Mitigation: the 24–28 week timeline assumes ~40 hrs/week with no sprinting. Ship weekly to maintain momentum. Recruit a part-time designer from week 12 onward (the primitives are in by then; the four themes need design polish). Build a small paid beta (20 users at $20/mo = $400/mo) by week 20 to validate monetization before full launch.

**Unsolved post-PMF problems.** Real-time multiplayer remains complex (add Yjs + Hocuspocus after V1). Vision critic at scale will need either self-hosted Phi-4 on dedicated GPU or continued reliance on Qwen2.5-VL-7B on Hyperbolic (cost scales linearly). SOC 2 certification takes 6–9 months; start paperwork at week 20. Enterprise SSO (SAML) is mandatory for most enterprise sales; defer to V2 unless a specific customer signs a letter of intent. Video export via Remotion requires the Company License for any team > 3 people, so defer until ARR justifies the $100/mo minimum. Full Figma parity (components, auto-layout, boolean ops) is a multi-year project — the bounded-canvas scope buys 24 months of product validation before that call needs to be made.

---

## Conclusion

V10.2 is the first version of this plan where every architectural claim is traceable to a named pattern, paper, or production engineering blog post, and every library dependency has a verified license, maintenance status, and realistic adoption risk. The plan trades the speculative ambition of V9/V10 (infinite canvas, twelve agents, self-evolving code) for a grounded, defensible core: a bounded Figma-grade editor on Konva, a four-agent pipeline on Skeleton-of-Thought fan-out, a hybrid JSON IR that lets slides live in template or free mode with reversible migration, and a PPTX export committed to measurable SSIM fidelity. The five defining bets — PPTX fidelity, the custom editor, template-to-primitive migration, real-time streaming, and standalone HTML export — are specifically chosen because they are axes on which the incumbent AI presentation tools are deliberately weak. The 24–28 week roadmap is costed, risked, and explicitly bounded; features that cannot be delivered by a solo developer in that window are named and deferred rather than promised and delivered late.

The single most important design decision in V10.2 is the elevation of **stable UUID-keyed identity** to an invariant across every subsystem: IR nodes, template slots, user edits, AI regenerations, undo commands, JSON-Patch paths, and collaboration ops. Every loophole in V9/V10/V10.1 that involved "regeneration broke my edit" or "undo doesn't work after AI runs" traces back to positional paths. V10.2 makes positional paths a bug and UUID paths the only legal way to reference an element. Everything downstream — edit preservation, layout retrieval, cache hit rate, PPTX export stability, command-pattern coalescing — becomes easier once that invariant holds.

Ship the pipeline by week 6, the editor by week 10, the PPTX fidelity by week 14, and the novel migration UX by week 17. Launch publicly by week 28. The rest is iteration.