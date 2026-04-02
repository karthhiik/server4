# Multi-MCP Strategic Intelligence Plan

Date: 2026-03-28
Project: Barise workspace
Backend target: `Server1_FastApi`
Frontend target: `lliveupdatedstreaming`
Primary goal: redesign Business Plan, GTM, SWOT, and Pitch Analysis into a living, evidence-backed, multi-MCP strategic intelligence system without breaking the current FastAPI product shape.

## 1. Executive Direction

This should not be built as four separate generators.
It should be built as one shared intelligence backbone that produces four artifact families:

1. Business Plan
2. GTM Strategy
3. SWOT Analysis
4. Pitch Analysis

The right product is a **Strategic Operating System** built on:

- one living evidence graph
- one shared research bundle
- one validation and citation policy
- one editable artifact model
- one monitoring and refresh layer

### Non-negotiable product promise

Literal zero error is not technically honest in a live AI + search system.
The engineering target should be:

- zero silent fabrication
- zero silent failure
- zero unsupported claims shown as facts
- fail-closed publishing when confidence is weak
- explicit recovery states when providers fail

## 2. Corrections Required By Your Feedback

Your feedback is correct. The upgraded plan must make these changes:

1. Use **TOON (Token-Oriented Object Notation)** as the canonical intelligence format instead of brace-heavy structured payloads.
2. Treat the Evidence Graph as a **living bundle**, not a one-time build.
3. Add **GraphRAG** so writers retrieve only the relevant subgraph for each section.
4. Add an **internal-data-mcp** so external market intel can be compared with internal company metrics.
5. Replace agent sprawl with a **planner-managed DAG** plus a small set of high-value review agents.
6. Move long-running deep research to **async task execution** with `202 Accepted`, `task_id`, and live progress streams.
7. Add **diff/patch regeneration** so user edits mark only dependent nodes stale.
8. Add **failure handling, refusal paths, HITL validation, and monitoring** as first-class architecture.
9. Upgrade the UI into a premium, editable strategy workspace with **React Flow + draw.io**.

## 3. Current Repo Ground Truth

This plan is aligned to the current project, not a generic stack.

### Backend reality in this repo

`Server1_FastApi/app/main.py` currently mounts:

- `business_routes_refactored.py`
- `gtm_routes_refactored.py`
- `pitch_analysis_routes_refactored.py`
- `swot_routes.py`
- `progress_ws_routes.py`

The existing platform already has:

- MongoDB as a persistent data store
- Redis for hot state and progress
- Celery queues for heavy work
- WebSocket progress routes under `/ws/progress/{progress_type}`
- Redis Pub/Sub progress fan-out
- an advanced Redis cache service already present in `app/core/cache_service.py`

### Existing routes and behavior

Current artifact routes already exist:

- `POST /api/generate-business-plan`
- `POST /generate_gtm_plan`
- `POST /api/swot`
- `POST /api/analyze-pitch`

Current behavior is mixed:

- Business, GTM, and SWOT are mostly request/response style in the active refactored routes.
- Pitch already has stronger task/status behavior and progress handling patterns.
- The repo already has the right primitives to extend that async pattern to all four artifacts.

### Existing real-time foundation

The repo already supports the exact style of deep-mode delivery we need:

- `Server1_FastApi/app/core/progress.py`
  - Redis Pub/Sub
  - WebSocket support
  - SSE support
  - persisted progress state for recovery
- `Server1_FastApi/app/api/routes/progress_ws_routes.py`
  - `/ws/progress/{progress_type}?token=...&task_id=...`

### Existing frontend fit

The frontend already contains the correct user-facing surfaces:

- `lliveupdatedstreaming/src/App.tsx`
  - `/business-plan-result`
  - `/swot-analysis`
  - `/analysis_businessplan`
  - `/gtm-strategy`
  - `/formforbusiness`
  - `/pitch_analysis`

It also already ships with the right visual stack:

- `reactflow`
- `@xyflow/react`
- `chart.js`
- `react-chartjs-2`
- `framer-motion`
- `lottie-react`

There are also existing GTM flow components and React Flow experiments in:

- `lliveupdatedstreaming/src/components/business/Flowchart.tsx`
- `lliveupdatedstreaming/src/components/business/nodereact.tsx`
- `lliveupdatedstreaming/src/pages/GTMStrategy.tsx`

### Important project-fit correction

One cleanup should happen early:

- current WebSocket progress types allow `business`
- business generation code still emits `business_plan`

That naming should be standardized before deep-mode rollout so progress subscriptions stay reliable.

## 4. Research Findings By Artifact

This section answers the research tasks directly.

### 4.1 Business Plan

#### What it is

A Business Plan should become a **decision document**, not a decorative long-form essay.

The most useful live components are:

- executive summary grounded in evidence
- customer and market definition
- problem and solution framing
- market sizing with source confidence
- competitor landscape
- business model and pricing logic
- GTM linkage
- operational plan
- milestone plan
- risk and mitigation plan
- scenario-based financial assumptions

#### Components that are useful in a real system

- market analysis based on current sources
- competitor comparison backed by evidence
- customer segmentation and buying logic
- pricing, revenue model, and unit-economics assumptions
- operating milestones and hiring priorities
- risk register and mitigation paths
- funding scenarios and runway sensitivity

#### Components that are low value or often misleading

