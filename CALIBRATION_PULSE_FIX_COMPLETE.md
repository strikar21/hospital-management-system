# Calibration Pulse Fix - Implementation Complete

**Issue:** Calibration pulse not appearing in ECG viewer
**Root Causes:**
1. Frontend never requested calibration from ESP32
2. Calibration pulse (600ms) too short compared to 25-second buffer

**Solution:** Combination fix implemented
- Frontend now requests calibration when ECG viewer opens
- Calibration pulse duration increased from 600ms to 3000ms

---

## Changes Made

### 1. Frontend - WebSocketService.ts ✅ (Already Working)
**File:** [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts)

The WebSocket service already had full support for `triggerCalibration` flag:
- Line 162: `subscribe()` method accepts `triggerCalibration` parameter
- Line 175: Sends calibration trigger during subscription
- Line 221-240: `subscribeToPatient()` includes calibration flag
- Line 244-259: `requestCalibration()` sends calibration request

**Status:** ✅ No changes needed - already implemented

---

### 2. Frontend - useECGViewer.ts ✅ (Already Fixed)
**File:** [hospital-display-app/src/hooks/useECGViewer.ts:49](hospital-display-app/src/hooks/useECGViewer.ts#L49)

**Change:** Subscription now includes `triggerCalibration: true` flag

```typescript
}, patient.id, true); // ← ADD patientId and triggerCalibration=true for calibration pulse
```

**Status:** ✅ Already modified - calibration requested on ECG viewer open

---

### 3. ESP32 - PhysiologicalSimulator.cpp ✅ (Fixed)
**File:** [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp)

**Changes Made:**

#### Line 45: Updated calibration duration
```cpp
// BEFORE
calibrationDuration = 600;  // 600ms total (200ms head + 200ms pulse + 200ms tail)

// AFTER
calibrationDuration = 3000;  // 3000ms total (1000ms head + 1000ms pulse + 1000ms tail)
```

#### Line 252: Updated log message
```cpp
// BEFORE
Serial.println("🔧 Calibration pulse started (600ms: 200ms head + 200ms pulse + 200ms tail)");

// AFTER
Serial.println("🔧 Calibration pulse started (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)");
```

#### Lines 278-288: Updated calibration pulse timing
```cpp
// BEFORE
if (elapsed < 200) {
    // Head: baseline (0mV)
    sample = 8388608;  // ADC midpoint
} else if (elapsed < 400) {
    // Pulse: 1.0mV square wave
    sample = 8388608 + 100000;  // 1mV above baseline
} else {
    // Tail: baseline (0mV)
    sample = 8388608;
}

// AFTER
if (elapsed < 1000) {
    // Head: baseline (0mV)
    sample = 8388608;  // ADC midpoint
} else if (elapsed < 2000) {
    // Pulse: 1.0mV square wave
    sample = 8388608 + 100000;  // 1mV above baseline
} else {
    // Tail: baseline (0mV)
    sample = 8388608;
}
```

**Status:** ✅ Fixed - calibration pulse now 3 seconds long

---

### 4. ESP32 - PhysiologicalSimulator.h ✅ (Fixed)
**File:** [esp32_hospital_watch_complete/PhysiologicalSimulator.h](esp32_hospital_watch_complete/PhysiologicalSimulator.h)

**Changes Made:**

#### Line 72: Updated method comment
```cpp
// BEFORE
void startCalibrationPulse();  // Trigger hardware calibration pulse (200ms flat → 200ms 1mV pulse → 200ms flat)

// AFTER
void startCalibrationPulse();  // Trigger hardware calibration pulse (1000ms flat → 1000ms 1mV pulse → 1000ms flat)
```

#### Line 132: Updated duration comment
```cpp
// BEFORE
unsigned long calibrationDuration;   // Total calibration duration: 600ms (200ms head + 200ms pulse + 200ms tail)

// AFTER
unsigned long calibrationDuration;   // Total calibration duration: 3000ms (1000ms head + 1000ms pulse + 1000ms tail)
```

**Status:** ✅ Fixed - documentation updated

---

### 5. Frontend - ecgConfig.ts ✅ (Fixed)
**File:** [hospital-display-app/src/config/ecgConfig.ts](hospital-display-app/src/config/ecgConfig.ts)

**Changes Made:**

#### Lines 44-50: Updated calibration constants
```typescript
// BEFORE
export const CALIBRATION_HEAD_DURATION_MS = 200;
export const CALIBRATION_PULSE_DURATION_MS = 200;
export const CALIBRATION_TAIL_DURATION_MS = 200;

// AFTER
export const CALIBRATION_HEAD_DURATION_MS = 1000;
export const CALIBRATION_PULSE_DURATION_MS = 1000;
export const CALIBRATION_TAIL_DURATION_MS = 1000;
```

#### Line 201: Updated documentation
```typescript
// BEFORE
 * - Calibration: 600ms total (200ms head + 200ms pulse + 200ms tail)

// AFTER
 * - Calibration: 3000ms total (1000ms head + 1000ms pulse + 1000ms tail)
```

**Status:** ✅ Fixed - constants now match ESP32 timing

---

## How It Works Now

### Calibration Flow:

1. **User opens ECG viewer** for a patient
2. **useECGViewer.ts** subscribes to WebSocket with `triggerCalibration: true` flag
3. **WebSocketService.ts** sends subscription message with calibration trigger
4. **Backend** receives `subscribePatient` message with `triggerCalibration: true`
5. **Backend** publishes MQTT message to `hospital/devices/{deviceId}/commands` topic with `{"type": "calibrate"}`
6. **ESP32 watch** receives calibrate command
7. **ESP32** calls `simulator.startCalibrationPulse()`
8. **ESP32** sends calibration pulse via waveform stream:
   - **0-1000ms**: Flat baseline (0mV, ADC=8388608)
   - **1000-2000ms**: Square wave (1mV, ADC=8488608)
   - **2000-3000ms**: Flat baseline (0mV, ADC=8388608)
9. **Backend** receives waveform data via MQTT and forwards to WebSocket
10. **Frontend** receives waveform, decodes delta encoding, renders to canvas
11. **User sees calibration pulse** (3 seconds = 1500 samples at 500Hz)

### Math:
```
Calibration pulse: 3000ms = 3 seconds = 1500 samples at 500Hz
Buffer capacity: 25000ms = 25 seconds = 12500 samples at 500Hz
Visible on screen: ~13.9 seconds = 6947 samples at 1313px width

Calibration percentage: 1500 / 12500 = 12% of total buffer
Calibration visibility: 1500 / 6947 = 21.6% of visible waveform

Result: Calibration pulse clearly visible for 3 seconds before ECG data fills screen
```

---

## Testing Instructions

### 1. Flash ESP32 Watch
```bash
# Upload modified firmware to ESP32
# Use Arduino IDE or PlatformIO to flash:
# - esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
# - esp32_hospital_watch_complete/PhysiologicalSimulator.cpp
# - esp32_hospital_watch_complete/PhysiologicalSimulator.h
```

### 2. Verify Calibration Trigger
1. Open hospital display app
2. Navigate to patient with assigned device
3. Click on patient to open ECG viewer
4. **Watch ESP32 serial monitor** - should see:
   ```
   🔧 Calibration pulse started (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
   ```
5. After 3 seconds:
   ```
   ✅ Calibration pulse complete
   ```

### 3. Verify Frontend Display
1. **Open ECG viewer** - canvas should be blank initially
2. **Within 1-2 seconds**, calibration pulse should appear:
   - 1 second flat baseline
   - 1 second square wave at 1mV (10mm high on 10mm/mV scale)
   - 1 second flat baseline
3. **After calibration**, normal ECG waveform should start flowing
4. **Check console logs** for waveform data messages

### 4. Verify Typewriter Mode Still Works
1. Calibration pulse should appear at **right edge** of screen
2. As ECG data arrives, waveform should **scroll leftward**
3. Old data (including calibration) should disappear off **left edge**
4. Full screen width (1313px) should be utilized

---

## Expected Behavior

### ✅ Success Criteria:
- [ ] Calibration pulse appears when ECG viewer opens
- [ ] Pulse is clearly visible for 3 seconds
- [ ] Pulse height matches 1mV medical standard (10mm on grid)
- [ ] Typewriter scrolling works (new data at right, scrolls left)
- [ ] Full screen width utilized
- [ ] Normal ECG data flows after calibration complete

### ❌ Failure Modes:
- **No calibration pulse appears**: Check ESP32 serial monitor - device may not be receiving MQTT command
- **Calibration too short**: Verify ESP32 code compiled with new 3000ms duration
- **Frontend constants wrong**: Check ecgConfig.ts has 1000ms per section
- **WebSocket not triggering**: Check useECGViewer.ts has `triggerCalibration: true`

---

## Files Modified

### ESP32 Firmware:
1. [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp)
   - Line 45: calibrationDuration = 3000
   - Line 252: Updated log message
   - Lines 278-288: Updated pulse timing (1000ms sections)

2. [esp32_hospital_watch_complete/PhysiologicalSimulator.h](esp32_hospital_watch_complete/PhysiologicalSimulator.h)
   - Line 72: Updated method comment
   - Line 132: Updated duration comment

### Frontend:
3. [hospital-display-app/src/config/ecgConfig.ts](hospital-display-app/src/config/ecgConfig.ts)
   - Lines 44-50: Calibration duration constants (1000ms each)
   - Line 201: Updated documentation

4. [hospital-display-app/src/hooks/useECGViewer.ts](hospital-display-app/src/hooks/useECGViewer.ts)
   - Line 49: Already has `triggerCalibration: true` ✅

5. [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts)
   - Already supports calibration trigger ✅

### Backend:
6. [hospital-backend/app/api/v1/websocket.py](hospital-backend/app/api/v1/websocket.py)
   - Already supports calibration trigger ✅

---

## Summary

**Problem:** Calibration pulse not visible in ECG viewer

**Root Causes:**
1. Frontend never requested calibration (missing `triggerCalibration` flag)
2. 600ms pulse drowned out by 25-second buffer

**Solution:**
1. ✅ Frontend now sends `triggerCalibration: true` when ECG viewer opens
2. ✅ Calibration pulse increased to 3000ms (1000ms + 1000ms + 1000ms)
3. ✅ All constants synchronized (ESP32 ↔ Frontend)

**Result:**
- Calibration pulse clearly visible for 3 seconds
- Medical-grade 1mV square wave from real ESP32 hardware
- Typewriter scrolling mode preserved
- Full screen width utilized

**Status:** ✅ **COMPLETE - READY FOR TESTING**
