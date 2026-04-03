# Premium Slide Generation — Complete New Implementation Plan
## Complete Rebuild of Slide Generation System

**Document Version**: 1.0 (Complete Rebuild)
**Created**: 2026-04-02
**Status**: Ready for Implementation

---

## Executive Summary

This plan outlines a **complete rebuild** of the slide generation system. The current Server4 generates slides but they don't meet quality/design expectations. This implementation creates a new architecture from the ground up that produces accurate, professionally designed slides.

**Key Change**: Not patching the existing system — building entirely new slide generation with:
- New 6-Agent orchestration
- New template accuracy system  
- New design intelligence
- New quality gates
- New PreTeXt layout validation

---

## Table of Contents

1. Current Problem Analysis
2. New Architecture Overview
3. Implementation Components
4. Phase 1: Foundation (Week 1-2)
5. Phase 2: Agent System (Week 3-4)
6. Phase 3: Template System (Week 5-6)
7. Phase 4: Design Intelligence (Week 7-8)
8. Phase 5: Quality & Validation (Week 9-10)
9. Phase 6: Integration & Testing (Week 11-12)
10. Code Structure (New Files)
11. Migration Strategy

---

## 1. Current Problem Analysis

### Why Current Slides Don't Work

| Issue | Root Cause | Impact |
|-------|------------|--------|
| **Content not accurate** | Single-pass LLM generation without domain rules | Fluff words, generic content |
| **Design not professional** | Basic theme application, no layout intelligence | Generic-looking slides |
| **Text overflow** | No text measurement, auto-fit | Text cuts off, bad readability |
| **No structure** | No pitch deck domain rules | Missing YC/Sequoia structure |
| **No quality control** | No quality gates or validation | Inconsistent output |
| **Template mismatch** | Basic placeholder resolution | Wrong layout for content type |

### What We Keep from Server4

- ✅ FastAPI infrastructure
- ✅ LLM clients (Azure, Cloudflare, Groq, OpenRouter)
- ✅ Model Router (for LLM calls)
- ✅ MongoDB/Redis connections
- ✅ PPTX/HTML/PDF builders (will enhance)
- ✅ WebSocket progress

---

## 2. New Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NEW SLIDE GENERATION ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐          │
│   │   Input      │ ->  │   Agents     │ ->  │   Output     │          │
│   │   Processing │     │   Pipeline   │     │   Generation │          │
│   └──────────────┘     └──────────────┘     └──────────────┘          │
│          │                    │                    │                 │
│          v                    v                    v                 │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│   │  Validation  │     │  Quality     │     │   Export     │        │
│   │  & Context   │     │  Gates       │     │   Pipeline   │        │
│   └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### New Components

| Component | Purpose | Replacement For |
|-----------|----------|-----------------|
| **AgentOrchestrator** | Coordinate 6 agents | Simple orchestrator.py |
| **CEOAgent** | Strategy & structure | Basic outline generation |
| **ResearcherAgent** | Content research | Basic content generation |
| **DesignerAgent** | Visual design | Theme application |
| **AssemblerAgent** | PPTX building | Basic pptx_builder |
| **QAAgent** | Quality validation | No current equivalent |
| **TemplateEngine** | Accurate templates | Current template system |
| **PreTextValidator** | Layout validation | No current equivalent |

---

## 3. Implementation Components

### New File Structure

```
app/services/slides_new/
├── __init__.py
├── orchestrator.py           # Main slide generation coordinator
├── agents/
│   ├── __init__.py
│   ├── base.py               # Base agent class
│   ├── ceo_agent.py         # Strategy & outline
│   ├── researcher_agent.py  # Content research
│   ├── designer_agent.py    # Visual design
│   ├── assembler_agent.py   # PPTX assembly
│   └── qa_agent.py           # Quality validation
├── templates/
│   ├── __init__.py
│   ├── engine.py             # Template accuracy engine
│   ├── resolver.py           # Placeholder resolution
│   ├── mapper.py             # Layout mapping
│   └── registry.py           # Template management
├── design/
│   ├── __init__.py
│   ├── style_discovery.py    # Visual style previews
│   ├── anti_ai_slop.py       # Design presets
│   └── color_system.py       # Color palette management
├── quality/
│   ├── __init__.py
│   ├── gates.py              # Quality validation
│   ├── reflective_loop.py   # Iteration system
│   └── validators.py         # Content/design validators
├── layout/
│   ├── __init__.py
│   └── pretext_validator.py # PreTeXt integration
└── router.py                  # Slide-specific routing
```

---

## 4. Phase 1: Foundation (Week 1-2)

### 4.1 Create New Slide Orchestrator

