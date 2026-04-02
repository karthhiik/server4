# Brain MCP — Full Implementation Plan

> **Owner**: Founder
> **Status**: Foundation DONE → Brain MCP upgrades needed
> **Date**: 2026-04-01

---

## 1. What Exists Today (Foundation — DONE)

| Layer | Status | Files |
|-------|--------|-------|
| 6-tier LLM Router (Kimi→DeepSeek→GPT4o-mini→Mistral→Groq 8-key→CF 5-worker) | ✅ DONE | `services/llm/model_router.py`, `azure_client.py`, `groq_client.py`, `cloudflare_client.py` |
| Crash-proof State Machine | ✅ DONE | `services/orchestrator/state_machine.py` |
| WebSocket Progress | ✅ DONE | `services/orchestrator/progress_tracker.py`, `routers/websocket.py` |
| Full CRUD + Editing (undo/redo, layout reflow, AI actions) | ✅ DONE | `routers/presentations.py`, `routers/slides.py` |
| 8 Built-in Themes + 8 Templates | ✅ DONE | `main.py` seed data |
| Celery Export Workers | ✅ DONE | `celery_worker.py` |
| Docker + Compose | ✅ DONE | `Dockerfile`, `docker-compose.yml` |
| 7 Research Engines | ✅ DONE | `brain_mcp/engines/` (search, market, news, social, financial, scraper, academic) |
| 6 Generators | ✅ DONE | `brain_mcp/generators/` (outline, slide, batch, template_filler, chart, notes) |
| 3 Refiners | ✅ DONE | `brain_mcp/refiners/` (content_refiner, content_fitter, narrative_checker) |
| 7 System Prompts | ✅ DONE | `brain_mcp/prompts/` |
| Prompt Sanitizer | ✅ DONE | `brain_mcp/security/prompt_sanitizer.py` |
| Design MCP (5 engines) | ✅ DONE | `design_mcp/engines/` |
| Render MCP (6 builders) | ✅ DONE | `render_mcp/builders/` |

**Total: 86 Python files, all syntax-validated.**

---

## 2. What Needs to Be Built (Brain MCP Upgrades)

### 2A. Content Writing Styles System

**Problem**: Current `content_refiner.py` only has `rewrite`, `expand`, `summarize`, `translate`. No style selection. User has zero control over the *voice* of the content.

**Solution**: Add a `ContentStyle` enum and a `style_rewrite()` method. User picks a style, the prompt engine rewrites with that exact voice.

#### Content Styles (All)

| Style ID | Name | Description | Best For |
|----------|------|-------------|----------|
| `yc_pitch` | YC Pitch Style | Sequoia-memo meets YC Demo Day. Short sentences. Bold claims backed by data. "We do X for Y, resulting in Z." No fluff. | Investor decks, YC applications |
| `narrative` | Narrative / Story Arc | Hero's journey structure. "Imagine a world where..." → problem → resolution. Emotional hooks. | Keynotes, vision decks |
| `descriptive` | Descriptive / Visual | Paints a picture. Rich adjectives, concrete details. "Our platform processes 2.3M transactions through a distributed mesh of..." | Product demos, technical showcases |
| `persuasive` | Persuasive / CTA-Driven | Every slide builds toward an ask. Social proof, urgency, scarcity. "Companies that adopt X see 340% ROI in 6 months." | Sales decks, fundraising |
| `analytical` | Analytical / Data-First | Lead with numbers. Every claim has a source. Charts > words. "Market growing at 34% CAGR (McKinsey 2025)." | Quarterly reports, board decks |
| `conversational` | Conversational / Casual | Speaks like a human. Contractions. Short paragraphs. "Here's the thing — nobody likes filling out forms." | Internal decks, workshops |
| `executive` | Executive Summary | Top-line only. 3 bullets max per slide. Decision-oriented. "Option A: $2M, 6 months. Option B: $800K, 12 months." | C-suite, board meetings |
| `technical` | Technical / Engineering | Precise terminology. Architecture diagrams described. Code-level detail where relevant. | Engineering reviews, RFPs |
| `academic` | Academic / Research | Formal register. Citations. Methodology sections. "As demonstrated by Smith et al. (2024)..." | Research presentations, conferences |
| `minimalist` | Minimalist / Zen | One idea per slide. Maximum 6 words in a title. Let whitespace do the work. | Design-forward decks, keynotes |
| `storytelling` | Customer Storytelling | Real or composite customer narratives. "Meet Sarah, a PM at a Series B startup..." | Case studies, customer success |
| `investor_update` | Investor Update | Monthly/quarterly update voice. Transparent about challenges. "Burn rate: $180K/mo. Runway: 14 months." | Post-investment updates |

