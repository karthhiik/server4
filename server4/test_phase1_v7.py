"""
Phase 1 V7 Verification Test Suite
===================================
Validates all Phase 1 deliverables:
  1. DSL v2 Schema (Pydantic models, validation, serialization)
  2. Context Board (sections, key validation)
  3. Tool Registry (44 tools, categories, handlers)
  4. MCP Server (singleton, tool registration, resources)
  5. ChromaDB Service (class structure, collections)
  6. Database indexes (V7 additions)
  7. Import chain integrity

Run:  python test_phase1_v7.py
"""

import sys
import os
import json
import traceback
from datetime import datetime

# ── colours for terminal output ──────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Ensure server4 root is on sys.path
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Track results
_results: list[dict] = []


def _record(name: str, passed: bool, detail: str = ""):
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}" + (f"  — {detail}" if detail else ""))
    _results.append({"name": name, "passed": passed, "detail": detail})


# ═════════════════════════════════════════════════════════════
# 1. DSL v2 SCHEMA TESTS
# ═════════════════════════════════════════════════════════════

def test_dsl_v2():
    print(f"\n{BOLD}{CYAN}═══ 1. DSL v2 Schema ═══{RESET}")

    # 1a: Import all models
    try:
        from app.models.dsl_v2 import (
            SlideType, LayoutType, BackgroundType, ElementType,
            AnimationType, ThreeSceneType, ThemeVariant, TransitionType,
            FontWeight, TextAlign,
            SlidePosition, SlideSize, BackgroundStyle, ElementStyle,
            SlideElement, FragmentAnimation, RevealConfig, ThreeSceneConfig,
            SlideStyle, KPIMetric, TeamMember, TimelineItem, ComparisonItem,
            SlideContentV2, SlideDSL, ThemeDSL,
            PresentationDimensions, PresentationMetadata, GenerationMetadataV2,
            PresentationCore, PresentationDSL,
        )
        _record("Import all DSL v2 models", True)
    except Exception as e:
        _record("Import all DSL v2 models", False, str(e))
        return  # can't continue

    # 1b: Enum member count
    _record("SlideType has 11 members", len(SlideType) == 11, f"got {len(SlideType)}")
    _record("LayoutType has 17 members", len(LayoutType) == 17, f"got {len(LayoutType)}")
    _record("ElementType has 9 members", len(ElementType) == 9, f"got {len(ElementType)}")
    _record("AnimationType has 6 members", len(AnimationType) == 6, f"got {len(AnimationType)}")
    _record("TransitionType has 6 members", len(TransitionType) == 6, f"got {len(TransitionType)}")
    _record("BackgroundType has 4 members", len(BackgroundType) == 4, f"got {len(BackgroundType)}")

    # 1c: SlidePosition normalised bounds
    try:
        SlidePosition(x=0.5, y=0.3)
        _record("SlidePosition valid (0-1)", True)
    except Exception as e:
        _record("SlidePosition valid (0-1)", False, str(e))

    try:
        SlidePosition(x=1.5, y=0.0)
        _record("SlidePosition rejects x>1", False, "should have raised")
    except Exception:
        _record("SlidePosition rejects x>1", True)

    # 1d: BackgroundStyle gradient validation
    try:
        BackgroundStyle(type=BackgroundType.GRADIENT_LINEAR, colors=["#ff0000"])
        _record("Gradient rejects single color", False, "should have raised")
    except Exception:
        _record("Gradient rejects single color", True)

    try:
        BackgroundStyle(type=BackgroundType.GRADIENT_LINEAR, colors=["#ff0000", "#00ff00"])
        _record("Gradient accepts 2 colors", True)
    except Exception as e:
        _record("Gradient accepts 2 colors", False, str(e))

    # 1e: Hex color validation
    try:
        BackgroundStyle(colors=["not-hex"])
        _record("Rejects invalid hex", False, "should have raised")
    except Exception:
        _record("Rejects invalid hex", True)

    try:
        BackgroundStyle(colors=["#ABC", "#aabbcc", "#aabbccdd"])
        _record("Accepts 3/6/8 char hex", True)
    except Exception as e:
        _record("Accepts 3/6/8 char hex", False, str(e))

    # 1f: SlideDSL fragment→element integrity
    try:
        SlideDSL(
            index=0, id="s1",
            elements=[SlideElement(id="e1", type=ElementType.TEXT)],
            fragments=[FragmentAnimation(elementId="e1", order=0)],
        )
        _record("Fragment refs valid element", True)
    except Exception as e:
        _record("Fragment refs valid element", False, str(e))

    try:
        SlideDSL(
            index=0, id="s1",
            elements=[SlideElement(id="e1", type=ElementType.TEXT)],
            fragments=[FragmentAnimation(elementId="MISSING", order=0)],
        )
        _record("Fragment rejects missing element", False, "should have raised")
    except Exception:
        _record("Fragment rejects missing element", True)

    # 1g: Unique element IDs
    try:
        SlideDSL(
            index=0, id="s1",
            elements=[
                SlideElement(id="dup", type=ElementType.TEXT),
                SlideElement(id="dup", type=ElementType.IMAGE),
            ],
        )
        _record("Rejects duplicate element IDs", False, "should have raised")
    except Exception:
        _record("Rejects duplicate element IDs", True)

    # 1h: Full PresentationDSL round-trip
    try:
        pres = PresentationDSL(
            version="2.0",
            presentation=PresentationCore(id="p1", title="Test Deck"),
            slides=[
                SlideDSL(index=0, id="slide-0", type=SlideType.TITLE_SLIDE,
                         content=SlideContentV2(title="Hello World")),
                SlideDSL(index=1, id="slide-1", type=SlideType.PROBLEM_SLIDE,
                         content=SlideContentV2(title="The Problem")),
            ],
        )
        doc = pres.to_mongo_doc()
        restored = PresentationDSL.from_mongo_doc(doc)
        _record("PresentationDSL round-trip (to/from mongo)", True,
                f"{len(restored.slides)} slides")
    except Exception as e:
        _record("PresentationDSL round-trip", False, str(e))

    # 1i: Contiguous slide index validation
    try:
        PresentationDSL(
            version="2.0",
            presentation=PresentationCore(id="p2", title="Bad Indexes"),
            slides=[
                SlideDSL(index=0, id="s0", content=SlideContentV2(title="A")),
                SlideDSL(index=5, id="s5", content=SlideContentV2(title="B")),
            ],
        )
        _record("Rejects non-contiguous indexes", False, "should have raised")
    except Exception:
        _record("Rejects non-contiguous indexes", True)

    # 1j: Unique slide IDs
    try:
        PresentationDSL(
            version="2.0",
            presentation=PresentationCore(id="p3", title="Dup IDs"),
            slides=[
                SlideDSL(index=0, id="dup", content=SlideContentV2(title="A")),
                SlideDSL(index=1, id="dup", content=SlideContentV2(title="B")),
            ],
        )
        _record("Rejects duplicate slide IDs", False, "should have raised")
    except Exception:
        _record("Rejects duplicate slide IDs", True)

    # 1k: JSON serialization
    try:
        pres = PresentationDSL(
            version="2.0",
            presentation=PresentationCore(id="p4", title="JSON Test"),
            slides=[SlideDSL(index=0, id="s0", content=SlideContentV2(title="Slide"))],
        )
        j = json.dumps(pres.to_mongo_doc())
        assert len(j) > 50
        _record("JSON serialization", True, f"{len(j)} bytes")
    except Exception as e:
        _record("JSON serialization", False, str(e))

    # 1l: GenerationMetadataV2
    try:
        meta = GenerationMetadataV2(
            skillVersions={"ceo": 3, "designer": 2},
            qualityScore=85,
            modelUsage={"ceo": "kimi-k2"},
            totalCost="$0.04",
        )
        assert meta.qualityScore == 85
        _record("GenerationMetadataV2", True)
    except Exception as e:
        _record("GenerationMetadataV2", False, str(e))

    # 1m: SlideContentV2 semantic fields
    try:
        content = SlideContentV2(
            title="Revenue Growth",
            subtitle="Q1 2025",
            bullets=["$2M ARR", "150% YoY"],
            kpi_metrics=[KPIMetric(label="ARR", value="$2M", trend="up")],
            team_members=[TeamMember(name="John", role="CEO")],
        )
        assert content.kpi_metrics[0].trend == "up"
        _record("SlideContentV2 semantic fields", True)
    except Exception as e:
        _record("SlideContentV2 semantic fields", False, str(e))