```python
# app/services/slides_new/orchestrator.py

"""
New Slide Generation Orchestrator
Replaces the old orchestrator with 6-agent pipeline.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import asyncio
import structlog

from app.services.slides_new.agents import (
    CEOAgent,
    ResearcherAgent, 
    DesignerAgent,
    AssemblerAgent,
    QAAgent
)
from app.services.slides_new.templates.engine import TemplateEngine
from app.services.slides_new.quality.reflective_loop import ReflectiveLoop

logger = structlog.get_logger()


class PresentationMode(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class SlideGenerationInput:
    """Input for new slide generation"""
    topic: str
    description: str
    purpose: str  # fundraising, sales, internal, etc.
    audience: str
    slide_count: int
    mode: PresentationMode
    writing_style: str = "general"
    selected_style_preset: Optional[str] = None
    company_name: Optional[str] = None
    custom_theme: Optional[dict] = None


@dataclass
class SlideGenerationResult:
    """Output from new slide generation"""
    success: bool
    slides: List[dict]
    quality_score: int
    iterations: int
    errors: List[str] = None
    metadata: dict = None


class SlideGenerationOrchestrator:
    """
    Complete new slide generation pipeline.
    Uses 6 specialized agents with quality gates.
    """
    
    def __init__(self, db, progress_tracker):
        self.db = db
        self.progress = progress_tracker
        
        # Initialize agents
        self.ceo_agent = CEOAgent(db)
        self.researcher_agent = ResearcherAgent(db)
        self.designer_agent = DesignerAgent(db)
        self.assembler_agent = AssemblerAgent(db)
        self.qa_agent = QAAgent(db)
        
        # Initialize supporting systems
        self.template_engine = TemplateEngine(db)
        self.reflective_loop = ReflectiveLoop()
        
        # Model router (from existing code)
        from app.services.llm import ModelRouter
        self.router = ModelRouter.get_instance()
    
    async def generate_slides(
        self,
        input_data: SlideGenerationInput,
        user_id: str
    ) -> SlideGenerationResult:
        """
        Complete new slide generation pipeline.
        """
        try:
            # Phase 1: Strategy & Outline (CEO Agent)
            logger.info("slide_gen_starting", topic=input_data.topic)
            await self.progress.update(5, "Creating presentation strategy...")
            
            strategy_result = await self.ceo_agent.execute(
                topic=input_data.topic,
                description=input_data.description,
                purpose=input_data.purpose,
                audience=input_data.audience,
                slide_count=input_data.slide_count,
                mode=input_data.mode.value
            )
            
            if not strategy_result.success:
                return SlideGenerationResult(
                    success=False,
                    slides=[],
                    quality_score=0,
                    iterations=0,
                    errors=strategy_result.errors
                )
            
            await self.progress.update(20, "Researching content...")
            
            # Phase 2: Research (Researcher Agent)
            research_result = await self.researcher_agent.execute(
                strategy=strategy_result.output,
                topic=input_data.topic
            )
            
            await self.progress.update(35, "Designing visual style...")
            
            # Phase 3: Design (Designer Agent)
            design_result = await self.designer_agent.execute(
                strategy=strategy_result.output,
                selected_preset=input_data.selected_style_preset,
                custom_theme=input_data.custom_theme
            )
            
            # If no preset selected, get previews for user
            if design_result.output.get("awaiting_selection"):
                return SlideGenerationResult(
                    success=False,
                    slides=[],
                    quality_score=0,
                    iterations=0,
                    errors=["Style selection required"],
                    metadata={
                        "style_previews": design_result.output["style_previews"],
                        "needs_style_selection": True
                    }
                )
            
            await self.progress.update(50, "Assembling slides...")
            
            # Phase 4: Assembly (Assembler Agent)
            assembly_result = await self.assembler_agent.execute(
                strategy=strategy_result.output,
                research=research_result.output,
                design=design_result.output
            )
            
            await self.progress.update(70, "Validating quality...")
            
            # Phase 5: Quality Check (QA Agent) with Reflective Loop
            final_result = await self.reflective_loop.execute(
                slides=assembly_result.output,
                strategy=strategy_result.output,
                max_iterations=3,
                quality_threshold=85,
                orchestrator=self
            )
            
            await self.progress.update(100, "Complete!")
            
            logger.info(
                "slide_gen_complete",
                quality_score=final_result.quality_score,
                iterations=final_result.iterations
            )
            
            return SlideGenerationResult(
                success=True,
                slides=final_result.slides,
                quality_score=final_result.quality_score,
                iterations=final_result.iterations,
                metadata={
                    "strategy": strategy_result.output,
                    "design": design_result.output
                }
            )
            
        except Exception as e:
            logger.error("slide_gen_failed", error=str(e))
            return SlideGenerationResult(
                success=False,
                slides=[],
                quality_score=0,
                iterations=0,
                errors=[str(e)]
            )
```

### 4.2 Base Agent Class

```python
# app/services/slides_new/agents/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import structlog

logger = structlog.get_logger()


class AgentType(str, Enum):
    CEO = "ceo"
    RESEARCHER = "researcher"
    DESIGNER = "designer"
    ASSEMBLER = "assembler"
    QA = "qa"


@dataclass
class AgentOutput:
    """Standard output format for all agents"""
    success: bool
    agent_type: AgentType
    output: Dict[str, Any]
    errors: List[str] = None
    model_used: str = None
    tokens_used: int = 0
    latency_ms: int = 0


class BaseAgent(ABC):
    """
    Base class for all slide generation agents.
    Provides common LLM calling, error handling, and logging.
    """
    
    def __init__(self, db):
        self.db = db
        from app.services.llm import ModelRouter, TaskType
        self.router = ModelRouter.get_instance()
        self.TaskType = TaskType
    
    async def call_llm(
        self,
        task_type: TaskType,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None
    ) -> AgentOutput:
        """Make LLM call with proper error handling."""
        
        import time
        start = time.monotonic()
        
        try:
            response = await self.router.complete(
                task_type=task_type,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            
            latency = int((time.monotonic() - start) * 1000)
            
            return AgentOutput(
                success=True,
                agent_type=self.get_agent_type(),
                output={"content": response.content},
                model_used=response.model,
                tokens_used=response.tokens_used,
                latency_ms=latency
            )
            
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            logger.error(
                "agent_llm_error",
                agent=self.get_agent_type(),
                error=str(e),
                latency_ms=latency
            )
            
            return AgentOutput(
                success=False,
                agent_type=self.get_agent_type(),
                output={},
                errors=[str(e)],
                latency_ms=latency
            )
    
    @abstractmethod
    def get_agent_type(self) -> AgentType:
        """Return the type of this agent"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> AgentOutput:
        """Execute the agent's main logic"""
        pass
```

---

## 5. Phase 2: Agent System (Week 3-4)

### 5.1 CEO Agent - Strategy & Structure

