# Unassign Bug Fix - Complete Implementation

## Problem Summary
Frontend received **400 Bad Request: "Device ID is required"** when attempting to unassign devices from patients.

## Root Cause (Evidence-Based)
V2 Devices API returned device field as `id` instead of `deviceId`, causing frontend to pass `undefined` to the unassign endpoint.

### Data Flow Analysis
1. **V2 API returned** (verified with database query):
   ```json
   { "id": "ESP32_WATCH_003", ... }  // NO deviceId field
   ```

2. **Frontend TypeScript interface expected**:
   ```typescript
   interface DeviceAssignmentRecord {
     deviceId: string;  // ← Expected but not provided!
   }
   ```

3. **Frontend called unassign**:
   ```typescript
   onUnassign(assignment.deviceId, ...)  // deviceId was undefined
   ```

4. **Backend received**:
   ```python
   deviceId = unassignmentData.get('deviceId')  # Got None/undefined
   if not deviceId:
       raise HTTPException(400, "Device ID is required")  # ← ERROR!
   ```

## Solution Implemented

**Added `deviceId` alias in V2 Devices API** while maintaining backwards compatibility.

### Files Modified

**hospital-backend/app/api/v2/devices.py**

#### Change 1: Main device query (Line 110)
```python
# BEFORE:
SELECT
    id,
    "deviceType",
    ...

# AFTER:
SELECT
    id AS "deviceId",  # Alias for camelCase consistency
    id,                # Keep for backwards compatibility
    "deviceType",
    ...
```

#### Change 2: Single device query (Line 196)
```python
# Same aliasing pattern
SELECT
    id AS "deviceId",
    id,
    ...
```

#### Change 3: Available watches endpoint (Line 305)
```python
SELECT id AS "deviceId", *
FROM devices_enriched
WHERE "deviceType" = 'watch' AND status = 'available'
```

#### Change 4: Assigned devices endpoint (Line 334)
```python
SELECT id AS "deviceId", *
FROM devices_enriched
WHERE "assignmentStatus" = 'active'
```

#### Change 5: Low battery devices endpoint (Line 363)
```python
SELECT id AS "deviceId", *
FROM devices_enriched
WHERE "batteryLevel" < 20
```

## Why This Solution?

### ✅ Pros
1. **Fixes root cause** - V2 API now returns camelCase `deviceId`
2. **System-wide consistency** - All parts use camelCase naming
3. **Backwards compatible** - Returns both `id` and `deviceId`
4. **No frontend changes needed** - Works immediately
5. **Future-proof** - Other components won't have this issue

### Considered Alternatives

**Option B: Map `id` to `deviceId` in frontend**
- ❌ Doesn't fix root cause (V2 API still inconsistent)
- ❌ Band-aid solution - may break elsewhere
- ❌ Would need mapping in multiple places

## Testing

Backend restarted successfully (PID: 19444):
- ✅ V2 Devices API registered successfully
- ✅ Watch management router registered successfully
- ✅ MQTT service started successfully
- ✅ ESP32 watch fit-00001 sending heartbeats

### Test Steps

1. Login to frontend as NUR0001 (PIN: 5678)
2. Navigate to: **Device Assignment → Assigned Devices tab**
3. Click **Unassign** button on any assigned device
4. **Expected Result**:
   - ✅ Success message appears
   - ✅ No 400 error in console
   - ✅ Backend logs show:
     ```
     🔍 Looked up patientId=... for deviceId=...
     📤 Deassignment notification sent to ...
     ```

### V2 API Response Structure (Now)

```json
{
  "devices": [
    {
      "deviceId": "ESP32_WATCH_003",  // ← NEW: camelCase alias
      "id": "ESP32_WATCH_003",        // ← OLD: backwards compatible
      "deviceType": "watch",
      "assignmentId": 4,
      "assignedPatientId": "081a5294-...",
      "patientName": "Thomas Brown",
      ...
    }
  ]
}
```

## Verification Checklist

- [x] V2 API returns `deviceId` field
- [x] V2 API returns `id` field (backwards compatibility)
- [x] Backend started successfully with changes
- [x] No syntax errors in modified files
- [ ] Unassign functionality works without 400 error (awaiting user test)
- [ ] Device assignment still works (regression test)
- [ ] Device pool tab still loads (regression test)

## Impact Analysis

### Code Using `device.id` (Backwards Compatible)
- NurseAdmissionProcessing.tsx
- DeviceSelectionPanel.tsx
- DeviceCard.tsx

These components will continue working because we kept the `id` field.

### Code Using `device.deviceId` (Now Works)
- AssignedDevicesTab.tsx (unassign functionality)
- Any future components following camelCase standard

## Next Steps

1. User tests unassign functionality
2. If successful, verify:
   - MQTT deassignment notification sent to ESP32
   - ESP32 stops sending vitals after unassignment
   - Device returns to available pool
3. Mark all remaining todos as complete

## Summary

**Fix Type**: Root cause fix (not workaround)
**Risk Level**: LOW (backwards compatible)
**Lines Changed**: 5 SELECT statements in one file
**Testing**: Backend running, awaiting user verification
**Deployment**: Ready for testing
