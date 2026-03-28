# Codebase Understanding: FASTAPI_COMMUNITY & Frontend

## 🏗️ Architecture Overview

Your system is a modern web application with a **FastAPI backend** and a **React-TypeScript frontend**, designed as a community/marketplace platform with real-time chat capabilities.

---

## 📱 FRONTEND: lliveupdatedstreaming

### Technology Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS (CSS Framework)
- **UI Components**: shadcn/ui (Radix UI + Tailwind), Material-UI (@mui/material), Heroicons
- **State Management**: Redux (@reduxjs/toolkit)
- **API Client**: TanStack React Query (react-query), axios, httpx
- **Authentication**: JWT token-based with context API
- **Real-time**: WebSocket implementation (service worker, push notifications)
- **Payment**: Cashfree Payments integration
- **Visualization**: @xyflow/react (node-based diagrams)
- **Form Validation**: React Hook Form with resolvers

### Project Structure

```
lliveupdatedstreaming/
├── src/
│   ├── main.tsx                 # Entry point with Redux provider & Service Worker registration
│   ├── App.tsx                  # Main router with 50+ routes
│   ├── index.css & App.css      # Global styles
│   ├── components/              # React components
│   │   ├── context/
│   │   │   └── Authcontext.tsx           # Auth context with JWT, redirects, login provider
│   │   ├── Community/            # War room, chat, profiles, live events
│   │   │   ├── pages/
│   │   │   │   ├── WarRoom.tsx           # Main community hub
│   │   │   │   ├── Chat.tsx              # Chat layout with WebSocket
│   │   │   │   ├── Profile.tsx           # Community profiles
│   │   │   │   ├── Liveevent.tsx         # Live events streaming
│   │   │   │   └── Idea.tsx              # Ideas/posts
│   │   │   └── components/
│   │   │       ├── community/
│   │   │       ├── layout/               # Navbar, sidebar, status tools
│   │   │       └── ...
│   │   ├── Auth/                 # Login, signup, password reset
│   │   ├── Ai_matching/          # AI-based matching system
│   │   ├── BusinessPlanfrom/     # Business plan generation
│   │   ├── ColdMail/             # Cold email outreach
│   │   ├── payments2/            # Subscription & payment pages
│   │   ├── matchingfront/        # Founder-Investor-Mentor matching
│   │   ├── Calculator_app/       # Financial calculator
│   │   ├── ui/                   # Base UI components (shadcn/ui)
│   │   ├── common/               # Reusable components
│   │   ├── Chatbot.tsx           # Interactive chatbot
│   │   └── ...
│   ├── pages/                  # Page components (routing targets)
│   │   ├── Index.tsx               # Legacy home page
│   │   ├── OrchidsLanding.tsx      # New landing page
│   │   ├── BusinessPlan.tsx        # Business plan builder
│   │   ├── SWOTAnalysis.tsx        # SWOT analysis page
│   │   ├── GTMStrategy.tsx         # Go-to-Market strategy
│   │   ├── pitch_anaylsis.tsx      # Pitch deck analysis
│   │   ├── TermsOfService.tsx
│   │   ├── PrivacyPolicy.tsx
│   │   ├── ContactPage.tsx
│   │   ├── FeedbackPage.tsx
│   │   ├── PageTracker.tsx         # Analytics/page tracking
│   │   └── ...
│   ├── services/
│   │   └── azureUpload.ts      # Azure blob storage upload
│   ├── store/
│   │   ├── index.ts            # Redux store setup
│   │   ├── businessPlanSlice.ts # Business plan state
│   │   └── usePageTracking.ts
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Utilities & helpers
│   └── config/                 # Configuration files
├── public/
│   └── sw.js                   # Service Worker (PWA support)
├── build/                      # Production build output
├── vite.config.ts              # Vite configuration
├── tailwind.config.ts          # Tailwind CSS config
├── tsconfig.json               # TypeScript config
└── package.json                # Dependencies

```

### Key Routes (50+ routes defined)

**Core Pages:**
- `/` - Landing page (OrchidsLanding)
- `/home_page` - Alternative home
- `/ai` - AI matching dashboard
- `/profile` - User profile
- `/login`, `/signup`, `/reset-password`, `/verify-email` - Auth pages

**Feature Pages:**
- `/business-plan` - Business plan builder
- `/swot-analysis` - SWOT analysis tool
- `/gtm-strategy` - Marketing strategy generator
- `/pitch-analysis` - Pitch deck analyzer
- `/calculator` - Financial calculator
- `/pay`, `/subscription-dashboard` - Premium/payments
- `/match-results`, `/match-results-investors`, `/match-result-mentorship` - Matching results

