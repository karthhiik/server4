# Slide Content V7 Standalone Research Plan

Production-grade standalone plan for `slide_content` generation that plugs into `PREMIUM_SLIDE_MCP_V7_PLAN.md` without modifying that file.

Scope:
- `server4` only
- pitch deck first
- investor-friendly output
- reading mode + presentation mode
- 56+ style system
- real-time factual retrieval with multi-source cross-validation
- MCP + multi-agent pipeline with debate, verification, and grounding
- startup-cost-aware provider routing with circuit breakers
- full failure handling with graceful degradation
- all 40+ API providers from `.env.example` mapped and utilized
- background processing via Celery for heavy research
- WebSocket/SSE streaming for real-time progress
- vector memory via ChromaDB for evidence reuse
- local HuggingFace models for zero-cost classification and embedding

This plan is based on the actual current `server4` code, the real API inventory in `.env.example`, verified public provider limits, and architecture patterns from these repositories:
- `u14app/deep-research`
- `assafelovic/gpt-researcher`
- `HKUDS/LightRAG`
- `microsoft/graphrag`
- `firecrawl/firecrawl-mcp-server`
- `lightpanda-io/browser`
- `infiniflow/ragflow`

## 1. Fit With The Existing V7 Master Plan

This document is additive to `PREMIUM_SLIDE_MCP_V7_PLAN.md`.

It fits directly into these V7 areas:
- Section 5 Agent System: this plan defines the content-side micro-agent workflow.
- Section 13 Current LLM Inventory & Usage: this plan reuses the current model inventory and adds task-level routing rules.
- Section 19 Reading vs Presentation Modes: this plan formalizes a dual-content contract per slide.
- Section 22 Pitch Deck Domain Intelligence: this plan operationalizes pitch-specific evidence, debate, and investor copy rules.

This plan does not replace the V7 renderer, theme engine, or deck assembly architecture. It upgrades the `slide_content` layer so the rest of V7 receives stronger, verified, mode-aware content objects.

## 2. Complete `.env.example` API Inventory — Every Provider Mapped

Every single API key in `.env.example` is assigned a role, budget class, and routing priority. Nothing is left unused.

### 2.1 LLM Model Inventory (7 Tiers)

| Tier | Provider | Model | Env Vars | Cost | Role |
| --- | --- | --- | --- | --- | --- |
| T0 | Azure | Kimi-K2-Thinking | `AZURE_KIMI_ENDPOINT`, `AZURE_KIMI_API_KEY`, `AZURE_KIMI_VERSION_DEPLOYMENT`, `AZURE_KIMI_VERSION_MODEL` | Subscription | Deep reasoning, debate synthesis, executive narrative |
| T0.5 | Azure | Phi-4-reasoning | `Phi-4-reasoning_endpoint`, `Phi-4-reasoning_deployment_name`, `Phi-4-reasoning_api_key` | Subscription | Reasoning fallback, evidence validation, logical proof |
| T1 | Azure | DeepSeek-V3.2 | `DEEPSEEK_API_KEY`, `DEEPSEEK_ENDPOINT`, `DEEPSEEK_MODEL_NAME`, `DEEPSEEK_API_VERSION` | Subscription | Code generation, technical synthesis, evidence normalization |
| T2 | Azure | GPT-4o-mini | `AZURE_GPT4O_MINI_ENDPOINT`, `AZURE_GPT4O_MINI_API_KEY`, `AZURE_GPT4O_MINI_DEPLOYMENT_NAME`, `AZURE_GPT4O_MINI_Model_NAME`, `AZURE_GPT4O_MINI_VERSION` | Subscription | Structured JSON, speaker notes, quick edits |
| T3 | Azure | Mistral-medium | `Mistral_endpoint`, `Mistral_deployment_name`, `Mistral_api_key` | Subscription | Narrative polish, investor copy, premium writing |
| T4 | Groq | LLaMA/Mixtral | `GROQ_API_KEY` through `GROQ_API_KEY7` (8 keys) | Free | Fast formatting, query rewriting, bulk transforms |
| T5 | Cloudflare | GLM-4.7-flash, Qwen-2.5-coder-32b, Gemma-3-12b | `CF_WORKER_GLM_URL`, `CF_WORKER_GLM_TOKEN`, `CF_WORKER_QWEN_URL`, `CF_WORKER_GEMMA_URL`, `CF_WORKER_GEMMA_TOKEN` | Free | Embeddings, RAG, classification, bulk rewriting |
| T5b | Cloudflare | Phoenix-1.0, Lucid-Origin | `CF_WORKER_PHOENIX_URL`, `CF_WORKER_PHOENIX_TOKEN`, `CF_WORKER_LUCID_URL`, `CF_WORKER_LUCID_TOKEN` | Free | Image description, creative generation |
| T6 | HuggingFace | TinyLlama, Flan-T5, Phi-2 | `HUGGINGFACE_API_TOKEN`, `USE_TINYLLAMA`, `USE_FLAN_T5`, `USE_PHI2`, `MODEL_DEVICE` | Free/Local | Zero-cost intent classification, evidence typing, claim categorization, embedding generation |
| T7 | OpenRouter | Qwen-3.6-plus:free | `openroute_service_api_key`, `openroute_model_free` | Free | Last-resort fallback for all text tasks |

### 2.2 Research API Inventory (All Providers)

| Category | Provider | Env Var(s) | Verified Limit | Role in Slide Content |
| --- | --- | --- | --- | --- |
| **Web Search** | Serper | `SERPER_API_KEY`, `SERPER_API_KEY2`, `SERPER_API_KEY3` | ~2500/key/month | Primary web search, round-robin across 3 keys |
| | SerpAPI | `SERPAPI_KEY`, `SERPAPI_KEY2` | 250/month/key free, 50/hour | Google-results fallback, round-robin across 2 keys |
| | Tavily | `TAVILY_API_KEY` | 1000 credits/month free | Semantic company/market discovery, deep search |
| | Exa.ai | `exa.ai_key` | ~1000 req/month free | Semantic search with autoprompt, competitor/category |
| | You.com | `you.com_API` | Varies | AI-powered search fallback for conversational queries |
| | Search API | `search_api` | Varies | Generic search fallback, reserve only |
| **Scraping** | Firecrawl | `firecrawl.dev_key` | 500 one-time credits, 2 concurrent, search 2 credits/10 results | Structured extraction, JS-heavy sites, map→scrape flow |
| | Jina.ai | `jina.ai_key` | Search 100 RPM, Reader 20 RPM anonymous | URL reader, reranking, deep-search helper |
| | ScrapeDo | `SCRAPE_DO_API_KEY` | Varies | Proxy-based scraping for sites that block direct requests, anti-bot bypass |
| **News** | NewsAPI | `NEWSAPI_KEY` | 100 req/day, 24hr delay | Development/testing only, NOT production core |
| | NewsData | `NEWSDATA_API_KEY` | 200 credits/day, 12hr delay | Low-cost backup news |
| | Guardian | `The_Guardian_API_key` | 500 calls/day, 1/sec | Free news backbone, reliable JSON |
| | World News API | `World_news_api_key` | Varies | International news coverage, non-English markets |
| **Financial** | FRED | `FRED_API_KEY` | 120/minute | GDP, unemployment, inflation, interest rates, consumer spending |
| | Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | ~25/day free | Sector performance, occasional enrichment only |
| | Finnhub | `FINNHUB_API_KEY` | 60/minute free | Market news, company profiles, stock data |
| | Polygon.io | `POLYGON_API_KEY` | Varies | Ticker data, market cap, employee count, SIC codes |
| | FMP | `financialmodelingprep.com_key` | Varies | Company profiles, sector data, revenue, CEO info |
| | CoinDesk | `coindesk.com_api_key` | Varies | Crypto market data for blockchain/web3 pitch decks |
| | EODHD | `EODHD_API_key` | Varies | End-of-day historical data, fundamental data, macro indicators |
| **Macro/Public** | World Bank | `WORLDBANK_API_KEY` (optional, no auth needed) | No limit | Default macro-economic, population, GDP by country |
| | US Census | `CENSUS_API_KEY` | No strict limit | Demographics, population, median income, home values |
| | NASA APOD | `NASA_APDO_API` | 1000/hour | Space/science imagery for deep-tech or science pitch decks |
| **Academic** | CORE | `CORE_API_KEY` | 1 batch or 5 single/10sec | Academic paper search for deep-tech validation |
| **Social** | Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | 60/minute with OAuth | Community signals, user sentiment, product mentions |
| | GitHub | `GITHUB_TOKEN` | 5000/hour authenticated | OSS traction, repo stars, dev community validation |
| | YouTube | `YOUTUBE_API_KEY` | 10,000 units/day (search=100 units) | Video evidence, product demos, conference talks |
| | ProductHunt | `PRODUCTHUNT_API_KEY` | Varies | Product launch traction, upvotes, category ranking |
| **Utility** | API Ninjas | `API_NINJAS_KEY` | Varies | Facts, quotes, historical data, domain-specific trivia |
| | AbuseIPDB | `ABUSELPDB_API` | N/A | Reserved for cybersecurity pitch decks only |
| **Image Gen** | Azure Flux | `AZURE_FLUX_ENDPOINT`, `AZURE_FLUX_API_KEY`, `AZURE_FLUX_DEPLOYMENT_NAME` | Subscription | Chart thumbnails, hero slide visuals, custom imagery |

### 2.3 Infrastructure Services

| Service | Env Vars | Role in Slide Content |
| --- | --- | --- |
| MongoDB | `MONGODB_URI`, `MONGODB_DB_NAME` | Evidence store, deck runs, claim history, presentation persistence |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_SSL`, `REDIS_DB`, `REDIS_URL` | Provider health cache, rate limit counters, research cache (TTL), real-time pub/sub |
| Celery | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_TIME_LIMIT`, `CELERY_WORKER_CONCURRENCY` | Background deep-research tasks, batch evidence collection, deck pre-warming |
| WebSocket | `WEBSOCKET_ENABLED`, `SOCKET_CORS_ORIGINS` | Real-time streaming to frontend for research progress |
| Azure Blob | `BLOB_STORAGE_CONNECTION_STRING`, `BLOB_CONTAINER_NAME` | Generated asset storage (charts, images, exported decks) |
| ChromaDB | `EMBEDDINGS_PATH` | Local vector store for evidence embeddings and semantic retrieval |
| Airtable | `VITE_AIRTABLE` | Feedback collection, analytics, user style preferences |
| Secret Key | `SECRET_KEY` | JWT signing, session management |

## 3. What Already Exists In `server4`

The current codebase has strong foundations. The main problem is not missing infrastructure; it is that the current content path is too flat, too linear, and does not utilize the full API inventory.

### 3.1 Existing anchors already in the repo

| File | What It Does | Current Gap |
| --- | --- | --- |
| `app/config.py` | Normalizes 40+ env-backed API keys across 7 LLM tiers | No provider health tracking or budget monitoring |
| `app/services/llm/model_router.py` | Routes tasks across Azure/Groq/Cloudflare/OpenRouter with 3-deep fallback | Missing task types for research, debate, citation guard |
| `app/mcp/tool_registry.py` | 40+ MCP tools for presentations, slides, generation, export | Missing research-specific tools and evidence verification tools |
| `app/mcp/brain_mcp/config.py` | Research depth, cache TTL, parallelism, rate limits | Rate limits are static, no dynamic circuit breaker |
| `app/mcp/brain_mcp/generators/outline_generator.py` | Slide outlines with `needs_research`, `needs_chart`, `needs_image` flags | No `research_priority`, `evidence_requirements`, or `slide_importance` |
| `app/mcp/brain_mcp/generators/slide_generator.py` | JSON slide content with retry logic and quality guards | Consumes flattened `research_context` string, no structured evidence |
| `app/mcp/brain_mcp/generators/batch_generator.py` | Parallel slide generation with semaphore (max 5) | No slide dependency ordering, no shared evidence graph |
| `app/mcp/brain_mcp/generators/chart_generator.py` | Chart data synthesis (bar, line, pie, donut, area) | No real-time data feed integration, no auto-source attribution |
| `app/mcp/brain_mcp/engines/search_engine.py` | Serper(3)→Tavily→SerpAPI(2)→Exa→You.com chain | Linear fallback, no intent routing, missing ScrapeDo and Search API |
| `app/mcp/brain_mcp/engines/scraper_engine.py` | Firecrawl + Jina extraction | Missing ScrapeDo, no anti-bot strategy, no Firecrawl map/agent modes |
| `app/mcp/brain_mcp/engines/news_engine.py` | NewsAPI→NewsData→Guardian fallback | Missing World News API, no freshness scoring |
| `app/mcp/brain_mcp/engines/market_engine.py` | FRED, Alpha Vantage, Finnhub | Missing EODHD, CoinDesk, no cross-validation |
| `app/mcp/brain_mcp/engines/financial_engine.py` | Polygon, FMP, Census | No cross-source verification, no confidence scoring |
| `app/mcp/brain_mcp/engines/academic_engine.py` | CORE | No citation impact scoring, no full-text extraction |
| `app/mcp/brain_mcp/engines/social_engine.py` | Reddit, GitHub, YouTube; ProductHunt configured but not implemented | ProductHunt not functional, no sentiment analysis |
| `app/mcp/brain_mcp/prompts/investor_system.py` | YC, Sequoia, traction, market sizing, unit economics prompts | No debate prompt templates, no evidence grounding rules |
| `app/mcp/brain_mcp/prompts/style_system.py` | 12 writing styles with full rules | Only 12 styles, need 56+ |
| `app/mcp/brain_mcp/prompts/quality_guards.py` | Fluff detection, unsourced claims, density checks | No cross-slide consistency, no evidence-backed verification |
| `app/services/chromadb_service.py` | Vector search service | Not integrated into slide content pipeline |
| `app/services/image_service.py` | Azure Flux image generation | Not connected to slide visual generation |
| `app/services/slides_new/agents/` | 6+ agents (CEO, CTO, Researcher, Designer, Code, QA) | Not integrated into content verification loop |

