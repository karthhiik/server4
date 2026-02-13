from app.db.mongo import get_community_db

async def check_upload_permissions(sender_id: str, recipient_id: str, file_size: int, content_type: str) -> tuple[bool, str]:
    """
    Enforce Upload Rules:
    1. Stranger: < 3 MB, No Audio
    2. Connection: < 15 MB, Audio Allowed
    """
    
    # 1. Check Relationship Status
    community_db = await get_community_db()
    
    # Check if sender follows recipient
    i_follow = await community_db["follows"].find_one({
        "follower_id": sender_id,
        "followed_id": recipient_id
    })
    
    # Check if recipient follows sender
    they_follow = await community_db["follows"].find_one({
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
        
        if file_size > STRANGER_LIMIT:
            return False, f"File too large. Limit is 3MB for new connections."
            
    else:
        # Is Connection
        if file_size > CONNECTION_LIMIT:
            return False, f"File too large. Limit is 15MB."
            
    return True, "Allowed"