- generic mission fluff without strategy value
- fake precision TAM numbers with no evidence
- boilerplate organization charts for idea-stage founders
- five-year exact forecasts presented as facts
- copied market-trend paragraphs with no effect on decisions

#### How it should be generated

The Business Plan should be generated from:

- user input
- current market evidence
- competitor research
- optional internal company metrics
- reusable GTM and risk intelligence from the shared bundle

#### What the UI should show

- long-form report sections
- editable assumptions
- evidence-linked market cards
- scenario cards
- roadmap graph
- risk heatmap
- React Flow strategy map

### 4.2 GTM Strategy

#### What it is

GTM is the operating plan for how the company reaches the right customer, with the right offer, through the right channels, at the right time.

#### Most useful GTM components

- ICP definition
- segment prioritization
- positioning
- category framing
- value proposition
- pricing and packaging
- channel mix
- launch sequence
- sales motion
- SEO and content opportunities
- funnel design
- KPI plan
- experiment backlog
- budget and timeline

#### What should not dominate the output

- generic marketing slogans
- unsupported channel claims
- random social-media recommendations detached from ICP
- static funnel diagrams with no metrics or evidence

#### How it should be generated

The GTM plan should combine:

- user product input
- customer and competitor research
- keyword and domain opportunity analysis
- geography and pricing signals
- optional internal funnel data

#### Real-world GTM requirement

GTM must be live enough to answer:

- what segment to start with
- which channels are highest confidence now
- which competitor alternatives users already compare against
- how pricing should change by market, stage, or motion

#### What the UI should show

- React Flow launch map
- editable channel nodes
- experiment board
- funnel stages
- SEO opportunity lane
- pricing logic cards
- KPI dashboard

### 4.3 SWOT Analysis

#### What SWOT means

SWOT separates:

- Strengths: internal advantages
- Weaknesses: internal limitations
- Opportunities: external favorable conditions
- Threats: external risks

#### What makes SWOT useful in a live system

A useful SWOT is not a four-box template only.
It should also produce:

- confidence-scored items
- TOWS pairings
- action recommendations
- mitigation paths
- evidence links

#### How it should be generated

The system should:

1. derive internal strengths and weaknesses from user input and optional internal metrics
2. derive opportunities and threats from external evidence
3. score each item by confidence and impact
4. create action pairings such as:
   - use Strength X to capture Opportunity Y
   - fix Weakness A before Threat B becomes material

#### What the UI should show

- editable 2x2 matrix
- evidence drawer per item
- impact/confidence sliders
- TOWS action graph
- mitigation chains

### 4.4 Pitch Analysis

#### What it should do

Pitch Analysis should not only score slides.
It should tell the founder:

- what is missing
- what is weak
- what is unsupported
- what investors will challenge
- how to rewrite or reorder the story

#### Useful pitch analysis dimensions

- deck completeness
- market claim validation
- traction proof quality
- narrative clarity
- design and readability
- investor objection risk
- ask readiness
- proof gaps

#### What to avoid

- shallow style-only feedback
- scoring slides without external verification
- praising decks with unsupported market claims

#### How it should be generated

Pitch Analysis should combine:

- uploaded deck extraction
- slide role classification
- external fact checking
- business model consistency checks
- investor persona review

#### What the UI should show

- slide score rail
- objection board
- rewrite queue
- story arc graph
- evidence mismatch alerts
- optional future pitch generation path

## 5. Canonical Data Format: TOON

TOON should become the canonical notation for intelligence exchange inside the new layer.

### Why TOON is the right choice here

- lower token overhead than quote-heavy object notation
- easier for streaming partial updates
- easier for human inspection in logs and debugging
- better for diff/patch workflows
- better for LLM section-by-section editing

### Canonical TOON objects

The system should standardize these core documents:

- `user_brief.toon`
- `research_query.toon`
- `evidence_node.toon`
- `evidence_edge.toon`
- `research_bundle.toon`
- `artifact_section.toon`
- `artifact_report.toon`
- `diagram_spec.toon`
- `bundle_patch.toon`
- `monitor_rule.toon`

### Example TOON shape

```text
artifact_report
  artifact_type: gtm
  bundle_id: bun_01
  company_name: Example AI
  mode: deep
  confidence: supported
  sections[
    section
      id: positioning
      title: Positioning
      support_level: verified
      body_md: ...
    section
      id: channels
      title: Channels
      support_level: inference
      body_md: ...
  ]
  nodes[
    node
      id: gtm_icp
      kind: icp
      state: editable
  ]
```

### TOON migration rule

All new intelligence modules should speak TOON internally.
Compatibility shims may still translate TOON at framework boundaries where current libraries expect existing wire formats, but the business-intelligence domain model should be TOON-first.

## 6. Architecture Recommendation

## 6.1 Core idea

Build a **Living Bundle + Evidence Graph + GraphRAG** system.

Flow:

1. normalize user input
2. build research queries
3. collect search, scrape, market, SEO, and optional internal data
4. score and deduplicate evidence
5. store evidence nodes and edges
6. retrieve only relevant subgraphs per section
7. synthesize artifact sections
8. review, validate, and publish
9. keep the bundle alive for refreshes and alerts

## 6.2 Living bundle states

Each bundle should move through clear states:

- `seeded`
- `collecting`
- `validating`
- `stable`
- `stale`
- `refreshing`
- `blocked`
- `archived`