**Community/WarRoom:**
- `/warroom` - Main community hub
- `/warroom/chats` - Chat interface
- `/warroom/chats/user/:userId` - User-specific chat
- `/warroom/saved` - Saved posts
- `/Accessprofile` - Community profiles
- `/ideas` - Ideas/posts feed
- `/event` - Live events
- `/p/:shareCode` - Shared post via code
- `/notifications` - Notification center
- `/search` - Search results

**Policies & Legal:**
- `/term`, `/policy`, `/cookies`, `/communityguideline` - Legal pages

### Components & Features

**Authentication:**
- JWT-based auth with httpClient (apiRequest, ApiRateLimitError)
- Login provider tracking (Google, LinkedIn, etc.)
- Redirect path management for post-login flow
- Service Worker for offline capability

**Community/Chat:**
- Real-time chat with WebSocket (`/warroom/chats`)
- Typing indicators
- Message read receipts
- Profile viewing within community
- Live event streaming
- Ideas/posts with comments

**Tools & Analysis:**
- AI-powered business matching
- Business plan generation from documents
- SWOT analysis generator
- GTM (Go-to-Market) strategy builder
- Pitch deck uploads and analysis
- Financial calculator

**Payments:**
- Cashfree payment integration
- Subscription plans selection
- Payment results handling
- Subscription dashboard

---

## 🔧 BACKEND: FASTAPI_COMMUNITY

### Technology Stack
- **Framework**: FastAPI (Python 3.11+)
- **ASGI Server**: Uvicorn
- **Database**: MongoDB (Motor async driver)
- **Cache/Message Broker**: Redis
- **Task Queue**: Celery
- **Authentication**: JWT (PyJWT) with secure cookies
- **File Upload**: Azure Blob Storage, Pillow for image processing
- **NLP/ML**: scikit-learn, Sentence Transformers, NLTK, Gensim
- **AI**: OpenAI API, Azure AI Document Intelligence
- **PDF/Document Processing**: PyPDF2, PyMuPDF, python-docx, python-pptx
- **Real-time Communication**: WebSockets (native FastAPI + python-socketio)
- **Email**: Firebase Admin SDK
- **Monitoring**: Flower (Celery monitor), Ruff (linting)

### Project Structure

