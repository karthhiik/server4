# Multi-MCP Business Intelligence Plan

Date: 2026-03-28
Project: Barise  workspace
Backend target: `Server1_FastApi`
Goal: redesign Business Plan, GTM, SWOT, and Pitch Analysis into a real-time, multi-MCP, multi-agent research system while preserving the current FastAPI structure and current user input flow.

## 1. Direction

This should be built as a **FastAPI-first shared intelligence layer**, not as four isolated generators.

The best architecture for your product is:

1. keep the current FastAPI routes and frontend pages
2. build one shared research backbone
3. use that research backbone to generate:
   - Business Plan
   - GTM Strategy
   - SWOT Analysis
   - Pitch Deck Analysis
4. stream evidence and progress into the UI as early as possible

The key product idea is a **Shared Evidence Graph + Research Bundle**:

- one research run
- many artifact outputs
- one source of truth
- one citation system
- one validation system

This gives you:

- faster total generation
- fewer duplicate searches
- much better consistency across Business Plan / GTM / SWOT / Pitch
- better explainability for users and investors
- easier partial regeneration when users edit only one section

### Reliability principle

It is not technically honest to promise literal `zero failure` or `zero false data` in a real-world AI + search system.

What this plan does promise is:

- zero silent fabrication as a design goal
- zero silent failure as a design goal
- fail-safe behavior when evidence is weak or systems fail
- explicit confidence labels instead of fake certainty
- user-visible recovery states instead of hidden broken flows

## 2. Correct Scope After Your Clarification

You are right:

- we should target **FastAPI**, not Flask
- the correct backend is `Server1_FastApi`
- model planning should use your existing Azure and Cloudflare model inventory

That changes the implementation plan in a good way, because the repo already has strong FastAPI patterns for:

- async routes
- Celery task dispatch
- Redis progress/state
- Azure OpenAI integrations
- pitch/business/GTM/SWOT service separation

## 3. Current FastAPI Baseline In This Repo

### Existing frontend flows

The frontend already has dedicated routes for the business intelligence features:

- `lliveupdatedstreaming/src/App.tsx`
  - `/business-plan-result`
  - `/swot-analysis`
  - `/analysis_businessplan`
  - `/gtm-strategy`
  - `/formforbusiness`
  - `/pitch_analysis`

The frontend also already ships with the right visualization stack:

- `reactflow`
- `@xyflow/react`
- `chart.js`
- `react-chartjs-2`
- `framer-motion`
- `lottie-react`

So the visual redesign can build on the current app instead of replacing it.

### Existing FastAPI routes

`Server1_FastApi` already exposes the core endpoints we need:

- `Server1_FastApi/app/api/routes/business_routes.py`
  - `POST /api/generate-business-plan`
- `Server1_FastApi/app/api/routes/gtm_routes.py`
  - `POST /generate_gtm_plan`
- `Server1_FastApi/app/api/routes/swot_routes.py`
  - `POST /api/swot`
- `Server1_FastApi/app/api/routes/pitch_analysis_routes.py`
  - `POST /api/analyze-pitch`

### Existing research and validation patterns

You also already have useful real-time research infrastructure patterns in `FASTAPI_COMMUNITY` that should be reused conceptually inside the FastAPI server:

- `FASTAPI_COMMUNITY/app/services/realtime_syn/mcp_gateway.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/source_quality.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/validator.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/news_expanded.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/market_expanded.py`

### Existing model configuration signals

`Server1_FastApi/app/core/config.py` already confirms Azure-centric model routing:

- `AZURE_MODELNAME_PITCH`
- `AZURE_MODELNAME_GTM`
- Azure OpenAI endpoint/deployment fields

The repo also already uses:

- Azure OpenAI clients
- Mistral through Azure-style endpoint patterns in other services
- Cloudflare services elsewhere in the repo

Conclusion:

We should not create a separate architecture outside `Server1_FastApi`.
We should add a shared intelligence and MCP adapter layer **inside the FastAPI project path**.

## 4. Model Strategy Using Your Available Models

Based on your note, the model plan should be explicit.

Assumption for this plan:

- `gpt-4o`, fine-tuned `gpt-4o`, `kimithinking`, `deepseek`, `mistral`, and the listed Cloudflare models are treated as available runtime options from your deployment environment, even if some of them are not yet fully surfaced in the current `Server1_FastApi/app/core/config.py` fields.

### Subscription / stronger models

- `gpt-4o (fine-tuned)`
- `gpt-4o`
- `kimithinking`
- `deepseek`
- `mistral`

### Free / utility Cloudflare models

- `qwen2.5-coder`
- `glm4.7`
- `gemma`

### Recommended model routing

#### A. Final business writing and artifact assembly

Use:

