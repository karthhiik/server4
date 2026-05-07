with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'r', encoding='utf-8') as f:
    text = f.read()

import re

old_m8 = "**Fallback**: Maintain python-pptx as a server-side alternative for enterprise resilience (single-developer risk for PptxGenJS)."
new_m8 = """### 23.6 Fallback: python-pptx Backend Service

**Note**: If PptxGenJS proves too limited for complex templates (e.g., custom SmartArt, advanced chart data binding), the exact same DSL will be routed to a Python microservice running python-pptx, rather than executing the conversion in the browser. 
*   **Tradeoff**: This breaks the serverless/edge deployment paradigm for PPTX rendering and introduces network latency for large file transfers, but guarantees 100% fidelity to the native Office Open XML specification. Maintains python-pptx as a server-side alternative for enterprise resilience (single-developer risk for PptxGenJS)."""

if old_m8 in text:
    text = text.replace(old_m8, new_m8)
    print("M8 Fixed")

with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'w', encoding='utf-8') as f:
    f.write(text)
