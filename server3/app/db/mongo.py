from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings

settings = get_settings()

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None
    community_db = None
    
    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client[settings.DATABASE_NAME]
        self.community_db = self.client[settings.COMMUNITY_DB_NAME]
        print(f"Connected to MongoDB: {settings.DATABASE_NAME} & {settings.COMMUNITY_DB_NAME}")

    async def close(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed")

db = MongoDB()

async def get_database():
    return db.db

async def get_community_db():
    return db.community_db
