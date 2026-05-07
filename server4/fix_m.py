import re

# open file
with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'r', encoding='utf-8') as f:
    text = f.read()

# M1
old_m1 = "│  Cost: 0.09ms per measurement — negligible                │\n  └─────────────────────────────────────────────────────────┘"
new_m1 = old_m1 + """

  ⚠️ MATURITY RISK & FALLBACK (from GLM5 review):             
  ┌─────────────────────────────────────────────────────────┐
  │  PreTeXt.js is extremely new (created March 2026).        │
  │  It may have undiscovered edge cases or browser bugs.     │
  │                                                           │
  │  Fallback Strategy:                                       │
  │  If PreTeXt throws errors or fails to load:               │
  │  1. Gracefully degrade to standard `canvas.measureText()` │
  │  2. Use DOM-based hidden div measurement (slower)         │
  │  3. Fall back to conservative character-count heuristics  │
  └─────────────────────────────────────────────────────────┘"""

if old_m1 in text:
    text = text.replace(old_m1, new_m1)
    print("M1 Fixed")

# M2
old_m2 = "### 8.3 Performance Guardrails\n\n```typescript"
new_m2 = """### 8.3 Performance Guardrails & Lazy Loading

⚠️ **CRITICAL LAZY-LOADING REQUIREMENT:** 
Three.js adds 350-450KB to the bundle size. It MUST be lazily loaded to ensure the presentation loads instantly.
- CSS-only slides and basic UI render immediately.
- 3D content shows a `<Skeleton />` or static image while downloading the Three.js payload.
- Only load `@react-three/fiber` on slides that explicitly require it.

```typescript"""

if old_m2 in text:
    text = text.replace(old_m2, new_m2)
    print("M2 Fixed")

# M3
new_m3 = """│  4. Add "View interactive version" link in PPTX speaker notes    │
└────────────────────────────────────────────────────────────────────┘
```

### 10.5 Centralized State Sync (WebSocket & CRDT)

To ensure the Unified Editor truly eliminates state drift (especially during multi-user collaboration), the DSL state is managed via:

1. **Centralized Store (Zustand/Redux):** The client holds a single state tree representing the entire presentation DSL.
2. **Yjs CRDTs:** Allows real-time multiplayer editing (like `open-pencil` architecture) without merge conflicts.
3. **WebSocket Broadcasting:** When an agent updates a slide, the patch is broadcasted to all connected clients instantly.
4. **Lineage Tracking:** Every node in the DSL tracks whether it was created by an Agent, a User, or a Template, allowing targeted undo/redo operations.

---

## 11"""

pattern_m3 = r"│  4\. Add \"View interactive version\" link in PPTX speaker notes    │\s*└────────────────────────────────────────────────────────────────────┘\s*```\s*---\s*## 11"
if re.search(pattern_m3, text):
    text = re.sub(pattern_m3, new_m3, text)
    print("M3 Fixed")

# M4
old_m4 = """### 6.2 Self-Evaluation Loop

The swarm doesn't just output slides; it evaluates them before user review:

1. **Information Density Check (QA Agent)**: Does this slide have too much text?
2. **Title Truncation Test**: Will this title fit on a 1920x1080 screen?
3. **Contrast Analysis**: Are the brand colors legible on this background?
4. **Narrative Flow**: Does slide 5 logically follow slide 4?

If a check fails"""

new_m4 = """### 6.2 Self-Evaluation Loop

The swarm doesn't just output slides; it evaluates them before user review using **Automated Visual Feedback Loops** (a critical mitigation identified in the GLM5 review):

1. **Information Density Check (QA Agent)**: Does this slide have too much text?
2. **Title Truncation Test**: Will this title fit on a 1920x1080 screen?
3. **Narrative Flow**: Does slide 5 logically follow slide 4?
4. **Visual Regression (Golden Master)**: 
   - Render the slide headlessly (Playwright).
   - Capture a screenshot.
   - Run Structural Similarity Index (SSIM) against Golden Master templates.
   - If the layout is severely broken (e.g., overlapping text, elements off screen), send it back to the Designer Agent.
5. **Accessibility Validation**: Validate 4.5:1 minimum contrast ratio using the captured screenshot.

If a check fails"""

if old_m4 in text:
    text = text.replace(old_m4, new_m4)
    print("M4 Fixed")
elif "Automated Visual Feedback" in text:
    pass
else:
    print("M4 Search Failed!")

# M8
old_m8 = "| Text styling inheritance | PPTX `<a:rPr>` tags don't inherit correctly | Apply color, font, size to EVERY text run explicitly |"
new_m8 = old_m8 + """

### 23.6 Fallback: python-pptx Backend Service

**Note**: If PptxGenJS proves too limited for complex templates (e.g., custom SmartArt, advanced chart data binding), the exact same DSL will be routed to a Python microservice running `python-pptx`, rather than executing the conversion in the browser. 
*   **Tradeoff**: This breaks the serverless/edge deployment paradigm for PPTX rendering and introduces network latency for large file transfers, but guarantees 100% fidelity to the native Office Open XML specification."""

if old_m8 in text:
    text = text.replace(old_m8, new_m8)
    print("M8 Fixed")

with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'w', encoding='utf-8') as f:
    f.write(text)