```
FASTAPI_COMMUNITY/
├── run.py                      # Entry point (uses app.main:app)
├── main.py                     # May redirect to app/main.py
├── requirements.txt            # Dependencies (FastAPI, Motor, Redis, Celery, etc.)
├── docker-compose.yml          # Services: FastAPI web, MongoDB, Redis, Celery worker
├── ruff.toml                   # Linting/formatting config
├── .env.docker                 # Docker environment variables
├── Dockerfile                  # FastAPI container
├── docker-environment.yml      # Service configuration
├── start_services.sh           # Bash script to start services
├── list_cols.py                # Utility to list MongoDB collections
│
├── app/
│   ├── main.py                 # FastAPI app initialization with lifespan hooks
│   ├── __init__.py
│   ├── Dockerfile              # Container definition
│   │
│   ├── api/
│   │   ├── main.py             # APIRouter setup - includes all route modules
│   │   ├── routes/             # REST API endpoints
│   │   │   ├── user_routes.py              # User management
│   │   │   ├── chat_routes.py              # Chat history & REST chat APIs
│   │   │   ├── websocket_routes.py         # WebSocket endpoints (main)
│   │   │   ├── profile_routes.py           # Profile management
│   │   │   ├── community_routes.py         # Community features
│   │   │   ├── ideas_routes.py             # Ideas/posts
│   │   │   ├── ideas_input_routes.py       # Idea submission
│   │   │   ├── comments_routes.py          # Comments on posts
│   │   │   ├── follow_routes.py            # Follow/unfollow system
│   │   │   ├── checkfollow_routes.py       # Check follow status
│   │   │   ├── notification_routes.py      # Push notifications
│   │   │   ├── live_routes.py              # Live events
│   │   │   ├── barise_bot_routes.py        # AI chatbot (Barise)
│   │   │   ├── business_routes.py          # Business plan analysis
│   │   │   ├── ads_routes.py               # Advertisements/promotions
│   │   │   ├── avatar_routes.py            # User avatars
│   │   │   ├── chat_helper_routes.py       # Chat utilities
│   │   │   ├── report_routes.py            # Report posts/users
│   │   │   ├── invite_share_routes.py      # Share & invite links
│   │   │   ├── celery_routes.py            # Async task management
│   │   │   ├── mongo_routes.py             # MongoDB utilities
│   │   │   ├── add_user_routes.py          # User creation
│   │   │   ├── push_routes.py              # Push notification APIs
│   │   │   ├── search_routes.py            # Full-text search
│   │   │   ├── health_routes.py            # Health check endpoints
│   │   │   ├── test_routes.py              # Testing endpoints
│   │   │   ├── test_data_routes.py         # Test data generation
│   │   │   └── [28 route files total]
│   │   │
│   │   ├── schemas/            # Pydantic models (request/response schemas)
│   │   │   └── [Data validation models]
│   │   │
│   │   ├── services/           # Business logic
│   │   │   └── news_fetcher.py             # Fetch news for feed
│   │   │
│   │   ├── utils/              # Utility functions
│   │   │   ├── auth.py                     # JWT verification, token parsing
│   │   │   ├── ads_scheduler.py            # Schedule ads display
│   │   │   ├── notification.py             # Push notification system
│   │   │   └── [Other utilities]
│   │   │
│   │   ├── websocket/          # WebSocket management
│   │   │   ├── chat_manager.py             # Handle chat events & message routing
│   │   │   ├── connection_manager.py       # Manage WebSocket connections
│   │   │   ├── notification_manager.py     # Handle notifications via WebSocket
│   │   │   ├── redis_manager.py            # Redis integration for real-time
│   │   │   └── [WebSocket utilities]
│   │   │
│   │   ├── sockets/            # Socket.io handlers (legacy/compatibility)
│   │   │   └── [Socket event handlers]
│   │   │
│   │   └── uploads/            # Uploaded files storage
│       └── [User uploads, avatars, documents]
│   │
│   ├── core/                   # Configuration & core utilities
│   │   ├── config.py           # Settings (env variables, constants, API keys)
│   │   ├── firebase.py         # Firebase initialization
│   │   ├── logging_config.py   # Logging setup
│   │   ├── scheduler.py        # APScheduler for background tasks
│   │   ├── rate_limiter.py     # Rate limiting system
│   │   ├── decorators.py       # Custom decorators
│   │   ├── socket_manager.py   # Socket.io manager
│   │   ├── celery.py           # Celery configuration
│   │   └── [Core utilities]
│   │
│   ├── db/                     # Database management
│   │   ├── mongo.py            # MongoDB connection & collection initialization
│   │   └── redis.py            # Redis connection
│   │
│   └── celery_tasks/           # Async tasks (Celery)
│       ├── search_tasks.py              # Search embedding updates
│       ├── socketchat_tasks.py          # Chat-related tasks
│       └── [Other async tasks]
│
├── docs/
│   ├── architecture.mermaid     # System architecture diagram
│   └── images/
│       └── architecture_diagram.png
│
├── secrets/
│   └── firebase-admin-key.json  # Firebase credentials
│
└── uploads/
    ├── avatars/                # User avatar images
    ├── ideas/                  # Idea attachments
    └── Secrets/                # Sensitive uploads

```

### API Endpoints (50+ routes)

**Base URL**: `/api/v1`

**Authentication & Users:**
- `POST /auth/login` - User login
- `POST /auth/signup` - User registration
- `POST /auth/refresh` - Refresh JWT token
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update profile
- `POST /user/avatar` - Upload avatar

**Community Features:**
- `GET /community/feed` - Get community feed
- `POST /community/posts` - Create post
- `GET /community/posts/{id}` - Get post details
- `POST /community/posts/{id}/like` - Like post
- `POST /community/posts/{id}/comment` - Add comment
- `DELETE /community/posts/{id}` - Delete post

**Chat System:**
- `GET /chat/{chat_id}/messages` - Get chat history
- `POST /chat/{chat_id}/messages` - Send message (REST)
- `GET /chat/list` - List user's chats
- `POST /chat/create` - Start new chat

**WebSocket Endpoints:**
- `WS /ws/notifications` - Receive notifications in real-time
- `WS /ws/chat` - Real-time chat with events:
  - `join_user_room` - User joins their personal room
  - `send_message` - User sends message
  - `join_chat_room` - User joins specific chat
  - `typing_start` / `typing_stop` - Typing indicators
  - `message_read` - Read receipts
  - `heartbeat` - Keep alive
- `WS /ws/chats` - SocketChat endpoint (legacy)
- `WS /ws/combined` - Combined notifications + chat endpoint

