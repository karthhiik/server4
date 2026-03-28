import base64
import hashlib


class StaticKeyProvider:
    def __init__(self, raw_key_material: str, key_version: str) -> None:
        if not raw_key_material.strip():
            raise ValueError("Encryption master key material must not be empty")
        self._raw_key_material = raw_key_material.strip()
        self._key_version = key_version.strip() or "v1"
        self._cached_key = hashlib.sha256(self._raw_key_material.encode("utf-8")).digest()

    @property
    def key_version(self) -> str:
        return self._key_version

    def get_key(self) -> bytes:
        return self._cached_key

    def get_key_id(self) -> str:
        digest = hashlib.sha256(self._cached_key).digest()[:8]
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
