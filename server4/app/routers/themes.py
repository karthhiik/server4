"""Theme management — list, generate, apply."""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
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


@router.get("")
async def list_themes(
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[ThemeResponse]:
    cursor = db.themes.find({}).sort("name", 1)
    docs = await cursor.to_list(50)
    return [_doc_to_response(d) for d in docs]


@router.get("/{theme_id}")
async def get_theme(
    theme_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> ThemeResponse:
    doc = await db.themes.find_one({"_id": theme_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Theme not found")
    return _doc_to_response(doc)


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
