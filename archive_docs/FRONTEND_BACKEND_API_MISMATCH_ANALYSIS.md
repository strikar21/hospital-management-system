# Frontend-Backend API Endpoint Mismatch Analysis

**Date**: 2025-10-14
**Status**: Backend Running, Frontend Errors Detected

## Summary

Backend server is running successfully on port 8001, but frontend is experiencing two API errors due to endpoint mismatches and authentication issues.

---

## Issue 1: Audit Logging - 403 Forbidden

### Frontend Request
- **URL**: `POST http://localhost:8001/api/v1/audit/log`
- **Error**: 403 Forbidden
- **Source**: [hospital-display-app/src/services/auditService.ts:289](hospital-display-app/src/services/auditService.ts#L289)

### Backend Endpoint
- **File**: [hospital-backend/app/api/v1/audit.py:16](hospital-backend/app/api/v1/audit.py#L16)
- **Route**: `@router.post("/log")`
- **Authentication**: `dependencies=[Depends(require_any_staff)]` (requires auth token)

### Root Cause
The audit endpoint **requires authentication** (JWT token from logged-in staff), but the frontend may be calling it before user authentication or without proper auth headers.

### Recommended Solution
**Option 1 (Quick Fix)**: Make audit logging non-blocking on frontend
- Frontend should catch 403 errors silently
- Audit logging should not block UI functionality

**Option 2 (Proper Fix)**: Ensure auth token is passed
- Frontend should only call audit endpoints after successful login
- Include JWT token in Authorization header

---

## Issue 2: Watch Management - 404 Not Found

### Frontend Request
- **URL**: `POST http://localhost:8001/api/v1/watch-management/assign`
- **Error**: 404 Not Found
- **Source**: [hospital-display-app/src/services/DeviceService.ts:113](hospital-display-app/src/services/DeviceService.ts#L113)
- **Code**:
```typescript
const response = await this.fetchFromBackend(`/watch-management/assign`, {
  method: 'POST',
  // ...
});
```

### Backend Endpoint
- **File**: [hospital-backend/app/api/v1/watch_management.py:118](hospital-backend/app/api/v1/watch_management.py#L118)
- **Registered In**: [hospital-backend/main.py:272](hospital-backend/main.py#L272)
- **Registration**:
```python
app.include_router(watchManagementRouter, prefix=f"{settings.apiV1Str}/watchmanagement", tags=["Watch Management"])
```
- **Actual URL**: `/api/v1/watchmanagement/assign` (NO hyphen)

### Root Cause
**Frontend uses hyphenated path**: `/watch-management/assign`
**Backend registered without hyphen**: `/watchmanagement/assign`

### Recommended Solution
**Option 1 (Frontend Fix)**: Update DeviceService.ts
- Change `/watch-management/assign` → `/watchmanagement/assign`
- Change `/watch-management/unassign` → `/watchmanagement/unassign`

**Option 2 (Backend Fix)**: Update main.py router registration
- Change `prefix="/watchmanagement"` → `prefix="/watch-management"`
- More RESTful naming convention

---

## Verification Steps

### Check Backend Routes
Backend is currently running. To verify available routes:
1. Visit `http://localhost:8001/docs` (Swagger UI)
2. Confirm registered endpoints

### Expected Working Endpoints
Based on backend registration in [main.py](hospital-backend/main.py):
- ✅ `/api/v1/auth/*`
- ✅ `/api/v1/audit/*`
- ✅ `/api/v1/watchmanagement/*` (no hyphen)
- ✅ `/api/v1/devices/*`
- ✅ `/api/v1/discharge/*`
- ✅ `/api/v2/devices/*`

---

## Recommended Implementation Plan

### Phase 1: Quick Fixes
1. **Fix watch-management endpoint mismatch**
   - Update frontend DeviceService.ts paths
   - Test device assignment functionality

2. **Make audit logging resilient**
   - Add try-catch in frontend audit service
   - Log errors but don't block UI

### Phase 2: Proper Auth Flow
1. **Ensure auth token flow**
   - Verify BaseService includes auth headers after login
   - Test all authenticated endpoints

2. **Audit endpoint authentication**
   - Verify audit logging works after user login
   - Consider making audit log optional/best-effort

---

## Files Requiring Changes

### Frontend Files
1. [hospital-display-app/src/services/DeviceService.ts](hospital-display-app/src/services/DeviceService.ts)
   - Line 113: `/watch-management/assign` → `/watchmanagement/assign`
   - Line 164: `/watch-management/unassign` → `/watchmanagement/unassign`

2. [hospital-display-app/src/services/auditService.ts](hospital-display-app/src/services/auditService.ts)
   - Add error handling for 403 responses
   - Make audit logging non-blocking

### Backend Files (Alternative)
If we prefer backend changes:
1. [hospital-backend/main.py](hospital-backend/main.py)
   - Line 272: Change router prefix to `/watch-management`

---

## Testing Checklist

After fixes:
- [ ] Device assignment works without 404 error
- [ ] Device unassignment works without 404 error
- [ ] Audit logging doesn't block UI (even if 403)
- [ ] Login flow provides auth token
- [ ] Authenticated requests include Bearer token
- [ ] Swagger docs at `/docs` shows correct endpoints

---

## Current Backend Status

✅ **Backend is Running Successfully**
- Server: `http://0.0.0.0:8001`
- PostgreSQL: Connected
- TimescaleDB: Connected
- WebSocket: Active
- ESP32 watches: Receiving heartbeats (ESP32_WATCH_003 @ 20% battery)

⚠️ **Services Not Available**
- MQTT service: Not started
- Watch monitoring: Not started

---

## Next Steps

**Question for User**:
Should we:
1. Fix frontend paths to match backend (faster, less risky)
2. Fix backend route registration to match frontend (more RESTful)
3. Both - align on consistent naming convention across all endpoints

**Recommendation**: Fix frontend paths first (Option 1) - it's a 2-line change and less likely to break other systems.
