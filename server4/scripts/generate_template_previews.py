"""
One-time script to pre-generate template preview background images
using the CF Phoenix image generation worker.

Usage:
    cd server4
    python scripts/generate_template_previews.py

Generates 5 images (one per template with preview_content), saves them
to server4/uploads/template_previews/, and outputs the URLs to paste
into template_definitions.json.

Uses CF_WORKER_PHOENIX_URL from .env (free tier, ~5s per image).
"""

import asyncio
import os
import sys
import json
import httpx
from pathlib import Path

# Add server4 to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


PHOENIX_URL = os.getenv("CF_WORKER_PHOENIX_URL", "").rstrip("/")
PHOENIX_TOKEN = os.getenv("CF_WORKER_PHOENIX_TOKEN", "")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "uploads" / "template_previews"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Carefully crafted prompts — one per template, designed for 16:9 backgrounds
# that work well under text overlays with dark scrim
TEMPLATE_PROMPTS = {
    "yc_pitch": (
        "Abstract geometric network of connected nodes and lines on dark navy "
        "background, subtle blue and purple gradients, fintech startup aesthetic, "
        "wide 16:9 composition, minimal, no text, leaves breathing room for headlines"
    ),
    "modern_pitch": (
        "Smooth flowing abstract gradient waves in coral and orange tones on dark "
        "background, modern glass morphism aesthetic, soft light reflections, "
        "wide 16:9, premium, no text overlay"
    ),
    "enterprise_sales": (
        "Clean minimal abstract architecture with soft light on white marble "
        "surface, subtle blue accents, corporate premium feel, wide 16:9, "
        "professional, no text, editorial photography style"
    ),
    "product_launch": (
        "Futuristic holographic interface elements floating in dark space, "
        "purple and cyan neon glow, product showcase aesthetic, wide 16:9, "
        "tech product launch, no text"
    ),
    "keynote_cinematic": (
        "Dramatic dark stage lighting with subtle spotlight cone from above, "
        "minimalist black background, metallic titanium surface reflections, "
        "wide 16:9, Apple keynote style, no text"
    ),
    "saas_onboarding": (
        "Soft welcoming pastel gradient with gentle floating UI cards and icons, "
        "SaaS onboarding aesthetic, friendly and approachable, wide 16:9, "
        "minimal text, clean modern design"
    ),
    "data_report": (
        "Abstract data visualization aesthetic with subtle grid lines and glowing "
        "chart bars on deep blue background, analytics dashboard feel, wide 16:9, "
        "no text, professional data-driven design"
    ),
    "company_overview": (
        "Warm corporate skyline silhouette at golden hour with soft gradient sky, "
        "company culture aesthetic, trustworthy and established, wide 16:9, "
        "no text, editorial photography style"
    ),
    "training_workshop": (
        "Bright energetic abstract shapes and learning symbols on clean white "
        "background, educational workshop aesthetic, approachable and clear, "
        "wide 16:9, no text, modern instructional design"
    ),
    "security_whitepaper": (
        "Dark cybersecurity aesthetic with shield and lock wireframe motifs, "
        "subtle green matrix-like grid on black background, wide 16:9, "
        "no text, technical and secure feel"
    ),
    "healthcare_clinical": (
        "Calming soft blue and white medical aesthetic with abstract DNA helix and "
        "cell patterns, clinical trust and care, wide 16:9, no text, "
        "clean biotech design"
    ),
    "fintech_investor": (
        "Sophisticated dark green and gold abstract financial graph lines rising, "
        "luxury fintech aesthetic, wealth and growth symbolism, wide 16:9, "
        "no text, premium investor feel"
    ),
    "ai_demo_day": (
        "Futuristic neural network visualization with glowing synaptic connections, "
        "AI and machine learning aesthetic, deep space purple background, wide 16:9, "
        "no text, cutting-edge technology feel"
    ),
    "board_meeting": (
        "Elegant dark wood boardroom table texture with subtle overhead lighting, "
        "executive corporate aesthetic, serious and authoritative, wide 16:9, "
        "no text, premium professional design"
    ),
    "deep_tech_architecture": (
        "Abstract technical blueprint aesthetic with circuit board traces and "
        "microchip patterns on dark background, engineering deep tech feel, "
        "wide 16:9, no text, precision and innovation"
    ),
    "vc_pitch_deck": (
        "Bold venture capital aesthetic with abstract rising bar chart silhouettes, "
        "confident startup energy, dark background with vibrant accent colors, "
        "wide 16:9, no text, investor-ready premium design"
    ),
    "executive_briefing": (
        "Minimal executive suite aesthetic with panoramic city skyline view, "
        "soft morning light, corporate leadership feel, wide 16:9, "
        "no text, authoritative and calm"
    ),
    "trust_compliance": (
        "Clean compliance and certification aesthetic with checkmark and shield "
        "motifs, subtle green accents on white background, wide 16:9, "
        "no text, trustworthy and verified feel"
    ),
    "cinematic_story": (
        "Dramatic cinematic storytelling aesthetic with film grain and soft "
        "vignette lighting, narrative emotional depth, wide 16:9, "
        "no text, movie poster quality"
    ),
    "seed_round_pitch": (
        "Early-stage startup energy with sprouting plant and growth motifs, "
        "fresh green and warm sunrise tones, wide 16:9, no text, "
        "hopeful and ambitious feel"
    ),
    "series_a_pitch": (
        "Growth-stage startup aesthetic with abstract scaling staircase and "
        "momentum lines, confident blue and orange palette, wide 16:9, "
        "no text, scaling and traction feel"
    ),
    "partnership_proposal": (
        "Warm handshake and collaboration aesthetic with interlocking shapes, "
        "soft earth tones and trust-building palette, wide 16:9, "
        "no text, partnership and unity feel"
    ),
    "customer_success": (
        "Bright customer-centric aesthetic with smiling abstract user profiles "
        "and satisfaction stars, warm and welcoming palette, wide 16:9, "
        "no text, success and happiness feel"
    ),
    "startup_story": (
        "Narrative journey aesthetic with winding road and milestone markers, "
        "adventure and perseverance symbolism, wide 16:9, no text, "
        "storytelling and inspiration feel"
    ),
    "minimal_agency": (
        "Ultra-minimal Swiss design aesthetic with bold typography grid and "
        "single accent color block, whitespace-forward, wide 16:9, "
        "no text, design agency portfolio feel"
    ),
    "edtech_course": (
        "Vibrant educational aesthetic with books, graduation cap and lightbulb "
        "motifs, playful yet structured palette, wide 16:9, no text, "
        "learning and discovery feel"
    ),
    "gamer_esports": (
        "Dynamic esports gaming aesthetic with RGB neon streaks and controller "
        "silhouettes, dark background with vibrant accents, wide 16:9, "
        "no text, competitive energy feel"
    ),
}


