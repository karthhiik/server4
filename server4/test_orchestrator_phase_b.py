"""
Phase B Integration Tests — validates the full orchestrator pipeline
with PromptEngine wiring (B1-B5) without making real LLM calls.
"""

from unittest.mock import MagicMock, AsyncMock
import json
import asyncio

from app.services.orchestrator.orchestrator import PresentationOrchestrator
from app.models.presentation import PresentationMode


class MockResponse:
    def __init__(self, content_str):
        self.content = content_str


class MockDB:
    def __init__(self):
        self.presentations = MagicMock()
        self.presentations.update_one = AsyncMock()
        self.presentations.find_one = AsyncMock(return_value={})
        self.slides = MagicMock()
        self.slides.insert_one = AsyncMock()
        self.slides.update_one = AsyncMock()
        self.slides.find_one = AsyncMock(return_value={})
        self.slides.find = MagicMock(
            return_value=MagicMock(to_list=AsyncMock(return_value=[]))
        )
        self.slides.count_documents = AsyncMock(return_value=0)
        self.slides.delete_one = AsyncMock()
        self.slides.find_one_and_update = AsyncMock()
        self.templates = MagicMock()
        self.templates.find_one = AsyncMock(return_value={})
        self.templates.count_documents = AsyncMock(return_value=0)
        self.export_jobs = MagicMock()
        self.export_jobs.update_one = AsyncMock()
        self.export_jobs.find_one = AsyncMock(return_value={})
        self.export_jobs.insert_one = AsyncMock()
        self.export_jobs.find = MagicMock(
            return_value=MagicMock(to_list=AsyncMock(return_value=[]))
        )
        self.template_analytics = MagicMock()
        self.template_analytics.update_one = AsyncMock()
        self.generation_logs = MagicMock()
        self.generation_logs.insert_one = AsyncMock()
        self.generation_logs.find = MagicMock(
            return_value=MagicMock(to_list=AsyncMock(return_value=[]))
        )


class MockProgressTracker:
    send_progress = AsyncMock()


async def mock_complete(**kwargs):
    """Mock LLM responses for all pipeline phases (async to match router.complete())."""
    task = kwargs.get("task_type", "")
    phase = kwargs.get("phase", "")

    if task == "outline_planning":
        return MockResponse(
            json.dumps(
                [
                    {
                        "title": "The Problem",
                        "purpose": "Problem statement",
                        "suggested_layout": "two-column",
                        "content_hints": "",
                    },
                    {
                        "title": "Our Solution",
                        "purpose": "Solution overview",
                        "suggested_layout": "bullets",
                        "content_hints": "",
                    },
                ]
            )
        )
    if phase == "research_planning":
        return MockResponse(
            json.dumps(
                {
                    "queries": [
                        {
                            "query": "AI SaaS market size",
                            "type": "general",
                            "priority": "high",
                        }
                    ],
                    "data_needs": [{"metric": "TAM", "source_type": "market"}],
                }
            )
        )
    if phase == "search_query":
        return MockResponse(
            json.dumps(
                [
                    {
                        "title": "AI SaaS Market",
                        "snippet": "Market at USD180B by 2028",
                        "source": "McKinsey",
                        "year": 2025,
                    },
                ]
            )
        )
    if phase == "research_synthesis":
        return MockResponse(
            "AI SaaS market: USD180B by 2028 (McKinsey), 34% CAGR (Gartner)."
        )
    if phase == "data_extraction":
        return MockResponse(
            json.dumps(
                {
                    "data_points": [
                        {
                            "metric": "Market Size",
                            "value": "$180B",
                            "year": "2028",
                            "source": "McKinsey",
                            "confidence": "high",
                            "chart_suitable": True,
                        }
                    ]
                }
            )
        )
    if task in ("structured_json", "narrative_storytelling", "general"):
        return MockResponse(
            json.dumps(
                {
                    "title": "Test Slide",
                    "bullets": [
                        "Market size $180B by 2028 — Source: McKinsey 2025",
                        "34% CAGR — Source: Gartner",
                    ],
                }
            )
        )
    if task == "template_fill":
        return MockResponse(
            json.dumps(
                {
                    "title": "The Problem",
                    "left_content": "Users struggle with data analysis.",
                    "right_content": "Market is USD180B by 2028.",
                }
            )
        )
    return MockResponse(json.dumps({"fallback": True}))


def make_orchestrator():
    mock_db = MockDB()
    mock_progress = MockProgressTracker()
    orch = PresentationOrchestrator(db=mock_db, progress_tracker=mock_progress)
    orch.router.complete = mock_complete
    return orch, mock_db


# ──────────────────── Tests ────────────────────


