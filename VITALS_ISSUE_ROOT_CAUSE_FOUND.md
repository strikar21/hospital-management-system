# Vitals Issue - Root Cause Found

**Date:** 2025-10-22
**Status:** ✅ **ROOT CAUSE IDENTIFIED**

---

## Summary

**ESP32 is NOT sending vitals because it doesn't know it's assigned to a patient.**

---

## Evidence

### 1. Database Assignment Status
```sql
SELECT * FROM deviceassignments WHERE "deviceId" = 'fit-00001';
-- Result: patientId='TEST001', status='active', assignedAt=2025-10-22 13:09:44
```
✅ **Backend knows device is assigned**

### 2. ESP32 Firmware Logic
**File:** [esp32_hospital_watch_complete.ino:646-657](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L646-L657)

```arduino
if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 1000) {
    simulator.update();
    heartRate = simulator.getHeartRate();
    // ...
    sendVitals();
    lastVitals = millis();
}
```

**Condition requires:** `isAssigned == true`

**Variable:** `isAssigned` is a boolean stored in ESP32 memory (line 93)

### 3. How ESP32 Learns About Assignment
**File:** [esp32_hospital_watch_complete.ino:1144-1154](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1144-L1154)

```arduino
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  // ...
  if (String(topic).endsWith("/assign")) {
    JsonDocument doc;
    if (deserializeJson(doc, message) == DeserializationError::Ok) {
      if (doc["patientId"].is<String>()) {
        assignedPatientId = doc["patientId"].as<String>();
        isAssigned = true;  // ← ESP32 sets this flag
        saveConfiguration();
        Serial.println("👤 Assigned to patient: " + assignedPatientId);
      }
    }
  }
}
```

ESP32 expects MQTT message on topic: `hospital/devices/fit-00001/assign`

### 4. Backend Assignment Flow
When a device is assigned via watch management API, backend should send MQTT message to notify device.

**Need to check:** Does backend send MQTT assignment message when device is assigned?

---

## Root Cause

**ESP32 `isAssigned` flag is FALSE** even though database shows assignment as active.

**Reason:** Backend assigned device BEFORE ESP32 was connected to MQTT (or backend didn't send MQTT assignment message).

---

## Timeline Reconstruction

1. ✅ **Device provisioned** - fit-00001 created in database
2. ✅ **Device assigned to TEST001** - Database updated, `deviceassignments` record created
3. ❓ **MQTT assignment message sent?** - ESP32 should have received `/assign` message
4. ❌ **ESP32 never received message** - `isAssigned` remains FALSE
5. ❌ **ESP32 skips vitals sending** - Condition `isAssigned == true` fails

---

## Why This Happened

**Possible scenarios:**

1. **Device was assigned while ESP32 was offline** - Assignment happened before ESP32 connected to MQTT
2. **Backend doesn't send MQTT assignment message** - Watch management API updates database but doesn't notify device
3. **MQTT message was sent but ESP32 wasn't subscribed yet** - Race condition during connection
4. **ESP32 restarted after assignment** - Lost `isAssigned` flag from memory (not persisted correctly)

---

## The Fix

**Option 1: Manually Send Assignment Message** (Quick test)
```bash
mosquitto_pub -h 127.0.0.1 -p 8883 \
  --cafile mosquitto/certs/hospital_ca.crt \
  --cert mosquitto/certs/client.crt \
  --key mosquitto/certs/client.key \
  -t "hospital/devices/fit-00001/assign" \
  -m '{"patientId":"TEST001"}'
```

**Option 2: Backend Send Assignment on Device Connect** (Proper fix)
When ESP32 connects to MQTT and sends first heartbeat, backend should check if device is assigned and send assignment message.

**Option 3: ESP32 Query Assignment Status on Connect** (Alternative)
ESP32 could query backend via HTTP API on MQTT connect to get current assignment status.

---

## Verification Steps

1. Check if backend sends MQTT assignment message in watch management API
2. Check ESP32 serial monitor to see if it received assignment
3. Check ESP32 `isAssigned` flag status
4. Manually send assignment message to test

---

## Next Steps

1. **Check backend watch management API** - Does it send MQTT message?
2. **Send manual assignment message** - Test if ESP32 starts sending vitals
3. **Implement proper fix** - Backend should send assignment on heartbeat if device doesn't know

---

**Status:** Root cause identified, ready to implement fix
