"""
Brevo Email Service for Server3.

Direct integration with Brevo (SendInBlue) API for sending
chat notification emails without cross-server dependency.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis key for daily email quota tracking
DAILY_EMAIL_COUNT_KEY = "server3:brevo:daily_email_count"


async def get_redis_client() -> aioredis.Redis:
    """Get async Redis client for quota tracking."""
    if settings.REDIS_SSL:
        url = f"rediss://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    else:
        url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    
    return aioredis.from_url(url, decode_responses=True)


async def check_daily_quota() -> tuple[bool, int]:
    """
    Check if we're within the daily email quota.
    
    Returns:
        Tuple of (within_quota: bool, current_count: int)
    """
    if not settings.EMAIL_RATE_LIMIT_ENABLED:
        return True, 0
    
    try:
        redis_client = await get_redis_client()
        count_str = await redis_client.get(DAILY_EMAIL_COUNT_KEY)
        await redis_client.aclose()
        
        current_count = int(count_str) if count_str else 0
        within_quota = current_count < settings.EMAIL_DAILY_QUOTA
        
        return within_quota, current_count
    except Exception as e:
        logger.warning(f"[EMAIL] Redis quota check failed: {e}, allowing send")
        return True, 0


async def increment_email_count() -> int:
    """
    Increment the daily email counter in Redis.
    Sets TTL to expire at midnight UTC.
    
    Returns:
        New count after increment
    """
    try:
        redis_client = await get_redis_client()
        
        # Increment counter
        new_count = await redis_client.incr(DAILY_EMAIL_COUNT_KEY)
        
        # Set TTL to expire at midnight UTC (if not already set)
        ttl = await redis_client.ttl(DAILY_EMAIL_COUNT_KEY)
        if ttl == -1:  # No expiry set
            now = datetime.now(timezone.utc)
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if now >= midnight:
                from datetime import timedelta
                midnight = midnight + timedelta(days=1)
            seconds_until_midnight = int((midnight - now).total_seconds())
            await redis_client.expire(DAILY_EMAIL_COUNT_KEY, seconds_until_midnight)
        
        await redis_client.aclose()
        return new_count
    except Exception as e:
        logger.warning(f"[EMAIL] Redis increment failed: {e}")
        return 0


async def send_transactional_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    sender_email: Optional[str] = None,
    sender_name: Optional[str] = None,
) -> dict:
    """
    Send a transactional email via Brevo API.
    
    Args:
        to_email: Recipient email address
        to_name: Recipient name
        subject: Email subject
        html_content: HTML email body
        sender_email: Override sender email (optional)
        sender_name: Override sender name (optional)
    
    Returns:
        Dict with status and message_id or error
    """
    # Check if Brevo is configured
    if not settings.MAIL_API_KEY:
        logger.warning("[EMAIL] Brevo API key not configured")
        return {"status": "error", "message": "Email service not configured"}
    
    # Check daily quota
    within_quota, current_count = await check_daily_quota()
    if not within_quota:
        logger.warning(f"[EMAIL] Daily quota exceeded ({current_count}/{settings.EMAIL_DAILY_QUOTA})")
        return {"status": "quota_exceeded", "count": current_count}
    
    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
        
        # Configure Brevo API client
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.MAIL_API_KEY
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        
        # Build email
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": to_name}],
            sender={
                "email": sender_email or settings.MAIL_SENDER_EMAIL,
                "name": sender_name or settings.MAIL_SENDER_NAME,
            },
            subject=subject,
            html_content=html_content,
        )
        
        # Send email
        response = api_instance.send_transac_email(send_smtp_email)
        
        # Increment counter on success
        new_count = await increment_email_count()
        
        logger.info(f"[EMAIL] ✓ Sent to {to_email}, message_id: {response.message_id}, quota: {new_count}/{settings.EMAIL_DAILY_QUOTA}")
        
        return {
            "status": "sent",
            "message_id": response.message_id,
            "quota_used": new_count,
        }
        
    except ImportError:
        logger.error("[EMAIL] sib-api-v3-sdk not installed")
        return {"status": "error", "message": "Email SDK not installed"}
    except ApiException as e:
        logger.error(f"[EMAIL] Brevo API error: {e.status} - {e.reason}")
        return {"status": "error", "message": f"API error: {e.reason}"}
    except Exception as e:
        logger.error(f"[EMAIL] Unexpected error: {e}")
        return {"status": "error", "message": str(e)}


async def send_email_with_quota_check(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> bool:
    """
    Convenience wrapper that returns simple success/failure.
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    result = await send_transactional_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        html_content=html_content,
    )
    return result.get("status") == "sent"
