"""
Phase 8 Pre-Implementation — Image Generation Model Testing.

Tests ALL available image generation endpoints:
1. Azure FLUX.1-Kontext-pro (Azure AI)
2. Cloudflare Phoenix Worker (free)
3. Cloudflare Lucid Worker (free)
4. Nvidia Stable Diffusion 3 Medium (free)

Reports: status, latency, response format, image size, errors.
"""

import base64
import io
import os
import sys
import time
import json
import traceback

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
env_vars = {}
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env_vars[key] = value
            os.environ.setdefault(key, value)

# ── Config ────────────────────────────────────────────────────
AZURE_FLUX_ENDPOINT = env_vars.get("AZURE_FLUX_ENDPOINT", "")
AZURE_FLUX_API_KEY = env_vars.get("AZURE_FLUX_API_KEY", "")
AZURE_FLUX_DEPLOYMENT = env_vars.get("AZURE_FLUX_DEPLOYMENT_NAME", "FLUX.1-Kontext-pro")

CF_PHOENIX_URL = env_vars.get("CF_WORKER_PHOENIX_URL", "")
CF_PHOENIX_TOKEN = env_vars.get("CF_WORKER_PHOENIX_TOKEN", "")
CF_LUCID_URL = env_vars.get("CF_WORKER_LUCID_URL", "")
CF_LUCID_TOKEN = env_vars.get("CF_WORKER_LUCID_TOKEN", "")

NVIDIA_API_KEY = env_vars.get("Nvidia_stable_api_key", "")

TEST_PROMPT = (
    "A modern minimalist office building with glass facade reflecting sunset, "
    "professional architectural photography, clean lines, warm golden hour lighting, "
    "no text, no people, high quality, 16:9 aspect ratio"
)

SHORT_PROMPT = "A blue abstract geometric pattern, professional, clean design"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.latency_ms = 0
        self.response_format = ""
        self.image_size_bytes = 0
        self.content_type = ""
        self.error = ""
        self.details = {}
        self.raw_response_keys = []

    def __str__(self):
        status = "PASS" if self.success else "FAIL"
        s = f"\n{'='*60}\n"
        s += f"  [{status}] {self.name}\n"
        s += f"{'='*60}\n"
        s += f"  Latency:         {self.latency_ms}ms\n"
        s += f"  Response Format:  {self.response_format}\n"
        s += f"  Image Size:       {self.image_size_bytes} bytes ({self.image_size_bytes//1024}KB)\n"
        s += f"  Content Type:     {self.content_type}\n"
        if self.raw_response_keys:
            s += f"  Response Keys:    {self.raw_response_keys}\n"
        if self.details:
            for k, v in self.details.items():
                s += f"  {k}: {v}\n"
        if self.error:
            s += f"  ERROR: {self.error}\n"
        return s


def save_test_image(name: str, image_bytes: bytes):
    """Save test image to disk for visual verification."""
    out_dir = Path(__file__).parent / "test_images"
    out_dir.mkdir(exist_ok=True)
    # Detect format from magic bytes
    ext = "bin"
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        ext = "png"
    elif image_bytes[:2] == b'\xff\xd8':
        ext = "jpg"
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        ext = "webp"
    path = out_dir / f"{name}.{ext}"
    path.write_bytes(image_bytes)
    print(f"  Saved: {path} ({len(image_bytes)//1024}KB)")
    return str(path)


# ══════════════════════════════════════════════════════════════
# TEST 1: Azure FLUX.1-Kontext-pro
# ══════════════════════════════════════════════════════════════

