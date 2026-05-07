"""
Unified Pipeline Service — V3 Generation Orchestrator.

Routes generation requests through either:
  STANDARD mode  → V7 Orchestrator (fast, ~30s, single-format)
  PREMIUM mode   → Brain MCP research pipeline → V7 Orchestrator (2-5min, multi-format, evidence report)

This is the single entry point for V3 generation.  It is called either
directly (for sync tests) or from the Celery task ``generate_unified_deck``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.mcp.brain_mcp.research.models import (
    BudgetMode,
    ContentEvent,
    SlideContentContract,
    SlideKind,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════


class UnifiedGenerationRequest(BaseModel):
    """V3 generation request — supports both standard and premium modes."""

    topic: str
    description: str = ""
    audience: str = "investors"
    purpose: str = "pitch"
    mode: str = "standard"  # "standard" | "premium"
    slide_count: int = Field(default=10, ge=3, le=30)
    writing_style: str = "yc_crisp"
    theme_id: Optional[str] = None
    custom_colors: Optional[dict] = None
    language: str = "en"
    generate_notes: bool = True
    target_formats: list[str] = Field(default_factory=lambda: ["revealjs"])
    company_name: Optional[str] = None
    outline: Optional[dict] = None  # Pre-built outline; auto-generated if None
    user_id: str = ""


class UnifiedGenerationResult(BaseModel):
    """V3 generation result — unified output for both modes."""

    success: bool
    deck_id: str
    mode: str
    presentation_id: Optional[str] = None
    slides: list[dict] = Field(default_factory=list)
    strategy: Optional[dict] = None
    research: Optional[dict] = None
    design: Optional[dict] = None
    quality_score: float = 0.0
    evidence_report: Optional[dict] = None  # Premium only
    exports: list[dict] = Field(default_factory=list)
    total_time_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)
    coherence_score: float = 0.0  # Cross-slide consistency score


class UnifiedPipelineService:
    """
    V3 Unified Pipeline — Standard / Premium mode routing.

    Standard mode:
      1. Build V7GenerationConfig (fast_mode=True)
      2. Run V7Orchestrator.generate() (no evidence_contracts)
      3. Return result

    Premium mode:
      1. Run Brain MCP research pipeline (async, 10-stage)
      2. Run cross-slide consistency validation
      3. Build V7GenerationConfig (fast_mode=False)
      4. Run V7Orchestrator.generate(evidence_contracts=contracts)
      5. Return result with evidence_report
    """

    def __init__(self, db: Any) -> None:
        self.db = db

    async def generate(
        self,
        request: UnifiedGenerationRequest,
        deck_id: str,
        event_emitter: Any = None,
    ) -> UnifiedGenerationResult:
        """
        Run the unified generation pipeline.

        Args:
            request: Generation parameters
            deck_id: Unique deck run identifier
            event_emitter: Optional ContentEventEmitter for progress streaming
        """
        start_time = time.time()

        try:
            if request.mode == "premium":
                result = await self._run_premium(request, deck_id, event_emitter)
            else:
                result = await self._run_standard(request, deck_id, event_emitter)

            result.total_time_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            logger.exception("unified_pipeline_failed", deck_id=deck_id, error=str(e))
            return UnifiedGenerationResult(
                success=False,
                deck_id=deck_id,
                mode=request.mode,
                errors=[str(e)],
                total_time_ms=(time.time() - start_time) * 1000,
            )

    # ── Standard Mode ────────────────────────────────────────

    async def _run_standard(
        self,
        request: UnifiedGenerationRequest,
        deck_id: str,
        emitter: Any = None,
    ) -> UnifiedGenerationResult:
        """Standard mode: V7 Orchestrator only, no brain_mcp research."""
        from app.services.slides_new.orchestrator.v7_orchestrator import (
            V7GenerationConfig,
            V7Orchestrator,
        )

        config = V7GenerationConfig(
            fast_mode=True,
            research_depth="quick",
            enable_3d=False,
            target_renderers=["revealjs"],
            max_qa_iterations=1,
            timeout_per_agent=15,
            parallel_research_design=True,
            enable_learning=False,
        )

        if emitter:
            await emitter.emit(
                ContentEvent.DECK_CONTEXT_READY,
                data={"mode": "standard", "topic": request.topic},
                stage="strategy",
                message="Starting standard generation pipeline",
            )

        orchestrator = V7Orchestrator(self.db)
        v7_result = await orchestrator.generate(
            user_id=request.user_id,
            topic=request.topic,
            description=request.description,
            purpose=request.purpose,
            audience=request.audience,
            slide_count=request.slide_count,
            company_name=request.company_name,
            custom_theme=request.custom_colors,
            config=config,
        )

        if emitter:
            await emitter.emit(
                ContentEvent.DECK_CONTENT_COMPLETE,
                data={"slides": len(v7_result.slides)},
                progress=1.0,
                stage="complete",
                message="Standard generation complete",
            )

        return UnifiedGenerationResult(
            success=v7_result.success,
            deck_id=deck_id,
            mode="standard",
            presentation_id=v7_result.presentation_id,
            slides=v7_result.slides,
            strategy=v7_result.strategy,
            research=v7_result.research,
            design=v7_result.design,
            quality_score=v7_result.quality_score,
            exports=[{"format": "revealjs", "status": "ready"}],
            errors=v7_result.errors,
        )

    # ── Premium Mode ─────────────────────────────────────────

    async def _run_premium(
        self,
        request: UnifiedGenerationRequest,
        deck_id: str,
        emitter: Any = None,
    ) -> UnifiedGenerationResult:
        """
        Premium mode: Brain MCP research pipeline → cross-validation →
        EvidenceBridge → V7 Orchestrator with evidence.
        """
        from app.services.slides_new.orchestrator.v7_orchestrator import (
            V7GenerationConfig,
            V7Orchestrator,
        )

        budget_mode = self._build_budget_mode(request.mode, request.purpose)

        # Stage 1: Run Brain MCP research pipeline
        if emitter:
            await emitter.emit(
                ContentEvent.DECK_CONTEXT_READY,
                data={"mode": "premium", "budget": budget_mode.value},
                stage="research",
                message="Starting premium evidence pipeline",
            )

        contracts, pipeline_meta = await self._run_brain_mcp_pipeline(
            deck_id=deck_id,
            outline=request.outline or {"slides": self._build_default_outline(
                request.topic, request.slide_count
            )},
            budget_mode=budget_mode,
            style=request.writing_style,
            topic=request.topic,
            audience=request.audience,
            emitter=emitter,
        )

        # Stage 2: Cross-slide consistency check
        if emitter:
            await emitter.emit(
                ContentEvent.CITATIONS_VERIFIED,
                data={"contracts": len(contracts)},
                stage="verification",
                message="Running cross-slide consistency validation",
            )

        from app.mcp.brain_mcp.prompts.quality_guards import (
            cross_slide_consistency_check,
            deck_level_coherence_score,
        )

        consistency_issues = cross_slide_consistency_check(contracts)
        coherence = deck_level_coherence_score(contracts)

        if consistency_issues:
            logger.warning(
                "consistency_issues_found",
                deck_id=deck_id,
                issues=len(consistency_issues),
                critical=sum(1 for i in consistency_issues if i["severity"] == "critical"),
            )

        # Stage 3: V7 Orchestrator with evidence
        config = V7GenerationConfig(
            fast_mode=False,
            research_depth="deep",
            enable_3d=True,
            target_renderers=["revealjs", "pptx", "html"],
            max_qa_iterations=3,
            timeout_per_agent=60,
            parallel_research_design=True,
            enable_learning=True,
        )

        if emitter:
            await emitter.emit(
                ContentEvent.SLIDE_BRIEF_READY,
                data={"contracts": len(contracts)},
                stage="generation",
                message="Starting V7 agent pipeline with premium evidence",
            )

        orchestrator = V7Orchestrator(self.db)
        v7_result = await orchestrator.generate(
            user_id=request.user_id,
            topic=request.topic,
            description=request.description,
            purpose=request.purpose,
            audience=request.audience,
            slide_count=request.slide_count,
            company_name=request.company_name,
            custom_theme=request.custom_colors,
            config=config,
            evidence_contracts=contracts,
        )

        if emitter:
            await emitter.emit(
                ContentEvent.DECK_CONTENT_COMPLETE,
                data={"slides": len(v7_result.slides), "coherence": coherence},
                progress=1.0,
                stage="complete",
                message="Premium generation complete",
            )

        # Build evidence report
        evidence_report = {
            "pipeline_meta": pipeline_meta,
            "consistency_issues": consistency_issues,
            "coherence_score": coherence,
            "total_contracts": len(contracts),
            "contracts_summary": [
                {
                    "slide_id": c.slide_id,
                    "slide_kind": c.slide_kind.value,
                    "evidence_score": c.evidence_score,
                    "citation_count": len(c.citations),
                }
                for c in contracts
            ],
        }

        if v7_result.evidence_report:
            evidence_report["v7_evidence_metrics"] = v7_result.evidence_report

        return UnifiedGenerationResult(
            success=v7_result.success,
            deck_id=deck_id,
            mode="premium",
            presentation_id=v7_result.presentation_id,
            slides=v7_result.slides,
            strategy=v7_result.strategy,
            research=v7_result.research,
            design=v7_result.design,
            quality_score=v7_result.quality_score,
            evidence_report=evidence_report,
            exports=[
                {"format": "revealjs", "status": "ready"},
                {"format": "pptx", "status": "ready"},
                {"format": "html", "status": "ready"},
            ],
            errors=v7_result.errors,
            coherence_score=coherence,
        )

    # ── Brain MCP Pipeline (extracted from research_tasks) ───

    async def _run_brain_mcp_pipeline(
        self,
        deck_id: str,
        outline: dict,
        budget_mode: BudgetMode,
        style: str,
        topic: str,
        audience: str,
        emitter: Any = None,
    ) -> tuple[list[SlideContentContract], dict]:
        """
        Run the full Brain MCP 10-stage research pipeline.

        Returns:
            Tuple of (contracts, pipeline_metadata)
        """
        import redis.asyncio as aioredis
        from app.config import settings
        from app.mcp.brain_mcp.research.provider_registry import ProviderRegistry
        from app.mcp.brain_mcp.research.circuit_breaker import CircuitBreaker
        from app.mcp.brain_mcp.research.content_events import ContentEventEmitter
        from app.mcp.brain_mcp.research.research_router import ResearchRouter
        from app.mcp.brain_mcp.research.query_planner import QueryPlanner
        from app.mcp.brain_mcp.research.evidence_assembler import EvidenceAssembler
        from app.mcp.brain_mcp.research.evidence_graph import EvidenceGraph
        from app.mcp.brain_mcp.research.cross_validator import CrossValidator
        from app.mcp.brain_mcp.research.community_summarizer import CommunitySummarizer
        from app.mcp.brain_mcp.research.debate_loop import DebateLoop
        from app.mcp.brain_mcp.research.freshness_scorer import FreshnessScorer
        from app.mcp.brain_mcp.generators.slide_generator_v2 import SlideGeneratorV2
        from app.mcp.brain_mcp.prompts.style_catalog import get_style
        from app.services.llm.model_router import ModelRouter

        start_time = time.time()
        style_profile = get_style(style)

        # Initialize Redis for internal events
        redis_client = None
        try:
            redis_client = aioredis.from_url(
                settings.REDIS_URL, decode_responses=True
            )
        except Exception as e:
            logger.warning("Redis unavailable for pipeline: %s", e)

        # Use provided emitter or create a new one
        internal_emitter = emitter
        if internal_emitter is None:
            internal_emitter = ContentEventEmitter(deck_id, redis_client)

        # Initialize pipeline components
        registry = ProviderRegistry(settings)
        breaker = CircuitBreaker(redis_client)
        router = ResearchRouter(registry, breaker, internal_emitter)
        planner = QueryPlanner()
        assembler = EvidenceAssembler()
        graph = EvidenceGraph()
        cross_validator = CrossValidator()
        freshness_scorer = FreshnessScorer()
        summarizer = CommunitySummarizer()

        model_router = ModelRouter.get_instance()
        debate = DebateLoop(model_router, internal_emitter)
        generator = SlideGeneratorV2(model_router)

        # ChromaDB for evidence indexing (best-effort)
        chroma_evidence = None
        try:
            from app.services.chromadb_service import ChromaService
            from app.services.chromadb_evidence import ChromaDBEvidence
            chroma_evidence = ChromaDBEvidence(ChromaService())
        except Exception:
            logger.warning("ChromaDB unavailable in premium pipeline")

        slides = outline.get("slides", [])
        all_packets = []
        contracts: list[SlideContentContract] = []
        errors = []

        try:
            # ── Stage 1: Intent + plan ─────────────────────────
            await internal_emitter.emit(
                ContentEvent.INTENT_CLASSIFIED,
                data={"audience": audience, "style": style, "budget": budget_mode.value},
                stage="research",
                message="Research pipeline initialized",
            )

            # ── Stage 2: Research per slide ────────────────────
            for idx, slide in enumerate(slides):
                slide_id = slide.get("id", f"slide_{idx}")
                slide_kind_str = slide.get("kind", slide.get("type", "problem"))
                try:
                    slide_kind = SlideKind(slide_kind_str)
                except ValueError:
                    slide_kind = SlideKind.PROBLEM

                queries = await planner.plan_queries(
                    topic, slide.get("title", ""), slide_kind, audience
                )

                # ChromaDB cross-deck reuse
                reused = []
                if chroma_evidence:
                    try:
                        reused = await chroma_evidence.search_similar(
                            query=f"{topic} {slide.get('title', '')}",
                            slide_kind=slide_kind,
                            min_confidence=0.6,
                            n_results=5,
                            exclude_deck_id=deck_id,
                        )
                    except Exception:
                        pass

                packets = await router.research_slide(
                    slide_id=slide_id,
                    slide_kind=slide_kind,
                    queries=queries,
                    topic=topic,
                    budget_mode=budget_mode,
                )

                # Merge reused evidence
                existing_claims = {p.claim.lower().strip() for p in packets}
                for r in reused:
                    if r.claim.lower().strip() not in existing_claims:
                        packets.append(r)
                        existing_claims.add(r.claim.lower().strip())

                # Index in ChromaDB
                if chroma_evidence and packets:
                    try:
                        await chroma_evidence.index_batch(packets, deck_id)
                    except Exception:
                        pass

                for pkt in packets:
                    graph.add_fact_packet(pkt)
                all_packets.extend(packets)

            # ── Stage 3: Cross-validation ──────────────────────
            all_packets = cross_validator.validate(all_packets)

            # ── Stage 4: Freshness scoring ─────────────────────
            for pkt in all_packets:
                pkt.confidence = freshness_scorer.adjust_confidence(
                    pkt, SlideKind.MARKET
                )

            # ── Stage 5: Community summaries ───────────────────
            community = await summarizer.summarize(all_packets, topic)

            # ── Stage 6-7: Generate content per slide ──────────
            for idx, slide in enumerate(slides):
                slide_id = slide.get("id", f"slide_{idx}")
                slide_kind_str = slide.get("kind", slide.get("type", "problem"))
                try:
                    slide_kind = SlideKind(slide_kind_str)
                except ValueError:
                    slide_kind = SlideKind.PROBLEM

                bundle = assembler.assemble(slide_id, slide_kind, all_packets)

                # Run debate for pitch decks
                is_pitch = audience.lower() in ("investors", "vcs", "angels")
                if is_pitch and slide_kind not in (SlideKind.TITLE, SlideKind.TEAM):
                    try:
                        debate_outcome = await debate.run_debate(
                            bundle, topic, slide_kind
                        )
                        bundle.approved_claim_ids = debate_outcome.approved_claims
                        bundle.debate_approved = True
                    except Exception as e:
                        logger.warning("Debate failed: %s", e)
                        bundle.approved_claim_ids = [p.id for p in bundle.evidence_packets]
                else:
                    bundle.approved_claim_ids = [p.id for p in bundle.evidence_packets]

                try:
                    deck_context = {
                        "community_summaries": community,
                        "graph_summary": graph.get_global_summary(),
                        "slide_index": idx,
                        "total_slides": len(slides),
                    }
                    contract = await generator.generate(
                        evidence_bundle=bundle,
                        style=style_profile,
                        topic=topic,
                        audience=audience,
                        budget_mode=budget_mode,
                        deck_context=deck_context,
                    )
                    contracts.append(contract)
                except Exception as e:
                    logger.error("Generation failed for %s: %s", slide_id, e)
                    errors.append({"slide_id": slide_id, "error": str(e)})

            pipeline_meta = {
                "total_fact_packets": len(all_packets),
                "total_contracts": len(contracts),
                "total_errors": len(errors),
                "total_time_ms": (time.time() - start_time) * 1000,
                "budget_mode": budget_mode.value,
                "evidence_graph_nodes": len(graph.to_dict().get("nodes", [])),
                "community_themes": list(community.keys()) if community else [],
            }

            return contracts, pipeline_meta

        finally:
            if redis_client:
                await redis_client.aclose()

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _build_budget_mode(mode: str, purpose: str) -> BudgetMode:
        """Map request mode + purpose to BudgetMode."""
        if mode != "premium":
            return BudgetMode.lean
        purpose_lower = purpose.lower()
        if any(kw in purpose_lower for kw in ("pitch", "fundrais", "investor", "demo_day")):
            return BudgetMode.hero
        return BudgetMode.balanced

    @staticmethod
    def _build_default_outline(topic: str, slide_count: int) -> list[dict]:
        """Build a default pitch deck outline when none is provided.

        Supports up to 30 slides by extending core kinds with supplementary topics.
        """
        core_kinds = [
            ("title", f"{topic}"),
            ("problem", "The Problem"),
            ("solution", "Our Solution"),
            ("market", "Market Opportunity"),
            ("product_demo", "Product"),
            ("competition", "Competitive Landscape"),
            ("gtm", "Go-to-Market Strategy"),
            ("traction", "Traction & Milestones"),
            ("team", "The Team"),
            ("financial", "Financial Projections"),
            ("ask", "The Ask"),
        ]
        supplementary_kinds = [
            ("why_now", "Why Now"),
            ("market", "Case Study"),
            ("product_demo", "Features Deep Dive"),
            ("financial", "Unit Economics"),
            ("gtm", "Partnerships & Ecosystem"),
            ("traction", "Customer Testimonials"),
            ("competition", "Market Expansion"),
            ("product_demo", "Technology Architecture"),
            ("financial", "Operational Metrics"),
            ("market", "Strategic Vision"),
            ("gtm", "Growth Roadmap"),
            ("traction", "Key Milestones"),
            ("problem", "Risk Analysis"),
            ("solution", "Implementation Plan"),
            ("market", "Industry Trends"),
            ("financial", "Revenue Breakdown"),
            ("product_demo", "User Journey"),
            ("team", "Advisory Board"),
            ("appendix", "Appendix"),
        ]
        # Use core, extend with supplementary if needed
        all_kinds = core_kinds + supplementary_kinds
        slides = []
        for idx, (kind, title) in enumerate(all_kinds[:slide_count]):
            slides.append({
                "id": f"slide_{idx}",
                "kind": kind,
                "title": title,
            })
        return slides
