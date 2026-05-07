# Barise Slide Generation - Streamlit Regression Test Suite
#
# Comprehensive testing dashboard for:
# 1. Slide Content Generation (V3 Pipeline - standard & premium)
# 2. Slide Generation (full end-to-end with multiple configs)
# 3. Slide Preview (visual rendering of generated slides)
# 4. Editor Session (CRUD operations, regeneration)
# 5. Regression Matrix (all combinations of mode x count x purpose x audience)
#
# Requirements:
#     pip install streamlit requests websocket-client
#
# Usage:
#     cd server4
#     streamlit run streamlit_test_app.py --server.port 8501
#
#     Server4 must be running on port 8003:
#     python run.py

import json
import time
import html as html_lib
from datetime import datetime
from typing import Optional

import requests
import streamlit as st

# ─── Configuration ────────────────────────────────────────────

SERVER4_URL = "http://127.0.0.1:8003"
API_V3 = f"{SERVER4_URL}/api/v3"
API_V2_EDITOR = f"{SERVER4_URL}/api/v2/editor"
API_V2 = f"{SERVER4_URL}/api/v2"

POLL_INTERVAL = 3  # seconds between status polls

# ─── Constants ────────────────────────────────────────────────

PURPOSES = ["pitch", "sales", "training", "update", "product", "conference"]
AUDIENCES = ["investors", "customers", "board", "partners", "team", "general"]
MODES = ["standard", "premium"]
WRITING_STYLES = [
    "yc_crisp", "analytical", "conversational", "storytelling",
    "technical", "persuasive", "minimalist",
]
SLIDE_COUNTS = [3, 5, 8, 10, 12, 15, 20, 25, 30]

LAYOUT_CONFIGS = {
    "title": {"emoji": "🎯", "bg": "#1e40af"},
    "title-content": {"emoji": "📄", "bg": "#1e3a5f"},
    "two-column": {"emoji": "📊", "bg": "#1e3a3a"},
    "image-left": {"emoji": "🖼️", "bg": "#3a1e3a"},
    "image-right": {"emoji": "🖼️", "bg": "#3a3a1e"},
    "section-header": {"emoji": "📌", "bg": "#2d1e5f"},
    "comparison": {"emoji": "⚖️", "bg": "#1e5f3a"},
    "blank": {"emoji": "⬜", "bg": "#2a2a2a"},
    "center-focus": {"emoji": "🎯", "bg": "#1e40af"},
    "split-screen": {"emoji": "📊", "bg": "#1e3a3a"},
    "full-bleed": {"emoji": "🌅", "bg": "#3a1e1e"},
    "bullets": {"emoji": "📝", "bg": "#1e4a3a"},
    "kpi-dashboard": {"emoji": "📈", "bg": "#1e3a5f"},
    "quote": {"emoji": "💬", "bg": "#3a1e5f"},
    "team-grid": {"emoji": "👥", "bg": "#1e5f5f"},
    "chart": {"emoji": "📉", "bg": "#3a3a1e"},
    "timeline": {"emoji": "⏳", "bg": "#5f3a1e"},
}

SLIDE_KIND_COLORS = {
    "title": "#3b82f6",
    "problem": "#ef4444",
    "solution": "#10b981",
    "market": "#8b5cf6",
    "product_demo": "#06b6d4",
    "product": "#14b8a6",
    "competition": "#f97316",
    "gtm": "#ec4899",
    "traction": "#f59e0b",
    "team": "#6366f1",
    "financial": "#22c55e",
    "ask": "#a78bfa",
    "why_now": "#f43f5e",
    "appendix": "#6b7280",
    "vision": "#8b5cf6",
    "case_study": "#0ea5e9",
    "demo": "#06b6d4",
    "pricing": "#22c55e",
    "testimonial": "#f59e0b",
    "roadmap": "#ec4899",
    "closing": "#8b5cf6",
}


# ─── API Helpers ──────────────────────────────────────────────

