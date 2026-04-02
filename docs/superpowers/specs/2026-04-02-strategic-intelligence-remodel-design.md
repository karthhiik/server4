# Strategic Intelligence Services -- Complete Remodel Design Specification

Date: 2026-04-02
Project: Barise Platform
Author: CTO Office
Status: Approved
Backend Target: Server1_FastApi
Frontend Target: lliveupdatedstreaming
Priority Order: Business Plan > GTM Strategy > SWOT Analysis > Pitch Deck Analysis

---

## 1. Executive Summary

This document defines the complete remodel of the four core strategic intelligence services on the Barise platform: Business Plan, GTM Strategy, SWOT Analysis, and Pitch Deck Analysis. The remodel follows the "Dedicated Canvases" approach where each service gets a purpose-built result experience with unique layouts, visualizations, and interaction patterns -- all powered by a shared component library called the "Shared Brain."

The remodel addresses three critical gaps in the current system:
1. Output quality -- AI-generated results must be deeply detailed, research-backed, and cite real sources
2. Visual innovation -- Each service needs a unique, premium visual identity with React Flow, charts, 3D elements, and motion
3. Input intelligence -- When users mention real companies or products, the system must web-search and inject real data into generation

### Current State

Backend (Server1_FastApi): Four fully functional services with sync and async endpoints, Celery task orchestration, MongoDB storage, Redis caching, WebSocket progress streaming, and an intelligence pipeline.

Frontend (lliveupdatedstreaming): BusinessPlan.tsx is active with a PromptInput component. SWOTAnalysis.tsx and GTMStrategy.tsx are entirely commented out. pitch_anaylsis.tsx is active with expansion pipeline. IntelligenceWorkspace.tsx is the most advanced component with React Flow, Recharts, DrawioViewer, and evidence graphs. All legacy result display components (ResultBusiness.tsx, SWOTResult.tsx, ShowGTM.tsx) are commented out.

### Design Principles

- Each service canvas is a standalone premium experience, not a reskinned template
- Shared Brain components (EvidenceDrawer, ConfidenceBadge, ExportToolbar, ReactFlowWrapper, SectionEditor) are built once and reused across all canvases
- Every AI claim must be backed by evidence with confidence scoring
- Real-time web search enrichment for company and competitor data
- Both prompt-based and structured form inputs for every service
- Editable, downloadable, version-tracked outputs

---

## 2. Shared Component Library (The Shared Brain)

### 2.1 EvidenceDrawer

Slide-out panel (480px wide, right side) showing research evidence backing any claim.

Features:
- Triggered by clicking citation badges [1], [2] or "View Sources" links
- Groups evidence by confidence level: Verified, Corroborated, Inference, Weak Signal
- Each evidence card: source title, URL domain, snippet, freshness date, confidence badge
- "Visuals" tab inside the drawer for scraped charts, graphs, and competitor logos
- Search/filter bar to search within evidence
- Glass-morphism panel: bg-slate-900/95 backdrop-blur-xl
- Left-border color coding: green = verified, amber = inference, red = weak signal

Props:
- isOpen: boolean
- onClose: callback
- citations: CitationReference[]
- bundleId: optional string
- highlightCitationId: optional string for auto-scroll

### 2.2 ConfidenceBadge

Inline indicator showing AI confidence about a specific claim or section.

Levels:
- verified: Emerald, ShieldCheck icon
- corroborated: Blue, CheckCircle2 icon
- inference: Amber, AlertTriangle icon
- scenario: Purple, Telescope icon
- weak_signal: Rose, Search icon (not Siren -- encourages investigation, not panic)
- blocked: Gray, Lock icon

Sizes: sm (icon only with tooltip), md (icon + label), lg (icon + label + source count)

### 2.3 ExportToolbar

Floating bottom-right toolbar for downloading artifacts.

Formats supported:
- PDF: Styled, branded with embedded charts. Uses jsPDF + html2canvas with explicit WebGL/Three.js canvas rasterization (gl.domElement.toDataURL()) before compositing with DOM elements to avoid black-box captures.
- DOCX: Structured Word document with sections, tables, headers via docx library
- Markdown: Raw markdown export
- PNG: Full canvas screenshot via html2canvas with Three.js pre-rasterization
- TOON: Raw TOON format for API consumers
- Share Link: Generates shareable read-only link (future)

