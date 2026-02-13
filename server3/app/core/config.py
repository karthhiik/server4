import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Barise Chat Server"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ghf984983jabdcjsichdscdsjbc652tyg3ryvwdftrq4rf3wqevhda12ser")
    ALGORITHM: str = "HS256"
    
    # Database (MongoDB)
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = "barise_chat_db"
    COMMUNITY_DB_NAME: str = "barise_auth_db" # Based on server1 analysis
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "Stroingredisrealbarisedata.redis.cache.windows.net")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6380))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD", "Alu2Tad5h1vQ68FbIe20X9K9X9A2Dl4ZIAzCaFCZl8w=")
    REDIS_SSL: bool = str(os.getenv("REDIS_SSL", "True")).lower() == "true"
    
    # Azure Blob Storage
    BLOB_STORAGE_CONNECTION_STRING: str = os.getenv("BLOB_STORAGE_CONNECTION_STRING", "")
    BLOB_CONTAINER_NAME: str = os.getenv("BLOB_CONTAINER_NAME", "blobpitchdeckstorage")
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "*"]

    # API Base URLs
    API_BASE_URL3: str = os.getenv("API_BASE_URL3", "http://localhost:8001")

    # VAPID (Push Notifications)
    VAPID_PUBLIC_KEY: str = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY: str = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT: str = os.getenv("VAPID_SUBJECT", "mailto:admin@barise.local")

    class Config:
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()
