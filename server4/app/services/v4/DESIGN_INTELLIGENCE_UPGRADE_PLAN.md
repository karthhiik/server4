# Design Intelligence Upgrade — Implementation Plan

## Current State (Audit)
- 5 visual directions (minimal_dark, swiss_editorial, warm_narrative, bold_contrast, light_professional)
- 29 kit components with basic styling
- Rule-based layout scoring with 30+ layout specs
- CSS token system with palette/fonts/spacing/weights
- Basic critic with anti-slop rules
- No design memory, no AI composition scoring, no image treatment pipeline

## Phase 1: Enhanced Design Token System (shape, animation, grid, advanced typography)
- **Files**: `design_resolver.py`, `design_system.py`, `tokens.ts`
- Add shape tokens (radius, shadows, borders, blur), animation tokens (easing, durations, stagger), grid tokens (columns, gutter, baseline), advanced typography (line-height scale, optical sizes, tracking)
- Add 10 new premium visual directions (cinematic_dark, luxury_gold, neon_futurism, pastel_soft, earth_organic, midnight_navy, coral_energy, sage_calm, berry_creative, obsidian_tech)

## Phase 2: Premium Kit Components
- **Files**: `sandbox/src/kit/*.tsx`
- Add: `CinematicHero`, `EditorialImage`, `GlassCard`, `DuotoneHero`, `MagazineLayout`, `DataVizBlock`, `AsymmetricGrid`, `MosaicGallery`, `SplitOverlap`, `FloatingStat`
- Upgrade existing kits with image masking, gradient overlays, glassmorphism, kinetic typography

## Phase 3: Layout Intelligence Engine v2
- **Files**: `layout/intent_engine.py`, `layout/scoring.py`
- AI-driven composition scoring (golden ratio alignment, visual weight balance, whitespace ratio)
- Grid-aware layout selection (12-column system, asymmetric grids, editorial grids)
- Content-density adaptive scoring

## Phase 4: Visual Composition + Grid System
- **Files**: `composition_engine.py`, `grid_system.py`
- Golden ratio grid generator
- Visual balance scorer (symmetry, tension, focal point)
- Whitespace optimizer
- Alignment quality scorer

## Phase 5: Advanced Typography Engine
- **Files**: `typography_engine.py`
- Font pairing database with harmony scores
- Dynamic type scale based on content length and viewport
- Optical sizing for display vs body
- Line-height adaptation based on measure

## Phase 6: AI Quality Scoring + Critic v2
- **Files**: `critic_engine.py`, `aesthetic_scorer.py`
- Composition quality (alignment, balance, hierarchy, whitespace)
- Color harmony (contrast, complementary, triadic scores)
- Typography quality (readability, hierarchy, measure)
- Visual interest (variety, focal point, negative space)
- Auto-regeneration triggers based on score thresholds

## Phase 7: Design Memory + Learning
- **Files**: `design_memory.py`, `pattern_library.py`
- Store successful design patterns (layout + tokens + content type)
- Pattern matching for new slides
- User preference learning (preferred directions, layouts, densities)
- Reference image analysis for pattern extraction

## Phase 8: Frontend Integration
- **Files**: `tokens.ts`, `primitives.tsx`, `SlideRuntime.tsx`
- Consume new token categories (shape, animation, grid)
- Support new kit components
- Dynamic CSS variable injection for animation tokens
- Grid overlay for debugging

## Files to Create
- `server4/app/services/v4/shape_tokens.py`
- `server4/app/services/v4/animation_tokens.py`
- `server4/app/services/v4/grid_tokens.py`
- `server4/app/services/v4/typography_engine.py`
- `server4/app/services/v4/composition_engine.py`
- `server4/app/services/v4/aesthetic_scorer.py`
- `server4/app/services/v4/design_memory.py`
- `server4/app/services/v4/pattern_library.py`
- `lliveupdatedstreaming/sandbox/src/kit/CinematicHero.tsx`
- `lliveupdatedstreaming/sandbox/src/kit/EditorialImage.tsx`
- `lliveupdatedstreaming/sandbox/src/kit/GlassCard.tsx`
- `lliveupdatedstreaming/sandbox/src/kit/DuotoneHero.tsx`
- `lliveupdatedstreaming/sandbox/src/kit/MagazineLayout.tsx`
- `lliveupdatedstreaming/sandbox/src/kit/AsymmetricGrid.tsx`
- `lliveupdatedstreaming/sandbox/src/kit/SplitOverlap.tsx`
- `lliveupdatedstreaming/sandbox/src/kit/FloatingStat.tsx`

## Verification
- `tests/v4_pipeline_smoke_test.py` — update for new tokens
- `tests/test_design_intelligence.py` — new tests for composition, scoring, memory
