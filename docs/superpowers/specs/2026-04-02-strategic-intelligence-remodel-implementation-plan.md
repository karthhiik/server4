# Strategic Intelligence Services -- Implementation Plan

Date: 2026-04-02
Project: Barise Platform
Design Spec: 2026-04-02-strategic-intelligence-remodel-design.md
Priority Order: Business Plan > GTM Strategy > SWOT Analysis > Pitch Deck Analysis
Backend Target: Server1_FastApi
Frontend Target: lliveupdatedstreaming

---

## Overview

This plan implements the Dedicated Canvases remodel in 6 phases. Each phase delivers a shippable increment. The first 3 phases are the critical path. Phases 4-6 add polish and advanced features.

Estimated component count: ~95 frontend components, ~8 backend modules, 4 new API endpoints.

---

## Phase 0: Foundation -- Shared Brain Components

This phase builds every shared component before touching any individual canvas. Nothing ships to users yet, but everything after depends on this.

### Step 0.1: Canvas Theme System

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/CanvasThemeProvider.tsx

What to build:
- React Context provider that accepts accent color, glow color, secondary color
- CSS variable injection for --canvas-accent, --canvas-glow, --canvas-secondary
- Export useCanvasTheme() hook
- Four preset configs: business-plan (blue), gtm (emerald), swot (violet), pitch (amber)

Dependencies: None
Estimated size: ~80 lines

### Step 0.2: ConfidenceBadge

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/ConfidenceBadge.tsx

What to build:
- 6 confidence levels with icon, color, label mapping
- 3 sizes: sm (icon + tooltip), md (icon + label), lg (icon + label + count)
- onClick prop to open EvidenceDrawer filtered to relevant claim
- Use Search icon for weak_signal (not Siren)
- Framer Motion subtle pulse animation on render

Dependencies: lucide-react icons, framer-motion
Estimated size: ~120 lines

### Step 0.3: MetricCard

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/MetricCard.tsx

What to build:
- 4 variants: number, gauge, sparkline, progress
- number: large text + label + trend arrow (up/down/flat) + optional delta percentage
- gauge: Recharts RadialBarChart 0-100 with accent color fill
- sparkline: number + tiny Recharts LineChart (30px tall)
- progress: label + progress bar with percentage
- Inherits accent from CanvasThemeProvider

Dependencies: recharts, CanvasThemeProvider
Estimated size: ~200 lines

### Step 0.4: EvidenceDrawer

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/EvidenceDrawer.tsx

What to build:
- Slide-in panel (480px, right side, dark scrim overlay)
- Two tabs: "Sources" and "Visuals"
- Sources tab: groups by confidence level (Verified, Corroborated, Inference, Weak Signal)
- Each evidence card: title, domain, snippet, date, ConfidenceBadge, "Open in new tab" button
- Visuals tab: thumbnails of scraped images/charts with lightbox on click
- Search bar at top to filter within evidence
- Auto-scroll to highlightCitationId if provided
- Framer Motion slide-in animation
- Click outside or X to close

Dependencies: ConfidenceBadge, framer-motion
Estimated size: ~300 lines

### Step 0.5: SectionEditor

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/SectionEditor.tsx

What to build:
- Read mode: renders markdown content with inline citation links using CitationRichText (already exists)
- Edit mode: React Quill rich text editor with custom toolbar
- "/" command menu: triggered by typing "/" in the editor. Commands: /rewrite, /expand, /add-data, /make-punchier, /simplify, /add-chart, /cite-source
- AI Sparkle button: appears on hover over any paragraph. Opens quick-action popover with "Make punchier", "Add data", "Rewrite for investors", "Simplify"
- "Regenerate This Section" button calling POST /api/regenerate-section
- "Save Draft" button for persisting edits without regeneration
- ConfidenceBadge in header
- Version history dot linking to VersionHistoryDrawer
- Auto-save debounced at 5 seconds

Dependencies: react-quill (already in stack), ConfidenceBadge, EvidenceDrawer
Estimated size: ~400 lines

### Step 0.6: VersionHistoryDrawer

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/VersionHistoryDrawer.tsx

What to build:
- Timeline list of versions (timestamp, author icon user/AI, change type badge)
- Click version to preview content
- "Compare" button opens diff view between two selected versions (red/green text highlighting)
- "Restore" button reverts to selected version
- Uses same slide-in panel pattern as EvidenceDrawer

Dependencies: framer-motion
Estimated size: ~250 lines

