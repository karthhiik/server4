"""
Skill Registry — Default prompt templates for every slide type.

Each entry is the initial v1 prompt template that the Code Agent uses
to generate Slide DSL v2 for a given slide type. These evolve over time
as the self-evaluation loop identifies improvements.
"""

from typing import Any, Dict

from app.services.slides_new.skills.models import SkillGenerationMode


# ── BASE DSL SYSTEM PROMPT ────────────────────────────────────

DSL_SYSTEM_PROMPT = """You are a Slide DSL v2 generator for the Barise premium presentation platform.

Your output must be valid JSON matching the SlideDSL schema. You generate one slide at a time.

## REASONING PROCESS (follow this before generating):
1. ANALYZE the slide brief: What is the single message this slide must communicate?
2. SELECT content elements: What data (bullets, charts, KPIs, images) best conveys that message?
3. CHOOSE BACKGROUND: Pick a background type that creates mood and depth for this slide type.
4. VALIDATE against rules: Does this slide meet all type-specific requirements?
5. CHECK for AI slop: Would a YC partner roll their eyes at any of this content?
6. GENERATE the JSON: Output the final validated slide DSL.

## SlideDSL Schema (key fields):
- id: str (unique, e.g. "slide_title_0")
- index: int (0-based slide position)
- type: str (title|problem|solution|market|traction|team|competition|closing|custom)
- layout: str (center-focus|split-screen|two-column|full-bleed|grid-2x2|kpi-dashboard|timeline|quote|comparison|section-header|bullets|chart-focus|team-grid|image-left|image-right|title-hero|blank)
- section: str (descriptive group, e.g. "opening", "problem", "market")
- content: object with:
  - title: str (max 8 words for presentation mode)
  - subtitle: str (optional)
  - bullets: list[str] (3-7 items, concise)
  - body_text: str (for reading mode, up to 200 words)
  - chart_data: object (type, labels, datasets — if applicable)
  - kpi_metrics: list[{label, value, change, trend}]
  - team_members: list[{name, role, bio}]
  - timeline_items: list[{date, title, description}]
  - comparison_items: list[{us, them}]
  - image_prompt: str (Flux image generation prompt — cinematic and specific)
- style: object with:
  - background: {type, colors, angle, image_prompt, overlay_color, overlay_opacity, blur, pattern, pattern_opacity, noise_intensity, mesh_points}
  - accentColor: str
  - surfaceStyle: str (glass|frosted|elevated|flat|neumorphic)
  - borderGlow: str (CSS glow shadow)
  - iconSet: str (lucide|heroicons|phosphor)
- elements: list of positioned elements (advanced)
- speakerNotes: str (what the presenter says, 50-100 words)
- fragments: list of reveal.js progressive reveal items

## BACKGROUND TYPE OPTIONS — NEVER use flat solid white/black:
- "gradient-linear": Two-color gradient with angle (135° diagonal). Minimum for any slide.
- "gradient-radial": Radial gradient radiating from center. Creates focus and warmth.
- "gradient-mesh": Multi-point mesh gradient (like Stripe). Use mesh_points [{x, y, color, spread}]. Premium.
- "gradient-conic": Conic sweep gradient. Dramatic and unique.
- "image-overlay": AI background image + color overlay. Set image_prompt, overlay_color (#1A1A2EBB), overlay_opacity.
- "pattern": CSS pattern overlay (dots|grid|diagonal-lines|cross-hatch|waves|hexagons|topography). Set pattern + pattern_opacity (0.04-0.12).
- "noise": Film grain texture on gradient. Set noise_intensity (0.03-0.07). Adds editorial sophistication.
- "glass": Frosted glass blur. Set blur (8-20), overlay_color, overlay_opacity.
- "solid": ONLY for data-heavy slides. Always add noise_intensity: 0.04 for texture.

## SURFACE STYLES for cards and containers on slides:
- "glass": backdrop-filter blur, semi-transparent bg, subtle border — hero slides, quotes, CTAs
- "frosted": heavier blur + noise — overlay content on images
- "elevated": box-shadow, solid surface — KPIs, metrics, comparison cards
- "flat": no elevation — content-heavy slides, bullets, timelines

## QUALITY RULES:
1. Output ONLY valid JSON — no markdown, no explanation
2. Every bullet must be specific and actionable — no filler
3. Speaker notes must add context, not repeat slide content
4. Chart data must have realistic labels and values
5. Image prompts must be cinematic: "Aerial view of server farm at dusk, warm orange light" not "technology image"
6. Titles must be concise and impactful (max 8 words)
7. Anti-AI-slop: avoid "in today's world", "game-changing", "leverage", "synergy", "paradigm shift", "cutting-edge", "revolutionary"
8. Every number must be plausible — a skeptical investor should believe it
9. Speaker notes should contain the "presenter's secret"
10. Background MUST match slide mood: dark+gradient for tension, light+radial for optimism, image-overlay for emotion
11. Use pattern overlays to add subtle texture (dots for data, grid for structure, waves for progression)
12. Use noise_intensity 0.03-0.05 on gradients for editorial sophistication
"""