```python
# app/services/slides_new/agents/ceo_agent.py

"""
CEO Agent - Creates presentation strategy and structure.
Determines archetype, creates outline, defines narrative arc.
"""

from .base import BaseAgent, AgentOutput, AgentType
from app.services.llm import TaskType
import json


class CEOAgent(BaseAgent):
    """
    Agent 1: Strategic planning for presentations.
    Determines presentation archetype and creates structured outline.
    """
    
    # YC/Sequoia pitch deck structures
    ARCHETYPE_TEMPLATES = {
        "yc_seed": {
            "slides": 10,
            "structure": [
                {"index": 0, "layout": "title-hero", "purpose": "One-liner"},
                {"index": 1, "layout": "two-column", "purpose": "Problem"},
                {"index": 2, "layout": "bullets", "purpose": "Solution"},
                {"index": 3, "layout": "bullets", "purpose": "Why Now"},
                {"index": 4, "layout": "chart", "purpose": "Market"},
                {"index": 5, "layout": "bullets", "purpose": "Product"},
                {"index": 6, "layout": "bullets", "purpose": "Business Model"},
                {"index": 7, "layout": "chart", "purpose": "Traction"},
                {"index": 8, "layout": "team-grid", "purpose": "Team"},
                {"index": 9, "layout": "two-column", "purpose": "Ask"}
            ]
        },
        "series_a": {
            "slides": 12,
            "structure": [  # Add Company Purpose and Financials
                {"index": 0, "layout": "title-hero", "purpose": "Company Purpose"},
                {"index": 1, "layout": "two-column", "purpose": "Problem"},
                {"index": 2, "layout": "bullets", "purpose": "Solution"},
                {"index": 3, "layout": "bullets", "purpose": "Why Now"},
                {"index": 4, "layout": "chart", "purpose": "Market"},
                {"index": 5, "layout": "bullets", "purpose": "Product"},
                {"index": 6, "layout": "bullets", "purpose": "Business Model"},
                {"index": 7, "layout": "chart", "purpose": "Traction"},
                {"index": 8, "layout": "comparison", "purpose": "Competition"},
                {"index": 9, "layout": "team-grid", "purpose": "Team"},
                {"index": 10, "layout": "kpi-dashboard", "purpose": "Financials"},
                {"index": 11, "layout": "two-column", "purpose": "Ask"}
            ]
        },
        "consulting": {
            "slides": 15,
            "structure": [  # More detailed structure
                {"index": 0, "layout": "title-hero", "purpose": "Title"},
                {"index": 1, "layout": "bullets", "purpose": "Executive Summary"},
                {"index": 2, "layout": "two-column", "purpose": "Current State"},
                {"index": 3, "layout": "chart", "purpose": "Analysis"},
                {"index": 4, "layout": "bullets", "purpose": "Opportunity"},
                {"index": 5, "layout": "two-column", "purpose": "Recommendation"},
                {"index": 6, "layout": "timeline", "purpose": "Roadmap"},
                {"index": 7, "layout": "chart", "purpose": "Impact"},
                {"index": 8, "layout": "comparison", "purpose": "Alternatives"},
                {"index": 9, "layout": "kpi-dashboard", "purpose": "Metrics"},
                {"index": 10, "layout": "bullets", "purpose": "Risks"},
                {"index": 11, "layout": "team-grid", "purpose": "Team"},
                {"index": 12, "layout": "chart", "purpose": "Investment"},
                {"index": 13, "layout": "bullets", "purpose": "Next Steps"},
                {"index": 14, "layout": "title-hero", "purpose": "Close"}
            ]
        },
        "quarterly_report": {
            "slides": 10,
            "structure": [
                {"index": 0, "layout": "title-hero", "purpose": "Cover"},
                {"index": 1, "layout": "kpi-dashboard", "purpose": "Highlights"},
                {"index": 2, "layout": "chart", "purpose": "Revenue"},
                {"index": 3, "layout": "chart", "purpose": "Growth"},
                {"index": 4, "layout": "bullets", "purpose": "Wins"},
                {"index": 5, "layout": "bullets", "purpose": "Challenges"},
                {"index": 6, "layout": "chart", "purpose": "Burn Rate"},
                {"index": 7, "layout": "bullets", "purpose": "Product Updates"},
                {"index": 8, "layout": "bullets", "purpose": "Team"},
                {"index": 9, "layout": "bullets", "purpose": "Asks"}
            ]
        },
        "sales": {
            "slides": 8,
            "structure": [
                {"index": 0, "layout": "title-hero", "purpose": "Intro"},
                {"index": 1, "layout": "two-column", "purpose": "Challenge"},
                {"index": 2, "layout": "bullets", "purpose": "Solution"},
                {"index": 3, "layout": "comparison", "purpose": "Comparison"},
                {"index": 4, "layout": "kpi-dashboard", "purpose": "Results"},
                {"index": 5, "layout": "quote", "purpose": "Testimonial"},
                {"index": 6, "layout": "bullets", "purpose": "Pricing"},
                {"index": 7, "layout": "title-hero", "purpose": "CTA"}
            ]
        }
    }
    
    def get_agent_type(self) -> AgentType:
        return AgentType.CEO
    
    async def execute(
        self,
        topic: str,
        description: str,
        purpose: str,
        audience: str,
        slide_count: int,
        mode: str
    ) -> AgentOutput:
        """
        Execute CEO agent - create presentation strategy.
        """
        
        # Step 1: Determine archetype based on purpose
        archetype = self._determine_archetype(purpose, audience)
        
        # Step 2: Get template structure
        template = self.ARCHETYPE_TEMPLATES.get(
            archetype,
            self.ARCHETYPE_TEMPLATES["sales"]  # Default
        )
        
        # Step 3: Generate specific outline with AI
        outline = await self._generate_outline(
            topic=topic,
            description=description,
            archetype=archetype,
            slide_count=slide_count,
            mode=mode
        )
        
        # Step 4: Determine writing style
        writing_style = self._get_writing_style(archetype)
        
        return AgentOutput(
            success=True,
            agent_type=self.get_agent_type(),
            output={
                "archetype": archetype,
                "slide_count": len(template["structure"]),
                "structure": template["structure"],
                "outline": outline,
                "writing_style": writing_style,
                "purpose": purpose,
                "audience": audience
            }
        )
    
    def _determine_archetype(self, purpose: str, audience: str) -> str:
        """Determine presentation archetype"""
        
        purpose_lower = purpose.lower()
        audience_lower = audience.lower()
        
        if "fundrais" in purpose_lower or "pitch" in purpose_lower:
            if "seed" in audience_lower or "angel" in audience_lower:
                return "yc_seed"
            return "series_a"
        
        if "consulting" in purpose_lower or "strategy" in purpose_lower:
            return "consulting"
        
        if "report" in purpose_lower or "quarterly" in purpose_lower or "update" in purpose_lower:
            return "quarterly_report"
        
        if "sales" in purpose_lower or "demo" in purpose_lower:
            return "sales"
        
        return "sales"  # Default
    
    async def _generate_outline(
        self,
        topic: str,
        description: str,
        archetype: str,
        slide_count: int,
        mode: str
    ) -> List[dict]:
        """Generate detailed slide outline with purposes and content hints"""
        
        prompt = f"""Create a detailed outline for a {archetype} presentation on:
- Topic: {topic}
- Description: {description}
- Total slides: {slide_count}
- Mode: {mode}

For each slide provide:
1. index (0-based)
2. title (specific, not generic)
3. layout type (title-hero, two-column, bullets, chart, team-grid, comparison, kpi-dashboard, timeline, quote)
4. purpose (what this slide achieves)
5. content_hints (what content should go here)

Return as JSON array.
Example:
[
  {{"index": 0, "title": "Company Name - One-liner", "layout": "title-hero", "purpose": "Introduce company", "content_hints": "Company name, tagline, founder"}},
  {{"index": 1, "title": "The Problem", "layout": "two-column", "purpose": "Quantify pain", "content_hints": "Problem description, statistics"}}
]"""
        
        result = await self.call_llm(
            task_type=self.TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.5,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        if result.success:
            try:
                return json.loads(result.output["content"])
            except:
                pass
        
        # Fallback to template structure
        return self.ARCHETYPE_TEMPLATES.get(archetype, {}).get("structure", [])
    
    def _get_writing_style(self, archetype: str) -> str:
        """Map archetype to writing style"""
        
        style_map = {
            "yc_seed": "yc_pitch",
            "series_a": "analytical",
            "consulting": "consulting",
            "quarterly_report": "investor_update",
            "sales": "sales"
        }
        return style_map.get(archetype, "general")
```

