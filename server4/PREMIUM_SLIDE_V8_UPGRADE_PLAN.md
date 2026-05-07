# Premium Slide Generation — V8 Upgrade Plan
## "Think-to-Render" Architecture (Gemini/Z.ai-Level Quality)

**Version**: 8.0 — Supersedes V7.1
**Status**: Architecture Proposal — Ready for Review
**Goal**: Transform basic template-filling into a 5-layer cognitive pipeline that produces pixel-perfect, emotionally-mapped, brand-coherent slides that rival Gemini and Z.ai output quality.

---

## 1. Executive Gap Analysis: V7 vs Gemini/Z.ai

### What V7 Does Well (Keep)
| Component | Status | Quality |
|-----------|--------|---------|
| Multi-renderer pipeline (4 formats) | ✅ Implemented | Excellent architecture |
| 8-agent swarm + orchestrator | ✅ Implemented | Good coordination |
| 24 built-in themes + generative engine | ✅ Implemented | Solid foundation |
| Anti-AI-Slop processor (9 rules) | ✅ Implemented | Good detection |
| BrandDNA extractor | ✅ Implemented | Good structure |
| WCAG accessibility checker | ✅ Implemented | Standards-compliant |
| Skill versioning system | ✅ Implemented | Future-proof |
| Multi-provider LLM routing (13 models) | ✅ Implemented | Cost-optimized |

### What V7 Is Missing (Critical Gaps)

```
┌──────────────────────────────────────────────────────────────────────┐
│  GAP ANALYSIS: WHY V7 SLIDES FEEL "BASIC" vs GEMINI/Z.AI            │
│                                                                      │
│  ❌ GAP 1: No Cognitive Reasoning Layer                              │
│     V7: CEO Agent picks archetype + slide order                      │
│     Gemini: Produces Narrative Blueprint with emotional_journey,     │
│            visual_metaphors per insight, hierarchy_map               │
│     Impact: Slides lack emotional storytelling depth                 │
│                                                                      │
│  ❌ GAP 2: No Visual Weight Calculation                              │
│     V7: Fixed CSS layouts (50:50, 60:40, 33:33:33)                   │
│     Gemini: Every element gets visual_weight (0.0-1.0, sum=1.0),    │
│            pixel-perfect positioning, balance_score algorithm         │
│     Impact: Layouts feel template-y, not custom-designed             │
│                                                                      │
│  ❌ GAP 3: No Fluid Grid System                                     │
│     V7: Predefined layout rules from dict lookup                     │
│     Gemini: 12-column fluid grid, content-aware sizing, golden       │
│            ratio spacing, dynamic column distribution                │
│     Impact: Content overflows or underflows fixed layouts            │
│                                                                      │
│  ❌ GAP 4: No Emotional Narrative Mapping                            │
│     V7: All slides treated with equal visual intensity               │
│     Gemini: Per-slide emotional curve (40% → 90% → 70% → 85%)      │
│            with visual intensity matching emotion                    │
│     Impact: Presentations feel flat, no narrative arc in visuals     │
│                                                                      │
│  ❌ GAP 5: Basic Image Prompt Engineering                            │
│     V7: "Professional presentation visual for {archetype} deck"     │
│     Gemini: Color palette injection, composition rules, mood         │
│            matching, negative space directives, style references     │
│     Impact: Generated images look generic/stock-photo-like          │
│                                                                      │
│  ❌ GAP 6: No Composition Engine (z-index layers)                    │
│     V7: CSS class-based flat layout (center-focus, split-screen)    │
│     Gemini: Multi-layer z-index composition with gradient blobs,    │
│            parallax, micro-interactions, glow effects               │
│     Impact: Slides look like styled HTML, not designed presentations │
│                                                                      │
│  ❌ GAP 7: No Real-Time Delta Updates                                │
│     V7: Regenerate entire slide on any change                       │
│     Gemini: Parse intent → compute diff → apply only changed props  │
│     Impact: Slow iteration, no "vibe coding" responsiveness         │
│                                                                      │
│  ❌ GAP 8: CSS Output Lacks Premium Visual Effects                   │
│     V7: Basic flexbox/grid, solid colors, minimal shadows           │
│     Gemini: Glassmorphism, accent glows, cinematic animations,      │
│            noise textures, gradient meshes, volumetric lighting      │
│     Impact: Output looks 2020-era, not 2026-premium                 │
│                                                                      │
│  ❌ GAP 9: No Information Density Optimization                       │
│     V7: Anti-slop detects "too many bullets" but no holistic        │
│          density scoring                                             │
│     Gemini: Density score per slide (not cluttered, not empty)       │
│     Impact: Some slides overpacked, some feel empty                 │
│                                                                      │
│  ❌ GAP 10: No Visual Hierarchy Scoring                              │
│     V7: QA checks structural quality (JSON valid, text fits)        │
│     Gemini: VLM scores visual hierarchy 0-100, balance 0.0-1.0     │
│     Impact: No automated measurement of "does this look good?"      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. V8 Architecture: 5-Layer "Think-to-Render" Pipeline

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  USER PROMPT                                                        │
│  "Create a pitch deck for NeuralScale AI infrastructure startup"   │
│                                                                     │
│        │                                                            │
│        ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: COGNITIVE REASONING (The "Brain")    [NEW]        │   │
│  │  Agent: CEO Agent (upgraded)                                │   │
│  │  Model: Kimi-K2-Thinking                                    │   │
│  │  Output: NarrativeBlueprint                                 │   │
│  │  • narrative_arc, emotional_journey per slide               │   │
│  │  • key_insights with visual_metaphors + emotional_weight    │   │
│  │  • hierarchy_map (hero_message, supporting_claims, CTA)     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│        │                                                            │
│        ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: SPATIAL REASONING (The "Architect")  [NEW]        │   │
│  │  Agent: Layout Agent (upgraded)                             │   │
│  │  Model: Phi-4-reasoning-vision-15B                          │   │
│  │  Output: GeometricLayout per slide                          │   │
│  │  • 12-column fluid grid, content-aware sizing               │   │
│  │  • visual_weight per element (sum = 1.0)                    │   │
│  │  • pixel-perfect positions {x, y, width, height}            │   │
│  │  • z-index layers, balance_score (0.8-0.95 optimal)         │   │
│  │  • spacing_rhythm (8px base × 1.5 multiplier)               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│        │                                                            │
│        ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: VISUAL GENERATION (The "Artist")     [UPGRADED]   │   │
│  │  Agent: Designer Agent + Image Pipeline                     │   │
│  │  Model: flux-pro-2 / phoenix / lucid                        │   │
│  │  Output: Contextual Assets                                  │   │
│  │  • Enhanced prompts with color palette injection            │   │
│  │  • Composition rules (rule of thirds, negative space)       │   │
│  │  • Mood-matched style constraints per theme                 │   │
│  │  • Multi-resolution output per element type                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│        │                                                            │
│        ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: COMPOSITION ENGINE (The "Assembler") [NEW]        │   │
│  │  Agent: Code Agent (upgraded)                               │   │
│  │  Output: Layered Render Tree → Premium HTML/CSS             │   │
│  │  • Multi-layer z-index composition                          │   │
│  │  • Glassmorphism, gradient meshes, accent glows             │   │
│  │  • Cinematic animations (cubic-bezier easing)               │   │
│  │  • Micro-interactions (hover, parallax, glow-intensify)     │   │
│  │  • Noise textures, SVG patterns, organic shapes             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│        │                                                            │
│        ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5: QUALITY ASSURANCE (The "Critic")     [UPGRADED]   │   │
│  │  Agent: QA Agent (upgraded)                                 │   │
│  │  Model: Phi-4-reasoning-vision-15B                          │   │
│  │  Output: Multi-Dimensional Quality Report                   │   │
│  │  • Visual hierarchy score (0-100)                           │   │
│  │  • WCAG contrast: PASS/FAIL per pair                        │   │
│  │  • Balance algorithm: 0.0-1.0 (optimal 0.8-0.95)           │   │
│  │  • Anti-AI-Slop 2.0: PASS (>85% slop-free)                 │   │
│  │  • Brand consistency: % match to theme DNA                  │   │
│  │  • Information density: OPTIMAL / SPARSE / CLUTTERED        │   │
│  │  • Emotional intensity match: alignment with blueprint      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 How This Maps to Existing V7 Components

| Layer | Existing V7 Component | Upgrade Required |
|-------|----------------------|-----------------|
| Layer 1 | `agents/ceo_agent.py` | Add NarrativeBlueprint output, emotional mapping |
| Layer 2 | `agents/layout_agent.py` | Replace dict-based rules with spatial reasoning |
| Layer 3 | `agents/designer_agent.py` + image pipeline | Enhanced prompt engineering |
| Layer 4 | `renderers/reveal_compiler.py` | Multi-layer composition, premium CSS |
| Layer 5 | `quality/` + `agents/qa_agent.py` | Visual hierarchy scoring, density checks |

---

## 3. Layer 1: Cognitive Reasoning Engine (Detailed Spec)

### 3.1 New Data Model: `NarrativeBlueprint`

```python
# File: app/services/slides_new/cognitive/narrative_blueprint.py  [NEW FILE]

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum


class EmotionalIntensity(str, Enum):
    """Per-slide emotional intensity level."""
    LOW = "low"          # 20-40% — calm, informational
    MEDIUM = "medium"    # 40-60% — engaged, interested
    HIGH = "high"        # 60-80% — excited, concerned
    PEAK = "peak"        # 80-100% — urgency, triumph, call-to-action


class VisualMetaphor(BaseModel):
    """A visual concept that represents an abstract idea."""
    concept: str          # "GPU costs kill startups"
    metaphor: str         # "burning_money" / "efficiency_graph" / "rocket_launch"
    visual_mood: str      # "dramatic", "hopeful", "triumphant"
    suggested_imagery: str  # Description for image generation
    color_accent: Optional[str] = None  # Override accent color for this element


class KeyInsight(BaseModel):
    """A key message with visual and emotional context."""
    insight: str               # "GPU clusters cost $50K+/month"
    evidence_type: str         # "statistic" | "case_study" | "quote" | "comparison"
    emotional_weight: EmotionalIntensity
    visual_metaphor: VisualMetaphor
    supporting_data: Optional[str] = None  # "$50K/month average"
    audience_reaction: str     # "concern", "hope", "excitement"


class SlideEmotionalSpec(BaseModel):
    """Emotional and visual specification for a single slide."""
    slide_index: int
    slide_type: str
    target_emotion: str        # "curiosity", "concern", "hope", "excitement"
    emotional_intensity: float  # 0.0 to 1.0
    visual_intensity: str       # "minimal", "moderate", "dramatic", "cinematic"
    key_message: str            # The ONE thing audience must remember
    transition_from_previous: str  # "escalate", "relief", "pivot", "conclude"


class HierarchyMap(BaseModel):
    """What matters most in this presentation."""
    hero_message: str          # "AI infra shouldn't burn cash"
    supporting_claims: List[str]
    proof_points: List[Dict]   # {"data": "70% cost reduction", "source": "case study"}
    call_to_action: str        # "Join the $12M round"
    narrative_arc: str         # "Problem-Agitate-Solve-Prove-Ask"


class NarrativeBlueprint(BaseModel):
    """
    Layer 1 output: Complete cognitive analysis of the presentation.
    This is NOT content — it's the STRATEGY that drives all downstream layers.
    """
    narrative_arc: str
    target_audience: str
    audience_sophistication: str  # "technical", "executive", "general"
    presentation_purpose: str     # "fundraise", "sell", "educate", "inspire"

    # Per-insight analysis
    key_insights: List[KeyInsight]

    # Per-slide emotional mapping
    emotional_journey: List[SlideEmotionalSpec]

    # Information hierarchy
    hierarchy_map: HierarchyMap

    # Visual strategy
    recommended_theme_mood: str  # "futuristic_professional", "warm_corporate"
    color_strategy: str          # "high_contrast_dark", "soft_light", "brand_match"
    animation_strategy: str      # "cinematic", "subtle", "none"