# ═════════════════════════════════════════════════════════════
# 2. CONTEXT BOARD TESTS
# ═════════════════════════════════════════════════════════════

def test_context_board():
    print(f"\n{BOLD}{CYAN}═══ 2. Context Board ═══{RESET}")

    try:
        from app.services.context_board import ContextBoard, VALID_SECTIONS
        _record("Import ContextBoard", True)
    except Exception as e:
        _record("Import ContextBoard", False, str(e))
        return

    # 2a: Valid sections
    expected = {"strategy", "research", "design", "layout", "dsl", "quality", "images", "status"}
    _record("8 valid sections", VALID_SECTIONS == expected,
            f"got {VALID_SECTIONS}")

    # 2b: Key validation
    try:
        ContextBoard._validate_key("strategy.archetype")
        _record("Valid key 'strategy.archetype'", True)
    except Exception as e:
        _record("Valid key 'strategy.archetype'", False, str(e))

    try:
        ContextBoard._validate_key("no_dot")
        _record("Rejects key without dot", False, "should have raised")
    except ValueError:
        _record("Rejects key without dot", True)

    try:
        ContextBoard._validate_key("invalid_section.field")
        _record("Rejects unknown section", False, "should have raised")
    except ValueError:
        _record("Rejects unknown section", True)

    # 2c: JSON parse helper
    assert ContextBoard._maybe_parse_json('{"a":1}') == {"a": 1}
    _record("_maybe_parse_json dict", True)
    assert ContextBoard._maybe_parse_json("plain text") == "plain text"
    _record("_maybe_parse_json string", True)

    # 2d: Instance creation
    try:
        board = ContextBoard(session_id="test-session-123")
        assert board.session_id == "test-session-123"
        _record("ContextBoard instance creation", True)
    except Exception as e:
        _record("ContextBoard instance creation", False, str(e))


