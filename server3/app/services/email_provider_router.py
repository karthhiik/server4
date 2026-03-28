from __future__ import annotations

from typing import Optional

from app.core.config import get_settings
from app.services import brevo_service, mailjet_service

settings = get_settings()


async def send_chat_email_via_provider(
    *,
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> dict:
    providers = [
        (settings.EMAIL_PROVIDER_CHAT_PRIMARY or "brevo").lower(),
        (settings.EMAIL_PROVIDER_CHAT_FALLBACK or "mailjet").lower(),
    ]

    tried: list[str] = []
    for provider in providers:
        if not provider or provider in tried:
            continue
        tried.append(provider)

        if provider == "mailjet":
            result = await mailjet_service.send_transactional_email(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
        else:
            result = await brevo_service.send_transactional_email(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                html_content=html_content,
            )

        if result.get("status") == "sent":
            return {**result, "provider": provider}

    return {
        "status": "error",
        "message": "All configured email providers failed",
        "providers": tried,
    }
