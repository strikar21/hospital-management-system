# Implementation Plan - Non-Blocking Calibration v5.2.13

**Date**: 2025-11-05
**Current Version**: v5.2.12
**Target Version**: v5.2.13
**Priority**: CRITICAL - Blocks user workflow

---

## OBJECTIVE

Fix two critical bugs in waveform calibration system:
1. **Blocking delay** - Remove `delay(3100)` that freezes ESP32 for 3.7 seconds
2. **Missing EEG calibration** - Add calibration pulse support for EEG mode

---

## CURRENT STATE ANALYSIS

### Bug #1: Blocking Delay

**File**: `esp32_hospital_watch_complete.ino`
**Location**: Lines 941-974
**Function**: `handleWaveformCalibrationCommand()`

**Current Code Flow**:
```
1. Receive calibration command
2. Call simulator.startCalibrationPulse()
3. Flash LED 3 times (600ms blocking)
4. delay(3100) ← BLOCKS EVERYTHING
5. Publish completion message
6. Send ACK
```

**Problem**: During step 4 (3100ms):
- ❌ loop() doesn't run
- ❌ No waveform streaming
- ❌ No vitals publishing
- ❌ No MQTT processing
- ❌ No WiFi management

**Evidence from user**: "no calibration no waveform after watch receives the command"

### Bug #2: Missing EEG Calibration

**File**: `PhysiologicalSimulator.cpp`
**Location**: Lines 547-572
**Function**: `generateEEGSampleWithPhase()`

**Current Code**: Does NOT check `isCalibrationActive()`

**Compare with ECG**:
- ECG generator (line 274): ✅ Has `if (isCalibrationActive())` check
- EEG generator (line 547): ❌ Missing calibration check

**Impact**: Calibration only works in ECG mode, not EEG mode

---

## SOLUTION DESIGN

### Part 1: Non-Blocking Calibration

**Approach**: Use state machine pattern with completion tracking

**Key Insight**: PhysiologicalSimulator ALREADY has non-blocking calibration!
- `startCalibrationPulse()` sets flag and start time
- `isCalibrationActive()` checks if 3000ms elapsed
- Automatically turns off calibration after 3 seconds

**Handler doesn't need to wait - simulator handles timing!**

### Part 2: EEG Calibration Support

**Approach**: Add calibration check to EEG generator (copy ECG pattern)

**Calibration Pulse Specifications**:
- **ECG**: 1mV (1000μV) square pulse - ADC offset +100000
- **EEG**: 100μV square pulse - ADC offset +10000 (1/10th of ECG)

**Medical Rationale**:
- ECG signals: typically 0.5-5mV
- EEG signals: typically 10-100μV (10x smaller)
- Calibration should match signal amplitude range

---

## IMPLEMENTATION PLAN

### STEP 1: Add Calibration Tracking Variables

**File**: `esp32_hospital_watch_complete.ino`
**Location**: After line 226 (after `bool waveformCalibrationDue = false;`)

**Add**:
```cpp
bool calibrationRequested = false;
String calibrationCommandId = "";
unsigned long calibrationStartMillis = 0;
```

**Purpose**:
- `calibrationRequested`: Flag to check in loop() if calibration is in progress
- `calibrationCommandId`: Store command ID for completion notification
- `calibrationStartMillis`: Track when calibration started (for timeout/debugging)

---

### STEP 2: Modify Calibration Handler (Non-Blocking)

**File**: `esp32_hospital_watch_complete.ino`
**Location**: Lines 941-974
**Function**: `handleWaveformCalibrationCommand()`

**Current Code** (TO REPLACE):
```cpp
void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");

  // ✅ Trigger physiological simulator waveform calibration (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
  simulator.startCalibrationPulse();

  // Flash LED to indicate waveform calibration in progress (non-blocking pattern)
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  // Wait for waveform calibration to complete (3000ms + margin)
  delay(3100);  // ← REMOVE THIS!

  // Publish completion notification
  String topic = "hospital/devices/" + deviceId + "/waveform_calibration_complete";
  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["success"] = true;
  doc["duration"] = 3000;  // ms (1000ms head + 1000ms pulse + 1000ms tail)

  String payload;
  serializeJson(doc, payload);
  publishWithRetry(topic.c_str(), payload.c_str());  // ✅ v5.2.1: QoS 1 with retry

  waveformCalibrationDue = false;
  sendCommandAck(commandId, true, "Waveform calibration sent to all ECG leads (3000ms)");

  Serial.println("✅ Waveform calibration complete - waveforms will contain calibration data");
  digitalWrite(2, HIGH);
}
```