Position: Fixed bottom-right, collapsible pill expanding on hover with radial layout via Framer Motion.

### 2.4 ReactFlowWrapper

Pre-configured React Flow canvas with consistent theming across all services.

Configuration:
- Dark background with dot grid pattern
- MiniMap bottom-left (collapsed, expands on hover)
- Controls panel: zoom, fit view, lock/unlock
- Animated edges with MarkerType.ArrowClosed
- Snap-to-grid 15px
- Multi-select with Shift+click
- Connection validation on drag

Shared Node Types:
- strategyNode: Rounded card with icon, title, subtitle, confidence badge, status dot
- metricNode: Compact KPI card with value, trend arrow, sparkline
- evidenceNode: Citation pill that opens EvidenceDrawer on click
- groupNode: Container node for grouping with label header

Each canvas registers its OWN additional node types. The wrapper supports rendering full React components inside nodes, including Three.js Canvas elements. Performance guard: 3D nodes only render when visible in the viewport using IntersectionObserver.

### 2.5 WebSearchContext

Real-time entity detection and web search enrichment system.

Flow:
1. User types in prompt input
2. Debounce 500ms, then NER call: POST /api/intelligence/detect-entities
3. Detected entities appear as interactive chips below input
4. Each chip has "Search" action triggering: POST /api/intelligence/web-enrich
5. Results show as structured cards: company description, funding, competitors, news
6. "Analyze Competitor" quick-action on entity chips triggers POST /api/intelligence/competitor-snapshot for deep side-analysis
7. User toggles which enrichments to include in generation context

### 2.6 SectionEditor

Inline editable section block used in every canvas.

Features:
- Default: Rich markdown rendering with inline citation links
- Edit mode: React Quill rich text editor
- "/" command menu: /rewrite, /expand, /add-data, /make-punchier, /simplify, /add-chart, /cite-source
- AI Sparkle button on hover of any paragraph for quick actions
- "Regenerate This Section" button: POST /api/regenerate-section for that section only
- "Save Draft" persists edit without regeneration
- Version history dot opens VersionHistoryDrawer showing diffs
- Auto-save every 5 seconds (debounced)

### 2.7 VersionHistoryDrawer

Timeline view showing edit/regeneration history.

Features:
- Each version: timestamp, author (user vs AI), change type (edit, regenerate, merge)
- Click any version to preview
- "Restore" button to revert
- Diff view between any two versions (red/green highlighting)

### 2.8 MetricCard

Reusable KPI display card.

Variants:
- number: Big number with label and trend arrow
- gauge: Circular gauge 0-100 for scores
- sparkline: Number with tiny inline sparkline chart
- progress: Progress bar with label

Inherits accent color from parent canvas.

### 2.9 Color Accent System

Each canvas has a distinct color accent flowing through all shared components:

| Service | Primary Accent | Secondary | Glow Color |
|---------|---------------|-----------|------------|
| Business Plan | #3B82F6 Blue | #1E40AF | blue-500/20 |
| GTM Strategy | #10B981 Emerald | #047857 | emerald-500/20 |
| SWOT Analysis | #8B5CF6 Violet | #6D28D9 | violet-500/20 |
| Pitch Deck | #F59E0B Amber | #D97706 | amber-500/20 |

Delivered via React Context:
```
<CanvasThemeProvider accent="blue" glow="blue-500/20">
  <BusinessPlanCanvas />
</CanvasThemeProvider>
```

---

## 3. Dual-Mode Input System

### 3.1 Architecture

Every service gets a single input page with two modes:
- Prompt Mode (hero, top of page, immediately visible)
- Structured Form Mode (below, expandable accordion)

Both modes feed the same generation pipeline. They cross-pollinate:
- Prompt to Form: lightweight extraction auto-fills structured fields from natural language
- Form to Prompt: generates a summary one-liner from structured inputs

### 3.2 Hero Section

Animated gradient mesh background using CSS @property animations in the service accent color. No Three.js on input pages (save 3D for canvases).

Per-service titles:
- Business Plan: "Craft Your Business Plan -- Backed by Real Intelligence"
- GTM Strategy: "Design Your Go-To-Market Battle Plan"
- SWOT Analysis: "Map Your Strategic SWOT Landscape"
- Pitch Deck: "Analyze and Perfect Your Pitch Deck"

Title animation: staggered letter reveal via Framer Motion. Service keyword pulses with accent color.

