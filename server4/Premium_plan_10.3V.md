# Premium Plan 10.3V

## The centralized founder plan for a real-time AI presentation SaaS

Version 10.3 is the first plan that properly unifies the strongest parts of V9, V10.1, and V10.2 without carrying forward their weakest assumptions.

The target is clear:

- Chronicle-grade presentation quality
- Figma-grade editing precision
- Canva-grade ease of use and collaboration
- Dokie-grade content-first generation and refinement
- PPTX/HTML/Reveal fidelity strong enough for real business use
- Real-time SaaS behavior, not a slow one-shot deck generator

This plan is grounded in two realities:

1. The current repo already contains meaningful editor, sync, render, and generation infrastructure.
2. The product must only rely on models and services that are actually available in this project.

V10.3 is not a speculative "moonshot architecture." It is a buildable migration path from the current server4 codebase into a strong standalone product.

---

## 1. Executive summary

The product should not be "another AI slide generator." It should be a real-time deck workspace that lets users:

- start from prompt, PDF, docx, URL, existing PPTX, or loose notes
- generate a full deck draft with strong narrative and polished layouts
- edit every slide directly in a precise visual editor
- collaborate live with teammates
- refine with AI at slide, section, or element level
- preview instantly
- export to PPTX, PDF, HTML, and Reveal-based live presentation mode

The central architectural decision in V10.3 is this:

**Use a dual-surface workspace.**

- Surface A: a bounded slide studio for precise editing of actual presentation slides
- Surface B: a freeform storyboard/workbench for idea capture, references, alternate layouts, notes, and branching structure

This resolves the main tension across V9 and V10.2:

- V9 overcommitted to infinite-canvas slide editing
- V10.2 correctly moved to bounded slides, but it underplayed the need for a wider creative workspace

The right answer is not one or the other. The right answer is:

- infinite workbench for thinking
- fixed 16:9 artboards for slides

That gives us:

- Canva-like whiteboard/workbench behavior
- Figma-like artboard precision
- Chronicle-like clean presentation output
- Dokie-like content-driven refinement

---

## 2. What V10.3 keeps, removes, and adds

### 2.1 Keep from V9

- strong ambition on slide quality and design intelligence
- layered think-to-render pipeline
- strong data visualization and diagram support
- serious QA and regression goals
- canvas editing as a first-class product area
- brand system, template intelligence, and partial regeneration

### 2.2 Keep from V10.1

- available-models-only policy
- grounded fit with current server4 services and routes
- 4-role core generation topology instead of 12 agents
- finite template system with controlled freedom
- DTCG token strategy and structured rendering pipeline
- safe self-refine instead of fake self-training

### 2.3 Keep from V10.2

- bounded-canvas editor architecture
- hybrid template/free primitive IR
- strong sandbox architecture
- real-time progressive generation and preview
- standalone HTML export as a differentiator
- PPTX fidelity harness as a hard requirement

### 2.4 Remove

- Generative Layout Algebra as the core system
- 12-agent orchestration
- speculative self-evolving code agent ideas
- fully open-ended infinite-canvas slide editing as the primary mode
- dependence on unavailable Gemini, Claude, or frontier OpenAI models
- multimodal critic dependence on models not already wired in this project

### 2.5 Add in V10.3

- dual-surface workspace: storyboard/workbench + slide studio
- a true collaboration model based on object/property operations
- a stronger layout system that combines retrieval, constraints, and visual scoring
- three preview tiers for speed: local canvas, reveal preview, isolated code sandbox
- clearer product strategy around Chronicle/Figma/Canva/Dokie-level user expectations
- a build sequence that matches the current repo instead of replacing it

---

## 3. Verified inspiration map

The following public product signals are real and useful:

### Chronicle

Verified public signals:

- starts from raw notes, outlines, docs, or existing decks
- generates polished, on-brand slides
- supports AI editing on a freeform canvas
- exports to PPT, PDF, or website
- emphasizes design quality, brand rules, and real-time collaboration

