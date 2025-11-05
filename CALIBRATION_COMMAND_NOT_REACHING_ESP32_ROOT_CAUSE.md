# Calibration Command Not Reaching ESP32 - ROOT CAUSE FOUND

**Date:** 2025-11-03
**Status:** 🔴 BUG CONFIRMED - MQTT Topic Mismatch

---

## Problem Statement

User reports: **"not reaching"** - calibration command not appearing on ESP32 device when ECG viewer opens.

---

## Root Cause Analysis

### Topic Name Mismatch (Singular vs Plural)

**ESP32 Firmware** ([esp32_hospital_watch_complete.ino:1602](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1602)):
```cpp
String commandTopic = "hospital/devices/" + deviceId + "/command";  // ❌ SINGULAR
mqttClient.subscribe(commandTopic.c_str());
```

**Backend MQTT Service** ([mqtt_service.py:182](hospital-backend/app/services/mqtt_service.py#L182)):
```python
topic = f"hospital/devices/{deviceId}/commands"  # ❌ PLURAL
```

**Result:** ESP32 never receives calibration commands because it's listening on the wrong topic!

---

## Evidence Trail

### 1. Frontend → Backend WebSocket
✅ **WORKING** - Frontend sends calibration trigger correctly:

[WebSocketService.ts:162-180](hospital-display-app/src/services/WebSocketService.ts#L162-L180):
```typescript
public subscribe(subscriberId: string, callback: Function, patientId?: string, triggerCalibration?: boolean)
```

[useECGViewer.ts:49](hospital-display-app/src/hooks/useECGViewer.ts#L49):
```typescript
}, patient.id, true); // ✅ triggerCalibration=true
```

### 2. Backend WebSocket → MQTT Publish
✅ **WORKING** - Backend publishes MQTT command:

[websocket.py:261-276](hospital-backend/app/api/v1/websocket.py#L261-L276):
```python
async def _triggerDeviceCalibration(deviceId: str, patientId: str) -> None:
    command = {
        'command': 'calibrate',
        'commandId': commandId,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'triggeredBy': 'ecgViewerOpen',
        'patientId': patientId
    }
    await mqttService.publishCommand(deviceId, command)
    logger.info(f"📤 Calibration command sent to device {deviceId}")
```

[mqtt_service.py:176-195](hospital-backend/app/services/mqtt_service.py#L176-L195):
```python
async def publishCommand(self, deviceId: str, command: Dict[str, Any]) -> bool:
    topic = f"hospital/devices/{deviceId}/commands"  # ❌ PLURAL
    payload = json.dumps(command)
    result = self.client.publish(topic, payload, qos=1)
```

### 3. MQTT Broker → ESP32
❌ **BROKEN** - ESP32 never receives message:

**ESP32 subscribes to:**
```
hospital/devices/ESP32_WATCH_001/command  ← Singular
```

**Backend publishes to:**
```
hospital/devices/ESP32_WATCH_001/commands  ← Plural
```

**MQTT broker receives the message on `/commands` but ESP32 is listening on `/command`, so it never arrives!**

---

## ESP32 Calibration Handler (Ready and Waiting)

[esp32_hospital_watch_complete.ino:905-938](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L905-L938):
```cpp
void handleCalibrationCommand(String commandId) {
  Serial.println("🔧 Calibration command received");  // ← Never prints because command never arrives!

  // Trigger physiological simulator calibration pulse (3000ms)
  simulator.startCalibrationPulse();

  // Flash LED to indicate calibration in progress
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  // Wait for calibration pulse to complete
  delay(700);

  // Publish completion notification
  String topic = "hospital/devices/" + deviceId + "/calibration_complete";
  // ...

  Serial.println("✅ Calibration pulse complete");
}
```

**Note:** Comment on line 908 still says "600ms" but code at [PhysiologicalSimulator.cpp:133](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L133) already updated to 3000ms.

---

## PhysiologicalSimulator Calibration (Already Fixed)

[PhysiologicalSimulator.cpp:278-288](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L278-L288):
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
    // ...
}
```

✅ Calibration pulse already extended from 600ms to 3000ms (1000ms + 1000ms + 1000ms).

---

## Frontend ecgConfig.ts (Already Synced)

[ecgConfig.ts:44-50](hospital-display-app/src/config/ecgConfig.ts#L44-L50):
```typescript
export const CALIBRATION_HEAD_DURATION_MS = 1000;
export const CALIBRATION_PULSE_DURATION_MS = 1000;
export const CALIBRATION_TAIL_DURATION_MS = 1000;
```

✅ Frontend constants already match ESP32 timing.

---

## Fix Required

**Option 1:** Change ESP32 to subscribe to `/commands` (plural)
**Option 2:** Change backend to publish to `/command` (singular)

**Recommendation:** Use **plural** (`/commands`) as it's more RESTful and consistent with other multi-entity topics.

### Files to Fix

1. **ESP32 Firmware:** [esp32_hospital_watch_complete.ino:1602](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1602)
   ```cpp
   // BEFORE
   String commandTopic = "hospital/devices/" + deviceId + "/command";

   // AFTER
   String commandTopic = "hospital/devices/" + deviceId + "/commands";
   ```

2. **ESP32 Message Handler:** [esp32_hospital_watch_complete.ino:740](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L740)
   ```cpp
   // BEFORE
   if (String(topic).endsWith("/command")) {

   // AFTER
   if (String(topic).endsWith("/commands")) {
   ```

3. **ESP32 Comment:** [esp32_hospital_watch_complete.ino:908](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L908)
   ```cpp
   // Update outdated comment from 600ms to 3000ms
   ```

---

## Testing Plan

1. **Flash ESP32** with fixed firmware
2. **Open ECG Viewer** for an assigned patient
3. **Check ESP32 Serial Monitor** for:
   ```
   🔧 Calibration command received
   ✅ Calibration pulse complete - waveforms will contain calibration data
   ```
4. **Check Frontend ECG Display** for 3-second calibration pulse:
   - 1000ms flat baseline at 0mV
   - 1000ms square pulse at 1.0mV (10 large squares high)
   - 1000ms flat baseline at 0mV

---

## Summary

- **Root Cause:** MQTT topic mismatch (`/command` vs `/commands`)
- **Impact:** Calibration commands never reach ESP32
- **Fix:** Change ESP32 to subscribe to `/commands` (plural)
- **Effort:** 3-line code change + re-flash device
- **Status:** Ready to implement

---

**Next Step:** Fix ESP32 firmware and re-flash device.
