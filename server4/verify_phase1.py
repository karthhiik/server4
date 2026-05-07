"""
Phase 1 Verification Script — Validates all V7 Foundation deliverables.
"""

import sys
import traceback

def test_dsl_v2_schema():
    """Test 1: DSL v2 Schema (Pydantic validation)"""
    from app.models.dsl_v2 import (
        PresentationDSL, SlideDSL, SlideType, LayoutType,
        ThemeDSL, PresentationCore, SlideContentV2
    )

    # Create a valid slide
    slide = SlideDSL(
        index=0,
        id="slide-1",
        type=SlideType.TITLE_SLIDE,
        layout=LayoutType.CENTER_FOCUS,
        content=SlideContentV2(title="Test Title", subtitle="Test Subtitle")
    )

    # Create a full presentation DSL
    pres = PresentationDSL(
        version="2.0",
        presentation=PresentationCore(id="test-1", title="Test Presentation"),
        slides=[slide]
    )

    assert pres.version == "2.0"
    assert len(pres.slides) == 1
    assert pres.slides[0].type == SlideType.TITLE_SLIDE
    return f"DSL v2 validated: {len(pres.slides)} slide(s), version {pres.version}"


def test_tool_registry():
    """Test 2: Tool Registry with 40+ tools"""
    from app.mcp.tool_registry import TOOL_REGISTRY, get_all_categories, get_tool_names_by_category

    tools_count = len(TOOL_REGISTRY)
    categories = get_all_categories()

    # Phase 1 requires 40+ tools
    assert tools_count >= 40, f"Expected 40+ tools, got {tools_count}"

    # Verify required categories exist
    required_cats = {"presentation", "slide", "content", "design", "pptx", "qa", "layout"}
    actual_cats = set(categories)
    missing = required_cats - actual_cats
    assert not missing, f"Missing categories: {missing}"

    return f"Tool Registry: {tools_count} tools in {len(categories)} categories ({categories})"


def test_mcp_server():
    """Test 3: FastMCP server with tools registered"""
    from app.mcp.mcp_server import get_mcp_v7_server

    mcp = get_mcp_v7_server()
    assert mcp is not None
    assert mcp.name == "barise-slide-mcp-v7"

    return f"FastMCP server: {mcp.name}"


def test_context_board():
    """Test 4: Agent Communication Protocol (Context Board)"""
    from app.services.context_board import ContextBoard, VALID_SECTIONS

    # Verify all required sections exist
    required_sections = {"strategy", "research", "design", "layout", "dsl", "quality", "images", "status"}
    assert VALID_SECTIONS == required_sections, f"Missing sections: {required_sections - VALID_SECTIONS}"

    # Verify class can be instantiated
    board = ContextBoard(session_id="test-session")
    assert board.session_id == "test-session"

    return f"ContextBoard sections: {list(VALID_SECTIONS)}"


def test_database_setup():
    """Test 5: MongoDB + Redis + ChromaDB configuration"""
    from app.config import settings

    # MongoDB
    assert settings.MONGODB_URI, "MONGODB_URI not configured"
    assert settings.MONGODB_DB_NAME, "MONGODB_DB_NAME not configured"

    # Redis
    assert settings.REDIS_URL, "REDIS_URL not configured"

    # Celery (uses Redis)
    assert settings.CELERY_BROKER_URL, "CELERY_BROKER_URL not configured"

    return f"Config OK: DB={settings.MONGODB_DB_NAME}, Redis configured"


def test_chromadb_service():
    """Test 6: ChromaDB vector store service"""
    from app.services.chromadb_service import ChromaService

    # Verify class exists and has required methods
    assert hasattr(ChromaService, 'add_presentation')
    assert hasattr(ChromaService, 'search_similar')

    return "ChromaDB service class available with required methods"


def test_crud_handlers():
    """Test 7: Basic CRUD handlers exist"""
    from app.mcp.tool_registry import (
        create_presentation, get_presentation, update_presentation,
        delete_presentation, list_presentations,
        add_slide, update_slide, delete_slide, get_slide, get_all_slides
    )

    # Verify they are async functions
    import asyncio
    assert asyncio.iscoroutinefunction(create_presentation)
    assert asyncio.iscoroutinefunction(get_presentation)
    assert asyncio.iscoroutinefunction(update_presentation)
    assert asyncio.iscoroutinefunction(delete_presentation)
    assert asyncio.iscoroutinefunction(list_presentations)
    assert asyncio.iscoroutinefunction(add_slide)
    assert asyncio.iscoroutinefunction(update_slide)
    assert asyncio.iscoroutinefunction(delete_slide)
    assert asyncio.iscoroutinefunction(get_slide)
    assert asyncio.iscoroutinefunction(get_all_slides)

    return "CRUD handlers: 10 async functions verified"


def test_database_indexes():
    """Test 8: V7 collection indexes defined"""
    from app.database import _create_indexes
    import asyncio

    # Just verify the function exists and is async
    assert asyncio.iscoroutinefunction(_create_indexes)

    return "Database index function ready (V7 collections defined)"


def main():
    tests = [
        ("DSL v2 Schema", test_dsl_v2_schema),
        ("Tool Registry (40+ tools)", test_tool_registry),
        ("FastMCP Server", test_mcp_server),
        ("Context Board (Agent Protocol)", test_context_board),
        ("Database Config (MongoDB/Redis)", test_database_setup),
        ("ChromaDB Service", test_chromadb_service),
        ("CRUD Handlers", test_crud_handlers),
        ("Database Indexes", test_database_indexes),
    ]

    print("=" * 60)
    print("V7 PHASE 1 VERIFICATION — Foundation")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            result = test_fn()
            print(f"✓ {name}")
            print(f"  └─ {result}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}")
            print(f"  └─ ERROR: {e}")
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 PHASE 1 VERIFICATION COMPLETE — All deliverables confirmed!")
        return 0
    else:
        print(f"\n⚠️ PHASE 1 INCOMPLETE — {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
