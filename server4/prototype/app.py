"""
Meridian V9 — Cognitive Design Intelligence Engine
Investor Prototype · Streamlit Application
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from llm_router import LLMRouter
from slide_engine import CDIPipeline, render_slide_html

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Meridian V9 — Slide Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    /* Global overrides for dark premium feel */
    .stApp { background-color: #0a0a0f !important; }
    [data-testid="stSidebar"] { background-color: #0f1420 !important; border-right: 1px solid #1e293b; }
    [data-testid="stSidebar"] .stMarkdown h3 { color: #8b5cf6 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px; border-radius: 8px 8px 0 0;
        background: #1e293b; color: #94a3b8; font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background: #8b5cf620 !important; color: #8b5cf6 !important;
        border-bottom: 2px solid #8b5cf6;
    }
    div[data-testid="stMetric"] {
        background: #1e293b; border-radius: 12px; padding: 12px 16px;
        border: 1px solid #334155;
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 12px !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #e2e8f0 !important; font-size: 20px !important; }
    .provider-badge {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        font-size: 12px; font-weight: 600; margin-bottom: 6px;
    }
    .provider-free { background: #10b98120; color: #34d399; border: 1px solid #10b98140; }
    .provider-paid { background: #3b82f620; color: #60a5fa; border: 1px solid #3b82f640; }
    .pipeline-stage {
        text-align: center; padding: 10px 6px; border-radius: 10px;
        transition: all 0.3s ease;
    }
    .stage-pending { background: #1e293b; border: 1px solid #334155; }
    .stage-running { background: #1e3a5f; border: 1px solid #3b82f6; animation: pulse 1.5s infinite; }
    .stage-complete { background: #052e16; border: 1px solid #10b981; }
    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.7; } }
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────
if "router" not in st.session_state:
    st.session_state.router = LLMRouter()
if "presentation" not in st.session_state:
    st.session_state.presentation = None
if "quick_topic" not in st.session_state:
    st.session_state.quick_topic = ""

router: LLMRouter = st.session_state.router

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:8px 0 4px;">
        <span style="font-size:28px;">⚡</span><br>
        <span style="font-size:22px;font-weight:800;background:linear-gradient(135deg,#8b5cf6,#3b82f6);
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;">Meridian V9</span><br>
        <span style="font-size:12px;color:#64748b;">Cognitive Design Intelligence</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Mode selection
    mode_label = st.radio(
        "**Generation Mode**",
        ["🆓  Standard (FREE)", "💎  Premium (Azure)"],
        index=0,
        help="Standard uses free models (Groq, Cloudflare). Premium uses Azure paid models.",
    )
    mode_key = "standard" if "Standard" in mode_label else "premium"

    st.divider()

    # Provider health
    st.markdown("### 📡 Available Providers")
    providers = router.get_providers(mode_key)
    if providers:
        for p in providers:
            tier_class = "provider-free" if p["tier"] == "FREE" else "provider-paid"
            st.markdown(
                f'<span class="provider-badge {tier_class}">{p["tier"]}</span> '
                f'**{p["name"]}** — `{p["model"]}`  \n'
                f'<span style="font-size:11px;color:#64748b;">{p.get("detail", "")}</span>',
                unsafe_allow_html=True,
            )
    else:
        st.warning("No providers configured. Demo mode will be used.")

    st.divider()

    # Cost tracker
    st.markdown("### 💰 Session Metrics")
    c1, c2 = st.columns(2)
    c1.metric("Cost", f"${router.total_cost:.4f}")
    c2.metric("API Calls", router.total_calls)

    st.divider()

    # Quick topics
    st.markdown("### 🎯 Quick Topics")
    quick_topics = [
        "AI-Powered Healthcare Platform",
        "FinTech Payment Revolution",
        "SaaS Productivity Suite",
        "Climate Tech Carbon Trading",
        "EdTech Personalized Learning",
        "Autonomous Delivery Drones",
    ]
    for t in quick_topics:
        if st.button(t, key=f"qt_{hash(t)}", use_container_width=True):
            st.session_state.quick_topic = t
            st.rerun()

# ── Main Content ─────────────────────────────────────────────

# Header
st.markdown("""
<div style="text-align:center;padding:16px 0 8px;">
    <h1 style="font-size:34px;font-weight:800;margin:0;
      background:linear-gradient(135deg,#8b5cf6,#3b82f6,#06b6d4);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        🎯 Cognitive Design Intelligence Engine
    </h1>
    <p style="color:#64748b;font-size:15px;margin-top:4px;">
        Generate investor-grade presentations with a 6-layer AI pipeline
    </p>
</div>
""", unsafe_allow_html=True)

# Topic input
default_topic = st.session_state.quick_topic
topic = st.text_input(
    "📝 Presentation Topic",
    value=default_topic,
    placeholder="e.g., AI-Powered Healthcare Platform for Emerging Markets",
    label_visibility="collapsed",
)

# Controls row
col_btn, col_slides, col_mode_info = st.columns([3, 1, 2])
with col_btn:
    generate = st.button("🚀  Generate Presentation", type="primary", use_container_width=True)
with col_slides:
    num_slides = st.selectbox("Slides", [6, 8, 10], index=1, label_visibility="collapsed")
with col_mode_info:
    mode_icon = "🆓" if mode_key == "standard" else "💎"
    mode_desc = "FREE models" if mode_key == "standard" else "Azure paid models"
    st.markdown(
        f'<div style="padding:8px 12px;background:#1e293b;border-radius:8px;text-align:center;">'
        f'<span style="font-size:13px;color:#94a3b8;">{mode_icon} {mode_desc}</span></div>',
        unsafe_allow_html=True,
    )

# ── Generation Pipeline ─────────────────────────────────────
if generate and topic.strip():
    st.session_state.quick_topic = ""
    pipeline = CDIPipeline(router)

    st.markdown("---")
    st.markdown(
        '<div style="font-size:18px;font-weight:700;color:#e2e8f0;margin-bottom:12px;">'
        '⚙️ 6-Layer CDI Pipeline</div>',
        unsafe_allow_html=True,
    )

    # Create 6 pipeline status columns
    stage_names = [
        "Narrative", "Content", "Spatial",
        "Visual", "Compose", "QA",
    ]
    stage_cols = st.columns(6)
    stage_slots = []
    for i, col in enumerate(stage_cols):
        with col:
            slot = st.empty()
            slot.markdown(
                f'<div class="pipeline-stage stage-pending">'
                f'<div style="font-size:11px;color:#64748b;">Layer {i+1}</div>'
                f'<div style="font-size:18px;margin:4px 0;">⏳</div>'
                f'<div style="font-size:10px;color:#475569;">{stage_names[i]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            stage_slots.append(slot)

    # Live progress callback
    def on_stage_update(stages):
        for i, stg in enumerate(stages):
            if stg.status == "running":
                stage_slots[i].markdown(
                    f'<div class="pipeline-stage stage-running">'
                    f'<div style="font-size:11px;color:#60a5fa;">Layer {i+1}</div>'
                    f'<div style="font-size:18px;margin:4px 0;">🔄</div>'
                    f'<div style="font-size:10px;color:#93c5fd;">{stg.detail[:35]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            elif stg.status == "complete":
                stage_slots[i].markdown(
                    f'<div class="pipeline-stage stage-complete">'
                    f'<div style="font-size:11px;color:#34d399;">Layer {i+1} ✓</div>'
                    f'<div style="font-size:18px;margin:4px 0;">✅</div>'
                    f'<div style="font-size:10px;color:#6ee7b7;">{stg.duration:.1f}s</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # Run the pipeline
    with st.spinner(""):
        pres = pipeline.generate(
            topic=topic.strip(),
            mode=mode_key,
            num_slides=num_slides,
            on_stage_update=on_stage_update,
        )
    st.session_state.presentation = pres

    # Summary metrics
    st.markdown("")
    m1, m2, m3, m4 = st.columns(4)
    avg_q = sum(s.quality_score for s in pres.slides) / max(len(pres.slides), 1)
    m1.metric("⏱️ Total Time", f"{pres.total_time:.1f}s")
    m2.metric("💰 Total Cost", f"${pres.total_cost:.4f}")
    m3.metric("🤖 Provider", pres.model_used[:28])
    m4.metric("📊 Avg Quality", f"{avg_q:.0f}/100")

    st.success(f"✅ Generated **{len(pres.slides)} slides** for *\"{pres.title}\"* in {pres.total_time:.1f}s")

# ── Display Presentation ────────────────────────────────────
pres = st.session_state.presentation

if pres and pres.slides:
    st.markdown("---")
    st.markdown(
        f'<div style="font-size:22px;font-weight:700;color:#e2e8f0;margin-bottom:4px;">'
        f'🎬 {pres.title}</div>'
        f'<div style="font-size:13px;color:#64748b;margin-bottom:12px;">'
        f'{len(pres.slides)} slides · {pres.narrative_arc.get("archetype", "custom")} arc '
        f'· theme: {pres.theme.get("mood", "custom")}</div>',
        unsafe_allow_html=True,
    )

    # Narrative arc visualization
    with st.expander("📈 Narrative Arc", expanded=False):
        arc_df = pd.DataFrame({
            "Emotional Intensity": [s.emotional_intensity for s in pres.slides],
        }, index=[f"{s.number}. {s.narrative_role}" for s in pres.slides])
        st.area_chart(arc_df, color="#8b5cf6", height=200)

    # Slide tabs
    tab_labels = []
    for s in pres.slides:
        label = s.title[:22] + "…" if len(s.title) > 22 else s.title
        tab_labels.append(f"{s.number}. {label}")

    tabs = st.tabs(tab_labels)

    for tab, slide in zip(tabs, pres.slides):
        with tab:
            # Render slide HTML
            html = render_slide_html(slide, pres.theme, slide.number, len(pres.slides))
            components.html(html, height=580, scrolling=False)

            # Slide metadata
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.markdown(f"**Type:** `{slide.type}`")
            mc2.markdown(f"**Role:** `{slide.narrative_role}`")
            mc3.markdown(f"**Layout:** `{slide.layout}`")
            mc4.markdown(f"**Intensity:** `{slide.emotional_intensity:.1f}`")

            quality_color = "#10b981" if slide.quality_score >= 80 else "#f59e0b" if slide.quality_score >= 60 else "#ef4444"
            mc5.markdown(
                f'**Quality:** <span style="color:{quality_color};font-weight:700;">'
                f'{slide.quality_score:.0f}/100</span>',
                unsafe_allow_html=True,
            )

    # Pipeline execution log
    with st.expander("📋 Pipeline Execution Log", expanded=False):
        if pres.stages:
            for stg in pres.stages:
                icon = "✅" if stg.status == "complete" else "❌"
                st.markdown(
                    f"{icon} **Layer {stg.layer}: {stg.name}** — "
                    f"{stg.duration:.2f}s — {stg.detail}"
                )
        if router.call_log:
            st.markdown("---")
            st.markdown("**API Calls:**")
            for call in router.call_log:
                status = "✅" if call.success else "❌"
                st.markdown(
                    f"{status} **{call.provider}** (`{call.model}`) — "
                    f"{call.latency:.2f}s — ${call.cost:.4f}"
                    + (f" — ⚠️ {call.error[:60]}" if call.error else "")
                )

elif pres is None:
    # Welcome state
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#475569;">
        <div style="font-size:48px;margin-bottom:16px;">🎯</div>
        <p style="font-size:18px;font-weight:600;color:#94a3b8;">Enter a topic and click Generate</p>
        <p style="font-size:14px;color:#64748b;max-width:500px;margin:8px auto;">
            The 6-layer CDI pipeline will create a complete investor-grade
            presentation using AI models — in seconds, at near-zero cost.
        </p>
        <div style="display:flex;gap:12px;justify-content:center;margin-top:24px;">
            <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px 16px;font-size:12px;">
                <span style="color:#10b981;">●</span> Standard: $0.00/deck
            </div>
            <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px 16px;font-size:12px;">
                <span style="color:#3b82f6;">●</span> Premium: ~$0.002/deck
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#334155;font-size:12px;padding:4px 0;">'
    'Meridian V9 · Cognitive Design Intelligence · Barise Platform · Prototype'
    '</div>',
    unsafe_allow_html=True,
)
