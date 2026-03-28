# Feed Lens -- Complete Idea & Architecture Design Document

**Version:** 1.1
**Date:** 2026-03-26
**Status:** Research & Design (Pre-Implementation)
**Author:** Research Architect Agent

---

## Table of Contents

1. [Codebase Analysis Summary](#1-codebase-analysis-summary)
2. [The Feed Lens Idea -- Complete Concept](#2-the-feed-lens-idea----complete-concept)
3. [Research Findings](#3-research-findings)
4. [UX/UI Design Concept](#4-uxui-design-concept)
5. [Input Methods -- How Users Define Their Algorithm](#5-input-methods----how-users-define-their-algorithm)
6. [The Scoring System Design](#6-the-scoring-system-design)
6.5. [Intent Mode -- Temporary Cross-System Priority Overlays](#65-intent-mode----temporary-cross-system-priority-overlays)
7. [Architecture Design](#7-architecture-design)
8. [Data Model Design](#8-data-model-design)
9. [Real-Time Syn Integration](#9-real-time-syn-integration)
10. [Security Design](#10-security-design)
11. [Scaling Design](#11-scaling-design)
12. [Problem Resolution](#12-problem-resolution)
13. [New Ideas & Innovations](#13-new-ideas--innovations)
14. [What Fits in FASTAPI_COMMUNITY vs. What's New](#14-what-fits-in-fastapi_community-vs-whats-new)
15. [Revision History](#revision-history)

---

## 1. Codebase Analysis Summary

### A. FASTAPI_COMMUNITY (Primary Community Backend)

This is the server where Feed Lens must live. Here is what exists today:

**Existing Scoring System** (`app/api/utils/community.py`, lines 123-254):
- `calculate_trending_score()` computes a single global score per post using:
  - Engagement: `likes * 3 + comments * 2 + bookmarks * 2`
  - Time decay: Exponential decay with daily cosine cycle, 24-hour half-life
  - Category weight: 8 categories with weights from 1.5 to 2.5 (Wins: 2.5, Questions/Help: 2.0, Deep Talk: 1.8, Event: 2.2, Milestones: 2.5, Collab: 2.0, Tools/Resources: 2.2, New Opportunities: 2.3)
  - Author reputation: Based on `setUserRole` (investor: 2.5, mentor: 2.0, founder: 1.8, guest: 1.0) plus account age bonus (0.5 to 1.5)
  - AI quality score: Groq API rates post content 0-10 on clarity, value, engagement, grammar (cached in `aiQualityScore` field)
  - Daily boost: Time-of-day multiplier (1.3 during peak hours, 1.1 midday, 1.0 night)
- Scores are recalculated every 15 minutes via `update_all_trending_scores_async()` in batches of 500

**Feed Endpoint** (`app/api/routes/community_routes.py`, lines 302-549):
- `GET /api/posts` with `filter` parameter supporting: `trending`, `recent`, `my_posts`, `feed`, `wins`, `engagement`, `popular`, `oldest`, `most_liked`, `most_commented`
- Supports both cursor-based and offset-based pagination
- Trending page 1 is cached in both memory (`TRENDING_POSTS_CACHE`) and MongoDB (`trending_posts_cache` collection) with multi-level fallback on timeout
- Each filter type applies different sort criteria and query filters

**Ideas System** (`app/api/utils/ideas.py`, `app/api/routes/ideas_routes.py`):
- Separate `calculate_trending_score()` for ideas (simpler: `(likes*2 + comments*3 + bookmarks*1.5) * time_factor`)
- Filter types: `all`, `my`, `public`, `private`, `popular`, `trending`, `new`
- Batch enrichment pattern (`batch_enrich_ideas()`) that solves N+1 queries -- this pattern should be reused

**MongoDB Collections** (`app/db/mongo.py`):
- 40+ collections under `community_db.*` namespace
- Key collections for Feed Lens: `posts`, `ideas`, `follows`, `users_collection`, `bookmarks`, `realtime_syn_items`, `realtime_syn_user_state`, `trending_posts_cache`
- Comprehensive indexes already exist for trending/feed queries including compound indexes on `(trendingScore, createdAt, _id)`
- No `feed_lenses` or `user_engagement_signals` collection exists yet

**Redis** (`app/db/redis.py`):
- Two Redis clients: main (`redis_client`) and websocket-specific (`websocket_redis_client`)
- Azure Redis with SSL support, auto-port correction (6379 to 6380)
- Currently used for rate limiting, session management, websocket pub/sub
- No feed-scoring keys exist yet

**Scheduler** (`app/core/scheduler.py`):
- APScheduler (AsyncIO) runs:
  - Trending score updates: every 15 minutes
  - Notification cleanup: every 24 hours
  - Real Time Syn sync: configurable interval
  - Real Time Syn cleanup: configurable interval
- All jobs have `max_instances=1` and `coalesce=True`

**Celery Tasks** (`app/celery_tasks/`):
- `community_tasks.py`: `update_trending_scores_task()` wraps the async trending update
- Separate task files for ads, bot, chat, comments, follow, ideas, notifications, push, realtime_syn, search

**Real Time Syn** (`app/services/realtime_syn/`):
- Full pipeline: providers (GNews, Guardian, MediaStack, NewsData, DuckDuckGo, Browser, MCP) fetch news
- Scoring module (`scoring.py`): 4 independent scores per item -- freshness (0-100), trust (0-100), impact (0-100), discussion (0-100)
- Channel-based classification (funding, layoffs, startup_news, product_launches, etc.)
- Entity resolution, image service, publisher, publication guard, cleanup
- Items stored in `realtime_syn_items` with `item_id`, scored fields, and TTL expiry

**Authentication** (`app/api/deps.py`):
- Firebase JWT tokens via Bearer header or cookie
- `get_current_user()` and `get_optional_current_user()` dependencies
- User activity tracked on each authenticated request
- Admin role check via `requires_admin()`

### B. lliveupdatedstreaming (Frontend)

**WarRoom Component** (`src/components/Community/pages/WarRoom.tsx`):
- Main feed page, approximately 800+ lines
- Filter tabs at the top: `trending`, `realtime_syn`, `recent` (labeled "My Posts"), `wins`, `engagement`
- Guest users only see `trending` and `realtime_syn` tabs
- Feed caching system using `useRef` with per-filter cache objects storing: posts, cursor, page, scrollY, hasMore, loadMoreBlocked, lastUpdated
- Socket.IO integration for real-time post arrival with queue-based "Show N New Posts" toast pattern
- Infinite scroll via IntersectionObserver on a `#scroll-sentinel` element
- Rate-limited API calls via `runRateLimited()` utility
- The filter tabs UI is a horizontal scrollable button bar -- this is where Feed Lens indicator will be added

**UI Library**: shadcn/ui with all key components present:
- `Slider` component exists at `src/components/ui/slider.tsx`
- `Dialog`, `Sheet`, `Card`, `Button`, `Tabs`, `Select`, `Switch`, `Toggle`, `Tooltip` all available
- Tailwind CSS with dark theme support

**Types** (`src/components/Community/types/communityTypes.ts`):
- `PostCategory`: 'Wins' | 'Questions/Help' | 'Deep Talk' | 'Event' | 'Milestones' | 'Collab' | 'Tools/Resources' | 'New Opportunities'
- `RealtimeSynItem` interface with item_id, channel, scores (freshness, trust, impact, discussion), etc.
- `FeedItem = Post | RealtimeSynItem` union type already exists

**State Management**:
- React Context (`Authcontext.tsx`) for auth state
- Redux store (`store/`) for business plan state
- No dedicated feed state store -- WarRoom manages its own state via hooks/refs

### C. server3 (Chat Backend)

- WebSocket infrastructure for real-time chat
- Connection manager pattern at `app/services/connection_manager.py`
- Independent auth (its own JWT verification in `app/core/security.py`)
- Not directly relevant to Feed Lens except: the WebSocket patterns could inform real-time lens preview delivery

### D. Server1_FastApi (Business Tools)

- Profile routes (`app/api/routes/profile_routes.py`) store rich user data: role, industries, skills, stage, fundingGoal, investmentRange, preferredSectors, etc.
- This profile data is a potential signal source for Feed Lens auto-configuration (matching user industries to post categories)
- Has its own Redis caching with TTLs (profile: 5min, activity: 1min)
- Not a target for Feed Lens implementation -- but profile data can be read from the shared MongoDB

---

## 2. The Feed Lens Idea -- Complete Concept

### Core Philosophy

**"Feed Lens"** is a system that gives every user control over what they see in their feed, without ever exposing code, algorithms, or technical complexity. The metaphor is deliberate: like a camera lens, it filters what you see. Change the lens, change your view of the community.

### What It Is

A Feed Lens is a stored, named, user-owned configuration that selects and ranks posts using only pre-approved building blocks. It is a parameter object -- a set of weights, filters, and preferences -- NOT executable code. The system takes these parameters and applies them as a weighted overlay on top of pre-computed post scores.

### What It Is NOT

- Not a code editor or programming interface
- Not a black-box ML model per user
- Not a separate feed engine -- it extends the existing scoring system
- Not a replacement for the platform default feed -- the default always exists as a fallback

### The "Never Say Algorithm" Principle

In all user-facing surfaces, the word "algorithm" is never used. Instead:
- "Feed Lens" -- the primary term
- "Recipe" -- when explaining how it works ("You're adjusting the recipe for what your feed serves you")
- "View" -- when switching ("Viewing via: My Morning Mix")
- "Taste profile" -- when the system learns from behavior

### Key Constraints

1. **Max 5 custom lenses per user** plus the immutable platform default
2. **Parameter objects only** -- weights are bounded numbers (0-3 range), filters are pick-lists of pre-approved values, never arbitrary strings
3. **Instant fallback** -- if a custom lens returns fewer than 5 posts, the system blends 70% platform default + 30% custom and shows a gentle toast notification
4. **Session-keyed** -- active lens is keyed to both `user_id` AND session token in Redis, preventing cross-user contamination on shared devices
5. **Versioned** -- every lens edit creates a version snapshot; users can revert to "yesterday's recipe"

---

## 3. Research Findings

### Industry Landscape

The research reveals that user-selectable feed algorithms have moved from theory to shipping products:

**Bluesky Custom Feeds** are the clearest precedent. As of mid-2025, Bluesky has 37M+ users with custom feed generators running on external servers via the AT Protocol. Anyone can create and publish a feed. Third-party tools like SkyFeed and Graze emerged to make feed-building accessible without coding -- Graze raised $1M in April 2025 and powers thousands of Bluesky feeds using templates, moderation logic, sort order, and social-graph inclusion. This proves the feasibility of many distinct ranking configs existing simultaneously.

**EU Digital Services Act (Article 27)** requires large platforms to offer at least one recommender option not based on profiling. A March 2026 Dutch court ruling upheld forcing Meta to offer chronological feeds. This is now a regulatory expectation, not just a feature.

**X (Twitter)** distinguishes "For You" from "Following" but doesn't let users define ranking logic. **Reddit** offers "Best" sort toggle but no customization. **Instagram** added "Following" and "Favorites" but they're constrained to platform-defined modes. None offer the depth Feed Lens proposes.

### Academic Research

Three papers are directly relevant:

1. **"Designing Usable Controls for Customizable Social Media Feeds"** (arxiv 2509.19615) -- Presents "Pilot," a system of controls on Bluesky that are expressive, intuitive, and integrated directly into the feed. Key finding: controls should live alongside normal browsing, not in a separate settings panel. Integration into the existing workflow is a key design objective.

2. **"BONSAI: Intentional and Personalized Social Media Feeds"** (CHI 2026, arxiv 2509.10776v2) -- Users express feed intent in natural language, then the system translates to sourcing/curating/ranking parameters. Key finding: natural language is a great zero-friction start, but must be paired with visible translation into concrete controls, fast preview feedback, and easy correction. Users felt empowered but noted extra cognitive effort.

3. **"Mapping the Design Space of Teachable Social Media Feed Experiences"** (CHI 2024, ACM) -- Interactive Machine Teaching (IMT) framework where the user is the "teacher" and the algorithm is the "learner." Users teach by reacting to real posts. Key finding: customization should live alongside normal browsing, and there is a constant tension between expressiveness and understandability.

### UX Best Practices

- **Progressive disclosure** is critical: most users (80%+) will use templates or the 3-question quick setup; only power users will touch sliders or the mind-map builder
- **Netflix-style onboarding** demonstrates that taste preference collection should happen at signup, not be buried in settings
- **Immediate feedback loops** are essential: every slider change should show a live preview of 3-4 real posts that would appear under that configuration
- **Reversibility reduces fear**: users experiment more when they can undo (research on "folk theories" of algorithms shows users develop hypotheses and test them)
- **Dwell time** is the most reliable implicit signal (LinkedIn, TikTok both use it as primary engagement proxy)

### Technical Patterns

- **Pre-computed component scores + per-user weighted dot product** is the standard pattern for scalable personalized ranking (used by LinkedIn, Twitter, recommendation systems)
- **Redis HSET for post scores + HGETALL for user lens** keeps the per-request overhead under 15ms
- **Feature stores** (batch + real-time pipelines) are the production pattern for managing scoring signals

---

## 4. UX/UI Design Concept

### Design Principles

1. **"Show, don't configure"** -- Every control shows real posts as feedback, not abstract numbers
2. **Zero-step default** -- New users get the platform default feed with zero configuration required
3. **One-tap switching** -- Active lens shown in feed header, one tap to switch
4. **No jargon** -- Labels use plain English outcomes ("Hidden Gems" not "Low engagement weight")
5. **Mobile-first** -- All interactions work on a phone screen; the mind-map builder is desktop-only
6. **Forgiving** -- Guardrails prevent empty feeds; the system auto-corrects extreme configurations

### Screen Flow Architecture

The Feed Lens feature introduces 4 new screens/panels, all accessible from the existing WarRoom:

**Entry Point 1: Feed Header Indicator (always visible)**

In the WarRoom, directly below the filter tabs (trending/realtime_syn/recent/wins/engagement), a subtle bar appears for logged-in users:

```
Viewing via: Barise Default  [Change Lens]
```

When a custom lens is active:

```
Viewing via: My Morning Mix  [Change] [Edit]
```

This indicator is small, non-intrusive, and always tells the user exactly which lens is active. The `[Change Lens]` button opens the Lens Picker Sheet.

**Entry Point 2: Lens Picker Sheet (bottom sheet on mobile, side panel on desktop)**

A slide-up panel showing:
- The platform default lens (always first, cannot be deleted)
- Up to 5 user-created lenses as cards
- Each card shows: name, emoji icon, mini slider visualization (5 tiny bars showing weight distribution), last-used date, and usage count
- "Create New Lens" button at the bottom
- One-tap to activate any lens -- feed reloads immediately with a brief shimmer animation

Card layout:

```
+----------------------------------+
|  [icon]  My Morning Mix          |
|  Used 24 times  |  Last: today   |
|  ||||.  ||...  ||||  |...  |||   |
|  [Active]           [Edit] [Use] |
+----------------------------------+
```

The 5 tiny bars represent the 5 core slider dimensions at a glance.

**Entry Point 3: Lens Editor (full-screen modal on mobile, large dialog on desktop)**

This is where lenses are created and edited. It uses progressive disclosure with 3 tabs:

- **Quick Setup** (default tab) -- The 3-question wizard
- **Vibe Sliders** -- The 5-8 slider panel with live preview
- **Templates** -- Pre-built lens gallery

An additional "Advanced" toggle at the bottom reveals:
- **AI Builder** -- Natural language input
- **Teach Mode** -- React-to-posts teaching flow

**Entry Point 4: Inline Feed Controls (embedded in the feed itself)**

On each post card, a subtle "..." menu gains a new option: "Tune my lens from this post" which opens a mini-panel:
- "More like this" -- boosts the weight dimensions that caused this post to rank
- "Less like this" -- reduces those dimensions
- "Why am I seeing this?" -- shows which lens parameters caused this post to appear

This is the "teach while browsing" channel from the research -- the most natural way for non-technical users to refine their feed.

### Accessibility for Non-Technical Users

The entire design is layered for progressive complexity:

**Layer 0 (zero effort):** User does nothing. Platform default feed works exactly as today.

**Layer 1 (30 seconds):** User picks a template from the gallery. One tap. Done. "Investor Eye," "Builder Mode," "Discovery Mode" etc.

**Layer 2 (2 minutes):** User answers 3 plain-English questions in the Quick Setup wizard. System creates a lens automatically.

**Layer 3 (5 minutes):** User adjusts the Vibe Sliders. Each slider has a human-readable label pair (e.g., "Hidden Gems" <--> "Most Popular"). Live preview shows 4 real posts updating as sliders move.

**Layer 4 (ongoing):** User taps "More like this" / "Less like this" on posts in their feed. The system learns incrementally.

**Layer 5 (power users only):** User types natural language ("show me funding news from people I follow, mostly recent"), AI translates to slider positions, user confirms.

Most users will never go past Layer 2. That is by design.

---

## 5. Input Methods -- How Users Define Their Algorithm

### Method 1: Template Gallery (Simplest -- One Tap)

Pre-built lenses that work immediately. Each template is a curated set of weights and filters designed for a specific use case.

**11 System Templates:**

| Template | Emoji | Primary Weights | Description |
|----------|-------|----------------|-------------|
| Barise Default | -- | All 1.0 | The platform's standard trending algorithm |
| Power Networker | handshake | following_boost: 2.8 | See posts from people you follow first |
| Deep Diver | microscope | quality: 2.5, reputation: 1.8 | Prioritize thoughtful, substantive content |
| Trend Surfer | surfer | engagement: 2.5, recency: 2.0 | What's hot right now |
| Fresh Feed | seedling | recency: 2.8 | Newest posts first, regardless of popularity |
| Founder Intel | brain | reputation: 2.8, quality: 1.5 | Posts from experienced founders and investors |
| Win Gallery | trophy | category_boost: 2.0 (Wins only) | Celebrate community wins |
| Question Hunter | question mark | category_boost: 4.0 (Questions/Help) | Find people who need help |
| Discovery Mode | globe | serendipity: 0.8, diversity: 0.8 | Surprise me with new voices and topics |
| Event Focus | calendar | category_boost: 4.0 (Events) | Don't miss upcoming events |
| Slow Scroll | coffee | quality: 2.0, recency: 0.3 | Quality over timeliness |

Templates can be "forked" -- the user picks a template, then edits it to create their own custom lens. The template remains unchanged; the fork becomes a personal lens.

### Method 2: 3-Question Quick Setup (30 Seconds)

Three plain-English questions with visual choice cards (not dropdowns):

**Question 1: "What kind of posts excite you most?"** (multi-select, pick 1-3)
- Cards with icons: Funding News | Product Launches | Founder Stories | Wins & Milestones | Questions & Help | Deep Discussions | Events | Tools & Resources | New Opportunities | Collaborations
- Maps to: `category_boost` weights and `filters.topics`

**Question 2: "Whose posts matter most to you?"** (single select)
- Cards: "People I Follow" | "A Mix of Everyone" | "Discover New Voices"
- Maps to: `following_boost` and `diversity` weights

**Question 3: "How fresh do you like your feed?"** (single select)
- Cards: "What's Trending Now" | "Newest Posts First" | "Quality Over Speed"
- Maps to: `recency`, `engagement`, and `quality` weights

After answering, the system shows: "Here's your lens: [auto-generated name]" with a preview of 4 real posts, and two buttons: "Looks Great!" and "Let Me Tweak It" (which opens the Vibe Sliders pre-populated with the Quick Setup answers).

### Method 3: Vibe Sliders Panel (Refinement -- 2 Minutes)

**8 weight dimensions**, each displayed as a labeled slider between two opposing concepts:

| Slider Label Left | Slider Label Right | Internal Dimension | Range | Default |
|---|---|---|---|---|
| Hidden Gems | Most Popular | engagement | 0-3 | 1.0 |
| All-time Classics | Just Posted | recency | 0-3 | 1.0 |
| Casual Posts | Deep Insights | quality | 0-3 | 1.0 |
| Anyone | Verified Voices | reputation | 0-3 | 1.0 |
| Category Ignored | Category First | category_boost | 0-3 | 1.0 |
| Discover Everyone | My Network Only | following_boost | 0-3 | 1.0 |
| Same Vibes OK | Max Variety | diversity | 0-1 | 0.0 |
| Predictable | Surprise Me | serendipity | 0-1 | 0.0 |

**The Key Innovation: Live Preview Panel**

Below the sliders, a panel shows 4 real posts that would appear under the current slider configuration. As the user moves any slider, the preview updates in real-time (debounced at 300ms). This makes abstract weights tangible.

The preview uses the same scoring engine as the real feed but operates on a cached sample of recent posts (stored in Redis, refreshed every 15 minutes). This means preview responses are sub-50ms.

Each slider has a small "reset" icon to return to the default value. A "Reset All" button at the top returns everything to platform defaults.

### Method 4: AI Conversation Builder (Natural Language)

A chat-style interface where the user types plain English:

> User: "I want to see funding news and product launches, mostly from people I follow, with some surprises mixed in"

The system (using **Mistral medium-2505 via the Azure endpoint**) translates this to slider positions and shows:

```
Here's what I set for you:
  - Category Focus: Funding News, Product Launches (category_boost: 2.5)
  - Network Priority: People I Follow (following_boost: 2.2)
  - Surprise Factor: Medium (serendipity: 0.4)

[Preview: 4 posts]

Does this look right? You can adjust the sliders or tell me what to change.
```

The AI ONLY translates intent into the same bounded parameter object -- it never generates executable logic. The translation is constrained to the same 8 dimensions and their valid ranges. This is a "translator from intent to safe config," not an autonomous ranking brain.

The user can refine conversationally: "Make it more focused on recent posts" and the Mistral medium-2505 (Azure endpoint) adjusts the recency slider up.

> **Note on AI Model Selection:** Mistral is the preferred AI model for Feed Lens because it is already integrated into Real Time Syn (`REALTIME_SYN_MISTRAL_REVIEW_ENABLED=true`) and runs on the project's Azure endpoint (`https://info-m98rto5s-eastus2.openai.azure.com/openai/v1/`), keeping all AI calls within a single Azure deployment. Groq remains in use only for the existing AI quality scoring on posts (`aiQualityScore` field) -- Feed Lens AI chat and natural language translation use Mistral exclusively.

### Method 5: "React to Posts" Teaching Mode (Learn by Example)

The system shows 12 real posts, sampled to cover different categories, recency levels, and engagement levels. The user reacts to each with one of 4 options:

- **Love it** (heart icon) -- strong positive signal
- **Good** (thumbs up) -- mild positive
- **Not for me** (wave icon) -- mild negative
- **Never show this** (X icon) -- strong negative

After 12 reactions, the system analyzes patterns:
- Did the user love mostly funding posts? Boost `category_boost` for funding.
- Did the user reject old posts? Boost `recency`.
- Did the user prefer posts from people they follow? Boost `following_boost`.

The resulting lens is presented with slider positions visible and adjustable. The user names it and saves.

This method is best for users who cannot articulate what they want in words but know it when they see it.

### Method 6: Mind Map Builder -- 3D Weight Sphere (Desktop Power Users)

The Mind Map Builder becomes a **3D Weight Sphere** using `React Three Fiber` (Three.js for React) and `@react-three/drei`. This is NOT the default entry point -- it is expert/explain mode only, hidden behind an "Advanced" toggle as the PDF reference warned: "the graph exists but the user rarely sees it."

**3D Visualization Concept:**

Each of the 8 weight dimensions is a "star node" floating in 3D space around a central "My Feed DNA" core sphere.

```
Visual rules:
- Node SIZE     = weight value (0-3) -- bigger = more important
- Node GLOW     = current activity level -- brighter = more posts matching
- Node COLOR    = dimension category:
    WHO  dimensions (reputation, following_boost)  -> Blue
    WHAT dimensions (quality, category_boost)      -> Green
    WHEN dimensions (recency)                      -> Orange
    HOW  dimensions (engagement, diversity, serendipity) -> Purple
- Connection lines from center -> each node pulse with animated particles
```

**3D Animation Moments:**

| User Action | Animation |
|---|---|
| Open Mind Map | Stars float in from center with starburst effect (spring physics, 600ms) |
| Drag weight up | Star expands + particle burst + live preview updates (debounced 300ms) |
| Drag weight down | Star shrinks + dims + particles retract |
| Switch lens | Entire constellation morphs to new positions (spring interpolation, 800ms) |
| Apply template | All 8 stars simultaneously animate to template positions with cascade delay |
| "Why This Post?" mode | Post's matching dimension stars light up gold + connecting beam to post card |
| Serendipity > 0.5 | Stars gently orbit/wobble to visualize randomness |
| Diversity > 0.5 | Stars spread apart from each other visually |

**Node Structure (preserved from original plan):**

```
              [My Feed DNA]  <- central glowing sphere
             /      |      \       \
        [WHAT]    [WHO]   [WHEN]  [HOW]
        /   \     /   \    /   \   /  \
     [Wins] [Deep] [Net] [New] [Fresh][Cycle] [Surprise]
     cat    qual   fol  rep   rec   div  ser
```

**Technology Stack:**
- `@react-three/fiber` -- React renderer for Three.js
- `@react-three/drei` -- helpers (OrbitControls, Stars background, Html overlays)
- `framer-motion-3d` -- physics-based spring animations on 3D objects
- `leva` -- optional debug panel for testing weight values during development

**Mobile Fallback:** 3D is desktop-only (requires WebGL). On mobile/tablet, the Mind Map collapses to the Vibe Sliders panel automatically. No feature loss -- same 8 dimensions, different presentation.

**Performance Notes:**
- Max 8 animated nodes -- negligible GPU load
- WebGL canvas is isolated in a React Suspense boundary -- if WebGL unavailable, falls back to 2D React Flow gracefully
- Particle count per node capped at 50 -- works on integrated graphics

### Ranking of Methods by User-Friendliness

1. Template Gallery -- zero thinking required
2. 3-Question Quick Setup -- guided, 30 seconds
3. React to Posts Teaching Mode -- intuitive, visual
4. Vibe Sliders -- requires understanding of tradeoffs
5. AI Conversation Builder -- requires articulating preferences
6. Mind Map Builder -- requires conceptual understanding of dimensions

### NEW Input Method: "Steal This Lens" (Social Sharing)

Users can share their lens configuration. When someone shares a lens:
- A unique fingerprint URL is generated (e.g., `/lens/abc123`)
- Anyone with the link can preview the lens effect on their own feed
- One tap to "fork" it as their own (consuming one of their 5 custom lens slots)
- The original creator sees a count of how many people forked their lens

This creates "feed culture" -- trusted community members become feed curators. New users can onboard faster by picking a trusted lens instead of building from scratch.

---

## 6. The Scoring System Design

### Current System (What Exists)

The existing `calculate_trending_score()` in `app/api/utils/community.py` computes a single global score:

```
trending_score = (engagement_score + category_score + reputation_score + ai_score) * time_decay * daily_boost
```

Where:
- `engagement_score = likes * 3 + comments * 2 + bookmarks * 2`
- `category_score` = category weight (1.5 to 2.5)
- `reputation_score` = role weight + account age bonus
- `ai_score` = Groq LLM quality rating (0-10)
- `time_decay` = exponential decay with cosine daily cycle
- `daily_boost` = time-of-day multiplier (1.0-1.3)

This score is pre-computed every 15 minutes and stored on each post document as `trendingScore`.

### Feed Lens Scoring System (What's New)

The Feed Lens system does NOT replace the existing scoring. It adds a second, per-user scoring step.

**Layer 1: Component Scores (Pre-computed, Same for All Users)**

Instead of computing a single `trendingScore`, the system computes and caches 6 independent component scores for each post:

| Component | Formula | Range | Cached In |
|-----------|---------|-------|-----------|
| `engagement` | `likes * 3 + comments * 2 + bookmarks * 2`, normalized to 0-100 | 0-100 | Redis HSET |
| `recency` | Freshness based on age in hours: <=1h=100, <=6h=92, <=24h=80, <=48h=65, <=72h=50, else 30 | 0-100 | Redis HSET |
| `quality` | AI quality score (0-10) * 10 | 0-100 | Redis HSET |
| `reputation` | Author role + account age, normalized | 0-100 | Redis HSET |
| `category_match` | 100 if post category matches user's preferred categories, 50 otherwise | 0-100 | Redis HSET |
| `network` | 100 if author is followed by user, 50 if mutual connection, 0 if stranger | 0-100 | Per-request |

These are computed by the existing 15-minute Celery/APScheduler job (extended, not replaced) and stored in Redis as `post_scores:{post_id}` hash maps. The `network` score is the only one computed per-request because it depends on who is asking.

**Layer 2: User Weights (Stored per User)**

Each Feed Lens stores 8 weights:

```
{
  "engagement": 1.0,       // 0-3 range
  "recency": 1.0,          // 0-3 range
  "quality": 1.0,          // 0-3 range
  "reputation": 1.0,       // 0-3 range
  "category_boost": 1.0,   // 0-3 range
  "following_boost": 1.0,  // 0-3 range
  "diversity": 0.0,        // 0-1 range
  "serendipity": 0.0       // 0-1 range
}
```

**Layer 3: Personalized Score Calculation (Per-Request)**

The final score for a post, for a specific user with a specific lens, is:

```
personalized_score =
    (component_scores.engagement * lens.engagement) +
    (component_scores.recency * lens.recency) +
    (component_scores.quality * lens.quality) +
    (component_scores.reputation * lens.reputation) +
    (component_scores.category_match * lens.category_boost) +
    (component_scores.network * lens.following_boost) +
    (serendipity_noise * lens.serendipity)
```

Then, if `lens.diversity > 0`, a post-processing step applies diversity re-ranking:
- Group the top-N results by author and category
- If any author appears more than `ceil(3 * (1 - diversity))` times, demote excess posts
- If any category appears more than `ceil(5 * (1 - diversity))` times, demote excess posts

This is a simple weighted dot product followed by optional diversity capping. For 200 posts, this is pure Python math taking approximately 3ms. No database queries are needed because component scores come from Redis pipeline reads.

**Serendipity Implementation**

The `serendipity` weight (0-1) controls how much random noise is injected:
- `serendipity = 0`: perfectly deterministic ranking
- `serendipity = 0.5`: moderate randomization in the middle of the feed (top 5 posts remain stable, positions 6-20 get shuffled)
- `serendipity = 1.0`: significant randomization (only top 3 are stable)

The noise is implemented as: for each post at position `i` beyond the stability threshold, add `random.gauss(0, serendipity * 10)` to its score before final sorting. This is seeded with `hash(user_id + date)` so the same user sees the same "random" feed within a single day (preventing jarring re-shuffles on refresh).

### Real Time Syn Scoring Integration

Real Time Syn items already have 4 component scores (freshness, trust, impact, discussion). The Feed Lens maps to these:

| Lens Dimension | Maps to RT Syn Score |
|----------------|---------------------|
| recency | freshness_score |
| quality | trust_score |
| engagement | discussion_score |
| category_boost | impact_score (with channel-to-category mapping) |

The same weighted dot product applies, allowing users to control how RT Syn items are ranked alongside community posts.

---

## 6.5 Intent Mode -- Temporary Cross-System Priority Overlays

This section describes a feature layer not in the original reference plans.

### The Problem It Solves

A user says "I want Jobs to be my priority this week." This is a cross-system intent that spans:
- Community Posts category: `New Opportunities` + `Collab`
- RT Syn channel: `jobs`

A static lens weight change is permanent and abstract. What is needed is a **temporary, understandable, cross-system priority override**.

### What an Intent Mode Is

An Intent Mode is a named, time-bounded priority layer that sits ON TOP of the user's active lens. It does not replace the lens -- it temporarily amplifies specific dimensions across both Community Posts and RT Syn simultaneously.

### User Flow

```
User taps "Set Priority" button in feed header (next to lens indicator)
  -> Shows a grid of intent cards with icons:

  [Job Hunting]       [Funding Watch]     [Event Mode]
  [Learning]          [Networking]        [Market Intel]
  [Wins Only]         [Deep Research]     [Custom...]

User taps "Job Hunting"
  -> Dialog: "How long do you want this priority?"
    [Today]  [This Week]  [Until I turn it off]
  -> Activates immediately
```

### Feed Header When Intent Mode Is Active

```
Viewing via: My Morning Mix - Job Hunting  [Change] [x 3 days left]
```

### Intent Mode Definitions (8 Built-in Modes)

| Intent Mode | Community Post Boosts | RT Syn Channel Boosts | Lens Weight Overrides |
|---|---|---|---|
| Job Hunting | New Opportunities: 3.0, Collab: 2.5 | jobs: HIGH, funding: MEDIUM | following_boost +0.5 |
| Funding Watch | New Opportunities: 2.5, Milestones: 2.0 | funding: HIGH, market_signals: HIGH | reputation +0.5 |
| Event Mode | Event: 3.0 | startup_news: MEDIUM | recency +0.5 |
| Learning | Deep Talk: 2.5, Tools/Resources: 2.5 | technology_news: HIGH | quality +0.5 |
| Networking | Collab: 3.0, Event: 2.0 | jobs: MEDIUM | following_boost +1.0 |
| Market Intel | Deep Talk: 2.0, Milestones: 2.0 | market_signals: HIGH, funding: HIGH | reputation +0.5 |
| Wins Only | Wins: 3.0, Milestones: 2.5 | startup_news: HIGH | engagement +0.3 |
| Deep Research | Deep Talk: 3.0, Tools/Resources: 2.5 | technology_news: HIGH | quality +0.8, recency -0.5 |

**Custom Intent Mode:** User can name their own and select which categories/channels to boost.

### AI (Mistral) Natural Language Support

User types: "I'm job hunting this week" -- Mistral detects intent -- suggests "Job Hunting" mode for 7 days -- user confirms with one tap.

User types: "I want to focus on AI news and deep discussions" -- Mistral maps to: Deep Talk boost + technology_news RT Syn channel + Learning mode -- user reviews and confirms.

### Data Model Addition

The `feed_lenses` document gains a new field:

```json
{
  "active_intent_mode": {
    "mode_id": "job_hunting",
    "name": "Job Hunting",
    "emoji": "briefcase",
    "expires_at": "ISODate",
    "post_category_boosts": {"New Opportunities": 3.0, "Collab": 2.5},
    "rt_syn_channel_boosts": {"jobs": "HIGH", "funding": "MEDIUM"},
    "lens_weight_overrides": {"following_boost": 0.5}
  }
}
```

### Intent Mode Rules

1. Only one active Intent Mode at a time per user
2. Intent Mode overlays the lens -- it does NOT modify the stored lens weights permanently
3. Expires automatically at the set time -- user gets a notification: "Job Hunting mode ended. Back to My Morning Mix."
4. User can dismiss it early with the [x] button in the feed header
5. If an Intent Mode makes the feed too narrow (<5 posts), the same 70/30 blend fallback applies

### New Redis Key

`feed_lens:intent:{user_id}` -- Hash, TTL = intent mode duration -- stores mode params for fast serving

---

## 7. Architecture Design

### 3-Layer Architecture

```
LAYER 1: DATA INGESTION
+--------------------+     +---------------------+
| Implicit Signals   |     | Explicit Weights    |
| (dwell/save/skip)  |     | (wizard/sliders/AI) |
+--------+-----------+     +---------+-----------+
         |                           |
         v                           v
+--------+-----------+     +---------+-----------+
| MongoDB:           |     | MongoDB:            |
| user_engagement    |     | feed_lenses         |
| _signals           |     |                     |
+--------+-----------+     +---------+-----------+
         |                           |
         +----------+  +------------+
                    |  |
                    v  v
LAYER 2: PROCESSING (Celery / APScheduler)
+---------------------------------------------------+
| Every 15 min: precompute_post_component_scores()  |
|   - Reads all active posts                        |
|   - Computes 6 component scores per post          |
|   - Writes to Redis: post_scores:{post_id} HSET  |
+---------------------------------------------------+
| Daily at 3am UTC: aggregate_user_signals()        |
|   - Reads user_engagement_signals (30 days)       |
|   - Detects drift patterns                        |
|   - If auto_evolve enabled: nudges lens weights   |
|   - Stores updated weights in MongoDB + Redis     |
+---------------------------------------------------+
                    |
                    v
LAYER 3: SERVING (FastAPI)
+---------------------------------------------------+
| GET /api/posts?filter=lens                        |
|   1. Active lens from Redis HGETALL (~1ms)        |
|   2. Candidate post IDs from MongoDB query        |
|   3. Component scores via Redis pipeline (~5ms)   |
|   4. Scoring loop: 200 posts, pure Python (~3ms)  |
|   5. Diversity re-ranking if enabled (~1ms)       |
|   6. Return top per_page posts                    |
|   Total overhead: ~11ms above baseline query      |
+---------------------------------------------------+
```

### Component Interaction Flow

**When a user creates/edits a lens:**

1. Frontend sends lens parameter object to `POST /api/feed-lens`
2. Backend validates all weights are within bounds (0-3 for main, 0-1 for diversity/serendipity)
3. Backend stores in MongoDB `feed_lenses` collection
4. Backend writes active lens to Redis `feed_lens:active:{user_id}` (HSET, 7-day TTL)
5. Backend returns the lens object + 4 preview posts

**When a user loads their feed with an active lens:**

1. `GET /api/posts?filter=lens` hits the existing posts endpoint with a new filter type
2. Dependency injection reads active lens from Redis (HGETALL, ~1ms)
3. If no active lens in Redis, falls back to MongoDB, re-populates Redis
4. If no lens at all, uses platform default (all weights = 1.0)
5. Standard MongoDB query fetches candidate posts (200, using existing indexes)
6. Redis pipeline fetches component scores for all 200 posts (~5ms)
7. Scoring loop computes personalized scores (~3ms)
8. Diversity/serendipity post-processing (~1ms)
9. Return top `per_page` posts with standard pagination

**When the preview panel needs a sample:**

1. Frontend sends current slider values to `GET /api/feed-lens/preview`
2. Backend reads a cached sample of 50 recent posts from Redis (refreshed every 15 min)
3. Applies the lens scoring to the sample
4. Returns top 4 posts
5. Total latency: ~10ms (no MongoDB hit)

### Integration with Existing Endpoints

The Feed Lens does NOT create a new feed endpoint. It extends the existing `GET /api/posts` endpoint:

- Current filter types: `trending`, `recent`, `my_posts`, `feed`, `wins`, `engagement`, `popular`, `oldest`, `most_liked`, `most_commented`
- New filter type: `lens` -- activates Feed Lens scoring
- The frontend WarRoom sends `filter=lens` when a custom lens is active, otherwise sends the regular filter type
- This means all existing feed infrastructure (caching, fallbacks, pagination, Socket.IO updates) continues to work

### New API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/feed-lens` | List user's lenses (returns array of lens objects) |
| POST | `/api/feed-lens` | Create new lens (returns lens + preview) |
| PUT | `/api/feed-lens/{lens_id}` | Update lens weights/filters |
| DELETE | `/api/feed-lens/{lens_id}` | Delete a custom lens (not default) |
| POST | `/api/feed-lens/{lens_id}/activate` | Set as active lens |
| GET | `/api/feed-lens/preview` | Preview with temporary weights (no save) |
| GET | `/api/feed-lens/templates` | List system templates |
| POST | `/api/feed-lens/from-template/{template_id}` | Fork a template |
| POST | `/api/feed-lens/from-questions` | Create from 3-question wizard |
| POST | `/api/feed-lens/from-reactions` | Create from teaching mode reactions |
| POST | `/api/feed-lens/from-natural-language` | AI translation of natural language (uses Mistral medium-2505 via Azure endpoint) |
| GET | `/api/feed-lens/shared/{fingerprint}` | Get a shared lens for preview |
| POST | `/api/feed-lens/{lens_id}/share` | Generate share link |
| POST | `/api/feed-lens/signal` | Record implicit engagement signal |

---

## 8. Data Model Design

### MongoDB Collection: `feed_lenses`

Each document represents one saved lens for one user:

```
{
  "_id": ObjectId,
  "user_id": "firebase_uid_123",
  "name": "My Morning Mix",
  "emoji": "telescope",
  "is_default": false,                    // true only for system default
  "is_system_template": false,            // true for the 11 templates
  "forked_from": null,                    // lens_id if forked from another
  "created_at": ISODate,
  "updated_at": ISODate,
  "last_used_at": ISODate,
  "usage_count": 24,
  "version": 3,
  "weights": {
    "engagement": 1.0,
    "recency": 0.8,
    "quality": 1.5,
    "reputation": 1.2,
    "category_boost": 2.0,
    "following_boost": 0.6,
    "diversity": 0.3,
    "serendipity": 0.1
  },
  "filters": {
    "topics": ["Funding", "Product Launches"],   // empty = all
    "include_new_voices": true,
    "exclude_categories": [],
    "min_quality_score": 0                       // 0-10, 0 = no filter
  },
  "creation_method": "quick_setup",              // quick_setup, sliders, ai, teaching, template, shared
  "auto_evolve": false,                          // whether implicit signals adjust weights
  "version_history": [
    {
      "version": 2,
      "weights": { ... },
      "changed_at": ISODate
    }
  ]
}
```

**Indexes needed:**
- `(user_id, 1)` -- find all lenses for a user
- `(user_id, 1, is_default, 1)` -- find active/default lens
- `(is_system_template, 1)` -- list templates
- `(shared_fingerprint, 1)` unique sparse -- shared lens lookup

### MongoDB Collection: `user_engagement_signals`

Stores implicit engagement signals for the auto-evolve feature:

```
{
  "_id": ObjectId,
  "user_id": "firebase_uid_123",
  "post_id": "post_objectid_str",
  "signal_type": "dwell",                      // dwell, like, bookmark, skip, hide
  "signal_value": 8.5,                         // seconds for dwell, 1/-1 for like/skip
  "post_category": "Wins",
  "post_author_id": "author_uid",
  "is_following_author": true,
  "post_age_hours": 4.2,
  "post_engagement_level": 45,                 // normalized 0-100
  "created_at": ISODate,
  "lens_id": "lens_objectid_str"               // which lens was active
}
```

**Indexes needed:**
- `(user_id, 1, created_at, -1)` -- recent signals for a user
- `(user_id, 1, signal_type, 1, created_at, -1)` -- signals by type
- TTL index on `created_at` at 30 days -- auto-delete old signals

### Redis Key Strategy

| Key Pattern | Type | TTL | Content |
|-------------|------|-----|---------|
| `feed_lens:active:{user_id}` | Hash | 7 days | Active lens weights (8 fields) |
| `feed_lens:session:{user_id}:{session_id}` | String | session lifetime | Lens ID for session safety |
| `post_scores:{post_id}` | Hash | 2 hours | 6 component scores |
| `feed_lens:preview:{user_id}:{hash}` | String (JSON) | 5 min | Cached preview result |
| `lens_feed:{user_id}:{lens_id}:p1` | String (JSON) | 15 min | Pre-ranked page 1 |
| `feed_lens:sample_posts` | String (JSON) | 15 min | 50 recent posts for preview |
| `feed_lens:templates` | String (JSON) | 24 hours | System template definitions |
| `feed_dna:{fingerprint}` | Hash | 30 days | Shared lens config |

---

## 9. Real-Time Syn Integration

> **WARNING -- PREREQUISITE: Critical Bug Must Be Fixed First**
>
> `FASTAPI_COMMUNITY/app/db/mongo.py` declares 9 `realtime_syn_*` collection globals
> but `connect()` never assigns them to actual database collections. This single bug
> means ALL Real Time Syn MongoDB operations silently fail.
>
> The 9 missing assignments that must be added inside `connect()` are:
> ```
> realtime_syn_items          = db["realtime_syn_items"]
> realtime_syn_entities       = db["realtime_syn_entities"]
> realtime_syn_sources        = db["realtime_syn_sources"]
> realtime_syn_runs           = db["realtime_syn_runs"]
> realtime_syn_metrics        = db["realtime_syn_metrics"]
> realtime_syn_rendered_posts = db["realtime_syn_rendered_posts"]
> realtime_syn_dedupe         = db["realtime_syn_dedupe"]
> realtime_syn_failures       = db["realtime_syn_failures"]
> realtime_syn_user_state     = db["realtime_syn_user_state"]
> ```
>
> **Feed Lens RT Syn integration CANNOT be implemented until this bug is fixed.
> This is the first action item before any Feed Lens work begins.**

### The Challenge

Real Time Syn items are a different data type from community posts. They come from external news sources (GNews, Guardian, DuckDuckGo, etc.), have different score dimensions (freshness, trust, impact, discussion), and are stored in `realtime_syn_items` instead of `posts`.

In the WarRoom, RT Syn items already appear in a separate tab (`realtime_syn`). Feed Lens must work when this tab is active too.

### The Solution

**Score Mapping:** RT Syn's 4 existing scores map directly to Feed Lens dimensions:

| RT Syn Score | Feed Lens Dimension | Rationale |
|---|---|---|
| freshness_score (0-100) | recency | Both measure how new the content is |
| trust_score (0-100) | quality | Both measure content reliability |
| discussion_score (0-100) | engagement | Both measure engagement potential |
| impact_score (0-100) | reputation + category_boost | Impact combines source authority and topic importance |

**Network dimension for RT Syn:** Since RT Syn items don't have a "following" relationship, the `following_boost` weight is ignored for RT Syn items. Instead, `following_boost > 2.0` is reinterpreted as "boost items from startups the user has previously engaged with" (using `realtime_syn_user_state` click/bookmark data).

**Channel-to-Category mapping:** RT Syn channels map to Barise post categories for `category_boost`:

| RT Syn Channel | Maps to Category |
|---|---|
| funding | New Opportunities |
| startup_failures, shutdowns | Deep Talk |
| layoffs | Deep Talk |
| product_launches | Tools/Resources |
| jobs | New Opportunities |
| startup_news | Wins |
| technology_news | Tools/Resources |
| market_signals | Deep Talk |

**Mixed Feed Mode (Future):** Currently, RT Syn and community posts live in separate tabs. A future enhancement could merge them into a single Feed Lens-ranked feed. The component score architecture supports this because both post types produce the same 6-dimension score vector.

### Unified Intent Mapping -- Category-to-Channel Cross-Reference

This table is the "Rosetta Stone" that allows Feed Lens and Intent Modes to work across both Community Posts and RT Syn with shared intent:

| User Intent / Theme | Community Post Categories | RT Syn Channels | Notes |
|---|---|---|---|
| Jobs / Career | New Opportunities, Collab | jobs | Highest cross-system overlap |
| Funding / Investment | New Opportunities, Milestones | funding | Also check market_signals |
| Events | Event | startup_news (when event-related) | RT Syn has no dedicated events channel |
| Learning / Education | Deep Talk, Tools/Resources | technology_news | Broadest RT Syn match |
| Networking | Collab, Event | jobs (networking section) | Partial RT Syn overlap |
| Market News | Deep Talk, Milestones | market_signals, funding | RT Syn stronger here |
| Product / Tech | Tools/Resources, Wins | product_launches, technology_news | Good cross-system match |
| Cybersecurity | Deep Talk, Tools/Resources | technology_news | RT Syn may have cyber channel |
| Startup News | Wins, Milestones, New Opportunities | startup_news, funding | Very strong cross-system match |
| Community Wins | Wins, Milestones | startup_news | Partial RT Syn match |

This mapping is stored as a config object in the backend (not hardcoded per-request) and is used by:
1. Intent Mode to know which categories/channels to boost
2. Mistral AI Builder to translate "show me job posts" to the right category + channel combination
3. The "Why This Post?" transparency layer to explain cross-system matches

---

## 10. Security Design

### No-Code Constraint Enforcement

This is the most critical security requirement. Users must NEVER be able to inject executable code.

**How it's enforced:**

1. **Parameter validation at API boundary:** Every lens creation/update request is validated by Pydantic schemas with strict constraints:
   - Weight values: `float`, `ge=0.0`, `le=3.0` (or `le=1.0` for diversity/serendipity)
   - Filter topics: `List[str]` where each string must be in an allowlist of known categories
   - Name: `str`, `max_length=50`, stripped, HTML-escaped
   - No arbitrary string fields that could be eval'd

2. **No dynamic query construction from user input:** The lens weights are used in Python math (`score += component * weight`), never in database queries or string interpolation

3. **Natural language input sanitization:** The AI builder receives user text but the output is always the same bounded parameter object. The LLM prompt explicitly constrains output to JSON with the 8 weight fields. Any response that doesn't parse to valid weights is rejected.

4. **Template immutability:** System templates are read-only. Users can fork but never modify the originals.

### Session Isolation (User Switching Safety)

**Problem:** If two users share a device (e.g., family tablet), switching accounts must not leak one user's lens to another.

**Solution:**

1. The active lens is stored in Redis with a compound key: `feed_lens:session:{user_id}:{session_token}`
2. When the auth token changes (login/logout), the session key changes
3. On logout, the frontend clears all feed cache refs (`feedCache.current` in WarRoom.tsx)
4. The `get_current_user()` dependency already re-validates the token on every request, so a stale session cannot access another user's lens
5. Redis TTL on session keys ensures cleanup even if explicit logout doesn't happen

**Edge case -- same browser, two tabs, different accounts:** The auth context (`Authcontext.tsx`) already handles this via `useAuth()` hook. When the token changes in one tab, the other tab's next API call will get a 401 and redirect to login.

### Rate Limiting

Lens operations are rate-limited to prevent abuse:
- Lens creation: 10 per hour per user
- Lens preview: 60 per minute per user (supports rapid slider adjustment)
- Signal recording: 120 per minute per user (dwell events fire frequently)

These limits use the existing Redis-based rate limiter in `app/core/rate_limiter.py`.

### Data Privacy

- Feed Lens configurations are private to each user (queries always filter by `user_id`)
- Shared lenses expose only the weight configuration, never personal data
- Engagement signals are auto-deleted after 30 days via MongoDB TTL index
- No cross-user data leakage: the scoring loop operates on one user's lens at a time

---

## 11. Scaling Design

### Why This Scales

The key insight is: **post component scores are the same for all users.** The per-user step is a lightweight dot-product, not a database scan.

**Breakdown of per-request cost:**

| Step | Operation | Latency | Scales With |
|------|-----------|---------|-------------|
| 1 | Read active lens from Redis | ~1ms | Constant (1 key read) |
| 2 | Fetch candidate post IDs from MongoDB | ~15-50ms | Existing (unchanged from current feed) |
| 3 | Fetch component scores from Redis | ~5ms | Linear with post count (pipeline, ~200 posts) |
| 4 | Scoring loop (dot product) | ~3ms | Linear with post count (pure Python math) |
| 5 | Diversity re-ranking | ~1ms | Linear with result size |
| **Total lens overhead** | | **~10ms** | |

For comparison, the existing feed query alone takes 15-50ms (MongoDB). Feed Lens adds ~10ms on top.

**At 10,000 concurrent users, each with a different lens:**
- MongoDB load is unchanged (same post queries)
- Redis load: 10,000 lens reads + 10,000 * 200 score reads = 2,010,000 Redis ops/request-cycle. At 1 request/second/user, that's ~2M Redis ops/sec. Azure Redis Premium tier handles 100K+ ops/sec on a single shard. With Redis pipeline batching (read 200 scores in 1 round-trip), actual network calls are ~10,000/sec. Well within limits.

**Pre-computation cost:**
- The 15-minute Celery job already processes all posts in batches of 500
- Adding 6 component score calculations per post adds ~50% compute time to the existing job
- Writing to Redis HSET is ~0.1ms per post
- For 100,000 posts: ~10 seconds of additional batch processing time every 15 minutes

### Caching Strategy

**Multi-tier caching prevents redundant computation:**

1. **Redis (hot cache):** Component scores, active lenses, preview results, page-1 pre-ranked feeds
2. **In-memory (process cache):** System templates (never change), recent preview sample (refreshed with batch job)
3. **MongoDB (persistent cache):** Lens configurations, signal history, version history
4. **Frontend (client cache):** The WarRoom `feedCache.current` ref already caches per-filter-tab. Feed Lens adds a cache entry keyed by `lens:{lens_id}`.

**Cache invalidation:**
- Post scores: 2-hour TTL, refreshed every 15 minutes by batch job
- Active lens: 7-day TTL, refreshed on every lens edit/switch
- Preview results: 5-minute TTL, keyed by hash of slider values
- Page-1 pre-ranked: 15-minute TTL, invalidated when lens changes

### Graceful Degradation

If Redis is unavailable:
1. Active lens falls back to MongoDB read (~5ms instead of ~1ms)
2. Component scores fall back to the existing `trendingScore` field on each post document (no personalization, but feed still works)
3. Preview becomes unavailable (returns empty with a message)
4. The feed never breaks -- it degrades to the existing trending algorithm

---

## 12. Problem Resolution

### Problem 1: User Understanding

**Challenge:** Users must immediately understand what Feed Lens does.

**Solution:**
- The onboarding tooltip on first visit: "Your feed is powered by a lens. The default lens shows what's trending. You can create your own lens to see what matters most to you."
- The feed header always shows the active lens name, making it visible and concrete
- Templates with descriptive names ("Investor Eye," "Discovery Mode") communicate purpose without explanation
- The Quick Setup wizard uses questions about outcomes ("What excites you?"), not technical parameters

### Problem 2: Non-Technical Users

**Challenge:** Someone with zero technical knowledge must be able to set their own algorithm.

**Solution:**
- Layer 0 (do nothing) works perfectly
- Layer 1 (pick a template) requires one tap and zero technical knowledge
- Layer 2 (answer 3 questions) uses plain English with visual cards, no sliders or numbers
- The Vibe Sliders use bipolar labels ("Hidden Gems" vs "Most Popular") that describe outcomes, not mechanisms
- The teaching mode ("Love it / Not for me") is the most intuitive of all -- users just react to posts they see

### Problem 3: No Code-Based Input

**Challenge:** Users must never write code. This is both a UX and security requirement.

**Solution:**
- There is literally no text input field anywhere that feeds into query construction
- The AI builder accepts natural language but outputs only bounded parameters (never code)
- All weights are numeric sliders with hard min/max bounds
- All filters are pick-lists from pre-approved values
- The backend validates every field against a Pydantic schema before storing

### Problem 4: Selection Process Based on Posts

**Challenge:** The algorithm must be based on posts, not abstract concepts.

**Solution:**
- The live preview panel shows 4 real posts for every slider configuration
- The teaching mode is entirely post-based (react to 12 real posts)
- The inline "Tune my lens from this post" feature ties every adjustment to a concrete example
- Template descriptions include example outcomes ("See posts like [real example]")

### Problem 5: Per-User Isolation

**Challenge:** Every user has their own algorithm; the system must handle this at scale.

**Solution:**
- Lenses are stored per-user in MongoDB with `user_id` index
- Active lens cached in Redis per-user with `feed_lens:active:{user_id}` key
- The scoring loop is stateless -- it reads one user's lens, scores, and returns. No shared mutable state.
- The pre-computed component scores are user-independent. Only the weight multiplication is per-user.
- See Scaling Design section for detailed capacity analysis

### Problem 6: No Confusion on User Switching

**Challenge:** When users switch accounts on the same device, no cross-contamination.

**Solution:**
- Redis key includes both `user_id` and `session_token`
- Frontend feed cache is cleared on logout (the `Authcontext.tsx` already triggers re-renders on auth state change)
- The feed header always shows the current user's active lens name -- if it says "Barise Default" after switching, the user knows it's a fresh state
- The `get_current_user()` dependency validates the Firebase JWT on every request, making it impossible to serve one user's lens to another

### Problem 7: Default Algorithm

**Challenge:** Platform default must always exist; user's custom lens overwrites display but default remains.

**Solution:**
- The platform default lens is a system record with `is_default: true` that cannot be deleted or modified by users
- When no custom lens is active, the system uses the default (all weights = 1.0, equivalent to the existing trending algorithm)
- Every user has an implicit default lens -- it's not stored per-user, it's a singleton system record
- The Lens Picker always shows "Barise Default" as the first card, with a lock icon indicating it can't be removed
- Switching back to default is one tap

### Problem 8: Failure Handling

**Challenge:** If a user's algorithm returns no/few results, handle gracefully.

**Solution:**
- **Blending rule:** If a custom lens returns fewer than 5 posts for a page, the system blends: 70% platform default results + 30% custom lens results
- **Toast notification:** "Your lens found fewer posts than usual. We're mixing in some trending posts to keep your feed full."
- **Never empty:** The platform default feed always has posts (it's the existing trending algorithm). If even the default returns empty (DB outage), the existing multi-level fallback (in-memory cache, persisted trending cache, stale cache) kicks in
- **Automatic lens health check:** If a lens consistently returns <5 posts for 3 consecutive loads, the system shows a suggestion: "Your lens might be too narrow. Want to broaden it?"

### Problem 9: Scaling

**Challenge:** Must work for many users with many different lenses simultaneously.

**Solution:** See Section 11 (Scaling Design). Summary:
- Pre-computed component scores eliminate per-user DB scans
- Redis pipeline reads keep per-request overhead under 10ms
- The architecture adds ~10ms latency on top of existing feed queries
- Azure Redis Premium handles the concurrent load
- Graceful degradation to existing trending algorithm if Redis fails

### Problem 10: UI Design -- Making It Intuitive

**Challenge:** Making algorithm-setting intuitive without requiring logical thinking.

**Solution:**
- Progressive disclosure ensures most users never see complexity
- Bipolar slider labels describe outcomes, not parameters
- Live preview makes every change tangible
- Templates provide instant gratification
- The cooking metaphor ("recipe for your feed") makes the concept accessible
- Post-based teaching ("Love it / Not for me") requires zero abstraction

### Problem 11: Input Methods

**Challenge:** How to collect algorithm preferences from users in various ways.

**Solution:** 6 input methods ranked from simplest to most powerful:
1. Template Gallery (one tap)
2. 3-Question Quick Setup (30 seconds)
3. React to Posts Teaching Mode (2 minutes)
4. Vibe Sliders Panel (refinement)
5. AI Conversation Builder (natural language)
6. Mind Map Builder (desktop power users)

Plus the social "Steal This Lens" sharing method for community-driven onboarding. See Section 5 for full details on each method.

---

## 13. New Ideas & Innovations

### 1. "Lens Analytics" Dashboard

Show users how their lens is performing compared to the default:
- "Your lens surfaced 12 posts you bookmarked this week vs 3 with the default"
- "You're spending 40% more time per post with your lens"
- This creates a feedback loop that encourages lens refinement

### 2. "Lens of the Week" Community Feature

Each week, the platform highlights a user-created lens that got the most forks. This:
- Creates social proof around the feature
- Provides free onboarding for new users
- Incentivizes lens creation and sharing
- Can be featured in the WarRoom sidebar

### 3. "Context Lenses" -- Time-Based Auto-Switching

Users can set rules like:
- "Use 'Morning Digest' lens before 10am"
- "Switch to 'Event Focus' lens on event days"
- "Use 'Deep Diver' on weekends"

This is stored as a simple schedule on the lens document. The backend checks the schedule on each feed request and auto-activates the matching lens. No complex cron logic -- just time-of-day matching.

### 4. "Why This Post?" Transparency Layer

On every post in a lens-filtered feed, a small info icon shows:
- Which lens dimensions caused this post to rank high
- A natural language explanation: "This post appeared because it's from someone you follow (high network score) and it's a recent Win (high category match)"
- This addresses the EU DSA transparency requirements and builds user trust

### 5. "Lens Drift Detection" -- Implicit Evolution Guard

Over time, users' preferences change but their lens stays static. The system watches engagement signals and detects drift:
- If a user consistently skips posts that their lens ranks highly, the system nudges: "Your feed preferences may have changed. Want to re-tune your lens?"
- If `auto_evolve` is enabled on a lens, the system gently adjusts weights based on 30-day signal analysis (capped at +/- 0.3 per dimension per cycle to prevent sudden changes)
- Users see a notification: "Your lens evolved slightly based on your recent activity. [See changes] [Undo]"

### 6. "Post Score Breakdown" for Content Creators

Authors can see how their posts score across the 6 component dimensions. This helps creators understand what makes their posts visible:
- "Your post scored high on quality (8/10) but low on engagement (12/100). Consider asking a question to boost discussion."
- This is a value-add for the creator community and drives higher-quality content

### 7. Onboarding Integration with Baina (AI Matching)

The existing Baina onboarding flow (`src/components/Ai_matching/`) collects user preferences (role, industries, experience level). When a new user completes Baina onboarding:
- The system auto-generates an initial Feed Lens based on their role and interests
- An investor gets "Founder Intel" as a suggested starting lens
- A founder gets "Trend Surfer" as a suggestion
- This eliminates the cold-start problem for the feed

---

## 14. What Fits in FASTAPI_COMMUNITY vs. What's New

### Existing Code That Can Be Extended

| Component | File | What to Extend |
|-----------|------|---------------|
| Post scoring | `app/api/utils/community.py` | `calculate_trending_score()` must be split into 6 component scores instead of one composite |
| Feed endpoint | `app/api/routes/community_routes.py` | `get_posts()` gains a new `filter_type == "lens"` branch |
| Feed pagination | `app/api/utils/feed_pagination.py` | Works as-is for lens-filtered feeds |
| Batch enrichment | `app/api/utils/ideas.py` | `batch_enrich_ideas()` pattern reused for batch scoring |
| Scheduler | `app/core/scheduler.py` | New job: `precompute_post_component_scores` (replaces/extends trending job) |
| Redis client | `app/db/redis.py` | Used as-is for new key patterns |
| Auth system | `app/api/deps.py` | `get_current_user()` used as-is; lens endpoints need auth |
| WarRoom frontend | `src/components/Community/pages/WarRoom.tsx` | Feed header indicator, filter tab extension, feedCache lens entry |
| shadcn/ui components | `src/components/ui/slider.tsx`, `dialog.tsx`, `sheet.tsx`, etc. | Used directly for lens editor UI |
| RT Syn scoring | `app/services/realtime_syn/scoring.py` | Component scores already exist; mapping to lens dimensions |
| RT Syn routes | `app/api/routes/realtime_syn_routes.py` | `list_realtime_syn_items()` gains lens-based sorting |

### Entirely New Components

| Component | Location | Description |
|-----------|----------|-------------|
| Feed Lens API routes | `app/api/routes/feed_lens_routes.py` | CRUD for lenses, preview, templates, sharing |
| Feed Lens schemas | `app/api/schemas/feed_lens.py` | Pydantic models for lens CRUD and validation |
| Feed Lens scoring engine | `app/api/utils/feed_lens_scoring.py` | Weighted dot product, diversity re-ranking, serendipity noise |
| Feed Lens service | `app/services/feed_lens_service.py` | Business logic: creation from questions/reactions/AI, sharing, evolution |
| Component score pre-computation | `app/celery_tasks/feed_lens_tasks.py` | Batch job to compute and cache component scores in Redis |
| Signal recording | `app/api/utils/feed_lens_signals.py` | Implicit signal collection and storage |
| Lens Editor UI | `src/components/Community/components/FeedLens/LensEditor.tsx` | Full-screen modal with Quick Setup, Sliders, Templates tabs |
| Lens Picker UI | `src/components/Community/components/FeedLens/LensPicker.tsx` | Bottom sheet / side panel for switching lenses |
| Lens Preview | `src/components/Community/components/FeedLens/LensPreview.tsx` | Live 4-post preview component |
| Feed Header Indicator | `src/components/Community/components/FeedLens/LensIndicator.tsx` | "Viewing via: ..." bar below filter tabs |
| Template Gallery | `src/components/Community/components/FeedLens/TemplateGallery.tsx` | Scrollable template card grid |
| Teaching Mode | `src/components/Community/components/FeedLens/TeachingMode.tsx` | 12-post reaction flow |
| AI Builder | `src/components/Community/components/FeedLens/AIBuilder.tsx` | Chat interface for natural language |
| Inline Tune Control | `src/components/Community/components/community/PostCard.tsx` | "Tune my lens" option in post menu |
| MongoDB collection | `community_db.feed_lenses` | New collection for lens storage |
| MongoDB collection | `community_db.user_engagement_signals` | New collection for implicit signals |

### What Does NOT Change

- The existing trending score calculation continues to work for the platform default
- The existing filter tabs (trending, realtime_syn, recent, wins, engagement) remain unchanged
- The existing Socket.IO real-time post delivery continues to work
- The existing pagination (cursor and offset) continues to work
- The existing Celery task infrastructure is extended, not replaced
- Server1_FastApi and server3 are not modified
- The auth system is not modified

---

## Appendix A: Referenced Research

- [Algorithmic Choice with Custom Feeds - Bluesky](https://bsky.social/about/blog/7-27-2023-custom-feeds)
- [Designing Usable Controls for Customizable Social Media Feeds](https://arxiv.org/html/2509.19615v1)
- [BONSAI: Intentional and Personalized Social Media Feeds](https://arxiv.org/html/2509.10776v2)
- [Mapping the Design Space of Teachable Social Media Feed Experiences](https://dl.acm.org/doi/fullHtml/10.1145/3613904.3642120)
- [User Control in Recommender Systems](https://web-ainf.aau.at/pub/jannach/files/Conference_EC_Web_2016.pdf)
- [Letting Users Choose Recommender Algorithms](https://md.ekstrandom.net/pubs/MultiRecs-Author.pdf)
- [Bluesky feed builder Graze raises $1M](https://techcrunch.com/2025/04/16/bluesky-feed-builder-graze-raises-1m-rolls-out-ads/)
- [EU Digital Services Act Article 27](https://www.eu-digital-services-act.com/Digital_Services_Act_Article_27.html)
- [Beyond clicks: dwell time for personalization](https://www.semanticscholar.org/paper/Beyond-clicks:-dwell-time-for-personalization-Yi-Hong/86e042df57619af7916b4caaa74386c2cc3f2fd1)
- [How does serendipity affect diversity in recommender systems?](https://link.springer.com/article/10.1007/s00607-018-0687-5)
- [Leveraging Dwell Time on LinkedIn Feed](https://www.linkedin.com/blog/engineering/feed/leveraging-dwell-time-to-improve-member-experiences-on-the-linkedin-feed)
- [Real-Time Personalization with Redis](https://redis.io/blog/real-time-personalization-for-retail/)
- [FastAPI and Redis Tutorial](https://redis.io/learn/develop/python/fastapi)
- [Algorithmic Freedom: How Bluesky Gives Users Control](https://hackernoon.com/algorithmic-freedom-how-bluesky-gives-users-control-over-their-feeds)
- [Netflix Personalization History](https://gibsonbiddle.medium.com/a-brief-history-of-netflix-personalization-1f2debf010a1)
- [Gobo: Exploring User Control of Invisible Algorithms](https://www.cs.unc.edu/~gaikwad/assets/publications/cscw-gobo.pdf)

## Appendix B: Reference Plans Incorporated

This document synthesizes and extends concepts from three reference plans provided by the project owner:

1. **PDF Reference** ("User-Selectable Feed Algorithms for Community Posts") -- Provided the "Feed Recipe" framing, 4 input channels concept, safety model, scaling constraints, and community-building extensions
2. **Reference Plan 2** ("Feed Lens Core Concept") -- Provided the lens metaphor, 5 input methods, UX card design, storage approach, scoring formula concept, and failure handling rules
3. **Reference Plan 3** ("WarRoom Implementation Plan") -- Provided the 8 weight dimensions, 11 system templates, Mind Map builder concept, Redis key strategy, 3-layer architecture, and the Real Time Syn bug identification

---

*This document is a complete idea and architecture design. It does not contain implementation code. The next step is implementation planning, which should be done in a separate document once this design is reviewed and approved.*

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-03-26 | Initial research and architecture design |
| 1.1 | 2026-03-26 | Added: Mistral AI integration (replacing Groq for Feed Lens AI chat), RT Syn mongo.py bug prerequisite warning, 3D Mind Map animation (React Three Fiber Weight Sphere), Intent Mode feature layer (Section 6.5), Unified category-to-channel cross-reference mapping |
