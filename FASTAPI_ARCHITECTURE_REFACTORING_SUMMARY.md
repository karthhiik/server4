# FastAPI Flask Pattern Refactoring - Implementation Summary

## Overview
Successfully refactored FastAPI `Server1_FastApi` to implement Flask architectural patterns while maintaining FastAPI's async capabilities for production-grade performance.

## Architecture Philosophy
The refactoring maintains two core principles:
1. **Flask-like Pattern**: Decorators (@token_required, @service_check), pure functions, simple route handlers
2. **FastAPI Performance**: Async/await throughout, non-blocking I/O, concurrent request handling

## Phases Completed

### ✅ Phase 1: Authentication Layer (app/core/auth.py)

#### Decorators Implemented

**@token_required**
- Extracts JWT from Authorization header (Bearer scheme)
- Validates token signature and expiry
- Verifies user exists in MongoDB
- Injects user_id as first positional argument
- Flask equivalent: `server2/blueprints/swot_plan.py` line 269

```python
@router.post("/api/endpoint")
@token_required
async def create_something(user_id: str, request: Request, data: Schema) -> dict:
    # user_id automatically injected from token
```

**@service_check(service_id)**
- Decorator factory for service access control
- Checks promo code access first (takes precedence)
- Falls back to subscription-based access
- Decrements tokens_remaining on successful access
- Logs service usage for audit trails
- Flask equivalent: `server2/blueprints/swot_plan.py` line 300

```python
@router.post("/api/swot")
@token_required
@service_check("309")
async def create_swot(user_id: str, request: Request, data: SwotCreate) -> dict:
    # Only reached if user has service 309 access
```

#### Rate Limiting (Thread-Safe)
- `check_rate_limit(user_id)` - Check if user/global limits exceeded
- `increment_user_requests(user_id)` - Thread-safe counter increment
- `decrement_user_requests(user_id)` - Thread-safe counter decrement
- `get_active_request_stats()` - Get tracking statistics

Limits:
- Per-user: 5 concurrent requests
- Global: 50 concurrent requests

#### Design Approach
- FastAPI-compatible async decorators
- Extract Request from kwargs in wrapper
- Handler chain: request.headers → token_required → service_check → route function
- All database operations async via Motor/MongoDB

---

### ✅ Phase 2: SWOT Service Refactoring (app/services/swot_service.py)

#### Service Functions (Pure Function Pattern)

All functions follow the Flask pattern:
- Take all inputs as parameters
- Return dictionaries (never None without raising)
- Raise exceptions for errors (not return error dicts)
- No class methods - all module-level functions
- Async/await for I/O operations

**AI Generation Functions**

1. `generate_swot_analysis(...)` - SWOT (S,W,O,T with 4 points each)
2. `generate_competitor_analysis(...)` - 3 competitors with 5 analysis points each
3. `generate_value_proposition(...)` - Customer profile + Value proposition (3 points each)
4. `generate_risk_analysis(...)` - Financial/Operational/Market risks (4 points each)
5. `generate_market_segmentation(...)` - Demographic/Psychographic/Behavioral (4 points each)

**Supporting Functions**

6. `get_ai_completion(prompt, system_prompt, request_id)` - Azure OpenAI integration
7. `get_industry_growth(industry, timeout)` - SerpAPI data collection

**Database Functions**

8. `save_swot_plan(user_id, request_id, business_name, ...)` - Insert to MongoDB
9. `get_swot_plan(plan_id, user_id)` - Retrieve user's plan
10. `list_user_swot_plans(user_id, limit, offset)` - Paginated listing
11. `delete_swot_plan(plan_id, user_id)` - Delete with auth check

#### Key Characteristics
- System prompt defined as module-level constant
- Thread-safe database operations using Motor
- Request tracking via request_id parameter
- Exception-based error handling
- Comprehensive logging throughout

#### Azure OpenAI Integration
- Async client via `AsyncAzureOpenAI`
- Settings-based configuration (endpoint, deployment, etc.)
- JSON response parsing with markdown cleanup
- Timeout handling with graceful fallbacks

#### SerpAPI Integration
- Industry growth rate extraction
- Regex-based percentage parsing
- Timeout-safe HTTP via httpx.AsyncClient
- Default fallback value (5.0%) if unavailable

---

### ✅ Phase 3: SWOT Routes Refactoring (app/api/routes/swot_routes.py)

#### Route Handlers (Simplified Pattern)

Removed:
- ❌ Dependency injection (`Depends()`)
- ❌ Complex imports from `app.api.deps`
- ❌ Service class instantiation

Implemented:
- ✅ Flask-style decorators for auth/service checks
- ✅ Direct service function calls
- ✅ Simplified error handling with HTTPException
- ✅ Inline rate limiting checks

