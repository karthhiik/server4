"""
Code Agent - Self-Evolving React/DSL Generator (Phase 3)
Agent 5b: Generates production-ready slide content via the yoyo-evolve pipeline.

Phase 3 capabilities:
- Skill-based generation (each slide type is a learnable skill)
- DSL v2 output (validated SlideDSL Pydantic objects)
- Multi-provider routing via CodeAgentRouter
- Few-shot retrieval from ChromaDB
- Self-evaluation loop (generate -> QA -> learn -> regenerate)
- Failure pattern avoidance
- React/Tailwind compilation from DSL
"""

import json
import re
from typing import Any, Dict, List, Optional

import structlog

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)
from app.services.slides_new.agents.code_agent_router import (
    CodeAgentRouter,
    CodeTaskType,
)
from app.services.slides_new.agents.evaluation_loop import (
    EvaluationLoop,
    EvaluationResult,
)
from app.services.slides_new.dsl.dsl_generator import DSLGenerator
from app.services.slides_new.skills.skill_registry import (
    SkillRegistry,
    DEFAULT_SKILL_PROMPTS,
)
from app.services.slides_new.skills.skill_store import SkillStore

logger = structlog.get_logger()


# Slide layout to React component mapping
LAYOUT_COMPONENT_MAP = {
    "title-hero": "TitleHeroSlide",
    "title-content": "TitleContentSlide",
    "bullets": "BulletsSlide",
    "two-column": "TwoColumnSlide",
    "image-left": "ImageLeftSlide",
    "image-right": "ImageRightSlide",
    "chart-focus": "ChartFocusSlide",
    "team-grid": "TeamGridSlide",
    "kpi-dashboard": "KPIDashboardSlide",
    "timeline": "TimelineSlide",
    "quote": "QuoteSlide",
    "comparison": "ComparisonSlide",
    "section-header": "SectionHeaderSlide",
    "blank": "BlankSlide",
}


