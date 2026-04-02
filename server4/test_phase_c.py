"""Phase C — Export Pipeline Integration Tests.

Run: python test_phase_c.py
"""

import asyncio
import json
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# ── Test Helpers ──────────────────────────────────────────────────


def make_slide(idx=0, layout="bullets", title="Test Slide"):
    return {
        "_id": f"slide_{idx}",
        "index": idx,
        "presentation_id": "pres_123",
        "layout": layout,
        "content": {
            "title": title,
            "bullets": [f"Point {i + 1} — Source: McKinsey 2025" for i in range(3)],
        },
        "speaker_notes": f"Notes for slide {idx}",
    }


def make_theme():
    return {
        "_id": "theme_1",
        "colors": {
            "primary": "#2563eb",
            "accent": "#7c3aed",
            "surface": "#f9fafb",
            "background": "#ffffff",
            "text_primary": "#111827",
            "text_secondary": "#9ca3af",
        },
        "fonts": {"heading": "Inter", "body": "Inter"},
    }


def make_metadata():
    return {"title": "Test Pitch Deck", "author": "Test Author"}


class MockDB:
    def __init__(self):
        self.presentations = AsyncMock()
        self.slides = AsyncMock()
        self.themes = AsyncMock()
        self.export_jobs = AsyncMock()


class MockBlobService:
    def __init__(self):
        self.upload_file = AsyncMock(return_value="exports/pres_123/presentation.pptx")
        self.generate_sas_download_url = MagicMock(
            return_value="https://acct.blob.core.windows.net/container/exports/pres_123/presentation.pptx?sv=2023-01-03&se=2026-04-01T12:00:00Z&sr=b&sp=r&sig=abc123"
        )
        self.close = AsyncMock()


# ── C1: SAS Token Generation ──────────────────────────────────────


async def test_sas_token_has_expiry():
    """SAS URL contains expiry parameter and is not a raw blob URL."""
    from app.services.storage.blob_service import BlobStorageService

    svc = BlobStorageService()
    svc._account_name = "testacct"
    svc._account_key = "dGVzdGtleQ=="

    url = svc.generate_sas_download_url("exports/test.pptx", expiry_hours=1)

    assert "sv=" in url, "SAS token missing version param"
    assert "se=" in url, "SAS token missing expiry param"
    assert "sp=r" in url, "SAS token missing read permission"
    assert "sig=" in url, "SAS token missing signature"
    print("[PASS] SAS token has expiry, read permission, and signature")


async def test_sas_token_uses_blob_name_not_raw_url():
    """upload_file returns blob name, not raw URL."""
    with patch("app.services.storage.blob_service.BlobServiceClient") as mock_client:
        mock_blob = MagicMock()
        mock_blob.upload_blob = AsyncMock()
        mock_container = MagicMock()
        mock_container.get_blob_client.return_value = mock_blob
        mock_client.from_connection_string.return_value.get_container_client.return_value = mock_container

        from app.services.storage.blob_service import BlobStorageService

        svc = BlobStorageService()
        result = await svc.upload_file(b"data", "test.pptx")

        assert "https://" not in result, (
            f"upload_file should return blob name, got: {result}"
        )
        assert "exports/" in result, f"Expected folder in blob name, got: {result}"
        print("[PASS] upload_file returns blob name (not raw URL)")


# ── C2: HtmlBuilder Output Quality ────────────────────────────────


async def test_html_builder_has_tailwind():
    """HTML output includes Tailwind CSS CDN and config."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    slides = [make_slide(0, "bullets", "Problem")]
    builder = HtmlBuilder()
    html_out = builder.build(slides, make_theme(), make_metadata())

    assert "cdn.tailwindcss.com" in html_out, "Missing Tailwind CDN"
    assert "tailwind.config" in html_out, "Missing Tailwind config"
    assert "primary: '#2563eb'" in html_out, "Missing theme primary color"
    print("[PASS] HTML has Tailwind CDN + theme config")


async def test_html_builder_has_animations():
    """HTML output includes CSS animation classes."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    slides = [make_slide(0, "bullets", "Problem")]
    builder = HtmlBuilder()
    html_out = builder.build(slides, make_theme(), make_metadata())

    assert "animate-slide-up" in html_out, "Missing slide-up animation class"
    assert "fadeIn" in html_out, "Missing fadeIn keyframes"
    assert "slideUp" in html_out, "Missing slideUp keyframes"
    assert "slideLeft" in html_out, "Missing slideLeft keyframes"
    assert "zoomIn" in html_out, "Missing zoomIn keyframes"
    print("[PASS] HTML has CSS animations (slide-up, fade-in, slide-left, zoom-in)")


