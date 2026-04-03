"""
Comprehensive Model Test Script
Tests all LLM models available in the system.
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings


def get_env(key: str, default: str = "") -> str:
    """Get config value safely"""
    val = getattr(settings, key, default)
    if val is None:
        val = default
    return str(val).strip().strip('"')


async def test_gpt4o_mini():
    """Test Azure GPT-4o-mini"""
    print("\n" + "=" * 60)
    print("Testing: GPT-4o-mini (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = get_env("AZURE_GPT4O_MINI_ENDPOINT")
    api_key = get_env("AZURE_GPT4O_MINI_API_KEY")
    deployment = get_env("AZURE_GPT4O_MINI_DEPLOYMENT")

    if not endpoint or not api_key:
        print("[SKIP] Not configured")
        return None

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}],
            temperature=0.3,
            max_tokens=10,
        )
        result = response.choices[0].message.content
        print(f"[PASS] Success: {result}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_deepseek_v3():
    """Test Azure DeepSeek-V3"""
    print("\n" + "=" * 60)
    print("Testing: DeepSeek-V3 (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = get_env("DEEPSEEK_ENDPOINT")
    api_key = get_env("DEEPSEEK_API_KEY")
    model = get_env("DEEPSEEK_MODEL_NAME")

    if not endpoint or not api_key:
        print("[SKIP] Not configured")
        return None

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
        print(f"[PASS] Success: {result[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_mistral():
    """Test Azure Mistral-medium"""
    print("\n" + "=" * 60)
    print("Testing: Mistral-medium (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = get_env("MISTRAL_ENDPOINT")
    api_key = get_env("MISTRAL_API_KEY")
    deployment = get_env("MISTRAL_DEPLOYMENT")

    if not endpoint or not api_key:
        print("[SKIP] Not configured")
        return None

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Explain AI in one sentence."}],
            temperature=0.5,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"[PASS] Success: {result[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_kimi():
    """Test Azure Kimi-K2-Thinking"""
    print("\n" + "=" * 60)
    print("Testing: Kimi-K2-Thinking (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = get_env("AZURE_KIMI_ENDPOINT")
    api_key = get_env("AZURE_KIMI_API_KEY")
    deployment = get_env("AZURE_KIMI_DEPLOYMENT")

    print(
        f"DEBUG: endpoint='{endpoint}', api_key={'set' if api_key else 'not set'}, deployment='{deployment}'"
    )

    if not endpoint or not api_key:
        print("[SKIP] Not configured")
        return None

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
        print(f"[PASS] Success: {result[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_phi4():
    """Test Azure Phi-4-reasoning"""
    print("\n" + "=" * 60)
    print("Testing: Phi-4-reasoning (Azure)")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = get_env("PHI4_REASONING_ENDPOINT")
    api_key = get_env("PHI4_REASONING_API_KEY")
    deployment = get_env("PHI4_REASONING_DEPLOYMENT")

    if not endpoint or not api_key:
        print("[SKIP] Not configured - trying alternate env names...")
        # Try direct env access
        endpoint = os.getenv("Phi-4-reasoning_endpoint", "")
        api_key = os.getenv("Phi-4-reasoning_api_key", "")
        deployment = os.getenv("Phi-4-reasoning_deployment_name", "Phi-4-reasoning")

        if not endpoint or not api_key:
            print("[SKIP] Not configured")
            return None

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Solve: If x + 5 = 12, what is x?"}],
            temperature=0.3,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"[PASS] Success: {result}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_flux_image():
    """Test Azure FLUX.1-Kontext-pro image generation"""
    print("\n" + "=" * 60)
    print("Testing: FLUX.1-Kontext-pro (Azure) - Image Generation")
    print("=" * 60)

    from openai import AsyncOpenAI

    endpoint = get_env("AZURE_FLUX_ENDPOINT")
    api_key = get_env("AZURE_FLUX_API_KEY")
    deployment = get_env("AZURE_FLUX_DEPLOYMENT_NAME")

    if not endpoint or not api_key:
        print("[SKIP] Not configured")
        return None

    try:
        client = AsyncOpenAI(base_url=endpoint.rstrip("/"), api_key=api_key)
        response = await client.images.generate(
            model=deployment,
            prompt="A cute baby polar bear",
            n=1,
            size="1024x1024",
        )

        b64_data = response.data[0].b64_json
        if b64_data:
            image_bytes = base64.b64decode(b64_data)
            print(f"[PASS] Success: Generated {len(image_bytes) // 1024}KB image")
            return True
        else:
            print("[FAIL] No image data returned")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_cf_qwen():
    """Test Cloudflare Qwen - Uses text mode"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare Qwen (text mode)")
    print("=" * 60)

    import httpx

    url = get_env("CF_WORKER_QWEN_URL")
    token = get_env("CF_WORKER_QWEN_TOKEN")

    if not url or not token:
        print("[SKIP] Not configured")
        return None

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
        print(f"[PASS] Success: {str(content)[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_cf_glm():
    """Test Cloudflare GLM - Uses text mode"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare GLM (text mode)")
    print("=" * 60)

    import httpx

    url = get_env("CF_WORKER_GLM_URL")
    token = get_env("CF_WORKER_GLM_TOKEN")

    if not url or not token:
        print("[SKIP] Not configured")
        return None

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
        print(f"[PASS] Success: {str(content)[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_cf_gemma():
    """Test Cloudflare Gemma - Uses text mode"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare Gemma (text mode)")
    print("=" * 60)

    import httpx

    url = get_env("CF_WORKER_GEMMA_URL")
    token = get_env("CF_WORKER_GEMMA_TOKEN")

    if not url or not token:
        print("[SKIP] Not configured")
        return None

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
        print(f"[PASS] Success: {str(content)[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_cf_lucid():
    """Test Cloudflare Lucid for image generation - Uses image mode"""
    print("\n" + "=" * 60)
    print("Testing: Cloudflare Lucid (Image Generation)")
    print("=" * 60)

    import httpx

    url = get_env("CF_WORKER_LUCID_URL")
    token = get_env("CF_WORKER_LUCID_TOKEN")

    if not url or not token:
        print("[SKIP] Not configured")
        return None

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

        print(f"[PASS] Success: Generated {len(image_bytes) // 1024}KB image")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_groq():
    """Test Groq models"""
    print("\n" + "=" * 60)
    print("Testing: Groq (llama-3.3-70b-versatile)")
    print("=" * 60)

    from openai import AsyncOpenAI

    api_keys = settings.groq_keys
    if not api_keys:
        print("[SKIP] No Groq API keys configured")
        return None

    try:
        client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_keys[0],
        )
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "What is Docker? One sentence."}],
            temperature=0.5,
            max_tokens=50,
        )
        result = response.choices[0].message.content
        print(f"[PASS] Success: {result[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def test_openrouter():
    """Test OpenRouter free model"""
    print("\n" + "=" * 60)
    print("Testing: OpenRouter (qwen/qwen3.6-plus:free)")
    print("=" * 60)

    from openai import AsyncOpenAI

    api_key = get_env("OPENROUTE_SERVICE_API_KEY")

    if not api_key:
        print("[SKIP] Not configured")
        return None

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
        print(f"[PASS] Success: {result}")
        return True
    except Exception as e:
        print(f"[FAIL] Error: {str(e)[:100]}")
        return False


async def main():
    """Run all model tests"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE MODEL TESTING")
    print("=" * 60)

    results = {}

    # Azure Models (Text)
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

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len(results)

    for name, status in results.items():
        if status is True:
            print(f"[PASS] {name}")
        elif status is False:
            print(f"[FAIL] {name}")
        else:
            print(f"[SKIP] {name}")

    print(
        f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped / {total} models"
    )


if __name__ == "__main__":
    asyncio.run(main())
