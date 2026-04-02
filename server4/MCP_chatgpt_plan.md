🎯 Premium Slide Generation MCP — Comprehensive Plan
Executive Summary
Modern AI slide-generation platforms share common goals: turning ideas or documents into polished presentations. From our research of 20+ open-source projects (e.g. Presenton, Allweone’s Presentation-AI, SlideBot-AI, PPTist, Paper2Any, etc.), we distilled best practices and gaps. Core strengths include outline-driven workflows, multi-LLM support (OpenAI/Gemini/Claude/Ollama), extensive theming systems, and AI image generation (DALL·E, Stable Diffusion, Gemini, stock imagery). However, no single solution unifies all needs. Key missing pieces are robust multi-agent orchestration, real-time collaboration, offline/local operation, integrated design QA, and native canvas editing.

Our proposed MCP (Model Context Protocol) server combines the best of these systems. It features a swarm-agent architecture (a coordinator plus specialized AI agents) and a rich toolset for outline planning, content writing, design theming, image generation, and export. We leverage a vector store + document DB for knowledge retrieval and structured storage. To ensure brand and content quality, we add automated quality gates. This plan is built from deep analysis of existing projects, ensuring we exceed current capabilities (e.g. proprietary tools) in a fully open, MCP-native design.

🔬 Research Findings & Patterns
We analyzed key open projects and distilled their architectures and innovations:

Presenton (4.5k★) – A self-hosted multi-agent system with built-in MCP server for presentations
. It uses an orchestrator (“o1-mini”) and expert agents (e.g. GPT-4o, Claude) coordinated via Azure’s Semantic Kernel
. Features: API-first, multi-provider LLM support (OpenAI, Gemini, Claude, Ollama)
, template/theme creation, PPTX/PDF export, and can run fully locally (with Docker or Electron)
.
Allweone Presentation-AI (2.7k★) – An outline-first workflow (user reviews AI-generated outline, then refines into slides)
. Provides 38 built-in themes and custom theming
, real-time slide preview, and PPTX export
. It supports multiple LLMs (cloud or local) and even web search. Notably, it lists “Real-Time Collaboration – Not Started”
, highlighting a current gap.
SlideBot-AI (~1k★) – A pipeline-based generator (Chinese project “SlideFlow AI”). It ingests ideas, transcripts audio, parses docs (PDF/Word/PPT/Excel) for content
, then generates an outline and slides. Key innovations: voice-to-text transcription and document understanding
, per-slide style presets, and interactive outline/design editing (AI updates instantly in response to user feedback)
. Outputs are rendered as images (not editable PPT shapes).
GitHub - tonyqinatcmu/SlideBot-AI:  SlideBot AI - AI-Powered Presentation Generator · GitHub
Figure: AI-driven slide generation UI (SlideFlow AI). Users input a topic, AI crafts an outline and slides; here the interface shows live outline editing and slide previews
.
PPTist (8.5k★) – A full-featured web-based slide editor (Vue/TS). Not focused on AI generation, but includes basic AI slide creation alongside an almost complete PowerPoint clone
. Supports rich canvas editing: add text, images, shapes, charts, animations, etc. Exports to PPTX/PDF. This shows the value of a robust canvas UI for post-generation editing and fine-tuning.
Paper2Any (2.1k★) – A research-focused pipeline converting papers/notes into slides (among other outputs)
. It’s RAG-driven: ingest PDF/text → GPT-powered outline/content → generate slides. Unique features: editable PPTX output with tables/figures inserted, layout-preserving PDF→PPT, image-to-slides, and an in-browser canvas editor. The demo shows multi-slide gallery and inline text/image editing
.
Azure AI Multi-Agent Demo (48★) – A sample project using Azure’s Semantic Kernel to coordinate multiple agents
. An “orchestrator” agent spawns content/planning agents (Claudes/GPTs) for each task, then assembles a PPTX. While lightweight, it illustrates the swarm agent pattern: dynamic agent creation, context sharing, and tool-based plugins
.
SlideSpeak Backend (92★) – Focused on RAG with LLMs for presentations. Uses LlamaIndex/GPT and Pinecone vector store to summarize/upload PPTs and answer questions
. Shows an architecture with MongoDB (docs), Pinecone (embeddings), and file storage (S3) for research-driven slide content
.
Common Features
From these projects, we identified recurring features:

Outline → Content → Design: Most use a two-stage flow. (Allweone explicitly “outline-first”
; nooqta’s Reveal.js generator also builds an outline then slides
.)
Multi-Provider LLMs: Support for multiple models/APIs (OpenAI, Gemini, Claude, local Ollama). Presenton exemplifies this with “Bring Your Own Key” for OpenAI/Gemini/Claude
 and local Ollama mode
.
Themes/Templates: Template-based slide design is ubiquitous. Allweone has 38 built-in themes
; Presenton allows custom HTML/Tailwind themes
. PPTist even enables extracting styles from slides.
AI Image Generation: Integrate image providers (DALL·E, Stable Diffusion, Gemini, stock APIs). For example, Allweone lets you choose different AI image models per slide
; SlideBot uses Google Gemini for per-slide illustrations
; Paper2Any supports figure and diagram generation.
Export Formats: Nearly all offer PPTX export. PPTist and Presenton explicitly support PPTX/PDF
. Some (like Reveal.js-based or image-only systems) may not produce real PPTX, but conversion tools (Paper2Any’s PDF→PPT) help cover formats
.
Gaps in Current Solutions
Despite rich features, gaps remain:

True Multi-Agent Orchestration: Only demos (Azure) or research projects show full agent orchestration
. Others are mostly single-prompt or fixed pipelines.
Real-time Collaboration: Interactive multi-user editing is rare. Presenton notes “Real-time collaboration – Not Started”
, whereas SlideBot hints at instant revisions
 but stops short of live co-edit.