```

### 3.2 CEO Agent Upgrade

```python
# Changes to: app/services/slides_new/agents/ceo_agent.py

# NEW: CEO Agent prompt now produces NarrativeBlueprint instead of basic strategy

NARRATIVE_REASONING_PROMPT = """
You are a world-class presentation strategist (Steve Jobs × McKinsey level).

USER REQUEST: {user_prompt}
CONTEXT: {context}

Do NOT generate slide content yet. REASON about the presentation:

1. NARRATIVE ARC: What storytelling structure fits best?
   Options: Problem-Agitate-Solve, Before-After, Vision-Journey,
            Challenge-Triumph, Data-Story-Ask

2. EMOTIONAL JOURNEY: Map emotional intensity per slide (0.0 to 1.0).
   Rules:
   - Never two 90%+ slides in a row (exhausting)
   - End on HIGH (not flat)
   - Curve should look like a story arc, not a flat line
   - Opening: CURIOSITY (0.4)
   - Problem: CONCERN (0.9) — peak tension
   - Solution: HOPE (0.7) — relief
   - Market: EXCITEMENT (0.85)
   - Traction: CONFIDENCE (0.85)
   - Ask: URGENCY (1.0) — peak action

3. KEY INSIGHTS: For each of the 3-5 most important messages:
   - What VISUAL METAPHOR represents this concept?
   - What's the EMOTIONAL WEIGHT (how much emphasis)?
   - What EVIDENCE supports it?

4. HIERARCHY: If audience remembers ONLY ONE thing, what is it?
   That's your hero_message. Everything else supports it.

Output as NarrativeBlueprint JSON.
"""
```

### 3.3 What Changes in the Pipeline

```
BEFORE (V7):
  CEO Agent → {archetype: "yc_seed", slides: [{index: 0, layout: "title-hero"}...]}
  (Just a list of slide types and layouts — no emotional context)

AFTER (V8):
  CEO Agent → NarrativeBlueprint {
    emotional_journey: [
      {slide_index: 0, emotion: "curiosity",   intensity: 0.4, visual: "minimal"},
      {slide_index: 1, emotion: "concern",      intensity: 0.9, visual: "dramatic"},
      {slide_index: 2, emotion: "hope",         intensity: 0.7, visual: "moderate"},
      {slide_index: 3, emotion: "excitement",   intensity: 0.85, visual: "dramatic"},
      {slide_index: 4, emotion: "urgency",      intensity: 1.0, visual: "cinematic"},
    ],
    key_insights: [
      {insight: "GPU costs kill startups",
       visual_metaphor: {concept: "cost", metaphor: "burning_money", mood: "dramatic"},
       emotional_weight: "peak"}
    ],
    hierarchy_map: {hero_message: "70% cost reduction in AI infrastructure"}
  }
  (Every downstream layer uses this blueprint for decisions)
```

---

## 4. Layer 2: Spatial Reasoning Engine (Detailed Spec)

### 4.1 New Data Model: `GeometricLayout`

```python
# File: app/services/slides_new/spatial/geometric_layout.py  [NEW FILE]

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional


class ElementPosition(BaseModel):
    """Pixel-perfect position of an element on the 1920×1080 canvas."""
    x: int = Field(ge=0, le=1920)
    y: int = Field(ge=0, le=1080)
    width: int = Field(ge=1, le=1920)
    height: int = Field(ge=1, le=1080)


class ElementTypography(BaseModel):
    """Typography spec for a text element."""
    font_family: str = "Inter"
    font_size: int = Field(ge=10, le=120)
    font_weight: int = Field(ge=100, le=900)
    line_height: float = Field(ge=0.8, le=2.5, default=1.3)
    letter_spacing: float = 0.0  # em units
    color: str = "#FFFFFF"
    text_align: str = "left"  # "left" | "center" | "right"


class ElementAnimation(BaseModel):
    """Animation spec for an element."""
    entrance: str = "fade-in"  # fade-in | slide-up | scale | cinematic-fade-in
    duration: float = 0.5
    delay: float = 0.0
    easing: str = "cubic-bezier(0.22, 1, 0.36, 1)"


class ElementInteraction(BaseModel):
    """Hover/click interaction for interactive mode."""
    hover_effect: Optional[str] = None   # "subtle_glow" | "scale_up" | "highlight"
    hover_scale: float = 1.0
    click_action: Optional[str] = None


class LayoutElement(BaseModel):
    """A single element in the geometric layout."""
    element_id: str
    element_type: str  # "typography" | "shape" | "image" | "chart" | "icon" | "accent"
    content: Optional[str] = None

    # Pixel-perfect positioning
    position: ElementPosition

    # Z-index layering
    z_index: int = Field(ge=1, le=20, default=5)

    # Visual weight (% of viewer attention this element should capture)
    visual_weight: float = Field(ge=0.0, le=1.0, default=0.1)

    # Type-specific specs
    typography: Optional[ElementTypography] = None
    animation: Optional[ElementAnimation] = None
    interaction: Optional[ElementInteraction] = None

    # Shape/accent-specific
    shape_type: Optional[str] = None  # "gradient_blob" | "circle" | "line" | "rect"
    shape_style: Optional[Dict] = None  # gradient colors, opacity, blur, etc.

    # Image-specific
    image_prompt: Optional[str] = None
    image_mask: Optional[str] = None   # "rounded-2xl" | "circle" | "blob"
    image_shadow: Optional[str] = None  # "glow-cyan" | "soft-dark" | "none"


class GeometricLayout(BaseModel):
    """
    Layer 2 output: Pixel-perfect layout specification for one slide.
    Every element has exact coordinates, visual weight, and z-index.
    """
    slide_index: int
    canvas_width: int = 1920
    canvas_height: int = 1080
    grid_system: str = "12-column-fluid"

    elements: List[LayoutElement]

    # Layout quality metrics
    spacing_rhythm: Dict = Field(default_factory=lambda: {"base_unit": 8, "multiplier": 1.5})
    balance_score: float = Field(ge=0.0, le=1.0, default=0.85)
    visual_center: Dict = Field(default_factory=lambda: {"x": 960, "y": 540})

    @field_validator("elements")
    @classmethod
    def visual_weights_sum_to_one(cls, v):
        total = sum(e.visual_weight for e in v)
        if abs(total - 1.0) > 0.05:  # Allow 5% tolerance
            # Normalize weights
            for e in v:
                e.visual_weight = e.visual_weight / total if total > 0 else 1.0 / len(v)
        return v
