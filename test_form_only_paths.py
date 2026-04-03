#!/usr/bin/env python3
"""
Test Form-Only Generation Paths
These SHOULD work since all form fields are provided
"""

import asyncio
import json
import httpx

API_BASE_URL = "http://localhost:8080"
JWT_TOKEN = "test-token-123"

async def test_business_plan_form():
    """Test Business Plan form-only (should work)"""
    print("\n[TEST] Business Plan - Form-Only Path")
    print("-" * 60)

    form_data = {
        "form_input": {
            "company_name": "TechVenture Inc.",
            "industry": "SaaS",
            "stage": "Series A",
            "founded_year": 2022,
            "target_customer": "Mid-market enterprises",
            "pain_points": "Complex dashboards, slow updates",
            "market_size_indicator": 50000.0,
            "key_features": "Real-time,  3D UI, multiplayer",
            "differentiation": "Best-in-class visualization",
            "pricing_model": "$10K-50K per month",
            "tam": 50000.0,
            "sam": 5000.0,
            "som": 500.0,
            "growth_rate": 0.45,
            "revenue_streams": "Subscription + enterprise",
            "cac": 5000.0,
            "ltv": 100000.0,
            "unit_economics": "3:1 LTV:CAC ratio",
            "channels": "Direct sales, partnerships",
            "launch_timeline": "Q3 2026",
            "customer_acquisition_plan": "Enterprise sales team",
            "direct_competitors": "Tableau, Looker, PowerBI",
            "positioning": "3D visualization innovator",
            "advantages": "Best UX, affordable, multiplayer",
            "revenue_yr1": 5.0,
            "revenue_yr3": 50.0,
            "burn_rate": 100.0,
            "breakeven_timeline": "18 months",
        },
        "mode": "deep",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/generate-business-plan-async",
                json=form_data,
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            print(f"Status: {response.status_code}")

            if response.status_code in [200, 202]:
                data = response.json()
                print("[OK] PASS - Task created successfully!")
                print(f"Response: {json.dumps(data, indent=2)}")
                return True
            else:
                error_data = response.json()
                print(f"[FAIL] Status {response.status_code}")
                print(f"Errors: {json.dumps(error_data, indent=2)}")
                return False

    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_swot_form():
    """Test SWOT form-only (should work)"""
    print("\n[TEST] SWOT Analysis - Form-Only Path")
    print("-" * 60)

    form_data = {
        "businessName": "TechVenture Inc.",
        "industry": "SaaS - Business Intelligence",
        "businessDescription": "Real-time BI platform with 3D visualization",
        "targetMarket": "Mid-market enterprise (500-5000 employees)",
        "competitors": ["Tableau", "Looker", "PowerBI"],
        "strengths": "3D visualization, multiplayer, affordable",
        "weaknesses": "Smaller sales team, limited integrations",
        "opportunities": "AI adoption, SMB expansion, M&A targets",
        "threats": "Microsoft dominance, competitive pricing",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/swot/async",
                json=form_data,
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            print(f"Status: {response.status_code}")

            if response.status_code in [200, 202]:
                data = response.json()
                print("[OK] PASS - Task created successfully!")
                print(f"Response: {json.dumps(data, indent=2)}")
                return True
            else:
                error_data = response.json()
                print(f"[FAIL] Status {response.status_code}")
                print(f"Errors: {json.dumps(error_data, indent=2)}")
                return False

    except Exception as e:
        print(f"[FAIL] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 70)
    print("FORM-ONLY GENERATION TEST")
    print("Testing form inputs that should work (all fields provided)")
    print("=" * 70)

    results = []
    results.append(("Business Plan Form", await test_business_plan_form()))
    results.append(("SWOT Form", await test_swot_form()))

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")

    passed = sum(1 for _, p in results if p)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")


if __name__ == "__main__":
    asyncio.run(main())
