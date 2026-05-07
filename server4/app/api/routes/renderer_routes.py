"""
Phase 4 — Renderer & Theme API Routes.

Endpoints:
- POST /api/v2/render/compile       — Compile PresentationDSL → reveal.js HTML
- POST /api/v2/render/preview-slide  — Render single slide HTML
- GET  /api/v2/themes/built-in       — List all built-in themes
- GET  /api/v2/themes/built-in/{id}  — Get a specific built-in theme
- POST /api/v2/themes/generate       — Generate theme from brand colors
- POST /api/v2/themes/{id}/mutate    — Mutate a theme (warmer, cooler, etc.)
- GET  /api/v2/themes/{id}/css       — Get compiled CSS for a theme
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.models.dsl_v2 import PresentationDSL, SlideDSL
from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
from app.services.slides_new.themes.theme_models import (
    BuiltInThemes,
    ThemeMutation,
)
from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine
from app.services.slides_new.themes.css_compiler import CSSCompiler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["renderer-v2"])


# ═══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════


class CompileRequest(BaseModel):
    """Request to compile a full presentation."""

    presentation: PresentationDSL
    theme_id: Optional[str] = None


class CompileResponse(BaseModel):
    """Compiled reveal.js output."""

    html: str
    css: str
    js: str
    slide_count: int
    success: bool
    error: Optional[str] = None


class PreviewSlideRequest(BaseModel):
    """Request to preview a single slide."""

    slide: SlideDSL
    theme_id: Optional[str] = None


class PreviewSlideResponse(BaseModel):
    """Single-slide preview HTML."""

    html: str
    success: bool
    error: Optional[str] = None


class GenerateThemeRequest(BaseModel):
    """Request to generate a theme from brand colors."""

    primary: str = Field(..., description="Primary brand color (#hex)")
    secondary: Optional[str] = Field(None, description="Secondary color (#hex)")
    accent: Optional[str] = Field(None, description="Accent color (#hex)")
    mood: str = Field("professional", description="Theme mood")
    name: Optional[str] = Field(None, description="Override theme name")

    @field_validator("primary", "secondary", "accent", mode="before")
    @classmethod
    def validate_hex_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v):
            raise ValueError(f"Invalid hex color: {v}")
        return v


class MutateThemeRequest(BaseModel):
    """Request to create a theme mutation."""

    mutation: ThemeMutation


class ThemeSummary(BaseModel):
    """Summary of a theme for listing."""

    id: str
    name: str
    variant: str
    character: str
    primary: str
    background: str
    heading_font: str
    body_font: str


class ThemeDetail(BaseModel):
    """Full theme details."""

    id: str
    name: str
    variant: str
    tier: str
    character: str
    colors: dict
    typography: dict
    spacing: dict


class ThemeCSSResponse(BaseModel):
    """Compiled CSS for a theme."""

    theme_id: str
    css: str
    warnings: list[str]


# ═══════════════════════════════════════════════════════════════════════
# SINGLETONS
# ═══════════════════════════════════════════════════════════════════════

_compiler = RevealCompiler()
_engine = GenerativeThemeEngine()
_css_compiler = CSSCompiler()


# ═══════════════════════════════════════════════════════════════════════
# RENDER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@router.post("/render/compile", response_model=CompileResponse)
async def compile_presentation(request: CompileRequest):
    """Compile a PresentationDSL to a self-contained reveal.js HTML document."""
    try:
        output = _compiler.render_presentation(request.presentation)
        return CompileResponse(
            html=output.html,
            css=output.css,
            js=output.js,
            slide_count=output.slide_count,
            success=output.success,
            error=output.error,
        )
    except Exception as e:
        logger.exception("compile_presentation_failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render/preview-slide", response_model=PreviewSlideResponse)
async def preview_slide(request: PreviewSlideRequest):
    """Render a single slide to an HTML <section> fragment."""
    try:
        html = _compiler.render_slide(request.slide)
        return PreviewSlideResponse(html=html, success=True)
    except Exception as e:
        logger.exception("preview_slide_failed")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# THEME ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@router.get("/themes/built-in", response_model=list[ThemeSummary])
async def list_builtin_themes():
    """List all 24 built-in themes."""
    results: list[ThemeSummary] = []
    for theme in BuiltInThemes.list_all():
        results.append(
            ThemeSummary(
                id=theme.id,
                name=theme.name,
                variant=theme.variant,
                character=theme.character,
                primary=theme.colors.primary,
                background=theme.colors.background,
                heading_font=theme.typography.heading_font,
                body_font=theme.typography.body_font,
            )
        )
    return results


@router.get("/themes/built-in/{theme_id}", response_model=ThemeDetail)
async def get_builtin_theme(theme_id: str):
    """Get full details of a built-in theme."""
    theme = BuiltInThemes.get(theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    return ThemeDetail(
        id=theme.id,
        name=theme.name,
        variant=theme.variant,
        tier=theme.tier.value,
        character=theme.character,
        colors=theme.colors.__dict__,
        typography=theme.typography.__dict__,
        spacing=theme.spacing.__dict__,
    )


@router.post("/themes/generate", response_model=ThemeDetail)
async def generate_theme(request: GenerateThemeRequest):
    """Generate a theme from brand colors and mood."""
    try:
        theme = _engine.from_brand_colors(
            primary=request.primary,
            secondary=request.secondary,
            accent=request.accent,
            mood=request.mood,
            name=request.name,
        )
        return ThemeDetail(
            id=theme.id,
            name=theme.name,
            variant=theme.variant,
            tier=theme.tier.value,
            character=theme.character,
            colors=theme.colors.__dict__,
            typography=theme.typography.__dict__,
            spacing=theme.spacing.__dict__,
        )
    except Exception as e:
        logger.exception("generate_theme_failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/themes/{theme_id}/mutate", response_model=ThemeDetail)
async def mutate_theme(theme_id: str, request: MutateThemeRequest):
    """Create a mutation of a built-in theme."""
    base = BuiltInThemes.get(theme_id)
    if base is None:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    try:
        mutated = _engine.mutate(base, request.mutation)
        return ThemeDetail(
            id=mutated.id,
            name=mutated.name,
            variant=mutated.variant,
            tier=mutated.tier.value,
            character=mutated.character,
            colors=mutated.colors.__dict__,
            typography=mutated.typography.__dict__,
            spacing=mutated.spacing.__dict__,
        )
    except Exception as e:
        logger.exception("mutate_theme_failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes/{theme_id}/css", response_model=ThemeCSSResponse)
async def get_theme_css(theme_id: str):
    """Get compiled CSS for a built-in theme."""
    theme = BuiltInThemes.get(theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    css, warnings = _css_compiler.compile_with_validation(theme)
    return ThemeCSSResponse(
        theme_id=theme_id,
        css=css,
        warnings=warnings,
    )