What we should take from Chronicle:

- presentation-native polish
- narrative clarity
- low-clutter UX
- export breadth
- design quality that looks intentional, not generic

### Figma

Verified engineering signals:

- client/server real-time collaboration over WebSockets
- document as a tree of objects with IDs and property values
- simplified server-authoritative sync model inspired by CRDT ideas
- property-level conflict handling instead of universal OT complexity

What we should take from Figma:

- object-based document model
- immediate local interaction with server reconciliation
- property-level operations
- robust multiplayer for a visual editor
- artboard precision rather than vague generative editing

### Canva

Verified public product signals:

- prompt-to-presentation flow
- presentation to whiteboard expansion and whiteboard to presentation conversion
- real-time editing and collaboration
- cinematic effects and broad export modes
- strong template and content-library workflow

What we should take from Canva:

- low-friction template-first workflow
- easy collaboration and whiteboard/workbench concepts
- broad export and device accessibility
- simple, non-threatening editing UX for non-designers

### Dokie

Verified public signals:

- content-first layout and structure
- multi-format input handling
- brand template upload and reuse
- advanced refinement with layout-preserving edits
- business-deck orientation rather than toy demos

What we should take from Dokie:

- content-first slide structuring
- refinement that preserves polish
- reuse of uploaded templates and brand systems
- strong PPT-oriented workflows

### V10.3 product positioning sentence

**Build a deck workspace that combines Chronicle's polish, Figma's editing model, Canva's workflow breadth, and Dokie's content-first refinement on top of the current server4 backend.**

---

## 4. Ground truth from the current repo

V10.3 must start from what is already in server4.

Already present in the repo:

- editor routes for slide CRUD, element CRUD, validation, versioning, regeneration, and HITL
- WebSocket sync infrastructure for collaborative editing
- server-side CRDT-style authoritative merge logic
- Redis-backed editor session metadata store
- reveal build caching and renderer collections
- react build and PPTX build cache collections
- V3 generation to editor bridge
- existing DSL v2 models and slide generation services
- FastAPI, MongoDB, Redis, Celery, Azure Blob, and Chroma infrastructure

This means V10.3 should **extend** the current substrate, not restart architecture from zero.

The migration philosophy is:

- keep the Python backend as the orchestration and persistence plane
- add a stronger frontend editor/application layer
- evolve DSL v2 into a document-graph-compatible v3.1 model through adapters
- preserve current renderers and caches where possible

---

## 5. Product experience in V10.3

### 5.1 Core flow

1. User starts from prompt, file, URL, PPTX, or mixed input.
2. System generates a storyboard and first-pass deck draft.
3. User enters a workspace with two synchronized views:
   - Storyboard/Workbench
   - Slide Studio
4. AI continues streaming slides, visuals, and suggestions.
5. User edits slides visually, asks for localized AI changes, and sees live preview.
6. User presents, shares, or exports.

### 5.2 The two workspace surfaces

#### A. Storyboard/Workbench

Purpose:

- collect source material
- keep notes, references, comments, citations, and alternatives
- branch narrative paths
- compare template directions
- drop loose charts, screenshots, diagrams, and copy fragments
- convert clusters of notes into slides or sections

This is where Canva whiteboard and early-stage FigJam behavior belongs.

#### B. Slide Studio

Purpose:

- precise editing of one actual slide at a time
- alignment, snapping, layers, typography, spacing, and visual polish
- property panel control
- slot locking/unlocking
- partial regeneration anchored to specific elements or regions

This is where Figma-like slide precision belongs.

### 5.3 Key UX promise

The user should feel like the product is fast in three distinct ways:

- fast to think with
- fast to edit with
- fast to preview with

---

## 6. Core architecture

### 6.1 Architecture in one sentence

Use the existing FastAPI/Mongo/Redis/Celery backend as the control plane, add a React-based deck workspace as the interaction plane, use a hybrid document graph as the state plane, and keep Reveal/PPTX/HTML compilers as the presentation plane.