Floating particles: 8-12 Framer Motion animated dots at 10-15% opacity, parallax-responsive to mouse.

### 3.3 Strategy Prompt Input

Large textarea (min-height 160px, grows with content). Dark glass card styling.

Features:
- Typewriter placeholder animation on mount with service-specific example prompts
- Entity detection chips below textarea (animated: detected > searching > enriched states)
- Enrichment preview cards (expand on chip click) showing company data, funding, competitors, news
- "Analyze Competitor" quick-action per entity chip
- "Use" toggle per enrichment to control context injection
- Mode toggle: Fast Mode (20-45s) vs Deep Research Mode (60-240s) as segmented control
- 3 suggestion pills for prompt starters when idle with < 30 chars

### 3.4 Structured Form

Organized as collapsible accordion sections with glass-card styling and accent-colored left borders.

Business Plan Form (8 sections):
1. Business Identity: Company Name, Industry, Business Type, Current Stage
2. Vision and Value: One-liner Hook, Founder Mission, Unique Value Prop, Unfair Advantage
3. Market and Customers: Target Market, Customer Persona, Market Size, Geographic Focus
4. Product and Tech: Core Product, Core Features, Tech Stack, Tech Infrastructure
5. Competition: Competitor 1/2/3 (name + weakness), Positioning
6. Business Model: Revenue Sources, Pricing Strategy, Acquisition Channels, Marketing Channels
7. Team and Operations: Founding Team roles, Team Size, Hiring Needs, Partnerships
8. Financials and Risk: Current Funding, Burn Rate, Revenue, Runway, Risk Appetite, Biggest Threats

GTM Strategy Form (6 sections):
1. Business Identity: Business Name
2. Battlefield -- Strategic Positioning: Industry, Target Segment, Demographics, Psychographics, Hangout Channels, Competitor 1-3 Weaknesses, GTM Mode Preference
3. Founder DNA -- Weapons: Unfair Advantage, Content Strategy
4. Resource Arsenal: Monthly Budget, Team Size, Launch Date, Target Location
5. Risk Appetite: Scale 1-10 with visual slider
6. Empire Blueprint: Category Design Intent, Exit Intent, Global vs Local

SWOT Analysis Form (3 sections):
1. Business Identity: Business Name, Industry, Business Description
2. Market Context: Target Market
3. Pre-Identified Factors (optional): Strengths, Weaknesses, Opportunities, Threats with AI Suggest per field

Pitch Deck Form (2 sections):
1. Pitch Context: Industry, Description
2. Deck Upload: File upload drag-and-drop zone (PDF/PPTX/PPT, max 50MB)

AI Assist buttons on eligible fields: "Suggest Target Market", "Find Competitors" (web search), "Suggest Revenue Model", "Suggest USP", "Estimate Runway"

### 3.5 Cross-Pollination

Prompt to Form:
- POST /api/intelligence/extract-form-fields extracts structured values from prompt text
- Auto-fills form with toast notification: "We extracted N fields from your prompt"
- Auto-filled fields glow briefly with accent color

Form to Prompt:
- Generated one-liner summary appears at top of prompt box
- User can edit before generating

### 3.6 Generate Button

Idle: Accent gradient button with shimmer animation and Deep Mode badge
Hover: 1.02x scale, intensified glow, tooltip with timing estimate
Loading: Transforms into progress bar with stage labels from WebSocket
Completion: Green flash, smooth page transition to Canvas via Framer Motion layoutId

### 3.7 New Backend Endpoints

POST /api/intelligence/detect-entities
- Input: text, artifact_type
- Output: entities array with name, type, span, confidence
- Utility-tier model, cached by text hash for 5 minutes

POST /api/intelligence/web-enrich
- Input: entity_name, entity_type, context
- Output: summary, funding, competitors, market_cap, revenue, news, key_products, sources
- Uses search-hub-mcp or SerpAPI fallback, cached 30 minutes

POST /api/intelligence/extract-form-fields
- Input: prompt, artifact_type
- Output: fields dict, confidence score
- Utility-tier model, fast extraction

POST /api/intelligence/competitor-snapshot
- Input: competitor_name, your_business_context, artifact_type
- Output: strengths, weaknesses, market_share, recent_moves, threat_level, opportunity_gaps, sources
- Research-tier model

### 3.8 Routing Updates