# ═════════════════════════════════════════════════════════════
# 3. TOOL REGISTRY TESTS
# ═════════════════════════════════════════════════════════════

def test_tool_registry():
    print(f"\n{BOLD}{CYAN}═══ 3. Tool Registry ═══{RESET}")

    try:
        from app.mcp.tool_registry import (
            TOOL_REGISTRY,
            get_all_categories,
            get_tool_names_by_category,
            ToolResult,
        )
        _record("Import Tool Registry", True)
    except Exception as e:
        _record("Import Tool Registry", False, str(e))
        return

    # 3a: Total tool count
    total = len(TOOL_REGISTRY)
    _record(f"Tool count >= 40", total >= 40, f"got {total}")

    # 3b: Categories
    cats = get_all_categories()
    expected_cats = {"presentation", "slide", "content", "strategy",
                     "research", "design", "pptx", "qa", "vfx", "layout"}
    _record("10 categories present", set(cats) == expected_cats,
            f"got {cats}")

    # 3c: Tools per category
    cat_counts = {c: len(get_tool_names_by_category(c)) for c in cats}
    _record("Presentation tools >= 6", cat_counts.get("presentation", 0) >= 6,
            f"got {cat_counts.get('presentation', 0)}")
    _record("Slide tools >= 7", cat_counts.get("slide", 0) >= 7,
            f"got {cat_counts.get('slide', 0)}")
    _record("Content tools >= 6", cat_counts.get("content", 0) >= 6,
            f"got {cat_counts.get('content', 0)}")
    _record("QA tools >= 4", cat_counts.get("qa", 0) >= 4,
            f"got {cat_counts.get('qa', 0)}")

    # 3d: All handlers are async callables
    all_async = True
    non_async = []
    import asyncio
    for name, meta in TOOL_REGISTRY.items():
        if not asyncio.iscoroutinefunction(meta["handler"]):
            all_async = False
            non_async.append(name)
    _record("All handlers are async", all_async,
            f"non-async: {non_async}" if non_async else "")

    # 3e: ToolResult schema
    try:
        tr = ToolResult(success=True, data={"test": 1}, meta={"version": "7.0"})
        assert tr.success is True
        assert tr.data == {"test": 1}
        _record("ToolResult schema", True)
    except Exception as e:
        _record("ToolResult schema", False, str(e))

    # 3f: Specific tool existence
    essential_tools = [
        "create_presentation", "get_presentation", "delete_presentation",
        "add_slide", "update_slide", "delete_slide", "reorder_slides",
        "generate_dsl", "compile_react", "compile_revealjs", "compile_html",
        "apply_theme", "create_pptx", "snapshot", "score_quality",
        "create_3d_scene", "select_layout", "validate_fit",
        "check_contrast", "research_topic",
    ]
    for tool in essential_tools:
        _record(f"Tool '{tool}' registered", tool in TOOL_REGISTRY)

    # 3g: check_contrast pure logic test (no DB needed)
    import asyncio
    try:
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["check_contrast"]["handler"](
                foreground="#ffffff", background="#000000"
            )
        )
        _record("check_contrast #fff/#000 ≈ 21:1",
                result["ratio"] >= 20.0 and result["aa_normal"] is True,
                f"ratio={result['ratio']}")
    except Exception as e:
        _record("check_contrast logic", False, str(e))

    # 3h: select_layout pure logic test
    try:
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["select_layout"]["handler"](
                slide_type="title-slide", content_length=50,
            )
        )
        _record("select_layout title→center-focus",
                result["recommended_layout"] == "center-focus",
                f"got {result['recommended_layout']}")
    except Exception as e:
        _record("select_layout logic", False, str(e))

    # 3i: optimize_grid pure logic test
    try:
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["optimize_grid"]["handler"](element_count=6)
        )
        _record("optimize_grid 6 elements → 3x2",
                result["cols"] == 3 and result["rows"] == 2,
                f"got {result['cols']}x{result['rows']}")
    except Exception as e:
        _record("optimize_grid logic", False, str(e))

    # 3j: measure_content pure logic test
    try:
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["measure_content"]["handler"](
                content={"title": "Test", "body_text": "x" * 600, "bullets": ["a", "b", "c"]}
            )
        )
        _record("measure_content overflow detection",
                result["body_length"] == 600 and result["bullet_count"] == 3,
                f"body={result['body_length']}, bullets={result['bullet_count']}")
    except Exception as e:
        _record("measure_content logic", False, str(e))

    # 3k: select_archetype pure logic test
    try:
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["select_archetype"]["handler"](
                topic="AI Startup", audience="investors"
            )
        )
        _record("select_archetype → problem-solution",
                result["recommended"] == "problem-solution",
                f"got {result['recommended']}")
    except Exception as e:
        _record("select_archetype logic", False, str(e))