### Step 0.7: ExportToolbar

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/ExportToolbar.tsx

What to build:
- Fixed bottom-right floating pill
- Hover expands to show format buttons in radial layout (Framer Motion spring animation)
- Format handlers: PDF (jsPDF + html2canvas + WebGL rasterization), DOCX (docx library), Markdown, PNG, TOON
- WebGL capture: before html2canvas, iterate all canvas.getContext('webgl') elements, call gl.domElement.toDataURL(), replace canvas with static image
- Loading spinner per format during export
- Success toast on completion

Dependencies: jspdf, html2canvas, docx (all already in stack), framer-motion
Estimated size: ~250 lines

### Step 0.8: ReactFlowWrapper

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/ReactFlowWrapper.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/nodes/StrategyNode.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/nodes/MetricNode.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/nodes/EvidenceNode.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/nodes/GroupNode.tsx

What to build:
- Pre-configured ReactFlow component with dark bg, dot grid, MiniMap, Controls
- Animated edges, snap-to-grid 15px, multi-select
- 4 shared node types registered by default
- Accepts additional nodeTypes prop for canvas-specific nodes
- StrategyNode: rounded card with icon, title, subtitle, ConfidenceBadge, status dot, click/double-click/right-click handlers
- MetricNode: compact KPI pill
- EvidenceNode: citation chip, click opens EvidenceDrawer
- GroupNode: container with label header
- IntersectionObserver guard for nodes containing Three.js Canvas elements

Dependencies: @xyflow/react (already in stack), ConfidenceBadge, EvidenceDrawer
Estimated size: ~500 lines total across 5 files

### Step 0.9: WebSearchContext + Entity Chips

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/WebSearchContext.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/EntityChip.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/EnrichmentCard.tsx

What to build:
- WebSearchContext: manages entity detection and enrichment state
- Debounced POST /api/intelligence/detect-entities on prompt change (500ms)
- EntityChip: animated chip (detected > searching > enriched states) with "Search" and "Analyze Competitor" actions
- EnrichmentCard: expandable card showing company data, funding, competitors, news. "Use" toggle. Framer Motion layoutId expand/collapse
- "Analyze Competitor" triggers POST /api/intelligence/competitor-snapshot

Dependencies: framer-motion
Estimated size: ~350 lines total across 3 files

### Step 0.10: DualModeInput Shell

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/DualModeInput.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/StrategyPromptInput.tsx
- lliveupdatedstreaming/src/features/intelligence/shared/StructuredFormAccordion.tsx

What to build:
- DualModeInput: page layout shell with hero section, prompt box, divider, collapsible form
- StrategyPromptInput: large textarea with typewriter placeholder, entity chips integration, mode toggle (Fast/Deep), suggestion pills, generate button with progress states
- StructuredFormAccordion: generic accordion renderer accepting section configs. Per-section: glass card with accent left border, icon + title + completion indicator, AI Assist button support
- Cross-pollination: extract-form-fields call on prompt submit, form-to-prompt summary generator

Dependencies: WebSearchContext, EntityChip, EnrichmentCard, CanvasThemeProvider, framer-motion
Estimated size: ~600 lines total across 3 files

### Step 0.11: Backend -- Intelligence Enrichment Endpoints

Files to create:
- Server1_FastApi/app/api/routes/intelligence_enrichment_routes.py
- Server1_FastApi/app/services/intelligence/entity_detector.py
- Server1_FastApi/app/services/intelligence/web_enricher.py
- Server1_FastApi/app/services/intelligence/competitor_analyzer.py

What to build:
- POST /api/intelligence/detect-entities: utility-tier model NER extraction, cached 5 min by text hash
- POST /api/intelligence/web-enrich: SerpAPI search + basic scraping for entity data (funding, competitors, news, market position), cached 30 min
- POST /api/intelligence/extract-form-fields: utility-tier model extraction of structured fields from prompt text
- POST /api/intelligence/competitor-snapshot: research-tier model deep competitor analysis with web enrichment
- All endpoints require @token_required auth
- Rate limiting: 10 per user per minute for detect-entities and extract-form-fields, 5 per user per minute for web-enrich and competitor-snapshot

Dependencies: Existing SerpAPI integration, existing Azure OpenAI integration, existing cache_service
Estimated size: ~600 lines total across 4 files

### Step 0.12: Backend -- Prompt Enhancement Middleware

