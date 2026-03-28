# FastAPI Flask Pattern Refactoring - Completion Action Plan

## Executive Summary

The FastAPI Server1_FastApi refactoring to Flask patterns is 40% complete:
- ✅ **COMPLETE**: Core authentication layer (app/core/auth.py)
- ✅ **COMPLETE**: SWOT service refactoring (app/services/swot_service.py)
- ✅ **COMPLETE**: SWOT routes refactoring (app/api/routes/swot_routes.py)
- ⏳ **PENDING**: GTM service refactoring (~3-4 hours)
- ⏳ **PENDING**: Business service refactoring (~2 hours)
- ⏳ **PENDING**: Pitch service refactoring (~2 hours)
- ⏳ **PENDING**: Integration & load testing (~3 hours)

**Total Estimated Remaining**: 10-15 hours

---

## Phase 4: GTM Service Refactoring

### File: `app/services/gtm_service.py`

#### Current State: Class-Based (❌ To be refactored)
```python
class GTMService:
    def __init__(self):
        self.ai_client = ...
        self.deployment = ...
    
    def generate_plan(self, ...):
        # 140+ lines of orchestration
    
    def _get_enhanced_industry_analysis(self, ...):
        # 46 lines
    
    # ... 17+ more private methods
```

#### Target State: Pure Functions (✅)

**Step 1: Create Factory Functions for Clients**
```python
def _get_ai_client():
    """Factory function for Azure OpenAI client"""
    return ai_factory.get_client("gtm")

def _get_ai_deployment():
    """Get GTM deployment name"""
    return ai_factory.get_deployment("gtm")

def _get_serpapi_key():
    """Get Serp API key from settings"""
    return settings.SERPAPI_API_KEY
```

**Step 2: Convert Private Methods to Module Functions**

For each private method in GTMService:
```python
# BEFORE
def _get_industry_growth_rate(self, industry_term: str) -> Dict[str, str]:
    # 60 lines of logic

# AFTER
async def get_industry_growth_rate(industry_term: str) -> Dict[str, str]:
    """Get industry growth rate data from multiple sources"""
    # Same 60 lines of logic
    # Remove 'self.' references
    # Change sync code to async where applicable
```

**List of Functions to Convert** (21 total):
1. `generate_plan()` - Main orchestration (PUBLIC)
2. `_get_enhanced_industry_analysis()` → `get_enhanced_industry_analysis()`
3. `_validate_and_correct_industry()` → `validate_and_correct_industry()`
4. `_get_industry_growth_rate()` → `get_industry_growth_rate()`
5. `_get_google_trends_data()` → `get_google_trends_data()`
6. `_get_news_sentiment()` → `get_news_sentiment()`
7. `_get_free_market_data()` → `get_free_market_data()`
8. `_analyze_market_dynamics()` → `analyze_market_dynamics()`
9. `_get_competitive_landscape()` → `get_competitive_landscape()`
10. `_get_emerging_trends()` → `get_emerging_trends()`
11. `_analyze_regulatory_environment()` → `analyze_regulatory_environment()`
12. `_get_investment_activity()` → `get_investment_activity()`
13. `_format_market_data_for_prompt()` → `format_market_data_for_prompt()`
14. `_construct_comprehensive_gtm_prompt()` → `construct_comprehensive_gtm_prompt()`
15. `_call_ai_for_gtm_plan()` → `call_ai_for_gtm_plan()`
16. `_generate_strategic_nodes()` → `generate_strategic_nodes()`
17. `_generate_node_connections()` → `generate_node_connections()`
18. Plus 4+ utility functions

**Step 3: Handle Async/Sync Code**

GTM service has many sync operations (SerpAPI, News API, etc.):
- Use `httpx.AsyncClient` for all HTTP calls
- Use `asyncio.run_in_executor()` for sync operations if unavoidable
- Prefer async implementations throughout

Example:
```python
# BEFORE (sync)
def get_industry_growth_rate(industry_term):
    response = requests.get("https://...", params=params)
    return response.json()

# AFTER (async)
async def get_industry_growth_rate(industry_term: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get("https://...", params=params)
        return response.json()
```

**Step 4: Database Operations**

Convert to async MongoDB operations via Motor:
```python
# BEFORE
collection = db["gtm_plans"]
result = collection.insert_one(document)

# AFTER
db = await get_db()
collection = db["gtm_plans"]
result = await collection.insert_one(document)
```

---

## Phase 5: GTM Routes Refactoring

### File: `app/api/routes/gtm_routes.py`

#### Pattern Template
```python
@router.post("/api/gtm-plan")
@token_required
@service_check("304")  # GTM service ID
async def create_gtm_plan(
    user_id: str,
    request: Request,
    data: GTMCreateSchema,
) -> Dict[str, Any]:
    """
    Generate GTM plan using Flask decorator pattern.
    
    Maps to Flask: server2/blueprints/gtm_bp.py::gtm_endpoint
    """
    if not check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    increment_user_requests(user_id)
    
    try:
        # Extract inputs
        business_name = data.businessName
        # ... more extraction
        
        # Call pure service functions
        result = await generate_plan(
            business_name=business_name,
            user_id=user_id,
            # ... all parameters
        )
        
        # Save to database
        plan_id = await save_gtm_plan(user_id, result)
        
        return {"plan": result, "planId": plan_id}
        
    except Exception as exc:
        logger.error(f"GTM generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        decrement_user_requests(user_id)
```

