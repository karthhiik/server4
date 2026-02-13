from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.services.connection_manager import manager
from app.services.push_service import send_push_notification
from app.core.security import get_current_user_id_from_token
from app.db.mongo import get_database, get_community_db
from app.models.chat import MessageCreate, MessageMetadata
from datetime import datetime, timedelta
from bson import ObjectId
import json

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket Endpoint for Real-Time Chat.
    Query param `token` required for authentication.
    """
    try:
        user_id = get_current_user_id_from_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, user_id)
    
    db = await get_database()
    community_db = await get_community_db()
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # Basic Event Handling
            event_type = payload.get("type")
            
            if event_type == "ping":
                # Heartbeat Response
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif event_type == "message":
                await handle_message(user_id, payload, db, community_db)
            elif event_type == "typing_start":
                recipient_id = payload.get("recipient_id")
                if recipient_id:
                    await manager.send_personal_message({
                        "type": "typing_start",
                        "sender_id": user_id,
                        "conversation_id": payload.get("conversation_id")
                    }, recipient_id)
            elif event_type == "typing_stop":
                recipient_id = payload.get("recipient_id")
                if recipient_id:
                    await manager.send_personal_message({
                        "type": "typing_stop",
                        "sender_id": user_id,
                        "conversation_id": payload.get("conversation_id")
                    }, recipient_id)
            elif event_type == "delivery_receipt":
                # New Logic: Client confirms it received the message
                message_id = payload.get("message_id")
                conversation_id = payload.get("conversation_id")
                sender_id = payload.get("sender_id") # Original sender of the message
                
                # Filter temp IDs
                if message_id and not str(message_id).startswith('temp-') and ObjectId.is_valid(message_id):
                     await db.messages.update_one(
                         {"_id": ObjectId(message_id)},
                         {"$set": {"status": "delivered"}}
                     )
                     # Notify original sender
                     if sender_id:
                         await manager.send_personal_message({
                            "type": "message_delivered",
                            "message_id": message_id,
                            "conversation_id": conversation_id
                         }, sender_id)

            elif event_type == "read_receipt":
                # Mark messages as read
                message_ids = payload.get("message_ids", [])
                conversation_id = payload.get("conversation_id")
                recipient_id = payload.get("recipient_id")
                
                if message_ids:
                    # Filter out temporary IDs (starting with 'temp-')
                    valid_message_ids = [mid for mid in message_ids if not str(mid).startswith('temp-') and ObjectId.is_valid(mid)]
                    
                    if valid_message_ids:
                        # Update DB
                        await db.messages.update_many(
                            {"_id": {"$in": [ObjectId(mid) for mid in valid_message_ids]}},
                            {"$set": {"status": "read"}}
                        )
                        # Notify sender (Real-time Ticks)
                        if recipient_id: 
                            await manager.send_personal_message({
                                "type": "read_receipt",
                                "message_ids": valid_message_ids,
                                "conversation_id": conversation_id,
                                "reader_id": user_id
                            }, recipient_id)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket, user_id)

async def check_permissions(sender_id: str, recipient_id: str, db, community_db, msg_type: str = "text"):
    """
    Check if sender is allowed to message recipient.
    Rules:
    1. Not blocked.
    2. 5-Message Limit if not following.
    """
    # 1. Check Block
    # Check if recipient blocked sender
    block_check = await db.blocks.find_one({"blocker_id": recipient_id, "blocked_id": sender_id})
    if block_check:
        return False, "You have been blocked by this user."
        
    # Check if sender blocked recipient (shouldn't happen in UI but good to enforce)
    my_block = await db.blocks.find_one({"blocker_id": sender_id, "blocked_id": recipient_id})
    if my_block:
        return False, "You blocked this user. Unblock to send messages."

    # 2. Check Follow Status (in Server 1 DB)
    # Based on Server 1 'follow_bp.py', the collection is 'follows' in 'barise_auth_db'
    # Server 1 accesses it via community_hub.follows (where community_hub is 'community_db' collection)
    # So actual collection name is 'community_db.follows'
    
    # Check if Recipient Follows Sender
    is_connected = await community_db["community_db.follows"].find_one({
        "follower_id": recipient_id,
        "followed_id": sender_id
    })
    
    if not is_connected:
        # Rule: If NO connection (mutual or they follow me), apply limit.
        # Strict Mutual Check: Both must follow each other for UNLIMITED.
        # If they follow me (is_connected), they initiated interest -> UNLIMITED (usually).
        # Wait, requirements say: "if mutual following unlimited... if not mutual friend... restrict"
        
        # So:
        # Mutual = I follow them AND they follow me.
        # If ONLY I follow them -> Restricted?
        # If ONLY they follow me -> Restricted? (Usually if they follow me, I can reply unlimitedly).
        
        # Let's check "Do I follow them?"
        i_follow_them = await community_db["community_db.follows"].find_one({
            "follower_id": sender_id,
            "followed_id": recipient_id
        })
        
        # Mutual means both exist
        is_mutual = is_connected and i_follow_them
        
        # User requirement: "if two users are mutual following each other then they can send more... if not mutual... restrict"
        # This implies strict mutual check.
        
        if not is_mutual:
            # Enforce Limit
            # Count messages from Sender to Recipient since last message from Recipient
            
            # Find last message from Recipient
            participants = sorted([sender_id, recipient_id])
            conversation = await db.conversations.find_one({"participants": {"$all": participants, "$size": 2}})
            
            if conversation:
                conv_id = str(conversation["_id"])
                last_reply = await db.messages.find_one(
                    {"conversation_id": conv_id, "sender_id": recipient_id},
                    sort=[("timestamp", -1)]
                )
                last_time = last_reply["timestamp"] if last_reply else datetime.min
                
                # Count Texts
                my_text_count = await db.messages.count_documents({
                    "conversation_id": conv_id,
                    "sender_id": sender_id,
                    "timestamp": {"$gt": last_time},
                    "type": "text"
                })

                # Rule: 5 Texts (Files removed)
                if msg_type == "text":
                    if my_text_count >= 5:
                         return False, "Text message limit reached (5/5). Wait for a reply or follow back."
                else:
                     return False, "Only text messages are supported for non-mutual connections."

    return True, None

from bson import ObjectId, json_util
import json
import traceback

# ... existing imports ...

async def handle_message(sender_id: str, payload: dict, db, community_db):
    """
    Process incoming message: Save to DB -> Route to Recipient
    Handles sanitization and safe BSON serialization.
    """
    try:
        recipient_id = payload.get("recipient_id")
        content = payload.get("content")
        msg_type = payload.get("message_type", "text")
        metadata = payload.get("metadata", {}) or {}
        reply_to = payload.get("reply_to")
        
        if not recipient_id or not content:
            return

        # Check Permissions
        allowed, error_msg = await check_permissions(sender_id, recipient_id, db, community_db, msg_type)
        if not allowed:
            await manager.send_personal_message({
                "type": "error",
                "message": error_msg,
                "conversation_id": payload.get("conversation_id")
            }, sender_id)
            return
        
        # --- DATA MAPPING & SANITIZATION ---
        
        # Generate Conversation ID
        participants = sorted([sender_id, recipient_id])
        conversation_query = {"participants": {"$all": participants, "$size": 2}}
        conversation = await db.conversations.find_one(conversation_query)
        
        if not conversation:
            res = await db.conversations.insert_one({
                "participants": participants,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            conversation_id = str(res.inserted_id)
        else:
            conversation_id = str(conversation["_id"])
            await db.conversations.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"updated_at": datetime.utcnow()}}
            )

        # Create Message Object
        new_message = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "content": content,
            "type": msg_type,
            "metadata": metadata,
            "reply_to": reply_to,
            "status": "sent",
            "timestamp": datetime.utcnow()
        }
        
        # Check Delivery Status
        if await manager.is_user_online(recipient_id):
            new_message["status"] = "delivered"

        # Handle Reply Data
        if reply_to:
            original_msg = await db.messages.find_one({"_id": ObjectId(reply_to)})
            if original_msg:
                 original_sender_id = original_msg["sender_id"]
                 original_sender_profile = await community_db.users.find_one({"user_id": original_sender_id})
                 sender_name = original_sender_profile.get("name") or original_sender_profile.get("username") or "Unknown"
                 
                 new_message["reply_to_data"] = {
                     "id": str(original_msg["_id"]),
                     "content": original_msg["content"],
                     "type": original_msg.get("type", "text"),
                     "sender_name": sender_name
                 }

        # Insert into DB
        res = await db.messages.insert_one(new_message)
        new_message["_id"] = str(res.inserted_id)
        # Convert datetime to string for immediate JSON usage, 
        # BUT we will use json_util for the broadcast payload to be safe.
        new_message["timestamp"] = new_message["timestamp"].isoformat()
        
        # --- SAFE BROADCASTING ---
        # Use json_util to handle any remaining BSON types (like ObjectId if we missed one)
        # and then parse back to dict for the manager.
        
        # 1. Send ACK to Sender (WhatsApp Style)
        # This confirms the message was saved and provides the real ID.
        ack_payload = {
            "type": "message_ack",
            "temp_id": payload.get("temp_id"), # The ID generated by frontend
            "real_id": new_message["_id"],
            "conversation_id": conversation_id,
            "status": "sent",
            "timestamp": new_message["timestamp"]
        }
        await manager.send_personal_message(ack_payload, sender_id)
        
        # 2. Send Message to Recipient
        # Serialize with json_util to handle ObjectId and Datetime, then load back to dict
        serialized_msg = json.loads(json_util.dumps(new_message))
        
        out_payload = {
            "type": "new_message",
            "message": serialized_msg
        }
        
        print(f"✅ Broadcasting {msg_type} from {sender_id} to {recipient_id}")
        
        # Send to Recipient
        await manager.send_personal_message(out_payload, recipient_id)
        
        # Delivery Receipt
        if new_message["status"] == "delivered":
            await manager.send_personal_message({
                "type": "message_delivered",
                "message_id": new_message["_id"],
                "conversation_id": conversation_id,
                "recipient_id": recipient_id
            }, sender_id)

        # Push Notification
        sender_profile = await community_db.users.find_one({"user_id": sender_id})
        sender_name = sender_profile.get("name") or sender_profile.get("username") or "Someone"
        
        push_body = content if msg_type == "text" else f"Sent a {msg_type}"
        if len(push_body) > 100: push_body = push_body[:97] + "..."
            
        await send_push_notification([recipient_id], {
            "title": f"New message from {sender_name}",
            "body": push_body,
            "icon": "/assets/intel.png", 
            "data": {
                "url": f"/chat/{conversation_id}",
                "conversation_id": conversation_id,
                "sender_id": sender_id
            }
        })

    except Exception as e:
        print(f"❌ CRITICAL ERROR in handle_message: {str(e)}")
        traceback.print_exc()
        # Notify sender of failure
        await manager.send_personal_message({
            "type": "error",
            "message": "Failed to deliver message. Please try again."
        }, sender_id)
