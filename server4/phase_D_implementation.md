# Phase D — Design Intelligence + Research Integration

> **Owner**: Founder
> **Status**: Planned (awaiting review)
> **Date**: 2026-04-01
> **Priority**: P1 — Quality improvements on working pipeline

---

## 1. Current State (What Exists)

| Component | Status | Issue |
|-----------|--------|-------|
| `theme_engine.py` | ✅ Algorithmic | Generates themes from brand colors via HSL math. No AI suggestions. No topic-aware recommendations. |
| `layout_solver.py` | ✅ Basic | Pure algorithmic layout solver. No content-aware analysis or suggestions. |
| `orchestrator.py` | ⚠️ Generic research | Uses generic LLM research call. No structured engine routing by purpose. |
| `orchestrator.py` | ⚠️ No quality pass | No post-content design quality validation. Slides go directly to output. |
| 7 Research Engines | ✅ Built | `search_engine`, `market_engine`, `news_engine`, `social_engine`, `financial_engine`, `scraper_engine`, `academic_engine` — all built but not wired into orchestrator. |
| Design MCP (5 engines) | ✅ Built | `theme_engine`, `layout_solver`, `color_engine`, `chart_styler`, `accessibility` — all built but minimally used. |

---

## 2. Architecture Decisions

### Design Intelligence Philosophy

```
┌─────────────────────────────────────────────────────────┐
│              Phase D Design Intelligence                 │
│                                                          │
│  BEFORE (Phases A-C):                                    │
│    topic → research → outline → slides → export          │
│    (functional but generic)                              │
│                                                          │
│  AFTER (Phase D):                                        │
│    topic → smart_research → outline → slides             │
│      → design_pass → quality_check → export              │
│    (intelligent, premium, investor-grade)                │
│                                                          │
│  Key additions:                                          │
│    1. AI theme suggestions (topic → mood → theme)        │
│    2. Content-aware layout analysis (bullets → chart?)   │
│    3. Structured research routing (purpose → engine)     │
│    4. Post-content quality validation (density, sources) │
└─────────────────────────────────────────────────────────┘
```

### Why Phase D Now?

- Phase B made generation intelligent (PromptEngine, writing styles, quality guards)
- Phase C made exports work (PPTX/PDF sync, HTML/PNG async, SAS tokens)
- Phase D makes everything feel **premium** — the difference between "a presentation" and "a pitch deck that gets funded"

---

## 3. Phase D Steps (4 Steps, 4 Files)

### D1: AI-Driven Theme Suggestions

**File**: `app/mcp/design_mcp/engines/theme_engine.py`

**Strategy**: Add `suggest_theme(topic, purpose, audience)` method that maps presentation context to the best built-in theme. V1 is rule-based (zero LLM cost). V1b adds LLM enhancement for vague inputs.

#### Topic → Mood → Theme Mapping

| Topic Keywords | Detected Mood | Recommended Theme |
|---------------|---------------|-------------------|
| AI, ML, tech, software, SaaS, platform | tech-neon | `tech-neon` |
| sales, pitch, startup, fundraising, investor | startup-gradient | `startup-gradient` |
| internal, meeting, workshop, review | minimal-mono | `minimal-mono` |
| quarterly, board, financial, report, revenue | corporate-blue | `corporate-blue` |
| health, green, nature, sustainability, ESG | nature-earth | `nature-earth` |
| medical, healthcare, pharma, biotech | medical-clean | `medical-clean` |
| education, training, learning, academic | academic-serif | `academic-serif` |
| creative, design, brand, marketing | creative-bold | `creative-bold` |

