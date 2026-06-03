"""
Barise Server4 FastAPI application entrypoint.

Initializes the presentation backend with MongoDB, Redis, CORS, and routers.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from app.routers import generation_v4, websocket

# ============================================================================
# GLOBAL STATE
# ============================================================================

# MongoDB client (initialize in startup)
db: Any = None


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================


async def startup_event() -> None:
    """Initialize MongoDB and create indexes."""
    global db

    # Connect to MongoDB
    # In production: use environment variables
    mongo_url = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(mongo_url)
    db = client["barise_v4"]

    # Create indexes
    presentations = db["presentations"]
    await presentations.create_index("deck_id", unique=True)
    await presentations.create_index("user_id")
    await presentations.create_index("created_at")

    investors = db["investors"]
    await investors.create_index("sector_focus")
    await investors.create_index("stage_focus")

    live_metrics = db["live_metrics"]
    await live_metrics.create_index("deck_id")
    await live_metrics.create_index("source", unique=True)

    engagement_events = db["engagement_events"]
    await engagement_events.create_index("deck_id")
    await engagement_events.create_index("investor_id")
    await engagement_events.create_index("timestamp")

    print("✓ MongoDB initialized and indexes created")


async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    global db
    if db:
        # Connection will be closed automatically
        print("✓ MongoDB connection closed")


# ============================================================================
# LIFESPAN CONTEXT
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Barise Server4",
    description="AI-powered presentation generation backend",
    version="v4.1",
    lifespan=lifespan,
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai.barise.in",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_db() -> Any:
    """Get MongoDB database instance."""
    return db


# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(generation_v4.router)
app.include_router(websocket.router)

# ============================================================================
# HEALTH CHECK
# ============================================================================


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "v4.1",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# ROOT ENDPOINT
# ============================================================================


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "message": "Barise server4 v4.1",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Any, exc: Exception) -> Dict[str, Any]:
    """Global exception handler."""
    return {
        "error": str(exc),
        "status_code": 500,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# STARTUP MESSAGE
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║           BARISE SERVER4 - Presentation Backend                ║
    ║                       v4.1                                      ║
    ╚════════════════════════════════════════════════════════════════╝
    
    Features:
    ✓ Content-aware layout selection
    ✓ Design token safety (surface_alt luminance check)
    ✓ Investor intelligence matching
    ✓ Live metric injection
    ✓ WYSIWYG HTML/PDF/PPTX export
    ✓ WebSocket live collaboration
    
    Endpoints:
    • POST   /api/v4/decks
    • GET    /api/v4/decks/{deck_id}
    • PATCH  /api/v4/decks/{deck_id}/slides/{slide_no}
    • POST   /api/v4/decks/{deck_id}/match-investors
    • POST   /api/v4/decks/{deck_id}/export
    • WS     /ws/v4/progress/{deck_id}
    
    Docs: http://localhost:8000/docs
    """)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