**New Code** (REPLACEMENT):
```cpp
void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");

  // ✅ Trigger physiological simulator waveform calibration (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
  simulator.startCalibrationPulse();

  // Store command ID and set flag for non-blocking completion tracking
  calibrationCommandId = commandId;
  calibrationRequested = true;
  calibrationStartMillis = millis();

  // Flash LED to indicate waveform calibration started (reduced blocking: 2 flashes × 100ms = 200ms)
  for (int i = 0; i < 2; i++) {
    digitalWrite(2, HIGH);
    delay(50);  // Reduced from 100ms to 50ms
    digitalWrite(2, LOW);
    delay(50);  // Reduced from 100ms to 50ms
  }

  // ✅ v5.2.13: NON-BLOCKING - Don't wait for calibration to complete!
  // Completion notification will be sent from loop() when simulator.isCalibrationActive() returns false
  // This allows waveform streaming, vitals publishing, and MQTT processing to continue during calibration

  // Send immediate acknowledgment
  sendCommandAck(commandId, true, "Waveform calibration started (non-blocking, 3000ms duration)");

  Serial.println("✅ Waveform calibration started - data streaming continues during calibration");
}
```

**Changes**:
1. ✅ Store `commandId` for later use
2. ✅ Set `calibrationRequested = true` flag
3. ✅ Record start time
4. ✅ Reduce LED flashing: 2 flashes (200ms) instead of 3 flashes (600ms)
5. ❌ **REMOVED**: `delay(3100)`
6. ✅ Send immediate ACK instead of waiting
7. ✅ Updated log message

**Total blocking time**: 200ms (down from 3700ms) - **18.5x improvement**

---

### STEP 3: Add Completion Check to loop()

**File**: `esp32_hospital_watch_complete.ino`
**Location**: After line 1134 (in main `loop()` function, after alert checks)

**Add** (NEW CODE):
```cpp
  // ✅ v5.2.13: Check if non-blocking calibration is complete
  if (calibrationRequested && !simulator.isCalibrationActive()) {
    // Calibration pulse just finished (3000ms elapsed)
    Serial.println("🎯 Waveform calibration pulse complete - sending completion notification");

    // Read current mode from GPIO pin
    bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;

    // Publish completion notification with mode information
    String topic = "hospital/devices/" + deviceId + "/waveform_calibration_complete";
    JsonDocument doc;
    doc["timestamp"] = getISO8601Timestamp();
    doc["success"] = true;
    doc["duration"] = 3000;  // ms (1000ms head + 1000ms pulse + 1000ms tail)
    doc["mode"] = isECGMode ? "ecg" : "eeg";  // ✅ v5.2.13: Include current mode
    doc["commandId"] = calibrationCommandId;

    String payload;
    serializeJson(doc, payload);
    publishWithRetry(topic.c_str(), payload.c_str());

    // Clear calibration tracking flags
    calibrationRequested = false;
    calibrationCommandId = "";

    Serial.println("✅ Waveform calibration completion notification sent");
  }
```

**Logic Flow**:
1. Check if calibration was requested (`calibrationRequested == true`)
2. Check if calibration finished (`simulator.isCalibrationActive() == false`)
3. If both true: calibration just completed
4. Read current mode from GPIO pin
5. Publish completion message with mode field
6. Clear tracking flags

**Placement**: This runs every loop iteration (~100ms), so completion is detected quickly after 3-second calibration finishes.

---

### STEP 4: Add EEG Calibration Support

**File**: `esp32_hospital_watch_complete/PhysiologicalSimulator.cpp`
**Location**: Line 547 (function `generateEEGSampleWithPhase()`)

**Current Code** (FIRST PART):
```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // Generate waveform based on activity state and channel (using current phase)
    float amplitude = generateEEGWaveform(eegPhase, channel);

    // ... rest of function ...
}
```

