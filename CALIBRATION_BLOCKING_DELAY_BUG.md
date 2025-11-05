# Calibration Blocking Delay Bug - CRITICAL

**Date**: 2025-11-05
**Severity**: CRITICAL - Blocks all ESP32 operations for 3+ seconds
**Issue**: `delay(3100)` in calibration handler freezes ESP32 completely

---

## ROOT CAUSE

[esp32_hospital_watch_complete.ino:941-974](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L941-L974):

```cpp
void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");

  // ✅ Trigger physiological simulator waveform calibration
  simulator.startCalibrationPulse();  // Sets calibrationActive = true

  // Flash LED to indicate waveform calibration in progress (non-blocking pattern)
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);   // ← 100ms blocking
    digitalWrite(2, LOW);
    delay(100);   // ← 100ms blocking
  }

  // Wait for waveform calibration to complete (3000ms + margin)
  delay(3100);  // ← ❌ CRITICAL BUG: 3.1 SECOND BLOCKING DELAY!

  // Publish completion notification
  String topic = "hospital/devices/" + deviceId + "/waveform_calibration_complete";
  // ...
  publishWithRetry(topic.c_str(), payload.c_str());

  waveformCalibrationDue = false;
  sendCommandAck(commandId, true, "Waveform calibration sent to all ECG leads (3000ms)");

  Serial.println("✅ Waveform calibration complete - waveforms will contain calibration data");
  digitalWrite(2, HIGH);
}
```

---

## WHAT HAPPENS DURING `delay(3100)`

### ESP32 is COMPLETELY BLOCKED:

1. ❌ **No waveform streaming** - `loop()` doesn't run, so `publishWaveformStream()` never gets called
2. ❌ **No vitals publishing** - 1-second vitals timer doesn't fire
3. ❌ **No MQTT messages processed** - Can't receive assign/unassign/other commands
4. ❌ **No WiFi management** - Connection could drop
5. ❌ **No NTP time sync** - Clock could drift
6. ❌ **No MQTT keepalive** - Broker might disconnect

### User Experience:

- **Frontend**: Sends calibration request
- **ESP32**: Receives command, LED flashes
- **Frontend**: Waveform data stops flowing for 3+ seconds (appears frozen)
- **Frontend**: After 3 seconds, waveform data resumes
- **User**: "Why is my data frozen? Is the watch broken?"

---

## WHY THIS BUG EXISTS

### Historical Context:

The calibration handler was designed with a **synchronous blocking approach**:

1. Start calibration pulse (`calibrationActive = true`)
2. Wait for pulse to complete (3100ms)
3. Publish completion notification
4. Return to normal operations

**Problem**: Arduino `delay()` is BLOCKING - nothing else can run!

---

## THE CORRECT APPROACH

The calibration pulse is **already asynchronous** in the PhysiologicalSimulator:

[PhysiologicalSimulator.cpp:255-267](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L255-L267):

```cpp
bool PhysiologicalSimulator::isCalibrationActive() {
    if (!calibrationActive) return false;

    // Check if 3000ms has elapsed
    unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);
    if (elapsed >= calibrationDuration) {
        calibrationActive = false;
        Serial.println("✅ Calibration pulse complete");
        return false;
    }

    return true;
}
```

**The simulator automatically turns off calibration after 3000ms!**

So the handler doesn't need to wait - it should:
1. Start calibration pulse
2. Return immediately (non-blocking)
3. Schedule completion notification for later

---

## SOLUTION: NON-BLOCKING CALIBRATION

### Step 1: Remove Blocking Delay

**File**: `esp32_hospital_watch_complete.ino`

**Change**:
```cpp
void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");

  // ✅ Trigger physiological simulator waveform calibration
  simulator.startCalibrationPulse();  // Sets calibrationActive = true

  // Store command ID for completion notification
  calibrationCommandId = commandId;  // ← NEW: Store for later
  calibrationRequested = true;       // ← NEW: Flag for completion tracking

  // Flash LED to indicate waveform calibration in progress (reduce from 600ms to 200ms)
  for (int i = 0; i < 2; i++) {  // ← Changed from 3 to 2 flashes
    digitalWrite(2, HIGH);
    delay(50);   // ← Reduced from 100ms to 50ms
    digitalWrite(2, LOW);
    delay(50);   // ← Reduced from 100ms to 50ms
  }

  // ❌ REMOVED: delay(3100);  // Don't block!

  // Send immediate acknowledgment
  sendCommandAck(commandId, true, "Waveform calibration started");

  Serial.println("✅ Waveform calibration started (non-blocking)");
}
```

**Total blocking time**: 200ms (down from 3700ms) - 18.5x improvement!

### Step 2: Add Calibration Completion Tracking

**Add global variables** (near line 226):

```cpp
bool calibrationRequested = false;
String calibrationCommandId = "";
unsigned long calibrationStartMillis = 0;
```