```

### 4.2 Layout Agent Upgrade

The current `layout_agent.py` uses a `LAYOUT_RULES` dict with fixed grid ratios. V8 replaces this with spatial reasoning:

```python
# Upgrade to: app/services/slides_new/agents/layout_agent.py

SPATIAL_REASONING_PROMPT = """
You are an award-winning visual designer (Apple Design Team level).

NARRATIVE BLUEPRINT: {blueprint}
THEME: {theme}
SLIDE TYPE: {slide_type}
SLIDE CONTENT: {content_summary}

CANVAS: 1920×1080 pixels (16:9)

Create a pixel-perfect GeometricLayout:

RULES:
1. VISUAL HIERARCHY: Assign visual_weight to each element.
   - Most important element = highest weight (0.3-0.5)
   - Least important = lowest weight (0.02-0.1)
   - All weights MUST sum to 1.0

2. EMOTIONAL INTENSITY ({emotional_intensity}):
   - LOW (0.2-0.4): Spacious layout, subtle colors, minimal accents
   - MEDIUM (0.4-0.6): Balanced content, moderate accent usage
   - HIGH (0.6-0.8): Bold typography, strong accent colors, dynamic shapes
   - PEAK (0.8-1.0): Cinematic composition, full-bleed visuals, dramatic contrast

3. SPACING (8px base unit × 1.5 multiplier):
   Margins: 80px from edges minimum
   Gutters: 32-64px between columns
   Use golden ratio (1:1.618) for aesthetic spacing

4. TYPOGRAPHY SCALE:
   Hero heading: 48-72px (weight 700-900)
   Subheading: 24-32px (weight 500-600)
   Body: 16-20px (weight 400)
   Caption: 12-14px (weight 300-400)

5. Z-INDEX LAYERS:
   Background accents: 1-3 (gradient blobs, noise textures)
   Decorative shapes: 4-6 (accent lines, circles)
   Images/charts: 5-8
   Body text: 8-10
   Headlines: 10-12

6. BALANCE: Visual center of mass should be within 5% of canvas center (960, 540)

7. CONTENT-AWARE GRID:
   Instead of fixed 50:50 or 60:40 splits, calculate proportional needs:
   - Measure content length (chars × estimated font-size)
   - Distribute columns based on content weight
   - Apply golden ratio for aesthetic proportions

8. ANTI-AI-SLOP:
   - NO centered-everything (asymmetry is intentional)
   - NO generic gradients unless theme-specific
   - Intentional negative space (>20% of canvas)

Output as GeometricLayout JSON with pixel-perfect coordinates.
"""
```

### 4.3 Fluid Grid Algorithm

```python
# File: app/services/slides_new/spatial/fluid_grid.py  [NEW FILE]

class FluidGridCalculator:
    """
    Content-aware 12-column grid system.
    Replaces fixed ratio layouts (50:50, 60:40) with dynamic distribution.
    """

    TOTAL_COLUMNS = 12
    CANVAS_WIDTH = 1920
    MARGIN = 80  # px from edges
    GUTTER = 32  # px between columns
    GOLDEN_RATIO = 1.618

    def calculate_distribution(
        self,
        content_blocks: list[dict],
        slide_type: str,
    ) -> list[dict]:
        """
        Dynamically distribute columns based on content measurement.

        content_blocks: [
          {"type": "text", "char_count": 150, "has_heading": True},
          {"type": "image", "aspect_ratio": 1.5},
          {"type": "bullets", "count": 4, "avg_length": 40},
        ]

        Returns column assignments with widths.
        """
        usable_width = self.CANVAS_WIDTH - (2 * self.MARGIN)
        total_weight = sum(self._content_weight(b) for b in content_blocks)

        assignments = []
        for block in content_blocks:
            weight = self._content_weight(block)
            proportion = weight / total_weight if total_weight > 0 else 1.0 / len(content_blocks)

            # Apply golden ratio bias for 2-column layouts
            if len(content_blocks) == 2:
                if block == content_blocks[0]:
                    proportion = self.GOLDEN_RATIO / (1 + self.GOLDEN_RATIO)  # ~0.618
                else:
                    proportion = 1.0 / (1 + self.GOLDEN_RATIO)  # ~0.382

            cols = max(1, round(proportion * self.TOTAL_COLUMNS))
            width = int(proportion * usable_width) - self.GUTTER

            assignments.append({
                "columns": cols,
                "width_px": width,
                "x_start": self.MARGIN + sum(a["width_px"] + self.GUTTER for a in assignments),
            })

        return assignments

    def _content_weight(self, block: dict) -> float:
        """Calculate how much space a content block needs."""
        if block["type"] == "text":
            return block.get("char_count", 100) * 0.01
        elif block["type"] == "image":
            return 4.0  # Images need substantial space
        elif block["type"] == "bullets":
            return block.get("count", 3) * 0.8
        elif block["type"] == "chart":
            return 5.0  # Charts need most space
        return 2.0
```

---

## 5. Layer 3: Visual Generation Engine (Detailed Spec)

### 5.1 Contextual Image Prompt Engineering

The current `SlideImagePromptBuilder` produces basic prompts. V8 upgrades this with theme-aware, composition-aware prompt engineering:

```python
# File: app/services/slides_new/visual/prompt_engineer.py  [NEW FILE]

