with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'r', encoding='utf-8') as f:
    text = f.read()

import re
old_timeline_pattern = r"## 25\. Implementation Phases.*?---"
# Use dotall to match across newlines
match = re.search(old_timeline_pattern, text, re.DOTALL)

if match:
    old_timeline = match.group(0)
    
    new_timeline = '''## 25. Implementation Phases (Revised: 20 Weeks)

### Phase 1: Foundation (Weeks 1-2)

**Deliverables:**
- FastMCP server (stdio/HTTP+SSE) with 40 core tools
- Slide DSL v2 schema (Zod validation)
- MongoDB + Redis + ChromaDB setup
- Basic CRUD (create/read/update/delete presentations)
- Agent Communication Protocol (Context Board)

**Dependencies:** None

### Phase 2: Agent Core (Weeks 3-5)

**Deliverables:**
- Orchestrator with Context Board
- CEO Agent (Kimi-K2-Thinking / DeepSeek, strategy)
- Researcher Agent (DeepSeek-V3.2, data)
- Layout Agent (GPT-4o, spatial reasoning)
- Agent parallel execution framework

**Dependencies:** Phase 1

### Phase 3: Code Agent + Self-Evolving Loop (Weeks 5-7)

**Deliverables:**
- Code Agent with skills system (yoyo-evolve pattern)
- DSL generation pipeline and Semantic Skill Versioning
- Multi-provider routing (8+ models) with Instant vs Thinking modes
- Self-evaluation loop (generate → evaluate → learn)

**Dependencies:** Phase 2

### Phase 4: reveal.js Renderer & CSS Architecture (Weeks 7-9)

**Deliverables:**
- DSL → reveal.js compiler
- UnoCSS integration (resolving Tailwind v4 conflict for reveal.js)
- Theme → CSS compiler (100+ themes)
- Auto-Animate support and speaker notes

**Dependencies:** Phase 3

### Phase 5: Design Intelligence & Brand DNA (Weeks 9-11)

**Deliverables:**
- Designer Agent (Phi-4-reasoning-vision-15B)
- Theme Engine: 24 built-in themes + Generative Theme Engine
- Brand DNA Extraction pipeline (crawling, logo analysis, rule generation)
- 12 anti-AI-slop presets and Visual Style Discovery UX
- PreTeXt integration with canvas.measureText() fallbacks

**Dependencies:** Phase 4

### Phase 6: React + Three.js Renderer (Weeks 11-13)

**Deliverables:**
- DSL → React component compiler
- 3D/VFX Agent (DeepSeek-V3.2)
- Performance guardrails (lazy-loading of Three.js chunks, 60fps)
- Vite dev server with HMR for hot preview

**Dependencies:** Phase 5

### Phase 7: PPTX & HTML Renderers + Template Injection (Weeks 13-15)

**Deliverables:**
- PptxGenJS integration (native objects)
- PPTX Template Injection (.potx master slide mapping)
- HTML-to-PPTX table conversion
- Zero-dep HTML renderer (inline CSS, minimal JS)
- React → PPTX conversion (Three.js → screenshot fallback transparency UI)

**Dependencies:** Phase 6

### Phase 8: Image Generation Pipeline (Weeks 15-16)

**Deliverables:**
- Flux-first image routing (flux-pro-2 → phoenix → lucid)
- Image resizing/optimizing and asset CDN
- Fallback infrastructure for Cloudflare limits

**Dependencies:** Phase 5

### Phase 9: Unified DSL Editor (Weeks 16-18)

**Deliverables:**
- Single Unified Editor interface replacing 4 isolated editors
- Contextual control panels per renderer view
- HITL (Human-in-the-Loop) Checkpoint gates
- Fast Mode generation toggle

**Dependencies:** Phase 7

### Phase 10: State Synchronization (Weeks 18-19)

**Deliverables:**
- Centralized Zustand/Redux state store 
- Yjs CRDTs for multiplayer editing
- WebSocket broadcasting for real-time agent updates

**Dependencies:** Phase 9

### Phase 11: QA + Polish + Delivery (Weeks 19-20)

**Deliverables:**
- QA Agent with Playwright-based Visual Regression (Golden Master SSIM)
- Accessibility validation (4.5:1 contrast, ARIA DOM)
- Presentation & Reading modes
- Production hardening and load testing

**Dependencies:** Phase 10

---'''
    text = text.replace(old_timeline, new_timeline)
    with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Timline replaced!')
else:
    print('Regex failed!')
