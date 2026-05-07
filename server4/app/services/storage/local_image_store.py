"""
Local image store for slide images.

Founder Plan-v5 (Apr 2026): the previous design uploaded every generated
slide image to Azure Blob Storage and emitted a SAS-signed HTTPS URL into
`compiled_slides[i].kit_jsx.props_json.imageUrl`. In the field this broke
in three ways:

  1. SAS expiry mismatches between the upload-time clock and the user's
     browser clock surfaced as "broken image" icons days after generation.
  2. Cross-origin <img> loads through the sandboxed iframe occasionally
     hit Azure's referrer / CORS heuristics depending on the storage
     account's policy, again rendering as broken images.
  3. Operators without Azure credentials configured (local dev, CI) had
     no rendered images at all even though `image_pipeline_router`
     successfully produced bytes.

This module persists image bytes to a local directory under
`server4/uploads/slide_images/{project_id}/{slide_id}.png` and returns an
absolute HTTP URL served by the FastAPI app itself. Same-origin to the
API, deterministic, no signing, no expiry, no CORS headache. Azure Blob
upload remains available as an optional backup tier (see
`image_generator._upload_to_blob`) but is never the primary path.

The store is intentionally tiny: one writer, one resolver. The router at
`app/routers/v4_images.py` streams the file with `Cache-Control: public,
max-age=31536000, immutable` since the slide_id is content-addressable
within a project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import structlog

from app.config import settings

logger = structlog.get_logger()


# Resolve once. `server4/uploads/slide_images/`. Created on demand.
_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
_STORE_DIR: Final[Path] = _PROJECT_ROOT / "uploads" / "slide_images"


def _public_base_url() -> str:
    """Absolute base URL the sandbox iframe can hit. Env override
    (`PUBLIC_BASE_URL`) wins; otherwise fall back to API_HOST/API_PORT."""
    explicit = getattr(settings, "PUBLIC_BASE_URL", "") or ""
    if explicit:
        return _validated_public_base_url(explicit.rstrip("/"))
    host = getattr(settings, "API_HOST", "0.0.0.0") or "127.0.0.1"
    # `0.0.0.0` is a bind address, not a routable URL host.
    if host in ("0.0.0.0", "::", ""):
        host = "127.0.0.1"
    port = getattr(settings, "API_PORT", 8003) or 8003
    return _validated_public_base_url(f"http://{host}:{port}")


def _is_local_environment() -> bool:
    env = str(getattr(settings, "ENVIRONMENT", "development") or "development").lower()
    return env in {"dev", "development", "local", "test", "testing"}


def _validated_public_base_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    local_hosts = {"127.0.0.1", "localhost", "0.0.0.0", "::1", ""}
    if _is_local_environment():
        return url
    if parsed.scheme != "https" or host in local_hosts:
        logger.error(
            "local_image_store_public_base_url_invalid",
            environment=getattr(settings, "ENVIRONMENT", ""),
            scheme=parsed.scheme,
            host=host,
        )
        raise RuntimeError("PUBLIC_BASE_URL must be a public HTTPS URL outside local development")
    return url


def store_dir_for_project(project_id: str) -> Path:
    """Return the on-disk directory for a project's slide images,
    creating it if necessary. Project IDs are sanitised to a flat string
    so they are safe to use as a directory name."""
    safe = "".join(ch for ch in str(project_id) if ch.isalnum() or ch in ("-", "_"))
    if not safe:
        safe = "unknown"
    d = _STORE_DIR / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def store_image(*, project_id: str, slide_id: str, image_bytes: bytes) -> str:
    """Write `image_bytes` to disk and return a same-origin absolute URL.

    Filename is `{slide_id}.png`. We assume PNG because every tier of
    the image pipeline (Azure Flux, NVIDIA SD3, Cloudflare Phoenix /
    Lucid, gradient SVG fallback) emits PNG-compatible bytes. The
    fallback gradient is actually SVG but the router rasterises it
    before returning, so PNG is correct for all live tiers.
    """
    safe_slide = "".join(
        ch for ch in str(slide_id) if ch.isalnum() or ch in ("-", "_")
    )
    if not safe_slide:
        safe_slide = "slide"

    target = store_dir_for_project(project_id) / f"{safe_slide}.png"
    try:
        target.write_bytes(image_bytes)
    except Exception as e:  # pragma: no cover — disk full / permission
        logger.error(
            "local_image_store_write_failed",
            project_id=project_id,
            slide_id=slide_id,
            path=str(target),
            error=str(e),
        )
        raise

    url = f"{_public_base_url()}/api/v4/images/{project_id}/{safe_slide}.png"
    logger.info(
        "local_image_stored",
        project_id=project_id,
        slide_id=slide_id,
        bytes=len(image_bytes),
        url=url,
    )
    return url


def resolve_path(project_id: str, filename: str) -> Path | None:
    """Return the on-disk path for a stored image, or None if it does not
    resolve safely under the store directory. Guards against path
    traversal — the resolved path must be inside `_STORE_DIR`."""
    safe_proj = "".join(
        ch for ch in str(project_id) if ch.isalnum() or ch in ("-", "_")
    )
    safe_name = "".join(
        ch for ch in str(filename) if ch.isalnum() or ch in ("-", "_", ".")
    )
    if not safe_proj or not safe_name or ".." in safe_name:
        return None

    candidate = (_STORE_DIR / safe_proj / safe_name).resolve()
    try:
        candidate.relative_to(_STORE_DIR.resolve())
    except ValueError:
        return None

    if not candidate.is_file():
        return None
    return candidate
