# Watch Features - Remaining Issues & Solutions

**Date**: 2025-10-15
**Status**: Analysis Complete, Implementation Pending

---

## Issue 1: No Watch Details in Patient Detail View ⏳

### Problem
When viewing a patient's detail page, there is no section showing their assigned watch information.

### Current State
**PatientOverview.tsx** (lines 30-49) shows:
- Patient demographics
- Room/Ward/Department
- Assigned Doctor
- ❌ **Missing: Assigned Watch Details**

### Proposed Solution

Add a "Device & Monitoring" section in PatientOverview.tsx:

```tsx
{/* Device & Monitoring Section */}
{patient.assignedDeviceId && (
  <div className="bg-blue-50 rounded-lg p-3 mb-2 flex-shrink-0">
    <h3 className="text-sm font-semibold text-blue-800 mb-2">📟 Assigned Watch</h3>
    <div className="grid grid-cols-4 gap-3 text-xs">
      <div>
        <span className="font-medium text-gray-600">Device ID:</span> {patient.assignedDeviceId}
      </div>
      <div>
        <span className="font-medium text-gray-600">Status:</span>
        <span className={`ml-1 px-2 py-0.5 rounded ${
          patient.deviceStatus === 'connected'
            ? 'bg-green-100 text-green-800'
            : 'bg-amber-100 text-amber-800'
        }`}>
          {patient.deviceStatus === 'connected' ? 'Connected' : 'Disconnected'}
        </span>
      </div>
      <div>
        <span className="font-medium text-gray-600">Battery:</span> {patient.deviceBatteryLevel}%
      </div>
      <div>
        <span className="font-medium text-gray-600">Last Seen:</span>
        {patient.deviceLastSeen ? new Date(patient.deviceLastSeen).toLocaleTimeString() : '--'}
      </div>
    </div>
  </div>
)}
```

### Implementation Steps
1. Add watch details section to PatientOverview.tsx
2. Use existing patient.assignedDeviceId, patient.deviceStatus fields
3. Format timestamps for better readability
4. Add click-to-view-more functionality (optional)

---

## Issue 2: Can't View More Watch Details from Dashboard ⏳

### Problem
From the dashboard patient card, users cannot:
- Click to see full watch details
- View connection history
- See device specifications

### Current State
**PatientCardHeader.tsx** (lines 47-64) shows:
- Small watch icon + status dot
- Connection status text
- ❌ **No way to view more details**

### Proposed Solution Option 1: Watch Icon Click Handler

Add click handler to watch icon to open watch details modal:

```tsx
{patient.assignedDeviceId && (
  <div
    className="flex items-center space-x-1 cursor-pointer hover:bg-gray-100 rounded p-1"
    title="Click for watch details"
    onClick={(e) => {
      e.stopPropagation();
      onViewWatchDetails(patient);
    }}
  >
    <Watch className={`w-3 h-3 ${patient.deviceStatus === 'connected' ? 'text-green-600' : 'text-amber-600'}`} />
    <div className={`w-2 h-2 rounded-full ${patient.deviceStatus === 'connected' ? 'bg-green-500' : 'bg-amber-500'}`}></div>
  </div>
)}
```

### Proposed Solution Option 2: Watch Details Modal Component

Create new component: `WatchDetailsModal.tsx`

**Shows:**
- Device ID, Serial Number
- Connection Status (with history)
- Battery Level (with chart)
- Last Heartbeat timestamp
- Assigned At, Assigned By
- Patient information
- Recent Vitals received from this watch
- Button: "Unassign Watch" or "Reassign to Different Patient"

### Implementation Steps
1. Create WatchDetailsModal component
2. Add onViewWatchDetails prop to PatientCard components
3. Make watch icon clickable
4. Fetch full device details from backend
5. Display in modal overlay

### Backend API Needed
```
GET /api/v1/watchmanagement/{deviceId}/details
```

Returns:
```json
{
  "deviceId": "ESP32_WATCH_003",
  "serialNumber": "SN_W003",
  "status": "assigned",
  "connectionStatus": "connected",
  "batteryLevel": 20,
  "lastSeen": "2025-10-15T02:39:29.925351Z",
  "assignedToPatient": {
    "id": "081a5294...",
    "name": "Thomas Brown",
    "room": "ICU-101",
    "bed": "B1"
  },
  "assignmentInfo": {
    "assignedAt": "2025-10-14T17:16:25.656015Z",
    "assignedBy": "NUR0001",
    "assignedByName": "Emily Rodriguez"
  },
  "connectionHistory": [
    {"timestamp": "2025-10-15T02:39:29Z", "event": "heartbeat"},
    {"timestamp": "2025-10-15T02:39:00Z", "event": "heartbeat"}
  ]
}
```

---

## Issue 3: Device Reassignment Shows "Bad Request" ❌

### Problem
**Error Message**: "Patient already has a watch assigned"

When trying to reassign a watch to a different patient, the backend rejects the request because:
- Patient already has Watch A assigned
- User tries to assign Watch B
- Backend checks if patient has **any** watch
- Rejects with 400 Bad Request

### Root Cause