class ContextualPromptEngineer:
    """
    Transforms generic image descriptions into Gemini-quality enhanced prompts.
    Uses theme colors, slide mood, composition needs, and brand DNA.
    """

    MOOD_MAP = {
        "electric-studio": "futuristic cyberpunk neon glow, sleek surfaces",
        "dark-developer": "minimalist terminal, monochrome with accent highlights",
        "bold-signal": "bold energetic startup vibrant, dynamic angles",
        "swiss-modern": "clean swiss international typographic, precise geometry",
        "terminal-green": "retro phosphor matrix, digital rain texture",
        "dark-botanical": "organic flowing shapes, natural growth patterns",
        "neon-cyber": "cyberpunk glitch aesthetic, holographic overlays",
        "carbon-fiber": "industrial precision, metallic surfaces, carbon weave",
    }

    COMPOSITION_RULES = {
        "hero_visual": "rule_of_thirds, subject in right third, negative space on left for text",
        "background": "abstract, full coverage, soft focus, no focal point",
        "icon": "centered, simple, clean lines, transparent background",
        "chart_bg": "subtle, low contrast, grid-like structure",
        "accent": "abstract, partial view, blurred edges, organic shape",
    }

    def enhance_prompt(
        self,
        basic_prompt: str,
        theme_colors: dict,
        slide_emotion: str,
        composition_role: str,
        brand_dna: dict = None,
    ) -> str:
        """Build a Gemini-quality enhanced prompt."""

        primary = theme_colors.get("primary", "#0F172A")
        accent = theme_colors.get("accent", "#00F5FF")
        secondary = theme_colors.get("secondary", "#7B2FF7")
        theme_name = theme_colors.get("theme_name", "").lower().replace(" ", "-")

        mood = self.MOOD_MAP.get(theme_name, "modern professional sleek")
        composition = self.COMPOSITION_RULES.get(composition_role, "balanced composition")

        # Emotion-to-visual mapping
        emotion_style = {
            "curiosity": "mysterious, intriguing, partially revealed",
            "concern": "dark, dramatic shadows, tense atmosphere",
            "hope": "warm light breaking through, ascending motion",
            "excitement": "dynamic, energetic, vibrant, motion blur",
            "confidence": "solid, grounded, powerful, heroic angle",
            "urgency": "bold, forward-leaning, countdown feeling",
        }.get(slide_emotion, "professional, modern")

        enhanced = f"""
{basic_prompt}

VISUAL STYLE CONSTRAINTS:
- Color palette: Primary {primary}, Accent {accent}, Secondary {secondary}
- Mood and atmosphere: {mood}
- Emotional tone: {emotion_style}
- Lighting: Soft volumetric with subtle rim light on key subjects
- Composition: {composition}
- Quality: 8K resolution, photorealistic or premium 3D render aesthetic
- Post-processing: Subtle grain texture, cinematic color grading
- Reference style: Premium tech product launch (Apple/NVIDIA/Tesla level)
- NO: Text in image, watermarks, clip-art, stock photo poses, generic backgrounds
- Negative space: Preserve areas for text overlay
"""

        # Inject brand DNA if available
        if brand_dna:
            enhanced += f"""
BRAND CONSTRAINTS:
- Match brand visual style: {brand_dna.get('visual_style', 'modern')}
- Density preference: {brand_dna.get('density', 'balanced')}
"""

        return enhanced.strip()
```

### 5.2 Asset Size Routing

```python
# Different element types need different image resolutions
ASSET_SIZE_MAP = {
    "hero_visual":    (1024, 1024),  # Large, high quality
    "background":     (1536, 864),   # Full slide, 16:9
    "icon":           (512, 512),    # Small, crisp
    "chart_bg":       (1280, 720),   # Medium, subtle
    "accent_shape":   (512, 512),    # Decorative, can be small
    "team_photo":     (512, 512),    # Square portrait
    "product_shot":   (1024, 768),   # Product showcase
}
```

---

## 6. Layer 4: Composition Engine (Detailed Spec)

### 6.1 Premium CSS System

The current `_layout_css()` in `reveal_compiler.py` outputs functional but basic CSS. V8 adds a premium CSS layer:

```python
# File: app/services/slides_new/renderers/premium_css.py  [NEW FILE]

