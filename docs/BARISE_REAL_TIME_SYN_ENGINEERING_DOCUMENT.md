# Barise Real Time Syn Engineering Document

Status: Design only. No implementation is included in this document.

## 1. Purpose

This document turns the Real Time Syn plan into an implementation-ready engineering blueprint for Barise. It is mapped to the current codebase and is intended to be the reference document used before actual implementation begins.

Real Time Syn is not just a news fetcher. It is a live startup-intelligence stream inside the Barise community that continuously discovers, verifies, scores, stores, and publishes near-real-time intelligence for real users at production scale.

## 2. Scope

Real Time Syn must support:

- startup news
- technology news
- founder and leadership moves
- funding rounds
- VC activity
- investments
- startup profiles
- product launches
- partnerships
- acquisitions
- startup failures
- shutdowns
- pivots
- layoffs
- jobs and hiring activity
- accelerators and incubators
- grants
- policy and regulation
- cybersecurity items
- research-backed developments
- market signals
- regional ecosystem updates
-latest news 
# High‑value additions I’d strongly consider
IPOs and public listings – filings, pricing, debut performance, lock‑up expirations. This is a distinct, high‑signal event type that Crunchbase and others explicitly track. 
news.crunchbase
+1
Exits (non‑IPO) – SPACs, direct listings, secondary sales, tender offers, and partial exits; not just full acquisitions.
Legal, compliance, and governance – lawsuits, IP disputes, regulatory actions/enforcements, fraud/scandals, board/auditor changes.
ESG and responsibility – climate/sustainability commitments, diversity & inclusion updates, ethics controversies, impact frameworks.
Milestones and metrics – user/customer count thresholds, revenue/ARR milestones, major awards/rankings, usage spikes.
Events and community – conferences, demo days, hackathons, meetups, ecosystem programs.
Customer and partner signals – major customer wins/losses, logos going on/off the website, renewals of big contracts.
Infrastructure and ops signals – outages, security incidents, major tech stack changes, cloud/infra migrations, data breaches.
Talent and culture – executive churn beyond just “moves,” culture‑related news, remote/hybrid policy changes, employer brand signals.
Research and IP – patents (filed/granted), published research, open‑source contributions, technical whitepapers.
Optional / nice‑to‑have depending on scope
Macroeconomic and industry indicators – interest rates, public market comps, sector‑specific indices, investor sentiment surveys.
Content and buzz – viral moments, social sentiment spikes, media coverage spikes (e.g., “most mentioned startups this week”).
How this fits with what you already have
You already cover:

Startup news, tech news, founder/leadership moves, funding rounds, VC activity, investments, startup profiles, product launches, partnerships, acquisitions, failures/shutdowns/pivots, layoffs, jobs/hiring, accelerators/incubators, grants, policy/regulation, cybersecurity items, research‑backed developments, market signals, regional ecosystem updates, latest news.
The additions above mostly plug gaps around:

Capital markets events (IPOs, SPACs, secondary exits),
Legal/ESG/intangibles (litigation, fraud, climate, DEI),
Harder‑to‑observe but high‑signal operational and customer signals (outages, major wins/losses),
Community/buzz (events, rankings, sentiment),
IP and research specifics.

It must also:

- integrate into `FASTAPI_COMMUNITY`
- show as a dedicated WarRoom tab after `Trending` and before `My Posts`
- support thin storage with redirect links to the original source
- support weekly cleanup and short-lived retention
- support optional image generation using the existing Mistral configuration when no usable source image is present
- support heavy usage and large ingest volume

## 3. Current Codebase Mapping

### 3.1 Primary ownership

`FASTAPI_COMMUNITY` is the correct home for Real Time Syn because it already owns:

- posts and feed APIs
- Mongo/Cosmos integration
- notifications
- push notification settings and subscriptions
- Socket.IO realtime publishing
- background schedulers and Celery workers

### 3.2 Existing files that matter

