#!/usr/bin/env python
"""Start server and test the async endpoint"""
import subprocess
import time
import httpx
import asyncio
import json
import os
import signal
import sys

async def test_endpoint():
    """Test the async endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "prompt": "Create a business plan for a B2B SaaS startup in AI/ML space",
                "research_mode": "deep"
            }

            headers = {
                "Authorization": "Bearer test_jwt_token",
                "Content-Type": "application/json"
            }

            print("\nTesting POST /api/generate-business-plan-async")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            print(f"\nHeaders: {dict(headers)}\n")

            response = await client.post(
                "http://127.0.0.1:8080/api/generate-business-plan-async",
                json=payload,
                headers=headers
            )

            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")

            if response.status_code == 422:
                print("[FAILED] Still getting 422 validation error!")
                print("Error details:")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(response.text)
                return False
            elif response.status_code == 202:
                print("[SUCCESS] Got 202 Accepted! Endpoint working correctly.")
                print("Response body:")
                try:
                    print(json.dumps(response.json(), indent=2))
                except:
                    print(response.text)
                return True
            else:
                print(f"[UNEXPECTED] Got status {response.status_code}")
                print(response.text)
                return False

    except Exception as e:
        print(f"Error during test: {e}")
        return False

def main():
    # Start server process
    print("Starting FastAPI server...")
    cwd = "/d/Desktop/New_Flask/FLASK/Server1_FastApi"
    server_proc = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )

    print(f"Server process started (PID: {server_proc.pid})")

    try:
        # Wait for server to start
        print("Waiting 10 seconds for server to be fully ready...")
        time.sleep(10)

        # Run async test
        print("\nRunning endpoint test...")
        result = asyncio.run(test_endpoint())

        sys.exit(0 if result else 1)

    finally:
        # Kill server
        print("\nStoppingserver...")
        try:
            if sys.platform == 'win32':
                os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
            else:
                os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
        except:
            server_proc.terminate()
        server_proc.wait(timeout=5)
        print("Server stopped")

if __name__ == "__main__":
    main()
