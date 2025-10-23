# Backend SSL Manual Start Instructions

## Current Situation

The backend is running on HTTP (port 8001) but needs to run on HTTPS for:
1. Security (HIPAA compliance)
2. Fix ADM0001 login issue (frontend expects HTTPS)

## Why Automated Restart Didn't Work

The PowerShell command to start the backend may have failed silently or not loaded the SSL config properly.

---

## Manual Steps to Enable SSL

### Step 1: Open PowerShell/Command Prompt

Open a new PowerShell window manually (not through automation).

### Step 2: Stop Current Backend

If backend is running, find and kill it:

```powershell
# Find PID on port 8001
Get-NetTCPConnection -LocalPort 8001 | Select OwningProcess

# Kill it (replace <PID> with actual PID)
Stop-Process -Id <PID> -Force
```

Or just close the PowerShell window where backend is running.

### Step 3: Navigate to Backend Directory

```powershell
cd C:\Users\Srikar\OneDrive\Desktop\hospital-management-system\hospital-backend
```

### Step 4: Verify SSL Files Exist

```powershell
dir ssl
```

You should see:
```
cert.pem
key.pem
```

### Step 5: Start Backend with SSL

```powershell
python main.py
```

**IMPORTANT:** Use `python main.py`, NOT `python -m uvicorn main:app --reload`

### Step 6: Look for SSL Confirmation in Logs

You should see:
```
🔒 HTTPS enabled with SSL certificate: ssl/cert.pem
INFO:     Uvicorn running on https://0.0.0.0:8001 (Press CTRL+C to quit)
```

If you see this instead:
```
⚠️ SSL paths configured but files not found - running HTTP
```

Then the SSL files weren't found at the expected paths.

---

## Verification

### Test HTTPS Endpoint

Open Git Bash and run:

```bash
curl -k https://localhost:8001/health
```

Expected: `{"status":"healthy"}`

If this works, HTTPS is enabled! ✅

If it fails with SSL error, backend is still on HTTP. ❌

### Test ADM0001 Login

1. Open frontend: `http://localhost:3000`
2. Type staff ID: `ADM0001`
3. **Should show:** Password field (not PIN)

If it shows password field, the issue is fixed! ✅

---

## Troubleshooting

### Problem: "SSL paths configured but files not found"

**Solution:**
```powershell
# Check current directory
pwd

# Should output: C:\Users\Srikar\OneDrive\Desktop\hospital-management-system\hospital-backend

# If not, cd to correct directory first
cd C:\Users\Srikar\OneDrive\Desktop\hospital-management-system\hospital-backend

# Verify SSL files exist
dir ssl\cert.pem
dir ssl\key.pem

# Both should exist
```

### Problem: Backend starts but HTTPS doesn't work

**Check backend logs carefully:**

Look for one of these messages:
- `🔒 HTTPS enabled with SSL certificate: ssl/cert.pem` ✅ SSL enabled
- `⚠️ SSL paths configured but files not found - running HTTP` ❌ SSL disabled
- No SSL message at all ❌ SSL disabled

### Problem: Frontend still shows PIN login for ADM0001

**Possible reasons:**
1. Backend still on HTTP (test with `curl -k https://localhost:8001/health`)
2. Frontend not connecting to backend (check browser console for errors)
3. Frontend cache (hard refresh: Ctrl+Shift+R)

---

## Configuration Reference

### Backend `.env` File (Already Correct)

```env
ENABLE_SSL=True
SSL_CERT_PATH=ssl/cert.pem
SSL_KEY_PATH=ssl/key.pem
```

### Frontend `apiConfig.ts` (Already Correct)

```typescript
BACKEND_BASE_URL: 'https://localhost:8001'
WS_BASE_URL: 'wss://localhost:8001'
```

---

## Quick Checklist

- [ ] Stop current backend (if running)
- [ ] Open PowerShell in `hospital-backend` directory
- [ ] Run `python main.py` (not uvicorn command)
- [ ] See "🔒 HTTPS enabled" in logs
- [ ] Test: `curl -k https://localhost:8001/health` works
- [ ] Open frontend: http://localhost:3000
- [ ] Type ADM0001 → see password field (not PIN)
- [ ] Login works with password "hospital123"

---

## Alternative: Disable SSL (Not Recommended)

If you want to use HTTP for development:

**Change frontend `apiConfig.ts`:**
```typescript
BACKEND_BASE_URL: 'http://localhost:8001'  // HTTP
WS_BASE_URL: 'ws://localhost:8001'  // WS
```

**Or disable SSL in backend `.env`:**
```env
ENABLE_SSL=False
```

**Not recommended** because:
- Less secure
- Doesn't match production
- Medical data should always use HTTPS

---

## Expected Final State

✅ Backend: Running on HTTPS (port 8001)
✅ Frontend: Connects to HTTPS backend
✅ ADM0001: Shows password login (not PIN)
✅ Login works: With password "hospital123"

---

## Current Backend Command That Works

The backend window should show something like:

```
PS C:\Users\Srikar\OneDrive\Desktop\hospital-management-system\hospital-backend> python main.py
INFO:     Started server process [31920]
INFO:     Waiting for application startup.
🔒 HTTPS enabled with SSL certificate: ssl/cert.pem
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:8001 (Press CTRL+C to quit)
```

If you don't see "🔒 HTTPS enabled", then SSL is not working.
