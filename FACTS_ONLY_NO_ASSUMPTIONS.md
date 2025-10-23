# Facts Only - No Assumptions

**Date:** 2025-10-22
**Status:** Evidence-based analysis only

---

## Your Questions

1. **Is lastSeen in GMT not local timezone?**
2. **Are vitals data coming through?**

---

## Question 1: lastSeen Timezone

### ✅ FACTS VERIFIED:

**Database Query:**
```sql
SELECT id, status, "lastSeen", "batteryLevel" FROM devices WHERE id = 'fit-00001';
-- Result: lastSeen=2025-10-22 15:47:52.281802+00:00
```

**Code:** [mqtt_service.py:717](hospital-backend/app/services/mqtt_service.py#L717)
```python
UPDATE devices SET "lastSeen" = NOW() WHERE id = $1
```

**PostgreSQL Documentation:** `NOW()` returns UTC timestamp

### ✅ ANSWER:
**YES, it's in UTC (GMT+0)**

**Is this correct?**
- Standard database practice is UTC storage
- Frontend should convert to local timezone for display

---

## Question 2: Vitals Data

### ✅ FACTS VERIFIED:

**Backend Logs (Last 2 hours):**
```
💓 MQTT Heartbeat: fit-00001 Battery 100% Signal -56dBm  (repeated every 30s)
```
- ✅ Heartbeat messages arriving
- ❌ NO vitals messages logged
- ❌ NO "Vitals processed" logs
- ❌ NO MQTT messages on topic `hospital/devices/fit-00001/vitals`

**Database Check:**
```sql
-- vitals_timeseries table EXISTS
SELECT COUNT(*) FROM vitals_timeseries;
-- Result: 272 rows

SELECT DISTINCT "deviceId" FROM vitals_timeseries;
-- Result: Only "TEST_WATCH_001" (old test data from Oct 8)

SELECT * FROM vitals_timeseries WHERE "deviceId" = 'fit-00001';
-- Result: 0 rows (NO DATA)
```

**ESP32 Firmware Code:** [esp32_hospital_watch_complete.ino:1342-1347](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1342-L1347)
```arduino
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    return;  // EXIT - don't send vitals
  }
  // ... send vitals code ...
}
```

**ESP32 Main Loop:** [esp32_hospital_watch_complete.ino:646](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L646)
```arduino
if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 1000) {
    simulator.update();
    heartRate = simulator.getHeartRate();
    // ...
    sendVitals();
}
```

**Device Assignment in Database:**
```sql
SELECT * FROM deviceassignments WHERE "deviceId" = 'fit-00001';
-- Result: patientId='TEST001', status='active', assignedAt=2025-10-22 13:09:44
```

### ✅ ANSWER:
**NO, vitals are NOT coming through from fit-00001**

---

## What We Know For Sure

1. ✅ ESP32 fit-00001 is connected to MQTT (heartbeats prove this)
2. ✅ Backend is receiving heartbeats every 30 seconds
3. ✅ Device is provisioned (has certificate, connects with mTLS)
4. ✅ Device is assigned to TEST001 in database
5. ❌ ESP32 is NOT sending vitals messages
6. ✅ ESP32 firmware has code to send vitals (exists in .ino file)
7. ✅ vitals_timeseries table exists and can store data
8. ✅ Backend has handler for vitals messages

---

## What We Don't Know

1. ❓ What is ESP32 `isAssigned` variable value? (requires serial monitor)
2. ❓ Does ESP32 think it's assigned to a patient? (requires serial monitor)
3. ❓ Was ESP32 ever notified about assignment via MQTT? (no logs found)
4. ❓ Did ESP32 persist assignment status in NVS? (requires serial monitor)
5. ❓ Why is ESP32 not sending vitals? (multiple possible reasons)

---

## Possible Reasons ESP32 Not Sending Vitals

### Reason 1: ESP32 `isAssigned` is FALSE
- ESP32 checks `if (!isAssigned)` before sending vitals
- If this variable is false, vitals never sent
- **Can't verify without serial monitor output**

### Reason 2: PhysiologicalSimulator Not Running
- ESP32 must call `simulator.update()` every loop
- If simulator not initialized, no vitals generated
- **Can't verify without serial monitor output**

### Reason 3: MQTT Connection Issue
- ESP32 checks `if (!mqttClient.connected())` before sending
- But heartbeats work, so connection is OK
- **This is unlikely**

### Reason 4: ESP32 Never Received Assignment Message
- Backend assigned device while ESP32 was offline/restarting
- Backend doesn't send assignment on heartbeat arrival
- ESP32 lost assignment from memory on power cycle
- **Possible, but can't confirm without checking backend assignment flow**

---

## Backend Assignment Flow - NEED TO CHECK

**Watch Management API:** [watch_management.py:186](hospital-backend/app/api/v1/watch_management.py#L186)
```python
# When device is assigned:
await conn.execute(
    "UPDATE devices SET status = 'assigned', \"updatedAt\" = $1 WHERE id = $2",
    now, deviceId
)
```

**Question:** Does this API also send MQTT message `hospital/devices/fit-00001/assign`?
**Need to check:** Full function to see if MQTT publish happens

---

## Summary - Facts Only

### Question 1: Timezone
- ✅ **FACT:** lastSeen is in UTC
- ✅ **STANDARD:** This is correct database practice

### Question 2: Vitals
- ✅ **FACT:** Heartbeats arriving from fit-00001
- ✅ **FACT:** NO vitals messages from fit-00001
- ✅ **FACT:** vitals_timeseries table exists but empty for fit-00001
- ✅ **FACT:** Device assigned in database
- ❓ **UNKNOWN:** ESP32 internal state (requires serial monitor)

### To Definitively Diagnose Vitals Issue:
1. Need ESP32 serial monitor output
2. OR check backend watch assignment code for MQTT publish
3. OR manually send MQTT assignment message and test

---

**Status:** Facts documented, ready for next diagnostic step
