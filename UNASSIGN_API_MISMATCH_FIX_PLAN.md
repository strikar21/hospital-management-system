# Unassign API Mismatch - Fix Plan

**Date:** 2025-10-22
**Issue:** Frontend can't unassign device - 400 Bad Request error
**Root Cause:** Frontend/Backend API mismatch - missing `patientId` parameter

---

## Problem Diagnosis

### Frontend Request (DeviceService.ts:163-170)
```typescript
await this.fetchFromBackend(`/watchmanagement/unassign`, {
  method: 'POST',
  body: JSON.stringify({
    deviceId,                     // ✅ Sent
    unassignedBy: staffId,       // ✅ Sent
    reason: unassignmentReason,  // ✅ Sent
    timestamp: new Date().toISOString()
  })
});
```

### Backend Expects (watch_management.py:222-228)
```python
patientId = unassignmentData.get('patientId')  # ❌ NOT SENT by frontend
deviceId = unassignmentData.get('deviceId')     # ✅ Sent
unassignedBy = current_user['id']               # ✅ From JWT token

if not patientId or not deviceId:
    raise HTTPException(status_code=400, detail="Patient ID and Device ID are required")
```

**Error:** Frontend doesn't send `patientId` → Backend returns 400 Bad Request

---

## Two Possible Solutions

###Option A: Make `patientId` Optional in Backend (RECOMMENDED ✅)

**Rationale:**
- Frontend doesn't always have `patientId` when unassigning
- Device ID alone is sufficient - there's only ONE active assignment per device
- Simpler for frontend - no need to track patient ID

**Changes:**
1. Backend looks up `patientId` from deviceassignments table using `deviceId`
2. If no active assignment found, return 404
3. Proceed with unassignment

**Implementation:**
```python
@router.post("/unassign")
async def unassignWatchFromPatient(
    unassignmentData: dict,
    current_user: dict = Depends(require_medical_staff)
):
    deviceId = unassignmentData.get('deviceId')
    patientId = unassignmentData.get('patientId')  # ← Optional
    unassignedBy = current_user['id']
    reason = unassignmentData.get('reason', 'Manual unassignment')

    if not deviceId:
        raise HTTPException(status_code=400, detail="Device ID is required")

    async with getDbConnection() as conn:
        async with conn.transaction():
            # If patientId not provided, look it up from active assignment
            if not patientId:
                assignment = await conn.fetchrow(
                    "SELECT * FROM deviceassignments WHERE \"deviceId\" = $1 AND status = 'active'",
                    deviceId
                )
                if not assignment:
                    raise HTTPException(status_code=404, detail="Active assignment not found for this device")
                patientId = assignment['patientId']
            else:
                # Verify assignment exists
                assignment = await conn.fetchrow(
                    "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND \"deviceId\" = $2 AND status = 'active'",
                    patientId, deviceId
                )
                if not assignment:
                    raise HTTPException(status_code=404, detail="Active assignment not found")

            # ... rest of unassignment logic ...
```

---

### Option B: Fix Frontend to Send `patientId`

**Rationale:**
- More explicit - frontend knows exactly which patient is being unassigned
- Validates assignment before unassigning

**Changes:**
1. Frontend must pass `patientId` to `unassignDevice()`
2. Update all call sites to include patient ID
3. May require fetching assignment details first

**Implementation:**
```typescript
// DeviceService.ts
static async unassignDevice(
  staffId: string,
  deviceId: string,
  patientId: string,  // ← Add parameter
  unassignmentReason: string = 'patientDischarge'
): Promise<boolean> {
  try {
    const response = await this.fetchFromBackend(`/watchmanagement/unassign`, {
      method: 'POST',
      body: JSON.stringify({
        deviceId,
        patientId,  // ← Now included
        unassignedBy: staffId,
        reason: unassignmentReason,
        timestamp: new Date().toISOString()
      })
    });
    return true;
  } catch (error) {
    return false;
  }
}
```

**Problem:** Frontend components don't always have `patientId` readily available when unassigning from device management view.

---

## Recommended Solution: Option A

### Why Option A is Better:

1. **Simpler for Frontend** - No need to track patient ID in device assignment UI
2. **Backwards Compatible** - Still accepts `patientId` if provided
3. **More Flexible** - Works with just device ID (which is always available)
4. **Database Constraint** - Device can only have ONE active assignment, so lookup is safe
5. **No Frontend Changes** - Fix is backend-only

### Implementation Steps:

1. **Modify watch_management.py unassign endpoint**
   - Make `patientId` parameter optional
   - Look up `patientId` from deviceassignments if not provided
   - Add validation that assignment exists

2. **Test with frontend**
   - Unassign device from device management page
   - Verify backend logs show: "✅ Unassigned watch from patient..."
   - Verify device status changes to 'available'

3. **Add MQTT deassignment notification** (bonus improvement)
   - Send MQTT message to ESP32 to clear `isAssigned` flag
   - ESP32 stops sending vitals
   - Clean state management

---

## Code Changes Required

### File: hospital-backend/app/api/v1/watch_management.py

**Current Code (lines 222-228):**
```python
patientId = unassignmentData.get('patientId')
deviceId = unassignmentData.get('deviceId')
unassignedBy = current_user['id']
reason = unassignmentData.get('reason', 'Manual unassignment')

if not patientId or not deviceId:
    raise HTTPException(status_code=400, detail="Patient ID and Device ID are required")
```

**New Code:**
```python
deviceId = unassignmentData.get('deviceId')
patientId = unassignmentData.get('patientId')  # Optional
unassignedBy = current_user['id']
reason = unassignmentData.get('reason', 'Manual unassignment')

if not deviceId:
    raise HTTPException(status_code=400, detail="Device ID is required")
```