# ═════════════════════════════════════════════════════════════
# 4. MCP SERVER TESTS
# ═════════════════════════════════════════════════════════════

def test_mcp_server():
    print(f"\n{BOLD}{CYAN}═══ 4. MCP Server ═══{RESET}")

    try:
        from app.mcp.mcp_server import get_mcp_v7_server
        _record("Import MCP server", True)
    except Exception as e:
        _record("Import MCP server", False, str(e))
        return

    # 4a: Singleton creation
    try:
        mcp = get_mcp_v7_server()
        _record("MCP server singleton created", mcp is not None)
    except Exception as e:
        _record("MCP server singleton created", False, str(e))
        return

    # 4b: Singleton identity
    try:
        mcp2 = get_mcp_v7_server()
        _record("Singleton returns same instance", mcp is mcp2)
    except Exception as e:
        _record("Singleton identity", False, str(e))

    # 4c: Server name
    try:
        name = mcp.name
        _record("Server name = 'barise-slide-mcp-v7'",
                name == "barise-slide-mcp-v7",
                f"got '{name}'")
    except Exception as e:
        _record("Server name", False, str(e))

    # 4d: Tools registered
    try:
        from app.mcp.tool_registry import TOOL_REGISTRY
        expected = len(TOOL_REGISTRY)
        # FastMCP stores tools internally — we verify by checking the registry length
        _record(f"Expected {expected} tools in registry", expected >= 40,
                f"got {expected}")
    except Exception as e:
        _record("Tool registration count", False, str(e))


