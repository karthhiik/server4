# Phase 0 Implementation Plan - Executive Summary

**Project**: Barise Strategic Intelligence Services Remodel
**Document**: 2026-04-02 Implementation Plan
**Current Status**: 62% Complete (8/13 components)
**Remaining Effort**: ~2,200 lines across 12 files

---

## 🎯 WHAT IS PHASE 0?

Phase 0 is the **foundation layer** for all Business Intelligence modules. It builds every shared component before touching any individual canvas (Business Plan, GTM, SWOT, Pitch).

**Key principle**: Nothing ships to users yet, but everything after depends on this.

---

## ✅ WHAT'S BEEN BUILT (62% Complete)

### Frontend Shared Components (8 components completed)

```
lliveupdatedstreaming/src/features/intelligence/shared/
├── CanvasThemeProvider.tsx         ✅ [1.4 KB]  - Theme system with 4 presets
├── ConfidenceBadge.tsx              ✅ [3.5 KB]  - 6 levels, 3 sizes
├── MetricCard.tsx                   ✅ [5.9 KB]  - 4 variants (number/gauge/sparkline/progress)
├── EvidenceDrawer.tsx               ✅ [13.1 KB] - Sources + Visuals tabs
├── SectionEditor.tsx                ✅ [17 KB]   - Read/edit modes, "/" commands
├── VersionHistoryDrawer.tsx         ✅ [9.7 KB]  - Timeline, compare, restore
├── ExportToolbar.tsx                ✅ [9.1 KB]  - PDF/DOCX/Markdown/PNG/TOON
└── types/                           ✅ [~30 KB]  - Full TS interfaces
    ├── canvas.ts
    ├── evidence.ts
    ├── metrics.ts
    ├── enrichment.ts
    └── index.ts
```

**Total implemented**: ~92 KB (~2,200 lines)

---

## ❌ WHAT'S REMAINING (38% Complete)

### Frontend (3 component groups = ~1,450 lines)

```
1. ReactFlowWrapper + 4 Node Types              [~500 lines]
   - Pre-configured ReactFlow (dark bg, grid, MiniMap, Controls)
   - StrategyNode, MetricNode, EvidenceNode, GroupNode
   - IntersectionObserver guard for Three.js
   - [NO dependencies - can start today]

2. WebSearchContext + Entity/Enrichment         [~350 lines]
   - Entity detection & enrichment state manager
   - EntityChip component (detected→searching→enriched)
   - EnrichmentCard showing company data, funding, competitors
   - [DEPENDS ON: Backend endpoints (Step 0.11)]

3. DualModeInput Shell (CRITICAL)               [~600 lines]
   - Page layout with hero + prompt box + form
   - StrategyPromptInput with Fast/Deep modes
   - StructuredFormAccordion for dynamic forms
   - [DEPENDS ON: Step 0.9, integrates everything]
```

### Backend (2 service groups = ~750 lines)

```
1. Intelligence Enrichment Endpoints            [~600 lines]
   POST /api/intelligence/detect-entities       [NER extraction]
   POST /api/intelligence/web-enrich            [SerpAPI + scraping]
   POST /api/intelligence/extract-form-fields   [Schema extraction]
   POST /api/intelligence/competitor-snapshot   [Deep analysis]

   - All require @token_required auth
   - Redis caching (5-30 min)
   - Rate limiting (5-10 ops/min per user)
   - [NO dependencies - can start today]

2. Prompt Enhancement Middleware                [~500 lines]
   - PromptEnhancer: raw → enhanced prompt
   - OutputValidator: AI output quality gates
   - Per-service schemas (Business Plan, GTM, SWOT, Pitch)
   - "No Fluff" mandate injection
   - [NO dependencies - can start today]
```

---

## 🎨 DEPENDENCY GRAPH