**Code Pattern**:
```python
class ThemeEngine:
    # Keyword → theme mapping (V1: rule-based, zero LLM cost)
    _TOPIC_THEME_MAP = {
        "tech-neon": ["ai", "ml", "tech", "software", "saas", "platform", "cloud", "api"],
        "startup-gradient": ["sales", "pitch", "startup", "fundraising", "investor", "venture"],
        "minimal-mono": ["internal", "meeting", "workshop", "review", "standup"],
        "corporate-blue": ["quarterly", "board", "financial", "report", "revenue", "earnings"],
        "nature-earth": ["health", "green", "nature", "sustainability", "esg", "environment"],
        "medical-clean": ["medical", "healthcare", "pharma", "biotech", "clinical"],
        "academic-serif": ["education", "training", "learning", "academic", "research"],
        "creative-bold": ["creative", "design", "brand", "marketing", "campaign"],
    }

    def suggest_theme(self, topic: str, purpose: str = "", audience: str = "") -> dict:
        """Suggest best theme based on topic, purpose, and audience."""
        topic_lower = topic.lower()
        scores = {}
        for theme_id, keywords in self._TOPIC_THEME_MAP.items():
            score = sum(1 for kw in keywords if kw in topic_lower)
            scores[theme_id] = score

        best_theme = max(scores, key=scores.get) if max(scores.values()) > 0 else "corporate-blue"

        # Purpose overrides
        if purpose in ("investor", "fundraising") and best_theme == "minimal-mono":
            best_theme = "startup-gradient"  # Investors expect bold, not minimal
        if purpose == "internal" and best_theme == "startup-gradient":
            best_theme = "minimal-mono"  # Internal decks should be clean

        return {"theme_id": best_theme, "confidence": max(scores.values()) / 3.0, "reason": f"Topic matches '{best_theme}' theme"}
```

**Changes**:
- Add `_TOPIC_THEME_MAP` class constant
- Add `suggest_theme()` method
- Add purpose override logic

---

### D2: Content-Aware Layout Suggestions

**File**: `app/mcp/design_mcp/engines/layout_solver.py`

**Strategy**: Analyze slide content after generation and suggest layout improvements. Returns warnings, not auto-changes. User decides.

#### Analysis Rules

| Rule | Trigger | Suggestion |
|------|---------|------------|
| Bullet overload | > 6 bullets detected | "Consider splitting into 2 slides or using a chart layout" |
| Single insight | 1 bullet, short text | "Consider title-hero layout for impact" |
| Number density | > 3 numbers in bullets | "Consider chart layout for data visualization" |
| Comparison text | "vs", "versus", "compared to" detected | "Consider comparison layout for clarity" |
| Timeline text | Years/dates detected in sequence | "Consider timeline layout for chronological data" |
| Quote detected | Text in quotes, attribution present | "Consider quote layout for emphasis" |
| Team content | Names + roles detected | "Consider team-grid layout" |
| KPI content | Metrics with %, $, growth indicators | "Consider kpi-dashboard layout" |

**Code Pattern**:
```python
class LayoutSolver:
    def analyze_slide(self, slide_content: dict) -> list[dict]:
        """Analyze slide content and suggest layout improvements."""
        suggestions = []
        bullets = slide_content.get("bullets", [])
        title = slide_content.get("title", "")
        full_text = title + " " + " ".join(str(b) for b in bullets)

        # Bullet overload check
        if len(bullets) > 6:
            suggestions.append({
                "type": "layout_suggestion",
                "severity": "warning",
                "message": f"{len(bullets)} bullets detected (max 6). Consider splitting into 2 slides or using a chart layout.",
                "suggested_layout": "chart" if any(self._is_number(b) for b in bullets) else "two-column",
            })

        # Number density check
        number_count = sum(1 for b in bullets if self._has_number(b))
        if number_count >= 3 and slide_content.get("layout") == "bullets":
            suggestions.append({
                "type": "layout_suggestion",
                "severity": "info",
                "message": f"{number_count} data points detected. Consider chart layout for better visualization.",
                "suggested_layout": "chart",
            })

        # Comparison detection
        if any(kw in full_text.lower() for kw in ["vs", "versus", "compared to", "versus", "vs."]):
            if slide_content.get("layout") not in ("comparison", "two-column"):
                suggestions.append({
                    "type": "layout_suggestion",
                    "severity": "info",
                    "message": "Comparison content detected. Consider comparison layout for clarity.",
                    "suggested_layout": "comparison",
                })

        return suggestions
```

**Changes**:
- Add `analyze_slide()` method
- Add helper methods: `_is_number()`, `_has_number()`, `_detect_comparison()`, `_detect_timeline()`, `_detect_team()`, `_detect_kpi()`
- Return list of suggestion dicts with `type`, `severity`, `message`, `suggested_layout`

