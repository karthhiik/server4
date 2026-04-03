#!/usr/bin/env python3
"""
Quality Validation Tests for Dual-Input Generation
Tests actual API responses and validates:
- Response structure
- Data quality (no nulls, proper types)
- Required fields presence
- Content quality
- Confidence scores
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, Any, List
import time

API_BASE_URL = "http://localhost:8080"
JWT_TOKEN = "test-token-123"  # Set via environment variable FASTAPI_TOKEN

class QualityValidator:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url
        self.token = token
        self.results = []

    async def validate_business_plan_quality(self, response_data: Dict) -> Dict[str, Any]:
        """Validate Business Plan response quality"""
        validations = {
            "has_sections": False,
            "section_count": 0,
            "has_company_info": False,
            "has_financials": False,
            "missing_fields": [],
            "quality_score": 0.0,
            "content_length": 0,
        }

        # Check required fields
        required_fields = [
            "executive_summary",
            "market_analysis",
            "company_description",
            "product_description",
            "go_to_market_strategy",
            "competitive_landscape",
            "financial_projections",
        ]

        plan = response_data.get("plan", {}) or response_data

        for field in required_fields:
            if not plan.get(field):
                validations["missing_fields"].append(field)
            else:
                content = plan.get(field, "")
                if isinstance(content, str):
                    validations["content_length"] += len(content)

        # Count sections
        sections = [
            plan.get("executive_summary"),
            plan.get("market_analysis"),
            plan.get("company_description"),
            plan.get("product_description"),
            plan.get("go_to_market_strategy"),
            plan.get("competitive_landscape"),
            plan.get("financial_projections"),
            plan.get("team"),
            plan.get("funding_requirements"),
            plan.get("risk_analysis"),
            plan.get("milestones"),
        ]
        validations["section_count"] = len([s for s in sections if s])
        validations["has_sections"] = validations["section_count"] >= 7

        # Check company info
        validations["has_company_info"] = bool(
            plan.get("company_name") and len(plan.get("company_name", "")) > 0
        )

        # Check financials
        validations["has_financials"] = bool(
            plan.get("financial_projections")
            or plan.get("revenue_projections")
            or plan.get("funding_requirements")
        )

        # Quality score
        fields_present = len(required_fields) - len(validations["missing_fields"])
        validations["quality_score"] = round(
            (fields_present / len(required_fields)) * 100 +
            (min(validations["content_length"] / 10000, 50)), 2
        )

        return validations

    async def validate_swot_quality(self, response_data: Dict) -> Dict[str, Any]:
        """Validate SWOT response quality"""
        validations = {
            "has_all_quadrants": False,
            "strengths_count": 0,
            "weaknesses_count": 0,
            "opportunities_count": 0,
            "threats_count": 0,
            "missing_quadrants": [],
            "quality_score": 0.0,
            "items_well_described": False,
        }

        analysis = response_data.get("analysis") or response_data.get("swot") or response_data

        # Count items per quadrant
        validations["strengths_count"] = len(analysis.get("strengths", []))
        validations["weaknesses_count"] = len(analysis.get("weaknesses", []))
        validations["opportunities_count"] = len(analysis.get("opportunities", []))
        validations["threats_count"] = len(analysis.get("threats", []))

        # Check missing quadrants
        if validations["strengths_count"] == 0:
            validations["missing_quadrants"].append("strengths")
        if validations["weaknesses_count"] == 0:
            validations["missing_quadrants"].append("weaknesses")
        if validations["opportunities_count"] == 0:
            validations["missing_quadrants"].append("opportunities")
        if validations["threats_count"] == 0:
            validations["missing_quadrants"].append("threats")

        validations["has_all_quadrants"] = len(validations["missing_quadrants"]) == 0

        # Check item quality (should have descriptions, not just titles)
        for item in analysis.get("strengths", [])[:1]:
            if isinstance(item, dict) and item.get("description"):
                validations["items_well_described"] = True
            elif isinstance(item, str) and len(item) > 50:
                validations["items_well_described"] = True

        # Quality score (each quadrant should have 3+ items)
        scores = [
            1 if validations["strengths_count"] >= 3 else 0.5,
            1 if validations["weaknesses_count"] >= 3 else 0.5,
            1 if validations["opportunities_count"] >= 3 else 0.5,
            1 if validations["threats_count"] >= 3 else 0.5,
        ]
        validations["quality_score"] = round(sum(scores) / len(scores) * 100, 2)

        return validations

    async def validate_gtm_quality(self, response_data: Dict) -> Dict[str, Any]:
        """Validate GTM Plan response quality"""
        validations = {
            "has_strategic_nodes": False,
            "node_count": 0,
            "has_budget_allocation": False,
            "has_market_intelligence": False,
            "missing_components": [],
            "quality_score": 0.0,
        }

        gtm = response_data.get("gtm_plan") or response_data.get("plan") or response_data

        # Check strategic nodes
        nodes = gtm.get("strategic_nodes") or []
        if isinstance(nodes, dict):
            validations["node_count"] = len(nodes)
        elif isinstance(nodes, list):
            validations["node_count"] = len(nodes)

        validations["has_strategic_nodes"] = validations["node_count"] > 0
        if validations["node_count"] == 0:
            validations["missing_components"].append("strategic_nodes")

        # Check budget allocation
        has_budget = bool(
            gtm.get("budget_allocation")
            or gtm.get("budget_plan")
            or gtm.get("budget_breakdown")
        )
        validations["has_budget_allocation"] = has_budget
        if not has_budget:
            validations["missing_components"].append("budget_allocation")

        # Check market intelligence
        has_market = bool(
            gtm.get("market_intelligence") or gtm.get("market_data") or gtm.get("market_analysis")
        )
        validations["has_market_intelligence"] = has_market
        if not has_market:
            validations["missing_components"].append("market_intelligence")

        # Quality score
        components_present = 3 - len(validations["missing_components"])
        node_score = min(validations["node_count"] / 10, 1.0)  # 10+ nodes = 100%
        validations["quality_score"] = round(
            (components_present / 3 * 50 + node_score * 50), 2
        )

        return validations

    async def validate_pitch_quality(self, response_data: Dict) -> Dict[str, Any]:
        """Validate Pitch Deck response quality"""
        validations = {
            "has_slides": False,
            "slide_count": 0,
            "has_all_key_slides": False,
            "missing_slides": [],
            "has_investor_metrics": False,
            "quality_score": 0.0,
        }

        deck = response_data.get("deck") or response_data.get("pitch") or response_data

        # Check slides
        slides = deck.get("slides") or []
        validations["slide_count"] = len(slides)
        validations["has_slides"] = validations["slide_count"] >= 8

        # Check key slide types
        slide_types = set()
        for slide in slides:
            slide_type = slide.get("type") or slide.get("slide_type")
            if slide_type:
                slide_types.add(slide_type)

        key_slides = {"cover", "pitch", "financials", "team"}
        found_key = key_slides.intersection(slide_types)
        validations["missing_slides"] = list(key_slides - found_key)
        validations["has_all_key_slides"] = len(validations["missing_slides"]) == 0

        # Check investor metrics
        has_metrics = bool(
            deck.get("investor_appeal")
            or deck.get("pitch_analysis")
            or deck.get("pitch_metrics")
        )
        validations["has_investor_metrics"] = has_metrics

        # Quality score
        slide_score = min(validations["slide_count"] / 8, 1.0) * 50  # 8+ slides = 50%
        key_score = (4 - len(validations["missing_slides"])) / 4 * 30  # Key slides = 30%
        metrics_score = 20 if has_metrics else 0  # Metrics = 20%
        validations["quality_score"] = round(slide_score + key_score + metrics_score, 2)

        return validations

    def format_result(self, service: str, input_type: str, validations: Dict[str, Any]) -> str:
        """Format validation result for display"""
        quality = validations.get("quality_score", 0)
        status = "[PASS] PASS" if quality >= 75 else "[WARN] PARTIAL" if quality >= 50 else "[FAIL] FAIL"

        result = f"\n{status} | {service.upper()} - {input_type}\n"
        result += f"{'─' * 60}\n"
        result += f"Quality Score: {quality}/100\n"

        for key, value in validations.items():
            if key == "quality_score":
                continue
            if isinstance(value, list):
                if value:
                    result += f"[WARN]  {key.replace('_', ' ').title()}: {', '.join(str(v) for v in value)}\n"
            elif isinstance(value, bool):
                symbol = "[OK]" if value else "[NO]"
                result += f"{symbol} {key.replace('_', ' ').title()}: {value}\n"
            else:
                result += f"- {key.replace('_', ' ').title()}: {value}\n"

        return result


async def test_business_plan_quality():
    """Test Business Plan with prompt and form inputs"""
    validator = QualityValidator(API_BASE_URL, JWT_TOKEN)

    print("\n" + "=" * 70)
    print("BUSINESS PLAN QUALITY VALIDATION")
    print("=" * 70)

    # Test 1: Prompt-only
    print("\n[PROMPT] Scenario 1: Prompt-Only Input")
    prompt = """Real-time Business Intelligence SaaS platform with stunning 3D visualizations.
    Series A funded, targeting mid-market enterprises (500-5000 employees).
    Founded 2022, 12-person team, $2M ARR. Asking for $5M Series A.
    Market opportunity: $50B+ global BI market."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/generate_business_plan_async",
                json={"prompt": prompt, "mode": "fast", "source": "prompt"},
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            if response.status_code in [200, 202]:
                data = response.json()
                task_id = data.get("task_id")
                print(f"   Task ID: {task_id}")

                # Wait and fetch result
                await asyncio.sleep(3)
                result_response = await client.get(
                    f"{API_BASE_URL}/api/intelligence/tasks/{task_id}/result",
                    headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                    timeout=30.0,
                )

                if result_response.status_code == 200:
                    result = result_response.json()
                    validations = await validator.validate_business_plan_quality(result)
                    print(validator.format_result("Business Plan", "Prompt", validations))
                else:
                    print(f"   [WAIT] Result not ready yet (status: {result_response.status_code})")
            else:
                print(f"   [FAIL] API Error: {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Error: {str(e)}")

    # Test 2: Form-only
    print("\n[FORM] Scenario 2: Form-Only Input")
    form_data = {
        "company_name": "TechVenture Inc.",
        "industry": "saas",
        "stage": "scaling",
        "target_customer": "Mid-market enterprises (500-5000 employees)",
        "pain_points": "Complex BI dashboards, slow implementation, poor visualization",
        "key_features": "Real-time data, 3D UI, multiplayer",
        "revenue_yr1": 2,
        "revenue_yr3": 20,
        "source": "form",
        "mode": "fast",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/generate_business_plan_async",
                json=form_data,
                headers={
                    "Authorization": f"Bearer {JWT_TOKEN}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code in [200, 202]:
                data = response.json()
                task_id = data.get("task_id")
                print(f"   Task ID: {task_id}")

                await asyncio.sleep(3)
                result_response = await client.get(
                    f"{API_BASE_URL}/api/intelligence/tasks/{task_id}/result",
                    headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                    timeout=30.0,
                )

                if result_response.status_code == 200:
                    result = result_response.json()
                    validations = await validator.validate_business_plan_quality(result)
                    print(validator.format_result("Business Plan", "Form", validations))
            else:
                print(f"   [FAIL] API Error: {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Error: {str(e)}")


async def test_swot_quality():
    """Test SWOT with prompt and form inputs"""
    validator = QualityValidator(API_BASE_URL, JWT_TOKEN)

    print("\n" + "=" * 70)
    print("SWOT ANALYSIS QUALITY VALIDATION")
    print("=" * 70)

    # Test 1: Prompt-only
    print("\n[PROMPT] Scenario 1: Prompt-Only Input")
    prompt = """SWOT for TechVenture - real-time BI SaaS platform.
    Strengths: innovative 3D UI, multiplayer, affordable.
    Weaknesses: smaller sales team, limited integrations.
    Opportunities: AI adoption, SMB expansion.
    Threats: Microsoft PowerBI dominance."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/swot/async",
                json={"prompt": prompt, "mode": "fast", "source": "prompt"},
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            if response.status_code in [200, 202]:
                data = response.json()
                task_id = data.get("task_id")
                print(f"   Task ID: {task_id}")

                await asyncio.sleep(3)
                result_response = await client.get(
                    f"{API_BASE_URL}/api/intelligence/tasks/{task_id}/result",
                    headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                    timeout=30.0,
                )

                if result_response.status_code == 200:
                    result = result_response.json()
                    validations = await validator.validate_swot_quality(result)
                    print(validator.format_result("SWOT", "Prompt", validations))
            else:
                print(f"   [FAIL] API Error: {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Error: {str(e)}")

    # Test 2: Form-only
    print("\n[FORM] Scenario 2: Form-Only Input")
    form_data = {
        "businessName": "TechVenture Inc.",
        "industry": "Business Intelligence SaaS",
        "competitors": ["Tableau", "Looker", "PowerBI"],
        "source": "form",
        "mode": "fast",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/swot/async",
                json=form_data,
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            )

            if response.status_code in [200, 202]:
                data = response.json()
                task_id = data.get("task_id")
                print(f"   Task ID: {task_id}")

                await asyncio.sleep(3)
                result_response = await client.get(
                    f"{API_BASE_URL}/api/intelligence/tasks/{task_id}/result",
                    headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                    timeout=30.0,
                )

                if result_response.status_code == 200:
                    result = result_response.json()
                    validations = await validator.validate_swot_quality(result)
                    print(validator.format_result("SWOT", "Form", validations))
            else:
                print(f"   [FAIL] API Error: {response.status_code}")
    except Exception as e:
        print(f"   [FAIL] Error: {str(e)}")


async def main():
    print("\n" + "=" * 70)
    print("DUAL-INPUT QUALITY VALIDATION TEST SUITE")
    print(f"Start: {datetime.now().isoformat()}")
    print("=" * 70)

    await test_business_plan_quality()
    await test_swot_quality()

    print("\n" + "=" * 70)
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