#### Routes Implemented (5 Analysis Types)

**POST /api/swot** (Service 309)
- Generate SWOT analysis
- Maps to Flask: `server2/blueprints/swot_plan.py` line 415
- Requires @token_required + @service_check("309")

**POST /api/competitor-analysis** (Service 310)
- Generate competitor analysis
- Maps to Flask: line 685

**POST /api/value-proposition-canvas** (Service 311)
- Generate value proposition canvas
- Maps to Flask: line 1260

**POST /api/risk-analysis** (Service 312)
- Generate risk analysis
- Maps to Flask: line 1495

**POST /api/market-segmentation** (Service 313)
- Generate market segmentation
- Maps to Flask: line 1752

#### CRUD Routes

**GET /api/swot/{plan_id}**
- Retrieve specific SWOT plan
- Authorization check only (@token_required)

**GET /api/user-swot-plans**
- List user's SWOT plans with pagination
- Parameters: limit (1-100, default 20), offset (default 0)

**DELETE /api/delete-swot/{plan_id}**
- Delete SWOT plan with auth check

#### System Routes

**GET /api/system/status**
- Active request metrics
- Per-user and global limits
- Total active requests

**GET /api/system/health**
- Simple health check
- Returns status and active thread count

#### Error Handling
- 401 Unauthorized (missing/invalid token)
- 403 Forbidden (no service access)
- 404 Not Found (user/plan not found)
- 429 Too Many Requests (rate limit exceeded)
- 500 Internal Server Error (AI/database failures)

#### Response Structure
```python
{
    "swot": {
        "strengths": [{"point": "..."}, ...],
        "weaknesses": [...],
        "opportunities": [...],
        "threats": [...]
    },
    "industryGrowth": 5.2,
    "requestId": "uuid",
    "planId": "mongodb_id"
}
```

---

## Code Structure Comparison

### Before (FastAPI Class-Based)
```python
# Service
class SWOTService:
    async def generate_swot(self, data: dict) -> dict:
        self.client.chat.completions.create(...)
        return result

# Route
async def generate_swot(
    data: SwotCreate,
    current_user: str = Depends(get_current_user),
    user: str = Depends(service_required("309")),
):
    service = SWOTService()
    await service.generate_swot(data)
```

### After (Flask Pure Function Pattern)
```python
# Service
async def generate_swot_analysis(
    business_name: str,
    industry: str,
    ...
) -> dict:
    client = _get_azure_client()
    response = await client.chat.completions.create(...)
    return parsed_result

# Route  
@router.post("/api/swot")
@token_required
@service_check("309")
async def create_swot(user_id: str, request: Request, data: SwotCreate) -> dict:
    result = await generate_swot_analysis(
        business_name=data.businessName,
        ...
    )
    return {"swot": result, ...}
```

**Benefits:**
- Simpler function signatures
- Easier to test (no class coupling)
- Clearer dependencies (all parameters explicit)
- Flask-familiar patterns for team consistency
- Better readability and maintainability

---

## Database Schema Integration

### Collections Used
- `users` - User accounts and service access tracking
- `subscriptions` - Subscription details and token tracking
- `swot_plans` - Generated SWOT analyses

### Document Structure (swot_plans)
```python
{
    "_id": ObjectId,
    "user_id": str,
    "request_id": str,
    "created_at": datetime,
    "business_name": str,
    "industry": str,
    "business_description": str,
    "target_market": str,
    "strengths": str,
    "weaknesses": str,
    "opportunities": str,
    "threats": str,
    "growth_rate": float,
    "swot_analysis": {
        "strengths": [...],
        "weaknesses": [...],
        "opportunities": [...],
        "threats": [...]
    }
}
```

---

## Request Flow Example

### Request: Generate SWOT Analysis

```
1. Client sends POST /api/swot with JWT token
   
2. FastAPI routes to @router.post("/api/swot")
   
3. @token_required decorator:
   - Extracts Authorization header
   - Validates JWT signature
   - Checks user exists in DB
   - Injects user_id = "user123"
   - Calls wrapped function with (user_id, request, data)
   
4. @service_check("309") decorator:
   - Receives user_id from @token_required
   - Checks promo access → falls through to subscription
   - Verifies subscription not expired
   - Checks tokens_remaining > 0
   - Verifies service 309 in selected_services
   - Decrements tokens_remaining
   - Logs service usage
   - Calls wrapped function with (user_id, request, data)
   
5. Route handler (create_swot):
   - Checks rate limit: check_rate_limit(user_id)
   - If exceeded: raise HTTPException(429)
   - Increments request counter: increment_user_requests(user_id)
   - Generates growth rate: await get_industry_growth("technology")
   - Generates SWOT: await generate_swot_analysis(...)
   - Saves plan: await save_swot_plan(...)
   - Decrements counter: decrement_user_requests(user_id)
   - Returns response with swot_analysis, industryGrowth, requestId
   
6. Client receives:
   {
       "swot": {...},
       "industryGrowth": 5.2,
       "requestId": "abc-123",
       "planId": "507f1f77bcf86cd799439011"
   }
```

