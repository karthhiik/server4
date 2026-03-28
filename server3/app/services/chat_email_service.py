from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.db.mongo import get_community_db, get_database
from app.services.email_provider_router import send_chat_email_via_provider
from app.services.llm_email_service import (
    build_chat_notification_html,
    generate_chat_email_content,
)
from app.services.notification_preferences import (
    get_notification_settings,
    notification_channel_enabled,
)
from app.services.presence_service import presence_service

logger = logging.getLogger(__name__)
settings = get_settings()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(raw_value: Any) -> datetime | None:
    if isinstance(raw_value, datetime):
        return raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=timezone.utc)
    if isinstance(raw_value, str):
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _absolute_chat_url(chat_url: str | None, *, sender_id: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    if chat_url:
        target = chat_url.strip()
        if target.startswith("http://") or target.startswith("https://"):
            return target
        if not target.startswith("/"):
            target = f"/{target}"
        return f"{base}{target}"
    return f"{base}/chats/user/{sender_id}"


def _normalize_message_preview(message_preview: str, message_type: str = "text") -> str:
    preview = (message_preview or "").strip()
    if message_type != "text" and preview and not preview.startswith("["):
        preview = f"[{message_type.title()}] {preview}"
    if not preview:
        preview = f"[{message_type.title()}]"
    if len(preview) > 220:
        preview = f"{preview[:217]}..."
    return preview


async def _get_user_info(user_id: str) -> dict[str, Any] | None:
    community_db = await get_community_db()
    if community_db is None:
        return None

    return await community_db.users.find_one(
        {"user_id": user_id},
        {"email": 1, "name": 1, "username": 1, "photo": 1},
    )


async def _build_rollup_document(
    *,
    recipient_id: str,
    sender_id: str,
    sender_name: str,
    sender_avatar_url: str | None,
    message_preview: str,
    conversation_id: str,
    chat_url: str,
) -> dict[str, Any]:
    now = _utc_now()
    return {
        "recipient_id": recipient_id,
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_avatar_url": sender_avatar_url,
        "chat_url": chat_url,
        "snippets": [message_preview],
        "unread_count": 1,
        "first_unread_at": now,
        "last_message_at": now,
        "updated_at": now,
        "created_at": now,
        "last_email_sent_at": None,
        "email_sent_count": 0,
    }


async def _update_rollup(
    db,
    *,
    recipient_id: str,
    sender_id: str,
    sender_name: str,
    sender_avatar_url: str | None,
    message_preview: str,
    conversation_id: str,
    chat_url: str,
) -> dict[str, Any]:
    rollups = db.chat_email_rollups
    existing = await rollups.find_one(
        {"recipient_id": recipient_id, "conversation_id": conversation_id}
    )
    if not existing:
        existing = await _build_rollup_document(
            recipient_id=recipient_id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_avatar_url=sender_avatar_url,
            message_preview=message_preview,
            conversation_id=conversation_id,
            chat_url=chat_url,
        )
        await rollups.insert_one(existing)
        return existing

    snippets = list(existing.get("snippets") or [])
    snippets.append(message_preview)
    snippets = snippets[-max(1, settings.CHAT_EMAIL_MAX_SUMMARY_MESSAGES) :]
    unread_count = int(existing.get("unread_count", 0)) + 1
    now = _utc_now()
    update_fields = {
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_avatar_url": sender_avatar_url,
        "chat_url": chat_url,
        "snippets": snippets,
        "unread_count": unread_count,
        "last_message_at": now,
        "updated_at": now,
    }
    await rollups.update_one(
        {"_id": existing["_id"]},
        {"$set": update_fields},
    )
    existing.update(update_fields)
    return existing


async def clear_chat_email_rollup(recipient_id: str, conversation_id: str) -> None:
    db = await get_database()
    await db.chat_email_rollups.delete_one(
        {"recipient_id": recipient_id, "conversation_id": conversation_id}
    )


async def clear_chat_email_rollups_for_user(recipient_id: str) -> None:
    db = await get_database()
    await db.chat_email_rollups.delete_many({"recipient_id": recipient_id})


async def _should_send_rollup_now(
    rollup: dict[str, Any],
    *,
    recipient_id: str,
) -> bool:
    if int(rollup.get("unread_count", 0)) < max(1, settings.CHAT_EMAIL_MIN_UNREAD_COUNT):
        return False

    prefs = await get_notification_settings(recipient_id)
    if not notification_channel_enabled(prefs, medium="email", category="chats"):
        return False

    presence = await presence_service.get_presence(recipient_id)
    if presence.get("status") == "online":
        return False

    last_seen = _parse_dt(presence.get("last_seen"))
    if last_seen is not None:
        minimum_offline_at = _utc_now() - timedelta(
            minutes=max(1, settings.CHAT_EMAIL_MIN_OFFLINE_MINUTES)
        )
        if last_seen > minimum_offline_at:
            return False

    last_email_sent_at = _parse_dt(rollup.get("last_email_sent_at"))
    if last_email_sent_at is not None:
        cooldown_cutoff = _utc_now() - timedelta(
            minutes=max(1, settings.CHAT_EMAIL_COOLDOWN_MINUTES)
        )
        if last_email_sent_at > cooldown_cutoff:
            return False

    return True


async def trigger_chat_email_notification(
    *,
    recipient_id: str,
    sender_id: str,
    sender_name: str,
    message_preview: str,
    conversation_id: str,
    sender_avatar_url: str | None = None,
    message_type: str = "text",
    chat_url: str | None = None,
) -> bool:
    if not (settings.MAIL_API_KEY or settings.MAILJET_API_KEY):
        logger.warning("[CHAT EMAIL] No email provider configured")
        return False

    recipient = await _get_user_info(recipient_id)
    if not recipient:
        return False

    recipient_email = (recipient.get("email") or "").strip()
    if not recipient_email or "@" not in recipient_email:
        return False

    normalized_preview = _normalize_message_preview(message_preview, message_type)
    resolved_chat_url = _absolute_chat_url(chat_url, sender_id=sender_id)
    db = await get_database()

    rollup = await _update_rollup(
        db,
        recipient_id=recipient_id,
        sender_id=sender_id,
        sender_name=sender_name,
        sender_avatar_url=sender_avatar_url,
        message_preview=normalized_preview,
        conversation_id=conversation_id,
        chat_url=resolved_chat_url,
    )

    if not await _should_send_rollup_now(rollup, recipient_id=recipient_id):
        return False

    recipient_name = (
        recipient.get("name")
        or recipient.get("username")
        or "there"
    )
    unread_count = int(rollup.get("unread_count", 1))
    llm_content = await generate_chat_email_content(
        sender_name=sender_name,
        message_preview=normalized_preview,
        unread_count=unread_count,
    )
    html_content = build_chat_notification_html(
        recipient_name=recipient_name,
        sender_name=sender_name,
        sender_avatar_url=sender_avatar_url,
        message_content=normalized_preview,
        chat_url=resolved_chat_url,
        llm_content=llm_content,
        unread_count=unread_count,
        brand_logo_url=settings.BARISE_EMAIL_LOGO_URL or None,
        message_snippets=rollup.get("snippets") or [],
    )

    result = await send_chat_email_via_provider(
        to_email=recipient_email,
        to_name=recipient_name,
        subject=llm_content.get("subject", f"{sender_name} messaged you on Barise"),
        html_content=html_content,
    )
    if result.get("status") != "sent":
        logger.warning(
            "[CHAT EMAIL] Failed to send rollup recipient=%s provider=%s status=%s",
            recipient_id,
            result.get("provider"),
            result.get("status"),
        )
        return False

    now = _utc_now()
    await db.chat_email_rollups.update_one(
        {"_id": rollup["_id"]},
        {
            "$set": {
                "last_email_sent_at": now,
                "updated_at": now,
                "last_delivery_provider": result.get("provider"),
            },
            "$inc": {"email_sent_count": 1},
        },
    )
    logger.info(
        "[CHAT EMAIL] Sent rollup recipient=%s conversation=%s unread=%s provider=%s",
        recipient_id,
        conversation_id,
        unread_count,
        result.get("provider"),
    )
    return True
