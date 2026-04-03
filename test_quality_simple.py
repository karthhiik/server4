#!/usr/bin/env python3
"""
Working Quality Validation Tests
Testing actual API with correct payload formats
"""

import asyncio
import json
import httpx
import sys

API_BASE_URL = "http://localhost:8080"
JWT_TOKEN = "test-token-123"

async def test_business_plan_prompt():
    """Test Business Plan prompt-only path"""
    print("\n[TEST] Business Plan - Prompt Path")
    print("-" * 60)

    prompt = "Real-time BI SaaS with 3D visualization. Series A, $2M ARR, asking $5M. Market: $50B+"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Send with null form_input
            payload = {
                "form_input": None,
                "prompt": prompt,
                "mode": "deep",
            }

            print(f"Sending: {json.dumps(payload, indent=2)}")

            response = await client.post(
                f"{API_BASE_URL}/api/generate-business-plan-async",
                json=payload,
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            print(f"Status: {response.status_code}")

            if response.status_code in [200, 202]:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")

                task_id = data.get("plan_id") or data.get("task_id")
                if task_id:
                    print(f"[OK] Task ID received: {task_id}")
                    return True
            else:
                error_data = response.json()
                print(f"[FAIL] Error: {json.dumps(error_data, indent=2)}")
                return False

    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_swot_prompt():
    """Test SWOT prompt-only path"""
    print("\n[TEST] SWOT - Prompt Path")
    print("-" * 60)

    prompt = "SWOT for BI SaaS startup. Strengths: innovation, UI. Weaknesses: small team. Opportunities: AI. Threats: Microsoft."

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "prompt": prompt,
                "source": "prompt",
                "mode": "deep",
            }

            print(f"Sending: {json.dumps(payload, indent=2)}")

            response = await client.post(
                f"{API_BASE_URL}/api/swot/async",
                json=payload,
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            print(f"Status: {response.status_code}")

            if response.status_code in [200, 202]:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")

                task_id = data.get("plan_id") or data.get("task_id")
                if task_id:
                    print(f"[OK] Task ID received: {task_id}")
                    return True
            else:
                error_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
                print(f"[FAIL] Error: {json.dumps(error_data, indent=2) if isinstance(error_data, dict) else error_data}")
                return False

    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_gtm_prompt():
    """Test GTM prompt-only path"""
    print("\n[TEST] GTM - Prompt Path")
    print("-" * 60)

    prompt = "GTM for BI SaaS: 100-day aggressive launch, $50K/month budget, 8 people, Q3 2026 in NA. Target CIOs."

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            form_data = {
                "prompt": prompt,
                "mode": "deep",
                "source": "prompt",
            }

            print(f"  Payload: {json.dumps(form_data, indent=2)}")

            response = await client.post(
                f"{API_BASE_URL}/generate_gtm_plan_async",
                json=form_data,
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            print(f"Status: {response.status_code}")

            if response.status_code in [200, 202]:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")

                task_id = data.get("plan_id") or data.get("task_id")
                if task_id:
                    print(f"[OK] Task ID received: {task_id}")
                    return True
            else:
                try:
                    error_data = response.json()
                    print(f"[FAIL] Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"[FAIL] Error: {response.text[:200]}")
                return False

    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 70)
    print("QUALITY VALIDATION - DUAL-INPUT API TESTS")
    print("=" * 70)

    results = []

    print("\nTesting prompt-based generation paths...")
    results.append(("Business Plan", await test_business_plan_prompt()))
    results.append(("SWOT", await test_swot_prompt()))
    results.append(("GTM", await test_gtm_prompt()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for service, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {service}")

    passed = sum(1 for _, p in results if p)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
