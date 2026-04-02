"""
Orchestrator — The Conductor.
Coordinates Brain MCP, Design MCP, and Render MCP to execute
the full presentation generation pipeline.

Uses PromptEngine for all LLM prompts (not hardcoded strings).
Passes writing_style from GenerationInput through the entire pipeline.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.presentation import (
    GenerationInput,
    GenerationState,
    TemplateGenerationInput,
)
from app.models.slide import SlideContent, SlideLayout
from app.services.llm import ModelRouter, TaskType
from app.services.orchestrator.state_machine import GenerationStateMachine
from app.services.orchestrator.progress_tracker import ProgressTracker
from app.mcp.brain_mcp.prompts.prompt_engine import PromptEngine
from app.mcp.brain_mcp.prompts.research_planner import (
    RESEARCH_PLANNER_SYSTEM,
    RESEARCH_SYNTHESIS_SYSTEM,
    DATA_EXTRACTOR_SYSTEM,
)
from app.mcp.brain_mcp.prompts.quality_guards import run_quality_guards

import structlog

logger = structlog.get_logger()


class PresentationOrchestrator:
    """
    Coordinates the full pipeline:
    Input → Research → Outline → Content → Design → Preview → Ready for Editing

    For v1, Brain MCP tools are called directly (in-process) rather than via
    MCP subprocess. This simplifies deployment while keeping the tool interface
    stable for later extraction.
    """

    def __init__(self, db: AsyncIOMotorDatabase, progress_tracker: ProgressTracker):
        self.db = db
        self.progress = progress_tracker
        self.router = ModelRouter.get_instance()
        self.prompt_engine = PromptEngine()

    async def generate_presentation(
        self,
        project_id: str,
        input_data: GenerationInput,
        user_id: str,
    ) -> dict:
        """
        Full AI generation pipeline.
        State is persisted after each phase — crash-proof.
        """
        sm = GenerationStateMachine(project_id, self.db, self.progress)

        # writing_style flows through the entire pipeline
        writing_style = getattr(input_data, "writing_style", None) or "yc_pitch"
        purpose = input_data.purpose

        try:
            # ═══════════ PHASE 1: RESEARCH (0-25%) ═══════════
            await sm.transition_to(
                GenerationState.RESEARCHING, 5, "Researching your topic..."
            )

            research_context = await self._do_research(
                topic=input_data.topic,
                description=input_data.description,
                purpose=purpose,
                mode=input_data.mode.value,
                project_id=project_id,
            )
            await sm.transition_to(GenerationState.RESEARCHING, 25, "Research complete")

            # ═══════════ PHASE 2: OUTLINE (25-40%) ═══════════
            await sm.transition_to(GenerationState.OUTLINING, 30, "Creating outline...")

            outline = await self._do_outline(
                topic=input_data.topic,
                audience=input_data.audience,
                purpose=purpose,
                writing_style=writing_style,
                slide_count=input_data.slide_count,
                research_context=research_context,
                mode=input_data.mode.value,
                project_id=project_id,
            )
            await sm.transition_to(GenerationState.OUTLINING, 40, "Outline ready")

            # ═══════════ PHASE 3: CONTENT (40-75%) ═══════════
            await sm.transition_to(
                GenerationState.GENERATING_CONTENT, 45, "Writing slides..."
            )

            slides = await self._do_content_generation(
                outline=outline,
                research_context=research_context,
                writing_style=writing_style,
                purpose=purpose,
                mode=input_data.mode.value,
                generate_notes=input_data.generate_notes,
                project_id=project_id,
                progress_callback=lambda p, m: sm.transition_to(
                    GenerationState.GENERATING_CONTENT, 45 + int(p * 0.30), m
                ),
            )
            await sm.transition_to(
                GenerationState.GENERATING_CONTENT, 75, "Content generated"
            )

            # ═══════════ PHASE 4: SAVE SLIDES TO DB (75-85%) ═══════════
            await sm.transition_to(GenerationState.DESIGNING, 80, "Saving slides...")

            slide_ids = []
            for i, slide_data in enumerate(slides):
                slide_id = str(ObjectId())
                await self.db.slides.insert_one(
                    {
                        "_id": slide_id,
                        "presentation_id": project_id,
                        "index": i,
                        "layout": slide_data.get("layout", "bullets"),
                        "content": slide_data.get("content", {}),
                        "version": 1,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                )
                slide_ids.append(slide_id)

            # Update presentation with slide count
            await self.db.presentations.update_one(
                {"_id": project_id},
                {
                    "$set": {
                        "slide_count": len(slides),
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            await sm.transition_to(GenerationState.DESIGNING, 85, "Design applied")

            # ═══════════ PHASE 5: READY FOR EDITING (85-100%) ═══════════
            await sm.transition_to(
                GenerationState.RENDERING_PREVIEW, 90, "Creating preview..."
            )

            # Phase D4: Run style-aware design quality pass
            design_warnings = self._run_design_quality_pass(
                slides=slides,
                purpose=input_data.purpose or "pitch",
                writing_style=writing_style,
            )

            # Phase E2: Fire-and-forget image generation (non-blocking)
            # Text is already visible to user; images populate via WebSocket
            pres_doc = await self.db.presentations.find_one({"_id": project_id})
            theme_id = pres_doc.get("theme_id") if pres_doc else None
            theme = {}
            if theme_id:
                theme = await self.db.themes.find_one({"_id": theme_id}) or {}
            asyncio.create_task(
                self._generate_slide_images_background(
                    slides=slides,
                    theme=theme,
                    presentation_id=project_id,
                    user_id=user_id,
                )
            )

            # Phase E3: Fire thumbnail Celery task (async gallery population)
            self._dispatch_thumbnail_task(project_id)

            await sm.transition_to(
                GenerationState.READY_FOR_EDITING, 100, "Ready for editing!"
            )

            # Collect all warnings (per-slide quality + design-level)
            all_warnings = []
            for s in slides:
                all_warnings.extend(s.get("quality_warnings", []))
            all_warnings.extend(design_warnings)

            return {
                "project_id": project_id,
                "slide_count": len(slides),
                "slide_ids": slide_ids,
                "warnings": all_warnings,
                "status": "ready_for_editing",
            }

        except Exception as e:
            logger.error("generation_failed", project_id=project_id, error=str(e))
            await sm.handle_failure(str(e), sm.current_state.value)
            raise

    async def generate_from_template(
        self,
        project_id: str,
        input_data: TemplateGenerationInput,
        user_id: str,
    ) -> dict:
        """
        Template-based generation pipeline.
        Loads template, fills placeholders with AI + user data.
        Uses template's default_writing_style for content voice.
        """
        sm = GenerationStateMachine(project_id, self.db, self.progress)

        try:
            await sm.transition_to(
                GenerationState.FILLING_TEMPLATE, 10, "Loading template..."
            )

            template = await self.db.templates.find_one({"_id": input_data.template_id})
            if not template:
                raise ValueError(f"Template not found: {input_data.template_id}")

            # Read template's default writing style and category
            template_style = template.get("default_writing_style", "yc_pitch")
            template_category = template.get("category", "general")

            await sm.transition_to(
                GenerationState.FILLING_TEMPLATE, 20, "Filling content..."
            )

            slides = []
            total = len(template.get("slides", []))
            for i, slide_def in enumerate(template.get("slides", [])):
                progress = 20 + int((i / max(total, 1)) * 60)
                await sm.transition_to(
                    GenerationState.FILLING_TEMPLATE,
                    progress,
                    f"Generating slide {i + 1}/{total}...",
                )

                filled = await self._fill_template_slide(
                    slide_def=slide_def,
                    user_inputs=input_data.user_inputs,
                    template_style=template_style,
                    template_category=template_category,
                    mode=input_data.mode.value,
                    project_id=project_id,
                )
                slides.append(filled)

            # Save slides to DB
            slide_ids = []
            for i, slide_data in enumerate(slides):
                slide_id = str(ObjectId())
                await self.db.slides.insert_one(
                    {
                        "_id": slide_id,
                        "presentation_id": project_id,
                        "index": i,
                        "layout": slide_data.get("layout", "bullets"),
                        "content": slide_data.get("content", {}),
                        "version": 1,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                )
                slide_ids.append(slide_id)

            await self.db.presentations.update_one(
                {"_id": project_id},
                {
                    "$set": {
                        "slide_count": len(slides),
                        "template_id": input_data.template_id,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            # Track template usage
            await self.db.template_analytics.update_one(
                {"template_id": input_data.template_id},
                {"$inc": {"total_uses": 1}},
                upsert=True,
            )

            await sm.transition_to(
                GenerationState.READY_FOR_EDITING, 100, "Ready for editing!"
            )

            return {
                "project_id": project_id,
                "slide_count": len(slides),
                "slide_ids": slide_ids,
                "status": "ready_for_editing",
            }

        except Exception as e:
            logger.error(
                "template_generation_failed", project_id=project_id, error=str(e)
            )
            await sm.handle_failure(str(e), sm.current_state.value)
            raise

    # ── Internal pipeline steps ──────────────────────────────

    # ── Phase E2: Fire-and-Forget Image Generation ───────────

    async def _generate_slide_images_background(
        self,
        slides: list[dict],
        theme: dict,
        presentation_id: str,
        user_id: str,
    ) -> None:
        """
        Generate AI images for slides in the background (non-blocking).

        After each image is ready, pushes the URL to the frontend via WebSocket
        so images "pop in" as they complete.

        This runs as a fire-and-forget asyncio.create_task() — the main
        generation loop returns immediately with text content.
        """
        from app.services.image_service import ImageService

        image_service = ImageService()
        try:
            # Fetch slide IDs from DB for WebSocket targeting
            slide_docs = (
                await self.db.slides.find({"presentation_id": presentation_id})
                .sort("index", 1)
                .to_list(None)
            )
            slide_id_map = {doc["index"]: str(doc["_id"]) for doc in slide_docs}

            for i, slide in enumerate(slides):
                layout = slide.get("layout", "bullets")
                content = slide.get("content", {})

                # Skip layouts that don't benefit from AI images
                if layout in ("chart", "kpi-dashboard", "team-grid", "blank"):
                    continue

                url = await image_service.generate_slide_image(
                    content=content,
                    layout=layout,
                    theme=theme,
                    presentation_id=presentation_id,
                    slide_index=i,
                    user_id=user_id,
                )
                if url:
                    # Update slide document with image URL
                    await self.db.slides.update_one(
                        {"presentation_id": presentation_id, "index": i},
                        {"$set": {"content.image_url": url}},
                    )

                    # Push to frontend via WebSocket
                    slide_id = slide_id_map.get(i, "")
                    await self.progress.send_slide_image_ready(
                        project_id=presentation_id,
                        slide_id=slide_id,
                        image_url=url,
                        slide_index=i,
                    )

                    logger.info(
                        "slide_image_pushed",
                        presentation_id=presentation_id,
                        slide_index=i,
                        slide_id=slide_id,
                    )
        except Exception as e:
            logger.error(
                "background_image_generation_failed",
                presentation_id=presentation_id,
                error=str(e),
            )
        finally:
            await image_service.close()

    @staticmethod
    def _dispatch_thumbnail_task(presentation_id: str) -> None:
        """Dispatch Celery thumbnail task (fire-and-forget)."""
        try:
            from celery_worker import celery_app

            celery_app.send_task(
                "thumbnail.generate",
                args=[presentation_id],
            )
            logger.info(
                "thumbnail_task_dispatched",
                presentation_id=presentation_id,
            )
        except Exception as e:
            logger.warning(
                "thumbnail_task_dispatch_failed",
                presentation_id=presentation_id,
                error=str(e),
            )

    async def _do_research(
        self,
        topic: str,
        description: str,
        purpose: str,
        mode: str,
        project_id: str,
    ) -> str:
        """
        Research step — gathers context for slide generation.

        Phase D3: Uses purpose-aware engine routing with asyncio.gather
        for parallel execution. Falls back to LLM-based research if
        engines are not configured.

        Engine routing matrix:
        - pitch/fundraising/investor → MarketEngine + SocialEngine (parallel)
        - quarterly/internal → FinancialEngine + NewsEngine (parallel)
        - sales/marketing → SearchEngine + SocialEngine (parallel)
        - academic/research → AcademicEngine + ScraperEngine (parallel)
        - general → SearchEngine (single)
        """
        purpose_lower = purpose.lower()

        # ── Phase D3: Parallel research engine routing ──
        engine_tasks = []
        engine_labels = []

        if purpose_lower in ("pitch", "fundraising", "investor"):
            engine_tasks.append(self._run_market_engine(topic))
            engine_tasks.append(self._run_social_engine(topic))
            engine_labels.extend(["market", "social"])

        elif purpose_lower in ("quarterly", "internal", "board"):
            engine_tasks.append(self._run_financial_engine(topic))
            engine_tasks.append(self._run_news_engine(topic))
            engine_labels.extend(["financial", "news"])

        elif purpose_lower in ("sales", "marketing"):
            engine_tasks.append(self._run_search_engine(topic))
            engine_tasks.append(self._run_social_engine(topic))
            engine_labels.extend(["search", "social"])

        elif purpose_lower in ("academic", "research"):
            engine_tasks.append(self._run_academic_engine(topic))
            engine_tasks.append(self._run_scraper_engine(topic))
            engine_labels.extend(["academic", "scraper"])

        else:
            # General — single search engine
            engine_tasks.append(self._run_search_engine(topic))
            engine_labels.append("search")

        # Run all engines in parallel (asyncio.gather)
        engine_results = {}
        if engine_tasks:
            results = await asyncio.gather(*engine_tasks, return_exceptions=True)
            for label, result in zip(engine_labels, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "research_engine_failed",
                        engine=label,
                        error=str(result),
                    )
                    engine_results[label] = {"error": str(result)}
                else:
                    engine_results[label] = result or {}

        # Check if all engines returned errors — fall back to LLM research
        all_failed = all("error" in r or not r for r in engine_results.values())

        if all_failed:
            logger.warning(
                "all_research_engines_failed",
                purpose=purpose_lower,
                fallback="llm_research",
            )
            return await self._fallback_llm_research(
                topic, description, purpose_lower, mode, project_id
            )

        # ── Synthesize engine results into research brief ──
        research_sections = []
        for label, data in engine_results.items():
            if data and "error" not in data:
                section = self._format_engine_result(label, data)
                if section:
                    research_sections.append(section)

        if not research_sections:
            return await self._fallback_llm_research(
                topic, description, purpose_lower, mode, project_id
            )

        synthesis_text = "\n\n".join(research_sections)

        # ── Extract structured data points ──
        try:
            extract_user_prompt = (
                f"Research data:\n{synthesis_text[:3000]}\n\n"
                f"Topic: {topic}\n"
                f"Extract all data points suitable for charts: market sizes, growth rates, "
                f"revenue figures, user counts. Include source attribution for each number."
            )

            extract_response = await self.router.complete(
                task_type=TaskType.STRUCTURED_JSON,
                messages=[
                    {"role": "system", "content": DATA_EXTRACTOR_SYSTEM},
                    {"role": "user", "content": extract_user_prompt},
                ],
                max_tokens=1500,
                response_format={"type": "json_object"},
                presentation_id=project_id,
                phase="data_extraction",
            )

            data_points_raw = extract_response.content.strip()
            structured_data = json.loads(data_points_raw)
            data_points_text = json.dumps(
                structured_data.get("data_points", []), indent=2
            )

            final_research = (
                f"# Research Brief: {topic}\n\n"
                f"{synthesis_text}\n\n"
                f"## Extracted Data Points (for charts)\n"
                f"{data_points_text}"
            )
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("data_extraction_failed", error=str(e))
            final_research = synthesis_text

        return final_research

    # ── Research Engine Wrappers (Phase D3) ──────────────────

    async def _run_market_engine(self, topic: str) -> dict:
        """Run MarketDataEngine for market analysis."""
        try:
            from app.mcp.brain_mcp.engines.market_engine import MarketDataEngine

            engine = MarketDataEngine()
            result = await engine.get_market_overview(topic)
            return result or {}
        except Exception as e:
            logger.warning("market_engine_error", error=str(e))
            return {}

    async def _run_social_engine(self, topic: str) -> dict:
        """Run SocialEngine for competitor analysis."""
        try:
            from app.mcp.brain_mcp.engines.social_engine import SocialEngine

            engine = SocialEngine()
            results = await engine.search_reddit(topic, max_results=5)
            github_results = await engine.search_github(topic, max_results=5)
            return {
                "reddit_posts": results,
                "github_repos": github_results,
            }
        except Exception as e:
            logger.warning("social_engine_error", error=str(e))
            return {}

    async def _run_financial_engine(self, topic: str) -> dict:
        """Run FinancialEngine for benchmarks."""
        try:
            from app.mcp.brain_mcp.engines.financial_engine import FinancialEngine

            engine = FinancialEngine()
            census_data = await engine.get_census_data(topic)
            return {
                "census_data": census_data,
            }
        except Exception as e:
            logger.warning("financial_engine_error", error=str(e))
            return {}

    async def _run_news_engine(self, topic: str) -> dict:
        """Run NewsEngine for industry trends."""
        try:
            from app.mcp.brain_mcp.engines.news_engine import NewsEngine

            engine = NewsEngine()
            results = await engine.search_news(topic, max_results=5)
            return {
                "news_articles": results,
            }
        except Exception as e:
            logger.warning("news_engine_error", error=str(e))
            return {}

    async def _run_search_engine(self, topic: str) -> dict:
        """Run SearchEngine for general web search."""
        try:
            from app.mcp.brain_mcp.engines.search_engine import SearchEngine

            engine = SearchEngine()
            results = await engine.search(topic, max_results=8)
            return results or {}
        except Exception as e:
            logger.warning("search_engine_error", error=str(e))
            return {}

    async def _run_academic_engine(self, topic: str) -> dict:
        """Run AcademicEngine for research papers."""
        try:
            from app.mcp.brain_mcp.engines.academic_engine import AcademicEngine

            engine = AcademicEngine()
            results = await engine.search_papers(topic, max_results=5)
            return results or {}
        except Exception as e:
            logger.warning("academic_engine_error", error=str(e))
            return {}

    async def _run_scraper_engine(self, topic: str) -> dict:
        """Run ScraperEngine for web content extraction."""
        try:
            from app.mcp.brain_mcp.engines.scraper_engine import ScraperEngine

            engine = ScraperEngine()
            # ScraperEngine may not have scrape_topic, use search instead
            if hasattr(engine, "scrape_topic"):
                result = await engine.scrape_topic(topic)
            elif hasattr(engine, "search"):
                result = await engine.search(topic)
            else:
                result = {}
            return result or {}
        except Exception as e:
            logger.warning("scraper_engine_error", error=str(e))
            return {}

    def _format_engine_result(self, label: str, data: dict) -> str:
        """Format engine result into a research section."""
        if not data:
            return ""

        section_titles = {
            "market": "Market Analysis",
            "social": "Competitor Analysis",
            "financial": "Financial Benchmarks",
            "news": "Industry Trends",
            "search": "Web Search Results",
            "academic": "Academic Research",
            "scraper": "Web Content",
        }
        title = section_titles.get(label, label.title())
        return f"## {title}\n{json.dumps(data, indent=2, default=str)}"

    async def _fallback_llm_research(
        self, topic: str, description: str, purpose: str, mode: str, project_id: str
    ) -> str:
        """Fallback LLM-based research when engines are not configured."""
        fallback_system = (
            "You are a research assistant for presentation creation. "
            "Given a topic, gather key facts, statistics, market data, and insights. "
            "Return a structured research brief with: key findings, data points with sources "
            "(e.g., 'According to McKinsey 2025...' or '$380B market size — Source: Grand View Research'). "
            "Include competitor names, market size figures, growth rates, and trend data. "
            "Every number must have a source attribution."
        )
        fallback_user = (
            f"Research the following topic for a {purpose} presentation:\n\n"
            f"Topic: {topic}\n"
            f"Description: {description}\n\n"
            f"Provide key findings, statistics, market data, competitor insights, "
            f"and trend data with source attributions."
        )
        fallback_response = await self.router.complete(
            task_type=TaskType.NARRATIVE_STORYTELLING
            if mode == "premium"
            else TaskType.GENERAL,
            messages=[
                {"role": "system", "content": fallback_system},
                {"role": "user", "content": fallback_user},
            ],
            max_tokens=3000 if mode == "premium" else 1500,
            presentation_id=project_id,
            phase="research",
        )
        return fallback_response.content

    async def _execute_targeted_search(
        self, queries: list[str], project_id: str, mode: str
    ) -> str:
        """
        Execute the highest-priority search queries to gather factual data.
        Uses GPT-4o-mini to simulate search results from the topic context
        (in production this would call the actual search engines).
        """
        if not queries:
            return ""

        search_results = []
        for query in queries:
            try:
                response = await self.router.complete(
                    task_type=TaskType.STRUCTURED_JSON,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a search results simulator. Given a query, return "
                                "realistic, plausible facts and statistics that might appear in search results. "
                                "Include specific numbers, dates, and source names. "
                                "Return 3-5 data points as JSON array: "
                                '[{"title": "...", "snippet": "...", "source": "...", "year": 2025}]. '
                                "Make data realistic and cite real-sounding sources (McKinsey, Gartner, Statista, etc.). "
                                "IMPORTANT: Return ONLY valid JSON."
                            ),
                        },
                        {"role": "user", "content": query},
                    ],
                    max_tokens=1000,
                    presentation_id=project_id,
                    phase="search_query",
                )
                try:
                    results = json.loads(response.content.strip())
                    for r in results if isinstance(results, list) else []:
                        search_results.append(
                            f"- {r.get('title', '')}: {r.get('snippet', '')} "
                            f"(Source: {r.get('source', 'N/A')}, {r.get('year', '?')})"
                        )
                except json.JSONDecodeError:
                    pass
            except Exception:
                pass

        return (
            "\n".join(search_results) if search_results else "No specific data found."
        )

    # ── Phase D4: Style-Aware Design Quality Pass ────────────

    def _run_design_quality_pass(
        self, slides: list[dict], purpose: str, writing_style: str
    ) -> list[str]:
        """Run post-content design quality validation.

        Phase D4: Style-aware thresholds — adjusts strictness based on
        writing_style. YC pitch and minimalist are strict; academic and
        technical are relaxed for complexity.

        Returns list of warning strings.
        """
        warnings = []

        # Style-aware limits (founder feedback: no "nanny state")
        bullet_word_limit = self._get_bullet_word_limit(writing_style)
        max_bullets = 8 if writing_style in ("academic", "technical") else 6

        for i, slide in enumerate(slides):
            content = slide.get("content", {})
            title = content.get("title", "")
            bullets = content.get("bullets", [])
            layout = slide.get("layout", "")

            # Title length check (relaxed for academic/technical)
            title_words = len(title.split())
            title_limit = 12 if writing_style in ("academic", "technical") else 8
            if title_words > title_limit:
                warnings.append(
                    f"Slide {i + 1}: Title has {title_words} words "
                    f"(max {title_limit} for {writing_style}). Consider shortening."
                )

            # Bullet count check
            if len(bullets) > max_bullets:
                warnings.append(
                    f"Slide {i + 1}: {len(bullets)} bullets "
                    f"(max {max_bullets} for {writing_style}). "
                    f"Consider splitting or using chart layout."
                )

            # Bullet word length check (only warn if significantly over limit)
            for j, bullet in enumerate(bullets):
                word_count = len(str(bullet).split())
                if word_count > bullet_word_limit * 1.5:
                    warnings.append(
                        f"Slide {i + 1}, bullet {j + 1}: {word_count} words "
                        f"(limit {bullet_word_limit} for {writing_style}). "
                        f"Consider simplifying."
                    )

            # Purpose-specific checks
            if purpose in ("pitch", "fundraising", "investor"):
                title_lower = title.lower()
                bullets_text = " ".join(str(b).lower() for b in bullets)

                # Market slide must have TAM/SAM/SOM or market size
                if "market" in title_lower or "market" in bullets_text:
                    has_market_data = any(
                        kw in bullets_text
                        for kw in [
                            "tam",
                            "sam",
                            "som",
                            "total addressable",
                            "market size",
                            "$",
                            "billion",
                            "million",
                        ]
                    )
                    if not has_market_data:
                        warnings.append(
                            f"Slide {i + 1}: Market slide missing TAM/SAM/SOM "
                            f"or market size data."
                        )

                # Traction slide should show trajectory
                if "traction" in title_lower or "growth" in title_lower:
                    has_trajectory = any(
                        kw in bullets_text
                        for kw in [
                            "growth",
                            "increased",
                            "up",
                            "rising",
                            "cagr",
                            "year-over-year",
                            "yoy",
                            "%",
                        ]
                    )
                    if not has_trajectory:
                        warnings.append(
                            f"Slide {i + 1}: Traction slide should show growth "
                            f"trajectory (numbers trending up)."
                        )

                # Ask slide must have specific amount
                if (
                    "ask" in title_lower
                    or "funding" in title_lower
                    or "raise" in title_lower
                ):
                    has_amount = any(
                        kw in bullets_text
                        for kw in ["$", "million", "billion", "k", "seed", "series"]
                    )
                    if not has_amount:
                        warnings.append(
                            f"Slide {i + 1}: Ask slide missing specific funding amount."
                        )

        return warnings

    def _get_bullet_word_limit(self, writing_style: str) -> int:
        """Get bullet word limit based on writing style.

        Style-aware thresholds prevent false warnings for complex content.
        """
        limits = {
            "yc_pitch": 15,
            "minimalist": 12,
            "executive": 15,
            "conversational": 20,
            "narrative": 25,
            "storytelling": 25,
            "persuasive": 20,
            "descriptive": 25,
            "analytical": 30,
            "investor_update": 25,
            "technical": 35,
            "academic": 35,
        }
        return limits.get(writing_style, 20)

    async def _do_outline(
        self,
        topic: str,
        audience: str,
        purpose: str,
        writing_style: str,
        slide_count: int,
        research_context: str,
        mode: str,
        project_id: str,
    ) -> list[dict]:
        """
        Generate presentation outline using PromptEngine.

        B2: Replaces hardcoded "presentation architect" prompt with
        PromptEngine.compose_outline_prompt() which layers:
        - Outline base instructions + writing style voice + domain expertise
          (YC principles for pitch/demo_day) + quality guard reminders.
        """
        # Compose the system prompt using PromptEngine
        system_prompt = self.prompt_engine.compose_outline_prompt(
            style=writing_style,
            purpose=purpose,
        )

        # Build user prompt with research context
        user_prompt = (
            f"Create a {slide_count}-slide outline for:\n"
            f"Topic: {topic}\n"
            f"Audience: {audience}\n"
            f"Purpose: {purpose}\n"
            f"Writing Style: {writing_style}\n\n"
            f"Research context:\n{research_context[:2000]}\n\n"
            f"Available layouts: title-hero, two-column, bullets, bullets-with-image, full-image, "
            f"chart, comparison, timeline, quote, team-grid, kpi-dashboard.\n\n"
            f"Return a JSON array of {slide_count} slides, each with: "
            f"title, purpose, suggested_layout, and content_hints. "
            f"The outline should tell a compelling story with a clear narrative arc. "
            f"IMPORTANT: Return ONLY valid JSON array, no markdown fences."
        )

        response = await self.router.complete(
            task_type=TaskType.OUTLINE_PLANNING,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4000,
            response_format={"type": "json_object"} if mode == "premium" else None,
            presentation_id=project_id,
            phase="outline",
        )

        try:
            content = response.content.strip()
            # Handle both {"slides": [...]} and direct [...] formats
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "slides" in parsed:
                return parsed["slides"]
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except json.JSONDecodeError:
            # Fallback: generate a basic outline
            logger.warning("outline_json_failed_using_fallback", topic=topic)
            return self._fallback_outline(topic, slide_count)

    async def _do_content_generation(
        self,
        outline: list[dict],
        research_context: str,
        writing_style: str,
        purpose: str,
        mode: str,
        generate_notes: bool,
        project_id: str,
        progress_callback=None,
    ) -> list[dict]:
        """
        Generate content for all slides.

        Accepts writing_style and purpose to pass through to each slide's
        PromptEngine-powered generation. Runs quality guards on each slide
        and attaches warnings to the slide output.

        Phase E2: After text content is generated, fires image generation
        tasks in the background (fire-and-forget). Images are pushed to
        frontend via WebSocket when ready.
        """
        slides = []
        total = len(outline)

        # Collect image generation tasks for fire-and-forget
        image_tasks = []

        for i, slide_def in enumerate(outline):
            if progress_callback:
                await progress_callback(
                    i / max(total, 1), f"Writing slide {i + 1}/{total}..."
                )

            slide = await self._generate_single_slide(
                slide_def=slide_def,
                context=research_context,
                previous_slide=slides[-1] if slides else None,
                writing_style=writing_style,
                purpose=purpose,
                generate_notes=generate_notes and mode == "premium",
                project_id=project_id,
            )
            slides.append(slide)

        # Phase E2: Fire-and-forget image generation for all slides
        # Don't await — let images populate in background
        image_tasks = self._fire_image_generation(
            slides=slides,
            project_id=project_id,
            writing_style=writing_style,
        )

        return slides

    async def _generate_single_slide(
        self,
        slide_def: dict,
        context: str,
        previous_slide: Optional[dict],
        writing_style: str,
        purpose: str,
        generate_notes: bool,
        project_id: str,
    ) -> dict:
        """
        Generate content for a single slide using PromptEngine.

        B3: Replaces generic "professional slide content writer" prompt with
        PromptEngine.compose_slide_prompt() which layers:
        - Base slide system + layout-specific format + style voice + domain expertise
          (investor overrides for chart/traction, data presentation rules) + quality guard reminders.

        After content generation, runs quality guards and attaches warnings
        to the output dict for downstream awareness.
        """
        layout = slide_def.get("suggested_layout", slide_def.get("layout", "bullets"))
        title = slide_def.get("title", "Untitled")
        slide_purpose = slide_def.get("purpose", "")
        hints = slide_def.get("content_hints", "")
        is_investor = purpose.lower() in {
            "pitch",
            "fundraising",
            "investor",
            "investor_update",
            "series_a",
            "seed",
            "demo_day",
        }

        # Compose the system prompt using PromptEngine
        system_prompt = self.prompt_engine.compose_slide_prompt(
            layout=layout,
            style=writing_style,
            purpose=purpose,
            slide_purpose=slide_purpose,
        )

        # Build previous slide context for narrative continuity
        prev_context = ""
        if previous_slide:
            prev_title = previous_slide.get("content", {}).get("title", "")
            prev_bullets = previous_slide.get("content", {}).get("bullets", [])
            if prev_bullets:
                prev_context = f"\nPrevious slide: '{prev_title}' — {prev_bullets[0] if prev_bullets else ''}"

        # Build user prompt with enhanced context
        user_context = context[:1000]
        user_prompt = (
            f"Generate slide content:\n"
            f"Title: {title}\n"
            f"Purpose: {slide_purpose}\n"
            f"Layout: {layout}\n"
            f"Content hints: {hints}\n"
            f"Writing Style: {writing_style}\n"
            f"Presentation Purpose: {purpose}\n\n"
            f"Research Context:\n{user_context}\n"
            f"{prev_context}\n\n"
            f"Return ONLY valid JSON with the appropriate content fields for this layout.\n"
            f"For 'bullets': title + bullets (array of 3-6 strings). "
            f"For 'chart': title + chart_type (bar/line/pie) + chart_data with labels and datasets. "
            f"Every number over $1M must have a source attribution like (Source: Name, Year)."
        )

        # Route based on layout type
        if layout in ("chart", "kpi-dashboard", "comparison"):
            task = TaskType.STRUCTURED_JSON
        elif layout in ("title-hero", "quote"):
            task = TaskType.NARRATIVE_STORYTELLING
        else:
            task = TaskType.STRUCTURED_JSON

        response = await self.router.complete(
            task_type=task,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2000,
            presentation_id=project_id,
            phase="content",
        )

        try:
            content = json.loads(response.content.strip())
        except json.JSONDecodeError:
            logger.warning("slide_json_decode_failed", layout=layout, title=title)
            content = {"title": title, "bullets": [response.content[:200]]}

        # Ensure title is present
        if "title" not in content:
            content["title"] = title

        # ── Run quality guards on generated content ──
        warnings = []
        try:
            guard_result = run_quality_guards(
                content=content,
                layout=layout,
                purpose=purpose,
                is_investor_deck=is_investor,
            )
            if not guard_result.passed:
                if guard_result.fluff_found:
                    warnings.extend(f"Fluff: {w}" for w in guard_result.fluff_found)
                if guard_result.unsourced_claims:
                    warnings.extend(
                        f"Missing source: {w}" for w in guard_result.unsourced_claims
                    )
                if guard_result.density_issues:
                    warnings.extend(
                        f"Density: {w}" for w in guard_result.density_issues
                    )
                if guard_result.investor_issues:
                    warnings.extend(
                        f"Investor: {w}" for w in guard_result.investor_issues
                    )
                if guard_result.warnings:
                    warnings.extend(guard_result.warnings)
        except Exception as e:
            logger.warning("quality_guards_failed", error=str(e))

        return {
            "layout": layout,
            "content": content,
            "quality_warnings": warnings,
        }

    # ── Phase E2: Fire-and-Forget Image Generation ───────────

    async def _generate_slide_images_background(
        self,
        slides: list[dict],
        theme: dict,
        presentation_id: str,
        user_id: str,
    ) -> None:
        """Generate images for all slides in background (non-blocking).

        Phase E2: After text content is ready, dispatch image generation
        for each slide that supports images. These run in parallel and
        update slides via WebSocket when ready.
        """
        from app.services.image_service import ImageService

        image_service = ImageService()
        tasks = []

        for i, slide in enumerate(slides):
            layout = slide.get("layout", "bullets")
            content = slide.get("content", {})

            # Skip layouts that don't benefit from AI images
            if layout in ("chart", "kpi-dashboard", "team-grid", "blank"):
                continue

            # Fire-and-forget: create task but don't await
            task = asyncio.create_task(
                self._generate_and_attach_image(
                    slide=slide,
                    image_service=image_service,
                    project_id=presentation_id,
                    slide_index=i,
                    user_id=user_id,
                )
            )
            tasks.append(task)

        if tasks:
            logger.info(
                "image_generation_fired",
                count=len(tasks),
                project_id=presentation_id,
            )

        # Wait for all images to complete (background task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _generate_and_attach_image(
        self,
        slide: dict,
        image_service: "ImageService",
        project_id: str,
        slide_index: int,
        user_id: str,
    ) -> None:
        """Generate image for a slide and attach URL to slide content."""
        layout = slide.get("layout", "bullets")
        content = slide.get("content", {})

        # Get theme from DB for style-aware prompting
        theme = {}
        try:
            pres = await self.db.presentations.find_one({"_id": project_id})
            if pres and pres.get("theme_id"):
                theme = await self.db.themes.find_one({"_id": pres["theme_id"]}) or {}
        except Exception:
            pass

        image_url = await image_service.generate_slide_image(
            content=content,
            layout=layout,
            theme=theme or {},
            presentation_id=project_id,
            slide_index=slide_index,
            user_id=user_id,
        )

        if image_url:
            # Attach image URL to slide content
            slide["content"]["image_url"] = image_url
            logger.info(
                "image_attached",
                slide=content.get("title", "")[:30],
                layout=layout,
            )
        else:
            logger.info(
                "image_skipped",
                slide=content.get("title", "")[:30],
                layout=layout,
                reason="generation_failed_or_not_needed",
            )

    def _dispatch_thumbnail_task(self, presentation_id: str) -> None:
        """Dispatch thumbnail generation Celery task."""
        try:
            from celery_worker import celery_app

            celery_app.send_task(
                "thumbnail.generate",
                args=[presentation_id],
            )
            logger.info("thumbnail_task_dispatched", presentation_id=presentation_id)
        except Exception as e:
            logger.warning("thumbnail_task_failed", error=str(e))

    async def _do_outline(
        self,
        slide_def: dict,
        user_inputs: dict,
        template_style: str,
        template_category: str,
        mode: str,
        project_id: str,
    ) -> dict:
        """
        Fill a template slide's placeholders with AI + user content.

        B4: Uses PromptEngine.compose_template_prompt() with the template's
        default_writing_style and category for domain-appropriate generation.
        This means fundraising templates use YC principles, sales templates use
        persuasion principles, internal templates use data presentation rules.
        """
        placeholders = slide_def.get("placeholders", {})
        ai_instructions = slide_def.get("ai_instructions", "")
        layout = slide_def.get("layout", "bullets")
        slide_purpose = slide_def.get("purpose", "")

        # Compose system prompt using PromptEngine
        system_prompt = self.prompt_engine.compose_template_prompt(
            template_category=template_category,
            style=template_style,
        )

        # Replace user-provided values
        filled = {}
        needs_ai = []
        for key, template_val in placeholders.items():
            if (
                isinstance(template_val, str)
                and template_val.startswith("{{")
                and template_val.endswith("}}")
            ):
                param_name = template_val[2:-2]
                if param_name in user_inputs:
                    filled[key] = user_inputs[param_name]
                else:
                    needs_ai.append((key, param_name))
            else:
                filled[key] = template_val

        # AI-fill remaining placeholders using PromptEngine-composed prompt
        if needs_ai and ai_instructions:
            fields_desc = ", ".join([f'"{k}" ({v})' for k, v in needs_ai])
            user_prompt = (
                f"Template category: {template_category}\n"
                f"Writing style: {template_style}\n"
                f"Slide purpose: {slide_purpose}\n\n"
                f"Template instructions: {ai_instructions}\n"
                f"Already filled fields: {json.dumps({k: v for k, v in filled.items() if isinstance(v, str)})}\n"
                f"User-provided data: {json.dumps(user_inputs)}\n\n"
                f"Generate content for these missing fields: {fields_desc}\n\n"
                f"Return a JSON object with ONLY the field names as keys and the generated content as values. "
                f"IMPORTANT: Return ONLY valid JSON, no markdown fences."
            )

            response = await self.router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1500,
                presentation_id=project_id,
                phase="template_fill",
            )

            try:
                ai_content = json.loads(response.content.strip())
                for key, _ in needs_ai:
                    if key in ai_content:
                        filled[key] = ai_content[key]
                    else:
                        filled[key] = f"[{key}]"
            except json.JSONDecodeError:
                logger.warning("template_fill_json_failed", fallback=True)
                # Use raw response as fallback
                for key, param_name in needs_ai:
                    filled[key] = f"[{param_name}]"

        return {
            "layout": layout,
            "content": filled,
        }

    def _fallback_outline(self, topic: str, slide_count: int) -> list[dict]:
        """Fallback outline if AI fails."""
        base_slides = [
            {
                "title": topic,
                "purpose": "Introduction",
                "suggested_layout": "title-hero",
                "content_hints": "",
            },
            {
                "title": "The Problem",
                "purpose": "Problem statement",
                "suggested_layout": "two-column",
                "content_hints": "",
            },
            {
                "title": "Our Solution",
                "purpose": "Solution overview",
                "suggested_layout": "bullets-with-image",
                "content_hints": "",
            },
            {
                "title": "Market Opportunity",
                "purpose": "Market size",
                "suggested_layout": "chart",
                "content_hints": "",
            },
            {
                "title": "How It Works",
                "purpose": "Product details",
                "suggested_layout": "bullets",
                "content_hints": "",
            },
            {
                "title": "Business Model",
                "purpose": "Revenue model",
                "suggested_layout": "two-column",
                "content_hints": "",
            },
            {
                "title": "Traction",
                "purpose": "Progress and metrics",
                "suggested_layout": "kpi-dashboard",
                "content_hints": "",
            },
            {
                "title": "Competition",
                "purpose": "Competitive landscape",
                "suggested_layout": "comparison",
                "content_hints": "",
            },
            {
                "title": "The Team",
                "purpose": "Team overview",
                "suggested_layout": "team-grid",
                "content_hints": "",
            },
            {
                "title": "The Ask",
                "purpose": "Call to action",
                "suggested_layout": "title-hero",
                "content_hints": "",
            },
        ]
        return base_slides[: min(slide_count, len(base_slides))]


# ── Helper function for research planner prompt construction ─────

# Purpose-aware research scoping constants
_PURPOSE_RESEARCH_CONFIGS = {
    "pitch": {
        "research_focus": (
            "market size and growth data, competitor analysis, industry trends, "
            "TAM/SAM/SOM data, unit economics benchmarks, traction benchmarks for similar companies, "
            "investor psychology and what metrics matter most"
        ),
        "data_priorities": [
            "Total Addressable Market (TAM) with source",
            "Market growth rate (CAGR)",
            "Top 3-5 competitors and their differentiation",
            "Industry-specific unit economics benchmarks (LTV/CAC, margin)",
            "Growth rate benchmarks for similar startups",
        ],
    },
    "demo_day": {
        "research_focus": (
            "traction benchmarks, market opportunity, competitive differentiation, "
            "growth rate validation, comparable company exits or valuations"
        ),
        "data_priorities": [
            "Market size (single compelling number with source)",
            "Growth rate benchmarks for the industry",
            "Comparable companies or exits in the space",
        ],
    },
    "investor_update": {
        "research_focus": (
            "industry benchmarks for MRR, revenue, growth rates, burn rates, "
            "competitive developments, market shifts relevant to the company's sector"
        ),
        "data_priorities": [
            "Industry benchmark growth rates for context",
            "Recent competitor news or funding rounds",
            "Market trend data",
        ],
    },
    "quarterly": {
        "research_focus": (
            "industry benchmarks, KPI frameworks, best practices for quarterly reporting in this sector"
        ),
        "data_priorities": [
            "Industry benchmark metrics for comparison",
            "Best practice KPI frameworks",
            "Recent industry news",
        ],
    },
    "internal": {
        "research_focus": (
            "best practices, frameworks, KPI suggestions, industry standards"
        ),
        "data_priorities": [
            "Best practice frameworks",
            "Industry standards and benchmarks",
            "Relevant case studies",
        ],
    },
    "education": {
        "research_focus": (
            "curriculum standards, teaching frameworks, relevant statistics about the topic"
        ),
        "data_priorities": [
            "Topic-specific statistics",
            "Teaching/learning frameworks",
            "Industry examples",
        ],
    },
    "sales": {
        "research_focus": (
            "customer success stories, ROI benchmarks, industry pain points, competitor weaknesses"
        ),
        "data_priorities": [
            "ROI benchmarks from similar tool adoption",
            "Industry pain points with data",
            "Competitor weaknesses or gaps",
        ],
    },
}


def _build_research_planner_prompt(
    topic: str,
    description: str,
    purpose: str,
    mode: str,
) -> str:
    """Build purpose-aware research planner prompt (B1)."""
    config = _PURPOSE_RESEARCH_CONFIGS.get(purpose, _PURPOSE_RESEARCH_CONFIGS["pitch"])

    token_budget = "comprehensive" if mode == "premium" else "standard"
    return (
        f"Topic: {topic}\n"
        f"Description: {description}\n"
        f"Purpose: {purpose}\n"
        f"Token Budget: {token_budget}\n\n"
        f"Research focus areas for this presentation type:\n"
        f"{config['research_focus']}\n\n"
        f"Prioritize these specific data points:\n"
        f"  - " + "\n  - ".join(config["data_priorities"]) + "\n\n"
        f"Plan a research strategy that gathers facts, statistics, market data, "
        f"competitor information, and trend data. "
        f"Every data point should be useful for slide generation and have a source attribution."
    )
