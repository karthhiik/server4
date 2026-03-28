import base64
import json
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .key_provider import StaticKeyProvider
from .types import CryptoContext


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def _build_aad(context: CryptoContext) -> bytes:
    payload = {
        "service": context.service,
        "collection": context.collection,
        "field_name": context.field_name,
        "route": context.route or "",
        "document_id": context.document_id or "",
        "metadata": context.metadata,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class CryptoService:
    def __init__(self, *, key_provider: StaticKeyProvider, enabled: bool = True) -> None:
        self._key_provider = key_provider
        self._enabled = enabled
        self._aesgcm = AESGCM(self._key_provider.get_key())

    @property
    def enabled(self) -> bool:
        return self._enabled

    def encrypt_text(self, value: str, context: CryptoContext) -> dict:
        if not self._enabled:
            return {"plaintext": value}

        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, value.encode("utf-8"), _build_aad(context))
        return {
            "__enc_v1": True,
            "alg": "AES-256-GCM",
            "key_version": self._key_provider.key_version,
            "key_id": self._key_provider.get_key_id(),
            "nonce": _b64encode(nonce),
            "ciphertext": _b64encode(ciphertext),
        }

    def decrypt_text(self, payload: dict, context: CryptoContext) -> str:
        if not self._enabled and "plaintext" in payload:
            return str(payload["plaintext"])

        nonce = _b64decode(str(payload["nonce"]))
        ciphertext = _b64decode(str(payload["ciphertext"]))
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, _build_aad(context))
        return plaintext.decode("utf-8")

    @staticmethod
    def is_encrypted_payload(value: object) -> bool:
        return isinstance(value, dict) and bool(value.get("__enc_v1"))


@lru_cache(maxsize=8)
def build_crypto_service(master_key: str, key_version: str, enabled: bool) -> CryptoService:
    return CryptoService(
        key_provider=StaticKeyProvider(master_key, key_version),
        enabled=enabled,
    )