## 6.3 GraphRAG instead of full-context prompting

This is critical.
Do not pass the whole evidence graph to every writer.

For each section request:

1. identify artifact and section intent
2. retrieve the relevant subgraph only
3. package evidence, contradictions, freshness, and gaps
4. feed only that packet to the writer/reviewer

Examples:

- Business Plan `pricing_strategy` retrieves competitor pricing, WTP signals, segment economics, and geo pricing evidence.
- GTM `channel_mix` retrieves ICP, keyword demand, channel benchmarks, and competitor acquisition clues.
- SWOT `threats` retrieves negative market trends, new competitor launches, policy changes, and product risks.
- Pitch `market_slide` retrieves TAM claims, market growth, and comparable funding context.

## 6.4 Storage strategy that fits this repo

Because the current project already uses MongoDB + Redis + Celery, Phase 1 should stay aligned to that stack.

### Phase 1 storage

Use MongoDB collections for:

- `intelligence_bundles`
- `evidence_nodes`
- `evidence_edges`
- `artifact_reports`
- `artifact_versions`
- `monitor_rules`
- `source_cache_index`
- `founder_memory`

Use Redis for:

- hot semantic cache
- progress state
- pub/sub updates
- distributed locks
- rate-limit counters
- short-lived retrieval packets

Use in-worker graph traversal with:

- `networkx` for early graph walking and dependency propagation

### Phase 3 or later storage upgrade

If graph depth or query complexity outgrows Mongo edge collections, add one of:

- Neo4j
- Apache AGE on Postgres
- vector-assisted retrieval on top of the current data layer

The key point is:

- do not start by replacing the whole project database stack
- grow from the current MongoDB + Redis foundation first

## 6.5 Internal-data overlay

Add `internal-data-mcp` so the system can merge external research with internal metrics.

Supported future connectors:

- Postgres
- Stripe
- HubSpot
- Google Analytics
- CSV upload
- Notion or sheet-based operating data

Security rules:

- read-only credentials
- workspace-scoped secrets
- redaction before model access
- audit logs for every internal query
- allow internal data to override only internal metrics, never external facts

## 7. Multi-MCP Set

This is the recommended MCP layout.

| MCP | Purpose | Primary repo patterns | Decision |
|---|---|---|---|
| `search-hub-mcp` | live search, query expansion, SERP retrieval | `slinusc/web-search-mcp-server`, `MattimaxForce/duckduckgo-mcp`, `Decodo/decodo-openclaw-skill` | Build |
| `scrape-extract-mcp` | page extraction, structured scrape, table capture | `Decodo/decodo-openclaw-skill`, `lightpanda-io/browser` | Build |
| `market-intel-mcp` | market size, public comps, funding context, macro | `gvaibhav/TAM-MCP-Server`, `OctagonAI/octagon-mcp-server`, `profitelligence/profitelligence-mcp-server` | Build |
| `growth-seo-mcp` | keyword, domain, alternatives, SEO opportunity | `coreyhaines31/marketingskills`, `every-app/open-seo`, `ezbiz-services/mcp-seo-marketing` | Build |
| `internal-data-mcp` | internal revenue, churn, funnel, CRM overlays | project-specific | Build |
| `research-orchestrator-mcp` | bundle assembly, planning DAG, GraphRAG packet creation | `langchain-ai/deepagents`, `u14app/deep-research`, `bytedance/deer-flow`, `agentscope-ai/agentscope` | Build |
| `memory-context-mcp` | founder memory, approved assumptions, prior bundles | `supermemoryai/supermemory`, `andrewyng/context-hub`, `bitbonsai/mcpvault` | Build |
| `visualization-mcp` | React Flow specs, draw.io docs, editable maps | `lgazo/drawio-mcp-server`, `jgraph/drawio-desktop`, `DayuanJiang/next-ai-draw-io` | Build |
| `trust-guard-mcp` | claim validation, contradiction detection, refusal gates | `FASTAPI_COMMUNITY` validator patterns, `millionco/expect` | Build |

### Advanced optional MCPs after core release

- `scenario-sim-mcp`
  - sensitivity analysis
  - what-if simulations
- `investor-arena-mcp`
  - skeptic, market expert, finance reviewer personas
  - inspired by `OctagonAI/octagon-vc-agents`
- `compliance-sentinel-mcp`
  - regulated vertical checks for fintech, health, legal-risk sectors

## 8. Repository Intelligence Mapping

This section shows which repositories should shape the build and which should stay reference-only.

### 8.1 Primary direct-adapt sources

- `coreyhaines31/marketingskills`
  - use for shared product-marketing context, pricing strategy, launch strategy, customer research, SEO, CRO, sales enablement
  - do not use as a runtime dependency; use it as a skill-pack design model
- `unicodeveloper/competitor-analysis`
  - use for citation-first competitor research UX, progressive research display, export/report patterns, live task feel
  - do not port its stack directly; adapt the UX and report architecture
- `every-app/open-seo`
  - use for keyword research, domain insight, backlinks, and audit workflow design
  - do not depend on its vendor assumptions until SEO API licensing is confirmed
- `lgazo/drawio-mcp-server`
  - primary runtime choice for draw.io generation and mutation
- `jgraph/drawio-desktop`
  - companion desktop editor for secure offline refinement, not a backend service