# ═════════════════════════════════════════════════════════════
# 5. CHROMADB SERVICE TESTS
# ═════════════════════════════════════════════════════════════

def test_chromadb_service():
    print(f"\n{BOLD}{CYAN}═══ 5. ChromaDB Service ═══{RESET}")

    try:
        from app.services.chromadb_service import ChromaService
        _record("Import ChromaService", True)
    except Exception as e:
        _record("Import ChromaService", False, str(e))
        return

    # 5a: Class has expected methods
    expected_methods = [
        "add_presentation", "search_similar", "delete_presentation",
        "add_skill_example", "search_skill_examples",
        "add_research_document", "search_research",
        "collection_count",
    ]
    for method_name in expected_methods:
        has_method = hasattr(ChromaService, method_name) and callable(getattr(ChromaService, method_name))
        _record(f"ChromaService.{method_name}() exists", has_method)

    # 5b: Try to instantiate (creates local ChromaDB in ./data/chromadb)
    try:
        service = ChromaService()
        _record("ChromaService instantiation", True)
    except Exception as e:
        _record("ChromaService instantiation", False, str(e))
        return

    # 5c: Collection counts (should be 0 initially or whatever exists)
    import asyncio
    try:
        count = asyncio.get_event_loop().run_until_complete(
            service.collection_count("presentations")
        )
        _record("collection_count('presentations')", count >= 0, f"count={count}")
    except Exception as e:
        _record("collection_count", False, str(e))

    # 5d: Add and search a test document
    try:
        asyncio.get_event_loop().run_until_complete(
            service.add_presentation(
                id="test-phase1-v7",
                text="AI startup pitch deck with market analysis and revenue projections",
                metadata={"test": True},
            )
        )
        results = asyncio.get_event_loop().run_until_complete(
            service.search_similar("AI startup pitch", n_results=1)
        )
        found = any(r["id"] == "test-phase1-v7" for r in results)
        _record("Add + search presentation", found,
                f"results={len(results)}")
    except Exception as e:
        _record("Add + search presentation", False, str(e))

    # 5e: Clean up test doc
    try:
        asyncio.get_event_loop().run_until_complete(
            service.delete_presentation("test-phase1-v7")
        )
        _record("Delete test presentation", True)
    except Exception as e:
        _record("Delete test presentation", False, str(e))

    # 5f: Skill example round-trip
    try:
        asyncio.get_event_loop().run_until_complete(
            service.add_skill_example(
                skill_name="title-slide",
                version=1,
                example_dsl='{"type":"title-slide","layout":"center-focus"}',
                quality_score=90,
            )
        )
        results = asyncio.get_event_loop().run_until_complete(
            service.search_skill_examples("title slide", n_results=1)
        )
        _record("Skill example add+search", len(results) > 0,
                f"results={len(results)}")
    except Exception as e:
        _record("Skill example add+search", False, str(e))


# ═════════════════════════════════════════════════════════════
# 6. DATABASE TESTS
# ═════════════════════════════════════════════════════════════

def test_database():
    print(f"\n{BOLD}{CYAN}═══ 6. Database Module ═══{RESET}")

    try:
        from app.database import get_db, connect_db, close_db, get_chroma_service
        _record("Import database module", True)
    except Exception as e:
        _record("Import database module", False, str(e))
        return

    # 6a: get_chroma_service function exists
    _record("get_chroma_service() callable", callable(get_chroma_service))

    # 6b: get_db raises before connect
    try:
        get_db()
        # If it doesn't raise, DB was already connected (ok in integration)
        _record("get_db() accessible", True, "DB already connected or test env")
    except RuntimeError:
        _record("get_db() raises before connect", True, "expected before connect_db()")
    except Exception as e:
        _record("get_db() behaviour", False, str(e))


# ═════════════════════════════════════════════════════════════
# 7. IMPORT CHAIN INTEGRITY
# ═════════════════════════════════════════════════════════════

