# Staff Resolution Fix Plan

**Issue:** Frontend shows staff IDs instead of names
**Root Cause:** Not all API endpoints use staff resolution middleware
**Date:** 2025-11-10

---

## Problem Analysis

### What Works ✅
- `StaffResolver` class exists in `app/domain/staff/resolver.py`
- `resolve_staff_in_response()` middleware exists in `app/middleware/staff_resolution_middleware.py`
- Some endpoints use staff resolution:
  - ✅ `app/api/v2/medications.py` - uses `resolve_staff_names` utility
  - ✅ `app/api/v2/patients.py` - uses `resolve_staff_in_response` middleware
  - ✅ `app/api/v1/device_management.py` - uses `resolve_staff_in_response` middleware
  - ✅ `app/api/v1/watch_management.py` - uses `resolve_staff_in_response` middleware

### What's Broken ❌
**`app/api/v2/atomic_medical.py`** - 11 POST endpoints return staff IDs without resolution

All atomic endpoints return `AtomicResponse` which contains:
- `medicalRecord` - has staff ID fields (`prescribedBy`, `performedBy`, etc.)
- `caseEntry` - has staff ID fields (`authorId`, `createdBy`, etc.)

**Missing staff resolution** means frontend receives IDs like "DOC001" instead of "Dr. Jane Smith"

---

## Solution Strategy

### Approach 1: Add Middleware to Each Endpoint (Recommended)
Use the existing `resolve_staff_in_response()` middleware function

**Pros:**
- Uses existing, tested middleware
- Consistent with other endpoints (medications.py, patients.py)
- Handles nested objects automatically
- No code duplication

**Cons:**
- Need to modify each endpoint function
- Adds database query to every atomic operation

### Approach 2: Middleware Decorator
Create a decorator that auto-applies staff resolution

**Pros:**
- Clean, declarative
- Easy to apply to multiple endpoints

**Cons:**
- Need to create new decorator (more work)
- May complicate error handling

### Approach 3: Response Model Post-Processing
Modify `AtomicResponse` model to auto-resolve

**Pros:**
- Centralized in one place

**Cons:**
- Pydantic models shouldn't have database access
- Breaks separation of concerns

---

## Recommended Solution: Approach 1

Add `resolve_staff_in_response()` to all atomic endpoints

### Implementation Steps

1. Import the middleware in atomic_medical.py:
```python
from ...middleware import resolve_staff_in_response
from ...core.database import getDbConnection
```

2. Wrap response before returning:
```python
# Before returning AtomicResponse
async with getDbConnection() as conn:
    result = await resolve_staff_in_response(result, conn)

return AtomicResponse(**result)
```

3. Apply to all 11 endpoints that return `AtomicResponse`

---

## Staff ID Fields to Resolve

The middleware automatically resolves these fields:
- `prescribedBy` → adds `prescribedByName`, `prescribedByRole`
- `performedBy` → adds `performedByName`, `performedByRole`
- `createdBy` → adds `createdByName`, `createdByRole`
- `modifiedBy` → adds `modifiedByName`, `modifiedByRole`
- `assignedBy` → adds `assignedByName`, `assignedByRole`
- `authorId` → adds `authorIdName`, `authorIdRole`
- `completedBy` → adds `completedByName`, `completedByRole`
- `acknowledgedBy` → adds `acknowledgedByName`, `acknowledgedByRole`
- `editedBy` → adds `editedByName`, `editedByRole`

---

## Endpoints to Fix

### atomic_medical.py (11 endpoints)

1. ✅ `/patients/{patient_id}/medications` (POST) - add_medication_atomic_endpoint
2. ✅ `/patients/{patient_id}/investigations` (POST) - add_investigation_atomic_endpoint
3. ✅ `/patients/{patient_id}/therapies` (POST) - add_therapy_atomic_endpoint
4. ✅ `/patients/{patient_id}/notes` (POST) - add_note_atomic_endpoint
5. ❌ `/patients/{patient_id}/medical-action` (POST) - execute_medical_action_endpoint (generic, skip for now)
6. ✅ `/patients/{patient_id}/medications/{medication_id}/administer` (POST) - administer_medication_atomic_endpoint
7. ✅ `/patients/{patient_id}/therapies/{therapy_id}/sessions` (POST) - record_therapy_session_atomic_endpoint
8. ✅ `/patients/{patient_id}/alerts/{alert_id}/acknowledge` (POST) - acknowledge_alert_atomic_endpoint
9. ✅ `/patients/{patient_id}/investigations/{investigation_id}/complete` (POST) - complete_investigation_atomic_endpoint
10. ✅ `/patients/{patient_id}/medications/{medication_id}/status` (POST) - update_medication_status_atomic_endpoint
11. ❌ `/patients/{patient_id}/transaction-status/{transaction_id}` (GET) - doesn't return medical records

**Total to fix:** 9 endpoints

---

## Testing Plan

After fixes:

1. **Manual Testing:**
   - Call each endpoint
   - Verify response includes both ID and Name fields
   - Example: `{"prescribedBy": "DOC001", "prescribedByName": "Dr. Jane Smith", "prescribedByRole": "Doctor"}`

2. **Frontend Testing:**
   - Verify patient case sheet shows staff names
   - Verify medications list shows prescriber names
   - Verify investigations show ordering doctor names
   - Verify alerts show acknowledging staff names

3. **Edge Cases:**
   - Test with "SYSTEM" user (should show "System" as name)
   - Test with inactive staff (should show "Unknown (ID)")
   - Test with missing staff IDs (should handle gracefully)

---

## Performance Considerations

**Current:** Each endpoint makes 0 staff resolution queries (returns IDs only)
**After Fix:** Each endpoint makes 1 batch query (all unique staff IDs in single query)

**Impact:** Minimal - staff resolution uses:
- Batch query (one query for all unique staff IDs)
- Caching (subsequent resolutions use cache)
- Typically < 50ms additional latency

**Optimization:** Already optimized by middleware's batch resolution

---

## Alternative: Global Middleware (Future Enhancement)

Instead of manually adding resolution to each endpoint, create FastAPI middleware that automatically resolves staff fields in ALL responses.

**Future Work:** Create global middleware in `app/middleware/__init__.py`:
```python
@app.middleware("http")
async def auto_resolve_staff(request: Request, call_next):
    response = await call_next(request)
    # Auto-resolve staff in response body
    return response
```

**Not implementing now** because:
- Requires testing all endpoints
- May break some endpoints that deliberately return IDs only
- Current fix is safer and more targeted

---

## Status

**Current:** Planning phase
**Next:** Implement fixes in atomic_medical.py
**ETA:** 30 minutes to fix all 9 endpoints + testing