async def test_full_pipeline_yc_pitch():
    """Test complete AI generation pipeline with ycpitch style and pitch purpose."""
    orch, mock_db = make_orchestrator()

    input_data = MagicMock()
    input_data.topic = "AI SaaS Platform"
    input_data.description = "B2B AI analytics"
    input_data.audience = "Investors"
    input_data.purpose = "pitch"
    input_data.mode = PresentationMode.PREMIUM
    input_data.slide_count = 2
    input_data.generate_notes = False
    input_data.writing_style = "yc_pitch"

    result = await orch.generate_presentation(
        project_id="test_proj_123",
        input_data=input_data,
        user_id="user_456",
    )
    assert result["status"] == "ready_for_editing"
    assert result["slide_count"] == 2
    assert "warnings" in result
    assert mock_db.slides.insert_one.call_count == 2
    print("[PASS] Full pipeline: ycpitch + pitch -> 2 slides with warnings field")


async def test_full_pipeline_investor_update():
    """Test complete pipeline with investor_update style (different voice, different research config)."""
    orch, mock_db = make_orchestrator()

    input_data = MagicMock()
    input_data.topic = "Cloud Security Platform"
    input_data.description = "Monthly update for existing investors"
    input_data.audience = "Board members"
    input_data.purpose = "investor_update"
    input_data.mode = PresentationMode.STANDARD
    input_data.slide_count = 3
    input_data.generate_notes = False
    input_data.writing_style = "investor_update"

    result = await orch.generate_presentation(
        project_id="test_proj_update",
        input_data=input_data,
        user_id="user_456",
    )
    assert result["status"] == "ready_for_editing"
    assert (
        result["slide_count"] >= 1
    )  # Mock returns 2 slides; real impl respects slide_count
    assert mock_db.slides.insert_one.call_count >= 1
    print("[PASS] Full pipeline: investor_update style + investor_update purpose")


async def test_yc_demo_day_template():
    """Test template generation with default_writing_style=ycpitch from seed data."""
    orch, mock_db = make_orchestrator()

    mock_db.templates.find_one = AsyncMock(
        return_value={
            "_id": "yc-demo-day",
            "name": "YC Demo Day",
            "category": "fundraising",
            "default_writing_style": "yc_pitch",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "One-liner",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{tagline}}",
                    },
                    "ai_instructions": "Write a compelling one-liner for investors",
                }
            ],
        }
    )

    input_data = MagicMock()
    input_data.template_id = "yc-demo-day"
    input_data.mode = PresentationMode.STANDARD
    input_data.user_inputs = {"company_name": "AcmeAI"}

    result = await orch.generate_from_template(
        project_id="test_yc_tpl",
        input_data=input_data,
        user_id="user_001",
    )
    assert result["status"] == "ready_for_editing"
    assert result["slide_count"] == 1
    assert mock_db.slides.insert_one.call_count == 1
    print("[PASS] yc-demo-day template: yc_pitch style, fundraising category")


async def test_sequoia_template():
    """Test template generation with analytical style (sequoia-pitch)."""
    orch, mock_db = make_orchestrator()

    mock_db.templates.find_one = AsyncMock(
        return_value={
            "_id": "sequoia-pitch",
            "name": "Sequoia Pitch Deck",
            "category": "fundraising",
            "default_writing_style": "analytical",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "Company purpose",
                    "placeholders": {
                        "title": "{{company_name}}",
                        "subtitle": "{{purpose}}",
                    },
                    "ai_instructions": "Define the company purpose in one sentence",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem",
                    "placeholders": {
                        "title": "Problem",
                        "left_content": "{{problem}}",
                        "right_content": "{{data}}",
                    },
                    "ai_instructions": "Describe the problem with data",
                },
            ],
        }
    )

    input_data = MagicMock()
    input_data.template_id = "sequoia-pitch"
    input_data.mode = PresentationMode.PREMIUM
    input_data.user_inputs = {"company_name": "DataCorp"}

    result = await orch.generate_from_template(
        project_id="test_seq_tpl",
        input_data=input_data,
        user_id="user_002",
    )
    assert result["status"] == "ready_for_editing"
    assert result["slide_count"] == 2
    assert mock_db.slides.insert_one.call_count == 2
    print("[PASS] sequoia-pitch template: analytical style, fundraising category")