- `gpt-4o (fine-tuned)` for Business Plan final assembly if the fine-tune is trained for your product tone/format
- `gpt-4o` as the default production writer for Business Plan, GTM, SWOT, and Pitch summaries

Why:

- strongest formatting reliability
- better long-form synthesis
- stronger JSON compliance for section payloads
- better investor-facing prose quality

#### B. Deep reasoning and contradiction review

Use:

- `kimithinking`
- `deepseek`
- `mistral`

Best roles:

- contradiction checker
- evidence reviewer
- reasoning-heavy SWOT pairing
- pitch-deck logic gap review
- competitor differentiation review

Recommendation:

- use one of these as a second-pass reviewer, not the primary writer
- `mistral` is especially good as a cheap validator/reviewer pattern because your repo already uses it in review-style flows

#### C. Cheap utility tasks

Use Cloudflare models for:

- prompt-to-structure extraction
- query expansion
- title normalization
- source clustering
- low-risk code/text transforms
- diagram JSON scaffolding

Recommended utility routing:

- `qwen2.5-coder` for JSON schema generation, parser logic, structured extraction, code-like tasks
- `glm4.7` for cheap intermediate summarization or classification
- `gemma` for lightweight labeling and tag generation

### Practical routing policy

Use a three-tier policy:

1. `utility tier`
   - Cloudflare models
   - fast, cheap, high-volume tasks
2. `research/review tier`
   - `mistral`, `deepseek`, `kimithinking`
   - evidence reasoning, contradiction checks, reviewer passes
3. `final output tier`
   - `gpt-4o` or `gpt-4o fine-tuned`
   - investor-facing output and final section assembly

This will be faster and cheaper than using one premium model for everything.

## 5. What Must Stay Intact

We should preserve:

- current FastAPI routes
- current user input forms
- current prompt-like upload/input flows
- current async progress behavior
- current result page structure

We should add:

- prompt-to-schema parser
- shared research bundle
- multi-MCP adapters
- evidence validation
- richer React Flow and diagram outputs

## 5.1 Additional repository learnings now folded into the plan

### `coreyhaines31/marketingskills`

Important contribution to this plan:

- strong skill-based marketing workflow breakdown
- product-marketing context as a shared foundation
- customer research, launch strategy, pricing strategy, competitor alternatives, sales enablement, CRO, analytics, and SEO workflows

What we should adopt conceptually:

- a shared `product-marketing-context` object for every artifact
- reusable marketing skill packets for GTM generation
- structured sub-workflows for:
  - launch strategy
  - pricing strategy
  - customer research
  - sales enablement
  - competitor alternative positioning
  - CRO and funnel improvement

### `unicodeveloper/competitor-analysis`

Important contribution to this plan:

- live deep-research progress UX
- side-by-side research/results UI
- source-backed competitor reports
- PDF export

What we should adopt conceptually:

- live progress during competitor research
- right-panel progressive result rendering
- visible source citations while research is still running
- competitor analysis as a first-class reusable artifact across Business Plan, GTM, SWOT, and Pitch

### `every-app/open-seo`

Important contribution to this plan:

- SEO workflow separation
- keyword research
- domain insights
- backlinks
- site audits
- focused workflows instead of a bloated suite

What we should adopt conceptually:

- a dedicated growth and SEO intelligence layer for GTM and Business Plan
- keyword and domain intelligence as evidence for organic acquisition strategy
- site and backlink audits as optional enrichment for existing businesses

### Draw.io ecosystem learnings

#### `jgraph/drawio-desktop`

Important contribution:

- local-first secure diagram editing
- isolated desktop editing model
- no forced remote data transmission

Use in plan:

- optional offline editing/export environment for premium reports and diagrams

#### `lgazo/drawio-mcp-server`

Important contribution:

- programmatic diagram creation and modification via MCP
- built-in editor mode
- nested structures, layers, and edge control

Use in plan:

- core diagram generation/editing MCP

#### `DayuanJiang/next-ai-draw-io`

Important contribution:

- natural-language diagram editing
- version history
- chat-based diagram refinement
- PDF/text-to-diagram flows

Use in plan:

- editable report visuals
- prompt-driven diagram refinement
- diagram history and restore support

#### `koral--/android-gif-drawable`

Important contribution:

- animation/GIF rendering ideas for mobile contexts

Use in plan:

- reference only for motion/presentation ideas
- not a direct dependency for the React/FastAPI web implementation

## 6. Research Findings For The Four Artifacts

### Business Plan

Primary practical sources:

- SBA:
  - `https://www.sba.gov/business-guide/plan-your-business/write-your-business-plan`
  - `https://www.sba.gov/business-guide/plan-your-business/market-research-competitive-analysis`
  - `https://www.sba.gov/business-guide/plan-your-business/calculate-your-startup-costs`

