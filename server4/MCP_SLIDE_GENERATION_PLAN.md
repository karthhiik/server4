# 🎯 Premium Slide Generation MCP — Comprehensive Plan

## Executive Summary

This document outlines a world-class MCP (Model Context Protocol) server for AI-powered presentation generation. The plan synthesizes deep research from 20+ GitHub repositories and latest web technologies.

---

## 🔬 Research Findings Summary

### Key Architecture Patterns Discovered

| Repository | Stars | Architecture | Key Innovation |
|------------|-------|--------------|-----------------|
| **Presenton** | 4.5k | Multi-Agent + MCP | API-first, multi-provider (OpenAI/Gemini/Claude/Ollama), Docker + Desktop |
| **presentation-ai** | 2.7k | Outline-first workflow | 38 themes, real-time generation, local models (Ollama/LM Studio) |
| **SlideBot-AI** | 981 | Pipeline-based | Document upload, chart embedding, multi-page iterative refinement |
| **PPTist** | 8.7k | Canvas-based editor | Full web PPT editor, AI integration, element-level editing |
| **pptx-mcp** | — | MCP-native | 40 tools, 32 slide types, 12 chart types, brand presets |
| **SlideSpeak** | 92 | RAG-based | Document understanding, vector search, PPT summarization |
| **ai-multi-agent-builder** | — | Azure AI Agents | Multi-agent orchestration, real-time collaboration |

### Common Features Across All Systems

1. **Outline → Content → Design** — Two-stage generation
2. **Multi-provider LLM** — OpenAI, Claude, Gemini, Ollama fallback
3. **Theme/Style system** — Template-based, customizable
4. **Image generation** — DALL-E, Stable Diffusion, Gemini, stock images
5. **Export formats** — PPTX, PDF, HTML, images

### Gaps in Current Systems

- ❌ No robust multi-agent orchestration for slides
- ❌ Limited real-time collaboration
- ❌ Poor offline/local-first capabilities
- ❌ No unified MCP with all capabilities
- ❌ Limited design quality validation
- ❌ No native canvas editing with AI

---

## 🏗️ Proposed MCP Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SLIDE GENERATION MCP SERVER                         │
│                                                                             │
│   Protocol: Model Context Protocol (MCP)                                   │
│   Framework: FastMCP + FastAPI                                            │
│   Language: Python 3.11+                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│   RESEARCH    │         │   GENERATION  │         │   RENDERING   │
│    AGENT      │         │    AGENTS     │         │    ENGINE     │
│               │         │               │         │               │
│ • Web Search  │         │ • Outline     │         │ • Canvas      │
│ • Document    │         │   Agent      │         │ • PPTX        │
│   Parser      │         │ • Content     │         │ • PDF         │
│ • Data Extract│         │   Agent       │         │ • HTML        │
│ • RAG Engine  │         │ • Design      │         │ • Images      │
│               │         │   Agent       │         │               │
└───────────────┘         │ • Image      │         └───────────────┘
        │                 │   Agent       │
        ▼                 └───────────────┘
┌───────────────┐                 │
│   KNOWLEDGE   │                 ▼
│    STORAGE    │         ┌───────────────┐
│               │         │   QUALITY     │
│ • Vector DB   │         │   GUARDS     │
│ • Document    │         │               │
│   Store       │         │ • Content     │
│ • Cache       │         │ • Design     │
└───────────────┘         │ • Brand      │
                           └───────────────┘
```

---

## 🔧 MCP Tools Specification

### Tool Categories

#### 1. Presentation Management Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `create_presentation` | Create new presentation | topic, purpose, audience, slide_count, style |
| `list_presentations` | List all presentations | filters, pagination |
| `get_presentation` | Get presentation by ID | presentation_id |
| `update_presentation` | Update presentation | presentation_id, updates |
| `delete_presentation` | Delete presentation | presentation_id |

#### 2. Outline & Content Generation Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `generate_outline` | Generate presentation outline | topic, purpose, slide_count, research_context |
| `refine_outline` | Refine existing outline | outline_id, feedback |
| `generate_slide_content` | Generate content for single slide | slide_id, layout, context, writing_style |
| `generate_all_slides` | Generate all slides content | outline_id, parallel |
| `improve_content` | AI improve existing content | content, improvement_type |

#### 3. Design & Theme Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `apply_theme` | Apply theme to presentation | presentation_id, theme_id |
| `generate_theme` | Generate custom theme | brand_colors, industry, style_preferences |
| `list_themes` | List available themes | category, search |
| `create_custom_theme` | Create custom theme | theme_config |
| `analyze_design_quality` | Analyze design quality | presentation_id |

#### 4. Image Generation Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `generate_slide_image` | Generate image for slide | slide_id, prompt, style |
| `generate_hero_image` | Generate hero/main image | presentation_id, topic |
| `search_stock_images` | Search stock images | query, count |
| `upload_custom_image` | Upload custom image | file_path, slide_id |

#### 5. Canvas & Editing Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `render_canvas` | Render presentation as canvas | presentation_id, format |
| `get_canvas_state` | Get current canvas state | presentation_id |
| `update_canvas_element` | Update element in canvas | element_id, properties |
| `add_canvas_element` | Add element to canvas | slide_id, element_type, properties |
| `delete_canvas_element` | Delete element from canvas | element_id |

#### 6. Export Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `export_pptx` | Export to PowerPoint | presentation_id, options |
| `export_pdf` | Export to PDF | presentation_id, quality |
| `export_html` | Export to HTML | presentation_id, template |
| `export_images` | Export as images | presentation_id, format, resolution |

#### 7. Research & Data Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `research_topic` | Research topic comprehensively | topic, depth, sources |
| `extract_document` | Extract content from documents | file_path, file_type |
| `search_web` | Search web for information | query, num_results |
| `analyze_data` | Analyze data for charts | data_source, analysis_type |

#### 8. Quality & Validation Tools

| Tool | Description | Parameters |
|------|--------------|------------|
| `validate_content` | Validate content quality | content, rules |
| `check_branding` | Check brand compliance | presentation_id, brand_guidelines |
| `validate_sources` | Validate source citations | content |
| `get_improvements` | Get improvement suggestions | presentation_id |

---

## 🤖 Agent System Design

### Agent 1: Research Agent

**Purpose**: Gather comprehensive research for presentation topic

**Capabilities**:
- Web search ( Tavily, DuckDuckGo)
- Document parsing (PDF, Word, Excel, PPT)
- Data extraction and structuring
- RAG-based knowledge retrieval
- Competitor analysis

**Workflow**:
```
Input: topic, purpose, audience
  ↓