async def generate_one(template_id: str, prompt: str) -> str | None:
    """Generate one image via CF Phoenix, save to disk, return filename."""
    if not PHOENIX_URL:
        print(f"  X CF_WORKER_PHOENIX_URL not set, skipping {template_id}")
        return None

    print(f"  > Generating {template_id}...")

    headers = {}
    if PHOENIX_TOKEN:
        headers["Authorization"] = f"Bearer {PHOENIX_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                PHOENIX_URL,
                json={"prompt": prompt},
                headers=headers,
            )
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")

            if "json" in content_type:
                data = resp.json()
                # Some workers return base64 in JSON
                if "image" in data:
                    import base64
                    image_bytes = base64.b64decode(data["image"])
                elif "result" in data and isinstance(data["result"], str):
                    import base64
                    image_bytes = base64.b64decode(data["result"])
                else:
                    print(f"  X Unexpected JSON response for {template_id}: {list(data.keys())}")
                    return None
            else:
                image_bytes = resp.content

            if len(image_bytes) < 1024:
                print(f"  X Image too small for {template_id} ({len(image_bytes)} bytes)")
                return None

            # Determine extension from content type
            ext = "png" if "png" in content_type else "jpg"
            filename = f"{template_id}_preview.{ext}"
            filepath = OUTPUT_DIR / filename

            filepath.write_bytes(image_bytes)
            size_kb = len(image_bytes) // 1024
            print(f"  OK {template_id}: {filename} ({size_kb} KB)")
            return filename

    except Exception as e:
        print(f"  X Failed {template_id}: {e}")
        return None


async def main():
    print("=" * 60)
    print("Template Preview Image Generator")
    print(f"Phoenix URL: {PHOENIX_URL or '(not set)'}")
    print(f"Output dir:  {OUTPUT_DIR}")
    print("=" * 60)

    results = {}
    for tid, prompt in TEMPLATE_PROMPTS.items():
        filename = await generate_one(tid, prompt)
        if filename:
            # URL path served by server4's static file router
            results[tid] = f"/api/v4/uploads/template_previews/{filename}"
        # Small delay between requests to be gentle on free tier
        await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print("Results:")
    print(json.dumps(results, indent=2))
    print("=" * 60)

    if results:
        print(f"\nOK Generated {len(results)}/{len(TEMPLATE_PROMPTS)} images")
        print("  Add the URLs as 'background_image' in preview_content slides.")
    else:
        print("\nX No images generated. Check CF_WORKER_PHOENIX_URL in .env")


if __name__ == "__main__":
    asyncio.run(main())
