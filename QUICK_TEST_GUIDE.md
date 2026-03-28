# QUICK TEST GUIDE - Login/Profile Flow Testing

## 🧪 Test Your Fixes in 5 Minutes

### Prerequisites
- Server running: `cd Server1_FastApi && python run.py`
- Server should be at: `http://127.0.0.1:8080`
- Have a test Firebase account ready (or use existing account)

### Test 1: New User Registration (2 min)

```bash
# 1. Register as brand new user
POST http://127.0.0.1:8080/register
Content-Type: application/json

{
  "idToken": "<YOUR_FIREBASE_TOKEN>",
  "turnstileToken": "<TURNSTILE_TOKEN>"
}

✅ EXPECTED: 
{
  "token": "eyJ...",
  "message": "Registration successful!",
  "promo_active": false
}
```

### Test 2: Check Session - Should Show is_first_login: true (30 sec)

```bash
# 2. Check session immediately after registration
GET http://127.0.0.1:8080/session
Authorization: Bearer eyJ...

✅ EXPECTED:
{
  "authenticated": true,
  "user": {
    "user_id": "...",
    "email": "...",
    "is_first_login": true,          ← ✅ MUST BE TRUE for new user
    "active_days": 1,
    "energy_level": 1,
    ...
  }
}

🐛 IF MISSING is_first_login field → STILL BROKEN
⚠️ IF is_first_login: false → Wrong, should be true
```

### Test 3: Complete Profile/Onboarding (1 min)

```bash
# 3. Mark onboarding as complete
POST http://127.0.0.1:8080/complete-onboarding
Authorization: Bearer eyJ...

✅ EXPECTED:
{
  "message": "Onboarding marked complete"
}
```

### Test 4: Check Session Again - Should Show is_first_login: false (30 sec)

```bash
# 4. Check session after completing onboarding
GET http://127.0.0.1:8080/session
Authorization: Bearer eyJ...

✅ EXPECTED:
{
  "authenticated": true,
  "user": {
    "user_id": "...",
    "is_first_login": false,         ← ✅ MUST BE FALSE after onboarding
    ...
  }
}

🐛 IF is_first_login: true → NOT FIXED YET
```

### Test 5: Check Get Status - Should Return is_first_login (1 min)

```bash
# 5. Check /get-status endpoint
GET http://127.0.0.1:8080/get-status
Authorization: Bearer eyJ...

✅ EXPECTED:
{
  "user_id": "...",
  "is_first_login": false,           ← ✅ MUST BE PRESENT
  "is_online": true,
  "last_seen": "2026-03-24T...",
  "username": "...",
  "active_days": 1,                  ← ✅ NEW: Must be present
  "energy_level": 1                  ← ✅ NEW: Must be present
}

🐛 IF is_first_login field missing → STILL BROKEN
🐛 IF active_days missing → STILL BROKEN
🐛 IF energy_level missing → STILL BROKEN
```

---

## 🎯 WHAT YOU SHOULD SEE NOW

### ✅ Fixed Behavior:

1. **New User Registration:**
   - `is_first_login: true` after registration ✅
   - Frontend redirects to profile page ✅

2. **After Profile Completion:**
   - `is_first_login: false` after `/complete-onboarding` ✅
   - Frontend shows dashboard ✅

3. **Next Day - User Logs In Again:**
   - `is_first_login: false` after login ✅ (NOT reset to true)
   - Frontend shows dashboard immediately ✅
   - NO redirect to profile generation page ✅

4. **/get-status Endpoint:**
   - Returns `is_first_login` field ✅
   - Returns `active_days` and `energy_level` ✅
   - No missing fields ✅

---

## 🔧 Troubleshooting

### Issue: /session returns is_first_login but /get-status doesn't

**Status:** ✅ FIXED - Both endpoints now return the field

### Issue: is_first_login keeps resetting to true

**Status:** ✅ FIXED - Now explicitly preserved in preserve_fields

### Issue: Register returns 409 error for existing user

**Status:** ✅ FIXED - Now updates gracefully instead of erroring

### Issue: is_first_login missing from /get-status response

**Status:** ✅ FIXED - Now included in response

---

## 📊 Testing Matrix

Use this to verify each endpoint:

| Endpoint | Method | Auth? | is_first_login? | active_days? | energy_level? | Status |
|----------|--------|-------|---|---|---|---|
| /register | POST | No | N/A | N/A | N/A | ✅ |
| /login | POST | No | N/A | N/A | N/A | ✅ |
| /session | GET | Yes | ✅ Should return | N/A | N/A | ✅ |
| /get-status | GET | Yes | ✅ Should return | ✅ Should return | ✅ Should return | ✅ FIXED |
| /get-status/{user_id} | GET | Yes | ✅ Should return | ✅ Should return | ✅ Should return | ✅ FIXED |
| /complete-onboarding | POST | Yes | N/A | N/A | N/A | ✅ |

---

## ✅ SUCCESS CRITERIA

Your fixes are working correctly if:

- [ ] New user has `is_first_login: true` in /session
- [ ] After onboarding, user has `is_first_login: false` in /session
- [ ] User logs out, logs back in, and `is_first_login: false` is preserved
- [ ] /get-status returns `is_first_login` field
- [ ] /get-status returns `active_days` field
- [ ] /get-status returns `energy_level` field
- [ ] Register works for both new and existing users
- [ ] No "new user" redirect when logging in as returning user
- [ ] Dashboard shows immediately for returning users

---

## 🚀 NEXT STEPS

If all tests pass:
1. ✅ Test with your actual frontend
2. ✅ Verify profile generation page shows only for new users
3. ✅ Verify dashboard shows for returning users
4. ✅ Test with real Firebase tokens
5. ✅ Test complete user journey (register → profile → logout → login)

If any test fails:
1. Re-read the AUTHENTICATION_FIXES_FINAL_REPORT.md
2. Check that all changes are in place
3. Restart the server
4. Try test again

---

## 📱 Quick cURL Testing

Copy-paste ready commands (replace tokens with actual values):

```bash
# Register
curl -X POST http://127.0.0.1:8080/register \
  -H "Content-Type: application/json" \
  -d '{"idToken":"TOKEN","turnstileToken":"CAPTCHA"}'

# Session check
curl -X GET http://127.0.0.1:8080/session \
  -H "Authorization: Bearer TOKEN"

# Complete onboarding
curl -X POST http://127.0.0.1:8080/complete-onboarding \
  -H "Authorization: Bearer TOKEN"

# Get status
curl -X GET http://127.0.0.1:8080/get-status \
  -H "Authorization: Bearer TOKEN"

# Login
curl -X POST http://127.0.0.1:8080/login \
  -H "Content-Type: application/json" \
  -d '{"idToken":"TOKEN","turnstileToken":"CAPTCHA"}'
```

---

## 💡 Tips

1. **Keep token from registration** - Use same token to test /session, /get-status, /complete-onboarding
2. **Check timestamp** - active_days and energy_level should reflect actual activity
3. **Verify database** - You can check MongoDB directly to see is_first_login value
4. **Watch server logs** - Check if any errors appear during requests

---

**Good luck! Your fixes should make the login/profile flow work perfectly now.** 🎉

