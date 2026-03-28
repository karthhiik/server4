"""
LLM Email Service for Server3.

Uses Mistral (via Azure OpenAI) to generate compelling email content
while preserving the original chat message unchanged.
"""

import json
import logging
import base64
from html import escape
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _resolve_brand_logo_url(override: Optional[str] = None) -> str:
    candidate = (override or settings.BARISE_EMAIL_LOGO_URL or "").strip()
    if candidate:
        if candidate.startswith(("http://", "https://", "data:")):
            return candidate
        try:
            raw_path = candidate.replace("\\", "/")
            candidate_path = Path(raw_path)
            if not candidate_path.is_absolute():
                candidate_path = Path(__file__).resolve().parents[2] / candidate_path
            if candidate_path.exists():
                encoded = base64.b64encode(candidate_path.read_bytes()).decode("ascii")
                suffix = candidate_path.suffix.lower()
                mime = "image/png"
                if suffix == ".svg":
                    mime = "image/svg+xml"
                elif suffix == ".jpg" or suffix == ".jpeg":
                    mime = "image/jpeg"
                return f"data:{mime};base64,{encoded}"
        except Exception:
            pass

    try:
        logo_path = Path(__file__).resolve().parents[3] / "lliveupdatedstreaming" / "Small_crop.svg"
        if logo_path.exists():
            encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
            return f"data:image/svg+xml;base64,{encoded}"
    except Exception:
        return ""
    return ""


async def _get_mistral_client():
    """Get AsyncOpenAI client configured for Mistral via Azure."""
    if not settings.MISTRAL_API_KEY or not settings.MISTRAL_ENDPOINT:
        return None
    
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=settings.MISTRAL_API_KEY,
            base_url=settings.MISTRAL_ENDPOINT,
        )
        return client
    except ImportError:
        logger.warning("[EMAIL] openai library not installed")
        return None
    except Exception as e:
        logger.warning(f"[EMAIL] Failed to create Mistral client: {e}")
        return None