New routes:
- /business-plan -> BusinessPlanInput (replaces current)
- /gtm-strategy -> GTMStrategyInput (replaces commented page)
- /swot-analysis -> SWOTAnalysisInput (replaces commented page)
- /pitch-analysis -> PitchAnalysisInput (enhances current)
- /canvas/business-plan/:taskId -> BusinessPlanCanvas (NEW)
- /canvas/gtm/:taskId -> GTMCanvas (NEW)
- /canvas/swot/:taskId -> SWOTCanvas (NEW)
- /canvas/pitch/:taskId -> PitchCanvas (NEW)

Preserved routes:
- /intelligence/workspace/:artifactType/:taskId remains as deep-mode progress shell, redirects to canvas on completion
- /artifact-library remains as artifact list
- /formforbusiness deprecated, redirects to /business-plan

---

## 4. Business Plan Canvas

### 4.1 Layout

Three-column "Strategy Workspace":
- Nav Rail (64px, left): Icon-only vertical navigation, 7 view icons
- Main Content (flex-grow, center): Active view with AnimatePresence transitions
- Intel Sidebar (320px, right, collapsible): Persistent context panel

### 4.2 Nav Rail Views

View 1 -- Executive Summary (Default):
- Hero block with company name, one-liner, 4 KPI MetricCards (TAM, Revenue, Team, Runway)
- 13 business plan sections as SectionEditor cards
- Each section: title with ConfidenceBadge, rich markdown with citations, edit/regenerate icons, "/" command menu
- Typography: Playfair Display for section titles, Inter for body, JetBrains Mono for numbers

View 2 -- Strategy Map (React Flow):
- Interactive node-based strategy visualization
- Custom nodes: marketNode (with 3D globe on hover via React Three Fiber, viewport-gated), customerNode, competitorNode, productNode, revenueNode, financeNode, riskNode, milestoneNode, exitNode
- Auto-layout via ELKjs (layered top-to-bottom)
- Primary flow: market > customer > product > revenue > finance > exit
- Lateral connections: risk and competitor nodes
- Click node: Intel Sidebar updates to show section evidence
- Double-click: Opens SectionEditor as modal
- Right-click: Context menu (Regenerate, View Sources, Mark as Reviewed)
- Stale nodes show pulsing amber border

View 3 -- Metrics Dashboard:
- CSS Grid, 2 columns desktop, 1 mobile
- Charts (all Recharts): Market Size donut (TAM/SAM/SOM), Revenue Projections area chart (3 scenarios), Competitive Position radar chart, Financial Health gauge cluster, Risk Heatmap scatter chart (Impact vs Probability), Milestone Timeline (custom Framer Motion component), Unit Economics KPI grid, Industry Benchmark bar chart
- Interactive: scenario toggle on revenue chart, clickable risk items

View 4 -- Full Report:
- Single column (max-width 800px), premium editorial styling
- Sticky Table of Contents sidebar
- Print-optimized CSS
- Reading progress bar at top
- All 13 sections sequentially with section numbers, ConfidenceBadges, embedded static charts, citation links

View 5 -- Sources and Evidence:
- Two-column: source list left, detail preview right
- Sources grouped by type: Web Search, Market Data API, News, Company Intel, User-Provided
- "Add Manual Source" button
- "Refresh Sources" button

View 6 -- Edit Mode:
- Split view: editable sections left, live markdown preview right
- "/" command menu and AI Sparkle button per paragraph
- Auto-save every 5s
- "Save and Update Bundle" persists edits and marks dependent nodes stale

View 7 -- Version History:
- Full-page timeline of all versions
- Compare any two versions with side-by-side diff
- Restore button per version

### 4.3 Intel Sidebar

Persistent right panel (collapsible) with:
- Market Snapshot: GDP, Inflation, Industry Growth, Sentiment, Unemployment from World Bank/FRED/Alpha Vantage
- Source Confidence: Verified/Corroborated/Inference/Weak Signal counts
- AI Confidence Gauge: RadialBarChart 0-100% with strongest/weakest sections
- Web Enrichment Used: Entity cards with type and usage status
- Quick Actions: Regenerate All, Refresh Data, Share Plan, Delete Plan

### 4.4 Entry Animation

1. Title fly-in via Framer Motion layoutId
2. Skeleton shimmer on all content areas
3. Progressive reveal as WebSocket sections arrive (KPI cards staggered 100ms, sections fade+slide)
4. Intel sidebar metrics count up from 0
5. Completion blue pulse ripple across header

