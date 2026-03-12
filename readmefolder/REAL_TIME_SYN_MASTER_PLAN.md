# REAL-TIME SYN Master Plan (War Room) - Corrected V2

Date: March 8, 2026  
Mode: Planning only (no code implementation in this document)

## 0) Feedback Reconciliation (Applied and Corrected)

This version is regenerated using your feedback, with live verification against official docs where available.

### Accepted from feedback

- Remove `NewsAPI.org` from production source set (free tier is development-only).
- Fix scheduler overlap risk (async loop + Celery beat) with a single scheduler authority plus distributed lock.
- Add cold-start strategy for new users.
- Add content-safety pipeline (text/image/link safety).
- Add MongoDB TTL and lifecycle policies.
- Add explicit dedup parameters and ranker weights.

### Corrected from feedback (official docs conflict)

- `World News API` free tier is documented as **50 points/day** (not 500 requests/day).
  - Quotas are points-based and endpoint-cost-based.
- `MediaStack` free tier is **100 requests/month** (about 3/day average), so it remains low-priority.

---

## 1) Product Goal and UX Contract

Add a new `SYN` tab beside `Trending` in War Room with:

- image
- concise summary
- source and freshness
- `Read More` button
- redirect to original website on click

And make ranking user-specific in real time using behavior signals.

---

## 2) Current Project Snapshot (Ground Truth from Your Code)

### Frontend

- War Room tabs are currently `trending`, `recent`, `wins`, `engagement`:
  - `lliveupdatedstreaming/src/components/Community/pages/WarRoom.tsx`
- Existing rotating feed card pulls `/api/ads/feed`:
  - `lliveupdatedstreaming/src/components/Community/pages/Rotationfeed.tsx`

### Backend

- Aggregated feed endpoint:
  - `FASTAPI_COMMUNITY/app/api/routes/ads_routes.py`
- Current feed processing and cached-news handling:
  - `FASTAPI_COMMUNITY/app/api/utils/ads.py`
- Current refresh loop:
  - `FASTAPI_COMMUNITY/app/api/utils/ads_scheduler.py`
- Celery beat also schedules news refresh:
  - `FASTAPI_COMMUNITY/app/core/celery.py`

### Realtime

- Socket.IO is already mounted and usable:
  - `FASTAPI_COMMUNITY/app/core/socket_manager.py`
  - `FASTAPI_COMMUNITY/app/main.py`

### Architectural implication

SYN should be a dedicated subsystem (`/api/syn/*`) and not a hard extension of `/api/ads/feed`.

---

## 3) Source Policy: Free-Tier-Only and Production-Safe Design

Your key constraint is free keys only.  
Therefore SYN must run with:

- strict per-provider quota budgets
- legal-policy flags per provider
- fallback graph when quota/policy blocks a source

### 3.1 Provider matrix (news ingestion)

| Provider | Verified free-tier status | Production/legal status | SYN role |
|---|---|---|---|
| NewsData.io | 200 credits/day, 12h delayed, 10 articles/credit | Usually fine for prototype; verify final terms | High-volume delayed context source |
| GNews | 100 requests/day, 10 articles/request, 48h delay | Free plan personal/non-commercial | Dev/testing or non-commercial mode |
| NewsAPI.org | Free developer plan, delayed | Not for production/commercial | Remove from production pipeline |
| MediaStack | 100 requests/month, delayed | Low capacity for realtime | Last-resort fallback only |
| World News API | 50 points/day, endpoint cost by points, backlink requirement | Usable if terms satisfied and attribution done | Realtime candidate source with strict point budget |
| The Guardian API | 500 req/day, 12 req/min, non-commercial developer key | Non-commercial unless approved | High-quality non-commercial source |
| Currents API | Public pricing/docs differ by page | Verify account-level quota directly | Secondary source after key validation |
| NYT API | Official limits not fully crawlable here | Treat as contract-dependent until validated | Premium-source supplement |
| TheNewsAPI | 100 req/day, 3 articles/request | Good free prototype source | Fast lane source |

### 3.2 Enrichment/search API matrix

Use for recall expansion, validation, and source discovery only (not as primary card source unless needed):

- Tavily
- Exa
- Serper
- SerpAPI
- You.com API
- SearchAPI / SearchApi.io
- Jina AI
- Firecrawl

Policy:

- capped daily enrichment budget
- enrich only top clusters
- disable enrichment first during quota pressure

### 3.3 Domain-pack APIs

- Finance: AlphaVantage, EODHD, FinancialModelingPrep, Finnhub, CoinDesk data endpoints
- Space: NASA APOD
- Safety/security: AbuseIPDB

These power topic-specific SYN lanes after core feed is stable.

---

## 4) Revised Capacity Model (Free Tier Reality)

Do not model capacity only as "articles/day".  
Use provider-native budget units.

### 4.1 Budget units

- request/day
- points/day
- credits/day
- requests/month

### 4.2 Practical daily planning numbers (starting defaults)