def test_azure_flux_kontext():
    """Test Azure FLUX.1-Kontext-pro image generation.

    FLUX.1-Kontext-pro on Azure uses the AI model inference API.
    We try multiple endpoint patterns to discover the correct one.
    """
    import requests

    result = TestResult("Azure FLUX.1-Kontext-pro")

    if not AZURE_FLUX_ENDPOINT or not AZURE_FLUX_API_KEY:
        result.error = "AZURE_FLUX_ENDPOINT or AZURE_FLUX_API_KEY not configured"
        return result

    base_url = AZURE_FLUX_ENDPOINT.rstrip("/")

    # Headers for Azure
    headers_openai = {
        "api-key": AZURE_FLUX_API_KEY,
        "Content-Type": "application/json",
    }

    headers_bearer = {
        "Authorization": f"Bearer {AZURE_FLUX_API_KEY}",
        "Content-Type": "application/json",
    }

    # ── Attempt 1: Azure OpenAI images/generations endpoint ──
    # Pattern: {base}/deployments/{deployment}/images/generations?api-version=...
    # Since base already has /openai/v1/, strip it for standard Azure format
    azure_base = base_url.replace("/openai/v1", "").replace("/openai/v1/", "")

    attempts = [
        {
            "name": "Azure OpenAI images/generations (api-key header)",
            "url": f"{azure_base}/openai/deployments/{AZURE_FLUX_DEPLOYMENT}/images/generations?api-version=2024-12-01-preview",
            "headers": headers_openai,
            "payload": {
                "prompt": SHORT_PROMPT,
                "n": 1,
                "size": "1024x1024",
            },
        },
        {
            "name": "Azure AI Inference /images/generations (Bearer)",
            "url": f"{base_url}/images/generations",
            "headers": headers_bearer,
            "payload": {
                "prompt": SHORT_PROMPT,
                "n": 1,
                "size": "1024x1024",
            },
        },
        {
            "name": "Azure AI Inference direct model endpoint (Bearer)",
            "url": f"{azure_base}/models/{AZURE_FLUX_DEPLOYMENT}/images/generations",
            "headers": headers_bearer,
            "payload": {
                "prompt": SHORT_PROMPT,
                "size": "1024x1024",
            },
        },
        {
            "name": "Azure OpenAI /images/generations (api-key, no deployment path)",
            "url": f"{azure_base}/openai/images/generations?api-version=2024-12-01-preview",
            "headers": {**headers_openai, "model": AZURE_FLUX_DEPLOYMENT},
            "payload": {
                "prompt": SHORT_PROMPT,
                "model": AZURE_FLUX_DEPLOYMENT,
                "n": 1,
                "size": "1024x1024",
            },
        },
        {
            "name": "Azure AI Services Inference (Services endpoint)",
            "url": f"{azure_base.replace('.openai.azure.com', '.services.ai.azure.com')}/models/{AZURE_FLUX_DEPLOYMENT}/images/generations",
            "headers": headers_bearer,
            "payload": {
                "prompt": SHORT_PROMPT,
                "size": "1024x1024",
            },
        },
    ]

    for attempt in attempts:
        print(f"\n  Trying: {attempt['name']}")
        print(f"  URL: {attempt['url']}")
        start = time.monotonic()
        try:
            resp = requests.post(
                attempt["url"],
                headers=attempt["headers"],
                json=attempt["payload"],
                timeout=120,
            )
            elapsed = int((time.monotonic() - start) * 1000)

            print(f"  Status: {resp.status_code}")
            print(f"  Latency: {elapsed}ms")

            # Try to parse response
            ct = resp.headers.get("Content-Type", "")
            print(f"  Content-Type: {ct}")

            if resp.status_code == 200:
                if "application/json" in ct:
                    data = resp.json()
                    result.raw_response_keys = list(data.keys()) if isinstance(data, dict) else ["(list)"]
                    print(f"  Response keys: {result.raw_response_keys}")

                    # Try to extract image from various response formats
                    image_bytes = None

                    # OpenAI format: data[0].b64_json or data[0].url
                    if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                        item = data["data"][0]
                        if isinstance(item, dict):
                            print(f"  Data item keys: {list(item.keys())}")
                            if "b64_json" in item:
                                image_bytes = base64.b64decode(item["b64_json"])
                                result.response_format = "JSON with b64_json"
                            elif "url" in item:
                                result.response_format = f"JSON with URL: {item['url'][:100]}"
                                result.details["image_url"] = item["url"][:200]
                                # Try to download the image
                                try:
                                    img_resp = requests.get(item["url"], timeout=30)
                                    if img_resp.status_code == 200:
                                        image_bytes = img_resp.content
                                except Exception as e:
                                    print(f"  Failed to download image URL: {e}")

                    # Azure AI format: image.base64 or artifacts
                    elif "image" in data:
                        img_data = data["image"]
                        if isinstance(img_data, dict) and "base64" in img_data:
                            image_bytes = base64.b64decode(img_data["base64"])
                            result.response_format = "JSON with image.base64"
                        elif isinstance(img_data, str):
                            image_bytes = base64.b64decode(img_data)
                            result.response_format = "JSON with image (base64 string)"

                    # Result format
                    elif "result" in data:
                        r = data["result"]
                        if isinstance(r, dict) and "image" in r:
                            image_bytes = base64.b64decode(r["image"])
                            result.response_format = "JSON with result.image"

                    # Output format
                    elif "output" in data:
                        o = data["output"]
                        if isinstance(o, str):
                            try:
                                image_bytes = base64.b64decode(o)
                                result.response_format = "JSON with output (base64)"
                            except Exception:
                                pass

                    if image_bytes and len(image_bytes) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(image_bytes)
                        result.content_type = ct
                        result.details["working_endpoint"] = attempt["name"]
                        result.details["working_url"] = attempt["url"]
                        save_test_image("azure_flux_kontext", image_bytes)
                        return result
                    else:
                        print(f"  Response JSON (first 500 chars): {json.dumps(data)[:500]}")

                elif "image/" in ct:
                    # Direct image response
                    image_bytes = resp.content
                    if len(image_bytes) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(image_bytes)
                        result.content_type = ct
                        result.response_format = f"Direct image ({ct})"
                        result.details["working_endpoint"] = attempt["name"]
                        result.details["working_url"] = attempt["url"]
                        save_test_image("azure_flux_kontext", image_bytes)
                        return result
                else:
                    print(f"  Response (first 500 chars): {resp.text[:500]}")

            else:
                error_text = resp.text[:300]
                print(f"  Error: {error_text}")
                result.details[f"attempt_{attempt['name']}_status"] = resp.status_code
                result.details[f"attempt_{attempt['name']}_error"] = error_text[:200]

        except requests.exceptions.Timeout:
            elapsed = int((time.monotonic() - start) * 1000)
            print(f"  TIMEOUT after {elapsed}ms")
        except Exception as e:
            print(f"  Exception: {e}")

    result.error = "All endpoint patterns failed. See details for each attempt."
    return result


