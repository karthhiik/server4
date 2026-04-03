# 🎯 Premium Slide Generation MCP — Final Comprehensive Plan
## Version 5.1 — World-Class Standalone MCP Server for AI Presentation & Pitch Deck Generation

---

**Document Version**: 5.1 (Complete Standalone Implementation + Template System)
**Created**: 2026-04-02
**Status**: Ready for Implementation
**Architecture**: Production-Grade MCP Server with 6 Specialized Agents + Reflective Loop + Template Generation System

---

## Executive Summary

This is a **complete standalone implementation plan** for a world-class Premium Slide Generation MCP Server with **enhanced Pitch Deck generation** and **accurate Template Generation System**. Built on deep research of 40+ GitHub repositories, YC/Sequoia pitch deck best practices, DocSend investor analytics, and evaluation of PreTeXt (32.2k⭐), OpenPencil (3.9k⭐), yoyo-evolve (1.4k⭐), ppt-master (3,526⭐), and deckbuilder (7⭐) reference repositories.

### Key Differentiators (vs v3.0/v4.0)

- **6 Specialized Agents** (NEW: Code Agent for React/Tailwind generation)
- **Reflective Generation Loop** (PPTAgent V2 inspired) with 2-3 iteration cycles
- **PreTeXt Integration** (32.2k⭐) — DOM-free text measurement for precise layout
- **Visual Style Discovery UX** — 3 preview options, user selects preferred style
- **Anti-AI-Slop Design** — 12 curated style presets avoiding generic aesthetics
- **Pitch Deck Domain Intelligence** — YC/Sequoia/DocSend rules as first-class constraints
- **40+ Built-in Templates** — Accurate template generation system with placeholder resolution
- **Real-World LLM Integration** — 15+ models (Cloudflare/Groq/Azure/OpenRouter) with noise handling
- **Hybrid Architecture** — Python (Core MCP) + TypeScript (Code Agent)
- **65+ MCP Tools** across 13 categories
- **14-Week Implementation Phases**

---

## Table of Contents

1. Executive Summary
2. Architecture Overview
3. Gap Analysis (18 Gaps)
4. Agent System (6 Specialized Agents)
5. Slide DSL Specification
5B. Template Generation System (NEW - Enhanced)
6. Technology Stack
6B. LLM Model Integration (Complete Real-World Implementation)
7. PreTeXt Integration Architecture
8. Reflective Generation Loop
9. Visual Style Discovery System
10. Pitch Deck Domain Intelligence
11. Enhanced Export Pipeline
12. Agent Communication Protocol
13. Tool Specification (65+ Tools)
14. Theme System (16 Color Schemes + 12 Style Presets)
15. Quality Gates (Enhanced)
16. Security Architecture
17. Storage Architecture
18. Implementation Phases (14 Weeks)
19. Success Metrics
20. Risk Assessment
21. Differentiation Summary
22. Reference Integration Analysis

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     PREMIUM SLIDE GENERATION MCP SERVER                            │
│                                                                                     │
│   Protocol: Model Context Protocol (MCP) — JSON-RPC over stdio/HTTP+SSE          │
│   Framework: FastMCP (FastAPI) + Node.js Code Agent                               │
│   Language: Python 3.11+ (Core) + TypeScript (Code Agent)                         │
│   Storage: Chroma (Vector) + MongoDB (Document) + Redis (Cache)                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   ORCHESTRATOR       │   │   AGENT SWARM        │   │   DESIGN ENGINE      │
│   (Supervisor)       │   │   (6 Specialized)     │   │   (Theme + Quality)  │
│                       │   │                       │   │                       │
│ • Task Decomposition  │   │ 1. CEO/Strategist    │   │ • Theme System       │
│ • Agent Coordination  │   │ 2. Researcher/Analyst │   │ • 16 Color Schemes   │
│ • Context Management  │   │ 3. Designer/Creative  │   │ • 12 Style Presets   │
│ • Quality Gates       │   │ 4. Assembler/Engineer │   │ • Visual Discovery   │
│ • Reflective Loop     │   │ 5. Code Agent (NEW)   │   │ • PreTeXt Validation │
│ • Error Recovery     │   │ 6. QA Lead/Reviewer   │   │ • Anti-AI-Slop      │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
        │                                   │                                   │
        ▼                                   ▼                                   ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   KNOWLEDGE LAYER    │   │   TOOL LAYER          │   │   RENDER LAYER         │
│   (Storage + RAG)    │   │   (65+ MCP Tools)    │   │   (Multi-Format)      │
│                       │   │                       │   │                       │
│ • Chroma Vector Store│   │ • Presentation CRUD   │   │ • React Components    │
│ • MongoDB Documents  │   │ • Slide Operations     │   │ • PPTX (PptxGenJS)    │
│ • Redis Cache        │   │ • Content Generation   │   │ • PDF (Puppeteer)     │
│ • File System        │   │ • Image Generation     │   │ • HTML (Zero-dep)     │
│                       │   │ • Code Agent Tools     │   │ • Google Slides       │
│                       │   │ • Diagram Integration  │   │ • Images Export       │
│                       │   │ • Template Management  │   │ • Template Registry   │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
                                            │
                                            ▼
                          ┌─────────────────────────────────┐
                          │   BROWSER DAEMON               │
                          │   (Playwright-based)           │
                          │                                 │
                          │ • Live Preview Rendering       │
                          │ • Visual QA & Screenshots      │
                          │ • Layout Verification          │
                          │ • PreTeXt Client Validation    │
                          └─────────────────────────────────┘