1. Generate search queries based on topic
2. Execute parallel searches
3. Parse and extract key information
4. Structure data points for charts
5. Synthesize research brief
Output: Research context with citations
```

### Agent 2: Outline Agent

**Purpose**: Generate structured presentation outline

**Capabilities**:
- Narrative structure planning
- Slide sequence optimization
- Content distribution across slides
- Purpose-aware organization
- Audience-appropriate depth

**Workflow**:
```
Input: topic, research_context, purpose, audience, slide_count
  ↓
1. Analyze presentation type (pitch, report, educational)
2. Determine narrative arc
3. Generate slide structure
4. Assign content distribution
5. Validate completeness
Output: Structured outline with slide purposes
```

### Agent 3: Content Agent

**Purpose**: Generate slide content with quality validation

**Capabilities**:
- Layout-specific content generation
- Quality guard enforcement
- Source attribution
- Writing style adaptation
- Iterative refinement

**Workflow**:
```
Input: slide_specification, research_context, writing_style
  ↓
1. Determine layout requirements
2. Generate content with constraints
3. Run quality guards (fluff, sources, density)
4. Apply writing style transformations
5. Validate against layout constraints
Output: Validated slide content
```

### Agent 4: Design Agent

**Purpose**: Apply visual design and theming

**Capabilities**:
- Theme selection and application
- Layout optimization
- Color scheme management
- Typography selection
- Image placement

**Workflow**:
```
Input: slide_content, theme, brand_guidelines
  ↓
1. Select appropriate theme
2. Apply color scheme
3. Optimize layout for content
4. Place and style images
5. Ensure brand consistency
Output: Designed slides ready for export
```

### Agent 5: Image Agent

**Purpose**: Generate and manage slide images

**Capabilities**:
- AI image generation (multi-provider)
- Stock image search
- Image optimization
- Style consistency

**Workflow**:
```
Input: slide_content, image_style, theme
  ↓
1. Generate image prompts from content
2. Select image provider (DALL-E, Stable Diffusion, etc.)
3. Generate images with retries
4. Optimize for presentation
5. Apply theme styling
Output: Styled images for slides
```

---

## 📊 Data Models

### Presentation Model

```python
class Presentation(BaseModel):
    id: str
    title: str
    topic: str
    purpose: str
    audience: str
    writing_style: str
    slides: List[Slide]
    theme: Theme
    status: PresentationStatus
    created_at: datetime
    updated_at: datetime
```

### Slide Model

```python
class Slide(BaseModel):
    id: str
    index: int
    layout: SlideLayout
    content: SlideContent
    design: SlideDesign
    image_url: Optional[str]
    notes: Optional[str]
    quality_warnings: List[str]
```

### Layout Types (12 Core Layouts)

1. `title-hero` — Hero title with subtitle
2. `bullets` — Bulleted list content
3. `two-column` — Two column comparison
4. `bullets-with-image` — Bullets with image
5. `chart` — Data visualization
6. `comparison` — Side-by-side comparison
7. `timeline` — Temporal sequence
8. `quote` — Quote with attribution
9. `team-grid` — Team member cards
10. `kpi-dashboard` — Metrics dashboard
11. `full-image` — Full background image
12. `blank` — Empty canvas

---

## 🎨 Theme System

### Built-in Themes (40+)

Categories:
- **Corporate**: Modern Blue, Executive Gray, Enterprise Green
- **Creative**: Vibrant Gradient, Minimal Dark, Neon Tech
- **Educational**: Academic Blue, Clean White, Text-focused
- **Startup**: YC Style, Pitch Deck, Investor Ready
- **Nature**: Eco Green, Earth Tones, Organic

### Theme Configuration

```python
class Theme(BaseModel):
    id: str
    name: str
    colors: ThemeColors  # primary, secondary, accent, background, text
    fonts: ThemeFonts    # heading, body, accent
    layouts: Dict[str, LayoutConfig]
    effects: ThemeEffects  # animations, transitions
   适用场景: List[str]
