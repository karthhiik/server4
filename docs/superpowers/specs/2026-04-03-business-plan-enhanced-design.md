# Business Plan Canvas: Enhanced Input → Generation → Output Design
**Date:** 2026-04-03
**Status:** APPROVED FOR IMPLEMENTATION
**Project:** Barise Server1_FastApi + lliveupdatedstreaming (Business Plan Module Only)
**Scope:** Task-3 & Task-4 (Enhanced Business Plan with Prompt + PDF + Form Input, Silent Generation, Multi-User Canvas)

---

## EXECUTIVE SUMMARY

This design specification covers the complete Business Plan workflow from input to output:

1. **3-Mode Input System** (Prompt + PDF + Form) with Fast/Deep research options
2. **Silent Resilient Generation** (guaranteed completion, APIs fail gracefully)
3. **Real-Time Multi-User** (Yjs CRDT collaborative editing)
4. **Premium Canvas Display** (7 views with Pretext 3D animations)
5. **Streaming Progress UI** (3D timeline showing Research → Analysis → Synthesis)
6. **Cost Management** (smart throttling, credit tracking, cache optimization)

**Key Principles:**
- Users never see API failures — backend handles silently with automatic fallbacks
- Generation **always completes** (quality degrades gracefully, never fails)
- Multiple users can edit the same plan **simultaneously** with Yjs CRDT (conflict-free merging)
- 3D animations + Pretext transforms for premium UX (balanced for performance)
- Credits tracked but hidden — user focus is on quality, not cost
- Ideas Workshop generates 10-15 innovative business pivots after plan completion

---

## 1. INPUT SYSTEM (3 Independent Modes)

### 1.1 Architecture

Users access Business Plan input page with **3 separate card sections** (all visible simultaneously):

1. **Prompt-Based Input** — Textarea with company name, Fast/Deep toggle
2. **PDF/Pitch Deck Input** — File upload with optional context, Fast/Deep toggle
3. **Structured Form Input** — 8-section accordion with optional fields, Fast/Deep toggle

Each mode is independent. User can fill any combination before submission.

**Time Estimates (Shown to User):**
```
Prompt Mode:
  Fast: 20-45 seconds | Deep: 90-240 seconds

PDF Mode:
  Fast: 30-60 seconds | Deep: 120-300 seconds

Form Mode:
  Fast: 20-45 seconds | Deep: 60-180 seconds
```

### 1.2 Mode Details

#### Prompt-Based Input
**Component:** `BusinessPlanInput.tsx` → `StrategyPromptInput.tsx`

```
Field: Textarea (min 20 characters)
Placeholder: "Give business plan for Amazon"
Auto-detected: Entity extraction on blur (debounce 500ms)
Shows detected companies inline with search status
Research toggle: Fast | Deep (with credit estimate)
Generate button: Submits with full prompt context
```

**Flow:**
1. User types prompt → debounce 500ms
2. Call `POST /api/intelligence/detect-entities` → extract companies
3. Display: "🔍 Detecting: Amazon, AWS, Competitors..."
4. User selects research mode → show time/credit estimate
5. Submit → merge prompt + research mode + companies

#### PDF/Pitch Deck Upload
**Component:** `BusinessPlanInput.tsx` → `PitchDeckUpload.tsx`

```
Field: Drag-drop zone (accepts PDF, PPTX, PPT, max 50MB)
Alternative: Browse button
Supported: PDF, PowerPoint formats
Optional context: Small textarea for additional notes
Research toggle: Fast | Deep
Generate button: Uploads → extracts → generates
```

**Flow:**
1. User drags/selects file
2. Validate: File type, size
3. Call `POST /api/server2/extract` (Server2 service wrapper) → extract text + structure
4. Auto-detect companies in PDF
5. User selects research mode
6. Submit → merge PDF structure + optional context + research mode

#### Structured Form Input
**Component:** `BusinessPlanInput.tsx` → `StructuredFormAccordion.tsx`

**8 Sections (All Optional):**
```
1. Business Identity
   □ Company Name
   □ Industry
   □ Business Type
   □ Current Stage

2. Vision and Value
   □ One-liner Hook
   □ Founder Mission
   □ Unique Value Prop
   □ Unfair Advantage

3. Market and Customers
   □ Target Market
   □ Customer Persona
   □ Market Size
   □ Geographic Focus

4. Product and Tech
   □ Core Product
   □ Core Features
   □ Tech Stack
   □ Tech Infrastructure

5. Competition
   □ Competitor 1 (name + weakness)
   □ Competitor 2 (name + weakness)
   □ Competitor 3 (name + weakness)
   □ Positioning

6. Business Model
   □ Revenue Sources
   □ Pricing Strategy
   □ Acquisition Channels
   □ Marketing Channels

7. Team and Operations
   □ Founding Team roles
   □ Team Size
   □ Hiring Needs
   □ Partnerships

8. Financials and Risk
   □ Current Funding
   □ Burn Rate
   □ Revenue
   □ Runway
   □ Risk Appetite (1-10 slider)
   □ Biggest Threats
```

