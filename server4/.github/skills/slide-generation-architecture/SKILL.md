---
name: slide-generation-architecture
description: "Design and build the core slide generation pipeline — from user query to structured slide data. Use when: architecting the generation pipeline, designing the slide DSL or document model, building layout intent engines, implementing query-to-slide transformation, designing skeleton-of-thought generation, working on template-to-freedom migration, or building the multi-stage content-to-slide pipeline."
---

# Slide Generation Architecture

## Purpose
This skill covers the entire pipeline that transforms a user's raw query into a fully structured, design-ready presentation. This is the hardest problem in the product — the generation intelligence is the competitive moat.

## The Generation Problem

The fundamental challenge: a user types "Series A pitch deck for an AI-powered hiring platform with $2M ARR" and expects a complete, professional, investor-grade 12-15 slide deck in under 30 seconds.

This requires solving:
1. **Query Understanding** — What type of presentation? What audience? What tone? What content depth?
2. **Narrative Planning** — What story arc? What slides in what order? What's the throughline?
3. **Content Generation** — What goes on each slide? Headlines, body text, data points, talking points
4. **Layout Assignment** — What layout pattern best serves each slide's content? (NOT picking a template first)
5. **Element Composition** — How are text blocks, images, charts, icons arranged within the layout?
6. **Design Treatment** — Colors, typography, spacing, backgrounds, visual hierarchy
7. **Deck Coherence** — Does the full deck tell a unified story with consistent design?

## Pipeline Architecture — The Four-Role Model

### Role 1: Strategist (Query → Deck Blueprint)
- Analyze the user query for intent, audience, domain, and tone
- Determine presentation type (pitch deck, product demo, quarterly review, educational, etc.)
- Generate a **Deck Blueprint**: ordered list of slide intents with narrative purpose
- Each slide intent specifies: purpose, key message, content requirements, suggested evidence type
- The Strategist thinks about the STORY, not the slides

**Critical Principle**: The Strategist never thinks about layouts or design. It thinks purely about communication strategy and narrative flow.

### Role 2: Researcher (Blueprint → Enriched Content)
- Takes each slide intent from the Blueprint
- Generates or retrieves relevant content: statistics, market data, competitor mentions, financial projections
- For pitch decks: pulls from known patterns (problem-solution-traction-team-ask framework)
- Enriches content with evidence markers (data points, quotes, case studies)
- Outputs structured content blocks per slide, not formatted text

**Critical Principle**: Research produces raw content materials. It doesn't decide how content is displayed — that's the Composer's job.

### Role 3: Composer (Content → Slide Structure)
- Takes enriched content blocks and assigns layout patterns
- **Content-driven layout selection**: The content determines the layout, NEVER the reverse
- Layout intent categories: hero statement, comparison, data showcase, team grid, timeline, feature list, quote highlight, image-dominant, split (text+visual), full bleed
- Composes elements within each layout: text hierarchy (H1/H2/body/caption), image placeholders, chart specifications, icon usage
- Outputs structured slide data in the DSL format

**Critical Principle**: The Composer respects content density. A slide with one big number gets a hero layout. A slide with 4 team members gets a grid. This is not random — it's design intelligence.

### Role 4: Critic (Structure → Quality Score)
- Reviews the complete deck for coherence, design consistency, content quality
- Checks: narrative flow, visual rhythm (alternating layouts), content density balance, design system consistency
- Flags issues: duplicate layouts in sequence, orphan slides, missing narrative connections, text overflow risks
- Returns a quality score and specific fix instructions
- If score < threshold, triggers targeted regeneration of flagged slides only

**Critical Principle**: The Critic prevents the "AI slop" problem — where generated decks feel repetitive and mechanical. It enforces variety and intentionality.

## The Document Model (DSL)

The slide DSL is the contract between generation, editing, and rendering. It must be:
- **Serializable** — JSON-friendly for storage and WebSocket sync
- **Renderable** — Maps cleanly to Reveal.js, PPTX, and HTML output
- **Editable** — Every property can be modified in the sandbox editor
- **Composable** — Elements combine predictably within layouts

