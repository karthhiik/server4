from fastapi import WebSocket
from typing import Dict, List, Set
import json
import asyncio
from app.db.redis import get_redis
from app.models.chat import Message
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        # Active connections: user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"User {user_id} connected. Active connections: {len(self.active_connections.get(user_id))}")
        
        # Update Presence in Redis
        await self.set_presence(user_id, "online")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                # Set Offline if no connections left
                await self.set_presence(user_id, "offline")
        print(f"User {user_id} disconnected")

    async def set_presence(self, user_id: str, status: str):
        """
        Update user status in Redis (online/offline/typing)
        """
        redis = await get_redis()
        if not redis: return

        key = f"user:presence:{user_id}"
        await redis.set(key, status, ex=300) # 5 mins TTL
        
        if status == "offline":
             await redis.set(f"user:last_seen:{user_id}", datetime.utcnow().isoformat())
             
        # Ideally, we should broadcast this to friends/active chats.
        # For MVP, we won't broadcast globally to save bandwidth, 
        # but the client can poll or we can implement a 'subscribe' mechanism.
        
    async def get_presence(self, user_id: str):
        redis = await get_redis()
        if not redis: return {"status": "offline", "last_seen": None}
        
        status = await redis.get(f"user:presence:{user_id}")
        last_seen = await redis.get(f"user:last_seen:{user_id}")
        
        return {
            "status": status or "offline",
            "last_seen": last_seen
        }

    async def is_user_online(self, user_id: str) -> bool:
        """Check if user has any active WebSocket connections locally"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

        
    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send a message to a specific user's connected sockets.
        """
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message to {user_id}: {e}")

    async def broadcast(self, message: dict):
        """
        Broadcast to all connected users.
        """
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                await connection.send_json(message)

    async def setup_redis_pubsub(self):
        """
        Listen to Redis channels for messages from other server instances.
        """
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("chat_messages")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                recipient_id = data.get("recipient_id")
                if recipient_id:
                    await self.send_personal_message(data, recipient_id)

manager = ConnectionManager()