#### Files to Create/Modify

| File | Action | What |
|------|--------|------|
| `brain_mcp/prompts/style_system.py` | **CREATE** | 12 style-specific system prompts. Each ~200 words of precise writing instructions + example output format. |
| `brain_mcp/refiners/content_refiner.py` | **MODIFY** | Add `style_rewrite(content, style_id, presentation_id)` method. Add `ContentStyle` enum import. |
| `models/slide.py` | **MODIFY** | Add `writing_style: Optional[str]` to `AISlideAction` model. |
| `routers/slides.py` | **MODIFY** | Add `POST /slides/{id}/style-rewrite` endpoint. |
| `models/presentation.py` | **MODIFY** | Add `writing_style: str = "yc_pitch"` to `GenerationInput` so the full pipeline uses the style from the start. |
| `brain_mcp/generators/slide_generator.py` | **MODIFY** | Accept `writing_style` parameter, prepend style instructions to the prompt. |
| `brain_mcp/generators/outline_generator.py` | **MODIFY** | Accept `writing_style`, adjust outline structure per style (e.g., minimalist = fewer slides, analytical = more chart slides). |

---

### 2B. YC-Style & Investor-Friendly Templates

**Problem**: Current templates are generic. No YC Demo Day format. No Sequoia-style memo deck. No investor-update template. The `investor-pitch` template exists but uses generic placeholders.

**Solution**: Add 4 new templates and rewrite the `investor-pitch` template to match real YC/Sequoia standards.

#### New Templates

| Template ID | Name | Slides | Source Pattern |
|-------------|------|--------|---------------|
| `yc-demo-day` | YC Demo Day (2-Minute) | 8 | Real YC Demo Day structure: Logo → One-liner → Problem (with data) → Solution (demo screenshot) → Traction (graph going up-right) → Business Model → Market Size → Team → The Ask |
| `sequoia-pitch` | Sequoia Capital Format | 12 | Don Valentine's framework: Company Purpose → Problem → Solution → Why Now → Market Size → Competition → Product → Business Model → Team → Financials → The Ask → Vision |
| `investor-update` | Monthly Investor Update | 10 | Standard VC update format: Highlights → KPIs (MRR, burn, runway) → Wins → Challenges → Product → Pipeline → Hiring → Cash Position → Asks → Next Month Goals |
| `series-a-deck` | Series A Deck | 14 | Post-seed format: Vision → Problem (validated) → Solution (with product) → Traction (18mo chart) → Unit Economics → Go-to-Market → Competition (matrix) → Team → Financials (3yr projection) → Use of Funds → Milestones → Appendix |

#### Rewrite Existing `investor-pitch`

The current `investor-pitch` template uses weak placeholders like `{{problem_description}}` and generic AI instructions like "Research real statistics about this problem".

**Rewrite** with:
- YC-grade AI instructions that force data-backed claims
- Specific research queries embedded in `ai_instructions` (e.g., "Search for TAM/SAM/SOM using industry reports from 2024-2026. Use top-down and bottom-up sizing. Include source names.")
- Layout choices that match what top VCs expect (traction = chart going up-right, not KPI cards)
- Forced narrative arc per YC's own guidance: "Don't pitch a product. Pitch a trajectory."

#### Files to Create/Modify

| File | Action | What |
|------|--------|------|
| `main.py` | **MODIFY** | Add 4 new templates to `_seed_templates()`. Rewrite `investor-pitch` template. |
| `brain_mcp/prompts/investor_system.py` | **CREATE** | Investor-specific prompt set: `YC_PITCH_SYSTEM`, `SEQUOIA_SYSTEM`, `INVESTOR_UPDATE_SYSTEM`, `TRACTION_SLIDE_SYSTEM`, `MARKET_SIZING_SYSTEM`, `UNIT_ECONOMICS_SYSTEM`. These are the enriched prompts that make content investor-grade. |

---

### 2C. Enriched Prompt Engine

