# Device Management - Staff Resolution Audit & Implementation Plan

## Date: 2025-10-13
## Issue: assignedBy/unassignedBy fields not being resolved to staff details

---

## UNDERSTANDING THE QUESTION

User asked: **"so why first name last name? also the assignedby tables?"**

### Clarification:
1. **firstName/lastName**: These are PATIENT names (p."firstName", p."lastName") - **THIS IS CORRECT**
   - We need patient names to display which patient is using each watch
   - Not a problem

2. **assignedBy/unassignedBy**: These are STAFF IDs - **THIS NEEDS STAFF RESOLUTION**
   - Currently just returning staff IDs like "DOC0001", "NUR0001"
   - Should return staff names and roles like "Dr. John Smith (Doctor)"
   - Staff resolution utilities already exist in `app/utils/staff_resolution.py`

---

## CURRENT STATE

### Staff Resolution Infrastructure
✅ **EXISTS**: `app/utils/staff_resolution.py`
- `resolve_staff_names()` function for batch resolution
- `get_staff_names()` function for lookup
- `resolve_staff_in_response()` standalone function

✅ **EXISTS**: `app/middleware/staff_resolution_middleware.py`
- Automatically resolves 9 staff ID fields including `assignedBy`
- Batch resolution with single query
- Recursive handling of nested objects

### Staff Fields in Device Management

#### 1. deviceassignments Table Schema
```sql
- assignedBy: text (staff ID)
- assignedAt: timestamp
- unassignedBy: text (staff ID)  -- MISSING FROM CURRENT SCHEMA OUTPUT
- unassignedAt: timestamp
```

#### 2. Where Staff IDs Appear

**watch_management.py**:
- **Line 72**: `SELECT d.*, da.*, ...` → Includes da.assignedBy
- **Line 127**: `assignedBy = assignmentData.get('assignedBy', 'System')`
- **Line 157-159**: INSERT with assignedBy
- **Line 200**: `unassignedBy = unassignmentData.get('unassignedBy', 'System')`
- **Line 221-223**: UPDATE with unassignedBy

**device_management.py**: (need to check)

---

## THE PROBLEM

### Current Behavior
When frontend calls `/api/v1/watchmanagement/assigned`:

**Current Response**:
```json
{
  "assignedWatches": [{
    "id": "assignment-123",
    "patientId": "PAT001",
    "deviceId": "WATCH001",
    "assignedBy": "DOC0001",         ← Just an ID
    "assignedAt": "2025-10-13T10:00:00Z",
    "firstName": "John",             ← Patient name (correct)
    "lastName": "Smith",             ← Patient name (correct)
    ...
  }]
}
```

**Expected Response (with staff resolution)**:
```json
{
  "assignedWatches": [{
    "id": "assignment-123",
    "patientId": "PAT001",
    "deviceId": "WATCH001",
    "assignedBy": "DOC0001",
    "assignedByName": "Dr. Sarah Johnson",   ← Added by staff resolution
    "assignedByRole": "Doctor",              ← Added by staff resolution
    "assignedAt": "2025-10-13T10:00:00Z",
    "firstName": "John",
    "lastName": "Smith",
    ...
  }]
}
```

---

## ROOT CAUSE ANALYSIS

### Why Staff Resolution Not Working?

1. **Not using resolve_staff_in_response()**: The `watch_management.py` endpoints don't call the staff resolution function before returning responses

2. **No middleware applied**: The endpoints are not using the `@with_staff_resolution` decorator (if it exists)

3. **Manual assignment**: Lines 127 and 200 use fallback `'System'` instead of proper staff ID from JWT token

---

## SOLUTION PLAN

### Phase 1: Verify Staff Resolution Works
**File**: Create test script
**Action**: Test that `resolve_staff_in_response()` correctly resolves assignedBy

### Phase 2: Add Staff Resolution to watch_management.py
**File**: `hospital-backend/app/api/v1/watch_management.py`

#### Location 1: getAssignedWatches() - Line 66-112
**Current**:
```python
@router.get("/assigned")
async def getAssignedWatches():
    ...
    return JSONResponse(content={
        "success": True,
        "assignedWatches": assignments,
        "count": len(assignments)
    })
```

**After**:
```python
from ...middleware.staff_resolution_middleware import resolve_staff_in_response

@router.get("/assigned")
async def getAssignedWatches():
    async with getDbConnection() as conn:
        query = """..."""
        rows = await conn.fetch(query)

        assignments = []
        for row in rows:
            assignmentDict = dict(row)
            # ... datetime conversion ...
            assignments.append(assignmentDict)

        # STAFF RESOLUTION
        response = {
            "success": True,
            "assignedWatches": assignments,
            "count": len(assignments)
        }

        # Resolve staff IDs (assignedBy → assignedByName, assignedByRole)
        response = await resolve_staff_in_response(response, conn)

        return JSONResponse(content=response)
```