#### Routes to Implement
1. POST /api/gtm-plan - Generate GTM plan (service 304)
2. POST /api/gtm-plan/pdf - Generate PDF report
3. GET /api/gtm-plan/{plan_id} - Retrieve plan
4. GET /api/user-gtm-plans - List user's plans
5. DELETE /api/delete-gtm/{plan_id} - Delete plan

#### Service ID
Check Flask blueprint for GTM service ID (likely 304 based on SWOT pattern)

---

## Phase 6-7: Business Service (Similar Pattern)

### File: `app/services/business_service.py`

Follow the SAME pattern as GTM:
1. Identify all methods (sync vs async)
2. Convert to module-level functions
3. Create factory functions for clients
4. Make all async where possible

### Service ID
Need to determine from Flask implementation

---

## Phase 8-9: Pitch Service (Similar Pattern)  

### File: `app/services/pitch_service.py`

Same approach:
1. Convert class methods to functions
2. Make async
3. Handle database with Motor
4. Create routes with decorators

### Service ID
Need to determine from Flask implementation

---

## Phase 10: Integration & Testing

### Unit Tests

**Test Authentication Decorators:**
```python
@pytest.mark.asyncio
async def test_token_required_valid_token(mock_db):
    @token_required
    async def dummy_handler(user_id: str, request: Request):
        return {"user_id": user_id}
    
    # Create mock request with valid token
    mock_request = create_mock_request_with_token("valid_token")
    result = await dummy_handler(request=mock_request)
    assert result["user_id"] == "test_user"

@pytest.mark.asyncio
async def test_service_check_valid_access(mock_db):
    # Test with valid subscription and service access
    pass

@pytest.mark.asyncio
async def test_service_check_expired_subscription(mock_db):
    # Test with expired subscription
    pass

@pytest.mark.asyncio
async def test_rate_limit_enforcement():
    # Test rate limit blocking after N requests
    pass
```

**Test Service Functions:**
```python
@pytest.mark.asyncio
async def test_generate_swot_analysis(mock_ai_client):
    result = await generate_swot_analysis(
        business_name="Test Co",
        industry="Tech",
        # ...
    )
    assert "strengths" in result
    assert "weaknesses" in result
    # ...

@pytest.mark.asyncio
async def test_generate_swot_database_save(mock_db):
    plan_id = await save_swot_plan(
        user_id="user123",
        business_name="Test",
        # ...
    )
    assert plan_id is not None
    # Verify saved to DB
```

### Integration Tests

**Test Complete Flow:**
```python
@pytest.mark.asyncio
async def test_swot_generation_full_flow(async_client, mock_db, mock_ai):
    # 1. Generate valid JWT token
    token = create_valid_jwt_token("user123")
    
    # 2. Make POST request with token
    response = await async_client.post(
        "/api/swot",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "businessName": "Test Co",
            "industry": "Tech",
            # ...
        }
    )
    
    # 3. Verify response structure
    assert response.status_code == 200
    assert "swot" in response.json()
    assert "requestId" in response.json()
    
    # 4. Verify database saved
    db = await get_db()
    plan = await db["swot_plans"].find_one({"user_id": "user123"})
    assert plan is not None

@pytest.mark.asyncio
async def test_rate_limit_returns_429(async_client, mock_db):
    # Make 6 concurrent requests (limit is 5)
    # Verify 6th returns 429
    pass

@pytest.mark.asyncio
async def test_unauthorized_without_token(async_client):
    response = await async_client.post(
        "/api/swot",
        json={"businessName": "...", ...}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_forbidden_without_service_access(async_client, mock_db):
    # User without service 309 access
    # Should return 403
    pass
```

### Load Testing

```python
import asyncio
from locust import HttpUser, task, between

class SwotLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.token = get_valid_jwt_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(1)
    def generate_swot(self):
        self.client.post(
            "/api/swot",
            headers=self.headers,
            json={
                "businessName": f"Company {random()}",
                "industry": "Tech",
                # ...
            }
        )
    
    @task(1)
    def list_plans(self):
        self.client.get(
            "/api/user-swot-plans",
            headers=self.headers,
        )

# Run with: locust -f tests/load/test_load.py --host=http://localhost:8000
```

---

## File Modification Checklist

