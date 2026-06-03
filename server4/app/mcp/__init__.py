"""
MCP Core Server - Premium Slide Generation System

This module provides the core MCP (Model Context Protocol) server
for the slide generation system. It exposes tools and resources
that can be used by MCP clients (Claude, etc.) to generate
professional presentations.

Architecture:
- brain_mcp/: Research and content generation engines
- design_mcp/: Visual design and layout engines  
- render_mcp/: Export and rendering builders (PPTX, PDF, HTML)
- core/: Orchestration, tools registry, context board

Available Tool Categories:
1. Presentation Management (create, update, delete)
2. Slide Operations (add, edit, reorder, delete slides)
3. Content Generation (AI-powered content)
4. Design & Theming (colors, fonts, layouts)
5. Image Generation (AI images, charts)
6. Research Tools (market data, financial data)
7. Export Tools (PPTX, PDF, HTML)
8. Quality Assurance (validation, scoring)
"""

# Lazy imports to avoid circular dependencies
def get_mcp_server():
    from app.mcp.mcp_server import get_mcp_v7_server
    return get_mcp_v7_server()

def get_context_board():
    raise NotImplementedError("ContextBoard has not been implemented in this version.")

def get_tools_registry():
    from app.mcp.tool_registry import TOOL_REGISTRY
    return TOOL_REGISTRY

__all__ = [
    "get_mcp_server",
    "get_context_board",
    "get_tools_registry",
]