**AI Assist Buttons (Selected Fields):**
- "Suggest Target Market"
- "Find Competitors" (web search)
- "Suggest Revenue Model"
- "Suggest USP"
- "Estimate Runway"

**Research Toggle:** Fast | Deep
**Form-to-Prompt:** Generate one-liner summary from filled fields

### 1.3 Intelligent Input Merging

If user fills **multiple modes**, backend determines priority:

```
Data Completeness Algorithm:
├─ Score each mode: (fields_filled / total_fields) * 100
├─ Primary source = highest score
├─ Secondary/tertiary = enrichment
├─ Example: PDF (70%) > Form (30%) > Prompt (20%)
│          → PDF is backbone, form + prompt clarify
└─ Merge all three into unified context for generation
```

---

## 2. GENERATION PIPELINE (Silent + Resilient)

### 2.1 Core Flow

```
User submits (any mode combination + research mode)
    ↓
input_processor.py
├─ Merge all 3 modes intelligently
├─ Extract all companies/competitors
├─ Validate & clean data
└─ Return unified context
    ↓
web_enrichment.py (Silent Fallback Strategy)
├─ Attempt 1: search-hub-mcp (real-time)
├─ Attempt 2: Fallback search provider
├─ Attempt 3: Cosmos DB cache (2+ hours)
└─ ALWAYS return something (worst case: form data)
    ↓
business_plan_engine.py
├─ Generate 13 sections with LLM (with multi-model fallback)
├─ Extract metrics for charts
├─ Extract nodes for React Flow
├─ Assign confidence scores
└─ Stream section completion via WebSocket
    ↓
ideas_generator.py (After main plan)
├─ Generate 10-15 business pivots/ideas
├─ Use main plan as context
├─ Each idea: description, market opportunity, confidence
└─ User can "Expand into Full Plan" for any idea
    ↓
Output to Cosmos DB + Yjs CRDT
├─ Store complete artifact
├─ Enable real-time sync for editing
├─ Record metadata (user, timestamp, research mode, credits)
└─ Ready for canvas display
```

### 2.2 Silent Failure Handling

**Zero user-facing errors.** All failures handled with automatic fallbacks:

**Web Search Failures:**
- Timeout → Retry 3x with exponential backoff (2s → 4s → 8s)
- Rate limited → Use cached data from 2-hour cache
- No results → Continue with user input only
- All APIs down → Use form data as-is

**LLM Generation Failures:**
- Rate limit → Queue in background, notify user "continues", switch to cheaper model
- Model unavailable → Failover: OpenAI → DeepSeek → Mistral → Groq → template
- Timeout → Retry same model, then switch to faster model
- Token limit exceeded → Truncate context, use shorter generation
- Malformed response → Retry with explicit structure prompt, then template
- Content policy blocked → Rephrase prompt, retry once, then use template

**Server2 PDF Extraction Failures:**
- Endpoint down → Timeout after 30s, retry 2x, then skip PDF (use form+prompt)
- Corrupted PDF → Try OCR approach or return extracted text with low confidence
- Encrypted/unreadable → Show warning, allow user to skip or use form

**Database Failures (Cosmos DB):**
- Connection timeout → Retry 3x, then queue to Redis
- Write conflict → Apply Yjs CRDT merge algorithm
- Transaction failure → Rollback, retry in background every 5 minutes
- Quota exceeded → Check user limits, show upgrade suggestion

**WebSocket Disconnections:**
- Connection drops → Client auto-reconnects (exponential backoff, 10 attempts)
- Timeout → Backend continues generation, cache results
- User closes browser → Backend finishes, results ready when user returns

### 2.3 Data Quality Scoring (Internal Only)

```
Base: 100/100
Penalties:
  Web search failed: -15
  PDF not processed: -20
  LLM timeout, recovered: -5
  Cache used: -10
  Template fallback: -25
  Form-only generation: -15

Never reveals to user (minimum quality: 60/100)
Used for:
  ✅ Internal logging/debugging
  ✅ Monitoring dashboards (DevOps)
  ✅ Background quality-tracking
  ✗ Never shown to user
```

