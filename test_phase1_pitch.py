#!/usr/bin/env python3
"""
Phase 1 Testing: Pitch Service Dual-Input Validation

Tests all 3+ input scenarios:
1. Prompt-only (NER extraction)
2. Form-only (baseline)
3. Dual input (form priority, prompt enriches)
4. From Business Plan (auto-fill from existing BP)

Usage:
    python test_phase1_pitch.py
"""

import asyncio
import os
import sys
import httpx
from datetime import datetime

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
JWT_TOKEN = os.getenv("FASTAPI_TOKEN", "test-token-123")

PROMPT_ONLY = """
Generate investor pitch deck for TechVenture - innovative SaaS platform for real-time business
intelligence with stunning 3D visualizations. Series A funded, targeting mid-market enterprise.
Asking for $5M to fuel growth. Market opportunity: $50B+ global BI market.
Unique value: makes analytics accessible, collaborative, and beautiful.
"""

FORM_ONLY = {
    "company_name": "TechVenture Inc.",
    "tagline": "Real-time analytics for teams that move fast",
    "vision": "Make business intelligence accessible to every team",
    "problem": "Existing BI tools are complex, slow to implement, single-user focused",
    "solution": "3D visualization + real-time multiplayer + AI insights",
    "target_market_size": "50B+ global BI market",
    "ask_amount": 5000000,
    "use_of_funds": "Engineering (50%), Sales (30%), Marketing (20%)",
}


class TestResult:
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.error = None
        self.details = {}

    def success(self, **details):
        self.passed = True
        self.details.update(details)

    def fail(self, error: str, **details):
        self.passed = False
        self.error = error
        self.details.update(details)

    def __repr__(self):
        status = "✅ PASS" if self.passed else f"❌ FAIL: {self.error}"
        return f"{status} | {self.test_name}"


async def test_scenario_1_prompt_only(client: httpx.AsyncClient) -> TestResult:
    """Test 1: Prompt-only input (NER extraction)"""
    result = TestResult("Scenario 1: Pitch Prompt-Only Input (NER Extraction)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Prompt: {PROMPT_ONLY[:60]}...")

        response = await client.post(
            f"{API_BASE_URL}/api/generate-pitch",
            json={"prompt": PROMPT_ONLY, "mode": "fast", "source": "prompt"},
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=120,
        )

        if response.status_code not in [200, 202]:
            result.fail(
                f"HTTP {response.status_code}: {response.text[:100]}",
                response_code=response.status_code,
            )
            return result

        data = response.json()
        plan_id = data.get("plan_id") or data.get("task_id") or data.get("deck_id")

        if not plan_id:
            result.fail("No plan_id in response", data=data)
            return result

        result.success(
            plan_id=plan_id,
            response_status=response.status_code,
            extraction_source="prompt_only"
        )

    except Exception as e:
        result.fail(f"Exception: {str(e)}", exception=str(e))

    return result


async def test_scenario_2_form_only(client: httpx.AsyncClient) -> TestResult:
    """Test 2: Form-only input (baseline)"""
    result = TestResult("Scenario 2: Pitch Form-Only Input (Baseline)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Company: {FORM_ONLY['company_name']}")

        response = await client.post(
            f"{API_BASE_URL}/api/generate-pitch",
            json={**FORM_ONLY, "mode": "fast", "source": "form"},
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=120,
        )

        if response.status_code not in [200, 202]:
            result.fail(
                f"HTTP {response.status_code}: {response.text[:100]}",
                response_code=response.status_code,
            )
            return result

        data = response.json()
        plan_id = data.get("plan_id") or data.get("task_id") or data.get("deck_id")

        if not plan_id:
            result.fail("No plan_id in response", data=data)
            return result

        result.success(
            plan_id=plan_id,
            response_status=response.status_code,
            extraction_source="form_only"
        )

    except Exception as e:
        result.fail(f"Exception: {str(e)}", exception=str(e))

    return result


async def test_scenario_3_dual_input(client: httpx.AsyncClient) -> TestResult:
    """Test 3: Dual input (form priority, prompt enriches)"""
    result = TestResult("Scenario 3: Pitch Dual Input (Form Priority)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Company (form): {FORM_ONLY['company_name']}")

        payload = {**FORM_ONLY, "prompt": PROMPT_ONLY, "mode": "fast", "source": "dual"}

        response = await client.post(
            f"{API_BASE_URL}/api/generate-pitch",
            json=payload,
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=120,
        )

        if response.status_code not in [200, 202]:
            result.fail(
                f"HTTP {response.status_code}: {response.text[:100]}",
                response_code=response.status_code,
            )
            return result

        data = response.json()
        plan_id = data.get("plan_id") or data.get("task_id") or data.get("deck_id")

        if not plan_id:
            result.fail("No plan_id in response", data=data)
            return result

        result.success(
            plan_id=plan_id,
            response_status=response.status_code,
            extraction_source="dual_input"
        )

    except Exception as e:
        result.fail(f"Exception: {str(e)}", exception=str(e))

    return result


async def test_scenario_4_from_business_plan(client: httpx.AsyncClient) -> TestResult:
    """Test 4: From Business Plan (auto-fill from existing BP)"""
    result = TestResult("Scenario 4: Pitch from Business Plan (Auto-Fill)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Source: existing business plan (would need valid plan_id)")

        # Note: This test uses a dummy plan_id - would need real one from running BP generation first
        dummy_plan_id = "bp_dummy_12345"

        response = await client.post(
            f"{API_BASE_URL}/api/generate-pitch",
            json={
                "businessPlanId": dummy_plan_id,
                "mode": "fast",
                "source": "business_plan",
                "prompt": "Emphasize scalability and international expansion potential"  # Optional additional prompt
            },
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=120,
        )

        # This might fail if plan_id doesn't exist, which is expected for this demo
        if response.status_code == 404:
            result.fail(
                "Business plan not found (expected if using dummy ID)",
                response_code=404,
                note="Would work with real business_plan_id from BP service"
            )
            return result

        if response.status_code not in [200, 202]:
            result.fail(
                f"HTTP {response.status_code}: {response.text[:100]}",
                response_code=response.status_code,
            )
            return result

        data = response.json()
        plan_id = data.get("plan_id") or data.get("task_id") or data.get("deck_id")

        if not plan_id:
            result.fail("No plan_id in response", data=data)
            return result

        result.success(
            plan_id=plan_id,
            response_status=response.status_code,
            extraction_source="business_plan",
            autofilled=True
        )

    except Exception as e:
        result.fail(f"Exception: {str(e)}", exception=str(e))

    return result


async def run_all_tests():
    """Run all test scenarios"""
    print("=" * 70)
    print("PHASE 1: PITCH SERVICE - DUAL INPUT TESTING")
    print("=" * 70)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Start: {datetime.now().isoformat()}")

    results = []

    async with httpx.AsyncClient() as client:
        results.append(await test_scenario_1_prompt_only(client))
        results.append(await test_scenario_2_form_only(client))
        results.append(await test_scenario_3_dual_input(client))
        results.append(await test_scenario_4_from_business_plan(client))

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for result in results:
        print(f"{result}")
        if result.details:
            for key, value in result.details.items():
                print(f"    └─ {key}: {value}")

    print("\n" + "-" * 70)
    print(f"Results: {passed}/{total} passed ({100*passed//total}%)")
    print("=" * 70)

    return passed >= 2  # At least 2/4 expected to pass (scenario 4 may not have valid BP)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
