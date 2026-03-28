# Barise Bot - Comprehensive Understanding

## 🤖 Overview

**Barise Bot** is an AI-powered automated content generation system that creates authentic, human-like startup community posts. It leverages:
- **Azure OpenAI (GPT-4)** for intelligent content generation
- **News Scraping** from Indian startup sources
- **Content Analysis** to extract insights
- **Celery** for scheduled/periodic task execution
- **MongoDB** for persistent storage
- **Free Image Generation** services for visuals

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Routes                            │
│    /api/v1/bot/start-bot                                   │
│    /api/v1/bot/stop-bot                                    │
│    /api/v1/bot/status                                      │
│    /api/v1/bot/create-post                                 │
│    /api/v1/auto-posts/* (legacy endpoints)                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              BariseBotManager (Routes)                       │
│  - Credential verification                                  │
│  - Bot state management                                     │
│  - Status tracking                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│          Celery Tasks (barise_bot_tasks.py)                 │
│  - create_automated_post_task                               │
│  - start_minute_posting_task                                │
│  - start_hourly_posting_task                                │
│  - stop_posting_task                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│        BariseBotTasks (Task Implementation)                 │
│  - _generate_post_with_ai()                                 │
│  - create_automated_post()                                  │
│  - _store_post_in_database()                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         Utility Classes (barise_bot.py)                     │
│  - NewsScraper (RSS, Reddit, Web scraping)                  │
│  - ContentAnalyzer (Extract insights)                       │
│  - ImageGenerator (Free image URLs)                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         External Services                                    │
│  - Azure OpenAI (GPT-4 for content)                         │
│  - RSS Feeds (YourStory, Inc42, Economic Times)             │
│  - Reddit API (r/indianstartups, etc)                       │
│  - Pollinations.ai (Free image generation)                  │
│  - MongoDB (Post storage)                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 API Endpoints

### Starting the Bot

**POST** `/api/v1/bot/start-bot`
```python
# Request
{
    "interval_minutes": 10  # Optional, default=10, range 1-60
}

# Response
{
    "success": true,
    "message": "Bot started (10-minute interval)",
    "status": {
        "history_count": 45,
        "posts_today": 3,
        "minute_posting_active": true,
        "hourly_posting_active": false,
        "last_posted": "2026-03-14T10:30:00Z"
    }
}
```

### Stopping the Bot

**POST** `/api/v1/bot/stop-bot`
```python
# Request (requires credentials)
{
    "username": "admin@example.com",
    "password": "password123"
}

# Response
{
    "success": true,
    "message": "Bot stopped",
    "status": {...}
}
```

### Hourly Posting

**POST** `/api/v1/bot/start-hour-bot`
- Starts posting every hour instead of every N minutes

**POST** `/api/v1/bot/stop-hour-bot`
- Requires credentials
- Stops hourly posting

### Status Check

**GET** `/api/v1/bot/status`
```python
# Response
{
    "success": true,
    "status": {
        "history_count": 45,          # Total posts created
        "posts_today": 3,             # Posts in last 24 hours
        "minute_posting_active": true,  # Is minute-based schedule running?
        "hourly_posting_active": false, # Is hourly schedule running?
        "last_posted": "2026-03-14T10:30:00Z"  # ISO timestamp of last post
    }
}
```

### Create Single Post

**POST** `/api/v1/bot/create-post`
```python
# Response
{
    "success": true,
    "message": "Post creation started",
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Legacy Endpoints (Flask Compatibility)

- **POST** `/api/v1/auto-posts/start` - Same as /bot/start-bot
- **POST** `/api/v1/auto-posts/stop` - Same as /bot/stop-bot
- **GET** `/api/v1/auto-posts/status` - Same as /bot/status
- **POST** `/api/v1/auto-posts/create-single` - Same as /bot/create-post

---

## 🔐 Authentication

The bot uses **credential verification** for control:

```python
class BariseBotManager:
    def __init__(self, mongodb_uri: str, openai_config: dict):
        self.admin_username = settings.ADMIN_USERNAME_SOURCE
        self.admin_password = settings.ADMIN_PASSWORD_SOURCE
    
    async def verify_credentials(self, credentials: BotCredentials) -> bool:
        # Check 1: Hardcoded admin credentials from config
        if (credentials.username == self.admin_username and 
            credentials.password == self.admin_password):
            return True
        
        # Check 2: Database user with password hash
        user = await users_collection.find_one({"user_id": credentials.username})
        if user and check_password_hash(user["password"], credentials.password):
            return True
        
        return False
```

**Protected Operations:**
- `POST /bot/stop-bot` - Requires credentials
- `POST /bot/stop-hour-bot` - Requires credentials
- (Stop operations prevent accidental shutdowns)

---

## 📰 Data Flow: Creating a Post

### Step 1: News Scraping

`NewsScraper` fetches from multiple sources:

```
RSS Feeds:
├── YourStory (https://yourstory.com/feed)
├── Inc42 (https://inc42.com/feed/)
├── Economic Times (Startups RSS)
├── Business Standard (Startups RSS)
├── LiveMint (Companies)
├── Hindu Business Line
├── Financial Express
└── MoneyControl (Startups)

Reddit Subreddits:
├── r/indianstartups
├── r/startup_india
├── r/bangalore
└── r/developersIndia

Web Scraping:
└── YourStory homepage (BeautifulSoup)
```

**Example News Item:**
```python
{
    "title": "Fintech startup raises $5M Series A",
    "summary": "Delhi-based payment platform...",
    "link": "https://example.com/article",
    "source": "YourStory",
    "published": "2026-03-14T08:00:00Z",
    "upvotes": 245  # Reddit only
}
```

### Step 2: Content Analysis

`ContentAnalyzer` extracts insights:

```python
insights = {
    "trending_topics": ["AI/ML", "Fintech", "Web3"],
    "companies_mentioned": ["PhonePe", "Razorpay", "Byju's"],
    "funding_amounts": ["$5M", "₹50 crore", "$2B"],
    "sectors": ["Fintech", "Edtech", "SaaS"],
    "key_trends": ["Regulatory compliance", "Profitability focus"]
}

# Extraction logic:
# - Regex matching for funding patterns: [$₹]\s*[\d,]+\s*(?:crore|lakh|million|...)
# - Company name extraction: [A-Z][a-zA-Z]+(?:[\s-][A-Z][a-zA-Z]+)*
# - Sector matching against predefined list
```

### Step 3: AI-Powered Post Generation

Uses **Azure OpenAI (GPT-4)** with sophisticated prompting:

```python
prompt = f"""
Create an AUTHENTIC, HUMAN-LIKE startup post for Barise community.

TOPIC: {topic}  # e.g., "Startup Journey"
POST CATEGORY: {post_category}  # Wins, Ask, Deep Talk, Event, Deal, Collab
CONTENT TYPE: {content_type}    # Story, Tips, Question, Observation
TIME CONTEXT: {time_context}    # Morning motivation, Afternoon actionable advice, etc.

NEWS CONTEXT: {json.dumps(news_context)}

[Detailed examples and enhanced context rules...]

STRICT REQUIREMENTS:
- MAXIMUM 1800 characters
- Write as REAL Indian founder
- Include specific numbers, timeframes, locations
- Mix professional insights with personal vulnerability
- Conversational language with strategic pauses
- Regional Indian context
- End with community engagement question
- 5-8 relevant hashtags
- Strategic emoji usage

Return JSON with:
{{
    "category": string,
    "content_type": string,
    "hook": "Opening line",
    "story": "Personal experience",
    "insight": "Key lesson",
    "community_element": "Engaging question",
    "full_post": "Complete post <1800 chars",
    "hashtags": ["#tag1", "#tag2"],
    "character_count": int,
    "expected_engagement": "High/Medium/Low"
}}
"""
```

**Smart Post Categorization:**
- **Time-Based**: Morning (motivation), Midday (strategy), Afternoon (actionable), Evening (reflection), Late night (struggles)
- **Context-Enhanced**: Funding + investments, Startup challenges, Motivation, Mentorship, Student founders, Tech trends, Market opportunities
- **Category Rotation**: Wins, Ask, Deep Talk, Event, Deal, Collab
- **Content Types**: Story, Tips, Question, Observation

### Step 4: Image Generation

Generates accompanying images:

```python
class ImageGenerator:
    @staticmethod
    def generate_image_url(prompt: str) -> str:
        # Services:
        # 1. https://pollinations.ai/p/{prompt}?width=1080&height=1080
        # 2. https://image.pollinations.ai/prompt/{prompt}
        
        # Result: Direct image URLs, no authentication needed
```

### Step 5: Database Storage

Stores in MongoDB `community_db.posts`:

```python
{
    "_id": ObjectId(...),
    "title": "3am. That's when our servers crashed...",
    "category": "Wins",
    "content": "Full 1800-char post content...",
    "callToAction": "Hype it",  # Get Call To Action from category
    "circleId": None,
    "mediaType": "image",
    "mediaUrl": "https://pollinations.ai/...",
    "tags": ["#StartupWins", "#TechScaling", "#FounderLife"],
    "author": {
        "user_id": "barisebot@gmail.com",
        "name": "BariseBot",
        "role": "Bot",
        "photo": None
    },
    "createdAt": datetime.now(UTC),
    "updatedAt": datetime.now(UTC),
    "likes": 0,
    "commentsCount": 0,
    "trending": False,
    "autoGenerated": True,
    "generationMetadata": {
        "news_reference": "YourStory article: ...",
        "character_count": 1245,
        "generated_at": "2026-03-14T10:30:00Z"
    }
}
```

Also updates global statistics:

```python
# MongoDB update
db["community_db.stats"].update_one(
    {"_id": "global_stats"},
    {
        "$inc": {"total_posts": 1},
        "$set": {"last_updated": datetime.now(UTC)}
    },
    upsert=True
)
```

---

## ⏱️ Scheduling System (Celery Beat)

### Minute-Based Posting

```python
@celery_app.task(name="app.celery_tasks.barise_bot_tasks.start_minute_posting_task")
def start_minute_posting_task(interval_minutes: int):
    """
    Dynamically creates a Celery Beat schedule
    """
    celery_app.conf.beat_schedule = {
        f"create-automated-post-every-{interval_minutes}-minutes": {
            "task": "app.celery_tasks.barise_bot_tasks.create_automated_post_task",
            "schedule": interval_minutes * 60,  # Convert to seconds
        }
    }
    # Posts run every N minutes until stopped
```

**Example:** 10-minute interval creates posts at:
- 10:00 AM
- 10:10 AM
- 10:20 AM
- 10:30 AM
- ...

### Hourly Posting

```python
@celery_app.task(name="app.celery_tasks.barise_bot_tasks.start_hourly_posting_task")
def start_hourly_posting_task():
    celery_app.conf.beat_schedule = {
        "create-automated-post-every-hour": {
            "task": "app.celery_tasks.barise_bot_tasks.create_automated_post_task",
            "schedule": 3600,  # 1 hour in seconds
        }
    }
```

### Stopping Posting

```python
@celery_app.task(name="app.celery_tasks.barise_bot_tasks.stop_posting_task")
def stop_posting_task():
    celery_app.conf.beat_schedule = {}  # Clear all schedules
```

---

## 🔄 Complete Workflow Example

```
User Request:
POST /api/v1/bot/start-bot?interval_minutes=15

↓

BariseBotManager.start_bot():
  1. Call start_minute_posting_task.delay(15)
  2. Set bot_manager.minute_posting_active = True
  3. Return status response

↓

Celery Beat Scheduler:
Every 15 minutes:
  1. Enqueue create_automated_post_task

↓

Celery Worker executes create_automated_post_task():
  1. Initialize BariseBotTasks
  2. await bot_tasks.create_automated_post()

↓

Create Post Flow:
  1. NewsScraper.scrape_startup_news()
     └─ Scrape RSS feeds, Reddit, web pages
  
  2. ContentAnalyzer.extract_key_insights()
     └─ Extract topics, companies, funding, sectors
  
  3. _generate_post_with_ai(news_context)
     └─ Call Azure OpenAI GPT-4
     └─ Receive JSON with post content, hashtags
  
  4. ImageGenerator.generate_image_url()
     └─ Create image using Pollinations.ai
  
  5. _store_post_in_database()
     └─ Insert into MongoDB community_db.posts
     └─ Update global statistics

↓

Result:
  ✅ Post appears in community with:
     - Auto-generated content
     - Relevant hashtags
     - Accompanying image
     - Metadata tracking generation

POST CREATED
```

---

## 🎯 Post Creation Strategy

### Content Categories

| Category | Use Case | CTA |
|----------|----------|-----|
| **Wins** | Celebrate successes | Hype it |
| **Ask** | Seek advice/help | Help |
| **Deep Talk** | Philosophical/reflections | Feedback |
| **Event** | Announce meetings/webinars | Connect |
| **Deal** | Share offers/opportunities | Connect |
| **Collab** | Find collaboration partners | Collab |

### Content Types

| Type | Approach |
|------|----------|
| **Story** | Narrative with emotional arc |
| **Tips** | Actionable, practical advice |
| **Question** | Engaging community participation |
| **Observation** | Commentary on trends |

### Authentication Elements

The bot builds credibility through:
- Specific numbers & metrics ("50,000+ concurrent users")
- Real timeframes ("6 months later")
- Personal vulnerability ("sitting in my pajamas")
- Industry terminology
- Indian startup context
- Specific locations ("Bangalore/Mumbai")
- Currency relevant to India ("INR")

---

## 📊 State Tracking

The `BariseBotManager` maintains state:

```python
class BariseBotManager:
    def __init__(self, ...):
        self.minute_posting_active = False     # Is minute schedule running?
        self.hourly_posting_active = False     # Is hourly schedule running?
    
    async def get_status(self) -> BotStatusResponse:
        # Fetch from database:
        latest_post = await posts_collection.find_one(
            {"author.user_id": "barisebot@gmail.com"},
            sort=[("createdAt", -1)]
        )
        
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        posts_today = await posts_collection.count_documents({
            "author.user_id": "barisebot@gmail.com",
            "createdAt": {"$gte": today_start}
        })
        
        return BotStatusResponse(
            history_count=100,              # Total ever
            hourly_posting_active=False,
            last_posted="2026-03-14T10:30:00Z",
            minute_posting_active=True,
            posts_today=5
        )
```

---

## 🛠️ Configuration

Environment variables required:

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_ENDPOINT=https://<name>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=barise_auth_db

# Celery & Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Admin credentials for bot control
ADMIN_USERNAME_SOURCE=admin@example.com
ADMIN_PASSWORD_SOURCE=secure_password
```

---

## 🚨 Error Handling

### Fallback Mechanism

If Azure OpenAI fails, uses template fallback:

```python
async def _create_fallback_post(self, context: dict) -> dict:
    templates = [
        "🚀 The Indian startup ecosystem is buzzing!...",
        "💡 Real talk: Building in India is different..."
    ]
    
    # Returns valid post structure
    return {
        "category": "Deep Talk",
        "full_post": template,
        "hashtags": ["IndianStartups", ...],
        "character_count": len(template),
        "news_reference": "General market trends"
    }
```

### Retries

```python
@celery_app.task(bind=True, max_retries=3)
def create_automated_post_task(self):
    try:
        return asyncio.run(_create_post())
    except Exception as e:
        # Retry after 5 minutes, up to 3 times
        raise self.retry(countdown=300, exc=e)
```

---

## 📈 Key Metrics

The bot tracks:

- `history_count` - Total posts ever created
- `posts_today` - Posts in last 24 hours
- `last_posted` - ISO timestamp of most recent post
- `minute_posting_active` - Boolean schedule state
- `hourly_posting_active` - Boolean schedule state

All posts marked as `"autoGenerated": True` for tracking.

---

## 🔗 Integration Points

### With Community

- Posts appear in community feed as normal posts
- Full community interactions (likes, comments, shares)
- Author shown as "BariseBot" with role "Bot"

### With User System

- Uses existing post schema
- Integrates with existing collection structure

### With Analytics

- Tracked via `generationMetadata` field
- Global statistics updated in `community_db.stats`

---

## 🎓 Key Learnings

1. **Authentic Voice**: Bot trained with examples of real founder experiences
2. **News-Driven**: Content grounded in actual Indian startup news
3. **Time-Aware**: Posts adjust tone based on time of day
4. **Flexible Scheduling**: Both minute and hourly intervals supported
5. **Fallback Safety**: Never fails completely, has template fallback
6. **Secure Control**: Credential verification for stopping bot
7. **Searchable**: Hashtags and keywords extracted for discoverability
8. **Traceable**: Full metadata stored for auditing AI generation

