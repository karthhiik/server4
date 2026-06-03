"""
Integration guide and module exports for Barise Server4 v4.1.

This file documents the complete system architecture and provides
convenient imports for the entire v4 backend.
"""

# ============================================================================
# FILE MANIFEST
# ============================================================================

"""
All 9 production-ready files for Barise Server4:

1. app/models/v4.py
   - PaletteTokens, FontTokens, TypeScale, ResolvedDesignTokens
   - MetricBlock, TextBlock, QuoteBlock, ChartBlock, MediaBlock
   - FlowNode, SlideContent, CompiledSlide, Presentation
   - CreateDeckRequest, DeckResponse, SlidePatchRequest, ExportRequest
   - InvestorProfile, LiveMetric
   - Use: Import models for type hints and validation

2. app/services/v4/design_resolver.py
   - 5 visual directions with 16-color palettes
   - ensure_surface_alt() - WCAG luminance check + 8% lightening
   - resolve_design_tokens() - Priority-based resolution
   - Use: Call resolve_design_tokens() when creating decks

3. app/services/v4/layout_selector.py
   - select_layout() - 11-level priority system
   - blocks_to_nodes() - Convert blocks to flow nodes
   - validate_layout_compatibility() - Ensure content fits layout
   - Use: Called by slide_compiler during compilation

4. app/services/v4/slide_compiler.py
   - SlideCompiler class with compile_slide() and compile_deck()
   - Integrates layout selection + validation
   - Outputs layout_type (NEVER kit_jsx)
   - Use: Call compiler.compile_slide() to build production slides

5. app/services/v4/investor_intelligence.py
   - InvestorIntelligenceEngine with investor matching
   - match_investors() - Score by thesis/recency/warmth
   - generate_pitch_strategy() - Tailor to investor thesis
   - track_engagement() - Record investor interactions
   - Use: Call during deck creation for investor recommendations

6. app/services/v4/live_metrics.py
   - LiveMetricResolver for dynamic metric injection
   - resolve_metric() - Fetch from MongoDB or use fallback
   - inject_metrics_into_slide() - Replace {{ source }} templates
   - snapshot_deck() - For exports, get_live_deck() - for share links
   - Use: Call when rendering decks with live data

7. app/services/v4/export_adapter.py
   - ExportAdapter for HTML, PDF, PPTX export
   - to_html() - CSS variables + layout-specific rendering
   - to_pptx() - Python-pptx with design tokens
   - Layout-specific rendering (hero, metrics, process_flow, etc.)
   - Use: Call when exporting decks

8. app/routers/generation_v4.py
   - FastAPI router with 5 endpoints
   - POST /decks - Create deck with design token resolution
   - GET /decks/{deck_id} - Retrieve with optional live metrics
   - PATCH /decks/{deck_id}/slides/{slide_no} - Update + recompile
   - POST /decks/{deck_id}/match-investors - Investor matching
   - POST /decks/{deck_id}/export - Export to HTML/PDF/PPTX
   - Use: Include router in FastAPI app

9. app/routers/websocket.py
   - WebSocket endpoint for live progress
   - WS /ws/v4/progress/{deck_id} - Subscribe to events
   - Event emitters: pipeline_start, slide_drafted, deck_complete, etc.
   - Redis integration for multi-server scaling
   - ProgressEmitter class for background tasks
   - Use: Include router in FastAPI app

10. app/main.py
    - FastAPI app with lifespan management
    - CORS middleware (ai.barise.in, localhost:3000)
    - MongoDB connection + index creation
    - Include routers: generation_v4, websocket
    - Health check endpoint
    - Use: Run with: python -m app.main

"""

# ============================================================================
# CRITICAL RULES (ENFORCED IN CODE)
# ============================================================================

"""
1. NEVER output kit_jsx
   ✓ All CompiledSlide.layout_type are strings: hero, metrics, process_flow, etc.
   ✓ NO React component names coupled to backend
   
2. NEVER assign process_flow without keywords
   ✓ layout_selector checks for BOTH step_keywords AND flow_verbs
   ✓ Prevents "DiagramBlock" on vague content
   
3. GUARANTEE surface_alt lighter than surface
   ✓ ensure_surface_alt() uses WCAG relative luminance formula
   ✓ If surface_alt <= surface + 0.05 luminance: lighten by 8%
   ✓ No more invisible UI elements
   
4. ALL functions are async where I/O occurs
   ✓ Database queries: await db.find_one(), await db.insert_one()
   ✓ External APIs: await http_client.get()
   ✓ Only sync functions: pure logic, no I/O
   
5. Pydantic v2 syntax throughout
   ✓ field_validator for custom validation
   ✓ Field(default_factory=...) for complex defaults
   ✓ model_dump() for serialization
   ✓ NO v1 syntax (@root_validator, Config class)
   
6. Full type hints
   ✓ Function signatures: (param: Type) -> ReturnType
   ✓ Dict, List, Optional types from typing
   ✓ Literal types for constrained strings
   
7. PDF/PPTX/HTML match editor exactly
   ✓ ExportAdapter uses compiled slide data
   ✓ Same design tokens, same layout logic
   ✓ No "rendering engine" drift

"""