# ══════════════════════════════════════════════════════════════
# TEST 2: Cloudflare Phoenix Worker
# ══════════════════════════════════════════════════════════════

def test_cloudflare_phoenix():
    """Test Cloudflare Phoenix image generation worker."""
    import requests

    result = TestResult("Cloudflare Phoenix (CF Worker)")

    if not CF_PHOENIX_URL or not CF_PHOENIX_TOKEN:
        result.error = "CF_WORKER_PHOENIX_URL or CF_WORKER_PHOENIX_TOKEN not configured"
        return result

    url = CF_PHOENIX_URL.rstrip("/")

    # Try multiple payload formats
    payloads = [
        {
            "name": "Standard prompt format",
            "data": {"prompt": SHORT_PROMPT},
        },
        {
            "name": "With num_steps",
            "data": {"prompt": SHORT_PROMPT, "num_steps": 20},
        },
        {
            "name": "Message format",
            "data": {"message": SHORT_PROMPT},
        },
    ]

    # Try with Bearer token
    headers = {
        "Authorization": f"Bearer {CF_PHOENIX_TOKEN}",
        "Content-Type": "application/json",
    }

    for payload in payloads:
        print(f"\n  Trying: {payload['name']}")
        start = time.monotonic()
        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload["data"],
                timeout=90,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            ct = resp.headers.get("Content-Type", "")

            print(f"  Status: {resp.status_code}, Content-Type: {ct}, Latency: {elapsed}ms")

            if resp.status_code == 200:
                # Check if response is raw image bytes
                if "image/" in ct or "octet-stream" in ct:
                    image_bytes = resp.content
                    if len(image_bytes) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(image_bytes)
                        result.content_type = ct
                        result.response_format = f"Direct image bytes ({ct})"
                        result.details["working_payload"] = payload["name"]
                        save_test_image("cf_phoenix", image_bytes)
                        return result
                    else:
                        print(f"  Image too small: {len(image_bytes)} bytes")

                # JSON response
                elif "json" in ct:
                    data = resp.json()
                    result.raw_response_keys = list(data.keys()) if isinstance(data, dict) else ["(list)"]
                    print(f"  Response keys: {result.raw_response_keys}")

                    image_bytes = None
                    # Try base64 extraction
                    if isinstance(data, dict):
                        for key in ["image", "result", "output", "data", "b64_json"]:
                            if key in data:
                                val = data[key]
                                if isinstance(val, str):
                                    try:
                                        image_bytes = base64.b64decode(val)
                                        if len(image_bytes) > 1000:
                                            result.response_format = f"JSON with {key} (base64)"
                                            break
                                    except Exception:
                                        pass
                                elif isinstance(val, list) and len(val) > 0:
                                    item = val[0]
                                    if isinstance(item, dict):
                                        for subkey in ["b64_json", "image", "base64"]:
                                            if subkey in item:
                                                try:
                                                    image_bytes = base64.b64decode(item[subkey])
                                                    if len(image_bytes) > 1000:
                                                        result.response_format = f"JSON with {key}[0].{subkey}"
                                                        break
                                                except Exception:
                                                    pass

                    if image_bytes and len(image_bytes) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(image_bytes)
                        result.content_type = ct
                        result.details["working_payload"] = payload["name"]
                        save_test_image("cf_phoenix", image_bytes)
                        return result
                    else:
                        print(f"  JSON response (first 300): {json.dumps(data)[:300]}")
                else:
                    # Unknown content type, check size
                    if len(resp.content) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(resp.content)
                        result.content_type = ct
                        result.response_format = f"Raw bytes ({ct})"
                        result.details["working_payload"] = payload["name"]
                        save_test_image("cf_phoenix", resp.content)
                        return result
                    print(f"  Response (first 300): {resp.text[:300]}")
            else:
                print(f"  Error: {resp.text[:300]}")

        except requests.exceptions.Timeout:
            print(f"  TIMEOUT")
        except Exception as e:
            print(f"  Exception: {e}")

    result.error = "All payload formats failed"
    return result