**New Code** (INSERT AT START OF FUNCTION):
```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ✅ v5.2.13: Check if calibration pulse is active (takes priority over normal EEG)
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // EEG calibration: 100μV square pulse (1/10th of ECG's 1mV pulse)
        // Extended calibration: 1000ms head (flat) → 1000ms pulse (100μV) → 1000ms tail (flat)
        if (elapsed < 1000) {
            // Head: baseline (0mV)
            sample = 8388608;  // ADC midpoint (24-bit)
        } else if (elapsed < 2000) {
            // Pulse: 0.1mV (100μV) square wave
            sample = 8388608 + 10000;  // 100μV above baseline (vs 100000 for ECG 1mV)
        } else {
            // Tail: baseline (0mV)
            sample = 8388608;
        }
        return;  // Skip normal EEG generation during calibration
    }

    // Normal EEG generation (existing code below)...
    float amplitude = generateEEGWaveform(eegPhase, channel);

    // ... rest of function unchanged ...
}
```

**Changes**:
1. ✅ Add calibration check at start of function (matches ECG pattern)
2. ✅ Generate 100μV pulse (appropriate for EEG scale)
3. ✅ Same timing as ECG: 1000ms head → 1000ms pulse → 1000ms tail
4. ✅ Return early if calibration active (skip normal generation)
5. ✅ Existing code unchanged (just moved after calibration check)

**Medical Accuracy**:
- ECG: 1000μV pulse = ADC +100000 (0.5-5mV range)
- EEG: 100μV pulse = ADC +10000 (10-100μV range)
- Ratio: 10:1 (matches physiological amplitude difference)

---

### STEP 5: Update Version and Changelog

**File**: `esp32_hospital_watch_complete.ino`

**Line 3** (Version):
```cpp
// CURRENT:
 * Version: 5.2.12

// CHANGE TO:
 * Version: 5.2.13
```

**Lines 30-31** (Add changelog entries):
```cpp
 * - ✅ v5.2.11: MEDICAL ACCURACY FIX - Channel-specific frequency mixing (frontal=beta, occipital=alpha)
 * - ✅ v5.2.12: CRITICAL BUGFIX - Simulator mode was only set once at boot, never updated when GPIO pin changed
 * - ✅ v5.2.13: CRITICAL BUGFIX - Non-blocking calibration (removed delay(3100) that froze ESP32 for 3.7s)
 * - ✅ v5.2.13: FEATURE - EEG calibration support (100μV pulse for EEG mode, 1mV pulse for ECG mode)
 * - ✅ v5.2.13: ENHANCEMENT - Mode field in calibration completion message for frontend awareness
```

**Lines 68-70** (Add to changes list):
```cpp
 * ✅ v5.2.12: Result: Mode switching now works correctly - waveforms match the current GPIO pin state
 * ✅ v5.2.13: CRITICAL FIX - Calibration handler no longer blocks (delay removed, completion tracked in loop)
 * ✅ v5.2.13: Bug: handleWaveformCalibrationCommand() used delay(3100) → froze all operations for 3.7s
 * ✅ v5.2.13: Fix: Non-blocking state machine with completion check in loop() → 200ms blocking only
 * ✅ v5.2.13: Result: Waveforms stream continuously during calibration, no data loss, better UX
 * ✅ v5.2.13: FEATURE - EEG calibration pulse (100μV) now works alongside ECG calibration (1mV)
 */
```

---

## TESTING PLAN

### Pre-Test Verification

**Before flashing firmware**:
1. ✅ Check all files are saved
2. ✅ Verify Arduino IDE compiles without errors
3. ✅ Confirm ESP32 board selection (ESP32 Dev Module)
4. ✅ Check COM port is correct

### Test 1: ECG Mode Non-Blocking Calibration

**Setup**:
1. Set watch GPIO 4 to HIGH (ECG mode)
2. Assign watch to patient
3. Open backend logs: `tail -f hospital-backend/logs/backend.log`
4. Open ESP32 Serial Monitor (115200 baud)

**Actions**:
1. Open ECG Viewer in frontend
2. Frontend should send calibration request

