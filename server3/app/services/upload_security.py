from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from shared_security.upload_security import (  # noqa: E402
    MIME_BY_EXTENSION,
    SAFE_AUDIO_EXTENSIONS,
    SAFE_CHAT_FILE_EXTENSIONS,
    SAFE_DOCUMENT_EXTENSIONS,
    SAFE_IMAGE_EXTENSIONS,
    SAFE_VIDEO_EXTENSIONS,
    UploadSecurityError,
    ValidatedUpload,
    normalize_extension,
    sanitize_user_filename,
    validate_upload_payload,
)

MAX_CHAT_IMAGE_BYTES = 10 * 1024 * 1024
MAX_CHAT_AUDIO_BYTES = 20 * 1024 * 1024
MAX_CHAT_VIDEO_BYTES = 20 * 1024 * 1024
MAX_CHAT_FILE_BYTES = 15 * 1024 * 1024


@dataclass(frozen=True)
class ChatUploadIntent:
    safe_filename: str
    extension: str
    declared_mime_type: str
    kind: str
    size_bytes: int


def _to_positive_int(value) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise UploadSecurityError("Invalid file size.") from exc
    if parsed <= 0:
        raise UploadSecurityError("Invalid file size.")
    return parsed


def _allowed_extensions_for_kind(kind: str) -> frozenset[str]:
    if kind == "image":
        return SAFE_IMAGE_EXTENSIONS
    if kind == "audio":
        return SAFE_AUDIO_EXTENSIONS
    if kind == "video":
        return SAFE_VIDEO_EXTENSIONS
    if kind == "file":
        return SAFE_DOCUMENT_EXTENSIONS
    raise UploadSecurityError("Unsupported attachment type.")


def _max_bytes_for_kind(kind: str) -> int:
    if kind == "image":
        return MAX_CHAT_IMAGE_BYTES
    if kind == "audio":
        return MAX_CHAT_AUDIO_BYTES
    if kind == "video":
        return MAX_CHAT_VIDEO_BYTES
    if kind == "file":
        return MAX_CHAT_FILE_BYTES
    raise UploadSecurityError("Unsupported attachment type.")


def infer_chat_upload_kind(filename: str, declared_mime_type: str | None) -> str:
    extension = normalize_extension(filename)
    declared_mime = (declared_mime_type or "").split(";", 1)[0].strip().lower()

    if extension in SAFE_IMAGE_EXTENSIONS:
        return "image"
    if extension in SAFE_VIDEO_EXTENSIONS:
        if declared_mime.startswith("audio/"):
            return "audio"
        return "video"
    if extension in SAFE_AUDIO_EXTENSIONS:
        return "audio"
    if extension in SAFE_DOCUMENT_EXTENSIONS:
        return "file"
    raise UploadSecurityError(
        "Chat attachments only support images, MP4/WEBM video, audio, PDF, DOCX, PPTX, TXT, and CSV files."
    )


def validate_chat_upload_request(
    *,
    filename: str,
    file_size,
    declared_mime_type: str | None = None,
) -> ChatUploadIntent:
    safe_filename = sanitize_user_filename(filename, default_stem="chat-upload")
    extension = normalize_extension(safe_filename)
    declared_mime = (declared_mime_type or "").split(";", 1)[0].strip().lower()

    if extension not in SAFE_CHAT_FILE_EXTENSIONS:
        raise UploadSecurityError(
            "Chat attachments only support images, MP4/WEBM video, audio, PDF, DOCX, PPTX, TXT, and CSV files."
        )

    kind = infer_chat_upload_kind(safe_filename, declared_mime)
    size_bytes = _to_positive_int(file_size)
    max_bytes = _max_bytes_for_kind(kind)
    if size_bytes > max_bytes:
        raise UploadSecurityError(
            f"{kind.capitalize()} attachments exceed the {max_bytes // (1024 * 1024)}MB limit."
        )

    allowed_mimes = MIME_BY_EXTENSION.get(extension, frozenset())
    ooxml_zip_declared = extension in {".docx", ".pptx"} and declared_mime == "application/zip"
    if declared_mime and allowed_mimes and declared_mime not in allowed_mimes and not ooxml_zip_declared:
        raise UploadSecurityError("Declared MIME type is not allowed for this file.")

    return ChatUploadIntent(
        safe_filename=safe_filename,
        extension=extension,
        declared_mime_type=declared_mime,
        kind=kind,
        size_bytes=size_bytes,
    )


def validate_completed_chat_upload(
    *,
    filename: str,
    payload: bytes,
    kind: str,
    declared_mime_type: str | None,
) -> ValidatedUpload:
    return validate_upload_payload(
        filename=filename,
        payload=payload,
        max_bytes=_max_bytes_for_kind(kind),
        allowed_extensions=_allowed_extensions_for_kind(kind),
        declared_mime_type=declared_mime_type,
    )
