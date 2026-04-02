# Phase 0 Complete Implementation Plan

> **Status:** Ready for subagent-driven-development execution
> **Production-Critical Project** - Zero shortcuts, full test coverage, careful review

**Goal:** Implement all 5 remaining Phase 0 components (2,550 lines) with production-grade code, tests, and integration.

**Tech Stack:** React 18, TypeScript 5, FastAPI, Pydantic, Redis, Azure OpenAI, SerpAPI

---

## 7-Task Breakdown

### Task 1: ReactFlowWrapper + 4 Node Types (~500 lines, 2-3h)
**What:** Visualization foundation with dark theme, grid, MiniMap, Controls
**Creates:** ReactFlowWrapper.tsx + 4 node components
**Unblocks:** Strategy Map, Launch Map, TOWS Actions views

### Task 2: WebSearchContext + EntityChip + EnrichmentCard (~350 lines, 2h)
**What:** Entity enrichment system with state management and animated UI
**Creates:** WebSearchContext.tsx + EntityChip.tsx + EnrichmentCard.tsx
**Unblocks:** DualModeInput (uses entity chips in prompt)

### Task 3: DualModeInput Shell (CRITICAL - ~600 lines, 3-4h)
**What:** Universal entry point for all canvas input pages
**Creates:** DualModeInput.tsx + StrategyPromptInput.tsx + StructuredFormAccordion.tsx
**Unblocks:** All Phase 1-4 input pages immediately

### Task 4: Backend Enrichment Endpoints (~600 lines, 3-4h)
**What:** 4 REST APIs with caching, rate limiting, auth validation
**Creates:** Routes + 3 service modules
**Endpoints:** detect-entities, web-enrich, extract-form-fields, competitor-snapshot

### Task 5: Prompt Enhancement & Output Validation (~500 lines, 2-3h)
**What:** Quality gates for AI output with "No Fluff" mandate
**Creates:** PromptEnhancer.py + OutputValidator.py
**Unblocks:** Phase 1-4 quality baseline

### Task 6: Integration Tests (~300 lines, 2h)
**What:** End-to-end tests covering all workflows
**Creates:** test_phase0_e2e.py

### Task 7: Final Verification (~1h)
**What:** Compilation, syntax, tests, code quality review
**Final Step:** Merge to main, ready for Phase 1

---

## Key Production Requirements

- ✅ Complete production code (no TBD, no placeholders)
- ✅ Full unit + integration tests (>90% coverage)
- ✅ Real error handling with logging
- ✅ Redis caching with msgpack compression
- ✅ Lua-based rate limiting (5-10/min)
- ✅ Auth middleware validation (@token_required)
- ✅ Type-safe (TypeScript + Pydantic)
- ✅ Frequent git commits after each task
- ✅ Careful code review between tasks
