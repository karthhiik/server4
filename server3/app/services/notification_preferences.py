from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db.mongo import get_community_db


DEFAULT_NOTIFICATION_SETTINGS: dict[str, Any] = {
    "push_enabled": True,
    "push_posts": True,
    "push_events": True,
    "push_chats": True,
    "push_ideas": True,
    "push_realtime_syn": True,
    "in_app_enabled": True,
    "in_app_posts": True,
    "in_app_events": True,
    "in_app_chats": True,
    "in_app_ideas": True,
    "in_app_realtime_syn": True,
    "chat_sounds": True,
    "email_posts": True,
    "email_chats": True,
    "email_events": True,
    "email_ideas": True,
    "email_realtime_syn": True,
}


async def get_notification_settings(user_id: str) -> dict[str, Any]:
    community_db = await get_community_db()
    if community_db is None:
        return {"user_id": user_id, **DEFAULT_NOTIFICATION_SETTINGS}

    doc = await community_db.notification_settings.find_one({"user_id": user_id})
    if not doc:
        default_doc = {
            "user_id": user_id,
            **DEFAULT_NOTIFICATION_SETTINGS,
            "updated_at": datetime.now(timezone.utc),
        }
        try:
            await community_db.notification_settings.insert_one(default_doc)
        except Exception:
            pass
        return default_doc

    return {"user_id": user_id, **DEFAULT_NOTIFICATION_SETTINGS, **doc}


def notification_channel_enabled(
    settings_doc: dict[str, Any],
    *,
    medium: str,
    category: str,
) -> bool:
    medium = (medium or "").strip().lower()
    category = (category or "").strip().lower()
    if not medium or not category:
        return True

    master_key = f"{medium}_enabled"
    category_key = f"{medium}_{category}"
    if master_key in settings_doc and settings_doc.get(master_key) is False:
        return False
    if category_key in settings_doc and settings_doc.get(category_key) is False:
        return False
    return True