### Create/Modify Files
- [ ] app/core/auth.py - ✅ DONE
- [ ] app/services/swot_service.py - ✅ DONE
- [ ] app/api/routes/swot_routes.py - ✅ DONE
- [ ] app/services/gtm_service.py - Convert to pure functions
- [ ] app/api/routes/gtm_routes.py - Implement with decorators
- [ ] app/services/business_service.py - Convert to pure functions
- [ ] app/api/routes/business_routes.py - Implement with decorators
- [ ] app/services/pitch_service.py - Convert to pure functions
- [ ] app/api/routes/pitch_routes.py - Implement with decorators
- [ ] tests/unit/test_auth.py - Unit tests
- [ ] tests/integration/test_routes.py - Integration tests
- [ ] tests/load/test_load.py - Load tests

### Backup Files
- [x] app/services/swot_service_old.py
- [x] app/api/routes/swot_routes_old.py
- [ ] app/services/gtm_service_old.py
- [ ] app/api/routes/gtm_routes_old.py
- [ ] app/services/business_service_old.py
- [ ] app/api/routes/business_routes_old.py
- [ ] app/services/pitch_service_old.py
- [ ] app/api/routes/pitch_routes_old.py

---

## Implementation Order

### Priority 1 (Critical - Completes patterns)
1. Refactor GTM service → pure functions
2. Refactor GTM routes → decorators
3. Verify SWOT + GTM work end-to-end

### Priority 2 (Important - Complete suite)
4. Refactor Business service
5. Refactor Business routes
6. Refactor Pitch service
7. Refactor Pitch routes

### Priority 3 (Quality - Validation)
8. Write unit tests
9. Write integration tests
10. Run load tests
11. Documentation updates

---

## Flask Blueprint References

### Service IDs (From Flask)
Look up in `server2/blueprints/` for correct service IDs:
```python
# swot_plan.py
309 - SWOT Analysis
310 - Competitor Analysis
311 - Value Proposition
312 - Risk Analysis
313 - Market Segmentation

# gtm_bp.py
??? - GTM Plan (Find this)

# business_bp.py
??? - Business Plan (Find this)

# pitch_analysis_bp.py
??? - Pitch Analysis (Find this)
```

### Function Mapping

To refactor each service:
1. Find Flask blueprint: `server2/blueprints/{name}_bp.py`
2. Identify pure functions vs. routes
3. Copy function logic (signatures + bodies)
4. Convert to async where needed
5. Implement routes with @token_required + @service_check

---

## Validation Checklist

### Before Deployment
- [ ] All Python files compile without syntax errors
- [ ] All imports resolve correctly
- [ ] Type hints are consistent
- [ ] Logging statements included throughout
- [ ] Error messages are user-friendly
- [ ] Rate limiting works correctly
- [ ] Database operations are async
- [ ] Decorators chain properly
- [ ] JWT validation works
- [ ] Service access control enforced

### After Testing
- [ ] Unit tests pass (100% coverage of decorators)
- [ ] Integration tests pass (full request-response cycles)
- [ ] Load tests show rate limiting works
- [ ] No memory leaks in long-running tests
- [ ] Error handling works for edge cases

### Before Production
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Deployment guide updated
- [ ] Azure environment variables verified
- [ ] MongoDB connection tested
- [ ] Redis connection tested (if used)
- [ ] Monitoring/logging configured
- [ ] Backup of old implementation retained

---

## Estimated Timeline

### If 1 Developer (Full-Time)
- Phase 4-5: GTM refactoring: 4 hours
- Phase 6-7: Business refactoring: 3 hours
- Phase 8-9: Pitch refactoring: 3 hours
- Testing: 4 hours
- Documentation: 2 hours
- **Total: 16 hours (2 business days)**

### If 2 Developers (Parallel)
- Phases 4-5 + 6-7 in parallel: 4 hours
- Phase 8-9: 3 hours
- Testing: 4 hours
- Documentation: 2 hours
- **Total: 13 hours (1.5 business days)**

---

## Success Criteria

✅ Refactoring is complete when:
1. All services use pure function pattern
2. All routes use Flask-style decorators
3. 80%+ code coverage with tests
4. Load test handles 50+ concurrent requests
5. Rate limiting enforces limits correctly
6. All error cases handled gracefully
7. Documentation matches implementation
8. Azure integration verified
9. Database operations async throughout
10. No breaking changes to existing APIs

---

## Questions to Resolve

Before starting Phase 4:
1. What is the GTM service ID? (Need to check Flask gtm_bp.py)
2. What is the Business service ID?
3. What is the Pitch Analysis service ID?
4. Should reportlab PDF generation remain sync or become async?
5. Are there any Celery tasks that need async conversion?
6. Should we keep backward compatibility with old endpoints?

---

## Notes for Implementation

- Always provide 3+ lines of context in oldString for replace operations
- Use `async def` for all I/O operations
- Prefer `httpx.AsyncClient` over `requests`
- Use Motor for all MongoDB operations
- Thread-safe operations only need `threading.Lock`, not asyncio.Lock
- Multiple decorators stack: @token_required over @service_check over route
- Pass Request object in kwargs from @token_required
- Request object becomes available after HTTPException is raised
- Keep error messages consistent across all routes
- Use logging.debug for details, logging.info for important events, logging.error for exceptions

