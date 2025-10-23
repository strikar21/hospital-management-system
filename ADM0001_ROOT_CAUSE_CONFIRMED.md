# ADM0001 Login Issue - ROOT CAUSE CONFIRMED

## Problem
User `ADM0001` shows **PIN login page** instead of **password login page**.

---

## ROOT CAUSE CONFIRMED

**Backend is running HTTP, but frontend is configured for HTTPS**

### Backend Configuration ❌

**File:** [hospital-backend/app/core/config.py:65](hospital-backend/app/core/config.py#L65)
```python
enableSsl: bool = Field(default=False, validation_alias="ENABLE_SSL")
```

**Settings:** `enableSsl = False` (default)

**Backend starts as:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```
No SSL configuration passed → Running on **HTTP** port 8001

### Frontend Configuration ❌

**File:** [hospital-display-app/src/config/apiConfig.ts:7-8](hospital-display-app/src/config/apiConfig.ts#L7-L8)
```typescript
BACKEND_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'https://localhost:8001'  // ❌ TRYING TO USE HTTPS
```

**Frontend calls:** `https://localhost:8001/api/v1/auth/check-type?staffId=ADM0001`

---

## Test Proof

### HTTP Works ✅
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

### HTTPS Fails ❌
```bash
$ curl -k "https://localhost:8001/api/v1/auth/check-type?staffId=ADM0001"
curl: (35) schannel: next InitializeSecurityContext failed: SEC_E_INVALID_TOKEN
```

**Error:** SSL/TLS handshake fails because backend doesn't have SSL certificates configured.

---

## Why PIN Login Shows

### Frontend Error Handling Flow

1. **Frontend tries HTTPS request:** `https://localhost:8001/api/v1/auth/check-type?staffId=ADM0001`
2. **Request fails:** SSL/TLS error (backend is HTTP, not HTTPS)
3. **AuthService.ts catches error:** [Lines 156-160](hospital-display-app/src/services/AuthService.ts#L156-L160)
   ```typescript
   } catch (error) {
     // Error checking authentication type
     // Fallback to PIN for safety
     return { requiresPin: true, requiresPassword: false };
   }
   ```
4. **Returns fallback:** `{ requiresPin: true, requiresPassword: false }`
5. **HybridLogin.tsx receives fallback:** [Lines 51-71](hospital-display-app/src/HybridLogin.tsx#L51-L71)
   ```typescript
   if (staffIdtocheck.startsWith('ADM') || staffIdtocheck.startsWith('PRV')) {
     // Admin/Provisioner: Prefer password over PIN
     if (authInfo.requiresPassword) {  // ❌ FALSE (from fallback)
       setAuthType('password');
     } else if (authInfo.requiresPin) {  // ✅ TRUE (from fallback)
       setAuthType('pin');  // ❌ SHOWS PIN LOGIN
     }
   }
   ```
6. **Result:** Shows PIN login instead of password login

---

## Solution Options

### Option 1: Change Frontend to HTTP (SIMPLEST) ✅

**File:** [hospital-display-app/src/config/apiConfig.ts](hospital-display-app/src/config/apiConfig.ts)

```typescript
// CHANGE FROM:
BACKEND_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'https://localhost:8001'  // ❌ HTTPS
  : (process.env.REACT_APP_BACKEND_URL || 'https://localhost:8001'),

WS_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'wss://localhost:8001'  // ❌ WSS
  : (process.env.REACT_APP_WS_URL || 'wss://localhost:8001'),

// CHANGE TO:
BACKEND_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'http://localhost:8001'  // ✅ HTTP
  : (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'),

WS_BASE_URL: process.env.NODE_ENV === 'development'
  ? 'ws://localhost:8001'  // ✅ WS
  : (process.env.REACT_APP_WS_URL || 'ws://localhost:8001'),
```

**Steps:**
1. Edit `apiConfig.ts` (change https → http, wss → ws)
2. Restart React frontend (`npm start`)
3. Test login with ADM0001
4. Should now show password login

---

### Option 2: Enable SSL on Backend (MORE COMPLEX)

**Would require:**
1. Generate SSL certificates
2. Set environment variables:
   ```bash
   ENABLE_SSL=true
   SSL_CERT_PATH=/path/to/cert.pem
   SSL_KEY_PATH=/path/to/key.pem
   ```
3. Restart backend with SSL config
4. Keep frontend as HTTPS

**Note:** For development, this is overkill. Use HTTP for simplicity.

---

## Recommendation

**Use Option 1** - Change frontend to HTTP

**Reasoning:**
- Development environment doesn't need SSL
- HTTP is faster (no SSL overhead)
- Easier to debug (no certificate issues)
- Can add SSL later for production deployment

---

## Expected Result After Fix

### Login Flow with ADM0001:

1. **User types:** `ADM0001` in staff ID field
2. **Frontend calls:** `http://localhost:8001/api/v1/auth/check-type?staffId=ADM0001` ✅
3. **Backend returns:** `{ hasPin: true, hasPassword: true }` ✅
4. **Frontend receives:** `{ requiresPin: true, requiresPassword: true }` ✅
5. **Frontend logic:** ADM prefix → prefer password ✅
6. **Shows:** Password login field ✅
7. **User enters:** password "hospital123"
8. **Login succeeds:** Welcome Lisa Thompson! ✅

---

## Files to Modify

**Only 1 file needs to change:**

- [hospital-display-app/src/config/apiConfig.ts](hospital-display-app/src/config/apiConfig.ts)
  - Line 8: Change `https://localhost:8001` → `http://localhost:8001`
  - Line 17: Change `wss://localhost:8001` → `ws://localhost:8001`

---

## Verification Steps

1. Edit apiConfig.ts (https → http)
2. Restart frontend: `npm start`
3. Open browser: `http://localhost:3000`
4. Type staff ID: `ADM0001`
5. **Should see:** Password field (not PIN)
6. Enter password: `hospital123`
7. **Should login:** Welcome Lisa Thompson!

---

## Database Confirms Both Auth Methods Work

ADM0001 has:
- PIN: SET ✅
- Password: SET ✅

Both authentication methods are configured correctly in the database. The issue is purely a frontend-backend communication problem due to HTTP/HTTPS mismatch.