| Current file | Existing responsibility | Real Time Syn role |
| --- | --- | --- |
| `FASTAPI_COMMUNITY/app/main.py` | app startup, scheduler startup, Socket.IO mount, router registration | register new routes, startup jobs, syn publisher wiring |
| `FASTAPI_COMMUNITY/app/api/main.py` | aggregates API routers | include `realtime_syn_routes` |
| `FASTAPI_COMMUNITY/app/core/socket_manager.py` | emits `new_post` to user/global/circle rooms | add `realtime_syn_item`, `realtime_syn_item_updated`, `realtime_syn_status` emit methods |
| `FASTAPI_COMMUNITY/app/db/mongo.py` | collection setup and indexes for posts, comments, bookmarks, notifications, cached news | add syn collections, TTL indexes, dedupe indexes, metrics collections |
| `FASTAPI_COMMUNITY/app/core/config.py` | env config, external API keys, Mistral config | add Real Time Syn feature flags, source toggles, MCP settings, API budgets |
| `FASTAPI_COMMUNITY/app/services/news_fetcher.py` | current small multi-source news fetcher | preserve as legacy source helper or refactor into one provider adapter |
| `FASTAPI_COMMUNITY/app/core/scheduler.py` | APScheduler jobs | schedule cleanup, lightweight hot-path sync if APS fits |
| `FASTAPI_COMMUNITY/app/core/celery.py` | Celery app and beat schedule | add heavy ingest and enrichment task queues |
| `FASTAPI_COMMUNITY/app/celery_tasks/` | background tasks by domain | add `realtime_syn_tasks.py` and related task modules |
| `FASTAPI_COMMUNITY/app/api/routes/community_routes.py` | `/api/posts`, bookmarks, stats, promotion-adjacent social feed logic | keep post system separate, allow selected syn items to promote into posts |
| `FASTAPI_COMMUNITY/app/api/routes/notification_routes.py` | notification feed and stats | optionally include syn notification counts |
| `FASTAPI_COMMUNITY/app/api/routes/push_routes.py` | web push settings and subscriptions | deliver urgent syn alerts |
| `lliveupdatedstreaming/src/components/Community/pages/WarRoom.tsx` | community tabs, feed cache, `/api/posts`, Socket.IO `new_post` handling | add `realtime_syn` tab, cache, endpoint fetch, socket listeners |
| `lliveupdatedstreaming/src/components/Community/components/community/PostCard.tsx` | standard community post card | keep for promoted syn items only |
| `lliveupdatedstreaming/src/components/Community/components/community/RecentPosts.tsx` | list rendering for post-like content | can inspire list behavior but should not be the canonical syn card |
| `lliveupdatedstreaming/src/components/Community/types/communityTypes.ts` | shared community types | add syn-specific types |
| `lliveupdatedstreaming/src/config/env.ts` | frontend API base URLs | no new base URL needed if syn stays in community backend |
| `Server1_FastApi/app/api/routes/progress_ws_routes.py` | progress WebSocket pattern with Redis pub/sub | optional deep research progress UX |
| `server3/app/routers/websocket.py` | chat WebSocket | reference only for reliability/presence patterns |

### 3.3 Existing realtime behavior we must preserve

- Community feed already uses Socket.IO from `FASTAPI_COMMUNITY`.
- `WarRoom.tsx` currently fetches `/api/posts` and listens for `new_post`.
- The new Real Time Syn stream must reuse this same realtime transport instead of introducing a separate user-facing transport layer.

## 4. Product Positioning

Real Time Syn should be treated as a distinct intelligence layer inside Barise with two modes:

- `Sync mode`: fast, thin, near-live intelligence cards
- `Research mode`: deeper MCP-assisted expansion of selected items into richer dossiers

It should not dump every discovered external item into the social `posts` collection. Instead:

- `realtime_syn_items` becomes the canonical intelligence layer
- `community_db.posts` remains the community discussion layer
- selected syn items can be promoted into posts when they cross a threshold or when a moderator/admin/user action explicitly promotes them

## 5. High-Level Architecture

### 5.1 Runtime layers

Real Time Syn should have these runtime layers:

1. discovery
2. fetch and render
3. extract and normalize
4. dedupe and verify
5. enrich and score
6. store thin canonical item
7. publish realtime event
8. optionally promote to post
9. clean up expired items

### 5.2 Hot path vs warm path vs deep path

This split is required for heavy usage.

- Hot path:
  - fast source discovery
  - fast fetch
  - thin extraction
  - dedupe
  - one-pass scoring
  - immediate publish
- Warm path:
  - second-source verification
  - market/TAM/VC enrichment
  - image fallback
  - ranking recalculation
- Deep path:
  - dossier generation
  - startup profile expansion
  - competitor mapping
  - founder research
  - market analysis report

Important rule:

- Deep MCP research must never block the live feed.

## 6. MCP Architecture