### 6.2 System overview

```text
[Input ingest]
    |
    v
[Planner + summarizer]
    |
    v
[Storyboard graph]
    |
    +------------------------+
    |                        |
    v                        v
[Template retrieval]    [Brand + asset extraction]
    |                        |
    +-----------+------------+
                |
                v
        [Slide writer fan-out]
                |
                v
        [Design compiler]
                |
                +-------------------+
                |                   |
                v                   v
       [Slide Studio state]   [Workbench state]
                |
                +---------+------------+-------------+
                          |            |             |
                          v            v             v
                  [Canvas preview] [Reveal preview] [Sandbox preview]
                          |
                          v
               [PPTX | PDF | HTML | Present mode]
```

### 6.3 Frontend stack

V10.3 should introduce a real frontend app under `frontend/` using:

- React + Vite
- TanStack Query for server state
- Zustand + Immer for local editor state
- react-konva for slide studio rendering
- Tiptap for rich text editing
- dnd-kit for sidebars, lists, and thumbnail reorder
- GSAP for presentation-grade motion where needed

Why Vite instead of a heavier SSR-first framework for the core app:

- the editor is interaction-heavy, not SEO-heavy
- the backend is already FastAPI
- Reveal ESM and canvas workflows fit cleanly into a Vite client app
- we avoid unnecessary architectural duplication

Marketing pages can be separate later if needed.

---

## 7. Document model: V10.3 hybrid graph

### 7.1 Core idea

V10.3 should move from a slide-only DSL mindset to a **deck document graph**.

That graph has two major node families:

- workspace nodes for the workbench
- slide artboards for actual presentation output

### 7.2 Canonical model

```ts
type DeckDocumentV10_3 = {
  id: string;
  schemaVersion: "10.3";
  theme: ThemePack;
  brand?: BrandPack;
  workspace: WorkspaceBoard;
  slides: SlideArtboard[];
  assets: AssetRecord[];
  checkpoints: HitlCheckpoint[];
  version: number;
  createdAt: string;
  updatedAt: string;
};

type WorkspaceBoard = {
  nodes: WorkspaceNode[];
  edges: WorkspaceEdge[];
  viewport: { x: number; y: number; zoom: number };
};

type SlideArtboard = {
  id: string;
  title?: string;
  size: { emuW: 12192000; emuH: 6858000 };
  mode: "template" | "hybrid" | "free";
  templateId?: string;
  elements: SlideElement[];
  slotBindings?: SlotBinding[];
  notes?: string;
  meta?: { sectionId?: string; objective?: string; sourceNodeIds?: string[] };
};
```

### 7.3 Core invariants

- Every slide and element has a stable UUID.
- Slide studio uses EMU-based canonical geometry for export fidelity.
- Workbench nodes use world-space coordinates for freeform planning.
- Template mode, hybrid mode, and free mode are all first-class.
- Regeneration never depends on array positions; it depends on stable IDs.

### 7.4 Migration from current repo

- `PresentationDSL` v2 remains the current execution format for existing services.
- V10.3 introduces a v3.1 adapter layer around it.
- Existing V3 generation output continues to bridge into editor sessions.
- New frontend operates on `DeckDocumentV10_3` and serializes to current DSL where needed until full migration is complete.

This avoids a dangerous big-bang rewrite.

---

## 8. The editor model

### 8.1 Central decision

**Do not make infinite canvas the primary slide editing surface.**

That is where V9 drifted into unnecessary complexity.

Instead:

- the workbench is infinite or effectively unbounded
- each slide is a bounded artboard

### 8.2 Slide Studio behavior

The slide studio should use the bounded-canvas mechanics from V10.2:

- layered Konva stage
- selection and multi-select transformer
- alignment guides and object snapping
- drag layer for performance
- keyboard shortcuts for nudge, z-order, grouping, duplicate, delete
- inline text editing by swapping to a DOM/Tiptap editor
- thumbnail virtualization and PNG thumbnail cache

