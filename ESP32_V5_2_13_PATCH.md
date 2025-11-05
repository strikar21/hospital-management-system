# ESP32 v5.2.13 - Manual Patch Instructions

**Issue**: Edit tool cannot modify file - apply changes manually

---

## CHANGE 1: Add Calibration Tracking Variables

**File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Location**: After line 226

**Find this code** (around line 224-228):
```cpp
unsigned long disconnectTrackerLastCheck = 0;
unsigned long lastCommandReceivedAt = 0;
bool waveformCalibrationDue = false;

// ====================================
// SYSTEM ALERTS
// ====================================
```

**Replace with**:
```cpp
unsigned long disconnectTrackerLastCheck = 0;
unsigned long lastCommandReceivedAt = 0;
bool waveformCalibrationDue = false;
bool calibrationRequested = false;
String calibrationCommandId = "";
unsigned long calibrationStartMillis = 0;

// ====================================
// SYSTEM ALERTS
// ====================================
```

**Lines added**: 3 new lines (calibrationRequested, calibrationCommandId, calibrationStartMillis)

---

## CHANGE 2: Rewrite Calibration Handler (Non-Blocking)

**File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Location**: Lines 941-974

**Find this ENTIRE function**:
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
  delay(3100);

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

**Replace with** (NEW VERSION):
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

**Key changes**:
- ❌ Removed: `delay(3100)` - THE BUG!
- ✅ Added: Store commandId, set calibrationRequested flag
- ✅ Changed: LED flashes 2 times (200ms) instead of 3 times (600ms)
- ✅ Changed: Immediate ACK instead of waiting

---

## CHANGE 3: Add Completion Check to loop()

**File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Location**: After line 1134 (in `loop()` function, after alert checks)

**Find this section** (around line 1130-1140):
```cpp
  // ✅ v5.2.4: Check alerts even when offline (patient safety first)
  if (isProvisioned && (unsigned long)(millis() - lastAlertCheck) > 2000) {
    runAlertEngine();  // Already handles offline queueing internally
    lastAlertCheck = millis();
  }

  // ✅ v5.2.1: Process offline queue every 30 seconds when connected
  if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
    offlineQueue.processPendingMessages();
    lastQueueProcess = millis();
  }
```

**Add AFTER this section** (NEW CODE):
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

---

## CHANGE 4: Add EEG Calibration Support

**File**: `esp32_hospital_watch_complete/PhysiologicalSimulator.cpp`
**Location**: Line 547 (function `generateEEGSampleWithPhase()`)

**Find the START of this function** (around line 547):
```cpp
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // Generate waveform based on activity state and channel (using current phase)
    float amplitude = generateEEGWaveform(eegPhase, channel);
```

**Insert THIS CODE at the START** (before the `float amplitude` line):
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
```

**Result**: The calibration check is now at the START of the function, before normal EEG generation.

---

## CHANGE 5: Update Version and Changelog

**File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

### 5a. Update Version Number (Line 3)

**Find** (line 3):
```cpp
 * Version: 5.2.12
```

**Replace with**:
```cpp
 * Version: 5.2.13
```

### 5b. Add Changelog Entries (After line 31)

**Find** (lines 31-32):
```cpp
 * - ✅ v5.2.11: MEDICAL ACCURACY FIX - Channel-specific frequency mixing (frontal=beta, occipital=alpha)
 *
 * CHANGES FROM v5.0:
```

**Replace with**:
```cpp
 * - ✅ v5.2.11: MEDICAL ACCURACY FIX - Channel-specific frequency mixing (frontal=beta, occipital=alpha)
 * - ✅ v5.2.12: CRITICAL BUGFIX - Simulator mode was only set once at boot, never updated when GPIO pin changed
 * - ✅ v5.2.13: CRITICAL BUGFIX - Non-blocking calibration (removed delay(3100) that froze ESP32 for 3.7s)
 * - ✅ v5.2.13: FEATURE - EEG calibration support (100μV pulse for EEG mode, 1mV pulse for ECG mode)
 * - ✅ v5.2.13: ENHANCEMENT - Mode field in calibration completion message for frontend awareness
 *
 * CHANGES FROM v5.0:
```

### 5c. Add Detailed Changes (After line 68)

**Find** (lines 68-70):
```cpp
 * ✅ v5.2.12: CRITICAL BUGFIX - Simulator mode was only set once at boot, never updated when GPIO pin changed
 * ✅ v5.2.12: Bug: Swap ECG↔EEG cable → frontend shows correct mode label but wrong waveforms
 * ✅ v5.2.12: Fix: Check GPIO pin every 1s (before simulator.update()) and call setMode() dynamically
 * ✅ v5.2.12: Result: Mode switching now works correctly - waveforms match the current GPIO pin state
 */
```

**Replace with**:
```cpp
 * ✅ v5.2.12: CRITICAL BUGFIX - Simulator mode was only set once at boot, never updated when GPIO pin changed
 * ✅ v5.2.12: Bug: Swap ECG↔EEG cable → frontend shows correct mode label but wrong waveforms
 * ✅ v5.2.12: Fix: Check GPIO pin every 1s (before simulator.update()) and call setMode() dynamically
 * ✅ v5.2.12: Result: Mode switching now works correctly - waveforms match the current GPIO pin state
 * ✅ v5.2.13: CRITICAL FIX - Calibration handler no longer blocks (delay removed, completion tracked in loop)
 * ✅ v5.2.13: Bug: handleWaveformCalibrationCommand() used delay(3100) → froze all operations for 3.7s
 * ✅ v5.2.13: Fix: Non-blocking state machine with completion check in loop() → 200ms blocking only
 * ✅ v5.2.13: Result: Waveforms stream continuously during calibration, no data loss, better UX
 * ✅ v5.2.13: FEATURE - EEG calibration pulse (100μV) now works alongside ECG calibration (1mV)
 */
```

---

## SUMMARY OF CHANGES

**Files Modified**: 2
1. `esp32_hospital_watch_complete.ino` - 5 changes
2. `PhysiologicalSimulator.cpp` - 1 change

**Total Lines Added**: ~50 lines
**Total Lines Removed**: ~10 lines

**Before**: Calibration freezes ESP32 for 3.7 seconds
**After**: Calibration is non-blocking (200ms), data continues flowing

---

## VERIFICATION AFTER APPLYING PATCH

After making all changes, verify:

1. **Compile Check**:
   ```
   Arduino IDE → Sketch → Verify/Compile
   Should compile without errors
   ```

2. **Line Count Check**:
   ```bash
   wc -l esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
   # Should be approximately 2210 lines (was ~2180)
   ```

3. **Grep Verification**:
   ```bash
   grep -n "calibrationRequested" esp32_hospital_watch_complete.ino
   # Should show lines: 226, 941, 1134 (approximately)

   grep -n "delay(3100)" esp32_hospital_watch_complete.ino
   # Should return NO results (removed!)

   grep -n "v5.2.13" esp32_hospital_watch_complete.ino
   # Should show version line and changelog entries
   ```

---

## NEXT STEPS AFTER PATCHING

1. **Compile** firmware in Arduino IDE
2. **Flash** to ESP32
3. **Test** calibration in ECG mode
4. **Test** calibration in EEG mode
5. **Verify** waveforms continue streaming during calibration

---

**STATUS**: Patch file created - ready for manual application