### 6.1 Primary MCP design

Create a Barise-owned orchestration layer named something like:

- `barise-realtime-syn-mcp`

This should not replace FastAPI. It should act as the agent and tool layer used by workers.

### 6.2 MCP tools required

The MCP layer should expose or orchestrate tools such as:

- `search_web`
- `search_news`
- `crawl_page`
- `render_dynamic_page`
- `extract_news_item`
- `extract_job_item`
- `extract_funding_item`
- `extract_startup_profile`
- `extract_competitor_signal`
- `extract_market_signal`
- `verify_with_second_source`
- `resolve_entities`
- `classify_channel`
- `score_item`
- `generate_image_if_needed`
- `publish_to_cosmos`
- `emit_realtime_event`

### 6.3 External MCPs to use

These MCPs should be part of the design:

- `deer-flow` for orchestration ideas and DAG-like flow design
- `hermes-agent` for scheduled and agentic execution patterns
- `web-search-mcp-server` or `duckduckgo-mcp` for search tool access
- `lightpanda/browser` as the browser-rendering layer for dynamic pages
- `deep-research` and `Deep_search_lightning` for long-form research workflows
- `TAM-MCP-Server` for market sizing and industry context
- `octagon-mcp-server` and `octagon-vc-agents` for funding and venture intelligence
- `stock-research-mcp` and `tradingview-mcp` for market context and public-company signals
- `adalyst-mcp` for competitor intelligence
- `reddit-research-mcp` for social and founder signal
- `arxiv-mcp-server` for research-backed tech signal
- `Dappier MCP` for realtime web and market data use cases

### 6.4 Where Lightpanda fits

Lightpanda should be used in the fetch/render layer, especially for:

- JavaScript-heavy startup websites
- careers pages
- dynamic press rooms
- portfolio pages
- investor sites
- pages where simple HTTP fetch misses useful content

Lightpanda should not be used for every item. It is a selective tool used when:

- normal API/RSS data is insufficient
- HTML content is incomplete without rendering
- the job page or company page is client-rendered

### 6.5 MCP usage policy

- Search MCPs are hot-path tools.
- Browser MCPs are selective hot/warm tools.
- Market and competitor MCPs are warm-path enrichment tools.
- Deep-research MCPs are deep-path tools.

This keeps the system fast enough for realtime usage while still supporting deeper intelligence.

## 7. Source Strategy

### 7.1 Source classes

Use sources in these classes:

- search and discovery
- official news APIs
- RSS and public source links
- finance and market APIs
- cybersecurity and specialty APIs
- direct public company pages

### 7.2 Hot-path sources

Use these for fast discovery:

- ActuallyRelevant
- Guardian Open Platform
- Tavily
- Exa
- DDG or SearXNG-style search MCP
- direct public page fetch
- Lightpanda-rendered page fetch when needed

### 7.3 Warm-path sources

Use these for enrichment and backfill:

- NewsData
- NewsAPI
- GNews
- MediaStack
- World News API
- TheNewsAPI
- Currents API if available and acceptable

### 7.4 Market and investment sources

Use these to enrich funding and market channels:

- Alpha Vantage
- Financial Modeling Prep
- EODHD
- Finnhub if current free limits are acceptable

### 7.5 Specialty sources

- NASA APOD for science and space-tech channel only
- AbuseIPDB for cybersecurity channel only

### 7.6 Source budget router

Do not call every provider every cycle.

Use a source-budget router that decides:

- source priority
- source cadence
- allowed daily budget
- fallback provider
- channel fit
- whether delayed sources are allowed for the requested freshness level

## 8. Storage Model

### 8.1 Canonical principle

Store thin intelligence cards, not full article bodies.

Each record should aim to be:

- link-first
- summary-first
- source-backed
- small enough for short retention

### 8.2 Thin-item record

Minimum useful fields for thin storage:

- `item_id`
- `item_type`
- `channel`
- `title`
- `short_summary`
- `canonical_url`
- `source_name`
- `source_domain`
- `published_at`
- `discovered_at`
- `startup_name`
- `tags`
- `entities`
- `freshness_score`
- `trust_score`
- `impact_score`
- `image_url`
- `image_origin`
- `promotion_status`
- `ttl_expires_at`

This lets the UI show headline, summary, badges, and redirect links while minimizing storage.

### 8.3 Retention and cleanup

Recommended default policy:

- retain thin items for 7 days
- run weekly cleanup
- keep promoted items longer
- keep engaged items longer
- preserve a linked stub if a deleted syn item is referenced by discussion or bookmarks

## 9. Mongo/Cosmos Collections And Schemas

### 9.1 New collections

Add the following collections in `FASTAPI_COMMUNITY/app/db/mongo.py`:

- `community_db.realtime_syn_items`
- `community_db.realtime_syn_entities`
- `community_db.realtime_syn_sources`
- `community_db.realtime_syn_runs`
- `community_db.realtime_syn_metrics`
- `community_db.realtime_syn_rendered_posts`
- `community_db.realtime_syn_dedupe`
- `community_db.realtime_syn_failures`
- `community_db.realtime_syn_user_state`

### 9.2 `realtime_syn_items` schema

Recommended document shape:

```json
{
  "_id": "ObjectId",
  "item_id": "syn_...",
  "item_type": "news|job|funding|startup_profile|market_signal|failure|policy|research",
  "channel": "startup_news|funding|jobs|layoffs|product_launches|startup_failures|vc_activity",
  "status": "new|verified|updated|promoted|archived|expired",
  "title": "string",
  "short_summary": "string",
  "long_summary": "string|null",
  "canonical_url": "string",
  "source_name": "string",
  "source_domain": "string",
  "source_type": "api|rss|search|browser|mcp",
  "source_tier": "hot|warm|deep",
  "published_at": "datetime",
  "discovered_at": "datetime",
  "last_verified_at": "datetime|null",
  "country": "string|null",
  "region": "string|null",
  "city": "string|null",
  "industry": "string|null",
  "sub_industry": "string|null",
  "startup_name": "string|null",
  "startup_slug": "string|null",
  "founders": ["string"],
  "company_stage": "string|null",
  "funding_round": "string|null",
  "funding_amount": "number|null",
  "currency": "string|null",
  "investors": ["string"],
  "valuation": "number|null",
  "job_title": "string|null",
  "job_type": "string|null",
  "salary_range": "string|null",
  "skills": ["string"],
  "remote_policy": "string|null",
  "tags": ["string"],
  "entities": ["string"],
  "sentiment": "positive|neutral|negative|null",
  "freshness_score": 0,
  "trust_score": 0,
  "impact_score": 0,
  "discussion_score": 0,
  "dedupe_key": "string",
  "duplicate_group_id": "string|null",
  "citation_links": ["string"],
  "evidence_snippets": ["string"],
  "image_url": "string|null",
  "image_origin": "source|generated|null",
  "rendered_post_id": "string|null",
  "promotion_status": "none|candidate|promoted|rejected",
  "engagement_stub": {
    "comments_count": 0,
    "bookmarks_count": 0,
    "clicks_count": 0
  },
  "raw_payload_ref": "string|null",
  "ttl_expires_at": "datetime",
  "version": 1
}
```

### 9.3 `realtime_syn_entities` schema

Purpose:

- company normalization
- founder normalization
- investor normalization
- alias resolution

Suggested fields:

- `entity_id`
- `entity_type`
- `canonical_name`
- `aliases`
- `domains`
- `social_links`
- `country`
- `industry`
- `last_seen_at`

### 9.4 `realtime_syn_sources` schema

Purpose:

- source health
- budget tracking
- rate-limit status
- provider quality

Suggested fields:

- `source_id`
- `name`
- `type`
- `is_enabled`
- `priority`
- `free_tier_budget`
- `remaining_budget_estimate`
- `last_success_at`
- `last_failure_at`
- `cooldown_until`
- `avg_latency_ms`
- `avg_quality_score`

### 9.5 `realtime_syn_runs` schema

Purpose:

- observability
- per-run metrics
- debugging

Suggested fields:

- `run_id`
- `job_type`
- `started_at`
- `finished_at`
- `status`
- `source_ids`
- `candidate_count`
- `stored_count`
- `published_count`
- `promoted_count`
- `error_count`

### 9.6 `realtime_syn_rendered_posts` schema

Purpose:

- map canonical syn items to community posts

Suggested fields:

- `item_id`
- `post_id`
- `promotion_reason`
- `promoted_at`
- `promoted_by`

### 9.7 Required indexes

Add indexes in `FASTAPI_COMMUNITY/app/db/mongo.py` for:

- `realtime_syn_items.item_id` unique
- `realtime_syn_items.dedupe_key`
- `realtime_syn_items.channel + discovered_at desc`
- `realtime_syn_items.channel + published_at desc`
- `realtime_syn_items.startup_name + discovered_at desc`
- `realtime_syn_items.promotion_status + discovered_at desc`
- `realtime_syn_items.ttl_expires_at` TTL
- `realtime_syn_sources.name` unique
- `realtime_syn_runs.started_at desc`
- `realtime_syn_rendered_posts.item_id`
- `realtime_syn_rendered_posts.post_id`

## 10. API Design

All syn APIs should live under the community API surface.

Recommended prefix:

- `/api/realtime-syn`

### 10.1 Public/feed endpoints

- `GET /api/realtime-syn`
  - list thin intelligence cards
  - supports cursor pagination
  - supports filters: `channel`, `item_type`, `startup_name`, `country`, `source_tier`, `min_trust`, `min_freshness`
- `GET /api/realtime-syn/channels`
  - list available channels and counts
- `GET /api/realtime-syn/{item_id}`
  - get a single syn item
- `GET /api/realtime-syn/trending`
  - optional if syn gets its own trend layer

### 10.2 Interaction endpoints

- `POST /api/realtime-syn/{item_id}/click`
  - record outbound click
- `POST /api/realtime-syn/{item_id}/bookmark`
  - optional syn-specific bookmark before promotion
- `POST /api/realtime-syn/{item_id}/promote`
  - admin/system/user-driven promotion to community post
- `POST /api/realtime-syn/{item_id}/dismiss`
  - hide or suppress noisy item
- `POST /api/realtime-syn/{item_id}/refresh`
  - request re-verification of a hot item

### 10.3 Admin/ops endpoints

- `GET /api/realtime-syn/metrics`
- `GET /api/realtime-syn/source-health`
- `GET /api/realtime-syn/runs`
- `POST /api/realtime-syn/admin/sync-now`
- `POST /api/realtime-syn/admin/rebuild-channel/{channel}`
- `POST /api/realtime-syn/admin/cleanup`

### 10.4 Pagination model

Use cursor-first pagination like the existing `GET /api/posts` behavior in `community_routes.py`.

Payload shape should mirror the existing feed pattern:

```json
{
  "items": [],
  "next_cursor": "2026-03-25T18:30:00+00:00",
  "has_more": true
}
```

## 11. Socket Event Design

Realtime publishing should stay in `FASTAPI_COMMUNITY/app/core/socket_manager.py`.

### 11.1 New Socket.IO events

- `realtime_syn_item`
- `realtime_syn_item_updated`
- `realtime_syn_status`
- `realtime_syn_digest_ready`

### 11.2 Event payloads

`realtime_syn_item`

```json
{
  "item_id": "syn_123",
  "channel": "funding",
  "title": "Startup X raises seed round",
  "short_summary": "Thin summary here",
  "canonical_url": "https://source.example/item",
  "source_name": "Source Name",
  "published_at": "2026-03-25T18:30:00Z",
  "freshness_score": 88,
  "trust_score": 91,
  "impact_score": 76,
  "image_url": "https://...",
  "image_origin": "source",
  "promotion_status": "none"
}
```

`realtime_syn_item_updated`

```json
{
  "item_id": "syn_123",
  "updated_fields": ["trust_score", "citation_links", "promotion_status"],
  "item": {}
}
```

`realtime_syn_status`

```json
{
  "channel": "jobs",
  "source_state": "healthy",
  "message": "Realtime sync active",
  "timestamp": "2026-03-25T18:30:00Z"
}
```

### 11.3 Rooms

Use room-based routing similar to the current feed:

- `global_syn`
- `channel_{channel}`
- `circle_{circle_id}`
- `user_{user_id}`

### 11.4 Socket manager responsibilities

Planned additions to `FASTAPI_COMMUNITY/app/core/socket_manager.py`:

- `broadcast_realtime_syn_item`
- `broadcast_realtime_syn_item_updated`
- `broadcast_realtime_syn_status`

## 12. Frontend Engineering Plan

### 12.1 Existing WarRoom behavior

Current WarRoom:

- uses `activeFilter`
- caches per filter
- calls `/api/posts`
- uses Socket.IO `new_post`
- has tab order `trending`, `recent`, `wins`, `engagement`

### 12.2 Required WarRoom change

The new order must be:

- `trending`
- `realtime_syn`
- `recent`
- `wins`
- `engagement`