class PremiumCSSGenerator:
    """
    Generates premium visual effects CSS that transforms basic slides
    into Gemini/Z.ai-level output.
    """

    def generate_premium_css(self, theme: dict, emotional_map: list) -> str:
        primary = theme.get("primary", "#7B2FF7")
        accent = theme.get("accent", "#00F5FF")
        bg = theme.get("background", "#0F172A")

        return f"""
/* ====== V8 PREMIUM EFFECTS ====== */

/* Accent glow effect on headings */
.premium-glow {{
  text-shadow: 0 0 40px {primary}40, 0 0 80px {primary}20;
}}

/* Glassmorphism card */
.glass-card {{
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3),
              inset 0 1px 0 rgba(255, 255, 255, 0.05);
}}

/* Gradient mesh background */
.gradient-mesh {{
  background:
    radial-gradient(at 20% 30%, {primary}30 0px, transparent 50%),
    radial-gradient(at 80% 70%, {accent}20 0px, transparent 50%),
    radial-gradient(at 50% 50%, {bg} 0px, transparent 100%);
  background-color: {bg};
}}

/* Noise texture overlay (subtle grain) */
.noise-overlay::after {{
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 100;
  mix-blend-mode: overlay;
}}

/* Decorative gradient blob */
.accent-blob {{
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, {primary}30 0%, transparent 70%);
  filter: blur(60px);
  pointer-events: none;
}}
.accent-blob-top-left {{
  top: -15%; left: -10%;
  width: 500px; height: 500px;
}}
.accent-blob-bottom-right {{
  bottom: -20%; right: -15%;
  width: 600px; height: 600px;
  background: radial-gradient(circle, {accent}20 0%, transparent 70%);
}}

/* Cinematic entrance animations */
@keyframes cinematic-fade-in {{
  0% {{ opacity: 0; transform: translateY(30px) scale(0.95); }}
  100% {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
@keyframes cinematic-slide-up {{
  0% {{ opacity: 0; transform: translateY(60px); }}
  100% {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes counter-tick {{
  0% {{ opacity: 0; transform: scale(0.5); }}
  50% {{ transform: scale(1.1); }}
  100% {{ opacity: 1; transform: scale(1); }}
}}

.animate-cinematic {{
  animation: cinematic-fade-in 0.8s cubic-bezier(0.22, 1, 0.36, 1) both;
}}
.animate-slide-up {{
  animation: cinematic-slide-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}}

/* Staggered entry for lists */
.stagger-children > * {{
  opacity: 0;
  animation: cinematic-slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
.stagger-children > *:nth-child(1) {{ animation-delay: 0.1s; }}
.stagger-children > *:nth-child(2) {{ animation-delay: 0.2s; }}
.stagger-children > *:nth-child(3) {{ animation-delay: 0.3s; }}
.stagger-children > *:nth-child(4) {{ animation-delay: 0.4s; }}
.stagger-children > *:nth-child(5) {{ animation-delay: 0.5s; }}
.stagger-children > *:nth-child(6) {{ animation-delay: 0.6s; }}

/* KPI counter animation */
.kpi-animated {{
  font-variant-numeric: tabular-nums;
}}
.kpi-glow {{
  text-shadow: 0 0 20px {accent}60, 0 0 40px {accent}30;
}}

/* Accent line separator */
.accent-line {{
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, {primary}, {accent});
  border-radius: 2px;
  margin: 1rem 0;
}}

/* Image glow shadow */
.image-glow {{
  box-shadow: 0 0 40px {accent}30, 0 4px 20px rgba(0,0,0,0.4);
  border-radius: 12px;
}}

/* Subtle hover interaction (for interactive mode) */
.interactive-hover {{
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}}
.interactive-hover:hover {{
  transform: scale(1.03) translateY(-2px);
  box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 0 30px {accent}20;
}}

/* Emotional intensity modifiers */
.intensity-low {{ --intensity-scale: 0.8; }}
.intensity-medium {{ --intensity-scale: 1.0; }}
.intensity-high {{ --intensity-scale: 1.15; }}
.intensity-peak {{ --intensity-scale: 1.3; }}

.intensity-high h1,
.intensity-peak h1 {{
  text-shadow: 0 0 60px {primary}50;
  letter-spacing: -0.03em;
}}
.intensity-peak .accent-blob {{
  filter: blur(40px) brightness(1.3);
}}
"""
```

### 6.2 Multi-Layer Slide Composition

```python
# Upgrade to: app/services/slides_new/renderers/reveal_compiler.py

def _compile_slide_with_layers(self, slide: SlideDSL, layout: GeometricLayout) -> str:
    """
    V8: Compile slide as multi-layer composition instead of flat HTML.

    Layer stack (bottom to top):
    z=1-3: Background accents (gradient blobs, noise textures)
    z=4-6: Decorative elements (accent lines, shapes)
    z=5-8: Visual content (images, charts)
    z=8-10: Body text, bullets
    z=10-12: Headlines
    z=100: Noise overlay (always on top)
    """
    layers = {}

    for element in layout.elements:
        z = element.z_index
        if z not in layers:
            layers[z] = []
        layers[z].append(element)

    html_parts = []

    # Render layers bottom-to-top
    for z in sorted(layers.keys()):
        for el in layers[z]:
            pos = el.position
            style = (
                f"position:absolute;"
                f"left:{pos.x}px;top:{pos.y}px;"
                f"width:{pos.width}px;height:{pos.height}px;"
                f"z-index:{z};"
            )

            if el.element_type == "accent":
                html_parts.append(self._render_accent(el, style))
            elif el.element_type == "typography":
                html_parts.append(self._render_typography(el, style))
            elif el.element_type == "image":
                html_parts.append(self._render_image(el, style))
            elif el.element_type == "chart":
                html_parts.append(self._render_chart(el, style))

    # Add noise overlay
    html_parts.append('<div class="noise-overlay"></div>')

    return "\n".join(html_parts)
```

---

## 7. Layer 5: Quality Assurance 2.0 (Detailed Spec)

### 7.1 Multi-Dimensional Quality Report

```python
# File: app/services/slides_new/quality/v8_quality.py  [NEW FILE]

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VisualHierarchyScore:
    """Does the viewer's eye follow the intended path?"""
    score: int = 0  # 0-100
    primary_element_weight: float = 0.0  # Should be 0.3-0.5
    attention_path: List[str] = field(default_factory=list)  # Element IDs in attention order
    issues: List[str] = field(default_factory=list)


@dataclass
class BalanceScore:
    """Is the visual weight evenly distributed?"""
    score: float = 0.0  # 0.0-1.0 (optimal: 0.8-0.95)
    center_of_mass: dict = field(default_factory=lambda: {"x": 960, "y": 540})
    offset_from_center: float = 0.0  # pixels
    verdict: str = "balanced"  # "balanced" | "left-heavy" | "right-heavy" | "top-heavy"


@dataclass
class InformationDensity:
    """Is the slide too crowded or too empty?"""
    verdict: str = "optimal"  # "sparse" | "optimal" | "dense" | "cluttered"
    text_area_ratio: float = 0.0  # % of canvas covered by text
    whitespace_ratio: float = 0.0  # % of canvas that's empty
    element_count: int = 0
    issues: List[str] = field(default_factory=list)


@dataclass
class EmotionalAlignment:
    """Does the slide's visual intensity match the narrative blueprint?"""
    target_intensity: float = 0.0  # From NarrativeBlueprint
    actual_intensity: float = 0.0  # Measured from visual properties
    alignment_score: float = 0.0  # 0.0-1.0
    issues: List[str] = field(default_factory=list)


@dataclass
class BrandConsistency:
    """Does the slide match the theme DNA?"""
    score: float = 0.0  # 0-100%
    color_match: float = 0.0  # % of colors matching theme palette
    typography_match: float = 0.0  # % using correct fonts
    spacing_match: float = 0.0  # % following spacing rhythm
    off_brand_elements: List[str] = field(default_factory=list)