async def generate_chat_email_content(
    sender_name: str,
    message_preview: str,
    unread_count: int = 1,
) -> dict:
    """
    Generate LLM-enhanced email content for chat notification.
    
    The original message is NEVER modified - only surrounding copy is generated.
    
    Args:
        sender_name: Display name of the message sender
        message_preview: The actual message content (will be preserved exactly)
    
    Returns:
        Dict with subject, greeting, context_text, and cta_text
    """
    # Default fallback content
    fallback = {
        "subject": f"{unread_count} unread message{'s' if unread_count != 1 else ''} from {sender_name}",
        "greeting": f"Hi there!",
        "context_text": f"{sender_name} sent you {unread_count} message{'s' if unread_count != 1 else ''} on Barise",
        "cta_text": "Open Chat",
        "preheader": f"Catch up with {sender_name} on Barise",
    }
    
    client = await _get_mistral_client()
    if not client:
        logger.info("[EMAIL] LLM not available, using fallback content")
        return fallback
    
    prompt = f"""You write chat notification emails for Barise, a community platform for startup founders and investors.

Generate an email notification for a new chat message:
- Sender: {sender_name}
- Message Type: Direct message
- Unread message count: {unread_count}

IMPORTANT: Do NOT modify or paraphrase the actual message. Just generate the surrounding email copy.
Keep the tone professional but friendly. Be concise.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "subject": "notification subject, max 50 chars",
  "greeting": "short greeting line, max 30 chars",
  "context_text": "brief context about receiving a message, max 80 chars",
  "cta_text": "call-to-action button text, max 20 chars",
  "preheader": "email preview line, max 60 chars"
}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.MISTRAL_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are an email copywriter. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean up potential markdown formatting
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        result = json.loads(content)
        
        # Validate required fields
        required = ["subject", "greeting", "context_text", "cta_text"]
        if all(key in result for key in required):
            logger.info(f"[EMAIL] LLM content generated: subject='{result['subject'][:30]}...'")
            return result
        else:
            logger.warning("[EMAIL] LLM response missing required fields")
            return fallback
            
    except json.JSONDecodeError as e:
        logger.warning(f"[EMAIL] LLM returned invalid JSON: {e}")
        return fallback
    except Exception as e:
        logger.warning(f"[EMAIL] LLM generation failed: {e}")
        return fallback


def build_chat_notification_html(
    recipient_name: str,
    sender_name: str,
    sender_avatar_url: Optional[str],
    message_content: str,
    chat_url: str,
    llm_content: dict,
    unread_count: int = 1,
    brand_logo_url: Optional[str] = None,
    message_snippets: Optional[list[str]] = None,
) -> str:
    """
    Build HTML email template for chat notification.
    
    The original message is preserved exactly (HTML-escaped for safety).
    
    Args:
        recipient_name: Name of the email recipient
        sender_name: Name of the message sender
        sender_avatar_url: URL to sender's avatar (optional)
        message_content: The original message (will be HTML-escaped)
        chat_room_id: ID of the chat room for deep linking
        llm_content: Dict with subject, greeting, context_text, cta_text
    
    Returns:
        Complete HTML email string
    """
    # HTML-escape the message content for XSS safety
    safe_message = escape(message_content)
    safe_sender = escape(sender_name)
    safe_recipient = escape(recipient_name)
    
    # Default avatar if none provided
    avatar_html = ""
    if sender_avatar_url:
        avatar_html = f'<img src="{escape(sender_avatar_url)}" alt="{safe_sender}" style="width: 48px; height: 48px; border-radius: 50%; margin-right: 12px;" />'
    else:
        # Fallback to initial letter
        initial = sender_name[0].upper() if sender_name else "?"
        avatar_html = f'''
        <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    display: flex; align-items: center; justify-content: center; margin-right: 12px;
                    color: white; font-weight: bold; font-size: 20px;">{initial}</div>
        '''
    
    preferences_url = f"{settings.FRONTEND_URL}/settings/notifications"
    preheader = escape(llm_content.get("preheader", f"Catch up with {safe_sender} on Barise"))
    safe_brand_logo_url = escape(_resolve_brand_logo_url(brand_logo_url))
    snippet_rows = ""
    if message_snippets:
        snippet_rows = "".join(
            f'<li style="margin: 0 0 8px; color: #4b5563; font-size: 13px; line-height: 1.5;">{escape(snippet)}</li>'
            for snippet in message_snippets
        )
        if snippet_rows:
            snippet_rows = f"""
            <div style="margin-top: 18px;">
                <p style="margin: 0 0 10px; color: #374151; font-size: 13px; font-weight: 600;">Recent messages</p>
                <ul style="padding-left: 18px; margin: 0;">{snippet_rows}</ul>
            </div>
            """

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(llm_content.get('subject', 'New Message'))}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{preheader}</div>
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    
                    <!-- Header with gradient -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; text-align: center;">
                            {f'<img src="{safe_brand_logo_url}" alt="Barise" style="width: 40px; height: 40px; display: block; margin: 0 auto 12px;" />' if safe_brand_logo_url else ''}
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">Barise</h1>
                            <p style="margin: 10px 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">Realtime chat updates for founders and operators</p>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <!-- Greeting -->
                            <p style="margin: 0 0 20px; color: #333333; font-size: 16px;">
                                {escape(llm_content.get('greeting', 'Hi there!'))}
                            </p>
                            
                            <!-- Context -->
                            <p style="margin: 0 0 25px; color: #555555; font-size: 15px; line-height: 1.5;">
                                {escape(llm_content.get('context_text', f'{safe_sender} sent you a message'))}
                            </p>
                            <p style="margin: 0 0 18px; color: #667085; font-size: 13px; line-height: 1.5;">
                                {unread_count} unread message{'s' if unread_count != 1 else ''} waiting in your Barise chat.
                            </p>
                            
                            <!-- Message Card -->
                            <table role="presentation" style="width: 100%; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <!-- Sender Info -->
                                        <table role="presentation" style="margin-bottom: 15px;">
                                            <tr>
                                                <td style="vertical-align: middle;">
                                                    {avatar_html}
                                                </td>
                                                <td style="vertical-align: middle;">
                                                    <strong style="color: #333333; font-size: 15px;">{safe_sender}</strong>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Message Content (Original, preserved exactly) -->
                                        <p style="margin: 0; color: #333333; font-size: 15px; line-height: 1.6; white-space: pre-wrap;">
                                            {safe_message}
                                        </p>
                                        {snippet_rows}
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- CTA Button -->
                            <table role="presentation" style="margin: 30px 0;">
                                <tr>
                                    <td>
                                        <a href="{chat_url}" 
                                           style="display: inline-block; padding: 14px 32px; 
                                                  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                                  color: #ffffff; text-decoration: none; 
                                                  border-radius: 8px; font-weight: 600; font-size: 15px;">
                                            {escape(llm_content.get('cta_text', 'Reply Now'))}
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 40px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0 0 10px; color: #888888; font-size: 13px; text-align: center;">
                                You received this email because you have chat notifications enabled.
                            </p>
                            <p style="margin: 0; text-align: center;">
                                <a href="{preferences_url}" style="color: #667eea; font-size: 13px; text-decoration: none;">
                                    Manage notification preferences
                                </a>
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return html