This means `Real Time Syn` is displayed after `Trending` and before `My Posts`.

### 12.3 Existing frontend files to modify later

| Existing file | Planned change |
| --- | --- |
| `lliveupdatedstreaming/src/components/Community/pages/WarRoom.tsx` | add `realtime_syn` tab, cache bucket, endpoint fetch, socket listeners, queue banner |
| `lliveupdatedstreaming/src/components/Community/types/communityTypes.ts` | add syn types |
| `lliveupdatedstreaming/src/config/env.ts` | likely no API base URL change required |
| `lliveupdatedstreaming/src/components/Community/components/community/PostCard.tsx` | keep for promoted items only |
| `lliveupdatedstreaming/src/components/Community/components/community/RecentPosts.tsx` | not the main syn renderer, but can inspire list behavior |

### 12.4 New frontend files recommended

| Proposed file | Responsibility |
| --- | --- |
| `lliveupdatedstreaming/src/components/Community/components/community/RealtimeSynCard.tsx` | thin syn card renderer |
| `lliveupdatedstreaming/src/components/Community/components/community/RealtimeSynList.tsx` | list wrapper and empty/loading states |
| `lliveupdatedstreaming/src/components/Community/hooks/useRealtimeSyn.ts` | optional fetch/cache helper if WarRoom gets too large |

### 12.5 Frontend data model

Add a dedicated interface such as:

```ts
export interface RealtimeSynItem {
  item_id: string;
  item_type: string;
  channel: string;
  title: string;
  short_summary: string;
  canonical_url: string;
  source_name: string;
  published_at: string;
  freshness_score: number;
  trust_score: number;
  impact_score: number;
  image_url?: string;
  image_origin?: "source" | "generated";
  promotion_status: "none" | "candidate" | "promoted" | "rejected";
}
```

### 12.6 WarRoom behavior for syn tab

`realtime_syn` should have:

- its own cache bucket
- its own cursor
- its own socket queue
- its own "Show X New Syn Items" banner
- its own loader and empty state
- filter chips by channel if needed later

The `realtime_syn` tab should call:

- `GET /api/realtime-syn`

It should listen to:

- `realtime_syn_item`
- `realtime_syn_item_updated`

### 12.7 Card behavior

The syn card should be intentionally thinner than `PostCard`.

Minimum card elements:

- title
- short summary
- source badge
- published time
- channel badge
- trust/freshness/impact badges
- image if available
- `Read More` external link
- optional `Open discussion` if promoted

### 12.8 Promotion UX

When an item is promoted:

- keep showing it in the syn tab
- link to the created community post
- allow `PostCard` to render the promoted version in the post feed

## 13. Backend Module Plan

### 13.1 Existing files to modify later

| Existing file | Planned role |
| --- | --- |
| `FASTAPI_COMMUNITY/app/api/main.py` | include new syn router |
| `FASTAPI_COMMUNITY/app/main.py` | startup wiring for scheduler/tasks, route registration |
| `FASTAPI_COMMUNITY/app/core/socket_manager.py` | new syn broadcasts |
| `FASTAPI_COMMUNITY/app/core/config.py` | env flags, source configs, budgets |
| `FASTAPI_COMMUNITY/app/db/mongo.py` | new collections and indexes |
| `FASTAPI_COMMUNITY/app/core/celery.py` | add queues/beat jobs |
| `FASTAPI_COMMUNITY/app/core/scheduler.py` | add lightweight jobs and weekly cleanup trigger |
| `FASTAPI_COMMUNITY/app/services/news_fetcher.py` | convert to one provider adapter or keep as legacy helper |

### 13.2 New backend files recommended

| Proposed file | Responsibility |
| --- | --- |
| `FASTAPI_COMMUNITY/app/api/routes/realtime_syn_routes.py` | REST API surface |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/service.py` | orchestration service |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/models.py` | request/response models |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/base.py` | provider interface |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/news_api.py` | NewsAPI adapter |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/newsdata.py` | NewsData adapter |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/gnews.py` | GNews adapter |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/guardian.py` | Guardian adapter |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/market_data.py` | Alpha Vantage/FMP/EODHD adapters |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/providers/browser_fetch.py` | Lightpanda-backed fetch/render adapter |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/mcp_gateway.py` | MCP invocation facade |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/extractors.py` | type-specific extraction |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/dedupe.py` | dedupe keys and duplicate groups |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/entity_resolution.py` | normalize startups/founders/investors |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/scoring.py` | trust/freshness/impact scoring |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/publisher.py` | socket publish and post promotion |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/image_service.py` | source image selection and Mistral fallback |
| `FASTAPI_COMMUNITY/app/services/realtime_syn/cleanup.py` | TTL and weekly cleanup logic |
| `FASTAPI_COMMUNITY/app/celery_tasks/realtime_syn_tasks.py` | background workers |

