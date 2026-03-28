from fastapi import APIRouter, Depends, HTTPException
from app.db.mongo import get_database, get_community_db
from app.core.content_crypto import (
    decrypt_message_document,
    decrypt_reply_preview,
    encrypt_message_document,
    resolve_message_content,
)
from app.core.security import get_current_user
from bson import ObjectId
from typing import List
from datetime import datetime
from app.services.avatar_service import (
    build_avatar_document_for_update,
    build_avatar_event_payload,
    resolve_user_avatar,
    _safe_seed,
    _normalize_variant,
)
from app.services.permissions import get_chat_permission_state

router = APIRouter()

async def _broadcast_avatar_update(
    *,
    user_id: str,
    resolved_avatar: dict,
) -> None:
    from app.services.connection_manager import manager

    db = await get_database()
    cursor = db.conversations.find({"participants": user_id})
    participant_ids: set[str] = set()
    async for conv in cursor:
        for participant_id in conv.get("participants", []):
            if participant_id == user_id:
                continue
            participant_ids.add(participant_id)

    if participant_ids:
        await manager.emit_to_users(
            {
                "type": "user_update",
                "user_id": user_id,
                "avatar": resolved_avatar["thumb_url"],
                "avatar_version": resolved_avatar["version"],
                "resolved_thumb_url": resolved_avatar["thumb_url"],
                "updated_at": resolved_avatar.get("updated_at"),
            },
            list(participant_ids),
        )

@router.post("/user/avatar")
async def update_avatar(payload: dict, user_id: str = Depends(get_current_user)):
    """
    Update user avatar (photo) in the central user database (community_db.users)
    payload supports:
    - {"avatar_url": "https://..."}
    - {"variant": "male|female|neutral", "options": {...}}
    """
    community_db = await get_community_db()
    user_doc = await community_db.users.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    if bool(payload.get("broadcast_only")):
        resolved_avatar = resolve_user_avatar(user_doc)
        event_payload = build_avatar_event_payload(user_id, resolved_avatar)
        await _broadcast_avatar_update(user_id=user_id, resolved_avatar=resolved_avatar)
        return {
            "message": "Avatar broadcast sent",
            "avatar_url": resolved_avatar["url"],
            "avatar_version": resolved_avatar["version"],
            "resolved_thumb_url": resolved_avatar["thumb_url"],
            "event": event_payload,
        }

    avatar_url = payload.get("avatar_url")
    variant = payload.get("variant")
    style_key = payload.get("style_key")
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}

    if avatar_url and not isinstance(avatar_url, str):
        raise HTTPException(status_code=400, detail="avatar_url must be a string")

    if not avatar_url:
        from chibi_renderer import render_chibi_svg
        seed = _safe_seed(user_doc)
        norm_variant = _normalize_variant(variant)
        svg = render_chibi_svg(seed, norm_variant, options or {})
        avatar_url = f"data:image/svg+xml;utf8,{svg}"

    source = payload.get("source", "generated")
    avatar_doc = build_avatar_document_for_update(
        user_doc=user_doc,
        avatar_url=avatar_url,
        variant=variant,
        style_key=style_key,
        options=options,
        source=source,
    )

    photo_value = str(avatar_url).strip()
    if photo_value.startswith("/uploads/"):
        photo_value = photo_value[len("/uploads/"):]
    elif photo_value.startswith("uploads/"):
        photo_value = photo_value[len("uploads/"):]
    
    # Update Server 1's User Collection
    result = await community_db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "photo": photo_value,
                "avatar": avatar_doc,
                "lastUpdated": datetime.utcnow(),
            }
        },
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = dict(user_doc)
    updated_user["photo"] = photo_value
    updated_user["avatar"] = avatar_doc
    resolved_avatar = resolve_user_avatar(updated_user)
    event_payload = build_avatar_event_payload(user_id, resolved_avatar)

    # Broadcast Real-Time Update to all connected peers
    await _broadcast_avatar_update(user_id=user_id, resolved_avatar=resolved_avatar)

    return {
        "message": "Avatar updated successfully",
        "avatar_url": resolved_avatar["url"],
        "avatar_version": resolved_avatar["version"],
        "resolved_thumb_url": resolved_avatar["thumb_url"],
        "event": event_payload,
    }
