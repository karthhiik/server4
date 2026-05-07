"""
FastMCP Server — Exposes all V7 tools as MCP-protocol endpoints.

Creates a single FastMCP instance and registers every tool from the
tool_registry. Each tool handler is wrapped with error handling and
structured response formatting.
"""

import inspect
import json
import traceback
from typing import Any

import structlog
from fastmcp import FastMCP

from app.mcp.tool_registry import TOOL_REGISTRY, get_all_categories, get_tool_names_by_category

logger = structlog.get_logger(__name__)

# ── Singleton MCP Server ──────────────────────────────────────

_mcp_server: FastMCP | None = None


def get_mcp_v7_server() -> FastMCP:
    """Return the singleton FastMCP server, creating it on first access."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = _create_server()
    return _mcp_server


def _create_server() -> FastMCP:
    """Build the FastMCP server with all 40+ tools registered."""
    mcp = FastMCP(
        "barise-slide-mcp-v7",
        instructions=(
            "Barise Slide MCP v7 — AI-powered presentation generation server.\n"
            "Provides 40+ tools covering presentation CRUD, slide operations,\n"
            "content generation, design theming, PPTX export, QA scoring,\n"
            "3-D VFX, and layout optimisation."
        ),
    )

    # Register every tool from the registry
    for tool_name, tool_meta in TOOL_REGISTRY.items():
        handler = tool_meta["handler"]
        category = tool_meta["category"]
        _register_tool(mcp, tool_name, handler, category)

    # Register introspection resources
    _register_resources(mcp)

    tool_count = len(TOOL_REGISTRY)
    cat_count = len(get_all_categories())
    logger.info(
        "mcp_v7_server_created",
        tools=tool_count,
        categories=cat_count,
    )
    return mcp


def _register_tool(
    mcp: FastMCP,
    name: str,
    handler: Any,
    category: str,
) -> None:
    """Register a single async tool handler with the FastMCP server."""
    # Extract the handler's docstring for the tool description
    description = (handler.__doc__ or "").strip().split("\n")[0]

    # Build a safe wrapper that catches errors and returns JSON
    async def _wrapped_handler(**kwargs: Any) -> str:
        try:
            result = await handler(**kwargs)
            return json.dumps({"success": True, "data": result}, default=str)
        except ValueError as exc:
            logger.warning("tool_value_error", tool=name, error=str(exc))
            return json.dumps({"success": False, "error": str(exc)})
        except Exception as exc:
            logger.exception("tool_error", tool=name)
            return json.dumps({
                "success": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            })

    # Copy signature metadata so FastMCP can introspect parameters
    _wrapped_handler.__name__ = name
    _wrapped_handler.__doc__ = f"[{category}] {description}"
    _wrapped_handler.__annotations__ = handler.__annotations__.copy()
    sig = inspect.signature(handler)
    _wrapped_handler.__signature__ = sig  # type: ignore[attr-defined]

    mcp.tool(name=name, description=f"[{category}] {description}")(_wrapped_handler)


def _register_resources(mcp: FastMCP) -> None:
    """Register read-only resources for server introspection."""

    @mcp.resource("tools://list")
    async def list_tools() -> str:
        """List all available tools grouped by category."""
        by_category: dict[str, list[str]] = {}
        for tool_name, meta in TOOL_REGISTRY.items():
            cat = meta["category"]
            by_category.setdefault(cat, []).append(tool_name)
        return json.dumps(by_category, indent=2)

    @mcp.resource("tools://categories")
    async def list_categories() -> str:
        """List tool categories with counts."""
        cats = get_all_categories()
        result = {
            cat: len(get_tool_names_by_category(cat))
            for cat in cats
        }
        return json.dumps(result, indent=2)

    @mcp.resource("server://info")
    async def server_info() -> str:
        """Server version and capability summary."""
        return json.dumps({
            "name": "barise-slide-mcp-v7",
            "version": "7.0.0",
            "dsl_version": "2.0",
            "tool_count": len(TOOL_REGISTRY),
            "categories": get_all_categories(),
        })