---

## Performance Characteristics

### Concurrency Model
- Per-request async handlers (non-blocking)
- Concurrent database queries via Motor
- Thread-safe rate limiting for controlled throughput
- Global rate limit prevents resource exhaustion

### Rate Limiting
- Soft limit (per-user): 5 concurrent requests
- Hard limit (global): 50 concurrent requests
- Lock-based coordination with threading.Lock
- Returns 429 Too Many Requests if exceeded

### Database Access
- Async Motor client for MongoDB
- Per-user locks for write operations
- Connection pooling via Motor
- Query optimization with indexed fields

### AI API Integration
- Async Azure OpenAI calls
- 30-second timeout for SerpAPI calls
- JSON response caching consideration
- Graceful fallbacks (default growth rate)

---

## Migration Status

### Phase 1-3: COMPLETE ✅
- Authentication layer: 100% implemented
- SWOT service: 100% refactored
- SWOT routes: 100% refactored

### Phase 4-9: PENDING
- GTM service refactoring
- GTM routes refactoring
- Business service refactoring
- Business routes refactoring
- Pitch service refactoring
- Pitch routes refactoring

### Phase 10: PENDING
- Main.py route registration verification
- End-to-end testing

---

## Testing Checklist

### Unit Tests
- [ ] token_required decorator with valid/invalid tokens
- [ ] service_check decorator with various access levels
- [ ] Rate limiting boundary conditions
- [ ] SWOT generation with mocked Azure API
- [ ] Database operations with mocked MongoDB

### Integration Tests
- [ ] Complete request flow with valid token
- [ ] Rate limit enforcement
- [ ] Service access control logic
- [ ] Token decrement on service use
- [ ] Error responses for edge cases

### Load Tests
- [ ] Concurrent request handling
- [ ] Global rate limit enforcement
- [ ] Database connection pool stability

---

## Files Modified

### New Files Created
- ✅ `app/core/auth.py` - Authentication decorators layer

### Files Refactored
- ✅ `app/services/swot_service.py` - Pure function pattern
- ✅ `app/api/routes/swot_routes.py` - Simplified Flask-like routes

### Backup Files
- `app/services/swot_service_old.py` - Old class-based version
- `app/api/routes/swot_routes_old.py` - Old dependency-injection version

---

## Flask Parity Mapping

| Flask Pattern | FastAPI Implementation | Location |
|---------------|------------------------|----------|
| @token_required | token_required decorator | app/core/auth.py |
| @service_check | service_check decorator | app/core/auth.py |
| Pure functions | Service module functions | app/services/swot_service.py |
| Simple routes | Simplified handlers | app/api/routes/swot_routes.py |
| Rate limiting | check_rate_limit() | app/core/auth.py |
| Request tracking | active_requests dict | app/core/auth.py |
| Error responses | HTTPException | app/api/routes/swot_routes.py |

---

## Deployment Considerations

### Environment Variables Required
- AZURE_ENDPOINT_swot or AZURE_OPENAI_ENDPOINT
- AZURE_ENDPOINT_subscription or AZURE_OPENAI_SUBSCRIPTION_KEY
- AZURE_ENDPOINT_apiversion or AZURE_OPENAI_API_VERSION
- AZURE_ENDPOINT_deployment or AZURE_OPENAI_DEPLOYMENT
- SERPAPI_API_KEY (optional, defaults to 5.0% growth)
- MONGODB_URI / MONGO_URI
- SECRET_KEY

### Docker Compatibility
- All changes maintain Docker compatibility
- No OS-specific dependencies added
- Async patterns work in containerized environments
- Ray limiting uses threading (compatible with gevent if needed)

### Azure Integration
- Azure OpenAI API calls maintained
- Motor async MongoDB driver compatible with Azure Cosmos
- No changes to Azure service endpoints

---

## Next Steps

1. **GTM Service Refactoring**: Apply same patterns to business_service and gtm_service
2. **Complete Route Refactoring**: Refactor all remaining routes
3. **Integration Testing**: Test end-to-end flows
4. **Load Testing**: Verify rate limiting and concurrency
5. **Deployment**: Roll out to production environment

---

## Notes

- Request tracking uses socket-safe threading primitives
- All error messages follow consistent format
- Comprehensive logging for debugging
- Service IDs taken from Flask implementation (309-313 for SWOT)
- Rate limits match Flask baseline (5 per-user, 50 global)
- AzureOpenAI client reusable via `_get_azure_client()` factory