@dataclass
class V8QualityReport:
    """
    Comprehensive quality assessment — goes far beyond V7's basic scoring.
    Each dimension is independently scored.
    """
    slide_index: int

    # V7 existing checks (keep)
    wcag_contrast_pass: bool = True
    anti_slop_score: float = 100.0  # 0 = all slop, 100 = slop-free
    anti_slop_pass: bool = True

    # V8 new checks
    visual_hierarchy: VisualHierarchyScore = field(default_factory=VisualHierarchyScore)
    balance: BalanceScore = field(default_factory=BalanceScore)
    information_density: InformationDensity = field(default_factory=InformationDensity)
    emotional_alignment: EmotionalAlignment = field(default_factory=EmotionalAlignment)
    brand_consistency: BrandConsistency = field(default_factory=BrandConsistency)

    # Overall
    overall_score: float = 0.0  # 0-100
    approved: bool = False
    rejection_reasons: List[str] = field(default_factory=list)

    def compute_overall(self):
        """Weighted combination of all quality dimensions."""
        self.overall_score = (
            (self.visual_hierarchy.score * 0.25) +
            (self.balance.score * 100 * 0.15) +
            (self.anti_slop_score * 0.20) +
            (self.emotional_alignment.alignment_score * 100 * 0.15) +
            (self.brand_consistency.score * 0.15) +
            (100.0 if self.wcag_contrast_pass else 0.0) * 0.10
        )
        self.approved = (
            self.overall_score >= 85.0
            and self.wcag_contrast_pass
            and self.anti_slop_pass
        )
```

### 7.2 Anti-AI-Slop 2.0

Extends the existing 9-rule `AntiAISlopProcessor` with additional detection:

```python
# Additions to: app/services/slides_new/design/anti_slop.py

# NEW RULES for V8:
SLOP_RULES_V2 = {
    # Existing 9 rules preserved...

    # NEW: Stock photo aesthetic detection
    "StockPhotoAesthetic": {
        "detection": "Image prompt contains: 'handshake', 'lightbulb moment', "
                     "'team celebrating', 'person pointing at screen'",
        "severity": "error",
        "fix": "Replace with abstract visualization matching theme palette",
    },

    # NEW: Centered everything syndrome
    "CenteredEverythingSyndrome": {
        "detection": "All text elements have text-align: center AND "
                     "all elements are horizontally centered",
        "severity": "warning",
        "fix": "Apply asymmetric layout with left-aligned primary text",
    },

    # NEW: Font consistency failure
    "FontConsistencyFailure": {
        "detection": "More than 2 distinct font families on one slide",
        "severity": "error",
        "fix": "Restrict to heading_font + body_font pair from theme",
    },

    # NEW: Missing visual anchor
    "MissingVisualAnchor": {
        "detection": "Slide has >3 text elements but no image, chart, or shape",
        "severity": "warning",
        "fix": "Add decorative accent, icon, or data visualization",
    },

    # NEW: Flat background syndrome
    "FlatBackgroundSyndrome": {
        "detection": "Background is a single solid color with no gradient, "
                     "texture, or decorative element",
        "severity": "info",
        "fix": "Add gradient mesh, noise overlay, or accent blob to background layers",
    },
}
```

---

## 8. Real-Time Delta Update System

### 8.1 Intent Parser

```python
# File: app/services/slides_new/editing/delta_engine.py  [NEW FILE]

class DeltaUpdateEngine:
    """
    Parse natural language edit requests into structured diffs.
    Apply only changed properties instead of full regeneration.
    """

    async def parse_intent(self, user_request: str, current_slide: dict) -> dict:
        """
        "Make the title bigger and add more drama"
        →
        {
            "action": "modify",
            "targets": [
                {"element": "headline", "changes": {"font_size": "+50%", "font_weight": 900}},
                {"element": "background", "changes": {"add_class": "intensity-peak"}},
            ],
            "add_elements": [
                {"type": "accent_blob", "position": "top-left", "style": "dramatic"},
            ]
        }
        """
        pass

    def apply_diff(self, current_html: str, diff: dict) -> str:
        """Apply only the changed properties to existing HTML."""
        # Parse current HTML
        # Apply targeted changes
        # Return updated HTML without full regeneration
        pass
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation Models (1-2 weeks)
- [ ] Create `cognitive/narrative_blueprint.py` with Pydantic models
- [ ] Create `spatial/geometric_layout.py` with Pydantic models
- [ ] Create `quality/v8_quality.py` with multi-dimensional report
- [ ] Create `spatial/fluid_grid.py` with content-aware calculator

### Phase 2: Layer 1 — CEO Agent Upgrade (1 week)
- [ ] Add `NARRATIVE_REASONING_PROMPT` to `ceo_agent.py`
- [ ] Add `NarrativeBlueprint` as structured output
- [ ] Add emotional journey mapping per slide
- [ ] Wire blueprint into Context Board

### Phase 3: Layer 2 — Layout Agent Upgrade (1-2 weeks)
- [ ] Replace `LAYOUT_RULES` dict with `SPATIAL_REASONING_PROMPT`
- [ ] Add `GeometricLayout` as structured output
- [ ] Implement visual weight calculation + balance algorithm
- [ ] Integrate `FluidGridCalculator` for content-aware sizing
- [ ] Wire geometric layout into render pipeline

### Phase 4: Layer 3 — Image Prompt Engineering (1 week)
- [ ] Create `visual/prompt_engineer.py`
- [ ] Add theme color injection into all image prompts
- [ ] Add composition rules per element role
- [ ] Add emotion-to-visual mapping
- [ ] Integrate with existing Flux/Phoenix/Lucid pipeline

### Phase 5: Layer 4 — Premium CSS + Composition (2 weeks)
- [ ] Create `renderers/premium_css.py`
- [ ] Add glassmorphism, gradient mesh, accent blob CSS
- [ ] Add cinematic animation keyframes
- [ ] Add noise texture overlay
- [ ] Upgrade `reveal_compiler.py` with multi-layer composition
- [ ] Add emotional intensity modifiers to CSS
- [ ] Add staggered entry animations for lists

### Phase 6: Layer 5 — QA 2.0 (1 week)
- [ ] Add `VisualHierarchyScore` computation
- [ ] Add `BalanceScore` algorithm
- [ ] Add `InformationDensity` checker
- [ ] Add `EmotionalAlignment` validator
- [ ] Add Anti-AI-Slop 2.0 rules
- [ ] Wire V8QualityReport into QA Agent