### 5.2 Researcher Agent - Content Research

```python
# app/services/slides_new/agents/researcher_agent.py

"""
Researcher Agent - Gathers factual content for slides.
"""

from .base import BaseAgent, AgentOutput, AgentType
from app.services.llm import TaskType
import json


class ResearcherAgent(BaseAgent):
    """
    Agent 2: Research content for each slide.
    Generates factual, well-sourced content.
    """
    
    def get_agent_type(self) -> AgentType:
        return AgentType.RESEARCHER
    
    async def execute(
        self,
        strategy: dict,
        topic: str
    ) -> AgentOutput:
        """
        Research content for all slides based on strategy outline.
        """
        
        outline = strategy.get("outline", [])
        archetype = strategy.get("archetype", "sales")
        
        research_results = []
        
        for slide in outline:
            # Research each slide
            slide_research = await self._research_slide(
                slide_index=slide.get("index"),
                slide_title=slide.get("title"),
                slide_purpose=slide.get("purpose"),
                content_hints=slide.get("content_hints", ""),
                archetype=archetype,
                topic=topic
            )
            
            research_results.append(slide_research)
        
        return AgentOutput(
            success=True,
            agent_type=self.get_agent_type(),
            output={
                "research": research_results,
                "topic": topic
            }
        )
    
    async def _research_slide(
        self,
        slide_index: int,
        slide_title: str,
        slide_purpose: str,
        content_hints: str,
        archetype: str,
        topic: str
    ) -> dict:
        """Research content for a specific slide"""
        
        # Purpose-specific research prompts
        purpose_prompts = {
            "problem": f"""Research the problem/topic: {topic}
Purpose: {slide_purpose}

Provide:
1. Problem statement (2-3 sentences, specific, no jargon)
2. Quantified impact (realistic statistics with source format)
3. Who experiences this problem (specific user personas)
4. Why current solutions fail

Format as structured content.""",
            
            "solution": f"""Research solution for: {topic}
Purpose: {slide_purpose}

Provide:
1. Solution description (what it is, how it works)
2. Key features/benefits (3-5 bullet points)
3. Unique value proposition
4. Competitive advantage

Format as structured content.""",
            
            "market": f"""Research market size for: {topic}
Purpose: {slide_purpose}

Provide:
1. TAM (Total Addressable Market) - with source
2. SAM (Serviceable Available Market) - with methodology
3. SOM (Serviceable Obtainable Market) - realistic year 1
4. Market growth rate
5. Key market trends

Use bottom-up methodology. Format with realistic numbers.""",
            
            "traction": f"""Research traction metrics for: {topic}
Purpose: {slide_purpose}

Provide:
1. Key metric (MRR, users, etc.)
2. Growth rate (MoM, YoY)
3. Notable customers/partners
4. Any validation metrics

If early stage, focus on engagement metrics.""",
            
            "team": f"""Research team for: {topic}
Purpose: {slide_purpose}

For each founder/key team member provide:
1. Name and role
2. One credential proving domain expertise
3. Prior relevant experience
4. Notable achievements

Format as team grid content.""",
            
            "default": f"""Research content for slide about: {slide_title}
Purpose: {slide_purpose}
Topic: {topic}
Content hints: {content_hints}

Provide well-structured content that matches the slide purpose.
Focus on specific, factual information over generic statements."""
        }
        
        # Select appropriate prompt
        purpose_key = slide_purpose.lower().split()[0] if slide_purpose else "default"
        prompt = purpose_prompts.get(purpose_key, purpose_prompts["default"])
        
        result = await self.call_llm(
            task_type=self.TaskType.NARRATIVE_STORYTELLING,
            prompt=prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse and structure the content
        content = result.output.get("content", "")
        
        return {
            "slide_index": slide_index,
            "slide_title": slide_title,
            "slide_purpose": slide_purpose,
            "content": content,
            "quality": "high" if result.success else "fallback"
        }
```

### 5.3 Designer Agent - Visual Design

