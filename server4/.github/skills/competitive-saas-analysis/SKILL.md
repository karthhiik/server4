---
name: competitive-saas-analysis
description: "Analyze competitor presentation tools and positioning the product against the market. Use when: comparing against Chronicle, Figma Slides, Canva, Dokie, Beautiful.ai, Gamma, Tome, or SlidesAI; identifying feature gaps to exploit; studying competitor UX patterns; understanding pricing models and free-tier limitations; positioning the product's unique value proposition; or analyzing what current tools get wrong about presentation generation."
---

# Competitive SaaS Analysis

## Purpose
This skill provides frameworks for analyzing the competitive landscape of AI-powered presentation tools. The founder must understand what exists, what works, what fails, and where the opportunity lies — grounded in real product analysis, not assumptions.

## The Competitive Landscape

### Tier 1: Established Players (Large user base, brand recognition)
**Canva** — The template empire
**Google Slides / PowerPoint** — The defaults
**Keynote** — The design-conscious default

### Tier 2: AI-First Challengers (AI generation as core feature)
**Gamma** — AI-generated presentations from prompts
**Tome** — AI storytelling with multimedia
**Beautiful.ai** — AI-assisted layout/design
**SlidesAI** — Google Slides plugin for AI generation

### Tier 3: Design-Forward Innovators (Pushing presentation boundaries)
**Chronicle** — Spatial canvas, interactive presentations
**Figma Slides** — Design-tool precision for presentations
**Dokie** — Minimalist, design-focused presentations
**Pitch** — Collaborative deck building for teams

## Competitor Deep-Dive Framework

When analyzing any competitor, evaluate across these dimensions:

### 1. Generation Intelligence
- Can it generate a full deck from a text prompt?
- How good is the content quality? (Generic vs. specific)
- Does it understand presentation structure or just fill templates?
- How fast is generation?
- Can it research and include real data?

### 2. Editing Experience
- Canvas-based or slide-list based?
- How precise is element control? (Pixel-perfect vs. constrained)
- Does it support freeform placement or locked grids?
- How does it handle text editing? (Rich text vs. basic)
- Undo/redo and version history?

### 3. Design Quality
- Do outputs look professionally designed?
- Is there a consistent design system across slides?
- Typography quality (font pairing, hierarchy, spacing)?
- Color usage (intentional palette vs. random)?
- Image handling (AI-generated, stock, placement quality)?

### 4. Collaboration
- Real-time multi-user editing?
- Comments and feedback workflows?
- Version control?
- Team libraries and brand kits?

### 5. Export & Delivery
- PPTX export quality (does it survive the round-trip)?
- PDF export?
- Web presentation mode (shareable links)?
- Presenter notes and speaker mode?
- Analytics (who viewed, how long)?

### 6. Pricing & Access
- Free tier limitations
- Price per seat
- Feature gating (what's free vs. paid)
- API access for developers

## Known Competitor Weaknesses (Opportunities to Exploit)

### The Template Prison Problem
**Who suffers**: Canva, Beautiful.ai, SlidesAI
**The issue**: Users pick a template, then fight it. Want to move an element? Template says no. Want a layout the template doesn't have? Start over. The template is supposed to help but becomes a constraint.
**Opportunity**: Content-driven layout assignment that adapts to what the user needs, not what the template allows.

### The Generic Content Problem
**Who suffers**: Gamma, Tome, SlidesAI
**The issue**: AI generates plausible-sounding but generic content. "Our solution leverages cutting-edge technology to..." — this is filler, not communication. No real data, no specific claims, no actual substance.
**Opportunity**: Generation pipeline with a Research role that pulls real data, uses specific numbers, and produces content that sounds like a human expert wrote it.

### The Design Illiteracy Problem
**Who suffers**: Google Slides, PowerPoint, most AI generators
**The issue**: Tools give users design freedom but no design intelligence. Users create slides with 8 font sizes, inconsistent colors, center-aligned everything, and walls of text. The tool doesn't stop them.
**Opportunity**: Design intelligence that enforces good design rules automatically — proper hierarchy, consistent spacing, intentional color usage — while still allowing user control.

### The Narrative Blindness Problem
**Who suffers**: All template-based tools, most AI generators
**The issue**: Each slide is treated as an independent unit. There's no concept of narrative flow, story arc, or how slides connect. The deck is a collection of slides, not a story.
**Opportunity**: Generation pipeline with a Strategist role that plans the narrative before generating any slides, ensuring every slide serves the story.

### The Sandbox Gap
**Who suffers**: Gamma, Tome, SlidesAI
**The issue**: AI generates the deck, but editing is limited. Users can tweak text but can't truly redesign a slide. There's no real canvas — just a glorified text editor with some formatting options.
**Opportunity**: Full sandbox editor where AI-generated slides can be freely modified — move elements, change layouts, adjust design — with the same power as a design tool.

### The Export Fidelity Problem
**Who suffers**: Gamma, Tome, Chronicle
**The issue**: Web-based presentations look great in the browser but export to PPTX as broken layouts. Investors often need PPTX files. If export is broken, the tool is useless for real fundraising.
**Opportunity**: Inch-based DSL that maps 1:1 to PPTX coordinates, ensuring what you see is what you export.

## Analysis Procedure

When the founder needs to research a competitor:

1. **Identify the competitor** and which tier they belong to
2. **Evaluate across all 6 dimensions** above — don't cherry-pick
3. **Focus on their generation pipeline** (if AI-powered) — how do they turn input into slides?
4. **Test their output quality** — generate a pitch deck and assess against the Pitch Deck Research skill's quality criteria
5. **Identify their #1 strength** — what would a user miss if they switched away?
6. **Identify their #1 weakness** — what frustration drives users to look for alternatives?
7. **Map to our opportunity** — how does our product address their weakness?
8. **Document with evidence** — screenshots, specific examples, not vague claims

## Positioning Framework

### Our Unique Value Proposition
The product is the ONLY tool that combines:
1. **Deep generation intelligence** (4-role pipeline: Strategist → Researcher → Composer → Critic)
2. **Real-time sandbox editing** (move, resize, restyle any element freely)
3. **Pitch deck specialization** (knows investor expectations, YC patterns, narrative frameworks)
4. **Export fidelity** (inch-based DSL ensures PPTX output matches the editor 1:1)

### Where We Don't Compete (Intentionally)
- General design tool (not competing with Figma/Canva's full design suite)
- Document editor (not competing with Notion/Google Docs)
- Video presentations (not competing with Loom/mmhmm)
- Whiteboarding (not competing with Miro/FigJam)

Focus wins. We do ONE thing — generate and edit high-quality presentations — better than anyone.

## Research Methods

When doing competitive analysis:
- **Use the web tool** to fetch current product pages and documentation
- **Check public GitHub repos** for open-source presentation tools and their approaches
- **Read product reviews** on G2, Capterra, ProductHunt for real user friction points
- **Study their changelogs** to understand where they're investing development effort
- **Watch demo videos** (YouTube) to understand the actual UX flow, not just marketing claims