### 8.3 Figma-like precision features

Required editing features:

- pixel-accurate move/resize/rotate
- smart guides and distance markers
- grid and layout overlays
- lock/hide/group/ungroup
- layer panel
- inspector panel
- reusable components
- slot lock and unlock behavior
- multi-select property edits
- copy style / paste style
- element variants and quick alternatives

### 8.4 Canva-like ease features

Required ease-of-use features:

- insert from template blocks
- quick apply theme
- drag in charts, tables, and icon sets
- convert a workbench cluster into a slide draft
- one-click replace image or chart style
- simple comments and reaction UX
- real-time cursors and presence

### 8.5 Chronicle/Dokie-like refinement

Required AI editing behaviors:

- "rewrite only this text box"
- "turn this bullet block into a 2-column comparison"
- "swap this chart to a waterfall"
- "make this slide feel more investor-ready"
- "keep layout, improve typography"
- "apply brand palette without moving structure"

This means AI edits must operate on selected nodes or scoped slide regions, not force full-slide rewrites by default.

---

## 9. Collaboration and sync model

### 9.1 Reuse the current repo substrate

The repo already has the right skeleton:

- sync WebSocket hub
- server-side authoritative CRDT-style merge
- session metadata in Redis
- presence and operation bus primitives

V10.3 should extend that rather than replace it.

### 9.2 Collaboration model

Use a Figma-inspired object/property sync model:

- not full OT for the whole document
- not raw JSON blob overwrites
- operations scoped to object IDs and property paths

Core operation types:

- `set_prop`
- `insert_node`
- `delete_node`
- `move_node`
- `resize_node`
- `reparent_node`
- `reorder_node`
- `batch`

### 9.3 Text editing strategy

Text is the one area where object-level sync alone is not enough.

Use this split:

- rich text inside a text element is handled by the editor layer
- slide and element structure is handled by the object/property sync model

This keeps collaboration tractable without turning the whole application into a generic CRDT research project.

### 9.4 Conflict model

Use the current server-authoritative merge philosophy:

- local edits apply instantly
- server reconciles and increments revision
- conflicts are recorded at property path level
- user-facing conflict UI appears only when needed

This is strong enough for a visual editor and much easier to reason about than universal OT.

---

## 10. Generation pipeline

### 10.1 Core topology

Keep the V10.1 simplification: 4 core roles, plus deterministic tool layers.

- Planner
- Writer
- Designer
- Critic

The retriever, validator, and render compiler are system layers, not "agents."

### 10.2 Available-model-only policy

V10.3 may only use the models already available in this project:

LLM inventory:

- Kimi-K2-Thinking
- Phi-4-reasoning
- DeepSeek-V3.2
- GPT-4o-mini
- Mistral-medium-2505
- Groq pool
- Cloudflare Worker models already in the router
- OpenRouter Qwen fallback already in the router

Image inventory:

- Azure FLUX.1-Kontext-pro
- Nvidia Stable Diffusion 3 Medium
- Cloudflare Phoenix
- Cloudflare Lucid

Explicitly out of scope for core architecture:

- Claude-dependent workflows
- Gemini-dependent workflows
- research ideas that require models not already wired here

### 10.3 Routing table

| Task | Primary | Fallback | Why |
|---|---|---|---|
| long-horizon deck planning | Kimi-K2-Thinking | DeepSeek-V3.2 | strongest reasoning for structure and narrative |
| per-slide writing fan-out | DeepSeek-V3.2 | Mistral-medium-2505 or Groq pool | cheap parallel writing with strong structure |
| schema repair and strict JSON normalization | GPT-4o-mini | Mistral-medium-2505 | reliable structured output enforcement |
| low-latency chat refine | Groq pool | GPT-4o-mini | better interaction feel |
| quality critic on structured metrics | Phi-4-reasoning | GPT-4o-mini | reasoning over layout and quality signals |
| long-context summarization | Cloudflare router models or Kimi | DeepSeek-V3.2 | use current router inventory |
| hero image | Azure FLUX.1-Kontext-pro | SD3 Medium | highest-value image slot |
| support visuals | Cloudflare Phoenix or Lucid | SD3 Medium | cheaper general support images |

