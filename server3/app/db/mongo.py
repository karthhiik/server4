from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None
    community_db = None
    
    async def connect(self):
        self.client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=15000,
            socketTimeoutMS=30000,
            maxIdleTimeMS=120000,
            retryWrites=False,
            retryReads=True,
            appname="barise-chat-server",
        )
        self.db = self.client[settings.DATABASE_NAME]
        self.community_db = self.client[settings.COMMUNITY_DB_NAME]
        await self._ensure_indexes()
        # print(f"Connected to MongoDB: {settings.DATABASE_NAME} & {settings.COMMUNITY_DB_NAME}")

    async def close(self):
        if self.client:
            self.client.close()
            # print("MongoDB connection closed")

    async def _safe_create_index(self, collection, keys, **kwargs):
        try:
            await collection.create_index(keys, **kwargs)
        except Exception as exc:
            logger.warning(
                "Skipping index creation for %s on %s: %s",
                keys,
                getattr(collection, "name", "unknown"),
                exc,
            )

    async def _ensure_indexes(self):
        if self.db is None:
            return

        await self._safe_create_index(
            self.db.conversations,
            "participants_key",
            unique=True,
            sparse=True,
        )
        await self._safe_create_index(
            self.db.conversations,
            [("participants", 1), ("updated_at", -1)],
        )
        await self._safe_create_index(
            self.db.conversations,
            [("hidden_for", 1), ("updated_at", -1)],
        )
        await self._safe_create_index(
            self.db.messages,
            [("conversation_id", 1), ("timestamp", -1)],
        )
        await self._safe_create_index(
            self.db.messages,
            [("conversation_id", 1), ("status", 1), ("timestamp", -1)],
        )
        await self._safe_create_index(
            self.db.messages,
            [("sender_id", 1), ("timestamp", -1)],
        )
        await self._safe_create_index(
            self.db.blocks,
            [("blocker_id", 1), ("blocked_id", 1)],
            unique=True,
        )
        await self._safe_create_index(
            self.db.chat_email_rollups,
            [("recipient_id", 1), ("conversation_id", 1)],
            unique=True,
        )
        await self._safe_create_index(
            self.db.chat_email_rollups,
            [("recipient_id", 1), ("last_message_at", -1)],
        )
        await self._safe_create_index(
            self.db.chat_email_rollups,
            "updated_at",
        )

db = MongoDB()

async def get_database():
    return db.db

async def get_community_db():
    return db.community_db
