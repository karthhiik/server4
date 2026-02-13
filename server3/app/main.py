from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.db.mongo import db as mongo_db
from app.db.redis import redis_client
from app.routers import websocket, chat, upload_v2
from app.services.cleanup import start_scheduler
# from fastapi.staticfiles import StaticFiles  <-- Removed
from contextlib import asynccontextmanager
import os

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await mongo_db.connect()
    await redis_client.connect()
    start_scheduler()
    yield
    # Shutdown
    await mongo_db.close()
    await redis_client.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Uploads - REMOVED
# UPLOAD_DIR = "uploads"
# if not os.path.exists(UPLOAD_DIR):
#    os.makedirs(UPLOAD_DIR)
# app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routes
app.include_router(websocket.router, tags=["websocket"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(upload_v2.router, prefix="/api/chat/upload", tags=["upload"])
