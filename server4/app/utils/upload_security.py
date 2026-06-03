"""Shared upload security checks for Server4 public upload endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, UploadFile


_MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".docx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".zip": (b"PK\x03\x04",),
}

_TEXT_EXTS = {".txt", ".md", ".csv"}


def _upload_error(code: str, message: str, status: int, **extra: object) -> HTTPException:
    detail = {"code": code, "message": message}
    detail.update({k: v for k, v in extra.items() if v is not None})
    return HTTPException(status_code=status, detail=detail)


def _looks_like_svg(raw: bytes) -> bool:
    sample = raw[:512].lstrip().lower()
    return sample.startswith(b"<svg") or (sample.startswith(b"<?xml") and b"<svg" in sample)


def _looks_like_json(raw: bytes) -> bool:
    return raw[:512].lstrip().startswith((b"{", b"["))


def _looks_like_text(raw: bytes) -> bool:
    try:
        raw[:4096].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _matches_magic(ext: str, raw: bytes) -> bool:
    if ext == ".svg":
        return _looks_like_svg(raw)
    if ext == ".json":
        return _looks_like_json(raw)
    if ext in _TEXT_EXTS:
        return _looks_like_text(raw)
    if ext == ".webp":
        return raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
    prefixes = _MAGIC_PREFIXES.get(ext)
    if not prefixes:
        return True
    return any(raw.startswith(prefix) for prefix in prefixes)


async def enforce_upload_constraints(
    file: UploadFile,
    *,
    allowed_exts: Iterable[str],
    max_bytes: int,
    scan_magic: bool = True,
) -> bytes:
    """Validate extension, size, and signature; return bytes with stream rewound."""

    if not file.filename:
        raise _upload_error("upload_filename_required", "A filename is required.", 400)

    allowed = {str(ext).lower() for ext in allowed_exts}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise _upload_error(
            "upload_invalid_file_type",
            f"Unsupported file type {ext or '(none)'}.",
            400,
            allowed=sorted(allowed),
            extension=ext,
        )

    raw = await file.read(max_bytes + 1)
    try:
        await file.seek(0)
    except Exception:
        pass

    if not raw:
        raise _upload_error("upload_empty_file", "The uploaded file is empty.", 400)
    if len(raw) > max_bytes:
        raise _upload_error(
            "upload_file_too_large",
            f"File exceeds the {max_bytes} byte limit.",
            413,
            max_bytes=max_bytes,
        )

    if scan_magic and not _matches_magic(ext, raw):
        raise _upload_error(
            "upload_invalid_file_type",
            "The uploaded file contents do not match its extension.",
            400,
            extension=ext,
        )

    return raw
