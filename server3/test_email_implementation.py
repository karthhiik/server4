"""
Test script to verify chat email notification implementation.

Run this to check:
1. All imports work correctly
2. Configuration is loaded
3. Services are properly connected
"""

import asyncio
import sys
sys.path.insert(0, '.')

async def test_email_implementation():
    """Test the email implementation."""
    print("=" * 60)
    print("CHAT EMAIL NOTIFICATION TEST")
    print("=" * 60)
    
    # Test 1: Import all modules
    print("\n1. Testing imports...")
    try:
        from app.core.config import get_settings
        print("   ✓ config.py imported")
        
        from app.services.brevo_service import (
            check_daily_quota,
            send_transactional_email,
        )
        print("   ✓ brevo_service.py imported")
        
        from app.services.llm_email_service import (
            generate_chat_email_content,
            build_chat_notification_html,
        )
        print("   ✓ llm_email_service.py imported")
        
        from app.services.chat_email_service import (
            trigger_chat_email_notification,
            check_email_service_health,
        )
        print("   ✓ chat_email_service.py imported")
        
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        print("\n   → Run: pip install sib-api-v3-sdk openai httpx")
        return False
    
    # Test 2: Check configuration
    print("\n2. Checking configuration...")
    settings = get_settings()
    
    checks = [
        ("MAIL_API_KEY", bool(settings.MAIL_API_KEY)),
        ("MAIL_SENDER_EMAIL", bool(settings.MAIL_SENDER_EMAIL)),
        ("MISTRAL_ENDPOINT", bool(settings.MISTRAL_ENDPOINT)),
        ("MISTRAL_API_KEY", bool(settings.MISTRAL_API_KEY)),
        ("FRONTEND_URL", bool(settings.FRONTEND_URL)),
        ("REDIS_HOST", bool(settings.REDIS_HOST)),
    ]
    
    all_ok = True
    for name, ok in checks:
        status = "✓" if ok else "✗"
        print(f"   {status} {name}: {'configured' if ok else 'MISSING'}")
        if not ok:
            all_ok = False
    
    # Test 3: Check email service health
    print("\n3. Checking email service health...")
    try:
        health = await check_email_service_health()
        print(f"   Status: {health.get('status')}")
        print(f"   Service: {health.get('service')}")
        print(f"   LLM enabled: {health.get('llm_enabled')}")
        if 'quota' in health:
            q = health['quota']
            print(f"   Quota: {q.get('used')}/{q.get('limit')} emails")
    except Exception as e:
        print(f"   ✗ Health check error: {e}")
    
    # Test 4: Test LLM content generation (dry run)
    print("\n4. Testing LLM content generation...")
    try:
        content = await generate_chat_email_content(
            sender_name="Test User",
            message_preview="Hey, this is a test message!",
        )
        print(f"   Subject: {content.get('subject')}")
        print(f"   Greeting: {content.get('greeting')}")
        print(f"   CTA: {content.get('cta_text')}")
    except Exception as e:
        print(f"   ✗ LLM error: {e}")
    
    # Test 5: Generate HTML template (dry run)
    print("\n5. Testing HTML template generation...")
    try:
        html = build_chat_notification_html(
            recipient_name="Test Recipient",
            sender_name="Test Sender",
            sender_avatar_url=None,
            message_content="Hello! This is a test message.",
            chat_room_id="test-room-123",
            llm_content=content,
        )
        print(f"   ✓ HTML generated ({len(html)} bytes)")
        print(f"   Contains gradient: {'gradient' in html}")
        print(f"   Contains CTA button: {'Reply' in html or 'reply' in html.lower()}")
    except Exception as e:
        print(f"   ✗ HTML error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    asyncio.run(test_email_implementation())