Files to create:
- Server1_FastApi/app/services/intelligence/prompt_enhancer.py
- Server1_FastApi/app/services/intelligence/output_validator.py

What to build:
- PromptEnhancer class: accepts raw prompt + enrichment context + market data, returns enhanced prompt with depth instructions, citation rules, structured output schema
- The "No Fluff" mandate injected into every system prompt
- OutputValidator class: post-generation checks for required fields, citation format, minimum content length, confidence scoring, metric extraction, node extraction
- Per-service output schema definitions (business plan section schema, SWOT item schema, GTM channel schema, pitch claim schema)

Dependencies: Existing AI service layer
Estimated size: ~500 lines total across 2 files

### Step 0.13: Type Definitions

Files to create:
- lliveupdatedstreaming/src/features/intelligence/types/canvas.ts
- lliveupdatedstreaming/src/features/intelligence/types/evidence.ts
- lliveupdatedstreaming/src/features/intelligence/types/metrics.ts
- lliveupdatedstreaming/src/features/intelligence/types/enrichment.ts

What to build:
- TypeScript interfaces for all shared data structures: ConfidenceLevel, CitationReference, MetricItem, VisualizationSpec, FlowNodeSpec, CanvasThemeConfig, ExportFormat, WebEnrichment, DetectedEntity, CompetitorSnapshot
- Per-service section interfaces
- API response types for new endpoints

Dependencies: None
Estimated size: ~300 lines total across 4 files

Phase 0 total: ~4,450 lines across ~20 files

---

## Phase 1: Business Plan Canvas (Flagship)

### Step 1.1: BusinessPlanInput Page

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/BusinessPlanInput.tsx

What to build:
- Import and configure DualModeInput with business-plan accent (blue)
- Business Plan structured form config (8 sections with field definitions)
- Service access check (service ID 108)
- On generate: call existing POST /api/generate-business-plan (fast mode) or POST /api/generate_business_plan_async (deep mode)
- On success: navigate to /canvas/business-plan/:taskId with Framer Motion layoutId transition

Dependencies: DualModeInput, CanvasThemeProvider, all shared components from Phase 0
Estimated size: ~300 lines

### Step 1.2: BusinessPlanCanvas Shell

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/BusinessPlanCanvas.tsx

What to build:
- Three-column layout: Nav Rail (64px left), Main Content (flex-grow), Intel Sidebar (320px right, collapsible)
- Nav Rail with 7 icons (Summary, Map, Metrics, Report, Sources, Edit, History)
- Active view state management with AnimatePresence transitions
- Header: company name, generation metadata, edit mode toggle, export button
- Fetch task result on mount (GET /api/business_plan/:planId or task result endpoint)
- WebSocket connection for deep mode progress
- Progressive reveal animation (skeleton > shimmer > content)

Dependencies: CanvasThemeProvider (blue), ExportToolbar, all shared components
Estimated size: ~400 lines

### Step 1.3: Intel Sidebar

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/IntelSidebar.tsx

What to build:
- Market Snapshot section with MetricCards (GDP, Inflation, Industry Growth, Sentiment)
- Source Confidence section with counts per level
- AI Confidence Gauge (RadialBarChart)
- Web Enrichment Used section with entity cards
- Quick Actions section
- Collapsible on smaller screens

Dependencies: MetricCard, ConfidenceBadge, recharts
Estimated size: ~250 lines

### Step 1.4: Executive Summary View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/views/ExecutiveSummary.tsx

What to build:
- Hero block: company name, one-liner, 4 KPI MetricCards in a row
- 13 SectionEditor cards rendered sequentially
- Animated gradient dividers between sections
- Progressive reveal: sections fade+slide as data arrives

Dependencies: MetricCard, SectionEditor, ConfidenceBadge
Estimated size: ~250 lines

### Step 1.5: Strategy Map View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/views/StrategyMap.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/MarketNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/CustomerNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/CompetitorNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/ProductNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/RevenueNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/FinanceNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/RiskNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/MilestoneNode.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/nodes/ExitNode.tsx

What to build:
- ReactFlowWrapper with 9 custom node types registered
- ELKjs auto-layout (top-to-bottom)
- Each node: styled card with icon, title, key data, ConfidenceBadge
- MarketNode: 3D globe on hover using React Three Fiber Canvas inside node (IntersectionObserver gated)
- Click node: Intel Sidebar shows section evidence
- Double-click: SectionEditor modal
- Right-click: context menu (Regenerate, View Sources, Mark Reviewed)
- Stale nodes: pulsing amber border