def check_health() -> dict:
    """Check server4 health and pipeline components."""
    try:
        r = requests.get(f"{SERVER4_URL}/health", timeout=5)
        health = r.json()
        try:
            r2 = requests.get(f"{SERVER4_URL}/health/pipeline", timeout=5)
            health["pipeline"] = r2.json()
        except Exception:
            health["pipeline"] = {"status": "unavailable"}
        return health
    except requests.ConnectionError:
        return {"status": "offline", "error": "Cannot connect to server4 at port 8003"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def start_generation(
    topic: str,
    description: str = "",
    audience: str = "investors",
    purpose: str = "pitch",
    mode: str = "standard",
    slide_count: int = 10,
    writing_style: str = "yc_crisp",
    language: str = "en",
    company_name: str = "",
) -> dict:
    """Start a V3 generation job."""
    payload = {
        "topic": topic,
        "description": description,
        "audience": audience,
        "purpose": purpose,
        "mode": mode,
        "slide_count": slide_count,
        "writing_style": writing_style,
        "language": language,
        "generate_notes": True,
        "target_formats": ["revealjs"],
    }
    if company_name:
        payload["company_name"] = company_name

    r = requests.post(f"{API_V3}/generate", json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def poll_status(deck_id: str) -> dict:
    """Poll deck generation status."""
    r = requests.get(f"{API_V3}/deck/{deck_id}/status", timeout=10)
    r.raise_for_status()
    return r.json()


def get_result(deck_id: str) -> dict:
    """Get full generation result."""
    r = requests.get(f"{API_V3}/deck/{deck_id}/result", timeout=15)
    r.raise_for_status()
    return r.json()


def get_evidence(deck_id: str) -> dict:
    """Get evidence report (premium only)."""
    r = requests.get(f"{API_V3}/deck/{deck_id}/evidence", timeout=10)
    r.raise_for_status()
    return r.json()


def cancel_generation(deck_id: str) -> dict:
    """Cancel an in-progress generation."""
    r = requests.post(f"{API_V3}/deck/{deck_id}/cancel", timeout=5)
    r.raise_for_status()
    return r.json()


def create_editor_session(deck_id: str) -> dict:
    """Create editor session from V3 result."""
    r = requests.post(f"{API_V3}/deck/{deck_id}/session", timeout=15)
    r.raise_for_status()
    return r.json()


def get_editor_session(presentation_id: str) -> dict:
    """Get editor session state."""
    r = requests.get(f"{API_V2_EDITOR}/sessions/{presentation_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def update_slide_content(presentation_id: str, slide_id: str, content: dict) -> dict:
    """Update a slide's content in the editor."""
    r = requests.put(
        f"{API_V2_EDITOR}/sessions/{presentation_id}/slides/content",
        json={"slide_id": slide_id, "content": content},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def close_editor_session(presentation_id: str) -> dict:
    """Close an editor session."""
    r = requests.delete(f"{API_V2_EDITOR}/sessions/{presentation_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def get_content_styles() -> list:
    """Get available writing styles."""
    try:
        r = requests.get(f"{API_V2}/styles", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def get_provider_health() -> dict:
    """Check provider availability."""
    try:
        r = requests.get(f"{API_V2}/providers/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"status": "unavailable"}


# ─── Slide Preview Renderer ──────────────────────────────────

def render_slide_html(
    slide: dict,
    theme: Optional[dict] = None,
    width: int = 720,
    height: int = 405,
) -> str:
    """Generate safe HTML preview for a single slide.

    No raw user content is inserted without escaping.
    """
    # Extract fields with safe defaults
    title = html_lib.escape(str(slide.get("title", slide.get("content", {}).get("title", "Untitled"))))
    content = slide.get("content", {})
    if isinstance(content, str):
        body = html_lib.escape(content)
        bullets = []
        subtitle = ""
    else:
        body = html_lib.escape(str(content.get("body_text", "")))
        bullets = content.get("bullets", []) or []
        subtitle = html_lib.escape(str(content.get("subtitle", "")))

    layout = str(slide.get("layout", "title-content"))
    slide_type = str(slide.get("type", slide.get("kind", "")))
    notes = html_lib.escape(str(slide.get("speakerNotes", slide.get("notes", ""))))
    slide_idx = slide.get("index", slide.get("slide_number", ""))

    # Theme
    if theme is None:
        theme = {}
    bg_color = theme.get("backgroundColor", "#0f172a")
    primary = theme.get("primaryColor", "#f8fafc")
    secondary = theme.get("secondaryColor", "#94a3b8")
    accent = theme.get("accentColor", "#6366f1")
    font = theme.get("fontFamily", "Inter, system-ui, sans-serif")
    font_heading = theme.get("fontHeading", font)

    # Kind color
    kind_color = SLIDE_KIND_COLORS.get(slide_type, accent)

    # Layout config
    lc = LAYOUT_CONFIGS.get(layout, {"emoji": "📄", "bg": bg_color})

    # Build bullet HTML
    bullet_html = ""
    if bullets:
        safe_bullets = "".join(
            f'<li style="margin-bottom:6px;">{html_lib.escape(str(b))}</li>'
            for b in bullets[:15]  # cap at 15
        )
        bullet_html = f'<ul style="margin:0;padding-left:20px;list-style:disc;color:{secondary};font-size:13px;line-height:1.6;">{safe_bullets}</ul>'

    # Layout-specific rendering
    if layout in ("title", "section-header"):
        content_html = f"""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;text-align:center;padding:40px;">
            <div style="width:50px;height:3px;background:{accent};border-radius:2px;margin-bottom:20px;"></div>
            <h2 style="font-family:{font_heading};color:{primary};font-size:28px;margin:0 0 12px 0;font-weight:700;line-height:1.2;">{title}</h2>
            {f'<p style="font-family:{font};color:{secondary};font-size:15px;max-width:80%;margin:0;">{subtitle or body.split(chr(10))[0] if body else ""}</p>' if subtitle or body else ''}
        </div>
        """
    elif layout in ("two-column", "comparison", "split-screen"):
        lines = body.split("\n") if body else []
        mid = len(lines) // 2
        left = "<br>".join(html_lib.escape(l) for l in lines[:mid]) if lines else "Column 1"
        right = "<br>".join(html_lib.escape(l) for l in lines[mid:]) if lines else "Column 2"
        content_html = f"""
        <div style="display:flex;flex-direction:column;height:100%;padding:30px;">
            <h2 style="font-family:{font_heading};color:{primary};font-size:22px;margin:0 0 16px 0;font-weight:700;">{title}</h2>
            <div style="flex:1;display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div style="background:{accent}10;border-radius:8px;padding:14px;">
                    <p style="font-family:{font};color:{secondary};font-size:12px;margin:0;line-height:1.5;">{left}</p>
                </div>
                <div style="background:{accent}10;border-radius:8px;padding:14px;">
                    <p style="font-family:{font};color:{secondary};font-size:12px;margin:0;line-height:1.5;">{right}</p>
                </div>
            </div>
        </div>
        """
    elif layout in ("kpi-dashboard",):
        # Try to render KPI metrics
        kpis = content.get("kpi_metrics", []) if isinstance(content, dict) else []
        if kpis:
            kpi_cards = ""
            for kpi in kpis[:6]:
                label = html_lib.escape(str(kpi.get("label", "")))
                value = html_lib.escape(str(kpi.get("value", "")))
                change = html_lib.escape(str(kpi.get("change", "")))
                kpi_cards += f"""
                <div style="background:{accent}12;border-radius:8px;padding:14px;text-align:center;">
                    <div style="font-size:10px;color:{secondary};margin-bottom:4px;">{label}</div>
                    <div style="font-size:22px;font-weight:700;color:{primary};">{value}</div>
                    <div style="font-size:10px;color:{accent};">{change}</div>
                </div>
                """
            content_html = f"""
            <div style="display:flex;flex-direction:column;height:100%;padding:30px;">
                <h2 style="font-family:{font_heading};color:{primary};font-size:22px;margin:0 0 16px 0;font-weight:700;">{title}</h2>
                <div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);gap:12px;align-content:center;">
                    {kpi_cards}
                </div>
            </div>
            """
        else:
            content_html = _default_content_html(title, body, bullet_html, font, font_heading, primary, secondary, accent)
    elif layout in ("image-left", "image-right", "text-left-visual-right", "text-right-visual-left"):
        image_url = ""
        if isinstance(content, dict):
            image_url = content.get("image_url", "") or ""
        img_block = f'<img src="{html_lib.escape(image_url)}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;" />' if image_url else f'<div style="width:100%;height:100%;background:{accent}15;border-radius:8px;display:flex;align-items:center;justify-content:center;"><span style="color:{secondary};opacity:0.4;font-size:11px;">Image</span></div>'
        text_block = f"""
        <div style="display:flex;flex-direction:column;justify-content:center;">
            <h2 style="font-family:{font_heading};color:{primary};font-size:20px;margin:0 0 10px 0;font-weight:700;">{title}</h2>
            {bullet_html if bullet_html else f'<p style="font-family:{font};color:{secondary};font-size:12px;margin:0;line-height:1.5;">{body}</p>'}
        </div>
        """
        if "left" in layout:
            grid = f"{img_block}{text_block}"
        else:
            grid = f"{text_block}{img_block}"
        content_html = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;height:100%;padding:30px;">{grid}</div>'
    else:
        # Default: title + content layout
        content_html = _default_content_html(title, body, bullet_html, font, font_heading, primary, secondary, accent)

    # Kind badge
    kind_badge = ""
    if slide_type:
        safe_type = html_lib.escape(str(slide_type))
        kind_badge = f'<span style="position:absolute;top:10px;left:12px;font-size:9px;background:{kind_color}22;color:{kind_color};padding:2px 8px;border-radius:10px;font-weight:600;">{safe_type}</span>'

    # Layout badge
    layout_badge_emoji = LAYOUT_CONFIGS.get(layout, {}).get("emoji", "📄")
    safe_layout = html_lib.escape(layout)
    layout_badge = f'<span style="position:absolute;top:10px;right:12px;font-size:9px;color:{secondary};opacity:0.5;">{layout_badge_emoji} {safe_layout}</span>'

    # Slide number
    num_badge = ""
    if slide_idx != "":
        num_badge = f'<span style="position:absolute;bottom:8px;right:12px;font-size:10px;color:{secondary};opacity:0.35;">{slide_idx}</span>'

    return f"""
    <div style="
        width:{width}px;height:{height}px;
        background:{bg_color};border-radius:12px;
        overflow:hidden;position:relative;
        font-family:{font};
        box-shadow:0 4px 24px rgba(0,0,0,0.3);
        border:1px solid rgba(255,255,255,0.06);
    ">
        {kind_badge}{layout_badge}{num_badge}
        {content_html}
    </div>
    """


def _default_content_html(
    title: str, body: str, bullet_html: str,
    font: str, font_heading: str,
    primary: str, secondary: str, accent: str,
) -> str:
    """Default title + content layout."""
    return f"""
    <div style="display:flex;flex-direction:column;height:100%;padding:30px 36px;">
        <h2 style="font-family:{font_heading};color:{primary};font-size:22px;margin:0 0 14px 0;font-weight:700;line-height:1.25;">{title}</h2>
        <div style="flex:1;overflow:hidden;">
            {bullet_html if bullet_html else f'<p style="font-family:{font};color:{secondary};font-size:13px;margin:0;white-space:pre-wrap;line-height:1.6;">{body or "<span style=opacity:0.3>Content will appear here...</span>"}</p>'}
        </div>
        <div style="display:flex;gap:6px;margin-top:auto;padding-top:10px;">
            <div style="height:2px;flex:1;background:{accent};border-radius:1px;"></div>
            <div style="height:2px;width:24px;background:{secondary};opacity:0.2;border-radius:1px;"></div>
        </div>
    </div>
    """


# ─── Streamlit Pages ─────────────────────────────────────────

def page_health():
    """Pipeline Health Check page."""
    st.header("🏥 Pipeline Health Check")

    if st.button("Check Health", type="primary"):
        with st.spinner("Checking server4..."):
            h = check_health()

        if h.get("status") == "offline":
            st.error(f"❌ Server4 is offline: {h.get('error')}")
            st.info("Start server4 with: `cd server4 && python run.py`")
            return

        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ Server4: {h.get('status', 'unknown')}")
            st.json(h)

        with col2:
            pipeline = h.get("pipeline", {})
            if isinstance(pipeline, dict):
                components = pipeline.get("components", pipeline)
                for name, status in (components.items() if isinstance(components, dict) else []):
                    icon = "✅" if status in (True, "ok", "connected") else "❌"
                    st.write(f"{icon} **{name}**: {status}")

    # Provider health
    st.subheader("🔌 Provider Health")
    if st.button("Check Providers"):
        with st.spinner("Checking providers..."):
            ph = get_provider_health()
        st.json(ph)


def page_single_generation():
    """Single Slide Generation page with full control."""
    st.header("🚀 Slide Generation")

    with st.form("gen_form"):
        col1, col2 = st.columns(2)

        with col1:
            topic = st.text_input("Topic *", "AI-Powered Customer Service Platform")
            description = st.text_area("Description", "Next-gen AI that reduces support tickets by 60%", height=80)
            company_name = st.text_input("Company Name", "Barise AI")
            audience = st.selectbox("Audience", AUDIENCES, index=0)
            purpose = st.selectbox("Purpose", PURPOSES, index=0)

        with col2:
            mode = st.selectbox("Mode", MODES, index=0)
            slide_count = st.slider("Slide Count", min_value=3, max_value=30, value=10)
            writing_style = st.selectbox("Writing Style", WRITING_STYLES, index=0)
            language = st.selectbox("Language", ["en", "es", "fr", "de", "ar", "zh", "ja"], index=0)

        submitted = st.form_submit_button("🎬 Generate Slides", type="primary")

    if submitted:
        _run_generation(
            topic=topic,
            description=description,
            company_name=company_name,
            audience=audience,
            purpose=purpose,
            mode=mode,
            slide_count=slide_count,
            writing_style=writing_style,
            language=language,
        )


def _run_generation(
    topic: str,
    description: str = "",
    company_name: str = "",
    audience: str = "investors",
    purpose: str = "pitch",
    mode: str = "standard",
    slide_count: int = 10,
    writing_style: str = "yc_crisp",
    language: str = "en",
):
    """Execute generation, poll status, display results."""
    # Start
    status_area = st.empty()
    progress_bar = st.progress(0)
    log_area = st.expander("📋 Generation Log", expanded=True)

    with status_area.container():
        st.info(f"Starting {mode} generation for '{topic}' ({slide_count} slides)...")

    try:
        resp = start_generation(
            topic=topic,
            description=description,
            audience=audience,
            purpose=purpose,
            mode=mode,
            slide_count=slide_count,
            writing_style=writing_style,
            language=language,
            company_name=company_name,
        )
    except requests.HTTPError as e:
        st.error(f"❌ Failed to start: {e.response.text if e.response else e}")
        return
    except requests.ConnectionError:
        st.error("❌ Cannot connect to server4. Is it running on port 8003?")
        return

    deck_id = resp.get("deck_id", "")
    task_id = resp.get("task_id", "")

    with log_area:
        st.write(f"**Deck ID:** `{deck_id}`")
        st.write(f"**Task ID:** `{task_id}`")
        st.write(f"**Mode:** {mode} | **Status:** {resp.get('status')}")

    # Poll
    start_time = time.time()
    max_wait = 180 if mode == "standard" else 660
    final_status = None

    while time.time() - start_time < max_wait:
        time.sleep(POLL_INTERVAL)
        try:
            status = poll_status(deck_id)
        except Exception as e:
            with log_area:
                st.warning(f"Poll error: {e}")
            continue

        current = status.get("status", "unknown")
        progress = 0
        total = status.get("total_slides", slide_count)
        generated = status.get("total_slides_generated", 0)
        if total > 0:
            progress = min(generated / total, 1.0)

        elapsed = time.time() - start_time
        progress_bar.progress(progress)

        with status_area.container():
            st.info(
                f"⏳ **{current.upper()}** — "
                f"{generated}/{total} slides "
                f"({elapsed:.0f}s elapsed)"
            )

        with log_area:
            st.write(
                f"`{datetime.now().strftime('%H:%M:%S')}` — "
                f"Status: {current}, "
                f"Slides: {generated}/{total}, "
                f"Quality: {status.get('quality_score', 0):.1f}"
            )

        if current in ("completed", "failed", "partial"):
            final_status = status
            break

    if final_status is None:
        st.error(f"⏰ Timed out after {max_wait}s")
        # Try cancel
        try:
            cancel_generation(deck_id)
        except Exception:
            pass
        return

    progress_bar.progress(1.0)

    # Result
    if final_status.get("status") == "completed":
        elapsed = time.time() - start_time
        with status_area.container():
            st.success(
                f"✅ Generation complete in {elapsed:.1f}s — "
                f"Quality: {final_status.get('quality_score', 0):.1f}/100"
            )

        # Fetch full result
        try:
            result = get_result(deck_id)
        except Exception as e:
            st.error(f"Failed to fetch result: {e}")
            return

        # Store in session state for preview
        st.session_state["last_result"] = result
        st.session_state["last_deck_id"] = deck_id
        st.session_state["last_mode"] = mode
        st.session_state["last_topic"] = topic

        _display_result(result, deck_id, mode)

    elif final_status.get("status") == "partial":
        with status_area.container():
            st.warning("⚠️ Partial generation — some slides may be missing")
        try:
            result = get_result(deck_id)
            st.session_state["last_result"] = result
            _display_result(result, deck_id, mode)
        except Exception:
            pass

    else:
        with status_area.container():
            st.error(f"❌ Generation failed: {json.dumps(final_status.get('errors', []))}")


def _display_result(result: dict, deck_id: str, mode: str):
    """Display generation result with slide previews."""
    slides = result.get("slides", [])
    quality = result.get("quality_score", 0)
    coherence = result.get("coherence_score", 0)
    total_time = result.get("total_time_ms", 0)
    errors = result.get("errors", [])

    # Metrics
    st.subheader("📊 Generation Metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Slides", len(slides))
    m2.metric("Quality", f"{quality:.1f}")
    m3.metric("Coherence", f"{coherence:.1f}")
    m4.metric("Time (ms)", f"{total_time:.0f}")
    m5.metric("Errors", len(errors))

    if errors:
        with st.expander("⚠️ Errors"):
            for e in errors:
                st.error(e)

    # Strategy
    strategy = result.get("strategy")
    if strategy:
        with st.expander("🧠 CEO Strategy"):
            st.json(strategy)

    # Evidence (premium)
    evidence = result.get("evidence_report")
    if evidence:
        with st.expander("🔬 Evidence Report"):
            st.json(evidence)

    # Design
    design = result.get("design")
    if design:
        with st.expander("🎨 Design Configuration"):
            st.json(design)

    # Slide Previews
    st.subheader("🖼️ Slide Previews")

    # Try to extract theme from design or use default dark theme
    theme = _extract_theme(result)
    deck_id = result.get("deck_id", st.session_state.get("last_deck_id", ""))

    # Display mode toggle
    view = st.radio(
        "View",
        ["Cards", "Reveal.js Preview", "Full Preview", "JSON"],
        horizontal=True,
        key="view_mode_single",
    )

    if view == "Cards":
        _render_slide_cards(slides, theme)
    elif view == "Reveal.js Preview":
        _render_revealjs_preview(deck_id)
    elif view == "Full Preview":
        _render_full_preview(slides, theme)
    else:
        st.json(slides)


def _extract_theme(result: dict) -> dict:
    """Extract or build a theme dict from the result."""
    design = result.get("design", {})
    if isinstance(design, dict):
        palette = design.get("palette", design.get("color_palette", {}))
        if isinstance(palette, dict):
            return {
                "backgroundColor": palette.get("background", palette.get("bg", "#0f172a")),
                "primaryColor": palette.get("primary", palette.get("text", "#f8fafc")),
                "secondaryColor": palette.get("secondary", palette.get("muted", "#94a3b8")),
                "accentColor": palette.get("accent", "#6366f1"),
                "fontFamily": design.get("font_family", "Inter, system-ui, sans-serif"),
                "fontHeading": design.get("font_heading", "Inter, system-ui, sans-serif"),
            }
    # Default dark theme
    return {
        "backgroundColor": "#0f172a",
        "primaryColor": "#f8fafc",
        "secondaryColor": "#94a3b8",
        "accentColor": "#6366f1",
        "fontFamily": "Inter, system-ui, sans-serif",
        "fontHeading": "Inter, system-ui, sans-serif",
    }


def _render_slide_cards(slides: list, theme: dict):
    """Render slides as HTML preview cards."""
    cols_per_row = 2
    for row_start in range(0, len(slides), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = row_start + j
            if idx >= len(slides):
                break
            slide = slides[idx]
            with col:
                slide_html = render_slide_html(slide, theme, width=440, height=248)
                st.markdown(slide_html, unsafe_allow_html=True)

                # Slide info
                title = slide.get("title", slide.get("content", {}).get("title", "")) if isinstance(slide.get("content"), dict) else slide.get("title", "")
                kind = slide.get("kind", slide.get("type", ""))
                layout = slide.get("layout", "")
                notes = slide.get("speakerNotes", slide.get("notes", ""))

                st.caption(f"**Slide {idx + 1}** — {kind} · {layout}")

                if notes:
                    with st.expander(f"📝 Speaker Notes"):
                        st.write(notes)


def _render_revealjs_preview(deck_id: str):
    """Fetch compiled reveal.js HTML from the server and embed it."""
    import streamlit.components.v1 as components

    if not deck_id:
        st.warning("No deck ID available. Generate a deck first.")
        return

    with st.spinner("Compiling reveal.js presentation..."):
        try:
            resp = requests.get(
                f"{API_V3}/deck/{deck_id}/preview", timeout=30
            )
            if resp.status_code == 200:
                reveal_html = resp.text
                st.success(
                    f"Reveal.js presentation loaded ({len(reveal_html):,} bytes)"
                )
                # Embed the full reveal.js presentation in an iframe
                components.html(reveal_html, height=680, scrolling=False)

                # Download button
                st.download_button(
                    "Download reveal.js HTML",
                    data=reveal_html,
                    file_name=f"presentation_{deck_id[:8]}.html",
                    mime="text/html",
                )
            elif resp.status_code == 409:
                st.warning("Generation is still in progress. Wait and retry.")
            else:
                st.error(
                    f"Preview failed (HTTP {resp.status_code}): {resp.text[:300]}"
                )
        except requests.exceptions.ConnectionError:
            st.error(
                "Cannot connect to server4. "
                "Make sure it is running: `cd server4 && python run.py`"
            )
        except Exception as e:
            st.error(f"Preview error: {e}")


def _render_full_preview(slides: list, theme: dict):
    """Render slides in full-width presentation-like view."""
    if not slides:
        st.info("No slides to preview.")
        return

    slide_idx = st.slider(
        "Slide", min_value=1, max_value=len(slides), value=1, key="full_preview_slider"
    )
    slide = slides[slide_idx - 1]

    # Large preview
    slide_html = render_slide_html(slide, theme, width=880, height=495)
    st.markdown(
        f'<div style="display:flex;justify-content:center;">{slide_html}</div>',
        unsafe_allow_html=True,
    )

    # Info panel
    col1, col2, col3 = st.columns(3)
    with col1:
        title = slide.get("title", "")
        if isinstance(slide.get("content"), dict):
            title = title or slide["content"].get("title", "")
        st.write(f"**Title:** {title}")
    with col2:
        st.write(f"**Type:** {slide.get('type', slide.get('kind', ''))}")
    with col3:
        st.write(f"**Layout:** {slide.get('layout', '')}")

    notes = slide.get("speakerNotes", slide.get("notes", ""))
    if notes:
        st.info(f"**Speaker Notes:** {notes}")

    # Raw data
    with st.expander("🔍 Slide Raw Data"):
        st.json(slide)


def page_regression():
    """Regression testing matrix — generates across many configurations."""
    st.header("🧪 Regression Testing Matrix")

    st.markdown("""
    Test slide generation across multiple combinations of **mode**, **slide count**,
    **purpose**, and **audience**. Each test dispatches a generation job and validates
    the result meets expectations (correct count, quality score, no errors).
    """)

    with st.form("regression_form"):
        topic = st.text_input("Topic", "AI-Powered Customer Service Platform")

        st.markdown("**Select test dimensions:**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            test_modes = st.multiselect("Modes", MODES, default=["standard"])
        with col2:
            test_counts = st.multiselect("Slide Counts", SLIDE_COUNTS, default=[5, 10, 15])
        with col3:
            test_purposes = st.multiselect("Purposes", PURPOSES, default=["pitch", "sales"])
        with col4:
            test_audiences = st.multiselect("Audiences", AUDIENCES, default=["investors"])

        max_concurrent = st.number_input("Max parallel jobs", min_value=1, max_value=5, value=1)
        submitted = st.form_submit_button("🧪 Run Regression Suite", type="primary")

    if submitted:
        _run_regression(topic, test_modes, test_counts, test_purposes, test_audiences)


def _run_regression(
    topic: str,
    modes: list,
    counts: list,
    purposes: list,
    audiences: list,
):
    """Run full regression matrix."""
    # Build test matrix
    tests = []
    for m in modes:
        for c in counts:
            for p in purposes:
                for a in audiences:
                    tests.append({
                        "mode": m,
                        "slide_count": c,
                        "purpose": p,
                        "audience": a,
                    })

    total = len(tests)
    st.write(f"**Total tests:** {total}")

    if total > 20:
        st.warning(f"⚠️ {total} tests — this will take a while. Consider reducing selections.")

    results_table = []
    progress = st.progress(0)
    status_text = st.empty()
    results_area = st.container()

    for i, test in enumerate(tests):
        status_text.write(
            f"**Test {i + 1}/{total}** — "
            f"{test['mode']} / {test['slide_count']} slides / {test['purpose']} / {test['audience']}"
        )

        row = {
            "Test": i + 1,
            "Mode": test["mode"],
            "Slides": test["slide_count"],
            "Purpose": test["purpose"],
            "Audience": test["audience"],
        }

        try:
            # Start generation
            resp = start_generation(
                topic=topic,
                audience=test["audience"],
                purpose=test["purpose"],
                mode=test["mode"],
                slide_count=test["slide_count"],
            )
            deck_id = resp.get("deck_id", "")
            row["Deck ID"] = deck_id[:8] + "..."

            # Poll until done
            start_time = time.time()
            max_wait = 180 if test["mode"] == "standard" else 660
            final = None

            while time.time() - start_time < max_wait:
                time.sleep(POLL_INTERVAL)
                try:
                    st_data = poll_status(deck_id)
                    current = st_data.get("status")
                    if current in ("completed", "failed", "partial"):
                        final = st_data
                        break
                except Exception:
                    continue

            if final is None:
                row["Status"] = "⏰ TIMEOUT"
                row["Generated"] = "—"
                row["Quality"] = "—"
                row["Time (ms)"] = f"{(time.time() - start_time) * 1000:.0f}"
                row["Pass"] = "❌"
                try:
                    cancel_generation(deck_id)
                except Exception:
                    pass
            else:
                row["Status"] = final.get("status", "unknown")
                row["Generated"] = f"{final.get('total_slides_generated', 0)}/{test['slide_count']}"
                row["Quality"] = f"{final.get('quality_score', 0):.1f}"
                row["Time (ms)"] = f"{final.get('total_time_ms', 0):.0f}"

                # Validation
                passed = True
                issues = []

                if final.get("status") != "completed":
                    passed = False
                    issues.append(f"Status: {final.get('status')}")

                gen_count = final.get("total_slides_generated", 0)
                expected = test["slide_count"]
                if gen_count < expected - 1:  # allow 1 slide tolerance
                    passed = False
                    issues.append(f"Count mismatch: {gen_count} vs {expected}")

                if final.get("quality_score", 0) < 20:
                    passed = False
                    issues.append(f"Low quality: {final.get('quality_score')}")

                row["Pass"] = "✅" if passed else "❌"
                if issues:
                    row["Issues"] = "; ".join(issues)

        except requests.ConnectionError:
            row["Status"] = "🔌 OFFLINE"
            row["Pass"] = "❌"
        except Exception as e:
            row["Status"] = f"💥 {str(e)[:40]}"
            row["Pass"] = "❌"

        results_table.append(row)
        progress.progress((i + 1) / total)

    # Display results
    status_text.write("**Regression complete!**")
    progress.progress(1.0)

    with results_area:
        import pandas as pd

        df = pd.DataFrame(results_table)
        pass_count = len([r for r in results_table if r.get("Pass") == "✅"])
        fail_count = total - pass_count

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tests", total)
        col2.metric("Passed", pass_count, delta=None)
        col3.metric("Failed", fail_count, delta=None, delta_color="inverse" if fail_count > 0 else "off")

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Results CSV", csv, "regression_results.csv", "text/csv")


def page_editor_test():
    """Editor Session integration test."""
    st.header("✏️ Editor Session Test")

    deck_id = st.text_input(
        "Deck ID",
        value=st.session_state.get("last_deck_id", ""),
        help="Enter a deck_id from a completed generation",
    )

    if not deck_id:
        st.info("First generate some slides, then come back here to test the editor.")
        return

    col1, col2, col3 = st.columns(3)

    # Create session
    with col1:
        if st.button("🔓 Open Editor Session"):
            try:
                with st.spinner("Creating session..."):
                    sess = create_editor_session(deck_id)
                st.session_state["editor_session"] = sess
                st.success(f"Session opened: `{sess.get('presentation_id', '')[:16]}...`")
                st.json(sess)
            except Exception as e:
                st.error(f"Failed: {e}")

    # Get session
    with col2:
        if st.button("📖 Get Session State"):
            sess = st.session_state.get("editor_session", {})
            pid = sess.get("presentation_id", "")
            if not pid:
                st.warning("Open a session first")
            else:
                try:
                    state = get_editor_session(pid)
                    st.json(state)
                except Exception as e:
                    st.error(f"Failed: {e}")

    # Close session
    with col3:
        if st.button("🔒 Close Session"):
            sess = st.session_state.get("editor_session", {})
            pid = sess.get("presentation_id", "")
            if pid:
                try:
                    close_editor_session(pid)
                    st.success("Session closed")
                    del st.session_state["editor_session"]
                except Exception as e:
                    st.error(f"Failed: {e}")

    # Slide content update test
    st.subheader("✏️ Slide Content Update")
    sess = st.session_state.get("editor_session", {})
    pid = sess.get("presentation_id", "")

    if pid:
        slide_id = st.text_input("Slide ID to update")
        new_title = st.text_input("New Title", "Updated Test Title")
        new_body = st.text_area("New Body Text", "This content was updated via editor API.")

        if st.button("💾 Update Slide"):
            try:
                resp = update_slide_content(pid, slide_id, {
                    "title": new_title,
                    "body_text": new_body,
                })
                st.success(f"Updated: {resp}")
            except Exception as e:
                st.error(f"Failed: {e}")


def page_slide_preview():
    """Standalone slide preview page — test all layouts and themes."""
    st.header("🖼️ Slide Preview Lab")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Layout Gallery", "🎨 Theme Tester", "📄 JSON Import", "🎬 Reveal.js Live",
    ])

    with tab1:
        _preview_layout_gallery()

    with tab2:
        _preview_theme_tester()

    with tab3:
        _preview_json_import()

    with tab4:
        _preview_revealjs_live()


def _preview_layout_gallery():
    """Preview all layouts with sample content."""
    st.subheader("All Layout Types")

    layouts = [
        "title", "title-content", "two-column", "image-left",
        "image-right", "section-header", "comparison", "blank",
        "center-focus", "split-screen", "kpi-dashboard", "bullets",
    ]

    theme = {
        "backgroundColor": "#0f172a",
        "primaryColor": "#f8fafc",
        "secondaryColor": "#94a3b8",
        "accentColor": "#6366f1",
        "fontFamily": "Inter, system-ui, sans-serif",
        "fontHeading": "Inter, system-ui, sans-serif",
    }

    sample_content = {
        "title": "Sample Title",
        "subtitle": "A great subtitle for this slide",
        "body_text": "Line one of content\nLine two with details\nLine three with data\nLine four conclusion\nLine five summary\nLine six extras",
        "bullets": [
            "First key point about the topic",
            "Second important detail",
            "Third supporting evidence",
            "Fourth strategic insight",
        ],
    }

    for row_start in range(0, len(layouts), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = row_start + j
            if idx >= len(layouts):
                break
            layout = layouts[idx]
            with col:
                slide = {
                    "title": f"{layout.title()} Layout",
                    "content": sample_content,
                    "layout": layout,
                    "type": "solution",
                    "index": idx + 1,
                }
                slide_html = render_slide_html(slide, theme, width=340, height=191)
                st.markdown(slide_html, unsafe_allow_html=True)
                st.caption(f"`{layout}`")


def _preview_theme_tester():
    """Let the user customize theme colors and preview."""
    st.subheader("Custom Theme Preview")

    col1, col2 = st.columns([1, 2])

    with col1:
        bg = st.color_picker("Background", "#0f172a")
        primary = st.color_picker("Primary Text", "#f8fafc")
        secondary = st.color_picker("Secondary Text", "#94a3b8")
        accent = st.color_picker("Accent", "#6366f1")
        font = st.selectbox("Font", ["Inter", "Georgia", "JetBrains Mono", "Playfair Display"], index=0)

    theme = {
        "backgroundColor": bg,
        "primaryColor": primary,
        "secondaryColor": secondary,
        "accentColor": accent,
        "fontFamily": f"{font}, system-ui, sans-serif",
        "fontHeading": f"{font}, system-ui, sans-serif",
    }

    sample_slides = [
        {
            "title": "The Problem",
            "content": {"title": "The Problem", "bullets": [
                "Customer support costs $50B/year", "Average response time: 4 hours",
                "60% of tickets are repetitive", "Agents burn out fast",
            ]},
            "layout": "title-content", "type": "problem", "index": 1,
        },
        {
            "title": "Our Solution",
            "content": {"title": "Our Solution", "body_text": "AI-powered platform that\nautomatically resolves 60% of\nsupport tickets in under 30 seconds.\n\nReal-time learning from every interaction."},
            "layout": "two-column", "type": "solution", "index": 2,
        },
        {
            "title": "Market Opportunity",
            "content": {"title": "$12B Market", "subtitle": "Growing 23% YoY", "body_text": "Customer service AI is the fastest\ngrowing B2B SaaS category."},
            "layout": "title", "type": "market", "index": 3,
        },
    ]

    with col2:
        for slide in sample_slides:
            slide_html = render_slide_html(slide, theme, width=540, height=304)
            st.markdown(slide_html, unsafe_allow_html=True)
            st.write("")


def _preview_json_import():
    """Import and preview slides from JSON."""
    st.subheader("Import Slides JSON")

    # Check if there's a last result
    last_result = st.session_state.get("last_result")
    if last_result:
        if st.button("📋 Load Last Generation Result"):
            st.session_state["preview_json"] = json.dumps(last_result.get("slides", []), indent=2)

    json_input = st.text_area(
        "Paste slides JSON array",
        value=st.session_state.get("preview_json", ""),
        height=200,
        help="Paste a JSON array of slide objects",
    )

    if json_input:
        try:
            slides = json.loads(json_input)
            if not isinstance(slides, list):
                slides = [slides]

            st.success(f"Loaded {len(slides)} slides")

            theme = _extract_theme({"design": {}})

            view = st.radio("View", ["Cards", "Slideshow"], horizontal=True, key="json_view")

            if view == "Cards":
                _render_slide_cards(slides, theme)
            else:
                _render_full_preview(slides, theme)

        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")


def _preview_revealjs_live():
    """Compile and preview a reveal.js deck from a deck_id or the last generation."""
    import streamlit.components.v1 as components

    st.subheader("Reveal.js Live Preview")
    st.markdown(
        "Enter a **deck ID** from a completed V3 generation to render the "
        "full reveal.js presentation with transitions, speaker notes, "
        "auto-animate, and all layout types."
    )

    last_id = st.session_state.get("last_deck_id", "")
    deck_id = st.text_input("Deck ID", value=last_id, key="revealjs_deck_id")

    col1, col2 = st.columns(2)
    with col1:
        preview_height = st.slider("Preview Height (px)", 400, 900, 680, step=20)
    with col2:
        st.write("")  # spacer

    if st.button("Compile & Preview", type="primary", key="revealjs_compile_btn"):
        if not deck_id:
            st.warning("Enter a deck ID first.")
            return

        with st.spinner("Fetching & compiling reveal.js..."):
            try:
                resp = requests.get(
                    f"{API_V3}/deck/{deck_id}/preview", timeout=30
                )
                if resp.status_code == 200:
                    reveal_html = resp.text
                    st.session_state["revealjs_html"] = reveal_html
                    st.session_state["revealjs_deck"] = deck_id
                elif resp.status_code == 409:
                    st.warning("Generation still in progress.")
                    return
                else:
                    st.error(f"HTTP {resp.status_code}: {resp.text[:300]}")
                    return
            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to server4. "
                    "Run: `cd server4 && python run.py`"
                )
                return
            except Exception as e:
                st.error(f"Error: {e}")
                return

    # Render cached HTML
    cached = st.session_state.get("revealjs_html")
    if cached:
        st.success(
            f"Deck `{st.session_state.get('revealjs_deck', '')[:12]}...` "
            f"({len(cached):,} bytes)"
        )
        components.html(cached, height=preview_height, scrolling=False)

        st.download_button(
            "Download reveal.js HTML",
            data=cached,
            file_name=f"deck_{st.session_state.get('revealjs_deck', 'unknown')[:8]}.html",
            mime="text/html",
            key="revealjs_download",
        )


def page_slide_content_gen():
    """Test slide content generation specifically (V2 content pipeline)."""
    st.header("📝 Slide Content Generation Test")

    st.markdown("""
    Test the **content generation** pipeline independently.
    This generates structured content for each slide (title, body, bullets,
    speaker notes, data) without full presentation rendering.
    """)

    with st.form("content_gen_form"):
        topic = st.text_input("Topic *", "AI SaaS Customer Platform")
        desc = st.text_area("Description", "AI reduces tickets 60%, 10K users, $2M ARR", height=80)

        col1, col2, col3 = st.columns(3)
        with col1:
            audience = st.selectbox("Audience", AUDIENCES, index=0, key="cg_aud")
        with col2:
            style = st.selectbox("Writing Style", WRITING_STYLES, index=0, key="cg_style")
        with col3:
            slide_count = st.slider("Slides", 3, 30, 10, key="cg_count")

        # Manual outline option
        use_outline = st.checkbox("Custom outline (JSON)")
        outline_json = ""
        if use_outline:
            outline_json = st.text_area("Outline JSON", '{"slides": []}', height=100)

        submitted = st.form_submit_button("📝 Generate Content", type="primary")

    if submitted:
        # Use V3 pipeline (standard mode = content + slides)
        st.subheader("⏳ Content Generation Progress")

        try:
            resp = start_generation(
                topic=topic,
                description=desc,
                audience=audience,
                purpose="pitch",
                mode="standard",
                slide_count=slide_count,
                writing_style=style,
            )
            deck_id = resp.get("deck_id", "")
            st.write(f"**Deck ID:** `{deck_id}`")

            # Poll
            progress_bar = st.progress(0)
            status_text = st.empty()

            start_t = time.time()
            result_data = None

            while time.time() - start_t < 180:
                time.sleep(POLL_INTERVAL)
                try:
                    sd = poll_status(deck_id)
                except Exception:
                    continue

                status = sd.get("status")
                gen = sd.get("total_slides_generated", 0)
                total = sd.get("total_slides", slide_count)
                if total > 0:
                    progress_bar.progress(min(gen / total, 1.0))
                status_text.write(f"**{status.upper()}** — {gen}/{total} slides ({time.time() - start_t:.0f}s)")

                if status in ("completed", "failed", "partial"):
                    if status == "completed":
                        result_data = get_result(deck_id)
                    break

            progress_bar.progress(1.0)

            if result_data:
                slides = result_data.get("slides", [])
                st.success(f"✅ Generated content for {len(slides)} slides")

                # Content analysis
                st.subheader("📊 Content Analysis")

                content_stats = []
                for i, s in enumerate(slides):
                    content = s.get("content", {})
                    if isinstance(content, str):
                        content = {"body_text": content}

                    title = content.get("title", s.get("title", ""))
                    body = content.get("body_text", "")
                    bullets = content.get("bullets", []) or []
                    notes = s.get("speakerNotes", s.get("notes", ""))

                    word_count = len((title + " " + body + " " + " ".join(str(b) for b in bullets)).split())

                    content_stats.append({
                        "Slide": i + 1,
                        "Kind": s.get("kind", s.get("type", "")),
                        "Title": title[:50],
                        "Body Words": len(body.split()) if body else 0,
                        "Bullets": len(bullets),
                        "Has Notes": "✅" if notes else "❌",
                        "Total Words": word_count,
                    })

                import pandas as pd
                df = pd.DataFrame(content_stats)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Word count chart
                st.bar_chart(df.set_index("Slide")["Total Words"])

                # Individual slide content
                st.subheader("📄 Slide Content Details")
                for i, s in enumerate(slides):
                    content = s.get("content", {})
                    if isinstance(content, str):
                        content = {"body_text": content}

                    with st.expander(f"Slide {i + 1}: {content.get('title', s.get('title', 'Untitled'))}"):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            if content.get("subtitle"):
                                st.write(f"**Subtitle:** {content['subtitle']}")
                            if content.get("body_text"):
                                st.markdown(f"**Body:**\n{content['body_text']}")
                            if content.get("bullets"):
                                st.markdown("**Bullets:**")
                                for b in content["bullets"]:
                                    st.write(f"• {b}")
                        with col2:
                            notes = s.get("speakerNotes", s.get("notes", ""))
                            if notes:
                                st.info(f"**Notes:** {notes}")
                            st.write(f"**Kind:** {s.get('kind', s.get('type', ''))}")
                            st.write(f"**Layout:** {s.get('layout', '')}")

                # Preview
                st.subheader("🖼️ Content Preview")
                theme = _extract_theme(result_data)
                _render_slide_cards(slides, theme)

            else:
                st.error("❌ Content generation failed or timed out")

        except requests.ConnectionError:
            st.error("❌ Server4 not running on port 8003")
        except Exception as e:
            st.error(f"Error: {e}")


def page_quick_tests():
    """Quick validation tests — import checks, model validation, etc."""
    st.header("⚡ Quick Validation Tests")

    if st.button("Run All Quick Tests", type="primary"):
        results = []

        # Test 1: Health check
        with st.spinner("Testing health..."):
            h = check_health()
            ok = h.get("status") not in ("offline", "error")
            results.append(("Health Check", ok, h.get("status", "?")))

        # Test 2: V3 Generate endpoint exists (send invalid body → expect 422)
        with st.spinner("Testing V3 endpoint..."):
            try:
                r = requests.post(
                    f"{API_V3}/generate",
                    json={"bad": "payload"},
                    timeout=10,
                )
                # 422 = endpoint exists and Pydantic rejected the body
                ok2 = r.status_code == 422
                results.append(("V3 /generate endpoint", ok2, f"HTTP {r.status_code}"))
            except Exception as e:
                results.append(("V3 /generate endpoint", False, str(e)))

        # Test 3: V3 Status endpoint (with fake ID — should 404 or 200)
        with st.spinner("Testing status endpoint..."):
            try:
                r = requests.get(f"{API_V3}/deck/test-nonexistent/status", timeout=15)
                ok3 = r.status_code in (404, 422, 200)  # Any of these means endpoint is live
                results.append(("V3 /status endpoint", ok3, f"HTTP {r.status_code}"))
            except Exception as e:
                results.append(("V3 /status endpoint", False, str(e)))

        # Test 4: Editor sessions endpoint
        with st.spinner("Testing editor endpoint..."):
            try:
                r = requests.get(f"{API_V2_EDITOR}/sessions/test-nonexistent", timeout=5)
                ok4 = r.status_code in (404, 422, 200)
                results.append(("V2 Editor endpoint", ok4, f"HTTP {r.status_code}"))
            except Exception as e:
                results.append(("V2 Editor endpoint", False, str(e)))

        # Test 5: Styles endpoint
        with st.spinner("Testing styles endpoint..."):
            try:
                styles = get_content_styles()
                ok5 = isinstance(styles, (list, dict))
                results.append(("V2 /styles endpoint", ok5, f"{len(styles) if isinstance(styles, list) else 'ok'} styles"))
            except Exception as e:
                results.append(("V2 /styles endpoint", False, str(e)))

        # Test 6: Validation — bad slide count
        with st.spinner("Testing validation (bad slide_count)..."):
            try:
                r = requests.post(f"{API_V3}/generate", json={
                    "topic": "Test", "mode": "standard", "slide_count": 0
                }, timeout=5)
                ok6 = r.status_code == 422  # Pydantic validation error
                results.append(("Validation: slide_count=0 rejected", ok6, f"HTTP {r.status_code}"))
            except Exception as e:
                results.append(("Validation: slide_count=0 rejected", False, str(e)))

        # Test 7: Validation — bad mode
        with st.spinner("Testing validation (bad mode)..."):
            try:
                r = requests.post(f"{API_V3}/generate", json={
                    "topic": "Test", "mode": "invalid_mode", "slide_count": 10
                }, timeout=5)
                ok7 = r.status_code in (422, 400)
                results.append(("Validation: bad mode rejected", ok7, f"HTTP {r.status_code}"))
            except Exception as e:
                results.append(("Validation: bad mode rejected", False, str(e)))

        # Test 8: Validation — slide count > 30
        with st.spinner("Testing validation (slide_count=50)..."):
            try:
                r = requests.post(f"{API_V3}/generate", json={
                    "topic": "Test", "mode": "standard", "slide_count": 50
                }, timeout=5)
                ok8 = r.status_code == 422
                results.append(("Validation: slide_count=50 rejected", ok8, f"HTTP {r.status_code}"))
            except Exception as e:
                results.append(("Validation: slide_count=50 rejected", False, str(e)))

        # Display results
        st.subheader("Results")
        passed = sum(1 for _, ok, _ in results if ok)
        total = len(results)

        col1, col2 = st.columns(2)
        col1.metric("Passed", f"{passed}/{total}")
        col2.metric("Status", "✅ ALL PASS" if passed == total else f"❌ {total - passed} FAILED")

        for name, ok, detail in results:
            icon = "✅" if ok else "❌"
            st.write(f"{icon} **{name}** — {detail}")


# ─── Main App ─────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Barise Slide Generation Tester",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for better slide rendering
    st.markdown("""
    <style>
        .stMarkdown div[style] {
            margin: 0 auto;
        }
        .block-container {
            max-width: 1200px;
        }
        [data-testid="stMetric"] {
            background: rgba(99, 102, 241, 0.05);
            border: 1px solid rgba(99, 102, 241, 0.1);
            border-radius: 12px;
            padding: 12px 16px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.title("🎯 Slide Gen Tester")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigate",
        [
            "🏥 Health Check",
            "🚀 Slide Generation",
            "📝 Content Generation",
            "🖼️ Slide Preview Lab",
            "✏️ Editor Session",
            "🧪 Regression Matrix",
            "⚡ Quick Tests",
        ],
    )

    # Server status indicator in sidebar
    try:
        r = requests.get(f"{SERVER4_URL}/health", timeout=2)
        st.sidebar.success("🟢 Server4 Online")
    except Exception:
        st.sidebar.error("🔴 Server4 Offline")
        st.sidebar.caption("Run: `cd server4 && python run.py`")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Server: `{SERVER4_URL}`")
    st.sidebar.caption(f"Last result: `{st.session_state.get('last_deck_id', 'none')[:12]}...`")

    # Route to page
    if "Health" in page:
        page_health()
    elif "Slide Generation" in page:
        page_single_generation()
    elif "Content Generation" in page:
        page_slide_content_gen()
    elif "Preview" in page:
        page_slide_preview()
    elif "Editor" in page:
        page_editor_test()
    elif "Regression" in page:
        page_regression()
    elif "Quick" in page:
        page_quick_tests()


if __name__ == "__main__":
    main()