**Follow System:**
- `POST /user/{id}/follow` - Follow user
- `POST /user/{id}/unfollow` - Unfollow user
- `GET /user/{id}/followers` - List followers
- `GET /user/{id}/following` - List following

**Ideas/Posts:**
- `GET /ideas` - List ideas
- `POST /ideas` - Create idea
- `GET /ideas/{id}` - Get idea details
- `PUT /ideas/{id}` - Update idea
- `DELETE /ideas/{id}` - Delete idea

**Notifications:**
- `GET /notifications` - Get notifications
- `POST /notifications/mark-read` - Mark as read
- `DELETE /notifications/{id}` - Delete notification
- `POST /notifications/subscribe` - Push notification subscription

**Live Events:**
- `GET /live/events` - List live events
- `POST /live/stream` - Start live stream
- `POST /live/{id}/join` - Join live event

**Business Analysis (AI):**
- `POST /business/analyze-plan` - Analyze business plan PDF
- `POST /business/swot-analysis` - Generate SWOT analysis
- `POST /business/gtm-strategy` - Generate GTM strategy
- `POST /business/pitch-analysis` - Analyze pitch deck

**Search:**
- `GET /search` - Full-text search (with ML embeddings)
- `GET /search/trending` - Trending topics

**AI Chatbot:**
- `POST /barise/chat` - Send message to Barise bot
- `GET /barise/config` - Get bot configuration

**Ads/Promotions:**
- `GET /ads` - Get active advertisements
- `POST /ads` - Create ad (admin)

**Admin Endpoints:**
- `GET /test-data` - Generate test data
- `GET /health` - Health check
- `POST /celery/task` - Monitor Celery tasks
- `GET /websocket/info` - WebSocket connection stats

### Database Collections (MongoDB)

**User/Auth Collections:**
- `users` - User accounts with profiles
- `services` - Service offerings by users

**Community Collections:**
- `community_hub` (main collection)
  - `posts` - Community posts
  - `comments` - Comments on posts
  - `follows` - Follow relationships
  - `chats` - Direct message conversations
  - `notifications` - User notifications
  - `ideas` - Ideas/project submissions
  - `events` - Live events
  - `invites` - Share/invite links
  - `shares` - Shared content
  - `reports` - Reported content
  - `bookmarks` - Saved posts

**Business Collections:**
- `orders` - User orders
- `transactions` - Payment transactions
- `subscriptions` - Subscription plans
- `promo_codes` - Promotional codes
- `promo_usage` - Promo code usage

**Admin Collections:**
- `feedback` - User feedback
- `news_collections` - News feed items
- `promotions` - Advertiser promotions
- `statistics` - Analytics data

### Core Features & Systems

#### 1. **Real-Time Chat System**
- **WebSocket Protocol**: Native FastAPI WebSockets
- **Redis Integration**: Message pub/sub, presence tracking
- **Features**:
  - Direct messaging between users
  - Typing indicators
  - Message read receipts
  - Online/offline presence
  - Room-based chat management
  - Rate limiting per user

#### 2. **Authentication & Security**
- **JWT Tokens**: Secure cookie-based auth
- **Rate Limiting**: Per-endpoint limits (auth: 30/min, upload: 60/min, etc.)
- **Secure Cookies**: Configurable domain, SameSite, secure flags
- **Token Refresh**: Automatic token rotation

#### 3. **Background Jobs (Celery + Redis)**
- **Message Processing**: Async message delivery with Redis queue
- **Search Embeddings**: Generate and cache ML embeddings for search
- **News Fetching**: Periodic web scraping for news feed
- **Notifications**: Send push notifications asynchronously
- **Ads Scheduler**: Display ads at scheduled times

#### 4. **AI/ML Integration**
- **Sentence Transformers**: Generate embeddings for search/matching
- **scikit-learn**: ML models for recommendations
- **NLTK**: Natural language processing
- **OpenAI API**: ChatGPT integration for Barise bot
- **Azure AI**: Document Intelligence for PDF analysis

#### 5. **Document Processing**
- **PyPDF2/PyMuPDF**: Extract text from PDFs
- **python-pptx**: Process PowerPoint presentations
- **python-docx**: Handle Word documents
- **OCR (Tesseract)**: Extract text from images
- **Document Analysis**: Business plan scoring, pitch deck evaluation

#### 6. **File Storage**
- **Azure Blob Storage**: Cloud file uploads
- **Local Uploads**: Avatars, ideas, documents stored in `uploads/`
- **Image Processing**: Pillow for image resizing, compression