# ══════════════════════════════════════════════════════════════
# TEST 3: Cloudflare Lucid Worker
# ══════════════════════════════════════════════════════════════

def test_cloudflare_lucid():
    """Test Cloudflare Lucid image generation worker."""
    import requests

    result = TestResult("Cloudflare Lucid (CF Worker)")

    if not CF_LUCID_URL or not CF_LUCID_TOKEN:
        result.error = "CF_WORKER_LUCID_URL or CF_WORKER_LUCID_TOKEN not configured"
        return result

    url = CF_LUCID_URL.rstrip("/")
    headers = {
        "Authorization": f"Bearer {CF_LUCID_TOKEN}",
        "Content-Type": "application/json",
    }

    payloads = [
        {"name": "Standard prompt", "data": {"prompt": SHORT_PROMPT}},
        {"name": "With num_steps", "data": {"prompt": SHORT_PROMPT, "num_steps": 20}},
        {"name": "Message format", "data": {"message": SHORT_PROMPT}},
    ]

    for payload in payloads:
        print(f"\n  Trying: {payload['name']}")
        start = time.monotonic()
        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload["data"],
                timeout=90,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            ct = resp.headers.get("Content-Type", "")

            print(f"  Status: {resp.status_code}, Content-Type: {ct}, Latency: {elapsed}ms")

            if resp.status_code == 200:
                if "image/" in ct or "octet-stream" in ct:
                    image_bytes = resp.content
                    if len(image_bytes) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(image_bytes)
                        result.content_type = ct
                        result.response_format = f"Direct image bytes ({ct})"
                        result.details["working_payload"] = payload["name"]
                        save_test_image("cf_lucid", image_bytes)
                        return result
                    else:
                        print(f"  Too small: {len(image_bytes)} bytes")

                elif "json" in ct:
                    data = resp.json()
                    result.raw_response_keys = list(data.keys()) if isinstance(data, dict) else ["(list)"]
                    print(f"  Response keys: {result.raw_response_keys}")

                    image_bytes = None
                    if isinstance(data, dict):
                        for key in ["image", "result", "output", "data", "b64_json"]:
                            if key in data:
                                val = data[key]
                                if isinstance(val, str):
                                    try:
                                        image_bytes = base64.b64decode(val)
                                        if len(image_bytes) > 1000:
                                            result.response_format = f"JSON with {key} (base64)"
                                            break
                                    except Exception:
                                        pass

                    if image_bytes and len(image_bytes) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(image_bytes)
                        result.content_type = ct
                        result.details["working_payload"] = payload["name"]
                        save_test_image("cf_lucid", image_bytes)
                        return result
                    else:
                        print(f"  JSON (first 300): {json.dumps(data)[:300]}")
                else:
                    if len(resp.content) > 1000:
                        result.success = True
                        result.latency_ms = elapsed
                        result.image_size_bytes = len(resp.content)
                        result.content_type = ct
                        result.response_format = f"Raw bytes ({ct})"
                        save_test_image("cf_lucid", resp.content)
                        return result
                    print(f"  Response (first 300): {resp.text[:300]}")
            else:
                print(f"  Error: {resp.text[:300]}")

        except requests.exceptions.Timeout:
            print(f"  TIMEOUT")
        except Exception as e:
            print(f"  Exception: {e}")

    result.error = "All payload formats failed"
    return result