# ============================================================================
# ARCHITECTURE DIAGRAM
# ============================================================================

"""
REQUEST FLOW:

FastAPI Router (generation_v4.py)
    ↓
POST /decks ────→ resolve_design_tokens() ────→ Create Presentation in MongoDB
    ↓
GET /decks/{id} ←──── SlideContent from DB ← Optional: LiveMetricResolver
    ↓
PATCH /slides ──→ SlideCompiler.compile_slide()
                        ↓
                  select_layout() [11 rules]
                        ↓
                  validate_layout_compatibility()
                        ↓
                  CompiledSlide with layout_type
    ↓
POST /export ───→ ExportAdapter
                        ├→ to_html() [CSS variables + layout rendering]
                        ├→ to_pptx() [python-pptx with design tokens]
                        └→ to_pdf() [weasyprint of HTML]
    ↓
POST /match-investors ──→ InvestorIntelligenceEngine
                              ├→ match_investors() [score by thesis/recency/warmth]
                              └→ generate_pitch_strategy() [tailor to thesis]

WEBSOCKET FLOW:

WS /ws/v4/progress/{deck_id}
    ↓
ProgressEmitter from background task
    ├→ emit_pipeline_start()
    ├→ emit_company_preflight()
    ├→ emit_skeleton_ready()
    ├→ emit_slide_drafted() [for each slide]
    ├→ emit_critic_passed() [quality check]
    ├→ emit_images_complete()
    └→ emit_deck_complete()

Optional Redis pub/sub for multi-server:
    Backend Service → Redis Channel → WebSocket Subscribers
"""

# ============================================================================
# SETUP INSTRUCTIONS
# ============================================================================

"""
1. Install dependencies:
   pip install fastapi uvicorn motor pydantic pydantic-settings python-pptx weasyprint

2. Set environment variables:
   MONGODB_URL=mongodb://localhost:27017
   REDIS_URL=redis://localhost:6379
   BARISE_ENV=development

3. Create MongoDB:
   brew install mongodb-community  # or use Docker
   mongod

4. Run server:
   python -m app.main

5. Access:
   API docs: http://localhost:8000/docs
   Health: http://localhost:8000/health
   Root: http://localhost:8000/

6. Test POST /decks:
   curl -X POST http://localhost:8000/api/v4/decks \\
     -H "Content-Type: application/json" \\
     -d '{
       "title": "Q1 Fundraise",
       "user_id": "user_123",
       "brief": "AI platform for legal tech",
       "mode": "edit",
       "slide_count": 12,
       "visual_direction": "premium_brand_house"
     }'
"""

# ============================================================================
# FEATURE HIGHLIGHTS
# ============================================================================

"""
✓ Content-Aware Layout Selection
  - 11-level priority system prevents bad layout assignments
  - Never assigns process_flow to vague content
  - Converts blocks to nodes only when appropriate

✓ Design Token Safety
  - surface_alt luminance checked against surface
  - WCAG relative luminance calculation (scientific)
  - Automatic 8% lightening if needed
  - No more invisible UI elements

✓ Investor Intelligence (Unfair Advantage)
  - Match investors by stage, sector, check size
  - Score by thesis overlap, recency, warm intro paths
  - Generate tailored pitch strategies
  - Track engagement events

✓ Live Metrics
  - Template syntax: {{ stripe_mrr }}, {{ user_count }}, etc.
  - Injected at render time or export time
  - Fallback values for missing data
  - Metric history for trends

✓ WYSIWYG Export
  - HTML output with CSS variables
  - PPTX with python-pptx
  - PDF via weasyprint
  - All use compiled slide data (no drift)

✓ Real-Time Collaboration
  - WebSocket progress updates
  - Live slide updates
  - Investor engagement tracking (War Room)
  - Redis pub/sub for multi-server

✓ Production-Ready
  - All functions typed with type hints
  - Pydantic v2 validation
  - Async I/O throughout
  - MongoDB indexes for performance
  - CORS middleware configured
  - Error handling with global exception handler
"""

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
# Create a deck
POST /api/v4/decks
{
  "title": "Seed Fundraise",
  "user_id": "user_abc123",
  "brief": "AI-powered sales intelligence",
  "mode": "edit",
  "slide_count": 10,
  "visual_direction": "premium_brand_house"
}

# Response:
{
  "success": true,
  "deck_id": "deck_xyz789",
  "message": "Deck created successfully",
  "slides": []
}

# Get deck with live metrics injected
GET /api/v4/decks/deck_xyz789?live=true