@router.get("/conversations")
async def get_conversations(user_id: str = Depends(get_current_user)):
    db = await get_database()
    community_db = await get_community_db()
    
    cursor = db.conversations.find(
        {
            "participants": user_id,
            "hidden_for": {"$ne": user_id},
        }
    ).sort("updated_at", -1)
    conversations = await cursor.to_list(length=100)
    
    results = []
    for conv in conversations:
        # Fetch last message
        last_msg = await db.messages.find_one(
            {"conversation_id": str(conv["_id"])},
            sort=[("timestamp", -1)]
        )
        
        # Determine other participant
        other_user_id = next((p for p in conv["participants"] if p != user_id), None)
        
        # Fetch User Details and Relationship
        other_user_data = None
        is_mutual = False
        is_following = False
        is_follower = False
        
        if other_user_id:
            other_user_data = await community_db.users.find_one({"user_id": other_user_id})
            
            # Check Relationships
            # 1. Do I follow them?
            i_follow = await community_db["community_db.follows"].find_one({
                "follower_id": user_id, 
                "followed_id": other_user_id
            })
            
            # 2. Do they follow me?
            they_follow = await community_db["community_db.follows"].find_one({
                "follower_id": other_user_id, 
                "followed_id": user_id
            })
            
            is_following = bool(i_follow)
            is_follower = bool(they_follow)
            is_mutual = is_following and is_follower
        
        # Default Name/Avatar if missing
        display_name = "Unknown User"
        username = "unknown"
        avatar_info = resolve_user_avatar({"user_id": other_user_id or "unknown"})
        avatar = avatar_info["thumb_url"]
        avatar_version = avatar_info["version"]
        
        if other_user_data:
            # User requested to show Name primarily, fallback to username
            display_name = other_user_data.get("name") or other_user_data.get("username") or display_name
            username = other_user_data.get("username") or username
            avatar_info = resolve_user_avatar(other_user_data)
            avatar = avatar_info["thumb_url"]
            avatar_version = avatar_info["version"]
        
        # Unread Count Logic
        unread_query = {
            "conversation_id": str(conv["_id"]),
            "sender_id": {"$ne": user_id},
            "status": {"$ne": "read"}
        }
        cleared_at = conv.get("cleared_at", {}).get(user_id)
        if cleared_at:
            unread_query["timestamp"] = {"$gt": cleared_at}
        unread_count = await db.messages.count_documents(unread_query)

        results.append({
            "id": str(conv["_id"]),
            "other_user_id": other_user_id,
            "other_user_name": display_name,
            "other_user_username": username,
            "other_user_avatar": avatar,
            "other_user_avatar_version": avatar_version,
            "is_mutual": is_mutual,
            "is_following": is_following,
            "is_follower": is_follower,
            "last_message": {
                "content": resolve_message_content(last_msg, route="chat.conversations") if last_msg else "",
                "sender_id": last_msg["sender_id"] if last_msg else None,
                "timestamp": last_msg["timestamp"].isoformat() if last_msg else None,
                "type": last_msg["type"] if last_msg else "text",
                "status": last_msg["status"] if last_msg else None,
            } if last_msg else None,
            "unread_count": unread_count
        })
        
    return results

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, user_id: str = Depends(get_current_user)):
    # Handle "new:..." temporary IDs from frontend
    if conversation_id.startswith("new:"):
        return []

    db = await get_database()
    
    try:
        oid = ObjectId(conversation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    # Verify participation
    conv = await db.conversations.find_one({"_id": oid, "participants": user_id})
    if not conv:
        # If conversation doesn't exist (maybe deleted?), return empty or 404
        # Return empty list to prevent frontend crash
        return []
        
    # Check if user cleared chat previously
    cleared_at = conv.get("cleared_at", {}).get(user_id)
    
    query = {"conversation_id": conversation_id}
    if cleared_at:
        query["timestamp"] = {"$gt": cleared_at}

    cursor = db.messages.find(query).sort("timestamp", 1)
    messages = await cursor.to_list(length=200)
    
    for msg in messages:
        decrypted_msg = decrypt_message_document(msg, route="chat.messages")
        reply_to_data = decrypted_msg.get("reply_to_data")
        if isinstance(reply_to_data, dict) and "content_encrypted" in reply_to_data:
            reply_to_data["content"] = decrypt_reply_preview(
                reply_to_data.pop("content_encrypted"),
                parent_document=decrypted_msg,
                route="chat.reply_preview",
            )
        msg.clear()
        msg.update(decrypted_msg)
        msg["id"] = str(msg["_id"])
        del msg["_id"]
        msg.pop("content_encrypted", None)
        msg["timestamp"] = msg["timestamp"].isoformat()
        
    return messages

@router.post("/users/{target_id}/block")
async def block_user(target_id: str, user_id: str = Depends(get_current_user)):
    db = await get_database()
    
    # Check if already blocked
    existing = await db.blocks.find_one({"blocker_id": user_id, "blocked_id": target_id})
    if existing:
        return {"message": "User already blocked"}
        
    await db.blocks.insert_one({
        "blocker_id": user_id,
        "blocked_id": target_id,
        "created_at": datetime.utcnow()
    })
    
    return {"message": "User blocked successfully"}

@router.post("/users/{target_id}/unblock")
async def unblock_user(target_id: str, user_id: str = Depends(get_current_user)):
    db = await get_database()
    result = await db.blocks.delete_one({"blocker_id": user_id, "blocked_id": target_id})
    
    if result.deleted_count == 0:
        return {"message": "User was not blocked"}
        
    return {"message": "User unblocked successfully"}

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, user_id: str = Depends(get_current_user)):
    db = await get_database()
    
    # Verify ownership
    msg = await db.messages.find_one({"_id": ObjectId(message_id), "sender_id": user_id})
    if not msg:
        raise HTTPException(status_code=403, detail="Message not found or access denied")
    
    # Soft delete or hard delete? Usually soft delete or replace content.
    # User said "Message is not getting deleted but it showing a alert".
    # We will remove it.
    await db.messages.delete_one({"_id": ObjectId(message_id)})
    
    # Notify other participants via WebSocket (Real-time Deletion)
    # We need to know who else is in the conversation to broadcast
    conversation_id = msg.get("conversation_id")
    if conversation_id:
        from app.services.connection_manager import manager
        
        # Broadcast to conversation participants (simulated via individual sends if broadcast not avail)
        # Ideally, connection manager should have broadcast_to_conversation
        # For now, we can try to send to the other user if we can find them
        # Faster: Client usually reloads, but user asked for REAL TIME.
        
        # Get conversation to find participants
        conv = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
        if conv:
            participant_ids = list(dict.fromkeys(conv.get("participants", [])))
            await manager.emit_to_users({
                "type": "message_deleted",
                "message_id": message_id,
                "conversation_id": conversation_id
            }, participant_ids)

    return {"message": "Message deleted"}

