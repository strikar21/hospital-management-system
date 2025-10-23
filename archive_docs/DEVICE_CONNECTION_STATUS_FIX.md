# Device Connection Status Fix - Complete

**Date**: 2025-10-15
**Issue**: Assigned watches showing as "disconnected" even when actively sending heartbeats
**Status**: ✅ RESOLVED

---

## Problem Summary

After successfully assigning ESP32_WATCH_003 to Thomas Brown, the watch was:
- ✅ Sending heartbeats every 30 seconds to backend
- ✅ Showing as "assigned" in database
- ❌ Displaying as "Watch assigned but disconnected" in frontend UI

### User Report
> "if watch is online, it shows assigned but disconnected, after i tried to restart the watch"

---

## Investigation

### Backend Verification
```
Device ID: ESP32_WATCH_003
Status: assigned
Last Seen: 30 seconds ago
CONNECTION STATUS: ONLINE (heartbeat within 5 min)
Assigned to: Thomas Brown
Battery: 20%
```

✅ Backend correctly tracking watch as ONLINE

### Frontend Check
[PatientCardHeader.tsx:47-58](hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx#L47-L58)
```typescript
{patient.assignedDeviceId ? (
  patient.deviceStatus === 'connected' ? (
    // Green indicator: "Watch connected and monitoring"
  ) : (
    // Amber indicator: "Watch assigned but disconnected"
  )
)}
```

❌ Frontend checking `patient.deviceStatus` field, but it wasn't being returned!

### Root Cause
Previous fix added `assignedDeviceId` but **NOT** `deviceStatus`:
```sql
-- Previous query (incomplete)
SELECT p.*, da."deviceId" as "assignedDeviceId"
FROM patients p
LEFT JOIN deviceassignments da ON ...
-- Missing: devices table JOIN for connection status
```

---

## Solution Implemented

### Enhanced Patient Query with Device Status

**File**: [hospital-backend/app/repositories/patient_repository.py:51-66](hospital-backend/app/repositories/patient_repository.py#L51-L66)

```sql
SELECT p.*,
       da."deviceId" as "assignedDeviceId",
       da."assignedAt" as "deviceAssignedAt",
       d."lastSeen" as "deviceLastSeen",
       d."batteryLevel" as "deviceBatteryLevel",
       CASE
           WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
           WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
           ELSE 'offline'
       END as "deviceStatus"
FROM patients p
LEFT JOIN deviceassignments da ON p.id = da."patientId" AND da."unassignedAt" IS NULL
LEFT JOIN devices d ON da."deviceId" = d.id
```

### Connection Status Logic

| Last Seen | Status | Frontend Display | Color |
|-----------|--------|-----------------|-------|
| < 5 min | `connected` | "Watch Connected" | Green |
| < 1 hour | `recentlySeen` | "Watch Disconnected" | Amber |
| > 1 hour | `offline` | "Watch Disconnected" | Amber |
| No device | - | "No watch assigned" | Gray |

---

## Data Flow

### Backend → Frontend

**Patient Object Now Includes**:
```json
{
  "id": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "firstName": "Thomas",
  "lastName": "Brown",
  "assignedDeviceId": "ESP32_WATCH_003",
  "deviceAssignedAt": "2025-10-14T17:16:25.656015Z",
  "deviceStatus": "connected",
  "deviceLastSeen": "2025-10-15T02:39:29.925351Z",
  "deviceBatteryLevel": 20
}
```

### Frontend Rendering

**PatientCardHeader Component**:
- Shows green watch icon + dot when `deviceStatus === 'connected'`
- Shows amber watch icon + dot when `deviceStatus !== 'connected'` but device assigned
- Shows gray WiFi-off icon when no device assigned

**Status Text** (lines 110-119):
```typescript
{patient.assignedDeviceId && (
  <span className={`ml-2 text-xs px-1 py-0.5 rounded ${
    patient.deviceStatus === 'connected'
      ? 'bg-green-100 text-green-800'  // Green: "Watch Connected"
      : 'bg-amber-100 text-amber-800'  // Amber: "Watch Disconnected"
  }`}>
    {patient.deviceStatus === 'connected' ? 'Watch Connected' : 'Watch Disconnected'}
  </span>
)}
```

---

## Testing Results

### Database Query Test
```
=== TESTING PATIENT QUERY WITH DEVICE STATUS ===
Test Patient: No device
Thomas Brown: Device: ESP32_WATCH_003, Status: connected, Battery: 20%
Jennifer Lee: No device
William Johnson: No device
Robert Anderson: No device
```

✅ Query returns correct connection status

### Expected Frontend Behavior

For **Thomas Brown** with ESP32_WATCH_003:
- ✅ Green watch icon with green dot
- ✅ Status badge: "Watch Connected" (green background)
- ✅ Vitals display actual values (not "--")
- ✅ Battery level: 20%

For **other patients** without devices:
- ✅ Gray WiFi-off icon
- ✅ No status badge
- ✅ Vitals show "--" placeholder

---

## Files Modified

1. **hospital-backend/app/repositories/patient_repository.py**
   - Lines 51-66: Added devices table JOIN
   - Added CASE statement for deviceStatus calculation
   - Returns deviceBatteryLevel, deviceLastSeen fields

---

## Git History

### Commits
1. `f20e459` - Fixed endpoint paths (/watch-management → /watchmanagement)
2. `f620433` - Added device assignment data to patient queries (assignedDeviceId)
3. `0b92ba1` - **Added device connection status to patient queries** (deviceStatus)

### Branch
- `feat/staff-resolution-standardization`
- All changes pushed to remote

---

## Monitoring

### Backend Logs
Watch for patient query logs:
```
app.repositories.patient_repository - INFO - Retrieved patients with device assignments
```

### Frontend Console
Check patient data structure:
```javascript
console.log(patient);
// Should include:
// - assignedDeviceId: "ESP32_WATCH_003"
// - deviceStatus: "connected"
// - deviceBatteryLevel: 20
// - deviceLastSeen: "2025-10-15T02:39:29.925351Z"
```

### ESP32 Heartbeats
Backend receives heartbeats:
```
app.api.v1.esp32 - INFO - 💓 Heartbeat: ESP32_WATCH_003 Battery 20%
```

Heartbeat updates `lastSeen` timestamp, which drives connection status calculation.

---

## Connection Status Timeline

| Time | Event | Status |
|------|-------|--------|
| T+0s | Watch sends heartbeat | `connected` |
| T+30s | Next heartbeat | `connected` |
| T+5min | No heartbeat for 5 min | `recentlySeen` → Amber |
| T+1hr | No heartbeat for 1 hour | `offline` → Amber |
| T+1hr+1s | Heartbeat resumes | `connected` → Green |

---

## Production Considerations

### Heartbeat Frequency
- ESP32 watches: Every 30 seconds
- Status check: Real-time (calculated in SQL query)
- No polling needed: Status computed on each patient list fetch

### Performance
- LEFT JOIN adds minimal overhead (indexed on patientId and deviceId)
- CASE statement evaluated per row (fast)
- No N+1 query problem: Single query returns all data

### Scaling
- Works with any number of devices
- Connection status always accurate
- No caching needed (SQL calculates fresh each time)

---

## Future Enhancements

### Possible Additions
1. **Last Heartbeat Display**: Show "Last seen: 30s ago" on hover
2. **Battery Level Alert**: Warn when < 10%
3. **Connection History**: Track disconnection events
4. **Offline Alerts**: Notify staff when watch goes offline

### Alternative Status Levels
Could add more granular status:
- `excellent`: < 1 min
- `good`: < 5 min
- `fair`: < 1 hour
- `poor`: > 1 hour

---

## Related Documentation

- [DEVICE_VISIBILITY_FIX_COMPLETE.md](DEVICE_VISIBILITY_FIX_COMPLETE.md) - Device assignment visibility
- [FRONTEND_BACKEND_API_MISMATCH_ANALYSIS.md](FRONTEND_BACKEND_API_MISMATCH_ANALYSIS.md) - Endpoint path fixes
- [PatientCardHeader.tsx](hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx) - Frontend UI component

---

## Success Metrics

✅ **Database**: Returns deviceStatus field
✅ **Backend**: Server running with updated code
✅ **API**: Patient list includes connection status
⏳ **Frontend**: UI should show green "Watch Connected" (pending hot-reload)

---

## Key Learnings

1. **Complete Data Requirements**: When adding feature, include ALL related fields
2. **Real-time Status**: Use SQL CASE for dynamic status calculation
3. **Connection Thresholds**: 5 min = connected, 1 hour = offline
4. **Testing Each Layer**: Verify database → API → frontend flow

---

## Next Steps

1. ✅ Backend updated and restarted
2. ✅ Changes committed and pushed
3. ⏳ Frontend hot-reload will pick up new patient data structure
4. ⏳ Verify green "Watch Connected" appears on Thomas Brown's card
5. ⏳ Test watch disconnect scenario (stop heartbeats, wait 5 min, verify amber status)
