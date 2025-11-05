# Calibration No Waveform Issue - Current Situation

**Date**: 2025-11-05
**User Report**: "no calibration no waveform after watch receives the command"
**Current Status**: Investigating

---

## What User Is Experiencing

**Symptoms:**
1. User opens ECG/EEG full screen viewer
2. Watch receives calibration command (visible on watch screen/LED)
3. **NO waveform data flows** - screen stays blank
4. No calibration pulse appears
5. No normal waveforms appear

**Expected Behavior:**
1. Watch receives calibration command
2. Calibration pulse appears (3-second pulse)
3. Normal waveforms resume after calibration

---

## Current File Status

### ⚠️ SOURCE CODE ISSUE

The `.ino` file was accidentally reset to v5.0.0 (old version) while investigating:

```bash
$ head -3 esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
/*
 * ESP32 Hospital Watch - Certificate-Based Authentication
 * Version: 5.0.0
```

**V5.0.0 DOES NOT HAVE:**
- Waveform streaming
- PhysiologicalSimulator integration
- Mode selection (ECG/EEG)
- Delta encoding
- Proper calibration handler

### ✅ SIMULATOR FILES INTACT

The simulator files (742 lines) are still present and have all the code:
- `PhysiologicalSimulator.cpp` - Has `startCalibrationPulse()`, `isCalibrationActive()`, etc.
- All other simulator files intact (ADS1298, MAX86178, BMI323, STS40, NFC)

---

## Two Possible Scenarios

### Scenario A: Watch Has OLD Firmware (v5.0)

**If watch actually has v5.0 flashed:**
- Would explain why no waveforms flow
- v5.0 has placeholder waveform function that just prints debug messages
- Calibration handler in v5.0 has `delay(3000)` blocking bug

**Evidence Against:**
- User was getting waveforms working before
- User mentioned EEG mode working
- v5.0 doesn't have mode selection

**Likelihood:** LOW - user was clearly using v5.2.x features

### Scenario B: Watch Has NEW Firmware (v5.2.x) But Has Bug

**If watch actually has v5.2.10+ flashed:**
- Source files got reset but watch firmware is still correct
- The bug is in the v5.2.x calibration handler itself

**Possible bugs in v5.2.x calibration:**
1. **Blocking delay** - `delay(3100)` at line 956 freezes ESP32 for 3+ seconds
2. **Mode-specific calibration** - EEG mode doesn't check calibration flag
3. **MQTT/WiFi disconnect** during calibration blocking period

**Likelihood:** HIGH - matches user's description

---

## Diagnostic Questions for User

To determine what's actually happening, need to know:

1. **What firmware version is currently on the watch?**
   - Check Serial Monitor when watch boots
   - Should print "Version: X.X.X"

2. **Were you getting waveforms BEFORE the calibration command?**
   - If YES: Watch has v5.2.x firmware, calibration breaks it
   - If NO: Different issue entirely

3. **After calibration command fails, do waveforms resume if you close and reopen viewer?**
   - If YES: Calibration temporarily breaks streaming
   - If NO: Calibration permanently breaks something

4. **What mode is the watch in (ECG or EEG)?**
   - GPIO pin 4 HIGH = ECG mode
   - GPIO pin 4 LOW = EEG mode

5. **What do you see in ESP32 Serial Monitor when calibration command is received?**
   - Should show: "🔧 Waveform calibration command received"
   - Then what happens?

---

## Known Bugs in v5.2.x Calibration

### Bug #1: Blocking Delay (CRITICAL)

**File:** `esp32_hospital_watch_complete.ino` line 956
**Code:**
```cpp
void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");
  simulator.startCalibrationPulse();

  // LED flashing (600ms blocking)
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  // ❌ BUG: 3.1 second blocking delay!
  delay(3100);

  // ... completion notification
}
```

**Impact:**
- ESP32 completely frozen for 3.7 seconds total
- NO waveform streaming during this time
- NO vitals publishing
- NO MQTT message processing
- User sees blank screen