## 4. Current Blockers In The Existing `slide_content` Path

### 4.1 Flattened research input

`slide_generator.py` consumes a single flattened `research_context` string. That means:
- no source lineage per claim
- no numeric claim verification contract
- no clean separation between deck-wide context and slide-local evidence
- no structured debate or confidence scoring before copy generation
- no way to trace which provider produced which fact

### 4.2 Linear search fallback

`search_engine.py` uses "try provider A, then B, then C" without understanding what kind of evidence is needed. A market sizing query should not use the same provider chain as a technical validation query.

### 4.3 No evidence graph

The current flow collects results but does not create a graph of entities, claims, relationships, and citations that can be reused across slides.

### 4.4 No pitch-debate layer

The code has investor prompts, but there is no explicit CEO vs CTO vs Research loop to challenge weak founder claims before they hit the slide.

### 4.5 Style system is too small

12 styles is insufficient for 56+ premium narrative styles across investor, reading, and presentation use cases.

### 4.6 Fallback content is too generic

The current fallback path in `slide_generator.py` risks producing placeholder-like slide copy when research quality is low.

The correct failure mode is:
- mark the slide as `insufficient_verified_data`
- surface what is missing in structured JSON
- keep structure usable for the renderer
- never invent investor-facing facts
- offer the user actionable suggestions for what data to provide manually

### 4.7 No provider health monitoring

No circuit breaker. If Serper is down, every request still tries Serper first, wastes time, then falls back.

### 4.8 No background processing

All research happens in the request path. Deep research for 15-slide pitch decks can take 30-60 seconds. Should use Celery background tasks with WebSocket progress.

### 4.9 Missing API integrations

These APIs exist in `.env.example` but are NOT used in the current content pipeline:
- ScrapeDo (proxy-based scraping)
- World News API (international coverage)
- CoinDesk (crypto data)
- EODHD (historical financial data)
- ProductHunt (product traction)
- API Ninjas (facts/quotes)
- NASA APOD (science imagery)
- HuggingFace local models (zero-cost classification)
- ChromaDB (vector search for evidence)
- Azure Flux (slide image generation)

### 4.10 No evidence cross-validation

When two providers return conflicting numbers for the same metric, the system has no mechanism to detect or resolve the conflict.

### 4.11 No adaptive research depth

Every slide gets the same research effort. A title slide does not need the same depth as a market sizing slide.

## 5. External Patterns Worth Importing

This plan borrows patterns from proven production systems, adapted to the actual `server4` architecture.

### 5.1 Deep Research / GPT Researcher pattern

From `u14app/deep-research` and `assafelovic/gpt-researcher`:
- break research into explicit stages with progress events
- stream progress continuously via SSE/WebSocket
- use tool selection before tool execution (plan-then-execute)
- maintain research steps as structured outputs, not only final prose
- self-correcting query refinement when initial results are weak
- multi-iteration deepening with diminishing cost thresholds

Imported decisions:
- `server4` slide research becomes a staged pipeline with explicit events and structured intermediate objects.
- query rewriting happens via Groq (free, fast) before spending Tavily/Exa credits.
- each research stage emits a structured progress event consumable by frontend React Flow.

### 5.2 Firecrawl MCP pattern

From `firecrawl/firecrawl-mcp-server`:
- use `search -> map -> scrape -> agent` escalation
- prefer JSON extraction over raw markdown when structure matters
- use agent mode only as a last resort (5 free daily runs)
- batch URLs to minimize credit consumption

Imported decisions:
- `server4` must NOT invoke Firecrawl agent by default. Cost: 2 credits per search/10 results.
- escalation order: Jina Reader (free RPM) → Firecrawl scrape (markdown) → ScrapeDo (proxy) → Firecrawl agent (last resort).
- JSON extraction mode preferred when target data is structured (pricing tables, feature lists, financial reports).

### 5.3 GraphRAG pattern

From `microsoft/graphrag`:
- separate local search from global search
- use community summaries for dataset-wide reasoning
- enforce evidence-grounded response generation
- map-reduce pattern for large evidence sets

Imported decisions:
- `server4` slide content uses deck-global evidence summaries for narrative consistency, and slide-local evidence bundles for factual precision.
- community summaries are generated once per deck run and shared across all slides for coherent storytelling.
- map-reduce used when evidence set exceeds single-context-window capacity.

### 5.4 LightRAG / RAGFlow pattern

From `HKUDS/LightRAG` and `infiniflow/ragflow`:
- keep entity-relation lineage connected to source chunks
- support grounded citations as first-class output
- mix graph reasoning with chunk retrieval (not vector-only)
- agentic reasoning with canvas DSL for complex analysis

Imported decisions:
- `server4` creates an in-session evidence graph for each deck run, not just a bag of search snippets.
- every node and edge stores source lineage traceable to a specific API call.
- ChromaDB used for vector indexing of evidence chunks, with graph overlay for relationship queries.

### 5.5 Lightpanda pattern

From `lightpanda-io/browser`:
- lightweight JS execution
- semantic DOM extraction → semantic tree / markdown
- MCP server for browser automation

Imported decision:
- use as design reference for optional lightweight browser adapter for hard JS-heavy pages.
- phase 6 dependency, not phase 1. Firecrawl + Jina + ScrapeDo cover most needs.

## 6. Design Principles For The New `slide_content` Layer

1. Pitch deck first. Every design decision optimizes for investor-grade output.
2. Facts before words. No copy is generated until evidence is collected, normalized, and scored.
3. Deck-global coherence plus slide-local evidence. All slides share a truth graph; each slide gets focused evidence bundles.
4. Reading mode and presentation mode must share the SAME evidence base. No factual divergence.
5. No invented claims. If evidence is insufficient, the system says so explicitly rather than generating confident-sounding filler.
6. Do not spend premium API budget until low-cost routes fail. Free → Cloudflare → Groq → Azure.
7. Reuse research across slides. Evidence collected for the market slide should enrich the competition and GTM slides.
8. Keep the output directly consumable by V7 DSL/render layers. No intermediate format translation.
9. Every numeric claim must have a traceable citation. No exceptions for pitch decks.
10. Fail loud, not quiet. Users must know when evidence is weak, not discover it in an investor meeting.
11. Use ALL available APIs. Every provider in `.env.example` has a defined role and routing priority.
12. Background-first for heavy work. Deep research uses Celery tasks with WebSocket progress streaming.

## 7. Proposed Architecture: Slide Content Control Plane

### 7.1 New control flow (Full Pipeline)

```text
User brief + V7 slides plan
    │
    ├── [Stage 0] Intent Classification (HuggingFace local, zero-cost)
    │   └── Classify deck type, audience, sector, urgency, depth
    │
    ├── [Stage 1] Slide Research Planner (Groq, free)
    │   ├── Analyze outline for evidence requirements per slide
    │   ├── Assign research_priority: hero | standard | minimal
    │   ├── Generate sub-queries per slide with intent tags
    │   └── Plan provider routing by evidence type
    │
    ├── [Stage 2] Provider Router + Circuit Breaker
    │   ├── Check provider health (Redis cache)
    │   ├── Check budget counters (Redis)
    │   ├── Route to optimal provider chain per intent
    │   └── Background: Celery task for deep research
    │
    ├── [Stage 3] Multi-Source Evidence Collection (Parallel)
    │   ├── Deterministic APIs (World Bank, FRED, Census, Polygon, FMP)
    │   ├── Web Search (Serper → Tavily → SerpAPI → Exa → You.com)
    │   ├── News (Guardian → NewsData → World News → NewsAPI)
    │   ├── Financial (Finnhub → EODHD → CoinDesk → Alpha Vantage)
    │   ├── Scraping (Jina → Firecrawl → ScrapeDo)
    │   ├── Academic (CORE → GitHub)
    │   ├── Social (Reddit → GitHub → ProductHunt → YouTube)
    │   └── Specialty (API Ninjas, NASA APOD)
    │
    ├── [Stage 4] Evidence Normalization → FactPackets
    │   ├── Deduplicate across providers
    │   ├── Assign confidence scores
    │   ├── Cross-validate conflicting claims
    │   ├── Classify claim types (numeric, qualitative, trend, quote)
    │   └── Generate citation labels
    │
    ├── [Stage 5] Evidence Graph Construction
    │   ├── Entity extraction (companies, markets, metrics, personas)
    │   ├── Relationship mapping (supports, contradicts, compares_to)
    │   ├── Store in ChromaDB for vector retrieval
    │   ├── Build community summaries (deck-global themes)
    │   └── WebSocket: stream graph build progress
    │
    ├── [Stage 6] Slide Evidence Bundle Assembly
    │   ├── Local search: map slide query → relevant FactPackets
    │   ├── Global search: inject community summaries for coherence
    │   ├── Rerank by relevance, freshness, source authority (Jina reranker)
    │   └── Fit evidence within context window budget
    │
    ├── [Stage 7] Pitch Debate Loop (pitch mode only)
    │   ├── CEOStoryAgent proposes thesis (Kimi-K2-Thinking)
    │   ├── CTOTechnicalAgent challenges feasibility (DeepSeek-V3)
    │   ├── FinancialEvidenceAgent challenges numbers (Phi-4-reasoning)
    │   ├── ResearchChiefAgent resolves with citations (DeepSeek-V3)
    │   ├── Max 3 debate rounds per slide group
    │   └── Output: approved_claims + rejected_claims + open_risks
    │
    ├── [Stage 8] Dual-Mode Content Generation
    │   ├── Presentation mode writer (Groq for speed)
    │   ├── Reading mode writer (DeepSeek for depth)
    │   ├── Speaker notes generator (GPT-4o-mini)
    │   ├── Chart data synthesizer (from FactPackets, not hallucinated)
    │   └── Image prompt generator (for Azure Flux)
    │
    ├── [Stage 9] Style Adaptation
    │   ├── Apply deck-level master style
    │   ├── Apply slide-level micro-style overrides
    │   └── Tone/density transformation (Cloudflare, free)
    │
    ├── [Stage 10] Citation Guard + Quality Firewall
    │   ├── Every numeric claim → must map to FactPacket
    │   ├── Fluff word detection → reject and rewrite
    │   ├── Cross-slide consistency check → number conflicts
    │   ├── Investor readiness check → TAM/SAM/SOM, traction, ask
    │   ├── Density check → presentation ≤15 words, reading unlimited
    │   └── Mark insufficient slides explicitly
    │
    └── [Stage 11] Final SlideContentContract JSON
        ├── presentation_mode + reading_mode + speaker_notes
        ├── citations array with source URLs
        ├── claim_status: verified | partial | insufficient
        ├── missing_data array for user follow-up
        ├── confidence_score: 0.0 to 1.0
        └── Stream to V7 renderer via WebSocket
```

### 7.2 The fundamental change

`slide_generator.py` must stop taking only a flattened research string.

The new content path takes a structured `SlideEvidenceBundle` which carries:
- per-claim source lineage
- confidence scores
- debate approval status
- cross-validation results
- freshness metadata

## 8. New Core Data Objects

### 8.1 `FactPacket`

Every sourced claim is normalized into a common evidence unit. This is the atomic building block of the entire system.

```python
@dataclass
class FactPacket:
    id: str                          # "fp_market_001"
    claim: str                       # "Global smartphone market grew by 7.8% in Q3 2024"
    claim_type: ClaimType            # NUMERIC | QUALITATIVE | TREND | QUOTE | STATISTIC | COMPARATIVE
    value: Optional[float]           # 7.8
    unit: Optional[str]              # "%"
    as_of: Optional[str]             # "2024-Q3"
    freshness_class: FreshnessClass  # REAL_TIME | CURRENT | RECENT | HISTORICAL | UNDATED
    entity_keys: list[str]           # ["smartphone_market", "global"]
    relation_keys: list[str]         # ["growth_trend", "quarterly"]
    source_type: SourceType          # MARKET_REPORT | GOVERNMENT_DATA | NEWS | ACADEMIC | SOCIAL | API_DATA
    source_provider: str             # "fred" | "tavily" | "finnhub" etc.
    source_title: str                # The article/report title
    source_url: str                  # Original URL
    retrieved_at: str                # ISO 8601 timestamp
    confidence: float                # 0.0 to 1.0
    cross_validated: bool            # True if confirmed by 2+ sources
    cross_validation_sources: list[str]  # Other providers that confirm this
    conflicting_claims: list[str]    # FactPacket IDs that contradict this
    citation_label: str              # "[M1]", "[F3]", "[N2]"
    slide_targets: list[str]         # ["market", "traction", "competition"]
    mode_safe_summary: str           # Safe for both modes: "Market expanded in latest quarter"
    extraction_method: str           # "api_structured" | "llm_extracted" | "regex_parsed"
    raw_snippet: Optional[str]       # Original text from which claim was extracted
    provider_request_id: Optional[str]  # For debugging and audit trail
```

### 8.2 `ClaimType` and `FreshnessClass` Enums

```python
class ClaimType(str, Enum):
    NUMERIC = "numeric"              # $1.2B, 7.8%, 500K users
    QUALITATIVE = "qualitative"      # "market is shifting toward AI"
    TREND = "trend"                  # "growing at 15% CAGR"
    QUOTE = "quote"                  # Direct attribution
    STATISTIC = "statistic"          # Survey/study result
    COMPARATIVE = "comparative"      # "3x faster than competitor"
    FORECAST = "forecast"            # Future projection
    REGULATORY = "regulatory"        # Legal/regulatory fact

class FreshnessClass(str, Enum):
    REAL_TIME = "real_time"          # < 1 hour old (API feeds)
    CURRENT = "current"             # < 30 days old
    RECENT = "recent"               # < 6 months old
    HISTORICAL = "historical"       # > 6 months old
    UNDATED = "undated"             # No date available

class SourceType(str, Enum):
    GOVERNMENT_DATA = "government_data"  # World Bank, FRED, Census
    MARKET_REPORT = "market_report"      # Industry reports
    FINANCIAL_DATA = "financial_data"    # Finnhub, Polygon, FMP
    NEWS = "news"                        # Guardian, NewsData
    ACADEMIC = "academic"                # CORE papers
    SOCIAL = "social"                    # Reddit, GitHub, YouTube
    COMPANY_PUBLIC = "company_public"    # Company websites, press releases
    API_STRUCTURED = "api_structured"    # Direct API data (no LLM extraction)
    WEB_EXTRACTED = "web_extracted"      # LLM-extracted from web pages
```

