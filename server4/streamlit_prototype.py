"""
Barise Presentation Engine — User Prototype Demo

Run: streamlit run streamlit_prototype.py
Requires: pip install streamlit requests

This app connects to the running server4 API (port 8003) and demonstrates
the full slide/presentation generation pipeline including:
  - V3 generation (standard & premium modes)
  - reveal.js live preview (iframe embed)
  - React + Three.js compiled code preview
  - HTML builder standalone preview
  - PPTX download
  - Slide card previews with layout-aware rendering
  - Real-time generation progress polling
  - Quality metrics, speaker notes, JSON inspection

Server4 must be running: cd server4 && python run.py
"""

import html as html_lib
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
import streamlit.components.v1 as components

# ── Server Configuration ──────────────────────────────────────
SERVER4_URL = "http://127.0.0.1:8003"
API_V3 = f"{SERVER4_URL}/api/v3"
API_V2 = f"{SERVER4_URL}/api/v2"
POLL_INTERVAL = 2  # seconds between status polls

# ── Constants ─────────────────────────────────────────────────
PURPOSES = ["pitch", "sales", "training", "update", "product", "conference"]
AUDIENCES = ["investors", "customers", "board", "partners", "team", "general"]
MODES = ["standard", "premium"]
WRITING_STYLES = [
    "yc_crisp",
    "analytical",
    "conversational",
    "storytelling",
    "technical",
    "persuasive",
    "minimalist",
]

