#!/usr/bin/env python3
"""
Direct test of prompt-only endpoint
Tests if the Optional fields are working
"""

import httpx
import json
import asyncio

API_BASE_URL = "http://localhost:8080"
JWT_TOKEN = "test-token-123"

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test Business Plan with ONLY prompt (correct format for new JSON endpoint)
        payload = {
            "prompt": "Create a business plan for a B2B SaaS startup in AI/ML space",
            "research_mode": "deep"
            # business_name, industry, business_type, vision are omitted (Optional)
        }

        print("Testing: POST /api/generate-business-plan-async")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = await client.post(
            f"{API_BASE_URL}/api/generate-business-plan-async",
            json=payload,
            headers={
                "Authorization": f"Bearer {JWT_TOKEN}",
                "Content-Type": "application/json"
            }
        )

        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text[:500]}")

        if response.status_code in [200, 202]:
            print("\n[SUCCESS] Endpoint accepted prompt-only request!")
            try:
                data = response.json()
                print(f"Plan ID: {data.get('plan_id')}")
            except:
                pass
        else:
            print("\n[FAILED] Endpoint rejected request")
            try:
                error = response.json()
                if 'detail' in error:
                    print(f"Error details: {json.dumps(error['detail'], indent=2)}")
            except:
                print(f"Raw response: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
