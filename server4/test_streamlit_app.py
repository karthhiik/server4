"""
Streamlit Test App for Server4 Slide & Image Generation

Run: streamlit run test_streamlit_app.py
Tests:
1. Slide content generation (all 12 layouts)
2. Image generation (Lucid worker)
3. HtmlBuilder output quality
4. PptxBuilder output
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

import streamlit as st

# Add server4 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server4"))

# Load env vars
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "server4", ".env"))


st.set_page_config(
    page_title="Barise Server4 Test Dashboard",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Barise Server4 — Slide & Image Generation Test")
st.markdown("---")


# ── Test Configuration ──────────────────────────────────────────

st.sidebar.header("Test Configuration")
test_topic = st.sidebar.text_input("Topic", value="AI in Healthcare")
test_purpose = st.sidebar.selectbox(
    "Purpose",
    ["pitch", "demo_day", "investor_update", "internal", "sales"],
)
test_style = st.sidebar.selectbox(
    "Writing Style",
    ["yc_pitch", "narrative", "analytical", "technical", "minimalist"],
)
test_slide_count = st.sidebar.slider("Slide Count", 3, 12, 6)

st.sidebar.markdown("---")
st.sidebar.header("Test Sections")
run_slide_test = st.sidebar.checkbox("Test Slide Generation", value=True)
run_image_test = st.sidebar.checkbox("Test Image Generation", value=True)
run_html_test = st.sidebar.checkbox("Test HTML Builder", value=True)
run_pptx_test = st.sidebar.checkbox("Test PPTX Builder", value=True)


# ── Helper Functions ────────────────────────────────────────────


def load_dotenv_manual():
    """Load .env file manually from server4 directory."""
    # Try multiple paths to find .env
    possible_paths = [
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".env"
        ),  # Same dir as script
        os.path.join(os.getcwd(), ".env"),  # Current working directory
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "server4", ".env"
        ),  # server4 subfolder
    ]

    for env_path in possible_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ.setdefault(key, value)
            return True
    return False


def get_available_models():
    """Check which models are configured."""
    models = {}

    # DeepSeek
    ds_endpoint = os.environ.get("DEEPSEEK_ENDPOINT", "")
    ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if ds_endpoint and ds_key:
        models["deepseek-v3"] = "✅ Configured"
    else:
        models["deepseek-v3"] = "❌ Not configured"

    # Mistral - check both case variants
    mistral_endpoint = (
        os.environ.get("MISTRAL_ENDPOINT") or os.environ.get("Mistral_endpoint") or ""
    )
    mistral_key = (
        os.environ.get("MISTRAL_API_KEY") or os.environ.get("Mistral_api_key") or ""
    )
    if mistral_endpoint and mistral_key:
        models["mistral-medium"] = "✅ Configured"
    else:
        models["mistral-medium"] = "❌ Not configured"

    # Groq - check all 8 possible keys
    groq_keys = []
    for i in range(8):
        key_name = f"GROQ_API_KEY{i}" if i > 0 else "GROQ_API_KEY"
        key = os.environ.get(key_name, "")
        if key:
            groq_keys.append(key)
    if groq_keys:
        models["groq"] = f"✅ {len(groq_keys)} key(s)"
    else:
        models["groq"] = "❌ Not configured"

    # CF Qwen
    qwen_url = os.environ.get("CF_WORKER_QWEN_URL", "")
    qwen_token = os.environ.get("CF_WORKER_QWEN_TOKEN", "")
    if qwen_url and qwen_token:
        models["cf-qwen"] = "✅ Configured"
    else:
        models["cf-qwen"] = "❌ Not configured"

    # CF Gemma
    gemma_url = os.environ.get("CF_WORKER_GEMMA_URL", "")
    gemma_token = os.environ.get("CF_WORKER_GEMMA_TOKEN", "")
    if gemma_url and gemma_token:
        models["cf-gemma"] = "✅ Configured"
    else:
        models["cf-gemma"] = "❌ Not configured"

    return models


def run_async(coro):
    """Run async code in Streamlit thread-safe way."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Main App ────────────────────────────────────────────────────

env_loaded = load_dotenv_manual()

if not env_loaded:
    st.warning(
        "⚠️ .env file not found. Please ensure server4/.env exists with API keys."
    )

# Show model status
st.header("📊 Model Status")
models = get_available_models()
cols = st.columns(len(models))
for i, (model, status) in enumerate(models.items()):
    cols[i].metric(model, status.split()[0])

