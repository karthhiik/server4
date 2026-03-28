# Environment Variables Audit Report
**Server1_FastApi Application**
**Date:** March 23, 2026

---

## Executive Summary
**Overall Status:** ⚠️ **MULTIPLE ISSUES FOUND**

The application has **INCONSISTENT** environment variable usage patterns across services and routes. While most configurations use the `settings` object properly, there are several critical issues:

1. **Hardcoded Placeholder API Keys** in gtm_service.py
2. **Inconsistent Configuration Pattern** with mixed os.getenv() and settings
3. **Variable Naming Inconsistencies** in SWOT configuration (AZURE_ENDPOINT_swot vs standard naming)
4. **Missing Configuration** for some optional APIs (ALPHA_VANTAGE)

---

## Detailed Audit by Service

### 1. ✅ GTM Service (`gtm_service.py`) & GTM Routes (`gtm_routes.py`)

**Status:** ⚠️ **PARTIALLY CORRECT WITH SECURITY ISSUES**

#### Environment Variables Configuration:
| Variable | Current Usage | Status | Issue |
|----------|---|--------|--------|
| `AZURE_ENDPOINT_GTM` | `ai_factory.get_client("gtm")` | ✅ Correct | Uses settings via factory |
| `AZURE_APIVERSION_GTM` | ai_factory | ✅ Correct | Centralized in ai.py |
| `AZURE_DEPLOYMENT_GTM` | ai_factory | ✅ Correct | Proper config pattern |
| `AZURE_SUBSCRIPTION_GTM` | ai_factory | ✅ Correct | Secure via settings |
| `SERPAPI_API_KEY` | `settings.SERPAPI_API_KEY` | ✅ Correct | Proper usage |
| `NEWS_API_KEY` | `os.getenv("NEWS_API_KEY", "bb0b82f1d8a74c529fca68561f990d08")` | ❌ **HARDCODED** | **Found placeholder key!** |
| `FRED_API_KEY` | `os.getenv("FRED_API_KEY", "3e7e485e7705143f49393fbeba964862")` | ❌ **HARDCODED** | **Found placeholder key!** |

#### Issues Found:

**CRITICAL - Hardcoded API Keys:**
```python
# Line 48-52 in gtm_service.py
self.news_api_key = os.getenv(
    "NEWS_API_KEY", "bb0b82f1d8a74c529fca68561f990d08"  # ❌ HARDCODED
)
self.fred_api_key = os.getenv(
    "FRED_API_KEY", "3e7e485e7705143f49393fbeba964862"  # ❌ HARDCODED
)
```

**Pattern Issues:**
- Uses `os.getenv()` directly instead of settings object
- Has placeholder API keys as defaults (these look like test keys)
- Compares against hardcoded values at runtime (lines 457, 535)

#### Recommendation:
1. **IMMEDIATE:** Move NEWS_API_KEY and FRED_API_KEY to settings.py with proper Field definitions
2. Remove hardcoded placeholder values
3. Standardize to use settings object consistently

---

### 2. ⚠️ Business Service (`business_service.py`) & Business Routes (`business_routes.py`)

**Status:** ⚠️ **MIXED PATTERNS - INCONSISTENT**

#### Environment Variables Configuration:
| Variable | Current Usage | Status | Issue |
|----------|---|--------|--------|
| `ALPHA_VANTAGE_API_KEY` | `os.getenv("ALPHA_VANTAGE_API_KEY", "")` | ❌ Inconsistent | Should use settings |
| `FRED_API_KEY` | `settings.FRED_API_KEY` | ✅ Correct | Proper config pattern |
| `NEWS_API_KEY` | `settings.NEWS_API_KEY` | ✅ Correct | Proper config pattern |
| `SERPAPI_API_KEY` | `settings.SERPAPI_API_KEY` | ✅ Correct | Proper config pattern |
| `AZURE_OPENAI_*` | `ai_factory.get_client("general")` | ✅ Correct | Uses factory pattern |

#### Issues Found:

**Inconsistent Pattern - Line 62:**
```python
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FRED_API_KEY = settings.FRED_API_KEY  # ✅ Consistent
NEWS_API_KEY = settings.NEWS_API_KEY  # ✅ Consistent
SERPAPI_API_KEY = settings.SERPAPI_API_KEY  # ✅ Consistent
```

**Usage Pattern - Two Different Approaches:**
- Some APIs use `os.getenv()` (ALPHA_VANTAGE)
- Others use `settings` object (FRED, NEWS, SERPAPI)
- Consistency issue with module-level variables