## 14. Worker Responsibilities

Heavy usage requires worker separation.

### 14.1 Required worker types

1. discovery worker
2. ingest worker
3. normalization worker
4. verification worker
5. enrichment worker
6. image worker
7. publish worker
8. cleanup worker
9. metrics worker

### 14.2 Worker responsibility detail

#### Discovery worker

- runs channel-specific source polling
- reads source budgets
- creates candidate fetch jobs

#### Ingest worker

- performs API fetch
- performs RSS fetch
- performs browser fetch via Lightpanda when required
- stores raw payload reference if needed

#### Normalization worker

- extracts canonical fields
- maps source payloads to standard syn schema
- builds dedupe keys

#### Verification worker

- requests second-source confirmation
- checks source quality
- updates `trust_score`

#### Enrichment worker

- calls TAM/VC/competitor/market MCPs
- enriches high-value items only
- does not block hot-path publish

#### Image worker

- keeps source image if valid
- requests Mistral-generated image only when item qualifies

#### Publish worker

- writes thin item to Mongo/Cosmos
- emits Socket.IO events
- optionally creates a promoted community post

#### Cleanup worker

- runs weekly cleanup
- archives or expires short-lived syn items
- preserves engagement-linked stubs

#### Metrics worker

- aggregates per-source and per-channel metrics
- stores source health and run quality

### 14.3 Queue design

Recommended Celery queues:

- `syn_discovery`
- `syn_ingest`
- `syn_normalize`
- `syn_verify`
- `syn_enrich`
- `syn_images`
- `syn_publish`
- `syn_cleanup`
- `syn_metrics`

## 15. Scheduling Plan

### 15.1 APScheduler use

Use APScheduler for:

- lightweight recurring checks
- weekly cleanup trigger
- small maintenance jobs

### 15.2 Celery use

Use Celery for:

- ingest
- normalization
- verification
- enrichment
- image generation
- publish
- metrics aggregation

### 15.3 Cadence policy

Recommended cadence policy:

- hot channels: every 1 to 5 minutes depending on source budget
- medium channels: every 10 to 30 minutes
- slow channels: hourly or more
- cleanup: weekly
- metrics aggregation: every 15 minutes or hourly

## 16. Ranking And Promotion Logic

### 16.1 Scores

Each item should compute:

- `freshness_score`
- `trust_score`
- `impact_score`
- `discussion_score`

### 16.2 Ranking inputs

Use:

- source recency
- corroboration count
- source quality
- startup/community relevance
- market significance
- novelty
- engagement potential

### 16.3 Promotion threshold

Only selected items should become community posts.

Promotion triggers may include:

- very high impact
- very high trust
- admin/manual promotion
- strong user engagement
- strategic startup importance

## 17. Notification And Push Strategy

Use existing notification infrastructure for high-signal syn events only.

Do not notify for every item.

Recommended cases for notifications:

- major funding
- urgent layoffs/shutdowns
- high-trust startup failure
- user-followed startup/company updates
- channel digest ready

Potential integrations:

- notification feed entry
- push notification to subscribed devices
- digest summary notification

## 18. Heavy-Load And Scale Requirements

This system must be built for heavy ingest and heavy user consumption.

### 18.1 Ingest scaling

- scale workers horizontally
- isolate slow providers
- apply provider-level circuit breakers
- apply cooldowns for 429s
- use rate-limit-aware retry with jitter

### 18.2 Publish scaling

- use Redis pub/sub between workers and API nodes
- batch publish bursts when possible
- keep socket payloads thin

### 18.3 Storage scaling

- thin records only
- TTL cleanup
- source-budget router
- selective enrichment
- selective image generation

### 18.4 UI scaling

- cursor pagination
- per-tab cache
- socket queue instead of forced instant prepend for all items
- only render visible list sections

### 18.5 Failure isolation

- failing source must not break the feed
- browser-render failures must fall back cleanly
- deep MCP research failure must not block hot-path publish

