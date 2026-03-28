from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime

from bson import ObjectId, json_util
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pymongo.errors import DuplicateKeyError

from app.core.content_crypto import (
    decrypt_reply_preview,
    encrypt_message_document,
    encrypt_reply_preview,
    resolve_message_content,
)
from app.core.rate_limiter import evaluate_websocket_connection
from app.core.security import get_authenticated_user_id_from_token, get_websocket_token
from app.db.mongo import get_community_db, get_database
from app.services.chat_email_service import (
    clear_chat_email_rollup,
    clear_chat_email_rollups_for_user,
    trigger_chat_email_notification,
)
from app.services.connection_manager import manager
from app.services.permissions import get_chat_permission_state
from app.services.push_service import send_push_notification

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_participants_key(participants: list[str]) -> str:
    return "::".join(sorted(participants))


def _chat_route_for_user(user_id: str) -> str:
    return f"/chats/user/{user_id}"


async def _ensure_conversation(db, *, sender_id: str, recipient_id: str) -> dict:
    participants = sorted([sender_id, recipient_id])
    participants_key = _build_participants_key(participants)
    conversation = await db.conversations.find_one({"participants_key": participants_key})
    if conversation:
        return conversation

    now = datetime.utcnow()
    conversation_doc = {
        "participants": participants,
        "participants_key": participants_key,
        "created_at": now,
        "createdAt": now,
        "updated_at": now,
        "updatedAt": now,
        "hidden_for": [],
    }
    try:
        result = await db.conversations.insert_one(conversation_doc)
        conversation_doc["_id"] = result.inserted_id
        return conversation_doc
    except DuplicateKeyError:
        return await db.conversations.find_one({"participants_key": participants_key})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    try:
        decision = evaluate_websocket_connection(websocket)
        if decision and not decision.allowed:
            await websocket.close(code=4408, reason="Rate limit exceeded")
            return

        resolved_token = get_websocket_token(websocket, token)
        if not resolved_token:
            raise HTTPException(status_code=401, detail="Authentication token missing")

        user_id = await get_authenticated_user_id_from_token(resolved_token)
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, user_id)
    await clear_chat_email_rollups_for_user(user_id)

    db = await get_database()
    community_db = await get_community_db()

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            event_type = payload.get("type")

            if event_type == "ping":
                await manager.heartbeat(user_id)
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif event_type == "message":
                await handle_message(user_id, payload, db, community_db)
            elif event_type == "typing_start":
                recipient_id = payload.get("recipient_id")
                if recipient_id:
                    await manager.emit_to_users(
                        {
                            "type": "typing_start",
                            "sender_id": user_id,
                            "conversation_id": payload.get("conversation_id"),
                        },
                        [recipient_id],
                    )
            elif event_type == "typing_stop":
                recipient_id = payload.get("recipient_id")
                if recipient_id:
                    await manager.emit_to_users(
                        {
                            "type": "typing_stop",
                            "sender_id": user_id,
                            "conversation_id": payload.get("conversation_id"),
                        },
                        [recipient_id],
                    )
            elif event_type == "delivery_receipt":
                message_id = payload.get("message_id")
                conversation_id = payload.get("conversation_id")
                sender_id = payload.get("sender_id")

                if message_id and not str(message_id).startswith("temp-") and ObjectId.is_valid(message_id):
                    await db.messages.update_one(
                        {"_id": ObjectId(message_id)},
                        {"$set": {"status": "delivered"}},
                    )
                    if sender_id:
                        await manager.emit_to_users(
                            {
                                "type": "message_delivered",
                                "message_id": message_id,
                                "conversation_id": conversation_id,
                            },
                            [sender_id],
                        )
            elif event_type == "read_receipt":
                message_ids = payload.get("message_ids", [])
                conversation_id = payload.get("conversation_id")
                recipient_id = payload.get("recipient_id")
                valid_message_ids = [
                    mid
                    for mid in message_ids
                    if not str(mid).startswith("temp-") and ObjectId.is_valid(mid)
                ]
                if valid_message_ids:
                    await db.messages.update_many(
                        {"_id": {"$in": [ObjectId(mid) for mid in valid_message_ids]}},
                        {"$set": {"status": "read"}},
                    )
                    await clear_chat_email_rollup(user_id, conversation_id)
                    if recipient_id:
                        await manager.emit_to_users(
                            {
                                "type": "read_receipt",
                                "message_ids": valid_message_ids,
                                "conversation_id": conversation_id,
                                "reader_id": user_id,
                            },
                            [recipient_id],
                        )
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception:
        await manager.disconnect(websocket, user_id)


async def check_permissions(sender_id: str, recipient_id: str, db, community_db, msg_type: str = "text"):
    permission_state = await get_chat_permission_state(sender_id, recipient_id)

    if permission_state["is_blocked"]:
        return False, permission_state["message"]

    if not permission_state["is_mutual"] and msg_type != "text":
        return False, "Only text messages are supported until both users follow each other."

    if not permission_state["can_send_message"]:
        return False, permission_state["message"]

    return True, None