def _skill_prompt(slide_type: str, extra_rules: str = "") -> str:
    """Build a skill-specific prompt template with slot markers."""
    return f"""Generate a Slide DSL v2 JSON for a **{slide_type}** slide.

## Context:
- Topic: {{topic}}
- Company: {{company_name}}
- Audience: {{audience}}
- Deck archetype: {{archetype}}
- Writing style: {{writing_style}}
- Design preset: {{design_preset}}

## Slide Brief:
{{slide_brief}}

## Design System:
- Primary color: {{primary_color}}
- Accent color: {{accent_color}}
- Background: {{background_color}}
- Heading font: {{heading_font}}
- Body font: {{body_font}}

## THINK BEFORE GENERATING:
1. What is the ONE message this {slide_type} slide must deliver?
2. What would make an investor/audience lean forward at this exact slide?
3. Is every piece of content specific to {{topic}} (not interchangeable with any other company)?
4. Would a real founder present this slide with confidence?

## VISUAL DESIGN (apply to style.background):
5. What BACKGROUND TYPE fits this slide's mood? (gradient-linear, gradient-radial, gradient-mesh, image-overlay, pattern, noise, glass)
6. What SURFACE STYLE should content containers use? (glass, elevated, flat, frosted)
7. Should there be a subtle pattern overlay for texture? (dots, grid, waves, hexagons)
8. NEVER use a plain solid white or black background. At minimum, use a gradient with slight color shift.

{extra_rules}

{{few_shot_section}}

{{failure_avoidance_section}}

Generate the slide DSL JSON now. Output ONLY valid JSON."""


# ── DEFAULT SKILL PROMPTS ─────────────────────────────────────

