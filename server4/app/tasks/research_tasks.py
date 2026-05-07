"""
Background research tasks for slide content generation.

These run in Celery workers, not in the HTTP request path.
Progress is published via Redis pub/sub for WebSocket streaming.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_event_loop():
    """Get or create an event loop for async code in Celery workers."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


@celery_app.task(bind=True, max_retries=2, time_limit=600, soft_time_limit=540)
def generate_deck_content(
    self,
    deck_id: str,
    outline: dict,
    budget_mode: str = "lean",
    style: str = "yc_crisp",
    topic: str = "",
    audience: str = "investors",
    user_id: str = "",
):
    """
    Full pipeline: research -> evidence -> debate -> generate -> verify.

    This is the main orchestrator task. It:
    1. Initializes all components (router, circuit breaker, emitter, etc.)
    2. Plans research queries for each slide
    3. Executes parallel research per slide
    4. Builds evidence graph
    5. Cross-validates evidence
    6. Generates community summaries
    7. Runs pitch debate (if investor deck)
    8. Generates slide content via SlideGeneratorV2
    9. Verifies citations
    10. Saves results to MongoDB
    11. Emits progress events throughout

    All async code runs via asyncio event loop.
    """
    loop = _get_event_loop()
    return loop.run_until_complete(
        _generate_deck_content_async(
            self, deck_id, outline, budget_mode, style, topic, audience, user_id
        )
    )


