#!/usr/bin/env python3
"""
Phase 1 Testing: SWOT Service Dual-Input Validation

Tests all 3 input scenarios:
1. Prompt-only (NER extraction)
2. Form-only (baseline)
3. Dual input (form priority, prompt enriches)

Usage:
    python test_phase1_swot.py
"""

import asyncio
import os
import sys
from typing import Dict, Any
import httpx
from datetime import datetime

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
JWT_TOKEN = os.getenv("FASTAPI_TOKEN", "test-token-123")

PROMPT_ONLY = """
SWOT analysis for TechVenture - a real-time Business Intelligence platform with 3D visualization
features. Competing against Tableau, Looker, and PowerBI in the mid-market enterprise segment.
Platform targets CIOs and data engineers looking for collaborative, easy-to-implement solutions.
Founded 2022, Series A funded.
"""

FORM_ONLY = {
    "businessName": "TechVenture Inc.",
    "industry": "Business Intelligence SaaS",
    "businessDescription": "Real-time analytics platform with 3D visualization and multiplayer collaboration",
    "targetMarket": "Mid-market enterprise (500-5000 employees)",
    "competitors": ["Tableau", "Looker", "PowerBI"],
    "strengths": "3D UI innovation, real-time multiplayer, affordable pricing",
    "weaknesses": "Limited integration ecosystem, smaller sales team",
    "opportunities": "Market consolidation, AI/ML adoption, SMB expansion",
    "threats": "Microsoft PowerBI dominance, competitive pricing pressure",
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
    result = TestResult("Scenario 1: SWOT Prompt-Only Input (NER Extraction)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Prompt: {PROMPT_ONLY[:60]}...")

        response = await client.post(
            f"{API_BASE_URL}/api/swot/async",
            json={"prompt": PROMPT_ONLY},
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
        plan_id = data.get("plan_id") or data.get("task_id")

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
    result = TestResult("Scenario 2: SWOT Form-Only Input (Baseline)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Business: {FORM_ONLY['businessName']}")

        response = await client.post(
            f"{API_BASE_URL}/api/swot/async",
            json=FORM_ONLY,
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
        plan_id = data.get("plan_id") or data.get("task_id")

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
    result = TestResult("Scenario 3: SWOT Dual Input (Form Priority)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Business (form): {FORM_ONLY['businessName']}")

        payload = {**FORM_ONLY, "prompt": PROMPT_ONLY}

        response = await client.post(
            f"{API_BASE_URL}/api/swot/async",
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
        plan_id = data.get("plan_id") or data.get("task_id")

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


async def run_all_tests():
    """Run all test scenarios"""
    print("=" * 70)
    print("PHASE 1: SWOT SERVICE - DUAL INPUT TESTING")
    print("=" * 70)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Start: {datetime.now().isoformat()}")

    results = []

    async with httpx.AsyncClient() as client:
        results.append(await test_scenario_1_prompt_only(client))
        results.append(await test_scenario_2_form_only(client))
        results.append(await test_scenario_3_dual_input(client))

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

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