```

---

## 3. Gap Analysis (18 Gaps)

### Original 12 Gaps (Retained and Enhanced)

| ID | Gap | Source | Solution |
| :--- | :--- | :--- | :--- |
| G1 | No multi-agent orchestration | Both plans | 6 agents with Supervisor-Worker pattern |
| G2 | Limited real-time collaboration | ChatGPT | P2P via WebRTC (future phase) |
| G3 | Weak offline/local capabilities | ChatGPT | Cloud LLM (user-defined in next chat) |
| G4 | No integrated design QA | ChatGPT | PreTeXt + contrast + brand compliance |
| G5 | No canvas editing with AI | ChatGPT | Konva.js/react-konva |
| G6 | Quality guards basic/absent | ChatGPT | Reflective loop + 15+ quality rules |
| G7 | No persistent browser preview | Gemini | Playwright daemon pattern |
| G8 | No intelligent layout selection | Gemini | Content-aware AI Template Selector |
| G9 | No auto-layout with text fitting | Gemini | PreTeXt DOM-free measurement |
| G10 | No professional color schemes | Gemini | 16 schemes + 12 style presets |
| G11 | No deployment archetypes | Gemini | 6 archetypes + pitch deck domain |
| G12 | No security layers | Gemini | Local isolation + audit + PII |

### New Gaps Discovered (G13-G18)

| ID | Gap | Research Source | Solution |
| :--- | :--- | :--- | :--- |
| G13 | No Code Agent for React/Tailwind | User request + analysis | New 6th agent: React/Tailwind generation |
| G14 | No reflective generation loop | PPTAgent V2 (EMNLP 2025) | Generate > Evaluate > Refine cycle |
| G15 | No visual style discovery UX | Frontend Slides (10k⭐) | 3 preview selection pattern |
| G16 | No pitch deck domain intelligence | YC/DocSend research | YC structure + investor rules |
| G17 | No self-contained HTML output | Frontend Slides | Zero-dependency inline bundler |
| G18 | No diagram integration | Excalidraw (83k⭐) + Mermaid | Excalidraw npm + Mermaid |

---

## 4. Agent System (6 Specialized Agents)

### Agent 1: CEO / Strategist Agent
**Purpose**: Narrative blueprinting, validates presentation necessity
- **Framework**: SCQA, Pyramid Principle, YC Pitch Deck Structure
- **Tools**: analyze_presentation, validate_strategy, select_archetype
- **Workflow**:
  1. Challenge premise: "Why this presentation?"
  2. Determine archetype: Pitch Deck / Consulting / Academic / Report / Sales
  3. Define narrative arc: Problem-Solution, Timeline, Comparison
  4. Activate Pitch Deck Domain Intelligence if investor deck
  5. Output: Strategic Outline with purpose, audience, slide order

### Agent 2: Researcher / Analyst Agent
**Purpose**: Gather source-backed evidence and data
- **Framework**: Grounded Research, Fact-Checking
- **Tools**: research_topic, extract_document, search_web, analyze_data, validate_sources
- **Workflow**:
  1. Generate search queries from topic
  2. Execute parallel web searches
  3. Parse uploaded documents (PDF/DocX/PPT/Excel)
  4. Ingest to vector DB for similarity search
  5. Synthesize with citations and data points

### Agent 3: Designer / Creative Agent
**Purpose**: Visual identity, theme application, layout optimization
- **Framework**: Cognitive Load Theory, Visual Hierarchy, Anti-AI-Slop
- **Tools**: apply_theme, generate_theme, analyze_design_quality, list_themes, discover_style
- **Workflow**:
  1. Activate Visual Style Discovery (generate 3 previews)
  2. User selects preferred style
  3. Apply color scheme (16 built-in palettes)
  4. Optimize layout per slide (AI Template Selector)
  5. Run accessibility checks (contrast ≥4.5:1)
  6. Apply anti-AI-slop processing

### Agent 4: Assembler / Engineer Agent
**Purpose**: Programmatic building of PPTX file using python-pptx
- **Framework**: Open XML Standards
- **Tools**: create_presentation, add_slide, add_chart, add_table, add_image
- **Workflow**:
  1. Initialize presentation with template
  2. Add slides with master layouts
  3. Populate content with placeholders
  4. Insert charts, tables, shapes
  5. Apply styling (fonts, colors, spacing)
  6. Set core properties

### Agent 5: Code Agent (NEW - Primary Addition)
**Purpose**: Generate React/Tailwind slide components, multi-format export
- **Framework**: Component-Driven Architecture, Slide DSL
- **Tools**: generate_slide_dsl, compile_react_slides, measure_text_fit, validate_slide_dsl, export_to_pptx, export_to_pdf, export_to_html, generate_diagram, preview_slides, apply_anti_slop
- **Workflow**:
  1. Receive content from CEO + Researcher
  2. Generate Slide DSL (structured JSON)
  3. PreTeXt validation for text fitting
  4. Compile to React components with Tailwind
  5. Apply anti-AI-slop styling
  6. Add interactive elements (diagrams, charts)
  7. Multi-format export (PPTX, PDF, HTML, React)

### Agent 6: QA Lead / Reviewer Agent
**Purpose**: Quality assurance, visual verification, reflective iteration
- **Framework**: E2E Testing, Aesthetic Audits, Reflective Loop
- **Tools**: validate_content, check_branding, validate_sources, get_improvements, browse, snapshot, screenshot
- **Workflow**:
  1. Render presentation in browser
  2. Capture screenshots for visual QA
  3. Verify layout integrity (PreTeXt + visual)
  4. Check for anti-AI-slop compliance
  5. Validate content against quality gates
  6. **Initiate Reflective Loop if needed** (return to agent for refinement)
  7. Report issues or pass verdict

---

## 5. Slide DSL Specification

The Slide DSL is the core abstraction that enables reliable LLM generation. Rather than generating raw code, the Code Agent generates structured JSON that a deterministic compiler transforms into React components.

```json
{
  "version": "5.0",
  "presentation": {
    "id": "deck_abc123",
    "title": "NeuralScale AI Infrastructure",
    "archetype": "investor-pitch",
    "theme": {
      "id": "modern-blue",
      "variant": "dark",
      "preset": "bold-signal"
    },
    "aspectRatio": "16:9",
    "dimensions": { "width": 1280, "height": 720 }
  },
  "slides": [
    {
      "index": 0,
      "type": "title-slide",
      "layout": "center-focus",
      "content": {
        "title": "NeuralScale",
        "subtitle": "AI Infrastructure for the Next Billion Parameters",
        "presenter": "Jane Doe, CEO",
        "tagline": "Series A — $12M"
      },
      "style": {
        "background": "gradient-radial",
        "accentColor": "#FF6B35"
      }
    }
  ]
}
```

### DSL Schema Validation

- Zod schemas for runtime validation
- PreTeXt text measurement before DSL finalization
- Quality gates check DSL compliance

---

## 5B. Template Generation System (NEW - Enhanced)

Based on deep research of **deckbuilder** (7⭐ MCP server), **pptx-template** (113⭐), **python-pptx-templater** (43⭐), **pptx-templatex** (PyPI), **powerpoint-template-system** (PyPI), and **SlideCoder** (EMNLP 2025), this system provides accurate, scalable template generation.

### 5B.1 Template Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TEMPLATE GENERATION SYSTEM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │  Template   │ -> │  Layout     │ -> │   Content   │            │
│  │  Loader     │    │  Engine     │    │   Filler    │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│        │                  │                  │                       │
│        ▼                  ▼                  ▼                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              TEMPLATE REGISTRY (MongoDB)                     │   │
│  │  • Built-in templates (40+)                                │   │
│  │  • Custom user templates                                    │   │
│  │  • Pitch deck archetypes                                    │   │
│  │  • Layout mappings                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              PLACEHOLDER RESOLUTION ENGINE                  │   │
│  │  • {{title}}, {{subtitle}}, {{bullets[]}}                   │   │
│  │  • {{chart.data}}, {{table.rows}}                           │   │
│  │  • {{image.path}}, {{logo.position}}                        │   │
│  │  • Conditional placeholders: {{#if hasChart}}...{{/if}}    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 5B.2 Template Types Supported

| Template Type | Description | Use Case |
| :--- | :--- | :--- |
| **PPTX Master** | Native PowerPoint .pptx templates with layout masters | Enterprise, legacy workflows |
| **JSON Schema** | JSON-defined templates with component mappings | AI generation, dynamic |
| **DSL Template** | Slide DSL with variable placeholders | Code Agent generation |
| **YAML Template** | Human-readable template definitions | Developer workflows |
| **HTML/Tailwind** | Web-based templates for HTML export | Web presentations |

### 5B.3 Placeholder System (Accuracy-Focused)

The template system uses a sophisticated placeholder resolution engine:

```python
# Placeholder Types
PLACEHOLDERS = {
    # Simple text placeholders
    "{{title}}": str,
    "{{subtitle}}": str,
    "{{presenter}}": str,
    
    # List/array placeholders
    "{{bullets[]}}": List[str],
    "{{team_members[]}}": List[Dict],
    
    # Data placeholders
    "{{chart.data}}": ChartData,
    "{{table.rows[]}}": List[List[str]],
    
    # Conditional placeholders
    "{{#if has_logo}}logo_block{{/if}}": ConditionalBlock,
    
    # Nested placeholders
    "{{slides[].title}}": List[str],
    "{{slides[].content.bullets[]}}": List[List[str]],
}

# Placeholder Resolution Rules
class PlaceholderResolver:
    def resolve(self, template: str, context: dict) -> str:
        # 1. Parse all placeholders
        placeholders = self.extract_placeholders(template)
        
        # 2. Validate against context
        for placeholder in placeholders:
            if not self.validate_placeholder(placeholder, context):
                raise PlaceholderError(f"Missing: {placeholder}")
        
        # 3. Apply transformations
        resolved = self.apply_resolvers(template, context)
        
        # 4. Validate output
        return self.validate_output(resolved)
```

### 5B.4 Layout Mapping Engine

Based on research of **pptx-template** (113⭐) and **python-pptx-templater** (43⭐):

```python
class LayoutMapper:
    """Maps content types to optimal PPTX layouts"""
    
    LAYOUT_MAPPINGS = {
        # Title slide layouts
        ("title", "default"): 0,      # Title Slide
        ("title", "centered"): 6,    # Title Only (centered)
        
        # Content layouts
        ("content", "bullets"): 1,   # Title and Content
        ("content", "two-column"): 2, # Two Content
        ("content", "comparison"): 2,  # Two Content (comparison)
        
        # Data layouts
        ("data", "chart"): 5,         # Chart
        ("data", "table"): 4,        # Table
        ("data", "diagram"): 3,      # Diagram
        
        # Special layouts
        ("team", "grid"): 2,          # Two Content (team grid)
        ("timeline", "process"): 3,  # Process (arrows)
        ("market", "tam-sam-som"): 5, # Chart (concentric circles)
    }
    
    def get_layout_index(self, content_type: str, style: str) -> int:
        key = (content_type, style)
        return self.LAYOUT_MAPPINGS.get(key, 1)  # Default to Title + Content
```

### 5B.5 Template Registry (MongoDB-backed)

```python
class TemplateRegistry:
    """Central template management with versioning"""
    
    async def register_template(self, template: Template) -> str:
        # Validate template structure
        self.validate_template(template)
        
        # Assign version
        template.version = await self.get_next_version(template.name)
        
        # Store in MongoDB
        await self.db.templates.insert_one(template.to_dict())
        
        return template.id
    
    async def get_template(self, template_id: str) -> Template:
        return await self.db.templates.find_one({"_id": template_id})
    
    async def list_templates(self, category: str = None) -> List[Template]:
        query = {"category": category} if category else {}
        return await self.db.templates.find(query).to_list()
    
    async def extract_layouts(self, pptx_path: str) -> List[LayoutInfo]:
        """Extract layout info from existing PPTX (like pptx-templatex)"""
        prs = Presentation(pptx_path)
        return [
            LayoutInfo(
                index=i,
                name=layout.name,
                placeholder_types=self.detect_placeholders(layout)
            )
            for i, layout in enumerate(prs.slide_layouts)
        ]