async def _generate_deck_content_async(
    task, deck_id, outline, budget_mode, style, topic, audience, user_id
):
    """Async implementation of the full generation pipeline."""
    import redis.asyncio as aioredis
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings
    from app.mcp.brain_mcp.research.models import (
        BudgetMode,
        SlideKind,
        ContentEvent,
    )
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
    mode = BudgetMode(budget_mode)
    style_profile = get_style(style)

    # ── Initialize Redis for events ──────────────────────────
    redis_client = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    except Exception as e:
        logger.warning("Redis unavailable for events: %s", e)

    # ── Initialize MongoDB for persistence ───────────────────
    mongo_client = None
    db = None
    try:
        mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = mongo_client[settings.MONGODB_DB_NAME]
    except Exception as e:
        logger.warning("MongoDB unavailable: %s", e)

    # ── Initialize pipeline components ───────────────────────
    emitter = ContentEventEmitter(deck_id, redis_client)
    registry = ProviderRegistry(settings)
    breaker = CircuitBreaker(redis_client)
    router = ResearchRouter(registry, breaker, emitter)
    planner = QueryPlanner()
    assembler = EvidenceAssembler()
    graph = EvidenceGraph()
    cross_validator = CrossValidator()
    freshness_scorer = FreshnessScorer()
    summarizer = CommunitySummarizer()

    model_router = ModelRouter.get_instance()
    debate = DebateLoop(model_router, emitter)
    generator = SlideGeneratorV2(model_router)

    # ── Initialize ChromaDB for evidence indexing/reuse (best-effort) ──
    chroma_evidence = None
    try:
        from app.services.chromadb_service import ChromaService
        from app.services.chromadb_evidence import ChromaDBEvidence
        chroma_evidence = ChromaDBEvidence(ChromaService())
        logger.info("chromadb_evidence_initialized", deck_id=deck_id)
    except Exception as e:
        logger.warning("ChromaDB unavailable, continuing without evidence store: %s", e)

    slides = outline.get("slides", [])
    total_slides = len(slides)
    all_packets = []
    contracts = []
    errors = []

    # Mark run as started in MongoDB
    if db is not None:
        await db.deck_runs.update_one(
            {"deck_id": deck_id},
            {
                "$set": {
                    "deck_id": deck_id,
                    "user_id": user_id,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "budget_mode": budget_mode,
                    "style": style,
                    "topic": topic,
                    "audience": audience,
                    "total_slides": total_slides,
                }
            },
            upsert=True,
        )

    try:
        # ── Stage 1: Intent classification ───────────────────
        await emitter.deck_context_ready(
            {"topic": topic, "slides": total_slides, "budget": budget_mode}
        )
        await emitter.intent_classified(
            {"audience": audience, "style": style, "deck_type": "pitch"}
        )

        # ── Stage 2: Research for each slide ─────────────────
        for idx, slide in enumerate(slides):
            slide_id = slide.get("id", f"slide_{idx}")
            slide_kind_str = slide.get("kind", slide.get("type", "problem"))
            try:
                slide_kind = SlideKind(slide_kind_str)
            except ValueError:
                slide_kind = SlideKind.PROBLEM

            # Plan queries
            queries = await planner.plan_queries(
                topic, slide.get("title", ""), slide_kind, audience
            )

            # Query ChromaDB for existing evidence (cross-deck reuse)
            reused_packets = []
            if chroma_evidence is not None:
                try:
                    reused_packets = await chroma_evidence.search_similar(
                        query=f"{topic} {slide.get('title', '')}",
                        slide_kind=slide_kind,
                        min_confidence=0.6,
                        n_results=5,
                        exclude_deck_id=deck_id,
                    )
                    if reused_packets:
                        logger.info(
                            "chromadb_evidence_reused",
                            slide_id=slide_id,
                            reused_count=len(reused_packets),
                        )
                except Exception as e:
                    logger.warning("ChromaDB search failed for %s: %s", slide_id, e)

            # Execute research
            packets = await router.research_slide(
                slide_id=slide_id,
                slide_kind=slide_kind,
                queries=queries,
                topic=topic,
                budget_mode=mode,
            )

            # Merge reused evidence (avoid duplicates by claim text similarity)
            existing_claims = {p.claim.lower().strip() for p in packets}
            for reused in reused_packets:
                if reused.claim.lower().strip() not in existing_claims:
                    packets.append(reused)
                    existing_claims.add(reused.claim.lower().strip())

            # Index all packets in ChromaDB for future reuse (best-effort)
            if chroma_evidence is not None and packets:
                try:
                    await chroma_evidence.index_batch(packets, deck_id)
                except Exception as e:
                    logger.warning("ChromaDB indexing failed for %s: %s", slide_id, e)

            # Build evidence graph incrementally
            for pkt in packets:
                graph.add_fact_packet(pkt)

            all_packets.extend(packets)

            # Update Celery task state for polling clients
            task.update_state(
                state="PROGRESS",
                meta={
                    "stage": "research",
                    "current_slide": idx + 1,
                    "total_slides": total_slides,
                    "packets_collected": len(all_packets),
                },
            )

        # ── Stage 3: Cross-validation ────────────────────────
        all_packets = cross_validator.validate(all_packets)

        # ── Stage 4: Freshness scoring ───────────────────────
        for pkt in all_packets:
            pkt.confidence = freshness_scorer.adjust_confidence(
                pkt, SlideKind.MARKET
            )

        # ── Stage 5: Community summaries ─────────────────────
        community = await summarizer.summarize(all_packets, topic)
        await emitter.emit(
            ContentEvent.COMMUNITY_SUMMARY_READY,
            None,
            {"themes": list(community.keys())},
            0.5,
            "evidence",
            "Community themes identified",
        )

        # ── Stage 6: Generate content per slide ──────────────
        for idx, slide in enumerate(slides):
            slide_id = slide.get("id", f"slide_{idx}")
            slide_kind_str = slide.get("kind", slide.get("type", "problem"))
            try:
                slide_kind = SlideKind(slide_kind_str)
            except ValueError:
                slide_kind = SlideKind.PROBLEM

            # Assemble evidence bundle for this slide
            bundle = assembler.assemble(slide_id, slide_kind, all_packets)

            # Run debate for pitch decks (skip title/team slides)
            is_pitch = audience.lower() in ("investors", "vcs", "angels")
            if is_pitch and slide_kind not in (SlideKind.TITLE, SlideKind.TEAM):
                try:
                    debate_outcome = await debate.run_debate(
                        bundle, topic, slide_kind
                    )
                    bundle.approved_claim_ids = debate_outcome.approved_claims
                    bundle.debate_approved = True
                except Exception as e:
                    logger.warning("Debate failed for %s: %s", slide_id, e)
                    bundle.approved_claim_ids = [
                        p.id for p in bundle.evidence_packets
                    ]
            else:
                bundle.approved_claim_ids = [
                    p.id for p in bundle.evidence_packets
                ]

            # Generate slide content
            try:
                deck_context = {
                    "community_summaries": community,
                    "graph_summary": graph.get_global_summary(),
                    "slide_index": idx,
                    "total_slides": total_slides,
                }
                contract = await generator.generate(
                    evidence_bundle=bundle,
                    style=style_profile,
                    topic=topic,
                    audience=audience,
                    budget_mode=mode,
                    deck_context=deck_context,
                )
                contracts.append(contract)
                await emitter.slide_content_ready(slide_id, contract)
            except Exception as e:
                logger.error("Generation failed for %s: %s", slide_id, e)
                errors.append({"slide_id": slide_id, "error": str(e)})
                await emitter.slide_content_blocked(
                    slide_id, "generation_failed", str(e)
                )

            # Update Celery task state
            task.update_state(
                state="PROGRESS",
                meta={
                    "stage": "generation",
                    "current_slide": idx + 1,
                    "total_slides": total_slides,
                    "contracts_generated": len(contracts),
                    "errors": len(errors),
                },
            )

        # ── Stage 7: Save to MongoDB ─────────────────────────
        total_time = (time.time() - start_time) * 1000
        result = {
            "deck_id": deck_id,
            "user_id": user_id,
            "status": "completed" if len(errors) == 0 else "partial",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "budget_mode": budget_mode,
            "style": style,
            "topic": topic,
            "audience": audience,
            "contracts": [c.to_dict() for c in contracts],
            "evidence_graph": graph.to_dict(),
            "community_summaries": community,
            "total_fact_packets": len(all_packets),
            "total_slides_generated": len(contracts),
            "total_slides_failed": len(errors),
            "total_time_ms": total_time,
            "errors": errors,
        }

        if db is not None:
            await db.deck_runs.update_one(
                {"deck_id": deck_id},
                {"$set": result},
                upsert=True,
            )

        await emitter.deck_content_complete(len(contracts), total_time)

        # Return serializable result (Celery JSON)
        return {
            "deck_id": deck_id,
            "status": result["status"],
            "total_slides_generated": len(contracts),
            "total_slides_failed": len(errors),
            "total_fact_packets": len(all_packets),
            "total_time_ms": total_time,
        }

    except Exception as e:
        logger.exception("Deck generation failed: %s", e)
        if db is not None:
            await db.deck_runs.update_one(
                {"deck_id": deck_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )
        raise
    finally:
        if redis_client:
            await redis_client.aclose()
        if mongo_client:
            mongo_client.close()


@celery_app.task(bind=True, max_retries=3, time_limit=120)
def research_slide_task(
    self,
    slide_id: str,
    slide_kind: str,
    queries: list,
    budget_mode: str = "lean",
    topic: str = "",
):
    """Research for a single slide (can be retried independently)."""
    loop = _get_event_loop()
    return loop.run_until_complete(
        _research_slide_async(slide_id, slide_kind, queries, budget_mode, topic)
    )


async def _research_slide_async(slide_id, slide_kind, queries, budget_mode, topic):
    """Async implementation of single slide research."""
    import redis.asyncio as aioredis
    from app.config import settings
    from app.mcp.brain_mcp.research.models import SlideKind, BudgetMode
    from app.mcp.brain_mcp.research.provider_registry import ProviderRegistry
    from app.mcp.brain_mcp.research.circuit_breaker import CircuitBreaker
    from app.mcp.brain_mcp.research.content_events import ContentEventEmitter
    from app.mcp.brain_mcp.research.research_router import ResearchRouter

    redis_client = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    except Exception as e:
        logger.warning("Redis unavailable for slide research: %s", e)

    try:
        registry = ProviderRegistry(settings)
        breaker = CircuitBreaker(redis_client)
        emitter = ContentEventEmitter(f"slide_{slide_id}", redis_client)
        router = ResearchRouter(registry, breaker, emitter)

        packets = await router.research_slide(
            slide_id=slide_id,
            slide_kind=SlideKind(slide_kind),
            queries=queries,
            topic=topic,
            budget_mode=BudgetMode(budget_mode),
        )
        return [p.to_dict() for p in packets]
    finally:
        if redis_client:
            await redis_client.aclose()