### 8.3 `SlideEvidenceBundle`

Each slide receives a structured evidence packet assembled from the evidence graph.

```python
@dataclass
class SlideEvidenceBundle:
    slide_id: str                    # "slide_market_01"
    slide_kind: SlideKind            # PROBLEM | SOLUTION | MARKET | COMPETITION | GTM | TRACTION | FINANCIAL | ASK | TEAM | TITLE | WHY_NOW | PRODUCT
    audience: str                    # "investor" | "board" | "team" | "general"
    research_priority: Priority      # HERO | STANDARD | MINIMAL
    goal: str                        # "prove market size, urgency, and category timing"
    evidence_requirements: list[str] # ["TAM_numeric", "growth_rate", "date_stamped_source"]
    approved_claims: list[FactPacket]       # Passed debate + citation guard
    supporting_claims: list[FactPacket]     # Supporting but not primary
    counterpoints: list[FactPacket]         # Opposing evidence (for balance/credibility)
    open_risks: list[str]                   # Risk factors identified during debate
    missing_data: list[MissingDataItem]     # What could not be found + suggestions
    community_summaries: list[str]          # Deck-global themes relevant to this slide
    debate_outcome: Optional[DebateOutcome] # Result of pitch debate loop
    source_mix: SourceMix                   # Categorized sources
    evidence_score: float            # 0.0 to 1.0 overall evidence quality
    freshness_score: float           # 0.0 to 1.0 how current the evidence is
    cross_validation_score: float    # 0.0 to 1.0 how well-corroborated

@dataclass
class MissingDataItem:
    what: str                        # "TAM figure for AI supply chain market"
    why_needed: str                  # "Investors expect specific market size"
    suggested_sources: list[str]     # ["Gartner report", "Grand View Research"]
    user_action: str                 # "Provide your own TAM estimate with source"
    severity: str                    # "critical" | "important" | "nice_to_have"

@dataclass
class SourceMix:
    deterministic: list[FactPacket]  # APIs with structured data (FRED, Census, Polygon)
    web: list[FactPacket]            # Web search results
    news: list[FactPacket]           # News articles
    financial: list[FactPacket]      # Financial data providers
    academic: list[FactPacket]       # Academic papers
    social: list[FactPacket]         # Social signals
    specialty: list[FactPacket]      # API Ninjas, NASA, CoinDesk, etc.
```

### 8.4 `SlideContentContract`

The final output object ALWAYS includes both modes, speaker notes, chart data, image prompt, and evidence metadata.

```python
@dataclass
class SlideContentContract:
    slide_id: str
    slide_kind: SlideKind
    presentation_mode: PresentationContent
    reading_mode: ReadingContent
    speaker_notes: list[str]
    chart_data: Optional[ChartData]
    image_prompt: Optional[str]      # For Azure Flux generation
    image_url: Optional[str]         # If image already generated
    citations: list[Citation]
    claim_status: ClaimStatus        # VERIFIED | PARTIAL | INSUFFICIENT | DEBATE_REJECTED
    confidence_score: float          # 0.0 to 1.0
    style_profile: str               # "sequoia_narrative"
    missing_data: list[MissingDataItem]
    generation_metadata: GenerationMetadata

@dataclass
class PresentationContent:
    title: str                       # Max 8 words
    subtitle: Optional[str]          # Max 12 words
    bullets: list[str]               # Max 5, each max 15 words
    visual_direction: str            # "market_map" | "growth_chart" | "comparison_grid"
    data_callout: Optional[str]      # Single headline number: "$4.2B"
    annotation: Optional[str]        # Chart/image annotation

@dataclass
class ReadingContent:
    title: str                       # Can be longer, more descriptive
    summary: str                     # 2-3 sentence executive summary
    body_sections: list[BodySection] # Detailed analysis sections
    footnotes: list[str]             # Source references
    assumptions: list[str]           # Explicit assumptions made
    risks: list[str]                 # Risk factors noted

@dataclass
class BodySection:
    heading: str
    content: str
    source_refs: list[str]           # Citation labels like "[M1]", "[F3]"

@dataclass
class Citation:
    label: str                       # "[M1]"
    source_title: str
    source_url: str
    source_type: SourceType
    provider: str
    retrieved_at: str
    confidence: float

@dataclass
class GenerationMetadata:
    total_providers_queried: int
    total_fact_packets: int
    approved_claims: int
    rejected_claims: int
    debate_rounds: int
    research_duration_ms: int
    generation_duration_ms: int
    models_used: list[str]
    budget_mode: str                 # "lean" | "balanced" | "hero"
    cache_hits: int
    errors_recovered: int
```

### 8.5 `DebateOutcome`

```python
@dataclass
class DebateOutcome:
    approved_claims: list[str]       # FactPacket IDs
    rejected_claims: list[RejectedClaim]
    open_risks: list[str]
    narrative_direction: str         # "numbers_first" | "story_first" | "problem_first"
    required_citations: list[str]    # FactPacket IDs that MUST appear
    debate_rounds: int
    ceo_confidence: float            # CEO agent's confidence in the thesis
    cto_confidence: float            # CTO agent's confidence in feasibility
    finance_confidence: float        # Finance agent's confidence in numbers

@dataclass
class RejectedClaim:
    fact_packet_id: str
    reason: str                      # "Unverifiable growth rate claim"
    rejected_by: str                 # "cto_agent" | "finance_agent"
    alternative_suggestion: Optional[str]  # "Use revenue range instead of exact figure"
```

## 9. New MCP Micro-Agent Topology For `slide_content`

This does not replace the V7 8-agent system. It specializes the content intelligence lane inside it.

### 9.1 Required micro-agents (10 agents)

1. `IntentClassifierAgent`
   - classifies deck type, audience, sector, urgency, research depth
   - runs on HuggingFace local models (zero API cost)
   - output: structured intent object that drives all downstream routing
   - fallback: keyword-based heuristics if model unavailable

2. `ResearchChiefAgent`
   - plans sub-queries per slide based on evidence requirements
   - selects source classes (deterministic vs web vs news vs financial)
   - sets freshness policy per claim type
   - manages research budget allocation across slides
   - coordinates parallel evidence collection
   - model: Groq (fast, free)

3. `CEOStoryAgent`
   - maps the deck into founder vision, narrative tension, why-now, fundraising framing
   - proposes the strongest investable thesis from the evidence
   - specialization of the V7 CEO/Strategist lane
   - model: Kimi-K2-Thinking (deep reasoning)

4. `CTOTechnicalAgent`
   - challenges product feasibility, moat realism, technical defensibility, roadmap credibility
   - identifies inflated technical claims
   - specialization of the V7 Researcher/Analyst + Code Agent lane
   - model: DeepSeek-V3 (technical depth)

5. `MarketIntelAgent`
   - owns market, competition, trend, category, and news evidence
   - dispatches queries to: World Bank, FRED, Census, Tavily, Exa, Serper, Guardian, NewsData, World News
   - performs competitor landscape mapping with source attribution
   - model: Groq (orchestration) + Cloudflare (embedding/classification)

6. `FinancialEvidenceAgent`
   - owns pricing, financial assumptions, TAM/SAM/SOM support, traction metrics, unit economics
   - dispatches queries to: Finnhub, Polygon, FMP, EODHD, CoinDesk, Alpha Vantage, FRED
   - cross-validates numbers across multiple financial sources
   - model: Phi-4-reasoning (numerical accuracy)

7. `SocialProofAgent`
   - owns developer traction, community signals, product launch data, user sentiment
   - dispatches queries to: Reddit, GitHub, YouTube, ProductHunt, API Ninjas
   - computes social momentum scores
   - model: Cloudflare GLM (fast, free)

8. `NarrativeEditorAgent`
   - turns approved evidence into investor-grade copy with mode awareness
   - generates presentation mode (tight, impactful) AND reading mode (detailed, cited)
   - generates speaker notes with talking points
   - model: DeepSeek-V3 (narrative quality) or Mistral-medium (premium polish)

9. `StyleDirectorAgent`
   - applies the selected style family and slide-level voice rules
   - transforms tone, density, and formatting per style profile
   - model: Cloudflare Qwen (free, fast for style transforms)

10. `CitationGuardianAgent`
    - blocks unsupported numeric or strategic claims from shipping
    - cross-checks every `$`, `%`, and `CAGR` against FactPackets
    - runs consistency checks across the full deck
    - marks insufficient slides with structured missing_data
    - model: GPT-4o-mini (pattern matching, structured output)

### 9.2 Mandatory pitch-deck debate loop

Required for pitch/investor/fundraising/demo_day decks.

```text
[Phase 1: Evidence Assembly]
ResearchChiefAgent orchestrates parallel evidence collection
    → MarketIntelAgent produces market evidence
    → FinancialEvidenceAgent produces financial evidence
    → SocialProofAgent produces traction evidence
    → All evidence normalized into FactPackets

[Phase 2: Thesis Formation]
CEOStoryAgent proposes the strongest fundraising thesis
    → Synthesizes evidence into investable narrative
    → Proposes headline numbers and story arc
    → Output: initial_thesis + proposed_claims

[Phase 3: Technical Challenge]
CTOTechnicalAgent challenges:
    → Technical feasibility of claimed moat
    → Realism of product roadmap
    → Inflated technical claims
    → Output: technical_challenges + revised_claims

[Phase 4: Financial Challenge]
FinancialEvidenceAgent challenges:
    → Unsupported revenue projections
    → Missing unit economics
    → TAM/SAM/SOM methodology flaws
    → Output: financial_challenges + revised_numbers

[Phase 5: Resolution]
ResearchChiefAgent resolves with citations:
    → Maps each surviving claim to FactPacket(s)
    → Rejects claims without 2+ source corroboration
    → Flags open risks explicitly
    → Output: DebateOutcome

[Phase 6: Iteration (max 3 rounds)]
If CEO confidence < 0.7 OR CTO confidence < 0.6:
    → Return to Phase 2 with narrowed thesis
    → Each round uses cheaper models (Groq → Cloudflare)
```

### 9.3 Non-pitch deck flow (simplified)

For non-investor decks (educational, internal, sales):
- skip debate loop entirely
- ResearchChiefAgent → evidence collection → NarrativeEditorAgent → StyleDirectorAgent → CitationGuardianAgent
- lighter quality bar: qualitative claims allowed without numeric backing
- faster generation, lower cost

## 10. Research Router: Intent-Based Multi-Provider Routing

The current search chain is too linear. The replacement is an intent-based router that selects providers by evidence type and tracks provider health via circuit breakers.

### 10.1 Provider Health & Circuit Breaker System

```python
@dataclass
class ProviderHealth:
    provider: str
    status: ProviderStatus          # HEALTHY | DEGRADED | OPEN_CIRCUIT
    consecutive_failures: int
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    avg_latency_ms: float
    requests_today: int
    daily_limit: int
    monthly_used: int
    monthly_limit: int
    circuit_open_until: Optional[datetime]  # Auto-close after cooldown

class ProviderStatus(str, Enum):
    HEALTHY = "healthy"             # 0-2 consecutive failures
    DEGRADED = "degraded"           # 3-4 consecutive failures, slower but usable
    OPEN_CIRCUIT = "open_circuit"   # 5+ failures, skip this provider for cooldown_seconds
```

Circuit breaker rules:
- 3 consecutive failures → DEGRADED (move to end of chain, log warning)
- 5 consecutive failures → OPEN_CIRCUIT (skip for 300 seconds, log error)
- 1 success after OPEN_CIRCUIT → back to HEALTHY
- Health state stored in Redis with TTL
- Provider latency tracked as exponential moving average

### 10.2 Route by evidence type, not by provider order

#### A. Macro / economic / demographic / public data

Use FIRST (deterministic, structured, zero hallucination risk):
- World Bank API (no auth, no limit)
- FRED API (120/min)
- US Census (no strict limit)

Use for enrichment:
- Polygon.io (ticker context)
- FMP (company fundamentals)
- EODHD (historical data, EOD prices)

Why this order:
- These are government/public APIs that return structured JSON. No LLM extraction needed.
- Better for TAM/SAM/SOM slides than any web search.
- Zero hallucination risk because data comes directly from the source.

#### B. Company / sector / market news

Primary chain:
- Finnhub (60/min, market news + company profiles)
- Guardian Open Platform (500/day, reliable journalism)
- NewsData (200/day, international coverage)
- World News API (international markets, non-English)

Reserve (NOT production core):
- NewsAPI (100/day, 24hr delay, dev-oriented)

Why:
- Guardian and Finnhub are production-reliable with reasonable limits.
- NewsAPI has 24-hour delay making it unsuitable for "current" evidence.
- World News API extends coverage to international markets.

#### C. Startup / competitor / category discovery

Primary:
- Tavily (1000/month, semantic search)
- Exa.ai (1000/month, autoprompt semantic)
- Serper (3 keys, ~7500 total/month, Google results)

Fallback:
- SerpAPI (2 keys, 500 total/month)
- You.com (conversational search)
- Search API (generic fallback)

Why:
- Tavily and Exa are optimized for AI-driven research queries.
- Serper provides raw Google results when semantic search is too narrow.
- 3 Serper keys + 2 SerpAPI keys = significant free capacity.

#### D. Financial data and company fundamentals

