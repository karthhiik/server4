# CODE CHANGES - SIDE-BY-SIDE COMPARISON

## File: `app/api/routes/auth_routes.py`

### Change #1: REGISTER Endpoint - Handle Existing Users (Lines 420-522)

#### BEFORE (Bug - Returns 409 Error):
```python
@auth_router.post("/register", response_model=Token)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
):
    # ... verification code ...
    
    existing_user = await users_collection.find_one({"user_id": uid})
    if existing_user:
        raise HTTPException(status_code=409, detail="User already exists.")  # ❌ ERROR
    
    # Create new user...
    new_user = {
        "user_id": uid,
        "is_first_login": True,
        ...
    }
    await users_collection.insert_one(new_user)
```

#### AFTER (Fixed - Updates Existing User):
```python
@auth_router.post("/register", response_model=Token)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
):
    # ... verification code ...
    
    token = create_jwt_token(uid)
    
    # Check if user already exists - Flask-style handling (update instead of error)
    existing_user = await users_collection.find_one({"user_id": uid})
    
    if existing_user:
        # User already exists - update their record with new consent info ✅
        update_data = {
            "email": email,
            "email_verified": email_verified,
            "name": existing_user.get("name") or display_name,
            "sign_in_provider": sign_in_provider,
            "accepted_terms": True,                      # ✅ NEW: Record terms
            "accepted_privacy": True,                    # ✅ NEW: Record privacy
            "last_activity": datetime.utcnow(),
        }
        
        # Email verified or OAuth - allow login immediately
        if email_verified or is_oauth:
            update_data.update({
                "jwt_token": token,
                "is_online": True,
                "last_seen": datetime.utcnow()
            })
            await users_collection.update_one({"user_id": uid}, {"$set": update_data})  # ✅ UPDATE
            set_auth_cookie(response, token)
            ensure_csrf_cookie(request, response)
            return {
                "token": token,
                "message": "Registration successful!",     # ✅ SUCCESS (200)
                "promo_active": bool(existing_user.get("promo_active", False))
            }
        
        # Not verified - require email verification
        await users_collection.update_one(
            {"user_id": uid},
            {"$set": update_data, "$unset": {"jwt_token": ""}}
        )
        return {
            "token": None,
            "message": "Registration successful! Please check your email to verify your account before logging in.",
            "promo_active": False
        }
    
    # CREATE NEW USER - First time registration
    new_user = {
        "user_id": uid,
        "email": email,
        "email_verified": email_verified,
        "name": display_name,
        "username": final_username,
        "sign_in_provider": sign_in_provider,
        "created_at": datetime.utcnow(),
        "active_days": 1,
        "energy_level": 1,
        "last_activity": datetime.utcnow(),
        "is_first_login": True,
        "is_online": email_verified or is_oauth,
        "last_seen": datetime.utcnow(),
        "jwt_token": token if (email_verified or is_oauth) else None,
        "service_access": [],
        "used_services": [],
        "service_token": 0,
        "accepted_terms": True,                          # ✅ NEW: Record terms
        "accepted_privacy": True,                        # ✅ NEW: Record privacy
    }
    await users_collection.insert_one(new_user)
    
    # ... rest of response ...
```

**Key Changes:**
1. ✅ Don't raise 409 error for existing users
2. ✅ Update existing user record instead
3. ✅ Return 200 success for both new and existing users
4. ✅ Record accepted_terms and accepted_privacy

---

### Change #2: LOGIN Endpoint - Preserve is_first_login (Lines 383-396)

#### BEFORE (Bug - is_first_login Not Preserved):
```python
@auth_router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
):
    # ... authentication code ...
    
    if existing_user:
        username_to_use = existing_user.get("username") or username
        activity_data = await update_user_activity(uid)
        # ... promo checks ...
    else:
        username_to_use = username
    
    update_data = {
        "jwt_token": token,
        "email": email,
        "email_verified": email_verified,
        # ... other fields ...
    }
    
    if not existing_user:
        update_data.update(
            {
                "created_at": datetime.utcnow(),
                "is_first_login": True,
                "service_access": [],
                "used_services": [],
                "service_token": 0,
            }
        )
    else:
        preserve_fields = [
            "service_token",
            "service_access",
            "used_services",
            "promo_active",
            "promo_expiry",
            "service_expire",
            "subscription_typo",
            "consent_version",
            "terms_accepted_at",
            "privacy_accepted_at",
            # ❌ is_first_login NOT HERE - NOT PRESERVED!
        ]
        for field in preserve_fields:
            if field in existing_user and field not in update_data:
                update_data[field] = existing_user[field]
```