#### Recommendation:
1. **Replace** `os.getenv("ALPHA_VANTAGE_API_KEY", "")` with `settings.ALPHA_VANTAGE_API_KEY`
2. Add ALPHA_VANTAGE_API_KEY to config.py settings
3. Standardize all API key access to use settings object

---

### 3. ⚠️ SWOT Service (`swot_service.py`) & SWOT Routes (`swot_routes.py`)

**Status:** ⚠️ **CONFIGURATION NAMING INCONSISTENCIES**

#### Environment Variables Configuration:
| Variable | Current Usage | Status | Issue |
|----------|---|--------|--------|
| `AZURE_ENDPOINT_swot` | Direct in __init__ | ⚠️ Non-standard | Should use ai_factory |
| `AZURE_ENDPOINT_subscription` | Direct in __init__ | ❌ Wrong name | Incorrectly naming pattern |
| `AZURE_ENDPOINT_deployment` | Direct in __init__ | ⚠️ Non-standard | Naming inconsistency |
| `AZURE_ENDPOINT_apiversion` | Direct in __init__ | ⚠️ Non-standard | Naming inconsistency |
| `SERPAPI_API_KEY` | `settings.SERPAPI_API_KEY` | ✅ Correct | Proper usage |

#### Issues Found:

**Variable Naming Inconsistency - Lines 301-307:**
```python
self.client = AsyncAzureOpenAI(
    azure_endpoint=settings.AZURE_ENDPOINT_swot or settings.AZURE_OPENAI_ENDPOINT,  # ❌ Non-standard
    api_key=settings.AZURE_ENDPOINT_subscription or settings.AZURE_OPENAI_SUBSCRIPTION_KEY,  # ❌ Wrong name
    api_version=settings.AZURE_ENDPOINT_apiversion or settings.AZURE_OPENAI_API_VERSION,  # ⚠️ Non-standard
)
self.deployment = settings.AZURE_ENDPOINT_deployment or settings.AZURE_OPENAI_DEPLOYMENT  # ❌ Wrong name
```