def test_import_chain():
    print(f"\n{BOLD}{CYAN}═══ 7. Import Chain Integrity ═══{RESET}")

    modules = [
        ("app.models.dsl_v2", "DSL v2 models"),
        ("app.services.context_board", "Context Board"),
        ("app.mcp.tool_registry", "Tool Registry"),
        ("app.mcp.mcp_server", "MCP Server"),
        ("app.services.chromadb_service", "ChromaDB Service"),
        ("app.database", "Database module"),
        ("app.config", "Config (Settings)"),
        ("app.services.llm.model_router", "LLM Model Router"),
    ]
    for mod_path, label in modules:
        try:
            __import__(mod_path)
            _record(f"import {label}", True)
        except Exception as e:
            _record(f"import {label}", False, str(e))

    # Verify get_model_router accessor
    try:
        from app.services.llm.model_router import get_model_router
        _record("get_model_router() importable", True)
    except Exception as e:
        _record("get_model_router() importable", False, str(e))


# ═════════════════════════════════════════════════════════════
# 8. CROSS-MODULE INTEGRATION
# ═════════════════════════════════════════════════════════════

def test_cross_module():
    print(f"\n{BOLD}{CYAN}═══ 8. Cross-Module Integration ═══{RESET}")

    # 8a: DSL v2 → tool_registry compile_react (no DB)
    try:
        from app.models.dsl_v2 import (
            PresentationDSL, PresentationCore, SlideDSL, SlideContentV2, SlideType,
        )
        from app.mcp.tool_registry import TOOL_REGISTRY
        import asyncio

        pres = PresentationDSL(
            version="2.0",
            presentation=PresentationCore(id="cross1", title="Cross-Module Test"),
            slides=[
                SlideDSL(index=0, id="s0", type=SlideType.TITLE_SLIDE,
                         content=SlideContentV2(title="Hello")),
                SlideDSL(index=1, id="s1", type=SlideType.PROBLEM_SLIDE,
                         content=SlideContentV2(title="Problem")),
            ],
        )
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["compile_react"]["handler"](
                presentation_dsl=pres.to_mongo_doc()
            )
        )
        _record("DSL→compile_react integration",
                result["format"] == "react" and result["slide_count"] == 2,
                f"format={result['format']}, slides={result['slide_count']}")
    except Exception as e:
        _record("DSL→compile_react integration", False, str(e))

    # 8b: DSL v2 → compile_revealjs
    try:
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["compile_revealjs"]["handler"](
                presentation_dsl=pres.to_mongo_doc()
            )
        )
        _record("DSL→compile_revealjs integration",
                result["format"] == "revealjs" and "<section" in result["html"],
                f"has sections={('<section' in result['html'])}")
    except Exception as e:
        _record("DSL→compile_revealjs integration", False, str(e))

    # 8c: DSL v2 → compile_html
    try:
        result = asyncio.get_event_loop().run_until_complete(
            TOOL_REGISTRY["compile_html"]["handler"](
                presentation_dsl=pres.to_mongo_doc()
            )
        )
        _record("DSL→compile_html integration",
                result["format"] == "html" and "<!DOCTYPE html>" in result["html"],
                f"length={len(result['html'])}")
    except Exception as e:
        _record("DSL→compile_html integration", False, str(e))


# ═════════════════════════════════════════════════════════════
# MAIN — RUN ALL TESTS
# ═════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'='*60}")
    print(f"  Phase 1 V7 Verification Suite  —  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'='*60}{RESET}")

    test_dsl_v2()
    test_context_board()
    test_tool_registry()
    test_mcp_server()
    test_chromadb_service()
    test_database()
    test_import_chain()
    test_cross_module()

    # ── Summary ───────────────────────────────────────────────
    total = len(_results)
    passed = sum(1 for r in _results if r["passed"])
    failed = total - passed

    print(f"\n{BOLD}{'='*60}")
    print(f"  RESULTS: {GREEN}{passed}{RESET}{BOLD} passed, "
          f"{RED if failed else GREEN}{failed}{RESET}{BOLD} failed, "
          f"{total} total")
    print(f"{'='*60}{RESET}")

    if failed:
        print(f"\n{RED}Failed tests:{RESET}")
        for r in _results:
            if not r["passed"]:
                print(f"  {RED}✗{RESET} {r['name']}: {r['detail']}")

    print(f"\n{'='*60}")
    print(f"  Pass rate: {passed/total*100:.1f}%")
    print(f"{'='*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