```

### 5B.6 Built-in Template Library (40+ Templates)

Based on research of **hugohe3/ppt-master** (3,526⭐), **m3dev/pptx-template** (113⭐), and pitch deck best practices:

#### Pitch Deck Templates (12)

| Template ID | Name | Layouts | Archetype |
| :--- | :--- | :--- | :--- |
| `yc-seed` | YC Seed Pitch | 12 slides | Investor Pitch |
| `series-a` | Series A Pitch | 15 slides | Investor Pitch |
| `enterprise-sales` | Enterprise Sales | 10 slides | Sales |
| `saas-metrics` | SaaS Metrics | 8 slides | Finance |
| `product-launch` | Product Launch | 10 slides | Marketing |
| `team-deck` | Team Introduction | 6 slides | Company |
| `market-analysis` | Market Analysis | 8 slides | Strategy |
| `competitive-landscape` | Competitive Analysis | 7 slides | Strategy |
| `technical-demo` | Technical Demo | 12 slides | Product |
| `investor-update` | Investor Update | 10 slides | Finance |
| `board-deck` | Board Presentation | 12 slides | Executive |
| `mvp-pitch` | MVP Pitch | 8 slides | Investor Pitch |

#### Business Templates (15)

| Template ID | Name | Layouts | Archetype |
| :--- | :--- | :--- | :--- |
| `quarterly-review` | Quarterly Business Review | 12 slides | Corporate |
| `project-update` | Project Status Update | 8 slides | Corporate |
| `proposal` | Business Proposal | 10 slides | Sales |
| `case-study` | Customer Case Study | 10 slides | Marketing |
| `training` | Training Deck | 15 slides | Education |
| `all-hands` | All Hands Meeting | 8 slides | Internal |
| `roadmap` | Product Roadmap | 10 slides | Product |
| `strategy-offsite` | Strategy Offsite | 12 slides | Executive |
| `product-demo` | Product Demo | 10 slides | Sales |
| `annual-plan` | Annual Planning | 12 slides | Corporate |
| `hiring-deck` | Recruiting Presentation | 8 slides | HR |
| `partnership-deck` | Partnership Pitch | 10 slides | BD |
| `investor-meeting` | Investor Meeting | 8 slides | Finance |
| `acquisition-deck` | M&A Presentation | 10 slides | Executive |
| `crisis-comms` | Crisis Communication | 6 slides | Corporate |

#### Academic/Educational Templates (8)

| Template ID | Name | Layouts | Archetype |
| :--- | :--- | :--- | :--- |
| `lecture-slide` | Academic Lecture | 20 slides | Education |
| `research-defense` | PhD Defense | 15 slides | Academic |
| `conference-talk` | Conference Presentation | 12 slides | Academic |
| `workshop` | Workshop Material | 15 slides | Education |
| `lab-presentation` | Lab Presentation | 10 slides | Academic |
| `thesis-proposal` | Thesis Proposal | 10 slides | Academic |
| `journal-club` | Journal Club | 8 slides | Academic |
| `seminar` | Seminar Talk | 12 slides | Academic |

#### Creative/Specialty Templates (5)

| Template ID | Name | Layouts | Archetype |
| :--- | :--- | :--- | :--- |
| `portfolio` | Creative Portfolio | 10 slides | Creative |
| `photo-story` | Photo Story | 8 slides | Creative |
| `timeline-history` | Historical Timeline | 10 slides | Narrative |
| `infographic` | Data Infographic | 6 slides | Data |
| `interactive-workshop` | Interactive Workshop | 12 slides | Education |

### 5B.7 Template Accuracy System

To ensure accuracy as requested, the system implements multiple validation layers:

```python
class TemplateAccuracyValidator:
    """Ensures template generation accuracy"""
    
    async def validate_template(self, template: Template) -> ValidationResult:
        errors = []
        warnings = []
        
        # 1. Schema validation
        schema_errors = self.validate_schema(template)
        errors.extend(schema_errors)
        
        # 2. Placeholder completeness
        placeholder_errors = self.validate_placeholders(template)
        errors.extend(placeholder_errors)
        
        # 3. Layout consistency
        layout_errors = self.validate_layouts(template)
        errors.extend(layout_errors)
        
        # 4. Style consistency
        style_errors = self.validate_styles(template)
        warnings.extend(style_errors)
        
        # 5. Accessibility check
        a11y_errors = self.validate_accessibility(template)
        warnings.extend(a11y_errors)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def validate_output(self, presentation: Presentation) -> ValidationResult:
        """Validate generated presentation"""
        errors = []
        
        # Check all placeholders resolved
        for slide in presentation.slides:
            if self.has_unresolved_placeholders(slide):
                errors.append(f"Unresolved placeholder in slide {slide.index}")
        
        # Check layout integrity
        if not self.validate_layout_integrity(presentation):
            errors.append("Layout integrity violation")
        
        # Check text overflow (via PreTeXt)
        for slide in presentation.slides:
            if self.has_text_overflow(slide):
                errors.append(f"Text overflow in slide {slide.index}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### 5B.8 Template Tools (MCP)

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `load_template` | template_id, version | Load template from registry |
| `register_template` | template_path, category, metadata | Register new template |
| `list_templates` | category, search | Search available templates |
| `extract_template_layouts` | pptx_path | Extract layouts from PPTX |
| `validate_template` | template_id | Validate template structure |
| `create_from_schema` | schema_path, name | Create template from JSON/YAML |
| `clone_template` | template_id, new_name | Clone existing template |
| `export_template` | template_id, output_path | Export template as file |
| `import_template` | template_path | Import external template |
| `get_template_metadata` | template_id | Get template details |

### 5B.9 Reference Implementations Used

| Reference | Stars | What Was Adopted |
| :--- | :--- | :--- |
| **hugohe3/ppt-master** | 3,526 | Template-based PPTX generation, 15 examples |
| **m3dev/pptx-template** | 113 | JSON-based template engine pattern |
| **python-pptx-templater** | 43 | Layout template filling |
| **pptx-templatex** (PyPI) | N/A | Slide copying + placeholder replacement |
| **powerpoint-template-system** | N/A | Business presentation templates |
| **deckbuilder** | 7 | MCP server for PPTX, content-first design |
| **SlideCoder** (EMNLP 2025) | N/A | Layout-aware RAG slide generation |

---

## 6. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Core MCP Server** | Python 3.11+, FastMCP | Agent orchestration, tool delivery |
| **Code Agent** | TypeScript, Node.js | React component generation, DSL compilation |
| **PPTX Generation** | PptxGenJS (native objects) | Editable PPTX with native objects |
| **PDF Generation** | Puppeteer (headless Chrome) | Pixel-perfect PDF from HTML |
| **HTML Export** | Inline bundler (zero deps) | Self-contained single HTML file |
| **Text Measurement** | PreTeXt (@chenglou/pretext) | DOM-free text fitting, overflow detection |
| **Layout Engine** | Yoga WASM | Server-side flexbox computation |
| **Styling** | Tailwind CSS v4 + @tailwindcss/typography | Utility-first design system |
| **Canvas Editor** | Konva.js + react-konva | Interactive WYSIWYG editing |
| **Browser Automation** | Playwright | Live preview, visual QA, screenshots |
| **Vector Store** | Chroma (embedded) | Presentation embeddings |
| **Document Store** | MongoDB | Presentations, slides, themes |
| **Cache** | Redis | LLM responses, theme configs |
| **LLM Clients** | Multi-provider (12+ providers) | Cloudflare, Azure, Groq, OpenRouter |
| **Diagrams** | Excalidraw npm + Mermaid | Hand-drawn diagrams, flowcharts |
| **Charts** | D3.js / Recharts | TAM/SAM/SOM, financial projections |

---

## 6B. LLM Model Integration (Complete Real-World Implementation)

Based on real-time project requirements, this section defines integration for all available models with proper usage patterns, noise handling, and routing strategies.

### 6B.1 Available Models Overview

#### Image Generation Models (Free - Cloudflare Workers AI)

| Model | Provider | Limit | Cost | Type |
| :--- | :--- | :--- | :--- | :--- |
| **FLUX.1-Kontext-pro** | Azure (Subscription) | Unlimited | Paid | Image Generation |
| **lucid-origin** | Cloudflare | 1,000/day | Free | Image Generation |
| **gemma-3-12b-it** | Cloudflare | 1,000/day | Free | Multimodal (Text + Image) |

#### Text Generation Models (Free - Cloudflare Workers AI)

| Model | Provider | Limit | Cost | Type |
| :--- | :--- | :--- | :--- | :--- |
| **qwen2.5-coder-32b-instruct** | Cloudflare | 1,000/day | Free | Code Generation |
| **glm-4.7-flash** | Cloudflare | 1,000/day | Free | Text Generation |

#### Text Generation Models (Free - OpenRouter)

| Model | Provider | Limit | Cost | Type |
| :--- | :--- | :--- | :--- | :--- |
| **qwen/qwen3.6-plus-preview:free** | OpenRouter | Unlimited | Free | Text Generation |

#### Text Generation Models (Free - Groq)

| Model | Provider | API Keys | Cost | Type |
| :--- | :--- | :--- | :--- | :--- |
| **Groq Mixtral** | Groq | 8 keys available | Free | Text Generation |
| **Groq Llama** | Groq | 8 keys available | Free | Text Generation |

#### Text Generation Models (Subscription - Azure)

| Model | Provider | Cost | Type |
| :--- | :--- | :--- | :--- |
| **Kimi-K2-Thinking** | Azure | Paid (Subscription) | Reasoning |
| **DeepSeek-V3.2** | Azure | Paid (Subscription) | Text Generation |
| **gpt-4o-mini** | Azure | Paid (Subscription) | Text Generation |
| **Phi-4-reasoning** | Azure | Paid (Subscription) | Reasoning |
| **mistral-medium-2505** | Azure | Paid (Subscription) | Text Generation |

---

### 6B.2 Cloudflare Workers AI Integration (Free Models)

Based on analysis of `pp.py` and Cloudflare Workers AI documentation (2026):

#### Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│              CLOUDFLARE WORKERS AI INTEGRATION                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Request Flow:                                                     │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────┐               │
│   │  App    │ -> │  Worker URL │ -> │  Cloudflare │               │
│   │         │    │             │    │  Workers AI │               │
│   └─────────┘    └─────────────┘    └─────────────┘               │
│                                                                      │
│   Authentication:                                                   │
│   Headers: { "Authorization": "Bearer {API_KEY}" }                 │
│                                                                      │
│   Response Format (may contain noise):                              │
│   { "message": "clean response" } OR { "text": "noisy response" }  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Implementation Code

```python
import requests
import json
import re
from typing import Optional, Dict, Any

class CloudflareWorkerClient:
    """Base client for Cloudflare Workers AI models"""
    
    def __init__(self, worker_url: str, api_key: str):
        self.worker_url = worker_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _clean_response(self, response: Dict[str, Any]) -> str:
        """
        Noise cleaning for Cloudflare responses.
        Cloudflare workers may return responses in different formats.
        """
        # Try common response keys
        for key in ['message', 'text', 'content', 'response', 'result', 'output']:
            if key in response:
                return self._post_clean(response[key])
        
        # Fallback: return entire response as string
        return self._post_clean(str(response))
    
    def _post_clean(self, text: str) -> str:
        """Post-process cleaned text to remove remaining artifacts"""
        # Remove markdown code blocks
        text = re.sub(r'```[\w]*\n', '', text)
        text = re.sub(r'```', '', text)
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _handle_error(self, response) -> Dict[str, Any]:
        """Handle error responses with detailed logging"""
        try:
            error_data = response.json()
            print(f"Cloudflare API Error: {error_data}")
            return {"error": error_data.get('message', 'Unknown error')}
        except:
            return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}


