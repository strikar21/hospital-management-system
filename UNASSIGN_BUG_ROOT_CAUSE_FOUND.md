# Unassign Bug - Root Cause Found

## Problem Summary
Frontend gets 400 Bad Request error: "Device ID is required" when trying to unassign devices.

## Root Cause Analysis

### Data Flow
1. **Frontend loads assigned devices** (DeviceAssignment.tsx:128)
   ```typescript
   const assignedData = await DeviceService.getAssignmentHistory(currentUser.staffId);
   ```

2. **DeviceService.getAssignmentHistory()** calls V2 API (DeviceService.ts:70)
   ```typescript
   const response = await this.fetchFromBackend(`/v2/devices/?${params.toString()}`);
   return response?.devices || [];
   ```

3. **V2 API returns devices** (devices.py:110-143)
   ```python
   SELECT
       id,                    # ❌ SHOULD BE deviceId
       "deviceType",
       name,
       ...
   ```

4. **Frontend tries to unassign** (AssignedDevicesTab.tsx:35)
   ```typescript
   onUnassign(assignment.deviceId, 'manual_unassignment');
   ```

5. **assignment.deviceId is UNDEFINED** because V2 API returned `id`, not `deviceId`

6. **Backend receives undefined deviceId** (watch_management.py:222)
   ```python
   deviceId = unassignmentData.get('deviceId')  # Gets None/undefined
   if not deviceId:
       raise HTTPException(status_code=400, detail="Device ID is required")
   ```

## The Bug

**V2 devices API returns `id` instead of `deviceId`** - violating camelCase naming standard and breaking frontend expectations.

### Evidence

**Backend V2 API (devices.py:110):**
```python
SELECT
    id,  # ❌ WRONG - should be deviceId or aliased as deviceId
    ...
```

**Frontend expects (AssignedDevicesTab.tsx:6):**
```typescript
interface DeviceAssignmentRecord {
  id: number;           // Assignment ID
  deviceId: string;     // ✅ Device ID - but V2 API doesn't provide this!
  ...
}
```

**Backend receives (watch_management.py:222):**
```python
deviceId = unassignmentData.get('deviceId')  # None/undefined
```

## Solution Options

### Option A: Add deviceId Alias in V2 API (RECOMMENDED)
**Why**: Maintains camelCase consistency across entire system

**Change**: hospital-backend/app/api/v2/devices.py:110
```python
SELECT
    id AS "deviceId",  # Primary fix - alias id as deviceId
    id,                # Keep id for backwards compatibility
    "deviceType",
    ...
```

**Pros**:
- ✅ Follows camelCase standard everywhere
- ✅ Frontend code works without changes
- ✅ Backwards compatible (keeps both `id` and `deviceId`)
- ✅ Consistent with rest of system

**Cons**:
- Data duplication (minor - just in JSON response)

### Option B: Update Frontend to Use `id`
**Why**: Match what V2 API currently returns

**Change**: hospital-display-app/src/DeviceAssignment.tsx:129-134
```typescript
const assignedWithPatients = (assignedData || []).map((assignment: deviceAssignmentRecord) => ({
  ...assignment,
  deviceId: assignment.id,  // Map id to deviceId
  ...
}));
```

**Pros**:
- ✅ No backend changes needed

**Cons**:
- ❌ Doesn't fix root cause (inconsistent naming)
- ❌ Workaround rather than proper fix
- ❌ May break again if other code expects deviceId

## Recommended Fix

**Option A** - Add `deviceId` alias in V2 API

This fixes the root cause and maintains naming consistency across the entire system.

## Implementation Plan

1. ✅ Update V2 devices API to return both `id` and `deviceId` (aliased)
2. ✅ Test unassign functionality
3. ✅ Verify vitals start flowing after assignment fix

## Files to Modify

1. **hospital-backend/app/api/v2/devices.py**
   - Line 110: Change `id,` to `id AS "deviceId", id,`
   - Line 195: Change `id,` to `id AS "deviceId", id,`

## Testing

After fix:
1. Login to frontend as NUR0001
2. Navigate to Device Assignment → Assigned Devices tab
3. Click unassign button on fit-00001
4. Should see success message
5. Backend logs should show:
   - `🔍 Looked up patientId=TEST001 for deviceId=fit-00001`
   - `📤 Deassignment notification sent to fit-00001`
   - No 400 error
