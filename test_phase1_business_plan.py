#!/usr/bin/env python3
"""
Phase 1 Testing: Business Plan Service Dual-Input Validation

Tests all 3 input scenarios:
1. Prompt-only (NER extraction)
2. Form-only (baseline)
3. Dual input (form priority, prompt enriches)

Requirements:
- FastAPI server running on http://localhost:8080
- Valid JWT token in FASTAPI_TOKEN env var

Usage:
    python test_phase1_business_plan.py
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any
import httpx
from datetime import datetime

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
JWT_TOKEN = os.getenv("FASTAPI_TOKEN", "test-token-123")  # Replace with real token

# Test data
PROMPT_ONLY = """
Business plan for TechVenture Inc., a SaaS Business Intelligence platform targeting mid-market
enterprises. Real-time analytics with 3D visualization. Series A funded in 2022.
TAM is approximately $500M with 25% annual growth rate.
Competing against Tableau, Looker, and PowerBI.
"""

FORM_ONLY = {
    "company_name": "TechVenture Inc.",
    "industry": "SaaS - Business Intelligence",
    "stage": "Series A",
    "founded_year": 2022,
    "target_customer": "Mid-market enterprises (500-5000 employees)",
    "pain_points": "Lack of real-time analytics, complex implementation, single-user limitation",
    "market_size_indicator": 500,
    "key_features": "Real-time dashboards, AI insights, 3D visualization, multiplayer collaboration",
    "differentiation": "3D visualization UI, real-time multiplayer, affordable pricing",
    "pricing_model": "Per-seat SaaS with usage-based tier",
    "tam": 500,
    "sam": 50,
    "som": 5,
    "growth_rate": 25,
    "revenue_streams": "Subscriptions, premium features, enterprise support",
    "cac": 1500,
    "ltv": 15000,
    "unit_economics": "LTV:CAC = 10:1",
    "channels": "Sales-led, product-led, partnerships",
    "launch_timeline": "Q3 2026",
    "customer_acquisition_plan": "Enterprise sales team + product demos",
    "direct_competitors": "Tableau, Looker, PowerBI",
    "positioning": "Open, collaborative BI platform",
    "advantages": "3D UI, real-time multiplayer, affordable",
    "revenue_yr1": 500000,
    "revenue_yr3": 5000000,
    "burn_rate": 50000,
    "breakeven_timeline": "24 months",
}


class TestResult:
    """Test result tracker"""

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
    result = TestResult("Scenario 1: Prompt-Only Input (NER Extraction)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Prompt: {PROMPT_ONLY[:60]}...")

        response = await client.post(
            f"{API_BASE_URL}/api/generate-business-plan",
            json={"prompt": PROMPT_ONLY, "mode": "fast"},
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=120,
        )

        if response.status_code != 200:
            result.fail(
                f"HTTP {response.status_code}: {response.text}",
                response_code=response.status_code,
            )
            return result

        data = response.json()

        # Validate response structure
        if not data.get("success"):
            result.fail("Response indicates failure", data=data)
            return result

        plan = data.get("plan", {})
        plan_id = data.get("plan_id")

        # Check extracted company name from prompt
        extracted_company = plan.get("company_name")
        if "TechVenture" not in extracted_company and "techventure" not in extracted_company.lower():
            result.fail(f"Company name not extracted correctly: {extracted_company}")
            return result

        # Check sections generated
        sections = plan.get("sections", {})
        if len(sections) < 10:
            result.fail(
                f"Not enough sections generated: {len(sections)}/13",
                sections_count=len(sections),
            )
            return result

        # Check metrics extracted
        metrics = plan.get("key_metrics", {})
        if not metrics.get("tam"):
            result.fail("TAM not extracted from prompt")
            return result

        result.success(
            plan_id=plan_id,
            company_name=extracted_company,
            sections_count=len(sections),
            tam_extracted=metrics.get("tam"),
            extraction_quality=plan.get("_extraction_source", "medium")
        )

    except Exception as e:
        result.fail(f"Exception: {str(e)}", exception=str(e))

    return result


async def test_scenario_2_form_only(client: httpx.AsyncClient) -> TestResult:
    """Test 2: Form-only input (baseline)"""
    result = TestResult("Scenario 2: Form-Only Input (Baseline)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Company: {FORM_ONLY['company_name']}")

        response = await client.post(
            f"{API_BASE_URL}/api/generate-business-plan",
            json={"form_input": FORM_ONLY, "mode": "fast"},
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=120,
        )

        if response.status_code != 200:
            result.fail(
                f"HTTP {response.status_code}: {response.text}",
                response_code=response.status_code,
            )
            return result

        data = response.json()

        if not data.get("success"):
            result.fail("Response indicates failure", data=data)
            return result

        plan = data.get("plan", {})
        plan_id = data.get("plan_id")

        # Check company name matches form input
        if plan.get("company_name") != FORM_ONLY["company_name"]:
            result.fail(f"Company name mismatch: {plan.get('company_name')}")
            return result

        # Check sections
        sections = plan.get("sections", {})
        if len(sections) < 10:
            result.fail(
                f"Not enough sections generated: {len(sections)}/13",
                sections_count=len(sections),
            )
            return result

        # Check metrics
        metrics = plan.get("key_metrics", {})
        if metrics.get("tam") != FORM_ONLY["tam"]:
            result.fail(
                f"TAM mismatch: {metrics.get('tam')} vs {FORM_ONLY['tam']}"
            )
            return result

        result.success(
            plan_id=plan_id,
            company_name=plan.get("company_name"),
            sections_count=len(sections),
            tam_value=metrics.get("tam"),
            source="form_only"
        )

    except Exception as e:
        result.fail(f"Exception: {str(e)}", exception=str(e))

    return result


async def test_scenario_3_dual_input(client: httpx.AsyncClient) -> TestResult:
    """Test 3: Dual input (form priority, prompt enriches)"""
    result = TestResult("Scenario 3: Dual Input (Form Priority, Prompt Enriches)")

    try:
        print(f"\n📝 {result.test_name}")
        print(f"   Company (form): {FORM_ONLY['company_name']}")
        print(f"   Prompt: {PROMPT_ONLY[:40]}...")

        response = await client.post(
            f"{API_BASE_URL}/api/generate-business-plan",
            json={"form_input": FORM_ONLY, "prompt": PROMPT_ONLY, "mode": "fast"},
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=120,
        )

        if response.status_code != 200:
            result.fail(
                f"HTTP {response.status_code}: {response.text}",
                response_code=response.status_code,
            )
            return result

        data = response.json()

        if not data.get("success"):
            result.fail("Response indicates failure", data=data)
            return result

        plan = data.get("plan", {})
        plan_id = data.get("plan_id")

        # Verify form data takes priority
        if plan.get("company_name") != FORM_ONLY["company_name"]:
            result.fail(f"Form priority not respected: {plan.get('company_name')}")
            return result

        # Check TAM from form (not prompt)
        metrics = plan.get("key_metrics", {})
        if metrics.get("tam") != FORM_ONLY["tam"]:
            result.fail(f"Form TAM not used: {metrics.get('tam')}")
            return result

        # Check sections
        sections = plan.get("sections", {})
        if len(sections) < 10:
            result.fail(
                f"Not enough sections: {len(sections)}/13",
                sections_count=len(sections),
            )
            return result

        result.success(
            plan_id=plan_id,
            company_name=plan.get("company_name"),
            sections_count=len(sections),
            tam_value=metrics.get("tam"),
            form_priority_respected=True,
            source="dual_input"
        )

    except Exception as e:
        result.fail(f"Exception: {str(e)}", exception=str(e))

    return result


async def run_all_tests():
    """Run all test scenarios"""
    print("=" * 70)
    print("PHASE 1: BUSINESS PLAN SERVICE - DUAL INPUT TESTING")
    print("=" * 70)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Start: {datetime.now().isoformat()}")

    results = []

    async with httpx.AsyncClient() as client:
        # Test 1: Prompt-only
        try:
            result1 = await test_scenario_1_prompt_only(client)
            results.append(result1)
        except Exception as e:
            print(f"❌ Test 1 failed with exception: {e}")
            results.append(TestResult("Scenario 1: Prompt-Only Input").fail(str(e)))

        # Test 2: Form-only
        try:
            result2 = await test_scenario_2_form_only(client)
            results.append(result2)
        except Exception as e:
            print(f"❌ Test 2 failed with exception: {e}")
            results.append(TestResult("Scenario 2: Form-Only Input").fail(str(e)))

        # Test 3: Dual input
        try:
            result3 = await test_scenario_3_dual_input(client)
            results.append(result3)
        except Exception as e:
            print(f"❌ Test 3 failed with exception: {e}")
            results.append(TestResult("Scenario 3: Dual Input").fail(str(e)))

    # Print summary
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
    print(f"Test End: {datetime.now().isoformat()}")
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