Primary:
- Finnhub (60/min, free, fast)
- Polygon.io (company details, market cap)
- FMP (revenue, CEO, sector)
- CoinDesk (crypto-specific, for blockchain pitches)
- EODHD (historical, fundamentals, macro)

Reserve:
- Alpha Vantage (25/day, too low for core use)

Why:
- Finnhub is the highest-throughput free financial API.
- Alpha Vantage is too rate-limited for production core.
- CoinDesk specifically for crypto/web3 pitch decks.
- EODHD provides historical data that other providers lack.

#### E. Content extraction from URLs

Primary:
- Jina.ai Reader (100 RPM search, 20 RPM reader)
- Firecrawl scrape in markdown mode (500 credits)
- Firecrawl JSON extraction mode (for structured pages)

Fallback:
- ScrapeDo (proxy-based, anti-bot bypass)
- Firecrawl map → scrape (site discovery)

Last resort:
- Firecrawl agent (5 free daily, expensive)

Why:
- Jina is highest throughput for reading URLs.
- ScrapeDo fills the gap for sites that block Jina/Firecrawl.
- Firecrawl agent is reserved for truly complex JS-heavy sites.

#### F. Academic / deep-tech validation

Primary:
- CORE (academic papers, 5 single/10sec)
- GitHub (5000/hour auth, technical validation)
- Exa.ai (academic-oriented semantic search)

Why:
- CORE is the largest free academic search API.
- GitHub validates open-source claims and developer traction.

#### G. Social proof / developer traction / community

Primary:
- GitHub REST API (5000/hour, repo stats, contributor data)
- Reddit OAuth (60/min, community sentiment)
- ProductHunt API (product launch traction, upvotes)

Secondary:
- YouTube Data API (100 searches/day at 100 units each)

Why:
- GitHub is the most objective social proof for tech startups.
- ProductHunt proves product-market interest at launch.
- YouTube costs 100 quota units per search, use sparingly.

#### H. Specialty / domain-specific

- API Ninjas: facts, quotes, historical data for general enrichment
- NASA APOD: space/science imagery for deep-tech or science decks
- CoinDesk: crypto market data for blockchain/web3 decks
- AbuseIPDB: cybersecurity context for infosec decks (rare)

### 10.3 Query Rewriting Pipeline

Before any search API is called, queries go through a rewriting pipeline:

```text
Raw query: "AI in logistics"
    │
    ├── [Step 1] HuggingFace classifier: intent = "market_sizing"
    │
    ├── [Step 2] Groq rewrite (free):
    │   ├── "AI logistics market size 2025 2026 CAGR report"
    │   ├── "artificial intelligence supply chain predictive maintenance TAM"
    │   ├── "logistics automation startup funding rounds 2025"
    │   └── Output: 3 specialized sub-queries
    │
    ├── [Step 3] Provider routing:
    │   ├── Query 1 → World Bank + FRED (macro data)
    │   ├── Query 2 → Tavily + Exa (industry reports)
    │   └── Query 3 → Finnhub + Serper (startup funding news)
    │
    └── [Step 4] Results aggregation → FactPackets
```

This ensures each API receives the query format it handles best.

## 11. Provider Budget Rules With Real-Time Tracking

Only verified limits from public docs are used below. Unverified limits are treated conservatively.

### 11.1 Complete Provider Limit Table

| Provider | Verified Public Limit | Daily Budget | Monthly Budget | Cost Per Call | Recommended Role |
| --- | --- | --- | --- | --- | --- |
| World Bank | No auth required, no limit | Unlimited | Unlimited | $0 | Default macro/economic data backbone |
| FRED | 120/min | ~5000 | ~150,000 | $0 | Economic indicators backbone |
| US Census | No strict limit | Generous | Generous | $0 | Demographics, population data |
| Tavily | 1000 credits/month free | ~33/day | 1000 | $0 | Primary semantic web search |
| Exa.ai | ~1000 req/month free | ~33/day | 1000 | $0 | Semantic company/market discovery |
| Serper | ~2500/key/month × 3 keys | ~250/day total | ~7500 | $0 | Primary Google search (3-key round-robin) |
| SerpAPI | 250/key/month × 2 keys, 50/hour | ~16/day total | 500 | $0 | Reserve Google search |
| You.com | Varies | Conservative | Conservative | $0 | AI search fallback |
| Search API | Varies | Conservative | Conservative | $0 | Generic search reserve |
| Firecrawl | 500 one-time credits, 2 concurrent, agent 5/day | 50/day budget | 500 one-time | 2 credits/10 results | Structured extraction, JS sites |
| Jina.ai | Search 100 RPM, Reader 20 RPM | ~2000/day | ~60,000 | $0 | URL reading, reranking backbone |
| ScrapeDo | Varies | Conservative | Conservative | Varies | Anti-bot proxy scraping |
| Finnhub | 60/min free | ~3600/day | ~100,000 | $0 | Financial news + company data backbone |
| Guardian | 500/day, 1/sec | 500 | ~15,000 | $0 | Free news backbone |
| NewsData | 200 credits/day, 12hr delay | 200 | ~6,000 | $0 | Backup news |
| World News | Varies | Conservative | Conservative | Varies | International news |
| NewsAPI | 100/day, 24hr delay | 100 | ~3,000 | $0 | Dev/test only |
| Polygon.io | Varies | Conservative | Conservative | Varies | Ticker data, market cap |
| FMP | Varies | Conservative | Conservative | Varies | Company profiles |
| CoinDesk | Varies | Conservative | Conservative | $0 | Crypto data |
| EODHD | Varies | Conservative | Conservative | Varies | Historical financial data |
| Alpha Vantage | ~25/day free | 25 | ~750 | $0 | Occasional enrichment only |
| YouTube Data | 10,000 units/day, search=100 units | 100 searches | ~3,000 | $0 | Only when video proof needed |
| GitHub REST | 5000/hour authenticated | ~40,000/day | ~1,200,000 | $0 | OSS/repo/technical validation |
| Reddit | 60/min with OAuth | ~3600/day | ~100,000 | $0 | Community sentiment |
| ProductHunt | Varies | Conservative | Conservative | Varies | Product launch traction |
| CORE | 5 single/10sec | ~1800/day | ~54,000 | $0 | Academic papers |
| API Ninjas | Varies | Conservative | Conservative | Varies | Facts, quotes |
| NASA APOD | 1000/hour | ~1000 | ~30,000 | $0 | Science imagery |
| Groq | Rate-limited per key × 8 keys | High (8-key rotation) | Very High | $0 | Fast LLM formatting |
| Cloudflare Workers | ~1000/day free | ~1000 | ~30,000 | $0 | Embeddings, RAG, classification |
| HuggingFace Local | Device-limited | Unlimited | Unlimited | $0 | Intent classification, claim typing |

### 11.2 Real-Time Budget Tracking (Redis)

```python
# Redis key patterns for budget tracking
BUDGET_KEYS = {
    "provider:{name}:daily:{date}": "int",      # Requests today
    "provider:{name}:monthly:{month}": "int",    # Requests this month
    "provider:{name}:health": "json",            # ProviderHealth object
    "provider:{name}:latency": "float",          # EMA latency in ms
    "deck:{deck_id}:budget": "json",             # Per-deck budget tracker
}
```

Before every API call:
1. `INCR provider:{name}:daily:{date}` → check against daily limit
2. `INCR provider:{name}:monthly:{month}` → check against monthly limit
3. If over limit → skip provider, use next in chain
4. After success → update latency EMA, reset consecutive failures
5. After failure → increment consecutive failures, check circuit breaker

### 11.3 Budget modes

#### `lean` mode (default for all decks)

Cost target: $0 per deck
- deterministic APIs first (World Bank, FRED, Census)
- ONE semantic web search provider per claim cluster (Tavily OR Exa, not both)
- Jina Reader only (no Firecrawl)
- NO Firecrawl agent
- NO premium Azure reasoning for bulk slides
- LLM: Groq + Cloudflare only
- Max parallel research: 3
- Research depth: 1 iteration

#### `balanced` mode (for important decks)

Cost target: minimal subscription cost
- TWO web providers per claim cluster
- Firecrawl scrape allowed for top 3 URLs
- Azure reasoning (DeepSeek, Phi-4) for key narrative slides only
- LLM: Groq + one Azure call per slide maximum
- Max parallel research: 5
- Research depth: 2 iterations

#### `hero` mode (for investor-facing final polish)

Cost target: acceptable subscription cost
- ALL providers available based on evidence type
- Full debate loop with 3 rounds
- Premium reasoning (Kimi-K2-Thinking) on hero slides
- Premium narrative polish (Mistral-medium or DeepSeek-V3)
- Azure Flux image generation for hero slides
- LLM: full model chain
- Max parallel research: 10
- Research depth: 3 iterations

### 11.4 Unverified providers — conservative treatment

These providers exist in `.env.example` but lack verified public free-tier documentation:
- ScrapeDo, Search API, World News API, ProductHunt, CoinDesk, EODHD, API Ninjas, AbuseIPDB

Conservative rules:
- assume daily limit of 50 requests unless proven otherwise
- monitor via Redis counters
- alert when 80% of conservative limit reached
- never use as primary in a route chain
- track actual usage to calibrate limits over time

## 12. Comprehensive Failure Handling Strategy

This is a production system. Every failure mode must be explicitly handled.

### 12.1 Provider-Level Failure Handling

```python
class ProviderFailureHandler:
    """
    Handles failures at the individual provider level.
    """
    FAILURE_RESPONSES = {
        # HTTP errors
        401: "invalid_api_key",         # Key revoked or expired
        403: "forbidden",               # IP blocked or plan restriction
        429: "rate_limited",            # Too many requests
        500: "server_error",            # Provider internal error
        502: "bad_gateway",             # Provider infrastructure issue
        503: "service_unavailable",     # Provider temporarily down
        504: "timeout",                 # Provider too slow

        # Application errors
        "empty_results": "no_data",     # Valid response but empty
        "malformed_json": "parse_error", # Response not parseable
        "timeout": "request_timeout",    # Our timeout exceeded
        "connection_error": "unreachable", # DNS/network failure
    }
```

For each failure type:

| Failure | Action | Retry? | Log Level |
| --- | --- | --- | --- |
| 401 Invalid Key | Disable key, try next key (round-robin) | No | ERROR |
| 429 Rate Limited | Exponential backoff (1s, 2s, 4s), switch provider | Yes (1x) | WARNING |
| 500/502/503 | Circuit breaker increment, switch provider | No | WARNING |
| 504 Timeout | Record latency spike, switch provider | No | WARNING |
| Empty Results | Try query rewrite, then next provider | Yes (rewrite) | INFO |
| Parse Error | Log raw response, switch provider | No | ERROR |
| Connection Error | Circuit breaker increment, switch provider | No | ERROR |

### 12.2 Research-Level Failure Handling

When all providers in a route chain fail:

```text
Route chain exhausted for evidence type "market_sizing"
    │
    ├── [Action 1] Try adjacent evidence type
    │   └── "market_sizing" → fallback to "industry_news" route
    │
    ├── [Action 2] Try broader query
    │   └── "AI logistics TAM 2026" → "logistics technology market"
    │
    ├── [Action 3] Use cached evidence
    │   └── Redis cache with TTL, MongoDB for historical evidence
    │
    ├── [Action 4] Use ChromaDB vector similarity
    │   └── Find semantically similar evidence from previous deck runs
    │
    └── [Action 5] Mark as insufficient
        └── Emit MissingDataItem with user_action suggestions
```

### 12.3 LLM-Level Failure Handling

The existing `model_router.py` 3-deep fallback chain is extended:

```text
LLM Task: PITCH_DEBATE (Kimi-K2-Thinking)
    │
    ├── [Attempt 1] Kimi-K2-Thinking (2 retries with +0.1 temp)
    ├── [Attempt 2] Phi-4-reasoning (2 retries)
    ├── [Attempt 3] DeepSeek-V3 (2 retries)
    ├── [Attempt 4] GPT-4o-mini (simplified task, 2 retries)
    ├── [Attempt 5] Groq round-robin (8 keys, 2 retries each)
    ├── [Attempt 6] Cloudflare Qwen/GLM (2 retries)
    └── [Attempt 7] OpenRouter free tier (last resort)

Max total attempts before hard failure: 20+
```

### 12.4 Slide-Level Failure Handling

When a single slide's evidence or generation fails:

```python
@dataclass
class SlideFailureState:
    slide_id: str
    failure_type: SlideFailureType
    recovery_attempted: bool
    recovery_method: Optional[str]
    final_state: str                 # "recovered" | "degraded" | "blocked"
    user_message: str                # User-friendly explanation
    user_actions: list[str]          # What the user can do to fix it

class SlideFailureType(str, Enum):
    NO_EVIDENCE = "no_evidence"                # Research found nothing
    WEAK_EVIDENCE = "weak_evidence"            # Evidence exists but low confidence
    CONFLICTING_EVIDENCE = "conflicting"       # Sources disagree
    GENERATION_FAILED = "generation_failed"    # LLM could not produce valid JSON
    DEBATE_REJECTED = "debate_rejected"        # All claims rejected by debate loop
    CITATION_FAILED = "citation_failed"        # Claims could not be traced to sources
```

Recovery cascade:

1. **NO_EVIDENCE**: Broaden query → try adjacent topics → use deck-global summaries → mark insufficient with suggestions
2. **WEAK_EVIDENCE**: Lower confidence threshold for non-critical slides → add caveats in reading mode → present with explicit uncertainty
3. **CONFLICTING_EVIDENCE**: Present both sides → note the conflict → let the user choose → reading mode includes full analysis
4. **GENERATION_FAILED**: Retry with simpler prompt → try different model → use template-based fallback → never use generic placeholder
5. **DEBATE_REJECTED**: Re-research with narrower queries → weaken claim to qualitative → use "according to [source]" framing
6. **CITATION_FAILED**: Strip uncitable claims → regenerate from evidence bundle only → reading mode notes what was removed

### 12.5 Deck-Level Failure Handling

