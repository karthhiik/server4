# BACKEND MASTER PLAN: Real-Time Chat System (Server 3)

## 1. Executive Summary
This document outlines the technical architecture for **Server 3**, a dedicated high-performance microservice for the Real-Time Chat system. Built with **FastAPI (Python) + Redis celery**, it integrates seamlessly with the existing **Server 1 (Community/Flask)** and **Server 2 (Auth/Flask)**.

**Key Goals:**
*   **Real-Time Performance:** Sub-50ms latency for message delivery using WebSockets.
*   **Scalability:** Horizontal scaling support using Redis Pub/Sub.
*   **Seamless Integration:** Reuse existing User IDs (Server 2) and Follower Logic (Server 1).
*   **Security:** End-to-End Encryption (E2EE) ready, JWT validation, and strictly enforced privacy rules.

---

## 2. System Architecture

### 2.1 Microservices Landscape
*   **Server 1 (Flask - Community):** Handles User Profiles, Follows, Posts, Feed.
*   **Server 2 (Flask - Auth):** Handles Registration, Login, JWT Token Generation.
*   **Server 3 (FastAPI - Chat):** Handles WebSocket Connections, Message Routing, Chat History, Presence.

### 2.2 Data Flow
1.  **Auth:** Client logs in via Server 2 -> Receives JWT.
2.  **Connect:** Client connects to Server 3 WebSocket (`wss://chat.barise.com/ws`) with JWT.
3.  **Validation:** Server 3 decodes JWT (using shared Secret) to authenticate user.
4.  **Permission Check:** When User A messages User B:
    *   Server 3 checks Redis cache for "Follow Status".
    *   If miss, queries Shared MongoDB (Server 1's DB) or calls Server 1 Internal API.
    *   Enforces "5-Message Rule" or "Block Status".
5.  **Delivery:** Message routed via Redis Pub/Sub to User B's connected instance.

---

## 3. Technology Stack

*   **Framework:** FastAPI (Python 3.10+) - Async, High Concurrency.
*   **Protocol:** WebSockets (Real-time), HTTP/2 (REST fallback/Uploads).
*   **Database (Persistent):** MongoDB (AsyncIOMotorClient).
*   **Database (Ephemeral/Cache):** Redis (aioredis) - Pub/Sub, Presence, Rate Limiting.
*   **Storage:** Azure Blob Storage / AWS S3 (for Media Attachments).
*   **Validation:** Pydantic Models.

---

## 4. Database Schema (MongoDB)

Server 3 will use a dedicated database `barise_chat_db` but will have read-access to `community_db` for follower checks.

### 4.1 Collections

#### `conversations`
Metadata about a chat thread between participants.
```json
{
  "_id": "ObjectId",
  "participants": ["user_id_1", "user_id_2"],
  "type": "direct", // or "group"
  "last_message": {
    "content": "Hello",
    "sender_id": "user_id_1",
    "timestamp": "ISO_DATE",
    "type": "text"
  },
  "updated_at": "ISO_DATE",
  "is_blocked": false,
  "blocked_by": null
}
```

#### `messages`
The actual message history.
```json
{
  "_id": "ObjectId",
  "conversation_id": "ObjectId",
  "sender_id": "user_id_1",
  "content": "Encrypted or Plain Text",
  "type": "text|image|file|audio",
  "metadata": {
    "file_url": "https://...",
    "file_name": "doc.pdf",
    "file_size": "2MB",
    "duration": "0:05" // for audio
  },
  "status": "sent|delivered|read",
  "timestamp": "ISO_DATE",
  "reply_to": "message_id_optional"
}
```

#### `unread_counts` (Optimization)
Fast lookup for sidebar badges.
```json
{
  "user_id": "user_id_1",
  "conversation_id": "conversation_id_A",
  "count": 5
}
```

---

## 5. Redis Strategy (Caching & Real-time)

*   **Presence System:**
    *   Key: `user:presence:{user_id}` -> Value: `online | offline | typing`
    *   TTL: 60 seconds (Heartbeat refreshes).
*   **Pub/Sub Channels:**
    *   Channel: `chat:user:{user_id}`
    *   Used to push real-time events to specific connected users across multiple server instances.
*   **Permission Cache:**
    *   Key: `rel:{user_A}:{user_B}` -> Value: `following | mutual | none | blocked`
    *   TTL: 5 minutes. Invalidated on Follow/Unfollow events from Server 1.

---

## 6. API Specification

### 6.1 WebSocket Events (`/ws`)

**Client -> Server:**
*   `auth`: `{ token: "jwt..." }`
*   `message`: `{ to: "user_id", content: "...", type: "..." }`
*   `typing_start`: `{ conversation_id: "..." }`
*   `typing_stop`: `{ conversation_id: "..." }`
*   `read_receipt`: `{ message_id: "..." }`

**Server -> Client:**
*   `message_received`: (New message payload)
*   `status_update`: (Online/Offline/Typing)
*   `message_status`: (Sent/Delivered/Read updates)
*   `error`: (Permission denied, Limit reached)

### 6.2 REST Endpoints

*   `POST /api/chat/upload`: Upload media (Audio/Image/File). Returns URL.
*   `GET /api/chat/conversations`: List all active chats (sorted by recent).
*   `GET /api/chat/{conversation_id}/messages`: Paginated message history.
*   `POST /api/chat/block`: Block a user (Syncs with Server 1 block list).

---

## 7. Business Logic & Rules Implementation

### 7.1 The "5-Message Rule"
*   **Logic:** Before processing a message from A to B:
    1.  Check Redis `rel:{A}:{B}`.
    2.  If `mutual` or `B_follows_A` -> ALLOW.
    3.  If `none` -> Check `messages` collection for count of A's messages since last B message.
    4.  If count >= 5 -> REJECT with error `LIMIT_REACHED`.

### 7.2 Blocking
*   Blocking is bidirectional for Chat.
*   If A blocks B:
    *   Store in MongoDB `conversations` or dedicated `blocks` collection.
    *   Reject WebSocket connection or Message packets immediately.

---

## 8. Security & Deployment

### 8.1 Security
*   **JWT Validation:** Server 3 must share the `SECRET_KEY` with Server 2 to validate tokens.
*   **Input Sanitization:** All text content is sanitized to prevent XSS.
*   **Rate Limiting:** Redis-based limiter (e.g., max 10 messages/second per user).

### 8.2 Directory Structure (Proposed)
```
server3/
├── app/
│   ├── main.py            # Entry point
│   ├── core/
│   │   ├── config.py      # Env vars
│   │   └── security.py    # JWT logic
│   ├── db/
│   │   ├── mongo.py       # Motor client
│   │   └── redis.py       # Aioredis client
│   ├── models/            # Pydantic models
│   ├── routers/
│   │   ├── websocket.py   # WS handlers
│   │   └── chat.py        # REST endpoints
│   └── services/
│       ├── chat_service.py # Business logic
│       └── connection_manager.py # WS Connection pool
├── requirements.txt
└── Dockerfile
```

---

## 9. Implementation Roadmap

1.  **Setup:** Init FastAPI project, Docker, and Redis connection.
2.  **Auth Integration:** Implement JWT decoding middleware.
3.  **WebSocket Core:** Build `ConnectionManager` to handle active socket list.
4.  **Messaging MVP:** 1-on-1 text messaging (no persistence).
5.  **Persistence:** Connect MongoDB, save/load history.
6.  **Advanced Features:** Implement Media Uploads (Audio/File) and Presence.
7.  **Rules Engine:** Implement 5-message limit and Block logic.
8.  **Production:** Nginx reverse proxy, SSL, and Load Balancing.