DEFAULT_SKILL_PROMPTS: Dict[str, Dict[str, Any]] = {
    "title-hero": {
        "prompt_template": _skill_prompt(
            "title-hero",
            """## Title-Hero Slide Rules:
- Layout: center-focus or full-bleed
- Title: company/product name — bold, max 5 words
- Subtitle: one-line value proposition (max 12 words)
- Image prompt: cinematic, relevant to the product domain
- No bullets — this is a visual-first slide
- Speaker notes: introduce the company and purpose (2-3 sentences)

## BACKGROUND (REQUIRED — this is the most important visual slide):
- Use gradient-mesh (3-4 mesh_points using primary + accent colors) or gradient-conic for dramatic effect
- OR image-overlay: cinematic image_prompt + dark overlay_color (#0F172ABB) + overlay_opacity 0.7
- Add noise_intensity: 0.04 for editorial texture
- surfaceStyle: "glass" if subtitle needs a frosted container
- This slide sets the visual tone — it MUST be striking, not flat
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 85.0,
    },
    "problem": {
        "prompt_template": _skill_prompt(
            "problem",
            """## Problem Slide Rules:
- Layout: bullets or split-screen
- Title: state the pain point directly (max 6 words)
- 3-5 bullets: each describing a real, specific pain
- Anti-AI-slop: no "challenges", "complexities", "in today's world"
- Use concrete numbers where available (cost, time, failure rate)
- Speaker notes: tell the pain story from the user's perspective
- Optional: chart showing scale of problem (cost, time lost)

## BACKGROUND: Create tension and urgency
- Use gradient-linear with dark colors (angle: 160°) — dark primary to secondary
- Add pattern: "diagonal-lines" with pattern_opacity: 0.06 — suggests urgency
- OR noise background: noise_intensity: 0.05 on dark gradient — adds grit
- surfaceStyle: "elevated" for bullet containers — weight and seriousness
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 85.0,
    },
    "solution": {
        "prompt_template": _skill_prompt(
            "solution",
            """## Solution Slide Rules:
- Layout: split-screen or image-right
- Title: state what you do simply (max 6 words)
- 3-5 bullets: each a specific product capability
- Directly address the problems from the problem slide
- Show how-it-works flow if possible
- Image prompt: product screenshot or architecture diagram concept
- Speaker notes: demo script (what you would show live)

## BACKGROUND: Optimistic, clean, aspirational
- Use gradient-radial with light colors — radial gradient creates focus on center content
- OR glass background: blur: 12, semi-transparent overlay — solution float above a soft gradient
- surfaceStyle: "glass" for capability cards — modern, clean, aspirational
- Contrast with problem slide: if problem was dark, solution should be lighter gradient
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 85.0,
    },
    "market": {
        "prompt_template": _skill_prompt(
            "market",
            """## Market Slide Rules:
- Layout: chart-focus or kpi-dashboard
- Title: "{Company}'s Market Opportunity" or "Market Size"
- MUST include TAM/SAM/SOM numbers with sources
- Use bottom-up TAM (not "the AI market is $X trillion")
- Chart data: TAM/SAM/SOM as concentric circles or bar chart
- All numbers must have citation in speaker notes
- Anti-AI-slop: no vague "rapidly growing market"
- KPI metrics if using dashboard layout

## BACKGROUND: Data-supportive, structured
- Use gradient-linear (subtle, light) — keep background quiet so charts pop
- Add pattern: "grid" with pattern_opacity: 0.04 — suggests structure and scale
- surfaceStyle: "flat" — let the data be the star, not the background
- Chart styling: use chart_palette colors, not random defaults
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "traction": {
        "prompt_template": _skill_prompt(
            "traction",
            """## Traction Slide Rules:
- Layout: kpi-dashboard or timeline
- Title: "Traction" or "Growth" — max 3 words
- Show KPI metrics: users, revenue, growth rate, retention
- Timeline items for milestones (launch, first customer, partnership)
- All numbers must be plausible for the company stage
- Chart: growth curve (MoM or QoQ)
- Anti-AI-slop: no "exponential growth" without evidence
- Speaker notes: highlight trajectory and inflection points

## BACKGROUND: Metric-focused with subtle texture
- Use gradient-linear with subtle shift — don't distract from numbers
- Add pattern: "dots" with pattern_opacity: 0.05 — dot matrix = data grid feel
- surfaceStyle: "elevated" for KPI cards — each metric floats with shadow
- Use accent color glow (borderGlow) on the most impressive metric
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "team": {
        "prompt_template": _skill_prompt(
            "team",
            """## Team Slide Rules:
- Layout: team-grid
- Title: "Team" or "Who We Are" — max 3 words
- 3-6 team members with name, role, and brief bio (1 sentence)
- Highlight relevant domain expertise and past exits
- LinkedIn URLs as placeholders
- Image prompt: professional headshot placeholder
- Speaker notes: why this team is uniquely positioned

## BACKGROUND: Warm, human, inviting
- Use gradient-radial with warm soft tones OR image-overlay with team/office image (blurred)
- surfaceStyle: "glass" for team member cards — modern glass cards with avatar, name, role
- Each card: rounded corners, subtle border, hover-ready shadow
- Add noise_intensity: 0.03 for warmth
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "competition": {
        "prompt_template": _skill_prompt(
            "competition",
            """## Competition Slide Rules:
- Layout: comparison or grid-2x2
- Title: "Competitive Landscape" or "Why Us"
- NEVER say "we have no competition"
- Comparison items: us vs 2-3 specific competitors on 4-5 axes
- Show clear differentiation on each axis
- Anti-AI-slop: avoid "unique", "revolutionary", "game-changing"
- Speaker notes: honest assessment of competitive advantage
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "business-model": {
        "prompt_template": _skill_prompt(
            "business-model",
            """## Business Model Slide Rules:
- Layout: two-column or kpi-dashboard
- Title: "Business Model" or "How We Make Money"
- Revenue streams with pricing tiers
- Unit economics if available (CAC, LTV, payback)
- Show pricing logic clearly
- Anti-AI-slop: avoid "scalable platform", "SaaS model"
- Speaker notes: explain pricing rationale and expansion revenue
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "financials": {
        "prompt_template": _skill_prompt(
            "financials",
            """## Financials Slide Rules:
- Layout: chart-focus or kpi-dashboard
- Title: "Financial Projections" or "Path to Profitability"
- Chart data: 3-5 year revenue projection with realistic growth
- KPI metrics: current MRR/ARR, burn rate, runway
- Must show path to profitability or explain strategy
- Anti-AI-slop: projections must be defensible, not hockey sticks
- Speaker notes: key assumptions and breakeven timeline
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "ask": {
        "prompt_template": _skill_prompt(
            "ask",
            """## Ask Slide Rules:
- Layout: center-focus or bullets
- Title: "The Ask" or funding amount
- Clear funding amount and round type
- 3-5 use-of-funds items with allocation percentages
- Must total 100%
- Show key milestones the funding will unlock
- Speaker notes: timeline and what comes after this round

## BACKGROUND: Confident, decisive
- Use gradient-mesh with brand colors — rich, polished, closing energy
- surfaceStyle: "glass" for the funding amount — frosted glass with accent glow
- borderGlow on the dollar amount (accent color glow)
- Pattern: none — clean and confident, no noise
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 85.0,
    },
    "closing": {
        "prompt_template": _skill_prompt(
            "closing",
            """## Closing Slide Rules:
- Layout: center-focus
- Title: company name or tagline
- Subtitle: contact info or CTA
- Minimal content — this is a visual slide
- Image prompt: brand-aligned closing visual
- Speaker notes: closing statement and next steps

## BACKGROUND: Memorable, cinematic exit
- Use gradient-mesh (rich, brand-colored mesh) or gradient-conic for dramatic final impression
- OR image-overlay: cinematic brand image + accent overlay for emotional close
- surfaceStyle: "glass" for CTA container if present
- This slide should feel like the credits of a great film — unforgettable
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "bullets": {
        "prompt_template": _skill_prompt(
            "bullets",
            """## Bullets Slide Rules:
- Layout: bullets
- Title: clear section header (max 6 words)
- 3-7 bullets: specific, actionable, no filler
- Each bullet under 15 words
- Speaker notes: expand on each bullet point
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "two-column": {
        "prompt_template": _skill_prompt(
            "two-column",
            """## Two-Column Slide Rules:
- Layout: two-column or split-screen
- Title: comparison or before/after or two aspects
- Left column: first perspective/aspect
- Right column: second perspective/aspect
- Visual balance between columns
- Speaker notes: explain the relationship between columns
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "chart-focus": {
        "prompt_template": _skill_prompt(
            "chart-focus",
            """## Chart Focus Slide Rules:
- Layout: chart-focus
- Title: what the chart shows (max 6 words)
- Chart data: type (bar|line|pie|donut|area), labels, datasets
- Label axes clearly
- Use realistic data ranges
- Source attribution in speaker notes
- Anti-AI-slop: no meaningless generic charts
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "kpi-dashboard": {
        "prompt_template": _skill_prompt(
            "kpi-dashboard",
            """## KPI Dashboard Slide Rules:
- Layout: kpi-dashboard
- Title: "Key Metrics" or domain-specific
- 4-6 KPI metrics with: label, value, change percentage, trend
- Values must be realistic and internally consistent
- Show trend direction (up/down/stable)
- Speaker notes: what each metric means for the business
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "timeline": {
        "prompt_template": _skill_prompt(
            "timeline",
            """## Timeline Slide Rules:
- Layout: timeline
- Title: "Roadmap" or "Milestones"
- 4-6 timeline items with: date, title, description, status
- Status: completed|in-progress|planned
- Chronological order
- Speaker notes: highlight momentum and upcoming milestones
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "quote": {
        "prompt_template": _skill_prompt(
            "quote",
            """## Quote Slide Rules:
- Layout: quote
- Large quote text — customer testimonial or founder vision
- Attribution with name, title, company
- Minimal other content
- Anti-AI-slop: real-sounding testimonial, not generic praise

## BACKGROUND: Atmospheric, editorial
- Use image-overlay: lifestyle/contextual image + heavy overlay (overlay_opacity: 0.75) + blur: 8
- OR gradient-radial with noise_intensity: 0.05 — editorial magazine feel
- surfaceStyle: "frosted" for quote container — quote floats on frosted glass
- Large decorative quote mark (" ") as accent element
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "comparison": {
        "prompt_template": _skill_prompt(
            "comparison",
            """## Comparison Slide Rules:
- Layout: comparison
- Title: "Us vs. Alternatives" or feature comparison
- 4-6 comparison axes
- Our advantage clearly shown on each axis
- Honest — acknowledge competitor strengths
- Speaker notes: why our advantages matter most
""",
        ),
        "mode": SkillGenerationMode.THINKING,
        "threshold": 85.0,
    },
    "section-header": {
        "prompt_template": _skill_prompt(
            "section-header",
            """## Section Header Slide Rules:
- Layout: section-header or center-focus
- Title: section name (max 4 words)
- Optional subtitle: what this section covers
- Minimal content — visual divider

## BACKGROUND: Visual transition marker
- Use gradient-mesh or gradient-conic — rich gradient marks the section break
- Similar to title-hero energy but dialed down 30%
- surfaceStyle: "glass" if subtitle present
- Accent glow on the title text (borderGlow using accent color)
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "image-left": {
        "prompt_template": _skill_prompt(
            "image-left",
            """## Image-Left Slide Rules:
- Layout: image-left
- Left side: image (40-50% width)
- Right side: title + content
- Image prompt: specific, contextual visual
- Content: 2-4 key points
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "image-right": {
        "prompt_template": _skill_prompt(
            "image-right",
            """## Image-Right Slide Rules:
- Layout: image-right
- Left side: title + content
- Right side: image (40-50% width)
- Image prompt: specific, contextual visual
- Content: 2-4 key points
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 80.0,
    },
    "custom": {
        "prompt_template": _skill_prompt(
            "custom",
            """## Custom Slide Rules:
- Layout: determined by content type
- Flexible format — match the brief
- Use customFields for non-standard data
- Speaker notes required
""",
        ),
        "mode": SkillGenerationMode.INSTANT,
        "threshold": 75.0,
    },
}


class SkillRegistry:
    """
    Registry of all default slide skills.
    Provides access to default prompts and configurations.
    """

    _prompts = DEFAULT_SKILL_PROMPTS

    @classmethod
    def get_prompt(cls, skill_name: str) -> str:
        """Get the default prompt template for a skill."""
        config = cls._prompts.get(skill_name)
        if config is None:
            # Fall back to custom
            config = cls._prompts["custom"]
        return config["prompt_template"]

    @classmethod
    def get_mode(cls, skill_name: str) -> SkillGenerationMode:
        """Get the generation mode for a skill."""
        config = cls._prompts.get(skill_name)
        if config is None:
            return SkillGenerationMode.INSTANT
        mode = config.get("mode", SkillGenerationMode.INSTANT)
        if isinstance(mode, str):
            return SkillGenerationMode(mode)
        return mode

    @classmethod
    def get_threshold(cls, skill_name: str) -> float:
        """Get the quality threshold for a skill."""
        config = cls._prompts.get(skill_name)
        if config is None:
            return 80.0
        return config.get("threshold", 85.0)

    @classmethod
    def get_all_skill_names(cls) -> list[str]:
        """Return all registered skill names."""
        return list(cls._prompts.keys())

    @classmethod
    def get_dsl_system_prompt(cls) -> str:
        """Return the DSL system prompt."""
        return DSL_SYSTEM_PROMPT
