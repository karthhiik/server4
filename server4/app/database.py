"""
MongoDB async connection using Motor driver.
Cosmos DB compatible via MongoDB API.

V7 additions:
- slide_skills collection (Code Agent skill versions)
- context_boards collection (agent communication state)
- generation_sessions collection (per-session tracking)
- ChromaDB client initialisation helper
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None

# ChromaDB singleton
_chroma_service = None


async def connect_db() -> None:
    global _client, _db
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    _db = _client[settings.MONGODB_DB_NAME]
    await _client.admin.command("ping")
    await _create_indexes()


async def close_db() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _db


def is_db_initialized() -> bool:
    return _db is not None


def get_chroma_service():
    """Return a lazily-initialised ChromaService singleton."""
    global _chroma_service
    if _chroma_service is None:
        from app.services.chromadb_service import ChromaService
        _chroma_service = ChromaService()
        logger.info("chromadb_service_initialized")
    return _chroma_service


async def _create_indexes() -> None:
    db = get_db()

    # presentations collection
    # ── v3-final Phase 1 (Day 1) schema additions ─────────────────
    # New deck-level sub-document fields on `presentations`:
    #   design_system : { tokens, css_artifact_url, version, … } | null
    #                    populated by Phase 2 (Day 2) generator.
    #   brand_kit     : { source_url, extracted_tokens, … } | null
    #                    populated by Phase 2.2 (post-MVP / v1.1).
    # New per-slide sub-document fields on `compiled_slides[]`:
    #   artifacts            : { kit_jsx, html_css_js, engine, reveal_legacy }
    #   artifact_version     : int
    #   design_system_version: str | null
    #   quality_score        : { … } | null   (Phase 4.5, Day 8)
    #   enrichment           : { … } | null   (Phase 7.5, Day 15)
    # No new indexes — none of these fields are queried in WHERE/SORT.
    # No backfill — `dict.get("design_system")` returns None for legacy
    # docs, which is functionally identical to None-stored.
    await db.presentations.create_index("user_id")
    await db.presentations.create_index("created_at")
    await db.presentations.create_index([("user_id", 1), ("created_at", -1)])

    # slides collection — one document per slide
    await db.slides.create_index("presentation_id")
    await db.slides.create_index([("presentation_id", 1), ("index", 1)], unique=True)

    # slide_versions — for undo/redo
    await db.slide_versions.create_index("slide_id")
    await db.slide_versions.create_index([("slide_id", 1), ("version", -1)])

    # templates
    await db.templates.create_index("category")
    await db.templates.create_index("name")

    # themes
    await db.themes.create_index("type")

    # generation_logs — for observability
    await db.generation_logs.create_index("presentation_id")
    await db.generation_logs.create_index([("created_at", -1)])
    await db.generation_logs.create_index("provider")

    # template_analytics
    await db.template_analytics.create_index("template_id", unique=True)

    # ── V7 collections ────────────────────────────────────────

    # slide_skills — Code Agent versioned skill storage (Phase 3)
    await db.slide_skills.create_index("name", unique=True)
    await db.slide_skills.create_index([("name", 1), ("version", -1)])
    await db.slide_skills.create_index("avg_quality")

    # context_boards — agent communication state per session
    await db.context_boards.create_index("session_id", unique=True)
    await db.context_boards.create_index("updated_at")

    # generation_sessions — per-session orchestrator tracking
    await db.generation_sessions.create_index("presentation_id")
    await db.generation_sessions.create_index("status")
    await db.generation_sessions.create_index([("created_at", -1)])
    await db.generation_sessions.create_index([("presentation_id", 1), ("created_at", -1)])

    # ── V7 content pipeline collections ───────────────────────

    # deck_runs — full pipeline run results
    await db.deck_runs.create_index("deck_id", unique=True)
    await db.deck_runs.create_index("user_id")
    await db.deck_runs.create_index("status")
    await db.deck_runs.create_index([("user_id", 1), ("created_at", -1)])

    # deck_evidence — per-packet evidence storage
    await db.deck_evidence.create_index("deck_id")
    await db.deck_evidence.create_index([("deck_id", 1), ("provider", 1)])

    # ── Phase 4 — Renderer & Theme collections ────────────────

    # reveal_builds — cached compiled reveal.js output
    await db.reveal_builds.create_index("deck_id")
    await db.reveal_builds.create_index("theme_id")
    await db.reveal_builds.create_index([("deck_id", 1), ("theme_id", 1)], unique=True)
    await db.reveal_builds.create_index([("created_at", -1)])

    # generated_themes — user-generated themes from brand colors
    await db.generated_themes.create_index("user_id")
    await db.generated_themes.create_index("base_theme")
    await db.generated_themes.create_index([("user_id", 1), ("created_at", -1)])

    # css_cache — compiled CSS keyed by theme hash
    await db.css_cache.create_index("cache_key", unique=True)
    await db.css_cache.create_index([("created_at", -1)])

    # ── Phase 5 — Design Intelligence collections ─────────────

    # brand_dna — extracted brand identity per user/upload
    await db.brand_dna.create_index("user_id")
    await db.brand_dna.create_index("source_file")
    await db.brand_dna.create_index([("user_id", 1), ("created_at", -1)])

    # style_sessions — user style discovery sessions
    await db.style_sessions.create_index("user_id")
    await db.style_sessions.create_index("deck_id")
    await db.style_sessions.create_index([("user_id", 1), ("created_at", -1)])

    # design_intelligence_cache — cached pipeline results
    await db.design_intelligence_cache.create_index("deck_id", unique=True)
    await db.design_intelligence_cache.create_index([("created_at", -1)])

    # ── Phase 6 — React + Three.js Renderer collections ─────\n\n    # react_builds — compiled React + Three.js bundle cache\n    await db.react_builds.create_index("deck_id")\n    await db.react_builds.create_index("theme_id")\n    await db.react_builds.create_index([('deck_id', 1), ('theme_id', 1)], unique=True)\n    await db.react_builds.create_index([('created_at', -1)])\n\n    # vfx_sessions — VFX Agent scene assignment history\n    await db.vfx_sessions.create_index("deck_id")\n    await db.vfx_sessions.create_index("session_id")\n    await db.vfx_sessions.create_index([('deck_id', 1), ('created_at', -1)])\n\n    # ── Phase 7 — PPTX & HTML Renderer collections ────────

    # pptx_builds — compiled PPTX file cache
    await db.pptx_builds.create_index("deck_id")
    await db.pptx_builds.create_index("theme_id")
    await db.pptx_builds.create_index([("deck_id", 1), ("theme_id", 1)], unique=True)
    await db.pptx_builds.create_index([("created_at", -1)])

    # html_builds — compiled HTML presentation cache
    await db.html_builds.create_index("deck_id")
    await db.html_builds.create_index("theme_id")
    await db.html_builds.create_index([("deck_id", 1), ("theme_id", 1)], unique=True)
    await db.html_builds.create_index([("created_at", -1)])

    # export_jobs — multi-format export job tracking
    await db.export_jobs.create_index("job_id", unique=True)
    await db.export_jobs.create_index("user_id")
    await db.export_jobs.create_index("status")
    await db.export_jobs.create_index([("user_id", 1), ("created_at", -1)])

    logger.info("database_indexes_created", v7=True, phase4=True, phase5=True, phase6=True, phase7=True)