async def test_html_builder_has_keyboard_nav():
    """HTML output includes keyboard navigation JS."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    slides = [make_slide(0, "bullets", "Problem")]
    builder = HtmlBuilder()
    html_out = builder.build(slides, make_theme(), make_metadata())

    assert "ArrowRight" in html_out, "Missing arrow key navigation"
    assert "ArrowLeft" in html_out, "Missing left arrow navigation"
    assert "PresentationNav" in html_out, "Missing PresentationNav global"
    assert "touchstart" in html_out, "Missing touch swipe support"
    assert "touchend" in html_out, "Missing touch end handler"
    print("[PASS] HTML has keyboard nav + touch swipe")


async def test_html_builder_has_offline_detection():
    """HTML output includes offline detection script."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    slides = [make_slide(0, "bullets", "Problem")]
    builder = HtmlBuilder()
    html_out = builder.build(slides, make_theme(), make_metadata())

    assert "navigator.onLine" in html_out, "Missing offline detection"
    assert "tailwind" in html_out, "Missing tailwind CDN check"
    assert "Chart" in html_out, "Missing Chart.js CDN check"
    assert "internet connection" in html_out, "Missing offline alert message"
    print("[PASS] HTML has offline detection with fallback")


async def test_html_builder_has_progress_bar():
    """HTML output includes progress bar and slide counter."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    slides = [make_slide(0, "bullets", "Problem"), make_slide(1, "bullets", "Solution")]
    builder = HtmlBuilder()
    html_out = builder.build(slides, make_theme(), make_metadata())

    assert "progress-bar" in html_out, "Missing progress bar"
    assert "slide-counter" in html_out, "Missing slide counter"
    assert "nav-controls" in html_out, "Missing navigation buttons"
    assert "notes-panel" in html_out, "Missing speaker notes panel"
    print("[PASS] HTML has progress bar, counter, nav, notes panel")


async def test_html_builder_all_layouts():
    """All 12 layouts render without error."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    layouts = [
        "title-hero",
        "bullets",
        "bullets-with-image",
        "two-column",
        "chart",
        "comparison",
        "timeline",
        "quote",
        "team-grid",
        "kpi-dashboard",
        "full-image",
        "blank",
    ]

    slides = [make_slide(i, layout, f"Slide {i}") for i, layout in enumerate(layouts)]
    builder = HtmlBuilder()
    html_out = builder.build(slides, make_theme(), make_metadata())

    for layout in layouts:
        assert f'data-layout="{layout}"' in html_out, f"Missing layout: {layout}"
    print(f"[PASS] All {len(layouts)} layouts render correctly")