### 4.5 Responsive Behavior

- 1280px+: Full 3-column
- 1024-1279px: Rail + main, sidebar as pull-out drawer
- 768-1023px: Top horizontal tab bar, full-width main, sidebar as drawer
- <768px: Bottom tab bar, full-width main, sidebar as full-screen modal

---

## 5. GTM Canvas

### 5.1 Layout

"Command Center" layout:
- Horizontal tab bar (7 tabs)
- Main content area
- Mission Metrics Bar (persistent bottom strip)
- Emerald accent throughout

### 5.2 Tab Views

Tab 1 -- War Room (Default):
- Bento grid (CSS Grid, 12-column) with glass-morphism cards
- Cards: Strategic Thesis (2-col), 100-Day Battle Plan timeline (3-col), ICP Card, Pricing Card, Top Channels Card, Risk Appetite gauge, Competitive Position radar chart, Market Opportunity donut (TAM/SAM/SOM)
- Each card clickable, navigates to relevant detail tab

Tab 2 -- Launch Map (React Flow):
- Left-to-right battle plan flow
- Custom nodes: icpNode, positioningNode, channelNode (unique color per channel), pricingNode, launchPhaseNode, experimentNode, kpiNode, competitorNode
- Layout: ICP > Positioning > Pricing > Channels (fan out) > Launch Phases
- Experiments hang below parent channel, KPIs at bottom
- Drag channels to reprioritize
- Right-click channel: "Reallocate Budget" modal with slider
- Auto-layout via ELKjs direction: RIGHT

Tab 3 -- Funnel View:
- Interactive vertical SVG funnel, each stage is a component
- Stages: Awareness > Interest > Consideration > Intent > Purchase > Retain
- Each stage shows: volume, conversion rate, active channels
- Click stage: expand to show detail, conversion tactics, experiments
- Animated flow particles (emerald dots) traveling down funnel
- "What-if" slider: drag conversion rate, downstream numbers update live

Tab 4 -- Channel Deep-Dive:
- Horizontal card carousel with detail panel below
- Each channel card: color-coded, budget % progress ring, status badge
- Selecting a card expands detail: budget, CAC, leads, tactics, experiments
- "Add Channel" button with AI-recommended channels based on ICP

Tab 5 -- Experiment Board:
- Kanban: Planned, Running, Completed columns
- Drag-and-drop between columns
- Each experiment card: name, channel, metric, priority, duration progress
- Click: full detail with hypothesis, control vs variant, success criteria
- "Suggest Experiment" button using AI

Tab 6 -- KPI Board:
- Dashboard grid: North Star Metric (giant number + sparkline), Revenue Projection area chart, CAC by Channel bar chart, Funnel Conversion step chart, Budget Allocation donut, Growth Rate line chart, Leading Indicators (4 MetricCards), Lagging Indicators (4 MetricCards), Milestone Tracker timeline
- Editable assumptions in Edit Mode
- "What-If" slider panel for budget/conversion/pricing assumptions

Tab 7 -- Full Report:
- All 15 GTM sections, military-style numbering
- Embedded funnel diagram, channel donut, tables for Tactical Execution Roadmap and 100-Day Battle Plan

### 5.3 Mission Metrics Bar

Persistent bottom strip showing 6 critical GTM metrics: CAC, LTV, LTV:CAC, Payback Period, Target MRR, Launch Date, Active Channels. Each with trend arrow. Clicking navigates to relevant section.

### 5.4 Entry Animation

1. GTM mode badge slides in from left with green flash
2. War Room cards animate with scan-line effect (CSS gradient animating vertically)
3. Mission Metrics Bar slides up, metrics count from 0
4. Funnel particles animate on Funnel View switch

---

## 6. SWOT Canvas

### 6.1 Layout

"Quadrant Arena" layout:
- Horizontal tab bar (5 tabs)
- Main content area
- Violet accent throughout

### 6.2 Tab Views

Tab 1 -- Interactive 2x2 Matrix (Default):
- Full-screen quadrant grid
- Quadrant colors: Strengths (emerald), Weaknesses (rose), Opportunities (blue), Threats (amber)
- Each SWOT item card: title, description, impact slider (LOW/MEDIUM/HIGH), ConfidenceBadge, category tag, source citation, drag handle, edit/delete icons
- Drag items between quadrants
- "+ Add" button per quadrant
- "Suggest More" AI button per quadrant
- Entry animation: quadrants slide from corners, items cascade with 80ms stagger