- NewsData: `200 credits/day` (up to 2,000 delayed article records/day)
- TheNewsAPI: `100 req/day` (about 300 records/day)
- GNews: `100 req/day` delayed (dev/non-commercial lane)
- Guardian: up to `500 req/day` (non-commercial lane)
- World News API: `50 points/day` (request shape depends on endpoint cost)
- MediaStack: `100 req/month` (minimal operational role)

### 4.3 Capacity correction note

Feedback claimed "World News API 500/day".  
Official docs currently describe free plan as 50 points/day, so this plan keeps 50-point budgeting.

---

## 5) Scheduler and Locking Plan (Critical)

## 5.1 Current risk

Your project currently has multiple refresh schedulers. This can duplicate pulls and burn quotas.

## 5.2 Corrected scheduler architecture

- Keep one canonical ingestion scheduler:
  - preferred: Celery Beat single instance
- Disable or gate any parallel async loop scheduler for SYN ingestion.

## 5.3 Distributed lock

Use Redis distributed lock for each ingest cycle:

- lock key: `syn:ingest:lock`
- TTL: 180-300 sec
- acquire: `SET key value NX EX ttl`
- heartbeat/extend while running
- if lock not acquired: skip cycle

For multi-node deployments requiring stronger guarantees, apply Redlock pattern conservatively and monitor lock drift.

---

## 6) SYN Data Model and TTL Governance

Mongo collections:

- `syn_raw_articles`
- `syn_story_clusters`
- `syn_feed_items`
- `syn_user_profiles`
- `syn_user_events`
- `syn_quota_state`
- `syn_rank_audit`

### 6.1 TTL policy

- `syn_raw_articles`: 30 days
- `syn_user_events`: 90 days (or 180 based on analytics needs)
- `syn_rank_audit`: 14-30 days
- `syn_quota_state`: no TTL (stateful)

Mongo TTL examples to apply in implementation phase:

- `expireAfterSeconds: 2592000` for 30 days
- `expireAfterSeconds: 7776000` for 90 days

---

## 7) Ingestion and Normalization Pipeline

1. Fetch from allowed providers based on budget and policy gates.
2. Normalize to canonical schema:
   - title, description, source, url, image, published_at, provider, language, topics
3. Validate URL and media fields.
4. Run dedup + clustering.
5. Generate summary.
6. Publish card candidates to `syn_feed_items`.

Canonical required fields for card rendering:

- `item_id`
- `title`
- `summary`
- `image_url`
- `source_name`
- `source_url`
- `published_at`
- `cluster_id`
- `topic_tags`

---

## 8) Dedup and Clustering Parameters (Now Explicit)

### 8.1 Tiered dedup

1. Exact dedup:
   - URL canonicalization + hash
2. Near duplicate:
   - shingle size: 3-5 words (default 5)
   - MinHash permutations: 128-200 (start 128)
   - LSH bands/rows: 18 x 7 (126 hash buckets)
   - Jaccard threshold target: around 0.85
3. Semantic dedup:
   - embedding cosine threshold: 0.85-0.88 (start 0.86)

### 8.2 Story clustering

- cluster by event semantic similarity + entity/time overlap
- one canonical card per cluster
- preserve alternate source links as related evidence

---

## 9) Personalization and Ranking

## 9.1 Cold start (new user)

When no behavioral history exists:

1. show global trending + freshness
2. ask onboarding topic picks
3. use locale/time-based priors
4. allocate higher exploration share initially (for first N interactions)

## 9.2 Baseline scoring (v1)

Starting weights:

- freshness: 0.30
- topical match: 0.25
- source quality/trust: 0.20
- behavior affinity: 0.15
- novelty/diversity: 0.10

Score:

`final_score = 0.30F + 0.25T + 0.20S + 0.15B + 0.10N - fatigue_penalty`

## 9.3 Online exploration

Use Thompson Sampling:

- per arm/article/topic posterior:
  - `alpha = clicks + 1`
  - `beta = impressions - clicks + 1`
- serve:
  - 90 percent exploit
  - 10 percent explore

## 9.4 Advanced phase

- two-stage retrieval:
  - candidate generation (keywords + semantic ANN)
  - reranker (hybrid features)
- keep MMR diversity post-processing in final slate.

---

## 10) Real-Time Delivery Design

Use Socket.IO first to match existing stack.

Events:

- `syn_new_items`
- `syn_feed_refresh`
- `syn_item_patch`

Fallback:

- cursor polling endpoint (`GET /api/syn/feed?cursor=...`)

---

## 11) War Room Integration Plan

UI changes to plan:

1. Add `syn` tab next to `trending` in WarRoom filters.
2. Render SYN cards with image + summary + source + read-more.
3. `Read More` click:
   - fire tracking event
   - open original source URL in new tab
4. Optional "Why this item" explanation chip in phase 2.

---

## 12) Safety, Moderation, and Trust

### 12.1 Link and source safety

- validate URL format and hostname
- optional AbuseIPDB checks for suspicious origins/IP context
- domain blocklist / allowlist controls

### 12.2 Content moderation