**Current Code (lines 230-238):**
```python
async with getDbConnection() as conn:
    async with conn.transaction():
        # Verify assignment exists
        assignment = await conn.fetchrow(
            "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND \"deviceId\" = $2 AND status = 'active'",
            patientId, deviceId
        )
        if not assignment:
            raise HTTPException(status_code=404, detail="Active assignment not found")
```

**New Code:**
```python
async with getDbConnection() as conn:
    async with conn.transaction():
        # If patientId not provided, look it up from device assignment
        if not patientId:
            assignment = await conn.fetchrow(
                "SELECT * FROM deviceassignments WHERE \"deviceId\" = $1 AND status = 'active'",
                deviceId
            )
            if not assignment:
                raise HTTPException(status_code=404, detail="No active assignment found for this device")
            patientId = assignment['patientId']
            logger.info(f"🔍 Looked up patientId {patientId} for device {deviceId}")
        else:
            # Verify assignment exists when patientId is provided
            assignment = await conn.fetchrow(
                "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND \"deviceId\" = $2 AND status = 'active'",
                patientId, deviceId
            )
            if not assignment:
                raise HTTPException(status_code=404, detail="Active assignment not found")
```

---

## Testing Plan

### Test 1: Unassign Without Patient ID (Frontend Current Behavior)
```json
POST /api/v1/watchmanagement/unassign
{
  "deviceId": "fit-00001",
  "unassignedBy": "NUR0001",
  "reason": "Manual unassignment"
}
```

**Expected:**
- ✅ Backend looks up patient ID from deviceassignments
- ✅ Backend logs: "🔍 Looked up patientId TEST001 for device fit-00001"
- ✅ Unassignment succeeds
- ✅ Device status → 'available'
- ✅ Assignment status → 'inactive'

### Test 2: Unassign With Patient ID (Explicit)
```json
POST /api/v1/watchmanagement/unassign
{
  "deviceId": "fit-00001",
  "patientId": "TEST001",
  "unassignedBy": "NUR0001",
  "reason": "Patient discharge"
}
```

**Expected:**
- ✅ Backend uses provided patient ID
- ✅ Backend verifies assignment exists
- ✅ Unassignment succeeds
- ✅ Device status → 'available'

### Test 3: Unassign Non-Existent Assignment
```json
POST /api/v1/watchmanagement/unassign
{
  "deviceId": "NONEXISTENT",
  "reason": "Test"
}
```

**Expected:**
- ❌ 404 error: "No active assignment found for this device"

---

## Bonus: Add MQTT Deassignment Notification

After unassigning, send MQTT message to ESP32 to clear assignment state:

### Backend Addition (mqtt_service.py)
```python
async def publishDeassignment(self, deviceId: str) -> bool:
    """
    Send deassignment notification to ESP32 watch via MQTT
    Clears patient assignment and stops vitals transmission
    """
    if not self.client or not self.connected:
        logger.warning("⚠️ MQTT not connected - cannot send deassignment")
        return False

    topic = f"hospital/devices/{deviceId}/unassign"
    payload = json.dumps({
        "command": "unassign",
        "timestamp": datetime.now().isoformat()
    })

    try:
        result = self.client.publish(topic, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"📤 Deassignment notification sent to {deviceId}")
            return True
        else:
            logger.error(f"❌ Failed to send deassignment to {deviceId}")
            return False
    except Exception as e:
        logger.error(f"❌ MQTT publish error: {e}")
        return False
```

### Call from watch_management.py (after line 255)
```python
# Send MQTT deassignment notification to ESP32 device
mqttSuccess = await mqttService.publishDeassignment(deviceId)
if not mqttSuccess:
    logger.warning(f"⚠️ MQTT deassignment notification failed for {deviceId}")
```

### ESP32 Handler (esp32_hospital_watch_complete.ino)
```arduino
if (String(topic).endsWith("/unassign")) {
    assignedPatientId = "";
    isAssigned = false;
    saveConfiguration();
    Serial.println("👋 Unassigned from patient");
}
```

---

## Files to Modify

1. **[hospital-backend/app/api/v1/watch_management.py](hospital-backend/app/api/v1/watch_management.py#L222-L238)**
   - Make `patientId` optional
   - Add lookup logic if not provided
   - Add MQTT deassignment notification (optional)

2. **[hospital-backend/app/services/mqtt_service.py](hospital-backend/app/services/mqtt_service.py)** (Optional)
   - Add `publishDeassignment()` function

3. **[esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino)** (Optional)
   - Add `/unassign` topic handler

---

## Alternative Considered: Frontend Fix

**Not Recommended Because:**
- Requires changes to multiple frontend components
- Frontend doesn't always have patient ID readily available
- More complex - need to fetch assignment details first
- Backend should be flexible enough to handle this

---

## Deployment Impact

- ✅ **Backend-only change** - No frontend rebuild required
- ✅ **Backwards compatible** - Still accepts `patientId` if provided
- ✅ **No database changes** - Uses existing tables
- ✅ **Low risk** - Only affects unassign endpoint

---

## Success Criteria

After implementation:
- [ ] Frontend can unassign device without providing patient ID
- [ ] Backend looks up patient ID from deviceassignments table
- [ ] Device status changes to 'available'
- [ ] Assignment status changes to 'inactive'
- [ ] Backend logs show successful unassignment
- [ ] No 400 errors in frontend console
- [ ] (Optional) ESP32 receives deassignment notification and clears state

---

**Status:** ✅ Root cause identified, solution designed
**Recommendation:** Implement Option A (make patientId optional in backend)
**Priority:** HIGH - Blocks device reassignment workflow
