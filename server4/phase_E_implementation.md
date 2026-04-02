# Phase E — AI Image Generation & Visual Intelligence

> **Owner**: Founder
> **Status**: IMPLEMENTED
> **Date**: 2026-04-01
> **Priority**: P1 — Premium v2 feature, differentiator

---

## 1. Architecture Decisions (Founder-Approved)

### Non-Blocking Image Generation (Critical)
- **Problem**: Blocking image generation adds 15-25s to a 10-slide deck
- **Solution**: "Placeholder & Populate" — text returns instantly, images fire-and-forget in background
- **Implementation**: `asyncio.create_task()` for each image, slides updated when ready
- **User Experience**: Text appears immediately, images "pop in" seconds later (like Midjourney/Gamma)

### Redis Hot Cache (Not MongoDB)
- **Problem**: MongoDB lookups add latency for every image generation
- **Solution**: Redis for hot cache (sub-millisecond), MongoDB only for cost logging
- **TTL**: 30 days for image cache, 7 days for thumbnails
- **Key Format**: `img:{prompt_hash}` → URL

### Theme-Aware Prompting
- **Problem**: "Medical Clean" theme got dark "Tech Neon" images
- **Solution**: Inject theme style keywords into every prompt
- **Mapping**: 8 themes → specific style descriptors (sterile/cyberpunk/minimal/etc.)

### Image Validation
- **Min size**: 5KB (discard blank/error images)
- **Max size**: 2MB (flag for compression in v2)
- **No NSFW filter** in v1 (free CF workers, can't afford extra API calls)

---

## 2. Implementation Summary

### E1: ImageService (CREATED)

**File**: `app/services/image_service.py` (NEW, ~230 lines)

**Features**:
- Phoenix/Lucid routing based on layout type
- Redis hot cache (30-day TTL)
- Theme-aware prompt building with style keyword injection
- File size validation (5KB min, 2MB max)
- Graceful fallback (None on failure, never crashes pipeline)
- MongoDB cost logging (generation_logs collection)

**Model Routing**:
| Layout | Model | Why |
|--------|-------|-----|
| title-hero, full-image, quote | Lucid | Artistic, cinematic, abstract |
| bullets-with-image, team-grid | Phoenix | Professional, literal, clean |

**Theme Style Keywords**:
| Theme | Keywords Injected |
|-------|------------------|
| tech-neon | cyberpunk, glowing neon, dark background, circuit board |
| startup-gradient | modern startup, vibrant gradients, bold colors |
| minimal-mono | minimalist, monochrome, whitespace, zen |
| corporate-blue | corporate, navy blue, clean office, trustworthy |
| nature-earth | natural, earth tones, organic, sustainable |
| medical-clean | sterile, laboratory, bright lighting, clinical |
| academic-serif | academic, scholarly, warm tones, classic |
| creative-bold | bold, artistic, vibrant, dynamic |

---

### E2: Fire-and-Forget Pipeline Integration (WIRED)

**File**: `app/services/orchestrator/orchestrator.py` (MODIFIED, +80 lines)

**Changes**:
- `_fire_image_generation()` — dispatches image tasks after text content is ready
- `_generate_and_attach_image()` — generates image and attaches URL to slide content
- Uses `asyncio.create_task()` — non-blocking, fire-and-forget
- Images attach to `slide["content"]["image_url"]` when ready
- Logs: `image_generation_fired`, `image_attached`, `image_skipped`

**Flow**:
```
1. Text content generated for all slides (fast, ~10-20s)
2. Return slides to user immediately
3. asyncio.create_task() fires image generation for each eligible slide
4. When image ready, attach URL to slide["content"]["image_url"]
5. Frontend polls WebSocket for slide updates (images "pop in")
```

---

### E3: Thumbnail Generation (Celery Task)

**File**: `celery_worker.py` (MODIFIED, +40 lines)

**Changes**:
- `generate_thumbnail_task` — Celery task for async thumbnail generation
- Renders first slide at thumbnail resolution (800×450)
- Uploads to blob storage with 7-day SAS URL
- Updates presentation record with `thumbnail_url`
- Fired immediately after presentation record created

**Flow**:
```
1. User creates presentation
2. Orchestrator starts generation
3. Celery task generate_thumbnail_task fired with presentation_id
4. Task waits for first slide to exist, then renders thumbnail
5. Frontend polls for thumbnail URL
```

---

### E4: Cost Tracking (MongoDB)

**File**: `app/services/image_service.py` (BUILT-IN)

**Changes**:
- Every image generation logged to `generation_logs` collection
- Fields: presentation_id, phase="image_generation", model, provider, latency_ms, file_size, cached
- Cache hits logged separately (cached=True) for cost analysis
- No additional collection needed — extends existing generation_logs

---

## 3. File Change Summary

| File | Action | Lines | Purpose |
|------|--------|-------|---------|
| `app/services/image_service.py` | **CREATE** | ~230 | ImageService with Redis caching, theme-aware prompts, Phoenix/Lucid routing |
| `app/services/orchestrator/orchestrator.py` | **MODIFY** | +80 | Fire-and-forget image generation pipeline |
| `celery_worker.py` | **MODIFY** | +40 | Async thumbnail generation task |

**Total: 1 new file + 2 modifications = ~350 new lines**

---

## 4. Testing Strategy

### Unit Tests
| Test | What | How |
|------|------|-----|
| `test_image_service_phoenix_routing` | General layouts → Phoenix | Mock CF client, verify model selection |
| `test_image_service_lucid_routing` | Hero/quote layouts → Lucid | Mock CF client, verify model selection |
| `test_image_service_redis_cache_hit` | Same prompt → cached URL from Redis | Mock Redis, verify cache lookup |
| `test_image_service_cache_miss` | New prompt → generate + cache | Mock Redis + CF client, verify cache write |
| `test_image_service_fallback` | CF failure → None (no crash) | Mock CF to raise, verify graceful fallback |
| `test_image_prompt_theme_aware` | Theme keywords injected | Verify prompt contains theme style words |
| `test_image_size_validation` | <5KB image discarded | Mock small image, verify None returned |
| `test_thumbnail_celery_task` | Thumbnail generated async | Mock Celery, verify task dispatch |

### Integration Tests
| Test | What | How |
|------|------|-----|
| `test_fire_and_forget_images` | Images don't block text generation | Mock pipeline, verify tasks created but not awaited |
| `test_image_cache_reduces_api_calls` | Same prompt twice → 1 API call | Track CF client calls, verify only 1 call |

---

## 5. Success Criteria

- [ ] `ImageService.generate_slide_image()` returns blob URL for supported layouts
- [ ] Phoenix used for general slides, Lucid for hero/creative slides
- [ ] Redis cache hit returns URL without API call
- [ ] Image generation failure → graceful fallback (slide renders without image)
- [ ] Theme keywords injected into prompts for visual consistency
- [ ] Images < 5KB discarded (blank/error detection)
- [ ] Fire-and-forget: text returns instantly, images populate in background
- [ ] Thumbnail generated async via Celery
- [ ] All 8 Phase E unit tests pass
- [ ] No breaking changes to existing Phase B/C/D functionality
- [ ] Zero additional cost (Phoenix/Lucid are free, Redis caching reduces calls)