**File**: [hospital-backend/app/api/v1/watch_management.py:148-154](hospital-backend/app/api/v1/watch_management.py#L148-L154)

```python
# Check if patient already has a watch assigned
existingAssignment = await conn.fetchrow(
    "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND status = 'active'",
    patientId
)
if existingAssignment:
    raise HTTPException(status_code=400, detail="Patient already has a watch assigned")
```

This **prevents reassignment** entirely!

### User Workflow (Current - Tedious)
1. Unassign Watch A from Patient 1
2. Assign Watch B to Patient 1
3. **Extra steps required!**

### Proposed Solutions

#### Solution A: Auto-Unassign on Reassignment (Recommended)

Modify `assignWatchToPatient` to automatically unassign existing watch:

```python
# Check if patient already has a watch assigned
existingAssignment = await conn.fetchrow(
    "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND status = 'active'",
    patientId
)

if existingAssignment:
    # AUTO-UNASSIGN: Mark old watch as inactive
    await conn.execute("""
        UPDATE deviceassignments
        SET status = 'inactive',
            "unassignedAt" = $1,
            "unassignedBy" = $2,
            "unassignmentReason" = 'Auto-unassigned for reassignment'
        WHERE \"patientId\" = $3 AND status = 'active'
    """, now, assignedBy, patientId)

    # Update old device status to available
    await conn.execute(
        "UPDATE devices SET status = 'available', \"updatedAt\" = $1 WHERE id = $2",
        now, existingAssignment['deviceId']
    )

    logger.info(f"🔄 Auto-unassigned existing watch {existingAssignment['deviceId']} for reassignment")

# Continue with new assignment...
```

**Pros**:
- Seamless user experience
- Single API call
- Audit trail preserved (both unassignment and new assignment recorded)

**Cons**:
- Less explicit (user might not realize old watch was unassigned)

#### Solution B: Add Explicit Reassign Endpoint

Create new endpoint: `POST /api/v1/watchmanagement/reassign`

```python
@router.post("/reassign")
async def reassignWatch(
    reassignmentData: dict,
    current_user: dict = Depends(require_medical_staff)
):
    """
    Reassign a watch - unassigns existing watch and assigns new one atomically
    """
    patientId = reassignmentData.get('patientId')
    newDeviceId = reassignmentData.get('deviceId')
    reason = reassignmentData.get('reason', 'Watch reassignment')

    async with conn.transaction():
        # Unassign existing watch
        await unassign_current_watch(patientId, current_user['id'], reason)

        # Assign new watch
        await assign_new_watch(patientId, newDeviceId, current_user['id'])
```

**Pros**:
- Explicit intent
- Clear API semantics
- Atomic transaction

**Cons**:
- Additional endpoint to maintain
- Frontend needs to detect and call different endpoint

#### Solution C: Frontend Handle (Not Recommended)

Frontend detects existing assignment and calls unassign + assign sequentially.

**Cons**:
- Two API calls (not atomic)
- Race conditions possible
- More complex frontend logic

### Recommended Approach

**Solution A: Auto-Unassign on Reassignment**

**Why?**
- Best user experience (just click "Assign" and it works)
- All logic in one place (backend)
- Atomic transaction (database ACID guarantees)
- Audit trail complete (both unassign and assign logged)

**Implementation**:
1. Modify watch_management.py assign endpoint
2. When existing assignment found, unassign it first
3. Log both actions
4. Continue with new assignment
5. Test with database transactions

---

## Implementation Priority

### High Priority (Fix First)
1. ✅ **Device Reassignment** - Users are blocked from reassigning watches
   - Impact: Cannot change patient's watch
   - Solution: Auto-unassign on reassignment
   - Effort: 1 hour

### Medium Priority
2. ⏳ **Watch Details in Patient View** - Users can't see device info
   - Impact: Limited visibility into patient's watch
   - Solution: Add device section to PatientOverview
   - Effort: 2 hours

### Lower Priority (Nice to Have)
3. ⏳ **Watch Details Modal from Dashboard** - Users can't deep-dive
   - Impact: No detailed device information accessible
   - Solution: Create WatchDetailsModal component
   - Effort: 4 hours

---

## Testing Checklist

### Device Reassignment
- [ ] Patient with Watch A, assign Watch B → succeeds
- [ ] Watch A status becomes 'available'
- [ ] Watch B status becomes 'assigned'
- [ ] Device assignments table shows 2 records: old (inactive), new (active)
- [ ] Unassignment reason: "Auto-unassigned for reassignment"
- [ ] assignedBy and unassignedBy properly logged

### Watch Details in Patient View
- [ ] Patient with watch shows device section
- [ ] Connection status displays correctly (green/amber)
- [ ] Battery level shows correct percentage
- [ ] Last seen timestamp formatted properly
- [ ] Patient without watch - section hidden

### Watch Details Modal
- [ ] Click watch icon opens modal
- [ ] Modal shows complete device information
- [ ] Connection history loads
- [ ] Unassign/Reassign buttons work
- [ ] Modal closes properly

---

## Files to Modify

### Issue 3: Device Reassignment
1. **hospital-backend/app/api/v1/watch_management.py**
   - Modify: `assignWatchToPatient` function (lines 118-183)
   - Change: Auto-unassign existing watch before new assignment

### Issue 1: Watch Details in Patient View
1. **hospital-display-app/src/components/PatientDetail/PatientOverview.tsx**
   - Add: Device & Monitoring section after Patient Information
   - Lines: After line 49

### Issue 2: Watch Details Modal
1. **hospital-display-app/src/components/WatchDetails/** (new directory)
   - Create: `WatchDetailsModal.tsx`
   - Create: `WatchConnectionHistory.tsx`
   - Create: `WatchBatteryChart.tsx`

2. **hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx**
   - Modify: Add click handler to watch icon
   - Add: onViewWatchDetails prop

3. **hospital-backend/app/api/v1/watch_management.py**
   - Add: GET endpoint for device details by ID

---

## Decision Required

**Which issue should we fix first?**

My recommendation: **Issue 3 (Device Reassignment)** because:
- Users are blocked from basic functionality
- Quickest fix (1 hour)
- Backend-only change
- No frontend modifications needed

**Should we proceed with fixing device reassignment?**
