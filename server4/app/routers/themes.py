"""Theme management — list, generate, apply."""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_auth
from app.models.theme import ThemeGenerateRequest, ThemeResponse, ThemeType

router = APIRouter(prefix="/api/themes", tags=["Themes"])


def _doc_to_response(doc: dict) -> ThemeResponse:
    from app.models.theme import ThemeColors, ThemeFonts
    return ThemeResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc.get("type", "builtin"),
        colors=ThemeColors(**doc.get("colors", {})),
        fonts=ThemeFonts(**doc.get("fonts", {})),
    )


def _theme_v2_payload(t) -> dict:
    """Serialize a v2 theme with the full frontend ThemeItem contract."""
    return {
        "id": t.id,
        "name": t.name,
        "categories": t.categories,
        "primary": t.primary,
        "accent": t.accent,
        "background": t.background,
        "heading_font": t.heading_font,
        "body_font": t.body_font,
        "density": t.density,
        "motion_style": t.motion_style,
        "layout_posture": t.layout_posture,
        "description": t.description,
        "tags": t.tags,
        "is_dark": t.is_dark,
    }


@router.get("")
async def list_themes(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[ThemeResponse]:
    cursor = db.themes.find({}).sort("name", 1).skip(offset)
    docs = await cursor.to_list(limit)
    return [_doc_to_response(d) for d in docs]


@router.post("/generate")
async def generate_theme(
    body: ThemeGenerateRequest,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> ThemeResponse:
    """
    Generative theme creation from brand colors.
    Uses HSL color math (no LLM needed for most of it).
    """
    from app.services.llm import ModelRouter, TaskType
    import colorsys
    import json

    base_hex = body.brand_colors[0].lstrip("#")
    r, g, b = int(base_hex[0:2], 16) / 255, int(base_hex[2:4], 16) / 255, int(base_hex[4:6], 16) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    def hls_to_hex(h_, l_, s_):
        r_, g_, b_ = colorsys.hls_to_rgb(h_, l_, s_)
        return f"#{int(r_*255):02x}{int(g_*255):02x}{int(b_*255):02x}"

    # Generate complementary colors using color theory
    primary = body.brand_colors[0]
    secondary = body.brand_colors[1] if len(body.brand_colors) > 1 else hls_to_hex(h, max(0.1, l - 0.15), s)
    accent = hls_to_hex((h + 0.08) % 1.0, min(0.6, l + 0.1), min(1.0, s + 0.1))

    # Light/dark variants
    is_dark_vibe = body.brand_vibe in ("bold", "tech")
    background = "#0F172A" if is_dark_vibe else "#FFFFFF"
    surface = "#1E293B" if is_dark_vibe else "#F8FAFC"
    text = "#F8FAFC" if is_dark_vibe else "#0F172A"
    text_secondary = "#94A3B8" if is_dark_vibe else "#475569"

    # Chart colors: rotate hue for variety
    chart_colors = [primary]
    for i in range(1, 8):
        ch = (h + i * 0.125) % 1.0
        chart_colors.append(hls_to_hex(ch, 0.5, 0.7))

    # Font selection via LLM (quick task)
    font_map = {
        "modern": {"heading": "Inter", "body": "Inter"},
        "classic": {"heading": "Libre Baskerville", "body": "Lato"},
        "playful": {"heading": "Poppins", "body": "Open Sans"},
        "technical": {"heading": "Space Grotesk", "body": "JetBrains Mono"},
    }
    fonts = font_map.get(body.font_preference, font_map["modern"])

    # Build and save theme
    theme_id = str(ObjectId())
    vibe = body.brand_vibe.title()
    doc = {
        "_id": theme_id,
        "name": f"Custom {vibe} Theme",
        "type": ThemeType.GENERATED.value,
        "colors": {
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "background": background,
            "surface": surface,
            "text": text,
            "text_secondary": text_secondary,
            "muted": "#94A3B8",
            "chart_colors": chart_colors,
        },
        "fonts": {**fonts, "code": "JetBrains Mono"},
        "user_id": user["user_id"],
        "generated_from": {
            "brand_colors": body.brand_colors,
            "brand_vibe": body.brand_vibe,
            "font_preference": body.font_preference,
        },
        "created_at": datetime.utcnow(),
    }
    await db.themes.insert_one(doc)
    return _doc_to_response(doc)


@router.put("/presentations/{presentation_id}/theme")
async def apply_theme_to_presentation(
    presentation_id: str,
    theme_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    pres = await db.presentations.find_one({"_id": presentation_id, "user_id": user["user_id"]})
    if not pres:
        raise HTTPException(status_code=404, detail="Presentation not found")

    theme = await db.themes.find_one({"_id": theme_id})
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    await db.presentations.update_one(
        {"_id": presentation_id},
        {"$set": {"theme_id": theme_id, "updated_at": datetime.utcnow()}},
    )
    return {"status": "theme_applied", "theme_id": theme_id}


@router.get("/visual-directions")
async def list_visual_directions() -> list[dict]:
    """Return curated visual directions for the design picker.
    Each direction is a fully-specified design system — one click
    gives the user a complete, coherent visual identity.
    Inspired by Open Design's deterministic direction approach."""
    from app.services.v4.design_resolver import get_visual_directions_list
    return get_visual_directions_list()


@router.get("/v2/visual-directions")
async def list_visual_directions_v2() -> list[dict]:
    """Compatibility endpoint for the v2 frontend theme picker."""
    return await list_visual_directions()


@router.post("/visual-directions/{direction_id}/resolve")
async def resolve_direction_tokens(direction_id: str) -> dict:
    """Resolve a visual direction into complete design tokens.
    Frontend uses this to preview what the direction will look like
    before committing to it."""
    from app.services.v4.design_resolver import resolve_from_direction, VISUAL_DIRECTIONS
    if direction_id not in VISUAL_DIRECTIONS:
        raise HTTPException(status_code=404, detail=f"Direction '{direction_id}' not found")
    tokens = resolve_from_direction(direction_id)
    return tokens.to_dict()


@router.get("/{theme_id}")
async def get_theme(
    theme_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> ThemeResponse:
    doc = await db.themes.find_one({"_id": theme_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Theme not found")
    return _doc_to_response(doc)


# ═══════════════════════════════════════════════════════════════════
# V2 THEME ENGINE ENDPOINTS (100+ themes)
# ═══════════════════════════════════════════════════════════════════

@router.get("/v2/categories")
async def list_theme_categories() -> list[dict]:
    """Return all theme categories with metadata."""
    from app.services.v4.theme_engine import ThemeEngine
    engine = ThemeEngine()
    return engine.get_categories()


@router.get("/v2/themes")
async def list_themes_v2(
    category: str | None = None,
    dark_only: bool = False,
    light_only: bool = False,
) -> list[dict]:
    """Return all themes, optionally filtered by category or mode."""
    from app.services.v4.theme_engine import ThemeEngine
    engine = ThemeEngine()

    if category:
        themes = engine.get_by_category(category)
    else:
        themes = engine.get_all()

    result = []
    for t in themes:
        if dark_only and not t.is_dark:
            continue
        if light_only and t.is_dark:
            continue
        result.append(_theme_v2_payload(t))
    return result


@router.get("/v2/themes/{theme_id}")
async def get_theme_v2(theme_id: str) -> dict:
    """Return a single theme by ID."""
    from app.services.v4.theme_engine import ThemeEngine
    engine = ThemeEngine()
    t = engine.get(theme_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    return _theme_v2_payload(t)


@router.get("/v2/search")
async def search_themes_v2(q: str) -> list[dict]:
    """Search themes by name, description, tag, or category."""
    from app.services.v4.theme_engine import ThemeEngine
    engine = ThemeEngine()
    themes = engine.search(q)
    return [_theme_v2_payload(t) for t in themes]


@router.get("/v2/recommend")
async def recommend_themes_v2(
    purpose: str | None = None,
    industry: str | None = None,
) -> list[dict]:
    """Recommend themes based on deck purpose and industry."""
    from app.services.v4.theme_engine import ThemeEngine
    engine = ThemeEngine()
    themes = engine.recommend(purpose=purpose, industry=industry)
    return [_theme_v2_payload(t) for t in themes]


@router.post("/v2/{theme_id}/resolve")
async def resolve_theme_tokens(theme_id: str) -> dict:
    """Resolve a theme into complete design tokens for preview."""
    from app.services.v4.theme_engine import ThemeEngine
    engine = ThemeEngine()
    tokens_dict = engine.resolve_theme(theme_id)
    if not tokens_dict:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    from app.services.v4.design_resolver import _resolve_from_theme_dict
    tokens = _resolve_from_theme_dict(tokens_dict)
    return tokens.to_dict()


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/v2/templates/categories")
async def list_template_categories() -> list[dict]:
    """Return all template categories with metadata."""
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()
    return engine.get_categories()


@router.get("/v2/templates")
async def list_templates_v2(
    category: str | None = None,
) -> list[dict]:
    """Return all templates, optionally filtered by category."""
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()

    if category:
        templates = engine.get_by_category(category)
    else:
        templates = engine.get_all()

    return [t.to_dict() for t in templates]


@router.get("/v2/templates/search")
async def search_templates_v2(q: str) -> list[dict]:
    """Search templates by name, description, tag, or category."""
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()
    templates = engine.search(q)
    return [t.to_dict() for t in templates]


@router.get("/v2/templates/recommend")
async def recommend_templates_v2(
    purpose: str | None = None,
    industry: str | None = None,
    slide_count: int | None = None,
) -> list[dict]:
    """Recommend templates based on purpose, industry, and slide count."""
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()
    templates = engine.recommend(purpose=purpose, industry=industry, slide_count=slide_count)
    return [t.to_dict() for t in templates]


@router.get("/v2/templates/{template_id}")
async def get_template_v2(template_id: str) -> dict:
    """Return a single template by ID."""
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()
    t = engine.get(template_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return t.to_dict()


@router.get("/v2/templates/{template_id}/validate")
async def validate_template_slide_count(template_id: str, slide_count: int) -> dict:
    """Validate that a slide count is compatible with a template."""
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()
    valid, message = engine.validate_slide_count(template_id, slide_count)
    return {"valid": valid, "message": message}


@router.get("/v2/visual-systems")
async def list_visual_systems() -> list[dict]:
    """Return curated visual systems pairing templates with token sets.

    A visual system is a deck personality the user can pick instead of a
    single template — e.g. "YC Canon" pairs the YC application,
    demo-day, partner-meeting, and classic templates with
    minimal_dark + swiss_editorial directions for a coherent
    typography + palette feel across the whole deck. Backed by
    ``barise_templates_v29.json::_visual_systems``.
    """
    from app.services.v4.template_engine import TemplateEngine
    engine = TemplateEngine()
    return engine.get_visual_systems()