Dependencies: ReactFlowWrapper, ELKjs (elkjs npm package), @react-three/fiber, @react-three/drei (both already in stack)
Estimated size: ~800 lines total across 10 files

### Step 1.6: Metrics Dashboard View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/views/MetricsDashboard.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/charts/MarketSizeDonut.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/charts/RevenueProjection.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/charts/CompetitiveRadar.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/charts/RiskHeatmap.tsx
- lliveupdatedstreaming/src/features/intelligence/business-plan/charts/MilestoneTimeline.tsx

What to build:
- CSS Grid layout (2 columns desktop, 1 mobile)
- MarketSizeDonut: Recharts PieChart with TAM/SAM/SOM data
- RevenueProjection: Recharts AreaChart with 3 scenario lines and toggle
- CompetitiveRadar: Recharts RadarChart (you vs 3 competitors, 6 dimensions)
- RiskHeatmap: Recharts ScatterChart (Impact Y vs Probability X, color by severity)
- MilestoneTimeline: custom Framer Motion horizontal timeline with milestone dots and popovers
- Unit Economics KPI grid using MetricCards
- Industry Benchmark bar chart using Recharts BarChart

Dependencies: recharts, MetricCard, framer-motion
Estimated size: ~700 lines total across 6 files

### Step 1.7: Full Report View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/views/FullReport.tsx

What to build:
- Single column (max-width 800px), centered, Playfair Display headings, Inter body
- Sticky Table of Contents sidebar
- Smooth scroll-to-section
- Print-optimized @media print CSS
- Reading progress bar (scroll position / total height)
- 13 sections with section numbers, ConfidenceBadges, embedded static charts, citation links

Dependencies: SectionEditor (read-only mode), ConfidenceBadge
Estimated size: ~300 lines

### Step 1.8: Sources and Evidence View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/views/SourcesEvidence.tsx

What to build:
- Two-column: source list (left), detail preview (right)
- Sources grouped by type
- Click source: right panel shows full snippet, metadata, "Sections Using This Source"
- "Add Manual Source" button
- "Refresh Sources" button

Dependencies: ConfidenceBadge
Estimated size: ~250 lines

### Step 1.9: Edit Mode View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/views/EditMode.tsx

What to build:
- Split view: editable sections (left), live markdown preview (right)
- 13 SectionEditors in edit mode
- "/" commands and AI Sparkle active
- Auto-save 5s debounce
- "Save and Update Bundle" button

Dependencies: SectionEditor
Estimated size: ~200 lines

### Step 1.10: Version History View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/business-plan/views/VersionHistory.tsx

What to build:
- Full-page VersionHistoryDrawer
- Compare and restore functionality

Dependencies: VersionHistoryDrawer
Estimated size: ~100 lines

### Step 1.11: Route Registration

Files to modify:
- lliveupdatedstreaming/src/App.tsx

What to change:
- Add lazy-loaded route: /business-plan -> BusinessPlanInput
- Add lazy-loaded route: /canvas/business-plan/:taskId -> BusinessPlanCanvas
- Redirect /formforbusiness -> /business-plan

### Step 1.12: Backend -- Enhanced Business Plan Output

Files to modify:
- Server1_FastApi/app/services/business_service.py
- Server1_FastApi/app/api/routes/business_routes_refactored.py

What to change:
- Integrate prompt_enhancer.py into the generation pipeline
- Each of the 13 section prompts enhanced with web enrichment context and depth instructions
- Response structure upgraded to include key_metrics, visualization_spec, strategic_nodes, citations per section
- OutputValidator runs on every section before returning
- Existing endpoints preserved, response shape extended (backwards compatible)

Phase 1 total: ~3,550 lines across ~25 files
Cumulative: ~8,000 lines

SHIP CHECKPOINT: Business Plan is fully functional with dual-mode input, 7-view canvas, React Flow strategy map, metrics dashboard, editing, evidence, version history, and enhanced AI output.

---

## Phase 2: GTM Canvas

### Step 2.1: GTMStrategyInput Page

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/GTMStrategyInput.tsx

What to build:
- DualModeInput with emerald accent
- GTM structured form config (6 sections matching current 18 fields)
- Service access check (service ID 316)
- On generate: call POST /generate_gtm_plan or POST /generate_gtm_plan_async
- Navigate to /canvas/gtm/:taskId

Dependencies: DualModeInput, CanvasThemeProvider
Estimated size: ~300 lines