async def handle_message(sender_id: str, payload: dict, db, community_db):
    try:
        recipient_id = payload.get("recipient_id")
        content = payload.get("content")
        msg_type = payload.get("message_type", "text")
        metadata = payload.get("metadata", {}) or {}
        reply_to = payload.get("reply_to")

        if not recipient_id or not content:
            return

        allowed, error_msg = await check_permissions(sender_id, recipient_id, db, community_db, msg_type)
        if not allowed:
            await manager.emit_to_users(
                {
                    "type": "error",
                    "message": error_msg,
                    "conversation_id": payload.get("conversation_id"),
                },
                [sender_id],
            )
            return

        conversation = await _ensure_conversation(
            db,
            sender_id=sender_id,
            recipient_id=recipient_id,
        )
        conversation_id = str(conversation["_id"])

        new_message = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "content": content,
            "type": msg_type,
            "metadata": metadata,
            "reply_to": reply_to,
            "status": "sent",
            "timestamp": datetime.utcnow(),
        }

        recipient_online = await manager.is_user_online(recipient_id)
        if recipient_online:
            new_message["status"] = "delivered"

        if reply_to and ObjectId.is_valid(reply_to):
            original_msg = await db.messages.find_one({"_id": ObjectId(reply_to)})
            if original_msg:
                original_sender_id = original_msg["sender_id"]
                original_sender_profile = await community_db.users.find_one({"user_id": original_sender_id})
                reply_sender_name = (
                    (original_sender_profile or {}).get("name")
                    or (original_sender_profile or {}).get("username")
                    or "Unknown"
                )
                new_message["reply_to_data"] = {
                    "id": str(original_msg["_id"]),
                    "type": original_msg.get("type", "text"),
                    "sender_name": reply_sender_name,
                    "content_encrypted": encrypt_reply_preview(
                        resolve_message_content(original_msg, route="ws.reply_preview"),
                        parent_document=new_message,
                        route="ws.reply_preview",
                    ),
                }

        stored_message = encrypt_message_document(new_message, route="ws.message")
        res = await db.messages.insert_one(stored_message)
        new_message["_id"] = str(res.inserted_id)
        if "reply_to_data" in new_message and "content_encrypted" in new_message["reply_to_data"]:
            reply_preview = new_message["reply_to_data"].pop("content_encrypted")
            new_message["reply_to_data"]["content"] = decrypt_reply_preview(
                reply_preview,
                parent_document=new_message,
                route="ws.reply_preview",
            )
        new_message["timestamp"] = new_message["timestamp"].isoformat()

        preview_text = content if msg_type == "text" else f"[{msg_type.title()}]"
        if len(preview_text) > 120:
            preview_text = f"{preview_text[:117]}..."

        await db.conversations.update_one(
            {"_id": conversation["_id"]},
            {
                "$set": {
                    "updated_at": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "last_message": {
                        "content": preview_text,
                        "sender_id": sender_id,
                        "timestamp": datetime.utcnow(),
                        "type": msg_type,
                        "status": new_message["status"],
                    },
                },
                "$pullAll": {"hidden_for": [sender_id, recipient_id]},
            },
        )

        ack_payload = {
            "type": "message_ack",
            "temp_id": payload.get("temp_id"),
            "real_id": new_message["_id"],
            "conversation_id": conversation_id,
            "status": "sent",
            "timestamp": new_message["timestamp"],
        }
        await manager.emit_to_users(ack_payload, [sender_id])

        serialized_msg = json.loads(json_util.dumps(new_message))
        out_payload = {
            "type": "new_message",
            "message": serialized_msg,
        }
        await manager.emit_to_users(out_payload, [recipient_id])

        if new_message["status"] == "delivered":
            await manager.emit_to_users(
                {
                    "type": "message_delivered",
                    "message_id": new_message["_id"],
                    "conversation_id": conversation_id,
                    "recipient_id": recipient_id,
                },
                [sender_id],
            )

        sender_profile = await community_db.users.find_one(
            {"user_id": sender_id},
            {"name": 1, "username": 1, "photo": 1},
        )
        sender_name = (
            (sender_profile or {}).get("name")
            or (sender_profile or {}).get("username")
            or "Someone"
        )
        sender_photo = (sender_profile or {}).get("photo")
        push_body = content if msg_type == "text" else f"Sent a {msg_type}"
        if len(push_body) > 100:
            push_body = f"{push_body[:97]}..."

        chat_url = _chat_route_for_user(sender_id)
        await send_push_notification(
            [recipient_id],
            {
                "title": f"New message from {sender_name}",
                "body": push_body,
                "message": push_body,
                "icon": "/favicon.ico",
                "tag": f"chat:{conversation_id}",
                "action_url": chat_url,
                "url": chat_url,
                "data": {
                    "conversation_id": conversation_id,
                    "sender_id": sender_id,
                    "url": chat_url,
                },
            },
            category="chats",
            require_offline=True,
        )

        try:
            await trigger_chat_email_notification(
                recipient_id=recipient_id,
                sender_id=sender_id,
                sender_name=sender_name,
                sender_avatar_url=sender_photo,
                message_preview=content,
                message_type=msg_type,
                conversation_id=conversation_id,
                chat_url=chat_url,
            )
        except Exception as email_err:
            logger.error("[CHAT] Failed to queue chat email notification: %s", email_err, exc_info=True)

    except Exception:
        traceback.print_exc()
        await manager.emit_to_users(
            {
                "type": "error",
                "message": "Failed to deliver message. Please try again.",
            },
            [sender_id],
        )