Tab 2 -- TOWS Actions (React Flow):
- Left column: SWOT items grouped by quadrant
- Right column: Action nodes
- Edges connect pairings: SO (emerald), WO (blue), ST (amber), WT (rose) with animated colored lines
- Custom nodes: strengthNode, weaknessNode, opportunityNode, threatNode, actionNode (with priority, owner, timeline, status fields)
- User can drag new connections for custom TOWS pairings
- Action nodes are editable with priority (P1/P2/P3), owner dropdown, date picker, status

Tab 3 -- Risk Radar:
- Center: Recharts RadarChart across 6 dimensions (Financial, Market, Operational, Strategic, Regulatory, Technology)
- Surrounding: Risk detail cards per category from Risk Analysis sub-service
- Below: Impact vs Probability scatter plot for all threat items
- "What-if" toggle: remove a risk item, radar reshapes

Tab 4 -- Deep Dive (Sub-Analyses):
- Vertical accordion with 4 sections:
  - Competitor Analysis: Table view (competitors as columns, dimensions as rows), web-enriched data, "Add Competitor" button
  - Value Proposition Canvas: Visual 2-panel layout (Customer Profile vs Value Proposition), items are draggable, color-coded (pains = rose, gains = emerald, jobs = blue), connecting lines show which reliever addresses which pain
  - Market Segmentation: Bubble chart (size = segment size, color = growth rate, position = purchasing power vs accessibility), detail cards below
  - Risk Analysis: Full text sections for Strategic, Operational, Financial, Market risks
- Each sub-analysis has Regenerate button and ConfidenceBadge

Tab 5 -- Full Report:
- Inline 2x2 matrix as styled table
- TOWS action table
- Embedded risk radar chart
- Value proposition canvas
- Market segmentation bubble chart
- Competitor comparison table
- All sub-analyses as sequential sections

### 6.3 Entry Animation

Four colored light beams from corners converging to center. Grid assembles as quadrants slide into position. Items cascade within each quadrant. Impact badges animate from gray to color.

---

## 7. Pitch Canvas

### 7.1 Layout

"Investor War Room" layout:
- Horizontal tab bar (7 tabs)
- Main content area
- Amber accent throughout

### 7.2 Tab Views

Tab 1 -- Score Card (Default):
- Large circular Investment Readiness gauge (0-100, amber fill, animated count-up)
- Dimension score cards in a row: Problem, Solution, Market, Traction, Team (each as mini gauge)
- Top Strengths / Top Weaknesses lists
- Investor Verdict: AI-generated summary paragraph

Tab 2 -- Slide Rail:
- Top: horizontal scroll of slide thumbnails with letter grades (A = emerald, B = blue, C = amber, D/F = rose)
- Bottom: detailed analysis of selected slide
  - Score and grade
  - Issues found with severity badges (HIGH/MEDIUM/LOW)
  - Evidence check: web search results vs slide claims with MISMATCH detection
  - AI rewrite suggestion with Accept/Edit/Dismiss actions

Tab 3 -- Objection Board:
- Kanban: Critical, Moderate, Minor columns
- Each card: likely investor question, triggering slide, severity
- "View Answer" expands AI-generated response talking points
- "Add to Deck" creates backup/appendix slide
- Editable: user can add own objections

Tab 4 -- Story Arc:
- Recharts AreaChart showing narrative tension/energy across slides
- Each dot is a slide, clickable to navigate to Slide Rail
- Below: AI commentary on narrative structure (strengths, gaps, missing inflection points)

Tab 5 -- Evidence Check:
- Two-column: Claims Made (left), Evidence Found (right)
- Each claim: color-coded status (green = match, amber = close, red = mismatch, gray = unverifiable)
- "Fix" button per mismatch opens rewrite suggestion
- Self-reported data marked as USER-PROVIDED

Tab 6 -- Rewrite Queue:
- Prioritized worklist of all suggested improvements
- Each item: priority badge, slide reference, current vs suggested text, Accept/Edit/Dismiss
- "Apply All Accepted" batch button
- Progress indicator: "N of M items resolved"

Tab 7 -- Full Report:
- Investment Readiness Summary
- Content Analysis
- Slide-by-Slide Analysis with inline scores
- Evidence Check Summary table
- Investor Objection Register
- Improvement Recommendations
- Competitive Landscape
- Narrative Structure Assessment