class CodeAgent(BaseAgent):
    """
    Agent 5b: Self-Evolving Code Generator (Phase 3).

    Responsibilities:
    - Load skill for each slide type (prompt, mode, few-shot examples)
    - Generate SlideDSL v2 via DSLGenerator + CodeAgentRouter
    - Run self-evaluation loop (max 3 rounds per slide)
    - Learn from success (best examples) and failure (patterns)
    - Compile DSL to React/Tailwind components
    - Write results to Context Board

    Uses multi-provider routing: DeepSeek for DSL, Qwen for React,
    GLM for reveal.js, Phi-4 for layout optimization.
    """

    DEFAULT_MODEL = "deepseek-v3"
    FALLBACK_MODELS = ["mistral-medium", "cf-qwen", "groq"]

    def __init__(self, db, context, context_board=None):
        super().__init__(db, context, context_board)
        self._code_router = CodeAgentRouter()
        self._skill_store: Optional[SkillStore] = None
        self._dsl_generator: Optional[DSLGenerator] = None
        self._eval_loop: Optional[EvaluationLoop] = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazy-init skill store, DSL generator, and eval loop."""
        if self._initialized:
            return

        # Initialize skill store with optional ChromaDB
        chroma = None
        try:
            from app.services.chromadb_service import ChromaService
            chroma = ChromaService()
        except Exception:
            logger.debug("code_agent_chromadb_unavailable")

        self._skill_store = SkillStore(db=self.db, chroma_service=chroma)
        self._dsl_generator = DSLGenerator(
            skill_store=self._skill_store,
            router=self._code_router,
        )
        self._eval_loop = EvaluationLoop(
            dsl_generator=self._dsl_generator,
            skill_store=self._skill_store,
            max_rounds=3,
            quality_threshold=85.0,
        )

        # Initialize default skills (idempotent)
        try:
            created = await self._skill_store.initialize_defaults(
                DEFAULT_SKILL_PROMPTS
            )
            if created > 0:
                logger.info("code_agent_skills_initialized", count=created)
        except Exception as e:
            logger.warning("code_agent_skill_init_error", error=str(e))

        self._initialized = True

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CODE_AGENT

    async def execute(self) -> AgentOutput:
        """
        Execute Phase 3 code generation pipeline.

        Flow:
        1. Initialize skill system
        2. Read designer + assembler output from previous agents
        3. For each slide: run evaluation loop (generate DSL -> QA -> learn)
        4. Compile passing DSL to React components
        5. Write results to Context Board
        """
        await self._ensure_initialized()

        # Get previous agent outputs
        designer_output = self.context.previous_outputs.get(AgentType.DESIGNER)
        assembler_output = self.context.previous_outputs.get(AgentType.ASSEMBLER)

        if not designer_output or not assembler_output:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                errors=["Missing designer or assembler output"],
            )

        try:
            design_system = designer_output.output.get("design_system", {})
            slides = assembler_output.output.get("slides", [])

            # Build presentation context for DSL generator
            gen_context = self._build_generation_context(design_system)

            # Process each slide through the evaluation loop
            generated_components = []
            eval_summaries = []
            total_score = 0.0

            for slide in slides:
                slide_type = self._resolve_slide_type(slide)
                slide_brief = self._extract_slide_brief(slide)

                # Run evaluation loop
                eval_result = await self._eval_loop.run(
                    slide_type=slide_type,
                    slide_brief=slide_brief,
                    context=gen_context,
                    presentation_id=self.context.task_id,
                )

                # Compile to React if we have valid DSL
                if eval_result.best_result and eval_result.best_result.dsl:
                    component = await self._compile_dsl_to_react(
                        dsl=eval_result.best_result.dsl,
                        design_system=design_system,
                    )
                    component["eval_score"] = eval_result.best_score
                    component["eval_rounds"] = eval_result.total_rounds
                    generated_components.append(component)
                else:
                    # Fallback to template generation
                    component = self._fallback_template_generation(
                        slide, design_system
                    )
                    component["eval_score"] = eval_result.best_score
                    component["eval_rounds"] = eval_result.total_rounds
                    generated_components.append(component)

                total_score += eval_result.best_score
                eval_summaries.append({
                    "slide_type": slide_type,
                    "score": round(eval_result.best_score, 1),
                    "rounds": eval_result.total_rounds,
                    "passed": eval_result.success,
                    "skill_updated": eval_result.skill_updated,
                })

            # Generate shared utilities and theme config
            shared_utils = self._generate_shared_utilities(design_system)
            theme_config = self._generate_theme_config(design_system)

            avg_score = (
                round(total_score / len(slides), 1) if slides else 0.0
            )

            # Write to Context Board
            await self._write_code_results_to_board(
                generated_components, eval_summaries, avg_score
            )

            # Get skill stats for output
            skill_stats = {}
            if self._skill_store:
                try:
                    skill_stats = await self._skill_store.get_skill_stats()
                except Exception:
                    pass

            return AgentOutput(
                success=True,
                agent_type=self.agent_type,
                output={
                    "components": generated_components,
                    "shared_utils": shared_utils,
                    "theme_config": theme_config,
                    "total_components": len(generated_components),
                    "avg_eval_score": avg_score,
                    "eval_summaries": eval_summaries,
                    "skill_stats": skill_stats,
                },
                context_board_writes=self._board_writes,
            )

        except Exception as e:
            logger.error("code_agent_error", error=str(e))
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                errors=[str(e)],
            )

    def _build_generation_context(
        self, design_system: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the context dict passed to DSLGenerator."""
        colors = design_system.get("colors", {})
        fonts = design_system.get("fonts", {})

        context = {
            "topic": self.context.topic,
            "company_name": self.context.company_name or "",
            "audience": self.context.audience,
            "archetype": self.context.metadata.get("archetype", "startup-pitch"),
            "writing_style": self.context.writing_style,
            "design_preset": self.context.selected_style_preset or "midnight",
            "primary_color": colors.get("primary", "#1A1A2E"),
            "accent_color": colors.get("accent", "#E94560"),
            "background_color": colors.get("background", "#FFFFFF"),
            "heading_font": fonts.get("heading", "DM Sans"),
            "body_font": fonts.get("body", "Inter"),
            "theme": design_system.get("theme", "light"),
            "surface_color": colors.get("surface", colors.get("background", "#FFFFFF")),
            "gradient_pairs": design_system.get("gradient_pairs", []),
            "chart_palette": design_system.get("chart_palette", []),
            "icon_style": design_system.get("icon_style", "lucide"),
        }

        # Inject learned design context from Design Memory (self-learning)
        learned_context = design_system.get("learned_context", "")
        if learned_context:
            context["_learned_design_lessons"] = learned_context

        return context

    def _resolve_slide_type(self, slide: Dict[str, Any]) -> str:
        """Map a slide dict to a skill name (slide type)."""
        # Try explicit type first
        slide_type = slide.get("type", "")
        if slide_type and slide_type in [
            "title-hero", "problem", "solution", "market",
            "traction", "team", "competition", "business-model",
            "financials", "ask", "closing",
        ]:
            return slide_type

        # Fall back to layout
        layout = slide.get("layout", "bullets")
        layout_to_type = {
            "title-hero": "title-hero",
            "center-focus": "title-hero",
            "full-bleed": "title-hero",
            "bullets": "bullets",
            "two-column": "two-column",
            "split-screen": "two-column",
            "image-left": "image-left",
            "image-right": "image-right",
            "chart-focus": "chart-focus",
            "chart": "chart-focus",
            "team-grid": "team",
            "kpi-dashboard": "kpi-dashboard",
            "timeline": "timeline",
            "quote": "quote",
            "comparison": "comparison",
            "section-header": "section-header",
        }
        return layout_to_type.get(layout, "custom")

    def _extract_slide_brief(self, slide: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a structured brief from the slide data."""
        return {
            "title": slide.get("title", ""),
            "content": slide.get("content", ""),
            "layout": slide.get("layout", "bullets"),
            "type": slide.get("type", "custom"),
            "section": slide.get("section", ""),
            "bullets": slide.get("bullets", []),
            "data": slide.get("data", {}),
            "speaker_notes": slide.get("speaker_notes", ""),
            "index": slide.get("index", 0),
        }

    async def _compile_dsl_to_react(
        self, dsl: Any, design_system: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compile a SlideDSL object into a React component."""
        layout_value = dsl.layout.value if hasattr(dsl.layout, "value") else str(dsl.layout)
        component_name = LAYOUT_COMPONENT_MAP.get(layout_value, "GenericSlide")

        # Build code generation prompt from DSL
        dsl_json = dsl.model_dump_json(indent=2)
        prompt = f"""Convert this Slide DSL into a React/TypeScript component.

## Component Name: {component_name}

## Slide DSL:
```json
{dsl_json}
```

## Design System:
```json
{json.dumps(design_system, indent=2)}
```

## Requirements:
1. TypeScript with proper type annotations
2. Tailwind CSS for all styling
3. Framer Motion for animations
4. Responsive (mobile-first)
5. WCAG AA accessible
6. Map DSL content fields to component props

Output ONLY the React component code in a ```tsx code block."""

        try:
            response = await self._code_router.generate_react(
                system_prompt=CODE_SYSTEM_PROMPT,
                user_prompt=prompt,
                presentation_id=self.context.task_id,
            )
            code = self._extract_code_from_response(response.content)
        except Exception as e:
            logger.warning(
                "react_compilation_failed",
                component=component_name,
                error=str(e),
            )
            code = self._get_fallback_react(
                component_name, dsl, design_system
            )

        return {
            "slide_id": dsl.id,
            "slide_index": dsl.index,
            "component_name": component_name,
            "layout_type": layout_value,
            "react_code": code,
            "dsl_json": dsl_json,
            "props_interface": self._generate_props_interface_from_dsl(dsl),
            "tailwind_classes": self._extract_tailwind_classes(code),
            "speaker_notes": dsl.speakerNotes or "",
        }

    def _get_fallback_react(
        self, component_name: str, dsl: Any, design_system: Dict[str, Any]
    ) -> str:
        """Generate fallback React code from DSL without LLM."""
        colors = design_system.get("colors", {})
        primary = colors.get("primary", "#1A1A2E")
        background = colors.get("background", "#FFFFFF")
        accent = colors.get("accent", "#E94560")

        title = dsl.content.title if dsl.content else "Slide"
        layout = dsl.layout.value if hasattr(dsl.layout, "value") else "bullets"

        template = FALLBACK_TEMPLATES.get(layout, FALLBACK_TEMPLATES["generic"])
        return template.format(
            component_name=component_name,
            title=title,
            content="",
            primary_color=primary,
            background_color=background,
            accent_color=accent,
        )

    def _generate_props_interface_from_dsl(self, dsl: Any) -> str:
        """Generate TypeScript interface from DSL."""
        return f"""interface SlideProps {{
  id: string;
  index: number;
  title: string;
  content: SlideContentV2;
  style: SlideStyle;
  speakerNotes?: string;
  theme: {{
    primary: string;
    secondary: string;
    accent: string;
    background: string;
  }};
  onNext?: () => void;
  onPrev?: () => void;
}}"""

    async def _write_code_results_to_board(
        self,
        components: List[Dict],
        eval_summaries: List[Dict],
        avg_score: float,
    ) -> None:
        """Write code generation results to the Context Board."""
        if self._context_board is None:
            return

        await self.write_to_board("code_agent_components", {
            "total": len(components),
            "avg_eval_score": avg_score,
            "components": [
                {
                    "slide_id": c.get("slide_id"),
                    "component_name": c.get("component_name"),
                    "layout": c.get("layout_type"),
                    "eval_score": c.get("eval_score", 0),
                }
                for c in components
            ],
        })
        await self.write_to_board("code_agent_eval_summary", {
            "avg_score": avg_score,
            "summaries": eval_summaries,
        })

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from LLM response."""
        code_pattern = r"```(?:tsx?|jsx?|javascript|typescript)?\n([\s\S]*?)```"
        matches = re.findall(code_pattern, response)
        if matches:
            return matches[0].strip()
        return response.strip()

    def _fallback_template_generation(
        self, slide: Dict[str, Any], design_system: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate component from template when LLM and eval loop fail."""
        slide_type = slide.get("layout", "title-content")
        component_name = LAYOUT_COMPONENT_MAP.get(slide_type, "GenericSlide")

        colors = design_system.get("colors", {})
        primary = colors.get("primary", "#1A1A2E")
        background = colors.get("background", "#FFFFFF")
        accent = colors.get("accent", "#E94560")

        code = FALLBACK_TEMPLATES.get(slide_type, FALLBACK_TEMPLATES["generic"])
        code = code.format(
            component_name=component_name,
            title=slide.get("title", "Slide Title"),
            content=slide.get("content", ""),
            primary_color=primary,
            background_color=background,
            accent_color=accent,
        )

        return {
            "slide_id": slide.get("id"),
            "slide_index": slide.get("index", 0),
            "component_name": component_name,
            "layout_type": slide_type,
            "react_code": code,
            "props_interface": self._generate_props_interface(slide),
            "tailwind_classes": [],
            "fallback_used": True,
        }

    def _generate_props_interface(self, slide: Dict[str, Any]) -> str:
        """Generate TypeScript interface for component props."""
        return f"""interface SlideProps {{
  id: string;
  index: number;
  title: string;
  content?: string;
  bullets?: string[];
  imageUrl?: string;
  chartData?: any;
  theme: {{
    primary: string;
    secondary: string;
    accent: string;
    background: string;
  }};
  onNext?: () => void;
  onPrev?: () => void;
}}"""

    def _extract_tailwind_classes(self, code: str) -> List[str]:
        """Extract Tailwind classes used in the component."""
        # Find all className attributes
        class_pattern = r'className=["\']([^"\']+)["\']'
        matches = re.findall(class_pattern, code)

        # Split classes and deduplicate
        all_classes = set()
        for match in matches:
            classes = match.split()
            all_classes.update(classes)

        return sorted(list(all_classes))

    def _generate_shared_utilities(self, design_system: Dict[str, Any]) -> str:
        """Generate shared utility functions and hooks."""
        return '''// Shared utilities for slide components

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence, Variants } from "framer-motion";

// Animation variants for slide transitions
export const slideVariants: Variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 1000 : -1000,
    opacity: 0,
  }),
  center: {
    zIndex: 1,
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    zIndex: 0,
    x: direction < 0 ? 1000 : -1000,
    opacity: 0,
  }),
};

// Stagger children animation
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

// Hook for keyboard navigation
export function useSlideNavigation(
  onNext: () => void,
  onPrev: () => void
) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        onNext();
      } else if (e.key === "ArrowLeft") {
        onPrev();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onNext, onPrev]);
}

// Hook for responsive sizing
export function useSlideSize() {
  const [size, setSize] = useState({ width: 1920, height: 1080 });

  useEffect(() => {
    const updateSize = () => {
      const container = document.querySelector("[data-slide-container]");
      if (container) {
        const rect = container.getBoundingClientRect();
        // Maintain 16:9 aspect ratio
        const aspectRatio = 16 / 9;
        let width = rect.width;
        let height = width / aspectRatio;
        if (height > rect.height) {
          height = rect.height;
          width = height * aspectRatio;
        }
        setSize({ width, height });
      }
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  return size;
}
'''

    def _generate_theme_config(self, design_system: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Tailwind theme configuration from design system."""
        colors = design_system.get("colors", {})
        fonts = design_system.get("fonts", {})
        spacing = design_system.get("spacing", {})

        return {
            "extend": {
                "colors": {
                    "slide": {
                        "primary": colors.get("primary", "#1A1A2E"),
                        "secondary": colors.get("secondary", "#16213E"),
                        "accent": colors.get("accent", "#E94560"),
                        "background": colors.get("background", "#FFFFFF"),
                        "text": colors.get("text", "#1A1A2E"),
                        "muted": colors.get("muted", "#6B7280"),
                    }
                },
                "fontFamily": {
                    "heading": [fonts.get("heading", "DM Sans"), "sans-serif"],
                    "body": [fonts.get("body", "Inter"), "sans-serif"],
                    "accent": [fonts.get("accent", "Space Mono"), "monospace"],
                },
                "spacing": {
                    "slide-base": f"{spacing.get('base', 8)}px",
                    "slide-tight": f"{spacing.get('tight', 4)}px",
                    "slide-loose": f"{spacing.get('loose', 16)}px",
                    "slide-section": f"{spacing.get('section', 32)}px",
                },
            }
        }


# System prompt for code generation
CODE_SYSTEM_PROMPT = """You are an elite React/TypeScript developer specializing in award-winning presentation slides.
You design slides that look like they belong in an Apple keynote, a Stripe product page, or a Linear changelog.

Your code must:
1. Be production-ready, type-safe TypeScript with strict mode
2. Use Tailwind CSS for all styling — exploit gradients, backdrop-blur, glass effects, subtle patterns
3. Use Framer Motion for fluid, purposeful animations (not gratuitous)
4. Be fully accessible (ARIA labels, semantic HTML, contrast ≥ 4.5:1)
5. Be responsive (mobile-first, 16:9 aspect ratio aware)

VISUAL DESIGN RULES — what separates your output from generic AI slop:
- BACKGROUNDS: Never flat solid white/black. Use gradient overlays, mesh gradients via CSS,
  subtle noise textures (SVG filter), dot/grid patterns (radial-gradient), or frosted glass (backdrop-blur).
- SURFACES: Cards should use glass morphism (backdrop-filter: blur(12px), semi-transparent bg, 1px border
  with rgba white), or elevated shadows with accent glow.
- DEPTH: Create visual layers. Background → decorative pattern → surface card → content → accent highlight.
- COLOR: Follow 60-30-10 rule. Use CSS custom properties from the design system. Accent color for emphasis only.
- TYPOGRAPHY: Use the design system fonts. Type scale: heading 48-64px, subheading 24-32px, body 16-20px.
  Letter-spacing -0.02em for headings. Line-height 1.5 for body.
- ICONS: Import from lucide-react. Use meaningful icons (TrendingUp for growth, Target for market, etc.).
- DECORATIVE: Add subtle gradient borders (background-clip trick), glow effects on accents, floating shapes.

Output ONLY code. No explanations. No markdown outside code blocks."""


# Fallback templates when LLM fails — visually rich, not flat
FALLBACK_TEMPLATES = {
    "title-hero": '''import React from "react";
import {{ motion }} from "framer-motion";

interface {component_name}Props {{
  title: string;
  subtitle?: string;
  backgroundImage?: string;
}}

export default function {component_name}({{ title, subtitle, backgroundImage }}: {component_name}Props) {{
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="relative w-full h-full flex flex-col items-center justify-center overflow-hidden"
    >
      {{/* Mesh gradient background */}}
      <div
        className="absolute inset-0"
        style={{{{
          background: "radial-gradient(ellipse at 20% 50%, {accent_color}22 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, {primary_color}18 0%, transparent 50%), radial-gradient(ellipse at 50% 80%, {accent_color}15 0%, transparent 60%), linear-gradient(135deg, {background_color}, {primary_color}08)",
        }}}}
      />
      {{/* Noise texture overlay */}}
      <div className="absolute inset-0 opacity-[0.03]" style={{{{ backgroundImage: "url(\\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\\")" }}}} />
      {{/* Content */}}
      <div className="relative z-10 text-center max-w-4xl mx-auto px-8">
        <motion.h1
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.6, ease: "easeOut" }}
          className="text-7xl font-bold tracking-tight leading-none"
          style={{ color: "{primary_color}", letterSpacing: "-0.03em" }}
        >
          {{title}}
        </motion.h1>
        {{subtitle && (
          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="text-2xl mt-8 font-light"
            style={{ color: "{accent_color}" }}
          >
            {{subtitle}}
          </motion.p>
        )}}
      </div>
      {{/* Decorative accent line */}}
      <motion.div
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ delay: 0.8, duration: 0.6 }}
        className="absolute bottom-24 h-[2px] w-24"
        style={{ background: "linear-gradient(90deg, transparent, {accent_color}, transparent)" }}
      />
    </motion.div>
  );
}}
''',
    "bullets": '''import React from "react";
import {{ motion }} from "framer-motion";

interface {component_name}Props {{
  title: string;
  bullets: string[];
}}

export default function {component_name}({{ title, bullets }}: {component_name}Props) {{
  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {{/* Gradient background with dot pattern */}}
      <div
        className="absolute inset-0"
        style={{{{
          background: "linear-gradient(160deg, {background_color} 0%, {primary_color}06 100%)",
        }}}}
      />
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{{{
          backgroundImage: "radial-gradient(circle, {primary_color} 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}}}
      />
      {{/* Content */}}
      <div className="relative z-10 p-16 flex flex-col h-full">
        <h2
          className="text-5xl font-bold mb-12 tracking-tight"
          style={{ color: "{primary_color}", letterSpacing: "-0.02em" }}
        >
          {{title}}
        </h2>
        <ul className="space-y-5 flex-1">
          {{bullets.map((bullet, index) => (
            <motion.li
              key={{index}}
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.2 + index * 0.1, ease: "easeOut" }}
              className="flex items-start gap-4 text-xl leading-relaxed"
              style={{ color: "{primary_color}" }}
            >
              <span
                className="mt-2 flex-shrink-0 rounded-full"
                style={{{{
                  width: "8px",
                  height: "8px",
                  background: "linear-gradient(135deg, {accent_color}, {accent_color}88)",
                  boxShadow: "0 0 8px {accent_color}40",
                }}}}
              />
              {{bullet}}
            </motion.li>
          ))}}
        </ul>
      </div>
    </div>
  );
}}
''',
    "two-column": '''import React from "react";
import {{ motion }} from "framer-motion";

interface {component_name}Props {{
  title: string;
  leftContent: string;
  rightContent: string;
}}

export default function {component_name}({{ title, leftContent, rightContent }}: {component_name}Props) {{
  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {{/* Subtle gradient background */}}
      <div
        className="absolute inset-0"
        style={{{{
          background: "linear-gradient(135deg, {background_color} 0%, {primary_color}05 50%, {accent_color}08 100%)",
        }}}}
      />
      {{/* Content */}}
      <div className="relative z-10 p-16 flex flex-col h-full">
        <h2
          className="text-5xl font-bold mb-12 tracking-tight"
          style={{ color: "{primary_color}", letterSpacing: "-0.02em" }}
        >
          {{title}}
        </h2>
        <div className="grid grid-cols-2 gap-8 flex-1">
          <motion.div
            initial={{ x: -30, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="p-8 rounded-xl"
            style={{{{
              background: "{primary_color}06",
              border: "1px solid {primary_color}10",
              backdropFilter: "blur(8px)",
            }}}}
          >
            <p className="text-lg leading-relaxed" style={{ color: "{primary_color}" }}>{{leftContent}}</p>
          </motion.div>
          <motion.div
            initial={{ x: 30, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.35, duration: 0.5 }}
            className="p-8 rounded-xl"
            style={{{{
              background: "{accent_color}08",
              border: "1px solid {accent_color}15",
              backdropFilter: "blur(8px)",
            }}}}
          >
            <p className="text-lg leading-relaxed" style={{ color: "{primary_color}" }}>{{rightContent}}</p>
          </motion.div>
        </div>
      </div>
    </div>
  );
}}
''',
    "generic": '''import React from "react";
import {{ motion }} from "framer-motion";

interface {component_name}Props {{
  title: string;
  content?: string;
}}

export default function {component_name}({{ title, content }}: {component_name}Props) {{
  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden">
      {{/* Gradient background with noise */}}
      <div
        className="absolute inset-0"
        style={{{{
          background: "linear-gradient(160deg, {background_color}, {primary_color}08)",
        }}}}
      />
      <div className="absolute inset-0 opacity-[0.03]" style={{{{ backgroundImage: "url(\\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\\")" }}}} />
      {{/* Content */}}
      <div className="relative z-10 p-16 flex flex-col h-full">
        <h2
          className="text-5xl font-bold mb-8 tracking-tight"
          style={{ color: "{primary_color}", letterSpacing: "-0.02em" }}
        >
          {{title}}
        </h2>
        {{content && (
          <motion.p
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xl leading-relaxed max-w-3xl"
            style={{ color: "{primary_color}" }}
          >
            {{content}}
          </motion.p>
        )}}
      </div>
    </div>
  );
}}
''',
}