Useful components:

- executive summary
- problem and solution
- market analysis
- target customer
- competitor analysis
- business model
- GTM summary
- operations plan
- financial assumptions
- funding use
- risk analysis

Not useful:

- generic filler
- unsupported TAM numbers
- overly precise hallucinated forecasts
- repeated mission/vision text

### GTM

Practical sources:

- `https://www.productplan.com/glossary/go-to-market-strategy/`
- `https://asana.com/templates/gtm-strategy`
- `https://asana.com/resources/go-to-market-gtm-strategy`
- `https://github.com/coreyhaines31/marketingskills`
- `https://github.com/every-app/open-seo`

Useful GTM components:

- ICP and segmentation
- positioning
- messaging
- pricing
- channels
- launch phases
- KPI tree
- budget allocation
- experiment plan
- SEO growth loops
- content and competitor-alternative pages
- customer-research-backed messaging
- sales enablement assets

Not useful:

- random channel lists
- no prioritization
- no budget logic
- no execution sequencing

### SWOT

Useful source:

- `https://www.evms.edu/media/evms_public/departments/gme/2018_acgme_conference_-_hn/ACGME_Self_Study_SWOT_Guide.pdf`

Useful SWOT logic:

- strengths and weaknesses are internal
- opportunities and threats are external
- action-pairing is more useful than the matrix alone

### Pitch Deck Analysis

Useful source:

- `https://pages.visible.vc/fundraising-road-map`

Useful pitch analysis dimensions:

- market opportunity
- product clarity
- traction
- team
- business model
- fundraising ask
- deck flow
- slide completeness
- investor objections
- competitor-positioning clarity
- proof quality of market and traction claims

### Competitor intelligence as a shared layer

Additional practical source:

- `https://github.com/unicodeveloper/competitor-analysis`

Important conclusion:

Competitor analysis should not be an optional side task.
It should be a shared reusable research layer used by:

- Business Plan competitive landscape
- GTM positioning and alternative pages
- SWOT threats and opportunities
- Pitch deck market positioning and investor objection review

## 7. Product Architecture Recommendation

Build a **Shared Evidence Graph** with these node types:

- company
- founder/team
- target segment
- geography
- market
- competitor
- claim
- metric
- source
- risk
- trend

This becomes the source of truth for all four artifacts.

### Why this is the right design

- Business Plan, GTM, SWOT, and Pitch should not search separately
- all four outputs should cite the same market and competitor facts
- if the user changes one field, only affected graph nodes should be recomputed
- visuals can be generated directly from graph data
- contradiction checks become much easier

## 8. Recommended MCP Set

Do not create one MCP per artifact.
Create MCPs by capability.

### MCP 1: `search-hub-mcp`

Purpose:

- live web search
- news search
- geo-aware search
- query expansion

Use ideas from:

- `slinusc/web-search-mcp-server`
- `MattimaxForce/duckduckgo-mcp`
- `Cometdev312/Dappier-MCP-Server-Real-Time-Web-Market-Data-for-AI-Agents`

### MCP 2: `scrape-extract-mcp`

Purpose:

- page fetch
- article extraction
- pricing/feature table extraction
- hard-page rendering

Use ideas from:

- `Decodo/decodo-openclaw-skill`
- `lightpanda-io/browser`

### MCP 3: `market-intel-mcp`

Purpose:

- TAM/SAM/SOM
- competitor and funding context
- public market and macro signal collection

Use ideas from:

- `gvaibhav/TAM-MCP-Server`
- `OctagonAI/octagon-mcp-server`
- `OctagonAI/octagon-vc-agents`
- `mz462/stock-research-mcp`
- `smitkunpara/tradingview-mcp`
- `profitelligence/profitelligence-mcp-server`
- `Mohit-Dhawan98/adalyst-mcp`

### MCP 4: `growth-seo-mcp`

Purpose:

- keyword research
- domain insights
- backlink/context analysis
- SEO opportunity discovery
- competitor-alternative page intelligence

Use ideas from:

- `every-app/open-seo`
- `coreyhaines31/marketingskills`
- `ezbiz-services/mcp-seo-marketing`

### MCP 5: `research-synthesis-mcp`

Purpose:

- research bundle assembly
- citation merging
- artifact-specific briefing packets
- contradiction review

Use ideas from:

- `langchain-ai/deepagents`
- `u14app/deep-research`
- `NousResearch/hermes-agent`
- `bytedance/deer-flow`
- `karpathy/autoresearch`
- `agentscope-ai/agentscope`
- `timwuhaotian/the-pair`

### MCP 6: `memory-context-mcp`

Purpose:

- store user/company context
- store prior approved assumptions
- reuse past research bundles