### Core Structure
```
Deck
├── metadata (title, author, theme_id, created_at, version)
├── theme (design tokens: colors, fonts, spacing, backgrounds)
├── slides[] (ordered)
│   ├── slide_intent (purpose, narrative_role)
│   ├── layout_type (hero, comparison, grid, timeline, etc.)
│   ├── elements[] (ordered by z-index)
│   │   ├── type (text, image, chart, shape, icon, video)
│   │   ├── position (x, y, width, height — inch-based for PPTX fidelity)
│   │   ├── style (per-element overrides)
│   │   └── content (type-specific data)
│   ├── speaker_notes
│   └── transition
└── design_system (global tokens, reusable styles)
```

### Key Design Decisions
- **Inch-based positioning**: All element positions use inches (not pixels) — this ensures PPTX export fidelity since PowerPoint uses inches natively
- **Layout as intent, not template**: A layout_type is a semantic hint ("this slide wants a comparison layout"), not a rigid template. The Composer interprets it.
- **Elements are flat**: No nested groups in v1. Each element is independently positioned. Grouping comes later.
- **Theme tokens cascade**: Global theme → slide-level overrides → element-level overrides

## Layout Intent Engine

Instead of a fixed template library, the Layout Intent Engine dynamically assigns layouts based on content analysis:

### Input Signals
- Number and type of content blocks (text count, image count, data points)
- Content hierarchy (one headline vs. headline + subhead + body)
- Slide intent from the Strategist (is this a "wow" moment or an "evidence" slide?)
- Previous slide's layout (avoid repeating the same layout pattern)
- Deck position (opening slides favor bold layouts, middle slides favor information density)

### Layout Categories
| Category | When to Use | Content Pattern |
|----------|-------------|-----------------|
| Hero Statement | Big claim, opening/closing | 1 headline, optional subtitle |
| Split Content | Explanation + visual | Text block + image/chart |
| Data Showcase | Metrics, financials | 2-4 key numbers + context |
| Comparison | Before/after, vs. | 2-3 parallel columns |
| Feature Grid | Product features, team | 3-6 equal items |
| Timeline | History, roadmap | 3-7 sequential events |
| Quote/Testimonial | Social proof | Large quote + attribution |
| Image Dominant | Product shots, demos | Full/large image + minimal text |
| Full Bleed | Atmosphere, transitions | Background image + overlay text |
| List/Steps | Process, how-it-works | Ordered items with icons |

### Anti-Pattern Prevention
- Never place two identical layouts adjacent to each other
- Never use more than 3 text-heavy layouts in sequence (insert a visual break)
- Never assign a grid layout to a slide with only 1-2 items
- Never assign a hero layout to a slide with dense content

## Skeleton-of-Thought Generation

For speed (sub-30s generation), use Skeleton-of-Thought:
1. **Phase 1 (fast, ~3s)**: Generate the full deck skeleton — all slide intents, layout types, and headline text. User sees the deck structure immediately.
2. **Phase 2 (parallel, ~10s)**: Flesh out each slide's content in parallel. Body text, data points, speaker notes stream in.
3. **Phase 3 (parallel, ~10s)**: Generate visual assets — image prompts, chart data, icon selections. These fill in as they arrive.
4. **Phase 4 (quick, ~3s)**: Critic pass — check coherence, flag issues, apply fixes.

The user sees progressive rendering: skeleton → content → visuals → polish. This feels fast even if total generation time is 25s.

## Procedure When Working on Generation

1. **Read existing generation code** in `app/services/` and `app/mcp/` — understand current pipelines
2. **Check available models** in the codebase — only use models that are actually configured
3. **Review the slide DSL** — understand the current data model before proposing changes
4. **Map to the Four-Role pipeline** — identify which role each existing function serves
5. **Identify gaps** — what's missing between current state and the target pipeline?
6. **Build incrementally** — implement one role at a time, test end-to-end after each
7. **Measure generation time** — enforce the <30s budget at every stage

## References
- Current generation code: `app/services/` (check for slide generation modules)
- Current DSL: `app/models/` (check for presentation/slide data models)
- MCP tools: `app/mcp/` (check for generation-related MCP tools)
- Editor routes: `app/api/routes/editor_routes.py` (the consumption point for generated data)
