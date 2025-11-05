# Mode-Specific Calibration Bug - ROOT CAUSE FOUND

**Date**: 2025-11-05
**Issue**: Calibration pulse triggers in wrong mode, user gets stuck seeing wrong waveform type
**Symptom**: User opens ECG Viewer, but if watch is in EEG mode, they see calibration pulse briefly then get stuck with EEG waveforms

---

## ROOT CAUSE

The calibration pulse is **NOT mode-aware**. It will trigger regardless of whether the watch is in ECG or EEG mode.

### Evidence: PhysiologicalSimulator.cpp Lines 273-291

```cpp
void PhysiologicalSimulator::generateECGSampleWithPhase(int lead, float phase, int32_t& sample) {
    // ✅ Check if calibration pulse is active (takes priority over normal ECG)
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // Extended calibration: 1000ms head (flat) → 1000ms pulse (1mV) → 1000ms tail (flat)
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
        return;  // Skip normal ECG generation during calibration
    }

    // Generate PQRST complex with given phase
    float amplitude = generatePQRST(phase, lead);
    // ...
}
```

**THE BUG**: This function is called from `fillSampleBuffer()` which checks `if (currentMode == MODE_ECG)` at [line 234](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L234).

**BUT** calibration check happens INSIDE `generateECGSampleWithPhase()` and doesn't verify mode!

---

## WHAT ACTUALLY HAPPENS

### Scenario: Watch is in EEG Mode, User Opens ECG Viewer

1. **Frontend** opens ECG Viewer for patient 081a5294
2. **Frontend** sends WebSocket: `{"type": "subscribePatient", "patientId": "081a5294...", "triggerWaveformCalibration": true}`
3. **Backend** receives request, looks up device: `fit-00001`
4. **Backend** publishes MQTT command: `{"command": "waveformCalibrate", ...}` to `hospital/devices/fit-00001/commands`
5. **ESP32** receives command
6. **ESP32** calls `simulator.startCalibrationPulse()` - sets `calibrationActive = true`
7. **ESP32** continues sending waveforms...
8. **ESP32** reads GPIO pin: `MODE_SELECT_PIN == LOW` → **EEG mode**
9. **ESP32** publishes waveform data with `"mode": "eeg"`

### What fillSampleBuffer() Does (Line 234-264)

```cpp
for (int i = 0; i < 10; i++) {
    if (currentMode == MODE_ECG) {
        // ECG path (not taken because currentMode == MODE_EEG)
        for (int lead = 0; lead < 8; lead++) {
            generateECGSampleWithPhase(lead, phase, buffer[lead][i]);  // ← Has calibration logic
        }
    } else {
        // EEG path (TAKEN)
        for (int channel = 0; channel < 8; channel++) {
            generateEEGSampleWithPhase(channel, buffer[channel][i]);  // ← NO calibration logic!
        }
    }
}
```

**PROBLEM**:
- `generateEEGSampleWithPhase()` does NOT check `isCalibrationActive()`
- Calibration pulse is ONLY injected in ECG mode, not EEG mode
- So even though `calibrationActive = true`, the EEG generator ignores it

---

## ACTUAL BUG: TWO ISSUES

### Issue 1: Calibration Pulse NOT Mode-Aware

**Current behavior**: Calibration command triggers in both modes, but only ECG generator respects it.

**Result**:
- If watch is in ECG mode → calibration pulse works ✅
- If watch is in EEG mode → calibration never appears, EEG continues ❌

### Issue 2: Calibration is Mode-Agnostic Command

**Current behavior**: Backend sends `waveformCalibrate` command without checking watch mode.

**Problem**: Backend doesn't know what mode the watch is currently in!

---

## WHERE THE MODE IS DETERMINED

### ESP32 Hardware Pin

[esp32_hospital_watch_complete.ino:2008](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L2008):

```cpp
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";
```

**Mode is determined by physical GPIO pin** on the ESP32 watch, not by software command.

### Mode-Specific Data Structures

- **ECG Mode** (line 2014-2059): Sends `ecgWaveform` object with `limb` (I, II, III) and `augmented` (aVR, aVL, aVF), `precordial` (V1-V6)
- **EEG Mode** (line 2061-2088): Sends `eegWaveform` object with `frontal` (Fp1, Fp2, F3, F4), `central` (C3, C4), `occipital` (O1, O2)

---

## SOLUTION OPTIONS

### Option 1: Make Calibration Pulse Mode-Specific (RECOMMENDED)

**ECG Calibration**: 1mV square pulse (current behavior)
**EEG Calibration**: 100μV square pulse (scaled for EEG amplitude range)

**Implementation**:
1. Add calibration check to `generateEEGSampleWithPhase()` in [PhysiologicalSimulator.cpp:303](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L303)
2. Generate 100μV calibration pulse for EEG mode (instead of 1mV for ECG)
3. Frontend ECG Viewer detects mode mismatch and warns user

