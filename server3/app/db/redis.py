import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()

class RedisClient:
    client: redis.Redis = None

    def _build_connection_kwargs(self, *, socket_timeout=5):
        redis_port = settings.REDIS_PORT
        if settings.REDIS_SSL and redis_port == 6379:
            redis_port = 6380

        connection_kwargs = {
            "host": settings.REDIS_HOST,
            "port": redis_port,
            "db": settings.REDIS_DB,
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": socket_timeout,
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "health_check_interval": 30,
        }

        if settings.REDIS_PASSWORD and settings.REDIS_PASSWORD.strip():
            connection_kwargs["password"] = settings.REDIS_PASSWORD

        if settings.REDIS_SSL:
            connection_kwargs["ssl"] = True
            connection_kwargs["ssl_cert_reqs"] = "none"
        else:
            connection_kwargs["ssl"] = False

        return connection_kwargs

    async def connect(self):
        self.client = redis.Redis(**self._build_connection_kwargs(socket_timeout=5))
        try:
            await self.client.ping()
            # print(f"Connected to Redis at {settings.REDIS_HOST}:{redis_port}")
        except Exception as e:
            await self.client.close()
            self.client = None
            # print(f"Redis connection failed: {e}")

    async def create_pubsub_client(self):
        client = redis.Redis(
            **self._build_connection_kwargs(socket_timeout=30),
            health_check_interval=15,
        )
        await client.ping()
        return client

    async def close(self):
        if self.client:
            await self.client.close()
            # print("Redis connection closed")

redis_client = RedisClient()

async def get_redis():
    return redis_client.client
