import asyncio
import json
from datetime import datetime, timedelta

import requests
import websockets
from jose import jwt

from app.core.config import get_settings

settings = get_settings()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
WS_URL = "ws://localhost:8000/ws"
API_URL = "http://localhost:8000/api/chat"

def create_test_token(user_id):
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def test_chat_flow():
    # print("--- Starting Chat System Test ---")

    # 1. Setup Test Users
    user_a = "user_test_A"
    user_b = "user_test_B"
    token_a = create_test_token(user_a)
    token_b = create_test_token(user_b)

    # print(f"Generated tokens for {user_a} and {user_b}")

    # 2. Test REST API (Health/Conversations)
    try:
        headers = {"Authorization": f"Bearer {token_a}"}
        resp = requests.get(f"{API_URL}/conversations", headers=headers)
        if resp.status_code == 200:
            # print("✅ REST API /conversations reachable")
        else:
            # print(f"❌ REST API Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        # print(f"❌ REST API Connection Error: {e}")

    # 3. Test WebSocket Connection & Messaging
    async with websockets.connect(f"{WS_URL}?token={token_b}") as ws_b:
        # print(f"✅ {user_b} connected to WebSocket")
        
        async with websockets.connect(f"{WS_URL}?token={token_a}") as ws_a:
            # print(f"✅ {user_a} connected to WebSocket")

            # A sends message to B
            msg_content = f"Hello from A at {datetime.now().isoformat()}"
            await ws_a.send(json.dumps({
                "type": "message",
                "recipient_id": user_b,
                "content": msg_content,
                "message_type": "text"
            }))
            # print(f"📤 {user_a} sent message")

            # B receives message
            # We might receive other messages first (like status updates), so loop briefly
            received = False
            try:
                # Wait for a few seconds max
                response = await asyncio.wait_for(ws_b.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get("type") == "new_message" and data["message"]["content"] == msg_content:
                    # print(f"✅ {user_b} received message: {data['message']['content']}")
                    received = True
                else:
                    # print(f"⚠️ Received unexpected message: {data}")
            except asyncio.TimeoutError:
                # print("❌ Timeout waiting for message delivery")

            # 4. Test 5-Message Rule (Limit)
            # We assume A and B are NOT following each other (mock data default).
            # We already sent 1. Let's send 5 more rapidly.
            # print("\n--- Testing Rate Limit / 5-Message Rule ---")
            for i in range(5):
                await ws_a.send(json.dumps({
                    "type": "message",
                    "recipient_id": user_b,
                    "content": f"Spam {i}",
                    "message_type": "text"
                }))
                # Read echo back to clear buffer
                try:
                    await asyncio.wait_for(ws_a.recv(), timeout=1.0) 
                except: pass

            # The last one should trigger an error if rule works
            try:
                # Expecting error message on the socket for A
                # We might need to drain the socket of "new_message" echos first
                while True:
                    resp = await asyncio.wait_for(ws_a.recv(), timeout=2.0)
                    data = json.loads(resp)
                    if data.get("type") == "error":
                        # print(f"✅ Correctly received Limit Error: {data['message']}")
                        break
            except asyncio.TimeoutError:
                # print("⚠️ Did not receive limit error (might be following each other or DB not connected to community DB properly)")

    # print("\n--- Test Finished ---")

if __name__ == "__main__":
    asyncio.run(test_chat_flow())