### 10.4 Pipeline stages

1. Ingest and normalize
2. Planner creates storyboard and section objectives
3. Template/layout retriever finds candidate structures
4. Parallel slide writers fill content into schema-bound slide plans
5. Design compiler maps content to actual slide elements
6. Image pipeline fills visual slots
7. Deterministic quality engine scores output
8. Critic proposes targeted patches
9. Draft lands in the editor workspace for user refinement

### 10.5 The right replacement for GLA

V9's biggest conceptual overreach was GLA.

V10.3 replaces it with a **Layout Intent Engine**:

- retrieval over a curated template/layout corpus
- constraint resolution for exact placement
- visual weight scoring to break ties
- deterministic overflow and spacing correction

This gives most of the value that V9 wanted without the speculative algebra layer.

### 10.6 Regeneration model

Regeneration must support five scopes:

- element-only
- selected region
- slide-only
- section-only
- whole-deck

User edits are preserved through stable IDs and patch-based three-way merge.

This is non-negotiable.

---

## 11. Design intelligence and layout system

### 11.1 Principles

- content leads structure
- structure leads layout
- layout leads style application
- style never destroys clarity

### 11.2 Theme and token system

Keep the DTCG-based direction from V10.1.

V10.3 design system layers:

- foundation tokens: color, type, spacing, radius, shadow, motion
- semantic tokens: title, body, accent, data-positive, data-negative, surface, border
- component tokens: chart, callout, quote, stat, agenda, comparison, diagram
- brand overlays: uploaded fonts, color accents, logo use rules, spacing preferences

### 11.3 Template library philosophy

Do not go back to V9's bloated 100+ template fantasy at the start.

Instead:

- keep a finite high-quality template corpus
- make it deeper in quality, not larger in count
- support template -> hybrid -> free editing transitions

Recommended starting library:

- 18 core slide archetypes
- 6 style families
- 108 high-quality combinations

This is enough variety without becoming unmaintainable.

### 11.4 Data and diagram system

V10.3 should retain V9's serious attitude toward non-trivial content, but scope it properly.

Phase 1 primitives:

- charts
- tables
- timelines
- process diagrams
- comparison matrices
- KPI/stat cards
- code blocks
- architecture diagrams

Preferred implementation path:

- strongly typed chart schema
- SVG-first rendering where possible
- Mermaid support for technical diagrams
- deterministic table layout rules
- optional advanced diagram compiler later

### 11.5 Chronicle-grade quality target

The product should look designed even when the user does very little.

That means:

- disciplined typography
- intentional whitespace
- limited palette variance
- strong hierarchy
- layouts that feel authored, not randomly generated

The design moat is not "more AI." The moat is **taste encoded into deterministic systems plus high-quality generation constraints**.

---

## 12. Sandbox and preview architecture

### 12.1 The three preview tiers

To feel fast, the product needs three different preview systems.

#### Tier 0: Local canvas preview

- immediate
- used while dragging, typing, resizing, or applying local edits
- no compile step

#### Tier 1: Reveal preview

- near-live presentation preview
- used for present mode, speaker flow, slide-to-slide transitions, and share preview
- compiled and cached aggressively

#### Tier 2: Isolated code sandbox preview

- only for interactive/code-heavy slides
- separate origin
- async compile
- snapshot fallback when not active

### 12.2 Sandbox architecture

Keep the V10.2 security direction.

Core rules:

- sandbox served from a separate origin
- `iframe sandbox="allow-scripts"` without `allow-same-origin`
- strict CSP
- typed `postMessage` protocol with origin validation
- esbuild-wasm in a worker for compile
- service worker or module resolver for dependency fetch
- rate-limited log and error channels

### 12.3 Build choice