When multiple slides fail in a deck:

- If ≤ 2 slides fail: generate remaining slides normally, mark failed slides with recovery suggestions
- If 3-5 slides fail: warn user that evidence quality is low, offer to continue or abort
- If > 5 slides fail: abort generation, return structured diagnosis of all failures with actionable guidance
- Never return a partial deck silently. Always tell the user what is missing and why.

### 12.6 User-Facing Error Messages

Every failure produces a user-friendly message, not a stack trace.

```python
USER_MESSAGES = {
    "no_market_data": "We couldn't find verified market size data for this specific niche. Consider providing your own TAM estimate with a source reference.",
    "conflicting_numbers": "Two sources report different revenue figures. We've included both with citations so you can verify which is correct.",
    "api_unavailable": "Some research sources are temporarily unavailable. We've used cached data where possible and marked slides that need fresh evidence.",
    "debate_rejected": "Our investor review process flagged this claim as unverifiable. We've replaced it with a safer framing that uses 'according to' attribution.",
    "weak_traction": "We found limited public traction data. Consider adding your own metrics (users, revenue, growth rate) for a stronger pitch.",
}
```

## 13. Best RAG Strategy For `slide_content`

The correct answer is not "just vector RAG". The best fit for `server4` is a 6-layer hybrid model using ChromaDB, Redis, MongoDB, and the evidence graph.

### 13.1 Layer 1: Real-Time Deterministic Retrieval

APIs that return structured JSON (FRED, World Bank, Census, Polygon, FMP, Finnhub, EODHD):
- no LLM extraction needed
- directly converted to FactPackets with `extraction_method = "api_structured"`
- confidence = 0.95+ (data from authoritative source)
- cached in Redis with 30-minute TTL for financial data, 24-hour TTL for macro data

### 13.2 Layer 2: Structured Web Evidence Retrieval

Search + scrape results (Tavily, Exa, Serper, Jina, Firecrawl, ScrapeDo):
- LLM extraction required (Groq for speed)
- converted to FactPackets with `extraction_method = "llm_extracted"`
- confidence = 0.6-0.85 depending on source quality
- extracted claims cross-referenced against Layer 1 when possible

### 13.3 Layer 3: In-Session Evidence Graph

Per deck run, built dynamically:
- **Nodes**: entities (companies, markets, metrics, personas, products, technologies)
- **Edges**: supports, contradicts, compares_to, grew_from, depends_on, mentioned_by, acquired_by, competes_with
- **Each node stores**: source lineage, FactPacket IDs, claim types, confidence
- **Each edge stores**: relationship strength, source, directionality
- Built using Cloudflare Workers embeddings (free) + HuggingFace entity extraction (free)

### 13.4 Layer 4: ChromaDB Vector Index

