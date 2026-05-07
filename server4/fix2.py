with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# M1
old_m1 = "│  Cost: 0.09ms per measurement — negligible                │   │\n│  └─────────────────────────────────────────────────────────┘   │"
new_m1 = old_m1 + """

│  ⚠️ MATURITY RISK & FALLBACK (from GLM5 review):             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PreTeXt.js is extremely new (created March 2026).        │   │
│  │  It may have undiscovered edge cases or browser bugs.     │   │
│  │                                                           │   │
│  │  Fallback Strategy:                                       │   │
│  │  If PreTeXt throws errors or fails to load:               │   │
│  │  1. Gracefully degrade to standard canvas.measureText() │   │
│  │  2. Use DOM-based hidden div measurement (slower)         │   │
│  │  3. Fall back to conservative character-count heuristics  │   │
│  └─────────────────────────────────────────────────────────┘   │"""

pattern_m1 = "│  Cost: 0.09ms per measurement — negligible                │   │\n│  └─────────────────────────────────────────────────────────┘   │"
if pattern_m1 in text:
    text = text.replace(pattern_m1, new_m1)
    print("M1 Done")

# M4
old_m4 = """### 6.2 Self-Evaluation Loop

`"""

new_m4 = """### 6.2 Self-Evaluation Loop & Visual Feedback

To address the GLM5 review feedback, the swarm evaluates slides before user review using **Automated Visual Feedback Loops**:

`markdown
1. Structural Regression (QA Agent)
   - Information Density Check: Does this slide have too much text?
   - Title Truncation Test: Will this title fit on a 1920x1080 screen?
   - Narrative Flow: Does slide 5 logically follow slide 4?

2. Visual Regression (Golden Master)
   - Render the slide headlessly (Playwright).
   - Capture a screenshot.
   - Run Structural Similarity Index (SSIM) against Golden Master templates.
   - If the layout is severely broken, force Regeneration.
   - Accessibility Validation: Validate 4.5:1 minimum contrast ratio using the captured screenshot.
`

`"""

if old_m4 in text:
    text = text.replace(old_m4, new_m4)
    print("M4 Done")

# M8
old_m8 = "| Text styling inheritance | PPTX <a:rPr> tags don't inherit correctly | Apply color, font, size to EVERY text run explicitly |"
new_m8 = old_m8 + """

### 23.6 Fallback: python-pptx Backend Service

**Note**: If PptxGenJS proves too limited for complex templates (e.g., custom SmartArt, advanced chart data binding), the exact same DSL will be routed to a Python microservice running python-pptx, rather than executing the conversion in the browser. 
*   **Tradeoff**: This breaks the serverless/edge deployment paradigm for PPTX rendering and introduces network latency for large file transfers, but guarantees 100% fidelity to the native Office Open XML specification."""

if old_m8 in text:
    text = text.replace(old_m8, new_m8)
    print("M8 Done")

with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'w', encoding='utf-8') as f:
    f.write(text)