# ============================================================
# GLM-4.7-Flash (Text Generation) - Cloudflare Worker
# ============================================================

class GLM47FlashClient(CloudflareWorkerClient):
    """GLM-4.7-Flash text generation via Cloudflare Worker"""
    
    # Worker URL - Replace with your actual worker endpoint
    WORKER_URL = "https://gklm47deploymentaiiglmodel.barisebot.workers.dev"
    API_KEY = "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"
    
    def __init__(self):
        super().__init__(self.WORKER_URL, self.API_KEY)
    
    def generate(self, message: str, system_prompt: str = None) -> str:
        """
        Generate text using GLM-4.7-Flash
        
        Args:
            message: User message/prompt
            system_prompt: Optional system prompt
            
        Returns:
            Cleaned response string
        """
        payload = {"message": message}
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(
            f"{self.worker_url}/",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return self._clean_response(result)
        else:
            error = self._handle_error(response)
            return f"Error: {error.get('error', 'Unknown error')}"


# ============================================================
# Qwen2.5-Coder-32B-Instruct (Code Generation) - Cloudflare
# ============================================================

class QwenCoderClient(CloudflareWorkerClient):
    """Qwen2.5-Coder-32B-Instruct code generation via Cloudflare Worker"""
    
    # Worker URL - Replace with your actual worker endpoint
    WORKER_URL = "https://qwenmodelllmcodingmodling.collegeaurora3.workers.dev"
    API_KEY = "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"
    
    def __init__(self):
        super().__init__(self.WORKER_URL, self.API_KEY)
    
    def generate_code(self, prompt: str, language: str = "python") -> str:
        """Generate code using Qwen2.5-Coder"""
        
        # Add language context to prompt
        enhanced_prompt = f"Write {language} code for: {prompt}"
        
        payload = {"message": enhanced_prompt}
        
        response = requests.post(
            f"{self.worker_url}/",
            headers=self.headers,
            json=payload,
            timeout=90  # Code generation may take longer
        )
        
        if response.status_code == 200:
            result = response.json()
            cleaned = self._clean_response(result)
            # Additional code-specific cleaning
            return self._clean_code_output(cleaned)
        else:
            error = self._handle_error(response)
            return f"Error: {error.get('error', 'Unknown error')}"
    
    def _clean_code_output(self, code: str) -> str:
        """Additional cleaning for code output"""
        # Ensure code blocks are properly formatted
        if '```' not in code:
            # Wrap in code block if no formatting
            code = f"```{code}```"
        return code


# ============================================================
# Gemma-3-12B-IT (Multimodal) - Cloudflare Worker
# ============================================================

class Gemma3Client(CloudflareWorkerClient):
    """Gemma-3-12B-IT multimodal model via Cloudflare Worker"""
    
    # Worker URL - Replace with your actual worker endpoint
    WORKER_URL = "http://gemmamodelforimageanddesigning.hiwings58.workers.dev"
    API_KEY = "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"
    
    def __init__(self):
        super().__init__(self.WORKER_URL, self.API_KEY)
    
    def generate(self, message: str, task: str = "general") -> str:
        """
        Generate using Gemma-3
        
        Args:
            message: User message
            task: Task type (general, code, analysis, image_description)
        """
        # Add task-specific context
        task_contexts = {
            "general": "Provide a clear and concise response.",
            "code": "Write clean, well-commented code.",
            "analysis": "Provide detailed analysis with reasoning.",
            "image_description": "Describe the image in detail."
        }
        
        enhanced_message = f"{task_contexts.get(task, task_contexts['general'])}\n\n{message}"
        payload = {"message": enhanced_message}
        
        response = requests.post(
            f"{self.worker_url}/",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return self._clean_response(result)
        else:
            error = self._handle_error(response)
            return f"Error: {error.get('error', 'Unknown error')}"


# ============================================================
# Lucid-Origin (Image Generation) - Cloudflare Worker
# ============================================================

import base64

class LucidOriginClient(CloudflareWorkerClient):
    """Lucid-Origin image generation via Cloudflare Worker"""
    
    # Worker URL - Replace with your actual worker endpoint
    WORKER_URL = "https://lucid-originmodel.barisebotsnetworking.workers.dev"
    API_KEY = "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"
    
    def __init__(self):
        super().__init__(self.WORKER_URL, self.API_KEY)
    
    def generate_image(self, prompt: str) -> Optional[bytes]:
        """
        Generate image using Lucid-Origin
        
        Args:
            prompt: Image generation prompt
            
        Returns:
            Image as bytes or None on failure
        """
        payload = {"prompt": prompt}
        
        try:
            response = requests.post(
                f"{self.worker_url}/",
                headers=self.headers,
                json=payload,
                timeout=120  # Image generation takes longer
            )
            
            if response.status_code == 200:
                # Lucid-Origin returns base64 encoded image
                return response.content  # Already decoded from base64 by worker
            else:
                self._handle_error(response)
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
    
    def generate_and_save(self, prompt: str, filename: str = None) -> Optional[str]:
        """Generate image and save to file"""
        import time
        
        image_data = self.generate_image(prompt)
        if image_data:
            if not filename:
                filename = f"generated_image_{int(time.time())}.jpg"
            
            with open(filename, "wb") as f:
                f.write(image_data)
            
            print(f"✅ Image saved to: {filename}")
            return filename
        return None
```

#### Noise Handling for Cloudflare Models

```python
class CloudflareNoiseHandler:
    """
    Comprehensive noise handling for Cloudflare Workers AI responses.
    Based on analysis of pp.py worker responses.
    """
    
    # Common noise patterns observed in Cloudflare worker responses
    NOISE_PATTERNS = [
        # Markdown artifacts
        r'```\w*\n?',  # Incomplete code blocks
        r'```',        # Unclosed code blocks
        # Extra formatting
        r'^\s*[-*]\s*[-*]\s*[-*]+\s*$',  # Separator lines
        # Whitespace issues
        r'\n\s*\n\s*\n+',  # Multiple newlines
        # JSON-like artifacts (when plain text expected)
        r'^\{.*\}\s*$',  # Stray JSON objects
    ]
    
    @classmethod
    def clean_response(cls, response: str) -> str:
        """Clean response with multiple passes"""
        cleaned = response
        
        # Remove noise patterns
        for pattern in cls.NOISE_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned)
        
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Remove control characters
        cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', cleaned)
        
        return cleaned.strip()
    
    @classmethod
    def validate_response(cls, response: str) -> bool:
        """Check if response is valid (not just noise)"""
        if not response or len(response.strip()) < 3:
            return False
        
        # Check for excessive special characters
        special_ratio = len(re.sub(r'[\w\s]', '', response)) / max(len(response), 1)
        if special_ratio > 0.5:  # More than 50% special chars = likely noise
            return False
        
        return True
```

---

### 6B.3 Azure AI Foundry Integration (Subscription Models)

Based on Microsoft Azure AI Foundry documentation (2026):

#### Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│              AZURE AI FOUNDRY INTEGRATION                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Options:                                                          │
│   1. OpenAI SDK (Recommended - v1 API)                              │
│   2. Azure AI Foundry SDK                                           │
│   3. Direct REST API                                                │
│                                                                      │
│   Authentication:                                                    │
│   - Azure Active Directory (AAD)                                   │
│   - API Key (simpler)                                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Implementation Code

```python
from openai import AzureOpenAI
from typing import Optional, Dict, Any, List
import time

class AzureOpenAIClient:
    """Base client for Azure OpenAI models using OpenAI SDK"""
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        api_version: str = "2024-12-01-preview"
    ):
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
    
    def generate(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """Generate text with specified model"""
        
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content


# ============================================================
# Kimi-K2-Thinking (Reasoning) - Azure
# ============================================================

class KimiK2ThinkingClient(AzureOpenAIClient):
    """Kimi-K2-Thinking for complex reasoning tasks"""
    
    # Configuration - Replace with your actual Azure values
    API_KEY = "YOUR_AZURE_API_KEY"
    ENDPOINT = "https://YOUR_RESOURCE.openai.azure.com/"
    MODEL = "kimi-k2-thinking"  # Replace with actual model deployment name
    
    def __init__(self):
        super().__init__(self.API_KEY, self.ENDPOINT)
    
    def reasoning_generate(self, prompt: str, thinking_depth: str = "high") -> Dict[str, Any]:
        """
        Generate with reasoning
        
        Args:
            prompt: Input prompt
            thinking_depth: thinking_effort level (low, medium, high)
        """
        messages = [
            {"role": "system", "content": "You are a reasoning AI. Show your thinking process."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=8192,
            extra_body={"thinking": {"type": "enabled", "max_tokens": thinking_depth}}
        )
        
        return {
            "reasoning": getattr(response, 'reasoning_content', None),
            "content": response.choices[0].message.content
        }


# ============================================================
# DeepSeek-V3.2 - Azure
# ============================================================

class DeepSeekV32Client(AzureOpenAIClient):
    """DeepSeek-V3.2 for general text generation"""
    
    API_KEY = "YOUR_AZURE_API_KEY"
    ENDPOINT = "https://YOUR_RESOURCE.openai.azure.com/"
    MODEL = "deepseek-v3-2"  # Replace with actual deployment name
    
    def __init__(self):
        super().__init__(self.API_KEY, self.ENDPOINT)
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text using DeepSeek-V3.2"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        return response.choices[0].message.content


# ============================================================
# GPT-4o-Mini - Azure
# ============================================================

class GPT4MiniClient(AzureOpenAIClient):
    """GPT-4o-Mini for fast, cost-effective generation"""
    
    API_KEY = "YOUR_AZURE_API_KEY"
    ENDPOINT = "https://YOUR_RESOURCE.openai.azure.com/"
    MODEL = "gpt-4o-mini"  # Replace with actual deployment name
    
    def __init__(self):
        super().__init__(self.API_KEY, self.ENDPOINT)
    
    def fast_generate(self, prompt: str) -> str:
        """Fast generation with GPT-4o-Mini"""
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        return response.choices[0].message.content


# ============================================================
# Phi-4-Reasoning - Azure
# ============================================================

class Phi4ReasoningClient(AzureOpenAIClient):
    """Phi-4 for reasoning-focused tasks"""
    
    API_KEY = "YOUR_AZURE_API_KEY"
    ENDPOINT = "https://YOUR_RESOURCE.openai.azure.com/"
    MODEL = "phi-4-reasoning"  # Replace with actual deployment name
    
    def __init__(self):
        super().__init__(self.API_KEY, self.ENDPOINT)
    
    def reasoning_generate(self, prompt: str) -> str:
        """Generate with Phi-4 reasoning capabilities"""
        messages = [
            {"role": "system", "content": "Provide step-by-step reasoning for your answer."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        return response.choices[0].message.content


# ============================================================
# Mistral-Medium-2505 - Azure
# ============================================================

class MistralMediumClient(AzureOpenAIClient):
    """Mistral Medium 2505 for balanced text generation"""
    
    API_KEY = "YOUR_AZURE_API_KEY"
    ENDPOINT = "https://YOUR_RESOURCE.openai.azure.com/"
    MODEL = "mistral-medium-2505"  # Replace with actual deployment name
    
    def __init__(self):
        super().__init__(self.API_KEY, self.ENDPOINT)
    
    def generate(self, prompt: str, context: str = None) -> str:
        """Generate using Mistral Medium"""
        messages = []
        
        if context:
            messages.append({"role": "system", "content": context})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        return response.choices[0].message.content


# ============================================================
# FLUX.1-Kontext-Pro (Image Generation) - Azure
# ============================================================

class FLUXKontextProClient(AzureOpenAIClient):
    """FLUX.1-Kontext-Pro for high-quality image generation"""
    
    API_KEY = "YOUR_AZURE_API_KEY"
    ENDPOINT = "https://YOUR_RESOURCE.openai.azure.com/"
    MODEL = "flux-1-kontext-pro"  # Replace with actual deployment name
    
    def __init__(self):
        super().__init__(self.API_KEY, self.ENDPOINT)
    
    def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        """
        Generate image using FLUX.1-Kontext-Pro
        
        Note: Azure image generation may use DALL-E or other image models.
        This is a placeholder - actual implementation depends on Azure offering.
        """
        # For image generation, we typically use the images API
        response = self.client.images.generate(
            model=self.MODEL,
            prompt=prompt,
            size=size,
            n=1
        )
        
        return response.data[0].url
```

---

### 6B.4 Groq Integration (Free Models - 8 API Keys)

Based on Groq Python SDK (2026):

```python
from groq import Groq
from typing import List, Dict, Any

class GroqClient:
    """Groq API client for free high-speed inference"""
    
    # 8 API keys available - rotate through them
    API_KEYS = [
        "gsk_your_first_key_here",
        "gsk_your_second_key_here",
        # ... up to 8 keys
    ]
    
    def __init__(self, api_key: str = None):
        # Use provided key or default to first available
        self.client = Groq(api_key=api_key or self.API_KEYS[0])
        self.current_key_index = 0
    
    def rotate_key(self):
        """Rotate to next available API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.API_KEYS)
        self.client = Groq(api_key=self.API_KEYS[self.current_key_index])
        print(f"Rotated to API key {self.current_key_index + 1}/{len(self.API_KEYS)}")
    
    def generate(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """Generate text with Groq model"""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            # Rate limit or other error - try rotating key
            if "rate_limit" in str(e).lower() or "429" in str(e):
                print(f"Rate limit hit, rotating key...")
                self.rotate_key()
                return self.generate(model, messages, temperature, max_tokens, **kwargs)
            raise


# Groq Model Options (Free Tier)
GROQ_MODELS = {
    "mixtral-8x7b-32768": "Mixtral 8x7B - Fast, good for general tasks",
    "llama-3.3-70b-versatile": "Llama 3.3 70B - High quality",
    "llama-3.1-70b-versatile": "Llama 3.1 70B - Reliable",
    "llama-3.1-8b-instant": "Llama 3.1 8B - Fast, lightweight",
    "gemma2-9b-it": "Gemma 2 9B - Google's model",
    "llama3-70b-8192": "Llama 3 70B - Original Llama 3",
    "llama3-8b-8192": "Llama 3 8B - Fast Llama",
}


class GroqLLM(GroqClient):
    """Easy-to-use Groq LLM wrapper"""
    
    def __init__(self, api_key: str = None):
        super().__init__(api_key)
    
    def chat(self, message: str, system_prompt: str = None, model: str = "mixtral-8x7b-32768") -> str:
        """Simple chat interface"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})
        
        return self.generate(model, messages)
    
    def code(self, prompt: str) -> str:
        """Code-specific generation"""
        return self.chat(
            prompt,
            system_prompt="You are a coding assistant. Write clean, efficient code.",
            model="mixtral-8x7b-32768"
        )
    
    def reason(self, prompt: str) -> str:
        """Reasoning-focused generation with higher tokens"""
        messages = [
            {"role": "system", "content": "Provide step-by-step reasoning for your answer."},
            {"role": "user", "content": prompt}
        ]
        
        return self.generate(
            "llama-3.3-70b-versatile",
            messages,
            max_tokens=8192
        )
```

---

### 6B.5 OpenRouter Integration (Free Models)

```python
import requests
from typing import List, Dict, Any

class OpenRouterClient:
    """OpenRouter API client for free models"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    API_KEY = "YOUR_OPENROUTER_API_KEY"  # Get from openrouter.ai
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or self.API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://barise.app",  # Required by OpenRouter
            "X-Title": "Barise Presentation Generator"
        }
    
    def generate(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Generate text using OpenRouter"""
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            f"{self.BASE_URL}/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None


# ============================================================
# Qwen3.6 Plus (Free) - OpenRouter
# ============================================================

class Qwen36PlusClient(OpenRouterClient):
    """Qwen3.6 Plus via OpenRouter - Free tier"""
    
    MODEL = "qwen/qwen3.6-plus-preview:free"
    
    def __init__(self):
        super().__init__()
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate using Qwen3.6 Plus"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.generate(self.MODEL, messages)
    
    def generate_structured(self, prompt: str, schema: dict) -> dict:
        """
        Generate structured output using OpenRouter's format parameter
        
        Note: May not be available for all free models
        """
        payload = {
            "model": self.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object", "schema": schema}
        }
        
        response = requests.post(
            f"{self.BASE_URL}/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            import json
            return json.loads(response.json()["choices"][0]["message"]["content"])
        return {"error": "Generation failed"}
```

---

### 6B.6 Model Routing & Cost Optimization

```python
from enum import Enum
from typing import Optional, Callable
import time

class ModelType(Enum):
    """Model categories for routing"""
    IMAGE_GENERATION = "image"
    CODE_GENERATION = "code"
    REASONING = "reasoning"
    GENERAL_TEXT = "general"
    FAST_TEXT = "fast"


class ModelRouter:
    """
    Intelligent model routing based on task type, cost, and availability.
    Implements the cost-optimization strategy from the architecture.
    """
    
    # Priority: Free > Subscription
    # Speed: Groq > Cloudflare > Azure
    
    ROUTING_RULES = {
        # Image Generation
        ModelType.IMAGE_GENERATION: {
            "primary": ("lucid-origin", "cloudflare"),  # Try free first
            "fallback": ("gemma-3-12b-it", "cloudflare"),
            "premium": ("FLUX.1-Kontext-pro", "azure"),  # Subscription
        },
        
        # Code Generation
        ModelType.CODE_GENERATION: {
            "primary": ("qwen2.5-coder-32b-instruct", "cloudflare"),
            "fallback": ("Groq mixtral", "groq"),
            "premium": ("gpt-4o-mini", "azure"),
        },
        
        # Reasoning
        ModelType.REASONING: {
            "primary": ("Groq llama-3.3-70b", "groq"),  # Fast, free
            "fallback": ("Phi-4-reasoning", "azure"),
            "premium": ("Kimi-K2-Thinking", "azure"),
        },
        
        # General Text
        ModelType.GENERAL_TEXT: {
            "primary": ("glm-4.7-flash", "cloudflare"),
            "fallback": ("qwen3.6-plus-preview", "openrouter"),
            "premium": ("DeepSeek-V3.2", "azure"),
        },
        
        # Fast/Quick tasks
        ModelType.FAST_TEXT: {
            "primary": ("Groq llama-3.1-8b", "groq"),
            "fallback": ("glm-4.7-flash", "cloudflare"),
        },
    }
    
    def __init__(self):
        self.clients = {}  # Lazy initialization
        self.daily_usage = {}  # Track daily limits
    
    def get_client(self, provider: str):
        """Get or initialize client for provider"""
        if provider not in self.clients:
            if provider == "cloudflare":
                # Initialize Cloudflare clients
                self.clients["cloudflare"] = {
                    "glm": GLM47FlashClient(),
                    "qwen_coder": QwenCoderClient(),
                    "gemma": Gemma3Client(),
                    "lucid": LucidOriginClient(),
                }
            elif provider == "azure":
                # Initialize Azure clients (lazy - requires API keys)
                pass
            elif provider == "groq":
                self.clients["groq"] = GroqLLM()
            elif provider == "openrouter":
                self.clients["openrouter"] = Qwen36PlusClient()
        
        return self.clients.get(provider)
    
    def route(self, task_type: ModelType, prompt: str, **kwargs) -> str:
        """
        Route request to appropriate model based on task type and availability
        """
        rules = self.ROUTING_RULES.get(task_type)
        
        # Try primary (free) first
        for priority in ["primary", "fallback", "premium"]:
            model_name, provider = rules.get(priority, (None, None))
            
            if not model_name:
                continue
            
            # Check daily limits
            if self.is_limit_reached(provider, model_name):
                print(f"Limit reached for {provider}/{model_name}, trying next...")
                continue
            
            try:
                client = self.get_client(provider)
                result = self._call_client(client, model_name, prompt, **kwargs)
                
                if result:
                    return result
                    
            except Exception as e:
                print(f"Error with {provider}/{model_name}: {e}")
                continue
        
        return "Error: All models failed or unavailable"
    
    def is_limit_reached(self, provider: str, model: str) -> bool:
        """Check if daily limit reached for model"""
        key = f"{provider}:{model}"
        usage = self.daily_usage.get(key, 0)
        
        limits = {
            "cloudflare:lucid-origin": 1000,
            "cloudflare:gemma-3-12b-it": 1000,
            "cloudflare:qwen2.5-coder-32b-instruct": 1000,
            "cloudflare:glm-4.7-flash": 1000,
        }
        
        limit = limits.get(key, 999999)  # Default to high limit
        return usage >= limit
    
    def _call_client(self, client, model: str, prompt: str, **kwargs) -> str:
        """Call appropriate client method based on model"""
        # Implementation depends on client type
        pass
```

---

### 6B.7 Usage Limits & Rate Management

```python
class RateLimitManager:
    """Manage rate limits and daily quotas for all providers"""
    
    # Daily limits per model (Cloudflare free tier)
    DAILY_LIMITS = {
        "lucid-origin": 1000,
        "gemma-3-12b-it": 1000,
        "qwen2.5-coder-32b-instruct": 1000,
        "glm-4.7-flash": 1000,
    }
    
    # Rate limits (requests per minute)
    RPM_LIMITS = {
        "cloudflare": 60,
        "groq": 30,
        "azure": 60,  # Depends on tier
        "openrouter": 50,
    }
    
    def __init__(self):
        self.usage = {model: 0 for model in self.DAILY_LIMITS}
        self.last_request_time = {}
    
    def can_make_request(self, model: str) -> bool:
        """Check if request can be made (within limits)"""
        if model in self.DAILY_LIMITS:
            if self.usage[model] >= self.DAILY_LIMITS[model]:
                return False
        
        return True
    
    def record_request(self, model: str):
        """Record request for tracking"""
        self.usage[model] = self.usage.get(model, 0) + 1
    
    def get_remaining(self, model: str) -> int:
        """Get remaining requests for model"""
        limit = self.DAILY_LIMITS.get(model, 999999)
        return max(0, limit - self.usage.get(model, 0))
```

---

## 7. PreTeXt Integration Architecture

PreTeXt is integrated at three critical points, based on chenglou/pretext (32.2k⭐) research:

### Phase 1: During DSL Generation (Code Agent Step 2)

```python
from pretext import prepare, layout

# Prepare text for measurement (one-time expensive operation)
prepared = prepare(
    "AI Infrastructure for the Next Billion Parameters",
    "bold 32px Inter"
)

# Fast layout computation (0.09ms per call)
{ height, lineCount } = layout(prepared, containerWidth, 40)

# If text overflows, either:
# - Suggest shorter copy
# - Switch to larger layout
# - Reduce font size within bounds
```

### Phase 2: During Component Compilation (Code Agent Step 3)

- PreTeXt measurements inform font-size decisions
- Automatic font reduction if text is close to overflow
- Minimum 24pt enforced (YC guidance)
- walkLineRanges() enables shrink-wrap layouts around images

### Phase 3: During Visual Validation (QA Agent Step 2)

- Fast pre-check (0.09ms) catches obvious overflow issues
- Runs before slower browser render step (~3s)
- Catches layout issues without DOM access

### Key PreTeXt APIs Used

| API | Purpose |
| :--- | :--- |
| `prepare(text, font)` | One-time text analysis + measurement |
| `layout(prepared, width, lineHeight)` | Fast height calculation |
| `prepareWithSegments()` | Rich segment structure for manual layout |
| `walkLineRanges()` | Binary search for optimal width |
| `layoutNextLine()` | Variable width line-by-line layout |

---

## 8. Reflective Generation Loop

Inspired by PPTAgent V2 (EMNLP 2025), the reflective loop replaces single-pass generation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REFLECTIVE GENERATION LOOP                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│   │ Generate │ -> │ Evaluate │ -> │  Refine  │ -> │Validate  │    │
│   │  (Agent)│    │  (QA)    │    │  (Agent) │    │  (Gate)  │    │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘    │
│        │               │               │               │              │
│        ▼               ▼               ▼               ▼              │
│   Output v1       Quality         Output v2      Quality            │
│                   Report                                Score        │
│        │               │               │               │              │
│        └───────────────┴───────────────┴───────────────┘              │
│                           │                                          │
│                           ▼                                          │
│                    Max 3 iterations                                   │
│                    or until 85% quality                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Loop Implementation

1. **Generation**: Orchestrator dispatches work to agents
2. **Evaluation**: QA Agent produces structured quality report with specific issues
3. **Refinement**: If quality < 85%, Orchestrator routes specific issues back to responsible agent
4. **Validation**: Check quality gates again
5. **Iteration**: Repeat up to 3 cycles
6. **Output**: Best version + improvement log

### Quality Report Structure

```json
{
  "qualityScore": 72,
  "issues": [
    {
      "type": "text-overflow",
      "location": "slide-3, bullet-2",
      "severity": "high",
      "suggestion": "Reduce text from 45 chars to 30 chars"
    },
    {
      "type": "contrast",
      "location": "slide-5, heading",
      "severity": "medium",
      "suggestion": "Increase contrast ratio to 4.5:1"
    }
  ],
  "iteration": 2,
  "antiAislopCompliance": true
}
```

---

## 9. Visual Style Discovery System

Adopted from Frontend Slides (10k⭐), this transforms theme selection:

```
┌─────────────────────────────────────────────────────────────────────┐
│                  VISUAL STYLE DISCOVERY UX                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   User: "Create pitch deck for AI startup"                          │
│                                                                      │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│   │  Preview A  │  │  Preview B  │  │  Preview C  │               │
│   │             │  │             │  │             │               │
│   │ Bold Signal │  │ Electric    │  │ Swiss       │               │
│   │ (Dark)      │  │ Studio      │  │ Modern      │               │
│   │             │  │ (Dark)      │  │ (Light)     │               │
│   └─────────────┘  └─────────────┘  └─────────────┘               │
│        ✓              ○                ○                            │
│      [SELECT]                                                     │
│                                                                      │
│   → System applies selected style across all slides               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Implementation

1. CEO Agent determines archetype (Pitch Deck)
2. Designer Agent generates 3 preview slides with different presets
3. User selects preferred style via MCP tool
4. System applies style consistently across deck
5. Anti-AI-slop processor ensures non-generic aesthetics

---

## 10. Pitch Deck Domain Intelligence

Encodes YC/Sequoia/DocSend rules as first-class constraints:

### YC Structure (12 Slides)

1. Title/One-Liner
2. Problem
3. Solution
4. Why Now
5. Market Size (bottom-up only)
6. Product/Demo
7. Traction
8. Business Model
9. Competition
10. Team
11. Ask
12. Appendix

### DocSend Analytics Rules

| Rule | Source | Action |
| :--- | :--- | :--- |
| Avg viewing time 2m24s | DocSend | Front-load key info |
| Team slide gets 1m2s | DocSend | Enhanced team slide generation |
| 10-15 slides optimal | DocSend | Cap at 15, prefer 10-12 |
| Data-rich = 3x engagement | DocSend | 30%+ slides need charts/data |
| Real screenshots > mockups | DocSend | Prioritize product images |

### Anti-Pitfall Rules

| Pitfall | Rule |
| :--- | :--- |
| Too much text | Max 6 bullets/slide, 15 words/bullet |
| Jargon | Generalist-readable language |
| "No competition" | Require competitive positioning |
| Top-down market | Bottom-up only (SAM/SOM calculation) |
| Missing "Why Now" | Mandatory slide for investor decks |
| Weak team | Credentials + photos required |
| Animations | YC: No transitions |

---

## 11. Enhanced Export Pipeline

| Format | Technology | Quality | Editability | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **PPTX (native)** | PptxGenJS | High | Full | Editable, investor sharing |
| **PPTX (visual)** | Puppeteer + PptxGenJS | Very High | None (images) | Design-critical |
| **PDF** | Puppeteer page.pdf() | Perfect | None | Read-only, printing |
| **HTML** | Inline bundler | High | Full source | Web sharing |
| **React** | Compiled from DSL | High | Full source | Canvas editor, embedding |
| **PNG** | Puppeteer screenshot | High | None | Social media |
| **Google Slides** | Google API | High | Full | Enterprise |

---

## 12. Agent Communication Protocol

Uses a **Context Board** (shared JSON document):

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTEXT BOARD STRUCTURE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   {                                                                 │
│     "orchestrator": { "task": "...", "status": "running" },       │
│     "ceo_agent": { "outline": {...}, "archetype": "pitch-deck" },  │
│     "researcher": { "findings": [...], "citations": [...] },       │
│     "designer": { "theme": "...", "preset": "bold-signal" },       │
│     "assembler": { "pptx_status": "complete" },                     │
│     "code_agent": { "dsl_status": "generating", "components": [] },│
│     "qa_agent": { "quality_score": 78, "issues": [...] }            │
│   }                                                                 │
│                                                                      │
│   Priority System:                                                  │
│   1. Domain rules (pitch deck constraints) > aesthetic preferences  │
│   2. User requirements > auto-generated suggestions                 │
│   3. Quality gate failures > completion signals                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **Async polling**: Agents poll Context Board for new inputs
2. **Parallel execution**: Researcher and Designer can work simultaneously
3. **Ordering guarantees**: Assembler waits for CEO outline + Researcher data
4. **Conflict resolution**: Orchestrator mediates via priority system

---

## 13. Tool Specification (65+ Tools)

### Category 1: Presentation Lifecycle (6)
- create_presentation, open_presentation, save_presentation
- get_presentation_info, set_core_properties, delete_presentation

### Category 2: Slide Operations (8)
- add_slide, delete_slide, reorder_slides, duplicate_slide
- set_slide_background, get_slide_content, set_transition, set_notes

### Category 3: Content & Text (6)
- populate_placeholder, add_bullet_points, manage_text
- add_text_box, find_replace, extract_slide_text

### Category 4: Visual Elements (8)
- add_image, add_shape, add_chart, add_table
- apply_picture_effects, crop_image, set_shape_style, add_hyperlink

### Category 5: Theme & Design (6)
- apply_theme, generate_theme, create_custom_theme
- list_themes, extract_theme, discover_style (NEW)

### Category 6: Image Generation (4)
- generate_image, generate_hero_image, search_stock_images, upload_custom_image

### Category 7: Research & Data (4)
- research_topic, extract_document, search_web, analyze_data

### Category 8: Quality & Validation (4)
- validate_content, check_branding, validate_sources, get_improvements

### Category 9: Code Agent (10) (NEW)
- generate_slide_dsl, compile_react_slides, measure_text_fit
- validate_slide_dsl, export_to_pptx, export_to_pdf, export_to_html
- generate_diagram, preview_slides, apply_anti_slop

### Category 10: Diagram Integration (3) (NEW)
- create_excalidraw_diagram, create_mermaid_diagram, embed_diagram_in_slide

### Category 11: Export Formats (6) (NEW)
- export_pptx, export_pdf, export_google_slides
- export_revealjs, export_slidev, export_images

### Category 12: Template Management (10) (NEW)
- load_template, register_template, list_templates
- extract_template_layouts, validate_template, create_from_schema
- clone_template, export_template, import_template, get_template_metadata

---

## 14. Theme System

### 16 Color Schemes (Expanded)

| Theme | Primary | Secondary | Accent | Best For |
| :--- | :--- | :--- | :--- | :--- |
| Modern Blue | #0078D4 | #106EBE | #FFB900 | Tech, SaaS |
| Corporate Gray | #605E5C | #323130 | #0078D4 | Consulting |
| Elegant Green | #107C10 | #0B6A43 | #00B294 | Sustainability |
| Warm Red | #D83B01 | #A4262C | #FF8C00 | Sales |
| Dark Developer | #0F172A | #1E293B | #38BDF8 | Dev tools |
| Bold Signal | #FF6B35 | #004E98 | #1A936F | Startup |
| Electric Studio | #7B2FF7 | #C000FF | #00F5FF | Futuristic |
| Neon Cyber | #FF00FF | #00FFFF | #FFFF00 | Gaming |
| Creative Voltage | #2D3748 | #4A5568 | #ED8936 | Creative |
| Soft Lavender | #667EEA | #764BA2 | #F687B3 | Wellness |
| Ocean Deep | #0C4A6E | #155E75 | #06B6D4 | Finance |
| Forest Premium | #14532D | #166534 | #22C55E | Nature |
| Sunset Gradient | #F97316 | #EA580C | #FBBF24 | Food |
| Midnight Purple | #4C1D95 | #5B21B6 | #A855F7 | Entertainment |
| Slate Professional | #334155 | #475569 | #94A3B8 | Legal |
| Amber Enterprise | #92400E | #B45309 | #F59E0B | Real Estate |

### 12 Curated Style Presets (Anti-AI-Slop)

| Preset | Category | Character |
| :--- | :--- | :--- |
| **Bold Signal** | Dark | High contrast, dynamic, accent glows |
| **Electric Studio** | Dark | Futuristic, tech, neon accents |
| **Dark Botanical** | Dark | Natural, sophisticated, organic shapes |
| **Notebook Tabs** | Light | Organized, clean, tab dividers |
| **Pastel Geometry** | Light | Soft, approachable, geometric |
| **Swiss Modern** | Specialty | Minimal, precise, grid system |
| **Terminal Green** | Specialty | Technical, hacker, phosphor |
| **Paper and Ink** | Specialty | Editorial, classic, ink texture |
| **Neon Cyber** | Specialty | Cyberpunk, gaming aesthetic |
| **Creative Voltage** | Dark | Creative, high energy |
| **Vintage Editorial** | Light | Classic, publication-style |
| **Split Pastel** | Light | Modern, dual-tone |

---

## 15. Quality Gates (Enhanced)

### Content Quality Rules
| Rule | Action |
| :--- | :--- |
| Fluff detection | Block: "revolutionary", "cutting-edge", "game-changing" |
| Source requirement | All data points require citation |
| Density check | Max 6 bullets/slide, 15 words/bullet |
| Investor requirements | TAM/SAM/SOM for market slides |

### Design Quality Rules
| Rule | Action |
| :--- | :--- |
| Contrast ratio | ≥4.5:1 for readability |
| Font consistency | Same fonts across all slides |
| Image resolution | ≥1920×1080 |
| Spacing uniformity | Consistent margins and padding |
| Text overflow | PreTeXt validation before render |
| Anti-AI-slop | Must use curated preset, no generic gradients |

### Pitch Deck Specific Rules
| Rule | Action |
| :--- | :--- |
| Slide count | Max 15, prefer 10-12 |
| First 3 slides | Must pass "3-second scan test" |
| Font size | Min 24pt |
| Market sizing | Bottom-up methodology only |
| Team slide | Credentials + photos required |
| Animations | YC: No transitions allowed |

### Self-Evolution Loop
| Phase | Action |
| :--- | :--- |
| 1. Initial Generation | Generate first draft |
| 2. Self-Critique | Evaluate against quality gates |
| 3. Iteration | Apply fixes to identified issues |
| 4. Re-validation | Check against gates again |
| 5. Max Iterations | Stop after 3 attempts |
| 6. Final Output | Best version + improvement log |

---

## 16. Security Architecture

### Layer 1: Local Context Isolation
- MCP server runs locally (stdio transport)
- Sensitive data processed locally
- Only summaries sent to LLM

### Layer 2: Browser Daemon Security
- `localhost-only` binding (no external access)
- Bearer token authentication
- 30-minute idle timeout

### Layer 3: Governance & Auditing
- Every tool invocation logged
- STRIDE/OWASP audit capability
- PII detection in generated content

### Layer 4: API Key Management
- Environment variable only
- "Bring Your Own Key" (BYOK) for users
- No hardcoded credentials

---

## 17. Storage Architecture

| Storage Type | Technology | Purpose |
| :--- | :--- | :--- |
| Vector Store | Chroma (embedded) | Presentation embeddings, similarity search |
| Document Store | MongoDB | Presentations, slides, themes |
| Object Storage | S3 / MinIO | Generated images, exported files |
| Cache | Redis | LLM responses, theme configs, sessions |
| File System | Local / Network | Template assets, working files |

---

## 18. Implementation Phases (14 Weeks)

| Phase | Weeks | Deliverables | Dependencies |
| :--- | :--- | :--- | :--- |
| **Phase 1: Foundation** | 1-2 | FastMCP server (stdio/HTTP+SSE); 34 core tools; basic CRUD; Chroma setup | None |
| **Phase 2: Agent Core** | 3-5 | Orchestrator with Context Board; CEO Agent; Researcher Agent; Agent Communication Protocol | Phase 1 |
| **Phase 3: Design Intelligence** | 5-7 | Designer Agent; 16 color schemes; 12 style presets; Visual Style Discovery; AI Template Selector | Phase 2 |
| **Phase 4: Code Agent** | 7-9 | Slide DSL schema (Zod); React compiler; PreTeXt integration; PptxGenJS export; Puppeteer PDF; Zero-dep HTML | Phase 2 + 3 |
| **Phase 5: Quality & Preview** | 9-11 | QA Agent; Browser daemon (Playwright); Live preview; Reflective Loop (2-3 cycles); Anti-AI-slop | Phase 3 + 4 |
| **Phase 6: Diagrams** | 11-12 | Excalidraw integration; Mermaid diagrams; D3.js/Recharts for data viz | Phase 4 |
| **Phase 7: Domain Intelligence** | 12-13 | Pitch Deck rules (YC, DocSend); Canvas editor (Konva.js); Deployment archetypes | Phase 5 |
| **Phase 8: Production** | 13-14 | Error handling; Performance; Testing; Documentation; Docker deployment | All phases |

---

## 19. Success Metrics

| Metric | Target |
| :--- | :--- |
| JSON validity (LLM output) | >95% |
| Image generation success | >90% (with fallback) |
| Export success rate | >99% |
| Quality pass rate (first attempt) | >75% |
| Quality pass rate (after reflective loop) | >90% |
| Content generation time | ≤5s/slide |
| Full deck generation (10 slides) | <60s |
| PreTeXt validation time | <1ms/text |
| Browser preview latency | <1s/command |

---

## 20. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| PreTeXt SSR not available | High | Medium | Client-side validation; Playwright fallback |
| Python/Node hybrid complexity | Medium | Medium | Clear interface boundaries |
| PptxGenJS vs python-pptx | Low | Medium | PptxGenJS for Code Agent; python-pptx for Assembler |
| Quality gate false positives | Medium | Low | Tunable threshold, user override |

---

## 21. Differentiation Summary

| Feature | Our MCP | Gamma | Beautiful.ai | Presenton |
| :--- | :--- | :--- | :--- | :--- |
| **Agent Orchestration** | 6 specialized | Single prompt | Single prompt | Multi-agent |
| **Code Agent** | React/Tailwind | None | None | None |
| **Reflective Loop** | 2-3 iterations | None | None | None |
| **PreTeXt Integration** | DOM-free measurement | None | None | None |
| **Visual Discovery** | 3-preview selection | Basic | Basic | None |
| **Anti-AI-Slop** | 12 curated presets | None | None | None |
| **Pitch Deck Domain** | YC/Sequoia/DocSend | Generic | Generic | Generic |
| **Format Support** | PPTX/PDF/HTML/React/Google | PPTX/PDF | PPTX | PPTX/HTML |
| **Open Source** | Full | No | No | Yes |

---

## 22. Reference Integration Analysis

| Reference | Stars | What Was Adopted |
| :--- | :--- | :--- |
| **PreTeXt** (chenglou/pretext) | 32.2k | DOM-free text measurement; two-phase API (prepare/layout); walkLineRanges for shrink-wrap |
| **OpenPencil** (open-pencil) | 3.9k | 90+ MCP tools benchmark; Yoga WASM; design-to-code export pattern |
| **yoyo-evolve** (yologdev) | 1.4k | Multi-provider architecture (12 providers); streaming REPL; subagent pattern |
| **Frontend Slides** (zarazhangrui) | 10k | Visual Style Discovery; 12 curated presets; anti-AI-slop design |
| **PPTAgent V2** (EMNLP 2025) | N/A | Reflective generation loop; generate-evaluate-refine cycle |
| **hugohe3/ppt-master** | 3,526 | Template-based PPTX generation; 15 examples; native editable output |
| **m3dev/pptx-template** | 113 | JSON-based template engine pattern; template + JSON data |
| **python-pptx-templater** | 43 | Layout template filling; customizable presentations |
| **pptx-templatex** (PyPI) | N/A | Slide copying + placeholder replacement |
| **powerpoint-template-system** (PyPI) | N/A | Business presentation templates; modern styling |
| **deckbuilder** (teknologika) | 7 | MCP server for PPTX; content-first design philosophy |
| **SlideCoder** (EMNLP 2025) | N/A | Layout-aware RAG-enhanced hierarchical slide generation |
| **presenton/presenton** | 4,513 | Custom template system; HTML + Tailwind + Zod schema |
| **slide-generator** (PyPI) | N/A | Convert presentation outlines to PPTX without LLM |
| **office-templates** (PyPI) | N/A | Generate PPTX from template files with flexible composition |

---

## 📝 Next Steps

1. Initialize project structure (Python MCP server + TypeScript Code Agent)
2. Implement core MCP tools (34 tools, Phase 1)
3. Integrate PreTeXt for text measurement
4. Build Agent Communication Protocol
5. Develop Slide DSL schema
6. Implement Visual Style Discovery
7. Add Reflective Generation Loop
8. Test with real-world pitch deck scenarios

---

**Document Version**: 5.1 (Complete Standalone Implementation + Template System)
**Status**: Ready for Implementation
**Architecture**: Production-Grade MCP Server with 6 Specialized Agents + Reflective Loop + Template Generation System