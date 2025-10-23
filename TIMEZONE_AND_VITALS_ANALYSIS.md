# Timezone and Vitals Data Analysis

**Date:** 2025-10-22
**Issues:**
1. `lastSeen` timestamp in GMT not local timezone
2. Are vitals data coming through?

---

## Issue 1: Timestamp Timezone (GMT vs Local)

### Current Implementation

**Heartbeat Handler:** [mqtt_service.py:717](hospital-backend/app/services/mqtt_service.py#L717)
```python
await conn.execute("""
    UPDATE devices
    SET "lastSeen" = NOW(), "batteryLevel" = $2,
        status = CASE WHEN status = 'offline' THEN 'available' ELSE status END,
        "updatedAt" = NOW()
    WHERE id = $1
""", deviceId, batteryLevel)
```

**`NOW()` Function:** PostgreSQL's `NOW()` returns **UTC timestamp** (GMT+0)

### Evidence

```sql
SELECT id, status, "lastSeen", "batteryLevel" FROM devices WHERE id = 'fit-00001';
-- Result: lastSeen=2025-10-22 15:47:52.281802+00:00 (UTC timezone, +00:00)
```

### Is This Correct?

**YES - This is correct and follows best practices!**

**Why UTC is correct:**
1. ✅ **Database Best Practice:** Always store timestamps in UTC
2. ✅ **Timezone Independence:** Works globally regardless of server location
3. ✅ **No DST Issues:** UTC never changes for daylight saving time
4. ✅ **Frontend Conversion:** Frontend should convert to local timezone for display

### What The Frontend Should Do

**Current Backend:** Stores UTC timestamps
**Frontend Should:** Convert to user's local timezone for display

```javascript
// Example frontend conversion:
const lastSeenUTC = "2025-10-22T15:47:52.281802Z"; // From backend
const lastSeenLocal = new Date(lastSeenUTC).toLocaleString(); // Converts to local
// Result: "10/22/2025, 8:47:52 PM" (if user is in IST GMT+5:30)
```

### Recommendation

**NO CHANGES NEEDED** - The backend is doing it correctly. If frontend is showing GMT time, that's a frontend display issue, not a backend issue.

---

## Issue 2: Are Vitals Data Coming Through?

### Current Status

**Heartbeats:** ✅ Working (we see `💓 MQTT Heartbeat: fit-00001 Battery 100% Signal -56dBm`)

**Vitals:** ❓ Unknown - Need to verify

### ESP32 Firmware Check

The ESP32 watch needs to send vitals on topic: `hospital/devices/fit-00001/vitals`

**Current ESP32 behavior:**
- ✅ Sends heartbeat every 30 seconds
- ❓ Does it send vitals? (Need to check firmware)

### Backend Vitals Handler

**Location:** [mqtt_service.py:350-500](hospital-backend/app/services/mqtt_service.py#L350-L500)

```python
async def _handleVitalsMessageNew(self, deviceId: str, payload: Dict[str, Any]):
    """Handle 8-channel vitals data from ESP32 watch"""
    try:
        # Parse and validate using Pydantic model
        try:
            vitalsMsg = VitalsRealtimeMessage(**payload)
        except Exception as e:
            logger.error(f"❌ Invalid vitals message from {deviceId}: {e}")
            return

        patientId = vitalsMsg.patientId

        # Validate device assignment
        async with getDbConnection() as conn:
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1", patientId)
            if not patient:
                logger.warning(f"⚠️ Patient {patientId} not found")
                return

            assignment = await conn.fetchrow(
                'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                patientId
            )
            if not assignment or assignment['deviceId'] != deviceId:
                logger.warning(f"⚠️ Device {deviceId} not assigned to patient {patientId}")
                return

        # Store in TimescaleDB vitals_realtime table
        await self._storeVitalsRealtime(vitalsMsg)

        # ... more processing ...
```

**This handler:**
1. ✅ Validates message format (Pydantic model)
2. ✅ Checks patient exists
3. ✅ Verifies device assignment
4. ✅ Stores in TimescaleDB `vitals_realtime` table
5. ✅ Broadcasts to frontend via WebSocket

### Verification Plan

**Need to check:**
1. Does ESP32 firmware send vitals messages?
2. What is the vitals message format from ESP32?
3. Are vitals messages arriving at backend?
4. Are vitals being stored in TimescaleDB?

### How to Verify

```bash
# Check backend logs for vitals messages:
grep "Vitals" backend.log
grep "hospital/devices/fit-00001/vitals" backend.log

# Check TimescaleDB for stored vitals:
SELECT * FROM vitals_realtime WHERE "deviceId" = 'fit-00001' ORDER BY time DESC LIMIT 5;
```

---

## Summary

### ✅ Timezone Issue: NOT AN ISSUE
- Backend correctly stores UTC timestamps
- Frontend should convert to local timezone for display
- This is database best practice
- **No backend changes needed**

### ❓ Vitals Issue: NEEDS INVESTIGATION
- Heartbeats working ✅
- Vitals status unknown ❓
- Need to verify:
  1. ESP32 firmware sends vitals
  2. Vitals messages arrive at backend
  3. Vitals stored in TimescaleDB

---

## Next Steps

1. **Check ESP32 firmware** - Does it send vitals or just heartbeats?
2. **Monitor MQTT logs** - Filter for vitals topic messages
3. **Query TimescaleDB** - Check if any vitals data exists
4. **If no vitals:** ESP32 firmware needs to send vitals messages
5. **If frontend timezone issue:** Update frontend to convert UTC to local time

---

**Report Status:** Investigation in progress
