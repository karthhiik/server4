import logging

from .types import CryptoContext

logger = logging.getLogger("shared_security.crypto")


def audit_crypto_event(event_name: str, *, context: CryptoContext) -> None:
    logger.info(
        "crypto_event=%s service=%s collection=%s field=%s route=%s document_id=%s",
        event_name,
        context.service,
        context.collection,
        context.field_name,
        context.route or "",
        context.document_id or "",
    )