Do **not** make full WebContainers the default phase-1 choice.

Reason:

- impressive technology, but heavier startup and memory profile
- more complexity than most slide use cases require
- code slides need fast isolated render, not full general-purpose dev environments on day one

V10.3 phase-1 sandbox should be closer to a self-hosted Sandpack-like client runtime:

- fast warm starts
- low memory footprint
- deterministic allowed dependencies
- safe screenshot capture back into the deck

WebContainers can remain a future premium/dev mode path if justified later.

### 12.4 Preview caching strategy

- local thumbnails cached in IndexedDB
- reveal output cached in `reveal_builds`
- React/interactive output cached in `react_builds`
- export-ready HTML cached in `html_builds`
- PPTX cached in `pptx_builds`

This aligns directly with the storage patterns already visible in the repo.

---

## 13. Rendering and export system

### 13.1 Editing surface

- Slide Studio on Konva

### 13.2 Presentation surface

- Reveal.js with the official React wrapper for preview and present mode

### 13.3 Export surfaces

- PPTX for real business deliverability
- PDF for static delivery
- standalone HTML for shareable interactive decks
- Reveal-based live presentation mode

### 13.4 Fidelity principle

PPTX fidelity is a product pillar, not an afterthought.

V10.3 keeps the V10.2 idea of a fidelity harness:

- compile PPTX
- render through headless office/PDF pipeline
- compare PNG outputs against expected slide renderings
- flag drift in font metrics, spacing, line breaks, and chart sizing

The product will not win serious users if the export is unreliable.

---

## 14. Quality system

### 14.1 Deterministic quality first

Because V10.3 is constrained to available models, the quality system should be deterministic-first.

Required checks:

- overlap detection
- overflow detection
- contrast rules
- title and body density limits
- whitespace and balance heuristics
- font size sanity
- chart label and legend fit
- broken asset detection
- missing citations or unsupported claims

### 14.2 AI critic second

The Critic should reason over structured quality signals and the slide document, not depend on unavailable multimodal magic.

That means:

- structured layout metrics
- content density summaries
- style consistency signals
- brand compliance checks
- rubric-based score output

### 14.3 Regression system

Keep V9's stronger instinct here:

- golden-image regression for critical templates
- SSIM or comparable visual regression for renderer outputs
- accessibility tests
- export fidelity tests
- load-time and interaction-performance budgets

---

## 15. SaaS architecture

### 15.1 Backend strategy

Stay with the current repo stack:

- FastAPI API layer
- MongoDB document storage
- Redis for session metadata, pub/sub, and fast state support
- Celery for background generation and compile jobs
- Azure Blob for assets and build artifacts
- Chroma for template/layout retrieval memory

Do not force a new database architecture unless the existing stack proves insufficient in production.

### 15.2 Multi-tenant SaaS requirements

V10.3 should treat these as first-class, not optional:

- users
- organizations/workspaces
- decks
- brand packs
- shared templates
- editor permissions
- comments and suggestions
- audit trail / version history
- background job tracking

### 15.3 Share and collaboration model

Required collaboration modes:

- private draft
- team editable
- comment-only
- presentation link
- published HTML share

### 15.4 API surfaces

The backend should converge around four major API planes:

- generation APIs
- editor APIs
- sync APIs
- renderer/export APIs

This is already directionally present in the repo and should be clarified, not reinvented.

---

## 16. Performance budgets

V10.3 should commit to explicit budgets.

### Deck generation

- first outline placeholder for a 10-slide deck: under 2.5s target
- first editable slide draft: under 5s target
- full first-pass 10-slide draft: under 20s target in normal mode

### Editing

- drag/resize/select: 60fps target with 100 on-slide elements
- hot local preview update: under 50ms target
- thumbnail update after edit: under 500ms debounced target

### Collaboration

- presence updates: under 150ms target
- operation propagation across active collaborators: under 250ms median target

### Preview and sandbox

- reveal preview refresh from cached build: under 800ms target
- sandbox cold start: under 2s target
- sandbox hot update: under 400ms target