**Expected Results**:

**Backend logs**:
```
📤 Command sent to fit-00001: {'command': 'waveformCalibrate', ...}
```

**ESP32 Serial Monitor**:
```
🔧 Waveform calibration command received
🔧 Calibration pulse started (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
✅ Waveform calibration started - data streaming continues during calibration
[... waveform and vitals messages continue every 100ms/1s ...]
🎯 Waveform calibration pulse complete - sending completion notification
✅ Waveform calibration completion notification sent
```

**Frontend**:
- Waveforms continue flowing (no freeze)
- Calibration pulse visible: 1-second flat → 1-second 1mV pulse → 1-second flat
- Total duration: 3 seconds
- Normal ECG resumes after calibration

**Key Verification**:
- ✅ No 3.7-second freeze
- ✅ Waveform data continues during calibration
- ✅ Vitals continue publishing
- ✅ Calibration pulse appears correctly

### Test 2: EEG Mode Calibration (NEW FEATURE)

**Setup**:
1. Set watch GPIO 4 to LOW (EEG mode)
2. Watch still assigned to same patient
3. Open ECG Viewer (mode mismatch intentional for testing)

**Actions**:
1. Frontend sends calibration request

**Expected Results**:

**ESP32 Serial Monitor**:
```
🔧 Waveform calibration command received
🔧 Calibration pulse started (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
✅ Waveform calibration started - data streaming continues during calibration
[... EEG waveform messages continue ...]
🎯 Waveform calibration pulse complete - sending completion notification
✅ Waveform calibration completion notification sent
```

**Waveform data**:
```json
{
  "mode": "eeg",
  "eegWaveform": {
    "frontal": {...},
    "central": {...},
    "occipital": {...}
  }
}
```

**Calibration completion**:
```json
{
  "timestamp": "2025-11-05T...",
  "success": true,
  "duration": 3000,
  "mode": "eeg"  // ← NEW FIELD
}
```

**Frontend**:
- EEG waveforms continue flowing
- Calibration pulse visible: 1-second flat → 1-second 100μV pulse → 1-second flat
- Pulse is 1/10th amplitude of ECG pulse (as expected for EEG)
- Normal EEG resumes after calibration