```python
# app/services/slides_new/agents/designer_agent.py

"""
Designer Agent - Applies visual design and style.
"""

from .base import BaseAgent, AgentOutput, AgentType
from app.services.llm import TaskType
import json


class DesignerAgent(BaseAgent):
    """
    Agent 3: Visual design, theme application, style discovery.
    """
    
    # Anti-AI-Slop style presets (12 curated designs)
    STYLE_PRESETS = {
        "bold-signal": {
            "name": "Bold Signal",
            "category": "dark",
            "colors": {
                "primary": "#FF6B35",
                "secondary": "#004E98",
                "accent": "#1A936F",
                "background": "#0F172A",
                "surface": "#1E293B",
                "text": "#F8FAFC",
                "text_secondary": "#94A3B8"
            },
            "fonts": {
                "heading": "Montserrat",
                "body": "DM Sans"
            },
            "character": "High contrast, dynamic, accent glows"
        },
        "electric-studio": {
            "name": "Electric Studio",
            "category": "dark",
            "colors": {
                "primary": "#7B2FF7",
                "secondary": "#C000FF",
                "accent": "#00F5FF",
                "background": "#1A1A2E",
                "surface": "#16213E",
                "text": "#FFFFFF",
                "text_secondary": "#B8B8D1"
            },
            "fonts": {
                "heading": "Space Grotesk",
                "body": "Inter"
            },
            "character": "Futuristic, tech, neon accents"
        },
        "notebook-tabs": {
            "name": "Notebook Tabs",
            "category": "light",
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#6366F1",
                "accent": "#8B5CF6",
                "background": "#FAFAFA",
                "surface": "#FFFFFF",
                "text": "#1F2937",
                "text_secondary": "#6B7280"
            },
            "fonts": {
                "heading": "Poppins",
                "body": "Inter"
            },
            "character": "Organized, clean, tab dividers"
        },
        "swiss-modern": {
            "name": "Swiss Modern",
            "category": "specialty",
            "colors": {
                "primary": "#000000",
                "secondary": "#333333",
                "accent": "#FF0000",
                "background": "#FFFFFF",
                "surface": "#F5F5F5",
                "text": "#000000",
                "text_secondary": "#666666"
            },
            "fonts": {
                "heading": "Helvetica Neue",
                "body": "Arial"
            },
            "character": "Minimal, precise, grid system"
        },
        "terminal-green": {
            "name": "Terminal Green",
            "category": "specialty",
            "colors": {
                "primary": "#22C55E",
                "secondary": "#16A34A",
                "accent": "#4ADE80",
                "background": "#0A0A0A",
                "surface": "#141414",
                "text": "#22C55E",
                "text_secondary": "#86EFAC"
            },
            "fonts": {
                "heading": "JetBrains Mono",
                "body": "JetBrains Mono"
            },
            "character": "Technical, hacker, phosphor"
        },
        "paper-ink": {
            "name": "Paper and Ink",
            "category": "specialty",
            "colors": {
                "primary": "#1C1917",
                "secondary": "#44403C",
                "accent": "#78716C",
                "background": "#FFFAF0",
                "surface": "#FFFEF8",
                "text": "#1C1917",
                "text_secondary": "#57534E"
            },
            "fonts": {
                "heading": "Merriweather",
                "body": "Source Serif Pro"
            },
            "character": "Editorial, classic, ink texture"
        }
    }
    
    def get_agent_type(self) -> AgentType:
        return AgentType.DESIGNER
    
    async def execute(
        self,
        strategy: dict,
        selected_preset: str = None,
        custom_theme: dict = None
    ) -> AgentOutput:
        """
        Apply visual design to slides.
        If no preset selected, return previews for user selection.
        """
        
        # If user already selected a preset
        if selected_preset:
            theme_config = self._apply_preset(selected_preset)
            
            # Generate layout optimization for each slide
            layout_opt = await self._optimize_layouts(
                structure=strategy.get("structure", [])
            )
            
            return AgentOutput(
                success=True,
                agent_type=self.get_agent_type(),
                output={
                    "theme_config": theme_config,
                    "layout_optimization": layout_opt,
                    "preset_used": selected_preset
                }
            )
        
        # Otherwise, generate style previews for user selection
        previews = await self._generate_style_previews(
            archetype=strategy.get("archetype", "sales")
        )
        
        return AgentOutput(
            success=True,
            agent_type=self.get_agent_type(),
            output={
                "style_previews": previews,
                "awaiting_selection": True
            }
        )
    
    async def _generate_style_previews(self, archetype: str) -> List[dict]:
        """Generate 3 style preview options"""
        
        # Select diverse presets based on archetype
        if "pitch" in archetype or "fundrais" in archetype:
            # For investor pitches, prefer dark/professional
            preset_keys = ["bold-signal", "swiss-modern", "electric-studio"]
        elif "report" in archetype or "quarterly" in archetype:
            # For reports, prefer clean/light
            preset_keys = ["notebook-tabs", "swiss-modern", "paper-ink"]
        else:
            # Default diversity
            preset_keys = list(self.STYLE_PRESETS.keys())[:3]
        
        previews = []
        for preset_id in preset_keys:
            preset = self.STYLE_PRESETS[preset_id]
            previews.append({
                "preset_id": preset_id,
                "name": preset["name"],
                "category": preset["category"],
                "character": preset["character"],
                "colors": preset["colors"],
                "preview_description": f"{preset['name']} - {preset['character']}"
            })
        
        return previews
    
    def _apply_preset(self, preset_id: str) -> dict:
        """Apply a selected style preset"""
        
        preset = self.STYLE_PRESETS.get(preset_id)
        
        if not preset:
            # Fallback to default
            preset = self.STYLE_PRESETS["bold-signal"]
            preset_id = "bold-signal"
        
        return {
            "preset_id": preset_id,
            "name": preset["name"],
            "colors": preset["colors"],
            "fonts": preset["fonts"],
            "category": preset["category"]
        }
    
    async def _optimize_layouts(self, structure: List[dict]) -> dict:
        """Optimize layout for each slide based on content"""
        
        layout_map = {
            "title-hero": {"text_align": "center", "vertical_align": "middle"},
            "two-column": {"column_count": 2, "gap": 40},
            "bullets": {"max_bullets": 6, "icon_style": "none"},
            "bullets-with-image": {"column_count": 2, "image_position": "right"},
            "chart": {"chart_type": "auto", "data_labels": True},
            "team-grid": {"columns": 3, "card_style": "photo-top"},
            "comparison": {"columns": 2, "highlight_position": "left"},
            "kpi-dashboard": {"card_count": 4, "layout": "grid"},
            "timeline": {"orientation": "horizontal", "connector": "arrow"},
            "quote": {"text_align": "center", "citation_position": "bottom"}
        }
        
        optimization = {}
        for slide in structure:
            slide_index = slide.get("index", 0)
            layout_type = slide.get("layout", "bullets")
            
            optimization[slide_index] = {
                "layout_type": layout_type,
                "settings": layout_map.get(layout_type, {}),
                "typography": self._get_typography_for_layout(layout_type)
            }
        
        return optimization
    
    def _get_typography_for_layout(self, layout: str) -> dict:
        """Get typography settings for layout"""
        
        type_map = {
            "title-hero": {"heading_size": 48, "body_size": 24},
            "two-column": {"heading_size": 32, "body_size": 18},
            "bullets": {"heading_size": 28, "body_size": 16, "bullet_indent": 30},
            "chart": {"heading_size": 28, "body_size": 14},
            "team-grid": {"heading_size": 24, "body_size": 14},
            "kpi-dashboard": {"heading_size": 36, "body_size": 48, "label_size": 14},
        }
        
        return type_map.get(layout, {"heading_size": 28, "body_size": 16})
```

### 5.4 Assembler Agent - PPTX Building