- `DayuanJiang/next-ai-draw-io`
  - use for prompt-based diagram editing, history/restore, PDF-to-diagram ideas, interactive diagram chat
- `Decodo/decodo-openclaw-skill`
  - use for Google-search-style structured search and universal scrape patterns
- `slinusc/web-search-mcp-server`
  - use for SearXNG-backed multi-engine search, HTTP/SSE MCP delivery, production-oriented search middleware
- `gvaibhav/TAM-MCP-Server`
  - use for TAM/SAM/SOM prompts, market calculators, economic-source coverage
- `supermemoryai/supermemory`
  - use for contradiction-aware memory, user profiles, connector ideas, and context continuity

### 8.2 Strong secondary sources

- `langchain-ai/deepagents`
  - planner and subtask orchestration patterns
- `u14app/deep-research`
  - deep-research flow and multi-stage retrieval ideas
- `bytedance/deer-flow`
  - memory, subagent, and tool-handoff patterns
- `agentscope-ai/agentscope`
  - trustworthy agent runtime, MCP support, observability mindset
- `NousResearch/hermes-agent`
  - long-horizon skill and agent-environment ideas
- `OctagonAI/octagon-mcp-server`
  - financial and filing-oriented market research patterns
- `OctagonAI/octagon-vc-agents`
  - investor reviewer personas
- `ezbiz-services/mcp-seo-marketing`
  - SEO and marketing MCP ideas
- `profitelligence/profitelligence-mcp-server`
  - financial intelligence enrichment ideas
- `Mohit-Dhawan98/adalyst-mcp`
  - competitor-intelligence reference
- `MattimaxForce/duckduckgo-mcp`
  - fallback search provider adapter
- `lightpanda-io/browser`
  - optional headless browser for sites that need rendering before extraction
- `millionco/expect`
  - browser-based validation and workflow testing

### 8.3 Useful reference-only sources

- `blazickjp/arxiv-mcp-server`
  - optional academic evidence only
- `king-of-the-grackles/reddit-research-mcp`
  - optional community signal only, never primary evidence
- `mz462/stock-research-mcp`
  - optional public-comps enrichment
- `smitkunpara/tradingview-mcp`
  - optional chart enrichment
- `Cometdev312/Dappier-MCP-Server-Real-Time-Web-Market-Data-for-AI-Agents`
  - optional premium real-time enrichment
- `positive666/Deep_search_lightning`
  - reference search orchestration
- `dotnetpower/infomesh`
  - reference only
- `paperclipai/paperclip`
  - orchestration and dashboard reference
- `karpathy/autoresearch`
  - research loop reference
- `timwuhaotian/the-pair`
  - reviewer-pair concept
- `andrewyng/context-hub`
  - context packaging reference
- `bitbonsai/mcpvault`
  - safe memory/retrieval reference
- `Michaelliv/pi-generative-ui`
  - generative UI reference
- `nandanNM/crazxy-ui`
  - visual reference
- `pbakaus/impeccable`
  - premium design reference
- `cyxzdev/Uncodixfy`
  - UI reference
- `microsoft/aspire`
  - observability reference
- `AltimateAI/altimate-code`
  - data-tooling reference

### 8.4 Discovery and catalog references

- `marianfoo/sap-ai-mcp-servers`
- `patchy631/ai-engineering-hub`
- `alirezarezvani/claude-skills`
- `alvinunreal/awesome-opensource-ai`
- `kesslernity/awesome-copilot-studio-agents`
- `WecoAI/awesome-autoresearch`

### 8.5 Skip for MVP

- `mitkox/vllm-turboquant`
- `ggml-org/llama.cpp`

Reason:

- you already have Azure-hosted and Cloudflare-hosted model options
- local inference adds complexity that is not needed for this project phase

### 8.6 Reference-only motion asset

- `koral--/android-gif-drawable`

Use only as inspiration for motion previews or export ideas.
Do not treat it as a runtime dependency for the web product.

## 9. Multi-Agent Strategy

The earlier wide agent list should be collapsed.

### Correct orchestration pattern

Use a small set of durable roles:

1. `Planner`
   - breaks the request into a DAG
   - chooses fast vs deep mode
   - selects which MCPs are needed
2. `Retriever`
   - builds GraphRAG packets for each section
3. `Synthesizer`
   - writes sections from retrieved evidence only
4. `Reviewer`
   - checks contradictions, missing support, and weak claims
5. `Refusal / Reality Check`
   - blocks impossible, unsupported, or dangerous output
6. `Failure Recovery`
   - handles fallback, partial mode, retries, and checkpoint resume
7. `Diagram Composer`
   - builds React Flow and draw.io specs
8. `Memory Updater`
   - stores approved assumptions and corrections

### Artifact logic should be skill packs, not separate chatty agents

Use skill packs for:

- Business Plan
  - market sizing
  - business model
  - finance scenario
  - operations
  - risk
- GTM
  - ICP
  - positioning
  - pricing
  - channels
  - SEO and content
  - experiments
- SWOT
  - internal factor extraction
  - external signal mapping
  - TOWS pair generation
- Pitch
  - slide role parsing
  - investor objection review
  - rewrite queue

This avoids:

- context ping-pong
- latency blowups
- loop-prone agent choreography

## 10. Model Routing

Use the model inventory you actually have.

### Final output tier

Use:

- `gpt-4o (fine-tuned)` for final artifact packaging when format stability matters most
- `gpt-4o` as the premium fallback

### Research and review tier

Use:

- `kimithinking`
- `deepseek`
- `mistral`

For:

- planning DAGs
- contradiction reviews
- SWOT pairing logic
- refusal decisions
- investor-objection reviews
- heavy reasoning over GraphRAG packets

### Utility tier

Use:

- `qwen2.5-coder`
- `glm4.7`
- `gemma`

For:

- prompt-to-form extraction
- label normalization
- TOON patch drafting
- lightweight clustering
- diagram token scaffolding

### Routing rule

- never spend premium model budget on simple extraction
- never let utility models publish final strategic claims
- always run reviewer logic separately from final prose assembly

## 11. Generation Flows

### 11.1 Supported input modes

The system must accept:

- existing structured forms
- freeform prompt input
- prompt plus website URL
- prompt plus competitor URLs
- uploaded pitch deck
- internal metrics upload
- partial forms with missing fields
- user edits after first generation

### 11.2 Input normalization rules

The normalizer should:

- detect stage: idea, MVP, growth, expansion
- detect model: B2B, B2C, SaaS, marketplace, AI, fintech, services, hybrid
- detect geography and currency
- infer missing fields as suggestions only
- surface ambiguity when there is material risk
- distinguish between fact, assumption, and desired future state

### 11.3 Fast mode vs deep mode

#### Fast mode

Purpose:

- preserve current user expectations
- return useful output quickly

Implementation:

- keep the existing main artifact routes
- run limited-source research
- use cached evidence when valid
- allow request/response generation where runtime stays short

#### Deep mode

Purpose:

- stronger verification
- more sources
- richer visuals
- living bundle creation
- monitoring enablement

Implementation:

- do not keep the HTTP request open for multi-minute jobs
- return `202 Accepted`
- return `task_id`
- stream progress over existing WebSocket routes
- persist checkpoints in Redis and MongoDB

### 11.4 Artifact-specific flow

#### Business Plan flow

1. parse structured input or prompt
2. build market, customer, competitor, and model queries
3. assemble shared bundle
4. retrieve subgraphs per section
5. write sections
6. validate each numeric or strategic claim
7. generate roadmap and scenario visuals
8. publish editable report

#### GTM flow

1. normalize product, target segment, geography, and stage
2. research ICP, competitors, channels, pricing, and search demand
3. build GTM strategy packet
4. generate segment choice, positioning, channel mix, launch phases, KPI plan, and experiment roadmap
5. render React Flow launch map
6. publish editable GTM workspace

#### SWOT flow

1. derive internal factors from user and internal data
2. derive external opportunities and threats from the bundle
3. score impact, confidence, and urgency
4. generate the matrix and TOWS actions
5. render graph view and mitigation chains
6. publish editable SWOT workspace

#### Pitch flow

1. extract slides
2. classify slide roles
3. compare claims against the shared bundle
4. score the narrative, proof, traction, and ask
5. generate investor objections and rewrites
6. render slide map and evidence mismatch view
7. publish editable slide-level analysis

## 12. Truth, Validation, Refusal, and Failure Handling

This is the most important section of the plan.

### 12.1 Publish rules

1. no hard metric without support
2. every key number must show source and date
3. estimates must be labeled as `Inference` or `Scenario`
4. contradictory evidence must be surfaced, not hidden
5. unsupported sections must publish as partial or blocked, never as verified

### 12.2 Confidence labels

Use:

- `Verified`
- `Corroborated`
- `Inference`
- `Scenario`
- `Weak Signal`
- `Blocked`

### 12.3 Refusal conditions

The system should refuse or downgrade when:

- the business premise is impossible or incoherent
- the user requests unsupported claims to be stated as facts
- the evidence base is too weak for a high-stakes claim
- internal and external data conflict without resolution
- a regulated-domain claim cannot be validated

Output in that case should be:

- a reality-check report
- missing-evidence list
- next-step collection prompts

### 12.4 HITL gates

Require human confirmation when:

- critical financial metrics fall below the confidence threshold
- deck claims conflict with retrieved evidence
- compliance-sensitive language appears
- internal data connector mapping is ambiguous

### 12.5 Failure classes

- provider timeout
- provider rate limit
- MCP unavailable
- scrape blocked
- malformed TOON response
- low-confidence synthesis
- contradiction detected
- diagram generation failure
- WebSocket disconnect
- partial artifact completion
- stale cache conflict

### 12.6 Required system behavior

For every failure:

1. checkpoint completed work
2. retry only within a step budget
3. fail over to the next provider if allowed
4. preserve user edits
5. mark affected nodes as partial or blocked
6. keep the artifact editable even when one visual fails
7. show the user exactly what failed and what still succeeded

### 12.7 Fallback examples

- search provider fails
  - use secondary provider
  - then cached bundle
  - then partial mode
- scrape fails
  - use alternate extraction path
  - then preserve search-only evidence
- premium writer unavailable
  - use review-tier model for temporary draft
  - flag for later premium re-run
- draw.io generation fails
  - publish React Flow-only view
  - keep later draw.io export available
- internal connector fails
  - continue with external-only plan
  - mark all internal overlays as unavailable

### 12.8 Monitoring and no-silent-failure rule

Add:

- provider health dashboard
- circuit breakers
- retry budgets
- stale-node counters
- alerting for repeated blocked bundles
- audit trails for every regeneration and edit

## 13. Living Bundle, Monitoring, and Diff/Patch

### 13.1 Living bundle behavior

The bundle should not die after initial generation.
It should stay refreshable.

Use cases:

- competitor launches a new feature
- funding event changes the pitch story
- regulatory change affects risks
- user edits target segment and downstream nodes become stale

### 13.2 Monitoring engine

Use Celery workers plus Celery Beat for:

- scheduled refresh checks
- keyword watches
- competitor event watches
- policy or news watches
- cache refreshes

### 13.3 Diff/Patch engine

When a user edits a section or node:

1. create a `bundle_patch.toon`
2. update the changed node
3. identify dependent nodes
4. mark only those nodes stale
5. re-run only affected retrieval and synthesis steps

Examples:

- changing `target_market` should stale:
  - pricing
  - channels
  - messaging
  - competitor set
- changing `revenue_model` should stale:
  - financials
  - pricing
  - deck ask logic

## 14. Speed and Heavy-System Design

### 14.1 Realistic delivery model

Deep research times of 2 to 5 minutes cannot sit inside a normal browser request lifecycle.
So the architecture must split:

- fast mode: immediate route response
- deep mode: task creation, progress streaming, later result fetch

### 14.2 Recommended task endpoints

Keep current endpoints intact for fast mode.
Add task-oriented deep endpoints such as:

- `POST /api/tasks/business-plan`
- `POST /api/tasks/gtm`
- `POST /api/tasks/swot`
- `POST /api/tasks/pitch`
- `GET /api/tasks/{task_id}`
- `GET /api/bundles/{bundle_id}`
- `POST /api/bundles/{bundle_id}/monitor`

Use current WebSocket progress delivery for deep mode:

- `/ws/progress/business`
- `/ws/progress/gtm`
- `/ws/progress/swot`
- `/ws/progress/pitch`

### 14.3 Semantic caching

Extend the existing Redis cache layer into semantic cache behavior:

- normalize query intent
- hash by company, artifact, geography, and freshness policy
- reuse recent evidence when still valid
- fetch only deltas when a close bundle already exists

Cache levels:

- raw search results
- extracted page content
- evidence nodes
- GraphRAG packets
- partial artifact sections

### 14.4 Suggested timing targets

| Artifact | Fast mode | Deep mode |
|---|---:|---:|
| Shared bundle seed | 5s-12s | 12s-30s |
| Business Plan | 20s-45s | 60s-150s |
| GTM | 15s-35s | 45s-110s |
| SWOT | 8s-20s | 25s-60s |
| Pitch Analysis | 25s-60s | 90s-240s |

Deep-mode timings assume:

- task-based async delivery
- streaming progress
- checkpoint recovery

## 15. Premium UX and Editable Strategy Workspace

### 15.1 Design direction

The UI should feel premium, editorial, and investor-ready.
Avoid generic dashboard styling.

Recommended direction:

- warm ivory, graphite, oxidized teal, brass accents
- serif + clean grotesk pairing for report readability
- subtle connector motion
- layered surfaces with evidence depth
- clear confidence color language

### 15.2 Shared workspace tabs

Each artifact should support:

- `Summary`
- `Evidence`
- `Map`
- `Metrics`
- `Sources`
- `Edit`
- `History`
- `Monitor`

### 15.3 Editable surface rules

Every artifact must allow editing of:

- headings
- body sections
- assumptions
- numeric ranges
- confidence labels
- node labels
- node links
- SWOT entries
- GTM channel cards
- pitch feedback blocks

Editing behavior:

- inline edit
- save draft without full regeneration
- regenerate one block only
- compare revisions
- keep version history
- sync edits back into the bundle

### 15.4 React Flow usage

Use React Flow for all four artifacts:

- Business Plan
  - market, customer, competitor, finance, risk, milestone nodes
- GTM
  - ICP, message, pricing, channel, KPI, launch-phase nodes
- SWOT
  - quadrant nodes plus action edges
- Pitch
  - slide, issue, evidence, and rewrite nodes

Each node should support:

- evidence drawer
- inline editing
- status badge
- stale marker
- single-node regeneration

### 15.5 draw.io usage split

Use:

- `drawio-mcp-server`
  - runtime diagram generation and mutation
- `drawio-desktop`
  - offline refinement and polished export
- `next-ai-draw-io` ideas
  - prompt-based diagram edits
  - history restore
  - document-to-diagram workflows

Recommended split:

- React Flow for live in-app editing and evidence navigation
- draw.io for polished exportable stakeholder diagrams

### 15.6 Real-time confidence streaming

As the artifact is generated or refreshed:

- green = verified
- amber = inference
- red = contradiction or blocked

This helps the user spot risky claims before reading the entire report.

### 15.7 Future premium extensions

- multiplayer strategy war room
- scenario sliders that re-write narrative sections
- investor bot arena
- compliance sentinel overlays
- native pitch generation export

## 16. FastAPI Implementation Shape

The cleanest implementation is inside the current FastAPI app, not beside it.

### Recommended backend structure