#### 7. **Push Notifications**
- **Web Push**: Service Worker integration
- **Firebase**: Cloud messaging
- **Real-time Delivery**: Via WebSocket fallback

#### 8. **Scheduling & Background Tasks**
- **APScheduler**: Schedule trending score updates
- **Ads Scheduler**: Schedule ad impressions
- **News Fetcher**: Periodic news refresh

### Environment Configuration

Key environment variables (from config.py):
```python
ENVIRONMENT          # "development" | "production"
PROJECT_NAME         # Project identifier
API_V1_STR          # "/api/v1"
SECRET_KEY          # JWT signing key
AUTH_COOKIE_*       # Cookie configuration

MONGODB_URI         # MongoDB connection string
MONGODB_DB_NAME     # Database name ("barise_auth_db")
USE_LOCAL_MONGO     # Use local MongoDB

REDIS_HOST, PORT, PASSWORD, DB  # Redis config
REDIS_SSL           # Enable SSL for Redis

CELERY_BROKER_URL   # Redis broker address
CELERY_RESULT_BACKEND  # Redis backend

RATE_LIMIT_*        # Rate limiting thresholds
MESSAGE_LIMIT_FOR_NON_FOLLOWERS  # Chat restrictions
```

### API Documentation
- **Swagger UI**: Available at `http://localhost:8000/docs`
- **ReDoc**: Available at `http://localhost:8000/redoc`
- Automatically generated from FastAPI models

---

## 🔄 Frontend-Backend Communication

### API Client Setup
- **Base URL**: Configured in `@/config/env`
- **Authentication**: JWT token in Authorization header or cookie
- **Error Handling**: ApiRateLimitError, ApiRequestError custom classes
- **Data Fetching**: TanStack React Query for caching & mutations

### WebSocket Connection
**Frontend → Backend:**
- Connects to `ws://localhost:8000/api/v1/ws/chat`
- Sends JWT token in query params or cookies
- Listens for real-time chat messages

**Event Flow:**
```
Frontend → WS → Backend (FastAPI)
  ↓
Chat Manager processes event
  ↓
Redis pub/sub broadcasts to other connections
  ↓
Backend → WS → All connected clients
```

### Data Flow

**Example: Send Chat Message**
1. User types message in React Chat component
2. Form submitted with WebSocket event: `{ type: "send_message", data: {...} }`
3. Backend receives via `websocket_routes.py`
4. `chat_manager.process_send_message()` stores in MongoDB
5. Redis publishes to chat room subscribers
6. Message delivered to all participants
7. Frontend receives & updates local state

---

## 🚀 Deployment

### Docker Compose Services
- **FastAPI Web**: Port 8000 (Uvicorn)
- **MongoDB**: Port 27018 (attached to 27017 internally)
- **Redis**: Port 6380 (attached to 6379 internally)
- **Celery Worker**: Processes async tasks
- **Frontend** (Vite): Port 3000 (dev server)

### Running Locally
```bash
# Backend
cd FASTAPI_COMMUNITY
docker-compose up --build

# Frontend
cd lliveupdatedstreaming
npm install
npm run dev  # Runs on http://localhost:5173 or 3000
```

---

## 📊 Key Metrics

**Backend Files:**
- 28+ route modules
- 10+ WebSocket handlers
- 8+ database collections
- Rate-limited endpoints

**Frontend:</code:**
- 50+ routes
- 100+ React components
- Redux store with slices
- TypeScript strict mode

---

## 🔑 Key Unique Features

1. **Real-Time Community Platform**: Live chat, typing indicators, presence
2. **AI-Powered Tools**: Business plan analysis, SWOT generator, pitch analysis
3. **Matching System**: Founder-investor-mentor matching using ML
4. **Document Processing**: PDF/PPT analysis with OCR
5. **Social Features**: Posts, comments, follows, notifications
6. **Payment Integration**: Cashfree for subscriptions
7. **Async Processing**: Celery for background jobs with Flower monitoring
8. **Enterprise Security**: Rate limiting, JWT auth, secure cookies

---

## 📝 Summary

This is a **full-stack, production-ready platform** combining:
- Modern React SPA frontend with TypeScript
- High-performance FastAPI backend
- Real-time WebSocket communication
- MongoDB for flexible document storage
- Redis for caching and real-time messaging
- Celery for async task processing
- ML/AI capabilities for content analysis and matching
- Cloud storage (Azure) for scalability

The architecture supports **real-time collaboration**, **AI-driven features**, and **enterprise-scale deployment**.
