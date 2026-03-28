---
name: Barise Platform Architecture
description: Full architecture of all 4 Barise platform components - FASTAPI_COMMUNITY, server3, Server1_FastApi, lliveupdatedstreaming frontend
type: project
---

The Barise platform is a multi-server startup community platform with 4 main components:

**FASTAPI_COMMUNITY** (Primary community backend - FastAPI + Motor + Redis + Celery)
- Handles: Posts, Ideas, Comments, Follows, Notifications, Events, Circles, Real Time Syn, Search, Reports
- DB: MongoDB (community_db namespace), Redis for caching/websockets
- Existing feed/scoring: `calculate_trending_score()` in `app/api/utils/community.py` uses engagement * time_decay * category_weight * reputation * AI_quality * daily_boost
- Feed filters: trending, recent, my_posts, wins, engagement, realtime_syn, popular, oldest, most_liked, most_commented
- Scheduler: APScheduler runs trending score updates every 15 min, Real Time Syn syncs on configurable interval
- Real Time Syn: News aggregation from multiple providers (GNews, Guardian, DuckDuckGo, etc.), scored by freshness/trust/impact/discussion
- Auth: Firebase JWT tokens, Bearer header or cookie

**Why:** This is the core server where Feed Lens logic must live.
**How to apply:** Any feed personalization work targets this server's `/api/posts` and `/api/realtime-syn` endpoints.

**lliveupdatedstreaming** (Frontend - React + Vite + TypeScript + Tailwind + shadcn/ui)
- WarRoom.tsx is the main feed page with filter tabs: trending, realtime_syn, recent (my posts), wins, engagement
- Uses cursor-based and offset-based pagination with feedCache refs
- Socket.IO for real-time post updates
- Rate limiter utility for API calls
- UI library: shadcn/ui components (Button, Card, Slider, Dialog, etc. all present)

**server3** (Chat/messaging backend - FastAPI)
- Handles: Chat, WebSocket connections, file uploads, push notifications
- Independent from community feed logic

**Server1_FastApi** (Business tools backend - FastAPI)
- Handles: Business plans, SWOT, GTM, Pitch analysis, User profiles, Payments, Matching
- Profile routes store user preferences (role, industries, skills, etc.)
- Has its own Redis and MongoDB connections