```text
Server1_FastApi/app/services/intelligence/
  toon/
    parser.py
    serializer.py
    patcher.py
  bundles/
    bundle_service.py
    bundle_repository.py
    stale_propagation.py
  graph/
    evidence_graph.py
    graph_retriever.py
    graph_ranker.py
  mcp/
    search_hub_client.py
    scrape_extract_client.py
    market_intel_client.py
    growth_seo_client.py
    internal_data_client.py
    visualization_client.py
    trust_guard_client.py
  orchestration/
    planner.py
    dag_runner.py
    task_router.py
    model_router.py
  artifacts/
    business_plan_pipeline.py
    gtm_pipeline.py
    swot_pipeline.py
    pitch_pipeline.py
  memory/
    founder_memory.py
    approved_assumptions.py
  monitoring/
    monitor_service.py
    refresh_tasks.py
    alert_rules.py
  trust/
    source_quality.py
    contradiction_checker.py
    refusal_gate.py
    publish_gate.py
    failure_policy.py
  edits/
    editable_report_service.py
    version_history.py
    node_edit_service.py
```

### Recommended route additions

```text
Server1_FastApi/app/api/routes/
  intelligence_tasks_routes.py
  intelligence_bundle_routes.py
  intelligence_edit_routes.py
  intelligence_monitor_routes.py
  intelligence_diagram_routes.py
```

### Recommended frontend structure

```text
lliveupdatedstreaming/src/features/intelligence/
  components/
    StrategyWorkspace.tsx
    EvidenceDrawer.tsx
    ConfidenceBadge.tsx
    FreshnessBadge.tsx
    StrategyGraph.tsx
    EditableSectionCard.tsx
    VersionHistoryDrawer.tsx
    ScenarioPanel.tsx
    MonitorPanel.tsx
    DiagramEditorPanel.tsx
  hooks/
    useBundleTask.ts
    useBundleMonitor.ts
    useArtifactEdit.ts
    useStrategyGraph.ts
  types/
    toon.ts
    bundle.ts
    artifact.ts
```

## 17. API Strategy And External Sources

Use the listed APIs in tiers.

### Primary production APIs

- `GNews`
  - fast current headlines and market coverage
- `TheNewsAPI`
  - reliable enrichment for recent articles
- `The Guardian API`
  - editorial cross-check and policy/news verification
- `Finnhub`
  - company news, public comps, fundamentals
- `Alpha Vantage`
  - market and economic context

### Strong secondary APIs

- `NewsData.io`
- `MediaStack`
- `World News API`
- `Currents API`
- `New York Times API`
- `you.com API`
- `CoinDesk API`

Use them for:

- overflow capacity
- specific vertical enrichments
- extra corroboration when primary providers disagree

### Not recommended as the main production source

- `NewsAPI` free developer plan

Reason:

- better as development or overflow than as the primary live-production path

### SEO API note

If you later want OpenSEO-depth backlink and domain workflows, add an SEO data provider in a later phase.
Until then:

- use search + scrape + domain-level heuristics
- keep SEO claims labeled appropriately when hard backlink data is unavailable

## 18. Implementation Roadmap

### Phase 0: project alignment

- standardize progress type naming
- map current request models to `user_brief.toon`
- identify shared fields across Business Plan, GTM, SWOT, and Pitch

### Phase 1: TOON and shared bundle foundation

- add TOON parser, serializer, and patcher
- create bundle, evidence-node, evidence-edge, and artifact-version collections
- add planner, model router, and publish gate
- port source-quality logic from `FASTAPI_COMMUNITY`

### Phase 2: MCP adapters and semantic cache

- build `search-hub-mcp`
- build `scrape-extract-mcp`
- build `market-intel-mcp`
- build `growth-seo-mcp`
- extend Redis cache into semantic reuse

### Phase 3: GraphRAG and fast artifact upgrade

- add evidence graph service
- add subgraph retrieval per section
- wire Business Plan, GTM, and SWOT to the shared bundle in fast mode
- reuse pitch async ideas for bundle-backed validation

### Phase 4: deep async mode and living bundles

- add task routes returning `202 Accepted`
- add bundle monitor rules
- add Celery Beat refresh jobs
- add checkpoint recovery and partial publish behavior

### Phase 5: premium UI and editing

- build shared workspace shell
- add React Flow across all four artifacts
- add evidence drawers, node editing, version history
- add draw.io generation and export

### Phase 6: internal data and advanced simulations

- add `internal-data-mcp`
- add scenario simulation
- add investor persona review
- add compliance sentinel for regulated verticals

### Phase 7: hardening

- provider outage drills
- failure-injection testing
- TOON contract tests
- browser E2E with live progress
- source-quality regression suite
- concurrency and rate-limit load testing

## 19. Final Recommendation

Build this as a **FastAPI-native, TOON-first, living strategic intelligence system** on top of the current `Server1_FastApi` and `lliveupdatedstreaming` codebase.

The correct product shape is:

- one living evidence graph
- one shared bundle per company or request
- GraphRAG retrieval for every section
- planner-managed DAG orchestration
- async deep mode with task IDs and WebSocket progress
- strong truth gates, refusal logic, and failure recovery
- premium editable React Flow workspaces with draw.io export

This is the best path to:

- faster generation
- stronger present-day accuracy
- lower duplication across artifacts
- better trust for founders and investors
- real-world usability instead of template output

