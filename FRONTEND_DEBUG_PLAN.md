# Frontend Debug Plan

## What's Wrong?

User says "the frontend is fucked" - need to identify the specific issue.

## Possible Issues:

### 1. Frontend Not Picking Up Changes (Most Likely)
**Symptom:** Changes to DeviceProvisioning.tsx not visible in browser
**Cause:** React dev server needs restart to pick up some changes
**Fix:**
```bash
# Kill current frontend process
taskkill /F /PID 17628

# Restart frontend
cd hospital-display-app
npm start
```

### 2. Runtime JavaScript Error
**Symptom:** White screen or error overlay
**Check:** Browser console (F12) for errors
**Common errors:**
- Undefined variable
- Import issues
- Type mismatch

### 3. API Connection Error
**Symptom:** PIN generation button doesn't work
**Check:** Network tab in browser (F12)
**Common errors:**
- CORS issues
- 401 Unauthorized
- 404 Not Found for /api/v1/provisioning/generate-code

### 4. Route/Navigation Issue
**Symptom:** Can't find Device Provisioning page
**Check:** How is DeviceProvisioning.tsx imported in App.tsx?
**Fix:** Verify routing configuration

### 5. Permission Issue
**Symptom:** "Access Denied" message
**Check:** User role in database
**Fix:** Ensure logged in as Administrator/Technician

## Quick Diagnosis Commands

### Check if DeviceProvisioning is imported in App
```bash
cd hospital-display-app/src
grep -r "DeviceProvisioning" App.tsx
```

### Check routing
```bash
grep -r "DeviceProvisioning" *.tsx
```

### Restart frontend cleanly
```bash
taskkill /F /PID 17628
cd hospital-display-app
npm start
```

## Next Steps

1. User needs to tell me WHAT SPECIFICALLY is broken:
   - White screen?
   - Error message?
   - Can't login?
   - Can't see PIN page?
   - Button doesn't work?
   - Something else?

2. Once I know the specific symptom, I can fix it properly.