---

### D3: Research Engine Integration into Orchestrator

**File**: `app/services/orchestrator/orchestrator.py`

**Strategy**: Replace generic LLM research call with purpose-aware routing to specific research engines. Returns structured data bundle instead of raw text.

#### Research Routing Matrix

| Purpose | Primary Engine | Secondary Engine | Data Expected |
|---------|---------------|------------------|---------------|
| pitch, fundraising, investor | `market_engine` | `social_engine` | TAM/SAM/SOM, growth rates, key players, competitors |
| quarterly, internal | `financial_engine` | `news_engine` | Benchmarks, KPIs, industry trends, news |
| sales, marketing | `search_engine` | `social_engine` | Competitor analysis, market positioning, social proof |
| academic, research | `academic_engine` | `scraper_engine` | Papers, citations, methodology |
| health, medical | `search_engine` | `news_engine` | Industry reports, regulatory updates |
| general | `search_engine` | `market_engine` | General market overview |

**Code Pattern**:
```python
async def _do_research(self, topic: str, purpose: str, mode: str) -> dict:
    """Purpose-aware research using specific engines."""
    from app.mcp.brain_mcp.engines.market_engine import MarketEngine
    from app.mcp.brain_mcp.engines.social_engine import SocialEngine
    from app.mcp.brain_mcp.engines.financial_engine import FinancialEngine
    from app.mcp.brain_mcp.engines.news_engine import NewsEngine
    from app.mcp.brain_mcp.engines.search_engine import SearchEngine

    research_bundle = {
        "key_facts": [],
        "sourced_numbers": [],
        "competitor_names": [],
        "market_data": {},
        "statistics": {},
        "raw_summary": "",
    }

    if purpose in ("pitch", "fundraising", "investor"):
        market = MarketEngine()
        market_data = await market.analyze(industry=topic, metrics=["tam", "growth_rate", "key_players"])
        research_bundle["market_data"] = market_data
        research_bundle["key_facts"].extend(market_data.get("facts", []))
        research_bundle["sourced_numbers"].extend(market_data.get("numbers", []))

        social = SocialEngine()
        competitors = await social.get_competitors(topic)
        research_bundle["competitor_names"] = competitors

    elif purpose in ("quarterly", "internal"):
        financial = FinancialEngine()
        benchmarks = await financial.get_benchmarks(topic)
        research_bundle["statistics"] = benchmarks

        news = NewsEngine()
        trends = await news.get_trends(topic)
        research_bundle["key_facts"].extend(trends.get("key_points", []))

    else:
        # Fallback: generic search
        search = SearchEngine()
        results = await search.search(topic, max_results=10)
        research_bundle["raw_summary"] = "\n".join(r.get("snippet", "") for r in results)

    return research_bundle
```

**Changes**:
- Replace generic LLM research call with engine routing
- Return structured `research_bundle` dict instead of raw text
- Pass `research_bundle` to outline and slide generators

---

### D4: Post-Content Design Quality Pass

**File**: `app/services/orchestrator/orchestrator.py`

**Strategy**: Add a new method `_run_design_quality_pass()` that runs after `_do_content_generation()` but before returning results. Validates slide density, required elements, style consistency.

#### Quality Checks

| Check | Rule | Severity |
|-------|------|----------|
| Slide density | Title: 3-8 words. Bullets: max 6, each max 15 words | warning |
| Market slide | Must have TAM/SAM/SOM or market size data | error |
| Traction slide | Must show growth trajectory (numbers trending up) | warning |
| Ask slide | Must have specific funding amount or ask | error |
| Style consistency | Same writing voice across all slides (no voice drift) | warning |
| Source coverage | > 70% of claims have sources | warning |
| Number consistency | Same numbers don't contradict across slides | error |