### Step 2.2: GTMCanvas Shell

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/GTMCanvas.tsx

What to build:
- Horizontal tab bar (7 tabs), main content, Mission Metrics Bar (bottom)
- Header with GTM mode badge, budget, risk appetite
- Tab switching with AnimatePresence
- Fetch GTM plan data on mount

Dependencies: CanvasThemeProvider (emerald), ExportToolbar
Estimated size: ~350 lines

### Step 2.3: Mission Metrics Bar

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/MissionMetricsBar.tsx

What to build:
- Fixed bottom bar with 6 key metrics (CAC, LTV, LTV:CAC, Payback, Target MRR, Launch Date)
- Trend arrows per metric
- Click metric navigates to relevant section
- Responsive: collapses to 3 on mobile

Dependencies: MetricCard
Estimated size: ~150 lines

### Step 2.4: War Room View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/views/WarRoom.tsx

What to build:
- Bento grid (CSS Grid 12-column) with cards
- Cards: Strategic Thesis, 100-Day Battle Plan timeline, ICP, Pricing, Top Channels, Risk Appetite gauge, Competitive Radar, Market Opportunity donut
- Each card clickable to relevant tab
- Scan-line entry animation

Dependencies: MetricCard, ConfidenceBadge, recharts
Estimated size: ~400 lines

### Step 2.5: Launch Map View (React Flow)

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/views/LaunchMap.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/nodes/ICPNode.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/nodes/PositioningNode.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/nodes/ChannelNode.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/nodes/PricingNode.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/nodes/LaunchPhaseNode.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/nodes/ExperimentNode.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/nodes/KPINode.tsx

What to build:
- ReactFlowWrapper with 7 custom node types
- ELKjs auto-layout direction: RIGHT
- Channel branching pattern: ICP > Positioning > Pricing > Channels (fan out) > Launch Phases
- Drag channels to reprioritize
- Right-click channel: "Reallocate Budget" modal

Dependencies: ReactFlowWrapper, elkjs
Estimated size: ~700 lines total across 8 files

### Step 2.6: Funnel View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/views/FunnelView.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/charts/FunnelSVG.tsx

What to build:
- Interactive vertical SVG funnel (6 stages)
- Each stage: volume, conversion rate, active channels
- Click stage: expand detail panel
- Animated flow particles (emerald dots, Framer Motion)
- "What-if" slider: drag conversion rate, downstream recalculates
- Conversion % on arrows between stages
- Funnel widths proportional to actual numbers

Dependencies: framer-motion
Estimated size: ~500 lines across 2 files

### Step 2.7: Channel Deep-Dive View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/views/ChannelDeepDive.tsx

What to build:
- Horizontal card carousel (scrollable)
- Detail panel below expanding on card selection
- Channel cards: color-coded, budget % ring, status badge
- Detail: budget, CAC, leads, tactics, experiments
- "Add Channel" with AI suggestions

Dependencies: MetricCard, framer-motion
Estimated size: ~350 lines

### Step 2.8: Experiment Board View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/views/ExperimentBoard.tsx

What to build:
- Kanban: Planned, Running, Completed columns
- Drag-and-drop between columns
- Experiment cards: name, channel, metric, priority, duration progress
- "Suggest Experiment" AI button

Dependencies: framer-motion (for drag), or @hello-pangea/dnd
Estimated size: ~350 lines

### Step 2.9: KPI Board View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/views/KPIBoard.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/charts/CACByChannel.tsx
- lliveupdatedstreaming/src/features/intelligence/gtm/charts/GrowthTrajectory.tsx

What to build:
- Dashboard grid with all chart widgets
- North Star Metric card, Revenue Projection, CAC by Channel, Funnel Conversion, Budget Donut, Growth Rate, Leading/Lagging indicators, Milestone Tracker
- Editable assumptions with "What-If" sliders

Dependencies: recharts, MetricCard
Estimated size: ~500 lines across 3 files

### Step 2.10: GTM Full Report View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/gtm/views/FullReport.tsx

What to build:
- 15 sections, military numbering
- Embedded mini-charts, tables for Tactical Roadmap and 100-Day Plan
- Risk gauge inline

Dependencies: SectionEditor (read-only), ConfidenceBadge
Estimated size: ~300 lines

### Step 2.11: Route Registration

Files to modify:
- lliveupdatedstreaming/src/App.tsx

What to change:
- /gtm-strategy -> GTMStrategyInput (lazy)
- /canvas/gtm/:taskId -> GTMCanvas (lazy)