```python
# app/services/slides_new/agents/assembler_agent.py

"""
Assembler Agent - Builds the actual presentation.
"""

from .base import BaseAgent, AgentOutput, AgentType
import json


class AssemblerAgent(BaseAgent):
    """
    Agent 4: Assemble slides into presentation.
    Uses python-pptx to create actual PPTX file.
    """
    
    def get_agent_type(self) -> AgentType:
        return AgentType.ASSEMBLER
    
    async def execute(
        self,
        strategy: dict,
        research: dict,
        design: dict
    ) -> AgentOutput:
        """
        Assemble presentation from agent outputs.
        """
        
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        
        # Create presentation
        prs = Presentation()
        prs.slide_width = Inches(13.333)  # 16:9 aspect ratio
        prs.slide_height = Inches(7.5)
        
        theme = design.get("theme_config", {})
        colors = theme.get("colors", {})
        
        research_data = research.get("research", [])
        
        # Build each slide
        for slide_data in strategy.get("outline", []):
            slide_index = slide_data.get("index", 0)
            layout_type = slide_data.get("layout", "bullets")
            
            # Get research content for this slide
            slide_content = self._get_slide_content(slide_index, research_data)
            
            # Add slide
            slide = self._add_slide(
                prs=prs,
                layout_type=layout_type,
                content=slide_content,
                theme=theme,
                colors=colors
            )
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        prs.save(buffer)
        buffer.seek(0)
        
        # Save to MongoDB GridFS or local
        # For now, return structure
        
        return AgentOutput(
            success=True,
            agent_type=self.get_agent_type(),
            output={
                "slide_count": len(strategy.get("outline", [])),
                "theme": theme.get("name"),
                "presentation_data": self._generate_slide_data(
                    strategy=strategy,
                    research=research,
                    design=design
                )
            }
        )
    
    def _get_slide_content(self, slide_index: int, research_data: list) -> dict:
        """Extract content for a specific slide from research"""
        
        for research in research_data:
            if research.get("slide_index") == slide_index:
                return {
                    "title": research.get("slide_title", ""),
                    "content": research.get("content", ""),
                    "purpose": research.get("slide_purpose", "")
                }
        
        return {"title": "", "content": "", "purpose": ""}
    
    def _add_slide(self, prs, layout_type: str, content: dict, theme: dict, colors: dict):
        """Add a single slide to presentation"""
        
        # Map layout type to PPTX layout index
        layout_map = {
            "title-hero": 0,      # Title Slide
            "two-column": 1,      # Title and Content
            "bullets": 1,          # Title and Content
            "bullets-with-image": 1,
            "chart": 5,            # Title only (we'll add chart)
            "team-grid": 1,
            "comparison": 1,
            "kpi-dashboard": 1,
            "timeline": 1,
            "quote": 1
        }
        
        layout_index = layout_map.get(layout_type, 1)
        slide_layout = prs.slide_layouts[layout_index]
        slide = prs.slides.add_slide(slide_layout)
        
        # Apply theme colors
        background = colors.get("background", "#FFFFFF")
        if background.startswith("#"):
            background = background.lstrip('#')
            r = int(background[0:2], 16)
            g = int(background[2:4], 16)
            b = int(background[4:6], 16)
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = RGBColor(r, g, b)
        
        # Add title
        if slide.shapes.title:
            title_text = content.get("title", "")
            slide.shapes.title.text = title_text
            
            # Apply heading font
            title_text_frame = slide.shapes.title.text_frame
            for paragraph in title_text_frame.paragraphs:
                paragraph.font.size = Pt(32)
                paragraph.font.bold = True
                primary = colors.get("primary", "#000000")
                if primary.startswith("#"):
                    primary = primary.lstrip('#')
                    r = int(primary[0:2], 16)
                    g = int(primary[2:4], 16)
                    b = int(primary[4:6], 16)
                    paragraph.font.color.rgb = RGBColor(r, g, b)
        
        # Add content based on layout
        content_text = content.get("content", "")
        if content_text and slide.placeholders:
            # Add to content placeholder
            for placeholder in slide.placeholders:
                if placeholder.placeholder_format.type == 1:  # Body
                    placeholder.text = content_text
                    break
        
        return slide
    
    def _generate_slide_data(self, strategy: dict, research: dict, design: dict) -> list:
        """Generate structured slide data (not PPTX) for other outputs"""
        
        slides = []
        
        for slide_def in strategy.get("outline", []):
            slide_index = slide_def.get("index", 0)
            
            # Get research content
            research_content = ""
            for r in research.get("research", []):
                if r.get("slide_index") == slide_index:
                    research_content = r.get("content", "")
                    break
            
            slides.append({
                "index": slide_index,
                "title": slide_def.get("title", ""),
                "layout": slide_def.get("layout", "bullets"),
                "purpose": slide_def.get("purpose", ""),
                "content": research_content,
                "theme": design.get("theme_config", {}),
                "layout_settings": design.get("layout_optimization", {}).get(slide_index, {})
            })
        
        return slides
```

### 5.5 QA Agent - Quality Validation

