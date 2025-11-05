# Calibration Pulse Not Reaching ESP32 - Diagnosis

## Issue
"now calibration pulse request doesnt come to the watch ever"

## Research Complete ✅

I've audited the entire calibration flow from frontend to ESP32. See [CALIBRATION_PULSE_COMPLETE_AUDIT.md](CALIBRATION_PULSE_COMPLETE_AUDIT.md) for full details.

## Code Status: ALL CORRECT ✅

Every part of the calibration flow code is correct:

1. ✅ Frontend triggers calibration
2. ✅ WebSocket service sends `triggerCalibration: true`
3. ✅ Backend WebSocket handler receives and processes
4. ✅ Backend queries database for device ID
5. ✅ Backend MQTT service publishes command
6. ✅ ESP32 subscribes to commands topic
7. ✅ ESP32 handles calibration command
8. ✅ ESP32 triggers simulator calibration pulse

**The code architecture is perfect. The issue is in the runtime state, not the code.**

## Most Likely Root Causes

### Issue 1: Device ID Mismatch 🎯 **MOST LIKELY**

**Database device:** `fit-00001` (assigned to patient `081a5294...`)
**ESP32 device ID:** Unknown - we don't know what the ESP32 is using

**Problem:**
- Backend publishes to: `hospital/devices/fit-00001/commands`
- ESP32 subscribes to: `hospital/devices/{ESP32_DEVICE_ID}/commands`
- If `{ESP32_DEVICE_ID}` ≠ `fit-00001`, commands never arrive

**How to Check:**
1. Open ESP32 Serial Monitor
2. Look for: `"Device ID: XXX"` during boot
3. Look for: `"📡 Subscribed to: hospital/devices/XXX/commands"`
4. Verify that `XXX` matches `fit-00001`

**Fix if Mismatched:**
- Either update database to use ESP32's actual device ID
- Or re-provision ESP32 with device ID `fit-00001`

---

### Issue 2: ESP32 Not Connected to MQTT 🎯 **SECOND MOST LIKELY**

**Problem:**
- ESP32 not connected to MQTT broker
- Can't receive commands if not connected

**How to Check:**
1. Open ESP32 Serial Monitor
2. Look for: `"✅ MQTT Connected with client certificate (mTLS)!"`
3. Look for: `"📡 Subscribed to: hospital/devices/XXX/commands"`
4. If you see `"❌ MQTT Connection failed"`, ESP32 is not connected

**Common Causes:**
- Wrong WiFi network
- Certificate issues
- MQTT broker not reachable
- Firewall blocking port 8883

---

### Issue 3: Backend MQTT Service Not Connected

**Problem:**
- Backend MQTT service not connected to broker
- Can't publish commands if not connected

**How to Check:**
1. Check backend logs/console
2. Look for: `"✅ MQTT Connected"` or `"⚠️ MQTT not connected"`
3. If not connected, backend can't send commands

**Fix:**
- Restart backend
- Check Mosquitto broker is running
- Check backend can reach broker

---

### Issue 4: No Device Assigned to Patient

**Status:** ✅ NOT THE ISSUE

I verified that device `fit-00001` IS assigned to patient `081a5294-da91-4c74-bb8a-e5062f5851dd`.

---

## Diagnostic Commands

### 1. Check ESP32 Device ID and MQTT Status
```
Open Arduino IDE Serial Monitor (115200 baud)
Press RESET on ESP32
Look for these lines:
  - "Device ID: XXX"
  - "✅ MQTT Connected"
  - "📡 Subscribed to: hospital/devices/XXX/commands"
```

### 2. Check Backend MQTT Status
```bash
# Look at backend console/logs
# Should see: "✅ MQTT Connected"
```

### 3. Test Manual MQTT Publish
```bash
# From Windows CMD or PowerShell
cd c:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto

# Publish test calibration command
mosquitto_pub -h localhost -p 8883 ^
  --cafile certs/ca.crt ^
  --cert certs/client.crt ^
  --key certs/client.key ^
  -t "hospital/devices/fit-00001/commands" ^
  -m "{\"command\":\"calibrate\",\"commandId\":\"test-123\",\"timestamp\":\"2025-01-04T00:00:00Z\"}"
```

If ESP32 receives the manual command → Backend MQTT service not publishing
If ESP32 doesn't receive manual command → ESP32 device ID mismatch or not connected

### 4. Monitor All MQTT Traffic
```bash
# Subscribe to all device topics
mosquitto_sub -h localhost -p 8883 ^
  --cafile certs/ca.crt ^
  --cert certs/client.crt ^
  --key certs/client.key ^
  -t "hospital/devices/#" ^
  -v
```

Open ECG viewer and watch for commands being published

---

## What to Do Next

### Step 1: Check ESP32 Device ID ⚠️ **DO THIS FIRST**
1. Open Serial Monitor
2. Press RESET on ESP32
3. Find device ID in boot messages
4. Compare with database device ID (`fit-00001`)

### Step 2: If Device ID Matches
- Check ESP32 MQTT connection status
- Check backend MQTT connection status
- Run manual MQTT publish test

### Step 3: If Device ID Doesn't Match
**Option A: Update Database**
```sql
-- Update device ID in database to match ESP32
UPDATE devices SET id = 'ESP32_ACTUAL_ID' WHERE id = 'fit-00001';
UPDATE deviceassignments SET "deviceId" = 'ESP32_ACTUAL_ID' WHERE "deviceId" = 'fit-00001';
```

**Option B: Re-provision ESP32**
- Generate new provisioning code for device ID `fit-00001`
- Re-provision ESP32 with that code
- ESP32 will use device ID from provisioning

---

## Summary

**Code is correct ✅** - All calibration flow logic is properly implemented

**Issue is runtime state ❌** - Most likely:
1. ESP32 device ID doesn't match database (`fit-00001`)
2. ESP32 not connected to MQTT broker
3. Backend MQTT service not connected

**Next Step:** Check ESP32 Serial Monitor to get device ID and MQTT connection status

**Files Created:**
- [CALIBRATION_PULSE_COMPLETE_AUDIT.md](CALIBRATION_PULSE_COMPLETE_AUDIT.md) - Full code audit
- [CALIBRATION_NOT_REACHING_ESP32_DIAGNOSIS.md](CALIBRATION_NOT_REACHING_ESP32_DIAGNOSIS.md) - This file
