"""
Streamlit Dashboard for New Slide Generation Pipeline
Run: streamlit run test_slides_new.py
"""

import asyncio
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="Barise - New Slide Generation",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Barise - New Slide Generation Pipeline")
st.markdown("---")

# Sidebar
st.sidebar.header("Configuration")

topic = st.sidebar.text_input("Topic", value="AI SaaS Product")
description = st.sidebar.text_area(
    "Description", value="A pitch deck for an AI-powered SaaS product"
)
purpose = st.sidebar.selectbox(
    "Purpose", ["seed_funding", "series_a", "sales", "consulting", "investor_update"]
)
audience = st.sidebar.selectbox(
    "Audience", ["investors", "clients", "team", "partners"]
)
slide_count = st.sidebar.slider("Slide Count", 3, 12, 6)
writing_style = st.sidebar.selectbox(
    "Writing Style",
    ["general", "yc_pitch", "analytical", "consulting", "sales", "marketing"],
)

st.sidebar.markdown("---")
st.sidebar.header("Model Info")
st.sidebar.info("**CEO:** kimi-k2-thinking")
st.sidebar.info("**Researcher:** gpt-4o-mini")
st.sidebar.info("**Designer:** deepseek-v3")
st.sidebar.info("**Assembler:** deepseek-v3")
st.sidebar.info("**QA:** gpt-4o-mini")

# Generate button
if st.button("Generate Presentation", type="primary"):
    st.markdown("---")
    st.subheader("Generation Progress")

    progress_bar = st.progress(0)
    status_text = st.empty()

    async def generate():
        from app.database import connect_db
        from app.services.slides_new.orchestrator.pipeline import PipelineOrchestrator

        # Connect
        status_text.text("Connecting to database...")
        progress_bar.progress(5)
        db = await connect_db()

        # Generate
        status_text.text("Creating presentation...")
        progress_bar.progress(10)
        orchestrator = PipelineOrchestrator(db)

        result = await orchestrator.generate_presentation(
            topic=topic,
            description=description,
            purpose=purpose,
            audience=audience,
            slide_count=slide_count,
            writing_style=writing_style,
        )

        progress_bar.progress(100)

        if result.get("success"):
            status_text.text("Generation Complete!")
            return result
        else:
            status_text.text(f"Error: {result.get('error')}")
            return None

    # Run
    result = asyncio.run(generate())

    if result and result.get("success"):
        st.success(f"Success! Quality Score: {result.get('quality_score')}%")

        pres = result.get("presentation", {})
        metadata = pres.get("metadata", {})

        col1, col2, col3 = st.columns(3)
        col1.metric("Slides", metadata.get("slide_count"))
        col2.metric("Quality Score", f"{result.get('quality_score')}%")
        col3.metric("Quality Passed", "Yes" if result.get("quality_passed") else "No")

        st.markdown("---")
        st.subheader("Slide Preview")

        slides = pres.get("slides", [])
        for i, slide in enumerate(slides):
            with st.expander(f"Slide {i + 1}: {slide.get('title', 'Untitled')}"):
                st.write(f"**Layout:** {slide.get('layout')}")
                st.write(f"**Purpose:** {slide.get('purpose')}")

                content = slide.get("content", {})
                if content.get("bullets"):
                    st.write("**Content:**")
                    for bullet in content.get("bullets", []):
                        st.write(f"- {bullet}")

                design = slide.get("design", {})
                st.write("**Design:**", design)
    else:
        st.error(
            f"Generation failed: {result.get('error') if result else 'Unknown error'}"
        )

# Info
st.markdown("---")
st.markdown("""
**Pipeline Flow:**
1. **CEO Agent** (kimi-k2-thinking) - Strategy & Structure
2. **Researcher Agent** (gpt-4o-mini) - Content Research
3. **Designer Agent** (deepseek-v3) - Visual Design
4. **Assembler Agent** (deepseek-v3) - Content Assembly
5. **QA Agent** (gpt-4o-mini) - Quality Assurance
""")
