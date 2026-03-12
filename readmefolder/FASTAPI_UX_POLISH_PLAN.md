# WarRoom UX & Real-Time Optimization Plan (Revised V2)

## 1. Executive Summary
This revised plan addresses the critical "Flash", "Stagnation", and "Glitchy Scroll" issues by shifting from a traditional Offset Pagination architecture to a **Cursor-Based Real-Time Architecture**. This ensures zero duplicate posts, accurate infinite scrolling, and handling of race conditions during rapid tab switching.

**Status**: Planning Mode (Ready for Approval).

---

## 2. Technical Architecture & Solutions

### Issue 1: Pagination Reliability (Switch to Cursor-Based)
*   **Current Problem**: Using `page=1, 2` (Offset) causes duplicates or skipped posts when new items are added to the top of the list in real-time.
*   **Solution**: **Cursor-Based Pagination**.
    *   **Backend**: The API will accept a `cursor` parameter (timestamp of the last post seen).
    *   **Logic**: `db.posts.find({ createdAt: { $lt: cursor } }).sort({ createdAt: -1 })`.
    *   **Response**: Returns `{ posts: [...], next_cursor: "2023-10-27T10:00:00Z", has_more: true }`.

### Issue 2: Race Conditions (Request Cancellation)
*   **Current Problem**: Switching tabs quickly (Trending -> Recent -> Trending) can result in the wrong data overwriting the view if the first request completes last.
*   **Solution**: **`AbortController`**.
    *   On every `fetchData` call, generate a signal.
    *   On tab unmount/switch, call `controller.abort()`.
    *   This ensures only the *current* tab's data ever reaches the state.

### Issue 3: Scroll Glitches (Synchronous Restoration)
*   **Current Problem**: Restoring scroll position via `useEffect` happens *after* the paint, causing a visible jump/flash.
*   **Solution**: **`useLayoutEffect`**.
    *   Restore scroll position synchronously before the browser paints the frame.
    *   Result: The user sees the exact position they left instantly, with no visual jump.

### Issue 4: Real-Time UX (New Posts Bubble)
*   **Current Problem**: Auto-inserting posts at the top pushes content down while the user is reading.
*   **Solution**: **"New Posts" Toast**.
    *   When a socket event arrives, add it to a temporary "queue".
    *   Show a "Show 5 New Posts" floating bubble at the top.
    *   Clicking it scrolls to top and merges the queue.

---

## 3. Implementation Phases

### Phase 1: Backend API Refactor (Cursor Support)
**Goal**: Enable stable pagination.
1.  **Modify `get_posts` (community_routes.py)**:
    *   Replace `page` parameter with `cursor` (str, optional).
    *   Update MongoDB query to use `$lt` (less than) comparison on `createdAt` (or `trendingScore` for Trending tab) if `cursor` is present.
    *   Update response schema to include `next_cursor`.
2.  **Fix "Recent" Filter**:
    *   Ensure `filter=recent` (or `my_posts`) strictly queries `{"author.user_id": current_user}`.

### Phase 2: Frontend Core Architecture (Cache & Concurrency)
**Goal**: Instant tab switching without race conditions.
1.  **Cache State Definition**:
    ```typescript
    const feedCache = useRef({
      trending: { posts: [], cursor: null, scrollY: 0, hasMore: true },
      recent: { posts: [], cursor: null, scrollY: 0, hasMore: true }
    });
    ```
2.  **Refactor `fetchData`**:
    *   Accept `AbortSignal`.
    *   Implement logic: If `!cursor` (Fresh Load) -> Replace. If `cursor` -> Append.
3.  **Implement `useLayoutEffect`**:
    *   Save scroll position on cleanup.
    *   Restore scroll position on mount *before* fetch.

### Phase 3: Infinite Scroll & Skeletons
**Goal**: Smooth loading experience.
1.  **Skeleton Screens**:
    *   Create `<PostSkeleton />`.
    *   Logic: `if (isInitialLoad) return <Skeleton />`.
    *   Logic: `if (isFetchingNext) return <Spinner />` (at bottom).
2.  **IntersectionObserver Integration**:
    *   Attach Observer to a bottom Sentinel.
    *   On trigger: Call `fetchData(feedCache.current[tab].cursor)`.

### Phase 4: Real-Time "Toast" Integration
**Goal**: Non-intrusive updates.
1.  **Socket Listener**:
    *   On `new_post`:
        *   If `activeFilter === 'recent'` (My Posts): Prepend immediately (Safe).
        *   If `activeFilter === 'trending'`: Increment "Unread Count" state.
2.  **UI Component**:
    *   Render "New Posts Available" button if `unreadCount > 0`.
    *   OnClick: Fetch latest, reset cursor, scroll top.

---

## 4. Verification Checklist

| Feature | Success Criteria |
| :--- | :--- |
| **Pagination** | Scrolling down loads older posts without duplicates or gaps. |
| **Tab Switching** | Switching is instant (from cache). Rapid switching does not mix data (AbortController works). |
| **Scroll Position** | Returning to a tab restores exact scroll position with ZERO flicker. |
| **Real-Time** | "New Posts" bubble appears for incoming content. "My Posts" appear instantly. |
| **API** | Backend correctly handles `cursor` based queries. |

---

This plan is technically robust and addresses all race conditions and pagination flaws. Ready for execution.