**Key Verification**:
- ✅ EEG calibration works (previously didn't)
- ✅ 100μV pulse (not 1mV)
- ✅ Mode field in completion message
- ✅ No data freeze

### Test 3: Continuous Streaming Verification

**Setup**:
1. Watch assigned to patient (either mode)
2. Monitor backend logs with timestamp

**Actions**:
1. Trigger calibration
2. Watch for gaps in waveform stream messages

**Expected Results**:

**Backend logs** (excerpt):
```
2025-11-05 01:00:00.000 - Waveform stream received: fit-00001
2025-11-05 01:00:00.100 - Waveform stream received: fit-00001
2025-11-05 01:00:00.200 - Waveform stream received: fit-00001
[calibration triggered at 01:00:00.250]
2025-11-05 01:00:00.300 - Waveform stream received: fit-00001  ← No gap!
2025-11-05 01:00:00.400 - Waveform stream received: fit-00001
2025-11-05 01:00:00.500 - Waveform stream received: fit-00001
[... continues every 100ms throughout 3-second calibration ...]
2025-11-05 01:00:03.300 - Waveform stream received: fit-00001
```

**Key Verification**:
- ✅ Waveform messages every 100ms (no gaps)
- ✅ Vitals messages every 1 second (no missed updates)
- ✅ No 3.7-second gap in logs

### Test 4: Mode Switching During Calibration

**Setup**:
1. Watch in ECG mode, assigned to patient
2. Have physical access to watch GPIO pin

**Actions**:
1. Trigger calibration
2. During calibration (within 3 seconds), flip GPIO pin from HIGH to LOW
3. Observe what happens

**Expected Results**:
- Calibration continues in mode it started (ECG)
- After calibration completes, waveforms switch to new mode (EEG)
- No crash or data corruption

**Key Verification**:
- ✅ System handles mode change gracefully
- ✅ Calibration completes properly
- ✅ Mode switches after calibration

---

## ROLLBACK PLAN

If bugs are discovered after flashing v5.2.13:

### Option 1: Disable Calibration (Quick Fix)

**Backend Side** - Comment out calibration trigger:
```python
# File: hospital-backend/app/api/v1/websocket.py
# Line 135
# await _triggerWaveformCalibration(deviceId, patientId)  # ← Comment out
```

**Result**: No calibration sent, waveforms work normally

### Option 2: Revert to v5.2.12

**Keep backup of v5.2.12 firmware**:
1. Before flashing v5.2.13, save current .ino file as `.ino.v5.2.12.backup`
2. If issues arise, restore backup and re-flash

### Option 3: Hot-patch Specific Issue

If only one part fails:
- **Calibration still blocks**: Revert Step 2 only (handler function)
- **EEG calibration broken**: Revert Step 4 only (simulator change)
- **Completion not working**: Revert Step 3 only (loop check)

---

## SUCCESS CRITERIA

**Must Pass**:
1. ✅ Calibration command received by ESP32
2. ✅ Waveforms continue streaming during calibration (no 3.7s freeze)
3. ✅ Vitals continue publishing during calibration
4. ✅ Calibration pulse appears in ECG mode (1mV, 3 seconds)
5. ✅ Calibration pulse appears in EEG mode (100μV, 3 seconds)
6. ✅ Completion message sent after 3 seconds
7. ✅ Completion message includes mode field

**Should Pass**:
1. ✅ LED flashes briefly (200ms) at calibration start
2. ✅ Serial Monitor shows non-blocking messages
3. ✅ No MQTT disconnections during calibration
4. ✅ Mode switching handled gracefully

**Nice to Have**:
1. ✅ Frontend displays mode mismatch warning if viewer/watch modes differ
2. ✅ Calibration pulse renders correctly on canvas (proper amplitude)
3. ✅ Backend logs show continuous data flow

---

## RISK ASSESSMENT

### Low Risk Changes

✅ **Adding global variables** (Step 1)
- No behavioral change
- Just storage for tracking

✅ **Adding loop() check** (Step 3)
- Only executes if flag is set
- Doesn't affect normal operation

### Medium Risk Changes

⚠️ **Modifying calibration handler** (Step 2)
- Changes core behavior
- Must ensure ACK still sent
- LED timing changed

**Mitigation**: Test thoroughly, keep backup

### High Risk Changes

⚠️ **EEG calibration** (Step 4)
- Modifies waveform generation
- Could affect normal EEG if logic wrong

**Mitigation**:
- Logic identical to ECG (proven working)
- Early return prevents affecting normal generation
- Amplitude scaled appropriately

---

## POST-IMPLEMENTATION CHECKLIST

After flashing firmware:

- [ ] ESP32 boots successfully
- [ ] WiFi connects
- [ ] MQTT connects
- [ ] Vitals publish normally
- [ ] Waveforms stream normally
- [ ] Calibration request received
- [ ] No 3.7-second freeze observed
- [ ] Calibration pulse appears in ECG mode
- [ ] Calibration pulse appears in EEG mode
- [ ] Completion message received
- [ ] Mode field present in completion message
- [ ] No crashes or errors in Serial Monitor
- [ ] Backend logs show continuous data flow
- [ ] Frontend displays waveforms correctly

---

## FILES TO MODIFY (SUMMARY)

1. **esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino**
   - Line 226: Add calibration tracking variables
   - Lines 941-974: Replace `handleWaveformCalibrationCommand()`
   - After line 1134: Add completion check to `loop()`
   - Line 3: Update version to 5.2.13
   - Lines 30-31, 68-70: Add changelog entries

2. **esp32_hospital_watch_complete/PhysiologicalSimulator.cpp**
   - Line 547: Add calibration check to `generateEEGSampleWithPhase()`

**Total lines changed**: ~80 lines
**Total files changed**: 2 files

---

## TIMELINE

**Estimated time**: 30 minutes

- 10 min: Make code changes
- 5 min: Compile and verify
- 10 min: Flash and test
- 5 min: Verify all functionality

---

**STATUS**: Plan complete - ready for implementation
**APPROVAL REQUIRED**: Yes - user should review plan before execution
