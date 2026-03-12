# Community Room Real-Time Optimization & Verification Plan V3 (FINAL)

## Status: Approved with Critical Modifications
This version incorporates strict requirements for "My Posts" separation, "Room-Based" WebSockets, and Engagement updates.

---

## Phase 1: Performance Optimization (Backend)
**Objective:** Decouple blocking "Trending" logic and fix "Recent" query bottlenecks.

### 1.1 Decouple Trending Calculation
- **Action:**
    - Create a dedicated background task (Celery or APScheduler) for `update_all_trending_scores_async`.
    - **CRITICAL:** Ensure `trendingScore` is persisted to MongoDB post documents.
    - Update `get_posts` to *only* query the pre-calculated `trendingScore` from the database.

### 1.2 Optimize "Recent" vs "My Posts" (Strict Separation)
- **Requirement:** "Recent" tab must be strictly for the user's *own* posts ("My Recent Posts").
- **Action:** Split the logic in `community_routes.py`:
    - **Endpoint:** `GET /posts`
    - **Filter `my_posts`:** Query `{"author.user_id": current_user}`. (Maps to Frontend "Recent" tab).
    - **Filter `feed`:** Query `{"$or": [{"author.user_id": user_id}, {"circleId": {"$in": user_circles}}]}`. (For a "Home" or "Feed" tab if needed later).
    - **Filter `trending`:** Query `{"trendingScore": -1}`.

### 1.3 Database Indexing Strategy
- **Action:** Ensure these compound indexes exist:
    1.  `posts`: `{"trendingScore": -1, "createdAt": -1}` (Stable Trending Feed)
    2.  `posts`: `{"author.user_id": 1, "createdAt": -1}` (Fast "My Posts")
    3.  `posts`: `{"circleId": 1, "createdAt": -1}` (Circle Feeds)

---

## Phase 2: True Real-Time Architecture (WebSocket)
**Objective:** Transition from "Pull" to "Push" with granular targeting and engagement updates.

### 2.1 Backend Room-Based Events
- **Action:** Update `socket_manager` to support room joining/leaving based on Circles.
- **Logic:**
    - On Connection: Join `user_{user_id}` and `global_feed`.
    - On Circle Join: Join `circle_{circle_id}`.
    - **Emit `new_post`:**
        - If Circle Post: Emit to `circle_{circle_id}`.
        - If Global Post: Emit to `global_feed`.
        - Always Emit to: `user_{author_id}` (to update author's "My Posts").
    - **Emit `post_updated`:**
        - Trigger on Like/Comment.
        - Payload: `{ post_id, likes, commentsCount }`.
        - Emit to: `global_feed` (or specific room if circle-scoped).

### 2.2 Frontend Integration (`WarRoom.tsx`)
- **Action:**
    - **Socket Listener:** Listen for `new_post` and `post_updated`.
    - **State Update:**
        - `new_post`: Optimistically prepend to `posts` array. Show "New" badge for 2 seconds.
        - `post_updated`: Find post by ID in `posts` array and update stats in-place (no re-fetch).
    - **Optimistic UI:** When *I* create a post, insert it immediately into state before server confirmation.

---

## Phase 3: Frontend "Glitch" & Stability Fixes
**Objective:** Eliminate white flashes and ensure reconnection reliability.

### 3.1 State Caching
- **Action:** Implement `postCache` state in `WarRoom.tsx`.
    ```typescript
    const [postCache, setPostCache] = useState({ my_posts: [], trending: [] });
    ```
- **Logic:** When switching tabs, check cache first. If exists, render immediately, *then* fetch background update.

### 3.2 Reconnection Logic
- **Action:**
    - Listen for socket `connect` event.
    - If `connect` fires after a disconnect, trigger a "soft refresh" (fetch latest 5 posts) to fill any gaps.

---

## 🔍 Q&A: Addressing Critical Verification Points

**1. Feed Definition: Is "Recent" actually "My Posts" or "Everything"?**
*   **Answer:** "Recent" will now be strictly defined as **"My Posts"** (`{"author.user_id": current_user}`) to match your requirement ("every user as their own recent posts"). We will add a separate filter/tab for "Global Feed" if you need to see other people's recent posts.

**2. Socket Rooms: Are we restricting `new_post` events?**
*   **Answer:** **Yes.** We will implement the Room-Based Logic. Users will only receive `new_post` events for:
    *   Global posts (Public).
    *   Posts in Circles they have joined (`circle_{id}`).
    *   Their own posts (`user_{id}`).
    *   *They will NOT receive events for private circles they are not part of.*

**3. Optimistic UI: Does it appear immediately?**
*   **Answer:** **Yes.** We will implement Optimistic UI. When you click "Post", it will appear in your feed *instantly* via local state update, while the backend processes it in the background. If the backend fails, we show an error and remove it (rollback).

**4. Reconnection: Does it fetch missed posts?**
*   **Answer:** **Yes.** We will add a "Reconnection Listener". If the internet drops and comes back, the frontend will automatically request the latest page of posts to ensure you didn't miss anything while offline.

---

## Implementation Checklist
1.  [ ] **Backend:** Implement `update_trending` background task (Celery/APScheduler).
2.  [ ] **Backend:** Add MongoDB Indexes.
3.  [ ] **Backend:** Update `GET /posts` to split `my_posts` vs `feed`.
4.  [ ] **Backend:** Implement `socket_manager` rooms and event emitters (`new_post`, `post_updated`).
5.  [ ] **Frontend:** Implement Socket listeners and Optimistic UI in `WarRoom.tsx`.
6.  [ ] **Frontend:** Implement Tab Caching to stop glitches.