Use ideas from:

- `supermemoryai/supermemory`
- `andrewyng/context-hub`
- `bitbonsai/mcpvault`

### MCP 7: `visualization-mcp`

Purpose:

- React Flow graph specs
- draw.io exports
- editable draw.io documents
- SWOT matrix specs
- GTM funnel specs
- pitch story maps
- animation-aware presentation specs

Use ideas from:

- `jgraph/drawio-desktop`
- `lgazo/drawio-mcp-server`
- `DayuanJiang/next-ai-draw-io`
- `Michaelliv/pi-generative-ui`
- `pbakaus/impeccable`
- `nandanNM/crazxy-ui`
- `cyxzdev/Uncodixfy`

### MCP 8: `trust-guard-mcp`

Purpose:

- source scoring
- freshness checking
- contradiction detection
- claim verification

Use ideas from:

- `FASTAPI_COMMUNITY/app/services/realtime_syn/source_quality.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/validator.py`
- `millionco/expect`

## 9. Multi-Agent Workflow

### Shared agents

- Input Normalizer Agent
- Query Planner Agent
- Search Agent
- Scrape Agent
- Market Agent
- Growth/SEO Agent
- Source Validator Agent
- Research Bundle Agent
- Failure Recovery Agent

### Business Plan agents

- Market Sizing Agent
- Competitor Agent
- Financial Assumptions Agent
- Operations Agent
- Risk Agent
- Writer Agent
- Citation QA Agent

### GTM agents

- ICP Agent
- Positioning Agent
- Channel Agent
- Pricing Agent
- SEO and Content Agent
- Competitor Alternatives Agent
- Sales Enablement Agent
- Launch Timeline Agent
- KPI Agent
- Writer Agent

### SWOT agents

- Internal Factors Agent
- External Opportunities Agent
- External Threats Agent
- Action Pairing Agent
- Writer Agent

### Pitch agents

- Slide Parser Agent
- Narrative Agent
- Investor Lens Agent
- Competitor Proof Agent
- Design and Readability Agent
- Ask/Readiness Agent
- Reviewer Agent

## 10. Generation Flow Per Artifact

### Shared input modes

#### Mode A: current structured forms

Keep the existing forms exactly as they are.

#### Mode B: prompt-based input

Add a prompt box above the current forms:

- user writes a freeform idea
- utility model extracts fields into current schema
- user edits the parsed fields
- generation continues using the same existing route

### Real-world input handling requirements

The system must handle messy real-world user input, not only ideal clean forms.

Support these input patterns:

- complete structured input
- partial structured input
- freeform prompt only
- uploaded pitch deck only
- prompt plus uploaded files
- competitor URL only
- company website plus short notes
- user-edited fields after generation

Input normalization rules:

- infer missing fields only as suggestions, never as final facts
- detect ambiguous entities and ask for confirmation only when risk is high
- support geography, currency, and market defaults
- support existing businesses and idea-stage startups separately
- support B2B, B2C, marketplace, SaaS, fintech, AI, services, and hybrid models
- detect whether the user is asking for launch, growth, repositioning, or fundraising

### Business Plan flow

1. normalize input
2. search live sources
3. build evidence graph
4. build business-plan brief
5. write sections
6. validate claims
7. render charts and maps
8. allow inline editing of sections, assumption cards, and evidence links

### GTM flow

1. normalize GTM inputs
2. search ICP, channels, competitors, and geography
3. build GTM brief
4. generate launch plan, budget, KPIs, SEO plan, and competitor-alternative strategy
5. render funnel and React Flow launch map
6. allow inline editing of nodes, messaging cards, channel strategy, and KPI assumptions

### SWOT flow

1. normalize internal inputs
2. search external threats/opportunities
3. separate internal vs external items
4. score confidence
5. generate matrix plus action pairs
6. allow inline editing of quadrant items, scores, and mitigation links

### Pitch flow

1. extract deck text
2. map slide roles
3. build or reuse research bundle
4. compare deck claims to external evidence
5. score completeness, logic, traction, and ask
6. render slide score map and rewrite queue
7. allow slide-level edits, rewritten content suggestions, and section re-analysis

## 11. API Key Strategy

Use the APIs you listed in tiers.

### Primary production set

#### GNews

Use for:

- fast headline retrieval
- Google News-style current market/news coverage

Source:

- `https://docs.gnews.io/`

#### TheNewsAPI

Use for:

- fast real-time enrichment
- predictable daily free usage

Source:

- `https://www.thenewsapi.com/pricing`

Observed from official pricing:

- free tier
- 100 requests daily
- 3 articles per request
- real-time and historical support

#### NewsData.io

Use for:

- secondary news coverage
- backup enrichment
- lower-priority aggregation