```python
# app/services/slides_new/agents/qa_agent.py

"""
QA Agent - Validates presentation quality.
"""

from .base import BaseAgent, AgentOutput, AgentType
from app.services.llm import TaskType
import json


class QAAgent(BaseAgent):
    """
    Agent 6: Quality validation and gate checking.
    """
    
    # Quality rules
    CONTENT_RULES = {
        "max_bullets": 6,
        "max_words_per_bullet": 15,
        "fluff_words": ["revolutionary", "cutting-edge", "game-changing", 
                       "disruptive", "innovative", "breakthrough"],
        "min_content_length": 50,
        "require_specificity": True
    }
    
    DESIGN_RULES = {
        "min_contrast": 4.5,
        "min_font_size": 24,
        "max_text_density": 0.6
    }
    
    PITCH_DECK_RULES = {
        "require_why_now": True,
        "require_market": True,
        "require_team": True,
        "no_animations": True,
        "max_slides": 15,
        "min_slides": 8
    }
    
    def get_agent_type(self) -> AgentType:
        return AgentType.QA
    
    async def execute(
        self,
        slides: list,
        strategy: dict
    ) -> AgentOutput:
        """
        Validate presentation against quality gates.
        """
        
        archetype = strategy.get("archetype", "sales")
        
        # Run quality checks
        quality_report = {
            "archetype": archetype,
            "total_slides": len(slides),
            "issues": [],
            "warnings": [],
            "score": 100
        }
        
        # Check each slide
        for slide in slides:
            slide_issues = self._validate_slide(slide, archetype)
            quality_report["issues"].extend(slide_issues)
            quality_report["score"] -= len(slide_issues) * 5
        
        # Archetype-specific checks
        archetype_issues = self._validate_archetype(slides, archetype)
        quality_report["issues"].extend(archetype_issues)
        quality_report["score"] -= len(archetype_issues) * 10
        
        # Ensure score doesn't go below 0
        quality_report["score"] = max(0, quality_report["score"])
        
        # Determine pass/fail
        passed = quality_report["score"] >= 85
        
        return AgentOutput(
            success=True,
            agent_type=self.get_agent_type(),
            output={
                "quality_report": quality_report,
                "passed": passed,
                "score": quality_report["score"]
            }
        )
    
    def _validate_slide(self, slide: dict, archetype: str) -> list:
        """Validate a single slide"""
        
        issues = []
        
        content = slide.get("content", "")
        
        # Check content length
        if len(content) < self.CONTENT_RULES["min_content_length"]:
            issues.append({
                "slide": slide.get("index"),
                "type": "content_too_short",
                "severity": "medium",
                "message": f"Slide content too short ({len(content)} chars)"
            })
        
        # Check for fluff words
        content_lower = content.lower()
        for fluff_word in self.CONTENT_RULES["fluff_words"]:
            if fluff_word in content_lower:
                issues.append({
                    "slide": slide.get("index"),
                    "type": "fluff_word",
                    "severity": "high",
                    "message": f"Contains fluff word: '{fluff_word}'"
                })
        
        # Check bullet count (if structured)
        if "bullets" in content:
            bullet_count = content.count("\n-")
            if bullet_count > self.CONTENT_RULES["max_bullets"]:
                issues.append({
                    "slide": slide.get("index"),
                    "type": "too_many_bullets",
                    "severity": "medium",
                    "message": f"Too many bullets: {bullet_count}"
                })
        
        return issues
    
    def _validate_archetype(self, slides: list, archetype: str) -> list:
        """Validate archetype-specific requirements"""
        
        issues = []
        
        purposes = [s.get("purpose", "").lower() for s in slides]
        
        # Pitch deck requirements
        if "pitch" in archetype or "fundrais" in archetype:
            if "why now" not in " ".join(purposes):
                issues.append({
                    "type": "missing_why_now",
                    "severity": "high",
                    "message": "Investor pitch deck missing 'Why Now' slide"
                })
            
            if "market" not in " ".join(purposes):
                issues.append({
                    "type": "missing_market",
                    "severity": "high",
                    "message": "Investor pitch deck missing market size slide"
                })
            
            if "team" not in " ".join(purposes):
                issues.append({
                    "type": "missing_team",
                    "severity": "medium",
                    "message": "Investor pitch deck missing team slide"
                })
        
        # Check slide count
        if len(slides) > self.PITCH_DECK_RULES.get("max_slides", 15):
            issues.append({
                "type": "too_many_slides",
                "severity": "medium",
                "message": f"Too many slides: {len(slides)} (max {self.PITCH_DECK_RULES['max_slides']})"
            })
        
        return issues
```

---

## 6. Phase 3: Template System (Week 5-6)

### 6.1 Template Engine

```python
# app/services/slides_new/templates/engine.py

"""
Template Engine - Handles template accuracy.
"""

from typing import Dict, Any, List
import json


class TemplateEngine:
    """
    Manages templates with accurate placeholder resolution.
    """
    
    def __init__(self, db):
        self.db = db
    
    async def get_template_for_archetype(self, archetype: str) -> dict:
        """Get template structure for archetype"""
        
        # This would load from MongoDB templates collection
        # For now, return embedded templates
        
        templates = {
            "yc_seed": {
                "name": "YC Seed Pitch",
                "slides": [
                    {"index": 0, "layout": "title-hero", "purpose": "One-liner"},
                    {"index": 1, "layout": "two-column", "purpose": "Problem"},
                    {"index": 2, "layout": "bullets", "purpose": "Solution"},
                    # ... more slides
                ]
            },
            # ... more templates
        }
        
        return templates.get(archetype, templates["sales"])
    
    async def resolve_placeholders(self, template: dict, context: dict) -> dict:
        """Resolve all placeholders in template"""
        
        resolved_slides = []
        
        for slide in template.get("slides", []):
            resolved_slide = self._resolve_slide(slide, context)
            resolved_slides.append(resolved_slide)
        
        return {"slides": resolved_slides}
    
    def _resolve_slide(self, slide: dict, context: dict) -> dict:
        """Resolve placeholders in single slide"""
        
        resolved = slide.copy()
        
        # Simple placeholder resolution
        placeholders = slide.get("placeholders", {})
        
        for key, placeholder in placeholders.items():
            if isinstance(placeholder, str) and "{{" in placeholder:
                # Extract placeholder name
                placeholder_name = placeholder.replace("{{", "").replace("}}", "").strip()
                
                # Get value from context
                value = context.get(placeholder_name, placeholder)
                resolved["content"][key] = value
        
        return resolved
```

---

## 7. Phase 4: Design Intelligence (Week 7-8)

### 7.1 Anti-AI-Slop Processor

```python
# app/services/slides_new/design/anti_ai_slop.py

"""
Anti-AI-Slop Design System
Applies curated design rules to avoid generic AI aesthetics.
"""

from typing import Dict, Any


class AntiAISlopProcessor:
    """
    Ensures designs avoid generic AI aesthetics.
    Uses 12 curated presets with specific design rules.
    """
    
    PRESETS = {
        "bold-signal": {
            "rules": {
                "background": "dark_gradient",
                "typography": "bold_headings",
                "accents": "glow_effects",
                "spacing": "comfortable"
            }
        },
        "swiss-modern": {
            "rules": {
                "background": "clean_white",
                "typography": "helvetica_style",
                "accents": "minimal",
                "spacing": "grid_based"
            }
        },
        # ... 10 more presets
    }
    
    def apply_preset(self, slide: dict, preset_id: str) -> dict:
        """Apply anti-AI-slop preset to slide"""
        
        preset = self.PRESETS.get(preset_id)
        
        if not preset:
            return slide
        
        # Apply preset rules
        styled_slide = slide.copy()
        styled_slide["design_rules"] = preset["rules"]
        styled_slide["preset"] = preset_id
        
        return styled_slide
```

---

## 8. Phase 5: Quality & Validation (Week 9-10)

### 8.1 Reflective Generation Loop

