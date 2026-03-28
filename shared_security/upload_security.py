from __future__ import annotations

import hashlib
import io
import mimetypes
import os
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


SAFE_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
SAFE_VIDEO_EXTENSIONS = frozenset({".mp4", ".webm"})
SAFE_AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".ogg", ".m4a", ".webm"})
SAFE_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".docx", ".pptx", ".txt", ".csv"})
SAFE_CHAT_FILE_EXTENSIONS = (
    SAFE_IMAGE_EXTENSIONS
    | SAFE_VIDEO_EXTENSIONS
    | SAFE_AUDIO_EXTENSIONS
    | SAFE_DOCUMENT_EXTENSIONS
)

MIME_BY_EXTENSION: dict[str, frozenset[str]] = {
    ".jpg": frozenset({"image/jpeg"}),
    ".jpeg": frozenset({"image/jpeg"}),
    ".png": frozenset({"image/png"}),
    ".webp": frozenset({"image/webp"}),
    ".mp4": frozenset({"video/mp4"}),
    ".webm": frozenset({"video/webm", "audio/webm"}),
    ".mp3": frozenset({"audio/mpeg", "audio/mp3"}),
    ".wav": frozenset({"audio/wav", "audio/x-wav", "audio/wave"}),
    ".ogg": frozenset({"audio/ogg"}),
    ".m4a": frozenset({"audio/mp4", "audio/x-m4a"}),
    ".pdf": frozenset({"application/pdf"}),
    ".docx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
    ),
    ".pptx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }
    ),
    ".txt": frozenset({"text/plain"}),
    ".csv": frozenset({"text/csv", "application/csv", "text/plain"}),
    ".svg": frozenset({"image/svg+xml"}),
}

INLINE_SAFE_EXTENSIONS = (
    SAFE_IMAGE_EXTENSIONS
    | SAFE_VIDEO_EXTENSIONS
    | SAFE_AUDIO_EXTENSIONS
    | frozenset({".svg"})
)

MP4_BRANDS_AUDIO = {
    b"M4A ",
    b"M4B ",
    b"M4P ",
}
OOXML_WORD_MARKERS = ("word/", "docProps/", "[Content_Types].xml")
OOXML_PPT_MARKERS = ("ppt/", "docProps/", "[Content_Types].xml")


class UploadSecurityError(ValueError):
    """Raised when an upload violates the shared security policy."""


@dataclass(frozen=True)
class ValidatedUpload:
    safe_filename: str
    extension: str
    detected_mime: str
    size_bytes: int
    sha256: str


def sanitize_user_filename(filename: str, *, default_stem: str = "upload") -> str:
    candidate = os.path.basename((filename or "").replace("\x00", "").strip())
    if not candidate:
        return default_stem

    invalid_chars = set('\\/:*?"<>|\r\n\t')
    cleaned = "".join("_" if ch in invalid_chars else ch for ch in candidate)
    stem, extension = os.path.splitext(cleaned)
    stem = (stem or default_stem).strip(" .") or default_stem
    stem = stem[:120]
    extension = extension.lower()[:16]
    return f"{stem}{extension}"


def normalize_extension(filename: str) -> str:
    return os.path.splitext(sanitize_user_filename(filename))[1].lower()


def safe_relative_upload_path(path_value: str) -> str:
    normalized = (path_value or "").replace("\\", "/").strip().lstrip("/")
    candidate = PurePosixPath(normalized)
    if not normalized or candidate.is_absolute():
        raise UploadSecurityError("Invalid upload path.")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise UploadSecurityError("Invalid upload path.")
    return str(candidate)


def resolve_upload_path(root: str | Path, relative_path: str) -> Path:
    safe_relative = safe_relative_upload_path(relative_path)
    root_path = Path(root).resolve()
    target = (root_path / safe_relative).resolve()
    try:
        target.relative_to(root_path)
    except ValueError as exc:
        raise UploadSecurityError("Resolved upload path escapes the upload root.") from exc
    return target


def build_storage_name(prefix: str, extension: str) -> str:
    normalized_extension = (extension or "").lower()
    if normalized_extension and not normalized_extension.startswith("."):
        normalized_extension = f".{normalized_extension}"
    return f"{prefix}_{uuid.uuid4().hex}{normalized_extension}"


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _looks_like_text(payload: bytes) -> bool:
    if not payload:
        return False
    if b"\x00" in payload:
        return False
    sample = payload[:4096]
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            sample.decode("utf-8-sig")
        except UnicodeDecodeError:
            return False
    return True


def _read_zip_members(payload: bytes) -> tuple[str, ...]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            return tuple(archive.namelist())
    except Exception as exc:
        raise UploadSecurityError("Invalid OOXML container.") from exc


