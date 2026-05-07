"""
Advanced Prompt Builder — Nano-Banana-quality prompt engineering for image generation.

Generates rich, narrative scene descriptions (not keyword lists) optimized per
provider. Applies Nano Banana best practices from Google's Gemini image docs:
  1. Describe scenes narratively — a paragraph beats a keyword list
  2. Be hyper-specific: materials, textures, lighting setups, camera angles
  3. Use photography/cinematography terms: softbox, three-point lighting, bokeh,
     depth-of-field, macro, wide-angle, f/2.8, 85mm
  4. Specify composition: rule of thirds, negative space, focal point placement
  5. Include atmosphere/mood: color temperature, ambient FX, atmospheric haze
  6. Use "semantic negative prompts": describe what you want positively
  7. Provider-tuned structure: Flux → rich narrative, SD3 → structured, CF → focused

Supports 8 built-in themes, 6 image intents, 4 provider formats.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.models.dsl_v2 import LayoutType, SlideType


# ── Image intent classification ──────────────────────────────────

class ImageIntent(str, Enum):
    """What kind of image the slide needs."""
    HERO_BACKGROUND = "hero_background"
    CONTENT_ILLUSTRATION = "content_illustration"
    DATA_CONTEXT = "data_context"
    CREATIVE_ARTISTIC = "creative_artistic"
    TEAM_PORTRAIT = "team_portrait"
    PRODUCT_SHOWCASE = "product_showcase"


@dataclass
class PromptContext:
    """Full context for building an image prompt."""
    title: str = ""
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    speaker_notes: str = ""
    slide_type: str = "custom"
    layout: str = "bullets"
    theme_id: str = ""
    primary_color: str = "#2563eb"
    accent_color: str = "#7c3aed"
    variant: str = "dark"  # "dark" or "light"
    company_name: str = ""
    industry: str = ""
    slide_index: int = 0
    total_slides: int = 12
    custom_prompt: Optional[str] = None  # User-provided override


# ── Theme style map (enriched with Nano Banana-level detail) ─────
# Each theme includes narrative style, lighting setup, material/texture,
# camera guidance, and negative keywords for SD3/Phoenix.

_THEME_STYLE_MAP = {
    "tech-neon": {
        "style": (
            "A dark, moody cyberpunk environment with deep indigo and midnight-black tones. "
            "Sharp neon accent lines in electric blue and magenta trace along geometric "
            "circuit-board patterns. Surfaces are polished obsidian and brushed dark steel "
            "with subtle holographic reflections"
        ),
        "lighting": (
            "dramatic rim lighting from behind casting neon edge glow, volumetric light "
            "rays cutting through atmospheric haze, point lights with cyan and magenta "
            "color temperatures, strong contrast between deep shadows and vivid highlights"
        ),
        "texture": "brushed titanium, frosted glass panels, micro-LED dot matrix, liquid crystal surfaces",
        "camera": "low-angle wide shot, 24mm lens, f/2.8, shallow depth-of-field on foreground elements",
        "mood": "energetic, innovative, cutting-edge, futuristic",
        "avoid": "nature, organic, vintage, warm tones, rustic, pastoral",
    },
    "startup-gradient": {
        "style": (
            "A contemporary Silicon Valley aesthetic with smooth gradient washes flowing "
            "between warm coral, electric violet, and sky blue. Clean geometric shapes "
            "float in space — rounded rectangles, soft circles, gentle arcs. Everything "
            "feels fresh, optimistic, and digitally native"
        ),
        "lighting": (
            "soft diffused overhead lighting with warm-to-cool gradient transitions, "
            "subtle ambient occlusion on floating elements, gentle shadow casting "
            "suggesting morning sunlight through a modern glass office"
        ),
        "texture": "smooth matte finishes, soft-touch plastic, frosted acrylic, subtle grain overlay",
        "camera": "eye-level centered shot, 50mm lens, f/4, clean depth with soft background blur",
        "mood": "optimistic, disruptive, forward-thinking, youthful energy",
        "avoid": "corporate, traditional, muted, dark, heavy, ornate, classical",
    },
    "minimal-mono": {
        "style": (
            "An ultra-minimalist composition with vast expanses of white negative space. "
            "A single carefully placed subject anchors the frame. Palette is restricted to "
            "pure white, warm gray, and a single deliberate accent. The design follows "
            "strict grid alignment with generous breathing room"
        ),
        "lighting": (
            "large key softbox from above-right creating gentle, even illumination with "
            "barely perceptible shadows. High-key lighting setup with reflector fill. "
            "Clean, shadow-free background with subtle gradient from white to warm ivory"
        ),
        "texture": "smooth matte paper, fine linen, uncoated stock, negative space as design element",
        "camera": "straight-on centered shot, 85mm lens, f/5.6, tack-sharp focus, ample negative space",
        "mood": "refined, focused, sophisticated, serene clarity",
        "avoid": "cluttered, colorful, noisy, busy patterns, heavy textures, vibrant colors",
    },
    "corporate-blue": {
        "style": (
            "A polished executive boardroom aesthetic. Deep navy and steel-blue tones "
            "paired with crisp white and brushed silver accents. Architecture features "
            "clean glass facades, precision-machined metal, and subtle pinstripe patterns. "
            "The visual language communicates trust, scale, and institutional gravitas"
        ),
        "lighting": (
            "three-point professional lighting with key light at 45 degrees, subtle fill, "
            "and cool-toned backlight. Even, controlled illumination like a premium "
            "corporate photo studio. Color temperature 5500K for neutral white balance"
        ),
        "texture": "polished marble, brushed aluminum, premium bond paper, woven navy fabric",
        "camera": "slightly elevated angle, 35mm lens, f/5.6, wide depth-of-field, architectural lines",
        "mood": "authoritative, reliable, established, trustworthy, commanding",
        "avoid": "playful, informal, neon, childish, casual, messy, graffiti",
    },
    "nature-earth": {
        "style": (
            "An organic, earth-toned landscape palette drawn from terracotta clay, moss green, "
            "warm sandstone, and deep forest umber. Natural materials dominate — weathered "
            "wood grain, river stones, pressed botanical specimens, raw linen. Shapes follow "
            "organic curves inspired by geological formations and plant growth"
        ),
        "lighting": (
            "warm golden-hour sunlight filtering through canopy leaves creating dappled "
            "patterns. Soft natural illumination with long shadows. Color temperature around "
            "4000K, giving warmth to earth tones. Gentle rim light on organic edges"
        ),
        "texture": "raw wood grain, hand-pressed paper, natural stone, woven hemp, dried leaf veins",
        "camera": "eye-level natural perspective, 50mm lens, f/4, shallow focus on foreground botanicals",
        "mood": "grounded, sustainable, genuine, living, connected to nature",
        "avoid": "synthetic, neon, futuristic, plastic, chrome, digital, artificial",
    },
    "medical-clean": {
        "style": (
            "A pristine clinical environment with sterile whites, soft pharmaceutical blues, "
            "and precise mint-green accents. Surfaces are immaculate — smooth white laminate, "
            "clear borosilicate glass, polished stainless steel. Molecular structures and "
            "microscopic patterns provide subtle scientific visual interest"
        ),
        "lighting": (
            "bright, even fluorescent-style illumination without harsh shadows. Diffused "
            "overhead panel lighting at 6500K daylight balance. Clean specular highlights "
            "on glass and steel surfaces. Antiseptic clarity in every tonal range"
        ),
        "texture": "surgical-grade steel, laboratory glass, sterile polymer, micropipette precision",
        "camera": "clean centered shot, 60mm macro perspective, f/8, sharp edge-to-edge focus",
        "mood": "trustworthy, precise, clean, scientific rigor, clinical excellence",
        "avoid": "dark, gritty, organic decay, warm tones, rust, dirt, chaos",
    },
    "academic-serif": {
        "style": (
            "A scholarly atmosphere reminiscent of rare-book libraries and research archives. "
            "Warm parchment tones, rich mahogany browns, aged gold leaf, and deep burgundy. "
            "Visual elements reference antique maps, engraved illustrations, copperplate "
            "typography, and bound leather volumes with embossed covers"
        ),
        "lighting": (
            "warm tungsten desk-lamp illumination casting a concentrated pool of golden light. "
            "Rich shadows in the periphery. Candlelight warmth at 3200K. Soft vignetting "
            "creates an intimate reading atmosphere with emphasis on the center"
        ),
        "texture": "laid paper, embossed leather, gold-foil stamping, oak grain, wax-sealed envelopes",
        "camera": "slightly top-down reading desk perspective, 50mm lens, f/4, warm shallow DOF",
        "mood": "intellectual, authoritative, traditional, scholarly wisdom",
        "avoid": "flashy, modern, neon, digital, pixelated, tech, glowing, contemporary",
    },
    "creative-bold": {
        "style": (
            "A vibrant contemporary art gallery aesthetic. Saturated primary and secondary colors "
            "clash intentionally — cobalt blue against cadmium orange, magenta over chartreuse. "
            "Geometric shapes intersect at dynamic angles. Paint splatters, bold brush strokes, "
            "and collage textures create an energetic mixed-media feel"
        ),
        "lighting": (
            "high-contrast gallery spotlighting with dramatic directional beams from above. "
            "Multiple color-gelled lights create overlapping warm and cool shadows. Bold "
            "chiaroscuro on three-dimensional elements. Track lighting at various angles"
        ),
        "texture": "thick acrylic paint, textured canvas, torn paper edges, screen-print halftone dots",
        "camera": "dynamic tilted angle, 28mm wide lens, f/4, exaggerated perspective, bold framing",
        "mood": "expressive, eye-catching, innovative, unapologetic, gallery-worthy",
        "avoid": "muted, corporate, conservative, bland, monochrome, pastel, timid",
    },
}

# ── Default theme (used when theme_id not in map) ────────────────

_DEFAULT_THEME = {
    "style": (
        "A clean, contemporary professional design with balanced proportions. "
        "Modern geometric elements float against a refined gradient background. "
        "Muted jewel tones with careful color harmony"
    ),
    "lighting": (
        "soft studio lighting with key light at 45 degrees and gentle fill. "
        "Even illumination, neutral 5000K color temperature"
    ),
    "texture": "smooth matte surfaces, subtle linen grain, soft-touch materials",
    "camera": "eye-level, 50mm lens, f/4, balanced depth-of-field",
    "mood": "professional, polished, confident",
    "avoid": "cluttered, low quality, amateur, harsh, noisy",
}

# ── Slide type to image intent mapping ───────────────────────────

_SLIDE_TYPE_INTENT = {
    SlideType.TITLE_SLIDE: ImageIntent.HERO_BACKGROUND,
    SlideType.PROBLEM_SLIDE: ImageIntent.CONTENT_ILLUSTRATION,
    SlideType.SOLUTION_SLIDE: ImageIntent.PRODUCT_SHOWCASE,
    SlideType.MARKET_SLIDE: ImageIntent.DATA_CONTEXT,
    SlideType.TRACTION_SLIDE: ImageIntent.DATA_CONTEXT,
    SlideType.BUSINESS_MODEL_SLIDE: ImageIntent.CONTENT_ILLUSTRATION,
    SlideType.TEAM_SLIDE: ImageIntent.TEAM_PORTRAIT,
    SlideType.FINANCIAL_SLIDE: ImageIntent.DATA_CONTEXT,
    SlideType.COMPETITION_SLIDE: ImageIntent.DATA_CONTEXT,
    SlideType.CLOSING_SLIDE: ImageIntent.HERO_BACKGROUND,
    SlideType.CUSTOM: ImageIntent.CONTENT_ILLUSTRATION,
}

_LAYOUT_INTENT = {
    LayoutType.CENTER_FOCUS: ImageIntent.HERO_BACKGROUND,
    LayoutType.FULL_BLEED: ImageIntent.HERO_BACKGROUND,
    LayoutType.OVERLAY: ImageIntent.HERO_BACKGROUND,
    LayoutType.QUOTE: ImageIntent.CREATIVE_ARTISTIC,
    LayoutType.CHART: ImageIntent.DATA_CONTEXT,
    LayoutType.KPI_DASHBOARD: ImageIntent.DATA_CONTEXT,
    LayoutType.TEAM_GRID: ImageIntent.TEAM_PORTRAIT,
}


class AdvancedPromptBuilder:
    """
    Builds Nano-Banana-quality image generation prompts from presentation context.

    Prompt philosophy (from Google's Nano Banana guide):
      "Describe the scene, don't just list keywords. A narrative paragraph
       will almost always produce a better, more coherent image than a list
       of disconnected words."

    Provider-specific formatting:
    - Azure Flux: Rich narrative scene descriptions (~150-200 words) with
      photography terminology, material specifics, and cinematic composition.
    - Nvidia SD3: Structured prompts (~80-100 words) with clear subject,
      style, and technical camera terms. Benefits from negative prompts.
    - CF Phoenix: Focused, direct prompts (~60-80 words) with strong subject
      and style direction.
    - CF Lucid: Creative/artistic prompts (~50-70 words) emphasizing mood,
      color, and abstract qualities.
    """

    def classify_intent(self, ctx: PromptContext) -> ImageIntent:
        """Classify the image intent from slide context."""
        # Try slide type first
        try:
            slide_type = SlideType(ctx.slide_type)
            if slide_type in _SLIDE_TYPE_INTENT:
                return _SLIDE_TYPE_INTENT[slide_type]
        except ValueError:
            pass

        # Then layout
        try:
            layout = LayoutType(ctx.layout)
            if layout in _LAYOUT_INTENT:
                return _LAYOUT_INTENT[layout]
        except ValueError:
            pass

        return ImageIntent.CONTENT_ILLUSTRATION

    def build_prompt(
        self,
        ctx: PromptContext,
        provider: str = "azure-flux",
    ) -> str:
        """
        Build a Nano-Banana-quality image prompt for the given provider.

        Produces narrative scene descriptions with photography terms, material
        specifics, lighting setups, and composition guidance — not keyword lists.
        """
        # User override takes priority
        if ctx.custom_prompt:
            return self._format_for_provider(ctx.custom_prompt, ctx, provider)

        intent = self.classify_intent(ctx)
        theme = _THEME_STYLE_MAP.get(ctx.theme_id, _DEFAULT_THEME)

        # Build the full narrative prompt per provider type
        if provider == "azure-flux":
            return self._build_flux_prompt(ctx, intent, theme)
        elif provider == "nvidia-sd3":
            return self._build_sd3_prompt(ctx, intent, theme)
        elif provider == "cf-phoenix":
            return self._build_phoenix_prompt(ctx, intent, theme)
        elif provider == "cf-lucid":
            return self._build_lucid_prompt(ctx, intent, theme)

        # Fallback: Flux-style prompt truncated
        return self._build_flux_prompt(ctx, intent, theme)[:1000]

    def build_negative_prompt(self, ctx: PromptContext) -> str:
        """Build a negative prompt for SD3/Phoenix providers."""
        theme = _THEME_STYLE_MAP.get(ctx.theme_id, _DEFAULT_THEME)
        avoid = theme.get("avoid", "")

        base_negatives = [
            "text", "words", "letters", "watermark", "signature", "logo", "brand mark",
            "blurry", "out of focus", "low quality", "low resolution", "jpeg artifacts",
            "compression artifacts", "pixelated", "noise", "grain",
            "distorted", "deformed", "disfigured", "ugly", "duplicate",
            "out of frame", "poorly drawn", "bad proportions",
            "human face", "portrait of person", "selfie", "photograph of people",
            "stock photo aesthetic", "clip art", "generic business imagery",
            "oversaturated", "underexposed", "overexposed",
        ]
        if avoid:
            base_negatives.extend(a.strip() for a in avoid.split(","))

        return ", ".join(base_negatives)

    # ── Provider-specific prompt builders ─────────────────────────

    def _build_flux_prompt(
        self, ctx: PromptContext, intent: ImageIntent, theme: dict
    ) -> str:
        """
        Build a rich narrative prompt for Azure FLUX.1-Kontext-pro (~150-200 words).

        Flux excels with detailed, descriptive paragraphs. We give it a full
        cinematic scene description with lighting, materials, camera, and mood.
        """
        title = ctx.title or "professional presentation"
        content_hint = self._content_summary(ctx)
        variant_desc = "dark theme with deep shadows" if ctx.variant == "dark" else "light theme with bright, airy tones"
        color_narrative = (
            f"The color palette is anchored by {ctx.primary_color} as the dominant tone "
            f"with {ctx.accent_color} used sparingly as a highlight accent"
        )

        scene = self._scene_description(intent, title, content_hint)
        style = theme["style"]
        lighting = theme.get("lighting", "soft professional studio lighting with even illumination")
        texture = theme.get("texture", "smooth modern surfaces")
        camera = theme.get("camera", "50mm lens, f/4, balanced composition")
        mood = theme["mood"]

        prompt = (
            f"{scene}. {style}. "
            f"The scene is illuminated by {lighting}. "
            f"Surface materials include {texture}. "
            f"{color_narrative}. {variant_desc}. "
            f"Captured with a {camera}. "
            f"The overall mood is {mood}. "
            f"This is a professional presentation background in 16:9 aspect ratio "
            f"designed for a pitch deck. The image must contain absolutely no text, "
            f"no letters, no words, no logos, and no watermarks. Leave generous clear "
            f"space for overlaying presentation text. Ultra-high quality, 4K clarity, "
            f"with crisp details and professional color grading."
        )
        return prompt[:2000]

    def _build_sd3_prompt(
        self, ctx: PromptContext, intent: ImageIntent, theme: dict
    ) -> str:
        """
        Build a structured prompt for Nvidia SD3 Medium (~80-100 words).

        SD3 works best with clear, structured descriptions. Strong subject,
        camera terms, and art direction. Benefits heavily from negative prompts.
        """
        title = ctx.title or "professional presentation"
        scene_short = self._scene_short(intent, title)
        style = theme["style"]
        camera = theme.get("camera", "50mm lens, f/4")
        mood = theme["mood"]

        prompt = (
            f"{scene_short}. {style}. "
            f"Shot with {camera}. Mood: {mood}. "
            f"Color palette: {ctx.primary_color} with {ctx.accent_color} accents. "
            f"16:9 aspect ratio, professional presentation background. "
            f"No text, no letters, no logos, no watermarks, no human faces. "
            f"Leave clear space for text overlay. "
            f"High quality, sharp focus, professional grade rendering."
        )
        return prompt[:800]

    def _build_phoenix_prompt(
        self, ctx: PromptContext, intent: ImageIntent, theme: dict
    ) -> str:
        """
        Build a focused prompt for Cloudflare Phoenix (~60-80 words).

        Phoenix needs direct, clear instructions with strong subject and style.
        """
        title = ctx.title or "presentation"
        scene_core = self._scene_core(intent, title)
        mood = theme["mood"]

        prompt = (
            f"{scene_core}. "
            f"Style: {mood}, professional quality. "
            f"Colors: {ctx.primary_color} and {ctx.accent_color}. "
            f"16:9 wide format, clean composition with space for text overlay. "
            f"No text, no logos, no faces. Sharp focus, high quality render."
        )
        return prompt[:500]

    def _build_lucid_prompt(
        self, ctx: PromptContext, intent: ImageIntent, theme: dict
    ) -> str:
        """
        Build a creative/artistic prompt for Cloudflare Lucid (~50-70 words).

        Lucid excels at artistic, abstract, and texture-rich imagery.
        """
        title = ctx.title or "presentation"
        mood = theme["mood"]
        abstract_subject = self._abstract_subject(intent, title)

        prompt = (
            f"{abstract_subject} for '{title}'. "
            f"Artistic, {mood}. "
            f"Palette: {ctx.primary_color}, {ctx.accent_color}. "
            f"Wide 16:9 format. No text, no logos, no faces. "
            f"Beautiful abstract composition."
        )
        return prompt[:500]

    # ── Scene description builders (per intent, per detail level) ─

    def _scene_description(
        self, intent: ImageIntent, title: str, content_hint: str
    ) -> str:
        """Full narrative scene for Flux (richest detail)."""
        descriptions = {
            ImageIntent.HERO_BACKGROUND: (
                f"A breathtaking cinematic wide-angle background for a presentation titled '{title}'. "
                f"The scene features a sweeping panoramic environment with dramatic depth — "
                f"architectural elements recede into an atmospheric vanishing point. "
                f"The lower two-thirds of the frame contains softer, darker tones to allow "
                f"white title text to read clearly when overlaid{content_hint}. "
                f"The upper portion has more visual complexity and detail"
            ),
            ImageIntent.CONTENT_ILLUSTRATION: (
                f"A sophisticated conceptual illustration representing '{title}'. "
                f"The visual tells a story through carefully arranged symbolic elements{content_hint}. "
                f"The composition uses the rule of thirds — the primary visual interest occupies "
                f"the left third of the frame while the right two-thirds remain open and "
                f"uncluttered, providing a clean area for body text overlay. "
                f"The illustration has depth with a clear foreground, midground, and background"
            ),
            ImageIntent.DATA_CONTEXT: (
                f"An abstract visualization environment suggesting data, analytics, and "
                f"quantitative insight for '{title}'. Delicate geometric structures — "
                f"translucent grid planes, softly glowing node-and-edge networks, subtle "
                f"flowing particle streams — create a three-dimensional data landscape{content_hint}. "
                f"The composition keeps the center and right side clean for chart or text overlay "
                f"while the left side carries more visual detail"
            ),
            ImageIntent.CREATIVE_ARTISTIC: (
                f"An evocative, atmospheric abstract artwork that sets the mood for '{title}'. "
                f"Fluid organic shapes blend with soft bokeh light circles. "
                f"The scene has a dreamlike, contemplative quality — like looking through "
                f"frosted glass at distant light sources{content_hint}. "
                f"The center of the frame is intentionally soft and ambient to allow "
                f"a quote or statement to be overlaid in high contrast"
            ),
            ImageIntent.TEAM_PORTRAIT: (
                f"A dynamic, abstract representation of collaboration and teamwork for '{title}'. "
                f"Interconnected geometric forms — overlapping circles, linked nodes, converging "
                f"pathways — symbolize diverse expertise coming together. "
                f"Abstract silhouette shapes suggest human figures in motion without depicting "
                f"actual faces or identifiable people{content_hint}. "
                f"Open space in the bottom half for team member names or text"
            ),
            ImageIntent.PRODUCT_SHOWCASE: (
                f"A premium product photography environment for '{title}'. "
                f"A sleek, elevated display surface made of polished material sits in a "
                f"modern studio setting. Three-point lighting creates soft highlights and "
                f"refined shadows{content_hint}. "
                f"The background has subtle depth with an out-of-focus gradient. "
                f"The center of the frame is the natural focal point with clean space "
                f"around it for descriptive text overlay"
            ),
        }
        return descriptions.get(
            intent,
            f"A professional, polished presentation background for '{title}'{content_hint}",
        )

    def _scene_short(self, intent: ImageIntent, title: str) -> str:
        """Structured scene for SD3 (medium detail)."""
        scenes = {
            ImageIntent.HERO_BACKGROUND: (
                f"Cinematic wide-angle hero background for '{title}'. "
                f"Dramatic depth with architectural elements receding to vanishing point. "
                f"Dark lower region for text overlay, detailed upper portion"
            ),
            ImageIntent.CONTENT_ILLUSTRATION: (
                f"Conceptual illustration for '{title}'. "
                f"Symbolic elements arranged in rule-of-thirds composition. "
                f"Visual interest on left, open right for text overlay"
            ),
            ImageIntent.DATA_CONTEXT: (
                f"Abstract data visualization for '{title}'. "
                f"Translucent geometric grids, glowing node networks, flowing particles. "
                f"Clean center for chart overlay"
            ),
            ImageIntent.CREATIVE_ARTISTIC: (
                f"Atmospheric abstract artwork for '{title}'. "
                f"Fluid shapes, soft bokeh circles, dreamlike quality. "
                f"Soft center area for quote text overlay"
            ),
            ImageIntent.TEAM_PORTRAIT: (
                f"Abstract teamwork composition for '{title}'. "
                f"Interconnected geometric forms and converging pathways. "
                f"Abstract silhouettes suggesting collaboration"
            ),
            ImageIntent.PRODUCT_SHOWCASE: (
                f"Premium studio product display for '{title}'. "
                f"Elevated polished surface, three-point lighting, soft shadows. "
                f"Clean background with subtle depth"
            ),
        }
        return scenes.get(intent, f"Professional presentation background for '{title}'")

    def _scene_core(self, intent: ImageIntent, title: str) -> str:
        """Core scene for Phoenix (concise, direct)."""
        cores = {
            ImageIntent.HERO_BACKGROUND: (
                f"Cinematic hero background with dramatic depth and atmosphere for '{title}'"
            ),
            ImageIntent.CONTENT_ILLUSTRATION: (
                f"Professional conceptual illustration for '{title}' with open space for text"
            ),
            ImageIntent.DATA_CONTEXT: (
                f"Abstract data visualization with geometric grids and glowing networks for '{title}'"
            ),
            ImageIntent.CREATIVE_ARTISTIC: (
                f"Atmospheric abstract artwork with soft bokeh and dreamlike quality for '{title}'"
            ),
            ImageIntent.TEAM_PORTRAIT: (
                f"Abstract teamwork visual with interconnected shapes for '{title}'"
            ),
            ImageIntent.PRODUCT_SHOWCASE: (
                f"Premium product display environment with studio lighting for '{title}'"
            ),
        }
        return cores.get(intent, f"Professional background for '{title}'")

    def _abstract_subject(self, intent: ImageIntent, title: str) -> str:
        """Abstract/artistic description for Lucid (creative, short)."""
        subjects = {
            ImageIntent.HERO_BACKGROUND: (
                f"Sweeping cinematic abstract landscape, dramatic light and shadow"
            ),
            ImageIntent.CONTENT_ILLUSTRATION: (
                f"Elegant abstract shapes suggesting insight and knowledge"
            ),
            ImageIntent.DATA_CONTEXT: (
                f"Luminous geometric grid and flowing particle streams"
            ),
            ImageIntent.CREATIVE_ARTISTIC: (
                f"Dreamy atmospheric bokeh with fluid organic shapes"
            ),
            ImageIntent.TEAM_PORTRAIT: (
                f"Connected abstract forms suggesting unity and collaboration"
            ),
            ImageIntent.PRODUCT_SHOWCASE: (
                f"Sleek minimalist surface with premium studio lighting"
            ),
        }
        return subjects.get(intent, f"Professional abstract composition")

    # ── Helpers ───────────────────────────────────────────────────

    def _content_summary(self, ctx: PromptContext) -> str:
        """Build a brief content hint from the slide's bullets/subtitle."""
        parts = []
        if ctx.subtitle:
            parts.append(ctx.subtitle[:60])
        if ctx.bullets:
            parts.extend(str(b)[:40] for b in ctx.bullets[:3])
        if ctx.industry:
            parts.append(f"{ctx.industry} industry context")
        if not parts:
            return ""
        return f". The visual should evoke themes of {', '.join(parts)}"

    def _format_for_provider(
        self,
        prompt: str,
        ctx: PromptContext,
        provider: str,
    ) -> str:
        """Format/truncate a custom user prompt per provider constraints."""
        if provider == "azure-flux":
            return prompt[:2000]
        elif provider == "nvidia-sd3":
            return prompt[:800]
        elif provider in ("cf-phoenix", "cf-lucid"):
            return prompt[:500]
        return prompt[:1000]