@router.put("/messages/{message_id}")
async def edit_message(message_id: str, content: str, user_id: str = Depends(get_current_user)):
    db = await get_database()
    
    # Verify ownership
    msg = await db.messages.find_one({"_id": ObjectId(message_id), "sender_id": user_id})
    if not msg:
        raise HTTPException(status_code=403, detail="Message not found or access denied")
        
    updated_document = encrypt_message_document(
        {
            **msg,
            "_id": str(msg["_id"]),
            "content": content,
        },
        route="chat.edit_message",
    )
    updated_document.pop("_id", None)
    await db.messages.update_one(
        {"_id": ObjectId(message_id)},
        {
            "$set": {
                **updated_document,
                "is_edited": True,
                "updated_at": datetime.utcnow(),
            },
            "$unset": {"content": ""},
        },
    )
    
    # Broadcast Real-Time Update
    conversation_id = msg.get("conversation_id")
    if conversation_id:
        from app.services.connection_manager import manager
        
        # Broadcast to conversation participants
        conv = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
        if conv:
            await manager.emit_to_users({
                "type": "message_updated",
                "message_id": message_id,
                "content": content,
                "is_edited": True,
                "conversation_id": conversation_id
            }, list(dict.fromkeys(conv.get("participants", []))))

    return {"message": "Message updated"}

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(get_current_user)):
    db = await get_database()
    
    # Verify participation
    conv = await db.conversations.find_one({"_id": ObjectId(conversation_id), "participants": user_id})
    if not conv:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # In a real app, you might want to "soft delete" or hide it for one user.
    # For now, we'll implement a "hide for user" mechanism or hard delete if both delete?
    # Simpler: Delete messages for this user context (requires complex schema).
    # MVP: Hard delete messages if requested (shared history gone? No, that's bad).
    
    # Better MVP: Just remove user from participants (if group) or hide it.
    # Let's implement "Clear History" logic: delete messages where conversation_id matches.
    # Wait, delete chat usually means "Hide from my list".
    
    # Implementation: Add "hidden_for" array to conversation
    await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$addToSet": {"hidden_for": user_id}}
    )
    
    return {"message": "Conversation deleted"}

@router.post("/conversations/{conversation_id}/clear")
async def clear_chat(conversation_id: str, user_id: str = Depends(get_current_user)):
    db = await get_database()
    
    # Verify participation
    conv = await db.conversations.find_one({"_id": ObjectId(conversation_id), "participants": user_id})
    if not conv:
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Logic: Mark all current messages as "deleted_for" this user.
    # Since we don't have "deleted_for" in schema yet, let's just pretend for MVP or delete strictly.
    # Strict delete is bad for the other user.
    # Let's add a "cleared_at" timestamp for the user in the conversation metadata.
    
    await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {f"cleared_at.{user_id}": datetime.utcnow()}}
    )
    
    return {"message": "Chat cleared"}

@router.get("/permissions/{target_id}")
async def get_chat_permissions(target_id: str, user_id: str = Depends(get_current_user)):
    if target_id == user_id:
        return {
            "can_send_message": False,
            "reason": "self",
            "message": "You cannot open a chat with yourself.",
            "is_blocked": False,
            "is_blocked_by_me": False,
            "is_blocked_by_them": False,
            "is_following": False,
            "is_follower": False,
            "is_mutual": False,
            "message_count": 0,
            "remaining_messages": 0,
        }

    return await get_chat_permission_state(user_id, target_id)

@router.get("/users/{user_id}/presence")
async def get_user_presence(user_id: str, current_user: str = Depends(get_current_user)):
    from app.services.connection_manager import manager
    presence = await manager.get_presence(user_id)
    return presence
