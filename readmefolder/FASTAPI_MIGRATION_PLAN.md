# FastAPI Community Migration & Update Plan

This document outlines the implementation phases to upgrade `FASTAPI_COMMUNITY` to fully replace `server1` (Flask), ensuring zero downtime for the frontend (`lliveupdatedstreaming`) and compatibility with `server3` (Chat).

## ✅ Phase 1: Foundation & Config Alignment
**Goal:** Ensure the server runs on the correct port and connects to the correct shared database.

1.  **Fix Port Conflict:**
    *   **Completed:** Modified `FASTAPI_COMMUNITY/run.py` to use **Port 9091**.
    *   *Reason:* Frontend is configured to talk to Main Server on 9091 (`VITE_API_BASE_URL2`). `server3` occupies 8000.
2.  **Database Synchronization:**
    *   **Completed:** Updated `app/core/config.py`: Set default `MONGODB_DB_NAME` to `barise_auth_db` (matching `server1` and `server3`).
3.  **Dependencies:**
    *   **Completed:** Added `pywebpush`, `bleach`, and `redis` to `FASTAPI_COMMUNITY/requirements.txt`.

## ✅ Phase 2: Porting "Lag" Features (Missing Functionality)
**Goal:** Implement critical features present in Flask but missing in FastAPI.

1.  **Web Push Notifications (VAPID):**
    *   **Completed:** Created `app/api/routes/push_routes.py`.
    *   **Completed:** Implemented endpoints matching Flask's `push_bp.py`:
        *   `GET /api/push/vapid-public-key`
        *   `POST /api/push/subscribe`
        *   `POST /api/push/unsubscribe`
        *   `GET/PUT /api/notifications/settings`
    *   **Completed:** Updated `app/db/mongo.py` to initialize `push_subscriptions` and `notification_settings` collections.

2.  **Health Checks:**
    *   **Completed:** Created `app/api/routes/health_routes.py`.
    *   **Completed:** Implemented `/healthz` and `/readyz` to ping MongoDB and Redis.

## ✅ Phase 3: Frontend Alignment (Routing)
**Goal:** Ensure API URL paths match exactly what the Frontend expects.

1.  **Route Registration:**
    *   **Completed:** Updated `app/main.py` to register `push_routes` and `health_routes`.
    *   **Crucial Detail:** Registered them **without** the `/api/v1` prefix (e.g., just `/api/push...`) to ensure exact parity with the legacy Flask routes the frontend is hardcoded to call.

## ✅ Phase 4: Bug Fixes & Stabilization
1.  **Redis SSL Fix:**
    *   **Fixed:** Modified `app/db/redis.py` to explicitly disable SSL (`ssl_cert_reqs`) when `REDIS_SSL` is false, fixing the local development `RedisSSLContext` error.
    *   **Fixed:** Updated `app/celery_tasks/search_tasks.py` to gracefully handle cases where Redis is offline, preventing crashes during embedding caching.
2.  **Trending Posts Visibility:**
    *   **Fixed:** Updated `app/api/routes/ideas_routes.py` to explicitly filter for **public** ideas (`is_private: false`) in the trending query. This ensures the frontend always receives visible data and avoids privacy leaks.

## Next Steps for User
1.  **Install Dependencies:** Run `pip install -r requirements.txt`.
2.  **Environment Variables:** Ensure your `.env` file has the VAPID keys (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`) copied from your Flask server's `.env`.
3.  **Run:** Start the server with `python run.py`. It will now listen on port **9091**.

---
**Migration Status: READY FOR DEPLOYMENT**