**Problem**: Current prompts are functional but generic. `OUTLINE_SYSTEM_PROMPT` says "create a compelling outline" but doesn't encode real pitch deck expertise. `slide_system.py` layout prompts just say "Generate content for a BULLETS slide" — no domain knowledge about *what makes a pitch deck slide work*.

**Solution**: Build a **Prompt Composition Engine** that layers: `Base Style` + `Layout Instructions` + `Domain Expertise` + `Research Context` + `Quality Guards`.

#### Prompt Engine Architecture

```
┌───────────────────────────────────────┐
│           PromptEngine                │
│                                       │
│  compose(task, layout, style,         │
│          context, constraints) → str  │
│                                       │
│  Layers:                              │
│  1. STYLE_LAYER    → writing voice    │
│  2. DOMAIN_LAYER   → pitch deck rules │
│  3. LAYOUT_LAYER   → format spec      │
│  4. CONTEXT_LAYER  → research data    │
│  5. QUALITY_LAYER  → guards/checks    │
│  6. OUTPUT_LAYER   → JSON schema      │
└───────────────────────────────────────┘
```

**Why composition, not monolithic prompts**: A single 2000-word system prompt wastes tokens and fights itself. The engine composes only the relevant layers for each call. A `yc_pitch` style outline needs `YC_DOMAIN + OUTLINE_FORMAT + QUALITY_GUARDS`. A `translate` call needs `TRANSLATE_RULES + OUTPUT_JSON` — no domain layer needed.

#### Domain Expertise Layers (New)

These are the layers that make prompts investor-grade:

| Layer | Content |
|-------|---------|
| `PITCH_DECK_RULES` | "Rule of 10/20/30: 10 slides, 20 minutes, 30pt font minimum. Every slide answers ONE question. Traction slides must show growth trajectory, not point-in-time metrics. Market sizing must use TAM→SAM→SOM funnel with clear logic for each step." |
| `YC_PRINCIPLES` | "YC's core advice: Talk to users, build product, grow revenue. Pitch the trajectory, not the product. Show you understand your market intimately. Founders > idea. The best pitch decks tell the story of an inevitability." |
| `INVESTOR_PSYCHOLOGY` | "VCs read 1000 decks/year. They decide in 3 slides whether to keep reading. Slide 1: What do you do? (must be crystal clear in <10 words). Slide 2: Why does this matter? (market pull, not push). Slide 3: Proof it's working (traction). If these 3 fail, the deck fails." |
| `DATA_PRESENTATION_RULES` | "Never say 'large market' — say '$380B by 2028 (Grand View Research)'. Never say 'fast growing' — say '34% CAGR 2024-2028'. Round numbers to human-readable: $2.3M not $2,341,872. Growth charts: always show the inflection point." |
| `COMMON_MISTAKES` | "Do NOT: Use jargon the audience doesn't know. Put 8 bullets on a slide. Use pie charts for more than 5 categories. Show revenue projections without assumptions. Have a 'Competition' slide that says 'No direct competitors'. Use the word 'disrupt' unironically." |

#### Quality Guard System

Every generated slide passes through quality checks before returning:

```
┌─────────────────────────────────────────────┐
│           Quality Guard Pipeline            │
│                                             │
│  1. claim_has_source_check()                │
│     - Any number > $1M must have a source   │
│     - "According to X" or "(Source, Year)"  │
│                                             │
│  2. slide_density_check()                   │
│     - Title: 3-8 words                      │
│     - Bullets: max 6, each max 15 words     │
│     - No wall-of-text body                  │
│                                             │
│  3. investor_readiness_check()              │
│     - Does traction slide show trajectory?  │
│     - Does market slide have TAM/SAM/SOM?   │
│     - Does ask slide have use-of-funds?     │
│                                             │
│  4. fluff_detector()                        │
│     - Flags: "cutting-edge", "best-in-class",│
│       "revolutionary", "synergy", "holistic"│
│     - Auto-rewrites to concrete language    │
│                                             │
│  5. consistency_check()                     │
│     - Same company name across all slides   │
│     - Numbers don't contradict each other   │
│     - Tense consistency                     │
└─────────────────────────────────────────────┘
```

#### Files to Create/Modify