### Phase 7: Delta Updates + Polish (1 week)
- [ ] Create `editing/delta_engine.py`
- [ ] Add intent parser for natural language edits
- [ ] Add diff-based HTML updates
- [ ] Integration testing across all 5 layers
- [ ] Performance benchmarking (<60s for 10 slides)

**Total estimate: 8-10 weeks on top of existing V7 implementation.**

---

## 10. Files to Create / Modify

### New Files
| File | Purpose |
|------|---------|
| `app/services/slides_new/cognitive/__init__.py` | Layer 1 package |
| `app/services/slides_new/cognitive/narrative_blueprint.py` | NarrativeBlueprint models |
| `app/services/slides_new/spatial/__init__.py` | Layer 2 package |
| `app/services/slides_new/spatial/geometric_layout.py` | GeometricLayout models |
| `app/services/slides_new/spatial/fluid_grid.py` | Content-aware grid calculator |
| `app/services/slides_new/spatial/visual_weight.py` | Visual weight + balance algorithms |
| `app/services/slides_new/visual/__init__.py` | Layer 3 package |
| `app/services/slides_new/visual/prompt_engineer.py` | Contextual prompt engineering |
| `app/services/slides_new/renderers/premium_css.py` | Premium visual effects CSS |
| `app/services/slides_new/quality/v8_quality.py` | Multi-dimensional quality report |
| `app/services/slides_new/editing/__init__.py` | Delta update package |
| `app/services/slides_new/editing/delta_engine.py` | Intent parser + diff engine |

### Modified Files
| File | Change |
|------|--------|
| `agents/ceo_agent.py` | Add NarrativeBlueprint output, emotional mapping prompt |
| `agents/layout_agent.py` | Replace LAYOUT_RULES with spatial reasoning, GeometricLayout output |
| `agents/designer_agent.py` | Wire contextual prompt engineer for image requests |
| `agents/qa_agent.py` | Add V8QualityReport with all new dimensions |
| `renderers/reveal_compiler.py` | Add multi-layer composition, premium CSS integration |
| `design/anti_slop.py` | Add 5 new V2 rules |
| `orchestrator/v7_orchestrator.py` | Wire 5-layer pipeline, pass NarrativeBlueprint through layers |
| `themes/css_compiler.py` | Include premium CSS generator output |

---

## 11. Cost Impact

| Layer | Model Used | Added Cost per Deck |
|-------|-----------|-------------------|
| Layer 1 (Cognitive) | Kimi-K2-Thinking | ~$0.02 (already used, just richer prompt) |
| Layer 2 (Spatial) | Phi-4-reasoning | ~$0.03 (per-slide spatial reasoning) |
| Layer 3 (Visual) | flux-pro-2 + cf-lucid | ~$0.00 (prompt enhancement is free) |
| Layer 4 (Composition) | None (CSS generation) | $0.00 |
| Layer 5 (QA 2.0) | Phi-4-reasoning-vision | ~$0.02 (richer evaluation) |
| **Total Added** | | **~$0.07 per deck** |
| **V7 Base Cost** | | $0.35-$0.50 |
| **V8 Total** | | **$0.42-$0.57 per deck** |

The cost increase is minimal (~15%) because the primary upgrades are:
1. Richer prompts (same models, more structured output)
2. New CSS generation (zero LLM cost)
3. Better quality scoring (slightly longer QA prompts)

---

## 12. Before vs After: Concrete Example

### Title Slide: "NeuralScale"

**V7 Output (Current):**
```html
<section data-background-color="#0F172A">
  <div class="center-focus">
    <p class="tagline">Series A — $12M</p>
    <h1>NeuralScale</h1>
    <h3>AI Infrastructure for Next-Gen Models</h3>
    <p class="presenter">Jane Doe, CEO</p>
  </div>
</section>
```
Result: Text centered on dark background. Clean but BASIC. No visual depth, no glow, no personality.

**V8 Output (Upgraded):**
```html
<section data-background-color="#0F172A" class="noise-overlay intensity-medium">
  <!-- z=1: Background accent blobs -->
  <div class="accent-blob accent-blob-top-left" style="background:radial-gradient(circle,#7B2FF720,transparent);"></div>
  <div class="accent-blob accent-blob-bottom-right" style="background:radial-gradient(circle,#00F5FF15,transparent);"></div>

  <!-- z=5: Generated hero visual -->
  <div style="position:absolute;right:80px;top:200px;width:640px;height:480px;z-index:5;">
    <img src="hero_neural_001.webp" class="image-glow" style="width:100%;height:100%;object-fit:cover;border-radius:16px;" />
  </div>

  <!-- z=10: Primary content -->
  <div style="position:absolute;left:80px;top:120px;z-index:10;">
    <p class="tagline animate-cinematic" style="animation-delay:0s;color:#00F5FF;font-size:14px;text-transform:uppercase;letter-spacing:0.2em;">Series A — $12M</p>
    <h1 class="premium-glow animate-cinematic" style="animation-delay:0.2s;font-size:72px;font-weight:900;letter-spacing:-0.03em;line-height:1.05;">NeuralScale</h1>
    <div class="accent-line" style="animation-delay:0.4s;"></div>
    <h3 class="animate-cinematic" style="animation-delay:0.5s;font-size:28px;font-weight:400;color:#94A3B8;max-width:600px;">AI Infrastructure for Next-Gen Models</h3>
    <p class="animate-cinematic" style="animation-delay:0.7s;font-size:16px;opacity:0.6;margin-top:2rem;">Jane Doe, CEO</p>
  </div>

  <aside class="notes">Welcome everyone. Open with the $50K/month GPU cost problem. Emphasize timing.</aside>
</section>
```
Result: Multi-layered composition with gradient blobs, noise texture, accent glow on title, cinematic staggered animations, hero image with glow shadow, accent separator line. Feels like a DESIGNED slide, not template-filled HTML.

---

*"V7 builds correct slides. V8 builds slides that make investors lean forward."*