### Step 2.12: Backend -- Enhanced GTM Output

Files to modify:
- Server1_FastApi/app/services/gtm_service_refactored.py
- Server1_FastApi/app/api/routes/gtm_routes_refactored.py

What to change:
- Integrate prompt_enhancer.py
- Enhanced per-section structured output: metrics, channel_data, experiment_data, funnel_data, timeline_data, node_spec
- Web enrichment injection for real competitor data
- OutputValidator integration

Phase 2 total: ~3,900 lines across ~20 files
Cumulative: ~11,900 lines

SHIP CHECKPOINT: GTM is fully functional with dual-mode input, 7-tab command center, War Room bento grid, Launch Map React Flow, interactive funnel, channel deep-dive, experiment board, KPI dashboard, Mission Metrics Bar.

---

## Phase 3: SWOT Canvas

### Step 3.1: SWOTAnalysisInput Page

Files to create:
- lliveupdatedstreaming/src/features/intelligence/swot/SWOTAnalysisInput.tsx

What to build:
- DualModeInput with violet accent
- SWOT structured form config (3 sections)
- Service access check (service ID 309)
- AI Suggest buttons per SWOT quadrant field

Dependencies: DualModeInput
Estimated size: ~250 lines

### Step 3.2: SWOTCanvas Shell

Files to create:
- lliveupdatedstreaming/src/features/intelligence/swot/SWOTCanvas.tsx

What to build:
- Horizontal tab bar (5 tabs), main content area
- Violet accent theming
- Fetch SWOT plan data (GET /api/swot/:planId)

Dependencies: CanvasThemeProvider (violet), ExportToolbar
Estimated size: ~300 lines

### Step 3.3: Quadrant Matrix View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/swot/views/QuadrantMatrix.tsx

What to build:
- Full-screen 2x2 grid with 4 colored quadrants
- SWOT item cards: title, description, impact slider, ConfidenceBadge, category tag, source link, drag handle, edit/delete
- Drag items between quadrants
- "+ Add" and "Suggest More" per quadrant
- Entry animation: quadrants from corners, items cascade 80ms stagger

Dependencies: ConfidenceBadge, framer-motion
Estimated size: ~500 lines

### Step 3.4: TOWS Actions View (React Flow)

Files to create:
- lliveupdatedstreaming/src/features/intelligence/swot/views/TOWSActions.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/nodes/StrengthNode.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/nodes/WeaknessNode.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/nodes/OpportunityNode.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/nodes/ThreatNode.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/nodes/ActionNode.tsx

What to build:
- Left column: SWOT items grouped by quadrant
- Right column: Action nodes
- Color-coded animated edges: SO (emerald), WO (blue), ST (amber), WT (rose)
- User can drag new connections
- ActionNode: editable priority (P1/P2/P3), owner, timeline, status

Dependencies: ReactFlowWrapper
Estimated size: ~600 lines across 6 files

### Step 3.5: Risk Radar View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/swot/views/RiskRadar.tsx

What to build:
- Center: Recharts RadarChart (6 dimensions)
- Surrounding: risk detail cards per category
- Below: Impact vs Probability scatter plot
- "What-if" toggle: remove risk, radar reshapes

Dependencies: recharts, MetricCard
Estimated size: ~350 lines

### Step 3.6: Deep Dive View (Sub-Analyses)

Files to create:
- lliveupdatedstreaming/src/features/intelligence/swot/views/DeepDive.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/sub-views/CompetitorTable.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/sub-views/ValuePropCanvas.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/sub-views/MarketSegBubble.tsx
- lliveupdatedstreaming/src/features/intelligence/swot/sub-views/RiskDetail.tsx

What to build:
- Vertical accordion with 4 expandable sections
- CompetitorTable: table (competitors as columns, dimensions as rows), "Add Competitor"
- ValuePropCanvas: 2-panel visual (Customer Profile vs Value Proposition), draggable items, connecting lines
- MarketSegBubble: Recharts ScatterChart as bubble chart (size = segment, color = growth)
- RiskDetail: full text sections from Risk Analysis sub-service
- Each with Regenerate button and ConfidenceBadge

Dependencies: recharts, ConfidenceBadge
Estimated size: ~700 lines across 5 files

### Step 3.7: SWOT Full Report View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/swot/views/FullReport.tsx

What to build:
- Inline 2x2 matrix as styled table
- TOWS action table
- Embedded risk radar, value prop canvas, market seg bubble, competitor table