| File | Action | What |
|------|--------|------|
| `brain_mcp/prompts/prompt_engine.py` | **CREATE** | `PromptEngine` class with `compose()` method. Layer registry. Auto-selects layers by task+style. |
| `brain_mcp/prompts/domain_layers.py` | **CREATE** | All domain expertise layers: `PITCH_DECK_RULES`, `YC_PRINCIPLES`, `INVESTOR_PSYCHOLOGY`, `DATA_PRESENTATION_RULES`, `COMMON_MISTAKES`. |
| `brain_mcp/prompts/quality_guards.py` | **CREATE** | Quality check functions: `claim_has_source_check()`, `slide_density_check()`, `investor_readiness_check()`, `fluff_detector()`, `consistency_check()`. |
| `brain_mcp/prompts/style_system.py` | **CREATE** | All 12 style prompts (from section 2A). |
| `brain_mcp/prompts/investor_system.py` | **CREATE** | Investor-specific prompts (from section 2B). |
| `brain_mcp/generators/outline_generator.py` | **MODIFY** | Use `PromptEngine.compose()` instead of raw `OUTLINE_SYSTEM_PROMPT`. |
| `brain_mcp/generators/slide_generator.py` | **MODIFY** | Use `PromptEngine.compose()` instead of raw `get_slide_prompt()`. |
| `brain_mcp/generators/chart_generator.py` | **MODIFY** | Use domain layer for data presentation rules. |
| `brain_mcp/refiners/content_refiner.py` | **MODIFY** | Add `style_rewrite()`. Use quality guards on output. |

---

## 3. Implementation Order

### Phase 1: Prompt Engine + Domain Layers (do first — everything depends on it)

```
1. brain_mcp/prompts/style_system.py          — 12 writing style prompts
2. brain_mcp/prompts/domain_layers.py          — pitch deck expertise layers
3. brain_mcp/prompts/investor_system.py        — investor-specific prompts
4. brain_mcp/prompts/prompt_engine.py          — PromptEngine compositor class
5. brain_mcp/prompts/quality_guards.py         — quality check pipeline
```

### Phase 2: Wire Prompt Engine into Generators

```
6. brain_mcp/generators/outline_generator.py   — use PromptEngine
7. brain_mcp/generators/slide_generator.py     — use PromptEngine + style
8. brain_mcp/generators/chart_generator.py     — use domain layers
9. brain_mcp/generators/notes_generator.py     — style-aware notes
```

### Phase 3: Content Styles in Refiner + API

```
10. brain_mcp/refiners/content_refiner.py      — add style_rewrite()
11. models/slide.py                            — add writing_style to AISlideAction
12. models/presentation.py                     — add writing_style to GenerationInput
13. routers/slides.py                          — add POST /slides/{id}/style-rewrite
```

### Phase 4: YC/Investor Templates

```
14. main.py                                    — add 4 new templates, rewrite investor-pitch
```

---

## 4. File Manifest (Complete)

### NEW Files (5)

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `brain_mcp/prompts/style_system.py` | ~400 | 12 content writing style prompts |
| `brain_mcp/prompts/domain_layers.py` | ~300 | Pitch deck, YC, investor expertise |
| `brain_mcp/prompts/investor_system.py` | ~350 | Investor-deck-specific prompts |
| `brain_mcp/prompts/prompt_engine.py` | ~200 | PromptEngine compositor class |
| `brain_mcp/prompts/quality_guards.py` | ~250 | Quality check functions |

### MODIFIED Files (8)

| File | Changes |
|------|---------|
| `brain_mcp/generators/outline_generator.py` | Use PromptEngine, accept `writing_style` param |
| `brain_mcp/generators/slide_generator.py` | Use PromptEngine, accept `writing_style` param |
| `brain_mcp/generators/chart_generator.py` | Use domain layer for data rules |
| `brain_mcp/generators/notes_generator.py` | Style-aware notes generation |
| `brain_mcp/refiners/content_refiner.py` | Add `style_rewrite()` with ContentStyle enum |
| `models/slide.py` | Add `writing_style` to `AISlideAction` |
| `models/presentation.py` | Add `writing_style` to `GenerationInput` |
| `routers/slides.py` | Add `POST /slides/{id}/style-rewrite` endpoint |
| `main.py` | Add 4 new templates, rewrite investor-pitch |

**Total: 5 new files + 9 modified files = 14 file touches.**

---

## 5. What This Does NOT Cover (Out of Scope)

- Frontend changes (separate task)
- Image generation via Flux (Render MCP scope)
- PDF/PPTX builder changes (Render MCP scope)
- Database schema changes (none needed — current schema supports all of this)
- New LLM providers (current 6-tier routing is sufficient)