### Export

- PPTX export for 15 slides: under 10s target
- HTML standalone export: under 5s target

If a design choice breaks these budgets, the design choice is wrong.

---

## 17. The V10.3 moat

The moat is not "we use more agents." The moat is the combination of five things:

1. Better first draft quality than generic AI deck tools
2. Real editor precision after generation
3. Reliable PPTX/HTML export fidelity
4. Real-time collaborative workflow
5. Fast scoped refinement that preserves user edits

That is what makes the product strong as a standalone SaaS.

---

## 18. Roadmap

### Phase 0 - Stabilize current substrate (Weeks 1-3)

- audit existing editor routes, sync routes, and render bridges
- formalize current DSL adapters
- clean up session/store/revision boundaries
- define `DeckDocumentV10_3`

### Phase 1 - Slide Studio v1 (Weeks 4-8)

- React/Vite frontend app
- bounded slide studio with Konva
- selection, resize, snap, guides, layers, Tiptap text editing
- editor API integration with existing backend

### Phase 2 - Generation v1 (Weeks 9-13)

- planner/writer/designer/critic routing using available models only
- template retrieval corpus in Chroma
- progressive slide streaming into editor state
- partial regeneration and patch preservation

### Phase 3 - Workbench and collaboration (Weeks 14-18)

- storyboard/workbench surface
- comments, cursors, presence, simple collaboration permissions
- workbench-to-slide conversion flows
- version snapshots and compare/restore UX

### Phase 4 - Preview, sandbox, export (Weeks 19-22)

- reveal preview and present mode
- sandbox preview for interactive/code slides
- PPTX fidelity harness
- standalone HTML export

### Phase 5 - Brand, data, and quality hardening (Weeks 23-27)

- brand pack ingestion
- chart/table/diagram system v1
- deterministic quality engine
- regression and accessibility pipeline

### Phase 6 - Launch hardening (Weeks 28-30)

- performance passes
- billing/usage controls
- team workspace flows
- onboarding, templates, and polish

---

## 19. What V10.3 explicitly refuses to do

V10.3 is stronger because it says no to the wrong complexity.

It refuses to:

- pretend infinite-canvas editing should replace slide artboards
- turn the system into a 12-agent orchestration maze
- depend on unavailable models to make the architecture look advanced
- ship a weak export layer behind a flashy editor
- bet product quality on pure LLM taste alone
- use self-evolving or self-modifying agent claims as a core capability

---

## 20. Final statement

Premium Plan 10.3V should be the new master direction.

It is more ambitious than V10.1 where the product experience matters.
It is more realistic than V9 where engineering complexity matters.
It is more complete than V10.2 because it properly solves the workspace problem, not just the slide editor problem.

In practical terms, V10.3 defines the product as:

**a real-time AI deck workspace with a storyboard board, a Figma-grade slide studio, a Chronicle-level presentation target, a Dokie-style content-first refinement model, and a server4-grounded backend that can actually be built.**

That is the correct centralized plan.

---

## Appendix A - The V10.3 decisions in one table

| Category | V10.3 decision |
|---|---|
| slide editing surface | bounded 16:9 artboards |
| ideation surface | freeform storyboard/workbench |
| collaboration model | object/property operations with server authority |
| document state | hybrid deck document graph |
| layout engine | retrieval + constraints + scoring |
| generation topology | 4 roles + deterministic tool layers |
| model policy | available models only |
| preview strategy | canvas + reveal + sandbox tiers |
| render targets | PPTX, PDF, HTML, Reveal present mode |
| brand system | DTCG tokens + brand packs |
| data support | structured charts, tables, diagrams |
| storage | Mongo + Redis + Celery + Blob + Chroma |
| product differentiation | quality + editability + fidelity + speed |

## Appendix B - Naming

Suggested display name for product-facing docs:

- Meridian V10.3

Suggested file name retained for repo continuity:

- `Premium_plan_10.3V.md`