# Chat System Implementation Plan

## 1. Executive Summary
This document outlines the plan to build a robust, real-time chat system inspired by WhatsApp. The system will be implemented as a dedicated microservice (**Server 3**) using **FastAPI** to ensure high performance and low latency. The frontend will be seamlessly embedded within the existing "WarRoom" section of the application.

## 2. Architecture Overview

### 2.1 Server 3 (New Microservice)
*   **Framework**: FastAPI (Python)
*   **Purpose**: Handle all real-time communication, WebSocket connections, and chat REST APIs.
*   **Protocol**: WebSocket (via `python-socketio` or native FastAPI WebSockets) for real-time events; HTTP for file uploads and history fetching.
*   **Database**: MongoDB (Shared with Server 1 & 2 for User data; specific collections for Chat).
*   **Message Broker / Cache**: Redis (for Pub/Sub, Presence, and Throttling).
*   **Async Tasks**: Celery (for media processing, notifications).

### 2.2 Frontend Integration
*   **Location**: Embedded within the WarRoom.
*   **Entry Point**: "Chats" link in the WarRoom Sidebar (`/warroom/chats`).
*   **Layout**:
    *   **App Sidebar**: Existing Global Navigation (Leftmost).
    *   **Chat Container**: Takes up the main content area.
    *   **Chat UI**: Split view (WhatsApp style):
        *   **Left Pane**: Conversation List (Search, Recent chats, Online status).
        *   **Right Pane**: Active Conversation (Messages, Input, Header).

## 3. Data Models (MongoDB)

### 3.1 Conversation
```json
{
  "_id": "ObjectId",
  "participants": ["userId1", "userId2"],
  "type": "direct", // or "group"
  "lastMessage": {
    "content": "Hello",
    "senderId": "userId1",
    "timestamp": "ISO Date"
  },
  "updatedAt": "ISO Date",
  "isBlocked": false,
  "blockedBy": null
}
```

### 3.2 Message
```json
{
  "_id": "ObjectId",
  "conversationId": "ObjectId",
  "senderId": "userId",
  "content": "text content",
  "attachments": [
    {
      "type": "image/png",
      "url": "...",
      "size": 1024
    }
  ],
  "status": "sent", // sent, delivered, read
  "createdAt": "ISO Date"
}
```

### 3.3 ConnectionStatus (For 5-Message Rule)
*   *Note: Can be derived from existing Follower data or stored in Redis for speed.*

## 4. Business Rules & Logic

### 4.1 Follower & Privacy Logic
*   **Mutual Followers**: Unlimited messaging.
*   **Non-Followers**:
    *   Sender can send **maximum 5 messages** to a non-follower.
    *   If the recipient replies, the limit is lifted (connection accepted).
    *   If the recipient follows back, the limit is lifted.

### 4.2 Blocking
*   Users can block others.
*   **Effect**:
    *   Prevents new messages (API returns 403).
    *   Hides online status.
    *   Terminates any active WebSocket room subscriptions for that pair.

### 4.3 File Limits
*   **Max Size**: 5MB per file.
*   **Allowed Types**: Images (JPG, PNG, WEBP), Documents (PDF), Videos (MP4 - short).
*   **Validation**: Checked at API Gateway level (FastAPI Dependency).

## 5. Implementation Steps

### Phase 1: Server 3 Setup (FastAPI)
1.  Initialize `server3` directory with `poetry` or `requirements.txt`.
2.  Setup `FastAPI` app with CORS (matching frontend).
3.  Configure `MongoDB` connection (using `motor` for async).
4.  Configure `Redis` connection.
5.  Implement Auth Middleware (Verify JWT from Server 1/2).

### Phase 2: Core Chat APIs & WebSocket
1.  **WebSocket Manager**: Handle `connect`, `disconnect`, `join_room`, `leave_room`.
2.  **Messaging**:
    *   Event: `send_message`
    *   Logic: Check Block -> Check 5-Msg Limit -> Save to DB -> Emit to Recipient.
3.  **History**: REST Endpoint `GET /chats/{id}/messages` (Pagination).
4.  **Inbox**: REST Endpoint `GET /chats` (List of conversations).

### Phase 3: Frontend Development (WarRoom Embedded)
1.  **Route**: Restore `<Route path="/warroom/chats" element={<ChatLayout />} />`.
2.  **Layout**: Create `ChatLayout.tsx` that uses `WarRoomShell` or sits inside the main provider.
3.  **Components**:
    *   `ChatSidebar`: List of active conversations.
    *   `ChatWindow`: Message bubble stream.
    *   `MessageInput`: Text area + Attachment button.
4.  **State**: Use `Zustand` or `React Context` for managing active socket connection and message queue.

### Phase 4: Business Rules Enforcement
1.  Implement "Follower Check" utility in Backend.
2.  Implement "Message Counter" for non-followers in Redis.
3.  Add "Block User" button in Frontend and corresponding API.
4.  Add File Upload endpoint with `Content-Length` validation.

## 6. Next Actions
1.  Create `server3` folder structure.
2.  Install dependencies (`fastapi`, `uvicorn`, `python-socketio`, `motor`, `redis`).
3.  Draft the API contract.