#### Location 2: getWatchConnectionStatus() - Line 250-306
**Same pattern** - Add staff resolution before returning

#### Location 3: getWatchAlerts() - Line 308-375
**Same pattern** - Add staff resolution before returning

### Phase 3: Use current_user for assignedBy/unassignedBy
**File**: `hospital-backend/app/api/v1/watch_management.py`

#### Location 4: assignWatchToPatient() - Line 114-185
**Current**:
```python
@router.post("/assign")
async def assignWatchToPatient(
    assignmentData: dict,
    current_user: dict = Depends(require_medical_staff)
):
    assignedBy = assignmentData.get('assignedBy', 'System')  # ← Wrong
```

**After**:
```python
@router.post("/assign")
async def assignWatchToPatient(
    assignmentData: dict,
    current_user: dict = Depends(require_medical_staff)
):
    # Use authenticated user's ID, not frontend-provided value
    assignedBy = current_user['id']  # ← Correct, from JWT token
```

#### Location 5: unassignWatchFromPatient() - Line 187-248
**Same fix** - Use `current_user['id']` instead of request data

### Phase 4: Add Staff Resolution to device_management.py
**File**: `hospital-backend/app/api/v1/device_management.py`

Need to check this file for similar patterns.

---

## IMPLEMENTATION ORDER

1. ✅ **First**: Verify device pool tests pass (8/8) ← DONE
2. **Second**: Test staff resolution utility with sample data
3. **Third**: Add staff resolution to getAssignedWatches()
4. **Fourth**: Add staff resolution to getWatchConnectionStatus()
5. **Fifth**: Add staff resolution to getWatchAlerts()
6. **Sixth**: Fix assignedBy/unassignedBy to use current_user
7. **Seventh**: Check device_management.py for similar issues
8. **Eighth**: Run comprehensive tests
9. **Ninth**: Create completion report

---

## FILES TO MODIFY

1. `hospital-backend/app/api/v1/watch_management.py` (3-5 changes)
2. `hospital-backend/app/api/v1/device_management.py` (need to audit first)

---

## TESTING PLAN

### Test 1: Staff Resolution Utility
```bash
cd hospital-backend
python test_staff_resolution.py
```
Expected: assignedBy "DOC0001" resolves to "Dr. John Smith"

### Test 2: API Response
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8001/api/v1/watchmanagement/assigned
```
Expected: Response includes `assignedByName` and `assignedByRole`

### Test 3: Security
```bash
# Try to assign watch with fake assignedBy in request body
# Should use JWT token user instead
```
Expected: assignedBy is current user's ID, not request data

---

## ALTERNATIVES CONSIDERED

### Alternative 1: SQL JOIN to staff table
**Pros**: Get staff names in same query
**Cons**:
- Breaks if staff deleted (FK constraint issues)
- More complex queries
- Code duplication across endpoints

### Alternative 2: Frontend resolution
**Pros**: Backend stays simple
**Cons**:
- Frontend needs staff lookup endpoint
- Extra API calls
- Inconsistent across different frontends
- **VIOLATES BACKEND-ONLY LOGIC PRINCIPLE**

### Alternative 3: Use existing staff resolution (RECOMMENDED)
**Pros**:
- ✅ Centralized, tested utility
- ✅ One query for all staff IDs (batch resolution)
- ✅ Consistent across all endpoints
- ✅ Easy to maintain
- ✅ Handles SYSTEM user
- ✅ Graceful fallback for missing staff

**Cons**: None

---

## SUCCESS CRITERIA

✅ All device endpoints return assignedByName and assignedByRole when assignedBy exists
✅ All device endpoints return unassignedByName and unassignedByRole when unassignedBy exists
✅ assignedBy/unassignedBy use authenticated user's ID from JWT, not request data
✅ Device pool tests still pass (8/8)
✅ No breaking changes to existing responses (backward compatible - adds fields, doesn't remove)
✅ Code is clean and uses existing staff resolution utilities

---

## SECURITY IMPLICATIONS

### BEFORE (Insecure):
```python
assignedBy = assignmentData.get('assignedBy', 'System')
```
**Problem**: Frontend can forge assignedBy value, claiming to be any user

### AFTER (Secure):
```python
assignedBy = current_user['id']
```
**Benefit**: assignedBy is ALWAYS the authenticated user from JWT token

---

## BACKWARD COMPATIBILITY

**Adding fields only** - no breaking changes:
- Old clients ignore new `assignedByName` and `assignedByRole` fields
- All existing fields remain unchanged
- Response structure stays the same

---

## NEXT STEPS

**USER DECISION NEEDED**:
1. Should we implement staff resolution for device management endpoints?
2. Should we fix assignedBy/unassignedBy to use JWT token user?
3. Should we audit device_management.py as well?

**READY TO IMPLEMENT** once user confirms the plan.
