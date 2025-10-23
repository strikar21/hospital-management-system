# ADM0001 Login Issue - Root Cause Diagnosis

## Problem

User `ADM0001` shows **PIN login page** instead of **password login page** in the frontend.

---

## Investigation Results

### Database Check ✅

```bash
$ python check_adm0001_auth.py

[Checking ADM0001 authentication fields]
  Staff ID: ADM0001
  Name: Lisa Thompson
  Role: Administrator
  Active: True
  PIN: SET ✅
  Password: SET ✅
  NFC Card: SET ✅

[Backend /auth/check-type response]
  hasPin: True
  hasPassword: True

[Frontend HybridLogin.tsx logic for ADM prefix]
  Would show: PASSWORD login (preferred)
```

**Result:** Database has BOTH PIN and password configured correctly.

---

### Backend Endpoint Test ✅

```bash
$ curl "http://localhost:8001/api/v1/auth/check-type?staffId=ADM0001"

{
    "authMethods": ["pin", "password", "nfc"],
    "staffId": "ADM0001",
    "hasPin": true,
    "hasPassword": true,
    "hasNfc": true
}
```

**Result:** Backend is returning correct data - BOTH `hasPin: true` and `hasPassword: true`.

---

### Frontend Logic Check ✅

**File:** [hospital-display-app/src/HybridLogin.tsx:57-63](hospital-display-app/src/HybridLogin.tsx#L57-L63)

```typescript
if (staffIdtocheck.startsWith('ADM') || staffIdtocheck.startsWith('PRV')) {
  // Admin/Provisioner: Prefer password over PIN
  if (authInfo.requiresPassword) {
    setAuthType('password');
  } else if (authInfo.requiresPin) {
    setAuthType('pin');  // Fallback if no password
  }
}
```

**Expected Behavior:** If `authInfo.requiresPassword` is true, show password login.

**File:** [hospital-display-app/src/services/AuthService.ts:132-148](hospital-display-app/src/services/AuthService.ts#L132-L148)

```typescript
static async checkAuthType(staffId: string): Promise<{ requiresPin: boolean, requiresPassword: boolean } | null> {
  const response = await this.fetchFromBackend(`/auth/check-type?staffId=${encodeURIComponent(sanitizedStaffId)}`);

  if (response) {
    return {
      requiresPin: response.hasPin || false,
      requiresPassword: response.hasPassword || false
    };
  }
  ...
}
```

**Logic:** `requiresPassword` should be `true` if backend returns `hasPassword: true`.

---

## ROOT CAUSE FOUND ❌

### Frontend API Configuration Issue

**File:** [hospital-display-app/src/config/apiConfig.ts:7-8](hospital-display-app/src/config/apiConfig.ts#L7-L8)

```typescript
BACKEND_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'https://localhost:8001'  // ❌ USING HTTPS
```

**Backend is actually running on:** `http://localhost:8001` (HTTP, not HTTPS)

### Test Proof:

```bash
# HTTP works:
$ curl "http://localhost:8001/api/v1/auth/check-type?staffId=ADM0001"
{
    "authMethods": ["pin", "password", "nfc"],
    "staffId": "ADM0001",
    "hasPin": true,
    "hasPassword": true,
    "hasNfc": true
}

# HTTPS would fail:
$ curl "https://localhost:8001/api/v1/auth/check-type?staffId=ADM0001"
curl: (35) schannel: next InitializeSecurityContext failed: Unknown error (0x80092012)
```

---

## Why PIN Login Shows Instead of Password?

### Frontend Fallback Logic

**File:** [hospital-display-app/src/services/AuthService.ts:156-160](hospital-display-app/src/services/AuthService.ts#L156-L160)

```typescript
} catch (error) {
  // Error checking authentication type
  // Fallback to PIN for safety
  return { requiresPin: true, requiresPassword: false };
}
```

**What Happens:**

1. Frontend tries to call `https://localhost:8001/api/v1/auth/check-type?staffId=ADM0001`
2. Backend is running on HTTP (port 8001), not HTTPS
3. Request **fails** with SSL/TLS error
4. Frontend catches error and **falls back to PIN login** (line 159)
5. Frontend then checks staff ID prefix in [HybridLogin.tsx:84-92](hospital-display-app/src/HybridLogin.tsx#L84-L92):
   ```typescript
   } catch (err) {
     // If staff endpoint fails, default based on staff ID pattern
     if (staffIdtocheck.startsWith('ADM') || staffIdtocheck.startsWith('PRV')) {
       setAuthType('password');  // ❌ BUT THIS IS IN THE OUTER CATCH
     }
   ```

Wait, this should set it to password... Let me check the logic flow again.

Actually, looking at the code more carefully:

**File:** [hospital-display-app/src/HybridLogin.tsx:48-72](hospital-display-app/src/HybridLogin.tsx#L48-L72)

The logic is:
1. Call backend `checkAuthType()` (AuthService.ts)
2. If backend returns data with `hasPin: true` and `hasPassword: true`
3. For ADM prefix, prefer password: `if (authInfo.requiresPassword) setAuthType('password')`

**The issue is:**
- Backend call is failing due to HTTPS vs HTTP mismatch
- `checkAuthType()` in AuthService.ts catches error and returns `{ requiresPin: true, requiresPassword: false }`
- Frontend receives this fallback response
- Frontend then checks: `if (authInfo.requiresPassword)` → **FALSE** (because fallback set it to false)
- Falls through to: `else if (authInfo.requiresPin)` → **TRUE** → Shows PIN login

---

## Solution

**Change frontend API config from HTTPS to HTTP:**

**File:** [hospital-display-app/src/config/apiConfig.ts](hospital-display-app/src/config/apiConfig.ts)

```typescript
// BEFORE (INCORRECT):
BACKEND_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'https://localhost:8001'  // ❌ Backend doesn't have SSL
  : (process.env.REACT_APP_BACKEND_URL || 'https://localhost:8001'),

WS_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'wss://localhost:8001'  // ❌ Backend doesn't have SSL
  : (process.env.REACT_APP_WS_URL || 'wss://localhost:8001'),

// AFTER (CORRECT):
BACKEND_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'http://localhost:8001'  // ✅ Match actual backend
  : (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'),

WS_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'ws://localhost:8001'  // ✅ Match actual backend
  : (process.env.REACT_APP_WS_URL || 'ws://localhost:8001'),
```

---

## Why This Wasn't Caught Earlier

The backend logs likely show these failed HTTPS connection attempts as connection errors, but they may not be visible in the terminal where backend is running.

The frontend silently falls back to PIN login without showing a visible error to the user, making it hard to diagnose.

---

## Verification Steps After Fix

1. **Change apiConfig.ts** - Use HTTP instead of HTTPS
2. **Restart React frontend** - `npm start`
3. **Login with ADM0001**
4. **Should now show:** Password login field (not PIN)
5. **Backend logs should show:** Successful `/auth/check-type` call

---

## Files to Modify

- [hospital-display-app/src/config/apiConfig.ts](hospital-display-app/src/config/apiConfig.ts) - Lines 7-8 and 16-17

---

## Alternative: Enable SSL on Backend (More Complex)

If you want to use HTTPS properly:

1. Generate SSL certificates
2. Configure backend to use SSL (main.py lines 464-473)
3. Keep frontend config as HTTPS

But for development, HTTP is simpler and faster.
