"""
Barise Presentation Engine - Streamlit Testing & Preview App

Run: streamlit run streamlit_app.py
Requires: pip install streamlit

Two modes:
  1. MOCK - Generate sample slides using the actual DSL models (no DB/LLM needed)
  2. LIVE - Connect to running server4 API (requires server4 running)
"""

import html
import json
import math
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# ── Add server4 root to path for imports ──
SERVER4_ROOT = str(Path(__file__).resolve().parent)
if SERVER4_ROOT not in sys.path:
    sys.path.insert(0, SERVER4_ROOT)

# Import DSL models
try:
    from app.models.dsl_v2 import (
        FragmentAnimation,
        LayoutType,
        PresentationDSL,
        RevealConfig,
        SlideDSL,
        SlideContentV2,
        SlideStyle,
        SlideType,
    )

    DSL_AVAILABLE = True
except ImportError:
    DSL_AVAILABLE = False

# Import agent/skill info for display
try:
    from app.services.slides_new.skills.skill_registry import (
        DEFAULT_SKILL_PROMPTS,
        DSL_SYSTEM_PROMPT,
        SkillRegistry,
    )

    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False

# Import agents for pipeline visualization
try:
    from app.services.slides_new.agents.protocols import (
        ArchetypeType,
        WritingStyle,
    )

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Page Config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.set_page_config(
    page_title="Barise Presentation Engine — Testing",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGENT_PIPELINE = [
    {
        "name": "CEO Agent",
        "model": "kimi-k2-thinking",
        "role": "Strategy & Narrative Arc",
        "color": "#6366F1",
        "icon": "👑",
    },
    {
        "name": "Researcher Agent",
        "model": "gpt-4o-mini",
        "role": "Evidence & Data Collection",
        "color": "#22C55E",
        "icon": "🔬",
    },
    {
        "name": "Designer Agent",
        "model": "deepseek-v3",
        "role": "Visual Design System",
        "color": "#F59E0B",
        "icon": "🎨",
    },
    {
        "name": "Layout Agent",
        "model": "gpt-4o-mini",
        "role": "Grid & Element Positioning",
        "color": "#EC4899",
        "icon": "📐",
    },
    {
        "name": "Code Agent",
        "model": "deepseek-v3 → router",
        "role": "DSL Generation + Skills",
        "color": "#8B5CF6",
        "icon": "💻",
    },
    {
        "name": "VFX Agent",
        "model": "deepseek-v3",
        "role": "3D Scenes & Animations",
        "color": "#06B6D4",
        "icon": "✨",
    },
    {
        "name": "Assembler Agent",
        "model": "deepseek-v3",
        "role": "Slide Assembly & Synthesis",
        "color": "#F97316",
        "icon": "🔧",
    },
    {
        "name": "QA Agent",
        "model": "gpt-4o-mini",
        "role": "Quality Gates & Coherence",
        "color": "#EF4444",
        "icon": "🛡️",
    },
]

# ── YC Seed Deck Slide Types ──
YC_DECK_SLIDES = [
    ("title-hero", "Title Slide"),
    ("problem", "Problem"),
    ("solution", "Solution"),
    ("traction", "Traction"),
    ("market", "Market Size"),
    ("business-model", "Business Model"),
    ("competition", "Competition"),
    ("team", "Team"),
    ("financials", "Financials"),
    ("ask", "The Ask"),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mock Data Generator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_mock_slides(
    topic: str,
    company: str,
    audience: str,
    archetype: str,
    num_slides: int = 10,
) -> List[Dict[str, Any]]:
    """Generate realistic mock slide data for preview."""
    slides = []

    templates = {
        "title-hero": {
            "layout": "center-focus",
            "content": {
                "title": company or topic,
                "subtitle": f"Transforming how {audience} approach {topic.lower()}",
                "tagline": "Series Seed | 2025",
                "image_prompt": f"Futuristic abstract visualization of {topic}, dark gradient background, glowing accent lines, premium tech aesthetic",
            },
            "speaker_notes": f"Welcome everyone. Today I want to share how {company or 'we'} are building the future of {topic.lower()}. In the next 10 minutes, I'll walk you through our vision, our traction, and why now is the right time.",
        },
        "problem": {
            "layout": "bullets",
            "content": {
                "title": f"The {topic} Problem",
                "bullets": [
                    f"87% of {audience} waste 40+ hours/month on manual {topic.lower()} tasks",
                    "Current tools are fragmented — average team uses 6+ disconnected platforms",
                    f"$12.3B lost annually to {topic.lower()} inefficiency (Gartner 2024)",
                    "Legacy solutions require 6-month implementation cycles",
                    f"Data silos prevent {audience} from making real-time decisions",
                ],
                "image_prompt": f"Frustrated professional surrounded by scattered documents and multiple screens, dim office lighting, stress visualization",
            },
            "speaker_notes": f"Let me paint you a picture. I talked to over 200 {audience} in the last year. The #1 pain? They spend more time wrestling with tools than actually doing their job. The problem isn't lack of solutions — it's that every solution creates a new silo.",
        },
        "solution": {
            "layout": "split-screen",
            "content": {
                "title": f"{company or 'Our'} Solution",
                "subtitle": "One platform. Zero friction.",
                "bullets": [
                    f"AI-powered {topic.lower()} automation — 10x faster than manual",
                    "Unified dashboard replacing 6+ fragmented tools",
                    "Real-time collaboration with role-based access",
                    "API-first architecture — connects to your existing stack in 5 minutes",
                ],
                "image_prompt": f"Clean modern SaaS dashboard interface mockup, dark theme, data visualizations, glowing UI elements, professional product screenshot style",
            },
            "speaker_notes": f"Here's what we built. {company or 'Our platform'} is the single workspace where {audience} do all their {topic.lower()} work. No more tab-switching, no more copy-paste between tools. One click to automate, one view to decide.",
        },
        "traction": {
            "layout": "kpi-dashboard",
            "content": {
                "title": "Traction",
                "kpi_metrics": [
                    {"label": "MRR", "value": "$47K", "change": "+23%", "trend": "up"},
                    {"label": "Users", "value": "2,340", "change": "+156%", "trend": "up"},
                    {"label": "NPS", "value": "72", "change": "+8", "trend": "up"},
                    {"label": "Retention", "value": "94%", "change": "+3%", "trend": "up"},
                ],
                "chart_data": {
                    "type": "line",
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    "datasets": [
                        {
                            "label": "MRR ($)",
                            "data": [12000, 18000, 24000, 31000, 39000, 47000],
                        }
                    ],
                },
            },
            "speaker_notes": "We launched 6 months ago and the numbers speak for themselves. MRR growing 23% month-over-month with zero paid acquisition. 94% retention tells us we've found product-market fit. Our NPS of 72 is in the top 1% for B2B SaaS.",
        },
        "market": {
            "layout": "chart-focus",
            "content": {
                "title": "Market Opportunity",
                "chart_data": {
                    "type": "bar",
                    "labels": ["TAM", "SAM", "SOM"],
                    "datasets": [
                        {
                            "label": "Market Size ($B)",
                            "data": [84, 12.6, 1.8],
                        }
                    ],
                },
                "bullets": [
                    "TAM: $84B global market (Grand View Research 2024)",
                    "SAM: $12.6B North America mid-market segment",
                    "SOM: $1.8B — our beachhead in 3 verticals",
                ],
                "body_text": "Bottom-up: 340K target companies × $5,280 avg annual contract = $1.8B SOM",
            },
            "speaker_notes": "Let me walk through our market sizing with a bottom-up approach. There are 340,000 companies in our target verticals with 50-500 employees. At our average contract value, that's a $1.8B serviceable obtainable market. We're not chasing the whole TAM — we're laser focused on where we win.",
        },
        "business-model": {
            "layout": "two-column",
            "content": {
                "title": "How We Make Money",
                "bullets": [
                    "Starter: $49/seat/mo — core automation",
                    "Pro: $129/seat/mo — analytics + integrations",
                    "Enterprise: Custom — SSO, SLA, dedicated support",
                ],
                "kpi_metrics": [
                    {"label": "ACV", "value": "$5,280", "change": "", "trend": "stable"},
                    {"label": "CAC", "value": "$340", "change": "-12%", "trend": "down"},
                    {"label": "LTV", "value": "$18,700", "change": "+8%", "trend": "up"},
                    {"label": "Payback", "value": "2.3 mo", "change": "-0.4", "trend": "down"},
                ],
            },
            "speaker_notes": "Our unit economics are strong and improving. LTV-to-CAC ratio of 55:1, with payback period under 3 months. This is driven by product-led growth — 62% of our customers upgrade from Starter to Pro within 60 days.",
        },
        "competition": {
            "layout": "comparison",
            "content": {
                "title": "Competitive Landscape",
                "comparison_items": [
                    {"us": "AI-native automation", "them": "Rule-based workflows"},
                    {"us": "5-min setup", "them": "6-month implementation"},
                    {"us": "Real-time collaboration", "them": "Async/email-based"},
                    {"us": "$49/seat starting", "them": "$200+ enterprise-only"},
                    {"us": "API-first (200+ integrations)", "them": "Closed ecosystem"},
                ],
            },
            "speaker_notes": "We respect our competitors — Competitor A has strong enterprise traction, Competitor B is great for SMBs. But they were built for a pre-AI world. We're the only platform that's AI-native from day one, which means we can deliver in 5 minutes what takes them 6 months to configure.",
        },
        "team": {
            "layout": "team-grid",
            "content": {
                "title": "Team",
                "team_members": [
                    {"name": "Sarah Chen", "role": "CEO", "bio": "Ex-Stripe PM, Stanford CS. Built payments infra processing $2B/year."},
                    {"name": "Marcus Williams", "role": "CTO", "bio": "Ex-Google SRE lead. Scaled systems from 0 to 100M users."},
                    {"name": "Priya Patel", "role": "VP Product", "bio": "Ex-Notion. Led product from $10M to $100M ARR."},
                    {"name": "James Kim", "role": "VP Sales", "bio": "Ex-Datadog. Closed $50M+ enterprise deals."},
                ],
            },
            "speaker_notes": "We've been fortunate to assemble a world-class team. Sarah and Marcus have been building together for 8 years. Each team member has scaled a company through the exact stage we're entering. We know what good looks like because we've done it before.",
        },
        "financials": {
            "layout": "chart-focus",
            "content": {
                "title": "Financial Projections",
                "chart_data": {
                    "type": "bar",
                    "labels": ["2024", "2025", "2026", "2027"],
                    "datasets": [
                        {"label": "Revenue ($M)", "data": [0.56, 3.2, 12.8, 38.4]},
                        {"label": "Costs ($M)", "data": [1.2, 2.8, 6.4, 15.2]},
                    ],
                },
                "kpi_metrics": [
                    {"label": "2025 ARR", "value": "$3.2M", "change": "+471%", "trend": "up"},
                    {"label": "Gross Margin", "value": "82%", "change": "+4%", "trend": "up"},
                    {"label": "Burn Rate", "value": "$180K/mo", "change": "", "trend": "stable"},
                    {"label": "Runway", "value": "18 months", "change": "", "trend": "stable"},
                ],
            },
            "speaker_notes": "Key assumptions: 15% MoM user growth (conservative vs. current 23%), 3% monthly churn (vs. current 6%), and 20% price increase at Pro tier in Q3. We hit profitability in Q2 2027 with this round.",
        },
        "ask": {
            "layout": "center-focus",
            "content": {
                "title": "$4M Seed Round",
                "subtitle": "Building the operating system for modern teams",
                "bullets": [
                    "Engineering (45%) — AI model development, platform scaling",
                    "Sales & Marketing (30%) — PLG expansion, enterprise pipeline",
                    "Operations (15%) — SOC 2, GDPR, enterprise readiness",
                    "Buffer (10%) — Strategic optionality",
                ],
                "body_text": "This round unlocks: 10K users, $3.2M ARR, Series A readiness in 18 months.",
            },
            "speaker_notes": "We're raising $4M at a $20M post-money valuation. This gives us 18 months of runway to hit the milestones that set up a strong Series A: 10,000 users, $3.2M ARR, and marquee enterprise logos. We have $2.4M committed, with room for one more strategic investor at this table.",
        },
    }

    for idx, (slide_type, label) in enumerate(YC_DECK_SLIDES[:num_slides]):
        tmpl = templates.get(slide_type, templates["title-hero"])
        slide = {
            "id": f"slide_{slide_type}_{idx}",
            "index": idx,
            "type": slide_type,
            "layout": tmpl["layout"],
            "section": label,
            "content": tmpl["content"],
            "speakerNotes": tmpl["speaker_notes"],
            "style": {
                "background": {
                    "type": "gradient" if idx == 0 else "solid",
                    "colors": ["#0F172A", "#1E293B"] if idx == 0 else None,
                    "color": "#FFFFFF" if idx > 0 else None,
                },
            },
            "quality_score": random.randint(82, 98),
        }
        slides.append(slide)

    return slides


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Slide HTML Renderer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def render_slide_html(slide: Dict[str, Any], primary: str, accent: str) -> str:
    """Render a slide as styled HTML for preview."""
    content = slide.get("content", {})
    layout = slide.get("layout", "center-focus")
    section = html.escape(str(slide.get("section", "")))
    title = html.escape(str(content.get("title", "")))
    subtitle = html.escape(str(content.get("subtitle", "")))
    bullets = content.get("bullets", [])
    kpi_metrics = content.get("kpi_metrics", [])
    chart_data = content.get("chart_data", {})
    team_members = content.get("team_members", [])
    comparison_items = content.get("comparison_items", [])
    body_text = html.escape(str(content.get("body_text", "")))
    quality = slide.get("quality_score", 0)

    # Quality badge color
    q_color = "#22C55E" if quality >= 90 else "#F59E0B" if quality >= 80 else "#EF4444"

    bg_style = slide.get("style", {}).get("background", {})
    if bg_style.get("type") == "gradient" and bg_style.get("colors"):
        bg_css = f"background: linear-gradient(135deg, {bg_style['colors'][0]}, {bg_style['colors'][1]});"
        text_color = "#FFFFFF"
    else:
        bg_css = f"background: {bg_style.get('color', '#FFFFFF')};"
        text_color = "#1E293B"

    bullets_html = ""
    if bullets:
        items = "".join(
            f'<li style="margin-bottom:8px;font-size:15px;color:{text_color}CC;">{html.escape(str(b))}</li>'
            for b in bullets
        )
        bullets_html = f'<ul style="padding-left:24px;margin-top:16px;">{items}</ul>'

    kpi_html = ""
    if kpi_metrics:
        cards = ""
        for m in kpi_metrics:
            trend_icon = "↑" if m.get("trend") == "up" else "↓" if m.get("trend") == "down" else "→"
            trend_color = "#22C55E" if m.get("trend") == "up" else "#EF4444" if m.get("trend") == "down" else "#94A3B8"
            cards += f"""
            <div style="background:{text_color}08;border:1px solid {text_color}15;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:12px;color:{text_color}80;text-transform:uppercase;letter-spacing:1px;">{html.escape(str(m.get('label','')))}</div>
                <div style="font-size:28px;font-weight:700;color:{accent};margin:8px 0;">{html.escape(str(m.get('value','')))}</div>
                <div style="font-size:13px;color:{trend_color};">{trend_icon} {html.escape(str(m.get('change','')))}</div>
            </div>"""
        kpi_html = f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:16px;">{cards}</div>'

    team_html = ""
    if team_members:
        members = ""
        for tm in team_members:
            members += f"""
            <div style="text-align:center;padding:12px;">
                <div style="width:64px;height:64px;border-radius:50%;background:{accent}30;margin:0 auto 8px;display:flex;align-items:center;justify-content:center;font-size:24px;">👤</div>
                <div style="font-weight:600;color:{text_color};font-size:14px;">{html.escape(str(tm.get('name','')))}</div>
                <div style="font-size:12px;color:{accent};font-weight:500;">{html.escape(str(tm.get('role','')))}</div>
                <div style="font-size:11px;color:{text_color}80;margin-top:4px;">{html.escape(str(tm.get('bio','')))}</div>
            </div>"""
        team_html = f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:16px;">{members}</div>'

    comparison_html = ""
    if comparison_items:
        rows = ""
        for ci in comparison_items:
            rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid {text_color}15;color:#22C55E;font-size:13px;">✓ {html.escape(str(ci.get('us','')))}</td>
                <td style="padding:8px 12px;border-bottom:1px solid {text_color}15;color:#EF4444;font-size:13px;">✗ {html.escape(str(ci.get('them','')))}</td>
            </tr>"""
        comparison_html = f"""
        <table style="width:100%;margin-top:16px;border-collapse:collapse;">
            <thead><tr>
                <th style="padding:8px 12px;text-align:left;color:{accent};font-size:12px;text-transform:uppercase;border-bottom:2px solid {accent};">Us</th>
                <th style="padding:8px 12px;text-align:left;color:{text_color}60;font-size:12px;text-transform:uppercase;border-bottom:2px solid {text_color}30;">Competitors</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>"""

    chart_html = ""
    if chart_data and chart_data.get("datasets"):
        ds = chart_data["datasets"][0]
        labels = chart_data.get("labels", [])
        values = ds.get("data", [])
        max_val = max(values) if values else 1
        bars = ""
        for lbl, val in zip(labels, values):
            pct = (val / max_val) * 100 if max_val else 0
            bars += f"""
            <div style="display:flex;align-items:center;margin-bottom:8px;">
                <div style="width:60px;font-size:12px;color:{text_color}80;">{html.escape(str(lbl))}</div>
                <div style="flex:1;height:28px;background:{text_color}08;border-radius:6px;overflow:hidden;">
                    <div style="height:100%;width:{pct}%;background:linear-gradient(90deg,{accent},{primary});border-radius:6px;display:flex;align-items:center;padding-left:8px;">
                        <span style="color:white;font-size:11px;font-weight:600;">{val}</span>
                    </div>
                </div>
            </div>"""
        chart_html = f'<div style="margin-top:16px;">{bars}</div>'

    body_html = ""
    if body_text and body_text != "None":
        body_html = f'<p style="margin-top:12px;font-size:13px;color:{text_color}90;line-height:1.6;">{body_text}</p>'

    slide_html = f"""
    <div style="{bg_css}border-radius:12px;padding:32px;aspect-ratio:16/9;display:flex;flex-direction:column;justify-content:center;position:relative;box-shadow:0 4px 24px rgba(0,0,0,0.12);overflow:hidden;">
        <div style="position:absolute;top:12px;left:16px;font-size:10px;color:{text_color}40;text-transform:uppercase;letter-spacing:1.5px;">{section}</div>
        <div style="position:absolute;top:10px;right:16px;font-size:11px;font-weight:600;color:{q_color};background:{q_color}15;padding:2px 8px;border-radius:10px;">Q: {quality}</div>
        <h2 style="color:{text_color};font-size:28px;font-weight:700;margin:0 0 8px;font-family:'DM Sans',sans-serif;">{title}</h2>
        {"<p style='color:" + text_color + "99;font-size:16px;margin:0 0 12px;font-family:Inter,sans-serif;'>" + subtitle + "</p>" if subtitle else ""}
        {bullets_html}
        {kpi_html}
        {chart_html}
        {team_html}
        {comparison_html}
        {body_html}
    </div>
    """
    return slide_html


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pipeline Animation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def show_pipeline_progress(progress_bar, status_text, stages: List[Dict]):
    """Animate the agent pipeline execution."""
    total = len(stages)
    for i, stage in enumerate(stages):
        progress = (i + 1) / total
        status_text.markdown(
            f'{stage["icon"]} **{stage["name"]}** — {stage["role"]}'
        )
        progress_bar.progress(progress)
        time.sleep(0.35)
    status_text.markdown("**Pipeline complete**")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main App
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    # ── Sidebar ──
    st.sidebar.title("Barise Presentation Engine")
    st.sidebar.caption("Testing & Preview Dashboard")

    page = st.sidebar.radio(
        "Navigate",
        [
            "Generate & Preview",
            "Agent Pipeline",
            "Skill Registry",
            "Quality Inspector",
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**System Status**")
    st.sidebar.markdown(
        f"- DSL Models: {'✅' if DSL_AVAILABLE else '❌'}"
    )
    st.sidebar.markdown(
        f"- Skill Registry: {'✅' if SKILLS_AVAILABLE else '❌'}"
    )
    st.sidebar.markdown(
        f"- Agent Protocols: {'✅' if AGENTS_AVAILABLE else '❌'}"
    )

    # ── Page: Generate & Preview ──
    if page == "Generate & Preview":
        st.title("Presentation Generator")
        st.caption("Enter your pitch details and preview generated slides")

        col1, col2 = st.columns([1, 1])

        with col1:
            topic = st.text_input("Topic / Product", value="AI-Powered Developer Tools")
            company = st.text_input("Company Name", value="CodeForge AI")
            description = st.text_area(
                "Description",
                value="An AI-native IDE extension that writes production-grade code, runs tests, and deploys — reducing development time by 10x for engineering teams.",
                height=100,
            )

        with col2:
            audience = st.selectbox(
                "Target Audience",
                ["Investors", "Enterprise Buyers", "Board of Directors", "Conference Attendees", "Customers"],
                index=0,
            )
            archetype = st.selectbox(
                "Deck Archetype",
                ["yc_seed", "series_a", "consulting", "quarterly_report", "sales", "product_launch"],
                index=0,
            )
            num_slides = st.slider("Number of Slides", 5, 10, 10)

        # Design system
        st.markdown("##### Design System")
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            primary_color = st.color_picker("Primary", "#0F172A")
        with dc2:
            accent_color = st.color_picker("Accent", "#6366F1")
        with dc3:
            bg_color = st.color_picker("Background", "#FFFFFF")

        if st.button("Generate Presentation", type="primary", use_container_width=True):
            # Pipeline animation
            st.markdown("---")
            st.subheader("Agent Pipeline Execution")
            progress_bar = st.progress(0)
            status_text = st.empty()
            show_pipeline_progress(progress_bar, status_text, AGENT_PIPELINE)

            # Generate mock slides
            slides = generate_mock_slides(topic, company, audience, archetype, num_slides)
            st.session_state["slides"] = slides
            st.session_state["gen_meta"] = {
                "topic": topic,
                "company": company,
                "audience": audience,
                "archetype": archetype,
                "primary_color": primary_color,
                "accent_color": accent_color,
                "timestamp": datetime.now().isoformat(),
            }
            st.rerun()

        # Display generated slides
        if "slides" in st.session_state:
            slides = st.session_state["slides"]
            meta = st.session_state.get("gen_meta", {})
            primary = meta.get("primary_color", "#0F172A")
            accent = meta.get("accent_color", "#6366F1")

            st.markdown("---")

            # Summary metrics
            avg_quality = sum(s.get("quality_score", 0) for s in slides) / len(slides) if slides else 0
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Slides", len(slides))
            mc2.metric("Avg Quality", f"{avg_quality:.1f}")
            mc3.metric("Archetype", meta.get("archetype", "—"))
            mc4.metric("Audience", meta.get("audience", "—"))

            st.markdown("---")
            st.subheader("Slide Preview")

            # View mode
            view_mode = st.radio(
                "View",
                ["Gallery (2-up)", "Full Width", "JSON"],
                horizontal=True,
            )

            if view_mode == "Gallery (2-up)":
                for i in range(0, len(slides), 2):
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx < len(slides):
                            with col:
                                st.markdown(
                                    render_slide_html(slides[idx], primary, accent),
                                    unsafe_allow_html=True,
                                )
                                with st.expander("Speaker Notes"):
                                    st.write(slides[idx].get("speakerNotes", ""))

            elif view_mode == "Full Width":
                for slide in slides:
                    st.markdown(
                        render_slide_html(slide, primary, accent),
                        unsafe_allow_html=True,
                    )
                    st.markdown("")
                    with st.expander(f"Speaker Notes — {slide.get('section', '')}"):
                        st.write(slide.get("speakerNotes", ""))
                    st.markdown("")

            elif view_mode == "JSON":
                for slide in slides:
                    with st.expander(
                        f"Slide {slide['index']}: {slide.get('section', '')} (Q: {slide.get('quality_score', 0)})"
                    ):
                        st.json(slide)

    # ── Page: Agent Pipeline ──
    elif page == "Agent Pipeline":
        st.title("Multi-Agent Pipeline")
        st.caption(
            "8 specialized AI agents collaborate to produce each presentation"
        )

        for i, agent in enumerate(AGENT_PIPELINE):
            with st.container():
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(
                        f"""
                        <div style="width:72px;height:72px;border-radius:16px;background:{agent['color']}15;border:2px solid {agent['color']};display:flex;align-items:center;justify-content:center;font-size:32px;margin:auto;">
                            {agent['icon']}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(f"### {agent['name']}")
                    st.markdown(f"**Model:** `{agent['model']}`")
                    st.markdown(f"**Role:** {agent['role']}")

                    # Agent-specific details
                    details = {
                        "CEO Agent": "Detects deck archetype (6 types), generates narrative arc using 4 frameworks (Problem-Solution-Proof, Situation-Complication-Resolution, Before-After-Bridge, Hero's Journey), creates detailed slide outline with CoT reasoning.",
                        "Researcher Agent": "Parallel batch research (3-5 slides/batch), confidence-calibrated citations, anti-hallucination checks (due diligence test, conservative estimates, ⚠️ verify markers).",
                        "Designer Agent": "5 anti-AI-slop visual presets, WCAG AA accessibility checking (≥4.5:1 contrast, ≥24px headings), 10 layout specifications with grid systems.",
                        "Layout Agent": "16 layout rules with grid specs, consistency scoring across slides, transition validation, responsive element positioning.",
                        "Code Agent": "Self-evolving DSL generator with 22 learnable skills, multi-provider routing (DeepSeek→DSL, Qwen→React, GLM→Reveal.js), evaluation loop (3 rounds, 85% threshold).",
                        "VFX Agent": "6 Three.js scene types (particles, globe, bar-chart, floating-cards, data-flow, scatter), performance budgets, 2D fallback generation.",
                        "Assembler Agent": "Synthesizes designer specs + researcher data into cohesive slides, content-design alignment, element positioning.",
                        "QA Agent": "6 quality gates with weighted scoring, 27-phrase corporate slop detection, cross-slide narrative coherence (6 dimensions), structural evaluation fallback.",
                    }
                    st.markdown(f"_{details.get(agent['name'], '')}_")

                if i < len(AGENT_PIPELINE) - 1:
                    st.markdown(
                        '<div style="text-align:center;color:#64748B;font-size:24px;margin:8px 0;">↓</div>',
                        unsafe_allow_html=True,
                    )

    # ── Page: Skill Registry ──
    elif page == "Skill Registry":
        st.title("Skill Registry Explorer")
        st.caption("22 learnable skill templates for DSL generation")

        # Show DSL System Prompt
        if SKILLS_AVAILABLE:
            with st.expander("DSL System Prompt (master prompt)", expanded=False):
                st.code(DSL_SYSTEM_PROMPT, language="markdown")

            st.markdown("---")
            st.subheader("Slide Type Skills")

            # Skill table
            skill_data = []
            for name, config in DEFAULT_SKILL_PROMPTS.items():
                mode = config.get("mode", "INSTANT")
                if hasattr(mode, "value"):
                    mode = mode.value
                skill_data.append(
                    {
                        "Skill": name,
                        "Mode": str(mode),
                        "Threshold": config.get("threshold", 80.0),
                    }
                )

            st.dataframe(skill_data, use_container_width=True)

            # Individual skill explorer
            selected = st.selectbox(
                "View Skill Prompt Template",
                list(DEFAULT_SKILL_PROMPTS.keys()),
            )
            if selected:
                config = DEFAULT_SKILL_PROMPTS[selected]
                st.code(config["prompt_template"], language="markdown")
        else:
            st.warning("Skill Registry not available — run from server4/ directory.")

    # ── Page: Quality Inspector ──
    elif page == "Quality Inspector":
        st.title("Quality Inspector")
        st.caption("Analyze generated slides for quality issues")

        if "slides" not in st.session_state:
            st.info("Generate a presentation first to inspect quality.")
            return

        slides = st.session_state["slides"]

        # Quality overview
        st.subheader("Quality Score Distribution")
        scores = [s.get("quality_score", 0) for s in slides]
        avg = sum(scores) / len(scores) if scores else 0
        min_s = min(scores) if scores else 0
        max_s = max(scores) if scores else 0

        qc1, qc2, qc3 = st.columns(3)
        qc1.metric("Average", f"{avg:.1f}")
        qc2.metric("Min", min_s)
        qc3.metric("Max", max_s)

        # Per-slide quality breakdown
        st.markdown("---")
        st.subheader("Per-Slide Analysis")

        SLOP_PHRASES = [
            "in today's world", "game-changing", "leverage", "synergy",
            "paradigm shift", "cutting-edge", "revolutionary", "move the needle",
            "think outside the box", "circle back", "deep dive", "low-hanging fruit",
            "at the end of the day", "it goes without saying", "take it to the next level",
            "best-in-class", "world-class", "next-generation", "state-of-the-art",
            "seamlessly", "holistic approach", "disruptive innovation",
            "unlock the potential", "empower", "robust solution",
            "scalable platform", "end-to-end",
        ]

        for slide in slides:
            quality = slide.get("quality_score", 0)
            q_color = "green" if quality >= 90 else "orange" if quality >= 80 else "red"
            section = slide.get("section", f"Slide {slide['index']}")

            with st.expander(
                f":{q_color}[Q:{quality}] {section} — {slide['layout']}"
            ):
                # Content analysis
                content = slide.get("content", {})
                title = content.get("title", "")
                bullets = content.get("bullets", [])
                notes = slide.get("speakerNotes", "")

                # Checks
                checks = []

                # Title length
                word_count = len(title.split())
                if word_count <= 8:
                    checks.append(("Title Length", f"{word_count} words", True))
                else:
                    checks.append(("Title Length", f"{word_count} words (max 8)", False))

                # Bullet count
                if bullets:
                    if 3 <= len(bullets) <= 7:
                        checks.append(("Bullet Count", f"{len(bullets)} items", True))
                    else:
                        checks.append(("Bullet Count", f"{len(bullets)} items (3-7 recommended)", False))

                # Speaker notes
                if notes and len(notes) > 20:
                    checks.append(("Speaker Notes", f"{len(notes)} chars", True))
                else:
                    checks.append(("Speaker Notes", "Missing or too short", False))

                # Slop detection
                all_text = (
                    title + " " + " ".join(bullets) + " " + (notes or "")
                ).lower()
                found_slop = [p for p in SLOP_PHRASES if p in all_text]
                if found_slop:
                    checks.append(("AI Slop", f"Found: {', '.join(found_slop)}", False))
                else:
                    checks.append(("AI Slop", "Clean", True))

                # Display checks
                for check_name, detail, passed in checks:
                    icon = "✅" if passed else "⚠️"
                    st.markdown(f"{icon} **{check_name}**: {detail}")

                # Show content preview
                st.markdown("**Content:**")
                st.json(content)


if __name__ == "__main__":
    main()