### 7.3 Entry Animation

Readiness gauge animates 0 to score (2s). Dimension cards flip in like cards being dealt. Strengths/weaknesses slide from left/right.

---

## 8. Enhanced AI Output Quality

### 8.1 Universal Prompt Enhancement Layer

New middleware: Server1_FastApi/app/services/intelligence/prompt_enhancer.py

Flow: User Input > Entity Detection + Web Enrichment > Prompt Enhancement Middleware > AI Model Call > Output Validator > Structured Response

The middleware:
- Injects web enrichment context (company data, competitor snapshots, market numbers)
- Injects market data (World Bank, FRED, Alpha Vantage -- already integrated)
- Adds citation instructions
- Adds structured output schema
- Adds depth instructions (the "No Fluff" mandate)

### 8.2 The "No Fluff" Mandate

Added to every system prompt across all 4 services:

1. Every section MUST be 500-1200 words minimum with specific, actionable content
2. Every market claim MUST cite a source using [Source Name, Year] or [1], [2] format
3. Every financial number MUST include methodology or basis
4. Never use filler phrases ("in today's rapidly evolving landscape", "leveraging synergies", etc.)
5. Replace generic statements with specific data points
6. For competitor analysis, use REAL competitor data from provided context. Never fabricate
7. For financial projections, show math with assumptions, formulas, and scenarios
8. For risk analysis, provide specific mitigation actions with owners and timelines
9. When data is unavailable, state "Data not available" with WEAK_SIGNAL confidence. Never fabricate
10. Include actionable recommendations, not just observations

### 8.3 Web Search Injection Pipeline

For every generation request:
1. Extract entities from user input (companies, competitors, products, geographies)
2. For each entity, run web enrichment (parallel, cached 30 min)
3. Compile into "Research Context Block"
4. Inject block into every section prompt with citation instructions

### 8.4 Per-Service Output Schema Upgrades

Business Plan sections return:
- content_md (500-1200 words with citations)
- confidence level
- key_metrics array (label, value, source, trend)
- visualization_spec (chart_type, data, title)
- strategic_nodes (React Flow node definitions)
- citations array

SWOT items return:
- title, description (detailed with data points)
- impact (low/medium/high), confidence, category
- evidence_sources
- related_items (cross-references to other quadrant items)
- tows_actions (pairing type, paired_with, action text)

GTM channels return:
- channel_name, type, priority_rank, budget_allocation_pct
- estimated_cac, estimated_monthly_leads, confidence
- rationale (with citations)
- tactics array
- experiments array
- evidence array

Pitch claims return:
- claim_text, slide_number, claim_type
- verification_status (match/mismatch/unverifiable)
- user_value vs verified_value
- verified_source, confidence, severity
- suggested_rewrite, investor_risk explanation

### 8.5 Output Validator

Post-generation checks:
- All required fields present
- Citation format correct
- Minimum content length per section
- Confidence scoring per section
- Metric extraction for charts
- Node extraction for React Flow

---

## 9. Frontend File Structure