Source:

- `https://newsdata.io/blog/pricing-plan-in-newsdata-io/`

Observed from official page:

- free plan exists
- 200 credits per day
- 10 articles per credit
- 12-hour delay on free plan

#### Alpha Vantage

Use for:

- market context
- economic indicators
- news/sentiment
- public-market comparables

Source:

- `https://www.alphavantage.co/documentation/`

#### Finnhub

Use for:

- company news
- quotes
- company fundamentals
- comparable-company context

Source:

- `https://finnhub.io/docs/api`

#### Guardian Open Platform

Use for:

- trusted editorial cross-checks
- policy and market verification

Source:

- `https://open-platform.theguardian.com/documentation/`

### Optional secondary set

- Mediastack
- Currents API
- New York Times API
- You.com API
- DataForSEO-style SEO APIs if you want OpenSEO-like depth for keyword, backlink, and site-audit workflows

These are good overflow or premium-enrichment sources, but I would not make all of them core on day one.

### Not recommended as a primary free production source

#### NewsAPI free developer plan

Source:

- `https://newsapi.org/pricing`

Observed from official pricing:

- 100 requests/day
- 24 hour delay
- development/testing use
- not good as the main production data path on the free tier

## 12. Truth and Validation Plan

This is the most important quality requirement.

### Honest guarantee

No live AI research system can guarantee literal zero error forever.

This plan is designed for:

- zero silent fabrication
- zero silent failure
- fail-closed behavior when confidence is low
- explicit uncertainty when evidence is incomplete

### Rules

1. no hard metric without evidence
2. accept a claim only if:
   - one authoritative primary source supports it, or
   - two credible independent sources support it
3. label model-estimated values as `Inference` or `Scenario`
4. always show source and date for important claims
5. surface contradictions instead of hiding them
6. degrade gracefully when evidence is weak

### Validation pipeline

1. source scoring
2. freshness scoring
3. duplicate clustering
4. claim extraction
5. cross-source verification
6. contradiction review
7. writer pass
8. reviewer pass
9. publish gate

### Reuse from existing repo patterns

- trusted domain logic from `FASTAPI_COMMUNITY/app/services/realtime_syn/source_quality.py`
- heuristic/reviewer logic from `FASTAPI_COMMUNITY/app/services/realtime_syn/validator.py`
- MCP gateway pattern from `FASTAPI_COMMUNITY/app/services/realtime_syn/mcp_gateway.py`

### Output labels

- Verified
- Supported
- Inference
- Weak signal
- Needs review

### Numeric claim policy

Every important number should have:

- source
- publication date
- retrieval timestamp
- unit/currency
- whether it is a fact, estimate, or scenario

### Failure handling and recovery plan

#### Failure classes

- provider timeout
- provider rate limit
- MCP unavailable
- low-quality scrape
- conflicting sources
- low-confidence model output
- malformed JSON/tool output
- websocket/progress interruption
- partial artifact generation
- diagram generation failure

#### System behavior

For every failure, the system should do all of the following:

1. log the failure with traceable request and bundle IDs
2. retry only when safe and useful
3. fallback to the next provider/model if confidence remains acceptable
4. preserve completed work instead of discarding everything
5. show a clear user-facing state
6. mark any affected section as partial, weak-signal, or needs-review

#### Hard rules

- never replace missing evidence with invented evidence
- never show a synthetic number as if it were verified
- never return success when critical validation failed
- never lose editable user changes during regeneration

#### Fallback chain examples

- search provider fails:
  - fallback to second search provider
  - then cached bundle
  - then user-visible partial mode
- premium model fails:
  - fallback to review-tier model
  - then utility extraction for structure
  - then queue for retry
- draw.io generation fails:
  - fallback to React Flow-only graph
  - keep node data editable
  - allow later draw.io export retry
- deck extraction fails on one slide:
  - continue analysis with partial deck
  - mark affected slides as extraction-incomplete

#### Operational controls

- circuit breaker per provider
- request timeout budgets
- per-step checkpoints
- idempotent regeneration keys
- stale-cache fallback for non-critical enrichments
- audit trail for edits and regenerations

## 13. Speed Plan

Support two modes.

### Fast mode

- fewer sources
- fast synthesis
- early partial UI

### Deep mode

- more sources
- stronger verification
- richer visuals
- stronger contradiction review

### Target timing

| Artifact | Fast mode | Deep mode |
|---|---:|---:|
| Shared research bundle | 6s-15s | 15s-35s |
| Business Plan | 25s-55s | 55s-120s |
| GTM | 18s-40s | 40s-90s |
| SWOT | 10s-22s | 22s-45s |
| Pitch Analysis | 60s-180s | 120s-300s |

### How to make it fast