def detect_mime_candidates(payload: bytes, *, extension: str | None = None) -> set[str]:
    candidates: set[str] = set()

    if payload.startswith(b"\xff\xd8\xff"):
        return {"image/jpeg"}
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return {"image/png"}
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return {"image/webp"}
    if payload.startswith(b"%PDF-"):
        return {"application/pdf"}
    if payload.startswith(b"GIF87a") or payload.startswith(b"GIF89a"):
        return {"image/gif"}
    if payload.startswith(b"OggS"):
        return {"audio/ogg"}
    if payload[:4] == b"RIFF" and payload[8:12] == b"WAVE":
        return {"audio/wav", "audio/x-wav", "audio/wave"}
    if payload.startswith(b"ID3") or (
        len(payload) >= 2 and payload[0] == 0xFF and (payload[1] & 0xE0) == 0xE0
    ):
        return {"audio/mpeg", "audio/mp3"}
    if payload.startswith(b"\x1a\x45\xdf\xa3"):
        return {"video/webm", "audio/webm"}

    if len(payload) >= 12 and payload[4:8] == b"ftyp":
        brand = payload[8:12]
        if extension == ".m4a" or brand in MP4_BRANDS_AUDIO:
            candidates.update({"audio/mp4", "audio/x-m4a"})
        else:
            candidates.add("video/mp4")
        return candidates

    if payload.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        members = _read_zip_members(payload)
        if extension == ".docx" and any(
            member.startswith(OOXML_WORD_MARKERS[0]) for member in members
        ):
            return {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/zip",
            }
        if extension == ".pptx" and any(
            member.startswith(OOXML_PPT_MARKERS[0]) for member in members
        ):
            return {
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "application/zip",
            }
        return {"application/zip"}

    if extension in {".txt", ".csv"} and _looks_like_text(payload):
        return {"text/plain", "text/csv", "application/csv"}

    guessed, _ = mimetypes.guess_type(f"file{extension or ''}")
    if guessed:
        return {guessed.lower()}

    return set()


def validate_upload_payload(
    *,
    filename: str,
    payload: bytes,
    max_bytes: int,
    allowed_extensions: Iterable[str],
    declared_mime_type: str | None = None,
) -> ValidatedUpload:
    safe_filename = sanitize_user_filename(filename)
    extension = normalize_extension(safe_filename)
    normalized_allowed_extensions = {ext.lower() for ext in allowed_extensions}

    if extension not in normalized_allowed_extensions:
        raise UploadSecurityError("Unsupported file type.")
    if not payload:
        raise UploadSecurityError("Uploaded file is empty.")
    if len(payload) > max_bytes:
        raise UploadSecurityError("Uploaded file exceeds the allowed size.")

    detected_candidates = detect_mime_candidates(payload, extension=extension)
    allowed_mimes = MIME_BY_EXTENSION.get(extension, frozenset())
    if not detected_candidates or (
        allowed_mimes and detected_candidates.isdisjoint(allowed_mimes)
    ):
        raise UploadSecurityError("Uploaded file content does not match its extension.")

    compatible_candidates = sorted(
        mime
        for mime in detected_candidates
        if not allowed_mimes or mime in allowed_mimes
    ) or sorted(detected_candidates)

    declared_mime = (declared_mime_type or "").split(";", 1)[0].strip().lower()
    ooxml_zip_declared = (
        extension in {".docx", ".pptx"}
        and declared_mime == "application/zip"
        and bool(compatible_candidates)
    )
    if declared_mime and allowed_mimes and declared_mime not in allowed_mimes and not ooxml_zip_declared:
        raise UploadSecurityError("Declared MIME type is not allowed for this file.")

    if declared_mime and declared_mime in compatible_candidates:
        detected_mime = declared_mime
    else:
        detected_mime = compatible_candidates[0]

    return ValidatedUpload(
        safe_filename=safe_filename,
        extension=extension,
        detected_mime=detected_mime,
        size_bytes=len(payload),
        sha256=sha256_hex(payload),
    )


def build_download_headers(
    *,
    filename: str | None = None,
    inline: bool = False,
    no_store: bool = False,
) -> dict[str, str]:
    headers = {"X-Content-Type-Options": "nosniff"}
    if filename:
        disposition = "inline" if inline else "attachment"
        headers["Content-Disposition"] = f'{disposition}; filename="{sanitize_user_filename(filename)}"'
    if no_store:
        headers["Cache-Control"] = "private, no-store"
    return headers


def is_inline_safe_extension(filename: str) -> bool:
    return normalize_extension(filename) in INLINE_SAFE_EXTENSIONS