# ══════════════════════════════════════════════════════════════
# TEST 4: Nvidia Stable Diffusion 3 Medium
# ══════════════════════════════════════════════════════════════

def test_nvidia_stable_diffusion():
    """Test Nvidia Stable Diffusion 3 Medium via Nvidia API."""
    import requests

    result = TestResult("Nvidia Stable Diffusion 3 Medium")

    if not NVIDIA_API_KEY:
        result.error = "Nvidia_stable_api_key not configured in .env"
        return result

    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium"

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
    }

    payload = {
        "prompt": SHORT_PROMPT,
        "cfg_scale": 5,
        "aspect_ratio": "16:9",
        "seed": 0,
        "steps": 50,
        "negative_prompt": "blurry, text, watermark, low quality, deformed",
    }

    print(f"\n  URL: {url}")
    print(f"  Prompt: {SHORT_PROMPT[:80]}...")

    start = time.monotonic()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        elapsed = int((time.monotonic() - start) * 1000)
        ct = resp.headers.get("Content-Type", "")

        print(f"  Status: {resp.status_code}, Content-Type: {ct}, Latency: {elapsed}ms")

        if resp.status_code == 200:
            data = resp.json()
            result.raw_response_keys = list(data.keys()) if isinstance(data, dict) else []
            print(f"  Response keys: {result.raw_response_keys}")

            # Nvidia returns {"image": "<base64>", "seed": ..., ...}
            image_bytes = None

            if "image" in data:
                try:
                    image_bytes = base64.b64decode(data["image"])
                    result.response_format = "JSON with image (base64)"
                except Exception:
                    pass

            # Or it might be in artifacts
            if not image_bytes and "artifacts" in data:
                artifacts = data["artifacts"]
                if isinstance(artifacts, list) and len(artifacts) > 0:
                    art = artifacts[0]
                    if "base64" in art:
                        image_bytes = base64.b64decode(art["base64"])
                        result.response_format = "JSON with artifacts[0].base64"

            # Or data array like OpenAI
            if not image_bytes and "data" in data:
                items = data["data"]
                if isinstance(items, list) and len(items) > 0:
                    item = items[0]
                    if isinstance(item, dict):
                        for key in ["b64_json", "image", "base64"]:
                            if key in item:
                                try:
                                    image_bytes = base64.b64decode(item[key])
                                    result.response_format = f"JSON with data[0].{key}"
                                    break
                                except Exception:
                                    pass

            if image_bytes and len(image_bytes) > 1000:
                result.success = True
                result.latency_ms = elapsed
                result.image_size_bytes = len(image_bytes)
                result.content_type = ct
                result.details["seed"] = data.get("seed", "N/A")
                result.details["finish_reason"] = data.get("finish_reason", "N/A")
                save_test_image("nvidia_sd3", image_bytes)
                return result
            else:
                print(f"  JSON (first 500): {json.dumps(data)[:500]}")

        else:
            error = resp.text[:500]
            print(f"  Error: {error}")
            result.error = f"HTTP {resp.status_code}: {error[:200]}"

    except requests.exceptions.Timeout:
        result.error = "Request timed out (120s)"
    except Exception as e:
        result.error = f"Exception: {str(e)}"
        traceback.print_exc()

    return result


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  IMAGE GENERATION MODEL TEST SUITE")
    print("  Testing all 4 image providers for Phase 8")
    print("=" * 70)

    # Print config status
    print("\n── Configuration Status ──")
    print(f"  Azure Flux Endpoint:    {'SET' if AZURE_FLUX_ENDPOINT else 'MISSING'}")
    print(f"  Azure Flux API Key:     {'SET' if AZURE_FLUX_API_KEY else 'MISSING'}")
    print(f"  Azure Flux Deployment:  {AZURE_FLUX_DEPLOYMENT}")
    print(f"  CF Phoenix URL:         {'SET' if CF_PHOENIX_URL else 'MISSING'}")
    print(f"  CF Phoenix Token:       {'SET' if CF_PHOENIX_TOKEN else 'MISSING'}")
    print(f"  CF Lucid URL:           {'SET' if CF_LUCID_URL else 'MISSING'}")
    print(f"  CF Lucid Token:         {'SET' if CF_LUCID_TOKEN else 'MISSING'}")
    print(f"  Nvidia SD3 API Key:     {'SET' if NVIDIA_API_KEY else 'MISSING'}")

    results = []

    # Test 1: Azure FLUX.1-Kontext-pro
    print("\n\n" + "=" * 70)
    print("  TEST 1: Azure FLUX.1-Kontext-pro")
    print("=" * 70)
    r1 = test_azure_flux_kontext()
    results.append(r1)
    print(r1)

    # Test 2: Cloudflare Phoenix
    print("\n\n" + "=" * 70)
    print("  TEST 2: Cloudflare Phoenix Worker")
    print("=" * 70)
    r2 = test_cloudflare_phoenix()
    results.append(r2)
    print(r2)

    # Test 3: Cloudflare Lucid
    print("\n\n" + "=" * 70)
    print("  TEST 3: Cloudflare Lucid Worker")
    print("=" * 70)
    r3 = test_cloudflare_lucid()
    results.append(r3)
    print(r3)

    # Test 4: Nvidia Stable Diffusion 3
    print("\n\n" + "=" * 70)
    print("  TEST 4: Nvidia Stable Diffusion 3 Medium")
    print("=" * 70)
    r4 = test_nvidia_stable_diffusion()
    results.append(r4)
    print(r4)

    # ── Summary ──
    print("\n\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    working = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\n  Working: {len(working)}/4")
    print(f"  Failed:  {len(failed)}/4\n")

    for r in results:
        status = "PASS" if r.success else "FAIL"
        latency = f"{r.latency_ms}ms" if r.success else "N/A"
        size = f"{r.image_size_bytes//1024}KB" if r.success else "N/A"
        fmt = r.response_format if r.success else r.error[:60]
        print(f"  [{status}] {r.name:<45} {latency:>8}  {size:>8}  {fmt}")

    if working:
        print(f"\n  Recommended fallback chain:")
        # Sort by: quality (flux > sd3 > phoenix > lucid), then by latency
        priority = {
            "Azure FLUX.1-Kontext-pro": 1,
            "Nvidia Stable Diffusion 3 Medium": 2,
            "Cloudflare Phoenix (CF Worker)": 3,
            "Cloudflare Lucid (CF Worker)": 4,
        }
        sorted_working = sorted(working, key=lambda r: priority.get(r.name, 99))
        for i, r in enumerate(sorted_working, 1):
            print(f"    {i}. {r.name} ({r.latency_ms}ms, {r.image_size_bytes//1024}KB)")

    print(f"\n  Test images saved to: {Path(__file__).parent / 'test_images'}/")
    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