- run search/news/market calls in parallel
- reuse a shared bundle across all four outputs
- cache article extraction
- cache market summaries
- render sources before final prose finishes
- regenerate only affected sections after edits

## 14. UI/UX Plan

Keep the existing Barise app shell and current route layout.
Upgrade the result experience into a richer strategy lab.

### Premium design direction

The output should feel premium, founder-grade, and investor-ready rather than like a generic dashboard.

Recommended visual direction:

- warm ivory and graphite surfaces
- deep teal and brass accents
- editorial typography for long-form report reading
- controlled glass/depth effects
- subtle animated connectors and staged reveals
- motion that clarifies structure, not motion for decoration only

### Common result tabs

- Summary
- Evidence
- Visual Map
- Metrics
- Sources
- Edit Mode
- Version History

### Visual outputs

#### Business Plan

- TAM/SAM/SOM map
- competitor matrix
- milestone roadmap
- revenue scenario cards

#### GTM

- React Flow launch chain
- funnel
- experiment board
- phase timeline

#### SWOT

- interactive 2x2 matrix
- action-pair graph
- threat mitigation chain

#### Pitch

- slide score rail
- story arc map
- investor objection board
- missing-proof checklist

### Editable report requirement

All four outputs must be editable after generation.

Editable units:

- report section titles
- section body text
- assumptions
- metrics
- confidence labels
- node labels
- node connections
- SWOT quadrant entries
- GTM channel cards
- pitch slide feedback blocks

Editing behaviors:

- edit inline in rich cards
- save draft without full regeneration
- regenerate one block only
- compare before/after versions
- keep version history with timestamps
- sync edited structured data back to the shared bundle

### React Flow node system

Every artifact should expose an interactive node graph:

- Business Plan:
  - market, customer, competitor, revenue, risk, milestone nodes
- GTM:
  - ICP, channel, budget, messaging, KPI, timeline nodes
- SWOT:
  - quadrant nodes plus action-pair edges
- Pitch:
  - slide nodes, issue nodes, evidence nodes, rewrite nodes

Each node should support:

- details drawer
- inline edit
- attach evidence
- regenerate node content
- export linked diagram

### Draw.io and React Flow split

Use `drawio-mcp-server` for:

- exportable stakeholder diagrams
- shareable editable artifacts
- diagram mutation from MCP tools
- `.drawio` export generation

Use `drawio-desktop` for:

- offline premium editing
- local secure diagram refinement
- final stakeholder-ready diagram polishing

Use ideas from `next-ai-draw-io` for:

- natural-language diagram refinement
- diagram history and restore
- prompt-based edits to existing diagrams

Use React Flow for:

- in-app interaction
- evidence-linked nodes
- live graph navigation

Use `android-gif-drawable` only as reference inspiration for animated preview/export ideas if you later add native mobile surfaces.

## 15. Repo Decision Matrix

