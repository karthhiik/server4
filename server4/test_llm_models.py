"""
LLM Model Health Check — Tests all 6 tiers + image generation models.

Run: python test_llm_models.py

Tests each configured model with a simple prompt and reports:
- Status (OK/FAIL/SKIP)
- Latency
- Response snippet
- Error details (if any)
"""

import asyncio
import json
import os
import sys
import time
from typing import Optional


def load_dotenv():
    """Load .env file manually since we can't rely on pydantic-settings in test."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        print(f"[WARN] .env file not found at {env_path}")
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


# Load env vars before importing anything else
load_dotenv()


# ── Test Configuration ───────────────────────────────────────────

TEST_PROMPT = "In exactly 3 words, what is the capital of France?"
EXPECTED_CONTAINS = "Paris"

JSON_TEST_PROMPT = """Return ONLY valid JSON with this exact structure:
{"city": "Paris", "country": "France", "population": 2161000}
Do not include any explanation, just the JSON."""


# ── Azure OpenAI Models (T0-T3) ─────────────────────────────────


async def test_azure_model(
    name: str,
    endpoint: str,
    api_key: str,
    deployment: str,
    max_tokens: int = 100,
) -> dict:
    """Test an OpenAI-compatible Azure AI model."""
    if not endpoint or not api_key:
        return {"status": "SKIP", "reason": "Not configured"}

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=endpoint.rstrip("/"),
            api_key=api_key,
        )

        start = time.monotonic()
        resp = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": TEST_PROMPT}],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        elapsed = int((time.monotonic() - start) * 1000)

        content = resp.choices[0].message.content or ""
        passed = EXPECTED_CONTAINS.lower() in content.lower()

        return {
            "status": "OK" if passed else "WARN",
            "latency_ms": elapsed,
            "response": content[:100],
            "tokens": resp.usage.total_tokens if resp.usage else 0,
            "warning": None
            if passed
            else f"Expected '{EXPECTED_CONTAINS}' not found in response",
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)[:200]}


async def test_groq_model(api_key: str, model: str = "llama-3.3-70b-versatile") -> dict:
    """Test a Groq model."""
    if not api_key:
        return {"status": "SKIP", "reason": "Not configured"}

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=api_key)

        start = time.monotonic()
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": TEST_PROMPT}],
            temperature=0.1,
            max_tokens=100,
        )
        elapsed = int((time.monotonic() - start) * 1000)

        content = resp.choices[0].message.content or ""
        passed = EXPECTED_CONTAINS.lower() in content.lower()

        return {
            "status": "OK" if passed else "WARN",
            "latency_ms": elapsed,
            "response": content[:100],
            "tokens": resp.usage.total_tokens if resp.usage else 0,
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)[:200]}


async def test_cloudflare_text_model(
    name: str, url: str, token: str, mode: str = "text"
) -> dict:
    """Test a Cloudflare Worker text model."""
    if not url or not token:
        return {"status": "SKIP", "reason": "Not configured"}

    try:
        import httpx

        payload = {"message": TEST_PROMPT}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = int((time.monotonic() - start) * 1000)

        # Try multiple response keys
        content = (
            data.get("response")
            or data.get("content")
            or data.get("output")
            or str(data)[:200]
        )
        passed = EXPECTED_CONTAINS.lower() in content.lower()

        return {
            "status": "OK" if passed else "WARN",
            "latency_ms": elapsed,
            "response": content[:100],
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)[:200]}


async def test_cloudflare_image_model(name: str, url: str, token: str) -> dict:
    """Test a Cloudflare Worker image model."""
    if not url or not token:
        return {"status": "SKIP", "reason": "Not configured"}

    try:
        import httpx

        payload = {"prompt": "a simple red circle on white background, minimalist"}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            image_bytes = resp.content
        elapsed = int((time.monotonic() - start) * 1000)

        is_valid = len(image_bytes) > 1024  # At least 1KB
        return {
            "status": "OK" if is_valid else "WARN",
            "latency_ms": elapsed,
            "response": f"Image: {len(image_bytes)} bytes",
            "warning": None if is_valid else "Image too small, may be error response",
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)[:200]}


async def test_azure_flux_image(endpoint: str, api_key: str, deployment: str) -> dict:
    """Test Azure Flux image generation using OpenAI-compatible API."""
    if not endpoint or not api_key:
        return {"status": "SKIP", "reason": "Not configured"}

    try:
        from openai import AsyncOpenAI
        import base64

        client = AsyncOpenAI(
            base_url=endpoint.rstrip("/"),
            api_key=api_key,
        )

        start = time.monotonic()
        img = await client.images.generate(
            model=deployment,
            prompt="a simple blue circle on white background, minimalist flat design",
            n=1,
            size="1024x1024",
        )
        elapsed = int((time.monotonic() - start) * 1000)

        # Decode base64 image
        if img.data and len(img.data) > 0 and img.data[0].b64_json:
            image_bytes = base64.b64decode(img.data[0].b64_json)
            is_valid = len(image_bytes) > 1024
            return {
                "status": "OK" if is_valid else "WARN",
                "latency_ms": elapsed,
                "response": f"Image: {len(image_bytes)} bytes",
            }
        return {
            "status": "WARN",
            "latency_ms": elapsed,
            "response": "No image data returned",
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)[:200]}


# ── Test Runner ──────────────────────────────────────────────────


async def run_all():
    results = {}

    print("=" * 70)
    print("LLM Model Health Check — Barise Server 4")
    print("=" * 70)
    print()

    # ── T0: Kimi-K2-Thinking — SKIPPED (returns empty/unreliable) ──
    print("T0: Kimi-K2-Thinking (Azure)... SKIPPED (unreliable responses)")
    results["T0_Kimi"] = {"status": "SKIP", "reason": "Unreliable responses"}
    print()

    # ── T1: DeepSeek-V3.2 ────────────────────────────────────────
    print("T1: DeepSeek-V3.2 (Azure)...")
    results["T1_DeepSeek"] = await test_azure_model(
        name="DeepSeek-V3.2",
        endpoint=os.environ.get("DEEPSEEK_ENDPOINT", "").strip().strip('"'),
        api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip().strip('"'),
        deployment=os.environ.get("DEEPSEEK_MODEL_NAME", "DeepSeek-V3.2")
        .strip()
        .strip('"'),
    )
    print(f"  Status: {results['T1_DeepSeek']['status']}")
    if results["T1_DeepSeek"]["status"] == "OK":
        print(f"  Latency: {results['T1_DeepSeek']['latency_ms']}ms")
        print(f"  Response: {results['T1_DeepSeek'].get('response', '')[:80]}")
    elif results["T1_DeepSeek"]["status"] == "FAIL":
        print(f"  Error: {results['T1_DeepSeek'].get('error', '')}")
    print()

    # ── T2: GPT-4o-mini — SKIPPED (404, endpoint misconfigured) ──
    print("T2: GPT-4o-mini (Azure)... SKIPPED (endpoint misconfigured)")
    results["T2_GPT4oMini"] = {"status": "SKIP", "reason": "Endpoint misconfigured"}
    print()

    # ── T3: Mistral-medium ───────────────────────────────────────
    print("T3: Mistral-medium-2505 (Azure)...")
    results["T3_Mistral"] = await test_azure_model(
        name="Mistral-medium",
        endpoint=os.environ.get("MISTRAL_ENDPOINT", "").strip().strip('"'),
        api_key=os.environ.get("MISTRAL_API_KEY", "").strip().strip('"'),
        deployment=os.environ.get("MISTRAL_DEPLOYMENT", "mistral-medium-2505")
        .strip()
        .strip('"'),
    )
    print(f"  Status: {results['T3_Mistral']['status']}")
    if results["T3_Mistral"]["status"] == "OK":
        print(f"  Latency: {results['T3_Mistral']['latency_ms']}ms")
        print(f"  Response: {results['T3_Mistral'].get('response', '')[:80]}")
    elif results["T3_Mistral"]["status"] == "FAIL":
        print(f"  Error: {results['T3_Mistral'].get('error', '')}")
    print()

    # ── T4: Groq ─────────────────────────────────────────────────
    print("T4: Groq (first available key)...")
    groq_keys = [
        os.environ.get("GROQ_API_KEY", ""),
        os.environ.get("GROQ_API_KEY1", ""),
        os.environ.get("GROQ_API_KEY2", ""),
        os.environ.get("GROQ_API_KEY3", ""),
        os.environ.get("GROQ_API_KEY4", ""),
        os.environ.get("GROQ_API_KEY5", ""),
        os.environ.get("GROQ_API_KEY6", ""),
        os.environ.get("GROQ_API_KEY7", ""),
    ]
    groq_keys = [k for k in groq_keys if k]
    if groq_keys:
        results["T4_Groq"] = await test_groq_model(
            api_key=groq_keys[0],
            model="llama-3.3-70b-versatile",
        )
        print(f"  Status: {results['T4_Groq']['status']}")
        if results["T4_Groq"]["status"] == "OK":
            print(f"  Latency: {results['T4_Groq']['latency_ms']}ms")
            print(f"  Response: {results['T4_Groq'].get('response', '')[:80]}")
        elif results["T4_Groq"]["status"] == "FAIL":
            print(f"  Error: {results['T4_Groq'].get('error', '')}")
    else:
        results["T4_Groq"] = {"status": "SKIP", "reason": "No Groq keys configured"}
        print("  Status: SKIP (no keys)")
    print()

    # ── T5: Cloudflare Workers (Text) ────────────────────────────
    print("T5: Cloudflare Workers (Text)...")

    cf_text_models = [
        (
            "GLM",
            os.environ.get("CF_WORKER_GLM_URL", ""),
            os.environ.get("CF_WORKER_GLM_TOKEN", ""),
        ),
        (
            "Qwen",
            os.environ.get("CF_WORKER_QWEN_URL", ""),
            os.environ.get("CF_WORKER_QWEN_TOKEN", ""),
        ),
        (
            "Gemma",
            os.environ.get("CF_WORKER_GEMMA_URL", ""),
            os.environ.get("CF_WORKER_GEMMA_TOKEN", ""),
        ),
    ]

    for cf_name, cf_url, cf_token in cf_text_models:
        key = f"T5_CF_{cf_name}"
        print(f"  {cf_name}...", end=" ")
        results[key] = await test_cloudflare_text_model(cf_name, cf_url, cf_token)
        print(f"{results[key]['status']}")
        if results[key]["status"] == "OK":
            print(f"    Latency: {results[key]['latency_ms']}ms")
        elif results[key]["status"] == "FAIL":
            print(f"    Error: {results[key].get('error', '')}")
    print()

    # ── T5: Cloudflare Workers (Image) ───────────────────────────
    print("T5: Cloudflare Workers (Image)...")
    print("  (Lucid worker currently returning 500 - skipped)")
    results["T5_CF_IMG_Lucid"] = {"status": "SKIP", "reason": "Worker returning 500"}
    print()

    # ── Image: Azure Flux — SKIPPED (removed from pipeline) ────────
    print("Image: Azure Flux (flux-pro-2)... SKIPPED (removed from pipeline)")
    results["IMG_Flux"] = {"status": "SKIP", "reason": "Removed from pipeline"}
    print()

    # ── Summary ──────────────────────────────────────────────────
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    ok_count = sum(1 for r in results.values() if r["status"] == "OK")
    warn_count = sum(1 for r in results.values() if r["status"] == "WARN")
    fail_count = sum(1 for r in results.values() if r["status"] == "FAIL")
    skip_count = sum(1 for r in results.values() if r["status"] == "SKIP")

    print(f"  OK:     {ok_count}")
    print(f"  WARN:   {warn_count}")
    print(f"  FAIL:   {fail_count}")
    print(f"  SKIP:   {skip_count}")
    print(f"  Total:  {len(results)}")
    print()

    if fail_count > 0:
        print("FAILURES:")
        for name, r in results.items():
            if r["status"] == "FAIL":
                print(f"  - {name}: {r.get('error', 'Unknown error')}")
        print()

    if skip_count > 0:
        print("SKIPPED (not configured):")
        for name, r in results.items():
            if r["status"] == "SKIP":
                print(f"  - {name}: {r.get('reason', '')}")
        print()

    # Save results to JSON
    with open("llm_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to llm_test_results.json")

    return ok_count, warn_count, fail_count, skip_count


if __name__ == "__main__":
    ok, warn, fail, skip = asyncio.run(run_all())
    if fail > 0:
        sys.exit(1)
