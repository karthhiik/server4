"""
Comprehensive Model Test Script
Tests all LLM models available in the system.
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings


async def test_gpt4o_mini():
    """Test Azure GPT-4o-mini"""
    print("\n" + "=" * 60)
    print("Testing: GPT-4o-mini (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = settings.AZURE_GPT4O_MINI_ENDPOINT.strip().strip('"')
    api_key = settings.AZURE_GPT4O_MINI_API_KEY.strip().strip('"')
    deployment = settings.AZURE_GPT4O_MINI_DEPLOYMENT.strip().strip('"')

    if not endpoint or not api_key:
        print("❌ Not configured")
        return False

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}],
            temperature=0.3,
            max_tokens=10,
        )
        result = response.choices[0].message.content
        print(f"✅ Success: {result}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_deepseek_v3():
    """Test Azure DeepSeek-V3"""
    print("\n" + "=" * 60)
    print("Testing: DeepSeek-V3 (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = settings.DEEPSEEK_ENDPOINT.strip().strip('"')
    api_key = settings.DEEPSEEK_API_KEY.strip().strip('"')
    model = settings.DEEPSEEK_MODEL_NAME.strip().strip('"')

    if not endpoint or not api_key:
        print("❌ Not configured")
        return False

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "What is Python? Answer in one sentence."}
            ],
            temperature=0.7,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"✅ Success: {result[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_mistral():
    """Test Azure Mistral-medium"""
    print("\n" + "=" * 60)
    print("Testing: Mistral-medium (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = settings.MISTRAL_ENDPOINT.strip().strip('"')
    api_key = settings.MISTRAL_API_KEY.strip().strip('"')
    deployment = settings.MISTRAL_DEPLOYMENT.strip().strip('"')

    if not endpoint or not api_key:
        print("❌ Not configured")
        return False

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Explain AI in one sentence."}],
            temperature=0.5,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"✅ Success: {result[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_kimi():
    """Test Azure Kimi-K2-Thinking"""
    print("\n" + "=" * 60)
    print("Testing: Kimi-K2-Thinking (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = settings.AZURE_KIMI_ENDPOINT.strip().strip('"')
    api_key = settings.AZURE_KIMI_API_KEY.strip().strip('"')
    deployment = settings.AZURE_KIMI_DEPLOYMENT.strip().strip('"')

    if not endpoint or not api_key:
        print("❌ Not configured")
        return False

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "user",
                    "content": "What is machine learning? Answer in 2 sentences.",
                }
            ],
            temperature=0.5,
            max_tokens=100,
        )
        result = response.choices[0].message.content
        print(f"✅ Success: {result[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_phi4():
    """Test Azure Phi-4-reasoning"""
    print("\n" + "=" * 60)
    print("Testing: Phi-4-reasoning (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = settings.PHI4_REASONING_ENDPOINT.strip().strip('"')
    api_key = settings.PHI4_REASONING_API_KEY.strip().strip('"')
    deployment = settings.PHI4_REASONING_DEPLOYMENT.strip().strip('"')

    if not endpoint or not api_key:
        print("❌ Not configured - checking .env field names...")
        # Try alternative field names
        print(f"PHI4_REASONING_ENDPOINT: '{settings.PHI4_REASONING_ENDPOINT}'")
        print(f"PHI4_REASONING_API_KEY: '{settings.PHI4_REASONING_API_KEY}'")
        print(f"PHI4_REASONING_DEPLOYMENT: '{settings.PHI4_REASONING_DEPLOYMENT}'")
        return False

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Solve: If x + 5 = 12, what is x?"}],
            temperature=0.3,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"✅ Success: {result}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_flux_image():
    """Test Azure FLUX.1-Kontext-pro image generation"""
    print("\n" + "=" * 60)
    print("Testing: FLUX.1-Kontext-pro (Azure) - Image Generation")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = settings.AZURE_FLUX_ENDPOINT.strip().strip('"')
    api_key = settings.AZURE_FLUX_API_KEY.strip().strip('"')
    deployment = settings.AZURE_FLUX_DEPLOYMENT_NAME.strip().strip('"')

    if not endpoint or not api_key:
        print("❌ Not configured")
        return False

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.images.generate(
            model=deployment,
            prompt="A cute baby polar bear",
            n=1,
            size="1024x1024",
        )

        # Decode base64 image
        image_bytes = base64.b64decode(response.data[0].b64_json)
        print(f"✅ Success: Generated {len(image_bytes) // 1024}KB image")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_cf_qwen():
    """Test Cloudflare Qwen"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare Qwen")
    print("=" * 60)

    import httpx

    url = settings.CF_WORKER_QWEN_URL.strip().strip('"')
    token = settings.CF_WORKER_QWEN_TOKEN.strip().strip('"')

    if not url or not token:
        print("❌ Not configured")
        return False

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json={"message": "What is AI? One sentence."},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("response") or data.get("content") or str(data)
        print(f"✅ Success: {content[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_cf_glm():
    """Test Cloudflare GLM"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare GLM")
    print("=" * 60)

    import httpx

    url = settings.CF_WORKER_GLM_URL.strip().strip('"')
    token = settings.CF_WORKER_GLM_TOKEN.strip().strip('"')

    if not url or not token:
        print("❌ Not configured")
        return False

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json={"message": "What is deep learning? One sentence."},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("response") or data.get("content") or str(data)
        print(f"✅ Success: {content[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_cf_gemma():
    """Test Cloudflare Gemma"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare Gemma")
    print("=" * 60)

    import httpx

    url = settings.CF_WORKER_GEMMA_URL.strip().strip('"')
    token = settings.CF_WORKER_GEMMA_TOKEN.strip().strip('"')

    if not url or not token:
        print("❌ Not configured")
        return False

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json={"message": "What is a neural network? One sentence."},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("response") or data.get("content") or str(data)
        print(f"✅ Success: {content[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_cf_lucid():
    """Test Cloudflare Lucid for image generation"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare Lucid (Image Generation)")
    print("=" * 60)

    import httpx

    url = settings.CF_WORKER_LUCID_URL.strip().strip('"')
    token = settings.CF_WORKER_LUCID_TOKEN.strip().strip('"')

    if not url or not token:
        print("❌ Not configured")
        return False

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                json={"prompt": "A cute cat"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            image_bytes = resp.content

        print(f"✅ Success: Generated {len(image_bytes) // 1024}KB image")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_groq():
    """Test Groq models"""
    print("\n" + "=" * 60)
    print("Testing: Groq (llama-3.1-70b-versatile)")
    print("=" * 60)

    from openai import AsyncOpenAI

    api_keys = settings.groq_keys
    if not api_keys:
        print("❌ No Groq API keys configured")
        return False

    try:
        # Use first available key
        client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_keys[0],
        )
        response = await client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": "What is Docker? One sentence."}],
            temperature=0.5,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"✅ Success: {result[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_openrouter():
    """Test OpenRouter free model"""
    print("\n" + "=" * 60)
    print("Testing: OpenRouter (qwen/qwen3.6-plus:free)")
    print("=" * 60)

    from openai import AsyncOpenAI

    api_key = settings.OPENROUTE_SERVICE_API_KEY.strip().strip('"')

    if not api_key:
        print("❌ Not configured")
        return False

    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        response = await client.chat.completions.create(
            model="qwen/qwen3.6-plus:free",
            messages=[{"role": "user", "content": "Hello! Say hi."}],
            temperature=0.7,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"✅ Success: {result}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Run all model tests"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE MODEL TESTING")
    print("=" * 60)

    results = {}

    # Azure Models
    results["gpt-4o-mini"] = await test_gpt4o_mini()
    results["deepseek-v3"] = await test_deepseek_v3()
    results["mistral-medium"] = await test_mistral()
    results["kimi-k2-thinking"] = await test_kimi()
    results["phi-4-reasoning"] = await test_phi4()
    results["flux-image"] = await test_flux_image()

    # Cloudflare Models
    results["cf-qwen"] = await test_cf_qwen()
    results["cf-glm"] = await test_cf_glm()
    results["cf-gemma"] = await test_cf_gemma()
    results["cf-lucid-image"] = await test_cf_lucid()

    # Groq & OpenRouter
    results["groq"] = await test_groq()
    results["openrouter"] = await test_openrouter()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} models working")


if __name__ == "__main__":
    asyncio.run(main())