*** Important points 1 : Keep the current inputs structure for the Business plan , GTM , SWOT AND PITCH DECK ANALYSIS (you can change their structure or design well but don't remove any input value becasue we have structed it by using the real time search ) and also keep the prompt based input for all the Business plan, GTM, Swot and pitch deck analysis. And also while taking the input make a designed background which look premium and next level with animation , motion and 3D. *** 

*** Important point 2: See the generated business plan , gtm , swot and ptich deck analysis need to be editable , downlaodable (in pdf , document also ) and also use the correct output for displaying and display it as greate as possible. if model as any doubts as the user for the input accordingly give the business plan , gtm , swot , pitch deck. See don't use the present model you cna use it as a reference but don't completely use it *** 

## 20. Source List

### Local project references

- `Server1_FastApi/app/main.py`
- `Server1_FastApi/app/core/progress.py`
- `Server1_FastApi/app/core/celery.py`
- `Server1_FastApi/app/core/cache_service.py`
- `Server1_FastApi/app/db/mongo.py`
- `Server1_FastApi/app/db/redis.py`
- `Server1_FastApi/app/api/routes/business_routes_refactored.py`
- `Server1_FastApi/app/api/routes/gtm_routes_refactored.py`
- `Server1_FastApi/app/api/routes/pitch_analysis_routes_refactored.py`
- `Server1_FastApi/app/api/routes/swot_routes.py`
- `Server1_FastApi/app/api/routes/progress_ws_routes.py`
- `Server1_FastApi/app/services/business_service.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/mcp_gateway.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/source_quality.py`
- `FASTAPI_COMMUNITY/app/services/realtime_syn/validator.py`
- `lliveupdatedstreaming/src/App.tsx`
- `lliveupdatedstreaming/src/pages/GTMStrategy.tsx`
- `lliveupdatedstreaming/src/components/business/Flowchart.tsx`
- `lliveupdatedstreaming/src/components/business/nodereact.tsx`
- `complete_plan.md`

### Strategy references

- `https://www.sba.gov/business-guide/plan-your-business/write-your-business-plan`
- `https://www.sba.gov/business-guide/plan-your-business/market-research-competitive-analysis`
- `https://www.productplan.com/glossary/go-to-market-strategy/`
- `https://asana.com/resources/go-to-market-gtm-strategy`
- `https://www.evms.edu/media/evms_public/departments/gme/2018_acgme_conference_-_hn/ACGME_Self_Study_SWOT_Guide.pdf`
- `https://pages.visible.vc/fundraising-road-map`

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

- `https://github.com/coreyhaines31/marketingskills`
- `https://github.com/unicodeveloper/competitor-analysis`
- `https://github.com/every-app/open-seo`
- `https://github.com/jgraph/drawio-desktop`
- `https://github.com/lgazo/drawio-mcp-server`
- `https://github.com/DayuanJiang/next-ai-draw-io`
- `https://github.com/koral--/android-gif-drawable`
- `https://github.com/Decodo/decodo-openclaw-skill`
- `https://github.com/langchain-ai/deepagents`
- `https://github.com/NousResearch/hermes-agent`
- `https://github.com/u14app/deep-research`
- `https://github.com/blazickjp/arxiv-mcp-server`
- `https://github.com/king-of-the-grackles/reddit-research-mcp`
- `https://github.com/gvaibhav/TAM-MCP-Server`
- `https://github.com/OctagonAI/octagon-vc-agents`
- `https://github.com/OctagonAI/octagon-mcp-server`
- `https://github.com/mz462/stock-research-mcp`
- `https://github.com/smitkunpara/tradingview-mcp`
- `https://github.com/Mohit-Dhawan98/adalyst-mcp`
- `https://github.com/ezbiz-services/mcp-seo-marketing`
- `https://github.com/profitelligence/profitelligence-mcp-server`
- `https://github.com/paperclipai/paperclip`
- `https://github.com/supermemoryai/supermemory`
- `https://github.com/slinusc/web-search-mcp-server`
- `https://github.com/Cometdev312/Dappier-MCP-Server-Real-Time-Web-Market-Data-for-AI-Agents`
- `https://github.com/positive666/Deep_search_lightning`
- `https://github.com/MattimaxForce/duckduckgo-mcp`
- `https://github.com/dotnetpower/infomesh`
- `https://github.com/cyxzdev/Uncodixfy`
- `https://github.com/marianfoo/sap-ai-mcp-servers`
- `https://github.com/patchy631/ai-engineering-hub`
- `https://github.com/andrewyng/context-hub`
- `https://github.com/alirezarezvani/claude-skills`
- `https://github.com/bitbonsai/mcpvault`
- `https://github.com/Michaelliv/pi-generative-ui`
- `https://github.com/nandanNM/crazxy-ui`
- `https://github.com/pbakaus/impeccable`
- `https://github.com/karpathy/autoresearch`
- `https://github.com/microsoft/aspire`
- `https://github.com/lightpanda-io/browser`
- `https://github.com/bytedance/deer-flow`
- `https://github.com/alvinunreal/awesome-opensource-ai`
- `https://github.com/timwuhaotian/the-pair`
- `https://github.com/kesslernity/awesome-copilot-studio-agents`
- `https://github.com/agentscope-ai/agentscope`
- `https://github.com/WecoAI/awesome-autoresearch`
- `https://github.com/AltimateAI/altimate-code`
- `https://github.com/mitkox/vllm-turboquant`
- `https://github.com/ggml-org/llama.cpp`
- `https://github.com/millionco/expect`