| Repo | Role | Decision |
|---|---|---|
| `Decodo/decodo-openclaw-skill` | structured scraping | Adapt |
| `coreyhaines31/marketingskills` | GTM, CRO, copy, SEO, launch workflow patterns | Strong adapt |
| `unicodeveloper/competitor-analysis` | live competitor deep-research UX and citation-first reports | Strong adapt |
| `every-app/open-seo` | keyword/domain/backlink/site-audit workflows | Strong adapt |
| `jgraph/drawio-desktop` | local secure premium diagram editing | Adopt as companion editor |
| `lgazo/drawio-mcp-server` | diagrams | Adopt |
| `DayuanJiang/next-ai-draw-io` | natural-language diagram editing and diagram history | Strong adapt |
| `koral--/android-gif-drawable` | animated preview inspiration | Reference only |
| `langchain-ai/deepagents` | planner/subagents | Adapt patterns |
| `NousResearch/hermes-agent` | long-horizon agent ideas | Reference |
| `u14app/deep-research` | deep research server | Adapt patterns |
| `blazickjp/arxiv-mcp-server` | academic sources | Optional |
| `king-of-the-grackles/reddit-research-mcp` | community signal | Optional, never primary |
| `gvaibhav/TAM-MCP-Server` | market sizing | Strong adapt |
| `OctagonAI/octagon-vc-agents` | VC review personas | Adapt |
| `OctagonAI/octagon-mcp-server` | filings/financial intelligence | Strong adapt |
| `mz462/stock-research-mcp` | stock research | Optional |
| `smitkunpara/tradingview-mcp` | market charts/data | Optional |
| `Mohit-Dhawan98/adalyst-mcp` | competitor analysis | Reference |
| `ezbiz-services/mcp-seo-marketing` | SEO/GTM intelligence | Adapt |
| `profitelligence/profitelligence-mcp-server` | market intel | Optional |
| `paperclipai/paperclip` | broad orchestration | Reference only |
| `supermemoryai/supermemory` | memory layer | Strong adapt |
| `slinusc/web-search-mcp-server` | search | Strong adopt/adapt |
| `Cometdev312/Dappier-MCP-Server-Real-Time-Web-Market-Data-for-AI-Agents` | real-time premium data | Optional |
| `positive666/Deep_search_lightning` | balanced search | Reference |
| `MattimaxForce/duckduckgo-mcp` | search | Strong adopt/adapt |
| `dotnetpower/infomesh` | decentralized search | Reference |
| `cyxzdev/Uncodixfy` | anti-generic UI ideas | Reference |
| `marianfoo/sap-ai-mcp-servers` | catalog | Reference |
| `patchy631/ai-engineering-hub` | tutorials | Reference |
| `andrewyng/context-hub` | context patterns | Adapt |
| `alirezarezvani/claude-skills` | skills catalog | Reference |
| `bitbonsai/mcpvault` | safe retrieval patterns | Reference |
| `Michaelliv/pi-generative-ui` | advanced generative UI | Reference |
| `nandanNM/crazxy-ui` | UI ideas | Reference |
| `pbakaus/impeccable` | design language | Strong reference |
| `karpathy/autoresearch` | autoresearch loops | Reference |
| `microsoft/aspire` | infra/observability | Reference |
| `lightpanda-io/browser` | headless browser | Strong optional tool |
| `bytedance/deer-flow` | super-agent harness | Strong reference |
| `alvinunreal/awesome-opensource-ai` | discovery list | Reference |
| `timwuhaotian/the-pair` | cross-checking agents | Adapt concept |
| `kesslernity/awesome-copilot-studio-agents` | catalog | Reference |
| `agentscope-ai/agentscope` | trustworthy multi-agent patterns | Strong reference |
| `WecoAI/awesome-autoresearch` | discovery list | Reference |
| `AltimateAI/altimate-code` | data tooling patterns | Reference |
| `mitkox/vllm-turboquant` | self-hosted inference optimization | Skip for MVP |
| `ggml-org/llama.cpp` | local inference | Skip for MVP |
| `millionco/expect` | browser verification | Strong reference |

## 16. Recommended FastAPI File Structure

The cleanest path is to add a new shared intelligence layer and wire it into `Server1_FastApi`.

```text
shared_intelligence/
  models/
    evidence.py
    research_bundle.py
    artifact_specs.py
    editable_report.py
  providers/
    search/
    news/
    market/
    scrape/
    seo/
  validation/
    source_quality.py
    claim_guard.py
    contradiction_checker.py
    failure_policy.py
  memory/
    memory_store.py
  mcp/
    search_hub_client.py
    scrape_extract_client.py
    market_intel_client.py
    growth_seo_client.py
    research_synthesis_client.py
    visualization_client.py
    trust_guard_client.py
  pipelines/
    build_bundle.py
    business_plan_pipeline.py
    gtm_pipeline.py
    swot_pipeline.py
    pitch_pipeline.py
  editors/
    report_sync.py
    node_edit_service.py
    version_history.py
```

Recommended FastAPI integration:

```text
Server1_FastApi/app/services/intelligence/
  orchestrator.py
  bundle_cache.py
  progress_streamer.py
  model_router.py
  artifact_renderers.py
  editable_report_service.py
  diagram_service.py
  failure_recovery.py
```

Recommended frontend integration:

```text
lliveupdatedstreaming/src/features/intelligence/
  components/
    EvidenceDrawer.tsx
    SourceCard.tsx
    ConfidenceBadge.tsx
    FreshnessBadge.tsx
    StrategyGraph.tsx
    EditableSectionCard.tsx
    DiagramEditorPanel.tsx
    VersionHistoryDrawer.tsx
  hooks/
    useResearchProgress.ts
    useEvidenceBundle.ts
    useEditableArtifact.ts
  types/
    evidence.ts
    bundle.ts
    editableArtifact.ts
```

## 17. Route Strategy

Do not break the current APIs.

Keep:

- `/api/generate-business-plan`
- `/generate_gtm_plan`
- `/api/swot`
- `/api/analyze-pitch`

Add optional request fields:

- `research_mode`
- `prompt_input`
- `target_geo`
- `strict_freshness`
- `citation_level`
- `regenerate_scope`

Optional new FastAPI endpoints:

- `/api/research/bundle`
- `/api/research/bundle/{bundle_id}`
- `/api/research/evidence/{claim_id}`
- `/api/research/regenerate`
- `/api/reports/{artifact_id}/edit`
- `/api/reports/{artifact_id}/node-edit`
- `/api/reports/{artifact_id}/history`
- `/api/reports/{artifact_id}/diagram/export`
- `/api/reports/{artifact_id}/diagram/refine`

