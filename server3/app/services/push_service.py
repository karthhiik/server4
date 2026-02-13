import json
import asyncio
from typing import List, Dict, Any
from pywebpush import webpush, WebPushException
from app.core.config import get_settings
from app.db.mongo import get_community_db

settings = get_settings()

def _vapid_claims():
    return {'sub': settings.VAPID_SUBJECT}

def _send_single_notification_sync(subscription_info: Dict, data: str, private_key: str):
    """
    Synchronous function to send a single web push notification.
    Returns: 'success', 'gone', 'error'
    """
    try:
        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=private_key,
            vapid_claims=_vapid_claims()
        )
        return 'success'
    except WebPushException as e:
        # 410 Gone or 404 Not Found usually means subscription is invalid
        if e.response is not None and e.response.status_code in [404, 410]:
            return 'gone'
        print(f"WebPush Exception: {e}")
        return 'error'
    except Exception as e:
        print(f"General Push Error: {e}")
        return 'error'

async def send_push_notification(user_ids: List[str], payload: Dict, exclude_user_id: str = None):
    """
    Send push notifications to the specified users.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        # print("VAPID keys not configured. Skipping push notification.")
        return

    target_ids = [uid for uid in user_ids if uid and uid != exclude_user_id]
    if not target_ids:
        return

    community_db = await get_community_db()
    if community_db is None:
        return

    # Find active subscriptions for these users
    # Server 1 uses 'community_hub.push_subscriptions', where 'community_hub' is collection 'community_db'.
    # So the actual collection name is 'community_db.push_subscriptions'.
    cursor = community_db["community_db.push_subscriptions"].find({
        'user_id': {'$in': target_ids}, 
        'active': True
    })
    subscriptions = await cursor.to_list(length=None)

    if not subscriptions:
        return

    payload_str = json.dumps(payload)
    
    loop = asyncio.get_running_loop()
    
    # Process each subscription
    for sub_doc in subscriptions:
        sub_info = sub_doc.get('subscription')
        if not isinstance(sub_info, dict) or not sub_info.get('endpoint'):
            continue
            
        # Run in executor
        result = await loop.run_in_executor(
            None, 
            _send_single_notification_sync, 
            sub_info, 
            payload_str, 
            settings.VAPID_PRIVATE_KEY
        )

        if result == 'gone':
            # Remove invalid subscription
            await community_db["community_db.push_subscriptions"].delete_one({'_id': sub_doc['_id']})