```
COMPLETED (Start here)
├── CanvasThemeProvider ✅
├── ConfidenceBadge ✅
├── MetricCard ✅
├── EvidenceDrawer ✅
├── SectionEditor ✅
├── VersionHistoryDrawer ✅
├── ExportToolbar ✅
└── Types ✅
    (All independent - foundation stable)

READY TO START (No blockers)
├── Step 0.8: ReactFlowWrapper
│   ├── No dependencies
│   └── Feeds into: Phase 1-4 views
│
├── Step 0.11: Enrichment Endpoints
│   ├── No dependencies
│   └── Feeds into: Step 0.9, 0.10
│
└── Step 0.12: Prompt Enhancement
    ├── No dependencies
    └── Feeds into: Phase 1-4 services

BLOCKING CHAINS
├── Step 0.9: WebSearchContext + Entity/Enrichment
│   ├── DEPENDS ON: Step 0.11 (enrichment endpoints)
│   └── Feeds into: Step 0.10
│
└── Step 0.10: DualModeInput Shell [CRITICAL]
    ├── DEPENDS ON: Step 0.8, 0.9
    └── UNBLOCKS: All Phase 1-4 input pages
```

---

## 📋 STEP-BY-STEP COMPLETION ORDER

### Parallel Track A: ReactFlowWrapper (No blockers)
```
Step 0.8: ReactFlowWrapper + 4 node types     (~500 lines)
├── Time to implement: 2-3 hours
├── Frontend only (no backend)
├── Skill: React + ReactFlow + Framer Motion
└── Output: Reusable visualization foundation
```

### Parallel Track B: Backend Enrichment & Validation
```
Step 0.11: Enrichment Endpoints               (~600 lines)
├── Time to implement: 3-4 hours
├── Services: entity_detector, web_enricher, competitor_analyzer
├── Endpoints: 4 REST routes with caching + rate limiting
├── Skills: FastAPI, SerpAPI integration, Azure OpenAI, Redis
└── Output: Powers entity detection UI

Step 0.12: Prompt Enhancement Middleware      (~500 lines)
├── Time to implement: 2-3 hours
├── Services: prompt_enhancer, output_validator
├── Integrations: Per-service schemas
├── Skills: Pydantic, prompt engineering, validation logic
└── Output: Quality gates for all AI outputs
```

### Serial: Enrichment UI (After Step 0.11 endpoints done)
```
Step 0.9: Entity Detection UI                 (~350 lines)
├── Time to implement: 2 hours (after 0.11)
├── Components: WebSearchContext, EntityChip, EnrichmentCard
├── Integrations: API calls to Step 0.11 endpoints
└── Output: Entity enrichment system in input pages
```

### Final: Input Page Shell (After Step 0.8, 0.9)
```
Step 0.10: DualModeInput Shell [CRITICAL]    (~600 lines)
├── Time to implement: 3-4 hours
├── Components: DualModeInput, StrategyPromptInput, StructuredFormAccordion
├── Integrations: All previous Phase 0 work
├── Features: Fast/Deep modes, form generation, entity chips
└── Output: UNBLOCKS all Phase 1-4 entry pages
```

---

## 📊 IMPLEMENTATION ESTIMATES

| Component | Type | Lines | Hours | Skills | Status |
|-----------|------|-------|-------|--------|--------|
| 0.8 ReactFlow | FE | 500 | 2-3h | React, D3-style, Animations | ❌ Todo |
| 0.9 Enrichment UI | FE | 350 | 2h | React, Context, Animations | ❌ Todo |
| 0.10 DualModeInput | FE | 600 | 3-4h | React, Forms, Theming | ❌ Todo |
| **Frontend subtotal** | | **1,450** | **7-9h** | | |
| 0.11 Endpoints | BE | 600 | 3-4h | FastAPI, SerpAPI, Redis | ❌ Todo |
| 0.12 Validation | BE | 500 | 2-3h | Pydantic, Validation | ❌ Todo |
| **Backend subtotal** | | **1,100** | **5-7h** | | |
| **PHASE 0 TOTAL** | | **2,550** | **12-16h** | | |

---

## 🧩 WHAT UNLOCKS AFTER PHASE 0

Once Phase 0 is complete:

### Phase 1: Business Plan Canvas (Flagship)
- BusinessPlanInput page (uses DualModeInput)
- BusinessPlanCanvas with 7 views
- Strategy Map (uses ReactFlowWrapper)
- Metrics Dashboard (uses MetricCard)
- Full Report view
- Version History view
- Edit Mode view

