# Calibration Command Status - What's Actually Done

**Date:** 2025-11-03
**Status:** ✅ **ALREADY FIXED** - ESP32 firmware updated

---

## Root Cause (from CALIBRATION_COMMAND_NOT_REACHING_ESP32_ROOT_CAUSE.md)

**The Problem:**
- ESP32 was subscribing to: `hospital/devices/{deviceId}/command` (singular)
- Backend was publishing to: `hospital/devices/{deviceId}/commands` (plural)
- **MQTT topic mismatch** = ESP32 never received calibration commands

---

## What's Already Fixed

### ✅ Fix 1: Subscription Topic (Line 1602)
**File:** [esp32_hospital_watch_complete.ino:1602](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1602)

```cpp
String commandTopic = "hospital/devices/" + deviceId + "/commands";  // ✅ PLURAL
mqttClient.subscribe(commandTopic.c_str());
Serial.println("📡 Subscribed to: " + commandTopic);
```

**Status:** ✅ **FIXED** - Now subscribes to `/commands` (plural)

---

### ✅ Fix 2: Message Handler (Line 1639)
**File:** [esp32_hospital_watch_complete.ino:1639](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1639)

```cpp
if (String(topic).endsWith("/commands")) {  // ✅ PLURAL
  lastCommandReceivedAt = millis();
  // ✅ v5.2.2: Bug #5 fix - Reset deviceUnresponsiveAlertSent when command received
  deviceUnresponsiveAlertSent = false;

  JsonDocument doc;
  if (deserializeJson(doc, message) == DeserializationError::Ok) {
    String commandType = doc["command"].as<String>();
    String commandId = doc["commandId"].as<String>();

    if (commandType == "ping") {
      handlePingCommand(commandId);
    } else if (commandType == "calibrate") {
      handleCalibrationCommand(commandId);
    }
  }
}
```

**Status:** ✅ **FIXED** - Now checks for `/commands` (plural)

---

### ✅ Fix 3: Comment Update (Line 908)
**File:** [esp32_hospital_watch_complete.ino:908](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L908)

```cpp
// ✅ Trigger physiological simulator calibration pulse (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
```

**Status:** ✅ **FIXED** - Comment updated from 600ms to 3000ms

---

## Backend Publishing (Already Working)

**File:** [mqtt_service.py:182](hospital-backend/app/services/mqtt_service.py#L182)

```python
topic = f"hospital/devices/{deviceId}/commands"  # ✅ PLURAL
```

**Status:** ✅ Backend publishes to `/commands` (plural) - no changes needed

---

## Calibration Handler (Already Working)

**File:** [esp32_hospital_watch_complete.ino:905-938](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L905-L938)

```cpp
void handleCalibrationCommand(String commandId) {
  Serial.println("🔧 Calibration command received");

  // Trigger physiological simulator calibration pulse (3000ms)
  simulator.startCalibrationPulse();

  // Flash LED to indicate calibration in progress
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  // Wait for calibration pulse to complete (3000ms + margin)
  delay(3100);

  // Publish completion notification
  String topic = "hospital/devices/" + deviceId + "/calibration_complete";
  // ...

  Serial.println("✅ Calibration pulse complete - waveforms will contain calibration data");
}
```

**Status:** ✅ Handler ready and waiting for commands

---

## PhysiologicalSimulator (Already Working)

**File:** [PhysiologicalSimulator.cpp:278-288](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L278-L288)

```cpp
void PhysiologicalSimulator::generateECGSampleWithPhase(int lead, float phase, int32_t& sample) {
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);
        if (elapsed < 1000) {
            sample = 8388608;  // Head: baseline (0mV) - 1000ms
        } else if (elapsed < 2000) {
            sample = 8388608 + 100000;  // Pulse: 1.0mV - 1000ms
        } else {
            sample = 8388608;  // Tail: baseline (0mV) - 1000ms
        }
        return;
    }
    // Normal ECG generation...
}
```

**Status:** ✅ Generates 3000ms calibration pulse (1000ms + 1000ms + 1000ms)

---

## Frontend (Already Working)

**File:** [ecgConfig.ts:44-50](hospital-display-app/src/config/ecgConfig.ts#L44-L50)

```typescript
export const CALIBRATION_HEAD_DURATION_MS = 1000;
export const CALIBRATION_PULSE_DURATION_MS = 1000;
export const CALIBRATION_TAIL_DURATION_MS = 1000;
```

**Status:** ✅ Frontend expects 3000ms calibration pulse

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| ESP32 subscription topic | ✅ Fixed | Changed to `/commands` (plural) |
| ESP32 message handler | ✅ Fixed | Checks for `/commands` (plural) |
| ESP32 comment accuracy | ✅ Fixed | Updated to 3000ms |
| Backend publishing | ✅ Working | Already uses `/commands` (plural) |
| Calibration handler | ✅ Ready | Waiting for commands |
| PhysiologicalSimulator | ✅ Ready | Generates 3000ms pulse |
| Frontend config | ✅ Synced | Expects 3000ms pulse |

---

## What Needs to Happen Next

**The ESP32 firmware file has been modified but NOT YET FLASHED to the device.**

### To Complete This Fix:

1. **Flash the updated firmware to ESP32 device**
   - Connect ESP32 via USB
   - Upload the modified `esp32_hospital_watch_complete.ino`
   - Verify upload successful

2. **Test the calibration command flow:**
   - Open ECG Viewer for an assigned patient
   - Check ESP32 Serial Monitor for:
     ```
     🔧 Calibration command received
     ✅ Calibration pulse complete - waveforms will contain calibration data
     ```
   - Verify frontend displays 3-second calibration pulse:
     - 1000ms flat baseline at 0mV
     - 1000ms square pulse at 1.0mV (10 large squares high)
     - 1000ms flat baseline at 0mV

---

## Git Status

The ESP32 firmware file is currently modified but not committed:
```
M esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
```

**Next steps:**
1. Flash firmware to device
2. Test calibration command
3. If working, commit changes with message: "FIX: Calibration command MQTT topic mismatch (singular → plural)"

---

**Conclusion:** All code changes are complete. The fix just needs to be **flashed to the physical ESP32 device** to take effect.
