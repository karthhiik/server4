import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()

class RedisClient:
    client: redis.Redis = None

    async def connect(self):
        connection_kwargs = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "password": settings.REDIS_PASSWORD,
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        }
        
        if settings.REDIS_SSL:
            connection_kwargs["ssl"] = True
            connection_kwargs["ssl_cert_reqs"] = None

        self.client = redis.Redis(**connection_kwargs)
        try:
            await self.client.ping()
            print(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            print(f"Redis connection failed: {e}")

    async def close(self):
        if self.client:
            await self.client.close()
            print("Redis connection closed")

redis_client = RedisClient()

async def get_redis():
    return redis_client.client