### Phase 2: GTM Strategy Canvas
- GTMStrategyInput page
- War Room bento grid
- Launch Map (uses ReactFlowWrapper)
- Interactive funnel with what-if sliders
- KPI Dashboard

### Phase 3: SWOT Analysis Canvas
- SWOTAnalysisInput page
- Quadrant Matrix (2x2 grid)
- TOWS Actions graph (uses ReactFlowWrapper)
- Risk Radar
- Deep dive sub-analyses

### Phase 4: Pitch Deck Canvas
- PitchAnalysisInput page
- Score card with readiness gauge
- Slide-by-slide analysis
- Objection board (Kanban)
- Evidence-based fact checking

---

## ⚠️ CRITICAL DEPENDENCIES

**DualModeInput (Step 0.10) is the gating item for all Phase 1-4.**

Without it, none of the input pages can be built. All three Phase 1-4 canvases depend on this shell:
- Business Plan Input page
- GTM Strategy Input page
- SWOT Analysis Input page
- Pitch Analysis Input page

**Recommendation**: Treat Step 0.10 as CRITICAL PATH after its dependencies (0.8, 0.9) are done.

---

## 🚀 RECOMMENDED START (Today)

### If you want to parallelize maximum progress:

**Developer 1: Frontend - ReactFlow Foundation**
```
→ Step 0.8: ReactFlowWrapper + 4 nodes (~2-3 hours)
  - Core visualization library for Strategy Maps
  - No backend dependencies
  - Can be tested with mock data
```

**Developer 2: Backend - Enrichment APIs**
```
→ Step 0.11: Enrichment endpoints (~3-4 hours)
  - detect-entities, web-enrich, extract-form-fields, competitor-snapshot
  - Sets up entity detection system
  - Feeds into Step 0.9
```

**Developer 3: Backend - Validation Layer**
```
→ Step 0.12: Prompt enhancement + output validation (~2-3 hours)
  - PromptEnhancer + OutputValidator services
  - Per-service quality schemas
  - Foundation for Phase 1-4 AI output quality
```

**After Step 0.11 completes** →
```
Step 0.9: WebSearchContext + Entity UI (~2 hours)
→ (Depends on Step 0.11 endpoints being live)
```

**After Step 0.8 & 0.9 complete** →
```
Step 0.10: DualModeInput Shell (~3-4 hours)
→ IMMEDIATELY UNBLOCKS all Phase 1 work
```

---

## ✨ PHASE 0 COMPLETION CHECKLIST

**When you're done with Phase 0, verify:**

- [ ] All 7 TypeScript components compile without errors
- [ ] All type definitions match actual component props
- [ ] ConfidenceBadge renders all 6 levels with correct icons
- [ ] MetricCard works in all 4 variants
- [ ] EvidenceDrawer opens/closes cleanly, search filters work
- [ ] SectionEditor "/" commands functional (at least /rewrite, /expand)
- [ ] ExportToolbar exports to PDF without losing charts
- [ ] VersionHistoryDrawer compare mode shows diffs correctly
- [ ] CanvasThemeProvider applies all 4 color configs
- [ ] ReactFlowWrapper renders 30+ nodes smoothly
- [ ] WebSearchContext detects entities correctly
- [ ] Entity enrichment shows real company data from SerpAPI
- [ ] DualModeInput form generates correctly from schema
- [ ] All 4 backend enrichment endpoints return correct shapes
- [ ] Rate limiting blocks requests > 10/min (detect) or > 5/min (enrich)
- [ ] Prompt enhancer injects "No Fluff" correctly
- [ ] Output validator catches missing citations
- [ ] No circular import dependencies in TypeScript
- [ ] Backend authentication middleware validates all endpoints

---

## 📞 Questions Before You Start?

1. **Team allocation**: Do you want 1 person doing everything sequentially, or 3 in parallel?
2. **Priority**: Is DualModeInput (Step 0.10) the gating item for your timeline?
3. **Testing**: Should I add unit tests as each component is completed, or after Phase 0 is 100%?
