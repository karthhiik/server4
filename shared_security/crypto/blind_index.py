import base64
import hashlib
import hmac


def compute_blind_index(value: str, *, secret: str, field_name: str) -> str:
    payload = f"{field_name}:{value}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