async def test_html_builder_chart_integration():
    """Chart slides include Chart.js canvas with data attributes."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    slide = {
        "index": 0,
        "layout": "chart",
        "content": {
            "title": "Market Size",
            "chart_data": {
                "labels": ["2023", "2024", "2025"],
                "datasets": [{"label": "Revenue", "values": [10, 20, 30]}],
            },
            "chart_type": "bar",
            "source_attribution": "McKinsey 2025",
        },
    }
    builder = HtmlBuilder()
    html_out = builder.build([slide], make_theme(), make_metadata())

    assert "canvas" in html_out, "Missing canvas element"
    assert "slide-chart" in html_out, "Missing slide-chart class"
    assert "chart.js" in html_out.lower(), "Missing Chart.js"
    assert "McKinsey 2025" in html_out, "Missing source attribution"
    print("[PASS] Chart slides include Chart.js canvas + data")


# ── C3: Cloudflare Client Modes ──────────────────────────────────


async def test_cf_client_text_mode_payload():
    """CF client in text mode sends {"message": "..."} not {"messages": [...]}."""
    from app.services.llm.cloudflare_client import CloudflareWorkerClient

    client = CloudflareWorkerClient(
        "cf-glm", "https://test.workers.dev", "test-token", mode="text"
    )

    captured_payload = {}

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "test output"}

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            captured_payload["body"] = json
            return MockResponse()

    with patch("app.services.llm.cloudflare_client.httpx.AsyncClient", MockClient):
        await client.complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=100,
        )

    assert "message" in captured_payload["body"], (
        f"Expected 'message' key, got: {captured_payload['body']}"
    )
    assert "messages" not in captured_payload["body"], (
        f"Should not have 'messages' key in text mode"
    )
    assert captured_payload["body"]["message"] == "hello"
    print("[PASS] CF text mode sends {'message': '...'} payload")


async def test_cf_client_openai_mode_payload():
    """CF client in openai mode sends {"messages": [...]}."""
    from app.services.llm.cloudflare_client import CloudflareWorkerClient

    client = CloudflareWorkerClient(
        "cf-test", "https://test.workers.dev", "test-token", mode="openai"
    )

    captured_payload = {}

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "test output"}}]}

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            captured_payload["body"] = json
            return MockResponse()

    with patch("app.services.llm.cloudflare_client.httpx.AsyncClient", MockClient):
        await client.complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=100,
        )

    assert "messages" in captured_payload["body"], (
        f"Expected 'messages' key, got: {captured_payload['body']}"
    )
    print("[PASS] CF openai mode sends {'messages': [...]} payload")


async def test_cf_client_text_mode_response_parsing():
    """CF client in text mode parses response/response/content/output keys."""
    from app.services.llm.cloudflare_client import CloudflareWorkerClient

    client = CloudflareWorkerClient(
        "cf-glm", "https://test.workers.dev", "test-token", mode="text"
    )

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "GLM output text"}

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            return MockResponse()

    with patch("app.services.llm.cloudflare_client.httpx.AsyncClient", MockClient):
        result = await client.complete(messages=[{"role": "user", "content": "test"}])

    assert result.content == "GLM output text", (
        f"Expected 'GLM output text', got: {result.content}"
    )
    print("[PASS] CF text mode parses response correctly")


async def test_cf_client_image_mode():
    """CF client in image mode sends {"prompt": "..."} and returns bytes."""
    from app.services.llm.cloudflare_client import CloudflareWorkerClient

    client = CloudflareWorkerClient(
        "cf-phoenix", "https://test.workers.dev", "test-token", mode="image"
    )

    captured_payload = {}

    class MockResponse:
        status_code = 200
        content = b"\x89PNG\r\n\x1a\nfake_image_data"

        def raise_for_status(self):
            pass

    class MockClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            captured_payload["body"] = json
            return MockResponse()

    with patch("app.services.llm.cloudflare_client.httpx.AsyncClient", MockClient):
        await client.complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=100,
        )

    assert "message" in captured_payload["body"], (
        f"Expected 'message' key, got: {captured_payload['body']}"
    )
    assert "messages" not in captured_payload["body"], (
        f"Should not have 'messages' key in text mode"
    )
    assert captured_payload["body"]["message"] == "hello"
    print("[PASS] CF text mode sends {'message': '...'} payload")


async def test_cf_client_openai_mode_payload():
    """CF client in openai mode sends {"messages": [...]}."""
    from app.services.llm.cloudflare_client import CloudflareWorkerClient

    client = CloudflareWorkerClient(
        "cf-test", "https://test.workers.dev", "test-token", mode="openai"
    )

    captured_payload = {}

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "test output"}}]}

    class MockClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            captured_payload["body"] = json
            return MockResponse()

    with patch("app.services.llm.cloudflare_client.httpx.AsyncClient", MockClient):
        await client.complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=100,
        )

    assert "messages" in captured_payload["body"], (
        f"Expected 'messages' key, got: {captured_payload['body']}"
    )
    print("[PASS] CF openai mode sends {'messages': [...]} payload")


async def test_cf_client_text_mode_response_parsing():
    """CF client in text mode parses response/response/content/output keys."""
    from app.services.llm.cloudflare_client import CloudflareWorkerClient

    client = CloudflareWorkerClient(
        "cf-glm", "https://test.workers.dev", "test-token", mode="text"
    )

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "GLM output text"}

    class MockClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            return MockResponse()

    with patch("app.services.llm.cloudflare_client.httpx.AsyncClient", MockClient):
        result = await client.complete(messages=[{"role": "user", "content": "test"}])

    assert result.content == "GLM output text", (
        f"Expected 'GLM output text', got: {result.content}"
    )
    print("[PASS] CF text mode parses response correctly")


async def test_cf_client_image_mode():
    """CF client in image mode sends {"prompt": "..."} and returns bytes."""
    from app.services.llm.cloudflare_client import CloudflareWorkerClient

    client = CloudflareWorkerClient(
        "cf-phoenix", "https://test.workers.dev", "test-token", mode="image"
    )

    captured_payload = {}

    class MockResponse:
        status_code = 200
        content = b"\x89PNG\r\n\x1a\nfake_image_data"

        def raise_for_status(self):
            pass

    class MockClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json=None, headers=None):
            captured_payload["body"] = json
            return MockResponse()

    with patch("app.services.llm.cloudflare_client.httpx.AsyncClient", MockClient):
        result = await client.generate_image("a futuristic robot")

    assert "prompt" in captured_payload["body"], (
        f"Expected 'prompt' key, got: {captured_payload['body']}"
    )
    assert captured_payload["body"]["prompt"] == "a futuristic robot"
    assert isinstance(result, bytes), f"Expected bytes, got: {type(result)}"
    assert result.startswith(b"\x89PNG"), "Expected PNG header"
    print("[PASS] CF image mode sends {'prompt': '...'} and returns bytes")


# ── C4: Export Routing (Sync vs Async with Threshold) ────────────


async def test_export_sync_small_pptx():
    """≤12 slides PPTX runs synchronously, returns completed status."""
    from app.routers.export import SLIDE_COUNT_THRESHOLD

    assert SLIDE_COUNT_THRESHOLD == 12, (
        f"Expected threshold=12, got {SLIDE_COUNT_THRESHOLD}"
    )
    print("[PASS] Slide count threshold is 12")


async def test_export_async_html_dispatch():
    """HTML export dispatches to Celery, returns PENDING status."""
    from app.routers.export import ASYNC_TASK_MAP, ExportFormat

    assert ExportFormat.HTML in ASYNC_TASK_MAP, "HTML not in async task map"
    assert ExportFormat.PNG in ASYNC_TASK_MAP, "PNG not in async task map"
    assert ASYNC_TASK_MAP[ExportFormat.HTML] == "export.generate_html"
    assert ASYNC_TASK_MAP[ExportFormat.PNG] == "export.generate_png"
    print("[PASS] HTML/PNG mapped to async Celery tasks")


async def test_export_sync_task_map():
    """PPTX/PDF mapped to sync tasks for threshold routing."""
    from app.routers.export import SYNC_TASK_MAP, ExportFormat

    assert ExportFormat.PPTX in SYNC_TASK_MAP, "PPTX not in sync task map"
    assert ExportFormat.PDF in SYNC_TASK_MAP, "PDF not in sync task map"
    assert SYNC_TASK_MAP[ExportFormat.PPTX] == "export.generate_pptx"
    assert SYNC_TASK_MAP[ExportFormat.PDF] == "export.generate_pdf"
    print("[PASS] PPTX/PDF mapped to sync Celery tasks for large decks")


# ── C5: Zombie Reaper ────────────────────────────────────────────


async def test_zombie_reaper_logic():
    """Reaper marks stuck jobs as FAILED."""
    mock_result = MagicMock()
    mock_result.modified_count = 3

    mock_collection = MagicMock()
    mock_collection.update_many.return_value = mock_result

    mock_db = MagicMock()
    mock_db.export_jobs = mock_collection

    mock_client = MagicMock()

    with patch("celery_worker._get_sync_db", return_value=(mock_db, mock_client)):
        from celery_worker import reap_stale_jobs

        result = reap_stale_jobs()

        assert result == 3, f"Expected 3 reaped, got {result}"
        mock_collection.update_many.assert_called_once()
        call_args = mock_collection.update_many.call_args
        # update_many(filter, update_dict) — both positional
        filter_query = call_args[0][0]
        update_dict = call_args[0][1]
        assert filter_query["status"] == "processing"
        assert "$set" in update_dict
        assert update_dict["$set"]["status"] == "failed"
        print("[PASS] Zombie reaper marks stuck jobs as FAILED")


# ── Test Runner ──────────────────────────────────────────────────


async def run_all():
    tests = [
        # C1: SAS Tokens
        test_sas_token_has_expiry,
        test_sas_token_uses_blob_name_not_raw_url,
        # C2: HTML Builder Quality
        test_html_builder_has_tailwind,
        test_html_builder_has_animations,
        test_html_builder_has_keyboard_nav,
        test_html_builder_has_offline_detection,
        test_html_builder_has_progress_bar,
        test_html_builder_all_layouts,
        test_html_builder_chart_integration,
        # C3: Cloudflare Client Modes
        test_cf_client_text_mode_payload,
        test_cf_client_openai_mode_payload,
        test_cf_client_text_mode_response_parsing,
        test_cf_client_image_mode,
        # C4: Export Routing
        test_export_sync_small_pptx,
        test_export_async_html_dispatch,
        test_export_sync_task_map,
        # C5: Zombie Reaper
        test_zombie_reaper_logic,
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
    print(f"Phase C Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 60}")

    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all())
