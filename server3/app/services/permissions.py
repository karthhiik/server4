from app.db.mongo import get_community_db, get_database

FOLLOWS_COLLECTION = "community_db.follows"


async def get_chat_permission_state(sender_id: str, recipient_id: str) -> dict:
    """Return the effective chat permissions for a sender/recipient pair."""
    db = await get_database()
    community_db = await get_community_db()

    blocked_by_recipient = await db.blocks.find_one(
        {"blocker_id": recipient_id, "blocked_id": sender_id}
    )
    blocked_by_sender = await db.blocks.find_one(
        {"blocker_id": sender_id, "blocked_id": recipient_id}
    )

    is_following = bool(
        await community_db[FOLLOWS_COLLECTION].find_one(
            {"follower_id": sender_id, "followed_id": recipient_id}
        )
    )
    is_follower = bool(
        await community_db[FOLLOWS_COLLECTION].find_one(
            {"follower_id": recipient_id, "followed_id": sender_id}
        )
    )
    is_mutual = is_following and is_follower

    participants = sorted([sender_id, recipient_id])
    conversation = await db.conversations.find_one(
        {"participants": {"$all": participants, "$size": 2}}
    )

    my_text_count = 0
    if conversation:
        conversation_id = str(conversation["_id"])
        last_reply = await db.messages.find_one(
            {"conversation_id": conversation_id, "sender_id": recipient_id},
            sort=[("timestamp", -1)],
        )
        text_query = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "type": "text",
        }
        if last_reply and last_reply.get("timestamp"):
            text_query["timestamp"] = {"$gt": last_reply["timestamp"]}

        my_text_count = await db.messages.count_documents(text_query)

    remaining_messages = None if is_mutual else max(0, 5 - my_text_count)

    if blocked_by_recipient:
        return {
            "can_send_message": False,
            "reason": "blocked_by_recipient",
            "message": "You have been blocked by this user.",
            "is_blocked": True,
            "is_blocked_by_me": False,
            "is_blocked_by_them": True,
            "is_following": is_following,
            "is_follower": is_follower,
            "is_mutual": is_mutual,
            "message_count": my_text_count,
            "remaining_messages": remaining_messages,
        }

    if blocked_by_sender:
        return {
            "can_send_message": False,
            "reason": "blocked_by_sender",
            "message": "You blocked this user. Unblock to continue chatting.",
            "is_blocked": True,
            "is_blocked_by_me": True,
            "is_blocked_by_them": False,
            "is_following": is_following,
            "is_follower": is_follower,
            "is_mutual": is_mutual,
            "message_count": my_text_count,
            "remaining_messages": remaining_messages,
        }

    if is_mutual:
        return {
            "can_send_message": True,
            "reason": "mutual_follow",
            "message": "You can chat freely with this connection.",
            "is_blocked": False,
            "is_blocked_by_me": False,
            "is_blocked_by_them": False,
            "is_following": is_following,
            "is_follower": is_follower,
            "is_mutual": True,
            "message_count": my_text_count,
            "remaining_messages": None,
        }

    if my_text_count >= 5:
        return {
            "can_send_message": False,
            "reason": "intro_limit_reached",
            "message": "Intro message limit reached. Wait for their reply or become mutual followers.",
            "is_blocked": False,
            "is_blocked_by_me": False,
            "is_blocked_by_them": False,
            "is_following": is_following,
            "is_follower": is_follower,
            "is_mutual": False,
            "message_count": my_text_count,
            "remaining_messages": 0,
        }

    return {
        "can_send_message": True,
        "reason": "intro_window_open",
        "message": f"You can send {remaining_messages} more intro message(s) until they reply.",
        "is_blocked": False,
        "is_blocked_by_me": False,
        "is_blocked_by_them": False,
        "is_following": is_following,
        "is_follower": is_follower,
        "is_mutual": False,
        "message_count": my_text_count,
        "remaining_messages": remaining_messages,
    }

async def check_upload_permissions(sender_id: str, recipient_id: str, file_size: int, content_type: str) -> tuple[bool, str]:
    """
    Enforce Upload Rules:
    1. Stranger: < 3 MB, No Audio
    2. Connection: < 15 MB, Audio Allowed
    """
    
    try:
        file_size_bytes = int(file_size)
    except (TypeError, ValueError):
        return False, "Invalid file size."

    if file_size_bytes <= 0:
        return False, "Invalid file size."

    # 1. Check Relationship Status
    community_db = await get_community_db()
    
    # Check if sender follows recipient
    i_follow = await community_db[FOLLOWS_COLLECTION].find_one({
        "follower_id": sender_id,
        "followed_id": recipient_id
    })
    
    # Check if recipient follows sender
    they_follow = await community_db[FOLLOWS_COLLECTION].find_one({
        "follower_id": recipient_id,
        "followed_id": sender_id
    })
    
    is_connected = bool(i_follow or they_follow) # Following or Follower = Connection
    is_mutual = bool(i_follow and they_follow)
    
    # For now, "Connection" means at least one way following (to be generous), 
    # OR strictly following. 
    # Requirement: "unfollowing or user a is not following user b" -> Stranger.
    # So if I follow them, I am NOT a stranger to them? Or if they follow me?
    # Let's be strict: If I don't follow them AND they don't follow me -> Stranger.
    
    is_stranger = not is_connected
    
    # Limits
    STRANGER_LIMIT = 3 * 1024 * 1024 # 3 MB
    CONNECTION_LIMIT = 15 * 1024 * 1024 # 15 MB
    
    # Check Rules
    if is_stranger:
        # NOTE: Temporarily disabled audio restriction for testing
        # if content_type.startswith("audio/"):
        #     return False, "Audio messages are not allowed for new connections."
        
        if file_size_bytes > STRANGER_LIMIT:
            return False, f"File too large. Limit is 3MB for new connections."
            
    else:
        # Is Connection
        if file_size_bytes > CONNECTION_LIMIT:
            return False, f"File too large. Limit is 15MB."
            
    return True, "Allowed"
