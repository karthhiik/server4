from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from app.core.config import get_settings
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from chibi_renderer import render_chibi_svg

settings = get_settings()

DEFAULT_STYLE_KEY = "barise-chibi-v2"


def normalize_avatar_url(value: str | None) -> str | None:
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("data:image/") or raw.startswith("blob:"):
        return raw

    base = settings.COMMUNITY_ASSET_BASE_URL.rstrip("/")
    if raw.startswith("/uploads/"):
        return f"{base}{raw}"
    if raw.startswith("uploads/"):
        return f"{base}/{raw}"
    return f"{base}/uploads/{raw.lstrip('/')}"


def _normalize_variant(variant: str | None) -> str:
    if variant in {"male", "female", "neutral"}:
        return variant
    return "neutral"


def _next_avatar_version(user_doc: dict[str, Any]) -> int:
    avatar = user_doc.get("avatar", {}) if isinstance(user_doc.get("avatar"), dict) else {}
    try:
        return int(avatar.get("version", 0)) + 1
    except Exception:
        return 1


def _safe_seed(user_doc: dict[str, Any]) -> str:
    avatar = user_doc.get("avatar", {}) if isinstance(user_doc.get("avatar"), dict) else {}
    return str(
        avatar.get("seed") or user_doc.get("user_id") or user_doc.get("username") or "unknown-user"
    ).lower()


def _scalar_options(options: dict[str, Any] | None) -> dict[str, str]:
    if not options:
        return {}

    out: dict[str, str] = {}
    for key, value in options.items():
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            out[key] = str(value[0])
        else:
            out[key] = str(value)
    return out


def resolve_user_avatar(user_doc: dict[str, Any]) -> dict[str, Any]:
    avatar = user_doc.get("avatar", {}) if isinstance(user_doc.get("avatar"), dict) else {}
    user_id = str(user_doc.get("user_id") or "")
    version = _next_avatar_version(user_doc) - 1
    if version <= 0:
        version = 1

    variant = _normalize_variant(avatar.get("variant"))

    assets = avatar.get("assets", {}) if isinstance(avatar.get("assets"), dict) else {}
    full_url = normalize_avatar_url(assets.get("full_url"))
    thumb_url = normalize_avatar_url(assets.get("thumb_url"))
    source = str(avatar.get("source") or "")

    if full_url and source in {"uploaded", "generated"}:
        return {
            "user_id": user_id,
            "url": full_url,
            "thumb_url": thumb_url or full_url,
            "type": source,
            "variant": variant,
            "version": version,
            "updated_at": avatar.get("updated_at"),
        }

    legacy_photo = normalize_avatar_url(user_doc.get("photo"))
    if legacy_photo:
        return {
            "user_id": user_id,
            "url": legacy_photo,
            "thumb_url": legacy_photo,
            "type": "uploaded",
            "variant": variant,
            "version": version,
            "updated_at": user_doc.get("lastUpdated"),
        }

    seed = _safe_seed(user_doc)
    chibi_svg = render_chibi_svg(seed, variant)
    fallback = f"data:image/svg+xml;utf8,{quote(chibi_svg)}"
    return {
        "user_id": user_id,
        "url": fallback,
        "thumb_url": fallback,
        "type": "fallback",
        "variant": variant,
        "version": version,
        "updated_at": user_doc.get("lastUpdated"),
    }


def build_avatar_document_for_update(
    *,
    user_doc: dict[str, Any],
    avatar_url: str,
    variant: str | None = None,
    style_key: str | None = None,
    options: dict[str, Any] | None = None,
    source: str = "generated",
) -> dict[str, Any]:
    normalized_variant = _normalize_variant(variant)
    version = _next_avatar_version(user_doc)
    resolved = normalize_avatar_url(avatar_url) or avatar_url

    option_seed = _scalar_options(options).get("seed")
    return {
        "source": source,
        "variant": normalized_variant,
        "style_key": style_key or DEFAULT_STYLE_KEY,
        "seed": (option_seed or _safe_seed(user_doc)).lower(),
        "options": _scalar_options(options),
        "version": version,
        "assets": {
            "full_url": resolved,
            "thumb_url": resolved,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_avatar_event_payload(user_id: str, resolved_avatar: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "avatar.updated.v2",
        "user_id": user_id,
        "avatar_version": resolved_avatar.get("version", 1),
        "resolved_thumb_url": resolved_avatar.get("thumb_url", resolved_avatar.get("url")),
        "resolved_url": resolved_avatar.get("url"),
        "source": resolved_avatar.get("type"),
        "variant": resolved_avatar.get("variant"),
        "updated_at": resolved_avatar.get("updated_at"),
    }