# Update a slide (auto-recompilation)
PATCH /api/v4/decks/deck_xyz789/slides/1
{
  "content": {
    "headline": "Our Traction",
    "body_blocks": [
      {
        "type": "metric",
        "value": "{{ stripe_mrr }}",
        "label": "Monthly Recurring Revenue"
      },
      {
        "type": "metric",
        "value": "{{ user_count }}",
        "label": "Active Users",
        "delta": "+45%",
        "delta_direction": "up"
      }
    ]
  }
}

# Match investors
POST /api/v4/decks/deck_xyz789/match-investors
{
  "investors": [
    {
      "id": "inv_001",
      "name": "Sarah Chen",
      "firm": "Lightspeed Ventures",
      "stage_focus": ["seed", "series-a"],
      "sector_focus": ["ai", "saas"],
      "check_size_min": 500000,
      "check_size_max": 5000000,
      ...
    }
  ],
  "strategy": {
    "lead_slide": "problem",
    "emphasis": ["traction", "team", "market"],
    "risk_questions": [
      "How will you handle competition from established players?",
      "What's your unit economics?"
    ],
    "warm_intro_message": "I'd like to introduce you to our founding team..."
  }
}

# Export to PDF
POST /api/v4/decks/deck_xyz789/export
{
  "format": "pdf",
  "include_watermark": true
}

# Export to PPTX
POST /api/v4/decks/deck_xyz789/export
{
  "format": "pptx",
  "include_watermark": false
}

# Subscribe to progress
WS ws://localhost:8000/ws/v4/progress/deck_xyz789

# Receive events:
{
  "event": "pipeline_start",
  "data": {"deck_id": "deck_xyz789"}
}

{
  "event": "slide_drafted",
  "data": {
    "slide_id": "slide_1",
    "slide_no": 1,
    "layout_type": "hero",
    "intent": "cover",
    "content": {...}
  }
}

{
  "event": "deck_complete",
  "data": {"deck_id": "deck_xyz789", "total_slides": 10}
}
"""

# ============================================================================
# MODULE EXPORTS
# ============================================================================

# Models
from app.models.v4 import (
    BodyBlock,
    ChartBlock,
    CompiledSlide,
    CreateDeckRequest,
    DeckResponse,
    ExportRequest,
    FlowNode,
    FontTokens,
    InvestorProfile,
    LiveMetric,
    MediaBlock,
    MetricBlock,
    PaletteTokens,
    Presentation,
    QuoteBlock,
    ResolvedDesignTokens,
    SlidePatchRequest,
    SlideContent,
    TextBlock,
    TypeScale,
)

# Services
from app.services.v4.design_resolver import (
    ensure_surface_alt,
    resolve_design_tokens,
    VISUAL_DIRECTIONS,
)
from app.services.v4.export_adapter import ExportAdapter
from app.services.v4.investor_intelligence import InvestorIntelligenceEngine
from app.services.v4.layout_selector import (
    blocks_to_nodes,
    get_layout_info,
    select_layout,
    validate_layout_compatibility,
)
from app.services.v4.live_metrics import LiveMetricResolver
from app.services.v4.slide_compiler import SlideCompiler

# Routers
from app.routers.generation_v4 import router as generation_router
from app.routers.websocket import (
    ProgressEmitter,
    emit_company_preflight,
    emit_critic_passed,
    emit_critic_regenerated,
    emit_deck_complete,
    emit_images_complete,
    emit_investor_viewed,
    emit_pipeline_start,
    emit_research_complete,
    emit_skeleton_ready,
    emit_slide_drafted,
    emit_slide_updated,
    router as websocket_router,
)

__all__ = [
    # Models
    "BodyBlock",
    "ChartBlock",
    "CompiledSlide",
    "CreateDeckRequest",
    "DeckResponse",
    "ExportRequest",
    "FlowNode",
    "FontTokens",
    "InvestorProfile",
    "LiveMetric",
    "MediaBlock",
    "MetricBlock",
    "PaletteTokens",
    "Presentation",
    "QuoteBlock",
    "ResolvedDesignTokens",
    "SlidePatchRequest",
    "SlideContent",
    "TextBlock",
    "TypeScale",
    # Services
    "ensure_surface_alt",
    "resolve_design_tokens",
    "VISUAL_DIRECTIONS",
    "ExportAdapter",
    "InvestorIntelligenceEngine",
    "blocks_to_nodes",
    "get_layout_info",
    "select_layout",
    "validate_layout_compatibility",
    "LiveMetricResolver",
    "SlideCompiler",
    # Routers
    "generation_router",
    "websocket_router",
    "ProgressEmitter",
    "emit_company_preflight",
    "emit_critic_passed",
    "emit_critic_regenerated",
    "emit_deck_complete",
    "emit_images_complete",
    "emit_investor_viewed",
    "emit_pipeline_start",
    "emit_research_complete",
    "emit_skeleton_ready",
    "emit_slide_drafted",
    "emit_slide_updated",
]