Store all FactPackets and evidence chunks in ChromaDB:
- embedding: Cloudflare Workers AI or HuggingFace local
- metadata filters: `slide_kind`, `claim_type`, `source_type`, `freshness_class`
- semantic similarity search for slide-local evidence retrieval
- enables cross-deck evidence reuse (user's previous deck runs can inform new ones)

### 13.5 Layer 5: Slide-Local Retrieval (GraphRAG Local Search)

For each slide:
- map slide query to entity keys in the evidence graph
- pull relevant FactPackets, relationships, and source summaries
- rerank by: relevance to slide goal, freshness, source authority, confidence
- fit within context window budget (max tokens per slide)
- use Jina reranker when available

### 13.6 Layer 6: Deck-Global Summary Retrieval (GraphRAG Global Search)

For deck-wide coherence:
- cluster FactPackets into thematic communities (market urgency, competitive landscape, traction narrative, financial trajectory)
- generate community summaries using map-reduce (Groq for map, DeepSeek for reduce)
- inject relevant community summaries into every slide as narrative anchors
- ensures the problem slide and market slide tell a consistent story

### 13.7 Evidence Cross-Validation Engine

When multiple sources provide data for the same metric:

```python
class CrossValidation:
    """
    Cross-validates claims from multiple providers.
    """
    def validate(self, claims: list[FactPacket]) -> CrossValidationResult:
        # Group claims by entity + metric
        # Compare numeric values across providers
        # Flag conflicts > 20% divergence
        # Promote claims confirmed by 2+ sources
        # Return: confirmed, conflicting, unverified
```

Rules:
- If 2+ providers agree (within 10% for numeric): `cross_validated = True`, confidence boost +0.1
- If 2 providers disagree (> 20% for numeric): flag both, present both in reading mode, weighted average in presentation mode
- If single source only: `cross_validated = False`, label as "according to [source]"
- Government data always wins over web-extracted data in conflicts

### 13.8 Evidence Freshness Scoring

```python
def compute_freshness_score(fact_packet: FactPacket) -> float:
    if fact_packet.freshness_class == FreshnessClass.REAL_TIME:
        return 1.0
    if fact_packet.freshness_class == FreshnessClass.CURRENT:
        return 0.9
    if fact_packet.freshness_class == FreshnessClass.RECENT:
        return 0.7
    if fact_packet.freshness_class == FreshnessClass.HISTORICAL:
        return 0.4
    return 0.2  # UNDATED
```

Freshness matters most for:
- Market sizing slides (data > 1 year old is suspect)
- Traction slides (must be current)
- News/trend slides (must be within 30 days)

Freshness matters least for:
- Team slides (biographical data is stable)
- Technology slides (architectural facts change slowly)
- Academic validation (papers don't expire)

### 13.9 Grounding rule (absolute)

If a numeric or strategic claim does not map back to a `FactPacket` with `confidence >= 0.5`, it does not ship.

For pitch decks specifically:
- `$` amounts require `confidence >= 0.7`
- `%` growth rates require `confidence >= 0.7`
- `CAGR` claims require `confidence >= 0.8`
- Market size claims require `cross_validated = True` OR `source_type = GOVERNMENT_DATA`

## 14. Pitch Deck Slide Specialization

This plan is pitch-deck first. Each major slide type gets its own evidence requirements, quality bar, and failure mode.

### 14.1 Title slide

Evidence requirements: Minimal
- company name, tagline, founding year
- one-line category positioning
- no external research needed (from user input)

Quality bar: Low (user-provided content)
Research priority: MINIMAL
Failure mode: Use user input as-is

### 14.2 Problem slide

Evidence requirements:
- pain intensity: quantified impact on target persona
- affected persona: specific, not generic
- urgency or market shift: trend data from news or market APIs
- at least ONE current external source if a trend is claimed

Quality bar: HIGH
Research priority: STANDARD
Providers used: Tavily, Exa (problem discovery), Guardian/NewsData (trend validation), FRED (macro indicators)

Failure mode: If no external trend data found, present the problem qualitatively with user-provided context. Mark reading mode with "trend data pending verification."

### 14.3 Solution slide

Evidence requirements:
- what changes (from user input)
- why current alternatives fail (competitive intelligence)
- why this team can build it (from user input + GitHub/ProductHunt validation)

Quality bar: MEDIUM
Research priority: STANDARD
Providers used: Exa (competitor analysis), GitHub (technical validation), ProductHunt (existing solutions)

Failure mode: User-provided solution description is always valid. Competitive intelligence is "nice to have" enrichment.

### 14.4 Market slide

Evidence requirements:
- TAM/SAM/SOM logic with methodology (top-down + bottom-up)
- date-stamped evidence for every number
- source preference: government/public data → industry reports → web research
- cross-validation required for numbers > $1B

Quality bar: VERY HIGH (investors scrutinize this most)
Research priority: HERO
Providers used: World Bank, FRED, Census (macro), Tavily/Exa (industry reports), Finnhub (sector data), EODHD (historical context)

Failure mode: If TAM cannot be sourced, present bottom-up calculation methodology. Mark as "estimate — requires verification." NEVER invent a TAM figure.

### 14.5 Competition slide

Evidence requirements:
- real competitors, not strawmen (named companies with sources)
- competitive wedge with evidence
- moat or operational advantage
- funding/size data from financial APIs

Quality bar: HIGH
Research priority: STANDARD
Providers used: Exa (competitor discovery), Finnhub (competitor financials), GitHub (OSS competitors), ProductHunt (competing products), Serper (recent competitor news)

Failure mode: If few competitors found, note "emerging market with limited direct competition" with sources showing why.

### 14.6 GTM slide

Evidence requirements:
- acquisition path with specifics
- customer motion (inbound vs outbound vs PLG)
- pricing or monetization evidence
- comparable company GTM data when available

Quality bar: MEDIUM
Research priority: STANDARD
Providers used: Reddit (customer feedback), ProductHunt (launch strategy evidence), Exa (comparable company case studies)

Failure mode: GTM is mostly founder-defined. Enrichment from comparable companies is "nice to have."

### 14.7 Traction slide

Evidence requirements:
- timeframe for every metric
- metric definitions (ARR vs MRR, MAU vs DAU)
- source lineage for every externalized number
- growth trajectory (not just snapshots)

Quality bar: VERY HIGH
Research priority: HERO when external validation possible
Providers used: GitHub (open-source traction via stars/forks/contributors), ProductHunt (launch metrics), Reddit (community signals), financial APIs for revenue validation if public

Failure mode: Traction is primarily user-provided. The system validates format (has timeframe, has definition) rather than the numbers themselves. Mark "self-reported" explicitly.

### 14.8 Financial slide

Evidence requirements:
- assumptions listed explicitly
- ranges rather than false precision when evidence is weak
- comparable company metrics for benchmarking
- unit economics: CAC, LTV, LTV:CAC, payback period, gross margin

Quality bar: HIGH
Research priority: STANDARD
Providers used: Finnhub (comparable companies), FMP (industry benchmarks), EODHD (historical benchmarks), Alpha Vantage (sector performance for context)

Failure mode: Financial projections are inherently speculative. System provides benchmarks but does not validate founder projections. Reading mode includes explicit caveats: "These projections are founder-provided estimates."

### 14.9 Team slide

Evidence requirements: Minimal external research
- Names and roles from user input
- LinkedIn/GitHub validation when available
- Previous company exits/funding from financial APIs

Quality bar: LOW (mostly user-provided)
Research priority: MINIMAL
Providers used: GitHub (technical team validation), optional Exa (previous company mentions)

Failure mode: Use user input as-is. No external enrichment required.

### 14.10 Ask slide

Evidence requirements:
- use of funds allocation
- milestone logic (what the money buys)
- credible dependency chain
- comparable funding rounds for context

Quality bar: HIGH
Research priority: STANDARD
Providers used: Finnhub (comparable funding rounds), Exa (similar company raises)

Failure mode: Ask slide is founder-defined. System validates structure (has use-of-funds breakdown, has milestones) rather than the amounts.

### 14.11 Why Now slide

Evidence requirements:
- macro trend data (FRED, World Bank)
- regulatory changes (news APIs)
- technology inflection (academic + GitHub)
- market timing evidence

Quality bar: HIGH
Research priority: HERO
Providers used: FRED (macro indicators), Guardian/NewsData (regulatory news), CORE (academic trends), GitHub (technology adoption)

Failure mode: "Why now" requires strong external evidence. If missing, mark as "timing thesis pending external validation."

### 14.12 Product / Demo slide

Evidence requirements: Minimal external
- product description from user input
- competitive feature comparison when available
- technology stack validation from GitHub

Quality bar: LOW (user-provided)
Research priority: MINIMAL
Providers used: GitHub (technology validation), optional Exa (feature comparison)

Failure mode: Use user input.

## 15. Reading Mode vs Presentation Mode Contract

V7 already wants both modes. This plan formalizes a hard content contract with precise rules.

### 15.1 Presentation mode (The Deck)

Optimize for: stage readability, investor attention span, visual impact

Hard rules:
- title: max 8 words
- subtitle: max 12 words
- bullets: max 5 items, each max 15 words
- body text: max 60 words total
- numbers prioritized over exposition
- one hero data callout per slide (e.g., "$4.2B" or "3x faster")
- chart-ready annotations that work without reading mode context
- no footnotes or caveats inline (put in speaker notes)

Formatting:
- `$1.2B` not `$1,200,000,000`
- `7.8%` not `seven point eight percent`
- `2024-Q3` not `the third quarter of the year 2024`
- contrast framing: "Old Way → New Way"
- every bullet starts with action verb or metric

Speaker notes:
- generated by GPT-4o-mini (fast, cheap, good for structured output)
- 3-5 talking points per slide
- include the "why" behind each bullet
- include source attribution for quoted numbers
- include transition cue to next slide

### 15.2 Reading mode (The Memo)

Optimize for: due diligence review, email-forward to IC, detailed analysis

Rules:
- title: descriptive, can be a full sentence
- summary: 2-3 sentence executive overview
- body: unlimited length, multi-section
- include source-aware commentary with `[M1]`, `[F3]` citation labels
- include explicit assumptions section
- include risk factors section
- include data gaps and what would strengthen the claim
- footnotes with clickable source URLs

Formatting:
- full numbers with context: "$1.2 billion, representing 7.8% growth from Q2 2024 (source: FRED)"
- paragraph-style analysis, not just bullet expansion
- competitor analysis includes funding data, employee count, and founded year
- financial projections include comparable company benchmarks

### 15.3 Shared source of truth (absolute rule)

Both modes MUST be generated from the SAME approved `SlideEvidenceBundle`.

- Presentation mode cannot contain claims that reading mode does not support.
- Reading mode cannot introduce facts that presentation mode contradicts.
- Both modes use the same citation labels (`[M1]`, `[F3]`).
- Both modes reference the same FactPackets.
- If evidence is insufficient, BOTH modes reflect this (presentation says "data pending", reading explains why).

### 15.4 Mode generation order

1. Generate reading mode FIRST (DeepSeek-V3, deeper reasoning)
2. Generate presentation mode from reading mode + evidence bundle (Groq, fast compression)
3. Generate speaker notes from both modes (GPT-4o-mini)
4. Cross-check: verify no factual divergence between modes (CitationGuardianAgent)

This order ensures presentation mode is a faithful compression, not an independent fabrication.

## 16. 56-Style Expansion Plan

The current style system has 12 styles. This plan expands to 56+ declarative style profiles.

### 16.1 Style families (8 families, 56 styles)

#### Fundraise Core (8 styles)

| # | Style ID | Headline Mode | Sentence Density | Tone | Best For |
|---|---|---|---|---|---|
| 1 | `yc_crisp` | metric | sparse | cold_data | Demo Day, YC batch |
| 2 | `sequoia_narrative` | thesis | medium | confident_grounded | Series A, B |
| 3 | `benchmark_product_first` | product | medium | understated | Product-led |
| 4 | `a16z_thesis` | thesis | dense | bold_contrarian | Thesis-driven raises |
| 5 | `tiger_numbers_first` | metric | sparse | numbers_only | Growth-stage |
| 6 | `first_round_founder` | personal | medium | authentic_warm | Seed |
| 7 | `bessemer_cloud` | metric | medium | saas_precision | Cloud/SaaS |
| 8 | `accel_growth` | growth | medium | momentum | Growth equity |

#### Founder Story (8 styles)

| # | Style ID | Headline Mode | Tone | Best For |
|---|---|---|---|---|
| 9 | `visionary_manifesto` | vision | inspiring_bold | World-changing products |
| 10 | `scrappy_builder` | action | humble_determined | Bootstrapped |
| 11 | `contrarian_insight` | challenge | provocative | Counter-consensus |
| 12 | `mission_driven` | mission | purposeful | Impact, climate |
| 13 | `deeptech_founder` | technical | expert_confident | PhD, hard tech |
| 14 | `community_led` | community | inclusive | Open-source, social |
| 15 | `craft_obsessed` | detail | meticulous | Design, manufacturing |
| 16 | `operator_confessional` | honest | transparent | Second-time founders |

#### Investor Diligence (8 styles)

| # | Style ID | Tone | Best For |
|---|---|---|---|
| 17 | `board_memo` | formal_direct | Board updates |
| 18 | `analyst_brief` | analytical | Research reports |
| 19 | `ic_memo` | structured | IC decision docs |
| 20 | `diligence_pack` | comprehensive | DD processes |
| 21 | `unit_economics_hardline` | numbers_only | Metrics-focused |
| 22 | `market_map_brief` | landscape | Category mapping |
| 23 | `risk_adjusted_case` | cautious | Risk-aware investing |
| 24 | `portfolio_fit` | strategic | Portfolio construction |

#### Product / GTM (8 styles)

| # | Style ID | Tone | Best For |
|---|---|---|---|
| 25 | `b2b_enterprise` | professional | Enterprise sales |
| 26 | `plg_motion` | approachable | Product-led growth |
| 27 | `consumer_viral` | exciting | Consumer apps |
| 28 | `marketplace_liquidity` | balanced | Two-sided markets |
| 29 | `fintech_trust` | trustworthy | Financial products |
| 30 | `healthtech_clinical` | precise | Healthcare/biotech |
| 31 | `climate_impact` | urgent | Climate tech |
| 32 | `developer_tooling` | technical | DevTools |

#### Reading-Heavy (8 styles)

| # | Style ID | Tone | Best For |
|---|---|---|---|
| 33 | `research_memo` | academic_lite | Research distribution |
| 34 | `whitepaper_compact` | authoritative | Thought leadership |
| 35 | `deep_dive_appendix` | exhaustive | Reference docs |
| 36 | `technical_qna` | conversational | FAQ format |
| 37 | `evidence_journal` | forensic | Evidence-heavy analysis |
| 38 | `founder_update_letter` | personal | Monthly updates |
| 39 | `expert_briefing` | strategic | Advisory sessions |
| 40 | `casefile` | narrative | Case studies |

#### Presentation-Heavy (8 styles)

| # | Style ID | Tone | Best For |
|---|---|---|---|
| 41 | `keynote_minimal` | serene | Apple-style keynotes |
| 42 | `cinematic_reveal` | dramatic | Product launches |
| 43 | `editorial_magazine` | editorial | Design-forward |
| 44 | `data_wall` | dense_visual | Data-heavy presentations |
| 45 | `neo_corporate` | modern_clean | Enterprise pitches |
| 46 | `luxury_brand` | premium | Premium products |
| 47 | `brutalist_signal` | raw | Anti-design aesthetic |
| 48 | `demo_showcase` | energetic | Product demos |

#### Sector-Specific (8 styles)

| # | Style ID | Tone | Best For |
|---|---|---|---|
| 49 | `saas_metrics_first` | metrics | SaaS companies |
| 50 | `ai_infra_technical` | technical | AI infrastructure |
| 51 | `biotech_evidence` | scientific | Biotech/pharma |
| 52 | `defense_security` | classified | Defense tech |
| 53 | `retail_ops` | operational | Retail/commerce |
| 54 | `education_outcomes` | outcomes | EdTech |
| 55 | `mobility_logistics` | efficiency | Transport/logistics |
| 56 | `real_estate_workflow` | process | PropTech |

### 16.2 Style profile schema

Each style is a declarative JSON profile, not a hardcoded prompt.

```python
@dataclass
class StyleProfile:
    style_id: str                    # "sequoia_narrative"
    family: str                      # "fundraise_core"
    headline_mode: str               # "thesis" | "metric" | "product" | "vision" | "action"
    sentence_density: str            # "sparse" | "medium" | "dense"
    bullet_tempo: str                # "tight" | "flowing" | "numbered"
    tone: str                        # "confident_grounded" | "cold_data" | "warm_authentic"
    evidence_density: str            # "minimal" | "medium" | "heavy"
    preferred_slide_types: list[str] # Slide types this style excels at
    presentation_rules: dict         # Mode-specific rules
    reading_rules: dict              # Mode-specific rules
    fluff_tolerance: float           # 0.0 (zero fluff) to 0.5 (some allowed)
    number_format: str               # "compact" ($1.2B) | "full" ($1,200,000,000)
    citation_style: str              # "inline" [M1] | "footnote" | "hidden"
    visual_preference: str           # "chart_heavy" | "text_focused" | "image_driven"
    max_bullets_presentation: int    # Override default
    max_words_per_bullet: int        # Override default
```

### 16.3 Selection logic

Style selection cascade:
1. User explicitly selects a style → use it
2. User selects family (e.g., "fundraise_core") → auto-select best fit based on audience + stage
3. No selection → infer from deck type + audience + sector using IntentClassifierAgent

```python
def select_style(
    audience: str,
    deck_type: str,
    sector: Optional[str],
    stage: Optional[str],
    mode: str,
    brand_direction: Optional[str],
) -> StyleProfile:
    # 1. Filter styles by deck_type compatibility
    # 2. Filter by audience match
    # 3. Score by sector relevance
    # 4. Score by stage fit
    # 5. Return highest-scoring profile
```

Deck-level master style is chosen first.
Individual slide-level micro-style overrides are optional (e.g., a data_wall style just for the traction slide within a sequoia_narrative deck).

## 17. LLM Routing Plan Using ALL `server4` Models

Every model in the inventory is assigned to specific task types. No model is wasted.

### 17.1 New task types to add to `model_router.py`

```python
# Add to TaskType enum
DEEP_RESEARCH_PLAN = "deep_research_plan"      # Planning sub-queries, evidence requirements
FACT_SYNTHESIS_JSON = "fact_synthesis_json"      # Extracting FactPackets from raw text
PITCH_DEBATE = "pitch_debate"                   # CEO/CTO/Finance debate rounds
DUAL_MODE_REWRITE = "dual_mode_rewrite"         # Generating presentation + reading modes
STYLE_ADAPTATION = "style_adaptation"           # Applying style profiles to content
CITATION_GUARD = "citation_guard"               # Verifying claims against evidence
EVIDENCE_EXTRACTION = "evidence_extraction"     # Extracting structured claims from documents
QUERY_REWRITE = "query_rewrite"                 # Optimizing search queries
CROSS_VALIDATION = "cross_validation"           # Comparing claims across sources
SPEAKER_NOTES = "speaker_notes"                 # Generating speaker notes
IMAGE_PROMPT = "image_prompt"                   # Generating prompts for Azure Flux
INTENT_CLASSIFICATION = "intent_classification" # Classifying deck type, audience
ENTITY_EXTRACTION = "entity_extraction"         # Extracting entities for evidence graph
COMMUNITY_SUMMARY = "community_summary"         # Summarizing deck-global themes
```

### 17.2 Complete routing table

| Task Type | Primary | Fallback 1 | Fallback 2 | Fallback 3 | Notes |
| --- | --- | --- | --- | --- | --- |
| `DEEP_RESEARCH_PLAN` | Kimi-K2-Thinking | Phi-4-reasoning | DeepSeek-V3 | Groq | Complex multi-step planning |
| `FACT_SYNTHESIS_JSON` | GPT-4o-mini | DeepSeek-V3 | Groq | CF-Qwen | Structured output critical |
| `PITCH_DEBATE` | Kimi-K2-Thinking | DeepSeek-V3 | Phi-4-reasoning | Groq | Deep reasoning required |
| `DUAL_MODE_REWRITE` | DeepSeek-V3 | Mistral-medium | GPT-4o-mini | Groq | Narrative quality matters |
| `STYLE_ADAPTATION` | CF-Qwen | CF-GLM | Groq | GPT-4o-mini | Free, fast, bulk |
| `CITATION_GUARD` | GPT-4o-mini | Groq | CF-Qwen | DeepSeek-V3 | Pattern matching |
| `EVIDENCE_EXTRACTION` | DeepSeek-V3 | GPT-4o-mini | Groq | CF-Qwen | Accuracy critical |
| `QUERY_REWRITE` | Groq | CF-Qwen | CF-GLM | GPT-4o-mini | Speed matters, free |
| `CROSS_VALIDATION` | Phi-4-reasoning | DeepSeek-V3 | GPT-4o-mini | Groq | Numerical reasoning |
| `SPEAKER_NOTES` | GPT-4o-mini | Groq | CF-Qwen | DeepSeek-V3 | Structured, fast |
| `IMAGE_PROMPT` | CF-Phoenix | CF-Lucid | Groq | GPT-4o-mini | Creative generation |
| `INTENT_CLASSIFICATION` | HuggingFace-local | CF-GLM | Groq | GPT-4o-mini | Zero-cost first |
| `ENTITY_EXTRACTION` | HuggingFace-local | CF-Qwen | Groq | DeepSeek-V3 | Zero-cost first |
| `COMMUNITY_SUMMARY` | DeepSeek-V3 | Groq | CF-Qwen | GPT-4o-mini | Quality summary |

### 17.3 HuggingFace Local Model Integration

Using the existing `HUGGINGFACE_API_TOKEN`, `USE_TINYLLAMA`, `USE_FLAN_T5`, `USE_PHI2` env vars:

```python
class LocalModelRouter:
    """
    Routes zero-cost tasks to local HuggingFace models.
    Falls back to Cloudflare Workers if local model unavailable.
    """
    TASK_MAP = {
        "intent_classification": {
            "model": "flan-t5",      # Fast, good at classification
            "fallback": "cf-glm",
        },
        "entity_extraction": {
            "model": "phi-2",        # Good at structured extraction
            "fallback": "cf-qwen",
        },
        "claim_typing": {
            "model": "flan-t5",      # Classify: numeric/qualitative/trend
            "fallback": "cf-glm",
        },
        "embedding": {
            "model": "all-MiniLM-L6-v2",  # Sentence embeddings for ChromaDB
            "fallback": "cf-workers-embedding",
        },
    }
```

### 17.4 Cost optimization rules

1. ALWAYS try HuggingFace local first for classification/embedding (cost: $0, latency: <100ms)
2. Use Cloudflare Workers for bulk transforms (cost: $0, latency: ~500ms)
3. Use Groq round-robin for formatting/query tasks (cost: $0, latency: ~300ms)
4. Use Azure models ONLY when quality demands it (debate, narrative, complex reasoning)
5. Track per-deck model usage: log which models were used, token counts, latencies
6. Budget mode determines which tier ceiling applies (lean → T4-T7 only, hero → all tiers)

## 18. Streaming Event Contract

Full event system for real-time frontend progress, using WebSocket + SSE.

### 18.1 Required events (30 events)

```python
class SlideContentEvent(str, Enum):
    # Research phase
    DECK_CONTEXT_READY = "deck_context_ready"           # User brief parsed
    INTENT_CLASSIFIED = "intent_classified"              # Deck type, audience identified
    RESEARCH_PLAN_READY = "research_plan_ready"          # Sub-queries planned
    SLIDE_RESEARCH_PLANNED = "slide_research_planned"    # Individual slide research plan
    PROVIDER_SELECTED = "provider_selected"              # Which API will be called
    PROVIDER_SKIPPED = "provider_skipped"                # Circuit breaker or budget skip
    SOURCE_FETCHING = "source_fetching"                  # API call in progress
    SOURCE_FETCHED = "source_fetched"                    # API call completed
    SOURCE_FAILED = "source_failed"                      # API call failed (with recovery action)
    QUERY_REWRITTEN = "query_rewritten"                  # Query optimized for next attempt

    # Evidence phase
    FACT_PACKET_CREATED = "fact_packet_created"           # New evidence normalized
    FACT_PACKET_REJECTED = "fact_packet_rejected"         # Evidence below quality bar
    CROSS_VALIDATION_RESULT = "cross_validation_result"   # Multi-source comparison
    EVIDENCE_GRAPH_UPDATED = "evidence_graph_updated"     # Graph node/edge added
    COMMUNITY_SUMMARY_READY = "community_summary_ready"   # Global theme identified
    EVIDENCE_BUNDLE_READY = "evidence_bundle_ready"       # Slide evidence assembled

    # Debate phase (pitch decks)
    CEO_THESIS_READY = "ceo_thesis_ready"               # CEO proposed thesis
    CTO_CHALLENGE_READY = "cto_challenge_ready"          # CTO challenged claims
    FINANCE_CHALLENGE_READY = "finance_challenge_ready"   # Finance challenged numbers
    DEBATE_ROUND_COMPLETE = "debate_round_complete"       # One debate round finished
    DEBATE_RESOLVED = "debate_resolved"                   # Final approved claims

    # Generation phase
    SLIDE_BRIEF_READY = "slide_brief_ready"              # Evidence → slide brief
    PRESENTATION_COPY_READY = "presentation_copy_ready"  # Presentation mode generated
    READING_COPY_READY = "reading_copy_ready"            # Reading mode generated
    SPEAKER_NOTES_READY = "speaker_notes_ready"          # Notes generated
    CHART_DATA_READY = "chart_data_ready"                # Chart synthesized
    IMAGE_PROMPT_READY = "image_prompt_ready"            # Image prompt generated
    CITATIONS_VERIFIED = "citations_verified"             # All claims checked

    # Final
    SLIDE_CONTENT_READY = "slide_content_ready"          # Final JSON for one slide
    SLIDE_CONTENT_BLOCKED = "slide_content_blocked"       # Slide failed quality bar
    DECK_CONTENT_COMPLETE = "deck_content_complete"       # All slides done
```

### 18.2 Event payload schema

```python
@dataclass
class ContentEvent:
    event: SlideContentEvent
    slide_id: Optional[str]
    timestamp: str                   # ISO 8601
    data: dict                       # Event-specific payload
    progress: float                  # 0.0 to 1.0 overall progress
    stage: str                       # "research" | "evidence" | "debate" | "generation" | "verification"
    message: str                     # User-friendly progress message

# Example payloads:
# fact_packet_created:
{
    "event": "fact_packet_created",
    "slide_id": "slide_market_01",
    "timestamp": "2026-04-04T10:30:05Z",
    "data": {
        "provider": "world_bank",
        "claim_type": "numeric",
        "claim": "Global GDP grew 3.1% in 2025",
        "citation_label": "[WB1]",
        "confidence": 0.96,
        "cross_validated": False
    },
    "progress": 0.35,
    "stage": "evidence",
    "message": "Found GDP growth data from World Bank"
}

# source_failed:
{
    "event": "source_failed",
    "slide_id": "slide_market_01",
    "timestamp": "2026-04-04T10:30:08Z",
    "data": {
        "provider": "alpha_vantage",
        "error": "rate_limited",
        "recovery": "switching to Finnhub",
        "circuit_breaker": "degraded"
    },
    "progress": 0.36,
    "stage": "research",
    "message": "Alpha Vantage rate limited, switching to Finnhub"
}
```

### 18.3 WebSocket + Celery Integration

```text
Frontend (React)
    │
    ├── WebSocket connection to /ws/deck/{deck_id}/content
    │
    ├── Receives: ContentEvent stream
    │
    └── React Flow: renders research graph in real-time
        ├── Node: data source → color by status (green=fetched, yellow=fetching, red=failed)
        ├── Node: agent → shows debate progress
        ├── Edge: evidence flow between nodes
        └── Progress bar: overall deck completion

Backend (FastAPI)
    │
    ├── POST /api/v1/deck/{deck_id}/generate-content
    │   └── Creates Celery task
    │   └── Returns: task_id
    │
    ├── Celery Worker
    │   ├── Executes full pipeline (stages 0-11)
    │   ├── Publishes ContentEvents to Redis pub/sub
    │   └── Stores results in MongoDB
    │
    └── WebSocket Handler
        ├── Subscribes to Redis pub/sub for deck_id
        ├── Forwards ContentEvents to connected frontend
        └── Handles reconnection gracefully
```

## 19. Background Processing via Celery

Heavy research and generation should NOT block the HTTP request.

### 19.1 Celery task architecture

```python
# Task: Deep research for a full deck
@celery_app.task(
    bind=True,
    max_retries=2,
    time_limit=600,           # From CELERY_TASK_TIME_LIMIT
    soft_time_limit=540,      # Warn 60s before hard limit
)
def generate_deck_content(
    self,
    deck_id: str,
    outline: dict,
    budget_mode: str = "lean",
    style: str = "yc_crisp",
) -> dict:
    """
    Full pipeline: research → evidence → debate → generate → verify
    Publishes progress events via Redis pub/sub.
    """

# Task: Research for a single slide (can be retried independently)
@celery_app.task(bind=True, max_retries=3, time_limit=120)
def research_slide(
    self,
    slide_id: str,
    slide_kind: str,
    queries: list[str],
    budget_mode: str,
) -> dict:
    """
    Executes research for one slide.
    Returns: list[FactPacket]
    """

# Task: Pre-warm evidence cache for common topics
@celery_app.task(bind=True, time_limit=300)
def prewarm_evidence_cache(
    self,
    topic: str,
    sector: str,
) -> dict:
    """
    Background task that pre-fetches common macro data.
    Runs periodically or on-demand.
    """
```

### 19.2 Concurrency model

- `CELERY_WORKER_CONCURRENCY = 4` (from .env)
- Each deck gets ONE orchestrator task
- Orchestrator spawns up to 5 parallel `research_slide` subtasks (matching `MAX_PARALLEL_SLIDES`)
- Each subtask has its own circuit breaker state
- Results aggregated by orchestrator before debate phase

### 19.3 MongoDB persistence

```python
# Collection: deck_runs
{
    "_id": ObjectId(),
    "deck_id": "uuid",
    "user_id": "uuid",
    "started_at": "ISO 8601",
    "completed_at": "ISO 8601",
    "status": "running" | "completed" | "failed" | "partial",
    "budget_mode": "lean" | "balanced" | "hero",
    "style": "yc_crisp",
    "outline": {},
    "evidence_graph": {},           # Serialized graph
    "fact_packets": [],             # All FactPackets
    "slide_bundles": [],            # All SlideEvidenceBundles
    "debate_outcomes": [],          # All DebateOutcomes
    "slide_contracts": [],          # All SlideContentContracts
    "generation_metadata": {},      # Timing, models, costs
    "errors": [],                   # All errors and recovery actions
}
```

This enables:
- resume interrupted deck generation
- cross-deck evidence reuse
- user can come back later and see detailed research provenance
- analytics on provider reliability and cost

## 20. Exact File-Level Implementation Plan

Every new file and every modification is listed explicitly. Nothing is left ambiguous.

### 20.1 New files to create

```text
app/mcp/brain_mcp/research/
├── __init__.py
├── models.py                      # FactPacket, SlideEvidenceBundle, SlideContentContract, all enums and dataclasses
├── provider_registry.py           # Provider inventory, health tracking, budget counters
├── circuit_breaker.py             # Circuit breaker state machine with Redis persistence
├── research_router.py             # Intent-based routing engine, provider chain builder
├── query_planner.py               # Sub-query generation, query rewriting pipeline
├── fact_packets.py                # FactPacket creation, normalization, confidence scoring
├── evidence_graph.py              # Entity-relation graph with source lineage
├── cross_validator.py             # Multi-source claim verification engine
├── community_summarizer.py        # Deck-global theme extraction (map-reduce)
├── evidence_assembler.py          # SlideEvidenceBundle construction from graph
├── debate_loop.py                 # CEO/CTO/Finance pitch debate manager
├── citation_guard.py              # Claim verification firewall
├── freshness_scorer.py            # Evidence age and relevance scoring
├── missing_data_reporter.py       # User-friendly missing data suggestions
└── content_events.py              # ContentEvent emitter for WebSocket/SSE

app/mcp/brain_mcp/generators/
├── slide_generator_v2.py          # New structured content generator (accepts SlideEvidenceBundle)
├── dual_mode_writer.py            # Presentation + reading mode parallel writer
├── chart_data_synthesizer.py      # Chart generation from FactPackets (no hallucination)
└── image_prompt_generator.py      # Azure Flux prompt generation

app/mcp/brain_mcp/prompts/
├── style_catalog.py               # 56 declarative style profiles
├── mode_transformers.py           # Presentation ↔ reading mode conversion rules
├── debate_prompts.py              # CEO, CTO, Finance debate prompt templates
└── evidence_extraction_prompts.py # Prompts for extracting FactPackets from raw text

app/mcp/brain_mcp/engines/
├── crypto_engine.py               # CoinDesk + EODHD integration
├── specialty_engine.py            # API Ninjas, NASA APOD, specialty data
├── producthunt_engine.py          # ProductHunt API integration
└── world_news_engine.py           # World News API integration

app/services/
├── evidence_store.py              # MongoDB persistence for deck runs, evidence, claims
├── chromadb_evidence.py           # ChromaDB integration for evidence vector search
└── local_model_router.py          # HuggingFace local model management

app/tasks/
├── __init__.py
├── research_tasks.py              # Celery tasks for background research
├── generation_tasks.py            # Celery tasks for content generation
└── cache_tasks.py                 # Celery tasks for cache warming

app/api/routes/
└── content_generation.py          # New API endpoints for V2 content generation

app/api/websockets/
└── content_progress.py            # WebSocket handler for real-time progress
```

### 20.2 Files to modify (extend, not break)

```text
app/config.py
    ADD: CoinDesk, EODHD, ScrapeDo, World News API, API Ninjas, NASA APOD config fields
    ADD: Budget mode configuration
    ADD: Circuit breaker settings
    KEEP: All existing fields unchanged

app/services/llm/model_router.py
    ADD: 14 new TaskType entries (Section 17.1)
    ADD: Corresponding routing chains (Section 17.2)
    ADD: HuggingFace local model fallback integration
    KEEP: All existing task types and routing chains

app/mcp/brain_mcp/config.py
    ADD: Circuit breaker thresholds
    ADD: Budget mode limits
    ADD: New provider rate limits
    ADD: Evidence quality thresholds
    KEEP: existing constants

app/mcp/tool_registry.py
    ADD: plan-slide-research
    ADD: run-slide-research
    ADD: run-pitch-debate
    ADD: generate-slide-content-v2
    ADD: verify-slide-claims
    ADD: get-evidence-graph
    ADD: get-deck-run-status
    KEEP: All existing 40+ tools

app/mcp/brain_mcp/engines/search_engine.py
    ADD: ScrapeDo provider in fallback chain
    ADD: Search API provider in fallback chain
    ADD: Circuit breaker health check before each provider attempt
    ADD: Budget counter increment for each call
    KEEP: Existing Serper/Tavily/SerpAPI/Exa/You.com chain

app/mcp/brain_mcp/engines/scraper_engine.py
    ADD: ScrapeDo as third extraction option
    ADD: Firecrawl map mode
    ADD: Firecrawl JSON extraction mode
    ADD: Anti-bot strategy selection
    KEEP: Existing Firecrawl/Jina extraction

app/mcp/brain_mcp/engines/news_engine.py
    ADD: World News API integration
    ADD: Freshness scoring per article
    KEEP: Existing NewsAPI/NewsData/Guardian chain

app/mcp/brain_mcp/engines/market_engine.py
    ADD: EODHD integration for historical data
    ADD: CoinDesk integration for crypto data
    ADD: Cross-source verification
    KEEP: Existing FRED/Alpha Vantage/Finnhub chain

app/mcp/brain_mcp/engines/social_engine.py
    ADD: ProductHunt implementation (currently configured but not functional)
    ADD: Social momentum scoring
    KEEP: Existing Reddit/GitHub/YouTube

app/mcp/brain_mcp/generators/slide_generator.py
    KEEP: Unchanged as compatibility layer
    ADD: Deprecation warning when called directly

app/mcp/brain_mcp/prompts/style_system.py
    KEEP: Existing 12 styles
    ADD: Import and delegation to style_catalog.py for 56+ styles

app/mcp/brain_mcp/prompts/quality_guards.py
    ADD: Cross-slide consistency check
    ADD: Evidence-backed verification (against FactPackets)
    ADD: Investor readiness scoring
    KEEP: Existing fluff detection, claim checking, density checks

app/main.py
    ADD: Content generation router inclusion
    ADD: WebSocket handler registration
    ADD: Celery task imports
    KEEP: All existing routers and lifespan logic
```

### 20.3 Files to NOT touch

```text
app/mcp/brain_mcp/generators/outline_generator.py    # Outline schema unchanged
app/mcp/brain_mcp/generators/batch_generator.py       # Batch logic still valid
app/mcp/brain_mcp/prompts/investor_system.py          # Investor prompts unchanged
app/mcp/brain_mcp/prompts/domain_layers.py            # Pitch rules unchanged
app/mcp/brain_mcp/prompts/outline_system.py           # Outline prompts unchanged
app/mcp/brain_mcp/prompts/slide_system.py             # Layout schemas unchanged
app/mcp/brain_mcp/prompts/chart_system.py             # Chart prompts unchanged
app/mcp/brain_mcp/engines/academic_engine.py          # CORE integration unchanged
app/mcp/brain_mcp/engines/financial_engine.py         # Polygon/FMP/Census unchanged
app/mcp/brain_mcp/security/prompt_sanitizer.py        # Security unchanged
```

## 21. Rollout Phases (8 phases)

### Phase 1: Core Data Objects + Evidence Pipeline

**Goal**: Replace flat research context with structured FactPackets and SlideEvidenceBundles.

Deliverables:
- `research/models.py` — all dataclasses, enums, type definitions
- `research/fact_packets.py` — FactPacket creation, confidence scoring
- `research/evidence_assembler.py` — SlideEvidenceBundle construction
- `generators/slide_generator_v2.py` — accepts SlideEvidenceBundle, outputs SlideContentContract
- Unit tests for all data objects

Dependencies: None
Risk: Low (additive, no existing code changed)

### Phase 2: Provider Health + Circuit Breaker + Budget Tracking

**Goal**: Replace static provider chains with health-aware, budget-tracked routing.

Deliverables:
- `research/provider_registry.py` — all provider configs with limits
- `research/circuit_breaker.py` — Redis-backed circuit breaker
- `config.py` modifications — new provider configs
- `brain_mcp/config.py` modifications — circuit breaker thresholds
- Redis integration for health counters

Dependencies: Phase 1 (models)
Risk: Medium (modifies search_engine.py provider selection)

### Phase 3: Intent Router + Query Rewriting + New API Integrations

**Goal**: Replace linear fallback with intent-based evidence routing. Activate all unused APIs.

Deliverables:
- `research/research_router.py` — intent-based provider routing
- `research/query_planner.py` — query rewriting pipeline
- `engines/crypto_engine.py` — CoinDesk + EODHD
- `engines/specialty_engine.py` — API Ninjas, NASA APOD
- `engines/producthunt_engine.py` — ProductHunt activation
- `engines/world_news_engine.py` — World News API
- `engines/search_engine.py` mods — ScrapeDo, Search API, circuit breaker
- `engines/scraper_engine.py` mods — ScrapeDo, Firecrawl map/JSON modes

Dependencies: Phase 2 (circuit breaker, budget tracking)
Risk: Medium (new engine files, modified existing engines)

### Phase 4: Evidence Graph + ChromaDB + Cross-Validation

**Goal**: Build per-deck evidence graph with entity relationships and vector search.

Deliverables:
- `research/evidence_graph.py` — entity-relation graph
- `research/cross_validator.py` — multi-source verification
- `research/community_summarizer.py` — deck-global themes
- `research/freshness_scorer.py` — evidence age scoring
- `services/chromadb_evidence.py` — ChromaDB integration
- `services/local_model_router.py` — HuggingFace local models

Dependencies: Phase 1 (FactPackets), Phase 3 (multiple providers for cross-validation)
Risk: Medium (new infrastructure: ChromaDB, local models)

### Phase 5: Pitch Debate Loop + Agent Pipeline

**Goal**: CEO/CTO/Finance challenge process before writing investor slides.

Deliverables:
- `research/debate_loop.py` — debate manager
- `prompts/debate_prompts.py` — agent prompt templates
- `prompts/evidence_extraction_prompts.py` — extraction prompts
- `model_router.py` modifications — PITCH_DEBATE, CROSS_VALIDATION task types

Dependencies: Phase 1 (evidence bundles), Phase 4 (evidence graph)
Risk: Medium (complex multi-agent orchestration)

### Phase 6: 56 Styles + Dual-Mode Writing + Failure Handling

**Goal**: Style-rich, mode-aware content with comprehensive failure handling.

Deliverables:
- `prompts/style_catalog.py` — 56 declarative style profiles
- `prompts/mode_transformers.py` — mode conversion rules
- `generators/dual_mode_writer.py` — presentation + reading mode parallel writer
- `generators/chart_data_synthesizer.py` — chart from FactPackets
- `generators/image_prompt_generator.py` — Azure Flux prompts
- `research/missing_data_reporter.py` — user-friendly failure messages
- `quality_guards.py` modifications — evidence-backed verification

Dependencies: Phase 1 (SlideContentContract), Phase 5 (debate outcomes for approved claims)
Risk: Low (mostly new files, minimal modification of existing)

### Phase 7: Background Processing + Streaming + Persistence

**Goal**: Celery background tasks, WebSocket progress, MongoDB persistence.

Deliverables:
- `tasks/research_tasks.py` — Celery research tasks
- `tasks/generation_tasks.py` — Celery generation tasks
- `tasks/cache_tasks.py` — cache warming tasks
- `research/content_events.py` — event emitter
- `api/routes/content_generation.py` — new API endpoints
- `api/websockets/content_progress.py` — WebSocket handler
- `services/evidence_store.py` — MongoDB persistence
- `main.py` modifications — router + WebSocket registration

Dependencies: Phase 6 (full pipeline complete)
Risk: High (infrastructure: Celery, WebSocket, MongoDB collections)

### Phase 8: Optional Lightweight Browser + Advanced RAG

**Goal**: Cover hardest JS-heavy pages and advanced evidence retrieval.

Deliverables:
- Optional Lightpanda-inspired browser adapter
- Advanced ChromaDB queries with graph+vector hybrid
- Cross-deck evidence reuse
- Cache warming for common topics

Dependencies: Phase 7 (full system running)
Risk: Low (optional enhancement, no existing code changes)

## 22. Testing Matrix

### 22.1 Unit tests (per module)

| Module | Test Focus | Test Count |
| --- | --- | --- |
| `models.py` | FactPacket creation, serialization, enum values | 15 |
| `fact_packets.py` | Confidence scoring, claim typing, deduplication | 12 |
| `evidence_assembler.py` | Bundle construction, evidence fitting | 10 |
| `circuit_breaker.py` | State transitions, Redis persistence, cooldown | 8 |
| `research_router.py` | Intent routing, provider selection, budget checks | 15 |
| `query_planner.py` | Query rewriting, sub-query generation | 8 |
| `evidence_graph.py` | Node/edge operations, traversal | 10 |
| `cross_validator.py` | Conflict detection, confidence boost, resolution | 10 |
| `debate_loop.py` | Debate flow, round limits, output structure | 8 |
| `citation_guard.py` | Claim verification, blocking, insufficiency marking | 12 |
| `slide_generator_v2.py` | SlideContentContract output, both modes, chart | 15 |
| `style_catalog.py` | All 56 styles load, schema validation | 56 |

### 22.2 Functional tests

- Each numeric claim in a pitch deck must map to at least one citation
- Unsupported claims must be blocked, not rewritten as confident filler
- Presentation mode and reading mode must differ in density but not in factual content
- Market sizing slide must prefer deterministic public data when available
- Cross-validated claims must have `cross_validated = True`
- Conflicting claims must surface both sources with labels
- All 40+ API providers must have health checks and budget counters
- Circuit breaker must open after 5 consecutive failures and close after cooldown
- Generation metadata must track all models used, tokens, and latencies

### 22.3 Quality tests

- Pitch problem slide feels urgent, not generic
- Market slide includes date-stamped evidence
- Competition slide does not use fake competitor claims
- Traction slide does not contain unlabeled metrics
- Ask slide has use-of-funds breakdown
- Why Now slide has external trend evidence
- Speaker notes include transition cues and source attributions
- Style profiles produce measurably different output (NLP similarity < 0.6 between styles)

### 22.4 Cost tests

- Lean mode must NOT invoke Firecrawl agent
- Lean mode must NOT invoke premium Azure models for all slides
- Lean mode must use HuggingFace local models for classification
- Hero mode must produce higher evidence_score than lean mode
- Budget counters must accurately track per-provider usage
- Per-deck cost report must be accurate within 10%

### 22.5 Failure handling tests

- All providers down → graceful degradation with user message
- Single provider timeout → seamless failover within 2 seconds
- Circuit breaker opens → provider skipped for cooldown period
- LLM failure → 7-deep fallback chain exhausted before hard failure
- Slide research fails → structured MissingDataItem returned
- Debate rejects all claims → slide marked as insufficient with suggestions
- Celery task timeout → partial results saved, user notified
- WebSocket disconnect → events buffered, resumable on reconnect
- MongoDB connection fail → in-memory fallback for active deck run
- Redis connection fail → fallback to in-memory rate limiting

### 22.6 Regression tests

- Old slide generation API (`slide_generator.py`) remains callable
- All 40+ existing MCP tools pass existing tests
- V7 deck assembly still receives valid slide content JSON
- Existing 12 styles produce identical output to current version
- Existing outline_generator produces identical output
- No existing test file breaks

### 22.7 Integration tests

- Full deck generation: 10-slide pitch deck, lean mode, < 120 seconds
- Full deck generation: 10-slide pitch deck, hero mode, < 300 seconds
- Cross-deck evidence reuse: second deck on same topic reuses cached evidence
- WebSocket: frontend receives all 30 event types in correct order
- Celery: task recovery after worker restart
- MongoDB: deck run survives server restart

## 23. Caching Strategy (3-Layer)

### 23.1 Layer 1: Redis (hot cache)

| Cache Key | TTL | Purpose |
| --- | --- | --- |
| `research:{query_hash}:{provider}` | 30 min | Raw API responses |
| `fact_packet:{claim_hash}` | 60 min | Normalized FactPackets |
| `evidence_bundle:{slide_kind}:{topic_hash}` | 60 min | Assembled evidence bundles |
| `community_summary:{deck_topic_hash}` | 120 min | Deck-global summaries |
| `provider:{name}:health` | 5 min | Circuit breaker state |
| `provider:{name}:daily:{date}` | 24 hours | Daily usage counter |
| `provider:{name}:monthly:{month}` | 31 days | Monthly usage counter |

### 23.2 Layer 2: MongoDB (warm cache)

- Full deck run records (evidence, debate, contracts)
- Historical FactPackets with source lineage
- Cross-deck evidence library (user's past research)
- TTL: configurable, default 30 days

### 23.3 Layer 3: ChromaDB (semantic cache)

- Vectorized FactPackets for similarity search
- Enables "find evidence similar to X from any previous deck run"
- Useful for cross-deck evidence reuse
- No TTL (embeddings are permanent, metadata controls relevance)

### 23.4 Cache invalidation rules

- Financial data: 30 min (markets change fast)
- News data: 60 min (news has a shelf life)
- Macro data: 24 hours (GDP/unemployment change quarterly)
- Academic data: 7 days (papers don't expire)
- Social data: 60 min (sentiment is volatile)
- Company data: 6 hours (company facts change infrequently)

## 24. Security Considerations

### 24.1 API key security

- All keys from environment variables via `app/config.py` Pydantic Settings
- Keys NEVER logged, even in debug mode
- Keys NEVER sent to frontend via WebSocket
- Failed auth attempts logged with provider name only (not key value)

### 24.2 Input sanitization

- Existing `prompt_sanitizer.py` handles all user input before LLM calls
- Query parameters sanitized before API calls (no injection into URLs)
- MongoDB queries use parameterized queries (no injection)

### 24.3 Output sanitization

- External URLs from search results are validated before inclusion
- Source URLs checked against basic allowlist patterns
- Generated content passes through quality guards before delivery
- No user PII stored in evidence cache (only topic/claim data)

### 24.4 Rate limiting

- Per-user rate limits on content generation endpoints
- Per-deck rate limits to prevent abuse
- Redis-backed counters with atomic operations

## 25. Hard Rules (Updated and Expanded)

1. Do not let `slide_content` consume only flattened research text anymore.
2. Do not use NewsAPI developer mode as the core production news source.
3. Do not use Alpha Vantage as a default live financial backbone in free mode.
4. Do not use Firecrawl agent before `search → map → scrape` fails.
5. Do not invent numbers when evidence is partial. Use `MissingDataItem` instead.
6. Do not let presentation mode diverge factually from reading mode.
7. Do not ship pitch slides without the CEO/CTO/research challenge loop.
8. Do not call premium Azure models for bulk low-value transforms. Use Groq/Cloudflare.
9. Do not ignore provider health status. Always check circuit breaker before calling.
10. Do not skip budget tracking. Every API call increments the Redis counter.
11. Do not generate charts from hallucinated data. Charts must trace to FactPackets.
12. Do not return generic error messages. Every failure has a user-friendly explanation.
13. Do not block the HTTP request for deep research. Use Celery background tasks.
14. Do not leave APIs unused. Every key in `.env.example` has a defined role.
15. Do not trust single-source numbers in pitch decks. Cross-validate when possible.
16. Do not hold evidence in memory only. Persist to MongoDB for recoverability.
17. Do not skip freshness scoring. Stale data is worse than no data for market slides.
18. Do not use YouTube for every query. 100 units per search, 10,000 daily budget.
19. Do not mix debate outcomes with non-debate slides. Debate is pitch-deck only.
20. Do not forget generation metadata. Track every model, provider, token, and millisecond.

## 26. Recommended First Implementation Order

If this plan is implemented next, the optimal first order is:

1. `research/models.py` — FactPacket, SlideEvidenceBundle, SlideContentContract, all enums
2. `research/fact_packets.py` — FactPacket creation and confidence scoring
3. `research/provider_registry.py` — provider inventory with limits
4. `research/circuit_breaker.py` — Redis-backed circuit breaker
5. `research/research_router.py` — intent-based router
6. `research/query_planner.py` — query rewriting pipeline
7. `research/evidence_assembler.py` — bundle construction
8. `generators/slide_generator_v2.py` — new structured generator
9. `research/debate_loop.py` — pitch debate manager
10. `prompts/style_catalog.py` — 56 style profiles
11. `generators/dual_mode_writer.py` — presentation + reading mode
12. `research/citation_guard.py` — claim verification firewall
13. `research/content_events.py` — streaming event emitter
14. New engine files (crypto, specialty, producthunt, world_news)
15. `model_router.py` modifications — 14 new task types
16. Celery tasks + WebSocket handler + MongoDB persistence
17. API endpoints + integration tests

This order fixes the root problem first: evidence quality entering `slide_content`. Each step is independently testable and does not break existing functionality.

## 27. Final Outcome

If implemented correctly, the `server4` slide content system will move from:

**Before (current)**:
```text
prompt + flattened research string → generic slide JSON
```

**After (V2)**:
```text
intent classification (HuggingFace, $0)
    → planned research with query rewriting (Groq, $0)
    → intent-routed evidence collection across 40+ APIs
    → normalized FactPackets with confidence + cross-validation
    → in-session evidence graph with entity relationships
    → deck-global community summaries for coherent storytelling
    → CEO/CTO/Finance pitch debate (for investor decks)
    → approved claims → dual-mode writing (presentation + reading)
    → 56-style adaptation
    → citation-guarded slide content JSON
    → with full generation metadata, missing data reports, and streaming progress
```

Every API key in `.env.example` is utilized.
Every failure mode has explicit handling.
Every numeric claim has traceable provenance.
Every slide tells the user what it knows, what it does not know, and what they can do about it.

That is the correct `slide_content` architecture for the V7 premium plan, built for real-world production use.