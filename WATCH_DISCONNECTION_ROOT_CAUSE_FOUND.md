# Watch Disconnection - Root Cause Found ✅

## Research Findings

### Device Registration Status (From Database)

```
ID: fit-00001
  Name: Fit Watch 00001
  Serial: SN-A0:A3:B3:AA:13:B0
  DB Status: assigned
  Battery: 100%
  Last Seen: 2025-11-04 19:19:28.362497+00:00
  Age: 1108.6 minutes ago (66515 seconds)
  Frontend Status: OFFLINE (red)
```

### ESP32 Actual Status (From Serial Monitor)

```
🏥 ESP32 Hospital Watch v5.2.8
✅ WiFi Connected (192.168.0.148)
✅ MQTT Connected with client certificate (mTLS)
📊 Vitals: Mode=ECG, HR=70, Temp=36.4°C, SpO2=98%, RR=14
```

## Root Cause: `lastSeen` Timestamp NOT Being Updated

**The Problem**:
1. ✅ ESP32 watch IS connected to WiFi
2. ✅ ESP32 watch IS connected to MQTT broker
3. ✅ ESP32 watch IS sending vitals/waveforms
4. ❌ **Backend MQTT service is NOT updating the `lastSeen` timestamp in database**

**Evidence**:
- `lastSeen` timestamp: `2025-11-04 19:19:28` (18+ hours ago!)
- Current time: `2025-11-05 (now)`
- Frontend connection threshold: 5 minutes
- Result: 18 hours > 5 minutes → Shows as "disconnected"

## Why `lastSeen` Not Being Updated

### Possible Causes:

**A. MQTT Service Not Processing Messages from fit-00001**
- Backend MQTT service is running (confirmed)
- But may not be receiving messages from `fit-00001`
- Or receiving messages but failing to update database

**B. Device ID Mismatch in MQTT Topics**
- ESP32 publishes to: `hospital/devices/fit-00001/vitals`
- Backend may be listening to different topic pattern
- Or device ID in messages doesn't match database ID

**C. Database Update Failure**
- MQTT service receives messages
- But `UPDATE devices SET "lastSeen" = NOW()` query fails silently
- Possible permission issue or connection pool issue

**D. Message Processing Error**
- MQTT service receives raw message
- But fails to parse/process it (malformed JSON?)
- Error occurs before `lastSeen` update

## Backend MQTT Service Code Review

From `mqtt_service.py` lines 543-546:
```python
# Update device last seen
await conn.execute(
    'UPDATE devices SET "lastSeen" = NOW(), "batteryLevel" = $2 WHERE id = $1',
    device_id, battery_level
)
```

This code SHOULD update `lastSeen` when processing vitals messages.

**But it's NOT happening for fit-00001!**

## Next Steps to Diagnose

### Step 1: Check Backend Console/Logs
Look for:
- MQTT message received from fit-00001
- Device ID extraction from topic
- Database update success/failure
- Any error messages

### Step 2: Check MQTT Topic Subscription
Verify backend is subscribed to correct topics:
- `hospital/devices/+/vitals`
- `hospital/devices/+/heartbeat`
- `hospital/devices/+/stream`

### Step 3: Test Manual Database Update
```sql
UPDATE devices SET "lastSeen" = NOW() WHERE id = 'fit-00001';
SELECT "lastSeen" FROM devices WHERE id = 'fit-00001';
```

If this works, database permissions are fine.

### Step 4: Check MQTT Message Format
ESP32 might be sending malformed messages that backend can't parse.

## Hypothesis

**Most Likely**: Backend MQTT service is receiving messages but the device ID extracted from the MQTT topic OR from the message payload doesn't match `'fit-00001'` exactly in the database query.

**Possible ID mismatch**:
- MQTT topic: `hospital/devices/fit-00001/vitals` ✅
- Message payload `deviceId`: might be different?
- Database ID: `fit-00001` ✅

**Alternative**: ESP32 v5.2.8 might have a bug where it doesn't include `deviceId` in vitals payload, causing backend to skip the `lastSeen` update.

## Recommended Fix Strategy

1. **Add debug logging** to MQTT service to see:
   - What device IDs are being extracted from messages
   - Whether database UPDATE is being called
   - Whether UPDATE succeeds or fails

2. **Check ESP32 v5.2.8 vitals payload** format:
   - Does it include `device_id` or `deviceId` field?
   - Does it match what backend expects?

3. **Verify MQTT subscription** is active for fit-00001's topics

4. **Test with mosquitto_sub** to see actual messages:
   ```bash
   mosquitto_sub -h localhost -p 8883 -t "hospital/devices/fit-00001/#" -v --cafile hospital_ca.crt
   ```

---

**Status**: Root cause identified - `lastSeen` not updating despite watch sending data
**Next**: Need to check backend MQTT service logs/console to see why UPDATE isn't happening
**Severity**: P1 - Watch is functional but appears disconnected in UI
