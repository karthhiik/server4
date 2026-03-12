# Final Polish & Fixes Plan (Community & Profile)

## Phase 1: Twitter-Style Infinite Scroll (Trending Feed)
**Objective:** Ensure the "Trending" feed loads continuously and smoothly as the user scrolls, just like Twitter/X.
-   **Backend (`community_routes.py`):**
    -   Verify `trending` filter uses stable sorting: `[("trendingScore", -1), ("createdAt", -1)]`.
    -   This ensures that even if scores are identical (e.g., 0), posts appear in a consistent chronological order, preventing "jumping" items during scroll.
-   **Frontend (`WarRoom.tsx`):**
    -   The `IntersectionObserver` is already implemented.
    -   **Action:** I will verify it triggers `handleNextPage` correctly without "bouncing" at the bottom.

## Phase 2: Fix "Recent" Feed Loading Flash (UX Polish)
**Objective:** Stop the "Start Post" / "No Posts" button from flashing while data is still loading.
-   **Issue:** The UI currently renders the empty state (Start Post) *before* the API response arrives.
-   **Fix (`WarRoom.tsx`):**
    -   Implement a **Skeleton Loader** (placeholder UI) that displays immediately when `loading` is true.
    -   Only show the "Start Post" empty state if `!loading` AND `posts.length === 0`.
    -   This provides the "instant" feel of X/Twitter.

## Phase 3: Fix Profile "MYLab" & 404 Errors
**Objective:** Fix the `404 Not Found` on `/profile` and ensure data accuracy matches Server 1.
-   **Issue 1 (404 Error):** The logs show a request to `GET /profile`. This endpoint is missing in FastAPI.
    -   **Fix:** Add `GET /profile` (and `/api/profile`) to `user_routes.py`, pointing it to the user details logic.
-   **Issue 2 (Accuracy):** "Profile is not as accurate as Server 1".
    -   **Analysis:** Server 1 returns a simple object: `{ name, role, photo }`.
    -   **Fix:** I will ensure the new `/profile` endpoint returns *at least* these fields, plus the rich stats (bookmarks, posts) that "MYLab" likely needs.
    -   **Action:** I will ensure the response structure matches exactly what the frontend "MYLab" component expects (likely the detailed stats).

## Execution Order
1.  **Backend:** Add missing `/profile` endpoints.
2.  **Frontend:** Add Skeleton Loaders to `WarRoom.tsx` to fix the flash.
3.  **Verification:** Check the "Trending" scroll behavior.