**Code Pattern**:
```python
def _run_design_quality_pass(self, slides: list[dict], purpose: str, style: str) -> list[dict]:
    """Run post-content design quality validation."""
    warnings = []

    for i, slide in enumerate(slides):
        content = slide.get("content", {})
        title = content.get("title", "")
        bullets = content.get("bullets", [])
        layout = slide.get("layout", "")

        # Title length check
        title_words = len(title.split())
        if title_words > 8:
            warnings.append(f"Slide {i+1}: Title has {title_words} words (max 8). Consider shortening.")

        # Bullet density check
        if len(bullets) > 6:
            warnings.append(f"Slide {i+1}: {len(bullets)} bullets (max 6). Consider splitting or using chart layout.")

        # Bullet length check
        for j, bullet in enumerate(bullets):
            if len(str(bullet).split()) > 15:
                warnings.append(f"Slide {i+1}, bullet {j+1}: {len(str(bullet).split())} words (max 15).")

        # Purpose-specific checks
        if purpose in ("pitch", "fundraising"):
            if "market" in title.lower() or "market" in " ".join(str(b) for b in bullets).lower():
                has_tam = any("tam" in str(b).lower() or "total addressable" in str(b).lower() for b in bullets)
                if not has_tam:
                    warnings.append(f"Slide {i+1}: Market slide missing TAM/SAM/SOM data.")

    return warnings
```

**Changes**:
- Add `_run_design_quality_pass()` method
- Call it in `generate_presentation()` after content generation
- Include warnings in generation response: `{"slide_count": N, "warnings": [...]}`

---

## 4. File Change Summary

| File | Action | Est. Lines | Purpose |
|------|--------|-----------|---------|
| `app/mcp/design_mcp/engines/theme_engine.py` | **MODIFY** | +50 lines | Add `suggest_theme()` with topic→mood→theme mapping |
| `app/mcp/design_mcp/engines/layout_solver.py` | **MODIFY** | +120 lines | Add `analyze_slide()` with 8 content-aware rules |
| `app/services/orchestrator/orchestrator.py` | **MODIFY** | +150 lines | Research engine routing + design quality pass |

**Total: 3 file modifications, ~320 new lines**

---

## 5. Implementation Order

```
Step 1: AI theme suggestions (D1)          — Zero LLM cost, immediate value
Step 2: Content-aware layout analysis (D2)  — Rule-based, no external deps
Step 3: Research engine integration (D3)    — Wire existing engines into orchestrator
Step 4: Post-content quality pass (D4)      — Validation layer on top of working pipeline
```

---

## 6. Testing Strategy

### Unit Tests
| Test | What | How |
|------|------|-----|
| `test_theme_suggestion_tech` | AI topic → tech-neon theme | Mock topic="AI SaaS platform", verify theme_id="tech-neon" |
| `test_theme_suggestion_investor` | Fundraising purpose → startup-gradient | Verify purpose override works |
| `test_layout_analysis_bullet_overload` | 10 bullets → chart suggestion | Mock slide content, verify warning returned |
| `test_layout_analysis_comparison` | "vs" text → comparison layout | Mock slide with comparison keywords |
| `test_research_routing_investor` | pitch purpose → market_engine + social_engine | Mock engines, verify calls |
| `test_quality_pass_density` | Long title + many bullets → warnings | Mock slides, verify warning count |

### Integration Tests
| Test | What | How |
|------|------|-----|
| `test_full_generation_with_design_intelligence` | End-to-end with theme suggestions + layout analysis | Create presentation → generate → verify theme_id + warnings in response |

---

## 7. Risk Areas & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Research engines not configured in dev | High | Medium | Graceful fallback to generic LLM research. Log warning, don't fail. |
| Layout suggestions annoy users | Medium | Low | Return as optional warnings, not auto-changes. User decides. |
| Quality pass slows generation | Low | Low | Rule-based checks (regex/length), zero LLM calls. ~5ms per slide. |
| Theme mapping too rigid | Medium | Low | V1b: Add LLM enhancement for vague inputs. V1: Rule-based is fast and free. |

---

## 8. Success Criteria

- [ ] `suggest_theme()` returns correct theme for 8+ topic categories
- [ ] `analyze_slide()` detects bullet overload, number density, comparison, timeline, team, KPI content
- [ ] Research routing calls correct engines based on purpose (pitch→market, quarterly→financial)
- [ ] Quality pass returns warnings for density violations, missing required elements
- [ ] All 6 Phase D unit tests pass
- [ ] No breaking changes to existing Phase B/C functionality
- [ ] Zero additional LLM cost for D1/D2 (rule-based)
