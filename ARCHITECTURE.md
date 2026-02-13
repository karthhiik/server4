# Architecture Overview

This repository contains a React front‑end and two Flask back‑end services (“server1” and “server2”). The front‑end communicates with both services via environment‑configured base URLs and uses WebSocket features provided by server1.

## Front‑End
- Location: [lliveupdatedstreaming](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming)
- Stack: React 18, Vite 5, TypeScript, Tailwind, assorted UI libraries
- Dev server: port 3000, see [vite.config.ts](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/vite.config.ts#L8-L14)
- Entry points:
  - HTML bootstrap: [index.html](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/index.html)
  - React bootstrap: [main.tsx](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/src/main.tsx), [App.tsx](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/src/App.tsx)
- API configuration:
  - Primary API base: VITE_API_BASE_URL (defaults to server2, 9090) in [.env](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/.env#L2)
  - Secondary API base: VITE_API_BASE_URL2 (defaults to server1, 9091) in [.env](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/.env#L5)
- Example API call locations: [api.ts](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/src/components/payments2/api/api.ts)
- Example UI component (community): [PostCard.tsx](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/src/components/Community/components/community/PostCard.tsx)

## Server1 (Community/Realtime)
- Location: [server1](file:///d:/Desktop/New_Flask/FLASK/server1)
- Purpose: Community features, chat, notifications, search caching, and Socket.IO realtime channels
- Frameworks: Flask, Flask‑CORS, Flask‑SocketIO, Flasgger (Swagger)
- Entry/run:
  - App startup: [app.py](file:///d:/Desktop/New_Flask/FLASK/server1/app.py#L81-L87) (defaults host 0.0.0.0, port 9091)
  - Route registration: [routes.py](file:///d:/Desktop/New_Flask/FLASK/server1/routes.py#L27-L49)
- Sockets:
  - Socket.IO init and CORS origins: [app.py](file:///d:/Desktop/New_Flask/FLASK/server1/app.py#L49-L70)
  - Chat/notification sockets: [routes.py](file:///d:/Desktop/New_Flask/FLASK/server1/routes.py#L89-L94)
- Blueprints (selected):
  - Community, chat, notifications, search, comments, live, ideas, ads, profile, user, health
  - See [routes.py](file:///d:/Desktop/New_Flask/FLASK/server1/routes.py#L28-L44)
- Swagger/OpenAPI: [swagger_config.py](file:///d:/Desktop/New_Flask/FLASK/server1/swagger_config.py)
- Config/env loading: [config.py](file:///d:/Desktop/New_Flask/FLASK/server1/config.py)

## Server2 (Core APIs/Business)
- Location: [server2](file:///d:/Desktop/New_Flask/FLASK/server2)
- Purpose: Core application APIs (auth, business, documents, feedback, etc.) and Swagger docs
- Frameworks: Flask, Flask‑CORS, Flasgger (Swagger)
- Entry/run:
  - App factory: [app.py](file:///d:/Desktop/New_Flask/FLASK/server2/app.py#L683-L894)
  - Run on port 9090: [app.py](file:///d:/Desktop/New_Flask/FLASK/server2/app.py#L900-L907)
- Swagger init: [blueprints/swagger_bp.py](file:///d:/Desktop/New_Flask/FLASK/server2/blueprints/swagger_bp.py)
- Routes/blueprints: [routes.py](file:///d:/Desktop/New_Flask/FLASK/server2/routes.py), [blueprints](file:///d:/Desktop/New_Flask/FLASK/server2/blueprints)
- Health endpoints: [app.py](file:///d:/Desktop/New_Flask/FLASK/server2/app.py#L840-L861), thread/status: [app.py](file:///d:/Desktop/New_Flask/FLASK/server2/app.py#L862-L871)

## Data Flow
- Front‑end → Server2 (HTTP): general APIs via VITE_API_BASE_URL (default http://127.0.0.1:9090)
- Front‑end → Server1 (HTTP/WebSocket):
  - Community/chat/notifications via VITE_API_BASE_URL2 (default http://localhost:9091)
  - Socket.IO uses allowed origins including localhost:3000/5173; see [app.py](file:///d:/Desktop/New_Flask/FLASK/server1/app.py#L49-L58)
- Internal jobs:
  - Search cache, ads system, and index creation are initialized at startup in server1

## Environment Configuration
- Front‑end env: [.env](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/.env)
  - Configure API base URLs (do not commit real secrets)
- Server2 env: [.env](file:///d:/Desktop/New_Flask/FLASK/server2/.env)
  - Contains many service API keys and secrets; secure these outside VCS for production
- Server1 config/env: [config.py](file:///d:/Desktop/New_Flask/FLASK/server1/config.py)
  - Loads SECRET_KEY, storage paths, Redis/Mongo settings

## Local Development
- Start server2 (9090): [server2/app.py](file:///d:/Desktop/New_Flask/FLASK/server2/app.py#L900-L907)
- Start server1 (9091): [server1/app.py](file:///d:/Desktop/New_Flask/FLASK/server1/app.py#L81-L87)
- Start front‑end (3000): [vite.config.ts](file:///d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming/vite.config.ts#L8-L14), with env pointing to the above ports
- Ensure CORS and Socket.IO origins include the front‑end dev server host

## Quick Responsibilities Map
- Front‑end: UI, routes, and components; calls both back‑ends
- Server1: Community modules, realtime chat/notifications, search cache, Swagger
- Server2: Core app APIs (auth, business, document processing, feedback), Swagger, health/status

## Notes
- Secrets in env files must not be exposed or committed in production; use secure secret management.
- Swagger/Flasgger is enabled on both servers to document endpoints.