## 18. Implementation Phases

### Phase 1: shared intelligence foundation

- create `shared_intelligence`
- port and improve source scoring logic
- add evidence and bundle schemas
- add model router for Azure + Cloudflare
- add failure policy and fail-safe publish gate

### Phase 2: search/scrape/market MCP adapters

- wire search-hub MCP
- wire scrape-extract MCP
- wire market-intel MCP
- wire growth-seo MCP
- add caching and citation packaging

### Phase 3: Business Plan and GTM upgrade

- plug current FastAPI business route into shared bundle
- plug current GTM route into shared bundle
- add React Flow and evidence tabs
- add editable sections and editable node graphs

### Phase 4: SWOT and Pitch upgrade

- plug SWOT route into shared bundle
- plug pitch route into shared bundle
- add investor-readiness and slide-map UI
- add diagram export/refinement workflow

### Phase 5: memory and partial regeneration

- store prior bundles
- allow section-only regeneration
- allow user/company memory
- add version history and edit audit trail

### Phase 6: hardening

- profiling
- cache tuning
- contract tests
- browser E2E
- UI polish
- failure injection testing
- provider outage drills

## 19. Final Recommendation

Build this as a **FastAPI-native shared research bundle system** using:

- Azure `gpt-4o` / fine-tuned `gpt-4o` for final artifact generation
- `mistral`, `deepseek`, and `kimithinking` for review and contradiction reasoning
- Cloudflare free models for utility extraction and cheap intermediate steps
- multiple MCPs for search, scrape, market intelligence, growth/SEO, visualization, memory, and trust-guard
- editable React Flow and draw.io-backed report surfaces
- explicit fail-safe recovery and no-silent-fabrication rules

This is the most practical way to get:

- real-time present-day research
- faster generation
- lower cost
- fewer hallucinations
- better UI/UX
- better cross-artifact consistency

## 20. Source List

### Local repo references

- `lliveupdatedstreaming/src/App.tsx`
- `lliveupdatedstreaming/package.json`
- `lliveupdatedstreaming/src/components/BusinessPlanfrom/from.tsx`
- `lliveupdatedstreaming/src/pages/GTMStrategy.tsx`
- `lliveupdatedstreaming/src/pages/SWOTAnalysis.tsx`
- `lliveupdatedstreaming/src/components/BusinessPlanfrom/plan_analysis.tsx`
- `lliveupdatedstreaming/src/components/business/Flowchart.tsx`
- `Server1_FastApi/app/api/routes/business_routes.py`
- `Server1_FastApi/app/api/routes/gtm_routes.py`
- `Server1_FastApi/app/api/routes/swot_routes.py`
- `Server1_FastApi/app/api/routes/pitch_analysis_routes.py`
- `Server1_FastApi/app/core/config.py`
- `Server1_FastApi/app/services/business_service.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/mcp_gateway.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/source_quality.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/validator.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/news_expanded.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/market_expanded.py`

### Strategy references

- `https://www.sba.gov/business-guide/plan-your-business/write-your-business-plan`
- `https://www.sba.gov/business-guide/plan-your-business/market-research-competitive-analysis`
- `https://www.sba.gov/business-guide/plan-your-business/calculate-your-startup-costs`
- `https://www.productplan.com/glossary/go-to-market-strategy/`
- `https://asana.com/templates/gtm-strategy`
- `https://asana.com/resources/go-to-market-gtm-strategy`
- `https://www.evms.edu/media/evms_public/departments/gme/2018_acgme_conference_-_hn/ACGME_Self_Study_SWOT_Guide.pdf`
- `https://pages.visible.vc/fundraising-road-map`

### GitHub references newly emphasized in this rewrite

- `https://github.com/coreyhaines31/marketingskills`
- `https://github.com/unicodeveloper/competitor-analysis`
- `https://github.com/every-app/open-seo`
- `https://github.com/jgraph/drawio-desktop`
- `https://github.com/lgazo/drawio-mcp-server`
- `https://github.com/DayuanJiang/next-ai-draw-io`
- `https://github.com/koral--/android-gif-drawable`

### API references

- `https://docs.gnews.io/`
- `https://www.thenewsapi.com/pricing`
- `https://newsdata.io/blog/pricing-plan-in-newsdata-io/`
- `https://www.alphavantage.co/documentation/`
- `https://finnhub.io/docs/api`
- `https://open-platform.theguardian.com/documentation/`
- `https://newsapi.org/pricing`
- `https://docs.you.com/welcome`

### GitHub references

All repositories from your original reference list were reviewed and mapped in Section 15 as `Adopt`, `Adapt`, `Optional`, `Reference`, or `Skip for MVP`.