st.markdown("---")

# ── Test 1: Slide Generation ────────────────────────────────────

if run_slide_test:
    st.header("📝 Test 1: Slide Content Generation")

    if st.button("Run Slide Generation Test", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            from app.services.llm.model_router import ModelRouter, TaskType
            from app.mcp.brain_mcp.prompts.prompt_engine import PromptEngine

            router = ModelRouter.get_instance()
            engine = PromptEngine()

            # Test each layout
            layouts = [
                "title-hero",
                "bullets",
                "two-column",
                "bullets-with-image",
                "chart",
                "comparison",
                "timeline",
                "quote",
                "team-grid",
                "kpi-dashboard",
                "full-image",
                "blank",
            ]

            results = {}
            total = len(layouts)

            for i, layout in enumerate(layouts):
                progress_bar.progress((i + 1) / total)
                status_text.text(f"Generating {layout} slide... ({i + 1}/{total})")

                # Compose prompt
                system_prompt = engine.compose_slide_prompt(
                    layout=layout,
                    style=test_style,
                    purpose=test_purpose,
                    slide_purpose=f"{test_topic} {layout}",
                )

                user_prompt = f"""Generate content for a '{layout}' layout slide about {test_topic}.
                
Return ONLY valid JSON with these fields:
- title: string (3-8 words)
- bullets: array of 3-6 strings (for bullets layout)
- subtitle: string (for title-hero)
- left_content, right_content: strings (for two-column)
- chart_type, chart_data: for chart layout
- events: array for timeline
- quote_text, quote_author, quote_role: for quote
- members: array for team-grid
- metrics: array for kpi-dashboard

CRITICAL: Return ONLY JSON, no markdown, no explanation."""

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]

                try:
                    response = run_async(
                        router.complete(
                            task_type=TaskType.STRUCTURED_JSON,
                            messages=messages,
                            temperature=0.6,
                            max_tokens=2048,
                            response_format={"type": "json_object"},
                        )
                    )

                    # Parse response
                    import json

                    text = response.content.strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()
                    if text.lower().startswith("json"):
                        text = text[4:].strip()

                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        data = json.loads(text[start:end])
                        results[layout] = {
                            "status": "✅ Success",
                            "content": data,
                            "latency_ms": response.latency_ms,
                            "model": response.model,
                        }
                    else:
                        results[layout] = {
                            "status": "⚠️ Parse Error",
                            "raw": text[:200],
                        }

                except Exception as e:
                    results[layout] = {
                        "status": f"❌ Failed: {str(e)[:100]}",
                    }

            status_text.text("✅ All slides generated!")
            progress_bar.progress(1.0)

            # Display results
            st.success(
                f"Generated {len([r for r in results.values() if '✅' in r['status']])}/{total} slides successfully"
            )

            # Show each slide
            for layout, result in results.items():
                with st.expander(
                    f"{layout.upper()} — {result['status']}", expanded=True
                ):
                    if "content" in result:
                        st.json(result["content"])
                        st.caption(
                            f"Model: {result.get('model', 'N/A')} | Latency: {result.get('latency_ms', 'N/A')}ms"
                        )
                    else:
                        st.error(
                            result.get("raw", result.get("status", "Unknown error"))
                        )

        except Exception as e:
            st.error(f"Test failed: {str(e)}")
            st.exception(e)

# ── Test 2: Image Generation ────────────────────────────────────

if run_image_test:
    st.header("🖼️ Test 2: Image Generation")

    if st.button("Run Image Generation Test", type="primary"):
        try:
            from app.services.image_service import ImageService

            service = ImageService()

            # Test image generation
            test_content = {
                "title": "AI in Healthcare",
                "bullets": [
                    "AI reduces diagnostic errors by 40% — Source: Nature Medicine 2025",
                    "Market size: $180B by 2028 — Source: McKinsey 2025",
                ],
            }
            test_theme = {
                "theme_id": "medical-clean",
                "colors": {"primary": "#0ea5e9"},
            }

            with st.spinner("Generating image..."):
                image_url = run_async(
                    service.generate_slide_image(
                        content=test_content,
                        layout="bullets-with-image",
                        theme=test_theme,
                        presentation_id="test_123",
                    )
                )

            if image_url:
                st.success("✅ Image generated successfully!")
                st.image(image_url, caption="Generated Image", use_column_width=True)
                st.code(image_url, language="text")
            else:
                st.warning("⚠️ Image generation returned None (graceful fallback)")
                st.info(
                    "This is expected if Lucid worker is down. The system gracefully falls back."
                )

        except Exception as e:
            st.error(f"Image test failed: {str(e)}")
            st.exception(e)