```

---

## 🔄 Quality Gates

### Content Quality Guard

| Rule | Validation |
|------|-------------|
| Fluff detection | Block: "revolutionary", "cutting-edge", "game-changing" |
| Source requirement | All data points require citation |
| Density check | Max bullets: 6, max words/bullet: 15 |
| Investor requirements | Market slides need TAM/SAM/SOM |

### Design Quality Guard

| Rule | Validation |
|------|-------------|
| Brand compliance | Colors within brand guidelines |
| Accessibility | Contrast ratio ≥ 4.5:1 |
| Consistency | Same fonts, spacing across slides |
| Image quality | Resolution ≥ 1920x1080 |

---

## 🚀 Implementation Phases

### Phase 1: Core MCP Server (Week 1-2)

- [ ] FastMCP server setup
- [ ] Basic tool implementations
- [ ] LLM integration (multi-provider)
- [ ] Simple PPTX generation

### Phase 2: Agent System (Week 3-4)

- [ ] Research Agent implementation
- [ ] Outline Agent implementation
- [ ] Content Agent with quality guards
- [ ] Basic theme system

### Phase 3: Advanced Features (Week 5-6)

- [ ] Design Agent with layout optimization
- [ ] Image Agent with multi-provider fallback
- [ ] Canvas rendering engine
- [ ] Export pipeline (PPTX, PDF, HTML)

### Phase 4: Premium Features (Week 7-8)

- [ ] Real-time collaboration
- [ ] Advanced animations
- [ ] Brand compliance checking
- [ ] RAG-based document understanding

### Phase 5: Production Ready (Week 9-10)

- [ ] Performance optimization
- [ ] Error handling and retry logic
- [ ] Comprehensive testing
- [ ] Documentation and examples

---

## 💾 Storage Architecture

### Vector Store (Chroma/Weaviate)

- Presentation embeddings
- Content search
- Similarity matching

### Document Store (MongoDB/PostgreSQL)

- Presentations
- Slides
- Themes
- User data

### Object Storage (S3/MinIO)

- Generated images
- Exported files
- Template assets

### Cache (Redis)

- LLM responses
- Theme configurations
- Session state

---

## 🔐 Security Considerations

- API key management via environment variables
- Input sanitization for prompts
- Rate limiting per user
- Content filtering for harmful outputs
- Secure file handling for uploads

---

## 📈 Success Metrics

| Metric | Target |
|--------|--------|
| Slide generation accuracy | >95% valid JSON |
| Image generation success | >90% with fallback |
| Export success rate | >99% |
| Quality pass rate | >85% first attempt |
| Response time (content) | <5s per slide |
| Response time (full deck) | <60s for 10 slides |

---

## 🎯 Differentiation from Existing Solutions

| Feature | Our MCP | Presenton | presentation-ai | pptx-mcp |
|---------|---------|-----------|-----------------|-----------|
| **Agent orchestration** | ✅ 5 specialized agents | Partial | Basic | ❌ |
| **Multi-provider LLM** | ✅ 5+ providers | ✅ 4 providers | ✅ 3 providers | ❌ |
| **Canvas editing** | ✅ Full canvas | Limited | ❌ | ❌ |
| **Quality guards** | ✅ Comprehensive | Basic | ❌ | ❌ |
| **Design review** | ✅ Built-in | ❌ | ❌ | ❌ |
| **RAG documents** | ✅ With vector store | ❌ | Limited | ❌ |
| **MCP-native** | ✅ Full MCP | ✅ MCP | ❌ | ✅ |
| **Offline mode** | ✅ With Ollama | ✅ Ollama | ✅ Ollama | ❌ |

---

## 🛠️ Tech Stack

```
Language:        Python 3.11+
MCP Framework:   FastMCP
Web Framework:   FastAPI
LLM Clients:     OpenAI, Anthropic, Google, Cloudflare, Groq
Image Gen:       DALL-E, Stable Diffusion, Lucid, Phoenix
Vector Store:    Chroma, Weaviate
Document Store:  MongoDB
Cache:           Redis
Storage:         S3, MinIO
PPTX Library:    python-pptx
HTML Render:     Custom + Tailwind
Testing:         pytest, pytest-asyncio
```

---

## 📝 Next Steps

1. **Initialize MCP server** with FastMCP
2. **Implement core tools** (presentation CRUD)
3. **Integrate LLM clients** with fallback chain
4. **Build agent system** sequentially
5. **Create theme engine** with 40+ themes
6. **Implement export pipeline**
7. **Add quality guards**
8. **Test and iterate**

---

**Document Version**: 1.0  
**Created**: 2026-04-02  
**Status**: Ready for Implementation