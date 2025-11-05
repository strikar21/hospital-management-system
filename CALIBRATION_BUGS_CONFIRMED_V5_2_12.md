# Calibration Bugs Confirmed - ESP32 v5.2.12

**Date**: 2025-11-05
**User Report**: "no calibration no waveform after watch receives the command"
**Firmware Version**: 5.2.12 (confirmed from user's paste)

---

## CONFIRMED BUGS

### Bug #1: Blocking Delay - CRITICAL

**File**: `esp32_hospital_watch_complete.ino`
**Lines**: 941-974
**Function**: `handleWaveformCalibrationCommand()`

**The Problem:**
```cpp
void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");

  simulator.startCalibrationPulse();  // Sets calibrationActive = true

  // LED flashing: 600ms blocking
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  // ❌ CRITICAL BUG: 3.1 second blocking delay!
  delay(3100);  // ← LINE 956 - THIS FREEZES EVERYTHING!

  // ... rest of function
}
```

**Impact:**
- **Total blocking time**: 3,700ms (600ms LED + 3100ms wait)
- During this time:
  - ❌ `loop()` doesn't execute
  - ❌ No waveform streaming (`sendWaveformStream()` never called)
  - ❌ No vitals publishing (`sendVitals()` never called)
  - ❌ No MQTT processing (`mqttClient.loop()` never called)
  - ❌ ESP32 completely frozen

**User Experience:**
1. User opens ECG Viewer
2. Frontend sends calibration request
3. Backend publishes MQTT command
4. ESP32 receives command, LED flashes
5. **Waveform data stops flowing for 3.7 seconds** ← User sees blank screen
6. After 3.7 seconds, waveforms resume

**This is EXACTLY what user reported**: "no waveform after watch receives the command"

---

### Bug #2: Mode-Specific Calibration - MEDIUM

**File**: `PhysiologicalSimulator.cpp`
**Lines**: 547-572
**Function**: `generateEEGSampleWithPhase()`

**The Problem:**
```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ❌ BUG: Doesn't check isCalibrationActive()!

    // Generate waveform based on activity state and channel (using current phase)
    float amplitude = generateEEGWaveform(eegPhase, channel);

    // ... convert to ADC values ...
    sample = 8388608 + (int32_t)(amplitude * 1000);

    // ✅ NOTE: Phase is updated by fillSampleBuffer() ONCE per sample, NOT here
}
```

**Compare to ECG generator** (Lines 274-291):
```cpp
void PhysiologicalSimulator::generateECGSampleWithPhase(int lead, float phase, int32_t& sample) {
    // ✅ CORRECT: Checks calibration FIRST
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // Extended calibration: 1000ms head → 1000ms pulse → 1000ms tail
        if (elapsed < 1000) {
            sample = 8388608;  // Baseline
        } else if (elapsed < 2000) {
            sample = 8388608 + 100000;  // 1mV pulse
        } else {
            sample = 8388608;  // Baseline
        }
        return;  // Skip normal ECG generation
    }

    // Normal ECG generation...
}
```

**Impact:**
- Calibration pulse only works in ECG mode
- If watch is in EEG mode (GPIO 4 LOW):
  - Calibration command received
  - Calibration flag set to true
  - But EEG generator ignores it
  - No calibration pulse appears
  - Normal EEG waveforms continue

**User Experience:**
- User opens ECG Viewer while watch is in EEG mode
- Watch receives calibration command, LED flashes
- **No calibration pulse appears** (Bug #2)
- **No waveforms at all for 3.7 seconds** (Bug #1)
- Then EEG waveforms resume (wrong mode!)

---

## ROOT CAUSE ANALYSIS

### Why Bug #1 Exists

**Historical Design Decision:**
The calibration handler was designed as a synchronous blocking operation:
1. Start calibration
2. Wait for completion
3. Publish notification
4. Return

**Why it seemed reasonable:**
- Calibration is only 3 seconds
- Happens infrequently (only when ECG Viewer opens)
- Simple linear flow

**Why it's wrong:**
- Arduino `delay()` is **completely blocking**
- All other operations stop (waveforms, vitals, MQTT)
- User sees frozen data

**The irony:**
- PhysiologicalSimulator has **non-blocking calibration** built in!
- `isCalibrationActive()` checks if 3000ms elapsed and auto-stops
- Handler doesn't need to wait - simulator handles it!

### Why Bug #2 Exists

**Copy-paste oversight:**
- ECG generator (`generateECGSampleWithPhase`) was created first with calibration support
- EEG generator (`generateEEGSampleWithPhase`) was created later
- Calibration check wasn't copied to EEG generator
- Nobody tested calibration in EEG mode

---

## THE FIX

### Fix #1: Remove Blocking Delay (NON-BLOCKING CALIBRATION)

**Changes Required:**

#### 1. Add global tracking variables (after line 226):
```cpp
bool calibrationRequested = false;
String calibrationCommandId = "";
unsigned long calibrationStartMillis = 0;
```

#### 2. Modify `handleWaveformCalibrationCommand()` (lines 941-974):
```cpp
void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");

  // Start calibration pulse
  simulator.startCalibrationPulse();

  // Store command ID for later completion notification
  calibrationCommandId = commandId;
  calibrationRequested = true;
  calibrationStartMillis = millis();

  // Reduced LED flashing (2 flashes instead of 3, 50ms instead of 100ms)
  for (int i = 0; i < 2; i++) {
    digitalWrite(2, HIGH);
    delay(50);
    digitalWrite(2, LOW);
    delay(50);
  }

  // ✅ v5.2.13: NON-BLOCKING - Don't wait! (removed delay(3100))
  // Completion notification will be sent from loop() when calibration finishes
  // This allows waveform streaming and vitals to continue during calibration

  // Send immediate acknowledgment
  sendCommandAck(commandId, true, "Waveform calibration started (non-blocking)");

  Serial.println("✅ Waveform calibration started - data will continue streaming");
}
```

**Total blocking time**: 200ms (down from 3700ms) - **18.5x improvement!**

#### 3. Add completion check to `loop()` (after line 1134):
```cpp
// ✅ v5.2.13: Check if calibration is complete (non-blocking)
if (calibrationRequested && !simulator.isCalibrationActive()) {
  // Calibration just finished
  Serial.println("🎯 Calibration pulse complete - sending completion notification");

  // Read current mode
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;

  // Publish completion notification
  String topic = "hospital/devices/" + deviceId + "/waveform_calibration_complete";
  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["success"] = true;
  doc["duration"] = 3000;
  doc["mode"] = isECGMode ? "ecg" : "eeg";  // ← NEW: Include mode
  doc["commandId"] = calibrationCommandId;

  String payload;
  serializeJson(doc, payload);
  publishWithRetry(topic.c_str(), payload.c_str());

  // Clear flag
  calibrationRequested = false;
  calibrationCommandId = "";

  Serial.println("✅ Calibration completion notification sent");
}
```

---

### Fix #2: Add EEG Calibration Support

**File**: `PhysiologicalSimulator.cpp`
**Function**: `generateEEGSampleWithPhase()` (line 547)

**Changes Required:**

```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ✅ v5.2.13: NEW - Check if calibration pulse is active
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // EEG calibration: 100μV square pulse (1/10th of ECG's 1mV)
        // Extended calibration: 1000ms head → 1000ms pulse → 1000ms tail
        if (elapsed < 1000) {
            // Head: baseline (0mV)
            sample = 8388608;  // ADC midpoint
        } else if (elapsed < 2000) {
            // Pulse: 0.1mV (100μV) square wave
            sample = 8388608 + 10000;  // 100μV above baseline (vs 100000 for ECG 1mV)
        } else {
            // Tail: baseline (0mV)
            sample = 8388608;
        }
        return;  // Skip normal EEG generation during calibration
    }

    // Normal EEG generation (existing code)...
    float amplitude = generateEEGWaveform(eegPhase, channel);
    // ... rest of function unchanged ...
}
```

**Why 100μV for EEG?**
- ECG amplitude: ~1mV (1000μV)
- EEG amplitude: ~100μV (10x smaller)
- Calibration pulse should match waveform scale
- Medical standard: EEG calibration is 50-100μV

---

## BENEFITS

### Before (Current Broken State):
- **Blocking time**: 3,700ms per calibration
- **Waveform packets lost**: ~37 packets (100ms each)
- **Vitals updates lost**: 3-4 updates
- **EEG calibration**: Not supported
- **User experience**: Frozen, confusing

### After (With Fixes):
- **Blocking time**: 200ms per calibration (18.5x faster!)
- **Waveform packets lost**: 2 packets (acceptable)
- **Vitals updates lost**: 0-1 updates
- **EEG calibration**: Fully supported (100μV pulse)
- **User experience**: Smooth, professional

---

## VERSION UPDATE

**Current**: v5.2.12
**Next**: v5.2.13

**Changelog Entry:**
```
✅ v5.2.13: CRITICAL BUGFIX - Non-blocking calibration (removed delay(3100) blocking)
✅ v5.2.13: FEATURE - EEG calibration support (100μV pulse for EEG mode)
✅ v5.2.13: ENHANCEMENT - Mode field in calibration completion message
```

---

## TESTING PLAN

### Test 1: ECG Mode Non-Blocking Calibration

**Setup:**
1. Set watch to ECG mode (GPIO 4 HIGH)
2. Assign patient
3. Open ECG Viewer

**Expected:**
1. Backend sends calibration command
2. ESP32 receives command
3. LED flashes twice quickly (~200ms)
4. **Waveform data continues streaming during calibration** ✅
5. Calibration pulse appears in waveform (3 seconds)
6. After 3 seconds, completion notification sent
7. Normal ECG waveforms continue

**Monitor Serial Output:**
```
🔧 Waveform calibration command received
🔧 Calibration pulse started (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
✅ Waveform calibration started - data will continue streaming
[3 seconds pass - waveforms continue flowing]
🎯 Calibration pulse complete - sending completion notification
✅ Calibration completion notification sent
```

### Test 2: EEG Mode Calibration

**Setup:**
1. Set watch to EEG mode (GPIO 4 LOW)
2. Assign patient
3. Open ECG Viewer (mode mismatch intentional)

**Expected:**
1. Backend sends calibration command
2. ESP32 receives command
3. LED flashes twice
4. **EEG waveform data continues streaming** ✅
5. **Calibration pulse appears in EEG data (100μV amplitude)** ✅
6. Completion message includes `"mode": "eeg"`
7. Normal EEG waveforms continue

### Test 3: Verify No Data Loss

**Monitor backend logs:**
```bash
tail -f hospital-backend/logs/backend.log | grep "waveform\|vitals"
```

**Expected:**
- Waveform stream every 100ms (no gaps)
- Vitals every 1 second (no missed updates)
- Continuous data flow during calibration

---

## FILES TO MODIFY

1. **esp32_hospital_watch_complete.ino**
   - Add calibration tracking globals (after line 226)
   - Modify `handleWaveformCalibrationCommand()` (lines 941-974)
   - Add completion check to `loop()` (after line 1134)
   - Update version to 5.2.13 (line 3)
   - Add changelog entries (lines 30-31)

2. **PhysiologicalSimulator.cpp**
   - Add calibration check to `generateEEGSampleWithPhase()` (after line 547)

---

## PRIORITY

**CRITICAL** - This bug completely breaks the user's workflow.

**User Impact:**
- Cannot use ECG Viewer (waveforms freeze for 3.7 seconds)
- EEG calibration doesn't work at all
- Data loss during calibration

**Fix Difficulty**: EASY - just remove blocking delay and add one `if` statement

---

**STATUS**: Ready to implement - waiting for user approval