### Step 3: Check Calibration Completion in loop()

**Add to main loop()** (after line 1134):

```cpp
void loop() {
  // ... existing code ...

  // ✅ NEW: Check if calibration is complete (non-blocking)
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

  // ... rest of loop ...
}
```

---

## BENEFITS

### Before (Blocking):
- **Total freeze time**: 3700ms (3.1s delay + 600ms LED flashing)
- **Waveform packets lost**: ~37 packets (100ms each)
- **Vitals updates missed**: 3-4 updates (1 per second)
- **User experience**: Data appears frozen, confusing

### After (Non-blocking):
- **Total freeze time**: 200ms (LED flashing only)
- **Waveform packets lost**: 2 packets
- **Vitals updates missed**: 0-1 updates
- **User experience**: Smooth, calibration pulse appears naturally in waveform stream

---

## ADDITIONAL FIX: LED Flashing

The LED flashing loop also blocks for 600ms (3 flashes × 200ms each).

**Options**:

### Option 1: Reduce LED flashing (IMPLEMENTED ABOVE)
- 2 flashes instead of 3
- 50ms per flash instead of 100ms
- Total: 200ms blocking (acceptable)

### Option 2: Remove LED flashing entirely
- Just rely on calibration pulse in waveform data
- Zero blocking time
- User won't know calibration is happening (might be confusing)

### Option 3: Non-blocking LED pattern (complex)
- Use state machine in loop()
- Track LED flash timing
- More code complexity

**RECOMMENDATION**: Option 1 (already implemented above) - good balance

---

## MODE-SPECIFIC CALIBRATION FIX

While fixing the blocking delay, also add EEG calibration support:

**File**: `PhysiologicalSimulator.cpp`

**Add calibration check to EEG generator** (line 303):

```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ✅ NEW: Check if calibration pulse is active
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // EEG calibration: 100μV square pulse (1/10th of ECG's 1mV)
        if (elapsed < 1000) {
            // Head: baseline (0mV)
            sample = 8388608;  // ADC midpoint
        } else if (elapsed < 2000) {
            // Pulse: 0.1mV (100μV) square wave
            sample = 8388608 + 10000;  // 100μV above baseline (vs 100000 for ECG)
        } else {
            // Tail: baseline (0mV)
            sample = 8388608;
        }
        return;  // Skip normal EEG generation during calibration
    }

    // Normal EEG generation...
    float amplitude = generateEEGWaveform(eegPhase, channel);
    // ...
}
```

---

## FILES TO MODIFY

1. **esp32_hospital_watch_complete.ino**
   - Remove `delay(3100)` from `handleWaveformCalibrationCommand()` (line 956)
   - Reduce LED flashing to 200ms total
   - Add calibration completion tracking to `loop()`
   - Add global variables for completion tracking

2. **PhysiologicalSimulator.cpp**
   - Add calibration pulse logic to `generateEEGSampleWithPhase()` (line 303)

---

## TESTING PLAN

### Test 1: Non-Blocking Calibration (ECG Mode)

1. Open ECG Viewer
2. Observe Serial Monitor: "🔧 Waveform calibration command received"
3. **Expected**: LED flashes twice quickly (~200ms)
4. **Expected**: Waveform data continues streaming during calibration
5. **Expected**: Calibration pulse appears in waveform data (3 seconds)
6. **Expected**: After 3 seconds, Serial Monitor shows "✅ Calibration completion notification sent"

### Test 2: Non-Blocking Calibration (EEG Mode)

1. Set watch to EEG mode (GPIO pin LOW)
2. Open ECG Viewer (mode mismatch - intentional)
3. **Expected**: LED flashes twice
4. **Expected**: EEG waveform data continues streaming
5. **Expected**: Calibration pulse appears in EEG data (100μV amplitude)
6. **Expected**: Completion message includes `"mode": "eeg"`

### Test 3: Verify No Data Loss

1. Monitor backend logs for waveform stream messages
2. Trigger calibration
3. **Expected**: Waveform stream continues every 100ms (no gaps)
4. **Expected**: Vitals continue every 1 second (no missed updates)

---

## PRIORITY

**CRITICAL** - This bug causes data loss and poor user experience.

**Impact**:
- 3.7 seconds of frozen data every time calibration is triggered
- ~37 waveform packets lost per calibration
- 3-4 vitals updates missed
- MQTT commands blocked during calibration
- User thinks device is malfunctioning

**Fix Difficulty**: EASY - just remove one line and add completion check to loop()

---

## RELATED ISSUES

This blocking delay bug is related to:

1. **Mode-specific calibration bug** - Fixed simultaneously
2. **Calibration pulse not appearing** - Fixed by making it non-blocking
3. **Waveform data stops flowing** - Fixed by removing blocking delay

All three issues are addressed by this fix.
