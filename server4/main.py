"""
Server 4 â€” Presentation/Pitch Deck Backend
FastAPI service for AI-powered presentation generation, content creation, and export.

Architecture:
- 3 MCP servers (Brain, Design, Render) as stdio subprocesses
- Crash-proof state machine (persisted to MongoDB)
- 6-tier LLM routing (Kimi â†’ DeepSeek â†’ GPT-4o-mini â†’ Mistral â†’ Groq â†’ CF Workers)
- WebSocket progress streaming
- Azure Blob Storage for exports
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import connect_db, close_db
from app.middleware.cors import setup_cors
from app.routers import (
    presentations,
    generation,
    slides,
    templates,
    themes,
    export,
    websocket,
    admin,
    business_plans,
    swot_analysis,
    gtm_analysis,
    pitch_decks,
    intelligence_enrichment,
    slides_new,
)
from app.api.routes import content_generation as content_generation_v2
from app.api.routes import renderer_routes as renderer_v2
from app.api.routes import design_routes as design_v2
from app.api.routes import react_routes as react_v2
from app.api.routes import export_routes as export_v2
from app.api.routes import image_routes as image_v2
from app.api.routes import editor_routes as editor_v2
from app.api.routes import sync_routes as sync_v2
from app.api.routes import quality_routes as quality_v2
from app.api.routes import v3_generation as v3_generation
from app.routers.generation_v4 import router as generation_v4_router
# Side-effect import: registers /generation/{id}/answer and
# /projects/{id}/company-icon endpoints on the v4 router above.
from app.routers import generation_v4_interactive  # noqa: F401
from app.routers.v4_editor import router as v4_editor_router
from app.routers.ai_edit import router as ai_edit_router
from app.routers.v4_images import router as v4_images_router
from app.api.websockets import content_progress as content_progress_ws
from app.api.websockets import v3_progress as v3_progress_ws
from app.api.websockets import v4_progress as v4_progress_ws
from app.utils.rate_limiter import close_redis

import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # â”€â”€ Startup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    logger.info("server_starting", port=settings.API_PORT, env=settings.ENVIRONMENT)

    # Connect to MongoDB
    try:
        await connect_db()
        logger.info("mongodb_connected", db=settings.MONGODB_DB_NAME)
    except Exception as e:
        logger.error("mongodb_connection_failed", error=str(e))
        raise

    # Seed built-in themes and templates
    await _seed_builtin_data()

    logger.info("server_ready", service="presentation-service", port=settings.API_PORT)
    yield

    # â”€â”€ Shutdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    await close_db()
    await close_redis()
    logger.info("server_stopped")


app = FastAPI(
    title="Barise Presentation Service",
    description="AI-powered pitch deck and presentation generation API",
    version="0.2.0",
    lifespan=lifespan,
)

# Middleware
setup_cors(app)

# Routers
app.include_router(presentations.router)
app.include_router(generation.router)
app.include_router(slides.router)
app.include_router(templates.router)
app.include_router(themes.router)
app.include_router(export.router)
app.include_router(websocket.router)
app.include_router(admin.router)
app.include_router(business_plans.router)
app.include_router(swot_analysis.router)
app.include_router(gtm_analysis.router)
app.include_router(pitch_decks.router)
app.include_router(intelligence_enrichment.router)
app.include_router(slides_new.router)
app.include_router(content_generation_v2.router)
app.include_router(renderer_v2.router)
app.include_router(design_v2.router)
app.include_router(react_v2.router)
app.include_router(export_v2.router)
app.include_router(image_v2.router)
app.include_router(editor_v2.router)
app.include_router(sync_v2.router)
app.include_router(quality_v2.router)
app.include_router(content_progress_ws.router)
app.include_router(v3_generation.router)
app.include_router(generation_v4_router)
app.include_router(v4_editor_router)
app.include_router(v4_images_router)
app.include_router(v3_progress_ws.router)
app.include_router(v4_progress_ws.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "presentation-service", "version": "0.2.0"}


@app.get("/health/pipeline")
async def pipeline_health():
    """
    Deep health check â€” verifies Redis, MongoDB, and Celery connectivity.
    Returns per-component status for monitoring dashboards.
    """
    from app.database import get_db

    checks = {}

    # MongoDB
    try:
        db = get_db()
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {str(e)[:80]}"

    # Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:80]}"

    # Celery (inspect active queues)
    try:
        from app.tasks.celery_app import celery_app as cel

        inspector = cel.control.inspect(timeout=3)
        active = inspector.active_queues()
        checks["celery"] = "ok" if active else "no_workers"
    except Exception as e:
        checks["celery"] = f"error: {str(e)[:80]}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "components": checks, "version": "0.2.0"}


# â”€â”€ Seed data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def _seed_builtin_data():
    """Seed built-in themes and templates on first run."""
    from app.database import get_db

    db = get_db()

    # Seed themes if empty
    theme_count = await db.themes.count_documents({"type": "builtin"})
    if theme_count == 0:
        await _seed_themes(db)
        logger.info("seeded_builtin_themes")

    # Seed templates if empty
    template_count = await db.templates.count_documents({})
    if template_count == 0:
        await _seed_templates(db)
        logger.info("seeded_builtin_templates")


async def _seed_themes(db):
    themes = [
        {
            "_id": "corporate-blue",
            "name": "Corporate Blue",
            "type": "builtin",
            "colors": {
                "primary": "#2563EB",
                "secondary": "#1E40AF",
                "accent": "#3B82F6",
                "background": "#FFFFFF",
                "surface": "#F8FAFC",
                "text": "#0F172A",
                "text_secondary": "#475569",
                "muted": "#94A3B8",
                "chart_colors": [
                    "#2563EB",
                    "#7C3AED",
                    "#EC4899",
                    "#F97316",
                    "#10B981",
                    "#06B6D4",
                    "#EAB308",
                    "#EF4444",
                ],
            },
            "fonts": {"heading": "Inter", "body": "Roboto", "code": "JetBrains Mono"},
        },
        {
            "_id": "startup-gradient",
            "name": "Startup Gradient",
            "type": "builtin",
            "colors": {
                "primary": "#7C3AED",
                "secondary": "#5B21B6",
                "accent": "#EC4899",
                "background": "#FFFFFF",
                "surface": "#FAF5FF",
                "text": "#1E1B4B",
                "text_secondary": "#6B7280",
                "muted": "#A78BFA",
                "chart_colors": [
                    "#7C3AED",
                    "#EC4899",
                    "#F59E0B",
                    "#10B981",
                    "#3B82F6",
                    "#EF4444",
                    "#8B5CF6",
                    "#06B6D4",
                ],
            },
            "fonts": {
                "heading": "Poppins",
                "body": "Open Sans",
                "code": "JetBrains Mono",
            },
        },
        {
            "_id": "minimal-mono",
            "name": "Minimal Mono",
            "type": "builtin",
            "colors": {
                "primary": "#18181B",
                "secondary": "#3F3F46",
                "accent": "#71717A",
                "background": "#FFFFFF",
                "surface": "#FAFAFA",
                "text": "#18181B",
                "text_secondary": "#71717A",
                "muted": "#A1A1AA",
                "chart_colors": [
                    "#18181B",
                    "#3F3F46",
                    "#52525B",
                    "#71717A",
                    "#A1A1AA",
                    "#D4D4D8",
                    "#E4E4E7",
                    "#F4F4F5",
                ],
            },
            "fonts": {
                "heading": "IBM Plex Sans",
                "body": "IBM Plex Sans",
                "code": "IBM Plex Mono",
            },
        },
        {
            "_id": "bold-dark",
            "name": "Bold Dark",
            "type": "builtin",
            "colors": {
                "primary": "#F97316",
                "secondary": "#EA580C",
                "accent": "#EF4444",
                "background": "#0F172A",
                "surface": "#1E293B",
                "text": "#F8FAFC",
                "text_secondary": "#94A3B8",
                "muted": "#475569",
                "chart_colors": [
                    "#F97316",
                    "#EF4444",
                    "#EAB308",
                    "#10B981",
                    "#3B82F6",
                    "#EC4899",
                    "#8B5CF6",
                    "#06B6D4",
                ],
            },
            "fonts": {
                "heading": "Montserrat",
                "body": "DM Sans",
                "code": "JetBrains Mono",
            },
        },
        {
            "_id": "nature-earth",
            "name": "Nature Earth",
            "type": "builtin",
            "colors": {
                "primary": "#059669",
                "secondary": "#047857",
                "accent": "#84CC16",
                "background": "#FFFFFF",
                "surface": "#F0FDF4",
                "text": "#14532D",
                "text_secondary": "#4B5563",
                "muted": "#6EE7B7",
                "chart_colors": [
                    "#059669",
                    "#84CC16",
                    "#10B981",
                    "#14B8A6",
                    "#0D9488",
                    "#34D399",
                    "#A3E635",
                    "#22C55E",
                ],
            },
            "fonts": {
                "heading": "Merriweather",
                "body": "Lato",
                "code": "JetBrains Mono",
            },
        },
        {
            "_id": "tech-neon",
            "name": "Tech Neon",
            "type": "builtin",
            "colors": {
                "primary": "#06B6D4",
                "secondary": "#0891B2",
                "accent": "#8B5CF6",
                "background": "#0F172A",
                "surface": "#1E293B",
                "text": "#E0F2FE",
                "text_secondary": "#7DD3FC",
                "muted": "#475569",
                "chart_colors": [
                    "#06B6D4",
                    "#8B5CF6",
                    "#EC4899",
                    "#10B981",
                    "#F59E0B",
                    "#EF4444",
                    "#3B82F6",
                    "#14B8A6",
                ],
            },
            "fonts": {
                "heading": "Space Grotesk",
                "body": "Inter",
                "code": "JetBrains Mono",
            },
        },
        {
            "_id": "warm-sunset",
            "name": "Warm Sunset",
            "type": "builtin",
            "colors": {
                "primary": "#F59E0B",
                "secondary": "#D97706",
                "accent": "#EF4444",
                "background": "#FFFBEB",
                "surface": "#FEF3C7",
                "text": "#78350F",
                "text_secondary": "#92400E",
                "muted": "#FCD34D",
                "chart_colors": [
                    "#F59E0B",
                    "#EF4444",
                    "#F97316",
                    "#EC4899",
                    "#8B5CF6",
                    "#10B981",
                    "#06B6D4",
                    "#EAB308",
                ],
            },
            "fonts": {
                "heading": "Nunito",
                "body": "Source Sans Pro",
                "code": "JetBrains Mono",
            },
        },
        {
            "_id": "ocean-calm",
            "name": "Ocean Calm",
            "type": "builtin",
            "colors": {
                "primary": "#0369A1",
                "secondary": "#075985",
                "accent": "#0EA5E9",
                "background": "#FFFFFF",
                "surface": "#F0F9FF",
                "text": "#0C4A6E",
                "text_secondary": "#0369A1",
                "muted": "#7DD3FC",
                "chart_colors": [
                    "#0369A1",
                    "#0EA5E9",
                    "#06B6D4",
                    "#14B8A6",
                    "#3B82F6",
                    "#6366F1",
                    "#8B5CF6",
                    "#0891B2",
                ],
            },
            "fonts": {
                "heading": "Libre Baskerville",
                "body": "Raleway",
                "code": "JetBrains Mono",
            },
        },
    ]
    await db.themes.insert_many(themes)


async def _seed_templates(db):
    templates = [
        {
            "_id": "investor-pitch",
            "name": "Investor Pitch Deck",
            "category": "fundraising",
            "description": "10-slide Sequoia-format investor pitch. Problemâ†’Solutionâ†’Why Nowâ†’Marketâ†’Productâ†’Teamâ†’Financialsâ†’Ask.",
            "slide_count": 10,
            "mode_available": ["standard", "premium"],
            "default_theme": "corporate-blue",
            "default_writing_style": "yc_pitch",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Company introduction â€” one-liner value prop",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{one_liner_value_prop}}",
                    },
                    "ai_instructions": "Write a single sentence: [Company] helps [audience] do [outcome] by [mechanism]. No adjectives. No fluff.",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem â€” quantified pain",
                    "placeholders": {
                        "title": "The Problem",
                        "left_content": "{{problem_description}}",
                        "right_content": "{{quantified_impact}}",
                    },
                    "ai_instructions": "Left: describe the problem in 2-3 sentences with a specific person feeling the pain. Right: 2-3 statistics with sources (e.g., '$X billion lost annually â€” Source'). Every number needs a citation.",
                },
                {
                    "index": 2,
                    "layout": "bullets-with-image",
                    "purpose": "Solution â€” what you built",
                    "placeholders": {
                        "title": "Our Solution",
                        "bullets": "{{solution_points}}",
                    },
                    "ai_instructions": "3 bullets max. Each bullet: [Feature] â†’ [Outcome with number]. No 'cutting-edge' or 'revolutionary'. Show, don't tell.",
                },
                {
                    "index": 3,
                    "layout": "bullets",
                    "purpose": "Why Now â€” market timing",
                    "placeholders": {
                        "title": "Why Now",
                        "bullets": "{{timing_factors}}",
                    },
                    "ai_instructions": "3-4 bullets on what changed: regulation, technology shift, consumer behavior, cost breakthrough. Each bullet must reference a specific recent event or trend with a year/date.",
                },
                {
                    "index": 4,
                    "layout": "chart",
                    "purpose": "Market opportunity â€” TAM/SAM/SOM",
                    "placeholders": {
                        "title": "Market Opportunity",
                        "chart_data": "{{tam_sam_som}}",
                    },
                    "ai_instructions": "Create TAMâ†’SAMâ†’SOM funnel. TAM: top-down from industry reports (cite source). SAM: geographic/segment filter. SOM: realistic year-1 capture. Both top-down and bottom-up methodologies. Every number sourced.",
                },
                {
                    "index": 5,
                    "layout": "bullets",
                    "purpose": "Business model â€” unit economics",
                    "placeholders": {
                        "title": "Business Model",
                        "bullets": "{{revenue_model}}",
                    },
                    "ai_instructions": "Show: revenue model, pricing, ACV, gross margin, LTV/CAC ratio (target >3x), payback period. Use actual or projected numbers. Format as 'Metric: $X (explanation)'.",
                },
                {
                    "index": 6,
                    "layout": "chart",
                    "purpose": "Traction â€” growth chart",
                    "placeholders": {
                        "title": "Traction",
                        "chart_data": "{{traction_metrics}}",
                    },
                    "ai_instructions": "Chart MUST go up and to the right. Show MRR, users, or GMV over time. Include: current MoM/YoY growth rate annotation, cohort retention if available. If pre-revenue, show engagement metrics with growth rate.",
                },
                {
                    "index": 7,
                    "layout": "comparison",
                    "purpose": "Competitive landscape â€” positioning",
                    "placeholders": {
                        "title": "Competitive Landscape",
                        "left_label": "{{company_name}}",
                        "right_label": "Alternatives",
                    },
                    "ai_instructions": "Never say 'no competitors'. Show 2x2 matrix positioning or feature comparison. Frame as 'alternative approaches' vs your approach. Highlight your unfair advantage.",
                },
                {
                    "index": 8,
                    "layout": "team-grid",
                    "purpose": "Team â€” why you",
                    "placeholders": {
                        "title": "The Team",
                        "members": "{{team_members}}",
                    },
                    "ai_instructions": "Each member: Name, role, and ONE credential that proves domain expertise (e.g., 'Ex-Stripe, built payments infra for 10M users'). Include advisor names if notable.",
                },
                {
                    "index": 9,
                    "layout": "two-column",
                    "purpose": "The Ask â€” funding + use of funds",
                    "placeholders": {
                        "title": "The Ask",
                        "left_content": "{{funding_amount_and_terms}}",
                        "right_content": "{{use_of_funds_breakdown}}",
                    },
                    "ai_instructions": "Left: 'Raising $X [round type]' + key milestone this funding enables. Right: 3-4 line use-of-funds breakdown with percentages (e.g., '60% Engineering â€” ship v2'). Include 18-month runway assumption.",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "yc-demo-day",
            "name": "YC Demo Day",
            "category": "fundraising",
            "description": "8-slide YC Demo Day format. 2-minute pitch, maximum impact. The exact structure YC coaches founders to use.",
            "slide_count": 8,
            "mode_available": ["standard", "premium"],
            "default_theme": "minimal-mono",
            "default_writing_style": "yc_pitch",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "One-liner â€” what you do",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{one_liner}}",
                    },
                    "ai_instructions": "Format: '[Company] is [category] that [does what] for [whom].' Maximum 12 words. No adjectives. Think Airbnb: 'Book rooms with locals rather than hotels.'",
                },
                {
                    "index": 1,
                    "layout": "chart",
                    "purpose": "Traction â€” the graph",
                    "placeholders": {
                        "title": "{{primary_metric}}",
                        "chart_data": "{{traction_data}}",
                    },
                    "ai_instructions": "THE most important slide. Single metric, going up and to the right. Annotate growth rate (e.g., '25% MoM'). If pre-revenue, show user growth or engagement. Chart must fill the slide. No clutter.",
                },
                {
                    "index": 2,
                    "layout": "two-column",
                    "purpose": "Problem + market size",
                    "placeholders": {
                        "title": "{{market_size_headline}}",
                        "left_content": "{{problem_in_one_sentence}}",
                        "right_content": "{{market_size}}",
                    },
                    "ai_instructions": "Left: the problem in ONE sentence a 5th grader understands. Right: TAM number with source. Keep it to 2-3 data points max. This slide gets 10 seconds.",
                },
                {
                    "index": 3,
                    "layout": "bullets",
                    "purpose": "Solution â€” how it works",
                    "placeholders": {
                        "title": "How It Works",
                        "bullets": "{{solution_steps}}",
                    },
                    "ai_instructions": "3 steps maximum. Each step: verb + outcome. Example: 'Upload data â†’ Get insights in 30 seconds â†’ Export to Slack.' No technical jargon unless audience is technical.",
                },
                {
                    "index": 4,
                    "layout": "bullets",
                    "purpose": "Business model",
                    "placeholders": {
                        "title": "Business Model",
                        "bullets": "{{model_points}}",
                    },
                    "ai_instructions": "2-3 bullets. Must include: who pays, how much, how often. Example: 'SaaS â€” $99/mo per seat, 140% net revenue retention.' Include one proof point if possible.",
                },
                {
                    "index": 5,
                    "layout": "kpi-dashboard",
                    "purpose": "Key metrics",
                    "placeholders": {"title": "Metrics", "metrics": "{{key_numbers}}"},
                    "ai_instructions": "3-4 KPI cards maximum. Pick from: MRR, growth rate, customers, retention, NPS, CAC payback. Each metric needs the number AND the trend (e.g., 'MRR: $45K â†‘ 30% MoM').",
                },
                {
                    "index": 6,
                    "layout": "team-grid",
                    "purpose": "Team â€” credibility",
                    "placeholders": {"title": "Team", "members": "{{founders}}"},
                    "ai_instructions": "Founders only (2-3 people). Each: name + ONE line proving they should build this. Example: 'Jane Doe â€” 8 years at Stripe, built fraud detection.' No advisors on this slide.",
                },
                {
                    "index": 7,
                    "layout": "title-hero",
                    "purpose": "The ask â€” memorable close",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{memorable_close}}",
                    },
                    "ai_instructions": "Repeat the one-liner or a memorable reframe. Include company name large. Optional: the single most impressive metric below. This is what investors photograph.",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "sequoia-pitch",
            "name": "Sequoia Pitch Deck",
            "category": "fundraising",
            "description": "12-slide Sequoia Capital format. The gold standard for Series A/B fundraising decks.",
            "slide_count": 12,
            "mode_available": ["premium"],
            "default_theme": "corporate-blue",
            "default_writing_style": "analytical",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Company purpose",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{company_purpose}}",
                    },
                    "ai_instructions": "Define the company purpose in one sentence. Sequoia format: 'We [verb] [outcome] for [audience].' Think big but specific.",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem â€” status quo",
                    "placeholders": {
                        "title": "Problem",
                        "left_content": "{{problem_narrative}}",
                        "right_content": "{{quantified_pain}}",
                    },
                    "ai_instructions": "Left: describe the problem as a story â€” who suffers, how, and why current solutions fail. Right: 3 statistics proving the pain is real and large. Every number cited.",
                },
                {
                    "index": 2,
                    "layout": "bullets-with-image",
                    "purpose": "Solution â€” your answer",
                    "placeholders": {
                        "title": "Solution",
                        "bullets": "{{solution_description}}",
                    },
                    "ai_instructions": "Describe the solution in plain language. What is it? How does it work? What is the 'aha' moment? 3-4 bullets, each one a concrete capability, not a buzzword.",
                },
                {
                    "index": 3,
                    "layout": "bullets",
                    "purpose": "Why Now â€” timing",
                    "placeholders": {
                        "title": "Why Now",
                        "bullets": "{{timing_factors}}",
                    },
                    "ai_instructions": "What has changed to make this possible/necessary NOW? Technology shifts, regulatory changes, behavior changes, cost curves. 3-4 specific, dated factors.",
                },
                {
                    "index": 4,
                    "layout": "chart",
                    "purpose": "Market size â€” TAM/SAM/SOM",
                    "placeholders": {
                        "title": "Market Size",
                        "chart_data": "{{market_data}}",
                    },
                    "ai_instructions": "Sequoia wants both top-down AND bottom-up sizing. TAM from industry reports (cited). Bottom-up: [# customers] Ã— [ACV] = SAM. Show the wedge â€” where you start and how you expand.",
                },
                {
                    "index": 5,
                    "layout": "bullets-with-image",
                    "purpose": "Product â€” how it works",
                    "placeholders": {
                        "title": "Product",
                        "bullets": "{{product_walkthrough}}",
                    },
                    "ai_instructions": "Show the product. If possible, reference a screenshot/demo. 3-4 bullets: each describes a workflow step and its outcome. Emphasize 10x improvement over status quo.",
                },
                {
                    "index": 6,
                    "layout": "bullets",
                    "purpose": "Business model â€” revenue engine",
                    "placeholders": {
                        "title": "Business Model",
                        "bullets": "{{business_model}}",
                    },
                    "ai_instructions": "Revenue model, pricing strategy, unit economics. Include: ACV, gross margin, LTV, CAC, LTV/CAC ratio, payback period. Show path to profitability.",
                },
                {
                    "index": 7,
                    "layout": "chart",
                    "purpose": "Traction â€” proof points",
                    "placeholders": {
                        "title": "Traction",
                        "chart_data": "{{traction_chart}}",
                    },
                    "ai_instructions": "Revenue or key metric over time. Must show consistent growth. Annotate inflection points. Include: current ARR/MRR, growth rate, # customers, net retention. Add cohort data if strong.",
                },
                {
                    "index": 8,
                    "layout": "comparison",
                    "purpose": "Competition â€” market map",
                    "placeholders": {
                        "title": "Competition",
                        "left_label": "Our Approach",
                        "right_label": "Alternatives",
                    },
                    "ai_instructions": "2Ã—2 matrix or comparison table. Axes should represent dimensions where you win. Never say 'no competition'. Show category creation or repositioning. Name specific competitors.",
                },
                {
                    "index": 9,
                    "layout": "team-grid",
                    "purpose": "Team â€” founder-market fit",
                    "placeholders": {"title": "Team", "members": "{{team}}"},
                    "ai_instructions": "Each member: name, title, credential proving founder-market fit. Why is THIS team the one to build THIS company? Highlight domain expertise, prior exits, relevant experience.",
                },
                {
                    "index": 10,
                    "layout": "kpi-dashboard",
                    "purpose": "Financials â€” projections",
                    "placeholders": {
                        "title": "Financials",
                        "metrics": "{{financial_projections}}",
                    },
                    "ai_instructions": "3-year projections: revenue, gross margin, burn rate, headcount. Show path to break-even. Be realistic â€” Sequoia partners will stress-test every assumption.",
                },
                {
                    "index": 11,
                    "layout": "two-column",
                    "purpose": "The Ask â€” raise details",
                    "placeholders": {
                        "title": "The Ask",
                        "left_content": "{{raise_details}}",
                        "right_content": "{{use_of_funds}}",
                    },
                    "ai_instructions": "Left: raising $X, round type, key terms. Right: use-of-funds breakdown by category with percentages. Include: target milestones this round enables, months of runway, next raise trigger.",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "investor-update",
            "name": "Monthly Investor Update",
            "category": "fundraising",
            "description": "10-slide monthly/quarterly investor update. Transparent, metrics-first format that keeps investors engaged.",
            "slide_count": 10,
            "mode_available": ["standard", "premium"],
            "default_theme": "minimal-mono",
            "default_writing_style": "investor_update",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Cover â€” period identifier",
                    "placeholders": {
                        "title": "{{company_name}} â€” {{period}} Update",
                        "subtitle": "{{one_line_summary}}",
                    },
                    "ai_instructions": "Title: 'Company â€” Month Year Update'. Subtitle: one sentence summary of the period (e.g., 'Crossed $100K MRR, closed enterprise pilot').",
                },
                {
                    "index": 1,
                    "layout": "kpi-dashboard",
                    "purpose": "Highlights â€” traffic light",
                    "placeholders": {
                        "title": "Key Highlights",
                        "metrics": "{{highlights}}",
                    },
                    "ai_instructions": "3-4 KPI cards. For each: metric name, current value, MoM change, and status (green/yellow/red). Include MRR, burn rate, runway months, and one product metric.",
                },
                {
                    "index": 2,
                    "layout": "chart",
                    "purpose": "Revenue â€” MRR/ARR chart",
                    "placeholders": {
                        "title": "Revenue",
                        "chart_data": "{{revenue_chart}}",
                    },
                    "ai_instructions": "MRR or ARR line chart over last 6-12 months. Annotate: current MRR, MoM growth %, net revenue retention. Add target line if applicable.",
                },
                {
                    "index": 3,
                    "layout": "chart",
                    "purpose": "Growth â€” user/customer metrics",
                    "placeholders": {
                        "title": "Growth",
                        "chart_data": "{{growth_chart}}",
                    },
                    "ai_instructions": "Total customers or users over time. Show: new, churned, net adds. Include activation rate and engagement metric if relevant.",
                },
                {
                    "index": 4,
                    "layout": "bullets",
                    "purpose": "Wins â€” what went right",
                    "placeholders": {"title": "Wins", "bullets": "{{wins}}"},
                    "ai_instructions": "3-5 bullets. Each win: what happened + quantified impact. Example: 'Closed Acme Corp ($50K ACV) â€” largest deal to date.' Be specific, not generic.",
                },
                {
                    "index": 5,
                    "layout": "bullets",
                    "purpose": "Challenges â€” what's hard",
                    "placeholders": {
                        "title": "Challenges",
                        "bullets": "{{challenges}}",
                    },
                    "ai_instructions": "2-3 honest challenges. For each: what the issue is, what you're doing about it, and expected resolution. Investors respect transparency. Never hide bad news.",
                },
                {
                    "index": 6,
                    "layout": "chart",
                    "purpose": "Burn & Runway",
                    "placeholders": {
                        "title": "Burn & Runway",
                        "chart_data": "{{burn_data}}",
                    },
                    "ai_instructions": "Monthly burn rate over time + cash balance. Calculate and show: months of runway remaining, projected zero-cash date. If runway < 6 months, flag it.",
                },
                {
                    "index": 7,
                    "layout": "bullets",
                    "purpose": "Product â€” shipped & planned",
                    "placeholders": {
                        "title": "Product Update",
                        "bullets": "{{product_updates}}",
                    },
                    "ai_instructions": "Split into 'Shipped' and 'Next Month'. 2-3 items each. Focus on customer-facing changes and their impact, not technical details.",
                },
                {
                    "index": 8,
                    "layout": "bullets",
                    "purpose": "Team â€” hires & needs",
                    "placeholders": {"title": "Team", "bullets": "{{team_updates}}"},
                    "ai_instructions": "New hires (name, role), departures, open roles. Include current headcount. If fundraising: mention hiring plan post-raise.",
                },
                {
                    "index": 9,
                    "layout": "bullets",
                    "purpose": "Asks â€” how investors can help",
                    "placeholders": {
                        "title": "How You Can Help",
                        "bullets": "{{asks}}",
                    },
                    "ai_instructions": "2-3 SPECIFIC asks. Not 'intros to customers' but 'intro to VP Eng at [Company X] â€” they match our ICP.' Make it easy for investors to act.",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "series-a-deck",
            "name": "Series A Deck",
            "category": "fundraising",
            "description": "14-slide comprehensive Series A deck. Data-heavy, metrics-driven format for $2M-$20M raises.",
            "slide_count": 14,
            "mode_available": ["premium"],
            "default_theme": "corporate-blue",
            "default_writing_style": "analytical",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Cover â€” company identity",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{category_defining_statement}}",
                    },
                    "ai_instructions": "Company name large. Subtitle: define the category you're creating or leading. Example: 'The operating system for [industry].' One sentence, no fluff.",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem â€” market pain at scale",
                    "placeholders": {
                        "title": "The Problem",
                        "left_content": "{{problem_story}}",
                        "right_content": "{{market_data}}",
                    },
                    "ai_instructions": "Left: the problem told through one specific customer's pain. Right: market-level data proving this is systemic â€” 3 stats with citations. Connect the personal to the market-wide.",
                },
                {
                    "index": 2,
                    "layout": "bullets-with-image",
                    "purpose": "Solution â€” product overview",
                    "placeholders": {
                        "title": "The Solution",
                        "bullets": "{{solution_pillars}}",
                    },
                    "ai_instructions": "3-4 solution pillars. Each: '[Capability] â€” [measurable outcome]'. Show the product vision, not just current features. Reference a product screenshot if available.",
                },
                {
                    "index": 3,
                    "layout": "bullets",
                    "purpose": "Why Now â€” market timing catalysts",
                    "placeholders": {"title": "Why Now", "bullets": "{{catalysts}}"},
                    "ai_instructions": "4 catalysts making this the right time. Mix technology, market, regulatory, and behavioral shifts. Each must be specific and dated. Show convergence of factors.",
                },
                {
                    "index": 4,
                    "layout": "chart",
                    "purpose": "Market â€” TAM/SAM/SOM with methodology",
                    "placeholders": {
                        "title": "Market Opportunity",
                        "chart_data": "{{market_sizing}}",
                    },
                    "ai_instructions": "Show both top-down (industry reports, cited) and bottom-up ([# target customers] Ã— [ACV]). Include market growth rate. Show expansion wedges â€” how SAM grows as you add products/segments.",
                },
                {
                    "index": 5,
                    "layout": "bullets-with-image",
                    "purpose": "Product â€” deeper dive",
                    "placeholders": {
                        "title": "Product Deep Dive",
                        "bullets": "{{product_details}}",
                    },
                    "ai_instructions": "3-4 bullets showing product depth. Include: key workflow, integration points, data moat, and switching cost. Show why this is hard to replicate.",
                },
                {
                    "index": 6,
                    "layout": "chart",
                    "purpose": "Traction â€” revenue growth",
                    "placeholders": {
                        "title": "Revenue Traction",
                        "chart_data": "{{revenue_traction}}",
                    },
                    "ai_instructions": "MRR/ARR chart, minimum 12 months. Annotate: current ARR, MoM growth, YoY growth, # paying customers. Include logo bar of notable customers if applicable.",
                },
                {
                    "index": 7,
                    "layout": "kpi-dashboard",
                    "purpose": "Unit economics â€” SaaS metrics",
                    "placeholders": {
                        "title": "Unit Economics",
                        "metrics": "{{unit_economics}}",
                    },
                    "ai_instructions": "6 KPI cards: LTV, CAC, LTV/CAC ratio (target >3x), payback period (target <18mo), gross margin (target >70%), net revenue retention (target >120%). Color-code: green if meeting benchmark.",
                },
                {
                    "index": 8,
                    "layout": "chart",
                    "purpose": "Cohort analysis â€” retention proof",
                    "placeholders": {
                        "title": "Cohort Retention",
                        "chart_data": "{{cohort_data}}",
                    },
                    "ai_instructions": "Cohort retention chart showing monthly cohorts. Highlight: Month 3/6/12 retention rates. Show logo retention AND revenue retention separately if possible. Flat/upward curves are the goal.",
                },
                {
                    "index": 9,
                    "layout": "comparison",
                    "purpose": "Competitive positioning",
                    "placeholders": {
                        "title": "Competitive Landscape",
                        "left_label": "Our Approach",
                        "right_label": "Market Alternatives",
                    },
                    "ai_instructions": "2Ã—2 positioning matrix with labeled axes representing your key differentiators. Place 3-5 named competitors. Show clear whitespace where you sit. Include a 3-column feature comparison below if space allows.",
                },
                {
                    "index": 10,
                    "layout": "team-grid",
                    "purpose": "Team + advisors",
                    "placeholders": {
                        "title": "Team",
                        "members": "{{team_and_advisors}}",
                    },
                    "ai_instructions": "Founders + key hires (VP Eng, VP Sales). Each: name, role, one credential proving founder-market fit. Add 2-3 notable advisors/board members. Show the team is complete enough to execute.",
                },
                {
                    "index": 11,
                    "layout": "kpi-dashboard",
                    "purpose": "Financial projections â€” 3 year",
                    "placeholders": {
                        "title": "Financial Plan",
                        "metrics": "{{projections}}",
                    },
                    "ai_instructions": "3-year projection: ARR, gross margin, burn rate, headcount, revenue per employee. Show path to cash-flow positive. Be conservative â€” sophisticated investors will cut your numbers in half.",
                },
                {
                    "index": 12,
                    "layout": "two-column",
                    "purpose": "The Ask â€” round details",
                    "placeholders": {
                        "title": "The Raise",
                        "left_content": "{{round_details}}",
                        "right_content": "{{use_of_funds}}",
                    },
                    "ai_instructions": "Left: raising $X Series A, target close date, lead investor status, committed capital. Right: use-of-funds: engineering (%), sales (%), marketing (%), G&A (%). Include: target milestones and months of runway.",
                },
                {
                    "index": 13,
                    "layout": "title-hero",
                    "purpose": "Close â€” vision statement",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{vision_statement}}",
                    },
                    "ai_instructions": "End with the big vision â€” where is this company in 10 years? One bold sentence. Include contact info. This slide should make investors want to follow up immediately.",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "sales-deck",
            "name": "Sales Deck",
            "category": "sales",
            "description": "8-slide sales presentation for prospects and demos.",
            "slide_count": 8,
            "mode_available": ["standard", "premium"],
            "default_theme": "startup-gradient",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Opening",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{value_proposition}}",
                    },
                    "ai_instructions": "Create a compelling value proposition",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Challenge",
                    "placeholders": {
                        "title": "The Challenge",
                        "left_content": "{{pain_points}}",
                        "right_content": "{{impact}}",
                    },
                    "ai_instructions": "Describe customer pain points",
                },
                {
                    "index": 2,
                    "layout": "bullets-with-image",
                    "purpose": "Solution",
                    "placeholders": {"title": "How We Help", "bullets": "{{features}}"},
                    "ai_instructions": "List top features",
                },
                {
                    "index": 3,
                    "layout": "comparison",
                    "purpose": "Before/After",
                    "placeholders": {
                        "title": "The Difference",
                        "left_label": "Before",
                        "right_label": "After",
                    },
                    "ai_instructions": "Show before/after comparison",
                },
                {
                    "index": 4,
                    "layout": "kpi-dashboard",
                    "purpose": "Results",
                    "placeholders": {"title": "Results", "metrics": "{{results}}"},
                    "ai_instructions": "Show customer success metrics",
                },
                {
                    "index": 5,
                    "layout": "quote",
                    "purpose": "Testimonial",
                    "placeholders": {
                        "quote_text": "{{testimonial}}",
                        "quote_author": "{{customer_name}}",
                    },
                    "ai_instructions": "Format customer testimonial",
                },
                {
                    "index": 6,
                    "layout": "bullets",
                    "purpose": "Pricing",
                    "placeholders": {
                        "title": "Plans & Pricing",
                        "bullets": "{{pricing_tiers}}",
                    },
                    "ai_instructions": "Format pricing information",
                },
                {
                    "index": 7,
                    "layout": "title-hero",
                    "purpose": "CTA",
                    "placeholders": {
                        "title": "Get Started",
                        "subtitle": "{{cta_message}}",
                    },
                    "ai_instructions": "Create a strong call to action",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "quarterly-report",
            "name": "Quarterly Report",
            "category": "internal",
            "description": "12-slide quarterly business review template.",
            "slide_count": 12,
            "mode_available": ["standard", "premium"],
            "default_theme": "minimal-mono",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Cover",
                    "placeholders": {
                        "title": "{{quarter}} Quarterly Report",
                        "subtitle": "{{company_name}}",
                    },
                    "ai_instructions": "Format quarter and year",
                },
                {
                    "index": 1,
                    "layout": "bullets",
                    "purpose": "Agenda",
                    "placeholders": {"title": "Agenda", "bullets": "{{agenda_items}}"},
                    "ai_instructions": "Create agenda from report sections",
                },
                {
                    "index": 2,
                    "layout": "kpi-dashboard",
                    "purpose": "KPI Summary",
                    "placeholders": {"title": "Key Metrics", "metrics": "{{kpis}}"},
                    "ai_instructions": "Format top-line KPIs",
                },
                {
                    "index": 3,
                    "layout": "chart",
                    "purpose": "Revenue",
                    "placeholders": {
                        "title": "Revenue Performance",
                        "chart_data": "{{revenue_data}}",
                    },
                    "ai_instructions": "Create revenue chart data",
                },
                {
                    "index": 4,
                    "layout": "chart",
                    "purpose": "Growth",
                    "placeholders": {
                        "title": "Growth Metrics",
                        "chart_data": "{{growth_data}}",
                    },
                    "ai_instructions": "Create growth chart data",
                },
                {
                    "index": 5,
                    "layout": "two-column",
                    "purpose": "Wins",
                    "placeholders": {
                        "title": "Key Wins",
                        "left_content": "{{wins}}",
                        "right_content": "{{impact}}",
                    },
                    "ai_instructions": "Highlight major achievements",
                },
                {
                    "index": 6,
                    "layout": "bullets",
                    "purpose": "Challenges",
                    "placeholders": {
                        "title": "Challenges & Learnings",
                        "bullets": "{{challenges}}",
                    },
                    "ai_instructions": "Summarize challenges faced",
                },
                {
                    "index": 7,
                    "layout": "two-column",
                    "purpose": "Product",
                    "placeholders": {
                        "title": "Product Updates",
                        "left_content": "{{shipped}}",
                        "right_content": "{{upcoming}}",
                    },
                    "ai_instructions": "List product updates",
                },
                {
                    "index": 8,
                    "layout": "bullets",
                    "purpose": "Customers",
                    "placeholders": {
                        "title": "Customer Highlights",
                        "bullets": "{{customer_wins}}",
                    },
                    "ai_instructions": "Customer success stories",
                },
                {
                    "index": 9,
                    "layout": "kpi-dashboard",
                    "purpose": "Team",
                    "placeholders": {
                        "title": "Team & Hiring",
                        "metrics": "{{team_metrics}}",
                    },
                    "ai_instructions": "Team growth metrics",
                },
                {
                    "index": 10,
                    "layout": "timeline",
                    "purpose": "Next Quarter",
                    "placeholders": {
                        "title": "Q+1 Priorities",
                        "events": "{{priorities}}",
                    },
                    "ai_instructions": "Next quarter roadmap",
                },
                {
                    "index": 11,
                    "layout": "title-hero",
                    "purpose": "Close",
                    "placeholders": {"title": "Thank You", "subtitle": "Questions?"},
                    "ai_instructions": "Closing slide",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "product-launch",
            "name": "Product Launch",
            "category": "marketing",
            "description": "10-slide product launch announcement.",
            "slide_count": 10,
            "mode_available": ["standard", "premium"],
            "default_theme": "tech-neon",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Announce",
                    "placeholders": {
                        "title": "Introducing {{product_name}}",
                        "subtitle": "{{launch_tagline}}",
                    },
                    "ai_instructions": "Create an exciting launch tagline",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem",
                    "placeholders": {
                        "title": "The Gap",
                        "left_content": "{{current_problem}}",
                        "right_content": "{{user_impact}}",
                    },
                    "ai_instructions": "Describe the problem being solved",
                },
                {
                    "index": 2,
                    "layout": "bullets-with-image",
                    "purpose": "Product",
                    "placeholders": {
                        "title": "Meet {{product_name}}",
                        "bullets": "{{key_features}}",
                    },
                    "ai_instructions": "Top 4-5 features",
                },
                {
                    "index": 3,
                    "layout": "bullets",
                    "purpose": "Features",
                    "placeholders": {
                        "title": "Key Features",
                        "bullets": "{{detailed_features}}",
                    },
                    "ai_instructions": "Detailed feature breakdown",
                },
                {
                    "index": 4,
                    "layout": "comparison",
                    "purpose": "Before/After",
                    "placeholders": {
                        "title": "The Difference",
                        "left_label": "Without",
                        "right_label": "With",
                    },
                    "ai_instructions": "Before/after using the product",
                },
                {
                    "index": 5,
                    "layout": "kpi-dashboard",
                    "purpose": "Beta results",
                    "placeholders": {
                        "title": "Beta Results",
                        "metrics": "{{beta_metrics}}",
                    },
                    "ai_instructions": "Format beta/early results",
                },
                {
                    "index": 6,
                    "layout": "quote",
                    "purpose": "Testimonial",
                    "placeholders": {
                        "quote_text": "{{beta_quote}}",
                        "quote_author": "{{beta_user}}",
                    },
                    "ai_instructions": "Format beta user testimonial",
                },
                {
                    "index": 7,
                    "layout": "bullets",
                    "purpose": "Pricing",
                    "placeholders": {"title": "Pricing", "bullets": "{{pricing}}"},
                    "ai_instructions": "Format launch pricing",
                },
                {
                    "index": 8,
                    "layout": "timeline",
                    "purpose": "Roadmap",
                    "placeholders": {"title": "Roadmap", "events": "{{roadmap}}"},
                    "ai_instructions": "Create product roadmap",
                },
                {
                    "index": 9,
                    "layout": "title-hero",
                    "purpose": "CTA",
                    "placeholders": {
                        "title": "Get Early Access",
                        "subtitle": "{{cta}}",
                    },
                    "ai_instructions": "Strong launch CTA",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "startup-overview",
            "name": "Startup Overview",
            "category": "general",
            "description": "6-slide quick company overview for networking.",
            "slide_count": 6,
            "mode_available": ["standard", "premium"],
            "default_theme": "startup-gradient",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Intro",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{one_liner}}",
                    },
                    "ai_instructions": "Create a memorable one-liner",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem/Solution",
                    "placeholders": {
                        "title": "What We Do",
                        "left_content": "{{problem}}",
                        "right_content": "{{solution}}",
                    },
                    "ai_instructions": "Concise problem-solution fit",
                },
                {
                    "index": 2,
                    "layout": "chart",
                    "purpose": "Market",
                    "placeholders": {
                        "title": "Market Opportunity",
                        "chart_data": "{{market_data}}",
                    },
                    "ai_instructions": "Market size visualization",
                },
                {
                    "index": 3,
                    "layout": "kpi-dashboard",
                    "purpose": "Traction",
                    "placeholders": {"title": "Traction", "metrics": "{{metrics}}"},
                    "ai_instructions": "Key traction metrics",
                },
                {
                    "index": 4,
                    "layout": "team-grid",
                    "purpose": "Team",
                    "placeholders": {"title": "The Team", "members": "{{team}}"},
                    "ai_instructions": "Team highlights",
                },
                {
                    "index": 5,
                    "layout": "title-hero",
                    "purpose": "Contact",
                    "placeholders": {
                        "title": "Let's Connect",
                        "subtitle": "{{contact_info}}",
                    },
                    "ai_instructions": "Contact information",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "workshop-training",
            "name": "Workshop / Training",
            "category": "education",
            "description": "15-slide workshop or training presentation.",
            "slide_count": 15,
            "mode_available": ["standard", "premium"],
            "default_theme": "nature-earth",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Cover",
                    "placeholders": {
                        "title": "{{workshop_title}}",
                        "subtitle": "{{instructor_name}}",
                    },
                    "ai_instructions": "Format workshop title",
                },
                {
                    "index": 1,
                    "layout": "bullets",
                    "purpose": "Objectives",
                    "placeholders": {
                        "title": "Learning Objectives",
                        "bullets": "{{objectives}}",
                    },
                    "ai_instructions": "3-5 learning objectives",
                },
                {
                    "index": 2,
                    "layout": "bullets",
                    "purpose": "Agenda",
                    "placeholders": {"title": "Agenda", "bullets": "{{agenda}}"},
                    "ai_instructions": "Create agenda",
                },
                {
                    "index": 3,
                    "layout": "two-column",
                    "purpose": "Topic 1",
                    "placeholders": {
                        "title": "{{topic_1}}",
                        "left_content": "{{concept}}",
                        "right_content": "{{example}}",
                    },
                    "ai_instructions": "First topic with example",
                },
                {
                    "index": 4,
                    "layout": "bullets",
                    "purpose": "Exercise 1",
                    "placeholders": {
                        "title": "Exercise: {{exercise_1}}",
                        "bullets": "{{instructions}}",
                    },
                    "ai_instructions": "Create practice exercise",
                },
                {
                    "index": 5,
                    "layout": "two-column",
                    "purpose": "Topic 2",
                    "placeholders": {
                        "title": "{{topic_2}}",
                        "left_content": "{{concept}}",
                        "right_content": "{{example}}",
                    },
                    "ai_instructions": "Second topic with example",
                },
                {
                    "index": 6,
                    "layout": "bullets",
                    "purpose": "Exercise 2",
                    "placeholders": {
                        "title": "Exercise: {{exercise_2}}",
                        "bullets": "{{instructions}}",
                    },
                    "ai_instructions": "Create practice exercise",
                },
                {
                    "index": 7,
                    "layout": "two-column",
                    "purpose": "Topic 3",
                    "placeholders": {
                        "title": "{{topic_3}}",
                        "left_content": "{{concept}}",
                        "right_content": "{{example}}",
                    },
                    "ai_instructions": "Third topic",
                },
                {
                    "index": 8,
                    "layout": "bullets",
                    "purpose": "Exercise 3",
                    "placeholders": {
                        "title": "Exercise: {{exercise_3}}",
                        "bullets": "{{instructions}}",
                    },
                    "ai_instructions": "Create practice exercise",
                },
                {
                    "index": 9,
                    "layout": "two-column",
                    "purpose": "Topic 4",
                    "placeholders": {
                        "title": "{{topic_4}}",
                        "left_content": "{{concept}}",
                        "right_content": "{{example}}",
                    },
                    "ai_instructions": "Fourth topic",
                },
                {
                    "index": 10,
                    "layout": "bullets",
                    "purpose": "Discussion",
                    "placeholders": {
                        "title": "Group Discussion",
                        "bullets": "{{discussion_questions}}",
                    },
                    "ai_instructions": "3-4 discussion questions",
                },
                {
                    "index": 11,
                    "layout": "bullets",
                    "purpose": "Best Practices",
                    "placeholders": {
                        "title": "Best Practices",
                        "bullets": "{{best_practices}}",
                    },
                    "ai_instructions": "Key best practices",
                },
                {
                    "index": 12,
                    "layout": "bullets",
                    "purpose": "Summary",
                    "placeholders": {
                        "title": "Key Takeaways",
                        "bullets": "{{takeaways}}",
                    },
                    "ai_instructions": "Summarize key learnings",
                },
                {
                    "index": 13,
                    "layout": "bullets",
                    "purpose": "Resources",
                    "placeholders": {
                        "title": "Additional Resources",
                        "bullets": "{{resources}}",
                    },
                    "ai_instructions": "Suggest learning resources",
                },
                {
                    "index": 14,
                    "layout": "title-hero",
                    "purpose": "Close",
                    "placeholders": {
                        "title": "Thank You!",
                        "subtitle": "Questions & Feedback",
                    },
                    "ai_instructions": "Closing slide",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "company-profile",
            "name": "Company Profile",
            "category": "corporate",
            "description": "8-slide company profile for partners and clients.",
            "slide_count": 8,
            "mode_available": ["standard", "premium"],
            "default_theme": "ocean-calm",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Cover",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{tagline}}",
                    },
                    "ai_instructions": "Company tagline",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "About",
                    "placeholders": {
                        "title": "About Us",
                        "left_content": "{{mission}}",
                        "right_content": "{{vision}}",
                    },
                    "ai_instructions": "Mission and vision statements",
                },
                {
                    "index": 2,
                    "layout": "bullets",
                    "purpose": "Services",
                    "placeholders": {
                        "title": "Our Services",
                        "bullets": "{{services}}",
                    },
                    "ai_instructions": "List core services",
                },
                {
                    "index": 3,
                    "layout": "kpi-dashboard",
                    "purpose": "Numbers",
                    "placeholders": {
                        "title": "By the Numbers",
                        "metrics": "{{company_stats}}",
                    },
                    "ai_instructions": "Key company statistics",
                },
                {
                    "index": 4,
                    "layout": "team-grid",
                    "purpose": "Leadership",
                    "placeholders": {
                        "title": "Leadership Team",
                        "members": "{{leaders}}",
                    },
                    "ai_instructions": "Format leadership team",
                },
                {
                    "index": 5,
                    "layout": "bullets",
                    "purpose": "Clients",
                    "placeholders": {"title": "Our Clients", "bullets": "{{clients}}"},
                    "ai_instructions": "Notable clients or logos",
                },
                {
                    "index": 6,
                    "layout": "quote",
                    "purpose": "Testimonial",
                    "placeholders": {
                        "quote_text": "{{client_quote}}",
                        "quote_author": "{{client_name}}",
                    },
                    "ai_instructions": "Client testimonial",
                },
                {
                    "index": 7,
                    "layout": "title-hero",
                    "purpose": "Contact",
                    "placeholders": {
                        "title": "Contact Us",
                        "subtitle": "{{contact_info}}",
                    },
                    "ai_instructions": "Contact details",
                },
            ],
            "usage_count": 0,
        },
        {
            "_id": "project-proposal",
            "name": "Project Proposal",
            "category": "business",
            "description": "10-slide project proposal for clients.",
            "slide_count": 10,
            "mode_available": ["standard", "premium"],
            "default_theme": "corporate-blue",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Cover",
                    "placeholders": {
                        "title": "{{project_name}}",
                        "subtitle": "Proposal for {{client_name}}",
                    },
                    "ai_instructions": "Format project and client names",
                },
                {
                    "index": 1,
                    "layout": "bullets",
                    "purpose": "Executive Summary",
                    "placeholders": {
                        "title": "Executive Summary",
                        "bullets": "{{summary_points}}",
                    },
                    "ai_instructions": "3-4 key summary points",
                },
                {
                    "index": 2,
                    "layout": "two-column",
                    "purpose": "Background",
                    "placeholders": {
                        "title": "Background",
                        "left_content": "{{context}}",
                        "right_content": "{{challenges}}",
                    },
                    "ai_instructions": "Project context and challenges",
                },
                {
                    "index": 3,
                    "layout": "bullets",
                    "purpose": "Objectives",
                    "placeholders": {
                        "title": "Objectives",
                        "bullets": "{{objectives}}",
                    },
                    "ai_instructions": "Clear project objectives",
                },
                {
                    "index": 4,
                    "layout": "bullets",
                    "purpose": "Approach",
                    "placeholders": {
                        "title": "Our Approach",
                        "bullets": "{{methodology}}",
                    },
                    "ai_instructions": "Project methodology",
                },
                {
                    "index": 5,
                    "layout": "timeline",
                    "purpose": "Timeline",
                    "placeholders": {
                        "title": "Project Timeline",
                        "events": "{{milestones}}",
                    },
                    "ai_instructions": "Project milestones",
                },
                {
                    "index": 6,
                    "layout": "team-grid",
                    "purpose": "Team",
                    "placeholders": {"title": "Project Team", "members": "{{team}}"},
                    "ai_instructions": "Proposed team members",
                },
                {
                    "index": 7,
                    "layout": "kpi-dashboard",
                    "purpose": "Deliverables",
                    "placeholders": {
                        "title": "Deliverables",
                        "metrics": "{{deliverables}}",
                    },
                    "ai_instructions": "Key deliverables",
                },
                {
                    "index": 8,
                    "layout": "chart",
                    "purpose": "Budget",
                    "placeholders": {
                        "title": "Budget Breakdown",
                        "chart_data": "{{budget}}",
                    },
                    "ai_instructions": "Budget visualization",
                },
                {
                    "index": 9,
                    "layout": "title-hero",
                    "purpose": "Next Steps",
                    "placeholders": {
                        "title": "Next Steps",
                        "subtitle": "{{next_steps}}",
                    },
                    "ai_instructions": "Clear next steps",
                },
            ],
            "usage_count": 0,
        },
    ]
    await db.templates.insert_many(templates)

