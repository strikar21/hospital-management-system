# ESP32 Watch Status Check - Is It Sending Vitals?

**Date**: 2025-10-15
**Watch ID**: ESP32_WATCH_003

---

## Backend Log Analysis ✅

### What the Backend IS Receiving:

```
INFO: 192.168.0.148:53XXX - "POST /api/v1/esp32/ESP32_WATCH_003/heartbeat HTTP/1.1" 200 OK
```

✅ **Heartbeats**: Watch is sending heartbeats every ~30 seconds via HTTP (HMAC authenticated)
✅ **Battery Level**: Reporting 20% battery
✅ **Connection**: All heartbeats returning 200 OK (successful)

### What the Backend is NOT Receiving:

❌ **MQTT Vitals**: No vitals messages visible in backend logs
❌ **MQTT Alerts**: No alert messages visible in backend logs

---

## Root Cause: MQTT Service NOT Running ⚠️

**Backend Log Evidence:**
```
2025-10-15 08:57:19,288 - main - WARNING - ⚠️ MQTT service not available - ESP32 watches will need display relay
2025-10-15 08:57:19,288 - main - WARNING - ⚠️ Watch monitoring service not available
```

**What This Means:**
- Backend MQTT broker/client is not initialized
- Watch cannot publish vitals to MQTT topics
- Backend cannot subscribe to watch vitals/alerts

---

## Watch Firmware Behavior (v3.3.0)

### Sending Logic (from firmware):

**Heartbeats** (Line 1132-1155):
```cpp
// Send heartbeat every 30 seconds (HMAC authenticated)
if (wifiConnected && isProvisioned && ntpSynced && millis() - lastHeartbeat > 30000) {
  sendHeartbeat();  // ← HTTP POST to /api/v1/esp32/{deviceId}/heartbeat
  lastHeartbeat = millis();
}
```
✅ **Status**: Working (we see these in logs)

**Vitals** (Line 1177-1203):
```cpp
// Send vitals every 5 seconds if assigned to patient (MQTT)
if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 5000) {
  sendVitals();  // ← MQTT publish to hospital/devices/{deviceId}/vitals
  lastVitals = millis();
}

void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    if (!mqttClient.connected()) {
      connectToMQTT();  // ← Try to reconnect
    }
    return;  // ← EXIT if not connected or not assigned
  }
  // ... send vitals via MQTT
}
```
❓ **Status**: Unknown - need to check:
1. Is watch assigned to a patient? (`isAssigned` flag)
2. Is MQTT connection successful? (`mqttClient.connected()`)
3. What errors is the watch seeing?

---

## How to Diagnose Further

### Option 1: Check ESP32 Serial Monitor Output

Connect to the ESP32's serial port (115200 baud) and look for:

**Expected Output if Working:**
```
💓 Heartbeat sent (HMAC authenticated)
📊 Vitals sent via MQTT: HR=75, Temp=98.6, SpO2=98%
```

**Expected Output if MQTT Failing:**
```
❌ MQTT Connection failed, rc=-2
🔄 Connecting to MQTT as: HospitalWatch_ESP32_WATCH_003
```

**Expected Output if Not Assigned:**
```
💓 Heartbeat sent (HMAC authenticated)
(no vitals messages - watch doesn't send if not assigned)
```

### Option 2: Check Watch Assignment in Database

Query the `devices` table to see if watch is assigned:
```sql
SELECT id, "macAddress", "serialNumber", "assignedPatientId"
FROM devices
WHERE "serialNumber" LIKE '%003%' OR "macAddress" = '<MAC_ADDRESS>';
```

### Option 3: Check Watch's Captive Portal Status Page

1. Connect to watch's WiFi network OR
2. If watch is on your network, go to: `http://<watch_ip>/status`

**Status Page Should Show:**
```
📱 Device ID: ESP32_WATCH_003
📋 Serial: HW-SN-XXXXX
📶 WiFi: Connected ✅
🕐 NTP Synced: Yes ✅
🏥 Provisioned: Yes ✅
👤 Patient: <patientId> ✅  ← OR "Not assigned ❌"
🔋 Battery: 20%
```

---

## Expected Behavior

### If Watch is Assigned to a Patient:
1. ✅ Sends heartbeats every 30 seconds via HTTP
2. ✅ Sends vitals every 5 seconds via MQTT (if MQTT connected)
3. ✅ Sends alerts every 2 seconds via MQTT (if conditions met)

### If Watch is NOT Assigned to a Patient:
1. ✅ Sends heartbeats every 30 seconds via HTTP
2. ❌ Does NOT send vitals (guards prevent it)
3. ❌ Does NOT send alerts (guards prevent it)

---

## Assignment Persistence

**Watch Assignment Status Survives:**
- ✅ Firmware updates (reads from NVS flash)
- ✅ Power cycles (reads from NVS flash)
- ✅ Reboots (reads from NVS flash)

**Assignment is Cleared Only By:**
- ❌ Factory reset (erases NVS)
- ❌ Manual NVS clear
- ❌ Unassign command from backend (if implemented)

---

## Current Status Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| **Watch → Backend Heartbeats** | ✅ Working | Logs show 200 OK every 30s |
| **Watch → Backend Vitals (MQTT)** | ❌ Not Working | No MQTT messages in logs |
| **Backend MQTT Service** | ❌ Not Running | Warning in startup logs |
| **Watch Assignment Status** | ❓ Unknown | Need to check database/serial |
| **Watch MQTT Connection** | ❓ Unknown | Need to check serial monitor |

---

## Next Steps

1. **Check ESP32 Serial Monitor** - See actual watch behavior and error messages
2. **Verify Watch Assignment** - Query database or check status page
3. **Start MQTT Service** - Backend needs MQTT broker/client running to receive vitals
4. **Test MQTT Connection** - Verify watch can connect to MQTT broker

---

## Conclusion

**The watch is successfully communicating with the backend via HTTP heartbeats**, but:

- ⚠️ **MQTT vitals transmission cannot work** because backend MQTT service is not running
- ❓ **Unknown if watch is assigned** to a patient (which would enable vitals sending)
- ❓ **Unknown if watch is trying to send vitals** (need serial monitor to confirm)

**To see vitals data flowing, you need to:**
1. Start the backend MQTT broker service
2. Ensure watch is assigned to a patient
3. Verify watch MQTT connection succeeds