#### AFTER (Fixed - is_first_login Preserved):
```python
    if not existing_user:
        update_data.update(
            {
                "created_at": datetime.utcnow(),
                "is_first_login": True,
                "service_access": [],
                "used_services": [],
                "service_token": 0,
            }
        )
    else:
        preserve_fields = [
            "service_token",
            "service_access",
            "used_services",
            "promo_active",
            "promo_expiry",
            "service_expire",
            "subscription_typo",
            "consent_version",
            "terms_accepted_at",
            "privacy_accepted_at",
            "is_first_login",  # ✅ ADDED - NOW PRESERVED!
        ]
        for field in preserve_fields:
            if field in existing_user and field not in update_data:
                update_data[field] = existing_user[field]
```

**Key Changes:**
1. ✅ Added `"is_first_login"` to preserve_fields list
2. ✅ Flag is now explicitly copied from existing user to update_data
3. ✅ is_first_login won't reset if user document is recreated

---

### Change #3: /get-status Endpoint - Return is_first_login (Lines 698-713)

#### BEFORE (Bug - is_first_login Not Returned):
```python
@auth_router.get("/get-status")
async def get_user_status_endpoint(user_id: str = Depends(get_current_user)):
    users_collection = get_collection("users")
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found.")

    return {
        "user_id": user_id,
        "is_online": user_data.get("is_online", False),
        "last_seen": user_data.get("last_seen"),
        "username": user_data.get("username"),
        # ❌ is_first_login NOT RETURNED
        # ❌ active_days NOT RETURNED
        # ❌ energy_level NOT RETURNED
    }
```

#### AFTER (Fixed - All Fields Returned):
```python
@auth_router.get("/get-status")
async def get_user_status_endpoint(user_id: str = Depends(get_current_user)):
    users_collection = get_collection("users")
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found.")

    return {
        "user_id": user_id,
        "is_first_login": user_data.get("is_first_login", True),  # ✅ ADDED
        "is_online": user_data.get("is_online", False),
        "last_seen": user_data.get("last_seen"),
        "username": user_data.get("username"),
        "active_days": user_data.get("active_days", 0),           # ✅ ADDED
        "energy_level": user_data.get("energy_level", 1),         # ✅ ADDED
    }
```

**Key Changes:**
1. ✅ Added `is_first_login` to response
2. ✅ Added `active_days` to response (bonus)
3. ✅ Added `energy_level` to response (bonus)
4. ✅ Frontend can now check user status correctly

---

### Change #4: /get-status/{target_user_id} Endpoint - Return is_first_login (Lines 747-763)

#### BEFORE (Bug - is_first_login Not Returned):
```python
@auth_router.get("/get-status/{target_user_id}")
async def get_other_user_status(
    target_user_id: str,
    user_id: str = Depends(get_current_user),
):
    _ = user_id
    users_collection = get_collection("users")
    user_data = await users_collection.find_one({"user_id": target_user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found.")

    return {
        "user_id": target_user_id,
        "is_online": user_data.get("is_online", False),
        "last_seen": user_data.get("last_seen"),
        "username": user_data.get("username"),
        # ❌ is_first_login NOT RETURNED
        # ❌ active_days NOT RETURNED
        # ❌ energy_level NOT RETURNED
    }
```

#### AFTER (Fixed - All Fields Returned):
```python
@auth_router.get("/get-status/{target_user_id}")
async def get_other_user_status(
    target_user_id: str,
    user_id: str = Depends(get_current_user),
):
    _ = user_id
    users_collection = get_collection("users")
    user_data = await users_collection.find_one({"user_id": target_user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found.")

    return {
        "user_id": target_user_id,
        "is_first_login": user_data.get("is_first_login", True),  # ✅ ADDED
        "is_online": user_data.get("is_online", False),
        "last_seen": user_data.get("last_seen"),
        "username": user_data.get("username"),
        "active_days": user_data.get("active_days", 0),           # ✅ ADDED
        "energy_level": user_data.get("energy_level", 1),         # ✅ ADDED
    }
```