LAYOUT_META = {
    "title": {"emoji": "🎯", "label": "Title"},
    "title-content": {"emoji": "📄", "label": "Title + Content"},
    "two-column": {"emoji": "📊", "label": "Two Column"},
    "image-left": {"emoji": "🖼️", "label": "Image Left"},
    "image-right": {"emoji": "🖼️", "label": "Image Right"},
    "section-header": {"emoji": "📌", "label": "Section Header"},
    "comparison": {"emoji": "⚖️", "label": "Comparison"},
    "center-focus": {"emoji": "🎯", "label": "Center Focus"},
    "split-screen": {"emoji": "📊", "label": "Split Screen"},
    "bullets": {"emoji": "📝", "label": "Bullets"},
    "kpi-dashboard": {"emoji": "📈", "label": "KPI Dashboard"},
    "chart-focus": {"emoji": "📉", "label": "Chart Focus"},
    "team-grid": {"emoji": "👥", "label": "Team Grid"},
    "timeline": {"emoji": "⏳", "label": "Timeline"},
    "quote": {"emoji": "💬", "label": "Quote"},
    "blank": {"emoji": "⬜", "label": "Blank"},
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

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Barise — Presentation Prototype",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown(
    """
<style>
    .main .block-container { max-width: 1400px; padding-top: 2rem; }
    [data-testid="stMetric"] {
        background: rgba(99,102,241,0.06);
        border: 1px solid rgba(99,102,241,0.12);
        border-radius: 12px;
        padding: 14px 18px;
    }
    .slide-card {
        border-radius: 12px; overflow: hidden;
        box-shadow: 0 4px 24px rgba(0,0,0,0.15);
        border: 1px solid rgba(255,255,255,0.06);
    }
    .kind-badge {
        position: absolute; top: 10px; left: 12px;
        font-size: 9px; padding: 2px 8px; border-radius: 10px;
        font-weight: 600;
    }
    .layout-badge {
        position: absolute; top: 10px; right: 12px;
        font-size: 9px; opacity: 0.5;
    }
    .slide-number {
        position: absolute; bottom: 8px; right: 12px;
        font-size: 10px; opacity: 0.35;
    }
    .pipeline-step {
        display: flex; align-items: center; gap: 12px;
        padding: 10px 16px; border-radius: 8px;
        margin-bottom: 6px;
    }
    .pipeline-step.active {
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.3);
    }
    .pipeline-step.done {
        background: rgba(34,197,94,0.08);
        border: 1px solid rgba(34,197,94,0.2);
    }
    .pipeline-step.pending {
        background: rgba(148,163,184,0.05);
        border: 1px solid rgba(148,163,184,0.1);
        opacity: 0.5;
    }
    .pipeline-icon {
        width: 36px; height: 36px; border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════
# DEMO / SAMPLE SLIDES (Pre-built for testing without AI generation)
# ═══════════════════════════════════════════════════════════════


def get_sample_slides(topic: str = "AI Startup") -> dict:
    """Get pre-built sample slides for demo/testing purposes.

    This bypasses the AI generation pipeline and provides
    properly formatted slides to test the display.
    """
    return {
        "deck_id": "demo-deck-001",
        "status": "completed",
        "topic": topic,
        "mode": "demo",
        "slides": [
            {
                "index": 0,
                "title": "AI Revolution: Transforming Industries",
                "layout": "title-hero",
                "kind": "title",
                "purpose": "Introduce the company and vision",
                "content": {
                    "headline": "AI Revolution: Transforming Industries",
                    "bullets": [
                        "Market size: $190B by 2025",
                        "73% of enterprises adopting AI",
                        "10x ROI in first year",
                    ],
                    "quote": {
                        "text": "AI is not just a technology, it's a fundamental shift in how businesses operate.",
                        "author": "Satya Nadella",
                    },
                },
                "design": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#0F172A", "#6366F1"],
                        "angle": 135,
                    },
                    "heading": {"color": "#F8FAFC", "font": "Inter"},
                    "body": {"color": "#CBD5E1", "font": "Inter"},
                    "accent": {"color": "#6366F1"},
                },
                "notes": "Welcome everyone. Today we'll explore how AI is transforming industries.",
            },
            {
                "index": 1,
                "title": "The Problem: $2.5T Lost Annually",
                "layout": "two-column",
                "kind": "problem",
                "purpose": "Quantify the pain point",
                "content": {
                    "headline": "The Problem: Inefficiency Costs Billions",
                    "bullets": [
                        "2.5 trillion hours wasted on manual tasks",
                        "67% of data workers spend time on repetitive tasks",
                        "Only 23% of companies have scaled AI beyond pilot",
                    ],
                    "data": [
                        {
                            "label": "Annual Loss",
                            "value": "$2.5T",
                            "source": "McKinsey 2024",
                        },
                        {"label": "Task Time", "value": "40%", "source": "Forrester"},
                    ],
                },
                "design": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#7F1D1D", "#EF4444"],
                        "angle": 135,
                    },
                    "heading": {"color": "#FEF2F2", "font": "Inter"},
                    "body": {"color": "#FECACA", "font": "Inter"},
                    "accent": {"color": "#EF4444"},
                },
                "notes": "The cost of NOT adopting AI is massive. Let me show you the numbers.",
            },
            {
                "index": 2,
                "title": "Our Solution: AI-Powered Automation",
                "layout": "bullets",
                "kind": "solution",
                "purpose": "Present the solution",
                "content": {
                    "headline": "Introducing Our AI Platform",
                    "bullets": [
                        "🤖 Intelligent Automation: 80% reduction in manual work",
                        "📊 Real-time Analytics: Instant insights from your data",
                        "🔗 Seamless Integration: Works with 50+ enterprise tools",
                        "🛡️ Enterprise-Grade Security: SOC2, GDPR compliant",
                    ],
                },
                "design": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#064E3B", "#10B981"],
                        "angle": 135,
                    },
                    "heading": {"color": "#ECFDF5", "font": "Inter"},
                    "body": {"color": "#A7F3D0", "font": "Inter"},
                    "accent": {"color": "#10B981"},
                },
                "notes": "Our platform addresses all these pain points with one integrated solution.",
            },
            {
                "index": 3,
                "title": "Market Opportunity: $190B by 2025",
                "layout": "kpi-dashboard",
                "kind": "market",
                "purpose": "Show market size and growth",
                "content": {
                    "headline": "Market Opportunity",
                    "data": [
                        {"label": "TAM", "value": "$190B", "change": "+25% YoY"},
                        {"label": "SAM", "value": "$45B", "change": "+30% YoY"},
                        {"label": "CAGR", "value": "38%", "change": "High"},
                        {"label": "Growth", "value": "10x", "change": "3-5 years"},
                    ],
                },
                "design": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#1E1B4B", "#6366F1"],
                        "angle": 135,
                    },
                    "heading": {"color": "#E0E7FF", "font": "Inter"},
                    "body": {"color": "#C7D2FE", "font": "Inter"},
                    "accent": {"color": "#6366F1"},
                },
                "notes": "The market is huge and growing fast. We're positioned to capture significant share.",
            },
            {
                "index": 4,
                "title": "Traction: 150+ Enterprise Customers",
                "layout": "bullets",
                "kind": "traction",
                "purpose": "Show evidence of product-market fit",
                "content": {
                    "headline": "Proven Traction",
                    "bullets": [
                        "🏆 150+ enterprise customers including 5 Fortune 500",
                        "📈 $5M ARR growing 300% YoY",
                        "⭐ 4.8/5 rating on G2 from 200+ reviews",
                        "💰 $25M saved by customers in first 6 months",
                    ],
                },
                "design": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#0F172A", "#0EA5E9"],
                        "angle": 135,
                    },
                    "heading": {"color": "#E0F2FE", "font": "Inter"},
                    "body": {"color": "#BAE6FD", "font": "Inter"},
                    "accent": {"color": "#0EA5E9"},
                },
                "notes": "We're not just promising - we're delivering real results for real customers.",
            },
            {
                "index": 5,
                "title": "The Team: Ex-Google, Meta, Microsoft",
                "layout": "two-column",
                "kind": "team",
                "purpose": "Show why this team can win",
                "content": {
                    "headline": "World-Class Team",
                    "bullets": [
                        "👨‍💻 CEO: Ex-Google AI Lead, 15 years in ML",
                        "👩‍💼 CTO: Ex-Meta, built systems serving 1B+ users",
                        "📊 COO: Ex-McKinsey, scaled 3 startups to exit",
                    ],
                },
                "design": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#1E293B", "#8B5CF6"],
                        "angle": 135,
                    },
                    "heading": {"color": "#EDE9FE", "font": "Inter"},
                    "body": {"color": "#DDD6FE", "font": "Inter"},
                    "accent": {"color": "#8B5CF6"},
                },
                "notes": "We've worked together before. This is our third startup.",
            },
            {
                "index": 6,
                "title": "The Ask: $20M Series A",
                "layout": "bullets",
                "kind": "ask",
                "purpose": "Clear call to action",
                "content": {
                    "headline": "Funding Ask: $20M Series A",
                    "bullets": [
                        "💵 $20M to accelerate go-to-market",
                        "📈 3x revenue in next 18 months",
                        "🎯 Expand team from 30 to 80",
                        "🏆 Target: Market leader in AI automation",
                    ],
                },
                "design": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#18181B", "#F59E0B"],
                        "angle": 135,
                    },
                    "heading": {"color": "#FEF3C7", "font": "Inter"},
                    "body": {"color": "#FDE68A", "font": "Inter"},
                    "accent": {"color": "#F59E0B"},
                },
                "notes": "We're looking for partners who share our vision. Let's build the future together.",
            },
        ],
        "strategy": {
            "archetype": "series_a",
            "archetype_name": "Series A Pitch",
            "structure": [
                {"index": 0, "title": "AI Revolution", "layout": "title-hero"},
                {"index": 1, "title": "Problem", "layout": "two-column"},
                {"index": 2, "title": "Solution", "layout": "bullets"},
                {"index": 3, "title": "Market", "layout": "kpi-dashboard"},
                {"index": 4, "title": "Traction", "layout": "bullets"},
                {"index": 5, "title": "Team", "layout": "two-column"},
                {"index": 6, "title": "Ask", "layout": "bullets"},
            ],
        },
        "design": {
            "colors": {
                "primary": "#6366F1",
                "secondary": "#8B5CF6",
                "accent": "#0EA5E9",
                "background": "#0F172A",
                "text": "#F8FAFC",
                "muted": "#94A3B8",
            },
            "fonts": {"heading": "Inter", "body": "Inter"},
        },
        "quality_score": 85.0,
        "coherence_score": 90.0,
        "total_time_ms": 1000,
        "errors": [],
        "reveal_html": None,
    }


def use_demo_mode():
    """Switch to demo mode with pre-built slides."""
    st.session_state["demo_mode"] = True
    st.session_state["last_result"] = get_sample_slides()
    st.session_state["last_deck_id"] = "demo-deck-001"
    st.session_state["last_mode"] = "demo"


def check_server_health() -> dict:
    """Check if server4 is running."""
    try:
        r = requests.get(f"{SERVER4_URL}/health", timeout=3)
        return {"online": True, "status": r.json().get("status", "ok")}
    except Exception:
        return {"online": False, "status": "offline"}


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
    """Start V3 generation."""
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


def get_preview_html(deck_id: str) -> str:
    """Get compiled reveal.js HTML."""
    try:
        r = requests.get(f"{API_V3}/deck/{deck_id}/preview", timeout=30)
        if r.status_code == 409:
            # Generation not complete
            raise Exception("Generation not complete yet")
        r.raise_for_status()
        return r.text
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            raise Exception("Presentation is still generating. Please wait.")
        raise


def compile_react(presentation_dsl: dict, theme_id: str = None) -> dict:
    """Compile PresentationDSL to React + Three.js bundle."""
    payload = {
        "presentation": presentation_dsl,
        "theme_id": theme_id,
        "quality": "high",
        "enable_3d": True,
    }
    r = requests.post(f"{API_V2}/react/compile", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def compile_html(presentation_dsl: dict, theme_id: str = None) -> dict:
    """Compile PresentationDSL to reveal.js HTML via renderer endpoint."""
    payload = {"presentation": presentation_dsl, "theme_id": theme_id}
    r = requests.post(f"{API_V2}/render/compile", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def list_themes() -> list:
    """List available built-in themes."""
    try:
        r = requests.get(f"{API_V2}/themes/built-in", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# SLIDE HTML RENDERER (layout-aware)
# ═══════════════════════════════════════════════════════════════


def render_slide_card(
    slide: dict,
    theme: dict,
    width: int = 440,
    height: int = 248,
) -> str:
    """Render a single slide as a styled HTML preview card."""
    content = slide.get("content", {})
    if isinstance(content, str):
        content = {"body_text": content}

    # V3 format uses "headline" for title, not "title"
    # Also check slide.get("title") for fallback
    title = html_lib.escape(
        str(content.get("headline", slide.get("title", "Untitled")))
    )
    subtitle = html_lib.escape(str(content.get("subtitle", "")))

    # V3 format has bullets in content.bullets as list
    bullets = content.get("bullets", [])
    if not bullets and content.get("data"):
        # If no bullets but has data, create bullet from data
        data = content.get("data", [])
        bullets = [f"{d.get('value', '')} {d.get('label', '')}" for d in data[:5]]

    body = html_lib.escape(str(content.get("body_text", "")))
    layout = str(slide.get("layout", "title-content"))
    slide_type = str(slide.get("kind", slide.get("type", "")))

    # V3 uses "notes" key
    notes = html_lib.escape(str(slide.get("notes", slide.get("speakerNotes", ""))))
    slide_idx = slide.get("index", slide.get("slide_number", ""))

    # Get background from design
    design = slide.get("design", {})
    bg_dict = design.get("background", {}) if isinstance(design, dict) else {}
    if bg_dict and isinstance(bg_dict, dict):
        colors = bg_dict.get("colors", ["#0f172a"])
        bg = colors[0] if colors else "#0f172a"
    else:
        bg = theme.get("backgroundColor", "#0f172a")

    primary = theme.get("primaryColor", "#f8fafc")
    secondary = theme.get("secondaryColor", "#94a3b8")
    accent = theme.get("accentColor", "#6366f1")
    font = theme.get("fontFamily", "Inter, system-ui, sans-serif")

    kind_color = SLIDE_KIND_COLORS.get(slide_type, accent)
    lm = LAYOUT_META.get(layout, {"emoji": "📄", "label": layout})

    # Build content HTML based on layout
    if layout in ("title-hero", "title", "section-header", "center-focus"):
        content_html = f"""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;text-align:center;padding:24px;">
            <div style="width:40px;height:3px;background:{accent};border-radius:2px;margin-bottom:14px;"></div>
            <h2 style="color:{primary};font-size:20px;margin:0 0 8px;font-family:{font};font-weight:700;line-height:1.2;">{title}</h2>
            {f'<p style="color:{secondary};font-size:12px;max-width:80%;margin:0;font-family:{font};">{subtitle or body.split(chr(10))[0] if body else ""}</p>' if subtitle or body else ""}
        </div>"""

    elif layout in ("two-column", "comparison", "split-screen"):
        # For two-column, show title and bullets side by side
        bullet_html = ""
        if bullets:
            items = "".join(
                f'<li style="margin-bottom:4px;color:{secondary};font-size:10px;">{html_lib.escape(str(b))}</li>'
                for b in bullets[:6]
            )
            bullet_html = f'<ul style="margin:10px 0 0 16px;padding:0;list-style:disc;">{items}</ul>'

        content_html = f"""
        <div style="display:flex;flex-direction:column;height:100%;padding:20px;">
            <h2 style="color:{primary};font-size:16px;margin:0 0 10px;font-family:{font};font-weight:700;">{title}</h2>
            <div style="flex:1;display:flex;flex-direction:column;">
                {bullet_html if bullet_html else f'<p style="color:{secondary};font-size:10px;margin:0;">{body or "Add your content here"}</p>'}
            </div>
        </div>"""

    elif layout in ("bullets", "bullets-with-image"):
        bullet_html = ""
        if bullets:
            items = "".join(
                f'<li style="margin-bottom:4px;color:{secondary};font-size:10px;">{html_lib.escape(str(b))}</li>'
                for b in bullets[:10]
            )
            bullet_html = f'<ul style="margin:10px 0 0 16px;padding:0;list-style:disc;">{items}</ul>'

        content_html = f"""
        <div style="display:flex;flex-direction:column;height:100%;padding:20px 24px;">
            <h2 style="color:{primary};font-size:16px;margin:0 0 8px;font-family:{font};font-weight:700;">{title}</h2>
            <div style="flex:1;overflow:hidden;">
                {bullet_html if bullet_html else f'<p style="color:{secondary};font-size:10px;">{body or ""}</p>'}
            </div>
            <div style="display:flex;gap:4px;margin-top:auto;padding-top:6px;">
                <div style="height:2px;flex:1;background:{accent};border-radius:1px;"></div>
                <div style="height:2px;width:16px;background:{secondary};opacity:0.2;border-radius:1px;"></div>
            </div>
        </div>"""

    elif layout == "kpi-dashboard":
        kpis = content.get("kpi_metrics", [])
        if not kpis and content.get("data"):
            # Create KPIs from data
            data = content.get("data", [])
            kpis = [
                {"label": d.get("label", ""), "value": d.get("value", ""), "change": ""}
                for d in data[:4]
            ]

        if kpis:
            cards = ""
            for k in kpis[:6]:
                cards += f"""
                <div style="background:{accent}12;border-radius:6px;padding:8px;text-align:center;">
                    <div style="font-size:8px;color:{secondary};">{html_lib.escape(str(k.get("label", "")))}</div>
                    <div style="font-size:14px;font-weight:700;color:{primary};">{html_lib.escape(str(k.get("value", "")))}</div>
                </div>"""
            content_html = f"""
            <div style="display:flex;flex-direction:column;height:100%;padding:20px;">
                <h2 style="color:{primary};font-size:16px;margin:0 0 10px;font-family:{font};font-weight:700;">{title}</h2>
                <div style="flex:1;display:grid;grid-template-columns:repeat(2,1fr);gap:8px;align-content:center;">{cards}</div>
            </div>"""
        else:
            content_html = _default_content(
                title, bullets, body, font, primary, secondary, accent
            )

    elif layout in ("image-left", "image-right", "text-left-visual-right"):
        img_url = content.get("image_url", "")
        img_block = (
            f'<img src="{html_lib.escape(img_url)}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;" />'
            if img_url
            else f'<div style="width:100%;height:100%;background:{accent}15;border-radius:6px;display:flex;align-items:center;justify-content:center;"><span style="color:{secondary};opacity:0.4;font-size:9px;">Image</span></div>'
        )

        bullet_html = ""
        if bullets:
            items = "".join(
                f'<li style="margin-bottom:4px;color:{secondary};font-size:10px;">{html_lib.escape(str(b))}</li>'
                for b in bullets[:6]
            )
            bullet_html = f'<ul style="margin:8px 0 0 16px;padding:0;list-style:disc;">{items}</ul>'

        text_block = f"""
        <div style="display:flex;flex-direction:column;justify-content:center;">
            <h2 style="color:{primary};font-size:14px;margin:0 0 6px;font-family:{font};font-weight:700;">{title}</h2>
            {bullet_html if bullet_html else f'<p style="color:{secondary};font-size:10px;margin:0;">{body}</p>'}
        </div>"""
        grid = (
            f"{img_block}{text_block}"
            if "left" in layout
            else f"{text_block}{img_block}"
        )
        content_html = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;height:100%;padding:20px;">{grid}</div>'

    else:
        content_html = _default_content(
            title, bullets, body, font, primary, secondary, accent
        )

    # Badges
    kind_badge = ""
    if slide_type:
        kind_badge = f'<span style="position:absolute;top:8px;left:10px;font-size:8px;background:{kind_color}22;color:{kind_color};padding:1px 6px;border-radius:8px;font-weight:600;">{html_lib.escape(slide_type)}</span>'

    layout_badge = f'<span style="position:absolute;top:8px;right:10px;font-size:8px;color:{secondary};opacity:0.5;">{lm["emoji"]} {html_lib.escape(lm["label"])}</span>'
    num_badge = (
        f'<span style="position:absolute;bottom:6px;right:10px;font-size:9px;color:{secondary};opacity:0.35;">Slide {int(slide_idx) + 1 if slide_idx != "" else "?"}</span>'
        if slide_idx != ""
        else ""
    )

    return f"""
    <div class="slide-card" style="width:{width}px;height:{height}px;background:{bg};overflow:hidden;position:relative;font-family:{font};">
        {kind_badge}{layout_badge}{num_badge}
        {content_html}
    </div>"""


def _default_content(
    title: str,
    bullets: list,
    body: str,
    font: str,
    primary: str,
    secondary: str,
    accent: str,
) -> str:
    """Default title + bullets/body layout."""
    bullet_html = ""
    if bullets:
        items = "".join(
            f'<li style="margin-bottom:4px;">{html_lib.escape(str(b))}</li>'
            for b in bullets[:10]
        )
        bullet_html = f'<ul style="margin:0;padding-left:16px;list-style:disc;color:{secondary};font-size:10px;line-height:1.5;font-family:{font};">{items}</ul>'

    return f"""
    <div style="display:flex;flex-direction:column;height:100%;padding:20px 24px;">
        <h2 style="color:{primary};font-size:16px;margin:0 0 8px;font-family:{font};font-weight:700;line-height:1.2;">{title}</h2>
        <div style="flex:1;overflow:hidden;">
            {bullet_html if bullet_html else f'<p style="color:{secondary};font-size:10px;margin:0;white-space:pre-wrap;line-height:1.4;font-family:{font};">{body or ""}</p>'}
        </div>
        <div style="display:flex;gap:4px;margin-top:auto;padding-top:6px;">
            <div style="height:2px;flex:1;background:{accent};border-radius:1px;"></div>
            <div style="height:2px;width:16px;background:{secondary};opacity:0.2;border-radius:1px;"></div>
        </div>
    </div>"""


def extract_theme(result: dict) -> dict:
    """Extract theme from generation result or return defaults."""
    design = result.get("design", {})

    if isinstance(design, dict):
        # V3 format: design.colors contains the palette
        colors = design.get("colors", {})
        if colors:
            return {
                "backgroundColor": colors.get(
                    "background", colors.get("background", "#0f172a")
                ),
                "primaryColor": colors.get("primary", colors.get("text", "#f8fafc")),
                "secondaryColor": colors.get(
                    "secondary", colors.get("muted", "#94a3b8")
                ),
                "accentColor": colors.get("accent", "#6366f1"),
                "fontFamily": design.get("fonts", {}).get(
                    "heading", "Inter, system-ui, sans-serif"
                ),
            }

        # Check slide_specs for background colors
        slide_specs = design.get("slide_specs", [])
        if slide_specs and len(slide_specs) > 0:
            first_spec = slide_specs[0]
            bg = first_spec.get("background", {})
            if bg and bg.get("colors"):
                colors = bg.get("colors", [])
                return {
                    "backgroundColor": colors[0] if colors else "#0f172a",
                    "primaryColor": "#f8fafc",
                    "secondaryColor": "#94a3b8",
                    "accentColor": "#6366f1",
                    "fontFamily": "Inter, system-ui, sans-serif",
                }

    return {
        "backgroundColor": "#0f172a",
        "primaryColor": "#f8fafc",
        "secondaryColor": "#94a3b8",
        "accentColor": "#6366f1",
        "fontFamily": "Inter, system-ui, sans-serif",
    }


# ═══════════════════════════════════════════════════════════════
# PIPELINE VISUALIZATION
# ═══════════════════════════════════════════════════════════════

AGENT_STAGES = [
    {
        "name": "CEO Strategist",
        "icon": "👑",
        "color": "#6366F1",
        "desc": "Narrative arc & slide outline",
    },
    {
        "name": "Researcher",
        "icon": "🔬",
        "color": "#22C55E",
        "desc": "Evidence gathering & citations",
    },
    {
        "name": "Designer",
        "icon": "🎨",
        "color": "#F59E0B",
        "desc": "Visual design system & layout",
    },
    {
        "name": "Layout Solver",
        "icon": "📐",
        "color": "#EC4899",
        "desc": "Grid & element positioning",
    },
    {
        "name": "Code Agent",
        "icon": "💻",
        "color": "#8B5CF6",
        "desc": "DSL generation & skills",
    },
    {
        "name": "VFX Agent",
        "icon": "✨",
        "color": "#06B6D4",
        "desc": "3D scenes & animations",
    },
    {
        "name": "Assembler",
        "icon": "🔧",
        "color": "#F97316",
        "desc": "Slide assembly & synthesis",
    },
    {
        "name": "QA Reviewer",
        "icon": "🛡️",
        "color": "#EF4444",
        "desc": "Quality gates & coherence",
    },
]


def render_pipeline(status: str, progress: float, active_stage: int = -1):
    """Render the agent pipeline visualization."""
    is_running = status in ("running", "queued")
    is_done = status in ("completed", "failed", "partial")

    for i, stage in enumerate(AGENT_STAGES):
        if is_done:
            state = "done"
        elif is_running and i <= active_stage:
            state = "active" if i == active_stage else "done"
        else:
            state = "pending"

        st.markdown(
            f"""
        <div class="pipeline-step {state}">
            <div class="pipeline-icon" style="background:{stage["color"]}20;color:{stage["color"]};">{stage["icon"]}</div>
            <div>
                <div style="font-size:13px;font-weight:600;color:#f8fafc;">{stage["name"]}</div>
                <div style="font-size:11px;color:#94a3b8;">{stage["desc"]}</div>
            </div>
            <div style="margin-left:auto;font-size:11px;">
                {"✅" if state == "done" else "⏳" if state == "active" else "○"}
            </div>
        </div>""",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════


def page_generate():
    """Main generation page — the primary user demo flow."""
    st.title("🎯 Presentation Generator")
    st.caption(
        "Enter your topic and watch the AI generate a complete presentation in real-time"
    )

    # Demo mode button
    col_demo1, col_demo2 = st.columns([1, 4])
    with col_demo1:
        if st.button(
            "🎮 Try Demo Mode", help="See a working demo without AI generation"
        ):
            use_demo_mode()
            st.rerun()
    with col_demo2:
        st.caption(
            "Don't want to wait for AI? Try the demo to see how slides will look!"
        )

    # Check if demo mode is active
    if st.session_state.get("demo_mode", False):
        st.success("🎮 Demo Mode Active - Showing pre-built slides")

        result = st.session_state.get("last_result", {})
        if result:
            # Show demo slides
            _display_results_demo(result, "demo-deck-001")

        if st.button("🔄 Back to Real Generation"):
            st.session_state["demo_mode"] = False
            st.session_state.pop("last_result", None)
            st.session_state.pop("last_deck_id", None)
            st.rerun()
        return

    # Input form
    with st.form("gen_form"):
        c1, c2 = st.columns(2)
        with c1:
            topic = st.text_input(
                "Topic / Product *", value="AI-Powered Developer Tools"
            )
            company = st.text_input("Company Name", value="CodeForge AI")
            description = st.text_area(
                "Description",
                value="An AI-native IDE extension that writes production-grade code, runs tests, and deploys — reducing development time by 10x for engineering teams.",
                height=80,
            )
        with c2:
            audience = st.selectbox("Audience", AUDIENCES, index=0)
            purpose = st.selectbox("Purpose", PURPOSES, index=0)
            mode = st.selectbox("Mode", MODES, index=0)
            slide_count = st.slider("Number of Slides", 5, 15, 10)
            writing_style = st.selectbox("Writing Style", WRITING_STYLES, index=0)

        submitted = st.form_submit_button(
            "🚀 Generate Presentation", type="primary", use_container_width=True
        )

    if not submitted:
        return

    # ── Start Generation ──
    status_area = st.empty()
    progress_bar = st.progress(0)
    pipeline_col, result_col = st.columns([1, 2])

    with status_area:
        st.info(f"Starting {mode} generation for '{topic}' ({slide_count} slides)...")

    try:
        resp = start_generation(
            topic=topic,
            description=description,
            company_name=company,
            audience=audience,
            purpose=purpose,
            mode=mode,
            slide_count=slide_count,
            writing_style=writing_style,
        )
    except requests.ConnectionError:
        st.error(
            "❌ Cannot connect to server4. Is it running on port 8003?\n\nStart with: `cd server4 && python run.py`"
        )
        return
    except requests.HTTPError as e:
        st.error(f"❌ Failed to start generation: {e.response.text[:300]}")
        return

    deck_id = resp.get("deck_id", "")
    with status_area:
        st.success(f"Generation started — Deck ID: `{deck_id[:12]}...`")

    # ── Poll Status ──
    start_time = time.time()
    max_wait = 180 if mode == "standard" else 660
    final_status = None
    poll_count = 0

    while time.time() - start_time < max_wait:
        time.sleep(POLL_INTERVAL)
        poll_count += 1
        try:
            status_resp = poll_status(deck_id)
        except Exception:
            continue

        current = status_resp.get("status", "unknown")

        # FIX: Handle total_slides being 0 - use slide_count from request or count from result
        total = status_resp.get("total_slides", slide_count)
        generated = status_resp.get("total_slides_generated", 0)

        # If total is 0 but status is completed, use slide_count
        if total == 0 and current == "completed":
            total = slide_count
            generated = slide_count

        progress = (
            min(generated / total, 1.0)
            if total > 0
            else (0.5 if current == "running" else 1.0)
        )
        elapsed = time.time() - start_time

        progress_bar.progress(progress)

        with status_area:
            st.info(
                f"⏳ **{current.upper()}** — {generated}/{total} slides ({elapsed:.0f}s)"
            )

        # Update pipeline visualization
        active_stage = int(progress * len(AGENT_STAGES)) if current == "running" else -1
        with pipeline_col:
            st.subheader("Agent Pipeline")
            render_pipeline(current, progress, active_stage)

        if current in ("completed", "failed", "partial"):
            final_status = status_resp
            break

    if final_status is None:
        st.error(f"⏰ Timed out after {max_wait}s")
        return

    progress_bar.progress(1.0)

    # ── Display Results ──
    if final_status.get("status") == "completed":
        elapsed = time.time() - start_time
        with status_area:
            st.success(
                f"✅ Generation complete in {elapsed:.1f}s — Quality: {final_status.get('quality_score', 0):.1f}/100"
            )

        try:
            result = get_result(deck_id)
        except Exception as e:
            st.error(f"Failed to fetch result: {e}")
            return

        # Debug: Print result structure
        slides = result.get("slides", [])
        st.write(f"Debug: Found {len(slides)} slides")

        if not slides:
            # Try to get slides from strategy structure as fallback
            strategy = result.get("strategy", {})
            structure = strategy.get("structure", [])
            if structure:
                st.info(
                    f"Found {len(structure)} slides in strategy structure - using those"
                )
                # Build slides from strategy
                for i, s in enumerate(structure):
                    slides.append(
                        {
                            "index": i,
                            "title": s.get("title", f"Slide {i + 1}"),
                            "layout": s.get("layout", "bullets"),
                            "purpose": s.get("purpose", ""),
                            "content": {
                                "headline": s.get("title", f"Slide {i + 1}"),
                                "bullets": [],
                            },
                            "notes": s.get("content_hints", ""),
                        }
                    )
                result["slides"] = slides

        # Store in session
        st.session_state["last_result"] = result
        st.session_state["last_deck_id"] = deck_id
        st.session_state["last_mode"] = mode

        _display_results(result, deck_id, mode)

    elif final_status.get("status") == "partial":
        with status_area:
            st.warning("⚠️ Partial generation completed — some slides may be missing")
        try:
            result = get_result(deck_id)
            st.session_state["last_result"] = result
            st.session_state["last_deck_id"] = deck_id
            _display_results(result, deck_id, mode)
        except Exception:
            pass
    else:
        with status_area:
            st.error(
                f"❌ Generation failed: {json.dumps(final_status.get('errors', []))}"
            )


def _display_results(result: dict, deck_id: str, mode: str):
    """Display the full generation results with all preview modes."""
    slides = result.get("slides", [])

    # If slides still empty, show error
    if not slides:
        st.error("No slides were generated. Try Demo Mode to see expected output.")

        # Offer demo option
        if st.button("🎮 Try Demo Mode Instead"):
            use_demo_mode()
            st.rerun()
        return

    # ... rest of function
    quality = result.get("quality_score", 0)
    coherence = result.get("coherence_score", 0)
    total_time = result.get("total_time_ms", 0)
    errors = result.get("errors", [])

    # Metrics
    st.markdown("---")
    st.subheader("📊 Generation Metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Slides", len(slides))
    m2.metric("Quality", f"{quality:.1f}")
    m3.metric("Coherence", f"{coherence:.1f}")
    m4.metric("Time (ms)", f"{total_time:.0f}")
    m5.metric("Errors", len(errors))

    if errors:
        for e in errors:
            st.error(e)

    # Strategy (CEO output)
    strategy = result.get("strategy")
    if strategy:
        with st.expander("🧠 CEO Strategy & Narrative"):
            st.json(strategy)

    # Evidence (premium)
    evidence = result.get("evidence_report")
    if evidence:
        with st.expander("🔬 Evidence Report (Premium)"):
            st.json(evidence)

    # Design config
    design = result.get("design")
    if design:
        with st.expander("🎨 Design Configuration"):
            st.json(design)

    # ── Preview Tabs ──
    st.markdown("---")
    st.subheader("🖼️ Slide Preview")

    theme = extract_theme(result)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📋 Slide Cards",
            "🎬 reveal.js Live",
            "⚛️ React + Three.js",
            "🌐 HTML Preview",
            "📥 Downloads",
        ]
    )

    with tab1:
        _render_slide_cards_view(slides, theme)

    with tab2:
        _render_revealjs_view(deck_id)

    with tab3:
        _render_react_view(result)

    with tab4:
        _render_html_view(result)

    with tab5:
        _render_downloads_view(result, deck_id)


def _display_results_demo(result: dict, deck_id: str):
    """Display results for demo mode - uses in-browser reveal.js rendering."""
    slides = result.get("slides", [])
    quality = result.get("quality_score", 0)
    total_time = result.get("total_time_ms", 0)
    errors = result.get("errors", [])

    if not slides:
        st.error("No slides in demo data!")
        return

    # Metrics
    st.markdown("---")
    st.subheader("📊 Demo Presentation Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Slides", len(slides))
    m2.metric("Quality", f"{quality:.1f}" if quality else "Demo")
    m3.metric("Time (ms)", f"{total_time:.0f}" if total_time else "< 1s")
    m4.metric("Errors", len(errors))

    if errors:
        for e in errors:
            st.error(e)

    # Theme
    design = result.get("design", {})
    colors = design.get("colors", {}) if isinstance(design, dict) else {}
    theme = {
        "backgroundColor": colors.get("background", "#0f172a"),
        "primaryColor": colors.get("primary", "#f8fafc"),
        "secondaryColor": colors.get("secondary", "#94a3b8"),
        "accentColor": colors.get("accent", "#6366f1"),
        "fontFamily": "Inter, system-ui, sans-serif",
    }

    # Preview tabs
    st.markdown("---")
    st.subheader("🖼️ Slide Preview")

    tab1, tab2, tab3 = st.tabs(["📋 Slide Cards", "🎬 Live Preview", "📥 Download"])

    with tab1:
        _render_slide_cards_view(slides, theme)

    with tab2:
        # Demo mode: render slides in browser with reveal.js
        st.info("🎮 Demo Mode: Using in-browser slide rendering")

        # Create simple HTML with all slides
        slides_html = ""
        for slide in slides:
            content = slide.get("content", {})
            if isinstance(content, str):
                content = {"headline": content}

            headline = content.get("headline", slide.get("title", ""))
            bullets = content.get("bullets", [])

            design = slide.get("design", {})
            bg_colors = design.get("background", {}).get(
                "colors", ["#0f172a", "#1e293b"]
            )
            bg = f"linear-gradient(135deg, {bg_colors[0]}, {bg_colors[1] if len(bg_colors) > 1 else bg_colors[0]})"

            bullet_html = ""
            if bullets:
                bullet_items = "".join(
                    [f"<li>{html_lib.escape(str(b))}</li>" for b in bullets[:8]]
                )
                bullet_html = f"<ul>{bullet_items}</ul>"

            slides_html += f"""
<section data-background-gradient="{bg}">
    <div style="padding: 40px;">
        <h2 style="color: white; font-size: 2.5em; margin-bottom: 20px;">{html_lib.escape(headline)}</h2>
        <div style="color: #cbd5e1; font-size: 1.2em;">{bullet_html}</div>
    </div>
</section>
"""

        # Simple reveal.js HTML
        reveal_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Demo Presentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/black.css">
    <style>
        .reveal ul {{ list-style: none; padding: 0; }}
        .reveal li {{ padding: 10px 0; color: #cbd5e1; }}
        .reveal li::before {{ content: "▸ "; color: #6366f1; }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
            {slides_html}
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
    <script>
        Reveal.initialize({{
            hash: true,
            center: true,
            transition: 'slide',
            backgroundTransition: 'fade'
        }});
    </script>
</body>
</html>"""

        if st.button("Load Live Preview"):
            st.session_state["demo_reveal_html"] = reveal_html

        if st.session_state.get("demo_reveal_html"):
            st.success(
                f"Presentation loaded ({len(st.session_state['demo_reveal_html']):,} bytes)"
            )
            components.html(
                st.session_state["demo_reveal_html"], height=600, scrolling=True
            )

            st.download_button(
                "📥 Download HTML",
                data=st.session_state["demo_reveal_html"],
                file_name="demo_presentation.html",
                mime="text/html",
            )

    with tab3:
        # Demo download
        st.subheader("📥 Export Options")
        st.download_button(
            "📄 Download Slides JSON",
            data=json.dumps(slides, indent=2),
            file_name="demo_slides.json",
            mime="application/json",
        )

        st.download_button(
            "📦 Download Full Result",
            data=json.dumps(result, indent=2, default=str),
            file_name="demo_result.json",
            mime="application/json",
        )


def _render_slide_cards_view(slides: list, theme: dict):
    """Render slides as preview cards in a grid."""
    if not slides:
        st.info("No slides to preview.")
        return

    st.write(f"**Showing {len(slides)} slides**")

    # Debug: Show first slide structure
    with st.expander("🔍 Debug: First slide structure"):
        st.json(slides[0] if slides else {})

    view = st.radio(
        "View Mode", ["2-Column Grid", "Full Width", "JSON"], horizontal=True
    )

    if view == "2-Column Grid":
        for i in range(0, len(slides), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(slides):
                    break
                slide = slides[idx]
                with col:
                    try:
                        slide_html = render_slide_card(
                            slide, theme, width=440, height=248
                        )
                        st.markdown(slide_html, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Error rendering slide {idx}: {e}")

                    content = slide.get("content", {})
                    if isinstance(content, str):
                        content = {"body_text": content}

                    # V3 format: content.get("headline") for title
                    title = content.get("headline", slide.get("title", ""))
                    kind = slide.get("kind", slide.get("type", ""))
                    layout = slide.get("layout", "")
                    # V3 uses "notes" not "speakerNotes"
                    notes = slide.get("notes", slide.get("speakerNotes", ""))

                    st.caption(f"**Slide {idx + 1}** — {kind} · {layout}")
                    if title:
                        st.caption(f"📌 {title[:60]}...")
                    if notes:
                        with st.expander("📝 Speaker Notes"):
                            st.write(notes)

    elif view == "Full Width":
        slide_idx = st.slider("Slide", 1, len(slides), 1, key="full_slider")
        slide = slides[slide_idx - 1]

        try:
            slide_html = render_slide_card(slide, theme, width=880, height=495)
            st.markdown(
                f'<div style="display:flex;justify-content:center;">{slide_html}</div>',
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.error(f"Error rendering slide: {e}")

        content = slide.get("content", {})
        if isinstance(content, dict):
            st.write(f"**Title:** {content.get('headline', content.get('title', ''))}")
            st.write(f"**Type:** {slide.get('kind', slide.get('type', ''))}")
            st.write(f"**Layout:** {slide.get('layout', '')}")
            st.write(f"**Bullets:** {len(content.get('bullets', []))} items")

        notes = slide.get("notes", slide.get("speakerNotes", ""))
        if notes:
            st.info(f"**Speaker Notes:** {notes}")

        with st.expander("🔍 Slide Raw Data"):
            st.json(slide)

    else:
        st.json(slides)


def _render_revealjs_view(deck_id: str):
    """Embed the compiled reveal.js presentation in an iframe."""
    if not deck_id:
        st.warning("No deck ID available. Generate a deck first.")
        return

    # Check if we have cached HTML for the CURRENT deck
    cached_deck = st.session_state.get("revealjs_deck", "")
    cached = st.session_state.get("revealjs_html", "")

    if cached and cached_deck != deck_id:
        # Clear cached HTML if it's from a different deck
        cached = ""

    if st.button("Load reveal.js Presentation", type="primary", key="revealjs_load"):
        with st.spinner("Loading reveal.js presentation..."):
            try:
                reveal_html = get_preview_html(deck_id)
                if reveal_html and len(reveal_html) > 100:
                    st.session_state["revealjs_html"] = reveal_html
                    st.session_state["revealjs_deck"] = deck_id
                    cached = reveal_html
                else:
                    st.error(
                        "No preview HTML available yet. The generation might still be processing."
                    )
                    return
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to server4. Is it running?")
                return
            except Exception as e:
                st.error(f"Preview error: {e}")
                return

    if cached and len(cached) > 100:
        st.success(f"reveal.js presentation loaded ({len(cached):,} bytes)")

        # Use a container with proper sizing for the presentation
        with st.container():
            components.html(cached, height=700, scrolling=True)

        st.download_button(
            "📥 Download reveal.js HTML",
            data=cached,
            file_name=f"presentation_{deck_id[:8]}.html",
            mime="text/html",
            key="revealjs_dl",
        )
    else:
        st.info("Click 'Load reveal.js Presentation' to load the generated slides.")


def _render_react_view(result: dict):
    """Show React + Three.js compiled code."""
    slides = result.get("slides", [])
    if not slides:
        st.info("No slides to preview.")
        return

    if st.button(
        "Compile React + Three.js Bundle", type="primary", key="react_compile"
    ):
        # Build a minimal PresentationDSL from the result
        dsl = _build_dsl_from_result(result)
        if dsl:
            with st.spinner("Compiling React + Three.js..."):
                try:
                    react_result = compile_react(dsl)
                    st.session_state["react_result"] = react_result
                except Exception as e:
                    st.error(f"React compilation error: {e}")
                    return

    react = st.session_state.get("react_result")
    if react and react.get("success"):
        st.success(f"React bundle compiled — {react.get('slide_count', 0)} slides")

        tab_a, tab_b, tab_c, tab_d = st.tabs(
            [
                "App.tsx",
                "Theme CSS",
                "Vite Config",
                "Dependencies",
            ]
        )

        with tab_a:
            st.code(react.get("app_tsx", ""), language="typescript")

        with tab_b:
            st.code(react.get("theme_css", ""), language="css")

        with tab_c:
            st.code(react.get("vite_config", ""), language="javascript")

        with tab_d:
            st.json(react.get("import_manifest", {}))

        # Scene configs
        scenes = react.get("scene_configs", [])
        if scenes:
            st.subheader("🎮 Three.js Scene Configs")
            for scene in scenes:
                st.json(scene)
    else:
        st.info("Click 'Compile React + Three.js Bundle' to generate the React code.")


def _render_html_view(result: dict):
    """Show HTML builder preview."""
    slides = result.get("slides", [])
    if not slides:
        st.info("No slides to preview.")
        return

    if st.button("Compile HTML Preview", type="primary", key="html_compile"):
        dsl = _build_dsl_from_result(result)
        if dsl:
            with st.spinner("Compiling HTML..."):
                try:
                    html_result = compile_html(dsl)
                    st.session_state["html_result"] = html_result
                except Exception as e:
                    st.error(f"HTML compilation error: {e}")
                    return

    html_res = st.session_state.get("html_result")
    if html_res and html_res.get("success"):
        st.success(
            f"HTML compiled — {html_res.get('slide_count', 0)} slides ({len(html_res.get('html', '')):,} bytes)"
        )

        # Feature check
        html_str = html_res.get("html", "")
        features = {
            "Tailwind CSS": "tailwind" in html_str.lower()
            or "cdn.tailwindcss" in html_str.lower(),
            "Animations": "animate-" in html_str,
            "Keyboard Nav": "ArrowRight" in html_str or "keydown" in html_str.lower(),
            "Progress Bar": "progress" in html_str.lower(),
            "Chart.js": "chart.js" in html_str.lower() or "chartjs" in html_str.lower(),
        }

        c1, c2, c3, c4, c5 = st.columns(5)
        for i, (feat, present) in enumerate(features.items()):
            [c1, c2, c3, c4, c5][i].metric(feat, "✅" if present else "❌")

        # Live preview
        components.html(html_str, height=600, scrolling=True)

        st.download_button(
            "📥 Download HTML",
            data=html_str,
            file_name="presentation.html",
            mime="text/html",
            key="html_dl",
        )
    else:
        st.info("Click 'Compile HTML Preview' to generate the HTML output.")


def _render_downloads_view(result: dict, deck_id: str):
    """Download buttons for all formats."""
    slides = result.get("slides", [])

    st.subheader("📥 Export Options")

    # JSON export
    st.markdown("#### Raw Data")
    st.download_button(
        "📄 Download Slides JSON",
        data=json.dumps(slides, indent=2),
        file_name=f"slides_{deck_id[:8]}.json",
        mime="application/json",
    )

    # reveal.js HTML
    reveal_html = st.session_state.get("revealjs_html")
    if reveal_html:
        st.download_button(
            "🎬 Download reveal.js HTML",
            data=reveal_html,
            file_name=f"presentation_{deck_id[:8]}.html",
            mime="text/html",
            key="dl_revealjs",
        )

    # React bundle
    react = st.session_state.get("react_result")
    if react and react.get("success"):
        st.download_button(
            "⚛️ Download App.tsx",
            data=react.get("app_tsx", ""),
            file_name="App.tsx",
            mime="text/typescript",
            key="dl_react",
        )

    # Full result JSON
    st.download_button(
        "📦 Download Full Result JSON",
        data=json.dumps(result, indent=2, default=str),
        file_name=f"full_result_{deck_id[:8]}.json",
        mime="application/json",
    )


def _build_dsl_from_result(result: dict) -> Optional[dict]:
    """Build a minimal PresentationDSL dict from V3 result for renderer APIs."""
    slides = result.get("slides", [])
    if not slides:
        return None

    design = result.get("design", {})
    palette = {}
    if isinstance(design, dict):
        p = design.get("palette", design.get("color_palette", {}))
        if isinstance(p, dict):
            palette = p

    dsl_slides = []
    for i, s in enumerate(slides):
        content = s.get("content", {})
        if isinstance(content, str):
            content = {"body_text": content}

        dsl_slides.append(
            {
                "id": s.get("id", f"slide_{i}"),
                "index": i,
                "slide_type": s.get("kind", s.get("type", "title-content")),
                "layout": s.get("layout", "title-content"),
                "content": content,
                "speaker_notes": s.get("speakerNotes", s.get("notes", "")),
            }
        )

    return {
        "presentation": {
            "id": result.get("deck_id", "demo"),
            "title": result.get("topic", "Presentation"),
            "slides": dsl_slides,
            "metadata": {
                "audience": result.get("audience", "investors"),
                "purpose": result.get("purpose", "pitch"),
                "mode": result.get("mode", "standard"),
            },
        },
        "theme": {
            "colors": {
                "primary": palette.get("primary", "#f8fafc"),
                "accent": palette.get("accent", "#6366f1"),
                "background": palette.get("background", "#0f172a"),
                "text_primary": palette.get("primary", "#f8fafc"),
                "text_secondary": palette.get("secondary", "#94a3b8"),
            },
            "fonts": {
                "heading": design.get("font_family", "Inter"),
                "body": design.get("font_family", "Inter"),
            },
        },
    }


def page_library():
    """Theme library explorer."""
    st.title("🎨 Theme Library")
    st.caption("Explore available built-in themes for your presentations")

    if st.button("Load Themes", type="primary"):
        try:
            themes = list_themes()
            st.session_state["themes"] = themes
        except Exception as e:
            st.error(f"Failed to load themes: {e}")
            return

    themes = st.session_state.get("themes", [])
    if not themes:
        st.info("Click 'Load Themes' to fetch from server4.")
        return

    st.success(f"Found {len(themes)} themes")

    # Display as cards
    for i in range(0, len(themes), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(themes):
                break
            t = themes[idx]
            with col:
                # Color swatch
                swatch = f"""
                <div style="border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);">
                    <div style="height:80px;background:linear-gradient(135deg,{t.get("primary", "#6366f1")},{t.get("background", "#0f172a")});display:flex;align-items:center;justify-content:center;">
                        <span style="color:white;font-size:20px;font-weight:700;">{t.get("name", "?")}</span>
                    </div>
                    <div style="padding:12px;background:#1e293b;">
                        <div style="font-size:12px;color:#f8fafc;font-weight:600;">{t.get("id", "")}</div>
                        <div style="font-size:10px;color:#94a3b8;">{t.get("variant", "")} · {t.get("character", "")}</div>
                        <div style="font-size:10px;color:#94a3b8;margin-top:4px;">{t.get("heading_font", "")} / {t.get("body_font", "")}</div>
                    </div>
                </div>"""
                st.markdown(swatch, unsafe_allow_html=True)


def page_info():
    """System info and architecture overview."""
    st.title("ℹ️ System Overview")
    st.caption("Barise Presentation Engine — V7 Architecture")

    # Server health
    health = check_server_health()
    if health["online"]:
        st.success(f"🟢 Server4 is online ({health['status']})")
    else:
        st.error("🔴 Server4 is offline — run `cd server4 && python run.py`")

    st.markdown("---")

    # Architecture
    st.subheader("🏗️ Architecture")
    st.markdown("""
    | Layer | Component | Purpose |
    |---|---|---|
    | **API** | FastAPI (port 8003) | REST endpoints for generation, preview, export |
    | **Pipeline** | V3 Unified Pipeline | Orchestrates 8 AI agents for slide generation |
    | **Content** | Brain MCP | LLM-powered content generation with research engines |
    | **Design** | Design MCP | Visual design system, theme engine, layout solver |
    | **Render** | Render MCP | Multi-format output (reveal.js, React, HTML, PPTX) |
    | **Storage** | MongoDB + Redis | Deck state, progress tracking, caching |
    | **Workers** | Celery | Background export jobs (PPTX, PDF, PNG) |
    """)

    st.subheader("🤖 Agent Pipeline")
    for stage in AGENT_STAGES:
        st.markdown(f"- {stage['icon']} **{stage['name']}** — {stage['desc']}")

    st.subheader("🎨 Renderers")
    st.markdown("""
    | Renderer | Output | Use Case |
    |---|---|---|
    | **reveal.js** | Self-contained HTML | Primary presentation format, live preview |
    | **React + Three.js** | App.tsx + scenes | Interactive 3D presentations |
    | **HTML Builder** | Standalone HTML | Quick sharing, email embedding |
    | **PPTX** | PowerPoint file | Traditional download format |
    """)

    st.subheader("📡 API Endpoints")
    st.markdown("""
    | Method | Endpoint | Purpose |
    |---|---|---|
    | POST | `/api/v3/generate` | Start generation (standard/premium) |
    | GET | `/api/v3/deck/{id}/status` | Poll generation status |
    | GET | `/api/v3/deck/{id}/result` | Get full result |
    | GET | `/api/v3/deck/{id}/preview` | Compiled reveal.js HTML |
    | POST | `/api/v2/render/compile` | Compile DSL → reveal.js |
    | POST | `/api/v2/react/compile` | Compile DSL → React + Three.js |
    | GET | `/api/v2/themes/built-in` | List available themes |
    | GET | `/health` | Server health check |
    """)


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════


def main():
    # Sidebar
    st.sidebar.title("🎯 Barise")
    st.sidebar.caption("Presentation Prototype Demo")

    # Server status
    health = check_server_health()
    if health["online"]:
        st.sidebar.success("🟢 Server4 Online")
    else:
        st.sidebar.error("🔴 Server4 Offline")
        st.sidebar.caption("Run: `cd server4 && python run.py`")

    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigate",
        ["🚀 Generate", "🎨 Theme Library", "ℹ️ System Info"],
        index=0,
    )

    st.sidebar.markdown("---")
    last_id = st.session_state.get("last_deck_id", "")
    if last_id:
        st.sidebar.caption(f"Last deck: `{last_id[:12]}...`")

    # Route
    if "Generate" in page:
        page_generate()
    elif "Theme" in page:
        page_library()
    else:
        page_info()


if __name__ == "__main__":
    main()
