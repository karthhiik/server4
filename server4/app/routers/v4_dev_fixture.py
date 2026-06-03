"""
V4 Dev Fixture Router — seed a real, editable project from a pre-built
`slides` JSON payload (typically the `full_slides` array from a successful
test run, e.g. `standard_mode_test_output.json`).

This skips:
  - research (Tavily/Exa/Firecrawl)
  - skeleton planning (LLM)
  - parallel writers (LLM)
  - critic (LLM)
  - image generation (paid image APIs)

…and goes straight to:
  - design token resolution (real theme lookup)
  - compile_slides (real JSX kit + design tokens)
  - persist to `db.presentations` + `db.slides` (real schema)

The resulting project_id can be opened in the existing editor surface,
PATCH'd via `/api/v4/projects/{id}/slides/{n}`, regenerated, exported to
PPTX — everything works because we hit the same persistence shape that
the real pipeline writes.

Endpoints (all gated behind `settings.ENABLE_DEV_ROUTES`):
  POST /api/v4/dev/seed-from-fixture
       Body: { slides: [GeneratedSlide-shaped dicts], theme_id?, deck_title?,
               purpose?, company_name?, industry? }
       Returns: { project_id, slide_count, compiled, design_tokens, theme_id }

  POST /api/v4/dev/seed-from-file
       Body: { file_path: str, theme_id?, deck_title?, ... }
       Reads a JSON file from `server4/` root and extracts `full_slides`
       (or `slides`, or top-level list). Same response shape.

  GET  /api/v4/dev/fixtures
       Lists JSON files in `server4/` root that look like fixture dumps
       (have `full_slides` or `slides` keys, slide_count > 0).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.config import settings
from app.database import get_db
from app.dependencies import optional_auth
from app.services.v4.design_resolver import resolve_design_tokens
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.slide_compiler import compile_slides

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v4/dev", tags=["v4-dev"])


# ── Schemas ────────────────────────────────────────────────────────


class SeedFromFixtureBody(BaseModel):
    """Direct seed: caller supplies the slide list inline."""
    slides: list[dict[str, Any]] = Field(..., min_length=1, max_length=60)
    theme_id: Optional[str] = None
    deck_title: Optional[str] = None
    purpose: str = "pitch_deck"
    mode: str = "standard"
    company_name: Optional[str] = None
    industry: Optional[str] = None
    keep_image_urls: bool = Field(
        default=True,
        description=(
            "If True, image_url values present on each slide dict are kept "
            "and baked into compiled artifacts. Set False to compile a "
            "deck whose image placeholders will be filled later."
        ),
    )


class SeedFromFileBody(BaseModel):
    """Seed from a JSON file on disk. Server-side path resolved relative
    to `server4/` root for safety — no absolute paths, no path traversal."""
    file_path: str = Field(..., max_length=240)
    theme_id: Optional[str] = None
    deck_title: Optional[str] = None
    purpose: str = "pitch_deck"
    mode: str = "standard"
    company_name: Optional[str] = None
    industry: Optional[str] = None
    keep_image_urls: bool = True


# ── Helpers ────────────────────────────────────────────────────────


def _ensure_dev_enabled() -> None:
    enabled = bool(getattr(settings, "ENABLE_DEV_ROUTES", False))
    is_prod = str(getattr(settings, "ENVIRONMENT", "")).lower() == "production"
    if is_prod or not enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    return
    """Block these endpoints on prod deployments. Honours
    `settings.ENABLE_DEV_ROUTES`; falls back to True when DEBUG is set."""
    enabled = bool(getattr(settings, "ENABLE_DEV_ROUTES", None))
    if not enabled:
        enabled = bool(getattr(settings, "DEBUG", False))
    if not enabled:
        raise HTTPException(
            status_code=403,
            detail=(
                "dev fixture routes are disabled — set ENABLE_DEV_ROUTES=true "
                "or DEBUG=true in server4/.env to use them."
            ),
        )


def _server4_root() -> Path:
    # routers/v4_dev_fixture.py → routers → app → server4
    return Path(__file__).resolve().parents[2]


def _safe_resolve_fixture_path(rel: str) -> Path:
    """Resolve `rel` relative to server4/ root and ensure it stays inside.
    Prevents `../../../etc/passwd`-style traversal."""
    root = _server4_root()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="file_path must resolve inside server4/ root",
        )
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"no such file: {rel}")
    if candidate.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="only .json fixtures accepted")
    return candidate


def _extract_slide_list(doc: Any) -> list[dict[str, Any]]:
    """Find the slide array inside a fixture JSON. Supports:
      - top-level list
      - {"full_slides": [...]} (preferred: includes raw, citations, etc.)
      - {"slides": [...]}
      - {"compiled_slides": [...]} — already compiled; not for re-seeding.
    """
    if isinstance(doc, list):
        return [s for s in doc if isinstance(s, dict)]
    if not isinstance(doc, dict):
        raise HTTPException(status_code=400, detail="fixture must be a JSON list or object")
    for key in ("full_slides", "slides"):
        val = doc.get(key)
        if isinstance(val, list) and val and all(isinstance(s, dict) for s in val):
            return val
    if isinstance(doc.get("compiled_slides"), list):
        raise HTTPException(
            status_code=400,
            detail=(
                "this fixture only contains `compiled_slides` (already-compiled "
                "JSX). Use a fixture with `full_slides` or `slides` (raw "
                "GeneratedSlide shape) instead."
            ),
        )
    raise HTTPException(
        status_code=400,
        detail="could not find a slide list in the fixture (expected `full_slides` or `slides`)",
    )


def _slide_from_dict(d: dict[str, Any], default_index: int) -> GeneratedSlide:
    """Reconstruct a `GeneratedSlide` from a serialized dict. Tolerant of
    missing fields — anything absent gets the dataclass default."""
    try:
        index = int(d.get("index", default_index))
    except (TypeError, ValueError):
        index = default_index

    return GeneratedSlide(
        index=index,
        intent=str(d.get("intent") or ""),
        layout=str(d.get("layout") or ""),
        headline=str(d.get("headline") or ""),
        subheadline=d.get("subheadline") or None,
        bullets=list(d.get("bullets") or []),
        body=d.get("body") or None,
        stat_blocks=list(d.get("stat_blocks") or []),
        quote=d.get("quote") or None,
        chart=d.get("chart") or None,
        table=d.get("table") or None,
        timeline=d.get("timeline") or None,
        comparison=d.get("comparison") or None,
        diagram=d.get("diagram") or None,
        image_prompt=d.get("image_prompt") or None,
        image_url=d.get("image_url") or None,
        image_source=d.get("image_source") or None,
        image_position=d.get("image_position") or None,
        image_intent=d.get("image_intent") or None,
        speaker_notes=d.get("speaker_notes") or None,
        citations=list(d.get("citations") or []),
        raw=dict(d.get("raw") or {}),
        render_decision=d.get("render_decision") or None,
        team_members=list(d.get("team_members") or []),
        requires_user_input=bool(d.get("requires_user_input", False)),
        user_input_kind=d.get("user_input_kind") or None,
        user_input_reason=d.get("user_input_reason") or None,
        company_icon_url=d.get("company_icon_url") or None,
        rationale=str(d.get("rationale") or ""),
        purpose=str(d.get("purpose") or ""),
    )


async def _seed_project(
    *,
    db: AsyncIOMotorDatabase,
    user_id: str,
    slide_dicts: list[dict[str, Any]],
    theme_id: Optional[str],
    deck_title: Optional[str],
    purpose: str,
    mode: str,
    company_name: Optional[str],
    industry: Optional[str],
    keep_image_urls: bool,
) -> dict[str, Any]:
    """Core seed logic shared by both inline and from-file routes."""
    if not slide_dicts:
        raise HTTPException(status_code=400, detail="no slides supplied")

    # Reconstruct GeneratedSlide objects.
    slides: list[GeneratedSlide] = []
    for i, d in enumerate(slide_dicts):
        slides.append(_slide_from_dict(d, default_index=i))
    slides.sort(key=lambda s: s.index)

    # Strip image URLs if the caller wants a clean fresh-image deck.
    if not keep_image_urls:
        for s in slides:
            s.image_url = None
            s.image_source = None

    # Resolve design tokens — uses the same code path as the live pipeline.
    design_profile = {
        "theme_id": theme_id,
        "brand": None,
        "user_provided": bool(theme_id),
        "visual_direction": None,
    }
    resolved_tokens = resolve_design_tokens(
        design_profile=design_profile,
        purpose=purpose,
        industry=industry,
    )
    design_tokens_dict = resolved_tokens.to_dict()

    # Build the image_urls map from whatever URLs are present on the slides.
    image_urls_map = {
        s.index: s.image_url for s in slides if getattr(s, "image_url", None)
    }

    # Compile to JSX artifacts.
    title_for_compile = deck_title or "Dev Fixture Deck"
    compiled = compile_slides(
        slides=slides,
        image_urls=image_urls_map or None,
        deck_title=title_for_compile,
        company_icon_url=None,
    )

    # Persist presentation + slides exactly the way `generation_v4` does so
    # every existing route (GET/PATCH/recompile/regenerate/export) works
    # unmodified against the seeded project.
    project_id = str(ObjectId())
    now = datetime.now(timezone.utc)

    await db.presentations.insert_one({
        "_id": project_id,
        "user_id": user_id,
        "title": title_for_compile[:200],
        "description": f"Seeded from fixture ({len(slides)} slides)",
        "mode": mode,
        "created_from": "v4_dev_fixture",
        "theme_id": theme_id,
        "design_profile": design_profile,
        "design_tokens": design_tokens_dict,
        "compiled_slides": compiled,
        "slide_count": len(slides),
        "generation_state": "completed",
        "generation_progress": 100,
        "generation_message": "Seeded from fixture (no LLM calls).",
        "generation_error": None,
        "input_method": "fixture",
        "industry": industry,
        "company_name": company_name,
        "purpose": purpose,
        "narrative_arc": purpose,
        "intent_summary": sorted({s.intent for s in slides if s.intent}),
        "overall_score": None,
        "created_at": now,
        "updated_at": now,
    })

    # Upsert slides — same dual-key (presentation_id + project_id) the
    # router writes so v4_editor.py queries work.
    for s in slides:
        doc_set = {
            "presentation_id": project_id,
            "project_id": project_id,
            "index": s.index,
            "intent": s.intent,
            "layout": s.layout,
            "headline": s.headline,
            "subheadline": s.subheadline,
            "bullets": s.bullets,
            "body": s.body,
            "stat_blocks": s.stat_blocks,
            "quote": s.quote,
            "chart": s.chart,
            "table": s.table,
            "timeline": s.timeline,
            "comparison": s.comparison,
            "diagram": s.diagram,
            "image_prompt": s.image_prompt,
            "image_url": s.image_url,
            "image_source": s.image_source,
            "image_position": s.image_position,
            "image_intent": s.image_intent,
            "speaker_notes": s.speaker_notes,
            "citations": s.citations,
            "render_decision": s.render_decision,
            "team_members": s.team_members,
            "requires_user_input": bool(s.requires_user_input),
            "user_input_kind": s.user_input_kind,
            "user_input_reason": s.user_input_reason,
            "company_icon_url": s.company_icon_url,
            "rationale": s.rationale,
            "purpose": s.purpose or purpose,
            "raw": s.raw,
            "version": 1,
            "updated_at": now,
        }
        await db.slides.update_one(
            {"presentation_id": project_id, "index": s.index},
            {
                "$set": doc_set,
                "$setOnInsert": {"_id": str(ObjectId()), "created_at": now},
            },
            upsert=True,
        )

    logger.info(
        "v4_dev_fixture.seeded",
        project_id=project_id,
        slide_count=len(slides),
        theme_id=theme_id,
        with_images=len(image_urls_map),
    )

    return {
        "project_id": project_id,
        "slide_count": len(slides),
        "title": title_for_compile,
        "theme_id": theme_id,
        "design_tokens": design_tokens_dict,
        "compiled_slides": compiled,
        "with_images": len(image_urls_map),
        "editor_url": f"/projects/{project_id}",
    }


# ── Routes ─────────────────────────────────────────────────────────


@router.get("/fixtures")
async def list_fixtures(
    user: dict | None = Depends(optional_auth),
) -> dict[str, Any]:
    """List all JSON files in `server4/` that look like seedable fixtures.

    A file counts as seedable if it parses as JSON, is a list or has a
    `full_slides`/`slides` array, and contains at least one slide-shaped
    dict. We surface the slide count and detected schema key so the UI
    can show a useful picker.
    """
    _ensure_dev_enabled()
    root = _server4_root()
    out: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_file() or entry.suffix.lower() != ".json":
            continue
        try:
            with entry.open("r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue
        if isinstance(doc, list):
            count = sum(1 for s in doc if isinstance(s, dict))
            key = "list"
        elif isinstance(doc, dict):
            count = 0
            key = None
            for k in ("full_slides", "slides"):
                if isinstance(doc.get(k), list):
                    count = sum(1 for s in doc[k] if isinstance(s, dict))
                    key = k
                    if count > 0:
                        break
        else:
            continue
        if count > 0 and key:
            out.append({
                "file_path": entry.name,
                "schema_key": key,
                "slide_count": count,
                "size_bytes": entry.stat().st_size,
                "modified": int(entry.stat().st_mtime),
            })
    return {"count": len(out), "fixtures": out}


@router.post("/seed-from-fixture")
async def seed_from_fixture(
    body: SeedFromFixtureBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    """Seed a project from an inline `slides` payload."""
    _ensure_dev_enabled()
    user_id = user["user_id"] if user else "dev-test-user"
    return await _seed_project(
        db=db,
        user_id=user_id,
        slide_dicts=body.slides,
        theme_id=body.theme_id,
        deck_title=body.deck_title,
        purpose=body.purpose,
        mode=body.mode,
        company_name=body.company_name,
        industry=body.industry,
        keep_image_urls=body.keep_image_urls,
    )


@router.post("/seed-from-file")
async def seed_from_file(
    body: SeedFromFileBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    """Seed a project from a fixture JSON file on the server4/ disk."""
    _ensure_dev_enabled()
    user_id = user["user_id"] if user else "dev-test-user"

    path = _safe_resolve_fixture_path(body.file_path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid JSON in {body.file_path}: {e}")

    slide_dicts = _extract_slide_list(doc)
    fallback_title = body.deck_title
    if not fallback_title and isinstance(doc, dict):
        inp = doc.get("input") or {}
        if isinstance(inp, dict):
            fallback_title = (
                inp.get("title")
                or inp.get("company_name")
                or inp.get("topic")
                or path.stem.replace("_", " ").title()
            )
    return await _seed_project(
        db=db,
        user_id=user_id,
        slide_dicts=slide_dicts,
        theme_id=body.theme_id,
        deck_title=fallback_title or path.stem.replace("_", " ").title(),
        purpose=body.purpose,
        mode=body.mode,
        company_name=body.company_name,
        industry=body.industry,
        keep_image_urls=body.keep_image_urls,
    )