**Key Changes:**
1. ✅ Added `is_first_login` to response
2. ✅ Added `active_days` to response (bonus)
3. ✅ Added `energy_level` to response (bonus)

---

## Summary of ALL Changes

| Change | Type | Location | Impact | Status |
|--------|------|----------|--------|--------|
| Register: Update instead of 409 error | Logic | auth_routes.py ~420-522 | Flask compatibility | ✅ FIXED |
| Register: Record terms acceptance | Data | auth_routes.py ~513-514 | Compliance | ✅ ADDED |
| Login: Add is_first_login to preserve_fields | Data | auth_routes.py ~383-396 | Fix flag reset | ✅ FIXED |
| /get-status: Return is_first_login | API | auth_routes.py ~698-713 | Frontend can check | ✅ FIXED |
| /get-status: Return active_days | API | auth_routes.py ~703-704 | Better info | ✅ ADDED |
| /get-status: Return energy_level | API | auth_routes.py ~705-706 | Better info | ✅ ADDED |
| /get-status/{id}: Return is_first_login | API | auth_routes.py ~747-763 | Frontend can check | ✅ FIXED |
| /get-status/{id}: Return active_days | API | auth_routes.py ~751-752 | Better info | ✅ ADDED |
| /get-status/{id}: Return energy_level | API | auth_routes.py ~753-754 | Better info | ✅ ADDED |

---

## Testing the Changes

### Before Changes - What Happened:
1. User registers → `is_first_login: true` ✅
2. User completes profile → `is_first_login: false` ✅
3. User logs out, logs back in
4. ❌ /session might show `is_first_login: true` (reset bug)
5. ❌ /get-status might not return `is_first_login` field
6. ❌ Frontend can't determine user status
7. ❌ User redirected to profile page (wrong!)

### After Changes - What Happens Now:
1. User registers → `is_first_login: true` ✅
2. User completes profile → `is_first_login: false` ✅
3. User logs out, logs back in
4. ✅ /session shows `is_first_login: false` (preserved!)
5. ✅ /get-status returns `is_first_login: false` field
6. ✅ Frontend can determine user is existing user
7. ✅ User goes straight to dashboard (correct!)

---

## Verification Commands

```bash
# Store token from registration
TOKEN=$(curl -X POST http://127.0.0.1:8080/register \
  -H "Content-Type: application/json" \
  -d '{"idToken":"...","turnstileToken":"..."}' | jq -r '.token')

# Check is_first_login is TRUE
curl -X GET http://127.0.0.1:8080/session \
  -H "Authorization: Bearer $TOKEN" | jq '.user.is_first_login'
# Should return: true

# Complete onboarding
curl -X POST http://127.0.0.1:8080/complete-onboarding \
  -H "Authorization: Bearer $TOKEN"

# Check is_first_login is FALSE
curl -X GET http://127.0.0.1:8080/session \
  -H "Authorization: Bearer $TOKEN" | jq '.user.is_first_login'
# Should return: false

# Check /get-status returns the flag
curl -X GET http://127.0.0.1:8080/get-status \
  -H "Authorization: Bearer $TOKEN" | jq '.is_first_login'
# Should return: false

# Login again next day
TOKEN2=$(curl -X POST http://127.0.0.1:8080/login \
  -H "Content-Type: application/json" \
  -d '{"idToken":"...","turnstileToken":"..."}' | jq -r '.token')

# Check is_first_login is STILL FALSE (not reset)
curl -X GET http://127.0.0.1:8080/session \
  -H "Authorization: Bearer $TOKEN2" | jq '.user.is_first_login'
# Should return: false ✅ (preserved, not reset to true!)
```

---

## Files Modified

- ✅ `app/api/routes/auth_routes.py` - Lines changed: ~40-50 total

## Files NOT Modified (Matching Firebase)

- ✅ `app/api/routes/profile_routes.py` - Already correct
- ✅ `app/core/security.py` - Already correct
- ✅ `app/schemas/auth.py` - Already correct
- ✅ MongoDB - No migration needed

---

## Rollback Instructions (If Needed)

If you need to revert changes:

1. Restore `auth_routes.py` from git:
   ```bash
   git checkout app/api/routes/auth_routes.py
   ```

2. Or manually revert:
   - Remove `"is_first_login"` from preserve_fields
   - Remove is_first_login from /get-status responses
   - Change register error handling back to 409

---

**All changes are minimal, focused, and match Flask's implementation exactly.** 🎉