# ── Test 3: HTML Builder ────────────────────────────────────────

if run_html_test:
    st.header("🌐 Test 3: HTML Builder")

    if st.button("Run HTML Builder Test", type="primary"):
        try:
            from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

            builder = HtmlBuilder()

            # Create test slides
            test_slides = [
                {
                    "layout": "title-hero",
                    "content": {
                        "title": "AI in Healthcare",
                        "subtitle": "Transforming patient outcomes with intelligent diagnostics",
                    },
                },
                {
                    "layout": "bullets",
                    "content": {
                        "title": "Market Opportunity",
                        "bullets": [
                            "$180B global healthcare AI market by 2028 — Source: McKinsey 2025",
                            "34% CAGR in AI diagnostics adoption — Source: Gartner 2025",
                            "78% of hospitals plan AI investment by 2026 — Source: HIMSS 2025",
                        ],
                    },
                },
                {
                    "layout": "chart",
                    "content": {
                        "title": "Healthcare AI Market Growth",
                        "chart_type": "bar",
                        "chart_data": {
                            "labels": ["2024", "2025", "2026", "2027", "2028"],
                            "datasets": [
                                {
                                    "label": "Market Size ($B)",
                                    "values": [35, 52, 78, 115, 180],
                                }
                            ],
                        },
                        "source_attribution": "Grand View Research 2025",
                    },
                },
            ]

            test_theme = {
                "colors": {
                    "primary": "#0ea5e9",
                    "accent": "#7c3aed",
                    "surface": "#f9fafb",
                    "background": "#ffffff",
                    "text_primary": "#111827",
                    "text_secondary": "#9ca3af",
                },
                "fonts": {"heading": "Inter", "body": "Inter"},
            }

            html_output = builder.build(
                test_slides, test_theme, {"title": "AI in Healthcare"}
            )

            st.success("✅ HTML generated successfully!")

            # Show HTML preview
            st.components.v1.html(html_output, height=600, scrolling=True)

            # Show HTML size
            st.metric("HTML Size", f"{len(html_output):,} bytes")

            # Check for key features
            features = {
                "Tailwind CSS": "cdn.tailwindcss.com" in html_output,
                "Animations": "animate-" in html_output,
                "Keyboard Nav": "ArrowRight" in html_output,
                "Progress Bar": "progress-bar" in html_output,
                "Offline Detection": "navigator.onLine" in html_output,
                "Chart.js": "chart.js" in html_output.lower(),
            }

            st.subheader("Feature Check")
            for feature, present in features.items():
                st.markdown(f"{'✅' if present else '❌'} {feature}")

        except Exception as e:
            st.error(f"HTML test failed: {str(e)}")
            st.exception(e)

# ── Test 4: PPTX Builder ────────────────────────────────────────

if run_pptx_test:
    st.header("📊 Test 4: PPTX Builder")

    if st.button("Run PPTX Builder Test", type="primary"):
        try:
            from app.mcp.render_mcp.builders.pptx_builder import PptxBuilder

            builder = PptxBuilder()

            test_slides = [
                {
                    "layout": "title-hero",
                    "content": {
                        "title": "AI in Healthcare",
                        "subtitle": "Transforming patient outcomes",
                    },
                },
                {
                    "layout": "bullets",
                    "content": {
                        "title": "Market Opportunity",
                        "bullets": [
                            "$180B market by 2028",
                            "34% CAGR growth",
                            "78% hospital adoption planned",
                        ],
                    },
                },
            ]

            test_theme = {
                "colors": {
                    "primary": "#0ea5e9",
                    "accent": "#7c3aed",
                    "background": "#ffffff",
                },
                "fonts": {"heading": "Inter", "body": "Inter"},
            }

            pptx_bytes = builder.build(
                test_slides, test_theme, {"title": "AI in Healthcare"}
            )

            st.success("✅ PPTX generated successfully!")
            st.metric("PPTX Size", f"{len(pptx_bytes):,} bytes")

            # Download button
            st.download_button(
                label="📥 Download PPTX",
                data=pptx_bytes,
                file_name="test_presentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

        except Exception as e:
            st.error(f"PPTX test failed: {str(e)}")
            st.exception(e)

# ── Footer ──────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    f"Test run at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
)
