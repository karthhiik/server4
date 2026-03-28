from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.mongo import get_community_db
from app.db.redis import get_redis

settings = get_settings()


class PresenceService:
    def __init__(self) -> None:
        self.instance_id = settings.CHAT_SERVER_INSTANCE_ID
        self.ttl_seconds = max(30, settings.CHAT_PRESENCE_TTL_SECONDS)
        self.set_ttl_seconds = max(
            self.ttl_seconds, settings.CHAT_PRESENCE_SET_TTL_SECONDS
        )

    def _instance_presence_key(self, user_id: str) -> str:
        return f"barise:chat:presence:{user_id}:instance:{self.instance_id}"

    def _instance_members_key(self, user_id: str) -> str:
        return f"barise:chat:presence:{user_id}:instances"

    def _last_seen_key(self, user_id: str) -> str:
        return f"barise:chat:last_seen:{user_id}"

    async def _set_presence_mirror(self, user_id: str, *, is_online: bool) -> None:
        community_db = await get_community_db()
        if community_db is None:
            return

        update = {"is_online": is_online}
        if not is_online:
            update["last_seen"] = datetime.now(timezone.utc)
        await community_db.users.update_one(
            {"user_id": user_id},
            {"$set": update},
        )

    async def mark_online(self, user_id: str) -> None:
        redis = await get_redis()
        if redis is not None:
            presence_key = self._instance_presence_key(user_id)
            members_key = self._instance_members_key(user_id)
            now_iso = datetime.now(timezone.utc).isoformat()
            pipe = redis.pipeline()
            pipe.set(presence_key, now_iso, ex=self.ttl_seconds)
            pipe.sadd(members_key, self.instance_id)
            pipe.expire(members_key, self.set_ttl_seconds)
            pipe.delete(self._last_seen_key(user_id))
            await pipe.execute()

        await self._set_presence_mirror(user_id, is_online=True)

    async def refresh_online(self, user_id: str) -> None:
        redis = await get_redis()
        if redis is None:
            return
        presence_key = self._instance_presence_key(user_id)
        members_key = self._instance_members_key(user_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        pipe = redis.pipeline()
        pipe.set(presence_key, now_iso, ex=self.ttl_seconds)
        pipe.sadd(members_key, self.instance_id)
        pipe.expire(members_key, self.set_ttl_seconds)
        await pipe.execute()

    async def mark_offline(self, user_id: str) -> None:
        redis = await get_redis()
        last_seen = datetime.now(timezone.utc)

        if redis is not None:
            presence_key = self._instance_presence_key(user_id)
            members_key = self._instance_members_key(user_id)
            pipe = redis.pipeline()
            pipe.delete(presence_key)
            pipe.srem(members_key, self.instance_id)
            pipe.set(self._last_seen_key(user_id), last_seen.isoformat(), ex=7 * 24 * 3600)
            await pipe.execute()

            other_instances = await self._active_instances(user_id)
            if other_instances:
                return

        await self._set_presence_mirror(user_id, is_online=False)

    async def _active_instances(self, user_id: str) -> list[str]:
        redis = await get_redis()
        if redis is None:
            return []

        members_key = self._instance_members_key(user_id)
        members = await redis.smembers(members_key)
        if not members:
            return []

        active_instances: list[str] = []
        stale_instances: list[str] = []
        for instance_id in members:
            key = f"barise:chat:presence:{user_id}:instance:{instance_id}"
            if await redis.exists(key):
                active_instances.append(instance_id)
            else:
                stale_instances.append(instance_id)

        if stale_instances:
            await redis.srem(members_key, *stale_instances)

        if active_instances:
            await redis.expire(members_key, self.set_ttl_seconds)

        return active_instances

    async def get_presence(self, user_id: str) -> dict[str, str | None]:
        active_instances = await self._active_instances(user_id)
        if active_instances:
            return {"status": "online", "last_seen": None}

        redis = await get_redis()
        last_seen = None
        if redis is not None:
            last_seen = await redis.get(self._last_seen_key(user_id))

        if not last_seen:
            community_db = await get_community_db()
            if community_db is not None:
                user = await community_db.users.find_one(
                    {"user_id": user_id},
                    {"last_seen": 1, "is_online": 1},
                )
                if user and user.get("is_online"):
                    return {"status": "online", "last_seen": None}
                if user and user.get("last_seen"):
                    raw_last_seen = user["last_seen"]
                    if hasattr(raw_last_seen, "isoformat"):
                        last_seen = raw_last_seen.isoformat()
                    else:
                        last_seen = str(raw_last_seen)

        return {"status": "offline", "last_seen": last_seen}

    async def is_online(self, user_id: str) -> bool:
        presence = await self.get_presence(user_id)
        return presence["status"] == "online"


presence_service = PresenceService()
