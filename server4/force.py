import re

with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'r', encoding='utf-8') as f:
    text = f.read()

# M1
m1_match = re.search(r"Cost: 0.09ms per measurement — negligible\s*│\s*└─────────────────────────────────────────────────────────┘\s*", text)
if m1_match and "MATURITY RISK" not in text:
    old = m1_match.group(0)
    new = old + '''
  ⚠️ MATURITY RISK & FALLBACK (from GLM5 review):             
  ┌─────────────────────────────────────────────────────────┐
  │  PreTeXt.js is extremely new (created March 2026).        │
  │  It may have undiscovered edge cases or browser bugs.     │
  │                                                           │
  │  Fallback Strategy:                                       │
  │  If PreTeXt throws errors or fails to load:               │
  │  1. Gracefully degrade to standard canvas.measureText() │
  │  2. Use DOM-based hidden div measurement (slower)         │
  │  3. Fall back to conservative character-count heuristics  │
  └─────────────────────────────────────────────────────────┘\n\n'''
    text = text.replace(old, new)
    print("M1 replaced")

# M2
m2_match = re.search(r"### 8.3 Performance Guardrails\n\n`	ypescript", text)
if m2_match and "CRITICAL LAZY-LOADING" not in text:
    old = m2_match.group(0)
    new = '''### 8.3 Performance Guardrails & Lazy Loading

⚠️ **CRITICAL LAZY-LOADING REQUIREMENT:** 
Three.js adds 350-450KB to the bundle size. It MUST be lazily loaded to ensure the presentation loads instantly.
- CSS-only slides and basic UI render immediately.
- 3D content shows a <Skeleton /> or static image while downloading the Three.js payload.
- Only load @react-three/fiber on slides that explicitly require it.

`	ypescript
const ThreeDBarChart = lazy(() => import('./charts/ThreeDBarChart'));
`

`	ypescript'''
    text = text.replace(old, new)
    print("M2 replaced")

# M3
m3_match = re.search(r"add \"View interactive version\" link.*?\n`\n\n---\n\n## 11", text, re.DOTALL)
if m3_match and "10.5 Centralized State Sync" not in text:
    old = m3_match.group(0)
    new = old.replace("## 11", "### 10.5 Centralized State Sync (WebSocket & CRDT)\n\nTo ensure the Unified Editor truly eliminates state drift (especially during multi-user collaboration), the DSL state is managed via:\n\n1. **Centralized Store (Zustand/Redux):** The client holds a single state tree representing the entire presentation DSL.\n2. **Yjs CRDTs:** Allows real-time multiplayer editing (like open-pencil architecture) without merge conflicts.\n3. **WebSocket Broadcasting:** When an agent updates a slide, the patch is broadcasted to all connected clients instantly.\n4. **Lineage Tracking:** Every node in the DSL tracks whether it was created by an Agent, a User, or a Template, allowing targeted undo/redo operations.\n\n---\n\n## 11")
    text = text.replace(old, new)
    print("M3 replaced")

# M4
m4_match = re.search(r"### 6.2 Self-Evaluation Loop.*?(?=If a check fails)", text, re.DOTALL)
if m4_match and "Automated Visual Feedback" not in text:
    old = m4_match.group(0)
    new = '''### 6.2 Self-Evaluation Loop & Visual Feedback

The swarm doesn't just output slides; it evaluates them before review using **Automated Visual Feedback Loops** (a critical mitigation identified in the GLM5 review):

1. **Information Density Check (QA Agent)**: Does this slide have too much text?
2. **Title Truncation Test**: Will this title fit on a 1920x1080 screen?
3. **Narrative Flow**: Does slide 5 logically follow slide 4?
4. **Visual Regression (Golden Master)**: 
   - Render the slide headlessly (Playwright).
   - Capture a screenshot.
   - Run Structural Similarity Index (SSIM) against Golden Master templates.
   - If the layout is severely broken (e.g., overlapping text, elements off screen), send it back to the Designer Agent.
5. **Accessibility Validation**: Validate 4.5:1 minimum contrast ratio using the captured screenshot.

'''
    text = text.replace(old, new)
    print("M4 replaced")

# M8
m8_match = re.search(r"Text styling inheritance.*?explicitly.*?\n", text, re.DOTALL)
if m8_match and "23.6 Fallback" not in text:
    old = m8_match.group(0)
    new = old + '''\n### 23.6 Fallback: python-pptx Backend Service\n\n**Note**: If PptxGenJS proves too limited for complex templates (e.g., custom SmartArt, advanced chart data binding), the exact same DSL will be routed to a Python microservice running python-pptx, rather than executing the conversion in the browser. \n*   **Tradeoff**: This breaks the serverless/edge deployment paradigm for PPTX rendering and introduces network latency for large file transfers, but guarantees 100% fidelity to the native Office Open XML specification.\n'''
    text = text.replace(old, new)
    print("M8 replaced")

with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'w', encoding='utf-8') as f:
    f.write(text)

print("Done with python")