Dependencies: SectionEditor (read-only)
Estimated size: ~300 lines

### Step 3.8: Route Registration + Backend Enhancement

Files to modify:
- lliveupdatedstreaming/src/App.tsx
- Server1_FastApi/app/services/swot_service_refactored.py
- Server1_FastApi/app/api/routes/swot_routes.py

What to change:
- Routes: /swot-analysis -> SWOTAnalysisInput, /canvas/swot/:taskId -> SWOTCanvas
- Backend: integrate prompt_enhancer, enhanced SWOT item schema with impact/confidence/category/tows_actions, web enrichment for real competitor data, OutputValidator

Phase 3 total: ~3,000 lines across ~18 files
Cumulative: ~14,900 lines

SHIP CHECKPOINT: SWOT is fully functional with interactive 2x2 matrix, TOWS React Flow graph, risk radar, 4 sub-analyses, value proposition canvas, market segmentation bubbles.

---

## Phase 4: Pitch Canvas

### Step 4.1: PitchAnalysisInput Page

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/PitchAnalysisInput.tsx

What to build:
- DualModeInput with amber accent
- Pitch structured form config (2 sections: context + file upload)
- Drag-and-drop file upload zone
- Expansion pipeline integration (existing expandPrompt/finalizeProfile flow)

Dependencies: DualModeInput
Estimated size: ~350 lines

### Step 4.2: PitchCanvas Shell

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/PitchCanvas.tsx

What to build:
- Horizontal tab bar (7 tabs), main content area
- Header: readiness score, slide count, issue count, rewrites needed
- Amber accent theming

Dependencies: CanvasThemeProvider (amber), ExportToolbar
Estimated size: ~300 lines

### Step 4.3: Score Card View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/views/ScoreCard.tsx
- lliveupdatedstreaming/src/features/intelligence/pitch/charts/ReadinessGauge.tsx
- lliveupdatedstreaming/src/features/intelligence/pitch/charts/DimensionScores.tsx

What to build:
- Large circular ReadinessGauge (Recharts RadialBarChart, animated count-up)
- DimensionScores row: 5 mini gauges (Problem, Solution, Market, Traction, Team)
- Top Strengths / Top Weaknesses lists
- Investor Verdict paragraph
- Entry animation: gauge 0 to score, cards flip in

Dependencies: recharts, MetricCard
Estimated size: ~400 lines across 3 files

### Step 4.4: Slide Rail View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/views/SlideRail.tsx

What to build:
- Horizontal scroll of slide thumbnails with letter grades and color coding
- Detail panel below for selected slide
- Issues with severity badges
- Evidence check with MISMATCH detection
- AI rewrite suggestion with Accept/Edit/Dismiss

Dependencies: ConfidenceBadge
Estimated size: ~450 lines

### Step 4.5: Objection Board View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/views/ObjectionBoard.tsx

What to build:
- Kanban: Critical, Moderate, Minor columns
- Cards: investor question, triggering slide, severity
- "View Answer" expander with AI talking points
- "Add to Deck" action
- User can add custom objections

Dependencies: framer-motion
Estimated size: ~350 lines

### Step 4.6: Story Arc View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/views/StoryArc.tsx
- lliveupdatedstreaming/src/features/intelligence/pitch/charts/StoryArcChart.tsx

What to build:
- Recharts AreaChart showing narrative tension across slides
- Clickable dots per slide
- AI commentary below on narrative structure

Dependencies: recharts
Estimated size: ~250 lines across 2 files

### Step 4.7: Evidence Check View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/views/EvidenceCheck.tsx

What to build:
- Two-column: Claims (left), Evidence (right)
- Color-coded: match (green), close (amber), mismatch (red), unverifiable (gray)
- "Fix" button per mismatch

Dependencies: ConfidenceBadge
Estimated size: ~300 lines

### Step 4.8: Rewrite Queue View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/views/RewriteQueue.tsx

What to build:
- Prioritized list: priority badge, slide ref, current vs suggested, Accept/Edit/Dismiss
- "Apply All Accepted" batch button
- Progress indicator

Estimated size: ~250 lines

### Step 4.9: Pitch Full Report View

Files to create:
- lliveupdatedstreaming/src/features/intelligence/pitch/views/FullReport.tsx

What to build:
- All 8 report sections sequentially

Dependencies: SectionEditor (read-only)
Estimated size: ~250 lines