### 2.4 WebSocket Streaming Events

Real-time updates sent to frontend:

```json
{
  "type": "web_search_started",
  "company": "Amazon",
  "research_mode": "deep"
}

{
  "type": "web_search_result",
  "company": "Amazon",
  "results": [...],
  "extracted_data": { "revenue": "$200B", "market_cap": "$2.1T", ... },
  "progress": "2/5 companies"
}

{
  "type": "section_complete",
  "section": 1,
  "section_name": "Executive Summary",
  "content": "...",
  "confidence": "verified",
  "citations": [...],
  "key_metrics": [...],
  "react_flow_node": {...},
  "progress": "1/13"
}

{
  "type": "ideas_ready",
  "ideas": [...]
}

{
  "type": "generation_complete",
  "artifact_id": "artifact_789",
  "total_time_ms": 67000,
  "credits_used": 15
}
```

---

## 3. REAL-TIME MULTI-USER (Yjs CRDT + Presence)

### 3.1 Architecture

**Scenario A + B Hybrid:**
- **A:** Users generate plans independently (no conflict)
- **B:** Same plan edited by multiple team members simultaneously (conflict-free)

**Technology:** Yjs CRDT + WebSocket broadcasting

### 3.2 Yjs Integration

**Client-Side (Frontend):**
```typescript
const ydoc = new Y.Doc();
const ymap = ydoc.getMap('business_plan');
const ysections = ydoc.getArray('sections');

const provider = new WebsocketProvider(
  `wss://${API_HOST}/yjs/${artifactId}`,
  'business-plan-room',
  ydoc
);

// Edit → automatic broadcast + conflict-free merge
const editSection = (index, content) => {
  ysections.get(index).set('content', content);
};
```

**Server-Side (Backend):**
```python
# Load artifact into Yjs
ydoc = load_artifact_to_yjs(artifact_id)

# Broadcast updates from clients
await broadcast_yjs_update(artifact_id, update)

# Persist to Cosmos DB (debounced, every 5s)
await persist_to_cosmos_async(artifact_id, ydoc)

# Add to version history
await version_history_service.add_version(artifact_id, content)
```

### 3.3 Conflict-Free Merging

CRDT guarantees: **All users see the same final result, no manual conflict resolution needed**

Example:
```
User A edits: "Amazon is a e-commerce leader"
             → "Amazon is a global e-commerce leader"

User B (simultaneously) edits:
             "Amazon is a e-commerce leader"
             → "Amazon is the leading e-commerce platform"

Result (CRDT): "Amazon is the leading global e-commerce platform"
             ✅ Both changes applied, grammatically correct, no conflicts
```

### 3.4 Presence Tracking

Display awareness indicators:

```typescript
// Other users' cursors visible in sections they're editing
// Type indicators: "John is editing Section 5..."
// Auto-clear after 5 minutes of inactivity
```

### 3.5 Notifications

Rich real-time notifications:

```
🟡 INFO: "John is viewing Section 5"
🔵 EDIT: "Maria updated Section 2 (Market Analysis)" → [View Changes]
✅ AUTO: "Plan auto-saved"
```

### 3.6 Concurrent Editing Limits

```
Max 5 simultaneous editors per plan
6th+ user → read-only mode (can watch/comment, not edit)
Can still view, comment, suggest edits
```

---

## 4. BUSINESS PLAN CANVAS (7 Views + Pretext 3D)

### 4.1 Layout

```
┌─────────────────────────────────────────────────┐
│ Header: Logo | "Company Plan" | User Menu       │
├──────────┬─────────────────────────┬────────────┤
│ Nav Rail │   Main Content          │ Intel      │
│ (64px)   │   (AnimatePresence)     │ Sidebar    │
│          │                          │ (320px,    │
│ 1️⃣ Exe   │ View 1: Executive Sum.  │ collapsible)
│    Summ  │ [Hero + 13 Sections]    │            │
│          │ Pretext 3D animations   │ • Market   │
│ 2️⃣ Strat │                          │   Snapshot │
│    Map   │                          │ • Source   │
│          │                          │   Confid.  │
│ 3️⃣ Metr  │                          │ • AI Conf  │
│    Dash  │                          │   Gauge    │
│          │                          │ • Enrich   │
│ 4️⃣ Full  │                          │   Used     │
│    Rept  │                          │ • Quick    │
│          │                          │   Actions  │
│ 5️⃣ Sour  │                          │            │
│    Evid  │                          │            │
│          │                          │            │
│ 6️⃣ Edit  │                          │            │
│    Mode  │                          │            │
│          │                          │            │
│ 7️⃣ Vers  │                          │            │
│    Hist  │                          │            │
└──────────┴─────────────────────────┴────────────┘