```python
# app/services/slides_new/quality/reflective_loop.py

"""
Reflective Generation Loop
Iteratively improves quality until threshold met.
"""

from typing import Dict, Any


class ReflectiveLoop:
    """
    Implements reflective generation loop (PPTAgent V2 inspired).
    Runs up to 3 iterations to reach quality threshold.
    """
    
    MAX_ITERATIONS = 3
    QUALITY_THRESHOLD = 85
    
    async def execute(
        self,
        slides: list,
        strategy: dict,
        max_iterations: int = 3,
        quality_threshold: int = 85,
        orchestrator=None
    ) -> Dict[str, Any]:
        """
        Execute reflective loop until quality threshold met.
        """
        
        iteration = 0
        current_slides = slides
        
        while iteration < max_iterations:
            # Run quality check
            from app.services.slides_new.agents.qa_agent import QAAgent
            
            qa_agent = QAAgent(orchestrator.db if orchestrator else None)
            quality_result = await qa_agent.execute(
                slides=current_slides,
                strategy=strategy
            )
            
            quality_score = quality_result.output.get("score", 0)
            
            if quality_score >= quality_threshold:
                # Quality threshold met
                return {
                    "slides": current_slides,
                    "quality_score": quality_score,
                    "iterations": iteration,
                    "passed": True
                }
            
            # Quality not met - refine
            if iteration < max_iterations - 1:
                current_slides = await self._refine_slides(
                    slides=current_slides,
                    quality_report=quality_result.output.get("quality_report", {}),
                    orchestrator=orchestrator
                )
            
            iteration += 1
        
        # Return best we have
        return {
            "slides": current_slides,
            "quality_score": quality_score,
            "iterations": iteration,
            "passed": quality_score >= quality_threshold
        }
    
    async def _refine_slides(
        self,
        slides: list,
        quality_report: dict,
        orchestrator
    ) -> list:
        """Refine slides based on quality issues"""
        
        # This would call LLM to regenerate problematic slides
        # For now, return as-is (placeholder)
        
        issues = quality_report.get("issues", [])
        
        # In real implementation, regenerate slides with issues
        
        return slides
```

---

## 9. Phase 6: Integration & Testing (Week 11-12)

### 9.1 API Endpoint

```python
# app/routers/slides_v2.py

"""
New slide generation router - replaces old generation router.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/v2/slides", tags=["slides_v2"])


class SlideGenerationRequest(BaseModel):
    topic: str
    description: str
    purpose: str
    audience: str = "investors"
    slide_count: int = 10
    mode: str = "standard"
    writing_style: Optional[str] = None
    selected_style_preset: Optional[str] = None
    company_name: Optional[str] = None


@router.post("/generate")
async def generate_slides_v2(
    request: SlideGenerationRequest,
    user_id: str = Depends(get_current_user)
):
    """New slide generation endpoint"""
    
    from app.services.slides_new.orchestrator import (
        SlideGenerationOrchestrator,
        SlideGenerationInput,
        PresentationMode
    )
    from app.database import get_db
    from app.services.orchestrator.progress_tracker import ProgressTracker
    
    db = get_db()
    progress = ProgressTracker(user_id, "presentation")
    
    orchestrator = SlideGenerationOrchestrator(db, progress)
    
    input_data = SlideGenerationInput(
        topic=request.topic,
        description=request.description,
        purpose=request.purpose,
        audience=request.audience,
        slide_count=request.slide_count,
        mode=PresentationMode(request.mode),
        writing_style=request.writing_style or "general",
        selected_style_preset=request.selected_style_preset,
        company_name=request.company_name
    )
    
    result = await orchestrator.generate_slides(input_data, user_id)
    
    if result.metadata and result.metadata.get("needs_style_selection"):
        return {
            "status": "style_selection_required",
            "previews": result.metadata["style_previews"]
        }
    
    return {
        "status": "complete" if result.success else "failed",
        "slides": result.slides,
        "quality_score": result.quality_score,
        "iterations": result.iterations,
        "errors": result.errors
    }


def get_current_user():
    # Placeholder - use actual auth
    return "user_123"
```

---

## 10. Code Structure Summary

### New Files to Create

```
app/services/slides_new/
├── __init__.py
├── orchestrator.py                    # Main coordinator (Phase 1)
├── router.py                          # Route to agents
├── agents/
│   ├── __init__.py
│   ├── base.py                        # Base agent class (Phase 2)
│   ├── ceo_agent.py                   # Strategy (Phase 2)
│   ├── researcher_agent.py            # Research (Phase 2)
│   ├── designer_agent.py              # Design (Phase 2)
│   ├── assembler_agent.py             # Build (Phase 2)
│   └── qa_agent.py                   # Validation (Phase 2)
├── templates/
│   ├── __init__.py
│   ├── engine.py                      # Template accuracy (Phase 3)
│   ├── resolver.py                    # Placeholder resolution (Phase 3)
│   ├── mapper.py                      # Layout mapping (Phase 3)
│   └── registry.py                    # Template storage (Phase 3)
├── design/
│   ├── __init__.py
│   ├── style_discovery.py             # Style previews (Phase 4)
│   ├── anti_ai_slop.py                # Design presets (Phase 4)
│   └── color_system.py                # Color management (Phase 4)
├── quality/
│   ├── __init__.py
│   ├── gates.py                       # Quality rules (Phase 5)
│   ├── reflective_loop.py             # Iteration (Phase 5)
│   └── validators.py                  # Content/design validators (Phase 5)
└── layout/
    ├── __init__.py
    └── pretext_validator.py           # PreTeXt integration (Phase 5)

app/routers/
└── slides_v2.py                       # New API endpoint (Phase 6)
```

---

## 11. Migration Strategy

### What to Replace

| Old Component | New Component | Notes |
|---------------|----------------|-------|
| `/api/generate` | `/api/v2/slides/generate` | New endpoint |
| `orchestrator.py` | `slides_new/orchestrator.py` | Complete rebuild |
| `pitch_decks.py` | Keep + enhance | Still useful |
| Model router | Keep | Works fine |
| LLM clients | Keep | Work fine |
| PPTX builder | Keep + enhance | Works |
| Theme system | Keep + enhance | Works |

### Implementation Order

1. **Week 1-2**: Create base files, agents base class, orchestrator skeleton
2. **Week 3-4**: Implement all 5 agents (CEO, Researcher, Designer, Assembler, QA)
3. **Week 5-6**: Template system, placeholders, layout mapping
4. **Week 7-8**: Design intelligence, style discovery, anti-AI-slop
5. **Week 9-10**: Quality gates, reflective loop, PreTeXt
6. **Week 11-12**: API integration, testing, deployment

---

**Document Status**: Complete New Implementation Plan Ready
**Next Step**: Start Phase 1 - Create foundation files