### Step 4.10: Route Registration + Backend Enhancement

Files to modify:
- lliveupdatedstreaming/src/App.tsx
- Server1_FastApi/app/services/pitch_service_refactored.py
- Server1_FastApi/app/api/routes/pitch_analysis_routes_refactored.py

What to change:
- Routes: /pitch-analysis -> PitchAnalysisInput, /canvas/pitch/:taskId -> PitchCanvas
- Backend: integrate prompt_enhancer, enhanced claim verification schema, web-search fact checking for every deck claim, OutputValidator

Phase 4 total: ~2,900 lines across ~15 files
Cumulative: ~17,800 lines

SHIP CHECKPOINT: Pitch is fully functional with score card, slide-by-slide analysis, objection board, story arc visualization, evidence-based fact checking, rewrite queue.

---

## Phase 5: Polish and Advanced Features

### Step 5.1: 3D Enhancements

Files to create/modify:
- Business Plan MarketNode: Add Three.js globe with highlighted market regions
- GTM War Room: Optional 3D funnel preview using Three.js
- Entry animations: add particle systems for canvas load sequences

### Step 5.2: What-If Scenario Engine

Files to create:
- lliveupdatedstreaming/src/features/intelligence/shared/ScenarioSlider.tsx

What to build:
- Reusable slider panel for adjusting assumptions
- Client-side recalculation of dependent metrics
- Used in GTM Funnel View, KPI Board, Business Plan financial projections

### Step 5.3: Multiplayer Awareness (Future)

Placeholder architecture for:
- Real-time cursor presence via WebSocket
- Collaborative editing locks
- Activity feed sidebar

### Step 5.4: Accessibility Audit

- ARIA labels on all interactive elements
- Keyboard navigation for React Flow nodes
- Screen reader support for charts (data tables as fallback)
- Focus management in drawers and modals

---

## Phase 6: Testing and Hardening

### Step 6.1: Component Unit Tests

- ConfidenceBadge: renders all 6 levels, 3 sizes
- MetricCard: renders all 4 variants
- EvidenceDrawer: opens/closes, filters, highlights
- SectionEditor: edit mode toggle, save, regenerate
- ExportToolbar: triggers correct format handler
- Each canvas: renders with mock data, tab switching works

### Step 6.2: Integration Tests

- BusinessPlanInput: prompt submission flow, form submission flow, cross-pollination
- Each Canvas: loads task result, renders all views, evidence drawer interaction
- WebSearchContext: entity detection, enrichment cards, competitor snapshot

### Step 6.3: E2E Tests

- Full flow: Input -> Generate -> Canvas -> Edit -> Export for each service
- Deep mode: WebSocket progress tracking through to result display
- Export: PDF/DOCX download verification

### Step 6.4: Performance

- React Flow: verify smooth rendering with 30+ nodes
- Three.js: verify no memory leaks with IntersectionObserver gating
- Bundle size: verify code splitting works for each canvas (lazy loading)
- Lighthouse audit: target 80+ performance score per canvas page

---

## Dependency Installation

New npm packages needed (not already in stack):
- elkjs: Auto-layout for React Flow graphs
- @hello-pangea/dnd: Drag-and-drop for Kanban boards (Experiment Board, Objection Board)

All other dependencies are already installed:
- @xyflow/react (React Flow)
- recharts
- @react-three/fiber, @react-three/drei (Three.js)
- framer-motion
- react-quill
- jspdf, html2canvas, docx
- lucide-react

---

## Summary

| Phase | Scope | Files | Lines (est.) | Ships |
|-------|-------|-------|-------------|-------|
| 0 | Shared Brain | ~20 | ~4,450 | Foundation only |
| 1 | Business Plan | ~25 | ~3,550 | BP Input + Canvas |
| 2 | GTM Strategy | ~20 | ~3,900 | GTM Input + Canvas |
| 3 | SWOT Analysis | ~18 | ~3,000 | SWOT Input + Canvas |
| 4 | Pitch Deck | ~15 | ~2,900 | Pitch Input + Canvas |
| 5 | Polish | ~5 | ~800 | 3D, Scenarios, A11y |
| 6 | Testing | ~15 | ~2,000 | Full test suite |
| TOTAL | | ~118 | ~20,600 | |

Priority execution: Phase 0 -> Phase 1 (SHIP) -> Phase 2 (SHIP) -> Phase 3 (SHIP) -> Phase 4 (SHIP) -> Phase 5 -> Phase 6
