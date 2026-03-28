from copy import deepcopy
import logging
from pathlib import Path
import sys

from cryptography.exceptions import InvalidTag

from app.core.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from shared_security.crypto import (  # noqa: E402
    COLLECTION_FIELD_REGISTRY,
    build_crypto_service,
    encrypt_document_fields,
)
from shared_security.crypto.audit import audit_crypto_event  # noqa: E402
from shared_security.crypto.crypto_service import CryptoService  # noqa: E402
from shared_security.crypto.types import CryptoContext  # noqa: E402

logger = logging.getLogger(__name__)

settings = get_settings()
MESSAGE_COLLECTION_KEY = "server3.messages"
MESSAGE_POLICY = COLLECTION_FIELD_REGISTRY[MESSAGE_COLLECTION_KEY]
CRYPTO_SERVICE = build_crypto_service(
    settings.ENCRYPTION_MASTER_KEY,
    settings.ENCRYPTION_KEY_VERSION,
    settings.ENCRYPTION_ENABLED,
)

MESSAGE_CONTENT_ROUTE = "server3.message.content.v1"
MESSAGE_LEGACY_ROUTES = (
    "ws.message",
    "chat.edit_message",
    "migration.server3.messages",
)
REPLY_PREVIEW_ROUTE = "server3.reply_preview.content.v1"
REPLY_PREVIEW_LEGACY_ROUTES = (
    "ws.reply_preview",
    "migration.server3.reply_preview",
)
UNAVAILABLE_MESSAGE_TEXT = "[Message unavailable]"
UNAVAILABLE_REPLY_PREVIEW = "[Original message unavailable]"


def _message_metadata(document: dict) -> dict[str, str]:
    metadata: dict[str, str] = {}
    conversation_id = document.get("conversation_id")
    sender_id = document.get("sender_id")
    if conversation_id is not None:
        metadata["conversation_id"] = str(conversation_id)
    if sender_id is not None:
        metadata["sender_id"] = str(sender_id)
    return metadata


def _message_context(
    field_name: str,
    document: dict,
    *,
    route: str | None,
    document_id: str | None,
) -> CryptoContext:
    return CryptoContext(
        service="server3",
        collection=MESSAGE_COLLECTION_KEY,
        field_name=field_name,
        route=route,
        document_id=document_id,
        metadata=_message_metadata(document),
    )


def _document_id_variants(document: dict) -> tuple[str | None, ...]:
    document_id = document.get("_id")
    normalized = str(document_id) if document_id is not None else None
    if normalized:
        return (None, normalized)
    return (None,)


def _context_variants(
    *,
    field_name: str,
    document: dict,
    requested_route: str | None,
    stable_route: str,
    legacy_routes: tuple[str, ...],
) -> list[CryptoContext]:
    routes: list[str | None] = [stable_route]
    if requested_route:
        routes.append(requested_route)
    routes.extend(legacy_routes)
    routes.append("")

    seen: set[tuple[str, str]] = set()
    contexts: list[CryptoContext] = []
    for route_value in routes:
        normalized_route = route_value or ""
        for document_id in _document_id_variants(document):
            key = (normalized_route, document_id or "")
            if key in seen:
                continue
            seen.add(key)
            contexts.append(
                _message_context(
                    field_name,
                    document,
                    route=route_value,
                    document_id=document_id,
                )
            )
    return contexts


def _decrypt_with_fallback(
    payload: dict,
    *,
    field_name: str,
    document: dict,
    requested_route: str,
    stable_route: str,
    legacy_routes: tuple[str, ...],
    fallback_text: str,
) -> str:
    if isinstance(payload, dict) and "plaintext" in payload:
        return str(payload["plaintext"])

    if not CryptoService.is_encrypted_payload(payload):
        return fallback_text

    for context in _context_variants(
        field_name=field_name,
        document=document,
        requested_route=requested_route,
        stable_route=stable_route,
        legacy_routes=legacy_routes,
    ):
        try:
            return CRYPTO_SERVICE.decrypt_text(payload, context)
        except InvalidTag:
            continue
        except Exception:
            continue

    logger.warning(
        "Unable to decrypt server3 message field=%s conversation_id=%s message_id=%s",
        field_name,
        document.get("conversation_id"),
        document.get("_id"),
    )
    return fallback_text


def _read_message_field(
    document: dict,
    *,
    field_name: str,
    route: str,
    stable_route: str,
    legacy_routes: tuple[str, ...],
    fallback_text: str,
) -> str | None:
    encrypted_name = f"{field_name}_encrypted"
    encrypted_value = document.get(encrypted_name)
    if encrypted_value is not None:
        return _decrypt_with_fallback(
            encrypted_value,
            field_name=field_name,
            document=document,
            requested_route=route,
            stable_route=stable_route,
            legacy_routes=legacy_routes,
            fallback_text=fallback_text,
        )

    value = document.get(field_name)
    if value is None:
        return None
    return str(value)


def encrypt_message_document(document: dict, *, route: str) -> dict:
    encrypted = encrypt_document_fields(
        document,
        policy=MESSAGE_POLICY,
        crypto_service=CRYPTO_SERVICE,
        context_factory=lambda field_name, current_document: _message_context(
            field_name,
            current_document,
            route=MESSAGE_CONTENT_ROUTE,
            document_id=None,
        ),
    )
    if CRYPTO_SERVICE.enabled and "content_encrypted" in encrypted:
        audit_crypto_event(
            "encrypt_message_content",
            context=_message_context(
                "content",
                encrypted,
                route=MESSAGE_CONTENT_ROUTE,
                document_id=None,
            ),
        )
    return encrypted


def decrypt_message_document(document: dict, *, route: str) -> dict:
    decrypted = deepcopy(document)
    content = _read_message_field(
        decrypted,
        field_name="content",
        route=route,
        stable_route=MESSAGE_CONTENT_ROUTE,
        legacy_routes=MESSAGE_LEGACY_ROUTES,
        fallback_text=UNAVAILABLE_MESSAGE_TEXT,
    )
    if content is not None:
        decrypted["content"] = content
        if CRYPTO_SERVICE.enabled:
            audit_crypto_event(
                "decrypt_message_content",
                context=_message_context(
                    "content",
                    decrypted,
                    route=MESSAGE_CONTENT_ROUTE,
                    document_id=None,
                ),
            )
    return decrypted


def resolve_message_content(document: dict, *, route: str) -> str:
    return (
        _read_message_field(
            document,
            field_name="content",
            route=route,
            stable_route=MESSAGE_CONTENT_ROUTE,
            legacy_routes=MESSAGE_LEGACY_ROUTES,
            fallback_text=UNAVAILABLE_MESSAGE_TEXT,
        )
        or ""
    )


def encrypt_reply_preview(content: str, *, parent_document: dict, route: str) -> dict:
    context = _message_context(
        "reply_to_data.content",
        parent_document,
        route=REPLY_PREVIEW_ROUTE,
        document_id=None,
    )
    return CRYPTO_SERVICE.encrypt_text(content, context)


def decrypt_reply_preview(payload: dict, *, parent_document: dict, route: str) -> str:
    return _decrypt_with_fallback(
        payload,
        field_name="reply_to_data.content",
        document=parent_document,
        requested_route=route,
        stable_route=REPLY_PREVIEW_ROUTE,
        legacy_routes=REPLY_PREVIEW_LEGACY_ROUTES,
        fallback_text=UNAVAILABLE_REPLY_PREVIEW,
    )
