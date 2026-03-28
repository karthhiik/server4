from __future__ import annotations

import asyncio
import json
from typing import Any

from pywebpush import WebPushException, webpush

from app.core.config import get_settings
from app.db.mongo import get_community_db
from app.services.notification_preferences import (
    get_notification_settings,
    notification_channel_enabled,
)
from app.services.presence_service import presence_service

settings = get_settings()


def _vapid_claims():
    return {"sub": settings.VAPID_SUBJECT}


def _send_single_notification_sync(
    subscription_info: dict[str, Any],
    data: str,
    private_key: str,
):
    try:
        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=private_key,
            vapid_claims=_vapid_claims(),
        )
        return "success"
    except WebPushException as exc:
        if exc.response is not None and exc.response.status_code in [404, 410]:
            return "gone"
        return "error"
    except Exception:
        return "error"


def _resolve_notification_url(url: str | None) -> str:
    target = (url or "/").strip() or "/"
    if target.startswith("http://") or target.startswith("https://"):
        return target
    return f"{settings.FRONTEND_URL.rstrip('/')}{target if target.startswith('/') else f'/{target}'}"


async def _is_push_allowed_for_user(
    user_id: str,
    *,
    category: str,
    require_offline: bool,
) -> bool:
    settings_doc = await get_notification_settings(user_id)
    if not notification_channel_enabled(settings_doc, medium="push", category=category):
        return False

    if require_offline:
        return not await presence_service.is_online(user_id)
    return True


async def send_push_notification(
    user_ids: list[str],
    payload: dict[str, Any],
    exclude_user_id: str | None = None,
    *,
    category: str = "chats",
    require_offline: bool | None = None,
):
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return

    target_ids = [uid for uid in user_ids if uid and uid != exclude_user_id]
    if not target_ids:
        return

    effective_require_offline = (
        settings.CHAT_PUSH_REQUIRE_OFFLINE if require_offline is None else require_offline
    )

    allowed_ids: list[str] = []
    for user_id in target_ids:
        if await _is_push_allowed_for_user(
            user_id,
            category=category,
            require_offline=effective_require_offline,
        ):
            allowed_ids.append(user_id)

    if not allowed_ids:
        return

    community_db = await get_community_db()
    if community_db is None:
        return

    subscriptions = await community_db["push_subscriptions"].find(
        {"user_id": {"$in": allowed_ids}, "active": True}
    ).to_list(length=None)
    if not subscriptions:
        subscriptions = await community_db["community_db.push_subscriptions"].find(
            {"user_id": {"$in": allowed_ids}, "active": True}
        ).to_list(length=None)

    if not subscriptions:
        return

    normalized_payload = {
        **payload,
        "url": _resolve_notification_url(payload.get("url")),
        "action_url": _resolve_notification_url(payload.get("action_url") or payload.get("url")),
        "category": category,
    }
    payload_str = json.dumps(normalized_payload)
    loop = asyncio.get_running_loop()

    for sub_doc in subscriptions:
        if sub_doc.get("user_id") not in allowed_ids:
            continue
        sub_info = sub_doc.get("subscription")
        if not isinstance(sub_info, dict) or not sub_info.get("endpoint"):
            continue

        result = await loop.run_in_executor(
            None,
            _send_single_notification_sync,
            sub_info,
            payload_str,
            settings.VAPID_PRIVATE_KEY,
        )

        if result == "gone":
            primary_exists = await community_db["push_subscriptions"].count_documents(
                {"_id": sub_doc["_id"]},
                limit=1,
            )
            if primary_exists:
                await community_db["push_subscriptions"].delete_one({"_id": sub_doc["_id"]})
            else:
                await community_db["community_db.push_subscriptions"].delete_one({"_id": sub_doc["_id"]})