## 19. Security, Trust, And Moderation

### 19.1 Trust controls

- show source name and link
- store citation links
- use corroboration when possible
- label generated images clearly

### 19.2 Abuse controls

- domain allowlist or quality scoring
- duplicate suppression
- spam suppression
- moderation path for bad or low-trust items

### 19.3 Link policy

The system should redirect users to original links for more information. This is aligned with the thin-storage model and reduces storage pressure.

## 20. File-By-File Implementation Map

### 20.1 Community backend

- Modify `FASTAPI_COMMUNITY/app/api/main.py`
  - include `realtime_syn_routes`
- Modify `FASTAPI_COMMUNITY/app/main.py`
  - register startup hooks and scheduler wiring for syn
- Modify `FASTAPI_COMMUNITY/app/core/socket_manager.py`
  - add syn event emitters
- Modify `FASTAPI_COMMUNITY/app/db/mongo.py`
  - register collections and indexes
- Modify `FASTAPI_COMMUNITY/app/core/config.py`
  - add env variables and source toggles
- Modify `FASTAPI_COMMUNITY/app/core/celery.py`
  - add queues and beat tasks
- Modify `FASTAPI_COMMUNITY/app/core/scheduler.py`
  - add lightweight jobs and weekly cleanup trigger
- Add `FASTAPI_COMMUNITY/app/api/routes/realtime_syn_routes.py`
- Add `FASTAPI_COMMUNITY/app/services/realtime_syn/`
- Add `FASTAPI_COMMUNITY/app/celery_tasks/realtime_syn_tasks.py`

### 20.2 Frontend

- Modify `lliveupdatedstreaming/src/components/Community/pages/WarRoom.tsx`
  - add tab and cache
  - add fetch path
  - add socket events
- Add `lliveupdatedstreaming/src/components/Community/components/community/RealtimeSynCard.tsx`
- Add `lliveupdatedstreaming/src/components/Community/components/community/RealtimeSynList.tsx`
- Modify `lliveupdatedstreaming/src/components/Community/types/communityTypes.ts`
  - add syn types

### 20.3 Deep research integration

- Reuse `Server1_FastApi` only for deep-path jobs and optional progress streaming
- No direct ownership of the hot realtime stream should move to `Server1_FastApi`

### 20.4 Chat service

- Do not move Real Time Syn into `server3`
- `server3` remains a reference for WebSocket reliability patterns only

## 21. Suggested Implementation Order

### Phase 0: groundwork

- finalize schema
- finalize source policy
- finalize MCP role split
- finalize retention policy

### Phase 1: backend skeleton

- add collections and indexes
- add config flags
- add empty service layer and route scaffolding
- add worker scaffolding

### Phase 2: hot path

- implement source router
- implement provider adapters
- implement thin-item storage
- implement `/api/realtime-syn`
- implement `realtime_syn_item` socket publish

### Phase 3: frontend stream

- add WarRoom `Real Time Syn` tab
- add syn cards and list UI
- add socket queue behavior
- add source redirect link handling

### Phase 4: enrichment

- add Lightpanda fetch path
- add market/competitor/TAM MCP enrichments
- add Mistral image fallback for selected items

### Phase 5: promotion and alerts

- add promotion to posts
- add selective notifications and push
- add discussion bridge between syn and posts

### Phase 6: deep research and scale

- add deeper research jobs through `Server1_FastApi`
- tune queues and budgets
- add metrics dashboards and source health views
- optimize for heavy traffic

## 22. Non-Goals For Phase 1

Do not do these in the first implementation pass:

- full article archival
- full-text mirroring of every external source
- deep MCP enrichment on every item
- mandatory image generation on every item
- moving syn into `server3`

## 23. Final Design Decisions

This document commits to the following design direction:

- Real Time Syn lives in `FASTAPI_COMMUNITY`
- it is exposed in WarRoom as a dedicated tab between `Trending` and `My Posts`
- it uses thin storage with source links and short retention
- it supports weekly cleanup
- it uses Lightpanda as the browser-render layer
- it includes market, TAM, VC, and competitor MCPs as enrichment layers
- it keeps deep research separate from the hot realtime path
- it keeps standard community posts separate from canonical syn items
- it is designed from day one for heavy ingest and heavy user access

## 24. Immediate Next Step

The next step after this document is to convert it into an implementation checklist and then implement in phases. This document itself does not change product behavior.