Offline/Local Mode: Most depend on cloud APIs. Presenton and Paper2Any support local modes (Ollama, etc.)
, but others do not.
Design QA & Accessibility: No tool enforces contrast, consistency, or brand compliance automatically.
Integrated Canvas Editing: Few combine AI generation with a full-fledged slide editor. PPTist has a canvas (but limited AI). Others output images (SlideBot, nbp_slides) or static HTML.
🏗️ Proposed MCP Architecture
yaml
Copy
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SLIDE GENERATION MCP SERVER                         │
│                                                                             │
│   Protocol: Model Context Protocol (MCP)                                   │
│   Framework: FastMCP + FastAPI                                            │
│   Language: Python 3.11+                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────┬───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
   Research Agent   Outline Agent   Content Agent   Design Agent   Image Agent
   (Web+Doc RAG,    (Narrative     (Slide text,     (Theming,      (AI image
    multimedia       structure)      iterations)      layouts)      generation)
Building on the above findings, we design a modular MCP server with these layers:

MCP Protocol & Server – Leverage FastMCP (based on FastAPI) for tool/agent integration. Inspired by Presenton’s built-in MCP
, our server exposes APIs for each function.

Agents – A swarm of specialized AI agents (modeled after Azure’s or HugoHe3’s architecture
):

Research Agent: Uses web search and RAG retrieval to gather facts, stats, and citations. (Similar to SlideSpeak’s pipeline, using Pinecone/Mongo
.)
Outline Agent: Plans the slide sequence and narrative arc given topic, purpose, audience. (This mirrors the “Outline-First” step in Allweone
 and nooqta’s approach
.)
Content Agent: Writes slide text per layout, enforcing brevity and source citation. (It can perform “Referee” style audits as in MixtapeTools, or content guards.)
Design Agent: Applies color schemes, fonts, and layout to fulfill a theme (based on the outline). Ensures brand compliance and accessibility (a new feature).
Image Agent: Generates/ searches images for slides. It creates prompts from slide text and calls multiple providers (DALL·E, Stable Diffusion, Gemini, stock APIs).
GitHub - Azure-Samples/ai-multi-agent-presentation-builder · GitHub
Figure: Example multi-agent orchestrator (Azure demo)
. Our MCP uses a similar design: an orchestrator agent spawns specialized agents (topic research, content, design, etc.) and collects their outputs into a final slide deck.

Each agent communicates through structured contexts (JSON-like slide specifications) over MCP. For instance, the Outline Agent outputs slide titles and purposes, which the Content Agent then fleshes out into bullet points or paragraphs, checking against quality rules (e.g. no fluff, citation needed). The Design Agent then chooses layouts (title slide, bullets, chart, image) and theme parameters for each slide.

🔧 MCP Tools Specification
We translate these features into MCP tools (functions exposed to the LLM agents) across categories:

Presentation Management: create_presentation(topic, purpose, audience, slide_count), list_presentations(), get_presentation(id), update_presentation(id, changes), delete_presentation(id) — CRUD for presentations.

Outline & Content Generation: generate_outline(topic, purpose, audience, slide_count), refine_outline(outline_id, feedback), generate_slide_content(slide_id, layout, context), generate_all_slides(outline_id), improve_content(content, style) — tools for structuring and writing slides. (Inspired by outline flows in Allweone
 and scripts like nbp_slides’ workflow
.)

Design & Themes: apply_theme(presentation_id, theme_id), generate_theme(brand_colors, style), list_themes(), create_custom_theme(config), analyze_design_quality(presentation_id) — manage color palettes, fonts, layouts. (Based on Presenton’s custom HTML themes
 and Allweone’s theme library
.)

Image Generation: generate_slide_image(slide_id, prompt, style), generate_hero_image(presentation_id, topic), search_stock_images(query), upload_custom_image(file_path, slide_id) — produce or fetch visuals. (Similar to SlideBot’s Gemini-based image tool
 and Allweone’s multi-model image support
.)

Canvas & Editing: render_canvas(presentation_id), get_canvas_state(presentation_id), update_canvas_element(element_id, props), add_canvas_element(slide_id, type, props), delete_canvas_element(element_id) — full slide-editor interface (HTML/CSS or PDF). (Reflects PPTist’s element API
 and Paper2Any’s inline editing
.)

Export Tools: export_pptx(presentation_id), export_pdf(presentation_id), export_html(presentation_id), export_images(presentation_id, format) — deliver final decks in PPTX/PDF/HTML. (Allweone and Presenton support PPTX export
.)

Research & Data Tools: research_topic(query), extract_document(path), search_web(query), analyze_data(source, type) — internal tools for the Research Agent to fetch facts. (Inspired by SlideSpeak’s document ingestion
 and general RAG practices.)

Quality & Validation: validate_content(text), check_branding(presentation_id), validate_sources(text), get_improvements(presentation_id) — enforce our quality rules (fluff detection, contrast check, brand colors). (These are new for our system; no existing repo fully covers them, though SlideSpeak ensures data validity by pipeline.)

Each tool returns structured JSON conforming to an MCP schema, allowing LLMs to call them as needed.

🤖 Agent Workflow Details
Agent 1: Research Agent
Goal: Gather comprehensive, source-backed content on the topic.
Workflow:

Query Generation: Based on topic, purpose, formulate search queries.
Web Search & Scraping: Use Bing/Tavily/Google to find relevant info.
Document Parsing: If user uploads files (PDF/DocX/PPT/Excel), extract text (using langchain/unoconv).
RAG Ingestion: Store new info in vector DB (Chroma/Pinecone)
. Use this to answer follow-up queries.
Synthesis: Summarize findings with bullet points and citations.
Example: Similar to SlideSpeak’s approach, ingesting PPTs with LlamaIndex and Pinecone
 to build a knowledge base.

Agent 2: Outline Agent
Goal: Create a logical slide outline (titles and purposes).
Workflow:

Structure Determination: Decide slide sequence using narrative templates (Problem/Solution, Timeline, etc.).
Slide Purposes: Assign each slide a clear goal (intro, data, conclusion).
Balance Content: Estimate content per slide (few bullets per slide).
Validation: Ensure no critical section is missing for the given purpose (e.g. TAM/SAM in investor deck).
Example: Follows the “outline-first” step in Allweone
. If revisions needed, the agent refines based on feedback (like SlideBot’s outline editing UI
).

Agent 3: Content Agent
Goal: Fill each slide with clear, concise text.
Workflow:

Layout-Specific Drafting: Generate bullet points, paragraphs or data narratives constrained to the chosen layout (e.g. chart vs text slide).
Quality Guards: Apply rules (no fluff, require citations for facts, limit length). For example, we ban overused terms (“cutting-edge”) and cap words/bullet.
Style Adaptation: Adjust tone/personality (professional, casual, storytelling) per user preference.
Iteration: Accept feedback (“make point 2 clearer”), regenerate or refine as needed.
This agent may use tool calling to query the Research Agent’s knowledge or to fetch a citation. It echoes PPT Master’s “Strategist” in stage 1
 but focused per slide.

Agent 4: Design Agent
Goal: Turn raw slide text into appealing visuals.
Workflow:

Theme Selection: Choose or generate an appropriate theme (based on industry/style preferences).
Color & Font: Apply color palette and font family to slides. Ensure brand colors are used (with check_branding).
Layout Optimization: Assign layouts (title, two-column, chart, image, etc.) that best fit the content. (For example, if slide has >=1 data point, use a chart layout.)
Graphic Placement: Place icons/charts/images. If a chart slide, call image agent to produce a chart.
Review Consistency: Ensure spacing/margins/contrast are uniform across slides.
Inspired by Presenton’s flexible templates
 and Paper2Any’s “PPTPolish” beautification
, this agent ensures the deck looks cohesive.

Agent 5: Image Agent
Goal: Provide high-quality visuals for slides.
Workflow:

Prompt Generation: Create an image prompt from slide content (e.g. “graphic showing X concept”).
Provider Selection: Choose the best model (DALL·E3, Gemini, Stable Diffusion, stock API).
Generation & Search: Generate AI image or query stock libraries.
Quality Check: Ensure resolution ≥1920×1080 and style matches theme. If it fails, try alternate prompts/providers.
Styling: Apply filters/tints so the image fits the deck’s color scheme (like Allweone’s “Audience-Focused Styles”
).
SlideBot used Google Gemini for context-consistent images
; we generalize this across many providers. Generated images are returned to Design Agent to be placed on slides.

🎨 Theme System
We will support 40+ prebuilt themes and custom themes, categorized by use-case: Corporate (e.g. Executive Blue, Green Tech), Creative (Gradient, Dark Mode), Educational (Clean White, Text-Focused), Startup (Pitch Deck styles), and Nature (Eco Green, Earth Tones).

A Theme includes:

python
Copy
class Theme(BaseModel):
    id: str
    name: str
    colors: ThemeColors  # primary, accent, background, text
    fonts: ThemeFonts    # heading, body
    layouts: Dict[str, LayoutConfig]
    effects: ThemeEffects  # e.g. animations, transitions
    industries: List[str]   # applicable industries/purposes
E.g. Allweone’s 38 themes
 inspire our variety, and users can create new themes (with color pickers and layouts) just as they might import from existing PPT files
.

🔄 Quality Gates
To ensure professionalism:

Content Rules: No fluff words (we detect and block terms like “revolutionary”, “game-changing”). All data statements must cite a credible source (e.g. web snippet). Slide bullets limited to 6 lines of text each.
Design Rules: Colors must maintain contrast ≥4.5:1 for readability. Fonts and spacing are uniform across slides. Uploaded logos/images checked for resolution.
Brand Compliance: If a brand palette is given, every slide’s colors are checked (via check_branding tool).
Accessibility: Diagrams get alt-text; no content reliant solely on color.
If any check fails, the appropriate agent (e.g. Content Agent or Design Agent) is prompted to revise before finalizing.

🚀 Implementation Phases
Phase 1 (Weeks 1–2): Set up core MCP server (FastMCP+FastAPI). Implement basic presentation CRUD tools and multi-provider LLM integration. Wire up PPTX export (python-pptx).
Phase 2 (Weeks 3–4): Build agent pipeline: start with Outline and Research Agents. Integrate Quality Guards for content. Develop basic theming engine (color palettes).
Phase 3 (Weeks 5–6): Add Design Agent (layouts, style) and Image Agent (DALL·E/SD/Gemini). Implement canvas rendering (HTML+Tailwind preview or headless browser).
Phase 4 (Weeks 7–8): Premium features: real-time collaborative editing, advanced animations, RAG with vector store for docs (Chroma/Pinecone) and slide search.
Phase 5 (Weeks 9–10): Optimization, error handling, extensive testing, and documentation.
💾 Data & Storage Architecture
Vector Store (Chroma/Pinecone): Index presentation content and web research for similarity search. (SlideSpeak uses Pinecone for embeddings
.)
Document Store (MongoDB/PostgreSQL): Store presentations, slides, themes, user data. (SlideSpeak uses MongoDB for content and Pinecone for index
.)
Object Storage (S3/MinIO): Store generated images, asset files, and exported decks. (As with SlideSpeak’s S3 integration
.)
Cache (Redis): Cache LLM responses and theme configs for fast reuse.
This mirrors architectures seen in SlideSpeak and Paper2Any, scaling to numerous concurrent decks.

🔐 Security Considerations
API Keys: All LLM/Image API keys are managed as environment variables (never logged). Features like “Bring Your Own Key” (Presenton
) are supported so teams use their own credentials.
Prompt Sanitization: User inputs (topics, doc text) are sanitized to prevent injection attacks.
Rate Limiting & Quotas: Per-user quotas and rate limits guard backend costs.
Content Moderation: AI outputs are filtered for toxicity or bias before user consumption.
Secure File Handling: Uploaded files are virus-scanned and sandboxed (using containers) to prevent exploits.
📈 Success Metrics
Accuracy: >95% valid JSON from LLM tools (via MCP schema validation).
Image Generation: >90% success (with fallback providers if one fails).
Export Reliability: >99% PPTX/PDF export success.
Quality: >85% of slides pass automated design/content checks on first try.
Performance: Content gen ≤5s/slide; full 10-slide deck <60s.
We will benchmark against projects like Presenton and Paper2Any to ensure competitive performance.

🎯 Differentiation
This MCP stands out by combining all strengths:

Full Multi-Agent Orchestration: Unlike single-step tools, we run 5+ specialized AI agents in concert (inspired by Azure’s demo
 and HugoHe3’s multi-stage pipeline
).
Multi-Provider LLM & Local Models: Support all major LLMs (OpenAI, Claude, Gemini, Ollama) with fallback chaining
. Offline mode via Ollama (as in Presenton) ensures functionality without internet
.
Interactive Canvas Editing: We integrate a full slide editor (HTML/CSS-based) with AI assistance – a capability not seen in the open generators (only PPTist comes close, but with minimal AI help)
.
Quality Guardrails: Built-in content and design validators (novel to our system) ensure every deck is polished. Other tools leave this to the user.
RAG & Collaboration: We combine document ingestion and retrieval (as in SlideSpeak) with plans for real-time collaboration.
In summary, our MCP is a one-stop premium solution: agent-driven, multi-source, and user-friendly.

🛠️ Tech Stack
Language: Python 3.11+ (ML ecosystem)
MCP Framework: FastMCP (agent protocol) atop FastAPI
LLM Clients: OpenAI, Anthropic (Claude), Google Gemini, Ollama (local), Groq
Vector DB: Chroma or Pinecone (as in SlideSpeak
)
Doc Store: MongoDB/PostgreSQL
Cache: Redis
Object Store: S3/MinIO for images & exports
PPTX: python-pptx (generating .pptx with shapes)
Rendering: Headless Chromium (for HTML/PDF), or custom Tailwind templates
UI (optional): Streamlit or React for dashboards (like Azure’s Streamlit demo)
Testing: pytest, Locust (load testing)
This aligns with common frameworks used by others: Python/Flask for backend (Paper2Any), Python for ML pipelines, and modern JS for any frontend components.

Sources: We built this plan on deep analysis of existing projects and literature. For example, Allweone’s Presentation-AI outlines key features
, Presenton’s README highlights multi-agent and MCP support
, SlideBot-AI’s documentation shows document/audio integration
, and Paper2Any’s roadmap demonstrates converting documents to editable PPTs
. These informed our architecture and tool design. All tools and workflows above are derived from connected sources as cited.

Document Version: 1.0 • Date: 2026-04-02 (updated)