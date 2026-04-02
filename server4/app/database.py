"""
MongoDB async connection using Motor driver.
Cosmos DB compatible via MongoDB API.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from contextlib import asynccontextmanager

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


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


async def _create_indexes() -> None:
    db = get_db()

    # presentations collection
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