Export Toolbar (fixed bottom-right):
┌─────────────────┐
│ ↓ [Expand]      │
├─────────────────┤
│ 📄 PDF          │
│ 📘 DOCX         │
│ 📝 Markdown     │
│ 🖼️  PNG         │
│ {} JSON         │
└─────────────────┘
```

### 4.2 View 1: Executive Summary (Default)

**Hero Block:**
- Company logo/name
- One-liner headline
- 4 MetricCards (TAM, Revenue, Team, Runway) with sparklines

**13 Section Cards:**
- Each section: title, ConfidenceBadge, content (500-1200 words), key metrics, citations
- Pretext 3D entrance animations (staggered)
- Actions: [Edit] [Regenerate] [💬 Comments]

### 4.3 View 2: Strategy Map (React Flow)

**9 Custom Nodes:**
- marketNode (🌍 with 3D globe on hover)
- customerNode
- competitorNode
- productNode
- revenueNode
- financeNode
- riskNode
- milestoneNode
- exitNode

**Auto-Layout:** ELKjs (layered top-to-bottom)
**Primary Flow:** Market → Customer → Product → Revenue → Finance → Exit
**Lateral Connections:** Risk ↔ Finance, Competitor ↔ Product

### 4.4 View 3: Metrics Dashboard (8 Charts)

1. Market Size Donut (TAM/SAM/SOM)
2. Revenue Projections Area (3 scenarios)
3. Competitive Position Radar (5 dimensions)
4. Financial Health Gauge (0-100)
5. Risk Heatmap Scatter (Impact vs Probability)
6. Milestone Timeline (Pretext 3D perspective)
7. Unit Economics (4 KPI cards)
8. Industry Benchmark Bar

### 4.5 View 4: Full Report (Editorial)

- Single-column layout (max-width 800px)
- Reading progress bar (top)
- Sticky Table of Contents (left sidebar)
- All 13 sections sequentially with section numbers
- Embedded charts/tables
- Print-optimized CSS

### 4.6 View 5: Sources & Evidence

**EvidenceDrawer Component:**
- 480px right slide-out panel
- Glass-morphism: `rgba(15, 23, 42, 0.95) + backdrop-filter: blur(12px)`
- 2 Tabs: Evidence | Visuals
- Evidence grouped by confidence: Verified (green) | Corroborated (blue) | Inference (amber) | Weak Signal (red)
- Searchable
- Each source: title, domain, snippet, date, confidence badge

### 4.7 View 6: Edit Mode (Split Editable/Preview)

**Left Panel:**
- Section selector
- React Quill rich text editor
- "/" Command menu: /rewrite, /expand, /add-data, /make-punchier, /simplify
- AI Sparkle button for quick actions

**Right Panel:**
- Live markdown preview
- Real-time sync via Yjs

### 4.8 View 7: Version History (Timeline)

- Timeline view of all versions
- Each version: timestamp, author (user vs AI), change type
- Click to preview / [Show Diff] / [Revert]
- Side-by-side diff view (red/green highlighting)

### 4.9 Shared Brain Components Used

✅ **CanvasThemeProvider** ← Wraps canvas, provides accent color (Blue for Business Plan)
✅ **ConfidenceBadge** ← In sections, metrics, evidence (verified/corroborated/inference/scenario/weak_signal)
✅ **EvidenceDrawer** ← Right slide-out panel with grouped sources
✅ **ExportToolbar** ← Fixed bottom-right with PDF/DOCX/MD/PNG/JSON
✅ **SectionEditor** ← Quill + "/" commands + AI Sparkle + auto-save
✅ **VersionHistoryDrawer** ← Timeline with diffs + restore
✅ **MetricCard** ← 4 variants (number/gauge/sparkline/progress)
✅ **ReactFlowWrapper** ← Pre-configured dark theme with custom business nodes

### 4.10 Pretext 3D Usage

**Full 3D (Expensive, worth it):**
- Progress page: 3D timeline with data flow (wow factor)

**Entrance Animations (Moderate):**
- Executive Summary hero block: perspective transform
- Section cards: staggered flip/fade entrance

**Accent Transforms (Light):**
- Strategy Map containers: light perspective depth
- Milestone Timeline: 3D staggered layout

**No full-page immersion:** Keep readable, balance performance

### 4.11 Color System

```
Business Plan accent: Blue (#3B82F6)
Secondary: #1E40AF
Glow: rgba(59, 130, 246, 0.2)

All Shared Brain components inherit via CanvasThemeProvider
```

---

## 5. PROGRESS UI (3D TIMELINE STREAMING)

### 5.1 Layout

```
┌──────────────────────────────────────┐
│ Header: Company | Time | Est. Time   │
├──────────────────────────────────────┤
│                                      │
│    3D STAGE TIMELINE (Pretext)        │
│                                      │
│  Stage 1: RESEARCH                   │
│  [Web search bubbles in 3D space]    │
│  ◉ ⊙ ◄─ Data flowing ─► ◉           │
│  AWS Amazon  News  Funding Competitors
│                                      │
│  Stage 2: ANALYSIS                   │
│  [Data processing nodes]             │
│  ◉ ◉ ⏳ Processing...              │
│  Market Analysis  Competitive Pos.   │
│                                      │
│  Stage 3: SYNTHESIS                  │
│  [13 sections coalescing]            │
│  ◉ ◉ ◉ Coalescing...               │
│                                      │
│ ────────────────────────────────────│
│                                      │
│  Real-Time Web Search Results        │
│  ┌────────────────────────────────┐  │
│  │ ✅ Amazon Q1 Earnings Report   │  │
│  │ ✅ AWS Market Share 35%        │  │
│  │ ⏳ Searching competitors... (2/5)
│  └────────────────────────────────┘  │
│                                      │
│  13 Section Progress Bars            │
│  ├─ 1. Executive Summary [████░░░]  │
│  ├─ 2. Market Opportunity [███░░░░] │
│  ├─ 3. Target Customer [██░░░░░░░]  │
│  └─ ... (10 more)                    │
│                                      │
│ 💳 Credit Tracker (Real-Time)        │
│ ├─ Web Search: -4 credits            │
│ ├─ LLM Gen: -2 credits (in progress) │
│ ├─ Total: 6 / 8 estimated           │
│ └─ Balance: 146 credits remaining    │
│                                      │
│ [Cancel] [Minimize to Background]    │
└──────────────────────────────────────┘
```

### 5.2 3D Timeline Stages (Pretext)

**Stage 1: RESEARCH**
- Three.js canvas with floating search bubbles
- Each bubble labeled with company name
- Status indicators: searching/found/error
- Count: "2/5 companies searched"

**Stage 2: ANALYSIS**
- Data processing nodes showing current step
- Spinner on active node
- Status: "Processing: Step 3/6"

**Stage 3: SYNTHESIS**
- Sections coalescing toward center
- Progress bars for each section
- Status: "Generating: 5/13 sections"

**Data Flow Animation:**
- Arrow between stages: "◄─ DATA FLOWING ─►"
- Animated opacity/movement to show data progression

### 5.3 Web Search Feed (Scrolling)

Animated scrolling list of search results:
- Title, domain, snippet, date
- ConfidenceBadge
- New results animate in from right

### 5.4 Section Progress Bars

13 animated progress bars:
- Section number + name
- Blue fill while generating
- Green fill when complete
- Percentage + status text
- Staggered entrance animations

### 5.5 Credit Tracker Display

Real-time cost breakdown:
- Base: 1 credit
- Web Search (per company): 2-5 credits
- LLM Generation: 2-8 credits
- Ideas (optional): 1-3 credits
- Used so far: X / Y estimated
- Projected balance after completion

### 5.6 User Controls

- [Cancel Generation] → Stop, no plan saved, return to input
- [Minimize] → Continue in background, show notification on completion
- Time display: ⏱️ Elapsed | Est. remaining

### 5.7 Mobile Responsive

- <768px: Stages stack vertically, full-width sections
- 768-1024px: Horizontal flow preserved, compact layout
- 1024px+: Full 3D experience with all animations

---

## 6. COST MANAGEMENT & CREDIT SYSTEM

### 6.1 Credit Pricing

```
Base: 1 credit per generation

Web Search:
  Fast: 2 credits per company
  Deep: 5 credits per company
  Cache hit: 0 credits (2-hour TTL)

LLM Generation:
  Fast: 2 credits
  Deep: 8 credits
  Fallback model: 1 credit

Ideas Workshop:
  Fast: 1 credit
  Deep: 3 credits
  Optional (skip to save)

Example Costs:
  Prompt (1 company) + Fast: 6 credits
  PDF (3 companies) + Deep: 27 credits
  Form only (no search) + Fast: 4 credits
```

### 6.2 Pre-Generation Cost Estimation

**Input Page shows:**
- Breakdown: Base + Web Search + LLM Gen + Ideas
- Total estimated credits
- User balance after generation
- Savings suggestions: "Save X credits with Fast mode"
- Time estimate for each research level

### 6.3 Real-Time Credit Tracking (During Generation)

**Progress page displays:**
- Starting balance
- Credits used so far (real-time WebSocket update)
- Breakdown per step (search, generation, ideas)
- Total used / estimated total
- Projected balance
- Disclaimer: "If APIs slow or fallbacks used, cost may vary"

### 6.4 Smart Throttling (Prevent Runaway Costs)

**Rate Limits per User:**
```
Hourly: 100 credits/hour
Daily: 500 credits/day
Max concurrent: 3 simultaneous generations
Max per day: 20 generations
```

**When limit hit:**
- Show warning before generation starts
- Suggest upgrade or wait until reset
- Allow user to choose: proceed or cancel

### 6.5 Web Search Caching (Cost Optimization)

**2-hour TTL:** Reuse same company search within 2 hours
- First search for "Amazon": 2-5 credits
- Second search for "Amazon" within 2h: 0 credits (cached)
- After 2h: Refresh and cost again

**Global cache stats:** Daily report on cache hit rates, credits saved

### 6.6 User Credit Dashboard

**Analytics page shows:**
- Current balance
- Monthly allowance
- Usage chart: progress bar + percentage
- Days remaining at current burn rate
- Recent generations (cost per generation)
- Savings tips: "Use Fast mode, skip ideas, use form-only"
- Upgrade path: [Upgrade Plan]

### 6.7 Graceful Degradation at Low Credits

```
At 80% usage: Yellow warning
At 95% usage: Red warning + upgrade suggestion
At 100% usage: Blocked from generating, can still edit/view/export
```

**What users can do at 0 credits:**
✅ View existing plans
✅ Edit existing plans
✅ Download/export
✅ Comment + collaborate
❌ Generate new plans
❌ Regenerate sections
❌ Use Ideas Workshop

---

## 7. DATA MODELS & APIS

### 7.1 Database Schema (Cosmos DB / MongoDB)

**Artifact Document:**
```json
{
  "_id": ObjectId,
  "type": "business_plan",
  "user_id": "user_123",
  "status": "completed" | "generating" | "failed",
  "metadata": {
    "company_name": "Amazon",
    "headline": "Global E-Commerce Leader",
    "industry": "Technology",
    "stage": "Mature",
    "created_at": "2026-04-03T14:00:00Z",
    "updated_at": "2026-04-03T14:30:00Z",
    "research_mode": "deep",
    "generation_time_ms": 67000,
    "credits_used": 15,
    "data_quality_score": 85
  },
  "sections": [
    {
      "name": "Executive Summary",
      "content_md": "Amazon is a global technology...",
      "confidence": "verified",
      "key_metrics": [
        { "label": "Annual Revenue", "value": "$200B", "source": "Reuters" }
      ],
      "citations": [
        { "id": "c_001", "title": "...", "url": "...", "confidence": "verified" }
      ],
      "chart_data": {...},
      "react_flow_node": {...}
    },
    // ... 12 more sections
  ],
  "ideas": [
    {
      "id": "idea_1",
      "title": "Hyperlocal Grocery (AI-Powered)",
      "description": "...",
      "market_opportunity": "$50B TAM",
      "confidence": "inference"
    },
    // ... 9-14 more ideas
  ],
  "version_history": [
    {
      "id": "v_001",
      "timestamp": "2026-04-03T14:00:00Z",
      "author": "system",
      "change_type": "generated",
      "content_snapshot": {...}
    }
  ],
  "collaborators": [
    { "user_id": "user_456", "role": "editor", "added_at": "..." }
  ]
}
```

**Yjs Document (in Cosmos DB):**
- Stores Yjs update history for collaborative editing
- Enables offline-first sync + conflict-free merging

### 7.2 API Endpoints (New)

These endpoints support the new input system and web enrichment:

```
POST /api/intelligence/detect-entities
├─ Input: { text, artifact_type }
├─ Output: { entities: [{name, type, confidence}] }
├─ Cache: 5 minutes
└─ Model: Utility-tier (fast)

POST /api/intelligence/web-enrich
├─ Input: { entity_name, entity_type, context }
├─ Output: { summary, funding, competitors, market_cap, news, sources }
├─ Cache: 30 minutes
└─ Service: search-hub-mcp (or fallback)

POST /api/intelligence/extract-form-fields
├─ Input: { prompt, artifact_type }
├─ Output: { fields: {...}, confidence_score }
├─ Cache: 5 minutes
└─ Model: Utility-tier (fast extraction)

POST /api/intelligence/competitor-snapshot
├─ Input: { competitor_name, business_context, artifact_type }
├─ Output: { strengths, weaknesses, threat_level, opportunity_gaps, sources }
├─ Cache: None (real-time)
└─ Model: Research-tier (deep)

POST /api/business/generate
├─ Input: { artifact_type, prompt/pdf/form, research_mode, include_ideas }
├─ Output: { task_id }
└─ WebSocket: /ws/progress/{taskId} (streaming)

WebSocket /ws/progress/{taskId}
├─ Streams: web_search_started, web_search_result, section_started, section_complete
├─ Streams: ideas_ready, generation_complete, credits_update
└─ Client receives real-time progress

GET /api/intelligence/artifact/{artifactId}
├─ Returns: Complete artifact with all sections, ideas, metadata
└─ Includes: Yjs state for collaborative editing

GET /api/intelligence/artifact/{artifactId}/presence
├─ Returns: { total_viewers, editors: [{user_id, editing_section, since}] }
└─ Used for real-time presence awareness

POST /api/intelligence/artifact/{artifactId}/section/{sectionIndex}/regenerate
├─ Input: { research_mode }
├─ Output: { task_id } (streaming via WebSocket)
└─ Regenerates single section only

POST /api/intelligence/artifact/{artifactId}/ideas/{ideaId}/expand
├─ Input: { research_mode }
├─ Output: { task_id } (new generation with idea as context)
└─ Generates full plan from single idea

GET /api/user/credits
├─ Returns: { balance, monthly_allowance, daily_usage, warnings }
└─ Shows current credit status

POST /api/user/credits/throttle-check
├─ Input: { estimated_cost }
├─ Output: { allowed: true/false, reason, retry_after }
└─ Checks limits before generation
```

### 7.3 Service Layer

**New Services (Server1_FastApi/app/services/intelligence/):**

```
input_processor.py
├─ parse_prompt(str) → context
├─ parse_pdf(File) → context (call Server2)
├─ parse_form(FormData) → context
└─ merge_contexts(contexts) → unified_context

web_enricher.py
├─ detect_entities(text) → entities[]
├─ search_company(name, mode) → results (with cache)
├─ extract_form_fields(text) → fields
└─ analyze_competitor(name, context) → analysis

business_plan_engine.py (Extended)
├─ generate_business_plan(context, research_mode) → artifact
├─ generate_section(section_idx, context, research_mode) → section
└─ generate_ideas(plan_content, research_mode) → ideas[]

cost_management_service.py (NEW)
├─ estimate_cost(inputs, research_mode) → cost_breakdown
├─ track_generation_cost(user_id, generation_id, actual_cost) → void
├─ check_throttle_limits(user_id, estimated_cost) → allowed/denied
└─ get_user_credit_status(user_id) → status

yjs_sync_service.py (NEW)
├─ load_artifact_to_yjs(artifact_id) → ydoc
├─ broadcast_yjs_update(artifact_id, update) → void
└─ persist_to_cosmos_async(artifact_id, ydoc) → void

error_handler_service.py (NEW)
├─ retry_with_backoff(func, max_attempts) → result
├─ get_fallback_service(service_name) → fallback_service
└─ log_failure_silently(service, error, context) → void
```

---

## 8. FRONTEND FILE STRUCTURE

```
lliveupdatedstreaming/src/
├─ features/intelligence/
│  ├─ shared/
│  │  ├─ CanvasThemeProvider.tsx
│  │  ├─ EvidenceDrawer.tsx
│  │  ├─ ConfidenceBadge.tsx
│  │  ├─ ExportToolbar.tsx
│  │  ├─ ReactFlowWrapper.tsx
│  │  ├─ SectionEditor.tsx
│  │  ├─ VersionHistoryDrawer.tsx
│  │  ├─ MetricCard.tsx
│  │  ├─ WebSearchContext.tsx
│  │  └─ DualModeInput.tsx
│  │
│  ├─ business-plan/
│  │  ├─ BusinessPlanInput.tsx (Enhanced: 3 modes)
│  │  ├─ BusinessPlanCanvas.tsx (7 views)
│  │  ├─ views/
│  │  │  ├─ ExecutiveSummary.tsx (Pretext 3D)
│  │  │  ├─ StrategyMap.tsx (React Flow)
│  │  │  ├─ MetricsDashboard.tsx (8 charts)
│  │  │  ├─ FullReport.tsx
│  │  │  ├─ SourcesEvidence.tsx
│  │  │  ├─ EditMode.tsx (Yjs sync)
│  │  │  └─ VersionHistory.tsx
│  │  ├─ nodes/ (9 custom React Flow nodes)
│  │  │  ├─ MarketNode.tsx
│  │  │  ├─ CustomerNode.tsx
│  │  │  ├─ ... (7 more)
│  │  └─ charts/
│  │     ├─ MarketSizeDonut.tsx
│  │     ├─ RevenueProjection.tsx
│  │     └─ ... (6 more)
│  │
│  ├─ progress/
│  │  ├─ ProgressPage.tsx (Progress container)
│  │  ├─ Timeline3D.tsx (Pretext 3D stages)
│  │  ├─ WebSearchFeed.tsx (Real-time results)
│  │  ├─ SectionProgress.tsx (13 bars)
│  │  └─ CreditTracker.tsx (Cost display)
│  │
│  ├─ hooks/
│  │  ├─ usePresence.ts (Yjs presence aware)
│  │  ├─ useBundleTask.ts
│  │  ├─ useArtifactEdit.ts
│  │  ├─ useCostEstimator.ts (NEW)
│  │  └─ useWebSearch.ts (NEW)
│  │
│  └─ types/
│     ├─ canvas.ts
│     ├─ generation.ts
│     ├─ cost.ts (NEW)
│     └─ presence.ts (NEW)
```

---

## 9. TESTING STRATEGY

### 9.1 Unit Tests

- Web enrichment service (happy path + fallbacks)
- Cost estimation calculator
- Input merging algorithm
- Yjs sync operations

### 9.2 Integration Tests

- Full generation flow: input → web search → LLM → output
- Fallback chains (search fails → cache → form data)
- Yjs CRDT conflicts (simultaneous edits)

### 9.3 E2E Tests

- User submits prompt → sees progress → gets plan → views canvas
- User uploads PDF → extraction → generation → canvas
- User fills form → generation → ideas workshop
- User-A edits Section 2 while User-B edits Section 5 (no conflicts)

### 9.4 Load Testing

- 10+ concurrent generations
- 5+ users editing same plan
- Web search caching efficiency (hit rate)
- Yjs sync latency (<50ms)

---

## 10. SUCCESS CRITERIA

### 10.1 Functionality

✅ 3 input modes work independently
✅ Fast/Deep research modes functional
✅ Web search integrates with search-hub-mcp
✅ PDF extraction via Server2
✅ Generation completes even if APIs fail (graceful degradation)
✅ Business Plan Canvas 7 views fully interactive
✅ Ideas Workshop generates 10-15 ideas
✅ Multi-user editing with Yjs (conflict-free)
✅ Real-time progress streaming (WebSocket)
✅ Credit tracking + throttling enforced

### 10.2 UX/Quality

✅ User never sees API failure messages
✅ 3D animations smooth on desktop (60fps)
✅ Mobile responsive (<768px)
✅ Pretext 3D CSS performant (no jank)
✅ Canvas loads in <5s
✅ Progress page feels real-time (<100ms latency)

### 10.3 Performance

✅ Generation completes in estimated time (or faster)
✅ Web search results arrive in real-time
✅ Yjs sync latency <50ms
✅ Concurrent users don't impact performance
✅ PDF extraction <30s for 50MB file

---

## 11. ASSUMPTIONS & CONSTRAINTS

**Assumptions:**
- search-hub-mcp is available and functional
- Server2 PDF extraction is reliable enough
- Cosmos DB multi-region replication works as expected
- Users have sufficient credits by default (trials have 100+ credits)
- Network latency acceptable (WebSocket ~50ms)

**Constraints:**
- Business Plan only (no GTM/SWOT/Pitch in this phase)
- Max 13 sections per plan (fixed, per spec)
- Max 15 companies per generation (search limits)
- Max 50MB PDF files
- 2-hour web search cache TTL fixed

---

## 12. FUTURE ENHANCEMENTS

Out of scope, but considered:
- Batch generation (multiple plans at once)
- API key management (users bring their own LLM keys)
- Custom section templates
- Industry reports as source data
- Live market data feeds (Alpha Vantage real-time)
- PDF generation with embed-able canvases (advanced PDF export)
- Workflow automation (trigger on quarterly intervals)

---

**APPROVAL STATUS: READY FOR IMPLEMENTATION PLANNING**

**Next Step:** Writing-plans skill to create detailed 4-week implementation roadmap

**Estimated Effort:** 4 weeks (1 backend engineer, 2 frontend engineers)
**Critical Path:** Input system → Generation pipeline → Canvas views
**Risk Level:** Low (modular design, comprehensive error handling)

---

*Spec written: 2026-04-03*
*Design approved by: CTO*
*Status: READY FOR IMPLEMENTATION*