### Bug #2: Mode-Specific Calibration

**File:** `PhysiologicalSimulator.cpp` line 303

**Code:**
```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ❌ BUG: Doesn't check isCalibrationActive()!

    // Normal EEG generation...
    float amplitude = generateEEGWaveform(eegPhase, channel);
    // ...
}
```

**Impact:**
- Calibration pulse only works in ECG mode
- EEG mode ignores calibration flag completely
- If watch is in EEG mode, calibration never appears

---

## Recommended Actions

### Step 1: Check Watch Firmware Version

Ask user to check Serial Monitor output when watch boots to confirm version.

### Step 2: If v5.2.x, Check Serial Monitor During Calibration

Watch for these messages:
```
🔧 Waveform calibration command received
🔧 Calibration pulse started (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
✅ Waveform calibration complete - waveforms will contain calibration data
```

**If all three appear:** Calibration handler is executing but blocking for 3+ seconds

**If only first appears:** Handler is crashing or blocking forever

### Step 3: Check Waveform Streaming During Calibration

Watch backend logs for waveform stream messages during calibration:
```bash
tail -f hospital-backend/logs/backend.log | grep "waveform"
```

**If streams stop:** Confirms blocking delay bug

**If streams continue:** Different issue (not blocking delay)

### Step 4: Check Mode

Ask user what mode watch is in:
- Physical GPIO pin state
- Or check waveform data `"mode": "ecg"` vs `"mode": "eeg"`

**If EEG mode:** Bug #2 (EEG calibration not implemented)

**If ECG mode:** Bug #1 (blocking delay)

---

## Immediate Workaround

**Disable calibration temporarily:**

### Option 1: Backend Side (Quick)

Comment out calibration trigger in `websocket.py`:

```python
# Line 288-298: Comment out
# if triggerWaveformCalibration:
#     await _triggerWaveformCalibration(deviceId, patientId)
```

**Result:** No calibration command sent, waveforms flow normally

### Option 2: Frontend Side (Quick)

Remove `triggerWaveformCalibration` from WebSocket message:

```typescript
// ECGViewerContainer.tsx or useECGViewer.ts
ws.send(JSON.stringify({
  type: 'subscribePatient',
  patientId: patient.patientId,
  // triggerWaveformCalibration: true  // ← Comment out
}));
```

**Result:** User can view waveforms without calibration pulse

---

## Permanent Fix (After Diagnosis)

Once we know which firmware version and which bug:

### Fix #1: Remove Blocking Delay

Change calibration handler to non-blocking:
- Remove `delay(3100)`
- Add completion tracking in `loop()`
- Total blocking time: 200ms (vs 3700ms)

### Fix #2: Add EEG Calibration Support

Add calibration check to EEG generator:
```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ✅ NEW: Check calibration
    if (isCalibrationActive()) {
        // Generate 100μV calibration pulse (1/10th of ECG's 1mV)
        // ...
        return;
    }

    // Normal EEG generation...
}
```

---

## Next Steps

1. **URGENT:** Ask user to check watch firmware version
2. **URGENT:** Get Serial Monitor output during calibration attempt
3. **URGENT:** Check if waveforms were working before calibration
4. Based on answers, apply appropriate fix

---

## Documentation References

- [CALIBRATION_BLOCKING_DELAY_BUG.md](CALIBRATION_BLOCKING_DELAY_BUG.md) - Blocking delay details
- [MODE_SPECIFIC_CALIBRATION_BUG_DIAGNOSIS.md](MODE_SPECIFIC_CALIBRATION_BUG_DIAGNOSIS.md) - Mode-specific calibration
- [EEG_TIMING_FIX_COMPLETE_V5_2_10.md](EEG_TIMING_FIX_COMPLETE_V5_2_10.md) - Latest known working version

---

**STATUS:** Awaiting user information to diagnose root cause
