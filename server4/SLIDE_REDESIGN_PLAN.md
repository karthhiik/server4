# Slide Generation System Redesign — Premium Version

## Current Architecture Review

### Components Analyzed
1. **Brain MCP** (`slide_generator.py`) — JSON-based content generation
2. **Design MCP** (`theme_engine.py`, `layout_solver.py`) — Rule-based themes
3. **Render MCP** (`html_builder.py`, `pptx_builder.py`, `pdf_builder.py`) — Output builders
4. **Image Service** — Lucid/Phoenix integration with Redis caching

### Issues Identified

| Area | Issue | Severity |
|------|-------|----------|
| **Content** | JSON parsing failures in slide_generator | High |
| **Content** | No layout-aware content optimization | Medium |
| **Design** | Theme selection is purely keyword-based | Medium |
| **Design** | Layout solver lacks content analysis | Medium |
| **Render** | PDF builder supports only 6 layouts | High |
| **Render** | HTML lacks advanced animations/effects | Medium |
| **Images** | Lucid worker returns 500 errors | High |
| **Images** | No local fallback image generation | High |

## Redesign Plan — Premium Slide Generation

### Phase 1: Content Generation Intelligence

#### 1.1 Layout-Aware Content Optimization
```
Before: Generate content, then fit to layout
After:  Analyze layout requirements → Generate optimized content
```

- Add `LayoutRequirementAnalyzer` class
- Pre-validate content fits layout constraints (bullet count, data points)
- Generate layout-specific prompts with strict constraints

#### 1.2 Enhanced Quality Guards
- Add **content density checker** — ensure no overcrowding
- Add **visual weight estimator** — predict how content fills slide
- Add **narrative flow validator** — check transitions between slides

#### 1.3 Multi-Pass Content Generation
```
Pass 1: Generate draft content
Pass 2: Refine for investor/purpose-specific language
Pass 3: Validate against quality gates
Pass 4: Optimize for presentation flow
```

### Phase 2: Design Intelligence

#### 2.1 Smart Theme Selection (Beyond Keywords)
```
Current: keyword → theme
New:     topic + purpose + audience + content_type → AI-suggested theme
```

- Add `ThemeRecommender` using LLM for nuanced theme selection
- Consider: brand colors, industry, presentation length, audience expertise

#### 2.2 Dynamic Layout Selection
```
Current: Outline suggests layout
New:     Content analyzer → Layout solver → Theme-adjusted layout
```

- Enhanced `LayoutSolver` with content complexity scoring
- Add theme-aware layout adjustments (spacing, hierarchy)

#### 2.3 Design Quality Pass (Already Implemented ✓)
- Keep `_run_design_quality_pass` in orchestrator
- Enhance with content-aware warnings

### Phase 3: Rendering Excellence

#### 3.1 HTML Builder Enhancements
- **Advanced animations**: Parallax, morphing, reveal on scroll
- **Interactive elements**: Clickable hotspots, embedded videos
- **Theme-aware transitions**: Smooth crossfade, directional wipes
- **Progressive loading**: Lazy load images, skeleton screens

#### 3.2 PPTX Builder Enhancements
- Add **native charts** with theme colors (already done ✓)
- Add **slide master templates** for consistent branding
- Add **speaker notes** auto-generation
- Add **embedded fonts** for offline viewing

#### 3.3 PDF Builder Rebuild
```
Current: Basic 6 layouts, WeasyPrint dependency
New:     Support all 12 layouts, proper chart/image embedding
```

- Use `python-pptx` as intermediate → convert to PDF
- Or use `reportlab` for direct PDF generation
- Target: Feature parity with HTML builder

### Phase 4: Image Generation Robustness

#### 4.1 Multi-Provider Fallback
```
Provider Priority:
1. Lucid (original) → on failure
2. Phoenix (backup) → on failure  
3. DALL-E 3 (premium fallback) → on failure
4. Local placeholder (last resort)
```

#### 4.2 Image Caching Strategy
- Redis caching with 24hr TTL
- Cache by: `presentation_id + slide_index + content_hash`
- Pre-generate images during slide generation

#### 4.3 Image-Text Sync
- Ensure image theme matches slide content
- Add `image_placeholder` for slides without generated images

### Phase 5: Premium Features

#### 5.1 Real-Time Preview
- WebSocket streaming of generation progress
- Live slide thumbnail updates
- Incremental HTML preview

#### 5.2 Export Pipeline
- Async exports (PPTX, PDF) via Celery
- SAS token for secure downloads
- Export quality options (draft/standard/premium)

#### 5.3 Template System
- Pre-built premium templates
- Template customization with brand guidelines
- User-created templates storage

## Implementation Priority

| Priority | Feature | Impact |
|----------|---------|--------|
| P0 | Fix JSON parsing in slide_generator | High |
| P0 | Image fallback chain (Lucid → Phoenix → DALL-E) | High |
| P1 | Enhanced layout-aware content | Medium |
| P1 | PDF builder all 12 layouts | High |
| P2 | Theme recommender (LLM-based) | Medium |
| P2 | HTML advanced animations | Low |
| P3 | Real-time preview streaming | Low |

## Testing Strategy

1. **Unit Tests**: Each component (generators, builders, engines)
2. **Integration Tests**: Full pipeline (input → output)
3. **Visual Tests**: Compare rendered outputs
4. **User Tests**: Real presentation generation

---

Want me to start implementing any specific phase or priority item?