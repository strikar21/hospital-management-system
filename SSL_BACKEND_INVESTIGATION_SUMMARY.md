# SSL Backend Investigation Summary

## User Question
"i thought backend must also run on https"

## Investigation Results

### Configuration ✅
- `.env` file has: `ENABLE_SSL=True`
- SSL certificates exist in `hospital-backend/ssl/`
- Paths configured: `ssl/cert.pem` and `ssl/key.pem`
- Backend config loads correctly

### The Problem ❌
**Backend is running on HTTP, not HTTPS**

Test results:
```bash
# HTTP works:
$ curl "http://localhost:8001/api/v1/auth/check-type?staffId=ADM0001"
{"hasPin":true,"hasPassword":true}  # ✅ WORKS

# HTTPS fails:
$ curl -k "https://localhost:8001/api/v1/auth/check-type?staffId=ADM0001"
curl: (35) SSL handshake failed  # ❌ FAILS
```

---

## Root Cause

The backend was started with:
```powershell
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

This command **bypasses** the SSL configuration in `main.py` because:
1. `uvicorn` command line doesn't include `--ssl-certfile` or `--ssl-keyfile`
2. The SSL config in `main.py` lines 464-481 only applies when running `python main.py`

---

## Solution

**Stop using:** `python -m uvicorn main:app --reload ...`

**Start using:** `python main.py`

This will load the SSL configuration from `main.py`:
```python
ssl_config = {}
if settings.enableSsl and settings.sslCertPath and settings.sslKeyPath:
    if os.path.exists(settings.sslCertPath) and os.path.exists(settings.sslKeyPath):
        ssl_config = {
            "ssl_certfile": settings.sslCertPath,
            "ssl_keyfile": settings.sslKeyPath
        }
        logger.info(f"🔒 HTTPS enabled with SSL certificate: {settings.sslCertPath}")

uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8001,
    reload=False,
    log_level="info",
    **ssl_config  # ← SSL config passed here
)
```

---

## Steps to Fix

### 1. Kill Current Backend
```powershell
# Find PID listening on port 8001
Get-NetTCPConnection -LocalPort 8001 | Select OwningProcess

# Kill it
Stop-Process -Id <PID> -Force
```

### 2. Start Backend with SSL
```powershell
cd hospital-backend
python main.py
```

### 3. Verify HTTPS Works
```bash
# Should now work with HTTPS:
curl -k https://localhost:8001/health
```

### 4. Check Frontend Still Works
The frontend is already configured for HTTPS in `apiConfig.ts`:
```typescript
BACKEND_BASE_URL: 'https://localhost:8001'  // ✅ Correct!
WS_BASE_URL: 'wss://localhost:8001'  // ✅ Correct!
```

So once backend starts with SSL, the frontend should work immediately.

---

## Why This Matters

**Security:**
- HTTPS encrypts all traffic between frontend and backend
- Protects patient data (HIPAA compliance)
- Prevents man-in-the-middle attacks

**ADM0001 Login Issue:**
- Frontend expects HTTPS
- When HTTPS fails, frontend falls back to PIN login
- Once HTTPS works, ADM0001 will show password login

---

## Expected Behavior After Fix

1. **Backend starts with log:**
   ```
   🔒 HTTPS enabled with SSL certificate: ssl/cert.pem
   ```

2. **HTTPS endpoint works:**
   ```bash
   $ curl -k https://localhost:8001/api/v1/auth/check-type?staffId=ADM0001
   {"hasPin":true,"hasPassword":true}
   ```

3. **Frontend connects successfully:**
   - `https://localhost:8001` works
   - ADM0001 shows password login (not PIN)

---

## Current Status

- ✅ SSL certificates exist
- ✅ Configuration is correct (.env, main.py)
- ❌ Backend started with wrong command (uvicorn directly)
- ⏳ **Need to restart backend with `python main.py`**

---

## Quick Fix Commands

```powershell
# 1. Kill current backend
$pid = (Get-NetTCPConnection -LocalPort 8001 | Select -First 1).OwningProcess
Stop-Process -Id $pid -Force

# 2. Start backend with SSL
cd C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend
python main.py

# 3. Test HTTPS (in Git Bash)
curl -k https://localhost:8001/health
```

---

## Alternative: Keep HTTP for Development

If you prefer HTTP for development (faster, no SSL overhead):

**Option A:** Disable SSL in `.env`
```
ENABLE_SSL=False
```

**Option B:** Change frontend to HTTP in `apiConfig.ts`
```typescript
BACKEND_BASE_URL: 'http://localhost:8001'
WS_BASE_URL: 'ws://localhost:8001'
```

**Recommendation:** Use HTTPS even in development to match production.

---

## Related Issue: ADM0001 PIN Login

This is WHY ADM0001 shows PIN login instead of password:
1. Frontend tries: `https://localhost:8001/api/v1/auth/check-type`
2. Backend is HTTP only → SSL handshake fails
3. Frontend catches error → falls back to PIN login

**Fix:** Start backend with SSL, then ADM0001 will show password login.