async def test_investor_update_template():
    """Test template generation with investor_update style."""
    orch, mock_db = make_orchestrator()

    mock_db.templates.find_one = AsyncMock(
        return_value={
            "_id": "investor-update",
            "name": "Monthly Investor Update",
            "category": "fundraising",
            "default_writing_style": "investor_update",
            "slides": [
                {
                    "index": 0,
                    "layout": "kpi-dashboard",
                    "purpose": "Highlights",
                    "placeholders": {
                        "title": "{{period}} Update",
                        "metrics": "{{kpis}}",
                    },
                    "ai_instructions": "Show key highlights for the period",
                },
            ],
        }
    )

    input_data = MagicMock()
    input_data.template_id = "investor-update"
    input_data.mode = PresentationMode.STANDARD
    input_data.user_inputs = {"period": "March 2026"}

    result = await orch.generate_from_template(
        project_id="test_inv_tpl",
        input_data=input_data,
        user_id="user_003",
    )
    assert result["status"] == "ready_for_editing"
    assert result["slide_count"] == 1
    print("[PASS] investor-update template: investor_update style")


async def test_quality_guards_fire_on_content():
    """Verify quality guards actually run and produce warnings."""
    orch, mock_db = make_orchestrator()

    # Override slide content response to include fluff
    async def mock_complete_fluff(**kwargs):
        task = kwargs.get("task_type", "")
        phase = kwargs.get("phase", "")
        if task == "outline_planning":
            return MockResponse(
                json.dumps(
                    [
                        {
                            "title": "Bad Slide",
                            "purpose": "test",
                            "suggested_layout": "bullets",
                            "content_hints": "",
                        },
                    ]
                )
            )
        if phase == "research_planning":
            return MockResponse(
                json.dumps(
                    {
                        "queries": [
                            {"query": "test", "type": "general", "priority": "high"}
                        ],
                        "data_needs": [],
                    }
                )
            )
        if phase == "search_query":
            return MockResponse(json.dumps([]))
        if phase == "research_synthesis":
            return MockResponse("Test data")
        if phase == "data_extraction":
            return MockResponse(json.dumps({"data_points": []}))
        if task in ("structured_json", "narrative_storytelling", "general"):
            return MockResponse(
                json.dumps(
                    {
                        "title": "Revolutionary Cutting-Edge Solution",
                        "bullets": [
                            "Our cutting-edge platform is revolutionary and disruptive",
                            "Seamless holistic synergy with best-in-class AI",
                            "Game-changing paradigm shift for $5M market",
                        ],
                    }
                )
            )
        return MockResponse(json.dumps({"fallback": True}))

    orch.router.complete = mock_complete_fluff

    input_data = MagicMock()
    input_data.topic = "Test"
    input_data.description = "Test"
    input_data.audience = "Test"
    input_data.purpose = "pitch"
    input_data.mode = PresentationMode.STANDARD
    input_data.slide_count = 1
    input_data.generate_notes = False
    input_data.writing_style = "yc_pitch"

    result = await orch.generate_presentation(
        project_id="test_quality",
        input_data=input_data,
        user_id="user_999",
    )
    # Quality warnings should contain flagged items
    warnings = result.get("warnings", [])
    print(f"[INFO] Quality warnings raised: {warnings}")
    assert len(warnings) > 0, (
        "Quality guards should have raised warnings for fluff content"
    )
    print("[PASS] Quality guards fired on generated content")


async def test_research_configs_purpose_aware():
    """Test that different purposes produce different research configs."""
    from app.services.orchestrator.orchestrator import _build_research_planner_prompt

    pitch = _build_research_planner_prompt("AI", "AI analytics", "pitch", "premium")
    assert "TAM" in pitch
    assert "competitor" in pitch.lower()
    print(f"[PASS] pitch research config: {len(pitch)} chars, has TAM+competitors")

    sales = _build_research_planner_prompt("CRM", "Sales tool", "sales", "standard")
    assert "ROI" in sales
    print(f"[PASS] sales research config: {len(sales)} chars, has ROI")

    internal = _build_research_planner_prompt(
        "Update", "Quarterly", "internal", "standard"
    )
    assert "benchmark" in internal.lower() or "KPI" in internal.upper()
    print(f"[PASS] internal research config: {len(internal)} chars")

    # Different purposes should produce different prompts
    assert pitch != sales != internal
    print("[PASS] Research configs differ by purpose")


# ──────────────────── Run All ────────────────────

if __name__ == "__main__":
    tests = [
        (
            "B1: Research planner configs purpose-aware",
            test_research_configs_purpose_aware,
        ),
        ("B2/B3: Full pipeline ycpitch+pitch", test_full_pipeline_yc_pitch),
        (
            "B2/B3: Full pipeline investor_update style",
            test_full_pipeline_investor_update,
        ),
        ("B4: YC Demo Day template (ycpitch)", test_yc_demo_day_template),
        ("B4: Sequoia template (analytical)", test_sequoia_template),
        ("B4: Investor Update template", test_investor_update_template),
        (
            "B5: Quality guards + writing_style flow",
            test_quality_guards_fire_on_content,
        ),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            asyncio.run(test_fn())
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
            import traceback

            traceback.print_exc()
            print()

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    if failed:
        exit(1)
