"""
VFX Agent — Phase 6, Agent #7.

The 3D/VFX Agent is an AI-powered agent that decides when and how to add
Three.js 3D scenes to slides. It analyses slide content, type, and
audience to determine appropriate 3D visualisations.

Responsibilities:
- Classify slides that benefit from 3D treatment
- Select the optimal ThreeSceneType for each slide
- Generate ThreeSceneConfig with data mappings
- Respect performance budgets via PerformanceGuardrails
- Provide 2D fallback definitions for each 3D scene
- Write scene configs to the Context Board

Scene selection heuristics:
    - Market/geo data → globe (AnimatedGlobe)
    - Financial projections → bar-chart (ThreeDBarChart)
    - Hero/vision/title → particles (ParticleField)
    - Team/feature showcase → floating-cards (FloatingCards)
    - Architecture/tech → data-flow (DataFlowViz)
    - Multi-dim data → scatter (ScatterPlot3D)
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
from app.models.dsl_v2 import (
    SlideDSL,
    SlideType,
    LayoutType,
    ThreeSceneConfig,
    ThreeSceneType,
)
from app.services.slides_new.renderers.performance_guardrails import (
    PerformanceGuardrails,
    QualityLevel,
    SceneBudgetReport,
    SCENE_COMPLEXITY,
    PRESENTATION_BUDGET,
)
from app.services.slides_new.renderers.react_templates import (
    SCENE_TEMPLATES,
    SceneTemplate,
    get_scene_template,
    get_3d_capable_layouts,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# HEURISTIC RULES — When to activate 3D
# ═══════════════════════════════════════════════════════════════════

# Slide type → preferred scene type(s)
SLIDE_TYPE_SCENE_MAP: dict[SlideType, list[str]] = {
    SlideType.TITLE_SLIDE: ["particles"],
    SlideType.MARKET_SLIDE: ["globe", "bar-chart"],
    SlideType.FINANCIAL_SLIDE: ["bar-chart", "scatter"],
    SlideType.TRACTION_SLIDE: ["bar-chart", "particles"],
    SlideType.TEAM_SLIDE: ["floating-cards"],
    SlideType.SOLUTION_SLIDE: ["data-flow", "particles"],
    SlideType.COMPETITION_SLIDE: ["scatter", "bar-chart"],
    SlideType.CLOSING_SLIDE: ["particles"],
}

# Content keywords that suggest specific scene types
KEYWORD_SCENE_MAP: dict[str, list[str]] = {
    "globe": [
        "global", "worldwide", "international", "countries", "regions",
        "geography", "expansion", "markets", "continents",
    ],
    "bar-chart": [
        "revenue", "growth", "projection", "quarterly", "annual",
        "forecast", "financial", "metrics", "performance", "sales",
    ],
    "particles": [
        "vision", "future", "innovation", "technology", "ai",
        "neural", "network", "ecosystem", "platform",
    ],
    "floating-cards": [
        "team", "founders", "leadership", "members", "advisors",
        "features", "capabilities", "offerings",
    ],
    "data-flow": [
        "architecture", "pipeline", "workflow", "infrastructure",
        "system", "integration", "api", "microservice",
    ],
    "scatter": [
        "correlation", "distribution", "analysis", "dimensions",
        "comparison", "benchmark", "positioning",
    ],
}

# Layouts that support 3D scenes
_3D_LAYOUTS = set(get_3d_capable_layouts())

# Maximum 3D slides per presentation
MAX_3D_SLIDES = PRESENTATION_BUDGET["max_3d_slides"]


# ═══════════════════════════════════════════════════════════════════
# VFX AGENT
# ═══════════════════════════════════════════════════════════════════


class VFXAgent(BaseAgent):
    """
    Agent #7: 3D/VFX Agent.

    Analyses a presentation's slides and determines which ones should
    receive Three.js 3D scenes, what scene type to use, and generates
    the ThreeSceneConfig objects with appropriate data mappings.

    The agent operates in two modes:
    1. Heuristic mode (fast, no LLM): Uses content analysis and slide type
       matching to select scenes deterministically.
    2. AI-enhanced mode (standard/deep): Uses LLM to make nuanced decisions
       about which slides benefit most from 3D treatment.

    Performance budgets are enforced automatically via PerformanceGuardrails.
    """

    DEFAULT_MODEL = "deepseek-v3"
    FALLBACK_MODELS = ["mistral-medium", "cf-qwen"]

    def __init__(self, db, context, context_board=None):
        super().__init__(db, context, context_board)
        self._guardrails = PerformanceGuardrails()
        self._quality = QualityLevel.HIGH

    @property
    def agent_type(self) -> AgentType:
        return AgentType.VFX

    # ═══════════════════════════════════════════════════════════════
    # MAIN EXECUTION
    # ═══════════════════════════════════════════════════════════════

    async def execute(self) -> AgentOutput:
        """
        Execute the VFX Agent. Expects slides in context.metadata["slides"]
        or reads from the Context Board.

        Returns AgentOutput with:
        - output["scene_assignments"]: dict of slide_index → ThreeSceneConfig dict
        - output["budget_report"]: Presentation budget analysis
        - output["fallback_2d"]: dict of slide_index → 2D fallback CSS
        """
        import time

        start_time = time.monotonic()

        try:
            # Get slides from context or board
            slides_data = await self._get_slides()
            if not slides_data:
                return AgentOutput(
                    success=True,
                    agent_type=self.agent_type,
                    output={
                        "scene_assignments": {},
                        "budget_report": {"passed": True, "total_3d_slides": 0},
                        "fallback_2d": {},
                    },
                    warnings=["No slides provided for VFX analysis"],
                    latency_ms=int((time.monotonic() - start_time) * 1000),
                )

            # 1. Classify each slide for 3D potential
            candidates = self._classify_slides(slides_data)

            # 2. Select top candidates within budget
            selected = self._select_within_budget(candidates)

            # 3. Generate scene configs for selected slides
            if self.context.mode == "fast":
                scene_assignments = self._generate_configs_heuristic(selected, slides_data)
            else:
                scene_assignments = await self._generate_configs_ai(selected, slides_data)

            # 4. Run performance validation
            budget_report = self._validate_budget(scene_assignments)

            # 5. Generate 2D fallbacks
            fallback_2d = self._generate_fallbacks(scene_assignments)

            # 6. Write to Context Board
            await self._write_results(scene_assignments, budget_report, fallback_2d)

            latency = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "vfx_agent_complete",
                task_id=self.context.task_id,
                total_slides=len(slides_data),
                three_d_slides=len(scene_assignments),
                budget_passed=budget_report.get("passed", True),
                latency_ms=latency,
            )

            return AgentOutput(
                success=True,
                agent_type=self.agent_type,
                output={
                    "scene_assignments": scene_assignments,
                    "budget_report": budget_report,
                    "fallback_2d": fallback_2d,
                },
                latency_ms=latency,
                context_board_writes=["vfx.scene_assignments", "vfx.budget_report"],
            )

        except Exception as e:
            latency = int((time.monotonic() - start_time) * 1000)
            logger.exception(
                "vfx_agent_error",
                task_id=self.context.task_id,
                error=str(e),
            )
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                errors=[str(e)],
                latency_ms=latency,
            )

    # ═══════════════════════════════════════════════════════════════
    # SLIDE CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════

    def _classify_slides(
        self, slides: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Score each slide for 3D suitability and determine candidate scene types.

        Scoring factors:
        - Slide type match (0-40 pts)
        - Content keyword match (0-30 pts)
        - Layout compatibility (0-15 pts)
        - Position in deck — hero/closing get bonus (0-15 pts)

        Returns sorted list of candidates with scores.
        """
        candidates: list[dict[str, Any]] = []

        total_slides = len(slides)
        for slide_data in slides:
            score = 0.0
            reasons: list[str] = []
            scene_candidates: list[str] = []

            index = slide_data.get("index", 0)
            slide_type_str = slide_data.get("type", "custom")
            layout_str = slide_data.get("layout", "center-focus")
            content = slide_data.get("content", {})
            title = content.get("title", "") if isinstance(content, dict) else ""
            body = content.get("body_text", "") if isinstance(content, dict) else ""
            text_blob = f"{title} {body}".lower()

            # Factor 1: Slide type match (0-40)
            try:
                slide_type = SlideType(slide_type_str)
            except ValueError:
                slide_type = SlideType.CUSTOM

            if slide_type in SLIDE_TYPE_SCENE_MAP:
                scene_candidates.extend(SLIDE_TYPE_SCENE_MAP[slide_type])
                score += 40
                reasons.append(f"Slide type '{slide_type.value}' suggests 3D")

            # Factor 2: Keyword match (0-30)
            keyword_scores: dict[str, int] = {}
            for scene_type, keywords in KEYWORD_SCENE_MAP.items():
                matches = sum(1 for kw in keywords if kw in text_blob)
                if matches > 0:
                    keyword_scores[scene_type] = min(matches * 10, 30)

            if keyword_scores:
                best_scene = max(keyword_scores, key=keyword_scores.get)
                score += keyword_scores[best_scene]
                if best_scene not in scene_candidates:
                    scene_candidates.append(best_scene)
                reasons.append(f"Content keywords match '{best_scene}' scene")

            # Factor 3: Layout compatibility (0-15)
            if layout_str in _3D_LAYOUTS:
                score += 15
                reasons.append("Layout supports 3D")

            # Factor 4: Position bonus (0-15)
            if index == 0:
                score += 15
                reasons.append("Opening slide — high visual impact")
                if "particles" not in scene_candidates:
                    scene_candidates.insert(0, "particles")
            elif total_slides > 0 and index == total_slides - 1:
                score += 10
                reasons.append("Closing slide — visual punctuation")
                if "particles" not in scene_candidates:
                    scene_candidates.append("particles")

            # Only consider if score is meaningful
            if score >= 25 and scene_candidates:
                candidates.append({
                    "index": index,
                    "score": score,
                    "scene_candidates": scene_candidates,
                    "reasons": reasons,
                    "slide_type": slide_type_str,
                    "layout": layout_str,
                    "content": content,
                })

        # Sort by score descending
        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates

    def _select_within_budget(
        self, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Select the top N candidates that fit within the presentation
        3D slide budget.
        """
        return candidates[:MAX_3D_SLIDES]

    # ═══════════════════════════════════════════════════════════════
    # CONFIG GENERATION — HEURISTIC
    # ═══════════════════════════════════════════════════════════════

    def _generate_configs_heuristic(
        self,
        selected: list[dict[str, Any]],
        slides: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """
        Generate ThreeSceneConfig for each selected slide using
        deterministic heuristics. Fast mode — no LLM calls.
        """
        assignments: dict[int, dict[str, Any]] = {}

        used_types: list[str] = []  # Track variety

        for candidate in selected:
            idx = candidate["index"]
            scene_candidates = candidate["scene_candidates"]
            content = candidate.get("content", {})

            # Pick scene type with variety preference
            scene_type = self._pick_varied_scene(scene_candidates, used_types)
            used_types.append(scene_type)

            # Get template default config
            template = get_scene_template(scene_type)
            config = dict(template.default_config) if template else {}

            # Customise config based on content
            config = self._customise_config(scene_type, config, content)

            # Run budget check
            report = self._guardrails.analyze_scene(scene_type, self._quality)

            assignments[idx] = {
                "scene_type": scene_type,
                "config": config,
                "quality": report.quality_level.value,
                "fallback_2d": report.fallback_2d,
                "budget": {
                    "passed": report.passed,
                    "polygons": report.polygons,
                    "particles": report.particles,
                    "memory_mb": report.estimated_memory_mb,
                },
            }

        return assignments

    def _pick_varied_scene(
        self, candidates: list[str], used: list[str]
    ) -> str:
        """Pick the best scene type from candidates, preferring variety."""
        # Prefer types not yet used
        for scene_type in candidates:
            if scene_type not in used:
                return scene_type

        # All types used — just pick the first candidate
        return candidates[0] if candidates else "particles"

    def _customise_config(
        self,
        scene_type: str,
        config: dict[str, Any],
        content: dict[str, Any],
    ) -> dict[str, Any]:
        """Customise scene config based on slide content."""
        title = content.get("title", "") if isinstance(content, dict) else ""

        if scene_type == "globe":
            # Extract region hints from content
            regions: list[str] = []
            text = f"{title} {content.get('body_text', '')}".lower() if isinstance(content, dict) else ""
            region_map = {
                "north america": "NA", "united states": "NA", "us": "NA", "usa": "NA",
                "europe": "EU", "european": "EU", "uk": "EU",
                "asia": "APAC", "pacific": "APAC", "china": "APAC", "japan": "APAC", "india": "APAC",
                "latin america": "LATAM", "brazil": "LATAM", "mexico": "LATAM",
                "africa": "AF", "middle east": "ME",
            }
            for keyword, code in region_map.items():
                if keyword in text and code not in regions:
                    regions.append(code)

            if regions:
                config["highlightRegions"] = regions
            else:
                config["highlightRegions"] = ["NA", "EU", "APAC"]

        elif scene_type == "bar-chart":
            # Check for KPI metrics to map to bars
            kpi_metrics = content.get("kpi_metrics", []) if isinstance(content, dict) else []
            if kpi_metrics and isinstance(kpi_metrics, list):
                bar_data = []
                for m in kpi_metrics[:8]:
                    if isinstance(m, dict):
                        label = m.get("label", "")
                        value_str = m.get("value", "0")
                        # Extract numeric value
                        numeric = re.sub(r"[^\d.]", "", str(value_str))
                        try:
                            value = float(numeric) if numeric else 0
                        except (ValueError, TypeError):
                            value = 0
                        bar_data.append({"label": label, "value": value})
                if bar_data:
                    config["data"] = bar_data

        elif scene_type == "particles":
            # Adjust particle density based on mood
            if any(word in title.lower() for word in ["vision", "future", "innovation"]):
                config["count"] = 8_000
                config["connectionDistance"] = 200
            else:
                config["count"] = 5_000

        elif scene_type == "floating-cards":
            # Map team members to card data
            members = content.get("team_members", []) if isinstance(content, dict) else []
            if members and isinstance(members, list):
                cards = []
                for m in members[:6]:
                    if isinstance(m, dict):
                        cards.append({
                            "name": m.get("name", ""),
                            "role": m.get("role", ""),
                            "image": m.get("image_url", ""),
                        })
                if cards:
                    config["cards"] = cards

        elif scene_type == "data-flow":
            # Create a simple architecture graph from bullets
            bullets = content.get("bullets", []) if isinstance(content, dict) else []
            if bullets and isinstance(bullets, list):
                nodes = [{"id": str(i), "label": str(b)[:30]} for i, b in enumerate(bullets[:6])]
                edges = [{"from": str(i), "to": str(i + 1)} for i in range(len(nodes) - 1)]
                config["nodes"] = nodes
                config["edges"] = edges

        return config

    # ═══════════════════════════════════════════════════════════════
    # CONFIG GENERATION — AI-ENHANCED
    # ═══════════════════════════════════════════════════════════════

    async def _generate_configs_ai(
        self,
        selected: list[dict[str, Any]],
        slides: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """
        Generate scene configs using LLM for nuanced decisions.
        Falls back to heuristic if LLM call fails.
        """
        # Build prompt with slide summaries
        slide_summaries = []
        for cand in selected:
            idx = cand["index"]
            slide_summaries.append(
                f"  Slide {idx}: type={cand['slide_type']}, "
                f"title=\"{cand['content'].get('title', '') if isinstance(cand['content'], dict) else ''}\", "
                f"candidates={cand['scene_candidates']}, "
                f"score={cand['score']}"
            )

        summaries_text = "\n".join(slide_summaries)
        available_scenes = ", ".join(SCENE_TEMPLATES.keys())

        prompt = f"""You are a presentation VFX specialist. Assign the optimal Three.js 3D scene to each slide.

Available 3D scene types: {available_scenes}

Candidate slides for 3D treatment:
{summaries_text}

For each slide, output a JSON array of assignments:
[
  {{
    "slide_index": <int>,
    "scene_type": "<one of: {available_scenes}>",
    "rationale": "<1-sentence reason>",
    "color_accent": "<hex color matching slide mood>"
  }}
]

Rules:
1. Choose the scene type that best visualises the slide's actual data/content
2. Prefer variety — avoid repeating the same scene type on adjacent slides
3. Maximum {MAX_3D_SLIDES} slides with 3D scenes
4. For title/hero slides, prefer "particles" for ambient visual impact
5. For data-heavy slides, prefer "bar-chart" or "scatter"
6. For market/geo slides, prefer "globe"

Return ONLY the JSON array, no commentary."""

        system_prompt = (
            "You are a 3D visualisation expert for business presentations. "
            "You select and configure Three.js scenes that enhance slide content "
            "without overwhelming the message. Output valid JSON only."
        )

        try:
            llm_result = await self.call_llm(
                task_type=TaskType.THREEJS_SCENE,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
            )

            if llm_result.success and llm_result.output.get("content"):
                raw = llm_result.output["content"]
                assignments_list = self._parse_llm_assignments(raw)

                if assignments_list:
                    return self._build_assignments_from_llm(
                        assignments_list, selected, slides
                    )

        except Exception as e:
            logger.warning(
                "vfx_ai_fallback",
                error=str(e),
                task_id=self.context.task_id,
            )

        # Fallback to heuristic
        return self._generate_configs_heuristic(selected, slides)

    def _parse_llm_assignments(self, raw: str) -> list[dict[str, Any]]:
        """Parse LLM response into a list of scene assignments."""
        # Extract JSON from response
        raw = raw.strip()

        # Try direct parse
        try:
            result = json.loads(raw)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # Try finding array in response
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return []

    def _build_assignments_from_llm(
        self,
        llm_assignments: list[dict[str, Any]],
        selected: list[dict[str, Any]],
        slides: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """Build full assignments from LLM output, with budget validation."""
        valid_scene_types = set(SCENE_TEMPLATES.keys())
        selected_indexes = {c["index"] for c in selected}
        assignments: dict[int, dict[str, Any]] = {}

        for item in llm_assignments:
            idx = item.get("slide_index")
            scene_type = item.get("scene_type", "")

            # Validate
            if idx is None or idx not in selected_indexes:
                continue
            if scene_type not in valid_scene_types:
                continue

            # Get template config
            template = get_scene_template(scene_type)
            config = dict(template.default_config) if template else {}

            # Apply accent color if provided
            accent = item.get("color_accent")
            if accent and re.match(r"^#[0-9a-fA-F]{6}$", accent):
                if scene_type == "particles":
                    config["color"] = accent
                elif scene_type == "globe":
                    config["dotColor"] = accent
                elif scene_type == "bar-chart":
                    config["barColor"] = accent

            # Find content for this slide
            slide_content = {}
            for s in slides:
                if s.get("index") == idx:
                    slide_content = s.get("content", {})
                    break

            config = self._customise_config(scene_type, config, slide_content)

            # Budget check
            report = self._guardrails.analyze_scene(scene_type, self._quality)

            assignments[idx] = {
                "scene_type": scene_type,
                "config": config,
                "quality": report.quality_level.value,
                "fallback_2d": report.fallback_2d,
                "rationale": item.get("rationale", ""),
                "budget": {
                    "passed": report.passed,
                    "polygons": report.polygons,
                    "particles": report.particles,
                    "memory_mb": report.estimated_memory_mb,
                },
            }

        return assignments

    # ═══════════════════════════════════════════════════════════════
    # BUDGET VALIDATION
    # ═══════════════════════════════════════════════════════════════

    def _validate_budget(
        self, assignments: dict[int, dict[str, Any]]
    ) -> dict[str, Any]:
        """Validate all scene assignments against the presentation budget."""
        scenes = [
            {
                "slide_index": idx,
                "scene_type": info["scene_type"],
            }
            for idx, info in assignments.items()
        ]

        if not scenes:
            return {"passed": True, "total_3d_slides": 0, "violations": []}

        report = self._guardrails.analyze_presentation(scenes)

        return {
            "passed": report.passed,
            "total_3d_slides": report.total_3d_slides,
            "total_polygons": report.total_polygons,
            "total_memory_mb": report.total_memory_mb,
            "recommended_quality": report.recommended_quality.value,
            "violations": [
                {
                    "metric": v.metric,
                    "limit": v.limit,
                    "actual": v.actual,
                    "severity": v.severity,
                    "recommendation": v.recommendation,
                }
                for v in report.violations
            ],
        }

    # ═══════════════════════════════════════════════════════════════
    # 2D FALLBACKS
    # ═══════════════════════════════════════════════════════════════

    def _generate_fallbacks(
        self, assignments: dict[int, dict[str, Any]]
    ) -> dict[int, dict[str, Any]]:
        """
        Generate 2D CSS fallback definitions for each 3D scene.
        Used when WebGL is unavailable or performance is too low.
        """
        fallbacks: dict[int, dict[str, Any]] = {}

        for idx, info in assignments.items():
            scene_type = info["scene_type"]
            config = info.get("config", {})

            if scene_type == "globe":
                color = config.get("dotColor", "#38BDF8")
                fallbacks[idx] = {
                    "type": "gradient",
                    "css": (
                        f"background: radial-gradient(circle at 50% 50%, "
                        f"{color}22 0%, transparent 60%), "
                        f"radial-gradient(circle at 50% 50%, #1a1a2e 0%, #0f0f1a 100%)"
                    ),
                    "label": "Globe visualization",
                    "icon": "🌍",
                }
            elif scene_type == "bar-chart":
                color = config.get("barColor", "#38BDF8")
                fallbacks[idx] = {
                    "type": "static_chart",
                    "css": f"background: linear-gradient(135deg, #1a1a2e 0%, {color}15 100%)",
                    "label": "3D bar chart",
                    "icon": "📊",
                }
            elif scene_type == "particles":
                color = config.get("color", "#38BDF8")
                fallbacks[idx] = {
                    "type": "gradient",
                    "css": (
                        f"background: radial-gradient(ellipse at 30% 30%, "
                        f"{color}15 0%, transparent 50%), "
                        f"radial-gradient(ellipse at 70% 70%, "
                        f"{color}10 0%, transparent 50%), "
                        f"#0f0f1a"
                    ),
                    "label": "Particle field",
                    "icon": "✨",
                }
            elif scene_type == "floating-cards":
                fallbacks[idx] = {
                    "type": "grid",
                    "css": "background: #1a1a2e",
                    "label": "Card grid (non-3D)",
                    "icon": "🃏",
                }
            elif scene_type == "data-flow":
                fallbacks[idx] = {
                    "type": "static_diagram",
                    "css": "background: linear-gradient(135deg, #1a1a2e 0%, #0f172a 100%)",
                    "label": "Data flow diagram",
                    "icon": "🔄",
                }
            elif scene_type == "scatter":
                fallbacks[idx] = {
                    "type": "static_chart",
                    "css": "background: linear-gradient(135deg, #1a1a2e 0%, #0f172a 100%)",
                    "label": "Scatter plot",
                    "icon": "📈",
                }
            else:
                fallbacks[idx] = {
                    "type": "gradient",
                    "css": "background: #1a1a2e",
                    "label": "Custom visual",
                    "icon": "🎨",
                }

        return fallbacks

    # ═══════════════════════════════════════════════════════════════
    # CONTEXT BOARD & DATA ACCESS
    # ═══════════════════════════════════════════════════════════════

    async def _get_slides(self) -> list[dict[str, Any]]:
        """Retrieve slides from context metadata or Context Board."""
        # Check context metadata first
        slides = self.context.metadata.get("slides", [])
        if slides:
            return slides

        # Try Context Board
        board_slides = await self.read_from_board("assembler.slides")
        if board_slides and isinstance(board_slides, list):
            return board_slides

        # Try code_agent output
        code_output = self.context.previous_outputs.get("code_agent")
        if code_output and code_output.success:
            return code_output.output.get("slides", [])

        return []

    async def _write_results(
        self,
        assignments: dict[int, dict[str, Any]],
        budget_report: dict[str, Any],
        fallbacks: dict[int, dict[str, Any]],
    ) -> None:
        """Write VFX results to the Context Board."""
        await self.write_to_board("vfx.scene_assignments", assignments)
        await self.write_to_board("vfx.budget_report", budget_report)
        await self.write_to_board("vfx.fallback_2d", fallbacks)
        await self.write_to_board("vfx.quality_level", self._quality.value)


# ═══════════════════════════════════════════════════════════════════
# STANDALONE UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


def classify_slide_for_3d(
    slide_type: str,
    layout: str,
    title: str = "",
    body: str = "",
) -> dict[str, Any]:
    """
    Standalone classification function for testing.
    Returns a dict with score, scene_candidates, and reasons.
    """
    text_blob = f"{title} {body}".lower()
    score = 0.0
    reasons: list[str] = []
    scene_candidates: list[str] = []

    try:
        st = SlideType(slide_type)
    except ValueError:
        st = SlideType.CUSTOM

    if st in SLIDE_TYPE_SCENE_MAP:
        scene_candidates.extend(SLIDE_TYPE_SCENE_MAP[st])
        score += 40
        reasons.append(f"Type '{st.value}' matched")

    for scene_type, keywords in KEYWORD_SCENE_MAP.items():
        matches = sum(1 for kw in keywords if kw in text_blob)
        if matches > 0 and scene_type not in scene_candidates:
            scene_candidates.append(scene_type)
            score += min(matches * 10, 30)
            reasons.append(f"Keywords match '{scene_type}'")

    if layout in _3D_LAYOUTS:
        score += 15
        reasons.append("Layout supports 3D")

    return {
        "score": score,
        "scene_candidates": scene_candidates,
        "reasons": reasons,
        "qualifies": score >= 25 and len(scene_candidates) > 0,
    }


def get_available_scene_types() -> list[str]:
    """Return all available Three.js scene type names."""
    return list(SCENE_TEMPLATES.keys())
