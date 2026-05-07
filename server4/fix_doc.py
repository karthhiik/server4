with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'r', encoding='utf-8') as f:
    text = f.read()

old_doc = '''## Document Control

**Version**: 7.0
**Status**: Ready for Implementation
**Supersedes**: V5 (PREMIUM_SLIDE_MCP_STANDALONE_PLAN_V5.md)
**Architecture**: Multi-Renderer Pipeline (4 renderers) + 8 Agents + Self-Evolving Code Agent
**Total Tools**: 75+
**Total Themes**: 100+ (24 built-in + generative + mutations + community)
**Renderers**: 4 (reveal.js, React+Three.js, Zero-dep HTML, PPTX)
**Editors**: 4 (Reveal, React Inspector, HTML/Monaco, Canvas/PPTX)
**Modes**: 2 (Reading, Presentation)
**Image Model**: Flux-first (flux-pro-2 primary)
**Thinking Models**: Kimi-K2-Thinking + Phi-4-reasoning
**Research Base**: 16 GitHub repositories analyzed'''

new_doc = '''## Document Control

**Version**: 7.1 (GLM5/Gemini Feedback Hardened)
**Status**: Architecture Approved. Ready for Phase 1 Implementation.
**Supersedes**: V7.0
**Architecture**: Multi-Renderer Pipeline (4 renderers) + Unified DSL Editor + 8 Agents
**Timeline**: 20 Weeks (11 Phases)
**Total Tools**: 75+
**Total Themes**: 100+ (Brand DNA + 24 built-in + generative)
**Renderers**: 4 (reveal.js [UnoCSS], React+Three.js, Zero-dep HTML, PPTX/PptxGenJS)
**Editor**: 1 Unified DSL Editor (Zero State Drift)
**Image Model**: FLUX.1-Kontext-pro primary
**Thinking Models**: Kimi-K2-Thinking + Phi-4-reasoning-vision-15B + DeepSeek-V3.2
**Quality Gates**: Human-in-the-Loop (HITL), Playwright SSIM Regression, PreTeXt verification
**Research Base**: 16 GitHub repositories analyzed (Verified imports)'''

text = text.replace(old_doc, new_doc)

with open('PREMIUM_SLIDE_MCP_V7_PLAN.md', 'w', encoding='utf-8') as f:
    f.write(text)
print('Document control replaced!')
