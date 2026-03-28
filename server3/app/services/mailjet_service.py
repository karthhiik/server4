from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MAILJET_DAILY_COUNT_KEY = "server3:mailjet:daily_email_count"


async def get_redis_client() -> aioredis.Redis:
    if settings.REDIS_SSL:
        url = f"rediss://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    else:
        url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    return aioredis.from_url(url, decode_responses=True)


async def check_daily_quota() -> tuple[bool, int]:
    if not settings.MAILJET_RATE_LIMIT_ENABLED:
        return True, 0

    try:
        redis_client = await get_redis_client()
        count_str = await redis_client.get(MAILJET_DAILY_COUNT_KEY)
        await redis_client.aclose()
        current_count = int(count_str) if count_str else 0
        return current_count < settings.MAILJET_DAILY_QUOTA, current_count
    except Exception as exc:
        logger.warning("[EMAIL][MAILJET] Redis quota check failed: %s", exc)
        return True, 0


async def increment_email_count() -> int:
    try:
        redis_client = await get_redis_client()
        new_count = await redis_client.incr(MAILJET_DAILY_COUNT_KEY)
        ttl = await redis_client.ttl(MAILJET_DAILY_COUNT_KEY)
        if ttl == -1:
            now = datetime.now(timezone.utc)
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            await redis_client.expire(
                MAILJET_DAILY_COUNT_KEY,
                int((midnight - now).total_seconds()),
            )
        await redis_client.aclose()
        return new_count
    except Exception as exc:
        logger.warning("[EMAIL][MAILJET] Redis increment failed: %s", exc)
        return 0


async def send_transactional_email(
    *,
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> dict:
    if not settings.MAILJET_API_KEY or not settings.MAILJET_SECRET_KEY:
        return {"status": "error", "message": "Mailjet not configured"}

    within_quota, current_count = await check_daily_quota()
    if not within_quota:
        return {"status": "quota_exceeded", "count": current_count}

    sender_email = settings.MAILJET_SENDER_MAIL or settings.MAIL_SENDER_EMAIL
    sender_name = settings.MAILJET_SENDER_NAME or settings.MAIL_SENDER_NAME

    payload = {
        "Messages": [
            {
                "From": {"Email": sender_email, "Name": sender_name},
                "To": [{"Email": to_email, "Name": to_name}],
                "Subject": subject,
                "HTMLPart": html_content,
            }
        ]
    }
    if text_content:
        payload["Messages"][0]["TextPart"] = text_content

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.mailjet.com/v3.1/send",
                auth=(settings.MAILJET_API_KEY, settings.MAILJET_SECRET_KEY),
                json=payload,
            )
        response.raise_for_status()
        new_count = await increment_email_count()
        return {
            "status": "sent",
            "quota_used": new_count,
            "response": response.json(),
        }
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[EMAIL][MAILJET] API error sending to %s: %s %s",
            to_email,
            exc.response.status_code,
            exc.response.text[:300],
        )
        return {
            "status": "error",
            "message": f"HTTP {exc.response.status_code}",
        }
    except Exception as exc:
        logger.error("[EMAIL][MAILJET] Unexpected error sending to %s: %s", to_email, exc)
        return {"status": "error", "message": str(exc)}
