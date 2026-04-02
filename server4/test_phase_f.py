"""Phase F — Slide Generation System Overhaul Tests.

Run: python test_phase_f.py
"""

import asyncio
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch


# ── F1: Model Router ─────────────────────────────────────────────


async def test_model_router_only_working_models():
    """Router only initializes working models."""
    from app.services.llm.model_router import ModelRouter, ROUTING_TABLE

    # Reset singleton
    ModelRouter._instance = None
    router = ModelRouter.get_instance()

    # Should only have working models
    expected_models = {"deepseek-v3", "mistral-medium", "groq", "cf-qwen", "cf-gemma"}
    actual_models = set(router._clients.keys())

    assert expected_models == actual_models, (
        f"Expected {expected_models}, got {actual_models}"
    )

    # All routing chains should only contain working models
    for task_type, chain in ROUTING_TABLE.items():
        for model in chain:
            assert model in expected_models, (
                f"Model '{model}' in routing chain for {task_type} is not initialized"
            )

    print("[PASS] Model router only initializes working models")


async def test_model_routing_fallback_chain():
    """Each task type has at least 2 fallback models."""
    from app.services.llm.model_router import ROUTING_TABLE

    for task_type, chain in ROUTING_TABLE.items():
        assert len(chain) >= 2, (
            f"Task {task_type} has only {len(chain)} model(s), need at least 2"
        )

    print("[PASS] All task types have at least 2 fallback models")


# ── F2: Slide Content Prompts ────────────────────────────────────


async def test_slide_prompts_have_json_schemas():
    """All layout prompts include explicit JSON schema."""
    from app.mcp.brain_mcp.prompts.slide_system import LAYOUT_PROMPTS

    for layout, prompt in LAYOUT_PROMPTS.items():
        assert "JSON Schema:" in prompt or "Return JSON:" in prompt, (
            f"Layout '{layout}' prompt missing JSON schema"
        )
        assert "title" in prompt, f"Layout '{layout}' prompt missing title field"

    print("[PASS] All layout prompts include JSON schemas")


async def test_slide_prompts_have_examples():
    """All layout prompts include examples."""
    from app.mcp.brain_mcp.prompts.slide_system import LAYOUT_PROMPTS

    for layout, prompt in LAYOUT_PROMPTS.items():
        assert "Example:" in prompt, f"Layout '{layout}' prompt missing example"

    print("[PASS] All layout prompts include examples")


async def test_slide_prompts_have_source_requirements():
    """All layout prompts require source attribution (except title/blank)."""
    from app.mcp.brain_mcp.prompts.slide_system import (
        LAYOUT_PROMPTS,
        BASE_SLIDE_SYSTEM,
    )

    assert "source" in BASE_SLIDE_SYSTEM.lower(), (
        "Base slide system missing source attribution requirement"
    )

    # Title-hero, blank, team-grid, quote, timeline don't need source attribution
    layouts_needing_sources = {
        "bullets",
        "bullets-with-image",
        "chart",
        "comparison",
        "kpi-dashboard",
        "two-column",
    }

    for layout in layouts_needing_sources:
        prompt = LAYOUT_PROMPTS.get(layout, "")
        assert "source" in prompt.lower(), (
            f"Layout '{layout}' prompt missing source attribution"
        )

    print("[PASS] All data-driven slide prompts require source attribution")


async def test_slide_prompts_have_fluff_rules():
    """Base slide system includes fluff word restrictions."""
    from app.mcp.brain_mcp.prompts.slide_system import BASE_SLIDE_SYSTEM

    fluff_words = ["revolutionary", "cutting-edge", "game-changing", "paradigm shift"]
    for word in fluff_words:
        assert word in BASE_SLIDE_SYSTEM, (
            f"Base slide system missing fluff word restriction: '{word}'"
        )

    print("[PASS] Base slide system includes fluff word restrictions")


# ── F3: Image Service ────────────────────────────────────────────


async def test_image_service_graceful_fallback():
    """Image service returns None on failure (graceful fallback)."""
    from app.services.image_service import ImageService

    service = ImageService()

    # Mock Lucid to fail
    with patch(
        "app.services.llm.cloudflare_client.create_cf_lucid_client"
    ) as mock_lucid:
        mock_client = MagicMock()
        mock_client.generate_image = AsyncMock(side_effect=Exception("Worker down"))
        mock_lucid.return_value = mock_client

        result = await service.generate_slide_image(
            content={"title": "Test Slide"},
            layout="bullets-with-image",
            theme={"theme_id": "corporate-blue", "colors": {}},
            presentation_id="test_123",
        )

        assert result is None, "Should return None on failure (graceful fallback)"

    print("[PASS] Image service gracefully falls back on failure")


# ── F4: Orchestrator Research Engine Fixes ───────────────────────


async def test_orchestrator_uses_correct_engine_methods():
    """Orchestrator calls correct engine methods."""
    from app.services.orchestrator.orchestrator import PresentationOrchestrator

    # Verify the orchestrator can be instantiated
    mock_db = MagicMock()
    mock_progress = MagicMock()

    # This should not raise any import errors
    orchestrator = PresentationOrchestrator(db=mock_db, progress_tracker=mock_progress)

    # Verify key methods exist
    assert hasattr(orchestrator, "_run_social_engine")
    assert hasattr(orchestrator, "_run_financial_engine")
    assert hasattr(orchestrator, "_run_news_engine")
    assert hasattr(orchestrator, "_run_search_engine")
    assert hasattr(orchestrator, "_generate_slide_images_background")
    assert hasattr(orchestrator, "_dispatch_thumbnail_task")

    print("[PASS] Orchestrator has all required methods")


# ── Test Runner ─────────────────────────────────────────────────


async def run_all():
    tests = [
        # F1: Model Router
        test_model_router_only_working_models,
        test_model_routing_fallback_chain,
        # F2: Slide Content Prompts
        test_slide_prompts_have_json_schemas,
        test_slide_prompts_have_examples,
        test_slide_prompts_have_source_requirements,
        test_slide_prompts_have_fluff_rules,
        # F3: Image Service
        test_image_service_graceful_fallback,
        # F4: Orchestrator
        test_orchestrator_uses_correct_engine_methods,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"[FAIL] {test_fn.__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Phase F Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 60}")

    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all())