```
lliveupdatedstreaming/src/
  features/
    intelligence/
      shared/
        CanvasThemeProvider.tsx
        EvidenceDrawer.tsx
        ConfidenceBadge.tsx
        ExportToolbar.tsx
        ReactFlowWrapper.tsx
        SectionEditor.tsx
        VersionHistoryDrawer.tsx
        MetricCard.tsx
        WebSearchContext.tsx
        DualModeInput.tsx
        StrategyPromptInput.tsx
        StructuredFormAccordion.tsx
        nodes/
          StrategyNode.tsx
          MetricNode.tsx
          EvidenceNode.tsx
          GroupNode.tsx
      business-plan/
        BusinessPlanInput.tsx
        BusinessPlanCanvas.tsx
        views/
          ExecutiveSummary.tsx
          StrategyMap.tsx
          MetricsDashboard.tsx
          FullReport.tsx
          SourcesEvidence.tsx
          EditMode.tsx
          VersionHistory.tsx
        nodes/
          MarketNode.tsx
          CustomerNode.tsx
          CompetitorNode.tsx
          ProductNode.tsx
          RevenueNode.tsx
          FinanceNode.tsx
          RiskNode.tsx
          MilestoneNode.tsx
          ExitNode.tsx
        charts/
          MarketSizeDonut.tsx
          RevenueProjection.tsx
          CompetitiveRadar.tsx
          RiskHeatmap.tsx
          MilestoneTimeline.tsx
      gtm/
        GTMStrategyInput.tsx
        GTMCanvas.tsx
        views/
          WarRoom.tsx
          LaunchMap.tsx
          FunnelView.tsx
          ChannelDeepDive.tsx
          ExperimentBoard.tsx
          KPIBoard.tsx
          FullReport.tsx
        nodes/
          ICPNode.tsx
          PositioningNode.tsx
          ChannelNode.tsx
          PricingNode.tsx
          LaunchPhaseNode.tsx
          ExperimentNode.tsx
          KPINode.tsx
        charts/
          FunnelSVG.tsx
          ChannelBudgetDonut.tsx
          CACByChannel.tsx
          GrowthTrajectory.tsx
        MissionMetricsBar.tsx
      swot/
        SWOTAnalysisInput.tsx
        SWOTCanvas.tsx
        views/
          QuadrantMatrix.tsx
          TOWSActions.tsx
          RiskRadar.tsx
          DeepDive.tsx
          FullReport.tsx
        nodes/
          StrengthNode.tsx
          WeaknessNode.tsx
          OpportunityNode.tsx
          ThreatNode.tsx
          ActionNode.tsx
        sub-views/
          CompetitorTable.tsx
          ValuePropCanvas.tsx
          MarketSegBubble.tsx
          RiskDetail.tsx
      pitch/
        PitchAnalysisInput.tsx
        PitchCanvas.tsx
        views/
          ScoreCard.tsx
          SlideRail.tsx
          ObjectionBoard.tsx
          StoryArc.tsx
          EvidenceCheck.tsx
          RewriteQueue.tsx
          FullReport.tsx
        charts/
          ReadinessGauge.tsx
          DimensionScores.tsx
          StoryArcChart.tsx
    hooks/
      useBundleTask.ts
      useBundleMonitor.ts
      useArtifactEdit.ts
      useStrategyGraph.ts
      useWebEnrichment.ts
      useEntityDetection.ts
    types/
      canvas.ts
      evidence.ts
      metrics.ts
      enrichment.ts
```

### Backend File Structure

```
Server1_FastApi/app/
  api/routes/
    intelligence_enrichment_routes.py    (NEW: detect-entities, web-enrich, extract-form-fields, competitor-snapshot)
  services/intelligence/
    prompt_enhancer.py                   (NEW: universal prompt enhancement middleware)
    entity_detector.py                   (NEW: NER extraction)
    web_enricher.py                      (NEW: web search enrichment)
    competitor_analyzer.py               (NEW: deep competitor snapshot)
    output_validator.py                  (NEW: post-generation validation)
    structured_output_schemas.py         (ENHANCED: per-service structured output definitions)
```

---

## 10. Source References

Strategy and design research:
- Miro GTM Strategy Template (miro.com/templates/go-to-market-strategy/)
- Funnelytics funnel mapping tool (funnelytics.io/mapping)
- Syncfusion React Funnel Chart (syncfusion.com/react-components)
- MUI X React Funnel Chart (mui.com/x/react-charts/funnel/)
- Untitled UI React Dashboards 2026 (untitledui.com/blog/react-dashboards)
- Fuselab Enterprise UX Design Guide 2026 (fuselabcreative.com/enterprise-ux-design-guide-2026)

Current project references:
- Server1_FastApi/app/api/routes/business_routes_refactored.py
- Server1_FastApi/app/api/routes/gtm_routes_refactored.py
- Server1_FastApi/app/api/routes/swot_routes.py
- Server1_FastApi/app/api/routes/pitch_analysis_routes_refactored.py
- Server1_FastApi/app/services/business_service.py
- Server1_FastApi/app/services/gtm_service_refactored.py
- Server1_FastApi/app/services/swot_service_refactored.py
- Server1_FastApi/app/services/pitch_service_refactored.py
- lliveupdatedstreaming/src/pages/BusinessPlan.tsx
- lliveupdatedstreaming/src/pages/IntelligenceWorkspace.tsx
- lliveupdatedstreaming/src/pages/ArtifactDetail.tsx
- lliveupdatedstreaming/src/lib/intelligenceApi.ts
- MULTI_MCP_BUSINESS_INTELLIGENCE_PLAN.md
