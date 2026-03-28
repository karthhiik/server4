---
name: Feed Lens Feature Research
description: Research findings for the Feed Lens (user-selectable feed algorithm) feature - scoring system, UX patterns, architecture decisions, v1.1 updates
type: project
---

Feed Lens is a planned feature allowing users to set their own feed algorithm via visual controls (never code). Architecture document is at `docs/FEED_LENS_ARCHITECTURE.md` (v1.1).

**Key architectural decisions from analysis:**
- Post scores are pre-computed by Celery/APScheduler every 15 min and stored on each post document (trendingScore field)
- Feed Lens must add a per-user weighted dot-product step at query time, NOT change the pre-computation
- Redis already exists for caching; Feed Lens adds keys for active lenses and post component scores
- MongoDB `community_db.feed_lenses` and `community_db.user_engagement_signals` are the two new collections needed
- The WarRoom.tsx filter tabs architecture (trending/realtime_syn/recent/wins/engagement) must be extended with a "Feed Lens" indicator

**v1.1 additions (2026-03-26):**
- AI Conversation Builder uses Mistral medium-2505 (Azure endpoint), NOT Groq. Groq stays only for existing AI quality scoring on posts.
- PREREQUISITE BUG: `FASTAPI_COMMUNITY/app/db/mongo.py` connect() never assigns 9 realtime_syn_* collection globals. Must be fixed before RT Syn integration.
- Mind Map Builder redesigned as 3D Weight Sphere using React Three Fiber + @react-three/drei + framer-motion-3d. Desktop only, mobile falls back to Vibe Sliders.
- New Section 6.5: Intent Mode -- temporary cross-system priority overlays (8 built-in modes + custom). Sits on top of active lens, time-bounded, stored in Redis with TTL.
- Unified Intent Mapping table added to Section 9: 10-row "Rosetta Stone" mapping user intents to Community Post categories and RT Syn channels.

**Why:** The user explicitly stated this should be an idea/architecture document, not implementation yet.
**How to apply:** Use this as the foundation when implementation begins. The scoring formula, data model, UX flow, Intent Mode system, and cross-system mapping are all defined in the architecture document.
