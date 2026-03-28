from copy import deepcopy

from .crypto_service import CryptoService
from .field_registry import CollectionFieldPolicy
from .types import CryptoContext


def _encrypted_field_name(field_name: str) -> str:
    return f"{field_name}_encrypted"


def read_field_value(
    document: dict,
    *,
    field_name: str,
    crypto_service: CryptoService,
    context: CryptoContext,
) -> str | None:
    encrypted_name = _encrypted_field_name(field_name)
    encrypted_value = document.get(encrypted_name)
    if CryptoService.is_encrypted_payload(encrypted_value):
        return crypto_service.decrypt_text(encrypted_value, context)
    if isinstance(encrypted_value, dict) and "plaintext" in encrypted_value:
        return str(encrypted_value["plaintext"])

    fallback_value = document.get(field_name)
    if fallback_value is None:
        return None
    return str(fallback_value)


def encrypt_document_fields(
    document: dict,
    *,
    policy: CollectionFieldPolicy,
    crypto_service: CryptoService,
    context_factory,
) -> dict:
    encrypted_document = deepcopy(document)
    for field_name in policy.encrypted_fields:
        value = encrypted_document.pop(field_name, None)
        if value in (None, ""):
            continue
        encrypted_document[_encrypted_field_name(field_name)] = crypto_service.encrypt_text(
            str(value),
            context_factory(field_name, encrypted_document),
        )
    return encrypted_document


def decrypt_document_fields(
    document: dict,
    *,
    policy: CollectionFieldPolicy,
    crypto_service: CryptoService,
    context_factory,
    only_fields: set[str] | None = None,
) -> dict:
    decrypted_document = deepcopy(document)
    fields_to_read = only_fields or set(policy.encrypted_fields)
    for field_name in policy.encrypted_fields:
        if field_name not in fields_to_read:
            continue
        decrypted_value = read_field_value(
            decrypted_document,
            field_name=field_name,
            crypto_service=crypto_service,
            context=context_factory(field_name, decrypted_document),
        )
        if decrypted_value is not None:
            decrypted_document[field_name] = decrypted_value
    return decrypted_document
