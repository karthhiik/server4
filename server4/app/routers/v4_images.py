"""
V4 slide image static-serving route.

Founder Plan-v5 (Apr 2026): every generated slide image is persisted to
the local store (`app/services/storage/local_image_store.py`) and served
from this route. Same-origin to the API, no SAS expiry, no Azure CORS
quirks. Cache-Control is `immutable` because filenames are stable per
(project_id, slide_id) and overwriting is intentional — clients should
re-fetch on a fresh URL only when the writer regenerates the slide
(which produces a new slide_id segment in `compiled_slides[i]`).
"""

from __future__ import annotations

import hashlib
import html
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from app.services.storage.local_image_store import resolve_path

router = APIRouter(prefix="/api/v4/images", tags=["v4-images"])

_TEMPLATE_PREVIEW_DIR = Path(__file__).resolve().parents[2] / "uploads" / "template_previews"
_FALLBACK_PALETTES = (
    ("#05070d", "#c8ff00", "#1f2a44"),
    ("#071426", "#00d9ff", "#223a5f"),
    ("#120a1f", "#8b5cf6", "#22d3ee"),
    ("#111111", "#f7c948", "#3a2b10"),
    ("#f8fafc", "#e11d48", "#0f172a"),
    ("#061b18", "#34d399", "#0ea5e9"),
)


def _safe_preview_name(filename: str) -> str:
    safe_name = "".join(ch for ch in filename if ch.isalnum() or ch in ("-", "_", "."))
    if not safe_name or ".." in safe_name:
        raise HTTPException(status_code=400, detail="invalid_filename")
    return safe_name


def _fallback_template_preview(filename: str) -> Response:
    digest = hashlib.sha256(filename.encode("utf-8")).hexdigest()
    palette = _FALLBACK_PALETTES[int(digest[:2], 16) % len(_FALLBACK_PALETTES)]
    background, accent, secondary = palette
    title = filename.rsplit(".", 1)[0].replace("_preview", "").replace("_", " ").replace("-", " ")
    title = html.escape(title.title())
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{background}"/>
      <stop offset="0.62" stop-color="{secondary}"/>
      <stop offset="1" stop-color="{accent}" stop-opacity="0.72"/>
    </linearGradient>
    <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
      <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#ffffff" stroke-opacity="0.08" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <rect width="1600" height="900" fill="url(#grid)"/>
  <rect x="92" y="96" width="1416" height="708" rx="28" fill="#000000" fill-opacity="0.18" stroke="#ffffff" stroke-opacity="0.24"/>
  <rect x="132" y="140" width="96" height="10" fill="{accent}"/>
  <text x="132" y="210" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="700" letter-spacing="8" fill="{accent}">BARISE TEMPLATE</text>
  <text x="132" y="378" font-family="Inter, Arial, sans-serif" font-size="88" font-weight="800" fill="#ffffff">{title}</text>
  <rect x="132" y="490" width="520" height="18" rx="9" fill="#ffffff" fill-opacity="0.72"/>
  <rect x="132" y="538" width="760" height="12" rx="6" fill="#ffffff" fill-opacity="0.42"/>
  <rect x="132" y="578" width="620" height="12" rx="6" fill="#ffffff" fill-opacity="0.32"/>
  <rect x="1050" y="188" width="330" height="420" rx="22" fill="#ffffff" fill-opacity="0.12" stroke="#ffffff" stroke-opacity="0.18"/>
  <circle cx="1138" cy="298" r="38" fill="{accent}" fill-opacity="0.82"/>
  <rect x="1100" y="382" width="220" height="16" rx="8" fill="#ffffff" fill-opacity="0.78"/>
  <rect x="1100" y="430" width="170" height="12" rx="6" fill="#ffffff" fill-opacity="0.42"/>
  <rect x="1100" y="472" width="238" height="12" rx="6" fill="#ffffff" fill-opacity="0.34"/>
</svg>"""
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*",
            "X-Barise-Preview-Fallback": "1",
        },
    )


@router.get("/template-previews/{filename}")
async def get_template_preview(filename: str) -> Response:
    """Serve pre-generated template preview background images.

    These are created once via `scripts/generate_template_previews.py`
    and stored in `uploads/template_previews/`. Immutable cache because
    the filenames are stable (e.g. `yc_pitch_preview.jpg`).
    """
    safe_name = _safe_preview_name(filename)
    candidate = (_TEMPLATE_PREVIEW_DIR / safe_name).resolve()
    try:
        candidate.relative_to(_TEMPLATE_PREVIEW_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="image_not_found")
    if not candidate.is_file():
        return _fallback_template_preview(safe_name)
    ext = candidate.suffix.lower()
    media = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    return FileResponse(
        path=str(candidate),
        media_type=media,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/{project_id}/{filename}")
async def get_slide_image(project_id: str, filename: str) -> Response:
    path = resolve_path(project_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="image_not_found")
    return FileResponse(
        path=str(path),
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=31536000",
            "Access-Control-Allow-Origin": "*",
        },
    )