**Pseudo-code**:
```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ✅ NEW: Check if calibration pulse is active
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // EEG calibration: 100μV square pulse (1/10th of ECG)
        if (elapsed < 1000) {
            sample = 8388608;  // Baseline
        } else if (elapsed < 2000) {
            sample = 8388608 + 10000;  // 100μV pulse (vs 1mV for ECG)
        } else {
            sample = 8388608;  // Baseline
        }
        return;
    }

    // Normal EEG generation...
    float amplitude = generateEEGWaveform(eegPhase, channel);
    // ...
}
```

### Option 2: Backend Tracks Watch Mode

**Implementation**:
1. Backend stores `currentMode` for each device (from waveform stream messages)
2. Backend only sends `waveformCalibrate` if mode matches viewer type
3. If mode mismatch, backend returns error to frontend

**Problem**: Adds complexity, requires database schema changes, mode could change between check and command.

### Option 3: Frontend Checks Mode Before Requesting Calibration

**Implementation**:
1. Frontend receives waveform data with `"mode": "ecg"` or `"mode": "eeg"`
2. ECG Viewer checks if mode == "ecg" before sending calibration request
3. If mode mismatch, show warning: "Device is in EEG mode, please switch to ECG mode"

**Problem**: User won't see calibration pulse until they physically flip the watch mode switch.

---

## RECOMMENDED FIX: Combination Approach

### Part 1: ESP32 - Add EEG Calibration Support

**File**: `PhysiologicalSimulator.cpp`

**Change**: Add calibration pulse to `generateEEGSampleWithPhase()` (lines 303-329)

**Benefit**: Calibration works in both modes

### Part 2: ESP32 - Send Mode in Calibration Completion Message

**File**: `esp32_hospital_watch_complete.ino` line 959

**Change**:
```cpp
// BEFORE
String topic = "hospital/devices/" + deviceId + "/waveform_calibration_complete";
JsonDocument doc;
doc["timestamp"] = getISO8601Timestamp();
doc["success"] = true;
doc["duration"] = 3000;

// AFTER
String topic = "hospital/devices/" + deviceId + "/waveform_calibration_complete";
JsonDocument doc;
doc["timestamp"] = getISO8601Timestamp();
doc["success"] = true;
doc["duration"] = 3000;
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";  // ← NEW: Include mode
```

**Benefit**: Backend/Frontend knows what mode the calibration pulse was generated in

### Part 3: Frontend - Detect Mode Mismatch

**File**: `ECGViewerContainer.tsx` or `useECGViewer.ts`

**Change**: Check if waveform data mode matches viewer type

```typescript
// When receiving waveform data:
if (waveformData.mode !== 'ecg') {
  console.warn(`⚠️ ECG Viewer received ${waveformData.mode.toUpperCase()} mode data - device mode mismatch!`);
  // Show warning to user: "Device is in EEG mode. Please switch to ECG mode on the watch."
}
```

**Benefit**: User understands why they're seeing wrong waveform type

---

## TESTING PLAN

### Test Case 1: ECG Mode Calibration (Current Behavior)

1. Set watch to ECG mode (MODE_SELECT_PIN = HIGH)
2. Open ECG Viewer
3. **Expected**: Calibration pulse appears (1mV square wave)
4. **Expected**: ECG waveforms appear after calibration

### Test Case 2: EEG Mode Calibration (NEW Behavior)

1. Set watch to EEG mode (MODE_SELECT_PIN = LOW)
2. Open ECG Viewer (mode mismatch)
3. **Expected**: Calibration pulse appears (100μV square wave)
4. **Expected**: EEG waveforms appear after calibration
5. **Expected**: Frontend shows warning: "Device is in EEG mode"

### Test Case 3: Mode Switch During Calibration

1. Set watch to ECG mode
2. Open ECG Viewer
3. Flip mode switch to EEG during calibration pulse
4. **Expected**: Calibration completes in mode it started in
5. **Expected**: After calibration, waveforms switch to new mode

---

## FILES TO MODIFY

1. **esp32_hospital_watch_complete/PhysiologicalSimulator.cpp**
   - Add calibration logic to `generateEEGSampleWithPhase()` (line 303)

2. **esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino**
   - Add `"mode"` field to calibration completion message (line 959)

3. **hospital-display-app/src/hooks/useECGViewer.ts**
   - Add mode mismatch detection when receiving waveform data

---

## PRIORITY

**MEDIUM** - This is a UX issue, not a critical bug.

**Impact**: Users might be confused why they see wrong waveform type after requesting calibration.

**Workaround**: User can physically flip the mode switch on the watch before opening ECG Viewer.

---

## USER'S QUESTION ANSWERED

> "isnt there mode specific calibration? why do i get stuck in ecg?"

**Answer**:

YES, there SHOULD be mode-specific calibration, but currently:

1. Calibration pulse is only implemented in ECG mode generator
2. EEG mode generator ignores calibration flag completely
3. Backend sends calibration command without knowing watch mode
4. If watch is in EEG mode when ECG Viewer opens, you get stuck seeing EEG waveforms because:
   - Calibration command triggers
   - But calibration pulse never appears (EEG generator doesn't have it)
   - Watch continues sending EEG mode waveforms
   - Frontend displays wrong waveform type

**Fix**: Implement calibration pulse in both ECG and EEG generators, with mode-appropriate amplitudes.