- text toxicity filter (for generated/ingested summary text)
- NSFW image detection for thumbnails
- source reputation scoring

### 12.3 Summary safety

- summary must be source-grounded
- no unsupported claims
- keep explicit link to original

---

## 13) API Surface (Planned)

- `GET /api/syn/feed`
- `POST /api/syn/feedback`
- `POST /api/syn/read-more/{item_id}`
- `GET /api/syn/topics`
- `POST /api/syn/topics/preferences`
- `GET /api/syn/health`
- `POST /api/syn/admin/refresh` (admin only)

Feedback events:

- impression
- card_open
- click_read_more
- hide
- not_interested

---

## 14) Observability and Guardrails

Track:

- ingestion success/failure by provider
- quota burn and reset times
- dedup ratio and cluster merge ratio
- p50/p95 feed latency
- CTR, read-more conversion
- hide rate and bounce signals
- cold-start cohort performance vs warm users
- personalization lift vs non-personalized baseline

Alerts:

- stale feed age above threshold
- sudden quota depletion
- provider error spikes
- ranking quality drops

---

## 15) Rollout Plan (Phased)

## Phase 0 - Governance and source policy hardening

- finalize provider policy flags (`dev_only`, `non_commercial`, `attribution_required`, `backlink_required`)
- register all keys and fetch runtime quota headers

## Phase 1 - SYN MVP (real-time + non-personalized)

- ingestion + normalization + dedup + summary + SYN tab
- socket push + read-more tracking
- source attribution and legal tags

## Phase 2 - Personalization v1

- profile vectors from interactions
- weighted ranker + cold-start flows + diversity constraints
- A/B test against baseline

## Phase 3 - Advanced ranking

- two-stage retrieval/ranking
- contextual bandit optimization
- explanation chips and deeper observability

## Phase 4 - Domain lanes

- finance lane
- space lane
- security lane

---

## 16) Critical Decisions (Before Implementation)

1. Confirm whether War Room is commercial production now or still pre-production.
2. Approve source tiers:
   - production-allowed
   - non-commercial-only
   - dev-only
3. Choose single scheduler owner (Celery Beat recommended).
4. Approve moderation provider stack (or in-house baseline).

---

## 17) Research Links Used for This Regeneration

News and provider policy:

- NewsAPI pricing and plan restrictions: https://newsapi.org/pricing
- GNews pricing/free plan details: https://gnews.io/pricing
- MediaStack pricing: https://mediastack.com/pricing/
- World News API pricing: https://worldnewsapi.com/pricing
- World News API quotas and rate limiting: https://worldnewsapi.com/docs/quotas-and-rate-limiting/
- World News API endpoint docs (point-cost behavior): https://worldnewsapi.com/docs
- The Guardian access and usage: https://open-platform.theguardian.com/access
- The Guardian terms: https://www.theguardian.com/open-platform/terms-and-conditions
- TheNewsAPI pricing: https://www.thenewsapi.com/pricing
- NewsData official pricing/rate posts:
  - https://newsdata.io/blog/pricing-plan-in-newsdata-io/
  - https://newsdata.io/blog/newsdata-rate-limit/
- Currents pricing/docs pages:
  - https://www.currentsapi.services/docs/pricing
  - https://docs.currents.dev/billing-and-pricing

Scheduler and lifecycle references:

- Celery periodic tasks and beat behavior: https://docs.celeryq.dev/en/main/userguide/periodic-tasks.html
- Redis distributed locks and Redlock discussion: https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
- MongoDB TTL indexes: https://www.mongodb.com/docs/current/core/index-ttl/

Benchmark and recommender references:

- X recommender overview: https://help.x.com/en/resources/recommender-systems/for-you-home-timeline-recommendations
- X recommendation algorithm blog: https://blog.x.com/engineering/en_us/topics/open-source/2023/twitter-recommendation-algorithm
- MIND dataset: https://msnews.github.io/
- NRMS paper: https://aclanthology.org/D19-1671/
- Actually Relevant: https://actuallyrelevant.news/
- Actually Relevant methodology: https://actuallyrelevant.news/methodology/

Enrichment/data APIs referenced:

- Tavily: https://docs.tavily.com/documentation/api-credits
- Exa: https://exa.ai/pricing/api
- Firecrawl: https://docs.firecrawl.dev/rate-limits
- SerpAPI: https://serpapi.com/pricing
- You API pricing: https://you.com/pricing
- SearchAPI: https://www.searchapi.site/pricing
- SearchApi.io: https://www.searchapi.io/pricing
- NASA API auth and rate limits: https://api.nasa.gov/assets/html/authentication.html
- AbuseIPDB docs and pricing:
  - https://docs.abuseipdb.com/
  - https://www.abuseipdb.com/pricing

---

## 18) Final Statement

This corrected V2 plan keeps your feedback direction, but locks capacity/legal assumptions to currently verified docs, especially for:

- NewsAPI production restriction
- World News API free-point budgeting
- scheduler dedup safety
- cold start and moderation completeness
- TTL and lifecycle governance

