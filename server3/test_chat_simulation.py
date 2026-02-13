import asyncio
import websockets
import json
from jose import jwt
from datetime import datetime, timedelta
import os
import sys

# Add server3 to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__)))
from app.core.config import get_settings

settings = get_settings()

def generate_test_token(user_id):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=60)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def test_chat_flow():
    print("--- Starting Chat Server Test Simulation ---")
    
    # Simulate User A and User B
    user_a_id = "user_test_A"
    user_b_id = "user_test_B"
    
    token_a = generate_test_token(user_a_id)
    token_b = generate_test_token(user_b_id)
    
    uri = "ws://localhost:8000/ws"

    print(f"1. Connecting User A ({user_a_id})...")
    async with websockets.connect(f"{uri}?token={token_a}") as ws_a:
        print("   User A Connected!")
        
        print(f"2. Connecting User B ({user_b_id})...")
        async with websockets.connect(f"{uri}?token={token_b}") as ws_b:
            print("   User B Connected!")
            
            # User A sends message to User B
            msg_content = "Hello User B, this is a test message!"
            payload = {
                "type": "message",
                "recipient_id": user_b_id,
                "content": msg_content,
                "message_type": "text"
            }
            
            print(f"3. User A sending message: '{msg_content}'")
            await ws_a.send(json.dumps(payload))
            
            # User B should receive it
            print("4. User B waiting for message...")
            response_b = await asyncio.wait_for(ws_b.recv(), timeout=5.0)
            data_b = json.loads(response_b)
            
            if data_b.get("type") == "new_message":
                print(f"   SUCCESS: User B received: {data_b['message']['content']}")
            else:
                print(f"   FAILURE: User B received unexpected: {data_b}")
                
            # User A should receive confirmation (echo)
            print("5. User A waiting for confirmation...")
            response_a = await asyncio.wait_for(ws_a.recv(), timeout=5.0)
            data_a = json.loads(response_a)
             
            if data_a.get("type") == "new_message":
                 print(f"   SUCCESS: User A received confirmation.")
            else:
                 print(f"   FAILURE: User A received unexpected: {data_a}")

            # Test Typing
            print("6. Testing Typing Indicator...")
            typing_payload = {
                "type": "typing_start",
                "recipient_id": user_b_id,
                "conversation_id": "test_conv"
            }
            await ws_a.send(json.dumps(typing_payload))
            
            typing_response = await asyncio.wait_for(ws_b.recv(), timeout=5.0)
            data_typing = json.loads(typing_response)
            if data_typing.get("type") == "typing_start":
                print("   SUCCESS: User B received typing indicator.")
            else:
                print(f"   FAILURE: Unexpected typing response: {data_typing}")

    print("--- Test Simulation Completed Successfully ---")

if __name__ == "__main__":
    try:
        asyncio.run(test_chat_flow())
    except Exception as e:
        print(f"\n[ERROR] Test Failed: {e}")
        print("Make sure Server 3 is running: 'python server3/run.py'")