**Problems:**
1. Variable names don't follow pattern (swot uses `AZURE_ENDPOINT_*` instead of standard `AZURE_ENDPOINT_SWOT` etc.)
2. `AZURE_ENDPOINT_subscription` is a wrong name for api_key (should be `AZURE_ENDPOINT_SWOT_KEY` or similar)
3. Should use `ai_factory.get_client("swot")` like GTM and Pitch services (but factory doesn't support "swot" yet)

**In .env file:**
```env
AZURE_ENDPOINT_swot="https://info-m98rto5s-eastus2.openai.azure.com/"  # lowercase; inconsistent
AZURE_ENDPOINT_model="gpt-4.1-mini"  # Wrong variable name
AZURE_ENDPOINT_deployment="1-mini-2025-04-14-BusinessModel1"  # Too generic
AZURE_ENDPOINT_subscription="FQ17oRl6RxHtHTsVdIyBV8eYLhYskTMVtbxQ0N8kjnoPdsqtiClUJQQJ99BDACHYHv6XJ3w3AAAAACOGKATS"  # Wrong semantic
AZURE_ENDPOINT_apiversion="2024-12-01-preview"  # Non-standard naming
```

#### Recommendation:
1. **Rename** variables in .env to follow pattern:
   - `AZURE_ENDPOINT_SWOT` (not `AZURE_ENDPOINT_swot`)
   - `AZURE_SUBSCRIPTION_SWOT` (not `AZURE_ENDPOINT_subscription`)
   - `AZURE_DEPLOYMENT_SWOT` (not `AZURE_ENDPOINT_deployment`)
   - `AZURE_APIVERSION_SWOT` (not `AZURE_ENDPOINT_apiversion`)

2. **Add to config.py:**
   ```python
   AZURE_ENDPOINT_SWOT: str = Field(default="", validation_alias="AZURE_ENDPOINT_SWOT")
   AZURE_SUBSCRIPTION_SWOT: str = Field(default="", validation_alias="AZURE_SUBSCRIPTION_SWOT")
   AZURE_DEPLOYMENT_SWOT: str = Field(default="", validation_alias="AZURE_DEPLOYMENT_SWOT")
   AZURE_APIVERSION_SWOT: str = Field(default="", validation_alias="AZURE_APIVERSION_SWOT")
   ```

3. **Extend ai_factory** to support "swot" service type or have SWOT use the factory pattern

---

### 4. ✅ Payment Routes (`payment_routes.py`)

**Status:** ✅ **CORRECT USAGE**

#### Environment Variables Configuration:
| Variable | Current Usage | Status |
|----------|---|--------|
| `PHONEPE_CLIENT_ID` | `settings.PHONEPE_CLIENT_ID` | ✅ Correct |
| `PHONEPE_CLIENT_SECRET` | `settings.PHONEPE_CLIENT_SECRET` | ✅ Correct |
| `PHONEPE_MERCHANT_ID` | `settings.PHONEPE_MERCHANT_ID` | ✅ Correct |
| `PHONEPE_SALT_KEY` | `settings.PHONEPE_SALT_KEY` | ✅ Correct |
| `PHONEPE_SALT_INDEX` | `settings.PHONEPE_SALT_INDEX` | ✅ Correct |
| `PHONEPE_ENV` | `settings.PHONEPE_ENV` | ✅ Correct |
| `PHONEPE_REDIRECT_URL` | `settings.PHONEPE_REDIRECT_URL` | ✅ Correct |
| `STRIPE_API_KEY` | `settings.STRIPE_API_KEY` | ✅ Correct |
| `STRIPE_WEBHOOK_SECRET` | `settings.STRIPE_WEBHOOK_SECRET` | ✅ Correct |
| `MERCHANT_USERNAME` | `settings.MERCHANT_USERNAME` | ✅ Correct |
| `MERCHANT_PASSWORD` | `settings.MERCHANT_PASSWORD` | ✅ Correct |

**Proper Pattern Used - Lines 38-53:**
```python
PHONEPE_MERCHANT_ID = settings.PHONEPE_MERCHANT_ID
PHONEPE_SALT_KEY = settings.PHONEPE_SALT_KEY
stripe.api_key = settings.STRIPE_API_KEY

# Safe initialization with checks
if settings.PHONEPE_CLIENT_ID and settings.PHONEPE_CLIENT_SECRET:
    phonepe_client = StandardCheckoutClient.get_instance(
        client_id=settings.PHONEPE_CLIENT_ID,
        client_secret=settings.PHONEPE_CLIENT_SECRET,
        ...
    )
```

✅ **All credentials properly sourced from settings**

---

### 5. ✅ Pitch Service (`pitch_service.py`) & Pitch Routes (`pitch_analysis_routes.py`)

**Status:** ✅ **CORRECT USAGE**

#### Environment Variables Configuration:
| Variable | Current Usage | Status |
|----------|---|--------|
| `AZURE_ENDPOINT_PITCH` | `ai_factory.get_client("pitch")` | ✅ Correct |
| `AZURE_MODELNAME_PITCH` | ai_factory | ✅ Correct |
| `AZURE_DEPLOYMENT_PITCH` | ai_factory | ✅ Correct |
| `AZURE_SUBSCRIPTION_PITCH` | ai_factory | ✅ Correct |
| `AZURE_APIVERSION_PITCH` | ai_factory | ✅ Correct |
| Redis config | `settings.get_redis_url` | ✅ Correct |

**Proper Factory Pattern - Line 191:**
```python
self.ai_client = ai_factory.get_client("pitch")  # ✅ Centralized configuration
```

✅ **All Azure credentials properly managed through ai_factory**

---

### 6. ✅ Avatar Routes (`avatar_routes.py`)

**Status:** ✅ **NO CREDENTIALS USED**

Avatar routes do not use external API credentials. They only use:
- `settings.UPLOAD_FOLDER` for avatar storage ✅
- File path validation and image processing

**No security issues found.**

---

### 7. ✅ Cold Mail Routes (`cold_mail_routes.py`)

**Status:** ✅ **CORRECT SMTP USAGE**

#### Environment Variables Configuration:
| Variable | Current Usage | Status |
|----------|---|--------|
| `MAIL_USERNAME` | `settings.MAIL_USERNAME` | ✅ Correct |
| `MAIL_PASSWORD` | `settings.MAIL_PASSWORD` | ✅ Correct |
| `MAIL_SERVER` | `settings.MAIL_SERVER` | ✅ Correct |
| `MAIL_PORT` | `settings.MAIL_PORT` | ✅ Correct |
| `MAIL_USE_TLS` | `settings.MAIL_USE_TLS` | ✅ Correct |
| `MAIL_USE_SSL` | `settings.MAIL_USE_SSL` | ✅ Correct |
| `MAIL_DEFAULT_SENDER` | `settings.MAIL_DEFAULT_SENDER` | ✅ Correct |
| `MONGODB_URI` | `settings.MONGODB_URI` | ✅ Correct |
| `MONGODB_DB_NAME` | `settings.MONGODB_DB_NAME` | ✅ Correct |

**Proper SMTP Configuration - Lines 605-649:**
```python
def _validate_mail_runtime_config() -> str | None:
    username = str(settings.MAIL_USERNAME or "").strip()  # ✅ From settings
    password = str(settings.MAIL_PASSWORD or "").strip()  # ✅ From settings
    
    if not username or not password:
        return "SMTP credentials are not configured on the server."

def _send_email_worker(log_id, payload: Dict[str, Any]):
    server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)  # ✅ Secure usage
```

✅ **All SMTP credentials properly secured through settings**

---

## Summary Table

| Component | Correct | Issues | Severity |
|-----------|---------|--------|----------|
| GTM Service | 60% | Hardcoded API keys | 🔴 HIGH |
| Business Service | 75% | Inconsistent patterns | 🟡 MEDIUM |
| SWOT Service | 50% | Naming inconsistencies | 🟡 MEDIUM |
| Payment Routes | 100% | None | ✅ NONE |
| Pitch Service | 100% | None | ✅ NONE |
| Avatar Routes | 100% | None | ✅ NONE |
| Cold Mail Routes | 100% | None | ✅ NONE |

---

## Recommended Priority Fixes

### 🔴 **CRITICAL - Fix First:**

1. **GTM Service - Remove Hardcoded Keys**
   - File: `Server1_FastApi/app/services/gtm_service.py` (lines 48-52)
   - Move NEWS_API_KEY and FRED_API_KEY to settings.py
   - Remove placeholder defaults

### 🟡 **HIGH - Fix Second:**

2. **SWOT Service - Fix Variable Naming**
   - File: `Server1_FastApi/app/core/config.py`
   - Add proper AZURE_ENDPOINT_SWOT, AZURE_SUBSCRIPTION_SWOT variables
   - Update .env file variable names
   - Update swot_service.py to use corrected variable names

3. **Business Service - Standardize Patterns**
   - File: `Server1_FastApi/app/services/business_service.py` (line 62)
   - Add ALPHA_VANTAGE_API_KEY to config.py
   - Replace os.getenv() with settings

---

## Configuration Best Practices Checklist

| Practice | Implementation | Status |
|----------|---|--------|
| Use BaseSettings from pydantic_settings | ✅ Implemented in config.py | ✅ |
| Load from .env file | ✅ `.env` file exists | ✅ |
| No hardcoded secrets in code | ⚠️ Found hardcoded values | ❌ |
| Consistent field naming | ⚠️ Naming inconsistencies | ❌ |
| Centralized access via config object | ⚠️ Mixed os.getenv and settings | ❌ |
| Use factory pattern for clients | ✅ ai_factory implemented | ✅ |
| Local defaults for optional configs | ✅ Proper defaults in settings | ✅ |
| Validation of secret presence | ⚠️ Some APIs have placeholder defaults | ❌ |

---

## Action Items

- [ ] **CRITICAL:** Remove hardcoded API keys from gtm_service.py
- [ ] **HIGH:** Reorganize SWOT configuration variables (config.py + .env)
- [ ] **HIGH:** Move ALPHA_VANTAGE_API_KEY to standardized access pattern
- [ ] **MEDIUM:** Add validation to warn/fail when API keys are placeholder values
- [ ] **MEDIUM:** Extend ai_factory to support "swot" service type for consistency
- [ ] **LOW:** Document configuration requirements for new developers

---

## Verification Commands

```bash
# Check for hardcoded values in codebase
grep -r "bb0b82f1d8a74c529fca68561f990d08\|3e7e485e7705143f49393fbeba964862" Server1_FastApi/

# Verify all settings are properly defined
grep -r "os\.getenv" Server1_FastApi/app/services/
grep -r "os\.getenv" Server1_FastApi/app/api/routes/

# Check .env variables are referenced in config.py
grep -F ".env" Server1_FastApi/app/core/config.py
```

---

**Report Generated:** March 23, 2026
**Audit Scope:** Medium Thoroughness - Credential Usage Patterns
**Reviewer Recommendation:** Address critical issues before production deployment
